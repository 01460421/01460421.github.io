"""Turn the drawn glyphs into font binaries (OTF / TTF / WOFF2) and a UFO source."""
import math
import os

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.bezierTools import splitCubicAtT
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

from .geom import Shape
from .params import *  # noqa: F401,F403


def _area(contour):
    # signed area via polyline through on-curve + control points (good enough for orientation)
    pts = [contour[0]]
    for seg in contour[1:]:
        pts.extend(seg[1:])
    a = 0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return a / 2


def _extrema_ts(p0, p1, p2, p3):
    ts = []
    for k in (0, 1):
        a = -p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]
        b = 2 * (p0[k] - 2 * p1[k] + p2[k])
        c = p1[k] - p0[k]
        if abs(a) < 1e-9:
            if abs(b) > 1e-9:
                ts.append(-c / b)
        else:
            disc = b * b - 4 * a * c
            if disc >= 0:
                r = math.sqrt(disc)
                ts += [(-b + r) / (2 * a), (-b - r) / (2 * a)]
    return sorted(t for t in ts if 0.02 < t < 0.98)


def clean(shape, add_extrema=True):
    """Round to the unit grid, drop degenerate segments, add missing extrema."""
    out = []
    for c in shape.contours:
        cur = c[0]
        segs = []
        for seg in c[1:]:
            if seg[0] == 'C' and add_extrema:
                ts = _extrema_ts(cur, seg[1], seg[2], seg[3])
                if ts:
                    for piece in splitCubicAtT(cur, seg[1], seg[2], seg[3], *ts):
                        segs.append(('C', piece[1], piece[2], piece[3]))
                else:
                    segs.append(seg)
            else:
                segs.append(seg)
            cur = seg[-1]
        rnd = lambda p: (round(p[0]), round(p[1]))
        start = rnd(c[0])
        nc = [start]
        cur = start
        for seg in segs:
            pts = tuple(rnd(p) for p in seg[1:])
            if pts[-1] == cur and (seg[0] == 'L' or (pts[0] == cur and pts[1] == cur)):
                continue
            if seg[0] == 'C':
                # a cubic whose handles are collinear with its chord is a line
                (x0, y0), (x3, y3) = cur, pts[2]
                dx, dy = x3 - x0, y3 - y0
                ln = math.hypot(dx, dy)
                if ln > 0:
                    d1 = abs((pts[0][0] - x0) * dy - (pts[0][1] - y0) * dx) / ln
                    d2 = abs((pts[1][0] - x0) * dy - (pts[1][1] - y0) * dx) / ln
                    if d1 < 0.6 and d2 < 0.6:
                        nc.append(('L', pts[2]))
                        cur = pts[2]
                        continue
                nc.append(('C',) + pts)
            else:
                nc.append(('L', pts[0]))
            cur = pts[-1]
        # merge collinear consecutive lines
        merged = [nc[0]]
        for seg in nc[1:]:
            if seg[0] == 'L' and len(merged) > 1 and merged[-1][0] == 'L':
                prev_start = merged[-2][-1] if len(merged) > 2 else merged[0]
                a, b, cpt = prev_start, merged[-1][1], seg[1]
                cross = (b[0] - a[0]) * (cpt[1] - a[1]) - (b[1] - a[1]) * (cpt[0] - a[0])
                dot = (b[0] - a[0]) * (cpt[0] - b[0]) + (b[1] - a[1]) * (cpt[1] - b[1])
                if cross == 0 and dot > 0:
                    merged[-1] = seg
                    continue
            merged.append(seg)
        nc = merged
        if nc[-1][-1] == nc[0] and nc[-1][0] == 'L':
            nc = nc[:-1]
        if len(nc) >= 3 or (len(nc) >= 2 and any(s[0] == 'C' for s in nc[1:])):
            if abs(_area(nc)) > 4:
                out.append(nc)
    return Shape(out)


def orient(shape, outer_ccw=True):
    """Make outer contours counter-clockwise (PostScript) or clockwise (TrueType)."""
    if not shape.contours:
        return shape
    big = max(shape.contours, key=lambda c: abs(_area(c)))
    ccw = _area(big) > 0
    return shape if ccw == outer_ccw else shape.reversed()


FAMILY = 'NiYu'
STYLE = 'Regular'
VERSION = '1.000'
REPO = 'https://github.com/01460421/01460421.github.io'
COPYRIGHT = f'Copyright 2026 The NiYu Project Authors ({REPO})'
LICENSE = ('This Font Software is licensed under the SIL Open Font License, Version 1.1. '
           'This license is available with a FAQ at: https://openfontlicense.org')
DESCRIPTION = ('NiYu (逆雨, "reverse rain") is a display serif built on a transitional skeleton. '
               'Three rules give it its character: every drop terminal points to the sky, hairlines '
               'stop a slit short of the stems they meet, and every dot is a 72-degree diamond.')
ASCENT, DESCENT = 920, -260      # hhea == typo, line gap 0; clears accented capitals


def _names():
    return {
        'copyright': COPYRIGHT,
        'familyName': FAMILY,
        'styleName': STYLE,
        'uniqueFontIdentifier': f'{VERSION};NIYU;{FAMILY}-{STYLE}',
        'fullName': f'{FAMILY} {STYLE}',
        'psName': f'{FAMILY}-{STYLE}',
        'version': f'Version {VERSION}',
        'manufacturer': 'The NiYu Project',
        'designer': 'The NiYu Project Authors',
        'description': DESCRIPTION,
        'vendorURL': REPO,
        'designerURL': REPO,
        'licenseDescription': LICENSE,
        'licenseInfoURL': 'https://openfontlicense.org',
        'sampleText': 'Rain rises over the quay in 1999.',
    }


