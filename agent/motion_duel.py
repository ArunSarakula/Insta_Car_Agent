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

from PIL import Image, ImageDraw

from .design import AMBER, BOLD, GREY, INK, MEDIUM, TEAL, WHITE
from .motion import GREEN, RED, W, X0, XW, _font, ease_out
from .motion_board import _a, _c, _fitted

SCORE_Y = 660    # names and scoreboard, under the caption line
PHOTO_BAND = (730, 970)  # the two car photos, when the post has them
PANEL = (28, 28, 36)
DIM = (72, 72, 84)
_photos = {}


def _ease_back(x):
    x = max(0.0, min(1.0, x))
    c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def _has_photos(post):
    duel_ = post["duel"]
    return bool(duel_["left"].get("photo") and duel_["right"].get("photo"))


def _box_y(post):
    return 1040 if _has_photos(post) else 850


def _photo(path, w, h):
    """The car photo scaled to fit w x h, cached."""
    key = (path, w, h)
    if key not in _photos:
        im = Image.open(path).convert("RGBA")
        k = min(w / im.width, h / im.height)
        _photos[key] = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    return _photos[key]


def _put_photo(frame, path, cx, cy, w, h, alpha=1.0, grey=False):
    im = _photo(path, int(w), int(h))
    if grey:
        im = im.convert("LA").convert("RGBA")
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    frame.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def _score(post, i):
    """Points each side has after rounds 0..i-1."""
    score = [0, 0]
    for r in post["duel"]["rounds"][:i]:
        if r.get("win") == "left":
            score[0] += 1
        elif r.get("win") == "right":
            score[1] += 1
    return score


def _header(post, frame, d, t, i, intro):
    duel = post["duel"]
    L, R = duel["left"], duel["right"]
    lc, rc = _c(L.get("color"), (90, 170, 255)), _c(R.get("color"), GREEN)
    p = ease_out(t / 0.5) if intro else 1.0
    off = (1 - p) * 300
    # name plates slide in from the sides, a colour bar under each
    for name, col, x, anchor, sgn in ((L["name"], lc, X0, "la", -1), (R["name"], rc, X0 + XW, "ra", 1)):
        f = _fitted(d, name.upper(), 300, 72, 30)
        tw = d.textlength(name.upper(), font=f)
        xx = x + sgn * off
        d.text((xx, SCORE_Y - 40), name.upper(), font=f, fill=_a(col, 255 * p), anchor=anchor)
        bx = xx if anchor == "la" else xx - tw
        d.rounded_rectangle([bx, SCORE_Y + 44, bx + tw, SCORE_Y + 52], radius=4, fill=_a(col, 255 * p))
    if _has_photos(post):
        y0, y1 = PHOTO_BAND
        r = post["duel"]["rounds"][i] if i < len(post["duel"]["rounds"]) else {}
        decided = t > 1.6
        for n, (car, side) in enumerate(((L, "left"), (R, "right"))):
            lost = decided and r.get("win") in ("left", "right") and r.get("win") != side
            cx = X0 + XW * (0.25 + 0.5 * n) + (-1 if n == 0 else 1) * off
            _put_photo(frame, car["photo"], cx, (y0 + y1) / 2, XW / 2 - 10, y1 - y0, alpha=p,
                       grey=lost)
    # the scoreboard between them
    before, after = _score(post, i), _score(post, i + 1)
    shown = after if t >= 1.9 else before
    cx, cy = X0 + XW / 2, SCORE_Y
    d.rounded_rectangle([cx - 120, cy - 62, cx + 120, cy + 62], radius=22, fill=_a(INK, 235 * p),
                        outline=_a(AMBER, 255 * p), width=4)
    for k, (val, x) in enumerate(((shown[0], cx - 62), (shown[1], cx + 62))):
        bump = 1.0
        if after[k] != before[k] and 1.9 < t < 2.4:
            bump = 1 + 0.35 * math.sin((t - 1.9) / 0.5 * math.pi)
        d.text((x, cy), str(val), font=_font(BOLD, int(84 * bump)), fill=_a(WHITE, 255 * p), anchor="mm")
    d.text((cx, cy), "-", font=_font(BOLD, 84), fill=_a(GREY, 255 * p), anchor="mm")


