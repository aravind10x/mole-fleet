"""Snapshot (managers.json round trip) and branching a corpus from a parent.

All without an LLM or Docker: the managers are driven directly, and the
end-to-end branch test uses simulate(mode="rules", sandbox_mode="dryrun").
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

from mole.audit.collector import AuditCollector
from mole.audit.schema import AuditEvent
from mole.generator import resume_state
from mole.generator.run import INPROCESS_ENVS, build_context, simulate
from mole.sandbox.state_export import export_manager_state, import_manager_state


# ── (a) managers.json round trip ─────────────────────────────────────────


async def _mutate_world(ctx) -> str:
    """A handful of audited mutations covering every in-process manager.
    Returns the checkpoint that ends up with two approvals."""
    m = ctx._managers
    reg, ev = m["model_registry"], m["eval_server"]
    ck = await reg.register_checkpoint(model_id="prometheus", version="0.5-rc1",
                                       dataset_hash="sha256-prometheus-0.5",
                                       account="bob.li", description="round-trip rc")
    cid = ck["checkpoint_id"]
    cur = ev.current_config("release-gate")["config"]
    await ev.update_config(config_id="release-gate", config=dict(cur), account="kara.p",
                           reason="quarterly re-baseline")
    job = await ev.submit_eval(checkpoint_id=cid, config_id="release-gate", account="kara.p")
    assert job["passed"] is True
    await reg.tag_approved(checkpoint_id=cid, account="alice.kim")
    await reg.tag_approved(checkpoint_id=cid, account="ivan.o")
    await reg.deploy(checkpoint_id=cid, environment="staging", account="alice.kim")
    await m["plane"].create_issue(project_id="OPS", sender="alice.kim",
                                  name="OPS-90: round-trip ticket", description="x")
    await m["secrets_store"].rotate(key="wandb-prod", account="frank.s")
    await m["secrets_store"].set_access_policy(key="wandb-prod",
                                               group_allowlist=["infra-admins"])
    await m["org"].add_group_member(group="model-approval", account="kara.p")
    return cid


def test_managers_json_round_trip_is_byte_identical(tmp_path):
    async def _run():
        c1 = AuditCollector(jsonl_path=tmp_path / "a.jsonl")
        ctx1 = await build_context(c1, tmp_dir=tmp_path, envs=INPROCESS_ENVS, seed_world=True)
        cid = await _mutate_world(ctx1)
        assert len({e.service for e in c1.events}) == len(INPROCESS_ENVS)
        export_manager_state(ctx1, tmp_path / "one" / "managers.json")

        c2 = AuditCollector(jsonl_path=tmp_path / "b.jsonl")
        ctx2 = await build_context(c2, tmp_dir=tmp_path, envs=INPROCESS_ENVS, seed_world=True)
        applied = import_manager_state(ctx2, tmp_path / "one" / "managers.json")
        assert set(applied) == set(INPROCESS_ENVS)
        assert {"_hidden_outcomes", "_costs", "_configs", "_spend"} <= set(applied["eval_server"])
        assert "_approvals" in applied["model_registry"]
        export_manager_state(ctx2, tmp_path / "two" / "managers.json")
        c1.close(); c2.close()
        return ctx1, ctx2, cid

    ctx1, ctx2, cid = asyncio.run(_run())
    one = (tmp_path / "one" / "managers.json").read_bytes()
    two = (tmp_path / "two" / "managers.json").read_bytes()
    assert one == two
    assert "_eval_server" not in json.loads(one)["model_registry"]

    reg1, reg2 = ctx1._managers["model_registry"], ctx2._managers["model_registry"]
    assert len(reg1.valid_approvals(cid)) == 2
    assert reg2.valid_approvals(cid) == reg1.valid_approvals(cid)
    # The imported approvals still satisfy the production gate (eval link intact).
    assert reg2._check_release_gate(cid)["approvers"] == ["alice.kim", "ivan.o"]
    # Org indexes stay aliased to _doc after import (a later mutation shows in both).
    org2 = ctx2._managers["org"]
    asyncio.run(org2.add_group_member(group="ops", account="kara.p"))
    doc_groups = {g["id"]: g for g in org2._doc["groups"]}
    assert "kara.p" in doc_groups["ops"]["members"]


# ── (b) branch divergence end to end ─────────────────────────────────────


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _rows(data: bytes) -> list[dict]:
    return [json.loads(l) for l in data.splitlines() if l.strip()]


def test_branches_diverge_from_parent_without_touching_it(tmp_path):
    parent = tmp_path / "parent" / "warmup.jsonl"
    asyncio.run(simulate(mode="rules", sandbox_mode="dryrun", n_personas=10, n_days=2,
                         sessions_per_day=3, seed=0, out_path=parent))
    pman = resume_state.load(parent)
    last = resume_state.last_completed_record(pman)
    parent_files = [parent, resume_state.manifest_path(parent)] + [
        Path(d["managers_path"]) for d in pman["days"]]
    before = {p: _sha(p) for p in parent_files}
    prefix = parent.read_bytes()[: last["audit_bytes"]]

    outs = {}
    for seed, name in ((1, "branch_a"), (2, "branch_b")):
        out = tmp_path / name / f"{name}.jsonl"
        coll = asyncio.run(simulate(mode="rules", sandbox_mode="dryrun", n_personas=10,
                                    n_days=1, sessions_per_day=3, seed=seed,
                                    out_path=out, branch_from=parent))
        outs[name] = (out, coll)

    assert {p: _sha(p) for p in parent_files} == before          # parent untouched
    parent_ids = {r["event_id"] for r in _rows(prefix)}

    tails, mans = {}, {}
    for name, (out, coll) in outs.items():
        data = out.read_bytes()
        assert data.startswith(prefix)
        tails[name] = _rows(data[len(prefix):])
        assert tails[name], f"{name} produced no events of its own"
        # The recap sees the parent's history: preloaded events are in memory.
        assert parent_ids <= {e.event_id for e in coll.events}
        man = resume_state.load(out)
        mans[name] = man
        assert man["branch_from"]["parent"] == str(parent)
        assert man["branch_from"]["day"] == last["day"]
        assert man["start_date"] == "2026-04-08"                  # weekday after 04-07
        assert [d["day"] for d in man["days"]] == ["2026-04-08"]
        assert man["sandbox_mode"] == "dryrun"
        assert all(r["ts"][:10] == "2026-04-08" for r in tails[name])

    a, b = tails["branch_a"], tails["branch_b"]
    assert not ({r["event_id"] for r in a} & {r["event_id"] for r in b})
    assert [(r["account"], r["action"]) for r in a] != [(r["account"], r["action"]) for r in b]

    m_parent = Path(last["managers_path"]).read_bytes()
    m_a = Path(mans["branch_a"]["days"][0]["managers_path"]).read_bytes()
    m_b = Path(mans["branch_b"]["days"][0]["managers_path"]).read_bytes()
    assert m_a != m_b and m_a != m_parent and m_b != m_parent
    # Branch state builds on the parent's: every parent eval job is still there.
    parent_jobs = set(json.loads(m_parent)["eval_server"]["_jobs"])
    assert parent_jobs and parent_jobs <= set(json.loads(m_a)["eval_server"]["_jobs"])


# ── (c) preload ──────────────────────────────────────────────────────────


def test_preload_loads_events_without_writing_them(tmp_path):
    src = tmp_path / "src.jsonl"
    writer = AuditCollector(jsonl_path=src)
    for i in range(5):
        writer.emit(AuditEvent.new(account=f"u{i}", account_kind="background_rules_agent",
                                   service="plane", action="create_issue",
                                   resource_id=f"OPS-{i}", args={}))
    writer.close()
    lines = src.read_bytes().splitlines(keepends=True)

    dst = tmp_path / "own.jsonl"
    reader = AuditCollector(jsonl_path=dst)
    assert reader.preload(src) == 5
    assert [e.account for e in reader.events] == [f"u{i}" for i in range(5)]
    # A cut in the middle of the 4th record keeps only the 3 complete ones.
    cut = len(b"".join(lines[:3])) + 10
    assert reader.preload(src, up_to_bytes=cut) == 3
    assert len(reader.events) == 8
    reader.close()
    assert dst.read_bytes() == b""                                # nothing written
