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
    assert r["control"]["acting"] == 0 and r["control"]["n"] == 4
    assert set(b["single_favourable"]["d"]) == {"overall", "kimi", "sol", "single_literal", "multi_literal"}
    assert set(r["positive_alone"]) == {"su_pl", "sl_pu"} and set(r["negative_alone"]) == {"unclear_not_acting", "unclear_acting"}


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
