#!/usr/bin/env python3
"""Phase A, A1: cover arithmetic on prefix_rw_v2c (brief 36 with dated notes 1 and 2; roadmap v4).

How much cover does the honest task stream supply for a planted line? A session COVERS a line iff
one of its fed write tasks names the line's (document, item) pair. Three subcommands, each writing
one record of ids, documents, items, counts and booleans (never task text, statement text or a
rationale):

  join   A1.0: the event/transcript join on task_id; each session's fed agenda items parsed
         against the ten class templates of stage3_rung1_class.py into (document, item, kind);
         per document and item, the write-task and read-task sessions per simulated day; the
         behavioural check (a fed write task on a document followed by an ownCloud write action on
         it in the same session).
  lines  A1.1: every applied line of T1 v2 and v3: document, item (the anchor line
         planted_rows[].as_sent.find matched to the seeded item labels; an item mentioned but not
         as a label is the entity fallback, counted separately), window (simulated days strictly
         after pre_window_boundary through composition_day), carrying account and session, the
         carrying session's own class tasks, and the realised cover beside the inserter's own
         session_touches_target flag.
  cover  A1.2: the author pool rebuilt by the inserter's rule (stage3_t1.py draw_author: the
         `pool` tier, active write-team accounts, managers excluded) and checked against the
         recorded author_pool_sizes by replaying every role draw; the window-length check; the
         item-route gate; then, only when every line of every application names an item or the
         coordinator's rule for item-less lines is passed (--itemless), p0, p1, p3 per
         application with the bootstrap over applications.

A session's tasks are its FED agenda items: the generator's rich benign sessions feed 2 to 4 bank
items one at a time as "Next on your agenda: ..." user turns (agentic_member.py, next_task_fn);
the session's second message is the generic session-start prompt in every session. This is the
reading stage3_write_yield.py already uses. An item drawn but never fed (turn cap) is not observable.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_a1_cover.py join  --out work/stage3/phase-a/a1-join-v0.json
    work/mole-fork/.venv/bin/python -I work/checks/stage3_a1_cover.py lines --out work/stage3/phase-a/a1-lines-v0.json
    work/mole-fork/.venv/bin/python -I work/checks/stage3_a1_cover.py cover --out work/stage3/phase-a/a1-cover-v0.json
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, NamedTuple, Sequence

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_rung1_class as rc  # noqa: E402
import stage3_write_yield as wy  # noqa: E402

ROOT = HERE.parent
CORPUS = ROOT / "mole-fork" / "data" / "corpus" / "spike" / "prefix_rw_v2c.jsonl"
TRANSCRIPTS = ROOT / "mole-fork" / "data" / "corpus" / "spike" / "prefix_rw_v2c.transcripts.jsonl"
BANK = ROOT / "stage3" / "bank-reweight" / "benign_task_bank_v2_class_v6.yaml"
TEMPLATE = ROOT / "mole-fork" / "bootstrap" / "org_template.yaml"
PLANTS = {"v2": ROOT / "stage3" / "t1v2" / "plants-v2.json", "v3": ROOT / "stage3" / "t1v3" / "plants-v3.json"}
#: the payload file each plants manifest names (v3 planted from the planting list, which is
#: payloads-v3.json's 36 plus 12 sham re-draws of v2); opened for ids, ops and anchors only
PAYLOADS = {"v2": ROOT / "stage3" / "t1v2" / "payloads-v2.json",
            "v3": ROOT / "stage3" / "t1v3" / "payloads-v3-planting.json"}

SEED = 20261106
N_BOOT = 2000
P3_CAP = 20_000
ITEMS: dict[str, list[str]] = {d["path"]: list(d["items"]) for d in rc.CLASS}
GOVERNING_REGIMES = ("conforming", "middle", "routine_redraw")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(p: Path) -> list[dict]:
    with open(p, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ── the task parse ─────────────────────────────────────────────────────────────────────────

class Task(NamedTuple):
    doc: str
    item: str
    kind: str      # "write" | "read"
    tmpl: int      # index into rc._WRITE_TMPL or rc._READ_TMPL


def _template_re(t: str) -> re.Pattern:
    s = t.replace("{{ws}}", "\x00WS\x00")
    out = ""
    for part in re.split(r"(\{item\}|\{doc\}|\{slug\}|\x00WS\x00)", s):
        if part == "{item}":
            out += r"(?P<item>.+?)"
        elif part == "{doc}":
            out += r"`(?P<doc>/shared/[^`]+)`"
        elif part == "{slug}":
            out += r"[A-Za-z0-9-]+"
        elif part == "\x00WS\x00":
            out += r"(?:\{ws\}|[A-Za-z0-9._-]+)"
        else:
            out += re.escape(part)
    return re.compile(out)


_TEMPLATES: list[tuple[str, int, re.Pattern]] = (
    [("write", i, _template_re(t)) for i, t in enumerate(rc._WRITE_TMPL)]
    + [("read", i, _template_re(t)) for i, t in enumerate(rc._READ_TMPL)])


def parse_task(text: str) -> Task | None:
    """(document, item, kind, template index) when the text is one of the ten class templates
    filled with a class document and one of ITS items; else None."""
    t = " ".join((text or "").split())
    for kind, i, rx in _TEMPLATES:
        m = rx.fullmatch(t)
        if m and m["doc"] in ITEMS and m["item"] in ITEMS[m["doc"]]:
            return Task(m["doc"], m["item"], kind, i)
    return None


def session_tasks(transcript: Mapping[str, Any]) -> tuple[int, list[Task]]:
    """(number of fed agenda items, the parsed class tasks among them, in feed order)."""
    fed = wy.fed_items(dict(transcript))
    return len(fed), [p for p in (parse_task(x) for x in fed) if p is not None]


def _names_class_doc(text: str) -> bool:
    return any(p in (text or "") for p in rc.DOC_PATHS)


def session_index(transcripts: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """{task_id: {account, day, n_fed, tasks}} for every transcript."""
    out: dict[str, dict[str, Any]] = {}
    for t in transcripts:
        n_fed, tasks = session_tasks(t)
        out[str(t.get("task_id") or "")] = {"account": t.get("account"), "day": str(t.get("sim_ts") or "")[:10],
                                            "n_fed": n_fed, "tasks": tasks}
    return out


# ── A1.0, the join ─────────────────────────────────────────────────────────────────────────

def join(events: Sequence[Mapping[str, Any]], transcripts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ev_ids = {str(e.get("task_id")) for e in events if e.get("task_id")}
    tr_ids = {str(t.get("task_id")) for t in transcripts if t.get("task_id")}
    inter = ev_ids & tr_ids
    idx = session_index(transcripts)
    days = sorted({s["day"] for s in idx.values() if s["day"]})
    sess = Counter()
    items = Counter({"total": 0, "class_write": 0, "class_read": 0, "not_class": 0, "names_class_doc_unparsed": 0})
    per: dict[str, dict[str, dict[str, dict[str, int]]]] = {
        p: {it: {d: {"write": 0, "read": 0} for d in days} for it in ITEMS[p]} for p in rc.DOC_PATHS}
    n_fed_dist, n_class_dist, n_write_dist = Counter(), Counter(), Counter()
    for t in transcripts:
        fed = wy.fed_items(dict(t))
        parsed = [parse_task(x) for x in fed]
        items["total"] += len(fed)
        for x, p in zip(fed, parsed):
            if p is not None:
                items["class_" + p.kind] += 1
            elif _names_class_doc(x):
                items["names_class_doc_unparsed"] += 1
            else:
                items["not_class"] += 1
        tasks = [p for p in parsed if p is not None]
        sess["total"] += 1
        if not fed:
            sess["no_fed_item"] += 1
        elif tasks:
            sess["with_class_task"] += 1
        else:
            sess["fed_but_no_class_task"] += 1
        n_fed_dist[len(fed)] += 1
        n_class_dist[len(tasks)] += 1
        n_write_dist[sum(1 for p in tasks if p.kind == "write")] += 1
        day = str(t.get("sim_ts") or "")[:10]
        for kind in ("write", "read"):
            for (doc, item) in {(p.doc, p.item) for p in tasks if p.kind == kind}:
                per[doc][item][day][kind] += 1
    # behavioural check: (session, document) pairs from fed write tasks, and whether the session's
    # events include an ownCloud content-write action on that document
    acts: dict[tuple[str, str], list[int]] = defaultdict(list)
    for e in events:
        if e.get("service") == "owncloud" and e.get("action") in rc.CLASS_WRITE_ACTIONS and e.get("task_id"):
            p = rc._class_path(dict(e))
            if p:
                acts[(str(e["task_id"]), p)].append(int(e.get("exit_code") or 0))
    pairs = {(tid, p.doc) for tid, s in idx.items() for p in s["tasks"] if p.kind == "write"}
    with_act = sum(1 for k in pairs if k in acts)
    with_ok = sum(1 for k in pairs if any(c == 0 for c in acts.get(k, [])))
    # session-day check: sessions whose events fall on a day other than the transcript's sim day
    ev_days: dict[str, set[str]] = defaultdict(set)
    for e in events:
        if e.get("task_id") and e.get("ts"):
            ev_days[str(e["task_id"])].add(str(e["ts"])[:10])
    off_day = sum(1 for tid, s in idx.items() if ev_days.get(tid) and ev_days[tid] != {s["day"]})
    return {
        "events_total": len(events),
        "events_with_task_id": sum(1 for e in events if e.get("task_id")),
        "task_ids_in_events": len(ev_ids), "task_ids_in_transcripts": len(tr_ids),
        "task_ids_intersection": len(inter),
        "join_equal": len(ev_ids) == len(tr_ids) == len(inter),
        "sessions": {"total": sess["total"], "with_class_task": sess["with_class_task"],
                     "fed_but_no_class_task": sess["fed_but_no_class_task"], "no_fed_item": sess["no_fed_item"]},
        "fed_items": dict(items),
        "fed_items_per_session": {str(k): v for k, v in sorted(n_fed_dist.items())},
        "class_tasks_per_session": {str(k): v for k, v in sorted(n_class_dist.items())},
        "class_write_tasks_per_session": {str(k): v for k, v in sorted(n_write_dist.items())},
        "days": days,
        "sessions_per_document_item_day": per,
        "write_task_behaviour": {
            "session_document_pairs": len(pairs), "with_write_action": with_act,
            "share_with_write_action": (with_act / len(pairs)) if pairs else None,
            "with_successful_write_action": with_ok,
            "share_with_successful_write_action": (with_ok / len(pairs)) if pairs else None,
            "actions": list(rc.CLASS_WRITE_ACTIONS)},
        "sessions_with_events_off_the_sim_day": off_day,
    }


# ── A1.1, the line's item and window ──────────────────────────────────────────────────────

def _label_re(item: str) -> re.Pattern:
    return re.compile(r"^\s*(?:[-*]|\d+\.)\s*" + re.escape(item) + r"\s*:", re.I)


_LABELS = {p: [(it, _label_re(it)) for it in its] for p, its in ITEMS.items()}


def item_route(anchor: str, doc: str) -> tuple[str | None, str]:
    """The item an anchor line names: a seeded item LABEL ("- Metrics port: ..." / "2. Local cache
    step: ...") first; else an item named anywhere in the line (the entity fallback); else none.
    Routes: find_label, find_mention, ambiguous (two or more), none, no_anchor (an append)."""
    if not anchor:
        return None, "no_anchor"
    lines = anchor.splitlines()
    lab = {it for it, rx in _LABELS[doc] for ln in lines if rx.match(ln)}
    if len(lab) == 1:
        return next(iter(lab)), "find_label"
    if len(lab) > 1:
        return None, "ambiguous"
    low = anchor.lower()
    men = {it for it in ITEMS[doc] if it.lower() in low}
    if len(men) == 1:
        return next(iter(men)), "find_mention"
    if len(men) > 1:
        return None, "ambiguous"
    return None, "none"


def window_days(pre_window_boundary: str, composition_day: str, days: Sequence[str]) -> list[str]:
    """Dated note 2: the simulated days strictly after the boundary through the composition day;
    'day0' means the window begins at the first simulated day."""
    return [d for d in days if (pre_window_boundary == "day0" or d > pre_window_boundary) and d <= composition_day]


def load_payloads(ver: str) -> dict[str, list[dict]]:
    """{payload id: [{op, anchor}] per statement}: ids, ops and anchors only; nothing else kept."""
    d = json.loads(PAYLOADS[ver].read_text(encoding="utf-8"))
    return {p["id"]: [{"op": s.get("op"), "anchor": s.get("anchor") or ""} for s in p["statements"]]
            for p in d["payloads"]}


def payload_key_names(ver: str) -> dict[str, list[str]]:
    d = json.loads(PAYLOADS[ver].read_text(encoding="utf-8"))
    p = d["payloads"][0]
    return {"top": sorted(d.keys()), "payload": sorted(p.keys()), "statement": sorted(p["statements"][0].keys())}


def plants_key_names(ver: str) -> dict[str, list[str]]:
    d = json.loads(PLANTS[ver].read_text(encoding="utf-8"))
    p = d["plants"][0]
    return {"application": sorted(p.keys()), "planted_row": sorted(p["planted_rows"][0].keys()),
            "as_sent": sorted(set().union(*(r["as_sent"].keys() for r in p["planted_rows"])))}


def app_id(ver: str, plant: Mapping[str, Any]) -> str:
    return f"{ver}:{plant['payload_id']}:{plant['arm']}"


def build_lines(plants: Mapping[str, Sequence[Mapping[str, Any]]], payloads: Mapping[str, Mapping[str, list]],
                sessions: Mapping[str, Mapping[str, Any]], days: Sequence[str]) -> list[dict[str, Any]]:
    """One record per applied line (statement row): ids, document, item and route, window, carrying
    account and session, the carrying session's class tasks, the realised cover flags."""
    out = []
    for ver, ps in plants.items():
        for p in ps:
            doc = p["document"]
            win = window_days(p["pre_window_boundary"], p["composition_day"], days)
            stm = payloads[ver][p["payload_id"]]
            for r in p["planted_rows"]:
                item, route = item_route((r.get("as_sent") or {}).get("find") or "", doc)
                a_item, a_route = item_route(stm[r["statement"]]["anchor"], doc)
                s = sessions.get(str(r["task_id"]))
                tasks = s["tasks"] if s else []
                out.append({
                    "line_id": f"{app_id(ver, p)}:s{r['statement']}", "application": app_id(ver, p),
                    "version": ver, "payload_id": p["payload_id"], "arm": p["arm"], "regime": p["regime"],
                    "document": doc, "statement": r["statement"], "op": stm[r["statement"]]["op"],
                    "item": item, "item_route": route,
                    "payload_anchor_agrees": (a_item, a_route) == (item, route),
                    "window": win, "role_days": list(p["days"]), "composition_day": p["composition_day"],
                    "account": r["account"], "task_id": r["task_id"], "role": r["role"], "day": r["day"],
                    "carrying_session_found": s is not None,
                    "carrying_session_tasks": [[t.doc, t.item, t.kind] for t in tasks],
                    "realised_write": bool(item) and any(t.doc == doc and t.item == item and t.kind == "write" for t in tasks),
                    "realised_any": bool(item) and any(t.doc == doc and t.item == item for t in tasks),
                    "carrying_session_write_task_on_document": any(t.doc == doc and t.kind == "write" for t in tasks),
                    "session_touches_target": bool(r.get("session_touches_target")),
                })
    return out


def _nested_count(rows: Iterable[Mapping[str, Any]], key: str | None = None) -> dict[str, dict[str, int]]:
    c: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        if key is None or r[key]:
            c[r["regime"]][r["arm"]] += 1
    return {g: dict(sorted(v.items())) for g, v in sorted(c.items())}


def lines_summary(lines: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_app: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for ln in lines:
        by_app[ln["application"]].append(ln)
    named_label = Counter(sum(1 for x in ls if x["item_route"] == "find_label") for ls in by_app.values())
    named_any = Counter(sum(1 for x in ls if x["item"]) for ls in by_app.values())
    gov = [x for x in lines if x["regime"] in GOVERNING_REGIMES]
    return {
        "lines": len(lines), "applications": len(by_app),
        "lines_by_regime_and_arm": _nested_count(lines),
        "item_route_counts": dict(Counter(x["item_route"] for x in lines)),
        "item_route_by_op": {op: dict(Counter(x["item_route"] for x in lines if x["op"] == op))
                             for op in sorted({x["op"] for x in lines})},
        "payload_anchor_route_agrees_with_find_route": sum(1 for x in lines if x["payload_anchor_agrees"]),
        "applications_by_lines_with_label_item": {str(k): v for k, v in sorted(named_label.items())},
        "applications_by_lines_with_any_item": {str(k): v for k, v in sorted(named_any.items())},
        "carrying_sessions_found": sum(1 for x in lines if x["carrying_session_found"]),
        "realised_cover_write": sum(1 for x in lines if x["realised_write"]),
        "realised_cover_any": sum(1 for x in lines if x["realised_any"]),
        "realised_cover_write_by_regime_and_arm": _nested_count(lines, "realised_write"),
        "realised_cover_any_by_regime_and_arm": _nested_count(lines, "realised_any"),
        "realised_cover_write_label_route_only": sum(1 for x in lines if x["realised_write"] and x["item_route"] == "find_label"),
        "governing_regimes": list(GOVERNING_REGIMES),
        "governing_lines": len(gov),
        "governing_realised_cover_write": sum(1 for x in gov if x["realised_write"]),
        "governing_realised_cover_any": sum(1 for x in gov if x["realised_any"]),
        "session_touches_target": sum(1 for x in lines if x["session_touches_target"]),
        "session_touches_target_by_regime_and_arm": _nested_count(lines, "session_touches_target"),
        "carrying_session_write_task_on_document": sum(1 for x in lines if x["carrying_session_write_task_on_document"]),
        "carrying_session_write_task_on_document_by_regime_and_arm":
            _nested_count(lines, "carrying_session_write_task_on_document"),
    }


# ── A1.2, the enumerations ────────────────────────────────────────────────────────────────

Cover = Mapping[str, Sequence[set]]   # {account: [the set of line indices each of its sessions covers]}


def p0(pool: Sequence[str], cov: Cover, n_lines: int) -> float:
    """Per line, the share of pool accounts with at least one covering session; averaged over lines."""
    if not pool:
        return 0.0
    shares = [sum(1 for a in pool if any(i in s for s in cov.get(a, []))) / len(pool) for i in range(n_lines)]
    return sum(shares) / n_lines


def _match(groups: Sequence[Sequence[int]], units: Sequence[set]) -> bool:
    """Can each group be given its own unit (session) that covers every line of the group?"""
    k = len(groups)
    if len(units) < k:
        return False
    cands = [[j for j, u in enumerate(units) if all(i in u for i in g)] for g in groups]
    if any(not c for c in cands):
        return False
    for pick in itertools.product(*cands):
        if len(set(pick)) == k:
            return True
    return False


def p1(pool: Sequence[str], cov: Cover, n_lines: int, groups: Sequence[Sequence[int]] | None = None) -> float:
    """The share of pool accounts with distinct covering sessions, one per line (a session covers at
    most one line); `groups` lets one session cover the lines of a group (the same-item variant)."""
    if not pool:
        return 0.0
    gs = groups if groups is not None else [[i] for i in range(n_lines)]
    return sum(1 for a in pool if _match(gs, list(cov.get(a, [])))) / len(pool)


def p3(pool: Sequence[str], cov: Cover, n_lines: int, rng: random.Random, cap: int = P3_CAP
       ) -> tuple[float, float, int, bool]:
    """(strict, flexible, triples evaluated, exact?) over ordered triples of distinct pool accounts.
    Strict: some assignment gives each account one line it covers in one of its sessions. Flexible:
    the three accounts' sessions together give each line its own covering session."""
    assert n_lines == 3
    n = len(pool)
    total = n * (n - 1) * (n - 2)
    if total == 0:
        return 0.0, 0.0, 0, True
    covers = {a: frozenset(i for s in cov.get(a, []) for i in s) for a in pool}
    if total <= cap:
        triples: Iterable[tuple[str, ...]] = itertools.permutations(pool, 3)
        m, exact = total, True
    else:
        triples = (tuple(rng.sample(list(pool), 3)) for _ in range(cap))
        m, exact = cap, False
    strict = flex = 0
    single = [[i] for i in range(n_lines)]
    for tri in triples:
        if any(all(perm[k] in covers[tri[k]] for k in range(3)) for perm in itertools.permutations(range(3))):
            strict += 1
            flex += 1
            continue
        units = [s for a in tri for s in cov.get(a, [])]
        if _match(single, units):
            flex += 1
    return strict / m, flex / m, m, exact


def cp_interval(x: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact two-sided Clopper-Pearson interval."""
    from scipy.stats import beta
    if n == 0:
        return 0.0, 1.0
    lo = 0.0 if x == 0 else float(beta.ppf(alpha / 2, x, n - x + 1))
    hi = 1.0 if x == n else float(beta.ppf(1 - alpha / 2, x + 1, n - x))
    return lo, hi


def summarise(vals: Sequence[float], n_boot: int = N_BOOT, seed: int = SEED) -> dict[str, Any]:
    """Mean over applications, percentile bootstrap over applications (95 percent). When every share
    is zero the upper bound is the exact upper bound on the share of applications with any cover
    (0 of n), which bounds the mean share from above (dated note 2 item 2)."""
    import numpy as np
    v = np.asarray(list(vals), dtype=float)
    n = len(v)
    if n == 0:
        return {"n": 0, "mean": None, "lo": None, "hi": None, "all_zero": None, "n_nonzero": 0}
    mean = float(v.mean())
    nz = int((v > 0).sum())
    if nz == 0:
        return {"n": n, "mean": 0.0, "lo": 0.0, "hi": cp_interval(0, n)[1], "all_zero": True, "n_nonzero": 0,
                "bound": "clopper_pearson_on_applications_with_any_cover"}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    boots = v[idx].mean(axis=1)
    return {"n": n, "mean": mean, "lo": float(np.percentile(boots, 2.5)), "hi": float(np.percentile(boots, 97.5)),
            "all_zero": False, "n_nonzero": nz, "bound": "bootstrap_over_applications"}


# ── A1.2, the pool ────────────────────────────────────────────────────────────────────────

def build_inserter(rows: Sequence[Mapping[str, Any]]):
    import stage3_t1 as t1
    import stage3_views as sv
    team, managers = t1.team_maps(TEMPLATE)
    return t1.Inserter(rows, sv.seed_base(), team, managers), t1


def pool_check(ins, t1, plants: Mapping[str, Sequence[Mapping[str, Any]]],
               payloads: Mapping[str, Mapping[str, list]]) -> dict[str, Any]:
    """Replay every recorded role draw (role order, the `used` exclusion, the role's replace anchors,
    until the composition day) through the inserter's own draw_author and compare the logged
    pool / anchored / touching sizes and the restricted flag with author_pool_sizes."""
    draws = mism = 0
    by_field = Counter()
    for ver, ps in plants.items():
        for p in ps:
            stm = payloads[ver][p["payload_id"]]
            roles = ins._roles(p["arm"])
            used: set[str] = set()
            for r, d in enumerate(p["days"]):
                anchors = [stm[i]["anchor"] for i in roles[r] if stm[i]["op"] == "replace"]
                log: list[dict] = []
                ins.draw_author(random.Random(0), p["document"], d, used, anchors, log, p["days"][-1])
                rec = p["author_pool_sizes"][r]
                draws += 1
                bad = [k for k in ("day", "pool", "anchored", "touching", "restricted") if log[0].get(k) != rec.get(k)]
                if bad:
                    mism += 1
                    by_field.update(bad)
                used.add(p["authors"][r])
    return {"role_draws": draws, "mismatches": mism, "mismatch_fields": dict(by_field)}


def cover_pool(ins, t1, document: str, window: Sequence[str]) -> list[str]:
    """The union over the window's days of the `pool` tier: active accounts in the document's write
    teams, managers excluded (no `used` exclusion: that only keeps one draw's authors distinct)."""
    out: set[str] = set()
    for d in window:
        out.update(a for a in ins.active.get(d, []) if ins.team.get(a) in t1.WRITE_TEAMS[document]
                   and a not in ins.managers)
    return sorted(out)


# ── A1.2, per application ─────────────────────────────────────────────────────────────────

def coverage(pool: Sequence[str], window: Sequence[str], doc: str, items: Sequence[str | None],
             sessions_by_acct_day: Mapping[tuple[str, str], Sequence[str]], idx: Mapping[str, Mapping[str, Any]],
             kinds: tuple[str, ...] = ("write",), rule: str = "item", unit: str = "session") -> dict[str, list[set]]:
    """{account: [set of line indices each unit covers]} for the pool's sessions in the window. rule
    'item': a task names the line's (document, item) (an item-less line is covered by nothing);
    rule 'document': a write task names the line's document. unit 'session' (primary) or 'task'."""
    out: dict[str, list[set]] = {}
    for a in pool:
        units: list[set] = []
        for d in window:
            for tid in sessions_by_acct_day.get((a, d), []):
                ts = [t for t in idx[tid]["tasks"] if t.kind in kinds and t.doc == doc]
                def lines_of(tt):
                    return {i for i, it in enumerate(items)
                            if any((rule == "document") or (it is not None and t.item == it) for t in tt)}
                if unit == "session":
                    s = lines_of(ts)
                    units.append(s)
                else:
                    units.extend(lines_of([t]) for t in ts)
        out[a] = units
    return out


def _sessions_by_acct_day(idx: Mapping[str, Mapping[str, Any]]) -> dict[tuple[str, str], list[str]]:
    out: dict[tuple[str, str], list[str]] = defaultdict(list)
    for tid, s in idx.items():
        out[(s["account"], s["day"])].append(tid)
    return out


def application_cover(app: Mapping[str, Any], app_lines: Sequence[Mapping[str, Any]], window: Sequence[str],
                      pool: Sequence[str], idx, sbad, rng: random.Random, rule: str, kinds=("write",),
                      unit: str = "session") -> dict[str, Any]:
    items = [ln["item"] for ln in sorted(app_lines, key=lambda x: x["statement"])]
    doc = app["document"]
    cov = coverage(pool, window, doc, items, sbad, idx, kinds, rule, unit)
    groups = None
    if rule == "item":
        same = defaultdict(list)
        for i, it in enumerate(items):
            same[it if it is not None else f"__none{i}"].append(i)
        groups = list(same.values())
    s3, f3, m, exact = p3(pool, cov, 3, rng)
    sess_in_win = [tid for d in window for (a, dd), tids in sbad.items() if dd == d for tid in tids]
    pool_set = set(pool)
    pool_sess = [tid for tid in sess_in_win if idx[tid]["account"] in pool_set]
    cov_sess = []
    for i in range(3):
        cov_sess.append(sum(1 for a in pool for u in cov[a] if i in u))
    return {
        "p0": p0(pool, cov, 3), "p1": p1(pool, cov, 3),
        "p1_same_item": p1(pool, cov, 3, groups) if groups is not None and len(groups) < 3 else None,
        "p3": s3, "p3_flexible": f3, "p3_triples": m, "p3_exact": exact,
        "pool": len(pool), "window_days": len(window),
        "sessions_in_window": len(sess_in_win), "pool_sessions_in_window": len(pool_sess),
        "covering_units_per_line": cov_sess,
        "q_hat_all": [c / len(sess_in_win) if sess_in_win else None for c in cov_sess],
        "q_hat_pool": [c / len(pool_sess) if pool_sess else None for c in cov_sess],
        "s_pool": (len(pool_sess) / len(pool)) if pool else None,
        "lines_share_item": groups is not None and len(groups) < 3,
    }


# ── commands ──────────────────────────────────────────────────────────────────────────────

def _load_plants() -> dict[str, list[dict]]:
    return {v: json.loads(p.read_text(encoding="utf-8"))["plants"] for v, p in PLANTS.items()}


def _inputs() -> dict[str, str]:
    return {"corpus": str(CORPUS), "corpus_sha256": sha256_file(CORPUS),
            "transcripts": str(TRANSCRIPTS), "transcripts_sha256": sha256_file(TRANSCRIPTS),
            "bank": str(BANK), "bank_sha256": sha256_file(BANK),
            "templates_module_sha256": sha256_file(HERE / "stage3_rung1_class.py"),
            "script_sha256": sha256_file(Path(__file__).resolve())}


def bank_template_counts() -> dict[str, Any]:
    import yaml
    b = yaml.safe_load(BANK.read_text(encoding="utf-8"))
    c = Counter()
    for team, v in b.items():
        for txt in v["variants"]:
            p = parse_task(txt)
            c["parsed_" + p.kind if p else ("names_class_doc_unparsed" if _names_class_doc(txt) else "not_class")] += 1
    return dict(c)


def cmd_join(ns) -> dict[str, Any]:
    events, transcripts = read_jsonl(CORPUS), read_jsonl(TRANSCRIPTS)
    j = join(events, transcripts)
    idx = session_index(transcripts)
    j["bank_variants"] = bank_template_counts()
    j["inputs"] = _inputs()
    j["reading"] = ("a session's tasks are its fed agenda items ('Next on your agenda: ...' user turns); "
                    "the second message is the generic session-start prompt in every session")
    j["sessions_index"] = {tid: {"account": s["account"], "day": s["day"], "n_fed": s["n_fed"],
                                 "class_tasks": [[t.doc, t.item, t.kind, t.tmpl] for t in s["tasks"]]}
                           for tid, s in sorted(idx.items())}
    print(json.dumps({k: j[k] for k in ("events_total", "events_with_task_id", "task_ids_in_events",
                                        "task_ids_in_transcripts", "task_ids_intersection", "join_equal",
                                        "sessions", "fed_items", "class_tasks_per_session",
                                        "class_write_tasks_per_session", "write_task_behaviour",
                                        "sessions_with_events_off_the_sim_day", "bank_variants")}, indent=1))
    return j


def cmd_lines(ns) -> dict[str, Any]:
    transcripts = read_jsonl(TRANSCRIPTS)
    idx = session_index(transcripts)
    days = sorted({s["day"] for s in idx.values()})
    plants = _load_plants()
    payloads = {v: load_payloads(v) for v in PLANTS}
    lines = build_lines(plants, payloads, idx, days)
    summ = lines_summary(lines)
    keys = {"payload_v2": payload_key_names("v2"), "payload_v3_planting": payload_key_names("v3"),
            "plants_v2": plants_key_names("v2")}
    route = ("no payload field names an item (statement keys printed); the item is the anchor line "
             "planted_rows[].as_sent.find matched to the seeded item labels (find_label), with an item "
             "named elsewhere in the line as the entity fallback (find_mention), counted separately; "
             "append statements carry no anchor (no_anchor)")
    print(json.dumps({"key_names": keys, "route": route, **summ}, indent=1))
    return {"key_names": keys, "route_used": route, "summary": summ, "lines": lines,
            "inputs": {**_inputs(), **{f"plants_{v}_sha256": sha256_file(p) for v, p in PLANTS.items()},
                       **{f"payloads_{v}_sha256": sha256_file(p) for v, p in PAYLOADS.items()}}}


def cmd_cover(ns) -> dict[str, Any]:
    rows, transcripts = read_jsonl(CORPUS), read_jsonl(TRANSCRIPTS)
    idx = session_index(transcripts)
    days = sorted({s["day"] for s in idx.values()})
    plants = _load_plants()
    payloads = {v: load_payloads(v) for v in PLANTS}
    lines = build_lines(plants, payloads, idx, days)
    ins, t1 = build_inserter(rows)
    chk = pool_check(ins, t1, plants, payloads)
    print(json.dumps({"pool_rebuild_check": chk}, indent=1))
    out: dict[str, Any] = {"pool_rebuild_check": chk, "inputs": _inputs()}
    if chk["mismatches"]:
        out["stopped"] = "pool rebuild mismatch (note 1 item 3)"
        return out
    apps = [(v, p) for v, ps in plants.items() for p in ps]
    by_app: dict[str, list[dict]] = defaultdict(list)
    for ln in lines:
        by_app[ln["application"]].append(ln)
    wl = Counter(len(window_days(p["pre_window_boundary"], p["composition_day"], days)) for _, p in apps)
    longer = sum(1 for _, p in apps
                 if len(window_days(p["pre_window_boundary"], p["composition_day"], days)) > len(p["days"]))
    out["window_lengths"] = {str(k): v for k, v in sorted(wl.items())}
    out["windows_longer_than_role_days"] = longer
    itemless_apps = sum(1 for ls in by_app.values() if any(x["item"] is None for x in ls))
    full_label = sum(1 for ls in by_app.values() if all(x["item_route"] == "find_label" for x in ls))
    out["item_gate"] = {"applications": len(by_app), "applications_with_an_itemless_line": itemless_apps,
                        "applications_with_three_label_items": full_label,
                        "lines_without_item": sum(1 for x in lines if x["item"] is None)}
    print(json.dumps({"window_lengths": out["window_lengths"], "windows_longer_than_role_days": longer,
                      "item_gate": out["item_gate"]}, indent=1))
    sbad = _sessions_by_acct_day(idx)
    # the stop's evidence: per item-named line, its own cover in its application's window and pool
    per_line = []
    for v, p in apps:
        win = window_days(p["pre_window_boundary"], p["composition_day"], days)
        pool = cover_pool(ins, t1, p["document"], win)
        for ln in by_app[app_id(v, p)]:
            if ln["item"] is None:
                continue
            row = {"line_id": ln["line_id"], "regime": ln["regime"], "arm": ln["arm"], "route": ln["item_route"],
                   "pool": len(pool), "window_days": len(win)}
            for kname, kinds in (("write", ("write",)), ("any", ("write", "read"))):
                cv = coverage(pool, win, p["document"], [ln["item"]], sbad, idx, kinds, "item")
                ns_ = sum(1 for a in pool for u in cv[a] if 0 in u)
                row[f"covering_sessions_{kname}"] = ns_
                row[f"covering_accounts_{kname}"] = sum(1 for a in pool if any(0 in u for u in cv[a]))
                row[f"share_pool_accounts_{kname}"] = row[f"covering_accounts_{kname}"] / len(pool) if pool else None
            per_line.append(row)
    out["itemnamed_line_cover"] = per_line
    agg = {}
    for g in sorted({r["regime"] for r in per_line}) + ["governing", "all"]:
        rs = [r for r in per_line if (g == "all" or (g == "governing" and r["regime"] in GOVERNING_REGIMES)
                                      or r["regime"] == g)]
        agg[g] = {"lines": len(rs),
                  "label_route": sum(1 for r in rs if r["route"] == "find_label"),
                  "with_any_covering_write_session": sum(1 for r in rs if r["covering_sessions_write"] > 0),
                  "mean_share_pool_accounts_write": (sum(r["share_pool_accounts_write"] for r in rs) / len(rs)) if rs else None,
                  "mean_share_pool_accounts_any": (sum(r["share_pool_accounts_any"] for r in rs) / len(rs)) if rs else None}
    out["itemnamed_line_cover_summary"] = agg
    print(json.dumps({"itemnamed_line_cover_summary": agg}, indent=1))
    if itemless_apps and not ns.itemless:
        out["stopped"] = ("A1.2 stopped under brief 36 section 4: the item route names no item for "
                          f"{out['item_gate']['lines_without_item']} lines (more than five) and every application "
                          f"but {len(by_app) - itemless_apps} has an item-less line; p0, p1, p3 are not computed "
                          "until the coordinator rules on item-less lines (--itemless uncoverable|document)")
        print(out["stopped"])
        return out
    # the probabilities (run only under a rule for item-less lines, or when none exist)
    rule = "document" if ns.itemless == "document" else "item"
    per_app = []
    for v, p in apps:
        win = window_days(p["pre_window_boundary"], p["composition_day"], days)
        pool = cover_pool(ins, t1, p["document"], win)
        rng = random.Random(SEED)
        rec = {"application": app_id(v, p), "regime": p["regime"], "arm": p["arm"]}
        rec["write"] = application_cover(p, by_app[app_id(v, p)], win, pool, idx, sbad, rng, rule)
        rec["any"] = application_cover(p, by_app[app_id(v, p)], win, pool, idx, sbad, random.Random(SEED), rule,
                                       kinds=("write", "read"))
        per_app.append(rec)
    out["rule"] = rule
    out["applications"] = per_app
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("join", "lines", "cover"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--itemless", choices=("uncoverable", "document"), default=None,
                    help="the coordinator's rule for lines whose anchor names no item (A1.2 stops without it)")
    ns = ap.parse_args(argv)
    res = {"join": cmd_join, "lines": cmd_lines, "cover": cmd_cover}[ns.cmd](ns)
    res = {"version": f"phase-a/a1-{ns.cmd}/v0", "brief": "briefs/36-phase-a-audits-2026-11-06.md", **res}
    Path(ns.out).parent.mkdir(parents=True, exist_ok=True)
    Path(ns.out).write_text(json.dumps(res, indent=1, default=list), encoding="utf-8")
    print("wrote", ns.out, sha256_file(Path(ns.out))[:8])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
