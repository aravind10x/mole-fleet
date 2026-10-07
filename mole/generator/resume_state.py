"""Day-boundary resume manifest for the generator.

A crash (OOM, node reboot, auth death) can strike mid-day. Resuming cleanly needs
a single source of truth for "the last fully-committed sim day" plus enough
bookkeeping to (a) trim any partial/garbage tail written after it and (b) restore
the world to that boundary. This module owns that manifest.

Why not just scan the audit log for the max date (the old `_last_completed_day`)?
Because a *partial* day looks identical to a complete one — a run that died early
on day 3 leaves day-3 events, so the date-scan treats day 3 as done and resumes at
day 4, silently abandoning the partial day AND keeping whatever garbage was
appended after the crash. The manifest fixes both: it only ever names a day whose
outputs are durably on disk, and it records the exact byte offsets to truncate
back to.

The manifest lives next to the audit log as `<audit>.resume.json` and is written
ATOMICALLY (tmp + os.replace) at each day boundary, AFTER the audit log,
transcript, in-process state export and docker snapshot for that day are flushed.

Per-day record (`days[]`):
  day               the YYYY-MM-DD that just completed
  audit_bytes       byte length of the audit jsonl at the boundary (truncate target)
  transcript_bytes  byte length of the transcript jsonl at the boundary
  snapshot_ok       docker world snapshot for the day succeeded (Phase B restore)
  managers_ok       in-process manager state export for the day succeeded
  snapshot_dir      path to the day's snapshot dir (if snapshot_ok)
  managers_path     path to the day's managers.json (if managers_ok)

Session-completion fields (None when the counts are unknown — e.g. rules mode, which
writes no transcript, or a manifest written before these fields existed):
  sessions_planned           sessions in the day's plan
  sessions_completed         sessions whose transcript record has no abort
                             (aborted_reason None, or "max_turns" — hitting the turn
                             cap is a normal end, not an abort)
  sessions_aborted           sessions aborted for any other reason (e.g. "llm_error:..."
                             from a provider 402/5xx), plus planned sessions that wrote
                             no transcript record at all (raised before writing one)
  attack_sessions_planned    sessions recorded with session_mode == "attack"
  attack_sessions_completed  of those, the ones that completed
  sessions_ok                derived: sessions_aborted == 0 and every attack session
                             completed; None when the counts are unknown

A day can export a perfectly valid managers.json while its sessions died mid-day
(the provider ran out of credit): managers_ok says the WORLD boundary is restorable,
sessions_ok says the day's CONTENT is complete. Resume selection still uses only the
former; `day_is_clean` / the --resume warning surface the latter for the operator.

Resume reads the LAST record for the truncation offsets + resume-from day, and the
last record with `snapshot_ok` for the world to restore (Phase B).
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from ..audit.io_retry import retry_on_disk_full

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


def manifest_path(audit_path: Path | str) -> Path:
    """Resume manifest path for a given audit-log path: `<audit>.resume.json`.

    We append rather than replace the suffix so it's unambiguous and never
    collides with the `.transcripts.jsonl` sibling.
    """
    audit_path = Path(audit_path)
    return audit_path.parent / (audit_path.name + ".resume.json")


def new_manifest(
    *,
    audit_path: Path | str,
    transcript_path: Path | str,
    start_date: str,
    n_days: int,
    seed: int | None,
    session_id: str | None,
) -> dict[str, Any]:
    """A fresh manifest for a new (non-resume) run."""
    return {
        "schema_version": SCHEMA_VERSION,
        "audit_path": str(audit_path),
        "transcript_path": str(transcript_path),
        "start_date": start_date,
        "n_days": n_days,
        "seed": seed,
        "session_id": session_id,
        "days": [],
    }


def load(audit_path: Path | str) -> dict[str, Any] | None:
    """Load the manifest for an audit log, or None if absent/unreadable."""
    p = manifest_path(audit_path)
    if not p.exists():
        return None
    try:
        m = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("resume_state: manifest %s unreadable (%s); ignoring", p, exc)
        return None
    if m.get("schema_version") != SCHEMA_VERSION:
        logger.warning("resume_state: manifest %s schema %s != %s; ignoring",
                       p, m.get("schema_version"), SCHEMA_VERSION)
        return None
    return m


def write_atomic(manifest: dict[str, Any], audit_path: Path | str) -> None:
    """Write the manifest atomically (tmp + os.replace) so a crash mid-write
    never leaves a torn manifest — the old one survives intact."""
    p = manifest_path(audit_path)
    tmp = p.parent / (p.name + ".tmp")
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, indent=2).encode("utf-8")

    def _do() -> None:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, p)

    # The tmp+replace body is idempotent, so retrying the whole thing on a full
    # disk (ENOSPC/EDQUOT) is safe — the manifest write STALLS instead of raising
    # and killing the sim at a day boundary.
    retry_on_disk_full(_do, what="resume manifest")


def record_day(
    manifest: dict[str, Any],
    audit_path: Path | str,
    *,
    day: str,
    audit_bytes: int,
    transcript_bytes: int,
    snapshot_ok: bool,
    managers_ok: bool,
    snapshot_dir: str | None = None,
    managers_path: str | None = None,
    sessions_planned: int | None = None,
    sessions_completed: int | None = None,
    sessions_aborted: int | None = None,
    attack_sessions_planned: int | None = None,
    attack_sessions_completed: int | None = None,
) -> None:
    """Append a completed-day record and persist the manifest atomically.

    Idempotent on `day`: re-recording a day (e.g. a re-run day on resume)
    replaces the prior record for that day rather than duplicating it.

    The session counts are optional (callers that pass none get None fields and
    `sessions_ok` None); see the module docstring for their meaning.
    """
    def _opt_int(v: int | None) -> int | None:
        return None if v is None else int(v)

    rec = {
        "day": day,
        "audit_bytes": int(audit_bytes),
        "transcript_bytes": int(transcript_bytes),
        "snapshot_ok": bool(snapshot_ok),
        "managers_ok": bool(managers_ok),
        "snapshot_dir": str(snapshot_dir) if snapshot_dir else None,
        "managers_path": str(managers_path) if managers_path else None,
        "sessions_planned": _opt_int(sessions_planned),
        "sessions_completed": _opt_int(sessions_completed),
        "sessions_aborted": _opt_int(sessions_aborted),
        "attack_sessions_planned": _opt_int(attack_sessions_planned),
        "attack_sessions_completed": _opt_int(attack_sessions_completed),
    }
    rec["sessions_ok"] = _derive_sessions_ok(rec)
    days = [d for d in manifest.get("days", []) if d.get("day") != day]
    days.append(rec)
    days.sort(key=lambda d: d["day"])
    manifest["days"] = days
    write_atomic(manifest, audit_path)


def _derive_sessions_ok(rec: dict[str, Any]) -> bool | None:
    """True iff no session aborted and every attack session completed; None when
    the abort count or either attack count is unknown."""
    aborted = rec.get("sessions_aborted")
    a_plan = rec.get("attack_sessions_planned")
    a_done = rec.get("attack_sessions_completed")
    if aborted is None or a_plan is None or a_done is None:
        return None
    return aborted == 0 and a_done == a_plan


def day_is_clean(rec: dict[str, Any] | None) -> bool | None:
    """Did this day's sessions all complete? True/False from the recorded
    `sessions_ok`; None when unknown (no record, a pre-counts manifest, or a run
    mode with no transcript). Informational only — resume selection never uses it."""
    if not rec:
        return None
    ok = rec.get("sessions_ok")
    if ok is None and "sessions_ok" not in rec:
        ok = _derive_sessions_ok(rec)   # hand-edited / partial record
    return None if ok is None else bool(ok)


def session_aborted(rec: dict[str, Any]) -> bool:
    """A transcript record counts as aborted when `aborted_reason` is set and is
    not "max_turns" (the turn cap is a normal session end)."""
    reason = rec.get("aborted_reason")
    return bool(reason) and reason != "max_turns"


def tally_day_sessions(
    transcript_path: Path | str,
    *,
    day: str,
    sessions_planned: int,
    start_byte: int = 0,
    end_byte: int | None = None,
) -> dict[str, int]:
    """Count the day's session outcomes from the transcript file.

    Reads transcript records in [start_byte, end_byte) whose `sim_ts` falls on
    `day` (the date filter makes a start of 0 safe for a branch, whose transcript
    begins with the parent's earlier days). Scanning the FILE rather than an
    in-memory tally means a --session-resume re-entry also counts the buckets
    that ran before the crash. Unparseable lines are skipped. Planned sessions
    with no record are counted as aborted. Returns the `record_day` count kwargs.
    """
    completed = aborted = attack_planned = attack_completed = 0
    path = Path(transcript_path)
    if path.exists():
        with path.open("rb") as f:
            f.seek(max(0, int(start_byte)))
            data = f.read() if end_byte is None else f.read(max(0, int(end_byte) - int(start_byte)))
        for line in data.splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            if not isinstance(rec, dict) or str(rec.get("sim_ts") or "")[:10] != day:
                continue
            is_attack = rec.get("session_mode") == "attack"
            if session_aborted(rec):
                aborted += 1
            else:
                completed += 1
                if is_attack:
                    attack_completed += 1
            if is_attack:
                attack_planned += 1
    missing = max(0, int(sessions_planned) - completed - aborted)
    return {
        "sessions_planned": int(sessions_planned),
        "sessions_completed": completed,
        "sessions_aborted": aborted + missing,
        "attack_sessions_planned": attack_planned,
        "attack_sessions_completed": attack_completed,
    }


def record_in_progress(
    manifest: dict[str, Any],
    audit_path: Path | str,
    *,
    day: str,
    next_bucket_index: int,
    audit_bytes: int,
    transcript_bytes: int,
    day_plan: list[Any],
) -> None:
    """Record a mid-day (bucket-boundary) checkpoint for session-level resume.

    Written after each quiescent bucket boundary WITHIN a day (only when the run
    opted in via --session-resume). Records: the day being generated, the index of
    the NEXT bucket to run, the audit/transcript byte offsets to trim a partial tail
    back to, and the serialized day plan. The saved plan lets resume reproduce the
    exact slots + attack schedule for the interrupted day WITHOUT re-running plan_day
    (which, under this run's day-0 RNG state on a fresh process, would diverge).

    Superseded by the day's committed record: `clear_in_progress` drops it when the
    day finishes. A single object (not a list) — only the newest mid-day boundary
    matters. Optional field; absent for runs that never used --session-resume, so
    old readers ignore it and the manifest schema stays version 1."""
    manifest["in_progress"] = {
        "day": day,
        "next_bucket_index": int(next_bucket_index),
        "audit_bytes": int(audit_bytes),
        "transcript_bytes": int(transcript_bytes),
        "day_plan": day_plan,
    }
    write_atomic(manifest, audit_path)


def clear_in_progress(manifest: dict[str, Any], audit_path: Path | str) -> None:
    """Drop the mid-day checkpoint — the just-committed day in `days[]` supersedes
    it, so a later resume must land on the day boundary, not re-enter the finished
    day. No-op (and no write) if there was no checkpoint."""
    if manifest.pop("in_progress", None) is not None:
        write_atomic(manifest, audit_path)


def in_progress_record(manifest: dict[str, Any]) -> dict[str, Any] | None:
    """The mid-day (bucket-boundary) checkpoint, or None. Present only for a run
    generated with --session-resume that died partway through a day (a clean
    day-boundary or non-session-resume run has none)."""
    return manifest.get("in_progress")


def last_completed_day(manifest: dict[str, Any]) -> str | None:
    """The most recent fully-committed sim day, or None if the manifest is empty."""
    days = manifest.get("days") or []
    return days[-1]["day"] if days else None


def last_completed_record(manifest: dict[str, Any]) -> dict[str, Any] | None:
    days = manifest.get("days") or []
    return days[-1] if days else None


def last_restorable_record(manifest: dict[str, Any]) -> dict[str, Any] | None:
    """The most recent day with a COMPLETE world boundary — both the docker
    snapshot and the in-process manager export succeeded. That alignment is what
    lets a --restore-world resume bring docker + in-process state back to the
    SAME day without one being ahead of the other. None if no such day exists."""
    for rec in reversed(manifest.get("days") or []):
        if (rec.get("snapshot_ok") and rec.get("snapshot_dir")
                and rec.get("managers_ok") and rec.get("managers_path")):
            return rec
    return None


def truncate_outputs(
    manifest: dict[str, Any],
    audit_path: Path | str,
    transcript_path: Path | str,
) -> tuple[int, int]:
    """Truncate the audit + transcript files back to the last completed day's
    byte offsets, discarding any partial/aborted tail written after the crash.

    Returns (audit_bytes_trimmed, transcript_bytes_trimmed). A no-op (0, 0) if
    the manifest has no completed days or the files are already short enough.
    """
    return truncate_to_record(last_completed_record(manifest), audit_path, transcript_path)


def truncate_to_record(
    rec: dict[str, Any] | None,
    audit_path: Path | str,
    transcript_path: Path | str,
) -> tuple[int, int]:
    """Truncate audit + transcript back to a SPECIFIC day record's byte offsets.

    Used both for the default resume (last completed day) and the
    --restore-world resume (the last day whose docker snapshot also succeeded —
    so audit/transcript line up with the restored world, not a later partial
    day). Returns (audit_trimmed, transcript_trimmed); (0, 0) if rec is None.
    """
    if rec is None:
        return (0, 0)
    trimmed = []
    for path, key in ((audit_path, "audit_bytes"), (transcript_path, "transcript_bytes")):
        path = Path(path)
        target = int(rec[key])
        if not path.exists():
            trimmed.append(0)
            continue
        cur = path.stat().st_size
        if cur <= target:
            trimmed.append(0)
            continue
        with path.open("r+b") as f:
            f.truncate(target)
        logger.info("resume_state: truncated %s from %d -> %d bytes (dropped %d)",
                    path.name, cur, target, cur - target)
        trimmed.append(cur - target)
    return (trimmed[0], trimmed[1])


_TABLE_COLS = (
    ("day", "day"),
    ("audit_bytes", "audit_bytes"),
    ("managers_ok", "managers_ok"),
    ("sessions_planned", "planned"),
    ("sessions_completed", "completed"),
    ("sessions_aborted", "aborted"),
    ("attack_sessions_planned", "atk_planned"),
    ("attack_sessions_completed", "atk_completed"),
    ("sessions_ok", "sessions_ok"),
)


def format_day_table(manifest: dict[str, Any]) -> str:
    """Plain-text table of the manifest's day records (missing fields show '-')."""
    rows = [[h for _, h in _TABLE_COLS]]
    for rec in manifest.get("days") or []:
        rows.append(["-" if rec.get(k) is None else str(rec.get(k)) for k, _ in _TABLE_COLS])
    widths = [max(len(r[i]) for r in rows) for i in range(len(_TABLE_COLS))]
    return "\n".join("  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip() for r in rows)


def main(argv: list[str] | None = None) -> int:
    """`python -m mole.generator.resume_state <audit.jsonl>` — print the resume
    manifest's day table. Read-only."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] in ("-h", "--help"):
        print("usage: python -m mole.generator.resume_state <audit.jsonl>", file=sys.stderr)
        return 2
    m = load(args[0])
    if m is None:
        print(f"no readable resume manifest at {manifest_path(args[0])}", file=sys.stderr)
        return 1
    print(format_day_table(m))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
