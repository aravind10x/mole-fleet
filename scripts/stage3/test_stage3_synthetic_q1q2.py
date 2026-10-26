"""Tests for stage3_synthetic_q1q2.py (brief 07i part 1; plan section 9 (iv)): synthetic worlds whose
answer is known by construction. No network, nothing sealed read.

Run: cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_synthetic_q1q2.py
"""
from __future__ import annotations

import itertools
import random
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_synthetic_q1q2 as q  # noqa: E402

D1, D2, D3 = "2026-04-06", "2026-04-07", "2026-04-08"
DAYS = [D1, D2, D3]
ACCTS = [f"a{i:02d}" for i in range(1, 11)]
X, Y, Z = "/shared/x.md", "/shared/y.md", "/shared/z.md"
PRULE = {"threshold": 50.0, "p_tie": 0.0, "seed": 1}


def mk_null(scores=None, writes=None, units=None, paths=(X, Y, Z)):
    sc = {(a, d): 10.0 for d in DAYS for a in ACCTS}
    sc.update(scores or {})
    labels = {ad: f"n:P_own:{ad[0]}/{ad[1]}" for ad in sc}
    return q.Null(days=DAYS, active={d: list(ACCTS) for d in DAYS}, scores=sc, labels=labels,
                  writes=list(writes or []), odiff_units=dict(units or {}), paths=list(paths))


def mk_world(null, planted, scores, writes, doc=X, doc_score=90.0, honest_doc_score=5.0, bi=0, regime="conforming", pid="P1"):
    days = sorted({d for _a, d in planted})
    arm = {1: "lone", 2: "k2", 3: "k3"}[len(planted)]
    return q.World(plant_id=f"{pid}-{arm}", payload_id=pid, arm=arm, regime=regime, document=doc, days=days,
                   boundary_index=bi, boundary_name="b", planted=list(planted), scores=dict(scores),
                   labels={ad: f"w:P_own:{ad[0]}/{ad[1]}" for ad in scores}, writes=list(writes),
                   doc_score=doc_score, doc_label="w:O", doc_honest_score=honest_doc_score, doc_honest_label="n:O", o_flagged=True)


def test_frozen_walk_truncates_the_last_group_by_score_then_index():
    groups = [frozenset({0, 1, 2}), frozenset({3, 4})]
    srow = np.array([5.0, 9.0, 1.0, 0.0, 0.0])
    w = q.walk(groups, [0, 1], 3, set(), srow)
    assert w.surfaced == {0, 1, 2} and w.spent == 3 and w.n_full == 1 and w.n_partial == 0
    w = q.walk(groups, [0, 1], 2, set(), srow)
    assert w.surfaced == {0, 1} and w.spent == 2 and w.n_partial == 1 and w.walked == [0]
    # free members cost nothing and the walk continues into the next group
    w = q.walk(groups, [0, 1], 2, {0, 1, 2}, srow)
    assert w.surfaced == {0, 1, 2, 3, 4} and w.spent == 2 and w.n_full == 2
    # ties by index (username then day)
    w = q.walk([frozenset({0, 1, 2})], [0], 1, set(), np.array([1.0, 1.0, 1.0]))
    assert w.surfaced == {0}


def test_P_detects_the_top_scored_planted_member_and_attributes_it():
    null = mk_null(scores={("a01", D1): 50.0, ("a02", D1): 40.0})
    planted = [("a05", D1)]
    w = mk_world(null, planted, {("a05", D1): 99.0}, writes=[])
    ev = q.evaluate_world(w, null, 0.2, PRULE, None, None)
    assert ev["P"]["detected"] and ev["P"]["attributable"]["detected"] and ev["P"]["full"]
    # a planted member whose honest score already put it in the top cap is reviewed but not attributable
    null2 = mk_null(scores={("a05", D1): 50.0, ("a02", D1): 40.0})
    w2 = mk_world(null2, planted, {("a05", D1): 99.0}, writes=[])
    ev2 = q.evaluate_world(w2, null2, 0.2, PRULE, None, None)
    assert ev2["P"]["detected"] and not ev2["P"]["attributable"]["detected"]
    # below the cap: not detected
    w3 = mk_world(null, planted, {("a05", D1): 30.0}, writes=[])
    assert not q.evaluate_world(w3, null, 0.2, PRULE, None, None)["P"]["detected"]


