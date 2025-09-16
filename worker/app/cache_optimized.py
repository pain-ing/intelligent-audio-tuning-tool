"""
内存优化的缓存模块
实现LRU淘汰、内存限制和智能清理
"""

import os
import time
import json
import hashlib
import threading
import gc
import psutil
from typing import Any, Optional, Dict, List
from collections import OrderedDict
from dataclasses import dataclass, asdict
import logging
import weakref

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    size_bytes: int
    ttl_sec: int

class MemoryAwareCache:
    """内存感知的缓存系统"""
    
    def __init__(self, 
                 max_memory_mb: float = 256.0,
                 max_entries: int = 1000,
                 cleanup_interval: float = 60.0,
                 memory_check_interval: float = 10.0):
        """
        初始化内存感知缓存
        
        Args:
            max_memory_mb: 最大内存使用限制 (MB)
            max_entries: 最大缓存条目数
            cleanup_interval: 清理间隔 (秒)
            memory_check_interval: 内存检查间隔 (秒)
        """
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self.max_entries = max_entries
        self.cleanup_interval = cleanup_interval
        self.memory_check_interval = memory_check_interval
        
        # 使用OrderedDict实现LRU
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        
        # 内存统计
        self._current_memory_bytes = 0
        self._total_hits = 0
        self._total_misses = 0
        
        # 后台清理线程
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        
        # 启动后台清理
        self._start_cleanup_thread()
        
        logger.info(f"内存感知缓存初始化: 最大内存={max_memory_mb}MB, 最大条目={max_entries}")
    
    def _start_cleanup_thread(self):
        """启动后台清理线程"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._stop_cleanup.clear()
            self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
            self._cleanup_thread.start()
    
    def _cleanup_worker(self):
        """后台清理工作线程"""
        while not self._stop_cleanup.wait(self.cleanup_interval):
            try:
                self._periodic_cleanup()
            except Exception as e:
                logger.error(f"缓存清理失败: {e}")
    
    def _periodic_cleanup(self):
        """定期清理过期和低价值缓存"""
        with self._lock:
            current_time = time.time()
            
            # 清理过期条目
            expired_keys = []
            for key, entry in self._cache.items():
                if current_time - entry.created_at > entry.ttl_sec:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_entry(key)
            
            # 检查内存使用
            if self._current_memory_bytes > self.max_memory_bytes * 0.8:  # 80%阈值
                self._memory_pressure_cleanup()
            
            # 检查条目数量
            if len(self._cache) > self.max_entries * 0.9:  # 90%阈值
                self._size_pressure_cleanup()
            
            logger.debug(f"缓存清理完成: {len(self._cache)}条目, {self._current_memory_bytes/1024/1024:.1f}MB")
    
    def _memory_pressure_cleanup(self):
        """内存压力清理"""
        target_memory = self.max_memory_bytes * 0.6  # 清理到60%
        
        # 按访问频率和时间排序，优先清理低价值条目
        entries_by_value = []
        current_time = time.time()
        
        for key, entry in self._cache.items():
            # 计算价值分数（访问频率 / 时间衰减 / 大小惩罚）
            time_factor = 1.0 / (1.0 + (current_time - entry.last_accessed) / 3600)  # 1小时衰减
            frequency_factor = entry.access_count
            size_penalty = 1.0 / (1.0 + entry.size_bytes / (1024 * 1024))  # 大文件惩罚
            
            value_score = frequency_factor * time_factor * size_penalty
            entries_by_value.append((value_score, key, entry.size_bytes))
        
        # 按价值分数排序，优先删除低价值条目
        entries_by_value.sort(key=lambda x: x[0])
        
        removed_memory = 0
        for _, key, size_bytes in entries_by_value:
            if self._current_memory_bytes - removed_memory <= target_memory:
                break
            
            self._remove_entry(key)
            removed_memory += size_bytes
        
        logger.info(f"内存压力清理: 释放了 {removed_memory/1024/1024:.1f}MB")
    
    def _size_pressure_cleanup(self):
        """条目数量压力清理"""
        target_count = int(self.max_entries * 0.7)  # 清理到70%
        
        # 使用LRU策略，删除最久未访问的条目
        while len(self._cache) > target_count:
            # OrderedDict的第一个元素是最久未访问的
            oldest_key = next(iter(self._cache))
            self._remove_entry(oldest_key)
        
        logger.info(f"条目数量压力清理: 保留了 {len(self._cache)} 个条目")
    
    def _remove_entry(self, key: str):
        """移除缓存条目"""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._current_memory_bytes -= entry.size_bytes
            
            # 尝试释放对象内存
            del entry.value
            del entry
    
    def _calculate_size(self, value: Any) -> int:
        """估算对象大小"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, dict):
                return len(json.dumps(value, default=str).encode())
            elif hasattr(value, '__sizeof__'):
                return value.__sizeof__()
            else:
                # 粗略估算
                return len(str(value).encode())
        except Exception:
            return 1024  # 默认1KB
    
    def get(self, namespace: str, key: str) -> Optional[Any]:
        """获取缓存值"""
        cache_key = f"{namespace}:{key}"
        
        with self._lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                current_time = time.time()
                
                # 检查是否过期
                if current_time - entry.created_at > entry.ttl_sec:
                    self._remove_entry(cache_key)
                    self._total_misses += 1
                    return None
                
                # 更新访问信息
                entry.last_accessed = current_time
                entry.access_count += 1
                
                # 移动到末尾（LRU）
                self._cache.move_to_end(cache_key)
                
                self._total_hits += 1
                return entry.value
            else:
                self._total_misses += 1
                return None
    
    def set(self, namespace: str, key: str, value: Any, ttl_sec: int = 3600) -> bool:
        """设置缓存值"""
        cache_key = f"{namespace}:{key}"
        
        # 计算对象大小
        size_bytes = self._calculate_size(value)
        
        # 检查单个对象是否过大
        if size_bytes > self.max_memory_bytes * 0.5:  # 单个对象不能超过总内存的50%
            logger.warning(f"对象过大，拒绝缓存: {size_bytes/1024/1024:.1f}MB")
            return False
        
        with self._lock:
            current_time = time.time()
            
            # 如果键已存在，先移除旧值
            if cache_key in self._cache:
                old_entry = self._cache[cache_key]
                self._current_memory_bytes -= old_entry.size_bytes
            
            # 检查是否需要清理空间
            while (self._current_memory_bytes + size_bytes > self.max_memory_bytes or 
                   len(self._cache) >= self.max_entries):
                if not self._cache:
                    break
                
                # 移除最久未访问的条目
                oldest_key = next(iter(self._cache))
                self._remove_entry(oldest_key)
            
            # 创建新条目
            entry = CacheEntry(
                value=value,
                created_at=current_time,
                last_accessed=current_time,
                access_count=1,
                size_bytes=size_bytes,
                ttl_sec=ttl_sec
            )
            
            self._cache[cache_key] = entry
            self._current_memory_bytes += size_bytes
            
            logger.debug(f"缓存设置: {cache_key}, 大小: {size_bytes/1024:.1f}KB")
            return True
    
    def delete(self, namespace: str, key: str) -> bool:
        """删除缓存值"""
        cache_key = f"{namespace}:{key}"
        
        with self._lock:
            if cache_key in self._cache:
                self._remove_entry(cache_key)
                return True
            return False
    
    def clear_namespace(self, namespace: str):
        """清理指定命名空间的所有缓存"""
        with self._lock:
            keys_to_remove = [key for key in self._cache.keys() if key.startswith(f"{namespace}:")]
            for key in keys_to_remove:
                self._remove_entry(key)
            
            logger.info(f"清理命名空间 {namespace}: 移除了 {len(keys_to_remove)} 个条目")
    
    def clear_all(self):
        """清理所有缓存"""
        with self._lock:
            self._cache.clear()
            self._current_memory_bytes = 0
            gc.collect()
            
            logger.info("清理所有缓存")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_requests = self._total_hits + self._total_misses
            hit_rate = self._total_hits / total_requests if total_requests > 0 else 0.0
            
            return {
                "entries_count": len(self._cache),
                "memory_usage_mb": self._current_memory_bytes / 1024 / 1024,
                "memory_limit_mb": self.max_memory_bytes / 1024 / 1024,
                "memory_usage_percent": (self._current_memory_bytes / self.max_memory_bytes) * 100,
                "hit_rate": hit_rate,
                "total_hits": self._total_hits,
                "total_misses": self._total_misses,
                "max_entries": self.max_entries
            }
    
    def shutdown(self):
        """关闭缓存系统"""
        self._stop_cleanup.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5.0)
        
        self.clear_all()
        logger.info("缓存系统已关闭")

