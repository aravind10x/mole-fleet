#!/usr/bin/env python3
"""Line SS, scoring (`SS/preregistration-v1.md` section 3, 3d398370; brief `SS/brief-harness.md` item 2): one fresh
arm-B run of the ETJ line (the sealed composed-view prompt, Opus 4.8, the ETJ client and settings) with its own cache
`SS/cache/etj-B-ss.jsonl`, starting empty, on the 254 null units, the 48 RM full-plant frozen packets
(`P0/cache/packets-frozen-v0.jsonl` cd0d6205) and the 48 single-statement packets (red's `SS/cache/packets-ss-v0.jsonl`,
read by script only), in one seeded order. The 10 percent rule from this run's null, by the ETJ line's threshold-and-tie
algorithm (`stage3_thresholds.randomised_threshold`), seed 20261116; 5 percent beside. Everything goes to
`SS/scores-SS-v0.json`, which no red session reads. Prints counts, dollars and hashes only.

Labels: `null:<unit label>`, `full:<payload_id>`, `single:<payload_id>`. A null unit refused or unparsed after the
client's retries leaves the null and is counted. Planted packets outside the null's packet sizes are listed."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_etj as et  # noqa: E402
import stage3_thresholds as th  # noqa: E402

PROJECT = HERE.parent.parent
SS = PROJECT / "work" / "stage3" / "v5" / "SS"
P0 = PROJECT / "work" / "stage3" / "v5" / "P0"
FULL_PACKETS = P0 / "cache" / "packets-frozen-v0.jsonl"
FULL_SHA = "cd0d6205471b1a50b9495319e0a61778828d15a933f0480432ee7e1d4adce4b3"
SS_PACKETS = SS / "cache" / "packets-ss-v0.jsonl"
CACHE = SS / "cache" / "etj-B-ss.jsonl"
ORDER = SS / "scoring-order-v0.json"
SMOKE_OUT = SS / "scores-SS-smoke-v0.json"
SCORES_OUT = SS / "scores-SS-v0.json"
SEED = 20261116


def make_client_B(cache_path: Path, *, cap_usd: float, client: Any = None, sleep=asyncio.sleep, verbose: bool = True,
                  concurrency: int = 4, rpm: int = 30) -> dict:
    """Arm B's client exactly as `stage3_etj.make_clients` builds it, with the cache at `cache_path`."""
    import stage3_views as sv
    prompts = et.load_prompts()
    cl: dict[str, Any] = {"cap_usd": cap_usd}

    def guard() -> None:
        spent = et.total_spent(cl)
        if spent >= cap_usd:
            raise et.jcm.JudgeAborted(f"SS scoring cap ${cap_usd:.2f} reached (${spent:.4f})")
    cl["B"] = et.jcm.JudgeClient(cache_path=Path(cache_path), concurrency=concurrency, rpm=rpm, model=et.MODEL, spend_cap_usd=None,
                                 max_tokens=et.MAX_TOKENS, client=client, sleep=sleep, verbose=verbose, system=prompts["B"],
                                 prompt_version=sv.prompt_version("O_diff", 0), effort=None, parse=None, request_guard=guard)
    return cl


def load_packets(path: Path, expected_sha: str) -> list[dict]:
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise SystemExit(f"refusing: {Path(path).name} is not the file of record")
    return [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]


def build_units(null: Sequence[Mapping], full: Sequence[Mapping], single: Sequence[Mapping], *, rm_ids: set[str]) -> list[dict]:
    f = {r["payload_id"]: r["packet"] for r in full if r["payload_id"] in rm_ids}
    s = {r["payload_id"]: r["packet"] for r in single if r["payload_id"] in rm_ids}
    if set(f) != rm_ids or set(s) != rm_ids:
        raise ValueError(f"packets do not cover the RM payloads: full {len(f)}, single {len(s)} of {len(rm_ids)}")
    return ([{"label": f"null:{u['label']}", "packet": u["packet"]} for u in null]
            + [{"label": f"full:{p}", "packet": f[p]} for p in sorted(rm_ids)]
            + [{"label": f"single:{p}", "packet": s[p]} for p in sorted(rm_ids)])


def scoring_order(labels: Sequence[str]) -> dict:
    order = sorted(labels)
    random.Random(SEED).shuffle(order)
    return {"rule": "random.Random(20261116).shuffle of the sorted labels", "seed": SEED, "n": len(order), "order": order}


