from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal, Optional, Dict
from sqlalchemy.orm import Session
import uuid
import os
import logging
from celery import Celery

from app.database import get_db, engine
from app.models import Base, Job, User
from app.worker_client import process_audio_job
from app.storage import storage_service

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Audio Style Matching API", version="0.1.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Celery client for task dispatch
redis_url = os.getenv("QUEUE_URL", "redis://localhost:6379/0")
celery_app = Celery("audio_api", broker=redis_url, backend=redis_url)

class JobCreate(BaseModel):
    mode: Literal["A", "B"]
    ref_key: str
    tgt_key: str
    opts: Optional[dict] = None

class JobResponse(BaseModel):
    job_id: str

class UploadSignRequest(BaseModel):
    content_type: str
    extension: str
    file_size: Optional[int] = None

class UploadSignResponse(BaseModel):
    upload_url: str
    download_url: str
    object_key: str
    expires_in: int

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/uploads/sign", response_model=UploadSignResponse)
def get_upload_signature(request: UploadSignRequest):
    """Get signed URL for file upload"""
    try:
        # 生成上传签名
        signature_data = storage_service.generate_upload_signature(
            content_type=request.content_type,
            file_extension=request.extension,
            expires_in=3600  # 1小时有效期
        )

        return UploadSignResponse(
            upload_url=signature_data["upload_url"],
            download_url=signature_data["download_url"],
            object_key=signature_data["object_key"],
            expires_in=signature_data["expires_in"]
        )

    except Exception as e:
        logging.error(f"Failed to generate upload signature: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate upload signature")

