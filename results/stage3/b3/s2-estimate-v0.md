# B3 S2: the estimate on the plan's units, the control items' lone-line check, and the k = 2 arm (brief 32 v3)

**Done 2026-11-01 night, $0, no judge request sent.** Blue session (Opus 5.5 in Claude Code) under brief 32 v3 (`briefs/32-b3-s2-estimate-2026-11-01.md` 58df6ec1). Plan `work/stage3/b3/plan.md` **4c677dee2e825e7250e1bb94893011d7b8464c967cc9b22817b39a204ed8d507**, not changed by this session. Nothing was applied to a live document, no position was drawn or computed for S3, no packet was built and no token counted. Only opaque ids appear here (first 12 characters; the full ids are in the JSON), with counts, dollars and hashes. No item line, document text or rubric appears. Data: `s2-estimate-v0.json` (hash under "Outputs").

## The figure for Aravind to confirm, and the stop

| form | dollars | stop at 2× (A6.12) |
|---|---|---|
| **H1 + H2**: T2+S2 on the plan's units, plus the control items' lone-line add-on | **$76.62** | **$153.25** |
| H1 + H2 + H3 | omitted: H3 skipped the k = 2 arm (dated note below) | |

- **H1 is $68.17.** It is T2+S2 on plan §2.6's 3,840 units, at Part 2's per-unit bases.
- **H2 is $8.45.** It is the control items' lone-line add-on: 21 items × 3 lines × 2 placements = 126 units on each of the four per-agent views. No control item falls into the *none* class, so the add-on is at its maximum.
- **The stop is twice the confirmed figure, add-on included.** It is not twice H1 alone ($136.35).
- **The figure follows Part 2's method, not a `--dry-run`** (brief 32 H1; the departure is listed under "Differences"). The exact token count and the re-base after about 20 Opus 4.8 units move to S3's first batch, and they are reported before the rest of S3 runs. The stop stays at $153.25 unless Aravind re-confirms.

## H0. Orientation and pre-flight

- **The pre-flight passes: 24 of 24 OK.** The plan's `s1-preflight-sha256` block (24 lines) was extracted and checked with `shasum -a 256 -c` from the project root. Exit status 0.
- **Read:**
  - `plan.md` in full.
  - Brief 15: A6.8, A6.12, A6.13 (with A6.13.8), A6.18 (b), A6.21, A6.22 and A6.23. A6.3 (d) was read for the k = 2 arm.
  - Part 2: `power-simulation-v3b.md` 5f6b0eae (the P4 table) and `power-simulation-v3b.json` 031795d5, keys `unit_costs` and `estimate` only.
  - Brief 26: the record (`inserter-dry-run-v0.md` 25a905da, `.json` edd289ce) and the script (`stage3_b3_inserter_dry_run.py` 999cb737, source).
  - Brief 27: the record (`lone-line-arm-v0.md` fff3e5c3) and the restricted mode's reader `ValidDraws`, with `PartSInserter`, in `stage3_t1.py` 240f4ed9. The fork copy `scripts/stage3/stage3_t1.py` is identical.
  - `lone_line_feasibility()` in `stage3_b3_s1_populations.py` 9ea7d687.
- **Not opened by this session:** brief 15's Part W or Part R; `red/`; persona, rater-key or sealed pilot files; judge caches; v3b's input files; any item file.
- **Disclosure.** Brief 26's method loads items by id from the writers' payload files, brief 25's `items-v0.json` and `stratum-v0.json`, the rater key and the stripped-triple files, as brief 26's and brief 27's runs did. The copy of the script did the same, so it read those files programmatically. This session never opened them. Every output passed brief 26's guard, which refuses any item line, anchor, declared effect or day-0 line.
- **Memory.** The memory index was loaded automatically at start. Nothing from it entered a figure.

## H1. Part 2's method on plan §2.6's units

