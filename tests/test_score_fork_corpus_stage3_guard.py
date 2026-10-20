"""The fork's Stage 2b P scorer (scripts/track_b/score_fork_corpus.py) has no --whole-key, so a
Stage 3 P run from it cannot render the target document whole (branch review 2026-10-20,
Spec finding a1; prep-report erratum 6). Stage 3's P view runs from
scripts/stage3/score_fork_corpus.py. The track_b copy refuses a Stage 3 run before it imports
anything, naming the copy to use. Run as a subprocess: the track_b copy imports judge_client
from work/checks, which this test suite does not put on sys.path."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACK_B = REPO / "scripts" / "track_b" / "score_fork_corpus.py"
STAGE3 = REPO / "scripts" / "stage3" / "score_fork_corpus.py"
REFUSAL = "scripts/stage3/score_fork_corpus.py"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(TRACK_B), *args], text=True,
                          capture_output=True, timeout=120)


def test_whole_key_from_the_track_b_copy_is_refused(tmp_path):
    r = _run(["--corpus", str(tmp_path / "prefix_v1.jsonl"), "--out", str(tmp_path / "o.parquet"),
              "--cache", str(tmp_path / "c.jsonl"), "--whole-key", "content", "--dry-run"])
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert "REFUSED" in r.stderr and REFUSAL in r.stderr, r.stderr


def test_stage3_named_corpus_from_the_track_b_copy_is_refused(tmp_path):
    for stem in ("f4_pilot_P", "stage3_prefix_1", "pilot_prefix_rw", "s5c_objective_benign_1"):
        r = _run(["--corpus", str(tmp_path / f"{stem}.jsonl"), "--out", str(tmp_path / "o.parquet"),
                  "--cache", str(tmp_path / "c.jsonl"), "--dry-run"])
        assert r.returncode == 2, (stem, r.returncode, r.stderr)
        assert "REFUSED" in r.stderr and REFUSAL in r.stderr, (stem, r.stderr)


def test_stage2b_invocation_is_not_refused_by_the_guard(tmp_path):
    # A Stage 2b-shaped call passes the guard (it then fails later for an unrelated reason in
    # this isolated subprocess: judge_client is not importable without work/checks).
    r = _run(["--corpus", str(tmp_path / "prefix_v1.jsonl"), "--out", str(tmp_path / "o.parquet"),
              "--cache", str(tmp_path / "c.jsonl"), "--dry-run"])
    assert "REFUSED" not in r.stderr, r.stderr


def test_stage3_copy_accepts_whole_key():
    src = STAGE3.read_text(encoding="utf-8")
    assert '"--whole-key"' in src and "REFUSED" not in src
