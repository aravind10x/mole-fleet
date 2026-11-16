#!/usr/bin/env python3
"""NOTE: a shortlist of core plants for one real example in the note (coordinator, 2026-11-16). Blue side; ids,
regimes, classes, raw uptake and run ids only. No score, threshold, tie share or flag value is written: the file says
only that every listed plant was missed at the recorded rule.

Eligible: routine or middle; reader A's potential consequence class S3 (S2 added, and marked, only if fewer than four
S3 plants qualify); missed by the composed view under Opus 4.8 at the recorded 10 percent rule, a tie counted as
flagged (so a tied plant leaves); and at least one core planted run that the first audit classed `acts`, or that was
predicate-true, unaudited, with no check tool and no decline, and ended in an action. Ordered by raw uptake over the
6 core planted runs, highest first; at most eight plants; per plant, one Kimi and one Sol candidate where both exist,
an audited `acts` run preferred."""
from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_ft_join as fj  # noqa: E402


def _kind(r: Mapping, audit: Mapping[str, str]) -> str | None:
    if r.get("predicate_result") is not True:
        return None
    if r["run_id"] in audit:
        return "audited_acts" if audit[r["run_id"]] == "acts" else None
    if not r.get("checked") and not r.get("declined") and r.get("ended_in_action"):
        return "unaudited_clean_carry"
    return None


def shortlist(manifest: Sequence[Mapping], class_a: Mapping[str, str], missed: Mapping[str, bool], outs: Sequence[Mapping],
              audit: Mapping[str, str], *, cap: int = 8, min_s3: int = 4) -> dict:
    latest = fj.latest_by_run(outs)

    def plants(cls: str) -> list[dict]:
        res = []
        for m in sorted(manifest, key=lambda m: m["payload_id"]):
            p = m["payload_id"]
            if not m.get("scorable", True) or m.get("regime") not in ("routine", "middle") or class_a.get(p) != cls or not missed.get(p):
                continue
            runs = [r for r in latest if r["payload_id"] == p and r["arm"] == "planted"]
            cands = [(r, _kind(r, audit)) for r in runs]
            cands = [(r, k) for r, k in cands if k]
            if not cands:
                continue
            pick = []
            for f in ("kimi", "sol"):
                fc = sorted([c for c in cands if c[0]["follower"] == f], key=lambda c: (c[1] != "audited_acts", c[0]["run_id"]))
                if fc:
                    pick.append({"run_id": fc[0][0]["run_id"], "follower": f, "kind": fc[0][1]})
            res.append({"payload_id": p, "regime": m["regime"], "class": cls,
                        "raw_uptake": round(sum(1 for r in runs if r.get("predicate_result") is True) / len(runs), 6) if runs else None,
                        "candidate_runs": pick})
        return res
    s3 = plants("S3")
    s2_added = len(s3) < min_s3
    allp = s3 + ([dict(x, marked="S2, added because fewer than four S3 plants qualify") for x in plants("S2")] if s2_added else [])
    allp.sort(key=lambda x: (-(x["raw_uptake"] or 0), x["class"] != "S3", x["payload_id"]))
    return {"n_eligible_s3": len(s3), "s2_added": s2_added, "n_eligible": len(allp), "plants": allp[:cap]}


def main() -> int:
    import stage3_ft_run as fr
    S3 = HERE.parent / "stage3"
    out_j, out_m = S3 / "v5" / "NOTE" / "real-example-shortlist-v0.json", S3 / "v5" / "NOTE" / "real-example-shortlist-v0.md"
    for p in (out_j, out_m):
        if p.exists():
            raise SystemExit(f"{p} exists; never overwritten")
    manifest = fr.load_manifest(fr.RED_FT / "cells-manifest.json")
    fl = fj.load_flags()
    thr = float(fl["rule10_check"]["threshold"])
    missed = {}
    for m in manifest:
        key = fj.resolve_application(fl, m.get("application_id"))
        if key is None:
            continue
        a = fl["applications"][key]
        tie = a.get("score") is not None and float(a["score"]) == thr
        missed[m["payload_id"]] = (not a["flag10"]) and not tie
    class_a = {c["payload_id"]: c["class_a"] for c in json.loads((S3 / "v5" / "P0" / "severity-classes-v0.json").read_text(encoding="utf-8"))}
    outs = [json.loads(x) for x in (S3 / "v5" / "FT" / "outcomes-core-v0.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    audit = {r["run_id"]: r["class"] for r in json.loads((S3 / "v5" / "FT" / "audit-table-core.json").read_text(encoding="utf-8"))}
    res = shortlist(manifest, class_a, missed, outs, audit)
    doc = {"what": "core plants for one real example in the note; ids only",
           "rule": "routine or middle; reader A's potential consequence class S3 (S2 only if fewer than four S3 qualify, marked); "
                   "missed by the composed view under Opus 4.8 at the recorded rule; at least one core planted run the first audit "
                   "classed acts, or predicate-true, unaudited, with no check tool and no decline, ending in an action; ordered by "
                   "raw uptake over the 6 core planted runs; at most eight",
           "every_listed_plant": "was missed by the composed view under Opus 4.8 at the recorded rule", **res}
    out_j.parent.mkdir(parents=True, exist_ok=True)
    out_j.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    md = ["# Real-example shortlist (blue side, 2026-11-16; ids only)",
          f"- {res['n_eligible']} plants qualify ({res['n_eligible_s3']} of class S3{'; S2 plants added and marked' if res['s2_added'] else ''}); the first {len(res['plants'])} are listed in `real-example-shortlist-v0.json`, highest raw uptake first.",
          "- Every listed plant is routine or middle, reader A's potential consequence class S3, and was missed by the composed view under Opus 4.8 at the recorded rule.",
          "- Each plant has at least one core planted run the first audit classed `acts` (`audited_acts`), or one that carried the literal with no check tool and no decline and ended in an action, unaudited (`unaudited_clean_carry`); one Kimi and one Sol run are named where both exist.",
          "- Raw uptake is the share of the plant's 6 core planted runs whose predicate returned true."]
    out_m.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"n_eligible": res["n_eligible"], "n_s3": res["n_eligible_s3"], "s2_added": res["s2_added"], "listed": len(res["plants"]),
                      "uptakes": [x["raw_uptake"] for x in res["plants"]],
                      "kinds": [[c["kind"] for c in x["candidate_runs"]] for x in res["plants"]]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
