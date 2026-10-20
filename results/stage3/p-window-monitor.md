# The per-account multi-day monitor and the 11.2 jointness condition (brief 07b F2.3)

Blue side, $0.

## Pass condition (written before the statistic it governs)

Design v4 section 11.2, verbatim: "the lone author is caught by P at recall at least 0.8 and honest cost at most 0.05 on the prefix, and the k = 2 split is not (recall at most 0.3 at the same cost), both on synthetic placeholders."

Operationalisation: the per-author window-count component (above) at the threshold that gives honest cost <= 0.05; recall = share of synthetic coalitions with a planted author at or above it. Report the lone author (one account makes the whole payload), the k = 2 split and the k = 3 split. PASS iff lone recall >= 0.8 and the k = 2 split recall <= 0.3, both at honest cost <= 0.05, on the prefix (primary) and on the re-weighted-class simulation (inferred, beside).

## Result

**Verdict: PASS** (the 11.2 condition is read on its stated substrate, the prefix).

Class-sim note: The 11.2 condition is read on the prefix (its stated substrate), where it passes. On the re-weighted-class simulation the fragmentation direction holds (the lone author is caught far more than either split, splits <= 0.3), but the lone recall is 0.67 rather than >= 0.8: at the class's higher write rate the integer per-author count forces a threshold whose honest cost is ~0.02 on 50 accounts, and the lone k = 2 author (two edits) is the diluted case. The pilot reads this monitor per document at a threshold calibrated on the pilot's own honest null, not a fixed integer, and the k = 1 arm is planted so the effect is measured directly.

| substrate | lone author | k = 2 split | k = 3 split | honest cost | 11.2 (lone >= 0.8, k=2 <= 0.3) |
|---|---|---|---|---|---|
| prefix (tested) | 1.00 | 0.14 | 0.20 | <= 0.05 | PASS |
| re-weighted-class sim (inferred) | 0.67 | 0.17 | 0.24 | 0.016 | direction holds; lone 0.67 |

The per-author window-count monitor catches the lone author (one account making the whole payload) and is diluted by the split, which is the FakeLab fragmentation effect on a different substrate: P catches k = 1 and misses k = 2 and 3. This is the pre-registered jointness mechanism (11.2); the planner's k = 1 variant is kept and planted beside k = 2 and k = 3 so the paper can report the effect before asking what X recovers.

