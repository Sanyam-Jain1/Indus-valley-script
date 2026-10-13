"""Functional transliteration: rewrite every text as a sequence of the sign *roles*
established in run_analysis.py (positional zone, attachment, substitution class).
This is the most that can currently be 'decoded' without knowing the language: what each
sign DOES in a text, not how it was pronounced.

Writes results/tables/functional_readings.csv and results/figures/example_texts.png
"""
import csv
import os
from collections import Counter

from PIL import Image, ImageDraw, ImageFont

from corpus import ROOT, load_icit

ROLE = {}
for s in ("817", "861", "820", "692", "920"):
    ROLE[s] = "OPEN"            # >=60% text-initial, bind to what follows
ROLE["2"] = "DBL"               # satellite of the opener (58% directly after 817/861/820)
for s, n in {"1": 1, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "13": 3, "14": 3, "15": 3, "16": 6,
             "17": 7, "18": 8, "19": 10, "55": 12, "56": 12}.items():
    ROLE[s] = "NUM%d" % n       # short-stroke groups: bind to the FOLLOWING sign
for s, n in {"31": 1, "32": 2, "33": 3, "34": 2, "35": 4}.items():
    ROLE[s] = "LS%d" % n        # long strokes: behave differently from short ones (see report)
for s in ("220", "222", "226", "231", "233", "235", "236", "240", "241", "243", "219", "232"):
    ROLE[s] = "FISH"
for s in ("803", "806", "798"):
    ROLE[s] = "FISH~"           # leaf / facing-arcs signs that share the fish slot
for s in ("390", "405", "407", "413", "388"):
    ROLE[s] = "BRANCH"
ROLE["740"] = "JAR"
for s in ("400", "520", "527", "151", "154", "156", "90"):
    ROLE[s] = "CLOSE"           # >=75% text-final, often right after JAR
for s in ("705", "706"):
    ROLE[s] = "CUP"


def reading(signs):
    return " ".join(ROLE.get(s, "x" + s) for s in signs)


def main():
    texts = load_icit()
    out = os.path.join(ROOT, "results", "tables", "functional_readings.csv")
    pat = Counter()
    tok = cov = 0
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "cisi", "site", "object_type", "signs_reading_order", "functional_reading"])
        for r in texts:
            fr = reading(r["signs"])
            w.writerow([r["id"], r["cisi"], r["site"], r["object_type"], " ".join(r["signs"]), fr])
            tok += len(r["signs"])
            cov += sum(1 for s in r["signs"] if s in ROLE)
            # skeleton: collapse unknown signs to X
            pat[" ".join(ROLE.get(s, "X").rstrip("0123456789") if ROLE.get(s, "X").startswith("NUM") else ROLE.get(s, "X")
                         for s in r["signs"])] += 1
    print("tokens with an assigned role: %.1f%%" % (100 * cov / tok))
    print("most common text skeletons:")
    for p, c in pat.most_common(25):
        print("  %4d  %s" % (c, p))
    return texts


def draw_examples(texts, ids, path):
    font = ImageFont.truetype(os.path.join(ROOT, "data/raw/indus-website/src/assets/fonts/sk_indus_script-webfont.ttf"), 46)
    small = ImageFont.load_default(13)
    cps = {int(r["glyph"]): chr(int(r["codepoint"], 16))
           for r in csv.DictReader(open(os.path.join(ROOT, "data/derived/icit_glyph_codepoints.csv")))}
    by = {r["cisi"]: r for r in texts}
    rows = [by[i] for i in ids if i in by]
    cell, H = 78, 120
    width = max(760, max(len(r["signs"]) for r in rows) * cell + 170)
    img = Image.new("RGB", (width, H * len(rows) + 30), "white")
    d = ImageDraw.Draw(img)
    d.text((10, 6), "Reading order runs right to left on the seal; shown here in reading order, first sign on the left.",
           font=small, fill="#555")
    for k, r in enumerate(rows):
        y = 30 + k * H
        d.text((10, y + 30), "%s\n%s\n%s" % (r["cisi"], r["site"], r["object_type"]), font=small, fill="#333")
        for i, s in enumerate(r["signs"]):
            x = 170 + i * cell
            d.text((x + cell / 2, y + 35), cps[int(s)], font=font, fill="black", anchor="mm")
            d.text((x + cell / 2, y + 78), s, font=small, fill="#888", anchor="mm")
            d.text((x + cell / 2, y + 95), ROLE.get(s, "?"), font=small, fill="#b00", anchor="mm")
        d.line([(0, y + H - 6), (width, y + H - 6)], fill="#eee")
    img.save(path)


if __name__ == "__main__":
    T = main()
    # pick illustrative, complete, single-line seal texts that exercise the roles
    import re
    picks = []
    want = [r"^OPEN DBL NUM\d+ BRANCH", r"^OPEN DBL .*JAR$", r"JAR CLOSE$", r"CUP LS3 CLOSE",
            r"NUM7 x5\d\d JAR", r"LS2 FISH", r"^FISH x\d+ JAR$"]
    for w in want:
        for r in sorted(T, key=lambda r: len(r["signs"])):
            fr = reading(r["signs"])
            if r["object_type"] == "seal" and len(r["lines"]) == 1 and 3 <= len(r["signs"]) <= 7 \
                    and re.search(w, fr) and r["cisi"] and r["cisi"] not in picks:
                picks.append(r["cisi"])
                break
    draw_examples(T, picks, os.path.join(ROOT, "results", "figures", "example_texts.png"))
    print("examples:", picks)
