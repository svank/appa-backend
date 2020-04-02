import json
import time
import traceback

import cache_fs as backing_cache
# Can't use `from log_buddy import lb` b/c it would be a circular import
import log_buddy
from author_record import AuthorRecord
from document_record import DocumentRecord
from progress_record import ProgressRecord

MAXIMUM_AGE = 31 * 24 * 60 * 60  # 1 month in seconds
MAXIMUM_PROGRESS_AGE = 30 * 60  # 30 min in seconds


def cache_document_data(document_record: DocumentRecord):
    backing_cache.store_document_data(
        json.dumps(document_record.asdict(), check_circular=False),
        document_record.bibcode
    )


def delete_document_data(bibcode):
    try:
        backing_cache.delete_document_data(bibcode)
    except:
        log_buddy.lb.e(
            f"Error deleting cache data for doc "
            f"{bibcode}\n{traceback.format_exc()}")


def document_is_in_cache(bibcode):
    return backing_cache.document_is_in_cache(bibcode)


def load_document_data(bibcode):
    raw_data = backing_cache.load_document_data(bibcode)
    
    try:
        data = json.loads(raw_data)
        record = DocumentRecord(**data)
    except ValueError:
        log_buddy.lb.e("Error decoding document cache JSON data " + bibcode)
        return None
    
    if time.time() - record.timestamp > MAXIMUM_AGE:
        backing_cache.delete_document_data(bibcode)
        raise CacheMiss("stale cache data: " + bibcode)
    return record


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


def delete_author_data(name):
    try:
        backing_cache.delete_author_data(str(name))
    except:
        log_buddy.lb.e(
            f"Error deleting cache data for author "
            f"{str(name)}\n{traceback.format_exc()}")


def author_is_in_cache(name):
    return backing_cache.author_is_in_cache(str(name))


def load_author_data(name):
    name = str(name)
    raw_data = backing_cache.load_author_data(name)
    
    try:
        data = json.loads(raw_data)
        author_record = AuthorRecord(**data)
    except ValueError:
        log_buddy.lb.e("Error decoding author cache JSON data " + name)
        return None
    
    if time.time() - author_record.timestamp > MAXIMUM_AGE:
        backing_cache.delete_author_data(name)
        raise CacheMiss("stale cache data: " + name)
    
    author_record.documents = [load_document_data(d)
                               for d in author_record.documents]
    
    return author_record


def cache_progress_data(progress_record: ProgressRecord, key: str):
    backing_cache.store_progress_data(
        json.dumps(progress_record.asdict(), check_circular=False),
        key
    )


def delete_progress_data(key: str):
    try:
        backing_cache.delete_progress_data(key)
    except:
        log_buddy.lb.e(
            f"Error deleting cache data for progress "
            f"{key}\n{traceback.format_exc()}")


def load_progress_data(key):
    raw_data = backing_cache.load_progress_data(key)
    
    try:
        data = json.loads(raw_data)
        record = ProgressRecord(**data)
    except ValueError:
        log_buddy.lb.e("Error decoding progress cache JSON data " + key)
        return None
    
    if time.time() - record.timestamp > MAXIMUM_PROGRESS_AGE:
        backing_cache.delete_progress_data(key)
        raise CacheMiss("stale cache data: " + key)
    
    return record


class CacheMiss(Exception):
    def __init__(self, key):
        log_buddy.lb.i("Cache miss for " + key)
