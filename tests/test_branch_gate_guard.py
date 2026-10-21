"""Threshold-ratchet guard: a branch refuses to start from a parent whose final
release-gate blocks the safe release candidate (unless allow_blocked_gate), and the
agentic manifest fingerprints the task bank it drew from."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import pytest

from mole.generator import resume_state
from mole.generator.run import simulate
from mole.llm.base import ChatResponse

SIM = dict(mode="rules", sandbox_mode="dryrun", n_personas=4, sessions_per_day=1, seed=0)


def _parent(tmp_path: Path, cap: float | None = None) -> Path:
    parent = tmp_path / "parent" / "warmup.jsonl"
    asyncio.run(simulate(out_path=parent, n_days=1, **SIM))
    if cap is not None:
        man = resume_state.load(parent)
        mp = Path(man["days"][-1]["managers_path"])
        state = json.loads(mp.read_text())
        versions = state["eval_server"]["_configs"]["release-gate"]["versions"]
        cfg = dict(versions[-1]["config"])
        cfg["thresholds"] = {**cfg["thresholds"], "cap_score_min": cap}
        versions.append({**versions[-1], "version": versions[-1]["version"] + 1, "config": cfg,
                         "updated_by": "ben.k39", "reason": "LLAMAF20-15: raise cap_score_min"})
        mp.write_text(json.dumps(state))
    return parent


def test_branch_refused_when_parent_gate_blocks_the_safe_candidate(tmp_path, caplog):
    parent = _parent(tmp_path, cap=0.75)          # every checkpoint scores 0.72
    out = tmp_path / "branch" / "b.jsonl"
    with pytest.raises(ValueError) as ei:
        asyncio.run(simulate(out_path=out, n_days=1, branch_from=parent, **SIM))
    msg = str(ei.value)
    assert "does not pass the safe release candidate ['ckpt-archetype-v1.1-rc1']" in msg
    assert "cap_score_min': 0.75" in msg and "--allow-blocked-gate" in msg
    # the override lets it through
    coll = asyncio.run(simulate(out_path=tmp_path / "forced" / "f.jsonl", n_days=1,
                                branch_from=parent, allow_blocked_gate=True, **SIM))
    assert coll is not None


def test_branch_from_a_passing_gate_is_allowed(tmp_path):
    parent = _parent(tmp_path)
    out = tmp_path / "branch" / "b.jsonl"
    asyncio.run(simulate(out_path=out, n_days=1, branch_from=parent, **SIM))
    assert resume_state.load(out)["branch_from"]["parent"] == str(parent)


class _Done:
    backend = model_id = "fake"

    async def complete(self, messages, *, tools=None, temperature=0.0, max_tokens=None, seed=None):
        return ChatResponse(content="done", tool_calls=[])


def test_agentic_manifest_fingerprints_the_task_bank(tmp_path):
    out = tmp_path / "ag.jsonl"
    asyncio.run(simulate(mode="agentic", sandbox_mode="dryrun", llm=_Done(), n_personas=2,
                         n_days=1, out_path=out, seed=0, sessions_per_day=1, max_turns=2,
                         attack_session_rate=0.0))
    man = resume_state.load(out)
    tb = man["task_bank"]
    bank = Path(tb["path"])
    assert bank.name == "benign_task_bank_inprocess.yaml"
    assert tb["sha256"] == hashlib.sha256(bank.read_bytes()).hexdigest()
    assert tb["tasks_per_team"]["evaluations"] == 15 and tb["tasks_per_team"]["legal"] == 16


def test_task_bank_record_is_persisted_before_the_first_day_record(tmp_path, monkeypatch):
    """Brief 07d (coordinator check of prefix_rw_v1, 2026-10-21): the manifest set task_bank
    in memory but did not persist it until the first day boundary, so a start-time manifest
    read `task_bank: None` for a run launched with --task-bank (L1 rule 2: the manifest is
    the evidence). The record must reach the disk before any day record does."""
    import copy
    writes: list[dict] = []
    real = resume_state.write_atomic

    def spy(manifest, out_path):
        writes.append(copy.deepcopy(manifest))
        return real(manifest, out_path)
    monkeypatch.setattr(resume_state, "write_atomic", spy)
    out = tmp_path / "ag2.jsonl"
    asyncio.run(simulate(mode="agentic", sandbox_mode="dryrun", llm=_Done(), n_personas=2,
                         n_days=1, out_path=out, seed=0, sessions_per_day=1, max_turns=2,
                         attack_session_rate=0.0))
    first_with_bank = next((w for w in writes if w.get("task_bank")), None)
    assert first_with_bank is not None
    assert not first_with_bank.get("days"), "task_bank must be on disk before the first day record"
