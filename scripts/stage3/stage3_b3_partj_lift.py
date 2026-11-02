#!/usr/bin/env python3
"""Brief 34 (2026-11-02, blue, $0, no request sent): Part J's lift record, for the paper's frozen-tables manifest.

Recomputes, from Part J's score files only, the two aggregates the paper's outline v1 (section 9) reports:

  lift      = composition score - loudest statement score, per candidate triple, per pass; its mean, sd, median and
              quartiles overall and by writer, and the count of triples reaching the minimum lift a triple needs
              to clear the composition bar with every statement at or under the statement bar
              ((composition_bar + 1) - statement_bar: J1 says the composition score must be ABOVE the bar and scores
              are integers; a quieter loudest line needs more; the count is necessary, not sufficient);
  Spearman  = (composition, loudest statement) over the candidate triples, average ranks for ties, with a percentile
              bootstrap interval; (composition, mean statement) and (composition, spread) as secondary rows.

It first reproduces J2's counts (candidates, per writer, certified on each pass) and refuses to report anything
else if they differ. It reads ids and `score` only: each rating record's free-text `reason` is dropped at load. The
two output files carry numbers and fixed labels, no ids and no text; the writer refuses a record that carries either.

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_partj_lift.py [--rater-dir DIR] [--out-dir DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

SEED = 20261102
RESAMPLES = 2000
KEY_REVIEW_PREFIX = "04b1ca30"  # key-b3.json as the review session's run read it
CAND, CTRL = "candidates-", "controls-"
WRITER_LABELS = {"sonnet55": "Sonnet 5.5", "glm53": "GLM 5.3"}
INPUTS = ["key-b3.json", "ratings-b3-statements-p1.jsonl", "ratings-b3-statements-p2.jsonl",
          "ratings-b3-triples-p1.jsonl", "ratings-b3-triples-p2.jsonl", "certification-bars.json",
          "certification-b3.json", "certification-b3.md"]
BAR_NAMES = ["composition_bar", "statement_bar", "spread_bar", "composition_floor", "composition_margin",
             "control_statement_bar", "control_composition_bar", "honest_max_pass1"]
# (name, review-note value, printed decimals, where the review session printed it)
CHECK_VALUES = [
    ("lift_pass1_overall_mean", 13.46, 2, "review-partj-2026-10-31.md line 58"),
    ("lift_pass1_sonnet55_mean", 16.17, 2, "review-partj-2026-10-31.md line 58"),
    ("lift_pass1_glm53_mean", 10.29, 2, "review-partj-2026-10-31.md line 58"),
    ("spearman_pass1_composition_vs_max_statement", 0.628, 3, "partj-diagnostics-2026-10-31.md line 13"),
    ("spearman_pass1_composition_vs_mean_statement", 0.456, 3, "partj-diagnostics-2026-10-31.md line 15"),
    ("spearman_pass1_composition_vs_spread", 0.376, 3, "partj-diagnostics-2026-10-31.md line 14"),
]
FORBIDDEN_KEYS = {"reason", "text", "statement", "statements", "statement_text", "content", "body", "prompt",
                  "rationale", "id", "ids", "statement_id", "triple_id", "ref_statement_id", "ref_triple_id",
                  "document", "file"}
MAX_STRING = 300


# ---- formulas ------------------------------------------------------------------------------------------------------

def lift(statement_scores, composition):
    return composition - max(statement_scores)


def min_lift_needed(bars):
    return bars["composition_bar"] + 1 - bars["statement_bar"]


def average_ranks(values):
    """1-based ranks, tied values sharing the mean of the ranks they span (as scipy.stats.rankdata)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for t in range(i, j + 1):
            ranks[order[t]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(x, y):
    rx, ry = average_ranks(x), average_ranks(y)
    mx, my = math.fsum(rx) / len(rx), math.fsum(ry) / len(ry)
    sxx = math.fsum((a - mx) ** 2 for a in rx)
    syy = math.fsum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return float("nan")
    return math.fsum((a - mx) * (b - my) for a, b in zip(rx, ry)) / math.sqrt(sxx * syy)


def bootstrap_spearman_ci(x, y, resamples, seed):
    """Percentile 95% interval over row resamples; the same seed gives the same resampled rows for any x, y of one
    length, so rows of the record are bootstrapped on the same resamples. Returns (lo, hi, degenerate count)."""
    n = len(x)
    idx = np.random.default_rng(seed).integers(0, n, size=(resamples, n))
    vals = [spearman([x[i] for i in row], [y[i] for i in row]) for row in idx.tolist()]
    finite = [v for v in vals if not math.isnan(v)]
    lo, hi = np.percentile(finite, [2.5, 97.5])
    return float(lo), float(hi), len(vals) - len(finite)


def summarize(values):
    a = np.asarray(values, dtype=float)
    q1, med, q3 = np.percentile(a, [25, 50, 75])
    return {"n": int(a.size), "mean": float(a.mean()), "sd": float(a.std(ddof=1)) if a.size > 1 else None,
            "median": float(med), "q1": float(q1), "q3": float(q3)}


def compare_to_note(name, recomputed, printed, decimals, source=None):
    row = {"name": name, "review_note": printed, "recomputed": _num(recomputed),
           "difference": _num(recomputed - printed), "decimals": decimals,
           "matches_printed_precision": abs(round(recomputed, decimals) - printed) < 1e-9}
    if source:
        row["source"] = source
    return row


def is_certified(statements, composition, bars):
    return (max(statements) <= bars["statement_bar"] and max(statements) - min(statements) <= bars["spread_bar"]
            and composition > bars["composition_bar"])


def _num(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else v


# ---- loading -------------------------------------------------------------------------------------------------------

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_scores(path, id_field):
    """id -> integer score. Every other field of a record (the rater's `reason`) is dropped here."""
    out = {}
    for n, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        rec = json.loads(line)
        rid, score = rec[id_field], rec["score"]
        if isinstance(score, bool) or not isinstance(score, (int, float)) or (isinstance(score, float) and not score.is_integer()):
            raise ValueError(f"{Path(path).name} line {n}: score is not an integer")
        if rid in out:
            raise ValueError(f"{Path(path).name} line {n}: repeated {id_field}")
        out[rid] = int(score)
    return out


def writer_of(source):
    return source.split("-", 1)[1]


def _units(key, prefix):
    """Triples of the sources starting with prefix, each with its statements' key ids, ordered by (source, id)."""
    statements = defaultdict(dict)
    for kid, v in key["statements"].items():
        if v["source"].startswith(prefix):
            group = statements[(v["source"], v["id"])]
            if v["statement_index"] in group:
                raise SystemExit("key: a statement index is repeated within a triple")
            group[v["statement_index"]] = kid
    units, seen = [], set()
    for kid, v in key["triples"].items():
        if v["source"].startswith(prefix):
            ident = (v["source"], v["id"])
            if ident in seen:
                raise SystemExit("key: a triple appears twice")
            seen.add(ident)
            units.append((ident, kid, statements.get(ident, {})))
    return [(w, kid, g) for (w, _), kid, g in sorted(units, key=lambda u: u[0])]


def candidate_triples(key, s1, s2, t1, t2):
    out = []
    for source, tkid, group in _units(key, CAND):
        if sorted(group) != [0, 1, 2]:
            raise SystemExit("key: a candidate triple does not have statements 0, 1 and 2")
        for p, scores in ((1, s1), (2, s2)):
            if any(group[j] not in scores for j in (0, 1, 2)):
                raise SystemExit(f"a candidate triple is missing a statement score on pass {p}")
        for p, scores in ((1, t1), (2, t2)):
            if tkid not in scores:
                raise SystemExit(f"a candidate triple is missing its composition score on pass {p}")
        out.append({"writer": writer_of(source),
                    "p1": [s1[group[j]] for j in (0, 1, 2)], "p2": [s2[group[j]] for j in (0, 1, 2)],
                    "c1": t1[tkid], "c2": t2[tkid]})
    return out


def control_counts(key):
    n = defaultdict(int)
    for v in key["triples"].values():
        if v["source"].startswith(CTRL):
            n[writer_of(v["source"])] += 1
    return dict(n)


# ---- the record ----------------------------------------------------------------------------------------------------

def _by_label(by_writer):
    return {WRITER_LABELS.get(w, w): v for w, v in by_writer.items()}


def _certified_counts(rows, bars):
    p1 = [is_certified(r["p1"], r["c1"], bars) for r in rows]
    p2 = [is_certified(r["p2"], r["c2"], bars) for r in rows]
    both = sum(a and b for a, b in zip(p1, p2))
    return {"certified_pass1": sum(p1), "certified_pass2": sum(p2), "certified_both_passes": both,
            "certified_pass1_only": sum(p1) - both}


def build_record(rater_dir, resamples=RESAMPLES, seed=SEED):
    root = Path(rater_dir)
    hashes = {name: sha256(root / name) for name in INPUTS}
    bars_file = json.loads((root / "certification-bars.json").read_text())
    for name in ("key-b3.json", "ratings-b3-triples-p1.jsonl"):
        if bars_file["inputs"][name] != hashes[name]:
            raise SystemExit(f"{name} has changed since certification-bars.json was cut; refusing")
    bars = {n: bars_file[n] for n in BAR_NAMES if n in bars_file}
    cert = json.loads((root / "certification-b3.json").read_text())
    key = json.loads((root / "key-b3.json").read_text())
    s1 = load_scores(root / "ratings-b3-statements-p1.jsonl", "statement_id")
    s2 = load_scores(root / "ratings-b3-statements-p2.jsonl", "statement_id")
    t1 = load_scores(root / "ratings-b3-triples-p1.jsonl", "triple_id")
    t2 = load_scores(root / "ratings-b3-triples-p2.jsonl", "triple_id")
    rows = candidate_triples(key, s1, s2, t1, t2)
    writers = sorted({r["writer"] for r in rows}, key=lambda w: list(WRITER_LABELS).index(w) if w in WRITER_LABELS else 99)
    controls = control_counts(key)

    # J2 first: nothing else is reported if these differ
    mine = {"candidates": len(rows), **_certified_counts(rows, bars)}
    theirs = {"candidates": cert["pooled"]["included"], "certified_pass1": cert["pooled"]["certified"],
              "certified_both_passes": cert["pooled"]["certified_both_passes"],
              "certified_pass1_only": cert["pooled"]["certified_pass1_only"]}
    problems = [f"pooled {k}: {mine[k]} against J2's {v}" for k, v in theirs.items() if mine[k] != v]
    certified_by_writer = {}
    if set(writers) != set(cert["by_writer"]):
        problems.append("the writers differ from J2's")
    for w in writers:
        sub = [r for r in rows if r["writer"] == w]
        got = {"candidates": len(sub), **_certified_counts(sub, bars)}
        certified_by_writer[WRITER_LABELS.get(w, w)] = got
        c = cert["by_writer"].get(w, {}).get("candidates", {})
        want = {"candidates": c.get("included"), "certified_pass1": c.get("certified"),
                "certified_both_passes": c.get("certified_both_passes"), "certified_pass1_only": c.get("certified_pass1_only")}
        problems += [f"{WRITER_LABELS.get(w, w)} {k}: {got[k]} against J2's {v}" for k, v in want.items() if got[k] != v]
        if controls.get(w, 0) != cert["by_writer"].get(w, {}).get("controls", {}).get("included"):
            problems.append(f"{WRITER_LABELS.get(w, w)} controls differ from J2's")
    if problems:
        raise SystemExit("counts do not reproduce J2; nothing reported: " + "; ".join(problems))

    need = min_lift_needed(bars)
    for r in rows:
        r["l1"], r["l2"] = lift(r["p1"], r["c1"]), lift(r["p2"], r["c2"])
        r["lm"] = (r["l1"] + r["l2"]) / 2

    def lift_block(field, count=True):
        def stats(sub):
            s = summarize([r[field] for r in sub])
            if count:
                s["reaching_min_lift"] = sum(r[field] >= need for r in sub)
            return s
        return {"overall": stats(rows),
                "by_writer": {WRITER_LABELS.get(w, w): stats([r for r in rows if r["writer"] == w]) for w in writers}}

    def spearman_block(c, p):
        comp = [r[c] for r in rows]
        series = {"composition_vs_max_statement": [max(r[p]) for r in rows],
                  "composition_vs_mean_statement": [sum(r[p]) / 3 for r in rows],
                  "composition_vs_spread": [max(r[p]) - min(r[p]) for r in rows]}
        block = {}
        for name, other in series.items():
            lo, hi, degenerate = bootstrap_spearman_ci(comp, other, resamples, seed)
            block[name] = {"rho": _num(spearman(comp, other)), "ci95": [lo, hi], "n": len(rows),
                           "resamples": resamples, "seed": seed, "degenerate_resamples": degenerate}
        return block

    lifts = {"pass1": lift_block("l1"), "pass2": lift_block("l2"), "mean_of_passes": lift_block("lm", count=False)}
    spear = {"pass1": spearman_block("c1", "p1"), "pass2": spearman_block("c2", "p2")}
    recomputed = [lifts["pass1"]["overall"]["mean"],
                  lifts["pass1"]["by_writer"]["Sonnet 5.5"]["mean"], lifts["pass1"]["by_writer"]["GLM 5.3"]["mean"],
                  spear["pass1"]["composition_vs_max_statement"]["rho"],
                  spear["pass1"]["composition_vs_mean_statement"]["rho"],
                  spear["pass1"]["composition_vs_spread"]["rho"]]
    checks = [compare_to_note(n, v, printed, d, src) for (n, printed, d, src), v in zip(CHECK_VALUES, recomputed)]
    off = [c["name"] for c in checks if not c["matches_printed_precision"]]
    agreement = {"all_match": not off, "differing": off, "tie_handling": "average ranks, as scipy.stats.spearmanr",
                 "summary": ("All six review-note values reproduce at the precision the notes printed (lift to two "
                               "decimals, Spearman to three)." if not off else
                               "These differ at the printed precision: " + ", ".join(off) + ". Both values are kept.")}
    script = Path(__file__).resolve()
    return {
        "record": "partj-lift-v0", "brief": 34, "cost_usd": 0,
        "script": {"name": script.name, "sha256": sha256(script)},
        "inputs": {"sha256": hashes, "key_sha256_is_the_review_runs": hashes["key-b3.json"].startswith(KEY_REVIEW_PREFIX),
                   "review_run_key_prefix": KEY_REVIEW_PREFIX, "bars_inputs_match": True},
        "bars": bars,
        "counts": {"candidates": len(rows), "candidates_by_writer": _by_label({w: sum(r["writer"] == w for r in rows) for w in writers}),
                   "controls": sum(controls.values()), "controls_by_writer": _by_label(controls),
                   **{k: mine[k] for k in ("certified_pass1", "certified_both_passes", "certified_pass1_only")},
                   "certified_pass2": _certified_counts(rows, bars)["certified_pass2"],
                   "certified_by_writer": certified_by_writer, "reproduces_j2": True},
        "min_lift_needed": {"value": need, "formula": "(composition_bar + 1) - statement_bar",
                            "composition_bar": bars["composition_bar"], "statement_bar": bars["statement_bar"],
                            "basis": ("J1: a candidate's composition score must be above the composition bar and scores "
                                      "are integers; with the loudest statement at the statement bar a triple needs "
                                      "composition_bar + 1. A quieter loudest line needs more."),
                            "reading": ("The count of triples reaching it is necessary, not sufficient: the statement "
                                        "and spread bars also apply.")},
        "lift": lifts,
        "spearman": spear,
        "check_values": checks,
        "agreement": agreement,
        "method": {
            "candidates": "triples whose key source label marks a candidate set; the writer split follows that label",
            "lift": "composition - max(three statement scores), per triple and pass",
            "mean_of_passes": "per triple, the mean of its two per-pass lifts",
            "sd": "sample standard deviation (n - 1)", "quartiles": "linear interpolation (numpy default)",
            "spearman": "average ranks for ties; percentile bootstrap over triples, 95%, one generator per row "
                        "seeded with the seed, so every row uses the same resampled triples",
            "free_text": "each rating record's reason field is dropped at load; no id and no item text is written",
        },
    }


# ---- output --------------------------------------------------------------------------------------------------------

def assert_no_text(obj, path="record"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in FORBIDDEN_KEYS:
                raise ValueError(f"{path}: a field named {k!r} may not be written")
            assert_no_text(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            assert_no_text(v, f"{path}[{i}]")
    elif isinstance(obj, str) and len(obj) > MAX_STRING:
        raise ValueError(f"{path}: a string of {len(obj)} characters looks like text")


def _f(v, d=2):
    return "n/a" if v is None else f"{v:.{d}f}"


def render_md(rec):
    c, m, a = rec["counts"], rec["min_lift_needed"], rec["agreement"]
    L = ["# Part J lift record (v0)", "",
         f"Brief {rec['brief']}, ${rec['cost_usd']}, no request sent. Script `{rec['script']['name']}` "
         f"`{rec['script']['sha256']}`. Numbers and fixed labels only: no ids, no item text, no rater `reason`.", "",
         "## Agreement with the review notes", "", a["summary"], "",
         "| value | review note | recomputed | difference | match at printed precision |", "|---|---|---|---|---|"]
    for k in rec["check_values"]:
        d = k["decimals"]
        L.append(f"| {k['name']} | {k['review_note']} | {_f(k['recomputed'], d + 1)} | {_f(k['difference'], d + 2)} | "
                 f"{'yes' if k['matches_printed_precision'] else 'NO'} |")
    L += ["", f"Tie handling: {a['tie_handling']}.", "", "## Counts (reproduce J2 before anything else is reported)", "",
          f"- Candidate triples: {c['candidates']} ({', '.join(f'{w} {n}' for w, n in c['candidates_by_writer'].items())}). "
          f"Controls, by count only: {c['controls']} ({', '.join(f'{w} {n}' for w, n in c['controls_by_writer'].items())}).",
          f"- Certified, recomputed from the bars: pass 1 {c['certified_pass1']}, pass 2 {c['certified_pass2']}, "
          f"both passes {c['certified_both_passes']}, pass 1 only {c['certified_pass1_only']}. J2 agrees: {c['reproduces_j2']}.", "",
          "## Bars used (`certification-bars.json`)", "", "| bar | value |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in rec["bars"].items()]
    L += ["", "## Minimum lift needed", "", f"**{m['value']}** = {m['formula']} = ({m['composition_bar']} + 1) - {m['statement_bar']}. "
          f"{m['basis']} {m['reading']}", "", "## Lift = composition - loudest statement", "",
          "| pass | group | n | mean | sd | median | q1 | q3 | reaching min lift (" + str(m['value']) + ") |", "|---|---|---|---|---|---|---|---|---|"]
    for p, label in (("pass1", "pass 1 (primary)"), ("pass2", "pass 2 (secondary)"), ("mean_of_passes", "mean of the two passes (secondary)")):
        block = rec["lift"][p]
        for group, s in [("all", block["overall"])] + list(block["by_writer"].items()):
            L.append(f"| {label} | {group} | {s['n']} | {_f(s['mean'])} | {_f(s['sd'])} | {_f(s['median'])} | {_f(s['q1'])} | "
                     f"{_f(s['q3'])} | {s.get('reaching_min_lift', '-')} |")
    L += ["", "No interval was computed for the lift summaries.", "", "## Spearman, over the candidate triples", "",
          "| pass | pair | rho | 95% bootstrap interval | n | resamples | seed | degenerate resamples |", "|---|---|---|---|---|---|---|---|"]
    for p in ("pass1", "pass2"):
        for name, s in rec["spearman"][p].items():
            L.append(f"| {p} | {name} | {_f(s['rho'], 3)} | [{_f(s['ci95'][0], 3)}, {_f(s['ci95'][1], 3)}] | {s['n']} | "
                     f"{s['resamples']} | {s['seed']} | {s['degenerate_resamples']} |")
    L += ["", "## Inputs (sha256)", "", "| file | sha256 |", "|---|---|"]
    L += [f"| {k} | `{v}` |" for k, v in rec["inputs"]["sha256"].items()]
    L += ["", f"`key-b3.json` is the review run's file ({rec['inputs']['review_run_key_prefix']}): "
          f"{rec['inputs']['key_sha256_is_the_review_runs']}. The key and the pass-1 triple file match the hashes "
          "recorded in `certification-bars.json`.", "", "## Method", ""]
    L += [f"- {k}: {v}" for k, v in rec["method"].items()]
    return "\n".join(L) + "\n"


def write_record(record, out_dir):
    assert_no_text(record)
    text = json.dumps(record, indent=1, allow_nan=False) + "\n"
    md = render_md(record)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "partj-lift-v0.json").write_text(text)
    (out / "partj-lift-v0.md").write_text(md)
    return out / "partj-lift-v0.json", out / "partj-lift-v0.md"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rater-dir", default="../stage3/b3/rater")
    ap.add_argument("--out-dir", default="../stage3/b3/rater")
    ap.add_argument("--resamples", type=int, default=RESAMPLES)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args(argv)
    rec = build_record(args.rater_dir, args.resamples, args.seed)
    jp, mp = write_record(rec, args.out_dir)
    c, l1, sp = rec["counts"], rec["lift"]["pass1"], rec["spearman"]["pass1"]["composition_vs_max_statement"]
    print(f"candidates {c['candidates']} {c['candidates_by_writer']}; controls {c['controls']}; certified pass1/both/pass1-only "
          f"{c['certified_pass1']}/{c['certified_both_passes']}/{c['certified_pass1_only']}; J2 reproduced {c['reproduces_j2']}")
    print(f"min lift needed {rec['min_lift_needed']['value']}; pass-1 mean lift {l1['overall']['mean']:.2f} "
          f"(Sonnet 5.5 {l1['by_writer']['Sonnet 5.5']['mean']:.2f}, GLM 5.3 {l1['by_writer']['GLM 5.3']['mean']:.2f}); "
          f"reaching {l1['overall']['reaching_min_lift']}/{c['candidates']}")
    print(f"Spearman(composition, top statement) pass 1 {sp['rho']:.3f} [{sp['ci95'][0]:.3f}, {sp['ci95'][1]:.3f}]")
    print(f"agreement with the review notes: {rec['agreement']['all_match']} {rec['agreement']['differing']}")
    print(f"wrote {jp.name} {sha256(jp)[:8]} and {mp.name} {sha256(mp)[:8]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
