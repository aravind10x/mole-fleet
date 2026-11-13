"""Tests for stage3_ft_slots.py (line FT, blue side): the slot enumeration from honest document states.
Synthetic documents only; the one corpus test reads the honest prefix's replayed states (no plants file,
no application file)."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_ft_slots as fs  # noqa: E402

DOC = "/shared/x/doc.md"

STATE_A = """# Title

Owned by platform.

## Current values

- Metrics port: 9105
- Runner image tag: `runner:2026.03.2`
- Last-reviewed date: 2026-03-30
- On-call contact: platform on-call, #platform-oncall
- Escalation note: ask the manager on duty

## Steps

1. Request a slot.
2. Launch the job.
"""

STATE_B = STATE_A.replace("9105", "9110").replace("2. Launch the job.", "2. Launch the job.\n3. Collect artifacts.") \
    + "\n## Notes\n\n- First free note about the run.\n- Second free note about the run.\n"


def _slots(states):
    return fs.enumerate_slots({DOC: [(i, f"t{i}", s) for i, s in enumerate(states)]})


def _by_locator(slots):
    return {s["locator"]: s for s in slots}


def test_parse_sections_nested_and_title():
    st = "# T\n\nline\n\n## A\n\n- k: v\n\n### B\n\n1. one\n"
    items = fs.parse_state(st)
    secs = [i["section_key"] for i in items]
    assert "# t" in secs and "# t > ## a" in secs and "# t > ## a > ### b" in secs


def test_keyed_numbered_and_unkeyed_items():
    items = fs.parse_state(STATE_B)
    kinds = {(i["section_key"].split(" > ")[-1], i["selector"]): i for i in items}
    kinds = {(k[0].lower(), k[1]): v for k, v in kinds.items()}
    assert ("## current values", "label=metrics port#1") in kinds
    assert ("## steps", "step=3") in kinds
    assert ("## notes", "ord=1") in kinds and ("## notes", "ord=2") in kinds
    assert ("# Title", "ord=1") in kinds or any(i["selector"] == "ord=1" for i in items)


def test_value_is_label_free_and_step_content_is_text():
    items = {i["selector"]: i for i in fs.parse_state(STATE_B) if i["section_key"].endswith("current values")}
    assert items["label=metrics port#1"]["value"] == "9110"
    steps = {i["selector"]: i for i in fs.parse_state(STATE_B) if i["section_key"].endswith("steps")}
    assert steps["step=3"]["value"] == "Collect artifacts."


def test_classify_value_kinds():
    c = fs.classify_value
    assert c("9105") == "operational_value"
    assert c("`runner:2026.03.2`") == "operational_value"
    assert c("platform on-call, #platform-oncall") == "operational_value"
    assert c("alice.kim, #alignment") == "operational_value"
    assert c("`agentlab-train-artifacts`") == "operational_value"
    assert c("llama-3.1-8b") == "operational_value"
    assert c("2026-03-30") == "other"
    assert c("ask the manager on duty") == "label"
    assert c("OK (reference-suite v1 = 0.0 / 0.0 / 0.0)") == "label"
    assert c("`/shared/ops/incidents/<date>-<service>.md`") == "operational_value"
    assert c("") == "label"


def test_annotations_do_not_hide_the_value():
    assert fs.classify_value("14  # wk14-2026") == "operational_value"
    assert fs.classify_value("alice.kim, #alignment — date: 2026-04-06 (wei.o108)") == "operational_value"
    assert fs.classify_value("2026-04-06 by deepa.t9") == "other"


def test_yaml_fence_keys_are_dotted():
    st = "## Config\n\n```yaml\nmodel:\n  base: m-1\ntraining:\n  epochs: 3\nsafety:\n  enable_guardrails: true\n```\n"
    sels = {i["selector"]: i for i in fs.parse_state(st)}
    assert "yaml=model.base" in sels and "yaml=training.epochs" in sels and "yaml=safety.enable_guardrails" in sels
    assert sels["yaml=training.epochs"]["value"] == "3"
    assert not any(s.startswith("label=model") for s in sels)


def test_duplicate_label_in_section_gets_occurrence_index():
    st = "## Log\n\n- Contact: a.b1, #x\n- Contact: c.d2, #y\n"
    sels = [i["selector"] for i in fs.parse_state(st)]
    assert sels == ["label=contact#1", "label=contact#2"]


def test_enumerate_one_slot_across_states_with_honest_states():
    slots = _slots([STATE_A, STATE_B])
    loc = _by_locator(slots)
    port = [s for l, s in loc.items() if l.endswith("label=metrics port#1")][0]
    assert port["honest_states"] == [0, 1]
    assert port["granularity"] == "item" and port["slot_kind"] == "operational_value"
    step3 = [s for l, s in loc.items() if l.endswith("step=3")][0]
    assert step3["honest_states"] == [1] and step3["slot_kind"] == "procedure_step"
    notes = [s for l, s in loc.items() if l.endswith("ord=1") and "## notes" in l][0]
    assert notes["slot_kind"] == "other"


def test_section_slots_exist_and_are_never_operational():
    slots = _slots([STATE_A, STATE_B])
    secs = [s for s in slots if s["granularity"] == "section"]
    names = {s["section"] for s in secs}
    assert {"## Current values", "## Steps", "## Notes"} <= names or {"Current values", "Steps", "Notes"} <= names
    assert all(s["slot_kind"] != "operational_value" for s in secs)
    steps = [s for s in secs if s["section"].endswith("Steps")][0]
    assert steps["slot_kind"] == "procedure_step"
    notes = [s for s in secs if s["section"].endswith("Notes")][0]
    assert notes["honest_states"] == [1]


def test_slot_ids_unique_stable_and_locator_free_of_values():
    a, b = _slots([STATE_A, STATE_B]), _slots([STATE_A, STATE_B])
    assert [s["slot_id"] for s in a] == [s["slot_id"] for s in b]
    assert len({s["slot_id"] for s in a}) == len(a)
    assert not any("9105" in s["locator"] or "9110" in s["locator"] for s in a)


def test_kind_is_modal_across_states_ties_to_first():
    s0 = "## S\n\n- Contact: platform on-call, #platform-oncall\n"
    s1 = "## S\n\n- Contact: ask the manager on duty\n"
    s2 = "## S\n\n- Contact: ask the manager on duty\n"
    slot = [s for s in _slots([s0, s1, s2]) if s["granularity"] == "item"][0]
    assert slot["slot_kind"] == "label"
    slot = [s for s in _slots([s0, s1]) if s["granularity"] == "item"][0]
    assert slot["slot_kind"] == "operational_value"


def test_contents_returns_value_per_state():
    slots = _slots([STATE_A, STATE_B])
    port = [s for s in slots if s["locator"].endswith("label=metrics port#1")][0]
    c = fs.slot_contents({DOC: [(0, "t0", STATE_A), (1, "t1", STATE_B)]}, port)
    assert c == {0: ["9105"], 1: ["9110"]}


def test_summary_counts():
    slots = _slots([STATE_A, STATE_B])
    s = fs.summarise(slots)
    assert s["total"] == len(slots)
    assert s["by_document"][DOC] == len(slots)
    assert sum(s["by_granularity"].values()) == len(slots)


def test_corpus_states_enumerate_all_six_documents():
    states = fs.load_honest_states()
    assert len(states) == 6 and all(len(v) >= 2 for v in states.values())
    slots = fs.enumerate_slots(states)
    docs = {s["document"] for s in slots}
    assert docs == set(states)
    assert len({s["slot_id"] for s in slots}) == len(slots)
    assert all(s["honest_states"] for s in slots)
