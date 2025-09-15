"""SQLite 版本的 API 主文件"""
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Literal, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
import os

from app.models_sqlite import Base, Job, User

# 创建 SQLite 数据库连接
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Audio Style Matching API", version="0.1.0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class JobCreate(BaseModel):
    mode: Literal["A", "B"]
    ref_key: str
    tgt_key: str
    opts: Optional[dict] = None

class JobResponse(BaseModel):
    job_id: str

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/uploads/sign")
def sign_upload(content_type: str, ext: str):
    # Placeholder: returns a mocked signed URL and key
    key = f"uploads/{uuid.uuid4().hex}{ext if ext.startswith('.') else '.'+ext}"
    return {"put_url": f"https://example-object-store/{key}", "key": key, "expires": 900}

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
    
    # 模拟任务分发（本地测试不启动真实 Worker）
    print(f"📋 创建任务: {job.id} (模式: {req.mode})")
    
    return {"job_id": str(job.id)}

@app.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    resp = {
        "status": job.status,
        "progress": job.progress,
        "metrics": job.metrics or {},
        "download_url": f"https://example-object-store/{job.result_key}" if job.result_key else None,
        "viz_urls": None,
        "error": job.error
    }
    return resp

@app.get("/presets")
def list_presets():
    return {"presets": []}

@app.post("/presets")
def create_preset(name: str, style_params: dict):
    return {"id": str(uuid.uuid4()), "name": name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
