"""Tests for stage3_b3_s3.py (brief 33 A3 and A4): the stream set asserted as exactly {1, 2, 3, 4, 6}; the id sets checked
by hash; the refusal classes; the unit order per cell; cache labels unique within S3 and no cache before Stage B; the
spend ledger (one guard across every cache, the in-flight reservations, the stop at $153.25 with an overshoot of at most
four bases); each client's own cap; the view order enforced; the scores file's flag through stage3_thresholds at the
sealed rule; the first batch's re-base arithmetic; the character-based estimate. Brief 33's dated notes 4 and 5: G7 (one
errored record keeps the cell open, two make the unit unscored; the G7-only stop and its continue count), G9 (the union's
keys checked by cause) and the Stage B refusals (the clean-items file at its hash, a passing G9 check). No request is
sent, nothing is drawn from S3's streams, nothing is written under work/stage3/b3 (temporary directories only).

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
    statuses = {"|".join(d.ORDER[0]): {"complete": False, "n_units": 5, "completed": 4, "scored": 4, "refused": 0, "errored_once": 0, "errored_final": 0, "errored_only": 0, "missing": 1, "dollars": 1.0}}
    monkeypatch.setattr(d, "cell_status", lambda a, v, j: statuses.get("|".join((v, j)), {"complete": False, "n_units": 3, "completed": 0, "scored": 0, "refused": 0,
                                                                                            "errored_once": 0, "errored_final": 0, "errored_only": 0, "missing": 3, "dollars": 0.0}))
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
    assert rows["b:item0:1"]["outcome"] == "errored_open"                                  # one errored record: open, re-asked once on --continue (G7)
    assert rows["a:line1:1"]["outcome"] == "missing"
    c = sc["cells"]["P_author_doc_iso|opus48"]
    assert {k: c[k] for k in ("n_units", "scored", "refused", "errored", "errored_open", "missing", "rule_kind", "tie_seed")} == {
        "n_units": 5, "scored": 1, "refused": 1, "errored": 0, "errored_open": 1, "missing": 2, "rule_kind": "author", "tie_seed": 20261112}
    assert c["honest_source"] == "work/stage3/b1/b1-null.json"
    assert all(set(r) == {"unit_id", "item_id", "regime", "arm", "role", "placement", "view", "judge", "outcome", "score", "flag", "flag_unit", "union_max",
                          "n_honest_other_pairs", "cache_label"} for r in sc["rows"])
    # O_diff: the unit rule keyed by the cache label, both flags equal, no union
    cpo = d.cache_path("O_diff", "sol")
    uo = d.cell_units(app, "O_diff", "sol")
    cpo.write_text(json.dumps({"cache_key": uo[0]["packets"]["O_diff"]["key"], "outcome": "scored", "score": 50, "cost_usd": 0.01}) + "\n")
    ro = {r["unit_id"]: r for r in d.build_scores(app, {"stopped": None})["rows"] if r["view"] == "O_diff" and r["judge"] == "sol"}
    assert ro["a:item0:1"]["flag"] == ro["a:item0:1"]["flag_unit"] == th.is_flagged(50.0, rule_u, uo[0]["packets"]["O_diff"]["label"]) and ro["a:item0:1"]["union_max"] is None
    # G7: one errored record keeps the unit open (the cell incomplete); a second makes it unscored, which completes the cell
    st = d.cell_status(app, d.ad.ISO, "opus48")
    assert st["errored_once"] == 1 and st["errored_final"] == 0 and st["errored_only"] == 1 and st["missing"] == 2 and not st["complete"]
    with cp.open("a") as fh:
        for u in us[2:]:
            fh.write(json.dumps({"cache_key": u["packets"][d.ad.ISO]["key"], "outcome": "errored", "score": None, "cost_usd": 0.01}) + "\n")
    st = d.cell_status(app, d.ad.ISO, "opus48")
    assert st["errored_once"] == 2 and st["errored_final"] == 1 and st["missing"] == 0 and not st["complete"]    # b:item0:1 has two records now; the lines one each
    with cp.open("a") as fh:
        for u in us[3:]:
            fh.write(json.dumps({"cache_key": u["packets"][d.ad.ISO]["key"], "outcome": "errored", "score": None, "cost_usd": 0.01}) + "\n")
    st = d.cell_status(app, d.ad.ISO, "opus48")
    assert st["errored_once"] == 0 and st["errored_final"] == 3 and st["missing"] == 0 and st["complete"]


def test_continue_clears_a_recorded_stop_and_counts_g7_only_continues_per_cell():
    run = {"stopped": {"reason": "x", "cell": "c", "ts": "t"}}
    d.clear_stop(run)
    assert run["stopped"] is None and run["stops_cleared"][0]["reason"] == "x" and "cleared" in run["stops_cleared"][0] and "g7_continues" not in run
    run["stopped"] = {"reason": "y", "cell": "c", "g7_only": True, "errored_once": 2, "missing": 0, "ts": "t"}
    d.clear_stop(run)
    run["stopped"] = {"reason": "z", "cell": "c", "g7_only": True, "errored_once": 1, "missing": 0, "ts": "t"}
    d.clear_stop(run)
    run["stopped"] = {"reason": "w", "cell": "e", "g7_only": False, "errored_once": 1, "missing": 3, "ts": "t"}
    d.clear_stop(run)
    assert run["g7_continues"] == {"c": 2} and len(run["stops_cleared"]) == 4 and run["stopped"] is None


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


# ── brief 33's dated notes 4 and 5: G7, G9 and the Stage B refusals ───────────────────────────────

def _cache_with(monkeypatch, tmp_path):
    app = _app()
    monkeypatch.setattr(d, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(d, "APPLICATIONS", tmp_path / "app.json")
    (tmp_path / "app.json").write_text("{}")
    monkeypatch.setattr(d, "sealed_rule", lambda v, j: {"kind": "author", "seed": 20261112, "threshold": 50.0, "p_tie": 0.5})
    monkeypatch.setattr(d, "honest_pairs_for", lambda v, j: {})
    us = d.cell_units(app, d.ad.ISO, "opus48")
    cp = d.cache_path(d.ad.ISO, "opus48")
    return app, us, cp


def _err(cp, u):
    with cp.open("a") as fh:
        fh.write(json.dumps({"cache_key": u["packets"][d.ad.ISO]["key"], "outcome": "errored", "score": None, "cost_usd": 0.01}) + "\n")


def test_one_errored_record_keeps_the_cell_open_and_the_stopped_file_names_it_g7(monkeypatch, tmp_path):
    app, us, cp = _cache_with(monkeypatch, tmp_path)
    cp.write_text("\n".join(json.dumps({"cache_key": u["packets"][d.ad.ISO]["key"], "outcome": "scored", "score": 40, "cost_usd": 0.01}) for u in us[1:]) + "\n")
    _err(cp, us[0])
    st = d.cell_status(app, d.ad.ISO, "opus48")
    assert st == {**st, "n_units": 5, "completed": 4, "errored_once": 1, "errored_final": 0, "errored_only": 1, "missing": 0, "complete": False}
    sc = d.build_scores(app, {"stopped": {"reason": "cell incomplete", "cell": "P_author_doc_iso|opus48", "g7_only": True}})
    cell = sc["cells"]["P_author_doc_iso|opus48"]
    assert cell["errored_open"] == 1 and cell["errored"] == 0 and cell["scored"] == 4
    assert sc["stopped"]["incomplete_rows"]["P_author_doc_iso|opus48"] == {"scored_rows": 4, "of": 5}
    # the open unit's row is not in a stopped file (the row is named by the stop record, not read); the other cells' missing rows neither
    assert not any(r["unit_id"] == us[0]["unit_id"] and r["view"] == "P_author_doc_iso" for r in sc["rows"])
    assert all(r["outcome"] not in ("missing", "errored_open") for r in sc["rows"]) and len(sc["rows"]) == 4
    # a file that is not stopped carries the open row, marked
    sc = d.build_scores(app, {"stopped": None})
    row = next(r for r in sc["rows"] if r["unit_id"] == us[0]["unit_id"] and r["view"] == "P_author_doc_iso")
    assert row["outcome"] == "errored_open" and row["score"] is None and row["flag"] is None and row["flag_unit"] is None


def test_a_second_errored_record_makes_the_unit_unscored_and_completes_the_cell_g7(monkeypatch, tmp_path):
    app, us, cp = _cache_with(monkeypatch, tmp_path)
    cp.write_text("\n".join(json.dumps({"cache_key": u["packets"][d.ad.ISO]["key"], "outcome": "scored", "score": 40, "cost_usd": 0.01}) for u in us[1:]) + "\n")
    _err(cp, us[0])
    _err(cp, us[0])
    st = d.cell_status(app, d.ad.ISO, "opus48")
    assert st["errored_once"] == 0 and st["errored_final"] == 1 and st["missing"] == 0 and st["complete"]
    sc = d.build_scores(app, {"stopped": None})
    row = next(r for r in sc["rows"] if r["unit_id"] == us[0]["unit_id"] and r["view"] == "P_author_doc_iso")
    assert row["outcome"] == "errored" and sc["cells"]["P_author_doc_iso|opus48"]["errored"] == 1 and sc["cells"]["P_author_doc_iso|opus48"]["errored_open"] == 0
    assert "P_author_doc_iso|opus48" not in {c for c, v in sc["cells"].items() if v["scored"] + v["refused"] + v["errored"] < v["n_units"]}
    # a scored record after the errors wins: the unit is scored, not errored
    with cp.open("a") as fh:
        fh.write(json.dumps({"cache_key": us[0]["packets"][d.ad.ISO]["key"], "outcome": "scored", "score": 60, "cost_usd": 0.01}) + "\n")
    st = d.cell_status(app, d.ad.ISO, "opus48")
    assert st["errored_final"] == 0 and st["completed"] == 5 and st["complete"]


def _run_cells_with(monkeypatch, tmp_path, status):
    app = _app()
    render = {"rows": {"|".join(c): {"s2_basis_per_unit": 0.01, "estimate": {"est_cost_usd": 1.0, "n_calls": 1}} for c in d.ORDER}, "applications_sha256": "x"}
    run = {"cells": {}, "first_batch": {"done": True}, "stopped": None}
    monkeypatch.setattr(d, "cell_status", lambda a, v, j: dict(status))
    monkeypatch.setattr(d, "make_client", lambda *a, **k: type("J", (), {"batch_log": lambda self, p, note=None: None})())

    async def fake_score(jc, view, units, ledger, basis, concurrency=4):
        return {}, None
    monkeypatch.setattr(d, "score_units", fake_score)
    monkeypatch.setattr(d, "write_json", lambda p, o: "h")
    monkeypatch.setattr(d, "write_scores", lambda a, r: "h")
    monkeypatch.setattr(d, "dollars_all", lambda: {"total": 0.0})
    monkeypatch.setattr(d, "CACHE_DIR", tmp_path)

    class NS:
        cont = True
        concurrency = 4
        rpm = 30
    rc = asyncio.run(d.run_cells(NS(), app, render, run))
    return rc, run


def test_the_stop_at_a_cells_end_says_whether_g7s_errored_units_are_its_only_cause(monkeypatch, tmp_path):
    base = {"complete": False, "n_units": 5, "completed": 4, "scored": 4, "refused": 0, "errored_only": 1, "errored_final": 0, "dollars": 1.0}
    rc, run = _run_cells_with(monkeypatch, tmp_path, {**base, "errored_once": 1, "missing": 0})
    assert rc == 1 and run["stopped"]["g7_only"] is True and run["stopped"]["errored_once"] == 1 and run["stopped"]["missing"] == 0 and "G7" in run["stopped"]["reason"]
    rc, run = _run_cells_with(monkeypatch, tmp_path, {**base, "errored_once": 1, "missing": 2})
    assert rc == 1 and run["stopped"]["g7_only"] is False
    rc, run = _run_cells_with(monkeypatch, tmp_path, {**base, "errored_once": 0, "missing": 1})
    assert rc == 1 and run["stopped"]["g7_only"] is False


def _hp(*pairs):
    return {(a, p): 50.0 for a, p in pairs}


def test_g9_checks_the_unions_keys_by_cause_and_refuses_only_an_unexplained_absence():
    app = _app()                                   # authors aa and ab on /shared/d.md
    other = "/shared/other.md"
    present = _hp(("aa", other), ("ab", "/shared/d.md"), ("zz", other), ("zz", "/shared/d.md"))
    cells = {(v, j): present for v, j in d.ORDER if v != "O_diff"}
    r = d.honest_pairs_check(app, cells, {"aa": 2, "ab": 1, "zz": 3}, {"aa", "ab", "zz"})
    c = r["cells"]["P_author_doc_iso|opus48"]
    assert r["pass"] and r["refusals"] == [] and c["authors_absent"] == 0 and c["documents_absent"] == 0 and c["author_key_mismatches"] == 0
    assert c["units"] == 5 and c["unit_authors"] == 2 and c["honest_authors"] == 3 and c["honest_documents"] == 2
    # ab's single honest pair sits on the planted document: its one unit has no other pair, explained by that cause; aa's four units have one
    assert c["units_with_no_other_pair"] == 1 and c["of_which_single_pair_on_the_planted_document"] == 1 and c["of_which_author_absent_explained"] == 0 and c["of_which_unexplained"] == 0
    assert c["units_by_n_other_pairs"] == {"0": 1, "1": 4} and r["author_set_identical_across_sources"] and r["path_set_identical_across_sources"]
    assert r["cells"]["P_author_doc_live|opus48"]["units"] == 3 and r["cells"]["P_author_doc_live|opus48"]["units_by_n_other_pairs"] == {"0": 1, "1": 2}
    # ab absent from every source, an account with no class-document write: explained, no refusal, the count recorded
    absent = _hp(("aa", other), ("zz", other), ("zz", "/shared/d.md"))
    r = d.honest_pairs_check(app, {k: absent for k in cells}, {"aa": 2, "zz": 3}, {"aa", "ab", "zz"})
    c = r["cells"]["P_author|sonnet"]
    assert r["pass"] and c["authors_absent"] == 1 and c["authors_absent_explained_no_class_write"] == 1 and c["authors_absent_unexplained"] == 0
    assert c["units_by_absent_explained_author"] == 1 and c["units_with_no_other_pair"] == 1 and c["of_which_author_absent_explained"] == 1
    # the same author with a class-document write in the honest corpus: unexplained, a refusal
    r = d.honest_pairs_check(app, {k: absent for k in cells}, {"aa": 2, "ab": 1, "zz": 3}, {"aa", "ab", "zz"})
    assert not r["pass"] and len(r["refusals"]) == 6 and r["cells"]["P_author_doc_live|sonnet"]["authors_absent_unexplained"] == 1 and r["cells"]["P_author_doc_live|sonnet"]["of_which_unexplained"] == 1
    # an author string that is no account of the honest corpus at all: unexplained (a format mismatch would look exactly like this)
    r = d.honest_pairs_check(app, {k: absent for k in cells}, {"aa": 2, "zz": 3}, {"aa", "zz"})
    assert not r["pass"] and r["cells"]["P_author_doc_iso|opus48"]["authors_absent_unexplained"] == 1
    # a planted document absent from a source's paths: a refusal
    bad_doc = _hp(("aa", other), ("ab", other), ("zz", other))
    r = d.honest_pairs_check(app, {k: bad_doc for k in cells}, {"aa": 2, "ab": 1, "zz": 3}, {"aa", "ab", "zz"})
    assert not r["pass"] and r["cells"]["P_author_doc_iso|opus48"]["documents_absent"] == 1 and r["cells"]["P_author_doc_iso|opus48"]["units_with_no_other_pair"] == 0
    # an author whose honest pairs lie elsewhere but not on another document than the planted one is impossible by construction; a mismatch between
    # the packet's author and the unit's author is a refusal
    app2 = _app()
    app2["units"]["b:item0:1"]["author"] = "not-aa"
    r = d.honest_pairs_check(app2, cells, {"aa": 2, "ab": 1, "zz": 3}, {"aa", "ab", "zz"})
    assert not r["pass"] and r["cells"]["P_author_doc_iso|opus48"]["author_key_mismatches"] == 1
    # nothing but counts in the output
    assert not any(isinstance(v, str) and ("/shared" in v or v in ("aa", "ab", "zz")) for cell in r["cells"].values() for v in cell.values())


def test_score_refuses_without_the_clean_items_file_at_its_hash_and_without_a_passing_g9_check(monkeypatch, tmp_path):
    monkeypatch.setattr(d, "preflight", lambda p: None)
    app = tmp_path / "app.json"
    app.write_text("{}")
    monkeypatch.setattr(d, "APPLICATIONS", app)
    render = tmp_path / "render.json"
    render.write_text(json.dumps({"applications_sha256": d.sha256_file(app), "rows": {}}))
    monkeypatch.setattr(d, "RENDER", render)
    monkeypatch.setattr(d, "CLEAN_ITEMS", tmp_path / "clean.json")
    monkeypatch.setattr(d, "HONEST_CHECK", tmp_path / "check.json")
    monkeypatch.setattr(d, "RUN", tmp_path / "run.json")
    monkeypatch.setattr(d, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(d, "LOCK_FILE", tmp_path / "cache" / ".s3-run.lock")

    class NS:
        config = str(d.CONFIG)
        cont = False
        concurrency = 4
        rpm = 30
    with pytest.raises(SystemExit, match="clean-items"):
        d.mode_score(NS())
    (tmp_path / "clean.json").write_text('{"touched_ids": []}\n')
    with pytest.raises(SystemExit, match="clean-items"):
        d.mode_score(NS())
    monkeypatch.setattr(d, "CLEAN_ITEMS", d.B3 / "s3-clean-items-v0.json")      # the committed file, 21e7ede2, read only
    assert d.sha256_file(d.CLEAN_ITEMS).startswith(d.CLEAN_ITEMS_SHA256)
    with pytest.raises(SystemExit, match="G9"):
        d.mode_score(NS())
    (tmp_path / "check.json").write_text(json.dumps({"pass": False, "applications_sha256": d.sha256_file(app)}))
    with pytest.raises(SystemExit, match="G9"):
        d.mode_score(NS())
    (tmp_path / "check.json").write_text(json.dumps({"pass": True, "applications_sha256": "other"}))
    with pytest.raises(SystemExit, match="G9"):
        d.mode_score(NS())
    (tmp_path / "check.json").write_text(json.dumps({"pass": True, "applications_sha256": d.sha256_file(app)}))
    monkeypatch.setattr(d, "run_cells", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("reached the controller")))
    with pytest.raises(RuntimeError, match="reached the controller"):
        d.mode_score(NS())                                                    # every refusal passed; the run would start
    assert not (tmp_path / "cache" / ".s3-run.lock").exists()


def test_an_errored_final_unit_is_never_asked_again_g10(monkeypatch, tmp_path):
    app, us, cp = _cache_with(monkeypatch, tmp_path)
    cp.write_text(json.dumps({"cache_key": us[1]["packets"][d.ad.ISO]["key"], "outcome": "scored", "score": 40, "cost_usd": 0.01}) + "\n")
    _err(cp, us[0])
    _err(cp, us[0])                                   # us[0] errored_final: unscored under G7
    _err(cp, us[2])                                   # us[2] errored once: open, asked again
    ask = [u["unit_id"] for u in d.askable_units(app, d.ad.ISO, "opus48")]
    assert ask == [us[2]["unit_id"], us[3]["unit_id"], us[4]["unit_id"]]     # not the scored one, not the final one; cell order kept
    # through run_cells: the units handed to score_units are exactly the askable ones
    render = {"rows": {"|".join(c): {"s2_basis_per_unit": 0.01, "estimate": {"est_cost_usd": 1.0, "n_calls": 1}} for c in d.ORDER}, "applications_sha256": "x"}
    run = {"cells": {}, "first_batch": {"done": True}, "stopped": None}
    seen = []

    async def fake_score(jc, view, units, ledger, basis, concurrency=4):
        seen.append([u["unit_id"] for u in units])
        return {}, None
    monkeypatch.setattr(d, "score_units", fake_score)
    monkeypatch.setattr(d, "make_client", lambda *a, **k: type("J", (), {"batch_log": lambda self, p, note=None: None})())
    monkeypatch.setattr(d, "write_json", lambda p, o: "h")
    monkeypatch.setattr(d, "write_scores", lambda a, r: "h")
    monkeypatch.setattr(d, "dollars_all", lambda: {"total": 0.0})

    class NS:
        cont = True
        concurrency = 4
        rpm = 30
    rc = asyncio.run(d.run_cells(NS(), app, render, run))
    assert rc == 1 and seen == [ask] and run["stopped"]["cell"] == "P_author_doc_iso|opus48" and run["stopped"]["errored_once"] == 1 and run["stopped"]["missing"] == 2
