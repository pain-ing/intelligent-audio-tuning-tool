"""
优化的音频处理流水线
支持并行处理、流式处理和智能调度
"""

import asyncio
import concurrent.futures
import threading
import queue
import time
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

from .performance_monitor import global_performance_monitor
from .audition_error_handler import global_error_handler

logger = logging.getLogger(__name__)


class ProcessingPriority(Enum):
    """处理优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AudioProcessingTask:
    """音频处理任务"""
    task_id: str
    input_path: str
    output_path: str
    style_params: Dict[str, Any]
    priority: ProcessingPriority = ProcessingPriority.NORMAL
    renderer_type: str = "default"
    use_streaming: Optional[bool] = None
    callback: Optional[Callable] = None
    
    # 状态信息
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    
    @property
    def duration(self) -> Optional[float]:
        """获取处理时长"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def wait_time(self) -> float:
        """获取等待时长"""
        start_time = self.started_at or time.time()
        return start_time - self.created_at


class AudioProcessingQueue:
    """音频处理队列"""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.queues = {
            ProcessingPriority.URGENT: queue.PriorityQueue(),
            ProcessingPriority.HIGH: queue.PriorityQueue(),
            ProcessingPriority.NORMAL: queue.PriorityQueue(),
            ProcessingPriority.LOW: queue.PriorityQueue()
        }
        self.tasks = {}  # task_id -> AudioProcessingTask
        self._lock = threading.Lock()
    
    def add_task(self, task: AudioProcessingTask) -> bool:
        """添加任务到队列"""
        with self._lock:
            if len(self.tasks) >= self.max_size:
                logger.warning("处理队列已满，拒绝新任务")
                return False
            
            # 使用负的创建时间作为优先级，确保先进先出
            priority_value = -task.created_at
            self.queues[task.priority].put((priority_value, task.task_id))
            self.tasks[task.task_id] = task
            
            logger.info(f"任务 {task.task_id} 已添加到 {task.priority.name} 优先级队列")
            return True
    
    def get_next_task(self) -> Optional[AudioProcessingTask]:
        """获取下一个待处理任务"""
        with self._lock:
            # 按优先级顺序检查队列
            for priority in [ProcessingPriority.URGENT, ProcessingPriority.HIGH, 
                           ProcessingPriority.NORMAL, ProcessingPriority.LOW]:
                try:
                    _, task_id = self.queues[priority].get_nowait()
                    task = self.tasks.get(task_id)
                    if task and task.status == TaskStatus.PENDING:
                        task.status = TaskStatus.RUNNING
                        task.started_at = time.time()
                        return task
                except queue.Empty:
                    continue
            
            return None
    
    def complete_task(self, task_id: str, result: Dict[str, Any]):
        """完成任务"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task:
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                task.result = result
                
                # 调用回调函数
                if task.callback:
                    try:
                        task.callback(task)
                    except Exception as e:
                        logger.error(f"任务回调执行失败: {e}")
    
    def fail_task(self, task_id: str, error_message: str):
        """标记任务失败"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task:
                task.status = TaskStatus.FAILED
                task.completed_at = time.time()
                task.error_message = error_message
                
                # 调用回调函数
                if task.callback:
                    try:
                        task.callback(task)
                    except Exception as e:
                        logger.error(f"任务回调执行失败: {e}")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        with self._lock:
            status = {
                "total_tasks": len(self.tasks),
                "queue_sizes": {},
                "status_counts": {status.value: 0 for status in TaskStatus}
            }
            
            # 统计各优先级队列大小
            for priority in ProcessingPriority:
                status["queue_sizes"][priority.name] = self.queues[priority].qsize()
            
            # 统计各状态任务数量
            for task in self.tasks.values():
                status["status_counts"][task.status.value] += 1
            
            return status


