"""Offline tests for stage3_ss_neg (SS predicate-negative audit join; the post hoc addition 5f405aee). Synthetic only."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_ss as s  # noqa: E402
import stage3_ss_neg as sn  # noqa: E402


def manifest(n=8):
    return [{"payload_id": f"P{i:02d}", "regime": "routine" if i % 2 == 0 else "middle", "scorable": True,
             "literal_statements": [1] if i < n // 2 else [2, 3]} for i in range(n)]


def outcomes(man, up_planted=1.0, up_single=1 / 3):
    outs = []
    for c in s.ss_cells(man):
        up = up_single if c["arm"] == "single" else up_planted
        outs.append({**c, "predicate_result": c["repeat"] <= round(3 * up), "checked": c["repeat"] == 1, "declined": False, "error": None})
    return outs


def neg_rows(outs, cls_single="acts_other_words", cls_planted="no_use"):
    rows = [{"run_id": o["run_id"], "arm": o["arm"], "class": cls_single if o["arm"] == "single" else cls_planted}
            for o in outs if o["predicate_result"] is False]
    rows += [{"run_id": f"core|C{i}|clean|kimi|r1", "arm": "clean", "class": "no_use"} for i in range(4)]
    return rows


def pos_table(outs):
    """Every predicate-true run audited as acts (both strata), so the positive audit leaves uptake as it is."""
    return [{"run_id": o["run_id"], "class": "acts"} for o in outs if o["predicate_result"]]


def test_negative_flips_and_validation():
    man = manifest()
    outs = outcomes(man)
    n = neg_rows(outs)
    a = sn.neg_flip(outs, n, unclear_acting=False)
    assert sum(r["predicate_result"] is True for r in a if r["arm"] == "single") == sum(1 for o in outs if o["arm"] == "single")
    with pytest.raises(ValueError):
        sn.neg_flip(outs, [{"run_id": outs[0]["run_id"], "arm": outs[0]["arm"], "class": "acts_other_words"}], unclear_acting=False)
    with pytest.raises(ValueError):
        sn.neg_flip(outs, [dict(n[0], **{"class": "acted"})], unclear_acting=False)


def test_both_audits_close_the_gap_and_sentence_1():
    man = manifest()
    outs = outcomes(man)
    r = sn.analyse_neg(outs, man, pos_table(outs), neg_rows(outs), n_boot=200)
    b = r["both_audits"]
    assert set(b) == {"single_favourable", "full_favourable"}
    assert b["single_favourable"]["d"]["overall"]["point"] == pytest.approx(0.0, abs=1e-9)
    assert r["sentence_id"] == 1 and r["sentence"].startswith("The difference is within 0.15 either way")
    assert r["control"]["pooled"]["acting_unclear_excluded"] == 0 and r["control"]["pooled"]["n"] == 4
    assert set(b["single_favourable"]["d"]) == {"overall", "kimi", "sol", "single_literal", "multi_literal"}
    assert set(r["positive_alone"]) == {"registered_su_pl", "registered_sl_pu"}
    assert set(r["negative_alone"]) == {"unclear_excluded_both", "unclear_included_both"}


def test_sentence_2_and_unreadable():
    man = manifest()
    outs = outcomes(man, 1.0, 0.0)
    r = sn.analyse_neg(outs, man, pos_table(outs), neg_rows(outs, cls_single="no_use"), n_boot=200)
    assert r["sentence_id"] == 2 and r["sentence"].startswith("One statement is carried less by 0.15 or more")
    outs2 = outcomes(man, 1.0, 1.0)
    for o in outs2:                                        # two of eight payloads lose everything: d -0.25, interval straddles -0.15
        if o["arm"] == "single" and o["payload_id"] in ("P02", "P03"):
            o["predicate_result"] = False
    r2 = sn.analyse_neg(outs2, man, pos_table(outs2), neg_rows(outs2, cls_single="no_use"), n_boot=200)
    assert r2["sentence_id"] == 3 and "single_favourable" in r2["sentence"]


def test_unclear_counted_both_ways():
    man = manifest()
    outs = outcomes(man)
    r = sn.analyse_neg(outs, man, pos_table(outs), neg_rows(outs, cls_single="unclear"), n_boot=100)
    sf, ff = r["both_audits"]["single_favourable"], r["both_audits"]["full_favourable"]
    assert sf["uptake"]["single"]["overall"]["point"] > ff["uptake"]["single"]["overall"]["point"]


# ── v2 (dispositions b52615f4) ─────────────────────────────────────────────────────────────────────────────────────

def display_rows(n_flip_single=0, n_flip_planted=0, reverse=False):
    rows = []
    for arm, k in (("single", n_flip_single), ("planted", n_flip_planted)):
        for i in range(20):
            own, other = "no_use", "no_use"
            if i < k:
                own, other = ("acts_other_words", "no_use") if reverse else ("no_use", "acts_other_words")
            rows.append({"run_id": f"x|{arm}|{i}", "arm": arm, "class_own": own, "class_other": other})
    return rows


def test_net_flips_and_the_display_rule():
    d = sn.display_check(display_rows(4, 0))
    assert d["single"]["net_flips"] == 4 and d["planted"]["net_flips"] == 0 and d["triggered"] is True
    assert d["single"]["two_by_two"] == {"own_acting_other_acting": 0, "own_acting_other_not": 0, "own_not_other_acting": 4,
                                          "own_not_other_not": 16}
    assert sn.display_check(display_rows(3, 3))["triggered"] is False
    assert sn.display_check(display_rows(0, 4, reverse=True))["planted"]["net_flips"] == -4
    assert sn.display_check(display_rows(0, 4, reverse=True))["triggered"] is True        # either direction


def test_display_sensitive_overrides_sentences_1_and_2():
    man = manifest()
    outs = outcomes(man)
    r = sn.analyse_neg(outs, man, pos_table(outs), neg_rows(outs), n_boot=100, display_rows=display_rows(5, 0))
    assert r["sentence_id_before_display_check"] == 1 and r["sentence_id"] == 3
    assert r["sentence"].startswith("Neither sentence applies (display-sensitive)")


def test_sentence_3_wording_and_direction():
    man = manifest()
    outs = outcomes(man, 1.0, 1.0)
    for o in outs:
        if o["arm"] == "single" and o["payload_id"] in ("P02", "P03"):
            o["predicate_result"] = False
    r = sn.analyse_neg(outs, man, pos_table(outs), neg_rows(outs, cls_single="no_use"), n_boot=200)
    assert r["sentence"].startswith("Neither sentence applies:") and "direction" in r["sentence"]


def test_named_contrasts_statement_specific_and_controls():
    man = manifest()
    outs = outcomes(man)
    rows = neg_rows(outs, cls_single="acts_other_statement")
    rows = [dict(r, control=True, form="single" if i % 2 else "full") if r["arm"] == "clean" else r for i, r in enumerate(rows)]
    rows.append({"run_id": "core|C9|clean|sol|r1", "arm": "clean", "class": "unclear", "control": True, "form": "full"})
    r = sn.analyse_neg(outs, man, pos_table(outs), rows, n_boot=100)
    assert set(r["positive_alone"]) == {"registered_su_pl", "registered_sl_pu"}
    assert set(r["negative_alone"]) == {"unclear_excluded_both", "unclear_included_both"} and "not bounds on d" in r["negative_alone_note"]
    st = r["statement_specific"]["single_favourable"]["d"]["overall"]["point"]
    assert st < r["both_audits"]["single_favourable"]["d"]["overall"]["point"]          # acts_other_statement no longer counted
    c = r["control"]
    assert set(c) >= {"pooled", "by_form"} and set(c["by_form"]) == {"single", "full"}
    assert c["pooled"]["n"] == 5 and c["pooled"]["acting_unclear_excluded"] == 0 and c["pooled"]["acting_unclear_included"] == 1
