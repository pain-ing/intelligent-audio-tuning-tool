"""
批处理API接口
"""

import logging
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field

from .batch_models import (
    BatchTask, BatchConfiguration, AudioProcessingParams,
    TaskStatus, BatchStatus, ProcessingPriority
)
from .batch_processor import global_batch_processor
from .batch_storage import global_batch_storage
from .batch_progress import global_progress_manager

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/batch", tags=["批处理"])


# Pydantic模型定义
class AudioProcessingParamsModel(BaseModel):
    """音频处理参数模型"""
    style_params: Dict[str, Any] = Field(default_factory=dict, description="风格参数")
    output_format: str = Field(default="wav", description="输出格式")
    output_quality: str = Field(default="high", description="输出质量")
    normalize_audio: bool = Field(default=True, description="是否标准化音频")
    apply_effects: bool = Field(default=True, description="是否应用效果")
    custom_effects: List[str] = Field(default_factory=list, description="自定义效果")
    use_audition: bool = Field(default=False, description="是否使用Adobe Audition")
    audition_template: Optional[str] = Field(default=None, description="Audition模板")
    audition_preset: Optional[str] = Field(default=None, description="Audition预设")


class BatchTaskModel(BaseModel):
    """批处理任务模型"""
    input_path: str = Field(..., description="输入文件路径")
    output_path: str = Field(..., description="输出文件路径")
    processing_params: AudioProcessingParamsModel = Field(
        default_factory=AudioProcessingParamsModel, 
        description="处理参数"
    )
    priority: ProcessingPriority = Field(default=ProcessingPriority.NORMAL, description="优先级")
    max_retries: int = Field(default=3, description="最大重试次数")


class BatchSubmissionModel(BaseModel):
    """批处理提交模型"""
    tasks: List[BatchTaskModel] = Field(..., description="任务列表")
    batch_id: Optional[str] = Field(default=None, description="批处理ID（可选）")
    auto_start: bool = Field(default=True, description="是否自动开始")
    config: Optional[Dict[str, Any]] = Field(default=None, description="批处理配置")


class BatchStatusResponse(BaseModel):
    """批处理状态响应"""
    batch_id: str
    status: str
    progress: Dict[str, Any]


class BatchListResponse(BaseModel):
    """批处理列表响应"""
    batches: List[Dict[str, Any]]
    total: int


@router.post("/submit", response_model=Dict[str, str])
async def submit_batch(
    submission: BatchSubmissionModel,
    background_tasks: BackgroundTasks
):
    """提交批处理任务"""
    try:
        # 转换任务模型
        batch_tasks = []
        for task_model in submission.tasks:
            # 转换处理参数
            params = AudioProcessingParams(
                style_params=task_model.processing_params.style_params,
                output_format=task_model.processing_params.output_format,
                output_quality=task_model.processing_params.output_quality,
                normalize_audio=task_model.processing_params.normalize_audio,
                apply_effects=task_model.processing_params.apply_effects,
                custom_effects=task_model.processing_params.custom_effects,
                use_audition=task_model.processing_params.use_audition,
                audition_template=task_model.processing_params.audition_template,
                audition_preset=task_model.processing_params.audition_preset
            )
            
            # 创建批处理任务
            task = BatchTask(
                input_path=task_model.input_path,
                output_path=task_model.output_path,
                processing_params=params,
                priority=task_model.priority,
                max_retries=task_model.max_retries
            )
            batch_tasks.append(task)
        
        # 提交批处理
        batch_id = global_batch_processor.submit_batch(
            tasks=batch_tasks,
            batch_id=submission.batch_id
        )
        
        # 保存到存储
        global_batch_storage.save_batch(
            batch_id=batch_id,
            status=BatchStatus.CREATED,
            total_tasks=len(batch_tasks),
            config=submission.config
        )
        
        # 保存任务
        for task in batch_tasks:
            global_batch_storage.save_task(task, batch_id)
        
        # 自动开始
        if submission.auto_start:
            background_tasks.add_task(start_batch_processing, batch_id)
        
        logger.info(f"批处理任务提交成功: {batch_id}, 任务数: {len(batch_tasks)}")
        
        return {
            "batch_id": batch_id,
            "message": f"批处理任务提交成功，包含 {len(batch_tasks)} 个任务",
            "auto_start": submission.auto_start
        }
        
    except Exception as e:
        logger.error(f"提交批处理任务失败: {e}")
        raise HTTPException(status_code=400, detail=f"提交失败: {str(e)}")


