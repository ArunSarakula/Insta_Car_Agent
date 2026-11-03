"""More big 3D visuals (layout "big3d"), for the owner's November reels: a
tyre's date code, a turbo, a 12 V battery, the four automatic gearboxes, a
CNG car and the five road-trip checks. Words stay few and big: the captions
at the top already carry the sentence."""

import math
import random

from .design import AMBER, BOLD, GREY, INK, TEAL, WHITE
from .motion import GREEN, RED, W, X0, XW, _font, _pill, ease_out
from .motion_3d import DARK, RIM, RUBBER, STEEL, VY3, callout
from .motion_visuals import _a, _label
from .three import Cam, Scene, _cross, _sub, glow, mix, shade

BLUE = (90, 170, 255)
BODY = (0, 150, 130)       # the car's paint, a darker teal
GLASS = (40, 60, 84)
CHROME = (205, 212, 222)


# ---- shared pieces ----------------------------------------------------------

def face_out(sc, pts, col, centre, lit=True, alpha=255):
    """A face wound so it shows from outside a convex object around centre."""
    n = _cross(_sub(pts[1], pts[0]), _sub(pts[2], pts[0]))
    c = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
    if sum(n[k] * (c[k] - centre[k]) for k in range(3)) > 0:  # face() wants the normal inwards
        pts = pts[::-1]
    sc.face(pts, col, lit, alpha)


def prism(sc, profile, x0, x1, col, top=None, after=None):
    """A convex side profile [(y, z), ...] extruded across x0..x1."""
    cy = sum(p[0] for p in profile) / len(profile)
    cz = sum(p[1] for p in profile) / len(profile)
    centre = ((x0 + x1) / 2, cy, cz)
    sc.begin(centre, after)
    face_out(sc, [(x1, y, z) for y, z in profile], col, centre)
    face_out(sc, [(x0, y, z) for y, z in profile], col, centre)
    for k in range(len(profile)):
        (ya, za), (yb, zb) = profile[k], profile[(k + 1) % len(profile)]
        c = top(k) if top else col
        face_out(sc, [(x0, ya, za), (x0, yb, zb), (x1, yb, zb), (x1, ya, za)], c, centre)


def car(sc, cam, t=0.0, spin=0.0, boot=0.0, bonnet=0.0, lights=0.0, body=BODY, wheel_cap=None):
    """A simple hatchback, nose towards +y, axles on x. boot / bonnet open
    0..1; lights 0..1 glow. Returns key points for callouts."""
    tread = lambda k, n: shade(RUBBER, 0.75) if k % 2 else RUBBER
    spokes = wheel_cap or (lambda k, n: RIM if (k % 6) in (0, 1) else (52, 58, 70))
    for x in (-0.47, 0.47):
        for y in (-0.62, 0.66):
            sc.disc(x, 0.2, 0.13, RUBBER, cap=spokes, side=tread, rot=spin, n=28, centre=(y, -0.13))
    # lower body: a long slab with a sloped nose
    prism(sc, [(-1.0, -0.12), (1.0, -0.12), (1.05, 0.08), (0.95, 0.2), (-1.0, 0.24)], -0.46, 0.46, body)
    # cabin with sloped screens; windows darker
    win = lambda k: GLASS if k in (0, 2) else shade(body, 0.92)
    prism(sc, [(-0.85, 0.24), (0.45, 0.2), (0.1, 0.52), (-0.7, 0.54)], -0.42, 0.42, shade(body, 0.92), top=win)
    if bonnet > 0:  # the bonnet panel tilts up from the windscreen hinge
        a = 1.1 * bonnet
        hy, hz = 0.45, 0.21
        tip = (hy + 0.55 * math.cos(a), hz + 0.55 * math.sin(a))
        prism(sc, [(hy, hz), tip, (tip[0] + 0.01, tip[1] + 0.02), (hy, hz + 0.02)], -0.44, 0.44, shade(body, 1.1))
    if boot > 0:  # the hatch swings up from the roof
        a = math.pi / 2 + 1.0 * boot
        hy, hz = -0.72, 0.54
        tip = (hy + 0.36 * math.cos(-a + math.pi) * -1, hz + 0.36 * math.sin(a) * (1 - 0.4 * boot))
        prism(sc, [(hy, hz), (tip[0], tip[1]), (tip[0] - 0.02, tip[1] + 0.02), (hy - 0.02, hz + 0.02)],
              -0.42, 0.42, shade(body, 0.85))
    # headlamps and tail lamps
    for x in (-0.3, 0.3):
        sc.box(x - 0.12, 0.96, 0.08, x + 0.12, 1.02, 0.15, mix((200, 205, 215), (255, 245, 200), lights))
        sc.box(x - 0.12, -1.02, 0.12, x + 0.12, -0.98, 0.19, mix((120, 30, 30), RED, lights))
    return {"front": (0, 1.02, 0.12), "rear": (0, -1.0, 0.15), "roof": (0, -0.2, 0.54),
            "wheel_fl": (-0.47, 0.66, -0.13), "wheel_fr": (0.47, 0.66, -0.13), "wheel_rl": (-0.47, -0.62, -0.13), "bonnet": (0, 0.7, 0.21),
            "boot": (0, -0.85, 0.3)}


