"""
video_processor.py
-------------------
The main pipeline. Given a video path, this:
  1) reads it frame by frame
  2) runs Detector.track_frame() -> gives each person/vehicle a persistent
     track_id
  3) for PERSON tracks, periodically crops + runs AttributeClassifier
     (jacket / uniform / cap / helmet / shoes)
  4) accumulates first_seen / last_seen per track_id -> dwell time in seconds
  5) draws a bounding box + text label on EVERY detected person/vehicle in
     EVERY frame of the annotated output video:
        - "Person #12"  /  "Truck #5"  /  "Car #2"  etc.
        - for people, a second line with the live attribute snapshot,
          e.g. "Jacket:Y Unif:N Cap:N Helmet:Y Shoes:N"
     plus a running summary bar at the top (people/vehicle counts + vehicle
     type breakdown).
  6) writes the annotated frames with OpenCV (fast, reliable), then
     RE-ENCODES that file to H.264 so it actually plays inline in a
     browser's <video> tag (OpenCV's own "mp4v" codec output is a valid
     file but is NOT browser-playable - see utils/video_transcode.py).
  7) writes a JSON report to outputs/reports

This same class is reused for:
  - a local file already in data/videos           (routes/video_routes.py)
  - a file uploaded through the API                (routes/video_routes.py)
  - a live RTSP CCTV stream                        (routes/stream_routes.py)
because a cv2.VideoCapture(...) behaves the same whether its source is a
file path or an rtsp:// URL.
"""
import json
import time
from datetime import datetime
from pathlib import Path

import cv2

from config import settings
from services.detector import get_detector, VEHICLE_CLASS_MAP, PERSON_CLASS_ID
from services.attribute_classifier import get_attribute_classifier, ALL_ATTRIBUTE_FIELDS
from utils.draw_utils import draw_box, draw_summary_bar, attribute_line, PERSON_COLOR, VEHICLE_COLOR
from utils.video_transcode import transcode_to_h264
from utils.logger import logger
from utils.video_transcode import transcode_to_h264


class TrackState:
    """Bookkeeping for a single tracked person or vehicle."""

    def __init__(self, track_id: int, cls_label: str, first_seen_sec: float):
        self.track_id = track_id
        self.cls_label = cls_label  # "person" or a vehicle type e.g. "truck"
        self.first_seen_sec = first_seen_sec
        self.last_seen_sec = first_seen_sec
        self.attribute_votes = {field: [] for field in ALL_ATTRIBUTE_FIELDS}
        # Latest attribute snapshot (updated every ATTRIBUTE_RECHECK_EVERY_N_FRAMES),
        # used to label the live annotated video even between rechecks.
        self.last_known_attributes: dict | None = None

    def update_seen(self, t_sec: float):
        self.last_seen_sec = t_sec

    def register_attributes(self, attrs: dict):
        self.last_known_attributes = attrs
        for key, val in attrs.items():
            if val is not None:
                self.attribute_votes[key].append(val)

    @property
    def dwell_time_sec(self) -> float:
        return round(self.last_seen_sec - self.first_seen_sec, 2)

    def final_attributes(self) -> dict:
        """Majority vote across all the times we checked this person."""
        result = {}
        for key, votes in self.attribute_votes.items():
            if not votes:
                result[key] = None
            else:
                result[key] = sum(votes) > (len(votes) / 2)
        return result


