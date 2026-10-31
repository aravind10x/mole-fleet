#!/usr/bin/env python3
"""Brief 19 (B4 sizing, Part B; $0): the anchor inventory for script insertions on `prefix_rw_v3rc`, and
the power simulation for B4's cross-document 2×2 (cells (1,1), (1,2), (2,2) and a same-shape control arm).

Inventory (counts, ids, days and paths only; no document line, no item value). For each SHARED item and
day, the insertion boundaries are the day's start and the point just after each of the day's successful
content writes to either of the item's two documents (the pair's own write stream, file order). The
anchor condition for a script insertion (brief 19 B4): both of the item's lines present in their
documents' states at the boundary, by name (`stage3_b4r.item_line`, primary) or by name or one of the
row's Z5 entities (`stage3_b4r.row_entities`, sensitivity), and the pair a read-together group with
maintenance support (constraint 5). Beside: the v3 inserter's whole-write floor (F4: a boundary before
the day's last whole rewrite of either document is refused), the accounts that could carry an insertion
(not a manager, in both documents' write teams, a session overlapping a qualifying boundary), and the
honest edits of the item's line after each qualifying boundary (which the windows of B4-R's view
construction then see as an overwrite).

Simulation (no data read): seeded; 300 experiments per design; flags drawn at each view's recall at
its sealed 0.10 threshold; placements of one test change share a beta propensity with the stated ICC;
item reuse adds an item-level beta propensity (a cluster); payload-clustered percentile bootstrap,
1,000 replicates, or a two-stage bootstrap (items, then test changes within item) when items are reused;
each contrast read under the four-outcome table on the 0.3 margin, after the headroom clause on its
carrying view (below headroom: "floor").

    work/mole-fork/.venv/bin/python -I work/checks/stage3_b4_power.py inventory \\
        --corpus work/mole-fork/data/corpus/spike/prefix_rw_v3rc.jsonl --out-json INV.json
    work/mole-fork/.venv/bin/python -I work/checks/stage3_b4_power.py simulate --out-json SIM.json
    work/mole-fork/.venv/bin/python -I work/checks/stage3_b4_power.py render --inventory INV.json \\
        --sim SIM.json --out-md TABLES.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_b4r as b4r  # noqa: E402
import stage3_b4r_design as dz  # noqa: E402

VERSION = "b4-power/v1"
SEED = 20261190
SIMS, REPS = 300, 1000
MARGIN = 0.3
OUTCOMES = ("floor", "present", "attenuated", "excluded", "inconclusive")
CORPUS_SHA = "d846524462d00fb6f96c8a019b07b6b55646cf1055bf36eb23ebf5f288cd34e9"
PROJECT = HERE.parent.parent
GROUPS_FILE = PROJECT / "work" / "stage3" / "b4r" / "groups-v3.json"
VALUE_TABLE = PROJECT / "work" / "stage3" / "b4r" / "value-table-v7b.json"
VALUE_CLASSES = {"contact", "path", "label"}       # B4-R Z5: the classes a value change may anchor on
MODES = ("name", "entity", "inserter_floor")
_WS = re.compile(r"\s+")


# ── the partition and the headroom clause ────────────────────────────────────

def four_outcome(lo: float, hi: float, point: float, margin: float = MARGIN) -> str:
    """The round-6 partition (theory pre-registration section 3)."""
    if lo > 0 and point >= margin:
        return "present"
    if lo > 0:
        return "attenuated"
    if hi < margin:
        return "excluded"
    return "inconclusive"


def at_headroom(lb_cell: float, ub_control: float, margin: float = MARGIN) -> bool:
    """The floor clause: the cell's lower bound exceeds the control's upper bound by at least `margin`."""
    return lb_cell - ub_control >= margin - 1e-12


def read_contrast(lo: float, hi: float, point: float, at_head: bool) -> str:
    return four_outcome(lo, hi, point) if at_head else "floor"


# ── the generating model ─────────────────────────────────────────────────────

def _beta(rng: np.random.Generator, mean: Any, icc: float, size: int) -> np.ndarray:
    mean = np.clip(np.broadcast_to(np.asarray(mean, float), (size,)), 1e-6, 1 - 1e-6)
    if icc <= 0:
        return mean.copy()
    k = (1 - icc) / icc
    return rng.beta(np.maximum(mean * k, 1e-3), np.maximum((1 - mean) * k, 1e-3))


def item_assignment(n: int, items: int) -> np.ndarray:
    """Test changes to items round-robin (balanced to within one)."""
    return np.arange(n) % items


def draw_arm(rng: np.random.Generator, p: float, n: int, pl: int, icc: float,
             item_of: np.ndarray | None = None, icc_item: float = 0.0) -> np.ndarray:
    """n test changes × pl placements of flags. A test change's placements share a propensity drawn
    Beta(mean, ICC icc); with items, the mean is the item's own propensity, Beta(p, ICC icc_item)."""
    if item_of is not None and icc_item > 0:
        means = _beta(rng, p, icc_item, int(item_of.max()) + 1)[item_of]
    else:
        means = np.full(n, p, float)
    prop = _beta(rng, means, icc, n)
    return rng.random((n, pl)) < prop[:, None]


