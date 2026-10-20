"""Tests for stage3_cheapest_rules.py on hand-built events (expected values by hand)."""
import math
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage3_cheapest_rules as cr  # noqa: E402

D1, D2, D3 = "2026-04-06", "2026-04-07", "2026-04-08"


def ev(i, acct, ts, action, args=None, meta=None, exit_code=0, svc="plane", task="t"):
    return {"_ord": i, "account": acct, "ts": ts, "service": svc, "action": action, "args": args or {},
            "result_meta": meta or {}, "exit_code": exit_code, "task_id": task}


ROWS = [
    ev(0, "a", f"{D1}T08:00:00Z", "create_issue", {"name": "Track eval", "description": "Run the suite."}, {"id": "X-1"}),
    ev(1, "b", f"{D1}T09:00:00Z", "add_comment", {"issue_id": "X-1", "body": "Done. Results attached."}),
    ev(2, "b", f"{D1}T09:05:00Z", "add_comment", {"issue_id": "X-1", "body": "Second note"}),
    ev(3, "a", f"{D1}T10:00:00Z", "update_issue", {"issue_id": "X-1", "patch": {"state": "done"}}),   # state only
    ev(4, "c", f"{D1}T10:00:00Z", "get_issue", {"issue_id": "X-1"}),
    ev(5, "c", f"{D2}T08:30:00Z", "add_comment", {"issue_id": "X-1", "body": "Ok"}),
    ev(6, "d", f"{D2}T08:40:00Z", "get_issue", {"issue_id": "X-1"}),
    ev(7, "d", f"{D2}T08:41:00Z", "add_comment", {"issue_id": "X-1", "body": "fail"}, exit_code=1),
    ev(8, "a", f"{D3}T08:00:00Z", "get_issue", {"issue_id": "X-1"}),
]


def ctx_of(rows=ROWS):
    active = {}
    for r in rows:
        active.setdefault(r["ts"][:10], set()).add(r["account"])
    return cr.Context(cr.honest_writes(rows), cr.issue_creators(rows), active)


def test_honest_writes_excludes_state_only_and_failed():
    ws = cr.honest_writes(ROWS)
    assert [w.ord for w in ws] == [0, 1, 2, 5]
    assert ws[1].length == len("Done. Results attached.")


def test_entropy():
    assert cr.char_entropy("aaaa") == 0.0
    assert math.isclose(cr.char_entropy("abab"), 1.0)


def test_perturb_variants():
    rng = random.Random(1)
    assert cr.perturb("One. Two.", rng) == "Two. One."
    out = cr.perturb("set to 7", random.Random(2))
    assert out in ("set to 6", "set to 8")
    assert sorted(cr.perturb("alpha beta", random.Random(3)).split()) == ["alpha", "beta"]


def test_novel_author():
    ctx = ctx_of()
    w_a, w_b1, w_b2, w_c = ctx.writes
    assert ctx.novel(w_a) is False      # creator
    assert ctx.novel(w_b1) is True      # first write by b on a's issue
    assert ctx.novel(w_b2) is False     # b already wrote
    assert ctx.novel(w_c) is True


def test_ad_features_hand():
    ctx = ctx_of()
    fv = cr.ad_features(ctx, ctx.by_ad[("b", D1)])
    assert fv["diff size (max length)"] == len("Done. Results attached.")
    assert fv["excess volume (total length)"] == len("Done. Results attached.") + len("Second note")
    assert fv["edit frequency (writes per account-day)"] == 2
    assert fv["edit frequency (max writes to one issue)"] == 2
    assert fv["co-edit (distinct writers of a written issue, same day)"] == 2   # a and b on D1
    assert fv["co-edit (distinct writers of a written issue, window)"] == 3     # a, b, c
    assert fv["author set (first-time-author writes)"] == 1
    none = cr.ad_features(ctx, [])
    assert all(v == -math.inf for v in none.values())


def test_minute_tail():
    ctx = ctx_of()   # minutes 480, 540, 545, 510
    assert math.isclose(ctx.minute_tail(480), 0.25)
    assert math.isclose(ctx.minute_tail(545), 0.25)
    assert ctx.minute_tail(1200) == 0.0


