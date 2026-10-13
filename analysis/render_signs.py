"""Render ICIT sign glyphs (from the sk_indus_script web font shipped with the ICIT digitisation)
into labelled contact sheets so sign shapes can be inspected by eye."""
import csv, os, sys
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
FONT = os.path.join(ROOT, "data/raw/indus-website/src/assets/fonts/sk_indus_script-webfont.ttf")


def load():
    cp = {int(r["glyph"]): chr(int(r["codepoint"], 16))
          for r in csv.DictReader(open(os.path.join(ROOT, "data/derived/icit_glyph_codepoints.csv")))}
    freq = Counter()
    for r in csv.DictReader(open(os.path.join(ROOT, "data/derived/icit_texts.csv"))):
        freq.update(t for t in r["signs_as_stored"].split() if t != "|")
    return cp, freq


def sheet(glyphs, cp, freq, out, cols=10, cell=110):
    font = ImageFont.truetype(FONT, 64)
    label = ImageFont.load_default(14)
    rows = (len(glyphs) + cols - 1) // cols
    img = Image.new("RGB", (cols * cell, rows * cell), "white")
    d = ImageDraw.Draw(img)
    for i, g in enumerate(glyphs):
        x, y = (i % cols) * cell, (i // cols) * cell
        d.rectangle([x, y, x + cell - 1, y + cell - 1], outline="#ccc")
        d.text((x + cell / 2, y + 48), cp[g], font=font, fill="black", anchor="mm")
        d.text((x + 4, y + cell - 18), "%d (n=%d)" % (g, freq[str(g)]), font=label, fill="#b00")
    img.save(out)


if __name__ == "__main__":
    cp, freq = load()
    os.makedirs(os.path.join(ROOT, "results/figures"), exist_ok=True)
    top = [int(g) for g, _ in freq.most_common()]
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    for k in range(0, n, 100):
        sheet(top[k:k + 100], cp, freq, os.path.join(ROOT, "results/figures/signs_by_frequency_%03d.png" % (k + 1)))
    print(len(freq), "sign types;", sum(freq.values()), "tokens")
