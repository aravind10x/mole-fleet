#!/usr/bin/env python3
"""Line P3-U: realised use of each item in the honest log (blue side; $0; no model call; no planted file).

The question: on this world's honest log (`prefix_rw_v2c`, the corpus the follower test's slots come from),
how often does honest work carry an item's current value into a state-changing action? Realised use on this
task bank, not need; it is not to be multiplied by any uptake rate.

Rule (written and tested before any count; `test_stage3_p3_use.py`):

  events     every row of the honest corpus, in timestamp order (file order breaks ties). A session is a row's
             `task_id`; a day is `ts[:10]`.
  unit       a successful state-changing action (a content write, a mkdir, a share, a message, an email, a
             ticket or issue action, a registry, eval or secrets action: the explicit list `STATE_CHANGING`) by a
             session that is not the one that last wrote the slot. The session that last wrote a slot is the
             session of the write that last changed the slot's content in its document (none for the day-0 seed).
  value      the slot's content as of the action: the document's state after every content write that comes
             before the action in the event order, read through the slot's locator (`stage3_ft_slots`).
  carries    the value appears in the action's content by the matching the slot kinds already define
             (`stage3_ft_tasks_validate`): the whole value, bounded, whitespace-normalised and case-insensitive, or
             a distinctive token of it (a backticked span, a #channel, a path, a word with a digit or underscore)
             that the slot's locator does not already carry. A section slot's value is its direct lines. The
             action's content is what it sends (`action_content`): for an edit the added or replacing text, for a
             write the document text, for a message, mail or ticket its text fields; never the audit layer's copy
             of the document.
  specific   a carry is also *specific* when it matches a needle that is not a date, a bare number or a token under
             six characters (`needle_class`): a shared date or a small number is a weak carry (the same literal turns
             up in unrelated text), so both counts are given.
  excluded   and counted apart, per slot and day: `edits` (a write to the slot's document that changes the slot
             itself), `copies` (a write of the whole document: a `write_file` to the slot's document, or any
             action whose content holds the document's whole current text) and `same_session` (the session that
             last wrote the slot). A slot absent from the document's current state gives no unit.

Per slot and day: units, units with content, carrying actions (any match; and by a whole value), distinct
sessions carrying, sessions that read the slot's document that day, and the excluded counts. Totals by
document, slot kind and granularity, and the share of slots never carried in the whole log.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_p3_use.py
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_ft_slots as fs  # noqa: E402
import stage3_ft_tasks_validate as tv  # noqa: E402
import stage3_t1v2_checks as vc  # noqa: E402

VERSION = "p3-use/v0"
OUT = fs.WORK / "stage3" / "v5" / "P3"
SLOTS = fs.OUT_DIR / "slots-v0.json"

#: state-changing actions, by action name: content writes, directory and sharing changes, messages and mail,
#: ticket actions, registry, eval-server and secrets actions, group changes.
STATE_CHANGING = frozenset({
    "write_file", "append_to_file", "replace_in_file", "mkdir", "delete", "share", "public_link",
    "send_email", "reply_email",
    "post_message", "send_direct_message", "create_channel",
    "create_issue", "update_issue", "transition_issue", "add_comment", "create_project",
    "register_checkpoint", "ensure_checkpoint", "tag_approved", "deploy",
    "submit_eval", "create_config", "update_config", "cancel_job", "redeploy", "run_reference_suite",
    "set_access_policy", "rotate", "add_group_member",
})
#: the argument keys that carry what an action says (its content), searched through nested values.
CONTENT_KEYS = ("text", "content", "body", "message", "comment", "subject", "name", "description", "patch", "config",
                "eval_config", "reason", "title", "value", "data", "label", "labels")
READ_ACTIONS = ("read_file", "read_bytes")


# ── rows, events, content ────────────────────────────────────────────────────────────────────

def sort_rows(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Rows in timestamp order; the file order breaks ties (a stable sort on the timestamp string)."""
    return sorted(rows, key=lambda r: str(r.get("ts") or ""))


def events_from_rows(sorted_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{"pos": i, "ts": str(r.get("ts") or ""), "session": r.get("task_id"), "service": r.get("service"),
             "action": r.get("action"), "args": r.get("args") or {}, "ok": (r.get("exit_code") or 0) == 0}
            for i, r in enumerate(sorted_rows)]


