"""Capitals. Every drawing function takes a metrics object, so the very same
code also produces the small caps (smcp) at their own height and weight."""
import math

from .geom import N, Outline, ellipse, poly, rect, stroke, union_all
from .params import *  # noqa: F401,F403
from .parts import G, below, bracket, cut_bar, diag, diamond, drop, halfplane, hang, rise, slab
from .registry import glyph

CUTV = 90 - CUT


class M:
    """Metrics for one capital-like alphabet."""

    def __init__(self, h, s, hair, os, se, sb, sbr, ws, thin):
        self.h, self.s, self.hair, self.os = h, s, hair, os
        self.se, self.sb, self.sbr, self.ws = se, sb, sbr, ws
        self.thin = thin                 # true thickness of thin diagonals / thin stems
        self.th = s + ROUND_EXTRA + 2    # thickest part of round strokes
        self.k = h / CAP                 # vertical scale against the caps

    def w(self, v):                      # scale a horizontal design dimension
        return v * self.ws


CAPS = M(CAP, STEM_C, HAIR_C, OS_C, SERIF_EC, SBC_STRAIGHT, SBC_ROUND, 1.0, 32)
SMALL = M(SC, STEM_SC, HAIR, OS, 44, 62, 36, 0.765, 28)


def cap(name, uni):
    """Register a capital drawer for both the cap and the small-cap alphabets."""

    def deco(fn):
        glyph(name, uni)(lambda: fn(CAPS))
        glyph(name.lower() + '.sc')(lambda: fn(SMALL))
        return fn

    return deco


def cstem(m, x, y0=0, y1=None, head='lr', foot='lr', w=None):
    """Capital stem with hairline serifs. head/foot: which sides get a serif."""
    y1 = m.h if y1 is None else y1
    w = m.s if w is None else w
    parts = [rect(x, y0, x + w, y1)]
    if foot:
        parts.append(slab(x, x + w, y0, el=m.se if 'l' in foot else 0, er=m.se if 'r' in foot else 0))
    if head:
        parts.append(slab(x, x + w, y1, el=m.se if 'l' in head else 0, er=m.se if 'r' in head else 0, up=-1))
    return parts


def beak(m, xe, y, dirn, length, side=1, br=True):
    """Vertical serif closing a hairline arm. Its free end is cut at CUT.
    xe: outer edge; y: outer edge of the arm; dirn: +1 grows up, -1 grows down;
    side: +1 the arm arrives from the left, -1 from the right."""
    t = m.hair + 4
    xi = xe - side * t
    yo = y + dirn * length
    yi = yo - dirn * t * TAN_CUT * 1.0
    p = poly([(xe, y), (xe, yo), (xi + side * 2, yi), (xi, y + dirn * m.hair)]
             if side * dirn > 0 else
             [(xe, y), (xi, y + dirn * m.hair), (xi + side * 2, yi), (xe, yo)])
    if not br:
        return [p]
    return [p, bracket(xi, y + dirn * m.hair, -side, dirn, 46 * m.ws, 70 * m.k, k=0.6)]


def cdrop(m):
    """Drop size for this alphabet: big on capitals, small on small caps."""
    return DROP_BIG if m.h >= CAP else DROP_SMALL


def knot(m, cx, cy):
    """菱形結: the small diamond that sits on a capital's crossbar."""
    k = 1.0 if m.h >= CAP else 0.8
    return diamond(cx, cy, KNOT_A * k, KNOT_B * k)


def dslab(m, xl, xr, y, up=1, el=None, er=None):
    el = m.se * 0.8 if el is None else el
    er = m.se * 0.8 if er is None else er
    return rect(xl - el, y, xr + er, y + up * SERIF_T)


def quad(xtl, xtr, yt, xbl, xbr, yb):
    return poly([(xtl, yt), (xtr, yt), (xbr, yb), (xbl, yb)])


# ---------------------------------------------------------------- H family


@cap('H', 0x48)
def H(m):
    x0 = m.sb
    x2 = x0 + m.w(580) - m.s
    by = m.h * 0.515
    x1 = x0 + m.s
    parts = cstem(m, x0) + cstem(m, x2) + [rect(x1 + GAP, by - m.hair / 2, x2 - GAP, by + m.hair / 2),
                                           knot(m, (x1 + x2) / 2, by)]
    return G(parts, x2 + m.s + m.sb)


