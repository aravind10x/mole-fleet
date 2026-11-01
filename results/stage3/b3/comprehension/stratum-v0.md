# Brief 25: B3's comprehension-quiet stratum, v0 (blue; counts, aggregates and hashes only)

**Comprehension-quiet stratum (A6.14.2): 28 of the 78 quiet candidates (0.359)**; by writer glm53 16, sonnet55 12. Rule: Kimi K3 D_part = 0 on every one of 2 samples and Sol's mean D_part at or under 0.50 (mean rule; stratum-plan.json, C1).

- Stratum ids sha256 `410e74613b9195a4f06b2c97dd0dfb598b2aeecc4ef473e9a86feb451cac01d7` (the sorted ids joined by newlines; the ids are in stratum-v0.json).
- Membership of the 78: not_quiet 50, quiet 28; share of the evaluable 0.359. Not quiet by writer: {'glm53': 21, 'sonnet55': 29}; not evaluable by writer: {}.
- Resolved-anchor subset: 19 of 62 candidates whose every replace anchor resolves in the day-0 text are in the stratum.
- Within the stratum, the whole is credited (D_whole > 0 under both readers) on 11 items and on no sample under either reader on 7 (quiet-but-illegible, A6.16.3's by-product).
- Beside: Kimi K3's rule alone 30; Sol's rule alone 50; both quiet at sample 0 alone 32 (the T1 proxy's form; T1 at one sample: 12 of 48). GLM-written candidates (37): stratum rule 16, Kimi K3 and Sonnet 5.5 (every sample) 15, all three 15, Sonnet 5.5 alone 23 (not evaluable under Sonnet 5.5: 0).
- C1's expectation (not a bar): at the chosen rule, P(labelled quiet | truly quiet) 0.519 [0.127, 0.742] and P(labelled quiet | not quiet) 0.005 [0.000, 0.032]; the T1 model expectation 0.222.

## Per reader and regime (mean over items of the per-item mean over samples)

| reader | regime | items | evaluable | D_part | D_whole | quiet under the reader's rule | D_part = 0, s0 / s1 |
|---|---|---|---|---|---|---|---|
| Kimi K3 | candidate | 78 | 78 | 0.455 | 0.631 | 0.385 | 0.564 / 0.436 |
| Kimi K3 | control | 22 | 22 | 0.000 | 0.000 | 1.000 | 1.000 / 1.000 |
| Kimi K3 | sham | 24 | 24 | 0.000 | 0.000 | 1.000 | 1.000 / 1.000 |
| GPT-6 Sol | candidate | 78 | 78 | 0.446 | 0.638 | 0.641 | 0.513 / 0.538 |
| GPT-6 Sol | control | 22 | 22 | 0.000 | 0.000 | 1.000 | 1.000 / 1.000 |
| GPT-6 Sol | sham | 24 | 24 | 0.000 | 0.000 | 1.000 | 1.000 / 1.000 |
| Claude Sonnet 5.5 | candidate | 37 | 37 | 0.264 | 0.426 | 0.622 | 0.757 / 0.676 |
| Claude Sonnet 5.5 | control | 10 | 10 | 0.000 | 0.000 | 1.000 | 1.000 / 1.000 |

## Not evaluable (a refused or missing part on some sample; never 0)

- Kimi K3: 0 items (none; reasons none).
- GPT-6 Sol: 0 items (none; reasons none).
- Claude Sonnet 5.5: 0 items (none; reasons none).

## Nulls: P(D_part > 0 | false target), controls and sham

| reader | set | items | per cell | any sample | reader's rule not quiet | D_whole > 0 per cell | paired s0: D_part > 0 / D_whole > 0 |
|---|---|---|---|---|---|---|---|
| Kimi K3 | control | 22 | 0.000 | 0.000 | 0.000 | 0.000 | n/a |
| Kimi K3 | sham | 24 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 / 0.000 (n 24) |
| Kimi K3 | pooled | 46 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 / 0.000 (n 24) |
| GPT-6 Sol | control | 22 | 0.000 | 0.000 | 0.000 | 0.000 | n/a |
| GPT-6 Sol | sham | 24 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 / 0.000 (n 24) |
| GPT-6 Sol | pooled | 46 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 / 0.000 (n 24) |
| Claude Sonnet 5.5 | control | 10 | 0.000 | 0.000 | 0.000 | 0.000 | n/a |
| Claude Sonnet 5.5 | pooled | 10 | 0.000 | 0.000 | 0.000 | 0.000 | n/a / n/a (n 0) |

The stratum rule applied to the 46 nulls against their false targets: {'quiet': 46}.

## Positive control (own edit, 20 candidates, sample 0)

- Kimi K3: D_whole_own 0.925 (n 20), D_part_own 1.000 (n 20), mean over parts 0.958.
- GPT-6 Sol: D_whole_own 0.850 (n 20), D_part_own 1.000 (n 20), mean over parts 0.967.
- Claude Sonnet 5.5: D_whole_own 1.000 (n 10), D_part_own 1.000 (n 10), mean over parts 0.900.

## Reliability

- Kimi K3: scorer pass kappa 0.925 (n 1168, agreement 0.974); candidates' quiet status flips between samples 18 of 78 (0.231; T1 retest: 2 of 10), D_part equal on both samples 0.692.
- GPT-6 Sol: scorer pass kappa 0.922 (n 1168, agreement 0.973); candidates' quiet status flips between samples 16 of 78 (0.205; T1 retest: 5 of 10), D_part equal on both samples 0.756.
- Claude Sonnet 5.5: scorer pass kappa 0.914 (n 416, agreement 0.971); candidates' quiet status flips between samples 7 of 37 (0.189; T1 retest: 1 of 10), D_part equal on both samples 0.757.

## Reader and scorer outcomes

Reader refusals (provider, DECLINED token or prose) and missing readings, summed over samples, per reader, regime and condition:

| reader | regime | whole | part0 | part1 | part2 |
|---|---|---|---|---|---|
| Kimi K3 | candidate | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) |
| Kimi K3 | control | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) |
| Kimi K3 | sham | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) |
| GPT-6 Sol | candidate | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) |
| GPT-6 Sol | control | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) |
| GPT-6 Sol | sham | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) |
| Claude Sonnet 5.5 | candidate | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) |
| Claude Sonnet 5.5 | control | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) | 0 (0 missing) |

