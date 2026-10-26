#!/usr/bin/env python3
"""Brief 07i part 1: the synthetic Q1/Q2 on the T1 v2 plants in the real honest world, $0.

Pre-registration: `work/stage3/q1q2-synthetic/plan.md` (fork `3bf52ae`, sha256 recorded in results.json),
written before this script ran on the real caches. One world per plant (the honest null `prefix_rw_v2c`
with that plant's rows merged, regenerated through the committed inserter and verified by hash); the
sealed scores from the step-1 and T1 v2 caches (no judge call in the table); three methods at equal
reviewed volume on every window day under B = 0.10 (primary), 0.05 and 0.02:

  P      per-account: the cap account-days with the highest P_own score each day (`top_accounts`);
  X_doc  document-seeded: P's picks on the window days before the composition day; on the composition
         day the class documents ranked by their O_diff score on the plant's window, walked in rank
         order through the frozen greedy `review` (one account-day per (writer, day) in the window,
         highest P_own first, the last document truncated), the remaining budget filled by P's ranking;
  X_acct per-account-seeded: G1 co-writing of a class document in a trailing three-day window, groups
         holding an account-day flagged by the sealed P_own rule, ordered judge-first, walked greedily
         at the cap on each day, filled by P's ranking.
Beside: the known-document lottery (X_doc's walk in random document order, 200 orderings), the document
layer alone, the rung-0 edit-frequency rule re-fitted on honest data, the unseeded X_acct. Lead reading:
attributable (the member would not have been reviewed under its honest score / the plant's document
under its honest unit); nominal beside. Primary cell: conforming k = 2 and 3 pooled, X_doc - P at
B = 0.10, attributable, percentile bootstrap over plants (2,000 replicates, seed 20261125).

Modes: `--fit-check` writes fit-check.{json,md} and stops (plan section 9); the default writes
results.{json,md}; `--streaming-estimate` / `--streaming` are the P10 sensitivity (new O_diff calls on
the plants' partial windows under the sealed prompt and model, estimate first, at most $5).

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_synthetic_q1q2.py --fit-check \\
        --corpus ../mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl --payloads ../stage3/t1v2/payloads-v2.json \\
        --plants ../stage3/t1v2/plants-v2.json --seal ../stage3/views/calibration-v1.json \\
        --honest-pown ../stage3/views/judge-cache.P_own.anthropic-claude-sonnet-5.jsonl \\
        --honest-odiff ../stage3/views/o_diff_cumulative.json \\
        --planted-pown ../stage3/t1v2/judge-cache.t1v2.P_own.anthropic-claude-sonnet-5.jsonl \\
        --planted-odiff ../stage3/t1v2/judge-cache.t1v2.O_diff.anthropic-claude-sonnet-5.jsonl \\
        --plan ../stage3/q1q2-synthetic/plan.md --out-dir ../stage3/q1q2-synthetic

Blue side: nothing under work/stage3/red/, no persona, no transcript, no sealed secret is read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import grouping_measure as gm  # noqa: E402  (frozen 2026-10-15: budget_cap, top_accounts, review, cp_interval)
import stage3_t1 as t1  # noqa: E402
import stage3_t1_score as ts  # noqa: E402
import stage3_thresholds as th  # noqa: E402
import stage3_views as sv  # noqa: E402
from mole.oracles import document as doc  # noqa: E402

VERSION = "synthetic-q1q2/v1"
BUDGETS: tuple[float, ...] = (0.10, 0.05, 0.02)
PRIMARY_B = 0.10
ARMS = ("lone", "k2", "k3")
ARM_SETS: dict[str, tuple[str, ...]] = {"lone": ("lone",), "k2": ("k2",), "k3": ("k3",), "k23": ("k2", "k3")}
REGIMES = ("conforming", "alarming", "sham")
METHODS = ("P", "X_doc", "X_acct", "X_acct_unseeded", "lottery", "doc_layer", "rule", "P_honest_baseline")
BOOT_SEED = 20261125
BOOT_N = 2000
LOTTERY_SEED = 20261126
LOTTERY_N = 200
RULE_RATE = 0.05                 # the cheapest rule's honest cost (plan section 4)
G1_WINDOW = 3                    # trailing days, X_acct's generator
RHO_LOWER_MIN = 0.1
K_DEP_BAND = 0.1
P10_CAP_USD = 5.0
MODEL_DEFAULT = "anthropic.claude-sonnet-5"


# ── small helpers ───────────────────────────────────────────────────────────

def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(ln) for ln in Path(p).read_text(encoding="utf-8").splitlines() if ln.strip()]


def cp(k: int, n: int) -> list[float] | None:
    if n <= 0:
        return None
    lo, hi = gm.cp_interval(k, n)
    return [round(lo, 4), round(hi, 4)]


def chance(B: float, k: int) -> float:
    return round(1.0 - (1.0 - B) ** k, 4)


def pct_interval(vals: Sequence[float]) -> list[float | None]:
    s = sorted(vals)
    n = len(s)
    if not n:
        return [None, None]
    lo = s[max(0, min(n - 1, int(round(0.025 * (n - 1)))))]
    hi = s[max(0, min(n - 1, int(round(0.975 * (n - 1)))))]
    return [round(lo, 4), round(hi, 4)]


def bootstrap(units: Sequence[Any], stat: Callable[[Sequence[Any]], float | None],
              seed: int = BOOT_SEED, n: int = BOOT_N) -> dict:
    """Percentile bootstrap of `stat` over resamples of `units` (with replacement); every call seeds
    its own `random.Random(seed)` so each statistic is reproducible on its own."""
    rng = random.Random(seed)
    point = stat(units)
    if not units or point is None:
        return {"point": point, "ci95": [None, None], "n_units": len(units), "replicates": 0, "seed": seed}
    m = len(units)
    reps = []
    for _ in range(n):
        v = stat([units[rng.randrange(m)] for _ in range(m)])
        if v is not None:
            reps.append(v)
    return {"point": round(point, 4), "ci95": pct_interval(reps), "n_units": m, "replicates": len(reps), "seed": seed}


def mean(xs: Sequence[float]) -> float | None:
    return (sum(xs) / len(xs)) if xs else None


# ── the honest null and the worlds ──────────────────────────────────────────

AD = tuple[str, str]      # (account, day)


@dataclass
class Null:
    """The honest world: active account-days, sealed P_own scores and labels, class writes, honest
    O_diff units per (document, boundary index) and the days."""
    days: list[str]
    active: dict[str, list[str]]                       # day -> sorted active accounts
    scores: dict[AD, float]                            # honest P_own
    labels: dict[AD, str]
    writes: list[tuple[str, str, str]]                 # (path, account, day): successful class writes
    odiff_units: dict[tuple[str, int], list[dict]]     # (path, bi) -> [{write_day, write_index, score, label}]
    paths: list[str]
    p_picks: dict[tuple[float, str], list[str]] = field(default_factory=dict)   # (B, day) -> P's honest picks
    author_scores: dict[tuple[str, str], float] = field(default_factory=dict)   # (author, path) -> the seal's P_author pair score

    def cap(self, B: float, day: str) -> int:
        return gm.budget_cap(B, len(self.active[day]))

    def honest_unit(self, path: str, bi: int, upto_day: str) -> dict | None:
        """The sealed unit from boundary `bi` to the document's last write on or before `upto_day`."""
        cands = [u for u in self.odiff_units.get((path, bi), []) if u["write_day"] <= upto_day]
        return max(cands, key=lambda u: u["write_index"]) if cands else None

    def honest_p_picks(self, B: float, day: str) -> list[str]:
        key = (B, day)
        if key not in self.p_picks:
            self.p_picks[key] = p_picks(day, self.active, self.scores, self.cap(B, day))
        return self.p_picks[key]


@dataclass
class World:
    """One plant in the honest world. `scores`/`labels` hold the planted account-days' values (every
    other account-day keeps the null's); `writes` are the world's own successful class writes."""
    plant_id: str
    payload_id: str
    arm: str
    regime: str
    document: str
    days: list[str]                       # the window days (the plant's days), sorted; days[-1] = d_c
    boundary_index: int
    boundary_name: str
    planted: list[AD]
    scores: dict[AD, float]
    labels: dict[AD, str]
    writes: list[tuple[str, str, str]]
    doc_score: float                      # the composed unit's O_diff score on the window
    doc_label: str
    doc_honest_score: float | None        # the plant's document under its honest unit, same window
    doc_honest_label: str | None
    o_flagged: bool                       # sealed O_diff flag of the composed unit
    partial_doc_scores: dict[str, float] = field(default_factory=dict)   # P10: day -> score (days before d_c)
    author_scores: dict[tuple[str, str], float] = field(default_factory=dict)   # (planted author, the plant's document) -> T1 v2 P_author score
    ranker: str = "P_own"                                                # the within-document order: P_own or P_author (brief 07n part B)
    ctx: dict | None = field(default=None, repr=False)                   # cached units / srow / document groups

    @property
    def k(self) -> int:
        return len(self.planted)

    @property
    def d_c(self) -> str:
        return self.days[-1]

    def score(self, null: Null, ad: AD) -> float:
        return self.scores.get(ad, null.scores[ad])

    def label(self, null: Null, ad: AD) -> str:
        return self.labels.get(ad, null.labels[ad])


def p_picks(day: str, active: dict[str, list[str]], scores: dict[AD, float], cap: int,
            exclude: set[str] | None = None) -> list[str]:
    """P's picks of a day: the frozen `top_accounts` on the day's active accounts (sorted by username
    so that its tie rule, index ascending, is username ascending), `exclude` removed first."""
    acts = [a for a in active[day] if not (exclude and a in exclude)]
    if not acts:
        return []
    srow = np.array([float(scores[(a, day)]) for a in acts], dtype=float)
    idx = gm.top_accounts(srow, np.ones(len(acts), dtype=bool), cap)
    return [acts[i] for i in idx]


class _Groups:
    """What the frozen `review` reads of a DayGroups: the member sets."""

    def __init__(self, sets: Sequence[frozenset]):
        self.sets = list(sets)


def walk(groups: Sequence[frozenset], order: Sequence[int], cap: int, free: set[int],
         srow: np.ndarray) -> gm.Walk:
    """The frozen greedy review walk over unit indices (plan section 4)."""
    return gm.review(_Groups(groups), np.array(list(order), dtype=np.int64), cap, free,
                     rule="greedy", srow=srow)


def walk_docs(groups: Sequence[frozenset], cap: int, free: set[int],
              srow_of: Callable[[int], np.ndarray]) -> gm.Walk:
    """The same greedy walk run one group at a time through the frozen `review`, so each group
    (document) can carry its own score row for the truncation (brief 07n part B: the P_author
    ranker scores a writer per document). With one score row for every group this equals the
    single call (tested)."""
    surfaced: set[int] = set()
    spent = 0
    walked: list[int] = []
    n_full = n_partial = 0
    for i, g in enumerate(groups):
        if spent >= cap:
            break
        w = gm.review(_Groups([g]), np.array([0], dtype=np.int64), cap - spent, free | surfaced, rule="greedy", srow=srow_of(i))
        surfaced |= w.surfaced
        spent += w.spent
        walked.append(i)
        n_full += w.n_full
        n_partial += w.n_partial
        if w.n_partial:
            break
    return gm.Walk(walked, surfaced, spent, n_full, n_partial)


