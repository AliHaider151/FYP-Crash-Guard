import cv2
import time
from collections import deque
from ultralytics import YOLO
import tempfile
import os
import threading
import queue
import traceback

import firebase_admin
from firebase_admin import credentials, firestore, messaging

import cloudinary
import cloudinary.uploader

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# ================================
# CONFIG
# ================================
CLOUDINARY_CONFIG = {
    "cloud_name": 'dlpjswzj0',
    "api_key": '787633141853545',
    "api_secret": 'XrRKeRsNpIhv-JWrJEx7C5jt2bM'
}
FIREBASE_KEY_PATH = 'keys/service-account.json'
ACCIDENT_CLASSES = ["Accident", "mild", "moderate", "severe"]
BUFFER_SECONDS = 10
AFTER_SECONDS = 10

cloudinary.config(**CLOUDINARY_CONFIG)
cred = credentials.Certificate(FIREBASE_KEY_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

# ================================
# GLOBALS
# ================================
upload_queue = queue.Queue()
last_accident_time = 0

# ================================
# UPLOAD WORKER
# ================================
def upload_worker():
    while True:
        item = upload_queue.get()
        if item is None:
            break
        try:
            frames, fps, clip_id, boxes_info, address, longitude, latitude = item
            url = upload_clip_to_cloudinary(frames, fps, clip_id)
            accident_boxes = [box for box in boxes_info if box['cls_name'] in ACCIDENT_CLASSES]

            if accident_boxes:
                best_box = max(accident_boxes, key=lambda b: b['conf'])
                accident_class = best_box['cls_name']
                accident_confidence = best_box['conf']
            else:
                accident_class = None
                accident_confidence = 0

            save_metadata_to_firestore(clip_id, url, address, accident_confidence, accident_class, longitude, latitude)

            # Send notifications to all users
            users = db.collection("users").stream()
            for u in users:
                data = u.to_dict()
                token = data.get("fcmToken")
                if token:
                    try:
                        send_fcm_notification(
                            token,
                            "🚨 Accident Detected",
                            f"An accident has been reported near {address}."
                        )
                    except Exception:
                        print("Error sending notification to:", token)

        except Exception:
            print("Error in upload worker:")
            traceback.print_exc()
        finally:
            upload_queue.task_done()

threading.Thread(target=upload_worker, daemon=True).start()

# ================================
# CLOUDINARY UPLOAD
# ================================
def upload_clip_to_cloudinary(frames, fps, clip_id):
    try:
        fd, temp_path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        height, width, _ = frames[0].shape
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))
        for f in frames:
            writer.write(f)
        writer.release()
        response = cloudinary.uploader.upload(temp_path, resource_type="video",
                                              public_id=f"accident_{clip_id}", folder="FYP")
        os.remove(temp_path)
        url = response.get('secure_url', None)
        print(f"Uploaded: {url}")
        return url
    except Exception:
        print("Error uploading to Cloudinary:")
        traceback.print_exc()
        return None

