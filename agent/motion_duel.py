"""A head-to-head car comparison reel (layout "duel"): two cars face each
other like a fight card, each round is a category, the winner of a round
scores a point on the scoreboard, and the last scene crowns the winner.

    post["duel"] = {
        "left": {"name": "Virtus", "color": "blue"},
        "right": {"name": "Slavia", "color": "green"},
        "rounds": [
            {"title": "ON-ROAD PRICE", "left": 13.2, "right": 11.9, "fmt": "Rs {:.1f} L", "win": "right"},
            {"title": "ENGINE", "left": "1.0 TSI", "right": "1.0 TSI", "win": "tie"},
        ],
        "verdict": {"big": "Rs 2,200", "sub": "LESS EVERY MONTH", "note": "Estimate, base variants"},
    }

Scene i draws round i; the scene after the last round is the verdict.
"""

import math
import random

from PIL import Image

from .design import AMBER, BOLD, GREY, INK, MEDIUM, TEAL, WHITE
from .motion import GREEN, RED, W, X0, XW, _font, ease_out
from .motion_board import _a, _c, _fitted

SCORE_Y = 650    # the scoreboard, under the caption line
CARS_Y = 910     # the road the two cars stand on
BOX_Y = 1030     # the round's title, then its two value tiles
PANEL = (24, 34, 50)
DIM = (60, 70, 86)


def _ease_back(x):
    x = max(0.0, min(1.0, x))
    c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def _car(d, cx, cy, s, col, facing, t, alpha=255, drive=0.0):
    """A side view of a sedan, s pixels long, nose towards `facing` (+1 right, -1 left)."""
    f = facing
    bob = 2 * math.sin(t * 9) * drive

    def P(x, y):  # x along the car from -0.5 (tail) to 0.5 (nose), y up from the road
        return (cx + f * x * s, cy - y * s + bob)

    body = [(-0.5, 0.09), (-0.5, 0.2), (-0.44, 0.24), (-0.3, 0.25), (-0.17, 0.37), (0.1, 0.37), (0.24, 0.26),
            (0.45, 0.22), (0.5, 0.16), (0.5, 0.09)]
    d.polygon([P(x, y) for x, y in body], fill=_a(col, alpha))
    d.polygon([P(x, y) for x, y in body[:6]] + [P(0.1, 0.37)], fill=_a(col, alpha))
    # windows
    glass = (170, 205, 235)
    d.polygon([P(-0.27, 0.26), P(-0.16, 0.345), P(-0.04, 0.345), P(-0.04, 0.26)], fill=_a(glass, alpha * 0.85))
    d.polygon([P(-0.01, 0.26), P(-0.01, 0.345), P(0.09, 0.345), P(0.2, 0.26)], fill=_a(glass, alpha * 0.85))
    # shine line and lamps
    d.line([P(-0.48, 0.19), P(0.47, 0.19)], fill=_a(WHITE, alpha * 0.35), width=max(2, int(s * 0.008)))
    d.ellipse([*P(0.455, 0.19), *P(0.49, 0.165)] if f > 0 else [*P(0.49, 0.19), *P(0.455, 0.165)],
              fill=_a(AMBER, alpha))
    d.rectangle([*P(-0.5, 0.2), *P(-0.475, 0.17)] if f > 0 else [*P(-0.475, 0.2), *P(-0.5, 0.17)],
                fill=_a(RED, alpha))
    # wheels with spinning spokes
    r = 0.085 * s
    for wx in (-0.3, 0.3):
        x, y = P(wx, 0.085)
        d.ellipse([x - r, y - r, x + r, y + r], fill=_a((18, 20, 26), alpha))
        d.ellipse([x - r * 0.62, y - r * 0.62, x + r * 0.62, y + r * 0.62], fill=_a((190, 196, 206), alpha))
        for k in range(5):
            a = t * 14 * drive * f + k * 2 * math.pi / 5
            d.line([(x, y), (x + r * 0.55 * math.cos(a), y + r * 0.55 * math.sin(a))],
                   fill=_a((90, 96, 108), alpha), width=max(2, int(r * 0.14)))
    # shadow
    x0, y0 = P(-0.52, 0.0)
    x1, y1 = P(0.52, -0.025)
    d.ellipse([min(x0, x1), y0 - 6, max(x0, x1), y0 + 8], fill=_a((0, 0, 0), alpha * 0.35))


def _score(post, i):
    """Points each side has after rounds 0..i-1."""
    score = [0, 0]
    for r in post["duel"]["rounds"][:i]:
        if r.get("win") == "left":
            score[0] += 1
        elif r.get("win") == "right":
            score[1] += 1
    return score


