"""A tiny 3D renderer for the animated reels: a perspective camera, flat
shaded boxes and cylinders, drawn with PIL. Objects are convex, so each one
hides its own back faces, and whole objects are painted far to near."""

import math

from PIL import Image, ImageDraw, ImageFilter

LIGHT = (-0.35, 0.55, 0.75)


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def mix(a, b, k):
    k = max(0.0, min(1.0, k))
    return tuple(int(a[n] + (b[n] - a[n]) * k) for n in range(3))


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


class Cam:
    """yaw turns the world round the vertical (z) axis, pitch tips the view
    down onto it; s is pixels per world unit, (ox, oy) the screen origin."""

    def __init__(self, yaw, pitch, s, ox, oy, F=3.2):
        self.a, self.pt = math.radians(yaw), math.radians(pitch)
        self.s, self.F, self.ox, self.oy = s, F, ox, oy

    def view(self, q):
        x, y, z = q
        ca, sa = math.cos(self.a), math.sin(self.a)
        X, Y = x * ca - y * sa, x * sa + y * ca
        cp, sp = math.cos(self.pt), math.sin(self.pt)
        return X, Y * sp - z * cp, Y * cp + z * sp  # screen x, screen y (down), depth (toward viewer)

    def p(self, q):
        X, Ys, D = self.view(q)
        f = self.F / (self.F - D)
        return (self.ox + X * self.s * f, self.oy + Ys * self.s * f)


class Scene:
    def __init__(self, cam):
        self.cam, self.objects, self._open = cam, [], None

    def begin(self, centre, after=None):
        """Starts a new object; its faces are painted together. after: a
        draw(d) callback for details painted on top of it (labels, marks)."""
        self._open = (self.cam.view(centre)[2], [], after)
        self.objects.append(self._open)

    def face(self, pts, col, lit=True, alpha=255):
        if self._open is None:
            self.begin(tuple(sum(p[k] for p in pts) / len(pts) for k in range(3)))
        scr = [self.cam.p(p) for p in pts]
        area = sum(scr[k][0] * scr[(k + 1) % len(scr)][1] - scr[(k + 1) % len(scr)][0] * scr[k][1]
                   for k in range(len(scr)))
        if area >= 0:  # turned away from the camera
            return
        n = _cross(_sub(pts[1], pts[0]), _sub(pts[2], pts[0]))
        ln = math.sqrt(sum(v * v for v in n)) or 1
        k = 0.62 + 0.55 * max(0.0, -sum(a * b / ln for a, b in zip(n, LIGHT))) if lit else 1.0
        self._open[1].append((scr, (*shade(col, k), int(alpha))))

    def box(self, x0, y0, z0, x1, y1, z1, col, after=None):
        self.begin(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), after)
        v = lambda x, y, z: (x, y, z)
        self.face([v(x0, y0, z1), v(x0, y1, z1), v(x1, y1, z1), v(x1, y0, z1)], col)  # top
        self.face([v(x0, y1, z0), v(x1, y1, z0), v(x1, y1, z1), v(x0, y1, z1)], col)  # front
        self.face([v(x1, y0, z0), v(x0, y0, z0), v(x0, y0, z1), v(x1, y0, z1)], col)  # back
        self.face([v(x1, y1, z0), v(x1, y0, z0), v(x1, y0, z1), v(x1, y1, z1)], col)  # right
        self.face([v(x0, y0, z0), v(x0, y1, z0), v(x0, y1, z1), v(x0, y0, z1)], col)  # left
        self.face([v(x0, y0, z0), v(x1, y0, z0), v(x1, y1, z0), v(x0, y1, z0)], col)  # bottom

    def disc(self, x, r, length, col, cap=None, rot=0.0, n=32, after=None, centre=(0.0, 0.0), side=None):
        """A cylinder on the x axis (the shaft line). cap(k, n) gives the
        colour of wedge k of each end face, so marks on it turn with rot;
        side(k, n) does the same for the curved face (tyre tread)."""
        cy, cz = centre
        self.begin((x, cy, cz), after)
        pt = lambda a, s: (x + s, cy + r * math.cos(a), cz + r * math.sin(a))
        h = length / 2
        angs = [rot + 2 * math.pi * k / n for k in range(n + 1)]
        for k in range(n):
            a, b = angs[k], angs[k + 1]
            self.face([pt(a, h), pt(b, h), pt(b, -h), pt(a, -h)], side(k, n) if side else col)
            c = cap(k, n) if cap else col
            self.face([(x + h, cy, cz), pt(b, h), pt(a, h)], c)
            self.face([(x - h, cy, cz), pt(a, -h), pt(b, -h)], c)

    def draw(self, d):
        for _, faces, after in sorted(self.objects, key=lambda o: o[0]):
            for scr, fill in faces:
                d.polygon(scr, fill=fill)
            if after:
                after(d)


def glow(frame, pts, color, radius=60, strength=150, squash=0.55):
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    g = ImageDraw.Draw(layer)
    for x, y in pts:
        g.ellipse([x - radius, y - radius * squash, x + radius, y + radius * squash], fill=(*color, int(strength)))
    frame.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius * 0.5)))