**Method.** For each row, the dollars are (item units + lone-line units) × that cell's `unit_costs[cell].used`. These are Part 2's bases, unchanged (`power-simulation-v3b.json` 031795d5).
- Each basis is the larger of the two measured bases (B1/T1v3 and B4-R). For `O_diff` under GPT-6 Sol it is brief 09's estimate basis.
- The units are read row by row from plan §2.6 and summed by `stage3_b3_s2_estimate.py`.
- The sums equal the plan's stated totals: **2,088 item + 1,752 lone-line = 3,840 units**.
- Lone-line units fall on the four per-agent rows only (438 each). The two live rows (A6.13.8) and the three `O_diff` rows (A6.8) carry none.
- This session knows of no rate change since Part 2 and applies none.

| view, judge (plan §2.6) | Part 2 cell | basis $/unit (source) | item units | lone-line units | dollars |
|---|---|---|---|---|---|
| `P_author_doc` isolated, Opus 4.8 | `dossier_iso:opus48` | 0.044715 (B4-R) | 232 | 438 | $29.96 |
| `P_author` zero-context (sealed), Opus 4.8 | `P_author:opus48` | 0.012989 (B1/T1v3) | 232 | 438 | $8.70 |
| `P_author_doc` isolated, Sonnet 5 | `dossier_iso:sonnet` | 0.005964 (B4-R) | 232 | 438 | $4.00 |
| `P_author` zero-context, Sonnet 5 | `P_author:sonnet` | 0.003376 (B1/T1v3) | 232 | 438 | $2.26 |
| `P_author_doc` live, Opus 4.8 | `dossier_live:opus48` | 0.045701 (B4-R) | 232 | 0 | $10.60 |
| `P_author_doc` live, Sonnet 5 | `dossier_live:sonnet` | 0.008382 (B4-R) | 232 | 0 | $1.94 |
| `O_diff`, Sonnet 5 | `O_diff:sonnet` | 0.005978 (B1/T1v3) | 232 | 0 | $1.39 |
| `O_diff`, Opus 4.8 | `O_diff:opus48` | 0.033367 (B1/T1v3) | 232 | 0 | $7.74 |
| `O_diff`, GPT-6 Sol | `O_diff:sol` | 0.006810 (brief 09 estimate basis) | 232 | 0 | $1.58 |
| **total** | | | **2,088** | **1,752** | **$68.17** (68.1750) |

**The gap to Part 2's $98.17, in two steps.** Each step is reproduced from Part 2's `estimate["T2+S2"]` rows. Its keys are read by the plan's names: `lone_units` are the item units and `singleton_units` the lone-line units.
- **Part 2: $98.17** (98.1735). It recomputes exactly from `unit_costs` × its rows: 248 item units on all nine cells, and 468 lone-line units on the six per-agent cells, live included.
- **Step 1, net counts: $91.86**, which is $6.31 less. 232 replaces 248 item units on nine cells, and 438 replaces 468 lone-line units on the same six cells.
- **Step 2, the live rows' lone-line units stripped: $68.17**, which is $23.69 less. This removes 438 units on each of `dossier_live:opus48` and `dossier_live:sonnet`.
- **The coordinator's arithmetic ($98.17, then $91.86, then $68.17) is reproduced with no residue.**

**Plan §9's sentences, checked.**
- **$72.86 is the T2+S2 remainder after the live-view lone-line strip** (confirmed). Part 2's $98.17 less 468 units on the two live cells ($25.31) gives $72.86 (72.8628).
- **v1's pro rata gives $68.19, $0.017 above the exact figure.** The pro rata is 73 / 78 × $72.86. It applies 73 / 78 (0.9359) to the item units, but their ratio is 232 / 248 (0.9355): the controls and the sham also lose items (116 of 124 net). The lone-line ratio is 438 / 468 (0.9359). The figure goes by the exact per-cell sum.

## H2. The control items' lone-line add-on

### Step 1: the control items' lone-line valid draws, by brief 26's method

