import dataclasses
from typing import List

from document_record import DocumentRecord
from ads_name import ADSName


@dataclasses.dataclass()
class AuthorRecord:
    name: ADSName
    documents: List[DocumentRecord]
    
    def __post_init__(self):
        self.name = ADSName(self.name)
    
    def copy(self):
        return AuthorRecord(name=self.name, documents=self.documents)
    
    def asdict(self):
        return dataclasses.asdict(self)
