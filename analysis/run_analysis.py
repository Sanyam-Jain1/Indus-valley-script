"""Structural analysis of the Indus script corpus.

Usage:  python3 analysis/run_analysis.py
Writes results/summary.json, results/tables/*.csv, results/figures/*.png and a readable
log results/analysis_log.md.  Every number quoted in report/ comes from these outputs.
"""
import json
import math
import os
import random
from collections import Counter, defaultdict

import numpy as np
from scipy import stats
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from corpus import ROOT, load_icit, load_m77, name, sign_names

RES = os.path.join(ROOT, "results")
TAB = os.path.join(RES, "tables")
FIG = os.path.join(RES, "figures")
for d in (RES, TAB, FIG):
    os.makedirs(d, exist_ok=True)

random.seed(0)
np.random.seed(0)
SUMMARY = {}
LOG = []

STROKE_NUMERALS = {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "13": 3, "14": 3, "15": 3,
                   "16": 6, "17": 7, "18": 8, "19": 10, "55": 12, "56": 12}
LONG_STROKES = {"31", "32", "33", "34", "35"}
FISH = {"220", "222", "226", "231", "233", "235", "236", "240", "241", "243", "219", "232"}
JAR = "740"


def log(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s)


def table(fname, header, rows):
    import csv
    with open(os.path.join(TAB, fname), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def md_table(header, rows, limit=None):
    rows = rows[:limit] if limit else rows
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def bh(pvals):
    """Benjamini-Hochberg q-values."""
    p = np.asarray(pvals, float)
    n = len(p)
    order = np.argsort(p)
    q = np.empty(n)
    prev = 1.0
    for rank, i in enumerate(order[::-1]):
        k = n - rank
        prev = min(prev, p[i] * n / k)
        q[i] = prev
    return q


def entropy(counter):
    n = sum(counter.values())
    return -sum(c / n * math.log2(c / n) for c in counter.values() if c)


# ---------------------------------------------------------------------------
# 0. data
# ---------------------------------------------------------------------------
ALL = load_icit()
SINGLE = [r for r in ALL if len(r["lines"]) == 1]
# unique texts (identical sign strings counted once) for sequence statistics
_seen = set()
UNIQ = []
for r in SINGLE:
    k = tuple(r["signs"])
    if k not in _seen:
        _seen.add(k)
        UNIQ.append(r["signs"])
M77 = [r["signs"] for r in load_m77()]
M77_CLEAN = [t for t in M77 if "0" not in t]


def check_direction():
    log("\n## 1. Reading direction\n")
    raw_first = Counter(r["signs_as_stored"].split()[0] for r in ALL)
    by_dir = defaultdict(lambda: [0, 0])
    for r in ALL:
        st = [t for t in r["signs_as_stored"].split() if t != "|"]
        if len(st) > 1 and JAR in st:
            by_dir[r["direction"]][0] += st[0] == JAR
            by_dir[r["direction"]][1] += st[-1] == JAR
    log("Jar sign position in STORED order (first, last), by DIRECTION field:", dict(by_dir))
    log("=> stored order is reverse reading order for both directions; texts are reversed.")
    # positional entropy in reading order
    first = Counter(t[0] for t in UNIQ if len(t) > 1)
    last = Counter(t[-1] for t in UNIQ if len(t) > 1)

    def k80(c):
        tot, acc = sum(c.values()), 0
        for i, (_, v) in enumerate(c.most_common(), 1):
            acc += v
            if acc >= 0.8 * tot:
                return i
    res = {"H_first_bits": round(entropy(first), 3), "H_last_bits": round(entropy(last), 3),
           "signs_covering_80pct_of_first": k80(first), "signs_covering_80pct_of_last": k80(last),
           "jar_share_of_text_final": round(last[JAR] / sum(last.values()), 3)}
    m_first = Counter(t[0] for t in M77_CLEAN if len(t) > 1)
    m_last = Counter(t[-1] for t in M77_CLEAN if len(t) > 1)
    res["M77_H_first_bits"] = round(entropy(m_first), 3)
    res["M77_H_last_bits"] = round(entropy(m_last), 3)
    res["M77_jar342_share_of_text_final"] = round(m_last["342"] / sum(m_last.values()), 3)
    res["M77_signs_covering_80pct_of_first"] = k80(m_first)
    res["M77_signs_covering_80pct_of_last"] = k80(m_last)
    log("Position entropies (reading order):", res)
    SUMMARY["direction"] = res


def corpus_profile():
    log("\n## 2. Corpus profile\n")
    toks = [s for r in ALL for s in r["signs"]]
    freq = Counter(toks)
    lens = [len(r["signs"]) for r in ALL]
    hapax = sum(1 for v in freq.values() if v == 1)
    f1, f2 = hapax, sum(1 for v in freq.values() if v == 2)
    chao1 = len(freq) + f1 * f1 / (2 * f2)
    ranks = np.arange(1, len(freq) + 1)
    vals = np.array(sorted(freq.values(), reverse=True), float)
    sl, ic, rv, _, _ = stats.linregress(np.log(ranks[:200]), np.log(vals[:200]))
    top10 = sum(v for _, v in freq.most_common(10)) / len(toks)
    p = {"objects": len(ALL), "single_line_objects": len(SINGLE), "unique_single_line_texts": len(UNIQ),
         "tokens": len(toks), "sign_types": len(freq), "hapax_types": hapax,
         "hapax_share_of_types": round(hapax / len(freq), 3), "chao1_inventory_estimate": round(chao1),
         "mean_text_length": round(float(np.mean(lens)), 2), "median_text_length": float(np.median(lens)),
         "max_text_length": max(lens), "texts_of_length_le_5": round(float(np.mean(np.array(lens) <= 5)), 3),
         "zipf_slope_top200": round(sl, 3), "zipf_r2": round(rv ** 2, 3), "top10_token_share": round(top10, 3),
         "M77_lines": len(M77), "M77_sign_types": len(Counter(s for t in M77 for s in t if s != "0"))}
    log(p)
    SUMMARY["profile"] = p
    # type-token growth (sign-inventory saturation)
    order = list(range(len(ALL)))
    curves = []
    for rep in range(20):
        random.shuffle(order)
        seen, c = set(), []
        for i in order:
            seen.update(ALL[i]["signs"])
            c.append(len(seen))
        curves.append(c)
    curve = np.mean(curves, axis=0)
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    ax[0].loglog(ranks, vals, ".", ms=3)
    ax[0].set(title="Rank-frequency (ICIT)", xlabel="rank", ylabel="tokens")
    ax[1].hist(lens, bins=range(1, max(lens) + 2), color="#4a6fa5")
    ax[1].set(title="Text length (signs per object)", xlabel="signs", ylabel="objects")
    ax[2].plot(np.arange(1, len(curve) + 1), curve)
    ax[2].axhline(chao1, ls="--", c="grey")
    ax[2].text(50, chao1 + 5, "Chao1 estimate %d" % chao1, fontsize=8)
    ax[2].set(title="Sign types vs objects read", xlabel="objects", ylabel="distinct signs")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "corpus_profile.png"), dpi=120)
    plt.close(fig)
    rows = [(s, name(s), v, round(v / len(toks), 4)) for s, v in freq.most_common()]
    table("sign_frequencies.csv", ["sign", "label", "count", "share"], rows)
    log(md_table(["sign", "count", "share"], [(r[1], r[2], r[3]) for r in rows], 25))
    return freq


