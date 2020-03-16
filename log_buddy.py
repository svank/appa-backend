import logging
import time
from statistics import median


# noinspection PyUnresolvedReferences
class LogBuddy:
    from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    def __init__(self):
        self.reset_stats()
        self.logger = logging.getLogger("LogBuddy")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def reset_stats(self):
        self.n_docs_loaded = 0
        
        self.n_authors_queried = 0
        self.n_network_queries = 0
        
        self.n_coauthors_considered = 0
        
        self.time_waiting_network = []
        self.start_time = None
        self.stop_time = None
        
    
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
        self.n_docs_loaded += n
    
    def on_author_queried(self, n=1):
        self.n_authors_queried += n
    
    def on_coauthor_considered(self, n=1):
        self.n_coauthors_considered += n
    
    def on_network_complete(self, time):
        self.n_network_queries += 1
        self.time_waiting_network.append(time)
    
    def on_start_path_finding(self):
        self.start_time = time.time()
    
    def on_stop_path_finding(self):
        self.stop_time = time.time()
    
    def get_search_time(self):
        return self.stop_time - self.start_time
    
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
        self.i(f"Search took {self.get_search_time():.2f} s")


logging.captureWarnings(True)
lb = LogBuddy()