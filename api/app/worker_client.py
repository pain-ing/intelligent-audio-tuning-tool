"""Client interface for dispatching tasks to workers."""
from celery import Celery
import os

redis_url = os.getenv("QUEUE_URL", "redis://localhost:6379/0")
celery_app = Celery("audio_api", broker=redis_url, backend=redis_url)

def process_audio_job(job_id: str, mode: str, ref_key: str, tgt_key: str, opts: dict = None):
    """Dispatch audio processing job to worker."""
    return celery_app.send_task(
        "app.worker.process_audio_job",
        args=[job_id, mode, ref_key, tgt_key, opts or {}],
        queue="audio_processing"
    )
