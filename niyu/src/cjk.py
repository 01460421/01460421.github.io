"""Chinese (workflow §11). The base is Noto Serif TC (SIL OFL 1.1), whose
variable-font outlines keep every brush stroke as its own contour. That lets
the three NiYu rules be applied stroke by stroke rather than to a finished
silhouette:

    菱形點  every 點 becomes the 72-degree diamond
            (under the rain radical 雨 the dots are drops that rise instead)
    斷線    thin 橫 strokes stop a slit short of the thick strokes they meet
    逆雨滴  hooks (鉤) that point upward end in a rising drop

The derived glyphs are renamed into NiYu and stay under the OFL.
"""
import glob
import math
import os
import pickle
import subprocess
import tarfile

import pathops
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont
from pathops import LineCap, LineJoin, PathOp

from .geom import Shape, poly
from .params import *  # noqa: F401,F403
from .parts import diamond, drop

PACKAGE = '@fontsource-variable/noto-serif-tc@5.3.1'
BASE_COPYRIGHT = '(c) 2017-2024 Adobe (http://www.adobe.com/).'

# ---- tuning ---------------------------------------------------------------
WGHT = 560            # instance of the base that matches the NiYu stems (vertical ~94, hairline 29)
GAP_CJK = 14          # 斷線 slit
THIN_MAX = 52         # mean thickness below which a horizontal counts as thin
DOT_MAX = 250         # largest extent of a 點
DROP_R = 33           # bulb radius of a hook drop
NUB = 64              # pieces of a cut bar narrower than this are stubs and are dropped
CROSS = 36            # a bar that runs on this far past a stroke crosses it and is not cut
RAIN = (0x96E8, 0x9750)   # Kangxi radical 173 雨 in the URO


# ---------------------------------------------------------------------------
# base font access
# ---------------------------------------------------------------------------


class Base:
    def __init__(self, cache_dir):
        self.dir = os.path.join(cache_dir, 'package', 'files')
        if not os.path.isdir(self.dir):
            fetch(cache_dir)
        self.fonts = {}
        self.cov = {}
        for fp in sorted(glob.glob(os.path.join(self.dir, '*.woff2'))):
            f = TTFont(fp)
            self.fonts[fp] = f
            for cp, name in f.getBestCmap().items():
                self.cov[cp] = (fp, name)
        self._gs = {}

    def glyphset(self, fp, wght):
        key = (fp, wght)
        if key not in self._gs:
            self._gs[key] = self.fonts[fp].getGlyphSet(location={'wght': wght})
        return self._gs[key]

    def strokes(self, cp, wght=WGHT):
        """Contours of one character, each as a single-contour cubic Shape."""
        fp, name = self.cov[cp]
        gs = self.glyphset(fp, wght)
        pen = DecomposingRecordingPen(gs)
        gs[name].draw(pen)
        out, cur, last = [], None, None
        for op, pts in pen.value:
            if op == 'moveTo':
                cur = [pts[0]]
                last = pts[0]
            elif op == 'lineTo':
                cur.append(('L', pts[0]))
                last = pts[0]
            elif op == 'qCurveTo':
                q = list(pts)
                for i in range(len(q) - 1):
                    ctrl = q[i]
                    end = q[-1] if i == len(q) - 2 else ((q[i][0] + q[i + 1][0]) / 2, (q[i][1] + q[i + 1][1]) / 2)
                    c1 = (last[0] + 2 / 3 * (ctrl[0] - last[0]), last[1] + 2 / 3 * (ctrl[1] - last[1]))
                    c2 = (end[0] + 2 / 3 * (ctrl[0] - end[0]), end[1] + 2 / 3 * (ctrl[1] - end[1]))
                    cur.append(('C', c1, c2, end))
                    last = end
            elif op == 'curveTo':
                cur.append(('C', pts[0], pts[1], pts[2]))
                last = pts[2]
            elif op in ('closePath', 'endPath'):
                if cur and len(cur) > 2:
                    out.append(cur)
                cur = None
        # TrueType outlines run clockwise; a counter-clockwise contour is a hole
        # and belongs to the smallest stroke that encloses it
        solids = [c for c in out if _signed_area(c) <= 0]
        holes = [c for c in out if _signed_area(c) > 0]
        shapes = [[c] for c in solids]
        boxes = [_bbox(c) for c in solids]
        for hc in holes:
            hb = _bbox(hc)
            best = None
            for i, b in enumerate(boxes):
                if b[0] <= hb[0] and b[1] <= hb[1] and b[2] >= hb[2] and b[3] >= hb[3]:
                    size = (b[2] - b[0]) * (b[3] - b[1])
                    if best is None or size < best[0]:
                        best = (size, i)
            if best is not None:
                shapes[best[1]].append(hc)
        out = [Shape(cs) for cs in shapes]
        adv = self.fonts[fp]['hmtx'][name][0]
        return out, adv