def ground(d, cam, z=-0.33, size=1.4, t=0.0, speed=0.0):
    pts = [cam.p(q) for q in ((-size, -size, z), (size, -size, z), (size, size, z), (-size, size, z))]
    d.polygon(pts, fill=_a((24, 30, 40)))
    if speed:
        for k in range(-6, 7):
            y0 = ((k * 0.35 - t * speed) % 3.2) - 1.6
            d.line([cam.p((-0.75, y0, z)), cam.p((-0.75, y0 + 0.15, z))], fill=_a((90, 98, 110)), width=6)


def big_word(d, text, y, col, t=1.0, start=0.0, size=96):
    y = min(y, VY3 + 760)  # clear of the handle line under it
    p = ease_out((t - start) / 0.35)
    if p <= 0:
        return
    f = _font(BOLD, int(size * (0.85 + 0.15 * p)))
    w = d.textlength(text, font=f)
    if w > XW:
        f = _font(BOLD, int(size * XW / w))
    d.text((X0 + XW / 2, y), text, font=f, fill=_a(col, 255 * p), anchor="mm")


def tick(d, x, y, ok, p=1.0, r=40):
    col = GREEN if ok else RED
    d.ellipse([x - r, y - r, x + r, y + r], fill=_a(col, 255 * p))
    w = max(6, r // 4)
    if ok:
        d.line([(x - r * 0.45, y), (x - r * 0.1, y + r * 0.38), (x + r * 0.5, y - r * 0.38)], fill=_a(INK, 255 * p),
               width=w, joint="curve")
    else:
        k = r * 0.4
        d.line([(x - k, y - k), (x + k, y + k)], fill=_a(INK, 255 * p), width=w)
        d.line([(x - k, y + k), (x + k, y - k)], fill=_a(INK, 255 * p), width=w)


def timer(d, cx, cy, r, frac, col, text):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=_a((50, 58, 72)), width=16)
    if frac > 0.01:
        d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * frac, fill=_a(col), width=16)
    d.text((cx, cy), text, font=_font(BOLD, int(r * 0.55)), fill=_a(WHITE), anchor="mm")


# ---- 1 tyre date code ---------------------------------------------------------

