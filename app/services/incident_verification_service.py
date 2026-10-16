from __future__ import annotations

import base64
import json
import logging
import random
import time
from typing import Any

import cv2
import numpy as np
import requests

from app.config import IncidentVerificationConfig, get_config

logger = logging.getLogger(__name__)

VERDICTS = {
    "likely_accident",
    "likely_fire_or_hazard",
    "likely_false_positive",
    "uncertain",
}
SEVERITIES = {"low", "moderate", "high", "critical", "unknown"}
RECOMMENDED_ACTIONS = {
    "continue_monitoring",
    "request_more_frames",
    "human_review",
    "urgent_alert_review",
}
INCIDENT_TYPES = {
    "vehicle_collision",
    "vehicle_rollover",
    "fire_or_explosion",
    "smoke",
    "pedestrian_or_cyclist_incident",
    "vehicle_departure_from_road",
    "multi_vehicle_pileup",
    "stationary_or_disabled_vehicle",
    "road_hazard",
    "secondary_hazard",
    "other_emergency",
}

SYSTEM_PROMPT = """You are Crash Guard's secondary incident-verification component. Review the supplied ordered traffic-camera frames and primary detector labels. Distinguish visible evidence from assumptions, consider benign alternatives, do not infer injuries or causes, and never call a visible fire or immediate road hazard a false positive. Return valid JSON only with exactly these keys:
verdict (likely_accident|likely_fire_or_hazard|likely_false_positive|uncertain), confidence (number 0-100), incident_types (array of supported strings), visual_evidence (array of strings), alternative_explanations (array of strings), hazards_detected (array of strings), severity (low|moderate|high|critical|unknown), requires_more_frames (boolean), recommended_action (continue_monitoring|request_more_frames|human_review|urgent_alert_review), reasoning_summary (string).
Use these incident_types identifiers when applicable: vehicle_collision, vehicle_rollover, fire_or_explosion, smoke, pedestrian_or_cyclist_incident, vehicle_departure_from_road, multi_vehicle_pileup, stationary_or_disabled_vehicle, road_hazard, secondary_hazard, other_emergency.
Use uncertain and human_review when evidence is ambiguous or insufficient. Recommend urgent_alert_review for visible flames or immediately threatening hazards. Do not claim motion from one frame."""


def sample_frame_indices(frame_count: int, sample_count: int, rng: random.Random | None = None) -> list[int]:
    if frame_count <= 0:
        return []
    count = min(frame_count, max(1, sample_count))
    randomizer = rng or random.SystemRandom()
    selected = []
    for bucket in range(count):
        bucket_start = bucket * frame_count // count
        bucket_end = (bucket + 1) * frame_count // count
        selected.append(randomizer.randrange(bucket_start, max(bucket_start + 1, bucket_end)))
    return sorted(set(selected))


def sample_incident_frames(frames: list[np.ndarray], sample_count: int) -> list[tuple[int, np.ndarray]]:
    indices = sample_frame_indices(len(frames), sample_count)
    return [(index, frames[index]) for index in indices]


