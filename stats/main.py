"""
This is a monolithic script that pulls existing data from Cloud Storage,
updates it with the latest Metrics and cache count data, stores the new
data file in Cloud Storage, stores an archived data file at the end of each
month, and produces updated plots, which it puts in Cloud Storage
"""
import json
import os
import time
from collections import defaultdict
from datetime import datetime

import dateutil.tz
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from google.cloud import monitoring_v3, pubsub_v1, storage
from google.cloud.monitoring_v3.types import MetricDescriptor
from matplotlib.ticker import ScalarFormatter
from stats_config import PROJECT_NAME, SUBSCRIPTION_NAME, TOPIC, PUBSUB_WAIT
from stats_config import STATS_BUCKET_NAME, PLOTS_BUCKET_NAME, EARLIEST_DATE

metrics_client = monitoring_v3.MetricServiceClient()
storage_client = storage.Client()
subscriber = pubsub_v1.SubscriberClient()
publisher = pubsub_v1.PublisherClient()

project_name = metrics_client.project_path(PROJECT_NAME)
subscription_path = subscriber.subscription_path(
    PROJECT_NAME, SUBSCRIPTION_NAME)
topic_path = publisher.topic_path(PROJECT_NAME, TOPIC)

bucket = storage_client.bucket(STATS_BUCKET_NAME)
pbucket = storage_client.bucket(PLOTS_BUCKET_NAME)

metrics = [
    ("ads_query_count", ("cumulative", "distribution"), "ADS lookup count"),
    ("authors_queried", ("cumulative", "distribution"), "authors loaded"),
    ("coauthors_seen", ("cumulative", "distribution"), "author names seen"),
    ("cold_starts", ("cumulative",), "Cloud Function instance cold starts"),
    ("connections_found", ("cumulative", "distribution"), "coauthorship chains found"),
    ("distance_found", ("distribution",), "distance between given authors"),
    ("docs_queried", ("cumulative", "distribution"), "documents used"),
    ("docs_returned", ("cumulative", "distribution"), "documents found to be relevant"),
    ("duration_ads", ("cumulative", "distribution"), "seconds querying ADS"),
    ("duration_cache_authors", ("cumulative", "distribution"), "seconds loading cached author records"),
    ("duration_cache_docs", ("cumulative", "distribution"), "seconds loading cached document records"),
    ("duration_compute", ("cumulative", "distribution"), "seconds processing"),
    ("duration_response", ("cumulative", "distribution"), "seconds prepping response"),
    ("duration_search", ("cumulative", "distribution"), "seconds searching for paths"),
    ("duration_total", ("cumulative", "distribution"), "total backend runtime (seconds)"),
    ("pf_count", ("cumulative",), "path finding requests served"),
   ]

timezone = dateutil.tz.gettz("America/Denver")


def get_metric_for_time(metric, t_start, t_end):
    if t_start < EARLIEST_DATE:
        t_start = EARLIEST_DATE
    interval = monitoring_v3.types.TimeInterval()
    interval.end_time.seconds = int(t_end)
    interval.start_time.seconds = int(t_start)
    aggregation = monitoring_v3.types.Aggregation()
    aggregation.alignment_period.seconds = int(t_end - t_start)
    aggregation.per_series_aligner = monitoring_v3.enums.Aggregation.Aligner.ALIGN_SUM
    results = metrics_client.list_time_series(
        project_name,
        f'metric.type = "logging.googleapis.com/user/{metric}"',
        interval,
        monitoring_v3.enums.ListTimeSeriesRequest.TimeSeriesView.FULL,
        aggregation)
    results = list(results)
    if len(results) > 1:
        print("WARNING: multiple results!")
    try:
        result = results[0]
    except IndexError:
        return None
    return result


def get_metric_for_hour(metric, t_start):
    return get_metric_for_time(metric, t_start, t_start + 60 * 60)


def get_metric_for_month(metric, t_end):
    # Define a month as a 30-day period
    t_start = t_end - 30 * 24 * 60 * 60
    return get_metric_for_time(metric,
                               t_start,
                               t_end)


