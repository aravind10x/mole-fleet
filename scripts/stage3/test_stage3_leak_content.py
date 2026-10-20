"""Tests for stage3_leak_content.py and stage3_leak_null.py on SYNTHETIC transcripts.

    cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_leak_content.py

The synthetic sessions use made-up neutral tokens (``wordaNN`` / ``wordbNN``) and made-up
account ids; no real transcript is read here.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_leak_content as lc  # noqa: E402
import stage3_leak_null as ln  # noqa: E402

VOCAB_A = [f"worda{i:02d}" for i in range(40)]
VOCAB_B = [f"wordb{i:02d}" for i in range(40)]


def _session(acc: str, date: str, hour: int, words: list[str], rng: random.Random,
             n_turns: int = 4) -> dict:
    msgs = [{"role": "system", "content": "systemtoken " * 3},
            {"role": "user", "content": "usertoken " * 3}]
    for t in range(n_turns):
        text = " ".join(rng.choice(words) for _ in range(rng.randint(8, 20)))
        m = {"role": "assistant", "content": text}
        if t % 2 == 0:
            m["tool_calls"] = [{"id": f"c{t}", "type": "function",
                                "function": {"name": "list_items", "arguments": "{}"}}]
            msgs.append(m)
            msgs.append({"role": "tool", "tool_call_id": f"c{t}", "name": "list_items",
                         "content": "tooltoken"})
        else:
            msgs.append(m)
    return {"account": acc, "sim_ts": f"{date}T{hour:02d}:00:00Z", "turn_count": n_turns,
            "session_mode": "benign", "messages": msgs}


def _write(tmp: Path, n_acc: int, separable: bool, seed: int = 0
           ) -> tuple[Path, dict[tuple[str, str], int]]:
    rng = random.Random(seed)
    labels: dict[tuple[str, str], int] = {}
    rows = []
    for a in range(n_acc):
        for date in ("2026-01-01", "2026-01-02"):
            acc = f"acct{a:03d}"
            y = int(rng.random() < 0.3)
            labels[(acc, date)] = y
            words = (VOCAB_A if y else VOCAB_B) if separable else VOCAB_A + VOCAB_B
            for h in (9, 14):
                rows.append(_session(acc, date, h, words, rng))
    p = tmp / "synthetic.transcripts.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return p, labels


def test_separable_scores_high(tmp_path: Path) -> None:
    p, labels = _write(tmp_path, 30, separable=True)
    X, y, info = lc.content_features(p, labels, n_features=512)
    assert X.shape == (60, 512 + len(lc.STYLE_FEATURES))
    assert info["rows_without_transcript_sessions"] == 0
    r = lc.classify(X, y, seed=1)
    assert r["status"] == "ok"
    assert r["auroc"] > 0.95
    assert r["passed"] is False  # a leak this strong fails the two-sided gate


def test_inseparable_scores_near_half(tmp_path: Path) -> None:
    p, labels = _write(tmp_path, 50, separable=False)
    X, y, _ = lc.content_features(p, labels, n_features=512)
    aucs = [lc.classify(X, y, seed=s)["auroc"] for s in range(5)]
    assert abs(float(np.mean(aucs)) - 0.5) < 0.12


def test_feature_determinism(tmp_path: Path) -> None:
    p, labels = _write(tmp_path, 20, separable=False)
    X1, y1, i1 = lc.content_features(p, labels, n_features=256)
    X2, y2, i2 = lc.content_features(p, labels, n_features=256)
    np.testing.assert_array_equal(X1, X2)
    np.testing.assert_array_equal(y1, y2)
    assert i1 == i2
    keys = sorted(labels)
    assert lc.random_labels(keys, 7, 0.2) == lc.random_labels(keys, 7, 0.2)
    assert lc.random_labels(keys, 7, 0.2) != lc.random_labels(keys, 8, 0.2)
    assert lc.classify(X1, y1, 3) == lc.classify(X2, y2, 3)


def test_random_labels_exact_share() -> None:
    keys = [(f"a{i}", "2026-01-01") for i in range(118)]
    lab = lc.random_labels(keys, 1, 0.2)
    assert sum(lab.values()) == 24
    assert sum(lc.random_labels(keys, 1, 0.5).values()) == 59


def test_style_features_and_missing_rows(tmp_path: Path) -> None:
    p, labels = _write(tmp_path, 5, separable=False)
    keys = sorted(labels) + [("acct999", "2026-01-01")]
    X, info = lc.content_matrix(p, keys, n_features=64)
    assert info["rows_without_transcript_sessions"] == 1
    assert np.all(X[-1, :64] == 0) and np.all(np.isnan(X[-1, 64:]))
    # every synthetic session alternates tool-call and plain turns: share 0.5
    assert np.allclose(X[:-1, 64 + 1], 0.5)
    norms = np.linalg.norm(X[:-1, :64], axis=1)
    assert np.allclose(norms, 1.0)


def _strings(o: object) -> list[str]:
    if isinstance(o, dict):
        return [str(k) for k in o] + [s for v in o.values() for s in _strings(v)]
    if isinstance(o, list):
        return [s for v in o for s in _strings(v)]
    return [o] if isinstance(o, str) else []


def test_cli_output_has_no_transcript_text(tmp_path: Path) -> None:
    p, labels = _write(tmp_path, 20, separable=True)
    out = tmp_path / "out.json"
    assert lc.main(["--transcripts", str(p), "--random-labels", "--seed", "3",
                    "--positive-share", "0.2", "--n-features", "256",
                    "--out-json", str(out)]) == 0
    raw = out.read_text(encoding="utf-8")
    for w in VOCAB_A + VOCAB_B + ["systemtoken", "usertoken", "tooltoken", "list_items",
                                 "acct0"]:
        assert w not in raw
    res = json.loads(raw)
    assert isinstance(res["classifier"]["auroc"], float)
    assert res["classifier"]["positives"] == 8 and res["classifier"]["negatives"] == 32
    # labels-file mode
    lab_path = tmp_path / "labels.json"
    lab_path.write_text(json.dumps({f"{a}|{d}": v for (a, d), v in labels.items()}))
    out2 = tmp_path / "out2.json"
    assert lc.main(["--transcripts", str(p), "--labels-json", str(lab_path),
                    "--n-features", "256", "--out-json", str(out2)]) == 0
    raw2 = out2.read_text(encoding="utf-8")
    assert all(w not in raw2 for w in VOCAB_A + VOCAB_B + ["acct0"])
    assert json.loads(raw2)["classifier"]["auroc"] > 0.95


def test_null_summary_and_verdict() -> None:
    runs = [{"auroc": a, "auroc_two_sided": max(a, 1 - a)} for a in (0.45, 0.5, 0.55, 0.62)]
    s = ln.summarise(runs, representative=runs[0])
    assert s["n_seeds"] == 4
    assert s["auroc_mean"] == pytest.approx(0.53)
    assert s["two_sided_max"] == pytest.approx(0.62)
    assert s["passed"] is True
    bad = ln.summarise(runs, representative=runs[3])
    assert bad["passed"] is False


def test_null_output_strings_are_safe(tmp_path: Path) -> None:
    p, _ = _write(tmp_path, 10, separable=False)
    ln.assert_no_text({"a": 1, "features": ["session_length"]}, p)
    with pytest.raises(ValueError):
        ln.assert_no_text({"x": "worda01 wordb02"}, p)
    with pytest.raises(ValueError):
        ln.assert_no_text({"x": "acct003"}, p)


def test_permutation_band_on_synthetic_null() -> None:
    rng = np.random.default_rng(0)
    X = rng.normal(size=(60, 4))

    def draw(seed: int) -> dict[str, np.ndarray]:
        return {"metadata": X}

    b = ln.permutation_band(draw, 0.2, range(40))
    assert b["n"] == 60 and b["positives"] == 12 and b["n_seeds"] == 40
    c = b["classifiers"]["metadata"]
    lo, hi = c["auroc"]["p2_5"], c["auroc"]["p97_5"]
    assert lo < 0.5 < hi and hi < 1.0
    t = c["two_sided"]
    assert 0.5 <= t["p2_5"] <= t["p97_5"] < 1.0
    assert t["p2_5"] <= c["calibrated_gate_two_sided_p95"] <= t["p97_5"]


def test_draw_labels_clustered_by_account() -> None:
    groups = [f"acc{i // 3}" for i in range(30)]          # 10 accounts x 3 days
    for seed in range(5):
        y = ln.draw_labels(30, seed, 0.2, groups)
        pos_acc = {g for g, v in zip(groups, y) if v}
        assert len(pos_acc) == 2                           # round(0.2 * 10) accounts
        assert all(v == (g in pos_acc) for g, v in zip(groups, y))
    y = ln.draw_labels(30, 1, 0.2)
    assert int(y.sum()) == 6
    with pytest.raises(ValueError):
        ln.draw_labels(30, 1, 0.2, groups[:-1])


def test_cli_guards(tmp_path: Path) -> None:
    j, m = tmp_path / "o.json", tmp_path / "o.md"
    j.write_text(json.dumps({"preregistration": {"utc": "x"}, "post_hoc_x": {}}))
    m.write_text("POST-HOC")
    with pytest.raises(SystemExit):           # cluster option without band mode
        ln.main(["--cluster-by-account", "--out-json", str(j), "--out-md", str(m)])
    with pytest.raises(SystemExit):           # pre-registered rerun over post-hoc blocks
        ln.main(["--out-json", str(j), "--out-md", str(m)])
    with pytest.raises(SystemExit):           # force flag outside the pre-registered run
        ln.main(["--permutation-band", "--force-prereg-rerun", "--out-json", str(j),
                 "--out-md", str(m)])
    assert ln.has_post_hoc(j, m)
    j.write_text(json.dumps({"preregistration": {"utc": "x"}}))
    m.write_text("pre-registered only")
    assert not ln.has_post_hoc(j, m)
