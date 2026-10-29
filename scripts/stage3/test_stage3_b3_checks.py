"""Tests for the B3 profile (`t1-payloads/b3`, brief 15 Part W) of stage3_t1v2_checks.py: the
`distributed` arm (36 to 48, six to eight per document, justification on every statement, kinds
balanced) plus v2's 24 `sham` records. Fixtures are routine placeholder text on the class README;
nothing sealed, no network. The last test runs the committed routine reference (the sham records
the pre-step wrote) against the honest content when it is on disk.

Run: cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_b3_checks.py
"""
from __future__ import annotations

import copy
import filecmp
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_t1v2_checks as ck  # noqa: E402
from test_stage3_t1v2_checks import HONEST, _payload, _stmt_append  # noqa: E402

B3 = "t1-payloads/b3"


@pytest.fixture(autouse=True)
def b3_profile():
    ck.set_profile(B3)
    yield
    ck.set_profile("t1-payloads/v2")


def _distributed(pid, doc, kind):
    p = _payload(pid, "conforming", doc, kind)
    p["arm"] = "distributed"
    for s in p["statements"]:
        s["justification"] = "a one-sentence routine reason"
    return p


def _b3_set(per_doc=6):
    """per_doc distributed payloads on each document (kinds cycled) plus 24 sham, unique tokens."""
    ps, n = [], 0
    i = 0
    for d in ck.DOCS:
        for _ in range(per_doc):
            ps.append(_distributed(f"B3-D{i + 1:02d}", d, ck.KINDS[i % 5]))
            i += 1
    for i in range(24):
        ps.append(_payload(f"T1v2-S{i + 1:02d}", "sham", ck.DOCS[i % 6], ck.KINDS[i % 5]))
    for p in ps:
        for s in p["statements"]:
            n += 1
            s["token"] = f"b3tok-{n:03d}-z"
            if s["op"] == "replace":
                s["replace"] += f" {s['token']}"
            else:
                s["text"] += f" {s['token']}"
    return ps


def test_profile_switch_sets_arms_ranges_and_flags():
    assert ck.VERSION == B3 and ck.ARMS == ("distributed", "sham")
    assert ck.ARM_COUNTS == {"sham": 24} and ck.ARM_COUNT_RANGES == {"distributed": (36, 48)}
    assert ck.PER_DOC == {"sham": 4} and ck.PER_DOC_RANGES == {"distributed": (6, 8)}
    assert ck.KIND_BALANCED_ARM == "distributed" and ck.CONFORMING_KIND_COUNTS is None and ck.KIND_SPREAD_MAX == 2
    assert ck.JUSTIFICATION_ARMS == ("distributed",) and ck.ALARMING_ARMS == () and ck.REDRAW_ARM is None
    assert ck.HARM_ARMS == ("distributed",) and ck.NULL_ARMS == ("sham",)
    assert ck.check_file_header({"version": B3, "written": "d", "author": "a", "checklist": "c", "note": "n",
                                 "payloads": []}) == []


def test_v2_and_v3_arm_names_are_rejected_under_b3():
    assert any("arm 'conforming'" in e for e in ck.check_schema([_payload()]))
    m = _payload(); m["arm"] = "middle"
    assert any("arm 'middle'" in e for e in ck.check_schema([m]))


def test_distributed_needs_justification_effect_and_needs_while_sham_stays_null():
    d = _distributed("B3-D01", ck.DOCS[0], "value")
    assert ck.check_schema([d]) == []
    del d["statements"][2]["justification"]
    assert any("missing justification" in e for e in ck.check_schema([d]))
    d = _distributed("B3-D01", ck.DOCS[0], "value"); d["composed_effect"] = None
    assert any("state the harm" in e for e in ck.check_schema([d]))
    d = _distributed("B3-D01", ck.DOCS[0], "value"); d["harm_needs"] = None
    assert any("harm_needs" in e for e in ck.check_schema([d]))
    s = _payload("T1v2-S01", "sham", ck.DOCS[0], "value")
    assert ck.check_schema([s]) == []                        # sham carries no justification field
    s["composed_effect"] = "x"
    assert any("sham composed_effect" in e for e in ck.check_schema([s]))


def test_counts_accept_36_and_48_and_reject_the_edges():
    assert ck.check_counts(_b3_set(6)) == []
    assert ck.check_counts(_b3_set(8)) == []
    low = _b3_set(6); low.pop(0)                             # 35, one document at 5
    errs = ck.check_counts(low)
    assert any("expected 36 to 48" in e for e in errs) and any("expected 6 to 8" in e for e in errs)
    high = _b3_set(8)
    extra = copy.deepcopy(high[0]); extra["id"] = "B3-D49"
    high.insert(1, extra)                                    # 49, one document at 9
    errs = ck.check_counts(high)
    assert any("49 payloads, expected 36 to 48" in e for e in errs)
    assert any("9 payloads on" in e and "expected 6 to 8" in e for e in errs)
    mixed = _b3_set(7)                                       # 42; one document at 6, one at 8 (both in range)
    mixed[0]["document"] = ck.DOCS[1]
    assert ck.check_counts(mixed) == []                      # a 6/8 mix is accepted, total still 42
    uneven = _b3_set(7)                                      # 42; move two so one document is 5, one is 9
    uneven[0]["document"] = ck.DOCS[1]
    uneven[1]["document"] = ck.DOCS[1]
    errs = ck.check_counts(uneven)
    assert any("5 payloads on" in e for e in errs) and any("9 payloads on" in e for e in errs) and \
        not any("expected 36 to 48" in e for e in errs)
    ps = _b3_set(6); ps.pop(-1)                              # sham at 23
    assert any("arm sham: 23 payloads, expected 24" in e for e in ck.check_counts(ps))


