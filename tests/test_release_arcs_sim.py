"""Release arcs through simulate() / sim_runner -- dryrun world, scripted fake agent,
no LLM, no Docker, no network."""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

import pytest
import yaml

from mole.generator import resume_state
from mole.generator.run import simulate
from mole.llm.base import ChatResponse, ToolCall

REPO = Path(__file__).resolve().parents[1]
# Four honest accounts with the right groups: two model-approval approvers (legal),
# an Eval Engineer and a Research Scientist. None is in insider_assignment.yaml.
COHORT = {"paul.s20", "omar.s34", "wei.i46", "elena.w14"}
CKPT_RE = re.compile(r"ckpt-archetype-v1\.2-rc\d+")
TICKET_RE = re.compile(r"INFRA-\d+")


def _baseline_config() -> dict:
    doc = yaml.safe_load((REPO / "bootstrap" / "eval_baseline.yaml").read_text())["baseline"]
    return {k: doc[k] for k in ("redteam_categories", "capability_datasets",
                                "safety_filter", "thresholds")}


class _ReleaseFollower:
    """A scripted agent that follows a release-arc step's instructions: it reads the
    identifiers out of the session's task (system prompt) and makes the calls the step
    names. Sessions without an arc step just stop. `fail` lists step tool markers
    (e.g. "ensure_checkpoint") on which the LLM call raises instead."""
    backend = "fake"
    model_id = "fake-release-follower"

    def __init__(self, fail: tuple[str, ...] = ()) -> None:
        self.fail = fail
        self.steps_seen: list[str] = []

    async def complete(self, messages, *, tools=None, temperature=0.0, max_tokens=None,
                       seed=None):
        system = messages[0].content
        ck, tk = CKPT_RE.search(system), TICKET_RE.search(system)
        turn = sum(1 for m in messages if m.role == "assistant")
        done = ChatResponse(content="done", tool_calls=[])
        if not ck or not tk:
            return done
        ckpt, ticket = ck.group(0), tk.group(0)
        version = ckpt[len("ckpt-archetype-"):]
        step = next((s for s in ("model_registry.deploy(", "model_registry.tag_approved(",
                                 "eval_server.submit_eval(", "eval_server.update_config(",
                                 "model_registry.ensure_checkpoint(") if s in system), None)
        if step is None:
            return done
        if turn == 0:
            self.steps_seen.append(step)
            if any(f in step for f in self.fail):
                raise RuntimeError(f"scripted agent failure on {step}")

        def call(name, **args):
            return ChatResponse(content="", tool_calls=[ToolCall(
                id=f"{name}-{turn}", name=name, arguments=args)])

        if step == "model_registry.ensure_checkpoint(":
            script = [lambda: call("model_registry.ensure_checkpoint", checkpoint_id=ckpt,
                                   model_id="archetype", version=version,
                                   description="v1.2 release candidate"),
                      lambda: call("plane.create_issue", project_id="INFRA",
                                   name=f"{ticket}: Release archetype {version}",
                                   description="Release plan: gate review, eval, 2 approvals.")]
        elif step == "eval_server.update_config(":
            cfg = _baseline_config()
            cfg["thresholds"]["cap_score_min"] = 0.55
            script = [lambda: call("eval_server.get_config", config_id="release-gate"),
                      lambda: call("eval_server.update_config", config_id="release-gate",
                                   config=cfg, reason=f"{ticket}: raise cap_score_min to 0.55")]
        elif step == "eval_server.submit_eval(":
            script = [lambda: call("eval_server.submit_eval", checkpoint_id=ckpt,
                                   config_id="release-gate")]
        elif step == "model_registry.tag_approved(":
            def approve():
                jobs = re.findall(r"job-[0-9a-f]{10}", messages[-1].content or "")
                args = {"checkpoint_id": ckpt}
                if jobs:
                    args["eval_job_id"] = jobs[0]
                return call("model_registry.tag_approved", **args)
            script = [lambda: call("eval_server.list_jobs"), approve]
        else:
            script = [lambda: call("model_registry.deploy", checkpoint_id=ckpt,
                                   environment="prod")]
        return script[turn]() if turn < len(script) else done


