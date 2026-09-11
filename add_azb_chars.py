#!/usr/bin/env python3
# Add South Azerbaijani (azb) letters to Vazir-Code:
#   ۆ U+06C6, ۇ U+06C7, ؤ U+0624, ؽ U+063D, ݣ U+0763
# including every contextual form (isolated / initial / medial / final)
# plus GSUB init / medi / fina rules so text shapes correctly.
#
# Usage:
#   fontforge -lang=py -script add_azb_chars.py [input.sfd] [output.ttf]
#
# Presentation forms (Unicode standard):
#   ۆ (U+06C6 OE):   isolated U+FBD9, final U+FBDA   (non-connecting)
#   ۇ (U+06C7 U):    isolated U+FBD7, final U+FBD8   (non-connecting)
#   ؤ (U+0624):      isolated U+FE85, final U+FE86   (non-connecting, pre-existing)
#   ؽ (U+063D):      unencoded init/medi/fina glyphs (no standard presentation forms)
#   ݣ (U+0763):      unencoded init/medi/fina glyphs (no standard presentation forms)
#
# Placeholder strategy (fine-tune the small marks afterwards):
#   ۆ ۇ  -> own base shapes (already in the font); final forms already exist
#   ؤ    -> already works via the و + hamza ligature
#   ؽ    -> base from Noto Naskh (like add_063D.py); contextual forms from ی
#   ݣ    -> base + contextual forms from ک
import fontforge, sys, re

SRC = sys.argv[1] if len(sys.argv) > 1 else "dist/Vazir-Code.sfd"
OUT = sys.argv[2] if len(sys.argv) > 2 else "dist/Vazir-Code.ttf"
DONOR = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"
MONO_WIDTH = 500

FINASUB = "'fina' Terminal Forms in Arabic lookup 0 subtable"
INITSUB = "'init' Initial Forms in Arabic lookup 2 subtable"
MEDISUB = "'medi' Medial Forms in Arabic lookup 1 subtable"

f = fontforge.open(SRC)
print(f"opened {SRC}: {len(list(f.glyphs()))} glyphs")


def exists(name):
    try:
        f[name]
        return True
    except TypeError:
        return False


def copy_outlines(dst_name, src_name):
    f.selection.none()
    f.selection.select(("more", None), src_name)
    f.copy()
    f.selection.none()
    f.selection.select(("more", None), dst_name)
    f.paste()
    f.selection.none()


def create_from(name, unicode, src_name, force=False):
    """create glyph `name` (mapped to `unicode`, or unencoded if None) as a copy of src outlines"""
    if exists(name):
        if force:
            f.removeGlyph(f[name])
        else:
            g = f[name]
            if unicode is not None:
                g.unicode = unicode
            g.width = MONO_WIDTH
            return g
    f.createChar(unicode if unicode is not None else -1, name)
    copy_outlines(name, src_name)
    print(f"created {name} U+{unicode:04X}" if unicode else f"created {name} (unencoded)")
    g = f[name]
    if unicode is not None:
        g.unicode = unicode
    g.width = MONO_WIDTH
    return g


def copy_anchors(dst_name, src_name):
    dst = f[dst_name]
    n = 0
    for ap in f[src_name].anchorPoints:
        try:
            if len(ap) >= 4:
                dst.addAnchorPoint(ap[0], ap[1], ap[2], ap[3])
                n += 1
        except Exception:
            pass
    if n:
        print(f"copied {n} anchors to {dst_name}")


# ---------- ۆ U+06C6 (non-connecting: only isolated + final forms) ----------
# base uni06C6 exists; final form uniFBDA (U+FBDA) already exists in the font
create_from("uniFBD9", 0xFBD9, "uni06C6", force=True)  # isolated presentation form
# remove glyphs wrongly created by earlier script versions (wrong codepoints)
for nm in ["uniFBDB", "uniFBDC", "uniFBDD", "uniFBDE"]:
    if exists(nm):
        f.removeGlyph(f[nm])
        print(f"removed wrong glyph {nm}")

# ---------- ۇ U+06C7 (non-connecting: only isolated + final forms) ----------
# base uni06C7 exists; final form uniFBD8 (U+FBD8) already exists
create_from("uniFBD7", 0xFBD7, "uni06C7", force=True)  # isolated presentation form
f["uniFBD8"].width = MONO_WIDTH
f["uniFBDA"].width = MONO_WIDTH

