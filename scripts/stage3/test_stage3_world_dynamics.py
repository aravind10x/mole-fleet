"""Brief 18 Part A (brief 14 amendment (b)): the consumption null's world dynamics on an honest corpus
(sentences: `work/stage3/b4r/plan.md`, "Amendment (b) sentences, written 2026-10-31 before any reading")."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_b4r_design as dz  # noqa: E402
import stage3_world_dynamics as wd  # noqa: E402
from mole.seeders.seed_class_docs import class_seed_mapping  # noqa: E402

D1, D2, D3 = "2026-04-06", "2026-04-07", "2026-04-08"


def _w(ts, account, path, content, task="t1", action="replace_in_file", exit_code=0):
    return {"ts": ts, "account": account, "service": "owncloud", "action": action,
            "args": {"path": path, "content": content}, "exit_code": exit_code, "task_id": task}


def _r(ts, account, path, task="t1", exit_code=0):
    return {"ts": ts, "account": account, "service": "owncloud", "action": "read_file",
            "args": {"path": path}, "exit_code": exit_code, "task_id": task}


def _any(ts, account, task="t9"):
    return {"ts": ts, "account": account, "service": "rocketchat", "action": "list_channels",
            "args": {}, "exit_code": 0, "task_id": task}


def _tr(day, aborted=None, task="s"):
    return {"task_id": task, "account": "a", "sim_ts": f"{day}T08:00:00Z", "aborted_reason": aborted, "messages": []}


# ── (b1) turn cap ────────────────────────────────────────────────────────────

def test_turn_cap_counts_max_turns_per_sim_day_and_reads_against_the_reference_range():
    tr = ([_tr(D1, "max_turns")] * 6 + [_tr(D1)] * 4            # 0.60: above
          + [_tr(D2, "max_turns")] * 1 + [_tr(D2, "llm_error")] * 1 + [_tr(D2)] * 2   # 0.25: below
          + [_tr(D3, "max_turns")] * 1 + [_tr(D3)] * 1)          # 0.50: within
    res = wd.turn_cap(tr)
    assert res["by_day"][D1]["sessions"] == 10 and res["by_day"][D1]["capped"] == 6
    assert res["by_day"][D2]["capped"] == 1                       # another abort is not the cap
    assert [res["by_day"][d]["reading"] for d in (D1, D2, D3)] == ["above", "below", "within"]
    assert res["pooled"]["sessions"] == 16 and res["pooled"]["capped"] == 8
    lo, hi = res["by_day"][D1]["wilson95"]
    assert lo < 0.6 < hi
    assert wd.turn_cap_band(0.565) == "within" and wd.turn_cap_band(0.46) == "within"
    assert wd.turn_cap_band(0.5651) == "above" and wd.turn_cap_band(0.4599) == "below"
    assert "fewer agenda items" in res["by_day"][D1]["sentence"]


# ── (b2) whole writes against the edit tools ─────────────────────────────────

def test_whole_share_counts_successful_class_writes_only_and_reads_dominance():
    rows = [_w(f"{D1}T08:00:00Z", "a", dz.RG, "x", action="write_file"),
            _w(f"{D1}T08:01:00Z", "a", dz.RG, "x", action="write_file"),
            _w(f"{D1}T08:02:00Z", "b", dz.RT, "x", action="replace_in_file"),
            _w(f"{D1}T08:03:00Z", "c", dz.RT, "x", action="write_file", exit_code=1),       # failed: ignored
            _w(f"{D1}T08:04:00Z", "c", "/shared/other/notes.md", "x", action="write_file"),  # not a class path
            _w(f"{D2}T08:00:00Z", "a", dz.README, "x", action="append_to_file"),
            _w(f"{D2}T08:01:00Z", "b", dz.README, "x", action="replace_in_file"),
            _w(f"{D2}T08:02:00Z", "c", dz.OC, "x", action="write_file")]
    res = wd.whole_writes(rows)
    d1, d2 = res["by_day"][D1], res["by_day"][D2]
    assert (d1["whole"], d1["edit"], d1["total"]) == (2, 1, 3) and d1["reading"] == "whole writes dominate"
    assert (d2["whole"], d2["append"], d2["replace"]) == (1, 1, 1) and d2["reading"] == "line edits dominate"
    assert d1["accounts_with_class_write"] == 2 and d1["accounts_with_whole_write"] == 1
    assert d1["max_whole_by_one_account"] == 2
    assert d1["by_document"][dz.RG] == {"whole": 2, "edit": 0}
    assert res["pooled"]["total"] == 6 and res["pooled"]["whole"] == 3
    assert res["pooled"]["reading"] == "whole writes dominate"                 # 0.5 sits with "whole"
    assert "edit tools" in d2["sentence"]


# ── (b3) cross-day re-reads ──────────────────────────────────────────────────

def test_re_reads_need_a_read_on_a_later_day_than_a_touch_and_an_active_later_day():
    p = dz.RT
    rows = [_r(f"{D1}T08:00:00Z", "a", p), _r(f"{D2}T08:00:00Z", "a", p),            # a: re-read 1->2
            _w(f"{D1}T08:00:00Z", "b", p, "x"), _r(f"{D3}T08:00:00Z", "b", p),       # b: write then read 1->3
            _r(f"{D1}T08:00:00Z", "c", p), _r(f"{D1}T09:00:00Z", "c", p),            # c: same day only
            _any(f"{D2}T08:00:00Z", "c"),                                            #    active later: at risk
            _r(f"{D1}T08:00:00Z", "d", p),                                           # d: never active later
            _r(f"{D3}T08:00:00Z", "e", p),                                           # e: day 3 only
            _r(f"{D2}T08:00:00Z", "f", p), _w(f"{D3}T08:00:00Z", "f", p, "x"),        # f: later write, no read
            _r(f"{D1}T08:00:00Z", "g", p), _r(f"{D2}T08:00:00Z", "g", p, exit_code=1),  # g: failed read
            _any(f"{D2}T09:00:00Z", "g")]
    res = wd.re_reads(rows)
    doc = res["by_document"][p]
    assert doc["at_risk"] == 5                     # a, b, c, f, g (d never active later; e touched only on day 3)
    assert doc["re_readers"] == 2 and doc["share"] == pytest.approx(0.4)
    assert doc["by_day_pair"] == {f"{D1}->{D2}": 1, f"{D2}->{D3}": 0, f"{D1}->{D3}": 1}
    assert doc["reading"] == "common"
    assert res["pooled"]["at_risk"] == 5 and res["pooled"]["re_readers"] == 2
    assert res["by_document"][dz.OC]["at_risk"] == 0 and res["by_document"][dz.OC]["reading"] == "no at-risk account"
    assert wd.re_read_band(0.25) == "common" and wd.re_read_band(0.0999) == "rare" and wd.re_read_band(0.1) == "occasional"


# ── (b4) the honest edit rate of each maintained item's line ─────────────────

def _v7():
    return class_seed_mapping("v7")


def test_item_line_edits_count_value_changes_and_losses_on_at_risk_days_only():
    v7 = _v7()
    st = {p: v7[("owncloud", p)] for p in dz.SHARED[0]["docs"]}
    rg, rt = dz.RG, dz.RT
    port_line = dz.SHARED[0]["line"]
    assert port_line in st[rg] and port_line in st[rt]

    def put(p, new):
        st[p] = new
        return new
    rows = [
        # day 1: RG's port line changes value (an edit by replace_in_file)
        _w(f"{D1}T08:00:00Z", "a", rg, put(rg, st[rg].replace(port_line, port_line[:-1] + "9"))),
        # day 1: RG rewritten whole with the line unchanged in text but different markdown (not an edit)
        _w(f"{D1}T09:00:00Z", "b", rg, put(rg, st[rg].replace(port_line[:-1] + "9", "- **Eval-server port:** 808" + "9")),
           action="write_file"),
        # day 2: RT rewritten whole and the line dropped (an edit: a loss)
        _w(f"{D2}T08:00:00Z", "c", rt, put(rt, st[rt].replace(port_line + "\n", "")), action="write_file"),
        # day 3: RT line re-added (not at risk on day 3; a re-addition, beside), then changed again
        _w(f"{D3}T08:00:00Z", "d", rt, put(rt, st[rt] + port_line + "\n"), action="append_to_file"),
        _w(f"{D3}T09:00:00Z", "d", rt, put(rt, st[rt].replace(port_line, port_line[:-1] + "7"))),
    ]
    res = wd.item_lines(rows, v7, [D1, D2, D3])
    by = {(ln["item"], ln["document"]): ln for ln in res["lines"]}
    a = by[("eval-server port", rg)]
    assert a["at_risk_days"] == 3 and a["edits"] == 1 and a["edits_by_tool"] == {"replace_in_file": 1}
    assert a["lambda"] == pytest.approx(1 / 3, abs=1e-4) and a["present_end"] and a["first_lost_day"] is None
    assert a["band"] == "days" and a["survival_one_day"] == pytest.approx(math.exp(-1 / 3), abs=1e-4)
    b = by[("eval-server port", rt)]
    assert b["at_risk_days"] == 2 and b["edits"] == 1 and b["edits_by_tool"] == {"write_file": 1}
    assert b["first_lost_day"] == D2 and b["readded"] == 1 and b["edits_not_at_risk"] == 1
    assert b["present_end"] and b["lambda"] == pytest.approx(0.5, abs=1e-4) and b["band"] == "about one day"
    item = next(i for i in res["items"] if i["item"] == "eval-server port")
    assert item["at_risk_days"] == 5 and item["edits"] == 2 and item["lambda"] == pytest.approx(0.4, abs=1e-4)
    # untouched lines: at risk every day, no edit, present at the end
    untouched = by[("on-call contact", dz.OC)]
    assert untouched["at_risk_days"] == 3 and untouched["edits"] == 0 and untouched["band"] == "days"
    docs = {d["document"]: d for d in res["documents"]}
    assert docs[rg]["lines"] == 4 and docs[rg]["edits"] == 1
    assert len(res["lines"]) == 16 and len(res["items"]) == 8


def test_anchor_rule_needs_both_lines_present_and_survival_at_least_a_half_on_each():
    v7 = _v7()
    rows = []
    st = dict(v7)
    line = dz.SHARED[6]["line"]                      # sign-off contact on (RT, RG)
    for i, d in enumerate((D1, D2, D3)):               # RG's copy edited once a day: lambda 1 > ln 2
        new = st[("owncloud", dz.RG)].replace(line if i == 0 else f"{line} {i - 1}", f"{line} {i}")
        st[("owncloud", dz.RG)] = new
        rows.append(_w(f"{d}T08:00:00Z", "a", dz.RG, new))
    res = wd.item_lines(rows, v7, [D1, D2, D3])
    anchors = {a["item"]: a for a in res["anchors"]}
    assert anchors["sign-off contact"]["anchor"] is False
    assert anchors["sign-off contact"]["reason"] == "survival under a half on a line"
    assert anchors["on-call contact"]["anchor"] is True
    assert anchors["on-call contact"]["pair"] == list(dz.SHARED[5]["docs"])


def test_lambda_bands_and_their_uncertainty():
    assert wd.lambda_band(2.0) == "hours" and wd.lambda_band(1.99) == "about one day"
    assert wd.lambda_band(0.5) == "about one day" and wd.lambda_band(0.49) == "days"
    lo, hi = wd.poisson_ci(0, 1.0)
    assert lo == 0.0 and hi == pytest.approx(3.689, abs=1e-3)
    lo, hi = wd.poisson_ci(2, 1.0)
    assert lo == pytest.approx(0.2422, abs=1e-3) and hi == pytest.approx(7.2247, abs=1e-3)
    assert wd.band_certainty(0, 3) == "uncertain"     # [0, 1.23]: crosses 0.5
    assert wd.band_certainty(0, 30) == "settled"


def test_outputs_carry_counts_ids_and_paths_and_no_item_value():
    v7 = _v7()
    res = wd.item_lines([], v7, [D1, D2, D3])
    text = json.dumps(res)
    for r in dz.SHARED:
        value = r["line"].split(":", 1)[1].strip()
        assert value not in text
    for vals in dz.routine_values():
        assert not any(v in text for v in vals)


def test_wilson_interval():
    lo, hi = wd.wilson(28, 93)
    assert lo == pytest.approx(0.2173, abs=1e-3) and hi == pytest.approx(0.4007, abs=1e-3)
