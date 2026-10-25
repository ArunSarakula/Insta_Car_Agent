"""Big 3D visuals for the animated reels (layout "big3d"): the part itself
fills the screen, drawn in perspective, and the spoken line runs underneath
as a short caption. Each visual draws scene i like the 2D ones."""

import math
import random

from .design import AMBER, BOLD, GREY, INK, TEAL, WHITE
from .motion import GREEN, RED, W, X0, XW, _font, _pill, ease_out
from .motion_visuals import DIM, _a, _bar, _label, _step
from .three import Cam, Scene, glow, mix, shade

STEEL = (150, 158, 172)
DARK = (78, 86, 100)
LINING = (175, 130, 90)
VY3 = 430  # top of the 3D area; the caption sits under it


def callout(d, cam, q, dx, dy, text, col, fg=INK, size=28):
    x, y = cam.p(q)
    tx, ty = x + dx, y + dy
    d.line([(x, y), (tx, ty)], fill=_a(col), width=3)
    d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=_a(col))
    f = _font(BOLD, size)
    w = d.textlength(text, font=f)
    tx = max(X0 + w / 2 + 16, min(X0 + XW - w / 2 - 16, tx))
    d.rounded_rectangle([tx - w / 2 - 16, ty - 24, tx + w / 2 + 16, ty + 24], radius=24, fill=_a(col))
    d.text((tx, ty), text, font=f, fill=_a(fg), anchor="mm")


def _pedal(d, x, y, press, on_dead):
    """The clutch pedal from the side, with the left foot on it or moved
    across to the dead pedal (a footrest that doesn't move)."""
    d.rounded_rectangle([x, y, x + 250, y + 290], radius=24, fill=_a((26, 30, 38)))
    pivot = (x + 170, y + 40)
    ang = math.radians(100 - 28 * press)  # the arm swings forward as it is pressed
    pad = (pivot[0] + 175 * math.cos(ang), pivot[1] + 175 * math.sin(ang))
    d.line([pivot, pad], fill=_a(GREY), width=14)
    d.ellipse([pivot[0] - 12, pivot[1] - 12, pivot[0] + 12, pivot[1] + 12], fill=_a(DIM))
    d.line([(pad[0] - 34, pad[1] - 12), (pad[0] + 10, pad[1] + 26)], fill=_a(WHITE), width=20)
    rest = (x + 50, y + 200)
    d.rounded_rectangle([rest[0] - 26, rest[1] - 50, rest[0] + 6, rest[1] + 50], radius=10, fill=_a((60, 66, 78)))
    fx, fy = (rest[0] + 40, rest[1] - 30) if on_dead else (pad[0] + 24, pad[1] - 46)
    k = 1 if on_dead else 0
    d.rounded_rectangle([fx - 28 - 10 * k, fy - 70, fx + 28, fy + 40], radius=26, fill=_a(AMBER, 240))
    _label(d, x + 125, y + 258, "DEAD PEDAL" if on_dead else "CLUTCH PEDAL", AMBER if not on_dead else GREEN,
           24, "ma")


