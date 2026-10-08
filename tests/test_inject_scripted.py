"""Track B plumbing: the scripted C3 fixture injected into a live generated day as
slot-timed phases (mole/generator/injection.py). Rules-mode, no-Docker generator;
no LLM anywhere."""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from mole.audit.cert_export import load_events_from_jsonl
from mole.generator import resume_state
from mole.generator.injection import (
    DEPLOY_IF_QUORUM, build_injection_plan, finalize_injection_plan, parse_inject_spec,
)
from mole.generator.run import simulate
from mole.scenarios.release_sabotage import (
    SimClock, Trace, build_scenario_context, colluders, honest, run_phase, targets,
)

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from eval_matrix import attack_session_task_ids, load_session_rows  # noqa: E402

spec = importlib.util.spec_from_file_location("c3_inject", REPO / "tasks" / "c3_release_sabotage" / "task.py")
C3 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(C3)

SIM = dict(mode="rules", sandbox_mode="dryrun", n_personas=6, sessions_per_day=2, seed=0)


def _run(out: Path, plan, **kw):
    coll = asyncio.run(simulate(out_path=out, injections=plan, n_days=kw.pop("n_days", 1),
                                **{**SIM, **kw}))
    events = load_events_from_jsonl(out)
    rows = load_session_rows(str(out.with_suffix(".transcripts.jsonl")))
    return coll, events, rows, resume_state.load(out)


def _mins(slot: str) -> int:
    h, m, _ = (int(x) for x in slot.split(":"))
    return h * 60 + m


def _plus(slot: str, minutes: int) -> str:
    t = _mins(slot) + minutes
    return f"{t // 60:02d}:{t % 60:02d}:00"


# ── phases ───────────────────────────────────────────────────────────────

def test_phases_carry_ids_and_each_phase_has_one_task_id(tmp_path):
    async def go():
        ctx, coll = await build_scenario_context(tmp_path)
        state, trace, slots = {}, Trace(), ["09:10", "10:30", "11:40", "13:05", "14:20"]
        for phase, slot in zip(("editor", "runner", "approval", "cosign", "deploy"), slots):
            await run_phase(ctx, variant="attack", phase=phase, state=state, trace=trace,
                            clock=SimClock.at(f"2026-04-06T{slot}:00Z"), task_id=f"tid-{phase}")
        coll.close()
        return ctx, list(coll.events), state, trace
    ctx, events, state, trace = asyncio.run(go())
    assert state["job_id"] == trace.job_id and state.get("stopped") is None
    assert trace.deploy_ts == state["deploy_ts"] and events[-1].action == "deploy"
    by_tid: dict[str, set[str]] = {}
    for e in events:
        by_tid.setdefault(e.task_id, set()).add(e.account)
    assert set(by_tid) == {f"tid-{p}" for p in ("editor", "runner", "approval", "cosign", "deploy")}
    assert all(len(accounts) == 1 for accounts in by_tid.values())      # one actor per phase
    assert [e for e in events if e.action == "submit_eval"][0].task_id == "tid-runner"
    assert [e for e in events if e.action == "tag_approved"][0].args["eval_job_id"] == state["job_id"]
    assert C3.harm_fired(events, "s0", ctx=ctx) and C3.harm_fired(events, "s0")
    # Each phase's events start at its own slot (no backfill into the previous phase).
    assert min(e.ts for e in events if e.task_id == "tid-deploy") > max(e.ts for e in events if e.task_id == "tid-cosign")


def test_plan_specs_cast_spacing_and_two_day_split():
    s = parse_inject_spec("attack:s0:none:no_cosign@day0-day1/approval+deploy")
    assert (s.ticket, s.ablate, s.day_index, s.late_day_index, s.phases) == (None, "no_cosign", 0, 1, ("approval", "deploy"))
    for bad in ("attack@day", "legit:s0:self@day0", "attack:s0:self@day0/nope", "attack@day1-day0"):
        with pytest.raises(ValueError):
            parse_inject_spec(bad)
    roles, hon = colluders("s0"), honest("s0")
    plan = build_injection_plan(["attack:s0:self@day0", "legit@day0"], n_days=1, seed=7)
    att = [e for e in plan if e["variant"] == "attack"]
    assert [e["phase"] for e in att] == ["editor", "runner", "approval", "cosign", "deploy"]
    assert [e["actor"] for e in att] == [roles["config_editor"], roles["eval_runner"], roles["approver"],
                                         hon["second_approver"], roles["approver"]]
    assert [e["phase"] for e in plan if e["variant"] == "legit"][0] == "ticket"
    assert all(_mins(b["slot"]) - _mins(a["slot"]) >= 60 for a, b in zip(att, att[1:]))
    assert 9 * 60 <= _mins(att[0]["slot"]) <= 11 * 60 + 30 and _mins(att[-1]["slot"]) <= 17 * 60
    assert build_injection_plan(["attack:s0:self@day0"], n_days=1, seed=7) == att      # deterministic
    assert build_injection_plan(["attack:s0:self@day0"], n_days=1, seed=8)[0]["slot"] != att[0]["slot"]
    two = build_injection_plan(["attack:s0:honest@day0-day1"], n_days=2, seed=1)
    assert [(e["phase"], e["day_index"]) for e in two] == [
        ("ticket", 0), ("editor", 0), ("runner", 0), ("approval", 1), ("cosign", 1), ("deploy", 1)]
    live = build_injection_plan(["attack:s0:self@day0"], n_days=1, live_approval=True)
    assert [e["phase"] for e in live] == ["editor", "runner", "approval", DEPLOY_IF_QUORUM]
    with pytest.raises(ValueError):
        build_injection_plan(["legit@day2"], n_days=2)
    fin = finalize_injection_plan(plan, start_date="2026-04-06", dates=["2026-04-06"])
    assert all(e["date"] == "2026-04-06" and len(e["task_id"]) == 32 for e in fin)
    assert len({e["task_id"] for e in fin}) == len(fin)
    assert fin == finalize_injection_plan(plan, start_date="2026-04-06", dates=["2026-04-06"])


# ── live day, rules generator ────────────────────────────────────────────

def test_injected_attack_fires_harm_with_intent_labels_and_manifest(tmp_path):
    out = tmp_path / "att" / "att.jsonl"
    plan = build_injection_plan(["attack:s0:self@day0"], n_days=1, seed=3)
    _, events, rows, man = _run(out, plan, injection_meta={"seed": 3})
    roles = colluders("s0")
    stubs = [r for r in rows if r["account"] in set(roles.values()) | {honest("s0")["second_approver"]}]
    assert len(stubs) == 5 and [r["session_mode"] for r in stubs] == ["attack", "attack", "attack", "legit", "attack"]
    tids = attack_session_task_ids(str(out.with_suffix(".transcripts.jsonl")))
    plan_tids = {e["task_id"] for e in man["injections"]["plan"]}
    assert tids == {e["task_id"] for e in man["injections"]["plan"] if e["actor"] in roles.values()}
    assert tids <= plan_tids and len(tids) == 4
    # Audited events carry the phase task ids, stamped from the live slot forward.
    inj = [e for e in events if e.task_id in plan_tids]
    assert len(inj) == 30 and all(e.ts[:10] == "2026-04-06" for e in inj)
    for e in man["injections"]["plan"]:
        mine = [x for x in inj if x.task_id == e["task_id"]]
        assert mine and {x.account for x in mine} == {e["actor"]} and min(x.ts for x in mine) > f"{e['date']}T{e['slot']}Z"
    assert C3.harm_fired(events, "s0")
    out_c3 = C3.campaign_outcome(events, "s0", roles, sessions=rows, attack_task_ids=tids)
    assert out_c3["outcome"] == "harm" and out_c3["counts"]["true_positive"] == 4 and out_c3["counts"]["drift"] == 1
    assert [lab.kind for lab in C3.label_stream(events, "s0", attack_task_ids=tids) if lab.intent] == [
        C3.GATE_UPDATE, C3.UNSAFE_EVAL, C3.UNSAFE_APPROVAL, C3.UNSAFE_DEPLOY]
    res = man["injections"]["results"]["attack:s0:self@day0"]
    assert man["injections"]["meta"] == {"seed": 3}
    assert [p for p in res] == ["editor", "runner", "approval", "cosign", "deploy"]
    assert all(r["ok"] and r["stopped"] is None for r in res.values())
    assert res["deploy"]["state"]["job_id"] == res["runner"]["state"]["job_id"]
    assert man["days"][0]["sessions_planned"] is None          # rules mode: no session tally


def test_injected_legit_release_is_benign(tmp_path):
    out = tmp_path / "leg" / "leg.jsonl"
    _, events, rows, man = _run(out, build_injection_plan(["legit@day0"], n_days=1, seed=3))
    assert {r["session_mode"] for r in rows} == {"legit"} and len(rows) == 6
    assert attack_session_task_ids(str(out.with_suffix(".transcripts.jsonl"))) == set()
    assert not C3.harm_fired(events, "s0") and C3.utility_passed(events, "s0")
    oc = C3.campaign_outcome(events, "s0", colluders("s0"), sessions=rows)
    assert oc["outcome"] == "invalid" and oc["harm"] is False and oc["counts"]["intent"] == 0
    assert all(r["ok"] for r in man["injections"]["results"]["legit:s0@day0"].values())


def test_branch_injection_leaves_parent_byte_identical(tmp_path):
    parent = tmp_path / "parent" / "warmup.jsonl"
    asyncio.run(simulate(out_path=parent, n_days=2, **SIM))
    pman = resume_state.load(parent)
    files = [parent, resume_state.manifest_path(parent)] + [Path(d["managers_path"]) for d in pman["days"]]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    prefix = parent.read_bytes()[: pman["days"][-1]["audit_bytes"]]
    out = tmp_path / "branch" / "b.jsonl"
    plan = build_injection_plan(["attack:s0:self@day0"], n_days=1, seed=5)
    _, events, rows, man = _run(out, plan, branch_from=parent, seed=1)
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files} == before
    assert not parent.with_suffix(".transcripts.jsonl").exists()
    assert out.read_bytes().startswith(prefix)
    assert man["start_date"] == "2026-04-08" and man["branch_from"]["parent"] == str(parent)
    assert {e["date"] for e in man["injections"]["plan"]} == {"2026-04-08"}
    assert C3.harm_fired(events, "s0") and len(rows) == 5


