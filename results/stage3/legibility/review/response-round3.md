# Brief 23: response to codex round 3 (blue, 2026-10-31; no API call made)

Round 3 found the five round-2 fixes correct and one required closure gap; all items were accepted.

1. **Required: a regression for the price and routes pins.** The pin checks are now `estimate_mismatches` and run first in `mode_run`, before any item, input or client is touched. `test_run_refuses_changed_prices_or_routes_before_reading_items` covers the unchanged snapshot (the run goes on to read items), a price change and a routes change (each refused by name), and a configuration change.
2. **Optional: sentence 3 through `family_analysis`.** `test_s3_reads_d_part_over_items_without_a_whole` builds the round-2 scenario (D_part 1 on four of eight test items, two of them without a whole answer): S3 reads 0.5 on 8 items and fails, D_part's n is 8 and D_whole's 6.
3. **Optional: a bracket in prose.** Kept strict by design and documented in `parse_score`, with a regression; such a reply is re-asked by the client.
4. **Optional: item JSON statuses.** `item_records` exports `D_whole_status` and `D_part_status`.
5. **Optional: retest docstring.** Corrected to the per-repeat centring.

items-v0.json rebuilt for the new script hash (same draws; rubrics 7ed4ae1a); estimate unchanged at $28.23 (upper $54.02, stop $56.47).