def tyre_code3d(frame, d, t, i):
    # 0 week then year: the tyre turns to show its sidewall, the code zooms in
    # 1 2325 = week 23 of 2025
    # 2 buying: an old code (red) swaps for a fresh one (green)
    # 3 rubber ages: tread wear bars and cracks
    turn = ease_out(t / 1.2) if i == 0 else 1.0
    yaw = -15 - 40 * turn + 3 * math.sin(t * 0.6)
    cam = Cam(yaw, 10, 860, W / 2, VY3 + 300)
    spin = -t * 0.25
    tread = lambda k, n: shade(RUBBER, 0.75) if k % 2 else RUBBER
    sidewall = lambda k, n: shade(RUBBER, 1.18) if k % 6 == 0 else RUBBER
    cracked = i == 3 and t > 1.4
    if cracked:
        sidewall = lambda k, n: (95, 90, 84) if k % 5 == 0 else shade(RUBBER, 1.05)
    sc = Scene(cam)
    sc.disc(0.0, 0.42, 0.2, RUBBER, cap=sidewall, side=tread, rot=spin, n=48)
    sc.disc(-0.104, 0.27, 0.012, (60, 66, 78), cap=lambda k, n: RIM if (k % 8) in (0, 1) else (52, 58, 70),
            rot=spin, n=40)
    sc.disc(-0.115, 0.07, 0.03, (140, 148, 160), rot=spin, n=16)
    sc.draw(d)

    # the code sits on the lower sidewall, in an oval stamp
    cx, cy = cam.p((-0.105, 0.0, -0.35))
    old = i == 2 and t < 1.3
    code = "1819" if old else "2325"
    p = ease_out((t - 0.9) / 0.4) if i == 0 else 1.0
    if p > 0:
        f = _font(BOLD, 88)
        w = d.textlength(code, font=f)
        col = RED if old else (GREEN if i == 2 else WHITE)
        d.rounded_rectangle([cx - w / 2 - 30, cy - 62, cx + w / 2 + 30, cy + 62], radius=60,
                            fill=_a((30, 34, 42), 235 * p), outline=_a(col, 255 * p), width=6)
        d.text((cx, cy), code, font=f, fill=_a(col, 255 * p), anchor="mm")
        if i in (0, 1):  # brackets under the two halves
            q = ease_out((t - (1.4 if i == 0 else 0.3)) / 0.4)
            if q > 0:
                half = w / 2
                for k, (lab, c) in enumerate((("WEEK", TEAL), ("YEAR", AMBER))):
                    x0 = cx - half + k * half
                    d.line([(x0 + 6, cy + 80), (x0 + half - 6, cy + 80)], fill=_a(c, 255 * q), width=8)
                    word = lab if i == 0 else ("23" if k == 0 else "2025")
                    _label(d, x0 + half / 2 + (k * 2 - 1) * 70, cy + 100, word, c, 48, "ma", 255 * q)
    if i == 2:
        tick(d, X0 + XW - 50, VY3 + 40, not old, 1.0, 44)
        big_word(d, "UNDER 1 YEAR OLD" if not old else "OLD STOCK", VY3 + 840, GREEN if not old else RED, t,
                 0.0 if old else 1.3, 64)
    if i == 3:
        if t > 0.3:  # wear bar in the tread groove
            callout(d, cam, (0.0, 0.0, 0.42), 140, -120, "WEAR BAR", AMBER)
        if cracked:
            rnd = random.Random(4)
            for _ in range(10):
                a = rnd.uniform(0.6, 2.5)
                r0 = rnd.uniform(0.3, 0.4)
                p0 = cam.p((-0.105, r0 * math.cos(a), r0 * math.sin(a)))
                p1 = cam.p((-0.105, (r0 + 0.03) * math.cos(a + 0.05), (r0 + 0.03) * math.sin(a + 0.05)))
                d.line([p0, p1], fill=_a(RED), width=4)
            callout(d, cam, (-0.105, 0.35 * math.cos(1.5), 0.35 * math.sin(1.5)), -120, -120, "CRACKS", RED, WHITE)


# ---- 2 turbo ------------------------------------------------------------------

def _turbo(sc, cam, spin, heat):
    hot = mix((120, 128, 140), (230, 60, 30), heat)
    blades = lambda base: (lambda k, n: shade(base, 1.25) if k % 3 == 0 else base)
    sc.disc(-0.36, 0.3, 0.2, hot, cap=blades(hot), rot=spin, n=36)               # turbine (exhaust side)
    sc.disc(-0.36, 0.14, 0.24, shade(hot, 0.8), rot=spin, n=24)
    sc.disc(0.0, 0.12, 0.3, (90, 98, 112), n=24)                                # bearing housing
    sc.disc(0.0, 0.05, 0.9, CHROME, rot=spin, n=12)                             # shaft
    sc.disc(0.36, 0.32, 0.2, (150, 172, 196), cap=blades((150, 172, 196)), rot=spin, n=36)  # compressor