Scorer outcomes per target and pass are in stratum-v0.json (`outcomes`). Refused part readings: Kimi K3 0; GPT-6 Sol 0; Claude Sonnet 5.5 0.

## For brief 20 Part 3

stratum-v0.json `items` carries, per candidate by opaque id: membership, composition (two-pass mean, both passes), the rater top line and top-two gap, the replace share, and per reader the per-sample D_whole and D_part and the continuous D_part (mean over samples) for the interaction sensitivity.

## Hashes and spend

- items-v0.json `064225b4fb59b511e45a74c149c3d34e518e5c3910fb0b57b3e24f4721b3e5e7`; rubrics `34791c330c3d3ed5c06695960d511190a29394428a9aa2ffa1e180b3d5c79496`; stratum-plan.json `65ea42a4b116dbcbcfd13615ea82453d12d415e872b63d467a6cce1e4fcb2828`; config `a79d49b8347616d1626adf1cff7be521059f612b545415084133982bace12961`; run script at items `57d80170b2aefb1af89c9efc115b256fcf1e9e867e12a4960c20edf98b55e810`; report script `5b55e3cb35392575c6cd1b8ddcb7d50cbd4dca62872a774b00677677debf4a7d`.
- Caches (main checkout only): sonnet55 `2ff6bb9ced8641af429a2473ce54fdbc56d572b47c344d047f20bf8922f11647`; kimi `c53dcae0a66bd8b699b6f6fed293e3a6d6fea1c1d2b31c28e463d8c8e386f360`; sol `8f8f157ab7fd0660779b5326b1520d42fe31e03feb697137d3f585b830cf0790`; scorer `7462ac06b7f141ddb87b531a209e5bb1776d36e3ea24af3bfe57184866298a6a`.
- Spend: sonnet55 $1.06, kimi $7.20, sol $2.58, scorer $8.61, routes $0.00, total $19.45 (dry run $32.28).

## Disclosures

- Readers: Kimi K3 (OpenRouter key 2) and GPT-6 Sol (Bedrock Converse) on every item; Claude Sonnet 5.5 (Bedrock global profile) on the GLM-written items only, beside, so that no reader reads its own family's items (the Sonnet-written candidates are not read by Sonnet 5.5). Sol is allowed here because the stratum feeds the per-agent readings under Opus 4.8; A6.3(e)'s Sol O_diff is never reported on this stratum.
- Scorer: Claude Sonnet 5 on Bedrock, two passes, brief 23's consequence-only instruction unchanged (prompt hashes checked against brief 23's items-v0.json before the items were written). The scorer never sees the item.
- Sampling: temperature not sent on any route; OpenRouter reasoning at the provider default; samples and passes sample at these settings, with the sample and pass indices in every cache label.
- Rendering as brief 23: each edit against its document's day-0 text with the note that the copy may predate other routine edits; replace anchors that do not resolve in the day-0 text are counted per regime, and the resolved-anchor subset is reported beside.
- The sham items are brief 23's control regime (v2's 24 same-shape sham triples), re-read here; their false targets are drawn from B3's quiet candidates on the same document, so their null figure is the false-credit rate against B3's rubrics.
- The positive control reads the own-edit target ('the document now says ...') on 20 candidates at sample 0; it checks the scorer chain's sensitivity on B3's edits and is not a null.
- Spend accounting is response-based (an abandoned OpenRouter request may be billed without a response on file).

## Deviations

- C1's model: the plan fits a cross-reader two-class latent class model (the main fit, which governs) and reports a reader-relative sensitivity (symmetric error from each reader's own flips) added after the first computation of the plan and before its commit and before any call; both give the same choice (stratum-plan.json).
- No candidate in C1 reaches 0.8 and 0.1; the run uses the best attainable pair, as the brief expects at 10 retest items per reader.
- Controls (B3's same-writer controls) carry no pairing in their records, so they have no paired-rubric sensitivity; the sham's paired rubric is brief 23's (T1v2-Snn to T1v2-Cnn), read at sample 0.
- The own-edit and paired targets are scored at sample 0 only; the L target (rubric or false target) on every sample.
- Seeds not named in the brief: C1's EM starts and bootstrap random.Random(20261208); call order brief 23's random.Random(20261205).
- The run mode exited 1 after every call had finished: its final print refused the approval rule's free text in the summary (the print guard working); run-summary.json was written before the print, with every phase complete and none aborted. The run script was left unchanged so that its hash stays the one the items manifest pinned.
