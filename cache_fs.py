import contextlib
import json
import os

import cache_buddy

CACHE_DIR = "cache"
DOC_CACHE_SUBDIR = os.path.join(CACHE_DIR, "documents")
AUTHOR_CACHE_SUBDIR = os.path.join(CACHE_DIR, "authors")
PROGRESS_CACHE_SUBDIR = os.path.join(CACHE_DIR, "progress")
_author_cache_contents = set()


def refresh():
    os.makedirs(DOC_CACHE_SUBDIR, exist_ok=True)
    os.makedirs(AUTHOR_CACHE_SUBDIR, exist_ok=True)
    os.makedirs(PROGRESS_CACHE_SUBDIR, exist_ok=True)
    global _author_cache_contents
    _author_cache_contents = set(os.listdir(AUTHOR_CACHE_SUBDIR))


refresh()


def store_document(data: dict, key: str):
    fname = os.path.join(DOC_CACHE_SUBDIR, key)
    data = json.dumps(data, check_circular=False)
    try:
        open(fname, "w").write(data)
    except FileNotFoundError:
        refresh()
        open(fname, "w").write(data)


def store_documents(datas: [], keys: []):
    for data, key in zip(datas, keys):
        store_document(data, key)


def delete_document(key: str):
    fname = os.path.join(DOC_CACHE_SUBDIR, key)
    os.remove(fname)


def load_document(key: str):
    fname = os.path.join(DOC_CACHE_SUBDIR, key)
    try:
        return json.load(open(fname))
    except FileNotFoundError:
        raise cache_buddy.CacheMiss(key)
    except json.decoder.JSONDecodeError:
        raise ValueError("Error decoding document cache JSON data" + key)


def load_documents(keys: []):
    return [load_document(key) for key in keys]


def store_author(data: dict, key: str):
    fname = os.path.join(AUTHOR_CACHE_SUBDIR, key)
    data = json.dumps(data, check_circular=False)
    try:
        open(fname, "w").write(data)
    except FileNotFoundError:
        refresh()
        open(fname, "w").write(data)
    _author_cache_contents.add(key)


def delete_author(key: str):
    fname = os.path.join(AUTHOR_CACHE_SUBDIR, key)
    os.remove(fname)
    if key in _author_cache_contents:
        _author_cache_contents.remove(key)


def author_is_in_cache(key):
    return key in _author_cache_contents


def load_author(key: str):
    fname = os.path.join(AUTHOR_CACHE_SUBDIR, key)
    try:
        return json.load(open(fname))
    except FileNotFoundError:
        if key in _author_cache_contents:
            refresh()
        raise cache_buddy.CacheMiss(key)
    except json.decoder.JSONDecodeError:
        raise ValueError("Error decoding author cache JSON data" + key)


def store_progress_data(data: str, key: str):
    fname = os.path.join(PROGRESS_CACHE_SUBDIR, key)
    data = json.dumps(data, check_circular=False)
    try:
        open(fname, "w").write(data)
    except FileNotFoundError:
        refresh()
        open(fname, "w").write(data)


def delete_progress_data(key: str):
    fname = os.path.join(PROGRESS_CACHE_SUBDIR, key)
    os.remove(fname)


def load_progress_data(key: str):
    fname = os.path.join(PROGRESS_CACHE_SUBDIR, key)
    try:
        return json.load(open(fname))
    except FileNotFoundError:
        raise cache_buddy.CacheMiss(key)


def clear_stale_data():
    # Cached data is automatically deleted upon load if it's expired
    for author in os.listdir(AUTHOR_CACHE_SUBDIR):
        try:
            cache_buddy.load_author(author)
        except cache_buddy.CacheMiss:
            pass
    for document in os.listdir(DOC_CACHE_SUBDIR):
        try:
            cache_buddy.load_document(document)
        except cache_buddy.CacheMiss:
            pass
    for key in os.listdir(PROGRESS_CACHE_SUBDIR):
        try:
            cache_buddy.load_progress_data(key)
        except cache_buddy.CacheMiss:
            pass


# A dummy batch manager
@contextlib.contextmanager
def batch():
    yield True
