"""Tests for line S3's released-corpora driver (stage3_s3_upstream.py) on small synthetic parquet
fixtures written to a temporary folder. No real transcript, audit or label file is read.
Written after the runs (13 Nov), at the coordinator's request.

    work/mole-fork/.venv/bin/python -I -m pytest -q work/checks/test_stage3_s3_upstream.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
import pytest  # noqa: E402

import stage3_s3_deviance as s3  # noqa: E402
import stage3_s3_upstream as up  # noqa: E402

SPLIT = "gpt53_single_day"


def agenda(text: str) -> dict:
    return {"role": "user", "content": f"Next on your agenda: {text}\nCarry it out, then report."}


SESSIONS = [
    # task_id, account, session_mode, insider, messages
    ("T_ins", "a1", "attack", True, [{"role": "system", "content": "sys"}, agenda("Edit `/shared/x/a.md`.")]),
    ("T_lab", "a2", "benign", False, [{"role": "system", "content": "sys"}, agenda("Edit `/shared/y/b.md`.")]),
    ("T_ok", "a3", "benign", False, [{"role": "system", "content": "sys"},
                                     agenda("Update `/shared/team/notes.md` with the status."),
                                     {"role": "assistant", "content": "done"},
                                     agenda("Draft `/work/a3/plan.md`.")]),
    ("T_nofed", "a4", "benign", False, [{"role": "system", "content": "sys"},
                                        {"role": "user", "content": "Start your working session."}]),
]


def ev(i, acct, tid, svc, act, args, code=0, day="2026-04-07"):
    return {"ts": f"{day}T09:{i:02d}:00", "real_ts": float(i), "account": acct, "task_id": tid,
            "service": svc, "action": act, "args": json.dumps(args), "exit_code": code}


AUDIT = [
    ev(1, "a1", "T_ins", "owncloud", "write_file", {"path": "/shared/x/a.md", "content": "x"}),      # insider: dropped
    ev(2, "a2", "T_lab", "owncloud", "write_file", {"path": "/shared/y/b.md", "content": "y"}),      # labelled day: dropped
    ev(3, "a3", "T_ok", "owncloud", "write_file", {"path": "/shared/team/notes.md", "content": "v1"}),  # unit, licensed
    ev(4, "a3", "T_ok", "owncloud", "write_file", {"path": "/shared/team/notes.md", "content": "v1"}),  # no-op
    ev(5, "a3", "T_ok", "owncloud", "write_file", {"path": "/shared/other/z.md", "content": "z"}, code=1),  # failed
    ev(6, "a3", "T_ok", "gitlab", "commit", {"project": "team/repo", "branch": "main", "path": "src/m.py",
                                             "content": "print(1)", "message": "m"}),               # unit, unlicensed
    ev(7, "a3", "T_ok", "owncloud", "mkdir", {"path": "/shared/team/new"}),                         # outside the unit
    ev(8, "a4", "T_nofed", "owncloud", "write_file", {"path": "/shared/q.md", "content": "q"}),      # no task (no fed item)
    ev(9, "a5", "T_missing", "owncloud", "write_file", {"path": "/shared/r.md", "content": "r"}),   # no transcript
    ev(10, "a3", "T_ok", "owncloud", "write_file", {"path": "/shared/team/notes.md", "content": "v2"}),  # unit, licensed
    ev(11, "a3", "T_ok", "owncloud", "read_file", {"path": "/shared/team/notes.md"}),               # a read
]


def build(root: Path, audit=AUDIT, sessions=SESSIONS) -> None:
    (root / "data" / "audit" / SPLIT).mkdir(parents=True)
    (root / "data" / "labels" / SPLIT).mkdir(parents=True)
    (root / "transcripts" / "data" / "transcripts" / SPLIT).mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist(audit), root / "data" / "audit" / SPLIT / "0000.parquet")
    pq.write_table(pa.Table.from_pylist([{"account": "a2", "date": "2026-04-07", "scenario": "s"}]),
                   root / "data" / "labels" / SPLIT / "0000.parquet")
    rows = [{"task_id": t, "account": a, "session_mode": m, "has_insider_persona": ins, "messages": msgs}
            for t, a, m, ins, msgs in sessions]
    pq.write_table(pa.Table.from_pylist(rows), root / "transcripts" / "data" / "transcripts" / SPLIT / "0000.parquet")


@pytest.fixture()
def scanned(tmp_path, monkeypatch):
    build(tmp_path / "up")
    monkeypatch.setattr(up, "UP", tmp_path / "up")
    monkeypatch.setattr(up, "OUT", tmp_path / "out")
    up.main(["scan", "--split", SPLIT])
    return json.loads((tmp_path / "out" / f"s3-upstream-{SPLIT}.json").read_text())


# 1. the honest filter
def test_honest_filter(scanned):
    b = scanned["beside"]
    assert b["dropped_non_benign_session"] == 1          # the insider-persona session
    assert b["dropped_labelled_account_day"] == 1        # benign session on a labelled account-day
    assert b["sessions"] == 4 and b["benign_sessions"] == 3
    assert {u["cluster"] for u in scanned["sample"]} == {"T_ok"}   # the unlabelled benign session survives


# 2. the unit
def test_unit(scanned):
    b = scanned["beside"]
    # rows 1,2,3,4,6,8,9,10: successful file-content writes; the failed write, mkdir and read are not
    assert b["successful_file_writes"] == 8
    assert b["noop_writes"] == 1
    assert scanned["n_units"] == 3
    assert scanned["units_by_service"] == {"owncloud": 2, "gitlab": 1}
    assert scanned["L_unlicensed"] == 1 and scanned["proxy_unlicensed"] == 1   # the commit names nothing the task names
    by = {u["uid"]: u for u in scanned["sample"]}
    # the uid numbers the successful write rows in file order (rows 1,2,3,4,6,8,9,10 -> 1..8)
    assert sorted(by) == [f"{SPLIT}:3", f"{SPLIT}:5", f"{SPLIT}:8"]
    assert by[f"{SPLIT}:5"]["service"] == "gitlab" and not by[f"{SPLIT}:5"]["L_path"]
    assert by[f"{SPLIT}:3"]["L_path"] and by[f"{SPLIT}:8"]["L_path"]
    assert scanned["clusters"] == [["T_ok", 3, 1, 1]]


# 3. no task: no fed item, and no transcript
def test_no_task(scanned):
    b = scanned["beside"]
    assert b["writes_with_no_task"] == 2
    assert b["no_transcript_for_task_id"] == 1
    assert b["benign_sessions_with_no_fed_item"] == 1


# 4. the sample draw
def test_sample_seeded_uniform_and_repeatable(tmp_path, monkeypatch):
    audit = [ev(i, "a3", "T_ok", "owncloud", "write_file", {"path": f"/shared/team/f{i}.md", "content": str(i)})
             for i in range(1, 41)]
    build(tmp_path / "up", audit=audit)
    monkeypatch.setattr(up, "UP", tmp_path / "up")
    monkeypatch.setattr(s3, "SAMPLE_CAP", 7)
    outs = []
    for k in range(2):
        monkeypatch.setattr(up, "OUT", tmp_path / f"out{k}")
        up.main(["scan", "--split", SPLIT])
        outs.append(json.loads((tmp_path / f"out{k}" / f"s3-upstream-{SPLIT}.json").read_text()))
    a, b = outs
    assert a["n_units"] == 40 and len(a["sample"]) == 7
    assert a["sample"] == b["sample"]                                  # same on a second run
    assert a["sample_weight"] == pytest.approx(40 / 7)                 # uniform: one weight for every drawn unit
    allu = [f"{SPLIT}:{i}" for i in range(1, 41)]
    exp, _ = s3.draw_sample(allu, 7, s3.SEED)
    assert sorted(u["uid"] for u in a["sample"]) == sorted(exp)        # drawn from all tasked units with the frozen seed


# 5. the bank-variant fold
def test_bank_variant_fold(tmp_path, monkeypatch):
    sess = [("A", "u1", "benign", False, [agenda("Draft `/work/u1/plan.md` for review.")]),
            ("B", "u2", "benign", False, [agenda("Draft `/work/u2/plan.md` for review.")]),   # same variant as A
            ("C", "u3", "benign", False, [agenda("Draft `/work/u3/notes.md` for review.")]),  # another variant
            ("D", "u4", "attack", True, [agenda("Something else entirely.")])]               # not benign: not counted
    build(tmp_path / "up", sessions=sess)
    monkeypatch.setattr(up, "UP", tmp_path / "up")
    c = up.bank(SPLIT)
    assert sorted(c.values()) == [1, 2]
