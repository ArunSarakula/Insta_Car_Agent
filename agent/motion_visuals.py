"""Animated explainer reels with a topic visual under the text: a clutch
pedal, a powertrain, a speedometer, a wheel, a charging curve, a radar.

Every format takes the usual slides: slide 1 is the hook, each later slide
gets its own scene, and the visual changes with it (scene i draws step i)."""

import math

import numpy as np
from PIL import Image, ImageDraw

from .design import AMBER, BOLD, GREY, INK, MEDIUM, NAVY, TEAL, WHITE, _fit, clean
from .motion import (BOT, GREEN, H, RED, TOP, W, X0, XW, Words, _ev_car, _fade_text, _font, _glow,
                     _hook_scene, _pill, ease_out)
from .motion_fog import _chips

VY = 990            # top of the visual
CX = X0 + XW // 2   # its centre line
BLUE = (90, 170, 255)
DIM = (70, 82, 100)


def _a(color, alpha=255):
    return (*color, int(alpha))


def _label(d, x, y, text, color=GREY, size=30, anchor="la", alpha=255):
    d.text((x, y), text, font=_font(BOLD, size), fill=_a(color, alpha), anchor=anchor)


def _bar(d, x, y, w, level, color, label, alpha=255):
    _label(d, x, y - 44, label, alpha=alpha)
    d.rounded_rectangle([x, y, x + w, y + 34], radius=17, fill=_a(DIM, alpha * 0.6))
    if level > 0.01:
        d.rounded_rectangle([x, y, x + w * min(1, level), y + 34], radius=17, fill=_a(color, alpha))


def _step(steps, i):
    return steps[min(i, len(steps) - 1)]


# ---- clutch ----------------------------------------------------------------

def clutch(frame, d, t, i):
    """Pedal on the left, flywheel and clutch plate on the right. Slip
    (plate turning slower than the engine) heats it and adds wear."""
    press, slip, wear, foot = _step([(0.12, 0.35, (0.0, 0.35), "rest"), (0.55, 0.7, (0.35, 0.65), "rest"),
                                     (0.0, 0.0, (0.65, 0.65), "dead"), (0.0, 0.0, (0.65, 0.65), "dead")], i)
    if i == 2:  # foot moves off to the dead pedal
        mv = ease_out((t - 0.8) / 0.5)
        press = 0.12 * (1 - mv)
    px, py = X0 + 150, VY + 10
    ang = math.radians(70 - 35 * press)
    ex, ey = px + 260 * math.cos(ang), py + 260 * math.sin(ang)
    d.line([(px, py), (ex, ey)], fill=_a(GREY), width=18)
    d.ellipse([px - 16, py - 16, px + 16, py + 16], fill=_a(WHITE))
    d.rounded_rectangle([ex - 60, ey - 18, ex + 60, ey + 18], radius=10, fill=_a(WHITE))
    _label(d, ex + 80, ey - 12, "CLUTCH", size=26)
    dead = (X0, VY + 330)
    d.rounded_rectangle([dead[0], dead[1], dead[0] + 120, dead[1] + 26], radius=8, fill=_a(DIM))
    _label(d, dead[0], dead[1] + 34, "DEAD PEDAL", size=24)
    sx, sy = ex - 80, ey - 62  # shoe on the pedal pad
    if i >= 2:
        mv = ease_out((t - 0.8) / 0.5) if i == 2 else 1.0
        sx, sy = sx + (dead[0] - 20 - sx) * mv, sy + (dead[1] - 46 - sy) * mv
    d.rounded_rectangle([sx, sy, sx + 160, sy + 44], radius=22, fill=_a(AMBER))  # shoe
    # flywheel + plate
    fx, fy, r = X0 + 540, VY + 130, 120
    engine = t * 9
    plate = engine * (1 - slip * ease_out((t - 0.4) / 0.6))
    heat = slip * ease_out((t - 0.6) / 0.8)
    for cx, rot, name, col in ((fx, engine, "ENGINE", GREY), (fx + 170, plate, "PLATE", WHITE)):
        glow = tuple(int(c + (RED[k] - c) * heat) for k, c in enumerate(col)) if name == "PLATE" else col
        d.ellipse([cx - 40, fy - r, cx + 40, fy + r], fill=_a(DIM), outline=_a(glow), width=8)
        my = fy + r * 0.8 * math.sin(rot)
        d.ellipse([cx - 12, my - 12, cx + 12, my + 12], fill=_a(glow))
        _label(d, cx, fy + r + 14, name, size=24, anchor="ma")
    if heat > 0.2:
        _label(d, fx + 85, fy - r - 50, "SLIPPING", RED, 30, "ma", 255 * min(1, heat * 2))
    lo, hi = wear
    _bar(d, X0 + 420, VY + 340, 420, lo + (hi - lo) * ease_out((t - 0.6) / 1.6), RED, "PLATE WEAR")


