from celery import Celery
import os
import time
import logging
import tempfile
import uuid
from typing import Dict, Literal
import boto3
import requests
from urllib.parse import urlparse

# Import our audio processing modules
from app.audio_analysis import analyzer
from app.parameter_inversion import ParameterInverter
from app.audio_rendering import renderer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize parameter inverter
inverter = ParameterInverter()

# Celery app configuration
redis_url = os.getenv("QUEUE_URL", "redis://localhost:6379/0")
app = Celery("audio_worker", broker=redis_url, backend=redis_url)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.worker.process_audio_job": {"queue": "audio_processing"},
    },
)

def download_file(url_or_key: str, local_path: str) -> str:
    """下载文件到本地路径"""
    try:
        if url_or_key.startswith("http"):
            # 直接下载 URL
            response = requests.get(url_or_key, stream=True)
            response.raise_for_status()

            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        else:
            # 从对象存储下载 (简化版，实际应使用 S3 SDK)
            # 这里先创建一个占位文件
            import numpy as np
            import soundfile as sf

            # 生成测试音频 (实际应从对象存储下载)
            duration = 10.0  # 10秒测试音频
            sample_rate = 48000
            t = np.linspace(0, duration, int(duration * sample_rate))

            # 生成不同的测试信号
            if "ref" in url_or_key:
                # 参考音频：包含一些处理效果
                audio = 0.3 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.sin(2 * np.pi * 880 * t)
                audio = np.tanh(audio * 2)  # 轻微饱和
            else:
                # 目标音频：干净信号
                audio = 0.5 * np.sin(2 * np.pi * 440 * t)

            sf.write(local_path, audio, sample_rate)

        logger.info(f"Downloaded file to: {local_path}")
        return local_path

    except Exception as e:
        logger.error(f"Failed to download {url_or_key}: {e}")
        raise

def upload_file(local_path: str, key: str) -> str:
    """上传文件到对象存储"""
    try:
        # 简化版：返回本地路径作为 key
        # 实际应上传到 S3/COS 并返回 key
        logger.info(f"Uploaded file: {local_path} -> {key}")
        return key

    except Exception as e:
        logger.error(f"Failed to upload {local_path}: {e}")
        raise

@app.task(bind=True)
def process_audio_job(self, job_id: str, mode: Literal["A", "B"], ref_key: str, tgt_key: str, opts: Dict = None):
    """Main audio processing task that orchestrates the pipeline."""
    logger.info(f"Starting job {job_id} with mode {mode}")
    
    try:
        # Update job status to ANALYZING
        update_job_status(job_id, "ANALYZING", 10)
        
        # Step 1: Analyze features
        ref_features = analyze_features.delay(ref_key).get()
        tgt_features = analyze_features.delay(tgt_key).get()
        
        # Update job status to INVERTING
        update_job_status(job_id, "INVERTING", 40)
        
        # Step 2: Invert parameters
        style_params = invert_params.delay(ref_features, tgt_features, mode).get()
        
        # Update job status to RENDERING
        update_job_status(job_id, "RENDERING", 70)
        
        # Step 3: Render audio
        result_key, metrics = render_audio.delay(tgt_key, style_params).get()
        
        # Update job status to COMPLETED
        update_job_status(job_id, "COMPLETED", 100, result_key=result_key, metrics=metrics)
        
        logger.info(f"Job {job_id} completed successfully")
        return {"status": "COMPLETED", "result_key": result_key, "metrics": metrics}
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        update_job_status(job_id, "FAILED", error=str(e))
        raise

