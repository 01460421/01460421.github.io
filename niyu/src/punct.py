"""Punctuation and symbols. Every dot is the 72-degree diamond (菱形點);
commas and quotes keep a comma shape with a sheared head."""
import math

from .geom import N, Outline, poly, rect, stroke
from .params import *  # noqa: F401,F403
from .parts import G, bracket, cut_bar, diamond, drop, slab
from .registry import glyph

T = STEM_C
HR = HAIR_C
DOT_Y = DIA_B - 10            # centre of a diamond resting on the baseline
DOT_W = 2 * DIA_A + 2 * 62    # advance of a lone diamond
THIN = 30                     # monoline symbols


def comma_shape(x0, y0):
    """Comma hanging from (x0, y0) = top-left of its sheared head."""
    o = Outline(x0, y0)
    o.L(x0 + 92, y0 + 92 * TAN_CUT)
    o.C((x0 + 96, y0 - 96), (x0 + 62, y0 - 196), (x0 + 6, y0 - 252))
    o.L(x0 - 6, y0 - 240)
    o.C((x0 + 34, y0 - 196), (x0 + 50, y0 - 140), (x0 + 44, y0 - 96))
    o.L(x0, y0 - 96)
    return o.close()


@glyph('period', 0x2E)
def period():
    return G([diamond(DOT_W / 2, DOT_Y)], DOT_W)


@glyph('comma', 0x2C)
def comma():
    return G([comma_shape(70, 92)], 232)


@glyph('colon', 0x3A)
def colon():
    return G([diamond(DOT_W / 2, DOT_Y), diamond(DOT_W / 2, XH - DIA_B + 4)], DOT_W)


@glyph('semicolon', 0x3B)
def semicolon():
    return G([comma_shape(DOT_W / 2 - 46, 92), diamond(DOT_W / 2, XH - DIA_B + 4)], DOT_W)


@glyph('ellipsis', 0x2026)
def ellipsis():
    step = 2 * DIA_A + 128
    return G([diamond(DOT_W / 2 + i * step, DOT_Y) for i in range(3)], DOT_W + 2 * step)


@glyph('periodcentered', 0xB7)
def periodcentered():
    return G([diamond(DOT_W / 2, XH / 2)], DOT_W)


@glyph('bullet', 0x2022)
def bullet():
    return G([diamond(150, XH / 2, DIA_A * 1.3, DIA_B * 1.3)], 300)


@glyph('exclam', 0x21)
def exclam():
    cx = 150
    top = CAP + 4
    body = poly([(cx - T / 2, top - T * TAN_CUT), (cx + T / 2, top), (cx + 14, 214), (cx - 14, 214)])
    return G([body, diamond(cx, DOT_Y)], 300)


@glyph('question', 0x3F)
def question():
    sb = 52
    hook = stroke([
        N(sb + 26, CAP - 172, HR + 16, d=95, to=0.6),
        N(sb + 168, CAP + OS_C - 14, 30, d=0, ti=0.6),
        N(sb + 330 - 47, CAP - 168, T, d=270, to=0.62),
        N(sb + 176, 300, HR + 6, d=262, ti=0.5),
        N(sb + 172, 214, HR + 4, d=270),
    ], start_cut=CUT_UP)
    return G([hook, diamond(sb + 172, DOT_Y)], sb + 330 + 48)


def wedge(cx, ytop, length, wtop=58, wbot=18):
    return poly([(cx - wtop / 2, ytop - wtop * TAN_CUT), (cx + wtop / 2, ytop), (cx + wbot / 2, ytop - length), (cx - wbot / 2, ytop - length)])


@glyph('quotesingle', 0x27)
def quotesingle():
    return G([wedge(100, ASC, 232)], 200)


@glyph('quotedbl', 0x22)
def quotedbl():
    return G([wedge(100, ASC, 232), wedge(224, ASC, 232)], 324)


def _raised_comma(x0):
    return comma_shape(x0, ASC - 4)


def _turned_comma(x0):
    # the opening quote is the closing one turned half round
    return comma_shape(0, 0).rotate(180).translate(x0 + 92, ASC - 252 + 20)


@glyph('quoteright', 0x2019)
def quoteright():
    return G([_raised_comma(62)], 216)


@glyph('quoteleft', 0x2018)
def quoteleft():
    return G([_turned_comma(62)], 216)


@glyph('quotedblright', 0x201D)
def quotedblright():
    return G([_raised_comma(62), _raised_comma(62 + 136)], 216 + 136)


@glyph('quotedblleft', 0x201C)
def quotedblleft():
    return G([_turned_comma(62), _turned_comma(62 + 136)], 216 + 136)


