"""Accented letters (workflow §6 step 11): base + mark, placed by anchors.
The dieresis is two diamonds, like every other dot."""
from .geom import N, Outline, poly, rect, stroke
from .params import *  # noqa: F401,F403
from .parts import G, diamond
from .registry import GLYPHS, glyph

MARK_Y = XH + 66        # bottom of a mark over a lowercase letter


def m_acute():
    return [poly([(-52, 0), (-30, -8), (74, 122), (18, 148)])]


def m_grave():
    return [poly([(52, 0), (30, -8), (-74, 122), (-18, 148)])]


def m_circumflex():
    t = 40
    return [poly([(0, 150), (118, 6), (92, -6), (0, 92), (-92, -6), (-118, 6)])]


def m_caron():
    return [poly([(0, -6), (118, 138), (92, 150), (0, 52), (-92, 150), (-118, 138)])]


def m_tilde():
    return [stroke([
        N(-128, 36, HAIR, d=64, to=0.5),
        N(-56, 104, 48, d=0, ti=0.6, to=0.75),
        N(56, 44, 48, d=0, ti=0.75, to=0.6),
        N(128, 112, HAIR, d=64, ti=0.5),
    ], start_cut=90, end_cut=90)]


def m_dieresis():
    a, b = DIA_A * 0.8, DIA_B * 0.8
    return [diamond(-76, b + 4, a, b), diamond(76, b + 4, a, b)]


def m_ring():
    r = 70
    o = Outline(r, r + 8)
    k = 0.5523
    def circ(rad, rev=False):
        cy = r + 8
        pts = Outline(rad, cy)
        pts.C((rad, cy + k * rad), (k * rad, cy + rad), (0, cy + rad))
        pts.C((-k * rad, cy + rad), (-rad, cy + k * rad), (-rad, cy))
        pts.C((-rad, cy - k * rad), (-k * rad, cy - rad), (0, cy - rad))
        pts.C((k * rad, cy - rad), (rad, cy - k * rad), (rad, cy))
        s = pts.close()
        return s.reversed() if rev else s
    return [circ(r) + circ(r - HAIR - 2, True)]


def m_macron():
    return [rect(-110, 44, 110, 44 + HAIR + 6)]


def m_cedilla():
    return [stroke([
        N(4, 8, 22, d=262, to=0.4),
        N(52, -92, 46, d=270, ti=0.6, to=0.6),
        N(-6, -170, 30, d=180, ti=0.6, to=0.4),
        N(-62, -150, 22, d=140, ti=0.4),
    ])]


MARKS = {
    'grave': m_grave, 'acute': m_acute, 'circumflex': m_circumflex, 'tilde': m_tilde,
    'dieresis': m_dieresis, 'ring': m_ring, 'caron': m_caron, 'macron': m_macron, 'cedilla': m_cedilla,
}

# standalone spacing marks
for _n, _u in (('acute', 0xB4), ('circumflex', 0x2C6), ('tilde', 0x2DC), ('dieresis', 0xA8),
               ('ring', 0x2DA), ('caron', 0x2C7), ('macron', 0xAF), ('cedilla', 0xB8)):
    def _mk(n=_n):
        dy = 0 if n == 'cedilla' else MARK_Y
        return G([p.translate(170, dy) for p in MARKS[n]()], 340)
    glyph(_n, _u)(_mk)

# (base, top anchor dx from the centre of the advance)
LOWER = {'a': -6, 'c': -8, 'e': -2, 'dotlessi': -4, 'n': 4, 'o': 0, 'u': -2, 'y': 6, 's': 0, 'z': 4}
UPPER = {'A': -8, 'C': 22, 'E': -8, 'I': 0, 'N': 0, 'O': 0, 'U': 0, 'Y': 4, 'S': 0, 'Z': 4}

