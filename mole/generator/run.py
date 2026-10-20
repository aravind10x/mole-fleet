"""Generator runner.

    python -m mole.generator.run --personas 3 --days 5 --out npc_audit.jsonl

Produces a benign-only audit log: N personas act over D simulated days
against the in-process data managers (org / model_registry / eval_server
/ secrets_store), with every call captured by the AuditCollector and
attributed to the acting background account (account_kind="background_rules_agent"). Deterministic for a
given --seed, so FACADE pretraining data is reproducible.

No containers are required — the data managers self-load from the
bootstrap YAML fixtures. This is the benign baseline Phase-2 monitors
train on (real agent traces from threat runs are the contrast).
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from ..audit.collector import AuditCollector
from ..audit.io_retry import is_disk_full, retry_on_disk_full
from ..sandbox.base import DryRunSandbox
from ..state.composite import CompositeStateManager
from . import resume_state
from .member import Member, NPCConfig
from .persona_loader import load_personas


class AuthCircuitBreakerError(RuntimeError):
    """Raised to halt a run after too many consecutive auth failures.

    Guards against the failure mode that silently destroyed an overnight kimi
    corpus: the token daemon died, every subsequent session got a 401, but the
    per-session `except` swallowed it and the sim marched on, accumulating
    thousands of empty auth-failed sessions. We'd rather stop and resume than
    burn the run writing garbage.
    """


# ── session-level (bucket-granular) resume: day-plan (de)serialization ──────
# For --session-resume, the interrupted day's plan is persisted so a warm resume
# reproduces the EXACT slots + attack schedule without re-running plan_day (which,
# on a fresh process whose per-member RNG is back at its day-0 state, would produce
# a different schedule). Statistically-equivalent fidelity: the schedule is pinned;
# within-session RNG draws for the re-run buckets are fresh (accepted).


def _serialize_day_plan(day_plan: list[tuple[Any, Any, str]]) -> list[list[str]]:
    """[(slot_datetime, member, key)] -> JSON-safe [[iso_ts, persona_id, key], ...]."""
    return [[t.isoformat(), m.persona.id, key] for (t, m, key) in day_plan]


def _session_index(key: str) -> int:
    """Slot index i from a "session_<i>" key. plan_day emits _today_keys in this
    order and the attack-slot pick indexes into it, so restore must match it."""
    try:
        return int(key.rsplit("_", 1)[-1])
    except (ValueError, IndexError):
        return 0


def _restore_day_plan(saved: list[list[str]], members: list[Any],
                      runners: list[Any] = ()) -> list[tuple[Any, Any, str]]:
    """Rebuild [(slot_datetime, member, key)] from a serialized plan and re-set each
    member's `_today_keys` (which plan_day would have set) so the deterministic
    attack-slot selection matches the pre-crash run. Members absent from the plan get
    an empty `_today_keys` (PTO / fully loafed that day). "inject:" keys map to the
    injection `runners` (an injected actor may also be a live member)."""
    from .injection import INJECT_KEY_PREFIX
    by_id = {getattr(m, "persona", m).id: m for m in members}
    runner_by_id = {r.persona.id: r for r in runners}
    plan: list[tuple[Any, Any, str]] = []
    keys_by_member: dict[int, list[str]] = {}
    for t_iso, member_id, key in saved:
        m = (runner_by_id if key.startswith(INJECT_KEY_PREFIX) else by_id).get(member_id)
        if m is None:
            continue                       # roster changed — shouldn't happen on resume
        plan.append((datetime.fromisoformat(t_iso), m, key))
        keys_by_member.setdefault(id(m), []).append(key)
    plan.sort(key=lambda x: x[0])
    for m in members:
        # Dedicated arc-step sessions ("arc:<step_id>") are not in plan_day's slot pool.
        keys = [k for k in keys_by_member.get(id(m), []) if not k.startswith("arc:")]
        m._today_keys = sorted(keys, key=_session_index)   # plan_day order (by slot index)
    return plan


def _world_ids(ctx: Any) -> tuple[set[str], set[str]]:
    """(checkpoint ids, plane ticket ids) already present in the in-process world."""
    managers = getattr(ctx, "_managers", {}) or {}
    ckpts = set(getattr(managers.get("model_registry"), "_checkpoints", {}) or {})
    tickets: set[str] = set()
    for ws in (getattr(managers.get("plane"), "_state", {}) or {}).values():
        tickets |= set((ws or {}).get("issues") or {})
    return ckpts, tickets


def _plan_release_arcs_for_run(
    n_arcs: int, *, ctx: Any, personas: list[Any], manifest: dict[str, Any],
    resume: bool, out_path: Path, start_date: str, n_days: int, seed: int | None,
    bucket_minutes: int, insider_ids: set[str],
) -> list[dict[str, Any]]:
    """Plan (or, on --resume, reload) the run's release arcs and record them in the
    manifest under "release_arcs". Every account in bootstrap/insider_assignment.yaml
    plus `insider_ids` is excluded from casting. Returns [] when n_arcs <= 0."""
    if resume and manifest.get("release_arcs") is not None:
        plans = list(manifest["release_arcs"])
        logger.info("--resume: reusing %d release arc(s) from the manifest", len(plans))
        return plans
    if n_arcs <= 0:
        return []
    from .release_arcs import load_insider_accounts, plan_release_arcs
    ckpts, tickets = _world_ids(ctx)
    plans = plan_release_arcs(
        n_arcs, personas, _weekday_dates(date.fromisoformat(start_date), n_days),
        seed=seed, insider_ids=load_insider_accounts() | set(insider_ids),
        bucket_minutes=bucket_minutes, taken_checkpoint_ids=ckpts, taken_ticket_ids=tickets)
    for arc in plans:
        logger.info("release arc %s: %s ticket %s days %s accounts %s",
                    arc["arc_id"], arc["checkpoint_id"], arc["ticket"],
                    arc["planned_days"], arc["accounts"])
    manifest["release_arcs"] = plans
    resume_state.write_atomic(manifest, out_path)
    return plans


def parse_pin_task(spec: str) -> tuple[str, int, str]:
    """Parse a --pin-task value ``ACCOUNT:DAY_INDEX:TASK_ID`` -> (account, day, task_id).

    DAY_INDEX is a 0-based index into the run's working days (negative counts from the
    end: -1 = the last day). TASK_ID is a task-bank id ``<bank_key>/<i>`` (see
    agentic_member.load_task_bank_ids). Raises ValueError on a malformed value."""
    parts = str(spec).split(":", 2)
    if len(parts) != 3 or not all(p.strip() for p in parts):
        raise ValueError(f"--pin-task wants ACCOUNT:DAY_INDEX:TASK_ID, got {spec!r}")
    account, day, task_id = (p.strip() for p in parts)
    try:
        day_index = int(day)
    except ValueError:
        raise ValueError(f"--pin-task DAY_INDEX must be an integer, got {day!r}") from None
    return account, day_index, task_id


def parse_pin_slot(spec: str) -> tuple[str, int, str, str]:
    """Parse a --pin-slot value ``ACCOUNT:DAY_INDEX:TASK_ID@HH:MM`` ->
    (account, day_index, task_id, "HH:MM:00").

    Like --pin-task, but the task runs in a DEDICATED session at that sim time of the
    day (the release-arc slot machinery), not in the account's first session, so it can
    be placed AFTER another account's session (e.g. the routine co-sign ten minutes
    after the colluding approver's slot). Raises ValueError on a malformed value."""
    text = str(spec)
    if "@" not in text:
        raise ValueError(f"--pin-slot wants ACCOUNT:DAY_INDEX:TASK_ID@HH:MM, got {spec!r}")
    head, _, clock = text.rpartition("@")
    account, day_index, task_id = parse_pin_task(head)
    parts = clock.strip().split(":")
    if len(parts) not in (2, 3) or not all(x.isdigit() for x in parts):
        raise ValueError(f"--pin-slot time must be HH:MM, got {clock!r}")
    hh, mm = int(parts[0]), int(parts[1])
    ss = int(parts[2]) if len(parts) == 3 else 0
    if not (0 <= hh < 24 and 0 <= mm < 60 and 0 <= ss < 60):
        raise ValueError(f"--pin-slot time out of range: {clock!r}")
    return account, day_index, task_id, f"{hh:02d}:{mm:02d}:{ss:02d}"


def _resolve_pins(
    pins: list[tuple] | None, *, personas: list[Any], dates: list[str],
    sandbox_mode: str, task_bank_path: str | None = None,
) -> tuple[dict[str, dict[str, dict[str, str]]], list[dict[str, Any]]]:
    """--pin-task / --pin-slot specs -> ({account: {date: {"task_id", "task"[, "slot"]}}},
    manifest records). A 3-tuple (account, day_index, task_id) pins the account's first
    benign session that day; a 4-tuple (..., "HH:MM:SS") schedules a dedicated session
    at that sim time.

    Task ids resolve against the bank the run draws from (the in-process bank in dryrun,
    the v2 bank in lab mode). Raises ValueError for an account outside the cohort, a day
    index outside the window, an unknown task id, or two pins on one account-day."""
    if not pins:
        return {}, []
    from .agentic_member import load_task_bank_ids
    ids = (load_task_bank_ids(bank="inprocess") if sandbox_mode == "dryrun"
           else load_task_bank_ids(task_bank_path, rich=True))
    cohort = {p.id for p in personas}
    by_account: dict[str, dict[str, dict[str, str]]] = {}
    records: list[dict[str, Any]] = []
    for pin in pins:
        account, day_index, task_id = pin[0], int(pin[1]), pin[2]
        slot = pin[3] if len(pin) > 3 else None
        flag = "--pin-slot" if slot else "--pin-task"
        if account not in cohort:
            raise ValueError(f"{flag} account {account!r} is not in this run's cohort")
        if not -len(dates) <= day_index < len(dates):
            raise ValueError(f"{flag} day index {day_index} is outside the "
                             f"{len(dates)}-day window")
        if task_id not in ids:
            key = task_id.split("/", 1)[0]
            near = sorted(i for i in ids if i.split("/", 1)[0] == key)
            raise ValueError(f"{flag} unknown task id {task_id!r}"
                             + (f"; ids for {key!r}: {near[0]}..{near[-1]}" if near
                                else f"; bank keys: {sorted({i.split('/', 1)[0] for i in ids})}"))
        day = dates[day_index]
        if day in by_account.get(account, {}):
            raise ValueError(f"{flag}: two pins for {account} on {day}")
        entry: dict[str, str] = {"task_id": task_id, "task": ids[task_id]}
        rec: dict[str, Any] = {"account": account, "day_index": day_index, "date": day,
                               "task_id": task_id}
        if slot:
            entry["slot"] = rec["slot"] = slot
        by_account.setdefault(account, {})[day] = entry
        records.append(rec)
    return by_account, records


