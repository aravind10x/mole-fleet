#!/usr/bin/env python3
"""Content-leak classifier over session transcripts at the account-day unit (Stage 3, brief 07
S4.3; design v3 section 4, "The leak repair, specified", and rungs 2 to 4).

Why: Stage 2b's metadata leak audit (L13) only sees session shape (length, turn cap, events,
first action). A planted session that rides the benign template can still differ in what the
assistant writes. This classifier is the cheap content and style check beside the metadata one:
if it separates planted account-days from honest ones, the world leaks by content.

What: per account-day (the account's sessions of that day, date = sim_ts[:10]) one document
built from the ASSISTANT turns only: the message text plus the names of the tools the turn
calls (not their arguments). Features:

* word unigrams and bigrams (lowercase, ``[a-z0-9_]+`` tokens, bigrams within one turn),
  hashed with CRC32 into ``n_features`` columns, weighted by sublinear TF (1 + log tf) times
  smoothed IDF over the rows being classified (label-free), each row L2-normalised;
* three style features: mean assistant turn length in characters, share of assistant turns
  that carry a tool call, distinct unigrams per 1,000 unigram tokens.

The classifier is ``grouping_measure.leak_classifier`` imported unchanged (the Stage 2b
numpy L2 logistic regression, stratified 5-fold AUROC, bootstrap interval, two-sided value);
its input is a dense float matrix, which the hashed features fit. No LLM calls, no network.
Deterministic: features have no randomness; labels and folds follow the seed.

Outputs carry numbers and feature names only: no transcript text, no account ids.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_leak_content.py \\
        --transcripts /abs/prefix_v1.transcripts.jsonl \\
        --random-labels --seed 20261020 --positive-share 0.2 --out-json /abs/out.json
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import grouping_measure as gm  # noqa: E402

VERSION = "stage3-leak-content-v1"
N_FEATURES = 4096
STYLE_FEATURES = ("mean_turn_chars", "tool_call_turn_share", "vocab_per_1k_tokens")
TOKEN_RE = re.compile(r"[a-z0-9_]+")

Key = tuple[str, str]  # (account, date YYYY-MM-DD)


# ----------------------------------------------------------------------------------
# Documents
# ----------------------------------------------------------------------------------

def _tool_names(msg: dict[str, Any]) -> list[str]:
    out = []
    for tc in msg.get("tool_calls") or []:
        if isinstance(tc, dict):
            fn = tc.get("function")
            name = fn.get("name") if isinstance(fn, dict) else tc.get("name")
            if isinstance(name, str) and name:
                out.append(name)
    return out


def account_day_turns(transcripts_path: str | Path) -> dict[Key, list[tuple[str, list[str]]]]:
    """(account, date) -> assistant turns as (text, tool names), in file order. Only the
    assistant role is read; system, user and tool messages are skipped."""
    days: dict[Key, list[tuple[str, list[str]]]] = {}
    with open(transcripts_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            if not isinstance(e, dict):
                continue
            acc, ts = e.get("account"), e.get("sim_ts")
            if not isinstance(acc, str) or not isinstance(ts, str) or len(ts) < 10:
                continue
            turns = days.setdefault((acc, ts[:10]), [])
            for m in e.get("messages") or []:
                if not isinstance(m, dict) or m.get("role") != "assistant":
                    continue
                c = m.get("content")
                turns.append((c if isinstance(c, str) else "", _tool_names(m)))
    return days


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _bucket(term: str, n_features: int) -> int:
    return zlib.crc32(term.encode("utf-8")) % n_features


def _row_terms(turns: list[tuple[str, list[str]]]) -> tuple[dict[int, int], list[float]]:
    """Hashed term counts (unbucketed until the caller supplies the width) and style values."""
    counts: dict[str, int] = {}
    n_tok = 0
    vocab: set[str] = set()
    lens = []
    tool_turns = 0
    for text, tools in turns:
        lens.append(len(text))
        if tools:
            tool_turns += 1
        tk = tokens(text)
        n_tok += len(tk)
        vocab.update(tk)
        for t in tk:
            counts[t] = counts.get(t, 0) + 1
        for a, b in zip(tk, tk[1:]):
            g = a + " " + b
            counts[g] = counts.get(g, 0) + 1
        for name in tools:
            g = "tool:" + name.lower()
            counts[g] = counts.get(g, 0) + 1
    style = [float(np.mean(lens)) if lens else math.nan,
             tool_turns / len(turns) if turns else math.nan,
             1000.0 * len(vocab) / n_tok if n_tok else math.nan]
    return counts, style  # type: ignore[return-value]


def content_matrix(transcripts_path: str | Path, keys: Iterable[Key],
                   n_features: int = N_FEATURES,
                   turns_by_day: dict[Key, list[tuple[str, list[str]]]] | None = None
                   ) -> tuple[np.ndarray, dict[str, Any]]:
    """Feature matrix for the given account-days, rows in the order of ``keys``. An
    account-day with no transcript session gets a zero text vector and NaN style values
    (``leak_classifier`` imputes NaN with the training-fold mean)."""
    keys = list(keys)
    days = turns_by_day if turns_by_day is not None else account_day_turns(transcripts_path)
    H = np.zeros((len(keys), n_features), dtype=float)
    S = np.full((len(keys), len(STYLE_FEATURES)), np.nan)
    missing = 0
    for i, k in enumerate(keys):
        turns = days.get(k)
        if not turns:
            missing += 1
            continue
        counts, style = _row_terms(turns)
        for term, c in counts.items():
            H[i, _bucket(term, n_features)] += c
        S[i] = style
    tf = np.where(H > 0, 1.0 + np.log(np.where(H > 0, H, 1.0)), 0.0)
    df = (H > 0).sum(axis=0)
    idf = np.log((1.0 + len(keys)) / (1.0 + df)) + 1.0
    W = tf * idf
    norm = np.linalg.norm(W, axis=1, keepdims=True)
    W = np.divide(W, norm, out=np.zeros_like(W), where=norm > 0)
    info = {
        "rows": len(keys),
        "rows_without_transcript_sessions": missing,
        "account_days_in_transcripts": len(days),
        "account_days_in_transcripts_not_classified": len(set(days) - set(keys)),
        "n_hashed_features": n_features,
        "n_hashed_features_nonzero": int((df > 0).sum()),
        "style_features": list(STYLE_FEATURES),
        "feature_description": (
            "assistant turns only; word unigrams + within-turn bigrams ([a-z0-9_]+, "
            "lowercased) and tool-call names (not arguments), CRC32-hashed into "
            f"{n_features} columns, sublinear TF x smoothed IDF over the classified rows "
            "(label-free), rows L2-normalised; plus style features "
            + ", ".join(STYLE_FEATURES)),
    }
    return np.hstack([W, S]), info


def content_features(transcripts_path: str | Path, labels: dict[Key, int],
                     n_features: int = N_FEATURES
                     ) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """(X, y, info) over the labelled account-days, rows sorted by (account, date)."""
    keys = sorted(labels)
    X, info = content_matrix(transcripts_path, keys, n_features)
    y = np.array([int(labels[k]) for k in keys], dtype=int)
    return X, y, info


# ----------------------------------------------------------------------------------
# Labels
# ----------------------------------------------------------------------------------

def random_labels(keys: Iterable[Key], seed: int, positive_share: float) -> dict[Key, int]:
    """Exactly round(share * n) positives (at least 1, at most n - 1), drawn uniformly
    without replacement over the sorted keys with numpy's default_rng(seed)."""
    keys = sorted(keys)
    n = len(keys)
    k = min(max(int(round(positive_share * n)), 1), n - 1)
    pos = set(np.random.default_rng(seed).permutation(n)[:k].tolist())
    return {key: int(i in pos) for i, key in enumerate(keys)}


