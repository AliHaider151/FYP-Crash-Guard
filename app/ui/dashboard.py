from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from app.services.camera_service import CameraConfig, load_cameras
from app.services.detection_service import start_detection, stop_detection_func


class DashboardWindow:
    def __init__(self, name: str = "", longitude: float = 0.0, latitude: float = 0.0) -> None:
        self.name = name
        self.longitude = longitude
        self.latitude = latitude
        self.cameras = load_cameras()
        self.cameras_by_name = {camera.name: camera for camera in self.cameras}
        self.selected_camera: CameraConfig | None = None

    def select_camera(self, camera_name: str) -> None:
        camera = self.cameras_by_name.get(camera_name)
        if camera is None:
            return
        self.selected_camera = camera
        self.name = camera.name
        self.longitude = camera.longitude
        self.latitude = camera.latitude
        self.video_label.configure(
            text=f"{camera.location}\n{camera.latitude:.4f}, {camera.longitude:.4f}\n{camera.video_path.name}"
        )

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

        ctk.CTkLabel(
            selector_box,
            text="Select Camera",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#F5F5F5",
        ).pack(pady=(16, 8))
        camera_selector = ctk.CTkOptionMenu(
            selector_box,
            values=list(self.cameras_by_name),
            width=220,
            height=40,
            fg_color="#F5F5F5",
            button_color="#D8D8D8",
            button_hover_color="#C6C6C6",
            text_color="#111111",
            dropdown_fg_color="#202020",
            dropdown_text_color="#F5F5F5",
            command=self.select_camera,
        )
        camera_selector.pack(pady=(0, 10), padx=14)
        self.video_label = ctk.CTkLabel(
            selector_box,
            text="",
            wraplength=230,
            justify="center",
            text_color="#BFBFBF",
        )
        self.video_label.pack(pady=(0, 16), padx=14)
        camera_selector.set(self.cameras[0].name)
        self.select_camera(self.cameras[0].name)

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
        if self.selected_camera is None:
            messagebox.showerror("Error", "Select a camera first!")
            return
        if not self.selected_camera.video_path.is_file():
            messagebox.showerror("Error", f"Camera video was not found:\n{self.selected_camera.video_path}")
            return

        start_detection(
            right_panel,
            status_label,
            self.selected_camera.name,
            self.selected_camera.longitude,
            self.selected_camera.latitude,
            str(self.selected_camera.video_path),
        )


def open_dashboard(name: str = "", longitude: float = 0.0, latitude: float = 0.0) -> None:
    DashboardWindow(name, longitude, latitude).open()
