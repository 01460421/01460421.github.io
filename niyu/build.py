#!/usr/bin/env python3
"""Build NiYu: draw every glyph, resolve overlaps, compile OTF / TTF / WOFF2."""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from src import lower, upper, figures, punct, swash, ligatures, ornaments, accents  # noqa: E402,F401  (registers glyphs)
from src import cjk  # noqa: E402
from src.compile import build, clean, save_latin_subset, save_ufo, save_woff2  # noqa: E402
from src.geom import Shape, rect, union_all  # noqa: E402
from src.registry import GLYPHS  # noqa: E402


ZIP_NAME = 'NiYu-fonts.zip'
ZIP_NOTE = """逆雨 NiYu  —  觀賞型襯線字型（拉丁字母＋中文）
====================================================

安裝
  Windows：對 NiYu-Regular.ttf 按右鍵 →「安裝」
  macOS：  點兩下 NiYu-Regular.otf →「安裝字體」
  Linux：  複製到 ~/.fonts/ 後執行 fc-cache

兩個檔案內容相同，裝其中一個即可。字型選單裡的名稱是 NiYu（繁體中文系統顯示為「逆雨」）。

使用
  建議字級 18 pt 以上。花飾預設開啟；若軟體支援 OpenType，
  可關閉「上下文替代字（calt）」讓版面安靜一點。
  其他功能：小型大寫、舊式數字、等寬數字、連字。

授權
  SIL Open Font License 1.1，可免費用於個人與商業用途、可改作，
  詳見 OFL.txt。中文字以 Noto Serif TC 為底改作。

樣張與原始碼
  https://01460421.github.io/niyu/
  https://github.com/01460421/01460421.github.io
"""


def package(out_dir):
    """One-click download: the two desktop fonts, the licence and a short note."""
    import zipfile
    path = os.path.join(out_dir, ZIP_NAME)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in ('NiYu-Regular.otf', 'NiYu-Regular.ttf', 'OFL.txt'):
            info = zipfile.ZipInfo('NiYu/' + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(os.path.join(out_dir, name), 'rb') as f:
                z.writestr(info, f.read())
        info = zipfile.ZipInfo('NiYu/說明.txt', date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, ZIP_NOTE.encode('utf-8'))
    return path


def main():
    t0 = time.time()
    out_dir = os.path.join(HERE, '..', 'fonts')
    os.makedirs(out_dir, exist_ok=True)
    if '--zip-only' in sys.argv:
        print(package(out_dir))
        return
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

    # ---- Chinese (workflow §11): Big5 level 1, derived from Noto Serif TC ----
    han_names = set()
    if '--no-cjk' not in sys.argv:
        from src.parts import diamond
        from src.punct import comma_shape
        han, status = cjk.build_set(os.path.join(HERE, '.cache'), log)
        for cp, (shape, adv) in sorted(han.items()):
            name = f'uni{cp:04X}'
            drawn[name] = (shape, adv)
            cmap[cp] = name
            han_names.add(name)

        def full(name, cp, shapes):
            drawn[name] = (clean(union_all(shapes)), 1000)
            cmap[cp] = name
            han_names.add(name)

        def centred(src, dy):
            shape, adv = drawn[src]
            return shape.translate(500 - adv / 2, dy)

        # full-width punctuation redrawn with the diamond, centred in the em
        full('uniFF01', 0xFF01, [centred('exclam', 30)])
        full('uniFF1F', 0xFF1F, [centred('question', 30)])
        full('uniFF1A', 0xFF1A, [diamond(500, 250), diamond(500, 520)])
        full('uniFF1B', 0xFF1B, [diamond(500, 520), comma_shape(500 - 46, 330)])
        full('uni2027', 0x2027, [diamond(500, 380)])
        full('uni30FB', 0x30FB, [diamond(500, 380)])
        drawn['uni3000'] = (Shape(), 1000)
        cmap[0x3000] = 'uni3000'
        han_names.add('uni3000')

    fea, kern_table = build_fea(drawn, log, skip=han_names)
    with open(os.path.join(HERE, 'features.fea'), 'w') as f:
        f.write(fea)
    otf = os.path.join(out_dir, 'NiYu-Regular.otf')
    ttf = os.path.join(out_dir, 'NiYu-Regular.ttf')
    build(drawn, cmap, fea, otf, ttf, has_cjk=bool(han_names))
    save_woff2(ttf, os.path.join(out_dir, 'NiYu-Regular.woff2'))
    save_latin_subset(ttf, os.path.join(out_dir, 'NiYu-Regular-Latin.woff2'), han_names)
    if '--fast' not in sys.argv:
        latin = {n: v for n, v in drawn.items() if n not in han_names}
        save_ufo(latin, {cp: n for cp, n in cmap.items() if n not in han_names}, fea,
                 os.path.join(HERE, 'sources', 'NiYu-Regular.ufo'))
    package(out_dir)
    for line in log:
        print(line)
    print(f'{len(drawn)} glyphs, {len(cmap)} code points in {time.time() - t0:.1f}s')
    return drawn, cmap, kern_table


if __name__ == '__main__':
    main()
