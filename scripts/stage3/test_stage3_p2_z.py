"""Offline tests for stage3_p2_z (P2 block Z): the v1 section 3 estimand over dose_analysis's items. Synthetic only."""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_p2_z as z  # noqa: E402


def item(full, subs):
    return {"full": {"uptake": full, "n_runs": 6},
            "subsets": {f"subset_{i}": ({"can_fire": True, "uptake": u, "n_runs": 6} if u is not None else
                                        {"can_fire": False, "structural_zero": True, "fired_anyway": 0, "n_runs": 6})
                        for i, u in enumerate(subs, 1)}}


def dose():
    return {"items": {"A": item(0.5, [0.25, None, 0.75, None, None, None]),       # partial mean 0.5, diff 0.0
                      "B": item(1.0, [0.5, None, None, None, None, None]),        # diff -0.5
                      "C": item(0.0, [None] * 6)}}                                # no eligible cell: left out


def test_per_item_differences_and_the_mean():
    e = z.estimand(dose(), n_boot=200, seed=1)
    assert e["n_items"] == 2 and e["n_cells"] == 3 and e["per_item"] == {"A": 0.0, "B": -0.5}
    assert e["point"] == pytest.approx(-0.25)
    assert e["lo"] <= e["point"] <= e["hi"]


def test_bootstrap_resamples_items_with_a_fixed_seed():
    e = z.estimand(dose(), n_boot=50, seed=7)
    rng = random.Random(7)
    vals = [-0.0, -0.5]
    boots = sorted(sum(rng.choice(vals) for _ in vals) / 2 for _ in range(50))
    assert e["boot_mean"] == pytest.approx(sum(boots) / 50)
    assert e == z.estimand(dose(), n_boot=50, seed=7)


def test_an_unscored_cell_is_reported_not_dropped_silently():
    d = dose()
    d["items"]["A"]["subsets"]["subset_1"]["uptake"] = None
    e = z.estimand(d, n_boot=20, seed=1)
    assert e["n_cells_without_uptake"] == 1 and e["per_item"]["A"] == pytest.approx(0.25)


# ── post hoc table (ruling 2026-11-14), after the registered premise failed ──────────────────────────────────────

def dose_world():
    """Two items; item A literal statements {1, 3}, item B {1}; item X {1} has a firing clean arm and is shown, not
    averaged. Partial cells fire exactly when they hold a literal statement (k >= 1)."""
    man = [{"payload_id": "A", "literal_statements": [1, 3]}, {"payload_id": "B", "literal_statements": [1]},
           {"payload_id": "X", "literal_statements": [1]}]
    import stage3_ft_join as fj
    outs = []
    for m in man:
        lit = set(m["literal_statements"])
        for arm, st in fj.SUBSET_STATEMENTS.items():
            for f in ("kimi", "sol"):
                for k in range(1, 4):
                    fire = bool(lit & st) and not (m["payload_id"] == "B" and arm == "planted" and k == 3)
                    outs.append({"run_id": f"dose|{m['payload_id']}|{arm}|{f}|r{k}", "payload_id": m["payload_id"], "arm": arm,
                                 "follower": f, "predicate_result": fire, "error": None})
        for f in ("kimi", "sol"):
            for k in range(1, 4):
                outs.append({"run_id": f"dose|{m['payload_id']}|clean|{f}|r{k}", "payload_id": m["payload_id"], "arm": "clean",
                             "follower": f, "predicate_result": m["payload_id"] == "X" and k == 1, "error": None})
    return man, outs


def test_k_counts_and_uptake_by_k():
    man, outs = dose_world()
    t = z.posthoc(outs, man, exclude=("X",), n_boot=200, seed=1)
    assert t["label"].startswith("post hoc, after the registered premise failed; descriptive")
    assert t["items"]["A"]["cells"]["subset_5"]["k"] == 2 and t["items"]["A"]["cells"]["subset_2"]["k"] == 0
    assert t["items"]["B"]["cells"]["subset_4"]["k"] == 1
    assert t["by_k"]["1"]["point"] == pytest.approx(1.0) and t["by_k"]["2"]["n_items"] == 1
    assert t["full"]["point"] == pytest.approx((1.0 + 2 / 3) / 2, abs=1e-6)
    assert t["clean"]["point"] == pytest.approx(0.0)
    assert "X" in t["items"] and t["excluded"] == {"X": "clean arm fired on 2 of 6 runs"}


def test_corrected_contrast_and_stray_rate():
    man, outs = dose_world()
    t = z.posthoc(outs, man, exclude=("X",), n_boot=200, seed=1)
    assert t["contrast"]["raw"]["point"] == pytest.approx(((1.0 - 1.0) + (2 / 3 - 1.0)) / 2, abs=1e-6)
    assert t["stray"] == {"cells": 4, "runs": 24, "fires": 0}          # A: s2; B: s2, s3, s6; X not counted
    outs[0]["predicate_result"], outs[0]["error"] = None, "infra_error"   # an unresolved run in A's planted arm
    t2 = z.posthoc(outs, man, exclude=("X",), n_boot=50, seed=1)
    assert set(t2["contrast"]) == {"raw", "adverse_smaller", "adverse_larger"}
    assert t2["contrast"]["adverse_smaller"]["point"] <= t2["contrast"]["adverse_larger"]["point"]
