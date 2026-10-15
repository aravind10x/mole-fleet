#!/usr/bin/env python3
"""B1, haystack (TRACK-B part 1, section 5) on the released MOLE corpora, with N-scaling.

Per corpus, like-for-like scope, every active day of the corpus, each generator variant
(G1, G3, G4-60, G4-180, G2-strict, G2-loose, G5) and window (1, 3, 7):
- groups per day (mean count; size mean / p50 / p90 over all emitted groups),
- volume V = distinct (account, day) review pairs implied by every emitted group,
  divided by the corpus's active account-days; fits at B if V <= B, B in {0.02, 0.10};
- G6 honest amplification: per seed at each active account on day d, the number of
  accounts with S > 0 (mean, p90);
- honest pair-interaction density by artefact type (share of unordered pairs of active
  accounts with L1_t > 0 and with W_t > 0): per day at w = 1 (mean over days); at
  w = 7 both the per-day mean and the whole-corpus union of 7-day windows;
- the G2 right tail: per ordered pair L2 (p50/p90/p99/max over pairs with >= 1
  handoff, each handoff counted once on its emission day), the unrequested-action
  rate, and the candidate multiplicity per B-action;
- the per-corpus argument-key usage table (section 1);
- N-scaling: induced sub-orgs N in {50, 100} (5 seeds each, random.Random(20261014+i))
  and N = 150, w in {1, 3}: V, groups per day, pooled pair density, G6 amplification;
- gate statement B (section 6): every corpus x G1..G5 variant x window has V > 0.10.

Usage (data dir untrusted: absolute paths, -I):

    work/mole-fork/.venv/bin/python -I work/checks/haystack.py \\
        --data-dir /abs/work/upstream-data --all-corpora \\
        --out /abs/work/stage2/b1-haystack.json --fig /abs/work/stage2/fig-n-scaling.png

Fork mode (TRACK-B part 2 draft section 2; the input for `blue_rules.py`): the same B1
tables on a fork audit JSONL, like-for-like scope, fork-only touches included, windows
w in {1, 2, 3} corpus days (trailing, truncated at day 1, none longer than the corpus),
plus G1 restricted to tickets and groups (`G1-tg`), the Rule T threshold curves V(w, t)
for G1 / G1-tg / G3 / G4 and G6's budget-capped volume:

    work/mole-fork/.venv/bin/python -I work/checks/haystack.py \\
        --fork-corpus /abs/work/mole-fork/data/corpus/spike/prefix_v1.jsonl \\
        --out /abs/work/stage2/b1-haystack.prefix_v1.json \\
        --md /abs/work/stage2/b1-haystack.prefix_v1.md
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
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
DEFAULT_CACHE = PROJECT / "work" / "stage2" / "cache"
DEFAULT_OUT = PROJECT / "work" / "stage2" / "b1-haystack.json"
DEFAULT_FIG = PROJECT / "work" / "stage2" / "fig-n-scaling.png"

B1_VARIANTS = ("G1", "G2-strict", "G2-loose", "G3", "G4-60", "G4-180", "G5")
#: Fork mode adds G1 restricted to tickets and groups (part 2 draft section 5 footprint).
G1_TG_TYPES = ("ticket", "group")
SCOPE = "likeforlike"
SEED0 = 20261014
N_SCALING = ((50, 5), (100, 5), (150, 1))
N_WINDOWS = (1, 3)


def groups_for(ci: gen.CorpusIndex, variant: str, d: int, w: int,
               min_link: float = 1) -> gen.Groups:
    """Groups of one variant on day d, window w. `min_link` (Rule T, fork mode) applies to
    the weighted generators G1, G1-tg, G3, G4-*; `G1-tg` is G1 restricted to tickets
    and groups (the primary cell's footprint, TRACK-B part 2 draft section 5)."""
    if variant == "G1":
        return gen.g1(ci, d, w, SCOPE, min_link=min_link)[0]
    if variant == "G1-tg":
        return gen.g1(ci, d, w, SCOPE, types=G1_TG_TYPES, min_link=min_link)[0]
    if variant == "G3":
        return gen.g3(ci, d, w, SCOPE, min_link=min_link)[0]
    if variant.startswith("G4-"):
        return gen.g4(ci, d, w, SCOPE, float(variant.split("-")[1]), min_link=min_link)[0]
    if variant.startswith("G2-"):
        return gen.g2(ci, d, w, SCOPE, variant.split("-")[1])[0]
    if variant == "G5":
        return gen.g5(ci, d, w, SCOPE)[0]
    raise ValueError(variant)


def volume_block(ci: gen.CorpusIndex, windows: tuple[int, ...], with_density: bool,
                 with_amplification: bool = True,
                 variants: tuple[str, ...] = B1_VARIANTS, union_w: int = 7) -> dict[str, Any]:
    """Groups per day, V, G6 amplification and (optionally) the pair density table.
    `union_w`: the window at which the whole-corpus density (union of the per-day
    windows' pairs) is also reported (7 in the released-corpus B1; the largest window
    in fork mode)."""
    out: dict[str, Any] = {"groups": {}, "g6": {}, "density": {}}
    nad = ci.n_account_days()
    like_codes = [gen.TYPE_CODES[t] for t in mc.LIKE_TYPES]
    for w in windows:
        per_var: dict[str, dict[str, list]] = {v: {"count": [], "sizes": [], "review": []}
                                                for v in variants}
        amp: list[int] = []
        dens: dict[str, dict[str, list[float]]] = {t: {"L1": [], "W": []}
                                                   for t in list(mc.LIKE_TYPES) + ["any"]}
        union_pairs: dict[str, dict[str, set]] = {t: {"L1": set(), "W": set()}
                                                  for t in list(mc.LIKE_TYPES) + ["any"]}
        for d in ci.days:
            d = int(d)
            for v in variants:
                g = groups_for(ci, v, d, w)
                per_var[v]["count"].append(len(g.sizes))
                per_var[v]["sizes"].append(g.sizes)
                per_var[v]["review"].append(g.review)
            win = gen.window_touches(ci, d, w, SCOPE)
            Wall = gen.interaction_w(win, ci.n)
            if with_amplification:
                act = np.flatnonzero(ci.active[d])
                amp.extend((Wall[act] > 0).sum(axis=1).tolist())
            if with_density:
                act_w = ci.active_in_window(d, w)
                na = int(act_w.sum())
                npairs = na * (na - 1) / 2
                iu = np.triu_indices(ci.n, 1)
                L1any = np.zeros((ci.n, ci.n))
                for t in mc.LIKE_TYPES:
                    m = win.type == gen.TYPE_CODES[t]
                    L1t = gen.cooc(win.acct[m & win.write], win.art[m & win.write], ci.n)
                    Wt = gen.cooc(win.acct[m], win.art[m], ci.n)
                    L1any += L1t
                    for nm, M in (("L1", L1t), ("W", Wt)):
                        hit = M[iu] > 0
                        dens[t][nm].append(hit.sum() / npairs if npairs else np.nan)
                        if w == union_w:
                            union_pairs[t][nm].update(zip(iu[0][hit].tolist(),
                                                          iu[1][hit].tolist()))
                for nm, M in (("L1", L1any), ("W", Wall)):
                    hit = M[iu] > 0
                    dens["any"][nm].append(hit.sum() / npairs if npairs else np.nan)
                    if w == union_w:
                        union_pairs["any"][nm].update(zip(iu[0][hit].tolist(),
                                                          iu[1][hit].tolist()))
        gw: dict[str, Any] = {}
        for v in variants:
            sizes = np.concatenate(per_var[v]["sizes"]) if per_var[v]["sizes"] else np.zeros(0)
            rev = np.unique(np.concatenate(per_var[v]["review"])) if per_var[v]["review"] \
                else np.zeros(0)
            V = len(rev) / nad if nad else float("nan")
            gw[v] = {"groups_per_day_mean": float(np.mean(per_var[v]["count"])),
                     "groups_per_day_p50": gen.pct(per_var[v]["count"], 50),
                     "groups_per_day_p90": gen.pct(per_var[v]["count"], 90),
                     "size_mean": float(sizes.mean()) if len(sizes) else float("nan"),
                     "size_p50": gen.pct(sizes, 50), "size_p90": gen.pct(sizes, 90),
                     "size_max": int(sizes.max()) if len(sizes) else 0,
                     "n_groups": int(len(sizes)), "review_pairs": int(len(rev)), "V": V,
                     "fits_0.02": bool(V <= 0.02), "fits_0.10": bool(V <= 0.10)}
        out["groups"][w] = gw
        if with_amplification:
            out["g6"][w] = {"mean_accounts_S_pos": float(np.mean(amp)) if amp else float("nan"),
                            "p90_accounts_S_pos": gen.pct(amp, 90), "n_seeds": len(amp)}
        if with_density:
            na_all = int(ci.active.any(axis=0).sum())
            np_all = na_all * (na_all - 1) / 2
            out["density"][w] = {
                t: {"L1_mean": float(np.nanmean(dens[t]["L1"])),
                    "W_mean": float(np.nanmean(dens[t]["W"])),
                    **({"L1_union": len(union_pairs[t]["L1"]) / np_all,
                        "W_union": len(union_pairs[t]["W"]) / np_all} if w == union_w else {})}
                for t in dens}
    return out


def g2_tail(ci: gen.CorpusIndex, windows: tuple[int, ...]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for variant in ("strict", "loose"):
        h = ci.handoffs[variant]
        for w in windows:
            e = h[(h["act_day"] - h["rec_day"]) <= w - 1]     # emitted on act_day with rec in window
            pair = e.groupby(["A", "B"]).size().to_numpy() if len(e) else np.zeros(0)
            mult = e.groupby("act_ev")["A"].nunique().to_numpy() if len(e) else np.zeros(0)
            out[f"{variant}|{w}"] = {
                "variant": variant, "w": w, "n_handoffs": int(len(e)),
                "n_pairs": int(len(pair)), "n_distinct_A": int(e["A"].nunique()) if len(e) else 0,
                "n_distinct_B": int(e["B"].nunique()) if len(e) else 0,
                "share_R_is_ticket": float(e["R_is_ticket"].mean()) if len(e) else float("nan"),
                "L2_p50": gen.pct(pair, 50), "L2_p90": gen.pct(pair, 90),
                "L2_p99": gen.pct(pair, 99), "L2_max": int(pair.max()) if len(pair) else 0,
                "n_B_actions": int(len(mult)),
                "mult_mean": float(mult.mean()) if len(mult) else float("nan"),
                "mult_p50": gen.pct(mult, 50), "mult_p90": gen.pct(mult, 90),
                "mult_max": int(mult.max()) if len(mult) else 0,
                "share_mult_ge2": float((mult >= 2).mean()) if len(mult) else float("nan"),
            }
    for w in windows:
        out[f"unrequested|{w}"] = gen.unrequested_rate(ci, w)
    return out


def n_scaling(ci: gen.CorpusIndex, template: mc.OrgTemplate) -> list[dict[str, Any]]:
    res = []
    for N, nseeds in N_SCALING:
        for i in range(nseeds):
            keep = mc.induce_suborg(template, N, SEED0 + i)
            sub = gen.restrict(ci, keep)
            vb = volume_block(sub, N_WINDOWS, with_density=False)
            for w in N_WINDOWS:
                # pooled pair density (any like-for-like type), per day mean
                dl, dw = [], []
                iu = np.triu_indices(sub.n, 1)
                for d in sub.days:
                    d = int(d)
                    win = gen.window_touches(sub, d, w, SCOPE)
                    act_w = sub.active_in_window(d, w)
                    na = int(act_w.sum())
                    npairs = na * (na - 1) / 2
                    L1 = gen.cooc(win.acct[win.write], win.art[win.write], sub.n)
                    Wm = gen.interaction_w(win, sub.n)
                    dl.append((L1[iu] > 0).sum() / npairs if npairs else np.nan)
                    dw.append((Wm[iu] > 0).sum() / npairs if npairs else np.nan)
                for v in B1_VARIANTS:
                    g = vb["groups"][w][v]
                    res.append({"N": N, "seed": SEED0 + i, "w": w, "generator": v, "V": g["V"],
                                "groups_per_day_mean": g["groups_per_day_mean"],
                                "size_mean": g["size_mean"],
                                "density_L1_any": float(np.nanmean(dl)),
                                "density_W_any": float(np.nanmean(dw)),
                                "g6_mean_S_pos": vb["g6"][w]["mean_accounts_S_pos"],
                                "n_account_days": sub.n_account_days()})
    return res


def run_corpus(args: argparse.Namespace, corpus: str, template: mc.OrgTemplate,
               do_scaling: bool) -> dict[str, Any]:
    t0 = time.time()
    tdf, rdf, adf, meta = mc.load_cache(args.data_dir, corpus, args.cache_dir, mc.eprint)
    ci = gen.build_index(corpus, tdf, rdf, adf, template, cache_dir=args.cache_dir,
                         log=mc.eprint)
    vb = volume_block(ci, tuple(args.windows), with_density=True)
    mc.eprint(f"[{corpus}] volumes done ({time.time()-t0:.1f}s)")
    tail = g2_tail(ci, tuple(args.windows))
    mc.eprint(f"[{corpus}] G2 tail done ({time.time()-t0:.1f}s)")
    t1 = time.time()
    scaling = n_scaling(ci, template) if do_scaling else []
    mc.eprint(f"[{corpus}] N-scaling {'done' if do_scaling else 'skipped'} "
              f"({time.time()-t1:.1f}s)")
    return {"corpus": corpus, "n_days": int(len(ci.days)),
            "n_accounts_active": int(ci.active.any(axis=0).sum()),
            "n_account_days": ci.n_account_days(), "volumes": vb, "g2_tail": tail,
            "scaling": scaling, "keys": meta["keys"],
            "args_parse_failures": meta.get("args_parse_failures"),
            "diagnostics": ci.diagnostics,
            "runtime_s": round(time.time() - t0, 1),
            "runtime_scaling_s": round(time.time() - t1, 1)}


# ----------------------------------------------------------------------------------
# Tables
# ----------------------------------------------------------------------------------

def f(x: Any, nd: int = 3) -> str:
    if x is None:
        return "-"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    x = float(x)
    if np.isnan(x):
        return "-"
    if x != 0 and abs(x) < 0.001:
        return f"{x:.1e}"
    return f"{x:.{nd}f}"


def table(head: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def key_table(results: dict[str, Any]) -> str:
    """Per-corpus argument-key usage for the touch-table actions (section 1)."""
    corpora = list(results)
    acts = [f"{r.service}.{r.action}" for r in mc.TOUCH_RULES]
    rows = []
    for a in dict.fromkeys(acts):
        keys: Counter = Counter()
        for c in corpora:
            keys.update({k: v for k, v in results[c]["keys"].get(a, {}).items()})
        if not keys:
            rows.append([a, "(no events)"] + ["0"] * len(corpora))
            continue
        for k, _ in keys.most_common():
            row = [a if k == "__events__" else "", "events" if k == "__events__" else f"`{k}`"]
            row += [str(results[c]["keys"].get(a, {}).get(k, 0)) for c in corpora]
            rows.append(row)
    short = [c.replace("deepseek_v4_flash", "ds").replace("qwen36_27b", "qwen")
             .replace("kimi_k26", "kimi").replace("_single_day", "-sd")
             .replace("_multiday", "-md") for c in corpora]
    return table(["service.action", "arg key"] + short, rows)


def render(results: dict[str, Any], gate: dict[str, Any], cmd: str, windows: list[int]) -> str:
    cap = f"_Script: `work/checks/haystack.py`; command: `{cmd}`._"
    out = []
    out.append("### B1-T1. Per corpus: groups per day, size, volume V, fit (like-for-like)\n")
    out.append(cap + "\n")
    for c, r in results.items():
        rows = []
        for w in windows:
            for v in B1_VARIANTS:
                g = r["volumes"]["groups"][w][v]
                rows.append([v, w, f(g["groups_per_day_mean"], 1), f(g["size_mean"], 2),
                             f(g["size_p50"], 0), f(g["size_p90"], 1), g["size_max"],
                             f(g["V"], 4), f(g["fits_0.02"]), f(g["fits_0.10"])])
        out.append(f"#### {c} ({r['n_days']} days, {r['n_account_days']:,} active "
                   f"account-days)\n\n" + table(
            ["generator", "w", "groups/day", "size mean", "size p50", "size p90", "size max",
             "V", "fits 0.02", "fits 0.10"], rows) + "\n")
        rows = [[w, f(r["volumes"]["g6"][w]["mean_accounts_S_pos"], 1),
                 f(r["volumes"]["g6"][w]["p90_accounts_S_pos"], 0)] for w in windows]
        out.append("G6 honest amplification (accounts with S > 0 per seed):\n\n" +
                   table(["w", "mean", "p90"], rows) + "\n")

    out.append("### B1-T2. Honest pair-interaction density by artefact type "
               "(share of unordered pairs of active accounts)\n")
    out.append(cap + "\n")
    types = list(mc.LIKE_TYPES) + ["any"]
    rows = []
    for c, r in results.items():
        d1 = r["volumes"]["density"].get(1, {})
        d7 = r["volumes"]["density"].get(7, {})
        for t in types:
            rows.append([c, t, f(d1.get(t, {}).get("L1_mean")), f(d1.get(t, {}).get("W_mean")),
                         f(d7.get(t, {}).get("L1_mean")), f(d7.get(t, {}).get("W_mean")),
                         f(d7.get(t, {}).get("L1_union")), f(d7.get(t, {}).get("W_union"))])
    out.append(table(["corpus", "type", "w=1 L1>0 (day mean)", "w=1 W>0 (day mean)",
                      "w=7 L1>0 (day mean)", "w=7 W>0 (day mean)",
                      "w=7 L1>0 (whole corpus)", "w=7 W>0 (whole corpus)"], rows) + "\n")

    out.append("### B1-T3. G2 right tail (F3' closure)\n")
    out.append(cap + "\n")
    rows = []
    for c, r in results.items():
        for variant in ("strict", "loose"):
            for w in windows:
                t = r["g2_tail"][f"{variant}|{w}"]
                rows.append([c, variant, w, t["n_handoffs"], t["n_pairs"], f(t["L2_p50"], 0),
                             f(t["L2_p90"], 1), f(t["L2_p99"], 1), t["L2_max"],
                             f(t["share_R_is_ticket"], 2), t["n_B_actions"], f(t["mult_mean"], 2),
                             f(t["mult_p90"], 1), t["mult_max"], f(t["share_mult_ge2"], 2)])
    out.append(table(["corpus", "G2", "w", "handoffs", "ordered pairs >= 1", "L2 p50", "L2 p90",
                      "L2 p99", "L2 max", "share R = read ticket", "B-actions",
                      "multiplicity mean", "mult. p90", "mult. max", "share mult >= 2"],
                     rows) + "\n")
    rows = []
    for c, r in results.items():
        for w in windows:
            u = r["g2_tail"][f"unrequested|{w}"]
            bt = u["by_type"]
            rows.append([c, w, u["n_write_touches"], f(u["rate"])] +
                        [f"{f(bt[t]['rate'])} ({bt[t]['n']})" if t in bt else "-"
                         for t in mc.LIKE_TYPES])
    out.append("Unrequested-action rate (like-for-like write touches with no earlier ticket "
               "record naming the value within the window; per type: rate (n)):\n\n" +
               table(["corpus", "w", "write touches", "rate"] + list(mc.LIKE_TYPES), rows) + "\n")

    out.append("### B1-T4. Argument-key usage per corpus for the touch-table actions "
               "(successful events)\n")
    out.append(cap + "\n")
    out.append(key_table(results) + "\n")

    out.append("### B1-T5. N-scaling: V against N (like-for-like; mean [min, max] over seeds)\n")
    out.append(cap + "\n")
    rows = []
    for c, r in results.items():
        if not r["scaling"]:
            continue
        sc = pd.DataFrame(r["scaling"])
        for w in N_WINDOWS:
            for v in B1_VARIANTS:
                cells = []
                for N, _ in N_SCALING:
                    x = sc[(sc["w"] == w) & (sc["generator"] == v) & (sc["N"] == N)]["V"]
                    cells.append(f"{f(x.mean(), 4)} [{f(x.min(), 4)}, {f(x.max(), 4)}]"
                                 if len(x) > 1 else f(x.mean(), 4))
                rows.append([c, w, v] + cells)
    out.append(table(["corpus", "w", "generator"] + [f"V at N={N}" for N, _ in N_SCALING],
                     rows) + "\n")
    rows = []
    for c, r in results.items():
        if not r["scaling"]:
            continue
        sc = pd.DataFrame(r["scaling"])
        for w in N_WINDOWS:
            for N, _ in N_SCALING:
                x = sc[(sc["w"] == w) & (sc["N"] == N)]
                gpd = {v: x[x["generator"] == v]["groups_per_day_mean"].mean()
                       for v in B1_VARIANTS}
                rows.append([c, w, N, f(x["density_L1_any"].mean()), f(x["density_W_any"].mean()),
                             f(x["g6_mean_S_pos"].mean(), 1)] + [f(gpd[v], 1) for v in B1_VARIANTS])
    out.append("Pooled pair density, G6 amplification and groups per day against N "
               "(mean over seeds):\n\n" + table(
        ["corpus", "w", "N", "L1>0 density", "W>0 density", "G6 mean S>0"] +
        [f"{v} groups/day" for v in B1_VARIANTS], rows) + "\n")

    out.append("### B1-T6. Gate statement B (TRACK-B section 6)\n")
    out.append(cap + "\n")
    out.append(f"B = **{str(gate['B']).lower()}** (every corpus x {', '.join(B1_VARIANTS)} x "
               f"windows {', '.join(map(str, windows))}, like-for-like, N = 150: V > 0.10). "
               f"Cells checked: {gate['n_cells']}; cells with V <= 0.10: "
               f"{len(gate['fitting_cells'])}.\n")
    if gate["fitting_cells"]:
        rows = [[x["corpus"], x["generator"], x["w"], f(x["V"], 4), f(x["V"] <= 0.02)]
                for x in gate["fitting_cells"]]
        out.append(table(["corpus", "generator", "w", "V", "also fits 0.02"], rows) + "\n")
    rows = [[c, r["runtime_s"], r["runtime_scaling_s"]] for c, r in results.items()]
    out.append("Runtime per corpus (s):\n\n" + table(["corpus", "total", "of which N-scaling"],
                                                     rows) + "\n")
    return "\n".join(out)


def gate_b(results: dict[str, Any], windows: list[int]) -> dict[str, Any]:
    cells = []
    for c, r in results.items():
        for w in windows:
            for v in B1_VARIANTS:
                cells.append({"corpus": c, "generator": v, "w": w,
                              "V": r["volumes"]["groups"][w][v]["V"]})
    fit = [x for x in cells if x["V"] <= 0.10]
    return {"B": len(fit) == 0, "n_cells": len(cells), "fitting_cells": fit}


def figure(results: dict[str, Any], path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    have = [c for c, r in results.items() if r["scaling"]]
    if not have:
        return
    colors = {"G1": "#2a78d6", "G2-strict": "#eb6834", "G2-loose": "#eb6834", "G3": "#1baf7a",
              "G4-60": "#4a3aa7", "G4-180": "#4a3aa7", "G5": "#e87ba4"}
    styles = {"G2-loose": "--", "G4-180": "--"}
    markers = {"G1": "o", "G2-strict": "s", "G2-loose": "s", "G3": "^", "G4-60": "D",
               "G4-180": "D", "G5": "v"}
    fig, axes = plt.subplots(len(have), len(N_WINDOWS), figsize=(10, 2.6 * len(have)),
                             sharex=True, squeeze=False)
    Ns = [N for N, _ in N_SCALING]
    for i, c in enumerate(have):
        sc = pd.DataFrame(results[c]["scaling"])
        for j, w in enumerate(N_WINDOWS):
            ax = axes[i][j]
            for v in B1_VARIANTS:
                x = sc[(sc["w"] == w) & (sc["generator"] == v)].groupby("N")["V"]
                mean, lo, hi = x.mean().reindex(Ns), x.min().reindex(Ns), x.max().reindex(Ns)
                floor = 1e-4
                ax.plot(Ns, np.maximum(mean, floor), styles.get(v, "-"), color=colors[v],
                        marker=markers[v], ms=5, lw=1.6, label=v)
                ax.fill_between(Ns, np.maximum(lo, floor), np.maximum(hi, floor),
                                color=colors[v], alpha=0.15, lw=0)
            for b in (0.02, 0.10):
                ax.axhline(b, color="#52514e", lw=1, ls=":")
                ax.text(Ns[-1] + 2, b, f"B={b:g}", va="center", fontsize=7, color="#52514e")
            ax.set_yscale("log")
            ax.set_ylim(1e-4, 1.5)
            ax.set_xticks(Ns)
            ax.grid(axis="y", color="#e5e4e0", lw=0.6)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
            ax.set_title(f"{c}, w = {w}", fontsize=9, loc="left")
            if j == 0:
                ax.set_ylabel("V (log; floor 1e-4)", fontsize=8)
            if i == len(have) - 1:
                ax.set_xlabel("N accounts in induced sub-org", fontsize=8)
    axes[0][-1].legend(fontsize=7, loc="lower right", ncol=2, frameon=False)
    fig.suptitle("B1 N-scaling: review volume V per generator against N (mean, min-max band "
                 "over 5 seeds; like-for-like)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(path, dpi=140)
    plt.close(fig)


# ----------------------------------------------------------------------------------
# Fork mode (--fork-corpus): B1 on the fork's own audit JSONL (TRACK-B part 2 draft
# section 2). Like-for-like scope only (the fork has only like-for-like services);
# fork-only touches included; windows w in {1, 2, 3} corpus days, trailing, truncated
# at day 1, never longer than the corpus; the Rule T threshold curves for the weighted
# generators; G6's budget-capped volume. The released-corpus mode above is unchanged.
# ----------------------------------------------------------------------------------

FORK_WINDOWS = (1, 2, 3)
FORK_VARIANTS = ("G1", "G1-tg", "G2-strict", "G2-loose", "G3", "G4-60", "G4-180", "G5")
#: Generators with a link strength that Rule T thresholds (G1, G3, G4; G1-tg is G1).
WEIGHTED_VARIANTS = ("G1", "G1-tg", "G3", "G4-60", "G4-180")
#: Threshold levels always reported (the integer scan below is complete regardless).
T_GRID = (1, 2, 3, 4, 6, 8)
FORK_BUDGET = 0.10


def _weighted(ci: gen.CorpusIndex, variant: str, d: int, w: int, min_link: float,
              want_members: bool) -> tuple[gen.Groups, np.ndarray]:
    if variant == "G1":
        return gen.g1(ci, d, w, SCOPE, min_link=min_link, want_members=want_members)
    if variant == "G1-tg":
        return gen.g1(ci, d, w, SCOPE, types=G1_TG_TYPES, min_link=min_link,
                      want_members=want_members)
    if variant == "G3":
        return gen.g3(ci, d, w, SCOPE, min_link=min_link, want_members=want_members)
    if variant.startswith("G4-"):
        return gen.g4(ci, d, w, SCOPE, float(variant.split("-")[1]), min_link=min_link,
                      want_members=want_members)
    raise ValueError(variant)


def threshold_curves(ci: gen.CorpusIndex, windows: tuple[int, ...],
                     variants: tuple[str, ...] = WEIGHTED_VARIANTS) -> dict[str, Any]:
    """V(w, t) for every integer threshold t = 1 .. (strongest emitted link + 1), plus the
    `T_GRID` levels (Rule T: a group is emitted only if its strongest pairwise link
    L >= t). V is non-increasing in t and 0 above the strongest link, so the scan holds
    the smallest t with V <= any bound. Keys: `<variant>|<w>`."""
    nad = ci.n_account_days()
    out: dict[str, Any] = {}
    for v in variants:
        for w in windows:
            smax = 0.0
            for d in ci.days:
                g, L = _weighted(ci, v, int(d), w, 1, True)
                for m in g.members:
                    smax = max(smax, gen.group_strength(L, m))
            levels = sorted(set(range(1, int(smax) + 2)) | set(T_GRID))
            curve = {}
            for t in levels:
                rev, ng = [], 0
                for d in ci.days:
                    g = _weighted(ci, v, int(d), w, t, False)[0]
                    rev.append(g.review)
                    ng += len(g.sizes)
                r = np.unique(np.concatenate(rev)) if rev else np.zeros(0)
                curve[t] = {"review_pairs": int(len(r)), "n_groups": int(ng),
                            "groups_per_day_mean": ng / len(ci.days) if len(ci.days)
                            else float("nan"),
                            "V": len(r) / nad if nad else float("nan")}
            out[f"{v}|{w}"] = {"variant": v, "w": w, "max_group_strength": smax,
                               "n_account_days": nad, "n_days_evaluated": int(len(ci.days)),
                               "levels": levels, "curve": curve}
    return out


def g6_volume(ci: gen.CorpusIndex, windows: tuple[int, ...], B: float = FORK_BUDGET
              ) -> dict[str, Any]:
    """G6 volume (part 1 section 5: 'by construction the budget'): for a unit seed at each
    active account s on day d, the top-max(1, floor(B N_active(d))) accounts by S are
    surfaced, but only accounts with S > 0 can be; V_G6(w) = mean over seeds of
    min(#{c : S(s, c) > 0}, cap) / N_active(d)."""
    out: dict[str, Any] = {}
    for w in windows:
        vals: list[float] = []
        at_cap: list[bool] = []
        for d in ci.days:
            d = int(d)
            S = gen.g6_scores(gen.interaction_w(gen.window_touches(ci, d, w, SCOPE), ci.n))
            act = np.flatnonzero(ci.active[d])
            n_act = len(act)
            if n_act == 0:
                continue
            cap = gen.budget_cap(B, n_act)
            npos = (S[act] > 0).sum(axis=1)
            vals.extend((np.minimum(npos, cap) / n_act).tolist())
            at_cap.extend((npos >= cap).tolist())
        out[w] = {"V": float(np.mean(vals)) if vals else float("nan"), "B": B,
                  "n_seeds": len(vals),
                  "share_seeds_at_cap": float(np.mean(at_cap)) if at_cap else float("nan")}
    return out


def touch_coverage(df: pd.DataFrame, parsed: list[dict], tdf: pd.DataFrame,
                   fork_erratum: bool = True) -> list[dict]:
    """Per successful (service, action): events, and events that yield at least one touch
    (write / read) or container row; actions outside the touch table are listed too."""
    ok = (df["exit_code"].to_numpy() == 0)
    ev_cnt = Counter(f"{s}.{a}" for s, a, g in zip(df["service"], df["action"], ok) if g)
    t = tdf.drop_duplicates(["ev", "kind"])
    hit: dict[str, Counter] = defaultdict(Counter)
    for sa, kind in zip(t["service"] + "." + t["action"], t["kind"]):
        hit[sa][kind] += 1
    rows = []
    for sa, n in sorted(ev_cnt.items()):
        svc, act = sa.split(".", 1)
        rules = mc.rules_for(svc, act, fork_erratum)
        desc = "; ".join(
            f"{rule.kind} {rule.type}{'/' + rule.sub if rule.sub else ''}: "
            f"{'/'.join(rule.keys) or ''}"
            f"{('result_meta.' + '/'.join(rule.meta_keys)) if rule.meta_keys else ''}"
            f"{'' if (rule.keys or rule.meta_keys) else '-'}"
            f"{' (' + rule.mode + ')' if rule.mode != 'first' else ''}"
            f"{' [fork only]' if rule.fork_only else ''}" for rule in rules)
        rows.append({"action": sa, "events": int(n), "rule": desc or None,
                     "events_with_touch": int(sum(hit[sa].values())),
                     "touch_rows": int((tdf["service"] + "." + tdf["action"] == sa).sum())})
    return rows


def run_fork(path: str, template: mc.OrgTemplate, fork_erratum: bool = True
             ) -> dict[str, Any]:
    t0 = time.time()
    p = Path(path)
    label = p.name[:-len(".jsonl")] if p.name.endswith(".jsonl") else p.stem
    df = mc.load_fork_audit(p)
    with mc.fork_scope():   # fork corpus: the released-only lower-case-id switch is ignored
        return _run_fork_body(p, label, df, template, fork_erratum, t0)


def _run_fork_body(p: Path, label: str, df: pd.DataFrame, template: mc.OrgTemplate,
                   fork_erratum: bool, t0: float) -> dict[str, Any]:
    import hashlib
    parsed, fails = mc.parse_args_column(df["args"])
    keys = mc.key_usage_table(df, parsed)
    meta_keys = mc.key_usage_table(df, list(df["result_meta"]))
    tdf = mc.touches(df, parsed, include_fork_only=True, fork_erratum=fork_erratum)
    rdf = mc.records(df, parsed, fork_erratum=fork_erratum)
    adf = mc.account_days(df)
    ci = gen.build_index(label, tdf, rdf, adf, template, cache_dir=None, log=mc.eprint,
                         day_rank=True)
    n_days = len(ci.day_list)
    windows = tuple(w for w in FORK_WINDOWS if w <= n_days)
    dropped = [w for w in FORK_WINDOWS if w > n_days]
    vb = volume_block(ci, windows, with_density=True, variants=FORK_VARIANTS,
                      union_w=max(windows))
    mc.eprint(f"[{label}] volumes done ({time.time()-t0:.1f}s)")
    tail = g2_tail(ci, windows)
    curves = threshold_curves(ci, windows)
    mc.eprint(f"[{label}] threshold curves done ({time.time()-t0:.1f}s)")
    g6v = g6_volume(ci, windows)
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    return {"corpus": label, "corpus_path": _rel(p), "corpus_sha256": h,
            "n_days": n_days, "days": list(ci.day_list),
            "windows": list(windows), "windows_dropped_longer_than_corpus": dropped,
            "n_accounts_active": int(ci.active.any(axis=0).sum()),
            "n_active_per_day": [ci.n_active(int(d)) for d in range(n_days)],
            "n_account_days": ci.n_account_days(),
            "n_events": int(len(df)), "n_success_events": int((df["exit_code"] == 0).sum()),
            "args_parse_failures": fails, "ordering": df.attrs.get("fork_ordering", {}),
            "volumes": vb, "g2_tail": tail, "threshold_curves": curves, "g6_volume": g6v,
            "keys": {k: dict(v) for k, v in keys.items()},
            "result_meta_keys": {k: dict(v) for k, v in meta_keys.items()},
            "fork_touch_table": "part2-erratum" if fork_erratum else "part1",
            "touch_coverage": touch_coverage(df, parsed, tdf, fork_erratum),
            "diagnostics": ci.diagnostics, "runtime_s": round(time.time() - t0, 1)}


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(PROJECT))
    except ValueError:
        return str(p)


def render_fork(r: dict[str, Any], cmd: str) -> str:
    cap = f"_Script: `work/checks/haystack.py` (fork mode); command: `{cmd}`._"
    ws = r["windows"]
    out = [f"## B1 on the fork corpus `{r['corpus']}`\n",
           f"`{r['corpus_path']}` (sha256 `{r['corpus_sha256'][:16]}...`): {r['n_days']} days "
           f"({', '.join(r['days'])}), {r['n_accounts_active']} active accounts, "
           f"{r['n_account_days']} active account-days (per day: "
           f"{', '.join(map(str, r['n_active_per_day']))}), {r['n_success_events']:,} successful "
           f"of {r['n_events']:,} events. Like-for-like scope, fork-only touches included; "
           f"touch table: **{r['fork_touch_table']}**"
           + (" (part 2 draft section 2 fork erratum: result_meta ids for create_issue, "
              "submit_eval job, register_checkpoint, create/update_config; submit_eval "
              "config_id and checkpoint_id; run_reference_suite checkpoint_id)"
              if r["fork_touch_table"] == "part2-erratum" else "") + ". "
           f"Windows: trailing w in {{{', '.join(map(str, ws))}}} corpus days (day index = rank "
           f"of the date), truncated at day 1"
           + (f"; w = {', '.join(map(str, r['windows_dropped_longer_than_corpus']))} dropped "
              f"(longer than the corpus, identical to w = {r['n_days']})"
              if r["windows_dropped_longer_than_corpus"] else "") + ".\n",
           f"Ordering: {mc.FORK_ORDERING_RULE}. Checks: "
           f"{r['ordering'].get('account_days_ts_non_monotone_in_file_order')} of "
           f"{r['ordering'].get('n_account_days')} account-days have `ts` decreasing in file "
           f"order; {r['ordering'].get('account_days_real_ts_raw_non_monotone_in_file_order')} "
           f"have the generator's `real_ts` decreasing; days decrease in file order "
           f"{r['ordering'].get('day_decreases_in_file_order')} times.\n"]
    out.append("### F-T1. Groups per day, size, volume V, fit (B/2 = 0.05 is Rule W's bound)\n")
    out.append(cap + "\n")
    rows = []
    for w in ws:
        for v in FORK_VARIANTS:
            g = r["volumes"]["groups"][w][v]
            rows.append([v, w, f(g["groups_per_day_mean"], 1), g["n_groups"], f(g["size_mean"], 2),
                         f(g["size_p50"], 0), f(g["size_p90"], 1), g["size_max"],
                         g["review_pairs"], f(g["V"], 4), f(g["V"] <= 0.02),
                         f(g["V"] <= 0.05), f(g["V"] <= 0.10)])
        g6 = r["g6_volume"][w]
        am = r["volumes"]["g6"][w]
        rows.append(["G6", w, "-", "-", "-", "-", "-", "-", "-", f(g6["V"], 4),
                     f(g6["V"] <= 0.02), f(g6["V"] <= 0.05), f(g6["V"] <= 0.10)])
    out.append(table(["generator", "w", "groups/day", "groups", "size mean", "size p50",
                      "size p90", "size max", "review pairs", "V", "fits 0.02", "fits 0.05",
                      "fits 0.10"], rows) + "\n")
    out.append("G1-tg is G1 restricted to tickets and groups. G6 V = mean over unit seeds of "
               "min(#accounts with S > 0, max(1, floor(0.10 N_active(d)))) / N_active(d).\n")
    rows = [[w, f(r["volumes"]["g6"][w]["mean_accounts_S_pos"], 1),
             f(r["volumes"]["g6"][w]["p90_accounts_S_pos"], 0), r["volumes"]["g6"][w]["n_seeds"]]
            for w in ws]
    out.append("G6 honest amplification (accounts with S > 0 per seed):\n\n" +
               table(["w", "mean", "p90", "seeds"], rows) + "\n")

    out.append("### F-T2. Rule T curves: V at link threshold t (groups with strongest "
               "pairwise link >= t)\n")
    out.append(cap + "\n")
    rows = []
    for key, c in r["threshold_curves"].items():
        cells = [f"{f(c['curve'][t]['V'], 4)} ({c['curve'][t]['n_groups']})" for t in T_GRID]
        fit = [t for t in c["levels"] if c["curve"][t]["V"] <= 0.05]
        rows.append([c["variant"], c["w"], f(c["max_group_strength"], 0)] + cells +
                    [min(fit) if fit else "-"])
    out.append(table(["generator", "w", "max strength"] + [f"V t={t} (groups)" for t in T_GRID]
                     + ["smallest t with V <= 0.05"], rows) + "\n")

    out.append("### F-T3. Honest pair-interaction density by artefact type "
               "(share of unordered pairs of active accounts)\n")
    out.append(cap + "\n")
    uw = max(ws)
    rows = []
    for t in list(mc.LIKE_TYPES) + ["any"]:
        row = [t]
        for w in ws:
            dd = r["volumes"]["density"][w][t]
            row += [f(dd["L1_mean"]), f(dd["W_mean"])]
        dd = r["volumes"]["density"][uw][t]
        row += [f(dd.get("L1_union")), f(dd.get("W_union"))]
        rows.append(row)
    head = ["type"]
    for w in ws:
        head += [f"w={w} L1>0 (day mean)", f"w={w} W>0 (day mean)"]
    head += [f"w={uw} L1>0 (whole corpus)", f"w={uw} W>0 (whole corpus)"]
    out.append(table(head, rows) + "\n")

    out.append("### F-T4. G2 right tail (F3' closure)\n")
    out.append(cap + "\n")
    rows = []
    for variant in ("strict", "loose"):
        for w in ws:
            t = r["g2_tail"][f"{variant}|{w}"]
            rows.append([variant, w, t["n_handoffs"], t["n_pairs"], f(t["L2_p50"], 0),
                         f(t["L2_p90"], 1), f(t["L2_p99"], 1), t["L2_max"],
                         f(t["share_R_is_ticket"], 2), t["n_B_actions"], f(t["mult_mean"], 2),
                         f(t["mult_p90"], 1), t["mult_max"], f(t["share_mult_ge2"], 2)])
    out.append(table(["G2", "w", "handoffs", "ordered pairs >= 1", "L2 p50", "L2 p90", "L2 p99",
                      "L2 max", "share R = read ticket", "B-actions", "multiplicity mean",
                      "mult. p90", "mult. max", "share mult >= 2"], rows) + "\n")
    rows = []
    for w in ws:
        u = r["g2_tail"][f"unrequested|{w}"]
        bt = u["by_type"]
        rows.append([w, u["n_write_touches"], f(u["rate"])] +
                    [f"{f(bt[t]['rate'])} ({bt[t]['n']})" if t in bt else "-"
                     for t in mc.LIKE_TYPES])
    out.append("Unrequested-action rate (per type: rate (n)):\n\n" +
               table(["w", "write touches", "rate"] + list(mc.LIKE_TYPES), rows) + "\n")

    out.append("### F-T5. Argument-key usage for the touch-table actions (successful events)\n")
    out.append(cap + "\n")
    out.append(key_table({r["corpus"]: r}) + "\n")
    rows = [[x["action"], x["events"], x["rule"] or "(not in the touch table)",
             x["events_with_touch"], x["touch_rows"]] for x in r["touch_coverage"]]
    out.append(f"Touch coverage per successful action (events yielding a touch or container "
               f"row; touch table {r['fork_touch_table']}, fork-only rules on):\n\n" +
               table(["service.action", "events", "rules", "events with touch", "touch rows"],
                     rows) + "\n")
    rows = []
    for a, ks in sorted(r["keys"].items()):
        svc, act = a.split(".", 1)
        if mc.rules_for(svc, act, r["fork_touch_table"] == "part2-erratum"):
            continue
        rows.append([a, ks.get("__events__", 0),
                     ", ".join(f"`{k}` {n}" for k, n in sorted(ks.items()) if k != "__events__")])
    out.append("Actions outside the touch table (keys and counts):\n\n" +
               table(["service.action", "events", "keys"], rows) + "\n")
    out.append(f"Runtime: {r['runtime_s']} s.\n")
    return "\n".join(out)


def fork_result(path: str, template: mc.OrgTemplate, cmd: str, fork_erratum: bool = True
                ) -> tuple[dict[str, Any], str]:
    """The fork-mode JSON document and its markdown tables (what --out / --md receive)."""
    r = run_fork(path, template, fork_erratum)
    tables = render_fork(r, cmd)
    res = {"spec": ("work/mole-fork/protocol/TRACK-B.md part 1 sections 1, 2, 5 on a fork "
                    "corpus; TRACK-B-part2-draft.md section 2 (Rules W and T inputs)"),
           "script": "work/checks/haystack.py", "mode": "fork", "command": cmd,
           "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "scope": SCOPE, "variants": list(FORK_VARIANTS),
           "weighted_variants": list(WEIGHTED_VARIANTS), "t_grid": list(T_GRID),
           "g1_tg_types": list(G1_TG_TYPES), "budget": FORK_BUDGET,
           "window_semantics": ("trailing corpus days (day index = rank of the date) "
                                "d-w+1..d, truncated at day 1"),
           "ordering_rule": mc.FORK_ORDERING_RULE, "include_fork_only": True,
           "fork_touch_table": r["fork_touch_table"], "fork": r}
    return res, tables


def main_fork(args: argparse.Namespace) -> None:
    if not args.out or Path(args.out).resolve() == DEFAULT_OUT.resolve():
        raise SystemExit("--fork-corpus needs an explicit --out (not the released B1 path)")
    template = mc.load_org_template(args.template)
    cmd = (f"python -I work/checks/haystack.py --fork-corpus {_rel(Path(args.fork_corpus))} "
           f"--out {_rel(Path(args.out))}" +
           (f" --md {_rel(Path(args.md))}" if args.md else "") +
           (" --part1-touch-table" if args.part1_touch_table else ""))
    res, tables = fork_result(args.fork_corpus, template, cmd,
                              fork_erratum=not args.part1_touch_table)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, default=lambda o: o.item() if hasattr(o, "item")
                                         else str(o)))
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text(tables)
    print(tables)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-dir", default=None,
                    help="released-corpus mode: the upstream data directory")
    ap.add_argument("--fork-corpus", default=None,
                    help="fork mode: absolute path of a fork audit .jsonl (exclusive with "
                         "--data-dir); needs --out, optional --md")
    ap.add_argument("--md", default=None, help="fork mode: write the markdown tables here")
    ap.add_argument("--part1-touch-table", action="store_true",
                    help="fork mode sensitivity: part 1 touch table only (no fork erratum)")
    ap.add_argument("--corpus", action="append", default=[])
    ap.add_argument("--all-corpora", action="store_true")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--fig", default=str(DEFAULT_FIG))
    ap.add_argument("--cache-dir", default=str(DEFAULT_CACHE))
    ap.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    ap.add_argument("--windows", default="1,3,7")
    ap.add_argument("--scaling-corpora", default="all",
                    help="comma list of corpora to run N-scaling on, or 'all'")
    ap.add_argument("--sensitivity-v1", action="store_true",
                    help="post-hoc sensitivity v1 (not pre-registered): errata items 1, 2, 3, 12")
    ap.add_argument("--lowercase-ids", action="store_true",
                    help="released-corpus mode only, post-hoc (TRACK-B part 1 errata item 2, "
                         "not bundled with --sensitivity-v1): create_issue explicit id matched "
                         "case-insensitively, prefix may contain hyphens (deepa-a1-214)")
    ap.add_argument("--tables-out", default=None)
    args = ap.parse_args()
    if args.fork_corpus:
        if (args.data_dir or args.corpus or args.all_corpora or args.sensitivity_v1
                or args.lowercase_ids):
            ap.error("--fork-corpus excludes --data-dir / --corpus / --all-corpora / "
                     "--sensitivity-v1 / --lowercase-ids")
        main_fork(args)
        return
    if not args.data_dir:
        ap.error("--data-dir (released corpora) or --fork-corpus (fork mode)")
    if args.sensitivity_v1:
        mc.set_sensitivity_v1(True)
        if args.out == str(DEFAULT_OUT):
            args.out = str(DEFAULT_OUT).replace(".json", ".sensitivity-v1.json")
        if args.fig == str(DEFAULT_FIG):
            args.fig = str(DEFAULT_FIG).replace(".png", ".sensitivity-v1.png")
    if args.lowercase_ids:
        mc.set_lowercase_ids(True)
        # never write over the frozen primary / sensitivity-v1 outputs
        if args.out.endswith(".json") and ".lowercase-ids." not in args.out:
            args.out = args.out[:-len(".json")] + ".lowercase-ids.json"
        if args.fig.endswith(".png") and ".lowercase-ids." not in args.fig:
            args.fig = args.fig[:-len(".png")] + ".lowercase-ids.png"
    args.windows = [int(x) for x in args.windows.split(",")]
    corpora = list(mc.CORPORA) if args.all_corpora else args.corpus
    if not corpora:
        ap.error("--corpus or --all-corpora")
    scal = set(corpora) if args.scaling_corpora == "all" else set(args.scaling_corpora.split(","))
    cmd = "python -I work/checks/haystack.py --data-dir work/upstream-data " + (
        "--all-corpora" if args.all_corpora else " ".join(f"--corpus {c}" for c in corpora)) + \
        " --out work/stage2/b1-haystack.json --fig work/stage2/fig-n-scaling.png" + \
        (" --sensitivity-v1 (out: *.sensitivity-v1.*)" if args.sensitivity_v1 else "") + \
        (" --lowercase-ids (out: *.lowercase-ids.*)" if args.lowercase_ids else "")
    template = mc.load_org_template(args.template)
    t0 = time.time()
    results: dict[str, Any] = {}
    for c in corpora:
        results[c] = run_corpus(args, c, template, c in scal)
        mc.eprint(f"[{c}] B1 corpus runtime {results[c]['runtime_s']}s")
    gate = gate_b(results, args.windows)
    tables = render(results, gate, cmd, args.windows)
    if args.sensitivity_v1:
        tables = "> **POST-HOC SENSITIVITY v1, NOT PART OF THE PRE-REGISTERED GATE.** Switched on together: (1) windows counted in active corpus days (day index) instead of calendar days; (2) `create_issue` explicit id matched case-insensitively as `<prefix>-<N>` (prefix `[A-Za-z][A-Za-z0-9]*`) at the start of `name`; (3) `ticket_id` (and `issue_id` / `identifier` on `create_issue`) accepted as ticket keys on comment / transition / update / create; (4) one trailing `.` or `:` stripped from tokens before G2 identifier matching. The gate statements printed below are what A / B would be under this variant; the recorded gate uses the primary (literal) run.\n" + "\n" + tables
    if args.lowercase_ids:
        tables = "> **POST-HOC LOWER-CASE TICKET IDS (TRACK-B part 1 errata item 2), NOT PART OF THE PRE-REGISTERED GATE.** `create_issue` explicit id matched as `<prefix>-<N>` at the start of `name`, case-insensitive, prefix may contain hyphens (`^\\s*([A-Za-z][A-Za-z0-9-]*-[0-9]+)(?![A-Za-z0-9_-])`, e.g. `deepa-a1-214`). Released-corpus mode only; not bundled with sensitivity v1.\n" + "\n" + tables
    res = {"spec": "work/mole-fork/protocol/TRACK-B.md part 1 (commit 0cfe331), section 5",
           "script": "work/checks/haystack.py", "command": cmd,
           "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "windows": args.windows, "scope": SCOPE, "variants": list(B1_VARIANTS),
           "n_scaling": {"N": [n for n, _ in N_SCALING], "seeds": SEED0,
                         "windows": list(N_WINDOWS)},
           "window_semantics": ("active corpus days (index) d-w+1..d" if args.sensitivity_v1
                                else "calendar days d-w+1..d"),
           "sensitivity_v1": bool(args.sensitivity_v1),
           "runtime_s_total": round(time.time() - t0, 1), "gate_B": gate,
           "corpora": results}
    if args.lowercase_ids:
        res["lowercase_ids"] = True
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, default=lambda o: o.item() if hasattr(o, "item")
                                         else str(o)))
    figure(results, args.fig)
    if args.tables_out:
        Path(args.tables_out).write_text(tables)
    print(tables)
    mc.eprint(f"B1 total runtime {res['runtime_s_total']}s; gate B = {gate['B']}")


if __name__ == "__main__":
    main()
