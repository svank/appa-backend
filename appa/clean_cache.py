"""
Deletes all expired data from the cache
"""
from cache import cache_buddy

if __name__ == "__main__":
    cache_buddy.backing_cache.clear_stale_data()
