# Rules and outcome sentences v0 (brief 29 E0-4; brief 24 E4 to E6 with the third amendment; brief 15 A6.15 (g), A6.16.3, A6.18 (n))

Written 2026-11-01 by session 29-A (Sonnet 5.5). Blue side. Everything here is fixed before round 1 and before any item exists. No result file was read; counts quoted from the amendments are marked as orientation. Design principle (Aravind, 2026-10-31): gates change what may be claimed, never whether work continues; every outcome below names its next action. **v0.1, 2026-11-02** (a Sonnet 5.5 session under the authoring note; brief 29 dated note 6): p is defined per valid item written, and the orientation's denominator is said to understate it; `n_r` is the quantity rounded up to a multiple of 6; "writer round" names the elicitation study's rounds ("round 1" and "round 2" without "writer" are B3's rounds, as in the amendments); the cold read's cap table is added as section 6, with the cap named as Aravind's capacity call. No target, floor, rule's intent or outcome changed.

## 1. Targets (third amendment, A6.18 (n))

- **One-document arm** (supplies B3's second round): **floor 12 certified and 12 quiet-but-illegible items; target 26 certified and at least 12 quiet-but-illegible, more if yield allows.** At the target, the level contrast is readable at m_L = 18.22 (P(excluded | truth 0) 0.72 at 12 per arm, 0.87 at 22, 0.94 at 26) and 26 also makes the slope beside readable at the stratum's spread. Both arms count (A6.16.3); the illegible arm is a by-product of certification and is kept.
- **Cross-document arm** (brief 22's G3 and path 1): at least **24 certified per cell**, plus 12 to 16 more for path 1's pre-test (discarded after it, never reused), and the honest-pair null of `cross-document-items-v0.md` passing. G3 waits on that null.
- Writers: Opus 5.5 and GPT-6.1-sol; Muse Wonder the named fallback; Kimi K3 withdrawn (it is the anchor reader).

## 2. Rules (brief 24 E5, restated)

1. **Writer rounds.** Every writer runs at least two writer rounds in each arm it writes. The feedback round is the point of the study: a zero yield in writer round 1 does not end a curve. A third writer round runs unless **futility** holds for that writer and arm: writer round 2 improved on writer round 1 by **fewer than 2 certified items and by less than 0.05 in development mean L**. Three writer rounds at most. *Definitions:* certified items are counted by certification (the fresh sessions of `certification-protocol-v0.md`), so certification runs after every writer round on that writer round's items. Development mean L is, over the writer's valid items of the writer round, the mean over the two development readers of `D_whole − D_part` (the whole answer's score minus the largest part answer's score, one sample).
2. **No stop on success.** A target reached is reported; writer rounds still run as rule 1 says. Every writer round's denominators are reported by writer, arm and mechanism: written, mechanically valid, quiet (gate i), legible (gates ii and iii), certified, and beside them quiet-but-illegible, mixed, part-derivable, loud and not evaluable.
3. **Counts per writer round.** E4's **24 candidates per arm per writer per writer round is the floor**, raised as needed to reach the target in three writer rounds (third amendment). *Raising rule (29-A's proposal, for the coordinator's confirmation):* after writer round 1's certification, pool the writers' writer-round-1 yields for each arm (certified p_c, quiet-but-illegible p_i). **p is defined over the valid items written in writer round 1:** p_c is the certified items, and p_i the quiet-but-illegible items, divided by the valid items written, the quantity the next writer round measures again (not per rater-quiet candidate). With W writers and R writer rounds left, writer round r's count per writer is `n_r = min(cap, max(24, roundup6(ceil(need / (W × R)))))`, where `need` is the larger of `(26 − certified so far) / p_c` and `(12 − illegible so far) / p_i`, and `cap` is 48 per writer, arm and writer round unless Aravind raises it (each writer round needs him to open writer and certification sessions, and E7 puts writers under $30 at API prices). **`n_r` is the quantity rounded up to a multiple of 6** (`roundup6(x)` is the least multiple of 6 that is not below x); `need` is not rounded, and since the floor 24 and the cap 48 are multiples of 6, so is every `n_r`. If a pooled yield is 0 after writer round 1, `n_r` is the cap; the count is not computed from a zero. The count is identical for every writer within a writer round (rule 4) and is written into `round.md`.
   *Orientation only, and its denominator is too small:* the earlier writers, with no feedback and a laxer reader, gave 11 certified-analogue and 7 quiet-but-illegible items from 78 (A6.17.5), that is p_c about 0.14 and p_i about 0.09. The 78 are brief 25's **rater-quiet candidates**, not the valid items its writers wrote, so the orientation understates the denominator a yield per valid item written divides by, and overstates p as rule 3 defines it. At those yields two writers at the floor over three writer rounds write 144 items and expect about 20 certified and about 13 illegible, so **the certified count binds the target of 26 (about 184 items, 31 per writer round) and the illegible count binds the floor of 12 + 12 (about 133 items against about 85)**. The pinned reader is stricter (A6.18 (m)), so real yields may be lower still; the first writer round measures them, per valid item written.
4. **Bytes and sessions.** Identical instruction bytes to every writer within a writer round: the packet, the preface and `round.md`. Only each writer's own drafts and feedback differ. A fresh session for every writer round.
5. **Reporting.** **Best-over-writers** is reported with the mean beside it, per arm. The curve is stated as a lower bound, and every sentence is scoped "with these writers" until the study has run (brief 24 purpose). A refused or stopped writer is reported as a bound, never silently replaced (E1).
6. **Order and timing.** Writer rounds follow brief 29's cold read (brief 30) and may overlap S3 under the isolation rules of A6.19 and A6.19.1. Certified and quiet-but-illegible items pass brief 26's edit-application check before the plan for B3's round 2 commits (A6.19).
7. **Arms.** The two arms are separate curves with separate denominators. Which arm each writer round writes, and in what order, is brief 30's decision under Aravind's capacity; the one-document arm has priority because it supplies B3's round 2.

## 3. Outcome sentences, each with its next action

The coordinator chooses the sentence once, from the study's counts at the end of its last writer round, and records it as a dated note. Brackets are filled from the counts.

**One-document arm**

| outcome (by the end of writer round 3, pooled over writers; best writer reported beside) | sentence | next action |
|---|---|---|
| **Target reached:** certified at least 26 and quiet-but-illegible at least 12 | "Capable writers with feedback produced [n_c] certified and [n_i] quiet-but-illegible one-document items by writer round [r]; the best writer produced [n_b]." | B3's round 2 runs on the committed design (level contrast at m_L 18.22, slope beside) once the edit-application check has run and its plan commits. |
| **Floor reached, target short:** both arms at least 12, one or both under target | "[n_c] certified and [n_i] quiet-but-illegible items, above the floor of 12 and 12 and short of [26 and 12]." | B3's round 2 runs at the achieved n, matched on writer, document and composition band; its operating characteristics at that n are disclosed (A6.18 (n)); the slope beside is descriptive below 26 certified; B3's combination sentence is scoped to that n. |
| **Below the floor on either arm** | "Writers produced [n_c] certified and [n_i] quiet-but-illegible items, short of the floor of 12 and 12." | A6.15 (g): B3's round 2 runs at the achieved n, with Part 3's operating characteristics at that n; where the illegible arm is short, the level contrast is descriptive and the slope carries the combination sentence, scoped to "with these writers, at n = [n]". The attacker-side round is designed from the taxonomy regardless. |
| **Flat near zero** (no certified item from any writer in two or more writer rounds) | "[Writers] with [feedback] in [r] writer rounds did not populate the middle band: a lower bound on difficulty, not an impossibility." | B3's round 2 does not run on elicited items; B3's combination sentence reads "not tested: no certified items from the strongest writers we elicited"; the attacker-side round is designed from the taxonomy regardless. |

**Cross-document arm**

| outcome | sentence | next action |
|---|---|---|
| **Usable yield:** the best writer certifies 24 or more per cell by writer round 3, and the honest-pair null passes | "Capable writers with feedback populate the middle band at [yield] by writer round [r]." | Brief 22's G3 holds; B4's path 1 proceeds if G1 and G2 hold. |
| **Rises, short of the need** | "Writers populate the middle band at [yield], short of B4's [need]." | B4's path 2 sentence is scoped to this curve; the one-document arm feeds the attacker-side round. |
| **Flat near zero** | "[Writers] with [feedback] in [r] writer rounds did not populate the middle band: a lower bound on difficulty, not an impossibility." | B4's path 2 reads "not constructible at headroom with the strongest writers we elicited", and the attacker-side round is designed from the taxonomy regardless. |
| **Null not clean:** the honest pairs' false-credit rate exceeds the one-document null's (0 of 46) | "Cross-document certification is not credited: the honest pairs were read as legible at [rate] against the one-document null's 0 of 46." | G3 is not met on this protocol; certified pairs are reported as candidates, not as certified; B4's path 2 is scoped as in the previous row; diagnose by reader and gate which one admitted the false credit, and decide a dated amendment to the pair protocol; no re-run before it. |

**Standing disclosure, replacing brief 24 E6's fourth sentence.** E6 had "Instrument invalid: legibility is measured by the rater's composition item only." The first amendment withdrew the instrument-level validity condition, so that sentence has no outcome to attach to. In its place every table carries: "Separation was not shown on the T1 items; certification is item-level" (next action: none; the gate is item-level and the human anchor stays).

## 4. The no-dead-end sentence (A6.15 (g), the design principle)

> Whatever the curve does, work continues. Every outcome above names its next action and none is "stop": a gate in this study changes what may be claimed, never whether work continues. If the elicitation ends short of B3's round 2 n, B3's round 2 runs at the achieved n with its operating characteristics disclosed, and B3's combination sentence is scoped to it.

## 5. Readings adopted by 29-A for the cold read

- The raising rule of rule 3, its cap of 48 and the rounding to a multiple of 6 are 29-A's proposal; brief 24 says only "raised as needed". Change them by a dated note before brief 30 if the coordinator prefers another rule. The cold read adopted the rule (variance ignored); the cap is Aravind's call (section 6).
- The futility rule's "development mean L" is defined here (rule 1); brief 24 uses the term without a definition.
- The outcome rows for the one-document arm are new (brief 24's E6 wrote only the cross-document sentences, before the second and third amendments made this study supply B3's round 2); they follow A6.15 (g) and A6.18 (n) and add no gate.

## 6. The cap of 48 is Aravind's capacity call (the cold read's table, quoted)

The cap is a call on how many writer and certification sessions Aravind opens, not a design fact, and the table below is **the review session's expectation table, not a decision**: it says what the raising rule would do at assumed yields, and nothing in it sets the cap. Provenance: the independent read of 2026-11-02 (`work/stage3/elicitation/review/fable-read-29a-2026-11-02.md`, ruling 6, 3f4a413c), reconciled in the review session's `cold-read-29a-2026-11-02.md` (43b2f01b). It computed the raising rule with W = 2 writers, a floor of 24 and three writer rounds. "As quoted" is brief 25's yields (0.141 and 0.090); "0.5 ×" is the A6.18 (m) case, the pinned reader crediting parts about twice as often. Quoted as computed there:

| yields | counts per writer round | items | E[certified] | E[illegible] | result |
|---|---|---|---|---|---|
| as quoted | 24, 35, 36 | 190 | 26.8 | 17.1 | target met |
| 0.7 × | 24, 48, 48 (cap binds) | 240 | 23.7 | 15.1 | target short |
| 0.5 × | 24, 48, 48 | 240 | 16.9 | 10.8 | illegible arm below its floor |
| 0.5 ×, cap 96 | | | 26.2 | 16.7 | target met |

- **Reading the first row.** It was computed with the rounding on `need`, which is why 35 appears; with `n_r` rounded to a multiple of 6 as rule 3 now says, the counts are 24, 36, 36 (192 items, about 27 certified, the review session's section 1), and the target is still met. The rows where the cap binds are unchanged.
- **Reach of the cap.** A cap of 48 reaches the target only with p_c at least 0.108 and p_i at least 0.050, both per valid item written (rule 3).
- **When Aravind decides.** After writer round 1's yields, with this table. Until he raises the cap, rule 3 uses 48. A short result at the cap is an outcome row of section 3, not a stop.
