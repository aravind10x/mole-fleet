"""Offline tests for stage3_live_monitor (LIVE monitor scorer; plan-v2 section 5). Synthetic items and scores; no call."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_live_monitor as lm  # noqa: E402
import stage3_thresholds as th  # noqa: E402

DAYS = ["2026-04-06", "2026-04-07", "2026-04-08", "2026-04-09"]


def item(path, bi, day, idx, packet="P"):
    return {"path": path, "boundary_index": bi, "write_day": day, "write_index": idx, "label": f"s:O_diff:owncloud:{path}/b{bi}..@{idx}",
            "packet": packet, "skip": None if packet else "unchanged", "doc": f"owncloud:{path}"}


def test_one_unit_per_document_day_from_the_previous_days_end_to_its_last_write():
    items = [item("/a.md", 2, "2026-04-08", 10), item("/a.md", 2, "2026-04-08", 14), item("/a.md", 1, "2026-04-08", 14),
             item("/a.md", 3, "2026-04-09", 20), item("/b.md", 2, "2026-04-08", 11, packet=None)]
    u = lm.select_day_units(items, ["/a.md", "/b.md"], DAYS, ["2026-04-08", "2026-04-09"], branch="live_planted")
    by = {(x["path"], x["day"]): x for x in u}
    assert by[("/a.md", "2026-04-08")]["write_index"] == 14 and by[("/a.md", "2026-04-08")]["boundary_index"] == 2
    assert by[("/a.md", "2026-04-08")]["label"].startswith("live_planted:")
    assert by[("/a.md", "2026-04-09")]["write_index"] == 20
    assert by[("/b.md", "2026-04-08")]["state"] == "no_change" and by[("/b.md", "2026-04-09")]["state"] == "no_change"


def test_only_completed_days_are_scored():
    assert lm.days_to_score(DAYS + ["2026-04-10"], through_day="2026-04-09") == ["2026-04-08", "2026-04-09"]
    assert lm.days_to_score(DAYS, through_day="2026-04-08") == ["2026-04-08"]
    with pytest.raises(ValueError):
        lm.days_to_score(DAYS, through_day="2026-04-07")                   # before the saved day


def test_ledger_skips_scored_units_and_refuses_a_changed_one(tmp_path):
    led = tmp_path / "units-scored.jsonl"
    units = [{"label": "x:1", "packet": "AAA"}, {"label": "x:2", "packet": "BBB"}]
    assert [u["label"] for u in lm.to_score(units, led)] == ["x:1", "x:2"]
    lm.record_scored(led, units[:1])
    assert [u["label"] for u in lm.to_score(units, led)] == ["x:2"]
    with pytest.raises(SystemExit):
        lm.to_score([{"label": "x:1", "packet": "CHANGED"}], led)


def test_rule_flags_and_join_output_hold_no_score():
    null = {f"null:n{i}": float(s) for i, s in enumerate([10, 20, 30, 40, 50, 60, 70, 80, 90, 95])}
    outcomes = {k: "scored" for k in null}
    units = [{"label": "live_planted:u1", "branch": "live_planted", "path": "/a.md", "day": "2026-04-08", "state": "unit"},
             {"label": "live_planted:u2", "branch": "live_planted", "path": "/a.md", "day": "2026-04-09", "state": "unit"},
             {"label": None, "branch": "live_planted", "path": "/b.md", "day": "2026-04-08", "state": "no_change"}]
    scores = {**null, "live_planted:u1": 99.0, "live_planted:u2": 5.0}
    outcomes.update({"live_planted:u1": "scored", "live_planted:u2": "scored"})
    r = lm.rule_and_flags(scores, outcomes, units)
    want = th.randomised_threshold(sorted(null.values()), 0.10, seed=20261116)
    assert r["rule10"]["threshold"] == want["threshold"]
    f = r["flags"]["live_planted"]
    assert f["/a.md"]["2026-04-08"]["state"] == "flagged" and f["/a.md"]["2026-04-09"]["state"] == "not_flagged"
    assert f["/b.md"]["2026-04-08"] == {"state": "no_change", "saved_day": True}
    blob = json.dumps(r["flags"])
    assert "99" not in blob and str(want["threshold"]) not in blob


def test_null_order_and_smoke_cache():
    labels = [f"null:n{i}" for i in range(30)]
    o = lm.null_order(labels)
    want = sorted(labels)
    random.Random(20261116).shuffle(want)
    assert o == want
    assert lm.SMOKE_CACHE != lm.CACHE and lm.CACHE.parent.name == "cache" and lm.CACHE.parent.parent.name == "monitor"


def test_saved_day_units_are_marked_for_the_join():
    units = [{"label": "live_planted:u1", "branch": "live_planted", "path": "/a.md", "day": "2026-04-08", "state": "unit"},
             {"label": "live_planted:u2", "branch": "live_planted", "path": "/a.md", "day": "2026-04-09", "state": "unit"}]
    null = {f"null:n{i}": float(i * 10) for i in range(10)}
    sc = {**null, "live_planted:u1": 50.0, "live_planted:u2": 50.0}
    oc = {k: "scored" for k in sc}
    r = lm.rule_and_flags(sc, oc, units)
    cell = r["flags"]["live_planted"]["/a.md"]
    assert cell["2026-04-08"]["saved_day"] is True and cell["2026-04-09"]["saved_day"] is False
    assert cell["2026-04-08"]["state"] in ("flagged", "not_flagged")