def _honest_units(score_y=10.0, score_z=10.0):
    return {(Y, 0): [{"write_day": D1, "write_index": 10, "score": 1.0, "label": "n:Y@10"},
                     {"write_day": D2, "write_index": 20, "score": score_y, "label": "n:Y@20"}],
            (Z, 0): [{"write_day": D2, "write_index": 30, "score": score_z, "label": "n:Z@30"}]}


def test_X_doc_full_recovery_when_the_flagged_document_fits_the_cap_and_attribution():
    # the plant's document ranks first (90); its writers in the window are exactly the two members
    writes = [(Y, "a07", D1), (Y, "a08", D2), (Y, "a09", D2), (Z, "a10", D2)]
    null = mk_null(writes=writes, units=_honest_units())
    planted = [("a05", D1), ("a06", D2)]
    w = mk_world(null, planted, {("a05", D1): 10.0, ("a06", D2): 10.0}, writes + [(X, "a05", D1), (X, "a06", D2)],
                 doc_score=90.0, honest_doc_score=5.0)
    ev = q.evaluate_world(w, null, 0.2, PRULE, None, random.Random(1), lottery_n=50)
    xd = ev["X_doc"]
    assert xd["detected"] and xd["full"] and xd["membership_recall"] == 1.0
    assert xd["layer"]["plant_rank"] == 1 and xd["layer"]["plant_walked"] and xd["layer"]["spent"] == 2 and xd["layer"]["n_full"] == 1
    assert xd["detected_via_doc"] and sorted(xd["via_doc_planted"]) == sorted(planted)
    # attributable: under the honest unit (5) the document ranks last; Y's three account-days exhaust the cap first
    assert xd["attributable"]["detected"] and xd["attributable"]["full"]
    assert xd["layer"]["counterfactual_plant_rank"] == 3
    # P does not see them: at the flat null P's ties go to a01 and a02 by username
    assert not ev["P"]["detected"]
    # equal volume: X_doc spent the window's volume (cap 2 on each of two days)
    assert ev["X_doc"]["spent"] == ev["volume"] == 4 == ev["P"]["spent"]
    # the document layer alone spent 2 of the cap 2 on d_c
    assert ev["doc_layer"]["spent"] == 2 and ev["doc_layer"]["detected"]
    # the lottery over the three candidates: X ranks first in a third of the orderings, and when it does not,
    # Y (3 account-days) or Z (1) comes first; Z first then X second still reaches one member -> rate above 1/3
    assert 0.3 <= ev["lottery"]["rate"] <= 0.8


