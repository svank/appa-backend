import dataclasses
import time
from typing import List


@dataclasses.dataclass()
class DocumentRecord:
    bibcode: str
    title: str
    authors: List[str]
    affils: List[str]
    doctype: str
    keywords: List[str]
    publication: str
    pubdate: str
    citation_count: int
    read_count: int
    timestamp: int = -1
    
    def __post_init__(self):
        if self.timestamp == -1:
            self.timestamp = int(time.time())
    
    def asdict(self):
        return dataclasses.asdict(self)
