"""The frozen-tables manifest against the files on disk (brief 13 W0f; the review session's addition, adopted by the coordinator).

An append to a pinned record, or a dated note on the plan, changes the file's hash without any test noticing; this module
hashes every pin the manifest currently holds, in the main checkout and in the fork, and fails on any mismatch."""
from __future__ import annotations

import json

import stage3_paper_w0 as w0
import stage3_paper_w0f as w0f


def _manifest() -> dict:
    return json.loads(w0.MANIFEST.read_bytes())


def test_manifest_reserialises_byte_identically():
    raw = w0.MANIFEST.read_bytes()
    assert (json.dumps(json.loads(raw), indent=1, ensure_ascii=False) + "\n").encode() == raw


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
    m["files"][0] = {**m["files"][0], "sha256": "0" * 64}
    assert f"main {m['files'][0]['path']}" in w0f.drift(m)
