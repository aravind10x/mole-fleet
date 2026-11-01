# Cold read of brief 28 (B3's S1 plan, 511780f9) and brief 29 (brief 24's E0, 301aff99) (review session, Opus 5.5, 2026-11-01)

Section 1 was written before the independent Fable read returned. Section 3 reconciles the two.

## 1. My read, written first

### Brief 28: ready once the fixes below are in
**Required**
1. **Name the readings that brief 22's gate G1 uses.** F1 item 3 does not name A6.3(e)'s `O_diff` readings, though G1 reads Opus 4.8's `O_diff` recall on the quiet set. Name:
   - G1's population: the full quiet set, net 73, with the stratum beside (A6.18);
   - that Sol's `O_diff` is never reported on the stratum (A6.14.1).
2. **Fix the seed by rule and forbid re-drawing.** Name the seed value by a rule (the next free integer in the project's seed register), not by choice. Placement draws are computed only from the committed `plan.md` (or in S3), never during drafting, and never re-drawn.
3. **Make the lone-line placement rule unambiguous.** F1 item 2 says "two placements per lone line ... on its own author", while brief 26 judged lone lines by "two valid draws by different authors". State both parts:
   - each lone line is applied alone in its own session (A6.5 (iii));
   - its two placements are two different (day, author) pairs from brief 26's lone-line `valid_draws`, under the same pair rule as items.
4. **State the order of the two fallbacks.** A6.13.4's instrument fallback (carrier to the second instrument when the carrier is at floor or unfit) and A6.17.9's population step-down (17, then 26, then the third branch) can both trigger. The plan must say which applies first: try the second instrument on the 17 before stepping down, or the reverse. It must also say whether a *floor* triggers the step-down at all. The floor is judge-against-sham separation, which is largely independent of population, so stepping down on a floor may change nothing.
5. **Recompute S2's estimate on the net items, and name the add-on decision.** About $73 is Part 2's $98.17 less the live singleton units for 78 items. Recompute units and dollars on the net 73 items (and their lone lines). Carry the controls' singleton add-on (A6.8, $15.99) as an explicit S2 decision line for Aravind (A6.13.8 leaves it to S2).

**Optional**
- In the draft's checklist, list each A6.18 item, (a) to (q), with the plan line that implements it.

### Brief 29: ready once the fixes below are in
**Required**
1. **Certification omits the quiet gate.** E0-3's rule is the stratum rule plus D_whole > 0, but brief 24 E2 still requires every statement's rater score to be at or under 60, as the mean of two certification sessions. Round 2's items must be quiet by the same rater rule as round 1's quiet set, or rounds 1 and 2 test different populations. Certification is therefore: the rater quiet gate, and the stratum rule, and D_whole > 0. State that E2's old legible clause ("L above the null's 95th percentile …") is superseded by the component gate.
2. **Define both arms exactly.** "D_whole > 0 under both" is ambiguous between any sample and every sample. Use A6.17.5's definitions for both arms:
   - certified: the whole credited under both readers on at least one sample;
   - illegible: the whole credited on no sample under either reader;
   - mixed items join neither arm.

   This is argued; E0-5 computes the yields under it.
3. **Rendering and insertion.** Brief 25's day-0 rendering artefact came from anchors written against later document states. The fixes:
   - say which document state the writers write against and which rendering certification uses (the same one);
   - require a brief-26-style insertion dry run on certified items before round 2, so that a certified item's quietness cannot again be a missing-line artefact.
4. **Pinning needs client support.** Pinning Kimi K3 to one provider and precision needs `judge_openrouter.py` to send OpenRouter's provider preferences (`order`, `allow_fallbacks: false`, a quantization filter). Brief 23's client changes did not add these. Add the option with a test and a probe costing cents that records the served provider and precision; otherwise name it as a prerequisite before any certification reading.
5. **Session order, for blindness.** E0-1's taxonomy must be written by a session "barred from every judge and rater result". E0-5 reads brief 25's `stratum-v0.json`, which carries the rater's composition and top-line scores. So E0-1 is written and committed before E0-5 opens any result file, or by a separate session.
6. **Disclosure.** The pinned reader (Wafer, MXFP4) credits parts about twice as often as brief 25's mixed Kimi K3. Round 2's certified items therefore pass a stricter comprehension test than round 1's stratum did. E0-5's proxy should use Part 3's Wafer-served reads where it can.

**Optional**
- E0-6: state that the cross-document validation for brief 22's G3 is deferred until items exist, so that E0 being "done" is not read as G3 being validated.

## 2. Fable's independent read (Fable 5.1, high; briefed without section 1)

Summary, not verbatim. Fable verified hashes, paths, counts, the dollar table, the JSON keys and the null table.

**Brief 28: ready with fixes.**
- **Commit gate.** List the four conditions once, name who commits, and replace the nonexistent "brief 27's valid-draw file" with brief 26's JSON (edd289ce) plus brief 27's module and record hashes.
- **Seed.** Fix it by rule (next in the series, 20261181), with a stream tag per arm. Commit the draft by hash at its first write. S1 computes no draw.
- **Fit failure.** Define it mechanically, and say whether the floor is checked per population.
- **Missing outcome-sentence families.** Floor; (b)'s ceiling; the two-step conflict; the disattenuated reading; the disagreement between subset and stratum; the D_part interaction; Q1 against Q3.
- **Missing readings.** A6.3(e) with no Sol on the stratum; A6.3(d)'s k = 2 arm; S0 and the direct test, run or withdrawn; the full set's document factor against the stratum's pooled bootstrap.
- **Naming.** Call the 22 "the same-shape sham, the floor"; make the lone-line author unambiguous.
- **Estimate.** Re-base it on net units (≈ $68); the controls' add-on and k = 2 are Aravind's decisions at S2.
- **Barrier and framing.** Add the anchor sheet, red/, persona and key files, and caches to the Do-not list. F0 should read Section 0, Part S and A6 only, not Part W, and use brief 26 v2's vocabulary.

**Brief 29: not ready.**
- **The barrier contradicts itself.** "No B3 result file" bars stratum-v0.json and v3c.json, which E0-5 and the pin need. Define the barred set as S3's outputs.
- **Certification is under-specified.** Name the second readers and their rules, including those for Muse-Wonder-written items. Pin the D_whole rule (11 certified and 7 illegible of 78 in brief 25). State that Sol is never an O_diff judge on these items. Name the development rater and readers.
- **Outputs.** Two outputs are missing: the gate-reachability file with its script, and the cross-document file. On the nulls, brief 25's 46 pass the gate 0 of 46.
- **G3 has no pass criterion.** Define a cross-document honest-pair null under the pair protocol, run and priced in brief 30; cite where constraints 1 to 6 live.
- **Writer packet.** List the exclusions; add the neutral-framing rule with the fallback order; fold in A6.19.1 (b) and (c); restore the 20-item human anchor.

## 3. Reconciliation (review session)

**Hashes.** The current briefs are 28 511780f9, 29 b08fc6dc, 15 cdc2e04e and 24 68aeefc4. STATUS's last line now cites the last two, so Fable's stale-hash flag was a transient caught mid-edit.

**Verdicts.** Brief 28 is ready with fixes. Brief 29 is not ready as written: the barrier contradiction, the missing quiet gate and G3's missing pass criterion each block it.

**Agreed.** Fixes on the seed, the lone-line wording, fit failure, the estimate re-base and A6.3(e) were raised by both reads.

**Adopted from Fable.**
- Brief 28: the commit-gate list and the valid-draw citation; the missing sentence families and readings; naming; barrier and framing (F0 reads no Part W).
- Brief 29: the barrier definition; the certification readers and rules; the missing outputs; G3's pass criterion; the writer-packet exclusions and framing; the human anchor.

**Kept from section 1.**
- Brief 28: the order of A6.13.4's instrument fallback against the population step-down.
- Brief 29:
  - the rater quiet gate, which is missing from E0-3's certification and is not in Fable's read;
  - the writer state and the certification rendering made the same;
  - client support for pinning, with a test and a probe;
  - taxonomy-first ordering for blindness;
  - the stronger-reader disclosure.
