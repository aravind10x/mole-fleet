# Judge dependence of the composed view (brief 07n, part A; written 2026-10-26 before the first call; blue side)

Replaces 07i part 2 (Opus 5.5 stopped at its null under 11.12(d)). Exploratory: no sealed instrument moves; Sonnet's readings stand as the pilot's instruments. Every number is a sealed defender parameter under `work/stage3/q1q2-synthetic/`.

## A1. Models (resolved 2026-10-26 from `GET https://openrouter.ai/api/v1/models`; `judge-dep-models.json`)

| named by Aravind | OpenRouter id (reading: the base variant, not `-pro`, `-prime`, `-flash` or `:batch`) | context | prompt $/MTok | completion $/MTok |
|---|---|---|---|---|
| Kimi K3 | `moonshotai/kimi-k3` | 1,048,576 | 0.18 | 20.00 |
| GLM 5.3 | `z-ai/glm-5.3` | 1,048,576 | 0.0699 | 1.40 |

Both are served. Settings: the provider default for thinking (no `reasoning` parameter sent; reasoning tokens, where the provider reports them, are recorded per call), `temperature` 0.0 (the fork client's default for every call, recorded; the Bedrock judge sends none), `max_tokens` 4,000, no seed. Routed through `mole/llm/openrouter.py` (`OpenRouterClient.complete`) with **key 1 only**: `OPENROUTER_API_KEY_2` is removed from the scorer's process environment so the client cannot rotate; a 402 or key-limit 403 is a stop. Caps checked 2026-10-26 before any call (values, never keys): key 1 limit $150, remaining $150 (weekly reset); account balance well above $40. No third model without a new plan.

## A2. Question and predictions (written first; the results stand whatever they show)

Is the composed view's conforming recall at a 10 percent honest cost a property of the judge or of the content?
1. Under each judge, the conforming composed recall (O_diff, all composed arms pooled, 64 plants, at that judge's own pooled rule at the sealed 10 percent rate) lies within 0.15 of Sonnet's 0.34, and the sham rate stays at or under 0.10.
2. The set of payloads invisible under every judge (flagged in no arm by O_diff and by no arm's P_author, each at the judge's own rules) holds at least 8 of the 13 invisible under Sonnet.
3. P_author's conforming lone recall (author-level rule at the sealed 5 percent cost on the judge's own null) stays under 0.3 under every judge.

## A3. Instruments

- The sealed prompts (`stage3_views.system_prompt`, shared harm text `shared-harm/v1`) and packets unchanged; units rebuilt by the committed code and checked against the Sonnet caches' keys (sha256 of the packet) before any call: honest O_diff 254, honest P_author 89 (context 0), plants O_diff 152, plants P_author 288. T1 v3's units do not exist (07l not run), so none are scored.
- **Each judge's own honest null and thresholds:** O_diff pooled rule at 0.10 and P_author author-level rule at 0.05 of 149 account-days (unit rule at 0.05 beside), by `randomised_threshold` / `author_level_threshold` with the sealed tie seed 20261112 and the seal's labels, so tie draws are the seal's draws. Per-document honest exceedance and the uninformative bar (0.30) as the seal has them.
- **Defect rule 11.12(d) on each judge's null, before any plant is scored:** refused or errored above 0.05 of a view's units, or `defect_check`'s degenerate distribution (one score over half; fewer than five distinct scores above the median), stops that judge with a report and no rewrite; the other judge continues. Outcome classes for an OpenAI-style response **(reading):** `finish_reason` `content_filter` or a provider refusal field = refused; empty content, a `length` stop without JSON, or no parseable verdict = errored (a refusal written as prose counts as errored; both count toward the 0.05 line); the client re-asks an errored unit up to twice as the Bedrock client does.
- **Cache:** one JSONL per (view, judge) with the Bedrock client's record shape (`cache_key` = view|label|sha256(packet), outcome, score, flag, rationale, model, model served, tokens including reasoning tokens, provider-reported cost when present else list price, request parameters, prompt version). A cache holds one model and one prompt version.
- The P_author reading is the T1 v2 one (the union over the author's honest pairs at the author rule; the judge's own honest pairs); P_own stays at Sonnet (disclosed).

## A4. Estimate and cap

Per judge, after a five-unit smoke on the first five honest O_diff units (README, day-0 boundary; under $0.10 for both judges at list prices): input tokens from the smoke's observed prompt tokens per packet character (fallback 2.15 characters per token), output tokens per call = the smoke's mean (reasoning included; at least three scored units required, no fallback), at list prices; the total at the smoke's maximum output tokens and at max_tokens beside. **Stop and report if the part's estimate (both judges) exceeds $30; cap $40 for the part**, enforced as one allowance across every cache, smoke and re-ask (cumulative cost from the records).

## A5. Readings (`judge-dep-results.{json,md}`)

The T1 v2 table's O_diff rows (composed flagged by arm and pooled, Clopper-Pearson, the paired honest counterpart) and P_author rows (lone / k = 2 / k = 3) under each judge beside Sonnet's, all three regimes; the invisible-payload sets per judge and their overlaps (with Sonnet's 13); the document classes re-derived per judge (T1 v2's rule); the recall-at-honest-exceedance curve per judge; Pearson and Spearman correlations of scores with Sonnet's on the shared units (honest and planted, per view); refused and errored counts by document; dollars and tokens per judge. A regime with an unscored unit under a judge is not evaluable for that judge. **Disclosure (wording corrected 2026-10-26, N1):** The placeholder writer's family (Claude) differs from these judges, so the writer-judge caveat does not apply to these rows. A different caveat does: Kimi K3 is the family that generated the honest world and will generate red's live text, while the placeholders are Claude-written, so a Kimi judge could score Claude-style text as unusual on authorship rather than content; GLM 5.3 is less exposed but the same reading applies. The sham arm is the control for this; the judges' thresholds are their own, by the seal's mechanism; cost and provider-default reasoning are an operating point, not a calibration.

## A6 to A8. Files and order

`work/checks/judge_openrouter.py` (the OpenRouter judge adapter, same cache format, tested offline with an injected client) and `judge_dep_q1q2.py` (modes models, smoke, estimate, null, plants, results per judge; each refusing to run before the previous one's file exists and checking the instrument identity), byte-identical fork copies; outputs `judge-dep-models.json`, `judge-dep-smoke.<judge>.json`, `judge-dep-estimate.json`, `judge-dep-null.<judge>.json`, the caches, `judge-dep-results.{json,md}`; the prep report "Brief 07n, part A"; one STATUS line. Order: this plan committed; adapter and tests; smoke both; estimate (stop line); null and defect check per judge; plants; results; report; commit, push.

## Dated readings and amendments

- **N2, reading rule (coordinator, 2026-10-26 13:37:04; the table `judge-dep-results.{json,md}` was written at 13:36:37, so the rule was written 27 seconds after the table and blind to it; neither the coordinator, the review session nor Aravind had read the table; applied to the existing table, not regenerated; reported as "a reading rule written after the table was produced and before anyone read it", never as pre-registered):** if a judge's sham rate at its own 10 percent rule exceeds 0.10, that judge's conforming recall is reported as not interpretable as content detection, and only its invisible-payload overlap with Sonnet's is read.
- **N3 (2026-10-26):** wherever a nominal reading appears: 288 planted account-days come from 36 authors; the bootstrap resamples plants, so nominal intervals are too narrow; attributable readings condition out the authors' honest standing.