def positional_profiles(freq):
    log("\n## 3. Positional profiles (unique single-line texts, length>=2)\n")
    pos = defaultdict(Counter)
    for t in UNIQ:
        if len(t) < 2:
            pos[t[0]]["solo"] += 1
            continue
        for i, s in enumerate(t):
            pos[s]["initial" if i == 0 else "final" if i == len(t) - 1 else "medial"] += 1
    rows = []
    for s, c in pos.items():
        n = sum(c.values())
        if n < 15:
            continue
        rows.append((s, name(s), n, round(c["initial"] / n, 2), round(c["medial"] / n, 2),
                     round(c["final"] / n, 2), c["solo"]))
    rows.sort(key=lambda r: -r[2])
    table("positional_profiles.csv", ["sign", "label", "n", "initial", "medial", "final", "solo"], rows)
    fin = sorted([r for r in rows if r[2] >= 25], key=lambda r: -r[5])[:12]
    ini = sorted([r for r in rows if r[2] >= 25], key=lambda r: -r[3])[:12]
    log("Most final-loving signs:\n" + md_table(["sign", "n", "init", "med", "final", "solo"],
                                                 [(r[1],) + r[2:] for r in fin]))
    log("Most initial-loving signs:\n" + md_table(["sign", "n", "init", "med", "final", "solo"],
                                                   [(r[1],) + r[2:] for r in ini]))
    SUMMARY["positional"] = {"final_loving": [(r[0], r[5]) for r in fin], "initial_loving": [(r[0], r[3]) for r in ini]}
    return {r[0]: r for r in rows}


