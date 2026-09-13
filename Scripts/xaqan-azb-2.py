#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add South Azerbaijani (azb) letters to any Arabic-script font.

Letters
    ۆ U+06C6  = و + U+065A (small v above)     forms: U+FBD9 / U+FBDA
    ۇ U+06C7  = و + U+064F (damma)             forms: U+FBD7 / U+FBD8
    ؤ U+0624  = left as-is (already in Persian fonts)
    ؽ U+063D  = ی + U+0302 (fallback U+065B)   unencoded .init/.medi/.fina
    ݣ U+0763  = ک + three dots of ش            unencoded .init/.medi/.fina
    ڭ U+06AD  = ك (U+FED9 / U+0643) + dots of ش
                                              forms: U+FBD3 / U+FBD4 / U+FBD5 / U+FBD6
    وْ         = و + ْ (U+0652 / U+FE7E); GPOS
                  lowers the sukun only on و / و.fina

Anchors are stripped from the vowel letters ۆ ۇ ؤ ؽ (and their forms)
because they do not take further marks.

Font Info names get the prefix "Xaqan".

Usage:
  fontforge -lang=py -script xaqan-azb.py <input> [output] [donor]

  input : any font FontForge can open (.sfd, .ttf, .otf, ...)
  output: default = <input base>-xaqan-azb.<ext>  (.ttf when input is .sfd)
  donor : optional font used only to supply a missing base / mark glyph
