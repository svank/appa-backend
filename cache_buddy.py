import json

import cache_fs as backing_cache
# Can't use `from log_buddy import lb` b/c it would be a circular import
import log_buddy
from author_record import AuthorRecord
from document_record import DocumentRecord
from progress_record import ProgressRecord


def cache_document_data(document_record: DocumentRecord):
    backing_cache.store_document_data(
        json.dumps(document_record.asdict(), check_circular=False),
        document_record.bibcode
    )


def document_is_in_cache(bibcode):
    return backing_cache.document_is_in_cache(bibcode)


def load_document_data(bibcode):
    raw_data = backing_cache.load_document_data(bibcode)
    
    try:
        data = json.loads(raw_data)
        return DocumentRecord(**data)
    except ValueError:
        log_buddy.lb.e("Error decoding document cache JSON data " + bibcode)
        return None


def cache_author_data(author_record: AuthorRecord):
    for doc in author_record.documents:
        cache_document_data(doc)
    
    author_record = author_record.copy()
    author_record.documents = [d.bibcode for d in author_record.documents]
    cache_key = str(author_record.name)
    author_record.name = author_record.name.original_name
    
    backing_cache.store_author_data(
        json.dumps(author_record.asdict(), check_circular=False),
        cache_key
    )


def author_is_in_cache(name):
    return backing_cache.author_is_in_cache(str(name))


def load_author_data(name):
    raw_data = backing_cache.load_author_data(str(name))
    
    try:
        data = json.loads(raw_data)
        author_record = AuthorRecord(**data)
    except ValueError:
        log_buddy.lb.e("Error decoding author cache JSON data " + name)
        return None
    
    author_record.documents = [load_document_data(d)
                               for d in author_record.documents]
    
    return author_record


def cache_progress_data(progress_record: ProgressRecord, key: str):
    backing_cache.store_progress_data(
        json.dumps(progress_record.asdict(), check_circular=False),
        key
    )


def load_progress_data(key):
    raw_data = backing_cache.load_progress_data(key)
    
    try:
        data = json.loads(raw_data)
        return ProgressRecord(**data)
    except ValueError:
        log_buddy.lb.e("Error decoding progress cache JSON data " + key)
        return None


class CacheMiss(Exception):
    def __init__(self, key):
        log_buddy.lb.i("Cache miss for " + key)