# ---- hybrid ----------------------------------------------------------------

def _flow(d, pts, t, color, n=7, speed=0.8, r=9, alpha=255):
    segs = [(pts[k], pts[k + 1]) for k in range(len(pts) - 1)]
    lens = [math.dist(a, b) for a, b in segs]
    total = sum(lens)
    d.line(pts, fill=_a(color, alpha * 0.25), width=8)
    for k in range(n):
        s = ((t * speed + k / n) % 1) * total
        for (a, b), ln in zip(segs, lens):
            if s <= ln:
                f = s / ln
                x, y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
                d.ellipse([x - r, y - r, x + r, y + r], fill=_a(color, alpha))
                break
            s -= ln


def hybrid(frame, d, t, i):
    if i >= 2:  # mileage gap bars, then city vs highway
        city = i == 2 or t < 1.8
        _label(d, X0, VY, "CITY TRAFFIC" if city else "HIGHWAY", WHITE, 40)
        strong, mild = (0.9, 0.3) if city else (0.45, 0.32)
        g = ease_out((t - 0.4) / 0.8) if i == 2 else 1.0
        _bar(d, X0, VY + 130, XW, strong * g, TEAL, "STRONG HYBRID: MILEAGE GAIN")
        _bar(d, X0, VY + 260, XW, mild * g, AMBER, "MILD HYBRID: MILEAGE GAIN")
        return
    strong = i == 0
    eng = (X0 + 130, VY + 70)
    bat = (X0 + 130, VY + 260)
    mot = (X0 + 450, VY + 260)
    whl = (X0 + 730, VY + 165)
    for (cx, cy), name, on, col in ((eng, "ENGINE", not strong, AMBER), (bat, "BATTERY", True, GREEN)):
        d.rounded_rectangle([cx - 120, cy - 55, cx + 120, cy + 55], radius=18, fill=_a(col if on else DIM))
        _label(d, cx, cy, name + ("" if on else ": OFF"), INK if on else GREY, 32, "mm")
    mr = 70 if strong else 46
    d.ellipse([mot[0] - mr, mot[1] - mr, mot[0] + mr, mot[1] + mr], fill=_a(TEAL))
    _label(d, mot[0], mot[1], "MOTOR", INK, 26 if strong else 20, "mm")
    d.ellipse([whl[0] - 95, whl[1] - 95, whl[0] + 95, whl[1] + 95], fill=_a(INK), outline=_a(GREY), width=24)
    _label(d, whl[0], whl[1] + 120, "WHEELS", GREY, 28, "ma")
    if strong:
        _flow(d, [(bat[0] + 120, bat[1]), (mot[0] - mr, mot[1])], t, TEAL, n=5)
        _flow(d, [(mot[0] + mr, mot[1]), (whl[0] - 95, whl[1])], t, TEAL, n=5)
        _pill(d, X0, VY + 350, "ELECTRIC ONLY AT LOW SPEED", TEAL, INK, size=30)
    else:
        _flow(d, [(eng[0] + 120, eng[1]), (whl[0] - 95, whl[1])], t, AMBER, n=8)
        _flow(d, [(bat[0] + 120, bat[1]), (mot[0] - mr, mot[1])], t, TEAL, n=3, r=6, speed=0.5)
        _flow(d, [(mot[0] + mr * 0.7, mot[1] - mr * 0.7), (whl[0] - 80, whl[1] + 40)], t, TEAL, n=2, r=6,
              speed=0.5)
        _pill(d, X0, VY + 350, "MOTOR ONLY ASSISTS THE ENGINE", AMBER, INK, size=30)


# ---- highway mileage -------------------------------------------------------