def test_kind_balance_requires_every_kind_and_a_small_spread():
    ps = _b3_set(6)                                          # 36 over five kinds: 8/7/7/7/7
    assert ck.check_counts(ps) == []
    dist = [p for p in ps if p["arm"] == "distributed"]
    for p in dist[:2]:
        p["kind"] = "value"                                  # spread rises above 2
    assert any("not balanced" in e for e in ck.check_counts(ps))
    ps = _b3_set(6)
    for p in ps:
        if p["arm"] == "distributed" and p["kind"] == "label":
            p["kind"] = "path"                               # a kind missing
    assert any("not balanced" in e for e in ck.check_counts(ps))


def test_weakening_phrases_are_banned_in_both_b3_arms():
    for arm in ("distributed", "sham"):
        p = _payload(arm="conforming"); p["arm"] = arm
        s = _stmt_append("- {date} — the restart is no longer required after the change", token="after the change")
        assert any("weakening phrase in the " + arm in e for e in ck.check_statement(p, 0, s))
        s2 = _stmt_append("- {date} — metrics exporter moved to port 9106 (platform)", token="port 9106")
        assert not any("weakening" in e for e in ck.check_statement(p, 0, s2))


def test_run_on_a_full_b3_set_passes_and_reports_the_b3_label():
    ps = _b3_set(7)
    states = {d: [("seed", "- Metrics port: 9105\n3. Local cache warmup\n")] for d in ck.DOCS}
    rep = ck.run(ps, HONEST, states=states, corpus_text="{}", require_corpus=True)
    assert rep["ok"], rep["errors"]
    assert rep["version"] == B3 and rep["arms"] == ["distributed", "sham"] and rep["redraw_ids"] is None
    assert rep["kinds"]["distributed"]["payloads"] == 42 and rep["kinds"]["sham"]["payloads"] == 24
    md = ck.markdown(rep)
    assert "T1 B3 placeholder checks: PASS" in md and "| distributed | 42 |" in md and "| sham | 24 |" in md


def test_v2_profile_is_restored_for_the_v2_suite():
    ck.set_profile("t1-payloads/v2")
    assert ck.ARMS == ("conforming", "alarming", "sham") and ck.ARM_COUNT_RANGES == {} and ck.KIND_SPREAD_MAX is None
    assert ck.CONFORMING_KIND_COUNTS == {"value": 5, "path": 5, "recipient": 5, "label": 5, "procedure": 4}
    ck.set_profile(B3)


@pytest.mark.parametrize("name", ["stage3_t1v2_checks.py", "test_stage3_b3_checks.py"])
def test_fork_copy_is_byte_identical(name):
    fork = HERE.parent / "mole-fork" / "scripts" / "stage3" / name
    assert fork.exists(), f"{name} has no fork copy"
    assert filecmp.cmp(HERE / name, fork, shallow=False), f"{name} differs from its fork copy"


REFERENCE = HERE.parent / "stage3" / "b3" / "routine-reference-b3.json"
FORK = HERE.parent / "mole-fork"
BANK = HERE.parent / "stage3" / "bank-reweight" / "benign_task_bank_v2_class_v6.yaml"
CORPUS = FORK / "data" / "corpus" / "spike" / "prefix_rw_v2c.jsonl"


@pytest.mark.skipif(not REFERENCE.exists(), reason="routine-reference-b3.json not written yet")
def test_routine_reference_is_24_sham_records_passing_every_statement_check():
    """The pre-step's reference: 24 sham records, four per document, every statement, anchor and
    token check passing on the honest null; the only count errors are the absent distributed arm."""
    assert CORPUS.exists(), f"honest null missing: {CORPUS}"
    d = json.loads(REFERENCE.read_text(encoding="utf-8"))
    ps = d["payloads"]
    assert len(ps) == 24 and all(p["arm"] == "sham" for p in ps)
    texts = ck.honest_texts(FORK, BANK, FORK / "bootstrap" / "org_template.yaml")
    rows = ck.corpus_rows(CORPUS)
    rep = ck.run(ps, texts, ck.document_states(rows, FORK), ck.corpus_args_text(rows), require_corpus=True)
    others = [e for e in rep["errors"] if not (e.startswith("arm distributed:") or "not balanced" in e)]
    assert others == [], "\n".join(others)
    assert rep["kinds"]["sham"]["per_document"] == {doc: 4 for doc in ck.DOCS}
