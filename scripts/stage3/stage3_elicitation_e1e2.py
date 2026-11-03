#!/usr/bin/env python3
"""Brief 30 Part 2 (brief 29 notes 9, 11 and 12): E1 and E2, the readings E0-5 named and priced but did not run.

E1: brief 23's r1 on the 38 T1 items read once (the T1 items outside brief 23's retest subset), under brief 23's three
    readers (Kimi K3 through E0-7's pin, GPT-6 Sol, Sonnet 5.5), so that every T1 item has two samples per reader.
E2: Kimi K3 pinned to Wafer at MXFP4, two new samples per item and condition, on brief 25's 124 items (the 78 B3
    candidates, the 22 controls and the 24 same-shape comparison items) and the 48 T1 items; the second readers'
    existing two samples stand (brief 25's for its items; brief 23's r0 with brief 23's r1 or E1's for the T1 items).

Everything a reader sees is brief 23's or brief 25's rendering unchanged: the rows, rubrics and triples are the
committed files, and the run refuses unless the rendered packets hash to each brief's `packets_sha256` and the
instrument's prompts and configuration hash to brief 23's. The scorer (Sonnet 5, two passes) scores each answer
against its L target only (a test item's rubric; a null item's false target), as E0-5 priced it. Kimi K3 runs through
`judge_openrouter_pin.PinnedOpenRouterJudge` on key 2 (brief 30 decision 9): a reply served off the pin is recorded as
errored and re-issued, up to REISSUE_ROUNDS times. Spend: each run under its cap (E1 $6.50, E2 $28.60, twice
E0-5's estimates), and over both runs a pause at $23.36 (four thirds of the approved $17.52) and a hard stop at
$35.04 (brief 30 dated note 1; the coordinator's STATUS line of 2026-11-03); passing the pause needs Aravind's word
(`--past-pause`). Key 2's remaining limit and the account's balance are recorded before each run (`limits`; numbers
only, no key text) and the run refuses when the smaller is below its stop.

No item text, rubric, answer or key is printed or written outside the caches; ids are opaque. The gate tables are
`stage3_elicitation_gate_reachability_v1.py`'s.

    set -a; source work/mole-fork/.env; set +a
    PY=work/mole-fork/.venv/bin/python
    $PY -I work/checks/stage3_elicitation_e1e2.py limits --exp e1
    $PY -I work/checks/stage3_elicitation_e1e2.py prices --exp e1
    $PY -I work/checks/stage3_elicitation_e1e2.py plan --exp e1
    $PY -I work/checks/stage3_elicitation_e1e2.py run --exp e1 --approved-usd 3.23
    (then the same for e2 with --approved-usd 14.29)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import traceback
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_legibility as lg  # noqa: E402

VERSION = "elicitation-e1e2/v0"
PROJECT = HERE.parent.parent
S3 = PROJECT / "work" / "stage3"
OUT = S3 / "elicitation" / "e1e2"
BRIEF = PROJECT / "briefs" / "30-elicitation-writer-rounds-2026-11-02.md"
B23 = "work/stage3/legibility"
B25 = "work/stage3/b3/comprehension"
T1_TRIPLES = "work/stage3/t1k-rater/stripped-triples.json"
B3_TRIPLES = "work/stage3/b3/rater/stripped-triples-b3.json"

T1_REGIMES = ("v2_conforming", "v3_middle")
RUBRIC_REGIMES = ("candidate",) + T1_REGIMES
FALSE_REGIMES = ("control", "sham")
EXPS = ("e1", "e2")
EXPECTED_ITEMS = {"e1": 38, "e2": 172}
E1_SAMPLE = 1                  # brief 23's r1
E2_SAMPLES = (0, 1)            # two new pinned samples
E1_READERS = ("kimi", "sol", "sonnet55")
KEY_ENV = "OPENROUTER_API_KEY_2"   # brief 30 decision 9
APPROVED = {"e1": 3.23, "e2": 14.29}   # E0-5's estimates (gate-reachability-v0.md), approved by Aravind (brief 29 note 12)
CAP_USD = {"e1": 6.50, "e2": 28.60}    # twice the estimates (brief 30 decision 9)
PAUSE_TOTAL_USD = 23.36                # four thirds of $17.52: pause for Aravind (brief 30 dated note 1)
HARD_TOTAL_USD = 35.04                 # twice $17.52 (the coordinator's STATUS line of 2026-11-03)
REISSUE_ROUNDS = 3                     # re-issues of reads left errored (a reply served off the pin is errored)
ORDER_OFFSET = {"e1": 300, "e2": 400}  # call order seeds: lg.ORDER_SEED + offset (+ reader index; scorer + 9)
LIMITS_MAX_AGE_S = 3 * 3600
OPENROUTER = "https://openrouter.ai/api/v1"


# ── rules (pure) ─────────────────────────────────────────────────────────────────────────────────

def l_target(regime: str) -> str:
    """The L target for brief 23's T1 regimes and brief 25's regimes together."""
    if regime in RUBRIC_REGIMES:
        return "rubric"
    if regime in FALSE_REGIMES:
        return "false"
    raise ValueError(f"no L target for regime {regime!r} in E1 or E2")


def select_e1(rows23: Sequence[Mapping[str, Any]], expected: int = EXPECTED_ITEMS["e1"]) -> list[dict]:
    """The T1 items brief 23 read once (not in its retest subset), by id."""
    out = sorted(({**r, "source": "b23"} for r in rows23 if r["regime"] in T1_REGIMES and not r["retest"]),
                 key=lambda r: r["item_id"])
    if len(out) != expected:
        raise SystemExit(f"refusing: E1 selects {len(out)} items, expected {expected}")
    return out


def select_e2(rows23: Sequence[Mapping[str, Any]], rows25: Sequence[Mapping[str, Any]],
              expected: int = EXPECTED_ITEMS["e2"]) -> list[dict]:
    """Brief 25's items (candidates, controls, comparison items), then brief 23's T1 items; each by id."""
    a = sorted(({**r, "source": "b25"} for r in rows25), key=lambda r: r["item_id"])
    b = sorted(({**r, "source": "b23"} for r in rows23 if r["regime"] in T1_REGIMES), key=lambda r: r["item_id"])
    ids = [r["item_id"] for r in a + b]
    if len(set(ids)) != len(ids):
        raise SystemExit("refusing: an item id occurs twice in E2's selection")
    if len(ids) != expected:
        raise SystemExit(f"refusing: E2 selects {len(ids)} items, expected {expected}")
    return a + b


def read_units(exp: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, list[tuple[int, str, str]]]:
    if exp == "e1":
        return {f: [(E1_SAMPLE, r["item_id"], c) for r in rows for c in lg.CONDS] for f in E1_READERS}
    if exp == "e2":
        return {"kimi": [(s, r["item_id"], c) for r in rows for s in E2_SAMPLES for c in lg.CONDS]}
    raise ValueError(exp)


def scorer_units(row: Mapping[str, Any]) -> list[tuple[int, str]]:
    t = l_target(row["regime"])
    return [(p, t) for p in lg.PASSES]


def rubric_text(row: Mapping[str, Any], cond: str, target: str, rub23: Mapping[str, Any], rub25: Mapping[str, Any]) -> str:
    if row["source"] == "b23":
        if target != "rubric":
            raise ValueError("E1 and E2 score brief 23's T1 items against their rubric only")
        return rub23["test"][row["item_id"]]
    import stage3_b3_comprehension as comp
    return comp.rubric_for(row, rub25, cond, target)


def stop_usd(exp: str, e1_spent: float, past_pause: bool = False) -> float:
    """The run's stop: E1 at its cap; E2 at its cap, the pause over both runs (or, past it, the hard stop) less E1's spend."""
    if exp == "e1":
        return CAP_USD["e1"]
    total = HARD_TOTAL_USD if past_pause else PAUSE_TOTAL_USD
    return round(min(CAP_USD["e2"], total - e1_spent), 6)


KEY_FIELDS = ("limit", "limit_remaining", "limit_reset", "usage", "usage_daily", "usage_weekly", "usage_monthly", "is_free_tier")


def limits_summary(key_json: Mapping[str, Any], credits_json: Mapping[str, Any] | None) -> dict:
    """Numbers only: the key's limit fields (never its label) and the account's balance; headroom is the smaller."""
    k = key_json.get("data") or {}
    key = {f: k.get(f) for f in KEY_FIELDS if f in k}
    acc = None
    if credits_json and credits_json.get("data"):
        c = credits_json["data"]
        acc = {"total_credits": float(c["total_credits"]), "total_usage": float(c["total_usage"]),
               "remaining": round(float(c["total_credits"]) - float(c["total_usage"]), 6)}
    vals = [float(key["limit_remaining"])] if key.get("limit_remaining") is not None else []
    if acc is not None:
        vals.append(acc["remaining"])
    return {"key": key, "account": acc, "headroom_usd": min(vals) if vals else None}


class Recs(lg.Records):
    """Brief 23's records and outcome rules, with the L target of both briefs' regimes."""

    def reader_status(self, fam: str, r: int, row: Mapping[str, Any], cond: str) -> str:
        rec = self.read.get((fam, r, row["item_id"], cond))
        if rec is None or rec.get("outcome") == "errored":
            return "missing"
        parsed = rec.get("parsed") or {}
        if rec["outcome"] == "refused":
            return "refused_token" if parsed.get("declined_token") else "refused_provider"
        if parsed.get("declined_token"):
            return "refused_token"
        lt = l_target(row["regime"])
        flags = [self.score.get((fam, r, row["item_id"], cond, lt, p)) for p in lg.PASSES]
        if all(f is not None and f.get("outcome") == "scored" and (f.get("parsed") or {}).get("declined") for f in flags):
            return "refused_prose"
        return "answered"


def sample_values(rec: Recs, fam: str, s: int, row: Mapping[str, Any]) -> tuple[float | None, float | None]:
    """(D_whole, D_part) of one reader and sample: the whole's score and the maximum over the parts (each the mean over
    the scored passes); None, None unless all four conditions are scored (E0-5's rule for a per-part record)."""
    st = rec.item_stat(fam, s, row, l_target(row["regime"]))
    if st["status"] != "computed":
        return None, None
    return float(st["D_whole"]), float(st["D_part"])


def served_summary(records: Sequence[Mapping[str, Any]]) -> dict:
    """Per final record (lg.latest: the last scored or refused, else the last errored): the provider and precision of
    its last attempt; every attempt served off the pin, counted."""
    off = sum(1 for r in records for s in (r.get("served") or []) if not s.get("on_pin"))
    fin = lg.latest(records)
    per, by = {}, Counter()
    for r in fin.values():
        s = (r.get("served") or [None])[-1]
        per[r["label"]] = {"outcome": r.get("outcome"), "provider": s and s.get("provider"), "precision": s and s.get("precision"),
                           "on_pin": s and s.get("on_pin")}
        by[f"{s['provider']}|{s['precision']}|{'on_pin' if s.get('on_pin') else 'off_pin'}" if s else "none"] += 1
    return {"final_records": len(fin), "final_by_provider": dict(sorted(by.items())), "attempts_off_pin": off,
            "final_off_pin": sum(1 for v in per.values() if v["on_pin"] is False), "per_record": dict(sorted(per.items()))}


def printable(summary: Mapping[str, Any]) -> dict:
    """The run summary as printed: no abort reasons (lg.strip_reasons) and the served block as counts (provider names hold
    spaces, which the print guard refuses; the names stay in run-summary.json)."""
    out = lg.strip_reasons(dict(summary))
    ks = summary.get("kimi_served")
    if ks is not None:
        out["kimi_served"] = {"final_records": ks["final_records"],
                              "final_on_pin": sum(v for k, v in ks["final_by_provider"].items() if k.endswith("|on_pin")),
                              "attempts_off_pin": ks["attempts_off_pin"], "final_off_pin": ks["final_off_pin"]}
    return out


# ── clients ──────────────────────────────────────────────────────────────────────────────────────

def make_pinned_kimi(cache_path: Path | None, models: Mapping[str, Any], cap: float | None, guard: Any = None,
                     listing: dict[str, list[str]] | None = None) -> Any:
    """lg.make_reader's OpenRouter reader for Kimi K3, unchanged but for the pin and the served record."""
    import judge_openrouter_pin as pin
    lg.check_reasoning_env()
    pr = lg.price_per_token("openrouter", pin.KIMI_MODEL, models)
    return pin.PinnedOpenRouterJudge(cache_path, pin.KIMI_MODEL, system=lg.READER_SYSTEM, prompt_version=lg.READER_PROMPT_VERSION,
                                     prices={"prompt": pr["in"], "completion": pr["out"]}, price_source=models.get("price_source", ""),
                                     concurrency=lg.READER_CONCURRENCY, rpm=lg.READER_RPM, temperature=None, spend_cap_usd=cap,
                                     parse=lg.parse_answer, moderation_as_refusal=True, verbose=False,
                                     request_guard=guard.check if guard is not None else None, api_key_env=KEY_ENV,
                                     pin=pin.KIMI_K3_WAFER_MXFP4, endpoint_listing=listing)


def _missing(client: Any, units: Sequence[tuple[int, str, str]]) -> list[tuple[int, str, str]]:
    done = {(lab["r"], lab["item"], lab["cond"]) for rec in client.cache.values()
            if rec.get("outcome") in ("scored", "refused") and (lab := lg.parse_label(rec["label"])) and lab["role"] == "read"}
    return [u for u in units if u not in done]


async def run_experiment(rows: Sequence[Mapping[str, Any]], packets: Mapping[tuple[str, str], str], readers: Mapping[str, Any],
                         scorer: Any, rubric_fn, units: Mapping[str, Sequence[tuple[int, str, str]]], guard: Any, log: Path,
                         offset: int) -> dict:
    """Every reader on its units (readers in parallel), re-issuing the units left without a scored or refused record up
    to REISSUE_ROUNDS times; then the scorer on every answered read's L target, two passes."""
    async def one(j: int, fam: str) -> dict:
        res, rounds = None, 0
        for rounds in range(1, REISSUE_ROUNDS + 2):
            todo = _missing(readers[fam], units[fam])
            if not todo:
                rounds -= 1
                break
            res = await lg.run_units(readers[fam], [(lg.READ_VIEW, lg.read_label(s, i, c), packets[(i, c)])
                                                    for s, i, c in lg.ordered(todo, offset + j)], guard, log, f"read:{fam}:round{rounds}")
            if res["aborted"]:
                break
        left = len(_missing(readers[fam], units[fam]))
        return {"units": len(units[fam]), "rounds": rounds, "missing_after": left,
                "aborted": bool(res and res["aborted"]), "abort_reason": res and res["abort_reason"]}

    fams = list(readers)
    out: dict[str, Any] = {"read": dict(zip(fams, await asyncio.gather(*(one(j, f) for j, f in enumerate(fams)))))}
    if any(v["aborted"] for v in out["read"].values()):
        out["score"] = {"skipped": True, "aborted": True, "abort_reason": "a reader aborted"}
        return out
    rec = Recs({f: cl.cache.values() for f, cl in readers.items()}, [])
    by_id = {r["item_id"]: r for r in rows}
    s_units = []
    for fam in fams:
        for s, i, c in units[fam]:
            a = rec.answer(fam, s, i, c)
            if a is None:
                continue
            for p, t in scorer_units(by_id[i]):
                s_units.append((lg.SCORE_VIEW, lg.score_label(p, fam, s, i, c, t), lg.scorer_packet(rubric_fn(by_id[i], c, t), a)))
    out["score"] = await lg.run_units(scorer, lg.ordered(s_units, offset + 9), guard, log, "score")
    out["score"]["units"] = len(s_units)
    return out


# ── inputs ───────────────────────────────────────────────────────────────────────────────────────

def day0_texts() -> dict[str, str]:
    """The seeder's day-0 texts of the six class documents (lg.load_inputs's code)."""
    import stage3_views as sv
    from stage3_t1v2_checks import DOCS
    seed = sv.seed_base()
    day0 = {path: text for (_svc, path), text in seed.items() if path in DOCS}
    if set(day0) != set(DOCS):
        raise SystemExit("refusing: the seeder's day-0 texts do not cover the six class documents")
    return day0


def load_sources(root: Path = PROJECT) -> dict[str, Any]:
    """Briefs 23 and 25's committed rows, rubrics and triples, with the checks that the rendering is theirs."""
    import stage3_b3_comprehension as comp
    items23, rows23, tr23, rub23 = lg.rows_and_triples(root / B23, root / T1_TRIPLES)
    items25, rows25, rub25 = comp.load_items(root / B25)
    t1 = json.loads((root / T1_TRIPLES).read_text(encoding="utf-8"))
    b3 = json.loads((root / B3_TRIPLES).read_text(encoding="utf-8"))
    tr25 = comp.triples_for(rows25, {"data": {"triples_b3": b3, "t1_triples": t1}})
    day0 = day0_texts()
    p23, p25 = lg.all_packets(rows23, tr23, day0), lg.all_packets(rows25, tr25, day0)
    checks = {"b23_packets": lg.packets_sha256(p23) == items23["packets_sha256"],
              "b25_packets": lg.packets_sha256(p25) == items25["packets_sha256"],
              "b23_day0": lg.day0_sha256(day0) == items23["day0_sha256"], "b25_day0": lg.day0_sha256(day0) == items25["day0_sha256"],
              "instrument_prompts_are_brief23s": items23["prompt_sha256"] == lg.prompt_hashes(),
              "instrument_config_is_brief23s": items23["config_sha256"] == lg.config_sha256(),
              "b25_instrument_config": items25["config"]["instrument_config_sha256"] == lg.config_sha256()}
    files = (f"{B23}/items-v0.json", f"{B23}/rubrics-v0.json", f"{B23}/routes-v0.json", f"{B25}/items-v0.json",
             f"{B25}/rubrics-v0.json", T1_TRIPLES, B3_TRIPLES)
    return {"rows23": rows23, "rows25": rows25, "rub23": rub23, "rub25": rub25, "packets": {**p23, **p25}, "checks": checks,
            "routes23": json.loads((root / B23 / "routes-v0.json").read_text()),
            "inputs_sha256": {f: lg.file_sha256(root / f) for f in files}}


def e0_5_estimates(root: Path = PROJECT) -> dict:
    """E0-5's figures by its own code (stage3_elicitation_gate_reachability.estimates, the caches' recorded costs)."""
    import stage3_elicitation_gate_reachability as gr
    e = gr.estimates(root, EXPECTED_ITEMS["e1"], EXPECTED_ITEMS["e2"], 0, 0)
    return {"e1": e["E1_t1_second_sample"], "e2": e["E2_pinned_kimi_two_samples"], "basis": e["basis"]}


def exp_rows(exp: str, src: Mapping[str, Any]) -> list[dict]:
    return select_e1(src["rows23"]) if exp == "e1" else select_e2(src["rows23"], src["rows25"])


def plan_core(exp: str, src: Mapping[str, Any]) -> dict:
    rows = exp_rows(exp, src)
    units = read_units(exp, rows)
    sub = {(r["item_id"], c): src["packets"][(r["item_id"], c)] for r in rows for c in lg.CONDS}
    return {"version": VERSION, "exp": exp, "items": len(rows), "item_ids_sha256": lg.sha256("\n".join(r["item_id"] for r in rows)),
            "by_regime": dict(sorted(Counter(r["regime"] for r in rows).items())),
            "reads": {f: len(u) for f, u in units.items()}, "scorer_calls_at_most": sum(len(u) for u in units.values()) * len(lg.PASSES),
            "samples": [E1_SAMPLE] if exp == "e1" else list(E2_SAMPLES), "packets_sha256": lg.packets_sha256(sub),
            "input_checks": src["checks"], "inputs_sha256": src["inputs_sha256"], "script_sha256": lg.file_sha256(Path(__file__)),
            "pin": "Wafer at MXFP4 (judge_openrouter_pin.KIMI_K3_WAFER_MXFP4)", "kimi_key_env": KEY_ENV,
            "dependency_sha256": {d: lg.file_sha256(PROJECT / d) for d in ("work/checks/judge_openrouter_pin.py", "work/checks/stage3_legibility.py",
                                                                         "work/checks/stage3_b3_comprehension.py", *lg.DEPENDENCIES)}}


# ── modes ────────────────────────────────────────────────────────────────────────────────────────

def _get(url: str, key: str) -> dict:
    import httpx
    r = httpx.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=30.0)
    r.raise_for_status()
    return r.json()


