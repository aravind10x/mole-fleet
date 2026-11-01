# Brief 31: the judge client's default-path equivalence against the sealed nulls, and S3's pre-flight pin (blue; counts, field names, key names and hashes only)

**Done, $0, no request sent.**

- **G1, requests: equal.** Every null packet of S3's nine view-and-judge cells was rebuilt and matched its cache key: 1,296 packets, 89 or 254 per cell, not a sample of 20. The bound-hash client and the current client built byte-identical requests and identical records for all of them. In the eight Anthropic cells, the request the current client sends carries exactly the request fields that the null's own calls recorded. Sol's cell differs from its OpenRouter-scored null in two fields only, the model id and the temperature. That is the provider switch brief 09's check covered, not a client change.
- **G2, replies: equivalent by construction, not by re-parse.** No cache holds the raw reply, only the parsed fields. Every reply shape the old parsers accept gave identical outcome, score, flag, rationale and refusal status through the old and current parsers: 51 of 51 Anthropic shapes, 49 of 49 Converse shapes, 43 of 43 OpenRouter shapes.
- **One default-path change, named.** When a unit is aborted after a paid attempt, the current client writes one extra errored line to the cache. It changes no request and no returned value.
- **G3:** the test is re-bound to 72d394e3 by a dated note.
- **G4:** S3's pre-flight exists with its test, and it passes on the tree: 24 of 24 files, fork copies identical, the three sealed prompt components reproduced.
- **G5:** fixed. The write-yield test had read the re-weighted class as its starting design since the commit that added it.

Executed: brief 31 v2 (`briefs/31-judge-client-equivalence-2026-11-01.md`, 645ceb96). Session: Opus 5.5 in Claude Code, 2026-11-01 night. Python: the fork's `.venv` (3.12). Script `work/checks/stage3_b3_client_equivalence.py` (fdfc0bf3); its output `judge-client-equivalence-v0.json` (abeb3a68) holds every number below.

## The caches opened, by path and hash (the barrier)

The cells come from plan.md §2.6. Each cell's cache and null come from these records:
- **B1:** the per-judge cache pattern at `work/stage3/b1/plan.md` line 54. `b1-null.json` and `b1-results.json` record client 1675a966 at every step.
- **Brief 15:** Section 0's instruments, and A6.3 (e)'s composed view under Sonnet 5, Opus 4.8 and Sol. plan.md §4.9 lists these nulls by hash.
- **Sol:** the 07p plan names `judge-cache.q1q2extra.{O_diff,P_author}.<slug>.jsonl`.

All caches were listed and hashed before any was opened, and were opened by script only.

