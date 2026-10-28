1. **Blocker for B4 validity — the repair leaves cheap rules based on item and document pair.** [plan.md:34](/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/plan.md:34), [stage3_b4r_design.py:39](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b4r_design.py:39).

   The cheapest rule is: **flag a repeated cross-document entity change unless both changed lines concern one of the eight named maintenance items on its declared document pair.** It needs no secret. Intended v7 maintenance contributes zero false positives to this rule; the remaining cost comes from background edits and failures to follow tasks. For the one-agent version, the unrepaired overall A of 0.020 is a reasonable starting estimate for that residual, **not a verified v3 bound**. B’s event share does not establish the two-agent version’s account-level cost.

   There is a second concentration problem. Using the registered model and actual allocation, each item’s individual cross-document account-window rate is only:

   | Item | Expected cross-document rate |
   |---|---:|
   | Four eight-update rows | 0.0382 each |
   | Runner image tag | 0.0114 |
   | On-call contact | 0.0263 |
   | Sign-off contact | 0.0263 |
   | Repository access contact | 0.0276 |

   These are model contributions, excluding background recurrence. They show why lifting a **class pooled across items** does not establish that an item-specific rule exceeds budget. The eight items also cover only **five document pairs**.

   **Fix:** pre-register and measure the residual rules now: outside-item/pair, unequal resulting values, and maintenance-shaped workflow exceptions. B4 must either stay within honest support on these dimensions or explicitly compete against the cheap rules. Measure equality after a declared session boundary or grace period: an immediate inequality rule would flag the first half of ordinary sequential maintenance. Do not assert that these rules are free until their v3 costs are measured.

2. **Important — packing classes into touched lines can clear the class gate without changing those classes’ values.** [plan.md:47](/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/plan.md:47), [plan.md:28](/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/plan.md:28).

   Changing `Eval-server port: 8088` to another port registers a host change because unchanged `eval-server` remains in the added line. Similar problems affect registry/port and config-label/path combinations. This faithfully uses B0’s primary definition, but the plan explicitly chooses line packing to lift every class while keeping overall A below 0.25. Consequently, the class gate can certify background support for host changes that never happened.

   The rows are mostly plausible maintenance content. The concern is their **measurement role**, rather than whether two classes may naturally share a line.

   **Fix:** retain frozen primary A, but put net-introduction A immediately beside every overall and class admission reading. Pre-write what happens when primary passes and net does not. Restrict later conclusions about changed host/path/etc. values to demonstrated support; a buried sensitivity table is insufficient.

3. **Important — statistic B still cannot establish the cross-account rule’s matched honest cost.** [plan.md:94](/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/plan.md:94), [plan.md:117](/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/plan.md:117).

   B measures flagged **entity events**, whereas the comparison budget concerns accounts or account-windows. Many recurring events concentrated on a few accounts can produce high B while an account-level cross-account rule remains below 5%. Acknowledging B0’s weakness does not resolve it for a new experiment expressly designed around that competitor.

   **Fix:** preserve B unchanged, and add the account-window indicator “this account changed an entity also changed in another document by another account.” Report its honest cost, account bootstrap, and pre-written reading at the relevant budget. Until then, describe B as recurrence frequency, not the rule’s comparable honest cost.

4. **Important — “completed” does not verify completion of the maintenance task.** [stage3_b4r.py:184](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b4r.py:184), [plan.md:84](/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/plan.md:84).

   `day_reading` counts any successful content write on each named path anywhere in the session. Unrelated agenda edits, no-op writes, or different values in the two documents count as completion. The test explicitly accepts contents `"x"` and `"y"` as a completed pair.

   This implements the plan’s proxy literally, but a broken maintenance bank could pass the instrument stop and later fail A for reasons the completion report conceals.

   **Fix:** retain path coverage as a diagnostic, and separately verify nonempty changes to the named item in both documents with the same resulting value. Use verified completion for the maintenance stop and report unrelated/path-only writes separately.

