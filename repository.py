from typing import Union

from cache_buddy import CacheBuddy
from ads_buddy import ADS_Buddy
from LogBuddy import lb
from author_record import AuthorRecord
from document_record import DocumentRecord
from ads_name import ADSName

Name = Union[str, ADSName]


class Repository:
    cache_buddy = CacheBuddy()
    ads_buddy = ADS_Buddy()
    
    def get_author_record(self, author: Name) -> AuthorRecord:
        if type(author) == str:
            author = ADSName(author)
        author_record = self.cache_buddy.load_author_data(author)
        if author_record is None:
            author_record = self.ads_buddy.get_papers_for_author(author)
            if type(author_record) == AuthorRecord:
                self.cache_buddy.cache_author_data(author_record)
            else:
                for record_author in author_record:
                    self.cache_buddy.cache_author_data(
                        author_record[record_author])
                author_record = author_record[author]
        lb.on_author_queried()
        lb.on_doc_loaded(len(author_record.documents))
        return author_record
    
    def get_document(self, bibcode) -> DocumentRecord:
        document_record = self.cache_buddy.load_document_data(bibcode)
        if document_record is None:
            document_record = self.ads_buddy.get_document(bibcode)
            self.cache_buddy.cache_document_data(document_record)
        return document_record
    
    def notify_of_upcoming_author_request(self, *authors):
        for author in authors:
            if not self.cache_buddy.author_is_in_cache(author):
                self.ads_buddy.notify_of_upcoming_author_request(author)