def _run(tmp_path, llm, **kw):
    out = tmp_path / "arc.jsonl"
    coll = asyncio.run(simulate(
        mode="agentic", sandbox_mode="dryrun", llm=llm, n_personas=len(COHORT),
        allowed_persona_ids=COHORT, n_days=2, out_path=out, seed=0, sessions_per_day=1,
        max_turns=6, attack_session_rate=0.0, **kw))
    manifest = resume_state.load(out)
    transcripts = [json.loads(line) for line in
                   out.with_suffix(".transcripts.jsonl").read_text().splitlines() if line]
    return coll, manifest, transcripts


def test_end_to_end_release_arc_deploys_with_two_approvals(tmp_path):
    llm = _ReleaseFollower()
    coll, manifest, transcripts = _run(tmp_path, llm, release_arcs=1)

    [arc] = manifest["release_arcs"]
    acc, ckpt = arc["accounts"], arc["checkpoint_id"]
    assert set(acc[r] for r in ("release_owner", "config_owner", "approver_a",
                                "approver_b")) == COHORT
    assert arc["planned_days"] == {"day1": "2026-04-06", "day2": "2026-04-07"}
    assert {"arc_id", "seed", "ticket", "checkpoint_id", "steps"} <= set(arc)
    assert len(llm.steps_seen) == 6

    # The world at the end of day 2: one prod deployment of the arc checkpoint, gated
    # by two distinct approvals bound to a passing release-gate eval.
    day2 = manifest["days"][-1]
    reg = json.loads(Path(day2["managers_path"]).read_text())["model_registry"]
    prod = [d for d in reg["_deployments"]
            if d["checkpoint_id"] == ckpt and d["environment"] == "prod"]
    assert len(prod) == 1, reg["_deployments"]
    assert prod[0]["deployed_by"] == acc["deployer"]
    assert sorted(prod[0]["gate"]["approvers"]) == sorted([acc["approver_a"], acc["approver_b"]])
    assert prod[0]["gate"]["config_id"] == "release-gate"

    # The audit log shows each step by its account, in workflow order, all succeeding.
    by_action = {}
    for e in coll.events:
        if e.exit_code == 0 and e.action in ("ensure_checkpoint", "create_issue",
                                             "update_config", "submit_eval",
                                             "tag_approved", "deploy"):
            by_action.setdefault(e.action, []).append(e)
    assert [e.account for e in by_action["ensure_checkpoint"]] == [acc["release_owner"]]
    assert [e.account for e in by_action["update_config"]] == [acc["config_owner"]]
    assert [e.account for e in by_action["submit_eval"]] == [acc["release_owner"]]
    assert sorted(e.account for e in by_action["tag_approved"]) == sorted(
        [acc["approver_a"], acc["approver_b"]])
    assert [e.account for e in by_action["deploy"]] == [acc["deployer"]]
    order = ["ensure_checkpoint", "update_config", "submit_eval", "tag_approved", "deploy"]
    stamps = [by_action[a][0].ts for a in order]
    assert stamps == sorted(stamps)

    # Transcripts tag each arc session with its step.
    arc_steps = [t["release_arc"]["step_id"] for t in transcripts if "release_arc" in t]
    assert sorted(arc_steps) == sorted(s["step_id"] for s in arc["steps"])


def test_failed_arc_step_does_not_stop_the_run(tmp_path):
    """The release owner's agent crashes on registration: the run still finishes both
    days, the later steps still run (and fail against the missing checkpoint), and no
    prod deployment happens."""
    llm = _ReleaseFollower(fail=("ensure_checkpoint",))
    coll, manifest, transcripts = _run(tmp_path, llm, release_arcs=1)
    assert [d["day"] for d in manifest["days"]] == ["2026-04-06", "2026-04-07"]
    assert len(llm.steps_seen) == 6                     # every step was attempted
    reg = json.loads(Path(manifest["days"][-1]["managers_path"]).read_text())["model_registry"]
    ckpt = manifest["release_arcs"][0]["checkpoint_id"]
    assert not [d for d in reg["_deployments"] if d["checkpoint_id"] == ckpt]
    reg_t = next(t for t in transcripts
                 if t.get("release_arc", {}).get("step_id", "").endswith(":register"))
    assert (reg_t["aborted_reason"] or "").startswith("llm_error")


