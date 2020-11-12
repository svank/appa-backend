import dataclasses
import time


@dataclasses.dataclass()
class ProgressRecord:
    n_ads_queries: int
    n_authors_queried: int
    n_docs_queried: int
    n_docs_loaded: int
    n_docs_relevant: int
    path_finding_complete: bool
    timestamp: float = -1
    
    def __post_init__(self):
        if self.timestamp == -1:
            self.timestamp = time.time()
    
    def asdict(self):
        return dataclasses.asdict(self)
