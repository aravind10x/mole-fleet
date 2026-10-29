#!/bin/bash
# Replacement for supervisor_v3.sh's credit/hours loop for the rehearsal (2026-10-29, dated in plan.md's record):
# identical spend rule (> $6 combined, key 1 limit_remaining delta + key 2 balance delta from the supervisor's start
# sample), the 402 check, and the wall-clock stop re-sized from 2 h to 4 h on the observed throughput (one session in
# flight at a time, about 12 min each, 10 sessions) before it was reached. Numbers only; never a key.
set -u
LOGDIR=/Users/aravind/KruxAI/tais-project-selection/work/stage3/prefix/run-v3/reh
CREDITS=/Users/aravind/KruxAI/tais-project-selection/work/stage3/gitlab-smoke-logs/credits_both.sh
RUNLOG=/Users/aravind/KruxAI/tais-project-selection/work/mole-fork-b4r/data/corpus/spike/logs/rehearsal_rw_v3.log
K1_START=64.345793968; K2_START=189.7115; T0=$(date -j -f "%Y-%m-%d %H:%M:%S" "2026-10-29 12:06:12" +%s); STOP_USD=6; STOP_HOURS=4
echo "$(date '+%F %T') credits_watch2: replaces the supervisor's credit loop; stops spend>$STOP_USD, hours>$STOP_HOURS (from 12:06:12)" >> "$LOGDIR/credits.log"
while [ ! -f "$LOGDIR/stop_watchdog" ]; do
  sleep 300
  OUT=$(bash "$CREDITS" 2>/dev/null | tr '\n' ' '); echo "$(date '+%F %T') $OUT" >> "$LOGDIR/credits.log"
  K1=$(echo "$OUT" | grep -o 'key1 limit [0-9.]* limit_remaining [0-9.]*' | awk '{print $5}')
  K2=$(echo "$OUT" | grep -o 'key2 account total_credits [0-9.]* total_usage [0-9.]* balance [0-9.]*' | awk '{print $8}')
  if [ -n "${K1:-}" ] && [ -n "${K2:-}" ]; then
    TOT=$(python3 -c "print(round(max(0.0,$K1_START-$K1)+max(0.0,$K2_START-$K2),2))")
    echo "$(date '+%F %T') spend total=$TOT (watch2)" >> "$LOGDIR/credits.log"
    if python3 -c "import sys; sys.exit(0 if $TOT > $STOP_USD else 1)"; then
      echo "$(date '+%F %T') STOP RULE: spend $TOT > $STOP_USD; killing runner" >> "$LOGDIR/credits.log"; PID=$(cat "$LOGDIR/runner.pid"); pkill -TERM -P "$PID"; kill -TERM "$PID"; touch "$LOGDIR/killed"; fi
  fi
  HRS=$(python3 -c "print(round(($(date +%s)-$T0)/3600,2))")
  if python3 -c "import sys; sys.exit(0 if $HRS > $STOP_HOURS else 1)"; then
    echo "$(date '+%F %T') STOP RULE: $HRS h > $STOP_HOURS; killing runner" >> "$LOGDIR/credits.log"; PID=$(cat "$LOGDIR/runner.pid"); pkill -TERM -P "$PID"; kill -TERM "$PID"; touch "$LOGDIR/killed"; fi
  if grep -q 'no unexhausted fallback key left\|KeyExhaustedError' "$RUNLOG" 2>/dev/null; then
    echo "$(date '+%F %T') STOP RULE: 402 with no fallback key (runner stops itself)" >> "$LOGDIR/credits.log"; fi
done
