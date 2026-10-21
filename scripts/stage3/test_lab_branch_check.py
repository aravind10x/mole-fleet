"""Offline tests for lab_branch_check.py (P1 to P3 of the C1 lab branch rehearsal) on a
synthetic parent/branch pair laid out like the generator's: data/corpus/spike/<stem>.jsonl,
<stem>.jsonl.resume.json, logs/<stem>.log, .snapshots/<stem>/day_<d>/volumes/<project>_owncloud-data.tar.gz.
Placeholder bytes only; no document, persona or objective text.

Run: work/mole-fork/.venv/bin/python -I -m pytest -q /abs/work/checks/test_lab_branch_check.py
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lab_branch_check as lbc  # noqa: E402

PARENT, BRANCH = "p_parent", "p_branch"
PDAY, D1, D2 = "2026-04-06", "2026-04-07", "2026-04-08"
PSESS, BSESS = "itb-npc-aaaa1111", "itb-npc-bbbb2222"
DOC = "/shared/infra/training-pipeline/README.md"
ROLES = [("ben.c11", D1), ("zoe.c36", D2)]


def _lay_out(tmp_path: Path, *, log_line_ok=True) -> tuple[Path, Path]:
    spike = tmp_path / "data" / "corpus" / "spike"
    (spike / "logs").mkdir(parents=True)
    docs = {p: f"placeholder {i}\n".encode() for i, p in enumerate(lbc.CLASS_DOCUMENTS)}
    # parent manifest + snapshot tarball holding the six documents
    snap = spike / ".snapshots" / PARENT / f"day_{PDAY}"
    (snap / "volumes").mkdir(parents=True)
    project = lbc.compose_project_name(PSESS)
    with tarfile.open(snap / "volumes" / f"{project}_owncloud-data.tar.gz", "w:gz") as tf:
        for p, b in docs.items():
            ti = tarfile.TarInfo(f"./data/{lbc.OC_USER}/files{p}")
            ti.size = len(b)
            tf.addfile(ti, io.BytesIO(b))
    parent = spike / f"{PARENT}.jsonl"
    parent.write_text("")
    Path(f"{parent}.resume.json").write_text(json.dumps({
        "session_id": PSESS, "days": [{"day": PDAY}]}))
    # branch manifest, audit log, transcripts, log
    branch = spike / f"{BRANCH}.jsonl"
    with branch.open("w") as f:
        for acct, day in ROLES:
            f.write(json.dumps({"account": acct, "ts": f"{day}T10:00:00Z", "service": "owncloud",
                                "action": "write_file", "args": {"path": DOC}, "exit_code": 0}) + "\n")
    tr = spike / f"{BRANCH}.transcripts.jsonl"
    with tr.open("w") as f:
        for acct, day in ROLES:
            f.write(json.dumps({"account": acct, "sim_ts": f"{day}T10:00:00Z",
                                "session_mode": "attack", "carrier": "benign"}) + "\n")
        f.write(json.dumps({"account": "wei.n2", "sim_ts": f"{D2}T11:00:00Z",
                            "session_mode": "benign"}) + "\n")
    bproject = lbc.compose_project_name(BSESS)
    Path(f"{branch}.resume.json").write_text(json.dumps({
        "session_id": BSESS, "transcript_path": str(tr),
        "branch_from": {
            "parent": str(parent), "day": PDAY, "managers_path": str(snap / "managers.json"),
            "snapshot_dir": str(snap), "source_session_id": PSESS,
            "volumes": [{"key": k, "restored_as": f"{bproject}_{k}"} for k in lbc.VOLUME_KEYS],
            "class_documents_at_start": [
                {"path": p, "present": True, "bytes": len(b),
                 "sha256": hashlib.sha256(b).hexdigest()} for p, b in docs.items()]}}))
    (spike / "logs" / f"{BRANCH}.log").write_text(
        "branch_from: imported parent in-process state\n" if log_line_ok
        else "seeded shared company world\n")
    return parent, branch


def _rows(parent, branch, **kw):
    return {i: (ok, d) for i, ok, d in lbc.check(parent, branch, kw.get("branch_log"),
                                                  DOC, kw.get("roles", ROLES))}


def test_all_items_pass_on_a_consistent_pair(tmp_path):
    parent, branch = _lay_out(tmp_path)
    rows = _rows(parent, branch, branch_log=branch.parent / "logs" / f"{BRANCH}.log")
    assert all(ok for ok, _ in rows.values()), {i: r for i, r in rows.items() if not r[0]}
    assert len([i for i in rows if i.startswith("P1 ")]) == 6
    assert len([i for i in rows if i.startswith("P3 ")]) == 5


def test_branch_log_defaults_to_the_standard_log_path(tmp_path):
    """Brief 07d: the coordinator's run omitted --branch-log and read two FAILs that were
    invocation artefacts; the default is logs/<branch stem>.log beside the corpus."""
    parent, branch = _lay_out(tmp_path)
    assert lbc.default_branch_log(branch) == branch.parent / "logs" / f"{BRANCH}.log"
    rows = _rows(parent, branch)                           # no --branch-log
    assert rows["P2 no seeding in the branch"][0] and rows["P2 in-process state imported"][0]
    parent, branch = _lay_out(tmp_path / "bad", log_line_ok=False)
    rows = _rows(parent, branch)
    assert rows["P2 no seeding in the branch"][0] is False
    assert rows["P2 in-process state imported"][0] is False


def test_role_is_accepted_repeatedly_and_as_a_list(tmp_path, capsys):
    parent, branch = _lay_out(tmp_path)
    common = ["--parent", str(parent), "--branch", str(branch), "--document", DOC]
    assert lbc.main(common + ["--role", "ben.c11:2026-04-07", "--role", "zoe.c36:2026-04-08"]) == 0
    assert lbc.main(common + ["--role", "ben.c11:2026-04-07", "zoe.c36:2026-04-08"]) == 0
    # one role given for a two-role instance: the "no other scenario session" item FAILs
    assert lbc.main(common + ["--role", "ben.c11:2026-04-07"]) == 1
    out = capsys.readouterr().out
    assert "[FAIL] P3 no other scenario session" in out


def test_json_output_and_hash_mismatch(tmp_path):
    parent, branch = _lay_out(tmp_path)
    man = json.loads(Path(f"{branch}.resume.json").read_text())
    man["branch_from"]["class_documents_at_start"][2]["sha256"] = "0" * 64
    Path(f"{branch}.resume.json").write_text(json.dumps(man))
    out = tmp_path / "o.json"
    rc = lbc.main(["--parent", str(parent), "--branch", str(branch), "--document", DOC,
                   "--role", "ben.c11:2026-04-07", "--role", "zoe.c36:2026-04-08",
                   "--json", str(out)])
    assert rc == 1
    rows = {r["item"]: r["pass"] for r in json.loads(out.read_text())}
    assert sum(1 for i, ok in rows.items() if i.startswith("P1 ") and not ok) == 1
