import json
import time

from google.cloud import firestore

import cache_buddy

DOC_CACHE_COLLECTION = "documents"
AUTHOR_CACHE_COLLECTION = "authors"
PROGRESS_CACHE_COLLECTION = "progress"

db = firestore.Client()
_batch = None
_batch_size = 0
_batch_bytes = 0

# When we check if an author exists, that involves retrieving the entire
# record. So here we'll store those record contents for any later reads.
_author_data_cache = {}

# A batch can contain 500 operations
MAX_OPS = 500
# An API call can max out at 10 MiB. I don't know how to account for overhead
# on each request, so use a conservative 8 MiB
MAX_API_CALL_SIZE = 8 * 1024 * 1024


def refresh():
    global _author_data_cache
    _author_data_cache = {}


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


def delete_author(key: str):
    doc_ref = db.collection(AUTHOR_CACHE_COLLECTION).document(key)
    _delete(doc_ref)


def author_is_in_cache(key):
    data = db.collection(AUTHOR_CACHE_COLLECTION).document(key).get()
    if data.exists:
        _author_data_cache[data.id] = data
        return True
    else:
        return False


def authors_are_in_cache(keys):
    doc_refs = [db.collection(AUTHOR_CACHE_COLLECTION).document(key)
                for key in keys]
    # get_all does not promise to return documents in the order they were given
    docs = {doc.id: doc for doc in db.get_all(doc_refs)}
    result = []
    for key in keys:
        if docs[key].exists:
            _author_data_cache[key] = docs[key]
            result.append(True)
        else:
            result.append(False)
    
    return result


def load_author(key: str):
    try:
        data = _author_data_cache[key]
        del _author_data_cache[key]
        return data.to_dict()
    except KeyError:
        pass
    doc_ref = db.collection(AUTHOR_CACHE_COLLECTION).document(key)
    data = doc_ref.get()
    if data.exists:
        return data.to_dict()
    else:
        raise cache_buddy.CacheMiss(key)


def load_authors(keys: [str]):
    """Does _not_ return author records in the order of the input names"""
    not_in_local_cache = []
    result = []
    for key in keys:
        try:
            result.append(_author_data_cache[key].to_dict())
            del _author_data_cache[key]
        except KeyError:
            not_in_local_cache.append(key)
    
    if len(not_in_local_cache):
        doc_refs = [db.collection(AUTHOR_CACHE_COLLECTION).document(key)
                    for key in keys]
        data = db.get_all(doc_refs)
        for datum in data:
            if not datum.exists:
                raise cache_buddy.CacheMiss(datum.id)
            result.append(datum.to_dict())
    return result


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


def clear_stale_data(authors=True, documents=True, progress=True):
    with batch():
        if authors:
            author_thresh = time.time() - cache_buddy.MAXIMUM_AGE_AUTO
            author_collection = db.collection(AUTHOR_CACHE_COLLECTION)
            author_query = author_collection.where(
                'timestamp', '<', author_thresh)
            i = 0
            for doc in author_query.stream():
                i += 1
                _delete(author_collection.document(doc.id))
            cache_buddy.log_buddy.lb.i(f"Cleared {i} authors")
        
        if documents:
            doc_thresh = time.time() - cache_buddy.MAXIMUM_AGE_AUTO
            doc_collection = db.collection(DOC_CACHE_COLLECTION)
            doc_query = doc_collection.where('timestamp', '<', doc_thresh)
            i = 0
            for doc in doc_query.stream():
                i += 1
                _delete(doc_collection.document(doc.id))
            cache_buddy.log_buddy.lb.i(f"Cleared {i} documents")
        
        if progress:
            progress_thresh = time.time() - cache_buddy.MAXIMUM_PROGRESS_AGE
            progress_collection = db.collection(PROGRESS_CACHE_COLLECTION)
            progress_query = progress_collection.where(
                'timestamp', '<', progress_thresh)
            i = 0
            for doc in progress_query.stream():
                i += 1
                _delete(progress_collection.document(doc.id))
            cache_buddy.log_buddy.lb.i(f"Cleared {i} progress parcels")


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
