from collections import defaultdict
from typing import Union

from cache import cache_buddy

from ads_buddy import ADS_Buddy
from cache.cache_buddy import CacheMiss
from log_buddy import lb
from names.ads_name import ADSName
from records.author_record import AuthorRecord
from records.document_record import DocumentRecord

Name = Union[str, ADSName]


class Repository:
    ads_buddy = ADS_Buddy()
    
    def __init__(self, can_skip_refresh=False):
        if not can_skip_refresh:
            cache_buddy.refresh()
    
    def get_author_record(self, author: Name) -> AuthorRecord:
        author = ADSName.parse(author)
        try:
            author_record = cache_buddy.load_author(author)
        except CacheMiss:
            author_record = self._try_generating_author_record(author)
            if author_record is None:
                author_record, documents = \
                    self.ads_buddy.get_papers_for_author(author)
                cache_buddy.cache_documents(documents)
                if type(author_record) == AuthorRecord:
                    self._fill_in_coauthors(author_record)
                    if len(author_record.documents):
                        cache_buddy.cache_author(author_record)
                else:
                    for rec in author_record.values():
                        self._fill_in_coauthors(rec)
                    cache_buddy.cache_authors(
                        [ar for ar in author_record.values()
                            if len(ar.documents)])
                    author_record = author_record[author]
        lb.on_author_queried()
        lb.on_doc_queried(len(author_record.documents))
        return author_record
    
    def get_author_record_by_orcid_id(self, orcid_id: str) -> AuthorRecord:
        try:
            author_record = cache_buddy.load_author(orcid_id)
        except CacheMiss:
            author_record, documents = \
                self.ads_buddy.get_papers_for_orcid_id(orcid_id)
            cache_buddy.cache_documents(documents)
            self._fill_in_coauthors(author_record)
            if len(author_record.documents):
                cache_buddy.cache_author(author_record, cache_key=orcid_id)
        lb.on_author_queried()
        lb.on_doc_queried(len(author_record.documents))
        return author_record
    
    def get_document(self, bibcode) -> DocumentRecord:
        try:
            document_record = cache_buddy.load_document(bibcode)
        except CacheMiss:
            document_record = self.ads_buddy.get_document(bibcode)
            cache_buddy.cache_document(document_record)
        return document_record
    
    def notify_of_upcoming_author_request(self, *authors):
        authors = [ADSName.parse(author) for author in authors]
        # If appropriate, the backing cache will pre-fetch the data while
        # checking if it exists
        is_in_cache = cache_buddy.authors_are_in_cache(authors)
        authors = [a for a, iic in zip(authors, is_in_cache) if not iic]
        
        can_generate = self._can_generate_author_requests(authors)
        authors = [a for a, cg in zip(authors, can_generate) if not cg]
        
        self.ads_buddy.add_authors_to_prefetch_queue(*authors)
    
    def notify_of_upcoming_document_request(self, *documents):
        # It's very unlikely that we'll ever load a document not already in
        # the cache, so this is just a matter of warming the cache in one bulk
        # load
        try:
            cache_buddy.load_documents(documents, missing_ok=True)
        except cache_buddy.CacheMiss:
            pass
    
    def _fill_in_coauthors(self, author_record: AuthorRecord):
        coauthors = defaultdict(set)
        appears_as = defaultdict(set)
        for document in cache_buddy.load_documents(author_record.documents):
            for coauthor in document.authors:
                if coauthor == author_record.name:
                    appears_as[coauthor].add(document.bibcode)
                else:
                    coauthors[coauthor].add(document.bibcode)
        
        # defaultdict doesn't play nicely with dataclasses' asdict(),
        # so convert to normal dicts. Also convert sets to (sorted) lists
        author_record.coauthors = {
            k: sorted(v) for k, v in coauthors.items()
        }
        author_record.appears_as = {
            k: sorted(v) for k, v in appears_as.items()
        }
    
    def _try_generating_author_record(self, author: ADSName):
        """Generate a requested record from existing cache data
        
        E.g. If "=Doe, J." is searched for and "Doe, J." is already cached,
        we can generate the requested record without going to ADS."""
        
        if not (author.require_exact_match
                or author.require_more_specific
                or author.require_less_specific):
            # This author does not have a modifier character in front
            return None
        
        selected_documents = []
        try:
            author_record = cache_buddy.load_author(author.full_name)
        except CacheMiss:
            return None
        
        try:
            documents = cache_buddy.load_documents(author_record.documents)
        except CacheMiss:
            return None
        # TODO: This can be done with author_record.appears_as
        for doc in documents:
            for coauthor in doc.authors:
                if coauthor == author:
                    selected_documents.append(doc.bibcode)
                    break

        new_author_record = AuthorRecord(name=author,
                                         documents=selected_documents)
        self._fill_in_coauthors(new_author_record)
        
        cache_buddy.cache_author(new_author_record)
        
        lb.i(f"Author record for {str(author)} constructed from cache")
        return new_author_record
    
    def _can_generate_author_requests(self, authors: [ADSName]):
        full_names = [author.full_name for author in authors]
        cache_eligibility = cache_buddy.authors_are_in_cache(full_names)
        # Check if the given author has limited equality and the
        # author's full record is in the cache
        return [
            in_cache
            and (author.require_exact_match
                 or author.require_more_specific
                 or author.require_less_specific)
            for in_cache, author in zip(cache_eligibility, authors)
        ]