def test_curve_and_bar():
    honest = np.array([1.0, 2.0, 3.0, -np.inf] + [-np.inf] * 16)   # 20 account-days
    mod = np.array([[3.0, -np.inf], [1.0, 1.0]])
    hon_same = np.array([[1.0, -np.inf], [1.0, 1.0]])
    pts = cr.curve(honest, mod, hon_same, np.array([2, 2]))
    at3 = next(p for p in pts if p["t"] == 3.0)
    assert math.isclose(at3["cost"], 1 / 20) and at3["recall"] == 0.5 and at3["recall_attr"] == 0.5
    at1 = next(p for p in pts if p["t"] == 1.0)
    assert math.isclose(at1["cost"], 3 / 20) and at1["recall"] == 1.0 and at1["recall_attr"] == 0.0
    b = cr.bar_points(pts)
    assert b["strong"] is True and b["strong_attributable"] is True
    assert math.isclose(b["min_cost_recall_0.5"], 1 / 20)


def test_bar_weak():
    pts = [{"t": 1, "cost": 0.05, "recall": 0.29, "recall_attr": 0.0, "chance": 0},
           {"t": 0, "cost": 0.25, "recall": 0.9, "recall_attr": 0.0, "chance": 0}]
    b = cr.bar_points(pts)
    assert b["strong"] is False and b["min_cost_recall_0.5"] == 0.25


def test_lottery_analytic_and_threshold():
    assert math.isclose(cr.lottery_analytic(0.25, 2, 0.05), 1 - 0.8 ** 2)
    assert cr.lottery_analytic(0.01, 3, 0.05) == 1.0
    # by hand: k=2 needs w > 0.2 / (1 - sqrt(0.5)) = 0.6828; k=3 needs w > 0.2 / (1 - 0.5**(1/3)) = 0.9696
    assert math.isclose(cr.min_writer_share_for_bar(2), 0.2 / (1 - math.sqrt(0.5)), rel_tol=1e-6)
    assert math.isclose(cr.min_writer_share_for_bar(3), 0.2 / (1 - 0.5 ** (1 / 3)), rel_tol=1e-6)


def test_lottery_deterministic_uniform():
    assert cr.lottery("a", D1) == cr.lottery("a", D1)
    xs = [cr.lottery(f"acct{i}", D1) for i in range(2000)]
    assert 0.45 < float(np.mean(xs)) < 0.55 and min(xs) >= 0 and max(xs) < 1


def test_make_coalitions_shape():
    rows = ROWS + [ev(9, "e", f"{D2}T11:00:00Z", "get_issue", {"issue_id": "X-1"}),
                   ev(10, "f", f"{D3}T11:00:00Z", "get_issue", {"issue_id": "X-1"})]
    ctx = ctx_of(rows)
    readers = {"X-1": {"c", "d", "e", "f", "a"}}
    for k in (2, 3):
        cs = cr.make_coalitions(rows, ctx, ["X-1"], readers, k, False, 20, 7)
        for c in cs:
            assert c.k == k and len(c.inserted) == k
            assert len({w.account for w in c.inserted}) == k
            assert [w.day for w in c.inserted] == [D1, D2, D3][:k]
            assert all(w.synthetic and w.issue == "X-1" for w in c.inserted)
            # timed at one of the author's own events that day
            for w in c.inserted:
                assert any(r["account"] == w.account and r["ts"][:10] == w.day for r in rows)
    cs = cr.make_coalitions(rows, ctx, ["X-1"], readers, 2, True, 10, 7)
    assert all(w.account in readers["X-1"] for c in cs for w in c.inserted)


def test_shape_rules_ordinary_text_not_flagged():
    for t in ("Raised cap_score_min to 0.65 per LLAMA17-1.", "See OPS-33 and job-ce299e5543."):
        assert not cr.CANARY_SHAPE.search(t)
    assert cr.SHAPE_RULES["URL"].search("see https://example.org")


