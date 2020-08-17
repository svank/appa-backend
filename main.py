"""
Entry points for Cloud Functions. For local usage, see appa.py
"""

import json

import backend_common
import cache_buddy
from log_buddy import lb

# Cloud Function responses cannot be larger than 10 MiB. If our response
# is larger, put it in Cloud Storage and return a link instead.
MAXIMUM_RESPONSE_SIZE = 9.5 * 1024 * 1024
# This bucket should be set to auto-delete files after a day or whatever
from local_config import CLOUD_STORAGE_BUCKET_NAME
CLOUD_STORAGE_URL_FORMAT = "https://storage.googleapis.com/storage/v1/b/{}/o/{}?alt=media"

lb.set_log_level(lb.INFO)
lb.i("Instance cold start")


def find_route(request):
    try:
        data, code, headers, cache_key = backend_common.find_route(
            request, load_cached_result=False)
        
        if data is None:
            # The result is already cached---refer the user to the cache file
            response = {"responseAtUrl": CLOUD_STORAGE_URL_FORMAT.format(
                CLOUD_STORAGE_BUCKET_NAME, cache_key)}
            return json.dumps(response), code, headers
        
        if len(data.encode('utf-8')) > MAXIMUM_RESPONSE_SIZE:
            lb.i("Sending large result as separate download")
            response = {"responseAtUrl": CLOUD_STORAGE_URL_FORMAT.format(
                CLOUD_STORAGE_BUCKET_NAME, cache_key)}
            return json.dumps(response), code, headers
        return data, code, headers
    except:
        lb.log_exception()


def get_graph_data(request):
    return backend_common.get_graph_data(request)


def clean_cache(request):
    cache_buddy.clear_stale_data()


# When we clear stale data in the cache, it's always possible that a
# path-finding that's in-progress could have already read stale author records
# and has not yet but will read corresponding stale document records. If we
# clear all the stale data at that point, the route-finding process will have
# to pull the document data from ADS, and later that same document data will
# be pulled again if/when the author record is pulled from ADS by a future
# route-finding process. So clearing both author and document records is best
# done at a quiet time when no route-finding is happening. But simply clearing
# stale author records doesn't have any associated problems: if a current
# process has used the stale author record, the stale document records will
# still be around. And if the author data is pulled from ADS before the
# stale document records are deleted, they'll be updated, saving our Firestore
# delete quota.
def clean_cache_not_documents(request):
    cache_buddy.clear_stale_data(documents=False)