def _speedo(d, cx, cy, r, speed, throttle):
    for k in range(0, 15):
        a = math.radians(180 + k * 180 / 14)
        x1, y1 = cx + r * math.cos(a), cy + r * math.sin(a)
        x2, y2 = cx + (r - (30 if k % 2 == 0 else 16)) * math.cos(a), cy + (r - (30 if k % 2 == 0 else 16)) * math.sin(a)
        d.line([(x1, y1), (x2, y2)], fill=_a(GREY), width=6)
        if k % 2 == 0:
            tx, ty = cx + (r - 70) * math.cos(a), cy + (r - 70) * math.sin(a)
            _label(d, tx, ty, str(k * 10), GREY, 24, "mm")
    for lo, hi in ((90, 100),):  # the sweet band
        d.arc([cx - r, cy - r, cx + r, cy + r], 180 + lo * 180 / 140, 180 + hi * 180 / 140, fill=_a(GREEN),
              width=16)
    a = math.radians(180 + speed * 180 / 140)
    d.line([(cx, cy), (cx + (r - 40) * math.cos(a), cy + (r - 40) * math.sin(a))], fill=_a(RED), width=10)
    d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], fill=_a(WHITE))
    _label(d, cx, cy + 34, f"{round(speed)} km/h", WHITE, 40, "ma")


def mileage(frame, d, t, i):
    cx, cy, r = X0 + 230, VY + 250, 230
    if i == 0:
        speed, throttle = 60 + 40 * ease_out(t / 2.0), 0.35
    elif i == 1:
        speed, throttle = 100 - 10 * ease_out((t - 0.3) / 2.2), 0.0
    elif i == 2:
        ph = (math.sin(t * 2.2) + 1) / 2
        speed, throttle = 90 + 10 * ph, 0.35 if math.cos(t * 2.2) > 0 else 0.0
    else:
        speed, throttle = 95, 0.15
    if i < 3:
        _speedo(d, cx, cy, r, speed, throttle)
        _bar(d, X0 + 520, VY + 120, 320, throttle / 0.5, AMBER, "ACCELERATOR")
        coasting = throttle == 0
        _pill(d, X0 + 520, VY + 220, "COASTING: IN GEAR" if coasting else "LIGHT PRESS",
              GREEN if coasting else AMBER, INK, size=28)
        if i == 2:
            _pill(d, X0 + 520, VY + 310, "WORKS ON EVs TOO", TEAL, INK, size=28)
    else:
        _chips(d, ["Clear road", "Safe gap", "Speed limit"], VY + 40, t, 0.5)
        _pill(d, X0, VY + 170, "NOT IN DENSE TRAFFIC", RED, WHITE, size=32)
        _pill(d, X0, VY + 260, "NEVER COAST IN NEUTRAL", RED, WHITE, size=32)


# ---- wheel balancing -------------------------------------------------------

def _wheel(d, cx, cy, r, rot, weight=True, wobble=0.0, t=0.0):
    cx += wobble * 14 * math.sin(t * 40)
    cy += wobble * 8 * math.cos(t * 37)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_a(INK), outline=_a((60, 64, 72)), width=40)
    d.ellipse([cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62], fill=_a(GREY))
    for k in range(5):
        a = rot + k * 2 * math.pi / 5
        d.line([(cx, cy), (cx + r * 0.6 * math.cos(a), cy + r * 0.6 * math.sin(a))], fill=_a(DIM), width=18)
    d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=_a(DIM))
    if weight:
        a = rot + 0.6
        wx, wy = cx + r * 0.66 * math.cos(a), cy + r * 0.66 * math.sin(a)
        d.rounded_rectangle([wx - 16, wy - 16, wx + 16, wy + 16], radius=6, fill=_a(AMBER))
    if wobble > 0.1:
        for s in (-1, 1):
            for k in range(3):
                x = cx + s * (r + 30 + k * 22)
                d.arc([x - 20, cy - 40 - k * 12, x + 20, cy + 40 + k * 12], 90 + s * 90 - 50, 90 + s * 90 + 50,
                      fill=_a(RED, 200), width=6)