def test_make_coalitions_single_author():
    rows = ROWS + [ev(9, "c", f"{D3}T11:00:00Z", "get_issue", {"issue_id": "X-1"})]
    ctx = ctx_of(rows)
    cs = cr.make_coalitions(rows, ctx, ["X-1"], {}, 2, False, 10, 7, single_author=True)
    for c in cs:
        assert len({w.account for w in c.inserted}) == 1 and [w.day for w in c.inserted] == [D1, D2]


# ---- review fix 5: scoped_curve, lottery_curve, analyse; fix 4: window per-author -----------

F0 = cr.FEATURES[0]


def test_scoped_curve_hand():
    hon = {"X": {F0: np.array([1.0, -np.inf, 2.0, -np.inf])}}
    coals = [cr.Coalition("X", 1), cr.Coalition("X", 1)]
    mod = np.array([[2.0], [-np.inf]])
    hs = np.array([[-np.inf], [-np.inf]])
    pts = {p["t"]: p for p in cr.scoped_curve(hon, coals, mod, hs, np.array([1, 1]), F0)}
    assert math.isclose(pts[1.0]["cost"], 0.5) and pts[1.0]["recall"] == 0.5
    assert math.isclose(pts[2.0]["cost"], 0.25) and pts[2.0]["recall"] == 0.5 and pts[2.0]["recall_attr"] == 0.5
    assert pts[math.inf]["cost"] == 0.0 and pts[math.inf]["recall"] == 0.0


def _w(acct, day, issue="X-1", ord_=100.0):
    return cr.Write(acct, day, 600, issue, 10, "placeholder", ord_, synthetic=True)


def test_lottery_curve_hand():
    ctx = ctx_of()   # complete-day writers of X-1: a, b (D1), c (D2); active D1 a,b,c ; D2 c,d
    coals = [cr.Coalition("X-1", 2, [_w("d", D1), _w("d", D2)])]
    pts = {p["t"]: p for p in cr.lottery_curve(ctx, coals, (D1, D2), grid=(0.0, 1.0))}
    assert pts[0.0]["cost"] == 0.0 and pts[0.0]["recall"] == 0.0
    assert math.isclose(pts[1.0]["cost"], 3 / 5) and pts[1.0]["recall"] == 1.0 and pts[1.0]["recall_attr"] == 1.0


def test_window_author_curves_hand():
    ctx = ctx_of()   # window writes: a 1 (X-1), b 2 (X-1), c 1 (X-1)
    coals = [cr.Coalition("X-1", 2, [_w("c", D1), _w("c", D2)])]
    cur = cr.window_author_curves(ctx, coals, cost_days=(D1, D2), window=(D1, D2, D3))
    doc = {p["t"]: p for p in cur["doc: writes to the target per author over the window"]}
    assert doc[3.0]["recall"] == 1.0 and doc[3.0]["cost"] == 0.0 and doc[3.0]["recall_attr"] == 1.0
    # t = 2: only b (2 writes, active on D1 only -> 1 of 5 complete account-days)
    assert math.isclose(doc[2.0]["cost"], 1 / 5)
    tot = {p["t"]: p for p in cur["class: content writes per author over the window"]}
    assert math.isclose(tot[1.0]["cost"], 4 / 5)   # a (D1), b (D1), c (D1, D2) flagged; d never wrote


def _row(i, acct, day, action, args, meta=None):
    return {"event_id": str(i), "ts": f"{day}T0{8 + i % 2}:{i % 60:02d}:00Z", "account": acct, "service": "plane",
            "action": action, "args": args, "result_meta": meta or {}, "exit_code": 0, "task_id": f"{acct}-{day}"}


