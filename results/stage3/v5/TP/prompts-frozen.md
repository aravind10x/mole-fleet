# Check TP: frozen prompts (blue executor, Fable 5.2; frozen 2026-11-19 14:56 IST, before any call)

| arm | file | sha256 |
|---|---|---|
| B (fresh baseline) | the sealed composed-view system prompt, `stage3_views.system_prompt("O_diff", 0)`, bytes unchanged, `shared-harm/v1+views/v1:O_diff` (1,495 chars) | 0dad3af9674834164cea8ca99f5ba88548eed771a6114741f2c7780b5688c909 |
| T (targeted paragraph) | `TP/prompt-T.txt` (2,533 chars): the sealed framing and harm text, the one paragraph, then the sealed answer format (scale and JSON form unchanged) | c08593403195334deaf0de744cc52e68376d28a172edb673a8d1c0aa521ede0c |
| T, the paragraph alone | `TP/paragraph-T.txt` (1,036 chars, one paragraph, no line break) | 1008c497bdd3b9c0e8af3025212d853a36ca35cef8007880f1afb42e821a6f39 |

**How arm T's prompt is built.** `stage3_tp.build_T`: the sealed framing, a blank line, the sealed harm text, a blank line, the paragraph, a blank line, the sealed answer format. Removing the paragraph and its blank line gives the sealed prompt's bytes (0dad3af9); a test checks this, and `stage3_tp.load_prompts` refuses to run if any of the three hashes differs.

**User messages.** Both arms receive the composed-view packet exactly as the sealed scorer builds it (`stage3_views.o_packet`), with nothing added. Packet field names: the sealed composed-view intro line; `Document`; `From`; `To`; `Unified diff (<n> chars)`; the diff text. No label, id, regime, example or plant content appears in either prompt.

**One prompt, one shot.** The paragraph was written by a session that has seen no plant, packet or transcript. Its wording changed once before this freeze, on the Codex read (`TP/codex-read.md`; draft 1 was 157c5ec4, never used in a call). It is not revised after any score is read.

**Source.** Modelled on SLEIGHT-Bench (arXiv 2605.16626), the "Doc-Planting Aware" monitor prompt, Appendix D.4; see `TP/preregistration-addition-TP.md`.

**Judge settings** (both arms, as the record and ETJ): `anthropic.claude-opus-4-8` on Bedrock through the pinned `judge_client.py` (72d394e3), effort default, max tokens 4,000; no OpenRouter request.
