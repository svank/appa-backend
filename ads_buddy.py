import time
from collections import deque

from ads_access import ads

from document_record import DocumentRecord
from author_record import AuthorRecord
from LogBuddy import lb
from ads_name import ADSName
from name_aware import NameAwareDict

FIELDS = ['bibcode', 'title', 'author', 'aff', 'doi', 'doctype',
          'keyword', 'pub', 'date', 'citation_count', 'read_count']
MAXIMUM_RESPONSE_SIZE = 2000
ESTIMATED_PAPERS_PER_AUTHOR = 150


class ADS_Buddy:
    prefetch_queue: deque
    prefetch_set: set
    
    def __init__(self):
        self.prefetch_queue = deque()
        self.prefetch_set = set()
    
    def get_document(self, bibcode):
        lb.i("Querying ADS for bibcode " + bibcode)
        t_start = time.time()
        q = ads.SearchQuery(bibcode=bibcode, fl=FIELDS)
        rec = self.article_to_record(q[0])
        t_stop = time.time()
        lb.on_network_complete(t_stop - t_start)
        return rec
    
    def get_papers_for_author(self, query_author):
        if type(query_author) == str:
            query_author = ADSName(query_author)
        
        authors = self.select_authors_to_prefetch()
        if query_author not in authors:
            authors.append(query_author)
        
        lb.i(f"Querying ADS for author " + query_author)
        if len(authors) > 1:
            lb.i(f"Also prefetching {len(authors) - 1} others")
            lb.d(" Prefetching " + str(authors))
        
        query_strings = []
        for author in authors:
            query_string = '"' + author.full_name + '"'
            if author.exact:
                query_string = "=" + query_string
            query_strings.append(query_string)
        query = " OR ".join(query_strings)
        query = f"author:({query})"
        
        t_start = time.time()
        
        q = ads.SearchQuery(q=query, fl=FIELDS,
                            doctype="article", database="astronomy", rows=2000)
        documents = self.articles_to_records(q)
        
        t_stop = time.time()
        lb.on_network_complete(t_stop - t_start)
        
        author_records = NameAwareDict()
        for author in authors:
            author_records[author] = AuthorRecord(name=author, documents=[])
        for document in documents:
            for author in document.authors:
                if author in author_records:
                    author_records[author].documents.append(document)
        
        if len(authors) == 1:
            return author_records[query_author]
        else:
            return author_records
    
    def articles_to_records(self, articles):
        return [self.article_to_record(art) for art in articles]
    
    def article_to_record(self, article):
        return DocumentRecord(
            bibcode=article.bibcode,
            title=article.title[0],
            authors=article.author,
            affils=article.aff,
            doi=article.doi[0] if article.doi is not None else None,
            doctype=article.doctype,
            keywords=article.keyword,
            publication=article.pub,
            pubdate=article.date,
            citation_count=article.citation_count,
            read_count=article.read_count
        )
    
    def add_author_to_prefetch_queue(self, author):
        if author in self.prefetch_set:
            return
        self.prefetch_set.add(author)
        self.prefetch_queue.append(author)
    
    def select_authors_to_prefetch(self):
        lb.d(f"{len(self.prefetch_queue)} authors in prefetch queue")
        n_prefetches = MAXIMUM_RESPONSE_SIZE // ESTIMATED_PAPERS_PER_AUTHOR - 1
        if n_prefetches > len(self.prefetch_queue):
            n_prefetches = len(self.prefetch_queue)
        if n_prefetches <= 0:
            return []
        prefetches = []
        for _ in range(n_prefetches):
            name = self.prefetch_queue.popleft()
            self.prefetch_set.remove(name)
            prefetches.append(ADSName(name))
        return prefetches
