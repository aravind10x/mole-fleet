#!/bin/bash
# Supervisor for one B4-R launch (brief 14; work/stage3/b4r/plan.md R0.4 / R2), run under screen. Usage:
#   supervisor_v3.sh <name: v3|v3b|v3c|reh> <corpus stem> <stop USD> <stop hours> <stop died per day>
# v2c's supervisor (work/stage3/prefix/run/supervisor_v2c.sh) with the main checkout as the working tree, a per-launch
# log folder, both keys' credit sampler every 5 min (numbers only), the hourly line, the disk watchdog, DIED-session
# counting (the turn cap is a normal end) and, at the day boundary, the informational readings (stage3_day1_stop.py and
# stage3_b4r.py day); the day-1 STOP of R0.4 is read by the session after the launch ends (each launch is one day, so
# the stop is "the next day is not launched"). At exit it records the runner code's diff against the launch commit.
set -u
NAME=$1; CORPUS=$2; STOP_USD=$3; STOP_HOURS=$4; STOP_ABORTED=$5
LOGDIR=/Users/aravind/KruxAI/tais-project-selection/work/stage3/prefix/run-v3/$NAME
mkdir -p "$LOGDIR"
WT=/Users/aravind/KruxAI/tais-project-selection/work/mole-fork-b4r   # the pinned worktree (plan A.9)
CREDITS=/Users/aravind/KruxAI/tais-project-selection/work/stage3/gitlab-smoke-logs/credits_both.sh
RUNLOG=$WT/data/corpus/spike/logs/$CORPUS.log
TRANS=$WT/data/corpus/spike/$CORPUS.transcripts.jsonl
LAUNCH_COMMIT=$(cd "$WT" && git rev-parse HEAD)
rm -f "$LOGDIR/stop_watchdog" "$LOGDIR/stop_credits" "$LOGDIR/stop_hourly" "$LOGDIR/stop_day1" "$LOGDIR/killed"
sample() { bash "$CREDITS" 2>/dev/null | tr '\n' ' '; }
START=$(sample)
K1_START=$(echo "$START" | grep -o 'key1 limit [0-9.]* limit_remaining [0-9.]*' | awk '{print $5}')
K2_START=$(echo "$START" | grep -o 'key2 account total_credits [0-9.]* total_usage [0-9.]* balance [0-9.]*' | awk '{print $8}')
T0=$(date +%s)
echo "$(date '+%F %T') supervisor: start key1 limit_remaining $K1_START key2 balance $K2_START; stops: spend>$STOP_USD, hours>$STOP_HOURS, died/day>$STOP_ABORTED, disk<4GiB, 402 on the last key" >> "$LOGDIR/supervisor.log"
echo "$(date '+%F %T') $START" >> "$LOGDIR/credits.log"
kill_runner() {
  PID=$(cat "$LOGDIR/runner.pid" 2>/dev/null || true); touch "$LOGDIR/killed"
  if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then pkill -TERM -P "$PID" 2>/dev/null || true; kill -TERM "$PID" 2>/dev/null || true; fi
}
spend_now() {
  OUT=$(sample); echo "$(date '+%F %T') $OUT" >> "$LOGDIR/credits.log"
  K1=$(echo "$OUT" | grep -o 'key1 limit [0-9.]* limit_remaining [0-9.]*' | awk '{print $5}')
  K2=$(echo "$OUT" | grep -o 'key2 account total_credits [0-9.]* total_usage [0-9.]* balance [0-9.]*' | awk '{print $8}')
  if [ -z "${K1:-}" ] || [ -z "${K2:-}" ]; then
    echo "$(date '+%F %T') credit sample FAILED (network?); spend not updated" >> "$LOGDIR/credits.log"
    echo "${LAST_D1:-0} ${LAST_D2:-0} ${LAST_TOT:-0}"; return
  fi
  python3 -c "
k1s,k2s,k1,k2=${K1_START:-0},${K2_START:-0},${K1},${K2}
d1=max(0.0,k1s-k1); d2=max(0.0,k2s-k2); print(round(d1,2),round(d2,2),round(d1+d2,2))"
}
( FLOOR_KB=4194304
  while [ ! -f "$LOGDIR/stop_watchdog" ]; do
    AV=$(df -k / | awk 'NR==2{print $4}'); echo "$(date '+%F %T') avail_kB=$AV" >> "$LOGDIR/watch.log"
    if [ "$AV" -lt "$FLOOR_KB" ]; then
      echo "$(date '+%F %T') KILL free<4GiB" >> "$LOGDIR/watch.log"; kill_runner; sleep 20
      for PRJ in $(DOCKER_CONFIG=/Users/aravind/KruxAI/tais-project-selection/work/stage3/lab-branch/run/dockercfg docker ps --format '{{.Label "com.docker.compose.project"}}' | grep '^itb-npc-' | sort -u); do
        (cd "$WT" && DOCKER_CONFIG=/Users/aravind/KruxAI/tais-project-selection/work/stage3/lab-branch/run/dockercfg docker compose -p "$PRJ" -f "$WT/data/corpus/spike/lab.nogitlab.yaml" down -v) >> "$LOGDIR/watch.log" 2>&1 || true
      done; exit 0
    fi; sleep 30
  done ) &