def build(drawn, cmap, fea, out_otf, out_ttf):
    """drawn: {glyph name: (Shape, advance)} — shapes already boolean-resolved.
    cmap: {codepoint: glyph name}."""
    order = ['.notdef'] + [g for g in drawn if g != '.notdef']
    names = _names()
    inked = [s.bounds() for s, _ in drawn.values() if s.contours]
    y_max = int(math.ceil(max(b[3] for b in inked)))
    y_min = int(math.floor(min(b[1] for b in inked)))
    for is_ttf, path in ((False, out_otf), (True, out_ttf)):
        fb = FontBuilder(UPM, isTTF=is_ttf)
        fb.setupGlyphOrder(order)
        fb.setupCharacterMap(cmap)
        metrics = {}
        glyphs = {}
        for name in order:
            shape, adv = drawn[name]
            adv = int(round(adv))
            sh = orient(shape, outer_ccw=not is_ttf)
            if is_ttf:
                tp = TTGlyphPen(None)
                sh.draw(Cu2QuPen(tp, max_err=0.8, reverse_direction=False))
                glyphs[name] = tp.glyph()
            else:
                pen = T2CharStringPen(adv, None)
                sh.draw(pen)
                glyphs[name] = pen.getCharString()
            xmin = int(round(shape.bounds()[0])) if shape.contours else 0
            metrics[name] = (adv, xmin)
        if is_ttf:
            fb.setupGlyf(glyphs)
        else:
            fb.setupCFF(names['psName'], {'FullName': names['fullName'], 'FamilyName': FAMILY, 'Weight': 'Regular',
                                          'Notice': COPYRIGHT, 'version': VERSION}, glyphs, {})
        fb.setupHorizontalMetrics(metrics)
        fb.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT, lineGap=0)
        fb.setupNameTable(names, mac=False)
        fb.setupOS2(
            version=4,
            sTypoAscender=ASCENT, sTypoDescender=DESCENT, sTypoLineGap=0,
            usWinAscent=max(y_max, ASCENT), usWinDescent=max(-y_min, -DESCENT),
            sxHeight=XH, sCapHeight=CAP, achVendID='NIYU',
            fsSelection=0x40 | 0x80,  # REGULAR + USE_TYPO_METRICS
            usWeightClass=400, usWidthClass=5, fsType=0,
            ySubscriptXSize=650, ySubscriptYSize=600, ySubscriptYOffset=75,
            ySuperscriptXSize=650, ySuperscriptYSize=600, ySuperscriptYOffset=350,
            yStrikeoutSize=HAIR, yStrikeoutPosition=int(XH * 0.55),
            panose=dict(bFamilyType=2, bSerifStyle=2, bWeight=5, bProportion=3, bContrast=8,
                        bStrokeVariation=2, bArmStyle=0, bLetterForm=2, bMidline=0, bXHeight=3),
        )
        fb.setupPost(underlinePosition=-110, underlineThickness=HAIR, isFixedPitch=0)
        if fea:
            addOpenTypeFeaturesFromString(fb.font, fea)
        font = fb.font
        font['head'].fontRevision = float(VERSION)
        font['OS/2'].recalcUnicodeRanges(font)
        font['OS/2'].recalcCodePageRanges(font)
        if 'ltag' in font:
            del font['ltag']
        if is_ttf:
            # unhinted TrueType: smooth at all sizes, smart drop-out control on
            from fontTools.ttLib import newTable
            gasp = newTable('gasp')
            gasp.gaspRange = {0xFFFF: 15}
            font['gasp'] = gasp
            prep = newTable('prep')
            from fontTools.ttLib.tables import ttProgram
            prep.program = ttProgram.Program()
            prep.program.fromAssembly(['PUSHW[]', '511', 'SCANCTRL[]', 'PUSHB[]', '4', 'SCANTYPE[]'])
            font['prep'] = prep
        font.save(path)
    return order


def save_woff2(src, dst):
    from fontTools.ttLib import TTFont
    f = TTFont(src)
    f.flavor = 'woff2'
    f.save(dst)


def save_ufo(drawn, cmap, fea, path):
    """Editable source for FontForge / Fontra / Glyphs (workflow §4)."""
    import shutil

    import ufoLib2
    font = ufoLib2.Font()
    i = font.info
    i.familyName, i.styleName = FAMILY, STYLE
    i.unitsPerEm, i.ascender, i.descender = UPM, ASC, DESC
    i.capHeight, i.xHeight = CAP, XH
    i.versionMajor, i.versionMinor = 1, 0
    i.copyright = COPYRIGHT
    i.openTypeNameLicense = LICENSE
    i.openTypeNameLicenseURL = 'https://openfontlicense.org'
    i.openTypeNameDescription = DESCRIPTION
    i.openTypeHheaAscender, i.openTypeHheaDescender, i.openTypeHheaLineGap = ASCENT, DESCENT, 0
    i.openTypeOS2TypoAscender, i.openTypeOS2TypoDescender, i.openTypeOS2TypoLineGap = ASCENT, DESCENT, 0
    i.postscriptFontName = f'{FAMILY}-{STYLE}'
    rev = {}
    for cp, name in cmap.items():
        rev.setdefault(name, []).append(cp)
    for name, (shape, adv) in drawn.items():
        g = font.newGlyph(name)
        g.width = int(round(adv))
        g.unicodes = sorted(rev.get(name, []))
        orient(shape, outer_ccw=True).draw(g.getPen())
    font.features.text = fea
    font.lib['public.glyphOrder'] = list(drawn)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        shutil.rmtree(path)
    font.save(path)
