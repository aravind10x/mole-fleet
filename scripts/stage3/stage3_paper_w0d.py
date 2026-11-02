#!/usr/bin/env python3
"""Brief 13 W0d: brief 34's Part J lift record into the frozen manifest, tagged methods (cold-read fix 2; the coordinator's
verification in STATUS 2026-11-02). $0. Additive, by stage3_paper_w0's conventions: one new amendment record; both files have
an identical fork copy and are also appended to `files`. The paper's §9 cites this record, not the review notes W0 added."""
from __future__ import annotations

import hashlib
import json
import sys

import stage3_paper_w0 as w0

BY = "brief 13 W0d (the writing session, Opus 5.5): brief 34's Part J lift record (cold-read fix 2)"
SOURCE = ("brief 34 ($0; script stage3_b3_partj_lift.py aed28cb4): Part J's lift and Spearman recomputed from Part J's files into a "
          "hashed, mirrored record; verified by the coordinator (STATUS 2026-11-02)")
FILES = [("b3/rater/partj-lift-v0.md", ["Minimum lift needed", "Lift = composition - loudest statement", "Spearman, over the candidate triples"]),
         ("b3/rater/partj-lift-v0.json", ["lift", "spearman"])]
TRACES = [
    ("§9.1 the writers' mean lift, pass 1", "13.46 overall (n 89); Sonnet 5.5 16.17 (48); GLM 5.3 10.29 (41); no interval computed", "b3/rater/partj-lift-v0.md", "Lift = composition - loudest statement", "methods"),
    ("§9.1 the minimum lift needed", "16 = (75 + 1) - 60", "b3/rater/partj-lift-v0.md", "Minimum lift needed", "methods"),
    ("§9.1 triples reaching the minimum lift, pass 1", "33 of 89 (Sonnet 5.5 23 of 48, GLM 5.3 10 of 41); necessary, not sufficient", "b3/rater/partj-lift-v0.md", "Lift table", "methods"),
    ("§9.1 Spearman(composition, loudest statement), pass 1", "0.628 [0.469, 0.756] (n 89, 2,000 resamples)", "b3/rater/partj-lift-v0.md", "Spearman, over the candidate triples", "methods"),
]


def main() -> int:
    raw = w0.MANIFEST.read_bytes()
    m = json.loads(raw)
    if (json.dumps(m, indent=1, ensure_ascii=False) + "\n").encode() != raw:
        raise SystemExit("refusing: the manifest does not re-serialise byte-identically")
    if w0.verify_existing(m):
        raise SystemExit("refusing: an existing entry no longer matches its hash")
    if any(a.get("by") == BY for a in m["amendments"]):
        raise SystemExit("refusing: W0d's amendment already exists")
    entries = [w0.entry_for(p, "methods", SOURCE, tb, False) for p, tb in FILES]
    if not all(e["copies_identical"] for e in entries):
        raise SystemExit("refusing: a fork copy differs")
    m["amendments"].append({
        "date": "2026-11-02", "by": BY, "added": [e["path"] for e in entries], "entries": entries,
        "traces": [{"figure": f, "value_as_recorded": v, "file": p, "table": t, "tag": g} for f, v, p, t, g in TRACES],
        "resolves": ["outline v1 pending: Part J's lift and Spearman (cold-read fix 2)"],
        "supersedes_for_citation": ["b3/review/review-partj-2026-10-31.md", "b3/review/partj-diagnostics-2026-10-31.md"],
        "note": "additive; no earlier entry changed; the two review files W0 added stay in the manifest as records and are no longer cited for numbers"})
    m["files"].extend(entries)
    m["n_files"] = len(m["files"])
    m["all_copies_identical"] = all(f["copies_identical"] for f in m["files"])
    m["mismatched_or_missing"] = sum(1 for f in m["files"] if not f["copies_identical"])
    out = (json.dumps(m, indent=1, ensure_ascii=False) + "\n").encode()
    w0.MANIFEST.write_bytes(out)
    (w0.FORK_STAGE3 / "b0" / "frozen-tables.json").write_bytes(out)
    print(f"written: n_files {m['n_files']}; sha256 {hashlib.sha256(out).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