( while [ ! -f "$LOGDIR/stop_credits" ]; do
    sleep 300
    read D1 D2 TOT <<< "$(spend_now)"; LAST_D1=$D1; LAST_D2=$D2; LAST_TOT=$TOT
    echo "$(date '+%F %T') spend key1=$D1 key2=$D2 total=$TOT" >> "$LOGDIR/credits.log"
    if python3 -c "import sys; sys.exit(0 if ${TOT:-0} > $STOP_USD else 1)"; then
      echo "$(date '+%F %T') STOP RULE: spend $TOT > $STOP_USD; killing runner" >> "$LOGDIR/credits.log"; kill_runner; fi
    HRS=$(python3 -c "print(round(($(date +%s)-$T0)/3600,2))")
    if python3 -c "import sys; sys.exit(0 if $HRS > $STOP_HOURS else 1)"; then
      echo "$(date '+%F %T') STOP RULE: $HRS h > $STOP_HOURS; killing runner" >> "$LOGDIR/credits.log"; kill_runner; fi
    if grep -q 'no unexhausted fallback key left\|KeyExhaustedError' "$RUNLOG" 2>/dev/null; then
      echo "$(date '+%F %T') STOP RULE: 402 with no fallback key (runner stops itself)" >> "$LOGDIR/credits.log"; fi
  done ) &
( while [ ! -f "$LOGDIR/stop_hourly" ]; do
    sleep 3600
    STATS=$(python3 - "$TRANS" <<'PY'
import json,sys,collections
done=0; ab=collections.Counter(); cap=collections.Counter(); byday=collections.Counter(); reasons=collections.Counter()
try:
    for l in open(sys.argv[1]):
        try: r=json.loads(l)
        except Exception: continue
        done+=1; d=str(r.get("sim_ts"))[:10]; byday[d]+=1
        ar=r.get("aborted_reason")
        if ar=="max_turns": cap[d]+=1
        elif ar: ab[d]+=1; reasons[str(ar)[:60]]+=1
except FileNotFoundError: pass
print(f"sessions_done={done} per_day={dict(byday)} turn_capped_per_day={dict(cap)} aborted_per_day={dict(ab)} abort_reasons={dict(reasons)} max_aborted_day={max(ab.values()) if ab else 0}")
PY
)
    MAXAB=$(echo "$STATS" | grep -o 'max_aborted_day=[0-9]*' | cut -d= -f2)
    HRS=$(python3 -c "print(round(($(date +%s)-$T0)/3600,2))")
    echo "$(date '+%F %T') HOURLY elapsed_h=$HRS $STATS host_free_kB=$(df -k / | awk 'NR==2{print $4}') days_committed=$(grep -c 'day-boundary manifest committed' "$RUNLOG" 2>/dev/null)" >> "$LOGDIR/hourly.log"
    if [ "${MAXAB:-0}" -gt "$STOP_ABORTED" ]; then
      echo "$(date '+%F %T') STOP RULE: $MAXAB died sessions in a day > $STOP_ABORTED; killing runner" >> "$LOGDIR/hourly.log"; kill_runner; fi
  done ) &
