"""Offline tests for stage3_b3_client_equivalence (brief 31): the comparison machinery names differences by field,
refuses a client whose bytes are not the stated hash, keeps no reply content from a cache, and finds the one
default-path change it reports (an aborted unit's paid attempts kept on file).

    cd work/checks && ../mole-fork/.venv/bin/python -I -m pytest -q test_stage3_b3_client_equivalence.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_b3_client_equivalence as eq  # noqa: E402


@pytest.fixture(scope="module")
def mods():
    return eq.load_clients()


def test_diff_paths_names_fields_never_values():
    a = {"model": "m", "thinking": {"type": "disabled"}, "messages": [{"role": "user", "content": "secret one"}], "x": 1}
    b = {"model": "m", "thinking": {"type": "adaptive"}, "messages": [{"role": "user", "content": "secret two"}], "y": 1}
    d = eq.diff_paths(a, b)
    assert d == ["messages[0].content", "thinking.type", "x (bound only)", "y (current only)"]
    assert not any("secret" in p for p in d)
    assert eq.diff_paths([1, 2], [1]) == [" (length)"] and eq.diff_paths({"k": [1]}, {"k": [1]}) == []


def test_source_text_refuses_a_wrong_hash(monkeypatch):
    monkeypatch.setitem(eq.SOURCES, "jc_72d394e3", {**eq.SOURCES["jc_72d394e3"], "sha256": "0" * 64})
    with pytest.raises(SystemExit, match="refusing"):
        eq.source_text("jc_72d394e3")


def test_every_version_loads_at_its_hash_and_the_bound_one_lacks_converse(mods):
    assert set(mods) == set(eq.SOURCES)
    assert not hasattr(mods[eq.BOUND], "BedrockConverseJudge") and hasattr(mods[eq.CURRENT], "BedrockConverseJudge")
    assert hasattr(mods[eq.CONVERSE_BASE], "BedrockConverseJudge")
    # the old OpenRouter client was loaded against the bound judge client
    assert mods[eq.JO_OLD].jc is mods[eq.BOUND] and mods[eq.JO_NOW].jc is mods[eq.CURRENT]


def _cell(model=eq.SONNET, mt=None):
    return {"view_key": "O_diff", "model": model, "max_tokens_arg": mt, "system": "a system prompt", "prompt_version": "v/1"}


def test_built_requests_are_compared_byte_for_byte_and_a_change_is_named(mods, monkeypatch):
    items = [{"label": f"u{i}", "packet": f"packet {i}", "key": eq.jc_mod.cache_key("O_diff", f"u{i}", f"packet {i}")} for i in range(3)]
    idx = {it["key"]: {"cache_key": it["key"], "packet_sha256": eq.jc_mod.sha256(it["packet"]), "packet_chars": len(it["packet"]),
                       "request_params": eq.jc_mod.request_params(eq.SONNET, 900, "a system prompt")} for it in items}
    r = eq.compare_cell(_cell(), items, idx, mods, (eq.BOUND, eq.CURRENT), "anthropic", eq.built_anthropic)
    assert r["requests_byte_equal"] == 3 and r["records_equal"] == 3 and r["sent_vs_recorded_equal"] == 3
    assert r["request_keys_current"] == ["max_tokens", "messages", "model", "system", "thinking"]
    # a client that sends another thinking setting (its record unchanged) is caught by field name, in the request
    # comparison and against the recorded request
    cur = mods[eq.CURRENT]
    orig = cur.JudgeClient._request

    async def _request(self, st, packet, label, *, system, max_tokens):
        monkeypatch.setattr(cur, "thinking_param", lambda model: {"type": "adaptive"})
        try:
            return await orig(self, st, packet, label, system=system, max_tokens=max_tokens)
        finally:
            monkeypatch.undo()
    altered = types.ModuleType("altered")
    altered.JudgeClient = type("JudgeClient", (cur.JudgeClient,), {"_request": _request})
    r2 = eq.compare_cell(_cell(), items, idx, {**mods, "altered": altered}, (eq.BOUND, "altered"), "anthropic", eq.built_anthropic)
    assert r2["requests_byte_equal"] == 0 and r2["request_diff_fields"] == {"thinking.type": 3}
    assert r2["sent_vs_recorded_diff_fields"] == {"thinking.type": 3}


def test_converse_requests_and_the_provider_switch_fields(mods):
    items = [{"label": "u", "packet": "p", "key": eq.jc_mod.cache_key("O_diff", "u", "p")}]
    openrouter_record = {"cache_key": items[0]["key"], "packet_sha256": eq.jc_mod.sha256("p"), "packet_chars": 1,
                         "request_params": {"model": eq.SOL_OPENROUTER, "max_tokens": 4000, "temperature": 0.0, "reasoning": "provider default",
                                            "system_sha256": eq.jc_mod.sha256("a system prompt"), "system_chars": 15}}
    r = eq.compare_cell(_cell(eq.SOL_BEDROCK), items, {items[0]["key"]: openrouter_record}, mods, (eq.CONVERSE_BASE, eq.CURRENT),
                        "converse", eq.built_converse)
    assert r["requests_byte_equal"] == 1 and r["records_equal"] == 1
    assert r["sent_vs_recorded_diff_fields"] == {"model": 1, "temperature": 1}


def test_cache_index_keeps_no_reply_content_and_reports_key_names(tmp_path):
    p = tmp_path / "c.jsonl"
    rec = {"cache_key": "V|l|h", "view": "V", "label": "l", "outcome": "scored", "score": 61, "flag": True, "rationale": "private words",
           "request_params": {"model": "m"}, "attempts": [{"outcome": "scored", "stop_reason": "end_turn"}], "packet_sha256": "h"}
    p.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    idx, shape = eq.cache_index(p)
    assert "private words" not in json.dumps(idx) and "score" not in idx["V|l|h"] and "rationale" not in idx["V|l|h"]
    assert shape["holds_raw_reply_text"] is False and "rationale" in shape["keys"] and shape["nested_keys"]["attempts[]"] == ["outcome", "stop_reason"]
    p.write_text(json.dumps({**rec, "response_text": "x"}) + "\n", encoding="utf-8")
    assert eq.cache_index(p)[1]["holds_raw_reply_text"] is True


def test_parser_shapes_are_distinct_and_a_parser_difference_is_found(mods):
    names = [n for n, _ in eq.text_shapes()]
    assert len(names) == len(set(names))
    shapes = eq.anthropic_shapes()
    same = eq.classify_equal(shapes, mods[eq.BOUND].classify, mods[eq.CURRENT].classify, lambda r: mods[eq.CURRENT].classify(r, None))
    assert same["equal"] == same["shapes"] and set(same["outcomes_bound"]) == {"scored", "refused", "errored"}

    def flips(resp):
        c = mods[eq.CURRENT].classify(resp)
        return {**c, "flag": (not c["flag"]) if c["flag"] is not None else None}
    d = eq.classify_equal(shapes[:2], mods[eq.BOUND].classify, flips, mods[eq.CURRENT].classify)
    assert d["equal"] == 0 and all(v == ["flag"] for v in d["differences"].values())


def test_the_loop_test_finds_the_abort_record_and_nothing_else(mods):
    r = eq.loop_equal(eq.anthropic_sequences, mods[eq.BOUND], mods[eq.CURRENT], "anthropic")
    assert r["differences"] == {"refusal then HTTP 403 (abort after a paid attempt)": ["cache_lines (length)"],
                                "unparseable then HTTP 404 (abort after a paid attempt)": ["cache_lines (length)"]}
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        seq = dict(eq.anthropic_sequences())["refusal then HTTP 403 (abort after a paid attempt)"]
        new = eq.run_loop(mods[eq.CURRENT], "anthropic", seq, Path(td))
    assert new["result"]["raised"] == "JudgeAborted" and new["requests"] == 2
    assert [ln["outcome"] for ln in new["cache_lines"]] == ["errored"] and new["cache_lines"][0]["error"] == "aborted after paid attempts"


def test_cross_provider_wrappers_agree_on_text(mods):
    r = eq.cross_provider(mods)
    assert r["equal"] == r["texts"] and r["differences"] == {}


def test_cells_follow_the_plan_order_and_settings():
    cs = eq.cells()
    assert [c["cell"] for c in cs] == ["P_author_doc_iso|opus48", "P_author|opus48", "P_author_doc_iso|sonnet", "P_author|sonnet",
                                       "P_author_doc_live|opus48", "P_author_doc_live|sonnet", "O_diff|sonnet", "O_diff|opus48", "O_diff|sol"]
    assert {c["max_tokens_arg"] for c in cs if c["judge"] == "opus48"} == {4000}
    assert [c["family"] for c in cs].count("converse") == 1


def test_stub_sends_nothing(mods):
    stub = eq.StubAnthropic()
    jc = mods[eq.CURRENT].JudgeClient(cache_path=None, model=eq.SONNET, spend_cap_usd=None, region="us-east-1", client=stub,
                                      sleep=eq._no_sleep, verbose=False, system="s", prompt_version="v")
    rec = asyncio.run(jc.score("V", "l", "p"))
    assert rec["outcome"] == "scored" and len(stub.messages.calls) == 1 and stub.messages.calls[0]["messages"][0]["content"] == "p"
