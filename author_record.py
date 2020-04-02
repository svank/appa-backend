import dataclasses
import time
from typing import List

from ads_name import ADSName
from document_record import DocumentRecord


@dataclasses.dataclass()
class AuthorRecord:
    name: ADSName
    documents: List[DocumentRecord]
    timestamp: int = -1
    
    def __post_init__(self):
        self.name = ADSName.parse(self.name)
        if self.timestamp == -1:
            self.timestamp = int(time.time())
    
    def copy(self):
        return AuthorRecord(name=self.name, documents=self.documents)
    
    def asdict(self):
        return dataclasses.asdict(self)
