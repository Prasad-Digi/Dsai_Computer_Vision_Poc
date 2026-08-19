from fastapi import APIRouter
from config import settings

router = APIRouter(tags=["Health"])


@router.get("/api/health", summary="Quick check that the API + config are alive")
def health():
    return {
        "status": "ok",
        "detection_model": settings.DETECTION_MODEL,
        "attribute_model": settings.ATTRIBUTE_MODEL,
        "device": settings.DEVICE,
    }
