"""Glyph registry: name -> (draw function, unicode)."""

GLYPHS = {}


def glyph(name, uni=None):
    def deco(fn):
        GLYPHS[name] = (fn, uni)
        return fn

    return deco
