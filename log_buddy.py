import logging
import time
from statistics import median

import cache_buddy
from local_config import logging_handler, log_error_extra, log_exception_extra
from progress_record import ProgressRecord


# noinspection PyUnresolvedReferences
class LogBuddy:
    from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    progress_key: str
    last_cache_update: float
    
    def __init__(self):
        self.reset_stats()
        self.logger = logging.getLogger("LogBuddy")
        self.logger.addHandler(logging_handler)
    
    def set_progress_key(self, key):
        self.progress_key = key
        self.update_progress_cache(force=True)
    
    def reset_stats(self):
        self.n_docs_loaded = 0
        self.n_docs_relevant = 0
        
        self.n_authors_queried = 0
        self.n_docs_queried = 0
        self.n_network_queries = 0
        self.n_authors_from_ADS = 0
        
        self.n_coauthors_seen = 0
        
        self.distance = -1
        self.n_connections = -1
        
        self.time_waiting_network = []
        self.time_waiting_cached_author = 0
        self.time_waiting_cached_doc = 0
        self.time_storing_to_cache = 0
        self.time_preparing_response = -1
        self.start_time = None
        self.stop_time = None
        self.path_finding_complete = False
        
        self.progress_key = None
        self.last_cache_update = 0
    
    def d(self, msg, **kwargs):
        self.logger.debug(msg, **kwargs)
        
    def i(self, msg, **kwargs):
        self.logger.info(msg, **kwargs)
        
    def w(self, msg, **kwargs):
        self.logger.warning(msg, **kwargs)
        
    def e(self, msg, **kwargs):
        self.logger.error(msg, **kwargs)
        log_error_extra(msg)
        
    def c(self, msg, **kwargs):
        self.logger.critical(msg, **kwargs)
        log_error_extra(msg)
    
    def log_exception(self):
        import traceback
        log_exception_extra()
        self.logger.error(traceback.format_exc())
    
    def set_log_level(self, level):
        self.logger.setLevel(level)
    
    def on_doc_queried(self, n=1):
        self.n_docs_queried += n
        self.update_progress_cache()
    
    def on_doc_loaded(self, n=1):
        self.n_docs_loaded += n
        self.update_progress_cache()
    
    def set_n_docs_relevant(self, n):
        self.n_docs_relevant = n
        self.update_progress_cache()
    
    def on_doc_load_timed(self, time):
        self.time_waiting_cached_doc += time
    
    def on_author_load_timed(self, time):
        self.time_waiting_cached_author += time
    
    def on_cache_store_timed(self, time):
        self.time_storing_to_cache += time
    
    def on_author_queried(self, n=1):
        self.n_authors_queried += n
        self.update_progress_cache()
    
    def on_coauthor_seen(self, n=1):
        self.n_coauthors_seen += n
    
    def on_network_complete(self, time):
        self.n_network_queries += 1
        self.time_waiting_network.append(time)
        self.update_progress_cache()
    
    def on_author_queried_from_ADS(self, n=1):
        self.n_authors_from_ADS += n
    
    def on_start_path_finding(self):
        self.start_time = time.time()
        self.update_progress_cache()
    
    def on_stop_path_finding(self):
        self.stop_time = time.time()
        self.path_finding_complete = True
        self.update_progress_cache(force=True)
    
    def on_result_prepared(self, time):
        self.time_preparing_response = time
    
    def set_distance(self, distance):
        self.distance = distance
    
    def set_n_connections(self, connections):
        self.n_connections = connections
    
    def get_search_time(self):
        if self.stop_time is None or self.start_time is None:
            return -1
        return self.stop_time - self.start_time
    
    def get_result_prep_time(self):
        return self.time_preparing_response
    
    def log_stats(self):
        self.i(f"{self.n_connections} connections found w/ distance {self.distance}!")
        self.i(f"{self.n_docs_queried} docs and {self.n_authors_queried} authors queried")
        self.i(f"{self.n_coauthors_seen} coauthor names seen")
        if self.n_docs_relevant >= 0:
            self.i(f"{self.n_docs_relevant} docs returned")
        if len(self.time_waiting_network) == 0:
            self.i("0 network queries")
        else:
            minimum = min(self.time_waiting_network)
            med = median(self.time_waiting_network)
            maximum = max(self.time_waiting_network)
            total = sum(self.time_waiting_network)
            self.i(f"{self.n_network_queries} network queries in "
                   "min/med/max/tot "
                   f"{minimum:.2f}/{med:.2f}/{maximum:.2f}/{total:.2f} s")
        self.i(f"Spent {self.time_waiting_cached_author:.2f} s loading authors,"
               f" {self.time_waiting_cached_doc:.2f} s loading docs,"
               f" and {self.time_storing_to_cache:.2f} s storing data"
               " to/from backing cache")
        self.i(f"Search took {self.get_search_time():.2f} s")
        self.i(f"Response prepared in {self.time_preparing_response:.2f} s")
        
        if self.time_preparing_response >= 0:
            own_time = (self.get_search_time() + self.time_preparing_response
                        - sum(self.time_waiting_network)
                        - self.time_waiting_cached_author
                        - self.time_waiting_cached_doc
                        - self.time_storing_to_cache)
            self.i(f"Total compute time: {own_time:.2f} s")
    
    def update_progress_cache(self, force=False):
        now = time.time()
        if (self.progress_key is not None
                and (now - self.last_cache_update > .25
                     or force)):
            self.last_cache_update = now
            cache_buddy.cache_progress_data(
                ProgressRecord(n_ads_queries=self.n_authors_from_ADS,
                               n_authors_queried=self.n_authors_queried,
                               n_docs_queried=self.n_docs_queried,
                               n_docs_relevant=self.n_docs_relevant,
                               n_docs_loaded=self.n_docs_loaded,
                               path_finding_complete=self.path_finding_complete),
                self.progress_key
            )


logging.captureWarnings(True)
lb = LogBuddy()