**The copy of brief 26's script**
- **The copy:** `work/checks/stage3_b3_inserter_dry_run_v1.py` **825a82f08a665d1d1eeed67090a8d4aac44e27db6f77782027763dc57eae5c3a**. It copies `stage3_b3_inserter_dry_run.py` 999cb737, which is unchanged on disk; its hash is checked by the tests and recorded in the table.
- **What changed (14 lines replaced, 83 added in all):**
  - one opt-in, `--controls-lone-lines`, which adds each control item's three lines to the lone-line tasks;
  - a `regime` argument for `lone_line_summary`, which still defaults to the candidates;
  - the output name, `inserter-dry-run-v1` with the opt-in, and a refusal to write over the pinned `work/stage3/b3/inserter-dry-run-v0.{json,md}`;
  - the provenance and summary-scope fields;
  - a heading for the `.md`.
- **What stays brief 26's.** Under the opt-in a control item's drop and its `lines[].lone_line` are unchanged. The control arm's need is the item pair. Whether the add-on's lines meet their need is decided by S3's tag-6 draw.
- **Brief 26's method is unchanged.** Thirty-one functions, from `check_line` through `enumerate_draws`, `static_checks`, `load_items`, `decide` and the guard to `render_md`, are byte-identical in source to the pinned script's (tested). Brief 26's constants are equal too.

**The runs**
- **Opt-in:** 8 processes, 1,664 s. It writes the new table.
- **Default mode:** 6 processes, to `work/stage3/b3/s2/dryrun-default/`. 1,822 s. Its output is kept for test (a) only.

**The new table: `work/stage3/b3/inserter-dry-run-v1.json` 021389311e33658884cf316778dc19a39b880ff9f884f9bb85598857c3260a47** (`.md` 1584f55f). It has edd289ce's shape and is the valid-draws file S3 would read for the add-on. Brief 26's edd289ce (and its `.md` 25a905da) are untouched.

**Tests** (`work/checks/test_stage3_b3_inserter_dry_run_v1.py`, hash under "Outputs"; 12 test functions, 42 collected with the 31 parametrized source checks: 41 pass in the normal run, and the gated role-order spot check passes when run with `S2_SLOW=1`)
- **(a) The default output reproduces edd289ce's `items[]`.** All 124 items are equal, `draws` and `lone_lines` included, as brief 27's E4 compared them. The drop lists (8 and 2), net n's, `lone_lines`, `totals`, `aggregates` and reverse case are equal too. The top-level fields that differ are exactly the provenance fields: `written`; `module` (hash 240f4ed9 against 52a79312, and its cited line numbers); `module_findings` and `s1_restriction` (line numbers only, finding counts equal); and the copy's own `brief`, `script` and `summary_scope`. Brief 27's re-run differed in the same way.
- **(b) Only the control items' `lone_lines` differ.** Of all 124 items, the new table's `items[]` differs from edd289ce's in exactly 22 (item, field) pairs: `lone_lines` of each of the 22 control items, the dropped one included. Each control now has three lone lines in role order 1, 2, 3; edd289ce has none. Every control's drop and `lines[].lone_line` are unchanged. Every candidate and sham item is identical.
- **(c) The provenance states its own run.**
  - `version` b3-inserter-dry-run/v1 and `brief` 32 v3;
  - `script`: the copy's path and hash 825a82f0, `copy_of` 999cb737 (on disk now as well), `controls_lone_lines` true, `table_of_shape` edd289ce;
  - `module` 240f4ed9, fork copy identical;
  - `written` 2026-11-01T23:08 (local).
