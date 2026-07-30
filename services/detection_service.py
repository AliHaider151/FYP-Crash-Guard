import cv2
import time
import threading
from collections import deque
from PIL import Image, ImageTk

from models.yolo_model import model
from services.firebase_service import save_metadata_to_firestore, send_fcm_notification
from services.cloudinary_service import upload_clip_to_cloudinary

stop_detection = False
upload_queue = []

def start_detection(right_panel, status_label, name, longitude, latitude, video_path):
    global stop_detection
    stop_detection = False

    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30

    buffer = deque(maxlen=fps * 10)

    def loop():
        nonlocal fps
        frame_count = 0

        while cap.isOpened() and not stop_detection:
            ret, frame = cap.read()
            if not ret:
                break

            buffer.append(frame)
            frame_count += 1

            results = model.predict(frame, conf=0.25, verbose=False)
            annotated = results[0].plot()

            frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img = img.resize((right_panel.winfo_width(), right_panel.winfo_height()))
            imgtk = ImageTk.PhotoImage(img)
            right_panel.configure(image=imgtk)
            right_panel.imgtk = imgtk

            status_label.configure(text="Status: Monitoring...")
            time.sleep(1/fps)

        cap.release()
        status_label.configure(text="Status: Idle")

    threading.Thread(target=loop, daemon=True).start()

def stop_detection_func():
    global stop_detection
    stop_detection = True
