#!/bin/bash
# Launch wrapper for the funded GitLab agentic smoke (s0_gitlab_agentic), 2026-10-20.
# Runs from the pinned worktree mole-fork-smoke2 @ b6a252f (L6). The exact command is
# pre-registered in work/stage3/gitlab-smoke-agentic-2026-10-20.md; this script is it.
# Key handling: OPENROUTER_API_KEY is overridden from .env key 2 (launch_line.py
# convention); no key value is ever printed. Credit caps were checked pre-launch (L3/L7).
set -euo pipefail
WT=/Users/aravind/KruxAI/tais-project-selection/work/mole-fork-smoke2
LOGDIR=/Users/aravind/KruxAI/tais-project-selection/work/stage3/gitlab-smoke-logs/run2
cd "$WT"
set -a; source .env; set +a
export OPENROUTER_API_KEY="$OPENROUTER_API_KEY_2"
export OPENROUTER_MODEL=moonshotai/kimi-k2.6
export GITLAB_PUMA_WORKERS=2 GITLAB_SIDEKIQ_CONCURRENCY=5
export DOCKER_CONFIG="$LOGDIR/dockercfg"   # credential-free, images are local
mkdir -p data/corpus/spike/logs
echo "$(date '+%F %T') wrapper: launching sim_runner (pid follows)" >> data/corpus/spike/logs/s0_gitlab_agentic.raw.log
exec ../mole-fork/.venv/bin/python scripts/sim_runner.py \
  --smoke --mode agentic --days 2 --sessions-per-day 2 --concurrency 5 \
  --personas alice.kim,deepa.a7,priya.a84,wei.n2,deepa.a1 \
  --seed 1 --no-insiders --out data/corpus/spike/s0_gitlab_agentic.jsonl \
  >> data/corpus/spike/logs/s0_gitlab_agentic.raw.log 2>&1
