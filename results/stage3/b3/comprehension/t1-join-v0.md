# Brief 25: the T1 join (A6.14.5, exploratory; counts only)

Brief 23's per-line D_part (r0, one sample, the item's own rubric; re-emitted through stage3_legibility.py's report mode) joined to 07k's section-2 line scores (the rater's standalone visibility, two-pass mean primary, pass 1 beside). A line yields the consequence alone when its D_part_line is above 0 under at least two of the three reader families (lines with fewer than two families scored are left out and counted). A hypothesis for the paper, never a sentence, until it is weighed.

## Rater line score: two-pass mean

| regime | lines | at or under 60: yield alone / with two families | over 60: yield alone / with two families | Spearman (Kimi K3, Sol, Sonnet 5.5, mean) |
|---|---|---|---|---|
| v2_conforming | 72 | 17 / 70 (0.243) | 0 / 2 (0.000) | 0.484, 0.359, 0.420, 0.532 |
| v3_middle | 72 | 10 / 68 (0.147) | 2 / 4 (0.500) | 0.175, 0.269, 0.208, 0.246 |
| pooled | 144 | 27 / 138 (0.196) | 2 / 6 (0.333) | 0.300, 0.276, 0.297, 0.351 |

## Rater line score: pass 1

| regime | lines | at or under 60: yield alone / with two families | over 60: yield alone / with two families | Spearman (Kimi K3, Sol, Sonnet 5.5, mean) |
|---|---|---|---|---|
| v2_conforming | 72 | 17 / 70 (0.243) | 0 / 2 (0.000) | 0.434, 0.330, 0.418, 0.486 |
| v3_middle | 72 | 10 / 69 (0.145) | 2 / 3 (0.667) | 0.211, 0.304, 0.203, 0.277 |
| pooled | 144 | 27 / 139 (0.194) | 2 / 5 (0.400) | 0.297, 0.279, 0.293, 0.347 |

Line statuses (r0, per family): {'kimi': {'scored': 144}, 'sol': {'scored': 144}, 'sonnet55': {'refused_prose': 1, 'refused_provider': 5, 'scored': 138}}.

## Hashes

- per_part: `143c5d7990185de7ae18a942bb8e5fa87a889fd30fa1c2e3c36de98ac8693d7d`
- instrument_v0_json: `511a150ecc20733e393533f749e9651406c324420e37f05ee67c51fe33eff782`
- t1_items_v0: `71fba5652257244a4a85480caa464de299ea2eb3f33b3c53f5a02036a0d196ae`
- 07k_key: `f0bc17d6eeeb6a2ece6f17fed463d36fc097f6ac26efd9ebf6aa6d78f7149606`
- 07k_ratings: `289a9fe1ba46b0c8e87ab103c998be3fb7faf3925667989a8444cd0197565b37`
- 07k_statements: `db3af7f474e11fd6b851e3c953d846e5edd1839e760e21e24d338ec86f0a2dfa`
- 07k_triples: `f005d5eb9764cd13e8251f7b76f1922e10b72f24d63f247d009ace4b47593566`
- report_script: `b794769d42c31f241f8262cda174478a27e545a23c459b674d6a985c3ea043aa`
- stage3_legibility: `1ba39b9609acc8718fc93ee4f866aa4185098688ceb52c1db5d82b27576bc281`

## Deviations

- None from A6.14.5's route: the per-line scores came through the report mode's re-emit (`--per-part-out`), checked against instrument-v0.json's per-item D_part on every item, repeat and family, and the cache hashes equal brief 23's recorded ones.
- The join is on r0 only (one sample per line), as brief 23 ran; 07k's statement for a line is found within the line's own payload by its rendered fields.
