"""Report what a corpus's final `release-gate` does to the safe release candidate and
to the unsafe checkpoints (passes / blocks / broken), from the run's last managers.json
snapshot. Use before branching a campaign from a warm-up (threshold ratchet check).

    .venv/bin/python scripts/gate_state.py data/corpus/spike/warmup_clean.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from mole.state.eval_server.manager import (  # noqa: E402
    gate_state, load_baseline_and_outcomes, outcomes_table_for,
)

SAFE = "ckpt-archetype-v1.1-rc1"


def report(corpus: Path) -> dict:
    from mole.generator import resume_state
    man = resume_state.load(corpus)
    days = man.get("days") or []
    if not days:
        raise SystemExit(f"{corpus}: no completed day in the manifest")
    last = days[-1]
    mp = Path(last["managers_path"])
    if not mp.exists():
        mp = corpus.parent / ".snapshots" / corpus.stem / f"day_{last['day']}" / "managers.json"
    state = json.loads(mp.read_text())["eval_server"]
    rec = state["_configs"]["release-gate"]
    ver = rec["versions"][-1]
    cfg = ver["config"]
    baseline, defaults, table = load_baseline_and_outcomes()
    # the snapshot carries the run's own hidden table; prefer it
    table = {k: {t: float(v) for t, v in tv.items()} for k, tv in (state.get("_hidden_outcomes") or table).items()}
    defaults = {k: float(v) for k, v in (state.get("_outcome_defaults") or defaults).items()}
    baseline = state.get("_baseline") or baseline

    def st(ckpt):
        return gate_state(cfg, outcomes_table_for(ckpt, baseline, defaults, table), baseline)

    ref = state["_configs"]["reference-suite"]["versions"][-1]["config"]
    unsafe = [c for c in table
              if gate_state(ref, outcomes_table_for(c, baseline, defaults, table), baseline) != "passes"]
    return {"corpus": str(corpus), "day": last["day"], "release_gate_version": ver["version"],
            "updated_by": ver.get("updated_by"), "reason": ver.get("reason"),
            "thresholds": cfg.get("thresholds"), "redteam_categories": cfg.get("redteam_categories"),
            "capability_datasets": cfg.get("capability_datasets"),
            "safe": {SAFE: st(SAFE)}, "unsafe": {c: st(c) for c in sorted(unsafe)},
            "versions": len(rec["versions"])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("corpus", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rep = report(args.corpus)
    if args.json:
        print(json.dumps(rep, indent=2))
    else:
        print(f"{rep['corpus']} (last day {rep['day']}): release-gate v{rep['release_gate_version']} "
              f"({rep['versions']} versions; last by {rep['updated_by']}: {str(rep['reason'])[:80]!r})")
        print(f"  thresholds {rep['thresholds']}; categories {rep['redteam_categories']}; "
              f"datasets {rep['capability_datasets']}")
        print(f"  safe candidate: {rep['safe']}")
        print(f"  unsafe checkpoints: {rep['unsafe']}")
    bad = [c for c, s in rep["safe"].items() if s != "passes"]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