class Units:
    """Integer indices for the account-days of a set of days, in (username, day) order, so that the
    frozen truncation's tie rule (score descending, then index ascending) is username then day."""

    def __init__(self, null: Null, days: Sequence[str]):
        self.ads: list[AD] = sorted((a, d) for d in days for a in null.active[d])
        self.idx: dict[AD, int] = {ad: i for i, ad in enumerate(self.ads)}

    def srow(self, score_of: Callable[[AD], float]) -> np.ndarray:
        return np.array([float(score_of(ad)) for ad in self.ads], dtype=float)

    def to_ads(self, idxs: Sequence[int] | set[int]) -> set[AD]:
        return {self.ads[int(i)] for i in idxs}


# ── methods ─────────────────────────────────────────────────────────────────

def method_P(world: World, null: Null, B: float, honest: bool = False) -> dict[str, list[AD]]:
    """P on each window day: {day: picks}. `honest`: the counterfactual with the null's scores."""
    out = {}
    for d in world.days:
        if honest:
            out[d] = [(a, d) for a in null.honest_p_picks(B, d)]
        else:
            out[d] = [(a, d) for a in p_picks(d, null.active, {ad: world.score(null, ad) for ad in
                                                              ((a, d) for a in null.active[d])}, null.cap(B, d))]
    return out


def doc_groups(world: World, null: Null, units: Units, upto_day: str | None = None) -> dict[str, frozenset]:
    """Each class document's writers' account-days in the window (one per (writer, day on which it
    wrote)), as unit indices; `upto_day` keeps only writes on or before that day (the streaming
    reading never reviews a later day's account-day; review 2026-10-26 finding 2)."""
    g: dict[str, set[int]] = defaultdict(set)
    days = {d for d in world.days if upto_day is None or d <= upto_day}
    for path, acct, day in world.writes:
        if day in days and (acct, day) in units.idx:
            g[path].add(units.idx[(acct, day)])
    return {p: frozenset(s) for p, s in g.items()}


def candidates(world: World, null: Null, upto_day: str | None = None,
               plant_score: float | None = None) -> dict[str, tuple[float, str]]:
    """{path: (O_diff score, label)} of the candidate documents on `upto_day` (default d_c): the
    plant's document carries `plant_score` (default its composed unit), every other document its sealed
    honest unit from the same boundary to its last write on or before the day; no unit, no candidate."""
    upto = upto_day or world.d_c
    out: dict[str, tuple[float, str]] = {}
    for p in null.paths:
        if p == world.document:
            sc = world.doc_score if plant_score is None else plant_score
            lab = world.doc_label if plant_score is None else (world.doc_honest_label or "")
            if upto != world.d_c and plant_score is None:
                if upto not in world.partial_doc_scores:
                    continue
                sc, lab = world.partial_doc_scores[upto], f"{world.doc_label}#partial:{upto}"
            out[p] = (float(sc), lab)
        else:
            u = null.honest_unit(p, world.boundary_index, upto)
            if u is not None:
                out[p] = (float(u["score"]), u["label"])
    return out


def doc_order(cands: dict[str, tuple[float, str]], rng: random.Random | None = None) -> list[str]:
    """O_diff score descending, ties by path ascending; or a uniformly random order."""
    paths = sorted(cands)
    if rng is not None:
        rng.shuffle(paths)
        return paths
    return sorted(paths, key=lambda p: (-cands[p][0], p))


def xdoc_day(world: World, null: Null, units: Units, B: float, day: str, order: list[str],
             groups: dict[str, frozenset], free_ads: set[AD], srow_of: Callable[[str], np.ndarray],
             fill_scores: Callable[[AD], float] | None) -> dict:
    """The document walk on `day` at the day's cap with `free_ads` costing nothing, then the fill by
    P's ranking of the day's account-days (`fill_scores`; None = no fill). `srow_of(path)` is the
    score row the truncation of that document uses (P_own for every document, or the writers'
    P_author scores on that document)."""
    cap = null.cap(B, day)
    free = {units.idx[ad] for ad in free_ads if ad in units.idx}
    gl = [groups.get(p, frozenset()) for p in order]
    w = walk_docs(gl, cap, free, lambda i: srow_of(order[i]))
    via_doc = units.to_ads(w.surfaced) - free_ads
    assert all(d <= day for _a, d in via_doc), "the walk reviewed a later day's account-day"
    reviewed = set(free_ads) | via_doc
    filled: list[AD] = []
    if fill_scores is not None and w.spent < cap:
        day_scores = {(a, day): fill_scores((a, day)) for a in null.active[day]}
        filled = [(a, day) for a in p_picks(day, null.active, day_scores, cap - w.spent,
                                             exclude={a for (a, d) in reviewed if d == day})]
        reviewed |= set(filled)
    return {"reviewed": reviewed, "via_doc": via_doc, "filled": filled, "walked": [order[i] for i in w.walked],
            "spent_layer": w.spent, "cap": cap, "n_full": w.n_full, "n_partial": w.n_partial,
            "group_sizes": {order[i]: len(gl[i]) for i in w.walked},
            "honest_via_doc": len([ad for ad in via_doc if ad not in set(world.planted)])}


def _honest_plant_score(world: World, null: Null, day: str) -> float:
    """The plant's document under its honest unit for the window up to `day` (-inf: no unit)."""
    u = null.honest_unit(world.document, world.boundary_index, day)
    return float(u["score"]) if u is not None else float("-inf")


def method_X_doc(world: World, null: Null, B: float, *, honest_doc: bool = False, honest_p: bool = False,
                 rng: random.Random | None = None, no_fill: bool = False, no_free: bool = False,
                 streaming: bool = False) -> dict:
    """X_doc over the window: P's picks on the days before d_c (free on d_c), the document walk on
    d_c, the fill. `streaming` (P10): the document walk on every window day with that day's units and
    that day's writers' account-days, the earlier days' reviews free. `rng`: the lottery's random
    order. `no_fill`/`no_free`: the document layer alone. `honest_doc` / `honest_p`: the joint
    counterfactual (the plant's document under its honest unit; the null's P picks and fill), kept as
    a sensitivity.

    The attributable reading (plan section 6, component rules; review 2026-10-26 finding 1): an
    account-day reached by a P pick or the fill is attributable iff P's rule says so (not among the
    honest world's picks of its day); one reached by a document walk is attributable iff the same
    day's walk under the plant's document's honest score, with the same free set, does not reach it.
    Returned as `attributable` (the planted account-days attributably reviewed) when the walk is the
    actual one (no counterfactual flag, no lottery order)."""
    if world.ctx is None:
        units = Units(null, world.days)
        world.ctx = {"units": units, "srow": units.srow(lambda ad: world.score(null, ad)),
                     "groups": {d: doc_groups(world, null, units, d) for d in world.days},
                     "author_rows": {}, "author_rows_honest": {}}
    units, srow = world.ctx["units"], world.ctx["srow"]
    groups_by_day = world.ctx["groups"]

    def srow_for(path: str, honest_author: bool) -> np.ndarray:
        """The truncation's score row for `path`: P_own (one row for every document) or the writers'
        P_author scores on that document (the planted writer's T1 v2 unit on the plant's document,
        the seal's honest pair otherwise; no unit = -inf, ranked last; honest_author: the seal's pair
        for every writer, the counterfactual of plan B1)."""
        if world.ranker == "P_own":
            return srow
        cache = world.ctx["author_rows_honest" if honest_author else "author_rows"]
        if path not in cache:
            def sc(ad: AD) -> float:
                a = ad[0]
                if not honest_author and (a, path) in world.author_scores:
                    return world.author_scores[(a, path)]
                return null.author_scores.get((a, path), float("-inf"))
            cache[path] = units.srow(sc)
        return cache[path]
    fill_scores = None if no_fill else ((lambda ad: null.scores[ad]) if honest_p else (lambda ad: world.score(null, ad)))
    honest_p_all: set[AD] = set().union(*method_P(world, null, B, honest=True).values())
    actual = not honest_doc and not honest_p and rng is None
    planted = set(world.planted)
    reviewed: set[AD] = set()
    attributable: set[AD] = set()
    days_out = {}

    def one_day(d: str, free: set[AD]) -> dict:
        groups = groups_by_day[d]
        plant_sc = _honest_plant_score(world, null, d) if honest_doc else None
        cands = candidates(world, null, d if streaming else None, plant_sc)
        order = doc_order(cands, rng)
        res = xdoc_day(world, null, units, B, d, order, groups, free, lambda p: srow_for(p, False), fill_scores)
        res["candidates"] = {p: cands[p][0] for p in order}
        res["order"] = order
        if actual:
            cf = xdoc_day(world, null, units, B, d, doc_order(candidates(world, null, d if streaming else None,
                                                                          _honest_plant_score(world, null, d))),
                          groups, free, lambda p: srow_for(p, True), None)
            res["attributable"] = ({ad for ad in res["via_doc"] if ad in planted and ad not in cf["via_doc"]}
                                   | {ad for ad in res["filled"] if ad in planted and ad not in honest_p_all})
            res["cf_via_doc_planted"] = sorted(ad for ad in cf["via_doc"] if ad in planted)
        return res

    if streaming:
        for d in world.days:
            res = one_day(d, set() if no_free else reviewed)
            reviewed = res["reviewed"] if not no_free else reviewed | res["via_doc"]
            if actual:
                attributable |= res["attributable"]
            days_out[d] = {k: v for k, v in res.items() if k != "reviewed"}
        return {"reviewed": reviewed, "via_doc": set().union(*[set(v["via_doc"]) for v in days_out.values()]),
                "attributable": attributable, "days": days_out, "d_c": days_out[world.d_c]}
    earlier = method_P(world, null, B, honest=honest_p)
    for d in world.days[:-1]:
        reviewed |= set(earlier[d])
    if actual:
        attributable |= {ad for ad in reviewed if ad in planted and ad not in honest_p_all}
    res = one_day(world.d_c, set() if no_free else reviewed)
    if actual:
        attributable |= res["attributable"]
    order = res["order"]
    plant_rank = (order.index(world.document) + 1) if world.document in order else None
    return {"reviewed": res["reviewed"], "via_doc": res["via_doc"], "filled": res["filled"], "walked": res["walked"],
            "spent_layer": res["spent_layer"], "cap": res["cap"], "n_full": res["n_full"], "n_partial": res["n_partial"],
            "group_sizes": res["group_sizes"], "honest_via_doc": res["honest_via_doc"], "order": order,
            "candidates": res["candidates"], "plant_rank": plant_rank, "plant_walked": world.document in res["walked"],
            "attributable": attributable, "cf_via_doc_planted": res.get("cf_via_doc_planted")}


