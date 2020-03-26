import dataclasses


@dataclasses.dataclass()
class ProgressRecord:
    n_ads_queries: int
    n_authors_queried: int
    n_docs_loaded: int
    
    def asdict(self):
        return dataclasses.asdict(self)
