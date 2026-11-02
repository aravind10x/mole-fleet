#!/usr/bin/env python3
"""Brief 13 W0e: re-hash brief 34's Part J lift record after its v0.1 section was appended (verified by the coordinator,
STATUS 2026-11-02). $0. One new amendment record holds the previous entries and the refreshed ones; the two `files` entries
are replaced, as --rerun-plan does for plan.md. Every other entry is verified first. The .md is checked to be an append (its
first bytes hash to the previous sha256); the .json is re-serialised by its writer, so only its new hash is recorded."""
from __future__ import annotations

import hashlib
import json
import sys

import stage3_paper_w0 as w0

BY = "brief 13 W0e (the writing session, Opus 5.5): the Part J lift record re-hashed after its v0.1 section"
PATHS = ["b3/rater/partj-lift-v0.md", "b3/rater/partj-lift-v0.json"]
TRACES = [
    ("§9.1 the paired difference rho(loudest) - rho(mean)", "pass 1 0.172 [0.054, 0.305]; pass 2 0.187 [0.069, 0.316]", "b3/rater/partj-lift-v0.md", "v0.1: Paired difference", "methods"),
    ("§9.1 the pass-1 lift mean's bootstrap interval", "13.46 [10.81, 16.29] (includes 16); Sonnet 5.5 16.17 [12.27, 20.12]; GLM 5.3 10.29 [6.77, 13.95]", "b3/rater/partj-lift-v0.md", "v0.1: Lift means, pass 1", "methods"),
    ("§9.1 triples above the composition bar, pass 1", "19; lines more than 10 apart 18; every line at or under 60 11; both 1", "b3/rater/partj-lift-v0.md", "v0.1: Candidate triples with composition above 75", "methods"),
]


def main() -> int:
    raw = w0.MANIFEST.read_bytes()
    m = json.loads(raw)
    if (json.dumps(m, indent=1, ensure_ascii=False) + "\n").encode() != raw:
        raise SystemExit("refusing: the manifest does not re-serialise byte-identically")
    if any(a.get("by") == BY for a in m["amendments"]):
        raise SystemExit("refusing: W0e's amendment already exists")
    # plan.md has moved with S3's notes; its refresh is held until the coordinator's STATUS line (--rerun-plan, once)
    held = "b3/plan.md"
    others = {**m, "files": [f for f in m["files"] if f["path"] not in PATHS + [held]]}
    if w0.verify_existing(others):
        raise SystemExit("refusing: another entry no longer matches its hash")
    held_now = w0.sha256(w0.STAGE3 / held)
    previous = [f for f in m["files"] if f["path"] in PATHS]
    if len(previous) != 2:
        raise SystemExit("refusing: the two entries to refresh are not both in files")
    md_prev = next(f for f in previous if f["path"].endswith(".md"))
    md_now = (w0.STAGE3 / md_prev["path"]).read_bytes()
    if hashlib.sha256(md_now[: md_prev["bytes"]]).hexdigest() != md_prev["sha256"]:
        raise SystemExit("refusing: the .md is not an append to its previous version")
    fresh = []
    for f in previous:
        e = w0.entry_for(f["path"], f["tag"], f["tag_source"] + "; re-hashed after the v0.1 section (W0e)", f.get("tables_drawn_on", []) + ["v0.1 section"], False)
        if not e["copies_identical"]:
            raise SystemExit(f"refusing: the fork copy of {f['path']} differs")
        fresh.append(e)
    m["amendments"].append({
        "date": "2026-11-02", "by": BY, "refreshed": [{"previous": p, "refreshed_to": n} for p, n in zip(previous, fresh)],
        "md_prefix_equals_previous": True,
        "held_not_refreshed": {"path": held, "on_disk_sha256": held_now,
                               "reason": "S3's dated notes moved plan.md; the coordinator holds --rerun-plan until its STATUS line records the last move before Stage B"},
        "traces": [{"figure": f, "value_as_recorded": v, "file": p, "table": t, "tag": g} for f, v, p, t, g in TRACES],
        "note": "the two files entries are replaced by their refreshed versions; no other entry changed"})
    m["files"] = [next((n for n in fresh if n["path"] == f["path"]), f) for f in m["files"]]
    m["n_files"] = len(m["files"])
    m["all_copies_identical"] = all(f["copies_identical"] for f in m["files"])
    m["mismatched_or_missing"] = sum(1 for f in m["files"] if not f["copies_identical"])
    out = (json.dumps(m, indent=1, ensure_ascii=False) + "\n").encode()
    w0.MANIFEST.write_bytes(out)
    (w0.FORK_STAGE3 / "b0" / "frozen-tables.json").write_bytes(out)
    print(f"written: n_files {m['n_files']}; refreshed {[e['sha256'][:8] for e in fresh]}; sha256 {hashlib.sha256(out).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
