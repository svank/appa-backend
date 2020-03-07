import dataclasses
from typing import List


@dataclasses.dataclass()
class DocumentRecord:
    bibcode: str
    title: str
    authors: List[str]
    affils: List[str]
    doi: str
    doctype: str
    keywords: List[str]
    publication: str
    pubdate: str
    citation_count: int
    read_count: int
    
    def asdict(self):
        return dataclasses.asdict(self)
