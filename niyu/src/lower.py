"""Lowercase. Expansion order follows workflow §6: n -> h m u r i l, o -> c e b d p q, ..."""
import math

from .geom import N, Outline, ellipse, poly, rect, stroke
from .params import *  # noqa: F401,F403
from .parts import G, below, bracket, cut_bar, diag, diamond, drop, flag, halfplane, hang, rise, slab, stem_flag
from .registry import glyph

S = STEM
L0 = SB_STRAIGHT          # left bearing of a straight stem
R0 = SB_STRAIGHT - 6      # right bearing of a straight stem (arches look tighter)
RR = SB_ROUND             # bearing of a round side
CW = 250                  # n counter (stem to stem)
TH = S + ROUND_EXTRA      # thickest part of a round stroke
CUTV = 90 - CUT           # direction of a cut line sheared CUT off the vertical


def arch(x1, x2, top=XH, s=S, branch=104, shoulder=178, top_w=34, bias=0.57, gap=GAP, y0=0):
    """n-arch from the right edge of a stem (x1) to a right stem starting at x2.
    With gap > 0 the hairline start is detached from the stem (斷線)."""
    xt = x1 + (x2 + s / 2 - x1) * bias
    nodes = [
        N(x1 + gap, top - branch, HAIR + 4, d=54, to=0.50),
        N(xt, top + OS - top_w / 2, top_w, d=0, ti=0.62, to=0.60),
        N(x2 + s / 2, top - shoulder, s, d=-90, ti=0.60),
        N(x2 + s / 2, y0, s, d=-90),
    ]
    return stroke(nodes, start_cut=90)


# ---------------------------------------------------------------- n family


@glyph('n', 0x6E)
def n():
    x0, x1 = L0, L0 + S
    x2 = x1 + CW
    parts = stem_flag(x0, 0, XH + 6) + [slab(x0, x1, 0), arch(x1, x2), slab(x2, x2 + S, 0)]
    return G(parts, x2 + S + R0)


@glyph('h', 0x68)
def h():
    x0, x1 = L0, L0 + S
    x2 = x1 + CW
    parts = stem_flag(x0, 0, ASC) + [slab(x0, x1, 0), arch(x1, x2), slab(x2, x2 + S, 0)]
    return G(parts, x2 + S + R0)


@glyph('m', 0x6D)
def m():
    cw = 224
    x0, x1 = L0, L0 + S
    x2 = x1 + cw
    x3 = x2 + S
    x4 = x3 + cw
    parts = stem_flag(x0, 0, XH + 6) + [
        slab(x0, x1, 0),
        arch(x1, x2, bias=0.56),
        slab(x2, x3, 0, el=42, er=42),
        arch(x3, x4, bias=0.56),
        slab(x4, x4 + S, 0),
    ]
    return G(parts, x4 + S + R0)


@glyph('u', 0x75)
def u():
    # the n-arch turned half round: the slit now sits at the right stem
    cw = CW - 6
    x0, x1 = L0 - 6, L0 - 6 + S
    x2 = x1 + cw
    x3 = x2 + S
    bowl_ = arch(-x2, -x1, top=0, y0=-(XH - 60)).rotate(180)
    parts = stem_flag(x0, 0, XH + 6)[1:] + stem_flag(x2, 0, XH + 6) + [
        bowl_,
        slab(x2, x3, 0, el=0, er=SERIF_E),
    ]
    return G(parts, x3 + R0 + 4)


@glyph('r', 0x72)
def r():
    x0, x1 = L0, L0 + S
    xe = x1 + 172
    ye = XH - 44
    nodes = [
        N(x1 + GAP, XH - 108, HAIR + 4, d=58, to=0.5),
        N(x1 + 106, XH + OS - 15, 30, d=0, ti=0.6, to=0.62),
        N(xe, ye, HAIR, d=-90, ti=0.62),
    ]
    arm = stroke(nodes, start_cut=90)
    parts = stem_flag(x0, 0, XH + 6) + [slab(x0, x1, 0), arm, drop(xe, ye + 2, DROP_BIG)]
    return G(parts, xe + DROP_BIG + 22)


@glyph('i', 0x69)
def i():
    x0, x1 = L0, L0 + S
    parts = stem_flag(x0, 0, XH + 6) + [slab(x0, x1, 0), diamond(x0 + S / 2 - 4, XH + 176)]
    return G(parts, x1 + L0 - 2)


