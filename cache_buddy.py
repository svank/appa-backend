import importlib
import time
import traceback

import local_config
# Can't use `from log_buddy import lb` b/c it would be a circular import
import log_buddy
from author_record import AuthorRecord
from document_record import DocumentRecord
from progress_record import ProgressRecord

backing_cache = importlib.import_module(local_config.backing_cache)

# Records older than this will not be loaded
MAXIMUM_AGE = 31 * 24 * 60 * 60  # 1 month in seconds
# Records older than this will be removed by clear_stale_data()
MAXIMUM_AGE_AUTO = MAXIMUM_AGE - 1.1 * 24 * 60 * 60
MAXIMUM_PROGRESS_AGE = 30 * 60  # 30 min in seconds

# Cache data format version numbers
AUTHOR_VERSION_NUMBER = 1
DOCUMENT_VERSION_NUMBER = 1


_loaded_documents = dict()
_loaded_authors = dict()


def refresh():
    now = time.time()
    old = [bibcode
           for bibcode, record in _loaded_documents.items()
           if now - record.timestamp > MAXIMUM_AGE_AUTO]
    with backing_cache.batch():
        for bibcode in old:
            del _loaded_documents[bibcode]
    
    old = [name
           for name, record in _loaded_authors.items()
           if now - record.timestamp > MAXIMUM_AGE_AUTO]
    with backing_cache.batch():
        for name in old:
            del _loaded_authors[name]
    
    backing_cache.refresh()


def key_is_valid(name):
    if name in ('.', '..', ',') or len(name) > 255 or len(name) == 0:
        return False
    if '<' in name and '>' in name:
        return False
    return all(
        (c.isprintable() and c not in """_*/\;:?"|+[{]}()#$%^""" 
         for c in name))


def cache_document(document_record: DocumentRecord):
    if not key_is_valid(document_record.bibcode):
        raise RuntimeError(
            "Invalid bibcode for caching: " + document_record.bibcode)
    _loaded_documents[document_record.bibcode] = document_record
    
    document_record = document_record.copy()
    document_record.compress()
    document_record = document_record.asdict()
    document_record['version'] = DOCUMENT_VERSION_NUMBER
    backing_cache.store_document(document_record, document_record['bibcode'])


def cache_documents(document_records: []):
    with backing_cache.batch():
        for document_record in document_records:
            cache_document(document_record)


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
            t_start = time.time()
            data = backing_cache.load_document(bibcode)
            log_buddy.lb.on_doc_load_timed(time.time() - t_start)
        except ValueError as e:
            log_buddy.lb.e(str(e))
            return None
    
    return _prepare_loaded_document(data)


def load_documents(bibcodes, missing_ok=False):
    """Note: documents are not guaranteed to be returned in the order given"""
    need_to_load = []
    records = []
    for key in bibcodes:
        try:
            records.append(_loaded_documents[key])
        except KeyError:
            need_to_load.append(key)
    if len(need_to_load):
        try:
            t_start = time.time()
            try:
                records.extend(backing_cache.load_documents(need_to_load))
            except CacheMiss:
                if missing_ok:
                    pass
                else:
                    raise
            log_buddy.lb.on_doc_load_timed(time.time() - t_start)
        except ValueError as e:
            log_buddy.lb.e(str(e))
            return None

    records = [_prepare_loaded_document(r) for r in records]
    
    if any([r is None for r in records]):
        if missing_ok:
            records = [r for r in records if r is not None]
        else:
            present = {r.bibcode for r in records if r is not None}
            missing = set(bibcodes) - present
            raise CacheMiss(missing)
    return records


def _prepare_loaded_document(data):
    if type(data) == DocumentRecord:
        record = data
        version = DOCUMENT_VERSION_NUMBER
    elif data is None:
        return None
    else:
        try:
            version = data['version']
            del data['version']
        except KeyError:
            version = -1
        record = DocumentRecord(**data)
        record.decompress()
        _loaded_documents[record.bibcode] = record
    
    if (time.time() - record.timestamp > MAXIMUM_AGE
            or version != DOCUMENT_VERSION_NUMBER):
        delete_document(record.bibcode)
        raise CacheMiss("stale cache data: " + record.bibcode)
    return record


def cache_author(author_record: AuthorRecord):
    cache_key = str(author_record.name)
    if not key_is_valid(cache_key):
        raise RuntimeError("Invalid author name for caching: " + cache_key)
    _loaded_authors[cache_key] = author_record
    
    author_record = author_record.copy()
    author_record.compress()
    author_record.name = author_record.name.original_name
    author_record = author_record.asdict()
    author_record['version'] = AUTHOR_VERSION_NUMBER
    backing_cache.store_author(author_record, cache_key)


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


def authors_are_in_cache(names):
    names = [str(name) for name in names]
    
    # We'll do an out-of-order mix of checking our in-memory cache one-by-one
    # and checking our backing cache in one batch. So here's a name-to-value
    # mapping to ensure we can send back results in the right order
    results_by_name = {}
    
    names_to_query = []
    for name in names:
        if name in _loaded_authors:
            results_by_name[name] = True
        else:
            names_to_query.append(name)
    
    for name, value in zip(names_to_query,
                           backing_cache.authors_are_in_cache(names_to_query)):
        results_by_name[name] = value
    
    return [results_by_name[name] for name in names]


def load_author(cache_key):
    cache_key = str(cache_key)
    try:
        record = _loaded_authors[cache_key]
    except KeyError:
        try:
            t_start = time.time()
            record = backing_cache.load_author(cache_key)
            log_buddy.lb.on_author_load_timed(time.time() - t_start)
        except ValueError as e:
            log_buddy.lb.e(str(e))
            return None
    record = _prepare_loaded_author(record)
    
    return record


def load_authors(cache_keys):
    """Note: records are not guaranteed to be returned in the order given"""
    cache_keys = [str(key) for key in cache_keys]
    need_to_load = []
    records = []
    for key in cache_keys:
        try:
            records.append(_loaded_authors[key])
        except KeyError:
            need_to_load.append(key)
    if len(need_to_load):
        try:
            t_start = time.time()
            records.extend(backing_cache.load_authors(need_to_load))
            log_buddy.lb.on_author_load_timed(time.time() - t_start)
        except ValueError as e:
            log_buddy.lb.e(str(e))
            return None
    
    records = [_prepare_loaded_author(record) for record in records]
    return records


def _prepare_loaded_author(data):
    if type(data) == AuthorRecord:
        record = data
        version = AUTHOR_VERSION_NUMBER
    else:
        try:
            version = data['version']
            del data['version']
        except KeyError:
            version = -1
        record = AuthorRecord(**data)
        record.decompress()
        _loaded_authors[str(record.name)] = record
    
    if (time.time() - record.timestamp > MAXIMUM_AGE
            or version != AUTHOR_VERSION_NUMBER):
        delete_author(str(record.name))
        raise CacheMiss("stale cache data: " + str(record.name))
    
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


def clear_stale_data(**kwargs):
    backing_cache.clear_stale_data(**kwargs)
    refresh()


class CacheMiss(Exception):
    def __init__(self, key):
        log_buddy.lb.d("Cache miss for " + key)
