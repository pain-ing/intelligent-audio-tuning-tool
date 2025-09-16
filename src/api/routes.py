"""
重构后的API路由
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel

from src.core.config import config
from src.core.exceptions import AudioTunerException
from src.services.job_service import JobService
from src.services.storage_service import get_storage_service
from api.app.database import get_db


# 请求模型
class CreateJobRequest(BaseModel):
    mode: str
    ref_key: str
    tgt_key: str


class JobResponse(BaseModel):
    id: str
    status: str
    progress: int
    mode: str
    created_at: str
    updated_at: Optional[str] = None
    download_url: Optional[str] = None
    error: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


# 创建路由器
router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "app_name": config.app_name,
        "version": config.app_version,
        "mode": config.app_mode.value
    }


@router.post("/jobs", response_model=Dict[str, str])
async def create_job(
    request: CreateJobRequest,
    db: Session = Depends(get_db)
):
    """创建音频处理任务"""
    try:
        job_service = JobService(db)
        result = await job_service.create_job(
            ref_key=request.ref_key,
            tgt_key=request.tgt_key,
            mode=request.mode
        )
        return result
        
    except AudioTunerException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.to_dict()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "Internal server error"
            }
        )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """获取任务详情"""
    try:
        job_service = JobService(db)
        job_data = await job_service.get_job(job_id)
        return JobResponse(**job_data)
        
    except AudioTunerException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.to_dict()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "Internal server error"
            }
        )


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """获取任务列表"""
    try:
        job_service = JobService(db)
        result = await job_service.list_jobs(
            status=status,
            limit=limit,
            offset=offset
        )
        return result
        
    except AudioTunerException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.to_dict()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "Internal server error"
            }
        )


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """取消任务"""
    try:
        job_service = JobService(db)
        result = await job_service.cancel_job(job_id)
        return result
        
    except AudioTunerException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.to_dict()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "Internal server error"
            }
        )


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传音频文件"""
    try:
        # 验证文件格式
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_INPUT",
                    "message": "Filename is required"
                }
            )
        
        file_ext = file.filename.split('.')[-1].lower()
        if file_ext not in config.supported_formats:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "UNSUPPORTED_FORMAT",
                    "message": f"Unsupported file format: {file_ext}"
                }
            )
        
        # 验证文件大小
        if file.size and file.size > config.max_file_size:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "FILE_TOO_LARGE",
                    "message": f"File too large: {file.size} bytes"
                }
            )
        
        # 保存文件
        import tempfile
        import uuid
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        # 上传到存储服务
        storage_service = get_storage_service()
        object_key = f"uploads/{uuid.uuid4().hex}.{file_ext}"
        await storage_service.upload_file(tmp_path, object_key)
        
        # 清理临时文件
        os.unlink(tmp_path)
        
        return {
            "object_key": object_key,
            "filename": file.filename,
            "size": len(content)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "UPLOAD_FAILED",
                "message": f"Upload failed: {str(e)}"
            }
        )


# 异常处理器函数（需要在主应用中注册）
async def audio_tuner_exception_handler(request, exc: AudioTunerException):
    """处理自定义异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )
