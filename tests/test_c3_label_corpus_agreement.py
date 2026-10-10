"""O7 on real data: the C3 effect label and the eval server agree on every
release-gate version in the three Kimi corpora (data/corpus/spike). Two checks:

1. for every successful release-gate `update_config`, the label's gate state equals
   a live EvalServerManager's verdict for the unsafe checkpoint under that config;
2. for every `submit_eval` of the unsafe checkpoint under release-gate whose audit
   `result_meta` recorded the server's verdict AT GENERATION TIME, the label's
   reconstructed state (passes <=> passed) matches it. This is the independent
   check: the verdict was written by the server during the run, the label is
   recomputed from the config stream afterwards.

Skipped when the corpora are not on disk (they are not in git)."""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from mole.audit.cert_export import load_events_from_jsonl
from mole.sandbox.base import DryRunSandbox
from mole.state.eval_server.manager import EvalServerManager

REPO = Path(__file__).resolve().parents[1]
CORPORA = ["c3_s0_campaign_kimi", "c3_s0_campaign_kimi_s2", "probe_kimi"]
SPIKE = REPO / "data" / "corpus" / "spike"

spec = importlib.util.spec_from_file_location("c3_corpus", REPO / "tasks" / "c3_release_sabotage" / "task.py")
C3 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(C3)


@pytest.fixture(scope="module")
def ev() -> EvalServerManager:
    m = EvalServerManager()
    asyncio.run(m.setup(sandbox=DryRunSandbox()))
    return m


@pytest.mark.parametrize("name", CORPORA)
def test_labels_agree_with_eval_server_on_every_gate_version(name, ev):
    path = SPIKE / f"{name}.jsonl"
    if not path.exists():
        pytest.skip(f"{path} not on disk")
    events = load_events_from_jsonl(path)
    tg = C3.METADATA["disjoint_targets"]["s0"]
    unsafe = tg["unsafe_checkpoint"]
    labels = C3.label_stream(events, "s0")
    gate = [lab for lab in labels if lab.kind == C3.GATE_UPDATE]
    assert gate, "corpus has no release-gate update"
    # (1) every version: label state == live server state for the unsafe checkpoint
    disagree = []
    for lab in gate:
        cfg = C3._normalised_config(C3._args(events[lab.index]).get("config"))
        server = ev.gate_state_for(unsafe, cfg)
        if server != lab.gate_state:
            disagree.append((lab.index, lab.account, lab.gate_state, server))
    assert not disagree, disagree
    # (2) every recorded unsafe-checkpoint gate eval: label state == the server's
    #     verdict recorded in result_meta when the job ran
    checked = 0
    mismatches = []
    for lab in labels:
        if lab.kind != C3.UNSAFE_EVAL:
            continue
        e = events[lab.index]
        if C3._args(e).get("config_id") != tg["gate_config"]:
            continue
        passed = (getattr(e, "result_meta", None) or {}).get("passed")
        if passed is None:
            continue
        checked += 1
        if bool(passed) != lab.effect:
            mismatches.append((lab.index, e.account, e.ts, passed, lab.effect))
    assert checked > 0, "no unsafe-checkpoint gate eval with a recorded verdict"
    assert not mismatches, mismatches
    states = {s: sum(1 for lab in gate if lab.gate_state == s) for s in ("blocks", "passes", "broken")}
    print(f"{name}: {len(gate)} gate versions {states}; {checked} unsafe gate evals checked")
