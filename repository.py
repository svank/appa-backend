from typing import Union

import cache_buddy
from LogBuddy import lb
from ads_buddy import ADS_Buddy
from ads_name import ADSName
from author_record import AuthorRecord
from document_record import DocumentRecord

Name = Union[str, ADSName]


class Repository:
    ads_buddy = ADS_Buddy()
    
    def get_author_record(self, author: Name) -> AuthorRecord:
        if type(author) == str:
            author = ADSName(author)
        author_record = cache_buddy.load_author_data(author)
        if author_record is None:
            author_record = self.try_generating_author_record(author)
            if author_record is None:
                author_record = self.ads_buddy.get_papers_for_author(author)
                if type(author_record) == AuthorRecord:
                    cache_buddy.cache_author_data(author_record)
                else:
                    for record_author in author_record:
                        cache_buddy.cache_author_data(
                            author_record[record_author])
                    author_record = author_record[author]
        lb.on_author_queried()
        lb.on_doc_loaded(len(author_record.documents))
        return author_record
    
    def get_document(self, bibcode) -> DocumentRecord:
        document_record = cache_buddy.load_document_data(bibcode)
        if document_record is None:
            document_record = self.ads_buddy.get_document(bibcode)
            cache_buddy.cache_document_data(document_record)
        return document_record
    
    def notify_of_upcoming_author_request(self, *authors):
        for author in authors:
            if not cache_buddy.author_is_in_cache(author):
                self.ads_buddy.add_author_to_prefetch_queue(author)
    
    def try_generating_author_record(self, author: ADSName):
        if not (author.exact
                or author.exclude_more_specific
                or author.exclude_less_specific):
            return None
        
        author_record = cache_buddy.load_author_data(author.full_name)
        if author_record is None:
            return None
        
        selected_documents = []
        
        for doc in author_record.documents:
            for coauthor in doc.authors:
                if coauthor == author:
                    selected_documents.append(doc)
                    break

        new_author_record = AuthorRecord(name=author,
                                         documents=selected_documents)
        cache_buddy.cache_author_data(new_author_record)
        
        lb.i(f"Author record for {str(author)} constructed from cache")
        return new_author_record
