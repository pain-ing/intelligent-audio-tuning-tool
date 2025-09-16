"""
批处理进度跟踪器
"""

import time
import threading
import logging
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
from collections import deque

from .batch_models import BatchTask, BatchProgress, BatchStatus, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class ProgressEvent:
    """进度事件"""
    event_type: str
    batch_id: str
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)


class ProgressTracker:
    """批处理进度跟踪器"""
    
    def __init__(self, batch_id: str, total_tasks: int):
        self.batch_id = batch_id
        self.total_tasks = total_tasks
        self.progress = BatchProgress(batch_id=batch_id, total_tasks=total_tasks)
        
        # 任务状态跟踪
        self.tasks: Dict[str, BatchTask] = {}
        self.task_history: deque = deque(maxlen=1000)  # 保留最近1000个任务的历史
        
        # 回调函数
        self.progress_callbacks: List[Callable[[BatchProgress], None]] = []
        self.event_callbacks: List[Callable[[ProgressEvent], None]] = []
        
        # 线程安全
        self._lock = threading.RLock()
        
        # 性能统计
        self.processing_times: deque = deque(maxlen=100)  # 保留最近100个任务的处理时间
        
        logger.info(f"创建进度跟踪器: batch_id={batch_id}, total_tasks={total_tasks}")
    
    def add_task(self, task: BatchTask):
        """添加任务到跟踪器"""
        with self._lock:
            self.tasks[task.task_id] = task
            self._emit_event("task_added", {"task_id": task.task_id})
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          error_message: Optional[str] = None,
                          processing_time: Optional[float] = None):
        """更新任务状态"""
        with self._lock:
            if task_id not in self.tasks:
                logger.warning(f"任务不存在: {task_id}")
                return
            
            task = self.tasks[task_id]
            old_status = task.status
            task.status = status
            
            if error_message:
                task.error_message = error_message
            
            if processing_time:
                task.processing_time = processing_time
                self.processing_times.append(processing_time)
            
            # 更新任务历史
            self.task_history.append({
                "task_id": task_id,
                "old_status": old_status.value,
                "new_status": status.value,
                "timestamp": time.time(),
                "processing_time": processing_time
            })
            
            # 更新整体进度
            self._update_progress()
            
            # 发送事件
            self._emit_event("task_status_changed", {
                "task_id": task_id,
                "old_status": old_status.value,
                "new_status": status.value,
                "processing_time": processing_time
            })
            
            logger.debug(f"任务状态更新: {task_id} {old_status.value} -> {status.value}")
    
    def _update_progress(self):
        """更新整体进度"""
        completed = sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED)
        failed = sum(1 for task in self.tasks.values() if task.status == TaskStatus.FAILED)
        cancelled = sum(1 for task in self.tasks.values() if task.status == TaskStatus.CANCELLED)
        
        # 计算平均处理时间
        avg_time = 0.0
        if self.processing_times:
            avg_time = sum(self.processing_times) / len(self.processing_times)
        
        # 更新进度
        self.progress.update_progress(completed, failed, cancelled, avg_time)
        
        # 通知回调
        for callback in self.progress_callbacks:
            try:
                callback(self.progress)
            except Exception as e:
                logger.error(f"进度回调执行失败: {e}")
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """发送进度事件"""
        event = ProgressEvent(
            event_type=event_type,
            batch_id=self.batch_id,
            data=data
        )
        
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"事件回调执行失败: {e}")
    
    def register_progress_callback(self, callback: Callable[[BatchProgress], None]):
        """注册进度回调"""
        self.progress_callbacks.append(callback)
    
    def register_event_callback(self, callback: Callable[[ProgressEvent], None]):
        """注册事件回调"""
        self.event_callbacks.append(callback)
    
    def get_progress(self) -> BatchProgress:
        """获取当前进度"""
        with self._lock:
            return self.progress
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        with self._lock:
            task = self.tasks.get(task_id)
            return task.status if task else None
    
    def get_failed_tasks(self) -> List[BatchTask]:
        """获取失败的任务"""
        with self._lock:
            return [task for task in self.tasks.values() if task.status == TaskStatus.FAILED]
    
    def get_completed_tasks(self) -> List[BatchTask]:
        """获取完成的任务"""
        with self._lock:
            return [task for task in self.tasks.values() if task.status == TaskStatus.COMPLETED]
    
    def get_processing_tasks(self) -> List[BatchTask]:
        """获取正在处理的任务"""
        with self._lock:
            return [task for task in self.tasks.values() if task.status == TaskStatus.PROCESSING]
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        with self._lock:
            stats = {
                "total_tasks": self.total_tasks,
                "pending": sum(1 for task in self.tasks.values() if task.status == TaskStatus.PENDING),
                "processing": sum(1 for task in self.tasks.values() if task.status == TaskStatus.PROCESSING),
                "completed": sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED),
                "failed": sum(1 for task in self.tasks.values() if task.status == TaskStatus.FAILED),
                "cancelled": sum(1 for task in self.tasks.values() if task.status == TaskStatus.CANCELLED),
                "retrying": sum(1 for task in self.tasks.values() if task.status == TaskStatus.RETRYING),
            }
            
            # 性能统计
            if self.processing_times:
                stats["avg_processing_time"] = sum(self.processing_times) / len(self.processing_times)
                stats["min_processing_time"] = min(self.processing_times)
                stats["max_processing_time"] = max(self.processing_times)
            else:
                stats["avg_processing_time"] = 0.0
                stats["min_processing_time"] = 0.0
                stats["max_processing_time"] = 0.0
            
            # 错误统计
            error_counts = {}
            for task in self.tasks.values():
                if task.status == TaskStatus.FAILED and task.error_message:
                    error_counts[task.error_message] = error_counts.get(task.error_message, 0) + 1
            stats["error_breakdown"] = error_counts
            
            return stats
    
    def get_recent_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的任务历史"""
        with self._lock:
            return list(self.task_history)[-limit:]
    
    def estimate_completion_time(self) -> Optional[float]:
        """估算完成时间"""
        with self._lock:
            if self.progress.current_processing_speed > 0 and self.progress.pending_tasks > 0:
                remaining_time = self.progress.pending_tasks / self.progress.current_processing_speed
                return time.time() + remaining_time
            return None
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """获取性能指标"""
        with self._lock:
            metrics = {
                "progress_percentage": self.progress.progress_percentage,
                "success_rate": self.progress.success_rate,
                "processing_speed": self.progress.current_processing_speed,
                "elapsed_time": self.progress.elapsed_time,
                "estimated_remaining_time": 0.0
            }
            
            # 估算剩余时间
            completion_time = self.estimate_completion_time()
            if completion_time:
                metrics["estimated_remaining_time"] = completion_time - time.time()
            
            return metrics
    
    def reset(self):
        """重置跟踪器"""
        with self._lock:
            self.tasks.clear()
            self.task_history.clear()
            self.processing_times.clear()
            self.progress = BatchProgress(batch_id=self.batch_id, total_tasks=self.total_tasks)
            logger.info(f"进度跟踪器已重置: {self.batch_id}")


class GlobalProgressManager:
    """全局进度管理器"""
    
    def __init__(self):
        self.trackers: Dict[str, ProgressTracker] = {}
        self._lock = threading.RLock()
    
    def create_tracker(self, batch_id: str, total_tasks: int) -> ProgressTracker:
        """创建进度跟踪器"""
        with self._lock:
            tracker = ProgressTracker(batch_id, total_tasks)
            self.trackers[batch_id] = tracker
            return tracker
    
    def get_tracker(self, batch_id: str) -> Optional[ProgressTracker]:
        """获取进度跟踪器"""
        with self._lock:
            return self.trackers.get(batch_id)
    
    def remove_tracker(self, batch_id: str):
        """移除进度跟踪器"""
        with self._lock:
            if batch_id in self.trackers:
                del self.trackers[batch_id]
                logger.info(f"移除进度跟踪器: {batch_id}")
    
    def get_all_progress(self) -> Dict[str, BatchProgress]:
        """获取所有批处理的进度"""
        with self._lock:
            return {batch_id: tracker.get_progress() 
                   for batch_id, tracker in self.trackers.items()}
    
    def cleanup_completed_trackers(self, max_age_hours: float = 24.0):
        """清理已完成的跟踪器"""
        with self._lock:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            to_remove = []
            for batch_id, tracker in self.trackers.items():
                progress = tracker.get_progress()
                if (progress.completed_tasks + progress.failed_tasks + progress.cancelled_tasks == progress.total_tasks):
                    # 批处理已完成
                    age = current_time - progress.started_at
                    if age > max_age_seconds:
                        to_remove.append(batch_id)
            
            for batch_id in to_remove:
                del self.trackers[batch_id]
                logger.info(f"清理已完成的跟踪器: {batch_id}")


# 全局进度管理器实例
global_progress_manager = GlobalProgressManager()
