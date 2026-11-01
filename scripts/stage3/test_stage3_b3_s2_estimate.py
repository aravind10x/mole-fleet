"""Tests for stage3_b3_s2_estimate (brief 32, B3's S2): synthetic rules first, then the real files by counts, dollars and
hashes only.

    cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_b3_s2_estimate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_b3_s1_populations as sp  # noqa: E402
import stage3_b3_s2_estimate as se  # noqa: E402

ROOT = se.ROOT
D1, D2 = "2026-04-06", "2026-04-07"


def _v3b() -> dict:
    return json.loads((ROOT / se.V3B).read_text(encoding="utf-8"))


# ── H1 ────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("view,cell", [
    ("`P_author_doc` isolated, Opus 4.8", "dossier_iso:opus48"),
    ("`P_author` zero-context (sealed), Opus 4.8", "P_author:opus48"),
    ("`P_author_doc` isolated, Sonnet 5", "dossier_iso:sonnet"),
    ("`P_author` zero-context, Sonnet 5", "P_author:sonnet"),
    ("`P_author_doc` live, Opus 4.8", "dossier_live:opus48"),
    ("`P_author_doc` live, Sonnet 5", "dossier_live:sonnet"),
    ("`O_diff`, Sonnet 5", "O_diff:sonnet"),
    ("`O_diff`, Opus 4.8", "O_diff:opus48"),
    ("`O_diff`, GPT-6 Sol", "O_diff:sol")])
def test_plan_rows_map_to_part_2s_cells(view, cell):
    assert se.cell_of(view) == cell


def test_an_unknown_view_or_judge_is_refused():
    with pytest.raises(ValueError):
        se.cell_of("`P_reader`, Opus 4.8")
    with pytest.raises(ValueError):
        se.cell_of("`O_diff`, Kimi K3")


def test_plan_section_2_6_is_read_row_by_row_and_summed():
    pu = se.plan_units((ROOT / se.PLAN).read_text(encoding="utf-8"))
    rows = pu["rows"]
    assert len(rows) == 9 and len({r["cell"] for r in rows}) == 9
    assert all(r["item_units"] == 232 for r in rows)
    assert {r["cell"] for r in rows if r["lone_units"]} == set(se.PER_AGENT)
    assert all(r["lone_units"] == 438 for r in rows if r["cell"] in se.PER_AGENT)
    assert (sum(r["item_units"] for r in rows), sum(r["lone_units"] for r in rows)) == (2088, 1752)
    assert pu["stated_totals"] == {"item_units": 2088, "lone_units": 1752, "units": 3840}


def test_part_2s_keys_are_read_by_the_plans_names():
    """`lone_units` in Part 2's estimate rows are the item units; `singleton_units` the lone-line units."""
    est = {"dollars": 0.0, "rows": {"a": {"lone_units": 10, "singleton_units": 0}, "dossier_live:sonnet": {"lone_units": 10, "singleton_units": 20}}}
    uc = {"a": {"used": 1.0}, "dossier_live:sonnet": {"used": 0.5}}
    g = se.part2_gap(est, uc, 9, 18)
    assert g["part2_dollars_recomputed"] == 10 + 30 * 0.5
    assert g["step1_net_counts"] == 9 + 27 * 0.5          # item units on both cells, lone-line units on the second
    assert g["step2_live_lone_stripped"] == 9 + 9 * 0.5    # the live cell's lone-line units stripped


def test_h1_reproduces_part_2_and_the_two_steps():
    v3b = _v3b()
    est, uc = v3b["estimate"]["T2+S2"], v3b["unit_costs"]
    g = se.part2_gap(est, uc, 232, 438)
    assert g["part2_dollars_recomputed"] == pytest.approx(est["dollars"], abs=1e-9)
    assert round(est["dollars"], 2) == 98.17 and round(g["step1_net_counts"], 2) == 91.86
    assert round(g["plan9_remainder_after_live_strip_gross"], 2) == 72.86
    pu = se.plan_units((ROOT / se.PLAN).read_text(encoding="utf-8"))
    h1 = se.price(pu["rows"], uc)
    assert h1["dollars"] == pytest.approx(g["step2_live_lone_stripped"], abs=1e-9)
    assert abs(h1["dollars"] - 68.17) < 0.01


def test_the_basis_is_the_larger_measured_one_and_sol_uses_brief_09s_estimate_basis():
    uc = _v3b()["unit_costs"]
    for c, v in uc.items():
        b = se.basis(uc, c)
        if c == "O_diff:sol":
            assert b["source"] == "brief09 estimate basis"
        else:
            assert b["used"] == max(v["B1/T1v3"], v["B4-R"])


# ── H2 step 2 ─────────────────────────────────────────────────────────────────────────────────────

def _item(item_draws, lines, iid="c1"):
    return {"item_id": iid, "regime": "control", "writer": "w", "draws": {"valid_draws": [list(x) for x in item_draws]},
            "lone_lines": [{"valid_draws": [list(x) for x in ln], "n_valid": len(ln), "n_drawable": len(ln)} for ln in lines]}


def test_item_pairs_are_the_functions_pairs():
    it = _item([(D1, "a"), (D2, "b"), (D2, "a"), (D1, "c")], [[]] * 3)
    assert se.item_pairs(it) == [((D1, "a"), (D2, "b")), ((D2, "b"), (D1, "c")), ((D2, "a"), (D1, "c"))]


