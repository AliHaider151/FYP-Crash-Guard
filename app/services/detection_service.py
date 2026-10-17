from __future__ import annotations

import logging
import queue
import threading
import time
from collections import deque
from collections.abc import Callable

import cv2

from app.config import get_config
from app.models.yolo_model import get_model
from app.services.cloudinary_service import upload_clip_to_cloudinary
from app.services.firebase_service import (
    get_all_user_tokens,
    save_metadata_to_firestore,
    save_verification_to_firestore,
    send_fcm_notification,
)
from app.services.incident_verification_service import sample_incident_frames, verify_sampled_incident

logger = logging.getLogger(__name__)

ACCIDENT_CLASSES = ["Accident", "mild", "moderate", "severe"]
BUFFER_SECONDS = 10
AFTER_SECONDS = 10
DETECTION_INTERVAL = 3
DETECTION_MAX_WIDTH = 640
DETECTION_MAX_HEIGHT = 360

upload_queue: queue.Queue = queue.Queue()
verification_queue: queue.Queue = queue.Queue()
last_accident_time = 0.0


def _start_verification_worker() -> None:
    def worker() -> None:
        while True:
            item = verification_queue.get()
            if item is None:
                verification_queue.task_done()
                break
            try:
                clip_id, sampled_frames, total_frame_count, boxes_info = item
                logger.info("Starting secondary incident verification for clip %s", clip_id)
                result = verify_sampled_incident(sampled_frames, total_frame_count, boxes_info)
                save_verification_to_firestore(clip_id, result)
                logger.info("Secondary verification saved for clip %s", clip_id)
            except Exception:
                logger.exception("Could not complete secondary verification for clip %s", item[0])
            finally:
                verification_queue.task_done()

    threading.Thread(target=worker, name="incident-verification-worker", daemon=True).start()


def _start_upload_worker() -> None:
    def worker() -> None:
        while True:
            item = upload_queue.get()
            if item is None:
                break
            try:
                frames, fps, clip_id, boxes_info, address, longitude, latitude = item
                url = upload_clip_to_cloudinary(frames, fps, clip_id)
                accident_boxes = [box for box in boxes_info if box["cls_name"] in ACCIDENT_CLASSES]
                best_box = max(accident_boxes, key=lambda b: b["conf"], default={"cls_name": None, "conf": 0})
                accident_class = best_box.get("cls_name")
                accident_confidence = float(best_box.get("conf", 0.0))

                save_metadata_to_firestore(
                    clip_id,
                    url,
                    address,
                    accident_confidence,
                    accident_class,
                    longitude,
                    latitude,
                )
                logger.info("Primary incident metadata saved for clip %s", clip_id)
                verification_settings = get_config().incident_verification
                sampled_frames = sample_incident_frames(frames, verification_settings.frame_count)
                verification_queue.put((clip_id, sampled_frames, len(frames), boxes_info))
                logger.info("Queued %d sampled frames for verification of clip %s", len(sampled_frames), clip_id)

                for token in get_all_user_tokens():
                    try:
                        send_fcm_notification(
                            token,
                            "🚨 Accident Detected",
                            f"An accident has been reported near {address}.",
                        )
                    except Exception:
                        logger.exception("Failed to send FCM notification to token: %s", token)

                logger.info("Primary notification flow completed for clip %s", clip_id)
            except Exception:
                logger.exception("Error in upload worker")
            finally:
                upload_queue.task_done()

    threading.Thread(target=worker, daemon=True).start()


_start_upload_worker()
_start_verification_worker()


def extract_boxes_info(boxes):
    model = get_model()
    info = []
    try:
        for box in boxes:
            cls_id = int(box.cls)
            conf = float(box.conf)
            cls_name = model.names[cls_id] if cls_id < len(model.names) else "Unknown"
            info.append({"cls_name": cls_name, "conf": conf})
    except Exception:
        logger.exception("Failed to extract detection metadata")
    return info


def should_run_detection(frame_count: int, interval: int = DETECTION_INTERVAL) -> bool:
    return frame_count % interval == 0


