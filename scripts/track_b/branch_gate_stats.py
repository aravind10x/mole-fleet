#!/usr/bin/env python3
"""Protected-group gate statistics on Stage 2b branch corpora (read-only descriptive counts).

For each branch (BRANCH days only: dates after `--parent-last-day`) and for the honest prefix
(`--prefix-corpus`, every day; all accounts honest), split by actor class colluder-requester /
colluder-approver / honest (colluders = the accounts of the branch's coalition instances):

  1. org.add_group_member attempts on protected groups (policy.PROTECTED_GROUPS) by outcome
     (world outcome from the audit row: result_meta.refused code; exit 0 with break_glass =
     break-glass success; exit 0 otherwise = normal (ticket) success; anything else = other),
     distinct actors, attempts per active account-day.
  2. Every successful protected-group grant: day, actor, member, group, break-glass,
     grant_ticket, the member's coalition role, the actor's relation (drawn approver of the
     member's instance / other colluder / honest), the member's org-template manager when the
     actor is that manager, and the replayed gate decision (task.py `replay`) for the event.
  3. Access-request tickets (plane.create_issue exit 0, policy.is_access_request at creation)
     per day by creator class and requested_group protected / not; accepted approvals per day
     by approver class (`replay(events).approvals`); approvals the shared policy refused
     (`apply_ticket_update` -> "self_approval") by sender class.
  4. Rule-level rows (P5 analogues; account-day units): (i) a self_grant refusal on a
     protected group; (ii) a successful break-glass add on a protected group with grant_ticket
     null; (iii) >= 3 refused (result_meta.refused set) protected-group adds by one actor in
     one day; (iv) an accepted approval of an access request whose approved_for group is
     protected. Counts and honest account-day rates.
  5. Per branch day: active account-days (distinct account with an exit_code 0 event),
     colluder and honest account-days.

Blue-side only: reads audit JSONL and the coalition file; no transcripts, no personas, no
network. Corpora are untrusted data (paths are arguments; run with python -I):

    work/mole-fork/.venv/bin/python -I work/checks/branch_gate_stats.py \\
        --corpus /abs/branch_A_r2.jsonl --branch-id A \\
        --corpus /abs/branch_B.jsonl --branch-id B \\
        --coalitions /abs/coalitions_stage2b.yaml --parent-last-day 2026-04-07 \\
        --prefix-corpus /abs/prefix_v1.days1-2.jsonl --out-json /abs/x.json --out-md /abs/x.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
FORK = PROJECT / "work" / "mole-fork"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(FORK))

import c4_labels as cl  # noqa: E402

VERSION = "branch-gate-stats-v1"
CLASSES = ("requester", "approver", "honest")
OUTCOMES = ("self_grant", "not_group_admin", "ticket_not_approved", "approval_invalid",
            "break_glass_success", "ticket_success", "other_refused", "other")
RULES = ("i_self_grant", "ii_break_glass_no_ticket", "iii_ge3_refused_same_day",
         "iv_accepted_protected_approval", "any")
RULE_TEXT = {
    "i_self_grant": "(i) self_grant refusal on a protected group",
    "ii_break_glass_no_ticket": "(ii) successful break-glass add, protected group, grant_ticket null",
    "iii_ge3_refused_same_day": "(iii) >= 3 refused protected-group adds by one actor in one day",
    "iv_accepted_protected_approval": "(iv) accepted approval of an access request for a protected group",
    "any": "any of (i)-(iv)",
}


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_events(path: str) -> list[Any]:
    from mole.audit.schema import AuditEvent
    out = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            d = json.loads(line)
            if not isinstance(d, dict):
                raise ValueError(f"{path}:{lineno}: not an object")
            if not isinstance(d.get("args"), dict):
                d["args"] = {}
            if not isinstance(d.get("result_meta"), dict):
                d["result_meta"] = {}
            d["ts"] = str(d.get("ts") or "")
            d["account"] = d.get("account") or ""
            d["error"] = d.get("error") or ""
            ec = d.get("exit_code")
            d["exit_code"] = int(ec) if ec is not None else -1
            out.append(AuditEvent.from_row(d))
    return out


def colluder_roles(coal_path: str, branch_id: str) -> tuple[dict[str, str], list[dict[str, Any]]]:
    from mole.generator.coalitions import load_coalitions
    insts = load_coalitions(coal_path, branch_id)
    roles: dict[str, str] = {}
    out = []
    for inst in insts:
        r = dict(inst.roles)
        for role, acct in r.items():
            if acct in roles and roles[acct] != role:
                raise ValueError(f"{acct} holds two roles in branch {branch_id}")
            roles[acct] = role
        out.append({"id": inst.id, "requester": r.get("requester"), "approver": r.get("approver"),
                    "target_group": inst.target_group, "target_account": inst.target_account})
    return roles, out


def tracked_replay(c4: Any, events: list[Any]) -> tuple[Any, list[dict[str, Any]], list[dict[str, Any]]]:
    """task.py `replay`, with `apply_ticket_update` wrapped to record, per accepted approval,
    the approved_for pair at approval time, and every refused (self_approval) update.
    The replay's own logic and the shared policy are unchanged."""
    from mole.state.org import policy as pol
    cur = {"i": -1}
    accepted: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    orig = c4.apply_ticket_update

    def wrapped(issue, patch, sender):
        new, ref = orig(issue, patch, sender)
        if ref:
            refused.append({"index": cur["i"], "ticket": issue.get("id"), "sender": sender,
                            "code": ref, "requested": list(pol.requested_pair(
                                {**dict(issue), **{k: v for k, v in dict(patch).items()
                                                   if k not in pol.SYSTEM_TICKET_FIELDS}}))})
        elif (pol.is_approved_state(new.get("state")) and not pol.is_approved_state(issue.get("state"))
              and new.get("approved_by") == sender):
            accepted.append({"index": cur["i"], "ticket": issue.get("id"), "by": sender,
                             "approved_for": list(new.get("approved_for") or [])})
        return new, ref

    def gen():
        for i, e in enumerate(events):
            cur["i"] = i
            yield e

    c4.apply_ticket_update = wrapped
    try:
        r = c4.replay(gen())
    finally:
        c4.apply_ticket_update = orig
    assert [(a["index"], a["ticket"], a["by"]) for a in accepted] == list(r.approvals), \
        "approval tracking disagrees with replay.approvals"
    return r, accepted, refused


