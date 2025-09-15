from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    plan = Column(String(50), default="free")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    jobs = relationship("Job", back_populates="user")
    presets = relationship("Preset", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    mode = Column(String(10), nullable=False)  # "A" or "B"
    ref_key = Column(Text, nullable=False)
    tgt_key = Column(Text, nullable=False)
    status = Column(String(20), default="PENDING")  # PENDING, ANALYZING, INVERTING, RENDERING, COMPLETED, FAILED
    progress = Column(Integer, default=0)
    params = Column(JSONB)
    metrics = Column(JSONB)
    error = Column(Text)
    result_key = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="jobs")
    segments = relationship("JobSegment", back_populates="job")
    metrics_history = relationship("Metric", back_populates="job")

class JobSegment(Base):
    __tablename__ = "job_segments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    idx = Column(Integer, nullable=False)
    status = Column(String(20), default="PENDING")
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    metrics = Column(JSONB)
    
    # Relationships
    job = relationship("Job", back_populates="segments")

class Preset(Base):
    __tablename__ = "presets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    style_params = Column(JSONB, nullable=False)
    public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="presets")

class Metric(Base):
    __tablename__ = "metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    stft_dist = Column(String(20))  # Using String for float4 equivalent
    mel_dist = Column(String(20))
    lufs_err = Column(String(20))
    tp_db = Column(String(20))
    artifacts_rate = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    job = relationship("Job", back_populates="metrics_history")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    target = Column(String(255), nullable=False)
    payload = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
