"""
重构后的任务处理器 - 分解长函数
"""
import time
import logging
from typing import Dict, Any, Tuple, Optional
from time import perf_counter
from dataclasses import dataclass

from src.core.exceptions import JobError, AudioProcessingError, ErrorCode
from src.services.audio_service import AudioService
from src.services.storage_service import get_storage_service
from src.services.cache_service import get_cache_service

logger = logging.getLogger(__name__)


@dataclass
class JobMetrics:
    """任务执行指标"""
    job_id: str
    status: str
    mode: str
    analyze_duration: float = 0.0
    invert_duration: float = 0.0
    render_duration: float = 0.0
    total_duration: float = 0.0
    timestamp: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "mode": self.mode,
            "analyze_s": round(self.analyze_duration, 3),
            "invert_s": round(self.invert_duration, 3),
            "render_s": round(self.render_duration, 3),
            "total_s": round(self.total_duration, 3),
            "timestamp": self.timestamp or int(time.time())
        }


class JobProcessor:
    """任务处理器 - 重构后的版本"""
    
    def __init__(self):
        self.audio_service = AudioService()
        self.storage_service = get_storage_service()
        self.cache_service = get_cache_service()
        self.logger = logger
    
    async def process_job(
        self,
        job_id: str,
        ref_key: str,
        tgt_key: str,
        mode: str
    ) -> Dict[str, Any]:
        """处理音频任务 - 主入口函数"""
        metrics = JobMetrics(job_id=job_id, status="FAILED", mode=mode)
        start_time = perf_counter()
        
        try:
            # 检查任务是否已取消
            if await self._is_job_cancelled(job_id):
                return await self._handle_cancellation(metrics, start_time)
            
            # 执行分析阶段
            ref_features, tgt_features = await self._execute_analysis_phase(
                job_id, ref_key, tgt_key, metrics, start_time
            )
            
            # 执行参数反演阶段
            style_params = await self._execute_inversion_phase(
                job_id, ref_features, tgt_features, mode, metrics, start_time
            )
            
            # 执行渲染阶段
            result_key, render_metrics = await self._execute_rendering_phase(
                job_id, tgt_key, style_params, metrics, start_time
            )
            
            # 完成任务
            return await self._complete_job(
                job_id, result_key, render_metrics, metrics, start_time
            )
            
        except Exception as e:
            return await self._handle_job_error(job_id, e, metrics, start_time)
    
    async def _execute_analysis_phase(
        self,
        job_id: str,
        ref_key: str,
        tgt_key: str,
        metrics: JobMetrics,
        start_time: float
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """执行分析阶段"""
        await self._update_job_status(job_id, "ANALYZING", 10)
        
        analysis_start = perf_counter()
        
        try:
            # 并行分析两个音频文件
            import asyncio
            ref_task = asyncio.create_task(self._analyze_audio_file(ref_key))
            tgt_task = asyncio.create_task(self._analyze_audio_file(tgt_key))
            
            ref_features, tgt_features = await asyncio.gather(ref_task, tgt_task)
            
            metrics.analyze_duration = perf_counter() - analysis_start
            
            # 检查是否取消
            if await self._is_job_cancelled(job_id):
                raise JobError("Job cancelled during analysis", ErrorCode.JOB_CANCELLED)
            
            self.logger.info(f"Analysis completed for job {job_id} in {metrics.analyze_duration:.3f}s")
            return ref_features, tgt_features
            
        except Exception as e:
            metrics.analyze_duration = perf_counter() - analysis_start
            raise AudioProcessingError(
                f"Analysis failed: {str(e)}",
                ErrorCode.AUDIO_ANALYSIS_FAILED
            )
    
    async def _execute_inversion_phase(
        self,
        job_id: str,
        ref_features: Dict[str, Any],
        tgt_features: Dict[str, Any],
        mode: str,
        metrics: JobMetrics,
        start_time: float
    ) -> Dict[str, Any]:
        """执行参数反演阶段"""
        await self._update_job_status(job_id, "INVERTING", 40)
        
        inversion_start = perf_counter()
        
        try:
            style_params = await self.audio_service.invert_parameters(
                ref_features, tgt_features, mode
            )
            
            metrics.invert_duration = perf_counter() - inversion_start
            
            # 检查是否取消
            if await self._is_job_cancelled(job_id):
                raise JobError("Job cancelled during inversion", ErrorCode.JOB_CANCELLED)
            
            self.logger.info(f"Parameter inversion completed for job {job_id} in {metrics.invert_duration:.3f}s")
            return style_params
            
        except Exception as e:
            metrics.invert_duration = perf_counter() - inversion_start
            raise AudioProcessingError(
                f"Parameter inversion failed: {str(e)}",
                ErrorCode.PARAMETER_INVERSION_FAILED
            )
    
    async def _execute_rendering_phase(
        self,
        job_id: str,
        tgt_key: str,
        style_params: Dict[str, Any],
        metrics: JobMetrics,
        start_time: float
    ) -> Tuple[str, Dict[str, Any]]:
        """执行渲染阶段"""
        await self._update_job_status(job_id, "RENDERING", 70)
        
        rendering_start = perf_counter()
        
        try:
            # 下载目标音频文件
            import tempfile
            import uuid
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as input_tmp:
                input_path = input_tmp.name
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as output_tmp:
                output_path = output_tmp.name
            
            await self.storage_service.download_file(tgt_key, input_path)
            
            # 执行音频渲染
            render_metrics = await self.audio_service.render_audio(
                input_path, output_path, style_params
            )
            
            # 上传结果文件
            result_key = f"processed/{job_id}_{uuid.uuid4().hex[:8]}.wav"
            await self.storage_service.upload_file(output_path, result_key)
            
            # 清理临时文件
            import os
            for path in [input_path, output_path]:
                if os.path.exists(path):
                    os.unlink(path)
            
            metrics.render_duration = perf_counter() - rendering_start
            
            # 检查是否取消
            if await self._is_job_cancelled(job_id):
                raise JobError("Job cancelled during rendering", ErrorCode.JOB_CANCELLED)
            
            self.logger.info(f"Audio rendering completed for job {job_id} in {metrics.render_duration:.3f}s")
            return result_key, render_metrics
            
        except Exception as e:
            metrics.render_duration = perf_counter() - rendering_start
            raise AudioProcessingError(
                f"Audio rendering failed: {str(e)}",
                ErrorCode.AUDIO_RENDERING_FAILED
            )
    
    async def _analyze_audio_file(self, object_key: str) -> Dict[str, Any]:
        """分析单个音频文件"""
        # 检查缓存
        cache_key = f"features:{object_key}"
        cached_features = await self.cache_service.get(cache_key)
        if cached_features:
            self.logger.info(f"Using cached features for {object_key}")
            return cached_features
        
        # 下载并分析文件
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            await self.storage_service.download_file(object_key, tmp_path)
            features = await self.audio_service.analyze_features(tmp_path)
            
            # 缓存结果
            await self.cache_service.set(cache_key, features, ttl=24*3600)  # 24小时
            
            return features
            
        finally:
            import os
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    async def _complete_job(
        self,
        job_id: str,
        result_key: str,
        render_metrics: Dict[str, Any],
        metrics: JobMetrics,
        start_time: float
    ) -> Dict[str, Any]:
        """完成任务"""
        metrics.status = "COMPLETED"
        metrics.total_duration = perf_counter() - start_time
        
        await self._update_job_status(
            job_id, "COMPLETED", 100,
            result_key=result_key,
            metrics=render_metrics
        )
        
        await self._record_metrics(metrics)
        
        self.logger.info(f"Job {job_id} completed successfully in {metrics.total_duration:.3f}s")
        
        return {
            "status": "COMPLETED",
            "result_key": result_key,
            "metrics": render_metrics,
            "processing_time": metrics.total_duration
        }
    
    async def _handle_cancellation(
        self,
        metrics: JobMetrics,
        start_time: float
    ) -> Dict[str, Any]:
        """处理任务取消"""
        metrics.status = "CANCELLED"
        metrics.total_duration = perf_counter() - start_time
        
        await self._record_metrics(metrics)
        
        self.logger.info(f"Job {metrics.job_id} was cancelled before processing")
        return {"status": "CANCELLED"}
    
    async def _handle_job_error(
        self,
        job_id: str,
        error: Exception,
        metrics: JobMetrics,
        start_time: float
    ) -> Dict[str, Any]:
        """处理任务错误"""
        metrics.status = "FAILED"
        metrics.total_duration = perf_counter() - start_time
        
        error_message = str(error)
        
        await self._update_job_status(job_id, "FAILED", error=error_message)
        await self._record_metrics(metrics)
        
        self.logger.error(f"Job {job_id} failed: {error_message}")
        
        return {
            "status": "FAILED",
            "error": error_message,
            "processing_time": metrics.total_duration
        }
    
    async def _is_job_cancelled(self, job_id: str) -> bool:
        """检查任务是否已取消"""
        try:
            # 这里应该检查数据库中的任务状态
            # 暂时返回False，实际实现需要查询数据库
            return False
        except Exception:
            return False
    
    async def _update_job_status(
        self,
        job_id: str,
        status: str,
        progress: Optional[int] = None,
        result_key: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """更新任务状态"""
        # 这里应该更新数据库中的任务状态
        # 暂时只记录日志
        self.logger.info(f"Job {job_id} status updated: {status} ({progress}%)")
    
    async def _record_metrics(self, metrics: JobMetrics):
        """记录任务指标"""
        try:
            # 可以将指标发送到监控系统或写入日志文件
            self.logger.info(f"Job metrics: {metrics.to_dict()}")
        except Exception as e:
            self.logger.error(f"Failed to record metrics: {e}")