def get_metric_sum_for_hour(*args, **kwargs):
    result = get_metric_for_hour(*args, **kwargs)
    if result is None:
        return 0
    
    sum = 0
    for point in result.points:
        if result.value_type == MetricDescriptor.INT64:
            sum += point.value.int64_value
        elif result.value_type == MetricDescriptor.DOUBLE:
            sum += round(point.value.double_value)
        elif result.value_type == MetricDescriptor.DISTRIBUTION:
            val = point.value.distribution_value
            sum += val.mean * val.count
    return sum


def get_updated_cache_count(n_author, n_document):
    """
    Processes Pub/Sub queue to update the count of items in the cache
    
    Firestore doesn't let you just count the number of documents in a
    collection without retrieving them all, which is slow and expensive.
    But it does let you fire off a Cloud Function every time a document is
    created or deleted. So we do that, and the Function leaves a Pub/Sub
    message indicating what happened. Our job here is to consume those
    messages to produce an updated item count. Firestore doesn't promise that
    the Cloud Function runs only once, so we need to be sure to de-duplicate.
    (Pub/Sub also mentions the possibility of seeing a single message multiple
    times, but I think that's more about multiple subscribers and
    acknowledgement timeouts.) Because of the need to de-dupe and because there
    can be some latency and out-of-order-ness in every step from Firestore to
    here, any message produced in the PUBSUB_WAIT seconds is re-sent to Pub/Sub
    (after de-duping) and is not incorporated in the final change list. This
    ensures that every message gets de-duped with regard to at least one
    minute of messages both before and after.
    """
    messages = []
    ack_ids = []
    now = time.time()
    
    # First: retrieve all pending messages. There's no way to make
    # max_messages unlimited.
    while True:
        response = subscriber.pull(subscription_path,
                                   max_messages=500)
        
        for msg in response.received_messages:
            ack_ids.append(msg.ack_id)
            msg = msg.message
            messages.append((
                msg.publish_time.seconds + msg.publish_time.nanos / 1e9,
                msg))
        
        if len(response.received_messages) == 0:
            break
    
    if len(messages) == 0:
        return n_author, n_document
    
    # Put messages in order by publication time
    messages = sorted(messages, key=lambda m: m[0])
    
    # Work out the final change for each item ID, ignoring duplicates
    # if there isn't an opposite-sign change in between. (i.e. create-create
    # should be de-duped, but create-delete-create is OK)
    author_changes = defaultdict(lambda: (0, 0))
    doc_changes = defaultdict(lambda: (0, 0))
    future = None
    for _, msg in messages:
        record = (author_changes if msg.attributes['type'] == "author"
                  else doc_changes)
        delta = 1 if msg.attributes['action'] == "create" else -1
        key = msg.data
        state, last_delta = record[key]
        if last_delta == delta:
            # This appears to be a duplicate message
            pass
        else:
            # If it's too recent of a message, re-add it to the Pub/Sub queue.
            # Record the sense of the change for de-duping, but don't let it
            # affect the count
            if now - msg.publish_time.seconds < PUBSUB_WAIT:
                record[key] = (state, delta)
                future = publisher.publish(topic_path,
                                           data=msg.data,
                                           type=msg.attributes['type'],
                                           action=msg.attributes['action'])
            else:
                record[key] = (state + delta, delta)
    
    # Boil down the change list to a number
    delta_author = [state for state, _ in author_changes.values()]
    delta_doc = [state for state, _ in doc_changes.values()]
    n_author += sum(delta_author)
    n_document += sum(delta_doc)
    
    # Ensure we wait until the last message is published
    if future is not None:
        future.result()
    
    # We can't ack too many messages at once
    CHUNK_SIZE = 500
    reqs = (ack_ids[i:i+CHUNK_SIZE]
            for i in range(0, len(ack_ids), CHUNK_SIZE))
    for req in reqs:
        subscriber.acknowledge(subscription_path, req)
    
    return n_author, n_document


