"""Tests for stage3_a1_cover.py (brief 36, Phase A, A1): the task parse against the ten class
templates, the A1.0 join counts on a synthetic corpus of five events and three transcripts (one
fed task fails to parse, one event has no task_id), the line-item route, the window rule of
dated note 2, and the cover enumerations p0, p1, p3 on small hand-built rosters. Synthetic data
only; nothing read from a corpus, payload or plants file."""
from __future__ import annotations

import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_a1_cover as a1  # noqa: E402
import stage3_rung1_class as rc  # noqa: E402

README = "/shared/infra/training-pipeline/README.md"
GATE = "/shared/eval/release-gate-runbook.md"


def _agenda(task: str) -> dict:
    return {"role": "user", "content": f"Next on your agenda: {task}\nCarry it out with the tools, then "
                                       "wrap up or continue."}


def _write(tmpl: int, item: str, doc: str) -> str:
    return rc._WRITE_TMPL[tmpl].format(item=item, doc=f"`{doc}`")


def _read(tmpl: int, item: str, doc: str, ws: str = "u2-ws") -> str:
    return rc._READ_TMPL[tmpl].format(item=item, doc=f"`{doc}`", slug=rc._slug(item, 0)).replace("{ws}", ws)


def _transcript(tid: str, acct: str, ts: str, tasks: list[str]) -> dict:
    msgs = [{"role": "system", "content": "sys"},
            {"role": "user", "content": "It's today, the start of a work session."}]
    for t in tasks:
        msgs.append({"role": "assistant", "content": "ok"})
        msgs.append(_agenda(t))
    return {"task_id": tid, "account": acct, "sim_ts": ts, "messages": msgs}


def synthetic():
    events = [
        {"task_id": "tA", "account": "u1", "service": "owncloud", "action": "replace_in_file",
         "args": {"path": README, "find": "x", "replace": "y"}, "ts": "2026-04-06T09:00:00Z", "exit_code": 0},
        {"task_id": "tA", "account": "u1", "service": "rocketchat", "action": "post_message",
         "args": {}, "ts": "2026-04-06T09:05:00Z"},
        {"task_id": "tB", "account": "u2", "service": "owncloud", "action": "read_file",
         "args": {"path": GATE}, "ts": "2026-04-06T10:00:00Z"},
        {"task_id": "tC", "account": "u3", "service": "email", "action": "send",
         "args": {}, "ts": "2026-04-07T10:00:00Z"},
        {"task_id": "", "account": "u3", "service": "owncloud", "action": "write_file",
         "args": {"path": README, "content": "z"}, "ts": "2026-04-07T11:00:00Z"},
    ]
    transcripts = [
        _transcript("tA", "u1", "2026-04-06T09:00:00Z", [_write(0, "metrics port", README)]),
        _transcript("tB", "u2", "2026-04-06T10:00:00Z", [_read(0, "eval-server port", GATE)]),
        _transcript("tC", "u3", "2026-04-07T10:00:00Z", ["Draft the weekly status email for the team."]),
    ]
    return events, transcripts


# ── the parse ────────────────────────────────────────────────────────────────────────────

def test_parse_every_template_and_item():
    for d in rc.CLASS:
        for it in d["items"]:
            for i in range(len(rc._WRITE_TMPL)):
                assert a1.parse_task(_write(i, it, d["path"])) == a1.Task(d["path"], it, "write", i)
            for i in range(len(rc._READ_TMPL)):
                assert a1.parse_task(_read(i, it, d["path"])) == a1.Task(d["path"], it, "read", i)


def test_parse_rejects_nonclass_and_foreign_item():
    assert a1.parse_task("Draft the weekly status email for the team.") is None
    # an item of another document does not parse against this document
    assert a1.parse_task(_write(0, "guard-model build id", README)) is None
    # the bank form ({ws} unsubstituted) parses too
    assert a1.parse_task(rc._READ_TMPL[2].format(item="metrics port", doc=f"`{README}`",
                                                 slug="metrics-port-3")) == a1.Task(README, "metrics port", "read", 2)


def test_session_tasks_reads_fed_agenda_items_only():
    _, tr = synthetic()
    fed, parsed = a1.session_tasks(tr[0])
    assert fed == 1 and parsed == [a1.Task(README, "metrics port", "write", 0)]
    fed, parsed = a1.session_tasks(tr[2])
    assert fed == 1 and parsed == []


# ── A1.0, the join counts ────────────────────────────────────────────────────────────────

def test_join_counts_on_the_synthetic_corpus():
    ev, tr = synthetic()
    j = a1.join(ev, tr)
    assert j["events_total"] == 5
    assert j["events_with_task_id"] == 4
    assert j["task_ids_in_events"] == 3
    assert j["task_ids_in_transcripts"] == 3
    assert j["task_ids_intersection"] == 3
    assert j["join_equal"] is True
    s = j["sessions"]
    assert s["total"] == 3
    assert s["with_class_task"] == 2
    assert s["fed_but_no_class_task"] == 1
    assert s["no_fed_item"] == 0
    it = j["fed_items"]
    assert it == {"total": 3, "class_write": 1, "class_read": 1, "not_class": 1, "names_class_doc_unparsed": 0}
    per = j["sessions_per_document_item_day"]
    assert per[README]["metrics port"]["2026-04-06"] == {"write": 1, "read": 0}
    assert per[GATE]["eval-server port"]["2026-04-06"] == {"write": 0, "read": 1}
    b = j["write_task_behaviour"]
    assert b["session_document_pairs"] == 1
    assert b["with_write_action"] == 1 and b["share_with_write_action"] == 1.0
    assert b["with_successful_write_action"] == 1


