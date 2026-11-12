"""OpenType features (workflow §8), generated from whatever glyphs exist."""
import string

from .params import *  # noqa: F401,F403
from .spacing import Kerner

FIGS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
CASE = ['hyphen', 'endash', 'emdash', 'parenleft', 'parenright', 'bracketleft', 'bracketright',
        'braceleft', 'braceright', 'guilsinglleft', 'guilsinglright', 'guillemotleft', 'guillemotright',
        'colon', 'semicolon', 'exclamdown', 'questiondown', 'periodcentered', 'bullet', 'slash', 'backslash', 'bar']


def _sub_block(tag, pairs, extra=''):
    if not pairs:
        return ''
    body = '\n'.join(f'    sub {a} by {b};' for a, b in pairs)
    return f'feature {tag} {{\n{extra}{body}\n}} {tag};\n\n'


def kerning(drawn, log=None):
    K = Kerner(drawn)
    have = set(K.prof)

    def fam(pred):
        return [n for n in drawn if n in have and pred(n)]

    def is_base(n):
        return '.' not in n and '_' not in n

    uc = fam(lambda n: is_base(n) and n[0].isupper() and n[0].isalpha() and len(n.rstrip(string.ascii_lowercase)) <= 1
             and not n.startswith('uni') and n not in ('I_',))
    lc = fam(lambda n: (is_base(n) and n[0].islower() and n not in PUNCT_NAMES and n not in FIGS and n not in MARK_NAMES
                        and not n.startswith('uni') and not n.startswith('u1')) or n in ('f_i', 'f_l', 'f_f'))
    sc = fam(lambda n: n.endswith('.sc'))
    fg = fam(lambda n: n in FIGS or (n.endswith('.onum') and n[:-5] in FIGS))
    pn = fam(lambda n: n in PUNCT_NAMES)
    sw = fam(lambda n: n.endswith('.ss01'))

    # --- targets come from the control strings (nn / HH / small-cap hh) ------
    zl, zc, zs = (0, XH), (0, CAP), (0, SC)
    KL, KC, KS = 92, 150, 100         # deepest raw kern allowed per alphabet
    t_l = K.measure('n', 'n', zl, 10_000)[1]
    t_c = K.measure('H', 'H', zc, 10_000)[1]
    t_s = K.measure('h.sc', 'h.sc', zs, 10_000)[1]
    if log is not None:
        log.append(f'kern targets: lc {t_l:.0f}  caps {t_c:.0f}  sc {t_s:.0f}')
        for a, b, z, t in (('o', 'o', zl, t_l), ('n', 'o', zl, t_l), ('o', 'n', zl, t_l),
                           ('O', 'O', zc, t_c), ('H', 'O', zc, t_c), ('O', 'H', zc, t_c),
                           ('o.sc', 'o.sc', zs, t_s), ('h.sc', 'o.sc', zs, t_s)):
            log.append(f'   control {a}{b}: {K.measure(a, b, z, 10_000)[1] - t:+.0f}')

    # (tag, left family, right family, zone, target, deepest kern, threshold)
    t_cl = (t_c + t_l) / 2
    plans = [
        ('lc_lc', lc, lc, zl, t_l, KL, 14),
        ('uc_uc', uc + sw, uc, zc, t_c, KC, 30),
        ('uc_lc', uc, lc, zl, t_cl - 4, KL + 12, 14),
        ('lc_pn', lc, pn, zl, t_l, KL, 20),
        ('pn_lc', pn, lc, zl, t_l, KL, 20),
        ('uc_pn', uc, pn, zc, t_c, KC, 34),
        ('pn_uc', pn, uc + sw, zc, t_c, KC, 34),
        ('sc_sc', sc, sc, zs, t_s, KS, 34),
        ('uc_sc', uc, sc, zs, (t_c + t_s) / 2, KS, 30),
        ('sc_pn', sc, pn, zs, t_s, KS, 34),
        ('pn_sc', pn, sc, zs, t_s, KS, 34),
        ('fg_fg', fg, fg, zc, t_c, 100, 34),
        ('fg_pn', fg, pn, zc, t_c, 110, 34),
        ('pn_fg', pn, fg, zc, t_c, 110, 34),
    ]
    out = ['feature kern {']
    cls_defs = []
    cid = 0
    total = 0
    table = {}
    for tag, left, right, zone, target, kmax, dead in plans:
        lcls = K.classes(left, 1)
        rcls = K.classes(right, 0)
        lines = []
        lnames, rnames = [], []
        for g in lcls:
            cid += 1
            lnames.append(f'@kL{cid}')
            cls_defs.append(f'@kL{cid} = [{" ".join(g)}];')
        for g in rcls:
            cid += 1
            rnames.append(f'@kR{cid}')
            cls_defs.append(f'@kR{cid} = [{" ".join(g)}];')
        for ln, lg in zip(lnames, lcls):
            for rn, rg in zip(rnames, rcls):
                k = K.kern(lg[0], rg[0], zone, target, kmax, dead=dead)
                if abs(k) >= 8:
                    lines.append(f'    pos {ln} {rn} {k};')
                    for a in lg:
                        for b in rg:
                            table[(a, b)] = k
        if lines:
            out.append(f'  lookup kern_{tag} {{')
            out += lines
            out.append(f'  }} kern_{tag};')
            total += len(lines)
    out.append('} kern;\n')
    if log is not None:
        log.append(f'kerning: {total} class pairs covering {len(table)} glyph pairs')
    return '\n'.join(cls_defs) + '\n\n' + '\n'.join(out), table


