# The stronger composed judge: pre-registration (brief 07i, part 2; written 2026-10-26 before any Opus call; blue side)

Exploratory. Nothing here moves a sealed threshold, prompt, seed or window; Sonnet's readings stand as the pilot's instruments. Every number produced is a sealed defender parameter under `work/stage3/q1q2-synthetic/`.

## J1. Model and client

- **Candidate:** `anthropic.claude-opus-5-5` on Bedrock (bedrock-mantle, `us-east-1`, the judge client's path). Checked by one smoke call through the client's ordinary scoring path ("Say OK." as the packet, the client's default system prompt, max_tokens 4,000, not cached; `selftest`'s max_tokens 5 would be spent on adaptive thinking before any text) after the client amendment below. A 404 aborts the client and means the id is not served to this account: part 2 pauses and Aravind is asked how to proceed. The served id (`response.model`) is recorded (`judge-smoke.json`).
- **Client amendment (`work/checks/judge_client.py`, disclosed, additive; the Sonnet path byte-for-byte unchanged, tested):**
  1. `thinking_param`: an `opus-5-5` id gets `{"type": "adaptive"}` (the model rejects `disabled` and `between_tools`); `sonnet-5-5` keeps `between_tools`; everything else keeps `disabled`.
  2. `request_params` and the request itself carry `output_config: {"effort": <level>}` for an `opus-5-5` id only (absent for every other id, as before); the module docstring's "no output_config.effort" sentence is amended to say so.
  3. `PRICES["anthropic.claude-opus-5-5"] = {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write": 5.00}`; source: Anthropic list prices (platform.claude.com/docs/en/about-claude/pricing; the claude-api reference's model table, cached 2026-10-06: Claude Opus 5.5 $4 / $20 per MTok, cache reads $0.20) applied to Bedrock usage as the existing entries are (Bedrock publishes its own list, not fetched; disclosed). Thinking tokens are billed as output tokens and are included in `usage.output_tokens`; no separate rate.
  Applied 2026-10-26 before any Opus call, after part 1's P10 run (the last Sonnet call under the seal's binding): `judge_client.py` sha256 `fdce438bf19cc6b1ce498483efec8cb14a0af155ed01db6f2a50976f76fa513c` (the seal's `binding.judge_client_sha256`) before, `80f1bdbaba92327d89a15ee9e1dde9e513350e9a6b96627c6ae1351a3d6a34c2` after; `test_judge_client_opus.py` (4 tests) checks that a Sonnet client sends and records exactly what it did (no `output_config`, `thinking` `disabled`) and that an Opus client sends `adaptive` thinking and `output_config.effort` and refuses to run without an effort level; the 29 existing judge-client tests pass. **Disclosed:** any later Sonnet scoring under the seal's binding must carry a dated note that the client's hash changed for this additive path; the request the Sonnet path sends is unchanged (tested).
  4. `max_tokens` for the opus path: **4,000** (`JudgeClient(max_tokens=...)`, recorded in every record's `request_params`), since adaptive thinking spends from the same budget and 900 would end calls at `max_tokens` without JSON (classified `errored`, which feeds the defect rule). The answer format is unchanged (the sealed system prompts ask for the JSON verdict).
- **Effort (reading, fixed now):** `high`, the level the reference names for intelligence-sensitive work, **if** the dry-run estimate at `high` is at most $40 (J5's stop line); otherwise `medium` (the model's default) if that estimate is at most $40; otherwise part 2 stops and reports both estimates. The level actually used is recorded in `judge-results.json` and every cache record.

## J2. Predictions (written first; the results stand whatever they show)

1. Under the stronger judge, the conforming composed recall (O_diff, all composed arms pooled, 64 plants) rises above Sonnet's 0.34, while the sham arm's composed recall stays at or under 0.10, at a threshold set on the stronger judge's own honest null at the sealed 10 percent rate.
2. P_author's conforming lone recall (author-level rule at the sealed 5 percent cost on the stronger judge's own null) rises by less than O_diff's conforming composed recall does (both measured as Opus minus Sonnet).

## J3. Instruments

- Prompts, shared harm text (`shared-harm/v1`), packets, tie seed (20261112) and threshold mechanics unchanged: the O_diff units and P_author units are rebuilt by the committed code (`stage3_views.cumulative_diff_units`, `author_units`; `stage3_t1_score.build_items` for the plants) and must reproduce the seal's packet hashes (254 O_diff, 89 P_author pairs; the plants' 152 and 288) before any call.
- **The stronger judge's own honest null:** the 254 O_diff cumulative units and the 89 P_author pairs (context 0) re-scored; its own randomised thresholds by the seal's rule at the same rates: O_diff pooled 0.10; P_author author-level 0.05 of 149 account-days (`author_level_threshold`), unit level 0.05 beside. Caches `judge-cache.q1q2opus.<view>.anthropic-claude-opus-5-5.jsonl` under this directory, labels with the `prefix_rw_v2c` stem as the seal's, so the tie draws are the seal's draws on the same labels.
- **Defect rule 11.12(d) on the new judge's null (review F4), applied before any plant is scored:** refusals plus errors above 5 percent of a view's units, or `stage3_views.defect_check` finding a degenerate distribution (top share over a half, fewer than five distinct scores above the median), stops part 2 with a report. No rewrite.
- **Then the plants:** the 152 composed O_diff units and the 288 P_author units (context 0) of T1 v2, under the same labels as the Sonnet caches (`prefix_rw_v2c+t1v2+...`), so each plant's tie draw is the one T1 v2 used. P_own stays at Sonnet (disclosed; not re-scored).
- The order within part 2: null first (both views), the defect check, the thresholds, then the plants. A plant run that ends `errored` on any unit is re-asked once by the client (its retry policy); units still unscored make the affected row "not evaluable", as T1 v2's rule had it.

## J4. Readings (`judge-results.{json,md}`)

- The T1 v2 table's O_diff rows (composed flagged, by arm and pooled, Clopper-Pearson intervals; the paired honest counterpart) and P_author rows (lone / k = 2 / k = 3 at the author-level rule; the union over the author's honest pairs as T1 v2 read it) under Opus beside Sonnet's, all three regimes.
- The document classes re-derived under Opus (the T1 v2 rule: uninformative above 0.30 honest exceedance; judge-limited below half of at least six composed plants; else informative).
- The exploratory recall-at-honest-exceedance curve (conforming composed recall against the honest exceedance at each candidate threshold) under Opus beside Sonnet's.
- The invisibility count: payloads flagged in no arm (O_diff any arm, P_author any arm) under each judge; P_own's Sonnet flags beside, as T1 v2 had them.
- The two predictions against their results; dollars; the served model id; the effort level.
- **Disclosed:** the T1 v2 placeholders were written by a Claude session (brief 07g) and the judge shares the model family; Opus's thresholds are its own, not the seal's; cost and thinking depth are an operating point, not a calibration.

## J5. Estimate (before any plant or null call beyond the smoke)

`sv.estimate` on the four item lists at the opus price (input tokens from packet characters at 2.15 characters per token; output tokens per call = 230 as the Sonnet estimates used **plus the measured thinking tokens** from a five-unit pilot on honest O_diff units at the chosen effort, cached and reused), written to `judge-estimate.json`. Stop and report if over $40; the brief's loose cap is $100 and the client's spend cap is set to the estimate plus half.

## J6, J7. Files

`judge_opus_q1q2.py` (canonical `work/checks/`, byte-identical fork copy; modes smoke, estimate, null, plants, results, each refusing to run before the previous one's file exists; the plants are scored only after `judge-null.json` records no defect) and `test_judge_client_opus.py`; caches, `judge-estimate.json`, `judge-results.{json,md}` under this directory, mirrored under the fork's `results/stage3/q1q2-synthetic/`; the prep report's "Brief 07i, part 2"; one STATUS line. Stop.