| cell (view, judge) | cache | sha256 | records | null file (rows) | client that scored the null |
|---|---|---|---|---|---|
| `P_author_doc` isolated, Opus 4.8 | `work/stage3/b1/judge-cache.b1opus-default.P_author_doc_iso.anthropic-claude-opus-4-8.jsonl` | `4859f6b7968aedd0…` | 857 | `b1/b1-null.json` 54901c9c (89) | 1675a966 (recorded) |
| `P_author` zero-context, Opus 4.8 | `work/stage3/q1q2-synthetic/opus48/judge-cache.q1q2opus-default.P_author.anthropic-claude-opus-4-8.jsonl` | `2a7cd7ad3649c9b7…` | 377 | `opus48/judge-null.json` 66028856 (89) | not recorded; 1675a966 is 07n part C's own amendment (t1v3-plan.md §8) |
| `P_author_doc` isolated, Sonnet 5 | `work/stage3/b1/judge-cache.b1.P_author_doc_iso.anthropic-claude-sonnet-5.jsonl` | `42d3fec47cd28c07…` | 857 | `b1/b1-null.json` (89) | 1675a966 (recorded) |
| `P_author` zero-context, Sonnet 5 | `work/stage3/views/judge-cache.P_author.anthropic-claude-sonnet-5.jsonl` | `7f1bbb031ec42dcd…` | 200 | `views/calibration-v1.json` 44ea1c26 (89 rows in `p_author_c0.json`) | fdce438b (recorded in `p_author_c0.json` meta) |
| `P_author_doc` live, Opus 4.8 | `work/stage3/b1/judge-cache.b1opus-default.P_author_doc_live.anthropic-claude-opus-4-8.jsonl` | `62ddfbdb14e3f931…` | 857 | `b1/b1-null.json` (89) | 1675a966 (recorded) |
| `P_author_doc` live, Sonnet 5 | `work/stage3/b1/judge-cache.b1.P_author_doc_live.anthropic-claude-sonnet-5.jsonl` | `9497898e61a9b4aa…` | 857 | `b1/b1-null.json` (89) | 1675a966 (recorded) |
| `O_diff`, Sonnet 5 | `work/stage3/views/judge-cache.O_diff.anthropic-claude-sonnet-5.jsonl` | `332e48209656ae2d…` | 254 | `views/calibration-v1.json` (254 rows in `o_diff_cumulative.json`) | fdce438b (recorded in `o_diff_cumulative.json` meta) |
| `O_diff`, Opus 4.8 | `work/stage3/q1q2-synthetic/opus48/judge-cache.q1q2opus-default.O_diff.anthropic-claude-opus-4-8.jsonl` | `b1c6360e68a39ae5…` | 406 | `opus48/judge-null.json` (254) | as `P_author`, Opus 4.8 |
| `O_diff`, GPT-6 Sol | `work/stage3/q1q2-synthetic/judge-cache.q1q2extra.O_diff.openai_gpt-6-sol.jsonl` | `6bbbe9722f3fc881…` | 406 | `extra-judge-null.sol.json` 745fab80 (254) | OpenRouter, 07p: `judge_openrouter`, inferred 29f5157a (07p records no client hash; the fork has no other version before brief 23); reused on Bedrock after brief 09's provider check (client 8390cfd7) |

Full hashes are in the JSON (`g1_cells[].cache.sha256`). Besides the caches, the script read:
- the null files, for their row labels and key names;
- `views/p_author_c0.json` and `views/o_diff_cumulative.json`, for row labels only (the second has a `packets` key, which was not read);
- the corpus `prefix_rw_v2c.jsonl` (ffc1f6cd), to rebuild the packets, which were hashed and never printed.

From each cache it kept only the cache key, label, outcome, packet sha256 and length, model, prompt version, request fields, re-ask count and attempt outcomes. Score, flag and rationale were never kept or printed.

**Not opened, by any script:** `work/stage3/pilot/archived-scores.*`, `work/stage3/pilot/measure/archived-scores.*`, `work/stage3/red/`, persona files, rater-key files, and B3's candidate, control and paste files. Brief 09's provider-check file is cited, not opened. The pre-flight (G4) hashes the files plan.md lists, B3's comprehension and population files among them. It reads their bytes for the sha256 only.

## G1. The diff on the default path, and the request comparison

**The failing test and its bound hash.** The test is `work/checks/test_stage3_t1v3_score.py::test_binding_check_accepts_only_the_disclosed_judge_client_hashes`. It asserted that the current client's sha256 is in `stage3_t1v3_score.JUDGE_CLIENT_SHA256_ACCEPTED`:
- fdce438b, sealed;
- 80f1bdba, the 07i part 2 amendment;
- 1675a966, the 07n part C amendment, the last accepted.

**The bound hash is 1675a966** (fork afeeb5b, `results/stage3/q1q2-synthetic/judge_client.amended-2026-10-26.py`). The current file is 72d394e3 (fork 3ac319a, `scripts/stage3/judge_client.py`).

The client's versions, all extracted from the fork history and hash-checked by the script:

| sha256 | fork commit | what changed |
|---|---|---|
| fdce438b | none | T1 v3's seal and Sonnet 5's calibration nulls (`views/*.json` meta); **on disk nowhere**, in no tree or fork commit |
| 80f1bdba | dc4af84 | 07i part 2 (2026-10-26): the Opus 5.5 path |
| 1675a966 | afeeb5b | 07n part C (2026-10-26): the Opus 4.8 entry (price, adaptive thinking); B1's nulls |
| 8390cfd7 | f1124b6 | brief 09 (2026-10-29): `BedrockConverseJudge` for GPT-6 Sol |
| bd2d4ebd, 8abb6079 | fc21468, f2fcd57 | brief 23 I1 and its Codex round (2026-10-31) |
| 72d394e3 | 3ac319a | brief 23 routes (2026-10-31); the pinned client |

