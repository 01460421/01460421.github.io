"""NiYu parameter table — the single source of truth (workflow §2).

All numbers are font units at UPM 1000. Every glyph is drawn against this
table; nothing is eyeballed per glyph.
"""
import math

UPM = 1000

# vertical metrics
CAP = 700          # cap height
XH = 470           # x-height
ASC = 740          # ascender
DESC = -230        # descender
FIG = 700          # lining figure height
SC = 500           # small-cap height

# weights
STEM = 86          # lowercase vertical stem
STEM_C = 94        # capital vertical stem
STEM_SC = 80       # small-cap stem
HAIR = 24          # lowercase hairline
HAIR_C = 26        # capital hairline
ROUND_EXTRA = 4    # rounds are this much heavier than straights

# overshoot
OS = 10            # lowercase
OS_C = 12          # capitals / figures

# the three signature features
GAP = 12           # 斷線: slit where a hairline meets a stem
CUT = 18.0         # shared shear angle of every cut stroke end (half a pentagram tip)
TAN_CUT = math.tan(math.radians(CUT))
DROP_BIG = 1.10 * STEM / 2    # 逆雨滴 radius, large
DROP_SMALL = 0.85 * STEM / 2  # 逆雨滴 radius, small
# 菱形點: the 72-degree rhombus (half apex = 2 x CUT)
DIA_A = 50                                    # half width
DIA_B = DIA_A / math.tan(math.radians(2 * CUT))  # half height (~68.8)

# serifs
SERIF_T = 24       # slab thickness (never below the 22-unit hairline floor)
SERIF_E = 46       # lowercase extension beyond the stem
SERIF_EC = 58      # capital extension
BRK_W = 30         # bracket width
BRK_H = 40         # bracket height

# spacing (side bearings)
SB_STRAIGHT = 80   # lowercase straight side, measured from the stem
SB_ROUND = 38      # lowercase round side
SBC_STRAIGHT = 98  # capital straight side, measured from the stem
SBC_ROUND = 54     # capital round side

# cut directions (all CUT degrees off an axis)
CUT_UP = -CUT          # for stroke ends that travel vertically (s, C, G, S, J terminals)
CUT_SIDE = 90 + CUT    # for stroke ends that travel sideways (c, e, t tails)