def sequence_entropy():
    log("\n## 4. Sequential structure: entropy and held-out predictability\n")

    def cond_entropy(texts, vocab):
        big = Counter()
        for t in texts:
            seq = ["<s>"] + [s if s in vocab else "<unk>" for s in t] + ["</s>"]
            big.update(zip(seq, seq[1:]))
        ctx = Counter()
        for (a, _), v in big.items():
            ctx[a] += v
        n = sum(big.values())
        return -sum(v / n * math.log2(v / ctx[a]) for (a, _), v in big.items())

    def shuffled(texts):
        out = []
        for t in texts:
            t = list(t)
            random.shuffle(t)
            out.append(t)
        return out

    def unigram_random(texts):
        pool = [s for t in texts for s in t]
        return [[random.choice(pool) for _ in t] for t in texts]

    freq = Counter(s for t in UNIQ for s in t)
    res = []
    for N in (20, 40, 80, 160, 320):
        vocab = {s for s, _ in freq.most_common(N)}
        real = cond_entropy(UNIQ, vocab)
        shuf = np.mean([cond_entropy(shuffled(UNIQ), vocab) for _ in range(10)])
        uni = np.mean([cond_entropy(unigram_random(UNIQ), vocab) for _ in range(10)])
        res.append((N, round(real, 3), round(shuf, 3), round(uni, 3)))
    log("Conditional entropy H(next|current) in bits; columns: vocab size N, real, "
        "within-text shuffle, unigram-random:\n" + md_table(["N", "real", "shuffled", "random"], res))

    # held-out cross-entropy of n-gram models (interpolated, add-k), 5-fold
    def xent(order, train, test, lam=(0.6, 0.3, 0.1)):
        V = len({s for t in train for s in t}) + 2
        cnt = [Counter() for _ in range(order + 1)]
        for t in train:
            seq = ["<s>"] * 3 + t + ["</s>"]
            for i in range(3, len(seq)):
                for k in range(order + 1):
                    cnt[k][tuple(seq[i - k:i + 1])] += 1
        ctx = [Counter() for _ in range(order + 1)]
        for k in range(1, order + 1):
            for g, v in cnt[k].items():
                ctx[k][g[:-1]] += v
        tot = sum(cnt[0].values())
        H, n = 0.0, 0
        for t in test:
            seq = ["<s>"] * 3 + t + ["</s>"]
            for i in range(3, len(seq)):
                p_uni = (cnt[0][(seq[i],)] + 0.1) / (tot + 0.1 * V)
                ps = [p_uni]
                for k in range(1, order + 1):
                    g = tuple(seq[i - k:i + 1])
                    c = ctx[k][g[:-1]]
                    ps.append((cnt[k][g] + 0.1 * ps[-1] * V) / (c + 0.1 * V) if c else ps[-1])
                H -= math.log2(ps[-1])
                n += 1
        return H / n
    idx = list(range(len(UNIQ)))
    random.shuffle(idx)
    folds = [idx[i::5] for i in range(5)]
    xr = {}
    for order in (0, 1, 2, 3):
        vals = []
        for f in folds:
            fs = set(f)
            train = [UNIQ[i] for i in idx if i not in fs]
            test = [UNIQ[i] for i in f]
            vals.append(xent(order, train, test))
        xr[order] = round(float(np.mean(vals)), 3)
    # same for within-text shuffled control
    SH = shuffled(UNIQ)
    xs = {}
    for order in (0, 1, 2):
        vals = []
        for f in folds:
            fs = set(f)
            vals.append(xent(order, [SH[i] for i in idx if i not in fs], [SH[i] for i in f]))
        xs[order] = round(float(np.mean(vals)), 3)
    log("Held-out cross-entropy (bits/sign), n-gram order 0..3:", xr, " shuffled control:", xs)
    SUMMARY["entropy"] = {"conditional_entropy_by_vocab": res, "heldout_xent_real": xr,
                          "heldout_xent_shuffled": xs}


def ngrams_and_segmentation():
    log("\n## 5. Recurrent sign groups and segmentation\n")
    ng = Counter()
    for t in UNIQ:
        for n in (2, 3, 4):
            for i in range(len(t) - n + 1):
                ng[tuple(t[i:i + n])] += 1
    uni = Counter(s for t in UNIQ for s in t)
    N = sum(uni.values())
    rows = []
    for g, c in ng.most_common():
        if c < 6:
            break
        pmi = math.log2((c / N) / np.prod([uni[s] / N for s in g]))
        rows.append((" ".join(g), " + ".join(name(s) for s in g), len(g), c, round(pmi, 2)))
    table("recurrent_ngrams.csv", ["ngram_reading_order", "labels", "n", "count", "pmi"], rows)
    log("Most frequent sign groups (reading order):\n" +
        md_table(["group", "len", "count", "PMI"], [(r[1], r[2], r[3], r[4]) for r in rows], 30))
    tri = [r for r in rows if r[2] >= 3][:15]
    log("Most frequent 3-4 sign groups:\n" + md_table(["group", "len", "count", "PMI"], [(r[1], r[2], r[3], r[4]) for r in tri]))

    # unsupervised segmentation: unigram 'word' model over candidate chunks, hard-EM Viterbi
    cand = {g for g, c in ng.items() if c >= 3} | {(s,) for s in uni}
    logp = {}
    tot = sum(ng[g] for g in cand if len(g) > 1) + N
    for g in cand:
        logp[g] = math.log((ng[g] if len(g) > 1 else uni[g[0]]) / tot)

    def viterbi(t):
        best = [0.0] + [-1e18] * len(t)
        back = [0] * (len(t) + 1)
        for j in range(1, len(t) + 1):
            for i in range(max(0, j - 4), j):
                g = tuple(t[i:j])
                if g in logp and best[i] + logp[g] > best[j]:
                    best[j], back[j] = best[i] + logp[g], i
        segs, j = [], len(t)
        while j > 0:
            segs.append(tuple(t[back[j]:j]))
            j = back[j]
        return segs[::-1]
    for it in range(8):
        seg_counts = Counter(g for t in UNIQ for g in viterbi(t))
        tot = sum(seg_counts.values())
        logp = {g: math.log(c / tot) - 1.2 * (len(g) - 1) for g, c in seg_counts.items()}  # length penalty
    segs = Counter(g for t in UNIQ for g in viterbi(t))
    multi = [(g, c) for g, c in segs.most_common() if len(g) > 1]
    covered = sum(c * len(g) for g, c in multi) / N
    rows = [(" ".join(g), " + ".join(name(s) for s in g), c) for g, c in multi[:60]]
    table("segmentation_lexicon.csv", ["segment", "labels", "count"], rows)
    examples = []
    for t in sorted(UNIQ, key=len, reverse=True)[:12]:
        examples.append(" | ".join("-".join(g) for g in viterbi(t)))
    log("Segmentation lexicon size %d (multi-sign units: %d), multi-sign units cover %.1f%% of tokens" %
        (len(segs), len(multi), 100 * covered))
    log("Top multi-sign segments:\n" + md_table(["segment", "count"], [(r[1], r[2]) for r in rows], 25))
    log("Segmented examples (longest texts):\n" + "\n".join("    " + e for e in examples))
    SUMMARY["segmentation"] = {"lexicon_size": len(segs), "multi_sign_units": len(multi),
                               "token_coverage_by_multi_sign_units": round(covered, 3),
                               "top_units": [(r[0], r[2]) for r in rows[:25]]}


