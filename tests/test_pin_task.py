"""--pin-task: force a task-bank task onto one account-day (no LLM, dryrun world)."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

from mole.generator import resume_state
from mole.generator.agentic_member import load_task_bank, load_task_bank_ids
from mole.generator.run import parse_pin_task, simulate
from mole.llm.base import ChatResponse

REPO = Path(__file__).resolve().parents[1]
APPROVER_TASK = "legal/14"


class _Capture:
    backend = "fake"
    model_id = "fake"

    def __init__(self):
        self.sessions: list[str] = []      # system prompt per session

    async def complete(self, messages, *, tools=None, temperature=0.0, max_tokens=None,
                       seed=None):
        if len(messages) == 2:
            self.sessions.append(messages[0].content)
        return ChatResponse(content="done", tool_calls=[])


def test_task_ids_follow_the_bank_order_and_name_the_approver_task():
    ids = load_task_bank_ids(bank="inprocess")
    by_team = load_task_bank(bank="inprocess")
    assert [t for i, t in ids.items() if i.startswith("legal/")] == by_team["legal"]
    assert len(by_team["legal"]) == 16
    assert "model_registry.tag_approved" in ids[APPROVER_TASK]
    assert "model_registry.deploy" in ids[APPROVER_TASK]


def test_parse_pin_task():
    assert parse_pin_task("paul.s20:1:legal/14") == ("paul.s20", 1, "legal/14")
    assert parse_pin_task("paul.s20:-1:legal/14") == ("paul.s20", -1, "legal/14")
    for bad in ("paul.s20:legal/14", "paul.s20:x:legal/14", "::", "paul.s20:1:"):
        with pytest.raises(ValueError):
            parse_pin_task(bad)


def _run(tmp_path, pins, personas=("paul.s20", "omar.s34", "hannah.m"), n_days=2):
    llm = _Capture()
    out = tmp_path / "pin.jsonl"
    asyncio.run(simulate(mode="agentic", sandbox_mode="dryrun", llm=llm,
                         n_personas=len(personas), allowed_persona_ids=set(personas),
                         n_days=n_days, out_path=out, seed=0, sessions_per_day=3,
                         max_turns=2, attack_session_rate=0.0, pinned_tasks=pins))
    transcripts = [json.loads(line) for line in
                   out.with_suffix(".transcripts.jsonl").read_text().splitlines() if line]
    return llm, transcripts, resume_state.load(out)


def test_pin_lands_on_first_session_of_that_account_day_only(tmp_path):
    task = load_task_bank_ids(bank="inprocess")[APPROVER_TASK]
    llm, transcripts, manifest = _run(tmp_path, [("paul.s20", -1, APPROVER_TASK)])
    assert len(llm.sessions) == len(transcripts)
    hits = [t for t, s in zip(transcripts, llm.sessions) if task in s]
    assert len(hits) == 1
    [hit] = hits
    assert hit["account"] == "paul.s20" and hit["sim_ts"].startswith("2026-04-07")
    assert hit["pinned_task_id"] == APPROVER_TASK
    first_day2 = min((t for t in transcripts
                      if t["account"] == "paul.s20" and t["sim_ts"].startswith("2026-04-07")),
                     key=lambda t: t["sim_ts"])
    assert first_day2["task_id"] == hit["task_id"]
    assert sum(1 for t in transcripts if "pinned_task_id" in t) == 1
    assert manifest["pinned_tasks"] == [{"account": "paul.s20", "day_index": -1,
                                         "date": "2026-04-07", "task_id": APPROVER_TASK}]


def test_pins_do_not_change_other_accounts(tmp_path):
    base_llm, base_t, _ = _run(tmp_path / "a", None)
    pin_llm, pin_t, _ = _run(tmp_path / "b", [("paul.s20", 0, APPROVER_TASK)])
    for who in ("omar.s34", "hannah.m"):
        a = [(t["sim_ts"], s) for t, s in zip(base_t, base_llm.sessions) if t["account"] == who]
        b = [(t["sim_ts"], s) for t, s in zip(pin_t, pin_llm.sessions) if t["account"] == who]
        assert a == b, who


@pytest.mark.parametrize("pin, match", [
    (("nobody.x", 0, APPROVER_TASK), "cohort"),
    (("paul.s20", 2, APPROVER_TASK), "window"),
    (("paul.s20", -3, APPROVER_TASK), "window"),
    (("paul.s20", 0, "legal/99"), "unknown task id"),
])
def test_bad_pins_are_refused_before_the_run(tmp_path, pin, match):
    with pytest.raises(ValueError, match=match):
        _run(tmp_path, [pin])


def test_pins_need_agentic_mode(tmp_path):
    with pytest.raises(ValueError, match="agentic"):
        asyncio.run(simulate(mode="rules", sandbox_mode="dryrun", n_personas=3, n_days=1,
                             out_path=tmp_path / "r.jsonl",
                             pinned_tasks=[("paul.s20", 0, APPROVER_TASK)]))


def test_sim_runner_parses_repeatable_pin_task(monkeypatch, tmp_path, capsys):
    for p in (REPO, REPO / "scripts"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import sim_runner
    seen: dict = {}

    async def _fake_simulate(**kw):
        seen.clear()
        seen.update(kw)

        class _C:
            events: list = []
        return _C()

    monkeypatch.setattr(sim_runner, "simulate", _fake_simulate)
    base = ["--smoke", "--no-docker", "--days", "2", "--out", str(tmp_path / "x.jsonl")]
    assert sim_runner.main([*base, "--pin-task", "paul.s20:-1:legal/14",
                            "--pin-task", "omar.s34:0:legal/15"]) == 0
    assert seen["pinned_tasks"] == [("paul.s20", -1, "legal/14"), ("omar.s34", 0, "legal/15")]
    assert sim_runner.main(base) == 0
    assert seen["pinned_tasks"] is None
    with pytest.raises(SystemExit):
        sim_runner.main([*base, "--pin-task", "paul.s20:legal/14"])
