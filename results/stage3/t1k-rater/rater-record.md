# Brief 07k rater record (K1 to K3)

- **Session:** independent rater, opened 2026-10-26 (session id `local_fd809567-640a-42fa-ab76-ee1ed0f330c9`).
- **Model id:** `claude-fable-5-1` (reported by the app's session metadata).
- **Effort:** `high` (reported by the app's session metadata; the model cannot observe its own effort setting directly).
- **Rating passes:** two sub-agents of the same model (`claude-fable-5-1`), each in a fresh context, each given only the rubric, the two stripped files and the day-0 document states. The rater session itself scores nothing, because it has read the brief.

## Files read before writing the rubric (and nothing else)

1. `README.md`
2. `PLAN.md` section 1
3. `work/stage3-research-design-2026-10-19.md` section 3
4. `work/mole-fork/scripts/stage3/stage3_t1v2_checks.py` (read-only, to find how the day-0 states are produced: `DOCS` and `document_states`, which take the seed state from `mole.seeders.seed_class_docs.class_seed_mapping`)
5. `work/mole-fork/scripts/stage3/stage3_rater_strip.py` (read-only, for the stripped files' field names)
6. The six class documents' day-0 states, rendered from `class_seed_mapping()` to `work/stage3/t1k-rater/doc-states-day0.md`
7. `STATUS.md` "Now" block and log lines mentioning 07k (to find where to write the status line and the stripped files' committed hashes; no payload content there)

Not opened: `key.json`, any `payloads-*.json`, anything under `work/stage3/t1/`, `t1v2/`, `t1v3/`, `q1q2-synthetic/`, `views-calibration.md`, judge caches or results, the prep report, decision memos, the roadmap, the sealed file, persona or memory files.

The stripped files were not opened until after `rubric.md` was written and hashed (see the order of entries below).

## Order of events

(appended as the work proceeds)

1. 2026-10-26: `rubric.md` written; sha256 `2f5fe209d16f77418d3ad468311b33a9cdbb4a47b056bdd86a9f3b52d03fc8ad`. `rubric-passes.md` is sections 1 to 3 of it verbatim (what each pass receives; section 4, the predictions, is withheld from the passes); sha256 `39a0723590d34cbf7d93d0f71a5ebbd50bd1c7df9d924097f77a28e7751de74d`. `doc-states-day0.md` sha256 `d0f3fbae0e1b67125196263395edcd658c000458dc54b8460e9a691e4edf31e0`. No statement or payload text had been opened at this point. Committed to the fork before the stripped files were opened (commit hash below).
2. 2026-10-26: before any pass ran and before any statement was opened, rule 2 of rubric section 2 was reworded (the phrase "your own suspicion of the author" became "your own guess about the author's intent"), because the brief forbids the words monitoring, suspicion or harm detection in any rating prompt and the pass-facing excerpt is part of that prompt. No other change. New sha256: `rubric.md` `81fc6e0e5c66decf674b0b069c47b3c42dc56372f73a6f2223866a15fbc07bc8`, `rubric-passes.md` `985fe0b2545e83a7c26b0e6851f202de5142bf0ee7041efad27bc89ac1341405`. The earlier commit (fork 864ac20) holds the first wording. The stripped files' structure (field names and counts only: 348 statements, 116 payloads, 36 texts repeated once each, 48 payloads with an empty composed_effect) was inspected by script without printing any text, before this commit.
