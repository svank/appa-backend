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
        
        lb.i("Storing large result for separate download")
        
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
