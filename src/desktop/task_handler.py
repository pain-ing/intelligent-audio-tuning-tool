"""
桌面版任务处理器 - 重构后的版本
"""
import os
import tempfile
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from src.core.exceptions import JobError, AudioProcessingError, ErrorCode
from src.services.audio_service import AudioService
from src.services.storage_service import get_storage_service

logger = logging.getLogger(__name__)


class DesktopTaskHandler:
    """桌面版任务处理器"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.audio_service = AudioService()
        self.storage_service = get_storage_service()
        self.logger = logger
    
    def process_audio_job(self, job_id: str, ref_key: str, tgt_key: str, mode: str) -> Dict[str, Any]:
        """处理音频任务 - 桌面版本"""
        self.logger.info(f"Starting desktop audio processing job {job_id}")
        
        try:
            # 验证任务存在
            job = self._get_job(job_id)
            
            # 创建临时工作目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # 准备文件路径
                file_paths = self._prepare_file_paths(temp_dir, job_id)
                
                # 下载输入文件
                self._download_input_files(ref_key, tgt_key, file_paths)
                
                # 执行音频处理流程
                result_metrics = self._execute_processing_pipeline(
                    job_id, file_paths, mode
                )
                
                # 上传结果文件
                result_key = self._upload_result_file(job_id, file_paths["result"])
                
                # 完成任务
                self._complete_job(job_id, result_key, result_metrics)
                
                return {
                    "status": "COMPLETED",
                    "result_key": result_key,
                    "metrics": result_metrics
                }
                
        except Exception as e:
            self._handle_job_error(job_id, e)
            raise
    
    def _get_job(self, job_id: str):
        """获取任务记录"""
        try:
            from models_sqlite import Job
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise JobError(
                    f"Job not found: {job_id}",
                    ErrorCode.JOB_NOT_FOUND
                )
            return job
        except Exception as e:
            raise JobError(f"Failed to get job {job_id}: {str(e)}")
    
    def _prepare_file_paths(self, temp_dir: str, job_id: str) -> Dict[str, str]:
        """准备文件路径"""
        return {
            "ref": os.path.join(temp_dir, f"ref_{job_id}.wav"),
            "tgt": os.path.join(temp_dir, f"tgt_{job_id}.wav"),
            "result": os.path.join(temp_dir, f"result_{job_id}.wav")
        }
    
    def _download_input_files(self, ref_key: str, tgt_key: str, file_paths: Dict[str, str]):
        """下载输入文件"""
        try:
            self.logger.info("Downloading input files")
            
            # 并行下载文件（在同步环境中使用线程池）
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                ref_future = executor.submit(
                    self.storage_service.download_file, ref_key, file_paths["ref"]
                )
                tgt_future = executor.submit(
                    self.storage_service.download_file, tgt_key, file_paths["tgt"]
                )
                
                # 等待下载完成
                concurrent.futures.wait([ref_future, tgt_future])
                
                # 检查是否有异常
                ref_future.result()
                tgt_future.result()
            
            self.logger.info("Input files downloaded successfully")
            
        except Exception as e:
            raise AudioProcessingError(
                f"Failed to download input files: {str(e)}",
                ErrorCode.DOWNLOAD_FAILED
            )
    
    def _execute_processing_pipeline(
        self,
        job_id: str,
        file_paths: Dict[str, str],
        mode: str
    ) -> Dict[str, Any]:
        """执行音频处理流程"""
        try:
            # 阶段1: 音频分析
            ref_features, tgt_features = self._execute_analysis_stage(
                job_id, file_paths["ref"], file_paths["tgt"]
            )
            
            # 阶段2: 参数反演
            style_params = self._execute_inversion_stage(
                job_id, ref_features, tgt_features, mode
            )
            
            # 阶段3: 音频渲染
            metrics = self._execute_rendering_stage(
                job_id, file_paths["tgt"], file_paths["result"], style_params
            )
            
            return metrics
            
        except Exception as e:
            raise AudioProcessingError(
                f"Processing pipeline failed: {str(e)}",
                ErrorCode.AUDIO_ANALYSIS_FAILED
            )
    
    def _execute_analysis_stage(
        self,
        job_id: str,
        ref_path: str,
        tgt_path: str
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """执行分析阶段"""
        self.logger.info(f"Starting analysis stage for job {job_id}")
        
        self._update_job_status(job_id, "ANALYZING", 30)
        
        try:
            # 导入分析器
            from app.audio_analysis import analyzer
            
            # 并行分析两个文件
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                ref_future = executor.submit(analyzer.analyze_features, ref_path)
                tgt_future = executor.submit(analyzer.analyze_features, tgt_path)
                
                ref_features = ref_future.result()
                tgt_features = tgt_future.result()
            
            self.logger.info(f"Analysis completed for job {job_id}")
            return ref_features, tgt_features
            
        except Exception as e:
            raise AudioProcessingError(
                f"Analysis stage failed: {str(e)}",
                ErrorCode.AUDIO_ANALYSIS_FAILED
            )
    
    def _execute_inversion_stage(
        self,
        job_id: str,
        ref_features: Dict[str, Any],
        tgt_features: Dict[str, Any],
        mode: str
    ) -> Dict[str, Any]:
        """执行参数反演阶段"""
        self.logger.info(f"Starting inversion stage for job {job_id}")
        
        self._update_job_status(job_id, "INVERTING", 50)
        
        try:
            from app.parameter_inversion import ParameterInverter
            
            inverter = ParameterInverter()
            style_params = inverter.invert_parameters(ref_features, tgt_features, mode)
            
            self.logger.info(f"Parameter inversion completed for job {job_id}")
            return style_params
            
        except Exception as e:
            raise AudioProcessingError(
                f"Inversion stage failed: {str(e)}",
                ErrorCode.PARAMETER_INVERSION_FAILED
            )
    
    def _execute_rendering_stage(
        self,
        job_id: str,
        input_path: str,
        output_path: str,
        style_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行渲染阶段"""
        self.logger.info(f"Starting rendering stage for job {job_id}")
        
        self._update_job_status(job_id, "RENDERING", 70)
        
        try:
            from app.audio_rendering import renderer
            
            metrics = renderer.render_audio(input_path, output_path, style_params)
            
            self.logger.info(f"Audio rendering completed for job {job_id}")
            return metrics
            
        except Exception as e:
            raise AudioProcessingError(
                f"Rendering stage failed: {str(e)}",
                ErrorCode.AUDIO_RENDERING_FAILED
            )
    
    def _upload_result_file(self, job_id: str, result_path: str) -> str:
        """上传结果文件"""
        try:
            import uuid
            result_key = f"processed/{job_id}_{uuid.uuid4().hex[:8]}.wav"
            
            self.storage_service.upload_file(result_path, result_key)
            
            self.logger.info(f"Result file uploaded: {result_key}")
            return result_key
            
        except Exception as e:
            raise AudioProcessingError(
                f"Failed to upload result file: {str(e)}",
                ErrorCode.UPLOAD_FAILED
            )
    
    def _complete_job(self, job_id: str, result_key: str, metrics: Dict[str, Any]):
        """完成任务"""
        try:
            from models_sqlite import Job
            
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "COMPLETED"
                job.progress = 100
                job.result_key = result_key
                job.metrics = metrics
                self.db.commit()
            
            self.logger.info(f"Job {job_id} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to complete job {job_id}: {e}")
            self.db.rollback()
            raise
    
    def _update_job_status(
        self,
        job_id: str,
        status: str,
        progress: Optional[int] = None,
        error: Optional[str] = None
    ):
        """更新任务状态"""
        try:
            from models_sqlite import Job
            
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = status
                if progress is not None:
                    job.progress = progress
                if error:
                    job.error = error
                self.db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to update job status: {e}")
            self.db.rollback()
    
    def _handle_job_error(self, job_id: str, error: Exception):
        """处理任务错误"""
        error_message = str(error)
        self.logger.error(f"Job {job_id} failed: {error_message}")
        
        try:
            self._update_job_status(job_id, "FAILED", error=error_message)
        except Exception as update_error:
            self.logger.error(f"Failed to update job error status: {update_error}")


# 工厂函数
def create_task_handler(db_session: Session) -> DesktopTaskHandler:
    """创建任务处理器实例"""
    return DesktopTaskHandler(db_session)
