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


# ── v1 (brief 36 dated notes 3 and 4): rule (iii), the exact p3, the ex-ante triple, the map ──

def _random_cov(rng, n_acct, n_lines=3):
    pool = [f"a{i}" for i in range(n_acct)]
    cov = {}
    for a in pool:
        k = rng.choice([0, 0, 0, 1, 1, 2, 3])
        cov[a] = [set(i for i in range(n_lines) if rng.random() < 0.35) for _ in range(k)]
    return pool, cov


def test_p3_exact_equals_full_enumeration():
    rng = random.Random(7)
    for _ in range(40):
        pool, cov = _random_cov(rng, rng.randint(3, 11))
        strict, flex, n, exact = a1.p3(pool, cov, 3, random.Random(0), cap=10 ** 9)
        assert exact
        s2, f2 = a1.p3_exact(pool, cov)
        assert abs(s2 - strict) < 1e-12 and abs(f2 - flex) < 1e-12


def test_p3_exact_same_item_groups():
    pool = ["a", "b", "c"]
    # lines 0 and 1 share an item; a's one session covers both, c covers line 2
    cov = {"a": [{0, 1}], "b": [], "c": [{2}]}
    strict, flex = a1.p3_exact(pool, cov)
    assert strict == 0.0 and flex == 0.0          # a single session cannot cover two lines
    strict_g, flex_g = a1.p3_exact(pool, cov, groups=[[0, 1], [2]])
    assert flex_g == 1.0                          # one session may cover the same-item lines
    assert strict_g == 0.0                        # strict: one line per account, b covers nothing


def test_ex_ante_triple_by_write_variant_count_ties_by_item_order():
    items = ["i0", "i1", "i2", "i3", "i4", "i5"]
    counts = {"i0": 3, "i1": 5, "i2": 3, "i3": 3, "i4": 5, "i5": 1}
    assert a1.top_items(items, counts) == ("i1", "i4", "i0")


def test_triples_of_six_items():
    assert len(a1.item_triples(list("abcdef"))) == 20
    assert len(a1.item_multisets_with_repeat(list("abcdef"))) == 36


def test_shared_resamples_keep_p1_bound_under_p0():
    import numpy as np
    r = np.random.default_rng(3)
    p0 = r.random(50) * 0.2
    p1 = p0 * r.random(50)
    p3 = p0 * 0.3
    s = a1.summarise_shared({"p0": p0, "p1": p1, "p3": p3}, ratio=("p3", "p0"), n_boot=500, seed=20261106)
    assert s["p1"]["hi"] <= s["p0"]["hi"] + 1e-12
    assert abs(s["ratio"]["mean"] - p3.mean() / p0.mean()) < 1e-12
    assert s["ratio"]["hi"] < 1.0


def test_shared_all_zero_uses_the_application_bound():
    import numpy as np
    s = a1.summarise_shared({"p0": np.full(30, 0.1), "p3": np.zeros(30)}, ratio=("p3", "p0"), n_boot=100, seed=1)
    assert s["p3"]["all_zero"] and abs(s["p3"]["hi"] - (1 - 0.025 ** (1 / 30))) < 1e-9


def _s(p0, p1, p3, ratio_hi=0.5):
    return {"p0": {"mean": p0[0], "lo": p0[1], "hi": p0[2]}, "p1": {"mean": p1[0], "lo": p1[1], "hi": p1[2]},
            "p3": {"mean": p3[0], "lo": p3[1], "hi": p3[2]}, "ratio": {"hi": ratio_hi}}


def test_outcome_map():
    assert a1.outcome_map(_s((0.01, 0.0, 0.03), (0.0, 0.0, 0.01), (0.0, 0.0, 0.02))) == "R1"
    assert a1.outcome_map(_s((0.3, 0.2, 0.4), (0.01, 0.0, 0.03), (0.2, 0.1, 0.3))) == "R2"
    assert a1.outcome_map(_s((0.07, 0.055, 0.09), (0.0, 0.0, 0.01), (0.004, 0.002, 0.006), 0.1)) == "R3a"
    assert a1.outcome_map(_s((0.07, 0.04, 0.09), (0.0, 0.0, 0.01), (0.004, 0.002, 0.006), 0.1)) == "R3b"
    assert a1.outcome_map(_s((0.07, 0.055, 0.09), (0.0, 0.0, 0.01), (0.004, 0.002, 0.006), 1.2)) == "R3b"
    # U0 < 0.05 but U3 >= 0.05 and no R2: unmapped
    assert a1.outcome_map(_s((0.03, 0.01, 0.045), (0.0, 0.0, 0.01), (0.03, 0.0, 0.06))) == "unmapped"