@glyph('dotlessi', 0x131)
def dotlessi():
    x0, x1 = L0, L0 + S
    return G(stem_flag(x0, 0, XH + 6) + [slab(x0, x1, 0)], x1 + L0 - 2)


@glyph('l', 0x6C)
def l():
    x0, x1 = L0, L0 + S
    parts = stem_flag(x0, 0, ASC) + [slab(x0, x1, 0)]
    return G(parts, x1 + L0 - 2)


# ---------------------------------------------------------------- o family


def ring(cx, cy, w, h, th=TH, hair=HAIR, tension=0.565):
    rx, ry = w / 2 - th / 2, h / 2 - hair / 2
    return stroke([
        N(cx + rx, cy, th, d=90),
        N(cx, cy + ry, hair, d=180),
        N(cx - rx, cy, th, d=270),
        N(cx, cy - ry, hair, d=0),
    ], closed=True, tension=tension)


@glyph('o', 0x6F)
def o():
    w = 474
    return G([ring(RR + w / 2, XH / 2, w, XH + 2 * OS)], w + 2 * RR)


@glyph('c', 0x63)
def c():
    sb = RR
    cx = sb + 222
    xa, ya = sb + 392, XH - 52
    nodes = [
        N(xa, ya, HAIR, d=90, to=0.58),
        N(cx + 14, XH + OS - 14, 28, d=180, ti=0.58),
        N(sb + TH / 2, XH / 2 - 2, TH, d=270),
        N(cx + 26, -OS + 15, 30, d=0, to=0.6),
        N(sb + 420, 104, HAIR, d=52, ti=0.5),
    ]
    body = stroke(nodes, end_cut=CUT_SIDE)
    return G([body, drop(xa, ya + 2, DROP_BIG)], sb + 392 + DROP_BIG + 20)


@glyph('e', 0x65)
def e():
    sb = RR
    w = 438
    cx = sb + w / 2
    ybar = 252
    wr = 74
    nodes = [
        N(sb + w - wr / 2, ybar + 2, wr, d=90),
        N(cx + 2, XH + OS - 12, HAIR, d=180),
        N(sb + TH / 2, XH / 2 - 4, TH, d=270),
        N(cx + 28, -OS + 15, 30, d=0, to=0.6),
        N(sb + 428, 108, HAIR, d=52, ti=0.5),
    ]
    body = stroke(nodes, end_cut=CUT_SIDE)
    bar = rect(sb + TH / 2, ybar, sb + w - 6, ybar + HAIR)
    return G([body, bar], sb + w + RR - 4)


def bowl(x1, bw=304, top=XH, bot=0, join=100, gap=GAP):
    """Bowl hanging off the right edge (x1) of a stem. Both joins are thin
    and both stop `gap` short of the stem (斷線). Used by b and p; mirrored
    for d and q."""
    cy = (top + bot) / 2
    nodes = [
        N(x1 + gap, top - join, HAIR + 4, d=56, to=0.5),
        N(x1 + bw * 0.50, top + OS - 15, 30, d=0, ti=0.62),
        N(x1 + bw - TH / 2, cy, TH, d=-90),
        N(x1 + bw * 0.50, bot - OS + 15, 30, d=180, to=0.62),
        N(x1 + gap, bot + join, HAIR + 4, d=124, ti=0.5),
    ]
    return stroke(nodes, start_cut=90, end_cut=90)


BW = 304


@glyph('b', 0x62)
def b():
    x0, x1 = L0, L0 + S
    parts = stem_flag(x0, 0, ASC) + [bowl(x1)]
    return G(parts, x1 + BW + RR)


@glyph('p', 0x70)
def p():
    x0, x1 = L0, L0 + S
    parts = stem_flag(x0, DESC, XH + 6) + [bowl(x1), slab(x0, x1, DESC)]
    return G(parts, x1 + BW + RR)


@glyph('d', 0x64)
def d():
    x1 = RR + BW          # left edge of the stem
    x2 = x1 + S
    parts = stem_flag(x1, 0, ASC) + [bowl(-x1).mirror_x(0), slab(x1, x2, 0, el=0)]
    return G(parts, x2 + R0 + 4)