def fetch(cache_dir):
    """Download the base font slices from the npm registry (5.9 MB)."""
    os.makedirs(cache_dir, exist_ok=True)
    subprocess.run(['npm', 'pack', PACKAGE, '--silent'], cwd=cache_dir, check=True)
    tgz = sorted(glob.glob(os.path.join(cache_dir, '*.tgz')))[-1]
    with tarfile.open(tgz) as t:
        t.extractall(cache_dir, filter='data')


# ---------------------------------------------------------------------------
# stroke analysis
# ---------------------------------------------------------------------------


class Stroke:
    def __init__(self, shape):
        self.shape = shape
        self.path = shape.to_path()
        b = self.path.bounds
        self.x0, self.y0, self.x1, self.y1 = b
        self.w, self.h = b[2] - b[0], b[3] - b[1]
        self.area = abs(self.path.area)
        self.cx, self.cy = _centroid(shape)
        self.kind = self._classify()

    def _classify(self):
        w, h, a = self.w, self.h, self.area
        if w >= 2.2 * h and w > 90 and a / max(w, 1) <= THIN_MAX:
            return 'thin'
        solid = len(self.shape.contours) == 1          # a small 口 has a counter and is no dot
        if solid and max(w, h) <= DOT_MAX and 1200 <= a <= 17500 and a / max(w, h) >= 34 and min(w, h) >= 36:
            return 'dot'
        return 'thick'


def _poly_of(contour):
    pts = [contour[0]]
    for seg in contour[1:]:
        pts.extend(seg[1:])
    return pts


def _signed_area(contour):
    pts = _poly_of(contour)
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts))) / 2


def _bbox(contour):
    pts = _poly_of(contour)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _flat(shape, n=6):
    pts = []
    for c in shape.contours:
        cur = c[0]
        pts.append(cur)
        for s in c[1:]:
            if s[0] == 'L':
                pts.append(s[1])
            else:
                p0, p1, p2, p3 = cur, s[1], s[2], s[3]
                for i in range(1, n + 1):
                    t = i / n
                    mt = 1 - t
                    pts.append((mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0],
                                mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1]))
            cur = s[-1]
    return pts


def _centroid(shape):
    pts = _flat(Shape([shape.contours[0]]))
    a = cx = cy = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        k = x0 * y1 - x1 * y0
        a += k
        cx += (x0 + x1) * k
        cy += (y0 + y1) * k
    if abs(a) < 1e-6:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return sum(xs) / len(xs), sum(ys) / len(ys)
    return cx / (3 * a), cy / (3 * a)


def _expand(path, g):
    """The path grown outward by g on every side."""
    s = pathops.Path(path)
    s.stroke(2 * g, LineCap.BUTT_CAP, LineJoin.MITER_JOIN, 4)
    return pathops.op(path, s, PathOp.UNION, fix_winding=True)


