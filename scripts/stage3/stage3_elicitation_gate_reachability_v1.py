#!/usr/bin/env python3
"""Brief 30 Part 2: E0-5's tables under the pinned reader for real (gate-reachability v1), from E1's and E2's runs
(`stage3_elicitation_e1e2.py`) with briefs 23 and 25's existing readings, and decision 8's trigger.

Decision 8 is `work/stage3/elicitation/review/reconcile-e2-rule-2026-11-02.md` (cb9f626e), adopted in full by brief 30's
dated note 2. The trigger is computed on the pair Kimi K3 pinned (Wafer, MXFP4; E2's two new samples) + GPT-6 Sol
(mean rule; brief 25's two samples) over the 78 B3 candidates, gate (iii) read per reader on any of its own samples
(protocol section 4): it fires if certified is fewer than 5 of 78 or quiet-but-illegible fewer than 3 of 78 (the
rates 26/432 and 12/432: two writers, writer round 1 at the floor of 24, rounds 2 and 3 at the cap of 96); the cap-48
lines (fewer than 9, fewer than 4), each rate's Wilson 95 % interval and the same-sample and both-both readings are
printed beside and never trigger. Beside, without a trigger: the 37 GLM-written candidates under Kimi pinned + Sonnet
5.5 (every sample), the T1 items, and the orientation (E0-5's 11 / 10 / 5 under brief 25's readers). The nulls: the
pinned reader's whole-credit and part-credit counts on the 46 (a nonzero whole credit is named).

E0-5's gates, classes and loaders are imported from `stage3_elicitation_gate_reachability.py` (c7a95ec2, unchanged).
Kimi K3 pinned is the reader `kimi_pin`; `kimi` stays brief 23's or brief 25's reads (mixed providers), except that a
T1 item's second Kimi sample from E1 is pinned (E1 read brief 23's r1 through the pin). No item text, rubric, answer or
key is read into the report; ids are opaque.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_gate_reachability_v1.py report \\
        --json work/stage3/elicitation/gate-reachability-v1.json --md work/stage3/elicitation/gate-reachability-v1.md
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_elicitation_e1e2 as e12  # noqa: E402
import stage3_elicitation_gate_reachability as gr  # noqa: E402  (E0-5, unchanged)
import stage3_legibility as lg  # noqa: E402

VERSION = "elicitation-gate-reachability/v1"
RULE_FILE = "work/stage3/elicitation/review/reconcile-e2-rule-2026-11-02.md"
E1D, E2D = "work/stage3/elicitation/e1e2/e1", "work/stage3/elicitation/e1e2/e2"
PIN = "kimi_pin"
TARGET_CERTIFIED, TARGET_ILLEGIBLE = 26, 12      # brief 30 note 4: 26 in both arms is the target; the rule's lines use 26 and 12
WRITERS, FLOOR, ROUNDS = 2, 24, 3
CAP, CAP_BESIDE = 96, 48
N_CANDIDATES = 78
Z95 = 1.959963984540054
DISCLOSURE = ("The lines are point expectations per rater-quiet candidate (B3's 78 candidates are rater-quiet by selection), "
              "made optimistic by the new writers' validity and rater-quiet losses; counts this small carry wide intervals.")
SAME_SAMPLE_NOTE = ("E2 pairs the pinned reader's new sample s with Sol's brief 25 sample s; the index pairing is arbitrary "
                    "(protocol section 4: samples are independent calls), so the same-sample count is beside only.")


# ── decision 8's lines, trigger and intervals ────────────────────────────────────────────────────

def round_items(cap: int) -> int:
    """Candidates over three writer rounds: two writers, round 1 at the floor, rounds 2 and 3 at the cap."""
    return WRITERS * (FLOOR + (ROUNDS - 1) * cap)


def trigger(certified: int, illegible: int, n: int = N_CANDIDATES, cap: int = CAP) -> dict:
    """Fires when a measured rate times the three rounds' candidates falls below its target (exact: count * N < target * n)."""
    N = round_items(cap)
    fc, fi = certified * N < TARGET_CERTIFIED * n, illegible * N < TARGET_ILLEGIBLE * n
    return {"cap": cap, "items_three_rounds": N, "n": n, "certified": certified, "illegible": illegible,
            "certified_rate_line": TARGET_CERTIFIED / N, "illegible_rate_line": TARGET_ILLEGIBLE / N,
            "fire_if_certified_fewer_than": math.ceil(TARGET_CERTIFIED * n / N),
            "fire_if_illegible_fewer_than": math.ceil(TARGET_ILLEGIBLE * n / N),
            "expected_certified_over_three_rounds": certified / n * N, "expected_illegible_over_three_rounds": illegible / n * N,
            "fires_certified": fc, "fires_illegible": fi, "fires": fc or fi}