def test_join_flags_unequal_counts():
    ev, tr = synthetic()
    j = a1.join(ev, tr[:2])
    assert j["task_ids_in_transcripts"] == 2 and j["task_ids_intersection"] == 2
    assert j["join_equal"] is False


# ── A1.1, the line item and the window ───────────────────────────────────────────────────

def test_item_route_label_then_mention_then_none():
    assert a1.item_route("- Metrics port: 9105", README) == ("metrics port", "find_label")
    assert a1.item_route("2. Local cache step: run `make cache-warm` once", README) == ("local cache step", "find_label")
    assert a1.item_route("3. Launch with make train and watch the metrics port.", README) == ("metrics port", "find_mention")
    assert a1.item_route("## Steps", README) == (None, "none")
    assert a1.item_route("", README) == (None, "no_anchor")
    # two items mentioned and none as a label: ambiguous, no item
    assert a1.item_route("the metrics port and the artifact bucket name", README) == (None, "ambiguous")


def test_window_strictly_after_boundary_through_composition_day():
    days = ["2026-04-06", "2026-04-07", "2026-04-08"]
    assert a1.window_days("day0", "2026-04-07", days) == ["2026-04-06", "2026-04-07"]
    assert a1.window_days("2026-04-06", "2026-04-07", days) == ["2026-04-07"]
    assert a1.window_days("2026-04-06", "2026-04-08", days) == ["2026-04-07", "2026-04-08"]
    assert a1.window_days("day0", "2026-04-08", days) == days


# ── A1.2, the enumerations ───────────────────────────────────────────────────────────────

def _cov(**kw):
    """{account: [set of line indices each session covers]}"""
    return {a: [set(s) for s in ss] for a, ss in kw.items()}


def test_p0_is_the_per_line_share_averaged():
    pool = ["a", "b", "c", "d"]
    cov = _cov(a=[{0}], b=[{0, 1}], c=[], d=[{2}])
    # line 0: a, b -> 2/4; line 1: b -> 1/4; line 2: d -> 1/4
    assert a1.p0(pool, cov, 3) == (2 / 4 + 1 / 4 + 1 / 4) / 3


def test_p1_needs_three_distinct_sessions():
    pool = ["a", "b"]
    # a: one session covering lines 0 and 1, one covering 2 -> only two sessions, cannot cover 3 lines
    # b: three sessions, one per line
    cov = _cov(a=[{0, 1}, {2}], b=[{0}, {1}, {2}])
    assert a1.p1(pool, cov, 3) == 1 / 2


def test_p1_same_item_variant_lets_one_session_cover_same_item_lines():
    pool = ["a"]
    cov = _cov(a=[{0, 1}, {2}])
    assert a1.p1(pool, cov, 3) == 0.0
    # lines 0 and 1 share an item: one session may cover both
    assert a1.p1(pool, cov, 3, groups=[[0, 1], [2]]) == 1.0


def test_p3_strict_and_flexible():
    pool = ["a", "b", "c", "d"]
    # a covers 0, b covers 1, c covers 2, d covers nothing
    cov = _cov(a=[{0}], b=[{1}], c=[{2}], d=[])
    rng = random.Random(1)
    strict, flex, n, exact = a1.p3(pool, cov, 3, rng, cap=20_000)
    # ordered triples of distinct accounts: 4*3*2 = 24; feasible iff {a,b,c} in some order: 6
    assert (n, exact) == (24, True)
    assert strict == 6 / 24
    assert flex == 6 / 24
    # one account covering all three lines in three sessions: flexible counts every triple containing it
    cov2 = _cov(a=[{0}, {1}, {2}], b=[], c=[], d=[])
    strict2, flex2, n2, _ = a1.p3(pool, cov2, 3, rng, cap=20_000)
    assert strict2 == 0.0
    assert flex2 == 18 / 24     # triples containing a: 24 - 3*2*1 = 18


def test_p3_samples_when_over_the_cap():
    pool = [f"u{i}" for i in range(30)]       # 30*29*28 = 24,360 > 20,000
    cov = {u: [] for u in pool}
    cov["u0"] = [{0}]
    cov["u1"] = [{1}]
    cov["u2"] = [{2}]
    strict, flex, n, exact = a1.p3(pool, cov, 3, random.Random(20261106), cap=20_000)
    assert (n, exact) == (20_000, False)
    assert 0.0 <= strict <= 0.01


def test_bootstrap_and_all_zero_bound():
    vals = [0.0] * 30
    b = a1.summarise(vals, n_boot=200, seed=20261106)
    assert b["mean"] == 0.0 and b["all_zero"] is True
    # Clopper-Pearson upper bound on 0 of 30 (two-sided 95 percent): 1 - 0.025**(1/30)
    assert abs(b["hi"] - (1 - 0.025 ** (1 / 30))) < 1e-9
    b2 = a1.summarise([0.0, 1.0] * 10, n_boot=500, seed=20261106)
    assert b2["all_zero"] is False and 0.2 < b2["lo"] < 0.5 < b2["hi"] < 0.8
