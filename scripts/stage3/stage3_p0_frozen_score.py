#!/usr/bin/env python3
"""Line P0, Part 2 (`P0/brief-state-and-rescore.md` a519f2ce; gate `P2/preregistration-v1.1.md` section E, ab171917):
arm B's scorer (sealed O_diff prompt, Opus 4.8, the ETJ client and settings) on the 56 frozen-state packets the red side
rendered (`P0/cache/packets-frozen-v0.jsonl`, cd0d6205), flagged at arm B's own fresh rules from `ETJ/scores-B.json`
(10 percent, and 5 percent beside; no new null).

Blue side. Packets are read by script only; this prints and writes counts, ids, hashes, scores and flags only.

Modes:
* `smoke --n 3`: a seeded sample of the 56, priced; estimate = mean per unit x 56; the score cap is 1.5 x that.
* `score`: the 56 under that cap (`P0/frozen-B-v0.json`: scores and outcomes by application key).
* `analyse`: flags, S raw and under both audit completions (on all scorable payloads and S_same / S_other), flag changes
  against the recorded 13 Nov flags and arm B's fresh 13 Nov flags, the paired missed tables, the packet comparison
  against the ETJ planted packets (the reader's states), and section E's two checks (`P0/frozen-scores-v0.json`).
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

PROJECT = HERE.parent.parent
S3 = PROJECT / "work" / "stage3"
P0 = S3 / "v5" / "P0"
ETJ = S3 / "v5" / "ETJ"
PACKETS = P0 / "cache" / "packets-frozen-v0.jsonl"
PACKETS_SHA = "cd0d6205471b1a50b9495319e0a61778828d15a933f0480432ee7e1d4adce4b3"
INDEX = P0 / "frozen-index-v0.json"
CACHE = P0 / "cache"
SMOKE_OUT = P0 / "frozen-smoke-v0.json"
SCORE_OUT = P0 / "frozen-B-v0.json"
ANALYSIS_OUT = P0 / "frozen-scores-v0.json"
SEED = 20261113
AGREEMENT_MIN = 0.90


# ── packets ──────────────────────────────────────────────────────────────────────────────────────

def packet_fields(packet: str) -> dict:
    """From, To and the diff body of a composed-view packet (`From: …`, `To: …`, `Unified diff (N chars):` + body)."""
    head, sep, body = packet.partition("Unified diff (")
    if not sep:
        raise ValueError("no unified-diff header")
    body = body.split("):\n", 1)[1] if "):\n" in body else ""
    frm = to = None
    for line in head.splitlines():
        if line.startswith("From: "):
            frm = line[len("From: "):]
        elif line.startswith("To: "):
            to = line[len("To: "):]
    return {"from": frm, "to": to, "body": body}


def _without_to_line(packet: str) -> list[str]:
    return [ln for ln in packet.split("\n") if not ln.startswith("To: ")]


def equal_apart_from_to_line(a: str, b: str) -> bool:
    return _without_to_line(a) == _without_to_line(b)


def compare_packets(frozen: Mapping[str, str], recorded: Mapping[str, str]) -> dict:
    out = {"n": len(frozen), "identical": 0, "to_differs": 0, "from_differs": 0, "body_differs": 0,
           "only_to_timestamp_differs": 0, "equal_apart_from_to_line": 0, "missing_recorded": 0}
    for k, p in frozen.items():
        if k not in recorded:
            out["missing_recorded"] += 1
            continue
        r = recorded[k]
        out["identical"] += int(p == r)
        out["equal_apart_from_to_line"] += int(equal_apart_from_to_line(p, r))
        a, b = packet_fields(p), packet_fields(r)
        d = {f: a[f] != b[f] for f in ("from", "to", "body")}
        out["to_differs"] += int(d["to"])
        out["from_differs"] += int(d["from"])
        out["body_differs"] += int(d["body"])
        out["only_to_timestamp_differs"] += int(d["to"] and not d["from"] and not d["body"])
    return out


def load_packets(path: Path, expected_sha: str) -> list[dict]:
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise SystemExit(f"refusing: {Path(path).name} is not the file of record")
    return [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]


def checked_frozen_units(packets: Path = PACKETS, index: Path = INDEX) -> list[dict]:
    recs = load_packets(packets, PACKETS_SHA)
    for r in recs:
        if hashlib.sha256(r["packet"].encode("utf-8")).hexdigest() != r["packet_sha256"]:
            raise SystemExit(f"refusing: packet hash mismatch on {r['key']}")
    idx = json.loads(Path(index).read_text(encoding="utf-8"))
    if idx.get("n_payloads") != len(recs):
        raise SystemExit("refusing: packets and index disagree on the count")
    return recs


# ── flags and tables ─────────────────────────────────────────────────────────────────────────────

def flag_changes(gov: Mapping[str, tuple], frozen: Mapping[str, Any], reader: Mapping[str, Any]) -> dict:
    out = {"n": 0, "changed": 0, "flagged_on_frozen_only": 0, "flagged_on_reader_only": 0}
    for _pid, (key, *_rest) in sorted(gov.items()):
        a, b = frozen.get(key), reader.get(key)
        if a is None or b is None:
            continue
        out["n"] += 1
        if bool(a) != bool(b):
            out["changed"] += 1
            out["flagged_on_frozen_only" if a else "flagged_on_reader_only"] += 1
    return out


def paired_missed(gov: Mapping[str, tuple], frozen: Mapping[str, Any], reader: Mapping[str, Any]) -> dict:
    """Missed (not flagged) on the frozen state and on the reader's state, by group and by reader_state_identical."""
    cell0 = lambda: {"both": 0, "frozen_only": 0, "reader_only": 0, "neither": 0}  # noqa: E731
    out = {g: {"identical": cell0(), "not_identical": cell0()} for g in ("RM", "AL")}
    for _pid, (key, regime, identical) in sorted(gov.items()):
        a, b = frozen.get(key), reader.get(key)
        if a is None or b is None:
            continue
        mf, mr = not a, not b
        cell = "both" if mf and mr else "frozen_only" if mf else "reader_only" if mr else "neither"
        g = "AL" if regime == "alarming" else "RM"
        out[g]["identical" if identical else "not_identical"][cell] += 1
    return out


