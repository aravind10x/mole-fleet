"""Tests for stage3_metadata_leak_released.py on synthetic frames (no released data needed).

    cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_metadata_leak_released.py

They exercise the feature assembly (the mirror of `metadata_features`' no-transcripts branch)
and the label assembly; the frozen classifier is only run end to end on a separable and an
inseparable synthetic corpus written in the released layout. Accounts and tasks are neutral
placeholders.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_metadata_leak_released as s6  # noqa: E402


def ev(account: str, ts: str, task: str | None, exit_code: int = 0) -> dict:
    return {"ts": ts, "account": account, "exit_code": exit_code, "task_id": task}


def labels_frame(rows: list[tuple[str, str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["account", "date", "scenario", "outcome"]).assign(
        confidence=1.0, judge="placeholder")


# ----------------------------------------------------------------------------------
# Feature assembly
# ----------------------------------------------------------------------------------

def test_features_mirror_metadata_features():
    df = pd.DataFrame([
        ev("u1", "2026-04-06T09:30:00Z", "t1"),
        ev("u1", "2026-04-06T08:15:30Z", "t1", exit_code=1),   # failed: counts, not first
        ev("u1", "2026-04-06T10:00:00Z", "t2"),
        ev("u1", "2026-04-06T11:00:00Z", None),                # None is one more task value
        ev("u1", "2026-04-07T07:00:00Z", "t3"),
        ev("u2", "2026-04-06T06:00:00Z", "t4", exit_code=1),   # no success: not active
    ])
    f = s6.account_day_features(df).set_index(["account", "date"])
    assert list(f.index) == [("u1", "2026-04-06"), ("u1", "2026-04-07")]
    r = f.loc[("u1", "2026-04-06")]
    assert r["n_events"] == 4 and r["n_sessions"] == 3
    assert r["events_per_session"] == pytest.approx(4 / 3)
    assert r["first_action_min"] == pytest.approx(9 * 60 + 30)
    assert f.loc[("u1", "2026-04-07"), "events_per_session"] == 1.0


def test_feature_set_two_feature_fallback_and_turn_field_refused():
    assert s6.feature_set(["ts", "account", "exit_code", "task_id"]) == [
        "events_per_session", "first_action_min"]
    with pytest.raises(SystemExit):
        s6.feature_set(["ts", "account", "turn_count"])


# ----------------------------------------------------------------------------------
# Label assembly
# ----------------------------------------------------------------------------------

@pytest.fixture()
def feats():
    keys = [("a", "2026-04-06"), ("a", "2026-04-07"), ("b", "2026-04-06"),
            ("c", "2026-04-06"), ("d", "2026-04-06"), ("e", "2026-04-06"),
            ("h", "2026-04-06"), ("h", "2026-04-07")]
    return pd.DataFrame(keys, columns=["account", "date"]).assign(
        events_per_session=1.0, first_action_min=1.0)


@pytest.fixture()
def labels():
    # Scenario names are placeholders, except the one f1_exact must recognise.
    return labels_frame([
        ("a", "2026-04-06", s6.F1_THREATS[0], "executed"),
        ("b", "2026-04-06", "placeholder_b", "attempted"),
        ("c", "2026-04-06", "placeholder_c", "no_attempt"),
        ("d", "2026-04-06T00:00:00", "placeholder_d", "refused"),    # date truncated to 10
        ("e", "2026-04-06", "placeholder_e", "executed"),             # not an f1 scenario
        ("z", "2026-04-06", "placeholder_z", "executed"),             # not active
    ])


def classes(feats, labels, rule):
    cls, info = s6.label_account_days(feats, labels, s6.LABEL_RULES[rule])
    return dict(zip(zip(feats["account"], feats["date"]), cls)), info


def test_primary_rule(feats, labels):
    c, info = classes(feats, labels, "primary")
    assert c[("a", "2026-04-06")] == 1 and c[("b", "2026-04-06")] == 1
    assert c[("e", "2026-04-06")] == 1
    assert c[("a", "2026-04-07")] == -1          # labelled account, other day: excluded
    assert c[("c", "2026-04-06")] == -1 and c[("d", "2026-04-06")] == -1
    assert c[("h", "2026-04-06")] == 0 and c[("h", "2026-04-07")] == 0
    assert info["positive_keys_not_active"] == 1
    assert (info["n_attack"], info["n_honest"], info["n_excluded"]) == (3, 2, 3)


def test_sensitivity_rules(feats, labels):
    c, _ = classes(feats, labels, "f1_exact")
    assert [k for k, v in c.items() if v == 1] == [("a", "2026-04-06")]
    c, _ = classes(feats, labels, "any_label")
    assert {k for k, v in c.items() if v == 1} == {("a", "2026-04-06"), ("b", "2026-04-06"),
                                                   ("c", "2026-04-06"), ("d", "2026-04-06"),
                                                   ("e", "2026-04-06")}
    c, info = classes(feats, labels, "stage2b_negatives")
    assert c[("a", "2026-04-07")] == 0 and c[("c", "2026-04-06")] == 0
    assert info["n_excluded"] == 0


# ----------------------------------------------------------------------------------
# End to end on synthetic corpora in the released layout
# ----------------------------------------------------------------------------------

def write_corpus(root: Path, name: str, separable: bool) -> None:
    """40 honest accounts and 20 labelled accounts over 3 days. Separable: labelled
    account-days start late with one long task; inseparable: every account-day identical."""
    rows, labs = [], []
    for i in range(60):
        acc = f"acct{i:02d}"
        attack = i >= 40
        for day in ("2026-04-06", "2026-04-07", "2026-04-08"):
            pos = attack and day == "2026-04-07"
            hour = 14 if (separable and pos) else 8
            n_tasks = 1 if (separable and pos) else 4
            for k in range(8):
                rows.append(ev(acc, f"{day}T{hour:02d}:{10 + k:02d}:00Z",
                               f"{acc}-{day}-{k % n_tasks}"))
            if pos:
                labs.append((acc, day, "placeholder_scenario", "executed"))
    for kind, frame in (("audit", pd.DataFrame(rows)), ("labels", labels_frame(labs))):
        p = root / "data" / kind / name
        p.mkdir(parents=True)
        frame.to_parquet(p / "0000.parquet", index=False)


def test_end_to_end_separable_and_inseparable(tmp_path):
    write_corpus(tmp_path, "sep", separable=True)
    write_corpus(tmp_path, "flat", separable=False)
    sep = s6.run_corpus(tmp_path, "sep")["rules"]["primary"]
    flat = s6.run_corpus(tmp_path, "flat")["rules"]["primary"]
    assert sep["labels"]["n_attack"] == 20 and sep["labels"]["n_honest"] == 120
    assert sep["features"] == ["events_per_session", "first_action_min"]
    assert sep["auroc_two_sided"] > 0.95 and sep["exceeds_gate"] is True
    assert flat["auroc"] == pytest.approx(0.5) and flat["exceeds_gate"] is False


def test_shuffle_sanity_runs(tmp_path):
    write_corpus(tmp_path, "sep", separable=True)
    s = s6.shuffle_sanity(tmp_path, "sep", seed=1, repeats=3)
    assert s["n_attack"] == 20 and len(s["repeat_aurocs"]) == 3
    assert np.isfinite(s["result"]["auroc"])


def test_two_sided_interval_and_hhmm():
    assert s6.two_sided_interval([0.55, 0.65]) == (0.55, 0.65)
    assert s6.two_sided_interval([0.30, 0.45]) == pytest.approx((0.55, 0.70))
    assert s6.two_sided_interval([0.32, 0.54]) == pytest.approx((0.5, 0.68))
    assert s6.hhmm(501.5) == "08:21" and s6.hhmm(float("nan")) == "n/a"


def test_main_writes_preregistration_first(tmp_path, monkeypatch):
    write_corpus(tmp_path, "flat", separable=False)
    seen = {}

    def spy(*a, **k):
        seen["md"] = (tmp_path / "o.md").read_text(encoding="utf-8")
        raise RuntimeError("stop after pre-registration")

    monkeypatch.setattr(s6, "run_corpus", spy)
    with pytest.raises(RuntimeError):
        s6.main(["--data-dir", str(tmp_path), "--corpora", "flat", "--shuffle-corpus", "flat",
                 "--out-json", str(tmp_path / "o.json"), "--out-md", str(tmp_path / "o.md")])
    assert "pass at max(AUROC, 1 − AUROC) ≤ 0.6" in seen["md"]
    assert "results pending" in seen["md"]
