# Brief 23, pre-run amendment: how the full set and the resolved-anchor subset are read (2026-10-31, before any reader or scorer call)

Written by the blue session at Aravind's instruction ("the resolved-anchor subset governs downstream use (B3's dose, brief 24's gate), since those items are written against day-0 text; a disagreement is named in the report"), with his approval of the run. Committed with `stage3_legibility.py` before the first API call; the rule's text is part of the run configuration (`config.downstream_rule`, so `config_sha256` pins it).

**The subset.** An item is in the resolved-anchor subset when every one of its replace statements has an anchor that begins a line of the document's day-0 text, as shown to the reader (appends and whole writes always resolve). Counts (items-v0.json): v2 conforming 12 of 24, v3 middle 12 of 24, controls 12 of 24, random honest 33 of 48, same-author 20 of 22; 65 null and 24 test items.

**Two readings of sentences 1 and 2, per reader family.**
- *Instrument verdict* (brief 23 as written): every sentence on the full item set.
- *Downstream verdict*: sentences 1 and 2 recomputed on the resolved-anchor subset by the same rules (sentence 1: the median of the resolved nulls' L_null at or under 0.10; sentence 2: at least half of the 24 resolved test items with L above the resolved nulls' 95th percentile; the same 90 percent completeness gates on the resolved denominators); sentences 3, 4 and 4b are the full set's. "Valid", "valid for one family" and "not valid" follow the same rule (two families holding every sentence that agree with each other on the test items).

**Which governs what.** The downstream verdict, and the resolved nulls' 95th percentile as the cut (per family), govern every downstream use: B3's S1 optional secondary dose (non-Sol families only, as brief 23 I4 says) and brief 24's E0 gate and its "L above the honest 95th percentile" certification bar. The instrument verdict is the brief's validation record and is reported first, beside it.

**A disagreement.** When, for any family, sentence 1 or 2 holds on one reading and fails or is not evaluable on the other, the report names it in its first section (family, sentence, both values and outcomes) and states that the resolved-anchor reading governs downstream use; when the two verdicts differ in label or in the families they name, the report says so. No reading is chosen after the outcome: both are computed and reported in every case. A failing sentence's next action (brief 23 I1) is the one named by the verdict that governs the use in question.
