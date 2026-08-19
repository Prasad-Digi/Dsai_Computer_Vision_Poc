"""
schemas.py
----------
All request/response models. FastAPI uses these to:
  1) validate incoming requests
  2) auto-generate the Swagger UI (/docs) so you can see & test the exact
     shape of every request and response without writing a frontend first.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceType(str, Enum):
    LOCAL_FILE = "local_file"   # a video already sitting in data/videos
    UPLOAD = "upload"           # a video uploaded via the API
    RTSP = "rtsp"               # a live CCTV / IP camera stream


# ---------- Requests ----------

class ProcessVideoRequest(BaseModel):
    filename: str = Field(..., description="Name of a video file already present in data/videos, e.g. 'lobby_test.mp4'")
    save_annotated_video: bool = Field(True, description="If true, writes a bounding-box-annotated .mp4 to outputs/processed_videos")


class ConnectStreamRequest(BaseModel):
    camera_name: str = Field(..., description="Key matching an entry in credentials/cctv_credentials.json")
    duration_seconds: Optional[int] = Field(60, description="How long to run live analysis before auto-stopping (safety limit for POC)")


# ---------- Responses ----------

class JobCreatedResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress_percent: float
    source: str
    error: Optional[str] = None


class VehicleTypeCount(BaseModel):
    type: str
    count: int


class PersonRecord(BaseModel):
    track_id: int
    first_seen_sec: float
    last_seen_sec: float
    dwell_time_sec: float
    wearing_jacket: Optional[bool] = None
    wearing_uniform: Optional[bool] = None
    wearing_cap: Optional[bool] = None
    wearing_helmet: Optional[bool] = None
    wearing_shoes: Optional[bool] = None
    attribute_confidence_note: Optional[str] = None


class VehicleRecord(BaseModel):
    track_id: int
    vehicle_type: str
    first_seen_sec: float
    last_seen_sec: float
    dwell_time_sec: float


class ReportResponse(BaseModel):
    job_id: str
    source_video: str
    video_duration_sec: float
    total_unique_persons: int
    total_unique_vehicles: int
    vehicle_type_breakdown: list[VehicleTypeCount]
    persons: list[PersonRecord]
    vehicles: list[VehicleRecord]
    annotated_video_url: Optional[str] = None
    raw_video_url: Optional[str] = None
    generated_at: str


class VideoListResponse(BaseModel):
    videos: list[str]


class CameraListResponse(BaseModel):
    cameras: list[str]
