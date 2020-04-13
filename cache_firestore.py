import json
import time

from google.cloud import firestore

import cache_buddy

DOC_CACHE_COLLECTION = "documents"
AUTHOR_CACHE_COLLECTION = "authors"
PROGRESS_CACHE_COLLECTION = "progress"
AUTHOR_CACHE_MAX_AGE = 540  # seconds
_author_cache_contents = set()
_author_cache_contents_timestamp = 0

db = firestore.Client()
_batch = None
_batch_size = 0
_batch_bytes = 0

# A batch can contain 500 operations
MAX_OPS = 500
# An API call can max out at 10 MiB. I don't know how to account for overhead
# on each request, so use a conservative 8 MiB
MAX_API_CALL_SIZE = 8 * 1024 * 1024


def refresh():
    global _author_cache_contents, _author_cache_contents_timestamp
    _author_cache_contents = {
        doc.id
        for doc in db.collection(AUTHOR_CACHE_COLLECTION).list_documents()
    }
    _author_cache_contents_timestamp = time.time()


def store_document(data: dict, key: str):
    doc_ref = db.collection(DOC_CACHE_COLLECTION).document(key)
    _set(doc_ref, data)


def delete_document(key: str):
    doc_ref = db.collection(DOC_CACHE_COLLECTION).document(key)
    _delete(doc_ref)


def load_document(key: str):
    doc_ref = db.collection(DOC_CACHE_COLLECTION).document(key)
    data = doc_ref.get()
    if data.exists:
        return data.to_dict()
    raise cache_buddy.CacheMiss(key)


def load_documents(keys: []):
    docs = db.get_all(
        [db.collection(DOC_CACHE_COLLECTION).document(key) for key in keys]
    )
    return [doc.to_dict() for doc in docs]


def store_author(data: dict, key: str):
    doc_ref = db.collection(AUTHOR_CACHE_COLLECTION).document(key)
    _set(doc_ref, data)
    _author_cache_contents.add(key)


def delete_author(key: str):
    doc_ref = db.collection(AUTHOR_CACHE_COLLECTION).document(key)
    _delete(doc_ref)
    try:
        _author_cache_contents.remove(key)
    except KeyError:
        pass


def author_is_in_cache(key):
    if time.time() - _author_cache_contents_timestamp > AUTHOR_CACHE_MAX_AGE:
        refresh()
    return key in _author_cache_contents


def load_author(key: str):
    if not author_is_in_cache(key):
        raise cache_buddy.CacheMiss(key)
    
    doc_ref = db.collection(AUTHOR_CACHE_COLLECTION).document(key)
    data = doc_ref.get()
    if data.exists:
        return data.to_dict()
    else:
        if key in _author_cache_contents:
            refresh()
        raise cache_buddy.CacheMiss(key)


def load_authors(keys: [str]):
    not_in_cache = [key for key in keys if not author_is_in_cache(key)]
    if len(not_in_cache):
        raise cache_buddy.CacheMiss(not_in_cache)
    
    doc_refs = [db.collection(AUTHOR_CACHE_COLLECTION).document(key)
                for key in keys]
    data = db.get_all(doc_refs)
    dicts = []
    for datum in data:
        if not datum.exists:
            refresh()
            raise cache_buddy.CacheMiss(datum.id)
        dicts.append(datum.to_dict())
    return dicts


def store_progress_data(data: str, key: str):
    doc_ref = db.collection(PROGRESS_CACHE_COLLECTION).document(key)
    _set(doc_ref, data)


def delete_progress_data(key: str):
    doc_ref = db.collection(PROGRESS_CACHE_COLLECTION).document(key)
    _delete(doc_ref)


def get_progress_cache_contents():
    return db.collection(PROGRESS_CACHE_COLLECTION).list_documents()


def load_progress_data(key: str):
    doc_ref = db.collection(PROGRESS_CACHE_COLLECTION).document(key)
    data = doc_ref.get()
    if data.exists:
        return data.to_dict()
    raise cache_buddy.CacheMiss(key)


def clear_stale_data():
    with batch():
        doc_thresh = time.time() - cache_buddy.MAXIMUM_AGE_AUTO
        doc_collection = db.collection(DOC_CACHE_COLLECTION)
        doc_query = doc_collection.where('timestamp', '<', doc_thresh)
        for doc in doc_query.stream():
            _delete(doc_collection.document(doc.id))
        
        author_thresh = time.time() - cache_buddy.MAXIMUM_AGE_AUTO
        author_collection = db.collection(AUTHOR_CACHE_COLLECTION)
        author_query = author_collection.where('timestamp', '<', author_thresh)
        for doc in author_query.stream():
            _delete(author_collection.document(doc.id))
        
        progress_thresh = time.time() - cache_buddy.MAXIMUM_PROGRESS_AGE
        progress_collection = db.collection(PROGRESS_CACHE_COLLECTION)
        progress_query = progress_collection.where('timestamp', '<', progress_thresh)
        for doc in progress_query.stream():
            _delete(progress_collection.document(doc.id))


def _set(doc_ref, data):
    global _batch, _batch_size, _batch_bytes
    if _batch is None:
        doc_ref.set(data)
    else:
        _batch.set(doc_ref, data)
        _batch_size += 1
        _batch_bytes += len(json.dumps(data).encode('utf-8'))
        if _batch_size >= MAX_OPS or _batch_bytes > MAX_API_CALL_SIZE:
            _batch.commit()
            _batch = db.batch()
            _batch_size = 0
            _batch_bytes = 0


def _delete(doc_ref):
    global _batch, _batch_size, _batch_bytes
    if _batch is None:
        doc_ref.delete()
    else:
        _batch.delete(doc_ref)
        _batch_size += 1
        _batch_bytes += 400  # NO idea what to put here
        if _batch_size >= MAX_OPS or _batch_bytes > MAX_API_CALL_SIZE:
            _batch.commit()
            _batch = db.batch()
            _batch_size = 0


class BatchManager:
    def __enter__(self):
        global _batch, _batch_size, _batch_bytes
        self.is_managing = _batch is None
        if self.is_managing:
            _batch = db.batch()
            _batch_size = 0
            _batch_bytes = 0
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        global _batch, _batch_size, _batch_bytes
        if exc_type is not None:
            return False
        if self.is_managing:
            if _batch is not None and _batch_size > 0:
                _batch.commit()
            _batch = None
            _batch_size = 0
            _batch_bytes = 0


def batch():
    return BatchManager()
