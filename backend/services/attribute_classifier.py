"""
attribute_classifier.py
------------------------
"jacket", "cap", "helmet", "uniform", "shoes" are NOT standard COCO classes,
so a normal yolo26*.pt detector has no idea what they are. Two ways to solve
this:

  OPTION A (used here, fastest to POC):
    Use YOLOE-26 - Ultralytics' open-vocabulary model. You give it a list of
    free-text class names at runtime (no training needed) and it will look
    for exactly those things. Good enough for a proof of concept and to
    validate the idea before investing in a custom dataset.

  OPTION B (recommended for production accuracy):
    Fine-tune a small yolo26 classification/detection head on your own
    labelled images of your staff/site (uniform vs no uniform, cap vs no
    cap, helmet vs no helmet, PPE shoes vs regular shoes). Swap
    ATTRIBUTE_MODEL in .env to your trained weights when ready - the rest
    of the pipeline doesn't change.

This service crops each PERSON bounding box out of the frame and asks the
open-vocabulary model "is any of these visible in this crop?".

NOTE: "cap" and "helmet" are tracked as SEPARATE attributes (a safety
helmet and a baseball-style cap mean very different things for compliance
reporting), unlike an earlier version of this file which merged them.
"""
from pathlib import Path
import numpy as np
from ultralytics import YOLOE
from config import settings
from utils.logger import logger

ATTRIBUTE_PROMPTS = [
    "jacket",
    "safety vest",
    "uniform shirt",
    "cap",
    "helmet",
    "safety helmet",
    "shoes",
    "boots",
    "sneakers",
]

# Map raw prompt hits -> the fields we report back on each person.
# "cap" and "helmet" are intentionally separate fields.
ATTRIBUTE_GROUPS = {
    "wearing_jacket": {"jacket", "safety vest"},
    "wearing_uniform": {"uniform shirt", "safety vest"},
    "wearing_cap": {"cap"},
    "wearing_helmet": {"helmet", "safety helmet"},
    "wearing_shoes": {"shoes", "boots", "sneakers"},
}

ALL_ATTRIBUTE_FIELDS = list(ATTRIBUTE_GROUPS.keys())


class AttributeClassifier:
    _instance: "AttributeClassifier | None" = None

    def __init__(self):
        weights_path = settings.weights_dir_path / settings.ATTRIBUTE_MODEL
        logger.info(f"Loading open-vocabulary attribute model: {weights_path}")
        self.model = YOLOE(str(weights_path))
        self.model.set_classes(ATTRIBUTE_PROMPTS, self.model.get_text_pe(ATTRIBUTE_PROMPTS))
        self.device = settings.DEVICE

    def analyze_person_crop(self, crop: np.ndarray) -> dict:
        """
        crop: BGR numpy image of just the person's bounding box.
        Returns dict like {"wearing_jacket": True, "wearing_helmet": False, ...}
        """
        if crop is None or crop.size == 0:
            return {k: None for k in ALL_ATTRIBUTE_FIELDS}

        results = self.model.predict(crop, conf=0.25, device=self.device, verbose=False)[0]
        found_labels = set()
        if results.boxes is not None:
            for cls_id in results.boxes.cls.tolist():
                found_labels.add(ATTRIBUTE_PROMPTS[int(cls_id)])

        return {
            field: bool(found_labels & keywords)
            for field, keywords in ATTRIBUTE_GROUPS.items()
        }

    @classmethod
    def get_instance(cls) -> "AttributeClassifier":
        if cls._instance is None:
            cls._instance = AttributeClassifier()
        return cls._instance


def get_attribute_classifier() -> AttributeClassifier:
    return AttributeClassifier.get_instance()