"""
import fontforge
import psMat
import sys
import os
import re
import tempfile

# ---------------- arguments ----------------
src = sys.argv[1] if len(sys.argv) > 1 else "dist/Vazir-Code.sfd"
in_ext = os.path.splitext(src)[1].lower()
if len(sys.argv) > 2:
    out = sys.argv[2]
else:
    out_ext = ".ttf" if in_ext == ".sfd" else (in_ext or ".ttf")
    out = os.path.splitext(src)[0] + "-xaqan-azb" + out_ext
donor_path = sys.argv[3] if len(sys.argv) > 3 else None

NAME_PREFIX = "Xaqan"
# Extra lowering of sukun sitting on و, as a fraction of UPM (em).
# Applied on top of a snap-to-just-above-bowl calculation.
SUKUN_ON_WAW_EXTRA_EM = 0.02
SUKUN_ON_WAW_GAP_EM = 0.03
MARK_GAP_EM = 0.04
DOTS_GAP_EM = 0.05

# ---------------- sources ----------------
WAW = ((0x0648,), ("uni0648", "waw", "afii57441", "uni0648.fina"))
WAW_FINA = ((0xFEEE,), ("uniFEEE", "uni0648.fina", "waw.fina"))
KAF_AR = ((0x0643, 0xFED9),
          ("uni0643", "uniFED9", "kaf", "afii57440"))
KAF_AR_FORMS = {
    "init": ((0xFEDB,), ("uniFEDB", "uni0643.init", "kaf.init")),
    "medi": ((0xFEDC,), ("uniFEDC", "uni0643.medi", "kaf.medi")),
    "fina": ((0xFEDA,), ("uniFEDA", "uni0643.fina", "kaf.fina")),
}
KEHEH = ((0x06A9, 0x0643), ("uni06A9", "uni0643", "keheh", "kaf", "afii57440"))
KEHEH_FORMS = {
    "init": ((0xFB90,), ("uniFB90", "uni06A9.init", "keheh.init")),
    "medi": ((0xFB91,), ("uniFB91", "uni06A9.medi", "keheh.medi")),
    "fina": ((0xFB8F,), ("uniFB8F", "uni06A9.fina", "keheh.fina")),
}
YEH = ((0x06CC, 0x064A), ("uni06CC", "uni064A", "farsiyeh", "yeh", "afii57534"))
YEH_FORMS = {
    "init": ((0xFBFE,), ("uniFBFE", "uni06CC.init", "farsiyeh.init", "yeh.init")),
    "medi": ((0xFBFF,), ("uniFBFF", "uni06CC.medi", "farsiyeh.medi", "yeh.medi")),
    "fina": ((0xFBFD,), ("uniFBFD", "uni06CC.fina", "farsiyeh.fina", "yeh.fina")),
}
SHEEN = ((0x0634,), ("uni0634", "sheen", "afii57427"))
SEEN = ((0x0633,), ("uni0633", "seen", "afii57426"))
THREE_DOTS_SYM = ((0xFBB6, 0x06DB), ("uniFBB6", "uni06DB"))
SUKUN = ((0x0652, 0xFE7E, 0xFE7F),
         ("uni0652", "uniFE7E", "uniFE7F", "sukun", "afii57452"))
SMALL_V = ((0x065A,), ("uni065A",))
DAMMA = ((0x064F, 0xFE78), ("uni064F", "uniFE78", "damma", "afii57441damma"))
CIRCUMFLEX = ((0x0302, 0x065B), ("uni0302", "circumflex", "uni065B"))

# letter specs
# skip_create: do not invent / redraw the glyph (ؤ)
# strip_anchors: vowels — no mark anchors
# connecting: dual-joining, needs .init/.medi/.fina
# mark_src: combining mark overlaid on base
# dots: overlay three dots taken from ش
# base_role: which source letter to copy
LETTERS = [
    dict(cp=0x06C6, name="uni06C6", base_role="waw",
         mark_role="small_v",
         forms=((0xFBD9, "uniFBD9"), (0xFBDA, "uniFBDA")),
         strip_anchors=True),
    dict(cp=0x06C7, name="uni06C7", base_role="waw",
         mark_role="damma",
         forms=((0xFBD7, "uniFBD7"), (0xFBD8, "uniFBD8")),
         strip_anchors=True),
    dict(cp=0x0624, name="uni0624", base_role="waw",
         skip_create=True,
         forms=((0xFE85, "uniFE85"), (0xFE86, "uniFE86")),
         strip_anchors=True),
    dict(cp=0x063D, name="uni063D", base_role="yeh",
         mark_role="circumflex", connecting=True,
         forms_src="yeh", strip_anchors=True),
    dict(cp=0x0763, name="uni0763", base_role="keheh",
         dots=True, connecting=True, forms_src="keheh"),
    dict(cp=0x06AD, name="uni06AD", base_role="kaf_ar",
         dots=True, connecting=True, forms_src="kaf_ar",
         forms=((0xFBD3, "uniFBD3"), (0xFBD4, "uniFBD4"),
                (0xFBD5, "uniFBD5"), (0xFBD6, "uniFBD6"))),
]


# ---------------- helpers ----------------
def exists(f, name):
    if not name:
        return False
    try:
        f[name]
        return True
    except (TypeError, KeyError):
        return False


def glyph_by_cp(f, cp):
    try:
        return f[cp].glyphname
    except (TypeError, ValueError, KeyError):
        return None


def find_glyph(f, cps=(), names=()):
    for cp in cps:
        n = glyph_by_cp(f, cp)
        if n:
            return n
    for nm in names:
        if exists(f, nm):
            return nm
    return None


def find_in(fonts, cps=(), names=()):
    """Return (font, glyphname) from the first font that has the glyph."""
    for f in fonts:
        if f is None:
            continue
        n = find_glyph(f, cps, names)
        if n:
            return f, n
    return None, None


def copy_outlines(f, dst, src):
    f.selection.none()
    f.selection.select(("more", None), src)
    f.copy()
    f.selection.none()
    f.selection.select(("more", None), dst)
    f.paste()
    f.selection.none()


def ensure_char(f, cp, name):
    if cp and cp > 0:
        existing = glyph_by_cp(f, cp)
        if existing:
            return existing
    if exists(f, name):
        if cp and cp > 0:
            f[name].unicode = cp
        return name
    f.createChar(cp if (cp and cp > 0) else -1, name)
    return name


def copy_from_local_or_donor(f, donor, dst, local_src, donor_cp=None, donor_name=None):
    if local_src and exists(f, local_src):
        copy_outlines(f, dst, local_src)
        f[dst].width = f[local_src].width
        return "local"
    if donor is not None:
        src = None
        if donor_cp:
            src = glyph_by_cp(donor, donor_cp)
        if not src and donor_name and exists(donor, donor_name):
            src = donor_name
        if src:
            donor.selection.none()
            donor.selection.select(("more", None), src)
            donor.copy()
            f.selection.none()
            f.selection.select(("more", None), dst)
            f.paste()
            f.selection.none()
            try:
                f[dst].width = donor[src].width
            except Exception:
                pass
            return "donor"
    return None


def bbox(g):
    try:
        return g.boundingBox()
    except Exception:
        return (0, 0, 0, 0)


def center_x(g):
    xmin, _, xmax, _ = bbox(g)
    return (xmin + xmax) / 2.0


def contour_cy(contour):
    ys = [p.y for p in contour]
    return sum(ys) / float(len(ys)) if ys else 0.0


def append_translated(f, dst_name, src_font, src_name, dx, dy):
    """Append src outlines to dst, translated by (dx, dy)."""
    tmp = "_AZB.tmp.overlay"
    if exists(f, tmp):
        f.removeGlyph(tmp)
    f.createChar(-1, tmp)
    if src_font is f:
        copy_outlines(f, tmp, src_name)
        f[tmp].width = f[src_name].width
    else:
        src_font.selection.none()
        src_font.selection.select(("more", None), src_name)
        src_font.copy()
        f.selection.none()
        f.selection.select(("more", None), tmp)
        f.paste()
        f.selection.none()
    f[tmp].transform(psMat.translate(dx, dy))
    dst = f[dst_name]
    layer = dst.foreground
    layer += f[tmp].foreground
    dst.foreground = layer
    f.removeGlyph(tmp)


def overlay_mark(f, donor, dst_name, mark_fonts_and_names, gap_em=MARK_GAP_EM):
    """Center a combining mark on dest and sit it just above dest's bowl."""
    src_f, mark = None, None
    for sf, namespec in mark_fonts_and_names:
        if sf is None:
            continue
        n = find_glyph(sf, *namespec) if isinstance(namespec, tuple) else (
            namespec if exists(sf, namespec) else None
        )
        if n:
            src_f, mark = sf, n
            break
    if not mark:
        return False
    dst = f[dst_name]
    db = bbox(dst)
    mb = bbox(src_f[mark])
    em = float(f.em or 1000)
    dx = center_x(dst) - (mb[0] + mb[2]) / 2.0
    gap = em * gap_em
    # Combining marks already live above the baseline. Snap so mark.ymin
    # sits a small gap above dest.ymax. If that would raise the mark a lot,
    # keep the mark's native y and only re-center horizontally.
    native_dy = 0.0
    snapped_dy = (db[3] + gap) - mb[1]
    if snapped_dy < em * 0.25:
        native_dy = snapped_dy
    append_translated(f, dst_name, src_f, mark, dx, native_dy)
    return True


