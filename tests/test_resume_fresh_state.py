"""--resume must not silently restart the in-process managers from the day-0 base.

Regression: when no managers.json was available (NPC_RESUME_MANAGERS_PATH unset and
no manifest managers_path, or the named file missing), --resume logged a warning and
carried on from a fresh world under an audit-log prefix that had already mutated it.
Now it refuses unless --resume-fresh-state is passed (then: WARNING + manifest flag).
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import pytest

from mole.generator import resume_state
from mole.generator.run import (
    ResumeStateMissingError, resolve_resume_managers_path, simulate,
)

REPO = Path(__file__).resolve().parents[1]


def _manifest(managers_path: str | None, managers_ok: bool = True) -> dict:
    return {"days": [{"day": "2026-04-06", "audit_bytes": 10, "transcript_bytes": 0,
                      "snapshot_ok": False, "managers_ok": managers_ok,
                      "managers_path": managers_path}]}


@pytest.fixture
def audit(tmp_path: Path) -> Path:
    p = tmp_path / "npc.jsonl"
    p.write_text('{"ts": "2026-04-06T09:00:00Z"}\n', encoding="utf-8")
    return p


@pytest.fixture(autouse=True)
def _no_env(monkeypatch):
    monkeypatch.delenv("NPC_RESUME_MANAGERS_PATH", raising=False)


def test_no_snapshot_raises_without_flag(audit):
    with pytest.raises(ResumeStateMissingError) as ei:
        resolve_resume_managers_path(_manifest(None, managers_ok=False), audit)
    msg = str(ei.value)
    assert "managers.json" in msg and "2026-04-06" in msg
    assert "NPC_RESUME_MANAGERS_PATH" in msg and "managers_path" in msg   # the two ways
    assert "--resume-fresh-state" in msg


def test_no_snapshot_with_flag_returns_none_and_warns(audit, caplog):
    with caplog.at_level(logging.WARNING, logger="mole.generator.run"):
        got = resolve_resume_managers_path(_manifest(None, managers_ok=False), audit,
                                           resume_fresh_state=True)
    assert got is None
    assert any(r.levelno == logging.WARNING and "--resume-fresh-state" in r.getMessage()
               for r in caplog.records)


def test_named_but_missing_snapshot_raises_naming_it(audit, tmp_path, monkeypatch):
    gone = tmp_path / "day_2026-04-06" / "managers.json"
    with pytest.raises(ResumeStateMissingError, match="day_2026-04-06/managers.json"):
        resolve_resume_managers_path(_manifest(str(gone)), audit)
    monkeypatch.setenv("NPC_RESUME_MANAGERS_PATH", str(tmp_path / "elsewhere.json"))
    with pytest.raises(ResumeStateMissingError, match="elsewhere.json"):
        resolve_resume_managers_path(_manifest(None, managers_ok=False), audit)
    assert resolve_resume_managers_path(_manifest(str(gone)), audit,
                                        resume_fresh_state=True) is None


def test_existing_snapshot_is_returned_env_wins(audit, tmp_path, monkeypatch):
    rec_path = tmp_path / "rec.json"
    rec_path.write_text("{}", encoding="utf-8")
    assert resolve_resume_managers_path(_manifest(str(rec_path)), audit) == rec_path
    env_path = tmp_path / "env.json"
    env_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("NPC_RESUME_MANAGERS_PATH", str(env_path))
    assert resolve_resume_managers_path(_manifest(str(rec_path)), audit) == env_path


def test_nothing_to_resume_is_not_an_error(tmp_path):
    # No audit prefix -> nothing has mutated the world; the day-0 base is consistent.
    assert resolve_resume_managers_path({"days": []}, tmp_path / "absent.jsonl") is None
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    assert resolve_resume_managers_path({"days": []}, empty) is None


def test_simulate_resume_refuses_then_proceeds_with_flag(tmp_path):
    out = tmp_path / "npc.jsonl"
    kw = dict(n_personas=2, out_path=out, seed=7, start_date="2026-04-06")
    asyncio.run(simulate(n_days=1, **kw))
    rec = resume_state.last_completed_record(resume_state.load(out))
    Path(rec["managers_path"]).unlink()                 # the snapshot is lost

    with pytest.raises(ResumeStateMissingError):
        asyncio.run(simulate(n_days=2, resume=True, **kw))
    assert "resume_fresh_state" not in resume_state.load(out)

    asyncio.run(simulate(n_days=2, resume=True, resume_fresh_state=True, **kw))
    manifest = json.loads(resume_state.manifest_path(out).read_text(encoding="utf-8"))
    assert manifest["resume_fresh_state"] is True
    assert resume_state.last_completed_day(manifest) == "2026-04-07"


def test_sim_runner_threads_resume_fresh_state(monkeypatch, tmp_path):
    for p in (REPO, REPO / "scripts"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import sim_runner
    seen: dict = {}

    async def _fake_simulate(**kw):
        seen.update(kw)

        class _C:
            events: list = []
        return _C()

    monkeypatch.setattr(sim_runner, "simulate", _fake_simulate)
    base = ["--smoke", "--mode", "rules", "--no-docker", "--days", "1",
            "--out", str(tmp_path / "x.jsonl")]
    assert sim_runner.main(base) == 0 and seen["resume_fresh_state"] is False
    assert sim_runner.main(base + ["--resume", "--resume-fresh-state"]) == 0
    assert seen["resume_fresh_state"] is True