COMPOSE = [
    # name, base, mark, unicode
    ('agrave', 'a', 'grave', 0xE0), ('aacute', 'a', 'acute', 0xE1), ('acircumflex', 'a', 'circumflex', 0xE2),
    ('atilde', 'a', 'tilde', 0xE3), ('adieresis', 'a', 'dieresis', 0xE4), ('aring', 'a', 'ring', 0xE5),
    ('ccedilla', 'c', 'cedilla', 0xE7),
    ('egrave', 'e', 'grave', 0xE8), ('eacute', 'e', 'acute', 0xE9), ('ecircumflex', 'e', 'circumflex', 0xEA),
    ('edieresis', 'e', 'dieresis', 0xEB),
    ('igrave', 'dotlessi', 'grave', 0xEC), ('iacute', 'dotlessi', 'acute', 0xED),
    ('icircumflex', 'dotlessi', 'circumflex', 0xEE), ('idieresis', 'dotlessi', 'dieresis', 0xEF),
    ('ntilde', 'n', 'tilde', 0xF1),
    ('ograve', 'o', 'grave', 0xF2), ('oacute', 'o', 'acute', 0xF3), ('ocircumflex', 'o', 'circumflex', 0xF4),
    ('otilde', 'o', 'tilde', 0xF5), ('odieresis', 'o', 'dieresis', 0xF6),
    ('ugrave', 'u', 'grave', 0xF9), ('uacute', 'u', 'acute', 0xFA), ('ucircumflex', 'u', 'circumflex', 0xFB),
    ('udieresis', 'u', 'dieresis', 0xFC),
    ('yacute', 'y', 'acute', 0xFD), ('ydieresis', 'y', 'dieresis', 0xFF),
    ('scaron', 's', 'caron', 0x161), ('zcaron', 'z', 'caron', 0x17E),
    ('amacron', 'a', 'macron', 0x101), ('emacron', 'e', 'macron', 0x113), ('imacron', 'dotlessi', 'macron', 0x12B),
    ('omacron', 'o', 'macron', 0x14D), ('umacron', 'u', 'macron', 0x16B),
    ('Agrave', 'A', 'grave', 0xC0), ('Aacute', 'A', 'acute', 0xC1), ('Acircumflex', 'A', 'circumflex', 0xC2),
    ('Atilde', 'A', 'tilde', 0xC3), ('Adieresis', 'A', 'dieresis', 0xC4), ('Aring', 'A', 'ring', 0xC5),
    ('Ccedilla', 'C', 'cedilla', 0xC7),
    ('Egrave', 'E', 'grave', 0xC8), ('Eacute', 'E', 'acute', 0xC9), ('Ecircumflex', 'E', 'circumflex', 0xCA),
    ('Edieresis', 'E', 'dieresis', 0xCB),
    ('Igrave', 'I', 'grave', 0xCC), ('Iacute', 'I', 'acute', 0xCD), ('Icircumflex', 'I', 'circumflex', 0xCE),
    ('Idieresis', 'I', 'dieresis', 0xCF),
    ('Ntilde', 'N', 'tilde', 0xD1),
    ('Ograve', 'O', 'grave', 0xD2), ('Oacute', 'O', 'acute', 0xD3), ('Ocircumflex', 'O', 'circumflex', 0xD4),
    ('Otilde', 'O', 'tilde', 0xD5), ('Odieresis', 'O', 'dieresis', 0xD6),
    ('Ugrave', 'U', 'grave', 0xD9), ('Uacute', 'U', 'acute', 0xDA), ('Ucircumflex', 'U', 'circumflex', 0xDB),
    ('Udieresis', 'U', 'dieresis', 0xDC),
    ('Yacute', 'Y', 'acute', 0xDD), ('Ydieresis', 'Y', 'dieresis', 0x178),
    ('Scaron', 'S', 'caron', 0x160), ('Zcaron', 'Z', 'caron', 0x17D),
    ('Amacron', 'A', 'macron', 0x100), ('Emacron', 'E', 'macron', 0x112), ('Imacron', 'I', 'macron', 0x12A),
    ('Omacron', 'O', 'macron', 0x14C), ('Umacron', 'U', 'macron', 0x16A),
]


def _compose(base, mark, height, dx, scale=1.0):
    g = GLYPHS[base][0]()
    ax = g.adv / 2 + dx
    if mark == 'cedilla':
        if base in ('c', 'C', 'c.sc'):
            ax += 14
        parts = [p.scale(scale, scale).translate(ax, 0) for p in MARKS[mark]()]
    else:
        dy = height + (MARK_Y - XH)
        if height > XH:
            dy -= 14           # marks sit a little closer on capitals
        parts = [p.scale(scale, scale).translate(ax, dy) for p in MARKS[mark]()]
    return G(g.parts + parts, g.adv)


for _name, _base, _mark, _uni in COMPOSE:
    if _base in LOWER:
        glyph(_name, _uni)(lambda b=_base, mk=_mark: _compose(b, mk, XH, LOWER[b]))
    else:
        glyph(_name, _uni)(lambda b=_base, mk=_mark: _compose(b, mk, CAP, UPPER[b]))
        # small-cap version of the accented capital
        glyph(_name.lower() + '.sc')(
            lambda b=_base, mk=_mark: _compose(b.lower() + '.sc', mk, SC, UPPER[b] * 0.76, scale=0.9))


@glyph('exclamdown', 0xA1)
def exclamdown():
    g = GLYPHS['exclam'][0]()
    return G([p.rotate(180, g.adv / 2, (CAP + 4 - 10 + DESC + 0) / 2 + 118) for p in g.parts], g.adv)


@glyph('questiondown', 0xBF)
def questiondown():
    g = GLYPHS['question'][0]()
    return G([p.rotate(180, g.adv / 2, (CAP + 4 - 10 + DESC + 0) / 2 + 118) for p in g.parts], g.adv)


def _guil(n, flip):
    t = 38
    parts = []
    for i in range(n):
        x0 = 60 + i * 156
        parts.append(poly([(x0 + 150, 392), (x0 + 150 - t, 392), (x0, 235), (x0 + 150 - t, 78), (x0 + 150, 78), (x0 + t + 6, 235)]))
    adv = 60 * 2 + 150 + 156 * (n - 1)
    if flip:
        parts = [p.mirror_x(adv / 2) for p in parts]
    return G(parts, adv)


glyph('guilsinglleft', 0x2039)(lambda: _guil(1, False))
glyph('guilsinglright', 0x203A)(lambda: _guil(1, True))
glyph('guillemotleft', 0xAB)(lambda: _guil(2, False))
glyph('guillemotright', 0xBB)(lambda: _guil(2, True))


@glyph('degree', 0xB0)
def degree():
    from .geom import ellipse
    r = 104
    return G([ellipse(160, CAP - r + 8, r, r) + ellipse(160, CAP - r + 8, r - 30, r - 30).reversed()], 320)
