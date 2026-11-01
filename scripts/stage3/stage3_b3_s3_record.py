#!/usr/bin/env python3
"""Brief 33 (S3, 2026-11-02): Stage A's record, `work/stage3/b3/s3-stage-a-v0.md`, assembled from the stage's artifacts by
hash (counts, hashes, ids and dollars only; no item text). Run at the end of Stage A, after the trace audit.

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_s3_record.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
B3 = PROJECT / "work/stage3/b3"
FORK = PROJECT / "work/mole-fork"
OUT = B3 / "s3-stage-a-v0.md"
FILES = ["s3-config-v0.json", "s3-preflight-v0-prenote.json", "s3-preflight-v0.json", "plan.md", "s3-analysis-matrix-v0.json", "s3-readings-dryrun-v0.json",
         "s3-readings-dryrun-v0.md", "s3-lone-line-check-v0.json", "s3-applications-v0.json", "s3-applications-v0.md", "s3-render-v0.json",
         "s3-trace-policy.json", "s3-trace-audit-stageA.json"]
SCRIPTS = ["stage3_b3_s3_matrix.py", "test_stage3_b3_s3_matrix.py", "stage3_b3_s3_readings.py", "test_stage3_b3_s3_readings.py", "stage3_b3_s3_dryrun.py",
           "stage3_b3_s3.py", "test_stage3_b3_s3.py", "stage3_b3_lone_line_check_s3.py", "test_stage3_b3_lone_line_check_s3.py",
           "stage3_b3_s3_trace_audit.py", "test_stage3_b3_s3_trace_audit.py", "stage3_b3_s3_record.py"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def j(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    h = {f: sha(B3 / f) for f in FILES if (B3 / f).exists()}
    hs = {f: sha(HERE / f) for f in SCRIPTS if (HERE / f).exists()}
    pre, pre0 = j(B3 / "s3-preflight-v0.json"), j(B3 / "s3-preflight-v0-prenote.json")
    cfg = j(B3 / "s3-config-v0.json")
    dry = j(B3 / "s3-readings-dryrun-v0.json")
    ll = j(B3 / "s3-lone-line-check-v0.json")
    app = j(B3 / "s3-applications-v0.json")
    ren = j(B3 / "s3-render-v0.json")
    tr = j(B3 / "s3-trace-audit-stageA.json") if (B3 / "s3-trace-audit-stageA.json").exists() else None
    head = subprocess.run(["git", "-C", str(FORK), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    fx, oc = dry["fixtures"], dry["oc"]
    L = [f"# S3 Stage A record (brief 33 v2.1, 99e3ec7f): the $0 stage before the gate — written {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%MZ')}", ""]
    L.append("Blue session (Fable 5.1). No judge request was sent; no OpenRouter request of any kind; nothing applied on disk outside the never-open "
             "application file. Barrier kept: ids, counts, hashes, scores and labels only; no item line, document text, rubric or declared effect printed, "
             "logged or written into any record; `work/stage3/red/`, persona files, `archived-scores*`, the anchor sheet and its draw file, and other briefs' "
             "judge caches not opened (the trace audit below). Every path is from the project root.")
    L.append("")
    L.append("## A1. Pre-flight and the stream set")
    L.append("")
    L.append(f"- Configuration `work/stage3/b3/s3-config-v0.json` ({h['s3-config-v0.json'][:8]}): placement seed {cfg['placement_seed']}, bootstrap {cfg['bootstrap_seed']} x {cfg['bootstrap_replicates']}, "
             f"tie {cfg['tie_seed']}, m_s {cfg['m_s_carrier']} and {cfg['m_s_second']}, m_L {cfg['m_L']}, arm seeds {cfg['arm_seeds']} (exactly the tags 1, 2, 3, 4 and 6; no tag 5).")
    L.append(f"- Before A1b's note: `stage3_b3_preflight.py --config` **{'PASS' if pre0['pass'] else 'FAIL'}**, {pre0['n_files']} of 26 files, {len(pre0.get('prompts', []))} prompt components, "
             f"value mismatches {pre0['values']['mismatches']}; plan.md {pre0['plan_sha256'][:8]} equal to the fork's HEAD copy ({pre0['plan_matches_fork_head']}). Output kept as `s3-preflight-v0-prenote.json` ({h['s3-preflight-v0-prenote.json'][:8]}).")
    L.append(f"- The driver asserts the stream set itself (`stage3_b3_s3.assert_arm_seeds`, tested: a tag 5, a missing tag 6 and a wrong value each refuse).")
    L.append("")
    L.append("## A1b. The dated note on the plan")
    L.append("")
    L.append(f"- Appended verbatim under the heading the brief gives, 2026-11-02; `work/stage3/b3/plan.md` **{h['plan.md'][:8]}** ({(B3 / 'plan.md').stat().st_size} bytes; its first 111,603 bytes hash to 58b0c121, so nothing above the note changed); "
             f"mirrored to `results/stage3/b3/plan.md` and committed to the fork (be0a600); the `s1-preflight-sha256` block is unchanged (26 lines).")
    L.append(f"- Pre-flight re-run after the commit: **{'PASS' if pre['pass'] else 'FAIL'}**, {pre['n_files']} of 26, plan.md {pre['plan_sha256'][:8]} matches HEAD ({pre['plan_matches_fork_head']}); `s3-preflight-v0.json` ({h['s3-preflight-v0.json'][:8]}). `test_stage3_b3_preflight.py` 10 pass.")
    L.append("")
    L.append("## A2. The analysis matrix, the readings script and the dry run")
    L.append("")
    L.append(f"- Matrix `work/stage3/b3/s3-analysis-matrix-v0.json` **{h['s3-analysis-matrix-v0.json'][:8]}** by `stage3_b3_s3_matrix.py` ({hs['stage3_b3_s3_matrix.py'][:8]}; tests {hs['test_stage3_b3_s3_matrix.py'][:8]}, 11 pass): "
             f"116 net items (73 candidates, 21 control items, 22 comparison items) keyed by opaque id; every input verified by sha256 before it is read (the seven files of 9a769d68 `inputs_sha256`, "
             f"stratum-v0.json 6113bd8d, s1-populations-v0.json f17e7a72, inserter-dry-run-v1.json 02138931, and the four payload and control files pinned in v1's `inputs_sha256`, read for each statement's `op` only); "
             f"section 1.2's table reproduced (means, SD, IQR, writer and document counts, pooled strata; tested against s1-populations-v0.json and Part 3's Step 0 to 1e-3); the candidates' rater fields equal brief 25's file; no item text (tested).")
    L.append(f"- Readings script `stage3_b3_s3_readings.py` **{hs['stage3_b3_s3_readings.py'][:8]}** (tests {hs['test_stage3_b3_s3_readings.py'][:8]}); dry run `stage3_b3_s3_dryrun.py` ({hs['stage3_b3_s3_dryrun.py'][:8]}); report "
             f"`s3-readings-dryrun-v0.md` ({h['s3-readings-dryrun-v0.md'][:8]}) and `.json` ({h['s3-readings-dryrun-v0.json'][:8]}).")
    L.append(f"- The exception table against Part 3's simulator, each delta tested: replicate failure more than 10 percent of 2,000 (not 2.5 percent); form (b) with the top-two gap (the note); the floor once on the full set against the sham; "
             f"2,000 replicates at seed 20261152 (not 1,000); the fixed quartiles 47.5 and 66.5 for every population; the cascade as seven ordered steps; a rank-deficient design is a fit failure (the simulator's fitter converges on one; tested).")
    L.append(f"- Reachability: {len(fx['fixtures'])} fixtures, all reaching their ids: **{fx['all_ok']}**; ids not reached by any fixture: {fx['unreached'] or 'none'}; S-P1 unreachable by decision (the k = 2 arm is not run); S4-1 by the separate session after Aravind reports. Wall time {fx['wall_seconds']} s.")
    if oc:
        acc = oc["acceptance"]
        L.append(f"- Operating characteristics through the adapter (seed {oc['seed']}, tag {oc['tag']}, ICC {oc['icc']}, {oc['experiments']} experiments per truth, {oc['replicates']} replicates; {oc['seeding']}): "
                 f"the carrier's P(excluded | 0) on the subset under the \"none\" model **{acc['P_excl_0_subset_C']:.3f}** against Part 3's 0.68; P(present | 1.5 x) **{acc['P_present_x1.5_subset_C']:.3f}** against 0.72; tolerance ± 0.08: "
                 f"**{'ACCEPTED' if acc['accepted'] else 'OUTSIDE'}**. The full set under the \"zero\" model beside, named in the report. Wall time {oc['wall_seconds']} s.")
    L.append("")
    L.append("## A3. The draws and the application set, once")
    L.append("")
    L.append(f"- (i) Payload and control files verified against v1's `inputs_sha256` before the draw; the applied id sets hash to section 1.1's values ({', '.join(f'{k} {v['n']} ({v['ids_sha256'][:8]})' for k, v in app['id_sets'].items())}).")
    cd, cv = ll["candidates_default_mode"], ll["control_items_v1"]
    L.append(f"- (ii) Brief 27's harness copied with an opt-in (`stage3_b3_lone_line_check_s3.py` {hs['stage3_b3_lone_line_check_s3.py'][:8]}; tests {hs['test_stage3_b3_lone_line_check_s3.py'][:8]}, 28 pass with the gated reproduction): "
             f"default mode reproduces the candidates' {cd['accepted_draws']} of {cd['listed_draws']} ({cd['reproduces_brief27']}); the control items through v1: net 21 items, {cv['net_21_items']['lines']} lines, "
             f"**{cv['net_21_items']['accepted_draws']} of {cv['net_21_items']['listed_draws']} listed draws accepted**, refused {cv['net_21_items']['refused_listed_by_reason'] or 'none'}; gross 22: {cv['gross_22_items']['accepted_draws']} of {cv['gross_22_items']['listed_draws']}; "
             f"record `s3-lone-line-check-v0.json` ({h['s3-lone-line-check-v0.json'][:8]}).")
    c = app["counts"]
    L.append(f"- The draw: module {app['module']['sha256'][:8]} in restricted mode on `inserter-dry-run-v1.json` {app['inputs_sha256']['work/stage3/b3/inserter-dry-run-v1.json'][:8]}, corpus {app['inputs_sha256']['work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl'][:8]}, "
             f"template {app['inputs_sha256']['work/mole-fork/bootstrap/org_template.yaml'][:8]}; arm seeds {app['arm_seeds']}; window {app['window']['days']} ({app['window']['rule']}). "
             f"Units: items {c['items']} (expected 232), lines {c['lines']} (expected 564); by regime: candidate items {c['candidate_items']}, control items {c['control_items']}, comparison items {c['sham_items']}, candidate lines {c['candidate_lines']}, control lines {c['control_lines']}; "
             f"counts equal the plan's: **{app['counts_equal_expected']}**; by stream tag {c['by_stream_tag']}; by day {c['by_day']}; by writer {c['by_writer']}.")
    from collections import Counter
    units = app["units"].values()
    broken = sum(1 for x in units if x["record"]["honest_edits_broken"] > 0)
    at_ten = sum(1 for x in units if x["redraws"] >= 10)
    composed_all = all(x["record"]["composed"] and x["record"]["delivered"] for x in units)
    pairs_ok = sum(1 for i in {x["item_id"] for x in units}
                   if len({x["author"] for x in units if x["item_id"] == i and x["arm"] == "item"}) == 2 and len({x["day"] for x in units if x["item_id"] == i and x["arm"] == "item"}) == 2)
    L.append(f"- Refused draws at application time (section 2.4 (3), the next draw of the same stream): {app['refused_draws_by_reason'] or 'none'}; re-draws per application {app['redraws']} "
             f"(the module's own rule, section 2.3: a draw that broke no honest edit is preferred for the first {10} re-draws; {at_ten} applications reached 10 and {broken} applications in all carry a broken honest edit, "
             f"rebuilt by the module as T1 v3 did). Every application delivered and composed: {composed_all}. Items whose two applications are by different authors on different days: {pairs_ok} of {len({x['item_id'] for x in units})}. "
             f"S3's own drops: **{app['own_drops']['n']}** {app['own_drops']['by_reason'] or ''}; control items leaving the add-on: **{app['addon_left']['n']}**.")
    L.append(f"- `s3-applications-v0.json` **{h['s3-applications-v0.json'][:8]}** (never-open: applied document states and packets; {len(app['units'])} units); record `s3-applications-v0.md` ({h['s3-applications-v0.md'][:8]}). Wall time {app['seconds']} s.")
    L.append("")
    L.append("## A4. The driver, the packets, the caches and the pre-signal")
    L.append("")
    L.append(f"- Driver `stage3_b3_s3.py` **{hs['stage3_b3_s3.py'][:8]}** (tests {hs['test_stage3_b3_s3.py'][:8]}): modes apply | render | score; the ledger (one guard through `request_guard` on every client, in-flight reservations, the stop at $153.25, "
             f"each client's own cap the stop less the other caches), the view order enforced, the pause after the first about 20 carrier units, resumable state, the scores file's flag through `stage3_thresholds.is_flagged` at the sealed rule (tested).")
    L.append(f"- Packets (`s3-render-v0.json` {h['s3-render-v0.json'][:8]}): cache labels unique within S3: {ren['labels_unique']} ({ren['n_labels']} labels); caches to live under `work/stage3/b3/cache-s3/`, none before Stage B (tested).")
    L.append("")
    L.append("| row | units (items + lines) | packets sha256 | pre-signal estimate | S2 at Part 2's basis | truncated |")
    L.append("|---|---|---|---|---|---|")
    for k, r in ren["rows"].items():
        L.append(f"| {k} | {r['n_units']} ({r['n_item_units']} + {r['n_line_units']}) | {r['packets_sha256'][:8]} | ${r['estimate']['est_cost_usd']:.2f} | ${r['s2_dollars_at_basis']:.2f} | {r['estimate']['n_truncated']} |")
    L.append(f"| **total** | | | **${ren['pre_signal_total_usd']:.2f}** | ${ren['s2_total_usd']:.2f} | |")
    L.append("")
    L.append(f"- Pre-signal total **${ren['pre_signal_total_usd']:.2f}** beside S2's $76.62 (ratio {ren['ratio_to_figure']}); exceeds the figure by more than a third: **{ren['escalate']}**. {ren['note']}.")
    L.append("")
    L.append("## Trace audit (Stage A)")
    L.append("")
    if tr:
        L.append(f"- `stage3_b3_s3_trace_audit.py` ({hs['stage3_b3_s3_trace_audit.py'][:8]}; tests {hs['test_stage3_b3_s3_trace_audit.py'][:8]}, 7 pass, the positive test bound to the empty `--writer-dir`) around the pinned script 2a409344 on this session's transcript "
                 f"`{Path(tr['trace']).name}` with `--writer-dir {Path(tr['writer_dir']).relative_to(PROJECT)}` (empty; every token absolutised first) and the policy `s3-trace-policy.json` ({h['s3-trace-policy.json'][:8]}): "
                 f"opened {tr['opened']}, allowed {tr['allowed']}, outside {tr['outside']} (existing files {tr['outside_existing_files']}, non-existent tokens {tr['outside_non_existent_tokens']}), **never-open {tr['never_open']}**; verdict {tr['verdict']}.")
    L.append("")
    L.append("## Differences from the brief and the plan, reported")
    L.append("")
    for line in (B3 / "s3-stage-a-rulings.md").read_text().splitlines() if (B3 / "s3-stage-a-rulings.md").exists() else ["(none recorded)"]:
        L.append(line)
    L.append("")
    L.append("## Hashes")
    L.append("")
    for f, v in h.items():
        L.append(f"- `work/stage3/b3/{f}` {v}")
    for f, v in hs.items():
        L.append(f"- `work/checks/{f}` {v}")
    L.append(f"- fork HEAD at writing: {head} (S3's Stage A commits are be0a600, the plan note, and 948865b, A1 to A2 and A4's code; the brief 13 writing session committed to the fork beside, ff2fc64, 8c3a490 and 39e34ab, untouched by S3)")
    L.append("")
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT.relative_to(PROJECT)} sha256 {sha(OUT)[:8]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
