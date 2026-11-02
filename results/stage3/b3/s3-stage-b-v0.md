# S3 Stage B record (brief 33 B1 to B4 under brief 33-B Part 2; the 33-B session, Fable 5.1): the judge run, the lock and the readings — 2026-11-02 09:37Z

Counts, hashes and dollars only; no sentence of `b3-results.md` is quoted here, no item text, no score, no flag aggregate. Barrier kept: the application file read by script only; `work/stage3/red/`, persona files, `archived-scores*`, the anchor sheet and its draw file, and other briefs' judge caches not opened (the trace audit below). Every path is from the project root. No OpenRouter request of any kind.

## B1. The first batch and the pause

- The gate: the coordinator's STATUS line of 2026-11-02 ("S3 GATE: HOLDS. STAGE B MAY BEGIN") on driver `stage3_b3_s3.py` 00e054ba (G10 in, fork 4a02207 pushed). `score` sent the first 20 Opus 4.8 item units of the carrier view (`P_author_doc` isolated, ascending opaque id) and paused by itself (exit 3): outcomes {'scored': 20}, 20 attempts, refused 0; realised 22958 input and 13526 output tokens (thinking inside, as B1's bases), $0.4529, $0.02265 per unit against the batch's own character estimate $0.01672 (ratio **1.3545**; fewer input tokens than estimated, about twice the output tokens), the whole cell's per-unit estimate $0.01654 beside (ratio 1.3692), and Part 2's basis $0.04472 (ratio 0.5065). Re-based total (every cell's estimate scaled by the ratio, as B1's `rebase`) **$66.19** beside the figure $76.62; escalate False (the threshold $102.16); stop $153.25 unchanged. Reported to the coordinator with no score or flag aggregate; the run continued on the coordinator's STATUS line ("S3 STAGE B: FIRST BATCH DONE; RE-BASE $66.19 AGAINST $76.62; NO ESCALATION; THE RUN CONTINUES") with `--continue`.

## B2. The cells in order, each complete before the next

| cell | units | scored | refused | errored | missing | realised $ | per unit | own estimate per unit | ratio | re-based $ | S2 at Part 2's basis |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P_author_doc_iso|opus48 | 796 | 796 | 0 | 0 | 0 | $13.3397 | $0.01676 | $0.01654 | 1.013 | $17.83 | $35.59 |
| P_author|opus48 | 796 | 796 | 0 | 0 | 0 | $8.8463 | $0.01111 | $0.01474 | 0.754 | $15.90 | $10.34 |
| P_author_doc_iso|sonnet | 796 | 796 | 0 | 0 | 0 | $3.0043 | $0.00377 | $0.00541 | 0.697 | $5.83 | $4.75 |
| P_author|sonnet | 796 | 796 | 0 | 0 | 0 | $2.5813 | $0.00324 | $0.00469 | 0.691 | $5.06 | $2.69 |
| P_author_doc_live|opus48 | 232 | 232 | 0 | 0 | 0 | $6.9044 | $0.02976 | $0.02146 | 1.387 | $6.74 | $10.60 |
| P_author_doc_live|sonnet | 232 | 232 | 0 | 0 | 0 | $1.4035 | $0.00605 | $0.00738 | 0.82 | $2.32 | $1.94 |
| O_diff|sonnet | 232 | 232 | 0 | 0 | 0 | $1.0779 | $0.00465 | $0.00568 | 0.818 | $1.79 | $1.39 |
| O_diff|opus48 | 232 | 232 | 0 | 0 | 0 | $5.7468 | $0.02477 | $0.02764 | 0.896 | $8.69 | $7.74 |
| O_diff|sol | 232 | 232 | 0 | 0 | 0 | $0.8895 | $0.00383 | $0.00647 | 0.593 | $2.03 | $1.58 |
| **total** | 4344 | 4344 | 0 | 0 | 0 | **$43.79** | | pre-signal $48.87 | | $66.19 | $76.62 |

- Every cell complete in B2's order; stops recorded: 0; G7-only continues: none; errored units: 0; refusals: 0. Stage B started 2026-11-02T06:59:37Z, completed 2026-11-02T09:30:02Z. Total **$43.79** against the pre-signal $48.87, the re-based $66.19, the figure $76.62 and the stop $153.25 (ratio to the figure 0.57); no draw repeated after any judge call; no OpenRouter request. Run record `s3-run-v0.json` 2bebb2cb.
- Caches under `work/stage3/b3/cache-s3/` (one per view and model; never open to a scenario-side session): `judge-batches.jsonl` 2bfc072c; `judge-cache.s3.O_diff.anthropic-claude-opus-4-8.jsonl` a6873339; `judge-cache.s3.O_diff.anthropic-claude-sonnet-5.jsonl` de3fb65c; `judge-cache.s3.O_diff.us-openai-gpt-6-sol.jsonl` 443e0f15; `judge-cache.s3.P_author.anthropic-claude-opus-4-8.jsonl` 92d65244; `judge-cache.s3.P_author.anthropic-claude-sonnet-5.jsonl` 456e78bd; `judge-cache.s3.P_author_doc_iso.anthropic-claude-opus-4-8.jsonl` 95564e4a; `judge-cache.s3.P_author_doc_iso.anthropic-claude-sonnet-5.jsonl` 94c87ee7; `judge-cache.s3.P_author_doc_live.anthropic-claude-opus-4-8.jsonl` 9966121b; `judge-cache.s3.P_author_doc_live.anthropic-claude-sonnet-5.jsonl` bb56832d.
- The scores file `s3-scores-v0.json` ad407998: 4344 rows (unit id, item id, regime, arm, role, placement, view, judge, outcome, score, flag (the union), flag_unit, union_max, n_honest_other_pairs, cache label; no text); built from the application file 02edac2a; stopped: None.

