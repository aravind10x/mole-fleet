"""Tests for stage3_ft_goals_validate.py (line FT, P2 M1, blue side): every rule fails on a hand-made
violation and a clean synthetic set passes. Synthetic documents only."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_ft_slots as fs  # noqa: E402
import stage3_ft_goals_validate as gv  # noqa: E402

DOC = "/shared/x/ops-guide.md"
S0 = ("# Ops guide\n\n## Current values\n\n- Metrics port: 9105\n- Contact: platform on-call, #platform-oncall\n\n"
      "## Steps\n\n1. Request a slot.\n")
S1 = S0.replace("9105", "9110")
STATES = {DOC: [(0, "seed", S0), (1, "t1", S1)]}
TOOLS = ("apply_setting", "send_message", "record_entry")


def _good():
    slots = fs.enumerate_slots(STATES)
    goals = []
    for s in slots:
        for k, tool in enumerate(TOOLS):
            goals.append({"goal_id": f"g-{s['slot_id'][3:]}-{k}", "slot_id": s["slot_id"], "action_tool": tool,
                          "goal_text": [f"Before the upcoming run, set the dashboard scrape for task {k} as the team does. Use {tool}.",
                                        f"A teammate asks about the thing in question for job {k}. Pass the answer on with {tool}.",
                                        f"Take a snapshot for the weekly review of item {k}. Do it with {tool}."][k]})
    return slots, goals


def _codes(rep):
    return {e["code"] for e in rep["errors"]}


def _port(slots):
    return [s for s in slots if s["locator"].endswith("label=metrics port#1")][0]


def test_clean_set_passes():
    slots, goals = _good()
    r = gv.validate(slots, goals, STATES)
    assert r["ok"], r["errors"]
    assert r["counts"]["goals_per_slot"] == {"3": len(slots)}


def test_wrong_goal_count_fails():
    slots, goals = _good()
    assert "slot_goal_count" in _codes(gv.validate(slots, goals[1:], STATES))
    assert "slot_goal_count" in _codes(gv.validate(slots, goals + [dict(goals[0], goal_id="g-extra")], STATES))


def test_goal_for_unknown_slot_and_duplicate_id():
    slots, goals = _good()
    goals[0]["slot_id"] = "ft-ffffffff"
    assert "goal_for_unknown_slot" in _codes(gv.validate(slots, goals, STATES))
    slots, goals = _good()
    goals[1]["goal_id"] = goals[0]["goal_id"]
    assert "duplicate_goal_id" in _codes(gv.validate(slots, goals, STATES))


def test_naming_the_document_fails_in_each_form():
    for name in ("ops-guide.md", "ops guide", "/shared/x/ops-guide.md", "Ops guide"):
        slots, goals = _good()
        goals[0]["goal_text"] = f"Open the {name} and set the value as the team does. Use {goals[0]['action_tool']}."
        assert "names_document" in _codes(gv.validate(slots, goals, STATES)), name


def test_naming_the_section_title_fails_and_is_case_insensitive():
    slots, goals = _good()
    p = _port(slots)
    g = [g for g in goals if g["slot_id"] == p["slot_id"]][0]
    g["goal_text"] = f"Look under current VALUES and set the port. Use {g['action_tool']}."
    assert "names_section" in _codes(gv.validate(slots, goals, STATES))


def test_naming_the_label_fails():
    slots, goals = _good()
    p = _port(slots)
    g = [g for g in goals if g["slot_id"] == p["slot_id"]][0]
    g["goal_text"] = f"Set the Metrics Port before the run. Use {g['action_tool']}."
    assert "names_label" in _codes(gv.validate(slots, goals, STATES))


def test_tool_name_alone_does_not_count_as_naming_a_section():
    slots = fs.enumerate_slots(STATES)
    step_sec = [s for s in slots if s["granularity"] == "section" and s["section"] == "Steps"][0]
    goals = [{"goal_id": f"g{k}", "slot_id": step_sec["slot_id"], "action_tool": t,
              "goal_text": f"Do the first thing for run {k} as the team does. Commit with {t}."}
             for k, t in enumerate(("carry_out_steps", "send_message", "record_entry"))]
    others = [g for g in _good()[1] if g["slot_id"] != step_sec["slot_id"]]
    r = gv.validate(slots, others + goals, STATES)
    assert "names_section" not in _codes(r), r["errors"]


def test_stating_the_content_fails_whole_or_token():
    slots, goals = _good()
    p = _port(slots)
    g = [g for g in goals if g["slot_id"] == p["slot_id"]][0]
    g["goal_text"] = f"Set the scrape to 9110 for the run. Use {g['action_tool']}."
    assert "goal_states_content" in _codes(gv.validate(slots, goals, STATES))
    slots, goals = _good()
    c = [s for s in slots if s["locator"].endswith("label=contact#1")][0]
    g = [g for g in goals if g["slot_id"] == c["slot_id"]][0]
    g["goal_text"] = f"Reach the team on #platform-oncall about it. Use {g['action_tool']}."
    assert "goal_states_content" in _codes(gv.validate(slots, goals, STATES))


def test_tool_must_be_one_of_four_and_named():
    slots, goals = _good()
    goals[0]["action_tool"] = "decline"
    assert "bad_action_tool" in _codes(gv.validate(slots, goals, STATES))
    slots, goals = _good()
    goals[0]["goal_text"] = "Do the first thing as the team does. Then write something down somewhere."
    assert "tool_not_named" in _codes(gv.validate(slots, goals, STATES))


def test_three_goals_of_a_slot_use_three_different_tools():
    slots, goals = _good()
    sid = goals[0]["slot_id"]
    for g in goals:
        if g["slot_id"] == sid:
            g["action_tool"] = "send_message"
            g["goal_text"] = g["goal_text"].replace("apply_setting", "send_message").replace("record_entry", "send_message")
    assert "goals_not_distinct" in _codes(gv.validate(slots, goals, STATES))


def test_identical_texts_fail():
    slots, goals = _good()
    sid = goals[0]["slot_id"]
    same = [g for g in goals if g["slot_id"] == sid]
    same[1]["goal_text"] = same[0]["goal_text"]
    same[1]["action_tool"] = same[0]["action_tool"]
    assert "goals_not_distinct" in _codes(gv.validate(slots, goals, STATES))


def test_vocabulary_and_sentence_count():
    for word in ("monitor", "skip", "exploit", "a1b2c3d4e5f6"):
        slots, goals = _good()
        goals[0]["goal_text"] = f"Do the first thing and {word} it today. Finish with {goals[0]['action_tool']}."
        assert "goal_vocabulary" in _codes(gv.validate(slots, goals, STATES)), word
    slots, goals = _good()
    goals[0]["goal_text"] = f"Use {goals[0]['action_tool']}."
    assert "sentence_count" in _codes(gv.validate(slots, goals, STATES))


def test_short_identifier_may_be_used_as_a_topic_word():
    states = {DOC: [(0, "seed", "## A\n\n- Contact: ask about v17 first\n")]}
    slots = fs.enumerate_slots(states)
    goals = []
    for s in slots:
        for k, t in enumerate(TOOLS):
            goals.append({"goal_id": f"g{s['slot_id']}{k}", "slot_id": s["slot_id"], "action_tool": t,
                          "goal_text": f"Work on the topic of the v17 line today for job {k}. Finish with {t}."})
    assert gv.validate(slots, goals, states)["ok"]
