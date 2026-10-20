#!/bin/bash
# Measures what the day-boundary snapshot would write for the GitLab service,
# without writing the tarball: pause, commit-layer size, tar czf of each volume
# streamed to wc -c, unpause. Same busybox tar czf as mole/sandbox/snapshot.py.
export DOCKER_CONFIG=/private/tmp/claude-501/-Users-aravind--claude-spares-spare-tzfTm1/360ae4ba-7b0e-4779-939a-8027617d2ac8/scratchpad/s0/dockercfg
C=s0boot-gitlab-1
echo "start $(date +%T)"
echo "writable layer (docker ps -s): $(docker ps -s --filter name=$C --format '{{.Size}}')"
docker pause $C
for V in s0boot_gitlab-config s0boot_gitlab-data; do
  T=$(date +%s)
  B=$(docker run --rm -v $V:/source:ro busybox sh -c 'cd /source && tar czf - . | wc -c')
  echo "$V tar.gz bytes=$B seconds=$(( $(date +%s) - T ))"
done
docker unpause $C
echo "end $(date +%T)"
