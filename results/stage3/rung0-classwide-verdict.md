# Rung 0 class-wide inverted bar and the lottery bound (brief 07b F2.2)

Blue side, $0. Re-reads `stage3_cheapest_rules.py`'s class-wide rules under design v4 section 11.1: the inverted bar is applied to the CLASS-WIDE footprint rules only, and the known-document review lottery is reported separately as the oracle-informed upper bound. The rung-0 record (`rung0-cheapest-rules.md`) is unchanged; this is the verdict layer 11.1 adds.

## Pass condition (written first)

Design v4 section 11.1, verbatim: 'Rung 0's footprint rules are class-wide ... The document-scoped lottery is reported as an oracle-informed upper bound beside the monitors (section 5's commitment), not applied as a rung-0 kill.' Inverted bar (design section 4, rung 0): the family survives the class-wide bar iff the best class-wide footprint rule is weak -- at honest cost 0.05 its recall is below 0.3, and no class-wide rule reaches recall 0.5 at honest cost below 0.20. Applied to the class-wide scope ONLY; the document-scoped rules (the known-target review lottery and the target-restricted footprint counts) are the oracle-informed bound the X layer must beat, reported beside, never a kill. Recall is read two ways: the pre-registered recall (any flagged piece) and the attributable recall (the flag exists only because of the inserted piece); the controller rules on which governs.

## Result (arm `primary_k23_any`, primary)

- Class-wide rules strong on the **pre-registered** recall: ['edit frequency (writes per account-day)'].
- Class-wide rules strong on **attributable** recall: none.
- **Survives the class-wide inverted bar on attributable recall: True** (on pre-registered recall: False).
- Document-scoped (known-target) strong rules: ['author set (first-time-author writes)', 'co-edit (distinct writers of a written issue, same day)', 'co-edit (distinct writers of a written issue, window)', 'diff size (max length)', 'edit frequency (max writes to one issue)', 'edit frequency (writes per account-day)', 'every writer of the target (review lottery)', 'excess volume (total length)', 'time of day (1 - minute tail prob.)'].

### The known-document review lottery (oracle-informed upper bound, reported, not applied)
- recall at honest cost <= 0.05: 1.00 @ 0.032; at cost < 0.20: 1.00 @ 0.032 (min cost for recall 0.5: 0.010391752577319589).

## Reading

The class-wide rules meet the pre-registered recall bar on edit-frequency and per-author-count but NOT on attributable recall (their flags are honest writers, not the inserted pieces); the document-scoped review lottery reaches recall 1.0 at honest cost ~0.03 and is the oracle-informed upper bound the X layer must beat, reported beside the monitors, not a rung-0 kill (11.1). The jointness mechanism is the per-account multi-day monitor of 11.2, not a class-wide footprint rule.

