"""Animated explainer reels with a topic visual under the text: a clutch
pedal, a powertrain, a speedometer, a wheel, a charging curve, a radar.

Every format takes the usual slides: slide 1 is the hook, each later slide
gets its own scene, and the visual changes with it (scene i draws step i)."""

import math

import numpy as np
from PIL import Image, ImageDraw

from .design import AMBER, BOLD, GREY, INK, MEDIUM, NAVY, TEAL, WHITE, _fit, clean
from .motion import (BOT, GREEN, H, RED, TOP, W, X0, XW, Words, _ev_car, _fade_text, _font, _glow, _pill,
                     ease_out)
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

def _flywheel(d, cx, cy, r, rot, label):
    """The engine's flywheel: a steel disc with a toothed ring gear and bolts."""
    for k in range(36):  # ring gear teeth
        a = rot + k * math.pi / 18
        d.line([(cx + (r - 4) * math.cos(a), cy + (r - 4) * math.sin(a)),
                (cx + (r + 10) * math.cos(a), cy + (r + 10) * math.sin(a))], fill=_a((150, 158, 170)), width=7)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_a((120, 128, 140)), outline=_a((90, 96, 108)), width=6)
    d.ellipse([cx - r * 0.72, cy - r * 0.72, cx + r * 0.72, cy + r * 0.72], fill=_a((160, 168, 180)))
    for k in range(6):  # bolts; one marked so the spin is visible
        a = rot + k * math.pi / 3
        bx, by = cx + r * 0.36 * math.cos(a), cy + r * 0.36 * math.sin(a)
        d.ellipse([bx - 9, by - 9, bx + 9, by + 9], fill=_a(AMBER if k == 0 else (70, 76, 88)))
    d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=_a((70, 76, 88)))
    _label(d, cx, cy + r + 22, label, GREY, 24, "ma")


def _clutch_plate(d, cx, cy, r, rot, label, heat=0.0):
    """The clutch plate: friction lining round the edge, damper springs and
    a splined hub. Heat turns the lining red."""
    if heat > 0.2:
        d.ellipse([cx - r - 20, cy - r - 20, cx + r + 20, cy + r + 20], fill=_a(RED, 80 * heat))
    lining = tuple(int((175, 130, 90)[k] + (RED[k] - (175, 130, 90)[k]) * heat) for k in range(3))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_a(lining))
    for k in range(16):  # grooves in the lining
        a = rot + k * math.pi / 8
        d.line([(cx + r * 0.68 * math.cos(a), cy + r * 0.68 * math.sin(a)),
                (cx + r * math.cos(a), cy + r * math.sin(a))], fill=_a((110, 80, 55)), width=4)
    d.ellipse([cx - r * 0.66, cy - r * 0.66, cx + r * 0.66, cy + r * 0.66], fill=_a((150, 158, 170)))
    for k in range(6):  # damper springs
        a = rot + k * math.pi / 3 + 0.5
        sx, sy = cx + r * 0.42 * math.cos(a), cy + r * 0.42 * math.sin(a)
        d.ellipse([sx - 12, sy - 12, sx + 12, sy + 12], fill=_a(AMBER if k == 0 else (90, 96, 108)))
    d.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=_a((70, 76, 88)))
    for k in range(8):  # splines
        a = rot + k * math.pi / 4
        d.line([(cx, cy), (cx + 18 * math.cos(a), cy + 18 * math.sin(a))], fill=_a((160, 168, 180)), width=3)
    _label(d, cx, cy + r + 22, label, GREY, 24, "ma")


