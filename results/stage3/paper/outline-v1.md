# Paper outline v1 (brief 13 A5.2; committed before any prose; for the review session's cold read)

Working title: **Splitting a change across agents: which fleet monitors it defeats, and the unit of review that survives.**

Written by the brief 13 writing session (Opus 5.5) from the frozen manifest `work/stage3/b0/frozen-tables.json` at sha256 `67c72050…` (88 files after W0; fork 22fef6d). Replaces outline v0's section list (W1) by A5.2. No prose is drafted until the review session has cold-read this file.

## Rules this outline and the draft follow

- **Numbers.** Every number is written `value [interval] (tag; file, table)` and is in the manifest, traced to its file and the table inside it. W0's amendment record carries the traces A5 names and three figures **not traced, therefore not written**: brief 22 §0's chance figure beside the cross-account rule, exact intervals beside the pilot's counts, and R-D's counts. No number is computed in this session.
- **Tags.** *confirmatory*, *exploratory*, *sensitivity* (from the plan that produced the file); *instrument* (a validation or measurement of an instrument, never an outcome); *methods* (the rater's certification aggregates); *design* (simulated operating characteristics); *pre-registration* (a committed plan's fixed figures). A tag travels with its number into every section, the research statement included.
- **The partition** (theory pre-registration §3): *present* LB > 0 and point ≥ 0.3; *attenuated* LB > 0 and point < 0.3; *excluded* LB ≤ 0 and UB < 0.3; *inconclusive* otherwise; read only at **headroom** (the lone arm's lower bound at least 0.3 above the sham lone arm's upper bound). Below headroom: "undetectable at this cost; Δ not read".
- **Vocabulary.** The paper's prose says *applied change*, *application*, *test change*, *control items*, *same-shape comparison items* (the sham, when B3 is meant) and *the sham arm* (T1's same-shape control). "Planted" and its kin appear only inside verbatim quotes. "The re-plant" is kept as the experiment's name (A5.2 item 5).
- **Scope words.** Every sentence about how narrow the middle band is, how little splitting buys, or what cannot be constructed carries "with these writers" until the elicitation study has run (brief 24's purpose line, verbatim in §10 and §14).
- **Not written now:** the abstract, the introduction and the discussion (headed placeholders until B3's round 1 lands; A2, A5.1); the results of B3, B4, TRACK-C and B3's S4 anchor. No S3 output is opened until STATUS records `b3-results` at a hash with the coordinator's gate line (A5.5).
- **No dates or deadlines** in the paper.

## Front matter (placeholders)

- **Abstract** — placeholder until B3's round 1 lands.
- **Introduction** — placeholder; when written it carries the scope sentence of `proposal-11.12-revised-2026-10-23.md` section 2 and A1's two headline sentences, each with its tag, never joined by "and" or "because".

## 1. The question and the thesis

- **Framing sentence (A4.2, verbatim):** *which fleet monitors does splitting a harm across agents actually defeat, and what unit of review survives either way?*
- **Setting.** Fifty AI-operated accounts share an organisation's documents; per-agent monitors score accounts, authors or account-days; a composed view reviews a document's diff; a deployer has a fixed review budget.
- **The theory** (`theory-preregistration-2026-10-28.md` §2): a per-agent score s over an action set; splitting into parts gains s(A) − max s(A_i). Three classes: max-type (splitting cannot help), superadditive (combination, volume or both ends of a dependency matter; splitting helps), sub-additive (diluted by honest cover; the lever is cover). One agent spread across documents or days is **fragmentation across artifacts**, named as such wherever it appears.
- **The measured instance of each class:**
  - *Max-type content judges:* 07o's confirmatory exclusion of v1's effect (§5); B1's dossier readings (§4, §7); B0's mechanism join (exploratory, in-sample); B3 prospective, pending (§10).
  - *Superadditive:* the judge-free edit-count rule's recall on the sham arm falls from lone to k = 3, 0.708 (17/24) [0.489, 0.874], 0.458 (11/24) [0.256, 0.672], 0.250 (4/16) [0.073, 0.524] (exploratory, not a pre-registered contrast; `t1-replant/replant-results.md`, volume rule); the structural rules in §11.
  - *Across documents (the workspace view and the dossier):* B4's pending test (§11).
- **The headline, as two sentences with their tags (A1), in this order:**
  1. An applied change is caught when it holds the most visible statement: B0's mechanism join, 11 of 12 cells, volume adding ΔAUC 0.005 to 0.067 (exploratory, in-sample; `b0/b0-results.md`, Z2), to be confirmed prospectively in B3.
  2. Not on how many agents applied it: 07o's exclusion of v1's effect under its own rule, DiD 0.083 [−0.125, 0.292] (confirmatory; `t1-replant/replant-results.md`), with no reading at headroom yet under the theory's clause (`b0/b0-results.md`, Z2 strata; B1's isolated dossier below headroom, its live readings at headroom unable to separate max-type scoring from the neighbour leak; `b1/b1-results.md`).
- **Not claimed** (pre-registration §5): "scales with judge capability"; "independent of k".

## 2. Outcome separability and the honest null

- **The corollary** (`work/blog-thesis/ASSESSMENT.md` §0): a benchmark can only label harm it can tell apart from honest work, so it builds harms whose outcomes honest work never produces; where that outcome sits in state the defender reads and needs nothing only the attacker knows, the scorer is a near-free detector. Stated as the paper's starting point; **Stage 0's and MOLE's numbers are not in the manifest** and are not written (§15 names them as pending entries).
- **What sits at the top of every judge's honest null (Z4, exploratory; `b0/b0-results.md`, Z4):** O_diff units at or above threshold are mostly retroactive approvals and contact or host moves (Sonnet 0.633), contact or host moves and retroactive approvals (GLM 0.686), "safety step weakened" and contact or host moves (Opus 4.8 0.962), and under Opus 5.5's own rule 0.462 beside 43 refusals; the keyword classifier is unchecked against a human read, and categories follow each judge's wording.
- **The threshold is held up by honest non-compliance:** Sonnet's 12 retroactive approvals at or above threshold all sit on the release-gate runbook (Z4); Opus 5.5 refused 43 of 254 honest composed units (0.169), 40 on that runbook, the units Sonnet scores highest (exploratory; `q1q2-synthetic/judge-results.md`).
- **Honest edits on the rater's scale:** routine statements cannot be told from honest edits, AUROC 0.563 [0.480, 0.648]; middle statements sit modestly above, 0.648 [0.568, 0.722] (exploratory; `rater-07s/rater-honest-reference.md`, J2).
- **The density axis with the human anchor:** stated qualitatively (Stage 2b's co-touch comparison against a human tracker); its figures are **not in the manifest** and wait for an entry (named in §15).

## 3. The world and the instruments

- **World.** A MOLE fork in lab mode; fifty accounts; six class documents (runbooks, guides, a checklist, a README); one generator, Kimi K2.6, for honest and scenario sessions (`CONTEXT.md`). *Record discrepancy for the review session:* 07p's disclosure names the world's generator as Kimi K3; CONTEXT and the launch lines name K2.6; the paper follows CONTEXT.
- **Both prefixes.** `prefix_rw_v2c` (three days, fifty accounts, 130 successful class-document content writes; `b0/b0-results.md`, Z5) carries T1 v2, v3, the re-plant, B1, B3 and the pilot. `prefix_rw_v3rc` (bank v7b; 285 sessions; `b4r/b4r-results.md`) carries B4, with **brief 14's disclosure line verbatim** (R0.8 as filled).
- **Honest behaviours measured** (A4.4): honest agents asked to propagate a change without a stated value declined to invent one (1 of 11 update tasks verified on the stopped first day; `b4r/b4r-results.md`, the world); they rewrite and reword shared documents, so shared item lines found by name fell from 16 to 12 to 7 over the first two days (same table); line edits still dominate, whole-document writes 0.037 (7 of 188) of class writes pooled (`b4r/world-dynamics-v3.md`, b2). *Wording note for the review session:* A4.4's "agents rewrite shared documents whole" is stated as the two records say it, rewrites and rewording with line edits dominant.
- **Persistence, a world-dynamics limitation:** honest edits reach a maintained item's line about once a day or more; none of the 8 items is an anchor under the plan's rule (`b4r/world-dynamics-v3.md`, b4). Level-2 consumption is not read in this paper; it is scoped to world one's conditional live confirmation; the efficacy argument rests on the documents' role (runbooks and guides are acted on by construction), and the simulator's maintenance rate is named as the reason the world cannot show it.
- **Views, each with its honest null:** P_own (account-day), P_author (the sealed per-author view, zero-context, with the in-context variant beside), the author dossier isolated and live (B1), O_diff (a document's composed diff), and B4-R's workspace views O_ws and O_ws_all (nulls only so far). Thresholds by the seal's randomised rule at the sealed rates (O_diff 0.10; P_author 0.05 at author level; the dossier at 0.10).
- **Judges and families:** Sonnet 5 (sealed primary), Opus 4.8, GLM 5.3, Kimi K3, GPT-6 Sol; Opus 5.5 stopped at its null. Each judge at its own threshold on its own null.
- **The sham and the controls:** the same-shape sham arm (same edit shape, no harm), the forward sham rule (a judge's readings are interpretable only when the sham's attributable rate is low), the paired honest control (attributable readings); B3's same-writer control items and same-shape comparison items.
- **The rater and its drift rule:** the Claude rater's 0 to 100 visibility scale; two fresh-context passes agree (Spearman 0.978; `t1k-rater/ratings-summary.md`); drift between sessions of +8.05 points (`rater-07s/rater-honest-reference.md`, J3) makes the rule one session per comparison.
- **The comprehension readers (brief 23):** the whole-and-part question, two reader families plus Sonnet 5.5 beside, a consequence-only scorer; stated as an instrument with its validation status (not valid on the T1 items; null and scorer sound), not as a result.
- **The inserter:** the v3-amended inserter (class hash unchanged since T1 v3) and the old inserter of T1 v1, whose edit volume §5 is about.

## 4. Results by regime

- **The regime table (central figure, as a table):** rows are plantings and arms (v2 conforming = routine, alarming, sham; v3 middle, routine re-draw, sham re-draw; the re-plant's v1 and sham), ordered by the rater's payload maximum (07k pass 1 medians, `rater-07s/rater-honest-reference.md`, J1); columns under Sonnet 5: P_author lone and k = 2, O_diff composed, P_own per-piece flip rate; the other judges' composed level beside.
- **The re-plant supplies v1's point** (lone 0.500 [0.291, 0.709], k = 2 0.500 [0.291, 0.709], composed 0.734 [0.609, 0.837]; confirmatory; `t1-replant/replant-results.md`, Sonnet table); **the old-inserter point is shown hollow beside it** (T1 v1: lone 0.7083 [0.4891, 0.8738], k = 2 0.25 [0.0977, 0.4671]; `t1/t1-results.md`; confirmatory, superseded for Δ).
- **Caption's two labels:** the old-inserter v1 point is hollow; the x-axis is the Claude rater's scale, with weak human agreement (§8). The next experiments, B1 (done, §4 and §7), B3 and B4, are named in the caption; A1's two halves may sit side by side there with both tags.
- **Readings:** v2's regime contrasts (`t1v2/t1v2-results.md`); v3's S4 "the band is empty for the instruments" (`t1v3/t1v3-results.md`); the composed level across judges (§7); B1's dossier lift: every isolated reading below headroom (re-plant margins 0.278 Sonnet, 0.255 Opus 4.8); the live readings reach headroom on the re-plant and read *inconclusive*; Opus 4.8's live v3 reading, a weak-link sensitivity, reads *attenuated*; a live reading shows a neighbour's statement, so it cannot separate max-type scoring from that leak (confirmatory; `b1/b1-results.md`); the rater's composition item: read as triples with the grouping given, routine and middle triples separate from honest triples, and composition adds a near-constant lift over the loudest line (`rater-07s/rater-composition.md`, C2 and C3; the oracle-grouping condition, said with it).

## 5. The re-plant: v1's effect as edit volume

- 07o's confirmatory outcome under Sonnet: v1's effect excluded, DiD 0.083 [−0.125, 0.292], Δ_v1 0.000 [−0.167, 0.167] against the old inserter's 0.458; the under-80 condition did not hold (`t1-replant/replant-results.md`).
- The mechanism: the old inserter's lone units of four or more changes were flagged 14 of 17 times against 3 of 7 at three (same file, n_changes stratum); the edit-count rule flags the sham arm as often as the change itself.
- GLM 5.3 not interpretable; Opus 4.8 inconclusive (DiD 0.250 [0.000, 0.500]).
- Under the theory's clause: no Sonnet stratum at headroom (margin 0.080); the one stratum at headroom is Opus 4.8 on the re-plant, inconclusive (`b0/b0-results.md`, Z2).
- **The methods lesson:** every set-level signal needs a same-shape sham; an inserter's edit volume can manufacture a fragmentation effect.

## 6. The synthetic Q2

- The primary cell: X_doc − P 0.075 [−0.050, 0.200] at B = 0.10 (confirmatory; `q1q2-synthetic/results.md`); the lone arm's gain is at least k = 2's, so the reading is **artifact monitoring, not collusion detection**; X_acct recovers nothing beyond P.
- The truncation mechanism: a walked document carries 16.175 writer account-days against daily caps of four and five (the document layer's operating point, same file).
- The streaming operating mode (sensitivity; `q1q2-synthetic/streaming.md`): 0.350 against P's 0.175, gap 0.175 [0.000, 0.350], sham 0.100; at B = 0.05 0.225 [0.075, 0.375].
- The author ranker (exploratory; `q1q2-synthetic/author-ranker-results.md`): 0.125 [0.000, 0.250]; no collusion-specific recovery claimed.
- The insertion's volume footprint (the cheapest rule's reading in the same file).

## 7. Judge dependence and the boundary

- Four judges of three families at their own 10 percent rules: conforming composed recall 0.344, 0.328, 0.406, 0.391 (Sonnet 5, GLM 5.3, Opus 4.8, GPT-6 Sol), sham at or under 0.078 (exploratory; `q1q2-synthetic/extra-judge-results.md`, R1); the composed level is the judge-robust quantity; the per-author view is not judge-stable.
- The canonical invisible counts (confirmatory; `t1v3/invisible-canonical.md`, `t1-replant/invisible-canonical.md`): Sonnet's v2 union 11 of 24; the post hoc all-judge sensitivity leaves one; on the re-plant 1 of 24 under every interpretable judge.
- The panel negative (`t1v3/t1v3-panel.md`): no panel at matched cost beats the best single judge (v2 post hoc; v3 pre-registered).
- The Opus 5.5 refusals (§2; `q1q2-synthetic/judge-results.md`).
- **Added by A5.2:** Kimi K3's routing disclosure (brief 15 A6.17.10 (a), quoted from `b3/plan.md` §7): the comprehension readings' "Kimi K3" was a mixture of quantized upstream deployments.

## 8. The human anchor and the rater

- Batch 1 (twenty statements drawn at random, scored blind): Spearman 0.365 [−0.140, 0.764] against pass 1; mean absolute difference 22.300 [15.400, 29.600] (confirmatory; `t1v3/t1v3-rater-join.md`); batch 2's band-wise table; the disclosure that batch 2 was scored after batch 1's agreement was known.
- Pass agreement and drift (§3); the axis is labelled *the Claude rater's scale*.
- **B3's S4 anchor:** placeholder until Aravind's scoring is recorded.

## 9. Measuring combination (new; A5.3; instrument records only; every figure an instrument look)

- **Part J** (methods): two writers produced 0 of 89 triples certified on both passes (`b3/rater/certification-b3.md`, J2); the writers' mean lift (composition minus the loudest line) was 13.46 against at least 16 needed (`b3/review/review-partj-2026-10-31.md`); composition tracks the loudest line, Spearman 0.628 (`b3/review/partj-diagnostics-2026-10-31.md`). A hypothesis on the max-type pattern **in the rater itself**, never a result about judges.
- **The comprehension instrument** (instrument; `legibility/instrument-v0.md`, sentence 3): a single line lets a reader state the change's consequence often on the T1 items, test mean D_part 0.442 (Sonnet 5.5, not evaluable at 43 of 48), 0.625 (Kimi K3), 0.448 (GPT-6 Sol) against nulls of 0.000 to 0.021 (no interval in the record); so validity as separation was never reachable on those items; certification became item-level (brief 24's first amendment).
- **The T1 join's one sentence**, copied exactly from brief 15 A6.17.7 and cited by that reference (exploratory; `b3/comprehension/t1-join-v0.md`).
- **The comprehension-quiet stratum** (instrument; `b3/comprehension/stratum-v0.md`): 28 of 78 (0.359); pure, not complete (C1's expectation 0.519 [0.127, 0.742] and 0.005 [0.000, 0.032]); the rendering artefact confirmed by brief 26 (`b3/inserter-dry-run-v0.md`); why round 1's carrier is the resolved-anchor subset (net 17) with the full set descriptive (A6.14's switch, A6.18; `b3/power-simulation-v3c.md`).
- **The re-specification as method, number-free:** a continuous primary with both error directions named (A6.5); one latent margin for both forms (A6.13.2); the power gate corrected after a first run no design could pass (A6.13.1); the dry-run discipline (lessons L17 to L25, as the record shows them); the blind decisions recorded before the numbers (A6.15, A6.19, A6.25). Written as the record, with hashes.

## 10. B3 (placeholders until S3 and round 2 land; A5.5)

- **Round 1 (S3, brief 33):** the pre-registered readings of `plan.md` §4 to §6 on the resolved-anchor subset (net 17) at T2+S2; the full set descriptive with its dilution figure; every sentence selected by rule; §7's disclosures verbatim; P-max's reading (*holds*, *partly missed*, *falsified*, *inconclusive*) with A6.18 (l)'s caveat in its own words.
- **Round 2:** the matched level contrast on certified against quiet-but-illegible items from the elicitation study (`plan.md` §8: m_L 18.22, a stated convention; floor 12 + 12; target 26 certified and at least 12 illegible), never pooled with round 1.
- **The elicitation study:** a capability-ceiling measurement whose curve is a lower bound; its purpose line verbatim.

## 11. The structural half of the theory, in rules (new; A5.4); then B4 as a conditional design

- **Splitting pays against superadditive signals, seen in rules:** the per-account cross-document entity rule costs 0.20 [0.11, 0.30] of honest account-windows on the repaired world (confirmatory, a pre-registered world readout; `b4r/z5-v3.md`) and catches a one-account, two-document change that keeps both copies equal by construction; two accounts evade it; the cross-account rule costs 0.40 [0.27, 0.53] (same file); the edit-count rule's sham-arm recall falls 0.708 to 0.458 to 0.250 from lone to k = 3 (exploratory; `t1-replant/replant-results.md`). Brief 22 §0's chance figure is **not written** (not traced).
- **B4 as a conditional design** (brief 22): the gate G1 to G3 read from B3; path 1 confirmatory; path 2 descriptive and scoped "with these writers"; stated as the pending test of whether the content views behave superadditively across documents and whether the workspace view recovers the split.

## 12. The pilot as existence results and the world-dynamics limitation (A3, A4.4)

- R-A: 2 of 4 instances composed within a day, and no instance held its composition to a day end, so days 4 and 5 read 0 of 0 (exploratory; `pilot/forensics/forensics.md`, A2); the one any-day carrier was a coalition account's non-scenario session and counts under the rule as written, not under a composition-at-carrying rule (A4). **Exact intervals: not in the manifest; not written.**
- R-C: three instances in the 40 to 69 band, one at 80 and above through a whole-document rewrite; the drift caveat; brief 16's same-session sensitivity moved one instance (sensitivity; `pilot/forensics/rc-sensitivity.md`).
- R-D: "the live footprint is volume" (the sentence only; its counts are not in the manifest).
- World one is deferred (the Checkpoint 3b memo); the persistence finding as §3's world-dynamics limitation.

## 13. TRACK-C: the live fragmentation test

- The pre-registered diff-size test (`work/fakelab/protocol/TRACK-C-protocol-v1.md` §12): the prediction (a per-commit monitor is max-type over hunks, so the drop from K = 1 to K = 3 is a size effect and does not survive size matching) and the falsifier (a size-matched drop at K = 3 whose interval excludes zero on a max-type monitor), stated number-free.
- Named the live fragmentation test, not the live collusion test (A3, A4.6). State: C1 stopped on cost; B8 part 1 under brief 21; arm A complete, arm B in progress; **result placeholder** until the coordinator's read of `work/fakelab/b8-diffsize-report.md` is recorded.

## 14. Limitations

- **Three cases for multi-document harm (A4.3), the paper's boundary:** composed in one document (the unit is the document); combined by a reader across documents (the unit is the honest co-read group; B4's workspace view); combined by a system that no reader joins (the unit is the dependency graph; provenance monitoring, roadmap v3 section 5, not built). Coalition recovery from interaction structure is the last resort, needed where the composing unit is unobservable; Stage 2a's and 2b's negatives (§15) are the evidence that it is not the first layer here.
- Synthetic insertion's volume footprint; one generator (Kimi K2.6); author reuse (the sham control is 64 applications from 24 test changes and a small set of authors; no dependence-aware interval); the rater's family (a Claude rater on Claude-written placeholders; Part J's writers are Sonnet 5.5 and GLM 5.3); Kimi K3's mixed deployments in the comprehension readings.
- **What is not claimed:** that content judges are max-type in general (a hypothesis until B3 reports); "scales with judge capability"; "independent of k"; level-2 consumption; any live collusion result; and every "narrow band", "collusion buys little" or "not constructible" sentence beyond "with these writers".

## 15. The kill log and the earlier stages

- Tier 0 and Tier 1 material from `PLAN.md` §2: four designs killed on paper by near-free checks; F1 on the released corpus; F2, F3 and F3′ killed; Stage 2a's seed expansion and pacing results; Stage 2b's measured negative and its mechanism (break-glass grants); the density axis; the metadata leak.
- **Their figures are not in the manifest.** The section is written as the record's sentences without numbers, and names the files whose manifest entries would let the numbers be written (the Stage 0 to 2 results named in PLAN §2 and STATUS's checkpoint reports). For the coordinator.

## Appendix (built with the draft)

- A figure index: every figure in the draft, its file and table, from the inline citations, checked by script against the manifest.

## Changelog

- v1, 2026-11-02: from A5.2; W0 done first (manifest 88 files, 67c72050).