def wilson(k: int, n: int, z: float = Z95) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [0.0 if k == 0 else max(0.0, c - h), 1.0 if k == n else min(1.0, c + h)]


# ── merges into E0-5's item form ─────────────────────────────────────────────────────────────────

def merge_e1(items: Sequence[Mapping[str, Any]], e1: Mapping[str, Mapping[str, tuple]]) -> list[dict]:
    """Brief 23's T1 items with E1's r1 as each reader's second sample; an item that already has one is refused."""
    out = []
    for it in items:
        it = copy.deepcopy(dict(it))
        for fam, vals in e1.items():
            if it["id"] not in vals:
                continue
            r = it["readers"][fam]
            if r["D_whole"][1] is not None or r["D_part"][1] is not None:
                raise ValueError(f"E1 would overwrite a second sample ({fam})")
            r["D_whole"][1], r["D_part"][1] = vals[it["id"]]
        out.append(it)
    return out


def add_pinned(items: Sequence[Mapping[str, Any]], pinned: Mapping[str, Mapping[str, list]]) -> list[dict]:
    out = []
    for it in items:
        it = copy.deepcopy(dict(it))
        v = pinned.get(it["id"]) or {"D_whole": [None, None], "D_part": [None, None]}
        it["readers"][PIN] = {"D_whole": list(v["D_whole"]), "D_part": list(v["D_part"])}
        out.append(it)
    return out


def null_credit(nulls: Sequence[Mapping[str, Any]], reader: str) -> dict:
    """The reader's whole and part credit on the nulls (against their false targets), by item and by cell."""
    ev = wi = pi = cells = wc = pc = 0
    wids, pids = [], []
    for it in nulls:
        r = it["readers"][reader]
        dw, dp = r["D_whole"], r["D_part"]
        ev += all(x is not None for x in (*dw, *dp))
        if any(x is not None and x > 0 for x in dw):
            wi += 1
            wids.append(it["id"])
        if any(x is not None and x > 0 for x in dp):
            pi += 1
            pids.append(it["id"])
        for a, b in zip(dw, dp):
            if a is None or b is None:
                continue
            cells += 1
            wc += a > 0
            pc += b > 0
    return {"items": len(nulls), "evaluable_items": ev, "whole_credit_items": wi, "part_credit_items": pi,
            "whole_credit_ids": sorted(wids), "part_credit_ids": sorted(pids), "cells": cells, "whole_credit_cells": wc,
            "part_credit_cells": pc}


def cell_rates(items: Sequence[Mapping[str, Any]], reader: str, samples: Sequence[int] | None = None) -> dict:
    n = a = b = 0
    for it in items:
        r = it["readers"].get(reader)
        if r is None:
            continue
        for s in (range(len(r["D_whole"])) if samples is None else samples):
            if r["D_whole"][s] is None or r["D_part"][s] is None:
                continue
            n += 1
            a += r["D_part"][s] > 0
            b += r["D_whole"][s] > 0
    return {"cells": n, "D_part_pos": a, "D_whole_pos": b, "share_D_part_pos": a / n if n else None,
            "share_D_whole_pos": b / n if n else None}


# ── loaders: E1 and E2's caches ──────────────────────────────────────────────────────────────────

def _rows(root: Path) -> tuple[list[dict], list[dict]]:
    r23 = json.loads((root / e12.B23 / "items-v0.json").read_text())["items"]
    r25 = json.loads((root / e12.B25 / "items-v0.json").read_text())["items"]
    return r23, r25


def _models(root: Path) -> dict[str, str]:
    ch = json.loads((root / e12.B23 / "routes-v0.json").read_text())["chosen"]
    return {f: ch[f]["model"] for f in e12.E1_READERS}


def cache_files(root: Path) -> dict[str, Path]:
    m = _models(root)
    out = {f"e1:{f}": lg.reader_cache(root / E1D, f, m[f]) for f in e12.E1_READERS}
    out["e1:scorer"] = lg.scorer_cache(root / E1D)
    out["e2:kimi"] = lg.reader_cache(root / E2D, "kimi", m["kimi"])
    out["e2:scorer"] = lg.scorer_cache(root / E2D)
    return out


def e1_values(root: Path) -> dict[str, dict[str, tuple]]:
    r23, _ = _rows(root)
    rows = e12.select_e1(r23)
    cf = cache_files(root)
    rec = e12.Recs({f: lg.read_jsonl(cf[f"e1:{f}"]) for f in e12.E1_READERS}, lg.read_jsonl(cf["e1:scorer"]))
    return {f: {r["item_id"]: e12.sample_values(rec, f, e12.E1_SAMPLE, r) for r in rows} for f in e12.E1_READERS}


