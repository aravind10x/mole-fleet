#!/usr/bin/env python3
"""Brief 14 (B4-R): the world repair's $0 instruments (pre-registration `work/stage3/b4r/plan.md`).

    count   R0.3: the number of cross-document maintenance variants from the measured yield model
            (`stage3_write_yield.measure` on prefix_rw_v2c, every day pooled), the expected share
            of account-windows with a completed cross-document write (statistic A), per entity
            class, and the day-1 expectations the stop reads; v1 day 1's calibration beside.

Model (written in plan R0.3 before it was run). For an account of team T, over a two-day window of
S = 2 days x 2 sessions x presence sessions, each session feeds on average f agenda items drawn
from the team pool of n_T tasks, so a given variant is fed with probability f / n_T per session;
an update-both variant completes as a two-document write with probability c = y^2 (y = the share
of fed single-document write variants that produced a non-empty write; plan R0.3 until day 1
measures c). With u_T update variants in T's pool the expected completed cross-document writes
in the window are lambda_T = S f c u_T / n_T, and an account has at least one with probability
1 - exp(-lambda_T); A_cross is the roster-weighted mean, and A combines it with the unrepaired
world's single-document rate a0 = 0.020 (B0's Z5) as 1 - (1 - A_cross)(1 - a0). Per entity
class, u_T counts only the rows whose shared line carries the class (`stage3_b4r_design`).
Check variants never complete as a two-document write and enter only n_T.

LABEL-BLIND: honest corpora only; no payload, plant, persona or transcript content is read
(transcripts are read only for the agenda lines the yield model counts).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_b4r_design as dz  # noqa: E402
import stage3_rung1_class as rc  # noqa: E402
import stage3_rung1_density as r1  # noqa: E402
import stage3_write_yield as wy  # noqa: E402

VERSION = "b4r/v1"
A0_UNREPAIRED = 0.020           # B0 Z5, prefix_rw_v2c, statistic A two-day pooled (b0-results.md)
BAND = (0.10, 0.25)
DAYS_PER_WINDOW = 2
SESSIONS_PER_DAY = wy.SESSIONS_PER_ACCOUNT_DAY
NOMINAL = wy.NOMINAL_ROSTER * SESSIONS_PER_DAY


def write_teams() -> dict[str, dict[str, int]]:
    return {d["path"]: dict(d["write_teams"]) for d in rc.CLASS}


def pools(shipped: Mapping[str, Any], alloc: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """n_T: the team's shipped tasks + its v6 class tasks + its cross-document variants (bank v7)."""
    cls = wy.class_counts_per_team(rc.CLASS)
    cross = Counter(v["team"] for v in alloc)
    return {t: len(r1.team_tasks(e)) + cls.get(t, 0) + cross.get(t, 0) for t, e in shipped.items()}


def expected(alloc: Sequence[Mapping[str, Any]], team_sizes: Mapping[str, int], n: Mapping[str, int], *,
             f: float, c: float, presence: float, a0: float = A0_UNREPAIRED) -> dict[str, Any]:
    """Statistic A's expectation under the model (module docstring): overall and per entity class,
    per team, and the expected fed and completed update variants per simulated day."""
    S = DAYS_PER_WINDOW * SESSIONS_PER_DAY * presence
    roster = sum(team_sizes.values())

    def share(sel) -> tuple[float, dict[str, float]]:
        lam = {t: S * f * c * sum(1 for v in alloc if v["team"] == t and v["kind"] == "update" and sel(v)) / n[t]
               for t in team_sizes}
        return sum(team_sizes[t] / roster * (1 - math.exp(-lam[t])) for t in team_sizes), lam

    a_cross, lam = share(lambda v: True)
    per_class = {k: share(lambda v, k=k: k in v["classes"])[0] for k in dz.ENTITY_CLASSES}
    fed_day = sum(team_sizes[t] * SESSIONS_PER_DAY * presence * f
                  * sum(1 for v in alloc if v["team"] == t and v["kind"] == "update") / n[t] for t in team_sizes)
    return {"S": S, "f": f, "c": c, "presence": presence,
            "A_cross": a_cross, "A": 1 - (1 - a_cross) * (1 - a0),
            "A_by_class_cross": per_class,
            "lambda_by_team": lam,
            "update_fed_per_day": fed_day, "update_completed_per_day": fed_day * c}


