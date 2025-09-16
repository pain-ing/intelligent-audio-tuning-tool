"""
内存优化的Celery配置和任务管理
实现任务间内存隔离、清理和监控
"""

import os
import gc
import time
import psutil
import threading
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextlib import contextmanager
from celery import Celery
from celery.signals import (
    task_prerun, task_postrun, task_failure, 
    worker_process_init, worker_process_shutdown,
    worker_ready, worker_shutdown
)

logger = logging.getLogger(__name__)

class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = self.get_memory_usage()
        self.peak_memory = self.initial_memory
        self.task_memory_usage = {}
        self._lock = threading.Lock()
    
    def get_memory_usage(self) -> Dict[str, float]:
        """获取当前内存使用情况"""
        try:
            memory_info = self.process.memory_info()
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": self.process.memory_percent()
            }
        except Exception as e:
            logger.warning(f"获取内存使用失败: {e}")
            return {"rss_mb": 0, "vms_mb": 0, "percent": 0}
    
    def record_task_start(self, task_id: str, task_name: str):
        """记录任务开始时的内存使用"""
        with self._lock:
            memory_usage = self.get_memory_usage()
            self.task_memory_usage[task_id] = {
                "task_name": task_name,
                "start_memory": memory_usage,
                "start_time": time.time()
            }
            
            # 更新峰值内存
            if memory_usage["rss_mb"] > self.peak_memory["rss_mb"]:
                self.peak_memory = memory_usage
    
    def record_task_end(self, task_id: str, success: bool = True):
        """记录任务结束时的内存使用"""
        with self._lock:
            if task_id not in self.task_memory_usage:
                return
            
            end_memory = self.get_memory_usage()
            task_info = self.task_memory_usage[task_id]
            
            # 计算内存增长
            memory_growth = end_memory["rss_mb"] - task_info["start_memory"]["rss_mb"]
            duration = time.time() - task_info["start_time"]
            
            # 记录统计信息
            task_stats = {
                "task_name": task_info["task_name"],
                "duration": duration,
                "memory_growth_mb": memory_growth,
                "start_memory_mb": task_info["start_memory"]["rss_mb"],
                "end_memory_mb": end_memory["rss_mb"],
                "success": success
            }
            
            # 如果内存增长过大，记录警告
            if memory_growth > 100:  # 100MB
                logger.warning(f"任务 {task_info['task_name']} 内存增长过大: {memory_growth:.1f}MB")
            
            # 清理任务记录
            del self.task_memory_usage[task_id]
            
            logger.info(f"任务内存统计 {task_info['task_name']}: "
                       f"耗时{duration:.1f}s, 内存增长{memory_growth:.1f}MB")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取内存监控统计"""
        current_memory = self.get_memory_usage()
        with self._lock:
            return {
                "initial_memory_mb": self.initial_memory["rss_mb"],
                "current_memory_mb": current_memory["rss_mb"],
                "peak_memory_mb": self.peak_memory["rss_mb"],
                "memory_growth_mb": current_memory["rss_mb"] - self.initial_memory["rss_mb"],
                "active_tasks": len(self.task_memory_usage),
                "memory_percent": current_memory["percent"]
            }

class TaskMemoryManager:
    """任务内存管理器"""
    
    def __init__(self, memory_limit_mb: float = 1024.0):
        self.memory_limit_mb = memory_limit_mb
        self.monitor = MemoryMonitor()
        self._cleanup_callbacks = []
    
    def register_cleanup_callback(self, callback: Callable):
        """注册清理回调函数"""
        self._cleanup_callbacks.append(callback)
    
    def check_memory_limit(self) -> bool:
        """检查内存限制"""
        current_memory = self.monitor.get_memory_usage()
        if current_memory["rss_mb"] > self.memory_limit_mb:
            logger.warning(f"内存使用超限: {current_memory['rss_mb']:.1f}MB > {self.memory_limit_mb}MB")
            return False
        return True
    
    def cleanup_memory(self):
        """清理内存"""
        logger.info("开始内存清理...")
        
        # 执行注册的清理回调
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"清理回调失败: {e}")
        
        # 强制垃圾回收
        collected = gc.collect()
        
        # 获取清理后的内存使用
        memory_after = self.monitor.get_memory_usage()
        
        logger.info(f"内存清理完成: 回收了{collected}个对象, "
                   f"当前内存使用: {memory_after['rss_mb']:.1f}MB")
    
    @contextmanager
    def task_context(self, task_id: str, task_name: str):
        """任务上下文管理器"""
        # 任务开始前检查内存
        if not self.check_memory_limit():
            self.cleanup_memory()
        
        # 记录任务开始
        self.monitor.record_task_start(task_id, task_name)
        
        try:
            yield
            # 任务成功完成
            self.monitor.record_task_end(task_id, success=True)
        except Exception as e:
            # 任务失败
            self.monitor.record_task_end(task_id, success=False)
            logger.error(f"任务 {task_name} 执行失败: {e}")
            raise
        finally:
            # 任务结束后清理
            self.cleanup_memory()

# 全局内存管理器
_memory_manager = None
_manager_lock = threading.Lock()

def get_memory_manager() -> TaskMemoryManager:
    """获取全局内存管理器"""
    global _memory_manager
    
    if _memory_manager is None:
        with _manager_lock:
            if _memory_manager is None:
                # 根据可用内存设置限制
                try:
                    available_memory_gb = psutil.virtual_memory().available / (1024**3)
                    if available_memory_gb > 8:
                        memory_limit_mb = 2048.0
                    elif available_memory_gb > 4:
                        memory_limit_mb = 1024.0
                    else:
                        memory_limit_mb = 512.0
                except Exception:
                    memory_limit_mb = 1024.0
                
                _memory_manager = TaskMemoryManager(memory_limit_mb)
    
    return _memory_manager

def memory_optimized_task(func):
    """内存优化任务装饰器"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        task_id = self.request.id
        task_name = self.name
        
        memory_manager = get_memory_manager()
        
        with memory_manager.task_context(task_id, task_name):
            return func(self, *args, **kwargs)
    
    return wrapper

