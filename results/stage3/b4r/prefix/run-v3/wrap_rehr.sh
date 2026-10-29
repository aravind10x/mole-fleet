#!/bin/bash
# Launch wrapper for rehearsal_rw_v3r (brief 14, B4-R; work/stage3/b4r/plan.md R0.4 / R2, Amendments A and B). Runs from the pinned
# worktree work/mole-fork-b4r at the approved stage3 commit (A.9; never work/mole-fork-pilot); the launch commit is logged
# and the supervisor checks the worktree is clean at that commit at every boundary. The sim_runner line and the key/env
# exports are the ones scripts/launch_line.py generated from the assignment file (saved as rehearsal-v3/launch-line-lab-v3r.txt), pasted verbatim
# (L15 rule 2; diff-checked). Key 1 active, key 2 the declared fallback (Amendment B). Differences from the generated text:
# .env sourced from the main checkout by absolute path, DOCKER_CONFIG the credential-free config with the compose plugin,
# unbuffered timestamped log. No key value is ever printed.
set -euo pipefail
F=/Users/aravind/KruxAI/tais-project-selection/work/mole-fork-b4r   # the pinned worktree (plan A.9)
cd "$F"
set -a; source /Users/aravind/KruxAI/tais-project-selection/work/mole-fork/.env; set +a
export OPENROUTER_API_KEY="${OPENROUTER_API_KEY}" && export OPENROUTER_API_KEY_2="${OPENROUTER_API_KEY_2}"   # key 1 active, key 2 the declared fallback (client rotation on 402)
export LAB_COMPOSE="$PWD/data/corpus/spike/lab.nogitlab.yaml"
export NPC_AGENTIC_ENVS="org,owncloud,email,rocketchat,plane,model_registry,eval_server,secrets_store"
export LLM_RETRY_MAX_ATTEMPTS="40"
export OPENROUTER_MODEL=moonshotai/kimi-k2.6
export DOCKER_CONFIG=/Users/aravind/KruxAI/tais-project-selection/work/stage3/lab-branch/run/dockercfg
export PYTHONUNBUFFERED=1
LOG=data/corpus/spike/logs/rehearsal_rw_v3r.log
mkdir -p data/corpus/spike/logs
echo "$(date '+%F %T') wrapper: launching rehearsal_rw_v3r from $F @ $(git rev-parse --short HEAD)" >> "$LOG"
.venv/bin/python scripts/sim_runner.py --smoke --personas alice.kim,zoe.c36,ben.c11,kofi.o52,wei.n2 --multi-day --no-insiders --task-bank results/stage3/bank-reweight/benign_task_bank_v7b_rehearsal_updates.yaml --class-documents --class-documents-version v7 --days 1 --sessions-per-day 2 --concurrency 5 --mode agentic --seed 20285 --out data/corpus/spike/rehearsal_rw_v3r.jsonl 2>&1 \
  | perl -pe 'BEGIN { $| = 1 } use POSIX qw(strftime); $_ = strftime("%F %T ", localtime) . $_' >> "$LOG"
exit "${PIPESTATUS[0]}"