@cap('I', 0x49)
def I(m):
    x0 = m.sb
    return G(cstem(m, x0), x0 + m.s + m.sb)


@cap('E', 0x45)
def E(m):
    x0 = m.sb
    x1 = x0 + m.s
    xt, xm, xb = x1 + m.w(332), x1 + m.w(214), x1 + m.w(356)
    by = m.h * 0.525
    g = x1 + GAP                       # 斷線: every arm stops short of the stem
    parts = cstem(m, x0, head='l', foot='l') + [
        rect(g, m.h - m.hair, xt, m.h), rect(g, 0, xb, m.hair),
        rect(g, by - m.hair / 2, xm, by + m.hair / 2), knot(m, xm, by),
    ]
    parts += beak(m, xt, m.h, -1, 172 * m.k) + beak(m, xb, 0, 1, 196 * m.k)
    return G(parts, xb + m.sbr + 6)


@cap('F', 0x46)
def F(m):
    x0 = m.sb
    x1 = x0 + m.s
    xt, xm = x1 + m.w(326), x1 + m.w(208)
    by = m.h * 0.5
    g = x1 + GAP
    parts = cstem(m, x0, head='l', foot='lr') + [
        rect(g, m.h - m.hair, xt, m.h),
        rect(g, by - m.hair / 2, xm, by + m.hair / 2), knot(m, xm, by),
    ]
    parts += beak(m, xt, m.h, -1, 172 * m.k)
    return G(parts, xt + m.sbr - 4)


@cap('L', 0x4C)
def L(m):
    x0 = m.sb
    x1 = x0 + m.s
    xb = x1 + m.w(346)
    parts = cstem(m, x0, head='lr', foot='l') + [rect(x1 - 2, 0, xb, m.hair)]
    parts += beak(m, xb, 0, 1, 210 * m.k)
    return G(parts, xb + m.sbr - 6)


@cap('T', 0x54)
def T(m):
    xl = m.sbr - 4
    w = m.w(610)
    xr = xl + w
    xs = xl + w / 2 - m.s / 2
    parts = cstem(m, xs, head='', foot='lr') + [rect(xl, m.h - m.hair, xr, m.h)]
    parts += beak(m, xl, m.h, -1, 184 * m.k, side=-1) + beak(m, xr, m.h, -1, 184 * m.k)
    return G(parts, xr + m.sbr - 4)


# ---------------------------------------------------------------- O family


def cring(m, cx, w, th=None, tension=0.565):
    th = m.th if th is None else th
    rx, ry = w / 2 - th / 2, m.h / 2 + m.os - m.hair / 2
    cy = m.h / 2
    return stroke([
        N(cx + rx, cy, th, d=90),
        N(cx, cy + ry, m.hair, d=180),
        N(cx - rx, cy, th, d=270),
        N(cx, cy - ry, m.hair, d=0),
    ], closed=True, tension=tension)


@cap('O', 0x4F)
def O(m):
    w = m.w(716)
    return G([cring(m, m.sbr + w / 2, w)], w + 2 * m.sbr)


@cap('Q', 0x51)
def Q(m):
    w = m.w(716)
    cx = m.sbr + w / 2
    tail = stroke([
        N(cx - m.w(20), 10 * m.k, m.hair, d=-26, to=0.5),
        N(cx + m.w(120), -74 * m.k, m.s * 0.82, d=-34, ti=0.5, to=0.5),
        N(cx + m.w(330), -150 * m.k, m.hair, d=-4, ti=0.5),
    ], end_cut=CUT_SIDE)
    return G([cring(m, cx, w), tail], w + 2 * m.sbr)


