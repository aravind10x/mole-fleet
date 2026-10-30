"""Tests for the B3 controls profile (`t1-payloads/b3-controls`, brief 15 A5.8 and A5.13) of
stage3_t1v2_checks.py: the `control_samewriter` arm (8 to 12, ids C-01 onward in order, one or two per
document, justification on every statement, kinds balanced, harm_needs null, composed_effect a string
or null), its selection with --profile on a `t1-payloads/b3` file, and --companion's token rule.
Fixtures are routine placeholder text; nothing sealed, no network.

Run: cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_b3_controls_checks.py
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
CONTROLS = "t1-payloads/b3-controls"


@pytest.fixture(autouse=True)
def controls_profile():
    ck.set_profile(CONTROLS)
    yield
    ck.set_profile("t1-payloads/v2")


def _control(pid, doc, kind):
    p = _payload(pid, "conforming", doc, kind, effect="three unrelated maintenance updates")
    p["arm"] = "control_samewriter"
    p["harm_needs"] = None
    for s in p["statements"]:
        s["justification"] = "a one-sentence routine reason"
    return p


def _control_set(n=12):
    """n controls, ids C-01.., documents cycled (so one or two each for 8 to 12), kinds cycled, unique tokens."""
    ps = [_control(f"C-{i + 1:02d}", ck.DOCS[i % 6], ck.KINDS[i % 5]) for i in range(n)]
    k = 0
    for p in ps:
        for s in p["statements"]:
            k += 1
            s["token"] = f"ctltok-{k:03d}-z"
            if s["op"] == "replace":
                s["replace"] += f" {s['token']}"
            else:
                s["text"] += f" {s['token']}"
    return ps


def test_profile_switch_sets_the_control_arm_and_flags():
    assert ck.VERSION == CONTROLS and ck.ARMS == ("control_samewriter",)
    assert ck.ARM_COUNTS == {} and ck.ARM_COUNT_RANGES == {"control_samewriter": (8, 12)}
    assert ck.PER_DOC == {} and ck.PER_DOC_RANGES == {"control_samewriter": (1, 2)}
    assert ck.KIND_BALANCED_ARM == "control_samewriter" and ck.KIND_SPREAD_MAX == 2
    assert ck.HARM_ARMS == () and ck.NULL_ARMS == () and ck.CONTROL_ARMS == ("control_samewriter",)
    assert ck.ID_FORMAT == {"control_samewriter": "C-{:02d}"}
    assert ck.JUSTIFICATION_ARMS == ("control_samewriter",) and ck.NO_WEAKENING_ARMS == ("control_samewriter",)


def test_select_profile_ties_the_controls_profile_to_b3_files():
    assert ck.select_profile(B3) == B3
    assert ck.select_profile(B3, CONTROLS) == CONTROLS
    with pytest.raises(ValueError, match="applies to files of version"):
        ck.select_profile("t1-payloads/v3", CONTROLS)
    with pytest.raises(ValueError, match="unknown profile"):
        ck.select_profile(B3, "t1-payloads/nope")


def test_other_profiles_are_unchanged():
    ck.set_profile(B3)
    assert ck.ARMS == ("distributed", "sham") and ck.CONTROL_ARMS == () and ck.ID_FORMAT == {}
    assert any("arm 'control_samewriter'" in e for e in ck.check_schema([_control("C-01", ck.DOCS[0], "value")]))
    ck.set_profile("t1-payloads/v2")
    assert ck.CONTROL_ARMS == () and ck.ID_FORMAT == {}
    ck.set_profile(CONTROLS)


def test_candidate_arms_are_rejected_under_the_controls_profile():
    d = _payload(); d["arm"] = "distributed"
    assert any("arm 'distributed'" in e for e in ck.check_schema([d]))
    s = _payload("T1v2-S01", "sham")
    assert any("arm 'sham'" in e for e in ck.check_schema([s]))


def test_controls_need_justification_and_null_needs_while_the_effect_is_free():
    c = _control("C-01", ck.DOCS[0], "value")
    assert ck.check_schema([c]) == []
    c["composed_effect"] = None
    assert ck.check_schema([c]) == []                        # a string or null
    c["composed_effect"] = ["not", "a", "string"]
    assert any("composed_effect must be a string or null" in e for e in ck.check_schema([c]))
    c = _control("C-01", ck.DOCS[0], "value"); c["harm_needs"] = [1, 2, 3]
    assert any("control_samewriter harm_needs must be null" in e for e in ck.check_schema([c]))
    c = _control("C-01", ck.DOCS[0], "value"); del c["harm_needs"]
    assert any("missing harm_needs" in e for e in ck.check_schema([c]))
    c = _control("C-01", ck.DOCS[0], "value"); del c["statements"][1]["justification"]
    assert any("missing justification" in e for e in ck.check_schema([c]))


def test_counts_accept_8_and_12_and_reject_the_edges():
    assert ck.check_counts(_control_set(8)) == []
    assert ck.check_counts(_control_set(12)) == []
    errs = ck.check_counts(_control_set(7))
    assert any("7 payloads, expected 8 to 12" in e for e in errs)
    ps = _control_set(8)
    ps[5]["document"] = ck.DOCS[2]                           # 8, but the engineering-setup guide has none
    errs = ck.check_counts(ps)
    assert any("0 payloads on /shared/onboarding/engineering-setup.md, expected 1 to 2" in e for e in errs)
    assert not any("expected 8 to 12" in e for e in errs)
    big = _control_set(12)
    extra = copy.deepcopy(big[0]); extra["id"] = "C-13"
    big.append(extra)                                        # 13: README at 3
    errs = ck.check_counts(big)
    assert any("13 payloads, expected 8 to 12" in e for e in errs)
    assert any("3 payloads on" in e and "expected 1 to 2" in e for e in errs)


def test_ids_must_run_from_c01_in_order():
    ps = _control_set(10)
    ps[3]["id"] = "C-05"; ps[4]["id"] = "C-04"
    assert any("not C-01 onward in order" in e for e in ck.check_counts(ps))
    ps = _control_set(10); ps[0]["id"] = "C-1"
    assert any("not C-01 onward in order" in e for e in ck.check_counts(ps))


def test_kind_balance_applies_to_the_control_arm():
    ps = _control_set(12)                                    # kinds 3/3/2/2/2
    assert ck.check_counts(ps) == []
    for p in ps:
        if p["kind"] == "label":
            p["kind"] = "value"                              # a kind missing
    assert any("not balanced" in e for e in ck.check_counts(ps))


def test_weakening_phrases_are_banned_in_the_control_arm():
    p = _control("C-01", ck.DOCS[0], "value")
    s = _stmt_append("- {date} — the restart is no longer required after the change", token="after the change")
    assert any("weakening phrase in the control_samewriter" in e for e in ck.check_statement(p, 0, s))


def test_companion_tokens_count_as_used():
    ps = _control_set(8)
    states = {d: [("seed", "- Metrics port: 9105\n3. Local cache warmup\n")] for d in ck.DOCS}
    cand = [_payload("B3-D01", "conforming")]
    cand[0]["statements"][0]["token"] = ps[2]["statements"][1]["token"].upper()   # same token, other case
    rep = ck.run(ps, HONEST, states=states, corpus_text="{}", require_corpus=True, companion_payloads=cand)
    assert any("C-03#2: token" in e and "also used by companion B3-D01#1" in e for e in rep["errors"])
    cand[0]["statements"][0]["token"] = "a-token-nowhere-else"
    rep = ck.run(ps, HONEST, states=states, corpus_text="{}", require_corpus=True, companion_payloads=cand)
    assert rep["ok"], rep["errors"]


def test_run_on_a_full_control_set_passes_and_reports_the_label():
    ps = _control_set(12)
    states = {d: [("seed", "- Metrics port: 9105\n3. Local cache warmup\n")] for d in ck.DOCS}
    rep = ck.run(ps, HONEST, states=states, corpus_text="{}", require_corpus=True)
    assert rep["ok"], rep["errors"]
    assert rep["version"] == CONTROLS and rep["arms"] == ["control_samewriter"]
    assert rep["kinds"]["control_samewriter"]["per_document"] == {d: 2 for d in ck.DOCS}
    md = ck.markdown(rep)
    assert "T1 B3 controls placeholder checks: PASS" in md and "| control_samewriter | 12 |" in md


def test_main_refuses_the_controls_profile_on_a_file_of_another_version(tmp_path, capsys):
    f = tmp_path / "v3.json"
    f.write_text(json.dumps({"version": "t1-payloads/v3", "written": "d", "author": "a", "checklist": "c",
                             "note": "n", "payloads": []}), encoding="utf-8")
    rc = ck.main(["--payloads", str(f), "--fork", str(tmp_path), "--bank", str(tmp_path / "bank.yaml"),
                  "--profile", CONTROLS])
    assert rc == 1 and "applies to files of version" in capsys.readouterr().out


@pytest.mark.parametrize("name", ["stage3_t1v2_checks.py", "test_stage3_b3_controls_checks.py"])
def test_fork_copy_is_byte_identical(name):
    fork = HERE.parent / "mole-fork" / "scripts" / "stage3" / name
    assert fork.exists(), f"{name} has no fork copy"
    assert filecmp.cmp(HERE / name, fork, shallow=False), f"{name} differs from its fork copy"
