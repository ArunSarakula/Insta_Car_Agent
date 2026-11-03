"""A visual built from the post's own data, so any topic gets an animated
picture without new drawing code: each slide after the hook carries a
`viz` describing what to draw for its scene.

    {"kind": "bars", "unit": "Rs/km", "items": [{"label": "Petrol", "value": 6.4, "text": "Rs 6.4", "color": "red"}]}
    {"kind": "check", "items": [{"text": "Factory-fitted kit", "ok": true}]}
    {"kind": "number", "value": "8 years", "label": "battery warranty", "sub": "or 1.6 lakh km", "color": "teal"}
    {"kind": "versus", "left": {"title": "Home", "lines": ["Rs 8/unit"], "color": "green"},
                       "right": {"title": "Public DC", "lines": ["Rs 22/unit"], "color": "red"}, "win": "left"}
    {"kind": "gauge", "value": 0.8, "label": "BATTERY HEALTH", "text": "80%", "color": "green"}
    {"kind": "steps", "items": ["Ask for a written estimate", "..."]}
"""

import math

from .design import AMBER, BOLD, GREY, INK, MEDIUM, TEAL, WHITE, _fit, clean
from .motion import GREEN, RED, X0, XW, _font, ease_out

VY = 990
COLORS = {"teal": TEAL, "amber": AMBER, "red": RED, "green": GREEN, "white": WHITE, "grey": GREY,
          "blue": (90, 170, 255)}
PANEL = (30, 38, 52)


def _c(name, default=TEAL):
    return COLORS.get(str(name or "").lower(), default)


def _a(color, alpha):
    return (*color, max(0, min(255, int(alpha))))


def _text(d, xy, text, size, color, alpha=255, anchor="la", font=BOLD):
    d.text(xy, text, font=_font(font, size), fill=_a(color, alpha), anchor=anchor)


def _fitted(d, text, width, size, minimum=24, font=BOLD):
    """The biggest font (up to size) that fits text on one line."""
    for s in range(size, minimum - 1, -2):
        f = _font(font, s)
        if d.textlength(text, font=f) <= width:
            return f
    return _font(font, minimum)


