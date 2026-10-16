from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


WIDTH = 1280
HEIGHT = 720
FPS = 24
BG = "#0B0D10"
PANEL = "#15191E"
PANEL_LIGHT = "#1C2229"
WHITE = "#F3F5F7"
MUTED = "#A5AFB9"
BLUE = "#3A8DFF"
MINT = "#72E0C0"


def get_fonts() -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, ...]:
    font_dir = Path("C:/Windows/Fonts")
    regular_candidates = [font_dir / "segoeui.ttf", font_dir / "arial.ttf"]
    bold_candidates = [font_dir / "segoeuib.ttf", font_dir / "arialbd.ttf"]

    def load(candidates: list[Path], size: int):
        for candidate in candidates:
            if candidate.exists():
                return ImageFont.truetype(str(candidate), size=size)
        return ImageFont.load_default()

    return (
        load(bold_candidates, 58),
        load(regular_candidates, 27),
        load(bold_candidates, 23),
        load(regular_candidates, 20),
        load(bold_candidates, 17),
        load(regular_candidates, 16),
    )


def draw_wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], font, fill: str, width: int, gap: int = 9) -> int:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)

    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + gap
    return y


def make_base(title: str, subtitle: str, slide: int, total: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    large, body, medium, small, tiny_bold, tiny = FONTS

    for x in range(0, WIDTH, 64):
        draw.line((x, 0, x, HEIGHT), fill="#101419", width=1)
    for y in range(0, HEIGHT, 64):
        draw.line((0, y, WIDTH, y), fill="#101419", width=1)

    draw.rounded_rectangle((42, 36, 80, 74), radius=10, fill=BLUE)
    draw.text((51, 41), "CG", font=tiny_bold, fill=WHITE)
    draw.text((94, 40), "CRASH GUARD", font=tiny_bold, fill=WHITE)
    draw.text((94, 62), "AI INCIDENT RESPONSE", font=tiny, fill=MUTED)
    draw.text((1132, 48), f"{slide:02d} / {total:02d}", font=tiny, fill=MUTED)
    draw.line((42, 96, WIDTH - 42, 96), fill="#29313A", width=1)

    draw.text((64, 129), title, font=large, fill=WHITE)
    draw_wrapped(draw, subtitle, (66, 204), body, MUTED, WIDTH - 132, 7)

    draw.line((64, HEIGHT - 47, WIDTH - 64, HEIGHT - 47), fill="#29313A", width=2)
    progress_width = int((WIDTH - 128) * slide / total)
    draw.line((64, HEIGHT - 47, 64 + progress_width, HEIGHT - 47), fill=BLUE, width=3)
    draw.text((64, HEIGHT - 35), "CRASH GUARD  /  PROJECT PRESENTATION", font=tiny, fill="#7E8994")
    return image, draw


def add_tag(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, color: str = BLUE) -> None:
    _, _, _, _, bold, _ = FONTS
    bounds = draw.textbbox((x, y), label, font=bold)
    draw.rounded_rectangle((x - 10, y - 5, bounds[2] + 10, bounds[3] + 7), radius=9, fill="#202832")
    draw.rounded_rectangle((x - 10, y - 5, x - 5, bounds[3] + 7), radius=2, fill=color)
    draw.text((x, y), label, font=bold, fill=WHITE)


def fit_image(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    return image


def paste_rounded(canvas: Image.Image, image: Image.Image, box: tuple[int, int, int, int], radius: int = 16) -> None:
    x, y, width, height = box
    fitted = fit_image(image, (width, height))
    background = Image.new("RGB", (width, height), "#090B0E")
    px = (width - fitted.width) // 2
    py = (height - fitted.height) // 2
    background.paste(fitted, (px, py))
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=255)
    canvas.paste(background, (x, y), mask)


def draw_title(duration: float, logo_path: Path) -> Iterator[np.ndarray]:
    large, body, medium, small, _, tiny = FONTS
    logo = Image.open(logo_path).convert("RGB") if logo_path.exists() else None
    for frame_index in range(round(duration * FPS)):
        image = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(image)
        for x in range(0, WIDTH, 64):
            draw.line((x, 0, x, HEIGHT), fill="#101419", width=1)
        for y in range(0, HEIGHT, 64):
            draw.line((0, y, WIDTH, y), fill="#101419", width=1)
        draw.rounded_rectangle((72, 76, 116, 120), radius=12, fill=BLUE)
        draw.text((82, 82), "CG", font=FONTS[4], fill=WHITE)
        draw.text((134, 82), "CRASH GUARD", font=FONTS[4], fill=WHITE)

        if logo:
            tile = Image.new("RGB", (300, 300), "#FFFFFF")
            logo_copy = fit_image(logo, (270, 270))
            tile.paste(logo_copy, ((300 - logo_copy.width) // 2, (300 - logo_copy.height) // 2))
            image.paste(tile, (842, 200))

        draw.text((76, 228), "SEE THE INCIDENT.", font=large, fill=WHITE)
        draw.text((76, 300), "MOVE THE RESPONSE.", font=large, fill=BLUE)
        draw_wrapped(
            draw,
            "AI-powered traffic accident detection, evidence capture, and authority response.",
            (80, 397),
            body,
            MUTED,
            700,
        )
        add_tag(draw, 80, 535, "CAMERA PANEL  +  AUTHORITY MANAGEMENT")
        draw.line((80, 625, WIDTH - 80, 625), fill="#29313A", width=2)
        draw.text((80, 644), "FINAL YEAR PROJECT  /  SYSTEM WALKTHROUGH", font=tiny, fill=MUTED)
        yield cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def draw_workflow(duration: float, slide: int, total: int) -> Iterator[np.ndarray]:
    large, body, medium, small, bold, tiny = FONTS
    steps = [
        ("01", "CAMERA FEED", "Traffic video enters the monitoring node."),
        ("02", "YOLOv8", "The model checks frames for accident classes."),
        ("03", "EVIDENCE", "Pre-event buffer plus post-event recording."),
        ("04", "AUTHORITY", "Incident record, video, location, and alert."),
    ]
    for frame_index in range(round(duration * FPS)):
        image, draw = make_base("One incident. One connected workflow.", "A camera-side detector sends evidence and incident details toward the authority workflow.", slide, total)
        start_x, gap, card_w = 65, 20, 270
        for i, (number, label, detail) in enumerate(steps):
            x = start_x + i * (card_w + gap)
            draw.rounded_rectangle((x, 335, x + card_w, 555), radius=18, fill=PANEL, outline="#29313A", width=1)
            draw.ellipse((x + 22, 360, x + 68, 406), fill=BLUE if i == 1 else "#26313C")
            draw.text((x + 32, 370), number, font=bold, fill=WHITE)
            draw.text((x + 22, 430), label, font=medium, fill=WHITE)
            draw_wrapped(draw, detail, (x + 22, 470), small, MUTED, card_w - 44, 5)
            if i < len(steps) - 1:
                cy = 444
                draw.line((x + card_w + 4, cy, x + card_w + gap - 4, cy), fill=BLUE, width=3)
                draw.polygon(((x + card_w + gap - 4, cy), (x + card_w + gap - 12, cy - 6), (x + card_w + gap - 12, cy + 6)), fill=BLUE)
        draw.text((67, 588), "10s PRE-EVENT BUFFER", font=bold, fill=MINT)
        draw.text((347, 588), "10s POST-EVENT CLIP", font=bold, fill=MUTED)
        yield cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def draw_demo_scene(
    cap: cv2.VideoCapture,
    source_fps: float,
    start_seconds: float,
    duration: float,
    panel: str,
    slide: int,
    total: int,
    title: str,
    subtitle: str,
    tag: str,
    detail: str,
    freeze: bool = False,
    redact_credentials: bool = False,
) -> Iterator[np.ndarray]:
    start_frame = int(start_seconds * source_fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    source_index = start_frame - 1
    last_source_frame = None
    source_midpoint = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) // 2)
    large, body, medium, small, bold, tiny = FONTS

    for output_index in range(round(duration * FPS)):
        wanted_index = start_frame + int(output_index * source_fps / FPS)
        while source_index < wanted_index and not freeze:
            ok, last_source_frame = cap.read()
            if not ok:
                break
            source_index += 1
        if last_source_frame is None:
            ok, last_source_frame = cap.read()
            if not ok:
                break
            source_index += 1

        if redact_credentials:
            x1, y1, x2, y2 = 425, 395, 660, 470
            last_source_frame[y1:y2, x1:x2] = cv2.GaussianBlur(last_source_frame[y1:y2, x1:x2], (31, 31), 0)

        if panel == "top":
            crop = last_source_frame[:source_midpoint]
        else:
            crop = last_source_frame[source_midpoint:]
        crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        crop_image = Image.fromarray(crop)

        image, draw = make_base(title, subtitle, slide, total)
        draw.rounded_rectangle((58, 300, 897, 632), radius=21, fill=PANEL, outline="#2B333D", width=1)
        paste_rounded(image, crop_image, (76, 318, 803, 296), 13)
        draw.rounded_rectangle((926, 300, 1222, 632), radius=20, fill=PANEL, outline="#2B333D", width=1)
        add_tag(draw, 951, 330, tag)
        text_y = draw_wrapped(draw, detail, (952, 386), small, WHITE, 235, 7)
        draw.line((952, text_y + 8, 1195, text_y + 8), fill="#313B45", width=1)
        draw.text((952, text_y + 24), "DEMO FOOTAGE", font=bold, fill=MUTED)
        draw.text((952, text_y + 50), "Recorded project interface", font=tiny, fill=MUTED)
        yield cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def draw_pipeline(duration: float, slide: int, total: int) -> Iterator[np.ndarray]:
    large, body, medium, small, bold, tiny = FONTS
    services = [
        ("CLOUDINARY", "Evidence video", BLUE),
        ("FIRESTORE", "Incident record", MINT),
        ("FCM", "Responder alert", "#E7C46A"),
    ]
    for frame_index in range(round(duration * FPS)):
        image, draw = make_base("Detection to dispatch-ready information.", "The upload worker handles cloud operations separately from the video preview loop.", slide, total)
        stages = [("DETECT", "YOLOv8"), ("CAPTURE", "Pre + post-event"), ("PUBLISH", "Cloud services"), ("REVIEW", "Authority panel")]
        x0, card_w, gap = 68, 250, 55
        for i, (label, detail) in enumerate(stages):
            x = x0 + i * (card_w + gap)
            draw.rounded_rectangle((x, 315, x + card_w, 408), radius=15, fill=PANEL, outline="#2B333D", width=1)
            draw.text((x + 20, 335), label, font=bold, fill=WHITE)
            draw.text((x + 20, 370), detail, font=small, fill=MUTED)
            if i < len(stages) - 1:
                draw.line((x + card_w + 8, 361, x + card_w + gap - 9, 361), fill=BLUE, width=3)
                draw.polygon(((x + card_w + gap - 8, 361), (x + card_w + gap - 17, 355), (x + card_w + gap - 17, 367)), fill=BLUE)

        for i, (label, detail, color) in enumerate(services):
            x = 181 + i * 312
            draw.rounded_rectangle((x, 465, x + 250, 548), radius=14, fill=PANEL_LIGHT, outline="#2B333D", width=1)
            draw.ellipse((x + 17, 487, x + 37, 507), fill=color)
            draw.text((x + 52, 476), label, font=bold, fill=WHITE)
            draw.text((x + 52, 508), detail, font=tiny, fill=MUTED)
        draw.text((184, 580), "Cloud video  ·  Firestore metadata  ·  Firebase Cloud Messaging", font=small, fill=MUTED)
        yield cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def draw_outro(duration: float, slide: int, total: int) -> Iterator[np.ndarray]:
    large, body, medium, small, bold, tiny = FONTS
    for frame_index in range(round(duration * FPS)):
        image, draw = make_base("CRASH GUARD", "AI-assisted accident detection and evidence delivery for faster incident awareness.", slide, total)
        draw.rounded_rectangle((66, 330, 1214, 535), radius=24, fill=PANEL, outline="#29313A", width=1)
        phrases = [("DETECT", BLUE), ("PRESERVE", WHITE), ("NOTIFY", MINT), ("RESPOND", WHITE)]
        x = 112
        for index, (phrase, color) in enumerate(phrases):
            draw.text((x, 394), phrase, font=medium, fill=color)
            x += 260
            if index < len(phrases) - 1:
                draw.text((x - 28, 394), "/", font=medium, fill=MUTED)
        draw.text((69, 585), "CAMERA PANEL  +  AUTHORITY MANAGEMENT", font=bold, fill=MUTED)
        yield cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the Crash Guard project presentation video.")
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1] / "Carsh Guard Final.mp4")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "Crash_Guard_Project_Presentation.mp4")
    args = parser.parse_args()

    if not args.source.exists():
        raise FileNotFoundError(f"Source demo not found: {args.source}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(args.source))
    if not cap.isOpened():
        raise OSError(f"Could not open source demo: {args.source}")
    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    if cap.get(cv2.CAP_PROP_FRAME_HEIGHT) < 2:
        raise ValueError("Source demo has invalid dimensions")

    writer = cv2.VideoWriter(
        str(args.output),
        cv2.VideoWriter_fourcc(*"mp4v"),
        FPS,
        (WIDTH, HEIGHT),
    )
    if not writer.isOpened():
        cap.release()
        raise OSError("Could not initialize MP4 video writer")

    scenes = [
        draw_title(4, Path(__file__).resolve().parents[1] / "logo.png"),
        draw_workflow(5, 2, 10),
        draw_demo_scene(cap, source_fps, 0, 6, "bottom", 3, 10, "Configure the camera node.", "Set a station label and geographic coordinates before monitoring.", "CAMERA SETUP", "Enter the camera address and its latitude / longitude before monitoring.", freeze=True),
        draw_demo_scene(cap, source_fps, 18, 7, "bottom", 4, 10, "AI monitoring on the video feed.", "The desktop panel displays model detections over the selected traffic video.", "LIVE DETECTION", "YOLOv8 labels vehicles and accident severity classes in the operator preview."),
        draw_demo_scene(cap, source_fps, 38, 6, "bottom", 5, 10, "Preserve context around an incident.", "A rolling frame buffer keeps recent footage available when a detection triggers.", "VIDEO EVIDENCE", "Capture pre-event context, then continue recording after the trigger."),
        draw_demo_scene(cap, source_fps, 0, 4, "top", 6, 10, "Authority sign-in screen.", "A recorded management-panel demo shows the responder login view.", "AUTHORITY ACCESS", "Sign-in screen shown in demo footage. Credential fields are blurred.", freeze=True, redact_credentials=True),
        draw_demo_scene(cap, source_fps, 55, 6, "top", 7, 10, "Authorities review the reported location.", "The management-panel demo includes a map view alongside incident information.", "AUTHORITY VIEW", "Use the incident location to support review and coordination."),
        draw_demo_scene(cap, source_fps, 69, 6, "top", 8, 10, "Review earlier accident reports.", "The recorded management-panel demo also shows an accident-log view.", "INCIDENT HISTORY", "Open a report to inspect its recorded details and evidence."),
        draw_pipeline(7, 9, 10),
        draw_outro(4, 10, 10),
    ]

    frame_count = 0
    for scene in scenes:
        for frame in scene:
            writer.write(frame)
            frame_count += 1

    writer.release()
    cap.release()
    print(f"Presentation created: {args.output}")
    print(f"Duration: {frame_count / FPS:.1f} seconds")


FONTS = get_fonts()


if __name__ == "__main__":
    main()