def mode_limits(ns: argparse.Namespace) -> int:
    import judge_client as jc
    import judge_openrouter as jo
    key = jo.key_from_env(KEY_ENV)
    if not key:
        raise SystemExit(f"{KEY_ENV} is not set (source work/mole-fork/.env)")
    try:
        kj = _get(f"{OPENROUTER}/key", key)
    except Exception:  # noqa: BLE001  (the older path)
        kj = _get(f"{OPENROUTER}/auth/key", key)
    try:
        cj = _get(f"{OPENROUTER}/credits", key)
    except Exception as exc:  # noqa: BLE001
        cj = None
        print(json.dumps({"credits_endpoint": type(exc).__name__}), file=sys.stderr)
    s = {"version": VERSION, "checked_at": jc._now_iso(), "key_env": KEY_ENV, **limits_summary(kj, cj)}
    d = Path(ns.out_dir) / ns.exp
    d.mkdir(parents=True, exist_ok=True)
    n = len(list(d.glob("limits-*.json")))
    p = d / f"limits-{n:02d}.json"
    p.write_text(json.dumps(s, indent=1) + "\n")
    lg.emit({"limits_file": p.name, "headroom_usd": s["headroom_usd"], "key": s["key"], "account": s["account"]})
    return 0


def mode_prices(ns: argparse.Namespace) -> int:
    d = Path(ns.out_dir) / ns.exp
    d.mkdir(parents=True, exist_ok=True)
    return lg.mode_prices(argparse.Namespace(out_dir=str(d)))