def turbo3d(frame, d, t, i):
    # 0 why: spinning very fast, the turbine glows red hot
    # 1 the fix: hard drive, idle 30-60 s while oil flows and it cools, switch off
    # 2 city driving: cool and calm; revving and cold hard driving: red X
    # 3 my rule: 30-60 s
    if i == 0:
        heat = ease_out(t / 1.6)
    elif i == 1:
        heat = 1 - 0.8 * ease_out((t - 0.6) / 2.6)
    elif i == 2:
        heat = 0.15
    else:
        heat = 0.2
    yaw = -32 + 6 * math.sin(t * 0.5)
    cam = Cam(yaw, 18, 760, W / 2, VY3 + 330)
    speed = 9.0 if i in (0, 1) else 3.0
    glow(frame, [cam.p((-0.36, 0, 0))], (255, 90, 30), 260, 170 * heat, 0.9)
    sc = Scene(cam)
    _turbo(sc, cam, -t * speed, heat)
    sc.draw(d)
    if i == 1:  # oil drops running through the bearing
        for k in range(8):
            u = ((t * 0.7 + k / 8) % 1.0)
            x = -0.15 + 0.3 * u
            px, py = cam.p((x, 0.0, 0.13))
            d.ellipse([px - 12, py - 12, px + 12, py + 12], fill=_a(AMBER, 230))
        callout(d, cam, (0.0, 0.0, 0.13), 120, -150, "OIL COOLS IT", AMBER)
        secs = int(min(60, 60 * ease_out((t - 0.6) / 2.6)))
        timer(d, X0 + 90, VY3 + 700, 80, secs / 60, GREEN, f"{secs}s")
        _label(d, X0 + 200, VY3 + 668, "IDLE, THEN OFF", WHITE, 56, alpha=255 * ease_out((t - 0.8) / 0.35))
    elif i == 0:
        callout(d, cam, (-0.36, 0.0, 0.3), -60, -140, "TURBINE", mix(GREY, RED, heat), WHITE)
        big_word(d, "VERY HOT", VY3 + 790, mix(WHITE, RED, heat), t, 0.9, 110)
    elif i == 2:
        rows = [("City drive", True), ("Revving", False), ("Hard when cold", False)]
        for n, (txt, ok) in enumerate(rows):
            q = ease_out((t - 0.3 - n * 0.8) / 0.35)
            if q > 0:
                y = VY3 + 620 + n * 85
                tick(d, X0 + 40, y, ok, q, 36)
                _label(d, X0 + 100, y - 30, txt, WHITE, 52, alpha=255 * q)
    else:
        timer(d, X0 + XW / 2, VY3 + 720, 120, ease_out(t / 1.5), GREEN, "")
        d.text((X0 + XW / 2, VY3 + 720), "30-60 s", font=_font(BOLD, 52), fill=_a(WHITE), anchor="mm")


# ---- 3 battery ----------------------------------------------------------------

def _battery3d(sc, level, crust=0.0, neg_off=0.0):
    sc.box(-0.42, -0.26, -0.3, 0.42, 0.26, 0.22, (40, 44, 52))      # case
    sc.box(-0.44, -0.28, 0.22, 0.44, 0.28, 0.28, (58, 64, 76))      # lid
    pos = (220, 70, 70)
    sc.box(0.22, -0.06, 0.28, 0.32, 0.04, 0.38, mix(pos, (235, 235, 225), crust))
    lift = 0.12 * neg_off
    sc.box(-0.32, -0.06, 0.28 + lift, -0.22, 0.04, 0.38 + lift, mix((60, 60, 66), (235, 235, 225), crust))
    # charge cells on the front face
    for k in range(5):
        on = level > k / 5 + 0.02
        col = (GREEN if level > 0.55 else (AMBER if level > 0.3 else RED)) if on else (30, 34, 40)
        x0 = -0.34 + k * 0.142
        sc.box(x0, 0.262, -0.18, x0 + 0.11, 0.268, 0.1, col)


def battery3d(frame, d, t, i):
    # 0 why: parked for weeks, the cells drain one by one
    # 1 the fix: a weekly 20-30 min drive refills it
    # 2 long break: the negative cable comes off
    # 3 warning signs: white crust on the terminals, slow crank
    if i == 0:
        level = 1 - 0.68 * ease_out((t - 0.3) / 2.4)
    elif i == 1:
        level = 0.32 + 0.66 * ease_out((t - 0.6) / 2.0)
    elif i == 2:
        level = 0.9
    else:
        level = 0.45
    crust = ease_out((t - 0.4) / 1.4) if i == 3 else 0.0
    neg = ease_out((t - 0.6) / 0.8) if i == 2 else 0.0
    cam = Cam(-24 + 5 * math.sin(t * 0.5), 22, 760, W / 2, VY3 + 330)
    glow(frame, [cam.p((0, 0.27, -0.05))], GREEN if level > 0.55 else RED, 240, 70, 0.7)
    sc = Scene(cam)
    _battery3d(sc, level, crust, neg)
    sc.draw(d)
    if i == 0:
        days = int(28 * ease_out((t - 0.3) / 2.4))
        big_word(d, f"PARKED {days} DAYS", VY3 + 800, RED if level < 0.4 else WHITE, t, 0.2, 80)
    elif i == 1:
        big_word(d, "WEEKLY DRIVE", VY3 + 800, GREEN, t, 0.3, 90)
    elif i == 2:
        callout(d, cam, (-0.27, -0.01, 0.38 + 0.12 * neg), 150, -40, "NEGATIVE OFF", AMBER)
        big_word(d, "LONG TRIP AWAY", VY3 + 800, WHITE, t, 0.3, 80)
    else:
        if crust > 0.3:
            callout(d, cam, (0.27, -0.01, 0.38), 90, -130, "WHITE CRUST", (235, 235, 225))
        big_word(d, "SLOW START?", VY3 + 800, RED, t, 1.2, 96)


