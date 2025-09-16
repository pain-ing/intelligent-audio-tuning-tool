"""
批处理相关的数据模型
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pathlib import Path


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class BatchStatus(Enum):
    """批处理状态枚举"""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingPriority(Enum):
    """处理优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class AudioProcessingParams:
    """音频处理参数"""
    style_params: Dict[str, Any] = field(default_factory=dict)
    output_format: str = "wav"
    output_quality: str = "high"
    normalize_audio: bool = True
    apply_effects: bool = True
    custom_effects: List[str] = field(default_factory=list)
    
    # Adobe Audition特定参数
    use_audition: bool = False
    audition_template: Optional[str] = None
    audition_preset: Optional[str] = None


@dataclass
class BatchTask:
    """单个批处理任务"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    input_path: str = ""
    output_path: str = ""
    processing_params: AudioProcessingParams = field(default_factory=AudioProcessingParams)
    
    # 任务状态
    status: TaskStatus = TaskStatus.PENDING
    priority: ProcessingPriority = ProcessingPriority.NORMAL
    
    # 时间信息
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # 处理信息
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # 结果信息
    processing_time: Optional[float] = None
    output_size: Optional[int] = None
    quality_metrics: Optional[Dict[str, float]] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.input_path:
            raise ValueError("input_path不能为空")
        if not self.output_path:
            raise ValueError("output_path不能为空")
    
    @property
    def duration(self) -> Optional[float]:
        """获取任务持续时间"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return time.time() - self.started_at
        return None
    
    @property
    def is_completed(self) -> bool:
        """检查任务是否完成"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
    
    @property
    def can_retry(self) -> bool:
        """检查任务是否可以重试"""
        return (self.status == TaskStatus.FAILED and 
                self.retry_count < self.max_retries)
    
    def start_processing(self):
        """开始处理任务"""
        self.status = TaskStatus.PROCESSING
        self.started_at = time.time()
    
    def complete_successfully(self, processing_time: float, 
                            output_size: Optional[int] = None,
                            quality_metrics: Optional[Dict[str, float]] = None):
        """标记任务成功完成"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = time.time()
        self.processing_time = processing_time
        self.output_size = output_size
        self.quality_metrics = quality_metrics
    
    def fail_with_error(self, error_message: str, 
                       error_details: Optional[Dict[str, Any]] = None):
        """标记任务失败"""
        self.status = TaskStatus.FAILED
        self.completed_at = time.time()
        self.error_message = error_message
        self.error_details = error_details
    
    def retry(self):
        """重试任务"""
        if self.can_retry:
            self.retry_count += 1
            self.status = TaskStatus.RETRYING
            self.started_at = None
            self.completed_at = None
            self.error_message = None
            self.error_details = None
    
    def cancel(self):
        """取消任务"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = time.time()


@dataclass
class BatchProgress:
    """批处理进度信息"""
    batch_id: str
    total_tasks: int
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    
    # 时间信息
    started_at: float = field(default_factory=time.time)
    estimated_completion: Optional[float] = None
    
    # 性能指标
    average_processing_time: float = 0.0
    current_processing_speed: float = 0.0  # 任务/秒
    
    @property
    def pending_tasks(self) -> int:
        """待处理任务数"""
        return self.total_tasks - self.completed_tasks - self.failed_tasks - self.cancelled_tasks
    
    @property
    def progress_percentage(self) -> float:
        """进度百分比"""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks + self.failed_tasks + self.cancelled_tasks) / self.total_tasks * 100
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        processed = self.completed_tasks + self.failed_tasks
        if processed == 0:
            return 0.0
        return self.completed_tasks / processed * 100
    
    @property
    def elapsed_time(self) -> float:
        """已用时间"""
        return time.time() - self.started_at
    
    def update_progress(self, completed: int, failed: int, cancelled: int,
                       avg_processing_time: float):
        """更新进度信息"""
        self.completed_tasks = completed
        self.failed_tasks = failed
        self.cancelled_tasks = cancelled
        self.average_processing_time = avg_processing_time
        
        # 计算处理速度
        elapsed = self.elapsed_time
        if elapsed > 0:
            processed = completed + failed + cancelled
            self.current_processing_speed = processed / elapsed
        
        # 估算完成时间
        if self.current_processing_speed > 0 and self.pending_tasks > 0:
            remaining_time = self.pending_tasks / self.current_processing_speed
            self.estimated_completion = time.time() + remaining_time


@dataclass
class BatchResult:
    """批处理结果"""
    batch_id: str
    status: BatchStatus
    
    # 任务统计
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    
    # 时间信息
    started_at: float
    completed_at: Optional[float] = None
    total_processing_time: float = 0.0
    
    # 性能指标
    average_task_time: float = 0.0
    total_input_size: int = 0
    total_output_size: int = 0
    
    # 质量指标
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    
    # 错误信息
    error_summary: Dict[str, int] = field(default_factory=dict)
    failed_tasks_details: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks * 100
    
    @property
    def duration(self) -> Optional[float]:
        """批处理总时长"""
        if self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def throughput(self) -> float:
        """处理吞吐量（任务/秒）"""
        duration = self.duration
        if duration and duration > 0:
            return self.total_tasks / duration
        return 0.0
    
    def add_failed_task(self, task: BatchTask):
        """添加失败任务详情"""
        self.failed_tasks_details.append({
            "task_id": task.task_id,
            "input_path": task.input_path,
            "error_message": task.error_message,
            "error_details": task.error_details,
            "retry_count": task.retry_count
        })
        
        # 更新错误统计
        error_type = task.error_message or "unknown_error"
        self.error_summary[error_type] = self.error_summary.get(error_type, 0) + 1


@dataclass
class BatchConfiguration:
    """批处理配置"""
    max_concurrent_tasks: int = 4
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout_per_task: float = 300.0
    
    # 资源限制
    max_memory_mb: float = 2048.0
    max_disk_space_mb: float = 10240.0
    
    # 进度报告
    progress_update_interval: float = 1.0
    enable_real_time_updates: bool = True
    
    # 错误处理
    stop_on_first_error: bool = False
    auto_retry_failed_tasks: bool = True
    
    # 输出设置
    preserve_directory_structure: bool = True
    create_output_directories: bool = True
    overwrite_existing_files: bool = False