def create_optimized_celery_app(name: str, broker_url: str, backend_url: str) -> Celery:
    """创建内存优化的Celery应用"""
    
    app = Celery(name, broker=broker_url, backend=backend_url)
    
    # 优化的配置
    app.conf.update(
        # 基本配置
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        
        # 内存优化配置
        worker_max_tasks_per_child=100,  # 限制每个worker处理的任务数
        worker_max_memory_per_child=1024 * 1024,  # 限制每个worker的内存使用(KB)
        worker_prefetch_multiplier=1,  # 减少预取任务数
        task_acks_late=True,  # 延迟确认，确保任务完成后才确认
        worker_disable_rate_limits=False,  # 启用速率限制
        
        # 结果后端优化
        result_expires=3600,  # 结果过期时间1小时
        result_cache_max=1000,  # 结果缓存最大数量
        
        # 任务路由
        task_routes={
            "app.worker.process_audio_job": {"queue": "audio_processing"},
            "app.worker.analyze_features": {"queue": "audio_analyze"},
            "app.worker.invert_params": {"queue": "audio_invert"},
            "app.worker.render_audio": {"queue": "audio_render"},
        },
        
        # 队列配置
        task_default_queue="default",
        task_default_exchange="default",
        task_default_exchange_type="direct",
        task_default_routing_key="default",
    )
    
    return app

# Celery信号处理器
@worker_process_init.connect
def worker_process_init_handler(sender=None, **kwargs):
    """Worker进程初始化"""
    logger.info("Worker进程初始化，设置内存管理器")
    
    # 初始化内存管理器
    memory_manager = get_memory_manager()
    
    # 注册缓存清理回调
    try:
        from app.cache_optimized import get_optimized_cache
        cache = get_optimized_cache()
        memory_manager.register_cleanup_callback(lambda: cache.clear_namespace("task_temp"))
    except ImportError:
        pass
    
    # 注册容器清理回调
    try:
        from src.core.container_optimized import get_optimized_container
        container = get_optimized_container()
        memory_manager.register_cleanup_callback(lambda: container.clear_all_scopes())
    except ImportError:
        pass

@worker_process_shutdown.connect
def worker_process_shutdown_handler(sender=None, **kwargs):
    """Worker进程关闭"""
    logger.info("Worker进程关闭，清理资源")
    
    try:
        memory_manager = get_memory_manager()
        memory_manager.cleanup_memory()
    except Exception as e:
        logger.error(f"Worker关闭清理失败: {e}")

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """任务执行前处理"""
    logger.debug(f"任务开始: {task.name} ({task_id})")

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, 
                        retval=None, state=None, **kwds):
    """任务执行后处理"""
    logger.debug(f"任务完成: {task.name} ({task_id}), 状态: {state}")

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """任务失败处理"""
    logger.error(f"任务失败: {sender.name} ({task_id}), 异常: {exception}")
    
    # 任务失败时强制清理内存
    try:
        memory_manager = get_memory_manager()
        memory_manager.cleanup_memory()
    except Exception as e:
        logger.error(f"任务失败清理内存失败: {e}")

@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Worker准备就绪"""
    logger.info("Worker准备就绪，开始接收任务")
    
    # 输出内存统计
    try:
        memory_manager = get_memory_manager()
        stats = memory_manager.monitor.get_stats()
        logger.info(f"Worker内存统计: {stats}")
    except Exception as e:
        logger.error(f"获取内存统计失败: {e}")

@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Worker关闭"""
    logger.info("Worker关闭")

# 兼容性函数
def get_celery_app() -> Celery:
    """获取优化的Celery应用实例"""
    redis_url = os.getenv("QUEUE_URL", "redis://localhost:6379/0")
    return create_optimized_celery_app("audio_worker", redis_url, redis_url)

def get_memory_stats() -> Dict[str, Any]:
    """获取内存统计信息"""
    try:
        memory_manager = get_memory_manager()
        return memory_manager.monitor.get_stats()
    except Exception as e:
        logger.error(f"获取内存统计失败: {e}")
        return {"error": str(e)}
