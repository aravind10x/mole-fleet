"""Tests for stage3_b3_s3.py (brief 33 A3 and A4): the stream set asserted as exactly {1, 2, 3, 4, 6}; the id sets checked
by hash; the refusal classes; the unit order per cell; cache labels unique within S3 and no cache before Stage B; the
spend ledger (one guard across every cache, the in-flight reservations, the stop at $153.25 with an overshoot of at most
four bases); each client's own cap; the view order enforced; the scores file's flag through stage3_thresholds at the
sealed rule; the first batch's re-base arithmetic; the character-based estimate. No request is sent, nothing is drawn
from S3's streams, nothing is written under work/stage3/b3 (temporary directories only).

Run: cd work/checks && ../mole-fork/.venv/bin/python -I -m pytest -q test_stage3_b3_s3.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import judge_client as jc_mod  # noqa: E402
import stage3_b3_s3 as d  # noqa: E402
import stage3_t1 as t1  # noqa: E402
import stage3_thresholds as th  # noqa: E402

CONFIG = {"placement_seed": 20261181, "bootstrap_seed": 20261152, "bootstrap_replicates": 2000, "tie_seed": 20261112, "m_s_carrier": 18.22,
          "m_s_second": 19.37, "m_L": 18.22, "arm_seeds": {"1": 2026118110, "2": 2026118120, "3": 2026118130, "4": 2026118140, "6": 2026118160}}


def test_the_stream_set_is_exactly_1_2_3_4_6():
    assert d.assert_arm_seeds(CONFIG) == {1: 2026118110, 2: 2026118120, 3: 2026118130, 4: 2026118140, 6: 2026118160}
    with pytest.raises(SystemExit, match="arm-seed set"):
        d.assert_arm_seeds({**CONFIG, "arm_seeds": {**CONFIG["arm_seeds"], "5": 2026118150}})     # the pre-flight alone would accept a tag 5
    with pytest.raises(SystemExit, match="arm-seed set"):
        d.assert_arm_seeds({**CONFIG, "arm_seeds": {k: v for k, v in CONFIG["arm_seeds"].items() if k != "6"}})
    with pytest.raises(SystemExit, match="arm-seed set"):
        d.assert_arm_seeds({**CONFIG, "arm_seeds": {**CONFIG["arm_seeds"], "6": 2026118161}})


def test_the_committed_configuration_passes():
    assert d.assert_arm_seeds(json.loads(d.CONFIG.read_text())) == d.ARMS_EXPECTED


def test_the_applied_id_sets_are_checked_against_section_1_1s_hashes():
    m = json.loads(d.MATRIX.read_text())
    sets = d.net_sets(m)
    assert {k: len(v) for k, v in sets.items()} == {"full": 73, "controls": 21, "sham": 22}
    bad = json.loads(json.dumps(m))
    bad["populations"]["full"]["ids"] = bad["populations"]["full"]["ids"][:-1]
    with pytest.raises(SystemExit, match="does not hash"):
        d.net_sets(bad)


def test_refusal_classes_separate_the_module_induced_drop_from_section_2_4_4():
    r = t1.Refused("k", "item", t1.RF_NO_VALID_DRAW, refused=[{"reason": "x"}] * (t1.MAX_REDRAWS + 1))
    assert d.classify_refusal(r).startswith("module-induced")
    r = t1.Refused("k", "item", t1.RF_NO_VALID_DRAW, refused=[{"reason": "x"}] * 3)
    assert d.classify_refusal(r).startswith("section 2.4 (4)")
    assert d.classify_refusal(t1.Refused("k", "item", t1.RF_PAIR)).startswith("section 2.4 (4)")


def _app():
    def u(iid, arm, role, pl, views):
        return {"unit_id": f"{iid}:{arm}{role}:{pl}", "item_id": iid, "regime": "candidate", "arm": arm, "role": role, "placement": pl, "day": "2026-04-06",
                "author": f"a{iid}", "document": "/shared/d.md", "packets": {v: {"packet": f"pkt {iid} {arm}{role} {pl} {v}", "truncated": False, "label": f"stem+s3:{iid}:{arm}{role}:{pl}",
                                                     "key": jc_mod.cache_key(v, f"stem+s3:{iid}:{arm}{role}:{pl}", f"pkt {iid} {arm}{role} {pl} {v}"), "author": f"a{iid}"}
                                                 for v in views}}
    all_views = (d.ad.ISO, d.ad.LIVE, "P_author", "O_diff")
    line_views = (d.ad.ISO, d.ad.LIVE, "P_author")
    units = [u("b", "item", 0, 1, all_views), u("a", "item", 0, 2, all_views), u("a", "item", 0, 1, all_views), u("a", "line", 2, 1, line_views),
             u("a", "line", 1, 1, line_views)]
    return {"units": {x["unit_id"]: x for x in units}}


def test_cell_units_are_items_ascending_opaque_id_then_lines_and_lines_only_on_per_agent_rows():
    app = _app()
    ids = [x["unit_id"] for x in d.cell_units(app, d.ad.ISO, "opus48")]
    assert ids == ["a:item0:1", "a:item0:2", "b:item0:1", "a:line1:1", "a:line2:1"]
    assert [x["unit_id"] for x in d.cell_units(app, d.ad.LIVE, "opus48")] == ["a:item0:1", "a:item0:2", "b:item0:1"]
    assert [x["unit_id"] for x in d.cell_units(app, "O_diff", "sol")] == ["a:item0:1", "a:item0:2", "b:item0:1"]


def test_cache_labels_carry_the_view_the_unit_id_and_the_run_tag_and_are_unique():
    app = _app()
    labels = set()
    for view, judge in d.ORDER:
        for x in d.cell_units(app, view, judge):
            lab = x["packets"][view]["label"]
            assert "s3:" in lab and x["unit_id"] in lab
            assert (view, judge, lab) not in labels            # unique within a cell (one cache per view and model)
            labels.add((view, judge, lab))
    assert d.unit_label("prefix_rw_v2c", "id:item0:1") == "prefix_rw_v2c+s3:id:item0:1"


def test_no_cache_exists_before_stage_b():
    if not d.RUN.exists():
        assert not (d.CACHE_DIR.exists() and any(d.CACHE_DIR.glob("*.jsonl")))
    else:
        assert json.loads(d.RUN.read_text())["stage_b_started"] is not None


class _FakeClient:
    def __init__(self, total):
        self._t = total

    def total_spent(self):
        return self._t


def test_the_ledger_stops_at_the_recorded_plus_reserved_dollars(monkeypatch):
    monkeypatch.setattr(d, "dollars_all", lambda: {"total": 0.0})
    L = d.Ledger(153.25, {"c1": _FakeClient(100.0), "c2": _FakeClient(50.0)})
    L.guard()                                   # 150.00 recorded, nothing in flight
    for _ in range(4):
        L.enter(0.5)                            # four units at a $0.50 basis in flight: 150 + 2 = 152 < 153.25
    L.guard()
    L.enter(0.5)                                # a fifth: 152.5 < 153.25 still passes
    L.guard()
    L.enter(0.5)                                # 153.0 passes; the sixth reservation reaches the stop
    L.guard()
    L.enter(0.5)
    with pytest.raises(jc_mod.JudgeAborted, match="S3 stop"):
        L.guard()
    for _ in range(7):
        L.leave()
    assert L.in_flight == 0
    L.guard()


def test_the_ledger_overshoot_is_at_most_concurrency_bases(monkeypatch):
    monkeypatch.setattr(d, "dollars_all", lambda: {"total": 0.0})
    L = d.Ledger(10.0, {"c": _FakeClient(9.9)})
    L.enter(0.05)
    L.guard()                                   # 9.95 < 10
    L.enter(0.05)
    with pytest.raises(jc_mod.JudgeAborted):
        L.guard()                               # 10.0 reaches the stop with two in flight: the overshoot bound is the in-flight bases


def test_the_ledger_reads_the_other_caches_from_disk(monkeypatch):
    monkeypatch.setattr(d, "dollars_all", lambda: {"P_author_doc_iso|opus48": 100.0, "P_author|opus48": 40.0, "total": 140.0})
    L = d.Ledger(153.25, {"P_author|opus48": _FakeClient(41.0)})     # the live client's total replaces its file's figure
    assert L.recorded() == 141.0


def test_each_clients_own_cap_is_the_stop_less_the_other_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(d, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(d, "dollars_all", lambda: {"P_author_doc_iso|opus48": 20.0, "P_author|opus48": 0.0, "total": 20.0})
    L = d.Ledger(153.25)
    jc = d.make_client("P_author", "opus48", L)
    assert jc.spend_cap_usd == pytest.approx(133.25) and jc.request_guard == L.guard and jc.max_tokens == 4000 and jc.model == d.MODELS["opus48"]
    assert jc.effort is None and jc.parse is None and jc.refusal_retries == jc_mod.MAX_REFUSAL_RETRIES
    sol = d.make_client("O_diff", "sol", L)
    assert sol.spend_cap_usd == pytest.approx(133.25) and sol.request_guard == L.guard and sol.model == "us.openai.gpt-6-sol"
    assert set(L.clients) == {"P_author|opus48", "O_diff|sol"}


def test_the_view_order_is_enforced(monkeypatch, tmp_path):
    app = _app()
    render = {"rows": {"|".join(c): {"s2_basis_per_unit": 0.01, "estimate": {"est_cost_usd": 1.0, "n_calls": 1}} for c in d.ORDER}, "applications_sha256": "x"}
    run = {"cells": {}, "first_batch": {"done": True}, "stopped": None}
    statuses = {"|".join(d.ORDER[0]): {"complete": False, "n_units": 5, "completed": 4, "scored": 4, "refused": 0, "errored_only": 0, "missing": 1, "dollars": 1.0}}
    monkeypatch.setattr(d, "cell_status", lambda a, v, j: statuses.get("|".join((v, j)), {"complete": False, "n_units": 3, "completed": 0, "scored": 0, "refused": 0,
                                                                                            "errored_only": 0, "missing": 3, "dollars": 0.0}))
    monkeypatch.setattr(d, "make_client", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no client must be built")))

    class NS:
        cont = True
        concurrency = 4
        rpm = 30
    # cell 0 is incomplete and the first batch is recorded: the run scores cell 0; make scoring a no-op that leaves it incomplete
    async def fake_score(jc, view, units, ledger, basis, concurrency=4):
        return {}, None
    monkeypatch.setattr(d, "score_units", fake_score)
    monkeypatch.setattr(d, "make_client", lambda *a, **k: type("J", (), {"batch_log": lambda self, p, note=None: None})())
    monkeypatch.setattr(d, "write_json", lambda p, o: "h")
    monkeypatch.setattr(d, "write_scores", lambda a, r: "h")
    monkeypatch.setattr(d, "dollars_all", lambda: {"total": 0.0})
    monkeypatch.setattr(d, "CACHE_DIR", tmp_path)
    rc = asyncio.run(d.run_cells(NS(), app, render, run))
    assert rc == 1 and run["stopped"]["cell"] == "|".join(d.ORDER[0])      # it stops rather than opening cell 1 with cell 0 incomplete


def test_the_scores_files_flag_comes_from_stage3_thresholds_at_the_sealed_rule(monkeypatch, tmp_path):
    app = _app()
    monkeypatch.setattr(d, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(d, "APPLICATIONS", tmp_path / "app.json")
    (tmp_path / "app.json").write_text("{}")
    rule_a = {"kind": "author", "seed": 20261112, "threshold": 50.0, "p_tie": 0.5}
    rule_u = {"kind": "unit", "seed": 20261112, "threshold": 50.0, "p_tie": 0.5}
    monkeypatch.setattr(d, "sealed_rule", lambda v, j: rule_u if v == "O_diff" else rule_a)
    # the author's honest units in the view's null: one on another document (enters the union), one on the planted document (does not)
    monkeypatch.setattr(d, "honest_pairs_for", lambda v, j: {("aa", "/shared/other.md"): 70.0, ("aa", "/shared/d.md"): 99.0, ("zz", "/shared/x.md"): 100.0})
    us = d.cell_units(app, d.ad.ISO, "opus48")
    cp = d.cache_path(d.ad.ISO, "opus48")
    recs = [{"cache_key": us[0]["packets"][d.ad.ISO]["key"], "outcome": "scored", "score": 50, "cost_usd": 0.01},
            {"cache_key": us[1]["packets"][d.ad.ISO]["key"], "outcome": "refused", "score": None, "cost_usd": 0.01},
            {"cache_key": us[2]["packets"][d.ad.ISO]["key"], "outcome": "errored", "score": None, "cost_usd": 0.01}]
    cp.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    sc = d.build_scores(app, {"stopped": None})
    rows = {r["unit_id"]: r for r in sc["rows"] if r["view"] == "P_author_doc_iso" and r["judge"] == "opus48"}
    r1 = rows["a:item0:1"]
    assert r1["union_max"] == 70.0 and r1["n_honest_other_pairs"] == 1                   # the planted document's own honest pair is excluded
    assert r1["flag"] == th.is_flagged(70.0, rule_a, "aa") is True                        # the sealed author-level reading, the tie keyed by the author
    assert r1["flag_unit"] == th.is_flagged(50.0, rule_a, "aa")                           # the planted unit's own flag beside
    assert rows["a:item0:2"]["outcome"] == "refused" and rows["a:item0:2"]["score"] is None and rows["a:item0:2"]["flag"] is None
    assert rows["b:item0:1"]["outcome"] == "errored"
    assert rows["a:line1:1"]["outcome"] == "missing"
    c = sc["cells"]["P_author_doc_iso|opus48"]
    assert {k: c[k] for k in ("n_units", "scored", "refused", "errored", "missing", "rule_kind", "tie_seed")} == {"n_units": 5, "scored": 1, "refused": 1, "errored": 1, "missing": 2, "rule_kind": "author", "tie_seed": 20261112}
    assert c["honest_source"] == "work/stage3/b1/b1-null.json"
    assert all(set(r) == {"unit_id", "item_id", "regime", "arm", "role", "placement", "view", "judge", "outcome", "score", "flag", "flag_unit", "union_max",
                          "n_honest_other_pairs", "cache_label"} for r in sc["rows"])
    # O_diff: the unit rule keyed by the cache label, both flags equal, no union
    cpo = d.cache_path("O_diff", "sol")
    uo = d.cell_units(app, "O_diff", "sol")
    cpo.write_text(json.dumps({"cache_key": uo[0]["packets"]["O_diff"]["key"], "outcome": "scored", "score": 50, "cost_usd": 0.01}) + "\n")
    ro = {r["unit_id"]: r for r in d.build_scores(app, {"stopped": None})["rows"] if r["view"] == "O_diff" and r["judge"] == "sol"}
    assert ro["a:item0:1"]["flag"] == ro["a:item0:1"]["flag_unit"] == th.is_flagged(50.0, rule_u, uo[0]["packets"]["O_diff"]["label"]) and ro["a:item0:1"]["union_max"] is None
    # G5 (i): a unit still errored after the client's retries is unscored and completes its cell
    st = d.cell_status(app, d.ad.ISO, "opus48")
    assert st["errored_only"] == 1 and st["missing"] == 2 and not st["complete"]
    for u in us[3:]:
        with cp.open("a") as fh:
            fh.write(json.dumps({"cache_key": u["packets"][d.ad.ISO]["key"], "outcome": "errored", "score": None, "cost_usd": 0.01}) + "\n")
    st = d.cell_status(app, d.ad.ISO, "opus48")
    assert st["errored_only"] == 3 and st["missing"] == 0 and st["complete"]


def test_continue_clears_a_recorded_stop():
    run = {"stopped": {"reason": "x", "cell": "c", "ts": "t"}}
    d.clear_stop(run)
    assert run["stopped"] is None and run["stops_cleared"][0]["reason"] == "x" and "cleared" in run["stops_cleared"][0]


def test_every_sealed_rule_carries_the_tie_seed_and_its_kind():
    for (view, judge) in d.ORDER:
        r = d.sealed_rule(view, judge)
        assert r["seed"] == 20261112 and r["kind"] == ("unit" if view == "O_diff" else "author")


def test_the_first_batch_report_rebases_every_cell_by_the_carriers_ratio_on_the_same_units(monkeypatch):
    render = {"rows": {"|".join(c): {"s2_basis_per_unit": 0.044715, "estimate": {"est_cost_usd": 10.0, "n_calls": 100}} for c in d.ORDER}}
    us = [{"unit_id": f"u{i}"} for i in range(20)]
    recs = {f"u{i}": {"outcome": "scored", "cost_usd": 0.2, "input_tokens": 1000, "output_tokens": 300, "attempts": [{}]} for i in range(20)}
    monkeypatch.setattr(d, "estimate_cell", lambda units, view, judge: {"est_cost_usd": 2.0 * len(units) / 20, "n_calls": len(units)})   # the batch's own estimate: $0.10 a unit
    fb = d.first_batch_report({}, recs, us, render)
    assert fb["n_units"] == 20 and fb["dollars"] == pytest.approx(4.0) and fb["realised_per_unit_usd"] == pytest.approx(0.2)
    assert fb["estimated_per_unit_usd"] == pytest.approx(0.1) and fb["cell_estimate_per_unit_usd"] == pytest.approx(0.1)   # like with like: the same units' estimate
    assert fb["ratio_realised_over_estimated"] == pytest.approx(2.0) and fb["rebased_total_usd"] == pytest.approx(180.0) and fb["escalate"]
    assert fb["ratio_realised_over_cell_estimate"] == pytest.approx(2.0)
    assert fb["ratio_realised_over_part2_basis"] == pytest.approx(0.2 / 0.044715, abs=1e-4)
    assert fb["input_tokens"] == 20000 and fb["output_tokens"] == 6000 and fb["refused"] == 0


def test_the_pre_signal_estimate_uses_2_15_chars_per_token_and_b1s_output_basis(monkeypatch):
    monkeypatch.setattr(d, "output_basis", lambda judge, view: 767.5)
    us = [{"packets": {"O_diff": {"packet": "x" * 2150, "truncated": False}}} for _ in range(10)]
    e = d.estimate_cell(us, "O_diff", "opus48")
    sys_chars = len(d.sv.system_prompt("O_diff", 0))
    assert e["n_calls"] == 10 and e["est_input_tokens"] == round((21500 + 10 * sys_chars) / 2.15) and e["est_output_tokens"] == 7675
    price = jc_mod.PRICES[d.MODELS["opus48"]]
    assert e["est_cost_usd"] == pytest.approx((e["est_input_tokens"] * price["input"] + 7675 * price["output"]) / 1e6, abs=1e-3)


@pytest.mark.skipif(not os.environ.get("S3_SLOW"), reason="S3_SLOW=1 renders one application outside S3's streams (loads the corpus)")
def test_one_application_renders_under_every_row_with_unique_labels():
    import random
    m = json.loads(d.MATRIX.read_text())
    items, _ = d.dr.load_items(d.dr.input_paths())
    by_id = {it["item_id"]: it for it in items}
    iid = sorted(m["populations"]["full"]["ids"])[0]
    W = d.World()
    ins = t1.build_parts_inserter(d.CORPUS, d.TEMPLATE, d.VALID)
    pair = ins.plant_pair(d.payload_of(by_id[iid]), "item", random.Random("test-not-an-s3-stream"), key=iid)
    pk = d.render_unit(W, pair[0], f"{iid}:item0:1", True)
    assert set(pk) == {d.ad.ISO, d.ad.LIVE, "P_author", "O_diff"}
    assert len({v["key"] for v in pk.values()}) == 4 and all(not v["truncated"] for v in pk.values())
    assert pk[d.ad.ISO]["meta"]["own_statements_shown"] == pk[d.ad.ISO]["meta"]["own_statements"] == 3
    line = ins.plant_pair(d.payload_of(by_id[iid]), 0, random.Random("test-not-an-s3-stream-2"), key=iid, exclude=tuple(x.authors[0] for x in pair))
    pl = d.render_unit(W, line[0], f"{iid}:line1:1", False)
    assert set(pl) == {d.ad.ISO, d.ad.LIVE, "P_author"} and pl[d.ad.ISO]["meta"]["own_statements"] == 1