@glyph('quotesinglbase', 0x201A)
def quotesinglbase():
    return G([comma_shape(70, 92)], 232)


@glyph('quotedblbase', 0x201E)
def quotedblbase():
    return G([comma_shape(70, 92), comma_shape(70 + 136, 92)], 232 + 136)


# ---------------------------------------------------------------- dashes

DASH_Y = 204


@glyph('hyphen', 0x2D)
def hyphen():
    return G([cut_bar(50, 290, DASH_Y, DASH_Y + 36)], 340)


@glyph('endash', 0x2013)
def endash():
    return G([rect(40, DASH_Y + 4, 500, DASH_Y + 4 + THIN)], 540)


@glyph('emdash', 0x2014)
def emdash():
    return G([rect(40, DASH_Y + 4, 880, DASH_Y + 4 + THIN)], 920)


@glyph('underscore', 0x5F)
def underscore():
    return G([rect(0, -150, 500, -150 + HR)], 500)


# ---------------------------------------------------------------- brackets

BR_TOP, BR_BOT = ASC + 30, DESC + 30


@glyph('parenleft', 0x28)
def parenleft():
    mid = (BR_TOP + BR_BOT) / 2
    s = stroke([
        N(250, BR_TOP, HR, d=236, to=0.55),
        N(96, mid, 74, d=270, ti=0.6, to=0.6),
        N(250, BR_BOT, HR, d=304, ti=0.55),
    ], start_cut=0, end_cut=0)
    return G([s], 300)


@glyph('parenright', 0x29)
def parenright():
    g = parenleft()
    return G([p.mirror_x(150) for p in g.parts], 300)


@glyph('bracketleft', 0x5B)
def bracketleft():
    x = 96
    parts = [rect(x, BR_BOT, x + 40, BR_TOP), rect(x, BR_TOP - HR, x + 170, BR_TOP), rect(x, BR_BOT, x + 170, BR_BOT + HR)]
    return G(parts, 300)


@glyph('bracketright', 0x5D)
def bracketright():
    g = bracketleft()
    return G([p.mirror_x(150) for p in g.parts], 300)


@glyph('braceleft', 0x7B)
def braceleft():
    mid = (BR_TOP + BR_BOT) / 2
    xs = 168
    up = stroke([
        N(274, BR_TOP - 13, HR, d=180, to=0.6),
        N(xs, BR_TOP - 110, 56, d=270, ti=0.6),
        N(xs, mid + 120, 56, d=270, to=0.6),
        N(64, mid, HR, d=198, ti=0.5),
    ], end_cut=90)
    lo = up.mirror_y(mid)
    return G([up, lo], 320)


@glyph('braceright', 0x7D)
def braceright():
    g = braceleft()
    return G([p.mirror_x(160) for p in g.parts], 320)


# ---------------------------------------------------------------- strokes


@glyph('slash', 0x2F)
def slash():
    return G([poly([(20, BR_BOT), (20 + 36, BR_BOT), (340, BR_TOP), (340 - 36, BR_TOP)])], 360)


@glyph('backslash', 0x5C)
def backslash():
    g = slash()
    return G([p.mirror_x(180) for p in g.parts], 360)


@glyph('bar', 0x7C)
def bar():
    return G([rect(120, BR_BOT, 120 + 32, BR_TOP)], 272)


MATH_Y = 250      # axis of the maths signs
MATH_W = 440


@glyph('plus', 0x2B)
def plus():
    x0 = 60
    cx = x0 + MATH_W / 2
    return G([rect(x0, MATH_Y - THIN / 2, x0 + MATH_W, MATH_Y + THIN / 2),
              rect(cx - THIN / 2, MATH_Y - MATH_W / 2, cx + THIN / 2, MATH_Y + MATH_W / 2)], MATH_W + 120)


@glyph('minus', 0x2212)
def minus():
    return G([rect(60, MATH_Y - THIN / 2, 60 + MATH_W, MATH_Y + THIN / 2)], MATH_W + 120)


@glyph('equal', 0x3D)
def equal():
    return G([rect(60, MATH_Y + 62, 60 + MATH_W, MATH_Y + 62 + THIN),
              rect(60, MATH_Y - 62 - THIN, 60 + MATH_W, MATH_Y - 62)], MATH_W + 120)


@glyph('multiply', 0xD7)
def multiply():
    cx = 60 + MATH_W / 2
    a = rect(cx - THIN / 2, MATH_Y - 250, cx + THIN / 2, MATH_Y + 250)
    return G([a.rotate(45, cx, MATH_Y), a.rotate(-45, cx, MATH_Y)], MATH_W + 120)


