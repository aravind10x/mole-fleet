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