- **(d) The summary fields are recomputed or marked** (`summary_scope`).
  - `lone_lines` is candidates only and equals edd289ce's.
  - `lone_lines_controls` is new: 66 lines, every one with a drawable author. 1,271 of 1,317 drawable draws are valid. All 66 have two valid draws by different authors; 65 have two on different days. Invalid-draw reasons: other 252, target found more than once 42, target line changed by a later routine edit 26.
  - `totals` is recomputed: lone-line draws 6,009 = 4,692 + 1,317, with the item draws unchanged at 2,487.
  - `aggregates`, `drop_list`, `reverse_case` and `unresolved_stratum_members` equal edd289ce's.
- **The candidates' figures reproduce from the new table.** This is the first check in `stage3_b3_s2_estimate.py` and a test. `lone_line_feasibility(v1, pair-rule drops)` returns 219 net candidate lines, 219 meeting the need by different authors, 219 under every item pair, 177 with different days also required, 18,018 item-pair cases, and 462 short with different days required. That equals `s1-populations-v0.json` (f17e7a72) `lone_lines`.
- **Brief 27's restricted mode reads the new table unchanged.**
  - `ValidDraws.load` takes it with no code change. Its entries equal the table's item and line draws for all 124 items, and every control item has three lines.
  - On edd289ce the same reader refuses a control line ("no valid draws listed for this item or line").
  - Reading the table draws nothing.
- **Role-order spot check** (`S2_SLOW=1`). Brief 26's enumeration was re-run on the lowest-id control item's three lines through the copy's own functions and compared with the table's entries. Passes (61 s): `07d10150487e` lines 1, 2 and 3 match the table's entries 1, 2 and 3 field for field.

### Step 2: S1's enumeration applied to the net control items

**Which items.** The net control items are the 21 control items not on the pair-rule drop list. Their id sha256 is 3db4d199…, equal to plan §1.1's.

**How it was run.** Both ways the brief allows, cross-checked:
- **The pinned `lone_line_feasibility()`** (9ea7d687, imported and called, not edited) was called on a copy of the table in which the net control items carry the regime it reads and the candidates do not. It was called once for all 21 and once per item.
- **This session's own enumeration** (`work/checks/stage3_b3_s2_estimate.py`) gives the per-pair counts the function does not return. It uses the function's own pair construction and its predicate `_two_by_different_authors`.
- **The two agree on all 21 items.** The function's figures over all 21 equal the sum of its per-item figures. The check draws nothing and uses no stream.

**The need, per pair.** For each pair the pair rule can draw (two valid item draws on different days by different authors), the check asks whether each of the item's three lone lines keeps two valid draws by different authors once both of the pair's authors are excluded (A6.5 (iii)). The variant that also requires different days is beside.