def grid_flags(rng: np.random.Generator, prop: np.ndarray, threshold: int = 60, step: int = 5,
               p_tie: float = 0.5) -> np.ndarray:
    """Flags read from scores on a `step`-point grid under the randomised tie rule (flag above the
    threshold; at it with probability p_tie): each unit's score puts mass b at the threshold and the
    rest above or below so that P(flag) equals its propensity."""
    prop = np.asarray(prop, float)
    b = np.minimum(0.2, 2 * np.minimum(prop, 1 - prop))
    above = prop - p_tie * b
    u = rng.random(prop.shape)
    grid_above = np.arange(threshold + step, 101, step)
    grid_below = np.arange(0, threshold, step)
    score = np.where(u < above, rng.choice(grid_above, prop.shape),
                     np.where(u < above + b, threshold, rng.choice(grid_below, prop.shape)))
    return (score > threshold) | ((score == threshold) & (rng.random(prop.shape) < p_tie))


# ── the bootstraps ───────────────────────────────────────────────────────────

def item_weights(rng: np.random.Generator, m: int, reps: int) -> np.ndarray:
    """Per replicate, how many times each item is drawn (items resampled with replacement)."""
    return rng.multinomial(m, np.full(m, 1 / m), size=reps)


def resample_counts(rng: np.random.Generator, n: int, reps: int, item_of: np.ndarray | None = None,
                    w: np.ndarray | None = None) -> np.ndarray:
    """reps × n resampling counts over test changes: payload-clustered, or (with item weights `w`)
    two-stage: each drawn item's test changes resampled within it."""
    if w is None:
        return rng.multinomial(n, np.full(n, 1 / n), size=reps).astype(float)
    c = np.zeros((w.shape[0], n))
    for i in range(w.shape[1]):
        js = np.flatnonzero(item_of == i)
        if len(js):
            c[:, js] = rng.multinomial(len(js), np.full(len(js), 1 / len(js)), size=w.shape[0]) * w[:, [i]]
    return c


def boot_means(counts: np.ndarray, flags: np.ndarray) -> np.ndarray:
    """Replicate means over plants (every test change has the same number of placements)."""
    x = flags.mean(axis=1)
    return (counts @ x) / counts.sum(axis=1)


def boot_payload(rng: np.random.Generator, flags: np.ndarray, reps: int) -> np.ndarray:
    return boot_means(resample_counts(rng, flags.shape[0], reps), flags)


def boot_two_stage(rng: np.random.Generator, flags: np.ndarray, item_of: np.ndarray, w: np.ndarray) -> np.ndarray:
    return boot_means(resample_counts(rng, flags.shape[0], w.shape[0], item_of, w), flags)


def _pct(x: np.ndarray) -> tuple[float, float]:
    lo, hi = np.percentile(x, [2.5, 97.5])
    return float(lo), float(hi)


# ── the simulation ───────────────────────────────────────────────────────────

def _truths(base: float, deltas: Sequence[float], implied: float) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for d in deltas:
        t = base - d
        out[f"{d:g}"] = t if t >= 0 else None
    out["implied"] = implied
    return out