def is_state_changing(e: Mapping[str, Any]) -> bool:
    return bool(e["ok"]) and e["action"] in STATE_CHANGING


def _leaves(v: Any) -> list[str]:
    if isinstance(v, str):
        return [v]
    if isinstance(v, Mapping):
        return [s for x in v.values() for s in _leaves(x)]
    if isinstance(v, (list, tuple)):
        return [s for x in v for s in _leaves(x)]
    return []


def action_content(e: Mapping[str, Any]) -> str:
    """What the action sends. An edit: the added or replacing text (never the audit layer's `content` and
    `edit`, nor `find`); a whole write: the document text; anything else: its text fields."""
    a, act = e["args"], e["action"]
    if act == "append_to_file":
        return str(a.get("text") or "")
    if act == "replace_in_file":
        return str(a.get("replace") or "")
    if act == "write_file":
        return "\n".join(a[k] for k in ("content", "body") if isinstance(a.get(k), str))
    return "\n".join(s for k in CONTENT_KEYS if k in a for s in _leaves(a[k]))


# ── matching ─────────────────────────────────────────────────────────────────────────────────

_BOUNDED: dict[str, re.Pattern[str]] = {}


def _hit(needle: str, hay: str) -> bool:
    if needle not in hay:
        return False
    pat = _BOUNDED.get(needle)
    if pat is None:
        pat = _BOUNDED[needle] = vc.bounded(needle)
    return pat.search(hay) is not None


_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_NUMERIC = re.compile(r"^[\d.:,-]+$")


def needle_class(n: str) -> str:
    """date, numeric (digits and . : , - only), short (under six characters) or specific. A shared date, a bare
    number or a short token is a weak carry: the same literal turns up in unrelated text."""
    if _DATE.match(n):
        return "date"
    if _NUMERIC.match(n):
        return "numeric"
    if len(n) < 6:
        return "short"
    return "specific"


def _needles(values: Sequence[str], locator: str) -> tuple[list[tuple[str, bool]], list[tuple[str, bool]]]:
    """(whole values, distinctive tokens the locator does not carry), each normalised, lower-cased and flagged
    specific or not."""
    whole, toks = [], []
    for v in values:
        if not v.strip():
            continue
        n = vc.norm(v).lower()
        whole.append((n, needle_class(n) == "specific"))
        for t in tv.distinctive_tokens(v):
            if not vc.occurs(t, locator):
                n = vc.norm(t).lower()
                toks.append((n, needle_class(n) == "specific"))
    return whole, toks


# ── the analysis ─────────────────────────────────────────────────────────────────────────────

_FIELDS = ("units", "units_with_content", "carrying", "carrying_whole", "carrying_specific", "edits", "copies", "same_session")