# ---- 4 gearboxes ----------------------------------------------------------------

def _gear(sc, x, r, rot, col, centre, teeth=None):
    n = teeth or max(12, int(r * 90))
    sc.disc(x, r, 0.08, col, cap=lambda k, nn: shade(col, 1.25) if k % 2 else shade(col, 0.85), rot=rot, n=n,
            centre=centre)


def gearbox3d(frame, d, t, i):
    # 0 AMT vs CVT: meshing gears with a jerky shift, pulleys with a sliding belt
    # 1 DCT vs torque converter: two clutches taking turns, a fluid coupling swirling
    # 2 pick: all four side by side, highlighted one by one
    # 3 test drive in traffic: a car creeping stop-go
    if i == 3:
        cam = Cam(-40, 20, 360, W / 2, VY3 + 320)
        creep = 0.5 * (1 + math.sin(t * 2.2))
        ground(d, cam, t=t, speed=0.6 * creep)
        sc = Scene(cam)
        pts = car(sc, cam, spin=-t * 3 * creep, lights=0.0)
        sc.draw(d)
        stop = math.sin(t * 2.2) < -0.3
        callout(d, cam, pts["rear"], -80, -260, "STOP" if stop else "GO", RED if stop else GREEN, WHITE)
        big_word(d, "TEST IN TRAFFIC", VY3 + 860, WHITE, t, 0.3, 70)
        return
    cam = Cam(-26, 14, 640, W / 2, VY3 + 330)
    sc = Scene(cam)
    if i == 0:
        # AMT on the left: two gears, the small one hops with a jerk every 1.2 s
        jerk = 0.05 * max(0.0, 1 - ((t % 1.2) / 0.15))
        _gear(sc, 0.0, 0.2, t * 2, AMBER, (-0.55, 0.15 + jerk))
        _gear(sc, 0.0, 0.13, -t * 2 * 0.2 / 0.13, shade(AMBER, 0.8), (-0.55 + 0.0, -0.18 + jerk))
        # CVT on the right: two pulleys, the belt radius slides smoothly
        u = 0.5 + 0.5 * math.sin(t * 1.4)
        r1, r2 = 0.08 + 0.12 * u, 0.2 - 0.12 * u
        for y, r in ((0.35, r1), (0.75, r2)):
            sc.disc(0.0, 0.22, 0.12, (90, 98, 112), centre=(y, 0.0), rot=t * 3, n=28)
            sc.disc(-0.065, r, 0.02, TEAL, centre=(y, 0.0), n=28)
        sc.draw(d)
        a, b = cam.p((-0.07, 0.35, r1)), cam.p((-0.07, 0.75, r2))
        c, e = cam.p((-0.07, 0.35, -r1)), cam.p((-0.07, 0.75, -r2))
        d.line([a, b], fill=_a(TEAL), width=10)
        d.line([c, e], fill=_a(TEAL), width=10)
        callout(d, cam, (0.0, -0.55, 0.38), 0, -110, "AMT", AMBER)
        callout(d, cam, (0.0, 0.55, 0.3), 40, -150, "CVT", TEAL)
        _label(d, X0 + 40, VY3 + 700, "JERKY", AMBER, 60)
        _label(d, X0 + XW - 40, VY3 + 700, "SMOOTH", TEAL, 60, "ra")
    elif i == 1:
        # DCT: two clutch discs, the engaged one lights up in turn
        which = int(t / 0.9) % 2
        for k, y in enumerate((-0.68, -0.42)):
            on = k == which
            sc.disc(0.0, 0.2, 0.06, BLUE if on else (70, 80, 96), rot=t * 6 if on else t * 1.5, n=28,
                    centre=(y, 0.0), cap=lambda kk, n, on=on: shade(BLUE if on else (70, 80, 96), 1.2 if kk % 4 == 0 else 1))
        # torque converter: a fat ring with fluid swirling round it
        sc.disc(0.0, 0.3, 0.2, GREEN, cap=lambda k, n: shade(GREEN, 1.25) if k % 3 == 0 else shade(GREEN, 0.8),
                rot=t * 4, n=36, centre=(0.55, 0.0))
        sc.draw(d)
        for k in range(10):  # swirl dots
            a = t * 5 + k * 2 * math.pi / 10
            px, py = cam.p((-0.11, 0.55 + 0.2 * math.cos(a), 0.2 * math.sin(a)))
            d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=_a(WHITE, 200))
        callout(d, cam, (0.0, -0.55, 0.22), 0, -130, "DCT", BLUE, INK)
        callout(d, cam, (0.0, 0.55, 0.32), 40, -140, "TORQUE CONV.", GREEN)
        _label(d, X0 + 40, VY3 + 700, "QUICK", BLUE, 60)
        _label(d, X0 + XW - 40, VY3 + 700, "TOUGH", GREEN, 60, "ra")
    else:
        names = [("AMT", AMBER, "BUDGET"), ("CVT", TEAL, "COMFORT"), ("DCT", BLUE, "FUN"), ("TC", GREEN, "COMFORT")]
        hi = min(3, int(t / 0.9))
        for k, (name, col, _) in enumerate(names):
            y = -0.9 + k * 0.6
            on = k == hi
            sc.disc(0.0, 0.22 if on else 0.17, 0.1, col if on else shade(col, 0.5), rot=t * (4 if on else 1),
                    n=24, centre=(y, 0.0), cap=lambda kk, n, c=col, on=on: shade(c if on else shade(c, 0.5), 1.25 if kk % 2 else 0.9))
        sc.draw(d)
        for k, (name, col, use) in enumerate(names):
            px, py = cam.p((-0.06, -0.9 + k * 0.6, -0.32))
            _label(d, px, py + 10, name, col if k == hi else GREY, 40, "ma")
        name, col, use = names[hi]
        big_word(d, f"{use}: {name}", VY3 + 820, col, t, 0.0, 80)


