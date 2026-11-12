"""Figures: wide lining figures (default), old-style (onum), tabular (tnum).
1 and 9 are the signature figures — they carry the name of the year."""
from .geom import N, Outline, poly, rect, stroke
from .params import *  # noqa: F401,F403
from .parts import G, bracket, cut_bar, diamond, drop, hang, rise, slab
from .registry import glyph

T = STEM_C          # figure stem
HR = HAIR_C         # figure hairline
O_ = OS_C


def fring(cx, cy, w, h, th=T + 4, hair=HR, tension=0.565):
    rx, ry = w / 2 - th / 2, h / 2 - hair / 2
    return stroke([
        N(cx + rx, cy, th, d=90),
        N(cx, cy + ry, hair, d=180),
        N(cx - rx, cy, th, d=270),
        N(cx, cy - ry, hair, d=0),
    ], closed=True, tension=tension)


def zero(h=FIG):
    sb = 46
    w = 508 if h == FIG else 430
    th = T + 4 if h == FIG else STEM + 2
    return G([fring(sb + w / 2, h / 2, w, h + 2 * O_, th=th)], w + 2 * sb)


def one(h=FIG):
    x0 = 190
    x1 = x0 + T
    top = h + 4
    # sheared top, long curved hairline flag, broad foot
    head = poly([(x0, h - 80), (x1, h - 80), (x1, top), (x0, top - T * TAN_CUT)])
    fl = stroke([
        N(x0 - 150, h - 168, HR, d=44, to=0.5),
        N(x0 + 14, top - T * TAN_CUT - 24, 46, d=26, ti=0.5),
    ], start_cut=CUT_SIDE, end_cut=90)
    parts = [rect(x0, 0, x1, h - 70), head, fl, slab(x0, x1, 0, el=96, er=96, bw=40, bh=52)]
    return G(parts, x1 + 96 + 48)


def two(h=FIG):
    sb = 46
    w = 452
    k = h / FIG
    body = stroke([
        N(sb + 34, h - 150 * k, HR, d=90, to=0.6),
        N(sb + 204, h + O_ - 14, 30, d=0, ti=0.6, to=0.58),
        N(sb + 416 - T / 2, h - 196 * k, T + 2, d=270, ti=0.58, to=0.7),
        N(sb + 24, 18, HR + 8, d=220, ti=0.42),
    ], end_cut=0)
    base = rect(sb + 6, 0, sb + w, HR + 4)
    bk = poly([(sb + w, 0), (sb + w, 150 * k + (HR + 4) * TAN_CUT), (sb + w - HR - 2, 150 * k), (sb + w - HR - 6, HR)])
    parts = [body, base, bk, bracket(sb + w - HR - 4, HR + 2, -1, 1, 44, 62, k=0.6),
             hang(sb + 34, h - 150 * k, DROP_BIG if h == FIG else DROP_SMALL)]
    return G(parts, sb + w + 44)


def three():
    sb, h = 44, FIG
    up = stroke([
        N(sb + 36, h - 148, HR, d=90, to=0.6),
        N(sb + 196, h + O_ - 14, 30, d=0, ti=0.6),
        N(sb + 388 - 42, h - 176, 84, d=270),
        N(sb + 176, 372, HR + 2, d=180),
    ])
    lo = stroke([
        N(sb + 170, 372, HR + 2, d=0),
        N(sb + 430 - 49, 186, 98, d=270),
        N(sb + 200, -O_ + 15, 30, d=180, to=0.6),
        N(sb + 30, 118, HR, d=98, ti=0.6),
    ])
    return G([up, lo, hang(sb + 36, h - 148, DROP_BIG), rise(sb + 30, 118, DROP_BIG)], sb + 430 + 46)


def four():
    sb, h = 30, FIG
    xs0 = sb + 352
    xs1 = xs0 + T
    yb = 196
    top = h + 4
    thin = poly([(xs0 + 22, top - 8), (xs0 - 16, top - 30), (sb + 4, yb + HR), (sb + 46, yb + HR)])
    head = poly([(xs0, h - 120), (xs1, h - 120), (xs1, top), (xs0, top - T * TAN_CUT)])
    bar = cut_bar(sb + 4, xs1 + 96, yb, yb + HR, left=False)
    parts = [rect(xs0, 0, xs1, h - 100), head, thin, bar, slab(xs0, xs1, 0, el=70, er=70)]
    return G(parts, xs1 + 96 + 30)


