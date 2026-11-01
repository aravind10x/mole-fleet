"""Offline tests for stage3_b3_comprehension_report (brief 25 C3): synthetic fixtures and a fake run only.

    cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_b3_comprehension_report.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_b3_comprehension as bc  # noqa: E402
import stage3_b3_comprehension_report as br  # noqa: E402
import stage3_legibility as lg  # noqa: E402
import test_stage3_b3_comprehension as tb  # noqa: E402

b3 = tb.b3   # the fixture


def _items(b3fix, kind="mean", threshold=0.5):
    items, rubrics, tr = b3fix
    return {**items, "config": {"sol_rule": {"kind": kind, "threshold": threshold}}}


def _comp(items):
    return {r["item_id"]: {"composition": 50.0, "composition_p1": 50.0, "composition_p2": 50.0, "rater_top_line": 40.0,
                           "rater_top_two_gap": 5.0, "replace_share": 1 / 3} for r in items["items"] if r["regime"] == "candidate"}


def _leaky(b3fix):
    return {i for i, e in b3fix[1]["rubric"].items() if "LEAKY" in e}


def test_rule_holds():
    assert br.rule_holds([0, 0], {"kind": "every"}) and not br.rule_holds([0, 0.5], {"kind": "every"})
    assert br.rule_holds([0, 1], {"kind": "mean", "threshold": 0.5}) and not br.rule_holds([0.5, 1], {"kind": "mean", "threshold": 0.5})
    assert br.rule_holds([0, 0, 1], {"kind": "majority"}) and not br.rule_holds([0, 1], {"kind": "majority"})


def test_membership_is_a_conjunction_with_not_evaluable_kept_apart():
    q = lambda v: {"quiet": v}  # noqa: E731
    assert br.membership({"kimi": q(True), "sol": q(True)}, ("kimi", "sol")) == "quiet"
    assert br.membership({"kimi": q(False), "sol": q(None)}, ("kimi", "sol")) == "not_quiet"
    assert br.membership({"kimi": q(True), "sol": q(None)}, ("kimi", "sol")) == "not_evaluable"


def test_report_on_a_fake_run_finds_the_non_leaking_candidates(tmp_path, b3):
    rows, rec, *_ = tb.fake_run(tmp_path, b3)
    items = _items(b3)
    plan = {"choice": {"sol_rule": items["config"]["sol_rule"], "p_labelled_quiet_given_quiet": 0.5, "ci95": [0.1, 0.7],
                       "p_labelled_quiet_given_not_quiet": 0.01, "ci95_not_quiet": [0.0, 0.03]},
            "t1_expectation_only": {"model_expected_share_at_choice": 0.2}}
    res = br.build_report(rec, items, plan, _comp(items))
    leaky = _leaky(b3)
    cands = {r["item_id"] for r in rows if r["regime"] == "candidate"}
    assert res["stratum"]["ids"] == sorted(cands - leaky) and res["stratum"]["n"] == 2
    assert res["stratum"]["by_writer"] == {"glm53": 1, "sonnet55": 1}
    assert res["stratum"]["ids_sha256"] == lg.sha256("\n".join(sorted(cands - leaky)))
    assert res["stratum"]["whole_credit_among_quiet"]["D_whole_positive_both_readers"] == 2
    for f in bc.PLAN_READERS:
        for g in ("control", "sham", "pooled"):
            if g in res["nulls"][f]:
                assert res["nulls"][f][g]["P_D_part_pos_per_cell"] == 0.0 and res["nulls"][f][g]["P_D_whole_pos_per_cell"] == 0.0
        assert res["sample_agreement"][f]["quiet_flips"] == 0
    assert res["nulls"]["kimi"]["sham"]["paired_sample0"]["P_D_part_pos"] == 0.0
    assert res["positive_control"]["kimi"]["D_whole_own"] == 1.0 and res["positive_control"]["sol"]["D_part_own"] == 1.0
    assert res["not_evaluable"]["kimi"]["n"] == 0 and res["refusal_counts"] == {f: 0 for f in bc.PLAN_READERS}
    assert res["kappa"]["kimi"]["kappa"] is None or res["kappa"]["kimi"]["agreement"] == 1.0
    per = res["items"]
    some = sorted(cands - leaky)[0]
    assert per[some]["readers"]["kimi"]["D_part"] == [0.0, 0.0] and per[some]["composition"] == 50.0
    lg.check_safe({k: v for k, v in res.items() if k not in ("plan",)})
    md = br.render_md({**res, "cache_sha256": {"kimi": "h"}, "dollars": {"total": 0.0}, "estimate_usd": 1.0,
                       "hashes": {"items_v0": "h", "rubrics": "h", "stratum_plan": "h", "config": "h", "script_at_items": "h", "report_script": "h"}})
    assert "**Comprehension-quiet stratum (A6.14.2): 2 of the 6" in md
    for eff in b3[1]["rubric"].values():
        assert eff not in md and eff not in json.dumps(res)


def test_a_refused_part_makes_the_item_not_evaluable_under_that_reader(tmp_path, b3):
    leaky = _leaky(b3)
    target = next(i for i, e in b3[1]["rubric"].items() if i not in leaky)
    n = b3[1]["rubric"][target].split("-D")[1][:2]
    rows, rec, *_ = tb.fake_run(tmp_path, b3, declined_item_token=f"TOK-T1v8-D{n}")
    items = _items(b3)
    plan = {"choice": {"sol_rule": items["config"]["sol_rule"], "p_labelled_quiet_given_quiet": 0.5, "ci95": None,
                       "p_labelled_quiet_given_not_quiet": 0.01, "ci95_not_quiet": None},
            "t1_expectation_only": {"model_expected_share_at_choice": 0.2}}
    res = br.build_report(rec, items, plan, _comp(items))
    assert res["items"][target]["membership"] == "not_evaluable"
    assert res["items"][target]["readers"]["kimi"]["not_evaluable_reason"] == "refused_token"
    assert res["items"][target]["readers"]["sol"]["quiet"] is True
    assert target in res["not_evaluable"]["kimi"]["ids"] and res["stratum"]["n"] == 1
    assert res["refusal_counts"]["kimi"] == 2


def _t1_fixture():
    t1_items = {"items": [{"item_id": "a1" * 32, "regime": "v2_conforming", "payload_ref": {"file": "v2", "id": "T1v2-C01"}},
                          {"item_id": "b2" * 32, "regime": "v3_middle", "payload_ref": {"file": "v3", "id": "T1v3-M01"}},
                          {"item_id": "c3" * 32, "regime": "control", "payload_ref": {"file": "v2", "id": "T1v2-S01"}}]}
    triples, key, ratings, sts = [], {"statements": {}}, {"statements": {}}, []
    scores = {"a1": [20, 50, 70], "b2": [30, 55, 90]}
    for iid, (file, arm, pid) in (("a1", ("work/x/payloads-v2.json", "conforming", "T1v2-C01")), ("b2", ("payloads-v3.json", "middle", "T1v3-M01"))):
        lines = [{"op": "append", "anchor_or_region": "end of document", "text": f"{iid} line {j}"} for j in range(3)]
        triples.append({"triple_id": iid * 32, "document": "/d", "statements": list(reversed(lines))})
        for j, st in enumerate(lines):
            sid = f"s-{iid}-{j}"
            key["statements"][sid] = {"file": file, "arm": arm, "payload_id": pid, "statement_index": j}
            ratings["statements"][sid] = {"pass1": {"score": scores[iid][j]}, "pass2": {"score": scores[iid][j] + 10}}
            sts.append({"statement_id": sid, **st})
    # per part: a1 parts in triple order are lines 2, 1, 0; b2 likewise
    pp = {}
    vals = {"kimi": {"a1": [1.0, 0.0, 1.0], "b2": [0.0, 1.0, 0.0]}, "sol": {"a1": [0.5, 0.0, 1.0], "b2": [0.0, 1.0, None]},
            "sonnet55": {"a1": [0.0, 0.0, 1.0], "b2": [0.0, 0.0, 0.0]}}
    for f, per in vals.items():
        pp[f] = {}
        for iid, v in per.items():
            pp[f][iid * 32] = {"r0": {c: {"score": x, "status": "scored" if x is not None else "refused_provider"} for c, x in zip(bc.PARTS, v)}}
    return pp, t1_items, triples, key, ratings, sts


def test_t1_join_matches_lines_by_their_fields_and_counts_yields():
    pp, t1_items, triples, key, ratings, sts = _t1_fixture()
    lines = br.t1_line_join(pp, t1_items, triples, key, ratings, sts)
    assert len(lines) == 6
    a = [x for x in lines if x["item_id"] == "a1" * 32]
    assert [x["rater_p1"] for x in a] == [70, 50, 20] and a[0]["rater_mean"] == 75     # part0 is line 2
    s = br.join_summary(lines, ["kimi", "sol", "sonnet55"])
    # at or under 60 (two-pass mean): a1 lines 0 (25) and 1 (55), b2 lines 0 (35); b2 line 1 is 60 -> also included
    q = s["pooled"]["at_or_under_60"]
    assert q["n_lines"] == 4 and q["n_with_two_families"] == 4
    # a1 line 0 (part2): kimi 1, sol 1, sonnet 1 -> yields; a1 line 1 (part1): none; b2 line 0 (part2): kimi 0, sol None -> not;
    # b2 line 1 (part1): kimi 1, sol 1 -> yields
    assert q["n_yield_alone"] == 2 and q["share"] == 0.5
    assert s["v2_conforming"]["n_lines"] == 3 and s["pooled"]["spearman_line_score_vs_D_part_line"]["kimi"]["n"] == 6
    assert s["pooled"]["spearman_line_score_vs_D_part_line"]["sol"]["n"] == 5


def test_t1_join_refuses_an_ambiguous_or_missing_line():
    pp, t1_items, triples, key, ratings, sts = _t1_fixture()
    sts[0]["text"] = "something else"
    with pytest.raises(ValueError, match="matches 0"):
        br.t1_line_join(pp, t1_items, triples, key, ratings, sts)