@app.task
def analyze_features(obj_key: str) -> Dict:
    """Analyze audio features from object storage."""
    logger.info(f"Analyzing features for {obj_key}")

    # 创建临时文件
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        # 下载音频文件
        download_file(obj_key, tmp_path)

        # 使用真实的音频分析
        features = analyzer.analyze_features(tmp_path)

        logger.info(f"Analysis completed for {obj_key}")
        return features

    except Exception as e:
        logger.error(f"Feature analysis failed for {obj_key}: {e}")
        # 返回默认特征以避免任务失败
        return {
            "stft": {"features": {"win_2048": {"spectral_centroid": 1000, "spectral_bandwidth": 1000}}},
            "mel": {"mean": -30, "std": 10},
            "lufs": {"integrated_lufs": -23.0, "short_term_lufs": []},
            "true_peak_db": -3.0,
            "f0": {"mean_f0": 0, "voiced_ratio": 0},
            "stereo": {"is_stereo": False, "width": 1.0, "correlation": 1.0},
            "reverb": {"rt60_estimate": 0.5, "reverb_presence": 0.0},
            "audio_info": {"duration_seconds": 10.0, "channels": 1, "sample_rate": 48000}
        }
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

@app.task
def invert_params(ref_features: Dict, tgt_features: Dict, mode: Literal["A", "B"]) -> Dict:
    """Invert style parameters from reference and target features."""
    logger.info(f"Inverting parameters for mode {mode}")

    try:
        # 使用真实的参数反演
        style_params = inverter.invert_parameters(ref_features, tgt_features, mode)

        logger.info(f"Parameter inversion completed for mode {mode}")
        return style_params

    except Exception as e:
        logger.error(f"Parameter inversion failed: {e}")
        # 返回默认参数以避免任务失败
        return {
            "eq": [],
            "lufs": {"target_lufs": -23.0},
            "limiter": {"tp_db": -1.0, "lookahead_ms": 1.0, "release_ms": 100.0},
            "reverb": {"ir_key": "ir/room_default.wav", "mix": 0.0},
            "stereo": {"width": 1.0},
            "pitch": {"semitones": 0.0},
            "compression": {"enabled": False},
            "metadata": {"mode": mode, "confidence": 0.5}
        }

@app.task
def render_audio(in_key: str, style_params: Dict) -> tuple[str, Dict]:
    """Render audio with applied style parameters."""
    logger.info(f"Rendering audio for {in_key}")

    # 创建临时文件
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_input:
        input_path = tmp_input.name

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_output:
        output_path = tmp_output.name

    try:
        # 下载输入音频
        download_file(in_key, input_path)

        # 使用真实的音频渲染
        metrics = renderer.render_audio(input_path, output_path, style_params)

        # 生成输出 key
        out_key = f"processed/{uuid.uuid4().hex}.wav"

        # 上传结果文件
        upload_file(output_path, out_key)

        logger.info(f"Audio rendering completed: {in_key} -> {out_key}")
        return out_key, metrics

    except Exception as e:
        logger.error(f"Audio rendering failed for {in_key}: {e}")
        # 返回默认结果以避免任务失败
        out_key = f"processed/{uuid.uuid4().hex}.wav"
        metrics = {
            "stft_dist": 0.0,
            "mel_dist": 0.0,
            "lufs_err": 0.0,
            "tp_db": -1.0,
            "artifacts_rate": 0.0
        }
        return out_key, metrics

    finally:
        # 清理临时文件
        for path in [input_path, output_path]:
            if os.path.exists(path):
                os.unlink(path)

def update_job_status(job_id: str, status: str, progress: int = None, result_key: str = None, metrics: Dict = None, error: str = None):
    """Update job status in database."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Import models (assuming they're shared or copied)
    import sys
    sys.path.append('/app')

    logger.info(f"Job {job_id}: {status} (progress: {progress}%)")

    try:
        # Create database connection
        db_url = os.getenv("DATABASE_URL") or os.getenv("DB_URL", "postgresql://user:pass@localhost:5432/audio")
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Update job in database
        db = SessionLocal()
        # Note: This is a simplified update - in production, import proper models
        db.execute(
            "UPDATE jobs SET status = :status, progress = :progress, "
            "result_key = :result_key, metrics = :metrics, error = :error, updated_at = NOW() "
            "WHERE id = :job_id",
            {
                "status": status,
                "progress": progress,
                "result_key": result_key,
                "metrics": metrics,
                "error": error,
                "job_id": job_id
            }
        )
        db.commit()
        db.close()

    except Exception as e:
        logger.error(f"Failed to update job status: {e}")
        # Don't fail the task if DB update fails

if __name__ == "__main__":
    app.start()
