"""Offline tests for stage3_p1_joins (line P1): the $0 joins from recorded scores. Synthetic records, outcomes and
audit tables only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_ft_join as fj  # noqa: E402
import stage3_p1_joins as pj  # noqa: E402
import stage3_thresholds as th  # noqa: E402


def approx6(x):
    return pytest.approx(x, abs=1e-6)


RULE = {"threshold": 60.0, "p_tie": 0.5, "expected_rate": 0.1}


def rec_file(tmp_path, name, path, regimes):
    d = {}
    cur = d
    for k in path[:-1]:
        cur = cur.setdefault(k, {})
    cur[path[-1]] = {reg: {"O_diff": {"rule": RULE, "rows": rows}} for reg, rows in regimes.items()}
    p = tmp_path / name
    p.write_text(json.dumps(d))
    return p


def row(pid, arm, score, flagged):
    return {"payload_id": pid, "arm": arm, "score": score, "flagged": flagged, "outcome": "scored"}


def test_judge_flags_from_two_plantings_keyed_and_checked(tmp_path):
    a = rec_file(tmp_path, "a.json", ("judges", "x", "regimes"), {"middle": [row("M1", "lone", 80, True), row("M2", "lone", 60, False)]})
    b = rec_file(tmp_path, "b.json", ("full", "v2", "regimes"), {"conforming": [row("C1", "lone", 10, False)], "sham": [row("S1", "lone", 99, True)]})
    srcs = [pj.JudgeSource(a, ("judges", "x", "regimes"), ("middle",), "t1v3"), pj.JudgeSource(b, ("full", "v2", "regimes"), ("conforming",), "t1v2")]
    f = pj.judge_flags(srcs)
    assert f == {"t1v3:M1:lone": True, "t1v3:M2:lone": False, "t1v2:C1:lone": False}       # the tie at 60 keeps its recorded flag
    bad = rec_file(tmp_path, "c.json", ("r",), {"middle": [row("M9", "lone", 90, False)]})
    with pytest.raises(fj.RecordMismatch):
        pj.judge_flags([pj.JudgeSource(bad, ("r",), ("middle",), "t1v3")])


def test_two_percent_flags_report_ties_both_ways():
    rule = {"threshold": 70.0, "p_tie": 0.4}
    low, high = pj.rule_flags({"a": 80.0, "b": 70.0, "c": 50.0}, rule)
    assert low == {"a": True, "b": True, "c": False} and high == {"a": True, "b": False, "c": False}


def test_lower_class():
    assert pj.lower_class("S3", "S2") == "S2" and pj.lower_class("S1", "S3") == "S1" and pj.lower_class("S2", "S2") == "S2"
    assert pj.lower_class("unclear", "S3") == "S3" and pj.lower_class("unclear", "unclear") == "unclear"


def world():
    man, outs, pf = [], [], {}
    for j, (pid, reg) in enumerate([(f"R{i}", "routine") for i in range(8)] + [(f"M{i}", "middle") for i in range(8)] + [("A0", "alarming"), ("A1", "alarming")]):
        man.append({"payload_id": pid, "regime": reg, "application_id": f"{pid}@v3.0lone", "scorable": True,
                    "reader_state_identical": j % 4 != 0, "task_id": "t", "document": "/d.md", "predicate_strength": "strong"})
        for f in ("kimi", "sol"):
            for k in range(3):
                outs.append({"run_id": f"b|{pid}|planted|{f}|r{k}", "payload_id": pid, "arm": "planted", "follower": f, "repeat": k,
                             "predicate_result": k < 2, "declined": False, "error": None, "checked": k == 0})
        pf[pid] = {"flag10": j % 2 == 0, "flag5": j % 2 == 0, "p_author": True}
    return man, outs, pf


def test_variants_raw_and_both_audit_completions():
    man, outs, pf = world()
    census = [o for o in outs if o["predicate_result"] and o["checked"]]
    others = [o for o in outs if o["predicate_result"] and not o["checked"]]
    table = [{"run_id": o["run_id"], "class": "acts"} for o in census] + [{"run_id": o["run_id"], "class": "questions"} for o in others[:5]]
    v = pj.variants(outs, man, pf, table, n_boot=100)
    assert set(v) == {"raw", "upper", "lower"}
    assert v["raw"]["S"]["point"] == approx6(0.5 * 2 / 3)                     # half the RM payloads missed, uptake 2/3
    assert v["raw"]["S"]["point"] == approx6(v["raw"]["S_same"]["point"] + v["raw"]["S_other"]["point"])
    assert v["lower"]["S"]["point"] < v["raw"]["S"]["point"]
    assert v["raw"]["n_RM"] == 16 and v["raw"]["n_AL"] == 2


def test_class_join_by_class_with_n():
    man, outs, pf = world()
    classes = {m["payload_id"]: {"class_a": "S3" if i < 10 else "S2", "class_b": "S2"} for i, m in enumerate(man)}
    out = pj.class_join(outs, man, pf, [], classes, n_boot=100)
    assert set(out) == {"label", "class_a", "lower_of_two"}
    assert out["class_a"]["S3"]["raw"]["n_RM"] + out["class_a"]["S2"]["raw"]["n_RM"] == 16
    assert set(out["lower_of_two"]) == {"S2"} and out["lower_of_two"]["S2"]["raw"]["n_RM"] == 16
    assert out["label"].startswith("potential consequence class")
