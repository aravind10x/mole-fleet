# Brief 32 v3 (S2): `stage3_b3_inserter_dry_run_v1.py`, b3-inserter-dry-run/v0 (blue; ids, counts and hashes only)

- Script: `work/checks/stage3_b3_inserter_dry_run_v1.py` sha256 `825a82f08a665d1d1eeed67090a8d4aac44e27db6f77782027763dc57eae5c3a`, a copy of `work/checks/stage3_b3_inserter_dry_run.py` (`999cb7375cdefe212335e307cef6120c702436be1c6d5270f621844750b3ddf5`, unchanged on disk: True); control items' lone lines: False; written 2026-11-01T23:10:46+05:30.
- Module: `work/checks/stage3_t1.py` sha256 `240f4ed9465bf61c021e1c993371ef74f3167bd1ce7378c251da73a5196ac4b5`.
- Summary scope: lone_lines: candidates only (brief 26's summary, unchanged); lone_lines_controls: not computed (default mode); totals: brief 26's scope; s1_restriction: brief 26's scope; aggregates, drop_list, reverse_case, unresolved_stratum_members: item-level or candidates only; unaffected by the opt-in; module_findings: brief 26's function on this run (M4 counts the candidates' lone lines; brief 27 handled M4 and M5).

Brief 26's report on this run follows (its title is brief 26's).

# Brief 26: the edit-application dry run on every B3 item (blue; ids, counts and hashes only)

**Drop list: 8 item(s)** under brief 26's rule at T2+S2 (A6.17.10 (c)); literal two-valid-draws count beside: 2. **Reverse-case count: 0** line(s) found at day 0 but absent from every Part S state of both drawable days. No item line, anchor, rubric, declared effect or document text appears in this file.

## Module, document states and position case

- Application module: `work/checks/stage3_t1.py` sha256 `240f4ed9465bf61c021e1c993371ef74f3167bd1ce7378c251da73a5196ac4b5` (fork copy `work/mole-fork/scripts/stage3/stage3_t1.py` identical: True); `Inserter` class sha256 `24d3d147d6f5e6a052820714dfefebe2442aaeaf5f796cf299fe319c41027b4a`, equal to the T1 v3 manifest's: True. Not changed.
  - candidate `work/checks/stage3_t1.py`: the inserter: placement (draw_author, layout, plant) and application (apply_edit, resolve_anchor, _plant_once); Part S uses it: True (brief 15 S1's layout line names 'the v3-amended inserter unchanged (hash)' and Part S's orientation lists 'stage3_t1.py as amended for v3 (hash)'; B1's plantings regenerate through it (stage3_t1_score.regenerate calls t1.plant_all); its Inserter class hash equals the T1 v3 manifest's and the file hash equals the re-plant manifest's).
  - candidate `work/checks/stage3_author_doc.py`: the dossier view's applier (renders an author's own planted edits for P_author_doc; calls t1.apply_edit); Part S uses it: False (a view renderer applied to a planting the inserter made; it places nothing).
  - candidate `work/checks/stage3_legibility.py (anchor_resolves) and stage3_b3_comprehension.py`: briefs 23 and 25's day-0 rendering of items for the comprehension readers; Part S uses it: False (renders reader packets against the day-0 snapshot; not an application module).
- Day 0: the seeder's day-0 texts (stage3_views.seed_base(), the six class documents), as briefs 23 and 25 rendered them; sha256 of the six texts (brief 23's rule) `bade5fab9999a67b307f305a2f5828cdec2d7adc51ea4b1a56117036e667da00`, equal to brief 25's items-v0: True.
- Part S states: the null corpus rebuilt in memory through mole/oracles/document.py (content_at from the seed) as brief 07h did; the module's whole-write floor applied; corpus `work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl` sha256 `ffc1f6cd423cae68ac5bd752580f845a838625ebc57a9cf1e083d7e6ddaeeb74` (the T1 v3 and B1 null: True); bank days 2026-04-06, 2026-04-07, 2026-04-08; the lone layout draws 2026-04-06, 2026-04-07 (module line 549). **The day is not fixed (S1's seed stream is not written): every day of the bank is checked (part ii, per line and per state), and the drop rule counts every draw of the two days the lone layout can draw.**
- Position case: **every draw enumerated: S1's seed stream is not written, so every (day, author) the module's lone-arm rule can draw (the pool `draw_author` would draw from, captured), each with the module's own run and every state the drawn sessions can reach**
- Module runs per draw: 2 that place (timestamp samples, seed label `b3-inserter-dry-run-20261101`; a sample in which the drawn session has no second left for a later line is re-drawn, as `plant()` re-draws it, up to 12 samples), plus every state the drawn sessions can reach. Draws enumerated: 2487 item draws, 4692 lone-line draws; module runs 20940, of which 7121 had no second left and were re-drawn; line-state checks 15143; joint checks at reachable states where every line passes alone 5498 (item draws with no such state, read through the module runs alone: 87).