@glyph('q', 0x71)
def q():
    x1 = RR + BW
    x2 = x1 + S
    # the top of the stem is simply sheared at CUT — no flag
    top = poly([(x1, XH - 60), (x2, XH - 60), (x2, XH + 12), (x1, XH + 12 - S * TAN_CUT)])
    parts = [rect(x1, DESC, x2, XH - 50), top, bowl(-x1).mirror_x(0), slab(x1, x2, DESC)]
    return G(parts, x2 + R0)


# ---------------------------------------------------------------- diagonals

WT = 95      # horizontal width of a thick diagonal
WH = 34      # horizontal width of a thin diagonal
DSE = 40     # serif extension on diagonals


def vee(xl, xr, xa, top=XH, bot=-8, wt=WT, wh=WH, flat=22):
    """V made of a thick left and a thin right diagonal meeting at xa. The
    thick stroke is trimmed along the outside of the thin one."""
    thick = poly([(xl, top), (xl + wt, top), (xa - flat / 2 + wt, bot), (xa - flat / 2, bot)])
    thin = poly([(xr - wh, top), (xr, top), (xa + flat / 2, bot), (xa + flat / 2 - wh, bot)])
    return [thick & halfplane((xa + flat / 2, bot), (xr, top)), thin]


def dserif(xl, xr, y, up=-1, el=DSE, er=DSE):
    return rect(xl - el, y, xr + er, y + up * SERIF_T)


@glyph('v', 0x76)
def v():
    xl = 52
    w = 452
    xr = xl + w
    xa = xl + w * 0.515
    parts = vee(xl, xr, xa) + [dserif(xl, xl + WT, XH), dserif(xr - WH, xr, XH, el=44, er=44)]
    return G(parts, xr + 48)


@glyph('w', 0x77)
def w():
    xl = 52
    top, bot, fl = XH, -8, 22
    run_t, run_n = 196, 172          # horizontal run of the thick / thin strokes
    xa1 = xl + run_t + fl / 2
    xm = xa1 + fl / 2 + run_n        # right corner of the middle apex
    x2 = xm - WT                     # top-left of the second thick stroke
    xa2 = x2 + run_t + fl / 2
    xr = xa2 + fl / 2 + run_n
    thick1 = poly([(xl, top), (xl + WT, top), (xa1 - fl / 2 + WT, bot), (xa1 - fl / 2, bot)])
    thin1 = poly([(xm - WH, top), (xm, top), (xa1 + fl / 2, bot), (xa1 + fl / 2 - WH, bot)])
    thick2 = poly([(x2, top), (xm, top), (xa2 - fl / 2 + WT, bot), (xa2 - fl / 2, bot)])
    thin2 = poly([(xr - WH, top), (xr, top), (xa2 + fl / 2, bot), (xa2 + fl / 2 - WH, bot)])
    parts = [thick1 & halfplane((xa1 + fl / 2, bot), (xm, top)), thin1,
             # middle apex: the second thick stroke is trimmed along the first thin one
             thick2 & halfplane((xa2 + fl / 2, bot), (xr, top)) & halfplane((xm - WH, top), (xa1 + fl / 2 - WH, bot)),
             thin2,
             dserif(xl, xl + WT, XH), dserif(xr - WH, xr, XH, el=44, er=44)]
    return G(parts, xr + 48)


@glyph('x', 0x78)
def x():
    xl = 58
    w = 420
    xr = xl + w
    thick = poly([(xl + 6, XH), (xl + 6 + WT, XH), (xr - 2, 0), (xr - 2 - WT, 0)])
    thin = poly([(xl + 8, 0), (xl + 8 + WH, 0), (xr - 12, XH), (xr - 12 - WH, XH)])
    parts = [thick, thin,
             dserif(xl + 6, xl + 6 + WT, XH), dserif(xr - 12 - WH, xr - 12, XH, el=44, er=44),
             dserif(xl + 8, xl + 8 + WH, 0, up=1, el=44, er=44), dserif(xr - 2 - WT, xr - 2, 0, up=1)]
    return G(parts, xr + 54)


