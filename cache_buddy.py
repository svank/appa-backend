import time
import traceback

# Can't use `from log_buddy import lb` b/c it would be a circular import
import log_buddy
from author_record import AuthorRecord
from document_record import DocumentRecord
from local_config import backing_cache
from progress_record import ProgressRecord

MAXIMUM_AGE = 31 * 24 * 60 * 60  # 1 month in seconds
MAXIMUM_PROGRESS_AGE = 30 * 60  # 30 min in seconds


_loaded_documents = dict()
_loaded_authors = dict()


def refresh():
    backing_cache.refresh()


def cache_document(document_record: DocumentRecord):
    backing_cache.store_document(
        document_record.asdict(),
        document_record.bibcode
    )
    _loaded_documents[document_record.bibcode] = document_record


def delete_document(bibcode):
    try:
        backing_cache.delete_document(bibcode)
    except:
        log_buddy.lb.e(
            f"Error deleting cache data for doc "
            f"{bibcode}\n{traceback.format_exc()}")
    if bibcode in _loaded_documents:
        del _loaded_documents[bibcode]


def load_document(bibcode):
    try:
        data = _loaded_documents[bibcode]
    except KeyError:
        try:
            data = backing_cache.load_document(bibcode)
        except ValueError as e:
            log_buddy.lb.e(str(e))
            return None
    
    return _prepare_loaded_document(data)


def load_documents(bibcodes):
    try:
        data = [_loaded_documents[bibcode] for bibcode in bibcodes]
    except KeyError:
        try:
            data = backing_cache.load_documents(bibcodes)
        except ValueError as e:
            log_buddy.lb.e(str(e))
            return None
    
    records = [_prepare_loaded_document(d) for d in data]
    return records


def _prepare_loaded_document(data):
    if type(data) == DocumentRecord:
        record = data
    else:
        record = DocumentRecord(**data)
        _loaded_documents[record.bibcode] = record
    
    if time.time() - record.timestamp > MAXIMUM_AGE:
        delete_document(record.bibcode)
        raise CacheMiss("stale cache data: " + record.bibcode)
    return record


def cache_author(author_record: AuthorRecord):
    with backing_cache.batch():
        for doc in author_record.documents:
            cache_document(doc)
    
        cache_key = str(author_record.name)
        _loaded_authors[cache_key] = author_record
        
        author_record = author_record.copy()
        author_record.documents = [d.bibcode for d in author_record.documents]
        author_record.name = author_record.name.original_name
        backing_cache.store_author(author_record.asdict(), cache_key)


def cache_authors(author_records: []):
    with backing_cache.batch():
        for author_record in author_records:
            cache_author(author_record)


def delete_author(name):
    cache_key = str(name)
    try:
        backing_cache.delete_author(cache_key)
    except:
        log_buddy.lb.e(
            f"Error deleting cache data for author "
            f"{cache_key}\n{traceback.format_exc()}")
    if cache_key in _loaded_authors:
        del _loaded_authors[cache_key]


def author_is_in_cache(name):
    cache_key = str(name)
    return (cache_key in _loaded_authors
            or backing_cache.author_is_in_cache(cache_key))


def load_author(cache_key):
    cache_key = str(cache_key)
    try:
        record = _loaded_authors[cache_key]
    except KeyError:
        try:
            data = backing_cache.load_author(cache_key)
        except ValueError as e:
            log_buddy.lb.e(str(e))
            return None
        record = AuthorRecord(**data)
        record.documents = load_documents(record.documents)
        _loaded_authors[cache_key] = record
    
    if time.time() - record.timestamp > MAXIMUM_AGE:
        delete_author(cache_key)
        raise CacheMiss("stale cache data: " + cache_key)
    
    return record


def cache_progress_data(progress_record: ProgressRecord, key: str):
    backing_cache.store_progress_data(progress_record.asdict(), key)


def delete_progress_data(key: str):
    try:
        backing_cache.delete_progress_data(key)
    except:
        log_buddy.lb.e(
            f"Error deleting cache data for progress "
            f"{key}\n{traceback.format_exc()}")


def load_progress_data(key):
    try:
        data = backing_cache.load_progress_data(key)
    except ValueError as e:
        log_buddy.lb.e(str(e))
        return None
    
    record = ProgressRecord(**data)
    
    if time.time() - record.timestamp > MAXIMUM_PROGRESS_AGE:
        delete_progress_data(key)
        raise CacheMiss("stale cache data: " + key)
    
    return record


class CacheMiss(Exception):
    def __init__(self, key):
        log_buddy.lb.i("Cache miss for " + key)
