"""Tests for stage3_elicitation_matching.py (brief 30 Part 3, note 7 item 4 and note 8: round 2's matching
rule fixed before writer round 1, and the $0 dry run of it at the 10-point band). The rule: many-to-one
within writer x document x composition band; every certified item in a stratum that holds a
quiet-but-illegible item is used, the certified arm is never cut to the comparison arm's size; the effective
n is 2 / (1/n_c + 1/n_i) on the matched strata. Synthetic items only: no real item, no B3 file."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_matching as mt  # noqa: E402

CERT, ILL = "certified", "quiet_but_illegible"


def it(writer="A", doc="d1", comp=55.0, cls=CERT):
    return {"writer": writer, "document": doc, "composition": comp, "class": cls}


# ---- the band -------------------------------------------------------------------------------------

def test_band_index_is_half_open_with_a_closed_top():
    assert mt.band_index(0.0, 10) == 0
    assert mt.band_index(9.99, 10) == 0
    assert mt.band_index(10.0, 10) == 1
    assert mt.band_index(100.0, 10) == 9, "a composition of exactly 100 joins the top band, not an eleventh"
    assert mt.band_index(100.0, 20) == 4


@pytest.mark.parametrize("bad", [-0.1, 100.1, float("nan")])
def test_band_index_refuses_a_score_off_the_scale(bad):
    with pytest.raises(ValueError):
        mt.band_index(bad, 10)


@pytest.mark.parametrize("w", [0, -10, 33])
def test_band_index_refuses_a_width_that_does_not_tile_the_scale(w):
    with pytest.raises(ValueError):
        mt.band_index(50.0, w)


# ---- the effective n ------------------------------------------------------------------------------

def test_effective_n_is_the_harmonic_form():
    assert mt.effective_n(26, 12) == pytest.approx(2 / (1 / 26 + 1 / 12))
    assert mt.effective_n(26, 12) == pytest.approx(16.4210526, abs=1e-6)
    assert mt.effective_n(12, 12) == pytest.approx(12.0)


def test_effective_n_is_zero_when_either_arm_is_empty():
    assert mt.effective_n(0, 12) == 0.0
    assert mt.effective_n(26, 0) == 0.0


# ---- the matching ---------------------------------------------------------------------------------

def test_certified_arm_is_never_cut_to_the_comparison_arms_size():
    items = [it(cls=CERT, comp=51 + k * 0.1) for k in range(5)] + [it(cls=ILL, comp=55.0)]
    m = mt.match(items, 10)
    assert (m["n_c"], m["n_i"]) == (5, 1)


def test_certified_item_in_a_stratum_with_no_illegible_item_is_dropped_and_counted():
    items = [it(cls=CERT, comp=15.0), it(cls=CERT, comp=55.0), it(cls=ILL, comp=55.0)]
    m = mt.match(items, 10)
    assert (m["n_c"], m["n_i"]) == (1, 1)
    assert m["unmatched_certified"] == 1 and m["unmatched_illegible"] == 0


def test_illegible_item_in_a_stratum_with_no_certified_item_is_dropped_and_counted():
    items = [it(cls=CERT, comp=55.0), it(cls=ILL, comp=55.0), it(cls=ILL, comp=85.0)]
    m = mt.match(items, 10)
    assert (m["n_c"], m["n_i"]) == (1, 1)
    assert m["unmatched_illegible"] == 1


@pytest.mark.parametrize("field,other", [("writer", "B"), ("document", "d2"), ("composition", 65.0)])
def test_a_difference_in_writer_document_or_band_breaks_the_stratum(field, other):
    a = it(cls=CERT)
    b = it(cls=ILL)
    b[field] = other
    m = mt.match([a, b], 10)
    assert (m["n_c"], m["n_i"], m["strata_used"]) == (0, 0, 0)
    assert m["n_eff"] == 0.0


def test_other_classes_join_neither_arm():
    items = [it(cls=c) for c in ("loud", "not_evaluable", "part_derivable", "mixed")] + [it(cls=CERT), it(cls=ILL)]
    m = mt.match(items, 10)
    assert (m["n_c"], m["n_i"], m["strata_used"]) == (1, 1, 1)
    assert m["n_c_total"] == 1 and m["n_i_total"] == 1


def test_an_unknown_class_is_refused_not_silently_dropped():
    with pytest.raises(ValueError):
        mt.match([it(cls="certfied")], 10)


def test_match_reports_totals_strata_and_n_eff():
    items = [it(cls=CERT, comp=52), it(cls=CERT, comp=57), it(cls=CERT, comp=58), it(cls=ILL, comp=53),
             it(cls=CERT, comp=91), it(cls=ILL, comp=12)]
    m = mt.match(items, 10)
    assert m["n_c_total"] == 4 and m["n_i_total"] == 2
    # band 5 (50 to 59.99) holds three certified and one illegible; the 91 and the 12 have no partner
    assert (m["n_c"], m["n_i"]) == (3, 1)
    assert m["strata_used"] == 1
    assert m["n_eff"] == pytest.approx(2 / (1 / 3 + 1 / 1))


def test_coarser_nested_bands_never_lower_the_matched_counts():
    import random
    rng = random.Random(7)
    items = [it(writer=rng.choice("AB"), doc=rng.choice(["d1", "d2", "d3"]), comp=rng.uniform(0, 100),
                cls=rng.choice([CERT, CERT, ILL])) for _ in range(120)]
    prev = (-1, -1)
    for w in (5, 10, 20, 50, 100):
        m = mt.match(items, w)
        assert m["n_c"] >= prev[0] and m["n_i"] >= prev[1], f"width {w} lowered a matched count"
        prev = (m["n_c"], m["n_i"])


# ---- the dry run ----------------------------------------------------------------------------------

def test_dry_run_is_deterministic_by_seed_and_changes_with_it():
    a = mt.dry_run(seed=mt.SEED, reps=40, scenarios=[(26, 12)], widths=(10,))
    b = mt.dry_run(seed=mt.SEED, reps=40, scenarios=[(26, 12)], widths=(10,))
    c = mt.dry_run(seed=mt.SEED + 1, reps=40, scenarios=[(26, 12)], widths=(10,))
    assert mt.canonical(a) == mt.canonical(b)
    assert mt.canonical(a) != mt.canonical(c)


def test_dry_run_reports_each_width_and_scenario_with_retention_and_n_eff():
    r = mt.dry_run(seed=mt.SEED, reps=60, scenarios=[(26, 12), (58, 21)], widths=(5, 10, 20))
    assert r["seed"] == mt.SEED and r["reps"] == 60
    rows = r["rows"]
    assert len(rows) == 6
    for row in rows:
        assert {"n_certified", "n_illegible", "width", "retained_certified", "retained_illegible",
                "n_eff_mean", "n_eff_p10", "n_eff_p90", "share_with_no_matched_stratum"} <= set(row)
        assert 0.0 <= row["retained_certified"] <= 1.0 and 0.0 <= row["retained_illegible"] <= 1.0
    by = {(row["n_certified"], row["width"]): row for row in rows}
    assert by[(26, 20)]["n_eff_mean"] >= by[(26, 10)]["n_eff_mean"] >= by[(26, 5)]["n_eff_mean"]


def test_dry_run_with_a_single_document_and_writer_matches_nearly_everything():
    r = mt.dry_run(seed=mt.SEED, reps=40, scenarios=[(26, 12)], widths=(10,), writers=1, documents=1)
    assert r["rows"][0]["retained_illegible"] > 0.9


def test_module_reads_no_file_and_imports_only_the_standard_library():
    src = (HERE / "stage3_elicitation_matching.py").read_text()
    tree = ast.parse(src)
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods |= {n.name.split(".")[0] for n in node.names}
        elif isinstance(node, ast.ImportFrom):
            mods.add((node.module or "").split(".")[0])
    stdlib = set(sys.stdlib_module_names)
    assert mods - {"__future__"} <= stdlib, f"non-stdlib imports: {mods - stdlib}"
    for banned in ("open(", "read_text", "read_bytes", "load_world", "b3-results", "s3-"):
        assert banned not in src, f"{banned!r} in the matching module"


def test_cli_passes_the_strata_parameters_through_to_the_run(tmp_path):
    out = tmp_path / "r.json"
    assert mt.main(["dry-run", "--out", str(out), "--reps", "5", "--documents", "1", "--writers", "1", "--sd", "9.5"]) == 0
    import json
    r = json.loads(out.read_text())
    assert (r["documents"], r["writers"], r["composition"]["sd"], r["reps"]) == (1, 1, 9.5, 5)
