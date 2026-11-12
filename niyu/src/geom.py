"""Geometry core for NiYu: shapes, boolean ops, outline builder and a
variable-width stroke expander (nodes sit on extremes, handles stay H/V).

Everything is cubic. A Shape is a list of closed contours; a contour is
[(x, y), seg, seg, ...] where seg is ('L', p) or ('C', c1, c2, p).
"""
import math

import pathops
from pathops import Path, PathOp

# --------------------------------------------------------------------------
# small vector helpers
# --------------------------------------------------------------------------


def vadd(a, b):
    return (a[0] + b[0], a[1] + b[1])


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def vmul(a, k):
    return (a[0] * k, a[1] * k)


def vlen(a):
    return math.hypot(a[0], a[1])


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def vcross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def unit(deg):
    r = math.radians(deg)
    return (math.cos(r), math.sin(r))


def left_normal(t):
    return (-t[1], t[0])


def line_hit(p0, t0, p3, t3):
    """Parameters (a, b) with p0 + a*t0 == p3 - b*t3, or None if parallel."""
    den = vcross(t0, t3)
    if abs(den) < 1e-6:
        return None
    d = vsub(p3, p0)
    a = vcross(d, t3) / den
    b = vcross(t0, d) / den  # p0 + a t0 = p3 - b t3  ->  d = a t0 + b t3
    return a, b


# --------------------------------------------------------------------------
# Shape
# --------------------------------------------------------------------------


class Shape:
    def __init__(self, contours=None):
        self.contours = contours or []

    # --- construction -----------------------------------------------------
    def copy(self):
        return Shape([list(c) for c in self.contours])

    def __add__(self, other):  # plain concatenation (no boolean)
        return Shape(self.contours + other.contours)

    # --- transforms -------------------------------------------------------
    def transform(self, fn):
        out = []
        for c in self.contours:
            nc = [fn(c[0])]
            for seg in c[1:]:
                nc.append((seg[0],) + tuple(fn(p) for p in seg[1:]))
            out.append(nc)
        return Shape(out)

    def translate(self, dx, dy=0):
        return self.transform(lambda p: (p[0] + dx, p[1] + dy))

    def scale(self, sx, sy=None, cx=0, cy=0):
        sy = sx if sy is None else sy
        s = self.transform(lambda p: (cx + (p[0] - cx) * sx, cy + (p[1] - cy) * sy))
        if sx * sy < 0:
            s = s.reversed()
        return s

    def mirror_x(self, cx=0):
        return self.scale(-1, 1, cx, 0)

    def mirror_y(self, cy=0):
        return self.scale(1, -1, 0, cy)

    def rotate(self, deg, cx=0, cy=0):
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        return self.transform(
            lambda p: (cx + (p[0] - cx) * c - (p[1] - cy) * s, cy + (p[0] - cx) * s + (p[1] - cy) * c)
        )

    def skew(self, deg, cy=0):
        k = math.tan(math.radians(deg))
        return self.transform(lambda p: (p[0] + (p[1] - cy) * k, p[1]))

    def reversed(self):
        out = []
        for c in self.contours:
            pts = [c[0]]
            segs = c[1:]
            # walk backwards
            cur = [c[0]] + [s[-1] for s in segs]
            nc = [cur[-1]]
            for i in range(len(segs) - 1, -1, -1):
                s = segs[i]
                if s[0] == 'L':
                    nc.append(('L', cur[i]))
                else:
                    nc.append(('C', s[2], s[1], cur[i]))
            out.append(nc)
        return Shape(out)

    # --- pathops bridge ---------------------------------------------------
    def to_path(self):
        p = Path()
        for c in self.contours:
            p.moveTo(*c[0])
            for seg in c[1:]:
                if seg[0] == 'L':
                    p.lineTo(*seg[1])
                else:
                    p.cubicTo(*seg[1], *seg[2], *seg[3])
            p.close()
        return p

    @staticmethod
    def from_path(path):
        contours = []
        cur = None
        last = None
        for verb, pts in path.segments:
            if verb == 'moveTo':
                cur = [pts[0]]
                last = pts[0]
            elif verb == 'lineTo':
                cur.append(('L', pts[0]))
                last = pts[0]
            elif verb == 'curveTo':
                cur.append(('C', pts[0], pts[1], pts[2]))
                last = pts[2]
            elif verb == 'qCurveTo':
                # quadratic (possibly multi-point) -> cubic
                qpts = list(pts)
                on = []
                for i in range(len(qpts) - 1):
                    if i < len(qpts) - 2:
                        mid = ((qpts[i][0] + qpts[i + 1][0]) / 2, (qpts[i][1] + qpts[i + 1][1]) / 2)
                    else:
                        mid = qpts[-1]
                    on.append((qpts[i], mid))
                for q, e in on:
                    c1 = (last[0] + 2 / 3 * (q[0] - last[0]), last[1] + 2 / 3 * (q[1] - last[1]))
                    c2 = (e[0] + 2 / 3 * (q[0] - e[0]), e[1] + 2 / 3 * (q[1] - e[1]))
                    cur.append(('C', c1, c2, e))
                    last = e
            elif verb in ('closePath', 'endPath'):
                if cur and len(cur) > 1:
                    contours.append(cur)
                cur = None
        if cur and len(cur) > 1:
            contours.append(cur)
        return Shape(contours)

    def _op(self, other, which):
        res = pathops.op(self.to_path(), other.to_path(), which, fix_winding=True)
        return Shape.from_path(res)

    def union(self, other):
        return self._op(other, PathOp.UNION)

    def __or__(self, other):
        return self.union(other)

    def __sub__(self, other):
        return self._op(other, PathOp.DIFFERENCE)

    def __and__(self, other):
        return self._op(other, PathOp.INTERSECTION)

    def simplified(self):
        p = self.to_path()
        p.simplify(fix_winding=True)
        return Shape.from_path(p)

    # --- queries ----------------------------------------------------------
    def bounds(self):
        if not self.contours:
            return (0, 0, 0, 0)
        b = self.to_path().bounds
        return b

    def area(self):
        return self.to_path().area

    def draw(self, pen):
        for c in self.contours:
            pen.moveTo(c[0])
            for seg in c[1:]:
                if seg[0] == 'L':
                    pen.lineTo(seg[1])
                else:
                    pen.curveTo(seg[1], seg[2], seg[3])
            pen.closePath()


