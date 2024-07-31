# /modular_store_backend/modules/cache.py
from flask_caching import Cache

cache = Cache(config={'CACHE_TYPE': 'simple'})
