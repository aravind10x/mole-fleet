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


# ── v1 (brief 36 dated notes 3 and 4): rule (iii) ─────────────────────────────────────────

def item_triples(items: Sequence[str]) -> list[tuple[str, str, str]]:
    """The 20 triples of distinct items among a document's six (item-list order)."""
    return list(itertools.combinations(items, 3))


def item_multisets_with_repeat(items: Sequence[str]) -> list[tuple[str, str, str]]:
    """The 36 multisets of three items with at least one repeat (the same-item variant)."""
    return [t for t in itertools.combinations_with_replacement(items, 3) if len(set(t)) < 3]


def top_items(items: Sequence[str], counts: Mapping[str, int], k: int = 3) -> tuple[str, ...]:
    """The k items with the highest count, ties by the item list's order."""
    order = {it: i for i, it in enumerate(items)}
    return tuple(sorted(items, key=lambda it: (-counts.get(it, 0), order[it]))[:k])


def p3_exact(pool: Sequence[str], cov: Cover, groups: Sequence[Sequence[int]] | None = None,
             n_lines: int = 3) -> tuple[float, float]:
    """(strict, flexible) p3 over ALL triples of distinct pool accounts, exactly (feasibility does not
    depend on order, so the share over unordered triples equals the share over ordered ones). Only
    accounts with a covering session can contribute; a triple's other members are counted
    combinatorially. Strict: an assignment gives each account one line it covers. Flexible: the three
    accounts' sessions give each line (or each same-item group, when `groups` is given) its own session."""
    n = len(pool)
    total = math.comb(n, 3)
    if total == 0:
        return 0.0, 0.0
    C = [a for a in pool if any(u for u in cov.get(a, []))]
    z = n - len(C)
    covers = {a: frozenset(i for u in cov[a] for i in u) for a in C}
    gs = groups if groups is not None else [[i] for i in range(n_lines)]
    strict = flex = 0
    for k in (1, 2, 3):
        if 3 - k > z:
            continue
        mult = math.comb(z, 3 - k)
        for T in itertools.combinations(C, k):
            units = [u for a in T for u in cov[a]]
            if _match(gs, units):
                flex += mult
            if k == 3 and any(all(perm[j] in covers[T[j]] for j in range(3))
                              for perm in itertools.permutations(range(3))):
                strict += 1
    return strict / total, flex / total


def summarise_shared(vecs: Mapping[str, Sequence[float]], ratio: tuple[str, str] | None = None,
                     n_boot: int = N_BOOT, seed: int = SEED) -> dict[str, Any]:
    """Means over applications and percentile bootstrap intervals on ONE set of application resamples
    shared by every probability (so an ordering that holds per application, p1 <= p0, holds for the
    bounds). An all-zero probability takes the exact upper bound on the share of applications with any
    cover (dated note 2 item 2). `ratio` = (num, den): the ratio of means on the same resamples."""
    import numpy as np
    keys = list(vecs)
    V = {k: np.asarray(list(vecs[k]), float) for k in keys}
    n = len(next(iter(V.values())))
    assert all(len(v) == n for v in V.values()), "one vector per probability, the same applications"
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    out: dict[str, Any] = {"n": n, "replicates": n_boot, "seed": seed, "shared_resamples": True}
    boots = {}
    for k, v in V.items():
        b = v[idx].mean(axis=1)
        boots[k] = b
        nz = int((v > 0).sum())
        if nz == 0:
            out[k] = {"mean": 0.0, "lo": 0.0, "hi": cp_interval(0, n)[1], "all_zero": True, "n_nonzero": 0,
                      "bound": "clopper_pearson_on_applications_with_any_cover"}
        else:
            out[k] = {"mean": float(v.mean()), "lo": float(np.percentile(b, 2.5)), "hi": float(np.percentile(b, 97.5)),
                      "all_zero": False, "n_nonzero": nz, "bound": "bootstrap_over_applications"}
    if ratio is not None:
        num, den = ratio
        with np.errstate(divide="ignore", invalid="ignore"):
            r = boots[num] / boots[den]
        r = r[np.isfinite(r)]
        m = float(V[num].mean() / V[den].mean()) if V[den].mean() > 0 else None
        out["ratio"] = {"of": f"{num}/{den}", "mean": m,
                        "lo": float(np.percentile(r, 2.5)) if len(r) else None,
                        "hi": float(np.percentile(r, 97.5)) if len(r) else None}
    return out


