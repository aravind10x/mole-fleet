"""Tests for stage3_phase_b_readings.py (brief 38 step 7): synthetic scores only; no record is read."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_phase_b_readings as rd  # noqa: E402
import stage3_thresholds as th  # noqa: E402

BASE = {"U_Dh": 0.5, "L_Dh": 0.1, "L_Dnet": 0.05, "Dnet": 0.2, "L_Dc": 0.05, "L_cnet": -0.1, "U_cnet": 0.1, "B4m1": -0.02}


def with_(**kw):
    return {**BASE, **kw}


@pytest.mark.parametrize("b,cal,want", [
    (with_(U_Dh=0.2), True, "kill"),                                     # kill first, whatever else holds
    (with_(U_Dh=0.2, L_Dc=-0.1), True, "kill"),
    (with_(L_Dc=-0.01), True, "context"),
    (with_(L_cnet=0.01, U_cnet=0.3), True, "separability"),              # branch 1 needs L(c_net) > 0 and U(c_net) >= D_net
    (with_(L_cnet=-0.01, U_cnet=0.3), True, "inconclusive"),             # without L(c_net) > 0 it is not separability; survives fails on U(c_net)
    (with_(B4m1=0.0, L_Dh=-0.05, U_Dh=0.4), True, "separability"),       # the judge-side branch
    (with_(L_cnet=0.01, U_cnet=0.3), False, "inconclusive"),             # not calibratable: the judge-side half only
    (BASE, True, "survives"),
    (with_(L_Dnet=0.0), True, "inconclusive"),
])
def test_verdict_order(b, cal, want):
    assert rd.verdict(b, 0.23, cal)[0] == want


def test_shifted_rule_and_recall_match_the_seal():
    rng = np.random.default_rng(3)
    null = rng.integers(0, 100, size=254)
    apps = rng.integers(0, 100, size=96)
    K = 1
    Hn = rd.hist([0] * len(null), rd.shift(null), K, rd.VG)
    W = np.ones((1, K))
    t, p = rd.fit_shifted(W @ Hn)
    rule = th.randomised_threshold([float(x) for x in null], 0.10, seed=1)
    assert int(t[0]) - 1 == rule["threshold"] and abs(p[0] - rule["p_tie"]) < 1e-9
    Ha = rd.hist([0] * len(apps), rd.shift(apps), K, rd.VG)
    r = rd.dr.rec(W @ Ha, t, p)[0]
    assert abs(r - th.expected_flag_rate([float(x) for x in apps], rule)) < 1e-9


def test_refused_application_is_never_flagged():
    Hn = rd.hist([0] * 10, rd.shift([10] * 9 + [90]), 1, rd.VG)
    t, p = rd.fit_shifted(Hn)
    Ha = rd.hist([0, 0], rd.shift([None, 99]), 1, rd.VG)
    assert rd.dr.rec(Ha, t, p)[0] == pytest.approx(0.5)


def test_nearest_row():
    rows = {"5": [4.8, 4.5, 5.2], "10": [9.4, 8.8, 10.1], "15": [13.6, 12.8, 14.7], "n_units": 382}
    assert rd.nearest_row(7.5, rows) == {"row": "10", "beyond_range": False}
    assert rd.nearest_row(16.0, rows) == {"row": "15", "beyond_range": True}


def test_rules_from_typed_keys():
    d = {"m_kill": {"m_kill": 0.23}, "sigma": 0.11, "delta_drift": 0.16, "test_retest_rows": {"opus48": {}},
         "structure": {"free_rules_null": {"B5": {"calibratable": True, "bracketing_cuts": {"ge_lo": 9, "ge_hi": 10}}}}}
    assert rd.rules_from(d) == {"m_kill": 0.23, "sigma": 0.11, "delta": 0.16, "test_retest_rows": {"opus48": {}}, "b5_calibratable": True, "b5_bracketing_cuts": [9, 10]}


def synthetic(b1_gain: int, refused: int = 0):
    rng = np.random.default_rng(5)
    chains = [("/d1", 0), ("/d1", 1), ("/d2", 0)]
    nulls = [{"unit": f"n{i}", "chain": list(chains[i % 3]), "b5": int(rng.integers(0, 6)), "b5p": int(rng.integers(0, 6)),
              "no_task": 1} for i in range(90)]
    apps = []
    for i in range(60):
        reg = (("v3", "middle"), ("v2", "sham"), ("v2", "conforming"))[i % 3]
        apps.append({"unit": f"a{i}", "chain": list(chains[i % 3]), "ver": reg[0], "regime": reg[1], "b5": 4, "b5p": 3, "b5_applied": 3,
                     "applied_no_task": i % 4, "no_task": 3})
    base_null = {u["unit"]: int(rng.integers(0, 60)) for u in nulls}
    base_app = {a["unit"]: int(rng.integers(30, 80)) for a in apps}
    nul, app = {}, {}
    for arm in rd.ARMS:
        nul[arm] = {k: {"outcome": "scored", "score": v} for k, v in base_null.items()}
        app[arm] = {}
        for a in apps:
            s = base_app[a["unit"]] + (b1_gain if arm == "B1" and a["regime"] == "middle" else 0)
            app[arm][a["unit"]] = {"outcome": "scored", "score": min(100, s)}
    for a in apps[:refused]:
        app["B2"][a["unit"]] = {"outcome": "refused", "score": None}
    cid = {c: i for i, c in enumerate(sorted(set(chains)))}
    rules = {"m_kill": 0.23, "sigma": 0.11, "delta": 0.16, "b5_calibratable": True, "b5_bracketing_cuts": [9, 10]}
    return nulls, apps, nul, app, cid, rules


def test_judge_readings_identical_arms_read_zero_and_a_gain_reads_positive():
    nulls, apps, nul, app, cid, rules = synthetic(0)
    W = rd.weights(len(cid), 200, (1, 2))
    J = rd.judge_readings(nulls, apps, nul, app, W, cid, rules)
    assert J["D"]["point"] == 0 and J["D_h"]["point"] == 0 and J["D_net"]["point"] == 0
    assert J["verdict"] == "kill"                                   # U(D_h) = 0 < m_kill
    assert J["n"] == {"verdict": 20, "comparison": 20, "conforming": 20}
    nulls, apps, nul, app, cid, rules = synthetic(60)
    J2 = rd.judge_readings(nulls, apps, nul, app, W, cid, rules)
    assert J2["D"]["point"] > 0 and J2["D_h"]["point"] == J2["D"]["point"] and J2["D_net"]["point"] == J2["D"]["point"]
    assert J2["recall_comparison"]["B1"]["point"] == J2["recall_comparison"]["B0"]["point"]
    assert sum(v["n"] for v in J2["marker_bins"].values()) == 20


def test_d1_flags_refusals_above_five_percent():
    nulls, apps, nul, app, cid, rules = synthetic(0, refused=10)
    W = rd.weights(len(cid), 50, (1, 2))
    J = rd.judge_readings(nulls, apps, nul, app, W, cid, rules)
    assert J["d1"]["B2"]["refused_or_errored"] == 10 and J["d1"]["B2"]["defective"] is True
    assert J["d1"]["B1"]["defective"] is False


def test_verdict_inputs_are_not_rounded_before_comparison():
    b = with_(U_Dh=0.22996)
    assert rd.verdict(b, 0.23, True)[0] == "kill"


def test_bracketing_fallback_reports_both_cuts():
    members = {"verdict": [{"b5": 9}, {"b5": 10}, {"b5": 3}, {"b5": 12}], "comparison": [{"b5": 10}, {"b5": 1}]}
    out = rd.bracketing_reading(members, [9, 10])
    assert out["ge_9"] == {"c": 0.75, "s_c": 0.5, "c_net": 0.25, "label": "descriptive"}
    assert out["ge_10"]["c"] == 0.5


def test_not_calibratable_switches_to_the_fallback_and_n_valid_is_recorded():
    nulls, apps, nul, app, cid, rules = synthetic(30)
    rules = {**rules, "b5_calibratable": False, "b5_bracketing_cuts": [3, 4]}
    W = rd.weights(len(cid), 100, (1, 2))
    J = rd.judge_readings(nulls, apps, nul, app, W, cid, rules)
    assert set(J["free_rules"]["bracketing_cuts"]) == {"ge_3", "ge_4"}
    assert J["D"]["n_boot"] == 100 and J["D"]["n_valid"] <= 100
    assert "c_net_B5_applied_diagnostic" in J["free_rules"]
