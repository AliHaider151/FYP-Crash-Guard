from __future__ import annotations

import json
import logging
from typing import Iterable

import firebase_admin
from firebase_admin import credentials, firestore, messaging

from app.config import get_config

logger = logging.getLogger(__name__)

_db = None


def is_stale_fcm_token_error(exc: Exception) -> bool:
    text = str(exc).lower()
    unregistered_phrases = (
        "device unregistered",
        "not registered",
        "registration token is not registered",
        "unregistered",
    )
    return any(phrase in text for phrase in unregistered_phrases)


def remove_stale_fcm_token(token: str) -> None:
    db = get_db()
    matches = db.collection("users").where("fcmToken", "==", token).stream()
    for user in matches:
        db.collection("users").document(user.id).update({"fcmToken": firestore.DELETE_FIELD})


def get_db():
    global _db
    if _db is not None:
        return _db

    config = get_config()
    if not config.firebase_credentials_json:
        raise ValueError("FIREBASE_SERVICE_ACCOUNT_JSON is required to connect to Firebase")
    try:
        service_account = json.loads(config.firebase_credentials_json)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "FIREBASE_SERVICE_ACCOUNT_JSON must contain valid JSON; in a .env file, "
            "enclose the complete JSON object in matching single quotes and use double "
            "quotes for JSON keys and string values"
        ) from exc
    if not isinstance(service_account, dict):
        raise ValueError("FIREBASE_SERVICE_ACCOUNT_JSON must contain a JSON object")
    firebase_credential = credentials.Certificate(service_account)

    firebase_admin.initialize_app(firebase_credential)
    _db = firestore.client()
    return _db


def save_metadata_to_firestore(clip_id, url: str | None, address: str, confidence: float, severity, longitude, latitude):
    db = get_db()
    payload = {
        "video_url": url,
        "longitude": float(longitude),
        "latitude": float(latitude),
        "address": address,
        "confidence": confidence,
        "severity": severity,
        "status": "pending",
        "timestamp": firestore.SERVER_TIMESTAMP,
    }

    db.collection("accidents").document(str(clip_id)).set(payload)
    logger.info("Saved accident metadata for clip %s", clip_id)


def save_verification_to_firestore(clip_id, verification: dict) -> None:
    db = get_db()
    db.collection("accidents").document(str(clip_id)).set(
        {"verification": verification},
        merge=True,
    )
    logger.info(
        "Saved secondary verification for incident %s: verdict=%s confidence=%s",
        clip_id,
        verification.get("verdict", "unknown"),
        verification.get("confidence", "unknown"),
    )


def send_fcm_notification(token: str, title: str, body: str) -> str:
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        webpush=messaging.WebpushConfig(
            notification=messaging.WebpushNotification(
                title=title,
                body=body,
                icon="logo.png",
            )
        ),
        token=token,
    )
    try:
        response = messaging.send(message)
        logger.info("Notification sent: %s", response)
        return response
    except Exception as exc:
        if is_stale_fcm_token_error(exc):
            logger.warning("Removing stale FCM token from Firestore: %s", token)
            try:
                remove_stale_fcm_token(token)
            except Exception:
                logger.exception("Failed to clear stale FCM token: %s", token)
            return ""
        raise


def get_all_user_tokens() -> Iterable[str]:
    db = get_db()
    tokens = []
    for user in db.collection("users").stream():
        token = user.to_dict().get("fcmToken")
        if token:
            tokens.append(token)
    return tokens
