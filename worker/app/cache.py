import os
import json
import hashlib
import logging
from typing import Optional, Any, Callable

import redis

# 导入优化的缓存系统
try:
    from .cache_optimized import (
        get_optimized_cache,
        cache_get as optimized_cache_get,
        cache_set as optimized_cache_set,
        cache_delete as optimized_cache_delete,
        cache_stats as optimized_cache_stats
    )
    OPTIMIZED_CACHE_AVAILABLE = True
except ImportError:
    OPTIMIZED_CACHE_AVAILABLE = False

logger = logging.getLogger(__name__)

# 缓存模式选择
CACHE_MODE = os.getenv("CACHE_MODE", "optimized" if OPTIMIZED_CACHE_AVAILABLE else "redis").lower()


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
    """获取缓存值（自动选择缓存后端）"""
    if os.getenv("ENABLE_CACHE", "true").lower() not in ("1", "true", "yes"):
        return None

    # 优先使用优化的内存缓存
    if CACHE_MODE == "optimized" and OPTIMIZED_CACHE_AVAILABLE:
        return optimized_cache_get(namespace, key)

    # 回退到Redis缓存
    r = _get_redis_client()
    if not r:
        # Redis不可用时使用优化缓存（如果可用）
        if OPTIMIZED_CACHE_AVAILABLE:
            return optimized_cache_get(namespace, key)
        return None

    try:
        data = r.get(f"{namespace}:{key}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.debug(f"Redis cache_get failed: {e}")
        # Redis失败时回退到优化缓存
        if OPTIMIZED_CACHE_AVAILABLE:
            return optimized_cache_get(namespace, key)

    return None


def cache_set(namespace: str, key: str, value: Any, ttl_sec: int = 3600) -> None:
    """设置缓存值（自动选择缓存后端）"""
    if os.getenv("ENABLE_CACHE", "true").lower() not in ("1", "true", "yes"):
        return

    # 优先使用优化的内存缓存
    if CACHE_MODE == "optimized" and OPTIMIZED_CACHE_AVAILABLE:
        optimized_cache_set(namespace, key, value, ttl_sec)
        return

    # 回退到Redis缓存
    r = _get_redis_client()
    if not r:
        # Redis不可用时使用优化缓存（如果可用）
        if OPTIMIZED_CACHE_AVAILABLE:
            optimized_cache_set(namespace, key, value, ttl_sec)
        return

    try:
        r.setex(f"{namespace}:{key}", ttl_sec, json.dumps(value, default=str))
    except Exception as e:
        logger.debug(f"Redis cache_set failed: {e}")
        # Redis失败时回退到优化缓存
        if OPTIMIZED_CACHE_AVAILABLE:
            optimized_cache_set(namespace, key, value, ttl_sec)


def cache_delete(namespace: str, key: str) -> bool:
    """删除缓存值"""
    if CACHE_MODE == "optimized" and OPTIMIZED_CACHE_AVAILABLE:
        return optimized_cache_delete(namespace, key)

    r = _get_redis_client()
    if not r:
        if OPTIMIZED_CACHE_AVAILABLE:
            return optimized_cache_delete(namespace, key)
        return False

    try:
        result = r.delete(f"{namespace}:{key}")
        return bool(result)
    except Exception as e:
        logger.debug(f"Redis cache_delete failed: {e}")
        if OPTIMIZED_CACHE_AVAILABLE:
            return optimized_cache_delete(namespace, key)
        return False


def cache_stats() -> dict:
    """获取缓存统计信息"""
    if CACHE_MODE == "optimized" and OPTIMIZED_CACHE_AVAILABLE:
        return optimized_cache_stats()

    # Redis统计信息（简化版）
    r = _get_redis_client()
    if r:
        try:
            info = r.info()
            return {
                "backend": "redis",
                "memory_usage_mb": info.get("used_memory", 0) / 1024 / 1024,
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
        except Exception as e:
            logger.debug(f"Redis stats failed: {e}")

    return {"backend": "none", "error": "No cache backend available"}