def e2_values(root: Path) -> tuple[dict[str, dict[str, list]], dict]:
    r23, r25 = _rows(root)
    rows = e12.select_e2(r23, r25)
    cf = cache_files(root)
    rec = e12.Recs({"kimi": lg.read_jsonl(cf["e2:kimi"])}, lg.read_jsonl(cf["e2:scorer"]))
    vals, status = {}, Counter()
    for r in rows:
        v = [e12.sample_values(rec, "kimi", s, r) for s in e12.E2_SAMPLES]
        vals[r["item_id"]] = {"D_whole": [x[0] for x in v], "D_part": [x[1] for x in v]}
        for s in e12.E2_SAMPLES:
            for c in lg.CONDS:
                st = rec.reader_status("kimi", s, r, c)
                if st != "answered":
                    status[f"{r['source']}:{r['regime']}:{c}:{st}"] += 1
    return vals, dict(sorted(status.items()))


def orientation(root: Path) -> dict:
    """E0-5's reading under brief 25's readers (Kimi K3 mixed providers + Sol mean), recomputed by E0-5's code."""
    cand = [i for i in gr.load_b25(root) if i["set"] == "candidate"]
    return gr.tally(cand, "kimi", "sol", "sol_mean", 2)


def usage_windows(checks: Sequence[tuple[str, Mapping[str, Any]]], openrouter_usd: Mapping[str, float]) -> list[dict]:
    """Key 2's usage between consecutive limit checks (in time order) against the OpenRouter spend in the run records of
    the run whose check opened the window (each run's spend counted in its first window only)."""
    out, seen = [], set()
    for (run, a), (_, b) in zip(checks, checks[1:]):
        rec = 0.0 if run in seen else float(openrouter_usd.get(run, 0.0))
        seen.add(run)
        d = float(b["key"]["usage"]) - float(a["key"]["usage"])
        out.append({"run": run, "from": a["checked_at"], "to": b["checked_at"], "key_usage_delta_usd": round(d, 4),
                    "run_openrouter_records_usd": round(rec, 4), "not_in_run_records_usd": round(d - rec, 4)})
    return out


def _spend(paths: Mapping[str, Path]) -> dict:
    out = {k: round(sum(float(x.get("cost_usd") or 0) for x in lg.read_jsonl(p)), 4) for k, p in paths.items()}
    for e in ("e1", "e2"):
        out[f"{e}:total"] = round(sum(v for k, v in out.items() if k.startswith(f"{e}:") and not k.endswith("total")), 4)
    out["total"] = round(out["e1:total"] + out["e2:total"], 4)
    return out


# ── the report ───────────────────────────────────────────────────────────────────────────────────

def _slim(t: dict) -> dict:
    return {k: v for k, v in t.items() if k != "ids"}