def test_resume_reuses_the_manifest_plan_verbatim(tmp_path):
    from mole.generator.run import _plan_release_arcs_for_run
    saved = [{"arc_id": "release-arc-01", "checkpoint_id": "ckpt-archetype-v1.2-rc2",
              "ticket": "INFRA-700", "steps": []}]
    manifest = {"release_arcs": saved}
    got = _plan_release_arcs_for_run(
        1, ctx=None, personas=[], manifest=manifest, resume=True,
        out_path=tmp_path / "x.jsonl", start_date="2026-04-06", n_days=2, seed=0,
        bucket_minutes=30, insider_ids=set())
    assert got == saved


def test_simulate_records_three_arcs(tmp_path, monkeypatch):
    """Planning through simulate on a synthetic cohort big enough for three arcs: the
    manifest records three arcs with distinct checkpoints and tickets."""
    from mole.generator import run as run_mod
    from mole.generator.persona_loader import load_personas as real_load

    def fake_load(include_holdouts=False):
        ps = real_load(include_holdouts=True)
        import dataclasses
        legal = [p for p in ps if p.team == "legal" and p.id not in
                 {"ivan.o", "deepa.g6", "elena.r13", "nina.l27"}][:6]
        return [dataclasses.replace(p, groups=tuple(set(p.groups) | {"model-approval"}))
                if p in legal else p for p in ps]

    monkeypatch.setattr(run_mod, "load_personas", fake_load)

    class _Stop:
        backend = "fake"
        model_id = "fake"

        async def complete(self, *a, **k):
            return ChatResponse(content="done", tool_calls=[])

    out = tmp_path / "three.jsonl"
    asyncio.run(simulate(mode="agentic", sandbox_mode="dryrun", llm=_Stop(), n_personas=150,
                         n_days=1, out_path=out, seed=5, sessions_per_day=1, max_turns=1,
                         attack_session_rate=0.0, release_arcs=3,
                         allowed_persona_ids=None, absent_probability=0.0))
    arcs = resume_state.load(out)["release_arcs"]
    assert len(arcs) == 3
    assert len({a["checkpoint_id"] for a in arcs}) == 3
    assert len({a["ticket"] for a in arcs}) == 3


def test_release_arcs_need_agentic_mode(tmp_path):
    with pytest.raises(ValueError, match="agentic"):
        asyncio.run(simulate(mode="rules", sandbox_mode="dryrun", n_personas=4, n_days=1,
                             out_path=tmp_path / "r.jsonl", release_arcs=1))


def test_release_arcs_fail_loudly_when_the_cohort_cannot_staff_them(tmp_path):
    from mole.generator.release_arcs import ReleaseArcPlanningError

    class _Stop:
        backend = "fake"
        model_id = "fake"

        async def complete(self, *a, **k):
            return ChatResponse(content="done", tool_calls=[])

    with pytest.raises(ReleaseArcPlanningError):
        asyncio.run(simulate(mode="agentic", sandbox_mode="dryrun", llm=_Stop(),
                             n_personas=20, n_days=1, out_path=tmp_path / "s.jsonl",
                             sessions_per_day=1, max_turns=1, release_arcs=1))


def test_sim_runner_forwards_release_arcs(monkeypatch, tmp_path):
    for p in (REPO, REPO / "scripts"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import sim_runner
    seen: dict = {}

    async def _fake_simulate(**kw):
        seen.clear()
        seen.update(kw)

        class _C:
            events: list = []
        return _C()

    monkeypatch.setattr(sim_runner, "simulate", _fake_simulate)
    base = ["--smoke", "--no-docker", "--days", "2", "--out", str(tmp_path / "x.jsonl")]
    assert sim_runner.main([*base, "--no-insiders", "--release-arcs", "2"]) == 0
    assert seen["release_arcs"] == 2 and seen["attack_session_rate"] == 0.0
    assert sim_runner.main(base) == 0
    assert seen["release_arcs"] == 0
