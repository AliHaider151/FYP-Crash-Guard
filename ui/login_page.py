import customtkinter as ctk
from tkinter import messagebox
from ui.dashboard import open_dashboard   # call dashboard after login

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def run_login_window():
    login_window = ctk.CTk()
    login_window.title("CrashGuard AI Login")
    login_window.geometry("420x480")
    login_window.minsize(420, 480)

    login_window.grid_rowconfigure(0, weight=1)
    login_window.grid_columnconfigure(0, weight=1)

    FIXED_WIDTH = 400

    center_frame = ctk.CTkFrame(login_window, fg_color="transparent")
    center_frame.grid(row=0, column=0, sticky="nsew")

    center_frame.grid_rowconfigure(0, weight=1)
    center_frame.grid_columnconfigure(0, weight=1)

    card = ctk.CTkFrame(center_frame, corner_radius=20, width=FIXED_WIDTH, height=430)
    card.grid(row=0, column=0)
    card.grid_propagate(False)
    card.grid_columnconfigure(0, weight=1)

    title_label = ctk.CTkLabel(
        card, 
        text="CrashGuard\n Camera Panel",
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

    name_entry = ctk.CTkEntry(card, placeholder_text="Camera Address", height=45, width=FIXED_WIDTH-40)
    name_entry.grid(row=2, column=0, pady=8)

    long_entry = ctk.CTkEntry(card, placeholder_text="Longitude", height=45, width=FIXED_WIDTH-40)
    long_entry.grid(row=3, column=0, pady=8)

    lat_entry = ctk.CTkEntry(card, placeholder_text="Latitude", height=45, width=FIXED_WIDTH-40)
    lat_entry.grid(row=4, column=0, pady=8)

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
