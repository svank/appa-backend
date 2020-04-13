import cache_fs
backing_cache = cache_fs

ADS_TOKEN = "token_here"

CLOUD_STORAGE_BUCKET_NAME = ""

import logging
logging_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s')
logging_handler.setFormatter(formatter)

# For Cloud Logging:
# from google.cloud import logging as cloud_logging
# logging_handler = cloud_logging.Client().get_default_handler()
