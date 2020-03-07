import logging
from statistics import median


class LogBuddy:
    from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    n_docs_loaded = 0
    
    n_authors_queried = 0
    n_network_queries = 0
    
    n_coauthors_considered = 0
    
    time_waiting_network = None
    
    def __init__(self):
        self.time_waiting_network = []
        self.logger = logging.getLogger("LogBuddy")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
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


logging.captureWarnings(True)
lb = LogBuddy()