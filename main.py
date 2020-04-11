"""
Entry points for Cloud Functions. For local usage, see appa.py
"""

import cache_buddy
from backend_common import _find_route, _get_progress
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
    data, code, headers = _find_route(request)
    
    if len(data.encode('utf-8')) > MAXIMUM_RESPONSE_SIZE:
        # It's rare we need these imports, so don't do it unless we need them
        from google.cloud import storage
        import hashlib
        import json
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(CLOUD_STORAGE_BUCKET_NAME)
        blob_name = hashlib.sha256(data.encode()).hexdigest()
        blob = bucket.blob(blob_name)
        blob.upload_from_string(data)
        
        response = {"responseAtUrl": CLOUD_STORAGE_URL_FORMAT.format(
            CLOUD_STORAGE_BUCKET_NAME, blob_name)}
        return json.dumps(response), code, headers
    return data, code, headers


def get_progress(request):
    return _get_progress(request)


def clean_cache(request):
    cache_buddy.backing_cache.clear_stale_data()