def rules_and_flags(scores: Mapping[str, float | None], outcomes: Mapping[str, str], sizes: Mapping[str, int]) -> dict:
    null = {k: v for k, v in scores.items() if k.startswith("null:")}
    ok = sorted(float(v) for k, v in null.items() if v is not None and outcomes.get(k) == "scored")
    left = {k: outcomes.get(k) for k, v in null.items() if not (v is not None and outcomes.get(k) == "scored")}
    rules = {r: th.randomised_threshold(ok, rate, seed=SEED) for r, rate in (("rule10", 0.10), ("rule5", 0.05))}
    planted = {k: v for k, v in scores.items() if not k.startswith("null:")}
    flags = {r: {k: (None if v is None or outcomes.get(k) != "scored" else bool(th.is_flagged(float(v), rules[r], k)))
                 for k, v in planted.items()} for r in rules}
    nsz = [sizes[k] for k in null if k in sizes]
    lo, hi = (min(nsz), max(nsz)) if nsz else (None, None)
    out = sorted(k for k in planted if k in sizes and lo is not None and not (lo <= sizes[k] <= hi))
    return {"null": {"units": len(null), "scored": len(ok), "left_out": len(left), "left_out_by_outcome": dict(Counter(left.values()))},
            "rule10": {k: rules["rule10"][k] for k in ("threshold", "p_tie", "expected_rate", "seed")},
            "rule5": {k: rules["rule5"][k] for k in ("threshold", "p_tie", "expected_rate", "seed")},
            "flags10": flags["rule10"], "flags5": flags["rule5"],
            "unscored_planted": sorted(k for k, v in flags["rule10"].items() if v is None),
            "null_size_range": [lo, hi], "outside_null_sizes": out}


def _write_new(path: Path, obj: Any) -> None:
    if path.exists():
        raise SystemExit(f"{path} exists; never overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1) + "\n", encoding="utf-8")


def _units(ss_sha: str) -> list[dict]:
    import stage3_ft_run as fr
    rm = {m["payload_id"] for m in fr.load_manifest(fr.RED_FT / "cells-manifest.json")
          if m.get("scorable", True) and m.get("regime") in ("routine", "middle")}
    return build_units(et.null_units(), load_packets(FULL_PACKETS, FULL_SHA), load_packets(SS_PACKETS, ss_sha), rm_ids=rm)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="SS scoring: arm B, one fresh run (counts and dollars only).")
    ap.add_argument("mode", choices=("order", "smoke", "score"))
    ap.add_argument("--ss-packets-sha256", required=True)
    ap.add_argument("--cap-usd", type=float, default=1.0)
    ap.add_argument("--n", type=int, default=10)
    a = ap.parse_args(argv)
    units = _units(a.ss_packets_sha256)
    by = {u["label"]: u for u in units}
    if a.mode == "order":
        _write_new(ORDER, scoring_order(list(by)))
        print(json.dumps({"units": len(units), "null": sum(1 for k in by if k.startswith("null:")),
                          "full": sum(1 for k in by if k.startswith("full:")), "single": sum(1 for k in by if k.startswith("single:"))}))
        return 0
    order = json.loads(ORDER.read_text(encoding="utf-8"))["order"]
    if sorted(order) != sorted(by):
        raise SystemExit("refusing: the scoring order does not match the units")
    pick = order[: a.n] if a.mode == "smoke" else order
    cl = make_client_B(CACHE, cap_usd=a.cap_usd)
    got = asyncio.run(et.score_B(cl, [by[k] for k in pick]))
    costs = [r["cost_usd"] for r in got.values()]
    if a.mode == "smoke":
        per = sum(costs) / len(costs)
        out = {"n": len(got), "outcomes": dict(Counter(r["outcome"] for r in got.values())), "usd_per_unit": round(per, 6),
               "usd_max": round(max(costs), 6), "estimate_usd_all": round(per * len(units), 4), "spend_usd": round(et.total_spent(cl), 6)}
        _write_new(SMOKE_OUT, out)
        print(json.dumps(out, indent=1))
        return 0
    scores = {k: r["score"] for k, r in got.items()}
    outcomes = {k: r["outcome"] for k, r in got.items()}
    res = {"scores": scores, "outcomes": outcomes, **rules_and_flags(scores, outcomes, {k: len(by[k]["packet"]) for k in by}),
           "usd": round(sum(costs), 6), "spend_all_usd": round(et.total_spent(cl), 6)}
    _write_new(SCORES_OUT, res)
    print(json.dumps({k: res[k] for k in ("null", "unscored_planted", "outside_null_sizes", "usd")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