@app.get("/uploads/{object_key:path}/download")
def get_download_url(object_key: str, expires_in: int = 3600):
    """Get download URL for uploaded file"""
    try:
        # 检查文件是否存在
        if not storage_service.file_exists(object_key):
            raise HTTPException(status_code=404, detail="File not found")

        # 生成下载 URL
        download_url = storage_service.generate_download_url(object_key, expires_in)

        return {
            "download_url": download_url,
            "object_key": object_key,
            "expires_in": expires_in
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Failed to generate download URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate download URL")

@app.get("/uploads/{object_key:path}/info")
def get_file_info(object_key: str):
    """Get file information"""
    try:
        file_info = storage_service.get_file_info(object_key)

        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")

        return file_info

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Failed to get file info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get file info")

@app.delete("/uploads/{object_key:path}")
def delete_file(object_key: str):
    """Delete uploaded file"""
    try:
        success = storage_service.delete_file(object_key)

        if not success:
            raise HTTPException(status_code=404, detail="File not found or failed to delete")

        return {"message": "File deleted successfully", "object_key": object_key}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Failed to delete file: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")

@app.post("/jobs", response_model=JobResponse)
def create_job(req: JobCreate, db: Session = Depends(get_db)):
    # Create job in database
    job = Job(
        user_id="00000000-0000-0000-0000-000000000000",  # Placeholder user ID
        mode=req.mode,
        ref_key=req.ref_key,
        tgt_key=req.tgt_key,
        status="PENDING",
        progress=0,
        params=req.opts or {}
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Dispatch to worker
    celery_app.send_task(
        "app.worker.process_audio_job",
        args=[str(job.id), req.mode, req.ref_key, req.tgt_key, req.opts or {}],
        queue="audio_processing"
    )

    return {"job_id": str(job.id)}

@app.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    resp = {
        "id": str(job.id),
        "user_id": str(job.user_id),
        "mode": job.mode,
        "status": job.status,
        "progress": job.progress,
        "metrics": job.metrics or {},
        "result_key": job.result_key,
        "download_url": f"https://example-object-store/{job.result_key}" if job.result_key else None,
        "viz_urls": None,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
    return resp

@app.post("/jobs/{job_id}/retry")
def retry_job(job_id: str, db: Session = Depends(get_db)):
    """Retry a failed job by resetting its state and re-dispatching the task."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "FAILED":
        raise HTTPException(status_code=400, detail="Only FAILED jobs can be retried")
    # reset state
    job.status = "PENDING"
    job.progress = 0
    job.error = None
    job.result_key = None
    job.metrics = None
    db.add(job)
    db.commit()
    # re-dispatch
    celery_app.send_task(
        "app.worker.process_audio_job",
        args=[str(job.id), job.mode, job.ref_key, job.tgt_key, job.params or {}],
        queue="audio_processing"
    )
    return {"job_id": str(job.id), "status": job.status}



from datetime import datetime
import base64, json
from uuid import UUID
from sqlalchemy import and_, or_

class JobItem(BaseModel):
    id: str
    user_id: str
    mode: str
    status: str
    progress: int
    created_at: datetime
    updated_at: datetime
    result_key: Optional[str] = None
    error: Optional[str] = None

class JobListResponse(BaseModel):
    items: list[JobItem]
    next_cursor: Optional[str] = None

def _encode_cursor(created_at: datetime, id_str: str) -> str:
    payload = {"created_at": created_at.isoformat(), "id": id_str}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
    return datetime.fromisoformat(data["created_at"]), data["id"]

@app.get("/jobs", response_model=JobListResponse)
def list_jobs(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    cursor: Optional[str] = None,
    created_before: Optional[str] = None,
    created_after: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List jobs with keyset pagination ordered by created_at desc, id desc."""
    limit = max(1, min(limit, 100))

    q = db.query(Job)
    if user_id:
        try:
            q = q.filter(Job.user_id == UUID(user_id))
        except Exception:
            raise HTTPException(status_code=400, detail="invalid user_id")
    if status:
        q = q.filter(Job.status == status)

    # explicit time range filters
    if created_after:
        try:
            ca = datetime.fromisoformat(created_after)
            q = q.filter(Job.created_at >= ca)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid created_after")
    if created_before:
        try:
            cb = datetime.fromisoformat(created_before)
            q = q.filter(Job.created_at <= cb)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid created_before")

    if cursor:
        try:
            created_after_c, last_id = _decode_cursor(cursor)
            # keyset: (created_at < c) OR (created_at = c AND id < last_id)
            q = q.filter(or_(Job.created_at < created_after_c, and_(Job.created_at == created_after_c, Job.id < UUID(last_id))))
        except Exception:
            raise HTTPException(status_code=400, detail="invalid cursor")

    q = q.order_by(Job.created_at.desc(), Job.id.desc()).limit(limit + 1)
    rows = q.all()

    items = []
    for r in rows[:limit]:
        items.append(JobItem(
            id=str(r.id),
            user_id=str(r.user_id),
            mode=r.mode,
            status=r.status,
            progress=r.progress or 0,
            created_at=r.created_at,
            updated_at=r.updated_at,
            result_key=r.result_key,
            error=r.error,
        ))

    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = _encode_cursor(last.created_at, str(last.id))

    return JobListResponse(items=items, next_cursor=next_cursor)

@app.get("/jobs/stats")
def jobs_stats(user_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Quick counts by status, cached for ~20s in Redis."""
    try:
        from app.cache import cache_get, cache_set
        cache_key = f"v1:{user_id or 'all'}"
        cached = cache_get("jobs_stats", cache_key)
        if cached:
            return cached
    except Exception:
        cached = None
    # compute
    statuses = ["PENDING","ANALYZING","INVERTING","RENDERING","COMPLETED","FAILED"]
    from sqlalchemy import func as sa_func
    q = db.query(Job.status, sa_func.count().label("cnt"))
    if user_id:
        try:
            q = q.filter(Job.user_id == UUID(user_id))
        except Exception:
            raise HTTPException(status_code=400, detail="invalid user_id")
    rows = q.group_by(Job.status).all()
    m = {s: 0 for s in statuses}
    for status, cnt in rows:
        if status in m:
            m[status] = int(cnt)
    try:
        cache_set("jobs_stats", cache_key, m, ttl_sec=20)
    except Exception:
        pass
    return m


