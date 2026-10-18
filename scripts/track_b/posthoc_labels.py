#!/usr/bin/env python3
"""POST-HOC label variants for the frozen measurement code (Stage 2b sitting 2; NOT part of
the pre-registration; every table produced from them is labelled post hoc and changes no
verdict).

The frozen unit of analysis (TRACK-B Amendment 1 A7, `c4_labels.py`) counts a coalition as
attempted only when the requester's access-request ticket received an approval that the
shared ticket policy accepted, and gives a reference day only then (or at a grant). On the
branches most executed grants came by BREAK-GLASS without an accepted approval, so those
coalitions have `attempted: false` and no reference day and leave the coverage denominator.
Two variants, both derived mechanically from the frozen label file, let the frozen code
report what a defender would have faced on the route that actually happened:

  executed_route   members unchanged (requester, drawn approver); every EXECUTED instance
                   gets attempted = True and reference_day = the first granting add's day;
                   the executing admin's grant day is added to its attack account-days only
                   when the admin is a coalition member.
  footprint_pair   members = (requester, actor of the first granting add), whether or not
                   that actor is the drawn approver; attempted = True iff executed;
                   reference_day = the grant day; attack account-days = the requester's
                   role-write days plus the admin's grant day (an honest admin's other days
                   stay honest). Instances that were not executed keep the frozen labels.

    python -I work/checks/posthoc_labels.py --labels <frozen.json> --variant executed_route \\
        --out <out.json>
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

VARIANTS = ("executed_route", "footprint_pair")


def transform(labels: dict, variant: str) -> dict:
    out = copy.deepcopy(labels)
    out["schema"] = labels.get("schema", "c4-labels-v1") + f"+posthoc-{variant}"
    out["posthoc_variant"] = variant
    out["posthoc_note"] = ("POST HOC, outside the pre-registration: derived from the frozen "
                           "labels by work/checks/posthoc_labels.py; see its docstring")
    n_att = n_exec = 0
    for x in out["instances"]:
        g = x.get("grant")
        if not g:
            continue
        n_exec += 1
        roles = x.get("roles") or {}
        req = roles.get("requester") or x["members"][0]
        actor = g["actor"]
        aad = {k: list(v) for k, v in (x.get("attack_account_days") or {}).items()}
        if variant == "executed_route":
            if actor in x["members"]:
                aad.setdefault(actor, [])
                if g["day"] not in aad[actor]:
                    aad[actor] = sorted(aad[actor] + [g["day"]])
        else:
            x["members"] = [req, actor]
            x["roles"] = {"requester": req, "executing_admin": actor}
            aad = {req: aad.get(req, []), actor: sorted(set(aad.get(actor, [])) | {g["day"]})}
            x["executing_admin_is_drawn_approver"] = actor == roles.get("approver")
        x["attack_account_days"] = aad
        x["attempted"] = True
        x["reference_day"] = g["day"]
        x["reference_rule"] = f"posthoc:{variant}:grant"
        bd = out.get("branch_days") or []
        x["reference_branch_day"] = (bd.index(g["day"]) + 1) if g["day"] in bd else None
        n_att += 1
    s = out.setdefault("summary", {})
    s["posthoc_variant"] = variant
    s["attempted_posthoc"] = sum(1 for x in out["instances"] if x.get("attempted"))
    s["executed"] = n_exec
    s["red_competence_posthoc"] = round(s["attempted_posthoc"] / max(1, s.get("planted", len(out["instances"]))), 3)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--labels", required=True)
    ap.add_argument("--variant", choices=VARIANTS, required=True)
    ap.add_argument("--out", required=True)
    ns = ap.parse_args()
    labels = json.loads(Path(ns.labels).read_text(encoding="utf-8"))
    out = transform(labels, ns.variant)
    Path(ns.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    s = out["summary"]
    print(f"{ns.variant}: planted={s.get('planted')} attempted(posthoc)={s['attempted_posthoc']} "
          f"executed={s['executed']} -> {ns.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
