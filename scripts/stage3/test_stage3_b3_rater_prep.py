"""Tests for stage3_b3_rater_prep.py (brief 17 R0.3): folders hold only the three inputs, checked by hash; a scale's
two pastes differ only in -p1 / -p2; the paste bodies carry none of the forbidden words; two note lines come first."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_b3_rater_prep as rp  # noqa: E402


def _bodies(n=10):
    return {(s, p): rp.body(s, p, "/home/x", n) for s, p in rp.SESSIONS}


def test_pastes_differ_only_in_pass_and_carry_no_forbidden_word():
    out = rp.check_pastes(_bodies())
    assert out["forbidden_hits"] == 0
    assert len(out["statements"]["differing_lines"]) == len(out["triples"]["differing_lines"]) == 2
    assert out["statements"]["differing_lines"][0] == out["triples"]["differing_lines"][0] == 3
    for (s, p), b in _bodies().items():
        assert b.startswith(f"Your working directory is /home/x/b3-rater-{s}-p{p}.")
        assert f"`ratings-b3-{s}-p{p}.jsonl`" in b and rp.STRIPPED[s] in b and rp.RUBRIC[0] in b and rp.DAY0[0] in b
        assert "key file" in b and "no brief" in b and "STATUS" in b and "outside your working directory" in b
        assert ("section 2 of the rubric" in b) == (s == "statements") and ("section 2b of the rubric" in b) == (s == "triples")
        assert "/KruxAI" not in b and "tais-project" not in b
        h = rp.header(s, p, "/home/x", 10)
        assert len(h.splitlines()) == 2 and all(line.startswith("<!--") and line.endswith("-->") for line in h.splitlines())


def test_check_pastes_rejects_a_leak_or_an_extra_difference():
    b = _bodies()
    bad = {**b, ("triples", 1): b[("triples", 1)] + "A candidate line.\n", ("triples", 2): b[("triples", 2)] + "A candidate line.\n"}
    with pytest.raises(ValueError):
        rp.check_pastes(bad)
    bad = {**b, ("statements", 2): b[("statements", 2)].replace("about 20", "about 25")}
    with pytest.raises(ValueError):
        rp.check_pastes(bad)


def test_build_copies_by_hash_into_otherwise_empty_folders(tmp_path, monkeypatch):
    t1k, rater, home = tmp_path / "t1k", tmp_path / "rater", tmp_path / "home"
    for d in (t1k, rater, home):
        d.mkdir()
    (t1k / "rubric-passes-2.md").write_text("# rubric\n")
    (t1k / "doc-states-day0.md").write_text("# day 0\n")
    (rater / "stripped-statements-b3.json").write_text(json.dumps([{"statement_id": "a"}] * 4))
    (rater / "stripped-triples-b3.json").write_text(json.dumps([{"triple_id": "b"}] * 3))
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    monkeypatch.setattr(rp, "RUBRIC", ("rubric-passes-2.md", h(t1k / "rubric-passes-2.md")))
    monkeypatch.setattr(rp, "DAY0", ("doc-states-day0.md", h(t1k / "doc-states-day0.md")))
    (rater / "hashes.txt").write_text(f"{h(rater / 'stripped-statements-b3.json')}  stripped-statements-b3.json\n"
                                      f"{h(rater / 'stripped-triples-b3.json')}  stripped-triples-b3.json\n")
    rec = rp.build(t1k, rater, home)
    assert rec["counts"] == {"statements": 4, "triples": 3}
    for s, p in rp.SESSIONS:
        assert sorted(x.name for x in (home / f"b3-rater-{s}-p{p}").iterdir()) == sorted(
            ["rubric-passes-2.md", "doc-states-day0.md", rp.STRIPPED[s]])
        assert (rater / f"paste-{s}-p{p}.md").read_text().splitlines()[2].startswith("Your working directory is")
    # a stripped file that no longer matches its committed hash stops the build
    (rater / "stripped-triples-b3.json").write_text("[]")
    with pytest.raises(ValueError):
        rp.build(t1k, rater, home)
    # a folder holding anything else stops the build
    (rater / "stripped-triples-b3.json").write_text(json.dumps([{"triple_id": "b"}] * 3))
    (home / "b3-rater-statements-p1" / "extra.txt").write_text("x")
    with pytest.raises(ValueError):
        rp.build(t1k, rater, home)