PUNCT_NAMES = {'period', 'comma', 'colon', 'semicolon', 'ellipsis', 'exclam', 'question', 'quotesingle', 'quotedbl',
               'quoteleft', 'quoteright', 'quotedblleft', 'quotedblright', 'quotesinglbase', 'quotedblbase',
               'hyphen', 'endash', 'emdash', 'parenleft', 'parenright', 'bracketleft', 'bracketright',
               'braceleft', 'braceright', 'slash', 'backslash', 'asterisk', 'guilsinglleft', 'guilsinglright',
               'guillemotleft', 'guillemotright', 'ampersand', 'at', 'exclamdown', 'questiondown'}
MARK_NAMES = {'grave', 'acute', 'circumflex', 'tilde', 'dieresis', 'ring', 'caron', 'macron', 'cedilla',
              'underscore', 'bar', 'plus', 'minus', 'equal', 'multiply', 'divide', 'less', 'greater',
              'asciicircum', 'asciitilde', 'numbersign', 'percent', 'dollar', 'degree', 'periodcentered', 'bullet',
              'sterling', 'dotlessi'}


def build_fea(drawn, log=None):
    names = set(drawn)
    fea = ['languagesystem DFLT dflt;', 'languagesystem latn dflt;', '']

    # small caps first: otherwise "WAFFLES" in small caps would pick up a lowercase ligature
    smcp = [(n[:-3], n) for n in sorted(names) if n.endswith('.sc') and n[:-3] in names]
    fea.append(_sub_block('smcp', smcp))
    c2sc = []
    for n in sorted(names):
        if n.endswith('.sc'):
            cap = n[:-3][0].upper() + n[:-3][1:]
            if cap in names and cap != n[:-3]:
                c2sc.append((cap, n))
    fea.append(_sub_block('c2sc', c2sc))

    ligs = [n for n in ('f_f', 'f_i', 'f_l') if n in names]
    fea.append(_sub_block('liga', [(' '.join(n.split('_')), n) for n in ligs]))

    fea.append(_sub_block('zero', [('zero', 'zero.zero')] if 'zero.zero' in names else []))
    fea.append(_sub_block('onum', [(f, f + '.onum') for f in FIGS if f + '.onum' in names]))
    fea.append(_sub_block('lnum', [(f + '.onum', f) for f in FIGS if f + '.onum' in names]))
    tn = [(f, f + '.tnum') for f in FIGS if f + '.tnum' in names]
    tn += [(f + '.onum', f + '.onum.tnum') for f in FIGS if f + '.onum.tnum' in names]
    fea.append(_sub_block('tnum', tn))
    fea.append(_sub_block('pnum', [(b, a) for a, b in tn]))

    fea.append(_sub_block('case', [(n, n + '.case') for n in CASE if n + '.case' in names]))

    # ss01 is contextual: a swash only appears where it has room.
    #  - A M N reach out to the left, so they only swash at the start of a word
    #  - K L Q R send a tail under what follows, so they stand down before a descender
    #  - Y y send a tail under what precedes, so they stand down after a descender
    import string as _s
    from .accents import COMPOSE
    letters = [c for c in _s.ascii_letters if c in names] + [n for n, *_ in COMPOSE if n in names]
    letters += [n for n in sorted(names) if n.endswith('.sc') or n.endswith('.ss01')] + ['f_f', 'f_i', 'f_l', 'dotlessi']
    desc = [n for n in ('g', 'j', 'p', 'q', 'y', 'Q', 'J', 'comma', 'semicolon', 'quotesinglbase', 'quotedblbase',
                        'ccedilla', 'Ccedilla', 'yacute', 'ydieresis', 'parenleft', 'parenright', 'bracketleft',
                        'bracketright', 'braceleft', 'braceright', 'slash', 'backslash', 'bar', 'underscore',
                        'three.onum', 'four.onum', 'five.onum', 'seven.onum', 'nine.onum', 'q.sc', 'j.sc',
                        'Y.ss01', 'y.ss01') if n in names]
    everything = [n for n in drawn if n != '.notdef']

    def swash_lookup(tag, glyphs, ignores):
        have = [g for g in glyphs if g + '.ss01' in names]
        if not have:
            return ''
        rows = [f'        ignore sub {r};' for r in ignores(' '.join(have))]
        rows += [f"        sub {g}' by {g}.ss01;" for g in have]
        return f'    lookup ss01_{tag} {{\n' + '\n'.join(rows) + f'\n    }} ss01_{tag};\n'

    tails = [n for n in ('K.ss01', 'L.ss01', 'Q.ss01', 'R.ss01') if n in names]
    fea.append(f'@sw_letter = [{" ".join(letters)}];\n@sw_desc = [{" ".join(desc)}];\n'
               f'@sw_low = [{" ".join(desc + tails)}];\n@sw_any = [{" ".join(everything)}];\n')
    fea.append(
        'feature ss01 {\n'
        '    featureNames {\n        name "Swash capitals and long tails";\n'
        '        name 3 1 0x0404 "\\82b1\\98fe\\5927\\5beb\\8207\\9577\\5c3e";\n    };\n'
        + swash_lookup('left', ['A', 'M', 'N'], lambda g: [f"@sw_letter [{g}]'"])
        + swash_lookup('right', ['K', 'L', 'Q', 'R'], lambda g: [
            f"[{g}]' @sw_desc", f"[{g}]' @sw_any @sw_desc", f"[{g}]' @sw_any @sw_any @sw_desc"])
        # tails that already swashed to the right count as descenders for what follows
        + swash_lookup('under', ['Y', 'y'], lambda g: [
            f"@sw_low [{g}]'", f"@sw_low @sw_any [{g}]'", f"@sw_low @sw_any @sw_any [{g}]'"])
        + '} ss01;\n')

    kern_fea, table = kerning(drawn, log)
    fea.append(kern_fea)

    # GDEF: glyph classes and a caret between the two letters of each ligature
    carets = '\n'.join(f'    LigatureCaretByPos {n} {int(drawn[n][1] * 0.47)};' for n in ligs)
    bases = ' '.join(n for n in drawn if n not in ligs and n != '.notdef')
    fea.append(f'@GDEF_base = [{bases}];\n@GDEF_lig = [{" ".join(ligs)}];\n'
               f'table GDEF {{\n    GlyphClassDef @GDEF_base, @GDEF_lig, , ;\n{carets}\n}} GDEF;\n')
    return '\n'.join(fea), table