def _frame_data_url(frame: np.ndarray) -> str:
    height, width = frame.shape[:2]
    scale = min(768 / max(width, 1), 768 / max(height, 1), 1.0)
    if scale < 1.0:
        frame = cv2.resize(
            frame,
            (max(1, round(width * scale)), max(1, round(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
    encoded, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 78])
    if not encoded:
        raise ValueError("Could not encode sampled frame as JPEG")
    image = base64.b64encode(buffer.tobytes()).decode("ascii")
    return f"data:image/jpeg;base64,{image}"


def _empty_result(reason: str, *, requires_more_frames: bool = True) -> dict[str, Any]:
    return {
        "verdict": "uncertain",
        "confidence": 0,
        "incident_types": [],
        "visual_evidence": [],
        "alternative_explanations": [],
        "hazards_detected": [],
        "severity": "unknown",
        "requires_more_frames": requires_more_frames,
        "recommended_action": "human_review",
        "reasoning_summary": reason,
    }


def validate_verification_result(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Verifier response must be a JSON object")

    required = {
        "verdict",
        "confidence",
        "incident_types",
        "visual_evidence",
        "alternative_explanations",
        "hazards_detected",
        "severity",
        "requires_more_frames",
        "recommended_action",
        "reasoning_summary",
    }
    if set(payload) != required:
        raise ValueError("Verifier response keys do not match the required schema")
    if not isinstance(payload["verdict"], str) or payload["verdict"] not in VERDICTS:
        raise ValueError("Verifier returned an unsupported verdict")
    confidence = payload["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 100:
        raise ValueError("Verifier confidence must be a number between 0 and 100")
    if not isinstance(payload["severity"], str) or payload["severity"] not in SEVERITIES:
        raise ValueError("Verifier returned an unsupported severity")
    if not isinstance(payload["recommended_action"], str) or payload["recommended_action"] not in RECOMMENDED_ACTIONS:
        raise ValueError("Verifier returned an unsupported recommended action")
    if not isinstance(payload["requires_more_frames"], bool):
        raise ValueError("requires_more_frames must be a boolean")
    for key in ("incident_types", "visual_evidence", "alternative_explanations", "hazards_detected"):
        if not isinstance(payload[key], list) or not all(isinstance(value, str) for value in payload[key]):
            raise ValueError(f"{key} must be an array of strings")
    if not all(value in INCIDENT_TYPES for value in payload["incident_types"]):
        raise ValueError("Verifier returned an unsupported incident type")
    if not isinstance(payload["reasoning_summary"], str):
        raise ValueError("reasoning_summary must be a string")
    return payload


def _apply_hazard_safety_guard(result: dict[str, Any]) -> dict[str, Any]:
    hazard_types = {"fire_or_explosion", "road_hazard", "secondary_hazard"}
    reported_hazard = bool(result["hazards_detected"]) or bool(hazard_types.intersection(result["incident_types"]))
    if result["verdict"] == "likely_false_positive" and reported_hazard:
        result["verdict"] = "likely_fire_or_hazard"
        result["recommended_action"] = "urgent_alert_review"
        result["reasoning_summary"] = (
            "A hazard was reported in the structured visual evidence, so it is not classified as a false positive. "
            + result["reasoning_summary"]
        )
    if "fire_or_explosion" in result["incident_types"]:
        result["verdict"] = "likely_fire_or_hazard"
        result["recommended_action"] = "urgent_alert_review"
    return result


def _request_content(response_json: dict[str, Any]) -> str:
    try:
        content = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Vision API response is missing choices[0].message.content") from exc
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [part["text"] for part in content if isinstance(part, dict) and isinstance(part.get("text"), str)]
        if text_parts:
            return "\n".join(text_parts)
    raise ValueError("Vision API returned unsupported message content")


def _parse_model_json(content: str) -> dict[str, Any]:
    candidate = content.strip()
    if candidate.startswith("```"):
        candidate = candidate.split("\n", 1)[-1]
        if candidate.endswith("```"):
            candidate = candidate[:-3].strip()
    try:
        return validate_verification_result(json.loads(candidate))
    except json.JSONDecodeError as exc:
        raise ValueError("Vision model did not return valid JSON") from exc


def verify_incident(
    frames: list[np.ndarray],
    primary_detections: list[dict[str, Any]],
    *,
    config: IncidentVerificationConfig | None = None,
    post=requests.post,
) -> dict[str, Any]:
    settings = config or get_config().incident_verification
    if not settings.enabled:
        logger.info("Incident verification disabled; retaining primary detector result")
        return _empty_result("Secondary visual verification is disabled.")
    if not settings.api_key:
        logger.warning("Incident verification unavailable: AMD_API_KEY is not configured")
        return _empty_result("Verification unavailable because the AMD API key is not configured.")
    if not frames:
        logger.warning("Incident verification has no frames to review")
        return _empty_result("Verification unavailable because the incident clip contained no frames.")

    sampled = sample_incident_frames(frames, settings.frame_count)
    return verify_sampled_incident(sampled, len(frames), primary_detections, config=settings, post=post)


def verify_sampled_incident(
    sampled: list[tuple[int, np.ndarray]],
    total_frame_count: int,
    primary_detections: list[dict[str, Any]],
    *,
    config: IncidentVerificationConfig | None = None,
    post=requests.post,
) -> dict[str, Any]:
    settings = config or get_config().incident_verification
    if not settings.enabled:
        logger.info("Incident verification disabled; retaining primary detector result")
        return _empty_result("Secondary visual verification is disabled.")
    if not settings.api_key:
        logger.warning("Incident verification unavailable: AMD_API_KEY is not configured")
        return _empty_result("Verification unavailable because the AMD API key is not configured.")
    if not sampled:
        logger.warning("Incident verification has no sampled frames to review")
        return _empty_result("Verification unavailable because the incident clip contained no frames.")

    logger.info(
        "Incident verification sampling selected %d of %d frames at indices %s",
        len(sampled),
        total_frame_count,
        [index for index, _ in sampled],
    )
    content: list[dict[str, Any]] = [
        {"type": "text", "text": f"Primary detector labels: {json.dumps(primary_detections, ensure_ascii=True)}. Images are ordered chronologically and marked by sampled frame index."}
    ]
    for index, frame in sampled:
        content.append({"type": "text", "text": f"Sampled frame index: {index}"})
        content.append({"type": "image_url", "image_url": {"url": _frame_data_url(frame)}})

    endpoint = f"{settings.api_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
    }
    logger.info("Requesting secondary incident review from model %s", settings.model)
    started = time.monotonic()
    try:
        response = post(
            endpoint,
            headers={"Authorization": f"Bearer {settings.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=settings.timeout_seconds,
        )
        response.raise_for_status()
        result = _apply_hazard_safety_guard(_parse_model_json(_request_content(response.json())))
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        logger.exception("Secondary incident verification failed; primary alert remains unchanged: %s", exc)
        return _empty_result(f"Verification unavailable: {type(exc).__name__}.")

    logger.info(
        "Secondary incident review completed in %.2fs: verdict=%s confidence=%s action=%s",
        time.monotonic() - started,
        result["verdict"],
        result["confidence"],
        result["recommended_action"],
    )
    return result