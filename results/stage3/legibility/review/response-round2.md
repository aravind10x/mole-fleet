# Brief 23: response to codex round 2 (blue, 2026-10-31; no API call made)

All five required findings and the optional ones were accepted.

1. **D_whole and D_part decoupled.** `Records.item_stat` computes D_whole when the whole is scored, D_part when all three parts are, L when both are (each with its own status). Regime tables report D_whole and D_part over their own denominators (n beside each); sentence 3 reads D_part on its own denominator; sentence 4b gates both of its statistics' denominators at 90 percent.
2. **Retest.** `within_regime_pearson` removes each regime's r0 mean from r0 and its r1 mean from r1; `bootstrap_ci` resamples the original (regime, r0, r1) records and refits the statistic (centring included) in every resample; the test-only interval is added; the mean r1 minus r0 shift is reported beside ICC(1) and the absolute difference.
3. **JSON envelopes.** `json_objects` scans structures with string tracking: every top-level structure must close and decode, or the reply is unparseable; a top-level array and nested objects are never candidates. Every score-carrying candidate is validated (reason absent or a string; null rejected) and numerically normalised (1 and 1.0 agree).
4. **Prices and routes pinned.** The estimate records the sha256 of `models-v0.json` and `routes-v0.json`; `run` refuses when either differs.
5. **Rendering pinned.** items-v0.json records the sha256 of the seeder's six day-0 texts and of every rendered reader packet; `dry-run` and `run` refuse on drift, and on a failed day-0 Markdown check.

Optional: kappa beside without reader prose refusals; the disclosures name sentence 2's null-side gate, the one-pass policy, informative missingness and the response-based spend accounting (an abandoned timed-out OpenRouter request may still bill); the run stops at the estimate's own `stop_at_usd`.

items-v0.json rebuilt (same draws; rubrics 7ed4ae1a; day-0 bade5fab…, packets 4ca2d554…); estimate unchanged at $28.23 (upper $54.02, stop $56.47).
