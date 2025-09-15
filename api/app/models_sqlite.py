"""SQLite 兼容的数据模型"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    plan = Column(String(50), default="free")
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    jobs = relationship("Job", back_populates="user")
    presets = relationship("Preset", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    mode = Column(String(10), nullable=False)  # "A" or "B"
    ref_key = Column(Text, nullable=False)
    tgt_key = Column(Text, nullable=False)
    status = Column(String(20), default="PENDING")  # PENDING, ANALYZING, INVERTING, RENDERING, COMPLETED, FAILED
    progress = Column(Integer, default=0)
    params = Column(JSON)  # 使用 JSON 而不是 JSONB
    metrics = Column(JSON)
    error = Column(Text)
    result_key = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="jobs")
    segments = relationship("JobSegment", back_populates="job")
    metrics_history = relationship("Metric", back_populates="job")

class JobSegment(Base):
    __tablename__ = "job_segments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False)
    idx = Column(Integer, nullable=False)
    status = Column(String(20), default="PENDING")
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    metrics = Column(JSON)
    
    # Relationships
    job = relationship("Job", back_populates="segments")

class Preset(Base):
    __tablename__ = "presets"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    style_params = Column(JSON, nullable=False)
    public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="presets")

class Metric(Base):
    __tablename__ = "metrics"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False)
    stft_dist = Column(String(20))  # 使用 String 存储浮点数
    mel_dist = Column(String(20))
    lufs_err = Column(String(20))
    tp_db = Column(String(20))
    artifacts_rate = Column(String(20))
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    job = relationship("Job", back_populates="metrics_history")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    target = Column(String(255), nullable=False)
    payload = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