def extract_sheen_dots(f, donor):
    """
    Build an unencoded glyph AZB.threedots from:
      1. U+FBB6 / U+06DB if present
      2. contours of ش that sit above س
      3. references inside ش that are not س
    Returns glyph name or None.
    """
    name = "AZB.threedots"
    fonts = (f, donor)
    sym_f, sym = find_in(fonts, *THREE_DOTS_SYM)
    if sym:
        ensure_char(f, -1, name)
        copy_from_local_or_donor(f, donor, name,
                                 sym if sym_f is f else None,
                                 donor_name=sym)
        f[name].width = 0
        print("  three-dots source: symbol %s" % sym)
        return name

    sheen_f, sheen = find_in(fonts, *SHEEN)
    if not sheen:
        print("  ! no ش — cannot extract three dots")
        return None

    # Bring sheen into a working glyph in f
    work = "_AZB.tmp.sheen"
    ensure_char(f, -1, work)
    copy_from_local_or_donor(f, donor, work,
                             sheen if sheen_f is f else None,
                             donor_name=sheen)

    seen_f, seen = find_in(fonts, *SEEN)
    thresh = None
    if seen:
        seen_box = bbox(seen_f[seen])
        thresh = seen_box[3] - max(20.0, (f.em or 1000) * 0.02)

    # Prefer referenced pieces (component dots)
    refs = []
    try:
        refs = list(f[work].references)
    except Exception:
        refs = []
    if refs and seen:
        seen_names = set()
        if seen:
            seen_names.add(seen)
        extra = []
        for ref in refs:
            rname = ref[0]
            if rname in seen_names:
                continue
            extra.append(ref)
        if extra:
            ensure_char(f, -1, name)
            f[name].clear()
            f[name].width = 0
            layer = f[name].foreground
            # unlink selected refs into dest via overlay of those glyphs
            for ref in extra:
                rname, matrix = ref[0], ref[1]
                tmp = "_AZB.tmp.ref"
                ensure_char(f, -1, tmp)
                if exists(f, rname):
                    copy_outlines(f, tmp, rname)
                elif donor is not None and exists(donor, rname):
                    copy_from_local_or_donor(f, donor, tmp, None, donor_name=rname)
                else:
                    continue
                f[tmp].transform(matrix)
                layer += f[tmp].foreground
                f.removeGlyph(tmp)
            f[name].foreground = layer
            if exists(f, work):
                f.removeGlyph(work)
            if any(True for _ in f[name].foreground):
                print("  three-dots source: references inside ش")
                return name

    # Contour filter: keep pieces whose centroid is above س
    layer = fontforge.layer()
    src_layer = f[work].foreground
    if thresh is None:
        xmin, ymin, xmax, ymax = bbox(f[work])
        thresh = ymin + 0.52 * (ymax - ymin)
    for c in src_layer:
        try:
            if contour_cy(c) > thresh:
                layer += c
        except Exception:
            continue
    if exists(f, work):
        f.removeGlyph(work)
    if not any(True for _ in layer):
        print("  ! could not isolate dots of ش")
        return None
    ensure_char(f, -1, name)
    f[name].clear()
    f[name].foreground = layer
    f[name].width = 0
    print("  three-dots source: upper contours of ش")
    return name