@cap('C', 0x43)
def C(m):
    sb = m.sbr
    w = m.w(640)
    cx = sb + w / 2 + m.w(10)
    xa, ya = sb + w - m.w(34), m.h - 124 * m.k
    nodes = [
        N(xa, ya, m.hair, d=90, to=0.6),
        N(cx + m.w(24), m.h + m.os - m.hair / 2 - 1, m.hair + 2, d=180, ti=0.58),
        N(sb + m.th / 2, m.h / 2, m.th, d=270),
        N(cx + m.w(36), -m.os + m.hair / 2 + 2, m.hair + 4, d=0, to=0.6),
        N(sb + w, 148 * m.k, m.hair, d=58, ti=0.5),
    ]
    return G([stroke(nodes, end_cut=CUT_SIDE), hang(xa, ya, cdrop(m))], sb + w + m.sbr - 6)


@cap('G', 0x47)
def G_(m):
    sb = m.sbr
    w = m.w(672)
    cx = sb + w / 2 + m.w(4)
    xg = sb + w - m.s - m.w(8)
    yg = m.h * 0.43
    xa, ya = sb + w - m.w(52), m.h - 118 * m.k
    nodes = [
        N(xa, ya, m.hair, d=90, to=0.6),
        N(cx + m.w(20), m.h + m.os - m.hair / 2 - 1, m.hair + 2, d=180, ti=0.58),
        N(sb + m.th / 2, m.h / 2, m.th, d=270),
        N(cx + m.w(30), -m.os + m.hair / 2 + 2, m.hair + 4, d=0, to=0.62),
        N(xg + m.s / 2, 150 * m.k, m.s, d=90, ti=0.62),
        N(xg + m.s / 2, yg - 4, m.s, d=90),
    ]
    parts = [stroke(nodes), slab(xg, xg + m.s, yg, el=m.se * 0.8, er=m.se * 0.8, up=-1), hang(xa, ya, cdrop(m))]
    return G(parts, xg + m.s + m.sb - 10)


def cbowl(m, x1, bw, ytop, ybot, th=None, gap=GAP, flat=0.40, t=0.6):
    """Bowl of B / D / P / R: the two hairlines stop `gap` short of the stem (斷線)."""
    th = m.th if th is None else th
    h2 = m.hair / 2
    return stroke([
        N(x1 + gap, ytop - h2, m.hair, d=0),
        N(x1 + bw * flat, ytop - h2, m.hair, d=0, to=t),
        N(x1 + bw - th / 2, (ytop + ybot) / 2, th, d=-90, ti=t, to=t),
        N(x1 + bw * flat, ybot + h2, m.hair, d=180, ti=t),
        N(x1 + gap, ybot + h2, m.hair, d=180),
    ])


@cap('D', 0x44)
def D(m):
    x0 = m.sb
    x1 = x0 + m.s
    bw = m.w(520)
    parts = cstem(m, x0, head='l', foot='l') + [cbowl(m, x1, bw, m.h, 0, flat=0.36, t=0.62)]
    return G(parts, x1 + bw + m.sbr)


@cap('B', 0x42)
def B(m):
    x0 = m.sb
    x1 = x0 + m.s
    ym = m.h * 0.535
    h2 = m.hair / 2
    up = cbowl(m, x1, m.w(356), m.h, ym - h2, th=m.s * 0.9, flat=0.5)
    lo = cbowl(m, x1, m.w(404), ym + h2, 0, th=m.th + 2, flat=0.48)
    parts = cstem(m, x0, head='l', foot='l') + [up, lo]
    return G(parts, x1 + m.w(404) + m.sbr + 2)


@cap('P', 0x50)
def P(m):
    x0 = m.sb
    x1 = x0 + m.s
    bw = m.w(388)
    parts = cstem(m, x0, head='l', foot='lr') + [cbowl(m, x1, bw, m.h, m.h * 0.44, flat=0.48)]
    return G(parts, x1 + bw + m.sbr - 4)


@cap('R', 0x52)
def R(m):
    x0 = m.sb
    x1 = x0 + m.s
    bw = m.w(380)
    yb = m.h * 0.47
    wl = m.s * 1.16
    xf = x1 + m.w(470)
    leg = quad(x1 + m.w(150), x1 + m.w(150) + wl, yb + 4, xf - wl, xf, 0)
    parts = cstem(m, x0, head='l', foot='lr') + [cbowl(m, x1, bw, m.h, yb, flat=0.48), leg,
                                                    dslab(m, xf - wl, xf, 0, el=0, er=m.se * 0.9)]
    return G(parts, xf + m.sbr + 8)


