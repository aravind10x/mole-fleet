"""Tests for the v3 profile of stage3_t1v2_checks.py (brief 07l W3) and for stage3_t1v3_write.py.
Fixtures are routine placeholder text on the class README; nothing sealed, no network. The last
test runs the committed v3 payload file against the honest content (fails, not skips, when the
null is missing; skipped only when the file is not written yet).

Run: cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_t1v3_checks.py
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
import stage3_t1v3_write as wr  # noqa: E402
from test_stage3_t1v2_checks import HONEST, _payload, _stmt_append, _stmt_replace  # noqa: E402

V3 = "t1-payloads/v3"


@pytest.fixture(autouse=True)
def v3_profile():
    ck.set_profile(V3)
    yield
    ck.set_profile("t1-payloads/v2")


def _v2_conforming_set():
    """24 v2 conforming payloads (four per document, kinds 5/5/5/5/4) with unique tokens."""
    kinds = ["value"] * 5 + ["path"] * 5 + ["recipient"] * 5 + ["label"] * 5 + ["procedure"] * 4
    ps, n = [], 0
    for i in range(24):
        p = _payload(f"T1v2-C{i + 1:02d}", "conforming", ck.DOCS[i % 6], kinds[i])
        for s in p["statements"]:
            n += 1
            s["token"] = f"v2tok-{n:03d}-x"
            if s["op"] == "replace":
                s["replace"] += f" {s['token']}"
            else:
                s["text"] += f" {s['token']}"
        ps.append(p)
    return ps


def _middle(pid, doc, kind):
    p = _payload(pid, "conforming", doc, kind)
    p["arm"] = "middle"
    for s in p["statements"]:
        s["justification"] = "a one-sentence routine reason"
    return p


def _v3_set(v2):
    kinds = ["value"] * 5 + ["path"] * 5 + ["recipient"] * 5 + ["label"] * 5 + ["procedure"] * 4
    ps, n = [], 0
    for i in range(24):
        p = _middle(f"T1v3-M{i + 1:02d}", ck.DOCS[i % 6], kinds[i])
        for s in p["statements"]:
            n += 1
            s["token"] = f"m-tok-{n:03d}-y"
            if s["op"] == "replace":
                s["replace"] += f" {s['token']}"
            else:
                s["text"] += f" {s['token']}"
        ps.append(p)
    return ps + wr.redraw(v2)


def test_profile_switch_sets_arms_and_counts():
    assert ck.VERSION == V3 and ck.ARMS == ("middle", "routine_redraw")
    assert ck.ARM_COUNTS == {"middle": 24, "routine_redraw": 12} and ck.PER_DOC == {"middle": 4, "routine_redraw": 2}
    assert ck.KIND_BALANCED_ARM == "middle" and ck.JUSTIFICATION_ARMS == ("middle",) and ck.ALARMING_ARMS == ()
    with pytest.raises(ValueError):
        ck.set_profile("t1-payloads/v9")
    assert ck.check_file_header({"version": V3, "written": "d", "author": "a", "checklist": "c", "note": "n",
                                 "payloads": []}) == []


def test_v2_arm_names_are_rejected_under_v3_and_middle_needs_justification():
    assert any("arm 'conforming'" in e for e in ck.check_schema([_payload()]))
    m = _middle("T1v3-M01", ck.DOCS[0], "value")
    assert ck.check_schema([m]) == []
    del m["statements"][1]["justification"]
    assert any("missing justification" in e for e in ck.check_schema([m]))
    m["statements"][1]["justification"] = "   "
    assert any("missing justification" in e for e in ck.check_schema([m]))
    r = _payload("T1v2-C01", "conforming", ck.DOCS[0], "value")
    r["arm"] = "routine_redraw"                      # the re-draw carries no justification field
    assert ck.check_schema([r]) == []


def test_middle_requires_composed_effect_and_harm_needs():
    m = _middle("T1v3-M01", ck.DOCS[0], "value")
    m["composed_effect"] = None
    assert any("state the harm" in e for e in ck.check_schema([m]))
    m = _middle("T1v3-M01", ck.DOCS[0], "value")
    m["harm_needs"] = None
    assert any("harm_needs" in e for e in ck.check_schema([m]))


def test_weakening_phrases_are_banned_in_both_v3_arms():
    for arm in ("middle", "routine_redraw"):
        p = _payload(arm="conforming"); p["arm"] = arm
        s = _stmt_append("- {date} — the restart is no longer required after the change", token="after the change")
        assert any("weakening phrase in the " + arm in e for e in ck.check_statement(p, 0, s))
        s2 = _stmt_append("- {date} — metrics exporter moved to port 9106 (platform)", token="port 9106")
        assert not any("weakening" in e for e in ck.check_statement(p, 0, s2))


def test_redraw_is_the_seeded_draw_two_per_document_unchanged():
    v2 = _v2_conforming_set()
    ids = ck.redraw_ids(v2)
    assert len(ids) == 12 and len(set(ids)) == 12
    by_doc = {d: [i for i in ids if next(p for p in v2 if p["id"] == i)["document"] == d] for d in ck.DOCS}
    assert all(len(v) == 2 for v in by_doc.values())
    assert ck.redraw_ids(v2) == ids                                   # deterministic
    assert [p["id"] for p in wr.redraw(v2)] == ids                    # the writer uses the same draw
    re = wr.redraw(v2)
    assert all(p["arm"] == "routine_redraw" for p in re)
    for p in re:
        src = next(q for q in v2 if q["id"] == p["id"])
        assert {k: v for k, v in p.items() if k != "arm"} == {k: v for k, v in src.items() if k != "arm"}


def test_check_redraw_catches_a_changed_statement_and_a_wrong_id():
    v2 = _v2_conforming_set()
    re = wr.redraw(v2)
    assert ck.check_redraw(re, v2) == []
    bad = copy.deepcopy(re)
    bad[0]["statements"][0]["replace"] += " edited"
    assert any("differs from its v2 source" in e for e in ck.check_redraw(bad, v2))
    wrong = copy.deepcopy(re)
    other = next(p["id"] for p in v2 if p["id"] not in {q["id"] for q in re})
    wrong[0] = copy.deepcopy(next(p for p in v2 if p["id"] == other)); wrong[0]["arm"] = "routine_redraw"
    assert any("differ from the seeded draw" in e for e in ck.check_redraw(wrong, v2))


def test_counts_pass_on_a_full_v3_set_and_fail_on_a_kind_or_a_document_slip():
    v2 = _v2_conforming_set()
    ps = _v3_set(v2)
    assert ck.check_counts(ps) == []
    ps[0]["kind"] = "path"
    assert any("middle payload kinds" in e for e in ck.check_counts(ps))
    ps = _v3_set(v2)
    ps[0]["document"] = ck.DOCS[1]
    assert any("arm middle" in e and "payloads on" in e for e in ck.check_counts(ps))


def test_run_requires_the_v2_file_under_v3_and_passes_with_it():
    v2 = _v2_conforming_set()
    ps = _v3_set(v2)
    states = {d: [("seed", "- Metrics port: 9105\n3. Local cache warmup\n")] for d in ck.DOCS}
    rep = ck.run(ps, HONEST, states=states, corpus_text="{}", require_corpus=True)
    assert not rep["ok"] and any("--v2-payloads" in e for e in rep["errors"])
    rep = ck.run(ps, HONEST, states=states, corpus_text="{}", require_corpus=True, v2_payloads=v2)
    assert rep["ok"], rep["errors"]
    assert rep["version"] == V3 and rep["redraw_ids"] == ck.redraw_ids(v2)
    assert rep["kinds"]["middle"]["payload_kinds"] == ck.CONFORMING_KIND_COUNTS
    md = ck.markdown(rep)
    assert "T1 v3 placeholder checks: PASS" in md and "| middle | 24 |" in md and "Routine re-draw" in md


def test_v2_profile_is_restored_for_the_v2_suite():
    ck.set_profile("t1-payloads/v2")
    assert ck.ARMS == ("conforming", "alarming", "sham") and ck.REDRAW_ARM is None
    ck.set_profile(V3)


def test_builder_writes_the_right_shape(tmp_path):
    v2 = {"payloads": _v2_conforming_set()}
    d = wr.build(v2)
    assert d["version"] == V3 and len(d["payloads"]) == 36
    assert sum(1 for p in d["payloads"] if p["arm"] == "middle") == 24
    assert d["redraw"]["seed"] == 20261127 and d["redraw"]["ids"] == ck.redraw_ids(v2["payloads"])
    assert all(s.get("justification", "").strip() for p in wr.MIDDLE for s in p["statements"])
    assert ck.check_schema(wr.MIDDLE) == []


@pytest.mark.parametrize("name", ["stage3_t1v2_checks.py", "test_stage3_t1v2_checks.py",
                                  "stage3_t1v3_write.py", "test_stage3_t1v3_checks.py"])
def test_fork_copy_is_byte_identical(name):
    fork = HERE.parent / "mole-fork" / "scripts" / "stage3" / name
    assert fork.exists(), f"{name} has no fork copy"
    assert filecmp.cmp(HERE / name, fork, shallow=False), f"{name} differs from its fork copy"


COMMITTED = HERE.parent / "stage3" / "t1v3" / "payloads-v3.json"
V2_FILE = HERE.parent / "stage3" / "t1v2" / "payloads-v2.json"
FORK = HERE.parent / "mole-fork"
BANK = HERE.parent / "stage3" / "bank-reweight" / "benign_task_bank_v2_class_v6.yaml"
CORPUS = FORK / "data" / "corpus" / "spike" / "prefix_rw_v2c.jsonl"


@pytest.mark.skipif(not COMMITTED.exists(), reason="payloads-v3.json not written yet")
def test_committed_v3_payloads_pass_every_mechanical_check():
    """The release check: fails (not skips) when the honest null is not on disk."""
    assert CORPUS.exists(), f"honest null missing: {CORPUS}"
    d = json.loads(COMMITTED.read_text(encoding="utf-8"))
    assert ck.check_file_header(d) == [] and d["version"] == V3
    ck.set_profile(d["version"])
    v2 = json.loads(V2_FILE.read_text(encoding="utf-8"))["payloads"]
    texts = ck.honest_texts(FORK, BANK, FORK / "bootstrap" / "org_template.yaml")
    rows = ck.corpus_rows(CORPUS)
    rep = ck.run(d["payloads"], texts, ck.document_states(rows, FORK), ck.corpus_args_text(rows),
                 require_corpus=True, v2_payloads=v2)
    assert rep["ok"], "\n".join(rep["errors"])
    assert len(d["payloads"]) == 36
    assert d["redraw"]["ids"] == ck.redraw_ids(v2)
    # the builder reproduces the committed file byte for byte
    assert json.dumps(wr.build({"payloads": v2}), indent=1, ensure_ascii=False) + "\n" == COMMITTED.read_text(encoding="utf-8")