def _is_auth_error(exc: BaseException) -> bool:
    """True if `exc` (or a cause in its chain) looks like an auth/credential
    failure — an expired/absent token, a 401/403, or a rejected credential —
    as opposed to a model/tool/transport error worth continuing past."""
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        name = type(cur).__name__
        # NB: a per-session complete() 403 (PermissionDeniedError) is normally
        # absorbed by the retry layer now — for some providers a 403 is a *flapping* grant,
        # so retry.py treats it as transient and waits it out instead of letting
        # it surface here. This breaker arm is the backstop for 403s that bypass
        # that path (capped/disabled retry, or auth failures outside complete()):
        # halting beats accumulating empty sessions. 401 still fails fast — a dead
        # token needs a re-mint, not a wait.
        if name in ("AuthenticationError", "PermissionDeniedError"):
            return True
        if getattr(cur, "status_code", None) in (401, 402, 403):
            return True
        msg = str(cur)
        if any(tok in msg for tok in (
            "invalid_token", "invalid_api_key", "Access token has expired",
            "401 Unauthorized", "Unauthorized",
            # OpenRouter: key or account out of credit. Without this the run marches
            # on writing empty sessions (observed 2026-10-07 on the benign-day run).
            "Error code: 402", "requires more credits", "Insufficient credits",
        )):
            return True
        cur = cur.__cause__ or cur.__context__
    return False

logger = logging.getLogger(__name__)

# Rule-based workflows only touch in-process data managers (fast, no containers).
NPC_ENVS: tuple[str, ...] = ("org", "model_registry", "eval_server", "secrets_store")
# Every manager that runs inside this Python process (no Docker service behind
# it). The Docker-free agentic runner (sandbox_mode="dryrun") and rules mode use
# exactly this set.
INPROCESS_ENVS: tuple[str, ...] = (
    "org", "plane", "model_registry", "eval_server", "secrets_store",
)
# simulate(sandbox_mode=...): "lab" starts the Docker LabSandbox in agentic mode
# (the full 9-service surface); "dryrun" uses DryRunSandbox + INPROCESS_ENVS only.
SANDBOX_MODES: tuple[str, ...] = ("lab", "dryrun")
DEFAULT_START_DATE = "2026-04-06"
# Agentic background accounts exercise the full service surface (like the agent), so they
# need the container-backed managers too — same env set the threats use.
# Override with $NPC_AGENTIC_ENVS (comma-separated) to run against a reduced set —
# e.g. dropping gitlab/rocketchat for a fast validation lab. Must match the
# services present in $LAB_COMPOSE (a manager whose container is absent fails setup).
_DEFAULT_AGENTIC_ENVS: tuple[str, ...] = (
    "org", "gitlab", "owncloud", "email", "rocketchat",
    "plane", "model_registry", "eval_server", "secrets_store",
)
AGENTIC_ENVS: tuple[str, ...] = tuple(
    e.strip() for e in os.environ["NPC_AGENTIC_ENVS"].split(",") if e.strip()
) if os.environ.get("NPC_AGENTIC_ENVS") else _DEFAULT_AGENTIC_ENVS


async def build_context(
    collector: AuditCollector,
    *,
    tmp_dir: Path,
    envs: tuple[str, ...] = NPC_ENVS,
    sandbox: Any | None = None,
    seed_world: bool = False,
    class_documents: bool = False,
) -> Any:
    """Build the canonical TaskContext (same path the orchestrator + generator tests
    use): audit-wrapped managers + a mutable account box the Member/AgenticMember
    writes before each session so events attribute to the background account. With `sandbox=None`
    a DryRunSandbox is used (in-process); pass a LabSandbox for full-service
    agentic runs. `seed_world=True` runs seed_org so agentic background accounts act on a
    populated world. `class_documents=True` (with `seed_world`) also seeds the six Stage 3
    class documents in ownCloud (seeders/seed_class_docs.py)."""
    composite = CompositeStateManager(environments=list(envs))
    sandbox = sandbox or DryRunSandbox()
    await composite.setup(sandbox=sandbox)

    if seed_world:
        from types import SimpleNamespace
        from ..seeders.seed_company import seed_company
        try:
            # Seed the ONE shared company world (org + every threat's resources) so
            # benign background accounts act on the same repos/files the attacks use — not an isolated
            # org-only world where they'd invent fictional names.
            counts = await seed_company(SimpleNamespace(**composite.managers))
            logger.info("generator build_context: seeded shared company world: %s", counts)
        except Exception:                                       # noqa: BLE001
            logger.exception("generator build_context: seed_company failed; continuing")
        if class_documents:
            # No try/except: a run that asked for the class must not start without it.
            from ..seeders.seed_class_docs import seed_class_documents
            await seed_class_documents(SimpleNamespace(**composite.managers))

    # Per-task account via ContextVar (see generator/account_context.py) — the
    # earlier mutable-dict box race-corrupted attribution under concurrency.
    from .account_context import get_account
    for svc_name, mgr in composite.managers.items():
        collector.wrap_manager(
            service_name=svc_name,
            manager=mgr,
            account_getter=get_account,
        )

    # Wire the org directory so is_external is classified by the company domain
    # (mirrors orchestrator.py). Without it the collector uses its internal-domain
    # fallback; either way internal mail is no longer mislabeled as egress.
    collector.set_org_lookup(lambda: composite.managers.get("org"))

    ctx = composite.create_context(
        task_dir=tmp_dir,
        sandbox=sandbox,
        audit=collector,
        sim_start="2026-04-06T00:00:00Z",
    )
    # Backward-compat shim — older code paths read `ctx._account_box["account"]`
    # directly. Expose a get-only proxy that resolves to the contextvar value;
    # writes are dropped (the canonical write path is set_account()).
    class _AccountProxy:
        def get(self, k, default=None):
            p, kind = get_account()
            return {"account": p, "kind": kind}.get(k, default)
        def __getitem__(self, k):
            return self.get(k)
        def __setitem__(self, k, v):
            # Quiet no-op; callers should use set_account() directly.
            pass
    ctx._account_box = _AccountProxy()
    ctx.collector = collector
    return ctx


def _dryrun_envs() -> tuple[str, ...]:
    """Env set for a Docker-free agentic run: INPROCESS_ENVS unless
    $NPC_AGENTIC_ENVS (comma-separated) is set, which is honoured as-is."""
    raw = os.environ.get("NPC_AGENTIC_ENVS", "")
    envs = tuple(e.strip() for e in raw.split(",") if e.strip())
    return envs or INPROCESS_ENVS


async def _start_sandbox(sandbox_mode: str, *, session_id: str,
                         restore_rec: dict[str, Any] | None = None,
                         branch_info: dict[str, Any] | None = None) -> Any:
    """Start the sandbox an agentic run acts in. "dryrun" → a DryRunSandbox (no
    Docker). "lab" → a LabSandbox under `session_id`; with `restore_rec` the
    docker volumes are first restored in place from that day's snapshot; with a
    lab `branch_info` (one carrying "snapshot_dir") the parent day's volumes are
    restored into this run's own fresh project before it is brought up."""
    if sandbox_mode == "dryrun":
        return DryRunSandbox()
    from ..sandbox.lab import LabSandbox
    from ..run_task import _default_lab_compose
    if restore_rec is not None:
        from ..sandbox.snapshot import restore_volumes_in_place
        logger.info("--restore-world: restoring docker volumes in-place from "
                    "%s into project %s", restore_rec["snapshot_dir"], session_id)
        await restore_volumes_in_place(restore_rec["snapshot_dir"])
    elif branch_info is not None and branch_info.get("snapshot_dir"):
        from ..sandbox.snapshot import restore_sandbox
        logger.info("branch_from: restoring the parent's docker volumes from %s into "
                    "the fresh project %s", branch_info["snapshot_dir"], session_id)
        res = await restore_sandbox(branch_info["snapshot_dir"], new_session_id=session_id,
                                    compose_project=True)
        restored = {v["volume_name"]: res["volume_remap"].get(v["volume_name"])
                    for v in branch_info["volumes"]}
        if any(new is None for new in restored.values()):
            raise RuntimeError(f"branch_from: volumes not restored: "
                               f"{[k for k, new in restored.items() if new is None]}")
        for v in branch_info["volumes"]:
            v["restored_as"] = restored[v["volume_name"]]
        sandbox = LabSandbox(session_id=session_id, compose_files=[_default_lab_compose()])
        await sandbox.start()
        branch_info["class_documents_at_start"] = await _class_documents_at_start(sandbox)
        return sandbox
    sandbox = LabSandbox(session_id=session_id, compose_files=[_default_lab_compose()])
    await sandbox.start()
    return sandbox


class ResumeStateMissingError(RuntimeError):
    """--resume cannot find the in-process managers.json snapshot (and
    --resume-fresh-state was not passed)."""


def resolve_resume_managers_path(
    manifest: dict[str, Any], audit_path: Path | str, *, resume_fresh_state: bool = False,
) -> Path | None:
    """managers.json to overlay on a plain --resume, or None to keep the day-0 base.

    The in-process managers (org/model_registry/eval_server/secrets_store/plane)
    live in THIS python process, not the docker lab, so a cross-process resume
    must re-import the last committed day's state; otherwise multi-day arcs that
    accumulate model/eval/plane/secret state silently reset under an audit-log
    prefix that already mutated them. Resolution: NPC_RESUME_MANAGERS_PATH wins
    (lets the file live on durable storage, e.g. a shared volume); else the
    manifest's last committed day's managers_path.

    No usable snapshot -> ResumeStateMissingError naming what is missing, unless
    `resume_fresh_state` (then a WARNING, manifest["resume_fresh_state"] = True --
    the caller persists it -- and None). An absent/empty audit log is
    not an error (nothing has mutated the world yet; day-0 base is consistent).
    """
    env_mp = os.environ.get("NPC_RESUME_MANAGERS_PATH", "").strip()
    rec = resume_state.last_completed_record(manifest)
    if env_mp:
        mp, source = env_mp, "NPC_RESUME_MANAGERS_PATH"
    elif rec and rec.get("managers_ok") and (rec.get("managers_path") or "").strip():
        mp, source = rec["managers_path"].strip(), f"manifest managers_path for day {rec['day']}"
    else:
        mp, source = "", ""
    if mp and Path(mp).exists():
        return Path(mp)
    audit_path = Path(audit_path)
    if not mp and (not audit_path.exists() or audit_path.stat().st_size == 0):
        logger.info("--resume: no prior audit events and no managers.json; in-process "
                    "managers start at the day-0 base")
        return None
    if mp:
        missing = f"managers.json {mp} (from {source}) not found"
    else:
        day = rec["day"] if rec else None
        missing = (f"no managers.json snapshot for the last committed day ({day}): "
                   f"NPC_RESUME_MANAGERS_PATH is unset and the manifest records no "
                   f"managers_path" + ("" if rec else " (no committed day)"))
    if not resume_fresh_state:
        raise ResumeStateMissingError(
            f"--resume: {missing}. Refusing to restart the in-process managers "
            f"(org/model_registry/eval_server/secrets_store/plane) from the day-0 base "
            f"under an audit log of {audit_path} that already mutated them. Supply the "
            f"snapshot either (1) via NPC_RESUME_MANAGERS_PATH=<path to the "
            f"day_<YYYY-MM-DD>/managers.json>, or (2) via the resume manifest "
            f"{resume_state.manifest_path(audit_path)} (its last committed day's "
            f"managers_ok + managers_path). Pass --resume-fresh-state to proceed from "
            f"the day-0 base anyway (recorded in the manifest as resume_fresh_state).")
    logger.warning("--resume-fresh-state: %s; in-process managers start at the day-0 base "
                   "(manifest records resume_fresh_state: true)", missing)
    manifest["resume_fresh_state"] = True
    return None