def simulate(design: Mapping[str, Any], pri: Mapping[str, Any], sims: int = SIMS, reps: int = REPS,
             seed: int = SEED) -> dict[str, Any]:
    """One design (n test changes per cell, pl placements, ICC, optional item reuse) under one prior set.
    Every contrast's tallies are fractions of experiments in the five outcomes; a truth the prior cannot
    reach (a negative recall) is None."""
    n, pl, icc = int(design["n"]), int(design["pl"]), float(design["icc"])
    items = design.get("items")
    icc_item = float(design.get("icc_item", 0.0))
    two_stage = design.get("boot", "payload") == "two_stage" and items
    grid = design.get("gen", "flag") == "grid"
    item_of = item_assignment(n, items) if items else None
    rng = np.random.default_rng(seed)

    e_od, e_d = pri["e_odiff"], pri["e_doss"]
    frag_t = _truths(pri["r11"], (0.3, 0.45), 1 - (1 - e_od) ** 2)
    split_t = _truths(pri["d12"], (0.0, 0.3, 0.45), 1 - (1 - e_d) ** 2)
    shifts = tuple(pri.get("ws_shift", (-0.15, 0.0, 0.15)))
    ws_w = {s: float(np.clip(pri["r11"] + s, 0.01, 0.99)) for s in shifts}
    ws_t = {s: _truths(ws_w[s], (0.3,), 1 - (1 - e_d) ** 2) for s in shifts}

    tally: dict[str, dict[str, dict[str, int] | None]] = {
        "C_frag": {k: (None if v is None else dict.fromkeys(OUTCOMES, 0)) for k, v in frag_t.items()},
        "C_split": {k: (None if v is None else dict.fromkeys(OUTCOMES, 0)) for k, v in split_t.items()}}
    for s in shifts:
        tally[f"C_ws_{s:g}"] = {k: (None if v is None else dict.fromkeys(OUTCOMES, 0)) for k, v in ws_t[s].items()}
    head = {"O_diff_11": 0, "dossier_12": 0, **{f"O_ws_22_{s:g}": 0 for s in shifts}}

    def arm(p: float) -> np.ndarray:
        if grid:
            means = (_beta(rng, p, icc_item, int(item_of.max()) + 1)[item_of]
                     if item_of is not None and icc_item > 0 else np.full(n, p))
            prop = _beta(rng, means, icc, n)
            return grid_flags(rng, np.repeat(prop[:, None], pl, axis=1))
        return draw_arm(rng, p, n, pl, icc, item_of, icc_item)

    for _ in range(sims):
        w = item_weights(rng, items, reps) if two_stage else None

        def counts() -> np.ndarray:
            return resample_counts(rng, n, reps, item_of, w)

        def lb_ub(flags: np.ndarray) -> tuple[float, float]:
            return _pct(boot_means(counts(), flags))

        def contrast(hi_arm: np.ndarray, lo_arm: np.ndarray, paired: bool) -> tuple[float, float, float]:
            c1 = counts()
            c2 = c1 if paired else counts()
            lo, hi = _pct(boot_means(c1, hi_arm) - boot_means(c2, lo_arm))
            return lo, hi, float(hi_arm.mean() - lo_arm.mean())

        _, ub_od = lb_ub(arm(pri["q_odiff"]))
        _, ub_d = lb_ub(arm(pri["q_doss"]))
        _, ub_w = lb_ub(arm(pri["q_ws"]))

        a11 = arm(pri["r11"])
        h = at_headroom(lb_ub(a11)[0], ub_od)
        head["O_diff_11"] += h
        for k, t in frag_t.items():
            if t is not None:
                tally["C_frag"][k][read_contrast(*contrast(a11, arm(t), False), h)] += 1

        d12 = arm(pri["d12"])
        h = at_headroom(lb_ub(d12)[0], ub_d)
        head["dossier_12"] += h
        for k, t in split_t.items():
            if t is not None:
                tally["C_split"][k][read_contrast(*contrast(d12, arm(t), False), h)] += 1

        for s in shifts:
            w22 = arm(ws_w[s])
            h = at_headroom(lb_ub(w22)[0], ub_w)
            head[f"O_ws_22_{s:g}"] += h
            for k, t in ws_t[s].items():
                if t is not None:
                    tally[f"C_ws_{s:g}"][k][read_contrast(*contrast(w22, arm(t), True), h)] += 1

    frac = {c: {k: (None if v is None else {o: round(x / sims, 4) for o, x in v.items()}) for k, v in tb.items()}
            for c, tb in tally.items()}
    return {"design": {"n": n, "pl": pl, "plants_per_cell": n * pl, "icc": icc, "items": items,
                       "icc_item": icc_item, "boot": "two_stage" if two_stage else "payload",
                       "gen": "grid" if grid else "flag"},
            "truths": {"C_frag": frag_t, "C_split": split_t, **{f"C_ws_{s:g}": ws_t[s] for s in shifts}},
            "P_headroom": {k: round(v / sims, 4) for k, v in head.items()}, **frac,
            "sims": sims, "reps": reps, "seed": seed}


PRIMARY = (("C_frag", ("0.3", "0.45")), ("C_split", ("0", "0.3", "0.45")), ("C_ws_0", ("0.3",)))


def decidable(res: Mapping[str, Any]) -> dict[str, Any]:
    """P(a reading lands outside floor and inconclusive) at each named truth of each primary contrast;
    the minimum over them and where it sits. A truth the prior cannot reach is skipped."""
    vals = {}
    for c, truths in PRIMARY:
        for t in truths:
            tb = res[c].get(t)
            if tb is not None:
                vals[f"{c}|{t}"] = round(1 - tb["floor"] - tb["inconclusive"], 4)
    worst = min(vals, key=vals.get) if vals else None
    return {"by": vals, "min": vals[worst] if worst else None, "argmin": worst}


def min_recall_for_headroom(n: int, pl: int, icc: float, q: float, sims: int = SIMS, reps: int = REPS,
                            seed: int = SEED, target: float = 0.8) -> float | None:
    """The smallest recall on a 0.05 grid at which the cell reaches headroom over a control at q with
    probability at least `target` (independent test changes)."""
    for r in np.round(np.arange(0.30, 1.0001, 0.05), 2):
        rng = np.random.default_rng(seed)
        hits = 0
        for _ in range(sims):
            lb = _pct(boot_payload(rng, draw_arm(rng, float(r), n, pl, icc), reps))[0]
            ub = _pct(boot_payload(rng, draw_arm(rng, q, n, pl, icc), reps))[1]
            hits += at_headroom(lb, ub)
        if hits / sims >= target:
            return float(r)
    return None


# ── priors (recall at each view's 0.10 threshold; sources in PRIOR_SOURCES) ──

