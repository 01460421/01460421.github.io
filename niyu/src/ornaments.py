"""Ornament layer: hairline geometry built on the pentagram that gives the
type its 18-degree cut and its 72-degree diamond."""
import math

from .geom import N, Outline, ellipse, poly, rect, stroke
from .params import *  # noqa: F401,F403
from .parts import G, diamond, drop
from .registry import glyph

LINE = 26          # ornament hairline
AX = 290           # ornaments sit on this axis (between x-height and baseline centre)


def ring_line(cx, cy, r, t=LINE):
    return ellipse(cx, cy, r, r) + ellipse(cx, cy, r - t, r - t).reversed()


def seg(p, q, t=LINE):
    dx, dy = q[0] - p[0], q[1] - p[1]
    ln = math.hypot(dx, dy)
    nx, ny = -dy / ln * t / 2, dx / ln * t / 2
    return poly([(p[0] + nx, p[1] + ny), (q[0] + nx, q[1] + ny), (q[0] - nx, q[1] - ny), (p[0] - nx, p[1] - ny)])


def star_pts(cx, cy, r, n=5, rot=90):
    return [(cx + r * math.cos(math.radians(rot + 360 * i / n)), cy + r * math.sin(math.radians(rot + 360 * i / n))) for i in range(n)]


@glyph('uni25C6', 0x25C6)
def black_diamond():
    return G([diamond(260, AX, 150, 150 * DIA_B / DIA_A)], 520)


@glyph('uni25C7', 0x25C7)
def white_diamond():
    a, b = 170, 170 * DIA_B / DIA_A
    k = (a - LINE * 1.7) / a
    return G([diamond(260, AX, a, b) + diamond(260, AX, a * k, b * k).reversed()], 520)


@glyph('uni25CB', 0x25CB)
def white_circle():
    return G([ring_line(330, AX, 270)], 660)


@glyph('uni25CE', 0x25CE)
def bullseye():
    return G([ring_line(330, AX, 270), diamond(330, AX, DIA_A * 1.4, DIA_B * 1.4)], 660)


@glyph('uni25B3', 0x25B3)
def triangle():
    p = star_pts(340, AX - 60, 320, 3)
    return G([seg(p[0], p[1]), seg(p[1], p[2]), seg(p[2], p[0])], 680)


@glyph('uni25BD', 0x25BD)
def triangle_down():
    p = star_pts(340, AX + 60, 320, 3, rot=-90)
    return G([seg(p[0], p[1]), seg(p[1], p[2]), seg(p[2], p[0])], 680)


@glyph('uni2606', 0x2606)
def pentagram():
    p = star_pts(350, AX - 10, 330)
    return G([seg(p[i], p[(i + 2) % 5]) for i in range(5)], 700)


@glyph('uni26E4', 0x26E4)
def pentagram_ring():
    cx, cy, r = 370, AX, 330
    p = star_pts(cx, cy, r - LINE / 2)
    return G([ring_line(cx, cy, r)] + [seg(p[i], p[(i + 2) % 5]) for i in range(5)], 740)


@glyph('uni2726', 0x2726)
def four_star():
    cx, cy, r, q = 300, AX, 300, 46
    pts = []
    for i in range(4):
        a = math.radians(90 * i)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        a2 = math.radians(90 * i + 45)
        pts.append((cx + q * math.cos(a2), cy + q * math.sin(a2)))
    return G([poly(pts)], 600)


@glyph('uni2727', 0x2727)
def four_star_line():
    cx, cy, r, q = 300, AX, 300, 70
    def star(r_, q_):
        pts = []
        for i in range(4):
            a = math.radians(90 * i)
            pts.append((cx + r_ * math.cos(a), cy + r_ * math.sin(a)))
            a2 = math.radians(90 * i + 45)
            pts.append((cx + q_ * math.cos(a2), cy + q_ * math.sin(a2)))
        return poly(pts)
    return G([star(r, q) + star(r - 92, q - 26).reversed()], 600)


@glyph('uni2020', 0x2020)
def dagger():
    cx = 220
    parts = [rect(cx - 14, DESC + 40, cx + 14, CAP - 60), rect(cx - 150, 450, cx + 150, 450 + LINE),
             diamond(cx, CAP - 30, DIA_A * 0.8, DIA_B * 0.8)]
    return G(parts, 440)


@glyph('uni2021', 0x2021)
def double_dagger():
    cx = 220
    parts = [rect(cx - 14, DESC + 100, cx + 14, CAP - 60), rect(cx - 150, 450, cx + 150, 450 + LINE),
             rect(cx - 150, 60, cx + 150, 60 + LINE),
             diamond(cx, CAP - 30, DIA_A * 0.8, DIA_B * 0.8), diamond(cx, DESC + 70, DIA_A * 0.8, DIA_B * 0.8)]
    return G(parts, 440)


@glyph('u1F4A7', 0x1F4A7)
def droplet():
    return G([drop(250, 620, 150, length=330, tipw=4, phi=24)], 500)


@glyph('uni2E3B', 0x2E3B)
def rule_diamond():
    """Divider: a long hairline with a diamond at its heart."""
    w = 1800
    y = AX - 60
    cx = 100 + w / 2
    parts = [rect(100, y - LINE / 2, cx - 120, y + LINE / 2), rect(cx + 120, y - LINE / 2, 100 + w, y + LINE / 2),
             diamond(cx, y, DIA_A * 1.1, DIA_B * 1.1),
             diamond(cx - 200, y, DIA_A * 0.5, DIA_B * 0.5), diamond(cx + 200, y, DIA_A * 0.5, DIA_B * 0.5)]
    return G(parts, w + 200)


@glyph('uni2767', 0x2767)
def rising_rain():
    """Three drops on their threads, rising — the mark of the type."""
    parts = []
    for i, (x, top, r) in enumerate([(150, 470, 44), (330, 640, 58), (510, 410, 38)]):
        parts.append(drop(x, top, r, tipw=3))
        parts.append(rect(x - 11, -60 + i * 0, x + 11, top - 2.3 * r - r - 40))
    return G(parts, 660)