class AudioProcessingWorker:
    """音频处理工作器"""
    
    def __init__(self, worker_id: str, audio_renderer):
        self.worker_id = worker_id
        self.audio_renderer = audio_renderer
        self.running = False
        self.current_task = None
        self.processed_count = 0
        self.error_count = 0
        self.total_processing_time = 0.0
    
    async def start(self, task_queue: AudioProcessingQueue):
        """启动工作器"""
        self.running = True
        logger.info(f"音频处理工作器 {self.worker_id} 已启动")
        
        while self.running:
            try:
                # 获取下一个任务
                task = task_queue.get_next_task()
                if not task:
                    await asyncio.sleep(0.1)  # 没有任务时短暂休眠
                    continue
                
                self.current_task = task
                logger.info(f"工作器 {self.worker_id} 开始处理任务 {task.task_id}")
                
                # 处理任务
                start_time = time.time()
                try:
                    result = await self._process_task(task)
                    processing_time = time.time() - start_time
                    
                    # 更新统计
                    self.processed_count += 1
                    self.total_processing_time += processing_time
                    
                    # 完成任务
                    task_queue.complete_task(task.task_id, result)
                    logger.info(f"任务 {task.task_id} 处理完成，耗时 {processing_time:.2f}秒")
                    
                except Exception as e:
                    processing_time = time.time() - start_time
                    self.error_count += 1
                    
                    # 标记任务失败
                    task_queue.fail_task(task.task_id, str(e))
                    logger.error(f"任务 {task.task_id} 处理失败: {e}")
                
                finally:
                    self.current_task = None
                    
            except Exception as e:
                logger.error(f"工作器 {self.worker_id} 发生错误: {e}")
                await asyncio.sleep(1.0)  # 错误后稍长休眠
    
    async def _process_task(self, task: AudioProcessingTask) -> Dict[str, Any]:
        """处理单个任务"""
        # 在线程池中执行音频处理（因为音频处理是CPU密集型）
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor,
                self.audio_renderer.render_audio,
                task.input_path,
                task.output_path,
                task.style_params,
                task.use_streaming
            )
        
        return result
    
    def stop(self):
        """停止工作器"""
        self.running = False
        logger.info(f"音频处理工作器 {self.worker_id} 已停止")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取工作器统计信息"""
        avg_processing_time = 0.0
        if self.processed_count > 0:
            avg_processing_time = self.total_processing_time / self.processed_count
        
        return {
            "worker_id": self.worker_id,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "avg_processing_time": avg_processing_time,
            "current_task": self.current_task.task_id if self.current_task else None,
            "success_rate": (self.processed_count / max(self.processed_count + self.error_count, 1)) * 100
        }


class AudioProcessingPipeline:
    """音频处理流水线"""
    
    def __init__(self, audio_renderer, max_workers: int = 4, queue_size: int = 100):
        self.audio_renderer = audio_renderer
        self.max_workers = max_workers
        self.task_queue = AudioProcessingQueue(max_size=queue_size)
        self.workers = []
        self.running = False
        self._lock = threading.Lock()
    
    async def start(self):
        """启动流水线"""
        with self._lock:
            if self.running:
                return
            
            self.running = True
            
            # 创建并启动工作器
            for i in range(self.max_workers):
                worker = AudioProcessingWorker(f"worker_{i}", self.audio_renderer)
                self.workers.append(worker)
                
                # 在后台启动工作器
                asyncio.create_task(worker.start(self.task_queue))
            
            logger.info(f"音频处理流水线已启动，{self.max_workers} 个工作器")
    
    async def stop(self):
        """停止流水线"""
        with self._lock:
            if not self.running:
                return
            
            self.running = False
            
            # 停止所有工作器
            for worker in self.workers:
                worker.stop()
            
            self.workers.clear()
            logger.info("音频处理流水线已停止")
    
    def submit_task(self, task: AudioProcessingTask) -> bool:
        """提交处理任务"""
        if not self.running:
            logger.error("流水线未启动，无法提交任务")
            return False
        
        return self.task_queue.add_task(task)
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """获取流水线状态"""
        queue_status = self.task_queue.get_queue_status()
        worker_stats = [worker.get_stats() for worker in self.workers]
        
        # 计算总体统计
        total_processed = sum(stats["processed_count"] for stats in worker_stats)
        total_errors = sum(stats["error_count"] for stats in worker_stats)
        avg_success_rate = sum(stats["success_rate"] for stats in worker_stats) / len(worker_stats) if worker_stats else 0
        
        return {
            "running": self.running,
            "worker_count": len(self.workers),
            "queue_status": queue_status,
            "worker_stats": worker_stats,
            "total_processed": total_processed,
            "total_errors": total_errors,
            "overall_success_rate": avg_success_rate,
            "active_tasks": sum(1 for stats in worker_stats if stats["current_task"])
        }
    
    async def process_batch(self, tasks: List[AudioProcessingTask]) -> List[Dict[str, Any]]:
        """批量处理任务"""
        if not self.running:
            await self.start()
        
        # 提交所有任务
        submitted_tasks = []
        for task in tasks:
            if self.submit_task(task):
                submitted_tasks.append(task)
            else:
                logger.warning(f"任务 {task.task_id} 提交失败")
        
        # 等待所有任务完成
        results = []
        while submitted_tasks:
            completed_tasks = []
            for task in submitted_tasks:
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    completed_tasks.append(task)
                    if task.status == TaskStatus.COMPLETED:
                        results.append(task.result)
                    else:
                        results.append({"error": task.error_message})
            
            # 移除已完成的任务
            for task in completed_tasks:
                submitted_tasks.remove(task)
            
            if submitted_tasks:
                await asyncio.sleep(0.1)  # 短暂等待
        
        return results


# 全局音频处理流水线实例
global_audio_pipeline = None


def get_audio_pipeline(audio_renderer=None) -> AudioProcessingPipeline:
    """获取全局音频处理流水线"""
    global global_audio_pipeline
    
    if global_audio_pipeline is None and audio_renderer:
        global_audio_pipeline = AudioProcessingPipeline(audio_renderer)
    
    return global_audio_pipeline