def _header(post, d, t, i, intro):
    duel = post["duel"]
    L, R = duel["left"], duel["right"]
    lc, rc = _c(L.get("color"), (90, 170, 255)), _c(R.get("color"), GREEN)
    p = ease_out((t - 0.0) / 0.5) if intro else 1.0
    # cars slide in from the sides on the first scene, then idle
    off = (1 - p) * 560
    for k in range(-1, 14):  # dashed road, moving while the cars drive in
        x = X0 - 40 + k * 80 - (t * 300 * (1 - p)) % 80
        d.line([(x, CARS_Y + 12), (x + 40, CARS_Y + 12)], fill=_a(DIM, 200), width=5)
    _car(d, X0 + 195 - off, CARS_Y, 370, lc, 1, t, 255, drive=1 - p + 0.15)
    _car(d, X0 + XW - 195 + off, CARS_Y, 370, rc, -1, t, 255, drive=1 - p + 0.15)
    # name plates
    for name, col, x, anchor in ((L["name"], lc, X0, "la"), (R["name"], rc, X0 + XW, "ra")):
        f = _fitted(d, name.upper(), 380, 64, 30)
        d.text((x, SCORE_Y - 30), name.upper(), font=f, fill=_a(col, 255 * p), anchor=anchor)
    # the scoreboard between them
    before, after = _score(post, i), _score(post, i + 1)
    flip = ease_out((t - 1.6) / 0.3)
    shown = after if flip >= 1 else before
    cx, cy = X0 + XW / 2, SCORE_Y
    d.rounded_rectangle([cx - 120, cy - 62, cx + 120, cy + 62], radius=22, fill=_a(INK, 235 * p),
                        outline=_a(AMBER, 255 * p), width=4)
    f = _font(BOLD, 84)
    for k, (val, x) in enumerate(((shown[0], cx - 62), (shown[1], cx + 62))):
        bump = 1.0
        if after[k] != before[k] and 1.6 < t < 2.1:
            bump = 1 + 0.35 * math.sin((t - 1.6) / 0.5 * math.pi)
        d.text((x, cy), str(val), font=_font(BOLD, int(84 * bump)), fill=_a(WHITE, 255 * p), anchor="mm")
    d.text((cx, cy), "-", font=f, fill=_a(GREY, 255 * p), anchor="mm")


def _value(r, side, k):
    v = r.get(side, "")
    if isinstance(v, (int, float)):
        return r.get("fmt", "{}").format(v * k)
    return str(v)


def _round(post, d, t, i):
    r = post["duel"]["rounds"][i]
    L, R = post["duel"]["left"], post["duel"]["right"]
    lc, rc = _c(L.get("color"), (90, 170, 255)), _c(R.get("color"), GREEN)
    # round title slams in
    p = _ease_back((t - 0.1) / 0.4)
    if p > 0:
        label = f"ROUND {i + 1}"
        d.text((X0 + XW / 2, BOX_Y - 40), label, font=_font(BOLD, 40), fill=_a(AMBER, 255 * min(1, p)),
               anchor="mm")
        f = _fitted(d, r["title"].upper(), XW, int(90 * max(0.6, p)), 40)
        d.text((X0 + XW / 2, BOX_Y + 40), r["title"].upper(), font=f, fill=_a(WHITE, 255 * min(1, p)), anchor="mm")
    # the two tiles, numbers counting up
    count = 0.75 + 0.25 * ease_out((t - 0.5) / 1.0)  # rolls up to the real number
    win = r.get("win")
    decided = t > 1.6
    w, gap, y0, y1 = (XW - 40) / 2, 40, BOX_Y + 110, BOX_Y + 300
    for n, (side, col) in enumerate((("left", lc), ("right", rc))):
        q = ease_out((t - 0.35 - n * 0.12) / 0.4)
        if q <= 0:
            continue
        x = X0 + n * (w + gap)
        y = y0 + 40 * (1 - q)
        lost = decided and win in ("left", "right") and win != side
        won = decided and win == side
        fill = PANEL if not won else tuple(int(c * 0.35) for c in col)
        d.rounded_rectangle([x, y, x + w, y1], radius=28, fill=_a(fill, 255 * q),
                            outline=_a(col if not lost else DIM, 255 * q), width=6 if won else 3)
        text = _value(r, side, count)
        f = _fitted(d, text, w - 40, 92, 36)
        d.text((x + w / 2, (y + y1) / 2), text, font=f, fill=_a(DIM if lost else WHITE, 255 * q), anchor="mm")
        if won:  # the +1 floats up to the scoreboard
            g = ease_out((t - 1.6) / 0.5)
            d.rounded_rectangle([x + w / 2 - 60, y1 - 24, x + w / 2 + 60, y1 + 30], radius=27,
                                fill=_a(col, 255 * g))
            d.text((x + w / 2, y1 + 3), "+1", font=_font(BOLD, 40), fill=_a(INK, 255 * g), anchor="mm")
    if decided and win == "tie":
        g = ease_out((t - 1.6) / 0.4)
        cx = X0 + XW / 2
        d.rounded_rectangle([cx - 90, y1 - 24, cx + 90, y1 + 30], radius=27, fill=_a(AMBER, 255 * g))
        d.text((cx, y1 + 3), "TIE", font=_font(BOLD, 40), fill=_a(INK, 255 * g), anchor="mm")
    if r.get("note"):
        d.text((X0 + XW / 2, y1 + 66), r["note"], font=_font(MEDIUM, 36),
               fill=_a(GREY, 255 * ease_out((t - 1.8) / 0.4)), anchor="mm")


