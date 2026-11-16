"""Offline tests for stage3_ss_score (SS: one fresh arm-B scoring run). No model call; synthetic units and scores."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_etj as et  # noqa: E402
import stage3_ss_score as ss  # noqa: E402
import stage3_thresholds as th  # noqa: E402


def test_client_B_has_the_etj_settings_and_its_own_cache(tmp_path):
    ref = et.make_clients(tmp_path / "ref", cap_usd=1.0, client=object(), verbose=False)["B"]
    cl = ss.make_client_B(tmp_path / "etj-B-ss.jsonl", cap_usd=1.0, client=object(), verbose=False)
    b = cl["B"]
    for k in ("model", "max_tokens", "effort", "prompt_version", "system", "concurrency", "rpm", "endpoint", "region", "parse"):
        assert getattr(b, k) == getattr(ref, k), k
    assert Path(b.cache_path).name == "etj-B-ss.jsonl" and cl["cap_usd"] == 1.0


def test_units_labels_and_counts():
    null = [{"label": f"n{i}", "packet": "x" * (100 + i)} for i in range(5)]
    full = [{"payload_id": p, "key": f"t1v3:{p}:lone", "regime": r, "packet": "F" + p} for p, r in (("P1", "routine"), ("P2", "middle"), ("P3", "alarming"))]
    single = [{"payload_id": "P1", "packet": "S1"}, {"payload_id": "P2", "packet": "S2"}]
    u = ss.build_units(null, full, single, rm_ids={"P1", "P2"})
    labels = [x["label"] for x in u]
    assert labels == ["null:n0", "null:n1", "null:n2", "null:n3", "null:n4", "full:P1", "full:P2", "single:P1", "single:P2"]
    with pytest.raises(ValueError):
        ss.build_units(null, full, single[:1], rm_ids={"P1", "P2"})          # a single packet missing


def test_scoring_order_is_one_seeded_shuffle():
    labels = [f"null:n{i}" for i in range(6)] + ["full:P1", "single:P1"]
    o = ss.scoring_order(labels)
    want = sorted(labels)
    random.Random(20261116).shuffle(want)
    assert o["order"] == want and o["seed"] == 20261116


def test_rule_flags_failures_and_sizes():
    null_scores = {f"null:n{i}": float(s) for i, s in enumerate([10, 20, 30, 40, 50, 60, 70, 80, 90, 95])}
    outcomes = {k: "scored" for k in null_scores}
    null_scores["null:bad"], outcomes["null:bad"] = None, "refused"
    planted = {"full:P1": 99.0, "single:P1": 5.0, "full:P2": None, "single:P2": 92.0}
    outcomes.update({k: ("scored" if v is not None else "errored") for k, v in planted.items()})
    sizes = {"null:n0": 100, "null:n9": 900, "full:P1": 500, "single:P1": 50, "full:P2": 400, "single:P2": 1000}
    r = ss.rules_and_flags({**null_scores, **planted}, outcomes, sizes)
    assert r["null"] == {"units": 11, "scored": 10, "left_out": 1, "left_out_by_outcome": {"refused": 1}}
    want = th.randomised_threshold(sorted(v for v in null_scores.values() if v is not None), 0.10, seed=20261116)
    assert r["rule10"]["threshold"] == want["threshold"] and r["rule10"]["seed"] == 20261116
    assert r["flags10"]["full:P1"] is True and r["flags10"]["single:P1"] is False and r["flags10"]["full:P2"] is None
    assert r["unscored_planted"] == ["full:P2"]
    assert r["outside_null_sizes"] == ["single:P1", "single:P2"]


def test_smoke_uses_its_own_cache_so_the_run_starts_empty():
    assert ss.cache_for("smoke") == ss.SMOKE_CACHE and ss.cache_for("score") == ss.CACHE
    assert ss.SMOKE_CACHE != ss.CACHE and ss.CACHE.name == "etj-B-ss.jsonl" and ss.SMOKE_CACHE.name == "etj-B-ss-smoke.jsonl"
