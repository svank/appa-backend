import contextlib
import json
import os
import time

import cache_buddy
import local_config

DOC_CACHE_SUBDIR = os.path.join(local_config.cache_fs_dir, "documents")
AUTHOR_CACHE_SUBDIR = os.path.join(local_config.cache_fs_dir, "authors")
PROGRESS_CACHE_SUBDIR = os.path.join(local_config.cache_fs_dir, "progress")
RESULT_CACHE_SUBDIR = os.path.join(local_config.cache_fs_dir, "results")
_author_cache_contents = set()


def refresh():
    os.makedirs(DOC_CACHE_SUBDIR, exist_ok=True)
    os.makedirs(AUTHOR_CACHE_SUBDIR, exist_ok=True)
    os.makedirs(PROGRESS_CACHE_SUBDIR, exist_ok=True)
    os.makedirs(RESULT_CACHE_SUBDIR, exist_ok=True)
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


def authors_are_in_cache(keys):
    return [author_is_in_cache(key) for key in keys]


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


def load_authors(keys: [str]):
    return [load_author(key) for key in keys]


def store_progress_data(data: dict, key: str):
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


def store_result(data, key):
    fname = os.path.join(RESULT_CACHE_SUBDIR, key)
    try:
        open(fname, "w").write(data)
    except FileNotFoundError:
        refresh()
        open(fname, "w").write(data)


def result_is_in_cache(key):
    try:
        load_result(key)
        return True
    except cache_buddy.CacheMiss:
        return False


def load_result(key):
    fname = os.path.join(RESULT_CACHE_SUBDIR, key)
    try:
        return open(fname).read()
    except FileNotFoundError:
        raise cache_buddy.CacheMiss(key)


def clear_stale_data(authors=True, documents=True,
                     progress=True, results=True):
    now = time.time()
    
    if authors:
        for key in os.listdir(AUTHOR_CACHE_SUBDIR):
            fname = os.path.join(AUTHOR_CACHE_SUBDIR, key)
            tstamp = os.path.getmtime(fname)
            if now - tstamp > cache_buddy.MAXIMUM_AGE_AUTO:
                os.remove(fname)
    
    if documents:
        for key in os.listdir(DOC_CACHE_SUBDIR):
            fname = os.path.join(DOC_CACHE_SUBDIR, key)
            tstamp = os.path.getmtime(fname)
            if now - tstamp > cache_buddy.MAXIMUM_AGE_AUTO:
                os.remove(fname)
    
    if progress:
        for key in os.listdir(PROGRESS_CACHE_SUBDIR):
            fname = os.path.join(PROGRESS_CACHE_SUBDIR, key)
            tstamp = os.path.getmtime(fname)
            if now - tstamp > cache_buddy.MAXIMUM_PROGRESS_AGE:
                os.remove(fname)
    
    if results:
        for key in os.listdir(RESULT_CACHE_SUBDIR):
            fname = os.path.join(RESULT_CACHE_SUBDIR, key)
            tstamp = os.path.getmtime(fname)
            if now - tstamp > 60 * 60:
                os.remove(fname)


# A dummy batch manager
@contextlib.contextmanager
def batch():
    yield True
