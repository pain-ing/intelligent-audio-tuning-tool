"""
批处理管理器
"""

import os
import time
import uuid
import logging
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Callable, Any
from pathlib import Path

from .batch_models import (
    BatchTask, BatchResult, BatchConfiguration, BatchStatus, 
    TaskStatus, AudioProcessingParams
)
from .batch_progress import ProgressTracker, global_progress_manager
from .audio_rendering import AudioRenderer
from .performance_monitor import global_performance_monitor
from .audition_error_handler import global_error_handler

logger = logging.getLogger(__name__)


class BatchProcessor:
    """批处理管理器"""
    
    def __init__(self, config: Optional[BatchConfiguration] = None):
        self.config = config or BatchConfiguration()
        self.audio_renderer = AudioRenderer()
        
        # 批处理状态
        self.active_batches: Dict[str, Dict[str, Any]] = {}
        self.batch_results: Dict[str, BatchResult] = {}
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_tasks)
        
        # 线程安全
        self._lock = threading.RLock()
        
        # 回调函数
        self.batch_callbacks: Dict[str, List[Callable]] = {
            "on_batch_start": [],
            "on_batch_complete": [],
            "on_task_complete": [],
            "on_task_failed": []
        }
        
        logger.info(f"批处理管理器初始化完成，最大并发任务数: {self.config.max_concurrent_tasks}")
    
    def submit_batch(self, tasks: List[BatchTask], 
                    batch_id: Optional[str] = None) -> str:
        """提交批处理任务"""
        if not tasks:
            raise ValueError("任务列表不能为空")
        
        batch_id = batch_id or str(uuid.uuid4())
        
        with self._lock:
            if batch_id in self.active_batches:
                raise ValueError(f"批处理ID已存在: {batch_id}")
            
            # 创建进度跟踪器
            tracker = global_progress_manager.create_tracker(batch_id, len(tasks))
            
            # 添加任务到跟踪器
            for task in tasks:
                tracker.add_task(task)
            
            # 初始化批处理状态
            self.active_batches[batch_id] = {
                "status": BatchStatus.CREATED,
                "tasks": {task.task_id: task for task in tasks},
                "tracker": tracker,
                "start_time": time.time(),
                "futures": {}
            }
            
            logger.info(f"提交批处理任务: batch_id={batch_id}, 任务数={len(tasks)}")
            
            return batch_id
    
    def start_batch(self, batch_id: str) -> bool:
        """开始执行批处理"""
        with self._lock:
            if batch_id not in self.active_batches:
                logger.error(f"批处理不存在: {batch_id}")
                return False
            
            batch_info = self.active_batches[batch_id]
            if batch_info["status"] != BatchStatus.CREATED:
                logger.error(f"批处理状态不正确: {batch_id}, 当前状态: {batch_info['status']}")
                return False
            
            # 更新状态
            batch_info["status"] = BatchStatus.RUNNING
            batch_info["start_time"] = time.time()
            
            # 触发开始回调
            self._trigger_callbacks("on_batch_start", batch_id)
            
            # 提交任务到线程池
            tasks = list(batch_info["tasks"].values())
            futures = {}
            
            for task in tasks:
                future = self.executor.submit(self._process_single_task, batch_id, task)
                futures[future] = task.task_id
            
            batch_info["futures"] = futures
            
            # 启动监控线程
            monitor_thread = threading.Thread(
                target=self._monitor_batch,
                args=(batch_id,),
                daemon=True
            )
            monitor_thread.start()
            
            logger.info(f"开始执行批处理: {batch_id}")
            return True
    
    def _process_single_task(self, batch_id: str, task: BatchTask) -> bool:
        """处理单个任务"""
        task_id = task.task_id
        
        try:
            # 更新任务状态为处理中
            tracker = self.active_batches[batch_id]["tracker"]
            tracker.update_task_status(task_id, TaskStatus.PROCESSING)
            
            # 开始性能监控
            with global_performance_monitor.monitor_session(
                session_id=f"{batch_id}_{task_id}",
                operation_type="batch_audio_processing"
            ) as session:
                
                # 设置输入大小
                if os.path.exists(task.input_path):
                    session.input_size = os.path.getsize(task.input_path)
                
                # 执行音频处理
                start_time = time.time()
                
                # 检查输入文件
                if not os.path.exists(task.input_path):
                    raise FileNotFoundError(f"输入文件不存在: {task.input_path}")
                
                # 创建输出目录
                output_dir = os.path.dirname(task.output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                
                # 执行音频渲染
                result = self.audio_renderer.render_audio(
                    input_path=task.input_path,
                    output_path=task.output_path,
                    style_params=task.processing_params.style_params
                )
                
                processing_time = time.time() - start_time
                
                # 获取输出文件大小
                output_size = None
                if os.path.exists(task.output_path):
                    output_size = os.path.getsize(task.output_path)
                    session.output_size = output_size
                
                # 标记任务完成
                task.complete_successfully(
                    processing_time=processing_time,
                    output_size=output_size,
                    quality_metrics=result.get("quality_metrics")
                )
                
                # 更新跟踪器
                tracker.update_task_status(
                    task_id, 
                    TaskStatus.COMPLETED,
                    processing_time=processing_time
                )
                
                # 触发任务完成回调
                self._trigger_callbacks("on_task_complete", batch_id, task)
                
                logger.debug(f"任务处理完成: {task_id}, 耗时: {processing_time:.2f}秒")
                return True
                
        except Exception as e:
            # 处理错误
            error_message = str(e)
            logger.error(f"任务处理失败: {task_id}, 错误: {error_message}")
            
            # 使用全局错误处理器
            error_context = global_error_handler.handle_error(
                e, f"batch_task_{task_id}", {"batch_id": batch_id, "task_id": task_id}
            )
            
            # 标记任务失败
            task.fail_with_error(error_message, {"error_context": error_context})
            
            # 更新跟踪器
            tracker.update_task_status(task_id, TaskStatus.FAILED, error_message)
            
            # 检查是否可以重试
            if task.can_retry and self.config.auto_retry_failed_tasks:
                logger.info(f"任务将重试: {task_id}, 重试次数: {task.retry_count + 1}")
                task.retry()
                tracker.update_task_status(task_id, TaskStatus.RETRYING)
                
                # 延迟后重新提交任务
                time.sleep(self.config.retry_delay)
                future = self.executor.submit(self._process_single_task, batch_id, task)
                self.active_batches[batch_id]["futures"][future] = task_id
            else:
                # 触发任务失败回调
                self._trigger_callbacks("on_task_failed", batch_id, task)
            
            return False
    
    def _monitor_batch(self, batch_id: str):
        """监控批处理进度"""
        batch_info = self.active_batches[batch_id]
        futures = batch_info["futures"]
        
        try:
            # 等待所有任务完成
            for future in as_completed(futures.keys()):
                task_id = futures[future]
                try:
                    success = future.result()
                    logger.debug(f"任务完成: {task_id}, 成功: {success}")
                except Exception as e:
                    logger.error(f"任务执行异常: {task_id}, 错误: {e}")
            
            # 所有任务完成，生成结果
            self._finalize_batch(batch_id)
            
        except Exception as e:
            logger.error(f"批处理监控异常: {batch_id}, 错误: {e}")
            self._finalize_batch(batch_id, BatchStatus.FAILED)
    
    def _finalize_batch(self, batch_id: str, 
                       final_status: Optional[BatchStatus] = None):
        """完成批处理"""
        with self._lock:
            if batch_id not in self.active_batches:
                return
            
            batch_info = self.active_batches[batch_id]
            tracker = batch_info["tracker"]
            
            # 获取最终统计
            stats = tracker.get_task_statistics()
            progress = tracker.get_progress()
            
            # 确定最终状态
            if final_status is None:
                if stats["failed"] == 0:
                    final_status = BatchStatus.COMPLETED
                elif stats["completed"] > 0:
                    final_status = BatchStatus.COMPLETED  # 部分成功也算完成
                else:
                    final_status = BatchStatus.FAILED
            
            # 创建批处理结果
            result = BatchResult(
                batch_id=batch_id,
                status=final_status,
                total_tasks=stats["total_tasks"],
                completed_tasks=stats["completed"],
                failed_tasks=stats["failed"],
                cancelled_tasks=stats["cancelled"],
                started_at=batch_info["start_time"],
                completed_at=time.time(),
                average_task_time=stats["avg_processing_time"]
            )
            
            # 添加失败任务详情
            for task in tracker.get_failed_tasks():
                result.add_failed_task(task)
            
            # 保存结果
            self.batch_results[batch_id] = result
            
            # 更新批处理状态
            batch_info["status"] = final_status
            
            # 触发完成回调
            self._trigger_callbacks("on_batch_complete", batch_id, result)
            
            logger.info(f"批处理完成: {batch_id}, 状态: {final_status.value}, "
                       f"成功: {stats['completed']}, 失败: {stats['failed']}")
    
    def _trigger_callbacks(self, event_type: str, *args):
        """触发回调函数"""
        for callback in self.batch_callbacks.get(event_type, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"回调执行失败: {event_type}, 错误: {e}")
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """获取批处理状态"""
        with self._lock:
            if batch_id not in self.active_batches:
                # 检查是否在结果中
                if batch_id in self.batch_results:
                    result = self.batch_results[batch_id]
                    return {
                        "batch_id": batch_id,
                        "status": result.status.value,
                        "progress": {
                            "total_tasks": result.total_tasks,
                            "completed_tasks": result.completed_tasks,
                            "failed_tasks": result.failed_tasks,
                            "cancelled_tasks": result.cancelled_tasks,
                            "progress_percentage": result.success_rate
                        }
                    }
                return None
            
            batch_info = self.active_batches[batch_id]
            tracker = batch_info["tracker"]
            progress = tracker.get_progress()
            
            return {
                "batch_id": batch_id,
                "status": batch_info["status"].value,
                "progress": {
                    "total_tasks": progress.total_tasks,
                    "completed_tasks": progress.completed_tasks,
                    "failed_tasks": progress.failed_tasks,
                    "cancelled_tasks": progress.cancelled_tasks,
                    "pending_tasks": progress.pending_tasks,
                    "progress_percentage": progress.progress_percentage,
                    "success_rate": progress.success_rate,
                    "elapsed_time": progress.elapsed_time,
                    "estimated_completion": progress.estimated_completion,
                    "current_processing_speed": progress.current_processing_speed
                }
            }
    
    def cancel_batch(self, batch_id: str) -> bool:
        """取消批处理"""
        with self._lock:
            if batch_id not in self.active_batches:
                logger.error(f"批处理不存在: {batch_id}")
                return False
            
            batch_info = self.active_batches[batch_id]
            
            # 取消所有未完成的任务
            for future in batch_info["futures"].keys():
                future.cancel()
            
            # 更新状态
            batch_info["status"] = BatchStatus.CANCELLED
            
            # 标记所有未完成任务为取消
            tracker = batch_info["tracker"]
            for task in batch_info["tasks"].values():
                if not task.is_completed:
                    task.cancel()
                    tracker.update_task_status(task.task_id, TaskStatus.CANCELLED)
            
            # 完成批处理
            self._finalize_batch(batch_id, BatchStatus.CANCELLED)
            
            logger.info(f"批处理已取消: {batch_id}")
            return True
    
    def get_batch_result(self, batch_id: str) -> Optional[BatchResult]:
        """获取批处理结果"""
        return self.batch_results.get(batch_id)
    
    def register_callback(self, event_type: str, callback: Callable):
        """注册回调函数"""
        if event_type in self.batch_callbacks:
            self.batch_callbacks[event_type].append(callback)
        else:
            logger.warning(f"未知的事件类型: {event_type}")
    
    def cleanup_completed_batches(self, max_age_hours: float = 24.0):
        """清理已完成的批处理"""
        with self._lock:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            to_remove = []
            for batch_id, result in self.batch_results.items():
                if result.completed_at and (current_time - result.completed_at) > max_age_seconds:
                    to_remove.append(batch_id)
            
            for batch_id in to_remove:
                del self.batch_results[batch_id]
                if batch_id in self.active_batches:
                    del self.active_batches[batch_id]
                global_progress_manager.remove_tracker(batch_id)
                logger.info(f"清理已完成的批处理: {batch_id}")
    
    def shutdown(self):
        """关闭批处理管理器"""
        logger.info("正在关闭批处理管理器...")
        self.executor.shutdown(wait=True)
        logger.info("批处理管理器已关闭")


# 全局批处理管理器实例
global_batch_processor = BatchProcessor()