def clutch3d(frame, d, t, i):
    # 0 foot resting: half engaged, the plate slips, heats and wears
    # 1 pedal held through a turn: plates apart, the release bearing works, the car coasts
    # 2 foot to the dead pedal: clamped, both spin together
    # 3 payoff: long clutch life
    press, slip = _step([(0.3, 0.45), (1.0, 0.7), (1.0, 0.7), (0.0, 0.0)], i)
    move = ease_out((t - 0.6) / 0.6) if i == 2 else (1.0 if i == 3 else 0.0)
    press *= 1 - move
    slip *= 1 - move
    gap = 0.012 + 0.07 * press

    yaw = -22 + 5 * math.sin(t * 0.5) + 14 * (1 - ease_out(t / 0.8)) + (8 * math.sin(t * 0.35) if i == 3 else 0)
    cam = Cam(yaw, 16, 690, W / 2 - 10, VY3 + 300)
    engine = t * 6.0
    lag = slip * ease_out((t - 0.2) / 0.6)
    plate = engine * (1 - lag)
    heat = lag * ease_out((t - 0.5) / 1.0) if i == 0 else 0.0

    xf = -0.36                       # flywheel centre
    xp = xf + 0.035 + gap + 0.015    # clutch plate
    xpp = xp + 0.015 + gap + 0.03    # pressure plate
    xb = xpp + 0.11                  # release bearing
    gx0 = 0.28                       # gearbox front

    col = lambda base, mark: (lambda k, n: AMBER if k == 0 else (shade(base, 0.82) if k % 4 == 2 else base))
    lining = mix(LINING, RED, heat)
    glow_col = RED if i == 0 else (GREEN if move > 0.5 else None)
    if glow_col:
        rim = [cam.p((xp, 0.3 * math.cos(a), 0.3 * math.sin(a))) for a in (0, 1.6, 3.2, 4.7)]
        glow(frame, rim, glow_col, 120, 120 * (heat if i == 0 else move), 0.9)

    sc = Scene(cam)
    sc.box(gx0, -0.16, -0.2, gx0 + 0.26, 0.16, 0.14, (54, 62, 76))
    sc.disc((xb + gx0) / 2, 0.035, gx0 - xb, (120, 128, 140), rot=plate)  # gearbox input shaft
    sc.disc(xf, 0.37, 0.05, (110, 116, 128), cap=lambda k, n: (130, 136, 148) if k % 2 else (90, 96, 108), n=60,
            rot=engine)  # ring gear teeth
    sc.disc(xf, 0.33, 0.075, STEEL, cap=col(STEEL, 0), rot=engine)
    sc.disc(xp, 0.3, 0.03, lining, cap=lambda k, n: AMBER if k == 0 else shade(lining, 0.8 if k % 2 else 1.0),
            rot=plate)
    sc.disc(xp - 0.03, 0.11, 0.03, DARK, rot=plate)
    sc.disc(xp + 0.03, 0.11, 0.03, DARK, cap=col(DARK, 0), rot=plate)
    sc.disc(xpp, 0.32, 0.06, DARK, cap=col((100, 108, 122), 0), rot=engine)
    bearing = AMBER if i == 1 else (120, 128, 140)
    sc.disc(xb, 0.08, 0.06, bearing, rot=engine if i == 1 else 0)
    sc.draw(d)

    if i == 0 and heat > 0.15:  # sparks off the slipping lining
        rnd = random.Random(int(t * 30))
        for _ in range(int(14 * heat)):
            a = rnd.uniform(0, 2 * math.pi)
            r0, r1 = 0.3, 0.3 + rnd.uniform(0.05, 0.16)
            p0 = cam.p((xp, r0 * math.cos(a), r0 * math.sin(a)))
            p1 = cam.p((xp, r1 * math.cos(a + 0.25), r1 * math.sin(a + 0.25)))
            d.line([p0, p1], fill=_a(mix(AMBER, RED, rnd.random())), width=4)

    callout(d, cam, (xf, 0.0, -0.37), -30, 80, "FLYWHEEL", STEEL)
    callout(d, cam, (xp, 0.0, -0.3), 120, 150, "CLUTCH PLATE", mix(LINING, RED, heat), WHITE if heat > 0.5 else INK)
    callout(d, cam, (gx0 + 0.13, 0.0, 0.14), 40, -110, "GEARBOX", DIM, WHITE)
    if i == 1:
        callout(d, cam, (xb, 0.0, -0.08), 120, 110, "RELEASE BEARING", AMBER)

    _pedal(d, X0 + XW - 250, VY3 + 570, press, move > 0.5)
    bx, by, bw = X0, VY3 + 800, XW - 300
    if i == 0:
        if heat > 0.3:
            _pill(d, X0, VY3 - 10, "SLIPPING: PLATE WEARS", RED, WHITE, size=32)
        _bar(d, bx, by, bw, 0.05 + 0.4 * ease_out((t - 0.5) / 1.6), RED, "PLATE WEAR")
    elif i == 1:
        if t > 0.6:
            _pill(d, X0, VY3 - 10, "DISENGAGED: CAR COASTS", AMBER, INK, size=32)
        _bar(d, bx, by, bw, 0.45 * ease_out((t - 0.6) / 1.6), AMBER, "BEARING WEAR")
    elif i == 2:
        if move > 0.5:
            _pill(d, X0, VY3 - 10, "LOCKED: SPIN TOGETHER", GREEN, INK, size=32)
        _bar(d, bx, by, bw, 0.45, mix(RED, GREEN, move), "WEAR STOPPED" if move > 0.5 else "PLATE WEAR")
    else:
        _pill(d, X0, VY3 - 10, "LASTS LONGER", GREEN, INK, size=32)
        _bar(d, bx, by, bw, 0.3 + 0.6 * ease_out((t - 0.3) / 1.2), GREEN, "CLUTCH LIFE")


VISUALS3D = {"clutch": clutch3d}
