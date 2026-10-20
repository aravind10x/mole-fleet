#!/bin/bash
# Supervisor for the funded GitLab smoke (run2), 2026-10-20, attempt 3.
# Attempt 2 died when the tool shell killed its backgrounded children on exit;
# this supervisor runs under `screen -dmS s0run` so the screen daemon owns the
# whole tree. Starts the watchdog, stats and credit samplers, then the runner
# (run2_wrap.sh, which execs sim_runner), waits for the runner, then retires
# the samplers via their stop files.
set -u
LOGS=/Users/aravind/KruxAI/tais-project-selection/work/stage3/gitlab-smoke-logs
LOGDIR=$LOGS/run2
rm -f "$LOGDIR/stop_watchdog" "$LOGDIR/stop_stats" "$LOGDIR/stop_credits"
bash "$LOGS/run2_watchdog.sh" &
bash "$LOGS/run2_stats.sh" &
bash "$LOGS/run2_credits.sh" &
bash "$LOGS/run2_wrap.sh" &
RUNPID=$!
echo "$RUNPID" > "$LOGDIR/runner.pid"
echo "$(date '+%F %T') supervisor: runner pid $RUNPID (attempt 3, under screen)" >> "$LOGDIR/supervisor.log"
wait "$RUNPID"
RC=$?
echo "$(date '+%F %T') supervisor: runner exited rc=$RC; retiring samplers" >> "$LOGDIR/supervisor.log"
touch "$LOGDIR/stop_watchdog" "$LOGDIR/stop_stats" "$LOGDIR/stop_credits"
echo "$(date '+%F %T') supervisor: done" >> "$LOGDIR/supervisor.log"
