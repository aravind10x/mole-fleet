"""Token and dollar accounting for a generated corpus (part-3 cost spike).

  python scripts/cost_report.py --transcripts data/corpus/spike/calib.transcripts.jsonl \
      --model moonshotai/kimi-k2.6 [--audit data/corpus/spike/calib.jsonl] [--json out.json]

Reads the per-session transcript records written by the agentic generator
(`input_tokens`, `output_tokens`, `turn_count`, `finish_reason`, `session_mode`,
`account`, `sim_ts`), prices them with configs/prices.yaml, and prints:
  - sessions, tokens in/out, mean and median per session, dollars, by mode
  - refusal/abort counts (finish_reason / aborted_reason) and sessions with no tool calls
  - extrapolations: one simulated day of benign cover for 150 accounts at
    --sessions-per-day, one k=3 campaign (3 colluders + --honest honest accounts,
    --campaign-days days), and the full Tier-1/Tier-2 volumes from 06-cost-estimate.md
If --audit is given, also reports audit events per session and harm-relevant
gate events (update_config / submit_eval / tag_approved / deploy to prod).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
PRICES = REPO / "configs" / "prices.yaml"

REFUSAL_MARKERS = ("i can't", "i cannot", "i won't", "i will not", "not able to help",
                   "can't help with", "decline", "refuse")


def load_prices(model: str) -> dict[str, float]:
    doc = yaml.safe_load(PRICES.read_text(encoding="utf-8"))
    p = (doc.get("models") or {}).get(model)
    if p is None:
        sys.exit(f"no price for {model!r} in {PRICES}; add it (USD per 1M tokens)")
    return {"input": float(p["input"]), "output": float(p["output"]),
            "cached_input": float(p.get("cached_input", p["input"]))}


def dollars(tok_in: int, tok_out: int, price: dict[str, float], cached_in: int = 0) -> float:
    uncached = max(0, tok_in - cached_in)
    return (uncached * price["input"] + cached_in * price["cached_input"]
            + tok_out * price["output"]) / 1e6


def _last_assistant_text(messages: list[dict]) -> str:
    for m in reversed(messages or []):
        if m.get("role") == "assistant" and isinstance(m.get("content"), str):
            return m["content"]
    return ""


def _tool_calls(messages: list[dict]) -> int:
    return sum(len(m.get("tool_calls") or []) for m in (messages or []) if m.get("role") == "assistant")


def analyse(records: list[dict], price: dict[str, float]) -> dict:
    by_mode: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_mode[r.get("session_mode", "benign")].append(r)
    out: dict = {"sessions": len(records), "by_mode": {}}
    tot_in = tot_out = 0
    for mode, rs in sorted(by_mode.items()):
        tin = [int(r.get("input_tokens") or 0) for r in rs]
        tout = [int(r.get("output_tokens") or 0) for r in rs]
        tot_in += sum(tin); tot_out += sum(tout)
        turns = [int(r.get("turn_count") or 0) for r in rs]
        finish = Counter(str(r.get("finish_reason")) for r in rs)
        aborted = Counter(str(r.get("aborted_reason")) for r in rs if r.get("aborted_reason"))
        no_tools = sum(1 for r in rs if _tool_calls(r.get("messages") or []) == 0)
        refusal_text = sum(1 for r in rs
                           if any(k in _last_assistant_text(r.get("messages") or []).lower()
                                  for k in REFUSAL_MARKERS))
        out["by_mode"][mode] = {
            "sessions": len(rs),
            "tokens_in": sum(tin), "tokens_out": sum(tout),
            "mean_in": round(statistics.mean(tin), 1) if tin else 0,
            "median_in": statistics.median(tin) if tin else 0,
            "mean_out": round(statistics.mean(tout), 1) if tout else 0,
            "mean_total": round(statistics.mean(i + o for i, o in zip(tin, tout)), 1) if tin else 0,
            "mean_turns": round(statistics.mean(turns), 1) if turns else 0,
            "dollars": round(dollars(sum(tin), sum(tout), price), 4),
            "dollars_per_session": round(dollars(sum(tin), sum(tout), price) / max(1, len(rs)), 4),
            "finish_reason": dict(finish),
            "aborted_reason": dict(aborted),
            "sessions_without_tool_calls": no_tools,
            "sessions_with_refusal_text": refusal_text,
        }
    out["tokens_in"] = tot_in
    out["tokens_out"] = tot_out
    out["cached_input_tokens"] = sum(int(r.get("cached_input_tokens") or 0) for r in records)
    out["reasoning_tokens"] = sum(int(r.get("reasoning_tokens") or 0) for r in records)
    reported = sum(float(r.get("cost_usd") or 0.0) for r in records)
    out["dollars_reported_by_provider"] = round(reported, 4)
    out["dollars_from_price_table"] = round(dollars(tot_in, tot_out, price), 4)
    # Prefer the provider-reported cost when present (it includes cache discounts and
    # reasoning-token billing); fall back to the price table.
    out["dollars"] = round(reported if reported > 0 else dollars(tot_in, tot_out, price), 4)
    out["dollars_per_session"] = round(out["dollars"] / max(1, len(records)), 4)
    out["accounts"] = len({r.get("account") for r in records})
    out["sim_days"] = len({str(r.get("sim_ts", ""))[:10] for r in records})
    return out


def extrapolate(rep: dict, *, sessions_per_day: int, honest: int, campaign_days: int) -> dict:
    per = rep["dollars_per_session"]
    benign_day_150 = 150 * sessions_per_day * per
    campaign = (3 + honest) * campaign_days * sessions_per_day * per
    return {
        "assumes_dollars_per_session": per,
        "benign_day_150_accounts": round(benign_day_150, 2),
        "k3_campaign_3_colluders_plus_honest": round(campaign, 2),
        "tier1_140_campaigns_plus_90_dev": round(230 * campaign, 2),
        "tier1_600_benign_releases_as_branch_days(10 accounts x 1 day each)":
            round(600 * 10 * sessions_per_day * per, 2),
        "tier2_live_world_150x10days": round(10 * benign_day_150, 2),
        "estimate_doc_assumed": {"tokens_per_session": 50_000, "blended_usd_per_M": 0.8,
                                 "usd_per_session": 0.04},
    }


def audit_summary(audit_path: Path, records: list[dict]) -> dict:
    n = 0
    per_task: Counter = Counter()
    gate = Counter()
    failed = 0
    with audit_path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            e = json.loads(line)
            n += 1
            per_task[e.get("task_id", "")] += 1
            if e.get("exit_code", 0) != 0:
                failed += 1
            svc, act = e.get("service"), e.get("action")
            args = e.get("args") or {}
            if (svc, act) in (("eval_server", "update_config"), ("eval_server", "submit_eval"),
                              ("model_registry", "tag_approved"), ("eval_server", "run_reference_suite")):
                gate[f"{svc}.{act}"] += 1
            if svc == "model_registry" and act == "deploy":
                env = str(args.get("environment", "")).strip().lower()
                gate[f"deploy.{'prod' if env in ('prod', 'production') else env or 'unknown'}"] += 1
    sessions = {r.get("task_id") for r in records if r.get("task_id")}
    counts = [per_task[t] for t in sessions]
    return {
        "events": n, "failed_events": failed,
        "events_per_session_mean": round(statistics.mean(counts), 1) if counts else 0,
        "sessions_with_zero_events": sum(1 for c in counts if c == 0),
        "gate_events": dict(gate),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cost_report")
    ap.add_argument("--transcripts", required=True)
    ap.add_argument("--model", required=True, help="OpenRouter slug (key in configs/prices.yaml)")
    ap.add_argument("--audit", default=None)
    ap.add_argument("--sessions-per-day", type=int, default=4)
    ap.add_argument("--honest", type=int, default=4, help="honest accounts per k=3 campaign")
    ap.add_argument("--campaign-days", type=int, default=3)
    ap.add_argument("--json", default=None, help="write the full report here")
    args = ap.parse_args(argv)

    price = load_prices(args.model)
    records = [json.loads(l) for l in Path(args.transcripts).read_text(encoding="utf-8").splitlines()
               if l.strip()]
    rep = analyse(records, price)
    rep["model"] = args.model
    rep["price_usd_per_M"] = price
    rep["extrapolation"] = extrapolate(rep, sessions_per_day=args.sessions_per_day,
                                       honest=args.honest, campaign_days=args.campaign_days)
    if args.audit:
        rep["audit"] = audit_summary(Path(args.audit), records)
    text = json.dumps(rep, indent=2)
    print(text)
    if args.json:
        Path(args.json).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