@glyph('divide', 0xF7)
def divide():
    cx = 60 + MATH_W / 2
    return G([rect(60, MATH_Y - THIN / 2, 60 + MATH_W, MATH_Y + THIN / 2),
              diamond(cx, MATH_Y + 160, DIA_A * 0.8, DIA_B * 0.8), diamond(cx, MATH_Y - 160, DIA_A * 0.8, DIA_B * 0.8)], MATH_W + 120)


def _chevron(x0, x1, flip=False):
    h = 190
    pts_outer = [(x1, MATH_Y + h), (x0, MATH_Y), (x1, MATH_Y - h)]
    t = THIN + 4
    k = math.hypot(x1 - x0, h) / h * t / 2    # horizontal half-thickness along the axis
    a = poly([(x1, MATH_Y + h), (x1, MATH_Y + h - t * 1.12), (x0 + 2 * k, MATH_Y), (x1, MATH_Y - h + t * 1.12), (x1, MATH_Y - h), (x0, MATH_Y)])
    return a.mirror_x((x0 + x1) / 2) if flip else a


@glyph('less', 0x3C)
def less():
    return G([_chevron(70, 70 + 420)], 420 + 140)


@glyph('greater', 0x3E)
def greater():
    return G([_chevron(70, 70 + 420, flip=True)], 420 + 140)


@glyph('asciicircum', 0x5E)
def asciicircum():
    cx = 250
    t = 34
    return G([poly([(cx, CAP + 20), (cx + 178, CAP - 250), (cx + 178 - t, CAP - 250), (cx, CAP - 36), (cx - 178 + t, CAP - 250), (cx - 178, CAP - 250)])], 500)


@glyph('asciitilde', 0x7E)
def asciitilde():
    s = stroke([
        N(64, MATH_Y - 30, HR, d=62, to=0.5),
        N(170, MATH_Y + 52, 58, d=0, ti=0.6, to=0.75),
        N(330, MATH_Y - 52, 58, d=0, ti=0.75, to=0.6),
        N(436, MATH_Y + 30, HR, d=62, ti=0.5),
    ], start_cut=CUT_SIDE - 20, end_cut=CUT_SIDE - 20)
    return G([s], 500)


@glyph('grave', 0x60)
def grave():
    return G([poly([(70, ASC + 10), (154, ASC + 10 - 6), (232, ASC - 150), (212, ASC - 156)])], 300)


@glyph('asterisk', 0x2A)
def asterisk():
    # five diamond petals, one every 72 degrees: the pentagram behind the 18-degree cut
    cx, cy = 210, CAP - 150
    petal = poly([(cx, cy - 6), (cx + 26, cy + 64), (cx, cy + 172), (cx - 26, cy + 64)])
    return G([petal.rotate(72 * i, cx, cy) for i in range(5)], 420)


@glyph('numbersign', 0x23)
def numbersign():
    x0 = 50
    w = 500
    k = TAN_CUT
    def post(x):
        return poly([(x, 0), (x + 34, 0), (x + 34 + CAP * k, CAP), (x + CAP * k, CAP)])
    parts = [post(x0 + 70), post(x0 + 260),
             rect(x0 + 30, 448, x0 + w + 40, 448 + THIN), rect(x0, 222, x0 + w + 10, 222 + THIN)]
    return G(parts, w + 140)


@glyph('percent', 0x25)
def percent():
    def small(cx, cy):
        return stroke([
            N(cx + 110, cy, 62, d=90), N(cx, cy + 158, HR - 2, d=180),
            N(cx - 110, cy, 62, d=270), N(cx, cy - 158, HR - 2, d=0)], closed=True, tension=0.565)
    x0 = 46
    parts = [small(x0 + 141, CAP - 160), small(x0 + 579, 160),
             poly([(x0 + 150, -20), (x0 + 150 + 34, -20), (x0 + 590, CAP + 20), (x0 + 590 - 34, CAP + 20)])]
    return G(parts, x0 + 720 + 46)


@glyph('dollar', 0x24)
def dollar():
    sb = 60
    w = 430
    h = CAP - 30
    y0 = 15
    nodes = [
        N(sb + w * 0.91, y0 + h - 172, HR + 16, d=96, to=0.6),
        N(sb + w * 0.50, y0 + h + 10 - HR / 2, HR + 2, d=180, ti=0.58),
        N(sb + T * 0.42, y0 + h - 176, T * 0.84, d=270, to=0.62),
        N(sb + w * 0.50, y0 + h * 0.515, T, d=-27, ti=0.7, to=0.7),
        N(sb + w - T * 0.44, y0 + 180, T * 0.9, d=270, ti=0.62),
        N(sb + w * 0.48, y0 - 10 + HR / 2, HR + 2, d=180, to=0.58),
        N(sb + w * 0.04, y0 + 166, HR + 16, d=84, ti=0.6),
    ]
    cx = sb + w / 2
    parts = [stroke(nodes, start_cut=CUT_UP, end_cut=CUT_UP), rect(cx - 14, -84, cx + 14, CAP + 84)]
    return G(parts, sb + w + 60)


