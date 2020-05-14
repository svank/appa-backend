import dataclasses
import time


@dataclasses.dataclass()
class ProgressRecord:
    n_ads_queries: int
    n_authors_queried: int
    n_docs_queried: int
    path_finding_complete: bool
    timestamp: int = -1
    
    def __post_init__(self):
        if self.timestamp == -1:
            self.timestamp = int(time.time())
    
    def asdict(self):
        return dataclasses.asdict(self)
