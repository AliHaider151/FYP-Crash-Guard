from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(__file__).resolve().parent / "Crash_Guard_Project_Presentation.pdf"
SOURCE = ROOT / "Carsh Guard Final.mp4"
WIDTH, HEIGHT = 1280, 720
BG = "#0B0D10"
PANEL = "#15191E"
WHITE = "#F3F5F7"
MUTED = "#A5AFB9"
BLUE = "#3A8DFF"
MINT = "#72E0C0"


def load_font(size: int, bold: bool = False):
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    path = Path("C:/Windows/Fonts") / name
    if not path.exists():
        path = Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


FONT_TITLE = load_font(49, True)
FONT_SUBTITLE = load_font(25)
FONT_HEAD = load_font(23, True)
FONT_BODY = load_font(19)
FONT_LABEL = load_font(16, True)
FONT_SMALL = load_font(15)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, width: int, font, color: str, line_gap: int = 8) -> int:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        y += font.size + line_gap
    return y


def base_slide(title: str, subtitle: str, page: int, total: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    slide = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(slide)
    for x in range(0, WIDTH, 64):
        draw.line((x, 0, x, HEIGHT), fill="#101419", width=1)
    for y in range(0, HEIGHT, 64):
        draw.line((0, y, WIDTH, y), fill="#101419", width=1)
    draw.rounded_rectangle((42, 34, 80, 72), radius=10, fill=BLUE)
    draw.text((50, 40), "CG", font=FONT_LABEL, fill=WHITE)
    draw.text((94, 38), "CRASH GUARD", font=FONT_LABEL, fill=WHITE)
    draw.text((94, 59), "AI INCIDENT RESPONSE", font=FONT_SMALL, fill=MUTED)
    draw.text((1132, 45), f"{page:02d} / {total:02d}", font=FONT_SMALL, fill=MUTED)
    draw.line((42, 91, WIDTH - 42, 91), fill="#29313A", width=1)
    draw.text((64, 120), title, font=FONT_TITLE, fill=WHITE)
    wrap_text(draw, subtitle, 66, 186, WIDTH - 132, FONT_SUBTITLE, MUTED, 5)
    draw.line((64, HEIGHT - 42, WIDTH - 64, HEIGHT - 42), fill="#29313A", width=2)
    draw.line((64, HEIGHT - 42, 64 + int((WIDTH - 128) * page / total), HEIGHT - 42), fill=BLUE, width=3)
    draw.text((64, HEIGHT - 32), "CRASH GUARD  /  PROJECT PRESENTATION", font=FONT_SMALL, fill="#7E8994")
    return slide, draw


def get_demo_frame(cap: cv2.VideoCapture, seconds: float, panel: str, redact: bool = False) -> Image.Image:
    cap.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError(f"Could not read demo footage at {seconds}s")
    mid = frame.shape[0] // 2
    frame = frame[:mid] if panel == "top" else frame[mid:]
    if redact:
        x1, y1, x2, y2 = 425, 395, 660, 470
        roi = frame[y1:y2, x1:x2]
        frame[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (41, 41), 0)
    return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))