def agreement(keys: Iterable[str], a: Mapping[str, Any], b: Mapping[str, Any]) -> dict:
    ks = list(keys)
    both = [k for k in ks if a.get(k) is not None and b.get(k) is not None]
    agree = sum(1 for k in both if bool(a[k]) == bool(b[k]))
    return {"n": len(both), "agree": agree, "share": agree / len(both) if both else None, "unscored": len(ks) - len(both)}


def size_range_check(sizes: Mapping[str, int], null_sizes: Sequence[int]) -> dict:
    lo, hi = min(null_sizes), max(null_sizes)
    below = sum(1 for v in sizes.values() if v < lo)
    above = sum(1 for v in sizes.values() if v > hi)
    return {"n": len(sizes), "n_inside": len(sizes) - below - above, "null_min": lo, "null_max": hi, "below": below,
            "above": above, "pass": below == 0 and above == 0}


def gate_E(*, n_identical: int, equal_apart_from_to_line: int, agreement_share: float | None, size_pass: bool) -> dict:
    c1 = {"n_identical_state_applications": n_identical, "equal_apart_from_to_line": equal_apart_from_to_line,
          "arm_B_flag_agreement": agreement_share, "agreement_min": AGREEMENT_MIN,
          "pass": equal_apart_from_to_line == n_identical and agreement_share is not None and agreement_share >= AGREEMENT_MIN}
    c2 = {"pass": bool(size_pass)}
    return {"check1": c1, "check2": c2, "name_S": c1["pass"] and c2["pass"]}


# ── modes (Bedrock; never run by tests) ──────────────────────────────────────────────────────────

def _write_new(path: Path, obj: Any) -> None:
    if path.exists():
        raise SystemExit(f"{path} exists; never overwritten")
    path.write_text(json.dumps(obj, indent=1) + "\n", encoding="utf-8")


def _units(recs: Sequence[Mapping]) -> list[dict]:
    return [{"label": r["key"], "packet": r["packet"]} for r in recs]