def union_all(shapes):
    """Union a list of shapes. Done pairwise on purpose: the batched
    OpBuilder shortcut punches holes where self-crossing contours overlap."""
    acc = None
    for s in shapes:
        if s is None or not s.contours:
            continue
        p = s.to_path()
        p.simplify(fix_winding=True)
        acc = p if acc is None else pathops.op(acc, p, PathOp.UNION, fix_winding=True)
    return Shape.from_path(acc) if acc is not None else Shape()


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------


def rect(x0, y0, x1, y1):
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    return Shape([[(x0, y0), ('L', (x1, y0)), ('L', (x1, y1)), ('L', (x0, y1))]])


def poly(pts):
    return Shape([[pts[0]] + [('L', p) for p in pts[1:]]])


def ellipse(cx, cy, rx, ry, t=0.5523):
    kx, ky = rx * t, ry * t
    return Shape([[
        (cx + rx, cy),
        ('C', (cx + rx, cy + ky), (cx + kx, cy + ry), (cx, cy + ry)),
        ('C', (cx - kx, cy + ry), (cx - rx, cy + ky), (cx - rx, cy)),
        ('C', (cx - rx, cy - ky), (cx - kx, cy - ry), (cx, cy - ry)),
        ('C', (cx + kx, cy - ry), (cx + rx, cy - ky), (cx + rx, cy)),
    ]])


class Outline:
    """Tiny outline builder. arc() draws a quarter-like curve whose handles
    lie along the horizontal / vertical tangents of its two end points."""

    def __init__(self, x, y):
        self.start = (x, y)
        self.cur = (x, y)
        self.segs = []

    def L(self, x, y):
        self.segs.append(('L', (x, y)))
        self.cur = (x, y)
        return self

    def H(self, x):
        return self.L(x, self.cur[1])

    def V(self, y):
        return self.L(self.cur[0], y)

    def rL(self, dx, dy):
        return self.L(self.cur[0] + dx, self.cur[1] + dy)

    def C(self, c1, c2, p):
        self.segs.append(('C', c1, c2, p))
        self.cur = p
        return self

    def arc(self, x, y, first='h', t=0.56, t2=None):
        """first='h': leave horizontally, arrive vertically (and vice versa)."""
        t2 = t if t2 is None else t2
        x0, y0 = self.cur
        if first == 'h':
            c1 = (x0 + (x - x0) * t, y0)
            c2 = (x, y + (y0 - y) * t2)
        else:
            c1 = (x0, y0 + (y - y0) * t)
            c2 = (x + (x0 - x) * t2, y)
        return self.C(c1, c2, (x, y))

    def bez(self, x, y, d0, d1, t=0.56, t2=None, l0=None, l1=None):
        """Curve to (x, y) leaving in direction d0 (deg) and arriving in
        direction d1 (deg). Handle lengths follow the tangent intersection
        (tension t) or explicit l0 / l1."""
        t2 = t if t2 is None else t2
        p0, p3 = self.cur, (x, y)
        T0, T3 = unit(d0), unit(d1)
        hit = line_hit(p0, T0, p3, T3)
        ch = vlen(vsub(p3, p0))
        if hit and hit[0] > 1e-6 and hit[1] > 1e-6:
            a, b = hit[0] * t, hit[1] * t2
        else:
            a, b = ch * 0.36, ch * 0.36
        if l0 is not None:
            a = l0
        if l1 is not None:
            b = l1
        return self.C(vadd(p0, vmul(T0, a)), vsub(p3, vmul(T3, b)), p3)

    def close(self):
        return Shape([[self.start] + self.segs])


# --------------------------------------------------------------------------
# stroke expander
# --------------------------------------------------------------------------


