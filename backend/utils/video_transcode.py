"""
video_transcode.py
-------------------
cv2.VideoWriter's "mp4v" fourcc (MPEG-4 Part 2) produces a valid .mp4
FILE, but most browsers can only play H.264-encoded video inline in a
<video> tag. That mismatch is exactly why the annotated video shows up
in the player as "0:00" and never plays, even though the file itself
isn't corrupted or empty.

Fix: after OpenCV finishes writing the raw annotated frames, re-encode
the file to H.264 using a bundled ffmpeg binary (via imageio-ffmpeg), so
nothing needs to be separately installed on Windows/Mac/Linux.
"""
import subprocess
from pathlib import Path

import imageio_ffmpeg

from utils.logger import logger


def transcode_to_h264(input_path: Path, output_path: Path) -> None:
    """
    Re-encodes input_path (any format ffmpeg can read) to a browser-playable
    H.264 .mp4 at output_path. Raises RuntimeError if ffmpeg fails.
    """
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe,
        "-y",                          # overwrite output if it already exists
        "-i", str(input_path),
        "-vcodec", "libx264",
        "-pix_fmt", "yuv420p",          # widest browser/player compatibility
        "-movflags", "+faststart",      # lets playback start before full download
        str(output_path),
    ]
    logger.info(f"Transcoding annotated video to browser-compatible H.264: {output_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"ffmpeg transcode failed: {result.stderr[-2000:]}")
        raise RuntimeError(f"ffmpeg transcode failed. stderr tail: {result.stderr[-500:]}")