def context_vectors(texts, signs):
    left, right = defaultdict(Counter), defaultdict(Counter)
    for t in texts:
        seq = ["<s>"] + t + ["</s>"]
        for i in range(1, len(seq) - 1):
            left[seq[i]][seq[i - 1]] += 1
            right[seq[i]][seq[i + 1]] += 1
    feats = sorted({k for s in signs for k in left[s]} | {k for s in signs for k in right[s]})
    fi = {f: i for i, f in enumerate(feats)}
    X = np.zeros((len(signs), 2 * len(feats)))
    for r, s in enumerate(signs):
        for k, v in left[s].items():
            X[r, fi[k]] = v
        for k, v in right[s].items():
            X[r, len(feats) + fi[k]] = v
    # PPMI
    tot = X.sum()
    pr = X.sum(1, keepdims=True) / tot
    pc = X.sum(0, keepdims=True) / tot
    with np.errstate(divide="ignore", invalid="ignore"):
        pmi = np.log((X / tot) / (pr * pc))
    pmi[~np.isfinite(pmi)] = 0
    P = np.maximum(pmi, 0)
    P /= np.linalg.norm(P, axis=1, keepdims=True) + 1e-12
    return P


def sign_classes(freq):
    log("\n## 6. Distributional sign classes (who substitutes for whom)\n")
    signs = [s for s, c in Counter(s for t in UNIQ for s in t).most_common() if c >= 12]
    P = context_vectors(UNIQ, signs)
    Z = linkage(P, "average", metric="cosine")
    lab = fcluster(Z, t=0.80, criterion="distance")
    groups = defaultdict(list)
    for s, l in zip(signs, lab):
        groups[l].append(s)
    rows = []
    for l, mem in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(mem) < 2:
            continue
        rows.append((l, len(mem), "; ".join(name(s) for s in mem)))
    table("distributional_classes.csv", ["cluster", "size", "members"], rows)
    log(md_table(["cluster", "size", "members"], rows, 20))
    # base sign vs modified forms
    S = P @ P.T
    idx = {s: i for i, s in enumerate(signs)}
    rand = [S[i, j] for i in range(len(signs)) for j in range(i + 1, len(signs))]
    tests = [("740", ["741", "742", "745", "760", "700", "705", "706", "752"]),
             ("220", ["222", "226", "231", "233", "235", "236", "240"]),
             ("90", ["91", "100", "104", "125", "142", "151"]),
             ("2", ["1", "3", "4", "5", "32", "33", "31"])]
    out = []
    for base, vs in tests:
        for v in vs:
            if base in idx and v in idx:
                sim = S[idx[base], idx[v]]
                out.append((name(base), name(v), round(float(sim), 3),
                            round(float(np.mean(np.array(rand) < sim)), 3)))
    log("Context similarity of a base sign and its modified forms (cosine of PPMI context vectors; "
        "'pctile' = share of all sign pairs that are less similar):\n" +
        md_table(["base", "variant", "cosine", "pctile"], out))
    table("base_vs_variant_similarity.csv", ["base", "variant", "cosine", "percentile"], out)
    SUMMARY["base_vs_variant"] = out
    # nearest neighbours of key signs
    nn = []
    for s in ["740", "400", "520", "220", "235", "2", "32", "861", "817", "820", "390", "90", "803", "590"]:
        if s in idx:
            o = np.argsort(-S[idx[s]])[1:6]
            nn.append((name(s), "; ".join("%s %.2f" % (name(signs[j]), S[idx[s], j]) for j in o)))
    log("Nearest distributional neighbours:\n" + md_table(["sign", "neighbours"], nn))
    SUMMARY["nearest_neighbours"] = nn