def _pieces(path):
    """Split a path into its separate outer contours (with their holes)."""
    sh = Shape.from_path(path)
    return [Shape([c]) for c in sh.contours]


def _resample(shape, step=4.0):
    """Outline as points roughly `step` apart (first contour only)."""
    raw = _flat(Shape([shape.contours[0]]), n=10)
    raw.append(raw[0])
    out = [raw[0]]
    acc = 0.0
    for (x0, y0), (x1, y1) in zip(raw, raw[1:]):
        d = math.hypot(x1 - x0, y1 - y0)
        if d < 1e-9:
            continue
        t = step - acc
        while t <= d:
            out.append((x0 + (x1 - x0) * t / d, y0 + (y1 - y0) * t / d))
            t += step
        acc = (acc + d) % step
    return out


def hook_tips(stroke, reach=20.0, step=4.0):
    """Upward-pointing hook ends of a stroke: [(x, y, direction in degrees)].
    A hook is a sharp convex tip with a concave crotch close by on the
    outline — which is what tells it from the pointed head of a 點 or 捺."""
    pts = _resample(stroke.shape, step)
    n = len(pts)
    if n < 40:
        return []
    k = max(2, int(round(reach / step)))
    area2 = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    orient = 1.0 if area2 > 0 else -1.0        # +1: counter-clockwise outline
    turn = []
    for i in range(n):
        a, p, b = pts[(i - k) % n], pts[i], pts[(i + k) % n]
        v1 = (p[0] - a[0], p[1] - a[1])
        v2 = (b[0] - p[0], b[1] - p[1])
        l1, l2 = math.hypot(*v1), math.hypot(*v2)
        if l1 < 1e-6 or l2 < 1e-6:
            turn.append(0.0)
            continue
        ang = math.degrees(math.atan2(v1[0] * v2[1] - v1[1] * v2[0], v1[0] * v2[0] + v1[1] * v2[1]))
        turn.append(ang * orient)                # > 0 convex, < 0 concave
    tips = []
    span = int(240 / step)
    for i in range(n):
        t = turn[i]
        if t < 108:
            continue
        if any(turn[(i + j) % n] > t for j in range(-k, k + 1) if j):
            continue
        # a crotch nearby?
        if not any(turn[(i + j) % n] < -50 for j in range(-span, span + 1)):
            continue
        a, p, b = pts[(i - k) % n], pts[i], pts[(i + k) % n]
        # a hook closes a stroke, so it sits in the lower part of it; the
        # pointed head of a vertical sits at the top and is not a hook
        d = ((p[0] - a[0]) + (p[0] - b[0]), (p[1] - a[1]) + (p[1] - b[1]))
        ang = math.degrees(math.atan2(d[1], d[0])) % 360
        low = p[1] <= stroke.y0 + 0.55 * stroke.h
        # 臥鉤 (心): a long lying stroke whose hook rises at its right end
        lying = stroke.w >= 450 and p[0] >= stroke.x0 + 0.6 * stroke.w and 100 <= ang <= 170
        if not (low or lying):
            continue
        tips.append((p[0], p[1], ang))
    return tips


# ---------------------------------------------------------------------------
# the three rules
# ---------------------------------------------------------------------------


