from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from app.ui.dashboard import open_dashboard


def run_login_window() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    login_window = ctk.CTk()
    login_window.title("CrashGuard AI Login")
    login_window.geometry("440x520")
    login_window.minsize(440, 520)
    login_window.configure(fg_color="#0B0B0B")

    login_window.grid_rowconfigure(0, weight=1)
    login_window.grid_columnconfigure(0, weight=1)

    fixed_width = 360

    center_frame = ctk.CTkFrame(login_window, fg_color="transparent")
    center_frame.grid(row=0, column=0, sticky="nsew")
    center_frame.grid_rowconfigure(0, weight=1)
    center_frame.grid_columnconfigure(0, weight=1)

    card = ctk.CTkFrame(center_frame, corner_radius=24, width=fixed_width, height=440, fg_color="#171717")
    card.grid(row=0, column=0)
    card.grid_propagate(False)
    card.grid_columnconfigure(0, weight=1)

    title_label = ctk.CTkLabel(
        card,
        text="CrashGuard\nCamera Panel",
        font=ctk.CTkFont(size=28, weight="bold"),
        justify="center",
        text_color="#F5F5F5",
    )
    title_label.grid(row=0, column=0, pady=(28, 8))

    subtitle = ctk.CTkLabel(
        card,
        text="Login to continue",
        font=ctk.CTkFont(size=13),
        text_color="#A7A7A7",
    )
    subtitle.grid(row=1, column=0, pady=(0, 20))

    field_style = {"height": 44, "width": fixed_width - 40, "border_color": "#2F2F2F", "fg_color": "#111111"}

    name_entry = ctk.CTkEntry(card, placeholder_text="Camera Address", **field_style)
    name_entry.grid(row=2, column=0, pady=8)

    long_entry = ctk.CTkEntry(card, placeholder_text="Longitude", **field_style)
    long_entry.grid(row=3, column=0, pady=8)

    lat_entry = ctk.CTkEntry(card, placeholder_text="Latitude", **field_style)
    lat_entry.grid(row=4, column=0, pady=8)

    def login_action() -> None:
        name = name_entry.get().strip()
        longitude = long_entry.get().strip()
        latitude = lat_entry.get().strip()

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
        open_dashboard(name, float(longitude), float(latitude))

    login_btn = ctk.CTkButton(
        card,
        text="Login",
        command=login_action,
        height=48,
        width=fixed_width - 80,
        corner_radius=14,
        fg_color="#F5F5F5",
        hover_color="#E0E0E0",
        text_color="#0B0B0B",
    )
    login_btn.grid(row=5, column=0, pady=(20, 12))

    login_window.mainloop()
