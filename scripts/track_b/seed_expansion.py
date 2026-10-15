#!/usr/bin/env python3
"""B0, seed expansion (TRACK-B part 1, section 4) on the released MOLE corpora.

For each corpus, each of the four colluding pairs, and each attack day (a label row of
either member for the pair's threat with outcome `executed`; `attempted` rows are the
secondary set), for each generator variant (G1, G2-strict, G2-loose, G3, G4-60,
G4-180, G5, G6), scope (likeforlike, allservices) and window (1, 3, 7): seed = the
labelled member, partner = the other member; candidates = every other account active in
the window; rank by L(seed, .) (row of the seed; for the directed G2 / G5 the seed is
the writer); pessimistic / optimistic rank; reviewable at B in {0.02, 0.10} if
r_pess <= max(1, floor(B * N_active(d))). Gate statement A (section 6) is evaluated on
the executed rows over the eight variants, both scopes and every window.

Sensitivity rows (not in the gate, reported separately): G1 per artefact type
(`G1:<type>`) and the reversed direction of the directed generators (`G2-strict:rev`,
`G2-loose:rev`, `G5:rev`, ranking by L(., seed)).

Usage (data dir is untrusted: absolute paths, -I):

    work/mole-fork/.venv/bin/python -I work/checks/seed_expansion.py \\
        --data-dir /abs/work/upstream-data --all-corpora \\
        --out /abs/work/stage2/b0-seed-expansion.json > b0-tables.md
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import generators as gen  # noqa: E402
import mole_corpus as mc  # noqa: E402

PROJECT = HERE.parent.parent
FORK = PROJECT / "work" / "mole-fork"
DEFAULT_TEMPLATE = FORK / "bootstrap" / "org_template.yaml"
DEFAULT_PAIRS = FORK / "bootstrap" / "insider_assignment.yaml"
DEFAULT_CACHE = PROJECT / "work" / "stage2" / "cache"
DEFAULT_OUT = PROJECT / "work" / "stage2" / "b0-seed-expansion.json"

GATE_VARIANTS = gen.VARIANTS
REV_VARIANTS = ("G2-strict", "G2-loose", "G5")
COLUMNS = ["corpus", "pair", "threat", "seed", "partner", "date", "outcome", "generator",
           "scope", "w", "L", "r_pess", "r_opt", "honest_above", "n_cand", "n_active",
           "cap_02", "cap_10", "rev_02", "rev_10", "partner_active_window",
           "seed_active_day", "gate_variant"]


def attack_rows(labels: pd.DataFrame, pairs: list[dict]) -> list[dict]:
    """Label rows of the pairs' members for the pair's threat (executed / attempted)."""
    out = []
    lab = labels.drop_duplicates(["account", "date", "scenario", "outcome"])
    for p in pairs:
        sub = lab[(lab["scenario"] == p["threat"]) & lab["account"].isin(p["members"])
                  & lab["outcome"].isin(["executed", "attempted"])]
        for r in sub.itertuples(index=False):
            partner = [m for m in p["members"] if m != r.account][0]
            out.append({"pair": p["pair"], "threat": p["threat"], "seed": r.account,
                        "partner": partner, "date": str(r.date)[:10], "outcome": r.outcome})
    return out


def run_corpus(args: argparse.Namespace, corpus: str, template: mc.OrgTemplate,
               pairs: list[dict]) -> tuple[list[list[Any]], dict[str, Any]]:
    t0 = time.time()
    tdf, rdf, adf, meta = mc.load_cache(args.data_dir, corpus, args.cache_dir, mc.eprint)
    ci = gen.build_index(corpus, tdf, rdf, adf, template, cache_dir=args.cache_dir,
                         log=mc.eprint)
    labels = mc.load_labels(args.data_dir, corpus)
    arows = attack_rows(labels, pairs)
    days = sorted({ci.day_rel(r["date"]) for r in arows})
    rows: list[list[Any]] = []
    skipped = []
    for d in days:
        if d < 0 or d >= ci.n_days:
            skipped.extend(r for r in arows if ci.day_rel(r["date"]) == d)
            continue
        n_act = ci.n_active(d)
        cap02, cap10 = gen.budget_cap(0.02, n_act), gen.budget_cap(0.10, n_act)
        todays = [r for r in arows if ci.day_rel(r["date"]) == d]
        for w in args.windows:
            act_w = ci.active_in_window(d, w)
            for scope in mc.SCOPES:
                L = gen.link_matrices(ci, d, w, scope, per_type=True)
                for r in todays:
                    s = ci.acc_idx[r["seed"]]
                    p = ci.acc_idx[r["partner"]]
                    cand = act_w.copy()
                    cand[s] = False
                    variants: list[tuple[str, np.ndarray, bool]] = [
                        (v, L[v][s], True) for v in GATE_VARIANTS]
                    variants += [(k, L[k][s], False) for k in L if k.startswith("G1:")]
                    variants += [(f"{v}:rev", L[v][:, s], False) for v in REV_VARIANTS]
                    for name, row, gate in variants:
                        rk = gen.rank_partner(row, cand, p)
                        rows.append([corpus, r["pair"], r["threat"], r["seed"], r["partner"],
                                     r["date"], r["outcome"], name, scope, w, rk["L"],
                                     rk["r_pess"], rk["r_opt"], rk["honest_above"],
                                     rk["n_cand"], n_act, cap02, cap10,
                                     rk["r_pess"] <= cap02, rk["r_pess"] <= cap10,
                                     bool(act_w[p]), bool(ci.active[d, s]), gate])
        mc.eprint(f"[{corpus}] day {ci.day_str(d)} done ({time.time()-t0:.1f}s)")
    info = {"runtime_s": round(time.time() - t0, 1), "n_attack_label_rows": len(arows),
            "n_executed": sum(r["outcome"] == "executed" for r in arows),
            "n_attempted": sum(r["outcome"] == "attempted" for r in arows),
            "skipped_label_rows_outside_corpus_days": skipped,
            "n_accounts": ci.n, "n_account_days": ci.n_account_days(),
            "args_parse_failures": meta.get("args_parse_failures"),
            "diagnostics": ci.diagnostics}
    mc.eprint(f"[{corpus}] B0 done: {len(arows)} label rows, {len(rows):,} result rows in "
              f"{info['runtime_s']}s")
    return rows, info


# ----------------------------------------------------------------------------------
# Tables
# ----------------------------------------------------------------------------------

def fmt(x: float, nd: int = 2) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    if isinstance(x, (int, np.integer)) or float(x).is_integer():
        return str(int(x))
    return f"{x:.{nd}f}"


def summarise(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    g = df.groupby(keys, sort=False)
    out = g.agg(n=("r_pess", "size"), med_r=("r_pess", "median"), max_r=("r_pess", "max"),
                rev02=("rev_02", "mean"), rev10=("rev_10", "mean"),
                L0=("L", lambda s: float((s == 0).mean())),
                med_cand=("n_cand", "median"), med_cap10=("cap_10", "median")).reset_index()
    return out


def md_table(df: pd.DataFrame, keys: list[str]) -> str:
    head = keys + ["n days", "median r_pess", "max r_pess", "share rev. B=0.02",
                   "share rev. B=0.10", "share L=0", "median cand.", "median cap@0.10"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in df.itertuples(index=False):
        vals = [str(getattr(r, k)) for k in keys]
        vals += [fmt(r.n), fmt(r.med_r, 1), fmt(r.max_r), fmt(r.rev02), fmt(r.rev10),
                 fmt(r.L0), fmt(r.med_cand, 1), fmt(r.med_cap10, 1)]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def order_frame(df: pd.DataFrame, var_order: list[str]) -> pd.DataFrame:
    df = df.copy()
    if "generator" in df:
        df["_g"] = df["generator"].map({v: i for i, v in enumerate(var_order)})
    sort = [c for c in ("corpus", "pair", "_g", "scope", "w") if c in df]
    return df.sort_values(sort).drop(columns=[c for c in ("_g",) if c in df])


def gate_a(df: pd.DataFrame) -> dict[str, Any]:
    """Gate statement A (section 6) over executed rows, gate variants, both scopes, every
    window: true iff no row has the partner reviewable at B = 0.10."""
    x = df[(df["outcome"] == "executed") & df["gate_variant"]]
    brk = x[x["rev_10"]]
    cells = (brk.groupby(["corpus", "pair", "generator", "scope", "w"]).size()
             .reset_index(name="days_reviewable"))
    tot = (x.groupby(["corpus", "pair", "generator", "scope", "w"]).size()
           .reset_index(name="days"))
    cells = cells.merge(tot, on=["corpus", "pair", "generator", "scope", "w"])
    return {"A": bool(len(brk) == 0), "n_rows": int(len(x)),
            "n_rows_reviewable_at_0.10": int(len(brk)),
            "breaking_cells": cells.to_dict(orient="records")}


def render_tables(df: pd.DataFrame, cmd: str) -> tuple[str, dict[str, Any]]:
    var_order = list(GATE_VARIANTS)
    cap = f"_Script: `work/checks/seed_expansion.py`; command: `{cmd}`._"
    out: list[str] = []
    ex = df[(df["outcome"] == "executed") & df["gate_variant"]]
    at = df[(df["outcome"] == "attempted") & df["gate_variant"]]

    out.append("### B0-T1. Per corpus, pair, generator, scope, window (executed attack days)\n")
    out.append(cap + "\n")
    for corpus in mc.CORPORA:
        sub = ex[ex["corpus"] == corpus]
        if len(sub) == 0:
            out.append(f"#### {corpus}\n\nno executed attack rows\n")
            continue
        t = order_frame(summarise(sub, ["pair", "generator", "scope", "w"]), var_order)
        out.append(f"#### {corpus}\n\n" + md_table(t, ["pair", "generator", "scope", "w"]) + "\n")

    out.append("### B0-T2. Pooled per generator over all corpora and pairs (executed)\n")
    out.append(cap + "\n")
    t = order_frame(summarise(ex, ["generator", "scope", "w"]), var_order)
    out.append(md_table(t, ["generator", "scope", "w"]) + "\n")

    out.append("### B0-T3. C2 pairs only, pooled over corpora (executed)\n")
    out.append(cap + "\n")
    c2 = ex[ex["pair"].str.startswith("C2")]
    t = order_frame(summarise(c2, ["pair", "generator", "scope", "w"]), var_order)
    out.append(md_table(t, ["pair", "generator", "scope", "w"]) + "\n")
    t = order_frame(summarise(c2, ["generator", "scope", "w"]), var_order)
    out.append("C2 both pairs pooled:\n\n" + md_table(t, ["generator", "scope", "w"]) + "\n")

    out.append("### B0-T4. C1 pairs only, pooled over corpora (executed)\n")
    out.append(cap + "\n")
    c1 = ex[ex["pair"].str.startswith("C1")]
    t = order_frame(summarise(c1, ["pair", "generator", "scope", "w"]), var_order)
    out.append(md_table(t, ["pair", "generator", "scope", "w"]) + "\n")

    out.append("### B0-T5. Secondary set: attempted attack days, pooled per generator\n")
    out.append(cap + "\n")
    if len(at):
        t = order_frame(summarise(at, ["generator", "scope", "w"]), var_order)
        out.append(md_table(t, ["generator", "scope", "w"]) + "\n")
    else:
        out.append("no attempted rows\n")

    out.append("### B0-T6. Sensitivity rows (not in the gate): G1 per type and reversed "
               "direction of G2 / G5, pooled over corpora (executed)\n")
    out.append(cap + "\n")
    sens = df[(df["outcome"] == "executed") & ~df["gate_variant"]]
    t = summarise(sens, ["generator", "scope", "w"]).sort_values(["generator", "scope", "w"])
    out.append(md_table(t, ["generator", "scope", "w"]) + "\n")

    ga = gate_a(df)
    sens_ex = df[(df["outcome"] == "executed")]
    a_with_sens = bool(not sens_ex["rev_10"].any())
    out.append("### B0-T7. Gate statement A (TRACK-B section 6)\n")
    out.append(cap + "\n")
    out.append(f"A = **{str(ga['A']).lower()}** over {ga['n_rows']:,} executed rows "
               f"(gate variants {', '.join(GATE_VARIANTS)}; scopes likeforlike, allservices; "
               f"windows 1, 3, 7); rows with the partner reviewable at B = 0.10: "
               f"{ga['n_rows_reviewable_at_0.10']:,}.\n")
    out.append(f"With the sensitivity variants also included (G1 per type, reversed G2/G5), "
               f"A would be {str(a_with_sens).lower()}.\n")
    if ga["breaking_cells"]:
        out.append("Cells where the partner was reviewable at B = 0.10 on at least one "
                   "executed attack day:\n")
        lines = ["| corpus | pair | generator | scope | w | days reviewable | executed days |",
                 "|---|---|---|---|---|---|---|"]
        bc = pd.DataFrame(ga["breaking_cells"])
        bc = order_frame(bc, var_order)
        for r in bc.itertuples(index=False):
            lines.append(f"| {r.corpus} | {r.pair} | {r.generator} | {r.scope} | {r.w} | "
                         f"{r.days_reviewable} | {r.days} |")
        out.append("\n".join(lines) + "\n")
    return "\n".join(out), ga


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--corpus", action="append", default=[])
    ap.add_argument("--all-corpora", action="store_true")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--cache-dir", default=str(DEFAULT_CACHE))
    ap.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    ap.add_argument("--pairs", default=str(DEFAULT_PAIRS))
    ap.add_argument("--windows", default="1,3,7")
    ap.add_argument("--sensitivity-v1", action="store_true",
                    help="post-hoc sensitivity v1 (not pre-registered): errata items 1, 2, 3, 12")
    ap.add_argument("--lowercase-ids", action="store_true",
                    help="post-hoc (TRACK-B part 1 errata item 2, not bundled with "
                         "--sensitivity-v1): create_issue explicit id matched case-insensitively, "
                         "prefix may contain hyphens (deepa-a1-214). Released corpora only (this "
                         "script has no fork mode)")
    ap.add_argument("--tables-out", default=None, help="also write the markdown tables here")
    args = ap.parse_args()
    if args.sensitivity_v1:
        mc.set_sensitivity_v1(True)
        if args.out == str(DEFAULT_OUT):
            args.out = str(DEFAULT_OUT).replace(".json", ".sensitivity-v1.json")
    if args.lowercase_ids:
        mc.set_lowercase_ids(True)
        # never write over the frozen primary / sensitivity-v1 outputs
        if args.out.endswith(".json") and ".lowercase-ids." not in args.out:
            args.out = args.out[:-len(".json")] + ".lowercase-ids.json"
    args.windows = [int(x) for x in args.windows.split(",")]
    corpora = list(mc.CORPORA) if args.all_corpora else args.corpus
    if not corpora:
        ap.error("--corpus or --all-corpora")
    cmd = "python -I work/checks/seed_expansion.py --data-dir work/upstream-data " + (
        "--all-corpora" if args.all_corpora else " ".join(f"--corpus {c}" for c in corpora)) + \
        " --out work/stage2/b0-seed-expansion.json" + \
        (" --sensitivity-v1 (out: b0-seed-expansion.sensitivity-v1.json)" if args.sensitivity_v1 else "") + \
        (" --lowercase-ids (out: *.lowercase-ids.json)" if args.lowercase_ids else "")
    template = mc.load_org_template(args.template)
    pairs = mc.load_pairs(args.pairs)
    t0 = time.time()
    all_rows: list[list[Any]] = []
    infos: dict[str, Any] = {}
    for c in corpora:
        rows, info = run_corpus(args, c, template, pairs)
        all_rows.extend(rows)
        infos[c] = info
    df = pd.DataFrame(all_rows, columns=COLUMNS)
    tables, ga = render_tables(df, cmd)
    if args.sensitivity_v1:
        tables = "> **POST-HOC SENSITIVITY v1, NOT PART OF THE PRE-REGISTERED GATE.** Switched on together: (1) windows counted in active corpus days (day index) instead of calendar days; (2) `create_issue` explicit id matched case-insensitively as `<prefix>-<N>` (prefix `[A-Za-z][A-Za-z0-9]*`) at the start of `name`; (3) `ticket_id` (and `issue_id` / `identifier` on `create_issue`) accepted as ticket keys on comment / transition / update / create; (4) one trailing `.` or `:` stripped from tokens before G2 identifier matching. The gate statements printed below are what A / B would be under this variant; the recorded gate uses the primary (literal) run.\n" + "\n" + tables
    if args.lowercase_ids:
        tables = "> **POST-HOC LOWER-CASE TICKET IDS (TRACK-B part 1 errata item 2), NOT PART OF THE PRE-REGISTERED GATE.** `create_issue` explicit id matched as `<prefix>-<N>` at the start of `name`, case-insensitive, prefix may contain hyphens (`^\\s*([A-Za-z][A-Za-z0-9-]*-[0-9]+)(?![A-Za-z0-9_-])`, e.g. `deepa-a1-214`). Released-corpus mode only; not bundled with sensitivity v1.\n" + "\n" + tables
    res = {
        "spec": "work/mole-fork/protocol/TRACK-B.md part 1 (commit 0cfe331), section 4",
        "script": "work/checks/seed_expansion.py", "command": cmd,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pairs": pairs, "windows": args.windows, "scopes": list(mc.SCOPES),
        "gate_variants": list(GATE_VARIANTS), "budgets": list(gen.BUDGETS),
        "window_semantics": ("active corpus days (index) d-w+1..d" if args.sensitivity_v1
                             else "calendar days d-w+1..d"), "corpora": infos,
        "sensitivity_v1": bool(args.sensitivity_v1),
        "runtime_s_total": round(time.time() - t0, 1),
        "gate_A": ga, "columns": COLUMNS,
        "rows": [[(x.item() if hasattr(x, "item") else x) for x in r] for r in all_rows],
    }
    if args.lowercase_ids:
        res["lowercase_ids"] = True
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, default=str))
    if args.tables_out:
        Path(args.tables_out).write_text(tables)
    print(tables)
    mc.eprint(f"B0 total runtime {res['runtime_s_total']}s; gate A = {ga['A']}")


if __name__ == "__main__":
    main()
