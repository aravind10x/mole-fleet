#!/usr/bin/env python3
"""Phase B Part 2 scorer (brief 38 steps 5 and 6, dated notes 3 and 4; pre-registration v1.2, 414cecc3).

Scores the composed view `O_diff` under the six arms (B0 fresh, B0h, B1, B2, B3, B4; B1-all not confirmed, not run)
for Opus 4.8 (max_tokens 4000, no effort) and Sonnet 5 (max_tokens 900), each with the sealed `O_diff` system prompt
and prompt version, through the pinned client. Packets come from the committed renderers
(`stage3_phase_b_grounded.py`, hash checked against the pre-registration's §4).

  nulls         the 254 honest units -> work/stage3/phase-b/nulls-v0.json
  applications  the 256 applications (T1 v3 middle, routine re-draw, sham re-draw; T1 v2 conforming, sham)
                -> work/stage3/phase-b/applications-v0.json
  --dry         build every packet and run the checks; no client is built, no call made

Spend: one cache per judge (`judge-cache.phaseb.O_diff.<model>.jsonl`), every client given `spend_cap_usd` explicitly
(the cap less the other judge's recorded dollars) and one shared `request_guard` that stops both clients when the
dollars recorded in both caches reach the cap. Arms are scored in order within a judge, the two judges in parallel;
after each arm its realised dollars are checked against twice its share of the estimate (`estimate-v1.json`), and
the run stops there if exceeded. Checks before any call: the pre-registration's hash, the renderers' hash, B0
byte-equal to the sealed null packets (nulls), no packet over the cap, no header naming a roster account.

Records keep ids, scores, outcomes, tokens, dollars and packet hashes; never a packet, a task, a statement or a
rationale (the cache holds the client's records, as every earlier run's did).

    cd work/mole-fork && set -a && source .env && set +a && cd ../.. && \\
      work/mole-fork/.venv/bin/python -I work/checks/stage3_phase_b_score.py nulls --cap 237.54
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import judge_client as jc_mod  # noqa: E402
import score_expensive_tier as set_  # noqa: E402
import stage3_phase_b_b1all as b1a  # noqa: E402
import stage3_phase_b_dryrun as dr  # noqa: E402
import stage3_phase_b_grounded as g  # noqa: E402
import stage3_thresholds as th  # noqa: E402
import stage3_views as sv  # noqa: E402

VERSION = "phase-b-score/v2"
P = HERE.parent / "stage3" / "phase-b"
PREREG = P / "preregistration-v1.2.md"
PREREG_SHA_PREFIX = "414cecc3"
ESTIMATE = P / "estimate-v1.json"
VIEW = "O_diff"
ARMS = g.ARMS + (b1a.ARM,)          # B1-all confirmed by Aravind (gate amendment, 7 Nov); beside B1, never in the verdict
MODELS = {"opus48": "anthropic.claude-opus-4-8", "sonnet": "anthropic.claude-sonnet-5"}
MAX_TOKENS = {"opus48": 4000, "sonnet": 900}
TIE_SEED = 20261112
BOOT_SEED = g.SEED
N_BOOT = 2000
OUT = {"nulls": P / "nulls-v0.json", "applications": P / "applications-v0.json"}


def sha256_file(p: Path) -> str:
    return g.file_sha256(p)


def cache_path(judge: str) -> Path:
    return P / f"judge-cache.phaseb.{VIEW}.{MODELS[judge].replace('.', '-')}.jsonl"


def committed_renderer_sha() -> str:
    text = PREREG.read_text(encoding="utf-8")
    key = "`stage3_phase_b_grounded.py` sha256 `"
    i = text.index(key) + len(key)
    return text[i:i + 64]


def preflight() -> dict:
    ps = sha256_file(PREREG)
    if not ps.startswith(PREREG_SHA_PREFIX):
        raise SystemExit(f"refusing: {PREREG.name} is {ps[:8]}, not the committed {PREREG_SHA_PREFIX}")
    rs = sha256_file(HERE / "stage3_phase_b_grounded.py")
    if rs != committed_renderer_sha():
        raise SystemExit("refusing: the renderers differ from the hash the pre-registration commits")
    return {"preregistration_sha256": ps, "renderer_sha256": rs, "script_sha256": sha256_file(Path(__file__).resolve()),
            "judge_client_sha256": sha256_file(HERE / "judge_client.py"), "estimate_sha256": sha256_file(ESTIMATE),
            "b1all_sha256": sha256_file(HERE / "stage3_phase_b_b1all.py"),
            "system_sha256": jc_mod.sha256(sv.system_prompt(VIEW, 0)), "prompt_version": sv.prompt_version(VIEW, 0)}


def headers_name_account(out: dict, u: dict, roster) -> int:
    return dr.names_in_headers(out, u, roster)


def build(world: g.World, mode: str) -> tuple[list[dict], list[dict], dict]:
    """(units, items, checks). Units carry ids, cluster and the free rules' counts; items one packet per unit and arm."""
    units, items = [], []
    chk = Counter()
    if mode == "nulls":
        sealed = dr.load(dr.S / "views" / "o_diff_cumulative.json")["packets"]
        src = [(u, None) for u in g.null_units(world)]
    else:
        src = [(a, None) for ver in ("v3", "v2") for a in g.application_units(world, ver)]
    for u, _ in src:
        out = g.render_packets(u["path"], u["frm"], u["to"], u["text"], u["edits"], world.pool, roster=world.roster)
        out[b1a.ARM] = b1a.packet(u["path"], u["frm"], u["to"], u["text"], u["edits"], world.feeds, roster=world.roster)
        head = g.sealed_head(u["path"], u["frm"], u["to"])
        blk = out[b1a.ARM]["packet"][len(head): len(out[b1a.ARM]["packet"]) - (len(out["B0"]["packet"]) - len(head))]
        chk["b1all_headers_naming_an_account"] += any(a in blk or g.workspace(a) in blk for a in world.roster)
        chk["b1all_last_not_in_force"] += sum(not b1a.last_is_in_force(world.feeds, e) for e in u["edits"])
        if mode == "nulls":
            chk["b0_equals_sealed"] += out["B0"]["packet"] == sealed.get(u["label"])
        chk["over_cap"] += sum(v["over_cap"] for v in out.values())
        chk["headers_naming_an_account"] += headers_name_account(out, u, world.roster)
        ukey = u["label"] if mode == "nulls" else f"{u['ver']}:{u['payload_id']}:{u['arm']}"
        rec = {"unit": ukey, "label": u["label"], "chain": [u["path"], u["boundary_index"]], "n_edits": len(u["edits"]),
               "b5": g.b5_count(u["edits"]), "b5p": g.b5p_count(u["edits"]), "b5_applied": g.b5_applied_count(u["edits"]),
               "no_task": sum(e.task is None for e in u["edits"]),
               "applied_no_task": sum(e.task is None for e in u["edits"] if e.applied)}
        if mode == "applications":
            rec.update({"ver": u["ver"], "regime": u["regime"], "payload_id": u["payload_id"], "arm": u["arm"]})
        else:
            rec.update({"write_index": u["write_index"], "boundary_day": u["boundary_day"]})
        units.append(rec)
        for arm in ARMS:
            v = out[arm]
            label = f"{u['label']}#phaseb:{arm}"
            items.append({"unit": ukey, "arm": arm, "label": label, "packet": v["packet"], "chars": v["chars"],
                          "packet_sha256": v["sha256"], "key": jc_mod.cache_key(VIEW, label, v["packet"])})
    chk["units"] = len(units)
    chk["items"] = len(items)
    return units, items, dict(chk)