def cell_key(app: Mapping[str, Any]) -> tuple:
    """Note 6's resampling unit: the (document, window, pool) cell. The pool is a function of the
    document and the window (`cover_pool`); its size is carried as a check."""
    return (app["document"], tuple(app["window"]), app["pool"])


def summarise_clustered(vecs: Mapping[str, Sequence[float]], clusters: Sequence[Any], ratio: tuple[str, str] | None = None,
                        n_boot: int = N_BOOT, seed: int = SEED) -> dict[str, Any]:
    """Note 6: the cluster bootstrap. Points are the means over applications, as before; each replicate
    draws clusters with replacement (one shared index set for every probability) and takes the
    application-weighted mean of the drawn clusters. An all-zero probability takes the exact upper bound
    on the share of CLUSTERS with any cover (0 of the cluster count)."""
    import numpy as np
    keys = list(vecs)
    V = {k: np.asarray(list(vecs[k]), float) for k in keys}
    n = len(next(iter(V.values())))
    assert len(clusters) == n and all(len(v) == n for v in V.values())
    ids = sorted(set(clusters), key=repr)
    pos = {c: i for i, c in enumerate(ids)}
    g = np.array([pos[c] for c in clusters])
    G = len(ids)
    cnt = np.bincount(g, minlength=G).astype(float)
    rng = np.random.default_rng(seed)
    draw = rng.integers(0, G, size=(n_boot, G))
    M = np.zeros((n_boot, G))
    for b in range(n_boot):
        M[b] = np.bincount(draw[b], minlength=G)
    den = M @ cnt
    out: dict[str, Any] = {"n": n, "clusters": G, "replicates": n_boot, "seed": seed, "shared_resamples": True}
    sums = {}
    for k, v in V.items():
        s = np.bincount(g, weights=v, minlength=G)
        sums[k] = s
        b = (M @ s) / den
        nzc = int((s > 0).sum())
        if nzc == 0:
            out[k] = {"mean": 0.0, "lo": 0.0, "hi": cp_interval(0, G)[1], "all_zero": True, "n_nonzero_clusters": 0,
                      "bound": "clopper_pearson_on_clusters_with_any_cover"}
        else:
            out[k] = {"mean": float(v.mean()), "lo": float(np.percentile(b, 2.5)), "hi": float(np.percentile(b, 97.5)),
                      "all_zero": False, "n_nonzero_clusters": nzc, "bound": "cluster_bootstrap"}
    if ratio is not None:
        num, den_k = ratio
        with np.errstate(divide="ignore", invalid="ignore"):
            r = (M @ sums[num]) / (M @ sums[den_k])
        r = r[np.isfinite(r)]
        out["ratio"] = {"of": f"{num}/{den_k}", "mean": float(V[num].mean() / V[den_k].mean()) if V[den_k].mean() > 0 else None,
                        "lo": float(np.percentile(r, 2.5)) if len(r) else None, "hi": float(np.percentile(r, 97.5)) if len(r) else None}
    return out


THRESH = 0.05


def outcome_map(s: Mapping[str, Any]) -> str:
    """Dated notes 2, 3 and 4: R1 every upper bound under 0.05; R2 p3's lower bound above p1's upper
    bound and p3's point at least 0.05; R3 (p0's upper bound at or above 0.05, p3's point under 0.05)
    split into R3a (p0's lower bound at or above 0.05 and p3/p0's upper bound under 1) and R3b; else
    unmapped. Reads the STRICT p3."""
    U0, U1, U3 = s["p0"]["hi"], s["p1"]["hi"], s["p3"]["hi"]
    L0, L3, P3 = s["p0"]["lo"], s["p3"]["lo"], s["p3"]["mean"]
    if U0 < THRESH and U1 < THRESH and U3 < THRESH:
        return "R1"
    if L3 > U1 and P3 >= THRESH:
        return "R2"
    if U0 >= THRESH and P3 < THRESH:
        rh = (s.get("ratio") or {}).get("hi")
        return "R3a" if (L0 >= THRESH and rh is not None and rh < 1) else "R3b"
    return "unmapped"


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