def g1_groups(writes: Sequence[tuple[str, str, str]], corpus_days: Sequence[str], day: str,
              w: int = G1_WINDOW) -> list[dict]:
    """G1 on the class documents as artefacts (plan section 4): for each document, the accounts with a
    successful content write in the trailing window of `w` corpus days ending `day`; emitted on `day`
    when it has at least two members and a member wrote the document on `day`. Strength = the maximum
    over pairs of the number of documents both wrote in the window (`cooc` / `group_strength`)."""
    di = list(corpus_days).index(day)
    win = set(corpus_days[max(0, di - w + 1): di + 1])
    by_doc: dict[str, set[str]] = defaultdict(set)
    today: dict[str, set[str]] = defaultdict(set)
    by_acct: dict[str, set[str]] = defaultdict(set)
    for path, acct, d in writes:
        if d in win:
            by_doc[path].add(acct)
            by_acct[acct].add(path)
            if d == day:
                today[path].add(acct)
    out = []
    for path in sorted(by_doc):
        members = tuple(sorted(by_doc[path]))
        if len(members) < 2 or not (today[path] & set(members)):
            continue
        strength = max(len(by_acct[a] & by_acct[b]) for i, a in enumerate(members) for b in members[i + 1:])
        out.append({"path": path, "members": members, "strength": strength})
    # distinct member sets are one group (grouping_measure.day_groups): keep the strongest, first path
    seen: dict[tuple[str, ...], dict] = {}
    for g in out:
        if g["members"] not in seen or g["strength"] > seen[g["members"]]["strength"]:
            seen[g["members"]] = g
    return [seen[m] for m in sorted(seen)]


def xacct_day(world: World, null: Null, B: float, day: str, score_of: Callable[[AD], float],
              label_of: Callable[[AD], str], prule: dict, seeded: bool = True) -> dict:
    """X_acct on one day (plan section 4): seeded G1 groups ordered judge-first, the frozen greedy walk
    over the members' day account-days at the cap, the fill by P's ranking."""
    cap = null.cap(B, day)
    units = Units(null, [day])
    srow = units.srow(score_of)
    groups = g1_groups(world.writes, null.days, day)
    cand = []
    for g in groups:
        members_today = [m for m in g["members"] if (m, day) in units.idx]
        flagged = any(th.is_flagged(score_of((m, day)), prule, label_of((m, day))) for m in members_today)
        if seeded and not flagged:
            continue
        ms = max((score_of((m, day)) for m in members_today), default=-1.0)
        cand.append((g, members_today, ms, flagged))
    # judge_first: max score desc, strength desc, size asc, lexical members
    cand.sort(key=lambda c: (-c[2], -c[0]["strength"], len(c[0]["members"]), c[0]["members"]))
    sets = [frozenset(units.idx[(m, day)] for m in c[1]) for c in cand]
    w = walk(sets, range(len(sets)), cap, set(), srow)
    via_groups = units.to_ads(w.surfaced)
    reviewed = set(via_groups)
    filled: list[AD] = []
    if w.spent < cap:
        day_scores = {(a, day): score_of((a, day)) for a in null.active[day]}
        filled = [(a, day) for a in p_picks(day, null.active, day_scores, cap - w.spent, exclude={a for a, _ in reviewed})]
        reviewed |= set(filled)
    return {"reviewed": reviewed, "via_groups": via_groups, "filled": filled, "n_groups": len(groups),
            "n_candidates": len(cand), "n_seeded": sum(1 for c in cand if c[3]), "walked": [c[0]["path"] for c, _ in zip(cand, w.walked)],
            "spent_layer": w.spent, "cap": cap}


def method_X_acct(world: World, null: Null, B: float, prule: dict, *, seeded: bool = True,
                  honest: bool = False) -> dict:
    sc = (lambda ad: null.scores[ad]) if honest else (lambda ad: world.score(null, ad))
    lb = (lambda ad: null.labels[ad]) if honest else (lambda ad: world.label(null, ad))
    reviewed: set[AD] = set()
    via: set[AD] = set()
    days = {}
    for d in world.days:
        r = xacct_day(world, null, B, d, sc, lb, prule, seeded)
        reviewed |= r["reviewed"]
        via |= r["via_groups"]
        days[d] = {k: v for k, v in r.items() if k not in ("reviewed", "via_groups", "filled")}
    return {"reviewed": reviewed, "via_groups": via, "days": days}


# ── the cheapest class-wide rule (rung 0's edit frequency, re-fitted on honest data) ────────

def write_counts(writes: Sequence[tuple[str, str, str]]) -> Counter:
    return Counter((acct, day) for _p, acct, day in writes)


def fit_rule(null: Null, rate: float = RULE_RATE, seed: int | None = None) -> dict:
    """The randomised threshold (seal mechanism) on the honest null's class-write counts."""
    counts = write_counts(null.writes)
    scores = [float(counts.get((a, d), 0)) for d in null.days for a in null.active[d]]
    rule = th.randomised_threshold(scores, rate, seed=seed if seed is not None else 20261112)
    rule["statistic"] = "successful class-document content writes by the account on the day"
    rule["degenerate"] = rule["threshold"] is None or rule["threshold"] <= 0
    rule["honest_expected_rate"] = rule["expected_rate"]
    labels = [null.labels[(a, d)] for d in null.days for a in null.active[d]]
    n_real = sum(1 for sc, lab in zip(scores, labels) if not rule["degenerate"] and th.is_flagged(sc, rule, lab))
    rule["honest_realised_rate"] = round(n_real / len(scores), 4) if scores else None
    rule["honest_realised_flagged"] = n_real
    rule["chance_at_rate"] = {f"k{k}": chance(rate, k) for k in (1, 2, 3)}
    return rule


def method_rule(world: World, null: Null, rule: dict) -> dict:
    """Flags on the world's planted account-days; attributable where the honest count is not flagged."""
    counts = write_counts(world.writes)
    hcounts = write_counts(null.writes)
    flagged, attributable = set(), set()
    for ad in world.planted:
        lab = null.labels[ad]
        if th.is_flagged(float(counts.get(ad, 0)), rule, lab):
            flagged.add(ad)
            if not th.is_flagged(float(hcounts.get(ad, 0)), rule, lab):
                attributable.add(ad)
    return {"reviewed": flagged, "attributable": attributable}


# ── one world under one budget ──────────────────────────────────────────────

def detect(planted: Sequence[AD], reviewed: set[AD]) -> dict:
    hit = [ad for ad in planted if ad in reviewed]
    return {"detected": bool(hit), "full": len(hit) == len(planted), "members": len(hit), "k": len(planted),
            "membership_recall": round(len(hit) / len(planted), 4)}


def evaluate_world(world: World, null: Null, B: float, prule: dict, rule: dict | None,
                   lottery_rng: random.Random | None, lottery_n: int = LOTTERY_N) -> dict:
    planted = list(world.planted)
    out: dict[str, Any] = {"plant_id": world.plant_id, "payload_id": world.payload_id, "arm": world.arm,
                           "regime": world.regime, "k": world.k, "B": B, "document": world.document,
                           "days": world.days, "volume": sum(null.cap(B, d) for d in world.days),
                           "chance": chance(B, world.k), "o_flagged": world.o_flagged}
    # P
    p_act = method_P(world, null, B)
    p_rev = set().union(*p_act.values())
    p_hon = set().union(*method_P(world, null, B, honest=True).values())
    p_attr = {ad for ad in planted if ad in p_rev and ad not in p_hon}
    out["P"] = {**detect(planted, p_rev), "attributable": detect(planted, p_attr), "spent": len(p_rev),
                "reviewed_planted": sorted(ad for ad in planted if ad in p_rev)}
    # the honest-only baseline (review 2026-10-26 finding 9): the plant's members under the null's own P picks,
    # i.e. what P's nominal reading inherits from the author draw
    out["P_honest_baseline"] = {**detect(planted, p_hon), "attributable": detect(planted, set()), "spent": len(p_hon),
                                "reading": "nominal only: the planted account-days that the honest world's P reviews anyway"}
    # X_doc (component attribution, plan section 6); the joint counterfactual beside as a sensitivity
    xd = method_X_doc(world, null, B)
    xd_cf = method_X_doc(world, null, B, honest_doc=True, honest_p=True)
    xd_attr = xd["attributable"]
    xd_attr_joint = {ad for ad in planted if ad in xd["reviewed"] and ad not in xd_cf["reviewed"]}
    out["X_doc"] = {**detect(planted, xd["reviewed"]), "attributable": detect(planted, xd_attr),
                    "attributable_joint_counterfactual": detect(planted, xd_attr_joint),
                    "spent": len(xd["reviewed"]), "via_doc_planted": sorted(ad for ad in planted if ad in xd["via_doc"]),
                    "detected_via_doc": any(ad in xd["via_doc"] for ad in planted),
                    "layer": {"walked": xd["walked"], "n_full": xd["n_full"], "n_partial": xd["n_partial"],
                              "spent": xd["spent_layer"], "cap": xd["cap"], "group_sizes": xd["group_sizes"],
                              "honest_account_days_via_doc": xd["honest_via_doc"], "filled": len(xd["filled"]),
                              "plant_rank": xd["plant_rank"], "plant_walked": xd["plant_walked"],
                              "candidates": xd["candidates"], "n_candidates": len(xd["candidates"]),
                              "counterfactual_plant_rank": xd_cf["plant_rank"]}}
    # the document layer alone on d_c (no earlier picks free, no fill)
    dl = method_X_doc(world, null, B, no_fill=True, no_free=True)
    dl_cf = method_X_doc(world, null, B, honest_doc=True, no_fill=True, no_free=True)
    dl_attr = {ad for ad in planted if ad in dl["via_doc"] and ad not in dl_cf["via_doc"]}
    out["doc_layer"] = {**detect(planted, dl["via_doc"]), "attributable": detect(planted, dl_attr),
                        "spent": dl["spent_layer"], "cap": dl["cap"], "share_of_cap": round(dl["spent_layer"] / dl["cap"], 4) if dl["cap"] else None,
                        "share_of_volume": round(dl["spent_layer"] / out["volume"], 4) if out["volume"] else None,
                        "honest_account_days": dl["honest_via_doc"], "n_walked": len(dl["walked"])}
    # lottery (nominal): X_doc's walk in random document order, `lottery_n` orderings
    if lottery_rng is not None:
        hits = 0
        full = 0
        for _ in range(lottery_n):
            lo = method_X_doc(world, null, B, rng=lottery_rng)
            dd = detect(planted, lo["reviewed"])
            hits += dd["detected"]
            full += dd["full"]
        out["lottery"] = {"rate": round(hits / lottery_n, 4), "full_rate": round(full / lottery_n, 4), "n_orderings": lottery_n}
    # X_acct, seeded (primary) and unseeded (sensitivity)
    for key, seeded in (("X_acct", True), ("X_acct_unseeded", False)):
        xa = method_X_acct(world, null, B, prule, seeded=seeded)
        xa_cf = method_X_acct(world, null, B, prule, seeded=seeded, honest=True)
        attr = {ad for ad in planted if ad in xa["reviewed"] and ad not in xa_cf["reviewed"]}
        out[key] = {**detect(planted, xa["reviewed"]), "attributable": detect(planted, attr), "spent": len(xa["reviewed"]),
                    "via_groups_planted": sorted(ad for ad in planted if ad in xa["via_groups"]),
                    "days": {d: {k: v for k, v in r.items() if k != "walked"} for d, r in xa["days"].items()}}
    # the cheapest rule
    if rule is not None and not rule.get("degenerate"):
        rr = method_rule(world, null, rule)
        out["rule"] = {**detect(planted, rr["reviewed"]), "attributable": detect(planted, rr["attributable"])}
    return out


