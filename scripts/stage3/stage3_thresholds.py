#!/usr/bin/env python3
"""Randomised flag thresholds that give the honest null exactly its nominal flag rate B, plus
the small statistics the Stage 3 gate checks need (bootstrap of the author-level threshold,
Clopper-Pearson intervals, the "degenerate null" defect checks).

Why randomise. Judge scores are integers 0..100 and tie heavily, so no plain quantile gives
the honest null a flag rate of exactly B. The rule here flags every unit scoring strictly above
t and a unit scoring exactly t with probability p_tie, with t and p_tie chosen so that the
expected honest flag rate is exactly B:

- t = the smallest observed score whose share strictly above it is <= B;
- a = share strictly above t, e = share equal to t, p_tie = (B - a) / e.

The tie decision for one unit is reproducible and independent of call order: it is
`tie_uniform(seed, label) < p_tie`, where `tie_uniform` maps sha256(f"{seed}|{label}") to a
uniform in [0, 1). The rule is a plain JSON-serialisable dict.

Sentinels: B >= 1 gives `threshold: None, p_tie: 1.0` (flag every scored unit); B <= 0 gives
`threshold: None, p_tie: 0.0` (flag nothing). A score of None (an author with no units) is
never flagged, under either sentinel too.

Author level. The cost of flagging a set of authors is their weight (active account-days) over
the total weight, which includes authors with no units. Same construction over author maxima;
p_tie is clamped to 1 when even flagging every author with units costs less than B (then
`expected_cost` < B and says so). `deterministic_threshold` is the "at most B, no
randomisation" reading: the lowest t with cost(max >= t) <= B (None = flag nothing).

Comparisons with B are exact (B read as its decimal repr through Fraction; weights as exact
Fractions), so B = 0.05 on n = 100 gives share 5/100 <= B, not a float near-miss.

Pure functions, no I/O. `python -I stage3_thresholds.py --selftest` runs a worked example.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from fractions import Fraction
from typing import Any, Hashable, Mapping, Sequence

import numpy as np


def _frac(x: float | int) -> Fraction:
    """Exact Fraction of a rate or weight; floats go through repr so 0.05 is 1/20."""
    if isinstance(x, (bool, np.bool_)):
        raise ValueError("boolean is not a number here")
    if isinstance(x, (int, np.integer)):
        return Fraction(int(x))
    return Fraction(repr(float(x)))


def _py(v: Any) -> Any:
    return v.item() if isinstance(v, np.generic) else v


def _fit(pairs: Sequence[tuple[Any, Fraction]], total: Fraction, bf: Fraction
         ) -> tuple[Any, Fraction, Fraction]:
    """Weighted core. pairs = (value, weight) of units that can be flagged. Returns
    (t, weight strictly above t, weight equal to t) for the smallest observed t with
    weight(> t) <= B * total."""
    by_val: dict[Any, Fraction] = {}
    for v, w in pairs:
        by_val[v] = by_val.get(v, Fraction(0)) + w
    cap = bf * total
    above = Fraction(0)
    t, above_t = None, Fraction(0)
    for v in sorted(by_val, reverse=True):
        if above > cap:
            break
        t, above_t = v, above
        above += by_val[v]
    assert t is not None
    return t, above_t, by_val[t]


def _deterministic(pairs: Sequence[tuple[Any, Fraction]], total: Fraction, bf: Fraction
                   ) -> tuple[Any, Fraction]:
    """Lowest observed t with weight(>= t) <= B * total, and that weight; (None, 0) if none."""
    by_val: dict[Any, Fraction] = {}
    for v, w in pairs:
        by_val[v] = by_val.get(v, Fraction(0)) + w
    cap = bf * total
    cum = Fraction(0)
    t, c = None, Fraction(0)
    for v in sorted(by_val, reverse=True):
        cum += by_val[v]
        if cum > cap:
            break
        t, c = v, cum
    return t, c


def tie_uniform(seed: int | str, label: str) -> float:
    """Deterministic uniform in [0, 1) from sha256(f"{seed}|{label}") (top 53 bits)."""
    h = hashlib.sha256(f"{seed}|{label}".encode("utf-8")).digest()
    return (int.from_bytes(h[:8], "big") >> 11) / float(1 << 53)


def randomised_threshold(scores: Sequence[float], rate: float, *, seed: int | str) -> dict:
    """The unit-level randomised rule on an equal-weight honest null (see module docstring)."""
    vals = [_py(s) for s in scores]
    if not vals:
        raise ValueError("randomised_threshold: empty scores")
    n = len(vals)
    k = len(set(vals))
    bf = _frac(rate)
    base = {"kind": "unit", "rate": rate, "seed": seed, "n": n, "distinct_scores": k}
    if bf >= 1:
        return {**base, "threshold": None, "p_tie": 1.0, "share_above": 1.0, "share_at": 0.0,
                "expected_rate": 1.0}
    if bf <= 0:
        return {**base, "threshold": None, "p_tie": 0.0, "share_above": 0.0, "share_at": 0.0,
                "expected_rate": 0.0}
    t, above, at = _fit([(v, Fraction(1)) for v in vals], Fraction(n), bf)
    p = min(Fraction(1), (bf * n - above) / at)
    a, e = above / n, at / n
    return {**base, "threshold": t, "p_tie": float(p), "share_above": float(a),
            "share_at": float(e), "expected_rate": float(a + p * e)}


def is_flagged(score: float | None, rule: Mapping[str, Any], label: str) -> bool:
    """True if score > t; at score == t, True iff tie_uniform(seed, label) < p_tie. A None
    score (no units) is never flagged. threshold None: flag all iff p_tie >= 1, else none."""
    if score is None:
        return False
    t, p = rule["threshold"], float(rule["p_tie"])
    if t is None:
        return p >= 1.0
    if score > t:
        return True
    if score == t:
        return p > 0.0 and tie_uniform(rule["seed"], label) < p
    return False


def expected_flag_rate(scores: Sequence[float], rule: Mapping[str, Any]) -> float:
    """Expectation over tie draws of the flagged share of `scores` under `rule`
    (= share above t + p_tie * share at t on these scores, which may be another sample)."""
    vals = [_py(s) for s in scores]
    if not vals:
        raise ValueError("expected_flag_rate: empty scores")
    t, p = rule["threshold"], _frac(rule["p_tie"])
    if t is None:
        return 1.0 if p >= 1 else 0.0
    above = sum(1 for v in vals if v > t)
    at = sum(1 for v in vals if v == t)
    return float((above + p * at) / len(vals))


def _author_pairs(author_max: Mapping[Hashable, float | None],
                  author_weight: Mapping[Hashable, float]
                  ) -> tuple[list[tuple[Any, Fraction]], Fraction]:
    for a, m in author_max.items():
        if m is not None and a not in author_weight:
            raise ValueError(f"author {a!r} has a max score but no weight")
    ws = {a: _frac(w) for a, w in author_weight.items()}
    if any(w < 0 for w in ws.values()):
        raise ValueError("negative author weight")
    total = sum(ws.values(), Fraction(0))
    if total <= 0:
        raise ValueError("total author weight must be positive")
    pairs = [(_py(author_max[a]), ws[a]) for a in ws if author_max.get(a) is not None]
    return pairs, total


def author_level_threshold(author_max: Mapping[Hashable, float | None],
                           author_weight: Mapping[Hashable, float], rate: float, *,
                           seed: int | str) -> dict:
    """Author-level randomised rule: authors with max > t flagged, max == t with p_tie, so the
    expected weighted cost is exactly B (or the cost of all authors with units, if less)."""
    pairs, total = _author_pairs(author_max, author_weight)
    bf = _frac(rate)
    t_det, c_det = _deterministic(pairs, total, bf) if pairs else (None, Fraction(0))
    base = {"kind": "author", "rate": rate, "seed": seed, "n_authors": len(author_weight),
            "total_weight": _py(sum(author_weight.values())),
            "deterministic_threshold": t_det, "deterministic_cost": float(c_det / total)}
    unit_cost = sum((w for _, w in pairs), Fraction(0)) / total
    if bf >= 1 or (bf > 0 and not pairs):
        return {**base, "threshold": None, "p_tie": 1.0, "cost_above": float(unit_cost),
                "cost_at": 0.0, "expected_cost": float(unit_cost)}
    if bf <= 0:
        return {**base, "threshold": None, "p_tie": 0.0, "cost_above": 0.0, "cost_at": 0.0,
                "expected_cost": 0.0}
    t, above, at = _fit(pairs, total, bf)
    p = Fraction(1) if at == 0 else min(Fraction(1), (bf * total - above) / at)
    return {**base, "threshold": t, "p_tie": float(p), "cost_above": float(above / total),
            "cost_at": float(at / total), "expected_cost": float((above + p * at) / total)}


def bootstrap_author_threshold(author_max: Mapping[Hashable, float | None],
                               author_weight: Mapping[Hashable, float], rate: float, *,
                               seed: int, n_boot: int = 2000) -> dict:
    """Cluster bootstrap (author = cluster, authors without units included) of the SEALED
    author-level threshold t (the randomised rule's t from `_fit`; review 2026-10-23 finding 11:
    the earlier version bootstrapped the deterministic threshold, which is a different point
    estimate), with the deterministic threshold's bootstrap kept beside under
    `deterministic`. Authors are put in sorted(str) order before
    resampling so the result does not depend on dict order. Percentiles use numpy's
    "inverted_cdf" method so every reported value is an observed threshold; a replica with no
    admissible threshold (flag nothing) counts as +inf, is keyed "none" in `distribution` and
    reported as None if it lands on a percentile."""
    _author_pairs(author_max, author_weight)                 # validation
    authors = sorted(author_weight, key=str)
    mx = [_py(author_max.get(a)) for a in authors]
    ws = [_frac(author_weight[a]) for a in authors]
    bf = _frac(rate)
    rng = np.random.default_rng(seed)
    out: list[Any] = []
    out_det: list[Any] = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(authors), size=len(authors))
        total = sum((ws[i] for i in idx), Fraction(0))
        pairs = [(mx[i], ws[i]) for i in idx if mx[i] is not None]
        if pairs and total > 0:
            out.append(_fit(pairs, total, bf)[0])
            out_det.append(_deterministic(pairs, total, bf)[0])
        else:
            out.append(None)
            out_det.append(None)

    def summar(vals: list[Any]) -> dict:
        arr = np.array([math.inf if t is None else float(t) for t in vals])

        def pct(q: float) -> float | None:
            v = float(np.percentile(arr, q, method="inverted_cdf"))
            return None if math.isinf(v) else v

        dist = Counter("none" if t is None else t for t in vals)
        keys = sorted((k for k in dist if k != "none")) + (["none"] if "none" in dist else [])
        return {"ci95": [pct(2.5), pct(97.5)], "median": pct(50), "distribution": {k: dist[k] for k in keys}}

    return {"n_boot": n_boot, **summar(out), "deterministic": summar(out_det)}


def _binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k), X ~ Binomial(n, p)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def _bisect(f: Any, lo: float = 0.0, hi: float = 1.0, tol: float = 1e-12) -> float:
    """Root of an increasing f on [lo, hi] (f(lo) <= 0 <= f(hi))."""
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if f(mid) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _clopper_pearson_exact(k: int, n: int, alpha: float) -> tuple[float, float]:
    """Clopper-Pearson by bisection on exact binomial tails (no scipy)."""
    lo = 0.0 if k == 0 else _bisect(lambda p: (1 - _binom_cdf(k - 1, n, p)) - alpha / 2)
    hi = 1.0 if k == n else _bisect(lambda p: alpha / 2 - _binom_cdf(k, n, p))
    return lo, hi


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact (Clopper-Pearson) two-sided 1 - alpha interval for a binomial proportion k / n.
    Uses scipy's beta quantiles when importable, else `_clopper_pearson_exact`."""
    if n <= 0 or not 0 <= k <= n:
        raise ValueError(f"clopper_pearson: need 0 <= k <= n, n > 0 (k={k}, n={n})")
    try:
        from scipy.stats import beta
    except ImportError:
        return _clopper_pearson_exact(k, n, alpha)
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def distinct_above_median(scores: Sequence[float]) -> int:
    """Number of distinct score values strictly above the median (numpy median; the
    degenerate-null check is "fewer than five")."""
    if len(scores) == 0:
        raise ValueError("distinct_above_median: empty scores")
    med = float(np.median(np.asarray(scores, dtype=float)))
    return len({_py(s) for s in scores if s > med})


