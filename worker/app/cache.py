import os
import json
import hashlib
import logging
from typing import Optional, Any, Callable

import redis

logger = logging.getLogger(__name__)


def _get_redis_client() -> Optional[redis.Redis]:
    try:
        url = os.getenv("QUEUE_URL", "redis://localhost:6379/0")
        return redis.from_url(url)
    except Exception as e:
        logger.warning(f"Redis unavailable for caching: {e}")
        return None


def make_file_hash(path: str, algo: str = "md5", chunk_size: int = 1 << 20) -> str:
    h = hashlib.new(algo)
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            h.update(chunk)
    return h.hexdigest()


def cache_get(namespace: str, key: str) -> Optional[Any]:
    if os.getenv("ENABLE_CACHE", "true").lower() not in ("1", "true", "yes"):
        return None
    r = _get_redis_client()
    if not r:
        return None
    try:
        data = r.get(f"{namespace}:{key}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.debug(f"cache_get failed: {e}")
    return None


def cache_set(namespace: str, key: str, value: Any, ttl_sec: int = 3600) -> None:
    if os.getenv("ENABLE_CACHE", "true").lower() not in ("1", "true", "yes"):
        return
    r = _get_redis_client()
    if not r:
        return
    try:
        r.setex(f"{namespace}:{key}", ttl_sec, json.dumps(value))
    except Exception as e:
        logger.debug(f"cache_set failed: {e}")

