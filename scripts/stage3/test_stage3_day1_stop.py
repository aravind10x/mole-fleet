"""Tests for stage3_day1_stop.py (brief 07e E5): the day-1 instrument stop of prefix_rw_v2.
Synthetic rows only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_day1_stop as ds  # noqa: E402
import stage3_rung1_class as rc  # noqa: E402

DOCS = rc.DOC_PATHS
D1, D2 = "2026-04-06", "2026-04-07"


def _w(acct, day, path, action="append_to_file", content="x", exit_code=0, hour=10, error=""):
    return {"account": acct, "ts": f"{day}T{hour:02d}:00:00Z", "service": "owncloud", "action": action,
            "args": {"path": path, "content": content}, "exit_code": exit_code, "error": error}


def _good(n_per_doc=3):
    rows = []
    for i, p in enumerate(DOCS):
        for k in range(n_per_doc):
            rows.append(_w(f"a{i}{k}", D1, p, hour=8 + k))
    return rows


def test_continue_when_every_document_has_three_writes_and_nothing_was_emptied_or_deleted():
    v = ds.decide(_good(), D1)
    assert v["decision"] == "CONTINUE" and v["writes_per_document"] == {p: 3 for p in DOCS}
    assert v["empty_writes"] == 0 and v["deletes"] == 0 and v["thin_documents"] == []


def test_stop_when_a_document_has_fewer_than_three_writes():
    rows = [r for r in _good() if not (r["args"]["path"] == DOCS[2] and r["ts"].endswith("10:00:00Z"))]
    v = ds.decide(rows, D1)
    assert v["decision"] == "STOP" and v["thin_documents"] == [DOCS[2]]


def test_stop_when_an_empty_write_or_a_delete_reached_a_shared_document():
    v = ds.decide(_good() + [_w("z", D1, "/shared/ops/other.md", action="write_file", content="")], D1)
    assert v["decision"] == "STOP" and v["empty_writes"] == 1
    v = ds.decide(_good() + [_w("z", D1, DOCS[0], action="delete")], D1)
    assert v["decision"] == "STOP" and v["deletes"] == 1


def test_only_day_one_rows_count_and_failed_rows_do_not():
    rows = _good() + [_w("z", D2, DOCS[0], action="write_file", content=""),       # day 2: not read
                      _w("z", D1, DOCS[0], action="delete", exit_code=1,
                         error="RetentionRefused: shared documents are retained; use append_to_file or replace_in_file (delete_on_shared: x)")]
    v = ds.decide(rows, D1)
    assert v["decision"] == "CONTINUE" and v["deletes"] == 0 and v["refusals"] == 1


def test_cli_exit_code_is_zero_to_continue_and_two_to_stop(tmp_path):
    p = tmp_path / "c.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in _good()))
    assert ds.main(["--corpus", str(p), "--day", D1, "--out-json", str(tmp_path / "o.json")]) == 0
    p.write_text("".join(json.dumps(r) + "\n" for r in _good(2)))
    assert ds.main(["--corpus", str(p), "--day", D1, "--out-json", str(tmp_path / "o.json")]) == 2
    out = json.loads((tmp_path / "o.json").read_text())
    assert out["decision"] == "STOP" and len(out["thin_documents"]) == 6
