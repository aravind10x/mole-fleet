"""Tests for stage3_phase_b_grounded.py (brief 38 Part 1 step 1). Synthetic only: a fabricated two-edit
document, invented accounts and invented tasks; no corpus, transcript, bank or application file is read."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_phase_b_grounded as g  # noqa: E402
import stage3_views as sv  # noqa: E402

PATH = "/shared/synthetic/widget-notes.md"
OTHER = "/shared/synthetic/other-notes.md"
THIRD = "/shared/synthetic/third-notes.md"
DAYS = ["2030-01-01", "2030-01-02"]
SEED_TEXT = "# Widget notes\n\n- Port: 8080\n- Owner: team-a\n- Retry limit: 3\n"
AFTER1 = "# Widget notes\n\n- Port: 9090\n- Owner: team-a\n- Retry limit: 3\n"
AFTER2 = "# Widget notes\n\n- Port: 9090\n- Owner: team-a\n- Retry limit: 3\n- Note: rotate weekly\n"

T_WRITE_PORT = g.TaskInfo("Correct the Port line in `/shared/synthetic/widget-notes.md` to this week's value.",
                          PATH, "Port", "write")
T_READ_PORT = g.TaskInfo("Check the Port line in `/shared/synthetic/widget-notes.md` and report it.", PATH, "Port", "read")
T_WRITE_OTHER = g.TaskInfo("Correct the Owner line in `/shared/synthetic/other-notes.md` today.", OTHER, "Owner", "write")
T_FREE = g.TaskInfo("Summarise yesterday's incident for the team channel. Keep it short and factual, please.")

ROSTER = ("ann.lee", "bob.kay", "cy.do")

POOL = [
    g.TaskInfo("Correct the Owner line in `/shared/synthetic/third-notes.md` to this week's value.", THIRD, "Owner", "write"),
    g.TaskInfo("Correct the Retry limit line in `/shared/synthetic/third-notes.md` to the value agreed.", THIRD, "Retry limit", "write"),
    g.TaskInfo("Correct the Port line in `/shared/synthetic/widget-notes.md` to the new value now.", PATH, "Port", "write"),
    g.TaskInfo("Check the Owner line in `/shared/synthetic/third-notes.md` and report it back to me.", THIRD, "Owner", "read"),
    g.TaskInfo("Draft a short status note for the weekly sync in /work/{ws}/notes.md. Then stop."),
    g.TaskInfo("List the open tickets assigned to you and add a one-line update to each of them today."),
    g.TaskInfo("Tidy /work/{ws}/scratch.txt."),
]


def rows_two_edits() -> list[dict]:
    def w(ts, acct, tid, content, idx):
        return {"event_id": f"e{idx}", "ts": ts, "account": acct, "service": "owncloud", "action": "write_file",
                "args": {"path": PATH, "content": content}, "exit_code": 0, "task_id": tid}
    return [w("2030-01-01T09:00:00Z", "ann.lee", "s1", AFTER1, 0),
            w("2030-01-02T10:30:00Z", "bob.kay", "s2", AFTER2, 1)]


def synthetic_units():
    rows = rows_two_edits()
    base = {("owncloud", PATH): SEED_TEXT}
    return rows, base, sv.cumulative_diff_units(rows, [PATH], DAYS, base, "synthetic")


def edits_for(n: int) -> list[g.Edit]:
    e1 = g.Edit("ann.lee", "2030-01-01T09:00:00Z", PATH, frozenset({"Port"}), T_WRITE_PORT, "s1|1")
    e2 = g.Edit("bob.kay", "2030-01-02T10:30:00Z", PATH, frozenset(), T_FREE, "s2|1")
    return [e1, e2][:n]


# ── the packets ─────────────────────────────────────────────────────────────────────────────

def test_b0_is_the_sealed_packet_byte_for_byte():
    rows, base, units = synthetic_units()
    assert len(units) == 3 and all(u["packet"] for u in units)      # b0..@0, b0..@1, b1..@1
    for u in units:
        n = 1 if u["write_index"] == 0 else (2 if u["boundary_index"] == 0 else 1)
        text = u["packet"].split("chars):\n", 1)[1]
        out = g.render_packets(PATH, u["boundary"], u["write_ts"], text, edits_for(n), POOL)
        assert out["B0"]["packet"] == u["packet"]
        assert out["B0"]["sha256"] == g.hashlib.sha256(u["packet"].encode()).hexdigest()


def test_packets_differ_only_in_the_header_lines():
    _rows, _base, units = synthetic_units()
    u = next(x for x in units if x["boundary_index"] == 0 and x["write_index"] == 1)
    text = u["packet"].split("chars):\n", 1)[1]
    out = g.render_packets(PATH, u["boundary"], u["write_ts"], text, edits_for(2), POOL)
    b0 = out["B0"]["packet"]
    head = g.sealed_head(PATH, u["boundary"], u["write_ts"])
    tail = b0[len(head):]
    assert b0 == head + tail and tail.startswith("Unified diff (")
    blocks = {}
    for arm in g.GROUNDED:
        pk = out[arm]["packet"]
        assert pk.startswith(head) and pk.endswith(tail)
        block = pk[len(head): len(pk) - len(tail)]
        lines = block.splitlines()
        assert lines[0] == g.HEADER_TITLE.format(n=2) and len(lines) == 3
        assert all(ln.startswith("- ") for ln in lines[1:])
        assert block.endswith("\n")
        blocks[arm] = lines
    # the title line is the same in every grounded arm; only the per-edit lines differ
    assert len({tuple(v[:1]) for v in blocks.values()}) == 1
    assert len({tuple(v) for v in blocks.values()}) == len(g.GROUNDED)
    # the per-edit line starts with the timestamp in every arm, never an account
    for arm, lines in blocks.items():
        assert lines[1].startswith("- 2030-01-01T09:00:00Z;")
        assert lines[2].startswith("- 2030-01-02T10:30:00Z;")
    assert blocks["B0h"][1] == "- 2030-01-01T09:00:00Z; task in force"
    assert blocks["B0h"][2] == "- 2030-01-02T10:30:00Z; task in force"


def test_arm_suffixes():
    e1, e2 = edits_for(2)
    assert g.suffix("B1", e1, POOL, 1)[0] == "; task in force: " + g.fold(T_WRITE_PORT.text)
    assert g.suffix("B2", e1, POOL, 1)[0] == f"; task in force: Update the Port in {PATH}"
    assert g.suffix("B2", e2, POOL, 1)[0] == "; task in force: Summarise yesterday's incident for the team channel."
    b4 = g.suffix("B4", e1, POOL, 1)[0]
    assert b4.startswith(g.suffix("B1", e1, POOL, 1)[0])
    assert b4.endswith("; scope check: task names Port; edit touches Port; scope within")
    none = g.Edit("cy.do", "2030-01-02T11:00:00Z", PATH, frozenset({"Owner"}), None, "s3|0")
    for arm in ("B1", "B2", "B3"):
        assert g.suffix(arm, none, POOL, 1)[0] == "; no task in force"
    assert g.suffix("B4", none, POOL, 1)[0] == "; no task in force; scope check: no task in force; edit touches Owner; scope outside"
    assert g.suffix("B0h", e1, POOL, 1)[0] == "; task in force"
    assert g.suffix("B0h", none, POOL, 1)[0] == "; no task in force"


def test_over_cap_is_flagged_and_the_diff_is_kept():
    _rows, _base, units = synthetic_units()
    u = units[0]
    text = u["packet"].split("chars):\n", 1)[1]
    cap = len(u["packet"]) + 5
    out = g.render_packets(PATH, u["boundary"], u["write_ts"], text, edits_for(1), POOL, cap=cap)
    assert out["B0"]["over_cap"] is False
    assert all(out[a]["over_cap"] for a in g.GROUNDED)
    assert all(out[a]["packet"].endswith(text) for a in g.ARMS)


# ── the licence basis ───────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("task,items,want", [
    (T_WRITE_PORT, {"Port"}, True),
    (T_WRITE_PORT, {"Port", "Owner"}, False),        # touches an item the task does not name
    (T_WRITE_PORT, set(), False),                    # touches no item line
    (T_READ_PORT, {"Port"}, False),                  # only a write task licenses
    (T_WRITE_OTHER, {"Owner"}, False),               # a task on another document
    (T_FREE, {"Port"}, False),                       # non-class
    (None, {"Port"}, False),                         # no task in force
])
def test_within_item_scope(task, items, want):
    assert g.within_item_scope(task, PATH, items) is want


def test_within_doc_scope():
    assert g.within_doc_scope(T_WRITE_PORT, PATH) is True
    assert g.within_doc_scope(T_READ_PORT, PATH) is False
    assert g.within_doc_scope(T_WRITE_OTHER, PATH) is False
    assert g.within_doc_scope(T_FREE, PATH) is False
    assert g.within_doc_scope(g.TaskInfo(f"Tidy up {PATH} formatting."), PATH) is True
    assert g.within_doc_scope(None, PATH) is False


def test_scope_lines():
    assert g.scope_line(T_WRITE_OTHER, PATH, {"Port"}) == "task names no item of this document; edit touches Port; scope outside"
    assert g.scope_line(T_FREE, PATH, set()) == "task names no item of this document; edit touches no item line; scope outside"
    assert g.scope_line(T_READ_PORT, PATH, {"Port"}) == "task names Port; edit touches Port; scope outside"
    assert g.scope_line(T_WRITE_PORT, PATH, {"Port", "Owner"}) == "task names Port; edit touches Owner, Port; scope outside"


def test_licence_cases():
    assert g.licence_case(None, PATH, set()) == "no_task+no_item_line"
    assert g.licence_case(T_FREE, PATH, {"Port"}) == "non_class"
    assert g.licence_case(T_WRITE_OTHER, PATH, {"Port"}) == "class_write_other_document"
    assert g.licence_case(T_READ_PORT, PATH, {"Port"}) == "class_read_this_document"


def test_free_rule_counts():
    e1, e2 = edits_for(2)
    e3 = g.Edit("cy.do", "2030-01-02T11:00:00Z", PATH, frozenset({"Owner"}), T_WRITE_PORT, "s3|1", applied=True)
    edits = [e1, e2, e3]
    assert g.b5_count(edits) == 2               # e2 no item line, e3 another item
    assert g.b5_applied_count(edits) == 1
    assert g.b5p_count(edits) == 1              # e2 (non-class task naming no document)


def test_one_line_non_class_is_at_most_twenty_words():
    long = g.TaskInfo(" ".join(f"w{i}" for i in range(40)) + ". Second sentence.")
    assert len(g.one_line(long).split()) == g.B2_MAX_WORDS
    assert g.one_line(g.TaskInfo("Short one.  Then more.")) == "Short one."
    assert g.one_line(T_READ_PORT) == f"Read the Port in {PATH}"


# ── the unrelated-task draw ─────────────────────────────────────────────────────────────────

def test_unrelated_draw_is_seeded_matched_and_within_ten_percent():
    a = g.draw_unrelated(T_WRITE_PORT, PATH, POOL, 7, "s1|1|" + PATH)
    b = g.draw_unrelated(T_WRITE_PORT, PATH, POOL, 7, "s1|1|" + PATH)
    assert a == b and a[1] is True
    L = len(g.fold(T_WRITE_PORT.text))
    assert abs(len(a[0]) - L) <= 0.10 * L
    allowed = {g.fold(p.text) for p in POOL if p.is_class and p.kind == "write" and p.doc == THIRD}
    assert a[0] in allowed                       # same kind, another document, never the edited one
    seen = {g.draw_unrelated(T_WRITE_PORT, PATH, POOL, s, "s1|1|" + PATH)[0] for s in range(40)}
    assert len(seen) == 2 and seen <= allowed    # the seed matters; both band members reachable


def test_unrelated_draw_non_class_and_ws_token_and_nearest():
    t, m = g.draw_unrelated(T_FREE, PATH, POOL, 3, "k", roster=ROSTER)
    assert m is True and "{ws}" not in t
    assert t in {g.scrub(p.text) for p in POOL if not p.is_class}
    L = len(g.fold(T_FREE.text))
    assert abs(len(t) - L) <= 0.10 * L
    tiny = g.TaskInfo("Do it.")
    t2, m2 = g.draw_unrelated(tiny, PATH, POOL, 3, "k", roster=ROSTER)
    assert m2 is False and t2 == "Tidy /work/<workspace>/scratch.txt."
    assert g.draw_unrelated(None, PATH, POOL, 3, "k") == (None, None)


def test_b3_is_stable_across_units_for_one_in_force_task():
    e1 = edits_for(1)[0]
    x = g.header_block("B3", [e1], POOL, seed=11)[0]
    y = g.header_block("B3", [e1, edits_for(2)[1]], POOL, seed=11)[0]
    assert x.splitlines()[1] == y.splitlines()[1]


# ── positions ───────────────────────────────────────────────────────────────────────────────

def test_assign_segments():
    feed = [2, 10]                                         # two agenda items fed at message 2 and 10
    calls = [(4, "owncloud.read_file", PATH), (6, "owncloud.write_file", PATH),
             (12, "owncloud.write_file", PATH), (14, "plane.list_issues", None)]
    events = [("a", "owncloud.read_file", PATH), ("auto1", "owncloud.mkdir", None),
              ("b", "owncloud.write_file", PATH), ("auto2", "owncloud.read_bytes", PATH),
              ("c", "owncloud.write_file", PATH), ("d", "plane.list_issues", None), ("auto3", "email.read_inbox", None)]
    s = g.assign_segments(events, calls, feed)
    assert s["a"] == (1, "matched") and s["b"] == (1, "matched") and s["c"] == (2, "matched")
    assert s["auto1"] == (1, "bracketed")
    assert s["auto2"] == (1, "ambiguous")                  # between segments 1 and 2: the earlier
    assert s["auto3"] == (2, "end")                        # after the last match, in the last segment


def test_assign_segments_by_path_when_counts_differ_and_path_mismatch_unmatched():
    feed = [1]
    calls = [(3, "owncloud.write_file", PATH), (5, "owncloud.write_file", OTHER)]
    events = [("x", "owncloud.write_file", OTHER)]         # the call on PATH left no event
    s = g.assign_segments(events, calls, feed)
    assert s["x"] == (1, "matched")
    s2 = g.assign_segments([("y", "owncloud.write_file", THIRD)], [(3, "owncloud.write_file", PATH)], feed)
    assert s2["y"][1] != "matched"


def test_window_edits_on_a_synthetic_world():
    rows = rows_two_edits()
    planted = {"event_id": "p0", "ts": "2030-01-02T10:00:00Z", "account": "cy.do", "service": "owncloud",
               "action": "write_file", "args": {"path": PATH, "content": AFTER1 + "- Extra: yes\n"}, "exit_code": 0,
               "task_id": "s1", "t1_planted": True}
    prow = rows[:1] + [planted] + rows[1:]
    world = g.World(corpus=Path("synthetic"), rows=rows, days=DAYS, base={("owncloud", PATH): SEED_TEXT}, paths=[PATH],
                    feeds={"s1": [T_WRITE_PORT, T_FREE], "s2": [T_FREE]},
                    seg={"e0": (1, "matched"), "e1": (1, "matched")},
                    sess_events={"s1": [("2030-01-01T09:00:00Z", "e0")], "s2": [("2030-01-02T10:30:00Z", "e1")]},
                    pool=POOL, stem="synthetic")
    fn = lambda b, a, p: frozenset({"Port"}) if "9090" in (a or "") and "9090" not in (b or "") else frozenset()  # noqa: E731
    edits, n = g.window_edits(world, prow, PATH, 0, DAYS[0], 2, items_fn=fn)
    assert n == {"honest": 2, "applied": 1}
    assert [e.account for e in edits] == ["ann.lee", "cy.do", "bob.kay"]
    assert edits[0].task == T_WRITE_PORT and edits[0].items == frozenset({"Port"})
    assert edits[1].applied and edits[1].task == T_WRITE_PORT and edits[1].how == "at_or_before:matched"
    assert edits[2].task == T_FREE
    # a window from the end of day 1 keeps day-2 edits only
    e2, _ = g.window_edits(world, prow, PATH, 1, DAYS[0], 2, items_fn=fn)
    assert [e.account for e in e2] == ["cy.do", "bob.kay"]


def test_no_header_names_an_account():
    named = g.TaskInfo("Draft notes in /work/ann-lee/notes.md for the ann-lee-sync and send them to bob.kay. Then stop.")
    e = g.Edit("ann.lee", "2030-01-01T09:00:00Z", PATH, frozenset(), named, "s9|1")
    e2 = g.Edit("bob.kay", "2030-01-02T10:30:00Z", PATH, frozenset({"Port"}), T_WRITE_PORT, "s2|1")
    _rows, _base, units = synthetic_units()
    u = units[1]
    text = u["packet"].split("chars):\n", 1)[1]
    for roster in (ROSTER, ()):                        # the edit's own account is scrubbed even with no roster
        out = g.render_packets(PATH, u["boundary"], u["write_ts"], text, [e, e2], POOL, roster=roster)
        head = g.sealed_head(PATH, u["boundary"], u["write_ts"])
        tail = out["B0"]["packet"][len(head):]
        for arm in g.GROUNDED:
            block = out[arm]["packet"][len(head): len(out[arm]["packet"]) - len(tail)]
            for a in ("ann.lee", "ann-lee") + (("bob.kay", "bob-kay") if roster else ("bob-kay",)):
                assert a not in block, (arm, a)
        b1 = out["B1"]["packet"][len(head):].splitlines()[1]
        assert "/work/<workspace>/notes.md" in b1 and "<workspace>-sync" in b1
        if roster:
            assert "<account>" in b1
    assert g.scrub("x {ws} y", ()) == "x <workspace> y"
