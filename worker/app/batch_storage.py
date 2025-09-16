"""
批处理状态持久化
"""

import os
import json
import pickle
import sqlite3
import logging
import threading
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta

from .batch_models import BatchTask, BatchResult, BatchStatus, TaskStatus

logger = logging.getLogger(__name__)


class BatchStorage:
    """批处理状态持久化存储"""
    
    def __init__(self, storage_dir: str = "data/batch_storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据库文件
        self.db_path = self.storage_dir / "batch_data.db"
        
        # 线程安全
        self._lock = threading.RLock()
        
        # 初始化数据库
        self._init_database()
        
        logger.info(f"批处理存储初始化完成: {self.storage_dir}")
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建批处理表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batches (
                    batch_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    total_tasks INTEGER NOT NULL,
                    completed_tasks INTEGER DEFAULT 0,
                    failed_tasks INTEGER DEFAULT 0,
                    cancelled_tasks INTEGER DEFAULT 0,
                    started_at REAL NOT NULL,
                    completed_at REAL,
                    config_json TEXT,
                    result_json TEXT,
                    created_at REAL DEFAULT (julianday('now'))
                )
            """)
            
            # 创建任务表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    input_path TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER DEFAULT 2,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    completed_at REAL,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    error_message TEXT,
                    processing_time REAL,
                    output_size INTEGER,
                    params_json TEXT,
                    FOREIGN KEY (batch_id) REFERENCES batches (batch_id)
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_batch_id ON tasks (batch_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_batches_status ON batches (status)")
            
            conn.commit()
    
    def save_batch(self, batch_id: str, status: BatchStatus, 
                  total_tasks: int, config: Optional[Dict] = None):
        """保存批处理信息"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    config_json = json.dumps(config) if config else None
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO batches 
                        (batch_id, status, total_tasks, started_at, config_json)
                        VALUES (?, ?, ?, ?, ?)
                    """, (batch_id, status.value, total_tasks, 
                         datetime.now().timestamp(), config_json))
                    
                    conn.commit()
                    logger.debug(f"保存批处理: {batch_id}")
                    
            except Exception as e:
                logger.error(f"保存批处理失败: {batch_id}, 错误: {e}")
    
    def update_batch_status(self, batch_id: str, status: BatchStatus,
                           completed_tasks: int = 0, failed_tasks: int = 0,
                           cancelled_tasks: int = 0):
        """更新批处理状态"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    completed_at = None
                    if status in [BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED]:
                        completed_at = datetime.now().timestamp()
                    
                    cursor.execute("""
                        UPDATE batches 
                        SET status = ?, completed_tasks = ?, failed_tasks = ?, 
                            cancelled_tasks = ?, completed_at = ?
                        WHERE batch_id = ?
                    """, (status.value, completed_tasks, failed_tasks, 
                         cancelled_tasks, completed_at, batch_id))
                    
                    conn.commit()
                    logger.debug(f"更新批处理状态: {batch_id} -> {status.value}")
                    
            except Exception as e:
                logger.error(f"更新批处理状态失败: {batch_id}, 错误: {e}")
    
    def save_task(self, task: BatchTask, batch_id: str):
        """保存任务信息"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    params_json = json.dumps({
                        "style_params": task.processing_params.style_params,
                        "output_format": task.processing_params.output_format,
                        "output_quality": task.processing_params.output_quality,
                        "normalize_audio": task.processing_params.normalize_audio,
                        "apply_effects": task.processing_params.apply_effects,
                        "use_audition": task.processing_params.use_audition
                    })
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO tasks 
                        (task_id, batch_id, input_path, output_path, status, priority,
                         created_at, started_at, completed_at, retry_count, max_retries,
                         error_message, processing_time, output_size, params_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        task.task_id, batch_id, task.input_path, task.output_path,
                        task.status.value, task.priority.value, task.created_at,
                        task.started_at, task.completed_at, task.retry_count,
                        task.max_retries, task.error_message, task.processing_time,
                        task.output_size, params_json
                    ))
                    
                    conn.commit()
                    logger.debug(f"保存任务: {task.task_id}")
                    
            except Exception as e:
                logger.error(f"保存任务失败: {task.task_id}, 错误: {e}")
    
    def update_task_status(self, task_id: str, status: TaskStatus,
                          error_message: Optional[str] = None,
                          processing_time: Optional[float] = None,
                          output_size: Optional[int] = None):
        """更新任务状态"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # 设置时间戳
                    started_at = None
                    completed_at = None
                    
                    if status == TaskStatus.PROCESSING:
                        started_at = datetime.now().timestamp()
                    elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                        completed_at = datetime.now().timestamp()
                    
                    cursor.execute("""
                        UPDATE tasks 
                        SET status = ?, started_at = COALESCE(?, started_at),
                            completed_at = ?, error_message = ?,
                            processing_time = ?, output_size = ?
                        WHERE task_id = ?
                    """, (status.value, started_at, completed_at, 
                         error_message, processing_time, output_size, task_id))
                    
                    conn.commit()
                    logger.debug(f"更新任务状态: {task_id} -> {status.value}")
                    
            except Exception as e:
                logger.error(f"更新任务状态失败: {task_id}, 错误: {e}")
    
    def save_batch_result(self, result: BatchResult):
        """保存批处理结果"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    result_json = json.dumps({
                        "total_processing_time": result.total_processing_time,
                        "average_task_time": result.average_task_time,
                        "total_input_size": result.total_input_size,
                        "total_output_size": result.total_output_size,
                        "quality_metrics": result.quality_metrics,
                        "error_summary": result.error_summary,
                        "failed_tasks_details": result.failed_tasks_details
                    })
                    
                    cursor.execute("""
                        UPDATE batches 
                        SET result_json = ?
                        WHERE batch_id = ?
                    """, (result_json, result.batch_id))
                    
                    conn.commit()
                    logger.debug(f"保存批处理结果: {result.batch_id}")
                    
            except Exception as e:
                logger.error(f"保存批处理结果失败: {result.batch_id}, 错误: {e}")
    
    def load_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """加载批处理信息"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT * FROM batches WHERE batch_id = ?
                    """, (batch_id,))
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    columns = [desc[0] for desc in cursor.description]
                    batch_data = dict(zip(columns, row))
                    
                    # 解析JSON字段
                    if batch_data["config_json"]:
                        batch_data["config"] = json.loads(batch_data["config_json"])
                    if batch_data["result_json"]:
                        batch_data["result"] = json.loads(batch_data["result_json"])
                    
                    return batch_data
                    
            except Exception as e:
                logger.error(f"加载批处理失败: {batch_id}, 错误: {e}")
                return None
    
    def load_batch_tasks(self, batch_id: str) -> List[Dict[str, Any]]:
        """加载批处理的所有任务"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT * FROM tasks WHERE batch_id = ?
                        ORDER BY created_at
                    """, (batch_id,))
                    
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    
                    tasks = []
                    for row in rows:
                        task_data = dict(zip(columns, row))
                        
                        # 解析参数JSON
                        if task_data["params_json"]:
                            task_data["params"] = json.loads(task_data["params_json"])
                        
                        tasks.append(task_data)
                    
                    return tasks
                    
            except Exception as e:
                logger.error(f"加载批处理任务失败: {batch_id}, 错误: {e}")
                return []
    
    def get_batch_list(self, status: Optional[BatchStatus] = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """获取批处理列表"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    if status:
                        cursor.execute("""
                            SELECT batch_id, status, total_tasks, completed_tasks,
                                   failed_tasks, cancelled_tasks, started_at, completed_at
                            FROM batches 
                            WHERE status = ?
                            ORDER BY started_at DESC
                            LIMIT ?
                        """, (status.value, limit))
                    else:
                        cursor.execute("""
                            SELECT batch_id, status, total_tasks, completed_tasks,
                                   failed_tasks, cancelled_tasks, started_at, completed_at
                            FROM batches 
                            ORDER BY started_at DESC
                            LIMIT ?
                        """, (limit,))
                    
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    
                    return [dict(zip(columns, row)) for row in rows]
                    
            except Exception as e:
                logger.error(f"获取批处理列表失败: 错误: {e}")
                return []
    
    def cleanup_old_data(self, days: int = 30):
        """清理旧数据"""
        with self._lock:
            try:
                cutoff_time = (datetime.now() - timedelta(days=days)).timestamp()
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # 删除旧的已完成批处理
                    cursor.execute("""
                        DELETE FROM batches 
                        WHERE completed_at IS NOT NULL 
                        AND completed_at < ?
                    """, (cutoff_time,))
                    
                    # 删除孤立的任务
                    cursor.execute("""
                        DELETE FROM tasks 
                        WHERE batch_id NOT IN (SELECT batch_id FROM batches)
                    """, )
                    
                    conn.commit()
                    
                    deleted_batches = cursor.rowcount
                    logger.info(f"清理旧数据完成，删除 {deleted_batches} 个批处理")
                    
            except Exception as e:
                logger.error(f"清理旧数据失败: 错误: {e}")


# 全局存储实例
global_batch_storage = BatchStorage()
