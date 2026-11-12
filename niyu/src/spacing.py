"""Kerning (workflow §7): side bearings are drawn into the glyphs; this module
measures every relevant pair on the finished outlines and writes class-based
kerning. Glyphs whose facing sides have the same profile share a class."""
import math

from .params import *  # noqa: F401,F403

STEP = 10
Y0, Y1 = -260, 800
NB = (Y1 - Y0) // STEP
BIG = 10_000


def _flatten(shape, n=10):
    segs = []
    for c in shape.contours:
        cur = c[0]
        pts = [cur]
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
        pts.append(c[0])
        segs.append(pts)
    return segs


def profile(shape, adv):
    """(left[], right[]) per horizontal band: distance from the origin to the
    leftmost ink, and from the rightmost ink to the advance. BIG where empty."""
    lo = [BIG] * NB
    hi = [-BIG] * NB
    for pts in _flatten(shape):
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            if ya > yb:
                xa, ya, xb, yb = xb, yb, xa, ya
            b0 = max(0, int(math.floor((ya - Y0) / STEP)))
            b1 = min(NB - 1, int(math.floor((yb - Y0) / STEP)))
            for b in range(b0, b1 + 1):
                yl, yh = Y0 + b * STEP, Y0 + (b + 1) * STEP
                # clip the segment to the band
                if yb == ya:
                    xs = (xa, xb)
                else:
                    ta = min(max((yl - ya) / (yb - ya), 0), 1)
                    tb = min(max((yh - ya) / (yb - ya), 0), 1)
                    xs = (xa + (xb - xa) * ta, xa + (xb - xa) * tb)
                lo[b] = min(lo[b], *xs)
                hi[b] = max(hi[b], *xs)
    left = [l if l < BIG else BIG for l in lo]
    right = [adv - h if h > -BIG else BIG for h in hi]
    return left, right


def _dilate(a, k=2):
    return [min(a[max(0, i - k):i + k + 1]) for i in range(len(a))]


def band(y):
    return int((y - Y0) // STEP)


class Kerner:
    def __init__(self, drawn):
        self.prof = {}
        for name, (shape, adv) in drawn.items():
            if shape.contours:
                l, r = profile(shape, adv)
                self.prof[name] = (_dilate(l), _dilate(r), l, r)

    def measure(self, a, b, zone, cap, w=0.3):
        """Optical distance between glyph a and glyph b (a on the left):
        the white between them, band by band, never counted deeper than
        `cap`, blended with their closest approach."""
        ra = self.prof[a][1]
        lb = self.prof[b][0]
        gaps = [ra[i] + lb[i] for i in range(NB)]
        m = min(gaps)
        z0, z1 = band(zone[0]), band(zone[1])
        vals = [min(g, cap) for g in gaps[z0:z1]]
        avg = sum(vals) / len(vals)
        return m, w * min(m, cap) + (1 - w) * avg

    def kern(self, a, b, zone, target, kmax, dead=14, gain=0.85, floor=28, hi=70):
        """Kern for the pair. Small deviations are sidebearing design, not
        kerning, so a dead zone swallows them; collisions are always fixed."""
        if a not in self.prof or b not in self.prof:
            return 0
        m, d = self.measure(a, b, zone, target + kmax)
        if m >= BIG:
            return 0
        k = target - d
        k = max(-kmax, k)
        if k < 0:
            k = -max(0.0, -k - dead) * gain
        else:
            k = 0
        k = max(k, floor - m)          # never let two glyphs come closer than `floor`
        k = min(hi, k)
        return int(round(k / 2.0)) * 2

    # ---- classes ---------------------------------------------------------
    def classes(self, names, side, tol=6, depth=240):
        """Partition glyphs by the shape of one side (0 = left, 1 = right).
        Ink deeper than `depth` behind the side cannot touch a neighbour, so
        it is ignored when comparing."""
        groups = []
        for n in names:
            if n not in self.prof:
                continue
            p = [min(v, depth) for v in self.prof[n][2 + side]]
            for g in groups:
                q = [min(v, depth) for v in self.prof[g[0]][2 + side]]
                if all(abs(x - y) <= tol for x, y in zip(p, q)):
                    g.append(n)
                    break
            else:
                groups.append([n])
        return groups