class N:
    """Skeleton node.

    x, y   position
    w      total width (split evenly) or wl / wr explicitly (left / right of travel)
    d      direction of travel in degrees (None -> automatic)
    ti, to tension of the incoming / outgoing handle
    li, lo explicit handle lengths (override tension)
    """

    def __init__(self, x, y, w=None, d=None, ti=None, to=None, li=None, lo=None, wl=None, wr=None):
        self.x, self.y = x, y
        self.wl = wl if wl is not None else (w or 0) / 2
        self.wr = wr if wr is not None else (w or 0) / 2
        self.d = d
        self.ti, self.to, self.li, self.lo = ti, to, li, lo

    @property
    def p(self):
        return (self.x, self.y)


def _auto_dirs(nodes, closed):
    n = len(nodes)
    for i, nd in enumerate(nodes):
        if nd.d is not None:
            continue
        if closed:
            a, b = nodes[(i - 1) % n], nodes[(i + 1) % n]
        else:
            a, b = nodes[max(i - 1, 0)], nodes[min(i + 1, n - 1)]
        nd.d = math.degrees(math.atan2(b.y - a.y, b.x - a.x))


def _handles(p0, T0, p3, T3, t0, t3, l0, l1):
    """Return (a, b, mode) handle lengths for the skeleton segment."""
    hit = line_hit(p0, T0, p3, T3)
    ch = vlen(vsub(p3, p0))
    if hit and hit[0] > 1e-6 and hit[1] > 1e-6 and hit[0] < 6 * ch and hit[1] < 6 * ch:
        a, b, mode = hit[0] * t0, hit[1] * t3, 'hit'
        base = hit
    else:
        a, b, mode = ch * 0.36 * (t0 / 0.56), ch * 0.36 * (t3 / 0.56), 'chord'
        base = (ch, ch)
    if l0 is not None:
        a = l0
    if l1 is not None:
        b = l1
    return a, b, mode, base


def _offset_seg(p0, T0, p3, T3, a, b, mode, base, q0, q3):
    """Offset copy of a skeleton segment between already-offset end points."""
    if mode == 'hit':
        hit = line_hit(q0, T0, q3, T3)
        if hit:
            fa = hit[0] / base[0]
            fb = hit[1] / base[1]
        else:
            fa = fb = 1.0
        fa = max(fa, 0.02)
        fb = max(fb, 0.02)
    else:
        ch = vlen(vsub(q3, q0))
        fa = fb = ch / base[0] if base[0] else 1.0
    return (vadd(q0, vmul(T0, a * fa)), vsub(q3, vmul(T3, b * fb)), q3)


def stroke(nodes, closed=False, start_cut=None, end_cut=None, tension=0.56):
    """Expand a skeleton into an outline.

    start_cut / end_cut: direction (deg) of the cut line at the open ends
    (default: perpendicular to travel).
    """
    nodes = list(nodes)
    _auto_dirs(nodes, closed)
    n = len(nodes)
    T = [unit(nd.d) for nd in nodes]
    Lp, Rp = [], []
    for i, nd in enumerate(nodes):
        Nn = left_normal(T[i])
        cut = None
        if not closed and i == 0 and start_cut is not None:
            cut = unit(start_cut)
        if not closed and i == n - 1 and end_cut is not None:
            cut = unit(end_cut)
        if cut is not None:
            k = vdot(cut, Nn)
            if abs(k) < 1e-6:
                raise ValueError('cut parallel to stroke')
            Lp.append(vadd(nd.p, vmul(cut, nd.wl / k)))
            Rp.append(vsub(nd.p, vmul(cut, nd.wr / k)))
        else:
            Lp.append(vadd(nd.p, vmul(Nn, nd.wl)))
            Rp.append(vsub(nd.p, vmul(Nn, nd.wr)))

    segsL, segsR = [], []
    count = n if closed else n - 1
    for i in range(count):
        j = (i + 1) % n
        A, B = nodes[i], nodes[j]
        t0 = A.to if A.to is not None else tension
        t3 = B.ti if B.ti is not None else tension
        a, b, mode, base = _handles(A.p, T[i], B.p, T[j], t0, t3, A.lo, B.li)
        segsL.append(_offset_seg(A.p, T[i], B.p, T[j], a, b, mode, base, Lp[i], Lp[j]))
        segsR.append(_offset_seg(A.p, T[i], B.p, T[j], a, b, mode, base, Rp[i], Rp[j]))

    def rev(segs, pts_start):
        # reverse a chain of cubic segments that starts at pts_start
        ends = [pts_start] + [s[2] for s in segs]
        out = []
        for i in range(len(segs) - 1, -1, -1):
            c1, c2, _ = segs[i]
            out.append(('C', c2, c1, ends[i]))
        return out

    if closed:
        outer = [Lp[0]] + [('C',) + s for s in segsL]
        inner_rev = rev(segsR, Rp[0])
        inner = [Rp[0]] + inner_rev
        return Shape([outer, inner])
    contour = [Lp[0]] + [('C',) + s for s in segsL]
    contour.append(('L', Rp[-1]))
    contour += rev(segsR, Rp[0])
    return Shape([contour])
