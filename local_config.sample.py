# The module whose name is in this string will be imported and used
backing_cache = "cache_fs"

# For firestore:
# backing_cache = "cache_firestore"
# relay_token = "token_here"

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

# Extra actions when an error or an unhandled exception is logged
def log_error_extra(msg): pass
def log_exception_extra(): pass

# For Cloud Error Reporting:
# def log_error_extra(message):
#     from google.cloud import error_reporting
#     if message:
#         error_reporting.Client().report(message)
#     else:
#         error_reporting.Client().report_exception()
#
#
# def log_exception_extra():
#     from google.cloud import error_reporting
#     error_reporting.Client().report_exception()
