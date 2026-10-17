from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class CloudinaryConfig:
    cloud_name: str = ""
    api_key: str = ""
    api_secret: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "cloud_name": self.cloud_name,
            "api_key": self.api_key,
            "api_secret": self.api_secret,
        }


@dataclass
class IncidentVerificationConfig:
    enabled: bool = True
    api_key: str = ""
    api_base_url: str = "https://developer.amd.com.cn/radeon/api/v1"
    model: str = "DeepSeek-V4-Flash-Vision-Exp"
    frame_count: int = 8
    timeout_seconds: int = 45


@dataclass
class AppConfig:
    env_file: str | None = None
    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1])
    model_path: str = ""
    app_name: str = ""
    firebase_credentials_json: str = ""
    cloudinary: CloudinaryConfig = field(default_factory=CloudinaryConfig)
    incident_verification: IncidentVerificationConfig = field(default_factory=IncidentVerificationConfig)

    def __post_init__(self) -> None:
        env_path = Path(self.env_file) if self.env_file else self.project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=True)

        self.model_path = os.getenv("MODEL_PATH", "best-train-2.pt")
        self.app_name = os.getenv("APP_NAME", "Crash Guard")
        self.firebase_credentials_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
        self.cloudinary = CloudinaryConfig(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
            api_key=os.getenv("CLOUDINARY_API_KEY", ""),
            api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
        )
        self.incident_verification = IncidentVerificationConfig(
            enabled=os.getenv("INCIDENT_VERIFICATION_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"},
            api_key=os.getenv("AMD_API_KEY", "").strip(),
            api_base_url=os.getenv(
                "AMD_API_BASE_URL",
                "https://developer.amd.com.cn/radeon/api/v1",
            ).rstrip("/"),
            model=os.getenv("INCIDENT_VERIFICATION_MODEL", "DeepSeek-V4-Flash-Vision-Exp").strip(),
            frame_count=max(1, int(os.getenv("INCIDENT_VERIFICATION_FRAME_COUNT", "8"))),
            timeout_seconds=max(1, int(os.getenv("INCIDENT_VERIFICATION_TIMEOUT_SECONDS", "45"))),
        )

    def resolve_path(self, raw_path: str) -> Path:
        if not raw_path:
            return self.project_root
        candidate = Path(raw_path)
        if candidate.is_absolute():
            return candidate
        return (self.project_root / candidate).resolve()


_default_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _default_config
    if _default_config is None:
        _default_config = AppConfig()
    return _default_config
