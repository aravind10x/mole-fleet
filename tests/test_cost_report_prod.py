"""scripts/cost_report.py buckets every production deploy (incl. prod-eu) as deploy.prod."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import cost_report  # noqa: E402


def test_audit_summary_counts_prod_eu_as_prod(tmp_path):
    rows = [{"task_id": "t1", "service": "model_registry", "action": "deploy",
             "args": {"environment": env}, "exit_code": 0}
            for env in ("prod", "Production", "prod-eu", "prod_us", "staging-eu", "")]
    audit = tmp_path / "a.jsonl"
    audit.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    gate = cost_report.audit_summary(audit, [{"task_id": "t1"}])["gate_events"]
    assert gate == {"deploy.prod": 4, "deploy.staging-eu": 1, "deploy.unknown": 1}