def transform(strokes, cp, log=None):
    """Apply 菱形點 / 斷線 / 逆雨滴 to the strokes of one character."""
    S = [Stroke(s) for s in strokes]
    rain = RAIN[0] <= cp <= RAIN[1]
    thick = [s for s in S if s.kind == 'thick']
    out = []
    stats = {'dot': 0, 'gap': 0, 'drop': 0}

    # --- 菱形點 ----------------------------------------------------------
    dots = []
    for s in S:
        if s.kind != 'dot':
            continue
        a = max(17.0, min(54.0, math.sqrt(s.area / (2 * DIA_B / DIA_A)) * 1.04))
        if rain:
            r = a * 0.80
            L = 2.25 * r
            dots.append(drop(s.cx, s.cy + (L + r) / 2 - r * 0.15, r, length=L, tipw=3))
        else:
            dots.append(diamond(s.cx, s.cy, a, a * DIA_B / DIA_A))
        stats['dot'] += 1
    solid = [s.path for s in thick] + [d.to_path() for d in dots]

    # --- 斷線 ------------------------------------------------------------
    # A thin bar is cut only where it ENDS at a thick stroke (a junction).
    # Where it runs straight through, it is left whole: cutting crossings
    # would split characters such as 重 down the middle.
    for s in S:
        if s.kind != 'thin':
            continue
        gap = max(8.0, min(GAP_CJK, s.w * 0.11))       # short bars get a finer slit
        touching = []
        for t in thick:
            if t.x1 < s.x0 - gap or t.x0 > s.x1 + gap or t.y1 < s.y0 - gap or t.y0 > s.y1 + gap:
                continue
            hit = pathops.op(s.path, t.path, PathOp.INTERSECTION, fix_winding=True)
            if abs(hit.area) < 30:
                continue
            hb = hit.bounds
            left, right = hb[0] - s.x0, s.x1 - hb[2]
            if left > CROSS and right > CROSS:
                continue                      # a crossing
            touching.append(t)
        # a short bar held at one end only is the entry flick of a stroke
        # (the top of 八): cutting it off would leave a stray dash
        if len(touching) == 1 and s.w < 230:
            touching = []
        p = s.path
        cut = bool(touching)
        for t in touching:
            p = pathops.op(p, _expand(t.path, gap), PathOp.DIFFERENCE, fix_winding=True)
        if cut:
            pieces = sorted(_pieces(p), key=lambda q: -abs(q.to_path().area))
            # the bar itself always stays; stubs left beyond a junction go
            keep = []
            for i, q in enumerate(pieces):
                qb = q.to_path().bounds
                if i == 0 or qb[2] - qb[0] >= NUB:
                    keep.append(q)
            if keep and abs(keep[0].to_path().area) >= 0.3 * s.area:
                stats['gap'] += 1
                out.extend(keep)
                continue
            # nearly the whole bar would vanish (it lies inside thick strokes): leave it alone
        out.append(s.shape)

    # --- 逆雨滴 on hooks ---------------------------------------------------
    drops = []
    dot_paths = [d.to_path() for d in dots]
    for t in (thick if not (rain and dots) else []):
        for (x, y, ang) in hook_tips(t):
            if not (72 <= ang <= 178):
                continue
            r = DROP_R
            L = 2.25 * r
            bx = x - math.cos(math.radians(ang)) * r * 0.55
            by = y - math.sin(math.radians(ang)) * r * 0.55
            d = drop(bx, by + L, r, length=L, tipw=3)
            # the drop must stand free: no other stroke may run through it
            dp = d.to_path()
            clash = 0.0
            for o in S:
                if o is t or o.kind == 'dot':
                    continue
                if o.x1 < x - 2 * r or o.x0 > x + 2 * r or o.y1 < y - r or o.y0 > y + L + r:
                    continue
                clash += abs(pathops.op(dp, o.path, PathOp.INTERSECTION, fix_winding=True).area)
            for q in dot_paths + [e.to_path() for e in drops]:
                clash += abs(pathops.op(dp, q, PathOp.INTERSECTION, fix_winding=True).area)
            if clash > 60:
                continue
            drops.append(d)
            stats['drop'] += 1

    parts = [s.shape for s in thick] + dots + out + drops
    if log is not None:
        log.append(stats)
    return parts, stats


# ---------------------------------------------------------------------------
# the character set and the batch build
# ---------------------------------------------------------------------------


def big5_level1():
    """The 5,401 frequently used characters of Big5 level 1 (0xA440-0xC67E)."""
    out = []
    for hi in range(0xA4, 0xC7):
        for lo in list(range(0x40, 0x7F)) + list(range(0xA1, 0xFF)):
            try:
                ch = bytes([hi, lo]).decode('big5')
            except UnicodeDecodeError:
                continue
            if 0x4E00 <= ord(ch) <= 0x9FFF:
                out.append(ord(ch))
    return out