AUDIT=$WT/data/corpus/spike/$CORPUS.jsonl
B4R=/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b4r.py
COUNT=/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/count.json
CHECK=/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_day1_stop.py
PYV=/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/.venv/bin/python
( SEEN=0
  while [ ! -f "$LOGDIR/stop_day1" ]; do
    sleep 120
    N=$(grep -c 'day-boundary manifest committed' "$RUNLOG" 2>/dev/null)
    if [ "${N:-0}" -gt "$SEEN" ]; then
      sleep 30
      for DAY in $(grep -o 'day-boundary manifest committed: day=[0-9-]*' "$RUNLOG" | cut -d= -f2 | tail -n +$((SEEN+1))); do
        "$PYV" -I "$CHECK" --corpus "$AUDIT" --day "$DAY" --out-json "$LOGDIR/day-reading-$DAY.json" > "$LOGDIR/day-reading-$DAY.txt" 2>&1
        "$PYV" -I "$B4R" day --audit "$AUDIT" --transcripts "$TRANS" --day "$DAY" --count "$COUNT" --out-json "$LOGDIR/cross-reading-$DAY.json" > "$LOGDIR/cross-reading-$DAY.txt" 2>&1
        echo "$(date '+%F %T') DAY READING $DAY (read by the session after the launch): $(head -1 "$LOGDIR/day-reading-$DAY.txt") | cross: $(tr -d '\n ' < "$LOGDIR/cross-reading-$DAY.txt" | cut -c1-300)" >> "$LOGDIR/hourly.log"
        (cd "$WT" && git rev-parse HEAD && git status --porcelain --untracked-files=no) > "$LOGDIR/code-state-$DAY.txt" 2>&1
        if [ "$(head -1 "$LOGDIR/code-state-$DAY.txt")" != "$LAUNCH_COMMIT" ] || [ "$(wc -l < "$LOGDIR/code-state-$DAY.txt")" -gt 1 ]; then
          echo "$(date '+%F %T') STOP RULE (A.9): the worktree left the approved commit or has tracked changes; killing runner" >> "$LOGDIR/hourly.log"; kill_runner; fi
      done
      SEEN=$N
    fi
  done ) &
echo "$(date '+%F %T') supervisor: $NAME $CORPUS launch commit $LAUNCH_COMMIT" >> "$LOGDIR/supervisor.log"
bash "/Users/aravind/KruxAI/tais-project-selection/work/stage3/prefix/run-v3/wrap_$NAME.sh" & RUNPID=$!
echo "$RUNPID" > "$LOGDIR/runner.pid"
echo "$(date '+%F %T') supervisor: runner pid $RUNPID" >> "$LOGDIR/supervisor.log"
wait "$RUNPID"; RC=$?
echo "$(date '+%F %T') supervisor: runner exited rc=$RC" >> "$LOGDIR/supervisor.log"
read D1 D2 TOT <<< "$(spend_now)"
echo "$(date '+%F %T') supervisor: final spend key1=$D1 key2=$D2 total=$TOT elapsed_h=$(python3 -c "print(round(($(date +%s)-$T0)/3600,2))")" >> "$LOGDIR/supervisor.log"
touch "$LOGDIR/stop_watchdog" "$LOGDIR/stop_credits" "$LOGDIR/stop_hourly" "$LOGDIR/stop_day1"
(cd "$WT" && git rev-parse HEAD && git status --porcelain --untracked-files=no) > "$LOGDIR/code-state-end.txt" 2>&1
echo "$(date '+%F %T') supervisor: worktree at exit: $(head -1 "$LOGDIR/code-state-end.txt") with $(($(wc -l < "$LOGDIR/code-state-end.txt") - 1)) tracked change(s) (launch commit $LAUNCH_COMMIT)" >> "$LOGDIR/supervisor.log"
echo "$(date '+%F %T') supervisor: done" >> "$LOGDIR/supervisor.log"
