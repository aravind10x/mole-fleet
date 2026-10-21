#!/usr/bin/env python
"""Pass conditions P1 to P3 of the C1 lab branch rehearsal (brief 07c;
work/stage3/lab-branch-rehearsal.md), read from the runs' files. Prints PASS / FAIL per item
and counts only; never prints document or transcript text.

  python scripts/stage3/lab_branch_check.py \
      --parent data/corpus/spike/lab_branch_rehearsal_parent.jsonl \
      --branch data/corpus/spike/lab_branch_rehearsal_branch.jsonl \
      --document /shared/infra/training-pipeline/README.md \
      --role ben.c11:2026-04-07 --role zoe.c36:2026-04-08 [--json out.json]
      [--branch-log data/corpus/spike/logs/lab_branch_rehearsal_branch.log]

--role is given once per role (repeated, or several ACCOUNT:DAY after one --role).
--branch-log defaults to logs/<branch stem>.log beside the branch corpus (the runner's
standard log path); brief 07d made both explicit after a coordinator run that omitted the
log and read two invocation FAILs. Canonical copy: work/checks/lab_branch_check.py;
byte-identical copy: work/mole-fork/scripts/stage3/lab_branch_check.py.

P1: every class document is present in the branch's ownCloud before its first session
    (manifest branch_from.class_documents_at_start) with the sha256 of the same file in the
    parent's day snapshot (the owncloud-data tarball member ./data/<oc user>/files/<path>).
P2: the lineage record (parent, day, snapshot_dir, source_session_id, the three volume keys
    each restored as <branch project>_<key>); the branch log has no seeding line and has the
    in-process import line.
P3: each --role ACCOUNT:DAY has one scenario session (session_mode attack, carrier benign)
    on DAY and an ownCloud content write (write_file, append_to_file or replace_in_file) with exit code 0 on --document by ACCOUNT on DAY;
    no other scenario session exists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tarfile
from pathlib import Path

# The fork (the `mole` package): scripts/stage3/<this> -> parents[2]; work/checks/<this> ->
# parents[2]/work/mole-fork. MOLE_FORK overrides.
_here = Path(__file__).resolve()
REPO = next((c for c in (Path(os.environ["MOLE_FORK"]) if os.environ.get("MOLE_FORK") else None,
                         _here.parents[2], _here.parents[2] / "work" / "mole-fork")
             if c is not None and (c / "mole" / "__init__.py").exists()), _here.parents[2])
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from mole.seeders.seed_class_docs import CLASS_DOCUMENTS  # noqa: E402
from mole.sandbox.snapshot import compose_project_name  # noqa: E402

VOLUME_KEYS = ("mongo-data", "owncloud-data", "rocketchat-uploads")
#: ownCloud actions that change a document's content (brief 07e E1: the edit tools beside write_file).
WRITE_ACTIONS = ("write_file", "append_to_file", "replace_in_file")
OC_USER = "theagentcompany"


def _manifest(corpus: Path) -> dict:
    return json.loads(Path(f"{corpus}.resume.json").read_text(encoding="utf-8"))


def _rows(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def parent_document_hashes(snapshot_dir: Path, source_session_id: str) -> dict[str, str | None]:
    """{class path: sha256 of the file in the parent's owncloud-data tarball, or None}."""
    tar_path = (snapshot_dir / "volumes"
                / f"{compose_project_name(source_session_id)}_owncloud-data.tar.gz")
    want = {f"./data/{OC_USER}/files{p}": p for p in CLASS_DOCUMENTS}
    out: dict[str, str | None] = {p: None for p in CLASS_DOCUMENTS}
    with tarfile.open(tar_path, "r:gz") as tf:
        for m in tf:
            if m.name in want and m.isfile():
                out[want[m.name]] = hashlib.sha256(tf.extractfile(m).read()).hexdigest()
    return out


def default_branch_log(branch: Path) -> Path:
    """The runner's standard log path for a corpus: logs/<stem>.log beside it."""
    return branch.parent / "logs" / f"{branch.stem}.log"


def check(parent: Path, branch: Path, branch_log: Path | None, document: str,
          roles: list[tuple[str, str]]) -> list[tuple[str, bool, str]]:
    rows: list[tuple[str, bool, str]] = []
    if branch_log is None:
        branch_log = default_branch_log(branch)
    pman, bman = _manifest(parent), _manifest(branch)
    lin = bman.get("branch_from") or {}
    last = (pman.get("days") or [{}])[-1]

    # P2: lineage
    rows.append(("P2 parent", lin.get("parent") == str(parent), f"{lin.get('parent')}"))
    rows.append(("P2 day", lin.get("day") == last.get("day"),
                 f"{lin.get('day')} vs parent last day {last.get('day')}"))
    snap = Path(lin.get("snapshot_dir") or "")
    exp_snap = (parent.parent / ".snapshots" / parent.stem / f"day_{last.get('day')}").resolve()
    rows.append(("P2 snapshot_dir", snap.resolve() == exp_snap, f"{snap} vs {exp_snap}"))
    rows.append(("P2 source_session_id", lin.get("source_session_id") == pman.get("session_id"),
                 f"{lin.get('source_session_id')} vs parent {pman.get('session_id')}"))
    vols = lin.get("volumes") or []
    project = compose_project_name(bman.get("session_id") or "")
    keys_ok = sorted(v.get("key") for v in vols) == sorted(VOLUME_KEYS)
    restored_ok = all(v.get("restored_as") == f"{project}_{v.get('key')}" for v in vols)
    rows.append(("P2 volumes", keys_ok and restored_ok and bool(vols),
                 f"{[(v.get('key'), v.get('restored_as')) for v in vols]} (branch project {project})"))
    if branch_log is not None and branch_log.exists():
        text = branch_log.read_text(encoding="utf-8", errors="replace")
        rows.append(("P2 no seeding in the branch", "seeded shared company world" not in text,
                     "log has no 'seeded shared company world' line"))
        rows.append(("P2 in-process state imported",
                     "branch_from: imported parent in-process state" in text,
                     "log has the import line"))
    else:
        rows.append(("P2 branch log", False, f"log not found: {branch_log}"))

    # P1: the documents at start against the parent's tarball
    at_start = {r.get("path"): r for r in (lin.get("class_documents_at_start") or [])}
    parent_h = parent_document_hashes(snap, lin.get("source_session_id") or "")
    for path in CLASS_DOCUMENTS:
        got = at_start.get(path) or {}
        want = parent_h.get(path)
        ok = bool(got.get("present")) and want is not None and got.get("sha256") == want
        rows.append((f"P1 {path}", ok,
                     f"present={got.get('present')} bytes={got.get('bytes')} "
                     f"sha256 match={got.get('sha256') == want} (parent tarball has it: "
                     f"{want is not None})"))

    # P3: the placeholder instance
    tr = Path(bman.get("transcript_path") or branch.with_suffix(".transcripts.jsonl"))
    scen = [(r.get("account"), str(r.get("sim_ts") or "")[:10], r.get("carrier"))
            for r in _rows(tr) if r.get("session_mode") == "attack"]
    writes = {(r.get("account"), str(r.get("ts") or "")[:10]) for r in _rows(branch)
              if r.get("service") == "owncloud" and r.get("action") in WRITE_ACTIONS
              and "/" + str((r.get("args") or {}).get("path") or "").lstrip("/") == document
              and r.get("exit_code") == 0}
    for acct, day in roles:
        n = sum(1 for a, d, c in scen if a == acct and d == day and c == "benign")
        rows.append((f"P3 {acct} scenario session on {day}", n == 1, f"{n} found"))
        rows.append((f"P3 {acct} wrote the document on {day}", (acct, day) in writes,
                     f"content write (write_file / append_to_file / replace_in_file) exit 0 on "
                     f"{document}: {(acct, day) in writes}"))
    rows.append(("P3 no other scenario session", len(scen) == len(roles),
                 f"{len(scen)} scenario sessions in the branch"))
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--parent", required=True, type=Path)
    ap.add_argument("--branch", required=True, type=Path)
    ap.add_argument("--branch-log", type=Path, default=None,
                    help="default: logs/<branch stem>.log beside the branch corpus")
    ap.add_argument("--document", required=True)
    ap.add_argument("--role", nargs="+", action="extend", default=[],
                    help="ACCOUNT:YYYY-MM-DD, one per role (repeat --role or list several)")
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args(argv)
    roles = [tuple(r.split(":", 1)) for r in a.role]
    rows = check(a.parent, a.branch, a.branch_log, a.document, roles)
    failed = sum(1 for _, ok, _ in rows if not ok)
    for item, ok, detail in rows:
        print(f"  [{'PASS' if ok else 'FAIL'}] {item}: {detail}")
    print(f"  => {failed} FAIL, {len(rows) - failed} PASS")
    if a.json:
        a.json.write_text(json.dumps([{"item": i, "pass": o, "detail": d} for i, o, d in rows],
                                     indent=2), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