def _import_resume_managers(ctx: Any, managers_path: Path | None) -> None:
    """On a plain --resume, overlay the resolved managers.json (see
    resolve_resume_managers_path) onto the in-process managers; None keeps the
    day-0 base (already logged by the resolver)."""
    if managers_path is None:
        return
    from ..sandbox.state_export import import_manager_state
    applied = import_manager_state(ctx, managers_path)
    logger.info("--resume: imported in-process manager state from %s: %s",
                managers_path, applied)


def _last_managers_record(manifest: dict[str, Any]) -> dict[str, Any] | None:
    """Most recent committed day with an in-process managers.json. The Docker-free
    analogue of resume_state.last_restorable_record (there is no docker snapshot)."""
    for rec in reversed(manifest.get("days") or []):
        if rec.get("managers_ok") and rec.get("managers_path"):
            return rec
    return None


def _next_weekday(day_iso: str) -> str:
    d = date.fromisoformat(day_iso) + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()


def _copy_prefix(src: Path, dst: Path, n_bytes: int) -> None:
    """Write the first `n_bytes` of `src` to `dst` (src is only read)."""
    if src.stat().st_size < n_bytes:
        raise ValueError(f"{src} is {src.stat().st_size} bytes, shorter than the "
                         f"recorded day boundary ({n_bytes} bytes)")
    dst.parent.mkdir(parents=True, exist_ok=True)
    remaining = n_bytes
    with src.open("rb") as fi, dst.open("wb") as fo:
        while remaining > 0:
            chunk = fi.read(min(remaining, 1 << 20))
            if not chunk:
                break
            fo.write(chunk)
            remaining -= len(chunk)


def _prepare_branch(parent_out: Path, out_path: Path,
                    transcript_path: Path,
                    lab_compose_files: list[Path] | None = None) -> dict[str, Any]:
    """Seed a branch run's outputs from a parent corpus.

    Takes the parent's last COMPLETED day boundary (which must have a
    managers.json), copies the parent audit log / transcript truncated to that
    boundary's byte offsets into this run's own paths, and returns the lineage
    record {parent, day, managers_path, next_day}. The parent's files are only
    read, never modified.

    `lab_compose_files` (an agentic lab branch): that same day must also have a
    docker snapshot holding a complete volume set for the compose stack
    (snapshot.branch_volume_set), checked BEFORE anything is copied; the record
    then also carries {snapshot_dir, source_session_id, volumes}."""
    parent_out = Path(parent_out)
    if parent_out.resolve() == out_path.resolve():
        raise ValueError("branch_from must name a different corpus than out_path")
    parent_manifest = resume_state.load(parent_out)
    if parent_manifest is None:
        raise FileNotFoundError(
            f"branch_from: no resume manifest for {parent_out} "
            f"(expected {resume_state.manifest_path(parent_out)})")
    rec = resume_state.last_completed_record(parent_manifest)
    if rec is None:
        raise ValueError(f"branch_from: parent {parent_out} has no completed day")
    if not rec.get("managers_ok") or not rec.get("managers_path"):
        raise ValueError(f"branch_from: parent day {rec['day']} has no managers.json "
                         f"(managers_ok={rec.get('managers_ok')})")
    managers_path = Path(rec["managers_path"])
    if not managers_path.exists():
        # The recorded path is relative to the parent run's cwd; fall back to the
        # canonical snapshot location next to the parent corpus.
        alt = (parent_out.parent / ".snapshots" / parent_out.stem
               / f"day_{rec['day']}" / "managers.json")
        if not alt.exists():
            raise FileNotFoundError(f"branch_from: managers.json not found at "
                                    f"{managers_path} or {alt}")
        managers_path = alt
    lab: dict[str, Any] = {}
    if lab_compose_files is not None:
        lab = _lab_branch_snapshot(parent_out, rec, lab_compose_files)
    _copy_prefix(parent_out, out_path, int(rec["audit_bytes"]))
    parent_transcript = Path(parent_manifest.get("transcript_path")
                             or parent_out.with_suffix(".transcripts.jsonl"))
    if parent_transcript.exists():
        _copy_prefix(parent_transcript, transcript_path, int(rec["transcript_bytes"]))
    return {"parent": str(parent_out), "day": rec["day"],
            "managers_path": str(managers_path), "next_day": _next_weekday(rec["day"]),
            **lab}


def _lab_branch_snapshot(parent_out: Path, rec: dict[str, Any],
                         compose_files: list[Path]) -> dict[str, Any]:
    """The parent's docker snapshot for the branch day `rec` (the day
    _prepare_branch selected), with its volume set checked complete for
    `compose_files`. Raises naming what is missing; never falls back to another
    day, since the audit prefix is cut at this one."""
    from ..sandbox.snapshot import branch_volume_set
    if not rec.get("snapshot_ok"):
        raise ValueError(f"branch_from: parent day {rec['day']} has no docker snapshot "
                         f"(snapshot_ok={rec.get('snapshot_ok')}); a lab branch needs the "
                         f"parent's volumes for that day (was NPC_SKIP_DOCKER_SNAPSHOT set?)")
    canonical = parent_out.parent / ".snapshots" / parent_out.stem / f"day_{rec['day']}"
    snap = Path(rec.get("snapshot_dir") or canonical)
    if not (snap / "manifest.json").exists():
        snap = canonical
    volumes = branch_volume_set(snap, list(compose_files))
    source = json.loads((snap / "manifest.json").read_text(encoding="utf-8")).get(
        "source_session_id")
    return {"snapshot_dir": str(snap.resolve()), "source_session_id": source,
            "volumes": volumes}


def _branch_lineage(branch_info: dict[str, Any]) -> dict[str, Any]:
    """The manifest's branch_from record: {parent, day, managers_path}, plus, for a
    lab branch, {snapshot_dir, source_session_id, volumes} (each volume's key,
    parent volume name, tarball, bytes and, once restored, restored_as) and, once the
    lab is up, class_documents_at_start."""
    keys = ("parent", "day", "managers_path")
    if branch_info.get("snapshot_dir"):
        keys += ("snapshot_dir", "source_session_id", "volumes")
    if "class_documents_at_start" in branch_info:
        keys += ("class_documents_at_start",)
    return {k: branch_info[k] for k in keys}