def substitution_frames():
    log("\n## 7. Substitution frames (minimal pairs: X _ Y with different fillers)\n")
    frames = defaultdict(Counter)
    for t in UNIQ:
        seq = ["<s>"] + t + ["</s>"]
        for i in range(1, len(seq) - 1):
            frames[(seq[i - 1], seq[i + 1])][seq[i]] += 1
    pair = Counter()
    for f, c in frames.items():
        fill = [s for s in c]
        for i in range(len(fill)):
            for j in range(i + 1, len(fill)):
                a, b = sorted((fill[i], fill[j]))
                pair[(a, b)] += 1
    rows = [(name(a), name(b), n) for (a, b), n in pair.most_common(30)]
    log(md_table(["sign A", "sign B", "shared frames"], rows))
    table("substitution_pairs.csv", ["a", "b", "shared_frames"], rows)
    # what fills the slot right before the final jar?
    pre = Counter(t[-2] for t in UNIQ if len(t) >= 2 and t[-1] == JAR)
    log("Signs immediately before a text-final jar: %d distinct signs; H=%.2f bits; top: %s" %
        (len(pre), entropy(pre), ", ".join("%s(%d)" % (name(s), c) for s, c in pre.most_common(10))))
    SUMMARY["jar_left_context"] = {"distinct": len(pre), "entropy_bits": round(entropy(pre), 2)}


def jar_and_genres():
    log("\n## 8. The jar sign, text genres and duplication\n")
    by = defaultdict(lambda: [0, 0, 0])  # objects, objects with jar, tokens
    for r in ALL:
        b = by[r["object_type"]]
        b[0] += 1
        b[1] += JAR in r["signs"]
        b[2] += len(r["signs"])
    rows = [(k, v[0], round(v[1] / v[0], 3), round(v[2] / v[0], 2)) for k, v in sorted(by.items(), key=lambda kv: -kv[1][0])]
    log(md_table(["object type", "objects", "share with jar", "mean length"], rows))
    table("object_types.csv", ["object_type", "objects", "share_with_jar", "mean_len"], rows)
    solo = sum(1 for r in ALL if r["signs"] == [JAR])
    log("Objects whose entire text is the jar sign:", solo)
    # duplication
    dup = defaultdict(list)
    for r in ALL:
        dup[tuple(r["signs"])].append(r)
    rep = {k: v for k, v in dup.items() if len(v) > 1}
    rows = []
    for ot in ("seal", "bas_relief_tablet", "incised_tablet", "sealing", "pottery"):
        objs = [r for r in ALL if r["object_type"] == ot]
        nd = sum(1 for r in objs if len(dup[tuple(r["signs"])]) > 1)
        rows.append((ot, len(objs), round(nd / max(1, len(objs)), 3)))
    log("Share of objects whose exact text recurs on another object:\n" + md_table(["type", "objects", "duplicated"], rows))
    cross = [(k, sorted({r["site"] for r in v})) for k, v in rep.items() if len({r["site"] for r in v}) > 1 and len(k) >= 3]
    log("Texts (len>=3) found at more than one site: %d. Examples: %s" %
        (len(cross), "; ".join("%s @ %s" % ("-".join(k), "/".join(s)) for k, s in cross[:8])))
    SUMMARY["genres"] = {"by_type": rows, "jar_solo_objects": solo, "cross_site_texts_len3plus": len(cross)}


def numerals():
    log("\n## 9. Stroke signs: numerals?\n")
    nxt, prv = defaultdict(Counter), defaultdict(Counter)
    for t in UNIQ:
        for i, s in enumerate(t):
            if s in STROKE_NUMERALS or s in LONG_STROKES:
                nxt[s][t[i + 1] if i + 1 < len(t) else "</s>"] += 1
                prv[s][t[i - 1] if i else "<s>"] += 1
    rows = []
    for s in sorted(set(nxt), key=lambda s: -sum(nxt[s].values())):
        n = sum(nxt[s].values())
        if n < 8:
            continue
        rows.append((name(s), n, round(nxt[s]["</s>"] / n, 2), round(prv[s]["<s>"] / n, 2), round(entropy(nxt[s]), 2),
                     ", ".join("%s(%d)" % (name(x), c) for x, c in nxt[s].most_common(4))))
    log(md_table(["stroke sign", "n", "P(final)", "P(initial)", "H(next)", "most common next signs"], rows))
    table("stroke_signs.csv", ["sign", "n", "p_final", "p_initial", "H_next", "next"], rows)
    # numeral + fish combos (Parpola's astral reading test)
    combos = Counter()
    for t in UNIQ:
        for a, b in zip(t, t[1:]):
            if a in STROKE_NUMERALS and b in FISH:
                combos[(STROKE_NUMERALS[a], name(b))] += 1
    log("Numeral -> fish-sign bigrams (reading order):", dict(combos.most_common(15)))
    # Do short strokes ever stack beyond 8? Which numerals exist at all?
    SUMMARY["numerals"] = {"rows": rows, "numeral_fish": [(k[0], k[1], v) for k, v in combos.most_common(15)]}


