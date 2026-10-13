"""Shared loader: returns texts in READING order (first sign = first sign read)."""
import csv
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def sign_names():
    p = os.path.join(ROOT, "analysis", "sign_names.csv")
    return {r["sign"]: (r["name"], r["class_by_shape"]) for r in csv.DictReader(open(p))}


def name(s, _cache={}):
    if not _cache:
        _cache.update(sign_names())
    return "%s[%s]" % (s, _cache[s][0]) if s in _cache else s


def load_icit(single_line_only=False):
    """ICIT digitisation. Stored order puts the jar sign first for both DIRECTION values,
    i.e. it is uniformly the reverse of reading order (verified in run_analysis.check_direction),
    so every text is reversed. Line breaks become separate 'lines'."""
    out = []
    for r in csv.DictReader(open(os.path.join(ROOT, "data/derived/icit_texts.csv"), encoding="utf-8")):
        toks = r["signs_as_stored"].split()[::-1]
        lines, cur = [], []
        for t in toks:
            if t == "|":
                if cur:
                    lines.append(cur)
                cur = []
            else:
                cur.append(t)
        if cur:
            lines.append(cur)
        if single_line_only and len(lines) != 1:
            continue
        r = dict(r)
        r["lines"] = lines
        r["signs"] = [s for l in lines for s in l]
        out.append(r)
    return out


def load_m77():
    """Mahadevan 1977, one entry per line; sign '0' = damaged/doubtful sign."""
    out = []
    for r in csv.DictReader(open(os.path.join(ROOT, "data/derived/m77_texts.csv"), encoding="utf-8")):
        out.append({"id": r["id"], "signs": r["signs"].split()})
    return out
