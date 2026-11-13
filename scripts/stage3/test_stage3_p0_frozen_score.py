"""Offline tests for stage3_p0_frozen_score (line P0, Part 2): arm B's flags on the frozen states and their joins.
Synthetic packets, scores and flags only; no real packet is read."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_p0_frozen_score as fs  # noqa: E402

HDR = "intro\n\nDocument: owncloud:/d.md\nFrom: {frm}\nTo: {to}\nUnified diff ({n} chars):\n{body}"


def pk(frm, to, body):
    return HDR.format(frm=frm, to=to, n=len(body), body=body)


def test_header_fields_and_body():
    p = pk("end of 2026-04-06", "2026-04-07T10:00:00Z", "--- a\n+++ b\n+x\n")
    assert fs.packet_fields(p) == {"from": "end of 2026-04-06", "to": "2026-04-07T10:00:00Z", "body": "--- a\n+++ b\n+x\n"}


def test_compare_packets_counts_only():
    frozen = {"k1": pk("end of d1", "T2", "+a\n"), "k2": pk("end of d1", "T5", "+b\n"), "k3": pk("start", "T9", "+c\n")}
    recorded = {"k1": pk("end of d1", "T2", "+a\n"), "k2": pk("end of d1", "T4", "+b\n"), "k3": pk("start", "T7", "+z\n")}
    c = fs.compare_packets(frozen, recorded)
    assert c == {"n": 3, "identical": 1, "to_differs": 2, "from_differs": 0, "body_differs": 1, "only_to_timestamp_differs": 1,
                 "equal_apart_from_to_line": 2, "missing_recorded": 0}
    c2 = fs.compare_packets(frozen, {"k1": recorded["k1"]})
    assert c2["n"] == 3 and c2["missing_recorded"] == 2 and c2["identical"] == 1


def test_equal_apart_from_the_to_line_is_strict_elsewhere():
    a = pk("end of d1", "T2", "+a\n")
    assert fs.equal_apart_from_to_line(a, pk("end of d1", "T9", "+a\n"))
    assert not fs.equal_apart_from_to_line(a, pk("end of d0", "T2", "+a\n"))
    assert not fs.equal_apart_from_to_line(a, "other intro" + a[5:])


def test_size_range_check():
    r = fs.size_range_check({"k1": 50, "k2": 120}, [40, 60, 200])
    assert r == {"n": 2, "n_inside": 2, "null_min": 40, "null_max": 200, "below": 0, "above": 0, "pass": True}
    r2 = fs.size_range_check({"k1": 30, "k2": 120, "k3": 250}, [40, 200])
    assert r2["n_inside"] == 1 and r2["below"] == 1 and r2["above"] == 1 and r2["pass"] is False


def test_agreement_and_gate_E():
    a = {"k1": True, "k2": False, "k3": True, "k4": None}
    b = {"k1": True, "k2": True, "k3": True, "k4": False}
    ag = fs.agreement(["k1", "k2", "k3", "k4"], a, b)
    assert ag == {"n": 3, "agree": 2, "share": pytest.approx(2 / 3), "unscored": 1}
    g = fs.gate_E(n_identical=47, equal_apart_from_to_line=47, agreement_share=0.93, size_pass=True)
    assert g["check1"]["pass"] and g["check2"]["pass"] and g["name_S"] is True
    assert fs.gate_E(n_identical=47, equal_apart_from_to_line=46, agreement_share=1.0, size_pass=True)["name_S"] is False
    assert fs.gate_E(n_identical=47, equal_apart_from_to_line=47, agreement_share=0.89, size_pass=True)["name_S"] is False
    assert fs.gate_E(n_identical=47, equal_apart_from_to_line=47, agreement_share=0.95, size_pass=False)["name_S"] is False


def test_load_packets_checks_the_file_hash(tmp_path):
    p = tmp_path / "p.jsonl"
    p.write_text(json.dumps({"payload_id": "P1", "key": "t1v3:M1:lone", "packet": "X"}) + "\n")
    good = hashlib.sha256(p.read_bytes()).hexdigest()
    assert fs.load_packets(p, good) == [{"payload_id": "P1", "key": "t1v3:M1:lone", "packet": "X"}]
    with pytest.raises(SystemExit):
        fs.load_packets(p, "0" * 64)


def test_flag_changes_and_the_paired_table():
    gov = {"P1": ("k1", "routine", True), "P2": ("k2", "middle", False), "P3": ("k3", "alarming", True), "P4": ("k4", "routine", True)}
    frozen = {"k1": True, "k2": False, "k3": True, "k4": False}
    reader = {"k1": False, "k2": False, "k3": True, "k4": False}
    ch = fs.flag_changes(gov, frozen, reader)
    assert ch == {"n": 4, "changed": 1, "flagged_on_frozen_only": 1, "flagged_on_reader_only": 0}
    t = fs.paired_missed(gov, frozen, reader)
    assert t["RM"]["identical"] == {"both": 1, "frozen_only": 0, "reader_only": 1, "neither": 0}
    assert t["RM"]["not_identical"] == {"both": 1, "frozen_only": 0, "reader_only": 0, "neither": 0}
    assert t["AL"]["identical"] == {"both": 0, "frozen_only": 0, "reader_only": 0, "neither": 1}
