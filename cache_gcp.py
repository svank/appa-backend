import json
import random
import time
import zlib

import requests
from google.cloud import firestore

import cache_buddy
import local_config

DOC_CACHE_COLLECTION = "documents"
AUTHOR_CACHE_COLLECTION = "authors"

SHARDS = [chr(i) for i in range(65, 75)]

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
# on each request, so use a conservative 7 MiB
MAX_API_CALL_SIZE = 7 * 1024 * 1024


def refresh():
    global _author_data_cache
    _author_data_cache = {}


# For now, compression is only applied to author records, which are by far
# larger than document records, so that document data is stored plainly to
# possibly ease future debugging.
def _compress_record(record):
    compressed_data = zlib.compress(
        json.dumps(record, check_circular=False, separators=(',', ':')).encode(),
        level=4)
    output = {'timestamp': record['timestamp'],
              'zlib_data': compressed_data,
              'zlib_data_size': len(compressed_data),
              'version': record['version']}
    if 'coauthors' in record:
        output['n_coauthors'] = len(record['coauthors'])
    if 'appears_as' in record:
        output['n_aliases'] = len(record['appears_as'])
    if 'documents' in record:
        output['n_documents'] = len(record['documents'])
    if 'name' in record:
        output['name'] = record['name']
    return output


def _decompress_record(record):
    return json.loads(zlib.decompress(record['zlib_data']).decode())


def store_document(data: dict, key: str):
    doc_ref = db.collection(DOC_CACHE_COLLECTION).document(key)
    data['shard'] = random.choice(SHARDS)
    _set(doc_ref, data)


def delete_document(key: str):
    doc_ref = db.collection(DOC_CACHE_COLLECTION).document(key)
    _delete(doc_ref)


def load_document(key: str):
    doc_ref = db.collection(DOC_CACHE_COLLECTION).document(key)
    data = doc_ref.get()
    if data.exists:
        data = data.to_dict()
        try:
            del data['shard']
        except KeyError:
            pass
        return data
    raise cache_buddy.CacheMiss(key)


def load_documents(keys: []):
    docs = db.get_all(
        [db.collection(DOC_CACHE_COLLECTION).document(key) for key in keys]
    )
    docs = [doc.to_dict() for doc in docs]
    for data in docs:
        try:
            del data['shard']
        except KeyError:
            pass
    return docs


def store_author(data: dict, key: str):
    doc_ref = db.collection(AUTHOR_CACHE_COLLECTION).document(key)
    data = _compress_record(data)
    data['shard'] = random.choice(SHARDS)
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
        return _decompress_record(data.to_dict())
    except KeyError:
        pass
    doc_ref = db.collection(AUTHOR_CACHE_COLLECTION).document(key)
    data = doc_ref.get()
    if data.exists:
        return _decompress_record(data.to_dict())
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
    return [_decompress_record(r) for r in result]


def store_progress_data(data: dict, key: str):
    data = json.dumps(data, check_circular=False, separators=(',', ':'))
    try:
        requests.post(
            local_config.relay_url,
            data={
                'key': key,
                'value': data,
                'token': local_config.relay_token
            },
            # Large first value to ensure a connection is made, low second
            # value to not wait for a response
            timeout=(1, 0.001)
        )
    except requests.Timeout:
        pass


def delete_progress_data(key: str):
    pass


def get_progress_cache_contents():
    return []


def load_progress_data(key: str):
    raise cache_buddy.CacheMiss(key)


def clear_stale_data(authors=True, documents=True, progress=True):
    if authors:
        _do_clear_data('author')
    
    if documents:
        _do_clear_data('document')


def _do_clear_data(mode):
    if mode == 'author':
        collection = db.collection(AUTHOR_CACHE_COLLECTION)
        version = cache_buddy.AUTHOR_VERSION_NUMBER
        msg = "Cleared {} authors"
    elif mode == 'document':
        collection = db.collection(DOC_CACHE_COLLECTION)
        version = cache_buddy.DOCUMENT_VERSION_NUMBER
        msg = "Cleared {} documents"
    else:
        return
    
    author_thresh = time.time() - cache_buddy.MAXIMUM_AGE_AUTO
    i = 0
    with batch():
        for shard_val in SHARDS:
            query = (collection.where('shard', '==', shard_val)
                               .where('timestamp', '<', author_thresh))
            for doc in query.stream():
                i += 1
                _delete(collection.document(doc.id))
            
            query = (collection.where('shard', '==', shard_val)
                               .where('version', '<', version))
            for doc in query.stream():
                i += 1
                _delete(collection.document(doc.id))
    
    cache_buddy.log_buddy.lb.i(msg.format(i))


def _set(doc_ref, data):
    global _batch, _batch_size, _batch_bytes
    if _batch is None:
        doc_ref.set(data)
    else:
        _batch.set(doc_ref, data)
        _batch_size += 1
        if 'zlib_data' in data:
            # We neglect the 'timestamp' field in the size calculation, but
            # the maximum size is set conservatively
            _batch_bytes += len(data['zlib_data'])
        else:
            _batch_bytes += len(
                json.dumps(data, check_circular=False).encode('utf-8'))
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