def iconography():
    log("\n## 10. Do texts depend on the seal's animal?\n")

    def norm(m):
        if not m:
            return None
        m = m.split(":")[0]
        return {"Bull1": "unicorn", "Bult": "short-horned bull", "Zebu": "zebu", "Gaur": "gaur/bison",
                "Elep": "elephant", "Rhin": "rhinoceros", "Tigr": "tiger", "Buff": "buffalo",
                "Gavi": "gharial", "Goat": "goat/markhor", "Mult": "composite animal", "Hare": "hare",
                "Fish": "fish", "Anth": "anthropomorphic", "Phyt": "plant", "Scene": "scene"}.get(m, None)
    seals = [r for r in ALL if r["object_type"] == "seal" and norm(r["motif"])]
    mot = Counter(norm(r["motif"]) for r in seals)
    log("Seals with identified motif:", len(seals), dict(mot.most_common()))
    # text length by motif
    len_rows = rows = []
    for m, c in mot.most_common():
        if c >= 10:
            L = [len(r["signs"]) for r in seals if norm(r["motif"]) == m]
            J = np.mean([JAR in r["signs"] for r in seals if norm(r["motif"]) == m])
            rows.append((m, c, round(float(np.mean(L)), 2), round(float(J), 2)))
    log(md_table(["motif", "seals", "mean text length", "share with jar"], rows))
    # sign x motif association (presence), unicorn vs all other motifs
    signs = [s for s, c in Counter(s for r in seals for s in set(r["signs"])).most_common() if c >= 10]
    res = []
    for m in [m for m, c in mot.items() if c >= 20]:
        inm = [set(r["signs"]) for r in seals if norm(r["motif"]) == m]
        out = [set(r["signs"]) for r in seals if norm(r["motif"]) != m]
        for s in signs:
            a = sum(s in x for x in inm)
            b = len(inm) - a
            c = sum(s in x for x in out)
            d = len(out) - c
            orr, p = stats.fisher_exact([[a, b], [c, d]])
            res.append((m, s, a, len(inm), c, len(out), orr, p))
    q = bh([r[-1] for r in res])
    sig = sorted([r + (qq,) for r, qq in zip(res, q) if qq < 0.05], key=lambda r: r[-1])
    rows = [(r[0], name(r[1]), "%d/%d" % (r[2], r[3]), "%d/%d" % (r[4], r[5]),
             "inf" if r[6] == float("inf") else round(r[6], 2), "%.1e" % r[8]) for r in sig]
    log("Sign-motif associations surviving FDR 5%% (%d tests):\n" % len(res) +
        md_table(["motif", "sign", "with motif", "other motifs", "odds ratio", "q"], rows, 30))
    table("sign_motif_associations.csv", ["motif", "sign", "with_motif", "other", "odds_ratio", "q"], rows)
    # overall mutual information vs permutation
    def mi(pairs):
        j = Counter(pairs)
        a = Counter(x for x, _ in pairs)
        b = Counter(y for _, y in pairs)
        n = len(pairs)
        return sum(c / n * math.log2(c * n / (a[x] * b[y])) for (x, y), c in j.items())
    pairs = [(norm(r["motif"]), s) for r in seals for s in set(r["signs"])]
    real = mi(pairs)
    ms = [p[0] for p in pairs]
    # permute motif labels at the seal level
    perm = []
    labels = [norm(r["motif"]) for r in seals]
    for _ in range(200):
        random.shuffle(labels)
        pp = [(labels[i], s) for i, r in enumerate(seals) for s in set(r["signs"])]
        perm.append(mi(pp))
    log("MI(motif; sign) = %.3f bits; permutation null mean %.3f (max %.3f) -> excess %.3f bits" %
        (real, np.mean(perm), np.max(perm), real - np.mean(perm)))
    SUMMARY["iconography"] = {"n_seals": len(seals), "motifs": dict(mot), "length_by_motif": len_rows,
                              "n_significant_assoc": len(sig), "mi_bits": round(real, 3),
                              "mi_null_mean": round(float(np.mean(perm)), 3), "mi_null_max": round(float(np.max(perm)), 3),
                              "assoc": [(r[0], r[1], r[4], r[5]) for r in rows[:30]]}


def regional():
    log("\n## 11. Regional variation: Mohenjo-daro vs Harappa (seals only)\n")
    sites = {"Mohenjo-daro": [], "Harappa": []}
    for r in ALL:
        if r["object_type"] == "seal" and r["site"] in sites:
            sites[r["site"]].append(r["signs"])
    cm = Counter(s for t in sites["Mohenjo-daro"] for s in t)
    ch = Counter(s for t in sites["Harappa"] for s in t)
    nm, nh = sum(cm.values()), sum(ch.values())
    res = []
    for s in set(cm) | set(ch):
        if cm[s] + ch[s] < 15:
            continue
        orr, p = stats.fisher_exact([[cm[s], nm - cm[s]], [ch[s], nh - ch[s]]])
        res.append((s, cm[s], ch[s], orr, p))
    q = bh([r[-1] for r in res])
    rows = sorted([(name(r[0]), r[1], r[2], round(r[3], 2), "%.1e" % qq) for r, qq in zip(res, q) if qq < 0.05],
                  key=lambda r: r[3])
    log("seals: M=%d (%d tokens), H=%d (%d tokens); %d signs tested, %d differ at FDR 5%%" %
        (len(sites["Mohenjo-daro"]), nm, len(sites["Harappa"]), nh, len(res), len(rows)))
    log(md_table(["sign", "Mohenjo-daro", "Harappa", "odds ratio (M/H)", "q"], rows))
    SUMMARY["regional"] = {"n_tested": len(res), "n_significant": len(rows), "rows": rows}