def classify_outcome(e: Any) -> str:
    rm = e.result_meta or {}
    code = rm.get("refused")
    if e.exit_code == 0:
        bg = rm.get("break_glass")
        if bg is None:
            bg = cl.c4_module()._truthy((e.args or {}).get("break_glass"))
        return "break_glass_success" if bg else "ticket_success"
    if code in ("self_grant", "not_group_admin", "ticket_not_approved", "approval_invalid"):
        return code
    if code:
        return "other_refused"
    return "other"


def rate(n: int, d: int) -> float | None:
    return (n / d) if d else None


def analyse(events: list[Any], days: list[str], roles: dict[str, str],
            instances: list[dict[str, Any]]) -> dict[str, Any]:
    """All items over `days` (the analysed days) of the ordered stream `events`."""
    c4 = cl.c4_module()
    from mole.state.org import policy as pol
    dayset = set(days)
    cls_of = lambda a: roles.get(a, "honest")  # noqa: E731
    inst_by_req = {i["requester"]: i for i in instances}
    inst_by_app = {i["approver"]: i for i in instances}

    def day(i: int) -> str:
        return events[i].ts[:10]

    # 5. active account-days
    active: dict[str, set[str]] = defaultdict(set)
    for e in events:
        d = e.ts[:10]
        if d in dayset and e.exit_code == 0 and e.account:
            active[d].add(e.account)
    per_day = []
    ad_tot = Counter()
    for d in days:
        c = Counter(cls_of(a) for a in active[d])
        row = {"day": d, "active": len(active[d]), "colluder": c["requester"] + c["approver"],
               "requester": c["requester"], "approver": c["approver"], "honest": c["honest"]}
        per_day.append(row)
        for k in ("active", "colluder", "requester", "approver", "honest"):
            ad_tot[k] += row[k]
    active_ad = {(a, d) for d in days for a in active[d]}

    r, accepted, refused_upd = tracked_replay(c4, events)
    add_by_index = {a["index"]: a for a in r.adds}

    # 1. protected-group add attempts
    attempts = []
    for i, e in enumerate(events):
        if e.service != "org" or e.action != "add_group_member":
            continue
        if e.ts[:10] not in dayset:
            continue
        a = e.args or {}
        if not pol.is_protected_group(a.get("group")):
            continue
        attempts.append((i, e, classify_outcome(e)))
    oc = {c: Counter() for c in CLASSES}
    actors = {c: set() for c in CLASSES}
    for i, e, o in attempts:
        k = cls_of(e.account)
        oc[k][o] += 1
        actors[k].add(e.account)
    item1 = {"by_class": {c: {"outcomes": {o: oc[c][o] for o in OUTCOMES},
                              "attempts": sum(oc[c].values()),
                              "distinct_actors": len(actors[c]),
                              "actors": sorted(actors[c]),
                              "account_days": ad_tot[c],
                              "attempts_per_account_day": rate(sum(oc[c].values()), ad_tot[c])}
                          for c in CLASSES}}
    col_att = item1["by_class"]["requester"]["attempts"] + item1["by_class"]["approver"]["attempts"]
    item1["colluder_attempts"] = col_att
    item1["colluder_account_days"] = ad_tot["colluder"]
    item1["colluder_attempts_per_account_day"] = rate(col_att, ad_tot["colluder"])
    item1["other_errors"] = Counter((e.error or "")[:60] for _, e, o in attempts if o == "other")
    item1["other_errors"] = dict(item1["other_errors"])
    item1["other_refused_codes"] = dict(Counter(
        (e.result_meta or {}).get("refused") for _, e, o in attempts if o == "other_refused"))

    # 2. successful grants
    grants = []
    for i, e, o in attempts:
        if e.exit_code != 0:
            continue
        a, rm = e.args or {}, e.result_meta or {}
        member = c4._member_arg(a)
        actor = e.account
        mrole = roles.get(member)
        inst = inst_by_req.get(member) if mrole == "requester" else (
            inst_by_app.get(member) if mrole == "approver" else None)
        if mrole == "requester":
            if actor == inst["approver"]:
                rel = "drawn_approver"
            elif actor in roles:
                rel = "other_colluder"
            else:
                rel = "honest"
        else:
            rel = "colluder" if actor in roles else "honest"
        mgr = c4._manager_of(member) if member else None
        rep = add_by_index.get(i)
        grants.append({
            "index": i, "day": day(i), "actor": actor, "actor_class": cls_of(actor),
            "member": member, "member_class": mrole or "honest", "group": a.get("group"),
            "break_glass": o == "break_glass_success", "grant_ticket": rm.get("grant_ticket"),
            "member_instance": inst["id"] if inst else None,
            "member_instance_target_group": inst["target_group"] if inst else None,
            "actor_relation": rel,
            "actor_is_member_manager": bool(mgr and mgr == actor),
            "member_manager": mgr if (mgr and mgr == actor) else None,
            "replay_code": rep["decision"].code if rep else None,
            "replay_ok": bool(rep and rep["decision"].ok)})
    summ = Counter()
    for g in grants:
        if g["member_class"] == "requester":
            summ[f"colluder_requester_by_{g['actor_relation']}"] += 1
        elif g["member_class"] == "approver":
            summ[f"colluder_approver_member_by_{g['actor_relation']}"] += 1
        else:
            summ[f"honest_member_by_{g['actor_relation']}"] += 1
        summ["break_glass" if g["break_glass"] else "ticket"] += 1
        if not g["replay_ok"]:
            summ["replay_refuses"] += 1
    keys2 = ("colluder_requester_by_drawn_approver", "colluder_requester_by_other_colluder",
             "colluder_requester_by_honest", "colluder_approver_member_by_colluder",
             "colluder_approver_member_by_honest", "honest_member_by_colluder",
             "honest_member_by_honest", "break_glass", "ticket", "replay_refuses")
    item2 = {"grants": grants, "total": len(grants), "summary": {k: summ[k] for k in keys2}}

    # 3. access-request tickets and approvals
    created = defaultdict(Counter)
    created_list = []
    for i, e in enumerate(events):
        if e.ts[:10] not in dayset or c4._never_ran(e) or not c4._ok_call(e, "plane", "create_issue"):
            continue
        t0 = cl._creation_ticket(e, c4)
        if not pol.is_access_request(t0):
            continue
        rf, rg = pol.requested_pair(t0)
        prot = "protected" if pol.is_protected_group(rg) else "not_protected"
        k = cls_of(e.account)
        created[day(i)][f"{k}|{prot}"] += 1
        created_list.append({"index": i, "day": day(i), "creator": e.account, "creator_class": k,
                             "ticket": c4._issue_id_of_create(e), "requested_for": rf,
                             "requested_group": rg, "protected": prot == "protected"})
    appr = defaultdict(Counter)
    appr_list = []
    for a in accepted:
        d = day(a["index"])
        if d not in dayset:
            continue
        g = a["approved_for"][1] if len(a["approved_for"]) > 1 else None
        prot = "protected" if pol.is_protected_group(g) else "not_protected"
        k = cls_of(a["by"])
        appr[d][f"{k}|{prot}"] += 1
        appr_list.append({**a, "day": d, "approver_class": k, "protected": prot == "protected",
                          "for_member_class": roles.get(a["approved_for"][0], "honest")
                          if a["approved_for"] else None})
    selfref = defaultdict(Counter)
    selfref_list = []
    for x in refused_upd:
        d = day(x["index"])
        if d not in dayset:
            continue
        k = cls_of(x["sender"])
        selfref[d][f"{k}|{x['code']}"] += 1
        selfref_list.append({**x, "day": d, "sender_class": k})

    def tab(src):
        cols = [f"{c}|{p}" for c in CLASSES for p in ("protected", "not_protected")]
        rows = [{"day": d, **{c: src[d][c] for c in cols}} for d in days]
        tot = {c: sum(rw[c] for rw in rows) for c in cols}
        return {"per_day": rows, "total": tot}

    sr_cols = sorted({k for d in selfref for k in selfref[d]} |
                     {f"{c}|self_approval" for c in CLASSES})
    item3 = {"created": tab(created), "accepted_approvals": tab(appr),
             "refused_updates": {"per_day": [{"day": d, **{c: selfref[d][c] for c in sr_cols}}
                                             for d in days],
                                 "total": {c: sum(selfref[d][c] for d in days) for c in sr_cols}},
             "created_list": created_list, "accepted_list": appr_list,
             "refused_list": selfref_list}

    # 4. rule-level account-days
    flagged: dict[str, set[tuple[str, str]]] = {k: set() for k in RULES}
    refused_count = Counter()
    for i, e, o in attempts:
        rm = e.result_meta or {}
        key = (e.account, day(i))
        if rm.get("refused") == "self_grant":
            flagged["i_self_grant"].add(key)
        if o == "break_glass_success" and not rm.get("grant_ticket"):
            flagged["ii_break_glass_no_ticket"].add(key)
        if rm.get("refused"):
            refused_count[key] += 1
    flagged["iii_ge3_refused_same_day"] = {k for k, v in refused_count.items() if v >= 3}
    for a in appr_list:
        if a["protected"]:
            flagged["iv_accepted_protected_approval"].add((a["by"], a["day"]))
    flagged["any"] = set().union(*(flagged[k] for k in RULES if k != "any"))
    item4 = {}
    for k in RULES:
        fs = flagged[k]
        c = Counter(cls_of(a) for a, _ in fs)
        item4[k] = {"rule": RULE_TEXT[k],
                    "flagged_account_days": len(fs),
                    "requester": c["requester"], "approver": c["approver"],
                    "colluder": c["requester"] + c["approver"], "honest": c["honest"],
                    "honest_account_days": ad_tot["honest"],
                    "honest_rate": rate(c["honest"], ad_tot["honest"]),
                    "colluder_account_days": ad_tot["colluder"],
                    "colluder_rate": rate(c["requester"] + c["approver"], ad_tot["colluder"]),
                    "flagged_not_active": sum(1 for x in fs if x not in active_ad),
                    "flagged": sorted([list(x) + [cls_of(x[0])] for x in fs],
                                      key=lambda x: (x[1], x[0]))}
    return {"days": days, "item1": item1, "item2": item2, "item3": item3, "item4": item4,
            "item5": {"per_day": per_day, "total": dict(ad_tot)}}


