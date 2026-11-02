#!/usr/bin/env python3
"""Brief 33 B4 (S3 Stage B; the 33-B session, 2026-11-02): the Stage B record and the entries B4 names, from the stage's
artefacts by hash (counts, hashes and dollars only; no sentence of b3-results is quoted here, no item text, no score).

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_s3_stage_b_record.py records    # the additions file, the record, the prep-report entry, the outputs index row
    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_s3_stage_b_record.py manifest   # after the fork mirror: the frozen-tables manifest entries

records writes `work/stage3/b3/b3-results-additions.md` (a dated addition beside `b3-results.md`, as S4-1 will be: the three
disclosures brief 33's notes carry that the frozen readings script does not write, from the Stage A record's A3b counts and
the coordinator's dated note 2), `work/stage3/b3/s3-stage-b-v0.md` (the run record and the spend table per cell against
S2's rows, the lock, the trace audit's counts, every artefact's hash), the prep-report entry "Brief 15 (B3), S3" with its
sealed-parameters subsection, and the B3 row of `work/stage3/INDEX.md`. manifest appends the outputs to
`work/stage3/b0/frozen-tables.json` as new file entries under one amendment (additive; no earlier entry changed).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
S3 = PROJECT / "work/stage3"
B3 = S3 / "b3"
FORK = PROJECT / "work/mole-fork"
RECORD = B3 / "s3-stage-b-v0.md"
ADDITIONS = B3 / "b3-results-additions.md"
PREP = S3 / "prep-report.md"
OUT_INDEX = S3 / "INDEX.md"
MANIFEST = S3 / "b0/frozen-tables.json"
FIGURE_USD, STOP_USD, PRE_SIGNAL_USD = 76.62, 153.25, 48.87
RESULT_FILES = ["b3-results.md", "b3-results.json", "b3-results-additions.md", "s3-scores-v0.json", "s3-run-v0.json", "s3-stage-a-v0.md", "s3-stage-b-v0.md",
                "s3-honest-pairs-check-v0.json", "s3-trace-audit-stageB.json"]
HASH_FILES = RESULT_FILES + ["s3-applications-v0.json", "s3-render-v0.json", "s3-analysis-matrix-v0.json", "s3-clean-items-v0.json", "plan.md",
                             "s3-trace-policy.json", "s3-readings-dryrun-v0.json", "s3-config-v0.json", "s3-preflight-v0.json"]
CACHE_FILES = sorted(p.name for p in (B3 / "cache-s3").glob("*.jsonl")) if (B3 / "cache-s3").exists() else []
SCRIPTS = ["stage3_b3_s3.py", "stage3_b3_s3_readings.py", "stage3_b3_s3_record.py", "stage3_b3_s3_stage_b_record.py", "stage3_b3_s3_trace_audit.py", "judge_client.py", "judge_openrouter.py"]
CELL_ORDER = ["P_author_doc_iso|opus48", "P_author|opus48", "P_author_doc_iso|sonnet", "P_author|sonnet", "P_author_doc_live|opus48", "P_author_doc_live|sonnet",
              "O_diff|sonnet", "O_diff|opus48", "O_diff|sol"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def j(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")


def a3b_counts(app: dict, matrix: dict) -> dict:
    """Brief 33's dated note 1 (G2): applications that broke a later honest edit, by arm and regime; counts only (the Stage A
    record's A3b, recomputed from the application file by script; the file itself is never open to a reader)."""
    units = list(app["units"].values())
    def share(sel):
        n = len(sel)
        k = sum(1 for x in sel if x["record"]["honest_edits_broken"] > 0)
        return {"k": k, "n": n, "share": round(k / n, 3) if n else None}
    out = {}
    for reg, label in (("candidate", "candidates"), ("control", "control items"), ("sham", "comparison items (sham)")):
        sel = [x for x in units if x["regime"] == reg]
        out[label] = {"items": share([x for x in sel if x["arm"] == "item"]), "lines": share([x for x in sel if x["arm"] == "line"]), "all": share(sel)}
    for pop, label in (("subset", "resolved-anchor subset"), ("stratum", "comprehension-quiet stratum"), ("full", "full quiet set")):
        ids = set(matrix["populations"][pop]["ids"])
        sel = [x for x in units if x["item_id"] in ids]
        out[label] = {"items": share([x for x in sel if x["arm"] == "item"]), "lines": share([x for x in sel if x["arm"] == "line"]), "all": share(sel)}
    out["all"] = {"items": share([x for x in units if x["arm"] == "item"]), "lines": share([x for x in units if x["arm"] == "line"]), "all": share(units)}
    out["items_touched"] = len({x["item_id"] for x in units if x["record"]["honest_edits_broken"] > 0})
    out["items"] = len({x["item_id"] for x in units})
    return out


