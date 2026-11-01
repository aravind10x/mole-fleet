# Brief 31 (blue; a fresh session on Opus 5.5 or Sonnet 5.5; $0, no API call; before S3 opens): the judge client's default-path equivalence against the sealed nulls, and S3's pre-flight pin

Written 2026-11-01 night by the coordinator from the review session's proposal after brief 27 (brief 15 A6.21). Working directory: the project root `/Users/aravind/KruxAI/tais-project-selection`; the fork is `work/mole-fork` (branch `stage3`). This brief reads code and cached replies and prints counts; it calls no judge.

**Why.** S3's per-agent and `O_diff` judges run through `work/checks/judge_client.py` (now 72d394e3, unchanged since brief 23) and `judge_openrouter.py` (e812157c). The sealed nulls and thresholds S3 reads against were produced by an older client. Brief 23 changed the client (a reply parser with a refused marker; refusal retries; a spend guard; moderation 403 read as a refusal on request; the Sonnet 5.5 route). The retries and the guard were verified to keep their defaults; **the parser change was not verified to leave default-path parsing of judge replies unchanged.** A parsing difference would shift S3's scores against sealed thresholds with no warning. A test in the suite binds the client's hash and now fails; re-binding it alone would hide the question it is there to answer.

## G1. The diff ($0)
Locate the failing test that binds `judge_client.py`'s hash (the T1 v3 scoring test; name it and its bound hash). Diff `judge_client.py` from that bound hash to 72d394e3 (the fork history holds both) and list every change on the **default path** of the views S3 uses (the per-agent views and `O_diff` under Sonnet 5, Opus 4.8 and GPT-6 Sol on Bedrock): parsing of a reply into score, flag and rationale fields; defaults of retries and the guard; anything that alters a returned score, flag or refusal status when no new option is set. Changes off the default path are listed separately.

## G2. The re-parse ($0)
By script, re-parse the cached raw replies behind the sealed nulls and thresholds S3 reads against (the judge caches those nulls were computed from; name each cache by path and hash; open them by script only, printing counts) with the current parser, and compare with the recorded parsed scores, flags and refusal statuses: agreement counts per view and judge; every disagreement named by cache label and field, never by content. Expected: 100 % agreement. Any disagreement is reported with its direction (score up or down; flag flipped; refusal status changed).

## G3. The re-bind ($0)
If G2 shows equivalence, re-bind the test to 72d394e3 by a dated note in the test file and in `work/stage3/b3/judge-client-equivalence-v0.md`, with G1's diff summary. If it does not, stop: report the disagreements and their direction; the coordinator decides (re-sealing the nulls under the current parser, or restoring the old default path) before S3.

## G4. S3's pre-flight pin ($0)
Write a pre-flight check for S3 (a small script or a test S3 runs first) that computes the sha256 of `judge_client.py` and `judge_openrouter.py` and refuses to start unless they equal the pinned values S1 records (72d394e3 and e812157c at S1's commit), printing the hashes it found. **Rule for later client changes (brief 29-B's E0-7 adds provider preferences to `judge_openrouter.py`):** the change must be opt-in with every default unchanged and tested; S3's pin is moved to the new hash only by a dated note after G2's re-parse is repeated on that hash and shows equivalence; S3's record states which hashes it ran on.

## G5. The writer-path test
`test_stage3_write_yield.py` fails for a reason unrelated to the judge route; fix it or re-bind it by a dated note with the reason. It does not gate S3.

## Outputs
`work/stage3/b3/judge-client-equivalence-v0.md` (G1's diff summary, G2's agreement table, G3's decision, G4's script and its hash, G5's note); the pre-flight script with its test; one STATUS line; the fork mirror; this brief's row in `briefs/INDEX.md`.

**Do not:** call any judge; print any reply's text, rationale or item content (counts, labels, fields and hashes only); change `judge_client.py` or `judge_openrouter.py` (a needed change is reported, not made); open `work/stage3/red/`, persona or rater-key files.

**Done means:** G1's diff is listed; G2's agreement is 100 % or every disagreement is named with its direction and the brief stops at G3; the pre-flight script exists with its test; G5 is fixed or re-bound by note; the record file exists with its hash in STATUS. S3 does not open before G2 is resolved and G4 is in place.

---
Changelog: 2026-11-01 night, written by the coordinator from the review session's proposal (brief 15 A6.21).
