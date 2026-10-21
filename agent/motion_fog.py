"""Animated "fog" format: glass fog, inside vs outside. A windshield fogs
up and a hand-wipe smears it; then a cross-section of the glass shows warm
humid air condensing on whichever side is warmer, and the fixes clear it.

Slides: 1 hook (the myth), 2 the myth's answer, 3 fog inside, 4 fog
outside; slide 3 and 4 may carry "chips", the fixes shown as tags."""

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .design import AMBER, BOLD, GREY, INK, MEDIUM, NAVY, TEAL, WHITE, _fit, clean
from .motion import (BOT, GREEN, H, RED, TOP, W, X0, XW, Words, _fade_text, _font, _glow, _hook_scene,
                     _pill, ease_out)

BLUE = (90, 170, 255)
GLASS = (160, 205, 235)
SHIELD = [(X0 + 100, 0), (X0 + XW - 100, 0), (X0 + XW, 360), (X0, 360)]  # relative to its top


def _fog_texture(w, h, seed=3, strength=215):
    rng = np.random.default_rng(seed)
    a = np.zeros((h, w))
    for cells, weight in ((6, 0.5), (14, 0.3), (40, 0.2)):
        small = Image.fromarray((rng.random((cells, cells * w // h + 1)) * 255).astype(np.uint8))
        a += np.asarray(small.resize((w, h), Image.BICUBIC), float) / 255 * weight
    a = np.clip(0.55 + (a - 0.5) * 1.2, 0, 1) * strength
    im = np.zeros((h, w, 4), np.uint8)
    im[..., :3] = (232, 238, 244)
    im[..., 3] = a.astype(np.uint8)
    return Image.fromarray(im, "RGBA")


class Windshield:
    """Front view: the road through the glass, fog on top of it."""

    def __init__(self, y, scale=1.0):
        self.y, self.w, self.h = y, X0 + XW, 360
        self.mask = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(self.mask).polygon(SHIELD, fill=255)
        self.fog = _fog_texture(self.w, self.h)

    def view(self, t):
        im = Image.new("RGB", (self.w, self.h))
        d = ImageDraw.Draw(im)
        for yy in range(self.h):  # dusk sky into road
            k = yy / self.h
            d.line([(0, yy), (self.w, yy)], fill=(int(30 + 40 * k), int(45 + 30 * k), int(80 - 20 * k)))
        cx = self.w // 2
        d.polygon([(cx - 30, 150), (cx + 30, 150), (cx + 330, self.h), (cx - 330, self.h)], fill=(52, 56, 64))
        for n in range(6):  # lane dashes rushing toward you
            p = ((t * 0.9 + n / 6) % 1) ** 2
            yy, ln = 150 + p * (self.h - 150), 6 + 40 * p
            d.rectangle([cx - 3 - 6 * p, yy, cx + 3 + 6 * p, yy + ln], fill=(230, 220, 160))
        return im

    def draw(self, frame, d, t, fog_level=1.0, wipe=None):
        """`wipe` = (sweep 0..1, recovery 0..1): a hand smear across the glass."""
        view = self.view(t).convert("RGBA")
        fog = self.fog
        if fog_level < 1:
            fog = fog.copy()
            fog.putalpha(fog.getchannel("A").point(lambda v: int(v * fog_level)))
        if wipe:
            sweep, rec = wipe
            m = Image.new("L", (self.w, self.h), 255)
            if sweep > 0:
                v = int(30 + 170 * ease_out(rec))  # it fogs back, streakier than before
                # a hand's wavy smear, drawn left to right
                n = max(2, int(40 * sweep))
                pts = [(120 + (self.w - 240) * k / 39, self.h * 0.52 + 46 * math.sin(k / 39 * 7))
                       for k in range(n)]
                ImageDraw.Draw(m).line(pts, fill=v, width=120, joint="curve")
                m = m.filter(ImageFilter.GaussianBlur(14))
            alpha = Image.fromarray((np.asarray(fog.getchannel("A"), float) * np.asarray(m, float) / 255)
                                    .astype(np.uint8))
            fog = fog.copy()
            fog.putalpha(alpha)
        view.alpha_composite(fog)
        frame.paste(view.convert("RGB"), (0, self.y), self.mask)
        pts = [(x, y + self.y) for x, y in SHIELD]
        d.line(pts + [pts[0]], fill=(*WHITE, 255), width=10, joint="curve")


class Section:
    """Side view of the glass: warm humid air on one side condenses into
    droplets on that face."""

    def __init__(self, y, seed=5):
        self.y, self.h, self.cx = y, 260, X0 + XW // 2
        rng = np.random.default_rng(seed)
        self.drops = [(self.y + 30 + rng.random() * (self.h - 60), 6 + rng.random() * 12, rng.random() * 0.5)
                      for _ in range(18)]

    def draw(self, d, t, warm, labels, grow=(0.7, 1.9), clear=None):
        """warm = "left" or "right"; labels = (left, right) side names;
        clear = (start, end) when the fix dries the glass."""
        cx, y, h = self.cx, self.y, self.h
        for side, name in zip((-1, 1), labels):
            hot = (side < 0) == (warm == "left")
            x = X0 if side < 0 else cx + 60
            state = "WARM + HUMID" if hot else "COLD"
            _pill(d, x, y - 70, f"{name}: {state}" if name else state, AMBER if hot else BLUE, INK, size=28)
        d.rounded_rectangle([cx - 26, y, cx + 26, y + h], radius=10, fill=(*GLASS, 210), outline=(*WHITE, 255),
                            width=4)
        d.text((cx, y + h + 16), "GLASS", font=_font(BOLD, 28), fill=(*GREY, 255), anchor="ma")
        sign = -1 if warm == "left" else 1
        dry = 1.0
        if clear:
            dry = 1 - ease_out((t - clear[0]) / (clear[1] - clear[0]))
        for n in range(3):  # humid air drifting toward the glass
            yy = y + 50 + n * 80
            far = X0 + 20 if sign < 0 else X0 + XW - 20
            near = cx + sign * 40
            pts = []
            for k in range(30):
                f = k / 29
                xx = far + (near - far) * f
                pts.append((xx, yy + 12 * math.sin(f * 9 - t * 6 + n)))
            d.line(pts, fill=(*AMBER, int(150 * dry)), width=5)
        for dy, r, delay in self.drops:
            p = ease_out((t - grow[0] - delay) / (grow[1] - grow[0])) * dry
            if p > 0:
                rr = r * p
                dx = cx + sign * (26 + rr)
                d.ellipse([dx - rr, dy - rr, dx + rr, dy + rr], fill=(220, 235, 250, 230))


def _chips(d, chips, y, t, start, gap=0.5, x=X0):
    for i, c in enumerate(chips):
        p = ease_out((t - start - i * gap) / 0.25)
        if p <= 0:
            continue
        f = _font(BOLD, 30)
        w = d.textlength(c.upper(), font=f) + 44
        if x + w > X0 + XW:
            break
        d.rounded_rectangle([x, y + 20 * (1 - p), x + w, y + 60 + 20 * (1 - p)], radius=30,
                            fill=(*GREEN, int(255 * p)))
        d.text((x + 22, y + 13 + 20 * (1 - p)), c.upper(), font=f, fill=(*INK, int(255 * p)))
        x += w + 16


def fog_scenes(post, handle):
    slides = post["slides"]
    hook, answer, inside, outside = slides[0], slides[1], slides[2], slides[3]
    vis_y = 960
    shield, section = Windshield(vis_y), Section(vis_y + 70)
    scenes = [_hook_scene(hook["heading"], "MYTH OR FACT?")]

    myth = Words(hook["heading"], TOP + 150, size=92)

    def myth_draw(frame, d, t):
        _pill(d, X0, TOP + 40, "MYTH", RED, WHITE, alpha=int(255 * ease_out(t / 0.2)), size=34)
        myth.draw(d, t, stagger=0.04)
        sweep = ease_out((t - 0.7) / 0.5)
        rec = ease_out((t - 1.6) / 1.0)
        shield.draw(frame, d, t, wipe=(sweep, rec))
        if t > 1.2:
            d.text((X0, vis_y + 380), "Wiped... and it's back.", font=_font(MEDIUM, 40),
                   fill=(*GREY, int(255 * ease_out((t - 1.2) / 0.3))))
        p = ease_out((t - 2.4) / 0.25)
        if p > 0:
            y0, y1 = myth.items[0][1] + 40, myth.bottom - 40
            d.line([(X0 - 10, y1), (X0 - 10 + (XW * 0.9) * p, y1 + (y0 - y1) * p)], fill=(*RED, 255), width=14)
    scenes.append((3.3, myth_draw, [("whoosh", 0), ("whoosh", 0.7), ("drain", 2.4)]))

    def text_scene(slide, badge, color, dur, visual, cues):
        heading = Words(slide["heading"], TOP + 150, size=88)

        def draw(frame, d, t):
            _pill(d, X0, TOP + 40, badge, color, INK, alpha=int(255 * ease_out(t / 0.2)), size=34)
            heading.draw(d, t)
            _fade_text(d, slide.get("body", ""), X0, heading.bottom + 24, t, 0.4, MEDIUM, GREY, size=40,
                       height=110)
            visual(frame, d, t)
        return dur, draw, cues

    scenes.append(text_scene(answer, "FACT", GREEN, 3.4,
                             lambda f, d, t: section.draw(d, t, "left", ("", "")),
                             [("whoosh", 0), ("pop", 0.9), ("pop", 1.2), ("pop", 1.5)]))
    for slide, warm, badge in ((inside, "right", "FOG INSIDE"), (outside, "left", "FOG OUTSIDE")):
        chips = slide.get("chips", [])

        def visual(f, d, t, warm=warm, chips=chips):
            section.draw(d, t, warm, ("OUTSIDE", "CABIN"), grow=(0.5, 1.4), clear=(2.6, 3.4))
            _chips(d, chips, vis_y + 390, t, 1.6)
        cues = [("whoosh", 0)] + [("pop", 1.6 + i * 0.5) for i in range(len(chips))] + [("ding", 2.8)]
        scenes.append(text_scene(slide, badge, TEAL, 4.3, visual, cues))
    return scenes


def fog_thumbnail(post, path, handle="@decodethedrive"):
    text = post.get("thumbnail_text") or "Why does my | glass fog up?"
    top, _, accent = text.partition("|")
    im = Image.new("RGBA", (W, H), (*NAVY, 255))
    im.alpha_composite(_glow(900, TEAL, 55), (-300, 900))
    d = ImageDraw.Draw(im)
    y = 250
    for part, color in ((top, WHITE), (accent, AMBER)):
        part = clean(part).upper()
        if part:
            f, lines, line_h = _fit(d, part, BOLD, W - 2 * X0, 520, 170, 90, spacing=1.05)
            for line in lines:
                d.text((W // 2, y), line, font=f, fill=color, anchor="ma")
                y += line_h
    frame = im.convert("RGB")
    shield = Windshield(max(y + 120, 1000))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    shield.draw(frame, ld, 0.3, wipe=(1.0, 0.0))
    _pill(ld, X0 + 160, shield.y + 400, "INSIDE OR OUTSIDE?", RED, WHITE, size=46)
    ld.text((W // 2, H - 210), handle, font=_font(BOLD, 48), fill=(*TEAL, 255), anchor="ma")
    out = frame.convert("RGBA")
    out.alpha_composite(layer)
    out.convert("RGB").save(path, "JPEG", quality=92)
    return path