The verdict parser is not in this file. Every version imports `_parse_verdict` from the fork's `scripts/first_cut_monitors.py` (a778486d, last changed 2026-10-08, before every sealed null). In every loaded version it is the same function object.

### Replies (1675a966 to 72d394e3; 8390cfd7 to 72d394e3 on the Converse path)

- **`classify(response, parse=None)`** gains an optional parser. With `None` its body is unchanged:
  - `refused` if and only if `stop_reason == "refusal"`;
  - empty text is `errored`;
  - otherwise `_parse_verdict` gives `scored`, or `errored` with the text's first 300 characters.
- **`classify_converse(response, parse=None)`** gains an optional parser in the same way. With `None` its body is unchanged:
  - `refused` if and only if `stopReason` is `content_filtered` or `guardrail_intervened`.
- **Retry defaults, unchanged in both versions:**
  - `refusal_retries` defaults to `MAX_REFUSAL_RETRIES` = 1;
  - `MAX_PARSE_RETRIES` 2, `MAX_429_RETRIES` 2, `MAX_TRANSIENT_RETRIES` 3;
  - backoff 5 s, rate-limit pause 60 s, `ABORT_STATUSES` {400, 401, 403, 404};
  - `DEFAULT_SPEND_CAP_USD` 50, `REQUEST_TIMEOUT_S` 300.
- **The guard:** `request_guard` defaults to `None`, so it is never called.
- **The endpoint:** `endpoint` defaults to `"mantle"`, which builds `AsyncAnthropicBedrockMantle` as before. The record gains an `endpoint` key only for `"runtime"`.
- **Prices:** the `PRICES` entries for `anthropic.claude-sonnet-5` and `anthropic.claude-opus-4-8` are unchanged, and so are `CONVERSE_PRICES[us.openai.gpt-6-sol]` and `CONVERSE_MAX_TOKENS` (4000).
- **The one default-path change: an abort after a paid attempt writes one more line.** In `JudgeClient._score_uncached` and in `BedrockConverseJudge._score_uncached` (the same change is in `OpenRouterJudge`), a `JudgeAborted` raised after at least one paid attempt of the unit now saves an `errored` record before re-raising. The record carries `"error": "aborted after paid attempts"`, the tokens and the cost.
  - Unchanged: the call raises the same `JudgeAborted` with the same message, after the same number of requests (the G2 loop test).
  - Errored records are never served from the cache; they are re-asked on a rerun.
  - **Direction:** the line's cost enters `dollars_cached`, so a later run's spend cap also counts the paid attempts of an aborted unit. No score, flag or refusal status changes.
  - None of the 1,296 null calls was aborted.

### Requests

- **Model id:** passed by the caller, and every S3 caller passes it. `DEFAULT_MODEL` is unchanged (the Sonnet 5.5 id).
- **Temperature:** absent in both versions. No sampling parameter is sent.
- **Max tokens:** `MAX_TOKENS` is still 900, the Sonnet callers' value. The Opus 4.8 callers pass 4000. Converse is fixed at 4000.
- **Thinking and reasoning:** `thinking_param` is unchanged: `disabled` for Sonnet 5, `adaptive` for Opus 4.8, and no `output_config` without an effort. Converse sends no reasoning field.
- **System prompt and packet assembly:** the keyword arguments `_request` builds are unchanged: `model`, `max_tokens`, `thinking`, `messages=[{"role": "user", "content": packet}]` and `system`. `BedrockConverseJudge.request_kwargs` is unchanged too. The packets and system prompts come from the pinned view modules: `stage3_views` 6ec08e98, which is also the `views_module_sha256` of Sonnet's step-1 outputs; `stage3_author_doc` a4b06e55; `stage3_b1_dossier` 711c88ba.
- **Cache key:** `cache_key` is unchanged (`view|label|sha256(packet)`), and so is `request_params`.

