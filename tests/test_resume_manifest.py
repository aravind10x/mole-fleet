"""Session-completion fields in the day-boundary resume manifest.

A day can export a valid managers.json while its sessions died mid-day (the LLM
provider returned 402 and the sessions were written with aborted_reason
"llm_error: ..."). These tests cover the per-day session counts, the derived
`sessions_ok`, the --resume warning for a kept unclean day, and the read-only
`python -m mole.generator.resume_state` table. No LLM, no Docker, no network.
"""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path

import pytest

from mole.generator import resume_state as rs
from mole.generator.run import simulate

REPO_ROOT = Path(__file__).resolve().parents[1]
COUNT_KEYS = ("sessions_planned", "sessions_completed", "sessions_aborted",
              "attack_sessions_planned", "attack_sessions_completed")


def _manifest(tmp_path):
    audit = tmp_path / "sim.jsonl"
    audit.write_text("e1\n", encoding="utf-8")
    m = rs.new_manifest(audit_path=audit, transcript_path=tmp_path / "sim.transcripts.jsonl",
                        start_date="2026-04-06", n_days=3, seed=0, session_id="s")
    return audit, m


def _record(m, audit, day="2026-04-06", **counts):
    rs.record_day(m, audit, day=day, audit_bytes=1, transcript_bytes=0,
                  snapshot_ok=False, managers_ok=True,
                  managers_path="/x/managers.json", **counts)
    return next(d for d in rs.load(audit)["days"] if d["day"] == day)


# ---------------------------------------------------------------- record_day

def test_record_day_without_counts_is_backward_compatible(tmp_path):
    audit, m = _manifest(tmp_path)
    rec = _record(m, audit)
    assert rec["managers_ok"] is True
    assert all(rec[k] is None for k in COUNT_KEYS)
    assert rec["sessions_ok"] is None
    assert rs.day_is_clean(rec) is None
    # Selection is unchanged by the new fields.
    assert rs.last_completed_record(rs.load(audit))["day"] == "2026-04-06"


def test_sessions_ok_true_when_all_complete(tmp_path):
    audit, m = _manifest(tmp_path)
    rec = _record(m, audit, sessions_planned=5, sessions_completed=5, sessions_aborted=0,
                  attack_sessions_planned=1, attack_sessions_completed=1)
    assert [rec[k] for k in COUNT_KEYS] == [5, 5, 0, 1, 1]
    assert rec["sessions_ok"] is True
    assert rs.day_is_clean(rec) is True


def test_sessions_ok_false_when_attack_session_missing(tmp_path):
    audit, m = _manifest(tmp_path)
    rec = _record(m, audit, sessions_planned=5, sessions_completed=5, sessions_aborted=0,
                  attack_sessions_planned=1, attack_sessions_completed=0)
    assert rec["sessions_ok"] is False
    assert rs.day_is_clean(rec) is False


def test_sessions_ok_false_when_non_max_turns_abort(tmp_path):
    audit, m = _manifest(tmp_path)
    rec = _record(m, audit, sessions_planned=5, sessions_completed=4, sessions_aborted=1,
                  attack_sessions_planned=0, attack_sessions_completed=0)
    assert rec["sessions_ok"] is False


def test_sessions_ok_none_when_counts_partial(tmp_path):
    audit, m = _manifest(tmp_path)
    rec = _record(m, audit, sessions_planned=5, sessions_completed=5)
    assert rec["sessions_ok"] is None


def test_record_day_idempotent_on_day_with_counts(tmp_path):
    audit, m = _manifest(tmp_path)
    _record(m, audit, sessions_planned=3, sessions_completed=1, sessions_aborted=2,
            attack_sessions_planned=1, attack_sessions_completed=0)
    rec = _record(m, audit, sessions_planned=3, sessions_completed=3, sessions_aborted=0,
                  attack_sessions_planned=1, attack_sessions_completed=1)
    days = rs.load(audit)["days"]
    assert len(days) == 1
    assert rec["sessions_ok"] is True and rec["sessions_aborted"] == 0


def test_day_is_clean_handles_legacy_records():
    assert rs.day_is_clean(None) is None
    assert rs.day_is_clean({"day": "2026-04-06", "managers_ok": True}) is None


# ---------------------------------------------------------------- tally

def _tline(day, mode="benign", aborted=None, **extra):
    return json.dumps({"sim_ts": f"{day}T10:00:00Z", "session_mode": mode,
                       "aborted_reason": aborted, "turn_count": 3, **extra}) + "\n"


def test_tally_day_sessions_classifies_aborts(tmp_path):
    t = tmp_path / "t.jsonl"
    prior = _tline("2026-04-03")                       # an earlier day (branch prefix)
    body = (_tline("2026-04-06")
            + _tline("2026-04-06", aborted="max_turns")              # completed
            + _tline("2026-04-06", mode="attack",
                     aborted="llm_error: APIStatusError: 402")       # aborted attack
            + _tline("2026-04-06", aborted="llm_error: boom")        # aborted benign
            + "{torn line\n")
    t.write_text(prior + body, encoding="utf-8")
    c = rs.tally_day_sessions(t, day="2026-04-06", sessions_planned=5,
                              start_byte=0, end_byte=t.stat().st_size)
    # 2 completed, 2 aborted records + 1 planned session with no record.
    assert c == {"sessions_planned": 5, "sessions_completed": 2, "sessions_aborted": 3,
                 "attack_sessions_planned": 1, "attack_sessions_completed": 0}
    # The byte window bounds the scan.
    c2 = rs.tally_day_sessions(t, day="2026-04-06", sessions_planned=1,
                               start_byte=len(prior.encode()),
                               end_byte=len(prior.encode()) + len(_tline("2026-04-06")))
    assert c2["sessions_completed"] == 1 and c2["sessions_aborted"] == 0