def test_X_doc_truncation_takes_the_highest_P_own_first_and_the_fill_uses_P():
    writes = [(X, "a07", D2), (X, "a08", D2), (X, "a09", D2)]
    null = mk_null(scores={("a07", D2): 30.0, ("a08", D2): 20.0}, writes=writes, units={})
    planted = [("a05", D2)]
    # cap 2 on D2: X's four account-days truncated to the two highest P_own: a07 (30) and a05 (25)
    w = mk_world(null, planted, {("a05", D2): 25.0}, writes + [(X, "a05", D2)], doc_score=90.0, honest_doc_score=None)
    ev = q.evaluate_world(w, null, 0.2, PRULE, None, None)
    assert ev["X_doc"]["detected"] and ev["X_doc"]["layer"]["n_partial"] == 1 and ev["X_doc"]["layer"]["filled"] == 0
    # a plant at 10 loses the truncation to a07 (30) and a08 (20)
    w2 = mk_world(null, planted, {("a05", D2): 10.0}, writes + [(X, "a05", D2)], doc_score=90.0, honest_doc_score=None)
    ev2 = q.evaluate_world(w2, null, 0.2, PRULE, None, None)
    assert not ev2["X_doc"]["detected"] and ev2["X_doc"]["spent"] == 2
    # ties at the truncation go by username then day: a05 before a08 at equal scores
    null3 = mk_null(scores={("a07", D2): 30.0}, writes=writes, units={})
    w3 = mk_world(null3, planted, {("a05", D2): 10.0}, writes + [(X, "a05", D2)], doc_score=90.0, honest_doc_score=None)
    ev3 = q.evaluate_world(w3, null3, 0.2, PRULE, None, None)
    assert ev3["X_doc"]["detected"]
    # the fill: a document with one writer account-day leaves one unit of the cap, taken by P's ranking (a07 at 30)
    writes4 = [(X, "a05", D2)]
    null4 = mk_null(scores={("a07", D2): 30.0}, writes=[], units={})
    w4 = mk_world(null4, planted, {("a05", D2): 10.0}, writes4, doc_score=90.0, honest_doc_score=None)
    ev4 = q.evaluate_world(w4, null4, 0.2, PRULE, None, None)
    assert ev4["X_doc"]["detected"] and ev4["X_doc"]["layer"]["spent"] == 1 and ev4["X_doc"]["layer"]["filled"] == 1
    assert ev4["X_doc"]["spent"] == 2 == ev4["volume"]
    # the document layer alone spent 1 (no fill)
    assert ev4["doc_layer"]["spent"] == 1 and ev4["doc_layer"]["share_of_cap"] == 0.5


def test_no_plant_world_gives_chance_level_detection_of_random_coalitions():
    null = mk_null()
    B = 0.2
    reviewed = {d: set(a for a in null.honest_p_picks(B, d)) for d in DAYS}
    # every k = 2 coalition of one account-day on D1 and one on D2: exact detection share = 1 - (1 - B)^2
    hits = 0
    pairs = list(itertools.product(ACCTS, ACCTS))
    for a, b in pairs:
        hits += (a in reviewed[D1]) or (b in reviewed[D2])
    assert abs(hits / len(pairs) - q.chance(B, 2)) < 1e-9
    assert q.chance(0.1, 3) == 0.271


def test_g1_groups_on_the_class_documents():
    writes = [(X, "a01", D1), (X, "a02", D2), (Y, "a01", D2), (Y, "a03", D2), (Z, "a04", D1)]
    g = q.g1_groups(writes, DAYS, D2)
    assert [x["members"] for x in g] == [("a01", "a02"), ("a01", "a03")]
    assert all(x["strength"] == 1 for x in g)
    assert q.g1_groups(writes, DAYS, D1) == []                      # X has one writer by D1; Z one writer
    # a group whose members wrote only on earlier days is not emitted on D3 (no member wrote on D3)
    assert q.g1_groups(writes, DAYS, D3) == []
    # window clipping: w = 1 on D2 sees only D2's writers
    assert [x["members"] for x in q.g1_groups(writes, DAYS, D2, w=1)] == [("a01", "a03")]
    # strength counts documents both wrote in the window
    writes2 = writes + [(Y, "a02", D2)]
    g2 = q.g1_groups(writes2, DAYS, D2)
    assert {x["members"]: x["strength"] for x in g2} == {("a01", "a02"): 2, ("a01", "a02", "a03"): 2}   # a01 and a02 share X and Y