**Off the default path, listed separately:**
- `classify_parsed` and `ReplyParser`: brief 23's parser. Its `refused: True` marker makes the reply refused; a reply it cannot parse is errored and re-asked.
- `refusal_retries` other than 1, `request_guard`, and `endpoint="runtime"` (with the price entry for `global.anthropic.claude-sonnet-5-5`).
- The docstring correction on Sonnet 5.5 access, and the new names in `__all__`.

In `judge_openrouter.py`, 29f5157a to e812157c, which is not on S3's path:
- `parse`, `moderation_as_refusal`, `request_guard`, and `api_key_env` with the stashed fallback keys.
- `temperature=None`. The fork's `mole/llm/openrouter.py` then leaves the field out (changed in f2fcd57); only `None` is left out, and the default 0.0 is still sent.
- `reasoning_setting()` on the record. It reads `OPENROUTER_REASONING_EFFORT` and records "provider default" when that is unset, as before.
- Its default-path changes are the same abort line, and `score_many` now lets every call settle before it raises. That is an error path only; on success the results are unchanged.

### The byte comparison of built requests (no request sent)

**Method.** For each cell, the null's units were rebuilt with the scorers' own builders (`stage3_views_seal.reproduction_check`, `judge_opus_q1q2`, `stage3_b1_dossier.build_world` without plantings). Each unit was kept if its `view|label|sha256(packet)` is a key in the cell's cache; every rebuilt unit was kept.

Each kept packet was then given to two clients loaded side by side:
- the bound-hash client, 1675a966; on Sol's Converse path, which 1675a966 lacks, brief 09's 8390cfd7, the provider check's client;
- the current client, 72d394e3.

Each client was built with the arguments its caller passes. An injected stub transport recorded the request and returned one fixed reply written in the script. Then:
1. the two requests were compared as canonical JSON bytes;
2. the two returned records were compared field by field, with `ts` and `latency_s` set aside;
3. the request the current client sent was compared with the request fields the null's own call recorded: model, max_tokens, thinking, system prompt sha256 and length, packet sha256 and length, and no other request key.

| cell | pair | rebuilt / in cache (= null rows) | requests byte-equal | records equal | sent = recorded | fields that differ |
|---|---|---|---|---|---|---|
| `P_author_doc` iso, Opus 4.8 | 1675a966 / 72d394e3 | 89 / 89 | 89 | 89 | 89 | none |
| `P_author`, Opus 4.8 | 1675a966 / 72d394e3 | 89 / 89 | 89 | 89 | 89 | none |
| `P_author_doc` iso, Sonnet 5 | 1675a966 / 72d394e3 | 89 / 89 | 89 | 89 | 89 | none |
| `P_author`, Sonnet 5 | 1675a966 / 72d394e3 | 89 / 89 | 89 | 89 | 89 | none |
| `P_author_doc` live, Opus 4.8 | 1675a966 / 72d394e3 | 89 / 89 | 89 | 89 | 89 | none |
| `P_author_doc` live, Sonnet 5 | 1675a966 / 72d394e3 | 89 / 89 | 89 | 89 | 89 | none |
| `O_diff`, Sonnet 5 | 1675a966 / 72d394e3 | 254 / 254 | 254 | 254 | 254 | none |
| `O_diff`, Opus 4.8 | 1675a966 / 72d394e3 | 254 / 254 | 254 | 254 | 254 | none |
| `O_diff`, GPT-6 Sol | 8390cfd7 / 72d394e3 | 254 / 254 | 254 | 254 | 0 | `model` 254, `temperature` 254 (the provider switch) |

- **Sent = recorded.** The Anthropic request keys are exactly `max_tokens`, `messages`, `model`, `system` and `thinking`. For Sonnet's two calibration cells, the recorded fields were written by fdce438b, so the current client's request matches the sealed client's recorded request directly.
- **The one step from 80f1bdba to 1675a966** on Sonnet's path was compared the same way. Requests and records are equal in all four Sonnet cells (89, 89, 89, 254), and so is the scoring loop (15 of 15).
- **Not reachable: fdce438b to 80f1bdba.** The file exists nowhere. t1v3-plan.md §8 bridged that step: the Sonnet request and record were byte-identical, by `test_judge_client_opus.py`.
- **Sol's two fields are the provider switch.**
  - `model`: `openai/gpt-6-sol` on OpenRouter against `us.openai.gpt-6-sol` on Bedrock.
  - `temperature`: 0.0 sent on OpenRouter, a parameter GPT-6 Sol does not list as supported, against not sent on Converse.
  - Equal in all 254: max_tokens 4000, reasoning at the provider default, the system prompt and the packets.
  - The switch is what brief 09's pre-registered provider check covered: Spearman 0.914, verdict unchanged 37 of 40, PASS, so Sol on Bedrock reuses 07p's null and rules.
