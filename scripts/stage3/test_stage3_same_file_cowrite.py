"""Tests for stage3_same_file_cowrite.py (brief 07, task S3) on synthetic frames only."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import stage3_same_file_cowrite as sf


def test_file_key_gitlab_and_owncloud():
    assert sf.file_key("gitlab", {"project": "infra/x", "path": "README.md"}) == "infra/x:README.md"
    # the same path in two projects is two documents
    assert sf.file_key("gitlab", {"project": "infra/y", "path": "README.md"}) != sf.file_key(
        "gitlab", {"project": "infra/x", "path": "README.md"})
    assert sf.file_key("gitlab", {"path": "README.md"}) is None
    assert sf.file_key("owncloud", {"path": " /shared/a.md "}) == "/shared/a.md"
    assert sf.file_key("owncloud", {"path": ""}) is None
    assert sf.parse_args('{"path": "/a"}') == {"path": "/a"} and sf.parse_args("not json") == {}


def _frame(rows):
    return pd.DataFrame(rows, columns=["day", "account", "file"])


def test_day_stats_two_files_three_accounts():
    # day 1: a and b write file F (a twice), c writes G; d is active but writes nothing.
    w = _frame([("d1", "a", "F"), ("d1", "a", "F"), ("d1", "b", "F"), ("d1", "c", "G")])
    r = _frame([("d1", "c", "F"), ("d1", "d", "F"), ("d1", "a", "G")])
    active = {"d1": {"a", "b", "c", "d"}}
    (row,) = sf.day_stats(w, r, active)
    assert row["max_writers_one_file"] == 2 and row["max_writer_share"] == 0.5
    assert row["writes_on_hottest_file"] == 3            # F: a twice + b
    assert row["files_with_2plus_writers"] == 1
    assert row["writer_account_days"] == 3 and row["writer_ad_with_cowriter"] == 2   # a, b yes; c no
    assert row["max_reader_share"] == 0.5
    # caps at N = 4: B 0.05 -> 1, B 0.10 -> 1; two writers exceed both
    assert row["hottest_exceeds_cap_B0.05"] and row["hottest_exceeds_cap_B0.10"]
    s = sf.summarise([row])
    assert abs(s["cowrite_share"] - 2 / 3) < 1e-12 and s["median_writes_on_hottest_file"] == 3


def test_cap_flag_false_when_hottest_fits():
    w = _frame([("d1", "a", "F"), ("d1", "b", "F")])
    active = {"d1": {f"u{i}" for i in range(40)} | {"a", "b"}}      # N = 42: cap B0.05 = 2, B0.10 = 4
    (row,) = sf.day_stats(w, _frame([]), active)
    assert not row["hottest_exceeds_cap_B0.05"] and not row["hottest_exceeds_cap_B0.10"]
    assert row["max_reader_share"] == 0.0


def test_analyse_corpus_honest_filter_and_types(tmp_path):
    corpus = "gpt53_single_day"
    (tmp_path / "data" / "audit" / corpus).mkdir(parents=True)
    (tmp_path / "data" / "labels" / corpus).mkdir(parents=True)
    ev = []
    def e(acc, svc, act, args, ec=0, ts="2026-04-06T09:00:00Z"):
        ev.append({"ts": ts, "real_ts": 0.0, "account": acc, "service": svc, "action": act,
                   "args": json.dumps(args), "exit_code": ec})
    # honest a, b co-write owncloud /s/F; honest c writes gitlab infra/x README; labelled z also writes /s/F
    e("a", "owncloud", "write_file", {"path": "/s/F", "content": "x"})
    e("b", "owncloud", "write_file", {"path": "/s/F", "content": "y"})
    e("z", "owncloud", "write_file", {"path": "/s/F", "content": "z"})
    e("c", "gitlab", "commit", {"project": "infra/x", "path": "README.md", "content": "c"})
    e("c", "gitlab", "commit", {"project": "infra/x", "path": "README.md"}, ec=1)        # failed: ignored
    e("a", "gitlab", "read_file", {"project": "infra/x", "path": "README.md"})
    e("b", "plane", "get_issue", {"issue_id": "X-1"})
    pd.DataFrame(ev).to_parquet(tmp_path / "data" / "audit" / corpus / "0000.parquet")
    pd.DataFrame([{"account": "z", "date": "2026-04-06", "scenario": "s", "outcome": "executed",
                   "confidence": 1.0, "judge": "j"}]).to_parquet(tmp_path / "data" / "labels" / corpus / "0000.parquet")
    out = sf.analyse_corpus(tmp_path, corpus)
    assert out["labelled_accounts"] == 1 and out["honest_active_account_days"] == 3   # a, b, c (z excluded)
    oc, cm, pooled = (out["by_type"][t] for t in ("owncloud", "commit", "pooled"))
    assert oc["median_daily_max_writers_one_file"] == 2 and abs(oc["median_daily_max_writer_share"] - 2 / 3) < 1e-12
    assert oc["cowrite_share"] == 1.0 and oc["median_writes_on_hottest_file"] == 2   # z's write not counted
    assert cm["median_daily_max_writers_one_file"] == 1 and cm["cowrite_share"] == 0.0
    assert cm["median_writes_on_hottest_file"] == 1                                   # the failed commit is ignored
    assert abs(cm["median_daily_max_reader_share"] - 1 / 3) < 1e-12
    assert pooled["median_files_with_2plus_writers"] == 1
    assert out["doc_events"] == {"commit.write": 1, "commit.read": 1, "owncloud.write": 2, "owncloud.read": 0}


def test_edit_tool_rows_are_owncloud_writes_in_the_scope():
    """Brief 07e E1: the amended like-for-like scope sees append_to_file / replace_in_file as
    ownCloud writes by path, beside write_file."""
    import stage3_same_file_cowrite as sf
    for action in ("write_file", "append_to_file", "replace_in_file"):
        assert sf.DOC_ACTIONS[("owncloud", action)] == ("owncloud", "write")
    assert sf.file_key("owncloud", {"path": "/shared/x.md"}) == "/shared/x.md"
