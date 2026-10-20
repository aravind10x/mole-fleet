"""Tests for stage3_rung1_class.py (brief 07b F2.1; design v4 section 11.1).

Synthetic/bank inputs only; the shipped bank is read, never written.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_candidate_docs as cd  # noqa: E402
import stage3_rung1_class as rc  # noqa: E402
import stage3_rung1_density as r1  # noqa: E402

FORK = HERE.parent / "mole-fork"
BANK = FORK / "bootstrap" / "benign_task_bank_v2.yaml"
TEMPLATE = FORK / "bootstrap" / "org_template.yaml"
FORBIDDEN = re.compile(r"\b(attack|payload|persona|objective|trigger|exfiltrat\w*|backdoor|"
                       r"poison\w*|secret|collu\w*|coalition|covert|malicious|inject\w*)\b", re.I)


def test_class_has_at_least_six_documents_across_teams():
    assert len(rc.CLASS) >= 6
    assert len({d["path"] for d in rc.CLASS}) == len(rc.CLASS)
    # every class document is written and read by at least one team; writers and readers span
    teams_writing = {t for d in rc.CLASS for t in d["write_teams"]}
    teams_reading = {t for d in rc.CLASS for t in d["read_teams"]}
    assert len(teams_writing) >= 4 and len(teams_reading) >= 5


def test_generated_tasks_classify_name_only_their_document_and_are_routine():
    ct = rc.class_tasks()
    for team, tasks in ct.items():
        for role, doc, text in tasks:
            assert cd.shared_paths(text) == [doc], (text, cd.shared_paths(text))
            assert cd.classify_doc_task(text, doc) == role, (role, text)
            assert not FORBIDDEN.search(text), text
            if role == "read":
                assert "{ws}" in text


def test_class_bank_appends_only_and_leaves_the_shipped_bank_byte_identical(tmp_path):
    shipped_text = BANK.read_text(encoding="utf-8")
    new = r1.reweighted_text(shipped_text, rc.added_for_reweight(rc.class_tasks()))
    # every shipped line survives in order (append-only)
    si = iter(shipped_text.splitlines())
    cur = next(si, None)
    for ln in new.splitlines():
        if cur is not None and ln == cur:
            cur = next(si, None)
    assert cur is None, "a shipped line was dropped or reordered"
    assert BANK.read_text(encoding="utf-8") == shipped_text        # unchanged on disk
    both = yaml.safe_load(new)
    assert set(both) == set(yaml.safe_load(shipped_text))          # same teams


def test_per_document_write_counts_are_comparable_and_span_teams():
    ct = rc.class_tasks()
    writes_per_doc = {}
    for team, tasks in ct.items():
        for role, doc, _ in tasks:
            if role == "write":
                writes_per_doc.setdefault(doc, []).append(team)
    assert set(writes_per_doc) == set(rc.DOC_PATHS)
    for doc, teams in writes_per_doc.items():
        assert len(set(teams)) >= 2, (doc, teams)                  # no single-team document


def _sim():
    tmpl = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))
    roster = r1.roster_from_template(tmpl)
    shipped = yaml.safe_load(BANK.read_text(encoding="utf-8"))
    idx = rc.team_index(rc.class_tasks(), shipped)
    return rc.simulate_class(idx, roster, 2, n_seeds=40)


@pytest.mark.skipif(not BANK.exists(), reason="bank not on disk")
def test_simulation_meets_the_amended_bars_at_s2():
    sim = _sim()
    v = rc.verdict(sim)
    assert v["status"] == "PASS", v
    assert v["class_writer_share"] >= rc.BAR_CLASS_WRITER_SHARE
    assert v["class_reader_share"] >= rc.BAR_CLASS_READER_SHARE
    assert all(w >= rc.BAR_DOC_WRITES for w in v["per_document_writes_per_day"].values())
    assert not v["rare_write_members"]


@pytest.mark.skipif(not BANK.exists(), reason="bank not on disk")
def test_simulation_is_reproducible_for_a_seed():
    a, b = _sim(), _sim()
    assert a["class"]["writer_share"]["mean"] == b["class"]["writer_share"]["mean"]


def test_verdict_kills_on_a_rare_write_member():
    sim = {"class": {"writer_share": {"mean": 0.2}, "reader_share": {"mean": 0.3}},
           "per_document": {p: {"writes_per_day": {"mean": 4.0}} for p in rc.DOC_PATHS}}
    sim["per_document"][rc.DOC_PATHS[0]]["writes_per_day"]["mean"] = 1.0
    v = rc.verdict(sim)
    assert v["status"] == "KILL" and v["kill"]["a_member_is_a_rare_write_field_P5"]
    assert v["rare_write_members"] == [rc.DOC_PATHS[0]]
