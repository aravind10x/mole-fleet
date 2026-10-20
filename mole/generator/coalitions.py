"""Coalition INSTANCES per collusion threat (Stage 2b; blue-side infrastructure).

`bootstrap/insider_assignment.yaml` holds one account per (threat, level, role) cell, so a
threat can run at most one coalition per stealth level. The Stage 2b design plants several
coalitions of the same threat per generated branch, each with its own role-to-account map.
This module loads that assignment (`bootstrap/coalitions_stage2b.yaml`, schema
`coalitions-v1`) for ONE branch and turns it into the per-account maps the runner already
uses (`persona_map`, `threat_map`, `role_map`, `level_map`) plus two new ones: the campaign
window per account and the acting-role order per instance.

Persona files are named by instance: `<threat>_<branch>_<n>_<role>.yaml` (instance id
"A1" -> branch "A", n "1"), in `bootstrap/personas/` only. A missing file prints the
runner's usual "warn: persona file missing" line and leaves the account out of
`persona_map`, so it is never planned as an attacker (as for any designated insider
without a persona). Nothing here contains or generates persona, goal or directive text.

Two schema versions load through the same `load_coalitions`:

`coalitions-v1` (Stage 2b; unchanged) targets `c4_access_split` (an escalated account):

    schema: coalitions-v1
    stage: <str>                       # optional, informational
    threat: c4_access_split
    variant: k2_req_app                # roles of every instance, in acting order
    draw: {...}                        # optional provenance; copied into the manifest verbatim
    reserved_honest_accounts: [...]    # optional; an instance may not use these accounts
    branches:
      A:
        corpus: branch_A               # optional, informational
        instances:
          - id: A1
            stealth_level: s0
            target_group: model-approval
            roles: {requester: <acct>, approver: <acct>}   # in acting order
            campaign_window: {first_day: 1, last_day: 3}   # 1-based branch working days

`coalitions-v2` (Stage 3) adds the family F4 threat `f4_shared_doc`: each instance
poisons ONE shared document that honest accounts later read; there is no escalated
account, so `target_account` is None for F4 and `TARGET_ROLE` has no F4 entry. F4
instances name the document they target and may omit `stealth_level` (default s0) and
`target_group` (not meaningful for F4):

    schema: coalitions-v2
    threat: f4_shared_doc
    variant: k3                        # k2 -> [editor_1, editor_2]; k3 -> +editor_3
    branches:
      R:
        instances:
          - id: R1
            document: {service: owncloud, path: /shared/runbooks/README.md}
            roles: {editor_1: <acct>, editor_2: <acct>, editor_3: <acct>}   # acting order
            campaign_window: {first_day: 1, last_day: 5}   # len >= number of roles
            # stealth_level, target_group optional for F4

Both versions use the same per-account maps, persona-file naming and manifest entry.
Nothing here contains or generates persona, goal or directive text.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SCHEMA = "coalitions-v1"
SCHEMA_V2 = "coalitions-v2"
SCHEMAS = (SCHEMA, SCHEMA_V2)

#: Threat whose instances poison a shared document (family F4); v2-only, no escalated
#: account (so it has no TARGET_ROLE entry and its target_account is None).
F4_THREAT = "f4_shared_doc"

#: Services a shared F4 document may live on (one per instance).
F4_DOCUMENT_SERVICES = ("owncloud", "gitlab", "plane", "eval_server")

#: Roles per variant, in acting order (mirrors each threat task's METADATA).
#: c4 variant names ("k3") collide with F4's, so VARIANT_ROLES is keyed by threat.
VARIANT_ROLES: dict[str, dict[str, list[str]]] = {
    "c4_access_split": {
        "k2_req_app": ["requester", "approver"],
        "k2_app_admin": ["approver", "group_admin"],
        "k3": ["requester", "approver", "group_admin"],
    },
    F4_THREAT: {
        "k2": ["editor_1", "editor_2"],
        "k3": ["editor_1", "editor_2", "editor_3"],
    },
}

#: The account escalated by a variant: the requester, except k2_app_admin (the approver).
#: F4 variants are absent on purpose -- F4 escalates no account, so target_account is None.
TARGET_ROLE: dict[str, str] = {"k2_req_app": "requester", "k3": "requester",
                               "k2_app_admin": "approver"}

_INSTANCE_ID_RE = re.compile(r"^([A-Za-z]+)(\d+)$")


@dataclass
class Instance:
    id: str
    branch: str
    threat: str
    variant: str
    stealth_level: str
    target_group: str
    roles: dict[str, str]              # role -> account, in acting order
    window: tuple[int, int]            # (first_day, last_day), 1-based branch working days
    persona_files: dict[str, str] = field(default_factory=dict)   # role -> file name
    document: dict[str, str] | None = None   # F4: {service, path} of the shared document

    @property
    def role_order(self) -> list[str]:
        return list(self.roles)

    @property
    def accounts(self) -> list[str]:
        return list(self.roles.values())

    @property
    def target_account(self) -> str | None:
        """The account a variant escalates, or None when the threat escalates no
        account (family F4 poisons a shared document rather than an account)."""
        if self.threat == F4_THREAT:
            return None
        return self.roles[TARGET_ROLE[self.variant]]


def persona_file_name(threat: str, instance_id: str, role: str) -> str:
    m = _INSTANCE_ID_RE.match(instance_id)
    if not m:
        raise ValueError(f"instance id {instance_id!r} must be <letters><digits>, e.g. A1")
    return f"{threat}_{m.group(1)}_{m.group(2)}_{role}.yaml"


def _req(d: dict, key: str, where: str) -> Any:
    if key not in d:
        raise ValueError(f"{where}: missing key {key!r}")
    return d[key]


def _parse_document(inst: dict, where: str) -> dict[str, str]:
    """Validate and normalise an F4 instance's shared-document target."""
    raw = _req(inst, "document", where)
    if not isinstance(raw, dict):
        raise ValueError(f"{where}: document must be a mapping {{service, path}}")
    service = str(_req(raw, "service", where))
    if service not in F4_DOCUMENT_SERVICES:
        raise ValueError(f"{where}: document.service {service!r} must be one of "
                         f"{list(F4_DOCUMENT_SERVICES)}")
    pth = _req(raw, "path", where)
    if not isinstance(pth, str) or not pth:
        raise ValueError(f"{where}: document.path must be a non-empty string")
    return {"service": service, "path": pth}


