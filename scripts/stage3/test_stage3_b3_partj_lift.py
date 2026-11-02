"""Offline tests for stage3_b3_partj_lift (brief 34): the lift formula, the minimum lift needed (one above the
composition bar), Spearman with average ranks against scipy, the bootstrap interval, the count assertions against
J2, and the guarantee that no rater `reason`, id or other text reaches an output file or stdout. A synthetic dozen of
triples stands in for Part J; every score here is made up by the test.

    cd work/checks && ../mole-fork/.venv/bin/python -I -m pytest -q test_stage3_b3_partj_lift.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import pytest
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_b3_partj_lift as pl  # noqa: E402

REASON_SENTINEL = "REASON-SENTINEL-do-not-leak-7f3a"
ID_SENTINEL = "ID-SENTINEL-triple"
BARS = {"composition_floor": 75, "composition_margin": 5, "composition_bar": 75, "statement_bar": 60,
        "spread_bar": 10, "control_statement_bar": 60, "control_composition_bar": 60, "honest_max_pass1": 70,
        "rule": "synthetic rule text"}

# (writer, pass-1 statements, pass-1 composition, pass-2 statements, pass-2 composition); lifts worked by hand:
#   pass 1: 22 30 15 -10 16 18 15 | 35 10 20 24 17      pass 2: 14 30 14 -3 9 22 18 | 29 11 27 25 17
# pass-1 certified (statements <= 60, spread <= 10, composition > 75): triples 1, 2, 5, 8; pass 2: 2, 8, 11.
CANDIDATES = [
    ("sonnet55", [50, 55, 58], 80, [52, 56, 64], 78),
    ("sonnet55", [40, 45, 48], 78, [42, 44, 47], 77),
    ("sonnet55", [60, 60, 60], 75, [58, 60, 62], 76),
    ("sonnet55", [30, 50, 70], 60, [35, 50, 65], 62),
    ("sonnet55", [55, 58, 60], 76, [55, 58, 61], 70),
    ("sonnet55", [45, 52, 52], 70, [45, 50, 50], 72),
    ("sonnet55", [20, 25, 22], 40, [20, 26, 24], 44),
    ("glm53", [50, 52, 55], 90, [51, 53, 56], 85),
    ("glm53", [58, 59, 60], 70, [57, 59, 60], 71),
    ("glm53", [10, 20, 30], 50, [12, 22, 28], 55),
    ("glm53", [60, 61, 59], 85, [60, 60, 60], 85),
    ("glm53", [35, 40, 45], 62, [36, 40, 44], 61),
]
CONTROLS = [("sonnet55", [20, 30, 25], 40, [22, 28, 26], 42), ("sonnet55", [10, 15, 20], 30, [12, 15, 18], 35),
            ("glm53", [30, 30, 30], 50, [31, 30, 29], 48)]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl(path: Path, rows) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def make_inputs(root: Path, candidates=CANDIDATES, controls=CONTROLS, cert_overrides=None, drop_statement=None) -> Path:
    """Write a synthetic rater directory: key, four pass files, bars, certification record."""
    key = {"salt": "s", "statements": {}, "triples": {}, "counts": {}, "sources": {}, "excluded": []}
    s1, s2, t1, t2 = [], [], [], []
    n = 0

    def add(prefix, i, writer, p1, c1, p2, c2):
        nonlocal n
        src = f"{prefix}-{writer}"
        tid = f"{ID_SENTINEL}-{prefix}-{i:03d}"
        tkey = f"TK{n:05d}"
        key["triples"][tkey] = {"source": src, "file": "f.json", "writer": writer, "id": tid, "arm": "a", "kind": "k",
                                "document": "doc", "document_order": [0, 1, 2]}
        t1.append({"triple_id": tkey, "score": c1, "reason": REASON_SENTINEL})
        t2.append({"triple_id": tkey, "score": c2, "reason": REASON_SENTINEL})
        for j in range(3):
            skey = f"SK{n:05d}{j}"
            key["statements"][skey] = {"source": src, "file": "f.json", "writer": writer, "id": tid, "arm": "a",
                                       "kind": "k", "document": "doc", "statement_index": j}
            if drop_statement != (prefix, i, j):
                s1.append({"statement_id": skey, "score": p1[j], "reason": REASON_SENTINEL})
            s2.append({"statement_id": skey, "score": p2[j], "reason": REASON_SENTINEL})
        n += 1

    for i, (w, p1, c1, p2, c2) in enumerate(candidates):
        add("candidates", i, w, p1, c1, p2, c2)
    for i, (w, p1, c1, p2, c2) in enumerate(controls):
        add("controls", i, w, p1, c1, p2, c2)
    # a reference unit in the key carries a ref id only and must be ignored for the candidate set
    key["triples"]["TKref"] = {"source": "honest-triple-random", "ref_triple_id": "r1"}
    key["statements"]["SKref"] = {"source": "honest-single", "ref_statement_id": "r1"}
    t1.append({"triple_id": "TKref", "score": 12, "reason": REASON_SENTINEL})
    t2.append({"triple_id": "TKref", "score": 13, "reason": REASON_SENTINEL})
    s1.append({"statement_id": "SKref", "score": 14, "reason": REASON_SENTINEL})
    s2.append({"statement_id": "SKref", "score": 15, "reason": REASON_SENTINEL})

    root.mkdir(parents=True, exist_ok=True)
    (root / "key-b3.json").write_text(json.dumps(key))
    _jsonl(root / "ratings-b3-statements-p1.jsonl", s1)
    _jsonl(root / "ratings-b3-statements-p2.jsonl", s2)
    _jsonl(root / "ratings-b3-triples-p1.jsonl", t1)
    _jsonl(root / "ratings-b3-triples-p2.jsonl", t2)
    bars = dict(BARS, inputs={"key-b3.json": _sha(root / "key-b3.json"),
                              "ratings-b3-triples-p1.jsonl": _sha(root / "ratings-b3-triples-p1.jsonl")})
    (root / "certification-bars.json").write_text(json.dumps(bars))

    def per_writer(w):
        return {"candidates": {"included": sum(c[0] == w for c in candidates)},
                "controls": {"included": sum(c[0] == w for c in controls)}}

    cert = {"pooled": {"included": len(candidates), "certified": 4, "certified_both_passes": 2,
                       "certified_pass1_only": 2, "controls_certified": len(controls)},
            "by_writer": {"sonnet55": per_writer("sonnet55"), "glm53": per_writer("glm53")}}
    cert["by_writer"]["sonnet55"]["candidates"].update(certified=3, certified_both_passes=1, certified_pass1_only=2)
    cert["by_writer"]["glm53"]["candidates"].update(certified=1, certified_both_passes=1, certified_pass1_only=0)
    for path, value in (cert_overrides or {}).items():
        d = cert
        *head, last = path.split(".")
        for h in head:
            d = d[h]
        d[last] = value
    (root / "certification-b3.json").write_text(json.dumps(cert))
    (root / "certification-b3.md").write_text("synthetic certification record\n")
    return root


# ---- the formulas --------------------------------------------------------------------------------------------------

def test_lift_is_composition_minus_the_loudest_statement():
    assert pl.lift([50, 60, 55], 80) == 20
    assert pl.lift([70, 20, 30], 60) == -10


def test_minimum_lift_needed_is_one_above_the_bar_less_the_statement_bar():
    # J1: the composition score must be ABOVE the bar, scores are integers: 76 - 60 = 16, not 75 - 60 = 15
    assert pl.min_lift_needed({"composition_bar": 75, "statement_bar": 60}) == 16
    assert pl.min_lift_needed({"composition_bar": 80, "statement_bar": 50}) == 31


def test_average_ranks_give_ties_the_mean_rank():
    v = [3, 1, 3, 2, 3]
    assert pl.average_ranks(v) == list(stats.rankdata(v))


@pytest.mark.parametrize("x,y", [
    ([1, 2, 3, 4, 5, 6], [2, 1, 4, 3, 6, 5]),
    ([80, 78, 75, 60, 76, 70, 40, 90, 70, 50, 85, 62], [58, 48, 60, 70, 60, 52, 25, 55, 60, 30, 61, 45]),
    ([5, 5, 5, 1, 2, 3, 3], [1, 1, 2, 2, 3, 3, 3]),
])
def test_spearman_matches_scipy_with_ties(x, y):
    assert pl.spearman(x, y) == pytest.approx(stats.spearmanr(x, y).statistic, abs=1e-12)


def test_spearman_of_a_constant_is_not_a_number():
    assert math.isnan(pl.spearman([1, 2, 3, 4], [7, 7, 7, 7]))


def test_bootstrap_interval_is_reproducible_and_sits_near_a_strong_correlation():
    x = list(range(30))
    y = [v + (3 if v % 3 == 0 else -2) for v in x]
    a = pl.bootstrap_spearman_ci(x, y, resamples=500, seed=20261102)
    b = pl.bootstrap_spearman_ci(x, y, resamples=500, seed=20261102)
    c = pl.bootstrap_spearman_ci(x, y, resamples=500, seed=1)
    assert a == b and a != c
    lo, hi, degenerate = a
    assert 0.9 < lo <= hi <= 1.0 and degenerate == 0


def test_bootstrap_counts_degenerate_resamples_when_one_side_is_constant_in_a_resample():
    x = [1, 2, 3]
    y = [5, 5, 9]  # a resample that draws only the first two rows has a constant y
    lo, hi, degenerate = pl.bootstrap_spearman_ci(x, y, resamples=400, seed=3)
    assert degenerate > 0 and -1.0 <= lo <= hi <= 1.0


def test_summary_uses_sample_sd_and_linear_quartiles():
    s = pl.summarize([1, 2, 3, 4, 10])
    assert s == {"n": 5, "mean": 4.0, "sd": pytest.approx(math.sqrt(12.5)), "median": 3.0, "q1": 2.0, "q3": 4.0}
    even = pl.summarize([1, 2, 3, 4])  # between-points quartiles: the interpolation is visible here
    assert (even["q1"], even["median"], even["q3"]) == (1.75, 2.5, 3.25)


def test_compare_to_note_reports_the_difference_at_the_printed_precision():
    r = pl.compare_to_note("x", 13.4571, 13.46, 2)
    assert r["matches_printed_precision"] is True and r["difference"] == pytest.approx(13.4571 - 13.46)
    assert pl.compare_to_note("x", 13.47, 13.46, 2)["matches_printed_precision"] is False
    assert pl.compare_to_note("x", 0.6283, 0.628, 3)["matches_printed_precision"] is True


# ---- loading ------------------------------------------------------------------------------------------------------

def test_load_scores_keeps_id_and_score_and_drops_reason(tmp_path):
    p = tmp_path / "r.jsonl"
    _jsonl(p, [{"triple_id": "a", "score": 70, "reason": REASON_SENTINEL}, {"triple_id": "b", "score": 55.0, "reason": "y"}])
    got = pl.load_scores(p, "triple_id")
    assert got == {"a": 70, "b": 55} and all(type(v) is int for v in got.values())
    assert REASON_SENTINEL not in repr(got)


def test_load_scores_refuses_a_repeated_id_and_a_non_integer_score(tmp_path):
    p = tmp_path / "r.jsonl"
    _jsonl(p, [{"triple_id": "a", "score": 70}, {"triple_id": "a", "score": 71}])
    with pytest.raises(ValueError, match="repeated"):
        pl.load_scores(p, "triple_id")
    _jsonl(p, [{"triple_id": "a", "score": 70.5}])
    with pytest.raises(ValueError, match="integer"):
        pl.load_scores(p, "triple_id")


# ---- the record on the synthetic dozen ----------------------------------------------------------------------------

@pytest.fixture()
def record(tmp_path):
    root = make_inputs(tmp_path / "rater")
    return pl.build_record(root, resamples=300, seed=20261102)


def test_counts_candidates_by_writer_and_controls(record):
    c = record["counts"]
    assert c["candidates"] == 12
    assert c["candidates_by_writer"] == {"Sonnet 5.5": 7, "GLM 5.3": 5}
    assert c["controls"] == 3 and c["controls_by_writer"] == {"Sonnet 5.5": 2, "GLM 5.3": 1}
    assert c["reproduces_j2"] is True


def test_certified_counts_are_recomputed_from_the_bars(record):
    c = record["counts"]
    assert (c["certified_pass1"], c["certified_pass2"], c["certified_both_passes"], c["certified_pass1_only"]) == (4, 3, 2, 2)


def test_minimum_lift_is_stated_with_the_bars_by_name(record):
    assert record["min_lift_needed"]["value"] == 16
    assert record["min_lift_needed"]["formula"] == "(composition_bar + 1) - statement_bar"
    b = record["bars"]
    assert (b["composition_bar"], b["statement_bar"], b["spread_bar"]) == (75, 60, 10)
    assert "rule" not in b


def test_pass1_lift_rows_match_a_hand_computation(record):
    row = record["lift"]["pass1"]
    assert row["overall"]["n"] == 12 and row["overall"]["mean"] == pytest.approx(212 / 12)
    assert row["by_writer"]["Sonnet 5.5"]["mean"] == pytest.approx(106 / 7)
    assert row["by_writer"]["GLM 5.3"]["mean"] == pytest.approx(106 / 5)
    # lifts 22 30 15 -10 16 18 15 | 35 10 20 24 17: those >= 16 are 22 30 16 18 | 35 20 24 17
    assert row["overall"]["reaching_min_lift"] == 8
    assert row["by_writer"]["Sonnet 5.5"]["reaching_min_lift"] == 4 and row["by_writer"]["GLM 5.3"]["reaching_min_lift"] == 4
    assert "necessary, not sufficient" in record["min_lift_needed"]["reading"]


def test_pass2_and_mean_of_passes_are_secondary_rows(record):
    assert record["lift"]["pass2"]["overall"]["mean"] == pytest.approx(213 / 12)
    assert record["lift"]["pass2"]["overall"]["reaching_min_lift"] == 7
    both = record["lift"]["mean_of_passes"]["overall"]
    assert both["mean"] == pytest.approx((212 + 213) / 24)
    assert "reaching_min_lift" not in both


def test_spearman_rows_agree_with_scipy_and_carry_an_interval(record):
    c1 = [c[2] for c in CANDIDATES]
    top = [max(c[1]) for c in CANDIDATES]
    mean = [sum(c[1]) / 3 for c in CANDIDATES]
    spread = [max(c[1]) - min(c[1]) for c in CANDIDATES]
    row = record["spearman"]["pass1"]
    assert row["composition_vs_max_statement"]["rho"] == pytest.approx(stats.spearmanr(c1, top).statistic, abs=1e-12)
    assert row["composition_vs_mean_statement"]["rho"] == pytest.approx(stats.spearmanr(c1, mean).statistic, abs=1e-12)
    assert row["composition_vs_spread"]["rho"] == pytest.approx(stats.spearmanr(c1, spread).statistic, abs=1e-12)
    r = row["composition_vs_max_statement"]
    assert r["n"] == 12 and r["resamples"] == 300 and r["seed"] == 20261102
    assert -1.0 <= r["ci95"][0] <= r["ci95"][1] <= 1.0 and "degenerate_resamples" in r
    p2 = record["spearman"]["pass2"]["composition_vs_max_statement"]["rho"]
    assert p2 == pytest.approx(stats.spearmanr([c[4] for c in CANDIDATES], [max(c[3]) for c in CANDIDATES]).statistic, abs=1e-12)


def test_the_six_review_note_values_are_compared_and_disagreement_is_reported(record):
    names = [c["name"] for c in record["check_values"]]
    assert names == ["lift_pass1_overall_mean", "lift_pass1_sonnet55_mean", "lift_pass1_glm53_mean",
                     "spearman_pass1_composition_vs_max_statement", "spearman_pass1_composition_vs_mean_statement",
                     "spearman_pass1_composition_vs_spread"]
    assert [c["review_note"] for c in record["check_values"]] == [13.46, 16.17, 10.29, 0.628, 0.456, 0.376]
    assert record["agreement"]["all_match"] is False  # the synthetic dozen cannot reproduce Part J's figures
    assert record["inputs"]["key_sha256_is_the_review_runs"] is False


# ---- refusals -----------------------------------------------------------------------------------------------------

def test_a_candidate_with_a_missing_statement_score_is_refused(tmp_path):
    root = make_inputs(tmp_path / "rater", drop_statement=("candidates", 3, 1))
    with pytest.raises(SystemExit, match="statement"):
        pl.build_record(root, resamples=50, seed=1)


def test_counts_that_do_not_reproduce_j2_are_refused(tmp_path):
    root = make_inputs(tmp_path / "rater", cert_overrides={"pooled.included": 13})
    with pytest.raises(SystemExit, match="J2"):
        pl.build_record(root, resamples=50, seed=1)
    root = make_inputs(tmp_path / "rater2", cert_overrides={"by_writer.glm53.candidates.included": 4})
    with pytest.raises(SystemExit, match="J2"):
        pl.build_record(root, resamples=50, seed=1)
    root = make_inputs(tmp_path / "rater3", cert_overrides={"pooled.certified_pass1_only": 1})
    with pytest.raises(SystemExit, match="J2"):
        pl.build_record(root, resamples=50, seed=1)


def test_inputs_that_changed_since_the_bars_were_cut_are_refused(tmp_path):
    root = make_inputs(tmp_path / "rater")
    with (root / "ratings-b3-triples-p1.jsonl").open("a") as f:
        f.write(json.dumps({"triple_id": "extra", "score": 1}) + "\n")
    with pytest.raises(SystemExit, match="certification-bars"):
        pl.build_record(root, resamples=50, seed=1)


# ---- nothing but numbers and fixed labels leaves the session -------------------------------------------------------

@pytest.mark.parametrize("bad", [
    {"reason": "free text"},
    {"nested": [{"statement": "x"}]},
    {"rows": {"text": "x"}},
    {"ids": ["a"]},
    {"x": "y" * 400},
])
def test_the_writer_refuses_a_record_carrying_a_text_field(bad, tmp_path):
    with pytest.raises(ValueError):
        pl.write_record(bad, tmp_path)
    assert not list(tmp_path.glob("partj-lift-v0.*"))


def test_no_reason_and_no_id_reaches_a_file_or_stdout(tmp_path, capsys):
    root = make_inputs(tmp_path / "rater")
    out = tmp_path / "out"
    pl.main(["--rater-dir", str(root), "--out-dir", str(out), "--resamples", "100"])
    printed = capsys.readouterr().out
    written = (out / "partj-lift-v0.json").read_text() + (out / "partj-lift-v0.md").read_text()
    for bad in (REASON_SENTINEL, ID_SENTINEL, "TK0", "SK0"):
        assert bad not in printed and bad not in written
    assert json.loads((out / "partj-lift-v0.json").read_text())["record"] == "partj-lift-v0"
    assert "Sonnet 5.5" in written and "GLM 5.3" in written and "candidates-" not in written
