"""Shared components (workflow §5): stems, serifs, the reverse-rain drop and
the diamond. Every glyph is assembled from these so the system stays a system.
"""
from .geom import Outline, Shape, poly, rect, union_all
from .params import *  # noqa: F401,F403


class G:
    """A drawn glyph: list of overlapping parts, cut-outs, and an advance."""

    def __init__(self, parts, adv, cuts=None):
        self.parts = parts
        self.adv = adv
        self.cuts = cuts or []

    def shape(self):
        s = union_all(self.parts)
        for c in self.cuts:
            s = s - c
        return s


# --------------------------------------------------------------------------
# serifs
# --------------------------------------------------------------------------


def bracket(x, y, sx, sy, w=BRK_W, h=BRK_H, k=0.72):
    """Concave fillet sitting in the corner (x, y) between a slab and a stem.
    sx: side it grows to (-1 left / +1 right); sy: +1 up / -1 down."""
    o = Outline(x + sx * w, y)
    o.C((x + sx * w * (1 - k), y), (x, y + sy * h * (1 - k)), (x, y + sy * h))
    o.L(x - sx * 3, y + sy * h)
    o.L(x - sx * 3, y - sy * 3)
    o.L(x + sx * w, y - sy * 3)
    return o.close()


def slab(xl, xr, y, el=SERIF_E, er=SERIF_E, t=SERIF_T, up=1, bw=BRK_W, bh=BRK_H):
    """Hairline serif across a stem xl..xr. up=+1: foot serif whose slab sits on
    y and brackets rise; up=-1: head serif hanging from y."""
    parts = [rect(xl - el, y, xr + er, y + up * t)]
    if el > 8:
        parts.append(bracket(xl, y + up * t, -1, up, min(bw, el * 0.7), bh))
    if er > 8:
        parts.append(bracket(xr, y + up * t, +1, up, min(bw, er * 0.7), bh))
    return union_all(parts)


def flag(xl, xr, ytop, ext=44, tip=14, bh=34):
    """Head serif of lowercase stems: the top is sheared at CUT and the
    flag runs out to the left. Returns (shape, y where the plain stem may stop)."""
    yl = ytop - (xr - xl + ext) * TAN_CUT
    yj = yl - tip - bh
    o = Outline(xr, ytop)
    o.L(xl - ext, yl)
    o.L(xl - ext, yl - tip)
    o.C((xl - ext * 0.42, yl - tip - 2), (xl, yl - tip - bh * 0.3), (xl, yj))
    o.L(xl, yj - 12)
    o.L(xr, yj - 12)
    return o.close(), yj - 6


def stem_flag(x, y0, ytop, w=STEM, ext=44):
    """Lowercase stem with its sheared head serif."""
    f, ys = flag(x, x + w, ytop, ext=ext)
    return [rect(x, y0, x + w, ys), f]


# --------------------------------------------------------------------------
# signature components
# --------------------------------------------------------------------------


def circle_arc(cx, cy, r, a0, a1):
    """Cubic segments of a circular arc from angle a0 to a1 (degrees, any direction)."""
    import math
    n = max(1, int(math.ceil(abs(a1 - a0) / 90.0)))
    segs = []
    for i in range(n):
        t0 = math.radians(a0 + (a1 - a0) * i / n)
        t1 = math.radians(a0 + (a1 - a0) * (i + 1) / n)
        k = 4 / 3 * math.tan((t1 - t0) / 4)
        p0 = (cx + r * math.cos(t0), cy + r * math.sin(t0))
        p3 = (cx + r * math.cos(t1), cy + r * math.sin(t1))
        c1 = (p0[0] - k * r * math.sin(t0), p0[1] + k * r * math.cos(t0))
        c2 = (p3[0] + k * r * math.sin(t1), p3[1] - k * r * math.cos(t1))
        segs.append((c1, c2, p3))
    return segs


def drop(tx, ty, r, length=None, lean=0.0, side=1, tipw=HAIR, phi=24, t=0.92, t2=0.34, tilt=0.0):
    """逆雨滴 — the reverse-rain drop. The tip is ALWAYS the top.

    (tx, ty)  centre of the tip
    r         bulb radius (DROP_BIG or DROP_SMALL — nothing else is allowed)
    length    tip to bulb centre
    lean      0 = symmetric pendant, 1 = the `side` flank flush with the hairline
    tipw      width at the tip (HAIR when it grows out of a hairline, ~0 when free)
    phi       how far above the equator the flanks touch the bulb
    """
    import math
    if length is None:
        length = 2.3 * r
    cx = tx - side * lean * (r - tipw / 2)
    cy = ty - length
    xr0, xl0 = tx + tipw / 2, tx - tipw / 2
    pr = (cx + r * math.cos(math.radians(phi)), cy + r * math.sin(math.radians(phi)))
    pl = (cx - r * math.cos(math.radians(phi)), cy + r * math.sin(math.radians(phi)))
    o = Outline(xr0, ty)
    o.bez(pr[0], pr[1], -90, phi - 90, t=t, t2=t2)
    for c1, c2, p in circle_arc(cx, cy, r, phi, -180 - phi):
        o.C(c1, c2, p)
    o.bez(xl0, ty, 90 - phi, 90, t=t2, t2=t)
    s = o.close()
    if tilt:
        s = s.rotate(tilt, tx, ty)
    return s


def diamond(cx, cy, a=DIA_A, b=DIA_B):
    """菱形點 — the 72-degree rhombus that replaces every dot."""
    return poly([(cx, cy + b), (cx + a, cy), (cx, cy - b), (cx - a, cy)])


def diag(xb, yb, xt, yt, w):
    """Straight diagonal stroke between two heights; w is its HORIZONTAL width.
    (xb, yb) / (xt, yt) are the centres of the bottom / top edges."""
    h = w / 2
    return poly([(xb - h, yb), (xb + h, yb), (xt + h, yt), (xt - h, yt)])


def cut_bar(x0, x1, y0, y1, left=True, right=True):
    """Horizontal bar whose free ends are sheared CUT off the vertical."""
    k = (y1 - y0) * TAN_CUT
    return poly([(x0, y0), (x1 - (k if right else 0), y0), (x1, y1), (x0 + (k if left else 0), y1)])


def hang(x, y, r):
    """Drop hanging from a hairline that ends (travelling down) at (x, y)."""
    return drop(x, y + 2, r)


def rise(x, y, r):
    """Drop rising from a hairline that ends (travelling up) at (x, y):
    the bulb sits on the stroke end and the free tip points to the sky."""
    L = 2.25 * r
    return drop(x, y + L, r, length=L, tipw=3)


def below(x0, y0, x1, y1, far=3000):
    """Half-plane polygon below / right of the line (x0,y0)->(x1,y1) (x1 > x0)."""
    return poly([(x0, y0), (x1, y1), (x1 + far, y1), (x1 + far, -far), (x0, -far)])


def halfplane(p0, p1, far=4000):
    """Everything to the LEFT of the directed line p0 -> p1 (used to trim
    one diagonal along the edge of another so apexes come out clean)."""
    import math
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ln = math.hypot(dx, dy)
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux
    a = (p0[0] - ux * far, p0[1] - uy * far)
    b = (p1[0] + ux * far, p1[1] + uy * far)
    return poly([a, b, (b[0] + nx * far, b[1] + ny * far), (a[0] + nx * far, a[1] + ny * far)])