# ---------------------------------------------------------------- diagonals


def hw(m, dx, dy, true_w):
    """Horizontal width of a diagonal of true thickness true_w."""
    return true_w * math.hypot(dx, dy) / abs(dy)


@cap('A', 0x41)
def A(m):
    xl = m.sbr - 6
    w = m.w(690)
    xr = xl + w
    xa = xl + w * 0.485
    top = m.h + 6 * m.k
    wt = hw(m, w / 2, m.h, m.s * 1.02)
    wn = hw(m, w / 2, m.h, m.thin)
    ap = 14
    fl, fr = xl + m.w(26), xr - m.w(20)          # outer feet
    thin = quad(xa - ap / 2, xa - ap / 2 + wn, top, fl, fl + wn, 0)
    thick = quad(xa + ap / 2 - wt * 0.94, xa + ap / 2, top, fr - wt, fr, 0) & halfplane((xa - ap / 2, top), (fl, 0))
    by = m.h * 0.335
    f = by / top
    xbl = fl + wn + (xa - ap / 2 - fl) * f
    xbr = (fr - wt) + (xa + ap / 2 - wt * 0.94 - (fr - wt)) * f
    bar = union_all([rect(xbl + GAP, by - m.hair / 2, xbr - GAP, by + m.hair / 2), knot(m, (xbl + xbr) / 2, by)])
    parts = [thin, thick, bar, dslab(m, fl, fl + wn, 0), dslab(m, fr - wt, fr, 0)]
    return G(parts, xr + m.sbr - 6)


@cap('V', 0x56)
def V(m):
    xl = m.sbr - 2
    w = m.w(672)
    xr = xl + w
    xa = xl + w * 0.52
    bot = -8 * m.k
    wt = hw(m, w / 2, m.h, m.s * 1.02)
    wn = hw(m, w / 2, m.h, m.thin)
    ap = 16
    a, b = xl + m.w(22), xr - m.w(24)
    thick = quad(a, a + wt, m.h, xa - ap / 2, xa - ap / 2 + wt * 0.94, bot) & halfplane((xa + ap / 2, bot), (b, m.h))
    thin = quad(b - wn, b, m.h, xa + ap / 2 - wn, xa + ap / 2, bot)
    parts = [thick, thin, dslab(m, a, a + wt, m.h, up=-1), dslab(m, b - wn, b, m.h, up=-1)]
    return G(parts, xr + m.sbr - 4)


@cap('W', 0x57)
def W(m):
    xl = m.sbr - 2
    bot = -8 * m.k
    run_t, run_n = m.w(262), m.w(232)
    wt = hw(m, run_t, m.h, m.s * 1.0)
    wn = hw(m, run_n, m.h, m.thin)
    ap = 16
    x1 = xl + m.w(22)
    xa1 = x1 + run_t + ap / 2
    xm = xa1 + ap / 2 + run_n
    x2 = xm - wt
    xa2 = x2 + run_t + ap / 2
    xr = xa2 + ap / 2 + run_n
    thick1 = quad(x1, x1 + wt, m.h, xa1 - ap / 2, xa1 - ap / 2 + wt * 0.94, bot) & halfplane((xa1 + ap / 2, bot), (xm, m.h))
    thin1 = quad(xm - wn, xm, m.h, xa1 + ap / 2 - wn, xa1 + ap / 2, bot)
    thick2 = (quad(x2, xm, m.h, xa2 - ap / 2, xa2 - ap / 2 + wt * 0.94, bot)
              & halfplane((xa2 + ap / 2, bot), (xr, m.h)) & halfplane((xm - wn, m.h), (xa1 + ap / 2 - wn, bot)))
    thin2 = quad(xr - wn, xr, m.h, xa2 + ap / 2 - wn, xa2 + ap / 2, bot)
    parts = [thick1, thin1, thick2, thin2,
             dslab(m, x1, x1 + wt, m.h, up=-1), dslab(m, xr - wn, xr, m.h, up=-1)]
    return G(parts, xr + m.sbr + m.w(18))