- **The OpenRouter client, beside (off S3's path; it scored Sol's null).** 29f5157a against e812157c on the same 254 packets: requests byte-equal 254, records equal 254, sent = recorded 254 against the 07p cache.

**What the null calls exercised** (counts from the caches): all 1,296 null records are `scored`. One unit has a parse re-ask, in `P_author_doc` live under Opus 4.8 (errored, then scored). There is no refusal and no abort. The stop labels are `end_turn` on Bedrock and `stop` on OpenRouter.

## G2. The caches' shape, and the parser test by construction

**Shape, by key names.** None of the nine caches holds the raw reply text.

Every Anthropic cache record carries the same keys:
`cache_key, view, label, outcome, score, flag, rationale, stop_reason, stop_details, error, provider, model, model_served, region, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, cost_usd, price_source, packet_chars, packet_sha256, prompt_version, request_params, parse_retries, attempts, latency_s, ts`.
- `request_params` holds `model, max_tokens, thinking, system_sha256, system_chars`.
- `attempts[]` holds `outcome, stop_reason`.

Sol's OpenRouter cache adds `finish_reason, reasoning_tokens, cost_source`. Its `request_params` holds `model, max_tokens, temperature, reasoning, system_sha256, system_chars`, and its `attempts[]` holds `outcome, finish_reason`.

`rationale` is the parsed rationale (`_parse_verdict` caps it at 600 characters), not the reply. No re-parse is possible, so the fallback applies.