def prepare_detection_frame(frame, max_width: int = DETECTION_MAX_WIDTH, max_height: int = DETECTION_MAX_HEIGHT):
    height, width = frame.shape[:2]
    scale = min(max_width / width, max_height / height) if width > 0 and height > 0 else 1.0

    if scale < 1.0:
        new_width = max(1, int(round(width * scale)))
        new_height = max(1, int(round(height * scale)))
        return cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

    return frame


def start_detection(
    on_frame: Callable,
    on_status: Callable[[str], None],
    name: str,
    longitude: float,
    latitude: float,
    video_path: str,
    on_finished: Callable[[str | None], None],
) -> threading.Event:
    global last_accident_time
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        cap.release()
        raise IOError(f"Unable to open video file: {video_path}")

    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    frame_buffer = deque(maxlen=fps * BUFFER_SECONDS)
    stop_event = threading.Event()

    def report_status(text: str) -> None:
        try:
            on_status(text)
        except Exception:
            logger.exception("Failed to update detection status")

    def detection_loop() -> None:
        nonlocal fps
        global last_accident_time

        frame_count = 0
        is_recording = False
        recording_start_time = 0.0
        accident_frames = []
        incident_boxes_info = []
        error = None
        try:
            while cap.isOpened() and not stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_buffer.append(frame)
                frame_count += 1
                current_time = time.time()

                if should_run_detection(frame_count):
                    detection_frame = prepare_detection_frame(frame)
                    results = get_model().predict(detection_frame, conf=0.25, verbose=False)
                    annotated = results[0].plot()
                    boxes_info = extract_boxes_info(results[0].boxes)
                    accident_detected = any(box["cls_name"] in ACCIDENT_CLASSES for box in boxes_info)
                else:
                    annotated = frame
                    boxes_info = []
                    accident_detected = False

                if accident_detected and not is_recording and (current_time - last_accident_time > AFTER_SECONDS):
                    report_status("Status: Accident Detected!")
                    logger.info("Accident detected at frame %s. Recording clip...", frame_count)
                    is_recording = True
                    recording_start_time = time.time()
                    accident_frames = []
                    incident_boxes_info = [box.copy() for box in boxes_info if box["cls_name"] in ACCIDENT_CLASSES]
                elif not accident_detected and not is_recording:
                    report_status("Status: Monitoring...")

                if is_recording:
                    accident_frames.append(frame)
                    if accident_detected:
                        for box in boxes_info:
                            if box["cls_name"] not in ACCIDENT_CLASSES:
                                continue
                            existing = next(
                                (item for item in incident_boxes_info if item["cls_name"] == box["cls_name"]),
                                None,
                            )
                            if existing is None:
                                incident_boxes_info.append(box.copy())
                            elif box["conf"] > existing["conf"]:
                                existing["conf"] = box["conf"]
                    if time.time() - recording_start_time >= AFTER_SECONDS:
                        all_frames = list(frame_buffer) + accident_frames
                        clip_id = int(time.time() * 1000)
                        upload_queue.put((all_frames, fps, clip_id, incident_boxes_info, name, longitude, latitude))
                        logger.info("Queued incident clip %s with %d frames for upload", clip_id, len(all_frames))
                        is_recording = False
                        accident_frames = []
                        incident_boxes_info = []
                        last_accident_time = time.time()
                        report_status("Status: Idle")
                        logger.info("Uploaded clip ID: %s", clip_id)

                if frame_count % 2 == 0:
                    try:
                        on_frame(annotated)
                    except Exception:
                        logger.exception("Failed to update detection preview")

                time.sleep(1.0 / max(fps, 1))
        except Exception as exc:
            error = str(exc)
            logger.exception("Detection processing failed")
        finally:
            cap.release()
            report_status("Status: Error" if error else "Status: Idle")
            try:
                on_finished(error)
            except Exception:
                logger.exception("Failed to finalize detection session")

    threading.Thread(target=detection_loop, daemon=True).start()
    return stop_event