def x_axis_dates(ax=None, fig=None):
    """Helper function to format the x axis as dates.

    Input:
    ax:  An Axes instance or an iterable of Axes instances.
    Optional, defaults to plt.gca()
    fig: The Figure instance containing those Axes or Axeses
    Optional, defaults to plt.gcf()
    """
    if ax is None: ax = plt.gca()
    if fig is None: fig = plt.gcf()
    loc = mdates.AutoDateLocator()
    fmt = mdates.AutoDateFormatter(loc)
    try:
        ax.xaxis.set_major_locator(loc)
        ax.xaxis.set_major_formatter(fmt)
    except AttributeError:
        for a in ax:
            # Fresh locators/formatters are needed for each instance
            loc = mdates.AutoDateLocator()
            fmt = mdates.AutoDateFormatter(loc)
            a.xaxis.set_major_locator(loc)
            a.xaxis.set_major_formatter(fmt)
    fig.autofmt_xdate()


def gen_bin_edges(value):
    opts = value.bucket_options.exponential_buckets
    if opts.growth_factor != 0:
        bounds = [opts.scale * opts.growth_factor ** i
                  for i in range(len(value.bucket_counts))]
        bounds.insert(0, 0)
        return bounds, "log"
    else:
        opts = value.bucket_options.linear_buckets
        bounds = [opts.offset + opts.width * i
                  for i in range(len(value.bucket_counts))]
        bounds.insert(0, 0)
        return bounds, "linear"