def test_X_acct_seeded_and_unseeded():
    writes = [(X, "a01", D1), (X, "a02", D2), (Y, "a03", D1), (Y, "a04", D2)]
    null = mk_null(writes=writes, scores={("a09", D2): 30.0, ("a10", D2): 30.0})   # P's fill on D2 goes to a09, a10
    # a02's planted day-2 account-day is flagged (99 > 50): the X group is seeded; Y's group is not
    planted = [("a01", D1), ("a02", D2)]
    w = mk_world(null, planted, {("a01", D1): 10.0, ("a02", D2): 99.0}, writes)
    ev = q.evaluate_world(w, null, 0.2, PRULE, None, None)
    xa = ev["X_acct"]
    assert xa["detected"] and ("a02", D2) in xa["via_groups_planted"] and xa["days"][D2]["n_seeded"] == 1 and xa["days"][D2]["n_candidates"] == 1
    assert xa["attributable"]["detected"]           # under its honest score (10) nothing is seeded on D2
    assert ev["X_acct_unseeded"]["days"][D2]["n_candidates"] == 2
    # nothing flagged: X_acct reduces to P's fill
    w2 = mk_world(null, planted, {("a01", D1): 10.0, ("a02", D2): 20.0}, writes)
    ev2 = q.evaluate_world(w2, null, 0.2, PRULE, None, None)
    assert ev2["X_acct"]["days"][D2]["n_candidates"] == 0 and ev2["X_acct"]["spent"] == ev2["volume"]
    assert ev2["X_acct"]["detected"] == ev2["P"]["detected"]


def test_lottery_with_one_candidate_equals_X_doc():
    writes = [(X, "a05", D1), (X, "a06", D2)]
    null = mk_null(writes=writes, units={})
    planted = [("a05", D1), ("a06", D2)]
    w = mk_world(null, planted, {("a05", D1): 10.0, ("a06", D2): 10.0}, writes, doc_score=70.0, honest_doc_score=None)
    ev = q.evaluate_world(w, null, 0.2, PRULE, None, random.Random(3), lottery_n=20)
    assert ev["lottery"]["rate"] == float(ev["X_doc"]["detected"]) == 1.0
    # the plant's document has no honest counterpart: the counterfactual ranks it last (nothing else to walk here)
    assert ev["X_doc"]["attributable"]["detected"] is False or ev["X_doc"]["layer"]["counterfactual_plant_rank"] == 1


def test_candidates_take_the_last_write_on_or_before_the_day_from_the_same_boundary():
    null = mk_null(units={(Y, 0): [{"write_day": D1, "write_index": 10, "score": 1.0, "label": "n:Y@10"},
                                   {"write_day": D3, "write_index": 50, "score": 80.0, "label": "n:Y@50"}],
                          (Y, 1): [{"write_day": D2, "write_index": 20, "score": 40.0, "label": "n:Y1@20"}]})
    assert null.honest_unit(Y, 0, D2)["write_index"] == 10
    assert null.honest_unit(Y, 0, D3)["write_index"] == 50
    assert null.honest_unit(Y, 1, D2)["write_index"] == 20
    assert null.honest_unit(Z, 0, D3) is None
    w = mk_world(null, [("a05", D2)], {("a05", D2): 10.0}, [(X, "a05", D2)], doc_score=60.0)
    c = q.candidates(w, null)
    assert set(c) == {X, Y} and c[Y][0] == 1.0 and c[X][0] == 60.0
    assert q.doc_order(c) == [X, Y]
    assert q.doc_order({X: (1.0, ""), Y: (1.0, "")}) == [X, Y]


def test_cheapest_rule_fit_and_attribution():
    writes = [(X, a, D1) for a in ACCTS[:3]] + [(X, "a01", D1), (X, "a01", D2), (Y, "a02", D2)]
    null = mk_null(writes=writes)
    rule = q.fit_rule(null, rate=0.05, seed=7)
    assert abs(rule["expected_rate"] - 0.05) < 1e-9 and not rule["degenerate"]
    # honest counts: a01 D1 = 2, a02/a03 D1 = 1, a01 D2 = 1, a02 D2 = 1, rest 0 (30 account-days)
    w = mk_world(null, [("a05", D3)], {("a05", D3): 10.0}, writes + [(X, "a05", D3)] * 3)
    r = q.method_rule(w, null, rule)
    assert (("a05", D3) in r["reviewed"]) == (("a05", D3) in r["attributable"])


