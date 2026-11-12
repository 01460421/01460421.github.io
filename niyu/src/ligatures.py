"""Ligatures (liga). In f_i the hanging drop of the f takes the place of
the dot — rain where the diamond would have been."""
from .geom import N, Outline, poly, rect, stroke
from .params import *  # noqa: F401,F403
from .parts import G, cut_bar, diamond, drop, hang, slab, stem_flag
from .registry import glyph
from . import lower as LW

S = STEM
F_X0 = 58


def _f_stem(xe, ye, x0=F_X0, top_extra=0):
    xc = x0 + S / 2
    return stroke([
        N(xc, 0, S, d=90),
        N(xc, ASC - 200, S, d=90, to=0.62),
        N(xc + (xe - xc) * 0.6, ASC + 6 - 14 + top_extra, 28, d=0, ti=0.62, to=0.62),
        N(xe, ye, HAIR, d=-90, ti=0.62),
    ])


@glyph('f_i')
def f_i():
    x0, x1 = F_X0, F_X0 + S
    xi0 = x1 + 190                     # the i stem
    xi1 = xi0 + S
    xe, ye = xi0 + S / 2 - 4, ASC - 30
    parts = [_f_stem(xe, ye), cut_bar(x0 - 56, xi0 + 4, XH - HAIR, XH, right=False), slab(x0, x1, 0),
             hang(xe, ye, DROP_BIG)]
    parts += stem_flag(xi0, 0, XH + 6) + [slab(xi0, xi1, 0)]
    return G(parts, xi1 + LW.L0 - 2)


@glyph('f_l')
def f_l():
    x0, x1 = F_X0, F_X0 + S
    xl0 = x1 + 196
    xl1 = xl0 + S
    xc = x0 + S / 2
    # the hook runs straight into the top of the l
    hook = stroke([
        N(xc, 0, S, d=90),
        N(xc, ASC - 200, S, d=90, to=0.62),
        N(xc + 150, ASC + 6 - 14, 28, d=0, ti=0.62, to=0.5),
        N(xl0 + 10, ASC - 44, HAIR + 4, d=-38, ti=0.5),
    ], end_cut=90)
    top = poly([(xl0, ASC - 120), (xl1, ASC - 120), (xl1, ASC + 4), (xl0, ASC + 4 - S * TAN_CUT)])
    parts = [hook, top, rect(xl0, 0, xl1, ASC - 110), cut_bar(x0 - 56, xl0 + 4, XH - HAIR, XH, right=False),
             slab(x0, x1, 0), slab(xl0, xl1, 0)]
    return G(parts, xl1 + LW.L0 - 2)


@glyph('f_f')
def f_f():
    x0, x1 = F_X0, F_X0 + S
    x2 = x1 + 176
    x3 = x2 + S
    xc = x0 + S / 2
    first = stroke([
        N(xc, 0, S, d=90),
        N(xc, ASC - 210, S, d=90, to=0.62),
        N(xc + 128, ASC - 30, 28, d=0, ti=0.62, to=0.5),
        N(x2 + 8, ASC - 96, HAIR + 4, d=-42, ti=0.5),
    ], end_cut=90)
    xe, ye = x2 + S / 2 + 200, ASC - 52
    second = _f_stem(xe, ye, x0=x2)
    parts = [first, second, cut_bar(x0 - 56, x3 + 104, XH - HAIR, XH), slab(x0, x1, 0), slab(x2, x3, 0),
             hang(xe, ye, DROP_BIG)]
    return G(parts, x3 + 122)