_BASE = {"ws_shift": (-0.15, 0.0, 0.15)}
PRIORS: dict[str, dict[str, Any]] = {
    "opus48_central": {**_BASE, "r11": 0.47, "e_odiff": 0.06, "q_odiff": 0.06, "d12": 0.53, "e_doss": 0.12,
                       "q_doss": 0.12, "q_ws": 0.06},
    "opus48_pessimistic": {**_BASE, "r11": 0.35, "e_odiff": 0.06, "q_odiff": 0.06, "d12": 0.40, "e_doss": 0.12,
                           "q_doss": 0.12, "q_ws": 0.06},
    "opus48_optimistic": {**_BASE, "r11": 0.875, "e_odiff": 0.06, "q_odiff": 0.06, "d12": 0.79, "e_doss": 0.12,
                          "q_doss": 0.12, "q_ws": 0.06},
    "opus48_live": {**_BASE, "r11": 0.47, "e_odiff": 0.06, "q_odiff": 0.06, "d12": 0.92, "e_doss": 0.15,
                    "q_doss": 0.15, "q_ws": 0.06},
    "sonnet_central": {**_BASE, "r11": 0.34, "e_odiff": 0.12, "q_odiff": 0.12, "d12": 0.36, "e_doss": 0.08,
                       "q_doss": 0.08, "q_ws": 0.12},
    "sonnet_optimistic": {**_BASE, "r11": 0.73, "e_odiff": 0.12, "q_odiff": 0.12, "d12": 0.71, "e_doss": 0.08,
                          "q_doss": 0.08, "q_ws": 0.12},
}
PRIOR_SOURCES = {
    "r11": "O_diff on the composed one-document cell: T1 v3 routine_redraw composed share (Sonnet 11/32 0.344, "
           "Opus 4.8 15/32 0.469; middle 0.344 / 0.594); optimistic = re-plant v1 composed share (0.734 / 0.875); "
           "Opus pessimistic 0.35 for B4-R's higher threshold (60 against 55)",
    "e_odiff": "O_diff on one routine end alone in a document: the same-shape sham's composed share (Sonnet "
               "v3 4/32 + re-plant 7/64 = 0.115; Opus 4.8 0/32 + 6/64 = 0.063); (1,2) implied = 1 - (1 - e)^2",
    "q_odiff": "the same-shape control under O_diff, per document unit: as e_odiff",
    "d12": "isolated dossier on (1,2) (one account holds both ends): B1 isolated lone recall, v3 pooled "
           "(Sonnet 13/36 0.36, Opus 4.8 19/36 0.53); optimistic = re-plant (0.71 / 0.79); Opus pessimistic 0.40 "
           "for B4-R's higher threshold (68 against 62); live = B1 Opus 4.8 live v3 33/36 0.92 at B1's "
           "threshold 40 (B4-R's is 58)",
    "e_doss": "the dossier on one routine end per account: B1's sham lone recall pooled over regimes (isolated "
              "Sonnet 5/60 0.083, Opus 4.8 7/60 0.117; live Opus 9/60 0.15); (2,2) implied = 1 - (1 - e)^2",
    "q_doss": "the same-shape control under the dossier: as e_doss",
    "q_ws": "the same-shape control under O_ws: as q_odiff (no O_ws prior exists)",
    "ws_shift": "O_ws on (2,2): no prior; O_diff's (1,1) value and 0.15 above and below (a sensitivity until the "
                "first scored batch)",
}


# ── the estimate (units per view per judge at B4-R's per-unit null costs) ────

NULL_COSTS = {  # view: (units, Sonnet $, Opus 4.8 $) from b4r-results.md's nulls table
    "P_author": (101, 0.33, 1.13), "O_diff": (388, 1.84, 9.41), "O_ws": (388, 2.67, 15.89),
    "O_ws_all": (388, 5.53, 29.68), "P_author_doc_iso": (38, 0.23, 1.70), "P_author_doc_live": (38, 0.32, 1.74)}
UNITS_PER_PLACEMENT = {  # per arm: units each view scores for one placement of one test change
    "11": {"O_diff": 1, "O_ws": 1, "O_ws_all": 1, "P_author_doc_iso": 1, "P_author_doc_live": 1, "P_author": 1},
    "12": {"O_diff": 2, "O_ws": 1, "O_ws_all": 1, "P_author_doc_iso": 1, "P_author_doc_live": 1, "P_author": 2},
    "22": {"O_diff": 2, "O_ws": 1, "O_ws_all": 1, "P_author_doc_iso": 2, "P_author_doc_live": 2, "P_author": 2},
    "control": {"O_diff": 2, "O_ws": 1, "O_ws_all": 1, "P_author_doc_iso": 1, "P_author_doc_live": 1, "P_author": 2},
    "21": {"O_diff": 1, "O_ws": 1, "O_ws_all": 1, "P_author_doc_iso": 2, "P_author_doc_live": 2, "P_author": 2},
}


def estimate(n: int, pl: int, include_21: bool = False) -> dict[str, Any]:
    arms = ["11", "12", "22", "control"] + (["21"] if include_21 else [])
    units = {v: n * pl * sum(UNITS_PER_PLACEMENT[a][v] for a in arms) for v in NULL_COSTS}
    by_view = {v: {"sonnet": round(units[v] * c[1] / c[0], 2), "opus48": round(units[v] * c[2] / c[0], 2)}
               for v, c in NULL_COSTS.items()}
    by_judge = {j: round(sum(x[j] for x in by_view.values()), 2) for j in ("sonnet", "opus48")}
    return {"n": n, "pl": pl, "arms": arms, "units": units,
            "dollars": {"by_view": by_view, "by_judge": by_judge, "total": round(sum(by_judge.values()), 2)}}


