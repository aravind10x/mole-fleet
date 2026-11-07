#!/usr/bin/env python3
"""Brief 30 note 9 item 2: the $0 forecast of the six-round course with writer round 1's yields folded in. Blue side;
numpy and the matching module only; no file read except through the CLI's named inputs; no model call.

Course A (notes 7 and 8): writer rounds at the cap continue while the matched effective n is below 26 and fewer than six
rounds have run; the floor rule stops the course after rounds 3 to 5 when the projected effective n at round 6 is below 12.
`replicate_course_a` re-runs the reconciled proposal's own model (two writers, per-pair Jeffreys posteriors from E2, losses
0.8, all certified items counted as matched) with this code, so the new forecast can be read beside figures this code
reproduces (the reconcile's 0.93 and 0.70). The new forecast replaces the all-matched statistic by the matched one
(`stage3_elicitation_matching`, 10-point band within writer x document) and the two writers by one.

Assumptions the forecast states and does not test: a writer's yields per valid item are constant across rounds (or drift
by the stated factor); class is independent of document and composition; the strata of future items are drawn from an
invented model (6 documents uniform, composition a clipped normal of spread 17.3) or from round 1's own observed
(document, composition) pairs; the floor rule's projection scales the cumulative counts by the planned items.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_elicitation_matching as mt  # noqa: E402

VERSION = "elicitation-forecast/v0"
SEED = 20261216            # unused by any earlier brief or script (checked by grep, 2026-11-07)
STOP_NEFF = 26.0
M_ROUNDS = 6
FLOOR_NEFF = 12.0
PLAN_ONE_WRITER = [24, 96, 96, 96, 96, 96]
LOSS = 0.8                 # the reconcile's validity and quiet losses, applied to per-rater-quiet-candidate rates
N_DOCUMENTS = 6
COMP_MEAN, COMP_SD = 50.0, 17.3


def jeffreys(k: int, n: int) -> tuple[float, float]:
    return (0.5 + k, 0.5 + n - k)


def drift_factor(r: int, kind: str) -> float:
    """The multiplier on the illegible rate at round r: none, or halving linearly from round 1 to round 4, then held."""
    if kind == "none":
        return 1.0
    if kind == "halving":
        return 1.0 - 0.5 * min(1.0, (r - 1) / 3.0)
    raise ValueError(f"unknown drift {kind!r}")


def neff(c: np.ndarray, i: np.ndarray) -> np.ndarray:
    c, i = np.asarray(c, dtype=float), np.asarray(i, dtype=float)
    out = np.zeros(np.broadcast(c, i).shape)
    ok = (c > 0) & (i > 0)
    out[ok] = 2.0 / (1.0 / np.broadcast_to(c, out.shape)[ok] + 1.0 / np.broadcast_to(i, out.shape)[ok])
    return out


def round_counts(rng: np.random.Generator, n_items: np.ndarray, p_c: np.ndarray, p_i: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Certified and illegible counts among n_items, per run: certified with p_c, then illegible with p_i among the rest."""
    n_items = np.asarray(n_items, dtype=np.int64)
    p_c, p_i = np.clip(np.asarray(p_c, dtype=float), 0, 1), np.clip(np.asarray(p_i, dtype=float), 0, 1)
    c = rng.binomial(n_items, p_c)
    q = np.where(p_c < 1.0, p_i / np.maximum(1.0 - p_c, 1e-12), 0.0)
    i = rng.binomial(n_items - c, np.clip(q, 0, 1))
    return c, i


def floor_stops(c: np.ndarray, i: np.ndarray, r: int, plan: Sequence[int], M: int = M_ROUNDS, floor: float = FLOOR_NEFF) -> np.ndarray:
    """After round r: stop if the projected effective n at round M is below `floor`, the cumulative counts scaled by the
    planned items (the reconcile's 'from the cumulative rates', all certified items counted as matched)."""
    scale = float(sum(plan[:M])) / float(sum(plan[:r]))
    return neff(np.asarray(c) * scale, np.asarray(i) * scale) < floor


def _decide(C: np.ndarray, I: np.ndarray, stat: np.ndarray, plan: Sequence[int], stop: float, M: int, floor: float) -> dict:
    """The course on cumulative counts C, I (runs x M) and the stop statistic `stat` (runs x M)."""
    runs = C.shape[0]
    outcome = np.full(runs, "limit", dtype=object)
    stop_round = np.full(runs, M)
    alive = np.ones(runs, dtype=bool)
    for r in range(1, M + 1):
        win = alive & (stat[:, r - 1] >= stop)
        outcome[win], stop_round[win] = "success", r
        alive &= ~win
        if floor > 0 and 3 <= r <= M - 1:
            fl = alive & floor_stops(C[:, r - 1], I[:, r - 1], r, plan, M, floor)
            outcome[fl], stop_round[fl] = "floor", r
            alive &= ~fl
    return {"outcome": outcome, "stop_round": stop_round}


def _cumulative(rng, runs: int, plan: Sequence[int], M: int, sampler) -> tuple[np.ndarray, np.ndarray]:
    C, I = np.zeros((runs, M)), np.zeros((runs, M))
    c_cum, i_cum = np.zeros(runs), np.zeros(runs)
    for r in range(1, M + 1):
        c, i = sampler(rng, r)
        c_cum, i_cum = c_cum + c, i_cum + i
        C[:, r - 1], I[:, r - 1] = c_cum, i_cum
    return C, I


def course_all_matched(rng: np.random.Generator, runs: int, plan: Sequence[int], p_c: np.ndarray, p_i: np.ndarray, stop: float = STOP_NEFF,
                       M: int = M_ROUNDS, floor: float = FLOOR_NEFF, v: np.ndarray | None = None, drift: str = "none",
                       first: tuple[int, int] | None = None) -> dict:
    """The course with every certified item counted as matched (the reconcile's statistic), one rate pair per run; `first`,
    when given, is round 1's (certified, illegible) as observed."""
    def sampler(rg, r):
        if r == 1 and first is not None:
            return np.full(runs, first[0]), np.full(runs, first[1])
        n = np.full(runs, plan[r - 1])
        if v is not None:
            n = rg.binomial(n, v)
        return round_counts(rg, n, p_c, p_i * drift_factor(r, drift))
    C, I = _cumulative(rng, runs, plan, M, sampler)
    N = neff(C, I)
    return {**_decide(C, I, N, plan, stop, M, floor), "cum_c": C, "cum_i": I, "all_n_eff": N}