def analyse(events: Sequence[Mapping[str, Any]], states: Mapping[str, Sequence[Mapping[str, Any]]],
            slots: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Counts per slot and day over `events` (already in timestamp order, `pos` their position) against
    `states` ({document: [{idx, ts, text, pos, session}]}: idx 0 the seed, then one state per content write, `pos`
    the write's event position and `session` its writer) and the slot inventory."""
    days = sorted({e["ts"][:10] for e in events})
    write_at: dict[int, tuple[str, int]] = {}
    write_pos: dict[str, list[int]] = {}
    for doc, lst in states.items():
        for i, s in enumerate(lst):
            if s["idx"] != i:
                raise ValueError(f"{doc}: state indices must be 0..n-1 in order")
        write_pos[doc] = [s["pos"] for s in lst if s["pos"] is not None]
        for s in lst:
            if s["pos"] is not None:
                write_at[s["pos"]] = (doc, s["idx"])
    doc_norm = {d: [vc.norm(s["text"]).lower() for s in lst] for d, lst in states.items()}
    mapping = {d: [(s["idx"], s["ts"], s["text"]) for s in lst] for d, lst in states.items()}

    info: dict[str, dict[str, Any]] = {}
    for s in slots:
        contents = fs.slot_contents(mapping, s)
        doc = s["document"]
        lw: list[Any] = []
        for k, st in enumerate(states[doc]):
            if k == 0:
                lw.append(None)
            else:
                lw.append(st["session"] if contents.get(k) != contents.get(k - 1) else lw[k - 1])
        info[s["slot_id"]] = {"doc": doc, "contents": contents, "last_writer": lw, "needles": {}, "loc": s["locator"]}

    reads: dict[tuple[str, str], set] = defaultdict(set)
    first_read: dict[tuple[str, Any], int] = {}
    for e in events:
        if e["ok"] and e["service"] == "owncloud" and e["action"] in READ_ACTIONS:
            doc = "/" + str(e["args"].get("path") or "").lstrip("/")
            reads[(doc, e["ts"][:10])].add(e["session"])
            first_read.setdefault((doc, e["session"]), e["pos"])

    cell_cnt: dict[tuple[str, str], Counter] = defaultdict(Counter)
    cell_carry: dict[tuple[str, str], set] = defaultdict(set)
    cell_carry_read: dict[tuple[str, str], set] = defaultdict(set)
    slot_sessions: dict[str, set] = defaultdict(set)
    per_action = Counter()
    carried_hist: Counter = Counter()
    n_sc = n_content = 0
    by_day_actions: dict[str, Counter] = defaultdict(Counter)
    by_action: dict[str, Counter] = defaultdict(Counter)
    for e in events:
        if not is_state_changing(e):
            continue
        day = e["ts"][:10]
        content = action_content(e)
        hay = vc.norm(content).lower()
        has = bool(hay)
        n_sc += 1
        n_content += has
        by_day_actions[day]["state_changing"] += 1
        by_day_actions[day]["with_content"] += has
        by_action[e["action"]]["state_changing"] += 1
        by_action[e["action"]]["with_content"] += has
        own = write_at.get(e["pos"])
        n_carried = n_spec = 0
        for sid, inf in info.items():
            doc = inf["doc"]
            k = bisect.bisect_left(write_pos[doc], e["pos"])
            cur = inf["contents"].get(k)
            if cur is None:
                continue
            c = cell_cnt[(sid, day)]
            if own is not None and own[0] == doc:
                if inf["contents"].get(own[1]) != cur:
                    c["edits"] += 1
                    continue
                if e["action"] == "write_file":
                    c["copies"] += 1
                    continue
            if has and doc_norm[doc][k] and doc_norm[doc][k] in hay:
                c["copies"] += 1
                continue
            lw = inf["last_writer"][k]
            if e["session"] is not None and e["session"] == lw:
                c["same_session"] += 1
                continue
            c["units"] += 1
            c["units_with_content"] += has
            if not has:
                continue
            nd = inf["needles"].get(k)
            if nd is None:
                nd = inf["needles"][k] = _needles(cur, inf["loc"])
            hits = [(n, sp) for n, sp in nd[0] + nd[1] if _hit(n, hay)]
            whole = any(_hit(n, hay) for n, _sp in nd[0])
            if hits:
                c["carrying"] += 1
                c["carrying_whole"] += whole
                spec = any(sp for _n, sp in hits)
                c["carrying_specific"] += spec
                n_spec += spec
                cell_carry[(sid, day)].add(e["session"])
                slot_sessions[sid].add(e["session"])
                fr = first_read.get((doc, e["session"]))
                if fr is not None and fr < e["pos"]:
                    cell_carry_read[(sid, day)].add(e["session"])
                n_carried += 1
        if n_carried:
            per_action["carrying_any_slot"] += 1
            carried_hist[n_carried] += 1
            by_day_actions[day]["carrying_any_slot"] += 1
            by_action[e["action"]]["carrying_any_slot"] += 1
        if n_spec:
            per_action["carrying_specific_any_slot"] += 1
            by_day_actions[day]["carrying_specific_any_slot"] += 1
            by_action[e["action"]]["carrying_specific_any_slot"] += 1

    cells: dict[tuple[str, str], dict[str, int]] = {}
    slot_totals: dict[str, dict[str, int]] = {}
    for s in slots:
        sid = s["slot_id"]
        tot = Counter()
        for d in days:
            c = cell_cnt.get((sid, d), Counter())
            rec = {f: int(c.get(f, 0)) for f in _FIELDS}
            rec["sessions_carrying"] = len(cell_carry.get((sid, d), ()))
            rec["sessions_carrying_after_reading"] = len(cell_carry_read.get((sid, d), ()))
            rec["sessions_reading"] = len(reads.get((s["document"], d), ()))
            cells[(sid, d)] = rec
            for f in _FIELDS:
                tot[f] += rec[f]
        slot_totals[sid] = {**{f: int(tot[f]) for f in _FIELDS}, "sessions_carrying": len(slot_sessions.get(sid, ()))}
    return {"days": days, "cells": cells, "slot_totals": slot_totals, "_slot_sessions": dict(slot_sessions),
            "actions": {"state_changing": n_sc, "state_changing_with_content": n_content,
                        "carrying_any_slot": per_action["carrying_any_slot"], "carrying_specific_any_slot": per_action["carrying_specific_any_slot"], "slots_carried_per_action": dict(sorted(carried_hist.items())),
                        "by_day": {d: dict(c) for d, c in sorted(by_day_actions.items())},
                        "by_action": {a: {f: int(c.get(f, 0)) for f in ("state_changing", "with_content", "carrying_any_slot", "carrying_specific_any_slot")} for a, c in sorted(by_action.items())}}}


def totals(res: Mapping[str, Any], slots: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Totals overall and by document, slot kind and granularity: slots, slots carried at least once, the share
    never carried, carrying actions summed over the group's slots, slot-days with a carrying action, distinct
    sessions carrying any of the group's slots."""
    def agg(group: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        n = len(group)
        carried = sum(res["slot_totals"][s["slot_id"]]["carrying"] > 0 for s in group)
        carried_sp = sum(res["slot_totals"][s["slot_id"]]["carrying_specific"] > 0 for s in group)
        sess: set = set()
        for s in group:
            sess |= res["_slot_sessions"].get(s["slot_id"], set())
        cd = sum(1 for s in group for d in res["days"] if res["cells"][(s["slot_id"], d)]["carrying"] > 0)
        sums = {f: sum(res["slot_totals"][s["slot_id"]][f] for s in group) for f in _FIELDS}
        return {"slots": n, "slots_carried": carried, "share_never_carried": (n - carried) / n if n else None,
                "slots_carried_specific": carried_sp, "share_never_carried_specific": (n - carried_sp) / n if n else None,
                "slot_days": n * len(res["days"]), "slot_days_carried": cd, "sessions_carrying_any": len(sess), **sums}

    def by(key: str) -> dict[str, Any]:
        groups: dict[str, list] = defaultdict(list)
        for s in slots:
            groups[s[key]].append(s)
        return {k: agg(v) for k, v in groups.items()}

    return {"all": agg(list(slots)), "by_document": by("document"), "by_kind": by("slot_kind"), "by_granularity": by("granularity")}


# ── the honest log ───────────────────────────────────────────────────────────────────────────

def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_world(order: str = "ts") -> dict[str, Any]:
    """Events in timestamp order, the class documents' states replayed in that order through the shared reader,
    and the slot inventory (`slots-v0.json`), plus the ordering diagnostics (file order against timestamp order)."""
    import stage3_views as sv
    rows = sv.read_jsonl(fs.CORPUS)
    srt = sort_rows(rows) if order == "ts" else list(rows)          # "file": the sensitivity, the corpus file's own order
    base = sv.seed_base()
    events = events_from_rows(srt)
    states: dict[str, list[dict[str, Any]]] = {}
    diag: dict[str, Any] = {}
    for p in sv.class_doc_paths():
        lst = [{"idx": 0, "ts": "seed", "text": base[("owncloud", p)], "pos": None, "session": None}]
        for ch in sv.document_timeline(srt, p, base):
            if ch.after is not None:
                lst.append({"idx": len(lst), "ts": str(ch.ts), "text": ch.after, "pos": ch.index, "session": ch.task_id})
        states[p] = lst
        file_tl = sv.document_timeline(rows, p, base)
        ts_file = [str(c.ts) for c in file_tl]
        diag[p] = {"writes": len(lst) - 1, "writes_out_of_ts_order_in_file": sum(1 for a, b in zip(ts_file, ts_file[1:]) if b < a),
                   "final_state_same_in_both_orders": (file_tl[-1].after if file_tl else None) == lst[-1]["text"]}
    slots = json.loads(SLOTS.read_text(encoding="utf-8"))
    return {"events": events, "states": states, "slots": slots, "diagnostics": diag, "n_rows": len(rows)}


# ── output ───────────────────────────────────────────────────────────────────────────────────

def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def build_record(world: Mapping[str, Any]) -> dict[str, Any]:
    res = analyse(world["events"], world["states"], world["slots"])
    tot = totals(res, world["slots"])
    short = {s["slot_id"]: s for s in world["slots"]}
    per_slot = []
    for s in world["slots"]:
        sid = s["slot_id"]
        per_slot.append({"slot_id": sid, "document": s["document"], "slot_kind": s["slot_kind"], "granularity": s["granularity"],
                         "total": res["slot_totals"][sid], "by_day": {d: res["cells"][(sid, d)] for d in res["days"]}})
    hist = Counter()
    for s in world["slots"]:
        n = res["slot_totals"][s["slot_id"]]["carrying"]
        hist["0" if n == 0 else "1" if n == 1 else "2-5" if n <= 5 else "6-20" if n <= 20 else "21+"] += 1
    return {"version": VERSION, "corpus": fs.CORPUS.name, "n_rows": world["n_rows"], "days": res["days"],
            "state_changing_actions": sorted(STATE_CHANGING), "content_keys": list(CONTENT_KEYS),
            "ordering_diagnostics": world["diagnostics"], "actions": res["actions"], "totals": tot,
            "carrying_actions_per_slot_histogram": {k: hist.get(k, 0) for k in ("0", "1", "2-5", "6-20", "21+")},
            "slots": per_slot, "slot_inventory_sha256": sha256_file(SLOTS)[:8],
            "script_sha256": sha256_file(Path(__file__).resolve())[:8]}


def render_md(rec: Mapping[str, Any]) -> str:
    t, a = rec["totals"], rec["actions"]
    A = t["all"]
    L = [f"# Realised use of each item in the honest log (`{rec['corpus'][:-6]}`, {VERSION})", "",
         "Counts only; no document text. **This is realised use on this task bank, not need, and it is not to be multiplied by any uptake rate.** "
         "Blue side, $0, no model call, no planted file.", "",
         "## What was counted", "",
         "- **Unit:** a successful state-changing action by a session that is not the one that last wrote the slot, events in timestamp order (file order breaks ties).",
         "- **Carries:** the slot's value as of the action (read through its locator) appears in the action's content, by the validator's matching: the whole value, bounded, normalised, case-insensitive; or a distinctive token of it that the locator does not already carry. `carrying_whole` counts the whole-value matches alone; `carrying, specific` leaves out matches that rest only on a date, a bare number or a token under six characters.",
         "- **Excluded, counted apart:** `edits` (a write to the slot's document that changes the slot), `copies` (a write of the whole document), `same_session` (the session that last wrote the slot).",
         f"- **Log:** {rec['n_rows']:,} rows on {len(rec['days'])} days ({', '.join(rec['days'])}). Successful state-changing actions: **{a['state_changing']:,}**, of which {a['state_changing_with_content']:,} have content; **{a['carrying_any_slot']:,}** of those carry at least one slot (as a unit), **{a['carrying_specific_any_slot']:,}** of them specifically.", ""]
    head = ["| group | slots | never carried | never carried (specific) | slot-action pairs (units) | carrying | carrying, specific | carrying, whole value | edits | copies | same session | slot-days carried | sessions carrying |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]

    def row(name: str, g: Mapping[str, Any]) -> str:
        return (f"| {name} | {g['slots']} | {g['slots'] - g['slots_carried']} ({_pct(g['share_never_carried'])}) | {g['slots'] - g['slots_carried_specific']} ({_pct(g['share_never_carried_specific'])}) | "
                f"{g['units']:,} | {g['carrying']:,} | {g['carrying_specific']:,} | {g['carrying_whole']:,} | {g['edits']:,} | {g['copies']:,} | {g['same_session']:,} | "
                f"{g['slot_days_carried']} / {g['slot_days']} | {g['sessions_carrying_any']} |")
    L += ["## Totals", ""] + head + [row("**all slots**", A)]
    for title, key in (("By document", "by_document"), ("By slot kind", "by_kind"), ("By granularity", "by_granularity")):
        L += ["", f"### {title}", ""] + head
        for k, g in t[key].items():
            L.append(row(k.split("/")[-1] if key == "by_document" else k, g))
    L += ["", "## By day", "", "| day | state-changing actions | with content | carrying at least one slot | of which specific |", "|---|---|---|---|---|"]
    for d, c in a["by_day"].items():
        L.append(f"| {d} | {c.get('state_changing', 0):,} | {c.get('with_content', 0):,} | {c.get('carrying_any_slot', 0):,} | {c.get('carrying_specific_any_slot', 0):,} |")
    L += ["", "## By action", "", "| action | state-changing | with content | carrying at least one slot | of which specific |", "|---|---|---|---|---|"]
    for k, c in a["by_action"].items():
        L.append(f"| {k} | {c['state_changing']:,} | {c['with_content']:,} | {c['carrying_any_slot']:,} | {c['carrying_specific_any_slot']:,} |")
    L += ["", "## Carrying actions per slot, whole log", "", "| carrying actions | 0 | 1 | 2-5 | 6-20 | 21+ |", "|---|---|---|---|---|---|",
          "| slots | " + " | ".join(str(rec["carrying_actions_per_slot_histogram"][k]) for k in ("0", "1", "2-5", "6-20", "21+")) + " |", "",
          "Slots carried by one action: how many slots a carrying action carries (action count by slots carried): "
          + ", ".join(f"{k} slot{'s' if int(k) != 1 else ''}: {v}" for k, v in a["slots_carried_per_action"].items()) + ".", "",
          "## Ordering", "",
          "File order is not timestamp order on any class document; the documents' states were replayed in timestamp order (file order breaks ties). Per document: writes, adjacent pairs out of timestamp order in the file, and whether the final state is the same in both orders.", "",
          "| document | writes | out of order in the file | final state the same |", "|---|---|---|---|"]
    for p, d in rec["ordering_diagnostics"].items():
        L.append(f"| {p.split('/')[-1]} | {d['writes']} | {d['writes_out_of_ts_order_in_file']} | {d['final_state_same_in_both_orders']} |")
    fo = rec.get("file_order_sensitivity")
    if fo:
        A0, F = t["all"], fo["all"]
        L += ["", "Sensitivity, the corpus file's own order instead of timestamp order (same rule, labelled; the timestamp order governs):", "",
              "| order | slots carried | slots carried, specific | carrying | carrying, specific | carrying actions (any slot) | edits | copies | same session |", "|---|---|---|---|---|---|---|---|---|",
              f"| timestamp (governing) | {A0['slots_carried']} | {A0['slots_carried_specific']} | {A0['carrying']:,} | {A0['carrying_specific']:,} | {a['carrying_any_slot']:,} | {A0['edits']:,} | {A0['copies']:,} | {A0['same_session']:,} |",
              f"| file | {F['slots_carried']} | {F['slots_carried_specific']} | {F['carrying']:,} | {F['carrying_specific']:,} | {fo['actions']['carrying_any_slot']:,} | {F['edits']:,} | {F['copies']:,} | {F['same_session']:,} |"]
    L += [""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out-dir", default=str(OUT))
    ns = ap.parse_args(argv)
    rec = build_record(load_world())
    alt = build_record(load_world("file"))          # sensitivity: the corpus file's own order instead of timestamp order
    rec["file_order_sensitivity"] = {"all": alt["totals"]["all"], "actions": {k: v for k, v in alt["actions"].items() if k in ("state_changing", "state_changing_with_content", "carrying_any_slot", "carrying_specific_any_slot")},
                                     "by_document_slots_carried": {d: g["slots_carried"] for d, g in alt["totals"]["by_document"].items()}}
    out = Path(ns.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "use-v0.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    (out / "use-v0.md").write_text(render_md(rec), encoding="utf-8")
    print(json.dumps({"actions": {k: v for k, v in rec["actions"].items() if k not in ("by_day", "by_action", "slots_carried_per_action")}, "all": rec["totals"]["all"], "hist": rec["carrying_actions_per_slot_histogram"]}, indent=1))
    print("wrote", out / "use-v0.json", sha256_file(out / "use-v0.json")[:8], out / "use-v0.md", sha256_file(out / "use-v0.md")[:8])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
