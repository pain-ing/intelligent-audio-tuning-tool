"""
本地任务队列实现（桌面模式）
替代 Celery + Redis 的轻量级任务队列
"""

import os
import json
import time
import uuid
import logging
import threading
from typing import Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, asdict
from enum import Enum
import queue

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    CANCELLED = "CANCELLED"


@dataclass
class Task:
    id: str
    func_name: str
    args: list
    kwargs: dict
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = None
    created_at: float = None
    started_at: float = None
    completed_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


class LocalTaskQueue:
    """本地任务队列"""
    
    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks: Dict[str, Task] = {}
        self.futures: Dict[str, Future] = {}
        self.task_registry: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        
        # 持久化目录
        appdata = os.getenv("APPDATA")
        if appdata:
            self.state_dir = os.path.join(appdata, "AudioTuner", "queue")
        else:
            self.state_dir = os.path.join(os.path.expanduser("~"), ".audio_tuner", "queue")
        
        try:
            os.makedirs(self.state_dir, exist_ok=True)
        except Exception:
            pass
        
        logger.info(f"Local task queue initialized with {max_workers} workers")
    
    def register_task(self, name: str, func: Callable):
        """注册任务函数"""
        self.task_registry[name] = func
        logger.debug(f"Registered task: {name}")
    
    def submit_task(self, func_name: str, *args, **kwargs) -> str:
        """提交任务"""
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            func_name=func_name,
            args=list(args),
            kwargs=kwargs
        )
        
        with self._lock:
            self.tasks[task_id] = task
        
        # 提交到线程池
        if func_name in self.task_registry:
            future = self.executor.submit(self._execute_task, task_id)
            self.futures[task_id] = future
        else:
            task.status = TaskStatus.FAILURE
            task.error = f"Unknown task: {func_name}"
            task.completed_at = time.time()
        
        logger.info(f"Submitted task {task_id}: {func_name}")
        return task_id
    
    def _execute_task(self, task_id: str):
        """执行任务"""
        with self._lock:
            task = self.tasks.get(task_id)
        
        if not task:
            return
        
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            
            func = self.task_registry[task.func_name]
            result = func(*task.args, **task.kwargs)
            
            task.status = TaskStatus.SUCCESS
            task.result = result
            task.completed_at = time.time()
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            task.status = TaskStatus.FAILURE
            task.error = str(e)
            task.completed_at = time.time()
            
            logger.error(f"Task {task_id} failed: {e}")
        
        finally:
            # 清理future引用
            self.futures.pop(task_id, None)
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        with self._lock:
            task = self.tasks.get(task_id)
        
        if not task:
            return None
        
        return {
            "id": task.id,
            "status": task.status.value,
            "result": task.result,
            "error": task.error,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at
        }
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        future = self.futures.get(task_id)
        if future and not future.done():
            cancelled = future.cancel()
            if cancelled:
                with self._lock:
                    task = self.tasks.get(task_id)
                    if task:
                        task.status = TaskStatus.CANCELLED
                        task.completed_at = time.time()
                logger.info(f"Task {task_id} cancelled")
                return True
        return False
    
    def list_tasks(self, status: Optional[TaskStatus] = None) -> list:
        """列出任务"""
        with self._lock:
            tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        return [self.get_task_status(t.id) for t in tasks]
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """清理已完成的任务"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        with self._lock:
            to_remove = []
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.CANCELLED] 
                    and task.completed_at and task.completed_at < cutoff_time):
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                del self.tasks[task_id]
        
        logger.info(f"Cleaned up {len(to_remove)} old tasks")
    
    def shutdown(self):
        """关闭队列"""
        logger.info("Shutting down local task queue")
        self.executor.shutdown(wait=True)


# 全局任务队列实例
_queue = None


def get_task_queue() -> LocalTaskQueue:
    """获取任务队列实例"""
    global _queue
    if _queue is None:
        _queue = LocalTaskQueue()
    return _queue


def register_task(name: str):
    """任务注册装饰器"""
    def decorator(func: Callable):
        get_task_queue().register_task(name, func)
        return func
    return decorator


def submit_task(func_name: str, *args, **kwargs) -> str:
    """提交任务"""
    return get_task_queue().submit_task(func_name, *args, **kwargs)


def get_task_status(task_id: str) -> Optional[Dict]:
    """获取任务状态"""
    return get_task_queue().get_task_status(task_id)


def cancel_task(task_id: str) -> bool:
    """取消任务"""
    return get_task_queue().cancel_task(task_id)