# punctuation taken from the base as drawn
PUNCT_KEEP = [0x3001, 0x3002, 0x3008, 0x3009, 0x300A, 0x300B, 0x300C, 0x300D, 0x300E, 0x300F, 0x3010, 0x3011,
              0x3014, 0x3015, 0xFF08, 0xFF09, 0xFF0C, 0xFF5E, 0x3005, 0x3007]

_BASE = None


def _init(cache_dir):
    global _BASE
    _BASE = Base(cache_dir)


def _one(cp):
    from .compile import clean
    from .geom import union_all
    try:
        strokes, adv = _BASE.strokes(cp, WGHT)
        plain = union_all(strokes)
        if cp in PUNCT_KEEP:
            return cp, clean(plain).contours, adv, {'dot': 0, 'gap': 0, 'drop': 0}, 'kept'
        parts, stats = transform(strokes, cp)
        shape = union_all(parts)
        a0, a1 = abs(plain.to_path().area), abs(shape.to_path().area)
        b0, b1 = plain.bounds(), shape.bounds()
        # diamonds stand a little taller than the dots they replace, so allow for that
        ok = a0 > 0 and 0.80 <= a1 / a0 <= 1.30 and b1[1] >= b0[1] - 45 and b1[3] <= b0[3] + 90
        if not ok:
            return cp, clean(plain).contours, adv, stats, 'fallback'
        return cp, clean(shape).contours, adv, stats, 'ok'
    except Exception as e:                       # never let one glyph stop the build
        return cp, None, 1000, {'dot': 0, 'gap': 0, 'drop': 0}, f'error: {e}'


def build_set(cache_dir, log=None, limit=None):
    """{codepoint: (Shape, advance)} for the Chinese set, cached on disk."""
    import hashlib
    import multiprocessing as mp
    here = os.path.dirname(__file__)
    src = b''.join(open(os.path.join(here, n), 'rb').read() for n in ('cjk.py', 'parts.py', 'compile.py', 'geom.py'))
    key = hashlib.sha1(src + repr((WGHT, GAP_CJK, DROP_R, STEM, HAIR, limit)).encode()).hexdigest()[:12]
    cache = os.path.join(cache_dir, f'cjk-{key}.pkl')
    if os.path.exists(cache):
        with open(cache, 'rb') as f:
            data = pickle.load(f)
    else:
        base = Base(cache_dir)
        cps = [cp for cp in big5_level1() if cp in base.cov] + [cp for cp in PUNCT_KEEP if cp in base.cov]
        if limit:
            cps = cps[:limit]
        del base
        with mp.Pool(initializer=_init, initargs=(cache_dir,)) as pool:
            rows = pool.map(_one, cps, chunksize=40)
        data = {'glyphs': {}, 'status': {}, 'stats': {'dot': 0, 'gap': 0, 'drop': 0}}
        for cp, contours, adv, stats, status in rows:
            data['status'][cp] = status
            if contours is None:
                continue
            data['glyphs'][cp] = (contours, adv)
            for k in data['stats']:
                data['stats'][k] += stats[k]
        with open(cache, 'wb') as f:
            pickle.dump(data, f)
    if log is not None:
        st = list(data['status'].values())
        log.append(f"chinese: {len(data['glyphs'])} glyphs  (rules applied {st.count('ok')}, base kept {st.count('kept')}, "
                   f"fallback {st.count('fallback')}, errors {sum(1 for v in st if v.startswith('error'))})")
        log.append(f"chinese: {data['stats']['dot']} dots redrawn, {data['stats']['gap']} bars slit, {data['stats']['drop']} hooks given a drop")
    return {cp: (Shape(c), adv) for cp, (c, adv) in data['glyphs'].items()}, data['status']