def overlay_dots(f, dst_name, dots_name, gap_em=DOTS_GAP_EM):
    if not dots_name or not exists(f, dots_name):
        return False
    dst = f[dst_name]
    dots = f[dots_name]
    db = bbox(dst)
    mb = bbox(dots)
    if mb[2] - mb[0] <= 0:
        return False
    em = float(f.em or 1000)
    dx = center_x(dst) - (mb[0] + mb[2]) / 2.0
    gap = em * gap_em
    dy = (db[3] + gap) - mb[1]
    append_translated(f, dst_name, f, dots_name, dx, dy)
    return True


def find_arabic_lookup(f, feature, table="gsub"):
    lookups = f.gsub_lookups if table == "gsub" else f.gpos_lookups
    for lk in lookups:
        try:
            info = f.getLookupInfo(lk)
        except Exception:
            continue
        feats = info[2] if len(info) > 2 else ()
        for ftag, _scripts in feats:
            if ftag == feature:
                subs = f.getLookupSubtables(lk)
                if subs:
                    return lk, subs[0]
    return None, None


def ensure_gsub_feature(f, feat):
    lk, st = find_arabic_lookup(f, feat, "gsub")
    if st:
        return st
    lk_name = "'%s' Terminal Forms (AZB)" % feat
    f.addLookup(lk_name, "gsub_single", None,
                ((feat, (("arab", ("dflt",)),)),))
    st = lk_name + " subtable"
    f.addLookupSubtable(lk_name, st)
    print("  created GSUB lookup: %s" % lk_name)
    return st


def clear_anchors(f, name):
    if not exists(f, name):
        return
    try:
        f[name].anchorPoints = ()
    except Exception:
        try:
            f[name].anchorPoints = []
        except Exception:
            pass


def prefix_human(val):
    val = (val or "").strip()
    if not val:
        return NAME_PREFIX
    if val.startswith(NAME_PREFIX):
        return val
    return NAME_PREFIX + " " + val


def prefix_ps(val):
    val = (val or "").strip().replace(" ", "")
    if not val:
        return NAME_PREFIX
    if val.lower().startswith(NAME_PREFIX.lower()):
        return val
    return NAME_PREFIX + "-" + val


