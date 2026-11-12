"""Second layer (ss01): swash capitals and long tails. This is where the
type gets loud — the default layer stays quiet so reading never suffers.
Capitals carry no drops in the default layer; here their tails end in rain
that rises."""
from .geom import N, Outline, poly, rect, stroke
from .params import *  # noqa: F401,F403
from .parts import G, below, bracket, cut_bar, diamond, drop, hang, rise, slab
from .registry import glyph
from . import upper as U
from . import lower as LW

m = U.CAPS


def left_curl(xc, y0, w, d0=270, reach=250, lift=104):
    """Hairline that leaves a stroke end at (xc, y0), swings out to the left
    along the baseline and turns up into a rising drop."""
    ex, ey = xc - reach, lift
    s = stroke([
        N(xc, y0, w, d=d0, to=0.62),
        N(xc - reach * 0.5, HAIR_C / 2 + 1, HAIR_C + 2, d=180, ti=0.6, to=0.62),
        N(ex, ey, HAIR_C, d=97, ti=0.6),
    ])
    return [s, rise(ex, ey, DROP_BIG)]


def right_tail(pts, r=DROP_BIG):
    """Long tail to the right that ends in a rising drop. pts: stroke nodes."""
    s = stroke(pts)
    return [s, rise(pts[-1].x, pts[-1].y, r)]


@glyph('A.ss01')
def A_sw():
    g = U.A(m)
    xl = m.sbr - 6
    w = m.w(690)
    xa = xl + w * 0.485
    wn = U.hw(m, w / 2, m.h, m.thin)
    # parts: thin, thick, bar, left serif, right serif -> drop the left serif
    parts = [g.parts[0], g.parts[1], g.parts[2], g.parts[4]]
    import math
    lx = xl + m.w(26) + wn / 2
    ang = math.degrees(math.atan2(-(m.h + 6), (xl + m.w(26)) - (xa - 8)))
    parts += left_curl(lx + 20, 62, m.thin, d0=ang, reach=270, lift=110)
    return G(parts, g.adv)


@glyph('M.ss01')
def M_sw():
    g = U.M_(m)
    x0 = m.sb - 6
    tn = m.thin + 2
    parts = [p for i, p in enumerate(g.parts) if i != 1]     # drop the left foot serif
    parts += left_curl(x0 + tn / 2, 190, tn, reach=250, lift=110)
    return G(parts, g.adv)


@glyph('N.ss01')
def N_sw():
    g = U.N_(m)
    x0 = m.sb - 4
    tn = m.thin + 2
    parts = [p for i, p in enumerate(g.parts) if i != 1]
    parts += left_curl(x0 + tn / 2, 190, tn, reach=250, lift=110)
    return G(parts, g.adv)


@glyph('Q.ss01')
def Q_sw():
    w = m.w(716)
    cx = m.sbr + w / 2
    tail = right_tail([
        N(cx - 26, 14, m.hair, d=-30, to=0.5),
        N(cx + 150, -86, m.s * 0.86, d=-30, ti=0.5, to=0.6),
        N(cx + 440, -176, 44, d=-6, ti=0.6, to=0.6),
        N(cx + 680, -190, m.hair + 2, d=6, ti=0.5, to=0.58),
        N(cx + 820, -122, m.hair, d=84, ti=0.6),
    ])
    return G([U.cring(m, cx, w)] + tail, w + 2 * m.sbr)


def _leg_tail(x_start, y_start, x1):
    return right_tail([
        N(x_start, y_start, m.hair + 12, d=-60, to=0.4),
        N(x1 + 300, 190, m.s * 1.04, d=-56, ti=0.4, to=0.5),
        N(x1 + 520, -96, 56, d=-30, ti=0.5, to=0.6),
        N(x1 + 740, -180, m.hair + 2, d=4, ti=0.6, to=0.58),
        N(x1 + 880, -118, m.hair, d=84, ti=0.6),
    ])


