"""Offline tests for stage3_note_shortlist (a real-example shortlist for the note; ids only). Synthetic only."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_note_shortlist as ns  # noqa: E402


def world():
    man = [{"payload_id": p, "regime": r, "scorable": True, "application_id": p} for p, r in
           (("P1", "routine"), ("P2", "middle"), ("P3", "routine"), ("P4", "alarming"), ("P5", "middle"))]
    classes = {"P1": "S3", "P2": "S3", "P3": "S2", "P4": "S3", "P5": "S3"}
    missed = {"P1": True, "P2": True, "P3": True, "P4": True, "P5": False}      # P5 flagged; P4 alarming
    outs = []
    for p in ("P1", "P2", "P3", "P4", "P5"):
        for f in ("kimi", "sol"):
            for k in range(1, 4):
                outs.append({"run_id": f"c|{p}|planted|{f}|r{k}", "payload_id": p, "arm": "planted", "follower": f,
                             "predicate_result": (p == "P1") or (p == "P2" and k == 1), "checked": k == 1 and f == "kimi",
                             "declined": False, "ended_in_action": True, "error": None})
    audit = {"c|P1|planted|kimi|r1": "acts", "c|P2|planted|kimi|r1": "questions"}
    return man, classes, missed, outs, audit


def test_eligibility_order_and_candidates():
    man, classes, missed, outs, audit = world()
    r = ns.shortlist(man, classes, missed, outs, audit, cap=8, min_s3=1)
    assert [x["payload_id"] for x in r["plants"]] == ["P1", "P2"]           # S3, RM, missed; ordered by uptake
    p1 = r["plants"][0]
    assert p1["raw_uptake"] == 1.0 and {c["follower"] for c in p1["candidate_runs"]} == {"kimi", "sol"}
    assert p1["candidate_runs"][0] == {"run_id": "c|P1|planted|kimi|r1", "follower": "kimi", "kind": "audited_acts"}
    p2 = r["plants"][1]                                                        # its only carried Kimi run was audited 'questions'
    assert p2["raw_uptake"] == round(2 / 6, 6) and [c["kind"] for c in p2["candidate_runs"]] == ["unaudited_clean_carry"]
    assert r["s2_added"] is False


def test_s2_added_and_marked_when_too_few_s3():
    man, classes, missed, outs, audit = world()
    for o in outs:
        if o["payload_id"] == "P3":
            o["predicate_result"] = True
    r = ns.shortlist(man, classes, missed, outs, audit, cap=8, min_s3=4)
    assert r["s2_added"] is True and any(x["payload_id"] == "P3" and x["class"] == "S2" for x in r["plants"])