def _value(r, side, k):
    v = r.get(side, "")
    if isinstance(v, (int, float)):
        return r.get("fmt", "{}").format(v * k)
    return str(v)


def _round(post, d, t, i):
    r = post["duel"]["rounds"][i]
    BOX_Y = _box_y(post)
    tall = 0 if _has_photos(post) else 170
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
    count = 1.0  # real numbers only, no rolling counter
    win = r.get("win")
    decided = t > 1.6
    w, gap, y0, y1 = (XW - 40) / 2, 40, BOX_Y + 110, BOX_Y + 300 + tall
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
        f = _fitted(d, text, w - 40, 92 + tall // 4, 36)
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
        d.text((X0 + XW / 2, y1 + 70), r["note"], font=_font(BOLD if tall else MEDIUM, 40 if tall else 36),
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
    duel_ = post["duel"]
    score = _score(post, len(duel_["rounds"]))
    side = "left" if score[0] > score[1] else "right" if score[1] > score[0] else None
    v = duel_.get("verdict", {})
    side = v.get("winner", side)
    car = duel_.get(side) if side else None
    col = _c(car.get("color"), GREEN) if car else AMBER
    top = 650
    if car and car.get("photo"):
        p = ease_out((t - 0.1) / 0.6)
        _put_photo(frame, car["photo"], X0 + XW / 2, 780, XW * 0.8, 260, alpha=p)
        top = 960
    q = _ease_back((t - 0.2) / 0.45)
    if q > 0:
        d.text((X0 + XW / 2, top), "THE WINNER", font=_font(BOLD, 40), fill=_a(AMBER, 255 * min(1, q)), anchor="mm")
        title = car["name"].upper() if car else "IT'S A TIE"
        f = _fitted(d, title, XW, int(150 * max(0.5, q)), 48)
        d.text((X0 + XW / 2, top + 105), title, font=f, fill=_a(col, 255 * min(1, q)), anchor="mm")
        d.text((X0 + XW / 2, top + 215), f"{score[0]} - {score[1]}", font=_font(BOLD, 64),
               fill=_a(WHITE, 255 * min(1, q)), anchor="mm")
    g = ease_out((t - 1.0) / 0.4)
    if g > 0 and v.get("big"):
        cy = top + 410 if top < 900 else top + 330
        d.rounded_rectangle([X0 + 40, cy - 115, X0 + XW - 40, cy + 115], radius=36, fill=_a(PANEL, 245 * g),
                            outline=_a(col, 255 * g), width=5)
        f = _fitted(d, v["big"], XW - 200, 120, 50)
        d.text((X0 + XW / 2, cy - 22), v["big"], font=f, fill=_a(WHITE, 255 * g), anchor="mm")
        if v.get("sub"):
            d.text((X0 + XW / 2, cy + 62), v["sub"].upper(), font=_font(BOLD, 38), fill=_a(col, 255 * g), anchor="mm")
        if v.get("note"):
            d.text((X0 + XW / 2, cy + 160), v["note"], font=_font(MEDIUM, 34),
                   fill=_a(GREY, 255 * ease_out((t - 1.5) / 0.4)), anchor="mm")
    if car:
        _confetti(d, t)


BG = (9, 9, 13)


def _theme(post, frame, t):
    """Fight-night look: near black, each half tinted with its car's colour,
    a bright diagonal seam between them and faint speed lines."""
    duel_ = post["duel"]
    lc, rc = _c(duel_["left"].get("color"), (90, 170, 255)), _c(duel_["right"].get("color"), GREEN)
    bg = Image.new("RGBA", (W, frame.height), (*BG, 255))
    tint = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    g = ImageDraw.Draw(tint)
    h = frame.height
    g.polygon([(0, 0), (W * 0.62, 0), (W * 0.38, h), (0, h)], fill=(*lc, 34))
    g.polygon([(W * 0.62, 0), (W, 0), (W, h), (W * 0.38, h)], fill=(*rc, 34))
    for k in range(9):  # speed lines drifting across
        y = (k * 233 + t * 260) % h
        g.line([(0, y), (W, y - 140)], fill=(255, 255, 255, 10), width=3)
    bg.alpha_composite(tint)
    frame.paste(bg, (0, 0))


def _intro(post, frame, d, t):
    """The first 2 seconds: two colour panels crash together, the names slam
    in, a VS hits the middle with a flash and a shake, then the question."""
    duel_ = post["duel"]
    L, R = duel_["left"], duel_["right"]
    lc, rc = _c(L.get("color"), (90, 170, 255)), _c(R.get("color"), GREEN)
    h = frame.height
    top, bot = 600, 1320
    mid = (top + bot) / 2
    p = ease_out((t - 0.75) / 0.25)            # panels crash in
    hit = max(0.0, 1 - abs(t - 1.05) / 0.12)   # the VS impact
    shake = 14 * hit * math.sin(t * 90)
    lx = -W * (1 - p) + shake
    rx = W * (1 - p) + shake
    d.polygon([(lx, top), (lx + W * 0.66, top), (lx + W * 0.34, bot), (lx, bot)], fill=_a(lc, 235))
    d.polygon([(rx + W * 0.66, top), (rx + W, top), (rx + W, bot), (rx + W * 0.34, bot)], fill=_a(rc, 235))
    d.line([(W * 0.66 + shake, top - 20), (W * 0.34 + shake, bot + 20)], fill=_a(WHITE, 255 * p), width=10)
    if L.get("photo") and R.get("photo"):
        _put_photo(frame, L["photo"], X0 + 200 + lx, mid - 190, 460, 240, alpha=p)
        _put_photo(frame, R["photo"], X0 + XW - 200 + rx, mid + 190, 460, 240, alpha=p)
    q = _ease_back((t - 0.8) / 0.3)
    if q > 0:
        for name, x, y, anchor in ((L["name"], X0 + lx * 0.3, top + 120, "la"),
                                   (R["name"], X0 + XW + rx * 0.3, bot - 120, "ra")):
            f = _fitted(d, name.upper(), XW * 0.62, int(150 * max(0.6, min(1.15, q))), 60)
            d.text((x, y), name.upper(), font=f, fill=_a(WHITE, 255), anchor=anchor[0] + "m",
                   stroke_width=6, stroke_fill=_a(INK, 255))
    v = _ease_back((t - 0.95) / 0.22)
    if v > 0:
        size = int(260 * (1 + 0.6 * max(0.0, 1 - v)))
        d.text((W / 2 + shake, mid), "VS", font=_font(BOLD, size), fill=_a(AMBER, 255), anchor="mm",
               stroke_width=10, stroke_fill=_a(INK, 255))
    if hit > 0:  # white flash on impact
        d.rectangle([0, 0, W, h], fill=(255, 255, 255, int(150 * hit)))
    s = ease_out((t - 1.3) / 0.3)
    if s > 0 and duel_.get("question"):
        text = duel_["question"].upper()
        f = _fitted(d, text, XW - 60, 58, 30)
        tw = d.textlength(text, font=f)
        y = bot + 65 - 30 * (1 - s)
        d.rounded_rectangle([W / 2 - tw / 2 - 30, y - 44, W / 2 + tw / 2 + 30, y + 44], radius=44,
                            fill=_a(WHITE, 255 * s))
        d.text((W / 2, y), text, font=f, fill=_a(INK, 255 * s), anchor="mm")


def duel(post, frame, d, t, i):
    _theme(post, frame, t)
    rounds = post["duel"]["rounds"]
    if post["duel"].get("question"):  # the first scene is the 2-second opener
        if i == 0:
            _intro(post, frame, d, t)
            return
        i -= 1
    if i < len(rounds):
        _header(post, frame, d, t, i, intro=False)
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
    want = len(rounds) + 1 + (1 if duel_.get("question") else 0)
    if len(post.get("slides", [])) - 1 != want:
        errors.append("duel: after the hook, need a slide for the opener (if any), each round and the verdict")
    return errors
