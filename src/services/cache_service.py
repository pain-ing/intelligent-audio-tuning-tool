"""
缓存服务实现
"""
import json
import pickle
from typing import Any, Optional, Dict
import asyncio
from threading import Lock

from src.services.base import BaseService, CacheServiceInterface
from src.core.config import config, CacheMode
from src.core.exceptions import StorageError


class LocalCacheService(BaseService, CacheServiceInterface):
    """本地内存缓存服务"""
    
    def __init__(self):
        super().__init__()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key in self._cache:
                item = self._cache[key]
                
                # 检查是否过期
                import time
                if item['expires'] > time.time():
                    return item['value']
                else:
                    # 删除过期项
                    del self._cache[key]
            
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存值"""
        import time
        
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expires': time.time() + ttl
            }
    
    async def delete(self, key: str) -> None:
        """删除缓存值"""
        with self._lock:
            self._cache.pop(key, None)
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        value = await self.get(key)
        return value is not None
    
    def clear_expired(self):
        """清理过期缓存"""
        import time
        current_time = time.time()
        
        with self._lock:
            expired_keys = [
                key for key, item in self._cache.items()
                if item['expires'] <= current_time
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                self.logger.info(f"Cleared {len(expired_keys)} expired cache items")


class RedisCacheService(BaseService, CacheServiceInterface):
    """Redis缓存服务"""
    
    def __init__(self):
        super().__init__()
        try:
            import redis.asyncio as redis
            self.redis = redis.from_url(config.redis_url)
        except ImportError:
            raise StorageError("Redis client not available")
        except Exception as e:
            raise StorageError(f"Failed to initialize Redis client: {str(e)}")
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            data = await self.redis.get(key)
            if data:
                return pickle.loads(data)
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get cache key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存值"""
        try:
            data = pickle.dumps(value)
            await self.redis.setex(key, ttl, data)
            
        except Exception as e:
            self.logger.error(f"Failed to set cache key {key}: {str(e)}")
    
    async def delete(self, key: str) -> None:
        """删除缓存值"""
        try:
            await self.redis.delete(key)
            
        except Exception as e:
            self.logger.error(f"Failed to delete cache key {key}: {str(e)}")
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            result = await self.redis.exists(key)
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"Failed to check cache key {key}: {str(e)}")
            return False


class DisabledCacheService(BaseService, CacheServiceInterface):
    """禁用的缓存服务"""
    
    async def get(self, key: str) -> Optional[Any]:
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        pass
    
    async def delete(self, key: str) -> None:
        pass
    
    async def exists(self, key: str) -> bool:
        return False


def get_cache_service() -> CacheServiceInterface:
    """获取缓存服务实例"""
    if config.cache_mode == CacheMode.LOCAL:
        return LocalCacheService()
    elif config.cache_mode == CacheMode.REDIS:
        return RedisCacheService()
    elif config.cache_mode == CacheMode.DISABLED:
        return DisabledCacheService()
    else:
        raise StorageError(f"Unsupported cache mode: {config.cache_mode}")


# 缓存装饰器
def cached(ttl: int = 3600, key_prefix: str = ""):
    """缓存装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache_service = get_cache_service()
            
            # 生成缓存键
            import hashlib
            key_data = f"{key_prefix}:{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # 尝试从缓存获取
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator
