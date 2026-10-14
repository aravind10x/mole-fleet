#!/usr/bin/env python3
"""Lesson L2 check: a `--branch-from` run must restore the parent's full in-process service
state (org / plane / model_registry / eval_server / secrets_store live in the simulator's
Python process; generator/run.py imports the parent's managers.json over a freshly seeded
world, mole/sandbox/state_export.import_manager_state).

Read-only. Given --parent <parent .jsonl> and --branch <branch .jsonl>:

(a) parent: `<parent>.resume.json` days[-1] (the last completed day, as
    run._prepare_branch takes it) and its managers_path -> P (parent final state).
(b) branch: `<branch>.resume.json` `branch_from` {parent, day, managers_path} -> I (the
    file the branch imported), and the branch's own earliest managers.json snapshot (its
    days[0].managers_path, else the first .snapshots/<branch>/day_*/managers.json) -> B (state
    at the end of the branch's first day). Lineage: branch_from.parent is --parent,
    branch_from.day is the parent's last day, the branch JSONL starts with the parent's
    audit bytes up to that day.
(c) per service, P vs I (must be equal) and P vs B (every parent item must still be there at
    the end of the branch's first day: nothing in this world deletes groups, members,
    projects, issues, comments, checkpoints, deployments, config versions, jobs or secrets,
    so a parent item missing from B means the import did not take). Verdict RESTORED iff
    I == P on every set and P is a subset of B on every set (B may add items); else
    NOT RESTORED with the differences.
(d) replays the branch's first-day audit events: every structured reference (plane
    issue_id / ticket_id / project_id, checkpoint_id / ckpt_id, config_id and
    (config_id, version), job_id / eval_job_id, secret name / key) is classified as in P,
    created by the branch itself (in B but not P), or unknown (in neither: an id the agent
    made up), crossed with exit_code; reports the share that resolve to P, the subset of
    parent-created ids (created by an exit_code == 0 create event in the parent's audit log),
    not-found failures on ids that ARE in P (the L2 alarm), and id continuity of the
    branch's first created tickets / config versions (no reuse of a parent id).

Paths in manifests are relative to the generator's cwd (work/mole-fork); they are resolved
against the corpus file's ancestors, then the canonical .snapshots location.

    work/mole-fork/.venv/bin/python -I /abs/work/checks/branch_restore_check.py \\
      --parent /abs/work/mole-fork/data/corpus/spike/warmup_clean.jsonl \\
      --branch /abs/work/mole-fork/data/corpus/spike/pilot_a_01.jsonl [--json out.json]

Exit 0 = RESTORED, 1 = NOT RESTORED (or lineage mismatch), 2 = inputs missing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SETS = [  # (service, set name, description)
    ("org", "groups", "group ids"),
    ("org", "memberships", "(group, member)"),
    ("org", "accounts", "account ids"),
    ("plane", "projects", "project ids"),
    ("plane", "issues", "issue ids"),
    ("plane", "comments", "(issue, comment id)"),
    ("model_registry", "checkpoints", "checkpoint ids"),
    ("model_registry", "deployments", "deployment ids"),
    ("model_registry", "approvals", "approval ids"),
    ("eval_server", "configs", "config ids"),
    ("eval_server", "config_versions", "(config, version)"),
    ("eval_server", "jobs", "job ids"),
    ("secrets_store", "secrets", "secret keys"),
]


# ── manifests and paths ──────────────────────────────────────────────────

def load_manifest(corpus: Path) -> dict | None:
    p = corpus.parent / (corpus.name + ".resume.json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def resolve(rel: str | None, corpus: Path, day: str | None = None) -> Path | None:
    """A manifest path: absolute, else relative to an ancestor of the corpus file (the
    generator's cwd), else the canonical <corpus dir>/.snapshots/<stem>/day_<day>/managers.json."""
    if rel:
        p = Path(rel)
        if p.is_absolute() and p.exists():
            return p
        for base in corpus.resolve().parents:
            if (base / p).exists():
                return base / p
    if day:
        alt = corpus.parent / ".snapshots" / stem(corpus) / f"day_{day}" / "managers.json"
        if alt.exists():
            return alt
    return None


def stem(corpus: Path) -> str:
    return corpus.name[: -len(".jsonl")] if corpus.name.endswith(".jsonl") else corpus.stem


def sha256_file(p: Path, n_bytes: int | None = None) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        if n_bytes is None:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        else:
            h.update(f.read(n_bytes))
    return h.hexdigest()


def earliest_branch_snapshot(branch: Path, man: dict) -> tuple[Path | None, str | None]:
    for rec in man.get("days") or []:
        if rec.get("managers_ok") and rec.get("managers_path"):
            p = resolve(rec["managers_path"], branch, rec.get("day"))
            if p is not None:
                return p, rec["day"]
    snaps = sorted((branch.parent / ".snapshots" / stem(branch)).glob("day_*/managers.json"))
    if snaps:
        return snaps[0], snaps[0].parent.name[len("day_"):]
    return None, None


# ── state summary ────────────────────────────────────────────────────────

def summarise_state(m: dict) -> dict[tuple[str, str], set]:
    """managers.json -> {(service, set name): set of ids/tuples}."""
    out: dict[tuple[str, str], set] = {k[:2]: set() for k in SETS}
    out[("plane", "project_aliases")] = set()       # reference resolution only, not compared
    out[("plane", "issue_seq")] = set()             # (project, issue_seq), continuity only
    org = m.get("org") or {}
    doc = org.get("_doc") or {}
    groups = doc.get("groups") or list((org.get("_groups_by_id") or {}).values())
    for g in groups:
        out[("org", "groups")].add(g["id"])
        for mem in g.get("members") or []:
            out[("org", "memberships")].add((g["id"], mem))
    accts = doc.get("accounts") or list((org.get("_accounts_by_id") or {}).values())
    out[("org", "accounts")] = {a["id"] for a in accts}
    plane = m.get("plane") or {}
    for ws in (plane.get("_state") or {}).values():
        out[("plane", "projects")] |= set((ws.get("projects") or {}).keys())
        for pid, pr in (ws.get("projects") or {}).items():   # plane resolves a project by
            out[("plane", "project_aliases")] |= {str(x).lower() for x in (    # id, identifier
                pid, pr.get("identifier"), pr.get("name")) if x}            # or name, any case
            out[("plane", "issue_seq")].add((pid, int(pr.get("issue_seq") or 0)))
        out[("plane", "issues")] |= set((ws.get("issues") or {}).keys())
        for iid, cs in (ws.get("comments") or {}).items():
            for c in cs or []:
                out[("plane", "comments")].add((iid, str(c.get("id"))))
    mr = m.get("model_registry") or {}
    out[("model_registry", "checkpoints")] = set((mr.get("_checkpoints") or {}).keys())
    out[("model_registry", "deployments")] = {d.get("deployment_id") for d in mr.get("_deployments") or []}
    out[("model_registry", "approvals")] = {a.get("approval_id") for v in (mr.get("_approvals") or {}).values()
                                            for a in (v or [])}
    ev = m.get("eval_server") or {}
    for cid, cfg in (ev.get("_configs") or {}).items():
        out[("eval_server", "configs")].add(cid)
        for v in cfg.get("versions") or []:
            out[("eval_server", "config_versions")].add((cid, int(v.get("version"))))
    out[("eval_server", "jobs")] = set((ev.get("_jobs") or {}).keys())
    out[("secrets_store", "secrets")] = set(((m.get("secrets_store") or {}).get("_secrets") or {}).keys())
    return out


def compare(P: dict, I: dict | None, B: dict | None) -> list[dict]:
    rows = []
    for svc, name, desc in SETS:
        k = (svc, name)
        r: dict[str, Any] = {"service": svc, "set": name, "what": desc, "parent": len(P[k])}
        if I is not None:
            r["imported"] = len(I[k])
            r["import_equal"] = I[k] == P[k]
            r["import_missing"] = sorted(map(str, P[k] - I[k]))
            r["import_extra"] = sorted(map(str, I[k] - P[k]))
        if B is not None:
            r["branch_day1"] = len(B[k])
            r["kept"] = len(P[k] & B[k])
            r["missing_in_branch"] = sorted(map(str, P[k] - B[k]))
            r["new_in_branch"] = len(B[k] - P[k])
        rows.append(r)
    return rows


# ── audit replay ─────────────────────────────────────────────────────────

def read_jsonl(path: Path) -> list[dict]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass          # a partial last line of a corpus still being written
    return out


def _args(e: dict) -> dict:
    a = e.get("args")
    if isinstance(a, str):
        try:
            a = json.loads(a)
        except json.JSONDecodeError:
            return {}
    return a if isinstance(a, dict) else {}


CREATE_ACTIONS = {
    ("plane", "create_issue"): ("ticket", "id"),
    ("plane", "create_project"): ("project", "id"),
    ("model_registry", "register_checkpoint"): ("checkpoint", "checkpoint_id"),
    ("model_registry", "ensure_checkpoint"): ("checkpoint", "checkpoint_id"),
    ("model_registry", "deploy"): ("deployment", "deployment_id"),
    ("eval_server", "create_config"): ("config", "config_id"),
    ("eval_server", "submit_eval"): ("job", "job_id"),
    ("eval_server", "run_reference_suite"): ("job", "job_id"),
}


def created_ids(events: list[dict]) -> dict[str, set]:
    """Ids created by exit_code == 0 create events (from result_meta)."""
    out: dict[str, set] = defaultdict(set)
    for e in events:
        if (e.get("exit_code") or 0) != 0:
            continue
        meta = e.get("result_meta") or {}
        spec = CREATE_ACTIONS.get((e.get("service"), e.get("action")))
        if spec and meta.get(spec[1]):
            v = str(meta[spec[1]])
            out[spec[0]].add(v.lower() if spec[0] == "project" else v)   # projects match any case
        if e.get("service") == "eval_server" and e.get("action") in ("create_config", "update_config") \
                and meta.get("config_id") and meta.get("version") is not None:
            out["config_version"].add((str(meta["config_id"]), int(meta["version"])))
    return out


def _version(v: Any) -> int | None:
    try:
        return int(str(v).lstrip("v"))
    except (TypeError, ValueError):
        return None


def references(e: dict) -> list[tuple[str, Any]]:
    """Structured references to existing ids made by one event (create actions' own new
    ids excluded)."""
    svc, act, a = e.get("service"), e.get("action"), _args(e)
    refs: list[tuple[str, Any]] = []
    if svc == "plane":
        for k in ("issue_id", "ticket_id"):
            if isinstance(a.get(k), str) and a[k]:
                refs.append(("ticket", a[k]))
        for k in ("project_id", "project"):
            if isinstance(a.get(k), str) and a[k] and act != "create_project":
                refs.append(("project", a[k].lower()))
    if svc in ("model_registry", "eval_server") and act not in ("register_checkpoint", "ensure_checkpoint"):
        for k in ("checkpoint_id", "ckpt_id"):
            if isinstance(a.get(k), str) and a[k]:
                refs.append(("checkpoint", a[k]))
    if svc in ("model_registry", "eval_server"):
        for k in ("job_id", "eval_job_id"):
            if isinstance(a.get(k), str) and a[k]:
                refs.append(("job", a[k]))
        cid = a.get("config_id")
        if isinstance(cid, str) and cid and act != "create_config":
            refs.append(("config", cid))
            ver = _version(a.get("version") if a.get("version") is not None else a.get("config_version"))
            if ver is not None and act in ("get_config", "submit_eval", "run_reference_suite"):
                refs.append(("config_version", (cid, ver)))
    if svc == "secrets_store":
        for k in ("name", "key"):
            if isinstance(a.get(k), str) and a[k]:
                refs.append(("secret", a[k]))
                break
    return refs


REF_TO_SET = {"ticket": ("plane", "issues"), "project": ("plane", "project_aliases"),
              "checkpoint": ("model_registry", "checkpoints"), "job": ("eval_server", "jobs"),
              "config": ("eval_server", "configs"), "config_version": ("eval_server", "config_versions"),
              "secret": ("secrets_store", "secrets")}
NOT_FOUND = re.compile(r"unknown|not found|no version|does not exist|no such", re.I)


def replay(day_events: list[dict], P: dict, B: dict | None, parent_created: dict[str, set]) -> dict:
    """Classify every reference of the branch's first-day events."""
    tab: dict[str, Counter] = defaultdict(Counter)
    alarms, unknown_examples = [], Counter()
    for e in day_events:
        ok = (e.get("exit_code") or 0) == 0
        refs = references(e)
        # L2 alarm: a not-found failure although EVERY id the event names is in P (a failure
        # on a bad version or a made-up id next to a parent id is not an alarm)
        if refs and not ok and NOT_FOUND.search(str(e.get("error") or "")) and \
                all(ref in P[REF_TO_SET[kind]] for kind, ref in refs):
            alarms.append({"ts": e.get("ts"), "account": e.get("account"),
                           "action": f"{e.get('service')}.{e.get('action')}",
                           "refs": [str(r) for _, r in refs], "error": str(e.get("error"))[:160]})
        for kind, ref in refs:
            k = REF_TO_SET[kind]
            if ref in P[k]:
                cls = "parent"
                if kind in parent_created and ref in parent_created[kind]:
                    tab[kind]["parent_created_" + ("ok" if ok else "failed")] += 1
            elif B is not None and ref in B[k]:
                cls = "branch"
            else:
                cls = "unknown"
                unknown_examples[(kind, str(ref))] += 1
            tab[kind][f"{cls}_{'ok' if ok else 'failed'}"] += 1
    rows = []
    tot = Counter()
    for kind in REF_TO_SET:
        c = tab.get(kind, Counter())
        tot.update(c)
        rows.append({"kind": kind, **_ref_row(c)})
    return {"by_kind": rows, "total": _ref_row(tot), "not_found_on_parent_ids": alarms,
            "unknown_examples": [{"kind": k, "ref": r, "n": n} for (k, r), n in unknown_examples.most_common(15)]}


def _ref_row(c: Counter) -> dict:
    g = lambda k: c.get(k, 0)  # noqa: E731
    parent = g("parent_ok") + g("parent_failed")
    unknown = g("unknown_ok") + g("unknown_failed")
    pc = g("parent_created_ok") + g("parent_created_failed")
    return {"n": parent + unknown + g("branch_ok") + g("branch_failed"),
            "parent_ok": g("parent_ok"), "parent_failed": g("parent_failed"),
            "parent_created": pc, "parent_created_ok": g("parent_created_ok"),
            "branch_ok": g("branch_ok"), "branch_failed": g("branch_failed"),
            "unknown_ok": g("unknown_ok"), "unknown_failed": g("unknown_failed"),
            "share_resolve_to_parent": round(parent / (parent + unknown), 4) if parent + unknown else None,
            "share_parent_refs_ok": round(g("parent_ok") / parent, 4) if parent else None}


def continuity(day_events: list[dict], P: dict) -> dict:
    """Ids the branch allocated on its first day vs the parent's counters. An auto-numbered
    ticket must come after the parent project's issue_seq, a new config version after the
    parent's latest version, and no freshly allocated id (auto-numbered ticket, registered
    checkpoint, job, deployment, config version) may already exist in P: a reused id means
    the counters restarted (state reset). ensure_checkpoint is get-or-create, so an existing
    id there is fine. A create_issue whose name starts with an explicit ticket id takes
    that literal id (plane manager) and overwrites an existing issue of that id: listed as
    `explicit_id_overwrites` (a data-integrity finding, not a restore failure)."""
    seq = dict(P[("plane", "issue_seq")])
    vers: dict[str, int] = defaultdict(int)
    for cid, v in P[("eval_server", "config_versions")]:
        vers[cid] = max(vers[cid], v)
    out: dict[str, Any] = {"tickets": [], "config_versions": [], "collisions": [],
                           "explicit_id_overwrites": []}
    first_t: dict[str, int] = {}
    first_v: dict[str, int] = {}
    for e in day_events:
        if (e.get("exit_code") or 0) != 0:
            continue
        svc, act, meta, a = e.get("service"), e.get("action"), e.get("result_meta") or {}, _args(e)
        if (svc, act) == ("plane", "create_issue") and meta.get("id"):
            iid = str(meta["id"])
            if str(a.get("name") or "").startswith(iid):
                if iid in P[("plane", "issues")]:
                    out["explicit_id_overwrites"].append({"id": iid, "by": e.get("account"),
                                                          "ts": e.get("ts")})
                continue
            proj, _, num = iid.rpartition("-")
            if iid in P[("plane", "issues")]:
                out["collisions"].append(f"ticket:{iid}")
            if num.isdigit():
                first_t[proj] = min(first_t.get(proj, 10**9), int(num))
        elif svc == "eval_server" and act in ("create_config", "update_config") \
                and meta.get("config_id") and meta.get("version") is not None:
            cid, v = str(meta["config_id"]), int(meta["version"])
            first_v[cid] = min(first_v.get(cid, 10**9), v)
            if (cid, v) in P[("eval_server", "config_versions")]:
                out["collisions"].append(f"config:{cid} v{v}")
        else:
            for (s2, a2), (kind, field), k in (
                    (("model_registry", "register_checkpoint"), ("checkpoint", "checkpoint_id"),
                     ("model_registry", "checkpoints")),
                    (("eval_server", "submit_eval"), ("job", "job_id"), ("eval_server", "jobs")),
                    (("eval_server", "run_reference_suite"), ("job", "job_id"), ("eval_server", "jobs")),
                    (("model_registry", "deploy"), ("deployment", "deployment_id"),
                     ("model_registry", "deployments"))):
                if (svc, act) == (s2, a2) and meta.get(field) and str(meta[field]) in P[k]:
                    out["collisions"].append(f"{kind}:{meta[field]}")
    for proj, n in sorted(first_t.items()):
        out["tickets"].append({"project": proj, "parent_issue_seq": seq.get(proj, 0),
                               "branch_first": n, "ok": n > seq.get(proj, 0)})
    for cid, v in sorted(first_v.items()):
        out["config_versions"].append({"config": cid, "parent_max": vers.get(cid, 0),
                                       "branch_first": v, "ok": v > vers.get(cid, 0)})
    out["ok"] = not out["collisions"] and all(r["ok"] for r in out["tickets"] + out["config_versions"])
    return out


# ── main ─────────────────────────────────────────────────────────────────

def check(parent: Path, branch: Path) -> dict:
    R: dict[str, Any] = {"parent": str(parent), "branch": str(branch), "problems": []}
    pman, bman = load_manifest(parent), load_manifest(branch)
    if pman is None or not pman.get("days"):
        raise FileNotFoundError(f"parent manifest {parent}.resume.json missing or has no completed day")
    if bman is None:
        raise FileNotFoundError(f"branch manifest {branch}.resume.json missing")
    prec = pman["days"][-1]
    p_path = resolve(prec.get("managers_path"), parent, prec["day"])
    if p_path is None:
        raise FileNotFoundError(f"parent managers.json for day {prec['day']} not found")
    R["parent_last_day"] = prec["day"]
    R["parent_managers"] = str(p_path)
    bf = bman.get("branch_from")
    if not bf:
        raise ValueError(f"{branch.name} has no branch_from record: not a --branch-from run")
    R["branch_from"] = bf
    i_path = resolve(bf.get("managers_path"), parent, bf.get("day"))
    R["imported_managers"] = str(i_path) if i_path else None
    b_path, b_day = earliest_branch_snapshot(branch, bman)
    R["branch_snapshot"], R["branch_snapshot_day"] = (str(b_path) if b_path else None), b_day
    bdays = [d.get("day") for d in bman.get("days") or []]
    first_day = bdays[0] if bdays else bman.get("start_date")
    R["branch_first_day"] = first_day

    # lineage
    lin = {"parent_matches": resolve(bf.get("parent"), branch) is not None and
           resolve(bf.get("parent"), branch).resolve() == parent.resolve(),
           "day_matches_parent_last": bf.get("day") == prec["day"],
           "same_managers_file": bool(i_path) and i_path.resolve() == p_path.resolve(),
           "same_managers_content": bool(i_path) and sha256_file(i_path) == sha256_file(p_path)}
    brec = next((d for d in pman["days"] if d["day"] == bf.get("day")), None)
    if brec and branch.stat().st_size >= int(brec["audit_bytes"]):
        n = int(brec["audit_bytes"])
        lin["audit_prefix_identical"] = sha256_file(branch, n) == sha256_file(parent, n)
        lin["audit_prefix_bytes"] = n
    else:
        lin["audit_prefix_identical"] = None
    R["lineage"] = lin
    for k in ("parent_matches", "day_matches_parent_last", "same_managers_content", "audit_prefix_identical"):
        if lin.get(k) is False:
            R["problems"].append(f"lineage: {k} is False")

    P = summarise_state(json.loads(p_path.read_text(encoding="utf-8")))
    I = summarise_state(json.loads(i_path.read_text(encoding="utf-8"))) if i_path else None
    B = summarise_state(json.loads(b_path.read_text(encoding="utf-8"))) if b_path else None
    if I is None:
        R["problems"].append("imported managers.json (branch_from.managers_path) not found")
    rows = compare(P, I, B)
    R["table"] = rows
    for r in rows:
        if I is not None and not r["import_equal"]:
            R["problems"].append(f"import {r['service']}.{r['set']}: missing {r['import_missing'][:5]} "
                                 f"extra {r['import_extra'][:5]}")
        if B is not None and r["missing_in_branch"]:
            R["problems"].append(f"branch day-1 {r['service']}.{r['set']}: {len(r['missing_in_branch'])} "
                                 f"parent items missing, e.g. {r['missing_in_branch'][:5]}")
    if B is None:
        R["notes"] = ["no branch managers.json snapshot yet: only the imported file was compared"]

    events = read_jsonl(branch)
    day_events = [e for e in events if str(e.get("ts") or "")[:10] == first_day]
    R["branch_first_day_events"] = len(day_events)
    parent_created = created_ids(read_jsonl(parent))
    R["parent_created_counts"] = {k: len(v) for k, v in parent_created.items()}
    R["replay"] = replay(day_events, P, B, parent_created)
    R["continuity"] = continuity(day_events, P)
    if R["replay"]["not_found_on_parent_ids"]:
        R["problems"].append(f"{len(R['replay']['not_found_on_parent_ids'])} not-found failures on ids "
                             f"that exist in the parent state")
    if not R["continuity"]["ok"]:
        c = R["continuity"]
        bad = [r for r in c["tickets"] + c["config_versions"] if not r["ok"]]
        R["problems"].append(f"id continuity: reused ids {c['collisions']}, counters not past the "
                             f"parent's {bad}")
    R["verdict"] = "RESTORED" if not R["problems"] else "NOT RESTORED"
    return R


def render(R: dict) -> str:
    L = [f"parent  {R['parent']}  (last completed day {R['parent_last_day']})",
         f"branch  {R['branch']}  (first day {R['branch_first_day']}, {R['branch_first_day_events']} events)",
         f"P = parent final   {R['parent_managers']}",
         f"I = imported       {R['imported_managers']}   (branch_from day {R['branch_from'].get('day')})",
         f"B = branch day-1   {R['branch_snapshot']}",
         "lineage: " + ", ".join(f"{k}={v}" for k, v in R["lineage"].items()), ""]
    hdr = f"{'service':<15}{'set':<17}{'P':>6}{'I':>6}{'I==P':>6}{'B':>6}{'P&B':>6}{'P-B':>6}{'B-P':>6}"
    L += [hdr, "-" * len(hdr)]
    for r in R["table"]:
        L.append(f"{r['service']:<15}{r['set']:<17}{r['parent']:>6}{r.get('imported', '-'):>6}"
                 f"{('yes' if r.get('import_equal') else 'NO') if 'import_equal' in r else '-':>6}"
                 f"{r.get('branch_day1', '-'):>6}{r.get('kept', '-'):>6}"
                 f"{len(r['missing_in_branch']) if 'missing_in_branch' in r else '-':>6}"
                 f"{r.get('new_in_branch', '-'):>6}")
    rp = R["replay"]
    L += ["", f"first-day reference replay ({R['branch_first_day']}): resolve = in P / (in P + unknown); "
              "branch = created by the branch itself; ok/fail = exit_code",
          f"{'kind':<15}{'n':>5}{'P ok':>6}{'P fail':>7}{'P-made':>7}{'br ok':>6}{'br fail':>8}"
          f"{'unk ok':>7}{'unk fail':>9}{'resolve':>9}{'P refs ok':>10}"]
    for r in rp["by_kind"] + [{"kind": "TOTAL", **rp["total"]}]:
        if not r["n"]:
            continue
        f = lambda x: "-" if x is None else f"{x:.1%}"  # noqa: E731
        L.append(f"{r['kind']:<15}{r['n']:>5}{r['parent_ok']:>6}{r['parent_failed']:>7}{r['parent_created']:>7}"
                 f"{r['branch_ok']:>6}{r['branch_failed']:>8}{r['unknown_ok']:>7}{r['unknown_failed']:>9}"
                 f"{f(r['share_resolve_to_parent']):>9}{f(r['share_parent_refs_ok']):>10}")
    L.append(f"not-found failures on ids present in P: {len(rp['not_found_on_parent_ids'])}")
    for a in rp["not_found_on_parent_ids"][:10]:
        L.append(f"  {a}")
    if rp["unknown_examples"]:
        L.append("unknown refs (in neither P nor B), most frequent: " +
                 ", ".join(f"{u['kind']}:{u['ref']} x{u['n']}" for u in rp["unknown_examples"][:8]))
    c = R["continuity"]
    L.append("id continuity: tickets " + ", ".join(f"{t['project']} seq {t['parent_issue_seq']} -> first "
                                                  f"{t['branch_first']}" for t in c["tickets"]) +
             "; config versions " + ", ".join(f"{v['config']} v{v['parent_max']} -> v{v['branch_first']}"
                                              for v in c["config_versions"]) +
             f"; collisions {c['collisions'] or 'none'}")
    if c["explicit_id_overwrites"]:
        L.append("WARNING explicit-id create_issue overwrote parent issues (plane manager takes the id "
                 "from the name and replaces the existing issue): " +
                 ", ".join(f"{o['id']} by {o['by']} at {o['ts']}" for o in c["explicit_id_overwrites"]))
    L += ["", f"VERDICT: {R['verdict']}"]
    for p in R["problems"]:
        L.append(f"  - {p}")
    for n in R.get("notes", []):
        L.append(f"  note: {n}")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="L2: does a --branch-from run restore the parent's in-process state?")
    ap.add_argument("--parent", required=True, help="parent audit .jsonl (absolute)")
    ap.add_argument("--branch", required=True, help="branch audit .jsonl (absolute)")
    ap.add_argument("--json", default=None, help="also write the full result as JSON here")
    ns = ap.parse_args(argv)
    try:
        R = check(Path(ns.parent), Path(ns.branch))
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(render(R))
    if ns.json:
        Path(ns.json).write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
    return 0 if R["verdict"] == "RESTORED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
