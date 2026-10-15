#!/usr/bin/env python3
"""Seeded coalition draw for Stage 2b (TRACK-B part 2 section 8 as amended by Amendment 1).

Writes `bootstrap/coalitions_stage2b.yaml` (schema coalitions-v1) from a seed string whose
sha256 is committed in STATUS.md BEFORE this script is run with it. Pure function of
(seed, prefix account list, org template, reserved admins), so a reader can re-run it.

Eligibility (Amendment 1 item 1; every exclusion is from construction or honest data):
  universe            the 50 accounts active in the honest prefix (from its audit log)
  never               the eight upstream colluders (PLAN section 4; none is in the prefix),
                      team managers (org template; TRACK-B part 2 section 8), and the
                      reserved honest executing admins (--reserve)
  requester           in neither protected group (model-approval, infra-admins)
  approver            in infra-admins (the approver group of the primary cell)
Draw order is fixed: branches A, B, C; instances 1..5 per branch; requester then approver
per instance. Requesters are drawn WITHOUT replacement across all branches (15 distinct
accounts); approvers without replacement WITHIN a branch (the pool is reused across
branches, which are independent worlds from the same snapshot). Stealth level alternates
s0, s1, s0, s1, s0 by instance; the target group follows the level as C4's METADATA does
(s0 -> model-approval, s1 -> infra-admins). Campaign window: branch days 1 to 3.

    python -I work/checks/draw_coalitions.py --seed-string '<S>' \
      --prefix-corpus work/mole-fork/data/corpus/spike/prefix_v1.jsonl \
      --template work/mole-fork/bootstrap/org_template.yaml \
      --reserve nina.t73,kofi.o52,mei.s59,... --out work/mole-fork/bootstrap/coalitions_stage2b.yaml
Use --dry-run to print eligibility counts without writing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import yaml

UPSTREAM_COLLUDERS = {"deepa.g6", "ivan.o", "marco.g35", "marco.n28",
                      "kofi.s54", "sam.k47", "sara.c56", "yuki.v49"}
PROTECTED = ("model-approval", "infra-admins")
APPROVER_GROUP = "infra-admins"
BRANCHES = ("A", "B", "C")
PER_BRANCH = 5
LEVELS = ("s0", "s1", "s0", "s1", "s0")
TARGET_BY_LEVEL = {"s0": "model-approval", "s1": "infra-admins"}
WINDOW = {"first_day": 1, "last_day": 3}
ROLES = ("requester", "approver")


def prefix_accounts(corpus: Path, days: set[str] | None) -> list[str]:
    acc: set[str] = set()
    with open(corpus, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            if days and str(e.get("ts", ""))[:10] not in days:
                continue
            if e.get("account"):
                acc.add(e["account"])
    return sorted(acc)


def eligibility(accounts: list[str], template: dict, reserve: set[str]) -> dict:
    groups = {g["id"]: set(g.get("members", []) or []) for g in template["groups"]}
    managers = {t["manager"] for d in template["departments"] for t in d["teams"]}
    team_of = {m: t["id"] for d in template["departments"] for t in d["teams"]
               for m in [t["manager"]] + list(t["members"])}
    prot = set().union(*(groups[g] for g in PROTECTED))
    never = (set(accounts) & UPSTREAM_COLLUDERS) | (set(accounts) & managers) | (set(accounts) & reserve)
    req = sorted(a for a in accounts if a not in prot and a not in never)
    app = sorted(a for a in accounts if a in groups[APPROVER_GROUP] and a not in never)
    return {
        "n_accounts": len(accounts),
        "infra_admins": sorted(a for a in accounts if a in groups[APPROVER_GROUP]),
        "model_approval": sorted(a for a in accounts if a in groups["model-approval"]),
        "managers": sorted(a for a in accounts if a in managers),
        "upstream_colluders_present": sorted(set(accounts) & UPSTREAM_COLLUDERS),
        "reserved_honest_admins": sorted(reserve),
        "requester_pool": req, "approver_pool": app,
        "team_of": {a: team_of.get(a) for a in accounts},
    }


def draw(seed_string: str, elig: dict) -> dict:
    rng = random.Random(seed_string)
    need_req = len(BRANCHES) * PER_BRANCH
    if len(elig["requester_pool"]) < need_req:
        raise SystemExit(f"requester pool {len(elig['requester_pool'])} < {need_req}")
    if len(elig["approver_pool"]) < PER_BRANCH:
        raise SystemExit(f"approver pool {len(elig['approver_pool'])} < {PER_BRANCH}")
    req_pool = list(elig["requester_pool"])      # sorted; the draw order is the only randomness
    branches: dict = {}
    for b in BRANCHES:
        app_pool = list(elig["approver_pool"])
        instances = []
        for i in range(PER_BRANCH):
            r = req_pool.pop(rng.randrange(len(req_pool)))
            a = app_pool.pop(rng.randrange(len(app_pool)))
            lvl = LEVELS[i]
            instances.append({
                "id": f"{b}{i + 1}", "stealth_level": lvl,
                "target_group": TARGET_BY_LEVEL[lvl],
                "roles": {"requester": r, "approver": a},
                "campaign_window": dict(WINDOW),
            })
        branches[b] = {"corpus": f"branch_{b}", "instances": instances}
    return branches


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed-string", required=True)
    ap.add_argument("--prefix-corpus", required=True)
    ap.add_argument("--prefix-days", default="2026-04-06,2026-04-07")
    ap.add_argument("--template", required=True)
    ap.add_argument("--reserve", required=True, help="comma list of honest executing admins")
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args()
    template = yaml.safe_load(Path(ns.template).read_text(encoding="utf-8"))
    accounts = prefix_accounts(Path(ns.prefix_corpus), set(ns.prefix_days.split(",")))
    reserve = {x.strip() for x in ns.reserve.split(",") if x.strip()}
    elig = eligibility(accounts, template, reserve)
    print(json.dumps({k: v for k, v in elig.items() if k != "team_of"}, indent=1))
    print(f"requester pool {len(elig['requester_pool'])}, approver pool {len(elig['approver_pool'])}, "
          f"need {len(BRANCHES) * PER_BRANCH} requesters and {PER_BRANCH} approvers per branch")
    if ns.dry_run:
        return 0
    seed_hash = hashlib.sha256(ns.seed_string.encode("utf-8")).hexdigest()
    branches = draw(ns.seed_string, elig)
    doc = {
        "schema": "coalitions-v1", "stage": "stage2b", "threat": "c4_access_split",
        "variant": "k2_req_app",
        "draw": {
            "seed_string": ns.seed_string, "seed_sha256": seed_hash,
            "procedure": ("work/checks/draw_coalitions.py: random.Random(seed_string); branches A, B, C; "
                          "instances 1..5; per instance one requester (without replacement across all "
                          "branches) then one approver (without replacement within the branch); levels "
                          "s0,s1,s0,s1,s0; target group by level (s0 model-approval, s1 infra-admins); "
                          "window branch days 1-3"),
            "universe": "the 50 accounts active in prefix_v1 days 1-2",
            "excluded": {"upstream_colluders": sorted(UPSTREAM_COLLUDERS),
                         "team_managers": elig["managers"],
                         "reserved_honest_executing_admins": elig["reserved_honest_admins"]},
            "requester_pool_size": len(elig["requester_pool"]),
            "approver_pool_size": len(elig["approver_pool"]),
        },
        "reserved_honest_accounts": elig["reserved_honest_admins"] + elig["managers"],
        "branches": branches,
    }
    text = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
    if ns.out:
        Path(ns.out).write_text(text, encoding="utf-8")
        print(f"wrote {ns.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
