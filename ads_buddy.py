import time
from collections import deque
from html import unescape

import requests

from ads_access import ADS_TOKEN
from ads_name import ADSName
from author_record import AuthorRecord
from document_record import DocumentRecord
from log_buddy import lb
from name_aware import NameAwareDict

FIELDS = ['bibcode', 'title', 'author', 'aff', 'doi', 'doctype',
          'keyword', 'pub', 'date', 'citation_count', 'read_count']

# These params control how many authors from the prefetch queue are included
# in each query. Note that the estimated number of papers per author must
# be high to accomodate outliers with many papers. Note also that in testing,
# it seems that increasing the number of authors per query, especially beyond
# two or so, slows down the query on the ADS side and so has mixed results in
# terms of speeding up the total time spent waiting on the network.
MAXIMUM_RESPONSE_SIZE = 2000
ESTIMATED_DOCUMENTS_PER_AUTHOR = 600


class ADS_Buddy:
    prefetch_queue: deque
    prefetch_set: set
    
    def __init__(self):
        self.prefetch_queue = deque()
        self.prefetch_set = set()
    
    def get_document(self, bibcode):
        lb.i("Querying ADS for bibcode " + bibcode)
        t_start = time.time()
        
        params = {"q": "bibcode:" + bibcode,
                  "fl": ",".join(FIELDS)}
        r = requests.get("https://api.adsabs.harvard.edu/v1/search/query",
                         params=params,
                         headers={"Authorization": f"Bearer {ADS_TOKEN}"})
        t_stop = time.time()
        lb.on_network_complete(t_stop - t_start)
        
        rec = self._article_to_record(r.json()['response']['docs'][0])
        return rec
    
    def get_papers_for_author(self, query_author):
        query_author = ADSName.parse(query_author)
        
        authors = self._select_authors_to_prefetch()
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
        
        params = {"q": query,
                  "fq": ["doctype:article", "database:astronomy"],
                  "rows": 2000,
                  "fl": ",".join(FIELDS)}
        r = requests.get("https://api.adsabs.harvard.edu/v1/search/query",
                         params=params,
                         headers={"Authorization": f"Bearer {ADS_TOKEN}"})
        t_stop = time.time()

        response_data = r.json()
        if response_data['response']['numFound'] > 2000:
            # TODO: Handle this
            lb.e(f"Too many ({response_data['response']['numFound']}) documents found for {authors}")
        
        documents = self._articles_to_records(response_data['response']['docs'])
        
        lb.on_network_complete(t_stop - t_start)
        if (t_stop - t_start) > 2:
            lb.w(f"Long ADS query: {t_stop-t_start:.2f} s for {authors}")
        
        author_records = NameAwareDict()
        for author in authors:
            author_records[author] = AuthorRecord(name=author, documents=[])
        # We need to go through all the documents and match them to our
        # author list. This is critically important if we're pre-fetching
        # authors, but it's also important to support the "<" and ">"
        # specificity selectors for author names
        for document in documents:
            for author in document.authors:
                if author in author_records:
                    author_records[author].documents.append(document)
        
        if len(authors) == 1:
            return author_records[query_author]
        else:
            return author_records
    
    def _articles_to_records(self, articles):
        return [self._article_to_record(art) for art in articles]
    
    def _article_to_record(self, article):
        return DocumentRecord(
            bibcode=article["bibcode"],
            title=(unescape(article["title"][0])
                   if "title" in article
                   else "[No title given]"),
            authors=[unescape(a) for a in article["author"]],
            affils=[unescape(a) for a in article["aff"]],
            doi=article["doi"][0] if "doi" in article else None,
            doctype=article["doctype"],
            keywords=([unescape(k) for k in article["keyword"]]
                      if "keyword" in article
                      else []),
            publication=(unescape(article["pub"])
                         if "pub" in article
                         else "[Publication not given]"),
            pubdate=article["date"],
            citation_count=(article["citation_count"]
                            if "citation_count" in article
                            else 0),
            read_count=(article["read_count"]
                        if "read_count" in article
                        else 0)
        )
    
    def add_author_to_prefetch_queue(self, author):
        if author in self.prefetch_set:
            return
        self.prefetch_set.add(author)
        self.prefetch_queue.append(author)
    
    def _select_authors_to_prefetch(self):
        lb.d(f"{len(self.prefetch_queue)} authors in prefetch queue")
        n_prefetches = MAXIMUM_RESPONSE_SIZE // ESTIMATED_DOCUMENTS_PER_AUTHOR - 1
        if n_prefetches > len(self.prefetch_queue):
            n_prefetches = len(self.prefetch_queue)
        if n_prefetches <= 0:
            return []
        prefetches = []
        for _ in range(n_prefetches):
            name = self.prefetch_queue.popleft()
            self.prefetch_set.remove(name)
            prefetches.append(ADSName.parse(name))
        return prefetches
