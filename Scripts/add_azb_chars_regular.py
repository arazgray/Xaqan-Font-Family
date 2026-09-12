#!/usr/bin/env python3
"""
Add South Azerbaijani (azb) letters to any Arabic-script font:
    ۆ U+06C6, ۇ U+06C7, ؤ U+0624, ؽ U+063D, ݣ U+0763
including every contextual form (isolated / initial / medial / final)
plus GSUB init / medi / fina rules so text shapes correctly.

Usage:
  fontforge -lang=py -script add_azb_chars_regular.py <input> [output] [donor]

  input : any font FontForge can open (.sfd, .ttf, .otf, ...)
  output: default = <input base>-azb.<ext>  (.ttf when input is .sfd)
  donor : optional font used only to supply a base glyph when the input
          font lacks the closest letters (e.g. Noto Naskh Arabic)

Placeholder strategy (fine-tune the small marks afterwards):
    ۆ ۇ ؤ <- the font's own و      ݣ <- the font's own ک      ؽ <- the font's own ی
Any of these letters already present in the input font are kept as-is.

Standard presentation forms (for direct codepoint access and for shaping
engines that fall back to them):
    ۆ (U+06C6): isolated U+FBD9, final U+FBDA
    ۇ (U+06C7): isolated U+FBD7, final U+FBD8
    ؤ (U+0624): isolated U+FE85, final U+FE86
    ؽ (U+063D) / ݣ (U+0763): no presentation forms -> unencoded .init/.medi/.fina
"""
import fontforge, sys, os, re, tempfile

# ---------------- arguments ----------------
src = sys.argv[1] if len(sys.argv) > 1 else "dist/Vazir-Code.sfd"
in_ext = os.path.splitext(src)[1].lower()
if len(sys.argv) > 2:
    out = sys.argv[2]
else:
    out_ext = ".ttf" if in_ext == ".sfd" else (in_ext or ".ttf")
    out = os.path.splitext(src)[0] + "-azb-regular" + out_ext
donor_path = sys.argv[3] if len(sys.argv) > 3 else None

# ---------------- sources for the closest letters ----------------
# role -> (unicode candidates, glyph-name candidates)
WAW = ((0x0648,), ("uni0648", "waw", "afii57441", "uni0648.fina"))
KAF = ((0x06A9, 0x0643), ("uni06A9", "uni0643", "keheh", "kaf", "afii57440"))
YEH = ((0x06CC, 0x064A), ("uni06CC", "uni064A", "farsiyeh", "yeh", "afii57534"))
# contextual forms of the closest letters (used for ؽ / ݣ)
YEH_FORMS = {"init": ((0xFBFE,), ("uniFBFE",)),
             "medi": ((0xFBFF,), ("uniFBFF",)),
             "fina": ((0xFBFD,), ("uniFBFD",))}
KAF_FORMS = {"init": ((0xFB90,), ("uniFB90",)),
             "medi": ((0xFB91,), ("uniFB91",)),
             "fina": ((0xFB8F,), ("uniFB8F",))}
FORMS_TABLE = {"yeh": YEH_FORMS, "kaf": KAF_FORMS}

# letter specs
LETTERS = [
    # ۆ -- non-connecting: isolated + final
    dict(cp=0x06C6, name="uni06C6", src="waw",
         forms=((0xFBD9, "uniFBD9"), (0xFBDA, "uniFBDA"))),
    # ۇ -- non-connecting
    dict(cp=0x06C7, name="uni06C7", src="waw",
         forms=((0xFBD7, "uniFBD7"), (0xFBD8, "uniFBD8"))),
    # ؤ -- non-connecting
    dict(cp=0x0624, name="uni0624", src="waw",
         forms=((0xFE85, "uniFE85"), (0xFE86, "uniFE86"))),
    # ؽ -- connecting: init/medi/fina from ی
    dict(cp=0x063D, name="uni063D", src="yeh", connecting=True, forms_src="yeh"),
    # ݣ -- connecting: init/medi/fina from ک
    dict(cp=0x0763, name="uni0763", src="kaf", connecting=True, forms_src="kaf"),
]


# ---------------- helpers ----------------
def exists(f, name):
    try:
        f[name]
        return True
    except TypeError:
        return False


def glyph_by_cp(f, cp):
    try:
        return f[cp].glyphname
    except (TypeError, ValueError):
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


def copy_outlines(f, dst, src):
    f.selection.none()
    f.selection.select(("more", None), src)
    f.copy()
    f.selection.none()
    f.selection.select(("more", None), dst)
    f.paste()
    f.selection.none()


def copy_from(f, donor, dst, local_src, donor_cp):
    """copy outlines into dst from local_src (this font) or donor[donor_cp]"""
    if local_src:
        copy_outlines(f, dst, local_src)
    elif donor:
        try:
            g = donor[donor_cp]
            donor.selection.none()
            donor.selection.select(("more", None), g.glyphname)
            donor.copy()
            f.selection.none()
            f.selection.select(("more", None), dst)
            f.paste()
            f.selection.none()
            return "donor"
        except (TypeError, ValueError):
            return None
    return local_src


def find_arabic_lookup(f, feature):
    """return (lookup_name, subtable_name) for the feature, or (None, None)"""
    for lk in f.gsub_lookups:
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