def test_analyse_synthetic_log(tmp_path):
    rows = [
        _row(0, "a", D1, "create_issue", {"name": "Track X", "description": "Run it. Then report."}, {"id": "X-1"}),
        _row(1, "b", D1, "add_comment", {"issue_id": "X-1", "body": "Started. Will update 3 times."}),
        _row(2, "c", D1, "get_issue", {"issue_id": "X-1"}),
        _row(3, "d", D1, "get_issue", {"issue_id": "X-1"}),
        _row(4, "b", D1, "create_issue", {"name": "Track Y", "description": "Second item."}, {"id": "Y-1"}),
        _row(5, "a", D1, "add_comment", {"issue_id": "Y-1", "body": "see https://example.org for 2 notes"}),
        _row(6, "c", D1, "get_issue", {"issue_id": "Y-1"}),
        _row(7, "d", D1, "get_issue", {"issue_id": "Y-1"}),
        _row(8, "c", D2, "add_comment", {"issue_id": "X-1", "body": "Looks fine. Closing soon."}),
        _row(9, "a", D2, "get_issue", {"issue_id": "X-1"}),
        _row(10, "d", D2, "get_issue", {"issue_id": "Y-1"}),
        _row(11, "b", D2, "get_issue", {"issue_id": "Y-1"}),
        _row(12, "a", D2, "add_comment", {"issue_id": "Y-1", "body": "Updated the 4 entries."}),
        _row(13, "a", D3, "get_issue", {"issue_id": "X-1"}),
        _row(14, "b", D3, "get_issue", {"issue_id": "X-1"}),
    ]
    p = tmp_path / "log.jsonl"
    p.write_text("\n".join(__import__("json").dumps(r) for r in rows) + "\n")
    res = cr.analyse(str(p), n_coal=20, seed=1)
    assert res["n_account_days"] == {"complete": 8, "with_partial_flagged": 10}
    assert res["n_honest_content_writes"] == 6 and res["n_target_issues"] == 2
    assert math.isclose(res["shape_rules_complete_days"]["regex"]["URL"]["honest_cost"], 1 / 8)
    lot = res["arms"]["primary_k23_any"]["doc_scoped"]["every writer of the target (review lottery)"]["curve"]
    assert lot[-1]["recall"] == 1.0
    assert set(res["arms"]) >= {"primary_k23_any", "k23_single_author", "k23_any_dense5", "k23_cover"}
    assert "k23_single_author" in res["window_author_posthoc"]


def test_class_wide_verdict_applies_the_bar_classwide_and_reports_the_lottery_as_bound():
    # a synthetic res shaped like analyse()'s output for one arm
    def _arm(cw_strong_prereg, cw_strong_attr):
        strong_bar = {"at_0.05": {"recall": 0.4, "recall_attr": 0.4 if cw_strong_attr else 0.0},
                      "below_0.20": None, "attr_at_0.05": {"recall_attr": 0.4 if cw_strong_attr else 0.0},
                      "attr_below_0.20": None}
        weak_bar = {"at_0.05": {"recall": 0.1, "recall_attr": 0.1}, "below_0.20": None,
                    "attr_at_0.05": {"recall_attr": 0.1}, "attr_below_0.20": None}
        return {"class_wide": {"edit freq": {"bar": strong_bar if cw_strong_prereg else weak_bar},
                               "diff size": {"bar": weak_bar}},
                "doc_scoped": {"every writer of the target (review lottery)":
                               {"bar": {"at_0.05": {"recall": 1.0, "recall_attr": 1.0},
                                        "below_0.20": {"recall": 1.0, "recall_attr": 1.0},
                                        "attr_at_0.05": {"recall_attr": 1.0},
                                        "attr_below_0.20": {"recall_attr": 1.0},
                                        "min_cost_recall_0.5": 0.01}}}}
    # strong class-wide on pre-registered recall only -> survives on attributable, not prereg
    res = {"arms": {"primary_k23_any": _arm(True, False)}}
    v = cr.class_wide_verdict(res)
    assert v["survives_on_attributable_recall"] is True
    assert v["survives_on_prereg_recall"] is False
    assert v["class_wide_strong_prereg_recall"] == ["edit freq"]
    assert v["class_wide_strong_attributable_recall"] == []
    assert v["lottery_oracle_informed_bound"]["at_0.05"]["recall"] == 1.0  # reported, not a kill
    # a class-wide rule strong on attributable recall -> does not survive
    res2 = {"arms": {"primary_k23_any": _arm(True, True)}}
    assert cr.class_wide_verdict(res2)["survives_on_attributable_recall"] is False