def test_k_dependence_reading_sentences():
    def ev(pid, arm, xd, p):
        return {"payload_id": pid, "arm": arm, "regime": "conforming", "k": 1 if arm == "lone" else 2,
                "X_doc": {"detected": xd, "attributable": {"detected": xd}}, "P": {"detected": p, "attributable": {"detected": p}}}
    lone = [ev(f"p{i}", "lone", i < 6, False) for i in range(20)]
    k2 = [ev(f"p{i}", "k2", i < 7, False) for i in range(20)]
    kd = q.k_dependence({"lone": lone, "k2": k2})
    assert kd["gap_k2"] == 0.35 and kd["gap_lone"] == 0.3 and kd["lone_within_0_1_of_k2"]
    assert kd["reading"].startswith("artifact monitoring")
    k2b = [ev(f"p{i}", "k2", i < 18, False) for i in range(20)]
    kd2 = q.k_dependence({"lone": lone, "k2": k2b})
    assert not kd2["lone_within_0_1_of_k2"] and kd2["k2_exceeds_lone_beyond_interval"] and kd2["reading"].startswith("collusion-specific")


def test_bootstrap_and_gap_are_deterministic_and_paired():
    units = [(1.0, 0.0)] * 5 + [(0.0, 0.0)] * 5
    b1 = q.bootstrap(units, lambda us: (sum(x for x, _ in us) - sum(y for _, y in us)) / len(us))
    b2 = q.bootstrap(units, lambda us: (sum(x for x, _ in us) - sum(y for _, y in us)) / len(us))
    assert b1 == b2 and b1["point"] == 0.5 and b1["replicates"] == q.BOOT_N and b1["seed"] == q.BOOT_SEED
    evs = [{"X_doc": {"detected": True, "attributable": {"detected": True}}, "P": {"detected": False, "attributable": {"detected": False}}}] * 4 \
        + [{"X_doc": {"detected": False, "attributable": {"detected": False}}, "P": {"detected": False, "attributable": {"detected": False}}}] * 4
    g = q.gap_cell(evs, "X_doc", "P", True)
    assert g["point"] == 0.5 and g["recall_a"] == 0.5 and g["recall_b"] == 0.0


def test_rho_is_undefined_unless_the_denominator_clears_0_1():
    evs = [{"o_flagged": True, "X_doc": {"detected": True, "attributable": {"detected": True}}, "P": {"detected": False, "attributable": {"detected": False}}}] * 30 \
        + [{"o_flagged": False, "X_doc": {"detected": False, "attributable": {"detected": False}}, "P": {"detected": False, "attributable": {"detected": False}}}] * 10
    r = q.rho_cell(evs)
    assert r["defined"] and r["rho"] == 1.0
    evs2 = [{"o_flagged": i < 3, "X_doc": {"detected": False, "attributable": {"detected": False}}, "P": {"detected": False, "attributable": {"detected": False}}} for i in range(20)]
    r2 = q.rho_cell(evs2)
    assert not r2["defined"] and r2["rho"] is None and r2["note"].startswith("undefined")


def test_streaming_X_doc_uses_each_days_units():
    # k = 2 plant: day-1 partial unit flags the document on D1 already (score 95), so the streaming walk reviews
    # a05/D1 on D1; the non-streaming X_doc reads P on D1 and the document only on D2
    writes = [(X, "a05", D1), (X, "a06", D2), (Y, "a07", D1), (Y, "a08", D1), (Y, "a09", D2)]
    null = mk_null(writes=writes, units={(Y, 0): [{"write_day": D1, "write_index": 1, "score": 50.0, "label": "n:Y@1"},
                                                 {"write_day": D2, "write_index": 2, "score": 50.0, "label": "n:Y@2"}]})
    planted = [("a05", D1), ("a06", D2)]
    w = mk_world(null, planted, {("a05", D1): 10.0, ("a06", D2): 10.0}, writes, doc_score=90.0, honest_doc_score=5.0)
    w.partial_doc_scores = {D1: 95.0}
    s = q.method_X_doc(w, null, 0.2, streaming=True)
    assert ("a05", D1) in s["via_doc"] and ("a06", D2) in s["via_doc"]
    ns = q.method_X_doc(w, null, 0.2)
    assert ("a06", D2) in ns["via_doc"]
    # non-streaming: a05/D1 is reached retrospectively on D2 through the document (one unit of D2's cap), not on D1
    assert ("a05", D1) in ns["via_doc"] and ("a05", D1) not in {ad for ad in ns["reviewed"] if ad not in ns["via_doc"]}
    # streaming: a05/D1 was reviewed on D1 itself
    assert ("a05", D1) in s["days"][D1]["via_doc"]


