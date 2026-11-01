"""Tests for stage3_b3_lone_line_check_s3.py (brief 33 A3 (ii)): S3's copy of brief 27's harness keeps every function it
does not name byte-identical to the pinned original (070212f7), writes under its own directory (never brief 27's parts or
record), reads S2's table only under the opt-in, selects lone-line tasks by regime, and splits the control items' counts
net of the pair-rule drops. The gated slow test (S3_SLOW=1) re-runs the default `lines` mode and compares it with brief
27's part: the candidates' 4,537 of 4,537 listed draws accepted.

Run: cd work/checks && ../mole-fork/.venv/bin/python -I -m pytest -q test_stage3_b3_lone_line_check_s3.py
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sys
from collections import Counter
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_b3_lone_line_check as orig  # noqa: E402
import stage3_b3_lone_line_check_s3 as s3  # noqa: E402

ORIG_SHA256 = "070212f7dfb417d808b242df4aa7900ed11a6be27cb0042609291d37332f03f6"
UNCHANGED = ("sha256_bytes", "sha256_json", "class_sha256", "_rng", "check_parts", "pre_change_source", "load_module",
             "_replay_one", "replay", "module_diff", "_set", "compare_dryrun", "dryrun", "_init", "_payload", "_apply_listed",
             "_check_unlisted", "_drawable", "_line_task", "_item_task", "items_check", "_guard", "write_part")


def test_the_original_is_the_pinned_harness():
    assert hashlib.sha256((HERE / "stage3_b3_lone_line_check.py").read_bytes()).hexdigest() == ORIG_SHA256


@pytest.mark.parametrize("name", UNCHANGED)
def test_unnamed_functions_are_byte_identical_to_the_original(name):
    assert inspect.getsource(getattr(s3, name)) == inspect.getsource(getattr(orig, name))


def test_the_copy_writes_under_its_own_directory_and_record():
    assert s3.PARTS != orig.PARTS and s3.OUT != orig.OUT
    assert s3.PARTS.name == "s3-lone-line-check" and s3.OUT.name == "s3-lone-line-check-v0.json"
    assert orig.PARTS.name == "lone-line-arm" and orig.OUT.name == "lone-line-arm-v0.json"


def test_default_mode_reads_brief_26s_file_and_the_opt_in_reads_s2s_table():
    assert s3._VALID_PATH == s3.B26_JSON == orig.B26_JSON
    assert s3.VALID == {"v0": s3.B26_JSON, "v1": s3.V1_JSON}
    assert s3.V1_JSON.name == "inserter-dry-run-v1.json" and s3.V1_JSON_SHA256 == "02138931"
    assert s3.RUN_SEED == orig.RUN_SEED and s3.RUNS_PER_DRAW == orig.RUNS_PER_DRAW


def test_lines_selects_tasks_by_regime_and_splits_the_counts_net_of_drops(monkeypatch, tmp_path):
    d1, d2 = "2026-04-06", "2026-04-07"
    items = [{"item_id": "c1", "regime": "candidate", "document": "/d", "statements": [{}] * 3},
             {"item_id": "k1", "regime": "control", "document": "/d", "statements": [{}] * 3},
             {"item_id": "k2", "regime": "control", "document": "/d", "statements": [{}] * 3}]
    table = {"items": [{"item_id": "c1", "regime": "candidate", "drop": False,
                        "lone_lines": [{"valid_draws": [[d1, "a"], [d2, "b"]], "pair_ok_distinct_authors": True, "literal_ok": True, "n_drawable": 2}] * 3},
                       {"item_id": "k1", "regime": "control", "drop": False,
                        "lone_lines": [{"valid_draws": [[d1, "a"], [d2, "b"]], "pair_ok_distinct_authors": True, "literal_ok": True, "n_drawable": 2}] * 3},
                       {"item_id": "k2", "regime": "control", "drop": True,
                        "lone_lines": [{"valid_draws": [[d1, "a"]], "pair_ok_distinct_authors": False, "literal_ok": False, "n_drawable": 2}] * 3}]}
    tp = tmp_path / "table.json"
    tp.write_text(json.dumps(table))
    monkeypatch.setattr(s3, "_VALID_PATH", tp)
    monkeypatch.setattr(s3.dr, "load_items", lambda paths: (items, {}))
    monkeypatch.setattr(s3.dr, "input_paths", lambda: {})
    seen = []

    def fake_pool(fn, tasks, procs):
        seen.extend(tasks)
        out = []
        for key, i, it in tasks:
            ln = next(t for t in table["items"] if t["item_id"] == key)["lone_lines"][i]
            acc = [tuple(x) for x in ln["valid_draws"]]
            out.append({"key": key, "line": i, "n_drawable": ln["n_drawable"], "n_listed": len(acc), "listed_not_drawable": 0,
                        "accepted": sorted(acc), "refused_listed": {}, "unlisted": {}, "identical_to_default": {"True": len(acc)}})
        return out
    monkeypatch.setattr(s3, "_pool_map", fake_pool)
    out = s3.lines(1, ("control",))
    assert {k for k, _i, _it in seen} == {"k1", "k2"} and len(seen) == 6
    assert out["regimes"] == ["control"] and out["lines"] == 6 and out["listed_draws"] == 9 and out["accepted_draws"] == 9
    assert out["net_of_pair_rule_drops"] == {"items": 1, "lines": 3, "listed_draws": 6, "accepted_draws": 6,
                                             "two_valid_distinct_authors": 3, "refused_listed_by_reason": {}}
    assert out["reproduced"] and all(p["regime"] == "control" for p in out["per_line"])
    assert Counter(p["drop"] for p in out["per_line"]) == {False: 3, True: 3}
    seen.clear()
    out = s3.lines(1)
    assert {k for k, _i, _it in seen} == {"c1"} and out["regimes"] == ["candidate"]


@pytest.mark.skipif(not os.environ.get("S3_SLOW"), reason="S3_SLOW=1 runs the copy's default lines mode (minutes)")
def test_the_default_lines_run_reproduces_brief_27s_4537_of_4537():
    part = s3.PARTS / "lines.json"
    assert part.exists(), "run: stage3_b3_lone_line_check_s3.py lines (default mode) first"
    got = json.loads(part.read_text(encoding="utf-8"))
    ref = json.loads((orig.PARTS / "lines.json").read_text(encoding="utf-8"))
    assert got["listed_draws"] == ref["listed_draws"] == 4537 and got["accepted_draws"] == ref["accepted_draws"] == 4537
    assert got["lines"] == ref["lines"] == 234 and got["reproduced"] and got["differences_by_reason"] == {}
    strip = lambda p: {k: v for k, v in p.items() if k not in ("regime", "drop")}  # noqa: E731
    assert [strip(p) for p in got["per_line"]] == ref["per_line"]
