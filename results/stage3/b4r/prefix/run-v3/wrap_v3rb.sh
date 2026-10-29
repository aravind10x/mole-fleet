#!/bin/bash
# Launch wrapper for prefix_rw_v3rb (brief 14, B4-R; work/stage3/b4r/plan.md R0.4 / R2, Amendments A and B). Runs from the pinned
# worktree work/mole-fork-b4r at the approved stage3 commit (A.9; never work/mole-fork-pilot); the launch commit is logged
# and the supervisor checks the worktree is clean at that commit at every boundary. The sim_runner line and the key/env
# exports are the ones scripts/launch_line.py generated from the assignment file (saved as launch-line-v3rb.txt), pasted verbatim
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
LOG=data/corpus/spike/logs/prefix_rw_v3rb.log
mkdir -p data/corpus/spike/logs
echo "$(date '+%F %T') wrapper: launching prefix_rw_v3rb from $F @ $(git rev-parse --short HEAD)" >> "$LOG"
.venv/bin/python scripts/sim_runner.py --smoke --personas alice.kim,ben.c91,carlos.v119,priya.a84,ben.l63,julian.x,deepa.a7,dan.r,zoe.w57,zoe.g92,sara.p29,ben.c106,zoe.c36,sam.w71,deepa.a1,frank.s,mei.w115,deepa.s107,kofi.o52,ines.m31,liam.h93,wei.o108,yuki.k38,liam.w65,deepa.t9,tom.k51,wei.n2,mei.s59,lena.n79,nina.t73,hannah.m,nina.n12,kofi.k110,maya.h96,elena.r61,tom.m82,raj.c89,carlos.o55,elena.r13,nina.l27,sam.l104,omar.s34,raj.k48,kara.p,raj.n88,kofi.p116,ben.c11,paul.k53,wei.i46,noah.g102 --branch-from data/corpus/spike/prefix_rw_v3r.jsonl --multi-day --no-insiders --task-bank results/stage3/bank-reweight/benign_task_bank_v2_class_v7b.yaml --days 1 --sessions-per-day 2 --concurrency 10 --mode agentic --seed 20282 --out data/corpus/spike/prefix_rw_v3rb.jsonl 2>&1 \
  | perl -pe 'BEGIN { $| = 1 } use POSIX qw(strftime); $_ = strftime("%F %T ", localtime) . $_' >> "$LOG"
exit "${PIPESTATUS[0]}"
