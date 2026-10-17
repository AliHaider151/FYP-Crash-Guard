from __future__ import annotations

import logging
import threading

import cv2

from app.services.camera_service import CameraConfig
from app.services.detection_service import start_detection

logger = logging.getLogger(__name__)


class DetectionManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._status = "Status: Idle"
        self._error: str | None = None
        self._latest_frame = b""
        self._frame_number = 0
        self._stop_event: threading.Event | None = None

    def start(self, camera: CameraConfig) -> bool:
        with self._lock:
            if self._running:
                return False

            self._running = True
            self._status = "Status: Starting..."
            self._error = None
            self._latest_frame = b""
            self._frame_number = 0
            try:
                self._stop_event = start_detection(
                    self._publish_frame,
                    self._set_status,
                    camera.name,
                    camera.longitude,
                    camera.latitude,
                    str(camera.video_path),
                    self._finish,
                )
            except Exception as exc:
                self._running = False
                self._stop_event = None
                self._status = "Status: Error"
                self._error = str(exc)
                raise
            return True

    def stop(self) -> bool:
        with self._lock:
            if not self._running:
                return False
            if self._stop_event is not None:
                self._stop_event.set()
            self._status = "Status: Stopping..."
            return True

    def status(self) -> dict[str, str | bool | None]:
        with self._lock:
            return {
                "running": self._running,
                "status": self._status,
                "error": self._error,
            }

    def preview(self) -> tuple[int, bytes, bool]:
        with self._lock:
            return self._frame_number, self._latest_frame, self._running

    def _publish_frame(self, frame) -> None:
        encoded, buffer = cv2.imencode(".jpg", frame)
        if not encoded:
            logger.error("OpenCV could not encode a detection preview frame")
            return
        with self._lock:
            self._latest_frame = buffer.tobytes()
            self._frame_number += 1

    def _set_status(self, status: str) -> None:
        with self._lock:
            self._status = status

    def _finish(self, error: str | None) -> None:
        with self._lock:
            self._running = False
            self._stop_event = None
            self._error = error
            self._status = "Status: Error" if error else "Status: Idle"


detection_manager = DetectionManager()
