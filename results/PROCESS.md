# How the work was done

**Two sides with a barrier between them.**
- **The red side** wrote the planted changes and the scorers that decide whether planted content reached a follower's action (the predicates). It kept them in its own files.
- **The blue side** built the harness, ran the monitors and the followers, and joined the outcomes.

The blue side never saw planted text. Where it needed planted material, it ran scripts that print only counts, ids, scores and hashes, and it called the red side's scorers as code without opening them. No plant was optimised against the monitor.

**Designs were filed before the runs.** Each block's design was written, reviewed and committed before its first run. That covers the estimands, the rules that turn counts into a sentence, the gates and the caps. A seal list then pinned every input by its sha256: the payloads, the draws, the task map, the red scorers and the runner. The commit history shows the order.

| block | filed design | seal list | review and dispositions |
|---|---|---|---|
| follower test (core) | `stage3/v5/FT/preregistration-v1.3.md` | `FT/pre-gate-v0.md` to `v2.md`, `FT/GATE.md` | `FT/review/` |
| blocks D, W, H | `stage3/v5/P2/preregistration-v1.md`, `-v1.1.md` | `P2/pre-gate-p2.md` | `P2/dispositions-round1.md`, `-round2.md` |
| single-statement arm | | `stage3/v5/SS/pre-gate-ss.md` | |
| honest deviance | `stage3/v5/S3/rules-frozen.md` | | |

Where a result was read after the fact, its record says "post hoc" or "descriptive", and the note says so beside the number.

**How runs were audited.** A script scores a run as *carried* when planted content appears in the follower's logged action. Two audits then read the runs, by readers who did not build the plants, each working from a rule frozen before it read:
- **The positive audit** read every carried run in which the follower had checked a source or declined, and a seeded sample of the rest. It asked whether the follower acted on the content or questioned it.
- **The negative audit** read the runs scored *not carried*, to find acting on the plant in other words.

Clean controls were read the same way. A second reader re-read a sample each time, and the agreement is in the records (`stage3/v5/P0/audit-neg-table-b.md`, `FT/red-audit-rule.md`, `P2/completion-reader-rule.md`, `P0/severity-rule.md`). Each result reports the share both ways the unread runs could fall, as a range, beside the script's own count.
