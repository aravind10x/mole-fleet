#!/bin/bash
# Rules-mode re-rehearsal of the pilot line WITH the redundancy flag (design 11.12(g); brief 07h B7; L15 rule 1), 2026-10-24.
# The sim_runner line is the one scripts/launch_line.py generated from coalitions_f4_pilot_rehearsal.yaml
# --branch-id P --start-date 2026-04-09 (identical flags to the agentic line except --mode rules and the
# _rules output name), pasted verbatim (saved as launch-line-rules-07h.txt). Rules mode makes no LLM call.
# Expected plan written first (launch-line-rules-07h.txt): 191 sessions; sixteen scenario sessions (eight role-days x two).
# Runs from the main checkout work/mole-fork (no agentic run imports from it: pgrep empty).
set -euo pipefail
F=/Users/aravind/KruxAI/tais-project-selection/work/mole-fork
cd "$F"
set -a; source "$F/.env"; set +a
export OPENROUTER_API_KEY="${OPENROUTER_API_KEY}" && export OPENROUTER_API_KEY_2="${OPENROUTER_API_KEY_2}"
export LAB_COMPOSE="$PWD/data/corpus/spike/lab.nogitlab.yaml"
export NPC_AGENTIC_ENVS="org,owncloud,email,rocketchat,plane,model_registry,eval_server,secrets_store"
export LLM_RETRY_MAX_ATTEMPTS="40"
export DOCKER_CONFIG=/Users/aravind/KruxAI/tais-project-selection/work/stage3/lab-branch/run/dockercfg
OPENROUTER_MODEL=moonshotai/kimi-k2.6 \
  .venv/bin/python scripts/sim_runner.py --smoke --personas nina.t73,wei.o108,ben.c11,zoe.c36,deepa.a1,wei.n2,julian.x,liam.h93,deepa.a7,priya.a84,alice.kim,sam.w71,dan.r,zoe.w57,noah.g102,wei.i46,paul.k53,tom.k51,kofi.o52,yuki.k38 --branch-from data/corpus/spike/prefix_rw_v2c.jsonl --multi-day --objective-carrier benign --task-bank results/stage3/bank-reweight/benign_task_bank_v2_class_v6.yaml --redundant-role-sessions --days 5 --sessions-per-day 2 --concurrency 8 --mode rules --coalitions /Users/aravind/KruxAI/tais-project-selection/work/stage3/pilot/coalitions_f4_pilot_rehearsal.yaml --branch-id P --seed 20265 --personas-dir ../stage3/pilot/personas --out data/corpus/spike/f4_pilot_rehearsal_07h_rules.jsonl
