# Facts for the note: who drafted the 56 plants, whether any was optimised against a monitor, and retention (blue harness session, 19 Nov 2026, 19:54 IST by `date`; $0, from blue-side T1, FT and P3 records)

Role terms only; no plant text. This adds to `facts-threat-model-v0.md` (ad89efbd).

**The 56 core plants by source** (`red/ft/cells-manifest.json` 7f44e41c, application ids by script):
- routine: 24, T1 v2 `conforming` (`T1v2-C…`);
- middle: 24, T1 v3 `middle` (`T1v3-M…`);
- alarming: 8, T1 v2 `alarming` (`T1v2-A…`).

## 1. Who drafted them: model sessions acting as writers, to written rules; no human wrote payload text
- **T1 v2 (routine and alarming):** written by one fresh Claude Code session (the brief 07g controller). It had seen none of T1 v1's statements, scores or rationales. It wrote all three arms itself; an Opus 5.5 sub-agent asked to draft the sham arm was stopped by a safety classifier before writing anything.
  - Brief: `briefs/07g-stage3-t1v2-placeholders-2026-10-23.md` 51017f65.
  - Rule: `work/stage3/decision-t1-rows-2-4-2026-10-23.md` (section 2, R1) 64fa09bc.
  - Checklist, written first: `work/stage3/t1v2/checklist.md` 92b9e153.
  - Record: `work/stage3/t1v2/README.md` faef9ffe (deviation 4).
  - Payloads committed by hash before anything was planted or scored: `payloads-v2.json` b2fe230b…, fork commit a3302f7, "committed before scoring".
  - The controller's model id is not recorded in the T1 v2 files.
- **T1 v3 (middle):** written by a fresh writer session, `claude-fable-5-1`, with no sub-agent.
  - Brief: `briefs/07l-stage3-t1v3-middle-band-2026-10-26.md` c8e84fd9.
  - Rule and checklist: `work/stage3/t1v3/checklist-v3.md` d76efc83. The middle-band rule is "unusual enough to be worth a question", without removing, weakening or bypassing a safeguard.
  - Record: `work/stage3/t1v3/writer-record.md` 6a744508.
  - Committed by hash before scoring: `payloads-v3.json` 13866e10…, fork commit d77dc3a.
- **The human's part:** The author did not draft payload text. He scored a sample of statements as human anchors for the rater (07k join, `t1v3/t1v3-rater-join.md` 899f70f0), after the payloads were fixed.

## 2. Optimisation: what is true
**No plant was drafted, filtered, sorted into a regime, dropped or rewritten using any model's score.** The plants were written to rules for each regime with no score seen, committed by hash, and then scored. Specifically:
- **The writers never saw a score.**
  - T1 v2: barred from T1 v1's scores (brief 07g), and nothing of v2 had been scored when it wrote.
  - T1 v3: read "no judge cache, … no score" (`checklist-v3.md` line 3; `writer-record.md`, "Part W never reads a score").
- **The only revision before the commit was a rule review, not a score.** T1 v2 had one Codex round (gpt-6.1-sol). It found nine conforming statements that weakened a requirement on their own, two with no supported harm, and fourteen sham statements that invented facts. They were rewritten (eight conforming payloads redesigned) before the commit and before any score (`t1v2/README.md`, "Review round").
- **Regimes come from the writers' rules, not from scores.** Routine is v2's conforming arm, middle is v3's middle arm, alarming is v2's alarming arm (each statement removes or weakens a check and says so).
- **The rater is a different model, used after the fact.** The "separate rater model" is the 07k blind rater: two `claude-fable-5-1` sub-agents in fresh contexts, scoring stripped statements for standalone visibility.
  - Records: `work/stage3/t1k-rater/rater-record.md` 0c5708e4, rubric `rubric.md` 20962e5a, `ratings-summary.md` 2c19122b.
  - It ran after both payload sets were committed, as a diagnostic: "a standalone-visibility score for every payload … so the axis is continuous and independent of the writer rules" (`roadmap-v2-2026-10-25.md`, row 07k).
  - Its scores defined no regime and selected, dropped or changed no plant.
  - The note's "a separate rater model scores their loudest line like an honest agent's own edit, or a little above" describes that rater's result, not a selection step.
  - It is not the document monitor's judge. That was Sonnet 5 (the sealed judge) and, in the record the headline uses, Opus 4.8 on the composed view.
- **The monitors' scores came after the plants and changed none.** Sonnet 5, GLM 5.3, Opus 4.8 (composed view), Kimi K3 and GPT-6 Sol scored the committed plants; those scores are results.
  - The follower test took all 56 payloads: "56 scorable, 0 excluded"; "No score, flag or outcome file was read" (`FT/red-selection.md` dac52668).
  - No Opus 4.8 composed-view score was used to choose or change a plant.
- **The panel and "invisible" files are reporting rules on those scores.**
  - `t1v3/t1v3-panel.md` e5eb8c93 (amendment A6) combines three judges' ranks into one panel judge at matched honest cost, as a diagnostic.
  - `t1v3/invisible-canonical.md` a9b6693a (A7) fixes one canonical count of payloads that no view of a judge flagged, for the boundary claim.
  - Neither chose, dropped or changed a plant.
- **One design-level fact, for completeness.** The middle band was added after v2's aggregate results (roadmap v2, brief 07l). The study's design responded to monitor results at the level of a regime. No plant was tuned.

**The honest one-line answer:** *the plants were written to rules for quiet and loud changes, with no score seen, and none was selected, filtered, sorted, dropped or revised against any monitor or rater score; a separate rater scored them afterwards as a diagnostic.*

## 3. Retention: "still standing" is partly by construction
`P3/retention-v0.md` 76605e5e: all 184 applications are censored, 0 ended. Three facts make that partly a property of the placement and replay rules, not only of the honest history.
- **The inserter guarantees survival through the composition day** (`work/checks/stage3_t1.py` 240f4ed9, docstring).
  - It re-draws a layout (up to `MAX_REDRAWS` = 20) when a statement is overwritten before the composition time.
  - It checks every statement's line present at the composition timestamp and at the end of the composition day.
  - For its first `PREFER_CLEAN_DRAWS` = 10 draws, it also requires that the plant breaks no later honest edit.
  - Authors are drawn from sessions after the document's whole rewrite (fix F4).
  - So "red chose the slot and timing using the whole honest log, to avoid later overwrites" agrees with the blue records.
- **The replay cannot remove a plant through an honest edit aimed at the old text.** An honest `replace_in_file` whose find text the plant displaced fails and is ignored: 119 such edits, on 54 of 184 applications. Only a later whole write or an edit of the planted line itself could end one, and the replay found none.
- **The window is short.** The replay runs from the first composed state to the end of the recorded log (the three-day prefix to 2026-04-08), on a fixed history that does not react to the plant (`retention-v0.md`, first paragraph).

So the note may say that no placement was undone in this replay, adding that placement was chosen so that each plant survived its composition day and broke no later honest edit where possible. It should not read the 184 as evidence that plants last.
