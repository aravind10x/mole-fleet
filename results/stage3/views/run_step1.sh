#!/bin/bash
# Step 1 of brief 07f: the honest calibrations of the five views under the shared harm text (views-calibration.md
# section 3 written first). Sequential; one judge cache per view; Bedrock anthropic.claude-sonnet-5; spend caps per view.
set -uo pipefail
R=/Users/aravind/KruxAI/tais-project-selection; F=$R/work/mole-fork; C=$R/work/checks; V=$R/work/stage3/views
cd "$F"; set -a; source "$F/.env"; set +a
PY="$F/.venv/bin/python -I"; CORPUS="$F/data/corpus/spike/prefix_rw_v2c.jsonl"; M=anthropic.claude-sonnet-5; SLUG=anthropic-claude-sonnet-5
echo "START $(date -u +%FT%TZ)"
$PY $C/score_fork_corpus.py --corpus $CORPUS --view P_own --out $V/p_own.parquet --cache $V/judge-cache.P_own.$SLUG.jsonl --model $M --spend-cap-usd 12 --concurrency 4 --rpm 40 --batch-log $V/judge-batches.jsonl; echo "P_own exit $? $(date -u +%T)"
$PY $C/score_fork_corpus.py --corpus $CORPUS --view P_author --context 0 --out $V/p_author_c0.json --cache $V/judge-cache.P_author.$SLUG.jsonl --model $M --spend-cap-usd 3 --concurrency 4 --rpm 40 --batch-log $V/judge-batches.jsonl; echo "P_author c0 exit $? $(date -u +%T)"
$PY $C/score_fork_corpus.py --corpus $CORPUS --view P_author --context 3 --out $V/p_author_c3.json --cache $V/judge-cache.P_author_ctx.$SLUG.jsonl --model $M --spend-cap-usd 3 --concurrency 4 --rpm 40 --batch-log $V/judge-batches.jsonl; echo "P_author c3 exit $? $(date -u +%T)"
$PY $C/score_fork_corpus.py --corpus $CORPUS --view P_author --context 0 --author-unit author-day --out $V/p_author_c0_authorday.json --cache $V/judge-cache.P_author.$SLUG.jsonl --model $M --spend-cap-usd 3 --concurrency 4 --rpm 40 --batch-log $V/judge-batches.jsonl; echo "P_author author-day exit $? $(date -u +%T)"
$PY $C/score_o_composed.py --corpus $CORPUS --view O_diff --cumulative --out $V/o_diff_cumulative.json --cache $V/judge-cache.O_diff.$SLUG.jsonl --model $M --spend-cap-usd 5 --concurrency 4 --rpm 40 --quiet --batch-log $V/judge-batches.jsonl; echo "O_diff exit $? $(date -u +%T)"
$PY $C/score_o_composed.py --corpus $CORPUS --view O_whole --each-write --out $V/o_whole_eachwrite.json --cache $V/judge-cache.O_whole.$SLUG.jsonl --model $M --spend-cap-usd 3 --concurrency 4 --rpm 40 --quiet --batch-log $V/judge-batches.jsonl; echo "O_whole exit $? $(date -u +%T)"
$PY $C/score_fork_corpus.py --corpus $CORPUS --view P_ctx --out $V/p_ctx.parquet --cache $V/judge-cache.P_ctx.$SLUG.jsonl --model $M --spend-cap-usd 16 --concurrency 4 --rpm 40 --batch-log $V/judge-batches.jsonl; echo "P_ctx exit $? $(date -u +%T)"
echo "END $(date -u +%FT%TZ)"
