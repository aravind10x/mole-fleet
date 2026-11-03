"""Tests for stage3_t1v2_checks_r2.py (brief 30, Part 1b; note 4 item 2 (i) as note 5 amends it).
The checks module stays byte-identical at its pinned hash (asserted here, the judge_openrouter_pin
precedent); round 2's profile is defined in the new module, registered and selected explicitly by
every entry point (never by the file header alone), and is named by the converter's own file
header. The profile carries no `justification`, no kind balance and no sham arm (B3's constraints
are not carried, since round 2's items are what the writers wrote), and its count range is the
converter's own output range per writer per round (0 to the cap 96). Fixtures are the converter's
synthetic writer file (made up; no real item); assertions are on keys, counts and report flags, so
no item text is printed on failure.

Run: cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_t1v2_checks_r2.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_convert as cv  # noqa: E402
import stage3_t1v2_checks as t1v2  # noqa: E402
import stage3_t1v2_checks_r2 as r2  # noqa: E402

# brief 30, note 5: the checks module stays byte-identical here (four records cite it by hash)
T1V2_CHECKS_SHA256 = "c0fe68c566276bef1d76431a7e8577143d245e2ca4b0689c04bd11c27332e023"
# captured after the new module's import: its import binds nothing in the checks module
T1V2_VERSION_AT_IMPORT = t1v2.VERSION
T1V2_PROFILES_AT_IMPORT = copy.deepcopy(t1v2.PROFILES)

V6_STATE = cv.STATE_ONE


# ── fixtures ─────────────────────────────────────────────────────────────────────────────────────

def _converted(tmp_path: Path) -> Path:
    """The synthetic writer file converted into tmp_path/out (the one-document arm's payloads)."""
    out = tmp_path / "out"
    if not (out / "key.json").exists():
        wf = tmp_path / "writer-answer.json"
        if not wf.exists():
            wf.write_text(json.dumps(cv.synthetic_writer_file(), indent=1), encoding="utf-8")
        cv.convert_file(wf, cv.STATE_ONE, out_dir=out, writer="synthetic", synthetic=True,
                        state_cross=cv.STATE_CROSS)
    return out


def _payloads(out: Path) -> list[dict]:
    return json.loads((out / "payloads.json").read_text(encoding="utf-8"))["payloads"]


def _honest() -> dict[str, str]:
    return t1v2.honest_texts(cv.FORK, cv.BANK, cv.TEMPLATE)


# ── the unchanged checks module and the explicit selection ───────────────────────────────────────

def test_the_checks_module_is_unchanged():
    assert hashlib.sha256((HERE / "stage3_t1v2_checks.py").read_bytes()).hexdigest() == T1V2_CHECKS_SHA256


def test_the_import_binds_nothing_and_the_existing_profiles_are_unchanged():
    assert T1V2_VERSION_AT_IMPORT == "t1-payloads/v2"
    assert r2.PROFILE not in T1V2_PROFILES_AT_IMPORT
    for name, profile in T1V2_PROFILES_AT_IMPORT.items():
        assert t1v2.PROFILES[name] == profile, name
    r2.select_r2()
    assert sorted(t1v2.PROFILES) == sorted([*T1V2_PROFILES_AT_IMPORT, r2.PROFILE])
    t1v2.set_profile("t1-payloads/v2")            # restore the import-time profile


def test_selection_is_explicit_and_binds_round_2s_rules():
    r2.select_r2()
    assert t1v2.VERSION == r2.PROFILE
    assert t1v2.ARMS == (r2.APP_ARM,) and t1v2.JUSTIFICATION_ARMS == ()
    assert t1v2.HARM_ARMS == (r2.APP_ARM,) and t1v2.NULL_ARMS == ()
    assert t1v2.KIND_BALANCED_ARM is None and t1v2.NO_WEAKENING_ARMS == (r2.APP_ARM,)
    t1v2.set_profile("t1-payloads/v2")


# ── the profile is named by the converter's own file header; the arm is the converter's ──────────

def test_the_profile_is_named_by_the_converters_file_header(tmp_path):
    out = _converted(tmp_path)
    d = json.loads((out / "payloads.json").read_text(encoding="utf-8"))
    assert d["version"] == r2.PROFILE == cv.VERSION
    assert {p["arm"] for p in d["payloads"]} == {r2.APP_ARM} == {cv.APP_ARM}
    r2.check_file(d)                              # the converted header is accepted


def test_the_header_rule(tmp_path):
    out = _converted(tmp_path)
    good = json.loads((out / "payloads.json").read_text(encoding="utf-8"))
    r2.check_file(good)
    with pytest.raises(r2.UsageError):
        r2.check_file({**good, "version": "t1-payloads/b3"})
    with pytest.raises(r2.UsageError):
        r2.check_file({"version": r2.PROFILE, "payloads": "not a list"})
    pair_file = json.loads((out / "payloads-pairs.json").read_text(encoding="utf-8"))
    with pytest.raises(r2.UsageError):
        r2.check_file(pair_file)                  # the pair payload form is not this module's schema


# ── the two-sided test: the field absent passes under round 2, B3 refuses for it ─────────────────

def test_a_converted_file_passes_under_round_2s_profile_with_the_field_absent(tmp_path):
    out = _converted(tmp_path)
    payloads = _payloads(out)
    assert all("justification" not in s for p in payloads for s in p["statements"])
    rep = r2.run_r2(payloads, _honest(), require_corpus=False)
    assert rep["ok"], rep["errors"]
    assert rep["version"] == r2.PROFILE and rep["arms"] == [r2.APP_ARM]


def test_the_same_payloads_under_b3s_profile_are_refused_for_justification(tmp_path):
    out = _converted(tmp_path)
    payloads = _payloads(out)
    before = t1v2.VERSION
    t1v2.set_profile("t1-payloads/b3")
    try:
        errs = t1v2.check_schema(payloads)
        assert errs and all("missing justification" in e for e in errs)
        assert len(errs) == 3 * len(payloads)     # every statement, and nothing else
        rep = t1v2.run(payloads, _honest(), require_corpus=False)
        assert rep["ok"] is False and any("missing justification" in e for e in rep["errors"])
    finally:
        t1v2.set_profile(before)


# ── B3's kind-balance and sham constraints are not carried ───────────────────────────────────────

def test_b3s_kind_balance_is_not_carried(tmp_path):
    out = _converted(tmp_path)
    payloads = _payloads(out)
    kinds = Counter(p["kind"] for p in payloads)
    assert min(kinds.get(k, 0) for k in t1v2.KINDS) == 0     # a kind is absent in what the writers wrote
    before = t1v2.VERSION
    t1v2.set_profile("t1-payloads/b3")
    try:
        assert any("not balanced" in e for e in t1v2.check_counts(payloads))
    finally:
        t1v2.set_profile(before)
    r2.select_r2()
    assert t1v2.check_counts(payloads) == []


def test_b3s_sham_arm_is_not_carried(tmp_path):
    assert r2.R2_PROFILE["arms"] == (r2.APP_ARM,) and "sham" not in r2.R2_PROFILE["arms"]
    assert r2.R2_PROFILE["null_arms"] == () and r2.R2_PROFILE["arm_counts"] == {}
    out = _converted(tmp_path)
    rep = r2.run_r2(_payloads(out), _honest(), require_corpus=False)
    assert rep["ok"] and set(rep["kinds"]) == {r2.APP_ARM}


# ── the count range is the converter's own output range ──────────────────────────────────────────

def test_the_count_range_is_the_converters_output_range():
    assert r2.ROUND_CAP == 96                    # the cap per arm per writer per writer round
    assert r2.R2_PROFILE["arm_count_ranges"] == {r2.APP_ARM: (0, r2.ROUND_CAP)}

    def payloads(n: int) -> list[dict]:
        return [{"arm": r2.APP_ARM, "document": t1v2.DOCS[0], "kind": "value"} for _ in range(n)]

    r2.select_r2()
    assert t1v2.check_counts(payloads(0)) == []   # every item can fail the funnel
    assert t1v2.check_counts(payloads(96)) == []
    errs = t1v2.check_counts(payloads(97))
    assert any("expected 0 to 96" in e for e in errs)


# ── the checks module's own rules still refuse a bad payload ────────────────────────────────────

def test_a_payload_missing_its_token_is_refused(tmp_path):
    out = _converted(tmp_path)
    payloads = _payloads(out)
    del payloads[0]["statements"][0]["token"]
    rep = r2.run_r2(payloads, _honest(), require_corpus=False)
    assert rep["ok"] is False and any("missing token" in e for e in rep["errors"])


# ── the corpus path (the W3 command's semantics, the round-2 brief's corpus) ────────────────────

def test_the_corpus_path_runs_under_round_2s_profile(tmp_path):
    out = _converted(tmp_path)
    payloads = _payloads(out)
    v6 = cv.parse_doc_states(V6_STATE.read_text(encoding="utf-8"))
    states = {d: [("seed", v6[d])] for d in t1v2.DOCS}
    rep = r2.run_r2(payloads, _honest(), states=states, corpus_text="{}", require_corpus=True)
    assert rep["ok"], rep["errors"]
    assert "corpus_args" in rep["honest_texts_checked"] and "document_states" in rep["honest_texts_checked"]
    assert rep["anchors"] and all(a["ok"] for a in rep["anchors"])
    states[t1v2.DOCS[0]] = [("seed", "a line the file anchors nothing on\n")]
    rep2 = r2.run_r2(payloads, _honest(), states=states, corpus_text="{}", require_corpus=True)
    assert rep2["ok"] is False and any("absent in" in e for e in rep2["errors"])


def test_the_cli_refuses_without_a_corpus(tmp_path):
    out = _converted(tmp_path)
    md = tmp_path / "out.md"
    rc = r2.main(["--payloads", str(out / "payloads.json"), "--fork", str(cv.FORK),
                  "--bank", str(cv.BANK), "--out-md", str(md)])
    assert rc == 1
    text = md.read_text(encoding="utf-8")
    assert "FAIL" in text and "incomplete" in text and "round 2" in text