class VideoProcessor:
    def __init__(self, job_id: str, video_path: Path, save_annotated_video: bool = True):
        self.job_id = job_id
        self.video_path = video_path
        self.save_annotated_video = save_annotated_video
        self.detector = get_detector()
        self.attribute_classifier = get_attribute_classifier()

        self.person_tracks: dict[int, TrackState] = {}
        self.vehicle_tracks: dict[int, TrackState] = {}

        self.progress_percent = 0.0
        self.status = "processing"
        self.error: str | None = None
        self.annotated_video_url: str | None = None

    def run(self):
        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            self.status = "failed"
            self.error = f"Could not open video source: {self.video_path}"
            logger.error(self.error)
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or None
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        writer = None
        raw_out_path = None    # OpenCV writes here first (mp4v - NOT browser playable)
        final_out_path = None  # after ffmpeg transcode, this is the browser-playable H.264 file
        if self.save_annotated_video:
            processed_dir = settings.output_dir_path / "processed_videos"
            final_out_path = processed_dir / f"{self.job_id}.mp4"
            raw_out_path = processed_dir / f"{self.job_id}_raw_temp.mp4"
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(raw_out_path), fourcc, fps, (width, height))

        frame_idx = 0
        t0 = time.time()
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break

                t_sec = frame_idx / fps
                result = self.detector.track_frame(frame)
                # frame is annotated IN PLACE inside _process_detections
                self._process_detections(result, frame, frame_idx, t_sec)

                if writer is not None:
                    vehicle_breakdown = self._current_vehicle_breakdown()
                    draw_summary_bar(frame, len(self.person_tracks), len(self.vehicle_tracks), vehicle_breakdown)
                    writer.write(frame)

                frame_idx += 1
                if total_frames:
                    self.progress_percent = round(min(99.0, frame_idx / total_frames * 100), 1)

        finally:
            cap.release()
            if writer is not None:
                writer.release()

        # ---- Transcode to browser-playable H.264 ----
        if self.save_annotated_video and raw_out_path is not None and raw_out_path.exists():
            try:
                transcode_to_h264(raw_out_path, final_out_path)
                raw_out_path.unlink(missing_ok=True)
                self.annotated_video_url = f"/outputs/processed_videos/{final_out_path.name}"
            except Exception as e:
                logger.error(f"[{self.job_id}] Transcode to H.264 failed, keeping raw file as a downloadable "
                              f"fallback (it may not play inline in the browser): {e}")
                raw_out_path.replace(final_out_path)
                self.annotated_video_url = f"/outputs/processed_videos/{final_out_path.name}"

        self.progress_percent = 100.0
        self.status = "completed"

        elapsed = round(time.time() - t0, 1)
        logger.info(f"[{self.job_id}] Finished processing {frame_idx} frames in {elapsed}s")

        self._write_report(total_duration_sec=frame_idx / fps if fps else 0)

    def _current_vehicle_breakdown(self) -> dict[str, int]:
        breakdown: dict[str, int] = {}
        for t in self.vehicle_tracks.values():
            breakdown[t.cls_label] = breakdown.get(t.cls_label, 0) + 1
        return breakdown

    def _process_detections(self, result, frame, frame_idx: int, t_sec: float):
        if result.boxes is None or result.boxes.id is None:
            return

        boxes_xyxy = result.boxes.xyxy.tolist()
        cls_ids = result.boxes.cls.tolist()
        track_ids = result.boxes.id.tolist()

        for xyxy, cls_id, track_id in zip(boxes_xyxy, cls_ids, track_ids):
            cls_id = int(cls_id)
            track_id = int(track_id)

            if cls_id == PERSON_CLASS_ID:
                self._handle_person(track_id, xyxy, frame, frame_idx, t_sec)
            elif cls_id in VEHICLE_CLASS_MAP:
                self._handle_vehicle(track_id, VEHICLE_CLASS_MAP[cls_id], xyxy, frame, t_sec)

    def _handle_person(self, track_id, xyxy, frame, frame_idx, t_sec):
        if track_id not in self.person_tracks:
            self.person_tracks[track_id] = TrackState(track_id, "person", t_sec)
        track = self.person_tracks[track_id]
        track.update_seen(t_sec)

        if frame_idx % settings.ATTRIBUTE_RECHECK_EVERY_N_FRAMES == 0:
            x1, y1, x2, y2 = map(int, xyxy)
            crop = frame[max(0, y1):y2, max(0, x1):x2]
            attrs = self.attribute_classifier.analyze_person_crop(crop)
            track.register_attributes(attrs)

        # Draw box + "Person #ID" + live attribute line on every frame,
        # using the most recently known attribute snapshot (attributes are
        # only re-checked every N frames for performance, but the label
        # stays visible on every frame in between).
        label_lines = [
            f"Person #{track_id}",
            attribute_line(track.last_known_attributes),
        ]
        draw_box(frame, xyxy, label_lines, color=PERSON_COLOR)

    def _handle_vehicle(self, track_id, vehicle_type, xyxy, frame, t_sec):
        if track_id not in self.vehicle_tracks:
            self.vehicle_tracks[track_id] = TrackState(track_id, vehicle_type, t_sec)
        self.vehicle_tracks[track_id].update_seen(t_sec)

        label_lines = [f"{vehicle_type.capitalize()} #{track_id}"]
        draw_box(frame, xyxy, label_lines, color=VEHICLE_COLOR)

    def _write_report(self, total_duration_sec: float):
        vehicle_type_counts = self._current_vehicle_breakdown()

        report = {
            "job_id": self.job_id,
            "source_video": str(self.video_path.name),
            "video_duration_sec": round(total_duration_sec, 2),
            "total_unique_persons": len([
                t for t in self.person_tracks.values()
                if t.dwell_time_sec >= settings.MIN_DWELL_SECONDS_TO_COUNT
            ]),
            "total_unique_vehicles": len(self.vehicle_tracks),
            "vehicle_type_breakdown": [{"type": k, "count": v} for k, v in vehicle_type_counts.items()],
            "persons": [
                {
                    "track_id": t.track_id,
                    "first_seen_sec": round(t.first_seen_sec, 2),
                    "last_seen_sec": round(t.last_seen_sec, 2),
                    "dwell_time_sec": t.dwell_time_sec,
                    **t.final_attributes(),
                    "attribute_confidence_note": "majority vote across periodic re-checks; open-vocabulary model, verify before compliance decisions",
                }
                for t in self.person_tracks.values()
                if t.dwell_time_sec >= settings.MIN_DWELL_SECONDS_TO_COUNT
            ],
            "vehicles": [
                {
                    "track_id": t.track_id,
                    "vehicle_type": t.cls_label,
                    "first_seen_sec": round(t.first_seen_sec, 2),
                    "last_seen_sec": round(t.last_seen_sec, 2),
                    "dwell_time_sec": t.dwell_time_sec,
                }
                for t in self.vehicle_tracks.values()
            ],
            "annotated_video_url": self.annotated_video_url,
            "raw_video_url": f"/raw-videos/{self.video_path.name}",
            "generated_at": datetime.utcnow().isoformat(),
        }

        report_path = settings.output_dir_path / "reports" / f"{self.job_id}.json"
        report_path.write_text(json.dumps(report, indent=2))
        logger.info(f"[{self.job_id}] Report written to {report_path}")