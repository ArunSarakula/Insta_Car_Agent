"""Reel formats. Each reel uses one of these, and the weekly plan rotates
them so no two reels in a row look alike (YouTube treats a channel of
identical-looking videos as reused content).

Each style turns the post's slides into frames plus how long each frame
stays on screen, and names the transition between frames."""

from PIL import Image, ImageDraw

from .design import (AMBER, BOLD, GREY, INK, MEDIUM, NAVY, REEL, REEL_SAFE_BOTTOM, REEL_SAFE_RIGHT,
                     REEL_SAFE_TOP, TEAL, WHITE, _draw_lines, _fit, _seconds, clean, render_slide)
from PIL import ImageFont

STYLES = ["explainer", "myth_fact", "versus", "quiz"]

W, H = REEL
X0 = 80
XW = W - X0 - REEL_SAFE_RIGHT - 40
TOP, BOT = REEL_SAFE_TOP, H - REEL_SAFE_BOTTOM
RED = (235, 70, 70)
GREEN = (40, 200, 120)


def _font(size, bold=True):
    return ImageFont.truetype(BOLD if bold else MEDIUM, size)


def _line_font(d, text, width, start, minimum):
    """Largest size at which `text` fits on one line."""
    size = start
    while size > minimum and d.textlength(text, font=_font(size)) > width:
        size -= 2
    return _font(size)


def _canvas(bg):
    im = Image.new("RGB", (W, H), bg)
    return im, ImageDraw.Draw(im)


def _text(d, text, y, color, start, minimum=36, height=400, font=BOLD, x=X0, width=XW):
    return _draw_lines(d, x, y, _fit(d, clean(text), font, width, height, start, minimum), color)


def _handle(d, y, handle, color=TEAL):
    d.text((X0, y), handle, font=_font(36), fill=color)


def _pill(d, y, label, bg):
    f = _font(56)
    w = d.textlength(label, font=f)
    d.rounded_rectangle([X0, y, X0 + w + 56, y + 92], radius=46, fill=bg)
    d.text((X0 + 28, y + 16), label, font=f, fill=WHITE)
    return y + 92