def load_coalitions(path: str | Path, branch_id: str) -> list[Instance]:
    """Parse and validate the assignment file (schema v1 or v2); return the
    instances of `branch_id`."""
    p = Path(path)
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    schema = doc.get("schema")
    if schema not in SCHEMAS:
        raise ValueError(f"{p}: schema {schema!r} is not one of {list(SCHEMAS)}")
    threat = str(_req(doc, "threat", str(p)))
    variant = str(_req(doc, "variant", str(p)))      # file default; an instance may override
    if threat not in VARIANT_ROLES or variant not in VARIANT_ROLES[threat]:
        raise ValueError(f"{p}: unknown threat/variant {threat!r}/{variant!r}")
    is_f4 = threat == F4_THREAT
    if is_f4 and schema != SCHEMA_V2:
        raise ValueError(f"{p}: threat {threat!r} requires schema {SCHEMA_V2!r}")
    reserved = set(doc.get("reserved_honest_accounts") or [])
    branches = _req(doc, "branches", str(p)) or {}
    if branch_id not in branches:
        raise ValueError(f"{p}: branch {branch_id!r} not in {sorted(branches)}")
    raw = (branches[branch_id] or {}).get("instances") or []
    if not raw:
        raise ValueError(f"{p}: branch {branch_id!r} has no instances")
    out: list[Instance] = []
    seen_accounts: dict[str, str] = {}
    seen_ids: set[str] = set()
    for i, inst in enumerate(raw):
        where = f"{p}: branch {branch_id} instance {i}"
        iid = str(_req(inst, "id", where))
        if iid in seen_ids:
            raise ValueError(f"{where}: duplicate instance id {iid!r}")
        seen_ids.add(iid)
        # stealth_level and target_group are optional for F4 (no escalated account / no
        # target group); required for the v1 c4 threat, unchanged.
        level = str(inst.get("stealth_level", "s0") if is_f4 else _req(inst, "stealth_level", where))
        if level not in ("s0", "s1"):
            raise ValueError(f"{where}: stealth_level {level!r} must be s0 or s1")
        group = str(inst.get("target_group", "") if is_f4 else _req(inst, "target_group", where))
        document = _parse_document(inst, where) if is_f4 else None
        # v2 may mix variants within one branch (e.g. F4's k2 and k3): an instance may
        # override the file-level variant. v1 files omit it, so they keep the file default.
        inst_variant = str(inst.get("variant", variant))
        if inst_variant not in VARIANT_ROLES[threat]:
            raise ValueError(f"{where}: unknown variant {inst_variant!r} for threat {threat!r}")
        roles_expected = VARIANT_ROLES[threat][inst_variant]
        roles_raw = _req(inst, "roles", where) or {}
        if list(roles_raw) != roles_expected:
            raise ValueError(f"{where}: roles {list(roles_raw)} must be exactly {roles_expected} "
                             f"in that order (variant {inst_variant})")
        roles = {r: str(a) for r, a in roles_raw.items()}
        for r, a in roles.items():
            if a in seen_accounts:
                raise ValueError(f"{where}: account {a!r} ({r}) already used in instance "
                                 f"{seen_accounts[a]} of branch {branch_id}")
            if a in reserved:
                raise ValueError(f"{where}: account {a!r} ({r}) is in reserved_honest_accounts")
            seen_accounts[a] = iid
        if len(set(roles.values())) != len(roles):
            raise ValueError(f"{where}: the same account holds two roles")
        win = _req(inst, "campaign_window", where) or {}
        first, last = int(_req(win, "first_day", where)), int(_req(win, "last_day", where))
        if first < 1 or last < first:
            raise ValueError(f"{where}: campaign_window first_day={first} last_day={last} invalid")
        if last - first + 1 < len(roles):
            raise ValueError(f"{where}: window of {last - first + 1} days is shorter than "
                             f"{len(roles)} roles")
        out.append(Instance(id=iid, branch=branch_id, threat=threat, variant=inst_variant,
                            stealth_level=level, target_group=group, roles=roles,
                            window=(first, last),
                            persona_files={r: persona_file_name(threat, iid, r) for r in roles},
                            document=document))
    return out


