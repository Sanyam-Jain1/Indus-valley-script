"""Build analysis-ready corpora from the downloaded sources.

Outputs (data/derived/, not committed):
  icit_texts.csv  one row per inscribed object from Yajnadevam's ICIT digitisation:
                  id, cisi, site, material, object_type, motif, complete, direction,
                  signs (space-separated, reading order, '|' marks a line break)
  m77_texts.csv   one row per text line from Mahadevan 1977 (M77 sign numbers)

Reading order. GLYPHSEQUENCE.IDX stores signs in the order they were keyed in; the
DIRECTION field says whether that order runs L/R or R/L on the object.  We do NOT trust
either convention a priori: run_analysis.py checks it empirically (the 'jar' sign, the
commonest Indus sign, is known from every concordance to close texts).
"""
import csv
import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
OUT = os.path.join(HERE, "..", "data", "derived")

TUPLE_RE = re.compile(r"\(((?:[^()\"]|\"[^\"]*\")*)\)")
FIELD_RE = re.compile(r'\s*("([^"]*)"|NULL|[-\d.]+)\s*(?:,|$)')


def insert_block(sql, table):
    m = re.search(r"INSERT INTO %s\s*\([^)]*\)\s*VALUES(.*?);\s*\n" % table, sql, re.S)
    if not m:
        raise ValueError("no INSERT block for " + table)
    rows = []
    for t in TUPLE_RE.finditer(m.group(1)):
        fields = []
        for f in FIELD_RE.finditer(t.group(1)):
            if f.group(2) is not None:
                fields.append(f.group(2))
            elif f.group(1) == "NULL":
                fields.append(None)
            else:
                fields.append(f.group(1))
        rows.append(fields)
    return rows


def object_type(features):
    """Collapse ICIT feature codes into coarse object classes."""
    for code, label in (("SEAL:CY", "cylinder_seal"), ("SEAL", "seal"), ("TAB:I", "incised_tablet"),
                        ("TAB:B", "bas_relief_tablet"), ("TAB", "tablet"), ("TAG", "sealing"),
                        ("POT", "pottery"), ("BNGL", "bangle"), ("ROD", "rod"), ("IMPL", "implement")):
        if any(f.startswith(code) for f in features):
            return label
    return "other"


def build_icit():
    sql = open(os.path.join(RAW, "indus-website", "population-script.sql"), encoding="utf-8").read()
    sites = {r[0]: r[1] for r in insert_block(sql, "SITE")}
    seals = {int(r[0]): r for r in insert_block(sql, "SEAL")}
    insc = {int(r[0]): r for r in insert_block(sql, "INSCRIPTION")}
    feats = {int(r[0]): r[1] for r in insert_block(sql, "FEATURE")}
    obj_feats = {}
    for sid, qid in insert_block(sql, "ICONOGRAPHYFEATURES"):
        obj_feats.setdefault(int(sid), []).append(feats[int(qid)])
    motif = {int(r[0]): r[1] for r in insert_block(sql, "ICONOGRAPHY")}
    glyph_uni = {int(r[0]): html.unescape(r[1]) for r in insert_block(sql, "GLYPH")}
    seq = {}
    for sid, gid, idx in insert_block(sql, "GLYPHSEQUENCE"):
        seq.setdefault(int(sid), []).append((int(idx), int(gid)))

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "icit_texts.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "cisi", "site", "material", "object_type", "features", "motif",
                    "complete", "direction", "signs_as_stored"])
        for sid in sorted(seq):
            glyphs = [g for _, g in sorted(seq[sid])]
            toks = ["|" if g == 0 else str(g) for g in glyphs]
            s = seals.get(sid, [sid, None, None, None])
            i = insc.get(sid, [sid, "Y", "R/L"])
            fl = obj_feats.get(sid, [])
            w.writerow([sid, s[3] or "", sites.get(s[1], "Unknown"), s[2] or "", object_type(fl),
                        ";".join(fl), motif.get(sid, ""), i[1], i[2], " ".join(toks)])
    with open(os.path.join(OUT, "icit_glyph_codepoints.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["glyph", "codepoint"])
        for g, u in sorted(glyph_uni.items()):
            if g:
                w.writerow([g, "%04X" % ord(u[0])])
    print("icit:", len(seq), "objects")


def build_m77():
    src = os.path.join(RAW, "indus_decipher", "data", "m77_indusscript_real_corpus.csv")
    with open(src, encoding="utf-8") as f, \
            open(os.path.join(OUT, "m77_texts.csv"), "w", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        w.writerow(["id", "signs"])
        n = 0
        for row in csv.DictReader(f):
            signs = [s.replace("MSg", "") for s in row["sign_sequence"].split()]
            w.writerow([row["inscription_id"], " ".join(signs)])
            n += 1
    print("m77:", n, "lines")


if __name__ == "__main__":
    build_icit()
    build_m77()
