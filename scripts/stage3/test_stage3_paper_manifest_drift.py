"""The frozen-tables manifest against the files on disk (brief 13 W0f; the review session's addition, adopted by the coordinator).

An append to a pinned record, or a dated note on the plan, changes the file's hash without any test noticing; this module
hashes every pin the manifest currently holds, in the main checkout and in the fork, and fails on any mismatch."""
from __future__ import annotations

import hashlib
import json

import pytest

import stage3_paper_w0 as w0
import stage3_paper_w0f as w0f


def _manifest() -> dict:
    return json.loads(w0.MANIFEST.read_bytes())


def test_manifest_reserialises_byte_identically():
    raw = w0.MANIFEST.read_bytes()
    assert (json.dumps(json.loads(raw), indent=1, ensure_ascii=False) + "\n").encode() == raw


@pytest.mark.skipif(w0.IN_FORK, reason="the project checkout is not part of the repository")
def test_fork_manifest_equals_main():
    assert (w0.FORK_STAGE3 / "b0" / "frozen-tables.json").read_bytes() == w0.MANIFEST.read_bytes()


def test_every_pin_matches_its_file_on_disk():
    assert w0f.drift(_manifest()) == []


def test_pins_cover_files_and_amendment_only_records():
    m = _manifest()
    pins = {p["path"] for p in w0f.current_pins(m)}
    assert {f["path"] for f in m["files"]} <= pins
    assert "work/lessons.md" in pins and "briefs/22-b4-conditional-2026-10-31.md" in pins
    assert m["n_files"] == len(m["files"])


def test_drift_detects_a_changed_pin():
    m = _manifest()
    if w0.IN_FORK:
        i = next(i for i, f in enumerate(m["files"]) if f["sha256_fork_copy"])
        m["files"][i] = {**m["files"][i], "sha256_fork_copy": "0" * 64}
        assert f"fork {m['files'][i]['path']}" in w0f.drift(m)
    else:
        m["files"][0] = {**m["files"][0], "sha256": "0" * 64}
        assert f"main {m['files'][0]['path']}" in w0f.drift(m)


# --- line REPO, 2026-11-16: relocation entries, unreleased pins, fork mode (synthetic manifests) ---

def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@pytest.fixture
def layout(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    stage3, fork_stage3 = root / "work" / "stage3", root / "work" / "mole-fork" / "results" / "stage3"
    for d in (stage3 / "x", fork_stage3 / "x", root / "work" / "elsewhere"):
        d.mkdir(parents=True)
    monkeypatch.setattr(w0, "ROOT", root)
    monkeypatch.setattr(w0, "STAGE3", stage3)
    monkeypatch.setattr(w0, "FORK", root / "work" / "mole-fork")
    monkeypatch.setattr(w0, "FORK_STAGE3", fork_stage3)
    monkeypatch.setattr(w0, "IN_FORK", False)
    return root, stage3, fork_stage3


def _m(files, entries=()):
    return {"files": files, "amendments": [{"entries": list(entries)}]}


def test_relocation_entry_moves_the_main_pin(layout):
    root, stage3, fork_stage3 = layout
    body = b"held record"
    (root / "work" / "elsewhere" / "a.md").write_bytes(body)  # moved out of work/stage3/x/
    files = [{"path": "x/a.md", "sha256": _sha(body), "sha256_fork_copy": None}]
    assert w0f.drift(_m(files)) == ["main x/a.md"]
    reloc = {"path": "x/a.md", "relocated_to": "work/elsewhere/a.md", "sha256": _sha(body)}
    assert w0f.drift(_m(files, [reloc])) == []
    assert files[0]["sha256"] == _sha(body)  # the files entry is untouched


def test_pin_without_fork_copy_is_not_checked_in_the_fork(layout):
    root, stage3, fork_stage3 = layout
    (stage3 / "x" / "b.md").write_bytes(b"b")
    files = [{"path": "x/b.md", "sha256": _sha(b"b"), "sha256_fork_copy": None}]
    assert w0f.drift(_m(files)) == []


def test_fork_mode_checks_only_fork_copies(layout, monkeypatch):
    root, stage3, fork_stage3 = layout
    (fork_stage3 / "x" / "c.md").write_bytes(b"c")
    files = [{"path": "x/c.md", "sha256": "f" * 64, "sha256_fork_copy": _sha(b"c")}]  # no project copy at all
    monkeypatch.setattr(w0, "IN_FORK", True)
    assert w0f.drift(_m(files)) == []
    (fork_stage3 / "x" / "c.md").write_bytes(b"changed")
    assert w0f.drift(_m(files)) == ["fork x/c.md"]


def test_fork_copy_edit_entry_repins_only_the_fork_copy(layout):
    # line REPO batch 4: a public copy edited for hygiene (e.g. a name replaced) is re-pinned by an appended entry;
    # the project copy's pin and the files entry stay as they are.
    root, stage3, fork_stage3 = layout
    (stage3 / "x" / "d.md").write_bytes(b"by Someone")
    (fork_stage3 / "x" / "d.md").write_bytes(b"by the author")
    files = [{"path": "x/d.md", "sha256": _sha(b"by Someone"), "sha256_fork_copy": _sha(b"by Someone")}]
    assert w0f.drift(_m(files)) == ["fork x/d.md"]
    edit = {"path": "x/d.md", "fork_copy_edit": "name replaced", "sha256_fork_copy": _sha(b"by the author")}
    assert w0f.drift(_m(files, [edit])) == []
    assert files[0]["sha256_fork_copy"] == _sha(b"by Someone")  # the files entry is untouched
