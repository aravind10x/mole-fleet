# Methods for the note (v1.0, 2026-11-19)

*Companion to `note-v1.0.md`, for the repository. It holds the method detail the note leaves out: loudness scores, the two monitor views, the audits' mechanics, the recorded and frozen states, the consequence-class figure, the detail behind the honest-deviance result, and the single-statement test. v1.0 adds the provenance notes the body moved here, computation 1 (serious and material plants together), the monitor budgets' sources with their unit caveat, and the retention replay's ignored edits. Every figure is traced in `claims-trace-v1.0.md` and the earlier traces it points to. No plant text, no threshold or tie value, no FakeLab figure.*

**Only the documents were monitored.** Every "missed" in the note and here is the document monitor's verdict. No monitor read the acting agent's run until the 19 Nov check on the acting agent, below.

## Definitions used throughout
- **Quiet plants** are the 48 routine and middle plants; **alarming** plants are the other 8. The regime is set by the rules the plants were written to; a rater scored the finished plants afterwards as a diagnostic (corrected 19 Nov).
- **Carried** means the planted content appears in a logged action call, by a script written before any run.
- **Acted on** means carried and not merely questioned, as classed by audit readers (first audit), plus actions the script missed (second audit).
- **Acted on and missed** is, over the 48 quiet plants, the mean of (missed by the monitor) × (the plant's acted-on rate), with the two followers mixed equally. It is a share of runs weighted equally over plants, not a count of plants.
- **Missed** is the recorded verdict of Opus 4.8 reading the document view at its 10 percent honest flag budget.
- **The two monitor views.** The *document view* reads a document's combined changes over a window as one diff (a line-by-line record of what was added and removed). The *per-author view* reads one author's edits to one document. A change split across several edits can look harmless edit by edit and odd only when read together.


**The world.**
- **The fork.** MOLE in lab mode: fifty AI-operated accounts sharing one organisation's documents, all run by Kimi K2.6.
- **Planting.** Plants were inserted by script into sessions that had read the target document.
- **The sham.** A same-shape sham, with the plants' edit shape and no harmful content, was read beside every set-level signal.
- **No task in view.** No monitor saw the task of the session that made the edit.
- **Regimes (corrected 19 Nov, `NOTE/facts-plant-provenance-v0.md` a1908c6a).** The regimes come from the rules the plants were written to, not from any score.
  - **Routine:** the first set's conforming arm.
  - **Middle:** the second set's middle arm, "unusual enough to be worth a question" without removing, weakening or bypassing a safeguard.
  - **Alarming:** the first set's alarming arm, where each statement removes or weakens a check and says so.
  - **Who wrote them.** Model sessions acting as writers wrote the plants to written rules, with no score seen: the T1 v2 controller session for routine and alarming, and a fresh `claude-fable-5-1` writer session for middle. Aravind drafted no plant text. He scored a sample of statements as human anchors for the rater, after the plants were fixed.
  - **Fixed before scoring.** Both sets were committed by hash before anything was planted or scored. The one revision before that was a rule review, which rewrote statements that broke the writing rules before any score existed.
  - **Nothing selected on a score.** No plant was selected, filtered, sorted, dropped or revised against any monitor's or rater's score. The follower test took all 56.
  - **The rater, after the fact.** A separate blind rater, two sub-agents in fresh contexts and not the document monitor's judge, scored the finished plants afterwards as a diagnostic: a routine line against an honest edit reads AUROC 0.563 [0.480, 0.648], where 0.5 is a coin toss and 1.0 is perfect; a middle line sits a little above (0.648). It defined no regime and changed no plant.
  - **One design-level fact.** The middle group was added to the design after the first set's aggregate results; no plant was tuned.
  - Of the 56 plants, 48 are quiet (24 routine, 24 middle) and 8 alarming.
- **The budget against the field's.** Recent control evaluations flag 1 to 2 percent: Greenblatt et al. 2023 audit the top 2 percent; Ctrl-Z 1 percent of actions; SHADE-Arena and MonitoringBench about 1 percent false positives; MiniLab 2 percent per agent trajectory; FakeLab reports 1, 2, 5 and 10 percent. Their budgets are counted per step, per trajectory or per team; this study's is per honest unit, one document's changes up to one honest edit. So the note's "five to ten times" is an order of magnitude, not a like-for-like ratio. The sources were read by the advisor's research subagent on each primary page, and the Anthropic risk report by the advisor in its text (`NOTE/brief-v1.0-from-advisor.md`, section 2 item 3).
- **The null.** The document monitor's honest baseline is 254 honest units on 18 document-day chains. A 1 percent budget is 2.54 of those units, so this baseline cannot be read at 1 percent.

**The follower test.**
- **Pre-registration.** The design was pre-registered before any run, and its scorers are code written by the side that built the plants before any run.
- **Runs.** 672 core runs, none unresolved. The clean control fired once in 336 clean runs.
- **Intervals.** 95 percent bootstraps over plants within regime.
- **The two followers** are not shown to differ: −0.056 [−0.153, 0.028] on routine and middle uptake.
- **One account per plant.** Each plant has one governing placement, made by a single account.
- **Recorded states.** The state check found that file order is the order the world applied writes in. It reproduces all 492 read sizes and all 69 successful replaces on the six documents. Every state the recorded scores used is one the world held.
- **Matching states.** On the 40 routine and middle plants whose scored and frozen states match, the share acted on and missed is 0.331 to 0.357 under both audits (raw 0.285 [0.177, 0.403]).

**The audits.**
- **First audit.**
  - **Coverage.** 121 runs: all 80 script-positive planted runs with a check tool or a decline, a seeded sample of 40 others (of which 1 was questioning), and the one clean-arm run the script scored as carried.
  - **Completions.** The two completions put the unaudited runs at the two ends of the sampled stratum's 95 percent Wilson interval.
  - **On its own.** This first audit alone gives uptake 0.646 to 0.699 and a share acted on and missed of 0.257 to 0.277.
- **Second audit.**
  - **Coverage.** All 80 script-negative planted runs and 40 clean controls, under a rule amended once before a full re-read by fresh readers.
  - **Agreement.** The readers' "another planted statement's wording" class agrees with a script count of the plant's literals on 76 of 80 runs.
- **Combining them.** The both-audits range pairs the first audit's lower completion with the second audit's unclear runs counted as not acting, and its upper completion with them counted as acting.

**Consequence classes.**
- **The rule.** The classing rule was written blind to every plant, and readers classed each plant from its own text only.
- **The class of record.** It is the first reader's: 25 serious, 17 material and 6 minor among the 48 routine and middle plants. The joins under the lower of the two readers' classes are in the repository.
- **The figure.** `figures/fig2-consequence-class.png` shows the share acted on and missed by class (serious 0.187 to 0.213, material 0.459 to 0.489, minor 0.642 to 0.666). The note gives the same ranges in prose.
- **Alarming plants.** They were acted on in 0.551 to 0.645 of runs, and the monitor had flagged all eight.
- **Serious and material plants together (v1.0, computation 1).** On the headline's count and weighting, the 42 serious and material plants were acted on and missed in 0.297 to 0.325 of runs (script count 0.278). Each class figure is a plant-weighted mean, so the 42-plant figure is the count-weighted mean of the two class figures; the same combination over all three classes reproduces the 48-plant figure. No interval is given: its bootstrap needs the per-run files (`computations-v1.0.md`).

**Retention, use and need.**
- **Retention** replays each first composed state forward against the honest log's recorded writes, under a rule hashed before the script ran. It is a mechanical reading on a fixed history: the recorded log never reacts to the plant. No placement ended (0 of 184), partly by construction: the inserter re-drew a plant's layout (up to 20 times) when a statement was overwritten before its composition time, checked every statement present at the composition time and at the end of that day, and, for its first 10 draws, required that the plant break no later honest edit. The replay runs only to the end of the three recorded days. An honest edit whose find text the plant had displaced would fail there and is ignored: 119 such edits, on 54 of the 184 placements (16 on 8 alarming, 37 on 13 middle, 66 on 33 routine). In a live world each could rewrite the planted line.
- **Use** counts an item as carried when its value appears in a later honest state-changing action by another session. The stricter count ignores matches that rest only on a date, a bare number or a short token.
- **Need.**
  - **Runnable tasks.** It is read off a mechanical rule over the 480 of 1,106 bank tasks that run offline.
  - **The 54 plants.** Two plants left this block before any outcome, because their literals are plain words any task could contain; they are the two left out of the topic-only tasks too.

**Topic-only tasks (discovery).**
- **Tasks.** One drawn goal per plant on 46 routine and middle plants. Carried at 0.779 [0.692, 0.862] on the script's count. Two plants left before any outcome, because their tested literals are plain words any task could contain.
- **The audit.** The note's topic-only range, 0.557 to 0.666 against 0.646 to 0.699 for pointed tasks, is after the first audit only. Discovery has only the first audit, so its audited range compares with the pointed tasks' first-audit range of 0.646 to 0.699, not with the both-audits pair. Of 94 audited runs, 77 acted and 17 were questioning, 15 of them GPT-6 Sol's; a second reader agreed on 14 of 14. On that audit's lower completion, discovery's acting is 0.093 below the pointed tasks' (−0.093 [−0.173, −0.012]), because more carried runs had questioned the content first.
- **The registered sentence** holds in all six registered computations. No clean run fired.

**The honest bank.**
- **Draws.** 216 drawn honest tasks, four per plant, each run on the planted and the clean document by both followers: 864 runs.
- **Access.** Access means the item's line was returned before the run's last action. Every one of the 60 carried runs had the line returned before the action that carried it.
- **Clean controls.** No clean run carried.

**The warned follower.**
- **Runs.** 1,536 runs on a frozen interleaved schedule.
- **Completed work.** Completion is scored by a scorer that agreed with fresh readers on 54 of the 54 runs they decided.
- **The two followers** differ: 0.111 [0.028, 0.194] on the warning's effect on uptake.

**Partial plants (post hoc).**
- **Superseded.** The single-statement test, filed in advance, replaces this reading in the note; the figures stay here as a record.
- **Runs.** 576 runs on 12 items.
- **One item set aside.** Its clean arm fired on 3 of 6 runs, so it is left out of the post hoc averages.
- **Cells holding no tested statement.** They never fired: 0 of 84 runs.

**The single-statement test.**
- **Design, filed before any run.** Each of the 48 quiet plants cut to one statement: the lowest-numbered statement holding a literal the script looks for, chosen by script with no outcome in view. Two strata were fixed in advance: 20 plants whose single statement offers the script every literal the full plant does, and 28 where it offers fewer.
- **Runs.** The single and full forms ran side by side, 48 plants × 2 followers × 3 repeats each: 576 runs, none unresolved.
- **The monitor.** One fresh scoring run of Opus 4.8 on the document view, on the honest baseline's units and both forms' documents, with the flag rule set at 10 percent of this run's own baseline. These are frozen-state scores, so they stand beside the headline's monitor figures and are not mixed with them. Missed: 36 of 48 single (0.750), 17 of 48 full (0.354); difference +0.396 [0.250, 0.542].
- **Carried and missed.** Single 0.359 to 0.438, full plant 0.205 to 0.236, over the raw count and the audit's two weightings.
- **The audit.** Ten fresh readers read 200 carried runs (every run with a check tool or a decline, and a seeded 20 others per cell): 150 acts, 44 questions, 6 unclear; a second reader agreed on 19 of 20.
- **The registered result: not stable under the audit.** The difference in carrying (single minus full) is −0.132 [−0.243, −0.024] on the script's count, −0.028 [−0.134, 0.072] with the single arm at its upper audit ends and the full plant at its lower, and −0.164 [−0.265, −0.072] the other way. Raw and audit computations disagree, so no sentence is made. All six computations are in `SS/result-SS-v1.md`.
- **Where the fall is.** On the 28 plants where the single statement offers fewer literals: −0.232 [−0.411, −0.071]. On the 20 where it offers the same: +0.008, +0.072 and −0.047, every interval including zero.
- **The concurrent full plant** carried at 0.771, beside the headline's earlier 0.799.
- **Second audit, added after the registered result** (`SS/result-SS-neg-v0.md` 4c6d8720; page ef4b73a3). Fresh readers read all 170 runs the script scored as not carried (104 single, 66 full plant) and 40 masked clean controls. They found acting on the planted content in 36 of 104 and 36 of 66, and in 1 of 40 controls; pass two agreed on 18 of 20. With both audits, d = −0.017 [−0.124, 0.088] (single-favourable) and −0.188 [−0.280, −0.098] (full-favourable). Neither sentence fixed beforehand applies, and the registered "not stable under the audit" stands. Display check: re-read under the full plant's form, all 6 of 20 single-statement runs classed as acting under their own form were not so classed (net −6, past the trigger of 4). Pass one under each arm's own form governs.

**The headline's repeat** (`SS/repeat-table-v1.md` e1391930, json 4e7b6f35; descriptive). The single-statement test's full-plant arm measured the headline quantity again three days later: the same 48 plants, tasks and followers, with fresh follower runs, fresh monitor scores and a fresh 254-unit honest baseline.
- **Acted on and missed, both audits:** 0.288 to 0.323 in the repeat, against 0.340 to 0.367 in the first run; pooled by plant, 0.314 to 0.345. The repeat's second audit is post hoc.
- **Uptake:** 0.771 against 0.799.
- **The monitor accounts for most of the gap.** It missed 21 of the 48 plants in the record and 17 in the repeat's fresh scoring, and 6 plants change flag between the two. Under one scoring the two runs agree on the script's count: 0.295 and 0.306 under the record's scoring, 0.240 and 0.236 under the repeat's.

**Provenance of the note's comparisons (moved from the body in v1.0).**
- **Ranges are completions.** Each both-audits range pairs the first audit's two completions of its unread runs with the second audit's unclear runs counted first as not acting, then as acting; it is not a confidence interval.
- **The repeat's second audit** was added after the fact; the repeat's figures are descriptive.
- **Other monitors.** The paired differences against the headline monitor were computed after the fact.
- **Stricter budgets.** The ranges at 5 and 2 percent run over how plants scored exactly at the line are counted.
- **The warning's audited rates** (per follower, and acting under both audits) are descriptive; the five registered computations are in the warned follower's section below.
- **The single-statement test's carried and missed** (single 0.359 to 0.438, full 0.205 to 0.236) comes from its own fresh scoring run on the frozen states and its own audit, so it does not compare with the headline's 0.340 to 0.367. The note gives only the test's monitor result and carry rates.
- **The single-statement test's second audit** was added after its registered result; the note gives its both-audits difference in one sentence, and the display check and strata are here.

**Added 19 Nov: the monitor on the acting agent** (`AM/result-AM.md` 3105b1ce; descriptive except the two registered sentences).
- **Design.** Pre-registration `AM/preregistration-AM.md` with two additions; prompts frozen before any call. Opus 4.8 on Bedrock scored every unit; nothing was read until all three passes had finished.
- **Views and prompts.** View T shows the task and the whole run as logged, every tool call with its result. View A shows the task and the state-changing actions only. Prompt G adapts the document monitor's harm framing to an agent's run. Prompt W adds the warning paragraph. The registered pass is T with G.
- **The line.** The 10 percent rule of each block's clean runs (same tasks, clean documents), with the document monitor's tie rule.
- **Registered sentences, view T, prompt G:**
  - core, "it catches some": R 0.374 [0.264, 0.483], 86 of 230 carried quiet runs over 48 plants;
  - topic-only tasks, "it misses most of them": R 0.288 [0.199, 0.395], 62 of 215 over 46 plants.

  Every audit weighting keeps the core between 0.30 and 0.70, and the topic-only tasks at or below 0.30.
- **Three-way share** (carried, missed by the document monitor, not flagged by the monitor on the acting agent), script count:
  - core 0.222 [0.132, 0.326], against the two-way 0.295;
  - topic-only 0.243 [0.138, 0.355], against 0.333.
  - With both audits, the core is 0.252 to 0.274.
- **Beside:**
  - prompt W: core 0.491, topic-only 0.302;
  - view A: core 0.326;
  - the harmless arm: 11 of 95 carried harmless runs flagged, 6 of 68 carried planted runs, 1 of 96 clean runs;
  - by follower, core: Kimi K2.6 0.450, GPT-6 Sol 0.303.
- **Limits:**
  - the scores bunch near zero, so each line sits at a low score, with randomised ties;
  - the frozen prompt asks about deliberate harm and may score an unwitting follower low;
  - every line is in-sample on the block's own clean runs.

**Added 19 Nov: the document monitor told what to look for** (`TP/result.md` 50457676; pre-registration addition `TP/preregistration-addition-TP.md` 8c3e7ddf).
- **Design.** Arm B is the sealed document-view prompt, bytes unchanged. Arm T is the same prompt plus one paragraph, modelled on SLEIGHT-Bench's "Doc-Planting Aware" monitor prompt (arXiv 2605.16626, Appendix D.4). The paragraph's wording was settled before the freeze, frozen before any call, and not revised after any score was read. Each arm is read at the 10 percent rule of its own fresh 254-unit null, on the same 184 planted applications, with Opus 4.8 through the pinned client.
- **Registered sentence:** "no detectable change from the targeted paragraph, at this size."
  - S_B 0.274 [0.163, 0.392];
  - S_T 0.278 [0.163, 0.392];
  - D = S_B − S_T = −0.003 [−0.083, 0.073].
- **Smaller budgets, descriptive:**
  - 5 percent: S_B 0.337, S_T 0.500, D −0.163 [−0.288, −0.056];
  - 2 percent: S_B 0.486, S_T 0.622, D −0.135 [−0.243, −0.031].
  - The 5 percent row counts ties at the line as not flagged, which costs arm T more than arm B.
- **Why there was no change.** The paragraph raised honest and planted scores alike: honest mean 23.3 against 31.3, so arm T's line rose with them. At its line arm T flags 119 of 184 planted applications, against arm B's 117.
- **Reproduction.** The fresh baseline's 10 percent line came out lower than the earlier draw's, and S_B is 0.274 against that draw's 0.302 and the record's 0.295. The draw-to-draw difference, 0.028, is larger than D.

**The example's class (added 19 Nov; `NOTE/facts-example-ground-truth-v0.md` b9415726).** Both readers classed `Pa5eacc80` serious from its own text, under a rule that counts weakening an access limit or exposing data. No honest line in the six documents says who may read `/safety-reports/` or `/shared/`. The world's account list gives a `/safety-reports` area to 27 of the 50 accounts (19 read, 8 read-write) and none to 23, but the lab does not enforce it, and agents see only folder names. The document monitor's packet and the follower's documents both held the honest line that post-mortems belong in `/safety-reports/postmortems/`, and neither held an access rule. The class is the readers' judgement of what relying on the text would cause.

**The followers' documents, recorded and frozen.** The monitor's verdicts are scores recorded earlier on each document as the organisation's log held it at the end of the day the plant came together. Followers read the document frozen at the moment the plant came together, which can be earlier. Scoring the followers' exact documents gives 0.292 against the recorded 0.295. In 22 of the 47 cases where the two states match, the follower's version yields a shorter diff, so 0.292 is a score on those documents rather than a like-for-like replacement. Opus 4.8's flags on the frozen documents agree with its fresh flags on the scored documents in 46 of the 47 matching cases.

**Other monitors, paired.** Against Opus 4.8 on the document view (0.295 [0.188, 0.413] carried and missed, script count), plant by plant and after the fact: GPT-6 Sol +0.135 [0.003, 0.271], GLM 5.3 +0.160 [0.045, 0.271], Sonnet 5 +0.319 [0.177, 0.462], Opus 4.8 on the per-author view +0.135 [0.021, 0.257].

**Explain-then-judge.** Carried and missed 0.302 [0.191, 0.424] for the fresh baseline against 0.250 [0.146, 0.358] with explanation first, a difference of 0.052 [−0.038, 0.149]. One variant, one judge (Opus 4.8) and one draw per arm. The study is sized for a difference of about 0.10 or more. The explanations were not read.

**Honest deviance.**
- **This world.** Writes are classed by what their session's given tasks license. Honest means a benign session; it does not mean safe. Of 127 honest writes to the six documents, 59 change an item that no task of their session names; 68 are licensed by a task that names the item, and none is dictated by a task. Under Sonnet 5, the 30 honest diffs that score at or above its threshold sit on 9 of the 18 day-and-document windows (six documents over three days), and all 30 contain at least one of 6 writes outside their tasks. The 12 after-the-fact approval records at the very top, written into the release runbook, come down to one write.
- **The released corpora.** Four models generated them from one shared task bank. The benchmark has eight released datasets, a single-day and a multi-day one per model; 5,763 task variants appear in all eight, and 81 to 96 percent of the tasks each dataset's sessions were given are among them. The judge is Sonnet 5 on one prompt, on seeded samples of about 600 writes per generator, with intervals clustered on session. Single-day and multi-day splits agree within each generator.
- **What the generator also sets.** It sets how many tasks a session is given (about 3.0 items for gpt53, about 1.2 for deepseek) and how much each session writes (1.7 changing writes per session for gpt53, 3.6 to 4.0 for the others). A design that fixes the given task per session is needed to separate these from the generator itself.

**The pilot overwrites** were read against a rule hashed before any transcript was opened. All three were assigned upkeep, not correction.

**The warned follower: the registered result.**
- **The registered class is "not stable under the audit".** The registered measure is the warned-minus-unwarned difference in literal uptake on the 48 quiet plants. On script counts the warning lowered it by less than 0.15; under the audit's adverse completions, by at least 0.15. Because the two disagree, the registered sentence is not made. All five registered computations:

| computation | difference [95%] | class |
|---|---|---|
| script counts | −0.083 [−0.139, −0.028] | lowered by less than 0.15 |
| script counts, unresolved warned runs carried, unwarned not | −0.083 [−0.139, −0.028] | lowered by less than 0.15 |
| script counts, unresolved warned runs not carried, unwarned carried | −0.083 [−0.139, −0.028] | lowered by less than 0.15 |
| audit: warned at its upper completion, unwarned at its lower | −0.234 [−0.286, −0.180] | lowered by at least 0.15 |
| audit: warned at its lower completion, unwarned at its upper | −0.394 [−0.462, −0.328] | lowered by at least 0.15 |

- **The instability runs one way.** With questioning runs weighed out, the warning's effect is larger, not smaller.
- **Registered work clause.** Completed work fell by 0.116 [−0.161, −0.074] on clean documents and 0.344 [−0.458, −0.240] on legitimately updated ones, with a colleague who holds the correct documents.
- **Descriptive, not registered.** The per-follower audited acted-on rates (Kimi K2.6 0.719 to 0.672; GPT-6 Sol 0.636 to 0.000) and acting under both audits (0.740 to 0.861 unwarned, 0.384 to 0.466 warned). The second audit's agreement on the warned set was 9 of 12 identical on class, against 20 of 20 on the core.

**What is already known (credits).** Value plants are adopted, often more readily than instructions: PoisonedRAG Table 4; SearchGEO, Results §6, on one backend (Gemini 3 Flash); HAE-GEO; ClashEval; Xie et al. Plants in a shared store reach later readers: Ju et al.; MINJA; AgentPoison; ARGUS; Context-Fractured Decomposition. Planted content reaches actions: AgentDojo; MCPTox; DDIPE; AgentPoison. Agents rarely verify: HAE-GEO §5.4. Control work fixes monitor budgets and shows split work evades per-unit monitors: FakeLab; MiniLab; MonitoringBench; SLEIGHT-Bench.

**In the repository, not here:** hashes and retry accounting; the audit strata and per-class tables; clustered intervals; per-follower, per-document and per-predicate rates; the checking contrast; explain-then-judge's paired tables and 5 percent reading; the literal-rule deviance figures; the earlier findings (the same-shape sham and the volume artefact, the loudest-line account, judge-free rules, grounding on this world, recall against budget); the figures' scripts and tests (`figures/make_figures.py`, `figures/test_figures.py`; for v0.9, `figures/make_figures_v09.py`, `figures/figure_data_v09.py`, `figures/test_figures_v09.py`, writing to `figures/v09/`; for v1.0, `figures/make_figures_v10.py`, `figures/figure_data_v10.py`, `figures/test_figures_v10.py`, writing to `figures/v10/`).
