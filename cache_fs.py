import os

CACHE_DIR = "cache"
DOC_CACHE_SUBDIR = os.path.join(CACHE_DIR, "documents")
AUTHOR_CACHE_SUBDIR = os.path.join(CACHE_DIR, "authors")


def store_document_data(data: str, key: str):
    os.makedirs(DOC_CACHE_SUBDIR, exist_ok=True)
    fname = os.path.join(DOC_CACHE_SUBDIR, key)
    open(fname, "w").write(data)


def document_is_in_cache(key):
    fname = os.path.join(DOC_CACHE_SUBDIR, key)
    return os.path.exists(fname)


def load_document_data(key: str):
    fname = os.path.join(DOC_CACHE_SUBDIR, key)
    if not os.path.exists(fname):
        return None
    return open(fname).read()


def store_author_data(data: str, key: str):
    os.makedirs(AUTHOR_CACHE_SUBDIR, exist_ok=True)
    fname = os.path.join(AUTHOR_CACHE_SUBDIR, key)
    open(fname, "w").write(data)


def author_is_in_cache(key):
    fname = os.path.join(AUTHOR_CACHE_SUBDIR, key)
    return os.path.exists(fname)


def load_author_data(key: str):
    fname = os.path.join(AUTHOR_CACHE_SUBDIR, key)
    if not os.path.exists(fname):
        return None
    return open(fname).read()