def build(root: Path) -> dict:
    b25, b23 = gr.load_b25(root), gr.load_b23(root)
    e1v = e1_values(root)
    e2v, e2_status = e2_values(root)
    cand = add_pinned([i for i in b25 if i["set"] == "candidate"], e2v)
    nulls = add_pinned([i for i in b25 if i["set"] in ("control", "sham")], e2v)
    glm = [i for i in cand if i["writer"] == "glm53"]
    t1_e1 = merge_e1([i for i in b23 if i["set"] in gr.T1_SETS], e1v)
    t1 = add_pinned(t1_e1, e2v)
    T = gr.tally

    e1 = {"t1_items_brief23_readers": {"kimi+sol (sol_mean)": T(t1_e1, "kimi", "sol", "sol_mean", 2),
                                       "kimi+sonnet55 (every)": T(t1_e1, "kimi", "sonnet55", "every", 2),
                                       "by_regime (kimi+sol, sol_mean)": {s: _slim(T([i for i in t1_e1 if i["set"] == s], "kimi", "sol", "sol_mean", 2))
                                                                          for s in gr.T1_SETS}},
          "two_samples_by_reader": {f: sum(1 for i in t1_e1 if gr.has_samples(i, f, 2)) for f in e12.E1_READERS},
          "items": len(t1_e1), "items_read_by_e1": len(e1v["kimi"]),
          "not_evaluable_at_r1": {f: sum(1 for v in e1v[f].values() if v[0] is None) for f in e12.E1_READERS},
          "note": "Kimi K3's second sample on the 38 items read once is E1's, through the pin; on the 10 retest items it is "
                  "brief 23's r1 (mixed providers). Sol and Sonnet 5.5 are brief 23's routes (Bedrock)."}

    sets = {
        "b3_candidates": {"kimi_pin+sol (sol_mean)": T(cand, PIN, "sol", "sol_mean", 2),
                          "kimi_pin+sol (every, beside)": _slim(T(cand, PIN, "sol", "every", 2)),
                          "by_writer (kimi_pin+sol, sol_mean)": {w: _slim(T([i for i in cand if i["writer"] == w], PIN, "sol", "sol_mean", 2))
                                                                 for w in sorted({i["writer"] for i in cand})}},
        "b3_candidates_glm_written": {"kimi_pin+sonnet55 (every)": T(glm, PIN, "sonnet55", "every", 2),
                                      "kimi_pin+sol (sol_mean), same items": _slim(T(glm, PIN, "sol", "sol_mean", 2))},
        "nulls_46": {"kimi_pin+sol (sol_mean)": T(nulls, PIN, "sol", "sol_mean", 2),
                     "kimi_pin+sol (every)": _slim(T(nulls, PIN, "sol", "every", 2)),
                     "kimi_pin+sonnet55 (every), the 10 controls read by Sonnet 5.5":
                         _slim(T([i for i in nulls if "sonnet55" in i["readers"]], PIN, "sonnet55", "every", 2)),
                     "by_set (kimi_pin+sol, sol_mean)": {s: _slim(T([i for i in nulls if i["set"] == s], PIN, "sol", "sol_mean", 2))
                                                          for s in ("control", "sham")}},
        "t1_items": {"kimi_pin+sol (sol_mean)": T(t1, PIN, "sol", "sol_mean", 2),
                     "kimi_pin+sonnet55 (every)": T(t1, PIN, "sonnet55", "every", 2),
                     "by_regime (kimi_pin+sol, sol_mean)": {s: _slim(T([i for i in t1 if i["set"] == s], PIN, "sol", "sol_mean", 2))
                                                            for s in gr.T1_SETS}},
    }

    def alone(items, reader, rule):
        return sum(1 for i in items if gr.has_samples(i, reader, 2) and gr.RULES[rule](i["readers"][reader]["D_part"][:2]))
    gate_ii = {"b3_candidates_78": {"kimi_pin every": alone(cand, PIN, "every"), "kimi (brief 25) every, beside": alone(cand, "kimi", "every"),
                                    "sol sol_mean": alone(cand, "sol", "sol_mean"),
                                    "kimi_pin every + sol sol_mean": sets["b3_candidates"]["kimi_pin+sol (sol_mean)"]["gate_ii_pass"],
                                    "kimi_pin every + sol every": sets["b3_candidates"]["kimi_pin+sol (every, beside)"]["gate_ii_pass"]},
               "b3_candidates_glm_37": {"kimi_pin every": alone(glm, PIN, "every"), "sonnet55 every": alone(glm, "sonnet55", "every"),
                                        "kimi_pin every + sonnet55 every": sets["b3_candidates_glm_written"]["kimi_pin+sonnet55 (every)"]["gate_ii_pass"],
                                        "kimi_pin every + sol sol_mean": sets["b3_candidates_glm_written"]["kimi_pin+sol (sol_mean), same items"]["gate_ii_pass"]}}

    main = sets["b3_candidates"]["kimi_pin+sol (sol_mean)"]
    cert, ill = main["classes"]["certified"], main["classes"]["quiet_but_illegible"]
    n = main["n"]
    trig = {"rule_file": RULE_FILE, "pair": "Kimi K3 pinned (E2) + Sol (mean; brief 25's samples)",
            "reading": "gate (iii) per reader on any of its own samples (protocol section 4)",
            "cap_96": trigger(cert, ill, n, CAP), "cap_48_beside": trigger(cert, ill, n, CAP_BESIDE),
            "beside_readings": {"same_sample": main["certified_by_reading"]["same_sample"], "both_both": main["certified_by_reading"]["both_both"],
                                "note": SAME_SAMPLE_NOTE},
            "wilson95": {"certified": wilson(cert, n), "quiet_but_illegible": wilson(ill, n), "mixed": wilson(main["classes"]["mixed"], n)},
            "disclosure": DISCLOSURE}
    trig["fires"] = trig["cap_96"]["fires"]
    o = orientation(root)
    rates = {"denominator": "per rater-quiet candidate: the 78 B3 candidates (rater-quiet by selection) under the trigger's pair",
             "p_c": cert / n, "p_i": ill / n, "p_c_wilson95": wilson(cert, n), "p_i_wilson95": wilson(ill, n),
             "orientation_beside": {"p_c": o["classes"]["certified"] / o["n"], "p_i": o["classes"]["quiet_but_illegible"] / o["n"],
                                    "pair": "Kimi K3 (mixed providers, brief 25) + Sol (mean)"},
             "glm37_kimi_pin+sonnet55_beside": {"p_c": sets["b3_candidates_glm_written"]["kimi_pin+sonnet55 (every)"]["classes"]["certified"] / len(glm),
                                                "p_i": sets["b3_candidates_glm_written"]["kimi_pin+sonnet55 (every)"]["classes"]["quiet_but_illegible"] / len(glm)}}

    b25_items = [i for i in b25 if i["set"] == "candidate"]
    cells = {"b3_candidates": {"kimi_pin (E2)": cell_rates(cand, PIN), "kimi (brief 25, mixed), beside": cell_rates(b25_items, "kimi")},
             "nulls_46": {"kimi_pin (E2)": cell_rates(nulls, PIN)},
             "t1_items": {"kimi_pin (E2)": cell_rates(t1, PIN), "kimi (brief 23 r0, mixed), beside": cell_rates(t1, "kimi", (0,))}}

    cf = cache_files(root)
    served = {"e1:kimi": e12.served_summary(lg.read_jsonl(cf["e1:kimi"])), "e2:kimi": e12.served_summary(lg.read_jsonl(cf["e2:kimi"])),
              "e1:sol": {"route": "converse", "model": _models(root)["sol"], "provider_pin": None},
              "e1:sonnet55": {"route": "bedrock", "model": _models(root)["sonnet55"], "provider_pin": None},
              "scorer": {"route": "bedrock", "model": lg.SCORER["bedrock"], "provider_pin": None}}
    runs = {e: json.loads((root / d / "run-summary.json").read_text()) for e, d in (("e1", E1D), ("e2", E2D))}
    pause_file = root / E2D / "run-summary-00-pause.json"
    pause = json.loads(pause_file.read_text()) if pause_file.exists() else None
    runner_at_plan = {e: json.loads((root / d / "plan-v0.json").read_text())["script_sha256"] for e, d in (("e1", E1D), ("e2", E2D))}
    limits = {e: [json.loads(p.read_text()) for p in sorted((root / d).glob("limits-*.json"))] for e, d in (("e1", E1D), ("e2", E2D))}

    files = [gr.STRATUM, gr.PER_PART, gr.T1_JOIN, f"{e12.B23}/items-v0.json", f"{e12.B23}/routes-v0.json", f"{e12.B25}/items-v0.json", RULE_FILE,
             *[str(p.relative_to(root)) for p in cf.values()],
             *[f"{d}/{f}" for d in (E1D, E2D) for f in ("plan-v0.json", "run-summary.json", "models-v0.json", "kimi-endpoints.json")],
             f"{E2D}/run-summary-00-pause.json", *[str(p.relative_to(root)) for d in (E1D, E2D) for p in sorted((root / d).glob("limits-*.json"))]]
    return {"version": VERSION, "script_sha256": gr.sha256(Path(__file__)), "e0_5_script_sha256": gr.sha256(HERE / "stage3_elicitation_gate_reachability.py"),
            "runner_script_sha256": gr.sha256(HERE / "stage3_elicitation_e1e2.py"),
            "inputs_sha256": {p: gr.sha256(root / p) for p in files if (root / p).exists()},
            "trigger": trig, "measured_rates": rates, "orientation_beside": _slim(o),
            "e2": {"sets": sets, "gate_ii_pass_by_rule": gate_ii, "nulls_credit": {"all_46": null_credit(nulls, PIN),
                   **{s: null_credit([i for i in nulls if i["set"] == s], PIN) for s in ("control", "sham")}},
                   "cell_rates": cells, "kimi_pin_not_answered": e2_status},
            "e1": e1, "served": served, "spend_usd": _spend(cf),
            "runs": {e: {k: r.get(k) for k in ("stop_usd", "past_pause", "e1_spent_usd", "headroom_usd", "limits_file", "dollars", "outcomes",
                                               "stopped", "started_at", "finished_at")} | {"read": r["run"]["read"], "score": {k: v for k, v in r["run"]["score"].items() if k != "abort_reason"}}
                     for e, r in runs.items()},
            "e2_pause": None if pause is None else {"stop_usd": pause["stop_usd"], "dollars": pause["dollars"], "score": {k: v for k, v in pause["run"]["score"].items() if k != "abort_reason"},
                                                    "read": pause["run"]["read"], "finished_at": pause["finished_at"]},
            "runner_sha256_at_plan": runner_at_plan, "key2_limits": limits,
            "key2_usage_windows": usage_windows(sorted(((e, x) for e, xs in limits.items() for x in xs), key=lambda t: t[1]["checked_at"]),
                                                {e: _spend(cf)[f"{e}:kimi"] for e in ("e1", "e2")})}


