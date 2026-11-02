# §10 draft for the cold read: B3's round 1 (brief 13 A6)

*Written by the brief 13 writing session (Opus 5.5) under brief 13 Amendment A6 (665b44d9), from the four S3 files A6 permits:*
- *`b3/b3-results.md` a759aba4 and `.json` b496d422, tag* results;
- *`b3/b3-results-additions.md` e08891ac and `b3/s3-stage-b-v0.md` 30b761ae, tag* methods;
- *the plan, `b3/plan.md` 59a98c15, tag* pre-registration;
- *brief 22's dated note of 2026-11-02 (pinned 1d3c454f), for the gates.*

*Manifest 04648a6a. Files are relative to `work/stage3/`. This text replaces the draft's §10.1 placeholder once the review session has cold-read it. §10.2 (round 2) and §10.3 (the elicitation study) stay as they are.*

---

## 10. B3: does a per-agent view read the combination, or only the loudest line?

**What B3 tested.** Each test change is a three-line change, quiet line by line, applied by a lone author. The question is whether a per-agent content view's score for the whole change rises with the change's composition beyond what its loudest line alone earns. Under the max-type hypothesis (P-max) it does not.

**How round 1 read it.** The pre-registered plan names:
- **the carrier:** form (a) on Opus 4.8's isolated dossier;
- **a second instrument:** form (a) on Opus 4.8's zero-context `P_author`;
- **the carrier population:** the resolved-anchor subset, 17 items at layout T2+S2. The comprehension-quiet stratum (26) is the next step-down, and the full quiet set (73) is descriptive under the switch (§9.3).

B3's labels follow the plan's §5.3 on the excess scale, against m_s 18.22 for the carrier and 19.37 for the second instrument. They do not follow the Δ partition of §1 to §7 (pre-registration; `b3/plan.md`, §4 to §7). Every sentence below was selected by rule from the plan's §6 and is printed in `b3/b3-results.md`. All 4,344 analysis rows were complete, and the run did not stop (results; `b3/b3-results.md`, analysis lock).

### 10.1 Round 1's verdict

**With these writers, P-max is *inconclusive* in round 1 on the resolved-anchor subset (n = 17).** Under the carrier, the contrast is 3.9 [−7.5, 20.4] against m_s 18.22, an interval that cannot tell zero from the margin (results; `b3/b3-results.md`, S-F4 and S-D4).

The plan states, before any score: "under a true max-type null the carrier reads *holds* about two times in three (0.67), so a non-*holds* reading in round 1 is weak evidence and round 2 is the test" (pre-registration; `b3/plan.md`, §7, A6.18 (l)).

The carrier's upper bound misses m_s by about 1.4 to 2.2 points, with about 0.7 to 0.9 points of bootstrap noise on it (the seed sensitivity A6.18 (e) disclosed for the subset). The pre-registered seed's reading governs (brief 22, dated note of 2026-11-02).

**What else holds around the verdict:**
- **Both instruments clear their floor.** Each separates the quiet set from the sham: AUROC 0.79 [0.70, 0.87] under the carrier and 0.81 [0.72, 0.89] under the second instrument (results; `b3/b3-results.md`, S-A1).
- **The comprehension-quiet stratum (n = 26) agrees** under the carrier: *inconclusive*, 7.4 [−2.6, 18.3] (results; same file, S-I1).

### 10.2 Beside the verdict, never as it

- **The second instrument reads *excluded*, beside.** On the subset it reads 0.8 [−6.7, 7.5], and on the stratum 3.3 [−3.5, 10.2], both against 19.37 (results; `b3/b3-results.md`, S-Fs2 and S-D3).
  - This is not a verdict and not a headline. The verdict is the carrier's label, and a one-step difference between the two instruments is not a conflict under the plan's combination rule.
- **Items with no broken honest edit (S-G6), as numbers only.** Form (a) was re-read on the items none of whose applications broke a later honest edit (results; same file, S-G6). These are numbers with no label attached:

| instrument | subset (15 of 17) | stratum (23 of 26) |
|---|---|---|
| carrier | −2.0 [−10.9, 8.9] | 2.2 [−5.9, 12.4] |
| second instrument | −0.2 [−9.5, 8.2] | 2.0 [−5.2, 10.7] |

- **The certified stratum's excess level (S-M2).** The 10 items with mean composition at or above 75 (9 of them Sonnet-written) have a mean excess of 22.6 [10.9, 33.5] under the carrier, and lone recall 0.75 [0.50, 0.95] (results; same file, S-M2).
  - That is an excess level with no slope: the stratum's composition spread carries none.
  - It includes the max-of-three inflation of form (a).
  - It is not set against m_s.

### 10.3 The full quiet set: descriptive, diluted, leaning upward