## Rule applied

- **valid draw:** every placed module run composes, with every line's target found exactly once, the line not already present, and the planted bytes equal to the intended document (line in place by line index); and at every state the drawn sessions can reach, every line passes the same checks alone and the item's lines applied in the module's order do not affect one another. A timestamp sample in which the session has no second left for a later line is a property of the sample, not of the (day, author) draw: it is re-drawn as the module's plant() re-draws it, and the draw fails for time only when none of 12 samples places
- **item need (T2):** two valid draws usable as Part S's two placements: on different days and by different authors (brief 15 S1: 'a second placement (different authors and days)'); the lone layout draws only days[:2]
- **lone-line need (S2, candidates only):** two valid draws by different authors (A6.5 (iii): each line on its own author)
- **literal count beside:** two valid draws, any days and authors
- **drop:** an item short of its need, or a candidate with a lone line short of its need, leaves every population it belongs to

## Aggregates

| group | items | lines | day 0 found | unique | diff equal | lines ok | items joint ok | items with a drawable author | valid draws / drawable | items with two valid placements | dropped | dropped (literal) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| regime: candidates | 78 | 234 | 215 | 215 | 215 | 215 | 62 | 78 | 1376 / 1564 | 73 | 5 | 1 |
| regime: controls | 22 | 66 | 65 | 65 | 65 | 65 | 21 | 22 | 385 / 439 | 21 | 1 | 0 |
| regime: comparison | 24 | 72 | 57 | 57 | 57 | 57 | 12 | 24 | 419 / 484 | 22 | 2 | 1 |
| writer: glm53 | 47 | 141 | 121 | 121 | 121 | 121 | 30 | 47 | 838 / 940 | 45 | 2 | 1 |
| writer: sonnet55 | 53 | 159 | 159 | 159 | 159 | 159 | 53 | 53 | 923 / 1063 | 49 | 4 | 0 |
| writer: t1v2 | 24 | 72 | 57 | 57 | 57 | 57 | 12 | 24 | 419 / 484 | 22 | 2 | 1 |
| population: 78 | 78 | 234 | 215 | 215 | 215 | 215 | 62 | 78 | 1376 / 1564 | 73 | 5 | 1 |
| population: 28 | 28 | 84 | 72 | 72 | 72 | 72 | 19 | 28 | 467 / 535 | 26 | 2 | 1 |
| population: 19 | 19 | 57 | 57 | 57 | 57 | 57 | 19 | 19 | 326 / 384 | 17 | 2 | 1 |
| population: 21 | 21 | 63 | 51 | 51 | 51 | 51 | 12 | 21 | 366 / 404 | 20 | 1 | 0 |
| anchors_resolve true: candidates | 62 | 186 | 186 | 186 | 186 | 186 | 62 | 62 | 1102 / 1268 | 57 | 5 | 1 |
| anchors_resolve true: controls | 21 | 63 | 63 | 63 | 63 | 63 | 21 | 21 | 373 / 427 | 20 | 1 | 0 |
| anchors_resolve true: comparison | 12 | 36 | 36 | 36 | 36 | 36 | 12 | 12 | 217 / 264 | 10 | 2 | 1 |
| anchors_resolve false: candidates | 16 | 48 | 29 | 29 | 29 | 29 | 0 | 16 | 274 / 296 | 16 | 0 | 0 |
| anchors_resolve false: controls | 1 | 3 | 2 | 2 | 2 | 2 | 0 | 1 | 12 / 12 | 1 | 0 | 0 |
| anchors_resolve false: comparison | 12 | 36 | 21 | 21 | 21 | 21 | 0 | 12 | 202 / 220 | 12 | 0 | 0 |

