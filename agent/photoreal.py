"""Photo-style thumbnails drawn from scratch (no stock photos): soft focus,
light bokeh, condensation droplets and glowing 3D lettering, so a cover
looks like a real camera shot rather than a flat diagram."""

import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from .design import AMBER, BOLD, WHITE, _fit, clean
from .motion import H, RED, W, X0, _font

RNG_SEED = 7


def _night_road(rng):
    """Sharp view through the windshield: a wet road at dusk with tail
    lights, street lamps and their reflections."""
    im = Image.new("RGB", (W, H))
    a = np.zeros((H, W, 3))
    yy = np.linspace(0, 1, H)[:, None]
    a[..., 0] = 18 + 30 * yy
    a[..., 1] = 24 + 28 * yy
    a[..., 2] = 48 + 20 * yy
    im = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(im, "RGBA")
    hz = int(H * 0.55)
    d.polygon([(W * 0.42, hz), (W * 0.58, hz), (W * 1.1, H), (-W * 0.1, H)], fill=(30, 32, 40, 255))
    lights = []
    for _ in range(26):  # street lamps and far traffic
        x, y = rng.uniform(0, W), rng.uniform(H * 0.32, hz - 20)
        r = rng.uniform(6, 20) * (0.6 + (y - H * 0.32) / (hz - H * 0.32))
        col = [(255, 190, 90), (255, 230, 180), (255, 120, 60), (200, 220, 255)][rng.integers(0, 4)]
        lights.append((x, y, r, col))
    cy = H * 0.47  # the car ahead: a dark body with two tail lights
    d.rounded_rectangle([W * 0.36, cy - 60, W * 0.64, cy + 70], radius=30, fill=(12, 13, 18, 255))
    d.rounded_rectangle([W * 0.40, cy - 110, W * 0.60, cy - 50], radius=24, fill=(16, 18, 24, 255))
    for x in (W * 0.39, W * 0.61):
        lights.append((x, cy - 10, 24, (255, 30, 30)))
    glow = Image.new("RGB", (W, H))
    refl = Image.new("RGB", (W, H))
    gd, rd = ImageDraw.Draw(glow), ImageDraw.Draw(refl)
    for x, y, r, col in lights:
        gd.ellipse([x - r, y - r, x + r, y + r], fill=col)
        rd.line([(x, max(y + r, hz)), (x, min(H, hz + (hz - y) * 0.9 + 40))], fill=tuple(int(c * 0.3) for c in col),
                width=int(r * 0.6))  # streaky reflection on the wet road
    im = ImageChops.add(im, glow.filter(ImageFilter.GaussianBlur(2)))
    im = ImageChops.add(im, glow.filter(ImageFilter.GaussianBlur(30)))
    im = ImageChops.add(im, refl.filter(ImageFilter.GaussianBlur(10)))
    return im


