import dataclasses
from typing import List

from ads_name import ADSName
from document_record import DocumentRecord


@dataclasses.dataclass()
class AuthorRecord:
    name: ADSName
    documents: List[DocumentRecord]
    
    def __post_init__(self):
        self.name = ADSName.parse(self.name)
    
    def copy(self):
        return AuthorRecord(name=self.name, documents=self.documents)
    
    def asdict(self):
        return dataclasses.asdict(self)