# ── supply ───────────────────────────────────────────────────────────────────

def supply(anchor_days: Mapping[str, Sequence[str]], n_cells: int = 3) -> dict[str, Any]:
    """Test changes per cell the anchors support: one test change per (item, day) anchor per cell. With
    reuse, every cell uses every anchor (an item shared by cells is a cluster); without, items are
    partitioned among the cells (best partition: the largest minimum). Two placements need two days of
    one item (different accounts and days)."""
    import itertools
    days = {i: len(set(d)) for i, d in anchor_days.items()}
    one = {i: d for i, d in days.items()}
    two = {i: d // 2 for i, d in days.items()}

    def best(per_item: Mapping[str, int]) -> int:
        items = list(per_item)
        if not items:
            return 0
        top = 0
        for lab in itertools.product(range(n_cells), repeat=len(items)):
            sums = [0] * n_cells
            for it, c in zip(items, lab):
                sums[c] += per_item[it]
            top = max(top, min(sums))
        return top
    return {"items": len(days), "anchors": sum(one.values()),
            "one_placement": {"reuse": sum(one.values()), "no_reuse": best(one)},
            "two_placements": {"reuse": sum(two.values()), "no_reuse": best(two)}}


# ── the inventory ────────────────────────────────────────────────────────────

def eligibility(row: Mapping[str, Any], groups: Sequence[Sequence[str]]) -> dict[str, bool]:
    """Constraint 5 (a read-together group with maintenance support; {README, on-call runbook} for the
    contact class only) and constraint 4 (a value change anchors on contact, path or label)."""
    pair = set(row["docs"])
    grouped = any(set(g) == pair for g in groups)
    if grouped and pair == {dz.README, dz.OC}:
        grouped = set(row["classes"]) == {"contact"}
    return {"grouped": grouped, "value_change": bool(set(row["classes"]) & VALUE_CLASSES)}


def _base_text(base: Mapping[Any, Any], p: str) -> str:
    b = base.get(("owncloud", p))
    return b if isinstance(b, str) else ""


def pair_events(rows: Sequence[Mapping[str, Any]], base: Mapping[Any, Any], pair: Sequence[str]) -> list[dict]:
    """Every successful content write to either document of the pair, in file order, with the state after it."""
    import stage3_views as sv
    out = []
    for p in pair:
        for c in sv.document_timeline(rows, p, base):
            out.append({"path": p, "ts": str(c.ts), "index": c.index, "action": c.action,
                        "after": c.after or ""})
    return sorted(out, key=lambda e: e["index"])


def boundaries(events: Sequence[Mapping[str, Any]], base: Mapping[Any, Any], pair: Sequence[str],
               day: str) -> list[dict]:
    """The day's insertion boundaries on the pair's write stream: the day's start, then just after each of
    the day's writes; each with its interval (`from`, `to`), both states and `pos` (the index in `events`
    of the last write applied, -1 for none)."""
    st = {p: _base_text(base, p) for p in pair}
    pos = -1
    for k, e in enumerate(events):
        if e["ts"][:10] < day:
            st[e["path"]] = e["after"]
            pos = k
    today = [(k, e) for k, e in enumerate(events) if e["ts"][:10] == day]
    ends = [e["ts"] for _, e in today] + [f"{day}T23:59:59.999999Z"]
    out = [{"from": f"{day}T00:00:00Z", "to": ends[0], "states": dict(st), "pos": pos}]
    for j, (k, e) in enumerate(today):
        st[e["path"]] = e["after"]
        out.append({"from": e["ts"], "to": ends[j + 1], "states": dict(st), "pos": k})
    return out


def name_present(states: Mapping[str, str], row: Mapping[str, Any]) -> bool:
    return all(b4r.item_line(states[p], row["item"]) is not None for p in row["docs"])


def _norm_line(text: str | None, item: str) -> str | None:
    ln = b4r.item_line(text, item)
    return None if ln is None else _WS.sub(" ", b4r.line_norm(ln)).strip()


def inventory(rows: Sequence[Mapping[str, Any]], base: Mapping[Any, Any], days: Sequence[str],
              groups: Sequence[Sequence[str]], team: Mapping[str, str], managers: set[str],
              rents: Sequence[set] | None = None) -> dict[str, Any]:
    import stage3_t1 as t1
    days = sorted(days)
    sessions = t1.sessions_by_account_day(rows)
    ent_cache: dict[tuple[int, str], bool] = {}

    def ent_present(text: str, i: int) -> bool:
        import stage3_b0 as b0
        key = (i, hashlib.sha256(text.encode()).hexdigest())
        if key not in ent_cache:
            ent_cache[key] = any({e for e in b0.entities(ln) if e[0] in b0.CLASSES} & rents[i]
                                 for ln in text.splitlines())
        return ent_cache[key]

    by: dict[str, dict[str, Any]] = {}
    anchors = {m: {"grouped_value": {}, "grouped_touch": {}, "ungrouped": {}} for m in MODES}
    for i, row in enumerate(dz.SHARED):
        pair, item = tuple(row["docs"]), row["item"]
        el = eligibility(row, groups)
        kind = "grouped_value" if el["grouped"] and el["value_change"] else ("grouped_touch" if el["grouped"]
                                                                             else "ungrouped")
        ev = pair_events(rows, base, pair)
        prev = {p: _norm_line(_base_text(base, p), item) for p in pair}
        changed = []
        for e in ev:
            now = _norm_line(e["after"], item)
            changed.append(now != prev[e["path"]])
            prev[e["path"]] = now
        whole = [e["action"] == "write_file" for e in ev]
        for d in days:
            bnd = boundaries(ev, base, pair, d)
            name = [name_present(b["states"], row) for b in bnd]
            ent = [nm or (rents is not None and all(ent_present(b["states"][p], i) for p in pair))
                   for nm, b in zip(name, bnd)]
            wf = [e["ts"] for e in ev if e["ts"][:10] == d and e["action"] == "write_file"]
            floor = max(wf) if wf else None
            f4 = [nm and (floor is None or b["from"] >= floor) for nm, b in zip(name, bnd)]
            accts = set()
            for (acct, dd), ss in sessions.items():
                if dd != d or acct in managers or any(team.get(acct) not in t1.WRITE_TEAMS[p] for p in pair):
                    continue
                # file order interleaves sessions, so a boundary's times can run backwards: use its span
                if any(s.first_ts <= max(b["from"], b["to"]) and s.last_ts >= min(b["from"], b["to"])
                       for s in ss for b, nm in zip(bnd, name) if nm):
                    accts.add(acct)
            cnt = dict.fromkeys(("overwrite_same_day", "overwrite_by_end", "whole_write_same_day",
                                 "whole_write_by_end"), 0)
            win = {"O_ws": {"containing": 0, "affected": 0}, "O_diff": {"containing": 0, "affected": 0}}
            n_starts = days.index(d) + 1
            for b, nm in zip(bnd, name):
                if not nm:
                    continue
                later = range(b["pos"] + 1, len(ev))
                g_over = next((g for g in later if changed[g]), None)
                g_whole = next((g for g in later if whole[g]), None)
                cnt["overwrite_by_end"] += g_over is not None
                cnt["overwrite_same_day"] += g_over is not None and ev[g_over]["ts"][:10] == d
                cnt["whole_write_by_end"] += g_whole is not None
                cnt["whole_write_same_day"] += g_whole is not None and ev[g_whole]["ts"][:10] == d
                if el["grouped"]:
                    win["O_ws"]["containing"] += n_starts * len(later)
                    win["O_ws"]["affected"] += n_starts * (len(ev) - g_over if g_over is not None else 0)
                for p in pair:
                    ends_p = [g for g in later if ev[g]["path"] == p]
                    g_p = next((g for g in ends_p if changed[g]), None)
                    win["O_diff"]["containing"] += n_starts * len(ends_p)
                    win["O_diff"]["affected"] += n_starts * (sum(g >= g_p for g in ends_p) if g_p is not None else 0)
            cell = {"row": i, "item": item, "pair": list(pair), "classes": list(row["classes"]), "kind": kind,
                    "day": d, "boundaries": len(bnd), "name": sum(name), "entity": sum(ent),
                    "inserter_floor": sum(f4), "accounts": len(accts), **cnt, "windows": win}
            by[f"{item}|{d}"] = cell
            for m in MODES:
                if cell[m] > 0:
                    anchors[m][kind].setdefault(item, []).append(d)
    return {"by_item_day": by, "anchors": anchors,
            "supply": {m: supply(anchors[m]["grouped_value"]) for m in MODES},
            "definition": "boundary = the day's start or just after one of the day's successful content writes to "
                          "either document of the item's pair (file order); name = both item lines present "
                          "(stage3_b4r.item_line); entity = name, or each document carries one of the row's Z5 "
                          "entities (stage3_b4r.row_entities); inserter_floor = name and at or after the day's last "
                          "whole rewrite of either document (the v3 inserter's F4); accounts = non-managers in both "
                          "documents' write teams with a session on the day overlapping a name boundary; overwrite = "
                          "a later honest write after which the item's line differs or is gone; windows = B4-R's "
                          "construction (every day boundary at or before the insertion day to every later write on "
                          "the group (O_ws) or document (O_diff)), summed over name boundaries: containing the "
                          "insertion, and of those ending at or after the overwrite (affected)"}


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_inventory(corpus: Path, version: str = "v7") -> dict[str, Any]:
    import stage3_t1 as t1
    import stage3_views as sv
    if _sha(corpus) != CORPUS_SHA:
        raise SystemExit(f"refusing: {corpus} is not prefix_rw_v3rc ({CORPUS_SHA[:8]}...)")
    b4r.check_provenance(corpus, version)
    base = b4r.seed_base(version)
    rows = sv.read_jsonl(corpus)
    groups = json.loads(GROUPS_FILE.read_text())["groups"]
    team, managers = t1.team_maps(sv.jc_mod.FORK / "bootstrap" / "org_template.yaml")
    inv = inventory(rows, base, sv.corpus_days(rows), groups, team, managers, b4r.row_entities())
    vt = json.loads(VALUE_TABLE.read_text())
    used: dict[str, set] = {}
    for v in vt["variants"]:
        used.setdefault(v["item"], set()).add(v["value"])
    inv["values"] = {r["item"]: {"table_values": len(vals), "update_variant_values": len(used.get(r["item"], ()))}
                     for r, vals in zip(dz.SHARED, dz.routine_values())}
    inv.update({"version": VERSION, "corpus": corpus.name, "corpus_sha256": CORPUS_SHA, "seed_version": version,
                "groups": groups, "groups_sha256": _sha(GROUPS_FILE), "value_table_sha256": _sha(VALUE_TABLE),
                "script_sha256": _sha(Path(__file__))})
    return inv


# ── the grid ─────────────────────────────────────────────────────────────────

NS, PLS, ICCS = (6, 12, 16, 24, 32), (1, 2), (0.3, 0.6)


def run_grid(sims: int = SIMS, reps: int = REPS, seed: int = SEED, log=print) -> dict[str, Any]:
    out: dict[str, Any] = {"version": VERSION, "seed": seed, "sims": sims, "reps": reps, "priors": PRIORS,
                           "prior_sources": PRIOR_SOURCES, "independent": [], "this_world": [], "grid_check": [],
                           "min_recall": []}
    for name, pri in PRIORS.items():
        for icc in ICCS:
            for n in NS:
                for pl in PLS:
                    r = simulate({"n": n, "pl": pl, "icc": icc}, pri, sims, reps, seed)
                    r["prior"] = name
                    r["decidable"] = decidable(r)
                    out["independent"].append(r)
                    log(json.dumps({"independent": name, "icc": icc, "n": n, "pl": pl,
                                    "min_decidable": r["decidable"]["min"]}))
    for name in ("opus48_central", "opus48_optimistic"):
        for icc_item in (0.1, 0.3):
            for boot in ("payload", "two_stage"):
                for n in NS:
                    for pl in PLS:
                        r = simulate({"n": n, "pl": pl, "icc": 0.3, "items": 3, "icc_item": icc_item, "boot": boot},
                                     PRIORS[name], sims, reps, seed)
                        r["prior"] = name
                        r["decidable"] = decidable(r)
                        out["this_world"].append(r)
                        log(json.dumps({"this_world": name, "icc_item": icc_item, "boot": boot, "n": n, "pl": pl,
                                        "min_decidable": r["decidable"]["min"]}))
    for gen in ("flag", "grid"):
        r = simulate({"n": 24, "pl": 2, "icc": 0.3, "gen": gen}, PRIORS["opus48_optimistic"], sims, reps, seed + 1)
        r["prior"] = "opus48_optimistic"
        r["decidable"] = decidable(r)
        out["grid_check"].append(r)
    for icc in ICCS:
        for q in (0.06, 0.12):
            for n in NS[1:]:
                for pl in PLS:
                    out["min_recall"].append({"n": n, "pl": pl, "icc": icc, "q": q,
                                              "recall": min_recall_for_headroom(n, pl, icc, q, sims, reps, seed)})
    out["estimates"] = {f"{n}x{pl}": estimate(n, pl) for n in NS for pl in PLS}
    out["estimates_with_21"] = {f"{n}x{pl}": estimate(n, pl, include_21=True) for n in NS for pl in PLS}
    out["script_sha256"] = _sha(Path(__file__))
    return out


# ── rendering (tables only; the report's prose is written by hand around them) ──

def _o(t: Mapping[str, float] | None, keys: Sequence[str]) -> str:
    return "n/a" if t is None else " / ".join(f"{t[k]:.2f}" for k in keys)


def render(inv: Mapping[str, Any], sim: Mapping[str, Any]) -> str:
    L = ["## Inventory tables (generated)", "",
         "| item | pair kind | day | boundaries | by name | by entity | inserter floor | accounts | overwritten same day / by end (of name) | whole rewrite same day / by end | O_ws windows affected / containing | O_diff windows affected / containing |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in inv["by_item_day"].values():
        w = c["windows"]
        L.append(f"| {c['item']} | {c['kind']} | {c['day']} | {c['boundaries']} | {c['name']} | {c['entity']} | "
                 f"{c['inserter_floor']} | {c['accounts']} | {c['overwrite_same_day']} / {c['overwrite_by_end']} | "
                 f"{c['whole_write_same_day']} / {c['whole_write_by_end']} | "
                 f"{w['O_ws']['affected']} / {w['O_ws']['containing']} | {w['O_diff']['affected']} / {w['O_diff']['containing']} |")
    L += ["", "| mode | grouped value-change anchors (item: days) | supply: one placement reuse / no reuse | two placements reuse / no reuse |",
          "|---|---|---|---|"]
    for m in MODES:
        a = inv["anchors"][m]["grouped_value"]
        s = inv["supply"][m]
        L.append(f"| {m} | " + "; ".join(f"{k}: {', '.join(v)}" for k, v in a.items()) +
                 f" | {s['one_placement']['reuse']} / {s['one_placement']['no_reuse']} | "
                 f"{s['two_placements']['reuse']} / {s['two_placements']['no_reuse']} |")
    keys = ("floor", "present", "attenuated", "excluded", "inconclusive")
    hdr = ("| prior | ICC | n × pl | P(head) O_diff (1,1) | P(head) dossier (1,2) | P(head) O_ws (2,2) −/0/+ | "
           "C-frag 0.3 | C-frag 0.45 | C-frag implied | C-split 0 | C-split 0.3 | C-split 0.45 | C-split implied | "
           "C-ws 0.3 (O_ws = O_diff) | C-ws implied | min decidable (where) |")
    sep = "|" + "---|" * 16

    def row(r: Mapping[str, Any], lead: str) -> str:
        ph = r["P_headroom"]
        return (f"| {lead} | {r['design']['n']}×{r['design']['pl']} | {ph['O_diff_11']:.2f} | {ph['dossier_12']:.2f} | "
                f"{ph['O_ws_22_-0.15']:.2f}/{ph['O_ws_22_0']:.2f}/{ph['O_ws_22_0.15']:.2f} | "
                f"{_o(r['C_frag']['0.3'], keys)} | {_o(r['C_frag']['0.45'], keys)} | {_o(r['C_frag']['implied'], keys)} | "
                f"{_o(r['C_split']['0'], keys)} | {_o(r['C_split']['0.3'], keys)} | {_o(r['C_split']['0.45'], keys)} | "
                f"{_o(r['C_split']['implied'], keys)} | {_o(r['C_ws_0']['0.3'], keys)} | {_o(r['C_ws_0']['implied'], keys)} | "
                f"{r['decidable']['min']} ({r['decidable']['argmin']}) |")
    L += ["", "## Simulation, independent anchors (generated)", "",
          "Cells: floor / present / attenuated / excluded / inconclusive.", "", hdr, sep]
    for r in sim["independent"]:
        L.append(row(r, f"{r['prior']} | {r['design']['icc']}"))
    L += ["", "## Simulation, this world's supply: three items reused across cells (generated)", "",
          hdr.replace("| prior | ICC |", "| prior | item ICC, bootstrap |"), sep]
    for r in sim["this_world"]:
        L.append(row(r, f"{r['prior']} | {r['design']['icc_item']}, {r['design']['boot']}"))
    L += ["", "## Score-grid check (generated)", "", hdr.replace("| prior | ICC |", "| prior | generator |"), sep]
    for r in sim["grid_check"]:
        L.append(row(r, f"{r['prior']} | {r['design']['gen']}"))
    L += ["", "## Smallest recall reaching headroom with probability 0.8 (generated)", "",
          "| ICC | control q | " + " | ".join(f"{n}×{pl}" for n in NS[1:] for pl in PLS) + " |",
          "|---|---|" + "---|" * (len(NS[1:]) * len(PLS))]
    for icc in ICCS:
        for q in (0.06, 0.12):
            cells = [next(x["recall"] for x in sim["min_recall"] if (x["n"], x["pl"], x["icc"], x["q"]) == (n, pl, icc, q))
                     for n in NS[1:] for pl in PLS]
            L.append(f"| {icc} | {q} | " + " | ".join("over 1.0" if c is None else f"{c:.2f}" for c in cells) + " |")
    L += ["", "## Estimate (generated; B4-R per-unit null costs)", "",
          "| n × pl | O_diff | O_ws | O_ws_all | dossier iso | dossier live | P_author | Sonnet $ | Opus 4.8 $ | total $ | total with (2,1) $ |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, e in sim["estimates"].items():
        u = e["units"]
        L.append(f"| {k} | {u['O_diff']} | {u['O_ws']} | {u['O_ws_all']} | {u['P_author_doc_iso']} | "
                 f"{u['P_author_doc_live']} | {u['P_author']} | {e['dollars']['by_judge']['sonnet']} | "
                 f"{e['dollars']['by_judge']['opus48']} | {e['dollars']['total']} | "
                 f"{sim['estimates_with_21'][k]['dollars']['total']} |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("inventory")
    a.add_argument("--corpus", type=Path, required=True)
    a.add_argument("--version", default="v7")
    a.add_argument("--out-json", type=Path, required=True)
    b = sub.add_parser("simulate")
    b.add_argument("--out-json", type=Path, required=True)
    b.add_argument("--sims", type=int, default=SIMS)
    b.add_argument("--reps", type=int, default=REPS)
    c = sub.add_parser("render")
    c.add_argument("--inventory", type=Path, required=True)
    c.add_argument("--sim", type=Path, required=True)
    c.add_argument("--out-md", type=Path, required=True)
    ns = ap.parse_args(argv)
    if ns.cmd == "inventory":
        res = run_inventory(ns.corpus, ns.version)
        ns.out_json.write_text(json.dumps(res, indent=1) + "\n")
        print(json.dumps({"out_json": str(ns.out_json), "sha256": _sha(ns.out_json)}))
    elif ns.cmd == "simulate":
        res = run_grid(ns.sims, ns.reps, log=lambda s: print(s, flush=True))
        ns.out_json.write_text(json.dumps(res, indent=1) + "\n")
        print(json.dumps({"out_json": str(ns.out_json), "sha256": _sha(ns.out_json)}))
    else:
        md = render(json.loads(ns.inventory.read_text()), json.loads(ns.sim.read_text()))
        ns.out_md.write_text(md)
        print(json.dumps({"out_md": str(ns.out_md), "sha256": _sha(ns.out_md)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
