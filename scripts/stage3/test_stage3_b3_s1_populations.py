"""Tests for stage3_b3_s1_populations (brief 28): synthetic rules, then the real files by counts and hashes only.

    cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_b3_s1_populations.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_b3_s1_populations as sp  # noqa: E402


def _rec(regime="candidate", membership="quiet", resolve=True, kimi=(0.0, 0.0), sol=(0.0, 0.0),
         kw=(0.0, 0.0), sw=(0.0, 0.0), comp=50.0, doc="d1", writer="sonnet55"):
    return {"regime": regime, "writer": writer, "document": doc, "anchors_resolve": resolve, "membership": membership,
            "composition": comp,
            "readers": {"kimi": {"D_part": list(kimi), "D_whole": list(kw)}, "sol": {"D_part": list(sol), "D_whole": list(sw)}}}


def test_ids_sha256_is_sorted_and_newline_joined():
    assert sp.ids_sha256(["b", "a"]) == sp.ids_sha256(["a", "b"])
    import hashlib
    assert sp.ids_sha256(["a", "b"]) == hashlib.sha256(b"a\nb").hexdigest()


def test_strict_needs_both_readers_zero_on_both_samples():
    assert sp.is_strict(_rec())
    assert not sp.is_strict(_rec(sol=(0.0, 0.5)))      # in the stratum under Sol's mean rule, not strict
    assert not sp.is_strict(_rec(membership="not_quiet"))


def test_preview_arms_and_mixed():
    assert sp.whole_credited_both(_rec(kw=(0.0, 1.0), sw=(0.5, 0.0)))
    assert not sp.whole_credited_both(_rec(kw=(0.0, 1.0)))            # mixed: one reader only
    assert sp.whole_never_credited(_rec())
    assert not sp.whole_never_credited(_rec(sw=(0.0, 0.5)))


def test_gross_populations_and_certified_bar():
    items = {"a": _rec(comp=75.0), "b": _rec(resolve=False, comp=74.5), "c": _rec(membership="not_quiet", comp=80.0),
             "k": _rec(regime="control", membership="quiet", comp=5.0), "s": _rec(regime="sham", membership="quiet")}
    p = sp.gross_populations(items)
    assert p["full"] == ["a", "b", "c"] and p["stratum"] == ["a", "b"] and p["subset"] == ["a"]
    assert p["unresolved_stratum"] == ["b"] and p["certified"] == ["a", "c"]    # at or above 75, quiet or not
    assert p["controls"] == ["k"] and p["sham"] == ["s"]


def test_lone_line_exclusion_of_the_item_authors():
    item = {"item_id": "i", "regime": "candidate",
            "draws": {"valid_draws": [["d1", "a"], ["d2", "b"]]},
            "lone_lines": [{"valid_draws": [["d1", "a"], ["d1", "c"], ["d1", "e"]]},     # c, e left; one day only
                           {"valid_draws": [["d1", "a"], ["d2", "b"], ["d1", "c"]]}]}    # c alone left
    r = sp.lone_line_feasibility({"items": [item]}, set())
    assert r["net_candidate_lines"] == 2 and r["two_valid_by_different_authors"] == 2
    assert r["every_item_pair_leaves_two_by_different_authors"] == 1
    assert r["beside_every_item_pair_leaves_two_on_different_days_by_different_authors"] == 0


def test_pooled_strata():
    assert sp.pooled_strata(["x"] * 6 + ["y"] * 4 + ["z"] * 3 + ["w"]) == [6, 4, 4]
    assert sp.pooled_strata(["x"] * 6 + ["y"] * 4 + ["z"] * 3 + ["w"] * 2 + ["v", "u"]) == [7, 6, 4]


REAL = sp.ROOT / sp.STRATUM


@pytest.mark.skipif(not REAL.exists(), reason="brief 25's stratum file is not on disk")
def test_real_files_reproduce_the_recorded_counts():
    res = sp.build()
    P = res["populations"]
    gross = {k: P[k]["gross"]["n"] for k in P}
    net = {k: P[k]["net_pair"]["n"] for k in P}
    lit = {k: P[k]["net_literal"]["n"] for k in P}
    assert P["stratum"]["gross"]["ids_sha256"].startswith("410e7461")                 # brief 25
    assert (gross["full"], gross["stratum"], gross["subset"], gross["strict"]) == (78, 28, 19, 21)
    assert (net["full"], net["stratum"], net["subset"], net["strict"], net["controls"], net["sham"]) == (73, 26, 17, 20, 21, 22)
    assert (lit["full"], lit["stratum"], lit["subset"], lit["strict"], lit["controls"], lit["sham"]) == (77, 27, 18, 21, 22, 23)
    assert net["subset_and_strict"] == 11                                                 # A6.18 (h)
    assert (gross["certified"], net["certified"]) == (11, 10)                             # A6.2 wording note
    assert (gross["preview_credited"], gross["preview_illegible"]) == (11, 7)             # A6.17.5
    assert gross["unresolved_stratum"] == 9 and net["unresolved_stratum"] == 9            # A6.17.11
    assert res["drops"]["pair"]["n"] == 8 and res["drops"]["literal"]["n"] == 2
    L = res["lone_lines"]
    assert L["net_candidate_lines"] == 219 and L["two_valid_by_different_authors"] == 219
    assert L["every_item_pair_leaves_two_by_different_authors"] == 219
    assert L["beside_every_item_pair_leaves_two_on_different_days_by_different_authors"] == 177
    # Part 3's Step 0 descriptions (power-simulation-v3c.json step0.populations)
    for name, mean, sd, iqr, writers, docs, pooled in (
            ("full", 56.2466, 15.8920, (47.5, 66.5), {"glm53": 35, "sonnet55": 38}, [14, 14, 13, 12, 12, 8], [14, 14, 13, 12, 12, 8]),
            ("stratum", 50.6154, 16.1259, (44.875, 58.375), {"glm53": 15, "sonnet55": 11}, [6, 6, 6, 4, 3, 1], [6, 6, 6, 4, 4]),
            ("subset", 49.5588, 18.3770, (47.5, 56.5), {"glm53": 6, "sonnet55": 11}, [6, 4, 3, 2, 1, 1], [7, 6, 4]),
            ("strict", 53.1, 15.2364, (46.625, 62.0), {"glm53": 12, "sonnet55": 8}, [6, 5, 4, 3, 2], [6, 5, 5, 4])):
        d = P[name]["net_pair"]
        assert d["composition"]["mean"] == pytest.approx(mean, abs=1e-3)
        assert d["composition"]["sd"] == pytest.approx(sd, abs=1e-3)
        assert tuple(d["composition"]["iqr"]) == pytest.approx(iqr)
        assert d["by_writer"] == writers and d["document_counts"] == docs and d["strata_pooled"] == pooled
