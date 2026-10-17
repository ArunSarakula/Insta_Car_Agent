"""Turns a post's slide text into finished Instagram media: branded JPG
slides for images, memes and carousels, and an MP4 for reels.

Everything is drawn from text, so every post is original (no copyright
issues) and needs no design work from the owner."""

import re
import subprocess
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import ROOT

FONTS = ROOT / "assets" / "fonts"
BOLD = str(FONTS / "Inter-ExtraBold.otf")
MEDIUM = str(FONTS / "Inter-Medium.otf")

# Royalty-free tracks (Pixabay licence), one folder per mood.
MUSIC = ROOT / "assets" / "music"
MOODS = ["upbeat", "tech", "chill", "epic", "phonk"]

NAVY = (14, 26, 43)
TEAL = (0, 209, 178)
AMBER = (255, 176, 32)
WHITE = (245, 247, 250)
GREY = (170, 182, 197)
INK = (20, 24, 31)

FEED = (1080, 1350)   # 4:5 portrait, the largest feed size
REEL = (1080, 1920)   # 9:16
REEL_SAFE_TOP = 290      # below Instagram's back button and "Reels" title
REEL_SAFE_BOTTOM = 440   # above the username, caption and audio line
REEL_SAFE_RIGHT = 120    # clear of the like / comment / share buttons
BRAND_GAP = 60           # handle shown under the text on reels
BRAND_HEIGHT = 44

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


def _brand_line(d, x, y, handle):
    font = ImageFont.truetype(BOLD, 36)
    d.text((x, y), handle, font=font, fill=TEAL)


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

    reel = size == REEL
    # Reels: Instagram draws its own buttons over the top ~15%, the bottom
    # ~22% and a column on the right, so text stays inside the clear area.
    top = REEL_SAFE_TOP if reel else 70
    d.rectangle([0, 0, w, 14], fill=TEAL)
    d.text((pad, top), "DECODE THE DRIVE", font=small, fill=TEAL if not meme else INK)
    if total > 1 and not reel:
        counter = f"{index}/{total}"
        d.text((w - pad - d.textlength(counter, font=small), top), counter, font=small, fill=GREY)

    usable = w - 2 * pad - (REEL_SAFE_RIGHT if reel else 0)
    head = _fit(d, heading, BOLD, usable, int(h * (0.24 if body else 0.36)),
                92 if reel else 104, 44) if heading else None
    text = _fit(d, body, MEDIUM, usable, int(h * 0.26), 50 if reel else 58, 30) if body else None
    gap = 132  # space for the amber divider between heading and body
    block = (len(head[1]) * head[2] if head else 0) + (gap if head and text else 0) \
        + (len(text[1]) * text[2] if text else 0) + (BRAND_GAP + BRAND_HEIGHT if reel else 0)
    if reel:  # centre within the clear area
        y = max(REEL_SAFE_TOP + 90, (REEL_SAFE_TOP + h - REEL_SAFE_BOTTOM - block) // 2)
    else:
        y = max(int(h * 0.14), (h - block) // 2 - 40)
    if head:
        y = _draw_lines(d, pad, y, head, head_fill)
    if head and text:
        d.rectangle([pad, y + 40, pad + 120, y + 50], fill=AMBER)
        y += gap
    if text:
        y = _draw_lines(d, pad, y, text, body_fill)
    if reel:  # handle right under the text, away from Instagram's own name
        _brand_line(d, pad, y + BRAND_GAP, handle)

    foot = ImageFont.truetype(MEDIUM, 32)
    if not reel:  # on reels Instagram already shows the username at the bottom
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


def _seconds(slide: dict, first: bool = False) -> float:
    """Fast pacing: the hook gets under 2 seconds (most viewers decide by
    then), the rest just long enough to read."""
    words = len(f"{slide.get('heading', '')} {slide.get('body', '')}".split())
    if first:
        return 1.8
    return max(2.0, min(4.0, 0.9 + words * 0.26))


def pick_track(mood: str, seed: str, music_dir: Path = MUSIC) -> Path | None:
    """A track for the mood, chosen from the post id so different reels get
    different tracks. Falls back to any track if the mood folder is empty."""
    tracks = sorted((music_dir / mood).glob("*.mp3")) or sorted(music_dir.glob("*/*.mp3"))
    return tracks[zlib.crc32(seed.encode()) % len(tracks)] if tracks else None


def render_reel(slides: list[dict], path: Path, handle="@decodethedrive",
                music: Path | None = None) -> Path:
    """One frame per slide, sliding from one to the next. The music track is trimmed to the
    reel's length (leading silence skipped, faded in and out, levelled);
    without one the reel gets a silent track, as Instagram expects audio."""
    frames = [render_slide(s, path.parent / f"frame-{i + 1}.jpg", REEL, i + 1, len(slides), handle)
              for i, s in enumerate(slides)]
    durations = [_seconds(s, first=i == 0) for i, s in enumerate(slides)]
    fade = 0.3
    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error"]
    for frame, dur in zip(frames, durations):
        cmd += ["-framerate", "30", "-loop", "1", "-t", f"{dur + fade:.2f}", "-i", str(frame)]
    total = sum(durations) + fade
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music)]
        audio = (f"[{len(frames)}:a]silenceremove=start_periods=1:start_threshold=-40dB,"
                 f"atrim=0:{total:.2f},asetpts=PTS-STARTPTS,afade=t=in:d=0.5,"
                 f"afade=t=out:st={max(0, total - 1.5):.2f}:d=1.5,"
                 f"loudnorm=I=-16:TP=-1.5,aresample=44100[a]")
    else:
        cmd += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=44100:cl=stereo"]
        audio = f"[{len(frames)}:a]anull[a]"

    chains, last, offset = [], "0:v", 0.0
    for i, dur in enumerate(durations):
        # Constant slow motion keeps the eye on screen: the hook pulls out
        # from a close zoom, later slides push in gently.
        n = int((dur + fade) * 30)
        zoom = f"1.12-0.12*on/{n}" if i == 0 else f"1+0.05*on/{n}"
        chains.append(f"[{i}:v]scale=1296:2304,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':"
                      f"y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,format=yuv420p,setsar=1[v{i}]")
    last = "v0"
    for i in range(1, len(frames)):
        offset += durations[i - 1]
        chains.append(f"[{last}][v{i}]xfade=transition=slideleft:duration={fade}:offset={offset:.2f}[x{i}]")
        last = f"x{i}"
    cmd += ["-filter_complex", ";".join(chains + [audio]), "-map", f"[{last}]", "-map", "[a]",
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
        track = pick_track(post.get("music") or "upbeat", post["id"])
        files = [render_reel(slides, out / "reel.mp4", handle, track)]
        if track:
            post["music_track"] = track.name
    elif fmt == "carousel" and len(slides) >= 2:
        slides = slides[:10]
        files = [render_slide(s, out / f"slide-{i + 1}.jpg", FEED, i + 1, len(slides), handle)
                 for i, s in enumerate(slides)]
    else:
        style = "meme" if fmt == "meme" else "info"
        files = [render_slide(slides[0], out / "post.jpg", FEED, handle=handle, style=style)]
    return [str(f.relative_to(media_root.parent)) for f in files]