def wheel(frame, d, t, i):
    cx, cy, r = X0 + 210, VY + 190, 175
    rot = t * 6
    if i == 0:
        km = int(5000 * ease_out(t / 2.4) // 10 * 10)
        _wheel(d, cx, cy, r, rot)
        d.rounded_rectangle([X0 + 470, VY + 90, X0 + 840, VY + 200], radius=18, fill=_a(INK),
                            outline=_a(TEAL), width=4)
        _label(d, X0 + 655, VY + 145, f"{km:,} km", TEAL, 56, "mm")
        if t > 2.4:
            _pill(d, X0 + 470, VY + 240, "BALANCE NOW", GREEN, INK, size=32)
    elif i == 1:
        hit = 1.0
        bump = ease_out((t - 0.5) / 0.3) * (1 - ease_out((t - 0.8) / 0.3))
        dropped = t > 0.85
        _wheel(d, cx, cy - 30 * bump, r, rot, weight=not dropped, wobble=ease_out((t - 1.0) / 0.6), t=t)
        d.ellipse([cx - 120, cy + r + 4, cx + 120, cy + r + 40], fill=_a((30, 32, 38)))
        _label(d, cx, cy + r + 50, "POTHOLE", GREY, 26, "ma")
        if dropped:
            fy = cy + 80 + 120 * ease_out((t - 0.85) / 0.4)
            d.rounded_rectangle([cx + 120, fy, cx + 150, fy + 30], radius=6, fill=_a(AMBER))
            _label(d, X0 + 470, VY + 120, "WEIGHT KNOCKED LOOSE", AMBER, 30)
        _bar(d, X0 + 470, VY + 260, 370, 0.7 * ease_out((t - 1.2) / 1.2) * hit, RED, "UNEVEN TYRE WEAR")
    elif i == 2:
        sw_x, sw_y, sr = X0 + 200, VY + 180, 150
        sh = 10 * math.sin(t * 45)
        d.ellipse([sw_x - sr + sh, sw_y - sr, sw_x + sr + sh, sw_y + sr], outline=_a(WHITE), width=26)
        d.line([(sw_x - sr + sh, sw_y), (sw_x + sr + sh, sw_y)], fill=_a(WHITE), width=22)
        d.line([(sw_x + sh, sw_y), (sw_x + sh, sw_y + sr)], fill=_a(WHITE), width=22)
        _label(d, sw_x, sw_y + sr + 30, "STEERING SHAKE", RED, 28, "ma")
        for n, c in enumerate(["80-100 km/h", "Patchy wear", "Hum"]):
            _chips(d, [c], VY + 60 + n * 90, t, 0.8 + n * 0.5, x=X0 + 440)
    else:
        _wheel(d, cx, cy, r, rot * (1 - ease_out(t / 1.5)), wobble=0.6 * (1 - ease_out(t / 1.5)), t=t)
        _pill(d, X0 + 450, VY + 120, "CHECK TYRE + RIM", RED, WHITE, size=34)
        _pill(d, X0 + 450, VY + 220, "BEFORE THE HIGHWAY", AMBER, INK, size=30)


# ---- DC fast charging ------------------------------------------------------

def _curve(x):  # charging power vs battery level (shape only, no figures)
    return 1.0 if x < 0.5 else (1.0 - 0.6 * (x - 0.5) / 0.3 if x < 0.8 else 0.4 - 0.32 * (x - 0.8) / 0.2)


def charging(frame, d, t, i):
    if i == 0:  # charger -> BMS -> cells
        c, b, cells = (X0 + 60, VY + 170), (CX, VY + 170), (X0 + XW - 110, VY + 170)
        d.rounded_rectangle([c[0] - 50, c[1] - 90, c[0] + 50, c[1] + 90], radius=16, fill=_a(DIM))
        _label(d, c[0], c[1] + 105, "DC CHARGER", GREY, 24, "ma")
        hot = t > 2.0
        _flow(d, [(c[0] + 50, c[1]), (b[0] - 80, b[1])], t, AMBER, n=8, speed=1.2)
        _flow(d, [(b[0] + 80, b[1]), (cells[0] - 90, cells[1])], t, AMBER, n=3 if hot else 8, speed=1.2,
              r=6 if hot else 9)
        d.polygon([(b[0], b[1] - 100), (b[0] + 80, b[1] - 60), (b[0] + 70, b[1] + 60), (b[0], b[1] + 100),
                   (b[0] - 70, b[1] + 60), (b[0] - 80, b[1] - 60)], fill=_a(TEAL))
        _label(d, b[0], b[1] - 20, "BMS", INK, 44, "ma")
        d.rounded_rectangle([cells[0] - 90, cells[1] - 70, cells[0] + 90, cells[1] + 70], radius=14,
                            fill=_a(GREEN))
        _label(d, cells[0], cells[1] - 16, "CELLS", INK, 30, "ma")
        if hot:
            _pill(d, X0, VY + 320, "HOT OR NEARLY FULL: POWER CUT", RED, WHITE, size=30)
        return
    if i == 1:
        gx, gy, gw, gh = X0 + 40, VY + 20, XW - 60, 290
        d.line([(gx, gy), (gx, gy + gh), (gx + gw, gy + gh)], fill=_a(GREY), width=5)
        _label(d, gx, gy - 44, "CHARGING SPEED", GREY, 26)
        _label(d, gx, gy + gh + 14, "BATTERY 0% → 100%", GREY, 26)
        prog = ease_out(t / 2.6)
        pts = [(gx + gw * x / 100, gy + gh - gh * 0.8 * _curve(x / 100)) for x in range(0, int(100 * prog) + 1)]
        if len(pts) > 1:
            d.line(pts, fill=_a(TEAL), width=10)
            x, y = pts[-1]
            d.ellipse([x - 14, y - 14, x + 14, y + 14], fill=_a(WHITE))
        mx = gx + gw * 0.8
        for yy in range(int(gy), int(gy + gh), 24):
            d.line([(mx, yy), (mx, yy + 12)], fill=_a(AMBER), width=4)
        _label(d, mx, gy - 44, "80%", AMBER, 28, "ma")
        if prog > 0.8:
            _pill(d, X0 + 300, VY + 150, "SLOWED ON PURPOSE", AMBER, INK, size=28)
        return
    if i == 2:
        _chips(d, ["Daily DC to 100%", "Peak heat"], VY + 60, t, 0.5)
        _chips(d, ["Right after hard driving"], VY + 150, t, 1.5)
        _bar(d, X0, VY + 300, XW, 0.6 * ease_out((t - 1.6) / 1.2), RED, "EXTRA BATTERY WEAR")
        return
    _chips(d, ["AC at home", "DC on trips"], VY + 40, t, 0.4)
    _chips(d, ["Stop near 80%"], VY + 130, t, 1.4)
    lvl = 0.8 * ease_out((t - 1.6) / 1.0)
    d.rounded_rectangle([X0, VY + 230, X0 + 600, VY + 360], radius=26, outline=_a(WHITE), width=10)
    d.rounded_rectangle([X0 + 606, VY + 270, X0 + 630, VY + 320], radius=6, fill=_a(WHITE))
    if lvl > 0.02:
        d.rounded_rectangle([X0 + 18, VY + 248, X0 + 18 + 564 * lvl, VY + 342], radius=16, fill=_a(GREEN))
    _label(d, X0 + 660, VY + 270, f"{round(lvl * 100)}%", GREEN, 56)


# ---- ADAS ------------------------------------------------------------------

def _car_top(d, cx, cy, color, w=90, h=160):
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=24, fill=_a(color))
    d.rounded_rectangle([cx - w / 2 + 12, cy - h / 2 + 26, cx + w / 2 - 12, cy - h / 2 + 62], radius=8,
                        fill=_a(NAVY))