def hook_frames(heading, tag=""):
    """The first second: the hook slams in chunk by chunk, black on amber,
    so it stands out from the dark reels around it and something changes
    on screen every few tenths of a second. `tag` (e.g. MYTH OR FACT?)
    sits above it so a myth never reads as advice. Returns frames, durations."""
    words = clean(heading).split()
    if not words:
        return [], []
    n = 1 if len(words) <= 2 else (2 if len(words) <= 4 else 3)
    size = -(-len(words) // n)
    chunks = [" ".join(words[:size * (k + 1)]) for k in range(n)]
    frames = []
    for text in chunks:
        im, d = _canvas(AMBER)
        full = _fit(d, clean(heading), BOLD, XW, 700, 130, 60)  # sized for the full line
        font, lines, line_h = _fit(d, text, BOLD, XW, 700, full[0].size, 60)
        y = (TOP + BOT) // 2 - len(full[1]) * line_h // 2
        if tag:
            f = _font(52)
            d.rounded_rectangle([X0, y - 150, X0 + d.textlength(tag, font=f) + 52, y - 64], radius=43, fill=INK)
            d.text((X0 + 26, y - 136), tag, font=f, fill=AMBER)
        _draw_lines(d, X0, y, (font, lines, line_h), INK)
        frames.append(im)
    return frames, [0.35] * (n - 1) + [0.75]


def explainer(post, handle, tmp):
    """The original look: one idea per slide, navy and teal."""
    slides = post["slides"]
    images = []
    for i, s in enumerate(slides):
        src = render_slide(s, tmp / f"src-{i}.jpg", REEL, i + 1, len(slides), handle)
        with Image.open(src) as im:
            images.append(im.copy())
        src.unlink()
    return (images,
            [_seconds(s, first=i == 0) for i, s in enumerate(slides)], "slideleft")


def myth_fact(post, handle, tmp):
    """Slide 1 is the myth, slide 2 the fact, any others are tips."""
    slides = post["slides"]
    myth, fact, tips = slides[0], slides[1], slides[2:]
    frames, durations = [], []
    dark = (40, 14, 20)

    im, d = _canvas(dark)
    y = _pill(d, TOP + 120, "MYTH", RED)
    y = _text(d, myth["heading"], y + 60, WHITE, 96, height=500)
    if myth.get("body"):
        y = _text(d, myth["body"], y + 30, GREY, 48, height=120, font=MEDIUM)
    _handle(d, y + 50, handle)
    frames.append(im); durations.append(1.8)

    im, d = _canvas(dark)
    y = _pill(d, TOP + 120, "MYTH", RED)
    y0 = y + 60
    y = _text(d, myth["heading"], y0, (120, 90, 95), 96, height=500)
    d.line([(X0 - 10, y - 30), (X0 + XW * 0.85, y0 + 30)], fill=RED, width=14)
    y = _pill(d, y + 60, "FACT", GREEN)
    y = _text(d, f"{fact['heading']}. {fact['body']}".strip(". "), y + 40, WHITE, 52, height=420, font=MEDIUM)
    _handle(d, y + 40, handle)
    frames.append(im); durations.append(_seconds(fact) + 1.2)

    for tip in tips:
        im, d = _canvas((10, 30, 22))
        y = _pill(d, TOP + 120, "TIP", GREEN)
        y = _text(d, tip["heading"], y + 60, WHITE, 80, height=420)
        if tip.get("body"):
            y = _text(d, tip["body"], y + 30, GREY, 48, height=300, font=MEDIUM)
        _handle(d, y + 50, handle)
        frames.append(im); durations.append(_seconds(tip))
    return frames, durations, "fade"


def versus(post, handle, tmp):
    """Split screen. Slide 1 is the question; every later slide is one row,
    heading = what is compared, body = "left value | right value"."""
    left, right = clean(post.get("versus_left", "")).upper(), clean(post.get("versus_right", "")).upper()
    rows = []
    for s in post["slides"][1:]:
        a, _, b = s.get("body", "").partition("|")
        rows.append((clean(s["heading"]), clean(a), clean(b)))
    mid = W // 2 - 20
    rcx = mid + (W - mid - REEL_SAFE_RIGHT) / 2
    lcx = mid / 2 + 20
    frames, durations = [], []
    for upto in range(len(rows) + 1):
        im, d = _canvas(NAVY)
        d.rectangle([0, 0, mid, H], fill=(0, 70, 64))
        d.rectangle([mid, 0, W, H], fill=(80, 55, 10))
        right_edge = W - REEL_SAFE_RIGHT
        for cx, room, name in (((mid - 70) / 2, mid - 70 - 40, left),
                               ((mid + 70 + right_edge) / 2, right_edge - mid - 70 - 40, right)):
            f = _line_font(d, name, room, 76, 28)
            d.text((cx, TOP + 90), name, font=f, fill=WHITE, anchor="mm")
        d.ellipse([mid - 70, TOP + 20, mid + 70, TOP + 160], fill=NAVY, outline=WHITE, width=6)
        d.text((mid, TOP + 90), "VS", font=_font(56), fill=AMBER, anchor="mm")
        y = TOP + 230
        row_h = min(190, (BOT - 80 - y) // max(1, len(rows)))
        for label, a, b in rows[:upto]:
            d.text((W / 2 - 50, y), label.upper(), font=_font(32), fill=GREY, anchor="mm")
            for cx, val in ((lcx, a), (rcx, b)):
                f = _line_font(d, val, mid - 70, 46, 24)
                d.text((cx, y + 66), val, font=f, fill=WHITE, anchor="mm")
            y += row_h
        if upto == 0:
            _text(d, post["slides"][0]["heading"], TOP + 420, WHITE, 80, height=360,
                  x=X0, width=XW)
        d.text((W / 2 - 50, BOT - 40), handle, font=_font(36), fill=TEAL, anchor="mm")
        frames.append(im)
        durations.append(2.2 if upto < len(rows) else 3.4)
    return frames, durations, "wipeup"


def quiz(post, handle, tmp):
    """Question, 3 options, a 3-2-1 countdown, then the answer.
    Slide 1 heading is the question; slide 2 explains the answer."""
    question = post["slides"][0]["heading"]
    explain = post["slides"][1] if len(post["slides"]) > 1 else {"heading": "", "body": ""}
    options = [clean(o) for o in post.get("quiz_options", [])][:3]
    answer = post.get("quiz_answer", 0)
    bg = (24, 18, 44)
    frames, durations = [], []
    for stage in ["ask", 3, 2, 1, "answer"]:
        im, d = _canvas(bg)
        d.text((X0, TOP + 40), "QUIZ", font=_font(44), fill=AMBER)
        y = _text(d, question, TOP + 100, WHITE, 76, height=330)
        y = max(y + 40, TOP + 420)
        for i, o in enumerate(options):
            right = stage == "answer" and i == answer
            wrong = stage == "answer" and i != answer
            fill = GREEN if right else ((60, 50, 80) if wrong else (48, 40, 82))
            d.rounded_rectangle([X0, y, X0 + XW, y + 110], radius=28, fill=fill)
            f = _line_font(d, f"{'ABC'[i]}. {o}", XW - 72, 46, 26)
            d.text((X0 + 36, y + 55), f"{'ABC'[i]}. {o}", font=f,
                   fill=(150, 140, 170) if wrong else WHITE, anchor="lm")
            y += 140
        if isinstance(stage, int):
            cx = W - REEL_SAFE_RIGHT - 110
            d.ellipse([cx - 70, y + 10, cx + 70, y + 150], outline=AMBER, width=8)
            d.text((cx, y + 80), str(stage), font=_font(80), fill=AMBER, anchor="mm")
            y += 160
        if stage == "answer":
            y = _text(d, f"{explain['heading']}. {explain['body']}".strip(". "), y + 10, WHITE, 46,
                      height=300, font=MEDIUM)
        _handle(d, y + 30, handle)
        frames.append(im)
        durations.append({"ask": 2.6, "answer": _seconds(explain) + 1.5}.get(stage, 1.0))
    return frames, durations, "fade"


def usable(post) -> str:
    """The post's style if it has what that style needs, else explainer."""
    style, slides = post.get("reel_style", "explainer"), post.get("slides", [])
    if style == "myth_fact" and len(slides) >= 2:
        return style
    if style == "versus" and post.get("versus_left") and post.get("versus_right") and \
            len(slides) >= 3 and all("|" in s.get("body", "") for s in slides[1:]):
        return style
    if style == "quiz" and len(post.get("quiz_options", [])) == 3 and \
            post.get("quiz_answer") in (0, 1, 2) and slides:
        return style
    return "explainer"


HOOK_TAG = {"myth_fact": "MYTH OR FACT?", "quiz": "QUIZ"}

RENDER = {"explainer": explainer, "myth_fact": myth_fact, "versus": versus, "quiz": quiz}
