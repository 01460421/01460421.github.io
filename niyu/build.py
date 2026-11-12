#!/usr/bin/env python3
"""Build NiYu: draw every glyph, resolve overlaps, compile OTF / TTF / WOFF2."""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from src import lower, upper, figures, punct, swash, ligatures, ornaments, accents  # noqa: E402,F401  (registers glyphs)
from src.compile import build, clean, save_ufo, save_woff2  # noqa: E402
from src.geom import Shape, rect  # noqa: E402
from src.registry import GLYPHS  # noqa: E402


def main():
    t0 = time.time()
    out_dir = os.path.join(HERE, '..', 'fonts')
    os.makedirs(out_dir, exist_ok=True)
    drawn = {'.notdef': ((rect(60, 0, 440, 700) - rect(84, 24, 416, 676)), 500),
             'space': (Shape(), 250), 'uni00A0': (Shape(), 250)}
    cmap = {0x20: 'space', 0xA0: 'uni00A0'}
    for name, (fn, uni) in GLYPHS.items():
        g = fn()
        drawn[name] = (clean(g.shape()), g.adv)
        if uni is not None:
            for u in (uni if isinstance(uni, (list, tuple)) else [uni]):
                cmap[u] = name
    # case-sensitive forms: lifted copies for all-caps setting
    from src.features import CASE, build_fea
    for name in CASE:
        if name in drawn:
            dy = 128 if name in ('hyphen', 'endash', 'emdash', 'guilsinglleft', 'guilsinglright',
                                 'guillemotleft', 'guillemotright', 'periodcentered', 'bullet') else 64
            if name in ('exclamdown', 'questiondown'):
                dy = 118
            if name in ('colon', 'semicolon'):
                dy = 0
                continue
            drawn[name + '.case'] = (drawn[name][0].translate(0, dy), drawn[name][1])
    drawn['.notdef'] = (clean(drawn['.notdef'][0]), 500)
    log = []
    fea, kern_table = build_fea(drawn, log)
    with open(os.path.join(HERE, 'features.fea'), 'w') as f:
        f.write(fea)
    otf = os.path.join(out_dir, 'NiYu-Regular.otf')
    ttf = os.path.join(out_dir, 'NiYu-Regular.ttf')
    build(drawn, cmap, fea, otf, ttf)
    save_woff2(ttf, os.path.join(out_dir, 'NiYu-Regular.woff2'))
    if '--fast' not in sys.argv:
        save_ufo(drawn, cmap, fea, os.path.join(HERE, 'sources', 'NiYu-Regular.ufo'))
    for line in log:
        print(line)
    print(f'{len(drawn)} glyphs, {len(cmap)} code points in {time.time() - t0:.1f}s')
    return drawn, cmap, kern_table


if __name__ == '__main__':
    main()