def spend_rows(run: dict, render: dict) -> list[dict]:
    rows = []
    for c in CELL_ORDER:
        v, r = run["cells"][c], render["rows"][c]
        e = r["estimate"]
        rows.append({"cell": c, "status": v["status"], "n_units": v["n_units"], "scored": v["scored"], "refused": v["refused"], "errored_final": v.get("errored_final", 0),
                     "errored_once": v.get("errored_once", 0), "missing": v["missing"], "dollars": round(v["dollars"], 4), "per_unit": round(v["dollars"] / v["n_units"], 5),
                     "estimate_usd": e["est_cost_usd"], "estimate_per_unit": round(e["est_cost_usd"] / e["n_calls"], 5),
                     "ratio_to_estimate": round((v["dollars"] / v["n_units"]) / (e["est_cost_usd"] / e["n_calls"]), 3),
                     "rebased_usd": run["first_batch"]["rebased_by_cell"][c], "s2_usd": r["s2_dollars_at_basis"], "s2_basis_per_unit": r["s2_basis_per_unit"]})
    return rows


def additions_md(h: dict, a3b: dict, rec_a: str) -> str:
    L = [f"# Dated addition beside `b3-results.md` ({h['b3-results.md'][:8]}; brief 33 B3): the disclosures brief 33's notes carry that the readings script does not write — {now()}", ""]
    L.append("Written by the 33-B session (brief 33-B Part 2, B4) beside the results file, as S4-1 will be added (brief 33 B3), because the readings script "
             f"(`stage3_b3_s3_readings.py` {h['stage3_b3_s3_readings.py'][:8]}) is frozen after its commit and was not edited after Stage B began. Counts and hashes only; "
             "nothing here selects or changes a sentence of `b3-results.md`, which carries section 7's disclosures verbatim, brief 31's three disclosures, the union-flag disclosure of "
             "brief 33's dated note 5, the operating characteristics beside Part 3's (O3) and S-G6's source (dated note 3).")
    L.append("")
    L.append("## 1. The executor (brief 33's dated note 6; the coordinator's gate line)")
    L.append("")
    L.append("Stage A (brief 33) and Stage B (brief 33-B) were executed by Fable 5.1 sessions, not by Opus 5.5 with Sonnet 5.5 as the named fallback. Every output is tested and hashed; "
             "the deviation has no bearing on validity and is disclosed with the results. Fable 5.1's independent reads of Stage A and its addendum (`review/fable-read-s3-stage-a-2026-11-02.md` 06da4716, "
             "`review/fable-read-s3-addendum-2026-11-02.md` 927d0c0b on disk) sit beside the review session's reads.")
    L.append("")
    L.append("## 2. The pre-signal's basis (brief 33's dated note 2; the Stage A record's addendum)")
    L.append("")
    L.append("The pre-signal estimate's carrier gap against S2 ($13.17 against $35.59) was not missing thinking tokens: Opus 4.8's thinking is inside `output_tokens`, as B1's bases were. S2's carrier "
             "basis was B4-R's $0.0447 per unit on the other prefix against B1's realised $0.01743 on this prefix; the pre-signal was 0.95 of B1's realised. Stage B's realised carrier cost was "
             f"$0.01676 per unit (ratio 1.01 to its own character estimate; 0.37 of S2's basis); the whole run cost $43.79 against the pre-signal $48.87, the first batch's re-based $66.19, the confirmed figure $76.62 and the stop $153.25 "
             f"(the spend table in `s3-stage-b-v0.md`).")
    L.append("")
    L.append(f"## 3. Applications that broke a later honest edit (brief 33's dated note 1, G2; the Stage A record `s3-stage-a-v0.md` {rec_a[:8]}, A3b; counts only)")
    L.append("")
    L.append("The module's own rule (plan section 2.2 unchanged; `PREFER_CLEAN_DRAWS` 10, then a draw that breaks a later honest edit is accepted and the edit rebuilt as T1 v3 did, section 2.3) "
             "changes the document history the dossier and `O_diff` views read for these applications. By arm, regime and population (`honest_edits_broken` > 0):")
    L.append("")
    L.append("| group | item applications | lone-line applications | all applications |")
    L.append("|---|---|---|---|")
    for g, v in a3b.items():
        if g in ("items_touched", "items"):
            continue
        def f(x):
            return f"{x['k']} of {x['n']}" + (f" ({x['share']:.3f})" if x["share"] is not None else "")
        L.append(f"| {g} | {f(v['items'])} | {f(v['lines'])} | {f(v['all'])} |")
    L.append("")
    L.append(f"Items with at least one such application: {a3b['items_touched']} of {a3b['items']} (the exclusion set of the clean-set sensitivity S-G6, `s3-clean-items-v0.json` {h['s3-clean-items-v0.json'][:8]}, "
             f"brief 33's dated note 3; by population subset 15 of 17 clean, stratum 23 of 26, full set 66 of 73). The shares did not differ materially between candidates, controls and sham "
             f"(the coordinator's dated note 1), so nothing beyond the disclosure and S-G6 was decided.")
    L.append("")
    L.append("## 4. The human anchor")
    L.append("")
    L.append("S4-2 stands in `b3-results.md` (not yet scored). S4-1 is computed by a separate $0 blue session after Aravind reports his scores, from the draw file S3 is barred from, and is added beside as its own dated addition.")
    L.append("")
    return "\n".join(L)


