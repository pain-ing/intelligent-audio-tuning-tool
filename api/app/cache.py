import os
import json
import hashlib
import logging
from typing import Optional, Any

import redis

logger = logging.getLogger(__name__)


def get_redis_client() -> Optional[redis.Redis]:
    try:
        url = os.getenv("QUEUE_URL", "redis://localhost:6379/0")
        return redis.from_url(url)
    except Exception as e:
        logger.warning(f"Redis unavailable for caching: {e}")
        return None


def cache_get(namespace: str, key: str) -> Optional[Any]:
    if os.getenv("ENABLE_CACHE", "true").lower() not in ("1", "true", "yes"):
        return None
    r = get_redis_client()
    if not r:
        return None
    try:
        data = r.get(f"{namespace}:{key}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.debug(f"cache_get failed: {e}")
    return None


def cache_set(namespace: str, key: str, value: Any, ttl_sec: int = 30) -> None:
    if os.getenv("ENABLE_CACHE", "true").lower() not in ("1", "true", "yes"):
        return
    r = get_redis_client()
    if not r:
        return
    try:
        r.setex(f"{namespace}:{key}", ttl_sec, json.dumps(value, default=str))
    except Exception as e:
        logger.debug(f"cache_set failed: {e}")