def mode_plan(ns: argparse.Namespace) -> int:
    d = Path(ns.out_dir) / ns.exp
    src = load_sources()
    if not all(src["checks"].values()):
        raise SystemExit(f"refusing: input checks failed {sorted(k for k, v in src['checks'].items() if not v)}")
    core = plan_core(ns.exp, src)
    est = e0_5_estimates()
    plan = {**core, "estimate": {"e0_5": est[ns.exp], "basis": est["basis"]}, "approved_usd": APPROVED[ns.exp], "cap_usd": CAP_USD[ns.exp],
            "pause_total_usd": PAUSE_TOTAL_USD, "hard_total_usd": HARD_TOTAL_USD, "reissue_rounds": REISSUE_ROUNDS,
            "brief": {"path": str(BRIEF.relative_to(PROJECT)), "sha256": lg.file_sha256(BRIEF)}}
    if est[ns.exp]["total_usd"] != APPROVED[ns.exp]:
        raise SystemExit(f"refusing: E0-5's estimate now gives {est[ns.exp]['total_usd']}, not the approved {APPROVED[ns.exp]}")
    d.mkdir(parents=True, exist_ok=True)
    (d / "plan-v0.json").write_text(json.dumps(plan, indent=1) + "\n")
    lg.emit({k: plan[k] for k in ("exp", "items", "by_regime", "reads", "scorer_calls_at_most", "packets_sha256", "input_checks",
                                  "approved_usd", "cap_usd")} | {"plan_sha256": lg.file_sha256(d / "plan-v0.json")})
    return 0