def record_md(h: dict, hs: dict, hc: dict, run: dict, render: dict, rows: list[dict], tr: dict | None, scores: dict, results: dict, head: str) -> str:
    fb = run["first_batch"]
    total = run["dollars"]["total"]
    L = [f"# S3 Stage B record (brief 33 B1 to B4 under brief 33-B Part 2; the 33-B session, Fable 5.1): the judge run, the lock and the readings — {now()}", ""]
    L.append("Counts, hashes and dollars only; no sentence of `b3-results.md` is quoted here, no item text, no score, no flag aggregate. Barrier kept: the application file read by script only; "
             "`work/stage3/red/`, persona files, `archived-scores*`, the anchor sheet and its draw file, and other briefs' judge caches not opened (the trace audit below). Every path is from the project root. "
             "No OpenRouter request of any kind.")
    L.append("")
    L.append("## B1. The first batch and the pause")
    L.append("")
    L.append(f"- The gate: the coordinator's STATUS line of 2026-11-02 (\"S3 GATE: HOLDS. STAGE B MAY BEGIN\") on driver `stage3_b3_s3.py` {hs['stage3_b3_s3.py'][:8]} (G10 in, fork 4a02207 pushed). "
             f"`score` sent the first {fb['n_units']} Opus 4.8 item units of the carrier view (`P_author_doc` isolated, ascending opaque id) and paused by itself (exit 3): outcomes {fb['outcomes']}, "
             f"{fb['attempts']} attempts, refused {fb['refused']}; realised {fb['input_tokens']} input and {fb['output_tokens']} output tokens (thinking inside, as B1's bases), ${fb['dollars']:.4f}, "
             f"${fb['realised_per_unit_usd']:.5f} per unit against the batch's own character estimate ${fb['estimated_per_unit_usd']:.5f} (ratio **{fb['ratio_realised_over_estimated']}**; fewer input tokens than "
             f"estimated, about twice the output tokens), the whole cell's per-unit estimate ${fb['cell_estimate_per_unit_usd']:.5f} beside (ratio {fb['ratio_realised_over_cell_estimate']}), and Part 2's basis "
             f"${fb['part2_basis_per_unit_usd']:.5f} (ratio {fb['ratio_realised_over_part2_basis']}). Re-based total (every cell's estimate scaled by the ratio, as B1's `rebase`) **${fb['rebased_total_usd']:.2f}** "
             f"beside the figure ${FIGURE_USD}; escalate {fb['escalate']} (the threshold ${FIGURE_USD * 4 / 3:.2f}); stop ${STOP_USD} unchanged. Reported to the coordinator with no score or flag aggregate; "
             f"the run continued on the coordinator's STATUS line (\"S3 STAGE B: FIRST BATCH DONE; RE-BASE $66.19 AGAINST $76.62; NO ESCALATION; THE RUN CONTINUES\") with `--continue`.")
    L.append("")
    L.append("## B2. The cells in order, each complete before the next")
    L.append("")
    L.append("| cell | units | scored | refused | errored | missing | realised $ | per unit | own estimate per unit | ratio | re-based $ | S2 at Part 2's basis |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        L.append(f"| {r['cell']} | {r['n_units']} | {r['scored']} | {r['refused']} | {r['errored_final']} | {r['missing']} | ${r['dollars']:.4f} | ${r['per_unit']:.5f} | ${r['estimate_per_unit']:.5f} | {r['ratio_to_estimate']} | ${r['rebased_usd']:.2f} | ${r['s2_usd']:.2f} |")
    L.append(f"| **total** | {sum(r['n_units'] for r in rows)} | {sum(r['scored'] for r in rows)} | {sum(r['refused'] for r in rows)} | {sum(r['errored_final'] for r in rows)} | {sum(r['missing'] for r in rows)} | "
             f"**${total:.2f}** | | pre-signal ${PRE_SIGNAL_USD} | | ${fb['rebased_total_usd']:.2f} | ${render['s2_total_usd']:.2f} |")
    L.append("")
    L.append(f"- Every cell complete in B2's order; stops recorded: {0 if not run.get('stops_cleared') else len(run['stops_cleared'])}; G7-only continues: {run.get('g7_continues') or 'none'}; "
             f"errored units: {sum(r['errored_final'] + r['errored_once'] for r in rows)}; refusals: {sum(r['refused'] for r in rows)}. Stage B started {run['stage_b_started']}, completed {run['completed']}. "
             f"Total **${total:.2f}** against the pre-signal ${PRE_SIGNAL_USD}, the re-based ${fb['rebased_total_usd']:.2f}, the figure ${FIGURE_USD} and the stop ${STOP_USD} (ratio to the figure {total / FIGURE_USD:.2f}); "
             f"no draw repeated after any judge call; no OpenRouter request. Run record `s3-run-v0.json` {h['s3-run-v0.json'][:8]}.")
    L.append(f"- Caches under `work/stage3/b3/cache-s3/` (one per view and model; never open to a scenario-side session): " + "; ".join(f"`{c}` {sha(B3 / 'cache-s3' / c)[:8]}" for c in CACHE_FILES) + ".")
    L.append(f"- The scores file `s3-scores-v0.json` {h['s3-scores-v0.json'][:8]}: {len(scores['rows'])} rows (unit id, item id, regime, arm, role, placement, view, judge, outcome, score, flag (the union), "
             f"flag_unit, union_max, n_honest_other_pairs, cache label; no text); built from the application file {scores['applications_sha256'][:8]}; stopped: {scores['stopped']}.")
    L.append("")
    L.append("## B3. The readings, once")
    L.append("")
    lock = results["lock"]
    cas = results["cascade"]
    L.append(f"- The analysis lock: {lock['rows']} of {lock['expected_rows']} rows, incomplete rows {lock['incomplete'] or 'none'}, stopped {bool(lock['stopped'])}: open. "
             f"`stage3_b3_s3_readings.py` {hs['stage3_b3_s3_readings.py'][:8]} run once on the scores file and the matrix ({h['s3-analysis-matrix-v0.json'][:8]}) with the clean-items file "
             f"({h['s3-clean-items-v0.json'][:8]}), G9's check file ({h['s3-honest-pairs-check-v0.json'][:8]}, PASS) and the dry run's operating characteristics ({h['s3-readings-dryrun-v0.json'][:8]}); "
             f"plan {h['plan.md'][:8]} (fork commit 1fafa57), judge clients judge_client.py {hs['judge_client.py'][:8]} and judge_openrouter.py {hs['judge_openrouter.py'][:8]} (section 4.10), the window rule as recorded.")
    L.append(f"- **`b3-results.md` {h['b3-results.md'][:8]}, `b3-results.json` {h['b3-results.json'][:8]}**: {len(results['sentences'])} sentences in section 6.0's assembly order, every one selected by rule and every "
             f"slot filled by rule; by family: {dict(sorted(Counter(s['family'] for s in results['sentences']).items()))}. The cascade reached state `{cas['state']}` at step {cas.get('step')} (the sentence families say which; "
             f"this record does not quote them). Section 7's disclosures verbatim, brief 31's three disclosures, the union-flag disclosure (dated note 5), the operating characteristics beside Part 3's (O3), "
             f"S-G6's source (dated note 3), the pointer to round 2 (section 8) and S4-2 are in the file; S-N2 or S-N3 selected by rule.")
    L.append(f"- Beside it, `b3-results-additions.md` {h['b3-results-additions.md'][:8]} (a dated addition, as S4-1 will be): the executor, the pre-signal's basis (dated note 2) and the broken-honest-edit counts "
             f"(dated note 1), which the frozen readings script does not write.")
    L.append("")
    L.append("## B4. Trace audit, entries and the mirror")
    L.append("")
    if tr:
        L.append(f"- Trace audit (this session's transcript `{Path(tr['trace']).name}`, the policy regenerated for it): opened {tr['opened']}, allowed {tr['allowed']}, outside {tr['outside']} (existing files "
                 f"{tr['outside_existing_files']}, non-existent tokens {tr['outside_non_existent_tokens']}), **never-open {tr['never_open']}**; verdict {tr['verdict']} (`s3-trace-audit-stageB.json` {h['s3-trace-audit-stageB.json'][:8]}; "
                 f"policy `s3-trace-policy.json` {h['s3-trace-policy.json'][:8]}).")
    L.append(f"- The prep-report entry \"Brief 15 (B3), S3\" with its sealed-parameters subsection; the outputs added to the frozen-tables manifest `b0/frozen-tables.json` under one amendment; the B3 row of "
             f"`work/stage3/INDEX.md`; the fork mirror under `results/stage3/b3/` and `scripts/stage3/` (not pushed; the coordinator pushes); one STATUS line; brief 33-B's row in `briefs/INDEX.md`.")
    L.append(f"- Done against brief 33: the gate held on the coordinator's STATUS line; every cell of section 2.6 and the add-on scored; `b3-results.{{json,md}}` exist with every family's sentence selected by rule; "
             f"the spend table is within the stop; the mirror is committed. Not done by S3, by design: S4-1 (the separate session after Aravind reports).")
    L.append("")
    L.append("## Hashes")
    L.append("")
    for f in HASH_FILES:
        if f in h:
            L.append(f"- `work/stage3/b3/{f}` {h[f]}")
    for c in CACHE_FILES:
        L.append(f"- `work/stage3/b3/cache-s3/{c}` {sha(B3 / 'cache-s3' / c)}")
    for f, v in hs.items():
        L.append(f"- `work/checks/{f}` {v}")
    L.append(f"- fork HEAD at writing: {head}")
    L.append("")
    return "\n".join(L)


def prep_entry(h: dict, hs: dict, rows: list[dict], run: dict, results: dict) -> str:
    fb = run["first_batch"]
    total = run["dollars"]["total"]
    L = ["", f"## Brief 15 (B3), S3 (2026-11-02): the application set, the judge readings and `b3-results` (${total:.2f} Bedrock; Stage A $0)", ""]
    L.append(f"**First line.** The pre-registered readings of plan `b3/plan.md` ({h['plan.md'][:8]}; S1 with its dated notes) are in **`b3/b3-results.md` {h['b3-results.md'][:8]}** (`.json` {h['b3-results.json'][:8]}): "
             f"{len(results['sentences'])} sentences in section 6.0's assembly order, every one selected by rule and every slot filled by rule, with section 7's disclosures verbatim, brief 31's, the union-flag "
             f"disclosure and the operating characteristics beside Part 3's; the dated addition `b3/b3-results-additions.md` ({h['b3-results-additions.md'][:8]}) beside it carries the executor, the pre-signal's basis and the "
             f"broken-honest-edit counts. This entry quotes no sentence: the paper reads the results file at its hash (the coordinator's verification and the review session's read precede the push). S4-1, the human anchor, "
             f"is pending Aravind's scores (a separate $0 session).")
    L.append("")
    L.append(f"**Stage A ($0; brief 33, record `b3/s3-stage-a-v0.md` {h['s3-stage-a-v0.md'][:8]}).** Pre-flight 27 of 27 with `s3-config-v0.json`; the matrix `b3/s3-analysis-matrix-v0.json` {h['s3-analysis-matrix-v0.json'][:8]}; "
             f"the readings script {hs['stage3_b3_s3_readings.py'][:8]} with its dry run (33 fixtures reaching every sentence id but the two decided; operating characteristics 0.64 / 0.09 / 0.02 / 0.73 against Part 3's 0.68 / 0.07 / 0.03 / 0.72, accepted); "
             f"the one draw (232 item and 564 lone-line applications, every count the plan's, no drop; `b3/s3-applications-v0.json` {h['s3-applications-v0.json'][:8]}, never open); the driver {hs['stage3_b3_s3.py'][:8]} with the ledger; "
             f"the union flag (plan.md's dated note 3) with G9's check PASS ({h['s3-honest-pairs-check-v0.json'][:8]}); G7's errored-unit rule; the pre-signal $48.87.")
    L.append("")
    L.append(f"**Stage B (brief 33-B; record `b3/s3-stage-b-v0.md` {h['s3-stage-b-v0.md'][:8]}).** The first batch of {fb['n_units']} carrier units re-based the run to ${fb['rebased_total_usd']:.2f} against the confirmed $76.62 (no escalation); "
             f"then B2's nine cells in order: 4,344 of 4,344 units scored, 0 refused, 0 errored, no stop; the lock opened and the readings ran once. Realised ${total:.2f}: "
             + "; ".join(f"{r['cell']} ${r['dollars']:.2f}" for r in rows) + ".")
    L.append("")
    L.append("### Sealed defender parameters produced by brief 15 (B3), S3 (added to the section-10 list; never read by a scenario-side session)")
    L.append("")
    L.append("- `b3/plan.md` with its dated notes (the pre-flight hash list at 27), `b3/s3-config-v0.json`, `b3/s3-analysis-matrix-v0.json`, `b3/s3-applications-v0.json` (never open: applied document states and packets) and `b3/s3-applications-v0.md`, "
             "`b3/s3-render-v0.json`, `b3/s3-clean-items-v0.json`, `b3/s3-honest-pairs-check-v0.json`, `b3/s3-run-v0.json`, `b3/s3-scores-v0.json`, `b3/b3-results.{json,md}`, `b3/b3-results-additions.md`, "
             "`b3/s3-stage-a-v0.md`, `b3/s3-stage-b-v0.md`, `b3/s3-readings-dryrun-v0.{json,md}` with `b3/s3-dryrun-parts/`, the nine judge caches `b3/cache-s3/judge-cache.s3.*.jsonl` and `b3/cache-s3/judge-batches.jsonl`, "
             "the trace audits `b3/s3-trace-audit-stage{A,A2,A3,B}.json` and the policy.")
    L.append("- The scripts `stage3_b3_s3.py`, `stage3_b3_s3_readings.py`, `stage3_b3_s3_dryrun.py`, `stage3_b3_s3_matrix.py`, `stage3_b3_s3_record.py`, `stage3_b3_s3_stage_b_record.py`, `stage3_b3_s3_trace_audit.py`, "
             "`stage3_b3_lone_line_check_s3.py` and their tests (canonical in `work/checks/`, byte-identical in the fork's `scripts/stage3/`).")
    L.append("")
    L.append("### Spend")
    L.append("")
    L.append(f"${total:.2f} of Bedrock (Opus 4.8 ${sum(r['dollars'] for r in rows if r['cell'].endswith('opus48')):.2f}, Sonnet 5 ${sum(r['dollars'] for r in rows if r['cell'].endswith('sonnet')):.2f}, "
             f"GPT-6 Sol ${sum(r['dollars'] for r in rows if r['cell'].endswith('sol')):.2f}) against the confirmed figure $76.62 and the stop $153.25; the pre-signal was $48.87 and the first batch's re-base $66.19. "
             "No OpenRouter use, nothing planted on disk outside the never-open application file, nothing launched.")
    L.append("")
    return "\n".join(L)


def mode_records() -> int:
    app, matrix = j(B3 / "s3-applications-v0.json"), j(B3 / "s3-analysis-matrix-v0.json")
    run, render = j(B3 / "s3-run-v0.json"), j(B3 / "s3-render-v0.json")
    scores, results = j(B3 / "s3-scores-v0.json"), j(B3 / "b3-results.json")
    tr = j(B3 / "s3-trace-audit-stageB.json") if (B3 / "s3-trace-audit-stageB.json").exists() else None
    hs = {f: sha(HERE / f) for f in SCRIPTS if (HERE / f).exists()}
    hc = j(B3 / "s3-honest-pairs-check-v0.json")
    h = {f: sha(B3 / f) for f in HASH_FILES if (B3 / f).exists()}
    h.update(hs)
    rows = spend_rows(run, render)
    if any(r["status"] != "complete" for r in rows) or scores["stopped"] or run.get("stopped"):
        raise SystemExit("refusing: the run is not complete; B4's record is written after the lock opens or a stop is recorded (this script handles the complete case)")
    ADDITIONS.write_text(additions_md(h, a3b_counts(app, matrix), h["s3-stage-a-v0.md"]), encoding="utf-8")
    h["b3-results-additions.md"] = sha(ADDITIONS)
    head = subprocess.run(["git", "-C", str(FORK), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    RECORD.write_text(record_md(h, hs, hc, run, render, rows, tr, scores, results, head), encoding="utf-8")
    h["s3-stage-b-v0.md"] = sha(RECORD)
    # the prep-report entry (appended once)
    prep = PREP.read_text(encoding="utf-8")
    marker = "## Brief 15 (B3), S3 (2026-11-02)"
    if marker in prep:
        raise SystemExit("refusing: the prep-report entry exists")
    PREP.write_text(prep.rstrip("\n") + "\n" + prep_entry(h, hs, rows, run, results), encoding="utf-8")
    # the B3 row of the outputs index
    ix = OUT_INDEX.read_text(encoding="utf-8")
    old = "**the S3 brief is `briefs/33-b3-s3-2026-11-02.md`** (cold read pending), then S3;"
    if ix.count(old) != 1:
        raise SystemExit("refusing: the outputs index's B3 row was not found once")
    new = (f"**S3 done 2026-11-02** (brief 33, Stage A $0, and brief 33-B, Stage B ${run['dollars']['total']:.2f} Bedrock): the readings `b3/b3-results.md` {h['b3-results.md'][:8]} (every sentence by rule; "
           f"the dated addition `b3/b3-results-additions.md` beside; S4-1 pending Aravind's scores), records `b3/s3-stage-a-v0.md` {h['s3-stage-a-v0.md'][:8]} and `b3/s3-stage-b-v0.md` {h['s3-stage-b-v0.md'][:8]}, "
           f"4,344 of 4,344 units scored with no refusal or error;")
    OUT_INDEX.write_text(ix.replace(old, new), encoding="utf-8")
    print(json.dumps({"additions": h["b3-results-additions.md"][:8], "record": h["s3-stage-b-v0.md"][:8], "results_md": h["b3-results.md"][:8], "results_json": h["b3-results.json"][:8],
                      "prep_report": sha(PREP)[:8], "outputs_index": sha(OUT_INDEX)[:8], "total_usd": run["dollars"]["total"]}))
    return 0


def mode_manifest() -> int:
    m = j(MANIFEST)
    tags = {"b3-results.md": "confirmatory", "b3-results.json": "confirmatory", "b3-results-additions.md": "methods", "s3-scores-v0.json": "methods", "s3-run-v0.json": "methods",
            "s3-stage-a-v0.md": "methods", "s3-stage-b-v0.md": "methods", "s3-honest-pairs-check-v0.json": "methods", "s3-trace-audit-stageB.json": "methods"}
    drawn = {"b3-results.md": ["every sentence of plan section 6 selected by rule (S-A to S-R, S4-2); the disclosures; the cascade"], "b3-results.json": ["readings, floors, labels, cascade, composed, sentences, meta"],
             "b3-results-additions.md": ["the executor; the pre-signal's basis; applications that broke a later honest edit"], "s3-scores-v0.json": ["unit outcomes, scores and flags (no text)"],
             "s3-run-v0.json": ["the first batch and its re-base; the cells' spend"], "s3-stage-a-v0.md": ["Stage A: pre-flight, matrix, dry run, the draw, A3b, the addenda"],
             "s3-stage-b-v0.md": ["B1 to B4: the spend table per cell against S2's rows; the lock; the trace audit"], "s3-honest-pairs-check-v0.json": ["G9: the union's keys, counts by cause"],
             "s3-trace-audit-stageB.json": ["the trace audit's counts"]}
    src = ("brief 33 (Stage A, $0) and brief 33-B (Stage B, $43.79 Bedrock; the 33-B session, Fable 5.1): S3's one application set scored under every row of plan section 2.6 and the add-on, "
           "the readings computed once after the 4,344-row lock opened; the coordinator verifies and the review session reads before the push")
    existing = {f["path"] for f in m["files"]}
    added, entries = [], []
    for f in RESULT_FILES:
        p = B3 / f
        if not p.exists():
            raise SystemExit(f"refusing: {p} is missing")
        rel = f"b3/{f}"
        if rel in existing:
            raise SystemExit(f"refusing: {rel} is already in the manifest")
        fork = FORK / "results/stage3" / rel
        if not fork.exists():
            raise SystemExit(f"refusing: {rel} has no fork copy yet (mirror first)")
        e = {"path": rel, "sha256": sha(p), "bytes": p.stat().st_size, "sha256_fork_copy": sha(fork), "copies_identical": sha(p) == sha(fork), "tag": tags[f], "tag_source": src,
             "added_beyond_brief_list": False, "tables_drawn_on": drawn[f]}
        entries.append(e)
        added.append(rel)
    m["files"].extend(entries)
    m["n_files"] = len(m["files"])
    m["all_copies_identical"] = all(f.get("copies_identical", True) for f in m["files"])
    m["amendments"].append({"date": "2026-11-02", "by": "brief 33 B4 (the 33-B session, Fable 5.1): S3's outputs", "added": added, "note": "additive; no earlier entry changed; b3/plan.md stays held as the W0e amendment records"})
    MANIFEST.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": sha(MANIFEST)[:8], "n_files": m["n_files"], "added": added, "all_copies_identical": m["all_copies_identical"]}))
    return 0


if __name__ == "__main__":
    sys.exit({"records": mode_records, "manifest": mode_manifest}[sys.argv[1]]())
