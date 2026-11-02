#!/usr/bin/env python3
"""Brief 34, dated note 2, item 2 (2026-11-02, blue, $0, no request sent): the v0.1 section appended to
partj-lift-v0.{json,md}. Nothing above the section changes: the v0 script (stage3_b3_partj_lift.py, the hash the v0
record names) is imported as it is, and the v0 files are extended, never regenerated.

  (a) the paired difference rho(composition, loudest statement) - rho(composition, mean statement), pass 1 and pass 2,
      with a 95% percentile interval over the record's own resamples (the same seed gives every row the same resampled
      triples, so the two rhos are paired resample by resample);
  (b) bootstrap 95% intervals for the pass-1 lift means, overall and by writer, on the same resamples, with the
      normal-approximation interval beside (the review session's indicative one);
  (c) among candidate triples whose pass-1 composition is above the composition bar: how many have lines more than
      10 apart, how many have every line at or under the statement bar, by writer and pooled.

It refuses unless the v0 record was written by the v0 script as it stands, the score files still hash as the v0 record
says, and the resamples reproduce all six of the v0 record's Spearman intervals exactly. The section carries numbers
and fixed labels only: no id, no item text, no rater `reason` (dropped at load by the v0 loader).

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_partj_lift_v01.py [--rater-dir DIR] [--record-dir DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_b3_partj_lift as pl  # noqa: E402

V0_JSON, V0_MD = "partj-lift-v0.json", "partj-lift-v0.md"
SERIES = ("composition_vs_max_statement", "composition_vs_mean_statement", "composition_vs_spread")
REVIEW_SRC = "review session's own run, another seed, indicative (read-partj-lift-record-2026-11-02.md)"
NORMAL_SRC = "review session's normal approximation 13.46 +/- 1.96 x 13.71 / sqrt(89), indicative"


# ---- resamples and intervals ---------------------------------------------------------------------------------------

def resample_indices(n, resamples, seed):
    """The v0 recipe: one generator seeded with the seed, `resamples` rows of n draws."""
    return np.random.default_rng(seed).integers(0, n, size=(resamples, n))


def spearman_values(x, y, idx):
    return [pl.spearman([x[i] for i in row], [y[i] for i in row]) for row in np.asarray(idx).tolist()]


def percentile_ci(values):
    finite = [v for v in values if not math.isnan(v)]
    lo, hi = np.percentile(finite, [2.5, 97.5])
    return float(lo), float(hi), len(values) - len(finite)


def paired_differences(a, b):
    return [float("nan") if math.isnan(p) or math.isnan(q) else p - q for p, q in zip(a, b)]


def paired_difference_ci(x, y1, y2, resamples, seed):
    idx = resample_indices(len(x), resamples, seed)
    diff = paired_differences(spearman_values(x, y1, idx), spearman_values(x, y2, idx))
    lo, hi, degenerate = percentile_ci(diff)
    return pl.spearman(x, y1) - pl.spearman(x, y2), lo, hi, degenerate


def mean_by_resample(values, idx, mask=None):
    """Mean of the resampled values per resample; with a mask, of the resampled rows the mask selects (nan if none)."""
    idx = np.asarray(idx)
    drawn = np.asarray(values, dtype=float)[idx]
    if mask is None:
        return drawn.mean(axis=1)
    keep = np.asarray(mask, dtype=bool)[idx]
    counts = keep.sum(axis=1)
    out = np.full(len(idx), np.nan)
    ok = counts > 0
    out[ok] = (drawn * keep).sum(axis=1)[ok] / counts[ok]
    return out


def normal_ci(values):
    s = pl.summarize(values)
    half = 1.96 * s["sd"] / math.sqrt(s["n"])
    return s["mean"] - half, s["mean"] + half


def high_composition_counts(rows, bars):
    """Pass-1 counts among rows whose composition is above the composition bar, by writer label and pooled."""
    def block(sub):
        return {"n": len(sub),
                "lines_more_than_10_apart": sum(max(r["p1"]) - min(r["p1"]) > bars["spread_bar"] for r in sub),
                "every_line_at_or_under_60": sum(max(r["p1"]) <= bars["statement_bar"] for r in sub),
                "within_10_and_every_line_at_or_under_60": sum(
                    max(r["p1"]) - min(r["p1"]) <= bars["spread_bar"] and max(r["p1"]) <= bars["statement_bar"] for r in sub)}
    above = [r for r in rows if r["c1"] > bars["composition_bar"]]
    writers = sorted({r["writer"] for r in above}, key=lambda w: list(pl.WRITER_LABELS).index(w) if w in pl.WRITER_LABELS else 99)
    out = {pl.WRITER_LABELS.get(w, w): block([r for r in above if r["writer"] == w]) for w in writers}
    out["pooled"] = block(above)
    return out


# ---- the section ---------------------------------------------------------------------------------------------------

def _row(name, recomputed, printed, decimals, source, like_for_like=True):
    row = pl.compare_to_note(name, recomputed, printed, decimals, source)
    row["like_for_like"] = like_for_like
    return row


def build_section(rater_dir, record_dir):
    root, rec_dir = Path(rater_dir), Path(record_dir)
    v0_json, v0_md = (rec_dir / V0_JSON).read_bytes(), (rec_dir / V0_MD).read_bytes()
    v0 = json.loads(v0_json)
    if "v0_1" in v0:
        raise SystemExit("the record already carries a v0.1 section; refusing to append another")
    script = Path(pl.__file__).resolve()
    if v0["script"]["sha256"] != pl.sha256(script):
        raise SystemExit("the v0 script is not the one that wrote this record (hash differs); refusing")
    for name, want in v0["inputs"]["sha256"].items():
        if pl.sha256(root / name) != want:
            raise SystemExit(f"{name} has changed since the v0 record; refusing")

    bars = {k: v for k, v in v0["bars"].items()}
    key = json.loads((root / "key-b3.json").read_text())
    rows = pl.candidate_triples(key,
                                pl.load_scores(root / "ratings-b3-statements-p1.jsonl", "statement_id"),
                                pl.load_scores(root / "ratings-b3-statements-p2.jsonl", "statement_id"),
                                pl.load_scores(root / "ratings-b3-triples-p1.jsonl", "triple_id"),
                                pl.load_scores(root / "ratings-b3-triples-p2.jsonl", "triple_id"))
    if len(rows) != v0["counts"]["candidates"]:
        raise SystemExit("the candidate count differs from the v0 record; refusing")
    first = v0["spearman"]["pass1"][SERIES[0]]
    n, resamples, seed = len(rows), first["resamples"], first["seed"]
    idx = resample_indices(n, resamples, seed)

    series = {}
    for p in (1, 2):
        comp = [r[f"c{p}"] for r in rows]
        scores = [r[f"p{p}"] for r in rows]
        series[p] = {"comp": comp, SERIES[0]: [max(s) for s in scores], SERIES[1]: [sum(s) / 3 for s in scores],
                     SERIES[2]: [max(s) - min(s) for s in scores]}

    # the record's own resamples: all six v0 Spearman rows must come out exactly as recorded
    values, unequal = {}, []
    for p in (1, 2):
        for name in SERIES:
            vals = spearman_values(series[p]["comp"], series[p][name], idx)
            values[(p, name)] = vals
            lo, hi, degenerate = percentile_ci(vals)
            old = v0["spearman"][f"pass{p}"][name]
            if [lo, hi] != old["ci95"] or degenerate != old["degenerate_resamples"] or \
                    pl.spearman(series[p]["comp"], series[p][name]) != old["rho"]:
                unequal.append(f"pass{p} {name}")
    if unequal:
        raise SystemExit("the shared resampling does not reproduce the v0 record's intervals (" + "; ".join(unequal) + "); refusing")

    paired = {}
    for p in (1, 2):
        a, b = values[(p, SERIES[0])], values[(p, SERIES[1])]
        lo, hi, degenerate = percentile_ci(paired_differences(a, b))
        ra, rb = pl.spearman(series[p]["comp"], series[p][SERIES[0]]), pl.spearman(series[p]["comp"], series[p][SERIES[1]])
        paired[f"pass{p}"] = {"estimate": ra - rb, "ci95": [lo, hi], "n": n, "resamples": resamples, "seed": seed,
                              "degenerate_resamples": degenerate,
                              "rho_composition_vs_max_statement": ra, "rho_composition_vs_mean_statement": rb}

    need = pl.min_lift_needed(bars)
    lifts = [pl.lift(r["p1"], r["c1"]) for r in rows]
    writers = sorted({r["writer"] for r in rows}, key=lambda w: list(pl.WRITER_LABELS).index(w) if w in pl.WRITER_LABELS else 99)

    def mean_row(mask):
        sub = [l for l, m in zip(lifts, mask) if m] if mask is not None else lifts
        boot = mean_by_resample(lifts, idx, mask).tolist()
        lo, hi, degenerate = percentile_ci(boot)
        nlo, nhi = normal_ci(sub)
        return {"mean": float(np.mean(sub)), "n": len(sub), "bootstrap_ci95": [lo, hi], "normal_ci95": [nlo, nhi],
                "degenerate_resamples": degenerate, "ci_includes_min_lift_needed": lo <= need <= hi}

    means = {"min_lift_needed": need, "resamples": resamples, "seed": seed, "overall": mean_row(None),
             "by_writer": {pl.WRITER_LABELS.get(w, w): mean_row([r["writer"] == w for r in rows]) for w in writers}}
    by_writer_counts = high_composition_counts(rows, bars)
    counts = {"composition_above": bars["composition_bar"], "pass": "pass 1 (the bars' pass)",
              "pooled": by_writer_counts.pop("pooled"), "by_writer": by_writer_counts}

    pd1, pd2, ov, pc = paired["pass1"], paired["pass2"], means["overall"], counts["pooled"]
    checks = [
        _row("paired_difference_pass1_estimate", pd1["estimate"], 0.172, 3, REVIEW_SRC),
        _row("paired_difference_pass1_ci_lo", pd1["ci95"][0], 0.044, 3, REVIEW_SRC),
        _row("paired_difference_pass1_ci_hi", pd1["ci95"][1], 0.308, 3, REVIEW_SRC),
        _row("paired_difference_pass2_estimate", pd2["estimate"], 0.187, 3, REVIEW_SRC),
        _row("paired_difference_pass2_ci_lo", pd2["ci95"][0], 0.069, 3, REVIEW_SRC),
        _row("paired_difference_pass2_ci_hi", pd2["ci95"][1], 0.325, 3, REVIEW_SRC),
        _row("lift_pass1_overall_mean_normal_ci_lo", ov["normal_ci95"][0], 10.6, 1, NORMAL_SRC),
        _row("lift_pass1_overall_mean_normal_ci_hi", ov["normal_ci95"][1], 16.3, 1, NORMAL_SRC),
        _row("lift_pass1_overall_mean_bootstrap_ci_lo", ov["bootstrap_ci95"][0], 10.6, 1, NORMAL_SRC + "; against this record's bootstrap", False),
        _row("lift_pass1_overall_mean_bootstrap_ci_hi", ov["bootstrap_ci95"][1], 16.3, 1, NORMAL_SRC + "; against this record's bootstrap", False),
        _row("composition_above_bar_pass1_n", pc["n"], 19, 0, REVIEW_SRC),
        _row("composition_above_bar_pass1_lines_more_than_10_apart", pc["lines_more_than_10_apart"], 18, 0, REVIEW_SRC),
        _row("composition_above_bar_pass1_every_line_at_or_under_60", pc["every_line_at_or_under_60"], 11, 0, REVIEW_SRC),
    ]
    off = [c["name"] for c in checks if c["like_for_like"] and not c["matches_printed_precision"]]
    agreement = {"all_match": not off, "differing": off,
                 "summary": ("Every like-for-like value of the review session's reproduces at its printed precision." if not off else
                             f"{len(off)} of {sum(c['like_for_like'] for c in checks)} like-for-like values differ at the printed "
                             "precision (listed under differing). The review session's run used another seed and called its "
                             "values indicative; both values are kept.")}
    this = Path(__file__).resolve()
    return {
        "section": "v0.1, appended by dated note 2 of brief 34; nothing above it changes",
        "script": {"name": this.name, "sha256": pl.sha256(this)},
        "built_on": {"v0_script": {"name": script.name, "sha256": v0["script"]["sha256"]},
                     "v0_json_sha256_before_append": hashlib.sha256(v0_json).hexdigest(),
                     "v0_md_sha256_before_append": hashlib.sha256(v0_md).hexdigest()},
        "resamples": {"n": resamples, "seed": seed},
        "own_resamples_check": {"reproduced_rows": 2 * len(SERIES), "all_equal": True,
                                "what": "the rho, 95% interval and degenerate count of all six v0 Spearman rows, exactly"},
        "paired_difference": paired,
        "lift_mean_intervals_pass1": means,
        "composition_above_bar_pass1": counts,
        "check_values": checks,
        "agreement": agreement,
        "method": {
            "paired_difference": "rho(composition, loudest) - rho(composition, mean), per resample, then the 2.5 and 97.5 "
                                 "percentiles; a resample degenerate on either side is dropped and counted",
            "lift_means": "per resample, the mean of the resampled triples' pass-1 lifts; by writer, of the resampled triples "
                          "of that writer (their number varies; not a stratified bootstrap); normal: mean +/- 1.96 sd/sqrt(n)",
            "counts": "pass 1; composition above the composition bar; lines more than 10 apart = max - min above the "
                      "spread bar; every line at or under the statement bar = max at or under it",
            "like_for_like": "the review session's bootstrap values came from another seed and its interval for (b) is a "
                             "normal approximation; rows marked false are shown for the difference only and are not "
                             "counted in the agreement",
        },
    }


def render_section_md(sec):
    b, ag, pdf, mn, cn = sec["built_on"], sec["agreement"], sec["paired_difference"], sec["lift_mean_intervals_pass1"], sec["composition_above_bar_pass1"]
    L = ["# v0.1 section (appended by dated note 2 of brief 34; nothing above this line changes)", "",
         f"$0, no request sent. Script `{sec['script']['name']}` `{sec['script']['sha256']}`, built on the v0 script "
         f"`{b['v0_script']['name']}` `{b['v0_script']['sha256']}` (verified to be the one that wrote the v0 record). The v0 files "
         f"before this append: json `{b['v0_json_sha256_before_append']}`, md `{b['v0_md_sha256_before_append']}`. Numbers and "
         "fixed labels only: no ids, no item text, no rater `reason`.", "",
         f"Resamples: {sec['resamples']['n']}, seed {sec['resamples']['seed']}, the v0 record's own. Check: "
         f"{sec['own_resamples_check']['reproduced_rows']} of the v0 Spearman rows reproduced exactly "
         f"({sec['own_resamples_check']['all_equal']}).", "",
         "## Agreement with the review session's indicative values", "", ag["summary"], "",
         "| value | review session | recomputed | difference | match at printed precision | like for like |", "|---|---|---|---|---|---|"]
    for k in sec["check_values"]:
        d = k["decimals"]
        shown = (str(round(k["recomputed"])), str(round(k["difference"]))) if d == 0 else (pl._f(k["recomputed"], d + 1), pl._f(k["difference"], d + 2))
        L.append(f"| {k['name']} | {k['review_note']} | {shown[0]} | {shown[1]} | "
                 f"{'yes' if k['matches_printed_precision'] else 'NO'} | {'yes' if k['like_for_like'] else 'no'} |")
    L += ["", "## Paired difference, rho(composition, loudest statement) minus rho(composition, mean statement)", "",
          "| pass | rho (loudest) | rho (mean) | difference | 95% interval | n | resamples | degenerate |", "|---|---|---|---|---|---|---|---|"]
    for p, r in pdf.items():
        L.append(f"| {p} | {pl._f(r['rho_composition_vs_max_statement'], 3)} | {pl._f(r['rho_composition_vs_mean_statement'], 3)} | "
                 f"{pl._f(r['estimate'], 3)} | [{pl._f(r['ci95'][0], 3)}, {pl._f(r['ci95'][1], 3)}] | {r['n']} | {r['resamples']} | {r['degenerate_resamples']} |")
    L += ["", f"## Lift means, pass 1 (minimum lift needed {mn['min_lift_needed']})", "",
          "| group | n | mean | bootstrap 95% | normal 95% | bootstrap interval includes the minimum |", "|---|---|---|---|---|---|"]
    for g, r in [("all", mn["overall"])] + list(mn["by_writer"].items()):
        L.append(f"| {g} | {r['n']} | {pl._f(r['mean'])} | [{pl._f(r['bootstrap_ci95'][0])}, {pl._f(r['bootstrap_ci95'][1])}] | "
                 f"[{pl._f(r['normal_ci95'][0])}, {pl._f(r['normal_ci95'][1])}] | {'yes' if r['ci_includes_min_lift_needed'] else 'no'} |")
    L += ["", f"## Candidate triples with composition above {cn['composition_above']}, {cn['pass']}", "",
          "| group | n | lines more than 10 apart | every line at or under 60 | within 10 and every line at or under 60 |", "|---|---|---|---|---|"]
    for g, r in list(cn["by_writer"].items()) + [("pooled", cn["pooled"])]:
        L.append(f"| {g} | {r['n']} | {r['lines_more_than_10_apart']} | {r['every_line_at_or_under_60']} | {r['within_10_and_every_line_at_or_under_60']} |")
    L += ["", "## Method (v0.1)", ""]
    L += [f"- {k}: {v}" for k, v in sec["method"].items()]
    return "\n".join(L) + "\n"


def write_appended(record_dir, section):
    """Validate, then extend the v0 files: the section goes in as the last key of the json and the last section of
    the md; both are composed before either is written, and the v0 bytes must remain a prefix of the new ones."""
    rec_dir = Path(record_dir)
    pl.assert_no_text(section, "v0_1")
    old_json, old_md = (rec_dir / V0_JSON).read_text(), (rec_dir / V0_MD).read_text()
    old = json.loads(old_json)
    if "v0_1" in old:
        raise SystemExit("the record already carries a v0.1 section; refusing to append another")
    new_json = json.dumps({**old, "v0_1": section}, indent=1, allow_nan=False) + "\n"
    if not new_json.startswith(old_json.rstrip("\n")[:-1].rstrip("\n") + ",\n"):
        raise SystemExit("appending would change bytes above the section; refusing")
    new_md = old_md + "\n" + render_section_md(section)
    (rec_dir / V0_JSON).write_text(new_json)
    (rec_dir / V0_MD).write_text(new_md)
    return rec_dir / V0_JSON, rec_dir / V0_MD


def append_v01(rater_dir, record_dir):
    section = build_section(rater_dir, record_dir)
    write_appended(record_dir, section)
    return section


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rater-dir", default="../stage3/b3/rater")
    ap.add_argument("--record-dir", default="../stage3/b3/rater")
    args = ap.parse_args(argv)
    sec = append_v01(args.rater_dir, args.record_dir)
    p1, p2, ov, pc = sec["paired_difference"]["pass1"], sec["paired_difference"]["pass2"], sec["lift_mean_intervals_pass1"]["overall"], sec["composition_above_bar_pass1"]["pooled"]
    print(f"own resamples reproduced {sec['own_resamples_check']['reproduced_rows']} v0 rows ({sec['resamples']['n']} resamples, seed {sec['resamples']['seed']})")
    print(f"paired difference pass 1 {p1['estimate']:.3f} [{p1['ci95'][0]:.3f}, {p1['ci95'][1]:.3f}]; pass 2 {p2['estimate']:.3f} [{p2['ci95'][0]:.3f}, {p2['ci95'][1]:.3f}]")
    print(f"pass-1 mean lift {ov['mean']:.2f}: bootstrap [{ov['bootstrap_ci95'][0]:.2f}, {ov['bootstrap_ci95'][1]:.2f}], normal [{ov['normal_ci95'][0]:.2f}, {ov['normal_ci95'][1]:.2f}]")
    for g, r in sec["lift_mean_intervals_pass1"]["by_writer"].items():
        print(f"  {g}: {r['mean']:.2f} bootstrap [{r['bootstrap_ci95'][0]:.2f}, {r['bootstrap_ci95'][1]:.2f}]")
    print(f"composition above {sec['composition_above_bar_pass1']['composition_above']} (pass 1): n {pc['n']}, lines more than 10 apart {pc['lines_more_than_10_apart']}, every line at or under 60 {pc['every_line_at_or_under_60']}, both bars within {pc['within_10_and_every_line_at_or_under_60']}")
    for g, r in sec["composition_above_bar_pass1"]["by_writer"].items():
        print(f"  {g}: n {r['n']}, apart {r['lines_more_than_10_apart']}, <=60 {r['every_line_at_or_under_60']}")
    print(f"agreement with the review session's like-for-like values: {sec['agreement']['all_match']} {sec['agreement']['differing']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
