# S3 table v1: honest deviance d by source, generator and rule, with the released MOLE corpora

Executor for line S3, Opus 5.5, 2026-11-13.

**Inputs.**
- Rules: `stage3_s3_deviance.py` 403f17c4, unchanged since the freeze (fork ed1623a). Judge prompt: `s3-semantic/v1` 333e5ea4.
- Released-corpora driver: `stage3_s3_upstream.py` 12848d69. The scans ran under ebe95fbd and 9ca399e5; their counts were recounted under 12848d69 and are equal. See `result.md`.
- Per-split records: `upstream/s3-upstream-<split>.json`. Judge records: `upstream/s3-judge-records-<split>.jsonl`. Task-bank overlap: `upstream/s3-upstream-bank-overlap.json`.
- Transcripts manifest: `mole-transcripts-manifest.json`, 18 files, 8,249,386,038 bytes.
- The prefix rows are carried from v0 unchanged. v0 stays as written.
- Counts, ids, hashes and flags only.

**How to read it.**
- d is the share of honest changing file writes that their task does NOT license.
- **Intervals** are 95% percentile bootstraps clustered on session: 2,000 resamples, seed 20261113.
- **The S column** is Sonnet 5 on Bedrock, on a seeded sample of 300 writes per split. Each split's sample is uniform, and the pooled rows weight the two splits by their sizes. The k/n in a pooled S cell is the unweighted sample count.
- **"No task at all"** counts writes from sessions that were fed no agenda item. They are outside the n.
- **Unit and honest filter.** The unit is a successful ownCloud `write_file` or GitLab `commit` that changes the resource. A session is honest only if it is benign (no insider persona) and its account-day has no label row.
- **Unscored units.** Six sampled writes were not scored: 4 gpt53 replies stopped at max_tokens with no parseable answer (after the client's re-asks), and on qwen36_27b_multiday 1 failed the same way and 1 was refused. All six are left out of d_S and of the agreement counts, with no imputation, and are shown as the gap between n and 300.

## The table (prefix and released corpora; FakeLab rows are not in this copy)

| source | generator | scope | n writes | n sessions / sequences | d under L | d under S (judge sample) | d under the proxy | no task at all | proxy vs judge: agreement, kappa (n) |
|---|---|---|---|---|---|---|---|---|---|
| prefix_rw_v2c | moonshotai/kimi-k2.6 | class documents (item level defined) | 127 | 97 | 0.244 [0.163, 0.327] (31/127); item level 0.465 [0.376, 0.550] (59/127) | 0.307 [0.222, 0.389] (39/127) | 0.244 [0.163, 0.327] (31/127) | 0 | 0.921, 0.804 (127) |
| prefix_rw_v2c | moonshotai/kimi-k2.6 | other file writes | 960 | 243 | 0.769 [0.734, 0.801] (738/960) | 0.526 [0.437, 0.614] (91/173) | 0.756 [0.720, 0.790] (726/960) | 94 | 0.763, 0.514 (173) |
| prefix_rw_v2c | moonshotai/kimi-k2.6 | all file writes (stratified judge sample, weighted) | 1087 | 252 | 0.707 [0.673, 0.742] (769/1087) | 0.500 [0.421, 0.576] (130/300) | 0.696 [0.661, 0.732] (757/1087) | 94 | 0.830, 0.663 (300) |
| MOLE released | gpt53 | gpt53_single_day | 43705 | 25113 | 0.194 [0.190, 0.198] (8492/43705) | 0.134 [0.097, 0.171] (40/299) | 0.169 [0.166, 0.173] (7405/43705) | 0 | 0.799, 0.202 (299) |
| MOLE released | gpt53 | gpt53_multiday | 48180 | 27480 | 0.181 [0.177, 0.185] (8721/48180) | 0.138 [0.101, 0.181] (41/297) | 0.156 [0.153, 0.160] (7540/48180) | 21 | 0.811, 0.174 (297) |
| MOLE released | kimi_k26 | kimi_k26_single_day | 90909 | 25074 | 0.737 [0.733, 0.740] (66999/90909) | 0.633 [0.577, 0.688] (190/300) | 0.706 [0.702, 0.710] (64201/90909) | 6303 | 0.730, 0.389 (300) |
| MOLE released | kimi_k26 | kimi_k26_multiday | 93034 | 25835 | 0.742 [0.739, 0.746] (69049/93034) | 0.617 [0.561, 0.670] (185/300) | 0.712 [0.709, 0.716] (66276/93034) | 8722 | 0.723, 0.388 (300) |
| MOLE released | deepseek_v4_flash | deepseek_v4_flash_single_day | 79356 | 20996 | 0.828 [0.825, 0.831] (65716/79356) | 0.777 [0.728, 0.821] (233/300) | 0.794 [0.791, 0.798] (63041/79356) | 22595 | 0.827, 0.506 (300) |
| MOLE released | deepseek_v4_flash | deepseek_v4_flash_multiday | 71314 | 19043 | 0.836 [0.833, 0.839] (59631/71314) | 0.740 [0.689, 0.788] (222/300) | 0.799 [0.795, 0.803] (56968/71314) | 34083 | 0.793, 0.414 (300) |
| MOLE released | qwen36_27b | qwen36_27b_single_day | 122010 | 30388 | 0.734 [0.731, 0.737] (89532/122010) | 0.650 [0.597, 0.703] (195/300) | 0.692 [0.689, 0.695] (84426/122010) | 2173 | 0.750, 0.439 (300) |
| MOLE released | qwen36_27b | qwen36_27b_multiday | 122814 | 30904 | 0.739 [0.736, 0.742] (90755/122814) | 0.614 [0.559, 0.667] (183/298) | 0.700 [0.697, 0.703] (86005/122814) | 3516 | 0.732, 0.409 (298) |
| MOLE released | gpt53 | gpt53_single_day + gpt53_multiday (pooled; judge weighted) | 91885 | 52593 | 0.187 [0.185, 0.190] (17213/91885) | 0.136 [0.109, 0.165] (81/596) | 0.163 [0.160, 0.165] (14945/91885) | 21 | 0.805, 0.188 (596) |
| MOLE released | kimi_k26 | kimi_k26_single_day + kimi_k26_multiday (pooled; judge weighted) | 183943 | 50909 | 0.740 [0.737, 0.742] (136048/183943) | 0.625 [0.587, 0.664] (375/600) | 0.709 [0.707, 0.712] (130477/183943) | 15025 | 0.727, 0.389 (600) |
| MOLE released | deepseek_v4_flash | deepseek_v4_flash_single_day + deepseek_v4_flash_multiday (pooled; judge weighted) | 150670 | 40039 | 0.832 [0.830, 0.834] (125347/150670) | 0.759 [0.724, 0.793] (455/600) | 0.797 [0.794, 0.799] (120009/150670) | 56678 | 0.810, 0.459 (600) |
| MOLE released | qwen36_27b | qwen36_27b_single_day + qwen36_27b_multiday (pooled; judge weighted) | 244824 | 61292 | 0.736 [0.734, 0.738] (180287/244824) | 0.632 [0.593, 0.672] (378/598) | 0.696 [0.694, 0.698] (170431/244824) | 5689 | 0.741, 0.424 (598) |

## Generator against task bank on the released corpora

**The bank is shared.**
- The fed task texts, folded to their bank variant and hashed, give 10,532 distinct variants across the eight splits. 5,763 of them appear in all eight.
- 81 to 96 percent of each split's fed items are on those shared variants (gpt53 81, kimi 87 to 93, deepseek 93 to 96, qwen 90 to 94).
- Pairwise Jaccard overlap of the variant sets runs from 0.66 to 1.00.
- So the four generators were fed from one task bank, mostly the same variants.

**On that shared bank, d differs sharply by generator.**

| generator | L (pooled) | judge (pooled) |
|---|---|---|
| gpt53 | 0.19 | 0.14 [0.11, 0.17] |
| kimi_k26 | 0.74 | 0.63 [0.59, 0.66] |
| qwen36_27b | 0.74 | 0.63 [0.59, 0.67] |
| deepseek_v4_flash | 0.83 | 0.76 [0.72, 0.79] |

Within each generator, single-day and multi-day agree.

**What the rows show.** With the bank held nearly fixed, the generator moves d by a factor of four to five under either rule. So d is not a property of the bank alone.

**What the rows do not show.** They do not show that the generator alone causes the gap. The generator also shapes which bank items a session actually receives, and how much it writes:
- **How many tasks get fed.** An agenda item is fed only after the previous one is done. gpt53 sessions were fed about 3.0 items each (about 100k per split). deepseek sessions were fed about 1.2 (38k to 44k per split), and 11k to 14k deepseek sessions were fed none.
- **How much each session writes.** gpt53 makes 1.7 changing writes per session; the other three make 3.6 to 4.0.
- **The service mix.** gpt53 writes more GitLab commits (37 percent, against 22 to 32 percent).

These differences are confounded with the generator by construction. A design that fixes the fed task per session is needed to separate them.

**Further cautions.**
- Kappa between the proxy and the judge is low on gpt53 (0.17 to 0.20) and moderate elsewhere (0.39 to 0.51). The proxy should not stand in for the judge on any split.
- The judge is one model on one prompt, with no human check.

## Beside the table (released corpora)

- **Writes dropped by the honest filter:** 443 to 7,551 per split, from labelled account-days. Single-day splits carry many more label rows. No write was dropped by the session-mode test alone, because every non-benign session sits in a labelled account-day.
- **No-op writes:** 670 to 5,708 per split, excluded.
- **Writes whose task_id has no transcript:** 178 (kimi_k26_single_day) and 94 (kimi_k26_multiday), counted as no task.
- **Writes with no task at all:**

| split | writes with no task |
|---|---|
| gpt53_single_day | 0 |
| gpt53_multiday | 21 |
| kimi_k26_single_day | 6,303 |
| kimi_k26_multiday | 8,722 |
| deepseek_v4_flash_single_day | 22,595 |
| deepseek_v4_flash_multiday | 34,083 |
| qwen36_27b_single_day | 2,173 |
| qwen36_27b_multiday | 3,516 |

## Judge dollars (released corpora)

$7.25 realised against $5.21 estimated for 2,400 calls. Each split ran at 1.31 to 1.43 times its estimate, under the 1.5 stop. Per split in `result.md`.
