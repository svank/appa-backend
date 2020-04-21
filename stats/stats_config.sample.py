from datetime import datetime, timedelta, timezone

STATS_BUCKET_NAME = "Storage bucket for stats data"
PLOTS_BUCKET_NAME = "Storage bucket for plots"

PROJECT_NAME = "GCP project name"

SUBSCRIPTION_NAME = "Pub/Sub subscription for firestore change messages"
TOPIC = "Pub/Sub topic for re-publishing firestore change messages"
PUBSUB_WAIT = 120

EARLIEST_DATE = datetime(2020, 4, 19, tzinfo=timezone(timedelta(0))).timestamp()