def _confetti(d, t, seed=7):
    rnd = random.Random(seed)
    for _ in range(70):
        x0, speed, sway, col = rnd.uniform(X0, X0 + XW), rnd.uniform(260, 520), rnd.uniform(0, 6), rnd.choice(
            (AMBER, TEAL, GREEN, WHITE, (255, 110, 150)))
        y = 580 + (t - 0.3) * speed - rnd.uniform(0, 300)
        if 560 < y < 1420:
            x = x0 + 30 * math.sin(t * 3 + sway)
            a = t * 5 + sway
            dx, dy = 12 * math.cos(a), 6 * math.sin(a)
            d.polygon([(x - dx, y - dy), (x + dy, y - dx), (x + dx, y + dy), (x - dy, y + dx)], fill=_a(col, 230))


def _verdict(post, d, t, frame):
    duel = post["duel"]
    score = _score(post, len(duel["rounds"]))
    side = "left" if score[0] > score[1] else "right" if score[1] > score[0] else None
    v = duel.get("verdict", {})
    side = v.get("winner", side)
    car = duel.get(side) if side else None
    col = _c(car.get("color"), GREEN) if car else AMBER
    p = ease_out((t - 0.1) / 0.6)
    # the winner drives to the middle
    if car:
        _car(d, X0 + XW / 2 + (1 - p) * (-460 if side == "left" else 460), 820, 520, col,
             1 if side == "left" else -1, t, 255, drive=(1 - p) + 0.1)
    q = _ease_back((t - 0.5) / 0.45)
    if q > 0:
        title = f"{car['name']} WINS".upper() if car else "IT'S A TIE"
        f = _fitted(d, title, XW, int(104 * max(0.5, q)), 48)
        d.text((X0 + XW / 2, 900), title, font=f, fill=_a(col, 255 * min(1, q)), anchor="mm",
               stroke_width=4, stroke_fill=_a(INK, 255))
        d.text((X0 + XW / 2, 985), f"{score[0]} - {score[1]}", font=_font(BOLD, 52),
               fill=_a(WHITE, 255 * min(1, q)), anchor="mm")
    g = ease_out((t - 1.0) / 0.4)
    if g > 0 and v.get("big"):
        cy = 1160
        d.rounded_rectangle([X0 + 60, cy - 110, X0 + XW - 60, cy + 110], radius=36, fill=_a(PANEL, 245 * g),
                            outline=_a(col, 255 * g), width=5)
        f = _fitted(d, v["big"], XW - 200, 110, 50)
        d.text((X0 + XW / 2, cy - 22), v["big"], font=f, fill=_a(WHITE, 255 * g), anchor="mm")
        if v.get("sub"):
            d.text((X0 + XW / 2, cy + 62), v["sub"].upper(), font=_font(BOLD, 36), fill=_a(col, 255 * g), anchor="mm")
    if v.get("note"):
        d.text((X0 + XW / 2, 1325), v["note"], font=_font(MEDIUM, 32),
               fill=_a(GREY, 255 * ease_out((t - 1.5) / 0.4)), anchor="mm")
    if car:
        _confetti(d, t)


def duel(post, frame, d, t, i):
    rounds = post["duel"]["rounds"]
    if i < len(rounds):
        _header(post, d, t, i, intro=(i == 0))
        _round(post, d, t, i)
    else:
        _verdict(post, d, t, frame)


def check_duel(post) -> list[str]:
    errors = []
    duel_ = post.get("duel") or {}
    for side in ("left", "right"):
        if not (duel_.get(side) or {}).get("name"):
            errors.append(f"duel: no {side} car name")
    rounds = duel_.get("rounds") or []
    if not rounds:
        errors.append("duel: no rounds")
    for n, r in enumerate(rounds, 1):
        if r.get("win") not in ("left", "right", "tie"):
            errors.append(f"round {n}: win must be left, right or tie")
    if len(post.get("slides", [])) - 1 != len(rounds) + 1:
        errors.append("duel: need one slide per round plus one for the verdict, after the hook")
    return errors