# 全局优化缓存实例
_global_cache = None
_cache_lock = threading.Lock()

def get_optimized_cache() -> MemoryAwareCache:
    """获取全局优化缓存实例"""
    global _global_cache
    
    if _global_cache is None:
        with _cache_lock:
            if _global_cache is None:
                # 根据可用内存动态调整缓存大小
                try:
                    available_memory_gb = psutil.virtual_memory().available / (1024**3)
                    if available_memory_gb > 8:
                        max_memory_mb = 512.0
                    elif available_memory_gb > 4:
                        max_memory_mb = 256.0
                    else:
                        max_memory_mb = 128.0
                except Exception:
                    max_memory_mb = 256.0
                
                _global_cache = MemoryAwareCache(max_memory_mb=max_memory_mb)
    
    return _global_cache

# 兼容性函数
def cache_get(namespace: str, key: str) -> Optional[Any]:
    """获取缓存值（兼容性函数）"""
    if os.getenv("ENABLE_CACHE", "true").lower() not in ("1", "true", "yes"):
        return None
    
    cache = get_optimized_cache()
    return cache.get(namespace, key)

def cache_set(namespace: str, key: str, value: Any, ttl_sec: int = 3600) -> None:
    """设置缓存值（兼容性函数）"""
    if os.getenv("ENABLE_CACHE", "true").lower() not in ("1", "true", "yes"):
        return
    
    cache = get_optimized_cache()
    cache.set(namespace, key, value, ttl_sec)

def cache_delete(namespace: str, key: str) -> bool:
    """删除缓存值（兼容性函数）"""
    cache = get_optimized_cache()
    return cache.delete(namespace, key)

def cache_clear_namespace(namespace: str):
    """清理命名空间（兼容性函数）"""
    cache = get_optimized_cache()
    cache.clear_namespace(namespace)

def cache_stats() -> Dict[str, Any]:
    """获取缓存统计（兼容性函数）"""
    cache = get_optimized_cache()
    return cache.get_stats()

def make_file_hash(file_path: str) -> str:
    """生成文件哈希（用于缓存键）"""
    try:
        stat = os.stat(file_path)
        content = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
        return hashlib.md5(content.encode()).hexdigest()
    except Exception:
        return hashlib.md5(file_path.encode()).hexdigest()