def apply_xaqan_names(f):
    f.fontname = prefix_ps(getattr(f, "fontname", "") or "")
    f.familyname = prefix_human(getattr(f, "familyname", "") or "")
    f.fullname = prefix_human(getattr(f, "fullname", "") or "")
    try:
        if getattr(f, "fondname", None):
            f.fondname = prefix_human(f.fondname)
    except Exception:
        pass
    skip_ids = {
        "SubFamily", "Preferred Styles", "WWS Subfamily",
        "Version", "Copyright", "License", "License URL",
        "Vendor URL", "Designer URL", "Sample Text",
    }
    ps_ids = {"PostScriptName"}
    try:
        names = list(f.sfnt_names)
    except Exception:
        names = []
    new_names = []
    for entry in names:
        try:
            lang, nid, val = entry
        except Exception:
            new_names.append(entry)
            continue
        if nid in skip_ids or not val:
            new_names.append(entry)
            continue
        if nid in ps_ids:
            new_names.append((lang, nid, prefix_ps(val)))
        else:
            new_names.append((lang, nid, prefix_human(val)))
    if new_names:
        try:
            f.sfnt_names = tuple(new_names)
        except Exception:
            try:
                f.sfnt_names = new_names
            except Exception:
                print("  ! could not write sfnt name table")
    print("  fontname=%s" % f.fontname)
    print("  familyname=%s" % f.familyname)
    print("  fullname=%s" % f.fullname)


def add_sukun_lowering(f):
    """GPOS pair: when ْ / ﹾ sits on و (or و final), drop it closer to the bowl."""
    waw_names = []
    for spec in (WAW, WAW_FINA):
        n = find_glyph(f, *spec)
        if n and n not in waw_names:
            waw_names.append(n)
    # unencoded contextual copies of و
    for extra in ("uni0648.fina", "waw.fina"):
        if exists(f, extra) and extra not in waw_names:
            waw_names.append(extra)

    sukun_names = []
    for cp in (0x0652, 0xFE7E, 0xFE7F):
        n = glyph_by_cp(f, cp)
        if n and n not in sukun_names:
            sukun_names.append(n)
    for extra in ("uni0652", "uniFE7E", "uniFE7F", "sukun"):
        if exists(f, extra) and extra not in sukun_names:
            sukun_names.append(extra)

    if not waw_names or not sukun_names:
        print("  ! skip وْ GPOS (missing و or ْ)")
        return

    lk_name = "'mark' Sukun on Waw (AZB)"
    st_name = lk_name + " subtable"
    existing = False
    for lk in f.gpos_lookups:
        if lk == lk_name:
            existing = True
            break
    if not existing:
        f.addLookup(lk_name, "gpos_pair", ("right_to_left",),
                    (("mark", (("arab", ("dflt",)),)),))
        f.addLookupSubtable(lk_name, st_name)
        print("  created GPOS lookup: %s" % lk_name)
    else:
        st_name = f.getLookupSubtables(lk_name)[0]

    em = float(f.em or 1000)
    extra = em * SUKUN_ON_WAW_EXTRA_EM
    gap = em * SUKUN_ON_WAW_GAP_EM
    for wn in waw_names:
        wb = bbox(f[wn])
        for sn in sukun_names:
            sb = bbox(f[sn])
            # Snap sukun.ymin to just above waw.ymax, then a little extra down.
            dy = (wb[3] + gap) - sb[1] - extra
            # Only lower, never raise.
            if dy > 0:
                dy = -extra
            dy = int(round(dy))
            try:
                f[wn].addPosSub(st_name, sn,
                                0, 0, 0, 0,
                                0, dy, 0, 0)
                print("  GPOS %s + %s  dy=%d" % (wn, sn, dy))
            except Exception as e:
                print("  ! GPOS %s + %s failed: %s" % (wn, sn, e))


def contextual_source(f, role, form, sources):
    table = {
        "yeh": YEH_FORMS,
        "keheh": KEHEH_FORMS,
        "kaf_ar": KAF_AR_FORMS,
    }.get(role, {})
    spec = table.get(form)
    if spec:
        n = find_glyph(f, *spec)
        if n:
            return n
    return sources.get(role) or sources.get("waw")


