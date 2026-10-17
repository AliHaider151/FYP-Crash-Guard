from __future__ import annotations

import logging
import time

from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from app.services.camera_service import load_cameras
from app.web.detection import detection_manager

logger = logging.getLogger(__name__)


@require_GET
def dashboard(request):
    return render(request, "web/dashboard.html", {"cameras": load_cameras()})


@require_POST
def start_detection(request):
    camera_name = request.POST.get("camera", "").strip()
    camera = next((item for item in load_cameras() if item.name == camera_name), None)
    if camera is None:
        return JsonResponse({"error": "Select a configured camera."}, status=400)
    if not camera.video_path.is_file():
        return JsonResponse({"error": f"Camera video was not found: {camera.video_path}"}, status=400)

    try:
        started = detection_manager.start(camera)
    except Exception as exc:
        logger.exception("Could not start detection for camera %s", camera.name)
        return JsonResponse({"error": str(exc)}, status=500)
    if not started:
        return JsonResponse({"error": "Detection is already running."}, status=409)
    return JsonResponse({"running": True})


@require_POST
def stop_detection(request):
    detection_manager.stop()
    return JsonResponse({"running": detection_manager.status()["running"]})


@require_GET
def detection_status(request):
    return JsonResponse(detection_manager.status())


@require_GET
def detection_preview(request):
    def frames():
        last_frame_number = -1
        while True:
            frame_number, frame, running = detection_manager.preview()
            if frame and frame_number != last_frame_number:
                last_frame_number = frame_number
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            if not running:
                break
            time.sleep(0.05)

    return StreamingHttpResponse(
        frames(),
        content_type="multipart/x-mixed-replace; boundary=frame",
    )
