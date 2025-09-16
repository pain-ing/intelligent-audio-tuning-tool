import os
import json
import hashlib
import logging
import time
import tempfile
from typing import Optional, Any
from pathlib import Path

import redis

logger = logging.getLogger(__name__)


class LocalFileCache:
    """本地文件缓存实现（桌面模式）"""
    def __init__(self):
        # Windows: 使用 %APPDATA%\AudioTuner\cache
        appdata = os.getenv("APPDATA")
        if appdata:
            self.cache_dir = os.path.join(appdata, "AudioTuner", "cache")
        else:
            self.cache_dir = os.path.join(os.path.expanduser("~"), ".audio_tuner", "cache")

        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception:
            # 回退到临时目录
            self.cache_dir = os.path.join(tempfile.gettempdir(), "audio_tuner_cache")
            os.makedirs(self.cache_dir, exist_ok=True)

        logger.info(f"Local cache initialized at: {self.cache_dir}")

    def _cache_file_path(self, namespace: str, key: str) -> str:
        safe_key = hashlib.md5(f"{namespace}:{key}".encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_key}.json")

    def get(self, namespace: str, key: str) -> Optional[Any]:
        try:
            cache_file = self._cache_file_path(namespace, key)
            if not os.path.exists(cache_file):
                return None

            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # 检查过期时间
            if cache_data.get("expires_at", 0) < time.time():
                try:
                    os.remove(cache_file)
                except:
                    pass
                return None

            return cache_data.get("value")
        except Exception as e:
            logger.debug(f"Local cache get failed: {e}")
            return None

    def set(self, namespace: str, key: str, value: Any, ttl_sec: int = 30) -> None:
        try:
            cache_file = self._cache_file_path(namespace, key)
            cache_data = {
                "value": value,
                "expires_at": time.time() + ttl_sec,
                "created_at": time.time()
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, default=str, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"Local cache set failed: {e}")


def get_redis_client() -> Optional[redis.Redis]:
    try:
        url = os.getenv("QUEUE_URL", "redis://localhost:6379/0")
        return redis.from_url(url)
    except Exception as e:
        logger.warning(f"Redis unavailable for caching: {e}")
        return None


# 全局缓存实例（根据运行模式选择）
_mode = (os.getenv("CACHE_MODE") or os.getenv("APP_MODE") or "").lower()
if _mode in ("desktop", "local"):
    _local_cache = LocalFileCache()
else:
    _local_cache = None


def cache_get(namespace: str, key: str) -> Optional[Any]:
    if os.getenv("ENABLE_CACHE", "true").lower() not in ("1", "true", "yes"):
        return None

    # 桌面模式使用本地文件缓存
    if _local_cache:
        return _local_cache.get(namespace, key)

    # 服务器模式使用Redis
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

    # 桌面模式使用本地文件缓存
    if _local_cache:
        _local_cache.set(namespace, key, value, ttl_sec)
        return

    # 服务器模式使用Redis
    r = get_redis_client()
    if not r:
        return
    try:
        r.setex(f"{namespace}:{key}", ttl_sec, json.dumps(value, default=str))
    except Exception as e:
        logger.debug(f"cache_set failed: {e}")


def make_file_hash(file_path: str) -> str:
    """生成文件哈希（用于缓存键）"""
    try:
        stat = os.stat(file_path)
        content = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
        return hashlib.md5(content.encode()).hexdigest()
    except Exception:
        return hashlib.md5(file_path.encode()).hexdigest()