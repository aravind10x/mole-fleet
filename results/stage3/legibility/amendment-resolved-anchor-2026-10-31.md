# Brief 23, pre-run amendment: how the full set and the resolved-anchor subset are read (2026-10-31, before any reader or scorer call)

Written by the blue session at Aravind's instruction ("the resolved-anchor subset governs downstream use (B3's dose, brief 24's gate), since those items are written against day-0 text; a disagreement is named in the report"), with his approval of the run. Committed with `stage3_legibility.py` before the first API call; the rule's text is part of the run configuration (`config.downstream_rule`, so `config_sha256` pins it).

**The subset.** An item is in the resolved-anchor subset when every one of its replace statements has an anchor that begins a line of the document's day-0 text, as shown to the reader (appends and whole writes always resolve). Counts (items-v0.json): v2 conforming 12 of 24, v3 middle 12 of 24, controls 12 of 24, random honest 33 of 48, same-author 20 of 22; 65 null and 24 test items.

**Two readings of sentences 1 and 2, per reader family.**
- *Instrument verdict* (brief 23 as written): every sentence on the full item set.
- *Downstream verdict*: sentences 1 and 2 recomputed on the resolved-anchor subset by the same rules (sentence 1: the median of the resolved nulls' L_null at or under 0.10; sentence 2: at least half of the 24 resolved test items with L above the resolved nulls' 95th percentile; the same 90 percent completeness gates on the resolved denominators); sentences 3, 4 and 4b are the full set's. "Valid", "valid for one family" and "not valid" follow the same rule (two families holding every sentence that agree with each other on the test items).

**Which governs what.** The downstream verdict, and the resolved nulls' 95th percentile as the cut (per family), govern every downstream use: B3's S1 optional secondary dose (non-Sol families only, as brief 23 I4 says) and brief 24's E0 gate and its "L above the honest 95th percentile" certification bar. The instrument verdict is the brief's validation record and is reported first, beside it.

**A disagreement.** When, for any family, sentence 1 or 2 holds on one reading and fails or is not evaluable on the other, the report names it in its first section (family, sentence, both values and outcomes) and states that the resolved-anchor reading governs downstream use; when the two verdicts differ in label or in the families they name, the report says so. No reading is chosen after the outcome: both are computed and reported in every case. A failing sentence's next action (brief 23 I1) is the one named by the verdict that governs the use in question.

## L17 dry run of the verdict rules, before any call ($0; `dryrun/verdict_sim.py`, `dryrun/s4_sim.py`)

Synthetic scores over the real item layout (ids, regimes and anchor flags from items-v0.json; no text), three reader families, a two-level scorer model (an answer is creditable or not; each of the two passes reads that with accuracy ACC), 20 to 40 replicates per scenario. Outcome rates (instrument verdict; the downstream verdict tracked it in every scenario):

| scenario (test whole-condition credit; parts; nulls) | ACC 0.95 | ACC 0.98 | ACC 0.995: test-item agreement (adopted) | pooled agreement | pooled, no test reversal |
|---|---|---|---|---|---|
| null: test items like the nulls | not valid 40/40 | not valid 30/30 | not valid 20/20 | not valid 20/20 | not valid 20/20 |
| every test item legible (whole 0.85, parts 0.03) | — | — | valid 0/20 | valid 5/20 | valid 2/20 |
| mixed 80/20 (whole 0.95 or 0.05) | — | — | valid 8/20 | valid 16/20 | valid 16/20 |
| mixed 60/40 | — | — | valid 9/20 | valid 6/20 | valid 6/20 |
| loud parts (parts 0.6) | not valid 40/40 | not valid 30/30 | not valid 20/20 | not valid 20/20 | not valid 20/20 |

Readings: every outcome is reachable; no scenario without a legible whole and quiet parts reached "valid" under any reading (no false confirmation seen). Two properties the run can fail on and that the report names when they bind: (i) at pass accuracy 0.98 or below, kappa falls under 0.8 at these low base rates (mean 0.70 at 0.95), so sentence 4 fails on scorer determinism; (ii) the test-item agreement adopted after codex round 1 cannot reach 0.6 when every test item is equally legible (single samples carry no between-item variance to agree on), so it can refute a working instrument there; the pooled reading is reported beside and a family failing sentence 4 on test-item agreement alone, with kappa and pooled agreement at threshold, is named in the report's first section (not re-read). The null's 95th percentile sits on a knife edge when about 5 percent of nulls reach L = 1 (values 0 to 1 across replicates), which the report's counts below, at and above the cut make visible.

## L18 check of this amendment against the error types

- *False confirmation:* the downstream verdict can only be as strict as or stricter than the full set on what governs downstream use (fewer items, wider null p95); its subset is fixed by an item property recorded before any call, not by an outcome.
- *False refutation:* the smaller subset (65 nulls, 24 test items) is more often not evaluable or failing; that cost falls on downstream use, which is the conservative direction, and both readings are reported.
- *A floor read as a result:* the same 90 percent completeness gates apply on the resolved denominators.
- *Attenuation read as exclusion:* not touched (no estimand changes).
- *Selection on instrument noise:* none: membership is the anchor flag, set before any call.
- *A null that does not measure the comparison's built-in advantage:* the resolved nulls keep their same-document false targets, so L_null on the subset still measures the whole condition's three chances of credit.
