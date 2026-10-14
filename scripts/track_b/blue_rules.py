#!/usr/bin/env python3
"""Blue's mechanical windows and thresholds (TRACK-B part 2 draft, section 2, Rule WT) from a
fork-mode B1 haystack JSON (`haystack.py --fork-corpus ...`).

- **Rule WT (window and threshold, jointly).** For each generator G with a window (G1,
  G1-tg = G1 on tickets and groups, G2-strict, G2-loose, G3, G4-60, G4-180) and each cell
  (w, t), w in {1, 2, 3} (only windows the corpus holds; trailing, truncated at day 1),
  t in {1, 2, 3, 4, 6, 8} for G1 / G1-tg / G3 / G4 (groups whose strongest pairwise link
  is below t are dropped) and t = 1 only for G2: the cell is **admissible** if
  V_G(w, t) <= B/2 = 0.05 at B = 0.10 **and** G still emits at least one group per day on
  average. `w_G` = the largest w with an admissible cell; `t_G` = the smallest admissible
  t at `w_G`. With no admissible cell, (w_G, t_G) = (1, 1) and G is flagged "over budget
  at every window". Rule WT does not apply to G5 (no window; its V is reported) or G6
  (its honest amplification is reported).
- **Primary generator.** Among G2-strict, G3 and G1-tg (in that tie order) with an
  admissible cell, the smallest V at (w_G, t_G); ties list every tied generator and the
  earliest in the order is primary. If none has an admissible cell, the primary is
  G2-strict at (1, 1), the pre-stated default (printed "default").
- The prefix's pair density by artefact type is printed beside the rules.

V comparisons with the bound are exact (review pairs / account-days as fractions); groups
per day = emitted groups / evaluated days, compared exactly as a fraction.

Usage (no LLM calls; inputs are this project's own JSON):

    work/mole-fork/.venv/bin/python -I work/checks/blue_rules.py \\
        --haystack-json /abs/work/stage2/b1-haystack.prefix_v1.json \\
        --out /abs/work/stage2/blue-rules.prefix_v1.json \\
        --md /abs/work/stage2/blue-rules.prefix_v1.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Sequence

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent

B = Fraction(1, 10)
BOUND = B / 2                                    # Rule WT bound, B/2 = 0.05
MIN_GROUPS_PER_DAY = Fraction(1)                 # Rule WT guard against emptying G
RULE_W_WINDOWS = (1, 2, 3)
T_LEVELS = (1, 2, 3, 4, 6, 8)
#: Generators Rule WT applies to, in report order.
WT_GENERATORS = ("G1", "G1-tg", "G2-strict", "G2-loose", "G3", "G4-60", "G4-180")
#: Generators with a link strength (all of T_LEVELS); the others have t = 1 only.
WEIGHTED = ("G1", "G1-tg", "G3", "G4-60", "G4-180")
#: Primary-cell footprint generators, in the draft's tie / expectation order.
PRIMARY_FOOTPRINT = ("G2-strict", "G3", "G1-tg")
PRIMARY_DEFAULT = ("G2-strict", 1, 1)


# ----------------------------------------------------------------------------------
# Pure rule functions (unit-tested in test_blue_rules.py)
# ----------------------------------------------------------------------------------

def admissible(V: Fraction, groups_per_day: Fraction, bound: Fraction = BOUND,
               min_gpd: Fraction = MIN_GROUPS_PER_DAY) -> bool:
    """Rule WT cell test: V <= B/2 and at least one group per day on average."""
    return V <= bound and groups_per_day >= min_gpd


def rule_wt(cells: dict[tuple[int, int], dict[str, Fraction]], bound: Fraction = BOUND,
            min_gpd: Fraction = MIN_GROUPS_PER_DAY) -> dict[str, Any]:
    """Rule WT over cells {(w, t): {"V": Fraction, "groups_per_day": Fraction}}: the largest
    w with an admissible cell, then the smallest admissible t at that w; else (1, 1)
    flagged over budget at every window."""
    adm = sorted((w, t) for (w, t), c in cells.items()
                 if admissible(c["V"], c["groups_per_day"], bound, min_gpd))
    if not adm:
        return {"w": 1, "t": 1, "over_budget_every_window": True, "admissible_cells": []}
    w = max(w for w, _ in adm)
    t = min(t for ww, t in adm if ww == w)
    return {"w": w, "t": t, "over_budget_every_window": False, "admissible_cells": adm}


def choose_primary(rows: dict[str, dict[str, Any]],
                   footprint: Sequence[str] = PRIMARY_FOOTPRINT) -> dict[str, Any]:
    """Primary generator: smallest V at (w_G, t_G) among footprint generators with an
    admissible cell (`over_budget_every_window` False), ties broken by the footprint
    order (all tied generators listed); none -> G2-strict at (1, 1) by default.
    `rows[g]` needs `V_final` (Fraction) and `over_budget_every_window`."""
    elig = [g for g in footprint if g in rows and not rows[g]["over_budget_every_window"]]
    excluded = [g for g in footprint if g in rows and rows[g]["over_budget_every_window"]]
    order = sorted(elig, key=lambda g: (Fraction(rows[g]["V_final"]), footprint.index(g)))
    if not order:
        g, w, t = PRIMARY_DEFAULT
        return {"eligible": [], "ordering": [], "primary": g, "tied_with": [],
                "default": True, "w": w, "t": t, "excluded_over_budget": excluded}
    vmin = Fraction(rows[order[0]]["V_final"])
    tied = [g for g in order if Fraction(rows[g]["V_final"]) == vmin]
    return {"eligible": elig,
            "ordering": [{"generator": g, "V": float(rows[g]["V_final"])} for g in order],
            "primary": order[0], "tied_with": tied[1:], "default": False,
            "w": rows[order[0]]["w"], "t": rows[order[0]]["t"],
            "excluded_over_budget": excluded}


# ----------------------------------------------------------------------------------
# Reading the haystack JSON
# ----------------------------------------------------------------------------------

def _num(V: Fraction | float | None) -> float | None:
    return None if V is None else float(V)


def cells_for(fork: dict[str, Any], g: str, windows: Sequence[int],
              levels: Sequence[int] = T_LEVELS) -> dict[tuple[int, int], dict[str, Any]]:
    """Rule WT cells of one generator from the haystack JSON (exact fractions)."""
    nad = int(fork["n_account_days"])
    out: dict[tuple[int, int], dict[str, Any]] = {}
    for w in windows:
        if g in WEIGHTED:
            c = fork["threshold_curves"][f"{g}|{w}"]
            nd = int(c["n_days_evaluated"])
            for t in levels:
                x = c["curve"][str(t)]
                out[(w, t)] = {"V": Fraction(int(x["review_pairs"]), nad),
                               "groups_per_day": Fraction(int(x["n_groups"]), nd),
                               "n_groups": int(x["n_groups"])}
        else:
            x = fork["volumes"]["groups"][str(w)][g]
            nd = sum(1 for n in fork["n_active_per_day"] if n > 0)   # = days evaluated
            out[(w, 1)] = {"V": Fraction(int(x["review_pairs"]), nad),
                           "groups_per_day": Fraction(int(x["n_groups"]), nd),
                           "n_groups": int(x["n_groups"])}
    return out


def apply_rules(hs: dict[str, Any], bound: Fraction = BOUND) -> dict[str, Any]:
    if hs.get("mode") != "fork":
        raise SystemExit("blue_rules.py needs a fork-mode haystack JSON (haystack.py "
                         "--fork-corpus)")
    fork = hs["fork"]
    windows = [int(w) for w in fork["windows"] if int(w) in RULE_W_WINDOWS]
    rows: dict[str, dict[str, Any]] = {}
    for g in WT_GENERATORS:
        cells = cells_for(fork, g, windows)
        r = rule_wt(cells, bound)
        fin = cells[(r["w"], r["t"])]
        rows[g] = {"generator": g, "rule": "WT", "w": r["w"], "t": r["t"],
                   "over_budget_every_window": r["over_budget_every_window"],
                   "admissible_cells": [list(x) for x in r["admissible_cells"]],
                   "V_final": fin["V"], "groups_per_day_final": _num(fin["groups_per_day"]),
                   "groups_final": fin["n_groups"],
                   "V_t1_by_w": {w: _num(cells[(w, 1)]["V"]) for w in windows},
                   "cells": {f"{w},{t}": {"V": _num(c["V"]),
                                          "groups_per_day": _num(c["groups_per_day"]),
                                          "admissible": admissible(c["V"], c["groups_per_day"],
                                                                   bound)}
                             for (w, t), c in sorted(cells.items())}}
    prim = choose_primary(rows)
    g5 = fork["volumes"]["groups"]["1"]["G5"]
    other = {"G5": {"V": float(Fraction(int(g5["review_pairs"]), int(fork["n_account_days"]))),
                    "n_groups": int(g5["n_groups"]), "note": "no window; Rule WT n/a"},
             "G6": {"amplification": {w: fork["volumes"]["g6"][str(w)] for w in windows},
                    "note": "propagation; Rule WT n/a"}}
    dens = fork["volumes"]["density"]
    uw = str(max(windows))
    density = {t: {"w1_L1_day_mean": dens["1"][t]["L1_mean"], "w1_W_day_mean": dens["1"][t]["W_mean"],
                   f"w{uw}_L1_whole_corpus": dens[uw][t].get("L1_union"),
                   f"w{uw}_W_whole_corpus": dens[uw][t].get("W_union")}
               for t in dens["1"]}
    for r in rows.values():
        r["V_final"] = _num(r["V_final"])
    return {"corpus": fork["corpus"], "corpus_path": fork["corpus_path"],
            "corpus_sha256": fork["corpus_sha256"], "n_days": fork["n_days"],
            "days": fork["days"], "windows": windows, "t_levels": list(T_LEVELS),
            "fork_touch_table": fork.get("fork_touch_table", "part1"),
            "windows_dropped_longer_than_corpus": fork["windows_dropped_longer_than_corpus"],
            "n_accounts_active": fork["n_accounts_active"],
            "n_account_days": fork["n_account_days"], "budget": float(B),
            "bound": float(bound), "rules": rows, "not_rule_wt": other, "primary": prim,
            "density": density, "density_union_window": int(uw)}


# ----------------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------------

def f(x: Any, nd: int = 4) -> str:
    if x is None:
        return "-"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, int):
        return str(x)
    x = float(x)
    if math.isnan(x):
        return "-"
    return f"{x:.{nd}f}"


def table(head: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def render(res: dict[str, Any], cmd: str) -> str:
    ws = res["windows"]
    cap = f"_Script: `work/checks/blue_rules.py`; command: `{cmd}`._"
    out = [f"## Blue's windows and thresholds on `{res['corpus']}` (TRACK-B part 2 draft "
           "section 2)\n",
           f"`{res['corpus_path']}`: {res['n_days']} days ({', '.join(res['days'])}), "
           f"{res['n_accounts_active']} active accounts, {res['n_account_days']} active "
           f"account-days. B = {res['budget']:.2f}, bound B/2 = {res['bound']:.2f}. Windows "
           f"evaluated: {', '.join(map(str, ws))}"
           + (f" (w = {', '.join(map(str, res['windows_dropped_longer_than_corpus']))} not "
              f"evaluated: longer than the corpus)"
              if res["windows_dropped_longer_than_corpus"] else "") + ".\n", cap + "\n",
           f"Fork touch table: {res['fork_touch_table']}.\n",
           "### Rule WT table\n"]
    rows = []
    for g, r in res["rules"].items():
        flag = "**over budget at every window**" if r["over_budget_every_window"] else "no"
        rows.append([g] + [f(r["V_t1_by_w"][w]) for w in ws] +
                    [r["w"], r["t"], f(r["V_final"]), f(r["groups_per_day_final"], 1),
                     len(r["admissible_cells"]), flag])
    out.append(table(["generator"] + [f"V w={w} (t=1)" for w in ws] +
                     ["w_G", "t_G", "V at (w_G, t_G)", "groups/day at (w_G, t_G)",
                      "admissible cells", "over-budget flag"], rows) + "\n")
    o = res["not_rule_wt"]
    out.append(f"Rule WT does not apply: G5 (no window) V = {f(o['G5']['V'])} "
               f"({o['G5']['n_groups']} groups); G6 honest amplification (accounts with S > 0 "
               "per seed): " + ", ".join(
                   f"w={w} mean {f(a['mean_accounts_S_pos'], 1)}, p90 "
                   f"{f(a['p90_accounts_S_pos'], 0)}" for w, a in o["G6"]["amplification"].items())
               + ".\n")
    rows = []
    for g in WT_GENERATORS:
        r = res["rules"][g]
        for w in ws:
            row = [g, w]
            for t in T_LEVELS:
                c = r["cells"].get(f"{w},{t}")
                row.append("-" if c is None else
                           f"{f(c['V'])} / {f(c['groups_per_day'], 1)}"
                           + (" **A**" if c["admissible"] else ""))
            rows.append(row)
    out.append("Rule WT cells: V / groups per day; **A** = admissible (V <= 0.05 and >= 1 "
               "group per day). G2 has t = 1 only.\n\n" +
               table(["generator", "w"] + [f"t={t}" for t in T_LEVELS], rows) + "\n")
    p = res["primary"]
    out.append("### Primary generator (draft section 2)\n")
    if p["default"]:
        out.append(f"**Primary: {p['primary']} at (w, t) = ({p['w']}, {p['t']}), default** "
                   "(no footprint generator among G2-strict, G3, G1-tg has an admissible "
                   "cell" + (f"; over budget at every window: "
                             f"{', '.join(p['excluded_over_budget'])}"
                             if p["excluded_over_budget"] else "") + ").\n")
    else:
        out.append(f"Eligible (footprint generators with an admissible cell): "
                   f"{', '.join(p['eligible'])}. Ordering by V at (w_G, t_G), ties in the "
                   f"order G2-strict, G3, G1-tg: " +
                   ", ".join(f"{x['generator']} {f(x['V'])}" for x in p["ordering"]) +
                   f". **Primary: {p['primary']} at (w, t) = ({p['w']}, {p['t']})**" +
                   (f" (tied with {', '.join(p['tied_with'])})" if p["tied_with"] else "") +
                   ".\n")
        if p["excluded_over_budget"]:
            out.append(f"Over budget at every window: {', '.join(p['excluded_over_budget'])}.\n")
    out.append("### Pair density by artefact type (share of unordered pairs of active "
               "accounts)\n")
    uw = res["density_union_window"]
    rows = [[t, f(d["w1_L1_day_mean"], 3), f(d["w1_W_day_mean"], 3),
             f(d[f"w{uw}_L1_whole_corpus"], 3), f(d[f"w{uw}_W_whole_corpus"], 3)]
            for t, d in res["density"].items()]
    out.append(table(["type", "w=1 L1>0 (day mean)", "w=1 W>0 (day mean)",
                      f"w={uw} L1>0 (whole corpus)", f"w={uw} W>0 (whole corpus)"], rows) + "\n")
    return "\n".join(out)


def _rel(p: str | Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(PROJECT))
    except ValueError:
        return str(p)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--haystack-json", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--md", default=None)
    args = ap.parse_args()
    raw = Path(args.haystack_json).read_bytes()
    hs = json.loads(raw)
    res = apply_rules(hs)
    cmd = (f"python -I work/checks/blue_rules.py --haystack-json {_rel(args.haystack_json)} "
           f"--out {_rel(args.out)}" + (f" --md {_rel(args.md)}" if args.md else ""))
    md = render(res, cmd)
    full = {"spec": "work/mole-fork/protocol/TRACK-B-part2-draft.md section 2 (Rules W, T) "
                    "and section 5 (primary generator)",
            "script": "work/checks/blue_rules.py", "command": cmd,
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "haystack_json": _rel(args.haystack_json),
            "haystack_json_sha256": hashlib.sha256(raw).hexdigest(), **res}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(full, indent=1, default=str))
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text(md)
    print(md)


if __name__ == "__main__":
    main()