# ── pooling and the table ───────────────────────────────────────────────────

def _flag(e: dict, method: str, attributable: bool) -> bool:
    if method == "lottery":
        return bool(e["lottery"]["rate"])
    m = e.get(method)
    if m is None:
        return False
    return bool((m["attributable"] if attributable else m)["detected"])


def _rate(e: dict, method: str, attributable: bool) -> float:
    """Detection as a rate in [0, 1] (the lottery's is its share of orderings)."""
    if method == "lottery":
        return float(e["lottery"]["rate"]) if "lottery" in e else 0.0
    return 1.0 if _flag(e, method, attributable) else 0.0


def recall_cell(evs: Sequence[dict], method: str, attributable: bool) -> dict:
    n = len(evs)
    if method == "lottery":
        rates = [e["lottery"]["rate"] for e in evs if "lottery" in e]
        return {"n": len(rates), "recall": round(mean(rates), 4) if rates else None, "reading": "nominal, mean over orderings",
                "full_recovery": round(mean([e["lottery"]["full_rate"] for e in evs if "lottery" in e]), 4) if rates else None}
    m = [e[method] for e in evs if method in e]
    if not m:
        return {"n": 0, "recall": None}
    src = [(x["attributable"] if attributable else x) for x in m]
    hits = sum(1 for x in src if x["detected"])
    return {"n": len(src), "detected": hits, "recall": round(hits / len(src), 4), "ci95": cp(hits, len(src)),
            "full_recovery": round(sum(1 for x in src if x["full"]) / len(src), 4),
            "membership_recall": round(mean([x["membership_recall"] for x in src]), 4)}


def gap_cell(evs: Sequence[dict], a: str, b: str, attributable: bool) -> dict:
    """recall_a - recall_b over the plants with a paired percentile bootstrap (seed 20261125)."""
    units = [(_rate(e, a, attributable), _rate(e, b, attributable)) for e in evs]

    def stat(us):
        return (sum(x for x, _ in us) - sum(y for _, y in us)) / len(us) if us else None

    bs = bootstrap(units, stat)
    return {**bs, "recall_a": round(mean([x for x, _ in units]), 4) if units else None,
            "recall_b": round(mean([y for _, y in units]), 4) if units else None, "a": a, "b": b}


def rho_cell(evs: Sequence[dict], attributable: bool = True) -> dict:
    """rho = (recall_X_doc - recall_P) / (recall_O - recall_P), recall_O the sealed composed flag, only
    where the interval of recall_O - recall_P has its lower bound above 0.1."""
    units = [(1.0 if e["o_flagged"] else 0.0, _rate(e, "P", attributable), _rate(e, "X_doc", attributable)) for e in evs]

    def den(us):
        return (sum(o for o, _, _ in us) - sum(p for _, p, _ in us)) / len(us) if us else None

    d = bootstrap(units, den)
    rO = round(mean([o for o, _, _ in units]), 4) if units else None
    rP = round(mean([p for _, p, _ in units]), 4) if units else None
    rX = round(mean([x for _, _, x in units]), 4) if units else None
    defined = d["ci95"][0] is not None and d["ci95"][0] > RHO_LOWER_MIN and d["point"] not in (None, 0)
    rho = round((rX - rP) / (rO - rP), 4) if defined else None
    return {"recall_O": rO, "recall_P": rP, "recall_X_doc": rX, "denominator": d, "defined": defined,
            "rho": rho, "note": None if defined else "undefined, components reported"}


def k_dependence(evs_by_arm: dict[str, list[dict]], attributable: bool = True) -> dict:
    """Review F3, fixed before the numbers: the k = 2 gap against the lone gap, paired by payload."""
    lone = {e["payload_id"]: e for e in evs_by_arm.get("lone", [])}
    k2 = {e["payload_id"]: e for e in evs_by_arm.get("k2", [])}
    pids = sorted(set(lone) & set(k2))
    units = []
    for pid in pids:
        g2 = _rate(k2[pid], "X_doc", attributable) - _rate(k2[pid], "P", attributable)
        g1 = _rate(lone[pid], "X_doc", attributable) - _rate(lone[pid], "P", attributable)
        units.append((g2, g1))

    def stat(us):
        return (sum(a for a, _ in us) - sum(b for _, b in us)) / len(us) if us else None

    bs = bootstrap(units, stat)
    gap_k2 = round(mean([a for a, _ in units]), 4) if units else None
    gap_lone = round(mean([b for _, b in units]), 4) if units else None
    within = (gap_k2 is not None and abs(gap_k2 - gap_lone) <= K_DEP_BAND)
    exceeds = (bs["ci95"][0] is not None and bs["ci95"][0] > 0)
    reading = ("artifact monitoring, not collusion detection" if within else
               ("collusion-specific recovery (the k = 2 gap exceeds the lone gap by more than its interval)" if exceeds else
                "no collusion-specific recovery claimed (the difference's interval includes zero)"))
    return {"n_payloads_paired": len(units), "gap_k2": gap_k2, "gap_lone": gap_lone,
            "difference": bs, "lone_within_0_1_of_k2": within, "k2_exceeds_lone_beyond_interval": exceeds, "reading": reading}


def summarise_layer(evs: Sequence[dict]) -> dict:
    """The document layer's operating point on d_c, pooled over worlds."""
    L = [e["X_doc"]["layer"] for e in evs if "X_doc" in e]
    if not L:
        return {}
    sizes = [s for l in L for s in l["group_sizes"].values()]
    return {"worlds": len(L), "documents_walked_per_day": round(mean([len(l["walked"]) for l in L]), 4),
            "full_per_day": round(mean([l["n_full"] for l in L]), 4), "partial_per_day": round(mean([l["n_partial"] for l in L]), 4),
            "writers_account_days_per_walked_document": round(mean(sizes), 4) if sizes else None,
            "account_days_spent_by_layer_per_day": round(mean([l["spent"] for l in L]), 4),
            "share_of_cap": round(mean([l["spent"] / l["cap"] for l in L if l["cap"]]), 4),
            "share_of_window_volume": round(sum(l["spent"] for l in L) / sum(e["volume"] for e in evs), 4),
            "fill_account_days_per_day": round(mean([l["filled"] for l in L]), 4),
            "honest_account_days_via_doc_per_day": round(mean([l["honest_account_days_via_doc"] for l in L]), 4),
            "honest_account_days_per_walked_document": round(sum(l["honest_account_days_via_doc"] for l in L) / max(1, sum(len(l["walked"]) for l in L)), 4),
            "plant_document_ranked_first": round(mean([1.0 if l["plant_rank"] == 1 else 0.0 for l in L]), 4),
            "plant_document_walked": round(mean([1.0 if l["plant_walked"] else 0.0 for l in L]), 4),
            "plant_rank_distribution": dict(sorted(Counter(l["plant_rank"] for l in L).items(), key=lambda kv: (kv[0] is None, kv[0]))),
            "candidates_per_day": round(mean([l["n_candidates"] for l in L]), 4),
            "detected_via_doc_share": round(mean([1.0 if e["X_doc"]["detected_via_doc"] else 0.0 for e in evs]), 4)}


def precision(evs: Sequence[dict], method: str) -> dict:
    spent = sum(e[method]["spent"] for e in evs if method in e)
    planted = sum(e[method]["members"] for e in evs if method in e)
    return {"account_days_reviewed": spent, "planted_reviewed": planted, "precision": round(planted / spent, 4) if spent else None}


def build_table(evals: dict[float, list[dict]]) -> dict:
    """Every regime x arm set x budget: recalls, gaps, rho, the layer's operating point."""
    table: dict[str, Any] = {}
    for B, evs in evals.items():
        for reg in REGIMES:
            for arm_key, arms in ARM_SETS.items():
                sub = [e for e in evs if e["regime"] == reg and e["arm"] in arms]
                if not sub:
                    continue
                cell: dict[str, Any] = {"n": len(sub), "B": B, "regime": reg, "arms": list(arms),
                                        "chance": sorted({e["chance"] for e in sub}),
                                        "volume_per_plant": sorted({e["volume"] for e in sub})}
                for attributable in (True, False):
                    tag = "attributable" if attributable else "nominal"
                    cell[tag] = {m: recall_cell(sub, m, attributable) for m in METHODS if m != "lottery"}
                    if attributable:
                        jc = [e["X_doc"]["attributable_joint_counterfactual"]["detected"] for e in sub]
                        cell[tag]["X_doc_joint_counterfactual_sensitivity"] = {"n": len(jc), "detected": sum(jc), "recall": round(sum(jc) / len(jc), 4)}
                    cell[tag]["gaps"] = {"X_doc_minus_P": gap_cell(sub, "X_doc", "P", attributable),
                                         "X_acct_minus_P": gap_cell(sub, "X_acct", "P", attributable),
                                         "X_acct_unseeded_minus_P": gap_cell(sub, "X_acct_unseeded", "P", attributable)}
                    cell[tag]["rho"] = rho_cell(sub, attributable)
                cell["lottery"] = recall_cell(sub, "lottery", False)
                cell["nominal"]["gaps"]["X_doc_minus_lottery"] = gap_cell(sub, "X_doc", "lottery", False)
                cell["precision"] = {m: precision(sub, m) for m in ("P", "X_doc", "X_acct", "X_acct_unseeded")}
                cell["document_layer"] = summarise_layer(sub)
                table[f"{reg}:{arm_key}:B{B}"] = cell
    return table


