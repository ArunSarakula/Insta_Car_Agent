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
