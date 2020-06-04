# Since cache entries in Firestore are stored as opaque, compressed blobs,
# this script will download a blob, decompress it, and save the data as JSON
# to a file.
# Syntax: python firestore2local.py [author|doc] [cache key] [filename]

import json
import sys

sys.path.append('..')

# Ensure cache_fs directories aren't generated
import local_config
local_config.backing_cache = "cache_firestore"

from cache_buddy import CacheMiss
import cache_firestore

try:
    if sys.argv[1] == 'author':
        result = cache_firestore.load_author(sys.argv[2])
    elif sys.argv[1] == 'doc':
        result = cache_firestore.load_document(sys.argv[2])
    else:
        print("First arg must be 'author' or 'doc'")
        sys.exit()
except CacheMiss:
    print("Second arg must be a valid cache key")
    sys.exit()

json.dump(result, open(sys.argv[3], 'w'))