async def start_batch_processing(batch_id: str):
    """后台任务：开始批处理"""
    try:
        success = global_batch_processor.start_batch(batch_id)
        if success:
            global_batch_storage.update_batch_status(batch_id, BatchStatus.RUNNING)
            logger.info(f"批处理开始执行: {batch_id}")
        else:
            logger.error(f"批处理启动失败: {batch_id}")
    except Exception as e:
        logger.error(f"批处理启动异常: {batch_id}, 错误: {e}")


@router.post("/start/{batch_id}")
async def start_batch(batch_id: str):
    """手动开始批处理"""
    try:
        success = global_batch_processor.start_batch(batch_id)
        if not success:
            raise HTTPException(status_code=400, detail="批处理启动失败")
        
        # 更新存储状态
        global_batch_storage.update_batch_status(batch_id, BatchStatus.RUNNING)
        
        return {"message": f"批处理 {batch_id} 已开始执行"}
        
    except Exception as e:
        logger.error(f"启动批处理失败: {batch_id}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")


@router.get("/status/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: str):
    """获取批处理状态"""
    try:
        status = global_batch_processor.get_batch_status(batch_id)
        if not status:
            # 尝试从存储加载
            stored_batch = global_batch_storage.load_batch(batch_id)
            if not stored_batch:
                raise HTTPException(status_code=404, detail="批处理不存在")
            
            # 构造状态响应
            status = {
                "batch_id": batch_id,
                "status": stored_batch["status"],
                "progress": {
                    "total_tasks": stored_batch["total_tasks"],
                    "completed_tasks": stored_batch["completed_tasks"],
                    "failed_tasks": stored_batch["failed_tasks"],
                    "cancelled_tasks": stored_batch["cancelled_tasks"],
                    "progress_percentage": 0.0
                }
            }
            
            # 计算进度百分比
            total = stored_batch["total_tasks"]
            if total > 0:
                completed = (stored_batch["completed_tasks"] + 
                           stored_batch["failed_tasks"] + 
                           stored_batch["cancelled_tasks"])
                status["progress"]["progress_percentage"] = (completed / total) * 100
        
        return BatchStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取批处理状态失败: {batch_id}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/cancel/{batch_id}")
async def cancel_batch(batch_id: str):
    """取消批处理"""
    try:
        success = global_batch_processor.cancel_batch(batch_id)
        if not success:
            raise HTTPException(status_code=400, detail="批处理取消失败")
        
        # 更新存储状态
        global_batch_storage.update_batch_status(batch_id, BatchStatus.CANCELLED)
        
        return {"message": f"批处理 {batch_id} 已取消"}
        
    except Exception as e:
        logger.error(f"取消批处理失败: {batch_id}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"取消失败: {str(e)}")


@router.get("/result/{batch_id}")
async def get_batch_result(batch_id: str):
    """获取批处理结果"""
    try:
        result = global_batch_processor.get_batch_result(batch_id)
        if not result:
            # 尝试从存储加载
            stored_batch = global_batch_storage.load_batch(batch_id)
            if not stored_batch:
                raise HTTPException(status_code=404, detail="批处理不存在")
            
            if stored_batch["status"] not in ["completed", "failed", "cancelled"]:
                raise HTTPException(status_code=400, detail="批处理尚未完成")
            
            # 构造结果响应
            result_data = stored_batch.get("result", {})
            return {
                "batch_id": batch_id,
                "status": stored_batch["status"],
                "total_tasks": stored_batch["total_tasks"],
                "completed_tasks": stored_batch["completed_tasks"],
                "failed_tasks": stored_batch["failed_tasks"],
                "cancelled_tasks": stored_batch["cancelled_tasks"],
                "started_at": stored_batch["started_at"],
                "completed_at": stored_batch["completed_at"],
                **result_data
            }
        
        # 转换结果为字典
        return {
            "batch_id": result.batch_id,
            "status": result.status.value,
            "total_tasks": result.total_tasks,
            "completed_tasks": result.completed_tasks,
            "failed_tasks": result.failed_tasks,
            "cancelled_tasks": result.cancelled_tasks,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "total_processing_time": result.total_processing_time,
            "average_task_time": result.average_task_time,
            "success_rate": result.success_rate,
            "throughput": result.throughput,
            "quality_metrics": result.quality_metrics,
            "error_summary": result.error_summary,
            "failed_tasks_details": result.failed_tasks_details
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取批处理结果失败: {batch_id}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取结果失败: {str(e)}")


@router.get("/list", response_model=BatchListResponse)
async def list_batches(
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(100, description="返回数量限制")
):
    """获取批处理列表"""
    try:
        # 转换状态过滤
        status_filter = None
        if status:
            try:
                status_filter = BatchStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的状态值: {status}")
        
        # 获取批处理列表
        batches = global_batch_storage.get_batch_list(status_filter, limit)
        
        return BatchListResponse(
            batches=batches,
            total=len(batches)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取批处理列表失败: 错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.get("/tasks/{batch_id}")
async def get_batch_tasks(batch_id: str):
    """获取批处理的所有任务"""
    try:
        tasks = global_batch_storage.load_batch_tasks(batch_id)
        if not tasks:
            # 检查批处理是否存在
            batch = global_batch_storage.load_batch(batch_id)
            if not batch:
                raise HTTPException(status_code=404, detail="批处理不存在")
        
        return {
            "batch_id": batch_id,
            "tasks": tasks,
            "total": len(tasks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取批处理任务失败: {batch_id}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务失败: {str(e)}")


@router.delete("/cleanup")
async def cleanup_old_batches(days: int = Query(30, description="保留天数")):
    """清理旧的批处理数据"""
    try:
        # 清理存储中的旧数据
        global_batch_storage.cleanup_old_data(days)
        
        # 清理内存中的已完成批处理
        global_batch_processor.cleanup_completed_batches(days * 24)
        
        # 清理进度跟踪器
        global_progress_manager.cleanup_completed_trackers(days * 24)
        
        return {"message": f"清理完成，删除了 {days} 天前的旧数据"}
        
    except Exception as e:
        logger.error(f"清理旧数据失败: 错误: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/statistics")
async def get_batch_statistics():
    """获取批处理统计信息"""
    try:
        # 获取所有批处理
        all_batches = global_batch_storage.get_batch_list(limit=1000)
        
        # 统计信息
        stats = {
            "total_batches": len(all_batches),
            "status_breakdown": {},
            "total_tasks": 0,
            "total_completed_tasks": 0,
            "total_failed_tasks": 0,
            "average_success_rate": 0.0
        }
        
        for batch in all_batches:
            status = batch["status"]
            stats["status_breakdown"][status] = stats["status_breakdown"].get(status, 0) + 1
            stats["total_tasks"] += batch["total_tasks"]
            stats["total_completed_tasks"] += batch["completed_tasks"]
            stats["total_failed_tasks"] += batch["failed_tasks"]
        
        # 计算平均成功率
        if stats["total_tasks"] > 0:
            stats["average_success_rate"] = (stats["total_completed_tasks"] / stats["total_tasks"]) * 100
        
        return stats
        
    except Exception as e:
        logger.error(f"获取批处理统计失败: 错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")
