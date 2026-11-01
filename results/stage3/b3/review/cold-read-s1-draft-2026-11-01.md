# Cold read of B3's S1 draft (`plan-draft.md` d6bf4440; `s1-populations-v0.json` f17e7a72) (review session, Opus 5.5, 2026-11-01)

Section 1 was written before the independent Fable read returned. Section 3 reconciles the two.

## 1. My read, written first

**Verdict: ready to commit once the gate holds and the decisions below are recorded.** The draft is careful, and almost every figure traces to a source and hash. No section lets S1 depend on S3 data. S1 computes no draw, and every fallback step is mechanical.

**Verified by script**
- **D2 (the per-item key).** `items[].draws.valid_by_day` holds per-day counts; the (day, author) pairs are in `items[].draws.valid_draws`.
  - Briefs 27 v3 (E2) and 28 v2.1 (F0 (c)) name the counts key. I relayed that name from Fable's earlier read without checking it, so the error is mine.
  - I sent the correction to the coordinator for brief 27's running session.
  - The draft's §2.2 cites all three keys correctly, and K3 checks the key at commit.
- **D1's feasibility** (`s1-populations-v0.json` `lone_lines`).
  - Under the draft's rule (two lone placements by different authors, neither of them an author of the item's pair, days free), all 219 net lines keep two valid draws for every possible item pair.
  - Under the same pair rule as items (different days as well), only 177 do; 462 of 18,018 item-pair cases fall short.
  - So D1 is the feasible reading of A6.5 (iii) together with A6.17.11. My earlier suggestion, "the same pair rule as items", was wrong once the author exclusion applies.

**D1 to D17**
- **Fine as drafted:** D2, D3, D4, D6, D8, D9, D10, D11, D12, D13, D14, D15, D16 and D17.
  - D3's instrument fallback at step 4 is moot in practice, because fit failure is essentially impossible on a 5-parameter model. But the floor rule (a floor failure hands the lead to S at step 1) is the one that matters, and it is right.
- **Needs the coordinator's dated note, because each changes pre-registered wording or values:**
  - **D1.** The lone-line rule above is a reading that brief 28 did not state.
  - **D5.** A6.14.4's fixed sentence adapted to the stratum branch. A6.14.4's wording names the full set, but the carrier is the subset.
  - **D7.** Q1-against-Q3 uses each population's own net quartiles instead of A6.4's fixed 47.5 and 68.0. The fixed values are the gross 78's, and on the subset (17; composition SD 19.5) they may not sit inside the population's range. The change is sensible, but it replaces a pre-registered value.

**Required before commit (beyond the gate)**
1. **The D2 correction lands in briefs 27 and 28 by dated note.** K3 must then confirm that brief 27's restricted mode reads `items[].draws.valid_draws`. The draft already requires this.
2. **The coordinator records D1, D5 and D7.**
3. **The record of this cold read** (this file and its hash) fills gate condition (d).

**Optional**
- §9 states the stop as about $136. Make it "twice S2's dry-run estimate", since S2 re-bases the figure.

## 2. Fable's independent read (Fable 5.1, high; briefed without section 1)

Summary, not verbatim. **Verdict: ready with fixes.** Fable reproduced `s1-populations-v0.json` byte for byte and verified every count, hash and simulation figure the draft cites.

**Required:**
1. **Stale source hashes.** Brief 28 is now 6e55d1d9 and brief 27 is e390ade7, both with the key corrected. D2 becomes a one-line note.
2. **Two rules contradict each other for the full set.** O3 (drop the document factor when the fit fails to converge) sits against §4.3 (i) (non-convergence is a fit failure). Order them: fit with the factor; if the point fit fails or more than 10% of replicates fail, refit without it under the document-stratified bootstrap; only then is the reading unfit.
3. **D3 needs the coordinator's decision.** The second instrument S is readable on the subset (0.66 / 0.04 / 0.04 / 0.69) and the stratum (0.81 / 0.07 / 0.04 / 0.77), so re-entering S at step 1 uses a readable instrument rather than discarding it. This is argued, not tested: no joint operating characteristics exist for a cascade led by S.

**D1 to D17:**
- D3, D5 and D7 need the coordinator.
- D7: the subset's own quartiles span 47.5 to 56.5, only 9 points, which is close to uninformative. Fable prefers the full net set's 47.5 and 66.5 for every population (argued).
- The rest are fine.

**Optional:**
- The order of fixes: draft v2, then the coordinator's sign-off, then commit.
- Precedence among floor, ceiling and fit.
- Operating characteristics stated "at the pre-registered n".
- S2 confirms the $72.86 reading.
- The author-exclusion file is regenerated if an item draw changes.

## 3. Reconciliation (review session)

**Verdict: ready with fixes.** We agree on the main points: the populations reproduce, every number traces, and nothing lets S1 depend on S3 data.

**Adopted from Fable:**
- the hash re-cites, with D2 settled;
- the ordering of O3 against fit failure (required). I missed this;
- D7's alternative (the full net set's quartiles for every population), offered to the coordinator;
- every optional item.

**D3 is moot in practice but should still be decided.** Fit failure is essentially impossible on the 5-parameter model, so the choice almost never applies. Recommendation (argued): whenever S takes the lead, it starts at step 1. That matches the floor rule, which already hands S the lead at step 1, and it uses a readable instrument. Record that no joint operating characteristics exist for a cascade led by S.

**Correction to section 1, on D1.** D1 needs no separate note. Brief 28 v2.1 asks for "two different (day, author) pairs from brief 26's lone-line valid draws", and D1 (different authors, excluding the item's authors, days free) satisfies that. It is feasible on all 219 lines.

**For the coordinator to decide:**
- **D3:** S starts at step 1 whenever it leads.
- **D5:** accept A6.14.4's sentence as adapted to the stratum branch, by dated note.
- **D7:** the full net set's quartiles for every population, or each population's own.
