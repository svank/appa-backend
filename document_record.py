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
    orcid_ids: List[str]
    orcid_id_src: List[int]
    timestamp: int = -1
    
    def __post_init__(self):
        if self.timestamp == -1:
            self.timestamp = int(time.time())
    
    def copy(self):
        return DocumentRecord(**self.asdict())
    
    def asdict(self):
        return dataclasses.asdict(self)

    def compress(self):
        """Performs an in-place compression of data.

        Useful immediately before caching this record.

        In the affiliation and ORCID ID lists, empty elements after the last
        non-empty element are dropped
        """
        valid_affil = [x != '' for x in self.affils]
        try:
            cut_start = len(valid_affil) - valid_affil[::-1].index(True)
            self.affils = self.affils[:cut_start]
        except ValueError:
            # There is no valid affiliation
            self.affils = []
        
        valid_orcid = [x != '' for x in self.orcid_ids]
        try:
            cut_start = len(valid_orcid) - valid_orcid[::-1].index(True)
            self.orcid_ids = self.orcid_ids[:cut_start]
            self.orcid_id_src = self.orcid_id_src[:cut_start]
        except ValueError:
            # There is no valid orcid id
            self.orcid_ids = []
            self.orcid_id_src = []

    def decompress(self):
        """Performs in-place the opposite of compress()"""
        self.affils += [''] * (len(self.authors) - len(self.affils))
        self.orcid_ids += [''] * (len(self.authors) - len(self.orcid_ids))
        self.orcid_id_src += [0] * (len(self.authors) - len(self.orcid_id_src))