# ---- 5 CNG ------------------------------------------------------------------------

def _cylinder(sc, cam, y=-0.55, glowing=None):
    sc.disc(0.0, 0.17, 0.62, (225, 230, 236), cap=lambda k, n: (200, 205, 214), n=24, centre=(y, 0.32))


def cng3d(frame, d, t, i):
    # 0 factory kit vs cheap kit: a green tick on the factory car
    # 1 trade-off: the boot opens on the cylinder, power down, cost down
    # 2 care: petrol gauge, spark plug, cylinder test date
    # 3 no damage with care
    cam = Cam(150 + 6 * math.sin(t * 0.4), 20, 380, W / 2, VY3 + 320)
    ground(d, cam, t=t, speed=0.0)
    boot = ease_out((t - 0.4) / 0.8) if i in (1, 2) else 0.0
    if i == 3:
        glow(frame, [cam.p((0, 0.7, 0.1))], GREEN, 300, 90, 0.8)
    sc = Scene(cam)
    pts = car(sc, cam, boot=boot)
    sc.draw(d)
    if boot > 0.4:  # the cylinder across the boot floor, drawn over the open hatch
        cyl = Scene(cam)
        cyl.disc(0.0, 0.13, 0.7 * ease_out((boot - 0.4) / 0.6), (228, 232, 238), cap=lambda k, n: (200, 205, 214),
                 n=24, centre=(-0.95, 0.3))
        cyl.draw(d)
    if i == 0:
        p = ease_out((t - 0.6) / 0.3)
        tick(d, X0 + XW - 70, VY3 + 60, True, p, 50)
        big_word(d, "FACTORY KIT", VY3 + 860, GREEN, t, 0.6, 90)
    elif i == 1:
        if boot > 0.5:
            callout(d, cam, (0.2, -0.95, 0.42), 160, -160, "LESS BOOT", AMBER)
        rows = [("POWER", RED, 0.85), ("COST", GREEN, 0.5)]
        for n, (lab, col, lv) in enumerate(rows):
            q = ease_out((t - 1.0 - n * 0.6) / 0.6)
            y = VY3 + 640 + n * 80
            _label(d, X0, y, lab, WHITE, 44)
            d.rounded_rectangle([X0 + 220, y + 6, X0 + XW, y + 46], radius=20, fill=_a((40, 46, 58)))
            w = (XW - 220) * (1 - (1 - lv) * q)
            d.rounded_rectangle([X0 + 220, y + 6, X0 + 220 + w, y + 46], radius=20, fill=_a(col))
            if q > 0.5:
                _label(d, X0 + XW, y - 4, "▼", col, 40, "ra")
    elif i == 2:
        if boot > 0.5:
            callout(d, cam, (0.2, -0.95, 0.42), 140, -170, "TEST: 3 YRS", TEAL)
        big_word(d, "KEEP SOME PETROL", VY3 + 860, AMBER, t, 0.8, 70)
    else:
        big_word(d, "NO DAMAGE", VY3 + 860, GREEN, t, 0.3, 110)


