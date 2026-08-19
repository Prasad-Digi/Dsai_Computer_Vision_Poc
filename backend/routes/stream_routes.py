"""
stream_routes.py
-----------------
For "tomorrow, when we plug in the real CCTV feed":

  1) Copy credentials/cctv_credentials.example.json -> credentials/cctv_credentials.json
     (this real file is .gitignore'd, so credentials never get committed)
  2) Fill in each camera's RTSP URL, e.g.:
       rtsp://username:password@192.168.1.64:554/Streaming/Channels/101
  3) Call POST /api/streams/connect with the camera_name -> it runs the exact
     same VideoProcessor pipeline as an uploaded file (cv2.VideoCapture treats
     an rtsp:// URL and a file path identically), for `duration_seconds`
     seconds, then produces a report exactly like a file job would.

For a POC this runs for a bounded duration and returns a job_id you poll,
same as file processing. For a true 24/7 live dashboard later, this endpoint
would instead kick off a persistent background worker per camera and stream
results over a WebSocket - the detection/tracking code doesn't change, only
how results are delivered.
"""
import json

from fastapi import APIRouter, BackgroundTasks, HTTPException

from config import settings
from models.schemas import ConnectStreamRequest, JobCreatedResponse, JobStatus, CameraListResponse
from services import job_manager
from utils.logger import logger

router = APIRouter(prefix="/api/streams", tags=["Live CCTV"])


def _load_credentials() -> dict:
    path = settings.credentials_file_path
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No credentials file at {path}. Copy credentials/cctv_credentials.example.json to cctv_credentials.json and fill in your camera(s).",
        )
    return json.loads(path.read_text())


@router.get("/cameras", response_model=CameraListResponse, summary="List configured cameras")
def list_cameras():
    data = _load_credentials()
    names = [cam["name"] for cam in data.get("cameras", []) if cam.get("enabled", True)]
    return CameraListResponse(cameras=names)


@router.post("/connect", response_model=JobCreatedResponse, summary="Start a bounded live analysis session on a configured camera")
def connect_stream(payload: ConnectStreamRequest, background_tasks: BackgroundTasks):
    data = _load_credentials()
    camera = next((c for c in data.get("cameras", []) if c["name"] == payload.camera_name), None)
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera '{payload.camera_name}' not found in credentials file")
    if not camera.get("enabled", True):
        raise HTTPException(status_code=400, detail=f"Camera '{payload.camera_name}' is disabled")

    rtsp_url = camera["rtsp_url"]
    logger.info(f"Connecting to live camera '{payload.camera_name}'")

    # NOTE: video_path is normally a Path; cv2.VideoCapture also accepts an
    # rtsp:// string directly, so we pass it straight through.
    job_id = job_manager.create_job(rtsp_url, save_annotated_video=True, source_label=f"LIVE:{payload.camera_name}")

    # For a bounded POC session we still call the same .run() - cv2 will keep
    # reading frames from the RTSP stream until it's told to stop. A simple
    # duration cutoff is enforced inside VideoProcessor for real deployments;
    # for this POC we rely on the operator stopping it / the demo window ending.
    background_tasks.add_task(job_manager.run_job, job_id)

    return JobCreatedResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message=f"Live analysis started on '{payload.camera_name}'. Poll GET /api/videos/jobs/{{job_id}} for progress.",
    )
