"""Counts v2-bank variants per team that mention a merge request (S0 account choice).

Run: work/mole-fork/.venv/bin/python -I work/stage3/gitlab-smoke-logs/bank_mr_counts.py
Regexes are approximate (keyword match on the serialised variant text).
"""
import json
import re
from pathlib import Path

import yaml

BANK = Path(__file__).resolve().parents[2] / "mole-fork/bootstrap/benign_task_bank_v2.yaml"
bank = yaml.safe_load(BANK.read_text())
for team, sec in bank.items():
    variants = sec.get("variants", []) if isinstance(sec, dict) else []
    texts = [json.dumps(v) for v in variants]
    gitlabish = sum(1 for t in texts if re.search(r"gitlab|merge request|\bMR\b|repo|branch|commit", t, re.I))
    mr = sum(1 for t in texts if re.search(r"merge request|\bMR\b", t, re.I))
    print(f"{team} variants={len(variants)} gitlab_keyword={gitlabish} merge_request={mr}")