def _latest_limits(d: Path) -> dict:
    import judge_client as jc
    fs = sorted(d.glob("limits-*.json"))
    if not fs:
        raise SystemExit("refusing: no key-limit record (run the limits mode first)")
    s = json.loads(fs[-1].read_text())
    from datetime import datetime
    age = (datetime.fromisoformat(jc._now_iso()) - datetime.fromisoformat(s["checked_at"])).total_seconds()
    if age > LIMITS_MAX_AGE_S:
        raise SystemExit("refusing: the key-limit record is older than three hours (run the limits mode again)")
    return {**s, "file": fs[-1].name}


def _cache_usd(d: Path) -> float:
    return round(sum(float(x.get("cost_usd") or 0) for p in (d / "cache").glob("*.jsonl") for x in lg.read_jsonl(p)), 6)


def mode_run(ns: argparse.Namespace) -> int:
    import judge_client as jc
    root = Path(ns.out_dir)
    d = root / ns.exp
    plan = json.loads((d / "plan-v0.json").read_text())
    if abs(float(ns.approved_usd) - APPROVED[ns.exp]) > 0.005 or abs(float(plan["approved_usd"]) - APPROVED[ns.exp]) > 0.005:
        raise SystemExit(f"refusing: --approved-usd is not the approved {APPROVED[ns.exp]}")
    src = load_sources()
    core = plan_core(ns.exp, src)
    bad = sorted(k for k, v in core.items() if plan.get(k) != v)
    if bad:
        raise SystemExit(f"refusing: the run differs from plan-v0.json: {bad}")
    if not all(src["checks"].values()):
        raise SystemExit("refusing: input checks failed")
    e1_spent = _cache_usd(root / "e1") if ns.exp == "e2" else 0.0
    if ns.exp == "e2" and not (root / "e1" / "run-summary.json").exists():
        raise SystemExit("refusing: E2 runs after E1 (brief 30 §3)")
    stop = stop_usd(ns.exp, e1_spent, ns.past_pause)
    lim = _latest_limits(d)
    if lim["headroom_usd"] is not None and lim["headroom_usd"] < stop:
        raise SystemExit(f"refusing: key 2's headroom ${lim['headroom_usd']:.2f} is below this run's stop ${stop:.2f}")
    if lg.any_cache_records(d) and not ns.resume:
        raise SystemExit("refusing: calls are already on file; pass --resume to continue this run")
    lg.check_reasoning_env()
    models = json.loads((d / "models-v0.json").read_text())
    import judge_openrouter_pin as pin
    endpoints = pin.fetch_endpoints(pin.KIMI_MODEL)
    listing = pin.listing_from_endpoints(endpoints)
    if pin.served_precision("Wafer", pin.KIMI_K3_WAFER_MXFP4, listing) != "mxfp4":
        raise SystemExit("refusing: Wafer at MXFP4 is not in Kimi K3's endpoint listing")
    (d / "kimi-endpoints.json").write_text(json.dumps({"fetched_at": jc._now_iso(), "listing": listing,
                                                      "sha256": jc.sha256(json.dumps(endpoints, sort_keys=True))}, indent=1) + "\n")
    guard = lg.SpendGuard(stop)
    rows = exp_rows(ns.exp, src)
    units = read_units(ns.exp, rows)
    readers: dict[str, Any] = {}
    for fam in units:
        cp = lg.reader_cache(d, fam, lg.FAMILIES[fam].get("openrouter") if fam == "kimi" else src["routes23"]["chosen"][fam]["model"])
        if fam == "kimi":
            readers[fam] = make_pinned_kimi(cp, models, cap=stop, guard=guard, listing=listing)
        else:
            ch = src["routes23"]["chosen"][fam]
            readers[fam] = lg.make_reader(fam, ch["route"], ch["model"], cp, models, cap=stop, guard=guard)
    scorer = lg.make_scorer(lg.scorer_cache(d), cap=stop, guard=guard)
    drift = {f: lg.cache_drift(c, lg.READER_SYSTEM) for f, c in readers.items()}
    drift["scorer"] = lg.cache_drift(scorer, lg.SCORER_SYSTEM)
    if any(drift.values()):
        raise SystemExit(f"refusing: cached records under another system prompt or max_tokens: {drift}")
    guard.clients = list(readers.values()) + [scorer]
    summary: dict[str, Any] = {"version": VERSION, "exp": ns.exp, "started_at": jc._now_iso(), "resume": bool(ns.resume),
                               "stop_usd": stop, "past_pause": bool(ns.past_pause), "e1_spent_usd": e1_spent,
                               "limits_file": lim["file"], "headroom_usd": lim["headroom_usd"],
                               "plan_sha256": lg.file_sha256(d / "plan-v0.json")}

    def rub(row, cond, target):
        return rubric_text(row, cond, target, src["rub23"], src["rub25"])

    summary["run"] = asyncio.run(run_experiment(rows, src["packets"], readers, scorer, rub, units, guard, d / "run-batches.jsonl",
                                                ORDER_OFFSET[ns.exp]))
    summary["finished_at"] = jc._now_iso()
    summary["dollars"] = {**{f: round(c.total_spent(), 4) for f, c in readers.items()}, "scorer": round(scorer.total_spent(), 4),
                          "total": round(guard.total(), 4)}
    summary["kimi_served"] = {k: v for k, v in served_summary(list(lg.read_jsonl(readers["kimi"].cache_path))).items() if k != "per_record"}
    summary["outcomes"] = {f: dict(Counter(r.get("outcome") for r in lg.latest(lg.read_jsonl(c.cache_path)).values()))
                           for f, c in {**readers, "scorer": scorer}.items()}
    summary["stopped"] = guard.total() >= stop or any(v["aborted"] for v in summary["run"]["read"].values()) or \
        bool(summary["run"]["score"].get("aborted"))
    (d / "run-summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    lg.emit(printable(summary))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="brief 30 Part 2: E1 and E2")
    ap.add_argument("mode", choices=("limits", "prices", "plan", "run"))
    ap.add_argument("--exp", choices=EXPS, required=True)
    ap.add_argument("--out-dir", default=str(OUT))
    ap.add_argument("--approved-usd", type=float, default=None)
    ap.add_argument("--past-pause", action="store_true", help="only on Aravind's word: E2's stop moves from the pause to the hard stop")
    ap.add_argument("--resume", action="store_true")
    ns = ap.parse_args(argv)
    if ns.mode == "run" and ns.approved_usd is None:
        raise SystemExit("refusing: run needs --approved-usd (E0-5's approved estimate)")
    fn = {"limits": mode_limits, "prices": mode_prices, "plan": mode_plan, "run": mode_run}[ns.mode]
    try:
        return fn(ns)
    except SystemExit:
        raise
    except Exception as exc:   # print the type only; the traceback (which may quote a value) goes to a file
        out = Path(ns.out_dir) / ns.exp
        out.mkdir(parents=True, exist_ok=True)
        with (out / "errors.log").open("a", encoding="utf-8") as f:
            f.write(traceback.format_exc() + "\n")
        print(json.dumps({"error": type(exc).__name__, "mode": ns.mode, "traceback": "errors.log"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
