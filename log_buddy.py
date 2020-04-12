import logging
import sys
import time
from statistics import median

import cache_buddy
from progress_record import ProgressRecord


# noinspection PyUnresolvedReferences
class LogBuddy:
    from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    progress_key: str
    last_cache_update: float
    
    def __init__(self):
        self.reset_stats()
        self.logger = logging.getLogger("LogBuddy")
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def set_progress_key(self, key):
        self.progress_key = key
    
    def reset_stats(self):
        self.n_docs_loaded = 0
        
        self.n_authors_queried = 0
        self.n_network_queries = 0
        
        self.n_coauthors_considered = 0
        
        self.time_waiting_network = []
        self.time_waiting_cached_author = 0
        self.time_waiting_cached_doc = 0
        self.time_preparing_response = -1
        self.start_time = None
        self.stop_time = None
        
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
        
    def c(self, msg, **kwargs):
        self.logger.critical(msg, **kwargs)
    
    def set_log_level(self, level):
        self.logger.setLevel(level)
    
    def on_doc_loaded(self, n=1):
        self.update_progress_cache()
        self.n_docs_loaded += n
    
    def on_doc_load_timed(self, time):
        self.time_waiting_cached_doc += time
    
    def on_author_load_timed(self, time):
        self.time_waiting_cached_author += time
    
    def on_author_queried(self, n=1):
        self.update_progress_cache()
        self.n_authors_queried += n
    
    def on_coauthor_considered(self, n=1):
        self.update_progress_cache()
        self.n_coauthors_considered += n
    
    def on_network_complete(self, time):
        self.update_progress_cache()
        self.n_network_queries += 1
        self.time_waiting_network.append(time)
    
    def on_start_path_finding(self):
        self.start_time = time.time()
        self.update_progress_cache()
    
    def on_stop_path_finding(self):
        self.stop_time = time.time()
    
    def on_result_prepared(self, time):
        self.time_preparing_response = time
    
    def get_search_time(self):
        if self.stop_time is None or self.start_time is None:
            return -1
        return self.stop_time - self.start_time
    
    def get_result_prep_time(self):
        return self.time_preparing_response
    
    def log_stats(self):
        self.i(f"{self.n_docs_loaded} docs and {self.n_authors_queried} authors queried")
        self.i(f"{self.n_coauthors_considered} coauthor names seen")
        if len(self.time_waiting_network) == 0:
            self.i("No network queries")
        else:
            minimum = min(self.time_waiting_network)
            med = median(self.time_waiting_network)
            maximum = max(self.time_waiting_network)
            total = sum(self.time_waiting_network)
            self.i(f"{self.n_network_queries} network queries in "
                   "min/med/max/tot "
                   f"{minimum:.2f}/{med:.2f}/{maximum:.2f}/{total:.2f} s")
        self.i(f"Spent {self.time_waiting_cached_author:.2f} s loading authors"
               f" and {self.time_waiting_cached_doc:.2f} s loading docs"
               " from backing cache")
        self.i(f"Search took {self.get_search_time():.2f} s")
        self.i(f"Response prepared in {self.time_preparing_response:.2f} s")
    
    def update_progress_cache(self):
        now = time.time()
        if (self.progress_key is not None
                and now - self.last_cache_update > 1):
            self.last_cache_update = now
            cache_buddy.cache_progress_data(
                ProgressRecord(n_ads_queries=self.n_network_queries,
                               n_authors_queried=self.n_authors_queried,
                               n_docs_loaded=self.n_docs_loaded),
                self.progress_key
            )


logging.captureWarnings(True)
lb = LogBuddy()