def adas(frame, d, t, i):
    rx0, rx1, ry0, ry1 = X0 + 140, X0 + XW - 140, VY - 20, VY + 330
    d.rectangle([rx0, ry0, rx1, ry1], fill=_a((44, 48, 56)))
    fade = 0.25 if i == 1 else 1.0
    speed = 1.0 if i != 2 else max(0.0, 1 - ease_out((t - 1.0) / 0.6))
    mid = (rx0 + rx1) / 2
    off = (t * 420 * speed) % 80 if i != 2 else (min(t, 1.0) * 420 + 0) % 80
    for x in (rx0 + 10, rx1 - 10):
        d.line([(x, ry0), (x, ry1)], fill=_a(WHITE, 220 * fade), width=8)
    y = ry0 - 80 + off
    while y < ry1:
        d.line([(mid, max(ry0, y)), (mid, min(ry1, y + 40))], fill=_a(WHITE, 220 * fade), width=8)
        y += 80
    me = ((rx0 + mid) / 2, ry1 - 100)
    cone_col = RED if (i == 2 and t > 0.8) or (i == 1 and t > 1.2) else TEAL
    d.polygon([(me[0] - 30, me[1] - 80), (me[0] + 30, me[1] - 80), (me[0] + 110, ry0 + 20),
               (me[0] - 110, ry0 + 20)], fill=_a(cone_col, 70))
    _car_top(d, *me, TEAL)
    if i == 0:
        _car_top(d, me[0], ry0 + 90 + 10 * math.sin(t * 2), GREY)
        _chips(d, ["Adaptive cruise", "Lane keep"], ry1 + 16, t, 0.6)
    elif i == 1:
        bx = rx1 - 40 - (rx1 - me[0] - 20) * ease_out((t - 0.6) / 0.8)
        d.rounded_rectangle([bx - 22, ry0 + 120, bx + 22, ry0 + 200], radius=14, fill=_a(AMBER))
        _label(d, bx, ry0 + 90, "BIKE", AMBER, 26, "ma")
        _chips(d, ["Faded lines", "Cut-ins", "City traffic"], ry1 + 16, t, 0.8)
    elif i == 2:
        oy = ry0 + 40 + 90 * ease_out(t / 1.0)
        d.rounded_rectangle([me[0] - 45, oy, me[0] + 45, oy + 70], radius=16, fill=_a(RED))
        if t > 1.0:
            _pill(d, rx0 - 60, ry1 + 16, "AUTO BRAKE", RED, WHITE, size=40)
    else:
        _chips(d, ["AEB on", "Lane keep off in city", "Hands on"], ry1 + 16, t, 0.4)