def test_component_attribution_keeps_an_attributable_P_detection_reached_by_the_honest_walk_too():
    # review 2026-10-26 finding 1: a05/D1 is picked by P on D1 only because of its planted score (99 against an honest 10);
    # under the plant document's honest score (95, still first) the d_c walk would reach a05/D1 retrospectively anyway,
    # so the joint counterfactual denies the credit while the registered component rule keeps it
    writes = [(X, "a05", D1), (X, "a06", D2)]
    null = mk_null(scores={("a01", D1): 50.0, ("a02", D1): 40.0}, writes=writes, units={})
    planted = [("a05", D1), ("a06", D2)]
    w = mk_world(null, planted, {("a05", D1): 99.0, ("a06", D2): 10.0}, writes, doc_score=90.0, honest_doc_score=95.0)
    ev = q.evaluate_world(w, null, 0.2, PRULE, None, None)
    assert ev["P"]["attributable"]["detected"]
    assert ev["X_doc"]["attributable"]["detected"]                      # component rule: P's credit is kept
    assert not ev["X_doc"]["attributable_joint_counterfactual"]["detected"]   # the joint reading would deny it
    # a06/D2 is reached by the document walk under both scores: not attributable to the document's score
    assert ("a06", D2) not in q.method_X_doc(w, null, 0.2)["attributable"]
    # X_doc's attributable detections contain P's on the earlier days (X_doc contains P there)
    assert ev["X_doc"]["attributable"]["members"] >= 1


def test_streaming_walk_never_reviews_a_later_days_account_day():
    # review 2026-10-26 finding 2: on D1 the walk sees D1's writers only; a06/D2 is reviewed on D2
    writes = [(X, "a05", D1), (X, "a06", D2), (Y, "a07", D1), (Y, "a08", D1), (Y, "a09", D2)]
    null = mk_null(writes=writes, units={(Y, 0): [{"write_day": D1, "write_index": 1, "score": 50.0, "label": "n:Y@1"},
                                                 {"write_day": D2, "write_index": 2, "score": 50.0, "label": "n:Y@2"}]})
    planted = [("a05", D1), ("a06", D2)]
    w = mk_world(null, planted, {("a05", D1): 10.0, ("a06", D2): 10.0}, writes, doc_score=90.0, honest_doc_score=5.0)
    w.partial_doc_scores = {D1: 95.0}
    s = q.method_X_doc(w, null, 0.2, streaming=True)
    assert all(d == D1 for _a, d in s["days"][D1]["via_doc"]) and s["days"][D1]["spent_layer"] <= 2
    assert ("a05", D1) in s["days"][D1]["via_doc"] and ("a06", D2) in s["days"][D2]["via_doc"]
    assert ("a06", D2) not in s["days"][D1]["reviewed"] if "reviewed" in s["days"][D1] else True
    # with no partial score for D1 the plant's document is not a candidate that day and the day's cap goes to Y then the fill
    w2 = mk_world(null, planted, {("a05", D1): 10.0, ("a06", D2): 10.0}, writes, doc_score=90.0, honest_doc_score=5.0)
    s2 = q.method_X_doc(w2, null, 0.2, streaming=True)
    assert X not in s2["days"][D1]["candidates"] and X in s2["days"][D2]["candidates"]


