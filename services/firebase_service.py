import firebase_admin
from firebase_admin import credentials, firestore, messaging

cred = credentials.Certificate("keys/service-account.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def save_metadata_to_firestore(clip_id, url, address, confidence, severity, longitude, latitude):
    db.collection('accidents').document(str(clip_id)).set({
        'video_url': url,
        'longitude': float(longitude),
        'latitude': float(latitude),
        'address': address,
        'confidence': confidence,
        'severity': severity,
        'status': 'pending',
        'timestamp': firestore.SERVER_TIMESTAMP
    })

def send_fcm_notification(token, title, body):
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=token
    )
    messaging.send(message)
