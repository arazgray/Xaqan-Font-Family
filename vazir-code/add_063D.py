#!/usr/bin/env python3
# Add U+063D (ؽ, FARSI YEH WITH INVERTED V) to Vazir-Code-AZB
# Usage:
#   fontforge -lang=py -script add_063D.py dist/Vazir-Code.sfd /tmp/Vazir-Code-AZB.ttf
# Then test: azb-test file should render without tofu.
import fontforge, sys

src = sys.argv[1] if len(sys.argv) > 1 else "dist/Vazir-Code.sfd"
out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/Vazir-Code-AZB.ttf"
DONOR = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"
TARGET_CP = 0x063D
TARGET_NAME = "uni063D"
MONO_WIDTH = 500

f = fontforge.open(src)
print(f"opened {src}: {len(list(f.glyphs()))} glyphs, fontname={f.fontname}")

# 1. if glyph already exists by name, just ensure unicode + width
try:
    existing = f[TARGET_NAME]
    print(f"{TARGET_NAME} already exists, unicode={existing.unicode}")
    existing.unicode = TARGET_CP
    existing.width = MONO_WIDTH
    f.generate(out)
    print(f"fixed width + regenerated -> {out}")
    sys.exit(0)
except TypeError:
    pass  # not found, continue to create

# 2. create new glyph
f.createChar(TARGET_CP, TARGET_NAME)
print(f"created {TARGET_NAME} U+{TARGET_CP:04X}")

# 3. copy outlines from donor (keeps correct ؽ shape)
donor = fontforge.open(DONOR)
donor.selection.select(("more", None), "uni063D")
donor.copy()
f.selection.select(("more", None), TARGET_NAME)
f.paste()
donor.close()
print("pasted outlines from Noto Naskh uni063D")

new = f[TARGET_NAME]
new.unicode = TARGET_CP
new.width = MONO_WIDTH

# 4. normalize horizontal scale to monospace width
# donor width is ~618, Vazir mono is 500. Scale outlines in X to fit with small side bearings.
# Compute bbox
bbox = new.boundingBox()
print(f"donor bbox: {bbox}")
if bbox[2] > bbox[0]:
    glyph_width = bbox[2] - bbox[0]
    target_draw = MONO_WIDTH - 40  # 20 units side bearing each side
    sx = target_draw / glyph_width if glyph_width > 0 else 1.0
    # center: move so bbox centered at MONO_WIDTH/2
    cx_before = (bbox[0] + bbox[2]) / 2.0
    cx_after = MONO_WIDTH / 2.0
    # transform: scale X then translate
    # x' = x*sx + dx  where dx = cx_after - cx_before*sx
    dx = cx_after - cx_before * sx
    new.transform((sx, 0, 0, 1, dx, 0))
    print(f"scaled X by {sx:.3f}, dx={dx:.1f}")
    new.width = MONO_WIDTH

# 5. copy anchors from Farsi Yeh so marks position correctly
try:
    yeh = f["uni06CC"]
    # fontforge anchors: list via .anchorPoints (tuple API varies by version, so use SFD fallback)
    # simplest: just ensure glyph has same anchor names via explicit add
    for ap_name, ap_type, x, y in [("Anchor-4", "basechar", 232, 347), ("Anchor-2", "basechar", 139, -231)]:
        try:
            new.addAnchorPoint(ap_name, ap_type, x, y)
        except Exception:
            pass
    print("added Yeh-like anchors")
except Exception as e:
    print(f"anchor copy skipped: {e}")

f.selection.select(("more", None), TARGET_NAME)
f.autoHint()
# f.autoInstr()  # uncomment if you want TT hinting

f.generate(out)
print(f"generated {out} with U+063D, width={f[TARGET_NAME].width}")
f.close()