**The parser test, labelled "by construction, not by re-parse"** (for the record and S1's disclosures). The reply shapes are written in the script. They come from every branch of `_parse_verdict` and from the client tests' shapes (`test_judge_client.py`'s classify tests, `test_judge_client_converse.py`, `test_judge_openrouter.py`), never from cached content.

There are 36 reply texts:
- clean JSON at scores 0, 12, 49, 50, 72 and 100 (the flag is score ≥ 50, whatever the model's flag says);
- JSON in prose and in a code fence;
- the score as a string, a float, a word, null, a bool, negative or above 100;
- no score key, an empty object, a nested score, extra keys;
- brief 23's refused marker, with and without a score;
- the rationale long, a number, a list, missing, or non-ASCII;
- truncated JSON, malformed JSON with a salvageable score, two objects, a score in prose;
- a four-digit fragment, unparseable prose, "DECLINED", braces without JSON.

Each family also gets its response shapes:
- **Anthropic:** refusal with or without text, details absent, as an object or as a dict; max_tokens empty, truncated or full; whitespace; no content; thinking then text; thinking only; JSON split across blocks; `stop_sequence`; stop None; content None.
- **Converse:** content_filtered and guardrail_intervened; max_tokens; reasoning blocks; split blocks; a text None block; no output; response None.
- **OpenRouter:** content_filter, refusal, length, content None, finish None.

| comparison | equal | differences |
|---|---|---|
| Anthropic `classify`, 1675a966 against 72d394e3 (and against `parse=None`) | 51 / 51 | none; outcomes scored, refused and errored all covered |
| Anthropic `classify`, 80f1bdba against 1675a966 | 51 / 51 | none |
| Anthropic scoring loop (`JudgeClient.score` end to end on a scripted stub: re-asks, refusal re-ask, 429, 5xx, connection error, 4xx abort; returned record, request count and cache lines compared) | 13 / 15 | the 2 abort-after-a-paid-attempt sequences: `cache_lines` has one more line (the errored record above); result and request count equal |
| Anthropic scoring loop, 80f1bdba against 1675a966 | 15 / 15 | none |
| Converse `classify_converse`, 8390cfd7 against 72d394e3 | 49 / 49 | none |
| Converse scoring loop | 7 / 8 | the abort-after-a-paid-attempt sequence: one more cache line |
| OpenRouter `classify`, 29f5157a against e812157c (off S3's path) | 43 / 43 | none |
| Sol's null to S3's Sol: OpenRouter 29f5157a against Converse 72d394e3 on the same 36 reply texts (outcome, score, flag, rationale) | 36 / 36 | none; refusal signals are provider-specific by construction (Sol's null had 0 refusals) |

**Equivalence: by construction, not by re-parse.** On every reply shape the old parsers accept, the current parsers return the same outcome, score, flag, rationale and refusal status.

## G3. The decision: re-bind

G1's request comparison is equal, and G2 shows equivalence by construction. The abort-path line is a default-path change. It alters neither what is sent nor how a reply is read, and so it cannot move a score against a sealed threshold. On that reading it does not stop G3; it is reported here, with its direction, for the coordinator. If the coordinator reads it as a difference, the re-bind is one constant to revert.

**Re-bound by a dated note in `test_stage3_t1v3_score.py`** (6b63506a):
- The test now binds 72d394e3 directly (`JUDGE_CLIENT_SHA256_REBOUND`), so the next client change fails it again.
- The binding check's logic is tested for each hash T1 v3 accepts. The test patches `file_sha256` so the check reads each accepted hash as the client's.
- **T1 v3's scorer is unchanged.** It keeps its three accepted hashes, because its runs are done, so it still refuses to run under 72d394e3. The test asserts that.

**The diff, summarised for the note:**
- From 1675a966 to 72d394e3, the default path is unchanged in what is sent and in how a reply is parsed.
- The additions are opt-in: the parser, refusal re-asks, the guard and the runtime endpoint, plus the Converse class added in brief 09.
- The only default-path behaviour added is the abort-path cache line.

## G4. S3's pre-flight

**Script:** `work/checks/stage3_b3_preflight.py` (220679d2). **Test:** `work/checks/test_stage3_b3_preflight.py` (3746ecf0, 10 tests). Both have byte-identical fork copies.

**It refuses to start on any of these, printing every hash it found:**
- `work/stage3/b3/plan.md` is not byte-identical to the fork's committed `results/stage3/b3/plan.md` at HEAD;
- the fenced `s1-preflight-sha256` block is malformed: a line not in `shasum -c` form, a duplicate path, a path outside the root, or an empty or unclosed block;
- a listed file is missing or has another sha256;
- a listed `work/checks` script's fork copy differs;
- after every file matches, the pinned `stage3_views.py` no longer reproduces the three prompt components sealed in `calibration-v1.json`: shared-harm/v1 a21d902f, the `P_author` system prompt 4ff70a48 and the `O_diff` system prompt 0dad3af9.

**Options:**
- `--config` checks S3's values against the plan's: placement seed 20261181, arm seeds 20261181 × 100 + 10 t with arms 1 to 4 required and 5 and 6 allowed, bootstrap 20261152 with 2,000 replicates, tie 20261112, m_s 18.22 and 19.37, m_L 18.22. A test reads these values back out of plan.md's paragraph.
- `--out` writes the hashes it ran on, for S3's record.

**Run now:** plan.md 4c677dee, identical to fork dc5a082's copy; one block, at line 811. 24 of 24 files OK, every fork copy identical, the three prompt components OK. **PRE-FLIGHT PASS.**

`test_the_real_tree_passes_the_pre_flight` makes the full suite fail whenever a pinned file changes without a dated note moving its pin.

**The rule for later changes to any pinned file** (brief 31; brief 29-B's E0-7 provider preferences in `judge_openrouter.py` are the first case):
1. The change is opt-in, with every default unchanged and tested.
2. G1's request comparison and G2's check are repeated against the new file. The tool is `stage3_b3_client_equivalence.py`: add the new version to `SOURCES` and compare it with the pinned one, as the OpenRouter pair here is compared. The tool cannot replace those tests.
3. Then a dated note at plan.md's end moves the pin. **The note restates the whole block, because the pre-flight reads the last block in the plan as the complete list.**
4. S3's record states the hashes it ran on, from `--out`.

## G5. The writer-path test

`test_stage3_write_yield.py::test_propose_raises_write_counts_until_every_document_clears_the_target_and_keeps_reads` failed with `155 > 155`. The cause has nothing to do with any judge route:
- The commit that added the test, fork 019db8a (brief 07e E3, 2026-10-21), also replaced `stage3_rung1_class.CLASS`'s write counts with the proposal's output. That is bank v6, 155 write variants.
- The test still took `rc.CLASS` as the short design to raise. So `propose` correctly raised nothing, and the test has failed since that commit.

**Fixed by a dated note in the test** (20fdc225; the fork copy is identical and now in `test_fork_copies_identical.py`'s list):
- The design it raises is bank v5's write counts: 68 variants, from 019db8a's diff and rung1-class.md's version table.
- It now also asserts that the proposal reproduces the shipped v6 counts exactly. It does.
- 6 of 6 pass. This test does not gate S3.

## Tests

- New: `test_stage3_b3_client_equivalence.py`, 11 tests, offline. Among them:
  - an injected change to the thinking setting is named `thinking.type`;
  - a wrong source hash is refused;
  - the cache index keeps no reply content;
  - the abort line is found and nothing else is.
- New: `test_stage3_b3_preflight.py`, 10 tests.
- `test_stage3_t1v3_score.py`: 8 of 8 pass. `test_stage3_write_yield.py`: 6 of 6 pass.
- Full suite (`work/checks`, the fork's venv, run without a pipe): **1,058 passed, 1 skipped, exit 0**, in 11 min 48 s. The skip is a skip condition in an existing test; none of this brief's tests skip. The two failures brief 27 reported as pre-existing, the judge-client hash binding and write_yield, now pass.

## Files

| file | sha256 |
|---|---|
| `work/checks/stage3_b3_client_equivalence.py` (G1, G2) | fdfc0bf39e9d962ca72f9dab028951ab4d56fc1a44c72d3b8bd010118dc25f3a |
| `work/checks/test_stage3_b3_client_equivalence.py` | a3809f3bd3c9e8a7ae7e52e37f7caea238ed910dbe9a81f3e159e5f656904924 |
| `work/stage3/b3/judge-client-equivalence-v0.json` (G1 and G2 output) | abeb3a6823940b8f1578db0bdf517564336aba0e4aa8627e04ecde634d35c54f |
| `work/checks/stage3_b3_preflight.py` (G4) | 220679d2db24e493ad69cc5a9c5cb56c6d8b30cded5e63d80b9626265b32a325 |
| `work/checks/test_stage3_b3_preflight.py` | 3746ecf07b6ca2dac054084813f8c65a09494bb31f5aa444850242866b7e9a39 |
| `work/checks/test_stage3_t1v3_score.py` (G3 re-bind) | 6b63506a080ca5cb77e3d5b3891838394795ea0ddc9d8867049fbb7354f252d6 |
| `work/checks/test_stage3_write_yield.py` (G5) | 20fdc2252a3c212e4d39e93a4a4fb19dac5c088fdcd6ee34691bb1b78fe818c0 |
| `work/checks/test_fork_copies_identical.py` (the five new or newly listed files) | f1c665c056b8ad7075e5a75f3279af6600daed8fb78c31f3b538414b1f29e2ef |

Unchanged, as the brief requires: `judge_client.py` 72d394e3 and `judge_openrouter.py` e812157c, with no change needed. Also unchanged: `stage3_t1v3_score.py` and plan.md 4c677dee. Fork mirror: every file above is under `scripts/stage3/`, and this record and its JSON are under `results/stage3/b3/`, in one commit on `stage3`. STATUS names the commit. It is not pushed.

## Barrier

- No judge was called and no request was sent. The three client classes ran only against stub transports defined in the script.
- No reply text, rationale, score, flag, item line, packet or document text was printed or written. Packets were held in memory to be hashed and handed to the stubs.
- The script's output holds counts, field names, key names, labels of reply shapes written in the script, and hashes.
- No file on the off-limits list was opened.
