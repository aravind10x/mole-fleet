#!/bin/bash
# Credit poller for the funded GitLab smoke (run2), 2026-10-20: both caps every 10 min
# (L3/L7 stop rule: kill if the account-balance delta exceeds $10). Numbers only.
# Retire with: touch <LOGDIR>/stop_credits
set -u
LOGDIR=/Users/aravind/KruxAI/tais-project-selection/work/stage3/gitlab-smoke-logs/run2
LOG=$LOGDIR/credits.log
START_BALANCE=98.7943
echo "$(date '+%F %T') credit poller start; start balance $START_BALANCE; stop rule delta > 10" >> "$LOG"
while [ ! -f "$LOGDIR/stop_credits" ]; do
  OUT=$(bash /Users/aravind/KruxAI/tais-project-selection/work/stage3/gitlab-smoke-logs/credits.sh 2>/dev/null)
  echo "$(date '+%F %T') $OUT" >> "$LOG"
  BAL=$(echo "$OUT" | grep -o 'balance [0-9.]*' | awk '{print $2}')
  if [ -n "${BAL:-}" ]; then
    DELTA=$(python3 -c "print(round($START_BALANCE - $BAL, 2))")
    echo "$(date '+%F %T') spend_so_far=$DELTA" >> "$LOG"
  fi
  sleep 600
done
echo "$(date '+%F %T') credit poller retired" >> "$LOG"