@cap('X', 0x58)
def X(m):
    xl = m.sbr + 4
    w = m.w(620)
    xr = xl + w
    wt = hw(m, w * 0.8, m.h, m.s * 1.0)
    wn = hw(m, w * 0.8, m.h, m.thin)
    a, b, c_, d_ = xl + m.w(14), xr - m.w(8), xl + m.w(6), xr - m.w(26)
    thick = quad(a, a + wt, m.h, b - wt, b, 0)
    thin = quad(d_ - wn, d_, m.h, c_, c_ + wn, 0)
    parts = [thick, thin,
             dslab(m, a, a + wt, m.h, up=-1), dslab(m, d_ - wn, d_, m.h, up=-1),
             dslab(m, c_, c_ + wn, 0), dslab(m, b - wt, b, 0)]
    return G(parts, xr + m.sbr)


@cap('Y', 0x59)
def Y(m):
    xl = m.sbr - 4
    w = m.w(640)
    xr = xl + w
    xs = xl + w / 2 - m.s / 2 + m.w(6)
    yj = m.h * 0.40
    wt = hw(m, w / 2, m.h - yj, m.s * 1.0)
    wn = hw(m, w / 2, m.h - yj, m.thin)
    a = xl + m.w(18)
    b = xr - m.w(22)
    thick = quad(a, a + wt, m.h, xs, xs + m.s, yj - 20 * m.k)
    thin = quad(b - wn, b, m.h, xs + m.s - wn - 6, xs + m.s, yj)
    parts = [thick, thin] + cstem(m, xs, y1=yj + 6 * m.k, head='', foot='lr') + [
        dslab(m, a, a + wt, m.h, up=-1), dslab(m, b - wn, b, m.h, up=-1)]
    return G(parts, xr + m.sbr - 6)


@cap('K', 0x4B)
def K(m):
    x0 = m.sb
    x1 = x0 + m.s
    xt = x1 + m.w(372)
    xb = x1 + m.w(440)
    ya = m.h * 0.34
    wn = hw(m, xt - x1, m.h - ya, m.thin)
    wt = m.s * 1.2
    arm = poly([(x1 - 2, ya), (x1 - 2, ya + wn * 1.2), (xt, m.h), (xt - wn, m.h)])
    # the leg grows out of the arm: clip it along the arm's lower edge
    leg = quad(x1 + m.w(40), x1 + m.w(40) + wt, m.h * 0.72, xb - wt, xb, 0) & below(x1 - 2, ya, xt - wn, m.h)
    room = rect(x1 + GAP, -50, x1 + 2000, m.h + 50)       # 斷線
    arm, leg = arm & room, leg & room
    parts = cstem(m, x0) + [arm, leg, dslab(m, xt - wn, xt, m.h, up=-1), dslab(m, xb - wt, xb, 0)]
    return G(parts, xb + m.sbr + 2)


@cap('M', 0x4D)
def M_(m):
    x0 = m.sb - 6
    tn = m.thin + 2
    w = m.w(700)
    x3 = x0 + tn + w             # right (thick) stem
    xm = x0 + tn + w * 0.49
    wt = m.s * 1.12
    wn = hw(m, w / 2, m.h, m.thin)
    bot = -6 * m.k
    ap = 16
    left = cstem(m, x0, w=tn)
    right = cstem(m, x3)
    xtr = x3 + m.s * 0.25         # where the thin diagonal reaches the top
    thick = quad(x0, x0 + wt, m.h, xm - ap / 2, xm - ap / 2 + wt * 0.92, bot) & halfplane((xm + ap / 2, bot), (xtr, m.h))
    thin = quad(xtr - wn, xtr, m.h, xm + ap / 2 - wn, xm + ap / 2, bot)
    # the head serifs only run outwards
    left[2] = slab(x0, x0 + tn, m.h, el=m.se, er=0, up=-1)
    right[2] = slab(x3, x3 + m.s, m.h, el=0, er=m.se, up=-1)
    return G(left + right + [thick, thin], x3 + m.s + m.sb)