5. **Important — severely insufficient exposure can silently pass day 1.** [plan.md:84](/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/plan.md:84), [stage3_b4r.py:217](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b4r.py:217).

   With **one to four updates fed and none completed**, neither stop fires. The expected exposure is 9.4 updates. A partially disabled bank can therefore proceed to days 2–3. The minimum-five exception is also an additional substantive deviation from the brief’s under-half-rate stop, absent from the nine declared deviations.

   **Fix:** declare the exception and an “insufficient exposure” outcome explicitly. Pre-register a minimum feeding criterion and stop continuation when there is too little exposure to assess completion. The 0.333 rate threshold is otherwise a reasonable instrument threshold around the stipulated prior; it is not a reliable test at tiny denominators.

6. **Important — v7 seed provenance disappears on branches, leaving a real route back to v6 analysis.** [run.py:558](/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/mole/generator/run.py:558), [run.py:1215](/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/mole/generator/run.py:1215), [launch_line.py:591](/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/scripts/launch_line.py:591).

   The fresh run records `class_documents_version`; branch preparation does not inherit it. A branch cannot explicitly select v7 either: the validation requires `class_documents=True`, which branches reject. The branch manifest check verifies document presence but not inherited seed version.

   Thus `v3b`/`v3c` can contain v7-derived documents while lacking the version field that elsewhere means “legacy v6.” Moreover, frozen [stage3_views.py:195](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_views.py:195) still defaults to v6. The required `b4r z5 --version` protects that particular invocation, but does not validate the choice against corpus provenance.

   **Fix:** inherit original seed version and hashes through branch lineage; validate them on branches; have new analysis wrappers resolve or verify their explicit base against that provenance. Keep the frozen reader unchanged.

7. **Important — the declared key-2-primary fallback path is unsupported.** [plan.md:80](/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/plan.md:80), [launch_line.py:254](/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/scripts/launch_line.py:254).

   The plan declares key 2 primary and key 1 fallback when key 1 lacks the day’s headroom. `_key_export` expressly rejects that assignment; only key 1 primary/key 2 fallback is supported. The balances written in the plan would select the supported direction currently, but the other pre-registered branch is unlaunchable.

   **Fix:** implement and offline-test both directions, or declare key 2 alone with its exhaustion stop. Do not discover this mismatch after the launch assignment is frozen.

8. **Important — the budget fallback lacks an exhaustion outcome.** [plan.md:128](/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/plan.md:128), [plan.md:137](/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/plan.md:137).

   Dropping unrun Opus nulls cannot always restore feasibility: some Opus work may already be spent, or the remaining Sonnet work alone may exceed the balance under $200. The plan simultaneously says no Sonnet null is dropped and supplies no explicit outcome after all removable Opus work is exhausted.

   **Fix:** specify: “If mandatory remaining work still exceeds the ceiling after all permitted drops, stop and report incomplete nulls; B4 lacks those views.” Apply a remaining-budget check before each batch. The stated $150–$192 arithmetic is consistent, but the estimate and drop list are not themselves a hard spending guard.

9. **Important — the main-checkout deviation records drift without preventing an unknowable execution.** [plan.md:80](/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/plan.md:80).

   A boundary `git diff --stat` cannot identify which version a lazy import loaded during the day. It also misses transient edits subsequently reverted and excludes bank/bootstrap inputs. Calling every observed change a disclosed deviation leaves no criterion for whether the resulting corpus still represents the registered world.

   **Fix:** keep the required main checkout stable during each launch, record approved code and input hashes, and prescribe a stop/invalidation outcome for relevant drift. Check that subsequent launches use the approved versions before starting them. Retrospective disclosure alone is too weak for this deviation.

10. **Important — the propagation statistic’s interpretation overstates what its correct implementation measures.** [plan.md:15](/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/plan.md:15), [stage3_b4r.py:293](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b4r.py:293).

    The code asks whether an **added/new entity** was already cited elsewhere immediately before the write. For the first port update from 8088 to 8090, the answer is false for 8090, although the other document’s old 8088 plainly creates a maintenance obligation. Meanwhile, unchanged `eval-server` on that line counts as cited elsewhere.

    The implementation matches R0.5, but this does not measure all changes a maintained lab would propagate. Nor can an event-weighted share bound account-window A without additional assumptions.

    **Fix:** retain the registered statistic with a precise label, remove the bound claim, and add a descriptive old-value/shared-item measure of propagation opportunities.