def update_stats(request):
    cur_hour = datetime.now()
    cur_hour = cur_hour.replace(minute=0, second=0, microsecond=0)
    cur_hour = cur_hour.timestamp()
    
    blob = bucket.blob("latest")
    if blob.exists():
        # Grab the existing data
        data = json.loads(blob.download_as_string())
        cumulative = data['cumulative']
        distr = data['distribution']
        # Make sure we're OK if metrics are added later on
        for metric in metrics:
            if "cumulative" in metric[1] and metric[0] not in cumulative:
                cumulative[metric[0]] = [0] * len(cumulative['timestamp'])
    else:
        # Initialize an empty data set
        data = {"cumulative": {}, "distribution": {}}
        cumulative = data['cumulative']
        distr = data['distribution']
        data['cache_size'] = {"authors": [0], "documents": [0]}
        # Have this data set be filled with the last day's data
        cumulative['timestamp'] = [cur_hour - 24 * 60 * 60]
        for metric in metrics:
            if "cumulative" in metric[1]:
                cumulative[metric[0]] = [0]
    
    # Fill in data for every complete hour that's passed since the last update
    timestamp = cumulative['timestamp'][-1]
    timestamp += 60 * 60
    n_collected_timestamps = 0
    while timestamp < cur_hour:
        n_collected_timestamps += 1
        print(f"Collecting data for timestamp {timestamp}")
        cumulative['timestamp'].append(timestamp)
        for metric in metrics:
            if "cumulative" in metric[1]:
                increment = get_metric_sum_for_hour(metric[0], timestamp)
                if metric[0] == "duration_total":
                    increment /= 1000
                new_val = cumulative[metric[0]][-1] + increment
                cumulative[metric[0]].append(new_val)
        
        timestamp += 60 * 60
    
    if n_collected_timestamps > 0:
        # Update distributions, which are a summary of the past month,
        # not a time series
        print("Updating distributions")
        for metric in metrics:
            if "distribution" in metric[1]:
                record = get_metric_for_month(metric[0], time.time())
                if record is not None:
                    value = record.points[0].value.distribution_value
                    bounds, type = gen_bin_edges(value)
                    counts = list(value.bucket_counts)
                    if metric[0] == "duration_total":
                        bounds = [bound / 1000 for bound in bounds]
                    distr[metric[0]] = (bounds, counts, type)
        
        print("Updating cache sizes")
        # Update the cache size data
        n_authors = data['cache_size']['authors'][-1]
        n_docs = data['cache_size']['documents'][-1]
        
        # If we have multiple timestamps we need to fill in, pad the list
        # with repeats, and put the update in the very last timestamp
        data['cache_size']['authors'].extend(
            [n_authors] * (n_collected_timestamps - 1))
        data['cache_size']['documents'].extend(
            [n_docs] * (n_collected_timestamps - 1))
        
        n_authors, n_docs = get_updated_cache_count(n_authors, n_docs)
        data['cache_size']['authors'].append(n_authors)
        data['cache_size']['documents'].append(n_docs)
        
        # Save the new data file
        print("Saving data")
        blob.upload_from_string(json.dumps(data))
    
        if (datetime.fromtimestamp(cumulative['timestamp'][-1], timezone).month
                !=
                datetime.fromtimestamp(cumulative['timestamp'][-2], timezone).month):
            # We've rolled over to another month---store an archive file
            print("Archiving data")
            last_month = datetime.fromtimestamp(cumulative['timestamp'][-2], timezone)
            ablob = bucket.blob(f"archive-{last_month.year}-{last_month.month}")
            ablob.upload_from_string(json.dumps(data))
    
    # Produce updated plots
    times = [mdates.date2num(datetime.fromtimestamp(ts, timezone)) for ts in cumulative['timestamp']]
    print("Updating plots")
    for cache_name in ("authors", "documents"):
        plt.figure(figsize=(5.5, 3.5))
        plt.plot(times, data['cache_size'][cache_name])
        x_axis_dates()
        plt.title(f"Number of {cache_name} in cache")
        fname = f"cache_size_{cache_name}.png"
        fpath = "/tmp/" + fname
        plt.savefig(fpath, dpi=100)
        plt.close()
        pbucket.blob(fname).upload_from_filename(fpath)
        os.remove(fpath)
    
    for metric in metrics:
        if "cumulative" in metric[1] and metric[0] in cumulative:
            plt.figure(figsize=(5.5, 3.5))
            plt.plot(times, cumulative[metric[0]])
            x_axis_dates()
            plt.title("Cumulative " + metric[2], fontsize=11)
            fname = metric[0] + "-cumulative.png"
            fpath = "/tmp/" + fname
            plt.savefig(fpath, dpi=100)
            plt.close()
            pbucket.blob(fname).upload_from_filename(fpath)
            os.remove(fpath)
        
        if "distribution" in metric[1] and metric[0] in distr:
            plt.figure(figsize=(5.5, 3.5))
            x, y, type = distr[metric[0]]
            width = np.diff(x)
            align = "center" if metric[0] == "distance_found" else "edge"
            plt.bar(x[:-1], y, align=align, width=width, edgecolor="#184B72")
            if type == "log":
                plt.xscale('log')
                
                # Scientific notation seems to be default for log axes, but I
                # don't want it
                formatter = ScalarFormatter()
                formatter.set_scientific(False)
                
                # By default, the minor formatter on log axes seems to be
                # something that intelligently turns labels on/off depending
                # on whether they're needed. If we replace the formatter,
                # we don't get that behavior and the labels always show up,
                # whether or not they should. The best way I can find to
                # replicate that behavior and still get non-sci-notation
                # labels is to (a) force the graph to render, then (b) check
                # if the rendered minor labels contain text, and if so,
                # replace the minor formatter; otherwise, leave it be so
                # minor labels don't appear.
                
                # Be cafeful! It seems plt.draw() is non-blocking, which makes
                # the following check not work, while canvas.draw() seems to
                # be a blocking call.
                plt.gcf().canvas.draw()
                if (len(plt.gca().get_xminorticklabels())
                        and plt.gca().get_xminorticklabels()[0].get_text() != ''):
                    plt.gca().xaxis.set_minor_formatter(formatter)
                plt.gca().xaxis.set_major_formatter(formatter)
            plt.title(f"Histogram of {metric[2]} per query", fontsize=11)
            fname = metric[0] + "-distribution.png"
            fpath = "/tmp/" + fname
            plt.savefig(fpath, dpi=100)
            plt.close()
            pbucket.blob(fname).upload_from_filename(fpath)
            os.remove(fpath)


if __name__ == "__main__":
    update_stats(None)