def paradigms():
    log("\n## 12. Kober-style alternations: shared stems, varying ends\n")
    # group unique texts (>=3 signs) by all but the last sign; and by all but the first sign
    by_stem = defaultdict(set)
    by_tail = defaultdict(set)
    for t in UNIQ:
        if len(t) >= 3:
            by_stem[tuple(t[:-1])].add(t[-1])
            by_tail[tuple(t[1:])].add(t[0])
    end_alt = Counter()
    for stem, ends in by_stem.items():
        for a in ends:
            for b in ends:
                if a < b:
                    end_alt[(a, b)] += 1
    beg_alt = Counter()
    for tail, begs in by_tail.items():
        for a in begs:
            for b in begs:
                if a < b:
                    beg_alt[(a, b)] += 1
    log("Stems seen with >1 final sign: %d; tails seen with >1 initial sign: %d" %
        (sum(1 for v in by_stem.values() if len(v) > 1), sum(1 for v in by_tail.values() if len(v) > 1)))
    log("Most frequent FINAL alternations (same preceding signs, different last sign):\n" +
        md_table(["a", "b", "stems"], [(name(a), name(b), c) for (a, b), c in end_alt.most_common(12)]))
    log("Most frequent INITIAL alternations (same following signs, different first sign):\n" +
        md_table(["a", "b", "tails"], [(name(a), name(b), c) for (a, b), c in beg_alt.most_common(12)]))
    ex = [(" ".join(name(s) for s in st), ", ".join(name(e) for e in sorted(en)))
          for st, en in sorted(by_stem.items(), key=lambda kv: -len(kv[1])) if len(en) > 2][:8]
    log("Stems with the most different endings:\n" + md_table(["stem (reading order)", "attested endings"], ex))
    SUMMARY["paradigms"] = {"final_alt": [(a, b, c) for (a, b), c in end_alt.most_common(12)],
                            "initial_alt": [(a, b, c) for (a, b), c in beg_alt.most_common(12)]}


def m77_replication():
    log("\n## 13. Replication on Mahadevan 1977 (independent transcription, different sign list)\n")
    big = Counter()
    for t in M77_CLEAN:
        big.update(zip(t, t[1:]))
    f = Counter(s for t in M77_CLEAN for s in t)
    last = Counter(t[-1] for t in M77_CLEAN if len(t) > 1)
    first = Counter(t[0] for t in M77_CLEAN if len(t) > 1)
    log("M77 clean lines: %d; top signs: %s" % (len(M77_CLEAN), f.most_common(8)))
    log("M77 top final: %s ; top initial: %s" % (last.most_common(6), first.most_common(6)))
    log("M77 top bigrams: %s" % big.most_common(10))
    SUMMARY["m77"] = {"lines_clean": len(M77_CLEAN), "top_final": last.most_common(6),
                      "top_initial": first.most_common(6), "top_bigrams": [(" ".join(k), v) for k, v in big.most_common(10)]}


def slot_grammar(prof):
    """Fit a 3-slot positional template: each sign gets an affinity for the start, core, or end
    region, estimated on training texts; evaluate on held-out texts how well affinity order
    predicts actual order (Kendall tau vs. random order)."""
    log("\n## 14. Is there a positional template? (held-out test)\n")
    idx = list(range(len(UNIQ)))
    random.shuffle(idx)
    cut = int(0.8 * len(idx))
    train = [UNIQ[i] for i in idx[:cut]]
    test = [UNIQ[i] for i in idx[cut:] if len(UNIQ[i]) >= 3]
    relpos = defaultdict(list)
    for t in train:
        for i, s in enumerate(t):
            relpos[s].append(i / (len(t) - 1) if len(t) > 1 else 0.5)
    mean_pos = {s: float(np.mean(v)) for s, v in relpos.items() if len(v) >= 3}
    taus, rnd = [], []
    for t in test:
        known = [(i, mean_pos[s]) for i, s in enumerate(t) if s in mean_pos]
        if len(known) < 3:
            continue
        tau = stats.kendalltau([k[0] for k in known], [k[1] for k in known])[0]
        if not np.isnan(tau):
            taus.append(tau)
        sh = [k[1] for k in known]
        random.shuffle(sh)
        tr = stats.kendalltau([k[0] for k in known], sh)[0]
        if not np.isnan(tr):
            rnd.append(tr)
    exact = 0
    tot = 0
    for t in test:
        known = [s for s in t if s in mean_pos]
        if len(known) < 3:
            continue
        tot += 1
        exact += sorted(known, key=lambda s: mean_pos[s]) == known
    log("Held-out texts: %d. Mean Kendall tau between actual order and order predicted from each sign's "
        "average position: %.3f (random: %.3f). Texts whose order is exactly predicted: %.1f%%" %
        (len(taus), np.mean(taus), np.mean(rnd), 100 * exact / tot))
    SUMMARY["slot_grammar"] = {"tau": round(float(np.mean(taus)), 3), "tau_random": round(float(np.mean(rnd)), 3),
                               "exact_order_pct": round(100 * exact / tot, 1), "n": len(taus)}


