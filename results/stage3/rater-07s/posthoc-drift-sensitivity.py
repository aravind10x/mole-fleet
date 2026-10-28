#!/usr/bin/env python3
"""Brief 07s part J, post hoc (labelled): the C3 contrast with the placeholders' 07k maxima raised by the
07s-minus-07k drift measured on the 60 re-drawn statements (uniform, and per 07k band); and the honest edits'
shares in pilot-gates.md B.3's R-C classes. Run from work/checks:
    ../mole-fork/.venv/bin/python -I ../stage3/rater-07s/posthoc-drift-sensitivity.py
"""
import collections
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import stage3_rater_join_07s as rj  # noqa: E402

D = Path(__file__).resolve().parent.parent / "t1k-rater"
L = lambda n: json.loads((D / n).read_text(encoding="utf-8"))
r2, k2, rt, kt, r7, k7 = (L(n) for n in ("ratings-2.json", "key-2.json", "ratings-triples.json", "key-triples.json", "ratings.json", "key.json"))
s2 = r2["statements"]
pairs = [(s2[s]["pass1"]["score"], r7["statements"][k2["statements"][s]["t1k_statement_id"]]["pass1"]["score"])
         for s in s2 if k2["statements"][s]["source"] == "t1k_redraw"]
by_band: dict[int, list[float]] = {}
for n, o in pairs:
    by_band.setdefault(rj.band(o), []).append(n - o)
drift = {b: statistics.fmean(v) for b, v in by_band.items()}
uni = statistics.fmean(n - o for n, o in pairs)
pl: dict[str, list[float]] = {}
for sid, ks in k7["statements"].items():
    if ks["file"].endswith("v3.json") and ks["arm"] == "routine_redraw":
        continue
    pl.setdefault(ks["payload_id"], []).append(r7["statements"][sid]["pass1"]["score"])
honest_by_row = {k2["statements"][s]["row_index"]: s for s in s2 if k2["statements"][s]["source"] == "honest"}
t = rt["triples"]
rng = random.Random(rj.BOOT_SEED + 1)
sa = [t[tid]["pass1"]["score"] - max(s2[honest_by_row[i]]["pass1"]["score"] for i in kk["row_indices"])
      for tid, kk in kt["triples"].items()
      if kk["source"] == "honest" and "same_author" in kk["null"] and all(i in honest_by_row for i in kk["row_indices"])]
out = {"drift_uniform": round(uni, 2), "drift_per_07k_band": {rj.BAND_LABELS[b]: round(v, 2) for b, v in sorted(drift.items())},
       "boot_seed": rj.BOOT_SEED + 1, "contrast_minus_same_author": {}}
for name, corr in (("uniform", lambda m: uni), ("per_band", lambda m: drift[rj.band(m)])):
    for g in rj.TEXT_GROUPS:
        dg = []
        for tid, kk in kt["triples"].items():
            if kk["source"] == "planted" and rj.text_group(kk["plantings"]) == g:
                pid = next(p["id"] for p in kk["plantings"] if p["id"] in pl)
                m = max(pl[pid])
                dg.append(t[tid]["pass1"]["score"] - min(100, m + corr(m)))
        out["contrast_minus_same_author"][f"{name} | {g}"] = {
            "mean_d": round(statistics.fmean(dg), 2), "diff": round(rj.mean_diff(dg, sa), 2),
            "ci": rj.boot_two(rj.mean_diff, [[x] for x in dg], [[x] for x in sa], rng)}
cls = lambda x: "under 40" if x < 40 else "40-69" if x < 70 else "70-79" if x < 80 else "80+"
for p in ("pass1", "pass2"):
    h = [s2[s][p]["score"] for s in s2 if k2["statements"][s]["source"] == "honest"]
    c = collections.Counter(cls(x) for x in h)
    out[f"rc_classes_honest_{p}"] = {k: round(c[k] / len(h), 3) for k in ("under 40", "40-69", "70-79", "80+")}
print(json.dumps(out, indent=1))