## B3. The readings, once

- The analysis lock: 4344 of 4344 rows, incomplete rows none, stopped False: open. `stage3_b3_s3_readings.py` c7e14a58 run once on the scores file and the matrix (1b80280a) with the clean-items file (21e7ede2), G9's check file (4ad97f7d, PASS) and the dry run's operating characteristics (357422ca); plan 59a98c15 (fork commit 1fafa57), judge clients judge_client.py 72d394e3 and judge_openrouter.py e812157c (section 4.10), the window rule as recorded.
- **`b3-results.md` a759aba4, `b3-results.json` b496d422**: 95 sentences in section 6.0's assembly order, every one selected by rule and every slot filled by rule; by family: {'S-A': 8, 'S-C': 1, 'S-D': 11, 'S-E': 6, 'S-F': 2, 'S-G': 11, 'S-G6': 4, 'S-I': 1, 'S-J': 1, 'S-K': 4, 'S-L': 6, 'S-M': 5, 'S-N': 4, 'S-O': 8, 'S-P': 1, 'S-Q': 2, 'S-R': 18, 'S-S': 1, 'S4': 1}. The cascade reached state `read` at step 1 (the sentence families say which; this record does not quote them). Section 7's disclosures verbatim, brief 31's three disclosures, the union-flag disclosure (dated note 5), the operating characteristics beside Part 3's (O3), S-G6's source (dated note 3), the pointer to round 2 (section 8) and S4-2 are in the file; S-N2 or S-N3 selected by rule.
- Beside it, `b3-results-additions.md` e08891ac (a dated addition, as S4-1 will be): the executor, the pre-signal's basis (dated note 2) and the broken-honest-edit counts (dated note 1), which the frozen readings script does not write.

## B4. Trace audit, entries and the mirror