def shares(mode: str) -> dict[tuple[str, str], float]:
    """Each (judge, arm)'s share of the estimate for this step."""
    rows = dr.load(ESTIMATE)["estimate"]["rows"]
    out: dict[tuple[str, str], float] = defaultdict(float)
    for r in rows:
        if (r["population"] == "null") == (mode == "nulls"):
            out[(r["judge"], r["arm"])] += r["usd"]
            if r["arm"] == "B1":
                out[(r["judge"], b1a.ARM)] += r["usd"]       # B1-all's share: B1's cost (the estimate's stated lower bound)
    return dict(out)


class Guard:
    """One spend stop across both judges' caches (the clients' request_guard)."""

    def __init__(self, cap: float):
        self.cap = cap
        self.clients: dict[str, Any] = {}
        self.aborted: str | None = None

    def total(self) -> float:
        live = {j: c.total_spent() for j, c in self.clients.items()}
        disk = {j: set_dollars(cache_path(j)) for j in MODELS if j not in live}
        return round(sum(live.values()) + sum(disk.values()), 6)

    def __call__(self) -> None:
        t = self.total()
        if t >= self.cap:
            self.aborted = f"Phase B cap: ${t:.4f} recorded across both caches reaches ${self.cap:.2f}"
            raise jc_mod.JudgeAborted(self.aborted)


def set_dollars(p: Path) -> float:
    """Every dollar recorded in a cache file (latest record per key), errored records included."""
    if not p.exists():
        return 0.0
    tot = 0.0
    for rec in set_.latest_records(p).values():
        tot += float(rec.get("cost_usd") or 0.0)
    return tot


