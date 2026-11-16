# Result, SS Part D: the audit set for the single-statement runs (red side; counts, ids and hashes only; 2026-11-16)

$0, no model call. Read under `v5/`:
- COMMON (c0dba7ff) and `SS/brief-red-D.md` (7aa6bf58);
- `SS/outcomes-SS-v0.jsonl` (0a521bf6, 576 rows), by script only;
- `P2/audit-table-W.json` (5f584243), not opened; its layout is the earlier join's, read from `ft_audit_w_join.py`.

No transcript was read for content. Nothing hashed changed: rule `audit-rule.md` 7b317092, `ft_audit_wlib.py` 2f7b6a7c and `ft_audit_w_prepare.py` 17b5b5be, all re-checked.

## Eligible and sampled (predicate-true, no error; 406 eligible in all)
| cell (arm, follower) | chk eligible | chk sampled | other eligible | other sampled |
|---|---|---|---|---|
| single, kimi | 25 | 25 (census) | 58 | 20 (sample) |
| single, sol | 25 | 25 (census) | 76 | 20 (sample) |
| planted, kimi | 34 | 34 (census) | 74 | 20 (sample) |
| planted, sol | 36 | 36 (census) | 78 | 20 (sample) |

## Items
- **Pass one: 200 items in 10 folders of 20.** Path `red/ft/audit-SS/items-pass1/folder-01` to `folder-10`. Tree hash (first 16) `6f8ecf93eb47f9b7`.
- **Pass two: 20 items** (a tenth of 200), under fresh masked ids. Path `red/ft/audit-SS/items-pass2/folder-01`. Tree hash `f9ff0ac4d4e598cc`.
- **Key:** `red/ft/audit-SS/key.json` `044a706d`. Readers are never pointed at it.
- **Seeds:**
  - `random.Random(2026111601)` was created once. It sampled in the brief's cell order, chk before other, run ids sorted, and the same stream then shuffled the items and drew their masked ids.
  - `random.Random(2026111602)` drew, ordered and named pass two.
  - The brief fixes only these two seeds; using the first stream for the shuffle and the ids is my reading of "created once".
- **Masking check:** every item file was searched for every run id, payload id, source payload id, task id, model and prompt hash of the block, and for arm or follower labels as fields or paths. **0 hits.** Longest line: 800 characters.

## Scripts and tests (sha256, first 8)
- `red/ft/ft_audit_ss_prepare.py` `7e75903d`
- `red/ft/ft_audit_ss_join.py` `cfb632c6`
- `red/ft/test_ft_audit_ss.py` `5597d44a`: **9 passed**, exit 0. They were written and run before the build.

## Join command (run from the project root)
```
work/mole-fork/.venv/bin/python -I work/stage3/red/ft/ft_audit_ss_join.py --classes1 <merged pass-one file> --classes2 <pass-two file> --key work/stage3/red/ft/audit-SS/key.json --out-json work/stage3/v5/SS/audit-table-SS.json --out-md work/stage3/v5/SS/audit-table-SS.md --out-summary work/stage3/v5/SS/audit-table-SS-summary.json
```
- Each classes file is JSON lines `{"id": <masked id>, "class": "acts" | "questions" | "unclear"}`, one line per item, nothing else.
- The table holds, per run: run id, arm, follower, regime, stratum, class. Per cell and stratum it holds the size before sampling, the number read, and the counts of acts, questions and unclear; then pass-two agreement as a count.
