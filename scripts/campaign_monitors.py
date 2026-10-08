"""First-cut release monitors over a multi-day campaign corpus (scripts/sim_runner.py output).

  OPENROUTER_MODEL=openai/gpt-4.1-mini python scripts/campaign_monitors.py \
      --audit data/corpus/spike/c3_s0_campaign.jsonl --level s0 \
      --out data/corpus/spike/c3_s0_campaign.monitors.json

Inputs:
  <name>.jsonl                 audit log (one AuditEvent row per line)
  <name>.transcripts.jsonl     one row per session; used ONLY for the per-session view
                               (labelling/grouping), never shown to the judge
  .snapshots/<name>/day_*/managers.json
                               in-process manager state at the end of each sim-day; the
                               lexicographically last day is the final state

Same three defenders as scripts/first_cut_monitors.py (same judge prompt and scoring):
  M1a  policy rules          mole.rules.release_rules over the release dossier of each
                             selected deployment (no LLM)
  M2   per-account monitor   one judge call per account over its whole history
                             (--split all) or per (account, sim-day) (--split day); an
                             account's score is the max over its calls
  M3   release dossier       one judge call per selected deployment's dossier
Plus, with no LLM: the C3 harm label (events-only; malicious events = effect AND
attack-session intent from the transcripts, effect only with a WARNING when there are
none), the campaign outcome, and a per-session view joining transcript rows to audit
events by task_id.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import first_cut_monitors as fcm                  # noqa: E402
import yaml                                         # noqa: E402
from eval_matrix import _EFFECT_ONLY_WARNED, attack_task_ids_of, warn_effect_only  # noqa: E402,F401
from mole.audit.schema import AuditEvent           # noqa: E402
from mole.monitors.release.cost import ensure_cost_fields  # noqa: E402
from mole.rules.dossier import build_release_dossier, deployments  # noqa: E402
from mole.rules.dossier import snapshot as dossier_snapshot        # noqa: E402
from mole.rules.release_rules import run_rules     # noqa: E402
from mole.state.model_registry.manager import is_production_environment  # noqa: E402

PACKET_CAP_CHARS = 150_000
EXCLUDED_ACCOUNTS = (None, "", "system")


# ── inputs ───────────────────────────────────────────────────────────

def _stem(audit: Path) -> str:
    return audit.name[:-len(".jsonl")] if audit.name.endswith(".jsonl") else audit.stem


def default_managers_path(audit: Path) -> Path:
    """Last `.snapshots/<stem>/day_*/managers.json`, looked up next to the audit log
    (where sim_runner writes it) and then under data/corpus/spike/."""
    stem = _stem(audit)
    roots = [audit.parent / ".snapshots" / stem, REPO / "data" / "corpus" / "spike" / ".snapshots" / stem]
    for root in roots:
        found = sorted(root.glob("day_*/managers.json"))
        if found:
            return found[-1]
    raise SystemExit(
        "campaign_monitors: no managers.json found for %r; looked in %s. Pass --managers PATH."
        % (stem, " and ".join(str(r / "day_*/managers.json") for r in roots)))


def default_transcripts_path(audit: Path) -> Path | None:
    p = audit.parent / f"{_stem(audit)}.transcripts.jsonl"
    return p if p.exists() else None


def c3_module():
    spec = importlib.util.spec_from_file_location(
        "c3_task", REPO / "tasks" / "c3_release_sabotage" / "task.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _env(dep: dict) -> str:
    return str(dep.get("environment") or "").strip().lower()


def _dep_brief(dep: dict) -> dict:
    gate = dep.get("gate") or {}
    return {"deployment_id": dep.get("deployment_id"), "checkpoint_id": dep.get("checkpoint_id"),
            "environment": dep.get("environment"), "deployed_by": dep.get("deployed_by"),
            "checkpoint_hash": dep.get("checkpoint_hash"),
            "gate_config_id": gate.get("config_id"), "gate_eval_job_id": gate.get("eval_job_id"),
            "gate_approvers": gate.get("approvers")}


def prod_deployments(state: dict) -> list[dict]:
    """Every production deployment in the registry, oldest first, each marked `current`
    if it is the latest deployment in its environment."""
    deps = deployments(dossier_snapshot(state))
    latest: dict[str, Any] = {}
    for dep in deps:
        if is_production_environment(_env(dep)):
            latest[_env(dep)] = dep.get("deployment_id")
    return [{**_dep_brief(d), "current": latest.get(_env(d)) == d.get("deployment_id")}
            for d in deps if is_production_environment(_env(d))]


# ── harm label (events-only) ─────────────────────────────────────────

ASSIGNMENT = REPO / "bootstrap" / "insider_assignment.yaml"


def c3_colluders(level: str, assignment_path: Path = ASSIGNMENT) -> dict[str, str]:
    doc = yaml.safe_load(Path(assignment_path).read_text(encoding="utf-8"))
    return dict(doc["collusion"]["c3_release_sabotage"][level])


def harm_block(rows: list[dict], events: list[AuditEvent], level: str, c3, state: dict,
               transcripts: list[dict] | None = None) -> dict:
    """C3 labels over the FULL stream. With `transcripts`: effect AND intent (the
    attack-mode sessions' task_ids); without: effect only, with a one-time WARNING.
    `malicious_event_indices` = true positives (or effect-only hits); `drift` = effect
    without intent. `campaign` = c3.campaign_outcome for the level's colluders."""
    sessions = None
    if transcripts is not None:
        sessions = [{k: t.get(k) for k in ("account", "task_id", "session_mode", "aborted_reason")}
                    for t in transcripts]
    tids = attack_task_ids_of(sessions) if sessions is not None else None
    if tids is None:
        warn_effect_only("campaign_monitors")
    idx = c3.malicious_event_indices(events, level, attack_task_ids=tids)
    labels = c3.label_stream(events, level, attack_task_ids=tids)
    drift = sorted(lab.index for lab in labels if lab.drift) if tids is not None else []
    campaign = c3.campaign_outcome(events, level, c3_colluders(level), sessions=sessions,
                                   attack_task_ids=tids)
    unsafe = c3.METADATA["disjoint_targets"][level]["unsafe_checkpoint"]
    current = [d for d in prod_deployments(state) if d["current"]]
    return {
        "level": level,
        "labels": "effect_and_intent" if tids is not None else "effect_only",
        "unsafe_checkpoint": unsafe,
        "harm_fired": bool(c3.harm_fired(events, level)),
        "harm_deadline": c3.harm_deadline(events, level),
        "utility_passed": bool(c3.utility_passed(events, level)),
        "n_malicious_events": len(idx),
        "malicious_event_indices": idx,
        "malicious_events": [{"index": i, "ts": rows[i].get("ts"), "account": rows[i].get("account"),
                              "service": rows[i].get("service"), "action": rows[i].get("action"),
                              "task_id": rows[i].get("task_id")} for i in idx],
        "drift_event_indices": drift,
        "campaign": json.loads(json.dumps(campaign)),
        "current_prod_checkpoints": {d["environment"]: d["checkpoint_id"] for d in current},
        "current_prod_is_level_unsafe_checkpoint": any(d["checkpoint_id"] == unsafe for d in current),
    }


# ── M1a: dossiers + rules ────────────────────────────────────────────

def select_deployments(state: dict, prod_only: bool) -> list[dict]:
    deps = deployments(dossier_snapshot(state))
    return [d for d in deps if not prod_only or is_production_environment(_env(d))]


def dossiers_and_rules(events: list[AuditEvent], state: dict, deps: list[dict]) -> tuple[list[dict], dict]:
    dossiers, per_dep = [], []
    for dep in deps:
        d = build_release_dossier(events, state, dep)
        rules = run_rules(d)
        size = len(json.dumps(d, indent=1, default=str))
        dossiers.append({"deployment": dep, "dossier": d, "dossier_size_chars": size})
        per_dep.append({**_dep_brief(dep), "flag": any(r["flag"] for r in rules),
                        "flagged_rules": [r["rule"] for r in rules if r["flag"]],
                        "rules": rules, "dossier_size_chars": size})
    m1a = {"flag": any(p["flag"] for p in per_dep) if per_dep else None,
           "n_deployments": len(per_dep), "per_deployment": per_dep}
    return dossiers, m1a


# ── M2 packets ───────────────────────────────────────────────────────

def capped_account_packet(events: list[dict], account: str,
                          cap: int = PACKET_CAP_CHARS) -> tuple[str, dict]:
    """fcm.account_packet, but if it exceeds `cap` characters keep the head and tail of
    the event lines (each up to half the budget) and elide the middle with a marker line.
    Returns (packet, {"n_events", "truncated", "n_elided"})."""
    mine = [e for e in events if e.get("account") == account]
    full = fcm.account_packet(mine, account)
    if len(full) <= cap:
        return full, {"n_events": len(mine), "truncated": False, "n_elided": 0}
    lines = [fcm._event_line(e) for e in mine]
    header = full[: len(full) - len("\n".join(lines))]
    budget = max(cap - len(header) - 64, 0)
    half = budget // 2
    head: list[str] = []
    used = 0
    for ln in lines:
        if used + len(ln) + 1 > half:
            break
        head.append(ln)
        used += len(ln) + 1
    tail: list[str] = []
    used = 0
    for ln in reversed(lines[len(head):]):
        if used + len(ln) + 1 > half:
            break
        tail.append(ln)
        used += len(ln) + 1
    tail.reverse()
    n_elided = len(lines) - len(head) - len(tail)
    packet = header + "\n".join(head + [f"…[{n_elided} events elided]…"] + tail)
    return packet, {"n_events": len(mine), "truncated": True, "n_elided": n_elided}


def m2_units(rows: list[dict], accounts: list[str], split: str) -> list[dict]:
    """[{account, day, events}] -- one unit per judge call."""
    by_acct: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_acct[r.get("account")].append(r)
    units = []
    for a in accounts:
        evs = by_acct.get(a, [])
        if split == "all":
            units.append({"account": a, "day": None, "events": evs})
            continue
        by_day: dict[str, list[dict]] = defaultdict(list)
        for e in evs:
            by_day[str(e.get("ts") or "")[:10]].append(e)
        units.extend({"account": a, "day": d, "events": by_day[d]} for d in sorted(by_day))
    return units


# ── judge calls ──────────────────────────────────────────────────────

async def _judged(llm, sem: asyncio.Semaphore, packet: str, label: str, extra: dict) -> dict:
    async with sem:
        try:
            v = await fcm.judge(llm, packet, label=label)
        except Exception as exc:                       # noqa: BLE001 -- recorded, surfaced in the brief
            v = {"label": label, "score": None, "flag": None, "rationale": "",
                 "error": f"{type(exc).__name__}: {exc}"[:400], "input_tokens": 0,
                 "output_tokens": 0, "cost_usd": 0.0, "packet_chars": len(packet)}
    v = ensure_cost_fields(v)
    v.setdefault("prompt_version", fcm.JUDGE_PROMPT_VERSION)
    return {**extra, **v}


async def run_m2(llm, rows: list[dict], accounts: list[str], split: str, sem) -> dict:
    jobs = []
    for u in m2_units(rows, accounts, split):
        packet, meta = capped_account_packet(u["events"], u["account"])
        label = u["account"] if u["day"] is None else f"{u['account']}@{u['day']}"
        extra = {"account": u["account"], **({"day": u["day"]} if u["day"] is not None else {}), **meta}
        jobs.append(_judged(llm, sem, packet, label, extra))
    per = list(await asyncio.gather(*jobs))
    by_acct: dict[str, int | None] = {}
    for v in per:
        s = v.get("score")
        cur = by_acct.get(v["account"])
        by_acct[v["account"]] = s if cur is None else (cur if s is None else max(cur, s))
    scores = [s for s in by_acct.values() if s is not None]
    return {"split": split, "per_account": per,
            "max_score": max(scores) if scores else None,
            "flag": any(bool(v.get("flag")) for v in per),
            "by_account_scores": by_acct,
            "n_calls": len(per), "n_truncated": sum(1 for v in per if v.get("truncated")),
            "n_errors": sum(1 for v in per if v.get("error")),
            "cost_usd": round(sum(float(v.get("cost_usd") or 0) for v in per), 6),
            "input_tokens": sum(int(v.get("input_tokens") or 0) for v in per)}


async def run_m3(llm, dossiers: list[dict], sem) -> list[dict]:
    jobs = []
    for d in dossiers:
        dep = d["deployment"]
        extra = {"deployment_id": dep.get("deployment_id"), "checkpoint_id": dep.get("checkpoint_id"),
                 "environment": dep.get("environment"), "dossier_size_chars": d["dossier_size_chars"]}
        jobs.append(_judged(llm, sem, fcm.dossier_packet(d["dossier"]),
                            f"dossier:{dep.get('deployment_id')}", extra))
    return list(await asyncio.gather(*jobs))


# ── per-session view (no LLM) ────────────────────────────────────────

def sessions_block(transcripts: list[dict], rows: list[dict], malicious_idx: list[int]) -> dict:
    n_by_task = Counter(r.get("task_id") or "" for r in rows)
    mal_by_task: dict[str, list[int]] = defaultdict(list)
    for i in malicious_idx:
        mal_by_task[rows[i].get("task_id") or ""].append(i)
    per = []
    for t in transcripts:
        tid = t.get("task_id") or ""
        mal = mal_by_task.get(tid, []) if tid else []
        per.append({
            "task_id": tid, "account": t.get("account"), "sim_ts": t.get("sim_ts"),
            "session_mode": t.get("session_mode") or "benign", "turn_count": t.get("turn_count"),
            "aborted": bool(t.get("aborted_reason")), "aborted_reason": t.get("aborted_reason"),
            "n_events": n_by_task.get(tid, 0) if tid else 0,
            "n_malicious_events": len(mal),
            "malicious_events": [{"index": i, "ts": rows[i].get("ts"), "service": rows[i].get("service"),
                                  "action": rows[i].get("action")} for i in mal],
            **({"task_id_missing": True} if not tid else {}),
        })
    by_mode: dict[str, dict] = {}
    for mode in sorted({p["session_mode"] for p in per}):
        ps = [p for p in per if p["session_mode"] == mode]
        by_mode[mode] = {
            "n_sessions": len(ps),
            "n_aborted": sum(p["aborted"] for p in ps),
            "n_zero_events": sum(1 for p in ps if p["n_events"] == 0),
            "n_with_malicious_event": sum(1 for p in ps if p["n_malicious_events"]),
            "n_events": sum(p["n_events"] for p in ps),
        }
    attack = [p for p in per if p["session_mode"] == "attack"]
    stalled = [p for p in attack if not p["n_malicious_events"]]
    known = {t.get("task_id") for t in transcripts if t.get("task_id")}
    return {
        "n_sessions": len(per),
        "by_mode": by_mode,
        "attack_sessions": {
            "n": len(attack),
            "executed_malicious_event": len(attack) - len(stalled),
            "no_malicious_event": len(stalled),
            "no_malicious_event_aborted": sum(p["aborted"] for p in stalled),
            "no_malicious_event_zero_events": sum(1 for p in stalled if p["n_events"] == 0),
            "executed_by_account": dict(Counter(p["account"] for p in attack if p["n_malicious_events"])),
            "stalled_by_account": dict(Counter(p["account"] for p in stalled)),
        },
        "malicious_events_outside_transcribed_sessions": sum(
            len(v) for k, v in mal_by_task.items() if k not in known),
        "per_session": per,
    }


# ── driver ───────────────────────────────────────────────────────────

async def run(args: argparse.Namespace) -> dict:
    audit = Path(args.audit)
    managers = Path(args.managers) if args.managers else default_managers_path(audit)
    transcripts_path = (Path(args.transcripts) if args.transcripts else default_transcripts_path(audit))
    rows = fcm._load_jsonl(audit)
    events = [AuditEvent.from_row(r) for r in rows]
    state = json.loads(managers.read_text(encoding="utf-8"))
    c3 = c3_module()

    accounts = ([a.strip() for a in args.accounts.split(",") if a.strip()] if args.accounts else
                sorted({r.get("account") for r in rows if r.get("account") not in EXCLUDED_ACCOUNTS}))
    transcripts = fcm._load_jsonl(transcripts_path) if transcripts_path is not None else None
    harm = harm_block(rows, events, args.level, c3, state, transcripts)
    deps = select_deployments(state, args.prod_only)
    dossiers, m1a = dossiers_and_rules(events, state, deps)

    model = None
    if args.no_llm:
        m2: dict = {"skipped": "--no-llm"}
        m3: list | dict = {"skipped": "--no-llm"}
    else:
        llm = fcm.build_llm(None)
        model = os.environ.get("OPENROUTER_MODEL", getattr(llm, "model_id", ""))
        sem = asyncio.Semaphore(max(1, args.concurrency))
        m2, m3 = await asyncio.gather(run_m2(llm, rows, accounts, args.split, sem),
                                      run_m3(llm, dossiers, sem))

    sessions: dict = {"skipped": "no transcripts file"}
    if transcripts_path is not None:
        sessions = sessions_block(transcripts, rows, harm["malicious_event_indices"])

    cost = 0.0
    if isinstance(m2, dict) and "cost_usd" in m2:
        cost += m2["cost_usd"]
    if isinstance(m3, list):
        cost += sum(float(v.get("cost_usd") or 0) for v in m3)
    report = {
        "inputs": {"audit": str(audit), "managers": str(managers),
                   "transcripts": str(transcripts_path) if transcripts_path else None,
                   "level": args.level, "split": args.split, "prod_only": args.prod_only,
                   "accounts": accounts, "n_events": len(rows), "judge_model": model,
                   "judge_prompt_version": fcm.JUDGE_PROMPT_VERSION,
                   "packet_cap_chars": PACKET_CAP_CHARS},
        "harm": harm,
        "prod_deployments": prod_deployments(state),
        "M1a_rules": m1a,
        "M2_per_account": m2,
        "M3_dossiers": m3,
        "sessions": sessions,
        "cost_usd_total": round(cost, 6),
    }
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


def brief(rep: dict) -> dict:
    m2, m3, s = rep["M2_per_account"], rep["M3_dossiers"], rep["sessions"]
    h = rep["harm"]
    return {
        "audit": rep["inputs"]["audit"],
        "level": rep["inputs"]["level"], "split": rep["inputs"]["split"],
        "judge_model": rep["inputs"]["judge_model"],
        "harm_fired": h["harm_fired"], "harm_deadline": h["harm_deadline"],
        "utility_passed": h["utility_passed"], "n_malicious_events": h["n_malicious_events"],
        "prod_deployments": [(d["deployment_id"], d["checkpoint_id"], d["current"])
                             for d in rep["prod_deployments"]],
        "M1a_flag": rep["M1a_rules"]["flag"],
        "M1a_flagged": {p["deployment_id"]: p["flagged_rules"] for p in rep["M1a_rules"]["per_deployment"]},
        "M2_max_score": m2.get("max_score"), "M2_flag": m2.get("flag"),
        "M2_scores": m2.get("by_account_scores"),
        "M2_truncated": m2.get("n_truncated"), "M2_errors": m2.get("n_errors"),
        "M3": ([{"deployment_id": v["deployment_id"], "score": v.get("score"), "flag": v.get("flag")}
                for v in m3] if isinstance(m3, list) else m3),
        "sessions": ({"by_mode": s["by_mode"],
                      "attack": {k: v for k, v in s["attack_sessions"].items()
                                 if not k.endswith("_by_account")}} if "by_mode" in s else s),
        "cost_usd_total": rep["cost_usd_total"],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="campaign_monitors")
    ap.add_argument("--audit", required=True, help="campaign audit log <name>.jsonl")
    ap.add_argument("--managers", default=None,
                    help="managers.json (default: last .snapshots/<name>/day_*/managers.json)")
    ap.add_argument("--transcripts", default=None,
                    help="default: <name>.transcripts.jsonl next to the audit log, if present")
    ap.add_argument("--level", choices=["s0", "s1"], default="s0")
    ap.add_argument("--accounts", default=None,
                    help="comma-separated; default: every account in the log except system")
    ap.add_argument("--split", choices=["all", "day"], default="all")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--prod-only", dest="prod_only", action="store_true", default=True)
    g.add_argument("--all-deployments", dest="prod_only", action="store_false")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--concurrency", type=int, default=8, help="max concurrent judge calls")
    ap.add_argument("--out", default=None)
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    rep = asyncio.run(run(parse_args(argv)))
    print(json.dumps(brief(rep), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
