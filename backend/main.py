"""
main.py
-------
Run with:   uvicorn main:app --reload --port 8000
Then open:  http://localhost:8000/docs   <- Swagger UI (test every endpoint here)
            http://localhost:8000/redoc  <- alternative docs view
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from routes import video_routes, stream_routes, health_routes
from utils.logger import logger

app = FastAPI(
    title="Crowd & Vehicle Vision Analytics API",
    description=(
        "POC backend for detecting people, vehicles, dwell time and PPE/uniform "
        "attributes from recorded video or live CCTV, powered by Ultralytics YOLO26."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve annotated output videos + JSON reports as static files so the
# frontend (or Swagger) can play/download them directly, e.g.:
#   http://localhost:8000/outputs/processed_videos/<job_id>.mp4
app.mount("/outputs", StaticFiles(directory=str(settings.output_dir_path)), name="outputs")

# Serve the RAW input videos too, so the frontend can preview the original
# clip (before annotation) right after picking/uploading it, e.g.:
#   http://localhost:8000/raw-videos/sample_test_video.mp4
app.mount("/raw-videos", StaticFiles(directory=str(settings.video_dir_path)), name="raw-videos")

app.include_router(health_routes.router)
app.include_router(video_routes.router)
app.include_router(stream_routes.router)


@app.on_event("startup")
def on_startup():
    logger.info("Backend starting up...")
    logger.info(f"Video dir:   {settings.video_dir_path}")
    logger.info(f"Weights dir: {settings.weights_dir_path}")
    logger.info(f"Output dir:  {settings.output_dir_path}")
    # Models are lazy-loaded on first request (see services/detector.py &
    # services/attribute_classifier.py) so the server starts instantly even
    # before weights are downloaded.