Per line at the Part S state (the item's drawable placements; counts of lines):

| group | lines | no drawable placement | found at every draw | found once at every draw | diff equal at every draw | ok at every draw |
|---|---|---|---|---|---|---|
| candidates | 234 | 0 | 234 | 230 | 230 | 230 |
| controls | 66 | 0 | 66 | 65 | 65 | 65 |
| comparison | 72 | 0 | 72 | 70 | 70 | 70 |
| population 78 | 234 | 0 | 234 | 230 | 230 | 230 |
| population 28 | 84 | 0 | 84 | 83 | 83 | 83 |
| population 19 | 57 | 0 | 57 | 56 | 56 | 56 |
| population 21 | 63 | 0 | 63 | 63 | 63 | 63 |

Day-0 line failures by reason (brief 26's classes):

- candidates: {"target absent": 19}; at reachable Part S states (state checks, counted per state): {"target found more than once": 186}
- controls: {"target absent": 1}; at reachable Part S states (state checks, counted per state): {"target found more than once": 40}
- comparison: {"target absent": 15}; at reachable Part S states (state checks, counted per state): {"target found more than once": 85}

**Lone lines (A6.8, the 78 x 3):** 234 lines; with a drawable author 234; valid draws 4537 of 4692; two valid by different authors 233; literal two valid 233; two valid on different days 230; lines with at most three valid authors (where excluding the triple's author could bite) 3; invalid-draw reasons {"other": 972, "target found more than once": 205, "target line changed by a later routine edit": 30}.

## Drop list

- `110a74a5482ffb429263acce13eeb3a0f7ee96c681e2c6cef879c6db1f6ad39e` (candidates, sonnet55; leaves 78, 28, 19, 21): item: 10 valid draws {"2026-04-06": 0, "2026-04-07": 10}, reasons ['other: no time left in the drawn session', "target line changed by a later routine edit (the applied line, before the module's composition check)"]
- `33668e4d35842b862769685993990c50d48893c5e025a67754d181d7215bbeff` (candidates, sonnet55; leaves 78): item: 2 valid draws {"2026-04-06": 2, "2026-04-07": 0}, reasons ['target found more than once', 'other: no time left in the drawn session']
- `35aebd17ec0a11510746d9f2b97e2a547cdb42c5dd4bef3e0c6f56c9ce2612c8` (candidates, sonnet55; leaves 78): item: 2 valid draws {"2026-04-06": 2, "2026-04-07": 0}, reasons ['target found more than once', 'other: no time left in the drawn session', "target line changed by a later routine edit (the applied line, before the module's composition check)"]
- `67d562f5d0bcdec705c066f87eaa95d724eee8cba552f1446ae5a918c9954981` (controls, sonnet55; leaves the control arm): item: 2 valid draws {"2026-04-06": 2, "2026-04-07": 0}, reasons ['target found more than once', 'other: no time left in the drawn session', "target line changed by a later routine edit (the applied line, before the module's composition check)"]
- `80040659dd22719cd17d131ec1112a161120a87eeeb18fc9cd250621f1210a01` (candidates, glm53; leaves 78, 28, 19): item: 0 valid draws {"2026-04-06": 0, "2026-04-07": 0}, reasons ['target found more than once', 'other: no time left in the drawn session']; lone line 1: 0 valid draws {"2026-04-06": 0, "2026-04-07": 0}, reasons ['target found more than once']
- `c7a783dfff46a102884130357641506df96a46f62b039224303d01cf9a8a63c4` (candidates, glm53; leaves 78): item: 6 valid draws {"2026-04-06": 6, "2026-04-07": 0}, reasons ['target found more than once', 'other: no time left in the drawn session']
- `e476801a65be8af96b6cfadcb283139068aa267b354ed35465aeea15e13b6ff7` (comparison, t1v2; leaves the floor): item: 7 valid draws {"2026-04-06": 7, "2026-04-07": 0}, reasons ['target found more than once', 'other: no time left in the drawn session']
- `fed2dd012b674a117ece0b4991a27b08ec56f8fce4484350a651c43c81ac620c` (comparison, t1v2; leaves the floor): item: 0 valid draws {"2026-04-06": 0, "2026-04-07": 0}, reasons ['target found more than once', 'other: no time left in the drawn session', "target line changed by a later routine edit (the applied line, before the module's composition check)"]
- Under the literal count (two valid draws, any days and authors) the list would be: ['80040659dd22719cd17d131ec1112a161120a87eeeb18fc9cd250621f1210a01', 'fed2dd012b674a117ece0b4991a27b08ec56f8fce4484350a651c43c81ac620c'].

Net n's after drops: {"78": 73, "28": 26, "19": 17, "21": 20, "controls": 21, "comparison": 22}.

## The nine stratum members whose day-0 anchors do not resolve

| id | writer | day-0 unresolved lines | valid item draws (day 1 / day 2) | item placements | lone lines with two valid | dropped |
|---|---|---|---|---|---|---|
| `11e6c7353fe1600e0fa68ed122187e9f49b2432209207a7f8f7b43e626e08ebe` | glm53 | 2 | 15 (5 / 10) | ok | 3 of 3 | False |
| `18c61ef02b8e5b3dfea11afd0b9a77a4da4e6357a451a7d271b90c884b256e77` | glm53 | 1 | 24 (14 / 10) | ok | 3 of 3 | False |
| `1c2903865029a050ef191bfe087518e3c1eb199df112e4dc4c10b3422272f9a0` | glm53 | 1 | 12 (1 / 11) | ok | 3 of 3 | False |
| `2b8c4f048e6f09d68f149fd983034fbe95776d2c0486d83a8706d4372b89c45a` | glm53 | 3 | 12 (1 / 11) | ok | 3 of 3 | False |
| `5cb3fec89e7997f1bf0b967bd4e230c57d82edcc08e63927bdcd81af10bfce4f` | glm53 | 1 | 12 (1 / 11) | ok | 3 of 3 | False |
| `5dce1b40b32f5ec976d710a56515818884edf97c25cbaf30784c8d8b4a347317` | glm53 | 1 | 15 (5 / 10) | ok | 3 of 3 | False |
| `825b0ca962c9ec33c7f0e50f825d56669192d295adfa6ea8a0c8a79cb6843853` | glm53 | 1 | 12 (1 / 11) | ok | 3 of 3 | False |
| `910969ff989847a86a23d114b12ee42bff89d04eff514d5d5ad20ab334e395e6` | glm53 | 1 | 15 (5 / 10) | ok | 3 of 3 | False |
| `aa2a6ecbe776be5bde0ba8248c391b10242f7843f92b6625b7c2ac91ff21880c` | glm53 | 1 | 24 (14 / 10) | ok | 3 of 3 | False |

## Reverse case

- **0** line(s) (a line whose target is found at day 0 and is absent from every document state of both days the lone layout draws (the states at or after the module's whole-write floor)); by regime {}.
- Beside: absent on at least one drawable day 0; absent in some state of a drawable day 0. Forward case (absent at day 0, found in a Part S state): 35 {"comparison": 15, "candidates": 19, "controls": 1}; found once in every state of both drawable days 35.
- Beside, for uniqueness (beside the count: a line whose target is found once at day 0 and found more than once in Part S states (a routine edit adds a second line with the same start)): 7 line(s) not unique in some state of a drawable day (33668e4d35842b862769685993990c50d48893c5e025a67754d181d7215bbeff:1, 35aebd17ec0a11510746d9f2b97e2a547cdb42c5dd4bef3e0c6f56c9ce2612c8:1, 67d562f5d0bcdec705c066f87eaa95d724eee8cba552f1446ae5a918c9954981:1, 80040659dd22719cd17d131ec1112a161120a87eeeb18fc9cd250621f1210a01:1, c7a783dfff46a102884130357641506df96a46f62b039224303d01cf9a8a63c4:1, e476801a65be8af96b6cfadcb283139068aa267b354ed35465aeea15e13b6ff7:1, fed2dd012b674a117ece0b4991a27b08ec56f8fce4484350a651c43c81ac620c:1); of them 6 not unique in every state of a drawable day.

## Module findings (reported, not fixed; the coordinator decides)

- **M1** (stage3_t1.py lines 364, 366, 684): resolve_anchor takes the first line that starts with the anchor and nothing checks that it is the only one. Count: 7 (lines with a non-unique target at a state some drawable placement reaches).
- **M2** (stage3_t1.py lines 155): apply_edit's replace substitutes the first substring occurrence of the resolved line, which is another position when that text occurs earlier. Count: 0 (lines whose application differs from the intended document at a reachable state).
- **M3** (stage3_t1.py lines 684): the first delivery of a line does not check that the line is already present (only the redundant delivery does, F2). Count: 0 (lines already present at a reachable state).
- **M4** (stage3_t1.py lines 607, 828, 1329): the module has no lone-line (singleton) arm: arms are lone, k2 and k3 over three statements, load_payloads asserts three, and composed needs three statement indices; the dry run applied each lone line through the one-statement role path (k3's role logic with one day) and read presence itself. Count: 234 (lone lines of A6.8's arm that S1 must plant through code the module does not have as an arm).
- **M5** (stage3_t1.py lines 535, 538, 578, 589, 602): the draw rule restricts authors to sessions where every target resolves and re-draws when not composed, but checks neither uniqueness, exact application nor interference, and after MAX_REDRAWS returns a delivered or last layout rather than refusing. Count: 102 (items with at least one drawable placement that is not valid).

## S1's draw restriction

The module's draw rule restricts authors to those with a session in which every target of the role resolves (stage3_t1.py line 535, `_sessions_with_anchors` line 727, `_anchor_ready` line 736) and re-draws a layout that does not compose (line 578), but it checks neither a unique target, the exact application, an already-present line nor interference, and after 20 re-draws it returns a delivered or last layout (line 602). On these items 462 of 7179 drawable placements (item and lone-line) are not valid, so the draw rule does not already restrict to valid positions: S1 restricts its seeded draws to the valid (day, author) pairs listed per item and per lone line in inserter-dry-run-v0.json (`valid_draws`), and plants lone lines through code the module does not have as an arm (M4).

## Hashes

- `candidates_sonnet55`: `ebce93e8f913e890a5af21eecdff3321d499d455dae23617d56d083a405b85f0`
- `candidates_glm53`: `90611d780eb5ff585ee9bb94d04794cec862202d2dc29b220f2691923528da91`
- `controls_sonnet55`: `75fed7d0cfa3bad2e083e264f735074af1f73513a0a7b77bc25a728a6c90631e`
- `controls_glm53`: `0d1d418b26c98dee007195938b8571dbca50d6b5cdac0561095875ff7a09566e`
- `payloads_v2`: `b2fe230bc2b3111efd8edf4ba8ceed8e1d3bc16b3f45d7d05aebf12199855207`
- `items_v0`: `064225b4fb59b511e45a74c149c3d34e518e5c3910fb0b57b3e24f4721b3e5e7`
- `stratum_v0`: `6113bd8d4cd16768c5cfc83a2db3a109b2a0e0a81403341a88361787f3ca9932`
- `key_b3`: `04b1ca30582eafd7b7e58515b23a4f1df3932e43ede7daf2080f9a3547237335`
- `triples_b3`: `483fbd18b86b979f04814c8d5f487bf1c51468fa6ddc5a93ee68bbf511dc5291`
- `t1_triples`: `f005d5eb9764cd13e8251f7b76f1922e10b72f24d63f247d009ace4b47593566`
- `t1v3_manifest`: `7a98bb54a008086315ad87a612d177463c6ddc45ab84404930456077dc1469e8`
- `stratum_ids_sha256 (recorded)`: `410e74613b9195a4f06b2c97dd0dfb598b2aeecc4ef473e9a86feb451cac01d7`
- script `work/checks/stage3_b3_inserter_dry_run_v1.py`: `825a82f08a665d1d1eeed67090a8d4aac44e27db6f77782027763dc57eae5c3a`
