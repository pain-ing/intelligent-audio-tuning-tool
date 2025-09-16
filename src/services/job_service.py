"""
任务管理服务
"""
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from src.services.base import BaseService
from src.core.exceptions import JobError, ValidationError, ErrorCode
from src.services.audio_service import AudioService
from src.services.storage_service import get_storage_service
from src.services.cache_service import get_cache_service


class JobService(BaseService):
    """任务管理服务"""

    def __init__(self, db: Session):
        super().__init__()
        self.db = db
        self.audio_service = AudioService()
        self.storage_service = get_storage_service()
        self.cache_service = get_cache_service()

    async def create_job(
        self,
        ref_key: str,
        tgt_key: str,
        mode: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建音频处理任务"""
        # 验证输入
        if mode not in ["A", "B"]:
            raise ValidationError(
                message="Invalid mode, must be 'A' or 'B'",
                detail={"mode": mode}
            )

        job_id = str(uuid.uuid4())
        try:
            # 提取为可打桩的方法，便于测试
            created = await self._create_job_record(job_id, ref_key, tgt_key, mode, user_id or "default")
            ret_id = created.get("id", job_id) if isinstance(created, dict) else job_id

            # 异步启动处理任务（不阻塞创建接口）
            await self._process_job_async(ret_id, ref_key, tgt_key, mode)

            self.logger.info(f"Job created: {ret_id}")
            return {"id": ret_id, "status": "PENDING"}
        except Exception as e:
            self.db.rollback()
            self._handle_error(e, f"Failed to create job")

    async def get_job(self, job_id: str) -> Dict[str, Any]:
        """获取任务信息（委托可打桩方法，便于测试）"""
        try:
            return self._get_job_record(job_id)
        except JobError:
            raise
        except Exception as e:
            self._handle_error(e, f"Failed to get job {job_id}")

    async def list_jobs(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """获取任务列表（委托可打桩方法，便于测试）"""
        try:
            return self._list_job_records(user_id=user_id, status=status, limit=limit, offset=offset)
        except Exception as e:
            self._handle_error(e, "Failed to list jobs")

    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """取消任务（委托状态更新方法，便于测试桩替换）"""
        try:
            await self._update_job_status(job_id, "CANCELLED")
            self.logger.info(f"Job cancelled: {job_id}")
            return {"status": "success"}
        except JobError:
            raise
        except Exception as e:
            self.db.rollback()
            self._handle_error(e, f"Failed to cancel job {job_id}")

    async def _process_job_async(self, job_id: str, ref_key: str, tgt_key: str, mode: str):
        """异步处理任务"""
        import asyncio

        # 在后台任务中处理
        asyncio.create_task(self._process_job(job_id, ref_key, tgt_key, mode))

    async def _process_job(self, job_id: str, ref_key: str, tgt_key: str, mode: str):
        """处理音频任务"""
        try:
            from api.app.models_sqlite import Job

            # 更新状态为分析中
            await self._update_job_status(job_id, "ANALYZING", 10)

            # 下载文件
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as ref_tmp:
                ref_path = ref_tmp.name
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tgt_tmp:
                tgt_path = tgt_tmp.name

            await self.storage_service.download_file(ref_key, ref_path)
            await self.storage_service.download_file(tgt_key, tgt_path)

            # 分析特征
            ref_features = await self.audio_service.analyze_features(ref_path)
            tgt_features = await self.audio_service.analyze_features(tgt_path)

            # 更新状态为参数反演
            await self._update_job_status(job_id, "INVERTING", 40)

            # 参数反演
            style_params = await self.audio_service.invert_parameters(
                ref_features, tgt_features, mode
            )

            # 更新状态为渲染中
            await self._update_job_status(job_id, "RENDERING", 70)

            # 音频渲染
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as output_tmp:
                output_path = output_tmp.name

            metrics = await self.audio_service.render_audio(
                tgt_path, output_path, style_params
            )

            # 上传结果
            result_key = f"processed/{job_id}.wav"
            await self.storage_service.upload_file(output_path, result_key)

            # 更新任务完成
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "COMPLETED"
                job.progress = 100
                job.result_key = result_key
                job.metrics = metrics
                job.updated_at = datetime.utcnow()
                self.db.commit()

            # 清理临时文件
            import os
            for path in [ref_path, tgt_path, output_path]:
                if os.path.exists(path):
                    os.unlink(path)

            self.logger.info(f"Job completed: {job_id}")

        except Exception as e:
            await self._update_job_status(job_id, "FAILED", error=str(e))
            self.logger.error(f"Job failed: {job_id}, error: {str(e)}")

    async def _update_job_status(
        self,
        job_id: str,
        status: str,
        progress: Optional[int] = None,
        error: Optional[str] = None
    ):
        """更新任务状态"""
        try:
            from api.app.models_sqlite import Job

            job = self.db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = status
                if progress is not None:
                    job.progress = progress
                if error:
                    job.error = error
                job.updated_at = datetime.utcnow()
                self.db.commit()

        except Exception as e:
            self.logger.error(f"Failed to update job status: {job_id}, error: {str(e)}")
            self.db.rollback()


    async def _create_job_record(self, job_id: str, ref_key: str, tgt_key: str, mode: str, user_id: str) -> Dict[str, Any]:
        """创建任务记录（可被测试替换）"""
        from api.app.models_sqlite import Job
        job = Job(
            id=job_id,
            user_id=user_id,
            mode=mode,
            ref_key=ref_key,
            tgt_key=tgt_key,
            status="PENDING",
            progress=0,
            created_at=datetime.utcnow()
        )
        self.db.add(job)
        self.db.commit()
        return {"id": job_id, "status": "PENDING"}

    def _get_job_record(self, job_id: str) -> Dict[str, Any]:
        """获取单个任务记录（可被测试替换）"""
        from api.app.models_sqlite import Job
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise JobError(message=f"Job not found: {job_id}", code=ErrorCode.JOB_NOT_FOUND)
        result: Dict[str, Any] = {
            "id": job.id,
            "status": job.status,
            "progress": job.progress,
            "mode": job.mode,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat() if job.updated_at else None
        }
        if getattr(job, "error", None):
            result["error"] = job.error
        if getattr(job, "metrics", None):
            result["metrics"] = job.metrics
        return result

    def _list_job_records(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """列出任务记录（可被测试替换）"""
        from api.app.models_sqlite import Job
        query = self.db.query(Job)
        if user_id:
            query = query.filter(Job.user_id == user_id)
        if status:
            query = query.filter(Job.status == status)
        total = query.count()
        jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()
        job_list: List[Dict[str, Any]] = []
        for job in jobs:
            job_list.append({
                "id": job.id,
                "status": job.status,
                "progress": job.progress,
                "mode": job.mode,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat() if job.updated_at else None
            })
        return {"jobs": job_list, "total": total, "limit": limit, "offset": offset, "has_more": offset + len(job_list) < total}
