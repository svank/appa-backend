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
    
    def delete_author(self, i):
        del self.authors[i]
        del self.affils[i]
        del self.orcid_ids[i]
        del self.orcid_id_src[i]
    
    def copy(self):
        return DocumentRecord(**self.asdict())
    
    def asdict(self):
        # dataclasses.asdict makes a deep copy and is a bit slow doing it.
        # It's faster to generate our own dict. Everything is either immutable
        # or a list of immutables, so if we just make fresh list instances
        # we still get the deep-copy semantics w/o a speed penalty.
        return {
            'bibcode': self.bibcode,
            'title': self.title,
            'authors': list(self.authors),
            'affils': list(self.affils),
            'doctype': self.doctype,
            'keywords': list(self.keywords),
            'publication': self.publication,
            'pubdate': self.pubdate,
            'citation_count': self.citation_count,
            'read_count': self.read_count,
            'orcid_ids': list(self.orcid_ids),
            'orcid_id_src': (self.orcid_id_src
                             if type(self.orcid_id_src) == str
                             else list(self.orcid_id_src)),
            'timestamp': self.timestamp,
        }

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
        # In Firestore, integers cost us 8 bytes, while each character in a
        # string costs us only 1 byte. So convert this list of ints to a
        # string
        self.orcid_id_src = ','.join(str(c) for c in self.orcid_id_src)

    def decompress(self):
        """Performs in-place the opposite of compress()"""
        if len(self.orcid_id_src):
            self.orcid_id_src = [int(c) for c in self.orcid_id_src.split(',')]
        else:
            # .split() on an empty string returns [''], but we want []
            self.orcid_id_src = []
        
        self.affils += [''] * (len(self.authors) - len(self.affils))
        self.orcid_ids += [''] * (len(self.authors) - len(self.orcid_ids))
        self.orcid_id_src += [0] * (len(self.authors) - len(self.orcid_id_src))
