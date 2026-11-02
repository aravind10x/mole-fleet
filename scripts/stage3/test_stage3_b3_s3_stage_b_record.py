"""Tests for stage3_b3_s3_stage_b_record.py (brief 33 B4; a $0 follow-up at the coordinator's request): the spend table's
arithmetic against the run and render records (synthetic and the committed ones, read only), the manifest's additive
amendment on a temporary copy, and the refusals (an incomplete run, an existing prep-report entry, a missing fork copy, a
duplicate manifest path, the outputs index's row not found once). Nothing is written under work/ (temporary directories
only); no sentence of b3-results is read.

Run: cd work/checks && ../mole-fork/.venv/bin/python -I -m pytest -q test_stage3_b3_s3_stage_b_record.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_b3_s3_stage_b_record as rec  # noqa: E402

CELLS = rec.CELL_ORDER


def _run_render(n_units=10, dollars=1.0, est=0.8, n_calls=10, rebase=1.25, basis=0.2, status="complete"):
    """Nine synthetic cells with the same numbers: dollars per cell, the cell's character estimate, the re-base and S2's basis."""
    run = {"stage_b_started": "t0", "completed": "t1", "stopped": None, "dollars": {c: dollars for c in CELLS},
           "first_batch": {"n_units": 20, "outcomes": {"scored": 20}, "attempts": 20, "refused": 0, "input_tokens": 1, "output_tokens": 1, "dollars": 0.4,
                           "realised_per_unit_usd": 0.02, "estimated_per_unit_usd": 0.016, "ratio_realised_over_estimated": rebase, "cell_estimate_per_unit_usd": 0.016,
                           "ratio_realised_over_cell_estimate": rebase, "part2_basis_per_unit_usd": basis, "ratio_realised_over_part2_basis": 0.1,
                           "rebased_by_cell": {c: round(est * rebase, 4) for c in CELLS}, "rebased_total_usd": round(9 * est * rebase, 2), "escalate": False},
           "cells": {c: {"status": status, "n_units": n_units, "completed": n_units, "scored": n_units, "refused": 0, "errored_once": 0, "errored_final": 0, "missing": 0, "dollars": dollars}
                     for c in CELLS}}
    run["dollars"]["total"] = round(9 * dollars, 6)
    render = {"rows": {c: {"estimate": {"est_cost_usd": est, "n_calls": n_calls}, "s2_dollars_at_basis": round(basis * n_units, 4), "s2_basis_per_unit": basis} for c in CELLS},
              "s2_total_usd": round(9 * basis * n_units, 2)}
    return run, render


def test_the_spend_tables_arithmetic_on_synthetic_records():
    run, render = _run_render(n_units=10, dollars=1.0, est=0.8, n_calls=10, rebase=1.25, basis=0.2)
    rows = rec.spend_rows(run, render)
    assert [r["cell"] for r in rows] == CELLS and len(rows) == 9
    for r in rows:
        assert r["per_unit"] == pytest.approx(0.1) and r["estimate_per_unit"] == pytest.approx(0.08) and r["ratio_to_estimate"] == pytest.approx(1.25)
        assert r["rebased_usd"] == pytest.approx(1.0) and r["s2_usd"] == pytest.approx(2.0) and r["status"] == "complete" and r["dollars"] == pytest.approx(1.0)
    assert sum(r["dollars"] for r in rows) == pytest.approx(run["dollars"]["total"])
    # the ratio is per unit against the cell's own estimate per call, not the cell's totals
    run2, render2 = _run_render(n_units=4, dollars=2.0, est=1.0, n_calls=8)
    r = rec.spend_rows(run2, render2)[0]
    assert r["per_unit"] == pytest.approx(0.5) and r["estimate_per_unit"] == pytest.approx(0.125) and r["ratio_to_estimate"] == pytest.approx(4.0)


def test_the_spend_table_reproduces_the_committed_run_and_render_records():
    run, render = rec.j(rec.B3 / "s3-run-v0.json"), rec.j(rec.B3 / "s3-render-v0.json")       # read only; counts and dollars
    rows = rec.spend_rows(run, render)
    assert sum(r["dollars"] for r in rows) == pytest.approx(run["dollars"]["total"], abs=1e-3)
    for r in rows:
        v, e = run["cells"][r["cell"]], render["rows"][r["cell"]]["estimate"]
        assert r["per_unit"] == pytest.approx(v["dollars"] / v["n_units"], abs=1e-5)
        assert r["ratio_to_estimate"] == pytest.approx((v["dollars"] / v["n_units"]) / (e["est_cost_usd"] / e["n_calls"]), abs=1e-3)
        assert r["rebased_usd"] == run["first_batch"]["rebased_by_cell"][r["cell"]] and r["s2_usd"] == render["rows"][r["cell"]]["s2_dollars_at_basis"]
        assert r["scored"] + r["refused"] + r["errored_final"] + r["missing"] == r["n_units"]


def _synthetic_b3(tmp_path, monkeypatch, run, render):
    """A temporary B3 directory with every file mode_records reads, synthetic and small; the module's paths re-pointed."""
    b3 = tmp_path / "b3"
    b3.mkdir(parents=True)
    fork = tmp_path / "fork"
    (fork / "results/stage3/b3").mkdir(parents=True)
    (fork / "scripts/stage3").mkdir(parents=True)
    ids = ["i1", "i2", "i3", "i4"]
    matrix = {"populations": {p: {"ids": ids} for p in ("subset", "stratum", "full")}, "items": {}}
    units = {f"{i}:item0:{p}": {"item_id": i, "regime": "candidate", "arm": "item", "record": {"honest_edits_broken": 1 if (i == "i1" and p == 1) else 0}} for i in ids for p in (1, 2)}
    files = {"s3-applications-v0.json": {"units": units}, "s3-analysis-matrix-v0.json": matrix, "s3-run-v0.json": run, "s3-render-v0.json": render,
             "s3-scores-v0.json": {"rows": [{}] * 3, "applications_sha256": "a" * 64, "stopped": None},
             "b3-results.json": {"lock": {"rows": 3, "expected_rows": 3, "incomplete": {}, "stopped": None}, "cascade": {"state": "read", "step": 1}, "sentences": [{"family": "S-S"}, {"family": "S4"}]},
             "s3-honest-pairs-check-v0.json": {"pass": True}, "s3-clean-items-v0.json": {"touched_ids": ["i1"]}, "s3-readings-dryrun-v0.json": {}}
    for name, obj in files.items():
        (b3 / name).write_text(json.dumps(obj))
    for name in ("s3-stage-a-v0.md", "b3-results.md", "plan.md", "s3-trace-policy.json"):
        (b3 / name).write_text(f"synthetic {name}\n")
    prep = tmp_path / "prep-report.md"
    prep.write_text("# prep\n\n## 10. list\n")
    index = tmp_path / "INDEX.md"
    index.write_text("| B3 | **the S3 brief is `briefs/33-b3-s3-2026-11-02.md`** (cold read pending), then S3; x |\n")
    monkeypatch.setattr(rec, "B3", b3)
    monkeypatch.setattr(rec, "FORK", fork)
    monkeypatch.setattr(rec, "RECORD", b3 / "s3-stage-b-v0.md")
    monkeypatch.setattr(rec, "ADDITIONS", b3 / "b3-results-additions.md")
    monkeypatch.setattr(rec, "PREP", prep)
    monkeypatch.setattr(rec, "OUT_INDEX", index)
    monkeypatch.setattr(rec, "CACHE_FILES", [])
    return b3, fork, prep, index


