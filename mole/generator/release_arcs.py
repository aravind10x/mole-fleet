"""Honest release arcs: scheduled multi-day, multi-account benign releases.

Under the random benign task draw an honest production release almost never
happens (it needs a registration, a gate eval, two approvals and a deploy, in
that order, by four different people). A release arc schedules exactly that, as
staging tasks on four honest accounts, so the corpus carries honest releases to
set against release-gate attacks. Default OFF; enabled by `--release-arcs N`
(scripts/sim_runner.py) / `simulate(release_arcs=N)`.

The steps ride the existing benign-arc path (AgenticMember.benign_arc_schedule):
each step is one schedule entry carrying a fixed sim-time `slot`, which makes the
member plan one dedicated session for it (see AgenticMember.plan_day). The slot
puts each step in its own sim-time bucket, ranked by the step's `order`, so the
steps of a day run in order across accounts (simulate runs buckets in sequence).

Pure planning lives here (no LLM, no world access): `plan_release_arcs` returns a
JSON-safe plan per arc, recorded in the run manifest under "release_arcs";
`arc_schedules_by_account` turns the plans into per-account schedule entries.
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

_BOOTSTRAP = Path(__file__).resolve().parents[2] / "bootstrap"
DEFAULT_TEMPLATE = _BOOTSTRAP / "release_arcs_v1.yaml"
DEFAULT_INSIDER_ASSIGNMENT = _BOOTSTRAP / "insider_assignment.yaml"

APPROVER_GROUP = "model-approval"
# Release owner = checkpoint owner (Research Scientists); config owner = gate config
# owner (Eval Engineers). Either team may stand in for the other when one runs out.
RELEASE_OWNER_TEAMS = ("alignment", "evaluations")
CONFIG_OWNER_TEAMS = ("evaluations", "alignment")
ROLES = ("release_owner", "config_owner", "approver_a", "approver_b")


class ReleaseArcPlanningError(ValueError):
    """The cohort cannot staff the requested arcs (too few eligible honest accounts)."""


def load_release_arc_template(path: str | Path | None = None) -> dict[str, Any]:
    """Load the arc template (bootstrap/release_arcs_v1.yaml). Raises if absent:
    a run that asked for release arcs must not silently get none."""
    p = Path(path) if path is not None else DEFAULT_TEMPLATE
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not doc.get("steps"):
        raise ValueError(f"release arc template {p} has no steps")
    return doc


def load_insider_accounts(path: str | Path | None = None) -> set[str]:
    """Every account named in the insider assignment (solo, collusion and shadow
    cells, any threat). These are never cast in a release arc."""
    p = Path(path) if path is not None else DEFAULT_INSIDER_ASSIGNMENT
    if not p.exists():
        return set()
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    out: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, str):
            out.add(node)

    for section in ("solo", "collusion", "shadow"):
        walk(doc.get(section) or {})
    return out


def arc_seed(run_seed: int | None, index: int) -> int:
    """Deterministic per-arc seed (independent of PYTHONHASHSEED and of every other
    RNG stream in the run)."""
    h = hashlib.sha256(f"release-arc:{run_seed or 0}:{index}".encode()).hexdigest()
    return int(h[:12], 16)


def _bucket_aligned_start(day_start: str, bucket_minutes: int) -> int:
    hh, mm = (int(x) for x in str(day_start).split(":")[:2])
    minutes = hh * 60 + mm
    b = max(1, int(bucket_minutes))
    return -(-minutes // b) * b               # round UP to a bucket boundary


def _slot_clock(start_min: int, order: int, bucket_minutes: int,
                rng: random.Random) -> str:
    """HH:MM:SS for a step of bucket rank `order`: the bucket's start plus a small
    jitter that stays inside the bucket (so the rank, not the jitter, sets order)."""
    b = max(1, int(bucket_minutes))
    jitter_s = rng.randint(0, max(0, (b * 60) // 3))
    total_s = (start_min + order * b) * 60 + jitter_s
    total_s = min(total_s, 24 * 3600 - 1)
    return f"{total_s // 3600:02d}:{(total_s // 60) % 60:02d}:{total_s % 60:02d}"


def _pick(pool: list[Any], used: set[str], rng: random.Random) -> Any | None:
    free = [p for p in pool if p.id not in used]
    return rng.choice(free) if free else None


def plan_release_arcs(
    n_arcs: int,
    personas: Iterable[Any],
    sim_dates: list[str],
    *,
    seed: int | None = 0,
    insider_ids: Iterable[str] = (),
    bucket_minutes: int = 30,
    taken_checkpoint_ids: Iterable[str] = (),
    taken_ticket_ids: Iterable[str] = (),
    template: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Plan `n_arcs` honest release arcs over `sim_dates` for the cohort `personas`.

    Each arc gets four DISTINCT honest accounts, disjoint from every other arc's:
    two approvers from org group `model-approval`, a config owner and a release
    owner from evaluations/alignment. `insider_ids` are never cast. Checkpoint ids
    and ticket ids are distinct across arcs and avoid `taken_*` (ids already in the
    world, e.g. a branch parent's arcs). Raises ReleaseArcPlanningError when the
    cohort cannot staff `n_arcs` arcs.

    Returns one JSON-safe dict per arc: arc_id, seed, accounts (role -> account,
    plus deployer), checkpoint_id, model_id, version, ticket, config_change,
    planned_days {day1, day2}, and steps [{step_id, role, account, date, slot,
    order, directive}] in execution order.
    """
    if n_arcs <= 0:
        return []
    if not sim_dates:
        raise ReleaseArcPlanningError("release arcs need at least one sim day")
    tpl = template if template is not None else load_release_arc_template()
    insiders = set(insider_ids)
    honest = sorted((p for p in personas if p.id not in insiders), key=lambda p: p.id)
    approvers = [p for p in honest if APPROVER_GROUP in (getattr(p, "groups", ()) or ())]

    def team_pool(teams: tuple[str, ...]) -> list[Any]:
        # Preferred team first, then the stand-in team.
        return [p for t in teams for p in honest if (getattr(p, "team", "") or "") == t]

    owners = team_pool(RELEASE_OWNER_TEAMS)
    config_owners = team_pool(CONFIG_OWNER_TEAMS)

    model_id = str(tpl.get("model_id") or "archetype")
    prefix = str(tpl.get("version_prefix") or "v1.2-rc")
    rc_next = int(tpl.get("rc_start", 2))
    project = str(tpl.get("ticket_project") or "INFRA")
    lo, hi = (int(x) for x in (tpl.get("ticket_range") or [600, 899]))
    changes = list(tpl.get("config_changes") or [])
    if not changes:
        raise ValueError("release arc template has no config_changes")
    deployer_roles = list(tpl.get("deployer_roles") or ["release_owner"])
    start_min = _bucket_aligned_start(str(tpl.get("day_start") or "12:00"), bucket_minutes)
    taken_ckpts = set(taken_checkpoint_ids)
    taken_tickets = set(taken_ticket_ids)

    used: set[str] = set()
    arcs: list[dict[str, Any]] = []
    for idx in range(n_arcs):
        s = arc_seed(seed, idx)
        rng = random.Random(s)
        cast: dict[str, Any] = {}
        for role, pool in (("approver_a", approvers), ("approver_b", approvers),
                           ("config_owner", config_owners), ("release_owner", owners)):
            p = _pick(pool, used, rng)
            if p is None:
                raise ReleaseArcPlanningError(
                    f"cannot staff release arc {idx + 1} of {n_arcs}: no free honest "
                    f"{role} in the cohort (honest {APPROVER_GROUP} members: "
                    f"{[a.id for a in approvers]}; honest evaluations/alignment: "
                    f"{[o.id for o in owners]}). Each arc needs 4 distinct non-insider "
                    f"accounts (2 approvers in {APPROVER_GROUP}); widen the cohort "
                    f"(--personas) or ask for fewer arcs.")
            cast[role] = p.id
            used.add(p.id)
        cast["deployer"] = cast[rng.choice(deployer_roles)]

        while f"ckpt-{model_id}-{prefix}{rc_next}" in taken_ckpts:
            rc_next += 1
        version = f"{prefix}{rc_next}"
        checkpoint_id = f"ckpt-{model_id}-{version}"
        taken_ckpts.add(checkpoint_id)
        rc_next += 1

        free_tickets = [n for n in range(lo, hi + 1) if f"{project}-{n}" not in taken_tickets]
        if not free_tickets:
            raise ReleaseArcPlanningError(f"no free {project} ticket id in [{lo}, {hi}]")
        ticket = f"{project}-{rng.choice(free_tickets)}"
        taken_tickets.add(ticket)

        change = rng.choice(changes)
        n = len(sim_dates)
        d = rng.randint(0, n - 2) if n >= 2 else 0
        day1, day2 = sim_dates[d], sim_dates[min(d + 1, n - 1)]
        arcs.append({
            "arc_id": f"release-arc-{idx + 1:02d}",
            "seed": s,
            "accounts": cast,
            "checkpoint_id": checkpoint_id,
            "model_id": model_id,
            "version": version,
            "ticket": ticket,
            "ticket_project": project,
            "config_change": {"id": change.get("id"), "summary": change.get("summary")},
            "planned_days": {"day1": day1, "day2": day2},
            "_rng": rng,
            "_change": change,
        })

    # Gate-config edits bump the release-gate version, and an approval stays valid
    # only under the version its eval job ran on. So an arc whose day 2 sees ANY
    # arc's config edit must run its eval on day 2 (after that edit), not day 1.
    edit_dates = {a["planned_days"]["day1"] for a in arcs}
    for arc in arcs:
        rng: random.Random = arc.pop("_rng")
        change = arc.pop("_change")
        fill = {
            "checkpoint_id": arc["checkpoint_id"], "model_id": arc["model_id"],
            "version": arc["version"], "ticket": arc["ticket"],
            "ticket_project": arc["ticket_project"],
            **{r: arc["accounts"][r] for r in (*ROLES, "deployer")},
            "config_change_summary": str(change.get("summary") or "").strip(),
            "config_change_instruction": " ".join(str(change.get("instruction") or "").split()),
        }
        conflict = arc["planned_days"]["day2"] in edit_dates
        steps: list[dict[str, Any]] = []
        for st in tpl["steps"]:
            slots = [tuple(x) for x in st.get("slots") or [[1, 0]]]
            day_no, order = slots[-1] if (conflict and len(slots) > 1) else rng.choice(slots)
            date = arc["planned_days"]["day1" if int(day_no) == 1 else "day2"]
            steps.append({
                "step_id": f"{arc['arc_id']}:{st['id']}",
                "role": st["role"],
                "account": arc["accounts"][st["role"]],
                "date": date,
                "order": int(order),
                "slot": _slot_clock(start_min, int(order), bucket_minutes, rng),
                "directive": " ".join(str(st["directive"]).split()).format_map(fill),
            })
        steps.sort(key=lambda x: (x["date"], x["order"]))
        arc["steps"] = steps
    return arcs


def arc_schedules_by_account(arcs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """{account: [benign_arc_schedule entries]} for AgenticMember. Each entry is a
    benign-arc step with a fixed `slot` (HH:MM:SS) and the release-arc metadata the
    transcript records."""
    out: dict[str, list[dict[str, Any]]] = {}
    for arc in arcs:
        for i, st in enumerate(arc["steps"]):
            out.setdefault(st["account"], []).append({
                "date": st["date"],
                "step_idx": i,
                "directive": st["directive"],
                "slot": st["slot"],
                "step_id": st["step_id"],
                "arc_id": arc["arc_id"],
                "role": st["role"],
            })
    for entries in out.values():
        entries.sort(key=lambda e: (e["date"], e["slot"]))
    return out


def slot_datetime(date_iso: str, slot: str) -> datetime:
    """UTC datetime for a schedule entry's (date, HH:MM:SS slot)."""
    base = datetime.fromisoformat(date_iso[:10]).replace(tzinfo=timezone.utc)
    hh, mm, ss = (int(x) for x in (slot.split(":") + ["0", "0"])[:3])
    return base + timedelta(hours=hh, minutes=mm, seconds=ss)
