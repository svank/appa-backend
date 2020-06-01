import difflib
import time
from collections import deque
from html import unescape

import requests

from ads_name import ADSName, InvalidName
from author_record import AuthorRecord
from document_record import DocumentRecord
from local_config import ADS_TOKEN
from log_buddy import lb
from name_aware import NameAwareDict

FIELDS = ['bibcode', 'title', 'author', 'aff', 'doctype',
          'keyword', 'pub', 'date', 'citation_count', 'read_count',
          'orcid_pub', 'orcid_user', 'orcid_other']

# These params control how many authors from the prefetch queue are included
# in each query. Note that the estimated number of papers per author must
# be high to accommodate outliers with many papers---it's more of a control
# parameter than a true estimate. Note also that in testing, I've gotten mixed
# results at different times on whether increasing the number of authors per
# query, especially beyond two or so, offers a true speed advantage or if it
# slows down the query on the ADS side enough that it doesn't help much.
MAXIMUM_RESPONSE_SIZE = 2000
ESTIMATED_DOCUMENTS_PER_AUTHOR = 300


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
        self._filter_invalid_authors(rec)
        return rec
    
    def get_papers_for_author(self, query_author):
        query_author = ADSName.parse(query_author)
        
        query_authors = self._select_authors_to_prefetch()
        if query_author not in query_authors:
            query_authors.append(query_author)
        
        lb.i(f"Querying ADS for author " + query_author)
        if len(query_authors) > 1:
            lb.i(" Also prefetching. Query: " + "; ".join(
                [str(a) for a in query_authors]))
        
        query_strings = []
        for author in query_authors:
            query_string = '"' + author.full_name + '"'
            if author.require_exact_match:
                query_string = "=" + query_string
            query_strings.append(query_string)
        query = " OR ".join(query_strings)
        query = f"author:({query})"
        
        params = {"q": query,
                  "fq": ["doctype:article", "database:astronomy"],
                  "start": 0,
                  "rows": 2000,
                  "fl": ",".join(FIELDS),
                  "sort": "date+asc"}
        
        documents = self._do_query_for_author(params, len(query_authors))
        
        lb.on_author_queried_from_ADS(len(query_authors))
        
        author_records = NameAwareDict()
        for author in query_authors:
            author_records[author] = AuthorRecord(name=author, documents=[])
        # We need to go through all the documents and match them to our
        # author list. This is critically important if we're pre-fetching
        # authors, but it's also important to support the "<" and ">"
        # specificity selectors for author names
        for document in documents:
            matched = False
            names = self._filter_invalid_authors(document)
            for name in names:
                try:
                    author_records[name].documents.append(
                        document.bibcode)
                    matched = True
                except KeyError:
                    pass
            if (not matched and all(not a.require_more_specific
                                    and not a.require_less_specific
                                    for a in query_authors)):
                # See if we can guess which names should have been matched
                guesses = []
                doc_authors = [n.full_name for n in names]
                doc_authors_initialized = \
                    [n.convert_to_initials().full_name for n in names]
                for query_author in query_authors:
                    guess = difflib.get_close_matches(
                        query_author.full_name, doc_authors, n=1, cutoff=0.8)
                    if len(guess):
                        guesses.append(
                            f"{query_author.full_name} -> {guess[0]}")
                    else:
                        # Try again, changing names to use initials throughout
                        guess = difflib.get_close_matches(
                            query_author.convert_to_initials().full_name,
                            doc_authors_initialized,
                            n=1, cutoff=0.7)
                        if len(guess):
                            # Having found a match with initialized names,
                            # report using the full form of each name
                            chosen_doc_author = doc_authors[
                                doc_authors_initialized.index(guess[0])]
                            guesses.append(f"{query_author.full_name}"
                                           f" -> {chosen_doc_author}")
                msg = "ADS Buddy: No matches for " + document.bibcode
                if len(guesses):
                    msg += " . Guesses: " + "; ".join(guesses)
                lb.w(msg)
        
        for author_record in author_records.values():
            # Remove any duplicate document listings
            # Becomes important for papers with _many_ authors, e.g. LIGO
            # papers, which use only initials and so can have duplicate names
            author_record.documents = sorted(set(author_record.documents))
        
        if len(query_authors) == 1:
            return author_records[query_author], documents
        else:
            return author_records, documents
    
    def _do_query_for_author(self, params, n_authors):
        t_start = time.time()
        r = requests.get("https://api.adsabs.harvard.edu/v1/search/query",
                         params=params,
                         headers={"Authorization": f"Bearer {ADS_TOKEN}"},
                         timeout=(6.05, 6 * n_authors))
        t_elapsed = time.time() - t_start
        lb.on_network_complete(t_elapsed)
        if t_elapsed > 2 * n_authors:
            lb.w(f"Long ADS query: {t_elapsed:.2f} s for {params['q']}")
        
        if int(r.headers.get('X-RateLimit-Remaining', 1)) <= 1:
            reset = time.strftime(
                "%Y-%m-%d %H:%M:%S UTC",
                time.gmtime(int(r.headers.get('X-RateLimit-Reset', 0))))
            raise ADSRateLimitError(r.headers.get('X-RateLimit-Limit'), reset)
        
        r_data = r.json()
        if "error" in r_data:
            raise ADSError('ads_error', r_data['error']['msg'])
            
        documents = self._articles_to_records(r_data['response']['docs'])
        
        if r_data['response']['numFound'] > len(documents) + params['start']:
            lb.i(f"Got too many documents in request."
                 f" numFound: {r_data['response']['numFound']}"
                 f" start: {params['start']}"
                 f" docs rec'd: {len(documents)}")
            params['start'] += len(documents)
            documents.extend(self._do_query_for_author(params, n_authors))
            
        return documents
    
    def _articles_to_records(self, articles):
        return [self._article_to_record(art) for art in articles]
    
    def _article_to_record(self, article):
        # Not every ORCID ID field is returned for every document, and not
        # every returned list has an entry for each author
        for key in ('orcid_pub', 'orcid_user', 'orcid_other'):
            if key not in article:
                article[key] = []
            article[key] = ['' if x == '-' else x for x in article[key]]
            article[key] += \
                [''] * (len(article['author']) - len(article[key]))
        
        # Choose one ORCID ID for each author
        orcid_id = []
        orcid_src = []
        for op, ou, oo in zip(article['orcid_pub'],
                              article['orcid_user'],
                              article['orcid_other']):
            if op != '':
                orcid_id.append(op)
                orcid_src.append(1)
            elif ou != '':
                orcid_id.append(ou)
                orcid_src.append(2)
            elif oo != '':
                orcid_id.append(oo)
                orcid_src.append(3)
            else:
                orcid_id.append('')
                orcid_src.append(0)
        
        article['aff'] = ['' if x == '-' else x for x in article['aff']]
        
        return DocumentRecord(
            bibcode=article["bibcode"],
            title=(unescape(article["title"][0])
                   if "title" in article
                   else "[No title given]"),
            authors=[unescape(a) for a in article["author"]],
            affils=[unescape(a) for a in article["aff"]],
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
                        else 0),
            orcid_ids=orcid_id,
            orcid_id_src=orcid_src
        )
    
    def _filter_invalid_authors(self, document):
        """Alters a DocumentRecord in-place to remove invalid author names
        
        Returns a list of the parsed ADSNames for the valid names."""
        bad_indices = []
        names = []
        for i, author in enumerate(document.authors):
            try:
                name = ADSName.parse(author)
            except InvalidName:
                lb.w(f"Invalid name for {document.bibcode}: {author}")
                bad_indices.append(i)
                continue
        
            if name.full_name in ("et al", "anonymous"):
                bad_indices.append(i)
                continue
            
            names.append(name)

        for i in reversed(bad_indices):
            document.delete_author(i)
        
        return names
    
    def add_authors_to_prefetch_queue(self, *authors):
        for author in authors:
            if author in self.prefetch_set:
                continue
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


def is_bibcode(value):
    return (
        len(value) == 19
        and _is_int(value[0:4])
    )


def _is_int(value):
    try:
        int(value)
        return True
    except ValueError:
        return False


class ADSRateLimitError(Exception):
    def __init__(self, limit, reset_time):
        super().__init__(f"ADS daily query quota of {limit} exceeded, reset at {reset_time}")
        self.reset_time = reset_time


class ADSError(RuntimeError):
    def __init__(self, key, message):
        super().__init__(message)
        self.key = key
    
    def __str__(self):
        return "ADS says: " + super().__str__()
