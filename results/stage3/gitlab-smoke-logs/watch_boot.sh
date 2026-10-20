#!/bin/bash
# Disk watchdog for the GitLab boot test: samples host free disk every 15 s;
# below $2 kB (default 1.5 GiB) it tears the s0boot project down (down -v) and exits.
LOG=$1
export DOCKER_CONFIG=/private/tmp/claude-501/-Users-aravind--claude-spares-spare-tzfTm1/360ae4ba-7b0e-4779-939a-8027617d2ac8/scratchpad/s0/dockercfg
while [ ! -f /private/tmp/claude-501/-Users-aravind--claude-spares-spare-tzfTm1/360ae4ba-7b0e-4779-939a-8027617d2ac8/scratchpad/s0/stop_watch_boot ]; do
  AV=$(df -k / | awk 'NR==2{print $4}')
  echo "$(date '+%T') avail_kB=$AV" >> $LOG
  if [ "$AV" -lt ${2:-1572864} ]; then
    echo "$(date '+%T') KILL free<1.5GiB: compose down -v" >> $LOG
    cd /Users/aravind/KruxAI/tais-project-selection/work/mole-fork-smoke/compose && docker compose -p s0boot -f lab.yaml down -v >> $LOG 2>&1
    exit 0
  fi
  sleep 15
done
