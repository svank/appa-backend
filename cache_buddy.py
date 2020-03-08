import json

import cache_fs as backing_cache
from LogBuddy import lb
from author_record import AuthorRecord
from document_record import DocumentRecord


def cache_document_data(document_record: DocumentRecord):
    backing_cache.store_document_data(
        json.dumps(document_record.asdict(), check_circular=False),
        document_record.bibcode
    )


def document_is_in_cache(bibcode):
    return backing_cache.document_is_in_cache(bibcode)


def load_document_data(bibcode, except_on_miss=False):
    raw_data = backing_cache.load_document_data(bibcode)
    if raw_data is None:
        lb.i("Doc cache miss for " + bibcode)
        if except_on_miss:
            raise ValueError
        else:
            return None
    try:
        data = json.loads(raw_data)
        return DocumentRecord(**data)
    except ValueError:
        lb.e("Error decoding document cache JSON data " + bibcode)
        return None


def cache_author_data(author_record: AuthorRecord):
    for doc in author_record.documents:
        cache_document_data(doc)
    
    author_record = author_record.copy()
    author_record.documents = [d.bibcode for d in author_record.documents]
    author_record.name = str(author_record.name)
    
    backing_cache.store_author_data(
        json.dumps(author_record.asdict(), check_circular=False),
        author_record.name
    )


def author_is_in_cache(name):
    return backing_cache.author_is_in_cache(str(name))


def load_author_data(name):
    raw_data = backing_cache.load_author_data(str(name))
    if raw_data is None:
        lb.i("Author cache miss for " + name)
        return None
    try:
        data = json.loads(raw_data)
        author_record = AuthorRecord(**data)
    except ValueError:
        lb.e("Error decoding author cache JSON data " + name)
        return None
    
    try:
        author_record.documents = [load_document_data(d)
                                   for d in author_record.documents]
    except ValueError:
        lb.e("Cache miss in loading author's documents")
        return None
    
    return author_record