@glyph('y', 0x79)
def y():
    xl = 52
    w = 452
    xr = xl + w
    xa = xl + w * 0.515
    thick = poly([(xl, XH), (xl + WT, XH), (xa - 12 + WT, -8), (xa - 12, -8)]) & halfplane((xa + 12, -8), (xr, XH))
    # the thin diagonal runs on below the baseline and curls into a rising drop
    dx, dy = (xr - WH / 2) - (xa + 12 - WH / 2), XH + 8
    ang = math.degrees(math.atan2(-dy, -dx))          # travelling down-left
    th = WH * math.sin(math.radians(-ang))            # true thickness of the thin stroke
    sx, sy = xr - WH / 2, XH
    ex, ey = sx - dx * (XH + 118) / dy, -118
    bx, by = ex - 92, DESC + 16
    tx, ty = bx - 96, DESC + 62
    tail = stroke([
        N(sx, sy, th, d=ang),
        N(ex, ey, th, d=ang, to=0.62),
        N(bx, by, HAIR + 4, d=180, ti=0.6, to=0.62),
        N(tx, ty, HAIR, d=96, ti=0.62),
    ], start_cut=0)
    parts = [thick, tail, rise(tx, ty, DROP_BIG),
             dserif(xl, xl + WT, XH), dserif(xr - WH, xr, XH, el=44, er=44)]
    return G(parts, xr + 48)


@glyph('z', 0x7A)
def z():
    xl = 46
    w = 372
    xr = xl + w
    top = rect(xl + 14, XH - HAIR, xr - 6, XH)
    bot = rect(xl, 0, xr, HAIR)
    dg = poly([(xl, 0), (xl + WT + 14, 0), (xr - 6, XH), (xr - 6 - WT - 14, XH)])
    # beaks: short vertical serifs whose free ends are cut at CUT
    bk1 = poly([(xl + 14, XH), (xl + 14 + HAIR + 6, XH), (xl + 14 + HAIR, XH - 122), (xl + 14, XH - 122 - (HAIR) * TAN_CUT)])
    bk2 = poly([(xr, 0), (xr - HAIR - 6, 0), (xr - HAIR, 128), (xr, 128 + HAIR * TAN_CUT)])
    parts = [top, bot, dg, bk1, bk2,
             bracket(xl + 14 + HAIR + 4, XH - HAIR, 1, -1, 34, 44), bracket(xr - HAIR - 4, HAIR, -1, 1, 34, 44)]
    return G(parts, xr + 44)


@glyph('k', 0x6B)
def k():
    x0, x1 = L0, L0 + S
    xt = x1 + 232
    xb = x1 + 322
    # thin arm rising to the right; the thick leg grows out of it
    arm = poly([(x1 - 2, 168), (x1 - 2, 168 + 44), (xt + WH + 2, XH), (xt, XH)])
    leg = poly([(x1 + 30, XH * 0.74), (x1 + 30 + WT + 8, XH * 0.74), (xb, 0), (xb - WT - 8, 0)]) & below(x1 - 2, 168, xt, XH)
    room = rect(x1 + GAP, -50, x1 + 900, ASC)          # 斷線: nothing touches the stem
    arm, leg = arm & room, leg & room
    parts = stem_flag(x0, 0, ASC) + [
        slab(x0, x1, 0), arm, leg,
        dserif(xt, xt + WH + 2, XH, el=44, er=44),
        dserif(xb - WT - 8, xb, 0, up=1, el=38, er=44),
    ]
    return G(parts, xb + 50)


# ---------------------------------------------------------------- the rest


@glyph('a', 0x61)
def a():
    sb = 44
    xs0 = sb + 250
    xs1 = xs0 + S
    xc = xs0 + S / 2
    xa, ya = sb + 76, XH - 38
    main = stroke([
        N(xc, 0, S, d=90),
        N(xc, XH - 170, S, d=90, to=0.58),
        N(xc - 112, XH + OS - 15, 30, d=180, ti=0.58, to=0.58),
        N(xa, ya, HAIR, d=270, ti=0.58),
    ])
    bw = stroke([
        N(xs0 - GAP, 262, HAIR + 2, d=176, to=0.62),
        N(sb + 41, 130, 86, d=270, ti=0.6),
        N(sb + 144, -OS + 14, 28, d=0, to=0.6),
        N(xs0 - GAP, 88, HAIR + 4, d=50, ti=0.5),
    ], start_cut=90, end_cut=90)
    parts = [main, bw, drop(xa, ya + 2, DROP_SMALL), slab(xs0, xs1, 0, el=0, er=40)]
    return G(parts, xs1 + R0 - 8)


