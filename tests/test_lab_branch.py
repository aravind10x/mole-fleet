"""Cross-corpus branching in agentic lab mode (brief 07c C1).

A lab branch restores the parent day's docker volumes into its own fresh compose
project, so it must find a COMPLETE volume set for that day before it copies
anything, record the lineage (snapshot directory and volume list) in the manifest,
and leave the dryrun branch path exactly as it was. No Docker and no LLM here: the
docker calls are faked and the end-to-end check is the lab rehearsal
(work/stage3/lab-branch-rehearsal.md).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from mole.generator import resume_state
from mole.generator import run as run_mod
from mole.generator.run import _branch_lineage, _prepare_branch, simulate
from mole.sandbox import snapshot as snap_mod
from mole.sandbox.base import ExecResult

SOURCE = "itb-npc-0b41786c"
KEYS = ("mongo-data", "owncloud-data", "rocketchat-uploads")
COMPOSE = """services:
  owncloud:
    image: x
    volumes: [owncloud-data:/var/www/html]
  mongo:
    image: x
    volumes: [mongo-data:/bitnami/mongodb]
  rocketchat:
    image: x
    volumes: [rocketchat-uploads:/app/uploads]
volumes:
  owncloud-data: null
  mongo-data: null
  rocketchat-uploads: null