# ---------- ؽ U+063D: base from Noto Naskh; contextual forms from ی ----------
if not exists("uni063D"):
    f.createChar(0x063D, "uni063D")
    donor = fontforge.open(DONOR)
    donor.selection.select(("more", None), "uni063D")
    donor.copy()
    f.selection.none()
    f.selection.select(("more", None), "uni063D")
    f.paste()
    donor.close()
    print("copied base outlines from Noto Naskh uni063D")
    bbox = f["uni063D"].boundingBox()
    gw = bbox[2] - bbox[0]
    if gw > 0:
        sx = (MONO_WIDTH - 40) / gw
        cx_before = (bbox[0] + bbox[2]) / 2.0
        dx = MONO_WIDTH / 2.0 - cx_before * sx
        f["uni063D"].transform((sx, 0, 0, 1, dx, 0))
        print(f"scaled base X by {sx:.3f}")
g = f["uni063D"]
g.unicode = 0x063D
g.width = MONO_WIDTH
copy_anchors("uni063D", "uni06CC")
create_from("uni063D.init", None, "uniFBFE")
create_from("uni063D.medi", None, "uniFBFF")
create_from("uni063D.fina", None, "uniFBFD")

# ---------- ݣ U+0763: base + contextual forms from ک ----------
create_from("uni0763", 0x0763, "uni06A9")
copy_anchors("uni0763", "uni06A9")
create_from("uni0763.init", None, "uniFB90")
create_from("uni0763.medi", None, "uniFB91")
create_from("uni0763.fina", None, "uniFB8F")

# ---------- fix GDEF glyph classes ----------
# uni06C6 carries "mark" anchors, which makes FontForge classify it as a MARK
# (GDEF class 3) in the generated TTF. The Arabic init/medi/fina lookups carry
# the IgnoreMarks flag, so HarfBuzz skips ۆ during shaping. Force it to BASE.
for nm in ["uni06C6", "uni06C7", "uni063D", "uni0763",
           "uniFBD7", "uniFBD8", "uniFBD9", "uniFBDA"]:
    if exists(nm):
        try:
            f[nm].glyphclass = "baseglyph"
        except Exception as e:
            print(f"glyphclass set failed for {nm}: {e}")

# ---------- hinting for new glyphs ----------
new_glyphs = ["uniFBD9", "uniFBD7",
              "uni063D", "uni063D.init", "uni063D.medi", "uni063D.fina",
              "uni0763", "uni0763.init", "uni0763.medi", "uni0763.fina"]
f.selection.none()
for nm in new_glyphs:
    if exists(nm):
        f.selection.select(("more", None), nm)
f.autoHint()
f.selection.none()

f.save()
print("saved SFD (glyphs done; GSUB rules added next)")
f.close()

# ---------- (re)write GSUB rules into the SFD text ----------
# Non-connecting letters (ۆ ۇ) only ever get FINA in real shaping, so they
# only need a fina rule. ؽ and ݣ are connecting and need all three.
RULES = {
    "uni06C6": [(FINASUB, "uniFBDA")],
    "uni06C7": [(FINASUB, "uniFBD8")],
    "uni063D": [(FINASUB, "uni063D.fina"), (INITSUB, "uni063D.init"), (MEDISUB, "uni063D.medi")],
    "uni0763": [(FINASUB, "uni0763.fina"), (INITSUB, "uni0763.init"), (MEDISUB, "uni0763.medi")],
}

with open(SRC, encoding="utf-8") as fh:
    text = fh.read()

for gname, rls in RULES.items():
    m = re.search(r"(StartChar: %s\n)(.*?)(\nEndChar)" % re.escape(gname), text, re.S)
    if not m:
        print(f"WARN: glyph block {gname} not found in SFD")
        continue
    body = re.sub(r"[ \t]*Substitution2: [^\n]*\n?", "", m.group(2))
    to_add = [f'Substitution2: "{sub}" {tgt}' for sub, tgt in rls]
    insert = "\n" + "\n".join(to_add) + "\n"
    text = text[:m.start(2)] + body + insert + text[m.end(2):]
    print(f"rewrote {len(to_add)} GSUB rules for {gname}")

with open(SRC, "w", encoding="utf-8") as fh:
    fh.write(text)

# ---------- regenerate the TTF from the finished SFD ----------
f = fontforge.open(SRC)
f.generate(OUT)
print(f"generated {OUT}")
f.close()
