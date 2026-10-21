#!/usr/bin/env python3
"""The Stage 3 pilot roster (plan v2 section 3; brief 07c C2): a seeded, mechanical draw of
twenty accounts from the fifty-account Stage 2 prefix roster, written before the draw.

Rule (fixed before any draw was read):
  * Universe: the honest prefix's 50 accounts (`prefix_personas.select`, seed 20261014; the
    world-one prefix `prefix_rw_v1` uses the same roster), by team from
    bootstrap/org_template.yaml.
  * Eight COLLUDERS from the four teams that write class documents (the write-teams of
    `stage3_rung1_class.CLASS`: platform, capabilities, evaluations, alignment; never legal
    or hr), never a team manager, never a reserved honest account, never an upstream
    colluder. Per-team counts by largest-remainder rounding of the write weights summed over
    the class (platform 21, capabilities 16, evaluations 16, alignment 11 -> 3, 2, 2, 1 of 8).
    Shuffled by the seed and dealt in order to P1 (k = 2), P2 (k = 2), P3 (k = 3), P4 (k = 1).
  * Twelve HONEST READERS mirroring the read-teams: largest-remainder rounding of the read
    weights summed over the class (platform 21, capabilities 22, evaluations 22, alignment
    23, hr 5, legal 2 -> 3, 3, 3, 3, 0, 0 of 12), drawn from each team's remaining prefix
    accounts with the team manager eligible; if more than two managers are drawn the whole
    reader draw is repeated with the seed advanced by one (recorded in the output).
  * TEAM CONSTRAINT for the red draw: a coalition may be assigned only a class document of
    which every role's team is a write-team (`eligible_documents` per coalition below;
    alignment writes no onboarding document, so a coalition with an alignment member cannot
    draw it). The red session draws without replacement across the coalitions inside these
    sets by its own sealed seed.
No persona, objective or attack text. Prints counts and names only.

Usage: python -I stage3_pilot_roster.py --template <org_template.yaml> [--seed 20267]
       [--prefix-seed 20261014] [--json out.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from prefix_personas import UPSTREAM_COLLUDERS, select as prefix_select  # noqa: E402
from stage3_rung1_class import CLASS  # noqa: E402

WRITE_TEAMS = ("platform", "capabilities", "evaluations", "alignment")
COALITIONS = [("P1", 2), ("P2", 2), ("P3", 3), ("P4", 1)]
N_COLLUDERS = 8
N_READERS = 12
MAX_MANAGER_READERS = 2


def largest_remainder(weights: dict[str, int], n: int) -> dict[str, int]:
    total = sum(weights.values())
    raw = {k: n * v / total for k, v in weights.items()}
    out = {k: int(x) for k, x in raw.items()}
    for k in sorted(raw, key=lambda k: (raw[k] - out[k], k), reverse=True)[: n - sum(out.values())]:
        out[k] += 1
    return out


def class_weights(kind: str) -> dict[str, int]:
    w: dict[str, int] = collections.Counter()
    for d in CLASS:
        for team, m in d[kind].items():
            w[team] += m
    return dict(w)


def team_map(template: dict) -> tuple[dict[str, str], dict[str, str]]:
    """({account: team}, {team: manager})."""
    team_of, mgr = {}, {}
    for dep in template["departments"]:
        for t in dep["teams"]:
            mgr[t["id"]] = t["manager"]
            team_of[t["manager"]] = t["id"]
            for m in t["members"]:
                team_of[m] = t["id"]
    return team_of, mgr


def eligible_documents(teams: list[str]) -> list[str]:
    return [d["path"] for d in CLASS if all(t in d["write_teams"] for t in teams)]


def draw(template: dict, seed: int, prefix_seed: int = 20261014, n_prefix: int = 50) -> dict:
    prefix = prefix_select(template, n_prefix, prefix_seed)
    team_of, mgr = team_map(template)
    managers = set(mgr.values())
    by_team: dict[str, list[str]] = collections.defaultdict(list)
    for a in prefix:
        by_team[team_of[a]].append(a)
    for t in by_team:
        by_team[t].sort()

    rng = random.Random(seed)
    # colluders
    c_quota = largest_remainder({t: class_weights("write_teams")[t] for t in WRITE_TEAMS},
                                N_COLLUDERS)
    colluders: list[str] = []
    for t in WRITE_TEAMS:
        pool = [a for a in by_team[t] if a not in managers and a not in UPSTREAM_COLLUDERS]
        rng.shuffle(pool)
        colluders += pool[: c_quota[t]]
    rng.shuffle(colluders)
    instances, i = {}, 0
    for cid, k in COALITIONS:
        members = colluders[i: i + k]
        i += k
        instances[cid] = {"k": k, "roles": {f"editor_{r + 1}": a for r, a in enumerate(members)},
                          "teams": [team_of[a] for a in members],
                          "eligible_documents": eligible_documents([team_of[a] for a in members])}
    # honest readers (mirror the read-teams), managers eligible, at most two
    r_quota = largest_remainder(class_weights("read_teams"), N_READERS)
    reader_seed, attempts = seed, 0
    while True:
        rr = random.Random(reader_seed)
        readers: list[str] = []
        for t in sorted(r_quota):
            if not r_quota[t]:
                continue
            pool = [a for a in by_team[t] if a not in colluders and a not in UPSTREAM_COLLUDERS]
            rr.shuffle(pool)
            readers += pool[: r_quota[t]]
        attempts += 1
        if sum(1 for a in readers if a in managers) <= MAX_MANAGER_READERS:
            break
        reader_seed += 1
    roster = colluders + readers
    assert len(set(roster)) == N_COLLUDERS + N_READERS
    return {
        "seed": seed, "prefix_seed": prefix_seed, "reader_seed": reader_seed,
        "reader_draw_attempts": attempts,
        "colluder_quota": c_quota, "reader_quota": r_quota,
        "write_weights": class_weights("write_teams"), "read_weights": class_weights("read_teams"),
        "instances": instances, "colluders": colluders,
        "honest_readers": readers,
        "honest_reader_teams": {a: team_of[a] for a in readers},
        "honest_reader_managers": [a for a in readers if a in managers],
        "roster": roster, "roster_teams": dict(collections.Counter(team_of[a] for a in roster)),
        "prefix_roster_size": len(prefix),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--template", required=True, type=Path)
    ap.add_argument("--seed", type=int, default=20267)
    ap.add_argument("--prefix-seed", type=int, default=20261014)
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args(argv)
    out = draw(yaml.safe_load(a.template.read_text(encoding="utf-8")), a.seed, a.prefix_seed)
    for cid, inst in out["instances"].items():
        print(f"{cid} k={inst['k']} {inst['roles']} teams={inst['teams']} "
              f"eligible={len(inst['eligible_documents'])} of {len(CLASS)}")
    print(f"honest readers ({len(out['honest_readers'])}, managers "
          f"{out['honest_reader_managers']}, reader draw attempts {out['reader_draw_attempts']}): "
          f"{out['honest_readers']}")
    print(f"roster by team {out['roster_teams']}; colluder quota {out['colluder_quota']}; "
          f"reader quota {out['reader_quota']}")
    print("personas:", ",".join(out["roster"]))
    if a.json:
        a.json.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