def acct_item_sessions(pool: Sequence[str], window: Sequence[str], doc: str,
                       sbad: Mapping[tuple[str, str], Sequence[str]], idx: Mapping[str, Mapping[str, Any]],
                       kinds: tuple[str, ...]) -> dict[str, list[frozenset]]:
    """{pool account: [the items each of its sessions in the window has a fed task of `kinds` naming on `doc`]}."""
    out = {}
    for a in pool:
        ss = []
        for d in window:
            for tid in sbad.get((a, d), []):
                ss.append(frozenset(t.item for t in idx[tid]["tasks"] if t.doc == doc and t.kind in kinds))
        out[a] = ss
    return out


def triple_cov(sess: Mapping[str, Sequence[frozenset]], lines: Sequence[str | None]) -> dict[str, list[set]]:
    return {a: [{j for j, it in enumerate(lines) if it is not None and it in s} for s in ss] for a, ss in sess.items()}


def probs(pool: Sequence[str], cov: Cover, groups: Sequence[Sequence[int]] | None = None) -> dict[str, float]:
    s, f = p3_exact(pool, cov, groups)
    return {"p0": p0(pool, cov, 3), "p1": p1(pool, cov, 3, groups), "p3": s, "p3f": f}


def _mean_probs(rs: Sequence[Mapping[str, float]]) -> dict[str, float]:
    return {k: float(sum(r[k] for r in rs) / len(rs)) for k in ("p0", "p1", "p3", "p3f")}


def _groups_of(lines: Sequence[str]) -> list[list[int]]:
    g: dict[str, list[int]] = defaultdict(list)
    for i, it in enumerate(lines):
        g[it].append(i)
    return list(g.values())


def write_variant_counts() -> dict[str, Counter]:
    """{document: Counter(item -> number of bank v6 WRITE variants naming it)} from A1.0's parse."""
    import yaml
    b = yaml.safe_load(BANK.read_text(encoding="utf-8"))
    out: dict[str, Counter] = defaultdict(Counter)
    for team, v in b.items():
        for txt in v["variants"]:
            p = parse_task(txt)
            if p is not None and p.kind == "write":
                out[p.doc][p.item] += 1
    return out


