from __future__ import annotations

import customtkinter as ctk

from app.ui.dashboard import open_dashboard


def run_login_window() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    login_window = ctk.CTk()
    login_window.title("Crash Guard Camera Panel")
    login_window.geometry("440x420")
    login_window.minsize(440, 420)
    login_window.configure(fg_color="#0B0B0B")

    login_window.grid_rowconfigure(0, weight=1)
    login_window.grid_columnconfigure(0, weight=1)

    fixed_width = 360

    center_frame = ctk.CTkFrame(login_window, fg_color="transparent")
    center_frame.grid(row=0, column=0, sticky="nsew")
    center_frame.grid_rowconfigure(0, weight=1)
    center_frame.grid_columnconfigure(0, weight=1)

    card = ctk.CTkFrame(center_frame, corner_radius=24, width=fixed_width, height=340, fg_color="#171717")
    card.grid(row=0, column=0)
    card.grid_propagate(False)
    card.grid_columnconfigure(0, weight=1)

    title_label = ctk.CTkLabel(
        card,
        text="Crash Guard\nCamera Panel",
        font=ctk.CTkFont(size=28, weight="bold"),
        justify="center",
        text_color="#F5F5F5",
    )
    title_label.grid(row=0, column=0, pady=(28, 8))

    subtitle = ctk.CTkLabel(
        card,
        text="Select a configured camera on the dashboard",
        font=ctk.CTkFont(size=13),
        text_color="#A7A7A7",
    )
    subtitle.grid(row=1, column=0, pady=(0, 20))

    def login_action() -> None:
        login_window.destroy()
        open_dashboard()

    login_btn = ctk.CTkButton(
        card,
        text="Open Monitoring Dashboard",
        command=login_action,
        height=48,
        width=fixed_width - 48,
        corner_radius=14,
        fg_color="#F5F5F5",
        hover_color="#E0E0E0",
        text_color="#0B0B0B",
    )
    login_btn.grid(row=2, column=0, pady=(30, 20))

    login_window.mainloop()