VISUALS = {
    "clutch": (clutch, ["THE HABIT", "ALSO BAD", "MY RULE", "THE PAYOFF"],
               [[("drain", 0.9)], [("drain", 0.9)], [("ding", 1.3)], [("ding", 0.5)]], 1),
    "hybrid": (hybrid, ["STRONG HYBRID", "MILD HYBRID", "MILEAGE", "WHICH ONE?"],
               [[("pop", 0.6)], [("pop", 0.6)], [("ding", 1.2)], [("whoosh", 1.8)]], 0),
    "mileage": (mileage, ["STEP 1", "STEP 2", "REPEAT", "SAFETY FIRST"],
                [[("pop", 1.8)], [("drain", 0.6)], [("pop", 1.0)], [("ding", 0.6)]], 2),
    "wheel": (wheel, ["MY RULE", "WHY", "WARNING SIGNS", "SAFETY"],
              [[("ding", 2.4)], [("hit", 0.55), ("drain", 1.0)], [("pop", 0.8)], [("hit", 0.3)]], 1),
    "charging": (charging, ["THE BOUNCER", "THE SLOW 20%", "WHAT WEARS IT", "THE RULE"],
                 [[("drain", 2.0)], [("pop", 2.1)], [("drain", 1.6)], [("ding", 2.4)]], 1),
    "adas": (adas, ["SHINES", "STRUGGLES", "THE REAL HERO", "SMART SETUP"],
             [[("pop", 0.6)], [("whoosh", 0.6)], [("hit", 1.0)], [("ding", 0.6)]], 2),
}


def visual_scenes(post, handle):
    visual, badges, cues, _ = VISUALS[post["reel_style"]]
    slides = post["slides"]
    scenes = [_hook_scene(slides[0]["heading"], post.get("hook_tag", ""))]
    for i, slide in enumerate(slides[1:]):
        heading = Words(slide["heading"], TOP + 150, size=86)
        badge = badges[min(i, len(badges) - 1)]

        def draw(frame, d, t, heading=heading, slide=slide, badge=badge, i=i):
            _pill(d, X0, TOP + 40, badge, TEAL, INK, alpha=int(255 * ease_out(t / 0.2)), size=34)
            heading.draw(d, t)
            _fade_text(d, slide.get("body", ""), X0, heading.bottom + 22, t, 0.4, MEDIUM, GREY, size=40,
                       height=VY - heading.bottom - 70)
            visual(frame, d, t, i)
        scenes.append((3.6, draw, [("whoosh", 0)] + cues[min(i, len(cues) - 1)]))
    return scenes


def visual_thumbnail(post, path, handle="@decodethedrive"):
    visual, _, _, step = VISUALS[post["reel_style"]]
    text = post.get("thumbnail_text") or post["slides"][0]["heading"]
    top, _, accent = text.partition("|")
    im = Image.new("RGBA", (W, H), (*NAVY, 255))
    im.alpha_composite(_glow(900, TEAL, 55), (-300, 900))
    d = ImageDraw.Draw(im)
    parts = [(clean(p).upper(), c) for p, c in ((top, WHITE), (accent, AMBER)) if clean(p)]
    for size in range(160, 70, -8):
        layouts = [(_fit(d, p, BOLD, W - 2 * X0, 2000, size, size, spacing=1.04), c) for p, c in parts]
        if 200 + sum(len(l[1]) * l[2] for l, _ in layouts) <= VY - 60:
            break
    y = 200
    for (f, lines, line_h), color in layouts:
        for line in lines:
            d.text((W // 2, y), line, font=f, fill=color, anchor="ma")
            y += line_h
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    visual(im, ImageDraw.Draw(layer), 2.5, step)
    im.alpha_composite(layer)
    ImageDraw.Draw(im).text((W // 2, H - 200), handle, font=_font(BOLD, 48), fill=TEAL, anchor="ma")
    im.convert("RGB").save(path, "JPEG", quality=92)
    return path
