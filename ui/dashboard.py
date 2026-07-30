import customtkinter as ctk
from tkinter import filedialog, messagebox
from services.detection_service import start_detection, stop_detection_func

video_path = None

def select_video_path(video_label):
    global video_path
    video_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4")])
    if video_path:
        video_label.configure(text=video_path)

def open_dashboard(name, longitude, latitude):
    dashboard = ctk.CTk()
    dashboard.title("Accident Detection Dashboard")
    dashboard.geometry("1200x700")

    left_panel = ctk.CTkFrame(dashboard, corner_radius=0)
    left_panel.place(relx=0, rely=0, relwidth=0.3, relheight=1)

    header = ctk.CTkLabel(left_panel, text="Crash Guard",
                          font=ctk.CTkFont(size=24, weight="bold"))
    header.pack(pady=20)

    video_label = ctk.CTkLabel(left_panel, text="No video selected")
    video_label.pack(pady=10)

    select_btn = ctk.CTkButton(left_panel, text="📂 Select Video",
                               command=lambda: select_video_path(video_label))
    select_btn.pack(pady=5)

    status_label = ctk.CTkLabel(left_panel, text="Status: Idle",
                                font=ctk.CTkFont(size=14))
    status_label.pack(pady=10)

    right_panel = ctk.CTkLabel(dashboard, text="Video Preview",
                               fg_color="#1E1E1E", corner_radius=10)
    right_panel.place(relx=0.3, rely=0, relwidth=0.7, relheight=1)

    start_btn = ctk.CTkButton(left_panel, text="▶ Start Detection", fg_color="green",
                              command=lambda: start_detection(right_panel, status_label, name, longitude, latitude, video_path))
    start_btn.pack(pady=10)

    stop_btn = ctk.CTkButton(left_panel, text="■ Stop Detection", fg_color="red",
                             command=stop_detection_func)
    stop_btn.pack(pady=10)

    dashboard.mainloop()