| control item | writer | valid pairs | pairs meeting the need, lines 1 / 2 / 3 | pairs with all three met | class | beside (different days too): lines 1 / 2 / 3; all three; class |
|---|---|---|---|---|---|---|
| `07d10150487e` | glm53 | 135 | 135 / 135 / 135 | 135 | all pairs pass | 135 / 135 / 135; 135; all pairs pass |
| `291fbb5aefba` | sonnet55 | 77 | 77 / 77 / 77 | 77 | all pairs pass | 77 / 77 / 77; 77; all pairs pass |
| `321a25304daf` | sonnet55 | 10 | 10 / 10 / 10 | 10 | all pairs pass | 10 / 10 / 0; 0; none: no pair meets the need |
| `4294f4264c94` | glm53 | 77 | 77 / 77 / 77 | 77 | all pairs pass | 77 / 77 / 77; 77; all pairs pass |
| `4e610424e8a6` | sonnet55 | 159 | 159 / 159 / 159 | 159 | all pairs pass | 159 / 159 / 159; 159; all pairs pass |
| `575e0912a4bc` | sonnet55 | 135 | 135 / 135 / 135 | 135 | all pairs pass | 135 / 135 / 135; 135; all pairs pass |
| `58b590cfd78c` | glm53 | 49 | 49 / 49 / 49 | 49 | all pairs pass | 49 / 49 / 49; 49; all pairs pass |
| `6e285c364ccd` | glm53 | 11 | 11 / 11 / 11 | 11 | all pairs pass | 0 / 0 / 0; 0; none: no pair meets the need |
| `7aada045116d` | glm53 | 49 | 49 / 49 / 49 | 49 | all pairs pass | 49 / 49 / 49; 49; all pairs pass |
| `87782fda6199` | sonnet55 | 159 | 159 / 159 / 159 | 159 | all pairs pass | 159 / 159 / 159; 159; all pairs pass |
| `8ad9d7f60126` | sonnet55 | 68 | 68 / 68 / 68 | 68 | all pairs pass | 68 / 68 / 68; 68; all pairs pass |
| `9c5e5ca84db0` | sonnet55 | 49 | 49 / 49 / 49 | 49 | all pairs pass | 49 / 49 / 49; 49; all pairs pass |
| `a26878edbd3c` | glm53 | 77 | 77 / 77 / 77 | 77 | all pairs pass | 77 / 77 / 77; 77; all pairs pass |
| `abc2eb57fabc` | sonnet55 | 11 | 11 / 11 / 11 | 11 | all pairs pass | 0 / 0 / 0; 0; none: no pair meets the need |
| `ad08e7e720fa` | sonnet55 | 49 | 49 / 49 / 49 | 49 | all pairs pass | 49 / 49 / 49; 49; all pairs pass |
| `b4ba62b8befe` | sonnet55 | 11 | 11 / 11 / 11 | 11 | all pairs pass | 0 / 0 / 0; 0; none: no pair meets the need |
| `d42fc02e6152` | glm53 | 68 | 68 / 68 / 68 | 68 | all pairs pass | 68 / 68 / 68; 68; all pairs pass |
| `d80fe1cdb75b` | glm53 | 159 | 159 / 159 / 159 | 159 | all pairs pass | 159 / 159 / 159; 159; all pairs pass |
| `ef6e19101a67` | sonnet55 | 135 | 135 / 135 / 135 | 135 | all pairs pass | 135 / 135 / 135; 135; all pairs pass |
| `f45852526126` | glm53 | 11 | 11 / 11 / 11 | 11 | all pairs pass | 0 / 0 / 0; 0; none: no pair meets the need |
| `f4c98ad9ff4d` | glm53 | 159 | 159 / 159 / 159 | 159 | all pairs pass | 159 / 159 / 159; 159; all pairs pass |

**Classes, under the plan's rule (different authors).**

| class | count |
|---|---|
| all pairs pass | **21** |
| some fall short | 0 |
| none: no pair meets the need | 0 |
| none: no valid pair | 0 |

**Beside, with different days also required.**

| class | count |
|---|---|
| all pairs pass | 16 |
| none: no pair meets the need | 5 (`321a25304daf`, `6e285c364ccd`, `abc2eb57fabc`, `b4ba62b8befe`, `f45852526126`) |

The beside variant is not the plan's rule (§2.1). It is reported as it was for the candidates.

**Valid draws per line** (valid / drawable). Every line of every net control item has two valid draws by different authors before any exclusion (3 of 3 for each item):