# ---------------- main ----------------
def main():
    donor = fontforge.open(donor_path) if donor_path else None
    work = tempfile.NamedTemporaryFile(suffix=".sfd", delete=False).name

    try:
        f = fontforge.open(src)
        f.save(work)
        f.close()
        f = fontforge.open(work)
        print(f"opened {src}: {len(list(f.glyphs()))} glyphs")

        print("metric mode: proportional, source-glyph widths preserved")

        waw = find_glyph(f, *WAW)
        kaf = find_glyph(f, *KAF)
        yeh = find_glyph(f, *YEH)
        sources = {"waw": waw, "kaf": kaf, "yeh": yeh}
        print(f"sources: و={waw}  ک={kaf}  ی={yeh}")
        if not waw:
            print("ERROR: the font has no و (U+0648) - not an Arabic-script font")
            return 1

        # ---- GSUB lookups: find or create fina / init / medi ----
        subtables = {}
        for feat in ("fina", "init", "medi"):
            lk, st = find_arabic_lookup(f, feat)
            if not st:
                lk_name = "'%s' Terminal Forms (AZB)" % feat
                f.addLookup(lk_name, "gsub_single", None,
                            ((feat, (("arab", ("dflt",)),)),))
                f.addLookupSubtable(lk_name, lk_name + " subtable")
                st = lk_name + " subtable"
                print(f"  created GSUB lookup: {lk_name}")
            subtables[feat] = st

        # ---- build each letter ----
        rules = {}
        for spec in LETTERS:
            base = glyph_by_cp(f, spec["cp"])
            if not base and exists(f, spec["name"]):
                base = spec["name"]
            if not base:
                f.createChar(spec["cp"], spec["name"])
                got = copy_from(f, donor, spec["name"], sources[spec["src"]],
                                spec["cp"])
                # Keep the donor glyph's original outlines and advance width.
                # Regular fonts should not be force-fitted to a monospace cell.
                base = spec["name"]
                print(f"  created {base} U+{spec['cp']:04X}"
                      + (" (from donor)" if got == "donor" else ""))
            g = f[base]
            g.unicode = spec["cp"]
            # Do not overwrite the existing/source advance width.

            # contextual forms
            if spec.get("connecting"):
                role = spec["forms_src"]
                for form in ("init", "medi", "fina"):
                    fn = base + "." + form
                    if not exists(f, fn):
                        src_g = find_glyph(f, *FORMS_TABLE[role][form])
                        if not src_g:
                            src_g = sources[role] or sources["waw"]
                        f.createChar(-1, fn)
                        copy_outlines(f, fn, src_g)
                        # copy_outlines does not copy metrics, so inherit the
                        # advance width from the contextual source glyph.
                        f[fn].width = f[src_g].width
                        print(f"  created {fn} (unencoded)")
                rules[base] = [(subtables["fina"], base + ".fina"),
                               (subtables["init"], base + ".init"),
                               (subtables["medi"], base + ".medi")]
            else:
                # standard presentation forms (isolated + final)
                final_target = None
                for fcp, fname in spec["forms"]:
                    target = glyph_by_cp(f, fcp)
                    if not target and exists(f, fname):
                        target = fname
                    if not target:
                        f.createChar(fcp, fname)
                        copy_outlines(f, fname, base)
                        # Presentation form uses the same advance width as base.
                        f[fname].width = f[base].width
                        target = fname
                        print(f"  created {fname} U+{fcp:04X}")
                    else:
                        f[target].unicode = fcp
                    final_target = target
                rules[base] = [(subtables["fina"], final_target)]

        # ---- force GDEF glyph class to BASE (see note below) ----
        touched = []
        for spec in LETTERS:
            b = glyph_by_cp(f, spec["cp"]) or spec["name"]
            touched.append(b)
            if spec.get("connecting"):
                touched += [b + ".init", b + ".medi", b + ".fina"]
            else:
                for fcp, fname in spec["forms"]:
                    touched.append(glyph_by_cp(f, fcp) or fname)
        for nm in touched:
            if exists(f, nm):
                try:
                    f[nm].glyphclass = "baseglyph"
                except Exception:
                    pass

        f.save(work)
        f.close()

        # ---- write GSUB rules into the SFD text ----
        with open(work, encoding="utf-8") as fh:
            text = fh.read()
        for gname, rls in rules.items():
            m = re.search(r"(StartChar: %s\n)(.*?)(\nEndChar)"
                          % re.escape(gname), text, re.S)
            if not m:
                print(f"  ! glyph block {gname} not found in SFD")
                continue
            body = re.sub(r"[ \t]*Substitution2: [^\n]*\n?", "", m.group(2))
            to_add = ['Substitution2: "%s" %s' % (sub, tgt) for sub, tgt in rls]
            insert = "\n" + "\n".join(to_add) + "\n"
            text = text[:m.start(2)] + body + insert + text[m.end(2):]
            print(f"  GSUB {gname}: {len(to_add)} rule(s)")
        with open(work, "w", encoding="utf-8") as fh:
            fh.write(text)

        # ---- regenerate in the requested format ----
        f = fontforge.open(work)
        f.generate(out)
        f.close()
        print(f"generated {out}")
        return 0
    finally:
        if donor:
            donor.close()
        if os.path.exists(work):
            os.unlink(work)


if __name__ == "__main__":
    sys.exit(main())