11. **Minor — propagation can manufacture a “two-day” window across a missing day.** [stage3_b4r.py:302](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b4r.py:302).

    `days` comes from extracted entity events. If April 7 has no such events, April 6 and April 8 become adjacent and are reported as a two-day window. Legitimate zero-event windows disappear.

    **Fix:** derive days from `sv.corpus_days(rows)`, matching B0, and preserve zero-event windows with an undefined share where appropriate.

12. **Important — greedy matching narrows the repaired support further.** [plan.md:121](/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/plan.md:121).

    The matching is deterministic and correctly implemented, but it is a substantive restriction of the brief’s co-read grouping idea. The five maintenance pairs form a graph whose maximum matching contains only **two pairs**. Consequently, if the workspace partition has three pairs, at least one pair has no added maintenance task connecting it.

    Even the favorable matching of README–fine-tune and release-gate–red-team leaves the added grouped contact support concentrated on sign-off contact, whose modeled rate is only 0.0263. Overall class A does not establish support within the groups B4 actually uses.

    **Fix:** freeze eligibility and honest-cost reporting by the intersection of **group, item/pair, and class**, before later content is written. Keep the all-six baseline. Describe view 4 as a pair-partition monitor, not a monitor of every qualifying co-read relationship.

13. **Minor — several non-A outcomes remain without a clear action sentence.** [plan.md:101](/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/plan.md:101), [plan.md:152](/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/plan.md:152).

    The numeric overall-A branches are exhaustive, but the wider process is not: exactly one pinned update succeeds; the honest leak statistic falls **below** its band; or overall A passes while no anchor class remains eligible. The rehearsal says pass requires both updates, but specifies the remediation only when both fail.

    **Fix:** write explicit stop/report/remediation sentences for these cases. Gate 6’s honest-null-only deviation is appropriate on an honest world, provided it is never presented as passing the unavailable scenario-versus-honest gate.

14. **Minor — the draw-model density credits checks with impossible two-document writes.** [stage3_rung1_class.py:153](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_rung1_class.py:153), [stage3_rung1_class.py:229](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_rung1_class.py:229).

    Both update and check variants become `"write"` on both documents. Yet the plan correctly says checks edit at most one stale document, often neither. Adding the check prefix satisfies the required classifier behavior, but does not justify those two write credits.

    **Fix:** preserve task kind in the simulation and distinguish potential write opportunities from executed writes. Keep the empirical G0a gate authoritative. The prefix deviation is acceptable syntactically; its classifier result should not serve as behavioral evidence.

**Checked and found correct**

- The 49 updates, 19 checks, pool sizes, and published count arithmetic agree. `λ = S f c u/n` is a sensible first-moment model assuming representative feeding. Poisson occurrence and the independence union with 0.02 are approximations; `y²` is the brief’s stipulated prior. The sensitivity grid is correctly calculated, but does not cover task-dependent feeding, value agreement, or correlated completion.
- Calibrating on v2c is better matched to the copied world than using v1 day 1 alone. The cap and rotating allocation are deterministic. The 68 variants exceed an orientation, not a numerical requirement.
- Versioned seeds are the right choice. v6 remains unchanged/default; v7 preserves every v6 line and its order. Fresh-manifest checks correctly interpret missing version as legacy v6 and verify hashes.
- `z5_on` replaces the sole seed reader used by frozen Z5 and restores it through `finally`.
- Propagation uses strict pre-write states and B0’s primary extractor.
- Workspace replay uses the other documents’ states just after the triggering write. Singleton equivalence to O_diff passed on v2c. O_ws adds no harm wording beyond the shared text.
- The ungrouped baseline correctly has O_diff’s candidate boundary/write count; scored counts can differ because skip decisions differ.
- No files were modified and no network, judge, or Docker calls were run. With pytest capture disabled, **21 B4-R tests and 12 seed/launcher tests passed**; **33 tests were blocked by temporary-directory permissions**, so the full suites were not verified.