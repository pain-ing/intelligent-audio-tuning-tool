"""
内存优化工具
"""
import gc
import psutil
import logging
import threading
import time
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """内存统计信息"""
    rss_mb: float
    vms_mb: float
    percent: float
    available_mb: float
    peak_mb: float = 0.0


class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self, warning_threshold: float = 80.0, critical_threshold: float = 90.0):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.process = psutil.Process()
        self.initial_memory = self._get_memory_stats()
        self.peak_memory = self.initial_memory.rss_mb
        self.monitoring = False
        self.monitor_thread = None
        self._lock = threading.Lock()
        
    def _get_memory_stats(self) -> MemoryStats:
        """获取当前内存统计"""
        try:
            memory_info = self.process.memory_info()
            system_memory = psutil.virtual_memory()
            
            return MemoryStats(
                rss_mb=memory_info.rss / 1024 / 1024,
                vms_mb=memory_info.vms / 1024 / 1024,
                percent=self.process.memory_percent(),
                available_mb=system_memory.available / 1024 / 1024,
                peak_mb=self.peak_memory
            )
        except Exception as e:
            logger.warning(f"获取内存统计失败: {e}")
            return MemoryStats(0, 0, 0, 0)
    
    def start_monitoring(self, interval: float = 1.0):
        """开始内存监控"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("内存监控已启动")
    
    def stop_monitoring(self):
        """停止内存监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("内存监控已停止")
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.monitoring:
            try:
                stats = self._get_memory_stats()
                
                with self._lock:
                    if stats.rss_mb > self.peak_memory:
                        self.peak_memory = stats.rss_mb
                
                # 检查内存使用阈值
                if stats.percent > self.critical_threshold:
                    logger.critical(f"内存使用过高: {stats.percent:.1f}% ({stats.rss_mb:.1f}MB)")
                    self._trigger_emergency_cleanup()
                elif stats.percent > self.warning_threshold:
                    logger.warning(f"内存使用警告: {stats.percent:.1f}% ({stats.rss_mb:.1f}MB)")
                    self._trigger_gentle_cleanup()
                
                time.sleep(interval)
            except Exception as e:
                logger.error(f"内存监控错误: {e}")
                time.sleep(interval)
    
    def _trigger_gentle_cleanup(self):
        """触发温和的内存清理"""
        logger.info("执行温和内存清理")
        gc.collect()
    
    def _trigger_emergency_cleanup(self):
        """触发紧急内存清理"""
        logger.warning("执行紧急内存清理")
        # 强制垃圾回收
        for _ in range(3):
            gc.collect()
        
        # 清理缓存（如果有全局缓存管理器）
        try:
            from worker.app.cache_optimized import get_optimized_cache
            cache = get_optimized_cache()
            cache.clear_expired()
            logger.info("已清理过期缓存")
        except Exception as e:
            logger.debug(f"缓存清理失败: {e}")
    
    def get_stats(self) -> MemoryStats:
        """获取当前内存统计"""
        stats = self._get_memory_stats()
        with self._lock:
            stats.peak_mb = self.peak_memory
        return stats


class MemoryOptimizer:
    """内存优化器"""
    
    def __init__(self, max_memory_mb: float = 1024.0):
        self.max_memory_mb = max_memory_mb
        self.monitor = MemoryMonitor()
        self.cleanup_callbacks = []
    
    def register_cleanup_callback(self, callback: Callable):
        """注册清理回调函数"""
        self.cleanup_callbacks.append(callback)
    
    def check_memory_limit(self) -> bool:
        """检查内存限制"""
        stats = self.monitor.get_stats()
        return stats.rss_mb <= self.max_memory_mb
    
    def force_cleanup(self):
        """强制清理内存"""
        logger.info("强制内存清理开始")
        
        # 执行注册的清理回调
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"清理回调执行失败: {e}")
        
        # 垃圾回收
        for _ in range(3):
            gc.collect()
        
        stats = self.monitor.get_stats()
        logger.info(f"内存清理完成，当前使用: {stats.rss_mb:.1f}MB")


@contextmanager
def memory_limit_context(max_memory_mb: float = 1024.0):
    """内存限制上下文管理器"""
    optimizer = MemoryOptimizer(max_memory_mb)
    monitor = optimizer.monitor
    
    try:
        monitor.start_monitoring()
        yield optimizer
    finally:
        monitor.stop_monitoring()
        optimizer.force_cleanup()


def memory_efficient(max_memory_mb: float = 1024.0):
    """内存高效装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with memory_limit_context(max_memory_mb) as optimizer:
                # 检查初始内存
                if not optimizer.check_memory_limit():
                    optimizer.force_cleanup()
                    if not optimizer.check_memory_limit():
                        raise MemoryError(f"内存使用超过限制: {max_memory_mb}MB")
                
                return func(*args, **kwargs)
        return wrapper
    return decorator


def get_memory_usage() -> Dict[str, float]:
    """获取当前内存使用情况"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        system_memory = psutil.virtual_memory()
        
        return {
            "process_rss_mb": memory_info.rss / 1024 / 1024,
            "process_vms_mb": memory_info.vms / 1024 / 1024,
            "process_percent": process.memory_percent(),
            "system_total_mb": system_memory.total / 1024 / 1024,
            "system_available_mb": system_memory.available / 1024 / 1024,
            "system_used_percent": system_memory.percent
        }
    except Exception as e:
        logger.error(f"获取内存使用失败: {e}")
        return {}


# 全局内存监控器实例
global_memory_monitor = MemoryMonitor()


def start_global_memory_monitoring():
    """启动全局内存监控"""
    global_memory_monitor.start_monitoring()


def stop_global_memory_monitoring():
    """停止全局内存监控"""
    global_memory_monitor.stop_monitoring()


def get_global_memory_stats() -> MemoryStats:
    """获取全局内存统计"""
    return global_memory_monitor.get_stats()