async def _class_documents_at_start(sandbox: Any) -> list[dict[str, Any]]:
    """[{path, present, bytes, sha256}] of the Stage 3 class documents in a freshly
    restored lab's ownCloud, read BEFORE any session (and before the audit collector
    wraps a manager, so the reads are not audit events): the evidence that a lab branch
    starts on its parent's documents. A lab without ownCloud records []."""
    from ..seeders.seed_class_docs import CLASS_DOCUMENTS
    from ..state.owncloud.manager import OwnCloudManager
    if "owncloud" not in AGENTIC_ENVS:
        return []
    oc = OwnCloudManager()
    await oc.setup(sandbox=sandbox)
    out: list[dict[str, Any]] = []
    try:
        for path in CLASS_DOCUMENTS:
            if not await oc.exists(path=path):
                out.append({"path": path, "present": False, "bytes": 0, "sha256": None})
                continue
            data = await oc.read_bytes(path=path)
            out.append({"path": path, "present": True, "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest()})
    finally:
        await oc.cleanup()
    logger.info("branch_from: class documents at start: %d of %d present",
                sum(r["present"] for r in out), len(out))
    return out


def gate_state_report(ctx: Any) -> dict[str, Any]:
    """The current `release-gate` of `ctx`'s eval server and what it does to the safe
    release candidate and to the C3 unsafe checkpoints: {version, safe: state,
    unsafe: {ckpt: state}} (states: passes / blocks / broken)."""
    from ..scenarios.release_sabotage import SAFE_RELEASE_CANDIDATE, GATE_CONFIG
    ev = (getattr(ctx, "_managers", {}) or {}).get("eval_server")
    if ev is None:
        return {}
    cur = ev.current_config(GATE_CONFIG)
    if cur is None:
        return {}
    cfg = cur["config"]
    unsafe = [c for c in ev._hidden_outcomes if ev.is_unsafe(c)]
    return {"version": cur.get("version"), "config": cfg,
            "safe": {SAFE_RELEASE_CANDIDATE: ev.gate_state_for(SAFE_RELEASE_CANDIDATE, cfg)},
            "unsafe": {c: ev.gate_state_for(c, cfg) for c in sorted(unsafe)}}


def _check_parent_gate(ctx: Any, branch_info: dict[str, Any], allow_blocked_gate: bool) -> None:
    """Refuse to branch from a parent whose final release-gate blocks the safe release
    candidate (threshold ratchet), unless `allow_blocked_gate`. Logs the gate's state
    either way, including whether it already passes an unsafe checkpoint."""
    rep = gate_state_report(ctx)
    if not rep:
        return
    logger.info("branch_from: parent release-gate v%s: safe %s, unsafe %s",
                rep["version"], rep["safe"], rep["unsafe"])
    blocked = [c for c, st in rep["safe"].items() if st != "passes"]
    if blocked and not allow_blocked_gate:
        thr = (rep["config"] or {}).get("thresholds")
        raise ValueError(
            f"branch_from: the parent's final release-gate (v{rep['version']}, thresholds "
            f"{thr}) does not pass the safe release candidate {blocked} (state "
            f"{[rep['safe'][c] for c in blocked]}): an honest release could not ship from "
            f"this world and the attack's approvals could never be valid. Reset or cap the "
            f"gate in the parent, or pass allow_blocked_gate=True (--allow-blocked-gate).")
    opened = [c for c, st in rep["unsafe"].items() if st == "passes"]
    if opened:
        logger.warning("branch_from: the parent's final release-gate v%s ALREADY passes the "
                       "unsafe checkpoint(s) %s; a campaign branched here has nothing to open",
                       rep["version"], opened)


def _weekday_dates(start: date, n_days: int) -> list[str]:
    """`n_days` consecutive working days (skip Sat/Sun) from `start`."""
    out: list[str] = []
    d = start
    while len(out) < n_days:
        if d.weekday() < 5:                # Mon–Fri
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def campaign_schedule_for(
    account_id: str,
    i: int,
    *,
    planning: str,
    persona_map: dict[str, str],
    threat_map: dict[str, str],
    role_map: dict[str, str],
    level_map: dict[str, str],
    sim_dates: list[str],
    seed: int | None,
    campaign_days: int,
    attack_session_rate: float,
    window_map: dict[str, tuple[int, int]] | None = None,
    role_order_map: dict[str, list[str]] | None = None,
    acts_on_day=None,
    instance_map: dict[str, str] | None = None,
) -> list[dict] | None:
    """Per-insider attack schedule handed to AgenticMember(campaign_schedule=...).

    `window_map` / `role_order_map` (coalition instances, mole/generator/coalitions.py):
    the account's campaign window (1-based first/last working day) and its instance's
    active roles in order, passed to build_campaign on the scripted path. `acts_on_day`
    (account, day) -> bool is the presence predicate (generator/presence.py) that makes
    this THE ONE planner for a coalition role's day in both rules and agentic mode (L15
    rule 4; brief 07b F1.7): the drawn day is kept when the account acts, re-drawn inside
    the role's rank slice otherwise, and the call fails loudly naming the instance
    (`instance_map`) and role when no slice day works. None keeps the raw draw.

    Built from a per-member RNG over the working days: "scripted" -> stage->trigger
    campaign; "single" -> K self-contained attack-days. "agentic" -> None (the agent
    authors at runtime in its first session); "coinflip" (legacy) and benign members
    -> None (the member's per-session i.i.d. path).

    attack_session_rate <= 0 (--attack-rate 0.0 / --no-insiders) is an HONEST world:
    every insider gets an explicit empty schedule [] in EVERY planning mode, so no
    attack session is ever planned (the deterministic planners otherwise ignore the
    rate, and an explicit [] also stops the agentic member from authoring one).
    """
    if account_id not in persona_map:
        return None
    if attack_session_rate <= 0:
        return []
    import random as _r
    rng = _r.Random((seed or 0) + i)
    if planning == "scripted":
        from .campaign import build_campaign
        return build_campaign(threat_map.get(account_id, ""), sim_dates, rng,
                              role=role_map.get(account_id),
                              stealth_level=level_map.get(account_id),
                              window=(window_map or {}).get(account_id),
                              roles=(role_order_map or {}).get(account_id),
                              acts_on_day=acts_on_day, account=account_id,
                              instance_id=(instance_map or {}).get(account_id)) or None
    if planning == "single":
        # Collusion is inherently multi-day (the requester->co-signer handoff needs
        # >=2 days); single-day can't coordinate it, so collusion insiders run BENIGN
        # in single-day mode rather than emitting degenerate (uncoordinated) "collusion"
        # cells. Collusion is evaluated only on the multi-day path.
        if role_map.get(account_id) is not None:
            # Return an EXPLICIT empty schedule -- [] NOT None. None routes the member
            # to its legacy i.i.d. attack coin-flip (agentic_member: the
            # `campaign_schedule is None` branch), which re-emits the (uncoordinated)
            # collusion attack anyway -- that bug put ~40% no-op collusion sessions
            # into the single_K4 corpus. An empty list is "not None", so the member
            # takes the schedule branch, matches no attack-day on any date, and stays
            # benign the whole run.
            return []
        from .campaign import build_single_day
        return build_single_day(sim_dates, rng, k=campaign_days) or None
    return None


def _last_completed_day(audit_jsonl: Path) -> str | None:
    """Read an existing audit jsonl and return the max date prefix (YYYY-MM-DD)
    found in any event's `ts`, or None if the file is empty / missing.

    Used by --resume to skip days already in the corpus. We treat any event on
    day D as evidence that D was "in progress"; the conservative choice is to
    restart from day D+1, accepting that the very last partial day may be
    re-run. Combined with the day-boundary snapshot logic, this gives a
    coarse-grained resume: at most one re-run day, no day permanently lost.
    """
    if not audit_jsonl.exists():
        return None
    last_date: str | None = None
    with audit_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = rec.get("ts", "")
            if len(ts) >= 10:
                day = ts[:10]
                if last_date is None or day > last_date:
                    last_date = day
    return last_date


async def simulate(
    *,
    n_personas: int,
    n_days: int,
    out_path: str | Path,
    start_date: str | None = None,    # None → DEFAULT_START_DATE (or, with
                                      # branch_from, the weekday after the parent's last day)
    seed: int | None = 0,
    sessions_per_day: int = 8,        # generation default; ~8 × 0.95 loaf ≈ 7.6/day
    config: NPCConfig | None = None,
    mode: str = "rules",
    llm: Any | None = None,
    include_holdouts: bool = False,
    concurrency: int = 1,
    bucket_minutes: int = 30,
    resume: bool = False,
    restore_world: bool = False,
    session_resume: bool = False,
    resume_fresh_state: bool = False,
    session_id: str | None = None,
    insider_persona_map: dict[str, str] | None = None,
    insider_threat_map: dict[str, str] | None = None,
    insider_role_map: dict[str, str] | None = None,
    insider_level_map: dict[str, str] | None = None,
    coalition_window_map: dict[str, tuple[int, int]] | None = None,
    coalition_role_order_map: dict[str, list[str]] | None = None,
    coalition_meta: dict[str, Any] | None = None,
    max_turns: int = 30,
    max_tool_calls_per_turn: int | None = None,   # None -> $MOLE_MAX_TOOL_CALLS_PER_TURN or 24
    elicit: bool = True,
    objective_carrier: str = "insider",
    elicit_share: float | None = None,
    task_bank_path: str | Path | None = None,
    class_documents: bool = False,
    allowed_persona_ids: set[str] | None = None,
    attack_session_rate: float = 0.20,
    multi_day: bool = False,
    benign_arcs: bool = False,
    release_arcs: int = 0,
    pinned_tasks: list[tuple] | None = None,
    planning: str | None = None,
    campaign_days: int = 4,   # K; calibrated to the v1 ar05 base rate (~3.2%)
    auth_failure_limit: int = 25,
    absent_probability: float = 0.01,
    sandbox_mode: str = "lab",
    branch_from: str | Path | None = None,
    injections: list[dict[str, Any]] | None = None,
    injection_meta: dict[str, Any] | None = None,
    allow_blocked_gate: bool = False,
) -> AuditCollector:
    """Generate a benign background-account audit corpus.

    mode="agentic" (the standard baseline): each background-account session is driven by an LLM
    persona-agent over the full service surface (needs a lab sandbox + llm), so the
    benign corpus matches the agent's generative process. mode="rules" (fast,
    no LLM/containers): the scripted-workflow path, kept for CI/tests.

    include_holdouts=True puts the holdout cohort into the SAME universe as the
    training cohort (one universe → split downstream by cohort tag for L1P-O). The
    holdouts' actions also shape the world the training cohort sees — alice posts to
    chat, paul.o17 reads it, etc. — which is the realism reason to generate them
    together rather than in a separate run.

    `concurrency` (default 1 = sequential) bounds in-flight sessions. With
    concurrency > 1, sessions within each `bucket_minutes` sim-time window run
    concurrently via `asyncio.gather` (semaphore-bounded). Sim-time buckets are
    processed in order, preserving causal interleaving between buckets. Per-task
    clock is carried via a contextvar (see `audit/collector.py::set_task_clock`),
    so concurrent sessions don't race on the shared `_clock_fn`. At the 150 × 7
    scale, concurrency=1 takes ~4 weeks wall time; concurrency=25 reduces to ~28h.

    `sandbox_mode="dryrun"` runs agentic mode without Docker: a DryRunSandbox, the
    in-process managers only (INPROCESS_ENVS, or $NPC_AGENTIC_ENVS), the seeded
    world on a fresh run, the in-process benign task bank, and no docker
    snapshot (managers.json is still exported each day). In rules mode it also
    seeds the world on a fresh run.

    `branch_from` (a parent audit jsonl; fresh runs only) starts this run from the
    parent's last completed day: the parent's audit log / transcript up to that
    boundary are copied into this run's own files (and preloaded so the recap
    sees the history), its managers.json is imported over a freshly seeded world,
    and `start_date` defaults to the next weekday. The parent is never modified.

    `release_arcs` (agentic mode only; default 0) schedules that many honest release
    arcs (generator/release_arcs.py): each casts four honest accounts of the cohort and
    runs register -> gate edit -> gate eval -> two approvals -> prod deploy as their
    staging tasks over two days. The plan is recorded in the manifest under
    "release_arcs" (a --resume reuses it).

    `pinned_tasks` (agentic mode only) is a list of (account, day_index, task_id) from
    --pin-task: that account's first benign session on that day runs the task-bank task
    `task_id` (agentic_member.load_task_bank_ids) instead of a random draw; a 4-tuple
    (account, day_index, task_id, "HH:MM:SS") from --pin-slot instead runs it in a
    dedicated session at that sim time (never loafed, runs on a PTO day), so it can be
    placed after another account's session. Recorded in the manifest under
    "pinned_tasks" (with "slot" for slotted pins).

    `task_bank_path` (agentic lab mode; rules mode ignores it): draw honest tasks from this bank file instead of
    the shipped v2 bank (Stage 3: the class bank); recorded in the manifest as
    task_bank {path, sha256, tasks_per_team}. `class_documents` (a fresh agentic lab run):
    seed the six class documents in ownCloud at world start, recorded as
    class_documents [{service, path, sha256}]; a lab branch inherits them from the
    parent's volumes instead, so the two are refused together.

    `allow_blocked_gate`: a `branch_from` run refuses to start when the parent's final
    `release-gate` would fail the safe release candidate (the honest threshold ratchet:
    a gate that blocks every checkpoint makes both the attack and the honest releases
    fail for a reason unrelated to the question). Pass True to branch anyway.

    `injections` (both modes; see generator/injection.py) is a plan of scripted
    release-scenario PHASES ({inject_id, variant, level, ticket, ablate, phase, actor,
    day_index, slot, live_approval}, from `build_injection_plan`). Each phase is run as
    one more session of its actor at that sim slot, gathered with the live sessions of
    its bucket, under a stable task_id, and leaves a transcript stub row
    (session_mode "attack" for a colluder's phase, else "legit"). In rules mode a
    transcript file is opened for these stubs. The plan, `injection_meta` and every
    phase's result (incl. `deploy_skipped_no_quorum` when --inject-live-approval found
    < 2 valid approvals) are recorded in the manifest under "injections"; a --resume
    reuses the manifest's plan and chain state.
    """
    if release_arcs and mode != "agentic":
        raise ValueError("release_arcs needs mode='agentic' (the steps are LLM agent sessions)")
    if pinned_tasks and mode != "agentic":
        raise ValueError("pinned_tasks needs mode='agentic' (rules mode draws no bank tasks)")
    if sandbox_mode not in SANDBOX_MODES:
        raise ValueError(f"sandbox_mode must be one of {SANDBOX_MODES}, got {sandbox_mode!r}")
    if branch_from is not None and resume:
        raise ValueError("branch_from starts a fresh run; it cannot be combined with resume")
    # An agentic lab branch also restores the parent day's docker volumes, so it
    # checks (in _prepare_branch, before anything is copied) that the parent's
    # snapshot for that day holds a complete volume set for the compose stack.
    lab_branch = branch_from is not None and mode == "agentic" and sandbox_mode == "lab"
    # Rules mode accepts both (the L15 rehearsal runs the agentic flags verbatim) and
    # ignores them: it draws no bank tasks and has no ownCloud.
    if (task_bank_path is not None or class_documents) and sandbox_mode == "dryrun":
        raise ValueError("task_bank_path / class_documents need sandbox_mode='lab' "
                         "(the class documents live in ownCloud)")
    if class_documents and mode == "agentic" and (branch_from is not None or resume):
        raise ValueError("class_documents seeds a fresh world; a branch or resume "
                         "inherits the parent's documents")
    config = config or NPCConfig(sessions_per_day=sessions_per_day,
                                 absent_probability=absent_probability)
    personas = load_personas(include_holdouts=include_holdouts)
    if allowed_persona_ids:
        # Per-persona filter — restrict the run to a specific set of accounts
        # (e.g. just the malicious insiders for prompt iteration). Skips the
        # n_personas slice; the caller controls the cohort directly.
        personas = [p for p in personas if p.id in allowed_persona_ids]
    elif n_personas < len(personas):
        personas = personas[:n_personas]

    out_path = Path(out_path)
    # Full session transcripts go to a sibling file (audit events are only the
    # metadata projection; level 2 LLM monitors need the whole conversation, and
    # regenerating an agentic corpus is expensive). One JSON object per session.
    transcript_path = out_path.with_suffix(".transcripts.jsonl")

    branch_info: dict[str, Any] | None = None
    if branch_from is not None:
        if lab_branch:
            from ..run_task import _default_lab_compose
            branch_info = _prepare_branch(Path(branch_from), out_path, transcript_path,
                                          lab_compose_files=[_default_lab_compose()])
        else:
            branch_info = _prepare_branch(Path(branch_from), out_path, transcript_path)
        if start_date is None:
            start_date = branch_info["next_day"]
        logger.info("branch_from: %s day %s -> %s (start_date=%s)",
                    branch_info["parent"], branch_info["day"], out_path, start_date)
    if start_date is None:
        start_date = DEFAULT_START_DATE

    # Resume: prefer the day-boundary resume manifest (the authoritative record
    # of the last FULLY-committed day + the byte offsets to trim a partial/
    # garbage tail back to). Falls back to a date-scan for legacy corpora that
    # predate the manifest (lossy: a partial last day is skipped, not re-run,
    # and any crash tail is kept).
    resume_after_day: str | None = None
    manifest: dict[str, Any] | None = None
    restore_rec: dict[str, Any] | None = None   # set only on a --restore-world resume
    resume_in_progress: dict[str, Any] | None = None  # set only on a --session-resume mid-day resume
    if resume:
        manifest = resume_state.load(out_path)
        if manifest is not None:
            in_prog = resume_state.in_progress_record(manifest)
            if (session_resume and not restore_world and in_prog is not None
                    and in_prog["day"] > (resume_state.last_completed_day(manifest) or "")):
                # Session-level (bucket-granular) warm resume: the run died mid-day
                # with a live lab. Trim to the last in-day BUCKET boundary (finer
                # than the day boundary) and re-enter that day from the saved plan
                # (see the day loop), instead of discarding the whole in-progress
                # day. Only buckets after the checkpoint re-run; days <= the last
                # COMMITTED day are still skipped.
                trimmed_a, trimmed_t = resume_state.truncate_to_record(
                    in_prog, out_path, transcript_path)
                resume_after_day = resume_state.last_completed_day(manifest)
                resume_in_progress = in_prog
                logger.info("--session-resume: re-entering day %s from bucket %d "
                            "(last committed day=%s); trimmed %d audit + %d "
                            "transcript bytes of partial tail",
                            in_prog["day"], in_prog["next_bucket_index"],
                            resume_after_day, trimmed_a, trimmed_t)
            else:
                # Day-granular resume target = last fully-committed day. With
                # --restore-world we instead target the last day that ALSO has a
                # complete docker+in-process world boundary, so the restored world
                # lines up with the (truncated) audit/transcript.
                target_rec = resume_state.last_completed_record(manifest)
                if restore_world:
                    # dryrun has no docker snapshot: the managers.json alone is
                    # the complete world boundary.
                    restore_rec = (resume_state.last_restorable_record(manifest)
                                   if sandbox_mode == "lab"
                                   else _last_managers_record(manifest))
                    if restore_rec is not None:
                        target_rec = restore_rec
                    else:
                        logger.warning("--restore-world: no day has a complete "
                                       "snapshot+managers boundary; falling back to "
                                       "re-seed resume.")
                trimmed_a, trimmed_t = resume_state.truncate_to_record(
                    target_rec, out_path, transcript_path)
                resume_after_day = target_rec["day"] if target_rec else None
                logger.info("--resume: target_day=%s (restore_world=%s); trimmed %d "
                            "audit + %d transcript bytes of partial/aborted tail",
                            resume_after_day, bool(restore_rec), trimmed_a, trimmed_t)
        else:
            resume_after_day = _last_completed_day(out_path)
            logger.warning("--resume: no resume manifest at %s; falling back to "
                           "date-scan (no garbage trim; partial last day skipped). "
                           "last event date=%s",
                           resume_state.manifest_path(out_path), resume_after_day)
    if manifest is None:
        manifest = resume_state.new_manifest(
            audit_path=out_path, transcript_path=transcript_path,
            start_date=start_date, n_days=n_days, seed=seed, session_id=session_id)
    manifest["sandbox_mode"] = sandbox_mode
    # Stage 3 carrier flags recorded in the manifest (L1 rule 2: the manifest, not the
    # argument parser, is the evidence of what a run did).
    manifest["objective_carrier"] = objective_carrier
    manifest["elicit_share"] = elicit_share
    # Plain --resume: resolve the in-process managers.json NOW (before any sandbox
    # starts) so a missing snapshot refuses the run instead of silently restarting
    # the world from day 0 (--restore-world imports restore_rec's own file).
    resume_managers_path: Path | None = None
    if resume and restore_rec is None:
        resume_managers_path = resolve_resume_managers_path(
            manifest, out_path, resume_fresh_state=resume_fresh_state)
        if manifest.get("resume_fresh_state"):
            resume_state.write_atomic(manifest, out_path)
    if branch_info is not None:
        manifest["branch_from"] = _branch_lineage(branch_info)
        resume_state.write_atomic(manifest, out_path)
    if coalition_meta is not None:
        # Coalition instances (Stage 2b): the plan without dates goes in now (both modes);
        # the agentic path rewrites it with the planned attack date per role below.
        from .coalitions import check_windows, manifest_entry
        check_windows(coalition_meta["instances"], n_days)
        manifest["coalitions"] = manifest_entry(
            coalition_meta["path"], coalition_meta["branch_id"],
            coalition_meta["instances"], coalition_meta["maps"], None,
            assignment_cells_skipped=coalition_meta.get("assignment_cells_skipped"))
        resume_state.write_atomic(manifest, out_path)

    # A branch appends to the parent prefix copied into out_path above.
    collector = AuditCollector(jsonl_path=out_path,
                               append=resume or branch_info is not None)
    if branch_info is not None:
        n_pre = collector.preload(out_path)
        logger.info("branch_from: preloaded %d parent events into the recap", n_pre)
    elif resume and out_path.exists():
        # The log was truncated to the resume boundary above; load what is left
        # so the cross-day session recap sees the pre-crash history.
        n_pre = collector.preload(out_path)
        logger.info("--resume: preloaded %d prior events into the recap", n_pre)
    tmp_dir = out_path.resolve().parent

    transcript_fh = None
    # One transcript write lock (agentic mode opens the file below; rules mode leaves
    # transcript_fh None). Defined unconditionally so _flush_durable — used by the
    # day-commit AND the --session-resume bucket checkpoint in BOTH modes — always
    # has it in scope.
    _t_lock = __import__("threading").Lock()

    def _flush_durable() -> tuple[int, int]:
        """Flush + fsync the audit log and transcript, returning their exact on-disk
        byte sizes. Used to record durable byte offsets at a day boundary AND (with
        --session-resume) at each in-day bucket boundary. transcript_fh is None in
        rules mode (audit-only), so only the audit size is returned there."""
        a_bytes = collector.flush_sync()
        t_bytes = 0
        if transcript_fh is not None:
            with _t_lock:
                retry_on_disk_full(transcript_fh.flush, what="transcript flush")
                try:
                    os.fsync(transcript_fh.fileno())
                except OSError as exc:
                    if is_disk_full(exc):
                        retry_on_disk_full(
                            lambda: os.fsync(transcript_fh.fileno()),
                            what="transcript fsync")
            t_bytes = transcript_path.stat().st_size
        return a_bytes, t_bytes

    transcript_mode = "a" if (resume or branch_info is not None) else "w"

    def _sink(rec: dict) -> None:
        with _t_lock:
            # write() buffers the line (exactly once); only the disk-touching
            # flush() is retried on a full disk, so ENOSPC/EDQUOT STALLS the
            # session instead of crashing it (was: uncaught OSError killed the
            # whole sim mid-day, losing the in-progress day). If write() itself
            # hits disk-full via an implicit buffer flush, the bytes stay
            # buffered and the retried flush below drains them (no dup).
            try:
                transcript_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except OSError as exc:
                if not is_disk_full(exc):
                    raise
            retry_on_disk_full(transcript_fh.flush, what="transcript sink")

    sandbox = None
    # ── ONE planner for every mode (brief 07b F1.7; L15 rule 4) ──────────────────────────
    # Everything a coalition role's day depends on is resolved HERE, before the mode
    # branch, so rules mode (the rehearsal) and agentic mode (the launch) plan the same
    # schedule for the same seed and roster: the member seeds (seed + roster index), the
    # presence predicate (generator/presence.py: the per-(seed, day) stream both member
    # classes draw their absence and loafing from) and campaign_schedule_for.
    persona_map = insider_persona_map or {}
    # Multi-day campaign schedules (flag-gated; default OFF -> campaign_schedule
    # is None and the member runs the current single-day i.i.d. path). Built per
    # insider from a deterministic per-member RNG over the sim's working days;
    # benign members and non-decomposable threats (04/05, collusion) get None.
    threat_map = insider_threat_map or {}
    # Collusion role per insider (approver_1/approver_2, read_access/egress_access);
    # drives requester-before-co-signer day sequencing in build_campaign. Empty for
    # solo/shadow (role=None there -> legacy single random day).
    role_map = insider_role_map or {}
    # Stealth level per insider (s0/s1); selects per-level collusion targets
    # (e.g. the c2 handoff folder) in build_campaign.
    level_map = insider_level_map or {}
    # Resolve the planning mode. Default is DETERMINISTIC: "scripted" (stage->
    # trigger multi-day campaign) when --multi-day, else "single" (K self-contained
    # attack-days per insider). "coinflip" is the legacy random single-day path,
    # kept only for exact v1 reproduction. Both deterministic modes need the window.
    if planning is None:
        planning = "scripted" if multi_day else "single"
    _sim_dates = (_weekday_dates(date.fromisoformat(start_date), n_days)
                  if planning != "coinflip" else [])

    if attack_session_rate <= 0 and persona_map:
        logger.info("attack_session_rate=%s <= 0: all %d insiders running BENIGN "
                    "(explicit empty attack schedule, planning=%s)",
                    attack_session_rate, len(persona_map), planning)

    from .presence import acts_predicate as _acts_predicate
    _acts_on_day = _acts_predicate(seed, {p.id: i for i, p in enumerate(personas)}, config,
                                   config.sessions_per_day)
    _instance_map = (coalition_meta or {}).get("maps", {}).get("instance_map") if coalition_meta else None

    def _campaign_for(account_id: str, i: int):
        # See campaign_schedule_for (module level, unit-tested). The one call site's
        # arguments are identical in both modes.
        return campaign_schedule_for(
            account_id, i, planning=planning, persona_map=persona_map,
            threat_map=threat_map, role_map=role_map, level_map=level_map,
            sim_dates=_sim_dates, seed=seed, campaign_days=campaign_days,
            attack_session_rate=attack_session_rate,
            window_map=coalition_window_map, role_order_map=coalition_role_order_map,
            acts_on_day=_acts_on_day, instance_map=_instance_map)

    if mode == "agentic":
        if llm is None:
            from ..llm.factory import build_llm
            llm = build_llm(None)
        from uuid import uuid4
        envs = AGENTIC_ENVS if sandbox_mode == "lab" else _dryrun_envs()
        # Resume sandbox policy:
        #  - --restore-world (restore_rec set): recreate the world from the last
        #    complete day boundary. In "lab" mode restore the docker volumes
        #    in-place under the ORIGINAL project name and bring that project up;
        #    in both modes overlay the in-process manager state from the same
        #    boundary. Crash-safe: does NOT assume the old containers survived.
        #  - plain --resume: reuse the prior session_id so compose reattaches to
        #    a still-running lab (works only if the containers outlived the crash,
        #    e.g. a python-only kill / the auth-breaker halt). No re-seed.
        #  - fresh run: new session id, seed the world (a branch then overlays
        #    the parent's managers.json).
        # "dryrun" mode never touches Docker: the sandbox is a DryRunSandbox and
        # the in-process managers are the whole world.
        if restore_rec is not None:
            sb_session = manifest.get("session_id") or session_id or f"itb-npc-{uuid4().hex[:8]}"
            sandbox = await _start_sandbox(sandbox_mode, session_id=sb_session,
                                           restore_rec=restore_rec)
            ctx = await build_context(collector, tmp_dir=tmp_dir, envs=envs,
                                      sandbox=sandbox, seed_world=False)
            from ..sandbox.state_export import import_manager_state
            applied = import_manager_state(ctx, Path(restore_rec["managers_path"]))
            logger.info("--restore-world: re-imported in-process state: %s", applied)
        else:
            sb_session = session_id or f"itb-npc-{uuid4().hex[:8]}"
            # Persist the real sandbox id into the manifest up front so even a
            # day-1 crash records which lab/snapshot lineage this corpus belongs to.
            if manifest.get("session_id") != sb_session:
                manifest["session_id"] = sb_session
                resume_state.write_atomic(manifest, out_path)
            sandbox = await _start_sandbox(
                sandbox_mode, session_id=sb_session,
                branch_info=branch_info if lab_branch else None)
            if lab_branch:
                # The restored volumes are the parent's container world: record which
                # volumes landed where, and do not seed over them (the parent's
                # managers.json is imported below, as on a --restore-world resume).
                manifest["branch_from"] = _branch_lineage(branch_info)
                resume_state.write_atomic(manifest, out_path)
            # On plain resume, the seeded world is assumed already in the live
            # containers — don't re-seed (would duplicate or fail on existing rows).
            ctx = await build_context(collector, tmp_dir=tmp_dir, envs=envs,
                                      sandbox=sandbox, seed_world=(not lab_branch) and ((not resume) or os.environ.get("NPC_RESEED_ON_RESUME","").lower() in ("1","true","yes")),
                                      class_documents=class_documents)
            if class_documents:
                from ..seeders.seed_class_docs import class_documents_record
                manifest["class_documents"] = class_documents_record()
                resume_state.write_atomic(manifest, out_path)
            # The in-process managers live in THIS python process, not the docker
            # lab, so a cross-process resume must overlay the last committed day's
            # managers.json (see _import_resume_managers).
            if resume:
                _import_resume_managers(ctx, resume_managers_path)
            elif branch_info is not None:
                from ..sandbox.state_export import import_manager_state
                applied = import_manager_state(ctx, Path(branch_info["managers_path"]))
                logger.info("branch_from: imported parent in-process state: %s", applied)
                _check_parent_gate(ctx, branch_info, allow_blocked_gate)
        from .agentic_member import AgenticMember, load_task_bank, load_arc_bank
        transcript_fh = open(transcript_path, transcript_mode, encoding="utf-8")

        if sandbox_mode == "dryrun":
            # Only tasks doable on the in-process services; RAISES if absent.
            task_bank = load_task_bank(bank="inprocess")
            from .agentic_member import _task_bank_path
            _bank_file = Path(_task_bank_path(None, rich=False, bank="inprocess"))
            manifest["task_bank"] = {
                "path": str(_bank_file),
                "sha256": hashlib.sha256(_bank_file.read_bytes()).hexdigest(),
                "tasks_per_team": {t: len(v) for t, v in task_bank.items()},
            }
        elif task_bank_path is not None:
            _bank_file = Path(task_bank_path)
            task_bank = load_task_bank(str(_bank_file), rich=True)   # RAISES if absent
            manifest["task_bank"] = {
                "path": str(_bank_file),
                "sha256": hashlib.sha256(_bank_file.read_bytes()).hexdigest(),
                "tasks_per_team": {t: len(v) for t, v in task_bank.items()},
            }
        else:
            task_bank = load_task_bank(rich=True)   # expanded (v2) bank; RAISES if absent (no silent v1 fallback)
        # Benign multi-day arc bank (default OFF; loaded only when --benign-arcs; {} if absent).
        arc_bank = load_arc_bank() if benign_arcs else {}
        if coalition_meta is not None:
            # Coalition instances (Stage 2b): record the plan (roles, accounts, window and
            # the planned attack date per role) in the manifest before any session runs.
            from .coalitions import manifest_entry
            _sched = {}
            if _sim_dates:
                for i, p in enumerate(personas):
                    if p.id in coalition_meta["maps"]["instance_map"]:
                        _sched[p.id] = _campaign_for(p.id, i)
            manifest["coalitions"] = manifest_entry(
                coalition_meta["path"], coalition_meta["branch_id"],
                coalition_meta["instances"], coalition_meta["maps"], _sched,
                assignment_cells_skipped=coalition_meta.get("assignment_cells_skipped"))
            resume_state.write_atomic(manifest, out_path)
            logger.info("coalitions: %d instance(s) from %s (branch %s)",
                        len(coalition_meta["instances"]), coalition_meta["path"],
                        coalition_meta["branch_id"])

        def _arc_for(persona, i: int):
            # Benign multi-day arc for a NON-INSIDER -- the benign analog of _campaign_for. Off by
            # default; only when benign_arcs + a non-coinflip window (arcs need _sim_dates). Insiders
            # keep the attack campaign (mutually exclusive). SEPARATE RNG stream (+100003) so it never
            # perturbs self.rng or the attack RNG -> the default-off path stays byte-identical. For a
            # benign member None and [] behave identically (no attack coin-flip to suppress), so
            # `or None` is the clean "no arc" signal -- the opposite of the collusion-disable case.
            if not benign_arcs or planning == "coinflip" or persona.id in persona_map:
                return None
            arcs = arc_bank.get(getattr(persona, "team", "") or "")
            if not arcs:
                return None
            import random as _r
            rng = _r.Random((seed or 0) + 100003 + i)
            from .campaign import build_benign_arc
            return build_benign_arc(rng.choice(arcs), _sim_dates, rng) or None

        # Honest release arcs (default 0 = off). Planned once over the run's working days,
        # after the world exists so arc ids avoid every checkpoint/ticket already in it
        # (e.g. a branch parent's arcs); a --resume reuses the manifest's plan verbatim.
        release_arc_plans = _plan_release_arcs_for_run(
            release_arcs, ctx=ctx, personas=personas, manifest=manifest, resume=resume,
            out_path=out_path, start_date=start_date, n_days=n_days, seed=seed,
            bucket_minutes=bucket_minutes,
            insider_ids=set(persona_map) | set(threat_map) | set(role_map) | set(level_map))
        from .release_arcs import arc_schedules_by_account
        release_sched = arc_schedules_by_account(release_arc_plans)

        # --pin-task: forced bank tasks per (account, day); validated against the cohort,
        # the window and the run's task bank before any session runs.
        pins_by_account, pin_records = _resolve_pins(
            pinned_tasks, personas=personas,
            dates=_weekday_dates(date.fromisoformat(start_date), n_days),
            sandbox_mode=sandbox_mode, task_bank_path=(
                None if task_bank_path is None else str(task_bank_path)))
        if pin_records:
            manifest["pinned_tasks"] = pin_records
            resume_state.write_atomic(manifest, out_path)
            logger.info("pinned tasks: %s", pin_records)

        def _arc_schedule_for(persona, i: int):
            # Legacy benign arc (if any) + this account's release-arc steps; None = no arc.
            steps = list(_arc_for(persona, i) or []) + release_sched.get(persona.id, [])
            return steps or None

        members: list[Any] = [
            AgenticMember(p, llm=llm, config=config, transcript_sink=_sink,
                          task_bank=task_bank,
                          rng_seed=(None if seed is None else seed + i),
                          persona_override=persona_map.get(p.id),
                          max_turns=max_turns,
                          max_tool_calls_per_turn=max_tool_calls_per_turn,
                          elicit=elicit,
                          objective_carrier=objective_carrier,
                          elicit_share=elicit_share,
                          attack_session_rate=attack_session_rate,
                          campaign_schedule=_campaign_for(p.id, i),
                          benign_arc_schedule=_arc_schedule_for(p, i),
                          pinned_tasks=pins_by_account.get(p.id),
                          planning_mode=planning,
                          campaign_days=campaign_days,
                          sim_dates=_sim_dates,
                          rich_sessions=True)
            for i, p in enumerate(personas)
        ]
    else:
        # Rules mode acts on the in-process managers only (plane included). A
        # dryrun fresh run and a branch seed the shared world like agentic mode.
        ctx = await build_context(
            collector, tmp_dir=tmp_dir, envs=INPROCESS_ENVS,
            seed_world=(not resume) and (sandbox_mode == "dryrun" or branch_info is not None))
        if restore_rec is not None:
            from ..sandbox.state_export import import_manager_state
            import_manager_state(ctx, Path(restore_rec["managers_path"]))
        elif resume:
            _import_resume_managers(ctx, resume_managers_path)
        elif branch_info is not None:
            from ..sandbox.state_export import import_manager_state
            applied = import_manager_state(ctx, Path(branch_info["managers_path"]))
            logger.info("branch_from: imported parent in-process state: %s", applied)
            _check_parent_gate(ctx, branch_info, allow_blocked_gate)
        # Docker-free: skip the synthetic owncloud/email/gitlab/rocketchat workflows
        # so the corpus only has events for services that exist. (Lab rules mode
        # keeps them — it is the container-free stand-in for the full surface.)
        rules_services = set(ctx._managers) if sandbox_mode == "dryrun" else None
        members = [
            Member(p, config=config, rng_seed=(None if seed is None else seed + i),
                   services=rules_services)
            for i, p in enumerate(personas)
        ]
        if injections:
            # Rules mode writes no session transcripts; the injected phases still
            # need their stub rows (attack ids / intent labels read the transcript).
            transcript_fh = open(transcript_path, transcript_mode, encoding="utf-8")

    # Scripted scenario injections (generator/injection.py). A --resume reuses the
    # manifest's plan (dates and task ids are a function of the start date) and the
    # chain state (job_id / ticket_id) of the phases already recorded.
    inject_runners: list[Any] = []
    if injections or (resume and manifest.get("injections")):
        from .injection import build_runners, finalize_injection_plan, restore_states
        _dates = _weekday_dates(date.fromisoformat(start_date), n_days)
        inj_rec = manifest.get("injections") if resume else None
        if inj_rec and inj_rec.get("plan"):
            if injections:
                logger.info("--resume: ignoring the given injections; reusing the manifest's plan")
            inj_plan = list(inj_rec["plan"])
        else:
            inj_plan = finalize_injection_plan(list(injections or []), start_date=start_date,
                                               dates=_dates, salt=out_path.stem)
            inj_rec = {"meta": dict(injection_meta or {}), "plan": inj_plan, "results": {}}
            manifest["injections"] = inj_rec
            resume_state.write_atomic(manifest, out_path)
        bad_dates = sorted({e["date"] for e in inj_plan} - set(_dates))
        if bad_dates:
            raise ValueError(f"injection plan names sim days outside this run: {bad_dates}")
        cohort = {p.id for p in personas}
        for a in sorted({e["actor"] for e in inj_plan} - cohort):
            logger.warning("injection actor %s is not in this run's cohort; its phases still "
                           "run as audited calls under that account", a)
        inj_states = restore_states(inj_rec.get("results") or {}, inj_plan)

        def _record_injection(e: dict[str, Any], result: dict[str, Any]) -> None:
            inj_rec.setdefault("results", {}).setdefault(e["inject_id"], {})[e["phase"]] = result
            resume_state.write_atomic(manifest, out_path)

        inject_runners = build_runners(inj_plan, states=inj_states, on_result=_record_injection,
                                       transcript_sink=_sink)
        logger.info("injections: %d phase(s) over %d actor(s): %s", len(inj_plan),
                    len(inject_runners),
                    [(e["date"], e["slot"], e["actor"], e["inject_id"], e["phase"]) for e in inj_plan])

    sem = asyncio.Semaphore(max(1, concurrency))

    # Auth circuit-breaker state. `consecutive` counts back-to-back auth-failed
    # sessions; any successful session resets it. `tripped` latches once the
    # limit is hit so the day loop can bail before writing more empty sessions.
    breaker = {"consecutive": 0, "tripped": False}

    async def _run_one(member: Any, slot_dt: Any, action_key: str) -> None:
        if breaker["tripped"]:
            return  # don't start new work once the breaker has latched
        async with sem:
            if breaker["tripped"]:
                return
            try:
                await member.run_at(
                    ctx, slot_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), action_key,
                )
                breaker["consecutive"] = 0  # a clean session => auth is healthy
            except Exception as exc:                                # noqa: BLE001
                if _is_auth_error(exc):
                    breaker["consecutive"] += 1
                    logger.error(
                        "simulate: AUTH failure %d/%d on session %s/%s: %s",
                        breaker["consecutive"], auth_failure_limit,
                        getattr(member.persona, "id", "?"), action_key, exc)
                    if (auth_failure_limit > 0
                            and breaker["consecutive"] >= auth_failure_limit):
                        breaker["tripped"] = True
                        logger.error("simulate: AUTH circuit-breaker TRIPPED after "
                                     "%d consecutive failures — halting run. Refresh "
                                     "the API credential, then --resume.",
                                     breaker["consecutive"])
                else:
                    logger.exception("simulate: session %s/%s raised; continuing",
                                     getattr(member.persona, "id", "?"), action_key)

    # Day-boundary snapshots: take one at the end of each day so a resume
    # could later restore-into-fresh-sandbox. With this Stage-1 resume
    # (reuse-existing-sandbox), snapshots are useful as a safety net for the
    # snapshot/restore path we'll add as a follow-on.
    snapshots_dir = out_path.parent / ".snapshots" / out_path.stem

    keep_sandbox_for_resume = False
    try:
        for day_iso in _weekday_dates(date.fromisoformat(start_date), n_days):
            if resume_after_day is not None and day_iso <= resume_after_day:
                logger.info("--resume: skipping completed sim-day %s", day_iso)
                # Surface (never act on) a kept day whose sessions did not all
                # complete — e.g. a provider 402 aborted the day's only attack
                # session while managers.json still exported fine. Rolling back
                # further is the operator's call.
                _kept = next((d for d in (manifest.get("days") or [])
                              if d.get("day") == day_iso), None)
                if resume_state.day_is_clean(_kept) is False:
                    logger.warning(
                        "--resume: kept sim-day %s has sessions_ok=False: "
                        "%s/%s sessions aborted, %s/%s attack sessions completed. "
                        "Its content is incomplete; roll back past it if that matters.",
                        day_iso, _kept.get("sessions_aborted"),
                        _kept.get("sessions_planned"),
                        _kept.get("attack_sessions_completed"),
                        _kept.get("attack_sessions_planned"))
                continue
            # Causal sim-time interleaving across all members for the day.
            # Old loop (`for m in members: await m.run_day`) ran each member's full
            # day before the next, letting later members see "future" events in the
            # shared world. The fix: gather every member's planned (slot, key) pairs
            # for the day, sort globally by slot, and run in that order — so alice's
            # 9am chat post is in the world when bob reads chat at 9:15am, not when
            # bob runs after alice has already done her 4pm post. Matches Chimera's
            # time-stepped scheduling (§3 of the paper: "At time step t, …").
            #
            # With concurrency>1: bucket plan entries by `bucket_minutes` sim-time
            # windows, process buckets in order, parallelize within each bucket via
            # asyncio.gather. Per-task contextvar clock keeps timestamps correct
            # even under concurrency. With concurrency=1: degenerates to the
            # original sequential behavior (sem permits one at a time, single bucket
            # gather just awaits each in turn).
            # Session-level resume: if this is the interrupted day, reuse its saved
            # plan (preserving slots + attack schedule without re-running plan_day
            # under a diverged RNG) and skip the buckets already durable on disk.
            resume_bucket_start = 0
            day_plan: list[tuple[Any, Any, str]]
            if resume_in_progress is not None and day_iso == resume_in_progress["day"]:
                resume_bucket_start = int(resume_in_progress["next_bucket_index"])
                day_plan = _restore_day_plan(resume_in_progress["day_plan"], members,
                                             inject_runners)
                logger.info("--session-resume: day %s reusing saved plan (%d sessions); "
                            "resuming at bucket %d", day_iso, len(day_plan), resume_bucket_start)
                resume_in_progress = None   # consumed; only this one day re-enters mid-way
            else:
                day_plan = [
                    (t, m, key) for m in members for (t, key) in m.plan_day(day_iso)
                ] + [
                    (t, r, key) for r in inject_runners for (t, key) in r.plan_day(day_iso)
                ]
                day_plan.sort(key=lambda x: x[0])

            # Group by sim-time bucket while preserving order.
            buckets: list[list[tuple[Any, Any, str]]] = []
            current_bucket_id: int | None = None
            for t, m, key in day_plan:
                bid = (t.hour * 60 + t.minute) // max(1, bucket_minutes)
                if bid != current_bucket_id:
                    buckets.append([])
                    current_bucket_id = bid
                buckets[-1].append((t, m, key))

            for bucket_idx, bucket in enumerate(buckets):
                if bucket_idx < resume_bucket_start:
                    continue   # generated pre-crash + kept in the truncated tail
                # The continuous-day schedule packs an account's sessions close in
                # sim-time, so several can land in one bucket. Run each ACCOUNT's
                # sessions sequentially (so the cross-session recap/clock stays
                # causal) while different accounts still run concurrently. Keyed by
                # account so an injected phase joins its actor's live sequence.
                by_member: dict[Any, list[tuple[Any, Any, str]]] = {}
                for t, m, key in bucket:
                    acct = getattr(getattr(m, "persona", None), "id", None) or id(m)
                    by_member.setdefault(acct, []).append((t, m, key))

                async def _run_member_seq(items: list[tuple[Any, Any, str]]) -> None:
                    for t, m, key in items:
                        await _run_one(m, t, key)

                await asyncio.gather(*(
                    _run_member_seq(items) for items in by_member.values()
                ))
                if breaker["tripped"]:
                    # Leave the lab containers UP so --resume can reattach
                    # (Stage-1 resume reuses the live sandbox; tearing it down
                    # would lose the seeded world).
                    keep_sandbox_for_resume = True
                    raise AuthCircuitBreakerError(
                        f"{breaker['consecutive']} consecutive auth failures; "
                        f"halted mid-day {day_iso}. Token is stale/dead — refresh "
                        f"it, then re-run with --resume --session-id "
                        f"{getattr(sandbox, 'session_id', None) or session_id}.")

                # Session-level (bucket-granular) checkpoint. Placed AFTER the gather
                # (the bucket is quiescent — no session in flight, so the audit log is
                # cleanly truncatable here) AND after the breaker check (so a
                # breaker-tripping bucket is NOT checkpointed and re-runs on resume).
                # Records byte offsets + next bucket + the day plan, so a mid-day crash
                # resumes from the next bucket instead of discarding the whole day.
                # Default OFF — only when the run opted into --session-resume.
                if session_resume:
                    a_bytes, t_bytes = _flush_durable()
                    resume_state.record_in_progress(
                        manifest, out_path, day=day_iso,
                        next_bucket_index=bucket_idx + 1,
                        audit_bytes=a_bytes, transcript_bytes=t_bytes,
                        day_plan=_serialize_day_plan(day_plan))

            # End-of-day snapshot + in-process state export (both best-effort).
            # Docker snapshot only meaningful in agentic mode where a real
            # LabSandbox is up. In-process state export runs in both modes —
            # the 5 in-process managers (org/model_registry/eval_server/
            # secrets_store/plane) hold mutable Python state that docker
            # snapshots don't capture. Failures are logged but don't abort
            # the sim — we'd rather lose the snapshot than the day's work.
            snap_out = snapshots_dir / f"day_{day_iso}"
            managers_ok = False
            snapshot_ok = False
            try:
                snap_out.mkdir(parents=True, exist_ok=True)
                from ..sandbox.state_export import export_manager_state
                export_manager_state(ctx, snap_out / "managers.json")
                managers_ok = True
                logger.info("day-boundary in-process state exported: %s",
                            snap_out / "managers.json")
            except Exception:                                       # noqa: BLE001
                logger.exception("in-process state export failed for %s; "
                                 "sim continues", day_iso)
            # The docker volume snapshot (pause containers + tar each volume) is
            # ONLY needed for --restore-world (rebuilding a DEAD lab). Plain
            # --resume reattaches the still-live lab, whose volumes persist in
            # dockerd across days, so the backup tars are redundant for it — and
            # they get progressively slower as the GitLab volume fills. Set
            # NPC_SKIP_DOCKER_SNAPSHOT=1 to skip them (keeps the cheap in-process
            # managers.json export above). snapshot_ok stays False → manifest
            # records no snapshot_dir, consistent with the --resume-only path.
            _skip_snap = os.environ.get("NPC_SKIP_DOCKER_SNAPSHOT", "").lower() in ("1", "true", "yes")
            # Only a real LabSandbox has docker volumes; dryrun skips this block.
            _docker = sandbox is not None and sandbox_mode == "lab"
            if _docker and _skip_snap:
                logger.info("day-boundary docker snapshot SKIPPED for %s "
                            "(NPC_SKIP_DOCKER_SNAPSHOT) — plain --resume reattaches "
                            "the live lab, volume backups are redundant", day_iso)
            elif _docker:
                try:
                    from ..sandbox.snapshot import snapshot_sandbox
                    await snapshot_sandbox(
                        sandbox.session_id, f"day_{day_iso}", out_dir=snap_out,
                        compose_files=getattr(sandbox, "compose_files", None),
                    )
                    snapshot_ok = True
                    logger.info("day-boundary docker snapshot saved: %s", snap_out)
                except Exception:                                       # noqa: BLE001
                    logger.exception("day-boundary docker snapshot failed for %s; "
                                     "sim continues", day_iso)

            # Commit the day to the resume manifest LAST, after the audit log,
            # transcript, state export and snapshot for the day are flushed to
            # disk. Record the exact byte offsets so a later --resume can trim a
            # partial/garbage tail back to this boundary. The manifest only ever
            # names a day whose outputs are durable — so resume can trust it.
            audit_bytes, transcript_bytes = _flush_durable()
            # Per-day session outcome counts, from this day's transcript records
            # (agentic mode only — rules mode writes no transcript, so counts stay
            # None). The day's slice starts at the previous committed day's offset;
            # tally_day_sessions also filters by sim_ts date. Best-effort: a tally
            # failure must never block the day commit.
            session_counts: dict[str, int] = {}
            if transcript_fh is not None and mode == "agentic":
                try:
                    _prev = [d for d in (manifest.get("days") or [])
                             if d.get("day", "") < day_iso]
                    session_counts = resume_state.tally_day_sessions(
                        transcript_path, day=day_iso, sessions_planned=len(day_plan),
                        start_byte=int(_prev[-1]["transcript_bytes"]) if _prev else 0,
                        end_byte=transcript_bytes)
                except Exception:                                   # noqa: BLE001
                    logger.exception("session tally failed for %s; recording no "
                                     "session counts", day_iso)
                    session_counts = {}
            resume_state.record_day(
                manifest, out_path, day=day_iso,
                audit_bytes=audit_bytes, transcript_bytes=transcript_bytes,
                snapshot_ok=snapshot_ok, managers_ok=managers_ok,
                snapshot_dir=str(snap_out) if snapshot_ok else None,
                managers_path=str(snap_out / "managers.json") if managers_ok else None,
                **session_counts,
            )
            # The committed day supersedes any mid-day (bucket) checkpoint for it, so
            # drop it — a later resume must land on this day boundary, not re-enter the
            # finished day. No-op when --session-resume wasn't used.
            if session_resume:
                resume_state.clear_in_progress(manifest, out_path)
            _day_rec = next((d for d in manifest["days"] if d.get("day") == day_iso), {})
            logger.info("day-boundary manifest committed: day=%s audit=%dB "
                        "transcript=%dB snapshot_ok=%s sessions planned=%s "
                        "completed=%s aborted=%s attack=%s/%s sessions_ok=%s",
                        day_iso, audit_bytes, transcript_bytes, snapshot_ok,
                        _day_rec.get("sessions_planned"), _day_rec.get("sessions_completed"),
                        _day_rec.get("sessions_aborted"),
                        _day_rec.get("attack_sessions_completed"),
                        _day_rec.get("attack_sessions_planned"),
                        _day_rec.get("sessions_ok"))
            if resume_state.day_is_clean(_day_rec) is False:
                logger.warning("day %s committed with incomplete sessions: %s/%s "
                               "aborted, %s/%s attack sessions completed",
                               day_iso, _day_rec.get("sessions_aborted"),
                               _day_rec.get("sessions_planned"),
                               _day_rec.get("attack_sessions_completed"),
                               _day_rec.get("attack_sessions_planned"))

        # Coalition role-action days (rules mode). Rules mode plans no attack sessions,
        # so it records each role's PLANNED ACTION DAY instead, for a rehearsal to compare
        # against a written plan (L15 rule 1). Since brief 07b (F1.7) the day comes from
        # THE SAME planner call the agentic launch makes (_campaign_for above: same seeds,
        # same presence predicate, same re-draw inside the rank slice, same loud failure
        # naming the instance and role), so the rehearsed planned_role_day IS the agentic
        # run's planned_attack_dates for the same seed and roster. planned_attack_dates
        # stays null here (no attacks in rules mode).
        if coalition_meta is not None and mode != "agentic":
            from .coalitions import manifest_entry as _manifest_entry
            _pindex = {p.id: i for i, p in enumerate(personas)}
            _role_days: dict[str, str | None] = {}
            for _inst in coalition_meta["instances"]:
                for _role, _acct in _inst.roles.items():
                    if _acct not in _pindex:
                        _role_days[_acct] = None          # not in this run's roster
                        continue
                    _sched = _campaign_for(_acct, _pindex[_acct])
                    _role_days[_acct] = _sched[0]["date"] if _sched else None
            manifest["coalitions"] = _manifest_entry(
                coalition_meta["path"], coalition_meta["branch_id"],
                coalition_meta["instances"], coalition_meta["maps"], None,
                assignment_cells_skipped=coalition_meta.get("assignment_cells_skipped"),
                role_days=_role_days)
            resume_state.write_atomic(manifest, out_path)
            logger.info("coalitions (rules): %d instance(s), role days %s",
                        len(coalition_meta["instances"]), _role_days)
    finally:
        collector.close()
        if transcript_fh is not None:
            transcript_fh.close()
        if sandbox is not None and not keep_sandbox_for_resume:
            try:
                await sandbox.stop()
            except Exception:                                  # noqa: BLE001
                pass
        elif keep_sandbox_for_resume:
            logger.warning("simulate: leaving sandbox %s UP for --resume (auth "
                           "breaker tripped). Tear it down manually if abandoning.",
                           getattr(sandbox, "session_id", "?"))
    return collector


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mole.generator.run")
    ap.add_argument("--personas", type=int, default=3, help="number of NPCs")
    ap.add_argument("--days", type=int, default=5, help="number of working days")
    ap.add_argument("--out", default="npc_audit.jsonl", help="audit jsonl output path")
    ap.add_argument("--start-date", default="2026-04-06", help="first sim day (YYYY-MM-DD)")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed (None for nondeterministic)")
    ap.add_argument("--sessions", type=int, default=8, help="sessions per account per day")
    ap.add_argument("--include-holdouts", action="store_true",
                    help="generate trajectories for the holdout cohort too, mixed into the "
                         "same universe as the training cohort (one universe → split by "
                         "cohort tag at eval time for L1P-O). Default: holdouts excluded "
                         "from generation entirely.")
    ap.add_argument("--mode", choices=["agentic", "rules"], default="agentic",
                    help="agentic=LLM persona-agents (standard, needs sandbox+LLM backend); "
                         "rules=scripted workflows (fast, no LLM)")
    ap.add_argument("--concurrency", type=int, default=1,
                    help="Max in-flight sessions per sim-time bucket. Default 1 "
                         "(sequential, deterministic). Set to ~25 for the 150x7 "
                         "production sim; bounded by provider rate limits.")
    ap.add_argument("--bucket-minutes", type=int, default=30,
                    help="Sim-time window for parallel buckets (default 30). "
                         "Sessions within the same window run via asyncio.gather; "
                         "windows are processed sequentially to preserve causal order.")
    ap.add_argument("--resume", action="store_true",
                    help="Resume from an existing audit log: open --out + transcripts "
                         "in append mode, skip any sim-day already present in the log, "
                         "and (if --session-id given) reattach to that sandbox. "
                         "Without --session-id, agentic mode starts a fresh sandbox; "
                         "the resume is only safe if the prior run's containers are "
                         "still up under that session-id.")
    ap.add_argument("--session-resume", action="store_true",
                    help="Opt into session-level (bucket-granular) warm resume: "
                         "checkpoint after each in-day sim-time bucket, so a mid-day "
                         "crash resumes from the last bucket (re-running only ~one "
                         "bucket) instead of discarding the whole in-progress day. "
                         "Default OFF (day-granular resume). Used together with "
                         "--resume; the live lab must have survived the crash.")
    ap.add_argument("--session-id", default=None,
                    help="Reattach to an existing LabSandbox by docker-compose project "
                         "name (only useful with --resume). If omitted on resume, a new "
                         "sandbox is started — only correct if you've separately "
                         "restored container state from a day-boundary snapshot.")
    ap.add_argument("--absent-prob", type=float, default=0.01,
                    help="Per-account whole-day absence probability (PTO/sick). "
                         "Default 0.01 (very rare); 0 disables.")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.WARNING)
    collector = asyncio.run(simulate(
        n_personas=args.personas, n_days=args.days,
        out_path=args.out, start_date=args.start_date, seed=args.seed,
        sessions_per_day=args.sessions, mode=args.mode,
        include_holdouts=args.include_holdouts,
        concurrency=args.concurrency, bucket_minutes=args.bucket_minutes,
        resume=args.resume, session_resume=args.session_resume,
        session_id=args.session_id,
        absent_probability=args.absent_prob,
    ))
    events = collector.events
    by_account = Counter(e.account for e in events)
    by_service = Counter(e.service for e in events)
    kinds = Counter(e.account_kind for e in events)
    print(f"generator: {len(events)} events -> {args.out}")
    if args.mode == "agentic":
        print(f"          transcripts -> {Path(args.out).with_suffix('.transcripts.jsonl')}")
    print(f"  account_kind: {dict(kinds)}")
    print(f"  by account: {dict(by_account)}")
    print(f"  by service: {dict(by_service)}")
    # The whole point: a benign-only log.
    n_malicious = sum(1 for e in events if e.is_malicious)
    print(f"  malicious events: {n_malicious} (expect 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