def make_client(judge: str, guard: Guard, cap: float, concurrency: int, rpm: int) -> jc_mod.JudgeClient:
    cp = cache_path(judge)
    model = MODELS[judge]
    system, pv = sv.system_prompt(VIEW, 0), sv.prompt_version(VIEW, 0)
    set_.check_cache(cp, model, prompt_version=pv)
    others = sum(set_dollars(cache_path(j)) for j in MODELS if j != judge)
    jc = jc_mod.JudgeClient(cache_path=cp, concurrency=concurrency, rpm=rpm, model=model, spend_cap_usd=round(cap - others, 4),
                            max_tokens=MAX_TOKENS[judge], system=system, prompt_version=pv, effort=None, request_guard=guard)
    want = jc_mod.sha256(system)
    bad = [r.get("cache_key") for r in jc.cache.values() if (r.get("request_params") or {}).get("system_sha256") not in (None, want)
           or (r.get("request_params") or {}).get("output_config") is not None
           or (r.get("request_params") or {}).get("max_tokens") not in (None, MAX_TOKENS[judge])]
    if bad:
        raise SystemExit(f"refusing: {cp.name} holds {len(bad)} record(s) under another prompt, effort or max_tokens")
    guard.clients[judge] = jc
    return jc


def slim(r: dict | None) -> dict:
    if r is None:
        return {"outcome": "missing", "score": None}
    return {"outcome": r.get("outcome"), "score": r.get("score"), "cost_usd": round(float(r.get("cost_usd") or 0.0), 6),
            "input_tokens": int(r.get("input_tokens") or 0), "output_tokens": int(r.get("output_tokens") or 0),
            "stop_reason": r.get("stop_reason"), "model_served": r.get("model_served"),
            "attempts": len(r.get("attempts") or [])}


async def run_judge(judge: str, jc: jc_mod.JudgeClient, items: list[dict], sh: dict, log: dict) -> None:
    by_arm = defaultdict(list)
    for it in items:
        by_arm[it["arm"]].append(it)
    log[judge] = {"arms": {}, "stopped": None}
    for arm in ARMS:
        its = by_arm[arm]
        recs: dict[str, dict] = {}
        aborted = None
        for _pass in range(2):                                   # a second pass re-asks errored records once
            todo = [it for it in its if (recs.get(it["key"]) or {}).get("outcome") not in ("scored", "refused")]
            if not todo:
                break
            got, aborted = await sv.score_items(jc, todo, VIEW)
            recs.update(got)
            if aborted:
                break
        usd = sum(float((recs.get(it["key"]) or {}).get("cost_usd") or 0.0) for it in its)
        share = sh.get((judge, arm), 0.0)
        oc = Counter((recs.get(it["key"]) or {}).get("outcome", "missing") for it in its)
        log[judge]["arms"][arm] = {"n": len(its), "outcomes": dict(oc), "usd": round(usd, 4), "share_usd": round(share, 4),
                                   "over_twice_share": usd > 2 * share, "scores": {it["unit"]: slim(recs.get(it["key"])) for it in its}}
        print(f"{judge} {arm}: {dict(oc)} ${usd:.2f} against share ${share:.2f}", file=sys.stderr, flush=True)
        if aborted:
            log[judge]["stopped"] = f"{arm}: {aborted}"
            return
        if usd > 2 * share:
            log[judge]["stopped"] = f"{arm}: realised ${usd:.2f} exceeds twice its share ${share:.2f}"
            return


def threshold_summary(units: list[dict], scores: dict) -> dict:
    """Per arm: the randomised 10 percent rule on the scored null and its chain-bootstrap interval (2,000 replicates,
    the 18 (document, boundary) chains resampled)."""
    clus = sorted({tuple(u["chain"]) for u in units})
    cid = {c: i for i, c in enumerate(clus)}
    rng = np.random.default_rng([BOOT_SEED, 5])
    idx = rng.integers(0, len(clus), size=(N_BOOT, len(clus)))
    W = np.zeros((N_BOOT, len(clus)))
    np.add.at(W, (np.repeat(np.arange(N_BOOT), len(clus)), idx.ravel()), 1.0)
    out = {}
    for arm, d in scores.items():
        xs = [(cid[tuple(u["chain"])], d[u["unit"]]["score"]) for u in units if d.get(u["unit"], {}).get("outcome") == "scored"]
        if not xs:
            continue
        rule = th.randomised_threshold([float(s) for _, s in xs], dr.RATE, seed=TIE_SEED)
        H = np.zeros((len(clus), dr.V))
        for c, s in xs:
            H[c, int(s)] += 1
        t, _p = dr.fit(W @ H)
        out[arm] = {"threshold": rule["threshold"], "p_tie": round(rule["p_tie"], 4), "expected_rate": rule["expected_rate"],
                    "n_scored": len(xs), "threshold_chain_boot": [float(np.quantile(t, 0.025)), float(np.quantile(t, 0.975))]}
    return out


