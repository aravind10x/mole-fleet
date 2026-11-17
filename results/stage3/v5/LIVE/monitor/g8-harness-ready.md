# G8: the harness side is ready, nothing scored (blue harness session, 2026-11-17)

Under Aravind's decisions 1(d) to 1(g) (`LIVE/g8/aravind-decisions-2026-11-17.md` 01dc7663). $0, no model call.

## Code (tests by module name)
- `work/checks/stage3_live_monitor.py` cb66e63196b93f68f45ed813c5ea112ae13ff6f763686fe41f1f954c4cdf907b; test 7b79a409c1abdbb459ec496b1447434aed3aab7f73233b592ab6d19ad96e72c5, 14 pass.
- `work/checks/stage3_live_perplant.py` cf6ad63e0cc35270e373f71e04916ea7ec0da91c82607a648938c3e20f47cd27; test ca475e3a6eb4b079662f6171f0ae8fbc7365e39704fb734bce9facf87725f7b8, 8 pass.

## 1. Two envelopes, sealed by construction
- **Output files:** each scoring run writes `machinery-<tag>.json` and a separate `outcome-<tag>.json` in its campaign folder. The machinery file carries the outcome file's name and sha256.
- **Outcome fields:** scores, flags, thresholds and tie shares, null scores, disagreements, k, P_m, per-plant flags, offline flags and the sentence.
- **Sealed print path:** the only print path, `emit()`, refuses to print any outcome key anywhere in a structure, and the machinery writer refuses any outcome key. There is no unsealed mode.
- **Removed:** the earlier score mode printed flag counts; that print is gone.
- **The judge cache:** the client's cache holds every score. It is an outcome file and is never opened.

## 2. Field lists for live-design
- `LIVE/g8/fields-harness.json` 69e4bc53a9317db0…: 87 fields, with file, meaning and the proposed class, machinery or outcome.
- `LIVE/g8/inputs-harness.json` 9d81682d1343e906…: the input fields, by script and source, each with where it was last shown present.

## 3. Campaigns and cost
- **Folders:** `--campaign NAME` gives each campaign its own folder, `LIVE/monitor/campaign-<NAME>/`, holding the cache, the smoke cache, the ledger and outputs. A marker names the campaign, and a folder marked for another campaign is refused. The G8 rehearsal uses `--campaign g8`, starting from an empty cache. The live run uses `--campaign live`, with its own empty cache and its own fresh null, as registered.
- **Price basis:** the single-statement scoring run's measured $0.0234 per unit (350 units, $8.175).

| campaign | null (254) | document-day units | one-plant (11) | 20-unit smoke | total |
|---|---|---|---|---|---|
| G8 rehearsal (3 branches × 6 documents × 2026-04-08 and 04-09, at most 36) | $5.93 | $0.84 | $0.26 | $0.47 | **about $7.5** |
| live (2 branches × 6 documents × 6 days, at most 72) | $5.93 | $1.68 | $0.26 | $0.47 | **about $8.3** |

- **Under $12, so nothing is cut.**
- **What the scripts allow:** `--through-day` limits the days scored. The null is fixed at the 254 units as built; neither script can score a reduced null. A rehearsal could skip the 20-unit smoke ($0.47), but the field check needs the full null, because the null's span counts and rules are fields.

## 4. Input fields fail loudly
- **Monitor** (`check_input_fields`, run before any unit is built):
  - on every row: `ts`, `service`, `action`;
  - on an ownCloud content write: `exit_code`, `account`, `task_id`;
  - on a successful one (exit code 0): `args.path`, `args.content`.
  - A failed write is not applied and need not carry `args` (the prefix holds 126 failed writes without `args.content` and 3 without `args.path`).
- **Per-plant:**
  - placement-record fields (`check_record_fields`);
  - the 2 added rows' `event_id`, `action` and `task_id`;
  - the content row's `event_id`, `task_id`, `action`, `resource_id`, `args.path`, `args.find` and `args.replace`, in both the one-plant corpus and the planted start.
- **Failure:** each check exits naming the field and the row.
- **Re-run on real data after the change:** checks (a) and (b) 11 of 11; dry build 11 units; monitor dry run on the prefix and on the rehearsal's planted start, 6 units each.

## 5. G8 is rehearsal
- G8's outcome files stay unopened until the live result, and are reported whatever they show, as a one-day rehearsal.
- They are excluded from every live reading and never pooled.
- G8's campaign folder is never reused by the live campaign.