def clutch(frame, d, t, i):
    """Left: the pedals as the driver sees them, foot on the clutch or the
    dead pedal. Right: engine flywheel and clutch plate spinning; when the
    plate lags behind (slip) it heats up and wears."""
    # 0 foot resting: partly pressed, the plate slips and wears
    # 1 pedal held down through a turn: plate pulled clear, it turns with the wheels
    #   while the engine spins on its own (no rubbing, but no engine control)
    # 2/3 foot off: plate clamped to the flywheel, both spin together
    press, slip, wear = _step([(0.25, 0.4, (0.0, 0.35)), (1.0, 0.45, (0.35, 0.35)),
                               (0.0, 0.0, (0.35, 0.35)), (0.0, 0.0, (0.35, 0.35))], i)
    move = ease_out((t - 0.8) / 0.5) if i == 2 else (1.0 if i == 3 else 0.0)
    press *= 1 - move
    # footwell
    fx0, fy0 = X0, VY - 10
    d.rounded_rectangle([fx0, fy0, fx0 + 400, fy0 + 380], radius=24, fill=_a((30, 34, 42)))
    pedals = [("DEAD\nPEDAL", fx0 + 20, 70, 150), ("CLUTCH", fx0 + 112, 80, 110),
              ("BRAKE", fx0 + 210, 90, 110), ("ACCEL", fx0 + 320, 48, 150)]
    for name, x, w, h in pedals:
        dy = 50 * press if name == "CLUTCH" else 0
        top = fy0 + 120 + dy
        if name != "DEAD\nPEDAL":
            d.line([(x + w / 2, fy0 + 20), (x + w / 2, top)], fill=_a(DIM), width=10)  # pedal arm
        d.rounded_rectangle([x, top, x + w, top + h], radius=14,
                            fill=_a(WHITE if name == "CLUTCH" else ((60, 66, 78) if "DEAD" in name else GREY)))
        for n, line in enumerate(name.split("\n")):
            _label(d, x + w / 2, fy0 + 290 + n * 28 + (0 if name != "CLUTCH" else 0), line,
                   AMBER if name == "CLUTCH" else GREY, 22, "ma")
    # the left foot, a shoe sole seen from above
    cx_c, cy_c = fx0 + 152, fy0 + 175 + 50 * press
    cx_d, cy_d = fx0 + 55, fy0 + 195
    sx, sy = cx_c + (cx_d - cx_c) * move, cy_c + (cy_d - cy_c) * move
    d.rounded_rectangle([sx - 34, sy - 64, sx + 34, sy + 64], radius=34, fill=_a(AMBER, 235))
    _label(d, sx, sy - 14, "FOOT", INK, 22, "ma")
    # flywheel and plate, face-on
    engine = t * 7
    lag = slip * ease_out((t - 0.3) / 0.6)
    plate = engine * (1 - lag)
    heat = lag * ease_out((t - 0.6) / 0.8) if i == 0 else 0.0
    _flywheel(d, X0 + 530, VY + 140, 96, engine, "ENGINE FLYWHEEL")
    _clutch_plate(d, X0 + 760, VY + 140, 100, plate, "CLUTCH PLATE", heat)
    if heat > 0.2:
        _label(d, X0 + 760, VY - 20, "SLIPPING!", RED, 32, "ma", 255 * min(1, heat * 2))
    if i == 0:  # riding the clutch: wear climbs
        _bar(d, X0 + 440, VY + 340, 420, wear[0] + (wear[1] - wear[0]) * ease_out((t - 0.6) / 1.6), RED,
             "PLATE WEAR")
    elif i == 1:  # held down: plate spins down, no engine braking, release bearing works
        if t > 0.8:
            _label(d, X0 + 645, VY - 20, "DISENGAGED: CAR COASTS", AMBER, 28, "ma")
        _bar(d, X0 + 440, VY + 340, 420, 0.4 * ease_out((t - 0.8) / 1.6), AMBER, "RELEASE BEARING WEAR")
    elif i == 2:  # foot off: no slip, the bar turns green and stops
        g = ease_out((t - 1.3) / 0.4)
        col = tuple(int(RED[k] + (GREEN[k] - RED[k]) * g) for k in range(3))
        _bar(d, X0 + 440, VY + 340, 420, wear[1], col, "WEAR STOPPED" if g > 0.5 else "PLATE WEAR")
        if g > 0.5:
            _label(d, X0 + 645, VY - 20, "NO SLIP: BOTH SPIN TOGETHER", GREEN, 26, "ma")
    else:  # the payoff: a long clutch life
        _bar(d, X0 + 440, VY + 340, 420, 0.3 + 0.6 * ease_out((t - 0.4) / 1.2), GREEN, "CLUTCH LIFE")
        _label(d, X0 + 645, VY - 20, "LASTS LONGER", GREEN, 30, "ma")


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

