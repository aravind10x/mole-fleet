"""Offline tests for stage3_b3_partj_lift_v01 (brief 34, dated note 2, item 2): the paired Spearman difference on the
record's own resamples, bootstrap intervals for the pass-1 lift means (overall and by writer), the counts among the
triples whose composition clears the bar, and the append that leaves the v0 record's bytes where they are. The
synthetic dozen of the v0 test module stands in for Part J; every score is made up by the tests.

    cd work/checks && ../mole-fork/.venv/bin/python -I -m pytest -q test_stage3_b3_partj_lift_v01.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_b3_partj_lift as pl  # noqa: E402
import stage3_b3_partj_lift_v01 as v01  # noqa: E402
from test_stage3_b3_partj_lift import CANDIDATES, ID_SENTINEL, REASON_SENTINEL, make_inputs  # noqa: E402

BARS = {"composition_bar": 75, "statement_bar": 60, "spread_bar": 10}


# ---- the resamples and the paired difference -----------------------------------------------------------------------

def test_per_resample_values_reproduce_the_v0_interval_and_match_scipy():
    x = [80, 78, 75, 60, 76, 70, 40, 90, 70, 50, 85, 62]
    y = [58, 48, 60, 70, 60, 52, 25, 55, 60, 30, 61, 45]
    idx = v01.resample_indices(len(x), 200, 20261102)
    vals = v01.spearman_values(x, y, idx)
    lo, hi, degenerate = v01.percentile_ci(vals)
    assert (lo, hi, degenerate) == pl.bootstrap_spearman_ci(x, y, 200, 20261102)
    for row, got in zip(idx[:25].tolist(), vals[:25]):  # an independent rho for the first resamples
        want = stats.spearmanr([x[i] for i in row], [y[i] for i in row]).statistic
        assert (math.isnan(got) and math.isnan(want)) or got == pytest.approx(want, abs=1e-12)


def test_the_paired_difference_is_taken_resample_by_resample():
    x = [80, 78, 75, 60, 76, 70, 40, 90, 70, 50, 85, 62]
    top = [58, 48, 60, 70, 60, 52, 25, 55, 60, 30, 61, 45]
    mean = [50.0, 45.0, 52.0, 50.0, 57.7, 49.0, 23.7, 52.3, 59.0, 20.0, 60.0, 40.0]
    idx = v01.resample_indices(len(x), 300, 7)
    a, b = v01.spearman_values(x, top, idx), v01.spearman_values(x, mean, idx)
    diff = v01.paired_differences(a, b)
    assert [d for d in diff if not math.isnan(d)] == [p - q for p, q in zip(a, b) if not (math.isnan(p) or math.isnan(q))]
    est, lo, hi, degenerate = v01.paired_difference_ci(x, top, mean, 300, 7)
    assert est == pytest.approx(stats.spearmanr(x, top).statistic - stats.spearmanr(x, mean).statistic, abs=1e-12)
    assert (lo, hi, degenerate) == v01.percentile_ci(diff)
    assert lo < hi


def test_a_resample_degenerate_on_either_side_is_dropped_from_the_difference():
    nan = float("nan")
    diff = v01.paired_differences([0.5, nan, 0.9, 0.1], [0.2, 0.3, nan, 0.05])
    assert diff[0] == pytest.approx(0.3) and math.isnan(diff[1]) and math.isnan(diff[2]) and diff[3] == pytest.approx(0.05)
    lo, hi, degenerate = v01.percentile_ci(diff)
    assert degenerate == 2 and 0.05 <= lo <= hi <= 0.3


# ---- the lift means --------------------------------------------------------------------------------------------------

def test_mean_by_resample_overall_and_for_the_rows_of_one_writer():
    lifts = [10, 20, 30, 40]
    writers = ["a", "a", "b", "b"]
    idx = np.array([[0, 1, 2, 3], [0, 0, 2, 2], [2, 3, 3, 3], [1, 1, 1, 1]])
    assert v01.mean_by_resample(lifts, idx).tolist() == [25.0, 20.0, 37.5, 20.0]
    a = v01.mean_by_resample(lifts, idx, [w == "a" for w in writers])
    assert a[:2].tolist() == [15.0, 10.0] and math.isnan(a[2]) and a[3] == 20.0  # row 3 draws no row of writer a
    b = v01.mean_by_resample(lifts, idx, [w == "b" for w in writers])
    assert b[0] == 35.0 and b[1] == 30.0 and b[2] == 37.5 and math.isnan(b[3])


def test_normal_interval_is_the_mean_plus_or_minus_1_96_standard_errors():
    lo, hi = v01.normal_ci([10, 20, 30, 40])
    se = float(np.std([10, 20, 30, 40], ddof=1)) / 2
    assert (lo, hi) == pytest.approx((25 - 1.96 * se, 25 + 1.96 * se))


# ---- the counts among triples whose composition clears the bar ------------------------------------------------------

ROWS = [
    {"writer": "sonnet55", "p1": [50, 70, 55], "c1": 80},   # above the bar; lines 20 apart; a line over 60
    {"writer": "sonnet55", "p1": [40, 55, 60], "c1": 76},   # lines 20 apart; every line at or under 60
    {"writer": "sonnet55", "p1": [10, 70, 70], "c1": 75},   # at the bar, not above it: out of the subset
    {"writer": "sonnet55", "p1": [58, 60, 59], "c1": 90},   # lines 2 apart; every line at or under 60
    {"writer": "glm53", "p1": [61, 62, 63], "c1": 77},      # lines 2 apart; every line over 60
    {"writer": "glm53", "p1": [20, 45, 60], "c1": 95},      # lines 40 apart; every line at or under 60
    {"writer": "glm53", "p1": [30, 30, 30], "c1": 60},      # below the bar: out of the subset
]


def test_counts_among_triples_above_the_bar_by_writer_and_pooled():
    got = v01.high_composition_counts(ROWS, BARS)
    assert got["Sonnet 5.5"] == {"n": 3, "lines_more_than_10_apart": 2, "every_line_at_or_under_60": 2,
                                 "within_10_and_every_line_at_or_under_60": 1}
    assert got["GLM 5.3"] == {"n": 2, "lines_more_than_10_apart": 1, "every_line_at_or_under_60": 1,
                              "within_10_and_every_line_at_or_under_60": 0}
    assert got["pooled"] == {"n": 5, "lines_more_than_10_apart": 3, "every_line_at_or_under_60": 3,
                             "within_10_and_every_line_at_or_under_60": 1}


def test_a_spread_of_exactly_10_is_not_more_than_10_apart_and_a_line_at_60_is_at_or_under_60():
    got = v01.high_composition_counts([{"writer": "glm53", "p1": [50, 60, 55], "c1": 76}], BARS)["pooled"]
    assert got["lines_more_than_10_apart"] == 0 and got["every_line_at_or_under_60"] == 1


# ---- the appended section ---------------------------------------------------------------------------------------------

@pytest.fixture()
def appended(tmp_path):
    root = make_inputs(tmp_path / "rater")
    rec = tmp_path / "rec"
    pl.write_record(pl.build_record(root, resamples=300, seed=20261102), rec)
    before = {n: (rec / n).read_bytes() for n in ("partj-lift-v0.json", "partj-lift-v0.md")}
    v01.append_v01(root, rec)
    return {"root": root, "rec": rec, "before": before,
            "json": (rec / "partj-lift-v0.json").read_text(), "md": (rec / "partj-lift-v0.md").read_text(),
            "section": json.loads((rec / "partj-lift-v0.json").read_text())["v0_1"]}


def test_everything_above_the_section_is_byte_for_byte_the_v0_record(appended):
    old_json = appended["before"]["partj-lift-v0.json"].decode()
    assert appended["json"].startswith(old_json.rstrip("\n")[:-1].rstrip("\n") + ",\n")
    assert appended["md"].startswith(appended["before"]["partj-lift-v0.md"].decode())
    new = json.loads(appended["json"])
    old = json.loads(old_json)
    assert {k: v for k, v in new.items() if k != "v0_1"} == old and list(new)[-1] == "v0_1"
    assert len(appended["section"]["built_on"]["v0_json_sha256_before_append"]) == 64


def test_the_section_reuses_the_records_own_resamples_and_proves_it(appended):
    s = appended["section"]
    assert s["resamples"] == {"n": 300, "seed": 20261102}
    assert s["own_resamples_check"]["reproduced_rows"] == 6 and s["own_resamples_check"]["all_equal"] is True


def test_paired_difference_rows_equal_the_difference_of_the_v0_rows(appended):
    old = json.loads(appended["before"]["partj-lift-v0.json"].decode())
    for p in ("pass1", "pass2"):
        row = appended["section"]["paired_difference"][p]
        want = old["spearman"][p]["composition_vs_max_statement"]["rho"] - old["spearman"][p]["composition_vs_mean_statement"]["rho"]
        assert row["estimate"] == pytest.approx(want, abs=1e-12)
        assert row["n"] == 12 and row["resamples"] == 300 and row["ci95"][0] <= row["ci95"][1]
        assert row["rho_composition_vs_max_statement"] == old["spearman"][p]["composition_vs_max_statement"]["rho"]
    c1 = [c[2] for c in CANDIDATES]
    top, mean = [max(c[1]) for c in CANDIDATES], [sum(c[1]) / 3 for c in CANDIDATES]
    assert appended["section"]["paired_difference"]["pass1"]["estimate"] == pytest.approx(
        stats.spearmanr(c1, top).statistic - stats.spearmanr(c1, mean).statistic, abs=1e-12)


def test_lift_mean_intervals_are_for_pass_1_overall_and_by_writer(appended):
    m = appended["section"]["lift_mean_intervals_pass1"]
    assert m["min_lift_needed"] == 16
    assert m["overall"]["mean"] == pytest.approx(212 / 12) and m["overall"]["n"] == 12
    assert m["by_writer"]["Sonnet 5.5"]["mean"] == pytest.approx(106 / 7) and m["by_writer"]["GLM 5.3"]["n"] == 5
    for row in [m["overall"], *m["by_writer"].values()]:
        assert row["bootstrap_ci95"][0] <= row["bootstrap_ci95"][1] and row["normal_ci95"][0] < row["mean"] < row["normal_ci95"][1]
        assert row["ci_includes_min_lift_needed"] == (row["bootstrap_ci95"][0] <= 16 <= row["bootstrap_ci95"][1])
    sd = float(np.std([22, 30, 15, -10, 16, 18, 15, 35, 10, 20, 24, 17], ddof=1))
    assert m["overall"]["normal_ci95"] == pytest.approx([212 / 12 - 1.96 * sd / math.sqrt(12), 212 / 12 + 1.96 * sd / math.sqrt(12)])


def test_the_counts_row_agrees_with_the_v0_certified_count(appended):
    c = appended["section"]["composition_above_bar_pass1"]
    # composition above 75 on pass 1: triples 1, 2, 5 | 8, 11 of the dozen; none has lines more than 10 apart
    assert c["composition_above"] == 75
    assert c["by_writer"]["Sonnet 5.5"]["n"] == 3 and c["by_writer"]["GLM 5.3"]["n"] == 2 and c["pooled"]["n"] == 5
    assert c["pooled"]["lines_more_than_10_apart"] == 0 and c["pooled"]["every_line_at_or_under_60"] == 4
    assert c["pooled"]["within_10_and_every_line_at_or_under_60"] == 4 == json.loads(appended["json"])["counts"]["certified_pass1"]


def test_the_review_sessions_values_sit_beside_the_recomputed_ones_with_the_difference(appended):
    checks = appended["section"]["check_values"]
    assert [c["name"] for c in checks] == [
        "paired_difference_pass1_estimate", "paired_difference_pass1_ci_lo", "paired_difference_pass1_ci_hi",
        "paired_difference_pass2_estimate", "paired_difference_pass2_ci_lo", "paired_difference_pass2_ci_hi",
        "lift_pass1_overall_mean_normal_ci_lo", "lift_pass1_overall_mean_normal_ci_hi",
        "lift_pass1_overall_mean_bootstrap_ci_lo", "lift_pass1_overall_mean_bootstrap_ci_hi",
        "composition_above_bar_pass1_n", "composition_above_bar_pass1_lines_more_than_10_apart",
        "composition_above_bar_pass1_every_line_at_or_under_60"]
    assert [c["review_note"] for c in checks] == [0.172, 0.044, 0.308, 0.187, 0.069, 0.325, 10.6, 16.3, 10.6, 16.3, 19, 18, 11]
    assert all({"recomputed", "difference", "matches_printed_precision", "like_for_like"} <= set(c) for c in checks)
    by = {c["name"]: c for c in checks}
    assert by["lift_pass1_overall_mean_normal_ci_lo"]["like_for_like"] is True
    assert by["lift_pass1_overall_mean_bootstrap_ci_lo"]["like_for_like"] is False
    assert appended["section"]["agreement"]["all_match"] is False  # a synthetic dozen cannot reproduce Part J's values
    assert "lift_pass1_overall_mean_bootstrap_ci_lo" not in appended["section"]["agreement"]["differing"]


def test_the_markdown_section_is_appended_and_carries_the_three_blocks(appended):
    tail = appended["md"][len(appended["before"]["partj-lift-v0.md"].decode()):]
    for needle in ("v0.1", "Paired difference", "Lift means", "composition above", "review session's indicative values"):
        assert needle in tail, needle
    assert "| composition_above_bar_pass1_n | 19 | 5 | -14 | NO | yes |" in tail  # counts are shown as integers


def test_an_append_twice_is_refused(appended):
    with pytest.raises(SystemExit, match="already"):
        v01.append_v01(appended["root"], appended["rec"])


def test_a_v0_record_from_another_script_is_refused(tmp_path):
    root = make_inputs(tmp_path / "rater")
    rec = tmp_path / "rec"
    pl.write_record(pl.build_record(root, resamples=100, seed=1), rec)
    j = json.loads((rec / "partj-lift-v0.json").read_text())
    j["script"]["sha256"] = "0" * 64
    (rec / "partj-lift-v0.json").write_text(json.dumps(j, indent=1) + "\n")
    with pytest.raises(SystemExit, match="v0 script"):
        v01.append_v01(root, rec)


def test_score_files_that_changed_since_the_v0_record_are_refused(tmp_path):
    root = make_inputs(tmp_path / "rater")
    rec = tmp_path / "rec"
    pl.write_record(pl.build_record(root, resamples=100, seed=1), rec)
    with (root / "ratings-b3-statements-p2.jsonl").open("a") as f:
        f.write(json.dumps({"statement_id": "extra", "score": 1}) + "\n")
    with pytest.raises(SystemExit, match="changed since the v0 record"):
        v01.append_v01(root, rec)


def test_resamples_that_do_not_reproduce_the_v0_intervals_are_refused_and_nothing_is_written(tmp_path):
    root = make_inputs(tmp_path / "rater")
    rec = tmp_path / "rec"
    pl.write_record(pl.build_record(root, resamples=100, seed=1), rec)
    j = json.loads((rec / "partj-lift-v0.json").read_text())
    j["spearman"]["pass2"]["composition_vs_spread"]["ci95"][0] += 0.01
    (rec / "partj-lift-v0.json").write_text(json.dumps(j, indent=1) + "\n")
    before = (rec / "partj-lift-v0.json").read_bytes(), (rec / "partj-lift-v0.md").read_bytes()
    with pytest.raises(SystemExit, match="does not reproduce"):
        v01.append_v01(root, rec)
    assert ((rec / "partj-lift-v0.json").read_bytes(), (rec / "partj-lift-v0.md").read_bytes()) == before


def test_the_writer_refuses_a_section_carrying_a_text_field_and_leaves_the_files_alone(tmp_path):
    rec = tmp_path / "rec2"
    root = make_inputs(tmp_path / "rater2")
    pl.write_record(pl.build_record(root, resamples=100, seed=1), rec)
    before = (rec / "partj-lift-v0.json").read_bytes(), (rec / "partj-lift-v0.md").read_bytes()
    with pytest.raises(ValueError):
        v01.write_appended(rec, {"reason": "free text"})
    with pytest.raises(ValueError):
        v01.write_appended(rec, {"nested": [{"statement": "x"}]})
    assert ((rec / "partj-lift-v0.json").read_bytes(), (rec / "partj-lift-v0.md").read_bytes()) == before


def test_no_reason_and_no_id_reaches_a_file_or_stdout(tmp_path, capsys):
    root = make_inputs(tmp_path / "rater")
    rec = tmp_path / "rec"
    pl.write_record(pl.build_record(root, resamples=100, seed=1), rec)
    capsys.readouterr()
    assert v01.main(["--rater-dir", str(root), "--record-dir", str(rec)]) == 0
    printed = capsys.readouterr().out
    written = (rec / "partj-lift-v0.json").read_text() + (rec / "partj-lift-v0.md").read_text()
    for bad in (REASON_SENTINEL, ID_SENTINEL, "TK0", "SK0"):
        assert bad not in printed and bad not in written
    assert "candidates-" not in written and "v0_1" in written
