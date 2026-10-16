from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.config import get_config


@dataclass(frozen=True)
class CameraConfig:
    name: str
    location: str
    video_path: Path
    latitude: float
    longitude: float


def load_cameras(config_path: str | Path | None = None) -> list[CameraConfig]:
    config = get_config()
    path = Path(config_path) if config_path else config.project_root / "assets" / "cameras.json"
    if not path.is_absolute():
        path = config.project_root / path
    if not path.is_file():
        raise FileNotFoundError(f"Camera configuration file not found: {path}")

    with path.open(encoding="utf-8") as file:
        payload = json.load(file)

    entries = payload.get("cameras") if isinstance(payload, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ValueError("Camera configuration must contain a non-empty 'cameras' list")

    cameras = []
    names = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"Camera entry {index} must be an object")
        try:
            name = str(entry["name"]).strip()
            location = str(entry.get("location", name)).strip()
            video_path = str(entry["video_path"]).strip()
            latitude = float(entry["latitude"])
            longitude = float(entry["longitude"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Camera entry {index} has missing or invalid fields") from exc

        if not name or not location or not video_path:
            raise ValueError(f"Camera entry {index} contains an empty name, location, or video path")
        if name in names:
            raise ValueError(f"Duplicate camera name: {name}")
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError(f"Camera {name} has coordinates outside valid latitude/longitude ranges")

        names.add(name)
        resolved_video_path = Path(video_path)
        if not resolved_video_path.is_absolute():
            resolved_video_path = config.project_root / resolved_video_path
        cameras.append(CameraConfig(name, location, resolved_video_path.resolve(), latitude, longitude))

    return cameras