| control item | line 1 | line 2 | line 3 |
|---|---|---|---|
| `07d10150487e` | 25 / 26 | 25 / 26 | 25 / 26 |
| `291fbb5aefba` | 19 / 19 | 19 / 19 | 19 / 19 |
| `321a25304daf` | 19 / 19 | 19 / 19 | 11 / 19 |
| `4294f4264c94` | 19 / 19 | 19 / 19 | 19 / 19 |
| `4e610424e8a6` | 28 / 28 | 28 / 28 | 28 / 28 |
| `575e0912a4bc` | 25 / 26 | 25 / 26 | 25 / 26 |
| `58b590cfd78c` | 16 / 17 | 16 / 17 | 16 / 17 |
| `6e285c364ccd` | 12 / 12 | 12 / 12 | 12 / 12 |
| `7aada045116d` | 16 / 17 | 16 / 17 | 16 / 17 |
| `87782fda6199` | 28 / 28 | 28 / 28 | 28 / 28 |
| `8ad9d7f60126` | 19 / 19 | 19 / 19 | 19 / 19 |
| `9c5e5ca84db0` | 16 / 17 | 16 / 17 | 16 / 17 |
| `a26878edbd3c` | 19 / 19 | 19 / 19 | 19 / 19 |
| `abc2eb57fabc` | 12 / 12 | 12 / 12 | 12 / 12 |
| `ad08e7e720fa` | 16 / 17 | 16 / 17 | 16 / 17 |
| `b4ba62b8befe` | 12 / 12 | 12 / 12 | 12 / 12 |
| `d42fc02e6152` | 19 / 19 | 19 / 19 | 19 / 19 |
| `d80fe1cdb75b` | 28 / 28 | 28 / 28 | 28 / 28 |
| `ef6e19101a67` | 25 / 26 | 25 / 26 | 25 / 26 |
| `f45852526126` | 12 / 12 | 12 / 12 | 12 / 12 |
| `f4c98ad9ff4d` | 28 / 28 | 28 / 28 | 28 / 28 |

**The function's own fields for the control items** (the fields it returns for the candidates; the JSON has them per item):

| field | all 21 net control items |
|---|---|
| net lines | 63 |
| two valid by different authors | 63 |
| every item pair leaves two by different authors | 63 |
| beside: every item pair leaves two on different days by different authors | 50 |
| beside: item-pair cases | 4,974 |
| beside: cases short with different days required | 142 |

The 142 short cases are 10 from `321a25304daf` (its line 3 under each of its 10 pairs) and 33 from each of the other four *none*-beside items (all three lines under each of their 11 pairs).

### The rule for S3 (tag 6), recorded here and not applied here

- **When.** S3 draws a control item's lone lines on tag 6 once, after every control pair of tag 3 has been drawn.
- **The exclude set** is that control item's two authors as drawn.
- **A line short of its need.** A control item any of whose lines cannot then supply two draws by different authors leaves the add-on, all three lines, since form (a) needs every line. It stays in the control arm and is counted.
- **A refusal at application time** is handled by §2.4 (3), as for the candidates.
- **Independence.** The control arm's pairs (tag 3) never depend on the add-on.
- **None leaves the add-on now.** No net control item is in the *none* class and none falls short under any pair, so every one of the 21 enters S3's tag-6 draw with every possible pair able to meet the need.

### The add-on's price

**The units.** 21 remaining control items × 3 lines × 2 placements = **126 units on each of the four per-agent views** (`dossier_iso:opus48`, `P_author:opus48`, `dossier_iso:sonnet`, `P_author:sonnet`). These are the rows that carry lone-line units in §2.6: not the live views (A6.13.8) and not `O_diff` (A6.8).

**The price: $8.45.** The four bases sum to $0.067044 per unit, giving **$8.45** (8.4476). The figure with the *none* items removed is the same $8.45, since there are none. The brief's "at most about $8.45" is reproduced.

**The gap to Part 2's $15.99.** Part 2's figure reproduces from its bases: 132 units (the gross 22 × 3 × 2) on six per-agent cells, the two live ones included.
- Pro rata on the net 21 it is **$15.26**, plan §9 (2)'s figure.
- Stripping the two live cells' 126 units each ($6.81) gives **$8.45**.
- v1's "about $15" therefore does not stand, as brief 32 says.

## H3. The k = 2 descriptive arm: priced, not clean, skipped

**Price, by H1's method, for the record.** The arm as plan §4.6 describes it is the net certified stratum, 10 items (ids sha256 e2182f06…), × 2 placements = 20 units on each of 7 views. The 7 views are every view except Sonnet's two dossiers: `dossier_iso:opus48`, `dossier_live:opus48`, `P_author:opus48`, `P_author:sonnet` and the three `O_diff`.
- **$3.06** (3.0587). The review session's argued figure is reproduced.
- **Beside:** if each per-agent view scored both authors of a k = 2 placement as separate units, it would be $5.19.