def cmd_cover_v1(ns) -> dict[str, Any]:
    rows, transcripts = read_jsonl(CORPUS), read_jsonl(TRANSCRIPTS)
    idx = session_index(transcripts)
    days = sorted({s["day"] for s in idx.values()})
    plants = _load_plants()
    payloads = {v: load_payloads(v) for v in PLANTS}
    lines = build_lines(plants, payloads, idx, days)
    by_app: dict[str, list[dict]] = defaultdict(list)
    for ln in lines:
        by_app[ln["application"]].append(ln)
    ins, t1 = build_inserter(rows)
    chk = pool_check(ins, t1, plants, payloads)
    sbad = _sessions_by_acct_day(idx)
    wvc = write_variant_counts()
    ex_ante = {d: top_items(ITEMS[d], wvc[d]) for d in rc.DOC_PATHS}
    W, ANY = ("write",), ("write", "read")
    apps = []
    for v, ps in plants.items():
        for p in ps:
            doc = p["document"]
            win = window_days(p["pre_window_boundary"], p["composition_day"], days)
            pool = cover_pool(ins, t1, doc, win)
            sw = acct_item_sessions(pool, win, doc, sbad, idx, W)
            sa = acct_item_sessions(pool, win, doc, sbad, idx, ANY)
            tri = item_triples(ITEMS[doc])
            rec: dict[str, Any] = {"application": app_id(v, p), "regime": p["regime"], "arm": p["arm"], "document": doc,
                                   "window": win, "pool": len(pool)}
            rec["write_mean"] = _mean_probs([probs(pool, triple_cov(sw, t)) for t in tri])
            rec["any_mean"] = _mean_probs([probs(pool, triple_cov(sa, t)) for t in tri])
            ms = item_multisets_with_repeat(ITEMS[doc])
            rec["write_same_item_mean"] = _mean_probs([probs(pool, triple_cov(sw, t), _groups_of(t)) for t in ms])
            rec["ex_ante_triple"] = list(ex_ante[doc])
            rec["write_ex_ante"] = probs(pool, triple_cov(sw, ex_ante[doc]))
            if len(win) < len(days):
                outside = [d for d in days if d not in win]
                # covering write SESSIONS per item on the days outside the window (every account)
                cnt = Counter(it for s in idx.values() if s["day"] in outside
                              for it in {t.item for t in s["tasks"] if t.doc == doc and t.kind == "write"})
                ot = top_items(ITEMS[doc], cnt)
                rec["outside_days_triple"] = list(ot)
                rec["write_outside_days"] = probs(pool, triple_cov(sw, ot))
            doc_cov = {a: [{0, 1, 2} if s else set() for s in ss] for a, ss in sw.items()}
            rec["write_document_level"] = probs(pool, doc_cov)
            lit = [ln["item"] for ln in sorted(by_app[app_id(v, p)], key=lambda x: x["statement"])]
            rec["literal_payload_items"] = probs(pool, triple_cov(sw, lit))
            named = [x for x in lit if x is not None]
            rec["payload_lines_share_an_item"] = len(named) != len(set(named))
            if p["arm"] == "k3":
                rec["time_axis"] = {}
                comp = p["composition_day"]
                upto = [d for d in days if d <= comp]
                for L in (1, 2, 3):
                    wL = upto[-L:]
                    poolL = cover_pool(ins, t1, doc, wL)
                    swL = acct_item_sessions(poolL, wL, doc, sbad, idx, W)
                    rec["time_axis"][str(L)] = {"pool": len(poolL),
                                                **_mean_probs([probs(poolL, triple_cov(swL, t)) for t in tri])}
            apps.append(rec)
    groups = {"conforming": ["conforming"], "middle": ["middle"], "routine_redraw": ["routine_redraw"],
              "governing": list(GOVERNING_REGIMES), "alarming": ["alarming"], "sham": ["sham"],
              "sham_redraw": ["sham_redraw"], "all": ["alarming", "conforming", "sham", "middle", "routine_redraw", "sham_redraw"]}
    variants = ("write_mean", "any_mean", "write_same_item_mean", "write_ex_ante", "write_document_level",
                "literal_payload_items")
    agg: dict[str, Any] = {}
    for g, regs in groups.items():
        sel = [a for a in apps if a["regime"] in regs]
        agg[g] = {"n": len(sel)}
        for var in variants:
            vecs = {k: [a[var][k] for a in sel] for k in ("p0", "p1", "p3", "p3f")}
            s = summarise_shared(vecs, ratio=("p3", "p0"))
            s["map"] = outcome_map(s)
            agg[g][var] = s
        so = [a for a in sel if "write_outside_days" in a]
        if so:
            s = summarise_shared({k: [a["write_outside_days"][k] for a in so] for k in ("p0", "p1", "p3", "p3f")},
                                 ratio=("p3", "p0"))
            s["map"] = outcome_map(s)
            agg[g]["write_outside_days_1_2_day_windows"] = s
        k3 = [a for a in sel if "time_axis" in a]
        if k3:
            agg[g]["time_axis"] = {}
            for L in ("1", "2", "3"):
                s = summarise_shared({k: [a["time_axis"][L][k] for a in k3] for k in ("p0", "p1", "p3", "p3f")},
                                     ratio=("p3", "p0"))
                s["map"] = outcome_map(s)
                agg[g]["time_axis"][L] = s
    gov = [a for a in apps if a["regime"] in GOVERNING_REGIMES]
    # pooled counts (descriptive only: the units are correlated; never a bound)
    pooled = {}
    for k, den_of in (("p0", lambda a: 3 * a["pool"]), ("p1", lambda a: a["pool"]), ("p3", lambda a: math.comb(a["pool"], 3)),
                      ("p3f", lambda a: math.comb(a["pool"], 3))):
        num = sum(round(a["write_mean"][k] * den_of(a) * 20) for a in gov)
        den = sum(den_of(a) * 20 for a in gov)
        pooled[k] = {"numerator": num, "denominator": den, "share": num / den if den else None,
                     "clopper_pearson_descriptive": cp_interval(num, den) if den else None}
    out = {
        "rule": "(iii): each document's 20 item triples on each application's own window and pool (dated notes 3 and 4)",
        "map_reads": "governing pool, write-task cover, mean over the 20 triples, strict p3; shared application resamples",
        "pool_rebuild_check": chk, "ex_ante_triples": {d: list(t) for d, t in ex_ante.items()},
        "write_variant_counts": {d: dict(c) for d, c in wvc.items()},
        "reading": agg["governing"]["write_mean"]["map"],
        "aggregates": agg, "pooled_counts_descriptive": pooled,
        "literal_i": {"applications_with_p1_zero": sum(1 for a in apps if a["literal_payload_items"]["p1"] == 0),
                      "applications_with_p3_zero": sum(1 for a in apps if a["literal_payload_items"]["p3"] == 0),
                      "applications": len(apps),
                      "applications_whose_named_lines_share_an_item": sum(1 for a in apps if a["payload_lines_share_an_item"])},
        "applications": apps, "inputs": _inputs(),
    }
    def fmt(s):
        return {k: (round(s[k]["mean"], 4), round(s[k]["lo"], 4), round(s[k]["hi"], 4)) for k in ("p0", "p1", "p3", "p3f")} | \
               {"ratio": (s["ratio"]["mean"] and round(s["ratio"]["mean"], 3), s["ratio"]["lo"] and round(s["ratio"]["lo"], 3),
                          s["ratio"]["hi"] and round(s["ratio"]["hi"], 3)), "map": s["map"]}
    print(json.dumps({"pool_rebuild_check": chk, "ex_ante": out["ex_ante_triples"], "literal_i": out["literal_i"]}, indent=1))
    for g in ("conforming", "middle", "routine_redraw", "governing", "all"):
        print(g, agg[g]["n"])
        for var in variants:
            print("  ", var, fmt(agg[g][var]))
        if "write_outside_days_1_2_day_windows" in agg[g]:
            print("   outside_days(1-2 day windows)", agg[g]["write_outside_days_1_2_day_windows"]["n"],
                  fmt(agg[g]["write_outside_days_1_2_day_windows"]))
        for L, s in (agg[g].get("time_axis") or {}).items():
            print("   time_axis", L, s["n"], fmt(s))
    print("READING (governing, write, mean over triples, strict p3):", out["reading"])
    return out


