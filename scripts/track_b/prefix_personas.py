#!/usr/bin/env python3
"""Select the honest prefix's 50 accounts from the org template (Stage 2a, T6).

Rule (written before the draw): sample within each of the six teams in proportion to team
size (largest-remainder rounding to N), always keep each team's manager, never include the
eight upstream colluders whose footprints the author has seen (PLAN.md section 4), never
include holdout-cohort accounts, seed random.Random(20261014). The threat-role accounts
named in bootstrap/insider_assignment.yaml are NOT excluded (they run honest under
--no-insiders), except the eight upstream colluders. Prints the comma-separated list and a
per-team / per-group summary.

Usage: python -I prefix_personas.py --template <org_template.yaml> [--n 50] [--seed 20261014]
"""
from __future__ import annotations
import argparse, random, collections
import yaml

UPSTREAM_COLLUDERS = {"deepa.g6", "ivan.o", "marco.g35", "marco.n28", "kofi.s54", "sam.k47", "sara.c56", "yuki.v49"}

def select(template: dict, n: int, seed: int) -> list[str]:
    acc = {a["id"]: a for a in template["accounts"]}
    teams = []
    for dep in template["departments"]:
        for t in dep["teams"]:
            members = [m for m in t["members"] if m not in UPSTREAM_COLLUDERS and acc.get(m, {}).get("cohort") != "holdout"]
            mgr = t["manager"]
            if mgr in UPSTREAM_COLLUDERS:
                mgr = None
            teams.append((t["id"], mgr, members))
    sizes = [(1 if mgr else 0) + len(m) for _, mgr, m in teams]
    total = sum(sizes)
    raw = [n * s / total for s in sizes]
    quota = [int(x) for x in raw]
    for i in sorted(range(len(teams)), key=lambda i: raw[i] - quota[i], reverse=True)[: n - sum(quota)]:
        quota[i] += 1
    rng = random.Random(seed)
    chosen: list[str] = []
    for (tid, mgr, members), q in zip(teams, quota):
        pool = sorted(members)
        rng.shuffle(pool)
        take = ([mgr] if mgr else []) + pool[: q - (1 if mgr else 0)]
        chosen += take
    assert len(chosen) == n and len(set(chosen)) == n, (len(chosen), n)
    assert not (set(chosen) & UPSTREAM_COLLUDERS)
    return chosen

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20261014)
    ns = ap.parse_args()
    template = yaml.safe_load(open(ns.template))
    chosen = select(template, ns.n, ns.seed)
    acc = {a["id"]: a for a in template["accounts"]}
    team_of = {m: t["id"] for dep in template["departments"] for t in dep["teams"] for m in [t["manager"]] + t["members"]}
    print(",".join(chosen))
    print("per team:", dict(collections.Counter(team_of[c] for c in chosen)))
    print("per group:", dict(collections.Counter(g for c in chosen for g in acc[c].get("groups", []))))
    print("managers:", [c for c in chosen if any(t["manager"] == c for dep in template["departments"] for t in dep["teams"])])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