def test_records_refuse_an_incomplete_run(tmp_path, monkeypatch):
    run, render = _run_render()
    run["cells"][CELLS[-1]]["status"] = "partial"
    b3, *_ = _synthetic_b3(tmp_path, monkeypatch, run, render)
    with pytest.raises(SystemExit, match="not complete"):
        rec.mode_records()
    assert not (b3 / "s3-stage-b-v0.md").exists() and not (b3 / "b3-results-additions.md").exists()
    run, render = _run_render()
    run["stopped"] = {"reason": "x"}
    _synthetic_b3(tmp_path / "two", monkeypatch, run, render)
    with pytest.raises(SystemExit, match="not complete"):
        rec.mode_records()


def test_records_write_the_four_outputs_once_and_refuse_a_second_prep_report_entry(tmp_path, monkeypatch, capsys):
    run, render = _run_render()
    b3, fork, prep, index = _synthetic_b3(tmp_path, monkeypatch, run, render)
    assert rec.mode_records() == 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert (b3 / "s3-stage-b-v0.md").exists() and (b3 / "b3-results-additions.md").exists()
    assert "## Brief 15 (B3), S3 (2026-11-02)" in prep.read_text() and "### Sealed defender parameters" in prep.read_text() and "### Spend" in prep.read_text()
    assert "**S3 done 2026-11-02**" in index.read_text() and "cold read pending" not in index.read_text()
    assert out["total_usd"] == pytest.approx(run["dollars"]["total"])
    md = (b3 / "s3-stage-b-v0.md").read_text()
    assert "| **total** | 90 | 90 | 0 | 0 | 0 | **$9.00**" in md and md.count("| complete") == 0 and "## Hashes" in md
    add = (b3 / "b3-results-additions.md").read_text()
    assert "| candidates | 1 of 8 (0.125) | 0 of 0 | 1 of 8 (0.125) |" in add and "Items with at least one such application: 1 of 4" in add
    with pytest.raises(SystemExit, match="prep-report entry exists"):
        rec.mode_records()