- Trace audit (this session's transcript `5cfad631-5c28-4c64-8607-c476fa7e1e42.jsonl`, the policy regenerated for it): opened 141, allowed 75, outside 66 (existing files 0, non-existent tokens 66), **never-open 0**; verdict PASS (`s3-trace-audit-stageB.json` 06458f71; policy `s3-trace-policy.json` 08660fd8).
- The prep-report entry "Brief 15 (B3), S3" with its sealed-parameters subsection; the outputs added to the frozen-tables manifest `b0/frozen-tables.json` under one amendment; the B3 row of `work/stage3/INDEX.md`; the fork mirror under `results/stage3/b3/` and `scripts/stage3/` (not pushed; the coordinator pushes); one STATUS line; brief 33-B's row in `briefs/INDEX.md`.
- Done against brief 33: the gate held on the coordinator's STATUS line; every cell of section 2.6 and the add-on scored; `b3-results.{json,md}` exist with every family's sentence selected by rule; the spend table is within the stop; the mirror is committed. Not done by S3, by design: S4-1 (the separate session after Aravind reports).

## Hashes

- `work/stage3/b3/b3-results.md` a759aba4785b9bf02a197a8f5acad069d423a85af2df1440ec28bd446f24f39c
- `work/stage3/b3/b3-results.json` b496d42275a7ae503d4b0a43158af2af4f6489ec27b040a9aeb5f2bbcbb18e0b
- `work/stage3/b3/b3-results-additions.md` e08891ac667d0926496723eea9f802fb9a2b41434823843ce5235bac526a98d4
- `work/stage3/b3/s3-scores-v0.json` ad4079983f3806da8e95c3b017cc0e3760985a513bf074d3f544f164a288f639
- `work/stage3/b3/s3-run-v0.json` 2bebb2cbb2968fa0585ab4007d13de82b916ff7170a66ac9f26d7da11c8d4ebb
- `work/stage3/b3/s3-stage-a-v0.md` 811fd33ba7a3481e2ae0d272b0000fcdbff095adbe4734d58c5fbcba6a1bbdf5
- `work/stage3/b3/s3-honest-pairs-check-v0.json` 4ad97f7d60d986f8a24e61a272fc2780b7cc204487e5ac7d77c2d7f24f5cc838
- `work/stage3/b3/s3-trace-audit-stageB.json` 06458f71593103b6aff3c97be53798e07bccaa16dd67a212a87c283468ec04d3
- `work/stage3/b3/s3-applications-v0.json` 02edac2a88fbdd3d9cfd4404e496aac6991c2f917fd27ca191394dc225c229bc
- `work/stage3/b3/s3-render-v0.json` 7c33c10433784bbbab57eca7640e9cd0f381dfff796cdf9157fdcd3700ee169f
- `work/stage3/b3/s3-analysis-matrix-v0.json` 1b80280ad8ed14d1ec0fed26b7137d3cc50a055e8f41b19e52083439f5b3effe
- `work/stage3/b3/s3-clean-items-v0.json` 21e7ede2b95b49af714d9339a96c5e63d2204df9964c3b43ddbddbe502616ae7
- `work/stage3/b3/plan.md` 59a98c155908c4727b20d60945b15d16bcaa1084bb009dca444059c5f78e22db
- `work/stage3/b3/s3-trace-policy.json` 08660fd82b8a977ec0be5683404aaee2f24a78d3e501f5f6cbec077dc4827f66
- `work/stage3/b3/s3-readings-dryrun-v0.json` 357422cabbba1b5e94083b61e6eb14c76f7e4ba3a04048cd88190beb827ccd82
- `work/stage3/b3/s3-config-v0.json` e28dca16fa9c0c809cc61a5117f15ffa9cce97a73c6e8a42ea54e24e9a1d45cc
- `work/stage3/b3/s3-preflight-v0.json` 8e332d9be1baacbef8a8ae2e807fad8b3e5d4728beb571b94873362df970c285
- `work/stage3/b3/cache-s3/judge-batches.jsonl` 2bfc072c5f8e94060f65d6079f5fb896b5a36328681a91423f3d8621098542a5
- `work/stage3/b3/cache-s3/judge-cache.s3.O_diff.anthropic-claude-opus-4-8.jsonl` a6873339c254f8d68aa2010d160c1b127554de884d9b6a4e4eff5b4e76054c38
- `work/stage3/b3/cache-s3/judge-cache.s3.O_diff.anthropic-claude-sonnet-5.jsonl` de3fb65cf6c73760048d5447c4ac7888e2e7445697b13c1197f73eca616826f6
- `work/stage3/b3/cache-s3/judge-cache.s3.O_diff.us-openai-gpt-6-sol.jsonl` 443e0f153c146dfdbba17952f45bc8cb1e76dd26e5e5dea8912724b97bcfe8d3
- `work/stage3/b3/cache-s3/judge-cache.s3.P_author.anthropic-claude-opus-4-8.jsonl` 92d652444c6b2a0a816a626e5d6b73824b935f62c51fccc61192b832c0a2e9b1
- `work/stage3/b3/cache-s3/judge-cache.s3.P_author.anthropic-claude-sonnet-5.jsonl` 456e78bdc85fc78fa121978e79b268dc7c28dd8a083db5707cf9062e600cc73e
- `work/stage3/b3/cache-s3/judge-cache.s3.P_author_doc_iso.anthropic-claude-opus-4-8.jsonl` 95564e4a7c9f97838e4a052aaea049a85c97e3db6ab7e1bd2e74edfe81894d42
- `work/stage3/b3/cache-s3/judge-cache.s3.P_author_doc_iso.anthropic-claude-sonnet-5.jsonl` 94c87ee73f37c02c79f8dbad7feca52dcba132c17c31580a877678911de3d51e
- `work/stage3/b3/cache-s3/judge-cache.s3.P_author_doc_live.anthropic-claude-opus-4-8.jsonl` 9966121b0bd4c9f62ac46662ce70a75a95f458e67e185ea069813b12369a33ee
- `work/stage3/b3/cache-s3/judge-cache.s3.P_author_doc_live.anthropic-claude-sonnet-5.jsonl` bb56832d3418792e912537c5fe96601db7cfbadca0e4e0e81bb2a91e8a8b257b
- `work/checks/stage3_b3_s3.py` 00e054ba30d270942aef3a77dc33cc785d4a9bd1e3f32c6738a37b2771c063ad
- `work/checks/stage3_b3_s3_readings.py` c7e14a580631d66a7f37216acb3412dd42ee6e97304c6662989eca1be6738693
- `work/checks/stage3_b3_s3_record.py` 19fad7ebdc93bd36b63bb46915b91f74a0b3fcd4660403b0c0c8f7c16e6dde14
- `work/checks/stage3_b3_s3_stage_b_record.py` 11e27bcdde46c6372b04d3a01e083b61ab3f8271845317e54d876c35bd30dcb5
- `work/checks/stage3_b3_s3_trace_audit.py` af2bf444b398b03caac349f1958c315de1492291ff1da21445145d31c702f388
- `work/checks/judge_client.py` 72d394e33584f7a5fe9ab638f4fc95c57ae9d0d7d0c93bf2c2d15928c4daf198
- `work/checks/judge_openrouter.py` e812157cb991445c12cd4c9197505b27cc03c04f1b23dbde447d417d88b71034
- fork HEAD at writing: 4a02207
