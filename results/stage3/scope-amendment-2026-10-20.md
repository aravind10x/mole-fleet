# Dated amendment to the frozen grouping measure's like-for-like scope (2026-10-20)

Brief 07b, task F2.6; design v4 (`work/stage3-research-design-2026-10-19.md`) section 11.6, verbatim: "The frozen grouping measure's like-for-like scope is amended, dated, to see ownCloud and GitLab documents, since the room statistic and the co-touch generators must read the document class; the Stage 2b numbers are not recomputed."

## What changes

- `work/checks/mole_corpus.py` (fork copy `scripts/track_b/mole_corpus.py`, byte-identical): a named, dated amendment table `SCOPE_AMENDMENTS = {"stage3-shared-documents-2026-10-20": ("file", "repo")}` with a switch (`set_scope_amendment`, `scope_amendment_context`, `like_types()`); `scope_types("likeforlike")` returns the frozen tuple `("ticket", "checkpoint", "eval", "secret", "group", "org_record")` when no amendment is on (the default) and that tuple plus `file` (ownCloud) and `repo` (GitLab) under the amendment. Mail and chat stay in the all-services scope only.
- `work/checks/generators.py` and `work/checks/grouping_measure.py` (fork copies byte-identical): the three reads of `mc.LIKE_TYPES` that select like-for-like write touches for the corpus index and the prior-touch matrix now read `mc.like_types()`; `grouping_measure.py` gains `--scope-amendment <name>` (default none) and records `scope_amendment` and `like_for_like_types` in the output meta. Nothing else in the frozen script changes; record scopes (G2 vocabulary, G5 mentions, `RECORD_SOURCES`) are not amended.

## What does not change

- Every Stage 2b reading: with the amendment off (the default and the only mode Stage 2b ever ran), the code paths select the same types. **Tested** (`work/checks/test_scope_amendment.py`): the prefix's per-day G1 like-for-like group counts are `[109, 74, 21]` on 2026-04-06, 04-07, 04-08 with the amendment off (the figures the rung-1 pre-registration printed from the frozen measure before the amendment existed) and, because the in-process prefix has no file or repo touches, also with it on. The Stage 2b outputs (`work/stage2/b-grouping.frozen.json`) are not recomputed.
- The frozen G1 definition (same-artefact write co-touch, w = 1, t = 1) and every budget, ordering and review rule.

## What the amendment makes visible (tested on the S5.3 lab corpus, `s5c_objective_benign_1.jsonl`)

Three accounts wrote `/shared/README.md` in ownCloud on 2026-04-06. Frozen scope: 0 G1 groups that day. Amended scope: 1 group, `{deepa.a1, priya.a84, wei.n2}`, the README's writers. All-services scope: 5 groups (chat and mail pairs besides the README trio), which the amendment does not admit.

## When it is used

Stage 3 only: rung 1's room statistic on the document class, the room and co-touch readings of the pilot and the first world, and the X layer's candidate-group generators on the class documents. Every Stage 3 grouping output names the amendment in its meta. Stage 2b readings are re-run, if ever, with the amendment off.

## Addendum 2026-10-23 (brief 07f B4): the two edit actions

Design v4 section 11.6; proposal 11.12 revised (`work/stage3/proposal-11.12-revised-2026-10-23.md`), 4(i), verbatim: "F2.6 (ownCloud edit actions counted as writes in the grouping measure) lands before planting, with tests; Stage 2b numbers are not recomputed."

- **What changed.** The fork added two ownCloud line-level edit actions on 2026-10-22, `append_to_file(path, text)` and `replace_in_file(path, find, replace)`. The touch table had no rule for them, so the grouping measure saw no write when an account edited a document that way. `work/checks/mole_corpus.py` (fork copy `scripts/track_b/mole_corpus.py`, byte-identical) now has a table `ACTION_AMENDMENTS`, filed under the same amendment name `stage3-shared-documents-2026-10-20`, that maps both actions to an ownCloud write touch of type `file` keyed by `path`, the same as `write_file` (marked fork-only, since the released corpora never had these actions). The table is read in one place only: the new `rule_for(service, action)`, which returns the part 1 rule (`RULES_BY_ACTION`) and, only when the amendment is on, falls back to the amendment's rule. Both `rules_for` (the fork-erratum path the grouping measure uses) and `touches()` now call it. There is no new switch. `generators.py` and `grouping_measure.py` are unchanged.
- **Amendment off (the default, and the only mode Stage 2b ever ran).** Neither action produces a touch, and every lookup returns the same rules as before. The Stage 2b numbers are not recomputed. `test_scope_amendment.py` passes unchanged, including the prefix_v1 G1 counts `[109, 74, 21]`.
- **Tested** in `work/checks/test_scope_amendment_f26.py`, on a synthetic corpus where two accounts edit `/shared/x.md` on one day. With the amendment off, the edit rows produce no touch, `write_file` still produces a file write, and G1 finds no group. With it on, both edit rows are file write touches on the path and G1 (same-artefact write co-touch) finds the pair. A failed edit row (exit_code 1) is never a touch. The test also checks that the two copies of `mole_corpus.py` are byte-identical.
