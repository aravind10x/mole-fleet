# Erratum, 2026-11-02: the world's generator is Kimi K2.6, not Kimi K3 (coordinator, Fable 5.1, $0)

**What is wrong.** Two frozen 07p texts name the generator of the honest world and of red's live text as "Kimi K3":
- `work/stage3/q1q2-synthetic/extra-judge-results.md` (3490eefc), line 101, the disclosure line: "the honest world and red's live text are Kimi K3's, a third family";
- `work/stage3/q1q2-synthetic/extra-judge-plan.md` (947aa5b8), line 54, the same sentence in the plan.

**What the launch records say.** Every launch line and every launch wrapper in `work/stage3/prefix/` sets the generator to `moonshotai/kimi-k2.6` via OpenRouter; no launch record names Kimi K3. Checked by grep on 2026-11-02 (one `OPENROUTER_MODEL=` line per launch-line file; one model id per wrapper):

| launch line | sha256 (8) | model |
|---|---|---|
| launch-line.txt | 8d7f4b4b | moonshotai/kimi-k2.6 |
| launch-line-v1b.txt | 44f1bd4a | moonshotai/kimi-k2.6 |
| launch-line-v2.txt | 44c6c17b | moonshotai/kimi-k2.6 |
| launch-line-v2b.txt | 5f2e25ab | moonshotai/kimi-k2.6 |
| launch-line-v2c.txt | 44bd205b | moonshotai/kimi-k2.6 |
| launch-line-v3.txt | 9cc90fc5 | moonshotai/kimi-k2.6 |
| launch-line-v3b.txt | 672aecb8 | moonshotai/kimi-k2.6 |
| launch-line-v3c.txt | 99945129 | moonshotai/kimi-k2.6 |
| launch-line-v3r.txt | aa1c9c04 | moonshotai/kimi-k2.6 |
| launch-line-v3rb.txt | dc662d85 | moonshotai/kimi-k2.6 |
| launch-line-v3rc.txt | 7343be1f | moonshotai/kimi-k2.6 |

The thirteen wrappers (`run/wrap.sh`, `wrap_v1b.sh`, `wrap_v2.sh`, `wrap_v2b.sh`, `wrap_v2c.sh`; `run-v3/wrap_reh.sh`, `wrap_rehr.sh`, `wrap_v3.sh`, `wrap_v3b.sh`, `wrap_v3c.sh`, `wrap_v3r.sh`, `wrap_v3rb.sh`, `wrap_v3rc.sh`) each carry `moonshotai/kimi-k2.6` once and no other Moonshot id. CONTEXT.md's generator row (Kimi K2.6, launch lines) is right. The world the T1 plantings and B3 plant on is `prefix_rw_v2c` (CONTEXT.md); B4's world is `v3rc`; both lineages use the same generator.

**How the error arose (read of the records, not established by a log).** Kimi K3 is the fourth judge of 07n and 07p (`moonshotai/kimi-k3`, 3,055 mentions in the q1q2-synthetic records, all as a judge). The disclosure sentence took the judge family's name for the generator's. The two models share a family, so 07p's point stands as written: the honest world and red's live text are neither Claude-written nor from the judge's own vendor family when the judge is OpenAI, Meta or Anthropic; they are from the Moonshot family, as is the Kimi K3 judge. Where the paper compares the Kimi K3 judge with the generator, it says that both are Moonshot models (K3 the judge, K2.6 the generator), not that the judge read its own text.

**What changes.** Nothing in the frozen files; they keep their hashes. The paper reads "Kimi K2.6" for the generator and cites this erratum and the launch line of the world in question (`launch-line-v2c.txt` 44bd205b for the T1 and B3 world; `launch-line-v3rc.txt` 7343be1f for B4's) rather than 07p's disclosure sentence. The frozen-tables manifest gains this erratum and the eleven launch lines, tagged *methods*, by the writing session's next W0 amendment; the launch lines are mirrored to the fork under `results/stage3/prefix/` in the same commit, since only `b4r/prefix/launch-line-v3.txt` and the pilot's launch lines were mirrored before.

**Raised by** the review session's cold read of outline v1 (`work/paper/review/cold-read-outline-v1-2026-11-02.md` 25230bc5, required fix 3), after the writing session named the discrepancy in its outline (STATUS 2026-11-02, outline v1 committed). Decided by the coordinator on 2026-11-02; recorded in STATUS the same day.
