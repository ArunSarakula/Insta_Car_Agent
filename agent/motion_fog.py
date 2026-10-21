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


def _fog_texture(w, h, seed=3, strength=245):
    rng = np.random.default_rng(seed)
    a = np.zeros((h, w))
    for cells, weight in ((6, 0.5), (14, 0.3), (40, 0.2)):
        small = Image.fromarray((rng.random((cells, cells * w // h + 1)) * 255).astype(np.uint8))
        a += np.asarray(small.resize((w, h), Image.BICUBIC), float) / 255 * weight
    a = np.clip(0.8 + (a - 0.5) * 0.8, 0, 1) * strength
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
        """Daytime road seen through the glass, with a car ahead."""
        im = Image.new("RGB", (self.w, self.h))
        d = ImageDraw.Draw(im)
        hz = 140
        for yy in range(hz):
            k = yy / hz
            d.line([(0, yy), (self.w, yy)], fill=(int(110 + 60 * k), int(160 + 40 * k), int(220 + 20 * k)))
        d.rectangle([0, hz, self.w, self.h], fill=(70, 130, 70))
        for tx in (60, 150, self.w - 170, self.w - 80):  # trees on the verge
            d.ellipse([tx - 34, hz - 70, tx + 34, hz + 4], fill=(40, 100, 55))
            d.rectangle([tx - 5, hz - 4, tx + 5, hz + 16], fill=(80, 60, 40))
        cx = self.w // 2
        d.polygon([(cx - 40, hz), (cx + 40, hz), (cx + 380, self.h), (cx - 380, self.h)], fill=(70, 74, 82))
        for n in range(6):  # lane dashes rushing toward you
            p = ((t * 0.9 + n / 6) % 1) ** 2
            yy, ln = hz + p * (self.h - hz), 6 + 40 * p
            d.rectangle([cx - 3 - 6 * p, yy, cx + 3 + 6 * p, yy + ln], fill=(240, 240, 230))
        ax, ay = cx - 70, hz + 40  # car ahead
        d.rounded_rectangle([ax - 50, ay, ax + 50, ay + 56], radius=12, fill=(200, 200, 205))
        d.rounded_rectangle([ax - 36, ay - 22, ax + 36, ay + 4], radius=10, fill=(60, 70, 90))
        for lx in (ax - 42, ax + 30):
            d.rounded_rectangle([lx, ay + 14, lx + 12, ay + 26], radius=3, fill=(220, 40, 40))
        return im

    def draw(self, frame, d, t, fog_level=1.0, wipe=None):
        """`wipe` = (sweep 0..1, recovery 0..1): a hand smears across the
        glass. Pillars, mirror, dashboard and steering make it read as the
        view from the driver's seat."""
        view = self.view(t).convert("RGBA")
        fog = self.fog
        if fog_level < 1:
            fog = fog.copy()
            fog.putalpha(fog.getchannel("A").point(lambda v: int(v * fog_level)))
        hand = None
        if wipe:
            sweep, rec = wipe
            m = Image.new("L", (self.w, self.h), 255)
            if sweep > 0:
                v = int(20 + 215 * ease_out(rec))  # it fogs back, streakier than before
                n = max(2, int(40 * sweep))
                pts = [(140 + (self.w - 280) * k / 39, self.h * 0.5 + 40 * math.sin(k / 39 * 7))
                       for k in range(n)]
                ImageDraw.Draw(m).line(pts, fill=v, width=110, joint="curve")
                m = m.filter(ImageFilter.GaussianBlur(14))
                if sweep < 1:
                    hand = (pts[-1][0], pts[-1][1] + self.y)
            alpha = Image.fromarray((np.asarray(fog.getchannel("A"), float) * np.asarray(m, float) / 255)
                                    .astype(np.uint8))
            fog = fog.copy()
            fog.putalpha(alpha)
        view.alpha_composite(fog)
        frame.paste(view.convert("RGB"), (0, self.y), self.mask)
        pts = [(x, y + self.y) for x, y in SHIELD]
        cabin = (24, 27, 33)
        d.line(pts + [pts[0]], fill=(*cabin, 255), width=34, joint="curve")          # pillars and roof
        mx = (pts[0][0] + pts[1][0]) / 2
        d.rectangle([mx - 6, self.y - 4, mx + 6, self.y + 22], fill=(*cabin, 255))  # rear-view mirror
        d.rounded_rectangle([mx - 90, self.y + 18, mx + 90, self.y + 62], radius=14, fill=(*cabin, 255),
                            outline=(*GREY, 255), width=3)
        by = self.y + self.h
        d.rounded_rectangle([X0 - 40, by - 14, X0 + XW + 40, by + 70], radius=30, fill=(*cabin, 255))  # dashboard
        sx, sy, sr = X0 + XW - 190, by + 120, 150   # steering on the right, as in Indian cars
        d.arc([sx - sr, sy - sr, sx + sr, sy + sr], 200, 340, fill=(*(50, 54, 62), 255), width=30)
        _label = _font(BOLD, 26)
        d.text((X0, by + 22), "DRIVER'S VIEW", font=_label, fill=(*GREY, 255))
        if hand:  # a palm with fingers, wiping
            hx, hy = hand
            skin = (224, 172, 130, 255)
            d.ellipse([hx - 44, hy - 30, hx + 44, hy + 60], fill=skin)
            for k, (dx, ln) in enumerate(((-34, 50), (-12, 62), (10, 60), (31, 48))):
                d.rounded_rectangle([hx + dx - 10, hy - 20 - ln, hx + dx + 10, hy - 10], radius=10, fill=skin)
            d.rounded_rectangle([hx + 36, hy, hx + 74, hy + 20], radius=10, fill=skin)
            d.rectangle([hx - 30, hy + 55, hx + 30, hy + 120], fill=(60, 90, 160, 255))  # sleeve


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
            d.text((X0, vis_y - 80), "Wiped... and it's back.", font=_font(MEDIUM, 40),
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
            f, lines, line_h = _fit(d, part, BOLD, W - 2 * X0, 520, 140, 90, spacing=1.05)
            for line in lines:
                d.text((W // 2, y), line, font=f, fill=color, anchor="ma")
                y += line_h
    frame = im.convert("RGB")
    shield = Windshield(max(y + 120, 1000))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    shield.draw(frame, ld, 0.3, wipe=(1.0, 0.0))
    _pill(ld, X0 + 160, shield.y + 480, "INSIDE OR OUTSIDE?", RED, WHITE, size=46)
    ld.text((W // 2, H - 210), handle, font=_font(BOLD, 48), fill=(*TEAL, 255), anchor="ma")
    out = frame.convert("RGBA")
    out.alpha_composite(layer)
    out.convert("RGB").save(path, "JPEG", quality=92)
    return path