@glyph('R.ss01')
def R_sw():
    x0 = m.sb
    x1 = x0 + m.s
    bw = m.w(380)
    yb = m.h * 0.47
    parts = U.cstem(m, x0, head='l', foot='lr') + [U.cbowl(m, x1, bw, m.h, yb, flat=0.48)]
    parts += _leg_tail(x1 + 178, yb + 2, x1)
    return G(parts, U.R(m).adv)


@glyph('K.ss01')
def K_sw():
    g = U.K(m)
    x0 = m.sb
    x1 = x0 + m.s
    xt = x1 + m.w(372)
    ya = m.h * 0.34
    wn = U.hw(m, xt - x1, m.h - ya, m.thin)
    # stem (3 parts) + arm + arm serif, then the swash leg clipped under the arm
    parts = g.parts[:4] + [g.parts[5]]
    tail = _leg_tail(x1 + 120, m.h * 0.60, x1)
    parts += [tail[0] & below(x1 - 2, ya, xt - wn, m.h), tail[1]]
    return G(parts, g.adv)


@glyph('Y.ss01')
def Y_sw():
    g = U.Y(m)
    xl = m.sbr - 4
    w = m.w(640)
    xs = xl + w / 2 - m.s / 2 + m.w(6)
    yj = m.h * 0.40
    xc = xs + m.s / 2
    ex, ey = xc - 300, DESC + 96
    tail = stroke([
        N(xc, yj, m.s, d=270),
        N(xc, -70, m.s, d=270, to=0.62),
        N(xc - 150, DESC + 15, 30, d=180, ti=0.62, to=0.62),
        N(ex, ey, m.hair, d=97, ti=0.6),
    ])
    parts = [g.parts[0], g.parts[1], tail, rise(ex, ey, DROP_BIG), g.parts[-2], g.parts[-1]]
    return G(parts, g.adv)


@glyph('L.ss01')
def L_sw():
    x0 = m.sb
    x1 = x0 + m.s
    tail = right_tail([
        N(x1 - 30, m.hair / 2 + 1, m.hair + 2, d=0),
        N(x1 + 250, m.hair / 2 + 1, m.hair + 2, d=0, to=0.5),
        N(x1 + 430, -70, 50, d=-22, ti=0.5, to=0.55),
        N(x1 + 630, -176, m.hair + 2, d=4, ti=0.55, to=0.58),
        N(x1 + 760, -118, m.hair, d=84, ti=0.6),
    ])
    parts = U.cstem(m, x0, head='lr', foot='l') + tail
    return G(parts, U.L(m).adv)


@glyph('y.ss01')
def y_sw():
    """Long-tailed y: the tail runs far out under the preceding letters."""
    import math
    S, XHh = STEM, XH
    xl = 52
    w = 452
    xr = xl + w
    xa = xl + w * 0.515
    thick = poly([(xl, XHh), (xl + LW.WT, XHh), (xa - 12 + LW.WT, -8), (xa - 12, -8)])
    dx, dy = (xr - LW.WH / 2) - (xa + 12 - LW.WH / 2), XHh + 8
    ang = math.degrees(math.atan2(-dy, -dx))
    th = LW.WH * math.sin(math.radians(-ang))
    sx, sy = xr - LW.WH / 2, XHh
    ex, ey = sx - dx * (XHh + 110) / dy, -110
    bx, by = ex - 170, DESC + 16
    tx, ty = bx - 240, DESC + 86
    tail = stroke([
        N(sx, sy, th, d=ang),
        N(ex, ey, th, d=ang, to=0.62),
        N(bx, by, HAIR + 6, d=180, ti=0.6, to=0.62),
        N(tx, ty, HAIR, d=97, ti=0.62),
    ], start_cut=0)
    parts = [thick, tail, rise(tx, ty, DROP_BIG),
             LW.dserif(xl, xl + LW.WT, XHh), LW.dserif(xr - LW.WH, xr, XHh, el=44, er=44)]
    return G(parts, xr + 48)
