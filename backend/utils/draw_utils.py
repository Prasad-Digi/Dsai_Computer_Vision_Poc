"""
draw_utils.py
--------------
Drawing helpers for the annotated output video.

Supports a MULTI-LINE label so each box can show:
    Line 1: "Person #12"          (or "Truck #5", "Car #2", etc.)
    Line 2: "Jacket:Y Cap:N ..."  (live attribute snapshot, person boxes only)
"""
import cv2

PERSON_COLOR = (60, 200, 60)      # green
VEHICLE_COLOR = (60, 140, 255)    # orange
UNKNOWN_ATTR_COLOR = (180, 180, 180)

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.5
FONT_THICKNESS = 1
LINE_HEIGHT = 18


def draw_box(frame, xyxy, lines: list[str], color=PERSON_COLOR):
    """
    Draws a bounding box plus a small stacked label block above it.
    `lines` is a list of strings, rendered top-to-bottom, e.g.:
        ["Person #12", "Jacket:Y Cap:N Helmet:N Shoes:N"]
    """
    x1, y1, x2, y2 = map(int, xyxy)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    if not lines:
        return frame

    # Measure the widest line so the label background fits everything
    widths = []
    for line in lines:
        (tw, _), _ = cv2.getTextSize(line, FONT, FONT_SCALE, FONT_THICKNESS)
        widths.append(tw)
    block_w = max(widths) + 10
    block_h = LINE_HEIGHT * len(lines) + 6

    label_y1 = max(0, y1 - block_h)
    cv2.rectangle(frame, (x1, label_y1), (x1 + block_w, y1), color, -1)

    for i, line in enumerate(lines):
        text_y = label_y1 + (i + 1) * LINE_HEIGHT - 4
        cv2.putText(frame, line, (x1 + 5, text_y), FONT, FONT_SCALE, (0, 0, 0), FONT_THICKNESS, cv2.LINE_AA)

    return frame


def attribute_line(attrs: dict | None) -> str:
    """
    Turns {"wearing_jacket": True, "wearing_cap": False, ...} into a compact
    display string: "Jacket:Y Cap:N Helmet:? Shoes:N"
    None/unknown (not checked yet) shows as "?".
    """
    if not attrs:
        return "checking..."

    def flag(key, short):
        v = attrs.get(key)
        symbol = "?" if v is None else ("Y" if v else "N")
        return f"{short}:{symbol}"

    return " ".join([
        flag("wearing_jacket", "Jacket"),
        flag("wearing_uniform", "Unif"),
        flag("wearing_cap", "Cap"),
        flag("wearing_helmet", "Helmet"),
        flag("wearing_shoes", "Shoes"),
    ])


def draw_summary_bar(frame, person_count: int, vehicle_count: int, vehicle_breakdown: dict[str, int] | None = None):
    h, w = frame.shape[:2]
    text = f"People: {person_count}   Vehicles: {vehicle_count}"
    if vehicle_breakdown:
        parts = ", ".join(f"{k}:{v}" for k, v in vehicle_breakdown.items())
        text += f"  ({parts})"
    cv2.rectangle(frame, (0, 0), (w, 30), (30, 30, 30), -1)
    cv2.putText(frame, text, (8, 21), FONT, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return frame
