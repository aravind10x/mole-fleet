#!/bin/bash
# Supervisor for the S5.3 placeholder run, 2026-10-20: runs under `screen -dmS s5crun` so the
# screen daemon owns the tree. Starts a disk watchdog (floor 4 GiB: SIGTERM the runner and
# `compose down -v` the run's project), a credit poller (both caps every 5 min, numbers only;
# stop rule: balance delta over $4), then the runner wrapper; waits; retires the samplers.
set -u
S5C=/Users/aravind/KruxAI/tais-project-selection/work/stage3/s5c
LOGDIR=$S5C/run
WT=/Users/aravind/KruxAI/tais-project-selection/work/mole-fork-s5c
mkdir -p "$LOGDIR"
rm -f "$LOGDIR/stop_watchdog" "$LOGDIR/stop_credits"
START_BALANCE=$(bash /Users/aravind/KruxAI/tais-project-selection/work/stage3/gitlab-smoke-logs/credits.sh 2>/dev/null | grep -o 'balance [0-9.]*' | awk '{print $2}')
echo "$(date '+%F %T') supervisor: start balance $START_BALANCE; stop rule delta > 4" >> "$LOGDIR/supervisor.log"

# --- disk watchdog ---
(
  FLOOR_KB=4194304
  echo "$(date '+%F %T') watchdog start floor=${FLOOR_KB}kB" >> "$LOGDIR/watch.log"
  while [ ! -f "$LOGDIR/stop_watchdog" ]; do
    AV=$(df -k / | awk 'NR==2{print $4}')
    echo "$(date '+%F %T') avail_kB=$AV" >> "$LOGDIR/watch.log"
    if [ "$AV" -lt "$FLOOR_KB" ]; then
      echo "$(date '+%F %T') KILL free<4GiB: stopping runner + compose down -v" >> "$LOGDIR/watch.log"
      PID=$(cat "$LOGDIR/runner.pid" 2>/dev/null || true)
      if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then pkill -TERM -P "$PID" 2>/dev/null || true; kill -TERM "$PID" 2>/dev/null || true; fi
      sleep 20
      for PRJ in $(DOCKER_CONFIG=$LOGDIR/dockercfg docker ps --format '{{.Label "com.docker.compose.project"}}' | sort -u); do
        echo "$(date '+%F %T') teardown project=$PRJ" >> "$LOGDIR/watch.log"
        (cd "$WT" && DOCKER_CONFIG=$LOGDIR/dockercfg docker compose -p "$PRJ" -f "$WT/data/corpus/spike/lab.nogitlab.yaml" down -v) >> "$LOGDIR/watch.log" 2>&1 || true
      done
      exit 0
    fi
    sleep 20
  done
  echo "$(date '+%F %T') watchdog retired" >> "$LOGDIR/watch.log"
) &

# --- credit poller ---
(
  while [ ! -f "$LOGDIR/stop_credits" ]; do
    OUT=$(bash /Users/aravind/KruxAI/tais-project-selection/work/stage3/gitlab-smoke-logs/credits.sh 2>/dev/null)
    echo "$(date '+%F %T') $OUT" >> "$LOGDIR/credits.log"
    BAL=$(echo "$OUT" | grep -o 'balance [0-9.]*' | awk '{print $2}')
    if [ -n "${BAL:-}" ] && [ -n "${START_BALANCE:-}" ]; then
      DELTA=$(python3 -c "print(round($START_BALANCE - $BAL, 2))")
      echo "$(date '+%F %T') spend_so_far=$DELTA" >> "$LOGDIR/credits.log"
      if python3 -c "import sys; sys.exit(0 if $DELTA > 4 else 1)"; then
        echo "$(date '+%F %T') STOP RULE: delta $DELTA > 4; killing runner" >> "$LOGDIR/credits.log"
        PID=$(cat "$LOGDIR/runner.pid" 2>/dev/null || true)
        if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then pkill -TERM -P "$PID" 2>/dev/null || true; kill -TERM "$PID" 2>/dev/null || true; fi
      fi
    fi
    sleep 300
  done
  echo "$(date '+%F %T') credit poller retired" >> "$LOGDIR/credits.log"
) &

bash "$S5C/run_s5c_wrap.sh" &
RUNPID=$!
echo "$RUNPID" > "$LOGDIR/runner.pid"
echo "$(date '+%F %T') supervisor: runner pid $RUNPID" >> "$LOGDIR/supervisor.log"
wait "$RUNPID"
RC=$?
echo "$(date '+%F %T') supervisor: runner exited rc=$RC; retiring samplers" >> "$LOGDIR/supervisor.log"
bash /Users/aravind/KruxAI/tais-project-selection/work/stage3/gitlab-smoke-logs/credits.sh 2>/dev/null | sed "s/^/$(date '+%F %T') final /" >> "$LOGDIR/credits.log"
touch "$LOGDIR/stop_watchdog" "$LOGDIR/stop_credits"
echo "$(date '+%F %T') supervisor: done" >> "$LOGDIR/supervisor.log"