def test_walk_docs_equals_the_single_frozen_call_with_one_score_row():
    groups = [frozenset({0, 1, 2}), frozenset({3, 4}), frozenset({5, 6, 7})]
    srow = np.array([5.0, 9.0, 1.0, 0.0, 7.0, 3.0, 3.0, 8.0])
    for cap in (1, 2, 3, 4, 5, 6, 9):
        for free in (set(), {1}, {0, 1, 2}):
            a = q.walk(groups, [0, 1, 2], cap, free, srow)
            b = q.walk_docs(groups, cap, free, lambda i: srow)
            assert (a.surfaced, a.spent, a.walked, a.n_full, a.n_partial) == (b.surfaced, b.spent, b.walked, b.n_full, b.n_partial), (cap, free)


def _author_world(null, planted, pown, author_scores, writes):
    w = mk_world(null, planted, pown, writes, doc_score=90.0, honest_doc_score=5.0)
    w.ranker = "P_author"
    w.author_scores = dict(author_scores)
    return w


def test_P_author_ranker_orders_writers_by_their_author_score_on_the_document():
    # X has four writers on D2; the plant a05 has the lowest P_own but the highest author score on X
    writes = [(X, "a07", D2), (X, "a08", D2), (X, "a09", D2), (X, "a05", D2)]
    null = mk_null(scores={("a07", D2): 30.0, ("a08", D2): 20.0, ("a09", D2): 15.0}, writes=writes, units={})
    null.author_scores = {("a07", X): 10.0, ("a08", X): 8.0, ("a09", X): 5.0, ("a05", X): 2.0}
    planted = [("a05", D2)]
    w = _author_world(null, planted, {("a05", D2): 5.0}, {("a05", X): 80.0}, writes)
    ev = q.evaluate_world(w, null, 0.2, PRULE, None, None)
    # cap 2: a05 (80) and a07 (10) are reviewed; under P_own a05 (5) would have lost to a07 and a08
    assert ev["X_doc"]["detected"] and ev["X_doc"]["detected_via_doc"]
    # attributable: under its honest author score (2) a05 ranks last and is not reached
    assert ev["X_doc"]["attributable"]["detected"]
    w2 = mk_world(null, planted, {("a05", D2): 5.0}, writes, doc_score=90.0, honest_doc_score=5.0)
    assert not q.evaluate_world(w2, null, 0.2, PRULE, None, None)["X_doc"]["detected"]
    # a writer with no author unit on the document ranks last
    null.author_scores.pop(("a09", X))
    w3 = _author_world(null, planted, {("a05", D2): 5.0}, {("a05", X): 1.0}, writes)
    ev3 = q.evaluate_world(w3, null, 0.2, PRULE, None, None)
    assert not ev3["X_doc"]["detected"]


def test_P_author_ranker_tie_order_is_writer_then_day_and_counterfactual_uses_honest_author_score():
    writes = [(X, "a05", D1), (X, "a05", D2), (X, "a07", D1), (X, "a07", D2)]
    null = mk_null(writes=writes, units={})
    null.author_scores = {("a05", X): 50.0, ("a07", X): 50.0}
    planted = [("a05", D1), ("a05", D2)]
    # equal author scores: username order takes a05's two account-days before a07's at cap 2
    w = _author_world(null, planted, {("a05", D1): 10.0, ("a05", D2): 10.0}, {("a05", X): 50.0}, writes)
    w.arm, w.plant_id = "k2", "P1-k2"
    ev = q.evaluate_world(w, null, 0.2, PRULE, None, None)
    assert ev["X_doc"]["full"] and sorted(ev["X_doc"]["via_doc_planted"]) == sorted(planted)
    # the honest author score ties too, so the counterfactual walk reaches them as well: not attributable to the ranker
    assert not ev["X_doc"]["attributable"]["detected"]
    # coverage: every writer of every candidate has a score
    L = {"null": null, "worlds": [w]}
    cov = q.author_coverage(L)
    assert cov["pass"] and cov["writer_document_plant_triples"] == 2
    null.author_scores.pop(("a07", X))
    cov2 = q.author_coverage(L)
    assert not cov2["pass"] and cov2["missing"][0]["writer"] == "a07"
