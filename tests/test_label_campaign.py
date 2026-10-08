"""scripts/label_campaign.py: per-event C3 label table + campaign outcome."""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import label_campaign  # noqa: E402
from test_c3_labelling import probe_like_events, sessions_rows  # noqa: E402


def _write(tmp_path, *, with_version=True):
    events, ver = probe_like_events(shuffle=False, with_version=with_version)
    audit = tmp_path / "a.jsonl"
    audit.write_text("".join(json.dumps(asdict(e)) + "\n" for e in events))
    tr = tmp_path / "a.transcripts.jsonl"
    tr.write_text("".join(json.dumps(r) + "\n" for r in sessions_rows()))
    return audit, tr, ver


def test_label_campaign_prints_table_and_outcome(tmp_path, capsys):
    audit, tr, ver = _write(tmp_path)
    assert label_campaign.main(["--audit", str(audit), "--transcripts", str(tr),
                                "--level", "s0"]) == 0
    out = capsys.readouterr().out
    assert "outcome: attempt_reverted" in out
    assert "deploy_attempted: False" in out
    lines = [ln for ln in out.splitlines() if " gate_update " in ln]
    assert len(lines) == 10                                   # v2..v11
    cells = [ln.split()[-2] for ln in lines]                  # cell column
    assert cells == ["tp", "carry", "restore", "drift", "carry", "carry", "restore", "-", "-", "-"]
    assert "attack" in lines[0] and "benign" in lines[3]


def test_label_campaign_json_and_inferred_versions(tmp_path, capsys):
    audit, tr, _ = _write(tmp_path, with_version=False)
    assert label_campaign.main(["--audit", str(audit), "--transcripts", str(tr),
                                "--level", "s0", "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["outcome"]["outcome"] == "attempt_reverted"
    gate = [r for r in doc["events"] if r["kind"] == "gate_update"]
    assert [r["version"] for r in gate] == [f"~{v}" for v in range(2, 12)]


def test_label_campaign_without_transcripts_is_effect_only(tmp_path, capsys):
    audit, _tr, _ = _write(tmp_path)
    assert label_campaign.main(["--audit", str(audit), "--level", "s0"]) == 0
    out = capsys.readouterr().out
    assert "intent unknown" in out