def _strata_draw(rng: np.random.Generator, n: int, model: str, empirical: Sequence[tuple[str, float]] | None) -> list[tuple[str, float]]:
    if n == 0:
        return []
    if model == "invented":
        docs = rng.integers(0, N_DOCUMENTS, n)
        comp = np.clip(rng.normal(COMP_MEAN, COMP_SD, n), 0.0, 100.0)
        return [(f"d{int(d)}", float(c)) for d, c in zip(docs, comp)]
    if model == "empirical":
        if not empirical:
            raise ValueError("empirical strata need round 1's observed (document, composition) pairs")
        idx = rng.integers(0, len(empirical), n)
        return [empirical[int(k)] for k in idx]
    raise ValueError(f"unknown strata model {model!r}")


def course_matched(rng: np.random.Generator, runs: int, plan: Sequence[int], p_c: np.ndarray, p_i: np.ndarray, v: np.ndarray, strata: str,
                   width: float = mt.BAND_WIDTH, stop: float = STOP_NEFF, M: int = M_ROUNDS, floor: float = FLOOR_NEFF, drift: str = "none",
                   first: Mapping[str, Any] | None = None, empirical: Sequence[tuple[str, float]] | None = None) -> dict:
    """The course with the matched statistic: each certified and illegible item carries a (document, composition) stratum
    and the statistic is `mt.match` on the cumulative items. `first`, when given, is round 1 as observed
    ({"c": certified, "i": illegible, "items": [{"document", "composition", "class"}]}); otherwise round 1 is sampled too."""
    C, I = np.zeros((runs, M)), np.zeros((runs, M))
    MN = np.zeros((runs, M))
    for run in range(runs):
        items: list[dict] = []
        c_cum = i_cum = 0
        for r in range(1, M + 1):
            if r == 1 and first is not None:
                c, i = int(first["c"]), int(first["i"])
                items += [dict(x, writer="w") for x in first["items"]]
            else:
                n = int(rng.binomial(plan[r - 1], v[run]))
                c, i = (int(x[0]) for x in round_counts(rng, np.array([n]), p_c[run:run + 1], p_i[run:run + 1] * drift_factor(r, drift)))
                for doc, comp in _strata_draw(rng, c, strata, empirical):
                    items.append({"writer": "w", "document": doc, "composition": comp, "class": mt.CERTIFIED})
                for doc, comp in _strata_draw(rng, i, strata, empirical):
                    items.append({"writer": "w", "document": doc, "composition": comp, "class": mt.ILLEGIBLE})
            c_cum, i_cum = c_cum + c, i_cum + i
            C[run, r - 1], I[run, r - 1] = c_cum, i_cum
            MN[run, r - 1] = mt.match(items, width)["n_eff"]
    return {**_decide(C, I, MN, plan, stop, M, floor), "cum_c": C, "cum_i": I, "all_n_eff": neff(C, I), "matched_n_eff": MN}