def load_labels_json(path: str | Path) -> dict[Key, int]:
    """JSON object {"account|YYYY-MM-DD": 0 or 1}."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    out: dict[Key, int] = {}
    for k, v in raw.items():
        acc, _, date = str(k).rpartition("|")
        if not acc or len(date) != 10:
            raise ValueError(f"label key must be 'account|YYYY-MM-DD' (bad key #{len(out)})")
        out[(acc, date)] = int(v)
    return out


# ----------------------------------------------------------------------------------
# Classifier result (numbers and feature names only)
# ----------------------------------------------------------------------------------

def classify(X: np.ndarray, y: np.ndarray, seed: int) -> dict[str, Any]:
    """``grouping_measure.leak_classifier`` unchanged, trimmed to numbers and status."""
    r = gm.leak_classifier(X, y, seed=seed)
    keep = ("n", "positives", "folds", "threshold", "auroc", "auroc_two_sided", "ci",
            "n_boot", "passed", "status")
    out = {k: r[k] for k in keep if k in r}
    out["negatives"] = int(r["n"] - r["positives"])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--transcripts", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--labels-json")
    g.add_argument("--random-labels", action="store_true")
    ap.add_argument("--seed", type=int, default=gm.SEED)
    ap.add_argument("--positive-share", type=float, default=0.2)
    ap.add_argument("--n-features", type=int, default=N_FEATURES)
    ap.add_argument("--out-json", required=True)
    ns = ap.parse_args(argv)
    if ns.random_labels:
        days = account_day_turns(ns.transcripts)
        labels = random_labels(days, ns.seed, ns.positive_share)
        X, info = content_matrix(ns.transcripts, sorted(labels), ns.n_features, days)
        y = np.array([labels[k] for k in sorted(labels)], dtype=int)
        lab_desc: dict[str, Any] = {"mode": "random", "seed": ns.seed,
                                    "positive_share": ns.positive_share}
    else:
        labels = load_labels_json(ns.labels_json)
        X, y, info = content_features(ns.transcripts, labels, ns.n_features)
        lab_desc = {"mode": "file", "labels_sha256": gm.sha256_file(ns.labels_json)}
    res = {
        "version": VERSION,
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": "python -I work/checks/stage3_leak_content.py " + " ".join(
            sys.argv[1:] if argv is None else argv),
        "script_sha256": gm.sha256_file(__file__),
        "transcripts_sha256": gm.sha256_file(ns.transcripts),
        "labels": lab_desc,
        "features": info,
        "classifier": classify(X, y, ns.seed),
    }
    Path(ns.out_json).write_text(json.dumps(gm._clean(res), indent=2, default=gm._json_default)
                                 + "\n", encoding="utf-8")
    c = res["classifier"]
    print(f"wrote {ns.out_json}; AUROC {c.get('auroc'):.3f} two-sided "
          f"{c.get('auroc_two_sided', float('nan')):.3f} n1={c['positives']} n0={c['negatives']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
