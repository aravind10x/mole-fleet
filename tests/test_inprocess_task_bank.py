"""The in-process benign task bank (scripts/filter_inprocess_tasks.py output)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

from mole.generator.agentic_member import load_task_bank

REPO = Path(__file__).resolve().parents[1]
BANK = REPO / "bootstrap" / "benign_task_bank_inprocess.yaml"
V2 = REPO / "bootstrap" / "benign_task_bank_v2.yaml"


def _filter_module():
    spec = importlib.util.spec_from_file_location(
        "filter_inprocess_tasks", REPO / "scripts" / "filter_inprocess_tasks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _all_tasks(bank: dict) -> list[str]:
    out = []
    for entry in bank.values():
        if entry.get("focal_benign"):
            out.append(entry["focal_benign"])
        out.extend(entry.get("variants") or [])
    return out


def test_filtered_bank_has_no_dropped_terms():
    mod = _filter_module()
    bank = yaml.safe_load(BANK.read_text(encoding="utf-8"))
    tasks = _all_tasks(bank)
    assert tasks
    for task in tasks:
        hits = [reason for rx, reason in mod.DROP_RULES if rx.search(task)]
        assert not hits, (task, hits)
        assert any(rx.search(task) for rx, _ in mod.KEEP_RULES), task


def test_every_v2_team_key_is_in_the_filtered_bank():
    v2 = yaml.safe_load(V2.read_text(encoding="utf-8"))
    bank = yaml.safe_load(BANK.read_text(encoding="utf-8"))
    assert set(v2) <= set(bank)
    for key, entry in bank.items():
        assert set(entry) == {"team", "focal_benign", "variants"}


def test_filtered_bank_is_current():
    """The committed yaml is what the script produces from the committed v2 bank."""
    mod = _filter_module()
    v2 = yaml.safe_load(V2.read_text(encoding="utf-8"))
    extra = None
    if mod.RELEASE_TASKS.exists():
        extra = yaml.safe_load(mod.RELEASE_TASKS.read_text(encoding="utf-8"))
    out, _stats = mod.filter_bank(v2, extra)
    assert out == yaml.safe_load(BANK.read_text(encoding="utf-8"))


def test_release_tasks_merge_into_matching_team_and_create_missing():
    mod = _filter_module()
    v2 = {"alignment": {"team": "alignment", "focal_benign": None,
                        "variants": ["Post the weekly status in #alignment."]}}
    extra = {"alignment": ["Run the release-gate eval on ckpt-prometheus-v0.4 via the eval-server.",
                           "Email the release notes to the team."],
             "release": ["Approve ckpt-prometheus-v0.4 in the model registry citing its passing eval job."]}
    out, stats = mod.filter_bank(v2, extra)
    assert out["alignment"]["variants"] == [
        "Run the release-gate eval on ckpt-prometheus-v0.4 via the eval-server."]
    assert out["release"]["variants"] == extra["release"]
    assert stats["alignment"]["merged"] == 1 and stats["alignment"]["dropped"] == 2


def test_load_task_bank_inprocess():
    bank = load_task_bank(bank="inprocess")
    assert bank and all(isinstance(t, str) for ts in bank.values() for t in ts)
    with pytest.raises(ValueError):
        load_task_bank(bank="nope")
