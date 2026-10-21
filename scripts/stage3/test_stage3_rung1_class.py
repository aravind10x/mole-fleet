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


# ── G0a: the tested reading of an actual lab corpus (brief 07c C5; plan v2 section 2) ──────
def _row(acct, day, action, path, exit_code=0, service="owncloud", hour=10):
    return {"account": acct, "ts": f"{day}T{hour:02d}:00:00Z", "service": service, "action": action,
            "args": {"path": path, **({"content": "x"} if action == "write_file" else {})},
            "exit_code": exit_code}


def test_corpus_measure_counts_class_writers_readers_and_writes_per_document_per_day():
    import stage3_rung1_class as rc
    docs = rc.DOC_PATHS
    days = ["2026-04-06", "2026-04-07"]
    rows = []
    # day 1: 10 active accounts; a0..a2 write doc0 (3 writes, one each), a3 writes doc1 twice,
    # a4..a6 read doc2; a7 reads a non-class path; a8, a9 only email
    for i in range(10):
        rows.append(_row(f"a{i}", days[0], "send_email", None, service="email"))
    for i in range(3):
        rows.append(_row(f"a{i}", days[0], "write_file", docs[0]))
    rows.append(_row("a3", days[0], "write_file", docs[1]))
    rows.append(_row("a3", days[0], "write_file", docs[1], hour=11))
    for i in (4, 5, 6):
        rows.append(_row(f"a{i}", days[0], "read_file", docs[2]))
    rows.append(_row("a7", days[0], "read_file", "/training-data/README.md"))
    rows.append(_row("a7", days[0], "write_file", docs[3], exit_code=1))      # failed: not counted
    # day 2: 4 active, a0 reads doc0, a1 writes doc0 three times
    for i in range(4):
        rows.append(_row(f"a{i}", days[1], "send_email", None, service="email"))
    rows.append(_row("a0", days[1], "read_bytes", docs[0]))
    for h in (9, 10, 11):
        rows.append(_row("a1", days[1], "write_file", docs[0], hour=h))
    m = rc.corpus_measure(rows)
    assert m["days"] == days
    d1 = m["per_day"][days[0]]
    assert d1["active"] == 10 and d1["class_writers"] == 4 and d1["class_readers"] == 3
    assert abs(d1["writer_share"] - 0.4) < 1e-9 and abs(d1["reader_share"] - 0.3) < 1e-9
    assert d1["writes_per_document"][docs[0]] == 3 and d1["writes_per_document"][docs[1]] == 2
    assert d1["writes_per_document"][docs[3]] == 0
    d2 = m["per_day"][days[1]]
    assert d2["active"] == 4 and d2["class_writers"] == 1 and d2["class_readers"] == 1
    assert d2["writes_per_document"][docs[0]] == 3
    # the verdict: operative reading = every document on every day >= 3 writes (here it fails),
    # class shares = means over days ((0.4 + 0.25) / 2 = 0.325, (0.3 + 0.25) / 2 = 0.275)
    v = m["verdict"]
    assert abs(v["class_writer_share"] - 0.325) < 1e-9 and abs(v["class_reader_share"] - 0.275) < 1e-9
    assert v["clauses"]["class_writer_share>=0.10"] and v["clauses"]["class_reader_share>=0.20"]
    assert v["clauses"]["every_document>=3_writes_every_day"] is False
    assert v["status"] == "KILL" and v["rare_write_members"]
    assert m["per_document"][docs[0]]["writes_per_day_min"] == 3
    assert m["per_document"][docs[1]]["writes_per_day_min"] == 0


def test_corpus_measure_cli_writes_json_and_md(tmp_path):
    import json
    import stage3_rung1_class as rc
    docs = rc.DOC_PATHS
    rows = []
    for d in ("2026-04-06",):
        for i in range(10):
            rows.append(_row(f"a{i}", d, "send_email", None, service="email"))
            for p in docs:
                rows.append(_row(f"a{i}", d, "write_file", p, hour=9))
                rows.append(_row(f"a{i}", d, "read_file", p, hour=10))
    corpus = tmp_path / "c.jsonl"
    corpus.write_text("".join(json.dumps(r) + "\n" for r in rows))
    rc_ = rc.main(["--from-corpus", str(corpus), "--out-json", str(tmp_path / "o.json"),
                   "--out-md", str(tmp_path / "o.md")])
    assert rc_ == 0
    res = json.loads((tmp_path / "o.json").read_text())
    assert res["verdict"]["status"] == "PASS" and res["source"] == "corpus"
    assert "every document on every day" in (tmp_path / "o.md").read_text()
