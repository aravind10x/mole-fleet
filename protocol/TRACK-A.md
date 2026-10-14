# TRACK-A: budget-paced escalation across a fleet (Q3, secondary chapter)

Pre-registration for the pacing chapter (`PLAN.md` v5.2, Q3). Written before any label row is read by the policy simulator and before any judge score exists on the released corpus. Carries forward A1 to A6 of `briefs/03-stage2-kickoff-2026-10-14.md` with the changes recorded in section 9. The question: given a cheap score for every account-day and an expensive judge under a daily budget, which allocation policy wins in which attack-arrival regime, and how many judge calls does each policy actually make.

Nothing below is changed after the freeze recorded in `STATUS.md` ("Track A freeze"). If a policy is found to be misdesigned before any label is read by the simulator (while it is developed against the cheap scores and a mock expensive table), it is fixed and re-committed, and the freeze hash is the later commit. After the simulator has read labels, no policy changes; later ideas go to `work/stage2/post-hoc-policies.md` and are excluded from every figure.

## 1. Unit, days, data

- **Corpus.** `gpt53_single_day` (primary). `kimi_k26_single_day` only if the stage has capacity after everything else in brief 04 is done (then A2 to A4 are repeated unchanged).
- **Unit.** An account-day is (account, `ts[:10]`) with at least one `exit_code == 0` event. Day index 1 is the corpus's first date (2026-04-06 for gpt53); there are 30 days.
- **Positives.** Label rows with `outcome == executed` are the primary positive set; `attempted` is a secondary positive set reported separately. Honest account-days are account-days of accounts with no label row on any day (never-labelled). Account-days of labelled accounts on unlabelled days are neither and are excluded from recall and honest-flag denominators (they are still scored and still compete for budget).
- **Days.** Online evaluation on days 6 to 30. Days 1 to 5 are calibration for the cheap tier's pooled fit and for the NP quantile; calibration never reads labels. Disclosed: calibration days contain attack account-days at the corpus base rate.

## 2. Cheap tier `c(a, d)`

`ZScoreAnomalyMonitor` (`mole/monitors/classical/anomaly.py`, length-normalised 18-feature rollup, robust median/MAD, clipped mean deviation), **fit on all account-days of days 1 to d−1** (rolling, refit per day), scoring the rollup row of (a, d). `is_malicious` is set False on every event the rollup sees. For days 1 to 5 a pooled in-sample fit on days 1 to 5 provides `c_cal`, used only to set NP's quantile and the burst statistic's initial history.

Separately, a boolean layer-1 flag from the Stage 0 non-noisy structural matcher set (`work/checks/upstream_matchers_as_detectors.py`, variants firing on more than 5 percent of never-labelled account-days dropped) is reported in every table with the caveat that those matchers are upstream's own labelling matchers, written knowing the threats, and are therefore a ceiling for layer 1, never a protocol-compliant rule set.

Script: `work/checks/score_cheap_tier.py` → `work/stage2/scores/<corpus>.cheap.parquet`. The cheap tier's own AUROC (executed positives against never-labelled account-days, evaluation days) and recall at k on the original schedule are the baseline row; MOLE's best classical baseline on this corpus is 0.694 AUROC, the sanity check.

## 3. Expensive tier `e(a, d)`

The per-account judge P: one call per account-day over that account-day's own successful events, packet built exactly as in Stage 1 (`work/checks/f1_upstream_row.py::p_packet`: the P intro, `render_event` lines, the 150,000-character packet bound with middle elision), the same system prompt (`scripts/first_cut_monitors.py::JUDGE_SYSTEM`, scaffold `c3-release-judge/v2`), `max_tokens` 900. Called through `work/checks/judge_client.py` on Amazon Bedrock (Mantle endpoint, region us-east-1).