def tied_top_triples(items: Sequence[str], counts: Mapping[str, int]) -> list[tuple[str, ...]]:
    """Every triple that is the top three under SOME tie-break: items above the third-highest count
    are in all of them; items at it fill the rest in every combination (item-list order)."""
    c3 = sorted((counts.get(it, 0) for it in items), reverse=True)[2]
    above = [it for it in items if counts.get(it, 0) > c3]
    at = [it for it in items if counts.get(it, 0) == c3]
    order = {it: i for i, it in enumerate(items)}
    return [tuple(sorted(above + list(c), key=order.get)) for c in itertools.combinations(at, 3 - len(above))]


def hypothesis(s: float, q: float) -> dict[str, float]:
    """The sparse-regime formulas (brief 36 A1.2), labelled hypothesis: s*q for p0, (s*q)^3 for p1,
    (3*s*q)^3 for p3."""
    return {"sq": s * q, "sq_cubed": (s * q) ** 3, "three_sq_cubed": (3 * s * q) ** 3}


def cmd_cover_v1_addendum(ns) -> dict[str, Any]:
    """Note 5 item 2(a): the ex-ante triple as the mean over the tied top triples, and the hypothesis
    formulas at the measured q-hat and s, beside the measured p0, p1, p3 (no v1 figure changes)."""
    rows, transcripts = read_jsonl(CORPUS), read_jsonl(TRANSCRIPTS)
    idx = session_index(transcripts)
    days = sorted({s["day"] for s in idx.values()})
    plants = _load_plants()
    ins, t1 = build_inserter(rows)
    sbad = _sessions_by_acct_day(idx)
    wvc = write_variant_counts()
    tied = {d: tied_top_triples(ITEMS[d], wvc[d]) for d in rc.DOC_PATHS}
    apps = []
    for v, ps in plants.items():
        for p in ps:
            doc = p["document"]
            win = window_days(p["pre_window_boundary"], p["composition_day"], days)
            pool = cover_pool(ins, t1, doc, win)
            sw = acct_item_sessions(pool, win, doc, sbad, idx, ("write",))
            per = [probs(pool, triple_cov(sw, t)) for t in tied[doc]]
            n_sess_pool = sum(len(ss) for ss in sw.values())
            all_sess = [tid for d in win for (a, dd), tids in sbad.items() if dd == d for tid in tids]
            cover_counts = {it: sum(1 for ss in sw.values() for s in ss if it in s) for it in ITEMS[doc]}
            cover_all = {it: sum(1 for tid in all_sess if any(t.doc == doc and t.item == it and t.kind == "write"
                                                                 for t in idx[tid]["tasks"])) for it in ITEMS[doc]}
            s_ = n_sess_pool / len(pool) if pool else 0.0
            q_pool = (sum(cover_counts.values()) / len(ITEMS[doc]) / n_sess_pool) if n_sess_pool else 0.0
            q_all = (sum(cover_all.values()) / len(ITEMS[doc]) / len(all_sess)) if all_sess else 0.0
            apps.append({"application": app_id(v, p), "regime": p["regime"], "document": doc,
                         "tied_triples": [list(t) for t in tied[doc]], "tied_per_triple": per,
                         "tied_mean": _mean_probs(per), "s": s_, "q_hat_pool": q_pool, "q_hat_all_sessions": q_all,
                         "hypothesis_pool": hypothesis(s_, q_pool), "hypothesis_all_sessions": hypothesis(s_, q_all)})
    out: dict[str, Any] = {"tied_top_triples": {d: [list(t) for t in ts] for d, ts in tied.items()}}
    for g, regs in (("governing", GOVERNING_REGIMES), ("all", ("alarming", "conforming", "sham", "middle", "routine_redraw", "sham_redraw"))):
        sel = [a for a in apps if a["regime"] in regs]
        s = summarise_shared({k: [a["tied_mean"][k] for a in sel] for k in ("p0", "p1", "p3", "p3f")}, ratio=("p3", "p0"))
        s["map"] = outcome_map(s)
        # the range over each document's four tied triples (the mean over that document's applications)
        rng_ = {}
        for d in rc.DOC_PATHS:
            sd = [a for a in sel if a["document"] == d]
            if sd:
                k = len(tied[d])
                rng_[d] = {m: [min(sum(a["tied_per_triple"][i][m] for a in sd) / len(sd) for i in range(k)),
                               max(sum(a["tied_per_triple"][i][m] for a in sd) / len(sd) for i in range(k))]
                           for m in ("p0", "p1", "p3")}
        hyp = {f"mean_over_applications_{basis}": {k: sum(a[f"hypothesis_{basis}"][k] for a in sel) / len(sel)
                                                   for k in ("sq", "sq_cubed", "three_sq_cubed")}
               for basis in ("pool", "all_sessions")}
        sbar = sum(a["s"] for a in sel) / len(sel)
        qbar = sum(a["q_hat_pool"] for a in sel) / len(sel)
        qbar_all = sum(a["q_hat_all_sessions"] for a in sel) / len(sel)
        hyp["at_mean_s_and_q_pool"] = {"s": sbar, "q_hat": qbar, **hypothesis(sbar, qbar)}
        hyp["at_mean_s_and_q_all_sessions"] = {"s": sbar, "q_hat": qbar_all, **hypothesis(sbar, qbar_all)}
        out[g] = {"n": len(sel), "tied_mean": s, "tied_range_by_document": rng_, "hypothesis": hyp}
    out["applications"] = apps
    out["inputs"] = _inputs()
    g = out["governing"]
    print(json.dumps({"tied": out["tied_top_triples"],
                      "governing_tied_mean": {k: (round(g["tied_mean"][k]["mean"], 5), round(g["tied_mean"][k]["lo"], 5),
                                                  round(g["tied_mean"][k]["hi"], 5)) for k in ("p0", "p1", "p3", "p3f")},
                      "map": g["tied_mean"]["map"], "ratio": g["tied_mean"]["ratio"],
                      "range_p3": {d.split("/")[-1]: [round(x, 5) for x in r["p3"]] for d, r in g["tied_range_by_document"].items()},
                      "hypothesis": {k: {kk: round(vv, 6) for kk, vv in v.items()} for k, v in g["hypothesis"].items()}}, indent=1))
    return out