def calibration_v2c(transcripts: Path, audit: Path) -> dict[str, Any]:
    """f, y, presence pooled over every day of an honest corpus (`stage3_write_yield.measure`)."""
    tr, au = wy._load_jsonl(str(transcripts)), wy._load_jsonl(str(audit))
    days = sorted({str(r.get("ts") or "")[:10] for r in au if r.get("ts")})
    per = {d: wy.measure(tr, au, d) for d in days}
    sess = sum(m["sessions"] for m in per.values())
    fed = sum(m["items_fed_total"] for m in per.values())
    wf = sum(m["write_variants_fed"] for m in per.values())
    wn = sum(m["write_variants_nonempty"] for m in per.values())
    return {"days": days, "sessions": sess, "f": fed / sess, "y": wn / wf, "presence": sess / (NOMINAL * len(days)),
            "per_day": {d: {k: m[k] for k in ("sessions", "items_fed_per_session", "write_variants_fed",
                                              "write_variants_nonempty", "write_yield", "class_writes")}
                        for d, m in per.items()}}


def mode_count(ns: argparse.Namespace) -> int:
    import yaml
    tmpl = yaml.safe_load(open(ns.template, encoding="utf-8"))
    roster = r1.roster_from_template(tmpl)
    team_sizes = dict(Counter(t for _, t in roster))
    shipped = yaml.safe_load(open(ns.bank_v2, encoding="utf-8"))
    alloc = dz.allocation(write_teams())
    n = pools(shipped, alloc)
    cal = calibration_v2c(Path(ns.transcripts), Path(ns.audit))
    v1 = json.loads(Path(ns.v1_yield).read_text())["calibration"]
    runs = {}
    for name, f, y, pres in (("v2c", cal["f"], cal["y"], cal["presence"]),
                             ("v1_day1", v1["f"], v1["y"], v1["presence"])):
        for cname, c in (("y_squared", y * y), ("c_0.5", 0.5), ("c_0.8", 0.8)):
            runs[f"{name}:{cname}"] = expected(alloc, team_sizes, n, f=f, c=c, presence=pres)
    prim = runs["v2c:y_squared"]
    out = {"version": VERSION, "mode": "count", "script": "work/checks/stage3_b4r.py",
           "inputs": {"transcripts": ns.transcripts, "audit": ns.audit, "v1_yield": ns.v1_yield,
                      "bank_v2": ns.bank_v2, "template": ns.template},
           "design": {"rows": [{k: (list(v) if isinstance(v, tuple) else v) for k, v in r.items()} for r in dz.SHARED],
                      "totals": dz.totals(alloc), "per_team_cap": dz.PER_TEAM_CAP},
           "team_sizes": team_sizes, "pools_v7": n, "pool_total_v7": sum(n.values()),
           "cross_share_of_pool": len(alloc) / sum(n.values()),
           "update_share_of_pool": sum(1 for v in alloc if v["kind"] == "update") / sum(n.values()),
           "calibration_v2c": cal, "calibration_v1_day1": {k: v1[k] for k in ("f", "y", "presence")},
           "a0_unrepaired": A0_UNREPAIRED, "band": list(BAND),
           "primary": "v2c:y_squared", "runs": runs,
           "in_band_primary": BAND[0] <= prim["A"] <= BAND[1]}
    Path(ns.out_json).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"primary_A": round(prim["A"], 4),
                      "by_class": {k: round(v, 4) for k, v in prim["A_by_class_cross"].items()},
                      "totals": out["design"]["totals"], "cross_share_of_pool": round(out["cross_share_of_pool"], 4),
                      "update_fed_per_day": round(prim["update_fed_per_day"], 2),
                      "sensitivity_A": {k: round(v["A"], 4) for k, v in runs.items()}}, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("count")
    c.add_argument("--transcripts", required=True)
    c.add_argument("--audit", required=True)
    c.add_argument("--v1-yield", required=True)
    c.add_argument("--bank-v2", required=True)
    c.add_argument("--template", required=True)
    c.add_argument("--out-json", required=True)
    ns = ap.parse_args(argv)
    return {"count": mode_count}[ns.mode](ns)


if __name__ == "__main__":
    raise SystemExit(main())