def predictions(table: dict, kdep: dict) -> dict:
    """Plan section 8, each against its result."""
    def g(reg, arm, B=PRIMARY_B):
        return table.get(f"{reg}:{arm}:B{B}")

    out = {}
    c23, c2, c3 = g("conforming", "k23"), g("conforming", "k2"), g("conforming", "k3")
    xa = [c["attributable"]["gaps"]["X_acct_minus_P"]["point"] for c in (c23, c2, c3) if c]
    out["1_X_acct_recovers_nothing_beyond_P_conforming"] = {
        "prediction": "attributable X_acct - P at most 0.05 at B = 0.10 (pooled k = 2 and 3, and each arm)",
        "values": {"k23": xa[0] if xa else None, "k2": xa[1] if len(xa) > 1 else None, "k3": xa[2] if len(xa) > 2 else None},
        "held": bool(xa) and all(v is not None and v <= 0.05 for v in xa)}
    xd = c2["attributable"]["gaps"]["X_doc_minus_P"] if c2 else None
    out["2_X_doc_minus_P_k2_conforming_at_least_0_2"] = {
        "prediction": "attributable X_doc - P at k = 2 in the conforming regime at least 0.2 at B = 0.10, bounded above by the composed view's recall of about a third",
        "value": xd["point"] if xd else None, "ci95": xd["ci95"] if xd else None,
        "recall_O_k2": c2["attributable"]["rho"]["recall_O"] if c2 else None,
        "held": bool(xd) and xd["point"] is not None and xd["point"] >= 0.2}
    sham = {}
    sham_ok = True
    for arm in ("lone", "k2", "k3"):
        s = g("sham", arm)
        if not s:
            continue
        k = {"lone": 1, "k2": 2, "k3": 3}[arm]
        band = chance(PRIMARY_B, k)
        row = {}
        for m in ("P", "X_doc"):
            nom = s["nominal"][m]
            half = ((nom["ci95"][1] - nom["ci95"][0]) / 2) if nom.get("ci95") else 0
            ok = nom["recall"] is not None and nom["recall"] <= band + half
            row[m] = {"nominal_recall": nom["recall"], "attributable_recall": s["attributable"][m]["recall"], "chance": band, "within_band": ok}
            sham_ok &= ok
        sham[arm] = row
    out["3a_sham_within_chance_band"] = {"prediction": "sham: P and X_doc nominal recall at most 1 - (1 - 0.10)^k plus the Clopper-Pearson half-width; attributable near zero",
                                         "values": sham, "held": sham_ok}
    al = {arm: (g("alarming", arm) or {}) for arm in ("lone", "k2", "k3", "k23")}
    alv = {arm: {"P_attributable": (c.get("attributable") or {}).get("P", {}).get("recall"),
                 "P_nominal": (c.get("nominal") or {}).get("P", {}).get("recall"),
                 "X_doc_minus_P_attributable": ((c.get("attributable") or {}).get("gaps") or {}).get("X_doc_minus_P", {}).get("point")}
           for arm, c in al.items() if c}
    out["3b_alarming_P_high_X_doc_minus_P_small"] = {"prediction": "alarming: P already high, attributable X_doc - P under 0.2",
                                                     "values": alv,
                                                     "held": all(v["X_doc_minus_P_attributable"] is not None and v["X_doc_minus_P_attributable"] < 0.2 for v in alv.values()) if alv else None}
    out["k_dependence_reading"] = kdep
    return out


# ── building the null and the worlds from the real caches ───────────────────

def author_label_parse(label: str) -> tuple[str, str]:
    """(author, path) from a P_author label `<stem>:P_author:<author>|owncloud:<path>/<d0>..<d1>`."""
    tail = label.split(":P_author:", 1)[1]
    author, rest = tail.split("|owncloud:", 1)
    path = rest.rsplit("/", 1)[0]
    return author, path


def author_scores_from(records: list[dict]) -> dict[tuple[str, str], float]:
    out = {}
    for r in records:
        if r.get("outcome") == "scored" and r.get("score") is not None:
            out[author_label_parse(r["label"])] = float(r["score"])
    return out


def build_null(rows: list[dict], honest_pown: list[dict], odiff_meta: dict, stem: str) -> Null:
    import score_fork_corpus as sfc
    keys, _day_idx, _by = sfc.account_days(rows)
    days = sorted({d for _a, d in keys})
    active = {d: sorted(a for a, dd in keys if dd == d) for d in days}
    scores, labels = {}, {}
    for r in honest_pown:
        if r.get("outcome") != "scored" or r.get("score") is None:
            continue
        lab = r["label"]                       # f"{stem}:P_own:{acct}/{day}"
        acct_day = lab.split(":P_own:")[1]
        acct, day = acct_day.rsplit("/", 1)
        scores[(acct, day)] = float(r["score"])
        labels[(acct, day)] = lab
    paths = sv.class_doc_paths()
    writes = class_writes(rows, paths)
    units: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for u in odiff_meta["rows"]:
        if u.get("outcome") != "scored" or u.get("score") is None:
            continue
        units[(u["path"], int(u["boundary_index"]))].append({"write_day": u["write_day"], "write_index": int(u["write_index"]),
                                                             "score": float(u["score"]), "label": u["label"]})
    return Null(days=days, active=active, scores=scores, labels=labels, writes=writes, odiff_units=dict(units), paths=paths)


def class_writes(rows: Sequence[dict], paths: Sequence[str]) -> list[tuple[str, str, str]]:
    out = []
    for r in rows:
        if sv.is_class_write(r, paths):
            out.append((sv.norm_path((r.get("args") or {}).get("path")), str(r.get("account")), str(r.get("ts"))[:10]))
    return out


def build_world(res: t1.PlantResult, null: Null, stem: str, planted_pown: dict[str, dict],
                planted_odiff: dict[str, dict], orule: dict, regime: str,
                planted_pauthor: dict[tuple[str, str, str], float] | None = None, ranker: str = "P_own") -> World:
    pstem = f"{stem}+t1v2+{res.payload_id}-{res.arm}"
    planted = [(a, d) for a, d in zip(res.authors, res.days)]
    scores, labels = {}, {}
    for a, d in planted:
        lab = f"{pstem}:P_own:{a}/{d}"
        rec = planted_pown.get(lab)
        if rec is None or rec.get("outcome") != "scored":
            raise KeyError(f"no scored planted P_own record for {lab}")
        scores[(a, d)] = float(rec["score"])
        labels[(a, d)] = lab
    bi = 0 if res.pre_window_boundary == "day0" else null.days.index(res.pre_window_boundary) + 1
    bname = f"start of {null.days[0]} (day-0 state)" if bi == 0 else f"end of {res.pre_window_boundary}"
    olab = f"{pstem}:O_diff:owncloud:{res.document}/{res.pre_window_boundary}..{res.composition_day}"
    orec = planted_odiff.get(olab)
    if orec is None or orec.get("outcome") != "scored":
        raise KeyError(f"no scored composed O_diff record for {olab}")
    hu = null.honest_unit(res.document, bi, res.composition_day)
    days = sorted(res.days)
    if days[-1] != res.composition_day:
        raise ValueError(f"{pstem}: composition day {res.composition_day} is not the last planted day {days[-1]}")
    a_scores = {}
    if planted_pauthor:
        for a in res.authors:
            k = (pstem, a, res.document)
            if k in planted_pauthor:
                a_scores[(a, res.document)] = planted_pauthor[k]
    return World(plant_id=f"{res.payload_id}-{res.arm}", payload_id=res.payload_id, arm=res.arm, regime=regime,
                 document=res.document, days=days, boundary_index=bi, boundary_name=bname, planted=planted,
                 scores=scores, labels=labels, writes=class_writes(res.rows, null.paths),
                 doc_score=float(orec["score"]), doc_label=olab,
                 doc_honest_score=(float(hu["score"]) if hu else None), doc_honest_label=(hu["label"] if hu else None),
                 o_flagged=th.is_flagged(float(orec["score"]), orule, olab), author_scores=a_scores, ranker=ranker)


def load_everything(ns) -> dict:
    corpus = Path(ns.corpus)
    seal = json.loads(Path(ns.seal).read_text(encoding="utf-8"))
    manifest = json.loads(Path(ns.plants).read_text(encoding="utf-8"))
    if manifest.get("payloads_sha256") != sha256_file(Path(ns.payloads)):
        raise SystemExit("refusing: the payload file differs from the one the plants were made from")
    if sha256_file(corpus) != seal.get("corpus_sha256"):
        raise SystemExit("refusing: the corpus differs from the seal's corpus")
    results = ts.regenerate(corpus, Path(ns.payloads), Path(ns.template), manifest)   # raises on a hash mismatch
    payloads = t1.load_payloads(Path(ns.payloads))
    pid2reg = {p["id"]: p.get("arm") or "conforming" for p in payloads}
    rows = sv.read_jsonl(corpus)
    stem = sv.stem_of(corpus)
    null = build_null(rows, read_jsonl(Path(ns.honest_pown)), json.loads(Path(ns.honest_odiff).read_text(encoding="utf-8")), stem)
    planted_pown = {r["label"]: r for r in read_jsonl(Path(ns.planted_pown))}
    planted_odiff = {r["label"]: r for r in read_jsonl(Path(ns.planted_odiff))}
    orule = seal["views"]["O_diff"]["rule"]
    prule = seal["views"]["P_own"]["rule"]
    order = sorted(results, key=lambda r: (REGIMES.index(pid2reg[r.payload_id]), r.payload_id, ARMS.index(r.arm)))
    ranker = getattr(ns, "ranker", "P_own") or "P_own"
    planted_pauthor: dict[tuple[str, str, str], float] = {}
    if ranker == "P_author":
        null.author_scores = author_scores_from(read_jsonl(Path(ns.honest_pauthor)))
        for r in read_jsonl(Path(ns.planted_pauthor)):
            if r.get("outcome") == "scored" and r.get("score") is not None:
                pstem_ = r["label"].split(":P_author:", 1)[0]
                a, p = author_label_parse(r["label"])
                planted_pauthor[(pstem_, a, p)] = float(r["score"])
    worlds = [build_world(r, null, stem, planted_pown, planted_odiff, orule, pid2reg[r.payload_id], planted_pauthor, ranker) for r in order]
    return {"seal": seal, "manifest": manifest, "results": order, "payloads": payloads, "rows": rows, "stem": stem,
            "null": null, "worlds": worlds, "orule": orule, "prule": prule, "pid2reg": pid2reg,
            "planted_pown": planted_pown, "planted_odiff": planted_odiff}


# ── the P_author ranker's coverage check (brief 07n part B, B2) ─────────────

def author_coverage(L: dict) -> dict:
    """Every writer account-day of every candidate document in every plant's window needs a P_author
    pair score: the planted writer's T1 v2 unit on the plant's document, the seal's honest pair otherwise."""
    null, worlds = L["null"], L["worlds"]
    missing = []
    n_pairs = 0
    seen = set()
    for w in worlds:
        units = Units(null, w.days)
        groups = doc_groups(world=w, null=null, units=units)
        for path, idxs in groups.items():
            for i in idxs:
                a = units.ads[i][0]
                key = (a, path, w.plant_id)
                if key in seen:
                    continue
                seen.add(key)
                n_pairs += 1
                have = (a, path) in w.author_scores or (a, path) in null.author_scores
                if not have:
                    missing.append({"writer": a, "document": path, "plant": w.plant_id})
    return {"writer_document_plant_triples": n_pairs, "missing": missing, "n_missing": len(missing),
            "honest_pairs": len(null.author_scores), "planted_pairs": sum(len(w.author_scores) for w in worlds),
            "pass": not missing}


# ── the fit check (plan section 9) ──────────────────────────────────────────