def _droplets(rng, mask, n=5200):
    """Condensation: many small beads, each with a dark rim and a bright
    highlight, denser towards the bottom of the glass."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    m = np.asarray(mask)
    for _ in range(n):
        y = int(H * (1 - rng.random() ** 1.6))
        x = int(rng.uniform(0, W))
        if m[min(H - 1, y), min(W - 1, x)] < 128:
            continue
        r = rng.uniform(2, 9) if rng.random() > 0.08 else rng.uniform(10, 18)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(225, 232, 242, 45), outline=(60, 66, 80, 70),
                  width=max(1, int(r / 5)))
        h = r * 0.4
        d.ellipse([x - r * 0.45 - h / 2, y - r * 0.45 - h / 2, x - r * 0.45 + h / 2, y - r * 0.45 + h / 2],
                  fill=(255, 255, 255, 220))
    return layer.filter(ImageFilter.GaussianBlur(0.7))


def _title_3d(im, text, y, color, size):
    """Thick extruded lettering with a soft drop shadow."""
    d = ImageDraw.Draw(im)
    f, lines, line_h = _fit(d, clean(text).upper(), BOLD, W - 2 * X0, 2000, size, size, spacing=1.02)
    for line in lines:
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).text((W // 2 + 10, y + 18), line, font=f, fill=(0, 0, 0, 200), anchor="ma")
        im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))
        dark = tuple(int(c * 0.45) for c in color)
        for k in range(10, 0, -1):  # extrusion
            d.text((W // 2 + k * 0.9, y + k), line, font=f, fill=(*dark, 255), anchor="ma")
        d.text((W // 2, y), line, font=f, fill=(*color, 255), anchor="ma", stroke_width=3,
               stroke_fill=(20, 20, 24, 255))
        y += line_h
    return y


def fog_photo_thumbnail(post, path, handle="@decodethedrive"):
    from .motion_fog import demister_icon
    rng = np.random.default_rng(RNG_SEED)
    sharp = _night_road(rng)
    # fogged glass: heavy blur, a milky haze with uneven density
    blurred = sharp.filter(ImageFilter.GaussianBlur(26))
    haze = np.asarray(Image.fromarray((rng.random((24, 14)) * 255).astype(np.uint8))
                      .resize((W, H), Image.BICUBIC), float) / 255
    fog = np.asarray(blurred, float) * (0.75 - 0.15 * haze[..., None]) * 1.4 + 190 * (0.32 + 0.12 * haze[..., None])
    fogged = Image.fromarray(np.clip(fog, 0, 255).astype(np.uint8))
    # a hand-wiped streak across the middle shows the sharp road behind
    wipe = Image.new("L", (W, H), 0)
    pts = [(W * 0.08 + W * 0.84 * k / 30, H * 0.47 + 60 * math.sin(k / 30 * 6.5)) for k in range(31)]
    ImageDraw.Draw(wipe).line(pts, fill=255, width=230, joint="curve")
    wipe = wipe.filter(ImageFilter.GaussianBlur(22))
    glass = Image.composite(sharp, fogged, wipe).convert("RGBA")
    # droplets on the fogged part, and drips running down from the streak
    glass.alpha_composite(_droplets(rng, ImageChops.invert(wipe)))
    drips = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(drips)
    for _ in range(14):
        x = rng.uniform(W * 0.1, W * 0.9)
        y0 = H * 0.47 + 60 * math.sin((x - W * 0.08) / (W * 0.84) * 6.5) + 120
        ln = rng.uniform(80, 320)
        dd.line([(x, y0), (x + rng.uniform(-8, 8), y0 + ln)], fill=(235, 240, 250, 120), width=int(rng.uniform(4, 9)))
        dd.ellipse([x - 8, y0 + ln - 8, x + 8, y0 + ln + 8], fill=(240, 245, 255, 170))
    glass.alpha_composite(drips.filter(ImageFilter.GaussianBlur(1.2)))
    # the car around the glass: dark pillars and a dashboard with a lit demister button
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    fd.polygon([(0, 0), (90, 0), (0, H * 0.75)], fill=(10, 11, 14, 255))
    fd.polygon([(W, 0), (W - 90, 0), (W, H * 0.75)], fill=(10, 11, 14, 255))
    dash_top = int(H * 0.82)
    fd.rectangle([0, dash_top, W, H], fill=(14, 15, 19, 255))
    fd.ellipse([-200, dash_top - 60, W + 200, dash_top + 120], fill=(14, 15, 19, 255))
    glass.alpha_composite(frame)
    bx, by, bs = W // 2 - 70, dash_top + 40, 140
    lit = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lit)
    ld.rounded_rectangle([bx, by, bx + bs, by + bs], radius=26, fill=(28, 30, 36, 255), outline=(60, 64, 72, 255),
                         width=4)
    demister_icon(ld, bx + 24, by + 18, 92, AMBER)
    glow = lit.filter(ImageFilter.GaussianBlur(18))
    glass.alpha_composite(glow)
    glass.alpha_composite(lit)
    # vignette
    yy, xx = np.mgrid[0:H, 0:W]
    v = np.clip(1.25 - np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2), 0.35, 1)
    arr = np.asarray(glass.convert("RGB"), float) * v[..., None]
    out = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    text = post.get("thumbnail_text") or "Windshield | fogging up?"
    top, _, accent = text.partition("|")
    y = 170
    y = _title_3d(out, top, y, WHITE, 150)
    _title_3d(out, accent, y, AMBER, 150)
    d = ImageDraw.Draw(out)
    tag = "INSIDE OR OUTSIDE?"
    f = _font(BOLD, 52)
    tw = d.textlength(tag, font=f)
    d.rounded_rectangle([(W - tw) / 2 - 34, H * 0.73, (W + tw) / 2 + 34, H * 0.73 + 92], radius=46, fill=(*RED, 255))
    d.text((W / 2, H * 0.73 + 18), tag, font=f, fill=(*WHITE, 255), anchor="ma")
    out.convert("RGB").save(path, "JPEG", quality=92)
    return path


def _fogged(rng, sharp, density=1.0):
    """The same scene seen through misted glass."""
    blurred = sharp.filter(ImageFilter.GaussianBlur(26))
    haze = np.asarray(Image.fromarray((rng.random((24, 14)) * 255).astype(np.uint8))
                      .resize((W, H), Image.BICUBIC), float) / 255
    mix = (0.32 + 0.12 * haze[..., None]) * density
    fog = np.asarray(blurred, float) * (1 - mix) * 1.15 + 200 * mix
    return Image.fromarray(np.clip(fog, 0, 255).astype(np.uint8))


def _day_road(rng):
    """Overcast, rainy highway in daytime: grey sky, tree line, wet road
    with lane marks and a car ahead with its tail lights on."""
    yy = np.linspace(0, 1, H)[:, None, None]
    sky = np.array([150, 165, 180]) * (1 - yy) + np.array([95, 105, 115]) * yy
    im = Image.fromarray(np.broadcast_to(sky, (H, W, 3)).astype(np.uint8))
    d = ImageDraw.Draw(im, "RGBA")
    hz = int(H * 0.50)
    for k in range(60):  # tree line
        x = rng.uniform(-50, W + 50)
        r = rng.uniform(40, 110)
        d.ellipse([x - r, hz - r * 1.6, x + r, hz + 20], fill=(48, 66, 52, 255))
    d.rectangle([0, hz, W, H], fill=(70, 78, 84, 255))
    d.polygon([(W * 0.44, hz), (W * 0.56, hz), (W * 1.2, H), (-W * 0.2, H)], fill=(52, 56, 62, 255))
    for k in range(8):  # dashed centre line in perspective
        t0, t1 = (k / 8) ** 1.8, ((k + 0.5) / 8) ** 1.8
        y0, y1 = hz + (H - hz) * t0, hz + (H - hz) * t1
        w0, w1 = 3 + 30 * t0, 3 + 30 * t1
        d.polygon([(W / 2 - w0, y0), (W / 2 + w0, y0), (W / 2 + w1, y1), (W / 2 - w1, y1)], fill=(235, 235, 225, 255))
    cy = hz + 90  # car ahead
    d.rounded_rectangle([W * 0.33, cy - 70, W * 0.67, cy + 60], radius=26, fill=(36, 40, 48, 255))
    d.rounded_rectangle([W * 0.38, cy - 140, W * 0.62, cy - 60], radius=26, fill=(44, 50, 60, 255))
    d.rectangle([W * 0.40, cy - 130, W * 0.60, cy - 72], fill=(90, 105, 120, 255))
    d.rectangle([W * 0.30, cy + 50, W * 0.70, cy + 80], fill=(20, 22, 26, 255))
    glow = Image.new("RGB", (W, H))
    gd = ImageDraw.Draw(glow)
    for x in (W * 0.36, W * 0.64):
        gd.rounded_rectangle([x - 40, cy - 40, x + 40, cy - 10], radius=10, fill=(255, 40, 40))
    for x, y in ((W * 0.12, hz + 10), (W * 0.2, hz + 4), (W * 0.85, hz + 6)):  # oncoming headlights
        gd.ellipse([x - 12, y - 8, x + 12, y + 8], fill=(255, 245, 220))
    im = ImageChops.add(im, glow.filter(ImageFilter.GaussianBlur(3)))
    im = ImageChops.add(im, glow.filter(ImageFilter.GaussianBlur(28)))
    # wet road reflection of the tail lights
    refl = glow.transpose(Image.FLIP_TOP_BOTTOM).crop((0, H - 2 * cy, W, 2 * H - 2 * cy)).filter(ImageFilter.GaussianBlur(18))
    return ImageChops.add(im, ImageChops.multiply(refl, Image.new("RGB", (W, H), (90, 90, 90))))


def _cabin(im, dash_frac=0.82, button=True, size=140):
    """Dark A-pillars and dashboard around the glass, with the lit demister key."""
    from .motion_fog import demister_icon
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    fd.polygon([(0, 0), (90, 0), (0, H * 0.75)], fill=(10, 11, 14, 255))
    fd.polygon([(W, 0), (W - 90, 0), (W, H * 0.75)], fill=(10, 11, 14, 255))
    dash_top = int(H * dash_frac)
    fd.rectangle([0, dash_top, W, H], fill=(16, 17, 21, 255))
    fd.ellipse([-200, dash_top - 60, W + 200, dash_top + 120], fill=(16, 17, 21, 255))
    im.alpha_composite(frame)
    if button:
        bx, by = W // 2 - size // 2, dash_top + 50
        lit = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lit)
        ld.rounded_rectangle([bx, by, bx + size, by + size], radius=size // 5, fill=(30, 32, 38, 255),
                             outline=(70, 74, 82, 255), width=4)
        demister_icon(ld, bx + size * 17 // 100, by + size * 13 // 100, size * 66 // 100, AMBER)
        im.alpha_composite(lit.filter(ImageFilter.GaussianBlur(size / 7)))
        im.alpha_composite(lit)
        return bx, by
    return None


def _vignette(im, lo=0.4):
    yy, xx = np.mgrid[0:H, 0:W]
    v = np.clip(1.25 - np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2), lo, 1)
    return Image.fromarray((np.asarray(im.convert("RGB"), float) * v[..., None]).astype(np.uint8)).convert("RGBA")


def _red_pill(im, text, y, size=52):
    d = ImageDraw.Draw(im)
    f = _font(BOLD, size)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle([(W - tw) / 2 - 34, y, (W + tw) / 2 + 34, y + size * 1.75], radius=size, fill=(*RED, 255))
    d.text((W / 2, y + size * 0.35), text, font=f, fill=(*WHITE, 255), anchor="ma")


def fog_split_thumbnail(post, path, handle="@decodethedrive"):
    """Before / after: the left half fogged with droplets, the right half
    crystal clear, split by a bright line."""
    rng = np.random.default_rng(11)
    sharp = _day_road(rng)
    fogged = _fogged(rng, sharp, 1.4)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rectangle([W // 2, 0, W, H], fill=255)
    glass = Image.composite(sharp, fogged, mask.filter(ImageFilter.GaussianBlur(3))).convert("RGBA")
    glass.alpha_composite(_droplets(rng, ImageChops.invert(mask), 3000))
    _cabin(glass, 0.84, button=False)
    out = _vignette(glass, 0.5)
    d = ImageDraw.Draw(out)
    d.line([(W // 2, 0), (W // 2, int(H * 0.84))], fill=(255, 255, 255, 255), width=8)
    f = _font(BOLD, 56)
    for x, label, col in ((W * 0.27, "BEFORE", RED), (W * 0.73, "AFTER", (40, 200, 120))):
        tw = d.textlength(label, font=f)
        d.rounded_rectangle([x - tw / 2 - 28, H * 0.70, x + tw / 2 + 28, H * 0.70 + 90], radius=45, fill=(*col, 255))
        d.text((x, H * 0.70 + 16), label, font=f, fill=(*WHITE, 255), anchor="ma")
    y = _title_3d(out, "Foggy", 190, WHITE, 170)
    _title_3d(out, "windshield?", y, AMBER, 118)
    d.text((W // 2, H - 150), handle, font=_font(BOLD, 46), fill=(255, 255, 255, 230), anchor="ma")
    out.convert("RGB").save(path, "JPEG", quality=92)
    return path


def fog_button_thumbnail(post, path, handle="@decodethedrive"):
    """Close-up: a fully fogged windshield and one big glowing demister key
    with an arrow pointing at it."""
    rng = np.random.default_rng(5)
    sharp = _night_road(rng)
    glass = _fogged(rng, sharp, 1.5).convert("RGBA")
    glass.alpha_composite(_droplets(rng, Image.new("L", (W, H), 255), 4200))
    bx, by = _cabin(glass, 0.62, button=True, size=300)
    out = _vignette(glass, 0.45)
    y = _title_3d(out, "Press", 170, WHITE, 170)
    _title_3d(out, "this button", y, AMBER, 140)
    d = ImageDraw.Draw(out)
    ax = W // 2  # arrow down to the key
    d.line([(ax, by - 230), (ax, by - 60)], fill=(*RED, 255), width=26)
    d.polygon([(ax - 60, by - 90), (ax + 60, by - 90), (ax, by - 10)], fill=(*RED, 255))
    _red_pill(out, "FOGGY WINDSHIELD?", int(H * 0.86) - 40, 50)
    out.convert("RGB").save(path, "JPEG", quality=92)
    return path


def fog_written_thumbnail(post, path, handle="@decodethedrive"):
    """'FOG?' written by a finger on the misted glass, the clear road
    showing through the letters, with drips running down."""
    rng = np.random.default_rng(21)
    sharp = _day_road(rng)
    fogged = _fogged(rng, sharp, 1.7)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    f = _font(BOLD, 300)
    md.text((W // 2, int(H * 0.36)), "FOG?", font=f, fill=255, anchor="ma")
    mask = mask.filter(ImageFilter.GaussianBlur(6))
    glass = Image.composite(sharp, fogged, mask).convert("RGBA")
    glass.alpha_composite(_droplets(rng, ImageChops.invert(mask.point(lambda v: 255 if v > 20 else 0)), 3600))
    drips = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(drips)
    box = mask.getbbox()
    for _ in range(12):
        x = rng.uniform(box[0] + 20, box[2] - 20)
        y0 = box[3] - 30
        ln = rng.uniform(60, 260)
        dd.line([(x, y0), (x, y0 + ln)], fill=(230, 236, 245, 150), width=int(rng.uniform(5, 10)))
        dd.ellipse([x - 9, y0 + ln - 9, x + 9, y0 + ln + 9], fill=(240, 245, 255, 190))
    glass.alpha_composite(drips.filter(ImageFilter.GaussianBlur(1.5)))
    _cabin(glass, 0.84, button=True, size=150)
    out = _vignette(glass, 0.5)
    y = _title_3d(out, "Inside or", 170, WHITE, 130)
    _title_3d(out, "outside?", y, AMBER, 130)
    out.convert("RGB").save(path, "JPEG", quality=92)
    return path


def _photo_base(photo):
    """The owner's own photo, letterbox bars trimmed, filled to 9:16 and
    given a little extra contrast so it reads on a small screen."""
    from PIL import ImageEnhance, ImageOps
    im = ImageOps.exif_transpose(Image.open(photo)).convert("RGB")
    rows = np.where(np.asarray(im.convert("L"), float).mean(1) > 12)[0]
    im = im.crop((0, rows[0] + 2, im.width, rows[-1] - 2))
    im = ImageOps.fit(im, (W, H), Image.LANCZOS)
    im = ImageEnhance.Contrast(im).enhance(1.25)
    yy = np.linspace(0, 1, H)[:, None, None]  # darker at the top behind the title
    shade = np.clip(1 - 0.45 * np.clip(1 - yy / 0.42, 0, 1), 0, 1)
    return Image.fromarray((np.asarray(im, float) * shade).astype(np.uint8)).convert("RGBA")


def _lit_key(im, cx, y, size):
    from .motion_fog import demister_icon
    lit = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lit)
    x = cx - size // 2
    ld.rounded_rectangle([x, y, x + size, y + size], radius=size // 5, fill=(26, 28, 34, 255),
                         outline=(80, 84, 92, 255), width=5)
    demister_icon(ld, x + size * 17 // 100, y + size * 13 // 100, size * 66 // 100, AMBER)
    im.alpha_composite(lit.filter(ImageFilter.GaussianBlur(size / 6)))
    im.alpha_composite(lit)


def fog_real_thumbnail(post, path, handle="@decodethedrive", photo=None, variant="question"):
    """Thumbnail on the owner's real fogged-windshield photo."""
    out = _photo_base(photo)
    if variant == "button":
        y = _title_3d(out, "Press", 170, WHITE, 170)
        _title_3d(out, "this button", y, AMBER, 140)
        key_y = int(H * 0.70)
        _lit_key(out, W // 2, key_y, 280)
        d = ImageDraw.Draw(out)
        d.line([(W // 2, key_y - 250), (W // 2, key_y - 70)], fill=(*RED, 255), width=26)
        d.polygon([(W // 2 - 60, key_y - 100), (W // 2 + 60, key_y - 100), (W // 2, key_y - 15)], fill=(*RED, 255))
        _red_pill(out, "FOGGY WINDSHIELD?", int(H * 0.47), 54)
    else:
        text = post.get("thumbnail_text") or "Windshield | fogging up?"
        top, _, accent = text.partition("|")
        y = _title_3d(out, top, 170, WHITE, 150)
        _title_3d(out, accent, y, AMBER, 150)
        _red_pill(out, "INSIDE OR OUTSIDE?", int(H * 0.60), 54)
        _lit_key(out, W // 2, int(H * 0.76), 200)
    out.convert("RGB").save(path, "JPEG", quality=92)
    return path
