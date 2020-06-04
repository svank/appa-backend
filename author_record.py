import dataclasses
import time
from typing import Dict, List

from ads_name import ADSName


@dataclasses.dataclass()
class AuthorRecord:
    name: ADSName
    documents: List[str]
    appears_as: Dict[str, List[str]] = dataclasses.field(default_factory=dict)
    coauthors: Dict[str, List[str]] = dataclasses.field(default_factory=dict)
    timestamp: int = -1
    
    def __post_init__(self):
        if self.name is not None:
            self.name = ADSName.parse(self.name)
        if self.timestamp == -1:
            self.timestamp = int(time.time())
    
    def load_documents(self):
        """Replaces the bibcodes in self.documents with full DocumentRecords"""
        import cache_buddy
        self.documents = cache_buddy.load_documents(self.documents)
    
    def copy(self):
        return AuthorRecord(**self.asdict())
    
    def asdict(self):
        # dataclasses.asdict makes a deep copy and is a bit slow doing it.
        # It's faster to generate our own dict. Everything is either immutable
        # or a list of immutables, so if we just make fresh list instances
        # we still get the deep-copy semantics w/o a speed penalty.
        return {
            'name': self.name,
            'documents': list(self.documents),
            'appears_as': {k: (list(v) if type(v) is list else v)
                           for k, v in self.appears_as.items()},
            'coauthors': {k: (list(v) if type(v) is list else v)
                          for k, v in self.coauthors.items()},
            'timestamp': self.timestamp,
        }
        
    def compress(self):
        """Performs an in-place compression of data.
        
        Useful immediately before caching this record.
        
        For records w/ many documents, the repeated bibcodes in the coauthor
        and appears_as lists dramatically inflate the record's size. This
        replaces those bibcodes in-place with an index into the documents
        lists. That list of indices is further converted to a comma-
        separated string, since that seems favored by the storage use
        accounting in Firestore.
        """
        mapping = {bibcode: str(i) for i, bibcode in enumerate(self.documents)}
        
        for coauthor in self.coauthors:
            self.coauthors[coauthor] = ",".join(
                [mapping[bibcode] for bibcode in self.coauthors[coauthor]])
        for alias in self.appears_as:
            self.appears_as[alias] = ",".join(
                [mapping[bibcode] for bibcode in self.appears_as[alias]])
    
    def decompress(self):
        """Performs in-place the opposite of compress()"""
        mapping = {str(i): bibcode for i, bibcode in enumerate(self.documents)}
        
        for coauthor in self.coauthors:
            self.coauthors[coauthor] = \
                [mapping[idx] for idx in self.coauthors[coauthor].split(",")]
        for alias in self.appears_as:
            self.appears_as[alias] = \
                [mapping[idx] for idx in self.appears_as[alias].split(",")]
