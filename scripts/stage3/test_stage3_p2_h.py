"""Offline tests for stage3_p2_h (P2 block H; preregistration-v1.1.md section D). Synthetic draws, bank and outcomes."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_p2_h as hh  # noqa: E402


def draws():
    return {"draws": [{"draw_id": "H0001", "payload_id": "P1", "slot_id": "s1", "stratum": "need", "task_id": "a/1", "need_class": "needs"},
                      {"draw_id": "H0002", "payload_id": "P1", "slot_id": "s1", "stratum": "any", "task_id": "b/1", "need_class": "no"},
                      {"draw_id": "H0003", "payload_id": "P2", "slot_id": "s2", "stratum": "any", "task_id": "b/1", "need_class": "no"}]}


BANK = [{"task_id": "a/1", "runnable": True, "text_offline": "Do A.", "expected_action_tool": "apply_setting", "weight": 0.1},
        {"task_id": "b/1", "runnable": True, "text_offline": "Do B.", "expected_action_tool": "record_entry", "weight": 0.2}]


def test_draws_with_tasks():
    out = hh.draws_with_tasks(draws(), BANK)
    assert [d["draw_id"] for d in out] == ["H0001", "H0002", "H0003"]
    assert out[0]["task"] == {"task_id": "a/1", "task_text": "Do A.", "slot_id": "s1", "action_tool": "apply_setting"}
    assert out[2]["task"]["slot_id"] == "s2" and out[2]["need_class"] == "no"
    with pytest.raises(KeyError):
        hh.draws_with_tasks({"draws": [dict(draws()["draws"][0], task_id="zz/9")]}, BANK)


def outs():
    rows = []
    spec = {("H0001", "planted"): (True, True), ("H0002", "planted"): (False, False), ("H0003", "planted"): (True, False),
            ("H0001", "clean"): (True, False), ("H0002", "clean"): (False, False), ("H0003", "clean"): (False, True)}
    meta = {d["draw_id"]: d for d in draws()["draws"]}
    for (did, arm), (acc, carry) in spec.items():
        for f in ("kimi", "sol"):
            rows.append({"run_id": f"H|{meta[did]['payload_id']}|{arm}|{f}|r1|{did}", "payload_id": meta[did]["payload_id"],
                         "arm": arm, "follower": f, "draw_id": did, "stratum": meta[did]["stratum"], "need_class": meta[did]["need_class"],
                         "predicate_result": carry, "access_last_action": acc, "access_first_action": acc,
                         "access_first_firing": (acc if carry else None), "error": None})
    return rows


def test_joint_table_equal_weight_per_draw():
    t = hh.joint_table(outs(), n_boot=200)
    p = t["planted"]["cells"]
    assert p["needs|access|carried"]["share"] == pytest.approx(1 / 3)
    assert p["no|no_access|not_carried"]["share"] == pytest.approx(1 / 3)
    assert p["no|access|not_carried"]["share"] == pytest.approx(1 / 3)
    assert sum(v["share"] for v in p.values()) == pytest.approx(1.0, abs=1e-5)
    assert t["clean"]["cells"]["no|no_access|carried"]["share"] == pytest.approx(1 / 3)
    assert {"lo", "hi"} <= set(p["needs|access|carried"])
    assert t["label"].startswith("descriptive")


def test_by_stratum_and_clean_firings_by_pair():
    r = hh.analyse_H(outs(), n_boot=100)
    assert set(r["by_stratum"]) == {"need", "any"}
    assert r["by_stratum"]["need"]["planted"]["carry"]["point"] == pytest.approx(1.0)
    assert r["clean_firings"] == [{"draw_id": "H0003", "payload_id": "P2", "task_id": None, "followers": ["kimi", "sol"]}]
    assert r["access_at_first_firing"]["planted"] == {"n_fired": 2, "access_at_first_firing": 2, "no_access_at_first_firing": 0, "unknown": 0}


def test_unresolved_runs_are_their_own_carry_class():
    rows = outs()
    rows[0]["predicate_result"], rows[0]["error"] = None, "infra_error"
    t = hh.joint_table(rows, n_boot=50)
    assert any(k.endswith("|unresolved") and v["n_runs"] == 1 for k, v in t["planted"]["cells"].items())
