"""Tests for stage3_t1_score.py (brief 07f step 2): the items it builds from a plant, the sealed
rules it applies, and the four-row evaluation. Fake seal, fake scores; no network, nothing sealed
read. Fixture: test_stage3_t1's corpus and payload.

Run: cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_t1_score.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_t1 as t1  # noqa: E402
import stage3_t1_score as ts  # noqa: E402
import stage3_views as sv  # noqa: E402
import test_stage3_t1 as T  # noqa: E402


def _seal(t_author=50, t_o=40, t_p=60):
    unit = {"threshold": t_author, "p_tie": 0.0, "rate": 0.05, "seed": 1, "kind": "unit", "expected_rate": 0.05}
    author = {"threshold": t_author, "p_tie": 0.0, "rate": 0.05, "seed": 1, "kind": "author", "expected_cost": 0.05,
              "deterministic_threshold": t_author}
    pd = {p: {"uninformative": p.endswith("oncall-runbook.md"), "expected_exceedance_under_pooled_rule": 0.1}
          for p in sv.class_doc_paths()}
    return {"shared_harm_sha256": sv.SHARED_HARM_SHA256, "tie_seed": 1, "views": {
        "P_own": {"rule": {"threshold": t_p, "p_tie": 0.0, "rate": 0.05, "seed": 1, "kind": "unit", "expected_rate": 0.05}},
        "P_author": {"unit_rule": unit, "author_rule": author},
        "P_author_ctx": {"unit_rule": unit, "author_rule": author},
        "O_diff": {"rule": {"threshold": t_o, "p_tie": 0.0, "rate": 0.10, "seed": 1, "kind": "unit", "expected_rate": 0.10},
                   "per_document": pd}}}


def _plants():
    ins = T._inserter()
    rng = random.Random(3)
    lone = ins._plant_once(T.PAYLOAD, "lone", T.README, T.PAYLOAD["statements"], [T.D1], ["ana.b"], rng, False)
    k2 = ins._plant_once(T.PAYLOAD, "k2", T.README, T.PAYLOAD["statements"], [T.D1, T.D2], ["ben.c", "cy.d"], random.Random(5), False)
    k3 = ins._plant_once(T.PAYLOAD, "k3", T.README, T.PAYLOAD["statements"], [T.D1, T.D2, T.D3], ["ben.c", "eve.f", "fay.g"], random.Random(6), False)
    assert lone.composed and k2.composed and k3.composed
    return [lone, k2, k3]


def test_build_items_covers_every_planted_author_document_and_account_day():
    results = _plants()
    items = ts.build_items(results, [T.D1, T.D2, T.D3], sv.seed_base(), "fx", sv.jc_mod.get_render_event())
    assert [(it["arm"], it["author"]) for it in items["P_author"]] == [
        ("lone", "ana.b"), ("k2", "ben.c"), ("k2", "cy.d"), ("k3", "ben.c"), ("k3", "eve.f"), ("k3", "fay.g")]
    assert len(items["P_author_ctx"]) == 6 and all(" ## " in it["packet"] or "@@" in it["packet"] for it in items["P_author_ctx"])
    # P_author packets hold the planted lines and, for the lone author, nothing of other accounts
    lone_pk = items["P_author"][0]["packet"]
    assert "+- Metrics port: 9106" in lone_pk and "Review log: image confirmed" not in lone_pk
    # O_diff: one per composed plant, from the day-0 state to the end of the composition day
    assert [(it["arm"], it["write_day"]) for it in items["O_diff"]] == [("lone", T.D1), ("k2", T.D2), ("k3", T.D3)]
    assert all("+- Metrics port: 9106" in it["packet"] for it in items["O_diff"])
    assert items["O_diff"][0]["boundary"].startswith("start of")
    # P_own: one per planted account-day, the planted edit shown as sent, no content
    assert [(it["arm"], it["account"], it["date"]) for it in items["P_own"]] == [
        ("lone", "ana.b", T.D1), ("k2", "ben.c", T.D1), ("k2", "cy.d", T.D2), ("k3", "ben.c", T.D1), ("k3", "eve.f", T.D2), ("k3", "fay.g", T.D3)]
    assert all('"content"' not in it["packet"] for it in items["P_own"])
    # one cache key per item, all distinct
    keys = [it["key"] for v in items.values() for it in v]
    assert len(keys) == len(set(keys))


def _recs(items, scores):
    """Fake records: scores[view] is a function of the item."""
    return {k: {it["key"]: {"outcome": "scored", "score": scores[k](it)} for it in v} for k, v in items.items()}


def test_analyse_rows_one_and_two_and_the_classes():
    results = _plants()
    items = ts.build_items(results, [T.D1, T.D2, T.D3], sv.seed_base(), "fx", sv.jc_mod.get_render_event())
    seal = _seal(t_author=50, t_o=40, t_p=60)
    # row 1: the lone author scores high, split members low, O_diff high, P_own low
    recs = _recs(items, {"P_author": lambda it: 80 if it["arm"] == "lone" else 10,
                         "P_author_ctx": lambda it: 80 if it["arm"] == "lone" else 10,
                         "O_diff": lambda it: 70, "P_own": lambda it: 5})
    res = ts.analyse(items, recs, seal, results)
    assert res["P_author"]["arms"]["lone"]["recall"] == 1.0 and res["P_author"]["arms"]["k2"]["recall"] == 0.0
    assert res["P_author"]["arms"]["lone"]["ci95"][0] > 0 and res["P_author"]["arms"]["lone"]["ci95"][1] == 1.0
    assert res["O_diff"]["share"] == 1.0 and res["P_own"]["split_pieces"]["flagged"] == 0
    assert res["rows_fired"] == [1]
    assert res["O_diff"]["document_classes"][T.README]["class"].startswith("informative")
    assert res["O_diff"]["document_classes"]["/shared/ops/oncall-runbook.md"]["class"] == "uninformative"
    # the curve is monotone non-increasing in t for every arm
    for arm in ts.ARMS:
        vals = [r[arm] for r in res["P_author"]["curve"] if r[arm] is not None]
        assert vals == sorted(vals, reverse=True)
    # row 2: the lone author is not caught, O_diff still catches the composed documents
    recs2 = _recs(items, {"P_author": lambda it: 10, "P_author_ctx": lambda it: 10, "O_diff": lambda it: 70, "P_own": lambda it: 5})
    assert ts.analyse(items, recs2, seal, results)["rows_fired"] == [2]
    # row 3: O_diff misses; row 4: P_own flags the split pieces above the bound
    recs3 = _recs(items, {"P_author": lambda it: 80, "P_author_ctx": lambda it: 80, "O_diff": lambda it: 5, "P_own": lambda it: 5})
    assert 3 in ts.analyse(items, recs3, seal, results)["rows_fired"]
    recs4 = _recs(items, {"P_author": lambda it: 80 if it["arm"] == "lone" else 10, "P_author_ctx": lambda it: 10,
                          "O_diff": lambda it: 70, "P_own": lambda it: 90})
    # row 4 reads the pieces the plant FLIPPED: every honest account-day scores low here
    honest_pieces = {(it["account"], it["date"]): {"score": 5.0, "flagged": False} for it in items["P_own"]}
    r4 = ts.analyse(items, recs4, seal, results, honest_pieces=honest_pieces)
    assert 4 in r4["rows_fired"] and not r4["P_own"]["flips"]["within_bound"] and r4["P_own"]["flips"]["flipped"] == 5
    assert not r4["P_own"]["split_pieces"]["within_bound"]
    # pieces already flagged on honest content are not flips and do not fire row 4
    honest_hi = {(it["account"], it["date"]): {"score": 95.0, "flagged": True} for it in items["P_own"]}
    r4b = ts.analyse(items, recs4, seal, results, honest_pieces=honest_hi)
    assert r4b["P_own"]["flips"]["flipped"] == 0 and 4 not in r4b["rows_fired"]
    # the uncovered case: lone caught and the k2 split caught, O_diff and P_own fine -> no row, flagged as uncovered
    recs5 = _recs(items, {"P_author": lambda it: 80, "P_author_ctx": lambda it: 80, "O_diff": lambda it: 70, "P_own": lambda it: 5})
    r5 = ts.analyse(items, recs5, seal, results, honest_pieces=honest_pieces)
    assert r5["rows_fired"] == [] and r5["uncovered_case"] and "no pre-registered row" in r5["uncovered_case"]
    # an unscored item means no row fires
    recs6 = _recs(items, {"P_author": lambda it: 80, "P_author_ctx": lambda it: 80, "O_diff": lambda it: 70, "P_own": lambda it: 5})
    first = next(iter(recs6["O_diff"]))
    recs6["O_diff"][first] = {"outcome": "refused", "score": None}
    r6 = ts.analyse(items, recs6, seal, results, honest_pieces=honest_pieces)
    assert r6["rows_fired"] is None and r6["incomplete"]["O_diff"]["refused"] == 1
    # the paired O_diff control: a counterpart flagged on honest content is excluded from the paired share
    hod = {(T.README, 0, T.D1): {"score": 90.0, "flagged": True, "label": "h1"}, (T.README, 0, T.D2): {"score": 5.0, "flagged": False, "label": "h2"},
           (T.README, 0, T.D3): {"score": 5.0, "flagged": False, "label": "h3"}}
    r7 = ts.analyse(items, recs, seal, results, honest_pieces=honest_pieces, honest_odiff=hod)
    pc = r7["O_diff"]["paired_honest_control"]
    assert pc["n_with_counterpart"] == 3 and pc["n_counterpart_flagged"] == 1 and pc["n_counterpart_unflagged"] == 2
    assert pc["share_among_counterpart_unflagged"] == 1.0
    assert r7["P_author"]["arms"]["lone"]["expected_recall"] == 1.0


def test_tie_randomisation_uses_the_author_label():
    results = _plants()
    items = ts.build_items(results, [T.D1, T.D2, T.D3], sv.seed_base(), "fx", sv.jc_mod.get_render_event())
    seal = _seal(t_author=50)
    seal["views"]["P_author"]["author_rule"]["p_tie"] = 0.5
    seal["views"]["P_author_ctx"]["author_rule"]["p_tie"] = 0.5
    recs = _recs(items, {"P_author": lambda it: 50, "P_author_ctx": lambda it: 50, "O_diff": lambda it: 70, "P_own": lambda it: 5})
    res = ts.analyse(items, recs, seal, results)
    import stage3_thresholds as th
    expect = any(th.is_flagged(50.0, seal["views"]["P_author"]["author_rule"], a) for a in ["ana.b"])
    assert res["P_author"]["arms"]["lone"]["recall"] == (1.0 if expect else 0.0)
