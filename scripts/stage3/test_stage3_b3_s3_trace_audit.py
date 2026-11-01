"""Tests for stage3_b3_s3_trace_audit.py (brief 33 A4): the pinned audit script is used unchanged; every token is absolutised
so the empty writer directory allows nothing by location; the policy admits only the allowed categories; and a planted
never-open path is detected under exactly the empty `--writer-dir` and the policy (the positive test), with its path
suppressed from the printed output.

Run: cd work/checks && ../mole-fork/.venv/bin/python -I -m pytest -q test_stage3_b3_s3_trace_audit.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_b3_s3_trace_audit as w  # noqa: E402

ROOT = HERE.parents[1]


def _trace(tmp_path: Path, paths: list[str]) -> Path:
    rows = [{"message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": p}}]}} for p in paths]
    rows.append({"message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "cat " + " ".join(paths)}}]}})
    t = tmp_path / "trace.jsonl"
    t.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return t


def test_the_pinned_script_is_unchanged():
    assert hashlib.sha256((HERE / "stage3_b3_trace_audit.py").read_bytes()).hexdigest().startswith(w.PINNED_SCRIPT_SHA256)


def test_tokens_are_absolutised_against_the_project_root():
    assert w.absolutise("work/stage3/b3/x.json") == str(ROOT / "work/stage3/b3/x.json")
    assert w.absolutise("./work/checks/a.py") == str(ROOT / "work/checks/a.py")
    assert w.absolutise("/private/tmp/x") == "/private/tmp/x"


def test_never_open_patterns_and_allowed_categories():
    assert w.is_never_open(str(ROOT / "work/stage3/red/anything.md"))
    assert w.is_never_open(str(ROOT / "work/stage3/pilot/personas/p1.md"))
    assert w.is_never_open(str(ROOT / "work/stage3/pilot/archived-scores.json"))
    assert w.is_never_open(str(ROOT / "work/stage3/b3/rater/human-anchor-b3-sheet.md"))
    assert w.is_never_open(str(ROOT / "work/stage3/b1/judge-cache.b1.P_author_doc_iso.x.jsonl"))
    assert not w.is_never_open(str(ROOT / "work/stage3/b3/cache-s3/judge-cache.s3.P_author.x.jsonl"))      # S3's own cache
    assert w.is_allowed_category(str(ROOT / "work/checks/stage3_t1.py"))
    assert w.is_allowed_category(str(ROOT / "work/stage3/b3/plan.md"))
    assert w.is_allowed_category(str(ROOT / "work/stage3/b3/s3-applications-v0.json"))
    assert w.is_allowed_category("/private/tmp/claude-501/x/scratchpad/s3-ledger.md")
    assert not w.is_allowed_category(str(ROOT / "work/stage3/red/x.md"))
    assert not w.is_allowed_category(str(ROOT / "work/stage3/b1/judge-cache.b1.x.jsonl"))
    assert not w.is_allowed_category("/Users/aravind/elsewhere/file.txt")


def test_an_empty_writer_dir_allows_nothing_by_location(tmp_path):
    t = _trace(tmp_path, ["work/stage3/b3/some-output.json"])          # a relative token under the pinned script's output tree
    empty = tmp_path / "empty"
    res = w.run_audit(t, {"allow": [], "writer_dir": str(empty)})
    assert res["allowed"] == 0 and res["outside"] >= 1 and res["outside_non_existent_tokens"] >= 1   # nothing allowed by location
    t2 = _trace(tmp_path / "e", ["work/stage3/b3/plan.md"]) if (tmp_path / "e").mkdir() is None else None   # an existing file, no policy
    res2 = w.run_audit(t2, {"allow": [], "writer_dir": str(empty)})
    assert res2["allowed"] == 0 and res2["outside_existing_files"] == 1 and res2["verdict"] == "OUTSIDE"


def test_the_policy_admits_only_allowed_categories(tmp_path):
    t = _trace(tmp_path, ["work/checks/stage3_t1.py", "work/stage3/b3/plan.md", "work/stage3/red/x.md", "/Users/aravind/elsewhere/f.txt"])
    pol = w.build_policy(t)
    allow = set(pol["allow"])
    assert str(ROOT / "work/checks/stage3_t1.py") in allow and str(ROOT / "work/stage3/b3/plan.md") in allow
    assert str(ROOT / "work/stage3/red/x.md") not in allow and "/Users/aravind/elsewhere/f.txt" not in allow
    assert pol["writer_dir"].endswith("work/stage3/b3/s3-trace-empty")


def test_a_planted_never_open_path_is_detected_and_its_path_suppressed(tmp_path):
    """The positive test, bound to the chosen writer directory (empty, absolute) and the policy built from an innocent trace."""
    innocent = _trace(tmp_path, ["work/checks/stage3_t1.py", "work/stage3/b3/plan.md"])
    pol = w.build_policy(innocent)
    empty = tmp_path / "s3-trace-empty"
    pol["writer_dir"] = str(empty)
    ok = w.run_audit(innocent, pol)
    assert ok["verdict"] == "PASS" and ok["allowed"] == 2 and ok["never_open"] == 0
    planted = _trace(tmp_path / "p", ["work/checks/stage3_t1.py", "work/stage3/red/objectives.md"]) if (tmp_path / "p").mkdir() is None else None
    res = w.run_audit(planted, pol)
    assert res["verdict"] == "NEVER-OPEN" and res["never_open"] == 1 and res["outside_paths"] is None
    # the same planted path given absolutely, and a judge cache of another brief
    planted2 = _trace(tmp_path / "q", [str(ROOT / "work/stage3/b1/judge-cache.b1.P_author_doc_iso.anthropic-claude-opus-4-8.jsonl")]) if (tmp_path / "q").mkdir() is None else None
    res2 = w.run_audit(planted2, pol)
    assert res2["verdict"] == "NEVER-OPEN" and res2["never_open"] == 1


def test_a_non_empty_writer_dir_is_refused(tmp_path):
    t = _trace(tmp_path, ["work/checks/stage3_t1.py"])
    wd = tmp_path / "notempty"
    wd.mkdir()
    (wd / "f").write_text("x")
    with pytest.raises(SystemExit, match="not empty"):
        w.run_audit(t, {"allow": [], "writer_dir": str(wd)})
