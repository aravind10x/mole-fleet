#!/bin/bash
# Launch wrapper for the S5.3 placeholder run (s5c_objective_benign_1), 2026-10-20.
# Runs from the pinned worktree work/mole-fork-s5c @ fc443fb (L6). The args line is the one
# scripts/launch_line.py generated from ../stage3/s5c/coalitions_f4_placeholder.yaml (L15
# rule 2) and rehearsed in rules mode (17 PASS, 1 SKIP, 0 FAIL); it is pasted verbatim.
# Key handling: OPENROUTER_API_KEY is overridden from .env key 2 (the launch_line.py
# convention); no key value is ever printed. Substrate (i-): LAB_COMPOSE is the no-GitLab
# compose file; NPC_AGENTIC_ENVS is the T5 set. Output lines are timestamped so the
# session-phase wall-clock (sessions per hour) can be read from the log.
set -euo pipefail
WT=/Users/aravind/KruxAI/tais-project-selection/work/mole-fork-s5c
LOGDIR=/Users/aravind/KruxAI/tais-project-selection/work/stage3/s5c/run
cd "$WT"
set -a; source .env; set +a
export OPENROUTER_API_KEY="$OPENROUTER_API_KEY_2"
export OPENROUTER_MODEL=moonshotai/kimi-k2.6
export LAB_COMPOSE="$WT/data/corpus/spike/lab.nogitlab.yaml"
export NPC_AGENTIC_ENVS=org,owncloud,email,rocketchat,plane,model_registry,eval_server,secrets_store
export DOCKER_CONFIG="$LOGDIR/dockercfg"   # credential-free, images are local
export PYTHONUNBUFFERED=1
mkdir -p data/corpus/spike/logs
echo "$(date '+%F %T') wrapper: launching sim_runner from $WT @ $(git rev-parse --short HEAD)" >> data/corpus/spike/logs/s5c_objective_benign_1.log
../mole-fork/.venv/bin/python scripts/sim_runner.py --smoke --personas deepa.a1,wei.n2,priya.a84 --multi-day --objective-carrier benign --days 1 --sessions-per-day 2 --concurrency 3 --mode agentic --coalitions ../stage3/s5c/coalitions_f4_placeholder.yaml --branch-id P --seed 20261 --personas-dir ../stage3/s5c/personas --out data/corpus/spike/s5c_objective_benign_1.jsonl 2>&1 \
  | perl -pe 'use POSIX qw(strftime); $_ = strftime("%F %T ", localtime) . $_' >> data/corpus/spike/logs/s5c_objective_benign_1.log
exit "${PIPESTATUS[0]}"
