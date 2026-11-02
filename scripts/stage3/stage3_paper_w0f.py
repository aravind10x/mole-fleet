#!/usr/bin/env python3
"""Brief 13 W0f: the plan.md re-run and the re-pins of drifted cited records, plus the manifest's current pins for the drift
test (the coordinator, 2026-11-02: plan.md at 59a98c15 will not move again before the paper). $0.

current_pins(m) is every entry the manifest pins now: each `files` entry, and each amendment-only entry at its latest pin
(a later amendment's entry for the same path supersedes an earlier one). test_stage3_paper_manifest_drift.py hashes them all.
W0f refreshes plan.md's `files` entry (the previous entry kept, its bytes checked to be a prefix of the new file) and re-pins
brief 22 (its dated note of 2026-11-02 states B4's gates) and work/lessons.md, which had moved since W0."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import stage3_paper_w0 as w0

BY = "brief 13 W0f (the writing session, Opus 5.5): plan.md re-run and the drifted cited records re-pinned"
PLAN = "b3/plan.md"
REPIN = {
    "briefs/22-b4-conditional-2026-10-31.md": ("results/stage3/b4/brief-22-b4-conditional.md", "design",
        "brief 22 (B4, conditional design) with its dated note of 2026-11-02 stating the gates from B3's round 1; the B4 lines of §10 and §11.2 state the gates as that note does; the 0.65 bar is brief 22's G1"),
    "work/lessons.md": (None, "record", "lessons L1 onward: cited for method (L17 to L24), never for a number; re-pinned after later lessons were appended"),
}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def current_pins(m: dict) -> list[dict]:
    """Every pin the manifest holds now: {path, main, sha256, fork, sha256_fork_copy}."""
    in_files = {f["path"] for f in m["files"]}
    latest: dict[str, dict] = {}
    for a in m["amendments"]:
        for e in a.get("entries", []):
            if e["path"] not in in_files:
                latest[e["path"]] = e
    pins = []
    for f in m["files"]:
        pins.append({"path": f["path"], "main": w0.STAGE3 / f["path"], "sha256": f["sha256"],
                     "fork": w0.FORK_STAGE3 / f["path"], "sha256_fork_copy": f["sha256_fork_copy"]})
    for p, e in latest.items():
        root = e.get("path_root") == "project root"
        main = (w0.ROOT / p) if root else (w0.STAGE3 / p)
        fork_path = e.get("fork_copy_path")
        fork = (w0.FORK / fork_path) if fork_path else (None if root else w0.FORK_STAGE3 / p)
        pins.append({"path": p, "main": main, "sha256": e["sha256"],
                     "fork": fork if (fork and e.get("sha256_fork_copy")) else None, "sha256_fork_copy": e.get("sha256_fork_copy")})
    return pins


def drift(m: dict) -> list[str]:
    bad = []
    for p in current_pins(m):
        if not p["main"].exists() or _sha(p["main"]) != p["sha256"]:
            bad.append(f"main {p['path']}")
        if p["fork"] is not None and (not p["fork"].exists() or _sha(p["fork"]) != p["sha256_fork_copy"]):
            bad.append(f"fork {p['path']}")
    return bad


def main() -> int:
    raw = w0.MANIFEST.read_bytes()
    m = json.loads(raw)
    if (json.dumps(m, indent=1, ensure_ascii=False) + "\n").encode() != raw:
        raise SystemExit("refusing: the manifest does not re-serialise byte-identically")
    if any(a.get("by") == BY for a in m["amendments"]):
        raise SystemExit("refusing: W0f's amendment already exists")
    expected = {f"main {PLAN}", f"fork {PLAN}"} | {f"main {p}" for p in REPIN} | {f"fork {p}" for p, (fk, _, _) in REPIN.items() if fk}
    bad = set(drift(m))
    if not bad <= expected:
        raise SystemExit(f"refusing: unexpected drift {sorted(bad - expected)}")
    prev = next(f for f in m["files"] if f["path"] == PLAN)
    now = (w0.STAGE3 / PLAN).read_bytes()
    prefix_ok = hashlib.sha256(now[: prev["bytes"]]).hexdigest() == prev["sha256"]
    if not prefix_ok:
        raise SystemExit("refusing: plan.md is not an append to its previous pinned version")
    new_plan = {**prev, "sha256": _sha(w0.STAGE3 / PLAN), "bytes": len(now), "sha256_fork_copy": _sha(w0.FORK_STAGE3 / PLAN)}
    new_plan["copies_identical"] = new_plan["sha256"] == new_plan["sha256_fork_copy"]
    new_plan["status_recorded_sha256"] = new_plan["sha256"]
    new_plan["status_recorded_bytes"] = len(now)
    new_plan["prefix_equals_status_version"] = True
    new_plan["note"] = ("re-run by W0f on the coordinator's word that plan.md (fork 1fafa57) will not move again before the paper; "
                        "STATUS records 59a98c15; the previous pin's bytes are a prefix of this one")
    if not new_plan["copies_identical"]:
        raise SystemExit("refusing: plan.md's fork copy differs")
    repins = []
    for p, (fk, tag, src) in REPIN.items():
        a = w0.ROOT / p
        e = {"path": p, "path_root": "project root", "sha256": _sha(a), "bytes": a.stat().st_size, "fork_copy_path": fk,
             "sha256_fork_copy": _sha(w0.FORK / fk) if fk else None}
        e["copies_identical"] = (e["sha256"] == e["sha256_fork_copy"]) if fk else None
        e.update({"tag": tag, "tag_source": src, "cited_only": True, "added_beyond_brief_list": False})
        if fk and not e["copies_identical"]:
            raise SystemExit(f"refusing: the fork copy of {p} differs")
        repins.append(e)
    m["amendments"].append({
        "date": "2026-11-02", "by": BY,
        "refreshed": [{"previous": prev, "refreshed_to": new_plan["sha256"]}],
        "entries": repins,
        "note": ("plan.md's files entry refreshed (prefix checked); brief 22 and work/lessons.md re-pinned as cited records; "
                 "test_stage3_paper_manifest_drift.py hashes every current pin from here on")})
    m["files"] = [new_plan if f["path"] == PLAN else f for f in m["files"]]
    m["n_files"] = len(m["files"])
    m["all_copies_identical"] = all(f["copies_identical"] for f in m["files"])
    m["mismatched_or_missing"] = sum(1 for f in m["files"] if not f["copies_identical"])
    left = drift(m)
    if left:
        raise SystemExit(f"refusing: drift remains after the refresh {left}")
    out = (json.dumps(m, indent=1, ensure_ascii=False) + "\n").encode()
    w0.MANIFEST.write_bytes(out)
    (w0.FORK_STAGE3 / "b0" / "frozen-tables.json").write_bytes(out)
    print(f"written: n_files {m['n_files']}; pins {len(current_pins(m))}; plan.md {new_plan['sha256'][:8]}; sha256 {hashlib.sha256(out).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
