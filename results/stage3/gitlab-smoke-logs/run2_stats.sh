#!/bin/bash
# Memory sampler for the funded GitLab smoke (run2), 2026-10-20: docker stats every
# 60 s (C2 under load); every 10th sample also `free -m` inside the gitlab container.
# Retire with: touch <LOGDIR>/stop_stats
set -u
LOGDIR=/Users/aravind/KruxAI/tais-project-selection/work/stage3/gitlab-smoke-logs/run2
LOG=$LOGDIR/stats.log
i=0
echo "$(date '+%F %T') stats sampler start" >> "$LOG"
while [ ! -f "$LOGDIR/stop_stats" ]; do
  i=$((i+1))
  echo "$(date '+%F %T') --- sample $i" >> "$LOG"
  docker stats --no-stream --format '{{.Name}} mem={{.MemUsage}} cpu={{.CPUPerc}}' >> "$LOG" 2>&1
  if [ $((i % 10)) -eq 0 ]; then
    GL=$(docker ps --format '{{.Names}}' | grep -m1 gitlab || true)
    if [ -n "$GL" ]; then
      echo "$(date '+%F %T') gitlab container free -m ($GL):" >> "$LOG"
      docker exec "$GL" free -m >> "$LOG" 2>&1 || true
    fi
  fi
  sleep 60
done
echo "$(date '+%F %T') stats sampler retired" >> "$LOG"
