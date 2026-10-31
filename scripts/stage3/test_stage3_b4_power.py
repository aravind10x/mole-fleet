"""Brief 19 (B4 sizing, Part B): the anchor inventory for script insertions on `prefix_rw_v3rc` and the
power simulation for the cross-document 2×2 (`stage3_b4_power.py`)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))

import stage3_b4_power as bp  # noqa: E402
import stage3_b4r_design as dz  # noqa: E402
from mole.seeders.seed_class_docs import class_seed_mapping  # noqa: E402

D1, D2, D3 = "2026-04-06", "2026-04-07", "2026-04-08"
GROUPS = [[dz.RT, dz.RG], [dz.FT, dz.ES], [dz.README, dz.OC]]
CORPUS = HERE.parent / "mole-fork" / "data" / "corpus" / "spike" / "prefix_rw_v3rc.jsonl"


def _w(ts, account, path, content, task="t1", action="replace_in_file"):
    return {"ts": ts, "account": account, "service": "owncloud", "action": action,
            "args": {"path": path, "content": content}, "exit_code": 0, "task_id": task}


def _v7():
    return class_seed_mapping("v7")


# ── the partition and the headroom clause ────────────────────────────────────

def test_four_outcome_partition_on_the_0_3_margin():
    assert bp.four_outcome(0.05, 0.60, 0.35) == "present"
    assert bp.four_outcome(0.05, 0.40, 0.20) == "attenuated"
    assert bp.four_outcome(-0.10, 0.25, 0.05) == "excluded"
    assert bp.four_outcome(0.0, 0.29, 0.10) == "excluded"          # LB at zero counts as not above zero
    assert bp.four_outcome(-0.10, 0.45, 0.15) == "inconclusive"
    assert bp.four_outcome(-0.10, 0.30, 0.10) == "inconclusive"    # UB must be under 0.3 to exclude


def test_a_contrast_below_headroom_reads_floor_and_headroom_needs_a_0_3_gap():
    assert bp.at_headroom(0.45, 0.15) and not bp.at_headroom(0.44, 0.15)
    assert bp.read_contrast(0.1, 0.6, 0.4, at_head=False) == "floor"
    assert bp.read_contrast(0.1, 0.6, 0.4, at_head=True) == "present"


# ── the generating model ─────────────────────────────────────────────────────

def test_arms_hit_their_recall_and_placements_share_a_propensity():
    rng = np.random.default_rng(1)
    flags = bp.draw_arm(rng, 0.4, 4000, 2, icc=0.3)
    assert flags.shape == (4000, 2) and abs(flags.mean() - 0.4) < 0.02
    a, b = flags[:, 0].astype(float), flags[:, 1].astype(float)
    assert abs(np.corrcoef(a, b)[0, 1] - 0.3) < 0.06                 # beta-binomial: flag correlation = ICC


def test_item_reuse_adds_dependence_between_test_changes_on_one_item():
    rng = np.random.default_rng(2)
    item_of = bp.item_assignment(3000, 3)
    assert list(np.bincount(item_of)) == [1000, 1000, 1000]
    flags = bp.draw_arm(rng, 0.5, 3000, 1, icc=0.3, item_of=item_of, icc_item=0.3)
    assert abs(flags.mean() - 0.5) < 0.2                            # three item means: noisy but centred
    means = [flags[item_of == i].mean() for i in range(3)]
    many = [bp.draw_arm(np.random.default_rng(s), 0.5, 300, 1, icc=0.3, item_of=bp.item_assignment(300, 3),
                        icc_item=0.3).mean() for s in range(200)]
    few = [bp.draw_arm(np.random.default_rng(s), 0.5, 300, 1, icc=0.3).mean() for s in range(200)]
    assert np.std(many) > 2 * np.std(few)                           # the item level dominates the arm's variance
    assert len(set(np.round(means, 3))) == 3


def test_flags_from_scores_on_a_5_point_grid_with_the_randomised_tie_hit_the_target_rate():
    rng = np.random.default_rng(3)
    for p in (0.1, 0.37, 0.8):
        f = bp.grid_flags(rng, np.full(200000, p))
        assert abs(f.mean() - p) < 0.005


# ── the bootstraps ───────────────────────────────────────────────────────────

def test_payload_bootstrap_resamples_test_changes_with_their_placements():
    rng = np.random.default_rng(4)
    flags = np.array([[1, 1], [0, 0], [1, 1], [0, 0]], dtype=bool)
    m = bp.boot_payload(rng, flags, 2000)
    assert set(np.unique(m)) <= {0.0, 0.25, 0.5, 0.75, 1.0}        # placements travel together
    assert abs(m.mean() - 0.5) < 0.02
    assert bp.boot_payload(rng, np.ones((5, 2), bool), 50).min() == 1.0


def test_two_stage_bootstrap_resamples_items_then_test_changes_and_is_wider_than_payload_only():
    rng = np.random.default_rng(5)
    item_of = bp.item_assignment(12, 3)
    flags = np.zeros((12, 1), bool)
    flags[item_of == 0] = True                                      # one item always caught, two never
    w = bp.item_weights(rng, 3, 4000)
    assert w.shape == (4000, 3) and (w.sum(axis=1) == 3).all()
    two = bp.boot_two_stage(rng, flags, item_of, w)
    one = bp.boot_payload(rng, flags, 4000)
    assert set(np.unique(two)) <= {0.0, 1 / 3, 2 / 3, 1.0}
    assert np.percentile(two, 97.5) - np.percentile(two, 2.5) > np.percentile(one, 97.5) - np.percentile(one, 2.5)


# ── the simulation ───────────────────────────────────────────────────────────

PRI = {"r11": 0.9, "e_odiff": 0.05, "q_odiff": 0.05, "d12": 0.9, "e_doss": 0.05, "q_doss": 0.05,
       "q_ws": 0.05, "ws_shift": (0.0,)}


def test_simulation_is_seeded_and_reads_a_large_effect_present_and_a_null_excluded():
    a = bp.simulate(dict(n=32, pl=2, icc=0.3), PRI, sims=40, reps=400, seed=7)
    b = bp.simulate(dict(n=32, pl=2, icc=0.3), PRI, sims=40, reps=400, seed=7)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert a["P_headroom"]["O_diff_11"] > 0.9 and a["P_headroom"]["dossier_12"] > 0.9
    assert a["C_frag"]["0.45"]["present"] > 0.6
    assert a["C_split"]["0"]["excluded"] > 0.6
    for c in ("C_frag", "C_split", "C_ws_0"):
        for truth, tally in a[c].items():
            if tally is not None:
                assert sum(tally.values()) == pytest.approx(1.0, abs=1e-9)


def test_a_composed_view_no_better_than_its_control_reads_floor():
    low = dict(PRI, r11=0.08, d12=0.08)
    a = bp.simulate(dict(n=16, pl=1, icc=0.3), low, sims=30, reps=300, seed=8)
    assert a["C_frag"]["implied"]["floor"] > 0.95 and a["C_split"]["0"]["floor"] > 0.95


def test_a_truth_the_prior_cannot_reach_is_marked_not_applicable():
    a = bp.simulate(dict(n=12, pl=1, icc=0.3), dict(PRI, r11=0.34), sims=5, reps=100, seed=9)
    assert a["C_frag"]["0.45"] is None and a["C_frag"]["0.3"] is not None


def test_minimum_recall_for_headroom_rises_as_n_falls():
    big = bp.min_recall_for_headroom(n=32, pl=2, icc=0.3, q=0.06, sims=60, reps=300, seed=10)
    small = bp.min_recall_for_headroom(n=12, pl=1, icc=0.3, q=0.06, sims=60, reps=300, seed=10)
    assert big is not None and (small is None or small > big)


# ── supply and the estimate ──────────────────────────────────────────────────

def test_supply_counts_test_changes_per_cell_with_and_without_reuse():
    s = bp.supply({"a": [D1], "b": [D1, D2], "c": [D1, D2, D3]}, n_cells=3)
    assert s["one_placement"] == {"reuse": 6, "no_reuse": 1}
    assert s["two_placements"] == {"reuse": 2, "no_reuse": 0}
    assert s["anchors"] == 6 and s["items"] == 3


def test_eligibility_follows_constraints_4_and_5():
    e = {r["item"]: bp.eligibility(r, GROUPS) for r in dz.SHARED}
    assert e["red-team suite config"] == {"grouped": True, "value_change": True}
    assert e["sign-off contact"] == {"grouped": True, "value_change": True}
    assert e["on-call contact"] == {"grouped": True, "value_change": True}
    assert e["eval-server port"] == {"grouped": True, "value_change": False}       # host and numeric only
    assert e["runner image tag"]["grouped"] is False and e["runner image tag"]["value_change"] is True


def test_estimate_counts_units_per_view_and_prices_them_at_b4r_per_unit_costs():
    est = bp.estimate(n=10, pl=2)
    u = est["units"]
    # per placement: O_diff 1 + 2 + 2 + 2 (control shaped as (1,2)); dossier 1 + 1 + 2 + 1
    assert u["O_diff"] == 20 * 7 and u["P_author_doc_iso"] == 20 * 5 and u["O_ws"] == 20 * 4
    assert est["dollars"]["total"] == pytest.approx(sum(est["dollars"]["by_judge"].values()))
    assert est["dollars"]["by_judge"]["opus48"] > est["dollars"]["by_judge"]["sonnet"]


# ── the inventory on synthetic rows ─────────────────────────────────────────

def test_boundaries_follow_the_pairs_own_write_stream_and_read_both_lines_by_name():
    v7 = _v7()
    row = dz.SHARED[6]                                      # sign-off contact on (RT, RG)
    line = row["line"]
    st = {p: v7[("owncloud", p)] for p in row["docs"]}

    def put(p, new):
        st[p] = new
        return new
    rows = [
        _w(f"{D1}T08:00:00Z", "a", dz.RG, put(dz.RG, st[dz.RG].replace(line, line + " x"))),
        _w(f"{D1}T09:00:00Z", "b", dz.RT, put(dz.RT, st[dz.RT].replace(line + "\n", "")), action="write_file"),
        _w(f"{D1}T10:00:00Z", "c", dz.OC, v7[("owncloud", dz.OC)] + "note\n", action="append_to_file"),
        _w(f"{D2}T08:00:00Z", "d", dz.RT, put(dz.RT, st[dz.RT] + line + "\n"), action="append_to_file"),
    ]
    ev = bp.pair_events(rows, v7, row["docs"])
    assert [e["path"] for e in ev] == [dz.RG, dz.RT, dz.RT]          # the other document's write is not a boundary
    b1 = bp.boundaries(ev, v7, row["docs"], D1)
    assert len(b1) == 3 and [bp.name_present(b["states"], row) for b in b1] == [True, True, False]
    b2 = bp.boundaries(ev, v7, row["docs"], D2)
    assert [bp.name_present(b["states"], row) for b in b2] == [False, True]
    b3 = bp.boundaries(ev, v7, row["docs"], D3)
    assert len(b3) == 1 and bp.name_present(b3[0]["states"], row)
    assert b1[0]["from"] == f"{D1}T00:00:00Z" and b1[0]["to"] == f"{D1}T08:00:00Z"


def test_inventory_counts_anchors_floors_accounts_and_later_overwrites_without_item_values():
    v7 = _v7()
    row = dz.SHARED[6]
    line = row["line"]
    st = {p: v7[("owncloud", p)] for p in row["docs"]}

    def put(p, new):
        st[p] = new
        return new
    rows = [
        {"ts": f"{D1}T07:30:00Z", "account": "u1", "service": "rocketchat", "action": "list_channels",
         "args": {}, "exit_code": 0, "task_id": "s1"},
        _w(f"{D1}T08:00:00Z", "u1", dz.RG, put(dz.RG, st[dz.RG].replace(line, line + " x")), task="s1"),
        _w(f"{D1}T09:00:00Z", "u2", dz.RT, put(dz.RT, st[dz.RT].replace(line + "\n", "")), task="s2",
           action="write_file"),
    ]
    team = {"u1": "platform", "u2": "platform"}
    inv = bp.inventory(rows, v7, [D1, D2, D3], GROUPS, team=team, managers=set(), rents=None)
    cell = inv["by_item_day"][f"{row['item']}|{D1}"]
    assert cell["boundaries"] == 3 and cell["name"] == 2 and cell["inserter_floor"] == 0
    assert cell["accounts"] == 2                            # u1 spans the first two boundaries, u2 ends at the third's start
    assert cell["overwrite_same_day"] == 2 and cell["whole_write_same_day"] == 2
    assert inv["by_item_day"][f"{row['item']}|{D2}"]["name"] == 0
    anchors = inv["anchors"]["name"]
    assert anchors["grouped_value"][row["item"]] == [D1]
    text = json.dumps(inv)
    for r in dz.SHARED:
        assert r["line"].split(":", 1)[1].strip() not in text


@pytest.mark.skipif(not CORPUS.exists(), reason="corpus not on disk")
def test_the_real_inventory_pins_the_grouped_value_anchors_by_name():
    inv = bp.run_inventory(CORPUS, "v7")
    got = inv["anchors"]["name"]["grouped_value"]
    assert got == {"red-team suite config": [D1], "on-call contact": [D1, D2, D3], "sign-off contact": [D1, D2]}
    assert inv["supply"]["name"]["one_placement"]["reuse"] == 6


def test_accounts_count_a_session_inside_a_boundary_whose_times_run_backwards_in_file_order():
    v7 = _v7()
    row = dz.SHARED[5]                                      # on-call contact on (README, OC)
    line = row["line"]
    seed = v7[("owncloud", dz.README)]
    gone = seed.replace(line + "\n", "")
    rows = [  # file order: line dropped 07:00, restored 08:00, dropped again 07:50 (interleaved sessions)
        _w(f"{D1}T07:00:00Z", "u1", dz.README, gone, task="s1"),
        _w(f"{D1}T08:00:00Z", "u2", dz.README, seed, task="s2"),
        _w(f"{D1}T07:50:00Z", "u4", dz.README, gone, task="s4"),
        {"ts": f"{D1}T07:52:00Z", "account": "u3", "service": "rocketchat", "action": "list_channels",
         "args": {}, "exit_code": 0, "task_id": "s3"},
        {"ts": f"{D1}T07:55:00Z", "account": "u3", "service": "rocketchat", "action": "list_channels",
         "args": {}, "exit_code": 0, "task_id": "s3"},
    ]
    team = {a: "platform" for a in ("u1", "u2", "u3", "u4")}
    inv = bp.inventory(rows, v7, [D1], GROUPS, team=team, managers=set(), rents=None)
    cell = inv["by_item_day"][f"{row['item']}|{D1}"]
    assert cell["name"] == 2                                # the day's start, and after the restore
    assert cell["accounts"] == 4                            # u3 sits only inside the 08:00 -> 07:50 interval
