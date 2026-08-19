"""
video_routes.py
----------------
Everything related to processing a video that is either:
  (a) already sitting in data/videos, or
  (b) uploaded by the user through the API / frontend.

Try these directly in Swagger UI at http://localhost:8000/docs
"""
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from config import settings
from models.schemas import (
    ProcessVideoRequest, JobCreatedResponse, JobStatusResponse,
    ReportResponse, VideoListResponse, JobStatus,
)
from services import job_manager
from utils.logger import logger

router = APIRouter(prefix="/api/videos", tags=["Videos"])


@router.get("/list", response_model=VideoListResponse, summary="List videos available in data/videos")
def list_videos():
    """
    Shows every video file currently sitting in the backend's data/videos folder.
    Drop a new .mp4 in there (or use /upload) and it will show up here -
    no code changes needed to point at a new test clip.
    """
    exts = {".mp4", ".avi", ".mov", ".mkv"}
    files = sorted(p.name for p in settings.video_dir_path.iterdir() if p.suffix.lower() in exts)
    return VideoListResponse(videos=files)


@router.post("/upload", response_model=VideoListResponse, summary="Upload a new video into data/videos")
async def upload_video(file: UploadFile = File(...)):
    dest = settings.video_dir_path / file.filename
    with open(dest, "wb") as f:
        f.write(await file.read())
    logger.info(f"Uploaded video saved to {dest}")
    return list_videos()


@router.post("/process", response_model=JobCreatedResponse, summary="Start processing a video by filename")
def process_video(payload: ProcessVideoRequest, background_tasks: BackgroundTasks):
    """
    `filename` must match a file already in data/videos (see /list or /upload first).
    Returns immediately with a job_id; processing runs in the background.
    """
    video_path = settings.video_dir_path / payload.filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"'{payload.filename}' not found in data/videos. Upload it first or check /api/videos/list")

    job_id = job_manager.create_job(video_path, payload.save_annotated_video, source_label=payload.filename)
    background_tasks.add_task(job_manager.run_job, job_id)

    return JobCreatedResponse(job_id=job_id, status=JobStatus.QUEUED, message="Processing started. Poll GET /api/videos/jobs/{job_id} for progress.")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse, summary="Poll job status/progress")
def get_job_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return JobStatusResponse(
        job_id=job_id,
        status=job.status,
        progress_percent=job.progress_percent,
        source=getattr(job, "_source_label", str(job.video_path)),
        error=job.error,
    )


@router.get("/jobs/{job_id}/results", response_model=ReportResponse, summary="Get full detection report once completed")
def get_job_results(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail=f"Job not finished yet (status={job.status})")

    report_path = settings.output_dir_path / "reports" / f"{job_id}.json"
    if not report_path.exists():
        raise HTTPException(status_code=500, detail="Report file missing unexpectedly")

    import json
    return JSONResponse(content=json.loads(report_path.read_text()))
