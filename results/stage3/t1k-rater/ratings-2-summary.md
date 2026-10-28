# Brief 07s part R (amendment B2): pass agreement

Agreement between the two fresh-context passes (`fable`, high effort) on each input. Pass 1 is primary, pass 2 the reliability check. band = min(4, floor(score / 20)): 0-19 -> '0 to 20', 20-39 -> '20 to 40', 40-59 -> '40 to 60', 60-79 -> '60 to 80', 80-100 -> '80 to 100'.

| Input | Rubric section | n | Spearman | Mean absolute difference | Band within one | Band exact |
|---|---|---|---|---|---|---|
| `stripped-statements-2.json` (`ratings-2.json`) | 2 | 176 | 0.977 | 3.08 | 1.000 | 0.881 |
| `stripped-triples.json` (`ratings-triples.json`) | 2b | 246 | 0.982 | 3.57 | 1.000 | 0.833 |

Single edits, identical items scored equally within each pass: pass1-statements-2.jsonl: 0 of 11 groups unequal; pass2-statements-2.jsonl: 0 of 11 groups unequal.
Triples, identical items scored equally within each pass: pass1-triples.jsonl: 0 of 1 groups unequal; pass2-triples.jsonl: 0 of 1 groups unequal.