@glyph('s', 0x73)
def s():
    sb = 48
    xa, ya = sb + 300, XH - 92            # top terminal: a drop hangs here
    xe, ye = sb + 26, 104                 # bottom terminal: a drop rises here
    nodes = [
        N(xa, ya, HAIR, d=90, to=0.6),
        N(sb + 174, XH + OS - 13, 26, d=180, ti=0.58),
        N(sb + 48, XH - 126, 80, d=270, to=0.6),
        N(sb + 168, XH / 2 + 2, 92, d=-24, ti=0.66, to=0.66),
        N(sb + 304, 126, 84, d=270, ti=0.6),
        N(sb + 158, -OS + 13, 26, d=180, to=0.58),
        N(xe, ye, HAIR, d=92, ti=0.6),
    ]
    body = stroke(nodes)
    return G([body, hang(xa, ya, DROP_SMALL), rise(xe, ye, DROP_SMALL)], sb + 344 + 46)


@glyph('f', 0x66)
def f():
    x0 = 58
    x1 = x0 + S
    xc = x0 + S / 2
    xe, ye = xc + 200, ASC - 52
    hook = stroke([
        N(xc, 0, S, d=90),
        N(xc, ASC - 200, S, d=90, to=0.62),
        N(xc + 124, ASC + 6 - 14, 28, d=0, ti=0.62, to=0.62),
        N(xe, ye, HAIR, d=-90, ti=0.62),
    ])
    bar = cut_bar(x0 - 56, x1 + 104, XH - HAIR, XH)
    parts = [hook, bar, slab(x0, x1, 0), drop(xe, ye + 2, DROP_BIG)]
    return G(parts, x1 + 122)


@glyph('t', 0x74)
def t():
    x0 = 60
    x1 = x0 + S
    xc = x0 + S / 2
    ytop = XH + 150
    body = stroke([
        N(xc, XH + 60, S, d=270),
        N(xc, 116, S, d=270, to=0.6),
        N(xc + 96, -OS + 16, 32, d=0, ti=0.62, to=0.6),
        N(xc + 190, 78, HAIR, d=56, ti=0.5),
    ], end_cut=CUT_SIDE)
    top = poly([(x0, XH + 50), (x1, XH + 50), (x1, ytop), (x0, ytop - S * TAN_CUT)])
    bar = cut_bar(x0 - 62, x1 + 108, XH - HAIR, XH)
    return G([body, top, bar], x1 + 150)


@glyph('j', 0x6A)
def j():
    x0, x1 = L0, L0 + S
    xc = x0 + S / 2
    tx, ty = xc - 196, DESC + 60
    tail = stroke([
        N(xc, XH - 110, S, d=270),
        N(xc, -74, S, d=270, to=0.6),
        N(xc - 104, DESC + 15, 28, d=180, ti=0.62, to=0.62),
        N(tx, ty, HAIR, d=96, ti=0.62),
    ])
    parts = stem_flag(x0, XH - 120, XH + 6) + [tail, diamond(x0 + S / 2 - 4, XH + 176),
                                               rise(tx, ty, DROP_SMALL)]
    return G(parts, x1 + L0 - 2)


@glyph('g', 0x67)
def g():
    sb = 40
    bw_, bh_ = 296, 336
    cx, cy = sb + 16 + bw_ / 2, XH + OS - bh_ / 2
    upper = ring(cx, cy, bw_, bh_, th=80)
    ex, ey = cx + 232, XH - 30
    ear = stroke([
        N(cx + 96, XH - 70, HAIR + 2, d=50, to=0.55),
        N(cx + 172, XH + OS - 14, 26, d=0, ti=0.6, to=0.6),
        N(ex, ey, HAIR, d=270, ti=0.6),
    ], start_cut=90)
    loop = stroke([
        N(cx - 60, cy - bh_ / 2 + 22, HAIR + 2, d=232, to=0.6),
        N(sb + 60, 78, 30, d=270, ti=0.6, to=0.62),
        N(sb + 166, 22, 66, d=-6, ti=0.6, to=0.6),
        N(sb + 372, -104, 62, d=270, ti=0.62, to=0.6),
        N(sb + 206, DESC + 14, 28, d=180, ti=0.6, to=0.6),
        N(sb + 40, -122, 56, d=90, ti=0.6, to=0.6),
        N(sb + 150, 6, HAIR, d=24, ti=0.6),
    ], start_cut=0, end_cut=90)
    return G([upper, ear, loop, hang(ex, ey, DROP_SMALL)], ex + DROP_SMALL + 26)
