from __future__ import annotations

from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.services.detection_service import start_detection, stop_detection_func


class DashboardWindow:
    def __init__(self, name: str, longitude: float, latitude: float) -> None:
        self.name = name
        self.longitude = longitude
        self.latitude = latitude
        self.video_path = None

    def select_video_path(self, video_label) -> None:
        self.video_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4")])
        if self.video_path:
            video_label.configure(text=self.video_path)

    def open(self) -> None:
        dashboard = ctk.CTk()
        dashboard.title("Accident Detection Dashboard")
        dashboard.geometry("1200x700")
        dashboard.minsize(1000, 600)
        dashboard.configure(fg_color="#0B0B0B")

        left_panel = ctk.CTkFrame(dashboard, corner_radius=0, fg_color="#141414")
        left_panel.place(relx=0, rely=0, relwidth=0.3, relheight=1)

        header = ctk.CTkLabel(left_panel, text="Crash Guard", font=ctk.CTkFont(size=26, weight="bold"), text_color="#F5F5F5")
        header.pack(pady=(22, 6))
        subtitle = ctk.CTkLabel(left_panel, text="Traffic Safety", font=ctk.CTkFont(size=15), text_color="#BFBFBF")
        subtitle.pack(pady=(0, 22))

        selector_box = ctk.CTkFrame(left_panel, corner_radius=18, fg_color="#1A1A1A")
        selector_box.pack(fill="x", padx=18, pady=(0, 18))

        video_label = ctk.CTkLabel(selector_box, text="No video selected", wraplength=200, justify="center", text_color="#E9E9E9")
        video_label.pack(pady=(16, 10), padx=14)
        select_btn = ctk.CTkButton(
            selector_box,
            text="📂 Select Video",
            width=180,
            height=40,
            fg_color="#F5F5F5",
            hover_color="#E5E5E5",
            text_color="#111111",
            command=lambda: self.select_video_path(video_label),
        )
        select_btn.pack(pady=(0, 16))

        control_frame = ctk.CTkFrame(left_panel, corner_radius=18, fg_color="#1A1A1A")
        control_frame.pack(fill="x", padx=18, pady=(0, 18))

        status_label = ctk.CTkLabel(control_frame, text="Status: Idle", font=ctk.CTkFont(size=14, weight="bold"), text_color="#FFFFFF")
        status_label.pack(pady=(16, 10))

        start_btn = ctk.CTkButton(
            control_frame,
            text="▶ Start Detection",
            width=180,
            height=42,
            fg_color="#F5F5F5",
            hover_color="#E5E5E5",
            text_color="#111111",
            command=lambda: self.start_detection_handler(right_panel, status_label),
        )
        start_btn.pack(pady=(0, 10))

        stop_btn = ctk.CTkButton(
            control_frame,
            text="■ Stop Detection",
            width=180,
            height=42,
            fg_color="#D9D9D9",
            hover_color="#CFCFCF",
            text_color="#111111",
            command=stop_detection_func,
        )
        stop_btn.pack(pady=(0, 16))

        right_panel = ctk.CTkLabel(dashboard, text="Video Preview", fg_color="#1A1A1A", corner_radius=18, text_color="#F5F5F5")
        right_panel.place(relx=0.3, rely=0, relwidth=0.7, relheight=1)

        self.dashboard = dashboard
        self.right_panel = right_panel
        self.status_label = status_label
        dashboard.mainloop()

    def start_detection_handler(self, right_panel, status_label) -> None:
        if not self.video_path:
            messagebox.showerror("Error", "Select a video first!")
            return

        start_detection(
            right_panel,
            status_label,
            self.name,
            self.longitude,
            self.latitude,
            self.video_path,
        )


def open_dashboard(name: str, longitude: float, latitude: float) -> None:
    DashboardWindow(name, longitude, latitude).open()
