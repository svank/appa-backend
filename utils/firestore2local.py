# Since cache entries in Firestore are stored as opaque, compressed blobs,
# this script will download a blob, decompress it, and save the data as JSON
# to a file.
# Syntax: python firestore2local.py <author|doc> <cache key> [filename]
# If no filename is given, the cache key is used
# Tip: view the file contents as `cat <filename> | python -m json.tool`

import json
import sys

sys.path.append('../appa')

# Ensure cache_fs directories aren't generated
import local_config
local_config.backing_cache = "cache_gcp"

from cache.cache_buddy import CacheMiss
from cache import cache_gcp

try:
    if sys.argv[1] == 'author':
        result = cache_gcp.load_author(sys.argv[2])
    elif sys.argv[1] == 'doc':
        result = cache_gcp.load_document(sys.argv[2])
    else:
        print("First arg must be 'author' or 'doc'")
        sys.exit()
except CacheMiss:
    print("Second arg must be a valid cache key")
    sys.exit()

if len(sys.argv) > 3:
    fname = sys.argv[3]
else:
    fname = sys.argv[2]

json.dump(result, open(fname, 'w'))
