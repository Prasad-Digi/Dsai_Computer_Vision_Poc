"""
job_manager.py
---------------
Minimal in-memory job registry so the API can be "fire and poll":
  1) POST /api/videos/process  -> returns a job_id immediately
  2) frontend polls GET /api/videos/jobs/{job_id} for progress
  3) once status == "completed", GET /api/videos/jobs/{job_id}/results

NOTE for production: this dict is wiped if the server restarts, and won't
work if you run multiple backend replicas. At that point swap this module
for Redis + Celery/RQ (same public functions, different storage) - nothing
in routes/ or services/video_processor.py needs to change.
"""
import uuid
from services.video_processor import VideoProcessor

_jobs: dict[str, VideoProcessor] = {}


def create_job(video_path, save_annotated_video: bool = True, source_label: str = "") -> str:
    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = VideoProcessor(job_id, video_path, save_annotated_video)
    _jobs[job_id]._source_label = source_label or str(video_path)
    return job_id


def get_job(job_id: str) -> VideoProcessor | None:
    return _jobs.get(job_id)


def run_job(job_id: str):
    job = _jobs.get(job_id)
    if job:
        try:
            job.run()
        except Exception as e:  # keep background task from crashing silently
            job.status = "failed"
            job.error = str(e)