# ---------------- main ----------------
def main():
    donor = fontforge.open(donor_path) if donor_path else None
    work = tempfile.NamedTemporaryFile(suffix=".sfd", delete=False).name

    try:
        f = fontforge.open(src)
        f.save(work)
        f.close()
        f = fontforge.open(work)
        print("opened %s: %d glyphs" % (src, len(list(f.glyphs()))))
        print("metric mode: proportional, source-glyph widths preserved")

        apply_xaqan_names(f)

        waw = find_glyph(f, *WAW)
        keheh = find_glyph(f, *KEHEH)
        kaf_ar = find_glyph(f, *KAF_AR) or keheh
        yeh = find_glyph(f, *YEH)
        sources = {"waw": waw, "keheh": keheh or kaf_ar,
                   "kaf_ar": kaf_ar, "yeh": yeh}
        print("sources: و=%s  ک=%s  ك=%s  ی=%s" % (waw, keheh, kaf_ar, yeh))
        if not waw:
            print("ERROR: the font has no و (U+0648) - not an Arabic-script font")
            return 1

        mark_roles = {
            "small_v": (SMALL_V,),
            "damma": (DAMMA,),
            "circumflex": (CIRCUMFLEX,),
        }

        dots_name = extract_sheen_dots(f, donor)

        subtables = {}
        for feat in ("fina", "init", "medi"):
            subtables[feat] = ensure_gsub_feature(f, feat)

        rules = {}
        touched = []

        for spec in LETTERS:
            base = glyph_by_cp(f, spec["cp"])
            if not base and exists(f, spec["name"]):
                base = spec["name"]

            if spec.get("skip_create"):
                if not base:
                    print("  skip %s U+%04X (expected to already exist)"
                          % (spec["name"], spec["cp"]))
                    continue
                print("  keep existing %s U+%04X" % (base, spec["cp"]))
            else:
                if not base:
                    base = ensure_char(f, spec["cp"], spec["name"])
                else:
                    # Rebuild placeholders so marks / dots are applied.
                    base = ensure_char(f, spec["cp"], spec["name"])
                local_src = sources.get(spec["base_role"])
                donor_cp = {
                    "waw": 0x0648, "yeh": 0x06CC,
                    "keheh": 0x06A9, "kaf_ar": 0x0643,
                }.get(spec["base_role"])
                got = copy_from_local_or_donor(
                    f, donor, base, local_src, donor_cp=donor_cp)
                print("  built %s U+%04X from %s%s"
                      % (base, spec["cp"], spec["base_role"],
                         " (donor)" if got == "donor" else ""))

                if spec.get("mark_role"):
                    queries = []
                    for namespec in mark_roles[spec["mark_role"]]:
                        queries.append((f, namespec))
                        queries.append((donor, namespec))
                    if overlay_mark(f, donor, base, queries):
                        print("    + mark %s" % spec["mark_role"])
                    else:
                        print("    ! mark %s missing — base only"
                              % spec["mark_role"])

                if spec.get("dots"):
                    if overlay_dots(f, base, dots_name):
                        print("    + three dots of ش")
                    else:
                        print("    ! three dots unavailable")

            g = f[base]
            g.unicode = spec["cp"]
            touched.append(base)

            if spec.get("connecting"):
                role = spec["forms_src"]
                form_map = {}
                encoded_forms = {}
                if spec.get("forms") and len(spec["forms"]) >= 4:
                    # isol, fina, init, medi — ڭ presentation forms
                    encoded_forms = {
                        "isol": spec["forms"][0],
                        "fina": spec["forms"][1],
                        "init": spec["forms"][2],
                        "medi": spec["forms"][3],
                    }
                    # isol presentation = same drawing as the base we just built
                    fcp, fname = encoded_forms["isol"]
                    isol = ensure_char(f, fcp, fname)
                    copy_outlines(f, isol, base)
                    f[isol].width = f[base].width
                    touched.append(isol)
                    print("    form %s U+%04X" % (isol, fcp))

                for form in ("init", "medi", "fina"):
                    fn = base + "." + form
                    src_g = contextual_source(f, role, form, sources)
                    if not src_g:
                        src_g = local_src or waw
                    if not exists(f, fn):
                        f.createChar(-1, fn)
                    copy_outlines(f, fn, src_g)
                    f[fn].width = f[src_g].width
                    if spec.get("mark_role"):
                        queries = []
                        for namespec in mark_roles[spec["mark_role"]]:
                            queries.append((f, namespec))
                            queries.append((donor, namespec))
                        overlay_mark(f, donor, fn, queries)
                    if spec.get("dots"):
                        overlay_dots(f, fn, dots_name)
                    print("    created %s (unencoded)" % fn)
                    touched.append(fn)
                    form_map[form] = fn

                    if form in encoded_forms:
                        fcp, fname = encoded_forms[form]
                        enc = ensure_char(f, fcp, fname)
                        copy_outlines(f, enc, fn)
                        f[enc].width = f[fn].width
                        touched.append(enc)
                        print("    form %s U+%04X" % (enc, fcp))

                rules[base] = [
                    (subtables["fina"], form_map["fina"]),
                    (subtables["init"], form_map["init"]),
                    (subtables["medi"], form_map["medi"]),
                ]
            else:
                final_target = None
                for fcp, fname in spec.get("forms") or ():
                    target = glyph_by_cp(f, fcp)
                    if not target and exists(f, fname):
                        target = fname
                    if not target:
                        target = ensure_char(f, fcp, fname)
                        copy_outlines(f, target, base)
                        f[target].width = f[base].width
                        print("    created %s U+%04X" % (target, fcp))
                    else:
                        f[target].unicode = fcp
                    touched.append(target)
                    final_target = target
                if final_target:
                    rules[base] = [(subtables["fina"], final_target)]

            if spec.get("strip_anchors"):
                clear_anchors(f, base)
                for nm in list(touched):
                    if nm == base or nm.startswith(base + ".") or nm.startswith("uni"):
                        pass
                # strip this letter's forms explicitly
                for extra in list(touched[-8:]):
                    if extra == base or extra.startswith(base):
                        clear_anchors(f, extra)
                for fcp_fname in spec.get("forms") or ():
                    clear_anchors(f, fcp_fname[1])
                    n = glyph_by_cp(f, fcp_fname[0])
                    if n:
                        clear_anchors(f, n)

        # GDEF base class
        for nm in touched:
            if exists(f, nm):
                try:
                    f[nm].glyphclass = "baseglyph"
                except Exception:
                    pass

        add_sukun_lowering(f)

        # ؤ may exist without having gone through skip path's form loop
        for cp, name in ((0x0624, "uni0624"), (0xFE85, "uniFE85"),
                         (0xFE86, "uniFE86")):
            n = glyph_by_cp(f, cp) or (name if exists(f, name) else None)
            if n:
                clear_anchors(f, n)

        f.save(work)
        f.close()

        with open(work, encoding="utf-8") as fh:
            text = fh.read()
        for gname, rls in rules.items():
            m = re.search(r"(StartChar: %s\n)(.*?)(\nEndChar)"
                          % re.escape(gname), text, re.S)
            if not m:
                print("  ! glyph block %s not found in SFD" % gname)
                continue
            body = re.sub(r"[ \t]*Substitution2: [^\n]*\n?", "", m.group(2))
            to_add = ['Substitution2: "%s" %s' % (sub, tgt) for sub, tgt in rls]
            insert = "\n" + "\n".join(to_add) + "\n"
            text = text[:m.start(2)] + body + insert + text[m.end(2):]
            print("  GSUB %s: %d rule(s)" % (gname, len(to_add)))
        with open(work, "w", encoding="utf-8") as fh:
            fh.write(text)

        f = fontforge.open(work)
        apply_xaqan_names(f)
        f.generate(out)
        f.close()
        print("generated %s" % out)
        return 0
    finally:
        if donor:
            donor.close()
        if os.path.exists(work):
            os.unlink(work)


if __name__ == "__main__":
    sys.exit(main())
