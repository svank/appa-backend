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
# error_logger = None
#
# def log_error_extra(message):
#     global error_logger
#     if error_logger is None:
#         from google.cloud import error_reporting
#         error_logger = error_reporting.Client()
#     error_logger.report(message)
#
#
# def log_exception_extra():
#     global error_logger
#     if error_logger is None:
#         from google.cloud import error_reporting
#         error_logger = error_reporting.Client()
#     error_logger.report_exception()
