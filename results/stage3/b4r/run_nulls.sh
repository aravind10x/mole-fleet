#!/bin/bash
# Brief 14 R5: the honest nulls in Amendment A.15's order (P_own dropped before any call: 11.12(d) truncation).
# Each null re-checks the $240 line before its first batch and after it (stage3_b4r_nulls.py null).
set -u
cd /Users/aravind/KruxAI/tais-project-selection/work/mole-fork
set -a; source .env; set +a
C=$PWD/data/corpus/spike/prefix_rw_v3rc.jsonl
OUT=/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/nulls
EST=/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/nulls-estimate.json
SPENT=109.34
LOG=/Users/aravind/KruxAI/tais-project-selection/work/stage3/b4r/nulls-run.log
ORDER="sonnet:P_author sonnet:O_diff sonnet:O_ws sonnet:O_ws_all sonnet:P_author_doc_iso sonnet:P_author_doc_live opus48:P_author_doc_iso opus48:P_author_doc_live opus48:O_diff opus48:O_ws opus48:P_author opus48:O_ws_all"
LIST=($ORDER)
for i in "${!LIST[@]}"; do
  J=${LIST[$i]%%:*}; V=${LIST[$i]#*:}
  if [ -f "$OUT/$V.$J.json" ]; then echo "$(date '+%F %T') skip $J $V (done)" >> "$LOG"; continue; fi
  REM=$(python3 -c "
import json; e=json.load(open('$EST')); L='''${LIST[*]:$((i+1))}'''.split()
print(round(sum(e['views'][x.split(':')[1]][x.split(':')[0]]['est_cost_usd'] for x in L),4))")
  echo "$(date '+%F %T') start $J $V (remaining planned after this \$$REM)" >> "$LOG"
  .venv/bin/python -I ../checks/stage3_b4r_nulls.py null --corpus "$C" --version v7 --view "$V" --judge "$J" --out-dir "$OUT" \
     --spent-openrouter $SPENT --remaining-usd "$REM" --concurrency 4 --rpm 40 >> "$LOG" 2>&1
  RC=$?
  echo "$(date '+%F %T') end $J $V rc=$RC" >> "$LOG"
  if [ $RC -eq 2 ]; then echo "$(date '+%F %T') STOP: the \$240 line" >> "$LOG"; break; fi
done
echo "$(date '+%F %T') nulls run done" >> "$LOG"
