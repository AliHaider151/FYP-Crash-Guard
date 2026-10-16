from __future__ import annotations

import logging
import os
import tempfile

import cloudinary
import cloudinary.uploader
import cv2

from app.config import get_config

logger = logging.getLogger(__name__)

config = get_config()
cloudinary.config(**config.cloudinary.as_dict())


def upload_clip_to_cloudinary(frames, fps: int, clip_id) -> str | None:
    """Encode a list of frames into an MP4 clip and upload it to Cloudinary."""
    if not frames:
        logger.warning("No frames supplied for upload.")
        return None

    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)

        height, width, _ = frames[0].shape
        writer = cv2.VideoWriter(temp_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        for frame in frames:
            writer.write(frame)
        writer.release()

        response = cloudinary.uploader.upload(
            temp_path,
            resource_type="video",
            public_id=f"accident_{clip_id}",
            folder="FYP",
        )
        url = response.get("secure_url")
        logger.info("Cloudinary upload succeeded for clip %s", clip_id)
        return url
    except Exception:
        logger.exception("Cloudinary upload failed for clip %s", clip_id)
        return None
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