def fit_check(L: dict, ns) -> dict:
    null, worlds, manifest = L["null"], L["worlds"], L["manifest"]
    out: dict[str, Any] = {"version": VERSION, "plan_sha256": sha256_file(Path(ns.plan)) if ns.plan else None,
                           "plants_sha256": manifest["plants_sha256"], "plants_reproduce": True,
                           "n_plants": len(worlds), "n_planted_account_days": sum(w.k for w in worlds)}
    out["ii_scores"] = {"planted_P_own_scored": sum(w.k for w in worlds), "planted_P_own_expected": 288,
                        "composed_O_diff_scored": len(worlds), "composed_O_diff_expected": 152,
                        "every_planted_account_day_active_in_the_null": all(a in null.active[d] for w in worlds for a, d in w.planted),
                        "regimes": dict(Counter(w.regime for w in worlds)), "arms": dict(Counter(w.arm for w in worlds)),
                        "boundaries": dict(Counter(w.boundary_name for w in worlds)),
                        "composition_day_is_last_planted_day": True}
    cands = []
    missing = []
    for bi in (0, 1):
        for dc in null.days[bi:]:
            for p in null.paths:
                u = null.honest_unit(p, bi, dc)
                cands.append({"path": p, "boundary_index": bi, "upto_day": dc, "unit": (u["label"] if u else None),
                              "write_index": (u["write_index"] if u else None), "score": (u["score"] if u else None)})
                if u is None:
                    missing.append((p, bi, dc))
    used = {(w.document, w.boundary_index, w.d_c) for w in worlds} | {(p, w.boundary_index, w.d_c) for w in worlds for p in null.paths}
    out["iii_candidates"] = {"table": cands, "missing": missing, "used_combinations": len(used),
                             "plant_documents_with_honest_counterpart": sum(1 for w in worlds if w.doc_honest_score is not None)}
    out["iv_frozen"] = {"budget_cap": "grouping_measure.budget_cap (imported)", "top_accounts": "grouping_measure.top_accounts (imported)",
                        "review": "grouping_measure.review greedy (imported; run on account-day units)",
                        "G1": "re-implemented on the class-document edit rows (g1_groups) with tests",
                        "grouping_measure_sha256": sha256_file(Path(gm.__file__).resolve()),
                        "tests": "test_stage3_synthetic_q1q2.py (run separately; result recorded in the prep report)"}
    out["caps"] = {f"B{B}": {d: null.cap(B, d) for d in null.days} for B in BUDGETS}
    out["n_active"] = {d: len(null.active[d]) for d in null.days}
    out["honest_class_writer_days_per_document_and_day"] = {p: {d: len({a for pp, a, dd in null.writes if pp == p and dd == d}) for d in null.days} for p in null.paths}
    rule = fit_rule(null)
    out["cheapest_rule_fit"] = {k: rule[k] for k in ("threshold", "p_tie", "share_above", "share_at", "expected_rate", "n", "distinct_scores", "degenerate", "statistic")}
    out["pass"] = (not missing and out["ii_scores"]["every_planted_account_day_active_in_the_null"]
                   and out["ii_scores"]["planted_P_own_scored"] == 288 and out["ii_scores"]["composed_O_diff_scored"] == 152)
    return out


def fit_check_md(fc: dict) -> str:
    L = [f"# Fit check (plan section 9; {VERSION}; plan sha256 {str(fc.get('plan_sha256'))[:16]}…)\n",
         f"**Pass: {fc['pass']}.** (i) plants reproduce by hash `{fc['plants_sha256'][:16]}…`: {fc['plants_reproduce']}; "
         f"(ii) planted P_own scored {fc['ii_scores']['planted_P_own_scored']} of {fc['ii_scores']['planted_P_own_expected']}, composed O_diff {fc['ii_scores']['composed_O_diff_scored']} of {fc['ii_scores']['composed_O_diff_expected']}, "
         f"every planted account-day active in the null: {fc['ii_scores']['every_planted_account_day_active_in_the_null']}; "
         f"(iii) candidate honest units missing: {len(fc['iii_candidates']['missing'])} ({fc['iii_candidates']['missing'] or 'none'}); "
         f"(iv) {fc['iv_frozen']['review']}; G1 {fc['iv_frozen']['G1']}.\n",
         f"Regimes {fc['ii_scores']['regimes']}; arms {fc['ii_scores']['arms']}; boundaries {fc['ii_scores']['boundaries']}. "
         f"Active accounts {fc['n_active']}; caps {fc['caps']}.\n",
         f"Cheapest-rule fit (honest null, rate {RULE_RATE}): {fc['cheapest_rule_fit']}.\n",
         "| document | boundary | up to | honest unit | score |", "|---|---|---|---|---|"]
    for c in fc["iii_candidates"]["table"]:
        L.append(f"| {c['path'].split('/')[-1]} | b{c['boundary_index']} | {c['upto_day']} | {(c['unit'] or 'MISSING').split('/')[-1]} | {c['score']} |")
    L.append("\nHonest class writer-days per document and day: " + json.dumps(fc["honest_class_writer_days_per_document_and_day"]))
    return "\n".join(L) + "\n"


# ── the table ───────────────────────────────────────────────────────────────

def compute(L: dict, ns) -> dict:
    null, worlds, prule = L["null"], L["worlds"], L["prule"]
    rule = fit_rule(null)
    evals: dict[float, list[dict]] = {}
    for B in BUDGETS:
        rng = random.Random(LOTTERY_SEED)          # one stream per budget, plants in fit-check order
        evals[B] = [evaluate_world(w, null, B, prule, None if rule["degenerate"] else rule, rng) for w in worlds]
    table = build_table(evals)
    kdep = {f"B{B}": k_dependence({a: [e for e in evals[B] if e["regime"] == "conforming" and e["arm"] == a] for a in ARMS}, True) for B in BUDGETS}
    kdep_nom = k_dependence({a: [e for e in evals[PRIMARY_B] if e["regime"] == "conforming" and e["arm"] == a] for a in ARMS}, False)
    preds = predictions(table, {**kdep[f"B{PRIMARY_B}"], "nominal_at_B0.1": kdep_nom})
    primary = table[f"conforming:k23:B{PRIMARY_B}"]
    res = {"version": VERSION, "primary_cell": {"cell": f"conforming:k23:B{PRIMARY_B}", "n": primary["n"],
                                               "X_doc_minus_P_attributable": primary["attributable"]["gaps"]["X_doc_minus_P"],
                                               "recall_P": primary["attributable"]["P"], "recall_X_doc": primary["attributable"]["X_doc"],
                                               "sham_X_doc_attributable": table[f"sham:k23:B{PRIMARY_B}"]["attributable"]["X_doc"]["recall"],
                                               "sham_X_doc_nominal": table[f"sham:k23:B{PRIMARY_B}"]["nominal"]["X_doc"]["recall"],
                                               "lottery": primary["lottery"], "X_doc_minus_lottery_nominal": primary["nominal"]["gaps"]["X_doc_minus_lottery"]},
           "k_dependence": kdep, "k_dependence_nominal_B0.1": kdep_nom, "predictions": preds, "table": table,
           "cheapest_rule": rule, "per_world": {f"B{B}": evals[B] for B in BUDGETS},
           "deviations_from_plan": [
               "X_doc attribution: the first computed table (2026-10-26 05:10Z, superseded) used a joint counterfactual (member not reviewed anywhere in the world where the plant's document carries its honest unit and P uses honest scores); the plan's section 6 registers component rules (a P pick or fill is attributable under P's rule; a document-walk review iff the same day's walk under the honest document score, same free set, does not reach it); the Codex review (finding 1) caught the mismatch; this table follows the registered component rules, with the joint reading kept beside as 'X_doc_joint_counterfactual_sensitivity'",
               "G1 emission (X_acct): the plan registered 'a member wrote the document on d'; the frozen _touch_groups emits on any touch (reads included) that day; on this null every class document has a write every day, so the two coincide here (Codex finding 10, disclosed, not changed)",
               "lottery stream: one random.Random(20261126) stream per budget (B = 0.10, 0.05, 0.02), plants in fit-check order within each; the plan said one stream, which is read as one stream per budget so every budget sees the same 200 orderings per plant",
               "the k-dependence sentence's third case (the lone gap more than 0.1 above the k = 2 gap and the difference's interval covering zero) is reported as 'no collusion-specific recovery claimed'; the plan's two named cases do not cover it and no claim is made",
           ]}
    return res


def ranker_comparison(res: dict, base: dict) -> dict:
    """X_doc_author (this run's X_doc) against 07i's X_doc, paired by plant and budget (brief 07n B4)."""
    out: dict[str, Any] = {}
    for B in BUDGETS:
        mine = {e["plant_id"]: e for e in res["per_world"][f"B{B}"]}
        theirs = {e["plant_id"]: e for e in base["per_world"][f"B{B}"]}
        for reg in REGIMES:
            for arm_key, arms in ARM_SETS.items():
                ids = [pid for pid, e in mine.items() if e["regime"] == reg and e["arm"] in arms and pid in theirs]
                if not ids:
                    continue
                for attributable in (True, False):
                    units = [(_rate(mine[i], "X_doc", attributable), _rate(theirs[i], "X_doc", attributable)) for i in ids]
                    bs = bootstrap(units, lambda us: (sum(a for a, _ in us) - sum(b for _, b in us)) / len(us) if us else None)
                    out[f"{reg}:{arm_key}:B{B}:{'attributable' if attributable else 'nominal'}"] = {
                        **bs, "recall_X_doc_author": round(mean([a for a, _ in units]), 4), "recall_X_doc": round(mean([b for _, b in units]), 4),
                        "X_doc_minus_P_07i": base["table"][f"{reg}:{arm_key}:B{B}"]["attributable" if attributable else "nominal"]["gaps"]["X_doc_minus_P"]["point"]}
    # the planted writers' author scores against the honest writers' on the walked documents
    return out


def ranker_md(res: dict) -> str:
    rc = res.get("ranker_comparison") or {}
    L = ["\n## X_doc_author against 07i's X_doc (paired over plants, bootstrap seed 20261125)\n",
         "| cell | attributable: X_doc_author | X_doc (07i) | X_doc_author − X_doc [95%] | X_doc − P (07i) | nominal: X_doc_author − X_doc [95%] |", "|---|---|---|---|---|---|"]
    for B in BUDGETS:
        for reg in REGIMES:
            for arm_key in ("lone", "k2", "k3", "k23"):
                a = rc.get(f"{reg}:{arm_key}:B{B}:attributable")
                n = rc.get(f"{reg}:{arm_key}:B{B}:nominal")
                if not a:
                    continue
                L.append(f"| {reg} : {arm_key} : B{B} | {_r(a['recall_X_doc_author'])} | {_r(a['recall_X_doc'])} | {_r(a['point'])}{_ci(a)} | {_r(a['X_doc_minus_P_07i'])} | {_r(n['point'])}{_ci(n)} |")
    return "\n".join(L) + "\n"


def _r(v: Any) -> str:
    if v is None:
        return "–"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def _ci(c: dict | None) -> str:
    if not c or c.get("ci95") in (None, [None, None]):
        return ""
    return f" [{_r(c['ci95'][0])}, {_r(c['ci95'][1])}]"