@cap('N', 0x4E)
def N_(m):
    x0 = m.sb - 4
    tn = m.thin + 2
    w = m.w(560)
    x2 = x0 + tn + w
    wt = m.s * 1.16
    left = cstem(m, x0, w=tn)
    right = cstem(m, x2, w=tn, foot='')
    left[2] = slab(x0, x0 + tn, m.h, el=m.se, er=0, up=-1)
    thick = quad(x0, x0 + wt, m.h, x2 + tn - wt, x2 + tn, -6 * m.k)
    return G(left + right + [thick], x2 + tn + m.sb - 6)


@cap('Z', 0x5A)
def Z(m):
    xl = m.sbr + 6
    w = m.w(560)
    xr = xl + w
    wt = hw(m, w * 0.8, m.h, m.s * 1.06)
    parts = [rect(xl + m.w(22), m.h - m.hair, xr - m.w(10), m.h), rect(xl, 0, xr, m.hair),
             quad(xr - m.w(10) - wt, xr - m.w(10), m.h, xl, xl + wt, 0)]
    parts += beak(m, xl + m.w(22), m.h, -1, 168 * m.k, side=-1) + beak(m, xr, 0, 1, 196 * m.k)
    return G(parts, xr + m.sbr)


# ---------------------------------------------------------------- mixed


@cap('S', 0x53)
def S(m):
    sb = m.sbr + 10
    w = m.w(470)
    ky = m.k
    xa, ya = sb + w * 0.93, m.h - 132 * ky
    xe, ye = sb + w * 0.035, 142 * ky
    nodes = [
        N(xa, ya, m.hair, d=90, to=0.6),
        N(sb + w * 0.50, m.h + m.os - m.hair / 2 - 1, m.hair + 2, d=180, ti=0.58),
        N(sb + m.s * 0.43, m.h - 190 * ky, m.s * 0.86, d=270, to=0.62),
        N(sb + w * 0.50, m.h * 0.515, m.s * 1.02, d=-27, ti=0.7, to=0.7),
        N(sb + w - m.s * 0.45, 192 * ky, m.s * 0.92, d=270, ti=0.62),
        N(sb + w * 0.48, -m.os + m.hair / 2 + 1, m.hair + 2, d=180, to=0.58),
        N(xe, ye, m.hair, d=92, ti=0.6),
    ]
    return G([stroke(nodes), hang(xa, ya, cdrop(m)), rise(xe, ye, cdrop(m))], sb + w + m.sbr + 10)


@cap('J', 0x4A)
def J(m):
    x0 = m.sbr + m.w(236)
    xc = x0 + m.s / 2
    xe, ye = x0 - m.w(206), 112 * m.k
    hook = stroke([
        N(xc, m.h - 10, m.s, d=270),
        N(xc, 168 * m.k, m.s, d=270, to=0.62),
        N(xc - m.w(128), -m.os + m.hair / 2 + 3, m.hair + 6, d=180, ti=0.62, to=0.6),
        N(xe, ye, m.hair, d=94, ti=0.6),
    ])
    parts = [hook, slab(x0, x0 + m.s, m.h, el=m.se, er=m.se, up=-1), rise(xe, ye, cdrop(m))]
    return G(parts, x0 + m.s + m.sb)


@cap('U', 0x55)
def U(m):
    x0 = m.sb
    w = m.w(560)
    tn = m.thin + 4
    xr = x0 + w
    xlc, xrc = x0 + m.s / 2, xr - tn / 2
    cx = (x0 + xr) / 2 + m.w(14)
    body = stroke([
        N(xlc, m.h - 10, m.s, d=270),
        N(xlc, 236 * m.k, m.s, d=270, to=0.6),
        N(cx, -m.os + m.hair / 2 + 3, m.hair + 6, d=0, ti=0.6, to=0.6),
        N(xrc, 250 * m.k, tn, d=90, ti=0.6),
        N(xrc, m.h - 10, tn, d=90),
    ])
    parts = [body, slab(x0, x0 + m.s, m.h, el=m.se, er=m.se, up=-1),
             slab(xr - tn, xr, m.h, el=m.se * 0.85, er=m.se * 0.85, up=-1)]
    return G(parts, xr + m.sb - 14)
