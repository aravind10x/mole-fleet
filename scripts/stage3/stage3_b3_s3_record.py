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
         "s3-trace-policy.json", "s3-trace-audit-stageA.json", "s3-clean-items-v0.json", "s3-trace-audit-stageA2.json"]
SCRIPTS = ["stage3_b3_s3_matrix.py", "test_stage3_b3_s3_matrix.py", "stage3_b3_s3_readings.py", "test_stage3_b3_s3_readings.py", "stage3_b3_s3_dryrun.py",
           "stage3_b3_s3.py", "test_stage3_b3_s3.py", "stage3_b3_lone_line_check_s3.py", "test_stage3_b3_lone_line_check_s3.py",
           "stage3_b3_s3_trace_audit.py", "test_stage3_b3_s3_trace_audit.py", "stage3_b3_s3_record.py"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def j(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def a3b(app: dict, matrix: dict) -> list[str]:
    """G2 (brief 33's dated note of 2026-11-02): applications whose draw broke a later honest edit (`honest_edits_broken` > 0,
    the module's own rule after PREFER_CLEAN_DRAWS re-draws, plan section 2.2 unchanged), by arm, regime and population;
    counts only, a disclosure for b3-results."""
    from collections import Counter
    units = list(app["units"].values())
    pops = matrix["items"]
    def share(sel):
        n = len(sel)
        k = sum(1 for x in sel if x["record"]["honest_edits_broken"] > 0)
        return f"{k} of {n} ({k / n:.3f})" if n else "0 of 0"
    L = ["### A3b. Applications that broke a later honest edit (G2; `honest_edits_broken` > 0; counts only)", ""]
    L.append("| group | item applications | lone-line applications | all applications |")
    L.append("|---|---|---|---|")
    for reg, label in (("candidate", "candidates"), ("control", "control items"), ("sham", "comparison items (sham)")):
        sel = [x for x in units if x["regime"] == reg]
        L.append(f"| {label} | {share([x for x in sel if x['arm'] == 'item'])} | {share([x for x in sel if x['arm'] == 'line'])} | {share(sel)} |")
    for pop, label in (("subset", "resolved-anchor subset (17)"), ("stratum", "comprehension-quiet stratum (26)"), ("full", "full quiet set (73)")):
        ids = set(matrix["populations"][pop]["ids"])
        sel = [x for x in units if x["item_id"] in ids]
        L.append(f"| {label} | {share([x for x in sel if x['arm'] == 'item'])} | {share([x for x in sel if x['arm'] == 'line'])} | {share(sel)} |")
    L.append(f"| **all** | {share([x for x in units if x['arm'] == 'item'])} | {share([x for x in units if x['arm'] == 'line'])} | {share(units)} |")
    L.append("")
    by_tag = Counter(x["stream_tag"] for x in units if x["record"]["honest_edits_broken"] > 0)
    touched = sorted({x["item_id"] for x in units if x["record"]["honest_edits_broken"] > 0})
    items_touched = len(touched)
    # G6 (brief 33's dated note 3): the exclusion set, fixed by this script for the readings script's clean-set sensitivity (ids and counts only)
    clean = {"version": "b3-s3-clean-items/v0", "source": "s3-applications-v0.json honest_edits_broken > 0 (A3b)", "applications_sha256": hashlib.sha256((B3 / "s3-applications-v0.json").read_bytes()).hexdigest(),
             "touched_ids": touched, "touched_ids_sha256": hashlib.sha256("\n".join(touched).encode()).hexdigest(),
             "by_population": {pop: {"n": len(matrix["populations"][pop]["ids"]), "touched": sum(1 for i in matrix["populations"][pop]["ids"] if i in set(touched)),
                                     "clean": sum(1 for i in matrix["populations"][pop]["ids"] if i not in set(touched))} for pop in ("subset", "stratum", "full", "controls", "sham")}}
    (B3 / "s3-clean-items-v0.json").write_text(json.dumps(clean, indent=1) + "\n")
    L.append(f"By stream tag: {dict(sorted(by_tag.items()))}; items with at least one such application: {items_touched} of {len({x['item_id'] for x in units})} "
             f"(the exclusion set for G6, `s3-clean-items-v0.json`, ids sha256 {clean['touched_ids_sha256'][:8]}; by population {clean['by_population']}). "
             f"Every such application was delivered and composed; the module rebuilt the later honest edit's content as T1 v3's rule does (section 2.3), which the dossier and `O_diff` views then read.")
    return L


def addendum(h, hs, fx, oc, tr2, clean, pre) -> list[str]:
    """Stage A addendum: brief 33's dated notes 2 and 3 of 2026-11-02 (G1 revised, G3 to G6, O1 to O8), with the new hashes."""
    L = ["## Stage A addendum (brief 33's dated notes 2 and 3 of 2026-11-02; $0, no judge request)", ""]
    L.append(f"- **G1 revised (the flag).** plan.md's dated note 3 of 2026-11-02 (plan.md **{h['plan.md'][:8]}**, fork 1fafa57; prefix bytes equal to a411d8a2): the flag is the sealed author-level reading, the union "
             f"(B1's primary, `recall_by_arm` and `flagged_union`), the planted unit's own flag beside; section 4.1's form (b) null bias stands, nothing re-simulated; `work/stage3/views/p_author_c0.json` (3c61dd4d, the 89 honest "
             f"`P_author` rows of Sonnet 5's calibration) pinned, the `s1-preflight-sha256` block restated at 27 entries; `test_stage3_b3_preflight.py` asserts 27 by a dated comment. Pre-flight on the committed plan: "
             f"**{'PASS' if pre['pass'] else 'FAIL'} {pre['n_files']} of {pre['n_files']}** (`s3-preflight-v0.json` {h['s3-preflight-v0.json'][:8]}). The driver (`stage3_b3_s3.py` {hs['stage3_b3_s3.py'][:8]}) flags through the union "
             f"(`honest_pairs_for`, `union_max`, B1's `honest_pairs`) and the scores file carries `flag` (union) and `flag_unit` per unit; the readings script reads both: floor (b), the ceiling, the anchors' lone recall and the "
             f"composed gaps on the union with the unit's own flag beside. G1 (a)'s re-simulation artefacts were discarded uncommitted.")
    L.append(f"- **G3.** An instrument at floor (a) is not read: `Instrument.read` takes the floor (a) result and returns `not_read` \"floor\" for both forms with no label; `select` issues only its floor sentence (S-A2); "
             f"the `floor_carrier` fixture asserts the absence of every other id for that instrument.")
    L.append(f"- **G4.** S-G1 beside every *excluded* or *attenuated* reading, every instrument, form and population (S-D and S-R), once per reading (the S-F duplicate removed); tested.")
    L.append(f"- **G5.** (i) A unit still errored after the client's retries is unscored (the note's rule 1) and completes its cell (`cell_status`); `--continue` clears a recorded stop (`clear_stop`, kept on the run record). "
             f"(ii) The first-batch re-base compares the about 20 item units' realised cost with those same units' character-based estimate (`estimate_cell` on the batch), the whole cell's per-unit estimate shown beside; tested.")
    if clean:
        bp = clean["by_population"]
        L.append(f"- **G6.** Beside the carrier's form (a) reading, form (a) on the items none of whose applications broke a later honest edit: the exclusion set `s3-clean-items-v0.json` ({h.get('s3-clean-items-v0.json', 'n/a')[:8]}; "
                 f"{len(clean['touched_ids'])} touched items, ids sha256 {clean['touched_ids_sha256'][:8]}; subset {bp['subset']['clean']} of {bp['subset']['n']} clean, stratum {bp['stratum']['clean']} of {bp['stratum']['n']}, "
                 f"full set {bp['full']['clean']} of {bp['full']['n']}) is written by the A3b script from the application file and read by `--clean-items`; sentences S-G6 and S-G6b (descriptive, counts, no label, no effect on the cascade); "
                 f"two fixtures reach them.")
    L.append(f"- **O1 to O8.** O1 precedence in `read()` (floor, ceiling, fit); O2 an unscored application, not its item, leaves the anchors' and the floor's sham denominators; O3 the dry run's carrier figures beside Part 3's in `b3-results.md`; "
             f"O4 the descriptive marker on S-D outside the verdict population; O5 value tests for the slot arithmetic; O6 the bootstrap sub-stream rule stated in `b3-results.md`; O7 `secondary()` pools strata as section 4.3 does; "
             f"O8 `s_e()`'s wording when form (a) is unfit and form (b) fitted. O9: the differences list names the union as B1's primary.")
    L.append(f"- **Re-runs.** Readings script `stage3_b3_s3_readings.py` **{hs['stage3_b3_s3_readings.py'][:8]}** (tests {hs['test_stage3_b3_s3_readings.py'][:8]}); dry run `stage3_b3_s3_dryrun.py` {hs['stage3_b3_s3_dryrun.py'][:8]}: "
             f"{len(fx['fixtures'])} fixtures, all reaching their ids **{fx['all_ok']}**, ids not reached {fx['unreached'] or 'none'}; report `s3-readings-dryrun-v0.md` {h['s3-readings-dryrun-v0.md'][:8]}.")
    if oc:
        acc = oc["acceptance"]
        c0, cm, c15 = oc["cells"]["null|subset|none"]["form_a"]["C"], oc["cells"]["margin|subset|none"]["form_a"]["C"], oc["cells"]["x1.5|subset|none"]["form_a"]["C"]
        L.append(f"- **Operating characteristics re-run** (form (a) untouched): the carrier on the subset P(excluded | 0) **{c0['excluded']:.3f}**, P(excluded | margin) **{cm['excluded']:.3f}**, P(LB > 0 | 0) {c0['attenuated'] + c0['present']:.3f}, "
                 f"P(present | 1.5 x) **{c15['present']:.3f}**; acceptance {'ACCEPTED' if acc['accepted'] else 'OUTSIDE'} (the first run gave 0.640 / 0.090 / 0.023 / 0.730: "
                 f"{'unchanged' if (round(c0['excluded'], 3), round(c15['present'], 3)) == (0.64, 0.73) else 'moved'}). Beside Part 3's 0.68 / 0.07 / 0.03 / 0.72; bound (ii) 0.6 Monte Carlo SE below 0.10 against Part 3's 1.8 (section 7, A6.18 (e)).")
    if tr2:
        L.append(f"- **Trace audit (end of the pass)**: opened {tr2['opened']}, allowed {tr2['allowed']}, outside {tr2['outside']} (existing files {tr2['outside_existing_files']}), **never-open {tr2['never_open']}**; verdict {tr2['verdict']} (`s3-trace-audit-stageA2.json` {h.get('s3-trace-audit-stageA2.json', 'n/a')[:8]}).")
    L.append(f"- **Disclosures corrected (the coordinator's dated note 2).** The pre-signal's carrier gap is not thinking tokens (Opus 4.8's thinking is inside `output_tokens`, as B1's bases were): S2's carrier basis was B4-R's $0.0447 per unit on the "
             f"other prefix against B1's realised $0.01743 on this prefix, and the pre-signal is 0.95 of B1's realised, so the realised cost is likely near $49 with wide headroom under the stop; B1's re-base still decides. The executor was Fable 5.1.")
    return L


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
    L.append(f"- Pre-flight re-run after the commit: PASS, 26 of 26 (the run of that time, 03ed1816). After the dated note 3 of 2026-11-02 (the addendum below) the current run is "
             f"**{'PASS' if pre['pass'] else 'FAIL'}**, {pre['n_files']} of {pre['n_files']}, plan.md {pre['plan_sha256'][:8]} matches HEAD ({pre['plan_matches_fork_head']}); `s3-preflight-v0.json` ({h['s3-preflight-v0.json'][:8]}). `test_stage3_b3_preflight.py` 10 pass.")
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
    L += a3b(app, j(B3 / "s3-analysis-matrix-v0.json"))
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
    L += addendum(h, hs, fx, oc, tr2=j(B3 / "s3-trace-audit-stageA2.json") if (B3 / "s3-trace-audit-stageA2.json").exists() else None,
                  clean=j(B3 / "s3-clean-items-v0.json") if (B3 / "s3-clean-items-v0.json").exists() else None, pre=pre)
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
