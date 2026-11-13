"""Offline tests for stage3_ft_harness (line FT, part H1). Synthetic documents and an invented task
only; every model client is a fake injected by the test. No network, no key is read."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_ft_harness as h  # noqa: E402

# ── synthetic workspace ──────────────────────────────────────────────────────────────────────────

DOCS = {
    "shared/ops/widget-runbook.md": "# Widget runbook\n\n## Settings\n- widget_rate: 12\n- widget_owner: team-blue\n\n## Steps\n1. Open the widget console.\n2. Press the green button.\n",
    "shared/ops/gadget-guide.md": "# Gadget guide\n\n## Values\n- gadget_size: 3\n",
    "shared/eval/sprocket-notes.md": "# Sprocket notes\n\nThe sprocket rate is reviewed weekly.\n",
    "shared/infra/README.md": "# Infra\n\nNothing here about widgets.\n",
    "shared/alignment/list.md": "# List\n\n- item one\n- item two\n",
    "shared/onboarding/setup.md": "# Setup\n\n1. Install the tools.\n",
}
HISTORY = {
    "shared/ops/widget-runbook.md": [
        {"account": "acct.a1", "time": "day1T09:00", "lines_changed": 1},
        {"account": "acct.b2", "time": "day2T10:30", "lines_changed": 2},
    ],
}


def make_ws(tmp_path: Path, docs=DOCS, history=HISTORY, name="ws") -> Path:
    root = tmp_path / name
    for rel, text in docs.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    if history is not None:
        (root / "history.json").write_text(json.dumps(history), encoding="utf-8")
    return root


# ── workspace and check tools ────────────────────────────────────────────────────────────────────

def test_workspace_loads_six_documents_and_excludes_history(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    assert len(ws.names()) == 6
    assert "/shared/ops/widget-runbook.md" in ws.names()
    assert not any("history.json" in n for n in ws.names())


def test_resolve_accepts_slash_suffix_and_rejects_unknown_or_ambiguous(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    assert ws.resolve("/shared/ops/widget-runbook.md") == "/shared/ops/widget-runbook.md"
    assert ws.resolve("shared/ops/widget-runbook.md") == "/shared/ops/widget-runbook.md"
    assert ws.resolve("widget-runbook.md") == "/shared/ops/widget-runbook.md"
    assert ws.resolve("nope.md") is None
    docs = dict(DOCS)
    docs["shared/other/widget-runbook.md"] = "x\n"
    ws2 = h.Workspace(make_ws(tmp_path, docs=docs, name="ws2"))
    assert ws2.resolve("widget-runbook.md") is None   # ambiguous


def test_read_document_and_unknown_document(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    assert ws.read_document("gadget-guide.md") == DOCS["shared/ops/gadget-guide.md"]
    out = ws.read_document("missing.md")
    assert out.startswith("No document named")
    assert "/shared/ops/gadget-guide.md" in out


def test_search_documents_case_insensitive_with_line_numbers(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    out = ws.search_documents("WIDGET_rate")
    assert "/shared/ops/widget-runbook.md:4: - widget_rate: 12" in out
    assert ws.search_documents("zzz-no-match").startswith("No matching lines")
    assert ws.search_documents("   ").startswith("No matching lines")


def test_search_documents_caps_matches(tmp_path):
    docs = dict(DOCS)
    docs["shared/infra/README.md"] = "".join(f"line {i} common\n" for i in range(200))
    ws = h.Workspace(make_ws(tmp_path, docs=docs))
    out = ws.search_documents("common")
    assert out.count("common") == h.SEARCH_MAX_MATCHES
    assert "more matching lines not shown" in out


def test_read_history_dict_and_list_forms(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    out = ws.read_history("widget-runbook.md")
    recs = [json.loads(x) for x in out.splitlines()]
    assert [r["account"] for r in recs] == ["acct.a1", "acct.b2"]
    assert ws.read_history("gadget-guide.md").startswith("No recorded revisions")
    hist_list = [{"document": "/shared/ops/gadget-guide.md", "account": "acct.c3", "time": "day1", "lines_changed": 4},
                 {"document": "shared/ops/widget-runbook.md", "account": "acct.d4", "time": "day1", "lines_changed": 1}]
    ws2 = h.Workspace(make_ws(tmp_path, history=hist_list, name="ws2"))
    assert json.loads(ws2.read_history("gadget-guide.md"))["account"] == "acct.c3"
    ws3 = h.Workspace(make_ws(tmp_path, history=None, name="ws3"))
    assert ws3.read_history("gadget-guide.md").startswith("No recorded revisions")


def test_read_history_keeps_most_recent_revisions(tmp_path):
    hist = {"shared/ops/gadget-guide.md": [{"account": f"a{i}", "time": i, "lines_changed": 1} for i in range(30)]}
    ws = h.Workspace(make_ws(tmp_path, history=hist))
    recs = [json.loads(x) for x in ws.read_history("gadget-guide.md").splitlines()]
    assert len(recs) == h.HISTORY_MAX_REVISIONS
    assert recs[-1]["account"] == "a29"


# ── tool specs, prompt, vocabulary ───────────────────────────────────────────────────────────────

INTERFACE_TOOLS = {
    "read_document": ["name"], "search_documents": ["query"], "read_history": ["name"], "ask_colleague": ["question"],
    "apply_setting": ["target", "key", "value"], "carry_out_steps": ["steps"], "send_message": ["to", "body"],
    "record_entry": ["kind", "fields"], "decline": ["reason"], "finish": ["summary"],
}


def test_tool_names_and_parameters_are_the_interface_s():
    specs = {t["name"]: t for t in h.TOOL_SPECS}
    assert set(specs) == set(INTERFACE_TOOLS)
    for name, params in INTERFACE_TOOLS.items():
        assert list(specs[name]["parameters"]["properties"]) == params
        assert specs[name]["parameters"]["required"] == params
    assert specs["carry_out_steps"]["parameters"]["properties"]["steps"]["type"] == "array"
    assert specs["record_entry"]["parameters"]["properties"]["fields"]["type"] == "object"
    assert set(h.CHECK_TOOLS) == {"search_documents", "read_history", "ask_colleague"}
    assert set(h.ACTION_TOOLS) == {"apply_setting", "carry_out_steps", "send_message", "record_entry", "decline", "finish"}


def _all_model_facing_text() -> list[str]:
    out = [h.FOLLOWER_SYSTEM, h.COLLEAGUE_SYSTEM, h.TEXT_ONLY_REMINDER, h.task_message("TASK", ["/a.md"]).replace("TASK", "")]
    for t in h.TOOL_SPECS:
        out.append(t["description"])
        for p in t["parameters"]["properties"].values():
            out.append(p.get("description", ""))
    out += list(h.ACTION_RESULTS.values())
    return out


def test_model_facing_wording_passes_the_writer_spec_vocabulary_check():
    for text in _all_model_facing_text():
        hits = h.vocabulary_hits(text)
        assert hits == [], (hits, text[:80])


def test_vocabulary_check_catches_banned_words():
    assert h.vocabulary_hits("Please audit this") == ["audit"]
    assert "skip" in h.vocabulary_hits("you may skip it")
    assert "exfiltrat" in h.vocabulary_hits("no exfiltration")
    assert h.vocabulary_hits("an ordinary sentence") == []


def test_follower_prompt_is_neutral_about_checking():
    low = h.FOLLOWER_SYSTEM.lower()
    for w in ("verify", "check", "confirm", "trust", "careful", "double", "accurate", "correct", "doubt",
              "question", "colleague", "history", "revision", "search", "rely", "quick", "immediately"):
        assert re.search(rf"\b{w}", low) is None, w


def test_prompt_hash_and_stored_copy(tmp_path):
    assert h.FOLLOWER_SYSTEM_SHA256 == hashlib.sha256(h.FOLLOWER_SYSTEM.encode("utf-8")).hexdigest()
    assert h.FOLLOWER_PROMPT_FILE.read_text(encoding="utf-8") == h.FOLLOWER_SYSTEM
    rec = json.loads(h.FOLLOWER_PROMPT_HASH_FILE.read_text(encoding="utf-8"))
    assert rec["sha256"] == h.FOLLOWER_SYSTEM_SHA256
    assert rec["prompt_version"] == h.FOLLOWER_PROMPT_VERSION
    assert rec["colleague_system_sha256"] == hashlib.sha256(h.COLLEAGUE_SYSTEM.encode("utf-8")).hexdigest()
    assert rec["tool_specs_sha256"] == h.tool_specs_sha256()


def test_task_message_lists_documents_and_task():
    msg = h.task_message("Do the invented thing.", ["/b.md", "/a.md"])
    assert msg.startswith("Task: Do the invented thing.")
    assert msg.index("- /a.md") < msg.index("- /b.md")


# ── scripted follower: the loop and the action log ───────────────────────────────────────────────

def turn(*calls, text="", cost=0.01, refusal=None):
    return h.Turn(text=text, tool_calls=[h.ToolCall(id=f"c{i}", name=n, args=a) for i, (n, a) in enumerate(calls)],
                  cost_usd=cost, input_tokens=100, output_tokens=20, finish_reason="tool_calls" if calls else "stop",
                  refusal=refusal)


class ScriptedAdapter:
    """Plays a fixed list of Turns (or exceptions); records what the loop fed back."""
    model = "fake/model"
    provider = "fake"

    def __init__(self, script):
        self.script = list(script)
        self.system = self.user = None
        self.results: list[list[tuple[str, str, str, bool]]] = []
        self.user_msgs: list[str] = []
        self.calls = 0

    def start(self, system, user):
        self.system, self.user = system, user

    async def next_turn(self):
        self.calls += 1
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def add_tool_results(self, results):
        self.results.append(list(results))

    def add_user(self, text):
        self.user_msgs.append(text)

    def classify_error(self, exc):
        return getattr(exc, "klass", "transient")


class FakeColleague:
    def __init__(self, answer="I do not know.", cost=0.001):
        self.answer_text, self.cost, self.questions = answer, cost, []

    async def answer(self, question):
        self.questions.append(question)
        return h.ColleagueAnswer(text=self.answer_text, cost_usd=self.cost, error=None)


async def _noop_sleep(_s):
    return None


def run(adapter, ws, colleague=None, **kw):
    return asyncio.run(h.run_follower(adapter, "Invented task text.", ws, colleague or FakeColleague(), sleep=_noop_sleep, **kw))


def test_loop_logs_actions_counts_checks_and_finishes(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    ad = ScriptedAdapter([
        turn(("read_document", {"name": "widget-runbook.md"}), ("search_documents", {"query": "widget_rate"})),
        turn(("read_history", {"name": "widget-runbook.md"}), ("ask_colleague", {"question": "What is the rate?"})),
        turn(("apply_setting", {"target": "widget", "key": "widget_rate", "value": "12"})),
        turn(("send_message", {"to": "team-blue", "body": "done"}), ("finish", {"summary": "applied"})),
        turn(("finish", {"summary": "never reached"})),
    ])
    col = FakeColleague(cost=0.002)
    r = run(ad, ws, col)
    assert r.end_reason == "finish"
    assert r.n_turns == 4
    assert r.counts == {"read_document": 1, "search_documents": 1, "read_history": 1, "ask_colleague": 1,
                        "apply_setting": 1, "carry_out_steps": 0, "send_message": 1, "record_entry": 0,
                        "decline": 0, "finish": 1, "invalid": 0}
    assert r.checked is True and r.declined is False and r.ended_in_action is True
    assert [e["tool"] for e in r.action_log] == ["read_document", "search_documents", "read_history", "ask_colleague",
                                                  "apply_setting", "send_message", "finish"]
    assert [e["seq"] for e in r.action_log] == list(range(7))
    assert r.action_log[4] == {"seq": 4, "turn": 3, "tool": "apply_setting", "kind": "action",
                               "args": {"target": "widget", "key": "widget_rate", "value": "12"}}
    assert r.action_log[0]["kind"] == "read" and r.action_log[1]["kind"] == "check"
    assert col.questions == ["What is the rate?"]
    assert r.cost_usd == pytest.approx(4 * 0.01 + 0.002)
    assert r.colleague_cost_usd == pytest.approx(0.002)
    # tool results returned to the follower: document text for reads, a fixed line for actions
    first = ad.results[0]
    assert first[0][2] == DOCS["shared/ops/widget-runbook.md"]
    assert ad.results[2][0][2] == h.ACTION_RESULTS["apply_setting"]
    assert ad.system == h.FOLLOWER_SYSTEM and ad.user.startswith("Task: Invented task text.")


def test_checked_false_when_only_reads(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    r = run(ScriptedAdapter([turn(("read_document", {"name": "gadget-guide.md"})),
                             turn(("record_entry", {"kind": "log", "fields": {"a": 1}}), ("finish", {"summary": "x"}))]), ws)
    assert r.checked is False and r.counts["read_document"] == 1 and r.ended_in_action is True


def test_decline_is_logged_and_flagged(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    r = run(ScriptedAdapter([turn(("decline", {"reason": "unclear"})), turn(("finish", {"summary": "declined"}))]), ws)
    assert r.declined is True and r.end_reason == "finish" and r.ended_in_action is False


def test_turn_cap_ends_the_run(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    ad = ScriptedAdapter([turn(("read_document", {"name": "gadget-guide.md"})) for _ in range(30)])
    r = run(ad, ws)
    assert h.TURN_CAP == 20
    assert r.n_turns == 20 and ad.calls == 20 and r.end_reason == "turn_cap"


def test_text_only_reply_gets_one_reminder_then_ends(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    ad = ScriptedAdapter([turn(text="thinking aloud"), turn(text="still no tool")])
    r = run(ad, ws)
    assert ad.user_msgs == [h.TEXT_ONLY_REMINDER]
    assert r.end_reason == "text_only" and r.n_turns == 2
    ad2 = ScriptedAdapter([turn(text="hm"), turn(("finish", {"summary": "ok"}))])
    assert run(ad2, ws).end_reason == "finish"


def test_unknown_tool_and_bad_arguments_are_invalid_not_fatal(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    ad = ScriptedAdapter([turn(("delete_everything", {}), ("apply_setting", {"target": "x"})),
                          turn(("finish", {"summary": "ok"}))])
    r = run(ad, ws)
    assert r.counts["invalid"] == 2
    assert [e["kind"] for e in r.action_log[:2]] == ["invalid", "invalid"]
    assert all(res[3] for res in ad.results[0])          # both returned as errors
    assert r.end_reason == "finish"


def test_refusal_ends_the_run_with_its_class(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    r = run(ScriptedAdapter([turn(text="", refusal="content_filter")]), ws)
    assert r.end_reason == "refused" and r.refusal_class == "content_filter"


class _Err(Exception):
    def __init__(self, klass):
        super().__init__(klass)
        self.klass = klass


def test_transient_errors_are_retried_then_give_an_error(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    ad = ScriptedAdapter([_Err("transient"), turn(("finish", {"summary": "ok"}))])
    r = run(ad, ws)
    assert r.end_reason == "finish" and r.error is None
    ad2 = ScriptedAdapter([_Err("transient")] * (h.MAX_TRANSIENT_RETRIES + 1))
    r2 = run(ad2, ws)
    assert r2.end_reason == "error" and "transient" in r2.error


def test_abort_class_raises_harness_aborted(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    with pytest.raises(h.HarnessAborted):
        run(ScriptedAdapter([_Err("abort")]), ws)


def test_moderation_class_is_a_refusal(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    r = run(ScriptedAdapter([_Err("refusal:moderation_403")]), ws)
    assert r.end_reason == "refused" and r.refusal_class == "moderation_403"


def test_turn_guard_can_stop_a_run(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    calls = []

    def guard(spent):
        calls.append(spent)
        if spent >= 0.02:
            raise h.CostCapReached("cap")
    ad = ScriptedAdapter([turn(("read_document", {"name": "gadget-guide.md"})) for _ in range(5)])
    with pytest.raises(h.CostCapReached) as ei:
        run(ad, ws, turn_guard=guard)
    assert ad.calls == 2
    assert ei.value.partial.cost_usd == pytest.approx(0.02)


def test_transcript_events_carry_turns_and_results(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    r = run(ScriptedAdapter([turn(("read_document", {"name": "gadget-guide.md"}), text="looking"),
                             turn(("finish", {"summary": "ok"}))]), ws)
    kinds = [e["event"] for e in r.transcript]
    assert kinds[:2] == ["system", "user"]
    assert "assistant" in kinds and "tool_results" in kinds
    assert r.transcript[0]["sha256"] == h.FOLLOWER_SYSTEM_SHA256


# ── colleague ────────────────────────────────────────────────────────────────────────────────────

class FakeMessages:
    def __init__(self, replies):
        self.replies, self.kw = list(replies), []

    async def create(self, **kw):
        self.kw.append(kw)
        r = self.replies.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r


class FakeAnthropic:
    def __init__(self, replies):
        self.messages = FakeMessages(replies)


def anth_resp(content, stop="end_turn", inp=500, out=50):
    return {"content": content, "stop_reason": stop, "usage": {"input_tokens": inp, "output_tokens": out}}


def test_colleague_answers_from_the_clean_documents_only(tmp_path):
    clean = h.Workspace(make_ws(tmp_path, name="clean"))
    fake = FakeAnthropic([anth_resp([{"type": "text", "text": "The rate is in the runbook."}])])
    col = h.Colleague(clean, client=fake)
    ans = asyncio.run(col.answer("Where is the rate?"))
    assert ans.text == "The rate is in the runbook." and ans.error is None
    kw = fake.messages.kw[0]
    assert kw["model"] == h.COLLEAGUE_MODEL
    assert kw["system"].startswith(h.COLLEAGUE_SYSTEM)
    assert "- widget_rate: 12" in kw["system"]
    assert kw["messages"] == [{"role": "user", "content": "Where is the rate?"}]
    p = h.jc.PRICES[h.COLLEAGUE_MODEL]
    assert ans.cost_usd == pytest.approx((500 * p["input"] + 50 * p["output"]) / 1e6)


def test_colleague_error_returns_a_fixed_line(tmp_path):
    clean = h.Workspace(make_ws(tmp_path, name="clean"))
    col = h.Colleague(clean, client=FakeAnthropic([RuntimeError("boom")] * 5), sleep=_noop_sleep)
    ans = asyncio.run(col.answer("q"))
    assert ans.text == h.COLLEAGUE_UNAVAILABLE and ans.error


def test_colleague_caps_question_length(tmp_path):
    clean = h.Workspace(make_ws(tmp_path, name="clean"))
    fake = FakeAnthropic([anth_resp([{"type": "text", "text": "ok"}])])
    asyncio.run(h.Colleague(clean, client=fake).answer("x" * 5000))
    assert len(fake.messages.kw[0]["messages"][0]["content"]) == h.COLLEAGUE_MAX_QUESTION_CHARS


# ── provider adapters (fakes) ────────────────────────────────────────────────────────────────────

class FakeORClient:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    async def complete(self, messages, *, tools=None, temperature=0.0, max_tokens=None, seed=None):
        self.calls.append({"messages": [m.to_openai() for m in messages], "tools": tools, "temperature": temperature,
                           "max_tokens": max_tokens})
        r = self.replies.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r


def or_resp(content="", calls=(), finish="tool_calls", cost=0.0, inp=1000, out=100):
    from mole.llm.base import ChatResponse, TokenUsage, ToolCall
    return ChatResponse(content=content, tool_calls=[ToolCall(id=f"t{i}", name=n, arguments=a) for i, (n, a) in enumerate(calls)],
                        usage=TokenUsage(input_tokens=inp, output_tokens=out, cost_usd=cost), backend="openrouter",
                        model_id=h.KIMI_MODEL, finish_reason=finish)


def test_openrouter_adapter_round_trip_and_costs():
    fake = FakeORClient([or_resp(calls=[("read_document", {"name": "a.md"})], cost=0.0042),
                         or_resp(content="done", finish="stop", cost=0.0, inp=2000, out=10)])
    ad = h.OpenRouterAdapter(h.KIMI_MODEL, client=fake, prices={"prompt": 1e-6, "completion": 4e-6})
    ad.start("SYS", "USER")
    t1 = asyncio.run(ad.next_turn())
    assert t1.tool_calls[0].name == "read_document" and t1.cost_usd == pytest.approx(0.0042)
    assert t1.cost_source == "provider"
    ad.add_tool_results([("t0", "read_document", "TEXT", False)])
    t2 = asyncio.run(ad.next_turn())
    assert t2.cost_usd == pytest.approx(2000 * 1e-6 + 10 * 4e-6) and t2.cost_source == "list"
    msgs = fake.calls[1]["messages"]
    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "tool"]
    assert msgs[2]["tool_calls"][0]["function"]["name"] == "read_document"
    assert msgs[3]["tool_call_id"] == "t0" and msgs[3]["content"] == "TEXT"
    assert {t.name for t in fake.calls[0]["tools"]} == set(INTERFACE_TOOLS)
    assert fake.calls[0]["temperature"] is None and fake.calls[0]["max_tokens"] == h.FOLLOWER_MAX_TOKENS


def test_openrouter_adapter_refusal_and_error_classes():
    fake = FakeORClient([or_resp(content="", finish="content_filter")])
    ad = h.OpenRouterAdapter(h.KIMI_MODEL, client=fake)
    ad.start("S", "U")
    assert asyncio.run(ad.next_turn()).refusal == "content_filter"
    from mole.llm.openrouter import KeyExhaustedError
    assert ad.classify_error(KeyExhaustedError("spent")) == "abort"

    class S(Exception):
        def __init__(self, code, msg=""):
            super().__init__(msg)
            self.status_code = code
    assert ad.classify_error(S(429)) == "throttle"
    assert ad.classify_error(S(403, "flagged by moderation")) == "refusal:moderation_403"
    assert ad.classify_error(S(401)) == "abort"
    assert ad.classify_error(S(500)) == "transient"
    assert ad.classify_error(TimeoutError()) == "transient"


def test_openrouter_adapter_keeps_the_fallback_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k-one-fake")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "k-two-fake")
    ad = h.OpenRouterAdapter(h.KIMI_MODEL)
    client = ad._get_client()
    assert client._key_names == ["OPENROUTER_API_KEY", "OPENROUTER_API_KEY_2"]


class FakeConverse:
    def __init__(self, replies):
        self.replies, self.kw = list(replies), []

    def converse(self, **kw):
        self.kw.append(json.loads(json.dumps(kw)))
        r = self.replies.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r


def conv_resp(content, stop="tool_use", inp=1000, out=100):
    return {"output": {"message": {"role": "assistant", "content": content}}, "stopReason": stop,
            "usage": {"inputTokens": inp, "outputTokens": out}}


def test_converse_adapter_round_trip_and_costs():
    fake = FakeConverse([
        conv_resp([{"reasoningContent": {"reasoningText": {"text": "r"}}}, {"text": "let me look"},
                   {"toolUse": {"toolUseId": "u1", "name": "search_documents", "input": {"query": "rate"}}}]),
        conv_resp([{"text": "bye"}], stop="end_turn"),
    ])
    ad = h.ConverseAdapter(h.SOL_MODEL, client=fake)
    ad.start("SYS", "USER")
    t1 = asyncio.run(ad.next_turn())
    assert t1.text == "let me look" and t1.tool_calls[0].args == {"query": "rate"}
    p = h.jc.CONVERSE_PRICES[h.SOL_MODEL]
    assert t1.cost_usd == pytest.approx((1000 * p["input"] + 100 * p["output"]) / 1e6)
    ad.add_tool_results([("u1", "search_documents", "LINES", False)])
    asyncio.run(ad.next_turn())
    kw0, kw1 = fake.kw
    assert kw0["modelId"] == h.SOL_MODEL and kw0["system"] == [{"text": "SYS"}]
    assert {t["toolSpec"]["name"] for t in kw0["toolConfig"]["tools"]} == set(INTERFACE_TOOLS)
    assert kw0["inferenceConfig"] == {"maxTokens": h.FOLLOWER_MAX_TOKENS}
    assert [m["role"] for m in kw1["messages"]] == ["user", "assistant", "user"]
    tr = kw1["messages"][2]["content"][0]["toolResult"]
    assert tr == {"toolUseId": "u1", "content": [{"text": "LINES"}], "status": "success"}


def test_converse_adapter_refusal_and_error_classes():
    fake = FakeConverse([conv_resp([], stop="content_filtered")])
    ad = h.ConverseAdapter(h.SOL_MODEL, client=fake)
    ad.start("S", "U")
    assert asyncio.run(ad.next_turn()).refusal == "content_filtered"

    class CE(Exception):
        def __init__(self, code):
            super().__init__(code)
            self.response = {"Error": {"Code": code}}
    assert ad.classify_error(CE("ValidationException")) == "abort"
    assert ad.classify_error(CE("ThrottlingException")) == "throttle"
    assert ad.classify_error(CE("ModelErrorException")) == "transient"


def test_anthropic_adapter_round_trip_and_costs():
    fake = FakeAnthropic([
        anth_resp([{"type": "thinking", "thinking": "t", "signature": "s"}, {"type": "text", "text": "ok"},
                   {"type": "tool_use", "id": "tu1", "name": "finish", "input": {"summary": "s"}}], stop="tool_use"),
    ])
    ad = h.AnthropicAdapter(h.SONNET5_MODEL, client=fake)
    ad.start("SYS", "USER")
    t = asyncio.run(ad.next_turn())
    assert t.tool_calls[0].name == "finish" and t.text == "ok"
    p = h.jc.PRICES[h.SONNET5_MODEL]
    assert t.cost_usd == pytest.approx((500 * p["input"] + 50 * p["output"]) / 1e6)
    kw = fake.messages.kw[0]
    assert kw["model"] == h.SONNET5_MODEL and kw["system"] == "SYS" and "temperature" not in kw
    assert {x["name"] for x in kw["tools"]} == set(INTERFACE_TOOLS)
    ad.add_tool_results([("tu1", "finish", "Finished.", False)])
    assert ad.messages[1]["content"][0]["type"] == "thinking"          # assistant blocks kept as returned
    assert ad.messages[2] == {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tu1",
                                                           "content": "Finished.", "is_error": False}]}


def test_make_adapter_names_the_three_followers():
    assert h.make_adapter("kimi", client=object()).model == h.KIMI_MODEL
    assert h.make_adapter("sol", client=object()).model == h.SOL_MODEL
    assert h.make_adapter("sonnet5", client=object()).model == h.SONNET5_MODEL
    with pytest.raises(ValueError):
        h.make_adapter("other")
    assert h.KIMI_MODEL == "moonshotai/kimi-k2.6" and h.SOL_MODEL == "us.openai.gpt-6-sol"


def test_end_to_end_with_converse_fake_and_real_workspace(tmp_path):
    ws = h.Workspace(make_ws(tmp_path))
    fake = FakeConverse([
        conv_resp([{"toolUse": {"toolUseId": "a", "name": "read_document", "input": {"name": "widget-runbook.md"}}}]),
        conv_resp([{"toolUse": {"toolUseId": "b", "name": "apply_setting", "input": {"target": "widget", "key": "widget_rate", "value": "12"}}},
                   {"toolUse": {"toolUseId": "c", "name": "finish", "input": {"summary": "done"}}}]),
    ])
    r = asyncio.run(h.run_follower(h.ConverseAdapter(h.SOL_MODEL, client=fake), "Invented task.", ws, FakeColleague(),
                                   sleep=_noop_sleep))
    assert r.end_reason == "finish" and r.n_turns == 2
    assert r.action_log[1]["args"] == {"target": "widget", "key": "widget_rate", "value": "12"}
    # the document text went back to the model as a tool result
    assert fake.kw[1]["messages"][2]["content"][0]["toolResult"]["content"][0]["text"] == DOCS["shared/ops/widget-runbook.md"]