# ---------------------------------------------------------------- runner smoke

class _OneToolThenStop:
    """Calls one in-process tool on its first turn, then stops. With `fail_marker`,
    raises (like a provider HTTP 402) on any call whose prompt contains it."""
    backend = "fake"
    model_id = "fake"

    def __init__(self, fail_marker: str | None = None):
        self.calls = 0
        self.fail_marker = fail_marker

    async def complete(self, messages, *, tools=None, temperature=0.0, max_tokens=None,
                       seed=None):
        from mole.llm.base import ChatResponse, ToolCall
        if self.fail_marker and any(self.fail_marker in str(getattr(m, "content", "") or "")
                                    for m in messages):
            raise RuntimeError("HTTP 402: insufficient credit")
        self.calls += 1
        if self.calls % 2 == 1:
            return ChatResponse(content="", tool_calls=[ToolCall(
                id=f"c{self.calls}", name="model_registry.list_checkpoints", arguments={})])
        return ChatResponse(content="done", tool_calls=[])


def _agentic_kw(out, **kw):
    base = dict(mode="agentic", sandbox_mode="dryrun", n_personas=2, out_path=out, seed=0,
                sessions_per_day=2, max_turns=4, absent_probability=0.0)
    base.update(kw)
    return base


@pytest.fixture
def clean_run(tmp_path):
    out = tmp_path / "clean.jsonl"
    asyncio.run(simulate(llm=_OneToolThenStop(), n_days=2, **_agentic_kw(out)))
    return out


def test_dryrun_multiday_manifest_records_session_counts(clean_run):
    days = rs.load(clean_run)["days"]
    assert len(days) == 2
    for d in days:
        assert all(isinstance(d[k], int) for k in COUNT_KEYS), d
        assert d["sessions_planned"] >= 1
        assert d["sessions_completed"] == d["sessions_planned"]
        assert d["sessions_aborted"] == 0
        assert d["sessions_ok"] is True


def test_rules_mode_records_unknown_counts(tmp_path):
    out = tmp_path / "rules.jsonl"
    asyncio.run(simulate(mode="rules", sandbox_mode="dryrun", n_personas=3, n_days=1,
                         out_path=out, seed=0, sessions_per_day=2))
    [d] = rs.load(out)["days"]
    assert d["sessions_ok"] is None and d["sessions_planned"] is None


def test_aborted_attack_session_marks_day_unclean_and_resume_warns(tmp_path, caplog):
    from mole.generator.persona_loader import load_personas
    insider = load_personas()[0].id
    marker = "ZZ_INSIDER_MARKER_ZZ"
    out = tmp_path / "abort.jsonl"
    kw = _agentic_kw(out, insider_persona_map={insider: f"{marker} You are disgruntled."},
                     planning="coinflip", attack_session_rate=1.0)
    asyncio.run(simulate(llm=_OneToolThenStop(fail_marker=marker), n_days=1, **kw))
    [d] = rs.load(out)["days"]
    assert d["managers_ok"] is True                  # world boundary still "fine"
    assert d["attack_sessions_planned"] >= 1
    assert d["attack_sessions_completed"] == 0
    assert d["sessions_aborted"] == d["attack_sessions_planned"]
    assert d["sessions_ok"] is False

    caplog.set_level(logging.WARNING, logger="mole.generator.run")
    asyncio.run(simulate(llm=_OneToolThenStop(), n_days=2, resume=True, **kw))
    warns = [r.getMessage() for r in caplog.records
             if r.levelno == logging.WARNING and "sessions_ok=False" in r.getMessage()]
    assert warns and d["day"] in warns[0]
    # Surfaced only: the unclean day is kept, and resume ran the next day.
    days = rs.load(out)["days"]
    assert [x["day"] for x in days][0] == d["day"] and len(days) == 2


# ---------------------------------------------------------------- CLI

def test_cli_prints_day_table(clean_run):
    proc = subprocess.run([sys.executable, "-m", "mole.generator.resume_state", str(clean_run)],
                          capture_output=True, text=True, cwd=REPO_ROOT, check=True)
    lines = proc.stdout.strip().splitlines()
    assert lines[0].split() == ["day", "audit_bytes", "managers_ok", "planned", "completed",
                                "aborted", "atk_planned", "atk_completed", "sessions_ok"]
    days = rs.load(clean_run)["days"]
    assert len(lines) == 1 + len(days)
    for line, d in zip(lines[1:], days):
        cols = line.split()
        assert cols[0] == d["day"] and cols[1] == str(d["audit_bytes"])
        assert cols[3] == str(d["sessions_planned"]) and cols[-1] == "True"


def test_cli_missing_manifest(tmp_path):
    assert rs.main([str(tmp_path / "nope.jsonl")]) == 1
    assert rs.main([]) == 2
