"""Offline tests for judge_extra.py (brief 07p): the smoke pick, the estimate and re-base arithmetic, the
$25 cap and the $20 stop lines, the judge order, the prediction's reading, the overlap and correlation
helpers, and one scored set through an injected client. No network."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import judge_client as jc
import judge_extra as je
import judge_openrouter as jo
import stage3_views as sv

PRICES = {"prompt": 2.0 / 1e6, "completion": 10.0 / 1e6}
MODELS = {"price_source": "test", "judges": {j: {"pricing": {"prompt": "0.000002", "completion": "0.00001"}, "served": True,
                                                 "temperature_supported": False} for j in je.ORDER}}


def _item(label, n):
    return {"label": label, "packet": "x" * n, "key": jc.cache_key("O_diff", label, "x" * n)}


def _rec(outcome="scored", inp=1000, out=500, reasoning=300, cost=0.0):
    return {"outcome": outcome, "input_tokens": inp, "output_tokens": out, "reasoning_tokens": reasoning, "cost_usd": cost}


def test_smoke_pick_takes_the_length_quantiles():
    items = [_item(f"u{i:03d}", 100 + i) for i in range(100)] + [{"label": "skip", "packet": None, "key": "k"}]
    got = je.smoke_pick(items)
    assert [len(it["packet"]) for it in got] == [110, 130, 150, 170, 190]
    assert len(je.smoke_pick(items[:3])) == 3   # a short list gives distinct indices only


def test_estimate_arithmetic_and_refusal():
    sys_o = len(sv.system_prompt("O_diff", 0))
    sets = {"honest:O_diff": [_item("a", 1000), _item("b", 3000)]}
    recs = [_rec(inp=1000, out=400), _rec(inp=1000, out=600), _rec(inp=1000, out=500)]
    chars = [2000, 2000, 2000]                   # 2 chars per input token
    e = je.estimate_from_smoke(recs, chars, sets, PRICES)
    assert e["chars_per_input_token"] == 2.0 and e["output_tokens_per_call"] == 500.0
    in_tok = (4000 + 2 * sys_o) / 2.0
    assert e["estimates"]["honest:O_diff"]["est_cost_usd"] == round(in_tok * PRICES["prompt"] + 1000 * PRICES["completion"], 4)
    assert e["total_if_every_call_hit_max_tokens"] >= e["total_at_smoke_max_output"] >= e["total_est_usd"]
    with pytest.raises(SystemExit):
        je.estimate_from_smoke([_rec(), _rec("errored"), _rec("refused")], chars, sets, PRICES)


def test_rebase_projection_uses_provider_basis():
    # null: 2 O_diff units, list cost each = 1000*2e-6 + 500*1e-5 = 0.007; provider charged 0.014 each (ratio 2)
    null = {"O_diff": [_rec(cost=0.014), _rec(cost=0.014)]}
    nchars = {"O_diff": 4000}
    rem = {"v2:O_diff": [_item("p1", 2000 - len(sv.system_prompt("O_diff", 0)))]}   # 2000 chars with the system prompt
    r = je.rebase_projection(null, nchars, rem, PRICES)
    pv = r["per_view_null"]["O_diff"]
    assert pv["provider_over_list"] == 2.0 and pv["mean_output_tokens"] == 500.0
    # input: 2000 chars * (2000 tok * 2e-6 / 4000 chars); output: 500 * 1e-5; times 2
    assert r["projected"]["v2:O_diff"]["projected_usd"] == round(2 * (2000 * (2000 * 2e-6 / 4000) + 500 * 1e-5), 4)


def test_prediction_reading():
    ok = je.prediction(0.45, 0.4062, "interpretable", True)
    assert ok["held"] is True and ok["reading"] == "held" and ok["band"] == [0.2562, 0.5562]
    assert je.prediction(0.60, 0.4062, "interpretable", True)["reading"] == "not held (recall)"
    c = je.prediction(0.45, 0.4062, "interpretable, with caution", True)
    assert c["held"] is False and c["reading"] == "not held (sham)" and c["composed_recall_interpretable_as_content_detection"]
    n = je.prediction(0.45, 0.4062, "not interpretable", True)
    assert n["reading"] == "not held (sham)" and not n["composed_recall_interpretable_as_content_detection"]
    assert je.prediction(0.45, 0.4062, None, True)["held"] is None
    assert je.prediction(0.45, 0.4062, "interpretable", False)["reading"] == "not evaluable"
    assert je.prediction(0.4062 + 0.15, 0.4062, "interpretable", True)["held"] is True   # the band is closed


def test_overlap_and_corr():
    o = je.overlap(["C03", "C15"], ["C03", "C13"])
    assert o["overlap"] == ["C03"] and o["invisible_only_under_this_judge"] == ["C15"] and o["reference_not_invisible_under_this_judge"] == ["C13"]
    assert je.overlap(["C03"], None)["overlap"] is None
    c = je.corr({"a": 1, "b": 2, "c": 3, "d": 9}, {"a": 2, "b": 4, "c": 6, "e": 1})
    assert c["n_shared_scored"] == 3 and c["pearson"] == 1.0 and c["spearman"] == 1.0


def _write_cache(out_dir: Path, judge: str, tag: str, view: str, costs):
    p = je.cache_path(out_dir, view, judge, tag)
    with p.open("a") as f:
        for i, c in enumerate(costs):
            f.write(json.dumps({"cache_key": f"{view}|l{i}|h", "label": f"l{i}", "outcome": "scored", "score": 1, "cost_usd": c,
                                "model": je.JUDGES[judge]["id"], "prompt_version": sv.prompt_version(view, 0),
                                "request_params": {"max_tokens": jo.MAX_TOKENS, "system_sha256": jc.sha256(sv.system_prompt(view, 0))}}) + "\n")


def test_dollars_and_the_cap_span_every_07p_cache(tmp_path):
    _write_cache(tmp_path, "sol", je.TAG_V2, "O_diff", [3.0, 2.0])
    _write_cache(tmp_path, "sol", je.TAG_V3, "P_author", [1.5])
    _write_cache(tmp_path, "muse", je.TAG_V2, "O_diff", [4.0])
    # a 07n cache in the same directory does not count
    (tmp_path / "judge-cache.q1q2dep.O_diff.z-ai_glm-5-3.jsonl").write_text(json.dumps({"cost_usd": 99.0}) + "\n")
    d = je.dollars_so_far(tmp_path)
    assert d == {"sol": 6.5, "muse": 4.0, "total": 10.5}
    j = je.make_judge("O_diff", "sol", je.TAG_V2, tmp_path, MODELS, concurrency=1, rpm=0)
    assert j.dollars_cached == 5.0 and abs(j.spend_cap_usd - (5.0 + je.CAP_USD - 10.5)) < 1e-9


def test_judge_order(tmp_path):
    je.require_turn(tmp_path, "sol")
    with pytest.raises(SystemExit):
        je.require_turn(tmp_path, "muse")
    (tmp_path / "extra-judge-null.sol.json").write_text(json.dumps({"stop": True, "stopped_on": "O_diff"}))
    je.require_turn(tmp_path, "muse")
    with pytest.raises(SystemExit):
        je.require_turn(tmp_path, "sol")
    (tmp_path / "extra-judge-null.muse.json").write_text(json.dumps({"stop": True}))
    assert je.first_unstopped(tmp_path) is None   # no third judge


def test_reasoning_effort_guard(monkeypatch):
    monkeypatch.delenv("OPENROUTER_REASONING_EFFORT", raising=False)
    je.require_default_reasoning()
    monkeypatch.setenv("OPENROUTER_REASONING_EFFORT", "high")
    with pytest.raises(SystemExit):
        je.require_default_reasoning()


class Fake:
    def __init__(self, responses):
        self.responses = list(responses)

    async def complete(self, messages, *, temperature, max_tokens):
        return self.responses.pop(0)


def _resp(content, finish="stop", cost=0.01):
    return SimpleNamespace(content=content, finish_reason=finish,
                           usage=SimpleNamespace(input_tokens=100, output_tokens=50, reasoning_tokens=20, cost_usd=cost))


def test_score_set_through_an_injected_client(tmp_path, monkeypatch):
    fake = Fake([_resp('{"score": 40, "flag": false, "rationale": "r"}'), _resp("x", finish="content_filter")])
    monkeypatch.setattr(jo.OpenRouterJudge, "_get_client", lambda self: fake)
    items = [{"label": "a /shared/ops/oncall-runbook.md", "packet": "p1", "key": jc.cache_key("O_diff", "a /shared/ops/oncall-runbook.md", "p1")},
             {"label": "b /shared/ops/oncall-runbook.md", "packet": "p2", "key": jc.cache_key("O_diff", "b /shared/ops/oncall-runbook.md", "p2")}]
    ns = SimpleNamespace(judge="sol", concurrency=1, rpm=0)
    recs, rows, st = asyncio.run(je.score_set("honest:O_diff", items, ns, tmp_path, MODELS, "test"))
    assert sorted(r["outcome"] for r in rows) == ["refused", "scored"] and st["dollars"] == 0.02
    assert je.by_document(rows) == {"/shared/ops/oncall-runbook.md": {"n": 2, "refused": 1, "errored": 0}}
    assert je.cache_path(tmp_path, "O_diff", "sol", je.TAG_V2).exists() and je.dollars_so_far(tmp_path)["sol"] == 0.02
    assert (tmp_path / "extra-judge-batches.jsonl").exists()


def test_score_set_refuses_when_the_cap_is_spent(tmp_path, monkeypatch):
    _write_cache(tmp_path, "sol", je.TAG_V3, "O_diff", [je.CAP_USD])
    monkeypatch.setattr(jo.OpenRouterJudge, "_get_client", lambda self: Fake([]))
    ns = SimpleNamespace(judge="sol", concurrency=1, rpm=0)
    with pytest.raises(SystemExit):
        asyncio.run(je.score_set("honest:O_diff", [{"label": "a", "packet": "p", "key": "k"}], ns, tmp_path, MODELS, "test"))


def test_point_rule_and_table_of():
    arm = lambda r: {"recall": r, "ci95": [0, 1], "n_delivered": 8}  # noqa: E731
    reg = {"O_diff": {"share": 0.09, "ci95": [0, 1], "by_arm": {}, "paired_honest_control": {"share_among_counterpart_unflagged": 0.08}, "document_classes": {}},
           "P_author": {"arms": {"lone": arm(0.0), "k2": arm(0.125), "k3": arm(0.0)}}}
    pr = je.point_rule({"sham": reg}, "sham")
    assert pr["composed"] is True and pr["P_author_all_arms"] is False
    assert je.table_of({"sham": reg})["sham"]["P_author"]["k2"]["recall"] == 0.125
    assert je.point_rule({}, "sham")["composed"] is None
