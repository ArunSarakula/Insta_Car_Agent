"""Animated reels: every frame is drawn, so text pops in word by word, a
meter drains as each point lands, and sound effects mark each beat.

"meter" format, for "what eats your X" topics (range, mileage, tyre life):
slide 1 is the hook, slide 2 the baseline (meter full), the middle slides
each knock a piece off the meter, and the last slide is the takeaway."""

import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .design import (AMBER, BOLD, GREY, INK, MEDIUM, NAVY, REEL, REEL_SAFE_BOTTOM, REEL_SAFE_RIGHT,
                     REEL_SAFE_TOP, TEAL, WHITE, _fit, clean, ffmpeg_exe)

W, H = REEL
FPS = 30
PACE = 0.65  # content plays at 65% of its timed speed
LEAD = 0.8   # seconds of the first scene's intro skipped
VOICE_AT = 0.25  # each scene's line starts this long after the scene
X0 = 80
XW = W - X0 - REEL_SAFE_RIGHT - 40
TOP, BOT = REEL_SAFE_TOP, H - REEL_SAFE_BOTTOM
RED = (235, 70, 70)
GREEN = (40, 200, 120)
RATE = 44100


def ease_out(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def ease_back(x):  # overshoots a little, then settles: a "pop"
    x = min(1.0, max(0.0, x))
    c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def _font(path, size):
    return ImageFont.truetype(path, size)


def _glow(radius=700, color=TEAL, strength=70):
    yy, xx = np.mgrid[-radius:radius, -radius:radius]
    a = np.clip(1 - np.sqrt(xx ** 2 + yy ** 2) / radius, 0, 1) ** 2 * strength
    im = np.zeros((2 * radius, 2 * radius, 4), np.uint8)
    im[..., :3] = color
    im[..., 3] = a.astype(np.uint8)
    return Image.fromarray(im, "RGBA")


class Words:
    """A heading laid out once; each word slides up and fades in on cue."""

    def __init__(self, text, y, size=96, minimum=56, height=420, font=BOLD, color=WHITE):
        probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        f, lines, line_h = _fit(probe, clean(text), font, XW, height, size, minimum)
        self.font, self.color, self.items = f, color, []
        for n, line in enumerate(lines):
            x = X0
            for word in line.split():
                self.items.append((x, y + n * line_h, word))
                x += probe.textlength(word + " ", font=f)
        self.bottom = y + len(lines) * line_h

    def draw(self, d, t, start=0.0, stagger=0.07, rise=46):
        for i, (x, y, word) in enumerate(self.items):
            p = ease_out((t - start - i * stagger) / 0.28)
            if p > 0:
                d.text((x, y + rise * (1 - p)), word, font=self.font, fill=(*self.color, int(255 * p)))


def _fade_text(d, text, x, y, t, start, font, color, width=XW, height=300, size=48):
    p = ease_out((t - start) / 0.35)
    if p <= 0:
        return y
    f, lines, line_h = _fit(d, clean(text), font, width, height, size, 30)
    for n, line in enumerate(lines):
        d.text((x, y + n * line_h + 20 * (1 - p)), line, font=f, fill=(*color, int(255 * p)))
    return y + len(lines) * line_h


def _pill(d, x, y, label, bg, fg=WHITE, alpha=255, size=40):
    f = _font(BOLD, size)
    w = d.textlength(label, font=f)
    d.rounded_rectangle([x, y, x + w + 44, y + size + 34], radius=(size + 34) // 2, fill=(*bg, alpha))
    d.text((x + 22, y + 15), label, font=f, fill=(*fg, alpha))


def _level_color(level):
    return GREEN if level > 0.62 else (AMBER if level > 0.4 else RED)


def _battery(d, y, level, label, flash=None, marker=None, alpha=255):
    """Horizontal battery. `flash` = (low, high, strength) for the piece
    just lost; `marker` = level of the buffer line."""
    bw, bh = 760, 190
    x = X0
    d.rounded_rectangle([x, y, x + bw, y + bh], radius=34, outline=(*WHITE, alpha), width=10)
    d.rounded_rectangle([x + bw + 8, y + bh * 0.3, x + bw + 34, y + bh * 0.7], radius=8, fill=(*WHITE, alpha))
    inner = bw - 44
    fill_w = max(0, inner * level)
    if fill_w > 4:
        d.rounded_rectangle([x + 22, y + 22, x + 22 + fill_w, y + bh - 22], radius=20,
                            fill=(*_level_color(level), alpha))
    if flash:
        lo, hi, s = flash
        if s > 0 and hi > lo:
            d.rounded_rectangle([x + 22 + inner * lo, y + 22, x + 22 + inner * hi, y + bh - 22], radius=20,
                                fill=(*RED, int(alpha * s)))
    if marker is not None:
        mx = x + 22 + inner * marker
        for yy in range(int(y - 26), int(y + bh + 26), 22):
            d.line([(mx, yy), (mx, yy + 12)], fill=(*WHITE, alpha), width=6)
        d.text((mx - 10, y + bh + 40), "buffer", font=_font(BOLD, 34), fill=(*WHITE, alpha))
    d.text((x, y - 62), label, font=_font(BOLD, 38), fill=(*GREY, alpha))
    d.text((x + bw - 10, y - 62), f"{round(level * 100)}%", font=_font(BOLD, 38),
           fill=(*_level_color(level), alpha), anchor="ra")


def meter_scenes(post, handle):
    """(duration, draw(frame, draw, t), sound cues) for each scene."""
    slides = post["slides"]
    base, drains, last = slides[1], slides[2:-1], slides[-1]
    levels = [round(v, 2) for v in np.linspace(1.0, 0.55, len(drains) + 1)]
    scenes = []
    battery_y = 1000

    def text_scene(slide, badge, battery, dur, cues):
        heading = Words(slide["heading"], TOP + 150, size=92)

        def draw(frame, d, t):
            if badge:
                _pill(d, X0, TOP + 40, badge, TEAL, INK, alpha=int(255 * ease_out(t / 0.2)), size=34)
            heading.draw(d, t)
            _fade_text(d, slide.get("body", ""), X0, heading.bottom + 30, t, 0.45, MEDIUM, GREY, size=46,
                       height=260)
            battery(d, t)
        return dur, draw, cues

    scenes.append(text_scene(base, "THE CLAIM", lambda d, t: _battery(
        d, battery_y, 1.0, "CLAIMED RANGE", alpha=int(255 * ease_out((t - 0.3) / 0.4))), 3.0, [("whoosh", 0)]))
    for i, s in enumerate(drains):
        hi, lo = levels[i], levels[i + 1]

        def battery(d, t, hi=hi, lo=lo):
            p = ease_out((t - 0.9) / 0.45)
            _battery(d, battery_y, hi - (hi - lo) * p, "REAL RANGE",
                     flash=(lo, hi, max(0.0, 1 - max(0, t - 0.9) / 0.7)) if t > 0.9 else (lo, hi, 0.0))
        scenes.append(text_scene(s, f"RANGE KILLER {i + 1}/{len(drains)}", battery, 3.1,
                                 [("whoosh", 0), ("drain", 0.9)]))
    final = levels[-1]
    scenes.append(text_scene(last, "THE FIX", lambda d, t: _battery(
        d, battery_y, final, "PLAN FOR THIS", marker=0.15 if t > 0.8 else None), 3.6,
        [("whoosh", 0), ("ding", 0.8)]))
    return scenes


# ---- sound -----------------------------------------------------------------

def _sfx(kind):
    n = {"whoosh": 0.45, "pop": 0.09, "hit": 0.35, "drain": 0.5, "ding": 0.8}[kind]
    t = np.arange(int(RATE * n)) / RATE
    rng = np.random.default_rng(len(kind))
    if kind == "whoosh":  # noise swept through a moving low-pass
        noise = rng.standard_normal(len(t))
        out, acc = np.zeros_like(noise), 0.0
        cut = 0.02 + 0.25 * np.sin(np.pi * t / n)
        for i, x in enumerate(noise):
            acc += cut[i] * (x - acc)
            out[i] = acc
        return out * np.sin(np.pi * t / n) ** 2 * 1.4
    if kind == "pop":
        return np.sin(2 * np.pi * 900 * t) * np.exp(-t * 60) * 0.5
    if kind == "hit":
        return (np.sin(2 * np.pi * (70 - 30 * t) * t) * np.exp(-t * 9)
                + 0.15 * rng.standard_normal(len(t)) * np.exp(-t * 30))
    if kind == "drain":  # falling tone: something lost
        f = 520 - 380 * t / n
        return np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t * 4) * 0.45
    return (np.sin(2 * np.pi * 1320 * t) + 0.5 * np.sin(2 * np.pi * 1980 * t)) * np.exp(-t * 5) * 0.3


def _decode(path):
    """An audio file as mono samples at RATE, from -1 to 1."""
    raw = subprocess.run([ffmpeg_exe(), "-loglevel", "error", "-i", str(path), "-f", "s16le", "-ac", "1",
                          "-ar", str(RATE), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16) / 32768


def _write_sfx(cues, total, path, voice=()):
    """Sound effects, plus the voice lines (samples, start) when there are
    any, with the effects turned down so the voice stays clear."""
    track = np.zeros(int(RATE * total) + RATE)
    for kind, at in cues:
        s = _sfx(kind)
        i = int(at * RATE)
        track[i:i + len(s)] += s[:len(track) - i]
    track *= 0.25 if voice else 0.6
    for samples, at in voice:
        i = int(at * RATE)
        track[i:i + len(samples)] += samples[:len(track) - i]
    track = np.clip(track, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((track * 32767).astype(np.int16).tobytes())


# ---- render ----------------------------------------------------------------

def formats():
    """Animated formats: reel_style -> (scene builder, thumbnail designer)."""
    from .motion_fog import fog_scenes, fog_thumbnail
    from .motion_visuals import VISUALS, visual_scenes, visual_thumbnail
    return {"meter": (meter_scenes, meter_thumbnail), "fog": (fog_scenes, fog_thumbnail),
            **{name: (visual_scenes, visual_thumbnail) for name in VISUALS}}


def caption_chunks(text, start, length, words=3, chars=18):
    """A spoken line cut into short on-screen captions, each shown for its
    share of the line's length (by letters), so they follow the voice."""
    weak = {"the", "a", "an", "to", "of", "and", "or", "your", "is", "are", "on", "in", "if", "you", "it"}
    chunks, cur = [], []
    for w in text.split():
        if cur and (len(cur) == words or len(" ".join(cur + [w])) > chars):
            carry = [cur.pop()] if len(cur) > 1 and cur[-1].lower() in weak else []
            chunks.append(" ".join(cur))
            cur = carry
        cur.append(w)
        if w[-1] in ".,?!:;" and cur:
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    total = sum(len(c) + 2 for c in chunks) or 1
    out, at = [], start
    for c in chunks:
        dur = length * (len(c) + 2) / total
        out.append((at, at + dur, c.strip(".,;:")))
        at += dur
    return out


def render_motion(post, path: Path, handle="@decodethedrive", music: Path | None = None,
                  voices: list[Path] | None = None) -> Path:
    """voices: one spoken line per scene; each scene then lasts at least as
    long as its line, so the text never moves on mid-sentence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    build, thumbnail = formats()[post["reel_style"]]
    # Scenes play slower than they were timed so the text can be read; there
    # is no question card up front, the thumbnail and cover already ask it.
    # The first scene starts with its heading already in, so the very first
    # frame (what the feed shows on autoplay) is never an empty screen.
    scenes = []
    for n, (dur, draw, c) in enumerate(build(post, handle)):
        lead = LEAD if n == 0 else 0.0
        scenes.append(((dur - lead) / PACE, lambda f, d, t, draw=draw, lead=lead: draw(f, d, lead + t * PACE),
                       [(k, (at - lead) / PACE) for k, at in c if at >= lead]))
    lines = [_decode(v) for v in voices] if voices else []
    for n, samples in enumerate(lines[:len(scenes)]):
        dur, draw, c = scenes[n]
        scenes[n] = (max(dur, VOICE_AT + len(samples) / RATE + 0.5), draw, c)
    starts, total = [], 0.0
    for dur, _, _ in scenes:
        starts.append(total)
        total += dur
    cues = [(k, s + at) for s, (_, _, c) in zip(starts, scenes) for k, at in c]
    captions = []
    if post.get("layout") in ("big3d", "captions") and lines:  # short captions follow the voice
        from .design import voice_lines
        for text, samples, s in zip(voice_lines(post, len(scenes)), lines, starts):
            captions += caption_chunks(text, s + VOICE_AT, len(samples) / RATE)
    sfx = path.parent / "sfx.wav"
    _write_sfx(cues, total, sfx, [(samples, s + VOICE_AT) for samples, s in zip(lines, starts)])

    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(sfx)]
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music)]
        audio = (f"[2:a]silenceremove=start_periods=1:start_threshold=-40dB,atrim=0:{total:.2f},"
                 f"asetpts=PTS-STARTPTS,afade=t=in:d=0.3,afade=t=out:st={total - 1.2:.2f}:d=1.2,"
                 f"loudnorm=I=-18:TP=-2,aresample=44100,volume={0.22 if lines else 0.7}[m];"
                 f"[1:a]aresample=44100,pan=stereo|c0=c0|c1=c0[s];"
                 f"[m][s]amix=inputs=2:duration=first:normalize=0[a]")
    else:
        audio = "[1:a]aresample=44100,pan=stereo|c0=c0|c1=c0[a]"
    cmd += ["-filter_complex", audio, "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium",
            "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}",
            "-movflags", "+faststart", str(path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    glow, glow2 = _glow(), _glow(560, AMBER, 34)
    handle_font = _font(BOLD, 36)
    for i in range(int(total * FPS)):
        t = i / FPS
        k = max(j for j, s in enumerate(starts) if s <= t)
        _, draw, _ = scenes[k]
        local = t - starts[k]
        frame = Image.new("RGBA", (W, H), (*NAVY, 255))
        # slow drifting light keeps the background alive
        frame.alpha_composite(glow, (int(-300 + 160 * math.sin(t * 0.5)), int(200 + 120 * math.cos(t * 0.4))))
        frame.alpha_composite(glow2, (int(500 + 120 * math.cos(t * 0.6)), int(900 + 140 * math.sin(t * 0.45))))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        draw(frame, d, local)
        d.rounded_rectangle([X0, TOP - 6, X0 + XW, TOP + 2], radius=4, fill=(255, 255, 255, 40))
        d.rounded_rectangle([X0, TOP - 6, X0 + XW * t / total, TOP + 2], radius=4, fill=(*TEAL, 255))
        d.text((X0, BOT - 40), handle, font=handle_font, fill=(*TEAL, 255))
        for a, b, text in captions:
            if a <= t < b:  # pops in, slightly enlarged, then settles
                f = _font(BOLD, int(78 * (1 + 0.12 * (1 - ease_out((t - a) / 0.12)))))
                d.text((X0 + XW / 2, TOP + 195), text.upper(), font=f, fill=(*WHITE, 255), anchor="mm",
                       stroke_width=6, stroke_fill=(*INK, 255))
        frame.alpha_composite(layer)
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError("ffmpeg failed while rendering the animated reel")
    sfx.unlink()
    thumbnail(post, path.parent / "thumbnail.jpg", handle)
    instagram_cover(path.parent / "thumbnail.jpg", path.parent / "cover.jpg")
    return path


def instagram_cover(thumbnail: Path, cover: Path) -> Path:
    """The YouTube thumbnail as the Instagram reel cover. The profile grid
    shows only the middle 3:4 of a reel cover, so the whole design is shrunk
    into that band to keep the title and visual from being cut off."""
    band = W * 4 // 3
    with Image.open(thumbnail) as im:
        art = im.convert("RGB").resize((band * W // H, band), Image.LANCZOS)
    out = Image.new("RGB", (W, H), NAVY)
    out.paste(art, ((W - art.width) // 2, (H - band) // 2))
    out.save(cover, "JPEG", quality=92)
    return cover


def render_meter(post, path: Path, handle="@decodethedrive", music: Path | None = None) -> Path:
    return render_motion({**post, "reel_style": "meter"}, path, handle, music)


def _ev_car(d, cx, y, w, body=WHITE):
    """Side view of an EV with a bolt on the door, so the battery reads as
    a car's, not a phone's."""
    x0, h = cx - w // 2, int(w * 0.42)
    d.rounded_rectangle([x0, y + h * 0.42, x0 + w, y + h * 0.82], radius=int(h * 0.16), fill=body)
    d.polygon([(x0 + w * 0.18, y + h * 0.45), (x0 + w * 0.33, y + h * 0.08), (x0 + w * 0.70, y + h * 0.08),
               (x0 + w * 0.86, y + h * 0.45)], fill=body)
    d.polygon([(x0 + w * 0.26, y + h * 0.43), (x0 + w * 0.36, y + h * 0.16), (x0 + w * 0.505, y + h * 0.16),
               (x0 + w * 0.505, y + h * 0.43)], fill=NAVY)
    d.polygon([(x0 + w * 0.535, y + h * 0.43), (x0 + w * 0.535, y + h * 0.16), (x0 + w * 0.67, y + h * 0.16),
               (x0 + w * 0.78, y + h * 0.43)], fill=NAVY)
    d.rounded_rectangle([x0 + w * 0.94, y + h * 0.5, x0 + w, y + h * 0.6], radius=6, fill=AMBER)
    bx, by = x0 + w * 0.47, y + h * 0.5
    d.polygon([(bx + 28, by), (bx - 6, by + 52), (bx + 14, by + 52), (bx - 4, by + 100), (bx + 40, by + 38),
               (bx + 18, by + 38), (bx + 34, by)], fill=AMBER)
    for wx in (0.22, 0.78):
        r = w * 0.115
        cxw, cyw = x0 + w * wx, y + h * 0.82
        d.ellipse([cxw - r, cyw - r, cxw + r, cyw + r], fill=INK, outline=body, width=8)
        d.ellipse([cxw - r * 0.45, cyw - r * 0.45, cxw + r * 0.45, cyw + r * 0.45], fill=GREY)


def meter_thumbnail(post, path: Path, handle="@decodethedrive") -> Path:
    """Search thumbnail: a short question in huge type, the car, and the
    meter's before/after, readable at the size YouTube shows in results.
    `thumbnail_text` is "white part | amber part"."""
    text = post.get("thumbnail_text") or post["slides"][0]["heading"]
    top, _, accent = text.partition("|")
    im = Image.new("RGBA", (W, H), (*NAVY, 255))
    im.alpha_composite(_glow(900, AMBER, 60), (-360, 1000))
    im.alpha_composite(_glow(700, TEAL, 60), (180, 420))
    d = ImageDraw.Draw(im)
    parts = [(clean(p).upper(), c) for p, c in ((top, WHITE), (accent, AMBER)) if clean(p)]
    for size in range(150, 70, -8):  # largest title that still leaves room for the car and meters
        layouts = [(_fit(d, p, BOLD, W - 2 * X0, 2000, size, size, spacing=1.04), c) for p, c in parts]
        if 170 + sum(len(l[1]) * l[2] for l, _ in layouts) <= 760:
            break
    y = 170
    for (f, lines, line_h), color in layouts:
        for line in lines:
            d.text((W // 2, y), line, font=f, fill=color, anchor="ma")
            y += line_h
    _ev_car(d, W // 2, y + 50, 760)
    real = post.get("meter_end", 0.55)
    bw, bh, x = 760, 150, (W - 760) // 2 - 16
    for n, (label, level, color) in enumerate((("CLAIMED", 1.0, GREEN), ("REAL", real, RED))):
        by = y + 520 + n * 250
        d.text((x, by - 70), label, font=_font(BOLD, 54), fill=WHITE)
        if n:  # the real figure depends on the car and the drive, so ask instead of inventing one
            d.text((x + bw, by - 88), "?", font=_font(BOLD, 86), fill=color, anchor="ra")
        d.rounded_rectangle([x, by, x + bw, by + bh], radius=32, outline=WHITE, width=12)
        d.rounded_rectangle([x + bw + 10, by + bh * 0.3, x + bw + 40, by + bh * 0.7], radius=8, fill=WHITE)
        d.rounded_rectangle([x + 24, by + 24, x + 24 + (bw - 48) * level, by + bh - 24], radius=20, fill=color)
    d.text((W // 2, H - 150), handle, font=_font(BOLD, 48), fill=TEAL, anchor="ma")
    im.convert("RGB").save(path, "JPEG", quality=92)
    return path
