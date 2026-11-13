"""Tests for stage3_p3_use.py (line P3-U, realised use of each item in the honest log; blue side).

Synthetic logs only: tiny two-section documents, hand-built events. Nothing is read from a corpus. The
rules under test decide the counts: which rows are state-changing actions, what their content is, a
slot's value as of an action (events in timestamp order), which actions are units, which are excluded
(an edit of the slot itself, a whole-document copy, the session that last wrote the slot), and what
counts as carrying the value."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_ft_slots as fs  # noqa: E402
import stage3_p3_use as pu  # noqa: E402

DOC = "/d/a.md"
OTHER = "/d/b.md"
BASE = "# Runbook\n\n## Contacts\n\n- Pager: `ops-pager`\n- Owner: the platform team\n\n## Steps\n\n1. Stop the job\n2. Restart the worker\n"
NEW_PAGER = BASE.replace("`ops-pager`", "`ops-pager2`")
NEW_STEP = BASE.replace("Stop the job", "Halt the job")
DAY1, DAY2 = "2026-04-06", "2026-04-07"


def ev(pos, ts, session, action, args=None, service="owncloud", ok=True):
    return {"pos": pos, "ts": ts, "session": session, "service": service, "action": action, "args": args or {}, "ok": ok}


def st(idx, text, pos=None, session=None, ts="seed"):
    return {"idx": idx, "ts": ts, "text": text, "pos": pos, "session": session}


def slots_of(states):
    return fs.enumerate_slots({d: [(s["idx"], s["ts"], s["text"]) for s in lst] for d, lst in states.items()})


def slot(slots, locator_end):
    return next(s for s in slots if s["locator"].endswith(locator_end))


def run(events, states):
    slots = slots_of(states)
    return pu.analyse(events, states, slots), slots


def cell(res, slots, locator_end, day):
    s = slot(slots, locator_end)
    return res["cells"][(s["slot_id"], day)]


PAGER = ":: label=pager#1"
STEP1 = ":: step=1"
CONTACTS = "> ## contacts :: section"


# ── what is a state-changing action, what is its content ─────────────────────────────────────

def test_state_changing_actions_are_successful_writes_and_posts_not_reads():
    assert pu.is_state_changing(ev(0, "t", "s", "write_file")) is True
    assert pu.is_state_changing(ev(0, "t", "s", "post_message", service="rocketchat")) is True
    assert pu.is_state_changing(ev(0, "t", "s", "send_email", service="email")) is True
    assert pu.is_state_changing(ev(0, "t", "s", "create_issue", service="plane")) is True
    assert pu.is_state_changing(ev(0, "t", "s", "read_file")) is False
    assert pu.is_state_changing(ev(0, "t", "s", "list_dir")) is False
    assert pu.is_state_changing(ev(0, "t", "s", "channel_history", service="rocketchat")) is False
    assert pu.is_state_changing(ev(0, "t", "s", "write_file", ok=False)) is False


def test_content_of_an_edit_is_what_it_writes_not_the_audit_layers_copy():
    app = ev(0, "t", "s", "append_to_file", {"path": DOC, "text": "added line", "content": "WHOLE DOC", "edit": {"x": "AUDIT"}})
    assert pu.action_content(app) == "added line"
    rep = ev(0, "t", "s", "replace_in_file", {"path": DOC, "find": "old text", "replace": "new text", "content": "WHOLE DOC", "edit": {"x": "AUDIT"}})
    assert pu.action_content(rep) == "new text"
    assert pu.action_content(ev(0, "t", "s", "write_file", {"path": DOC, "content": "full body"})) == "full body"


def test_content_of_messages_and_issues_reads_their_text_fields_not_their_addressing():
    msg = ev(0, "t", "s", "post_message", {"channel": "#ops-room", "sender": "alice", "text": "hello there"}, service="rocketchat")
    assert pu.action_content(msg) == "hello there"
    iss = ev(0, "t", "s", "update_issue", {"project_id": "p1", "issue_id": "i1", "patch": {"description": "new words", "state": "done"}}, service="plane")
    assert "new words" in pu.action_content(iss) and "p1" not in pu.action_content(iss)
    assert pu.action_content(ev(0, "t", "s", "mkdir", {"path": "/x/y", "recursive": True})) == ""


# ── timestamp order ──────────────────────────────────────────────────────────────────────────

def test_sort_events_is_by_timestamp_with_file_order_breaking_ties():
    rows = [{"ts": "2026-04-06T09:00:00Z", "n": 0}, {"ts": "2026-04-06T08:00:00Z", "n": 1}, {"ts": "2026-04-06T08:00:00Z", "n": 2}]
    assert [r["n"] for r in pu.sort_rows(rows)] == [1, 2, 0]


# ── carrying ─────────────────────────────────────────────────────────────────────────────────

def _one_write_log():
    # pos 0: B posts the pager value (current value, seed state); pos 1: A rewrites the pager (state 1);
    # pos 2: B posts the OLD value (no longer current); pos 3: B posts the NEW value
    states = {DOC: [st(0, BASE), st(1, NEW_PAGER, pos=1, session="A", ts=DAY1 + "T10:00:00Z")]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "page `ops-pager` for this"}, service="rocketchat"),
              ev(1, DAY1 + "T10:00:00Z", "A", "replace_in_file", {"path": DOC, "find": "`ops-pager`", "replace": "`ops-pager2`"}),
              ev(2, DAY1 + "T11:00:00Z", "B", "post_message", {"text": "page `ops-pager` again"}, service="rocketchat"),
              ev(3, DAY1 + "T12:00:00Z", "B", "post_message", {"text": "page `ops-pager2` now"}, service="rocketchat")]
    return events, states


def test_an_action_carries_the_value_current_at_its_timestamp():
    events, states = _one_write_log()
    res, slots = run(events, states)
    c = cell(res, slots, PAGER, DAY1)
    assert c["carrying"] == 2                 # pos 0 carries the old value while current; pos 3 the new one
    assert c["carrying_whole"] == 2
    assert c["sessions_carrying"] == 1        # both by session B
    # pos 2 holds the old value after it was replaced: not current, not carried


def test_the_edit_that_changes_the_slot_is_excluded_and_counted_apart():
    events, states = _one_write_log()
    res, slots = run(events, states)
    c = cell(res, slots, PAGER, DAY1)
    assert c["edits"] == 1
    assert c["units"] == 3                    # the three posts; the edit is not a unit


def test_the_session_that_last_wrote_the_slot_is_not_a_unit_for_it():
    events, states = _one_write_log()
    events.append(ev(4, DAY1 + "T13:00:00Z", "A", "post_message", {"text": "A repeats `ops-pager2`"}, service="rocketchat"))
    res, slots = run(events, states)
    c = cell(res, slots, PAGER, DAY1)
    assert c["same_session"] == 1
    assert c["carrying"] == 2 and c["units"] == 3


def test_the_seed_value_has_no_last_writer():
    states = {DOC: [st(0, BASE)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "A", "post_message", {"text": "use `ops-pager`"}, service="rocketchat")]
    res, slots = run(events, states)
    c = cell(res, slots, PAGER, DAY1)
    assert c["carrying"] == 1 and c["same_session"] == 0


def test_a_failed_action_is_not_a_unit():
    states = {DOC: [st(0, BASE)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "A", "post_message", {"text": "use `ops-pager`"}, service="rocketchat", ok=False)]
    res, slots = run(events, states)
    assert cell(res, slots, PAGER, DAY1)["units"] == 0


def test_a_message_with_no_text_is_a_unit_without_content():
    states = {DOC: [st(0, BASE)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "A", "mkdir", {"path": "/x"}), ev(1, DAY1 + "T09:30:00Z", "A", "post_message", {"text": "words"}, service="rocketchat")]
    res, slots = run(events, states)
    c = cell(res, slots, PAGER, DAY1)
    assert c["units"] == 2 and c["units_with_content"] == 1 and c["carrying"] == 0


# ── whole-document copies and edits of the slot ──────────────────────────────────────────────

def test_a_write_of_the_whole_document_is_a_copy_not_a_unit():
    states = {DOC: [st(0, BASE)], OTHER: [st(0, "# Other\n\n## Notes\n\nplain\n")]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "write_file", {"path": "/elsewhere/copy.md", "content": BASE})]
    res, slots = run(events, states)
    c = cell(res, slots, PAGER, DAY1)
    assert c["copies"] == 1 and c["units"] == 0 and c["carrying"] == 0


def test_a_whole_document_write_that_changes_another_slot_is_an_edit_of_that_slot_and_a_copy_for_the_rest():
    states = {DOC: [st(0, BASE), st(1, NEW_STEP, pos=0, session="B", ts=DAY1 + "T09:00:00Z")]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "write_file", {"path": DOC, "content": NEW_STEP})]
    res, slots = run(events, states)
    assert cell(res, slots, STEP1, DAY1)["edits"] == 1
    c = cell(res, slots, PAGER, DAY1)
    assert c["copies"] == 1 and c["edits"] == 0 and c["units"] == 0


def test_an_append_to_the_document_that_leaves_a_slot_unchanged_can_carry_it():
    appended = BASE + "\nSee also `ops-pager` for paging.\n"
    states = {DOC: [st(0, BASE), st(1, appended, pos=0, session="B", ts=DAY1 + "T09:00:00Z")]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "append_to_file", {"path": DOC, "text": "See also `ops-pager` for paging.", "content": appended})]
    res, slots = run(events, states)
    c = cell(res, slots, PAGER, DAY1)
    assert c["units"] == 1 and c["carrying"] == 1 and c["copies"] == 0 and c["edits"] == 0


# ── what counts as carrying ──────────────────────────────────────────────────────────────────

def test_a_distinctive_token_carries_but_is_not_a_whole_value():
    states = {DOC: [st(0, BASE)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "ping ops-pager please"}, service="rocketchat")]
    res, slots = run(events, states)
    c = cell(res, slots, PAGER, DAY1)
    assert c["carrying"] == 1 and c["carrying_whole"] == 0


def test_a_value_inside_a_longer_word_does_not_carry():
    states = {DOC: [st(0, NEW_PAGER)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "the ops-pager2x thing"}, service="rocketchat")]
    res, slots = run(events, states)
    assert cell(res, slots, PAGER, DAY1)["carrying"] == 0


def test_a_section_slot_carries_when_a_direct_line_of_it_does():
    states = {DOC: [st(0, BASE)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "do 2. Restart the worker"}, service="rocketchat")]
    res, slots = run(events, states)
    s = slot(slots, "> ## steps :: section")
    assert res["cells"][(s["slot_id"], DAY1)]["carrying"] == 1


def test_a_slot_absent_from_the_current_state_gives_no_unit():
    states = {DOC: [st(0, "# Runbook\n\n## Steps\n\n1. Stop the job\n"), st(1, BASE, pos=1, session="A", ts=DAY1 + "T10:00:00Z")]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "page `ops-pager`"}, service="rocketchat")]
    res, slots = run(events, states)
    assert cell(res, slots, PAGER, DAY1)["units"] == 0


# ── reads, days, totals ──────────────────────────────────────────────────────────────────────

def test_sessions_that_read_the_slots_document_that_day():
    states = {DOC: [st(0, BASE)], OTHER: [st(0, "# Other\n\n## Notes\n\nplain\n")]}
    events = [ev(0, DAY1 + "T08:00:00Z", "B", "read_file", {"path": DOC}), ev(1, DAY1 + "T08:10:00Z", "B", "read_bytes", {"path": DOC}),
              ev(2, DAY1 + "T08:20:00Z", "C", "read_file", {"path": OTHER}), ev(3, DAY2 + "T08:20:00Z", "D", "read_file", {"path": DOC}),
              ev(4, DAY1 + "T08:30:00Z", "E", "read_file", {"path": DOC}, ok=False)]
    res, slots = run(events, states)
    assert cell(res, slots, PAGER, DAY1)["sessions_reading"] == 1
    assert cell(res, slots, PAGER, DAY2)["sessions_reading"] == 1


def test_counts_by_day_stay_apart():
    states = {DOC: [st(0, BASE)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "`ops-pager`"}, service="rocketchat"),
              ev(1, DAY2 + "T09:00:00Z", "C", "post_message", {"text": "`ops-pager`"}, service="rocketchat"),
              ev(2, DAY2 + "T10:00:00Z", "D", "post_message", {"text": "`ops-pager`"}, service="rocketchat")]
    res, slots = run(events, states)
    assert cell(res, slots, PAGER, DAY1)["carrying"] == 1
    c2 = cell(res, slots, PAGER, DAY2)
    assert c2["carrying"] == 2 and c2["sessions_carrying"] == 2


def test_totals_by_document_and_kind_and_the_share_never_carried():
    states = {DOC: [st(0, BASE)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "`ops-pager`"}, service="rocketchat")]
    res, slots = run(events, states)
    tot = pu.totals(res, slots)
    assert tot["all"]["slots"] == len(slots) == 7
    carried = {s["locator"].split(" :: ", 1)[1] for s in slots if res["slot_totals"][s["slot_id"]]["carrying"] > 0}
    assert carried == {"# runbook > ## contacts :: label=pager#1", "# runbook > ## contacts :: section"}    # the item, and its section by the backticked token
    assert abs(tot["all"]["share_never_carried"] - 5 / 7) < 1e-12
    assert tot["by_kind"]["operational_value"]["slots"] == 1 and tot["by_kind"]["operational_value"]["slots_carried"] == 1
    assert tot["by_document"][DOC]["carrying"] == 2          # carrying actions summed over the document's slots
    assert tot["all"]["slots_carried_specific"] == 2 and abs(tot["all"]["share_never_carried_specific"] - 5 / 7) < 1e-12
    assert tot["all"]["slots_carried_specific_nocopy"] == 2 and abs(tot["all"]["share_never_carried_specific_nocopy"] - 5 / 7) < 1e-12


def test_a_carrying_action_is_counted_once_per_slot_even_when_it_carries_several_slots():
    states = {DOC: [st(0, BASE)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "`ops-pager` then restart the worker"}, service="rocketchat")]
    res, slots = run(events, states)
    assert res["actions"]["state_changing"] == 1 and res["actions"]["carrying_any_slot"] == 1
    assert res["actions"]["slots_carried_per_action"] == {3: 1}      # the pager item, its section, and step 2


def test_carrying_sessions_that_had_read_the_document_before_the_action():
    states = {DOC: [st(0, BASE)]}
    events = [ev(0, DAY1 + "T08:00:00Z", "B", "read_file", {"path": DOC}),
              ev(1, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "`ops-pager`"}, service="rocketchat"),
              ev(2, DAY1 + "T09:10:00Z", "C", "post_message", {"text": "`ops-pager`"}, service="rocketchat"),
              ev(3, DAY1 + "T09:20:00Z", "D", "post_message", {"text": "`ops-pager`"}, service="rocketchat"),
              ev(4, DAY1 + "T09:30:00Z", "D", "read_file", {"path": DOC})]
    res, slots = run(events, states)
    c = cell(res, slots, PAGER, DAY1)
    assert c["sessions_carrying"] == 3 and c["sessions_carrying_after_reading"] == 1      # D read only after carrying


# ── specific matches: a date, a bare number or a short token is a weak carry ─────────────────

def test_needle_class_separates_specific_values_from_dates_numbers_and_short_tokens():
    assert pu.needle_class("2026-04-01") == "date"
    assert pu.needle_class("2026-04-01t10:00:00z") == "date"
    assert pu.needle_class("3.2") == "numeric"
    assert pu.needle_class("12:30") == "numeric"
    assert pu.needle_class("v2") == "short"
    assert pu.needle_class("ops-pager") == "specific"
    assert pu.needle_class("#oncall-room") == "specific"
    assert pu.needle_class("/shared/ops/runbook.md") == "specific"


def test_a_shared_date_carries_but_is_not_a_specific_carry():
    doc = BASE + "\n## Review\n\n- Reviewed: 2026-04-01\n"
    states = {DOC: [st(0, doc)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "see the note of 2026-04-01"}, service="rocketchat"),
              ev(1, DAY1 + "T09:10:00Z", "C", "post_message", {"text": "page `ops-pager`"}, service="rocketchat")]
    res, slots = run(events, states)
    d = cell(res, slots, ":: label=reviewed#1", DAY1)
    assert d["carrying"] == 1 and d["carrying_specific"] == 0
    p = cell(res, slots, PAGER, DAY1)
    assert p["carrying"] == 1 and p["carrying_specific"] == 1


def test_actions_are_also_counted_by_action_name():
    states = {DOC: [st(0, BASE)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "`ops-pager`"}, service="rocketchat"),
              ev(1, DAY1 + "T09:10:00Z", "C", "post_message", {"text": "nothing here"}, service="rocketchat"),
              ev(2, DAY1 + "T09:20:00Z", "C", "mkdir", {"path": "/x"})]
    res, slots = run(events, states)
    ba = res["actions"]["by_action"]
    assert ba["post_message"] == {"state_changing": 2, "with_content": 2, "carrying_any_slot": 1, "carrying_specific_any_slot": 1, "carrying_specific_nocopy_any_slot": 1}
    assert ba["mkdir"] == {"state_changing": 1, "with_content": 0, "carrying_any_slot": 0, "carrying_specific_any_slot": 0, "carrying_specific_nocopy_any_slot": 0}


def test_an_action_that_carries_only_a_date_is_not_counted_as_a_specific_carrier():
    doc = BASE + "\n## Review\n\n- Reviewed: 2026-04-01\n"
    states = {DOC: [st(0, doc)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "see the note of 2026-04-01"}, service="rocketchat")]
    res, slots = run(events, states)
    assert res["actions"]["carrying_any_slot"] >= 1 and res["actions"]["carrying_specific_any_slot"] == 0


# ── v1: near-copies (an action whose content holds half or more of a document's current lines) ──

def test_line_share_is_the_share_of_current_non_empty_lines_the_content_holds():
    assert pu.line_share(BASE, "## Contacts\n- Pager: `ops-pager`") == (2, 7)
    assert pu.line_share(BASE, "nothing") == (0, 7)
    assert pu.line_share("a line one\n\nb line two\n", "the a line one only") == (1, 2)      # blank lines are not lines
    assert pu.line_share("   \n\n", "x") == (0, 0)


def test_half_or_more_is_a_near_copy():
    assert pu.is_near_copy(1, 2) is True
    assert pu.is_near_copy(4, 7) is True
    assert pu.is_near_copy(3, 7) is False
    assert pu.is_near_copy(0, 0) is False


PART = "# Runbook\n## Contacts\n- Pager: `ops-pager`\n- Owner: the platform team"       # 4 of the 7 non-empty lines


def test_an_action_holding_half_the_documents_lines_is_a_near_copy_and_leaves_the_third_count():
    states = {DOC: [st(0, BASE)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "write_file", {"path": "/elsewhere/part.md", "content": PART}),
              ev(1, DAY1 + "T09:10:00Z", "C", "post_message", {"text": "page `ops-pager` please"}, service="rocketchat")]
    res, slots = run(events, states)
    c = cell(res, slots, PAGER, DAY1)
    assert c["carrying_specific"] == 2 and c["carrying_specific_nocopy"] == 1       # the partial copy is left out, the message stays
    a = res["actions"]
    assert a["carrying_specific_any_slot"] == 2 and a["carrying_specific_nocopy_any_slot"] == 1


def test_a_partial_copy_that_is_under_half_stays_in_the_third_count():
    states = {DOC: [st(0, BASE)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "write_file", {"path": "/elsewhere/part.md", "content": "## Contacts\n- Pager: `ops-pager`\n- Owner: the platform team"})]
    res, slots = run(events, states)
    c = cell(res, slots, PAGER, DAY1)
    assert c["carrying_specific"] == 1 and c["carrying_specific_nocopy"] == 1         # 3 of 7 lines


def test_the_near_copy_test_reads_the_document_the_slot_belongs_to():
    other = "# Other\n\n## Notes\n\n- Contact: `ops-desk`\n- Extra: something here\n"
    states = {DOC: [st(0, BASE)], OTHER: [st(0, other)]}
    # the content holds three of the OTHER document's four lines and none of DOC's
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "# Other\n## Notes\n- Contact: `ops-desk`\npage `ops-pager`"}, service="rocketchat")]
    res, slots = run(events, states)
    assert cell(res, slots, PAGER, DAY1)["carrying_specific_nocopy"] == 1            # 0 of 7 lines of DOC
    assert cell(res, slots, ":: label=contact#1", DAY1)["carrying_specific"] == 1
    assert cell(res, slots, ":: label=contact#1", DAY1)["carrying_specific_nocopy"] == 0   # 3 of 4 lines of OTHER


def test_near_copies_are_characterised_by_action_and_target():
    states = {DOC: [st(0, BASE)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "write_file", {"path": "/elsewhere/part.md", "content": PART}),
              ev(1, DAY1 + "T09:10:00Z", "C", "append_to_file", {"path": DOC, "text": PART, "content": BASE + PART}),
              ev(2, DAY1 + "T09:20:00Z", "D", "post_message", {"text": "page `ops-pager`"}, service="rocketchat")]
    res, slots = run(events, states)
    ch = res["characterisation"]
    assert ch["carrying_actions"] == 3
    assert ch["near_copy_by_action_target"] == {"write_file|other_path": 1, "append_to_file|same_document": 1}
    assert ch["by_action"]["post_message"] == {"carrying": 1, "many_slot": 0, "many_slot_weak_only": 0, "many_slot_with_specific": 0, "near_copy": 0}
    assert ch["by_action"]["write_file"]["near_copy"] == 1
    assert sum(ch["share_bins"].values()) == 3


def test_many_slot_actions_are_those_carrying_ten_or_more_slots():
    lines = "\n".join(f"- Key{i}: `val-{i}-abc`" for i in range(12))
    doc = "# Big\n\n## Keys\n\n" + lines + "\n"
    states = {DOC: [st(0, doc)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "\n".join(f"`val-{i}-abc`" for i in range(11))}, service="rocketchat")]
    res, slots = run(events, states)
    ch = res["characterisation"]
    assert ch["many_slot_actions"] == 1 and ch["by_action"]["post_message"]["many_slot"] == 1


def test_slots_carried_only_by_a_near_copy_are_never_carried_under_the_third_count():
    states = {DOC: [st(0, BASE)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "write_file", {"path": "/elsewhere/part.md", "content": PART})]
    res, slots = run(events, states)
    tot = pu.totals(res, slots)["all"]
    assert tot["slots_carried_specific"] > 0 and tot["slots_carried_specific_nocopy"] == 0
    assert tot["share_never_carried_specific_nocopy"] == 1.0


def test_many_slot_actions_that_rest_only_on_a_shared_date_are_told_apart_from_specific_ones():
    lines = "\n".join(f"- Dated{i}: 2026-04-06" for i in range(12))
    doc = "# Big\n\n## Dates\n\n" + lines + "\n"
    states = {DOC: [st(0, doc)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "nothing changed since 2026-04-06"}, service="rocketchat")]
    res, slots = run(events, states)
    ch = res["characterisation"]
    assert ch["many_slot_actions"] == 1 and ch["many_slot_weak_only"] == 1 and ch["many_slot_with_specific"] == 0
    assert ch["by_action"]["post_message"]["many_slot_weak_only"] == 1
    assert res["actions"]["carrying_specific_any_slot"] == 0


def test_a_many_slot_action_with_a_specific_carry_is_counted_as_such():
    lines = "\n".join(f"- Key{i}: `val-{i}-abc`" for i in range(12))
    doc = "# Big\n\n## Keys\n\n" + lines + "\n"
    states = {DOC: [st(0, doc)]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "\n".join(f"`val-{i}-abc`" for i in range(11))}, service="rocketchat")]
    res, slots = run(events, states)
    ch = res["characterisation"]
    assert ch["many_slot_with_specific"] == 1 and ch["many_slot_weak_only"] == 0


def test_many_slot_actions_are_told_apart_by_whether_one_shared_literal_carries_most_slots():
    dated = "\n".join(f"- Dated{i}: 2026-04-06" for i in range(12))
    states = {DOC: [st(0, "# Big\n\n## Dates\n\n" + dated + "\n")]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "nothing changed since 2026-04-06"}, service="rocketchat")]
    res, _ = run(events, states)
    assert res["characterisation"]["many_slot_one_literal"] == 1 and res["characterisation"]["many_slot_many_literals"] == 0
    keys = "\n".join(f"- Key{i}: `val-{i}-abc`" for i in range(12))
    states = {DOC: [st(0, "# Big\n\n## Keys\n\n" + keys + "\n")]}
    events = [ev(0, DAY1 + "T09:00:00Z", "B", "post_message", {"text": "\n".join(f"`val-{i}-abc`" for i in range(11))}, service="rocketchat")]
    res, _ = run(events, states)
    assert res["characterisation"]["many_slot_one_literal"] == 0 and res["characterisation"]["many_slot_many_literals"] == 1


def test_needles_come_in_a_fixed_order_so_a_run_does_not_depend_on_the_hash_seed():
    whole, toks = pu._needles(["`zeta-9` and `alpha-1` and `mid_2` plus `beta-3`"], "")
    assert [n for n, _ in toks] == sorted(n for n, _ in toks)