def _car_top(d, cx, cy, color, L=190, Wd=100, brake=False):
    """A car seen from above, pointing right: wheels, glass, mirrors, lights."""
    x0, x1, y0, y1 = cx - L / 2, cx + L / 2, cy - Wd / 2, cy + Wd / 2
    for wx in (x0 + 30, x1 - 58):  # tyres poking out
        d.rounded_rectangle([wx, y0 - 9, wx + 30, y0 + 8], radius=5, fill=_a(INK))
        d.rounded_rectangle([wx, y1 - 8, wx + 30, y1 + 9], radius=5, fill=_a(INK))
    d.rounded_rectangle([x0, y0, x1, y1], radius=30, fill=_a(color))
    dark = tuple(max(0, c - 45) for c in color)
    d.rounded_rectangle([x0 + 62, y0 + 12, x1 - 62, y1 - 12], radius=14, fill=_a(dark))  # roof
    d.polygon([(x1 - 62, y0 + 12), (x1 - 38, y0 + 20), (x1 - 38, y1 - 20), (x1 - 62, y1 - 12)], fill=_a(NAVY))
    d.polygon([(x0 + 62, y0 + 12), (x0 + 44, y0 + 22), (x0 + 44, y1 - 22), (x0 + 62, y1 - 12)], fill=_a(NAVY))
    for my in (y0 - 6, y1 - 2):  # mirrors
        d.ellipse([x1 - 70, my, x1 - 56, my + 8], fill=_a(dark))
    for ly in (y0 + 8, y1 - 22):
        d.rounded_rectangle([x1 - 12, ly, x1 - 2, ly + 14], radius=4, fill=_a((255, 240, 180)))
        d.rounded_rectangle([x0 + 2, ly, x0 + 12, ly + 14], radius=4,
                            fill=_a((255, 40, 40) if brake else (150, 30, 30)))
    if brake:
        d.ellipse([x0 - 40, cy - 50, x0 + 10, cy + 50], fill=_a(RED, 60))


def _bike_top(d, cx, cy, color=AMBER):
    """A motorbike and rider from above, pointing right."""
    d.rounded_rectangle([cx + 36, cy - 6, cx + 74, cy + 6], radius=6, fill=_a(INK))   # front tyre
    d.rounded_rectangle([cx - 74, cy - 7, cx - 34, cy + 7], radius=6, fill=_a(INK))   # rear tyre
    d.rounded_rectangle([cx - 44, cy - 14, cx + 44, cy + 14], radius=14, fill=_a(color))
    d.line([(cx + 34, cy - 34), (cx + 34, cy + 34)], fill=_a(GREY), width=8)          # handlebar
    d.ellipse([cx - 30, cy - 30, cx + 16, cy + 30], fill=_a((60, 70, 90)))           # rider's shoulders
    d.ellipse([cx - 12, cy - 18, cx + 22, cy + 18], fill=_a(WHITE))                   # helmet