def _tick(d, cx, cy, r, ok, alpha):
    col = GREEN if ok else RED
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_a(col, alpha))
    w = max(5, r // 4)
    if ok:
        d.line([(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.38), (cx + r * 0.5, cy - r * 0.38)],
               fill=_a(INK, alpha), width=w, joint="curve")
    else:
        k = r * 0.4
        d.line([(cx - k, cy - k), (cx + k, cy + k)], fill=_a(INK, alpha), width=w)
        d.line([(cx - k, cy + k), (cx + k, cy - k)], fill=_a(INK, alpha), width=w)


def _bars(d, t, viz):
    items = viz.get("items", [])[:5]
    top = max((float(i.get("value", 0)) for i in items), default=1) or 1
    row = min(130, 560 // max(1, len(items)))
    y0 = VY - 60 + (560 - row * len(items)) // 2
    label_w = 250
    for n, it in enumerate(items):
        p = ease_out((t - 0.2 - n * 0.35) / 0.7)
        if p <= 0:
            continue
        y = y0 + n * row
        col = _c(it.get("color"), TEAL)
        f = _fitted(d, it["label"], label_w - 16, 40)
        d.text((X0, y + 22), it["label"], font=f, fill=_a(WHITE, 255 * p), anchor="lm")
        bx, bw = X0 + label_w, XW - label_w - 10
        d.rounded_rectangle([bx, y, bx + bw, y + 46], radius=23, fill=_a(PANEL, 255 * p))
        w = bw * float(it.get("value", 0)) / top * p
        if w > 46:
            d.rounded_rectangle([bx, y, bx + w, y + 46], radius=23, fill=_a(col, 255))
        label = it.get("text") or str(it.get("value"))
        _text(d, (bx + 6, y + 58), label, 34, col, 255 * ease_out((t - 0.5 - n * 0.35) / 0.4))
    if viz.get("unit"):
        _text(d, (X0 + XW, VY - 110), viz["unit"].upper(), 28, GREY, 255 * ease_out(t / 0.4), "ra")


def _check(d, t, viz):
    items = viz.get("items", [])[:5]
    row = min(124, 580 // max(1, len(items)))
    y0 = VY - 70 + (580 - row * len(items)) // 2
    for n, it in enumerate(items):
        p = ease_out((t - 0.25 - n * 0.45) / 0.4)
        if p <= 0:
            continue
        y = y0 + n * row + 16 * (1 - p)
        d.rounded_rectangle([X0, y, X0 + XW, y + row - 18], radius=26, fill=_a(PANEL, 255 * p))
        cy = y + (row - 18) / 2
        _tick(d, X0 + 52, cy, 30, it.get("ok", True), 255 * p)
        f, lines, lh = _fit(d, clean(it["text"]), BOLD, XW - 130, row - 30, 40, 26, spacing=1.1)
        ty = cy - len(lines) * lh / 2
        for k, line in enumerate(lines):
            d.text((X0 + 104, ty + k * lh), line, font=f, fill=_a(WHITE, 255 * p))


def _steps(d, t, viz):
    items = [{"text": s} if isinstance(s, str) else s for s in viz.get("items", [])][:5]
    row = min(124, 580 // max(1, len(items)))
    y0 = VY - 70 + (580 - row * len(items)) // 2
    for n, it in enumerate(items):
        p = ease_out((t - 0.25 - n * 0.45) / 0.4)
        if p <= 0:
            continue
        y = y0 + n * row
        x = X0 + 30 * (1 - p)
        cy = y + (row - 18) / 2
        d.rounded_rectangle([x, y, X0 + XW, y + row - 18], radius=26, fill=_a(PANEL, 255 * p))
        d.ellipse([x + 22, cy - 30, x + 82, cy + 30], fill=_a(AMBER, 255 * p))
        _text(d, (x + 52, cy), str(n + 1), 36, INK, 255 * p, "mm")
        f, lines, lh = _fit(d, clean(it["text"]), BOLD, XW - 140, row - 30, 40, 26, spacing=1.1)
        ty = cy - len(lines) * lh / 2
        for k, line in enumerate(lines):
            d.text((x + 106, ty + k * lh), line, font=f, fill=_a(WHITE, 255 * p))


def _number(d, t, viz):
    col = _c(viz.get("color"), TEAL)
    cx, cy = X0 + XW // 2, VY + 150
    p = ease_out((t - 0.15) / 0.5)
    pulse = 1 + 0.04 * math.sin(t * 4) * (t > 0.8)
    r = 250 * p * pulse
    if r > 4:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_a(col, 40))
        d.ellipse([cx - r * 0.86, cy - r * 0.86, cx + r * 0.86, cy + r * 0.86], outline=_a(col, 200), width=8)
    value = str(viz.get("value", ""))
    pop = ease_out((t - 0.35) / 0.35)
    if pop > 0:
        f = _fitted(d, value, 400, int(130 * (0.7 + 0.3 * pop)), 40)
        d.text((cx, cy - 20), value, font=f, fill=_a(WHITE, 255 * pop), anchor="mm")
        if viz.get("label"):
            f = _fitted(d, viz["label"].upper(), 380, 34, 20)
            d.text((cx, cy + 75), viz["label"].upper(), font=f, fill=_a(col, 255 * pop), anchor="mm")
    if viz.get("sub"):
        q = ease_out((t - 0.9) / 0.4)
        _text(d, (cx, cy + 290), viz["sub"], 38, GREY, 255 * q, "mm", MEDIUM)


def _card(d, x, w, side, t, start, win):
    p = ease_out((t - start) / 0.45)
    if p <= 0:
        return
    col = _c(side.get("color"), TEAL)
    y0, y1 = VY - 70 + 30 * (1 - p), VY + 480
    if win:
        d.rounded_rectangle([x - 8, y0 - 8, x + w + 8, y1 + 8], radius=36, outline=_a(col, 255 * p), width=8)
    d.rounded_rectangle([x, y0, x + w, y1], radius=30, fill=_a(PANEL, 255 * p))
    d.rounded_rectangle([x, y0, x + w, y0 + 110], radius=30, fill=_a(col, 255 * p))
    d.rectangle([x, y0 + 80, x + w, y0 + 110], fill=_a(col, 255 * p))
    f = _fitted(d, side.get("title", "").upper(), w - 40, 46, 24)
    d.text((x + w / 2, y0 + 55), side.get("title", "").upper(), font=f, fill=_a(INK, 255 * p), anchor="mm")
    y = y0 + 140
    for k, line in enumerate(side.get("lines", [])[:4]):
        q = ease_out((t - start - 0.3 - k * 0.25) / 0.35)
        f2, lines, lh = _fit(d, clean(line), BOLD, w - 50, 140, 38, 24, spacing=1.08)
        for ln in lines:
            d.text((x + 25, y), ln, font=f2, fill=_a(WHITE, 255 * q))
            y += lh
        y += 22
    if win and t > start + 1.2:
        q = ease_out((t - start - 1.2) / 0.3)
        f3 = _font(BOLD, 30)
        tw = d.textlength("WINNER", font=f3)
        d.rounded_rectangle([x + w / 2 - tw / 2 - 20, y1 - 30, x + w / 2 + tw / 2 + 20, y1 + 24], radius=27,
                            fill=_a(col, 255 * q))
        d.text((x + w / 2, y1 - 3), "WINNER", font=f3, fill=_a(INK, 255 * q), anchor="mm")


def _versus(d, t, viz):
    gap = 60
    w = (XW - gap) // 2
    win = viz.get("win")
    _card(d, X0, w, viz.get("left", {}), t, 0.15, win == "left")
    _card(d, X0 + w + gap, w, viz.get("right", {}), t, 0.45, win == "right")
    p = ease_out((t - 0.7) / 0.3)
    if p > 0:
        cx, cy = X0 + w + gap // 2, VY + 200
        d.ellipse([cx - 44, cy - 44, cx + 44, cy + 44], fill=_a(AMBER, 255 * p))
        _text(d, (cx, cy), "VS", 34, INK, 255 * p, "mm")


def _gauge(d, t, viz):
    col = _c(viz.get("color"), GREEN)
    cx, cy, r = X0 + XW // 2, VY + 250, 300
    box = [cx - r, cy - r, cx + r, cy + r]
    for k, zc in enumerate((RED, AMBER, GREEN)):
        d.arc(box, 180 + k * 60, 180 + (k + 1) * 60, fill=_a(zc, 110), width=46)
    level = float(viz.get("value", 0.5)) * ease_out((t - 0.2) / 1.2)
    d.arc(box, 180, 180 + 180 * level, fill=_a(col, 255), width=46)
    a = math.pi + math.pi * level
    d.line([(cx, cy), (cx + (r - 70) * math.cos(a), cy + (r - 70) * math.sin(a))], fill=_a(WHITE, 255), width=12)
    d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=_a(WHITE, 255))
    q = ease_out((t - 0.9) / 0.4)
    if viz.get("text"):
        _text(d, (cx, cy + 90), viz["text"], 96, WHITE, 255 * q, "mm")
    if viz.get("label"):
        _text(d, (cx, cy + 175), viz["label"].upper(), 34, col, 255 * q, "mm")


KINDS = {"bars": _bars, "check": _check, "number": _number, "versus": _versus, "gauge": _gauge,
         "steps": _steps}


def board(post, frame, d, t, i):
    """Scene i draws the viz of slide i + 1."""
    slides = post["slides"][1:]
    if not slides:
        return
    viz = slides[min(i, len(slides) - 1)].get("viz") or {"kind": "number", "value": "?"}
    KINDS.get(viz.get("kind"), _number)(d, t, viz)


board.wants_post = True


def check_viz(post) -> list[str]:
    """Problems with a board post's viz data, for tests and before rendering."""
    errors = []
    for n, s in enumerate(post.get("slides", [])[1:], 2):
        viz = s.get("viz")
        if not viz:
            errors.append(f"slide {n}: no viz")
        elif viz.get("kind") not in KINDS:
            errors.append(f"slide {n}: unknown kind {viz.get('kind')}")
    return errors

