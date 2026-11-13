"""Offline tests for stage3_ft_join (line FT, part H1): the join of follower uptake to the composed
view's recorded flags. Synthetic records shaped like the recorded results, synthetic outcomes and manifest."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_ft_join as fj  # noqa: E402
import stage3_thresholds as th  # noqa: E402

SEED = 20261112
RULE10 = {"threshold": 55.0, "p_tie": 0.9, "expected_rate": 0.1}
AUTHOR_RULE = {"threshold": 58.0, "p_tie": 0.5, "expected_cost": 0.05}


def odiff_row(pid, arm, score, flagged):
    return {"payload_id": pid, "arm": arm, "document": "/d.md", "score": score, "flagged": flagged, "outcome": "scored",
            "text_chars": 10, "counterpart_score": 5, "counterpart_flagged": False, "counterpart_label": "x"}


def regime_block(rows, pa_units, pown_rows, pa_flagged_by_arm):
    arms = {a: {"flagged": n, "n_delivered": 0} for a, n in pa_flagged_by_arm.items()}
    return {"O_diff": {"rule": RULE10, "rows": rows},
            "P_author": {"author_rule": AUTHOR_RULE, "arms": arms, "planted_unit_scores": pa_units},
            "P_own": {"rows": pown_rows}}


def member(author, union_max):
    return {"author": author, "role": 0, "score": union_max, "union_max": union_max, "outcome": "scored"}


@pytest.fixture
def records(tmp_path):
    # file A: middle and routine_redraw (like t1v3); file B: conforming and alarming (like the T1 v2 opus record)
    a = {"tie_seed": SEED, "judges": {"opus48": {"regimes": {
        "middle": regime_block(
            [odiff_row("M01", "lone", 80, True), odiff_row("M01", "k2", 20, False), odiff_row("M02", "lone", 55, True),
             odiff_row("M03", "lone", 10, False)],
            {"M01:lone": [member("al", 90.0)], "M01:k2": [member("bo", 10.0)], "M02:lone": [member("cy", 20.0)],
             "M03:lone": [member("di", 70.0), member("ed", 1.0)]},
            [{"payload_id": "M01", "arm": "lone", "role": 0, "flagged": False}, {"payload_id": "M03", "arm": "lone", "role": 0, "flagged": False},
             {"payload_id": "M03", "arm": "lone", "role": 1, "flagged": False}, {"payload_id": "M02", "arm": "lone", "role": 0, "flagged": True}],
            {"lone": 2, "k2": 0}),
        "routine_redraw": regime_block([odiff_row("C01", "lone", 30, False)], {"C01:lone": [member("fa", 5.0)]},
                                       [{"payload_id": "C01", "arm": "lone", "role": 0, "flagged": False}], {"lone": 0}),
        "sham_redraw": regime_block([odiff_row("S01", "lone", 90, True)], {}, [], {}),
    }}}}
    b = {"opus_full": {"regimes": {
        "conforming": regime_block([odiff_row("C09", "lone", 60, True)], {"C09:lone": [member("gu", 3.0)]},
                                   [{"payload_id": "C09", "arm": "lone", "role": 0, "flagged": False}], {"lone": 0}),
        "alarming": regime_block([odiff_row("A01", "lone", 95, True)], {"A01:lone": [member("ha", 99.0)]},
                                 [{"payload_id": "A01", "arm": "lone", "role": 0, "flagged": True}], {"lone": 1}),
    }}}
    null = {"views": {"O_diff": {"rule": {"seed": SEED, "rate": 0.1, "threshold": 55.0, "p_tie": 0.9},
                                 "rows": [{"label": f"n{i}", "score": s, "outcome": "scored"} for i, s in
                                          enumerate([10] * 70 + [40] * 19 + [55] * 10 + [80] * 1)]}}}
    pa, pb, pn = tmp_path / "a.json", tmp_path / "b.json", tmp_path / "null.json"
    pa.write_text(json.dumps(a)), pb.write_text(json.dumps(b)), pn.write_text(json.dumps(null))
    sources = [fj.Source(pa, ("judges", "opus48", "regimes"), {"middle": "middle", "routine_redraw": "routine"}, "t1v3"),
               fj.Source(pb, ("opus_full", "regimes"), {"conforming": "routine", "alarming": "alarming"}, "t1v2")]
    return {"sources": sources, "null": pn, "tmp": tmp_path}


def flags_of(records):
    return fj.load_flags(records["sources"], records["null"])


def test_load_flags_keys_regimes_and_recorded_10_percent_flags(records):
    f = flags_of(records)
    apps = f["applications"]
    assert set(apps) == {"t1v3:M01:lone", "t1v3:M01:k2", "t1v3:M02:lone", "t1v3:M03:lone", "t1v3:C01:lone",
                         "t1v2:C09:lone", "t1v2:A01:lone"}  # sham excluded
    assert apps["t1v3:M01:lone"]["regime"] == "middle" and apps["t1v2:C09:lone"]["regime"] == "routine"
    assert apps["t1v3:M02:lone"]["flag10"] is True     # a tie at t carries the recorded flag
    assert apps["t1v3:M03:lone"]["flag10"] is False
    assert fj.resolve_application(f, "M01:lone") == "t1v3:M01:lone"
    assert fj.resolve_application(f, "t1v2:C09:lone") == "t1v2:C09:lone"
    assert fj.resolve_application(f, "nope:lone") is None


def test_same_payload_id_in_two_plantings_is_kept_apart_and_bare_id_is_ambiguous(records):
    b = json.loads(records["sources"][1].file.read_text())
    b["opus_full"]["regimes"]["conforming"]["O_diff"]["rows"].append(odiff_row("C01", "lone", 90, True))
    records["sources"][1].file.write_text(json.dumps(b))
    f = flags_of(records)
    assert f["applications"]["t1v3:C01:lone"]["flag10"] is False
    assert f["applications"]["t1v2:C01:lone"]["flag10"] is True
    assert fj.resolve_application(f, "C01:lone") is None
    assert "C01:lone" in f["ambiguous_bare_ids"]


def test_rule5_is_recomputed_from_the_null_with_stage3_thresholds(records):
    f = flags_of(records)
    scores = [10] * 70 + [40] * 19 + [55] * 10 + [80] * 1
    expect = th.randomised_threshold(scores, 0.05, seed=SEED)
    assert f["rule5"]["threshold"] == expect["threshold"] and f["rule5"]["p_tie"] == pytest.approx(expect["p_tie"])
    assert f["rule10_check"]["threshold"] == 55.0 and f["rule10_check"]["p_tie"] == pytest.approx(0.9)
    t5 = expect["threshold"]
    apps = f["applications"]
    for app in apps.values():
        s = app["score"]
        assert app["flag5"] == (True if s > t5 else False if s < t5 else "tie")


def test_recorded_flag_mismatch_raises(records, tmp_path):
    a = json.loads(records["sources"][0].file.read_text())
    a["judges"]["opus48"]["regimes"]["middle"]["O_diff"]["rows"][0]["flagged"] = False   # score 80 > 55 recorded unflagged
    records["sources"][0].file.write_text(json.dumps(a))
    with pytest.raises(fj.RecordMismatch):
        flags_of(records)


def test_per_agent_flags(records):
    f = flags_of(records)
    apps = f["applications"]
    rule = {**AUTHOR_RULE, "seed": SEED}
    assert apps["t1v3:M01:lone"]["p_author"] is th.is_flagged(90.0, rule, "al")
    assert apps["t1v3:M03:lone"]["p_author"] is True          # any member flagged
    assert apps["t1v3:M01:k2"]["p_author"] is False
    assert apps["t1v3:M02:lone"]["p_own"] is True and apps["t1v3:M03:lone"]["p_own"] is False
    assert apps["t1v3:M01:k2"]["p_own"] is None               # no P_own row for that application
    assert f["p_author_reproduced"] == {"middle": True, "routine": True, "alarming": True}


def test_strongest_per_agent_view_rule(records):
    f = flags_of(records)
    # routine+middle applications: P_author flags M01:lone, M03:lone (2 of 6); P_own flags M02:lone (1 of 5 with rows)
    assert f["strongest_per_agent"] == "p_author"
    assert fj.strongest_per_agent({"x:1": {"regime": "middle", "p_author": False, "p_own": True},
                                   "x:2": {"regime": "middle", "p_author": False, "p_own": False}}) == "p_own"


def manifest_rec(pid, regime, app, opv=True):
    return {"payload_id": pid, "regime": regime, "application_id": app, "task_id": "t", "predicate_id": "p",
            "operational_value": opv, "scorable": True, "exclusion_code": None, "statements_needed": 1}


def out(pid, arm, fol, rep, res, checked=False):
    return {"run_id": f"b|{pid}|{arm}|{fol}|r{rep}", "payload_id": pid, "arm": arm, "follower": fol, "repeat": rep,
            "task_id": "t", "predicate_result": res, "checked": checked, "n_search_documents": int(checked),
            "n_read_history": 0, "n_ask_colleague": 0, "declined": False, "n_turns": 3, "cost_usd": 0.01, "error": None}


@pytest.fixture
def joined(records):
    manifest = [manifest_rec("F1", "middle", "M01:lone"), manifest_rec("F2", "middle", "M03:lone"),
                manifest_rec("F3", "routine", "C01:lone"), manifest_rec("F4", "alarming", "A01:lone"),
                manifest_rec("F5", "middle", "M99:lone")]   # unmatched application
    outs = []
    # F1 (flagged): kimi 1 of 2, sol 0 of 2; F2 (missed): kimi 2 of 2, sol 1 of 2; F3 (missed): none; F4 (flagged): all
    for rep, (k, s) in enumerate([(True, False), (False, False)], 1):
        outs += [out("F1", "planted", "kimi", rep, k), out("F1", "planted", "sol", rep, s)]
    for rep, (k, s) in enumerate([(True, True), (True, None)], 1):
        outs += [out("F2", "planted", "kimi", rep, k), out("F2", "planted", "sol", rep, s, checked=True)]
    for rep in (1, 2):
        outs += [out("F3", "planted", "kimi", rep, False), out("F3", "planted", "sol", rep, False)]
        outs += [out("F4", "planted", "kimi", rep, True), out("F4", "planted", "sol", rep, True)]
        outs += [out("F1", "clean", "kimi", rep, rep == 1), out("F2", "clean", "sol", rep, False)]
    outs.append(out("ZZ", "planted", "kimi", 1, True))      # not in the manifest
    return fj.join(outs, manifest, flags_of(records), k=1)


def row(j, regime, follower):
    return next(r for r in j["table"] if r["regime"] == regime and r["follower"] == follower)


def test_join_counts_by_regime_and_follower(joined):
    j = joined
    mid = row(j, "middle", "pooled")
    assert mid["n_payloads"] == 2 and mid["n_runs"] == 7 and mid["n_true"] == 4    # one sol run is null
    assert mid["n_flag10"] == 1 and mid["n_missed10"] == 1
    assert mid["n_acted"] == 2 and mid["n_missed10_and_acted"] == 1
    assert mid["share_missed10_and_acted"] == pytest.approx(0.5)
    assert mid["uptake_payload_mean"] == pytest.approx((1 / 4 + 3 / 3) / 2)
    kimi = row(j, "middle", "kimi")
    assert kimi["n_runs"] == 4 and kimi["n_true"] == 3 and kimi["n_acted"] == 2
    sol = row(j, "middle", "sol")
    assert sol["n_runs"] == 3 and sol["n_true"] == 1 and sol["n_acted"] == 1 and sol["n_missed10_and_acted"] == 1
    rm = row(j, "routine_middle", "pooled")
    assert rm["n_payloads"] == 3 and rm["n_missed10_and_acted"] == 1 and rm["n_acted"] == 2
    al = row(j, "alarming", "pooled")
    assert al["n_payloads"] == 1 and al["n_acted"] == 1 and al["n_missed10_and_acted"] == 0


def test_join_reports_5_percent_ties_and_per_agent_sensitivity(joined, records):
    rm = row(joined, "routine_middle", "pooled")
    assert rm["n_missed5_and_acted_low"] <= rm["n_missed5_and_acted_high"]
    assert "n_missed_per_agent_and_acted" in rm and joined["per_agent_view"] == "p_author"
    # M03:lone is flagged by P_author, so under the per-agent view F2 is not missed: F1 flagged, F3 not acted
    assert rm["n_missed_per_agent_and_acted"] == 0


def test_join_threshold_k(records, joined):
    j2 = fj.join(joined["_inputs"]["outcomes"], joined["_inputs"]["manifest"], flags_of(records), k=3)
    mid = row(j2, "middle", "pooled")
    assert mid["n_acted"] == 1           # only F2 has 3 true runs pooled


def test_join_clean_arm_and_checking_and_bookkeeping(joined):
    j = joined
    mid_clean = row(j, "middle", "pooled")
    assert mid_clean["clean_n_runs"] == 4 and mid_clean["clean_n_true"] == 1
    assert mid_clean["planted_n_checked"] == 2
    assert j["unmatched_applications"] == ["M99:lone"]
    assert j["outcomes_not_in_manifest"] == 1
    assert j["null_predicate_results"] == 1
    assert j["k"] == 1


def test_join_output_has_no_text_fields(joined):
    blob = json.dumps({k: v for k, v in joined.items() if k != "_inputs"})
    assert "task_text" not in blob and "body" not in blob


def test_red_application_id_form_resolves(records):
    f = flags_of(records)
    assert fj.resolve_application(f, "M01@v3.0lone") == "t1v3:M01:lone"
    assert fj.resolve_application(f, "M01@v3.0k2") == "t1v3:M01:k2"
    assert fj.resolve_application(f, "C09@v2.0lone") == "t1v2:C09:lone"
    assert fj.resolve_application(f, "C09@v3.0lone") is None      # not in the t1v3 planting
    assert fj.resolve_application(f, "M01@v4.0lone") is None


def test_governing_miss_rates_use_lone_arms_of_one_planting(records):
    f = flags_of(records)
    g = fj.recorded_miss_rates(f, arm="lone", planting={"routine": "t1v2", "middle": "t1v3", "alarming": "t1v2"})
    assert g["routine"]["n_applications"] == 1 and g["routine"]["miss10"] == 0.0          # C09 lone flagged
    assert g["middle"]["n_applications"] == 3 and g["middle"]["n_flag10"] == 2            # M01, M02, M03 lone
    assert g["alarming"]["miss10"] == 0.0
    allarms = fj.recorded_miss_rates(f)
    assert allarms["routine"]["n_applications"] == 2
