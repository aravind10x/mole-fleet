#!/usr/bin/env python3
"""Brief 13 W0c: decision 5 (the coordinator, STATUS 2026-11-02): the committed Stage 0 to 2 result files that the paper's
§2, §14 and §15 draw on, added to the frozen manifest tagged exploratory ($0).

Files outside work/stage3/ are kept in the amendment record with their project-root path and the fork copy's path; seven are
mirrored now (results/stage0, results/stage1, results/stage2), four reuse the fork's existing results/stage2b/ mirrors, and the
Stage 3 metadata-leak audit (already mirrored) is also appended to `files`. Every figure written from them is traced below,
with the record discrepancies a locate pass found against PLAN.md's wording. Refuses if its amendment exists or a file carries
a credential-like literal."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys

import stage3_paper_w0 as w0

BY = "brief 13 W0c (the writing session, Opus 5.5): decision 5, the earlier stages' result files"
TAG_SRC = "decision 5 (the coordinator, STATUS 2026-11-02): an earlier-stage result file, tagged exploratory for the paper; "
# (project-root path, fork copy path, mirror now, source note, tables drawn on)
FILES = [
    ("work/blog-thesis/checks/mole_r10_gpt53_single_day.json", "results/stage0/blog-thesis-checks/mole_r10_gpt53_single_day.json", True,
     "the Stage 0 rules and the benchmark's matchers scored blind under the benchmark's protocol, GPT-5.3 corpus", ["detectors: D_struct, D_upstream_ceiling, D_union (R10_overall)"]),
    ("work/blog-thesis/checks/mole_r10_kimi_k26_single_day.json", "results/stage0/blog-thesis-checks/mole_r10_kimi_k26_single_day.json", True,
     "as above, Kimi K2.6 corpus", ["detectors: D_struct, D_upstream_ceiling, D_union (R10_overall)"]),
    ("work/stage0/q1-upstream-results/summary.md", "results/stage0/q1-upstream-results/summary.md", True,
     "Stage 0: the benchmark's matchers run blind on its released corpora", ["Headline reading, item 2"]),
    ("work/stage1/f-upstream-row.md", "results/stage1/f-upstream-row.md", True,
     "Stage 1 F1 on the released corpus, with the corrections after review (f1_corrections.py output appended)", ["C3 rho is undefined", "C5 combined pipeline"]),
    ("work/stage2/b0-seed-expansion.md", "results/stage2/b0-seed-expansion.md", True,
     "Stage 2a: seed expansion on the released corpora", ["Gate decision and interpretation, items 1 and 2"]),
    ("work/stage2/b1-haystack.md", "results/stage2/b1-haystack.md", True,
     "Stage 2a: the honest haystack", ["Gate decision and interpretation, item 3"]),
    ("work/stage2/a-track-a-results.md", "results/stage2/a-track-a-results.md", True,
     "Stage 2a: pacing (Track A)", ["1 Primary comparison", "K2 expensive tier vs cheap tier"]),
    ("work/stage2/b-grouping.frozen.md", "results/stage2b/b-grouping.frozen.md", False,
     "Stage 2b: the grouping result by frozen code", ["Labels (C4 oracle)", "Leak audit", "Statements (K3 inputs)"]),
    ("work/stage2/b-grouping.md", "results/stage2b/b-grouping.md", False,
     "Stage 2b: the grouping report with the controller's reading", ["A.1 the verdict and what the cell showed (items on break-glass and density)", "C.2 Density axis"]),
    ("work/stage2/branch-gate-stats.md", "results/stage2b/branch-gate-stats.md", False,
     "Stage 2b: branch gate statistics", ["Pooled over branches A, B, C: 2 Successful protected-group grants"]),
    ("work/stage2/density-anchor.md", "results/stage2b/density-anchor.md", False,
     "Stage 2b: the human density anchor (Apache Jira)", ["Headline"]),
]
STAGE3_FILE = ("s6-released-metadata-leak.md", "the Stage 3 prep audit (S6) of metadata leaks on the released corpora, two features",
               ["Result (primary label rule)", "Notes on the primary table"])
TRACES = [
    ("§2.1 the Stage 0 structural rules, R@10/day on the GPT-5.3 corpus", "0.7253 (D_struct); the benchmark's matchers alone 0.6011 (D_upstream_ceiling); union 0.7339 (D_union)", "work/blog-thesis/checks/mole_r10_gpt53_single_day.json", "detectors", "exploratory"),
    ("§2.1 the same on the Kimi K2.6 corpus", "0.3989 (D_struct); 0.3903 (D_upstream_ceiling); 0.4583 (D_union)", "work/blog-thesis/checks/mole_r10_kimi_k26_single_day.json", "detectors", "exploratory"),
    ("§15.1 the benchmark's quiet matchers", "eight; essentially zero false alarms and 86% to 100% recall; six of the eight depend wholly or mostly on seeded names", "work/stage0/q1-upstream-results/summary.md", "Headline reading, item 2", "exploratory"),
    ("§15.1 F1: the combined pipeline", "81/85 (0.953) at honest 0.050", "work/stage1/f-upstream-row.md", "C5 combined pipeline", "exploratory"),
    ("§15.1 F1: the cross-account layer", "recall_X - recall_P = +0.0000 (exactly zero)", "work/stage1/f-upstream-row.md", "C3 rho is undefined", "exploratory"),
    ("§15.2 seed expansion on the C1 pairs", "0.43 of executed days at w = 1 (53 of 122)", "work/stage2/b0-seed-expansion.md", "Gate decision, item 1", "exploratory"),
    ("§15.2 seed expansion on the C2 pairs", "L = 0 on 0.96 or more of executed days for G1, G2 and G3 in like-for-like scope", "work/stage2/b0-seed-expansion.md", "Gate decision, item 2", "exploratory"),
    ("§15.2 the haystack", "every structural generator (G1, G3, G4, G5) exceeds B = 0.10 at every window on every corpus", "work/stage2/b1-haystack.md", "Gate decision, item 3", "exploratory"),
    ("§15.2 pacing with a reserve against plain top-k", "-0.037 [-0.073, -0.006]", "work/stage2/a-track-a-results.md", "1 Primary comparison", "exploratory"),
    ("§15.2 the expensive tier's full-coverage recall", "0.525 [0.323, 0.713]", "work/stage2/a-track-a-results.md", "K2", "exploratory"),
    ("§15.2 Stage 2b groups that acted on the designed route", "4 of 15 (minimum 10): inconclusive by design", "work/stage2/b-grouping.frozen.md", "Labels; Statements", "exploratory"),
    ("§15.2 protected-group grants through break-glass", "25 of 25", "work/stage2/b-grouping.md", "A.1", "exploratory"),
    ("§2.5 / §15.2 the density axis", "branches 0.35 to 0.49 write co-touch a day against 0.0073 for the 50 most active humans; 'about 50 to 70 times the human anchor'", "work/stage2/b-grouping.md", "A.1 item 7; C.2", "exploratory"),
    ("§2.5 the prefix against the human anchor", "about 77 times below the fork prefix (0.562 any type)", "work/stage2/density-anchor.md", "Headline", "exploratory"),
    ("§15.2 the fork's metadata leak (four features)", "AUROC 0.698 [0.620, 0.777]", "work/stage2/b-grouping.frozen.md", "Leak audit, pooled", "exploratory"),
    ("§15.2 the released single-day corpora (two features)", "gpt53 0.604 [0.573, 0.639] (straddles the gate); kimi 0.652 [0.625, 0.681]; deepseek 0.682 [0.648, 0.717]; qwen 0.552 [0.511, 0.594]", "s6-released-metadata-leak.md", "Result (primary label rule); notes", "exploratory"),
]
DISCREPANCIES = [
    "PLAN.md §2 says 'Upstream MOLE's own matchers, run blind as detectors ... reach R@10/day 0.73': the 0.725 is D_struct, the Stage 0 structural rules; the benchmark's matchers alone are 0.601 (ASSESSMENT §0 says 'your Stage 0 rules', correctly)",
    "'nine of twelve' threats (PLAN §1, STATUS, c-paper-skeleton) is summary-only; the result file's headline names eight quiet matchers",
    "F1's interval [0.653, 1.000] (theory-note evidence table) is the judge alone (72/85), not the 81/85 pipeline",
    "F2's 0.006 of account-days is the Checkpoint 1 review's arithmetic, not a result file's figure; not written",
    "the density ratio: 'about 50 to 70 times' is the branches against the anchor (b-grouping.md); density-anchor.md gives 'about 77 times' for the prefix",
    "PLAN's 'AUROC 0.70' is the fork's four-feature audit; the released corpora's three-of-four result is a separate two-feature run (s6), not directly comparable, with gpt53 straddling the gate",
    "Stage 2b's cost ($401; about $300 avoidable) is summary-only (retrospective, STATUS budget); not written",
]


def sha(p) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


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
        raise SystemExit("refusing: W0c's amendment already exists")
    for path, fork_path, mirror, _, _ in FILES:
        if re.search(r"sk-or-|OPENROUTER_API_KEY=[^$]|AKIA[0-9A-Z]{12}", (w0.ROOT / path).read_text()):
            raise SystemExit(f"refusing: {path} carries a credential-like literal")
        if not mirror and sha(w0.FORK / fork_path) != sha(w0.ROOT / path):
            raise SystemExit(f"refusing: the existing mirror {fork_path} differs")
    if args.check:
        for path, fork_path, mirror, _, _ in FILES:
            print(path, sha(w0.ROOT / path)[:8], fork_path, "mirror now" if mirror else "existing")
        return 0
    entries = []
    for path, fork_path, mirror, note, tables in FILES:
        a, b = w0.ROOT / path, w0.FORK / fork_path
        if mirror:
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(a, b)
        e = {"path": path, "path_root": "project root", "sha256": sha(a), "bytes": a.stat().st_size,
             "fork_copy_path": fork_path, "sha256_fork_copy": sha(b)}
        e["copies_identical"] = e["sha256"] == e["sha256_fork_copy"]
        e.update({"tag": "exploratory", "tag_source": TAG_SRC + note, "added_beyond_brief_list": False,
                  "mirrored_by_this_amendment": mirror, "tables_drawn_on": tables})
        entries.append(e)
    s6 = w0.entry_for(STAGE3_FILE[0], "exploratory", TAG_SRC + STAGE3_FILE[1], STAGE3_FILE[2], False)
    if not all(e["copies_identical"] for e in entries + [s6]):
        raise SystemExit("refusing: a fork copy differs")
    m["amendments"].append({
        "date": "2026-11-02", "by": BY, "added": [s6["path"]], "entries": entries + [s6],
        "traces": [{"figure": f, "value_as_recorded": v, "file": p, "table": t, "tag": g} for f, v, p, t, g in TRACES],
        "record_discrepancies_found": DISCREPANCIES,
        "note": ("additive; no earlier entry changed. Entries outside work/stage3/ stay in this record (project-root path and fork copy "
                 "path); the S6 audit is also appended to files. Sentences whose figures have no result file stay number-free.")})
    m["files"].append(s6)
    m["n_files"] = len(m["files"])
    m["all_copies_identical"] = all(f["copies_identical"] for f in m["files"])
    m["mismatched_or_missing"] = sum(1 for f in m["files"] if not f["copies_identical"])
    out = (json.dumps(m, indent=1, ensure_ascii=False) + "\n").encode()
    w0.MANIFEST.write_bytes(out)
    (w0.FORK_STAGE3 / "b0" / "frozen-tables.json").write_bytes(out)
    print(f"written: n_files {m['n_files']}; amendment entries {len(entries) + 1}; sha256 {hashlib.sha256(out).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