def test_classes():
    many = [(D1, x) for x in "defg"]
    ok = se.control_check(_item([(D1, "a"), (D2, "b")], [many] * 3))
    assert ok["n_pairs"] == 1 and ok["variants"]["different_authors"]["class"] == "all pairs pass"
    # some fall short: pairs (a, b) and (a, c); line 2's draws by b and d keep two authors only when b is not in the pair
    v = se.control_check(_item([(D1, "a"), (D2, "b"), (D2, "c")], [many, [(D1, "b"), (D1, "d")], many]))["variants"]
    v = v["different_authors"]
    assert v["pairs_meeting_need_per_line"] == [2, 1, 2] and v["pairs_all_three_lines_met"] == 1
    assert v["class"] == "some fall short" and v["pairs_short"] == 1 and v["lines_short_under_some_pair"] == [2]
    # none: the one pair (a, b) leaves line 3 a single author
    v = se.control_check(_item([(D1, "a"), (D2, "b")], [many, many, [(D1, "a"), (D2, "b"), (D1, "c")]]))["variants"]
    v = v["different_authors"]
    assert v["pairs_meeting_need_per_line"] == [1, 1, 0] and v["class"] == "none: no pair meets the need"
    # no valid pair at all: both item draws on one day
    v = se.control_check(_item([(D1, "a"), (D1, "b")], [many] * 3))["variants"]["different_authors"]
    assert v["class"] == "none: no valid pair"


def test_the_days_variant_is_beside_and_stricter():
    same_day = [(D1, x) for x in "defg"]
    v = se.control_check(_item([(D1, "a"), (D2, "b")], [same_day] * 3))["variants"]
    assert v["different_authors"]["class"] == "all pairs pass"
    assert v["beside_different_days_too"]["class"] == "none: no pair meets the need"


def test_the_per_pair_counts_agree_with_the_pinned_function():
    many = [(D1, x) for x in "defg"] + [(D2, "h")]
    it = _item([(D1, "a"), (D2, "b"), (D2, "e")], [many, [(D1, "b"), (D1, "c"), (D2, "d")], [(D1, "e"), (D2, "f")]])
    other = dict(_item([(D1, "x"), (D2, "y")], [[]] * 3, iid="z1"), regime="candidate")
    dry = {"items": [it, other]}
    f = se.function_fields(dry, ["c1"])
    assert f["per_item"]["c1"] == f["all"]
    assert f["all"]["net_candidate_lines"] == 3            # the real candidate is not read in this call
    assert se.agrees_with_function(se.control_check(it), f["per_item"]["c1"])
    assert dry["items"][0]["regime"] == "control"          # the table itself is not relabelled


def test_compare_items_names_each_differing_field():
    a = {"items": [{"item_id": "1", "regime": "control", "lone_lines": [], "x": 1},
                   {"item_id": "2", "regime": "candidate", "lone_lines": [1], "x": 1}]}
    b = {"items": [{"item_id": "1", "regime": "control", "lone_lines": [1, 2, 3], "x": 1},
                   {"item_id": "2", "regime": "candidate", "lone_lines": [1], "x": 1}]}
    c = se.compare_items(a, b)
    assert c["diffs"] == [{"item_id": "1", "regime": "control", "field": "lone_lines"}] and c["only_control_lone_lines"]
    b["items"][1]["x"] = 2
    assert not se.compare_items(a, b)["only_control_lone_lines"]


# ── H3 ────────────────────────────────────────────────────────────────────────────────────────────

def test_the_k2_arm_is_not_executionally_clean():
    c = se.k2_cleanness()
    assert c["(i) no new application code"]["passes"] is False
    assert c["(ii) no new arm or stream beyond tag 5"]["passes"] is True
    assert c["(iii) valid draws at $0 by brief 26's method, read by restricted mode unchanged"]["passes"] is False
    assert c["clean"] is False


# ── the whole record, on the real files ───────────────────────────────────────────────────────────

@pytest.mark.skipif(not (ROOT / se.V1).exists(), reason="inserter-dry-run-v1.json has not been written")
def test_build_on_the_real_files():
    r = se.build()
    assert r["h1"]["sums_equal_plan"] and abs(r["h1"]["dollars"] - 68.17) < 0.01
    assert r["h2"]["table"]["compare_to_v0"]["only_control_lone_lines"]
    assert list(r["h2"]["table"]["candidates_reproduced"].values()) == [219, 219, 219, 177, 18018, 462]
    assert r["h2"]["net_controls"]["n"] == 21 and all(r["h2"]["agrees_with_function"].values())
    assert sum(r["h2"]["classes"]["different_authors"].values()) == 21
    a = r["h2"]["addon"]
    assert abs(a["dollars_max_all_net"] - 8.45) < 0.01 and a["dollars"] <= a["dollars_max_all_net"] + 1e-12
    assert a["units_per_view"] == 6 * a["remaining_items"]
    assert abs(a["gap_to_part2"]["part2_recomputed"] - a["gap_to_part2"]["part2_gross"]) < 1e-9
    assert r["h3"]["skipped"] and abs(r["h3"]["price"]["dollars"] - 3.06) < 0.01
    f = r["confirmation"][0]
    assert f["form"] == "H1 + H2" and f["stop_2x"] == 2 * f["dollars"]
    assert f["dollars"] == pytest.approx(r["h1"]["dollars"] + a["dollars"])
    assert all(x["form"] != "H1 + H2 + H3" for x in r["confirmation"])
