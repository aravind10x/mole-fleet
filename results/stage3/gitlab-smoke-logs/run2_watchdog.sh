#!/bin/bash
# Disk watchdog for the funded GitLab smoke (run2), 2026-10-20.
# Samples host free disk every 20 s; below 4 GiB (4194304 kB) it SIGTERMs the runner
# and tears the run's compose project down (down -v), the first sitting's watch_boot.sh
# pattern with a floor raised for this run's larger budget. Retire with:
#   touch <LOGDIR>/stop_watchdog
set -u
LOGDIR=/Users/aravind/KruxAI/tais-project-selection/work/stage3/gitlab-smoke-logs/run2
LOG=$LOGDIR/watch.log
WT=/Users/aravind/KruxAI/tais-project-selection/work/mole-fork-smoke2
FLOOR_KB=4194304
echo "$(date '+%F %T') watchdog start floor=${FLOOR_KB}kB" >> "$LOG"
while [ ! -f "$LOGDIR/stop_watchdog" ]; do
  AV=$(df -k / | awk 'NR==2{print $4}')
  echo "$(date '+%F %T') avail_kB=$AV" >> "$LOG"
  if [ "$AV" -lt "$FLOOR_KB" ]; then
    echo "$(date '+%F %T') KILL free<4GiB: stopping runner + compose down -v" >> "$LOG"
    PID=$(cat "$LOGDIR/runner.pid" 2>/dev/null || true)
    if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then
      pkill -TERM -P "$PID" 2>/dev/null || true
      kill -TERM "$PID" 2>/dev/null || true
    fi
    sleep 20
    for P in $(docker ps --format '{{.Label "com.docker.compose.project"}}' | sort -u); do
      CFG=$(docker ps --format '{{.Label "com.docker.compose.project"}} {{.Label "com.docker.compose.project.config_files"}}' | awk -v p="$P" '$1==p{print $2; exit}')
      echo "$(date '+%F %T') teardown project=$P cfg=$CFG" >> "$LOG"
      if [ -n "$CFG" ]; then
        (cd "$WT" && docker compose -p "$P" -f "$CFG" down -v) >> "$LOG" 2>&1
      else
        docker ps -q --filter "label=com.docker.compose.project=$P" | xargs docker rm -f >> "$LOG" 2>&1 || true
      fi
    done
    echo "$(date '+%F %T') watchdog teardown done" >> "$LOG"
    exit 0
  fi
  sleep 20
done
echo "$(date '+%F %T') watchdog retired by stop file" >> "$LOG"
