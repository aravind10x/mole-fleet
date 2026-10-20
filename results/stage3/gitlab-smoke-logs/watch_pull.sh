#!/bin/bash
# Samples free host disk every 20 s while the pull runs; kills the pull if free < 3 GB.
PID=$1; LOG=$2
while kill -0 $PID 2>/dev/null; do
  AV=$(df -k / | awk 'NR==2{print $4}')
  echo "$(date '+%T') avail_kB=$AV" >> $LOG
  if [ "$AV" -lt 3145728 ]; then echo "$(date '+%T') KILL free<3GB" >> $LOG; kill $PID; fi
  sleep 20
done
echo "$(date '+%T') pull process exited" >> $LOG
