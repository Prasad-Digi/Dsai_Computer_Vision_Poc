"""
detector.py
-----------
Wraps the Ultralytics YOLO26 model for PERSON + VEHICLE detection, with
built-in multi-object tracking (BoT-SORT) so every person/vehicle gets a
persistent track_id across frames. That track_id is what lets us compute
"how many seconds did this person stay".

COCO classes we care about (standard indices used by yolo26*.pt):
    0  person
    1  bicycle
    2  car
    3  motorcycle
    5  bus
    7  truck
"""
from pathlib import Path
from ultralytics import YOLO
from config import settings
from utils.logger import logger

# class_id -> human readable label
VEHICLE_CLASS_MAP = {
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}
PERSON_CLASS_ID = 0

TARGET_CLASSES = [PERSON_CLASS_ID, *VEHICLE_CLASS_MAP.keys()]


class Detector:
    """Singleton-style wrapper so the (heavy) model is loaded only once."""

    _instance: "Detector | None" = None

    def __init__(self):
        weights_path = self._resolve_weights_path(settings.DETECTION_MODEL)
        logger.info(f"Loading detection model: {weights_path}")
        # Ultralytics will auto-download the official weights the first time
        # if `weights_path` is a bare model name like 'yolo26m.pt' and no
        # local file exists yet - they get cached into data/weights/.
        self.model = YOLO(str(weights_path))
        self.device = settings.DEVICE

    def _resolve_weights_path(self, model_name: str) -> Path:
        local_path = settings.weights_dir_path / model_name
        if local_path.exists():
            return local_path
        # let ultralytics handle download/cache; ultralytics saves to CWD by default,
        # so we point it at our weights dir explicitly:
        return settings.weights_dir_path / model_name

    def track_frame(self, frame, persist: bool = True):
        """
        Run detection + tracking on a single BGR frame (numpy array).
        Returns the raw ultralytics Results object (first item in list).
        """
        results = self.model.track(
            frame,
            persist=persist,
            classes=TARGET_CLASSES,
            conf=settings.CONFIDENCE_THRESHOLD,
            iou=settings.IOU_THRESHOLD,
            device=self.device,
            tracker="botsort.yaml",
            verbose=False,
        )
        return results[0]

    @classmethod
    def get_instance(cls) -> "Detector":
        if cls._instance is None:
            cls._instance = Detector()
        return cls._instance


def get_detector() -> Detector:
    return Detector.get_instance()