def top_share(scores: Sequence[float]) -> float:
    """The largest share any single score value holds."""
    if len(scores) == 0:
        raise ValueError("top_share: empty scores")
    return max(Counter(_py(s) for s in scores).values()) / len(scores)


def _selftest() -> dict:
    tied = [5] * 40 + [10] * 30 + [20] * 20 + [60] * 6 + [72] * 4
    r = randomised_threshold(tied, 0.05, seed=7)
    assert r["threshold"] == 60 and abs(expected_flag_rate(tied, r) - 0.05) < 1e-12
    amax = {"a": 90, "b": 80, "c": 80, "d": 50, "e": 10, "f": 10}
    aw = {"a": 2, "b": 3, "c": 5, "d": 20, "e": 30, "f": 30, "quiet": 10}
    ar = author_level_threshold(amax, aw, 0.05, seed=3)
    assert ar["threshold"] == 80 and abs(ar["expected_cost"] - 0.05) < 1e-12
    return {"unit_rule": r, "author_rule": ar,
            "bootstrap": bootstrap_author_threshold(amax, aw, 0.05, seed=3, n_boot=200),
            "clopper_pearson_12_24": clopper_pearson(12, 24),
            "distinct_above_median": distinct_above_median(tied), "top_share": top_share(tied)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true", help="run a worked example and print it")
    args = ap.parse_args()
    if args.selftest:
        print(json.dumps(_selftest(), indent=2))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
