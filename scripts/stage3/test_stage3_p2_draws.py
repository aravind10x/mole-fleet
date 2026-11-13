"""Offline tests for stage3_p2_draws (line P2, step 2.2): the D and H draws and the exact need table. Synthetic manifest,
goals, bank, need matrix and clean workspaces only."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_p2_draws as pd  # noqa: E402

DOC = "/shared/ops/oncall-runbook.md"
CLEAN = "# Oncall\n\n## Settings\n- pager_rate: 5\n- owner: team-a\n\n## Steps\n1. Open the console.\n2. Page the owner.\n"
L_RATE = f"{DOC} :: # oncall > ## settings :: label=pager_rate#1"
L_OWNER = f"{DOC} :: # oncall > ## settings :: label=owner#1"
L_GONE = f"{DOC} :: # oncall > ## settings :: label=retired_key#1"
L_STEP = f"{DOC} :: # oncall > ## steps :: step=2"


def world(tmp_path):
    slots = {"s-rate": {"slot_id": "s-rate", "document": DOC, "locator": L_RATE},
             "s-owner": {"slot_id": "s-owner", "document": DOC, "locator": L_OWNER},
             "s-gone": {"slot_id": "s-gone", "document": DOC, "locator": L_GONE},
             "s-step": {"slot_id": "s-step", "document": DOC, "locator": L_STEP}}
    goals = [{"goal_id": f"g-{s}-{i}", "slot_id": s, "goal_text": "x", "action_tool": "apply_setting"} for s in slots for i in range(3)]
    man = [{"payload_id": "P2", "regime": "middle", "slot_id": "s-rate", "scorable": True},
           {"payload_id": "P1", "regime": "routine", "slot_id": "s-owner", "scorable": True},
           {"payload_id": "P3", "regime": "alarming", "slot_id": "s-gone", "scorable": True}]
    bank = [{"task_id": "a/1", "weight": 0.1, "runnable": True}, {"task_id": "a/2", "weight": 0.2, "runnable": True},
            {"task_id": "a/3", "weight": 0.3, "runnable": True}, {"task_id": "b/1", "weight": 0.15, "runnable": True},
            {"task_id": "c/1", "weight": 0.25, "runnable": False}]
    matrix = {"tasks": {"a/1": {"needs": ["s-rate"], "may_touch": ["s-step"]}, "a/2": {"needs": ["s-gone"], "may_touch": ["s-rate"]},
                        "a/3": {"needs": [], "may_touch": ["s-owner", "s-rate"]}, "b/1": {"needs": [], "may_touch": []}}}
    root = tmp_path / "docs"
    for pid in ("P1", "P2", "P3"):
        d = root / pid / "clean"
        d.mkdir(parents=True)
        (d / "oncall-runbook.md").write_text(CLEAN)
        (d / "history.json").write_text(json.dumps({"as_of": "t", "paths": {"oncall-runbook.md": DOC}, "revisions": {}}))
    return slots, goals, man, bank, matrix, root


def test_slot_exists_uses_blue_parser(tmp_path):
    assert pd.slot_exists(CLEAN, L_RATE) and pd.slot_exists(CLEAN, L_STEP)
    assert not pd.slot_exists(CLEAN, L_GONE)
    assert pd.slot_exists(CLEAN, f"{DOC} :: # oncall > ## steps :: section")


def test_draw_D_follows_the_registered_rule(tmp_path):
    slots, goals, man, bank, matrix, root = world(tmp_path)
    d = pd.draw_D(man, goals)
    rng = random.Random(20261114)
    want = []
    for m in sorted(man, key=lambda m: m["payload_id"]):
        i = rng.randrange(3)
        want.append((m["payload_id"], f"g-{m['slot_id']}-{i}"))
    assert [(x["payload_id"], x["goal_id"]) for x in d["draws"]] == want
    assert d["seed"] == 20261114 and set(d["draws"][0]) == {"payload_id", "slot_id", "goal_id", "goal_index", "action_tool"}


def test_eligibility_needs_every_needed_slot_in_the_clean_state(tmp_path):
    slots, goals, man, bank, matrix, root = world(tmp_path)
    clean = pd.clean_docs(root, "P1")
    assert pd.eligible(matrix["tasks"]["a/1"], slots, clean) is True
    assert pd.eligible(matrix["tasks"]["a/2"], slots, clean) is False          # needs a slot absent from the clean state
    assert pd.eligible(matrix["tasks"]["b/1"], slots, clean) is True           # needs nothing


def test_need_table_exact_shares(tmp_path):
    slots, goals, man, bank, matrix, root = world(tmp_path)
    t = pd.need_table(man, matrix, bank, slots, root)
    p2 = t["payloads"]["P2"]                                                     # slot s-rate
    assert p2["need_weight_share_all"] == pytest.approx(0.1) and p2["need_weight_share_runnable"] == pytest.approx(0.1 / 0.75)
    assert p2["may_touch_weight_share_all"] == pytest.approx(0.5)                # a/2 and a/3 may touch it, neither needs it
    assert p2["may_touch_eligible_weight_share_all"] == pytest.approx(0.3)      # a/2 is not eligible (needs a missing slot)
    assert t["payloads"]["P1"]["need_weight_share_all"] == 0.0
    assert t["n_empty"] == {"need": 1, "may_touch": 1, "need_eligible": 2, "may_touch_eligible": 1}
    assert t["mean"]["need_weight_share_all"] == pytest.approx((0.1 + 0.0 + 0.2) / 3)       # P3's slot is needed by a/2
    assert set(t["by_regime"]) == {"routine", "middle", "alarming"}


def test_draw_H_strata_with_overflow_to_the_last(tmp_path):
    slots, goals, man, bank, matrix, root = world(tmp_path)
    h = pd.draw_H(man, matrix, bank, slots, root)
    by = {}
    for x in h["draws"]:
        by.setdefault(x["payload_id"], []).append(x)
    assert all(len(v) == 4 for v in by.values())
    p2 = [x["stratum"] for x in by["P2"]]
    assert p2 == ["need", "need", "may_touch", "all"]
    p1 = [x["stratum"] for x in by["P1"]]                                      # P1's slot is needed by no task: its 2 go to the last
    assert p1 == ["may_touch", "all", "all", "all"]
    assert all(x["task_id"] == "a/1" for x in by["P2"] if x["stratum"] == "need")
    assert all(x["task_id"] != "c/1" for x in h["draws"])                      # never a task that is not runnable
    assert all(x["task_id"] != "a/2" for x in h["draws"])                      # never an ineligible task
    assert h == pd.draw_H(man, matrix, bank, slots, root)                      # seeded


# ── v1 (preregistration-v1.1 sections A and D): 54 retained payloads; need at the payload's clean state ─────────────

def fake_need(task, slots_of_document, text):
    """Synthetic stand-in for stage3_ft_bank.need_at_state: the task's needs / may_touch from its record, limited to
    slots whose label occurs in the text."""
    present = {s["slot_id"] for s in slots_of_document if s["locator"].split("label=")[-1].split("#")[0] in text
               or s["locator"].endswith("step=2")}
    return {"needs": sorted(x for x in task.get("_needs", []) if x in present),
            "may_touch": sorted(x for x in task.get("_may", []) if x in present)}


def world_v1(tmp_path):
    slots, goals, man, bank, matrix, root = world(tmp_path)
    for b in bank:
        t = matrix["tasks"].get(b["task_id"], {})
        b["_needs"], b["_may"] = t.get("needs", []), t.get("may_touch", [])
    validity = [{"payload_id": "P1", "valid": True, "code": None}, {"payload_id": "P2", "valid": True, "code": None},
                {"payload_id": "P3", "valid": False, "code": "single_plain_word"}]
    return slots, goals, man, bank, root, validity


def test_retained_drops_the_invalid_payloads(tmp_path):
    slots, goals, man, bank, root, validity = world_v1(tmp_path)
    kept = pd.retained(man, validity)
    assert [m["payload_id"] for m in kept] == ["P1", "P2"]
    with pytest.raises(ValueError):
        pd.retained(man, validity[:2])                                   # a payload missing from the table


def test_draw_D_v1_runs_on_the_retained_payloads(tmp_path):
    slots, goals, man, bank, root, validity = world_v1(tmp_path)
    d = pd.draw_D(pd.retained(man, validity), goals)
    assert [x["payload_id"] for x in d["draws"]] == ["P1", "P2"]


def test_need_at_state_populations_and_draw_H_v1(tmp_path):
    slots, goals, man, bank, root, validity = world_v1(tmp_path)
    kept = pd.retained(man, validity)
    pop = pd.populations_at_state(kept[1], bank, slots, root, need_fn=fake_need)      # P2, slot s-rate
    assert [b["task_id"] for b in pop["need"]] == ["a/1"]
    assert [b["task_id"] for b in pop["may_touch"]] == ["a/2", "a/3"]
    assert [b["task_id"] for b in pop["any"]] == ["a/1", "a/2", "a/3", "b/1"]           # all runnable, sorted
    h = pd.draw_H_v1(kept, bank, slots, root, need_fn=fake_need)
    assert h["n"] == 8 and len({x["draw_id"] for x in h["draws"]}) == 8
    p2 = [x for x in h["draws"] if x["payload_id"] == "P2"]
    assert [x["stratum"] for x in p2] == ["need", "need", "may_touch", "any"]
    assert all(x["need_class"] == "needs" for x in p2 if x["stratum"] == "need")
    p1 = [x for x in h["draws"] if x["payload_id"] == "P1"]                          # P1's slot: no task needs it
    assert [x["stratum"] for x in p1] == ["may_touch", "any", "any", "any"]
    assert {x["need_class"] for x in p1} <= {"needs", "may_touch", "no"}
    rng = random.Random(20261114)                                                      # one generator, payloads in order
    pop1 = pd.populations_at_state(kept[0], bank, slots, root, need_fn=fake_need)
    want = rng.choices(pop1["may_touch"], weights=[b["weight"] for b in pop1["may_touch"]], k=1)
    assert p1[0]["task_id"] == want[0]["task_id"]
    assert h == pd.draw_H_v1(kept, bank, slots, root, need_fn=fake_need)


def test_need_table_v1_counts(tmp_path):
    slots, goals, man, bank, root, validity = world_v1(tmp_path)
    t = pd.need_table_v1(pd.retained(man, validity), bank, slots, root, need_fn=fake_need)
    assert t["n_payloads"] == 2 and t["payloads"]["P2"]["need_weight_share_all"] == pytest.approx(0.1)
    assert t["payloads"]["P2"]["need_weight_share_runnable"] == pytest.approx(0.1 / 0.75)
    assert t["n_empty"] == {"need": 1, "may_touch": 0}
    assert t["mean"]["need_weight_share_all"] == pytest.approx(0.05)
