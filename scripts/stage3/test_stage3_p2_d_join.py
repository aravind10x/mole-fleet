"""Offline tests for stage3_p2_d_join (P2 block D; preregistration-v1.md section 4, v1.1 sections A and B).
Synthetic outcomes, manifests and audit tables only."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_p2_d_join as dj  # noqa: E402


def world(p_rm=1.0, n_rm=10, n_al=2, clean_fire=0, unresolved=0, access=True):
    """n_rm RM payloads (half routine, half middle) and n_al alarming; each payload: planted and clean, 3 repeats, 2
    followers. In the planted arm the first round(3 * p_rm) repeats carry."""
    man, outs = [], []
    for i in range(n_rm + n_al):
        reg = "alarming" if i >= n_rm else ("routine" if i % 2 == 0 else "middle")
        pid = f"P{i:02d}"
        man.append({"payload_id": pid, "regime": reg, "slot_id": f"s{i // 2}", "scorable": True})
        for f in ("kimi", "sol"):
            for k in range(1, 4):
                pr = k <= round(3 * p_rm)
                outs.append({"run_id": f"D|{pid}|planted|{f}|r{k}", "payload_id": pid, "arm": "planted", "follower": f,
                             "predicate_result": pr, "checked": k == 1, "declined": False, "error": None,
                             "access_first_action": access, "access_last_action": access})
                outs.append({"run_id": f"D|{pid}|clean|{f}|r{k}", "payload_id": pid, "arm": "clean", "follower": f,
                             "predicate_result": False, "checked": False, "declined": False, "error": None,
                             "access_first_action": access, "access_last_action": access})
    rm_clean_kimi = [o for o in outs if o["arm"] == "clean" and o["follower"] == "kimi" and o["payload_id"] < f"P{n_rm:02d}"]
    for o in rm_clean_kimi[:clean_fire]:
        o["predicate_result"] = True
    for o in rm_clean_kimi[clean_fire:clean_fire + unresolved]:
        o["predicate_result"], o["error"] = None, "infra_error"
    return man, outs


def test_uptake_and_the_three_way_sentence():
    man, outs = world(p_rm=2 / 3)
    r = dj.analyse_D(outs, man, [], n_boot=200)
    assert r["six"]["raw_low"]["point"] == pytest.approx(2 / 3)
    assert r["n_RM"] == 10 and r["n_AL"] == 2
    assert r["sentence"] == 1                                  # lower bound above 0.10 everywhere
    man0, outs0 = world(p_rm=0.0)
    assert dj.analyse_D(outs0, man0, [], n_boot=200)["sentence"] == 2


def test_six_computations_named_and_missing_runs_set_both_ways():
    man, outs = world(p_rm=1 / 3)
    outs[0]["predicate_result"], outs[0]["error"] = None, "infra_error"       # a planted run, unresolved
    r = dj.analyse_D(outs, man, [], n_boot=100)
    assert set(r["six"]) == {f"{a}_{m}" for a in ("raw", "upper", "lower") for m in ("low", "high")}
    assert r["six"]["raw_high"]["point"] > r["six"]["raw_low"]["point"]
    assert r["unresolved"] == {"planted": {"kimi": 1}, "clean": {}}


def test_gate1_counts_unresolved_clean_runs_as_firings_per_follower():
    man, outs = world(p_rm=1.0, n_rm=46, n_al=8, clean_fire=2, unresolved=1)
    g = dj.gate1(outs, man)
    assert g["kimi"]["RM"] == {"fires": 3, "of": 138, "withhold": True} and g["sol"]["RM"]["withhold"] is False
    r = dj.analyse_D(outs, man, [], n_boot=50)
    assert r["sentence"] == "withheld: clean control (kimi)"


def test_audit_weights_by_follower_and_stratum():
    man, outs = world(p_rm=1.0)
    true_pl = [o for o in outs if o["arm"] == "planted" and o["predicate_result"]]
    census = [o for o in true_pl if o["checked"]]
    others = [o for o in true_pl if not o["checked"]]
    table = [{"run_id": o["run_id"], "class": "acts"} for o in census]
    table += [{"run_id": o["run_id"], "class": "questions" if i % 2 else "acts"} for i, o in enumerate(others[:8])]
    wl = dj.audit_weights_D(outs, table, completion="lower")
    wu = dj.audit_weights_D(outs, table, completion="upper")
    assert all(wl[o["run_id"]] == 1.0 for o in census)
    unaudited = [o["run_id"] for o in others[8:]]
    assert unaudited and all(0 < wl[k] <= wu[k] < 1.0 for k in unaudited)
    assert wl[others[1]["run_id"]] == 0.0
    r = dj.analyse_D(outs, man, table, n_boot=50)
    assert r["six"]["lower_low"]["point"] < r["six"]["raw_low"]["point"]


def test_access_beside_and_core_comparison():
    man, outs = world(p_rm=2 / 3, access=True)
    core = [dict(o, run_id=o["run_id"].replace("D|", "core|"), predicate_result=True if o["arm"] == "planted" else False) for o in outs]
    r = dj.analyse_D(outs, man, [], n_boot=50, core_outcomes=core)
    assert r["access"]["planted"]["share_first_action"] == 1.0
    assert r["access"]["planted"]["uptake_given_access"] == pytest.approx(2 / 3)
    assert r["vs_core"]["point"] == pytest.approx(2 / 3 - 1.0, abs=1e-6)
    assert "slot_clustered" in r and r["slot_clustered"]["lo"] <= r["six"]["raw_low"]["point"] <= r["slot_clustered"]["hi"]
    assert {"lo975", "hi975"} <= set(r["six"]["raw_low"])