def attachment():
    """Which neighbour is each sign bound to?  For sign s, compare the mean PMI with the sign
    that follows it and with the sign that precedes it (token-weighted).  A numeral that
    qualifies the following sign (Num-N order) should bind rightwards."""
    log("\n## 15. Attachment direction (does a sign bind to what follows or what precedes?)\n")
    uni = Counter(s for t in UNIQ for s in t)
    big = Counter()
    for t in UNIQ:
        big.update(zip(t, t[1:]))
    N = sum(uni.values())
    NB = sum(big.values())

    def pmi(a, b):
        return math.log2((big[(a, b)] / NB) / ((uni[a] / N) * (uni[b] / N)))
    rows = []
    for s, c in uni.most_common():
        if c < 30:
            break
        r = [pmi(s, b) for t in UNIQ for a, b in zip(t, t[1:]) if a == s]
        l = [pmi(a, s) for t in UNIQ for a, b in zip(t, t[1:]) if b == s]
        if len(r) >= 10 and len(l) >= 10:
            rows.append((s, name(s), c, round(float(np.mean(r)), 2), round(float(np.mean(l)), 2),
                         round(float(np.mean(r) - np.mean(l)), 2)))
    rows.sort(key=lambda r: -r[5])
    table("attachment.csv", ["sign", "label", "n", "pmi_with_next", "pmi_with_prev", "right_minus_left"], rows)
    log("Binds rightwards (to the following sign):\n" + md_table(["sign", "n", "PMI next", "PMI prev", "diff"], [r[1:] for r in rows[:12]]))
    log("Binds leftwards (to the preceding sign):\n" + md_table(["sign", "n", "PMI next", "PMI prev", "diff"], [r[1:] for r in rows[-12:]]))
    num = [r for r in rows if r[0] in STROKE_NUMERALS or r[0] in LONG_STROKES]
    log("Stroke signs only:\n" + md_table(["sign", "n", "PMI next", "PMI prev", "diff"], [r[1:] for r in num]))
    SUMMARY["attachment"] = {"rightward": [(r[0], r[5]) for r in rows[:12]], "leftward": [(r[0], r[5]) for r in rows[-12:]],
                             "strokes": [(r[0], r[3], r[4], r[5]) for r in num]}


def initial_markers():
    log("\n## 16. The opening formula: [oval/diamond sign] + [two short strokes]\n")
    heads = ["817", "861", "820", "803", "806"]
    rows = []
    for h in heads:
        occ = [t for t in UNIQ if h in t]
        nxt = Counter(t[t.index(h) + 1] if t.index(h) + 1 < len(t) else "</s>" for t in occ)
        at0 = np.mean([t.index(h) == 0 for t in occ]) if occ else 0
        rows.append((name(h), len(occ), round(float(at0), 2), round(nxt["2"] / max(1, len(occ)), 2),
                     ", ".join("%s(%d)" % (name(x), c) for x, c in nxt.most_common(3))))
    log(md_table(["head", "texts", "share at text start", "share followed by 2 short strokes", "next signs"], rows))
    # what precedes '2 short strokes'?
    prev2 = Counter(t[i - 1] if i else "<s>" for t in UNIQ for i, s in enumerate(t) if s == "2")
    log("Signs preceding '2 short strokes': %s" % ", ".join("%s(%d)" % (name(x), c) for x, c in prev2.most_common(10)))
    pos2 = Counter(min(i, 4) for t in UNIQ for i, s in enumerate(t) if s == "2")
    log("Position (0-based, 4 = 4+) of '2 short strokes':", dict(sorted(pos2.items())))
    SUMMARY["opening_formula"] = {"rows": rows, "prev_of_2": prev2.most_common(10), "pos_of_2": dict(pos2)}


def heatmap():
    """Relative-position heat map for the 40 most frequent signs."""
    top = [s for s, _ in Counter(s for t in UNIQ for s in t).most_common(40)]
    bins = 5
    M = np.zeros((len(top), bins))
    for t in UNIQ:
        if len(t) < 2:
            continue
        for i, s in enumerate(t):
            if s in top:
                M[top.index(s), int(round((bins - 1) * i / (len(t) - 1)))] += 1
    M = M / M.sum(1, keepdims=True)
    order = np.argsort(M @ np.arange(bins))
    fig, ax = plt.subplots(figsize=(7, 11))
    ax.imshow(M[order], aspect="auto", cmap="Blues")
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels([name(top[i]) for i in order], fontsize=7)
    ax.set_xticks(range(bins))
    ax.set_xticklabels(["start", "", "middle", "", "end"])
    ax.set_title("Where each sign sits in a text (reading order)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "positional_heatmap.png"), dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    check_direction()
    freq = corpus_profile()
    prof = positional_profiles(freq)
    sequence_entropy()
    ngrams_and_segmentation()
    sign_classes(freq)
    substitution_frames()
    jar_and_genres()
    numerals()
    iconography()
    regional()
    paradigms()
    m77_replication()
    slot_grammar(prof)
    attachment()
    initial_markers()
    heatmap()
    with open(os.path.join(RES, "summary.json"), "w") as f:
        json.dump(SUMMARY, f, indent=1, default=str)
    with open(os.path.join(RES, "analysis_log.md"), "w") as f:
        f.write("# Analysis log (generated by analysis/run_analysis.py)\n\n" + "\n\n".join(LOG) + "\n")