On the full quiet set (n = 73), descriptive under the switch, both instruments' form (a) readings carry the label *attenuated* (results; `b3/b3-results.md`, S-D2 and S-J1):
- **the carrier:** 9.8 [2.7, 17.8] against 18.22;
- **the second instrument:** 13.4 [6.7, 21.1] against 19.37.

**Why these readings carry no weight on P-max:**
- **They are not the verdict.** No verdict is issued from this population.
- **It is diluted.** Under the dilution model with non-members at excess zero, this design reads *holds* at the margin with probability 0.63 (results; same file, S-J1).
- **They lean upward.** The singleton maximum's max-of-three inflation tilts form (a) toward a higher contrast (results; same file, the S-D measurement-error clause).

So they are not evidence of a composed effect.

**Form (b) on the same population** is also descriptive:
- **the carrier:** 0.295 [0.11, 0.56] (printed 0.30), against the margin of 0.30. Its lower bound net of the simulated null bias of 0.040 is 0.067 (results; same file, S-D2; `b3/b3-results.json`, readings C full b).
- **the second instrument:** 0.17 [−0.02, 0.45]. Its bias-net lower bound, at a bias of 0.036, is −0.051 (S-D4).

**Two reliability corrections cross the margin.** They are sensitivities on this descriptive population, not claims:
- the carrier's form (b): 0.35 [0.13, 0.65];
- the live dossier under Opus 4.8, form (b): 0.31 [0.11, 0.51] (results; same file, S-G1).

Each divides an already diluted, upward-leaning descriptive reading by a reliability factor. P-max is not read from them, and they do not bear on the round-1 verdict.

**The mechanism, prospectively.** B0's in-sample join said an author's flag follows the author's most visible line. On this pool:
- under the carrier the join is not confirmed: AUROC 0.622 [0.50, 0.72] against the plan's 0.65 (results; `b3/b3-results.md`, S-Q2; `b3/b3-results.json`, readings C mechanism);
- under the second instrument it is met at the boundary: AUROC 0.655 [0.54, 0.75] against 0.65, printed 0.66 (S-Q1; readings S mechanism).

Both are descriptive: there are no matched controls, and the sham is unrated on this axis.

### 10.4 The composed view and B4's gates

The composed view is not a P-max reading and carries no partition (results; `b3/b3-results.md`, S-N1). On the full quiet set's 146 item applications, at their sealed rules, it flags:
- **Opus 4.8:** 0.29 [0.21, 0.38], with controls 0.10 and sham 0.05;
- **Sonnet 5:** 0.16 [0.10, 0.22];
- **GPT-6 Sol:** 0.12 [0.06, 0.18].

**Brief 22's gates, as its dated note states them:**
- **G1 fails.** Opus 4.8's composed recall on the full quiet set is 0.29 [0.21, 0.38], below 0.65. The comprehension-quiet stratum's 0.12 is beside it (results; `b3/b3-results.md`, S-N3).
- **G2 holds by its letter, and is not positive evidence.** The verdict is *inconclusive*, which is not *excluded*. That is not the per-account combination response G2's purpose asks for.
- **G3 waits** on the elicitation study.
- **The consequence.** With G1 failing, B4's confirmatory path is not opened. B4 goes to path 2, a descriptive reading, together with the elicitation curve. G2 holding changes nothing about that (brief 22, dated note of 2026-11-02).

### 10.5 Disclosures carried with the section

- **The executors.** Both S3 stages ran in Fable 5.1 sessions, not in Opus 5.5 with Sonnet 5.5 as the named fallback. Every output is tested and hashed (methods; `b3/b3-results-additions.md`, §1).
- **The union flag.** On each per-agent row, 73 of 796 units have no honest pair on another class document, so their union flag equals their own flag, as in B1 (results; `b3/b3-results.md`, header).
- **Operating characteristics.** The readings script's own dry run gives the carrier 0.64 / 0.09 / 0.02 / 0.73. Part 3's figures, quoted by S-F's fixed clauses, are 0.68 / 0.07 / 0.03 / 0.72. Bound (ii) sits 0.6 Monte Carlo SE below 0.10 here, against Part 3's 1.8 (results; same file, header).
- **Broken honest edits.** 31 of 796 applications broke a later honest edit (0.039), and 10 of 116 items carry at least one such application (methods; `b3/b3-results-additions.md`, §3).
  - Clean items: 15 of 17 in the subset, 23 of 26 in the stratum, 66 of 73 in the full set.
  - The shares did not differ materially between candidates, control items and the sham.
- **The pre-signal's basis and spend.** The run cost $43.79, against a pre-signal estimate of $48.87, the confirmed figure of $76.62 and the stop of $153.25 (methods; `b3/b3-results-additions.md`, §2).
- **What was not run or is pending.** The k = 2 descriptive arm was not run (S-P0). B3's human anchor is not yet scored (S4-2).
- **The plan's own disclosures** (§7) and brief 31's disclosures are printed verbatim in `b3/b3-results.md`, and travel with this section.