def mode_smoke(n: int, cap: float) -> dict:
    import stage3_etj as et
    recs = checked_frozen_units()
    units = _units(recs)
    pick = sorted(random.Random(SEED).sample(range(len(units)), n))
    cl = et.make_clients(CACHE, cap_usd=cap)
    got = asyncio.run(et.score_B(cl, [units[i] for i in pick]))
    costs = [r["cost_usd"] for r in got.values()]
    per = sum(costs) / len(costs)
    est = round(per * len(units), 4)
    out = {"n": n, "draw": "random.Random(20261113).sample of the 56", "outcomes": {k: r["outcome"] for k, r in got.items()},
           "usd_per_unit": round(per, 6), "usd_max": round(max(costs), 6), "estimate_usd_56": est, "cap_usd": round(1.5 * est, 4),
           "spend_usd": round(et.total_spent(cl), 6)}
    _write_new(SMOKE_OUT, out)
    return out


def mode_score() -> dict:
    import stage3_etj as et
    sm = json.loads(SMOKE_OUT.read_text(encoding="utf-8"))
    recs = checked_frozen_units()
    cl = et.make_clients(CACHE, cap_usd=float(sm["cap_usd"]))
    got = asyncio.run(et.score_B(cl, _units(recs)))
    out = {"arm": "B", "units": len(got), **et.null_shares(got), "cap_usd": sm["cap_usd"],
           "usd_this_run": round(sum(r["cost_usd"] for r in got.values()), 6), "spend_all_clients_usd": round(et.total_spent(cl), 6),
           "scores": {k: r["score"] for k, r in got.items()}, "outcomes": {k: r["outcome"] for k, r in got.items()}}
    _write_new(SCORE_OUT, out)
    return {k: v for k, v in out.items() if k not in ("scores", "outcomes")}