def check_windows(instances: list[Instance], n_days: int) -> None:
    for inst in instances:
        if inst.window[1] > n_days:
            raise ValueError(f"instance {inst.id}: campaign_window ends on day {inst.window[1]} "
                             f"but the run has {n_days} working days")


def coalition_maps(instances: list[Instance], personas_dir: str | Path,
                   warn=print) -> dict[str, dict[str, Any]]:
    """Per-account maps for the runner: persona_map {account: override text} (only accounts
    whose persona file exists and matches), threat_map, role_map, level_map, window_map
    {account: (first_day, last_day)}, instance_map {account: instance id}, role_order_map
    {account: [roles of its instance in order]}, found_map {account: bool}."""
    pdir = Path(personas_dir)
    maps: dict[str, dict[str, Any]] = {k: {} for k in (
        "persona_map", "threat_map", "role_map", "level_map", "window_map", "instance_map",
        "role_order_map", "found_map")}
    for inst in instances:
        for role, acct in inst.roles.items():
            maps["threat_map"][acct] = inst.threat
            maps["role_map"][acct] = role
            maps["level_map"][acct] = inst.stealth_level
            maps["window_map"][acct] = inst.window
            maps["instance_map"][acct] = inst.id
            maps["role_order_map"][acct] = inst.role_order
            fname = inst.persona_files[role]
            path = pdir / fname
            if not path.exists():
                warn(f"warn: persona file missing for {acct} ({inst.threat}/{inst.id}/{role}): {fname}")
                maps["found_map"][acct] = False
                continue
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for key, want in (("employee_id", acct), ("threat", inst.threat),
                              ("stealth_level", inst.stealth_level), ("role_label", role)):
                if str(doc.get(key)) != want:
                    raise ValueError(f"{path}: {key}={doc.get(key)!r}, expected {want!r} "
                                     f"(instance {inst.id})")
            text = doc.get("persona_override")
            if not text:
                raise ValueError(f"{path}: empty persona_override")
            maps["persona_map"][acct] = text
            maps["found_map"][acct] = True
    return maps


def manifest_entry(path: str | Path, branch_id: str, instances: list[Instance],
                   maps: dict[str, dict[str, Any]],
                   schedules: dict[str, list[dict]] | None = None,
                   assignment_cells_skipped: str | None = None,
                   role_days: dict[str, str | None] | None = None) -> dict[str, Any]:
    """The `coalitions` block of the run manifest: provenance plus, per instance, the
    roles, accounts, window, the shared document (F4), persona-file presence and the
    planned attack dates per role (from `schedules` {account: [{date, phase, directive},
    ...]}, when attack planning ran). `assignment_cells_skipped` ("all" from the runner's
    coalitions-only mode) is recorded when given. `role_days` {account: day_iso} adds a
    `planned_role_day` per role (the day the role is scheduled to act); rules mode uses it
    to record role days without planning attack sessions, so `planned_attack_dates` stays
    null there. When `role_days` is None no `planned_role_day` field is emitted (v1 output
    unchanged)."""
    p = Path(path)
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    rec: dict[str, Any] = {
        "file": str(p), "file_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        # One variant for the whole branch, or "mixed" when its instances differ (v2 can
        # mix F4's k2 and k3); each instance record also carries its own variant.
        "branch_id": branch_id, "threat": doc.get("threat"),
        "variant": (instances[0].variant if len({i.variant for i in instances}) == 1
                    else "mixed") if instances else doc.get("variant"),
        "draw": doc.get("draw"), "instances": [],
    }
    if assignment_cells_skipped is not None:
        rec["assignment_cells_skipped"] = assignment_cells_skipped
    for inst in instances:
        roles = []
        for role, acct in inst.roles.items():
            sched = (schedules or {}).get(acct)
            entry = {"role": role, "account": acct,
                     "persona_file": inst.persona_files[role],
                     "persona_found": bool(maps["found_map"].get(acct)),
                     "planned_attack_dates": ([s["date"] for s in sched]
                                              if sched is not None else None)}
            if role_days is not None:
                entry["planned_role_day"] = role_days.get(acct)
            roles.append(entry)
        inst_rec = {"id": inst.id, "variant": inst.variant,
                    "stealth_level": inst.stealth_level,
                    "target_group": inst.target_group,
                    "target_account": inst.target_account,
                    "campaign_window": {"first_day": inst.window[0],
                                        "last_day": inst.window[1]},
                    "roles": roles}
        if inst.document is not None:
            inst_rec["document"] = inst.document
        rec["instances"].append(inst_rec)
    return rec
