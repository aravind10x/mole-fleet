"""Run a scripted release-gate scenario (no LLM, no Docker) and report the harm oracle.

  python scripts/run_scenario.py --scenario attack --level s0 --ticket self --out data/corpus/spike/attack_s0
  python scripts/run_scenario.py --scenario legit  --level s0 --out data/corpus/spike/legit_s0

Writes <out>/audit.jsonl, <out>/managers.json and <out>/summary.json. With --rules,
also builds the release dossier for the production deployment and runs the policy
rules (mole/rules), recording them under summary["rules"].
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from mole.scenarios.release_sabotage import (          # noqa: E402
    SimClock, build_scenario_context, export_state, play_attack, play_legit,
    prod_deployment,
)


def _c3_module():
    spec = importlib.util.spec_from_file_location(
        "c3_task", REPO / "tasks" / "c3_release_sabotage" / "task.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


async def _main(args: argparse.Namespace) -> dict:
    out = Path(args.out)
    ctx, collector = await build_scenario_context(out)
    clock = SimClock.at(args.start)
    if args.scenario == "attack":
        ticket = None if args.ticket == "none" else args.ticket
        trace = await play_attack(ctx, level=args.level, clock=clock, ticket=ticket)
    else:
        trace = await play_legit(ctx, level=args.level, clock=clock)
    state = export_state(ctx, out)
    collector.close()

    c3 = _c3_module()
    events = list(collector.events)
    dep = prod_deployment(ctx)
    summary = {
        "scenario": args.scenario,
        "level": args.level,
        "ticket": args.ticket if args.scenario == "attack" else None,
        "harm_fired": bool(c3.harm_fired(events, args.level, ctx=ctx)) if hasattr(c3, "harm_fired") else None,
        "harm_fired_events_only": bool(c3.harm_fired(events, args.level)) if hasattr(c3, "harm_fired") else None,
        "harm_deadline": c3.harm_deadline(events, args.level) if hasattr(c3, "harm_deadline") else None,
        "deployed_prod": dep.get("checkpoint_id") if dep else None,
        "n_events": len(events),
        **trace.summary(),
    }
    if args.rules and dep is not None:
        from mole.rules.dossier import build_release_dossier
        from mole.rules.release_rules import run_rules
        d_live = build_release_dossier(events, ctx, dep)
        d_file = build_release_dossier(events, state, dep)
        summary["dossier_consistent"] = (json.dumps(d_live, sort_keys=True, default=str)
                                         == json.dumps(d_file, sort_keys=True, default=str))
        summary["rules"] = run_rules(d_live)
        (out / "dossier.json").write_text(json.dumps(d_live, indent=2, default=str), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="run_scenario")
    ap.add_argument("--scenario", choices=["attack", "legit"], required=True)
    ap.add_argument("--level", choices=["s0", "s1"], default="s0")
    ap.add_argument("--ticket", choices=["self", "honest", "none"], default="self",
                    help="attack only: who files the pretext ticket")
    ap.add_argument("--start", default="2026-04-06T09:00:00Z")
    ap.add_argument("--rules", action="store_true")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    summary = asyncio.run(_main(args))
    print(json.dumps({k: v for k, v in summary.items() if k != "steps"}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