def test_records_refuse_when_the_outputs_index_row_is_not_found_once(tmp_path, monkeypatch):
    run, render = _run_render()
    b3, fork, prep, index = _synthetic_b3(tmp_path, monkeypatch, run, render)
    index.write_text("| B3 | nothing to replace |\n")
    with pytest.raises(SystemExit, match="B3 row was not found once"):
        rec.mode_records()


def _manifest(tmp_path, monkeypatch, with_fork_copies=True, duplicate=None):
    run, render = _run_render()
    b3, fork, prep, index = _synthetic_b3(tmp_path, monkeypatch, run, render)
    for name in rec.RESULT_FILES:
        p = b3 / name
        if not p.exists():
            p.write_text(f"synthetic {name}\n")
        if with_fork_copies:
            (fork / "results/stage3/b3" / name).write_bytes(p.read_bytes())
    m = {"version": "b0/v1", "n_files": 2, "all_copies_identical": True, "mismatched_or_missing": [],
         "files": [{"path": "b0/x.json", "sha256": "0" * 64, "copies_identical": True}, {"path": "b1/y.md", "sha256": "1" * 64, "copies_identical": True}],
         "amendments": [{"date": "2026-10-28", "by": "earlier", "added": ["b1/y.md"], "note": "additive"}]}
    if duplicate:
        m["files"].append({"path": duplicate, "sha256": "2" * 64, "copies_identical": True})
        m["n_files"] = 3
    mp = tmp_path / "frozen-tables.json"
    mp.write_text(json.dumps(m))
    monkeypatch.setattr(rec, "MANIFEST", mp)
    return mp, m


def test_the_manifest_amendment_is_additive_on_a_temporary_copy(tmp_path, monkeypatch, capsys):
    mp, before = _manifest(tmp_path, monkeypatch)
    assert rec.mode_manifest() == 0
    after = json.loads(mp.read_text())
    n = len(rec.RESULT_FILES)
    assert after["n_files"] == before["n_files"] + n == len(after["files"]) and after["all_copies_identical"] is True
    assert after["files"][:len(before["files"])] == before["files"]                         # no earlier entry changed
    assert after["amendments"][:-1] == before["amendments"] and after["amendments"][-1]["added"] == [f"b3/{f}" for f in rec.RESULT_FILES]
    new = after["files"][len(before["files"]):]
    assert [e["path"] for e in new] == [f"b3/{f}" for f in rec.RESULT_FILES]
    for e in new:
        assert e["sha256"] == e["sha256_fork_copy"] and e["copies_identical"] and e["tag"] in ("confirmatory", "methods") and e["tables_drawn_on"] and e["added_beyond_brief_list"] is False
        assert e["bytes"] == (rec.B3 / Path(e["path"]).name).stat().st_size
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["n_files"] == after["n_files"] and out["all_copies_identical"]


def test_the_manifest_refuses_a_missing_fork_copy_and_a_duplicate_path(tmp_path, monkeypatch):
    mp, before = _manifest(tmp_path, monkeypatch, with_fork_copies=False)
    with pytest.raises(SystemExit, match="no fork copy"):
        rec.mode_manifest()
    assert json.loads(mp.read_text()) == before                                               # untouched on a refusal
    mp, before = _manifest(tmp_path / "dup", monkeypatch, duplicate="b3/b3-results.md")
    with pytest.raises(SystemExit, match="already in the manifest"):
        rec.mode_manifest()
    assert json.loads(mp.read_text()) == before


def test_nothing_was_written_under_the_project_by_these_tests():
    # the module's real paths are untouched by the tests above (they re-point every path to a temporary directory)
    assert rec.B3 == rec.PROJECT / "work/stage3/b3" and rec.MANIFEST == rec.PROJECT / "work/stage3/b0/frozen-tables.json"
