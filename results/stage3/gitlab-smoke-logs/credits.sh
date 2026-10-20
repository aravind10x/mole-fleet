#!/bin/bash
# Prints key-2 limit_remaining and account balance numbers only (never the key).
set -a; source /Users/aravind/KruxAI/tais-project-selection/work/mole-fork/.env; set +a
K="$OPENROUTER_API_KEY_2"
curl -s https://openrouter.ai/api/v1/auth/key -H "Authorization: Bearer $K" | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print('key2 limit_remaining', d.get('limit_remaining'), 'usage', d.get('usage'), 'usage_daily', d.get('usage_daily'))"
curl -s https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $K" | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print('account total_credits', d['total_credits'], 'total_usage', round(d['total_usage'],4), 'balance', round(d['total_credits']-d['total_usage'],4))"