- **Model.** `anthropic.claude-sonnet-5-5` if the AWS account has access to it at launch, else `anthropic.claude-sonnet-5` (at the time of writing Sonnet 5.5 returns "model does not exist" on this account; the realised model id is recorded in the Track A freeze entry and in every score record). Sampling parameters cannot be sent to the Claude 5 family (the SDK and the API reject `temperature`); thinking is turned off (`between_tools` on Sonnet 5.5, `disabled` on Sonnet 5). This is a provider change from Stage 1 (OpenRouter, temperature 0), recorded as such; the refusal behaviour is re-smoked (T0).
- **Every call returns one of three outcomes:** scored (an integer 0 to 100), refused (`stop_reason == "refusal"`), errored (no parseable verdict after the retry policy). Tokens and dollars at the Bedrock list price are recorded per call.
- **Refusal policy.** A refused packet is surfaced (refusal escalates). Recall under refusal-as-zero is a sensitivity. Errored calls count as not surfaced and are reported.
- **Coverage.** Every account-day of days 6 to 30 (about 3,700 calls; expected about $160 at Stage 1's 19.7k input tokens per call and $2/MTok, plus output). Scores are computed label-blind: nothing in the packet or prompt references labels or threat names.
- **Detection threshold θ = 50**, the scaffold's own flag threshold (`"flag": true if score >= 50`), fixed by the prompt before any score existed. Sensitivity: θ at the 95th percentile of `e` over the never-labelled account-days of days 6 to 10 (disclosed: this reads evaluation-day scores, not labels).

Script: `work/checks/score_expensive_tier.py` → `work/stage2/scores/<corpus>.expensive.parquet` (score, outcome, tokens, dollars, model, stop details per call; every raw verdict kept in the cache JSONL).

## 4. Budgets and policies

**Budgets k** (expensive calls per day): 2, 5, 10, 15, 20. k = 10 is primary (MOLE reports recall at 10 per day).

Each policy chooses, each evaluation day `d`, which account-days of `d` receive an expensive call, using only `c` (today's and past), the results of its own past expensive calls, and history. `N_d` = active accounts on day `d`. A policy's **deployed call count** is the number of calls it actually made over days 6 to 30 under each k and regime; it is reported beside recall as the cost statistic (policies with carry-over or thresholds do not spend exactly k per day).

- **U, uniform.** k account-days of `d` drawn uniformly at random (`random.Random(20261014 + d)`).
- **S, selective.** The top-k of `d` by `c` (MOLE RQ5).
- **C, per-account adaptive credence** (Wen et al. 2024's macro-protocol applied per account). Per account `a`: `π_a(0) = 0.5`; on each day `π_a(d) = λ π_a(d−1) + (1−λ) q_a(d)` where `q_a(d)` is the within-day percentile rank of `c(a, d)` in [0, 1]; after an expensive call on (a, d): `π_a(d) ← 1` if surfaced (`e ≥ θ` or refused), else `π_a(d) ← 0.5 π_a(d)`. Choose the top-k by `π_a(d) · q_a(d)`. `λ ∈ {0.8, 0.9, 0.95}`.
- **PACE, pacing with a spend target, a rolling window and a burst reserve** (the ads-delivery loop). Parameters: window `w ∈ {3, 5}` days, reserve `r ∈ {0, 0.2, 0.4}`, controller gain `η = 0.2` (fixed). State: a yield table `Y[b]` over ten buckets `b` of within-day `c`-rank decile, each initialised with pseudo-counts (1 surfaced, 1 not); every expensive result updates its bucket (surfaced = `e ≥ θ` or refused). Each day:
  1. Window budget `K = k · w`; available `A_d = K − (calls made on days d−w+1 .. d−1)`.
  2. Burst: `burst(d)` is true if the total `c` mass of day `d` exceeds the mean plus one standard deviation of the daily `c` mass over the previous five days (days before `d`, using `c_cal` for days 1 to 5).
  3. Spendable today: `n_d = min(A_d, 2k)` if `burst(d)`, else `n_d = max(0, min(A_d − r · K, 2k))`.
  4. Controller on the yield threshold `y*` (initial 0.5): plan-to-date `= k · (d − 5)`; if calls made so far exceed the plan, `y* ← y* (1 + η)`; if they fall short by more than k, `y* ← y* (1 − η)`; clamp to [0.01, 0.99].
  5. Call set: rank today's account-days by `Y[bucket(a, d)]` then by `c`; call those with `Y ≥ y*`, at most `n_d`.
- **NP, static threshold** (the cost-constrained-monitors allocation). A `c` quantile is fixed from the calibration days so that the mean calls per day over days 1 to 5 under `c_cal` equals k; on every evaluation day, every account-day with `c` above that quantile value is called (spend varies by day; the deployed call count shows by how much).
- **ORACLE, labels known.** Every positive of `d` first, then the rest by `c`, cut at k. An upper bound only.

Every parameter grid above is swept; nothing is tuned after seeing results.

## 5. Metrics

- **Allocation recall**: share of positives that received an expensive call.
- **Detection recall**: share of positives that received a call and were surfaced (`e ≥ θ` or refused).
- **Honest flag rate**: share of never-labelled account-days surfaced.
- **Deployed judge-call count** per policy, k and regime, and **dollars per corpus per policy** at the measured mean cost per call.
- **Budget-AUC**: detection recall integrated over k ∈ {2, 5, 10, 15, 20} (trapezoid, normalised by 18).
- **Expensive-tier quality**: AUROC of `e` (refused treated as 100; sensitivity refused as 0) and of `c` over evaluation-day executed positives against never-labelled account-days; detection recall of the expensive tier at full coverage.
- **Intervals**: cluster bootstrap over the 38 labelled insider accounts (resampling accounts, keeping each account's positives together), 1,000 resamples, seed 20261014; reported for every recall and for every policy difference.

## 6. Regimes

The original schedule is primary. Secondary regimes re-time positive account-days while keeping every account-day's `c` and `e` fixed: a re-timed positive is treated as occurring on its new day and competes there for budget.

- **Rate**: subsample positives to 50 and 25 percent (`random.Random(20261014)`), the rest removed from the day.
- **Burstiness**: all positives placed on 5 of the 25 evaluation days (chosen at random with the same seed, positives assigned to them uniformly); spread uniformly over the 25 days; original.
- **Adversarial placement**: positives placed on the days whose honest `c` mass is highest (the worst case for S and NP), in order.

Disclosed: re-timing breaks multi-day context for C and PACE's yield history; the original schedule is the only regime for C's headline.

## 7. Primary comparison and kill rule

- **Primary comparison, fixed now:** PACE (w = 3, r = 0.2) versus S at k = 10 on the original schedule, detection recall, `gpt53_single_day`, with the bootstrap interval on the difference. Everything else is secondary or exploratory and labelled so in the results.
- **K2:** if the expensive tier at full coverage does not beat the cheap tier on AUROC (executed positives versus never-labelled account-days), pacing is a null result on this corpus: it is reported as one, the regime grid is run anyway for completeness, and the second corpus is recommended at Checkpoint 2.
- **K1 (from T0):** judge refusal above 30 percent on either smoke set stops scoring until the prompt is fixed within the scaffold; the fix is reported.

## 8. Outputs

`work/checks/escalation_sim.py` loads the two score tables and the labels, implements the six policies exactly as above, runs every (policy, k, regime, parameter) cell, bootstraps, and writes `work/stage2/a-track-a-results.md` (one table per budget, the primary comparison first with its interval, the deployed call counts, then the regime grid; each cell labelled primary / secondary / exploratory) and `work/stage2/fig-phase-diagram.png` (regime axes: rate × burstiness, with adversarial placement as a marked column; cell colour is the winning policy by detection recall at k = 10; a second panel for allocation recall; a third for deployed calls).

## 9. Changes from brief 03's A1

- Judge through `work/checks/judge_client.py` on Amazon Bedrock; model id rule and sampling constraints as in section 3.
- θ is the scaffold's own threshold (50), not the 95th percentile of calibration-day scores, because days 1 to 5 are not scored by the judge under brief 04 (only days 6 to 30 are).
- Deployed judge-call count added as the cost statistic.
- PACE's controller, yield table, burst statistic and spend cap written out so the simulator is a transcription (brief 03 described them in prose).
- NP's quantile is fixed from `c_cal` on days 1 to 5.
- Errored calls are a third outcome beside scored and refused.

## 10. Freeze record

The commit hashes of this file and of `work/checks/escalation_sim.py` are recorded in `STATUS.md` under "Track A freeze" before the simulator reads any label row. The scoring scripts read no labels except to write the `is_positive` columns that the simulator joins on.

## Errata (recorded before any label row is read by the simulator)

- 2026-10-14, after the cheap tier was built: the fork's `ZScoreAnomalyMonitor` rollup has 20 numeric features, not 18 (upstream's docstring predates the addition of `public_link_count` and `external_share_count`; the fork's code is identical to `vendor/mole`). Section 2 should read "20-feature rollup". The rollup counts every event of the account-day, failed calls included (upstream's definition); an account-day still needs at least one successful event to exist. Day index is the rank of the date among the corpus's dates (30 weekday dates; day 6 of gpt53 is 2026-04-13). Neither changes a policy or a threshold.
- 2026-10-14, after the T0 smoke: K1 was evaluated on `anthropic.claude-sonnet-5` (0 refusals of 40 on both corpora, scored 40, errored 0; `work/stage2/judge-smoke.md`). Sonnet 5.5 remains unreachable on this AWS account; the realised judge model for the full run is recorded in the Track A freeze entry.