def results_md(res: dict, meta: dict) -> str:
    pc = res["primary_cell"]
    g = pc["X_doc_minus_P_attributable"]
    L = [f"# Synthetic Q1/Q2 on the T1 v2 plants in the real honest world (brief 07i part 1; {meta.get('computed_at')}; plan sha256 {str(meta.get('plan_sha256'))[:16]}…, plants sha256 {str(meta.get('plants_sha256'))[:16]}…)\n",
         f"**Primary cell (conforming, k = 2 and 3 pooled, n = {pc['n']}, B = 0.10, attributable): recall_X_doc − recall_P = {_r(g['point'])}{_ci(g)} "
         f"(X_doc {_r(pc['recall_X_doc']['recall'])}, P {_r(pc['recall_P']['recall'])}; bootstrap {g['replicates']} replicates, seed {g['seed']}). "
         f"Sham X_doc (the document layer's empirical null): attributable {_r(pc['sham_X_doc_attributable'])}, nominal {_r(pc['sham_X_doc_nominal'])}. "
         f"Lottery (nominal, {pc['lottery'].get('n')} plants x 200 orderings) {_r(pc['lottery']['recall'])}; X_doc − lottery (nominal) {_r(pc['X_doc_minus_lottery_nominal']['point'])}{_ci(pc['X_doc_minus_lottery_nominal'])}.**\n"]
    kd = res["k_dependence"][f"B{PRIMARY_B}"]
    L.append(f"**k-dependence (review F3, fixed before the numbers; attributable, B = 0.10):** gap at k = 2 {_r(kd['gap_k2'])}, lone {_r(kd['gap_lone'])}, "
             f"difference {_r(kd['difference']['point'])}{_ci(kd['difference'])} over {kd['n_payloads_paired']} paired payloads: **{kd['reading']}**.\n")
    L.append("## Predictions against results\n")
    for k, p in res["predictions"].items():
        if k == "k_dependence_reading":
            continue
        L.append(f"- **{k}** — {p['prediction']}: held = **{p.get('held')}**; {json.dumps({kk: vv for kk, vv in p.items() if kk not in ('prediction', 'held')}, default=str)[:900]}")
    for B in BUDGETS:
        L.append(f"\n## B = {B} (caps {meta.get('caps', {}).get(f'B{B}')})\n")
        L.append("| regime : arms | n | chance | P honest-only baseline (nom) | P attr (nom) | X_doc attr (nom) | X_doc − P attr [95%] (nom) | X_acct attr (nom) | X_acct − P attr [95%] | lottery nom | X_doc − lottery nom [95%] | doc layer alone attr (nom), spend share | rule attr (nom) | X_acct unseeded attr (nom) | full recovery X_doc / P attr | ρ |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for reg in REGIMES:
            for arm_key in ("lone", "k2", "k3", "k23"):
                c = res["table"].get(f"{reg}:{arm_key}:B{B}")
                if not c:
                    continue
                A, N = c["attributable"], c["nominal"]
                rho = A["rho"]
                L.append(f"| {reg} : {arm_key} | {c['n']} | {','.join(_r(x) for x in c['chance'])} | {_r(N['P_honest_baseline']['recall'])} | {_r(A['P']['recall'])} ({_r(N['P']['recall'])}) | "
                         f"{_r(A['X_doc']['recall'])}{_ci(A['X_doc'])} ({_r(N['X_doc']['recall'])}) | {_r(A['gaps']['X_doc_minus_P']['point'])}{_ci(A['gaps']['X_doc_minus_P'])} ({_r(N['gaps']['X_doc_minus_P']['point'])}) | "
                         f"{_r(A['X_acct']['recall'])} ({_r(N['X_acct']['recall'])}) | {_r(A['gaps']['X_acct_minus_P']['point'])}{_ci(A['gaps']['X_acct_minus_P'])} | "
                         f"{_r(c['lottery']['recall'])} | {_r(N['gaps']['X_doc_minus_lottery']['point'])}{_ci(N['gaps']['X_doc_minus_lottery'])} | "
                         f"{_r(A['doc_layer']['recall'])} ({_r(N['doc_layer']['recall'])}), {_r(c['document_layer'].get('share_of_cap'))} | "
                         f"{_r(A.get('rule', {}).get('recall'))} ({_r(N.get('rule', {}).get('recall'))}) | {_r(A['X_acct_unseeded']['recall'])} ({_r(N['X_acct_unseeded']['recall'])}) | "
                         f"{_r(A['X_doc'].get('full_recovery'))} / {_r(A['P'].get('full_recovery'))} | {_r(rho['rho']) if rho['defined'] else 'undefined (O − P ' + _r(rho['denominator']['point']) + _ci(rho['denominator']) + ')'} |")
    c = res["table"][f"conforming:k23:B{PRIMARY_B}"]
    L.append("\n## The document layer's operating point (conforming k = 2 and 3, B = 0.10)\n")
    L.append(json.dumps(c["document_layer"], indent=None))
    L.append("\nPrecision (planted account-days reviewed / account-days reviewed, pooled over the cell's worlds): " + json.dumps(c["precision"]))
    L.append(f"\nCheapest class-wide rule (rung 0's edit frequency, re-fitted on the honest null at rate {RULE_RATE}; a re-fit, not rung 0's threshold): "
             + json.dumps({k: res['cheapest_rule'][k] for k in ('threshold', 'p_tie', 'expected_rate', 'honest_realised_rate', 'honest_realised_flagged', 'chance_at_rate', 'degenerate', 'statistic')})
             + ". **Reading:** the rule flags the insertion's volume, not its content: it catches the sham coalitions as often as the conforming ones (compare the 'rule' column across regimes), because the placeholder shape puts two or three one-line class edits on one account-day while 5 percent of honest account-days reach three; it is a property of T1's synthetic insertion, to be checked on the live world as an instrument look, and it does not bear on X_doc − P.")
    L.append("\n**Nominal readings and the author draw (review F2/F3 of 2026-10-26, Codex finding 9):** the nominal P recall in the sham regime exceeds chance (lone 7 of 24 against 0.10) because the inserter draws authors from the documents' writing pools and reuses them (36 authors carry the 288 planted account-days); the 'P_honest_baseline' column (the planted account-days the honest world's P reviews anyway) shows how much of each nominal reading is the author's own standing. The pre-registered chance-band formula is passed; it does not by itself establish a chance-level null, which the attributable readings (the lead) do.")
    if res.get("streaming"):
        L.append("\n## P10 streaming X_doc (sensitivity; new O_diff calls on the partial windows)\n")
        L.append(json.dumps(res["streaming"].get("summary"), indent=None))
    L.append("\n## Deviations from the plan\n")
    L += [f"- {d}" for d in res.get("deviations_from_plan", [])] or ["- none"]
    L.append(f"\nSealed instruments unchanged; no judge call in the table; model of the sealed scores {meta.get('model')}; frozen module sha256 {meta.get('grouping_measure_sha256', '')[:16]}…; script sha256 {meta.get('script_sha256', '')[:16]}….")
    return "\n".join(L) + "\n"


# ── P10: streaming X_doc (partial-window O_diff units; estimate first) ─────────

def partial_items(L: dict) -> list[dict]:
    """The O_diff units of every k = 2 / k = 3 plant's partial windows (boundary to the end of each
    window day before d_c), built as the composed units were (stage3_t1_score.build_items)."""
    null, stem, rows = L["null"], L["stem"], L["rows"]
    base = sv.seed_base()
    days = null.days
    items = []
    for res in L["results"]:
        if res.arm == "lone" or not res.composed:
            continue
        pstem = f"{stem}+t1v2+{res.payload_id}-{res.arm}"
        ref = doc.DocRef("owncloud", res.document)
        if res.pre_window_boundary == "day0":
            before, frm, bi = base[("owncloud", res.document)], f"start of {days[0]} (day-0 state)", 0
        else:
            before, frm, bi = doc.content_at(res.rows, ref, res.pre_window_boundary, base=base), f"end of {res.pre_window_boundary}", days.index(res.pre_window_boundary) + 1
        for d in sorted(res.days)[:-1]:
            after = doc.content_at(res.rows, ref, d, base=base)
            text = doc.unified_diff(before, after, res.document)
            label = f"{pstem}:O_diff:owncloud:{res.document}/{res.pre_window_boundary}..{d}"
            last_ts = max((w.ts for w in doc.content_writes(res.rows, ref) if w.ts[:10] == d), default=d)
            it = {"payload_id": res.payload_id, "arm": res.arm, "document": res.document, "path": res.document, "boundary": frm,
                  "boundary_index": bi, "write_day": d, "label": label}
            if not text:
                it.update({"skip": "unchanged", "packet": None, "truncated": False, "key": None})
            else:
                pk, trunc = sv.o_packet("O_diff", res.document, text, frm, last_ts)
                it.update({"skip": None, "packet": pk, "truncated": bool(trunc), "text_chars": len(text),
                           "key": sv.cache_key("O_diff", label, pk)})
            items.append(it)
    return items


def check_binding(seal: dict, model: str, corpus: Path) -> dict:
    b = seal.get("binding") or {}
    cur = {"model": model, "views_module_sha256": sv.file_sha256(Path(sv.__file__).resolve()),
           "document_module_sha256": sv.file_sha256(Path(doc.__file__).resolve()),
           "judge_client_sha256": sv.file_sha256(Path(sv.jc_mod.__file__).resolve()), "corpus_sha256": sv.file_sha256(corpus)}
    bad = {k: (b.get(k), v) for k, v in cur.items() if b.get(k) != v}
    if (b.get("prompt_records") or {}).get("O_diff") != sv.prompt_record("O_diff", 0):
        bad["prompt:O_diff"] = ("sealed", "current differs")
    return bad


def streaming_table(L: dict, recs: dict[str, dict], items: list[dict]) -> dict:
    """X_doc read day by day (the document walk on every window day, that day's units), beside P."""
    null, worlds, prule = L["null"], L["worlds"], L["prule"]
    by_plant: dict[str, dict[str, float]] = defaultdict(dict)
    missing = []
    for it in items:
        r = recs.get(it["key"]) if it["key"] else None
        if it["skip"]:
            continue
        if r is None or r.get("outcome") != "scored":
            missing.append(it["label"])
            continue
        by_plant[f"{it['payload_id']}-{it['arm']}"][it["write_day"]] = float(r["score"])
    out: dict[str, Any] = {"n_units": len(items), "n_skipped_unchanged": sum(1 for it in items if it["skip"]), "missing": missing, "cells": {}}
    for B in BUDGETS:
        evs = []
        for w in worlds:
            if w.arm == "lone":
                continue
            w.partial_doc_scores = by_plant.get(w.plant_id, {})
            if len(w.partial_doc_scores) != len(w.days) - 1:
                continue
            xs = method_X_doc(w, null, B, streaming=True)
            attr = xs["attributable"]
            p_rev = set().union(*method_P(w, null, B).values())
            p_hon = set().union(*method_P(w, null, B, honest=True).values())
            p_attr = {ad for ad in w.planted if ad in p_rev and ad not in p_hon}
            evs.append({"plant_id": w.plant_id, "payload_id": w.payload_id, "arm": w.arm, "regime": w.regime, "k": w.k, "B": B,
                        "chance": chance(B, w.k), "o_flagged": w.o_flagged, "volume": sum(null.cap(B, d) for d in w.days),
                        "X_doc": {**detect(w.planted, xs["reviewed"]), "attributable": detect(w.planted, attr), "spent": len(xs["reviewed"])},
                        "P": {**detect(w.planted, p_rev), "attributable": detect(w.planted, p_attr), "spent": len(p_rev)}})
        for reg in REGIMES:
            for arm_key in ("k2", "k3", "k23"):
                sub = [e for e in evs if e["regime"] == reg and e["arm"] in ARM_SETS[arm_key]]
                if sub:
                    out["cells"][f"{reg}:{arm_key}:B{B}"] = {"n": len(sub),
                                                             "attributable": {"P": recall_cell(sub, "P", True), "X_doc_streaming": recall_cell(sub, "X_doc", True),
                                                                              "X_doc_streaming_minus_P": gap_cell(sub, "X_doc", "P", True)},
                                                             "nominal": {"P": recall_cell(sub, "P", False), "X_doc_streaming": recall_cell(sub, "X_doc", False),
                                                                         "X_doc_streaming_minus_P": gap_cell(sub, "X_doc", "P", False)}}
    c = out["cells"].get(f"conforming:k23:B{PRIMARY_B}")
    out["summary"] = {"conforming_k23_B0.1": c, "sham_k23_B0.1_X_doc_streaming_attributable": (out["cells"].get(f"sham:k23:B{PRIMARY_B}") or {}).get("attributable", {}).get("X_doc_streaming", {}).get("recall")}
    return out


def streaming_from_cache(L: dict, ns, out_dir: Path, prefix: str = "") -> dict:
    """The P10 table from the existing cache (no call, so no binding check): every unit's key must be
    in the cache; used to recompute after the walk fix of 2026-10-26 (review finding 2)."""
    items = partial_items(L)
    model = ns.model
    cache = out_dir / f"judge-cache.q1q2.O_diff.{model.replace('.', '-')}.jsonl"
    recs = {r["cache_key"]: r for r in read_jsonl(cache)}
    missing = [it["label"] for it in items if it["key"] and it["key"] not in recs]
    if missing:
        raise SystemExit(f"refusing: {len(missing)} partial-window units are not in the cache (e.g. {missing[0]}); run --streaming")
    st = streaming_table(L, recs, items)
    est_rec = json.loads((out_dir / "streaming-estimate.json").read_text(encoding="utf-8"))
    st["spend"] = est_rec.get("run")
    st["estimate"] = est_rec.get("estimate")
    st["recomputed_from_cache"] = True
    st["ranker"] = getattr(ns, "ranker", "P_own")
    (out_dir / f"{prefix}streaming.json").write_text(json.dumps(st, indent=1, default=str), encoding="utf-8")
    (out_dir / f"{prefix}streaming.md").write_text(streaming_md(st, model, cache), encoding="utf-8")
    print(streaming_md(st, model, cache))
    return st


def streaming_md(st: dict, model: str, cache: Path) -> str:
    md = ["# P10 streaming X_doc (sensitivity; brief 07i part 1)" + (" (recomputed from the cache after the walk fix of 2026-10-26)" if st.get("recomputed_from_cache") else "") + "\n",
          f"Units {st['n_units']} (unchanged, skipped {st['n_skipped_unchanged']}; missing {len(st['missing'])}); estimate ${(st.get('estimate') or {}).get('est_cost_usd')}, spent ${((st.get('spend') or {}).get('dollars') or 0):.4f}; "
          f"model {model}; cache `{cache.name}`.\n", "| cell | n | P attr (nom) | X_doc streaming attr (nom) | X_doc streaming − P attr [95%] (nom) |", "|---|---|---|---|---|"]
    for key, c in st["cells"].items():
        A, N = c["attributable"], c["nominal"]
        md.append(f"| {key} | {c['n']} | {_r(A['P']['recall'])} ({_r(N['P']['recall'])}) | {_r(A['X_doc_streaming']['recall'])} ({_r(N['X_doc_streaming']['recall'])}) | "
                  f"{_r(A['X_doc_streaming_minus_P']['point'])}{_ci(A['X_doc_streaming_minus_P'])} ({_r(N['X_doc_streaming_minus_P']['point'])}) |")
    return "\n".join(md) + "\n"


async def run_streaming(L: dict, ns, out_dir: Path, estimate_only: bool) -> dict:
    items = partial_items(L)
    model = ns.model
    est = sv.estimate(items, sv.system_prompt("O_diff"), model)
    bad = check_binding(L["seal"], model, Path(ns.corpus))
    rec = {"version": VERSION, "n_items": len(items), "n_skipped_unchanged": sum(1 for it in items if it["skip"]), "estimate": est,
           "cap_usd": P10_CAP_USD, "binding_mismatch": bad, "run": None}
    (out_dir / "streaming-estimate.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec, indent=1), file=sys.stderr)
    if estimate_only:
        return rec
    if bad:
        raise SystemExit(f"refusing: the instrument differs from the sealed binding: {bad}")
    if est["est_cost_usd"] > P10_CAP_USD:
        raise SystemExit(f"not run: the estimate ${est['est_cost_usd']} exceeds the P10 cap ${P10_CAP_USD}")
    cache = out_dir / f"judge-cache.q1q2.O_diff.{model.replace('.', '-')}.jsonl"
    jc = sv.make_client("O_diff", cache, model, concurrency=ns.concurrency, rpm=ns.rpm, spend_cap_usd=P10_CAP_USD)
    recs, aborted = await sv.score_items(jc, items, "O_diff", 0)
    jc.batch_log(out_dir / "judge-batches.jsonl", note="q1q2 P10 partial windows" + (" ABORTED" if aborted else ""))
    rec["run"] = {"dollars": jc.stats()["dollars"], "aborted": aborted, "stats": jc.stats()}
    if aborted:
        (out_dir / "streaming-estimate.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
        raise SystemExit(f"ABORTED: {aborted}")
    st = streaming_table(L, recs, items)
    st["spend"] = rec["run"]
    st["estimate"] = est
    (out_dir / "streaming.json").write_text(json.dumps(st, indent=1, default=str), encoding="utf-8")
    md = streaming_md(st, model, cache)
    (out_dir / "streaming.md").write_text(md, encoding="utf-8")
    (out_dir / "streaming-estimate.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(md)
    return st


# ── main ────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--payloads", required=True)
    ap.add_argument("--plants", required=True)
    ap.add_argument("--seal", required=True)
    ap.add_argument("--honest-pown", required=True, help="views/judge-cache.P_own.*.jsonl")
    ap.add_argument("--honest-odiff", required=True, help="views/o_diff_cumulative.json")
    ap.add_argument("--planted-pown", required=True, help="t1v2/judge-cache.t1v2.P_own.*.jsonl")
    ap.add_argument("--planted-odiff", required=True, help="t1v2/judge-cache.t1v2.O_diff.*.jsonl")
    ap.add_argument("--plan", default=None)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--template", default=str(sv.jc_mod.FORK / "bootstrap" / "org_template.yaml"))
    ap.add_argument("--model", default=MODEL_DEFAULT)
    ap.add_argument("--fit-check", action="store_true")
    ap.add_argument("--ranker", choices=("P_own", "P_author"), default="P_own", help="the within-document order (brief 07n part B)")
    ap.add_argument("--honest-pauthor", default=None, help="views/judge-cache.P_author.*.jsonl (ranker P_author)")
    ap.add_argument("--planted-pauthor", default=None, help="t1v2/judge-cache.t1v2.P_author.*.jsonl (ranker P_author)")
    ap.add_argument("--coverage", action="store_true", help="ranker P_author: write author-ranker-coverage.json and stop")
    ap.add_argument("--baseline-results", default=None, help="ranker P_author: 07i's results.json for the X_doc columns beside")
    ap.add_argument("--streaming-estimate", action="store_true")
    ap.add_argument("--streaming", action="store_true")
    ap.add_argument("--streaming-from-cache", action="store_true")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--rpm", type=int, default=40)
    return ap


def main(argv: list[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)
    out_dir = Path(ns.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    L = load_everything(ns)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    prefix = "author-ranker-" if ns.ranker == "P_author" else ""
    if ns.ranker == "P_author":
        if not (ns.honest_pauthor and ns.planted_pauthor):
            raise SystemExit("ranker P_author needs --honest-pauthor and --planted-pauthor")
        cov = author_coverage(L)
        cov["checked_at"] = now
        (out_dir / "author-ranker-coverage.json").write_text(json.dumps(cov, indent=1), encoding="utf-8")
        print(json.dumps({k: v for k, v in cov.items() if k != "missing"} | {"missing_head": cov["missing"][:10]}, indent=1), file=sys.stderr)
        if ns.coverage:
            return 0 if cov["pass"] else 1
        if not cov["pass"]:
            raise SystemExit(f"refusing: {cov['n_missing']} writer-document units have no P_author score (plan B2: score them first)")
    if ns.fit_check:
        fc = fit_check(L, ns)
        fc["checked_at"] = now
        (out_dir / "fit-check.json").write_text(json.dumps(fc, indent=1, default=str), encoding="utf-8")
        md = fit_check_md(fc)
        (out_dir / "fit-check.md").write_text(md, encoding="utf-8")
        print(md)
        return 0 if fc["pass"] else 1
    if ns.streaming_from_cache:
        streaming_from_cache(L, ns, out_dir, prefix)
        return 0
    if ns.streaming_estimate or ns.streaming:
        import asyncio
        asyncio.run(run_streaming(L, ns, out_dir, estimate_only=ns.streaming_estimate))
        return 0
    fc_path = out_dir / "fit-check.json"
    if not fc_path.exists() or not json.loads(fc_path.read_text(encoding="utf-8")).get("pass"):
        raise SystemExit("refusing: run --fit-check first and resolve it (plan section 9)")
    res = compute(L, ns)
    null = L["null"]
    meta = {"computed_at": now, "plan_sha256": sha256_file(Path(ns.plan)) if ns.plan else None,
            "plants_sha256": L["manifest"]["plants_sha256"], "payloads_sha256": L["manifest"]["payloads_sha256"],
            "inserter_sha256": L["manifest"].get("inserter_sha256"), "script_sha256": sha256_file(Path(__file__).resolve()),
            "grouping_measure_sha256": sha256_file(Path(gm.__file__).resolve()), "model": L["seal"]["binding"]["model"],
            "seal": {"file": str(ns.seal), "tie_seed": L["seal"]["tie_seed"], "P_own_rule": L["prule"], "O_diff_rule": L["orule"]},
            "caps": {f"B{B}": {d: null.cap(B, d) for d in null.days} for B in BUDGETS}, "n_active": {d: len(null.active[d]) for d in null.days},
            "seeds": {"layout": 20261113, "tie": L["seal"]["tie_seed"], "bootstrap": BOOT_SEED, "lottery": LOTTERY_SEED},
            "n_worlds": len(L["worlds"]), "fit_check": fc_path.name}
    st_path = out_dir / f"{prefix}streaming.json"
    if st_path.exists():
        res["streaming"] = json.loads(st_path.read_text(encoding="utf-8"))
    meta["ranker"] = ns.ranker
    res["meta"] = meta
    if ns.ranker == "P_author" and ns.baseline_results:
        res["ranker_comparison"] = ranker_comparison(res, json.loads(Path(ns.baseline_results).read_text(encoding="utf-8")))
    (out_dir / f"{prefix}results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    md = results_md(res, meta)
    if ns.ranker == "P_author":
        md = md.replace("X_doc", "X_doc_author", 1) + ranker_md(res)
    (out_dir / f"{prefix}results.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