# ── markdown ─────────────────────────────────────────────────────────────────────────────────────

def _r(t: dict, name: str, label: str) -> str:
    return gr._row(name, label, t)


def _ci(x):
    return "n/a" if x is None else f"[{x[0]:.3f}, {x[1]:.3f}]"


def render_md(R: dict) -> str:
    G, S, Tr, M, O = R["e2"], R["e2"]["sets"], R["trigger"], R["measured_rates"], R["orientation_beside"]
    t96, t48 = Tr["cap_96"], Tr["cap_48_beside"]
    main = S["b3_candidates"]["kimi_pin+sol (sol_mean)"]
    nc = G["nulls_credit"]["all_46"]
    sp = R["spend_usd"]
    e2s, e1s = R["served"]["e2:kimi"], R["served"]["e1:kimi"]
    fired = Tr["fires"]
    L = ["# Gate reachability under the pinned reader (brief 30 Part 2: E1 and E2; blue; counts, aggregates and hashes only)", "",
         f"Script `work/checks/stage3_elicitation_gate_reachability_v1.py` {R['script_sha256'][:8]}, importing E0-5's "
         f"`stage3_elicitation_gate_reachability.py` {R['e0_5_script_sha256'][:8]} unchanged; the runs by "
         f"`stage3_elicitation_e1e2.py` {R['runner_script_sha256'][:8]}. Decision 8 is `{RULE_FILE}` "
         f"({R['inputs_sha256'].get(RULE_FILE, '')[:8]}). Item ids are in the JSON; no item text, rubric or answer was read.", "",
         "## Decision 8's trigger", "",
         f"- **The trigger {'FIRES' if fired else 'does not fire'}.** On the pair {Tr['pair']}, {Tr['reading']}: **{t96['certified']} of "
         f"{t96['n']} certified** (fires if fewer than {t96['fire_if_certified_fewer_than']}) and **{t96['illegible']} of {t96['n']} "
         f"quiet-but-illegible** (fires if fewer than {t96['fire_if_illegible_fewer_than']}), at cap {t96['cap']} ({t96['items_three_rounds']} "
         f"candidates over three writer rounds: expected {t96['expected_certified_over_three_rounds']:.1f} certified against 26 and "
         f"{t96['expected_illegible_over_three_rounds']:.1f} quiet-but-illegible against 12). Certified fires: {t96['fires_certified']}; "
         f"illegible fires: {t96['fires_illegible']}.",
         f"- Beside, never a trigger: at cap 48 ({t48['items_three_rounds']} candidates) the lines are fewer than "
         f"{t48['fire_if_certified_fewer_than']} and fewer than {t48['fire_if_illegible_fewer_than']} (the rules file's 0.108 and 0.050): "
         f"certified {'below' if t48['fires_certified'] else 'at or above'}, illegible {'below' if t48['fires_illegible'] else 'at or above'}. "
         f"Same-sample reading {Tr['beside_readings']['same_sample']}, both readers on both samples {Tr['beside_readings']['both_both']}. "
         + Tr["beside_readings"]["note"],
         f"- Wilson 95 % intervals: certified {main['classes']['certified']}/{main['n']} {_ci(Tr['wilson95']['certified'])}; "
         f"quiet-but-illegible {main['classes']['quiet_but_illegible']}/{main['n']} {_ci(Tr['wilson95']['quiet_but_illegible'])}; "
         f"mixed {main['classes']['mixed']}/{main['n']} {_ci(Tr['wilson95']['mixed'])}. {Tr['disclosure']}",
         f"- Orientation beside (E0-5, brief 25's readers, Kimi K3 on mixed providers): certified {O['classes']['certified']}, same sample "
         f"{O['certified_by_reading']['same_sample']}, both-both {O['certified_by_reading']['both_both']}, quiet-but-illegible "
         f"{O['classes']['quiet_but_illegible']}, of {O['n']}.",
         ("- **If it fires** (rule file): Part 2 stops and the choice goes to Aravind by dated note before writer round 1." if fired else
          f"- **It does not fire:** the pin stays, and the raising rule's orientation rates are replaced by E2's measured rates "
          f"(Part 3's dated note): p_c = {M['p_c']:.4f} {_ci(M['p_c_wilson95'])} and p_i = {M['p_i']:.4f} {_ci(M['p_i_wilson95'])}, "
          f"{M['denominator']}."),
         "", "## The nulls under the pinned reader", "",
         f"- 46 nulls (22 controls, 24 same-shape comparison items, against their false targets), Kimi K3 pinned at two samples: "
         f"{nc['evaluable_items']} evaluable; **whole credit on {nc['whole_credit_items']} items** ({nc['whole_credit_cells']} of "
         f"{nc['cells']} cells), part credit on {nc['part_credit_items']} items ({nc['part_credit_cells']} cells)."
         + (f" **A nonzero whole credit for a null, named:** ids {', '.join(i[:12] for i in nc['whole_credit_ids'])} (full ids in the JSON)."
            if nc["whole_credit_items"] else ""),
         f"- Class under Kimi pinned + Sol (mean): certified {S['nulls_46']['kimi_pin+sol (sol_mean)']['classes']['certified']} of 46 "
         "(holds by construction, since Sol's brief 25 samples credit no null's whole; not the finding).", "",
         "## The gate at two samples under the pin (E2)", "", gr.HEAD,
         _r(main, "B3 candidates", "Kimi K3 pinned + Sol (mean): the trigger"),
         _r(S["b3_candidates"]["kimi_pin+sol (every, beside)"], "B3 candidates", "Kimi K3 pinned + Sol (every, beside)")]
    for w, t in S["b3_candidates"]["by_writer (kimi_pin+sol, sol_mean)"].items():
        L.append(_r(t, f"B3 candidates, {w}-written", "Kimi K3 pinned + Sol (mean)"))
    L += [_r(S["b3_candidates_glm_written"]["kimi_pin+sonnet55 (every)"], "B3 candidates, GLM-written", "Kimi K3 pinned + Sonnet 5.5 (every), beside"),
          _r(S["b3_candidates_glm_written"]["kimi_pin+sol (sol_mean), same items"], "B3 candidates, GLM-written", "Kimi K3 pinned + Sol (mean)"),
          _r(S["nulls_46"]["kimi_pin+sol (sol_mean)"], "nulls (46)", "Kimi K3 pinned + Sol (mean)"),
          _r(S["nulls_46"]["kimi_pin+sol (every)"], "nulls (46)", "Kimi K3 pinned + Sol (every)"),
          _r(S["nulls_46"]["kimi_pin+sonnet55 (every), the 10 controls read by Sonnet 5.5"], "nulls, 10 controls read by Sonnet 5.5",
             "Kimi K3 pinned + Sonnet 5.5 (every)")]
    for s, t in S["nulls_46"]["by_set (kimi_pin+sol, sol_mean)"].items():
        L.append(_r(t, f"nulls, {s}", "Kimi K3 pinned + Sol (mean)"))
    L += [_r(S["t1_items"]["kimi_pin+sol (sol_mean)"], "T1 items (48), beside", "Kimi K3 pinned + Sol (mean)"),
          _r(S["t1_items"]["kimi_pin+sonnet55 (every)"], "T1 items (48), beside", "Kimi K3 pinned + Sonnet 5.5 (every)")]
    for s, t in S["t1_items"]["by_regime (kimi_pin+sol, sol_mean)"].items():
        L.append(_r(t, f"T1 {s[3:].replace('_', ' ')}", "Kimi K3 pinned + Sol (mean)"))
    L += ["", f"Gate (i) is E0-5's single session (brief 25's `rater_top_line` for the candidates, 07k's two-pass line mean for the T1 items, "
          "not applied to nulls). The second readers' samples are brief 25's for its items and, for the T1 items, brief 23's r0 with "
          "brief 23's r1 (10 retest items) or E1's r1 (38 items).", "",
          "## Gate (ii) by rule under the pin", "", "| items | rule | pass |", "|---|---|---|"]
    for name, d in G["gate_ii_pass_by_rule"].items():
        for rule, k in d.items():
            L.append(f"| {name.replace('_', ' ')} | {rule} | {k} |")
    L += ["", "Kimi K3's cell rates (a cell is one item and sample with all four conditions scored):", "",
          "| items | reader | cells | D_part > 0 | D_whole > 0 |", "|---|---|---|---|---|"]
    for name, d in G["cell_rates"].items():
        for rd, c in d.items():
            L.append(f"| {name.replace('_', ' ')} | {rd} | {c['cells']} | {gr._pct(c['share_D_part_pos'])} | {gr._pct(c['share_D_whole_pos'])} |")
    na = G["kimi_pin_not_answered"]
    L += ["", f"Pinned reads not answered (by source, regime, condition and status): {json.dumps(na) if na else 'none'}.", "",
          "## E1: the T1 items at two samples under brief 23's three readers", "", gr.HEAD]
    E1 = R["e1"]["t1_items_brief23_readers"]
    L += [_r(E1["kimi+sol (sol_mean)"], "T1 items (48)", "Kimi K3 + Sol (mean)"), _r(E1["kimi+sonnet55 (every)"], "T1 items (48)", "Kimi K3 + Sonnet 5.5 (every)")]
    for s, t in E1["by_regime (kimi+sol, sol_mean)"].items():
        L.append(_r(t, f"T1 {s[3:].replace('_', ' ')}", "Kimi K3 + Sol (mean)"))
    L += ["", f"Items with two samples per reader: {json.dumps(R['e1']['two_samples_by_reader'])} of {R['e1']['items']}; E1 read "
          f"{R['e1']['items_read_by_e1']} items; not evaluable at E1's r1: {json.dumps(R['e1']['not_evaluable_at_r1'])}. {R['e1']['note']}", "",
          "## Served provider and precision", "",
          f"- E2, Kimi K3: {e2s['final_records']} final records, by provider|precision|pin {json.dumps(e2s['final_by_provider'])}; attempts served "
          f"off the pin {e2s['attempts_off_pin']} (each recorded errored and re-issued); final records off the pin {e2s['final_off_pin']}.",
          f"- E1, Kimi K3: {e1s['final_records']} final records, {json.dumps(e1s['final_by_provider'])}; attempts off the pin "
          f"{e1s['attempts_off_pin']}; final off the pin {e1s['final_off_pin']}.",
          f"- E1, Sol: {R['served']['e1:sol']['route']} `{R['served']['e1:sol']['model']}`; Sonnet 5.5: {R['served']['e1:sonnet55']['route']} "
          f"`{R['served']['e1:sonnet55']['model']}`; scorer: `{R['served']['scorer']['model']}` (Bedrock; no provider choice). Every "
          "Kimi record's provider and precision is in the JSON (`served.*.per_record`, by label).", "",
          "## Spend and key 2", ""]
    for e in ("e1", "e2"):
        ru = R["runs"][e]
        L.append(f"- {e.upper()}: ${sp[f'{e}:total']:.2f} (" + ", ".join(f"{k.split(':')[1]} ${v:.2f}" for k, v in sp.items()
                                                                if k.startswith(f"{e}:") and not k.endswith("total"))
                 + f"); stop ${ru['stop_usd']:.2f}; stopped {ru['stopped']}; outcomes {json.dumps(ru['outcomes'])}.")
    L.append(f"- Both runs: ${sp['total']:.2f} against the approved $17.52 (pause $23.36, hard stop $35.04).")
    if R.get("e2_pause"):
        p = R["e2_pause"]
        L.append(f"- E2 stopped at the pause ({p['finished_at']}): stop ${p['stop_usd']:.2f}, spent ${p['dollars']['total']:.2f}, every read done, "
                 f"scorer {p['score'].get('done')} of {p['score'].get('of')}; it resumed from cache past the pause on Aravind's word in this "
                 "session (`--past-pause`: E2's stop at its $28.60 cap, under the hard stop over both runs).")
    rs = R["runner_sha256_at_plan"]
    L.append(f"- Runner hash at each plan: E1 {rs['e1'][:8]}, E2 {rs['e2'][:8]}, now {R['runner_script_sha256'][:8]} (E1's run ended at its summary "
             "print, after every call and the summary file; the change since adds the print-safe summary and nothing else).")
    for e, ls in R["key2_limits"].items():
        for x in ls:
            L.append(f"- Key 2 before {e.upper()} ({x['checked_at']}): limit remaining ${x['key'].get('limit_remaining', 0):.2f}, "
                     f"account remaining ${(x['account'] or {}).get('remaining', float('nan')):.2f}, headroom ${x['headroom_usd']:.2f}.")
    for w in R["key2_usage_windows"]:
        L.append(f"- Key 2's usage from {w['from']} to {w['to']} (the window {w['run'].upper()} opened): ${w['key_usage_delta_usd']:.2f}, against "
                 f"${w['run_openrouter_records_usd']:.2f} of OpenRouter calls in {w['run'].upper()}'s records; ${w['not_in_run_records_usd']:.2f} "
                 "is not in this run's records (Sol, Sonnet 5.5 and the scorer are Bedrock, not key 2).")
    L += ["", "## Inputs", ""] + [f"- `{p}` {h[:8]}" for p, h in R["inputs_sha256"].items()] + [""]
    return "\n".join(L) + "\n"


def cmd_report(a: argparse.Namespace) -> int:
    R = build(Path(a.root))
    Path(a.json).write_text(json.dumps(R, indent=1) + "\n")
    Path(a.md).write_text(render_md(R))
    t = R["trigger"]["cap_96"]
    print(f"trigger fires {R['trigger']['fires']}: certified {t['certified']} of {t['n']} (fires under {t['fire_if_certified_fewer_than']}), "
          f"quiet-but-illegible {t['illegible']} of {t['n']} (fires under {t['fire_if_illegible_fewer_than']}); "
          f"same sample {R['trigger']['beside_readings']['same_sample']}, both-both {R['trigger']['beside_readings']['both_both']}; "
          f"null whole credit {R['e2']['nulls_credit']['all_46']['whole_credit_items']}; spend ${R['spend_usd']['total']:.2f}; wrote {a.json} and {a.md}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("report")
    p.add_argument("--root", default=str(HERE.parent.parent))
    p.add_argument("--json", required=True)
    p.add_argument("--md", required=True)
    a = ap.parse_args(argv)
    return {"report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
