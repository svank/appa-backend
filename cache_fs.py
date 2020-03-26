import os

import cache_buddy

CACHE_DIR = "cache"
DOC_CACHE_SUBDIR = os.path.join(CACHE_DIR, "documents")
AUTHOR_CACHE_SUBDIR = os.path.join(CACHE_DIR, "authors")
PROGRESS_CACHE_SUBDIR = os.path.join(CACHE_DIR, "progress")
_author_cache_contents = None
_document_cache_contents = None


def refresh_dirs_and_cache():
    os.makedirs(DOC_CACHE_SUBDIR, exist_ok=True)
    os.makedirs(AUTHOR_CACHE_SUBDIR, exist_ok=True)
    os.makedirs(PROGRESS_CACHE_SUBDIR, exist_ok=True)
    global _author_cache_contents, _document_cache_contents
    _author_cache_contents= set(os.listdir(AUTHOR_CACHE_SUBDIR))
    _document_cache_contents = set(os.listdir(DOC_CACHE_SUBDIR))


refresh_dirs_and_cache()


def store_document_data(data: str, key: str):
    fname = os.path.join(DOC_CACHE_SUBDIR, key)
    try:
        open(fname, "w").write(data)
    except FileNotFoundError:
        refresh_dirs_and_cache()
        open(fname, "w").write(data)
    _document_cache_contents.add(key)


def document_is_in_cache(key):
    return key in _document_cache_contents


def load_document_data(key: str):
    fname = os.path.join(DOC_CACHE_SUBDIR, key)
    try:
        return open(fname).read()
    except FileNotFoundError:
        if key in _document_cache_contents:
            refresh_dirs_and_cache()
        raise cache_buddy.CacheMiss(key)


def store_author_data(data: str, key: str):
    fname = os.path.join(AUTHOR_CACHE_SUBDIR, key)
    try:
        open(fname, "w").write(data)
    except FileNotFoundError:
        refresh_dirs_and_cache()
        open(fname, "w").write(data)
    _author_cache_contents.add(key)


def author_is_in_cache(key):
    return key in _author_cache_contents


def load_author_data(key: str):
    fname = os.path.join(AUTHOR_CACHE_SUBDIR, key)
    try:
        return open(fname).read()
    except FileNotFoundError:
        if key in _author_cache_contents:
            refresh_dirs_and_cache()
        raise cache_buddy.CacheMiss(key)


def store_progress_data(data: str, key: str):
    fname = os.path.join(PROGRESS_CACHE_SUBDIR, key)
    try:
        open(fname, "w").write(data)
    except FileNotFoundError:
        refresh_dirs_and_cache()
        open(fname, "w").write(data)


def load_progress_data(key: str):
    fname = os.path.join(PROGRESS_CACHE_SUBDIR, key)
    try:
        return open(fname).read()
    except FileNotFoundError:
        raise cache_buddy.CacheMiss(key)