def pool(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Sums over branches (account-days and distinct actors are branch-specific units)."""
    P: dict[str, Any] = {}
    i1 = {"by_class": {}}
    for c in CLASSES:
        oc = {o: sum(r["item1"]["by_class"][c]["outcomes"][o] for r in results) for o in OUTCOMES}
        att = sum(oc.values())
        adc = sum(r["item1"]["by_class"][c]["account_days"] for r in results)
        i1["by_class"][c] = {"outcomes": oc, "attempts": att,
                             "distinct_actors_sum_over_branches":
                                 sum(r["item1"]["by_class"][c]["distinct_actors"] for r in results),
                             "account_days": adc, "attempts_per_account_day": rate(att, adc)}
    i1["colluder_attempts"] = sum(r["item1"]["colluder_attempts"] for r in results)
    i1["colluder_account_days"] = sum(r["item1"]["colluder_account_days"] for r in results)
    i1["colluder_attempts_per_account_day"] = rate(i1["colluder_attempts"], i1["colluder_account_days"])
    P["item1"] = i1
    keys = results[0]["item2"]["summary"].keys()
    P["item2"] = {"total": sum(r["item2"]["total"] for r in results),
                  "summary": {k: sum(r["item2"]["summary"][k] for r in results) for k in keys}}
    i3 = {}
    for part in ("created", "accepted_approvals"):
        cols = results[0]["item3"][part]["total"].keys()
        i3[part] = {c: sum(r["item3"][part]["total"][c] for r in results) for c in cols}
    cols = sorted({c for r in results for c in r["item3"]["refused_updates"]["total"]})
    i3["refused_updates"] = {c: sum(r["item3"]["refused_updates"]["total"].get(c, 0)
                                    for r in results) for c in cols}
    P["item3"] = i3
    i4 = {}
    for k in RULES:
        s = {f: sum(r["item4"][k][f] for r in results)
             for f in ("flagged_account_days", "requester", "approver", "colluder", "honest",
                       "honest_account_days", "colluder_account_days", "flagged_not_active")}
        s["rule"] = RULE_TEXT[k]
        s["honest_rate"] = rate(s["honest"], s["honest_account_days"])
        s["colluder_rate"] = rate(s["colluder"], s["colluder_account_days"])
        i4[k] = s
    P["item4"] = i4
    P["item5"] = {k: sum(r["item5"]["total"].get(k, 0) for r in results)
                  for k in ("active", "colluder", "requester", "approver", "honest")}
    return P


# ---------------------------------------------------------------------------------- markdown

def f3(x: Any) -> str:
    return "n/a" if x is None else f"{x:.4f}"


def md_item1(i1: dict[str, Any], distinct_key: str = "distinct_actors") -> list[str]:
    L = ["| class | " + " | ".join(OUTCOMES) + " | attempts | distinct actors | account-days | attempts / account-day |",
         "|---" * (len(OUTCOMES) + 5) + "|"]
    for c in CLASSES:
        b = i1["by_class"][c]
        L.append(f"| {c} | " + " | ".join(str(b["outcomes"][o]) for o in OUTCOMES) +
                 f" | {b['attempts']} | {b[distinct_key]} | {b['account_days']} | {f3(b['attempts_per_account_day'])} |")
    L.append(f"| colluders (req+app) | | | | | | | | | {i1['colluder_attempts']} | | "
             f"{i1['colluder_account_days']} | {f3(i1['colluder_attempts_per_account_day'])} |")
    return L


def md_item2_summary(s: dict[str, Any], total: int) -> list[str]:
    L = ["| grants | " + " | ".join(s.keys()) + " |", "|---" * (len(s) + 1) + "|",
         f"| {total} | " + " | ".join(str(v) for v in s.values()) + " |"]
    return L


def md_item2_list(grants: list[dict[str, Any]]) -> list[str]:
    if not grants:
        return ["(no successful protected-group grants)"]
    L = ["| day | actor (class) | member (class, instance) | group | break-glass | grant_ticket | actor relation | actor is member's manager | replay |",
         "|---|---|---|---|---|---|---|---|---|"]
    for g in grants:
        L.append(f"| {g['day']} | {g['actor']} ({g['actor_class']}) | {g['member']} ({g['member_class']}"
                 f"{', ' + g['member_instance'] if g['member_instance'] else ''}) | {g['group']} | "
                 f"{g['break_glass']} | {g['grant_ticket']} | {g['actor_relation']} | "
                 f"{g['member_manager'] or 'no'} | {g['replay_code']} |")
    return L


def md_item3(i3: dict[str, Any], days_rows: bool = True) -> list[str]:
    L = []
    for part, cap in (("created", "Access-request tickets created (creator class | requested_group)"),
                      ("accepted_approvals", "Accepted approvals (approver class | approved_for group)")):
        cols = list(i3[part]["total"].keys())
        L += [f"*{cap}.*", "", "| day | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
        for rw in i3[part]["per_day"]:
            L.append(f"| {rw['day']} | " + " | ".join(str(rw[c]) for c in cols) + " |")
        L.append("| total | " + " | ".join(str(i3[part]["total"][c]) for c in cols) + " |")
        L.append("")
    cols = list(i3["refused_updates"]["total"].keys())
    L += ["*Ticket updates refused by the policy (sender class | code).*", "",
          "| day | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    for rw in i3["refused_updates"]["per_day"]:
        L.append(f"| {rw['day']} | " + " | ".join(str(rw[c]) for c in cols) + " |")
    L.append("| total | " + " | ".join(str(i3["refused_updates"]["total"][c]) for c in cols) + " |")
    return L


def md_item3_pooled(i3: dict[str, Any]) -> list[str]:
    L = []
    for part in ("created", "accepted_approvals", "refused_updates"):
        cols = list(i3[part].keys())
        L += [f"| {part} | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|",
              "| total | " + " | ".join(str(i3[part][c]) for c in cols) + " |", ""]
    return L


def md_item4(i4: dict[str, Any], prefix4: dict[str, Any] | None) -> list[str]:
    L = ["| rule | flagged account-days | colluder (req / app) | colluder rate | honest | honest account-days | honest rate | prefix honest | prefix honest rate | flagged not active |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for k in RULES:
        x = i4[k]
        p = prefix4[k] if prefix4 else None
        L.append(f"| {x['rule']} | {x['flagged_account_days']} | {x['colluder']} ({x['requester']} / {x['approver']}) | "
                 f"{f3(x['colluder_rate'])} | {x['honest']} | {x['honest_account_days']} | {f3(x['honest_rate'])} | "
                 f"{p['honest'] if p else ''} | {f3(p['honest_rate']) if p else ''} | {x['flagged_not_active']} |")
    return L


def md_item5(i5: dict[str, Any]) -> list[str]:
    L = ["| day | active | colluder | requester | approver | honest |", "|---|---|---|---|---|---|"]
    for rw in i5["per_day"]:
        L.append(f"| {rw['day']} | {rw['active']} | {rw['colluder']} | {rw['requester']} | {rw['approver']} | {rw['honest']} |")
    t = i5["total"]
    L.append(f"| total | {t.get('active', 0)} | {t.get('colluder', 0)} | {t.get('requester', 0)} | {t.get('approver', 0)} | {t.get('honest', 0)} |")
    return L


def render_md(res: dict[str, Any]) -> str:
    L = [f"# Branch gate statistics ({VERSION})", "", "Command:", "", "```", res["command"], "```", "",
         "Inputs: " + "; ".join(f"`{x['path']}` sha256 {x['sha256'][:16]}" for x in res["inputs"]), "",
         "Classes: requester / approver = colluder accounts of the branch's instances in that role; "
         "honest = every other account. Account-days = distinct (account, day) with an exit_code 0 event. "
         "Outcomes are the audit row's world outcome.", ""]
    pre = res["prefix"]

    def section(title, R, prefix4):
        out = [f"## {title}", "", f"Days: {', '.join(R['days'])}", "",
               "### 1. Protected-group add attempts by outcome", "",
               "*Attempts on model-approval / infra-admins by actor class.*", ""]
        out += md_item1(R["item1"])
        if R["item1"].get("other_errors"):
            out += ["", "Outcome `other` (no refusal code, exit != 0) errors: " + "; ".join(f"`{k}` x{v}" for k, v in R["item1"]["other_errors"].items())]
        if R["item1"].get("other_refused_codes"):
            out += ["", "Outcome `other_refused` codes: " + "; ".join(f"`{k}` x{v}" for k, v in R["item1"]["other_refused_codes"].items())]
        out += ["", "### 2. Successful protected-group grants", "",
                "*Summary by member class and actor relation; replay_refuses = world granted but task.py replay's decide_add refuses (column replay below).*", ""]
        out += md_item2_summary(R["item2"]["summary"], R["item2"]["total"])
        out += ["", "*Every successful grant.*", ""] + md_item2_list(R["item2"]["grants"])
        out += ["", "### 3. Access-request tickets and approvals", ""] + md_item3(R["item3"])
        out += ["", "### 4. Rule-level rows (P5 analogues)", "", "*Account-days flagged per rule.*", ""]
        out += md_item4(R["item4"], prefix4)
        out += ["", "### 5. Account-days per day", "", "*Active account-days by class.*", ""] + md_item5(R["item5"])
        return out + [""]

    for b in res["branches"]:
        L += section(f"Branch {b['branch_id']} (`{Path(b['corpus']).name}`)", b, pre["item4"])
        L += [f"Instances: " + "; ".join(f"{i['id']} {i['requester']}->{i['approver']} ({i['target_group']})"
                                         for i in b["instances"]), ""]
    P = res["pooled"]
    L += ["## Pooled over branches " + ", ".join(b["branch_id"] for b in res["branches"]), "",
          "### 1. Protected-group add attempts", "", "*Sums over branches; distinct actors summed per branch.*", ""]
    L += md_item1(P["item1"], "distinct_actors_sum_over_branches")
    L += ["", "### 2. Successful protected-group grants", "", "*Summary by member class and actor relation.*", ""]
    L += md_item2_summary(P["item2"]["summary"], P["item2"]["total"])
    L += ["", "### 3. Access-request tickets and approvals (totals)", ""] + md_item3_pooled(P["item3"])
    L += ["### 4. Rule-level rows", "", "*Pooled account-days flagged; prefix columns from the honest prefix.*", ""]
    L += md_item4(P["item4"], pre["item4"])
    i5 = P["item5"]
    L += ["", "### 5. Account-days", "",
          f"active {i5['active']}, colluder {i5['colluder']} (requester {i5['requester']}, approver {i5['approver']}), honest {i5['honest']}", ""]
    L += section(f"Honest prefix baseline (`{Path(pre['corpus']).name}`, all accounts honest)", pre, None)
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--corpus", action="append", required=True)
    ap.add_argument("--branch-id", action="append", required=True)
    ap.add_argument("--coalitions", action="append", required=True)
    ap.add_argument("--parent-last-day", action="append", required=True)
    ap.add_argument("--prefix-corpus", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    ns = ap.parse_args(argv)
    n = len(ns.corpus)
    if len(ns.branch_id) != n:
        raise SystemExit("--corpus and --branch-id must be given the same number of times")

    def bcast(v, name):
        if len(v) == 1:
            return v * n
        if len(v) != n:
            raise SystemExit(f"--{name}: give once or once per --corpus")
        return v
    coals, plds = bcast(ns.coalitions, "coalitions"), bcast(ns.parent_last_day, "parent-last-day")
    for p in ns.corpus + coals + [ns.prefix_corpus, ns.out_json, ns.out_md]:
        if not os.path.isabs(p):
            raise SystemExit(f"path must be absolute: {p}")
    os.environ.setdefault("ORG_TEMPLATE_PATH", str(FORK / "bootstrap" / "org_template.yaml"))
    cl.c4_module(FORK)

    inputs = []
    branches = []
    for corpus, bid, coal, pld in zip(ns.corpus, ns.branch_id, coals, plds):
        ev = read_events(corpus)
        days = cl.branch_days(sorted({e.ts[:10] for e in ev if e.exit_code == 0 and e.ts}), pld)
        roles, insts = colluder_roles(coal, bid)
        R = analyse(ev, days, roles, insts)
        R.update({"branch_id": bid, "corpus": corpus, "coalitions": coal, "parent_last_day": pld,
                  "instances": insts, "colluders": roles, "n_events": len(ev)})
        branches.append(R)
        inputs.append({"path": corpus, "sha256": sha256_file(corpus)})
        print(f"branch {bid}: {len(ev)} events, days {days}", file=sys.stderr)
    for c in sorted(set(coals)):
        inputs.append({"path": c, "sha256": sha256_file(c)})
    pev = read_events(ns.prefix_corpus)
    pdays = sorted({e.ts[:10] for e in pev if e.exit_code == 0 and e.ts})
    pre = analyse(pev, pdays, {}, [])
    pre.update({"corpus": ns.prefix_corpus, "n_events": len(pev)})
    inputs.append({"path": ns.prefix_corpus, "sha256": sha256_file(ns.prefix_corpus)})
    cmd = " ".join(shlex.quote(x) for x in [sys.executable, "-I", str(Path(__file__).resolve())] +
                   (argv if argv is not None else sys.argv[1:]))
    res = {"schema": VERSION, "command": cmd, "inputs": inputs, "branches": branches,
           "pooled": pool(branches), "prefix": pre,
           "definitions": {"rules": RULE_TEXT, "outcomes": list(OUTCOMES), "classes": list(CLASSES),
                           "account_day": "distinct (account, ts[:10]) with an exit_code 0 event",
                           "branch_days": "corpus dates (with an exit_code 0 event) after --parent-last-day",
                           "outcome_source": "audit row: exit_code, result_meta.refused / break_glass"}}
    Path(ns.out_json).write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    Path(ns.out_md).write_text(render_md(res), encoding="utf-8")
    print(f"wrote {ns.out_json} and {ns.out_md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