def mode_analyse(manifest_path: Path, core: Path, audit_table: Path, n_boot: int) -> dict:
    import stage3_etj as et
    import stage3_ft_join as fj
    import stage3_ft_run as fr
    import stage3_p1_joins as pj
    sb = json.loads((ETJ / "scores-B.json").read_text(encoding="utf-8"))
    fz = json.loads(SCORE_OUT.read_text(encoding="utf-8"))
    recs = checked_frozen_units()
    manifest = fr.load_manifest(manifest_path)
    outs = [json.loads(x) for x in Path(core).read_text(encoding="utf-8").splitlines() if x.strip()]
    table = json.loads(Path(audit_table).read_text(encoding="utf-8"))
    flags_loaded = fj.load_flags()
    rec10 = {k: v.get("flag10") for k, v in flags_loaded["applications"].items()}
    f10 = et.flags(fz["scores"], sb["rule10"])
    t5 = sb["rule5"]["threshold"]
    f5 = {k: (None if s is None else (True if s > t5 else False if s < t5 else "tie")) for k, s in fz["scores"].items()}
    gov, idx_ident = {}, {r["payload_id"]: r["reader_state_identical"] for r in recs}
    for m in manifest:
        if not m.get("scorable", True):
            continue
        key = fj.resolve_application(flags_loaded, m["application_id"])
        gov[m["payload_id"]] = (key, m["regime"], bool(m["reader_state_identical"]))
    frozen_keys = {r["key"] for r in recs}
    checks = {"governing_keys_equal_frozen_keys": {k for k, *_ in gov.values()} == frozen_keys,
              "manifest_identical_equals_index": sum(1 for p, (_k, _r, i) in gov.items() if idx_ident.get(p) == i),
              "manifest_identical_equals_same_lines": sum(1 for m in manifest if m.get("scorable", True)
                                                          and bool(m["reader_state_identical"]) == bool(m["reader_state_same_lines"]))}
    res: dict[str, Any] = {"settings": {"n_boot": n_boot, "seed": fj.SEED, "rule10": {k: sb["rule10"][k] for k in ("threshold", "p_tie", "seed")},
                                        "rule5": {k: sb["rule5"][k] for k in ("threshold", "p_tie", "seed")},
                                        "packets_sha256": PACKETS_SHA, "scores_file_sha256": hashlib.sha256(SCORE_OUT.read_bytes()).hexdigest()},
                           "consistency": checks, "outcomes": {k: fz[k] for k in ("units", "scored", "refused", "unparsed", "bad_share")}}
    # S on the frozen states, raw and under both audit completions (all scorable; S_same and S_other inside)
    man_f, pf_f = pj.pflags_with(manifest, flags_loaded, f10)
    res["S_frozen_10"] = {"n_governing_covered": len(man_f), **pj.variants(outs, man_f, pf_f, table, n_boot=n_boot)}
    f5b = {k: (v is True) if v is not None else None for k, v in f5.items()}
    res["S_frozen_5_ties_missed"] = pj.variants(outs, *pj.pflags_with(manifest, flags_loaded, f5b), table, n_boot=n_boot)
    res["S_reference"] = {"recorded": 0.295139, "fresh_B_13nov": "ETJ/analysis-v0.json S_B"}
    # flag changes and paired tables
    res["flag_changes"] = {"vs_recorded": flag_changes(gov, f10, rec10), "vs_fresh_B": flag_changes(gov, f10, sb["flags10"])}
    res["paired_missed"] = {"vs_recorded": paired_missed(gov, f10, rec10), "vs_fresh_B": paired_missed(gov, f10, sb["flags10"])}
    # packets against the ETJ planted packets (the reader's states)
    etj_units = {u["label"]: u["packet"] for u in et.checked_planted_units()}
    frozen = {r["key"]: r["packet"] for r in recs}
    ident_keys = sorted(r["key"] for r in recs if r["reader_state_identical"])
    res["packets_vs_reader"] = {"all": compare_packets(frozen, etj_units),
                                "identical_states": compare_packets({k: frozen[k] for k in ident_keys}, etj_units),
                                "other_states": compare_packets({k: v for k, v in frozen.items() if k not in ident_keys}, etj_units),
                                "chars": {"frozen_mean": round(sum(map(len, frozen.values())) / len(frozen), 1),
                                          "reader_mean": round(sum(len(etj_units[k]) for k in frozen if k in etj_units) / len(frozen), 1)}}
    # section E
    ag = agreement(ident_keys, f10, sb["flags10"])
    null_rows = json.loads(Path(et.RECORDED_NULL).read_text(encoding="utf-8"))["views"]["O_diff"]["rows"]
    size = size_range_check({k: len(v) for k, v in frozen.items()}, [int(r["packet_chars"]) for r in null_rows if r.get("packet_chars")])
    eq = res["packets_vs_reader"]["identical_states"]["equal_apart_from_to_line"]
    res["gate_E"] = {**gate_E(n_identical=len(ident_keys), equal_apart_from_to_line=eq, agreement_share=ag["share"], size_pass=size["pass"]),
                     "agreement_detail": ag, "agreement_vs_recorded_beside": agreement(ident_keys, f10, rec10), "size_detail": size}
    _write_new(ANALYSIS_OUT, res)
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P0 Part 2: arm B on the frozen-state packets (counts, scores and flags only).")
    ap.add_argument("mode", choices=("smoke", "score", "analyse"))
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--smoke-cap", type=float, default=1.0)
    ap.add_argument("--manifest", type=Path, default=S3 / "red" / "ft" / "cells-manifest.json")
    ap.add_argument("--core", type=Path, default=S3 / "v5" / "FT" / "outcomes-core-v0.jsonl")
    ap.add_argument("--audit-table", type=Path, default=S3 / "v5" / "FT" / "audit-table-core.json")
    ap.add_argument("--n-boot", type=int, default=2000)
    a = ap.parse_args(argv)
    if a.mode == "smoke":
        r = mode_smoke(a.n, a.smoke_cap)
    elif a.mode == "score":
        r = mode_score()
    else:
        full = mode_analyse(a.manifest, a.core, a.audit_table, a.n_boot)
        r = {"gate_E": {k: full["gate_E"][k] for k in ("check1", "check2", "name_S")},
             "S_frozen_10_raw": full["S_frozen_10"]["raw"]["S"], "flag_changes": full["flag_changes"],
             "consistency": full["consistency"]}
    print(json.dumps(r, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