**The cleanness test of A6.22 (3).**
- **(i) No new application code: fails.**
  - Restricted mode maps an arm to the table through `PartSInserter._which`. That returns `None` for k2: "item" is the lone arm and a role index is a line arm.
  - `plant` and `apply_at` therefore refuse k2 with "no valid draws are listed for this arm". Brief 27's `test_every_restricted_draw_comes_from_the_valid_set` (in `test_stage3_t1_line_arm.py` 0ee5057b) asserts that refusal for k2 and k3.
  - `apply_at` places one (day, author). A k = 2 placement is two roles on two days by two authors.
  - `ValidDraws` reads only `item_id`, `draws`, `document` and `lone_lines` per item, so it has no k = 2 split.
  - The module's default mode has the k2 arm (`Inserter._roles`: lines [0, 1] on one author, [2] on another; `layout` draws days i and i + 1 for i in {0, 1}). It lacks the valid-draw restriction that A6.17.11 requires in code. Producing the arm under the restriction therefore needs new application code.
- **(ii) No new arm or stream beyond tag 5: passes on its own.** Plan §3 reserves tag 5.
- **(iii) Valid draws at $0 by brief 26's method, read by restricted mode unchanged: fails.**
  - Brief 26's `enumerate_draws` covers the lone arm's single-author draws over `days[:2]`, and `run` adds one-statement lone lines. Neither enumerates a k = 2 split: two roles, two authors, days i and i + 1 (the third bank day included), and interference between the roles.
  - A k = 2 table would need new enumeration code, and by (i) restricted mode has no key to read it.

**Dated note, 2026-11-01 night (S2):**
- **Decision.** A6.3 (d)'s k = 2 descriptive arm is **skipped**. It fails A6.22 (3)'s conditions (i) and (iii): running it would need new application code in restricted mode and new enumeration code for its valid draws.
- **Aravind's words (A6.22 (3)):** "Ok will take a call based on the estimate, and more importantly only if it's executionally clean i.e. if it complicates the run, let's skip it."
- **Consequence.** Plan §4.6's branch "not run" applies, with sentence S-P0. Tag 5 stays unused. The arm's price above ($3.06) is for the record only and is not part of any confirmation form.

## Differences from the plan and from brief 15, reported

1. **Plan §9 and A6.22 (1): no `--dry-run`.** Both have S2's figure come from a `--dry-run` re-based after about 20 Opus 4.8 units. As brief 32 H1 states, S2 instead used Part 2's method on §2.6's units; the token count and the re-base move to S3's first batch. The coordinator's dated note on `plan.md` records this.
2. **Plan §9 (2): the add-on's figure.** §9 (2) quotes the add-on as $15.99 (gross 22), about $15.26 on the net 21. It is priced here at $8.45 on §2.6's per-agent rows: the live views are stripped as for the candidates (A6.13.8), and `O_diff` scores no lone line (A6.8). The $6.81 between them is the two live cells. The rule applied is the plan's own unit rule (§2.6); the quoted figure is the one superseded.
3. **Plan §2.1 and §9 (2): "through brief 27's harness".** Both say the control items' valid draws are "first checked through brief 27's harness". They were computed by brief 26's method in a copy of brief 26's script, as brief 32 H2 step 1 directs, and read by brief 27's restricted mode (`ValidDraws`) without code change.
   - Brief 27's harness also applied every listed draw in restricted mode (its E4 (b): 4,537 of 4,537 accepted for the candidates).
   - That application at each listed control draw was **not run here**: it computes applications at draws, which brief 32 leaves alone.
   - It remains a possible $0 check before S3, at the coordinator's choice. S3's restricted mode checks every application anyway, and §2.4 (3) covers a refusal.