def five():
    sb, h = 46, FIG
    top = cut_bar(sb + 78, sb + 404, h - 34, h, left=False)
    bk = poly([(sb + 404, h), (sb + 404 - 30, h), (sb + 404 - 26, h - 96), (sb + 404 + 4, h - 96 - 30 * TAN_CUT)])
    neck = rect(sb + 78, 380, sb + 78 + 32, h)
    bowl = stroke([
        N(sb + 84, 372, HR + 6, d=52, to=0.5),
        N(sb + 224, 452, 32, d=0, ti=0.6),
        N(sb + 432 - 49, 222, 98, d=270),
        N(sb + 202, -O_ + 15, 30, d=180, to=0.6),
        N(sb + 30, 118, HR, d=98, ti=0.6),
    ], start_cut=90)
    return G([top, neck, bowl, rise(sb + 30, 118, DROP_BIG)], sb + 432 + 46)


def six():
    sb, h = 46, FIG
    xa, ya = sb + 398, h - 92
    body = stroke([
        N(xa, ya, HR, d=90, to=0.6),
        N(sb + 290, h + O_ - 14, 30, d=180, ti=0.6),
        N(sb + 49, 300, 98, d=270),
        N(sb + 246, -O_ + 15, 30, d=0),
        N(sb + 484 - 47, 220, 94, d=90),
        N(sb + 262, 446, 30, d=180, to=0.6),
        N(sb + 96, 346, HR, d=236, ti=0.5),
    ], end_cut=90)
    return G([body, hang(xa, ya, DROP_SMALL)], sb + 484 + 44)


def seven():
    sb, h = 44, FIG
    w = 452
    bar = rect(sb, h - HR, sb + w, h)
    bk = poly([(sb, h), (sb + HR + 6, h), (sb + HR + 2, h - 150), (sb, h - 150 - HR * TAN_CUT)])
    dg = stroke([
        N(sb + w - 22, h - 8, 36, d=246, to=0.4),
        N(sb + 186, 0, 100, d=262, ti=0.4),
    ], start_cut=0, end_cut=0)
    return G([bar, bk, dg, bracket(sb + HR + 4, h - HR, 1, -1, 44, 62, k=0.6)], sb + w + 40)


def eight():
    sb, h = 46, FIG
    w = 468
    cx = sb + w / 2
    lo = fring(cx, (386 - O_) / 2, w, 386 + O_, th=T + 4)
    up = fring(cx, (360 + h + O_) / 2, w - 68, h + O_ - 360, th=T - 8)
    return G([lo, up], w + 2 * sb)


def nine():
    sb, h = 46, FIG
    body = stroke([
        N(sb + 388, 342, HR, d=236, to=0.5),
        N(sb + 232, 244, 30, d=180, ti=0.6),
        N(sb + 47, 476, 94, d=90),
        N(sb + 242, h + O_ - 15, 30, d=0),
        N(sb + 484 - 49, 404, 98, d=270, to=0.6),
        N(sb + 208, -O_ + 15, 30, d=180, ti=0.6, to=0.6),
        N(sb + 34, 118, HR, d=98, ti=0.6),
    ], start_cut=90)
    return G([body, rise(sb + 34, 118, DROP_BIG)], sb + 484 + 44)


NAMES = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
DRAW = [zero, one, two, three, four, five, six, seven, eight, nine]
TAB_W = 600


def _shift(g, dy):
    return G([p.translate(0, dy) for p in g.parts], g.adv)


def _old(i):
    """Old-style figure: 0 1 2 at x-height, 3 4 5 7 9 hang, 6 8 ascend."""
    if i in (0, 1, 2):
        return DRAW[i](XH)
    if i in (3, 4, 5, 7, 9):
        return _shift(DRAW[i](), XH - FIG)
    return DRAW[i]()


def _tab(g):
    b = g.shape().bounds()
    dx = (TAB_W - (b[2] - b[0])) / 2 - b[0]
    return G([p.translate(dx, 0) for p in g.parts], TAB_W)


for _i, (_n, _f) in enumerate(zip(NAMES, DRAW)):
    glyph(_n, 0x30 + _i)(_f)
    glyph(_n + '.onum')(lambda i=_i: _old(i))
    glyph(_n + '.tnum')(lambda f=_f: _tab(f()))
    glyph(_n + '.onum.tnum')(lambda i=_i: _tab(_old(i)))


@glyph('zero.zero')
def zero_dotted():
    g = zero()
    return G(g.parts + [diamond(g.adv / 2, FIG / 2, DIA_A * 0.9, DIA_B * 0.9)], g.adv)
