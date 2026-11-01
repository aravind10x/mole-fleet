#!/usr/bin/env python3
"""Brief 13 A5 W0: extend the frozen-tables manifest with the records the paper now draws on ($0; counts and hashes only).

Additive: no earlier entry changes. Every new record gets an entry with the manifest's fields (path, sha256, bytes, the fork
copy's sha256, tag, tag source) under one new `amendments` record; records that are number sources under work/stage3/ with a
byte-identical fork copy are also appended to `files`, as earlier amendments did. Records cited for method only (briefs 15, 22,
24 and work/lessons.md) and records with no fork mirror stay in the amendment record only. The figures A5 names are traced to
their file and the table inside it; a figure that cannot be traced is listed as not traced and is not written.

Modes: default writes the amendment (refuses if one by this brief exists); --check prints the plan without writing;
--rerun-plan refreshes only the plan.md entry when STATUS records S3's dated note (A5.1 W0)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE3 = ROOT / "work" / "stage3"
FORK = ROOT / "work" / "mole-fork"
FORK_STAGE3 = FORK / "results" / "stage3"
MANIFEST = STAGE3 / "b0" / "frozen-tables.json"
BY = "brief 13 A5 W0 (the writing session, Opus 5.5)"
PLAN_STATUS_SHA = "58b0c1211bfd1e2b10c329f592f25dba96fc3036e9fbbb2d4a49def2457f6f13"
PLAN_STATUS_FORK_COMMIT = "58b0c24"

# (path under work/stage3, tag, tag source, tables drawn on, beyond A5's list)
NUMBER_SOURCES = [
    ("legibility/instrument-v0.md", "instrument",
     "brief 23 v2.2: the comprehension instrument's validation sentences 1 to 4b, pre-registered; verdict not valid; every figure an instrument look, never an outcome (brief 13 A5.3)",
     ["header verdict", "Validation sentences per reader family (sentences 1 to 4b)"], False),
    ("legibility/instrument-v0.json", "instrument", "as instrument-v0.md (the numbers behind the report)", ["sentences", "families"], False),
    ("legibility/instrument-v0-reading.md", "instrument",
     "brief 23: the blue reading written after the run, and the coordinator's dated note of 2026-11-01 (the cause is the validation items)",
     ["verdict table", "What the run shows 1 to 6", "dated note 2026-11-01"], False),
    ("b3/comprehension/stratum-v0.md", "instrument",
     "brief 25 (brief 15 A6.14.1, A6.14.2): the comprehension-quiet stratum under C1's rule, committed before any reader call",
     ["first line (28 of 78)", "C1's expectation", "Nulls", "Positive control", "Reliability"], False),
    ("b3/comprehension/stratum-v0.json", "instrument", "as stratum-v0.md (per-item membership by opaque id; aggregates only are read)", ["summary"], False),
    ("b3/comprehension/stratum-plan.json", "instrument", "brief 25 C1: the stratum rule and its expected error rates, committed before any reader call", ["the chosen rule"], False),
    ("b3/comprehension/t1-join-v0.md", "exploratory",
     "brief 15 A6.14.5 (exploratory) and A6.17.7 (the one permitted sentence)", ["Rater line score: two-pass mean"], False),
    ("b3/comprehension/t1-join-v0.json", "exploratory", "as t1-join-v0.md", ["two_pass_mean"], False),
    ("b3/rater/certification-b3.md", "methods",
     "brief 17 Part J (brief 15 Part R, A5.7): the rater's certification of round 1, aggregates and counts only",
     ["J1 bars", "J2 certification by writer (pooled; of which both passes)", "Pass agreement per scale", "Reference drift"], False),
    ("b3/rater/certification-b3.json", "methods", "as certification-b3.md (the rater's aggregates; per-item fields are not read)", ["bars", "pooled", "by_writer", "agreement_and_drift"], False),
    ("b3/inserter-dry-run-v0.md", "instrument",
     "brief 26 (brief 15 A6.17.10 (c), A6.17.11): the edit-application check on every B3 item, $0; the rendering artefact confirmed",
     ["first line (drop list 8; reverse case 0)", "Aggregates", "Per line at the Part S state"], False),
    ("b3/inserter-dry-run-v0.json", "instrument", "as inserter-dry-run-v0.md", ["summaries"], False),
    ("b0/b0-results.md", "exploratory",
     "brief 11 (B0) prespec Z0: Z2 to Z5 exploratory; the R checks are reproductions; each table carries its own label inside",
     ["First lines", "Z2 (i) flag against visibility and volume", "Z2 strata and pools", "Z3", "Z4 the honest-null taxonomy", "Z5"], False),
    ("b0/b0-results.json", "exploratory", "as b0-results.md", ["z2", "z3", "z4", "z5"], False),
    ("b3/power-simulation-v3b.md", "design",
     "brief 20 Part 2 (brief 15 A6.13): $0 simulation; operating characteristics, never outcomes", ["Summary (adopted layout T2+S2; one latent margin)"], False),
    ("b3/power-simulation-v3b.json", "design", "as power-simulation-v3b.md", ["summary"], False),
    ("b3/power-simulation-v3c.md", "design",
     "brief 20 Part 3 (brief 15 A6.14.3, A6.18): $0 simulation; the switch and the carrier", ["first line", "populations table", "2 and 3"], False),
    ("b3/power-simulation-v3c.json", "design", "as power-simulation-v3c.md", ["summary"], False),
    ("b3/s1-populations-v0.json", "pre-registration", "brief 28 S1: B3's populations by hash, committed with plan.md", ["populations"], False),
    ("b3/plan.md", "pre-registration",
     "brief 28 S1 with its dated notes (brief 15 A6.18 (p), A6.24 (2), brief 33 A1b); hashed as on disk; see status_recorded_sha256",
     ["1 Populations", "5 The readings and the cascade", "6 Every outcome sentence", "7 The disclosures", "8 Round 2"], False),
    ("pilot/forensics/forensics.md", "exploratory",
     "brief 16 part A spec (sha256 7c9bf41b, fork e541f1c): 'counts only; exploratory'; A5 lists brief 16 as sensitivity, and the file's own plan labels part A exploratory, so the manifest takes the plan's label (disclosed)",
     ["A1 Fact losses", "A2 How long each composition lasted", "A4 The carrier write"], False),
    ("pilot/forensics/rc-sensitivity.md", "sensitivity",
     "brief 16 part B: R-C sensitivities (exploratory), the mapped cut points committed by hash before any rating",
     ["same-session sensitivity table (brief 09 band, moved)", "touched-lines rendering"], False),
    ("b3/review/partj-diagnostics-2026-10-31.md", "methods",
     "the review session's aggregate Part J diagnostics (run on key-b3.json 04b1ca30 and the four pass files), cited by review-partj; added beyond A5's list because it holds A4.5's Spearman (a disclosed deviation)",
     ["spearman comp vs top line"], True),
    ("b3/review/review-partj-2026-10-31.md", "methods",
     "the review session's Part J review, reconciled with the independent Fable read and verified by the coordinator (STATUS 2026-10-31); added beyond A5's list because it holds A4.5's mean lift and the 16 needed (a disclosed deviation)",
     ["2 Fable's read: Mechanism", "3 Reconciliation: Verified from the files"], True),
]

# Cited for method or record, never for a number: (path from the project root, fork copy under the fork root, tag, source)
CITED_ONLY = [
    ("briefs/15-b3-distributed-visibility-2026-10-28.md", "results/stage3/b3/brief-15-b3-distributed-visibility.md", "design",
     "brief 15 (B3) with amendments A5 to A6.26: cited for method and verbatim quotations (A6.17.7, A6.18 (l)), never as a number source"),
    ("briefs/22-b4-conditional-2026-10-31.md", "results/stage3/b4/brief-22-b4-conditional.md", "design",
     "brief 22 (B4, conditional design): cited for the gate G1 to G3 and the paths; its section-0 figures are traced to their result files below"),
    ("briefs/24-elicitation-study-design-2026-10-31.md", "results/stage3/elicitation/brief-24-elicitation-study-design.md", "design",
     "brief 24 (the elicitation study design): cited for its purpose line ('with these writers'), never for a number"),
    ("work/lessons.md", None, "record", "lessons L1 to L25: cited for method (L17 to L25), never for a number"),
]

# The figures A5 names (A1, A3, A4.2, A4.4, A4.5, A5.3, A5.4, A5.5), traced to file and table. Values as the record prints them.
TRACES = [
    ("A1 (1) the mechanism join: cells where the author's maximum rater score predicts the per-author flag", "11 of 12", "b0/b0-results.md", "First lines, item 2 (Z2)", "exploratory"),
    ("A1 (1) volume beyond visibility", "ΔAUC 0.005 to 0.067", "b0/b0-results.md", "First lines, item 2; Z2 (i) column ΔAUC_vol", "exploratory"),
    ("A1 (2) 07o's exclusion of v1's effect under Sonnet", "DiD 0.083 [-0.125, 0.292]; Δ_v1 0.000 [-0.167, 0.167]", "t1-replant/replant-results.md", "first line (outcome under Sonnet 5)", "confirmatory"),
    ("A1 (2) no reading at headroom: Sonnet re-plant margin", "0.080 against 0.3", "b0/b0-results.md", "Z2 strata (Sonnet P_author, re-plant)", "exploratory"),
    ("A1 (2) the one stratum at headroom (Opus 4.8, re-plant)", "DiD 0.250 [0.000, 0.500], inconclusive", "b0/b0-results.md", "Z2 strata (Opus 4.8 P_author, re-plant)", "exploratory"),
    ("W1 item 4: the re-plant's v1 point under Sonnet, lone", "0.500 (12/24) [0.291, 0.709]", "t1-replant/replant-results.md", "Sonnet 5 table, P_author lone recall", "confirmatory"),
    ("W1 item 4: the re-plant's v1 point under Sonnet, k = 2", "0.500 (12/24) [0.291, 0.709]", "t1-replant/replant-results.md", "Sonnet 5 table, P_author k2 recall", "confirmatory"),
    ("W1 item 4: the re-plant's v1 point under Sonnet, composed", "0.734 (47/64) [0.609, 0.837]", "t1-replant/replant-results.md", "Sonnet 5 table, O_diff nominal composed share", "confirmatory"),
    ("W1 item 4: the old inserter's v1 point (hollow)", "Δ 0.458; lone units of four or more changes 14/17 against 3/7 at three", "t1-replant/replant-results.md", "DiD line (v1 old inserter Δ); P_author by n_changes stratum, old inserter rows", "confirmatory (superseded for Δ)"),
    ("A4.2 the edit-count rule's recall on the control (sham) arm by arm", "lone 0.708 (17/24) [0.489, 0.874]; k2 0.458 (11/24) [0.256, 0.672]; k3 0.250 (4/16) [0.073, 0.524]", "t1-replant/replant-results.md", "Volume rule (judge-free; edit count at 5 percent honest cost)", "exploratory (not a pre-registered contrast; A4.2)"),
    ("A4.2 the edit-count rule's honest cost", "t 3, honest realised 0.045 (4/89)", "t1-replant/replant-results.md", "Volume rule", "exploratory"),
    ("A4.4 shared item lines found by name over the first two days", "16 to 12 to 7", "b4r/b4r-results.md", "The world: honest behaviour disclosed (C.4 and the day-2 note)", "confirmatory (world record)"),
    ("A4.4 the day-1 stop: update tasks verified when no value was given", "1 of 11", "b4r/b4r-results.md", "The world: Bank", "confirmatory (world record)"),
    ("A4.4 whole-document writes, pooled share", "0.037 (7 of 188)", "b4r/world-dynamics-v3.md", "(b2) Whole-document writes against the edit tools, pooled", "confirmatory"),
    ("A4.4 brief 14's disclosure line", "R0.8 as filled", "b4r/b4r-results.md", "The disclosure line (R0.8, filled)", "confirmatory"),
    ("A4.5 Part J: triples certified on both passes", "0 of 89", "b3/rater/certification-b3.md", "J2 (pooled 1 of 89 on pass 1; of which both passes 0)", "methods"),
    ("A4.5 Part J: the writers' mean lift (composition minus the top line)", "13.46 (Sonnet 16.17, GLM 10.29)", "b3/review/review-partj-2026-10-31.md", "3 Reconciliation, Verified from the files", "methods"),
    ("A4.5 Part J: the lift needed with every line at or under 60", "at least 16", "b3/review/review-partj-2026-10-31.md", "2 Fable's read, Mechanism", "methods"),
    ("A4.5 Part J: Spearman(composition, top line)", "0.628", "b3/review/partj-diagnostics-2026-10-31.md", "diagnostics block, 'spearman comp vs top line'", "methods"),
    ("A5.3 brief 23: test items' mean D_part against the nulls", "Sonnet 5.5 0.442 vs 0.000 (not evaluable, 43 of 48); Kimi K3 0.625 vs 0.011; GPT-6 Sol 0.448 vs 0.021; no interval in the record", "legibility/instrument-v0.md", "Validation sentences per reader family, sentence 3", "instrument"),
    ("A5.3 the T1 join's one sentence (verbatim from brief 15 A6.17.7)", "27 of 138; v2 0.24; v3 0.15; Spearman 0.28 to 0.35 pooled", "b3/comprehension/t1-join-v0.md", "Rater line score: two-pass mean (pooled row; v2_conforming and v3_middle rows)", "exploratory"),
    ("A5.3 the comprehension-quiet stratum", "28 of 78 (0.359)", "b3/comprehension/stratum-v0.md", "first line", "instrument"),
    ("A5.3 purity, not completeness (C1's expectation)", "P(labelled quiet | truly quiet) 0.519 [0.127, 0.742]; P(labelled quiet | not quiet) 0.005 [0.000, 0.032]", "b3/comprehension/stratum-v0.md", "C1's expectation (not a bar)", "instrument"),
    ("A5.3 the rendering artefact confirmed (brief 26)", "unresolved-anchor candidates: 16 items, 29 of 48 lines found at day 0; every candidate line found at every Part S draw (234 of 234); reverse case 0; drop list 8", "b3/inserter-dry-run-v0.md", "first line; Aggregates (anchors_resolve false: candidates); Per line at the Part S state", "instrument"),
    ("A5.3 / A5.5 the resolved-anchor subset, net", "17", "b3/power-simulation-v3c.md", "populations table (resolved-anchor subset 17)", "design"),
    ("A5.4 the per-account cross-document entity rule's honest cost", "0.20 [0.11, 0.30] (unrepaired 0.020 [0.000, 0.050])", "b4r/z5-v3.md", "The pass (R0.1); residual rules, any_cross_document", "confirmatory (pre-registered world readout)"),
    ("A5.4 the cross-account rule's honest cost", "0.40 [0.27, 0.53]", "b4r/z5-v3.md", "The cross-account cell (R0.5, A.3)", "confirmatory (pre-registered world readout)"),
    ("A5.4 the edit-count rule's control-arm recall from lone to k = 3", "0.708, 0.458, 0.250", "t1-replant/replant-results.md", "Volume rule", "exploratory"),
    ("A5.5 m_L", "18.22 (a stated convention)", "b3/plan.md", "8 Round 2", "pre-registration"),
    ("A5.5 round 2 floor and target", "floor 12 + 12; target 26 certified and at least 12 quiet-but-illegible", "b3/plan.md", "8 Round 2, Size", "pre-registration"),
    ("A5.5 A6.18 (l)'s caveat", "0.67", "b3/plan.md", "7 The disclosures (A6.18 (l), verbatim)", "pre-registration"),
    ("A3 R-A: instances composed within a day; held to a day end", "2 of 4 composed (P2, P4), both lost the same day; 0 held to a day end", "pilot/forensics/forensics.md", "A2 How long each composition lasted", "exploratory"),
    ("A3 R-A: the one any-day carrier", "one carrier, a coalition account's non-scenario session; counts under the rule as written, not under a composition-at-carrying rule", "pilot/forensics/forensics.md", "A4 The carrier write", "exploratory"),
    ("A3 R-C: bands per instance and the sensitivity", "brief 09 bands P1 80 and above, P2 to P4 40 to 69; P2 moved under the same-session sensitivity", "pilot/forensics/rc-sensitivity.md", "same-session sensitivity table", "sensitivity"),
]

NOT_TRACED = [
    ("A5.4 (brief 22 section 0) the chance figure beside the cross-account rule ('chance 0.64')",
     "held only in work/stage3/b4/power-simulation-b4.md (brief 19's design record, not in the manifest), computed there as 1 - 0.6^2; "
     "not in b4r-results, z5-v3, b0-results or the re-plant table: not written (A5.4)"),
    ("A3 the exact intervals beside the pilot's counts",
     "no manifest file carries an exact interval for 2 of 4 or for the carrier count; brief 13 W3 forbids computing one: counts are written without intervals and the gap is named"),
    ("A3 R-D's counts (the live footprint)",
     "held in the pilot's measure files (m1c-footprint.md, via the checkpoint 3b memo), not in the manifest: R-D is written as its sentence only"),
]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def entry_for(path: str, tag: str, source: str, tables: list[str], beyond: bool) -> dict:
    a, b = STAGE3 / path, FORK_STAGE3 / path
    e = {"path": path, "sha256": sha256(a), "bytes": a.stat().st_size,
         "sha256_fork_copy": sha256(b) if b.exists() else None}
    e["copies_identical"] = e["sha256_fork_copy"] == e["sha256"]
    e.update({"tag": tag, "tag_source": source, "added_beyond_brief_list": beyond, "tables_drawn_on": tables})
    if not b.exists():
        e["note"] = "no fork mirror at results/stage3/" + path + "; kept in this amendment record only, not in files, until the coordinator mirrors it"
    if path == "b3/plan.md":
        raw = a.read_bytes()
        prior_bytes = len(_git_show(PLAN_STATUS_FORK_COMMIT, "results/stage3/b3/plan.md"))
        e["status_recorded_sha256"] = PLAN_STATUS_SHA
        e["status_recorded_bytes"] = prior_bytes
        e["prefix_equals_status_version"] = hashlib.sha256(raw[:prior_bytes]).hexdigest() == PLAN_STATUS_SHA
        e["note"] = ("STATUS's latest record of plan.md is 58b0c121 (fork 58b0c24); the file on disk carries S3 Stage A's appended dated note "
                     "(fork be0a600), which STATUS has not yet recorded. Hashed as on disk; prefix_equals_status_version checks that nothing "
                     "above the note changed. Re-run with --rerun-plan when STATUS records the move (A5.1 W0). Only sections 1 to 8 are read.")
    return e


def _git_show(commit: str, path: str) -> bytes:
    import subprocess
    return subprocess.run(["git", "-C", str(FORK), "show", f"{commit}:{path}"], check=True, capture_output=True).stdout


def cited_entry(path: str, fork_path: str | None, tag: str, source: str) -> dict:
    a = ROOT / path
    b = FORK / fork_path if fork_path else None
    e = {"path": path, "path_root": "project root", "sha256": sha256(a), "bytes": a.stat().st_size,
         "fork_copy_path": fork_path, "sha256_fork_copy": sha256(b) if b and b.exists() else None}
    e["copies_identical"] = e["sha256_fork_copy"] == e["sha256"] if e["sha256_fork_copy"] else None
    e.update({"tag": tag, "tag_source": source, "cited_only": True, "added_beyond_brief_list": False})
    if e["sha256_fork_copy"] is None:
        e["note"] = "no fork mirror; cited for method only"
    return e


def verify_existing(m: dict) -> list[str]:
    bad = []
    for f in m["files"]:
        a, b = STAGE3 / f["path"], FORK_STAGE3 / f["path"]
        if not a.exists() or sha256(a) != f["sha256"]:
            bad.append(f"main {f['path']}")
        if not b.exists() or sha256(b) != f["sha256_fork_copy"]:
            bad.append(f"fork {f['path']}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--rerun-plan", action="store_true")
    args = ap.parse_args()
    raw = MANIFEST.read_bytes()
    m = json.loads(raw)
    if (json.dumps(m, indent=1, ensure_ascii=False) + "\n").encode() != raw:
        raise SystemExit("refusing: the manifest does not re-serialise byte-identically")
    bad = verify_existing(m)
    print(f"existing entries: {len(m['files'])}; hash mismatches or missing copies: {len(bad)} {bad[:5]}")
    if bad:
        raise SystemExit("refusing: an existing entry no longer matches its hash")
    mine = [a for a in m.get("amendments", []) if a.get("by") == BY]
    if args.rerun_plan:
        if not mine:
            raise SystemExit("refusing: no W0 amendment to refresh")
        new = entry_for("b3/plan.md", *[x[1:] for x in NUMBER_SOURCES if x[0] == "b3/plan.md"][0])
        rec = mine[0]
        rec.setdefault("plan_refreshes", []).append({"previous": next(e for e in rec["entries"] if e["path"] == "b3/plan.md"), "refreshed_to": new["sha256"]})
        rec["entries"] = [new if e["path"] == "b3/plan.md" else e for e in rec["entries"]]
        m["files"] = [new if f["path"] == "b3/plan.md" else f for f in m["files"]]
    else:
        if mine:
            raise SystemExit("refusing: a W0 amendment already exists (use --rerun-plan for plan.md)")
        entries = [entry_for(*x) for x in NUMBER_SOURCES]
        cited = [cited_entry(*x) for x in CITED_ONLY]
        to_files = [e for e in entries if e["copies_identical"]]
        traces = [{"figure": f, "value_as_recorded": v, "file": p, "table": t, "tag": g} for f, v, p, t, g in TRACES]
        known = {e["path"] for e in m["files"]} | {e["path"] for e in entries}
        missing = sorted({t["file"] for t in traces} - known)
        if missing:
            raise SystemExit(f"refusing: traces name files outside the manifest: {missing}")
        rec = {"date": "2026-11-02", "by": BY,
               "added": [e["path"] for e in to_files],
               "entries": entries + cited,
               "kept_in_amendment_only": [e["path"] for e in entries if not e["copies_identical"]] + [c["path"] for c in cited],
               "traces": traces,
               "not_traced": [{"figure": f, "reason": r} for f, r in NOT_TRACED],
               "note": ("additive; no earlier entry changed. Every other figure the paper writes carries its file and table inline as "
                        "(tag; file, table); every file so cited is in this manifest. Records cited for method only (briefs 15, 22, 24; "
                        "work/lessons.md) are never a number source.")}
        if args.check:
            print(json.dumps({k: (v if k != "entries" else [(e["path"], e["sha256"][:8], e["sha256_fork_copy"] and e["sha256_fork_copy"][:8], e["tag"]) for e in v]) for k, v in rec.items() if k != "traces"}, indent=1, ensure_ascii=False))
            print(f"traces {len(traces)}; files would become {len(m['files']) + len(to_files)}")
            return 0
        m["amendments"].append(rec)
        m["files"].extend(to_files)
    m["n_files"] = len(m["files"])
    m["all_copies_identical"] = all(f["copies_identical"] for f in m["files"])
    m["mismatched_or_missing"] = sum(1 for f in m["files"] if not f["copies_identical"])
    out = (json.dumps(m, indent=1, ensure_ascii=False) + "\n").encode()
    MANIFEST.write_bytes(out)
    (FORK_STAGE3 / "b0" / "frozen-tables.json").write_bytes(out)
    print(f"written: n_files {m['n_files']}; all_copies_identical {m['all_copies_identical']}; sha256 {hashlib.sha256(out).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