async def amain(ns) -> int:
    t0 = time.time()
    pf = preflight()
    world = g.World.load()
    units, items, chk = build(world, ns.mode)
    print(f"{ns.mode}: {json.dumps(chk)}", flush=True)
    if (chk["over_cap"] or chk["headers_naming_an_account"] or chk.get("b1all_headers_naming_an_account") or chk.get("b1all_last_not_in_force")
            or (ns.mode == "nulls" and chk["b0_equals_sealed"] != len(units))):
        raise SystemExit(f"STOP: a pre-call check failed: {chk}")
    sh = shares(ns.mode)
    if ns.dry:
        print(json.dumps({"dry": True, "units": len(units), "items": len(items), "shares_usd": {f"{j}:{a}": round(v, 2) for (j, a), v in sh.items()},
                          "chars_by_arm": {a: int(sum(it["chars"] for it in items if it["arm"] == a)) for a in ARMS}, **pf}))
        return 0
    if ns.cap is None:
        raise SystemExit("--cap is required (pass the spend cap explicitly)")
    judges = [ns.judge] if ns.judge != "both" else list(MODELS)
    guard = Guard(ns.cap)
    clients = {j: make_client(j, guard, ns.cap, ns.concurrency, ns.rpm) for j in judges}
    spent0 = guard.total()
    log: dict[str, Any] = {}
    sub = [it for it in items if (not ns.limit or it["unit"] in {u["unit"] for u in units[: ns.limit]})]
    await asyncio.gather(*(run_judge(j, clients[j], sub, sh, log) for j in judges))
    for j, jc in clients.items():
        jc.batch_log(P / "judge-batches.jsonl", note=f"phase-b {ns.mode} {j}" + (f" STOPPED {log[j]['stopped']}" if log[j]["stopped"] else ""))
    step_usd = round(sum(a["usd"] for j in log for a in log[j]["arms"].values()), 4)
    step_share = round(sum(v for (jj, _a), v in sh.items() if jj in judges), 4)
    rec = {"version": VERSION, "mode": ns.mode, **pf, "checks": chk, "cap_usd": ns.cap, "limit": ns.limit,
           "spent_before_usd": round(spent0, 4), "spent_after_usd": guard.total(), "step_usd": step_usd, "step_share_usd": step_share,
           "step_over_twice_share": step_usd > 2 * step_share,
           "judges": {j: {"model": MODELS[j], "max_tokens": MAX_TOKENS[j], "stopped": log[j]["stopped"],
                          "arms": {a: {k: v for k, v in d.items() if k != "scores"} for a, d in log[j]["arms"].items()},
                          "stats": clients[j].stats()} for j in judges},
           "units": units, "scores": {j: {a: d["scores"] for a, d in log[j]["arms"].items()} for j in judges},
           "seconds": round(time.time() - t0, 1)}
    if ns.mode == "nulls":
        rec["thresholds"] = {j: threshold_summary(units, rec["scores"][j]) for j in judges}
    out = Path(ns.out) if ns.out else OUT[ns.mode]
    if ns.limit:
        out = out.with_name(out.stem + f"-smoke{ns.limit}.json")
    out.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print("SUMMARY", json.dumps({"step_usd": step_usd, "step_share_usd": step_share, "spent_after_usd": rec["spent_after_usd"],
                                 "stopped": {j: log[j]["stopped"] for j in judges},
                                 "outcomes": {j: {a: d["outcomes"] for a, d in log[j]["arms"].items()} for j in judges},
                                 "usd": {j: {a: d["usd"] for a, d in log[j]["arms"].items()} for j in judges},
                                 "thresholds": rec.get("thresholds")}, default=str))
    print(f"wrote {out} sha256 {sha256_file(out)[:16]}")
    return 1 if any(log[j]["stopped"] for j in judges) or rec["step_over_twice_share"] else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("mode", choices=("nulls", "applications"))
    ap.add_argument("--cap", type=float, default=None, help="the spend cap across both judges' caches (required for a run)")
    ap.add_argument("--judge", choices=("opus48", "sonnet", "both"), default="both")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--rpm", type=int, default=40)
    ap.add_argument("--limit", type=int, default=0, help="smoke: only the first N units (output gets a -smokeN suffix)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry", action="store_true")
    return asyncio.run(amain(ap.parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
