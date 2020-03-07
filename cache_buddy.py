import os
import json

from document_record import DocumentRecord
from author_record import AuthorRecord
from LogBuddy import lb

CACHE_DIR = "cache"
DOC_CACHE_SUBDIR = os.path.join(CACHE_DIR, "documents")
AUTHOR_CACHE_SUBDIR = os.path.join(CACHE_DIR, "authors")


class CacheBuddy:
    def cache_document_data(self, document_record: DocumentRecord):
        os.makedirs(DOC_CACHE_SUBDIR, exist_ok=True)
        fname = os.path.join(DOC_CACHE_SUBDIR, document_record.bibcode)
        with open(fname, "w") as f:
            json.dump(document_record.asdict(), f, check_circular=False)
    
    def document_is_in_cache(self, bibcode):
        fname = os.path.join(DOC_CACHE_SUBDIR, bibcode)
        return os.path.exists(fname)
    
    def load_document_data(self, bibcode, except_on_miss=False):
        fname = os.path.join(DOC_CACHE_SUBDIR, bibcode)
        if not os.path.exists(fname):
            lb.i("Doc cache miss for " + bibcode)
            if except_on_miss:
                raise ValueError
            else:
                return None
        with open(fname) as f:
            try:
                data = json.load(f)
                return DocumentRecord(**data)
            except ValueError:
                lb.e("Error decoding document cache JSON file " + fname)
                return None

    def cache_author_data(self, author_record: AuthorRecord):
        os.makedirs(AUTHOR_CACHE_SUBDIR, exist_ok=True)
        fname = os.path.join(AUTHOR_CACHE_SUBDIR, str(author_record.name))
        
        for doc in author_record.documents:
            self.cache_document_data(doc)
        
        author_record = author_record.copy()
        author_record.documents = [d.bibcode for d in author_record.documents]
        author_record.name = str(author_record.name)
        
        with open(fname, "w") as f:
            json.dump(author_record.asdict(), f, check_circular=False)

    def author_is_in_cache(self, name):
        name = str(name)
        fname = os.path.join(AUTHOR_CACHE_SUBDIR, name)
        return os.path.exists(fname)
    
    def load_author_data(self, name):
        name = str(name)
        fname = os.path.join(AUTHOR_CACHE_SUBDIR, name)
        if not os.path.exists(fname):
            lb.i("Author cache miss for " + name)
            return None
        with open(fname) as f:
            try:
                data = json.load(f)
                author_record = AuthorRecord(**data)
            except ValueError:
                lb.e("Error decoding author cache JSON file " + fname)
                return None
        
        try:
            author_record.documents = [self.load_document_data(d)
                                       for d in author_record.documents]
        except ValueError:
            lb.e("Cache miss in loading author's documents")
            return None
        
        return author_record