def rounded_image(slide: Image.Image, image: Image.Image, box: tuple[int, int, int, int], radius: int = 15) -> None:
    x, y, width, height = box
    image = image.convert("RGB")
    scale = min(width / image.width, height / image.height)
    image = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
    panel = Image.new("RGB", (width, height), "#07090C")
    panel.paste(image, ((width - image.width) // 2, (height - image.height) // 2))
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=255)
    slide.paste(panel, (x, y), mask)


def add_tag(draw: ImageDraw.ImageDraw, text: str, x: int, y: int) -> None:
    bounds = draw.textbbox((x + 14, y + 7), text, font=FONT_LABEL)
    draw.rounded_rectangle((x, y, bounds[2] + 13, bounds[3] + 8), radius=8, fill="#202832")
    draw.rounded_rectangle((x, y, x + 5, bounds[3] + 8), radius=2, fill=BLUE)
    draw.text((x + 14, y + 7), text, font=FONT_LABEL, fill=WHITE)


def feature_slide(cap, page: int, total: int, title: str, subtitle: str, seconds: float, panel: str, tag: str, detail: str, redact: bool = False, freeze_note: str | None = None) -> Image.Image:
    slide, draw = base_slide(title, subtitle, page, total)
    demo = get_demo_frame(cap, seconds, panel, redact=redact)
    draw.rounded_rectangle((58, 280, 875, 640), radius=20, fill=PANEL, outline="#29313A", width=1)
    rounded_image(slide, demo, (77, 300, 779, 321))
    draw.rounded_rectangle((899, 280, 1222, 640), radius=20, fill=PANEL, outline="#29313A", width=1)
    add_tag(draw, tag, 924, 312)
    text_bottom = wrap_text(draw, detail, 925, 375, 270, FONT_BODY, WHITE, 8)
    draw.line((925, text_bottom + 10, 1195, text_bottom + 10), fill="#313B45", width=1)
    if freeze_note:
        note = freeze_note
    else:
        note = "Recorded demo footage"
    wrap_text(draw, note, 925, text_bottom + 30, 265, FONT_SMALL, MUTED, 6)
    return slide


def workflow_slide(page: int, total: int) -> Image.Image:
    slide, draw = base_slide("One incident. One connected workflow.", "Camera-side detection preserves evidence and shares incident details with the authority workflow.", page, total)
    steps = [
        ("01", "CAMERA FEED", "Traffic video enters the monitoring node."),
        ("02", "YOLOv8", "The model checks frames for accident classes."),
        ("03", "EVIDENCE", "Pre-event buffer plus post-event recording."),
        ("04", "AUTHORITY", "Incident record, video, location, and alert."),
    ]
    for index, (number, heading, detail) in enumerate(steps):
        x = 65 + index * 290
        draw.rounded_rectangle((x, 325, x + 270, 550), radius=18, fill=PANEL, outline="#29313A", width=1)
        draw.ellipse((x + 22, 350, x + 68, 396), fill=BLUE if index == 1 else "#26313C")
        draw.text((x + 31, 360), number, font=FONT_LABEL, fill=WHITE)
        draw.text((x + 22, 419), heading, font=FONT_HEAD, fill=WHITE)
        wrap_text(draw, detail, x + 22, 461, 225, FONT_BODY, MUTED, 5)
        if index < 3:
            draw.line((x + 274, 438, x + 286, 438), fill=BLUE, width=3)
    draw.text((67, 580), "10s PRE-EVENT BUFFER", font=FONT_LABEL, fill=MINT)
    draw.text((350, 580), "10s POST-EVENT CLIP", font=FONT_LABEL, fill=MUTED)
    return slide


def services_slide(page: int, total: int) -> Image.Image:
    slide, draw = base_slide("Detection to dispatch-ready information.", "The upload worker handles cloud operations separately from the video preview loop.", page, total)
    stages = [("DETECT", "YOLOv8"), ("CAPTURE", "Pre + post-event"), ("PUBLISH", "Cloud services"), ("REVIEW", "Authority panel")]
    for index, (heading, caption) in enumerate(stages):
        x = 68 + index * 305
        draw.rounded_rectangle((x, 300, x + 250, 395), radius=15, fill=PANEL, outline="#2B333D", width=1)
        draw.text((x + 20, 319), heading, font=FONT_LABEL, fill=WHITE)
        draw.text((x + 20, 353), caption, font=FONT_BODY, fill=MUTED)
        if index < 3:
            draw.line((x + 259, 348, x + 294, 348), fill=BLUE, width=3)
    services = [("CLOUDINARY", "Evidence video", BLUE), ("FIRESTORE", "Incident record", MINT), ("FCM", "Responder alert", "#E7C46A")]
    for index, (heading, caption, color) in enumerate(services):
        x = 181 + index * 312
        draw.rounded_rectangle((x, 458, x + 250, 540), radius=14, fill="#1C2229", outline="#2B333D", width=1)
        draw.ellipse((x + 17, 480, x + 37, 500), fill=color)
        draw.text((x + 52, 469), heading, font=FONT_LABEL, fill=WHITE)
        draw.text((x + 52, 502), caption, font=FONT_SMALL, fill=MUTED)
    draw.text((184, 572), "Cloud video  ·  Firestore metadata  ·  Firebase Cloud Messaging", font=FONT_BODY, fill=MUTED)
    return slide


def closing_slide(page: int, total: int) -> Image.Image:
    slide, draw = base_slide("CRASH GUARD", "AI-assisted accident detection and evidence delivery for faster incident awareness.", page, total)
    draw.rounded_rectangle((66, 315, 1214, 525), radius=24, fill=PANEL, outline="#29313A", width=1)
    phrases = [("DETECT", BLUE), ("PRESERVE", WHITE), ("NOTIFY", MINT), ("RESPOND", WHITE)]
    x = 112
    for index, (phrase, color) in enumerate(phrases):
        draw.text((x, 385), phrase, font=FONT_HEAD, fill=color)
        x += 260
        if index < len(phrases) - 1:
            draw.text((x - 28, 385), "/", font=FONT_HEAD, fill=MUTED)
    draw.text((69, 572), "CAMERA PANEL  +  AUTHORITY MANAGEMENT", font=FONT_LABEL, fill=MUTED)
    return slide


def cover_slide(total: int) -> Image.Image:
    slide = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(slide)
    for x in range(0, WIDTH, 64):
        draw.line((x, 0, x, HEIGHT), fill="#101419", width=1)
    for y in range(0, HEIGHT, 64):
        draw.line((0, y, WIDTH, y), fill="#101419", width=1)
    draw.rounded_rectangle((72, 62, 116, 106), radius=12, fill=BLUE)
    draw.text((82, 69), "CG", font=FONT_LABEL, fill=WHITE)
    draw.text((134, 69), "CRASH GUARD", font=FONT_LABEL, fill=WHITE)

    logo_path = ROOT / "logo.png"
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGB")
        logo.thumbnail((280, 280), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (310, 310), "#FFFFFF")
        tile.paste(logo, ((310 - logo.width) // 2, (310 - logo.height) // 2))
        slide.paste(tile, (866, 202))

    draw.text((76, 220), "SEE THE INCIDENT.", font=FONT_TITLE, fill=WHITE)
    draw.text((76, 285), "MOVE THE RESPONSE.", font=FONT_TITLE, fill=BLUE)
    wrap_text(
        draw,
        "AI-powered traffic accident detection, evidence capture, and authority response.",
        80,
        372,
        700,
        FONT_SUBTITLE,
        MUTED,
    )
    add_tag(draw, "CAMERA PANEL  +  AUTHORITY MANAGEMENT", 80, 495)
    draw.text((80, 605), "FINAL YEAR PROJECT  /  SYSTEM WALKTHROUGH", font=FONT_SMALL, fill=MUTED)
    draw.line((80, HEIGHT - 42, WIDTH - 80, HEIGHT - 42), fill="#29313A", width=2)
    draw.line((80, HEIGHT - 42, 80 + int((WIDTH - 160) / total), HEIGHT - 42), fill=BLUE, width=3)
    return slide


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Source demo not found: {SOURCE}")
    cap = cv2.VideoCapture(str(SOURCE))
    if not cap.isOpened():
        raise OSError(f"Could not open source demo: {SOURCE}")

    total = 10
    slides = [
        cover_slide(total),
        workflow_slide(2, total),
        feature_slide(cap, 3, total, "Configure the camera node.", "Each monitoring node is identified by its location and coordinates.", 0, "bottom", "CAMERA SETUP", "Enter the camera address and its latitude / longitude before monitoring.", freeze_note="Recorded camera-panel demo"),
        feature_slide(cap, 4, total, "AI monitoring on the video feed.", "The desktop panel displays model detections over the selected traffic video.", 18, "bottom", "LIVE DETECTION", "YOLOv8 labels vehicles and accident severity classes in the operator preview."),
        feature_slide(cap, 5, total, "Preserve context around an incident.", "A rolling frame buffer keeps recent footage available when a detection triggers.", 38, "bottom", "VIDEO EVIDENCE", "Capture pre-event context, then continue recording after the trigger."),
        feature_slide(cap, 6, total, "Authority sign-in screen.", "The recording includes a responder sign-in view for the management panel.", 0, "top", "AUTHORITY ACCESS", "Sign-in screen shown in demo footage. Visible credential fields are blurred.", redact=True, freeze_note="Recorded authority-panel demo · credentials obscured"),
        feature_slide(cap, 7, total, "Authorities review the reported location.", "The management-panel demo includes a map view alongside incident information.", 55, "top", "AUTHORITY VIEW", "Use the incident location to support review and coordination."),
        feature_slide(cap, 8, total, "Review earlier accident reports.", "The recorded management-panel demo also shows an accident-log view.", 69, "top", "INCIDENT HISTORY", "Open a report to inspect its recorded details and evidence."),
        services_slide(9, total),
        closing_slide(10, total),
    ]

    cap.release()
    slides[0].save(
        OUTPUT,
        "PDF",
        resolution=120.0,
        save_all=True,
        append_images=slides[1:],
        quality=88,
        optimize=True,
    )
    print(f"PDF created: {OUTPUT}")
    print(f"Pages: {len(slides)} | page size: {WIDTH} x {HEIGHT} px, landscape")


if __name__ == "__main__":
    main()