def replicate_course_a(runs: int = 40000, seed: int = SEED) -> dict:
    """The reconciled proposal's model, re-run here: two writers (rounds of 24 then 96 per writer), half the candidates under
    each reader pair, per-pair Jeffreys posteriors from E2 (the pair of Kimi pinned + Sol: 12 and 2 of 78; Kimi pinned +
    Sonnet 5.5: 3 and 2 of 37, per rater-quiet candidate), losses 0.8, the stop at an all-matched n_eff of 26, the floor
    rule. `halving` takes the illegible rate to half by round 4."""
    plan = [48, 192, 192, 192, 192, 192]
    pairs = [(jeffreys(12, 78), jeffreys(2, 78)), (jeffreys(3, 37), jeffreys(2, 37))]
    out = {}
    for name, drift in (("no_drift", "none"), ("halving", "halving")):
        rng = np.random.default_rng(seed)
        pc = [rng.beta(a, b, runs) * LOSS for (a, b), _ in pairs]
        pi = [rng.beta(a, b, runs) * LOSS for _, (a, b) in pairs]

        def sampler(rg, r, pc=pc, pi=pi, drift=drift):
            c = i = 0
            for k in range(2):
                ck, ik = round_counts(rg, np.full(runs, plan[r - 1] // 2), pc[k], pi[k] * drift_factor(r, drift))
                c, i = c + ck, i + ik
            return c, i
        C, I = _cumulative(rng, runs, plan, M_ROUNDS, sampler)
        N = neff(C, I)
        d = _decide(C, I, N, plan, STOP_NEFF, M_ROUNDS, FLOOR_NEFF)
        succ = d["outcome"] == "success"
        at = d["stop_round"] - 1
        cs, is_ = C[np.arange(runs), at], I[np.arange(runs), at]
        out[name] = {"p_success": float(succ.mean()), "p_floor": float((d["outcome"] == "floor").mean()),
                     "median_certified_illegible_at_stop": [float(np.median(cs)), float(np.median(is_))],
                     "p_limit": float((d["outcome"] == "limit").mean()), "mean_rounds_beyond_3": float(np.maximum(d["stop_round"] - 3, 0).mean()),
                     "median_certified_illegible_after_round_6": [float(np.median(C[:, -1])), float(np.median(I[:, -1]))]}
    out["runs"], out["seed"] = runs, seed
    return out


def one_writer_original(runs: int = 40000, seed: int = SEED) -> float:
    """Course A's own model with the second writer removed: one writer (rounds of 24 then 96), the Kimi pinned + Sonnet 5.5
    pair's E2 rates per rater-quiet candidate, the reconcile's losses of 0.8, all certified items matched; P(n_eff of 26)."""
    plan = list(PLAN_ONE_WRITER)
    rng = np.random.default_rng(seed)
    pc = rng.beta(*jeffreys(3, 37), runs) * LOSS
    pi = rng.beta(*jeffreys(2, 37), runs) * LOSS
    res = course_all_matched(rng, runs, plan, pc, pi)
    return float(np.mean(res["outcome"] == "success"))


# ── the forecast with round 1 folded in ───────────────────────────────────────────────────────────────────────

E2_SONNET_PAIR = {"certified": 3, "illegible": 2, "n": 37}     # E2's rater-quiet candidates read by Kimi pinned + Sonnet 5.5


def posteriors(round1: Mapping[str, Any]) -> dict:
    """Beta parameters per scenario: `round1_only` is Jeffreys on round 1's counts; `e2_prior_plus_round1` adds round 1 to
    E2's rates for the Sonnet 5.5 pair, per rater-quiet candidate and so scaled by the losses (0.8), with the weight of
    E2's 37 items."""
    n_v, k_c, k_i = int(round1["valid"]), int(round1["certified"]), int(round1["illegible"])
    v = list(jeffreys(n_v, int(round1["written"])))
    n = E2_SONNET_PAIR["n"]
    # E2's rates are per rater-quiet candidate; per valid item written they scale by the share of valid items that are
    # rater-quiet. Round 1's own share (13 of 20) is used when the record has it; else the reconcile's combined 0.8
    q = (float(round1["quiet"]) / n_v) if round1.get("quiet") is not None else LOSS
    a_c, a_i = q * E2_SONNET_PAIR["certified"], q * E2_SONNET_PAIR["illegible"]
    return {"round1_only": {"p_c": list(jeffreys(k_c, n_v)), "p_i": list(jeffreys(k_i, n_v)), "v": v},
            # round 1 not folded in: one writer at E2's rates for the Sonnet 5.5 pair, round 1 sampled like the rest (the
            # decomposition of the fall from course A's figure into the lost second writer and round 1's evidence)
            "e2_prior_only": {"p_c": [a_c, n - a_c], "p_i": [a_i, n - a_i], "v": v},
            "e2_prior_plus_round1": {"p_c": [a_c + k_c, n - a_c + (n_v - k_c)], "p_i": [a_i + k_i, n - a_i + (n_v - k_i)], "v": v}}


def _stats(x: np.ndarray) -> dict:
    return {"mean": round(float(np.mean(x)), 3), "p10": round(float(np.percentile(x, 10)), 3), "p90": round(float(np.percentile(x, 90)), 3)}


def _summarise(res: Mapping[str, Any], matched: bool) -> dict:
    o, sr = res["outcome"], res["stop_round"]
    out = {"p_success_by_round": {str(r): round(float(np.mean((o == "success") & (sr <= r))), 4) for r in range(2, 7)},
           "p_success": round(float(np.mean(o == "success")), 4), "p_floor": round(float(np.mean(o == "floor")), 4),
           "p_limit": round(float(np.mean(o == "limit")), 4),
           "p_floor_after_round": {str(r): round(float(np.mean((o == "floor") & (sr == r))), 4) for r in (3, 4, 5)},
           "certified_after": {str(r): _stats(res["cum_c"][:, r - 1]) for r in (3, 6)},
           "illegible_after": {str(r): _stats(res["cum_i"][:, r - 1]) for r in (3, 6)},
           "all_matched_n_eff_after": {str(r): _stats(res["all_n_eff"][:, r - 1]) for r in (3, 6)}}
    if matched:
        out["matched_n_eff_after"] = {str(r): _stats(res["matched_n_eff"][:, r - 1]) for r in (3, 6)}
    return out


def forecast(round1: Mapping[str, Any], runs_all: int = 40000, runs_matched: int = 4000, seed: int = SEED, width: float = mt.BAND_WIDTH) -> dict:
    """round1: {"written", "valid", "certified", "illegible", "items": [round 1's certified and illegible items as
    {"document", "composition", "class"}], "valid_strata": [(document, composition) of every valid item]}."""
    post = posteriors(round1)
    first = {"c": int(round1["certified"]), "i": int(round1["illegible"]), "items": list(round1["items"])}
    empirical = [tuple(x) for x in round1["valid_strata"]]
    out: dict[str, Any] = {"version": VERSION, "seed": seed, "runs_all_matched": runs_all, "runs_matched": runs_matched, "width": width,
                           "plan_written_per_round": PLAN_ONE_WRITER, "stop_n_eff": STOP_NEFF, "floor_n_eff": FLOOR_NEFF, "rounds": M_ROUNDS,
                           "round1": {k: round1[k] for k in ("written", "valid", "certified", "illegible") + (("quiet",) if round1.get("quiet") is not None else ())}, "posteriors": post,
                           "replication": replicate_course_a(runs=runs_all, seed=seed),
                           "one_writer_original_p_success": one_writer_original(runs=runs_all, seed=seed), "scenarios": {}}
    for si, (name, pr) in enumerate(post.items()):
        out["scenarios"][name] = {}
        for di, drift in enumerate(("none", "halving")):
            row: dict[str, Any] = {}
            fold = name != "e2_prior_only"
            rng = np.random.default_rng([seed, si, di, 0])
            rates = lambda n, g: (g.beta(*pr["p_c"], n), g.beta(*pr["p_i"], n), g.beta(*pr["v"], n))  # noqa: E731
            pc, pi, v = rates(runs_all, rng)
            res = course_all_matched(rng, runs_all, PLAN_ONE_WRITER, pc, pi, v=v, drift=drift, first=(first["c"], first["i"]) if fold else None)
            row["all_matched"] = _summarise(res, matched=False)
            for ki, strata in enumerate(("invented", "empirical")):
                rng = np.random.default_rng([seed, si, di, 1 + ki])
                pc, pi, v = rates(runs_matched, rng)
                res = course_matched(rng, runs_matched, PLAN_ONE_WRITER, pc, pi, v, strata, width=width, drift=drift, first=first if fold else None, empirical=empirical)
                row[f"matched_{strata}"] = _summarise(res, matched=True)
            out["scenarios"][name][drift] = row
    return out


def canonical(obj: Any) -> str:
    import json
    return json.dumps(obj, sort_keys=True, indent=1, default=float) + "\n"


def load_round1(part3: Path, writer: str, round_no: int) -> dict:
    """Round 1's aggregates and its items' (document, composition, class), from the files the round wrote under part3/."""
    import json
    P = Path(part3)
    rec = json.loads((P / f"round-{round_no}-v0.json").read_text(encoding="utf-8"))["writers"][writer]["funnel"]
    rr = json.loads((P / f"round-{round_no}" / writer / "round-record.json").read_text(encoding="utf-8"))["ids_by_class"]
    key = json.loads((P / f"round-{round_no}" / writer / "converted" / "key.json").read_text(encoding="utf-8"))["triples"]
    comp = json.loads((P / "raters" / f"{writer}-r{round_no}-cert" / "gate-i.json").read_text(encoding="utf-8"))["composition"]
    items = [{"document": key[i]["document"], "composition": float(comp[i]), "class": cls}
             for cls in ("certified", "quiet_but_illegible") for i in sorted(rr.get(cls, []))]
    every = sorted(i for ids in rr.values() for i in ids)
    return {"written": int(rec["written"]), "valid": int(rec["valid"]), "quiet": int(rec["quiet"]), "certified": int(rec["certified"]),
            "illegible": int(rec["quiet_but_illegible"]), "items": items,
            "valid_strata": [(key[i]["document"], float(comp[i])) for i in every]}


def render_md(res: Mapping[str, Any], module_sha: str = "") -> str:
    """The forecast record: method, the replication check, the scenarios, and a plain reading. Aggregates only."""
    f = lambda x: f"{x:.2f}"  # noqa: E731
    st = lambda d: f"{d['mean']:.1f} [{d['p10']:.0f}, {d['p90']:.0f}]"  # noqa: E731
    rep = res["replication"]
    L = []
    L.append("# Forecast of the six-round course with round 1's yields folded in (brief 30 dated note 9 item 2)\n")
    L.append(f"Written 2026-11-07 by the Part 3 session (Sonnet 5.5). $0, no model call, no item, no B3 file. Module `stage3_elicitation_forecast.py` {module_sha}, seed {res['seed']}, {res['runs_all_matched']} runs per all-matched cell and {res['runs_matched']} per matched cell. Counts and aggregates only.\n")
    r1 = res["round1"]
    L.append("## What is forecast\n")
    L.append(f"One writer (GPT-6.1-sol), writer rounds 2 to 6 at the cap of 96 items written, round 1 as observed (24 written, {r1['valid']} valid, {r1['certified']} certified, {r1['illegible']} quiet-but-illegible). The course is note 8's: rounds continue while the matched effective n is below 26 and fewer than six rounds have run; the floor rule stops it after rounds 3 to 5 when the projected effective n at round 6 is below 12 (the cumulative counts scaled by the planned items, all certified items counted as matched, the reconcile's definition). **P(stop by success)** is the share of simulated courses that reach an effective n of 26 at some round up to 6 before the floor rule stops them. Matching is note 7's rule at the 10-point band within writer x document (`stage3_elicitation_matching.py`).\n")
    L.append("**Yield scenarios** (Beta posteriors, per valid item written; the valid share per round from round 1's 20 of 24): `round1_only` is Jeffreys on round 1's counts (certified 2 of 20, illegible 0 of 20); `e2_prior_plus_round1` adds round 1 to E2's rates for the Kimi pinned + Sonnet 5.5 pair (3 and 2 of 37 per rater-quiet candidate, scaled to per valid item by round 1's quiet share of 13 of 20, weight 37 items; the reconcile's flat 0.8 would double-count validity beside the valid share); `e2_prior_only` leaves round 1 out (one writer at E2's rates, round 1 sampled) to show how much of the fall from course A's figure is the lost second writer and how much is round 1's evidence. **Drift:** `none`, or the illegible rate falling linearly to half by round 4 (my reading of the reconcile's 'halving by round 4'). **Strata** of future items: `invented` (6 documents uniform, composition a clipped normal of spread 17.3 from plan section 8) or `empirical` (resampled from round 1's own 20 observed (document, composition) pairs). **Not modelled:** any change of yield with feedback (round 1 had none; round 2 is the feedback round), any association of class with document or composition, any change of the valid share.\n")
    L.append("## The replication check: this code on course A's own model\n")
    L.append("| | course A as reconciled (two writers, all certified items matched) | this code, same model |\n|---|---|---|")
    L.append(f"| P(n_eff of 26), rates hold | 0.93 | {f(rep['no_drift']['p_success'])} |")
    L.append(f"| P(n_eff of 26), illegible rate halves | 0.70 | {f(rep['halving']['p_success'])} |")
    L.append(f"| mean extra rounds beyond 3, rates hold / halve | 1.07 / 1.73 | {rep['no_drift']['mean_rounds_beyond_3']:.2f} / {rep['halving']['mean_rounds_beyond_3']:.2f} |")
    L.append(f"| median certified and illegible at the stop, rates hold / halve | 58 and 21 / 72 and 17 | {rep['no_drift']['median_certified_illegible_at_stop'][0]:.0f} and {rep['no_drift']['median_certified_illegible_at_stop'][1]:.0f} / {rep['halving']['median_certified_illegible_at_stop'][0]:.0f} and {rep['halving']['median_certified_illegible_at_stop'][1]:.0f} |\n")
    L.append("The rates-hold case reproduces the reconcile (0.93, 1.07, 58 and 21); the halving case is milder here (0.77 against 0.70) because the reconcile's drift schedule is not written down and this is my reading of it. A step to half at round 2 gives 0.67 and at round 4 gives 0.83, so the reconcile's schedule lies between the linear reading and the round-2 step. The new forecast uses the linear reading throughout.\n")
    L.append("## The forecast\n")
    for name, d in res["scenarios"].items():
        L.append(f"### {name}\n")
        L.append("| drift | statistic | P(stop by success) by round 6 | P(floor rule stops it) | P(reaches round 6 without either) | certified after round 3 | after round 6 | illegible after round 3 | after round 6 | effective n after round 6 |\n|---|---|---|---|---|---|---|---|---|---|")
        for drift in ("none", "halving"):
            for key, lab in (("all_matched", "every certified item matched (course A's)"), ("matched_invented", "matched, invented strata"), ("matched_empirical", "matched, round 1's strata")):
                m = d[drift][key]
                n6 = (m.get("matched_n_eff_after") or m["all_matched_n_eff_after"])["6"]
                L.append(f"| {drift} | {lab} | {f(m['p_success_by_round']['6'])} | {f(m['p_floor'])} | {f(m['p_limit'])} | {st(m['certified_after']['3'])} | {st(m['certified_after']['6'])} | {st(m['illegible_after']['3'])} | {st(m['illegible_after']['6'])} | {n6['mean']:.1f} |")
        L.append("")
    L.append("Counts are cumulative, round 1 included, mean [p10, p90], and are what the writer would hold if every round were run (the course may stop earlier). P(floor rule stops it) is the share of courses the floor rule ends after round 3, 4 or 5; the three shares per cell are in the JSON.\n")
    S, no = res["scenarios"], "none"
    cells = [S[n][no][k] for n in ("round1_only", "e2_prior_plus_round1") for k in ("matched_invented", "matched_empirical")]
    allm = [S[n][no]["all_matched"] for n in ("round1_only", "e2_prior_plus_round1")]
    pr = lambda xs: f"{f(min(xs))} to {f(max(xs))}"  # noqa: E731
    p3 = [c["p_floor_after_round"]["3"] for c in cells + allm]
    L.append("## Reading\n")
    L.append(f"- **The success stop is now unlikely.** Course A was chosen on 0.93 and 0.70. With one writer and round 1 folded in, and rates holding, the matched statistic reaches 26 by round 6 in {pr([c['p_success_by_round']['6'] for c in cells])} of simulated courses across the two yield scenarios and the two strata models (course A's own all-matched statistic: {pr([c['p_success_by_round']['6'] for c in allm])}); with the illegible rate falling to half it is {pr([S[n]['halving'][k]['p_success_by_round']['6'] for n in ('round1_only', 'e2_prior_plus_round1') for k in ('matched_invented', 'matched_empirical')])}.")
    L.append(f"- **The floor rule governs.** It ends {pr([c['p_floor'] for c in cells])} of courses under no drift (matched statistic), and {pr(p3)} of all courses end by it right after round 3, because the illegible count is still small then; of the courses it does not end, most run to the sixth round without reaching 26 ({pr([c['p_limit'] for c in cells])} of all courses).")
    dec = [("course A as reconciled (two writers, losses 0.8, all certified items matched)", rep["no_drift"]["p_success"]),
           ("the same with the second writer removed (one writer, the Sonnet 5.5 pair's rates, losses 0.8)", res["one_writer_original_p_success"]),
           ("with round 1's validity and quiet shares (20 of 24 valid, 13 of 20 quiet: about 0.54 combined, against 0.8) in place of the flat 0.8 (`e2_prior_only`)", S["e2_prior_only"][no]["all_matched"]["p_success"]),
           ("with round 1's counts folded in (`e2_prior_plus_round1`)", S["e2_prior_plus_round1"][no]["all_matched"]["p_success"]),
           ("and matched at the 10-point band on round 1's strata", S["e2_prior_plus_round1"][no]["matched_empirical"]["p_success"])]
    L.append("- **Where the fall from 0.93 comes from** (P(stop by success), rates holding):\n")
    L.append("| step | P |\n|---|---|")
    for lab, v in dec:
        L.append(f"| {lab} | {f(v)} |")
    L.append("")
    cc = [S[n][no]["matched_empirical"] for n in ("round1_only", "e2_prior_plus_round1")]
    rng2 = lambda a, b: (f"{min(a, b):.0f}" if round(a) == round(b) else f"{min(a, b):.0f} to {max(a, b):.0f}")  # noqa: E731
    c3, c6 = (rng2(cc[0]["certified_after"][r]["mean"], cc[1]["certified_after"][r]["mean"]) for r in ("3", "6"))
    i3, i6 = (rng2(cc[0]["illegible_after"][r]["mean"], cc[1]["illegible_after"][r]["mean"]) for r in ("3", "6"))
    i6max = max(cc[0]["illegible_after"]["6"]["mean"], cc[1]["illegible_after"]["6"]["mean"])
    c6min = min(cc[0]["certified_after"]["6"]["mean"], cc[1]["certified_after"]["6"]["mean"])
    verdict = (f"the illegible mean stays below the floor of 12 even after round 6, so the floor of 12 + 12 is not expected to be reached and brief 24's target of 26 + 26 is out of reach on the illegible side" if i6max < 12
               else "the illegible mean reaches the floor of 12 by round 6 on at least one yield scenario")
    L.append(f"- **What the writer is expected to hold** (rates holding, every round run, round 1 included; the two yield scenarios): after round 3, {c3} certified and {i3} quiet-but-illegible; after round 6, {c6} certified and {i6} illegible (the p10 to p90 spread is in the table). The certified side {'reaches' if c6min >= 12 else 'does not reach'} the floor of 12 by round 6; {verdict}.")
    L.append("- **What would change it.** A second writer (Muse Wonder, once Aravind names its harness) joining at round 3 starts its own feedback course and is matched within writer; the forecast above does not include it. Feedback may raise the illegible yield, which is what round 2 measures (round 1 had none); nothing here is evidence that it will not. The forecast is re-run on round 2's counts before any round beyond the third.\n")
    L.append("## Reproduce\n")
    L.append("```\nwork/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_forecast.py --part3 work/stage3/elicitation/part3 --writer gpt61sol --round 1\n```\n")
    return "\n".join(L) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import hashlib
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "after":
        return main_after(argv[1:])
    ap = argparse.ArgumentParser(description="brief 30 note 9: the course forecast")
    ap.add_argument("--part3", required=True)
    ap.add_argument("--writer", required=True)
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--runs-all", type=int, default=40000)
    ap.add_argument("--runs-matched", type=int, default=4000)
    ns = ap.parse_args(argv)
    P = Path(ns.part3)
    res = forecast(load_round1(P, ns.writer, ns.round), ns.runs_all, ns.runs_matched)
    (P / "forecast-v0.json").write_text(canonical(res), encoding="utf-8")
    sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:8]
    (P / "forecast-v0.md").write_text(render_md(res, sha), encoding="utf-8")
    print(f"wrote forecast-v0.json and forecast-v0.md in {P}")
    return 0




# ── after round 3: observed strata, per-writer yields, the bar (brief 30 note 12 and its addendum) ─────────────────

CAP_ROUND = 96


def writer_posterior(rounds: Sequence[Mapping[str, Any]]) -> dict:
    """Jeffreys posteriors on a writer's cumulative observed counts: the certified and illegible rates per valid item, and the
    valid share per item written."""
    V = sum(int(r["valid"]) for r in rounds)
    W = sum(int(r["written"]) for r in rounds)
    C = sum(int(r["certified"]) for r in rounds)
    I = sum(int(r["illegible"]) for r in rounds)
    return {"p_c": [0.5 + C, 0.5 + V - C], "p_i": [0.5 + I, 0.5 + V - I], "v": [0.5 + V, 0.5 + W - V]}


def bar_reading(p: float, runs: int, bar: float = 0.5) -> str:
    """The reading against the bar: a value on the margin (its 95 percent Monte Carlo interval holds the bar) reads as below."""
    se = (max(p * (1 - p), 1e-12) / runs) ** 0.5
    return "at or above 0.5" if p - 1.96 * se > bar else "below 0.5"


def drift_after(r: int, done: int, kind: str) -> float:
    """The illegible-rate multiplier at future round r given `done` rounds observed: none, or halving linearly over the next three."""
    if kind == "none":
        return 1.0
    if kind == "halving":
        return 1.0 - 0.5 * min(1.0, (r - done) / 3.0)
    raise ValueError(f"unknown drift {kind!r}")


def _observed(observed: Mapping[str, Any]) -> tuple[dict, dict]:
    per = {}
    for w, d in observed["writers"].items():
        rs = d["rounds"]
        per[w] = {"written": sum(int(r["written"]) for r in rs), "valid": sum(int(r["valid"]) for r in rs),
                  "certified": sum(int(r["certified"]) for r in rs), "illegible": sum(int(r["illegible"]) for r in rs)}
    tot = {k: sum(v[k] for v in per.values()) for k in ("certified", "illegible", "written", "valid")}
    return per, tot


def _course_after(rng: np.random.Generator, runs: int, observed: Mapping[str, Any], per: Mapping[str, Mapping[str, int]], drift: str,
                  matched: bool, width: float, M: int, stop: float, floor: float) -> dict:
    done = int(observed["rounds_done"])
    fut = list(range(done + 1, M + 1))
    writers = list(observed["writers"])
    post = {w: writer_posterior(observed["writers"][w]["rounds"]) for w in writers}
    draws = {w: tuple(rng.beta(*post[w][k], runs) for k in ("p_c", "p_i", "v")) for w in writers}
    n_f = len(fut)
    Cw = {w: np.zeros((runs, n_f)) for w in writers}
    Iw = {w: np.zeros((runs, n_f)) for w in writers}
    for ri, r in enumerate(fut):
        for w in writers:
            pc, pi, v = draws[w]
            n_valid = rng.binomial(CAP_ROUND, v)
            c, i = round_counts(rng, n_valid, pc, pi * drift_after(r, done, drift))
            Cw[w][:, ri], Iw[w][:, ri] = c, i
    tot_c0 = sum(per[w]["certified"] for w in writers)
    tot_i0 = sum(per[w]["illegible"] for w in writers)
    C = tot_c0 + np.cumsum(sum(Cw[w] for w in writers), axis=1)
    I = tot_i0 + np.cumsum(sum(Iw[w] for w in writers), axis=1)
    out = {"C": C, "I": I, "Cw": Cw, "Iw": Iw, "all_n_eff": neff(C, I)}
    if matched:
        MN = np.zeros((runs, n_f))
        for run in range(runs):
            items = [dict(x, writer=w) for w in writers for x in observed["writers"][w]["items"]]
            for ri in range(n_f):
                for w in writers:
                    c, i = int(Cw[w][run, ri]), int(Iw[w][run, ri])
                    emp = [tuple(x) for x in observed["writers"][w]["valid_strata"]]
                    for doc, comp in _strata_draw(rng, c, "empirical", emp):
                        items.append({"writer": w, "document": doc, "composition": comp, "class": mt.CERTIFIED})
                    for doc, comp in _strata_draw(rng, i, "empirical", emp):
                        items.append({"writer": w, "document": doc, "composition": comp, "class": mt.ILLEGIBLE})
                MN[run, ri] = mt.match(items, width)["n_eff"]
        out["stat"] = MN
    else:
        out["stat"] = out["all_n_eff"]
    # the course on the statistic: success after each future round; the floor rule (optional) after future rounds before the last
    written_now = sum(per[w]["written"] for w in writers)
    written_plan = written_now + CAP_ROUND * len(writers) * n_f

    def course(with_floor: bool) -> tuple[np.ndarray, np.ndarray]:
        outcome = np.full(runs, "limit", dtype=object)
        stop_round = np.full(runs, M)
        alive = np.ones(runs, dtype=bool)
        for ri, r in enumerate(fut):
            win = alive & (out["stat"][:, ri] >= stop)
            outcome[win], stop_round[win] = "success", r
            alive &= ~win
            if with_floor and r < M:
                w_r = written_now + CAP_ROUND * len(writers) * (ri + 1)
                scale = written_plan / w_r
                fl = alive & (neff(C[:, ri] * scale, I[:, ri] * scale) < floor)
                outcome[fl], stop_round[fl] = "floor", r
                alive &= ~fl
        return outcome, stop_round
    out["with_floor"], out["without_floor"] = course(True), course(False)
    out["fut"] = fut
    return out


def _summ_after(res: Mapping[str, Any], runs: int, done: int, base_c: float, base_i: float) -> dict:
    fut = res["fut"]
    o, sr = res["with_floor"]
    o2, _ = res["without_floor"]
    by = {str(r): round(float(np.mean((o == "success") & (sr <= r))), 4) for r in fut}
    p6 = float(np.mean(o == "success"))
    row = {"p_success_by_round": by,
           "with_floor_rule": {"p_success": round(p6, 4), "p_floor": round(float(np.mean(o == "floor")), 4), "p_limit": round(float(np.mean(o == "limit")), 4),
                               "p_floor_after_round": {str(r): round(float(np.mean((o == "floor") & (sr == r))), 4) for r in fut[:-1]}},
           "without_floor_rule": {"p_success": round(float(np.mean(o2 == "success")), 4)},
           "certified_after": {str(done): {"mean": base_c, "p10": base_c, "p90": base_c}, **{str(r): _stats(res["C"][:, i]) for i, r in enumerate(fut)}},
           "illegible_after": {str(done): {"mean": base_i, "p10": base_i, "p90": base_i}, **{str(r): _stats(res["I"][:, i]) for i, r in enumerate(fut)}},
           "n_eff_after": {str(r): _stats(res["stat"][:, i]) for i, r in enumerate(fut)},
           "bar_reading": bar_reading(p6, runs)}
    return row


def forecast_after(observed: Mapping[str, Any], runs_all: int = 40000, runs_matched: int = 20000, seed: int = SEED,
                   width: float = mt.BAND_WIDTH, M: int = M_ROUNDS, stop: float = STOP_NEFF, floor: float = FLOOR_NEFF) -> dict:
    """The forecast of the remaining rounds after `rounds_done` observed rounds: each writer's own Jeffreys yields (per valid item,
    the valid share as observed), no drift or halving, rounds at the cap for every writer who wrote, the statistic matched on the
    observed strata (each writer's own valid items' (document, composition) resampled) beside course A's all-matched one, the floor
    rule on and off. A value on the margin of the bar of 0.5 reads as below."""
    per, tot = _observed(observed)
    done = int(observed["rounds_done"])
    written_plan = tot["written"] + CAP_ROUND * len(per) * (M - done)
    c_now, i_now = tot["certified"], tot["illegible"]
    proj = float(neff(np.array([c_now * written_plan / tot["written"]]), np.array([i_now * written_plan / tot["written"]]))[0])
    out: dict[str, Any] = {"version": VERSION, "seed": seed, "runs_all_matched": runs_all, "runs_matched": runs_matched, "width": width,
                           "rounds_done": done, "rounds": M, "stop_n_eff": stop, "floor_n_eff": floor, "cap_per_writer_round": CAP_ROUND,
                           "writers": {w: {"posterior": writer_posterior(observed["writers"][w]["rounds"]), "observed": per[w]} for w in per},
                           "observed_totals": tot, "floor_rule_now": {"fires": bool(proj < floor), "projected_n_eff": proj, "line": floor},
                           "scenarios": {}, "per_further_round": {}}
    for di, drift in enumerate(("none", "halving")):
        out["scenarios"][drift] = {}
        for si, (stat, matched, runs) in enumerate((("all_matched", False, runs_all), ("matched_observed", True, runs_matched))):
            rng = np.random.default_rng([seed, di, si])
            res = _course_after(rng, runs, observed, per, drift, matched, width, M, stop, floor)
            out["scenarios"][drift][stat] = _summ_after(res, runs, done, c_now, i_now)
            if drift == "none" and stat == "all_matched":     # per further round, the counts that do not depend on the matching
                fut = res["fut"]
                ca = {str(r): _stats(sum(res["Cw"][w][:, i] for w in per)) for i, r in enumerate(fut)}
                ia = {str(r): _stats(sum(res["Iw"][w][:, i] for w in per)) for i, r in enumerate(fut)}
                bw = {w: {"certified_added": {str(r): _stats(res["Cw"][w][:, i]) for i, r in enumerate(fut)},
                          "illegible_added": {str(r): _stats(res["Iw"][w][:, i]) for i, r in enumerate(fut)}} for w in per}
                out["per_further_round"] = {"certified_added": ca, "illegible_added": ia, "by_writer": bw}
    return out


def load_observed(part3: Path, writer_rounds: Mapping[str, Sequence[int]], rounds_done: int) -> dict:
    """The observed state for `forecast_after`: each writer's rounds (counts), items and valid strata, from the files its
    rounds wrote under part3/ (round-N-v0.json, round-N/<writer>/round-record.json, the certification raters' gate-i.json)."""
    out: dict[str, Any] = {"rounds_done": int(rounds_done), "writers": {}}
    for w, rounds in writer_rounds.items():
        rs, items, strata = [], [], []
        for n in rounds:
            d = load_round1(part3, w, n)
            rs.append({"round": n, "written": d["written"], "valid": d["valid"], "certified": d["certified"], "illegible": d["illegible"]})
            items += d["items"]
            strata += d["valid_strata"]
        out["writers"][w] = {"rounds": rs, "items": items, "valid_strata": strata}
    return out


def render_after_md(res: Mapping[str, Any], module_sha: str = "") -> str:
    """The post-round-3 record: the bar's reading as note 12's addendum names it, the cases beside it, the floor rule now, and
    the expected certified count per further round for Phase E."""
    f = lambda x: f"{x:.2f}"  # noqa: E731
    st = lambda d: f"{d['mean']:.1f} [{d['p10']:.0f}, {d['p90']:.0f}]"  # noqa: E731
    sc, done = res["scenarios"], res["rounds_done"]
    prim = sc["none"]["matched_observed"]
    L = [f"# Forecast after writer round {done}'s certification (brief 30 note 12 and its addendum)\n"]
    L.append(f"Written by the Part 3 session (Sonnet 5.5). $0, no model call, no item, no B3 file. Module `stage3_elicitation_forecast.py` {module_sha}, seed {res['seed']}, {res['runs_all_matched']} runs per all-matched cell and {res['runs_matched']} per matched cell. Counts and aggregates only.\n")
    L.append("## What is computed\n")
    L.append(f"The remaining rounds ({done + 1} to {res['rounds']}) at the cap of {res['cap_per_writer_round']} per writer, for the writers who wrote: " + "; ".join(f"`{w}` ({d['observed']['written']} written, {d['observed']['valid']} valid, {d['observed']['certified']} certified, {d['observed']['illegible']} illegible)" for w, d in res["writers"].items()) + ". **Yields** are Jeffreys posteriors on each writer's own observed counts (per valid item, the valid share as observed), no drift. **The statistic** is the matched effective n at the 10-point band within writer x document, on the observed strata (each writer's own valid items' (document, composition) pairs resampled for the future items), against 26. The cases beside it: the all-matched statistic (course A's), and the illegible rate falling linearly to half over the next three rounds (`halving`). **P(stop by success)** is the share of simulated courses reaching 26 at some remaining round, with the floor rule applied after rounds before the last (the course as governed); the same without the floor rule is printed beside. **A value on the margin of the bar (its 95 percent Monte Carlo interval holds 0.5) reads as below 0.5.**\n")
    L.append("## The reading for the bar\n")
    b = prim["with_floor_rule"]["p_success"]
    L.append(f"**P(stop by success within the remaining rounds), matched on the observed strata, no drift: {f(b)}; it reads: {prim['bar_reading']}.** The bar for opening rounds {done + 1} to {res['rounds']} is at least 0.5.\n")
    L.append("| case | statistic | P(stop by success), floor rule on | floor rule off | P(floor rule ends it) | reading |\n|---|---|---|---|---|---|")
    for drift in ("none", "halving"):
        for stat, lab in (("matched_observed", "matched, observed strata"), ("all_matched", "every certified item matched (course A's)")):
            m = sc[drift][stat]
            L.append(f"| {drift} | {lab} | {f(m['with_floor_rule']['p_success'])} | {f(m['without_floor_rule']['p_success'])} | {f(m['with_floor_rule']['p_floor'])} | {m['bar_reading']} |")
    fl = res["floor_rule_now"]
    L.append(f"\n**The floor rule now** (rules v0.2: stop if the projected effective n at round {res['rounds']} is below {fl['line']:.0f}; the cumulative counts scaled by the planned items, every certified item counted as matched): projected {fl['projected_n_eff']:.1f}, so it **{'fires' if fl['fires'] else 'does not fire'}**.\n")
    L.append("## Counts if every remaining round were run (mean [p10, p90], matched case, no drift)\n")
    L.append("| after round | certified | quiet-but-illegible | matched effective n |\n|---|---|---|---|")
    for r in [str(done)] + [k for k in prim["n_eff_after"]]:
        c, i = prim["certified_after"][r], prim["illegible_after"][r]
        n = prim["n_eff_after"].get(r)
        L.append(f"| {r} | {st(c)} | {st(i)} | {st(n) if n else 'as certified'} |")
    L.append("\n## Phase E: the expected certified count per further round\n")
    L.append("Certified items are what the paper needs first (roadmap v4; note 12 item 2). Added per round, all writers and by writer, mean [p10, p90], no drift:\n")
    pf = res["per_further_round"]
    writers = list(res["writers"])
    L.append("| round | all writers (certified) | " + " | ".join(f"`{w}` certified" for w in writers) + " | all writers (illegible) |\n|---|---|" + "---|" * len(writers) + "---|")
    for r in pf["certified_added"]:
        L.append(f"| {r} | {st(pf['certified_added'][r])} | " + " | ".join(st(pf['by_writer'][w]['certified_added'][r]) for w in writers) + f" | {st(pf['illegible_added'][r])} |")
    L.append("\n## Reproduce\n")
    L.append("```\nwork/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_forecast.py after --part3 work/stage3/elicitation/part3 --rounds-done 3 --writer gpt61sol:1,2,3 [--writer muse_wonder:3]\n```\n")
    return "\n".join(L) + "\n"


def main_after(argv: Sequence[str]) -> int:
    import argparse
    import hashlib
    ap = argparse.ArgumentParser(description="brief 30 note 12: the forecast after a certified round")
    ap.add_argument("--part3", required=True)
    ap.add_argument("--rounds-done", type=int, required=True)
    ap.add_argument("--writer", action="append", required=True, help="name:rounds, e.g. gpt61sol:1,2,3")
    ap.add_argument("--runs-all", type=int, default=40000)
    ap.add_argument("--runs-matched", type=int, default=20000)
    ns = ap.parse_args(argv)
    wr = {w.split(":")[0]: [int(x) for x in w.split(":")[1].split(",")] for w in ns.writer}
    P = Path(ns.part3)
    res = forecast_after(load_observed(P, wr, ns.rounds_done), ns.runs_all, ns.runs_matched)
    name = f"forecast-after-r{ns.rounds_done}-v0"
    (P / f"{name}.json").write_text(canonical(res), encoding="utf-8")
    (P / f"{name}.md").write_text(render_after_md(res, hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:8]), encoding="utf-8")
    print(f"wrote {name}.json and {name}.md in {P}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