COVER_V1 = ROOT / "stage3" / "phase-a" / "a1-cover-v1.json"
COVER_V1_ADD = ROOT / "stage3" / "phase-a" / "a1-cover-v1-addendum.json"


def cmd_cover_v1_cells(ns) -> dict[str, Any]:
    """Note 6: every interval of a1-cover-v1 re-bootstrapped with the (document, window, pool) cell as the
    unit (2,000 resamples on one shared index set, seed 20261106), the six documents as the unit beside;
    points unchanged; the map re-read under the cell bounds with note 2's thresholds. Reads the two
    records and adds the cell-level fields beside the old ones; nothing is recomputed from the corpus."""
    d = json.loads(COVER_V1.read_text(encoding="utf-8"))
    add = json.loads(COVER_V1_ADD.read_text(encoding="utf-8"))
    apps = d["applications"]
    groups = {"conforming": ["conforming"], "middle": ["middle"], "routine_redraw": ["routine_redraw"],
              "governing": list(GOVERNING_REGIMES), "alarming": ["alarming"], "sham": ["sham"],
              "sham_redraw": ["sham_redraw"], "all": ["alarming", "conforming", "sham", "middle", "routine_redraw", "sham_redraw"]}
    variants = ("write_mean", "any_mean", "write_same_item_mean", "write_ex_ante", "write_document_level", "literal_payload_items")
    P = ("p0", "p1", "p3", "p3f")

    def both(sel, var_of, key_of):
        vecs = {k: [var_of(a)[k] for a in sel] for k in P}
        sc = summarise_clustered(vecs, [key_of(a) for a in sel], ratio=("p3", "p0"))
        sd = summarise_clustered(vecs, [a["document"] for a in sel], ratio=("p3", "p0"))
        sc["map"], sd["map"] = outcome_map(sc), outcome_map(sd)
        return sc, sd

    cells, docs, ncells = {}, {}, {}
    for g, regs in groups.items():
        sel = [a for a in apps if a["regime"] in regs]
        ncells[g] = len({cell_key(a) for a in sel})
        cells[g], docs[g] = {"n": len(sel), "cells": ncells[g]}, {"n": len(sel), "documents": len({a["document"] for a in sel})}
        for var in variants:
            cells[g][var], docs[g][var] = both(sel, lambda a, v=var: a[v], cell_key)
        so = [a for a in sel if "write_outside_days" in a]
        if so:
            cells[g]["write_outside_days_1_2_day_windows"], docs[g]["write_outside_days_1_2_day_windows"] = \
                both(so, lambda a: a["write_outside_days"], cell_key)
        k3 = [a for a in sel if "time_axis" in a]
        if k3:
            cells[g]["time_axis"], docs[g]["time_axis"] = {}, {}
            for L in ("1", "2", "3"):
                cells[g]["time_axis"][L], docs[g]["time_axis"][L] = both(
                    k3, lambda a, L=L: a["time_axis"][L], lambda a, L=L: (a["document"], L, a["time_axis"][L]["pool"]))
                cells[g]["time_axis"][L]["cells"] = len({(a["document"], a["time_axis"][L]["pool"]) for a in k3})
    by_id = {a["application"]: a for a in apps}
    add_cells = {}
    for g in ("governing", "all"):
        sel = [a for a in add["applications"] if a["regime"] in groups[g]]
        sc, sd = both(sel, lambda a: a["tied_mean"], lambda a: cell_key(by_id[a["application"]]))
        add_cells[g] = {"cells": len({cell_key(by_id[a["application"]]) for a in sel}), "tied_mean_cells": sc,
                        "tied_mean_documents": sd}
    note = ("brief 36 dated note 6 (post-look, labelled): intervals re-bootstrapped with the (document, window, pool) cell as "
            "the unit, the six documents beside; points unchanged; the per-application intervals above are too narrow")
    d["cells"] = {"note": note, "unit": "(document, window, pool) cell; cluster bootstrap, application-weighted",
                  "replicates": N_BOOT, "seed": SEED, "cells_per_group": ncells,
                  "reading_cells": cells["governing"]["write_mean"]["map"],
                  "reading_documents": docs["governing"]["write_mean"]["map"],
                  "aggregates_cells": cells, "aggregates_documents": docs}
    add["cells"] = {"note": note, **add_cells}
    COVER_V1.write_text(json.dumps(d, indent=1, default=list), encoding="utf-8")
    COVER_V1_ADD.write_text(json.dumps(add, indent=1, default=list), encoding="utf-8")

    def f(s):
        return {k: (round(s[k]["mean"], 5), round(s[k]["lo"], 5), round(s[k]["hi"], 5)) for k in P} | \
               {"ratio": tuple(round(x, 4) if isinstance(x, float) else x for x in (s["ratio"]["mean"], s["ratio"]["lo"], s["ratio"]["hi"])),
                "map": s["map"]}
    print("cells per group", ncells)
    for g in ("governing", "conforming", "middle", "routine_redraw", "all"):
        print(g, cells[g]["n"], cells[g]["cells"])
        for var in variants + ("write_outside_days_1_2_day_windows",):
            if var in cells[g]:
                print("  cells", var, f(cells[g][var]))
                print("  docs ", var, f(docs[g][var]))
        for L, s in (cells[g].get("time_axis") or {}).items():
            print("  cells time_axis", L, s["n"], s["cells"], f(s))
            print("  docs  time_axis", L, f(docs[g]["time_axis"][L]))
    for g, v in add_cells.items():
        print("addendum", g, v["cells"], "cells", f(v["tied_mean_cells"]), "docs", f(v["tied_mean_documents"]))
    print("READING over cells:", d["cells"]["reading_cells"], "over documents:", d["cells"]["reading_documents"])
    return {"wrote": [str(COVER_V1), str(COVER_V1_ADD)], "sha256": {str(COVER_V1): sha256_file(COVER_V1),
                                                                   str(COVER_V1_ADD): sha256_file(COVER_V1_ADD)}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("join", "lines", "cover", "cover-v1", "cover-v1-addendum", "cover-v1-cells"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--itemless", choices=("uncoverable", "document"), default=None,
                    help="the coordinator's rule for lines whose anchor names no item (A1.2 stops without it)")
    ns = ap.parse_args(argv)
    res = {"join": cmd_join, "lines": cmd_lines, "cover": cmd_cover, "cover-v1": cmd_cover_v1,
           "cover-v1-addendum": cmd_cover_v1_addendum, "cover-v1-cells": cmd_cover_v1_cells}[ns.cmd](ns)
    if ns.cmd == "cover-v1-cells":
        # the cell fields are written into the two v1 records in place; --out holds only the run's receipt
        Path(ns.out).parent.mkdir(parents=True, exist_ok=True)
        Path(ns.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
        print("receipt", ns.out)
        return 0
    ver = {"cover-v1": "phase-a/a1-cover/v1", "cover-v1-addendum": "phase-a/a1-cover/v1-addendum"}.get(
        ns.cmd, f"phase-a/a1-{ns.cmd}/v0")
    res = {"version": ver, "brief": "briefs/36-phase-a-audits-2026-11-06.md", **res}
    Path(ns.out).parent.mkdir(parents=True, exist_ok=True)
    Path(ns.out).write_text(json.dumps(res, indent=1, default=list), encoding="utf-8")
    print("wrote", ns.out, sha256_file(Path(ns.out))[:8])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
