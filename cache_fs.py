import os

import cache_buddy

CACHE_DIR = "cache"
DOC_CACHE_SUBDIR = os.path.join(CACHE_DIR, "documents")
AUTHOR_CACHE_SUBDIR = os.path.join(CACHE_DIR, "authors")
PROGRESS_CACHE_SUBDIR = os.path.join(CACHE_DIR, "progress")
_author_cache_contents = set()
_document_cache_contents = set()


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


def delete_document_data(key: str):
    fname = os.path.join(DOC_CACHE_SUBDIR, key)
    os.remove(fname)
    if key in _document_cache_contents:
        _document_cache_contents.remove(key)


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


def delete_author_data(key: str):
    fname = os.path.join(AUTHOR_CACHE_SUBDIR, key)
    os.remove(fname)
    if key in _author_cache_contents:
        _author_cache_contents.remove(key)


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


def delete_progress_data(key: str):
    fname = os.path.join(PROGRESS_CACHE_SUBDIR, key)
    os.remove(fname)


def load_progress_data(key: str):
    fname = os.path.join(PROGRESS_CACHE_SUBDIR, key)
    try:
        return open(fname).read()
    except FileNotFoundError:
        raise cache_buddy.CacheMiss(key)


def clear_stale_data():
    # Cached data is automatically deleted upon load if it's expired
    for author in os.listdir(AUTHOR_CACHE_SUBDIR):
        try:
            cache_buddy.load_author_data(author)
        except cache_buddy.CacheMiss:
            pass
    for document in os.listdir(DOC_CACHE_SUBDIR):
        try:
            cache_buddy.load_document_data(document)
        except cache_buddy.CacheMiss:
            pass
    for key in os.listdir(PROGRESS_CACHE_SUBDIR):
        try:
            cache_buddy.load_progress_data(key)
        except cache_buddy.CacheMiss:
            pass
