#!/usr/bin/env python3
"""Brief 13 W0b: the coordinator's decisions on the outline cold read (STATUS 2026-11-02), added to the frozen manifest ($0).

Fix 3: the generator erratum and the eleven launch-line files, tagged methods; the launch lines are mirrored to the fork's
results/stage3/prefix/ in the same commit. Decision 5 (part): brief 19's B4 sizing record, tagged design, for brief 22 §0's
chance figure. Additive, by stage3_paper_w0's conventions: one new amendment record; entries with an identical fork copy are
also appended to `files`. Refuses if its amendment exists, or if a launch line carries a literal key."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys

import stage3_paper_w0 as w0

BY = "brief 13 W0b (the writing session, Opus 5.5): the coordinator's decisions on cold-read fix 3 and decision 5 (chance figure)"
LAUNCH = ["launch-line.txt", "launch-line-v1b.txt", "launch-line-v2.txt", "launch-line-v2b.txt", "launch-line-v2c.txt",
          "launch-line-v3.txt", "launch-line-v3b.txt", "launch-line-v3c.txt", "launch-line-v3r.txt", "launch-line-v3rb.txt",
          "launch-line-v3rc.txt"]
LAUNCH_SOURCE = ("the world's launch records: one OPENROUTER_MODEL line each, moonshotai/kimi-k2.6; added by the coordinator's decision "
                 "on cold-read fix 3 (STATUS 2026-11-02), with the erratum; the API key is a variable reference, never a literal")
SOURCES = [("q1q2-synthetic/erratum-generator-2026-11-02.md", "methods",
            "the coordinator's erratum against 07p's disclosure sentence (the generator is Kimi K2.6, not Kimi K3); 07p's frozen files unchanged",
            ["What the launch records say (table)", "What changes"])]
SOURCES += [(f"prefix/{f}", "methods", LAUNCH_SOURCE, ["OPENROUTER_MODEL"]) for f in LAUNCH]
SOURCES += [("b4/power-simulation-b4.md", "design",
             "brief 19 (B4 sizing part B), $0 simulation; added for brief 22 §0's chance figure by the coordinator's decision (STATUS 2026-11-02)",
             ["C-rule (beside every number)", "summary C-rule line"])]
TRACES = [
    ("§3.1 the generator's model id", "moonshotai/kimi-k2.6", "prefix/launch-line-v2c.txt", "OPENROUTER_MODEL (the T1 and B3 world)", "methods"),
    ("§3.2 the generator for B4's world", "moonshotai/kimi-k2.6", "prefix/launch-line-v3rc.txt", "OPENROUTER_MODEL", "methods"),
    ("§3.1 the erratum against 07p's disclosure", "Kimi K2.6, not Kimi K3", "q1q2-synthetic/erratum-generator-2026-11-02.md", "What the launch records say", "methods"),
    ("§11.1 chance for a two-account change beside the cross-account rule", "1 − 0.6² = 0.64", "b4/power-simulation-b4.md", "C-rule (beside every number)", "design"),
]


def no_literal_key(path) -> bool:
    t = path.read_text()
    return all(v.startswith("${") for v in re.findall(r"OPENROUTER_API_KEY=[\"']?(\S+)", t)) and not re.search(r"sk-or-", t)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    raw = w0.MANIFEST.read_bytes()
    m = json.loads(raw)
    if (json.dumps(m, indent=1, ensure_ascii=False) + "\n").encode() != raw:
        raise SystemExit("refusing: the manifest does not re-serialise byte-identically")
    if w0.verify_existing(m):
        raise SystemExit("refusing: an existing entry no longer matches its hash")
    if any(a.get("by") == BY for a in m["amendments"]):
        raise SystemExit("refusing: W0b's amendment already exists")
    for f in LAUNCH:
        if not no_literal_key(w0.STAGE3 / "prefix" / f):
            raise SystemExit(f"refusing: {f} may carry a literal key")
    if not args.check:
        (w0.FORK_STAGE3 / "prefix").mkdir(parents=True, exist_ok=True)
        for f in LAUNCH:
            shutil.copyfile(w0.STAGE3 / "prefix" / f, w0.FORK_STAGE3 / "prefix" / f)
    entries = [w0.entry_for(p, t, s, tb, False) for p, t, s, tb in SOURCES]
    to_files = [e for e in entries if e["copies_identical"]]
    if args.check:
        print(json.dumps([(e["path"], e["sha256"][:8], (e["sha256_fork_copy"] or "none")[:8], e["tag"]) for e in entries], indent=1))
        return 0
    if len(to_files) != len(entries):
        raise SystemExit(f"refusing: fork copies differ: {[e['path'] for e in entries if not e['copies_identical']]}")
    m["amendments"].append({
        "date": "2026-11-02", "by": BY, "added": [e["path"] for e in to_files], "entries": entries,
        "traces": [{"figure": f, "value_as_recorded": v, "file": p, "table": t, "tag": g} for f, v, p, t, g in TRACES],
        "resolves": ["W0 not_traced: brief 22 §0's chance figure (now traced to b4/power-simulation-b4.md, design)",
                     "outline v1 pending: the generator's model id (cold-read fix 3)"],
        "note": "additive; no earlier entry changed; launch lines mirrored to the fork's results/stage3/prefix/ in the same commit"})
    m["files"].extend(to_files)
    m["n_files"] = len(m["files"])
    m["all_copies_identical"] = all(f["copies_identical"] for f in m["files"])
    m["mismatched_or_missing"] = sum(1 for f in m["files"] if not f["copies_identical"])
    out = (json.dumps(m, indent=1, ensure_ascii=False) + "\n").encode()
    w0.MANIFEST.write_bytes(out)
    (w0.FORK_STAGE3 / "b0" / "frozen-tables.json").write_bytes(out)
    print(f"written: n_files {m['n_files']}; all_copies_identical {m['all_copies_identical']}; sha256 {hashlib.sha256(out).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