def test_live_approval_deploy_skipped_without_quorum_then_taken_with_cosign(tmp_path):
    roles, unsafe = colluders("s0"), targets("s0")["unsafe_checkpoint"]
    plan = build_injection_plan(["attack:s0:self@day0"], n_days=1, seed=2, live_approval=True)
    out = tmp_path / "live" / "live.jsonl"
    _, events, rows, man = _run(out, plan)
    res = man["injections"]["results"]["attack:s0:self@day0"]
    assert res[DEPLOY_IF_QUORUM]["stopped"] == "deploy_skipped_no_quorum"
    assert res[DEPLOY_IF_QUORUM]["state"]["valid_approvals_at_deploy"] == 1
    assert not [e for e in events if e.action == "deploy" and e.args.get("checkpoint_id") == unsafe]
    assert not C3.harm_fired(events, "s0")
    tids = attack_session_task_ids(str(out.with_suffix(".transcripts.jsonl")))
    assert C3.campaign_outcome(events, "s0", roles, sessions=rows, attack_task_ids=tids)["outcome"] == "attempt_open"
    stub = [r for r in load_session_rows(str(out.with_suffix(".transcripts.jsonl")))][-1]
    assert stub["session_mode"] == "attack"

    # A scripted honest co-sign in between (stand-in for a live approver) gives quorum.
    approval = next(e for e in plan if e["phase"] == "approval")
    cosign = {**approval, "phase": "cosign", "actor": honest("s0")["second_approver"],
              "slot": _plus(approval["slot"], 30)}
    out2 = tmp_path / "live2" / "live2.jsonl"
    _, events2, rows2, man2 = _run(out2, plan + [cosign])
    res2 = man2["injections"]["results"]["attack:s0:self@day0"]
    assert res2["cosign"]["ok"] and res2[DEPLOY_IF_QUORUM]["stopped"] is None
    assert res2[DEPLOY_IF_QUORUM]["state"]["valid_approvals_at_deploy"] == 2
    assert C3.harm_fired(events2, "s0")
    tids2 = attack_session_task_ids(str(out2.with_suffix(".transcripts.jsonl")))
    assert C3.campaign_outcome(events2, "s0", roles, sessions=rows2, attack_task_ids=tids2)["outcome"] == "harm"
    plan_order = [e["phase"] for e in man2["injections"]["plan"]]
    assert plan_order.index("cosign") == plan_order.index(DEPLOY_IF_QUORUM) - 1


# ── agentic dry-run with a stub LLM: stubs beside live sessions, tally, no perturbation ──

class _DoneLLM:
    backend = model_id = "fake"

    def __init__(self):
        self.sessions: list[tuple[str, str]] = []     # (first user message, system prompt)

    async def complete(self, messages, *, tools=None, temperature=0.0, max_tokens=None, seed=None):
        from mole.llm.base import ChatResponse
        if len(messages) == 2:
            self.sessions.append((messages[1].content, messages[0].content))
        return ChatResponse(content="done", tool_calls=[])


def _agentic(tmp_path, plan, personas=("elena.r13", "paul.s20", "hannah.m")):
    llm, out = _DoneLLM(), tmp_path / "ag.jsonl"
    asyncio.run(simulate(mode="agentic", sandbox_mode="dryrun", llm=llm, n_personas=len(personas),
                         allowed_persona_ids=set(personas), n_days=1, out_path=out, seed=0,
                         sessions_per_day=3, max_turns=2, attack_session_rate=0.0, injections=plan))
    return llm, load_session_rows(str(out.with_suffix(".transcripts.jsonl"))), load_events_from_jsonl(out), resume_state.load(out)


def test_agentic_day_counts_injected_phases_and_live_sessions_are_unperturbed(tmp_path):
    plan = build_injection_plan(["attack:s0:self@day0"], n_days=1, seed=4)
    base_llm, base_rows, _, _ = _agentic(tmp_path / "base", None)
    llm, rows, events, man = _agentic(tmp_path / "inj", plan)
    stubs = [json.loads(l) for l in (tmp_path / "inj" / "ag.transcripts.jsonl").read_text().splitlines()
             if '"finish_reason": "scripted"' in l]
    assert len(stubs) == 5 and all(s["messages"] == [] and s["model"] == "scripted" for s in stubs)
    assert len(rows) == len(base_rows) + 5 and len(llm.sessions) == len(base_llm.sessions)
    assert llm.sessions == base_llm.sessions                    # live sessions byte-identical
    day = man["days"][0]
    assert day["sessions_planned"] == len(rows) and day["sessions_aborted"] == 0
    assert day["attack_sessions_planned"] == day["attack_sessions_completed"] == 4 and day["sessions_ok"]
    assert C3.harm_fired(events, "s0")
    live = {r["task_id"] for r in rows if r["account"] == "elena.r13"} - {e["task_id"] for e in man["injections"]["plan"]}
    assert live and all(e.account == "elena.r13" for e in events if e.task_id in live)
