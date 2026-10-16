"""Turns a post's slide text into finished Instagram media: branded JPG
slides for images, memes and carousels, and an MP4 for reels.

Everything is drawn from text, so every post is original (no copyright
issues) and needs no design work from the owner."""

import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import ROOT

FONTS = ROOT / "assets" / "fonts"
BOLD = str(FONTS / "Inter-ExtraBold.otf")
MEDIUM = str(FONTS / "Inter-Medium.otf")

NAVY = (14, 26, 43)
TEAL = (0, 209, 178)
AMBER = (255, 176, 32)
WHITE = (245, 247, 250)
GREY = (170, 182, 197)
INK = (20, 24, 31)

FEED = (1080, 1350)   # 4:5 portrait, the largest feed size
REEL = (1080, 1920)   # 9:16

# Inter has no emoji; drop anything outside the ranges it covers.
_UNSUPPORTED = re.compile("[\U0001F000-\U0001FFFF☀-➿️‍]")


def clean(text: str) -> str:
    return re.sub(r"[ \t]+", " ", _UNSUPPORTED.sub("", text or "")).strip()


def _wrap(draw, text, font, width):
    lines = []
    for para in text.split("\n"):
        words, line = para.split(), ""
        for word in words:
            trial = f"{line} {word}".strip()
            if draw.textlength(trial, font=font) <= width or not line:
                line = trial
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def _fit(draw, text, font_path, width, height, start, minimum, spacing=1.18):
    """Largest font size at which `text` wraps into the box."""
    size = start
    while True:
        font = ImageFont.truetype(font_path, size)
        lines = _wrap(draw, text, font, width)
        line_h = int(size * spacing)
        if len(lines) * line_h <= height or size <= minimum:
            return font, lines, line_h
        size -= 4


def _draw_lines(draw, x, y, layout, fill):
    font, lines, line_h = layout
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_h
    return y


def render_slide(slide: dict, path: Path, size=FEED, index=1, total=1,
                 handle="@decodethedrive", style="info") -> Path:
    w, h = size
    pad = 96
    heading, body = clean(slide.get("heading", "")), clean(slide.get("body", ""))
    meme = style == "meme"
    bg, head_fill, body_fill = (WHITE, INK, (0, 140, 120)) if meme else (NAVY, WHITE, GREY)

    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)
    small = ImageFont.truetype(BOLD, 30)

    d.rectangle([0, 0, w, 14], fill=TEAL)
    d.text((pad, 70), "DECODE THE DRIVE", font=small, fill=TEAL if not meme else INK)
    if total > 1:
        counter = f"{index}/{total}"
        d.text((w - pad - d.textlength(counter, font=small), 70), counter, font=small, fill=GREY)

    usable = w - 2 * pad
    reel = size == REEL
    head = _fit(d, heading, BOLD, usable, int(h * (0.32 if body else 0.5)),
                128 if reel else 104, 48) if heading else None
    text = _fit(d, body, MEDIUM, usable, int(h * 0.36), 64 if reel else 58, 30) if body else None
    gap = 132  # space for the amber divider between heading and body
    block = (len(head[1]) * head[2] if head else 0) + (gap if head and text else 0) \
        + (len(text[1]) * text[2] if text else 0)
    y = max(int(h * 0.14), (h - block) // 2 - 40)
    if head:
        y = _draw_lines(d, pad, y, head, head_fill)
    if head and text:
        d.rectangle([pad, y + 40, pad + 120, y + 50], fill=AMBER)
        y += gap
    if text:
        _draw_lines(d, pad, y, text, body_fill)

    foot = ImageFont.truetype(MEDIUM, 32)
    d.text((pad, h - 130), handle, font=foot, fill=GREY if not meme else INK)
    if total > 1 and index < total and size == FEED:
        swipe = "swipe  >"
        d.text((w - pad - d.textlength(swipe, font=foot), h - 130), swipe, font=foot, fill=TEAL)

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=92)
    return path


def ffmpeg_exe() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _seconds(slide: dict) -> float:
    words = len(f"{slide.get('heading', '')} {slide.get('body', '')}".split())
    return max(2.5, min(6.0, 1.2 + words * 0.32))


def render_reel(slides: list[dict], path: Path, handle="@decodethedrive") -> Path:
    """One frame per slide, cross-faded, with a silent audio track
    (Instagram expects an audio stream)."""
    frames = [render_slide(s, path.parent / f"frame-{i + 1}.jpg", REEL, i + 1, len(slides), handle)
              for i, s in enumerate(slides)]
    durations = [_seconds(s) for s in slides]
    fade = 0.4
    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error"]
    for frame, dur in zip(frames, durations):
        cmd += ["-loop", "1", "-t", f"{dur + fade:.2f}", "-i", str(frame)]
    total = sum(durations) + fade
    cmd += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=44100:cl=stereo"]

    chains, last, offset = [], "0:v", 0.0
    for i in range(len(frames)):
        chains.append(f"[{i}:v]fps=30,format=yuv420p,setsar=1[v{i}]")
    last = "v0"
    for i in range(1, len(frames)):
        offset += durations[i - 1]
        chains.append(f"[{last}][v{i}]xfade=transition=fade:duration={fade}:offset={offset:.2f}[x{i}]")
        last = f"x{i}"
    cmd += ["-filter_complex", ";".join(chains), "-map", f"[{last}]", "-map", f"{len(frames)}:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(path)]
    subprocess.run(cmd, check=True)
    for frame in frames[1:]:
        frame.unlink()
    frames[0].rename(path.parent / "cover.jpg")
    return path


def render_post(post: dict, media_root: Path, handle="@decodethedrive") -> list[str]:
    """Render a post's media and return paths relative to the repo root."""
    out = media_root / post["id"]
    slides = [s for s in post.get("slides", []) if s.get("heading") or s.get("body")]
    if not slides:
        slides = [{"heading": post.get("hook", post.get("title", "")), "body": ""}]
    fmt = post["format"]
    if fmt == "reel":
        files = [render_reel(slides, out / "reel.mp4", handle)]
    elif fmt == "carousel" and len(slides) >= 2:
        slides = slides[:10]
        files = [render_slide(s, out / f"slide-{i + 1}.jpg", FEED, i + 1, len(slides), handle)
                 for i, s in enumerate(slides)]
    else:
        style = "meme" if fmt == "meme" else "info"
        files = [render_slide(slides[0], out / "post.jpg", FEED, handle=handle, style=style)]
    return [str(f.relative_to(media_root.parent)) for f in files]