def adas(frame, d, t, i):
    """Top view of a two-lane road; our car drives right with its radar."""
    rx0, rx1, ry0, ry1 = X0, X0 + XW, VY + 10, VY + 300
    d.rectangle([rx0, ry0, rx1, ry1], fill=_a((44, 48, 56)))
    fade = 0.25 if i == 1 else 1.0
    run = t if i != 2 else min(t, 1.0) + max(0.0, t - 1.0) * 0.05
    mid = (ry0 + ry1) / 2
    for y in (ry0 + 8, ry1 - 8):
        d.line([(rx0, y), (rx1, y)], fill=_a(WHITE, 220 * fade), width=8)
    x = rx0 - 100 + (-(run * 420) % 100)
    while x < rx1:
        d.line([(max(rx0, x), mid), (min(rx1, x + 50), mid)], fill=_a(WHITE, 220 * fade), width=8)
        x += 100
    me = (rx0 + 150, (mid + ry1) / 2)
    alert = (i == 2 and t > 0.8) or (i == 1 and t > 1.1)
    cone = RED if alert else TEAL
    d.polygon([(me[0] + 95, me[1] - 24), (me[0] + 95, me[1] + 24), (rx1 - 20, me[1] + 66), (rx1 - 20, me[1] - 66)],
              fill=_a(cone, 70))
    _car_top(d, *me, TEAL)
    if i == 0:
        _car_top(d, rx1 - 190 + 12 * math.sin(t * 2), me[1], GREY)
        _label(d, rx0 + 330, me[1] - 30, "SAFE GAP", WHITE, 26, alpha=200)
        _chips(d, ["Adaptive cruise", "Lane keep"], ry1 + 30, t, 0.6)
    elif i == 1:
        p = ease_out((t - 0.5) / 0.9)
        bx, by = rx1 - 120 - 300 * p, (mid + ry0) / 2 + (me[1] - (mid + ry0) / 2) * p
        _bike_top(d, bx, by)
        _label(d, bx, ry0 - 40, "BIKE CUTS IN", AMBER, 28, "ma")
        _chips(d, ["Faded lines", "Cut-ins", "City traffic"], ry1 + 30, t, 0.8)
    elif i == 2:
        ox = rx1 - 120 - 230 * ease_out(t / 1.0)
        _car_top(d, ox, me[1], GREY, brake=True)
        _label(d, ox, ry0 - 40, "SUDDEN STOP", RED, 28, "ma")
        if t > 1.0:
            _pill(d, X0, ry1 + 30, "AUTO BRAKE", RED, WHITE, size=40)
    else:
        _chips(d, ["AEB on", "Lane keep off in city", "Hands on"], ry1 + 30, t, 0.4)


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
    scenes = []
    for i, slide in enumerate(slides[1:]):
        heading = Words(slide["heading"], TOP + 150, size=86)
        badge = badges[min(i, len(badges) - 1)]

        def draw(frame, d, t, heading=heading, slide=slide, badge=badge, i=i):
            _pill(d, X0, TOP + 40, badge, TEAL, INK, alpha=int(255 * ease_out(t / 0.2)), size=34)
            if post.get("hide_text"):  # voice-only version: just the visual, moved up to the middle
                art = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                visual(art, ImageDraw.Draw(art), t, i)
                frame.alpha_composite(art.crop((0, VY - 120, W, VY + 540)), (0, (H - 660) // 2 - 60))
                return
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
    for size in range(180, 70, -8):  # short titles get huge type
        layouts = [(_fit(d, p, BOLD, W - 2 * X0, 2000, size, size, spacing=1.04), c) for p, c in parts]
        if 180 + sum(len(l[1]) * l[2] for l, _ in layouts) <= 820:
            break
    y = 180
    for (f, lines, line_h), color in layouts:
        for line in lines:
            d.text((W // 2, y), line, font=f, fill=color, anchor="ma")
            y += line_h
    # the visual, cropped to what it draws and blown up to fill the space left
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    visual(im, ImageDraw.Draw(layer), 2.5, step)
    box = layer.getbbox()
    if box:
        art = layer.crop(box)
        room_h = H - 260 - (y + 70)
        k = min(1000 / art.width, room_h / art.height, 1.6)
        art = art.resize((int(art.width * k), int(art.height * k)), Image.LANCZOS)
        im.alpha_composite(art, ((W - art.width) // 2, y + 70 + (room_h - art.height) // 2))
    ImageDraw.Draw(im).text((W // 2, H - 190), handle, font=_font(BOLD, 48), fill=TEAL, anchor="ma")
    im.convert("RGB").save(path, "JPEG", quality=92)
    return path