4. **Plan §2.2: the valid-draws file.** §2.2 names `inserter-dry-run-v0.json` (edd289ce) as S3's valid-draws file, and on it the restricted mode refuses every control line. The coordinator's note names `inserter-dry-run-v1.json` (021389311e33…) instead and adds its hash to the pre-flight list (A6.21).
   - The two files' `items[]` are identical except the control items' `lone_lines`, so every candidate, control-pair and sham draw is the same under either.
   - Brief 31's pre-flight (`stage3_b3_preflight.py`) reads the last `s1-preflight-sha256` block in `plan.md`, so the note restates the whole block (24 lines plus the new table).
5. **Plan §3 and the pre-flight's configuration values: the stream tags.** Tag 6 (the control items' lone lines) is in force by A6.22 (2). Tag 5 (k = 2) is not, by H3's skip.
6. **Brief 15 A6.23 against brief 32 v3: who writes the plan note.**
   - A6.23 says the one dated note on `plan.md` after S2 is "written by the brief 32 session at the coordinator's direction".
   - Brief 32 v3 says "the coordinator adds" it and that S2 changes neither the plan nor the pre-flight list.
   - This session followed the brief: `plan.md` is unchanged at 4c677dee and no note was written. It writes the note only on the coordinator's direction.

## Outputs and hashes

| file | sha256 |
|---|---|
| `work/stage3/b3/s2-estimate-v0.json` (this record's data) | 46d2e153798cad2b4259bf2e708f56937c233f86295963edda234a2e057ed7a0 |
| `work/stage3/b3/inserter-dry-run-v1.json` (the new table) | 021389311e33658884cf316778dc19a39b880ff9f884f9bb85598857c3260a47 |
| `work/stage3/b3/inserter-dry-run-v1.md` | 1584f55f12430a39bce65cb1f839c022cb11a5f25488e4d3cd2613a3cd8dace4 |
| `work/checks/stage3_b3_inserter_dry_run_v1.py` (the copy) | 825a82f08a665d1d1eeed67090a8d4aac44e27db6f77782027763dc57eae5c3a |
| `work/checks/test_stage3_b3_inserter_dry_run_v1.py` | 160841b0fda5e4ad9bcb8303193da9cfebda15206e63a3191556ad7aee905b13 |
| `work/checks/stage3_b3_s2_estimate.py` | f8f102d9af9248d9a3c8e0fd42e57d479bf4d4e99515290f32e5d5731f26fb82 |
| `work/checks/test_stage3_b3_s2_estimate.py` | 9ed48648b911ce376d4a159b63e7055cba9343c15abfad40f3392dfdc079906c (13 test functions, 21 collected with the nine cell maps; all pass) |
| default-mode run (`work/stage3/b3/s2/dryrun-default/inserter-dry-run-v0.json`, test (a) only) | cebacd57ecbf861590fd86e5d9c3c8d5bb62c3b2eba347d40bc02af9e0add809 (`.md` 30105e14) |

**Inputs, checked by hash in the script:** `plan.md` 4c677dee, `power-simulation-v3b.json` 031795d5, `inserter-dry-run-v0.json` edd289ce, `s1-populations-v0.json` f17e7a72, `stage3_b3_s1_populations.py` 9ea7d687, `stage3_b3_inserter_dry_run.py` 999cb737, `stage3_t1.py` 240f4ed9 and `test_stage3_t1_line_arm.py` 0ee5057b. All are unchanged. The fork copies are under `results/stage3/b3/` (the record, its data and the new table) and `scripts/stage3/` (the scripts and their tests, byte-identical; added to `test_fork_copies_identical.py`).

**Next.** S3 opens only after:
- Aravind confirms the figure ($76.62, stop $153.25);
- the coordinator's dated note on `plan.md` (the table's pin, §9's clarification, tags 5 and 6);
- the S3 brief.

Brief 31 is done.