# ================================
# FIRESTORE METADATA
# ================================
def save_metadata_to_firestore(clip_id, url, address, confidence, severity, longitude, latitude):
    try:
        doc_ref = db.collection('accidents').document(str(clip_id))
        doc_ref.set({
            'video_url': url,
            'longitude': float(longitude),
            'latitude': float(latitude),
            'address': address,
            'confidence': confidence,
            'severity': severity,
            'status': 'pending',
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        print(f"Saved metadata for clip: {clip_id}")
    except Exception:
        print("Error saving metadata to Firestore:")
        traceback.print_exc()

# ================================
# FCM NOTIFICATION
# ================================
def send_fcm_notification(token, title, body):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        webpush=messaging.WebpushConfig(
            notification=messaging.WebpushNotification(
                title=title,
                body=body,
                icon="logo.png",
            ),
        ),
        token=token,
    )
    response = messaging.send(message)
    print("Notification sent:", response)

# ================================
# YOLO MODEL
# ================================
model = YOLO("best-train-2.pt")

def extract_boxes_info(boxes):
    info = []
    try:
        for box in boxes:
            cls_id = int(box.cls)
            conf = float(box.conf)
            cls_name = model.names[cls_id] if cls_id < len(model.names) else "Unknown"
            info.append({"cls_name": cls_name, "conf": conf})
    except Exception:
        traceback.print_exc()
    return info

# ================================
# DASHBOARD UI
# ================================
video_path = None
stop_detection = False

def select_video_path(video_label):
    global video_path
    video_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4")])
    if video_path:
        video_label.configure(text=video_path)

def start_detection(right_panel, status_label, name, longitude, latitude):
    global stop_detection, last_accident_time
    if not video_path:
        messagebox.showerror("Error", "Select a video first!")
        return

    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    buffer_size = fps * BUFFER_SECONDS
    frame_buffer = deque(maxlen=buffer_size)

    is_recording = False
    recording_start_time = None
    accident_frames = []
    boxes_info = []
    clip_id = None
    stop_detection = False

    def detection_loop():
        nonlocal is_recording, recording_start_time, accident_frames, boxes_info, clip_id
        frame_count = 0
        global last_accident_time

        while cap.isOpened() and not stop_detection:
            ret, frame = cap.read()
            if not ret:
                break
            frame_buffer.append(frame)
            frame_count += 1

            # Resize for YOLO
            frame_resized = cv2.resize(frame, (480, 480))
            results = model.predict(frame_resized, conf=0.25, show=False, verbose=False)
            annotated = results[0].plot()
            boxes_info = extract_boxes_info(results[0].boxes)

            accident_detected = any(box['cls_name'] in ACCIDENT_CLASSES for box in boxes_info)
            current_time = time.time()

            # COOL DOWN: ignore accidents detected in last AFTER_SECONDS
            if accident_detected and not is_recording and (current_time - last_accident_time > AFTER_SECONDS):
                status_label.configure(text="Status: Accident Detected!")
                print(f"🔥 Accident detected at frame {frame_count}! Recording clip...")
                is_recording = True
                recording_start_time = time.time()
                accident_frames = []

            elif not accident_detected and not is_recording:
                status_label.configure(text="Status: Monitoring...")

            # Record frames during accident
            if is_recording:
                accident_frames.append(frame)
                if time.time() - recording_start_time >= AFTER_SECONDS:
                    all_frames = list(frame_buffer) + accident_frames
                    clip_id = int(time.time() * 1000)
                    upload_queue.put((all_frames, fps, clip_id, boxes_info, name, longitude, latitude))
                    is_recording = False
                    accident_frames = []
                    last_accident_time = time.time()  # start cooldown
                    status_label.configure(text="Status: Idle")
                    print(f"📤 Uploaded clip ID: {clip_id}")

            # Update preview every 2 frames
            if frame_count % 2 == 0:
                frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img = img.resize((right_panel.winfo_width(), right_panel.winfo_height()))
                imgtk = ImageTk.PhotoImage(img)
                right_panel.configure(image=imgtk)
                right_panel.imgtk = imgtk

            time.sleep(1/fps)

        cap.release()
        status_label.configure(text="Status: Idle")

    threading.Thread(target=detection_loop, daemon=True).start()

def stop_detection_func():
    global stop_detection
    stop_detection = True

def open_dashboard(name, longitude, latitude):
    dashboard = ctk.CTk()
    dashboard.title("Accident Detection Dashboard")
    dashboard.geometry("1200x700")
    dashboard.minsize(1000, 600)

    # LEFT PANEL
    left_panel = ctk.CTkFrame(dashboard, corner_radius=0)
    left_panel.place(relx=0, rely=0, relwidth=0.3, relheight=1)

    header = ctk.CTkLabel(left_panel, text="Crash Guard", font=ctk.CTkFont(size=24, weight="bold"))
    header.pack(pady=(20,5))
    subtitle = ctk.CTkLabel(left_panel, text="Teten Drows", font=ctk.CTkFont(size=16))
    subtitle.pack(pady=(0,20))

    select_btn = ctk.CTkButton(left_panel, text="📂 Select Video", width=180, height=40,
                               command=lambda: select_video_path(video_label))
    select_btn.pack(pady=(0,10))
    video_label = ctk.CTkLabel(left_panel, text="No video selected", wraplength=200)
    video_label.pack(pady=(0,20))

    control_frame = ctk.CTkFrame(left_panel)
    control_frame.pack(pady=(0,20))
    status_label = ctk.CTkLabel(left_panel, text="Status: Idle", font=ctk.CTkFont(size=14))
    status_label.pack(pady=(10,0))

    start_btn = ctk.CTkButton(control_frame, text="▶ Start Detection", width=150, height=40, fg_color="green",
                              command=lambda: start_detection(right_panel, status_label, name, longitude, latitude))
    start_btn.pack(pady=(0,10))
    stop_btn = ctk.CTkButton(control_frame, text="■ Stop Detection", width=150, height=40, fg_color="red",
                             command=stop_detection_func)
    stop_btn.pack(pady=(0,10))

    # RIGHT PANEL
    right_panel = ctk.CTkLabel(dashboard, text="Video Preview", fg_color="#1E1E1E", corner_radius=10)
    right_panel.place(relx=0.3, rely=0, relwidth=0.7, relheight=1)

    dashboard.mainloop()

# ================================
# LOGIN WINDOW
# ================================
import customtkinter as ctk
from tkinter import messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def run_login_window():
    login_window = ctk.CTk()
    login_window.title("CrashGuard AI Login")
    login_window.geometry("420x480")
    login_window.minsize(420, 480)

    # Make whole window act like flexbox for centering
    login_window.grid_rowconfigure(0, weight=1)
    login_window.grid_columnconfigure(0, weight=1)

    FIXED_WIDTH = 400

    # ====== CENTER WRAPPER (full screen flexbox layer) ======
    center_frame = ctk.CTkFrame(login_window, fg_color="transparent")
    center_frame.grid(row=0, column=0, sticky="nsew")

    # Enable centering inside this frame
    center_frame.grid_rowconfigure(0, weight=1)
    center_frame.grid_columnconfigure(0, weight=1)

    # ====== LOGIN CARD (fixed size) ======
    card = ctk.CTkFrame(center_frame, corner_radius=20, width=FIXED_WIDTH, height=430)
    card.grid(row=0, column=0, sticky="")  # no sticky → stays center
    card.grid_propagate(False)

    card.grid_columnconfigure(0, weight=1)

    # ====== TITLE ======
    title_label = ctk.CTkLabel(
        card, 
        text="CrashGuard \nCamera Panel",
        font=ctk.CTkFont(size=24, weight="bold"),
        justify="center"
    )
    title_label.grid(row=0, column=0, pady=(25, 10))

    subtitle = ctk.CTkLabel(
        card,
        text="Login to continue",
        font=ctk.CTkFont(size=14),
        text_color="#b0b0b0"
    )
    subtitle.grid(row=1, column=0, pady=(0, 20))

    # ====== INPUT FIELDS ======
    name_entry = ctk.CTkEntry(card, placeholder_text="Camera Address", height=45, width=FIXED_WIDTH-40)
    name_entry.grid(row=2, column=0, pady=8)

    long_entry = ctk.CTkEntry(card, placeholder_text="Longitude", height=45, width=FIXED_WIDTH-40)
    long_entry.grid(row=3, column=0, pady=8)

    lat_entry = ctk.CTkEntry(card, placeholder_text="Latitude", height=45, width=FIXED_WIDTH-40)
    lat_entry.grid(row=4, column=0, pady=8)

    # ====== LOGIN HANDLER ======
    def login_action():
        name = name_entry.get()
        longitude = long_entry.get()
        latitude = lat_entry.get()

        if not name or not longitude or not latitude:
            messagebox.showerror("Error", "Fill all fields!")
            return

        try:
            float(longitude)
            float(latitude)
        except ValueError:
            messagebox.showerror("Error", "Coordinates must be numbers!")
            return

        login_window.destroy()
        open_dashboard(name, longitude, latitude)

    # ====== BUTTON ======
    login_btn = ctk.CTkButton(
        card, 
        text="Login", 
        command=login_action,
        height=48,
        width=FIXED_WIDTH - 100,
        corner_radius=15
    )
    login_btn.grid(row=5, column=0, pady=25)

    login_window.mainloop()

# ================================
# ENTRY POINT
# ================================
if __name__ == "__main__":
    run_login_window()
