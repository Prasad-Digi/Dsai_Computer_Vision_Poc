"""
config.py
---------
Single source of truth for all backend settings.
Reads from a `.env` file (see `.env.example`) so nothing is hard-coded.

Why this matters for you:
- Want to swap the YOLO model?            -> change DETECTION_MODEL in .env
- Want to point at a different video?      -> handled per-request (see routes/video_routes.py),
                                               VIDEO_DIR is just the default folder we look in.
- Want to run on GPU later?                -> change DEVICE=cuda:0 in .env
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- Server ----
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ---- Models ----
    DETECTION_MODEL: str = "yolo26m.pt"
    ATTRIBUTE_MODEL: str = "yoloe-26m-seg.pt"
    DEVICE: str = "cpu"
    CONFIDENCE_THRESHOLD: float = 0.35
    IOU_THRESHOLD: float = 0.5

    # ---- Paths (relative to backend/ folder) ----
    VIDEO_DIR: str = "data/videos"
    WEIGHTS_DIR: str = "data/weights"
    OUTPUT_DIR: str = "outputs"
    CCTV_CREDENTIALS_FILE: str = "credentials/cctv_credentials.json"

    # ---- Business logic ----
    MIN_DWELL_SECONDS_TO_COUNT: float = 1.0
    ATTRIBUTE_RECHECK_EVERY_N_FRAMES: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def video_dir_path(self) -> Path:
        p = BASE_DIR / self.VIDEO_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def weights_dir_path(self) -> Path:
        p = BASE_DIR / self.WEIGHTS_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def output_dir_path(self) -> Path:
        p = BASE_DIR / self.OUTPUT_DIR
        p.mkdir(parents=True, exist_ok=True)
        (p / "processed_videos").mkdir(exist_ok=True)
        (p / "reports").mkdir(exist_ok=True)
        return p

    @property
    def credentials_file_path(self) -> Path:
        return BASE_DIR / self.CCTV_CREDENTIALS_FILE


settings = Settings()
