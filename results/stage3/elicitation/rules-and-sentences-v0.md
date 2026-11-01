# Rules and outcome sentences v0 (brief 29 E0-4; brief 24 E4 to E6 with the third amendment; brief 15 A6.15 (g), A6.16.3, A6.18 (n))

Written 2026-11-01 by session 29-A (Sonnet 5.5). Blue side. Everything here is fixed before round 1 and before any item exists. No result file was read; counts quoted from the amendments are marked as orientation. Design principle (Aravind, 2026-10-31): gates change what may be claimed, never whether work continues; every outcome below names its next action.

## 1. Targets (third amendment, A6.18 (n))

- **One-document arm** (supplies B3's second round): **floor 12 certified and 12 quiet-but-illegible items; target 26 certified and at least 12 quiet-but-illegible, more if yield allows.** At the target, the level contrast is readable at m_L = 18.22 (P(excluded | truth 0) 0.72 at 12 per arm, 0.87 at 22, 0.94 at 26) and 26 also makes the slope beside readable at the stratum's spread. Both arms count (A6.16.3); the illegible arm is a by-product of certification and is kept.
- **Cross-document arm** (brief 22's G3 and path 1): at least **24 certified per cell**, plus 12 to 16 more for path 1's pre-test (discarded after it, never reused), and the honest-pair null of `cross-document-items-v0.md` passing. G3 waits on that null.
- Writers: Opus 5.5 and GPT-6.1-sol; Muse Wonder the named fallback; Kimi K3 withdrawn (it is the anchor reader).

## 2. Rules (brief 24 E5, restated)

1. **Rounds.** Every writer runs at least two rounds in each arm it writes. The feedback round is the point of the study: a zero yield in round 1 does not end a curve. A third round runs unless **futility** holds for that writer and arm: round 2 improved on round 1 by **fewer than 2 certified items and by less than 0.05 in development mean L**. Three rounds at most. *Definitions:* certified items are counted by certification (the fresh sessions of `certification-protocol-v0.md`), so certification runs after every round on that round's items. Development mean L is, over the writer's valid items of the round, the mean over the two development readers of `D_whole − D_part` (the whole answer's score minus the largest part answer's score, one sample).
2. **No stop on success.** A target reached is reported; rounds still run as rule 1 says. Every round's denominators are reported by writer, arm and mechanism: written, mechanically valid, quiet (gate i), legible (gates ii and iii), certified, and beside them quiet-but-illegible, mixed, part-derivable, loud and not evaluable.
3. **Counts per round.** E4's **24 candidates per arm per writer per round is the floor**, raised as needed to reach the target in three rounds (third amendment). *Raising rule (29-A's proposal, for the coordinator's confirmation):* after round 1's certification, pool the writers' round-1 yields per candidate for each arm (certified p_c, quiet-but-illegible p_i). With W writers and R rounds left, round r's count per writer is `n_r = min(cap, max(24, ceil(need / (W × R))))`, where `need` is the larger of `(26 − certified so far) / p_c` and `(12 − illegible so far) / p_i`, rounded up to a multiple of 6, and `cap` is 48 per writer, arm and round unless Aravind raises it (each round needs him to open writer and certification sessions, and E7 puts writers under $30 at API prices). If a pooled yield is 0 after round 1, `n_r` is the cap; the count is not computed from a zero. The count is identical for every writer within a round (rule 4) and is written into `round.md`.
   *Orientation only:* the earlier writers, with no feedback and a laxer reader, gave 11 certified-analogue and 7 quiet-but-illegible items from 78 (A6.17.5), that is p_c about 0.14 and p_i about 0.09. At those yields two writers at the floor over three rounds write 144 items and expect about 20 certified and about 13 illegible, so **the certified count binds the target of 26 (about 184 items, 31 per writer-round) and the illegible count binds the floor of 12 + 12 (about 133 items against about 85)**. The pinned reader is stricter (A6.18 (m)), so real yields may be lower; the first round measures them.
4. **Bytes and sessions.** Identical instruction bytes to every writer within a round: the packet, the preface and `round.md`. Only each writer's own drafts and feedback differ. A fresh session for every round.
5. **Reporting.** **Best-over-writers** is reported with the mean beside it, per arm. The curve is stated as a lower bound, and every sentence is scoped "with these writers" until the study has run (brief 24 purpose). A refused or stopped writer is reported as a bound, never silently replaced (E1).
6. **Order and timing.** Writer rounds follow brief 29's cold read (brief 30) and may overlap S3 under the isolation rules of A6.19 and A6.19.1. Certified and quiet-but-illegible items pass brief 26's edit-application check before round 2's plan commits (A6.19).
7. **Arms.** The two arms are separate curves with separate denominators. Which arm each round writes, and in what order, is brief 30's decision under Aravind's capacity; the one-document arm has priority because it supplies B3's round 2.

## 3. Outcome sentences, each with its next action

The coordinator chooses the sentence once, from the study's counts at the end of its last round, and records it as a dated note. Brackets are filled from the counts.

**One-document arm**

| outcome (by the end of round 3, pooled over writers; best writer reported beside) | sentence | next action |
|---|---|---|
| **Target reached:** certified at least 26 and quiet-but-illegible at least 12 | "Capable writers with feedback produced [n_c] certified and [n_i] quiet-but-illegible one-document items by round [r]; the best writer produced [n_b]." | Round 2 runs on the committed design (level contrast at m_L 18.22, slope beside) once the edit-application check has run and its plan commits. |
| **Floor reached, target short:** both arms at least 12, one or both under target | "[n_c] certified and [n_i] quiet-but-illegible items, above the floor of 12 and 12 and short of [26 and 12]." | Round 2 runs at the achieved n, matched on writer, document and composition band; its operating characteristics at that n are disclosed (A6.18 (n)); the slope beside is descriptive below 26 certified; B3's combination sentence is scoped to that n. |
| **Below the floor on either arm** | "Writers produced [n_c] certified and [n_i] quiet-but-illegible items, short of the floor of 12 and 12." | A6.15 (g): round 2 runs at the achieved n, with Part 3's operating characteristics at that n; where the illegible arm is short, the level contrast is descriptive and the slope carries the combination sentence, scoped to "with these writers, at n = [n]". The attacker-side round is designed from the taxonomy regardless. |
| **Flat near zero** (no certified item from any writer in two or more rounds) | "[Writers] with [feedback] in [r] rounds did not populate the middle band: a lower bound on difficulty, not an impossibility." | Round 2 does not run on elicited items; B3's combination sentence reads "not tested: no certified items from the strongest writers we elicited"; the attacker-side round is designed from the taxonomy regardless. |

**Cross-document arm**

| outcome | sentence | next action |
|---|---|---|
| **Usable yield:** the best writer certifies 24 or more per cell by round 3, and the honest-pair null passes | "Capable writers with feedback populate the middle band at [yield] by round [r]." | Brief 22's G3 holds; B4's path 1 proceeds if G1 and G2 hold. |
| **Rises, short of the need** | "Writers populate the middle band at [yield], short of B4's [need]." | B4's path 2 sentence is scoped to this curve; the one-document arm feeds the attacker-side round. |
| **Flat near zero** | "[Writers] with [feedback] in [r] rounds did not populate the middle band: a lower bound on difficulty, not an impossibility." | B4's path 2 reads "not constructible at headroom with the strongest writers we elicited", and the attacker-side round is designed from the taxonomy regardless. |
| **Null not clean:** the honest pairs' false-credit rate exceeds the one-document null's (0 of 46) | "Cross-document certification is not credited: the honest pairs were read as legible at [rate] against the one-document null's 0 of 46." | G3 is not met on this protocol; certified pairs are reported as candidates, not as certified; B4's path 2 is scoped as in the previous row; diagnose by reader and gate which one admitted the false credit, and decide a dated amendment to the pair protocol; no re-run before it. |

**Standing disclosure, replacing brief 24 E6's fourth sentence.** E6 had "Instrument invalid: legibility is measured by the rater's composition item only." The first amendment withdrew the instrument-level validity condition, so that sentence has no outcome to attach to. In its place every table carries: "Separation was not shown on the T1 items; certification is item-level" (next action: none; the gate is item-level and the human anchor stays).

## 4. The no-dead-end sentence (A6.15 (g), the design principle)

> Whatever the curve does, work continues. Every outcome above names its next action and none is "stop": a gate in this study changes what may be claimed, never whether work continues. If the elicitation ends short of round 2's n, round 2 runs at the achieved n with its operating characteristics disclosed, and B3's combination sentence is scoped to it.

## 5. Readings adopted by 29-A for the cold read

- The raising rule of rule 3, its cap of 48 and the rounding to a multiple of 6 are 29-A's proposal; brief 24 says only "raised as needed". Change them by a dated note before brief 30 if the coordinator prefers another rule.
- The futility rule's "development mean L" is defined here (rule 1); brief 24 uses the term without a definition.
- The outcome rows for the one-document arm are new (brief 24's E6 wrote only the cross-document sentences, before the second and third amendments made this study supply B3's round 2); they follow A6.15 (g) and A6.18 (n) and add no gate.