"""


def _compose(tmp_path: Path) -> Path:
    f = tmp_path / "lab.test.yaml"
    f.write_text(COMPOSE, encoding="utf-8")
    return f


def _parent(tmp_path: Path, *, snapshot_ok: bool = True, keys=KEYS,
            tarballs=KEYS) -> Path:
    """A parent lab corpus with one committed day, its managers.json and a docker
    snapshot whose volume records are `keys` and whose tarballs on disk are
    `tarballs` (each a few bytes)."""
    parent = tmp_path / "parent" / "prefix_test.jsonl"
    parent.parent.mkdir(parents=True)
    parent.write_bytes(b'{"event_id": "e1"}\n{"event_id": "e2"}\n')
    transcript = parent.with_suffix(".transcripts.jsonl")
    transcript.write_bytes(b'{"session": 1}\n')
    day = "2026-04-06"
    snap = parent.parent / ".snapshots" / parent.stem / f"day_{day}"
    (snap / "volumes").mkdir(parents=True)
    (snap / "managers.json").write_text("{}", encoding="utf-8")
    services = [{"service": k.split("-")[0], "image": "i",
                 "volumes": [{"volume_name": f"{SOURCE}_{k}",
                              "tarball": f"{SOURCE}_{k}.tar.gz",
                              "mount_point": "/m"}]} for k in keys]
    (snap / "manifest.json").write_text(json.dumps(
        {"name": f"day_{day}", "source_session_id": SOURCE, "services": services}),
        encoding="utf-8")
    for k in tarballs:
        (snap / "volumes" / f"{SOURCE}_{k}.tar.gz").write_bytes(b"\x1f\x8b" + k.encode())
    man = resume_state.new_manifest(audit_path=parent, transcript_path=transcript,
                                    start_date=day, n_days=1, seed=0, session_id=SOURCE)
    resume_state.record_day(man, parent, day=day, audit_bytes=parent.stat().st_size,
                            transcript_bytes=transcript.stat().st_size,
                            snapshot_ok=snapshot_ok, managers_ok=True,
                            snapshot_dir=str(snap) if snapshot_ok else None,
                            managers_path=str(snap / "managers.json"))
    return parent


def _out(tmp_path: Path) -> tuple[Path, Path]:
    out = tmp_path / "branch" / "branch_test.jsonl"
    return out, out.with_suffix(".transcripts.jsonl")


def test_lab_branch_lineage_records_the_snapshot_and_volume_list(tmp_path):
    parent, compose = _parent(tmp_path), _compose(tmp_path)
    out, tr = _out(tmp_path)
    info = _prepare_branch(parent, out, tr, lab_compose_files=[compose])
    snap = parent.parent / ".snapshots" / parent.stem / "day_2026-04-06"
    assert info["snapshot_dir"] == str(snap.resolve())
    assert info["source_session_id"] == SOURCE
    assert [v["key"] for v in info["volumes"]] == sorted(KEYS)
    assert [v["volume_name"] for v in info["volumes"]] == [f"{SOURCE}_{k}" for k in sorted(KEYS)]
    assert all(v["bytes"] > 0 for v in info["volumes"])
    lineage = _branch_lineage(info)
    assert list(lineage) == ["parent", "day", "managers_path", "snapshot_dir",
                             "source_session_id", "volumes"]
    assert lineage["parent"] == str(parent) and lineage["day"] == "2026-04-06"
    # The audit prefix is still copied, exactly as on the dryrun path.
    assert out.read_bytes() == parent.read_bytes()


def test_dryrun_branch_lineage_is_unchanged(tmp_path):
    parent = _parent(tmp_path)
    out, tr = _out(tmp_path)
    info = _prepare_branch(parent, out, tr)
    assert set(info) == {"parent", "day", "managers_path", "next_day"}
    # The manifest record a dryrun branch writes is the pre-C1 one, key for key.
    assert _branch_lineage(info) == {k: info[k] for k in ("parent", "day", "managers_path")}
    assert list(_branch_lineage(info)) == ["parent", "day", "managers_path"]


@pytest.mark.parametrize("keys,tarballs,exc,needle", [
    (KEYS, ("mongo-data", "owncloud-data"), FileNotFoundError, "rocketchat-uploads"),
    (("mongo-data", "owncloud-data"), ("mongo-data", "owncloud-data"), ValueError,
     "rocketchat-uploads"),
])
def test_lab_branch_refuses_an_incomplete_volume_set_before_copying(
        tmp_path, keys, tarballs, exc, needle):
    parent, compose = _parent(tmp_path, keys=keys, tarballs=tarballs), _compose(tmp_path)
    out, tr = _out(tmp_path)
    with pytest.raises(exc, match=needle):
        _prepare_branch(parent, out, tr, lab_compose_files=[compose])
    assert not out.exists() and not tr.exists()          # nothing copied


def test_lab_branch_refuses_a_day_without_a_docker_snapshot(tmp_path):
    parent, compose = _parent(tmp_path, snapshot_ok=False), _compose(tmp_path)
    out, tr = _out(tmp_path)
    with pytest.raises(ValueError, match="no docker snapshot"):
        _prepare_branch(parent, out, tr, lab_compose_files=[compose])
    assert not out.exists()


def test_simulate_agentic_lab_branch_checks_the_volume_set(tmp_path, monkeypatch):
    """The old guard refused every agentic lab branch; now the refusal is the
    volume check, raised before any sandbox or LLM is touched."""
    parent = _parent(tmp_path, tarballs=("mongo-data",))
    monkeypatch.setenv("LAB_COMPOSE", str(_compose(tmp_path)))
    out, _ = _out(tmp_path)
    with pytest.raises(FileNotFoundError, match="owncloud-data"):
        asyncio.run(simulate(mode="agentic", sandbox_mode="lab", n_personas=3, n_days=1,
                             out_path=out, branch_from=parent, llm=object()))
    assert not out.exists()


def _fake_docker(monkeypatch, *, existing: set[str] = frozenset()):
    calls: list[str] = []

    async def fake(cmd, timeout_s=300, *, check=False):
        calls.append(cmd)
        if cmd.startswith("docker volume inspect"):
            name = cmd.split()[-1]
            return ExecResult(stdout="", stderr="", return_code=0 if name in existing else 1)
        return ExecResult(stdout="", stderr="", return_code=0)

    monkeypatch.setattr(snap_mod, "_async_run", fake)
    return calls


def test_restore_into_a_compose_project_names_and_labels_volumes(tmp_path, monkeypatch):
    parent = _parent(tmp_path)
    snap = parent.parent / ".snapshots" / parent.stem / "day_2026-04-06"
    calls = _fake_docker(monkeypatch)
    res = asyncio.run(snap_mod.restore_sandbox(snap, new_session_id="itb-npc-branch01",
                                               compose_project=True))
    assert res["volume_remap"] == {f"{SOURCE}_{k}": f"itb-npc-branch01_{k}" for k in KEYS}
    creates = [c for c in calls if c.startswith("docker volume create")]
    assert len(creates) == 3
    for k in KEYS:
        assert any(c.endswith(f" itb-npc-branch01_{k}")
                   and "com.docker.compose.project=itb-npc-branch01" in c
                   and f"com.docker.compose.volume={k}" in c for c in creates)
    assert sum("tar xzf" in c for c in calls) == 3


def test_restore_into_a_compose_project_refuses_an_existing_volume(tmp_path, monkeypatch):
    parent = _parent(tmp_path)
    snap = parent.parent / ".snapshots" / parent.stem / "day_2026-04-06"
    calls = _fake_docker(monkeypatch, existing={"itb-npc-branch01_mongo-data"})
    with pytest.raises(RuntimeError, match="already exists"):
        asyncio.run(snap_mod.restore_sandbox(snap, new_session_id="itb-npc-branch01",
                                             compose_project=True))
    assert not any("tar xzf" in c and "mongo-data" in c for c in calls)


def test_start_sandbox_restores_before_bring_up_and_records_restored_as(tmp_path,
                                                                        monkeypatch):
    parent, compose = _parent(tmp_path), _compose(tmp_path)
    out, tr = _out(tmp_path)
    info = _prepare_branch(parent, out, tr, lab_compose_files=[compose])
    order: list[str] = []

    async def fake_restore(snapshot_dir, *, new_session_id, compose_project=False):
        assert compose_project and snapshot_dir == info["snapshot_dir"]
        order.append("restore")
        return {"volume_remap": {v["volume_name"]: f"{new_session_id}_{v['key']}"
                                 for v in info["volumes"]}}

    class FakeLab:
        def __init__(self, session_id, compose_files):
            self.session_id = session_id

        async def start(self):
            order.append("start")

    import mole.sandbox.lab as lab_mod
    monkeypatch.setattr(snap_mod, "restore_sandbox", fake_restore)
    monkeypatch.setattr(lab_mod, "LabSandbox", FakeLab)
    monkeypatch.setenv("LAB_COMPOSE", str(compose))

    async def fake_docs(sandbox):
        order.append("read class documents")
        return [{"path": "/shared/x.md", "present": True, "bytes": 3, "sha256": "ab"}]

    monkeypatch.setattr(run_mod, "_class_documents_at_start", fake_docs)
    asyncio.run(run_mod._start_sandbox("lab", session_id="itb-npc-b2", branch_info=info))
    assert order == ["restore", "start", "read class documents"]
    lineage = _branch_lineage(info)
    assert [v["restored_as"] for v in lineage["volumes"]] == [
        f"itb-npc-b2_{k}" for k in sorted(KEYS)]
    assert lineage["class_documents_at_start"][0]["sha256"] == "ab"


def test_class_documents_at_start_hashes_what_the_restored_lab_holds(monkeypatch):
    import hashlib

    import mole.state.owncloud.manager as oc_mod
    from mole.seeders.seed_class_docs import CLASS_DOCUMENTS
    held = {p: c.encode() for p, c in list(CLASS_DOCUMENTS.items())[:5]}   # one missing

    class FakeOC:
        async def setup(self, *, sandbox):
            pass

        async def exists(self, *, path):
            return path in held

        async def read_bytes(self, *, path):
            return held[path]

        async def cleanup(self):
            pass

    monkeypatch.setattr(oc_mod, "OwnCloudManager", FakeOC)
    rows = asyncio.run(run_mod._class_documents_at_start(object()))
    assert [r["path"] for r in rows] == list(CLASS_DOCUMENTS)
    assert [r["present"] for r in rows] == [True] * 5 + [False]
    first = next(iter(held))
    assert rows[0]["sha256"] == hashlib.sha256(held[first]).hexdigest()