@glyph('ampersand', 0x26)
def ampersand():
    sb = 50
    s1 = stroke([
        N(sb + 640, 392, HR + 2, d=232, to=0.5),
        N(sb + 318, -OS_C + 15, 32, d=180, ti=0.62),
        N(sb + 49, 190, 98, d=90, to=0.62),
        N(sb + 262, 432, 38, d=34, ti=0.5, to=0.5),
        N(sb + 408 - 18, 590, 36, d=90, ti=0.6),
        N(sb + 296, CAP + OS_C - 14, 28, d=180),
        N(sb + 172 + 42, 566, 84, d=270, to=0.5),
        N(sb + 372, 300, 106, d=-52, ti=0.42, to=0.4),
        N(sb + 606, 0, 100, d=-50, ti=0.4),
    ], start_cut=0, end_cut=0)
    parts = [s1, rect(sb + 566, 392 - 4, sb + 730, 392 - 4 + HR), rect(sb + 540, 0, sb + 722, HR)]
    return G(parts, sb + 730 + 40)


@glyph('at', 0x40)
def at():
    sb = 50
    cx, cy = sb + 400, 250
    inner = stroke([
        N(cx + 96, cy, 74, d=90), N(cx - 14, cy + 150, HR, d=180),
        N(cx - 128, cy, 80, d=270), N(cx - 14, cy - 150, HR, d=0)], closed=True, tension=0.565)
    outer = stroke([
        N(cx + 96, cy + 110, 74, d=270),
        N(cx + 96, cy - 60, 74, d=270, to=0.6),
        N(cx + 210, cy - 150, HR + 4, d=0, ti=0.6, to=0.6),
        N(cx + 340, cy + 20, 62, d=90, ti=0.6),
        N(cx, cy + 420, HR, d=180),
        N(cx - 352, cy, 62, d=270),
        N(cx, cy - 420, HR, d=0, to=0.55),
        N(cx + 250, cy - 330, HR, d=34, ti=0.5),
    ], end_cut=CUT_SIDE)
    return G([inner, outer], sb + 800 + 50)


@glyph('sterling', 0xA3)
def sterling():
    sb = 56
    xs = sb + 150                      # centre of the stem
    hook = stroke([
        N(sb + 408, CAP - 168, HR + 16, d=98, to=0.6),
        N(sb + 290, CAP + OS_C - 14, 30, d=180, ti=0.6, to=0.6),
        N(xs, CAP - 210, T, d=270, ti=0.62),
        N(xs, 150, T, d=270, to=0.5),
        N(xs - 60, 26, 44, d=220, ti=0.5),
    ], start_cut=CUT_UP, end_cut=0)
    base = stroke([
        N(sb + 6, 30, 30, d=-12, to=0.5),
        N(sb + 150, 26, 54, d=0, ti=0.5, to=0.55),
        N(sb + 330, 22, 44, d=0, ti=0.55, to=0.5),
        N(sb + 448, 74, HR, d=50, ti=0.5),
    ], start_cut=90, end_cut=CUT_SIDE)
    bar = cut_bar(sb + 20, sb + 340, 352, 352 + HR)
    return G([hook, base, bar], sb + 448 + 50)


@glyph('Euro', 0x20AC)
def euro():
    sb = 92
    w = 500
    cx = sb + w / 2 + 6
    body = stroke([
        N(sb + w - 20, CAP - 190, HR + 16, d=94, to=0.6),
        N(cx + 20, CAP + OS_C - 14, HR + 2, d=180, ti=0.58),
        N(sb + (T + 4) / 2, CAP / 2, T + 4, d=270),
        N(cx + 30, -OS_C + 15, HR + 4, d=0, to=0.6),
        N(sb + w, 144, HR - 2, d=58, ti=0.5),
    ], start_cut=CUT_UP, end_cut=CUT_SIDE)
    bars = [cut_bar(sb - 70, sb + 330, 400, 400 + HR), cut_bar(sb - 70, sb + 300, 290, 290 + HR)]
    return G([body] + bars, sb + w + 50)
