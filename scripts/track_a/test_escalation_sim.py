"""Tests for work/checks/escalation_sim.py on tiny hand-built tables (3 accounts, 8 days).
No real data is read.

    work/mole-fork/.venv/bin/python -I -m pytest work/checks/test_escalation_sim.py -q
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import escalation_sim as es  # noqa: E402

ACCTS = ["a", "b", "c"]
DATES = es.weekdays(es.date(2026, 4, 6), 8)


def tiny_tables(c_by_day=None, cal_by_day=None, executed=(), attempted=(), outcomes=None, scores=None):
    """3 accounts x 8 days. c_by_day[d] / cal_by_day[d] = [c_a, c_b, c_c]."""
    rows, erows = [], []
    for di, dt in enumerate(DATES):
        d = di + 1
        for ai, a in enumerate(ACCTS):
            ev = d >= 6
            c = (c_by_day or {}).get(d, [0.1 * (ai + 1)] * 3)[ai] if ev else None
            cc = (cal_by_day or {}).get(d, [0.1 + 0.01 * d, 0.2 + 0.01 * d, 0.3 + 0.01 * d])[ai] if not ev else None
            rows.append({"account": a, "date": dt, "day_index": d, "is_eval_day": ev,
                         "c_z": np.nan if c is None else float(c),
                         "c_z_cal": np.nan if cc is None else float(cc), "l1_nonnoisy": False})
            if ev:
                oc = (outcomes or {}).get((a, d), "scored")
                sc = (scores or {}).get((a, d), 10.0)
                erows.append({"account": a, "date": dt, "day_index": d, "outcome": oc,
                              "score": np.nan if oc != "scored" else float(sc), "cost_usd": 0.05,
                              "model": "test"})
    cheap = pd.DataFrame(rows).sort_values(["account", "date"]).reset_index(drop=True)
    exp = pd.DataFrame(erows)
    ex = {(a, DATES[d - 1]) for a, d in executed}
    at = {(a, DATES[d - 1]) for a, d in attempted}
    labels = {"executed": ex, "attempted": at - ex,
              "labelled_accounts": sorted({a for a, _ in ex | at}), "info": {}}
    return cheap, exp, labels


def tiny_world(**kw):
    cheap, exp, labels = tiny_tables(**kw)
    return es.build_world(cheap, exp, labels, {"summary": {"mean_cost_usd": 0.05}}, False)


def rid(w, a, d):
    return int(np.where((w.account == a) & (w.day == d))[0][0])


# ── PACE controller ──────────────────────────────────────────────────────

# ── PACE as restated by Amendment 1 ──────────────────────────────────────

def test_pav_isotonic_fit():
    assert list(es.pav_increasing([0.1, 0.2, 0.3], [1, 1, 1])) == pytest.approx([0.1, 0.2, 0.3])
    assert list(es.pav_increasing([0.5, 0.2], [1, 3])) == pytest.approx([0.275, 0.275])
    # 0.6 / 0.3 pool to 0.45 (w 2), then 0.2 (w 2) pools in: (0.6 + 0.3 + 0.4) / 4 = 0.325
    assert list(es.pav_increasing([0.1, 0.6, 0.3, 0.2, 0.9], [1, 1, 1, 2, 1])) == \
        pytest.approx([0.1, 0.325, 0.325, 0.325, 0.9])
    rng = np.random.default_rng(0)
    for _ in range(50):
        y, wt = rng.random(10), rng.random(10) + 0.1
        f = es.pav_increasing(y, wt)
        assert (np.diff(f) >= -1e-12).all()
        assert (f * wt).sum() == pytest.approx((y * wt).sum())      # weighted mean preserved


def test_pace_monotone_prior_and_untested_bucket_never_outranks_tested_higher():
    s, f = es.pace_prior()
    assert list(s) == pytest.approx([0.2 * (b + 1) for b in range(10)])
    assert list(s + f) == pytest.approx([2.0] * 10)
    p = es.PacePolicy(3, 0.2)
    assert list(p.yields()) == pytest.approx([0.1 * (b + 1) for b in range(10)])
    p.f[9] += 50                                         # top bucket tested, yield ~ 0.04
    Y = p.yields()
    assert (np.diff(Y) >= -1e-12).all()
    assert Y[8] <= Y[9] + 1e-12 and Y[0] <= Y[9] + 1e-12   # untested lower buckets pooled down
    # buckets 1..9 pool at their count-weighted mean (sum s 10.8 over weight 68); bucket 0's
    # prior 0.1 is below that and stays
    assert Y[0] == pytest.approx(0.1)
    assert list(Y[1:]) == pytest.approx([10.8 / 68] * 9)


def test_pace_carry_and_pool_arithmetic():
    L = es.CarryLedger(3)                                # k = 10, r = 0.2: base 8
    assert L.total(6) == 0                               # day 6: nothing deposited yet
    L.deposit(6, 5.0)
    assert L.total(7) == 5
    L.deposit(7, 0.0)                                    # an overspent day deposits nothing
    assert L.total(8) == 5
    assert es.pace_pool_add(0.0, 0.2, 10, 3) == pytest.approx(2.0)
    assert es.pace_pool_add(5.0, 0.2, 10, 3) == pytest.approx(6.0)     # cap r k w
    assert es.pace_pool_add(0.0, 0.0, 10, 3) == 0.0
    assert es.pace_daily_cap(8.0, 5.0, 6.0, 10, burst=False) == 13
    assert es.pace_daily_cap(8.0, 5.0, 6.0, 10, burst=True) == 19
    assert es.pace_daily_cap(8.0, 16.0, 6.0, 10, burst=True) == 20     # 2k cap
    assert es.pace_daily_cap(1.6, 0.0, 0.4, 2, burst=False) == 1       # floor(1.6)
    assert es.pace_daily_cap(1.6, 0.0, 0.4, 2, burst=True) == 2        # floor(2.0)
    assert es.pace_reserve_used(17, 8.0, 5.0, 6.0, burst=True) == pytest.approx(4.0)
    assert es.pace_reserve_used(12, 8.0, 5.0, 6.0, burst=True) == 0.0
    assert es.pace_reserve_used(20, 8.0, 5.0, 6.0, burst=True) == pytest.approx(6.0)
    assert es.pace_reserve_used(17, 8.0, 5.0, 6.0, burst=False) == 0.0


def test_carry_ledger_fifo_consumed_once_and_expiry():
    L = es.CarryLedger(3)                                # deposits live for w - 1 = 2 days
    L.deposit(6, 3.0)
    L.deposit(7, 5.0)
    assert L.total(8) == pytest.approx(8.0)
    assert L.draw(4.0) == pytest.approx(4.0)             # oldest first: all 3 of day 6, 1 of day 7
    assert L.deposits == [[7, pytest.approx(4.0)]]
    assert L.total(8) == pytest.approx(4.0)
    assert L.total(9) == pytest.approx(4.0)              # day 7's deposit live on days 8, 9
    assert L.total(10) == 0.0                            # ... and expired on day 10
    # one unspent day is spent once, not on each of the next w - 1 days
    L = es.CarryLedger(3)
    L.deposit(6, 8.0)
    assert L.total(7) == 8.0 and L.draw(8.0) == 8.0
    L.deposit(7, 0.0)
    assert L.total(8) == 0.0                             # the recomputed-sum reading gave 8 here
    # draw never exceeds what is live
    L = es.CarryLedger(5)
    L.deposit(6, 1.5)
    assert L.draw(4.0) == pytest.approx(1.5) and L.total(7) == 0.0
    # expiry with w = 5: live on days j + 1 .. j + 4
    L.deposit(10, 2.0)
    assert L.total(14) == 2.0 and L.total(15) == 0.0


def test_pace_unspent_day_spent_once_in_policy():
    # k = 2, r = 0, w = 3 (base 2), 30 rows a day, equal daily masses (never a burst).
    # Day 6: no row qualifies -> floor(n_d / 2) = 1 call -> deposit 1. Day 7: everything
    # qualifies, C = 1 -> n_d = 3, 3 calls, the deposit is drawn. Day 8: C = 0 -> n_d = 2
    # (the recomputed-sum reading would have given C = 1 and n_d = 3 again).
    ids = np.arange(30)
    st = es.SimState(k=2, mass={d: 10.0 for d in range(1, 31)})
    p = es.PacePolicy(3, 0.0)
    acct = np.array([f"u{i}" for i in ids])
    c = np.linspace(0.1, 3.0, 30)
    for d in (6, 7, 8):
        if d == 6:
            p.f = p.f + 1000.0                           # every fitted yield ~ 0 -> none qualify
            p.y = 0.95
        else:
            p.s, p.f = es.pace_prior()                   # prior yields 0.1 .. 1.0
            p.y = 0.05
        rows = es.DayRows(d, ids, c, acct)
        ch = p.choose(rows, st)
        p.observe(rows, ch, {i: True for i in ch}, st)
        st.calls[d] = len(ch)
        p.y = 0.05
    t = {x["d"]: x for x in p.trace}
    assert [t[d]["carry"] for d in (6, 7, 8)] == pytest.approx([0.0, 1.0, 0.0])
    assert [t[d]["n_d"] for d in (6, 7, 8)] == [2, 3, 2]
    assert [st.calls[d] for d in (6, 7, 8)] == [1, 3, 2]
    assert t[7]["carry_drawn"] == pytest.approx(1.0)
    assert sum(st.calls.values()) <= es.pace_total_bound(2, 0.0, p.reserve_used_total)


def test_pace_carry_and_pool_in_simulation():
    # 3 rows per day on days 6..8 only, k = 10, r = 0.2, w = 3: base 8, PACE calls all 3 rows
    w = tiny_world()
    s = es.make_schedule(w, 1.0, "original")
    p = es.PacePolicy(3, 0.2)
    _, calls = es.simulate(p, w, s, 10, np.zeros(w.n, bool))
    t = {x["d"]: x for x in p.trace}
    assert [calls[d] for d in (6, 7, 8, 9)] == [3, 3, 3, 0]
    assert [t[d]["carry"] for d in (6, 7, 8, 9, 10)] == pytest.approx([0, 5, 10, 10, 13])
    assert [t[d]["pool"] for d in (6, 7, 8, 9)] == pytest.approx([2, 4, 6, 6])     # capped at 6
    assert not any(t[d]["burst"] for d in (6, 7, 8))
    assert t[7]["n_d"] == 13 and t[8]["n_d"] == 18


def test_pace_burst_draws_reserve_pool():
    # k = 1, r = 0.4, w = 3: base 0.6; day 6 burst: n_d = floor(0.6 + 0 + 0.4) = 1, pool used 0.4
    w = tiny_world(c_by_day={6: [5.0, 6.0, 7.0]})
    s = es.make_schedule(w, 1.0, "original")
    p = es.PacePolicy(3, 0.4)
    _, calls = es.simulate(p, w, s, 1, np.zeros(w.n, bool))
    t = {x["d"]: x for x in p.trace}
    assert t[6]["burst"] and t[6]["n_d"] == 1 and calls[6] == 1
    assert t[6]["reserve_used"] == pytest.approx(0.4)
    assert t[7]["pool"] == pytest.approx(0.4)            # emptied, then +0.4
    assert not t[7]["burst"] and t[7]["n_d"] == 0 and calls[7] == 0    # floor(0.6 + carry 0)


def test_pace_controller_amended():
    k = 10
    assert es.pace_controller(0.5, so_far=41, plan=30, k=k) == pytest.approx(0.6)   # over by > k
    assert es.pace_controller(0.5, so_far=40, plan=30, k=k) == pytest.approx(0.5)   # over by k: band
    assert es.pace_controller(0.5, so_far=31, plan=30, k=k) == pytest.approx(0.5)
    assert es.pace_controller(0.5, so_far=19, plan=30, k=k) == pytest.approx(0.4)   # short by > k
    assert es.pace_controller(0.5, so_far=20, plan=30, k=k) == pytest.approx(0.5)
    assert es.pace_controller(0.9, so_far=99, plan=30, k=k) == pytest.approx(0.95)  # clamp high
    assert es.pace_controller(0.06, so_far=0, plan=30, k=k) == pytest.approx(0.05)  # clamp low


def test_pace_controller_uses_reserve_adjusted_plan():
    # k = 10, r = 0.4: base 6. 3 calls/day on days 6..8. Day 7: plan 6 * 2 = 12, so_far 3 ->
    # short 9 <= k: unchanged (with plan k (d - 5) = 20 it would be 17 > k). Day 8: plan 18,
    # so_far 6 -> short 12 > k -> y* falls to 0.4.
    w = tiny_world()
    s = es.make_schedule(w, 1.0, "original")
    p = es.PacePolicy(3, 0.4)
    es.simulate(p, w, s, 10, np.zeros(w.n, bool))
    t = {x["d"]: x for x in p.trace}
    assert t[6]["y_star"] == pytest.approx(0.5)
    assert t[7]["y_star"] == pytest.approx(0.5)
    assert t[8]["y_star"] == pytest.approx(0.4)


def test_pace_spend_floor():
    order = np.arange(10)
    elig = np.array([True] + [False] * 9)
    assert list(es.pace_call_set(order, elig, 8)) == [0, 1, 2, 3]          # 1 < floor(8/2) = 4
    elig5 = np.array([True] * 5 + [False] * 5)
    assert list(es.pace_call_set(order, elig5, 8)) == [0, 1, 2, 3, 4]      # 5 >= 4: only qualifying
    assert list(es.pace_call_set(order, np.array([True] * 10), 3)) == [0, 1, 2]   # at most n_d
    assert list(es.pace_call_set(order, np.zeros(10, bool), 3)) == [0]     # floor(3/2) = 1
    assert len(es.pace_call_set(order, np.zeros(10, bool), 1)) == 0        # floor(1/2) = 0
    # in a policy: nothing qualifies (y* = 0.95, every yield ~ 0) -> floor(n_d / 2) calls
    w = tiny_world(c_by_day={6: [1.0, 2.0, 3.0]})
    s = es.make_schedule(w, 1.0, "original")
    p = es.PacePolicy(3, 0.0)
    p.y = 0.95
    p.f += 1000.0
    called, calls = es.simulate(p, w, s, 2, np.zeros(w.n, bool))
    assert p.trace[0]["n_d"] == 2 and p.trace[0]["n_eligible"] == 0 and p.trace[0]["floor_applied"]
    assert calls[6] == 1 and called[rid(w, "c", 6)]                     # top by rank (c ties on Y)


def test_pace_total_bound():
    assert es.pace_total_bound(10, 0.0, 0.0) == 250
    assert es.pace_total_bound(10, 0.2, 7.5) == pytest.approx(207.5)
    assert es.pace_total_bound(10, 0.2, 50.0) == pytest.approx(250.0)    # reserve <= 25 r k


# ── PACE v0 (section 4 as first written; --pace-v0 only) ──────────────────

def test_v0_pace_controller_moves_y_star_the_right_way():
    k = 10
    assert es.pace_controller_v0(0.5, so_far=31, plan=30, k=k) == pytest.approx(0.6)      # overspent
    assert es.pace_controller_v0(0.5, so_far=19, plan=30, k=k) == pytest.approx(0.4)      # short by > k
    assert es.pace_controller_v0(0.5, so_far=20, plan=30, k=k) == pytest.approx(0.5)      # short by exactly k
    assert es.pace_controller_v0(0.5, so_far=30, plan=30, k=k) == pytest.approx(0.5)      # on plan
    assert es.pace_controller_v0(0.95, so_far=99, plan=30, k=k) == pytest.approx(0.99)    # clamp high
    assert es.pace_controller_v0(0.011, so_far=0, plan=30, k=k) == pytest.approx(0.01)    # clamp low


def test_v0_pace_policy_lowers_y_star_when_underspending():
    # r = 0.4 with w = 3, k = 1: K = 3, A - rK = 3 - 1.2 -> 1 call/day at most (non-burst),
    # so after day 6 the plan k (d - 5) is never exceeded; force under-spending by making every
    # yield bucket ineligible: y* starts at 0.5 and all Y are 0.5 -> eligible. Use r large instead.
    w = tiny_world()
    s = es.make_schedule(w, 1.0, "original")
    surf = np.zeros(w.n, bool)
    p = es.PacePolicyV0(3, 0.4)
    p.r = 2.0                                            # n_d = 0 every non-burst day
    es.simulate(p, w, s, 1, surf)
    ys = [t["y_star"] for t in p.trace]
    # day 6: plan 1, so_far 0 -> short by 1 = k (no change); day 7: plan 2, short 2 > 1 -> down
    assert ys[0] == pytest.approx(0.5)
    assert ys[1] == pytest.approx(0.4)
    assert all(b <= a + 1e-12 for a, b in zip(ys, ys[1:]))


def test_v0_pace_policy_raises_y_star_when_overspending():
    # bursts on days 6 and 7 let PACE spend 2k = 2 per day: so_far = 4 > plan k (8 - 5) = 3 on
    # day 8 -> y* rises (every call surfaces, so the called buckets stay eligible).
    w = tiny_world(c_by_day={6: [5.0, 6.0, 7.0], 7: [50.0, 60.0, 70.0]})
    s = es.make_schedule(w, 1.0, "original")
    p = es.PacePolicyV0(5, 0.0)
    es.simulate(p, w, s, 1, np.ones(w.n, bool))
    assert [t["burst"] for t in p.trace[:2]] == [True, True]
    assert [t["calls"] for t in p.trace[:2]] == [2, 2]
    assert p.trace[1]["y_star"] == pytest.approx(0.5)        # day 7: so_far 2 = plan 2
    assert p.trace[2]["y_star"] == pytest.approx(0.6)


# ── burst rule and spend cap ─────────────────────────────────────────────

def test_burst_rule():
    prev = [10, 10, 10, 10, 10]                          # mean 10, sd 0
    assert not es.is_burst(10, prev)
    assert es.is_burst(10.01, prev)
    prev = [8, 12, 8, 12, 10]                            # mean 10, population sd sqrt(3.2)
    sd = math.sqrt(3.2)
    assert not es.is_burst(10 + sd - 1e-9, prev)
    assert es.is_burst(10 + sd + 1e-9, prev)


def test_v0_burst_uses_calibration_masses_on_day_6():
    # cal mass of day d = 0.6 + 0.03 d (days 1..5: mean 0.69, population sd 0.042)
    w = tiny_world(c_by_day={6: [0.3, 0.3, 0.3]})        # day 6 mass 0.9 > 0.732 -> burst
    s = es.make_schedule(w, 1.0, "original")
    assert s.mass[1] == pytest.approx(0.63) and s.mass[6] == pytest.approx(0.9)
    p = es.PacePolicyV0(3, 0.4)
    es.simulate(p, w, s, 1, np.zeros(w.n, bool))
    assert p.trace[0]["burst"] is True
    assert p.trace[0]["n_d"] == 2                        # min(A = 3, 2k = 2)


def test_v0_pace_spendable():
    assert es.pace_spendable_v0(A=30, k=10, K=30, r=0.2, burst=False) == 20     # min(30-6, 20)
    assert es.pace_spendable_v0(A=10, k=10, K=30, r=0.2, burst=False) == 4
    assert es.pace_spendable_v0(A=4, k=10, K=30, r=0.2, burst=False) == 0       # max(0, .)
    assert es.pace_spendable_v0(A=4, k=10, K=30, r=0.2, burst=True) == 4        # reserve released
    assert es.pace_spendable_v0(A=6, k=2, K=6, r=0.2, burst=False) == 4         # floor(6 - 1.2)


def test_v0_pace_call_bound():
    assert es.pace_call_bound_v0(10, 3) == 260
    assert es.pace_call_bound_v0(10, 5) == 250
    assert es.pace_call_bound_v0(2, 3) == 52


def test_v0_pace_buckets_and_yield_update():
    q = es.within_day_rank(np.array([3.0, 1.0, 2.0, 2.0]))
    assert list(q) == pytest.approx([1.0, 0.0, 0.5, 0.5])
    assert list(es.bucket_of(q)) == [9, 0, 5, 5]
    w = tiny_world(c_by_day={d: [1.0, 2.0, 3.0] for d in range(6, 9)})
    s = es.make_schedule(w, 1.0, "original")
    surf = np.zeros(w.n, bool)
    surf[rid(w, "c", 6)] = True
    p = es.PacePolicyV0(5, 0.0)
    es.simulate(p, w, s, 1, surf)
    # day 6 calls the top (bucket 9, account c) and it surfaces: bucket 9 = 2 surfaced / 1 not
    assert p.trace[0]["calls"] >= 1
    assert p.s[9] >= 2


# ── NP quantile ──────────────────────────────────────────────────────────

def test_np_quantile():
    w = tiny_world()
    cal = w.c_cal[np.isin(w.day, es.CAL_DAYS)]          # 15 distinct values
    for k in (1, 2):
        tau = es.np_threshold(cal, k)
        assert (cal > tau).sum() == 5 * k
    assert es.np_threshold(cal, 3) == float("-inf")     # 15 values, 5k = 15 -> everything
    # NP then calls every evaluation account-day above tau
    tau = es.np_threshold(cal, 1)
    pol = es.NPPolicy(tau)
    rows = es.DayRows(d=6, ids=np.array([0, 1, 2]), c=np.array([tau, tau + 1e-6, 100.0]),
                      acct=np.array(ACCTS))
    assert pol.choose(rows, es.SimState(k=1, mass={})) == {1, 2}


# ── C credence ───────────────────────────────────────────────────────────

def test_credence_update_and_surfaced_boost():
    w = tiny_world(c_by_day={6: [1.0, 2.0, 3.0], 7: [1.0, 2.0, 3.0], 8: [3.0, 2.0, 1.0]})
    s = es.make_schedule(w, 1.0, "original")
    surf = np.zeros(w.n, bool)
    surf[rid(w, "c", 6)] = True                          # c surfaces on day 6
    pol = es.CredencePolicy(0.8)
    st = es.SimState(k=1, mass=s.mass)
    ids6 = s.by_day[6]
    r6 = es.DayRows(6, ids6, w.c[ids6], w.account[ids6])
    ch = pol.choose(r6, st)
    # q = (0, .5, 1); pi = .8*.5 + .2 q = (.4, .5, .6); priority = (0, .25, .6) -> c
    assert ch == {rid(w, "c", 6)}
    pol.observe(r6, ch, {i: bool(surf[i]) for i in ch}, st)
    assert pol.pi == pytest.approx({"a": 0.4, "b": 0.5, "c": 1.0})
    ids7 = s.by_day[7]
    r7 = es.DayRows(7, ids7, w.c[ids7], w.account[ids7])
    ch = pol.choose(r7, st)
    assert ch == {rid(w, "c", 7)}                        # pi_c = .8 + .2 = 1.0, priority 1.0
    pol.observe(r7, ch, {i: bool(surf[i]) for i in ch}, st)   # not surfaced -> halved
    assert pol.pi["c"] == pytest.approx(0.5 * (0.8 * 1.0 + 0.2 * 1.0))
    assert pol.pi["a"] == pytest.approx(0.8 * 0.4 + 0.2 * 0.0)
    assert pol.pi["b"] == pytest.approx(0.8 * 0.5 + 0.2 * 0.5)


def test_credence_inactive_account_keeps_pi():
    w = tiny_world()
    s = es.make_schedule(w, 1.0, "original")
    pol = es.CredencePolicy(0.9)
    pol.pi = {"a": 0.7}
    ids = np.array([rid(w, "b", 6), rid(w, "c", 6)])
    rows = es.DayRows(6, ids, w.c[ids], w.account[ids])
    ch = pol.choose(rows, es.SimState(k=1, mass=s.mass))
    pol.observe(rows, ch, {i: False for i in ch}, None)
    assert pol.pi["a"] == 0.7


# ── U, S, ORACLE spend exactly k ─────────────────────────────────────────

def test_uniform_selective_oracle_spend_k():
    w = tiny_world(executed=[("a", 7)])
    s = es.make_schedule(w, 1.0, "original")
    surf = np.zeros(w.n, bool)
    for pol in (es.UniformPolicy(), es.SelectivePolicy(), es.OraclePolicy(s.pos_ids)):
        called, calls = es.simulate(pol, w, s, 2, surf)
        assert sum(calls.values()) == 3 * 2              # 3 non-empty eval days x k
    called, _ = es.simulate(es.OraclePolicy(s.pos_ids), w, s, 1, surf)
    assert called[rid(w, "a", 7)]                        # lowest c, but ORACLE calls it first


# ── cluster bootstrap ────────────────────────────────────────────────────

def test_cluster_bootstrap_keeps_account_positives_together():
    W = es.cluster_weights(3, 200, seed=7)
    assert (W.sum(axis=1) == 3).all()
    npos = np.array([4.0, 1.0, 0.0])                    # account 0 has 4 positives
    hits = np.array([4.0, 0.0, 0.0])                    # all of account 0's are hit
    den = W @ npos
    # every replicate's positive count is a sum of whole accounts: 4 * n0 + 1 * n1
    assert set(np.unique(den)) <= {4 * i + j for i in range(4) for j in range(4)}
    r = es.boot_ratio(W, hits, npos)
    # explicit resampling of account lists gives the same replicate recalls
    rng = np.random.default_rng(7)
    idx = rng.integers(0, 3, size=(200, 3))
    for b in range(200):
        n = sum(npos[i] for i in idx[b])
        h = sum(hits[i] for i in idx[b])
        assert (math.isnan(r[b]) and n == 0) or r[b] == pytest.approx(h / n)


def test_cell_metrics_and_differences():
    w = tiny_world(executed=[("a", 6), ("a", 7), ("b", 8)])
    s = es.make_schedule(w, 1.0, "original")
    W = es.cluster_weights(len(w.labelled_accounts), 500, seed=3)
    called = np.zeros(w.n, bool)
    called[[rid(w, "a", 6), rid(w, "a", 7)]] = True
    surf = np.zeros(w.n, bool)
    surf[rid(w, "a", 6)] = True
    m = es.cell_metrics(w, s, called, surf, W)
    assert m["alloc"]["pt"] == pytest.approx(2 / 3) and m["det"]["pt"] == pytest.approx(1 / 3)
    lo, hi = m["alloc"]["ci"]
    assert lo <= m["alloc"]["pt"] <= hi
    assert m["honest_flag_rate"] == 0.0 and m["n_honest"] == 3      # account c, days 6-8
    z = es.cell_metrics(w, s, np.zeros(w.n, bool), surf, W)
    d = es.diff_est(m, z, "det", W)
    assert d["pt"] == pytest.approx(1 / 3)


# ── regime re-timers ─────────────────────────────────────────────────────

def test_subsample_rate():
    pos = list(range(10, 30))
    k50 = es.subsample_positives(pos, 0.5, es.SEED)
    k25 = es.subsample_positives(pos, 0.25, es.SEED)
    assert len(k50) == 10 and len(k25) == 5 and set(k50) <= set(pos)
    assert k50 == es.subsample_positives(list(reversed(pos)), 0.5, es.SEED)   # order-free
    assert es.subsample_positives(list(range(7)), 0.5, 1).__len__() == 4       # floor(3.5 + .5)


def test_burst_uniform_adversarial_placement():
    pos = list(range(23))
    b = es.place_burst(pos, es.SEED)
    days = sorted(set(b.values()))
    assert len(days) == 5 and set(b) == set(pos) and set(days) <= set(es.EVAL_DAYS)
    counts = sorted(list(b.values()).count(d) for d in days)
    assert counts == [4, 4, 5, 5, 5]                     # dealt evenly
    u = es.place_uniform(list(range(30)), es.SEED)
    assert sorted(set(u.values())) == list(es.EVAL_DAYS)
    mass = {d: float(d % 7) for d in es.EVAL_DAYS}       # highest: 6,13,20,27 (mass 6) then 12 (5)
    assert es.adversarial_days(mass) == [6, 13, 20, 27, 12]
    a = es.place_adversarial([1, 2, 3, 4, 5, 6], {1: 9, 2: 8, 3: 7, 4: 6, 5: 10, 6: 11}, mass)
    assert a == {4: 6, 3: 13, 2: 20, 1: 27, 5: 12, 6: 6}


def test_make_schedule_retimes_only_positives():
    w = tiny_world(executed=[("a", 6), ("b", 7)], attempted=[("b", 8)],
                   c_by_day={6: [0.5, 0.5, 9.0], 7: [0.5, 0.5, 0.1], 8: [0.5, 0.5, 0.2]})
    for pl in es.PLACEMENTS:
        s = es.make_schedule(w, 1.0, pl)
        assert len(s.pos_ids) == 2
        nonpos = np.setdiff1d(np.arange(w.n), s.pos_ids)
        assert (s.sim_day[nonpos] == w.day[nonpos]).all()          # others (and attempted) stay
        assert all(int(i) in set(s.by_day[int(s.sim_day[i])]) for i in s.pos_ids)
        assert sum(len(v) for v in s.by_day.values()) == w.n        # every row exactly once
    s = es.make_schedule(w, 0.5, "original")
    assert len(s.pos_ids) == 1
    gone = (set(np.where(w.is_exec)[0]) - set(s.pos_ids)).pop()
    assert s.sim_day[gone] == 0 and all(gone not in set(v) for v in s.by_day.values())
    # adversarial: honest (account c) mass 9.0 on day 6, 0.2 on 8, 0.1 on 7, 0 after -> days
    # [6, 8, 7, 9, 10]; positives by original day: a6 -> 6, b7 -> 8
    assert es.adversarial_days({d: float(w.c[w.honest & (w.day == d)].sum()) for d in es.EVAL_DAYS}) == [6, 8, 7, 9, 10]
    s = es.make_schedule(w, 1.0, "adversarial")
    assert int(s.sim_day[rid(w, "a", 6)]) == 6 and int(s.sim_day[rid(w, "b", 7)]) == 8
    assert int(s.sim_day[rid(w, "b", 8)]) == 8                       # attempted stays
    # a re-timed positive keeps its c and competes on its new day
    sb = es.make_schedule(w, 1.0, "burst5")
    p = rid(w, "b", 7)
    assert w.c[p] == 0.5 and p in set(sb.by_day[int(sb.sim_day[p])])
    assert sb.mass[int(sb.sim_day[p])] >= 0.5


# ── theta and refusal handling ───────────────────────────────────────────

def test_theta_and_refusal_handling():
    oc = np.array(["scored", "scored", "refused", "errored", "missing", "scored"], dtype=object)
    sc = np.array([50.0, 49.0, np.nan, np.nan, np.nan, 100.0])
    assert list(es.surfaced_vector(oc, sc, 50)) == [True, False, True, False, False, True]
    assert list(es.surfaced_vector(oc, sc, 50, refusal_as_zero=True)) == [True, False, False, False, False, True]
    assert list(es.surfaced_vector(oc, sc, 49)) == [True, True, True, False, False, True]
    e = es.e_for_auroc(oc, sc, 100.0, 0.0)
    assert list(e) == [50.0, 49.0, 100.0, 0.0, 0.0, 100.0]
    e0 = es.e_for_auroc(oc, sc, 0.0, None)
    assert e0[2] == 0.0 and math.isnan(e0[3]) and math.isnan(e0[4])
    honest = np.array([True, True, True, True, True, False])
    day = np.array([6, 7, 8, 9, 11, 6])
    # honest days 6-10 with a value: 50, 49, 100 (refused); errored excluded; day 11 excluded
    assert es.theta95(oc, sc, honest, day) == pytest.approx(np.percentile([50, 49, 100], 95))


def test_errored_call_counts_but_does_not_surface():
    w = tiny_world(executed=[("c", 6)], outcomes={("c", 6): "errored"})
    s = es.make_schedule(w, 1.0, "original")
    surf = es.surfaced_vector(w.outcome, w.score, es.THETA)
    called, calls = es.simulate(es.SelectivePolicy(), w, s, 1, surf)
    W = es.cluster_weights(1, 50, 1)
    m = es.cell_metrics(w, s, called, surf, W)
    assert m["alloc"]["pt"] == 1.0 and m["det"]["pt"] == 0.0 and m["calls"] == 3


def test_refused_surfaces_and_feeds_credence():
    w = tiny_world(c_by_day={6: [1.0, 2.0, 3.0], 7: [1.0, 2.0, 3.0]}, outcomes={("c", 6): "refused"})
    surf = es.surfaced_vector(w.outcome, w.score, es.THETA)
    assert surf[rid(w, "c", 6)]
    pol = es.CredencePolicy(0.8)
    es.simulate(pol, w, es.make_schedule(w, 1.0, "original"), 1, surf)
    # day 6 refused -> pi_c = 1; day 7: (.8 + .2) = 1.0, called, scored 10 -> 0.5;
    # day 8: .8 * .5 + .2 * 1 = .6, called, not surfaced -> 0.3
    assert pol.pi["c"] == pytest.approx(0.3)


def test_incomplete_expensive_table_refused(tmp_path):
    _, exp, _ = tiny_tables()
    p = tmp_path / "x.expensive.parquet"
    exp.to_parquet(p, index=False)
    (tmp_path / "x.expensive.meta.json").write_text(json.dumps({"complete": False}))
    with pytest.raises(SystemExit):
        es.load_expensive(p, allow_incomplete=False)
    df, meta = es.load_expensive(p, allow_incomplete=True)
    assert len(df) == 9 and meta["complete"] is False


def test_missing_expensive_rows_refused_unless_allowed():
    cheap, exp, labels = tiny_tables()
    exp = exp.iloc[1:]
    with pytest.raises(SystemExit):
        es.build_world(cheap, exp, labels, {}, False)
    w = es.build_world(cheap, exp, labels, {}, True)
    assert (w.outcome == "missing").sum() == 1


def test_read_labels_precedence_and_crosscheck(tmp_path):
    lab = pd.DataFrame({"account": ["a", "a", "b"], "date": [DATES[5], DATES[5], DATES[6]],
                        "scenario": ["s", "s", "s"], "outcome": ["attempted", "executed", "attempted"]})
    p = tmp_path / "labels.parquet"
    lab.to_parquet(p, index=False)
    units = [(a, d) for a in ACCTS for d in DATES]
    L = es.read_labels(p, units)
    assert L["executed"] == {("a", DATES[5])} and L["attempted"] == {("b", DATES[6])}
    assert L["labelled_accounts"] == ["a", "b"]