# ---- 6 trip checks ----------------------------------------------------------------

def trip3d(frame, d, t, i):
    # 0 tyres and spare: each tyre gets a pressure ring
    # 1 fluids: the bonnet opens on oil, coolant, washer
    # 2 wipers and lights: lamps glow, the wiper sweeps
    # 3 brakes: front discs glow, the car stops straight
    yaw = -35 + (40 if i == 1 else 0) * 0 + 6 * math.sin(t * 0.4)
    cam = Cam(yaw if i != 1 else 20 + 6 * math.sin(t * 0.4), 22, 380, W / 2, VY3 + 320)
    rolling = i == 3 and t < 1.4
    ground(d, cam, t=t, speed=1.2 * max(0.0, 1 - t / 1.4) if i == 3 else 0.0)
    lights = (0.5 + 0.5 * math.sin(t * 6)) if i == 2 else 0.0
    if i == 2:
        for q in ((0.3, 1.05, 0.12), (-0.3, 1.05, 0.12)):
            glow(frame, [cam.p(q)], (255, 240, 190), 120, 160 * lights, 0.7)
    sc = Scene(cam)
    bonnet = ease_out((t - 0.3) / 0.8) if i == 1 else 0.0
    pts = car(sc, cam, spin=(-t * 6 if rolling else 0.0), bonnet=bonnet, lights=lights)
    sc.draw(d)
    if i == 0:
        for n, key in enumerate(("wheel_fl", "wheel_fr")):
            q = ease_out((t - 0.3 - n * 0.6) / 0.4)
            if q > 0:
                x, y = cam.p(pts[key])
                d.ellipse([x - 70, y - 70, x + 70, y + 70], outline=_a(GREEN, 255 * q), width=8)
        if t > 1.5:
            callout(d, cam, pts["boot"], 120, -220, "SPARE TOO", AMBER)
        big_word(d, "PRESSURE (COLD)", VY3 + 880, WHITE, t, 0.3, 70)
    elif i == 1:
        if bonnet > 0.6:
            for n, (lab, col, q3) in enumerate((("OIL", AMBER, (-0.2, 0.75, 0.24)), ("COOLANT", TEAL, (0.2, 0.8, 0.24)),
                                                ("WASHER", BLUE, (0.3, 0.6, 0.24)))):
                if t > 1.0 + n * 0.6:
                    callout(d, cam, q3, -160 + n * 160, -200 - 40 * n, lab, col)
        big_word(d, "ENGINE COLD", VY3 + 880, WHITE, t, 0.3, 70)
    elif i == 2:
        a = math.sin(t * 3)  # the wiper sweeping the windscreen
        p0 = cam.p((0.0, 0.42, 0.22))
        p1 = cam.p((0.35 * a, 0.26, 0.48))
        d.line([p0, p1], fill=_a(INK), width=10)
        big_word(d, "WIPERS + LIGHTS", VY3 + 880, WHITE, t, 0.3, 70)
    else:
        q = ease_out((t - 1.0) / 0.4)
        if q > 0:
            x, y = cam.p(pts["wheel_fl"])
            d.ellipse([x - 70, y - 70, x + 70, y + 70], outline=_a(GREEN, 255 * q), width=8)
        big_word(d, "STOPS STRAIGHT", VY3 + 880, GREEN, t, 1.4, 70)


VISUALS3D_MORE = {"tyre_code": tyre_code3d, "turbo": turbo3d, "battery": battery3d, "gearbox": gearbox3d,
                  "cng": cng3d, "trip": trip3d}
