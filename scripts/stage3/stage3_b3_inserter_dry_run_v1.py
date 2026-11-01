#!/usr/bin/env python3
"""Brief 26 (B3): the edit-application dry run of S3's application module on every B3 item, before brief 20 Part 3.

A reproducibility check of the study's own tooling ($0, no API call): every item (the 78 quiet candidates, the 22
same-writer controls, the 24 comparison items of brief 23's v2 regime) and every line of it is applied in memory, by
the application module brief 15's Part S names (`stage3_t1.py`, the v3-amended inserter, unchanged), against
(i) the day-0 snapshot (the seeder's texts, as briefs 23 and 25 rendered them) and (ii) the document states Part S
will use, rebuilt through `mole.oracles.document` from the null corpus as brief 07h did. S1's seed stream is not
written, so every position the layout can draw is enumerated: for the lone arm, each day in `days[:2]` and each
author in the pool the module's own `draw_author` would draw from (captured, not re-implemented); at each draw the
module's `_plant_once` runs (two timestamp samples), and every document state the drawn sessions can reach is
checked line by line and for the item as a whole. A lone line of A6.8's singleton arm is applied through the
module's one-statement role path (the k = 3 role logic with one day), since the module has no singleton arm.

A line is checked against a state for: target found (replace: a line starting with the committed anchor; append: the
document exists), found exactly once (one anchored line, and the resolved line occurring once as a substring, since
the manager's replace hits the first occurrence), the line already present, and the document after the module's
application equal byte for byte to the intended document (the line put in place by line index, built here
independently of the module's substring rule). A draw is valid (A6.17.10 (c)) when every module run composes with
every line found once, not already present and byte-equal, and every reachable state passes the line checks and the
joint check (the item's lines applied in the module's order do not affect one another). Drops follow brief 26's rule
at T2+S2: two valid placements per item (on different days, by different authors, as Part S's layout places a second
placement) and two per lone line (by different authors); the literal count of valid draws is reported beside.

Outputs carry ids, booleans, counts, reason codes, days and honest account names only: no item line, anchor, rubric,
declared effect or document text (a guard refuses to write a file containing any of them).

Brief 32 v3 (B3 S2, H2 step 1; 2026-11-01): a copy of brief 26's script (`stage3_b3_inserter_dry_run.py` 999cb737,
pinned, not edited) with one opt-in, `--controls-lone-lines`. Without it the copy runs brief 26's method unchanged and
its `items[]` reproduce `inserter-dry-run-v0.json` (edd289ce). With it, each control item's three lines are also
enumerated as lone lines by the same method (the same `enumerate_draws`, the one-statement role path), and only the
control items' `lone_lines` (role order 1, 2, 3) change in `items[]`: a control's drop and its `lines[].lone_line` stay
brief 26's, since the control arm's need is the item pair and the add-on's need is decided by S3's tag-6 draw. The table
is written as `inserter-dry-run-v1.json`, of edd289ce's shape, for brief 27's restricted mode (`ValidDraws`) to read
unchanged. The copy never writes over the pinned `work/stage3/b3/inserter-dry-run-v0.{json,md}`.

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_inserter_dry_run_v1.py run --controls-lone-lines
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import multiprocessing as mp
import random
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_t1 as t1  # noqa: E402  (the application module, read and called, never changed)
import stage3_views as sv  # noqa: E402
from mole.oracles import document as doc  # noqa: E402

VERSION = "b3-inserter-dry-run/v0"
VERSION_V1 = "b3-inserter-dry-run/v1"         # brief 32: the table with the control items' lone lines
B26_SCRIPT_SHA256 = "999cb7375cdefe212335e307cef6120c702436be1c6d5270f621844750b3ddf5"
B26_JSON_SHA256 = "edd289ce14eae1be6d131562600b482539d0f7f3903fcdb33e524565c15af5e8"
PROJECT = HERE.parent.parent
S3 = PROJECT / "work" / "stage3"
OUT = S3 / "b3"
CORPUS = PROJECT / "work" / "mole-fork" / "data" / "corpus" / "spike" / "prefix_rw_v2c.jsonl"
RUN_SEED = "b3-inserter-dry-run-20261101"      # the timestamp samples of the module runs (not Part S's stream; S1 writes that)
RUNS_PER_DRAW = 2                              # placed module runs per draw
MAX_SAMPLES = 12                               # timestamp samples per draw at most (a "no second left" sample is re-drawn)
NEED_ITEM, NEED_LINE = 2, 2                    # T2+S2 (brief 20 Part 2): two placements per item, two per lone line
EXPECTED = {"candidate": 78, "control": 22, "sham": 24}
EXPECTED_POPS = {"78": 78, "28": 28, "19": 19, "21": 21}
# A6.17.1 and A6.17.2's figures (the strict two-family stratum; the resolved-anchor subset)
EXPECTED_POP_WRITERS = {"78": {"sonnet55": 41, "glm53": 37}, "28": {"glm53": 16, "sonnet55": 12},
                        "19": {"sonnet55": 12, "glm53": 7}, "21": {"glm53": 12, "sonnet55": 9}}
REGIME_NAME = {"candidate": "candidates", "control": "controls", "sham": "comparison"}
RATED_ARM = {"candidate": "distributed", "control": "control_samewriter", "sham": "sham"}
# the module's v3 manifest (work/stage3/t1v3/plants-v3.json) and the re-plant's record these
V3_INSERTER_CLASS_SHA256 = "24d3d147d6f5e6a052820714dfefebe2442aaeaf5f796cf299fe319c41027b4a"
V2C_CORPUS_SHA256 = "ffc1f6cd423cae68ac5bd752580f845a838625ebc57a9cf1e083d7e6ddaeeb74"

# reason codes (brief 26 D1's five classes; "other" named)
R_ABSENT = "target absent"
R_MULTI = "target found more than once"
R_PRESENT = "line already present"
R_CHANGED_BEFORE = "target line changed by a later routine edit (between day 0 and the placement)"
R_CHANGED_AFTER = "target line changed by a later routine edit (the applied line, before the module's composition check)"
R_DIFF = "other: the document after application differs from the intended result"
R_MULTILINE = "other: the line spans more than one line"
R_INTERFERE_SAME = "other: two lines of the item target the same line"
R_INTERFERE_TARGET = "other: an earlier line of the item removes or changes a later line's target"
R_INTERFERE_MATCH = "other: an earlier line of the item adds a second match for a later line's target"
R_INTERFERE_PRESENT = "other: an earlier line of the item already puts a later line in"
R_INTERFERE_COMPOSITE = "other: the lines applied in order differ from the lines put in place independently"
R_NO_DRAW = "other: no author the module can draw (no session in which every target resolves)"
R_NO_TIME = "other: no time left in the drawn session"
R_UNKNOWN_STATE = "other: document state unknown or absent"
R_NO_LANDING = "other: no line landed"
R_UNMAPPED = "other: unmapped module reason"
NOT_FOUND = {R_ABSENT, R_CHANGED_BEFORE, R_UNKNOWN_STATE}
BRIEF_CLASS = {R_ABSENT: "target absent", R_MULTI: "target found more than once", R_PRESENT: "line already present",
               R_CHANGED_BEFORE: "target line changed by a later routine edit",
               R_CHANGED_AFTER: "target line changed by a later routine edit"}


def brief_class(reason: str) -> str:
    return BRIEF_CLASS.get(reason, "other")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def file_sha256(p: Path) -> str:
    return sha256_bytes(Path(p).read_bytes())


# ── the line check and the intended document ───────────────────────────────────────────────────────

def intended(state: str, stmt: Mapping[str, Any], line: str) -> str:
    """The document with the line in place, by line index: a replace swaps the first line that starts with the anchor
    (keeping its line ending); an append adds the line as a new last line. Built independently of `t1.apply_edit`."""
    parts = state.splitlines(keepends=True)
    bare = state.splitlines()
    if stmt["op"] == "append":
        if parts and parts[-1] == bare[-1]:          # the last line has no line ending: it gets one
            parts[-1] += "\n"
        return "".join(parts) + line + "\n"
    i = next(k for k, ln in enumerate(bare) if ln.startswith(stmt["anchor"]))
    parts[i] = line + parts[i][len(bare[i]):]
    return "".join(parts)


def sent_of(state: str, stmt: Mapping[str, Any], line: str) -> tuple[str, dict]:
    """What the module sends at this state (`_plant_once`: the find is `resolve_anchor`'s line)."""
    if stmt["op"] == "replace":
        return "replace_in_file", {"find": t1.resolve_anchor(state, stmt["anchor"]), "replace": line}
    return "append_to_file", {"text": line}


def check_line(state: Any, stmt: Mapping[str, Any], line: str, found_at_day0: bool | None = None) -> dict:
    """One line against one document state: found, unique, already present, byte-equal application, reason."""
    out = {"found": False, "unique": False, "already_present": False, "diff_equal": False, "reason": None,
           "anchor_lines": 0, "find_occurrences": 0}
    if not isinstance(state, str) or doc.is_unknown(state):
        out["reason"] = R_UNKNOWN_STATE
        return out
    lines = state.splitlines()
    if stmt["op"] == "replace":
        n = sum(1 for ln in lines if ln.startswith(stmt["anchor"]))
        out["anchor_lines"] = n
        out["found"] = n > 0
        if out["found"]:
            out["find_occurrences"] = state.count(t1.resolve_anchor(state, stmt["anchor"]))
        out["unique"] = n == 1 and out["find_occurrences"] == 1
    else:
        out["found"] = out["unique"] = True
        out["anchor_lines"] = out["find_occurrences"] = 1
    out["already_present"] = line in lines
    if out["found"]:
        action, sent = sent_of(state, stmt, line)
        try:
            out["diff_equal"] = t1.apply_edit(state, action, sent) == intended(state, stmt, line)
        except ValueError:
            out["diff_equal"] = False
    if len(line.splitlines()) != 1 or line != line.splitlines()[0]:
        out["reason"] = R_MULTILINE
    elif not out["found"]:
        out["reason"] = R_CHANGED_BEFORE if found_at_day0 else R_ABSENT
    elif not out["unique"]:
        out["reason"] = R_MULTI
    elif out["already_present"]:
        out["reason"] = R_PRESENT
    elif not out["diff_equal"]:
        out["reason"] = R_DIFF
    return out


def line_ok(c: Mapping[str, Any]) -> bool:
    return c["reason"] is None


def joint_check(state: Any, stmts: Sequence[Mapping[str, Any]], day: str, alone_required: bool = True) -> dict:
    """The item's lines applied in the module's order (index order; `_plant_once` sorts its plan stably by session
    time) against one state: each line still found once with the same target as alone, and the result equal to the
    lines put in place independently (replace targets by line index, appends in order). With alone_required False
    (a draw's reachable states, where a line planted in another session need not pass here), a state at which some
    line fails alone is not applicable (ok None): only mutual interference is read."""
    if not isinstance(state, str) or doc.is_unknown(state):
        return {"ok": False if alone_required else None, "reason": R_UNKNOWN_STATE if alone_required else None}
    lines_ = [t1.statement_line(st, day) for st in stmts]
    alone = [check_line(state, st, ln) for st, ln in zip(stmts, lines_)]
    if not all(line_ok(c) for c in alone):
        if not alone_required:
            return {"ok": None, "reason": None}
        return {"ok": False, "reason": next(c["reason"] for c in alone if not line_ok(c))}
    bare = state.splitlines()
    targets = [next(k for k, ln in enumerate(bare) if ln.startswith(st["anchor"])) if st["op"] == "replace" else None
               for st in stmts]
    tl = [t for t in targets if t is not None]
    if len(tl) != len(set(tl)):
        return {"ok": False, "reason": R_INTERFERE_SAME}
    running = state
    for st, ln in zip(stmts, lines_):
        c = check_line(running, st, ln)
        if not c["found"]:
            return {"ok": False, "reason": R_INTERFERE_TARGET}
        if st["op"] == "replace" and t1.resolve_anchor(running, st["anchor"]) != t1.resolve_anchor(state, st["anchor"]):
            return {"ok": False, "reason": R_INTERFERE_TARGET}
        if not c["unique"]:
            return {"ok": False, "reason": R_INTERFERE_MATCH}
        if c["already_present"]:
            return {"ok": False, "reason": R_INTERFERE_PRESENT}
        action, sent = sent_of(running, st, ln)
        running = t1.apply_edit(running, action, sent)
    parts = state.splitlines(keepends=True)
    for st, ln, t in zip(stmts, lines_, targets):
        if t is not None:
            parts[t] = ln + parts[t][len(bare[t]):]
    composite = "".join(parts)
    for st, ln in zip(stmts, lines_):
        if st["op"] == "append":
            composite = intended(composite, st, ln)
    if running != composite:
        return {"ok": False, "reason": R_INTERFERE_COMPOSITE}
    return {"ok": True, "reason": None}


# ── the module's reasons, mapped to codes (the module's text can quote an anchor: never written out) ─────

def statement_named(r: str) -> int | None:
    """The statement index a module reason names ("... for statement N", "... before statement N"); digits only."""
    m = re.search(r"(?:for|before) statement (\d+)", r)
    return int(m.group(1)) if m else None


def map_module_reason(r: str) -> str:
    if r.startswith("anchor absent at plant time"):
        return R_ABSENT
    if r.startswith("no session of role"):
        return R_ABSENT
    if " has no second left " in r:
        return R_NO_TIME
    if r.startswith("document state unknown or absent"):
        return R_UNKNOWN_STATE
    if r.startswith("a statement was overwritten before"):
        return R_CHANGED_AFTER
    if r.startswith("no statement landed"):
        return R_NO_LANDING
    if r.startswith("no author with an anchored session"):
        return R_NO_DRAW
    return R_UNMAPPED


# ── the module's draw rule, captured ───────────────────────────────────────────────────────────────

class _PoolCapture:
    """Stands in for the rng in `Inserter.draw_author`: records the sequence the module would draw from."""

    def __init__(self) -> None:
        self.pool: list[str] | None = None

    def choice(self, seq):
        self.pool = list(seq)
        return self.pool[0]


def drawable_authors(ins: t1.Inserter, path: str, day: str, anchors: Sequence[str]) -> tuple[list[str], dict]:
    """The authors the module's `draw_author` draws from on `day` for these anchors (the lone arm and one-statement
    roles pass until_day = the role's own day), and its pool log."""
    cap, log = _PoolCapture(), []
    ins.draw_author(cap, path, day, set(), list(anchors), log, day)
    return sorted(cap.pool or []), (log[0] if log else {})


def chosen_sessions(ins: t1.Inserter, ref: doc.DocRef, acct: str, day: str, stmts: Sequence[Mapping[str, Any]],
                    n_need: int) -> list[t1.Session]:
    """`_plant_once`'s session choice for a role (touching sessions first, then time order; the first n_need, used in
    time order); re-stated here only to enumerate the states the drawn sessions can reach."""
    elig = ins._sessions_with_anchors(ins.rows, ref, acct, day, list(stmts), day)
    touching = ins.touch.get(ref.key, set())
    order = [s for s in elig if s.task_id in touching] + [s for s in elig if s.task_id not in touching]
    return sorted(order[:n_need], key=lambda s: (s.first_ts, s.task_id))


class States:
    """Document states through the reader (`doc.content_at` on the null corpus from the seed), cached by time."""

    def __init__(self, ins: t1.Inserter) -> None:
        self.ins = ins
        self._cache: dict[tuple[str, str | None], Any] = {}
        self._writes: dict[str, list[str]] = {}

    def at(self, path: str, ts: str | None) -> Any:
        k = (path, ts)
        if k not in self._cache:
            self._cache[k] = doc.content_at(self.ins.rows, doc.DocRef("owncloud", path), ts, base=self.ins.base)
        return self._cache[k]

    def write_times(self, path: str) -> list[str]:
        if path not in self._writes:
            self._writes[path] = [w.ts for w in doc.content_writes(self.ins.rows, doc.DocRef("owncloud", path))]
        return self._writes[path]

    def reachable(self, path: str, s: t1.Session, ready: str) -> list[Any]:
        """Every distinct state a statement planted in session s from `ready` on can see (`_ts_in`: inside the span,
        strictly after `ready`, at the session's precision; the plant sits after every row at or before its ts)."""
        lo = t1._dt(ready) + timedelta(microseconds=1)
        hi = t1._dt(s.last_ts)
        if s.ts_style == "min":
            lo_m = lo.replace(second=0, microsecond=0)
            if lo_m < lo:
                lo_m += timedelta(minutes=1)
            hi_m = hi.replace(second=0, microsecond=0)
            if hi_m < lo_m:
                return []
            times = [t1._fmt(lo_m, "min")]
            for w in self.write_times(path):
                wt = t1._dt(w)
                if lo_m < wt <= hi_m:
                    m = wt.replace(second=0, microsecond=0)
                    if m < wt:
                        m += timedelta(minutes=1)
                    if m <= hi_m:
                        times.append(t1._fmt(m, "min"))
        else:
            if hi < lo:
                return []
            times = [t1._fmt(lo, "frac")] + [w for w in self.write_times(path) if lo < t1._dt(w) <= hi]
        out, seen = [], set()
        for t in times:
            st = self.at(path, t)
            key = st if isinstance(st, str) else repr(st)
            if key not in seen:
                seen.add(key)
                out.append(st)
        return out

    def day_states(self, path: str, day: str) -> list[Any]:
        """The document's distinct states during `day` at or after the module's whole-write floor up to that day
        (F4: a plant before the floor cannot compose): the day's opening state when the floor is earlier, and the
        state after each of the day's writes."""
        floor = self.ins.whole_write_floor(path, day)
        prev = (datetime.fromisoformat(day) - timedelta(days=1)).date().isoformat()
        times: list[str] = []
        if floor is None or floor[:10] < day:
            times.append(prev)
        times += [w for w in self.write_times(path) if w[:10] == day and (floor is None or w >= floor)]
        out, seen = [], set()
        for t in times:
            st = self.at(path, t)
            key = st if isinstance(st, str) else repr(st)
            if key not in seen:
                seen.add(key)
                out.append(st)
        return out


# ── one draw: the module's run and every reachable state ───────────────────────────────────────────

def _rng(*parts: Any) -> random.Random:
    return random.Random("|".join(str(p) for p in (RUN_SEED,) + parts))


def module_run(ins: t1.Inserter, payload: Mapping[str, Any], arm: str, stmts: Sequence[Mapping[str, Any]], day: str,
               acct: str, rng: random.Random, single: bool, found_day0: Sequence[bool]) -> dict:
    """`Inserter._plant_once` at (day, author) as the module runs it; each planted row checked against the state the
    module applied it to (rebuilt through the reader from the run's rows), its bytes against the intended document."""
    path = payload["document"]
    ref = doc.DocRef("owncloud", path)
    try:
        res = ins._plant_once(payload, arm, path, list(stmts), [day], [acct], rng, False)
    except Exception as exc:      # recorded by type only (a message can quote a line)
        r = f"other: the module raised {type(exc).__name__}"
        return {"ok": False, "composed": False, "reasons": [r], "honest_edits_broken": 0, "stopped": True,
                "lines": {i: {"found": False, "unique": False, "already_present": False, "diff_equal": False, "reason": r,
                              "anchor_lines": 0, "find_occurrences": 0} for i in range(len(stmts))}}
    reasons = [map_module_reason(r) for r in res.reasons]
    if single:      # `_check` needs three statement indices for `composed`: its "overwritten" reason is spurious here
        reasons = [r for r in reasons if r != R_CHANGED_AFTER]
    per_line: dict[int, dict] = {}
    if not res.rows:
        # `_plant_once` stopped part way (it attaches its rows only at the end): the run fails with the module's
        # reasons, each attributed to the statement it names; the lines it landed before stopping are not re-checked
        for raw, code in zip(res.reasons, map(map_module_reason, res.reasons)):
            i = statement_named(raw)
            if i is not None and i < len(stmts):
                per_line[i] = {"found": code not in NOT_FOUND, "unique": False, "already_present": False,
                               "diff_equal": False, "reason": code, "anchor_lines": 0, "find_occurrences": 0}
        return {"ok": False, "composed": False, "reasons": sorted(set(reasons)) or [R_NO_LANDING], "lines": per_line,
                "honest_edits_broken": len(res.honest_edits_broken), "stopped": True}
    by_eid = {r.get("event_id"): i for i, r in enumerate(res.rows) if r.get("t1_planted")}
    for s in res.statements:
        if s.duplicate:
            continue
        pos = by_eid[t1._event_id(payload["id"], arm, s.index, False)]
        before = doc.content_at(res.rows[:pos], ref, None, base=ins.base)
        c = check_line(before, stmts[s.index], s.line_text, found_day0[s.index])
        c["diff_equal"] = bool(c["found"]) and s.args.get("content") == intended(before, stmts[s.index], s.line_text)
        if c["reason"] is None and not c["diff_equal"]:
            c["reason"] = R_DIFF
        per_line[s.index] = c
    if single and res.statements:
        s = res.statements[0]
        at_ts = doc.content_at(res.rows, ref, s.ts, base=ins.base)
        present = isinstance(at_ts, str) and s.line_text in at_ts.splitlines() and all(res.present_at_day_end)
        if not present:
            reasons.append(R_CHANGED_AFTER)
        composed = present
    else:
        composed = res.composed
    landed = len(per_line) == len(stmts)
    ok = composed and landed and not reasons and all(line_ok(per_line[i]) for i in range(len(stmts)))
    return {"ok": ok, "composed": composed, "reasons": sorted(set(reasons)) or ([] if landed else [R_NO_LANDING]),
            "lines": per_line, "honest_edits_broken": len(res.honest_edits_broken), "stopped": False}


def run_draw(ins: t1.Inserter, states: States, key: str, payload: Mapping[str, Any], stmts: Sequence[Mapping[str, Any]],
             day: str, acct: str, single: bool, found_day0: Sequence[bool]) -> dict:
    """One position draw (day, author): RUNS_PER_DRAW module runs that place (a timestamp sample in which a session has
    no second left for a later line is re-drawn, as `plant()` re-draws it, up to MAX_SAMPLES samples; the draw fails
    for time only when no sample places), and the line checks and the joint check on every state the drawn sessions
    can reach (lone: statements 1 and 2 in the first session, 3 in the second)."""
    path = payload["document"]
    ref = doc.DocRef("owncloud", path)
    arm = "k3" if single else "lone"
    reasons: Counter = Counter()
    line_fail: dict[int, Counter] = {i: Counter() for i in range(len(stmts))}
    runs = []
    k = no_time = 0
    while len(runs) < RUNS_PER_DRAW and k < MAX_SAMPLES:
        r = module_run(ins, payload, arm, stmts, day, acct, _rng(key, day, acct, k), single, found_day0)
        k += 1
        if r["stopped"] and r["reasons"] == [R_NO_TIME]:
            no_time += 1
            continue
        runs.append(r)
        reasons.update(r["reasons"])
        for i, c in r["lines"].items():
            if c["reason"]:
                line_fail[i][c["reason"]] += 1
    if not runs:
        reasons[R_NO_TIME] += no_time
    anchors = [st["anchor"] for st in stmts if st["op"] == "replace"]
    n_need = 1 if single else 2
    ss = chosen_sessions(ins, ref, acct, day, stmts, n_need)
    n_states = n_joint = 0
    joint_fail: Counter = Counter()
    if ss:
        role_sessions = [ss[0]] if single else [ss[0], ss[0], ss[-1]]
        seen_sessions: dict[str, list[Any]] = {}
        for s in {x.task_id: x for x in role_sessions}.values():
            ready = ins._anchor_ready(ins.rows, ref, s, anchors, day)
            seen_sessions[s.task_id] = states.reachable(path, s, ready) if ready is not None else []
        for i, s in enumerate(role_sessions):
            line = t1.statement_line(stmts[i], day)
            for st in seen_sessions[s.task_id]:
                n_states += 1
                c = check_line(st, stmts[i], line, found_day0[i])
                if c["reason"]:
                    line_fail[i][c["reason"]] += 1
        if not single:
            for sts in seen_sessions.values():
                for st in sts:
                    j = joint_check(st, stmts, day, alone_required=False)
                    if j["ok"] is None:
                        continue
                    n_joint += 1
                    if not j["ok"]:
                        joint_fail[j["reason"]] += 1
    else:
        reasons[R_NO_DRAW] += 1
    all_reasons = Counter(reasons)
    for c in line_fail.values():
        all_reasons.update(c)
    all_reasons.update(joint_fail)
    ok = bool(runs) and all(r["ok"] for r in runs) and not any(line_fail[i] for i in line_fail) and not joint_fail and bool(ss)
    return {"day": day, "author": acct, "valid": ok, "module_samples": k, "module_samples_no_time": no_time,
            "module_runs_placed": len(runs), "module_runs_ok": sum(1 for r in runs if r["ok"]),
            "module_composed": sum(1 for r in runs if r["composed"]), "module_stopped": sum(1 for r in runs if r["stopped"]),
            "states_checked": n_states,
            "joint_states_applicable": n_joint, "joint_failures": dict(joint_fail), "reasons": dict(all_reasons),
            "line_fail": {i: dict(c) for i, c in line_fail.items()},
            "honest_edits_broken_max": max((r["honest_edits_broken"] for r in runs), default=0)}


# ── per item and per lone line ─────────────────────────────────────────────────────────────────────

def pair_ok(valid: Sequence[tuple[str, str]], distinct_days: bool) -> bool:
    """Two valid draws usable together: by different authors (and on different days when the layout places the
    second placement on another day)."""
    for i, (d1, a1) in enumerate(valid):
        for d2, a2 in valid[i + 1:]:
            if a1 != a2 and (d1 != d2 or not distinct_days):
                return True
    return False


def enumerate_draws(ins: t1.Inserter, states: States, key: str, payload: Mapping[str, Any],
                    stmts: Sequence[Mapping[str, Any]], single: bool, found_day0: Sequence[bool]) -> dict:
    path = payload["document"]
    anchors = [st["anchor"] for st in stmts if st["op"] == "replace"]
    draws, pools = [], {}
    for day in ins.days[:2]:                      # the lone layout's day draw (`layout`: rng.choice(self.days[:2]))
        authors, log = drawable_authors(ins, path, day, anchors)
        pools[day] = {"pool": log.get("pool"), "anchored": log.get("anchored"), "touching": log.get("touching"),
                      "drawable": len(authors)}
        for a in authors:
            draws.append(run_draw(ins, states, key, payload, stmts, day, a, single, found_day0))
    valid = [(d["day"], d["author"]) for d in draws if d["valid"]]
    reasons: Counter = Counter()
    for d in draws:
        if not d["valid"]:
            reasons.update(d["reasons"])
    per_line = []
    for i in range(len(stmts)):
        fails = [d for d in draws if d["line_fail"].get(i)]
        rc: Counter = Counter()
        for d in fails:
            rc.update(d["line_fail"][i])
        # at every state the draw reaches and in every module run: found; then found once; then the exact application
        ks = [set(d["line_fail"].get(i, {})) for d in draws]
        found = [not (k & NOT_FOUND) for k in ks]
        unique = [f and R_MULTI not in k for f, k in zip(found, ks)]
        equal = [u and R_DIFF not in k for u, k in zip(unique, ks)]
        per_line.append({"draws": len(draws), "draws_found": sum(found), "draws_unique": sum(unique),
                         "draws_diff_equal": sum(equal), "draws_line_ok": len(draws) - len(fails), "reasons": dict(rc)})
    return {"pools": pools, "n_drawable": len(draws), "n_valid": len(valid),
            "valid_by_day": {day: sum(1 for d, _a in valid if d == day) for day in ins.days[:2]},
            "valid_draws": [list(v) for v in valid],
            "valid_authors": len({a for _d, a in valid}),
            "pair_ok_distinct_days": pair_ok(valid, True), "pair_ok_distinct_authors": pair_ok(valid, False),
            "literal_ok": len(valid) >= 2,
            "states_checked": sum(d["states_checked"] for d in draws),
            "joint_states_applicable": sum(d["joint_states_applicable"] for d in draws),
            "draws_without_an_applicable_joint_state": sum(1 for d in draws if not single and d["joint_states_applicable"] == 0),
            "module_runs": sum(d["module_samples"] for d in draws),
            "module_samples_no_time": sum(d["module_samples_no_time"] for d in draws),
            "module_runs_placed": sum(d["module_runs_placed"] for d in draws),
            "module_runs_ok": sum(d["module_runs_ok"] for d in draws),
            "module_runs_stopped": sum(d["module_stopped"] for d in draws),
            "invalid_draws": len(draws) - len(valid), "invalid_reasons": dict(reasons),
            "joint_failures": dict(sum((Counter(d["joint_failures"]) for d in draws), Counter())),
            "honest_edits_broken_max": max((d["honest_edits_broken_max"] for d in draws), default=0),
            "per_line": per_line}


def static_checks(states: States, days: Sequence[str], item: Mapping[str, Any], day0: Mapping[str, str]) -> dict:
    """(i) the day-0 snapshot and (ii) every day of the bank (each day's states after the module's floor), per line
    and for the item's lines together."""
    path, stmts = item["document"], item["statements"]
    s0 = day0[path]
    lines0, found0 = [], []
    for st in stmts:
        c = check_line(s0, st, t1.statement_line(st, days[0]))
        found0.append(c["found"])
        lines0.append({k: c[k] for k in ("found", "unique", "already_present", "diff_equal", "reason")})
    j0 = joint_check(s0, stmts, days[0])
    bank: dict[str, Any] = {}
    for d in days:
        sts = states.day_states(path, d)
        per = []
        for i, st in enumerate(stmts):
            cs = [check_line(x, st, t1.statement_line(st, d), found0[i]) for x in sts]
            per.append({"states": len(cs), "found": sum(c["found"] for c in cs), "unique": sum(c["unique"] for c in cs),
                        "diff_equal": sum(c["diff_equal"] for c in cs), "ok": sum(line_ok(c) for c in cs),
                        "reasons": dict(Counter(c["reason"] for c in cs if c["reason"]))})
        js = [joint_check(x, stmts, d) for x in sts]
        bank[d] = {"states": len(sts), "lines": per, "joint_ok": sum(j["ok"] for j in js),
                   "joint_reasons": dict(Counter(j["reason"] for j in js if not j["ok"]))}
    return {"day0": {"lines": lines0, "joint_ok": j0["ok"], "joint_reason": j0["reason"]}, "bank_days": bank,
            "found_day0": found0}


# ── workers (fork: the inserter is built once and shared) ──────────────────────────────────────────

_G: dict[str, Any] = {}


def _init_globals(corpus: Path, template: Path) -> None:
    ins, _rows = t1.build_inserter(corpus, template)
    _G["ins"], _G["states"] = ins, States(ins)


def _task(task: tuple) -> tuple:
    kind, key, payload, stmts, found_day0 = task
    ins, states = _G["ins"], _G["states"]
    single = kind == "line"
    return kind, key, enumerate_draws(ins, states, key, payload, stmts, single, found_day0)


# ── inputs ─────────────────────────────────────────────────────────────────────────────────────────

def input_paths(root: Path = PROJECT) -> dict[str, Path]:
    s3 = root / "work" / "stage3"
    return {"candidates_sonnet55": s3 / "b3" / "payloads-b3-candidates-sonnet55.json",
            "candidates_glm53": s3 / "b3" / "payloads-b3-candidates-glm53.json",
            "controls_sonnet55": s3 / "b3" / "controls-b3-sonnet55.json",
            "controls_glm53": s3 / "b3" / "controls-b3-glm53.json",
            "payloads_v2": s3 / "t1v2" / "payloads-v2.json",
            "items_v0": s3 / "b3" / "comprehension" / "items-v0.json",
            "stratum_v0": s3 / "b3" / "comprehension" / "stratum-v0.json",
            "key_b3": s3 / "b3" / "rater" / "key-b3.json",
            "triples_b3": s3 / "b3" / "rater" / "stripped-triples-b3.json",
            "t1_triples": s3 / "t1k-rater" / "stripped-triples.json",
            "t1v3_manifest": s3 / "t1v3" / "plants-v3.json"}


def load_items(paths: Mapping[str, Path]) -> tuple[list[dict], dict]:
    """Every item by brief 25's opaque id with its payload (by writer file and id), document, regime, writer,
    brief 25's anchors_resolve and its populations; checked against the stripped triples and the stratum file."""
    import stage3_legibility as lg
    data = {k: json.loads(Path(p).read_text(encoding="utf-8")) for k, p in paths.items()}
    files = {"candidates-sonnet55": data["candidates_sonnet55"], "candidates-glm53": data["candidates_glm53"],
             "controls-sonnet55": data["controls_sonnet55"], "controls-glm53": data["controls_glm53"]}
    pay = {(src, p["id"]): p for src, d in files.items() for p in d["payloads"]}
    v2 = {p["id"]: p for p in data["payloads_v2"]["payloads"]}
    key = data["key_b3"]["triples"]
    tri = {t["triple_id"]: t for t in data["triples_b3"]} if isinstance(data["triples_b3"], list) else \
        {t["triple_id"]: t for t in data["triples_b3"]["triples"]}
    t1t = {t["triple_id"]: t for t in data["t1_triples"]} if isinstance(data["t1_triples"], list) else \
        {t["triple_id"]: t for t in data["t1_triples"]["triples"]}
    strat = data["stratum_v0"]
    srec = strat["items"]
    members = set(strat["stratum"]["ids"])
    items = []
    for row in data["items_v0"]["items"]:
        tid, reg = row["item_id"], row["regime"]
        if reg == "sham":
            ref = row["payload_ref"]
            p, src, tt = v2[ref["id"]], "t1v2", t1t[tid]
        else:
            kv = key[tid]
            src = kv["source"]
            p, tt = pay[(src, kv["id"])], tri[tid]
        if p.get("arm") != RATED_ARM[reg] or str(p["document"]) != row["document"] or tt["document"] != row["document"]:
            raise ValueError(f"item {tid}: payload arm or document differs")
        if lg.payload_statements(p) != lg.triple_statements(tt):
            raise ValueError(f"item {tid}: the payload's statements differ from its stripped triple")
        if len(p["statements"]) != 3:
            raise ValueError(f"item {tid}: not three lines")
        pops = []
        if reg == "candidate":
            sr = srec[tid]
            pops.append("78")
            if sr["membership"] == "quiet":
                if tid not in members:
                    raise ValueError(f"item {tid}: membership and the stratum ids disagree")
                pops.append("28")
                if row["anchors_resolve"]:
                    pops.append("19")
                rd = sr["readers"]
                if rd["kimi"]["D_part"] == [0.0, 0.0] and rd["sol"]["D_part"] == [0.0, 0.0]:
                    pops.append("21")
        items.append({"item_id": tid, "regime": reg, "writer": row["writer"], "document": row["document"],
                      "source": src, "payload_id": p["id"], "statements": p["statements"],
                      "anchors_resolve": row["anchors_resolve"], "n_unresolved_anchors": row["n_unresolved_anchors"],
                      "populations": pops})
    counts = Counter(it["regime"] for it in items)
    if dict(counts) != EXPECTED:
        raise ValueError(f"item counts {dict(counts)} differ from {EXPECTED}")
    pc = Counter(p for it in items for p in it["populations"])
    if {k: pc.get(k, 0) for k in EXPECTED_POPS} != EXPECTED_POPS:
        raise ValueError(f"population counts {dict(pc)} differ from {EXPECTED_POPS}")
    if {it["item_id"] for it in items if "28" in it["populations"]} != members:
        raise ValueError("the 28 differ from the stratum's ids")
    for pop, want in EXPECTED_POP_WRITERS.items():
        got = dict(Counter(it["writer"] for it in items if pop in it["populations"]))
        if got != want:
            raise ValueError(f"population {pop} by writer {got} differs from {want}")
    meta = {"day0_sha256_items_v0": data["items_v0"].get("day0_sha256"),
            "stratum_ids_sha256": strat["stratum"]["ids_sha256"],
            "t1v3_corpus_sha256": data["t1v3_manifest"].get("corpus_sha256"),
            "t1v3_inserter_class_sha256": data["t1v3_manifest"].get("inserter_class_sha256")}
    return items, meta


def guard_texts(items: Sequence[Mapping[str, Any]], day0: Mapping[str, str], paths: Mapping[str, Path]) -> list[str]:
    """Strings that must never appear in an output: every line, anchor and region of every item (any day), the
    declared effects, and every line of the day-0 documents of at least 25 characters."""
    out: set[str] = set()
    for it in items:
        for st in it["statements"]:
            for k in ("anchor", "replace", "text", "region", "justification"):
                v = st.get(k)
                if isinstance(v, str) and v != "end of document":
                    out.update(f for f in v.split("{date}") if len(f.strip()) >= 12)
    for k in ("candidates_sonnet55", "candidates_glm53", "controls_sonnet55", "controls_glm53", "payloads_v2"):
        for p in json.loads(Path(paths[k]).read_text(encoding="utf-8"))["payloads"]:
            v = p.get("composed_effect")
            if isinstance(v, str) and len(v.strip()) >= 8:
                out.add(v)
    for txt in day0.values():
        out.update(ln for ln in txt.splitlines() if len(ln.strip()) >= 25)
    return sorted(out)


def assert_clean(text: str, guard: Sequence[str]) -> None:
    bad = sum(1 for g in guard if g in text)
    if bad:
        raise SystemExit(f"refusing to write: {bad} guarded strings would appear in the output")


# ── the module record (D0) and its findings ────────────────────────────────────────────────────────

def module_line(needle: str) -> int:
    src = Path(t1.__file__).read_text(encoding="utf-8").splitlines()
    hits = [i + 1 for i, ln in enumerate(src) if needle in ln]
    if len(hits) != 1:
        raise ValueError(f"module line not unique: {needle!r} ({len(hits)})")
    return hits[0]


def module_record() -> dict:
    p = Path(t1.__file__).resolve()
    fork = PROJECT / "work" / "mole-fork" / "scripts" / "stage3" / "stage3_t1.py"
    cls = sha256_bytes(inspect.getsource(t1.Inserter).encode("utf-8"))
    return {
        "path": "work/checks/stage3_t1.py", "fork_path": "work/mole-fork/scripts/stage3/stage3_t1.py",
        "sha256": file_sha256(p), "fork_sha256": file_sha256(fork), "fork_copy_identical": file_sha256(p) == file_sha256(fork),
        "inserter_class_sha256": cls, "inserter_class_equals_t1v3_manifest": cls == V3_INSERTER_CLASS_SHA256,
        "functions_called": ["Inserter.__init__ (via build_inserter)", "Inserter.draw_author (pool captured)",
                             "Inserter._sessions_with_anchors", "Inserter._anchor_ready", "Inserter.whole_write_floor",
                             "Inserter._plant_once", "apply_edit", "resolve_anchor", "statement_line", "_event_id"],
        "candidates": [
            {"path": "work/checks/stage3_t1.py", "role": "the inserter: placement (draw_author, layout, plant) and application (apply_edit, resolve_anchor, _plant_once)",
             "part_s_uses": True,
             "why": "brief 15 S1's layout line names 'the v3-amended inserter unchanged (hash)' and Part S's orientation lists 'stage3_t1.py as amended for v3 (hash)'; B1's plantings regenerate through it (stage3_t1_score.regenerate calls t1.plant_all); its Inserter class hash equals the T1 v3 manifest's and the file hash equals the re-plant manifest's"},
            {"path": "work/checks/stage3_author_doc.py", "role": "the dossier view's applier (renders an author's own planted edits for P_author_doc; calls t1.apply_edit)",
             "part_s_uses": False, "why": "a view renderer applied to a planting the inserter made; it places nothing"},
            {"path": "work/checks/stage3_legibility.py (anchor_resolves) and stage3_b3_comprehension.py", "role": "briefs 23 and 25's day-0 rendering of items for the comprehension readers",
             "part_s_uses": False, "why": "renders reader packets against the day-0 snapshot; not an application module"}],
        "lines": {"lone_day_draw": module_line("d = rng.choice(self.days[:2])"),
                  "draw_author": module_line("def draw_author("),
                  "anchored_pool": module_line("anchored = [a for a in pool if self._has_anchored_session("),
                  "touching_pool": module_line("chosen_pool = touching or anchored"),
                  "sessions_with_anchors": module_line("def _sessions_with_anchors("),
                  "anchor_ready": module_line("def _anchor_ready("),
                  "plant_redraws": module_line("for attempt in range(MAX_REDRAWS + 1):"),
                  "plant_accepts_unclean": module_line("if res.composed and (not res.honest_edits_broken or attempt >= PREFER_CLEAN_DRAWS):"),
                  "plant_returns_uncomposed": module_line('out.reasons.append(f"not composed after {MAX_REDRAWS} re-draws")'),
                  "resolve_anchor": module_line("def resolve_anchor("),
                  "resolve_first_match": module_line("        if ln.startswith(anchor):"),
                  "replace_first_occurrence": module_line("return before.replace(find, repl if isinstance(repl, str) else str(repl), 1)"),
                  "primary_find": module_line("elif find is None or find not in state:"),
                  "roles": module_line('return {"lone": [[0, 1, 2]], "k2": [[0, 1], [2]], "k3": [[0], [1], [2]]}[arm]'),
                  "composed_needs_three": module_line("res.composed_at_ts = len({s.index for s in real}) == 3"),
                  "load_payloads_three": module_line('assert ps and all(len(p["statements"]) == 3 for p in ps), "payloads of 3 statements"'),
                  "session_choice": module_line("chosen = sorted(order[:n_need], key=lambda s: (s.first_ts, s.task_id))")},
    }


# ── aggregation ────────────────────────────────────────────────────────────────────────────────────

def decide(item: Mapping[str, Any], draws: Mapping[str, Any], lone: Sequence[Mapping[str, Any]] | None) -> dict:
    """Brief 26's rule: too few valid draws for the item (two placements on different days by different authors) or,
    for a candidate, for any lone line (two by different authors); the literal counts beside."""
    reasons = []
    if not draws["pair_ok_distinct_days"]:
        reasons.append({"what": "item", "valid_draws": draws["n_valid"], "valid_by_day": draws["valid_by_day"],
                        "why": top_reasons(draws)})
    lit = draws["literal_ok"]
    if lone is not None:
        for i, ld in enumerate(lone):
            lit = lit and ld["literal_ok"]
            if not ld["pair_ok_distinct_authors"]:
                reasons.append({"what": f"lone line {i + 1}", "valid_draws": ld["n_valid"], "valid_by_day": ld["valid_by_day"],
                                "why": top_reasons(ld)})
    return {"drop": bool(reasons), "drop_reasons": reasons, "drop_literal": not lit}


def top_reasons(d: Mapping[str, Any]) -> list[str]:
    if d["n_drawable"] == 0:
        return [R_NO_DRAW]
    rc = Counter(d["invalid_reasons"])
    return [r for r, _n in rc.most_common(3)]


def _agg(rows: Sequence[Mapping[str, Any]]) -> dict:
    n_lines = sum(len(r["lines"]) for r in rows)
    d0 = [ln["day0"] for r in rows for ln in r["lines"]]
    rc0 = Counter(brief_class(x["reason"]) for x in d0 if x["reason"])
    rcd: Counter = Counter()
    for r in rows:
        for ln in r["lines"]:
            for k, v in ln["part_s"]["reasons"].items():
                rcd[brief_class(k)] += v
    ps_lines = [ln["part_s"] for r in rows for ln in r["lines"]]
    ps_line = {"lines_without_a_drawable_draw": sum(1 for x in ps_lines if not x["draws"]),
               "lines_found_at_every_draw": sum(1 for x in ps_lines if x["draws"] and x["draws_found"] == x["draws"]),
               "lines_found_once_at_every_draw": sum(1 for x in ps_lines if x["draws"] and x["draws_unique"] == x["draws"]),
               "lines_diff_equal_at_every_draw": sum(1 for x in ps_lines if x["draws"] and x["draws_diff_equal"] == x["draws"]),
               "lines_ok_at_every_draw": sum(1 for x in ps_lines if x["draws"] and x["draws_line_ok"] == x["draws"])}
    return {"items": len(rows), "lines": n_lines,
            "day0": {"found": sum(x["found"] for x in d0), "unique": sum(x["unique"] for x in d0),
                     "diff_equal": sum(x["diff_equal"] for x in d0), "ok": sum(x["reason"] is None for x in d0),
                     "items_joint_ok": sum(r["day0_joint_ok"] for r in rows), "failures_by_reason": dict(sorted(rc0.items()))},
            "part_s": {"items_with_a_drawable_author": sum(r["draws"]["n_drawable"] > 0 for r in rows),
                       "drawable_draws": sum(r["draws"]["n_drawable"] for r in rows),
                       "valid_draws": sum(r["draws"]["n_valid"] for r in rows),
                       "items_two_valid_placements": sum(r["draws"]["pair_ok_distinct_days"] for r in rows),
                       "items_literal_two_valid": sum(r["draws"]["literal_ok"] for r in rows),
                       **ps_line,
                       "line_failures_by_reason_state_checks": dict(sorted(rcd.items()))},
            "dropped": sum(r["drop"] for r in rows), "dropped_literal": sum(r["drop_literal"] for r in rows)}


def aggregates(rows: Sequence[Mapping[str, Any]]) -> dict:
    out: dict[str, Any] = {"by_regime": {}, "by_writer": {}, "by_population": {}, "by_anchors_resolve": {}}
    for g in ("candidate", "control", "sham"):
        out["by_regime"][REGIME_NAME[g]] = _agg([r for r in rows if r["regime"] == g])
    for w in sorted({r["writer"] for r in rows}):
        out["by_writer"][w] = _agg([r for r in rows if r["writer"] == w])
    for p in EXPECTED_POPS:
        out["by_population"][p] = _agg([r for r in rows if p in r["populations"]])
    for v in (True, False):
        out["by_anchors_resolve"][str(v).lower()] = {g: _agg([r for r in rows if r["regime"] == g and r["anchors_resolve"] is v])
                                                     for g in ("candidate", "control", "sham")}
    return out


def lone_line_summary(rows: Sequence[Mapping[str, Any]], regime: str = "candidate") -> dict:
    ls = [ld for r in rows if r["regime"] == regime for ld in r["lone_lines"]]
    rc: Counter = Counter()
    for ld in ls:
        rc.update({brief_class(k): v for k, v in ld["invalid_reasons"].items()})
    return {"lines": len(ls), "with_a_drawable_author": sum(ld["n_drawable"] > 0 for ld in ls),
            "drawable_draws": sum(ld["n_drawable"] for ld in ls), "valid_draws": sum(ld["n_valid"] for ld in ls),
            "two_valid_distinct_authors": sum(ld["pair_ok_distinct_authors"] for ld in ls),
            "literal_two_valid": sum(ld["literal_ok"] for ld in ls),
            "two_valid_distinct_days": sum(ld["pair_ok_distinct_days"] for ld in ls),
            "at_most_three_valid_authors": sum(ld["valid_authors"] <= 3 for ld in ls),
            "invalid_draw_reasons": dict(sorted(rc.items()))}


def reverse_case(rows: Sequence[Mapping[str, Any]], drawable_days: Sequence[str]) -> dict:
    """Lines found at day 0 but not in the Part S state: absent from every state of both drawable days (cannot be
    placed: the count), and beside, absent on one drawable day, or in some state of a drawable day. The forward case
    (absent at day 0, found in a Part S state) beside."""
    out = {"definition": "a line whose target is found at day 0 and is absent from every document state of both days "
                         "the lone layout draws (the states at or after the module's whole-write floor)",
           "count": 0, "ids": [], "by_regime": Counter(), "absent_on_one_drawable_day": 0,
           "absent_in_some_state_of_a_drawable_day": 0, "forward_case_count": 0, "forward_case_by_regime": Counter(),
           "forward_case_found_unique_on_both_days": 0,
           "uniqueness": {"definition": "beside the count: a line whose target is found once at day 0 and found more than once in "
                                        "Part S states (a routine edit adds a second line with the same start)",
                          "not_unique_in_some_state": [], "not_unique_in_every_state_of_a_drawable_day": []}}
    for r in rows:
        for i, ln in enumerate(r["lines"]):
            bd = ln["bank_days"]
            found_d = {d: bd[d]["found"] for d in drawable_days}
            states_d = {d: bd[d]["states"] for d in drawable_days}
            if ln["day0"]["unique"]:
                if any(bd[d]["unique"] < bd[d]["found"] for d in drawable_days):
                    out["uniqueness"]["not_unique_in_some_state"].append(f"{r['item_id']}:{i + 1}")
                if any(states_d[d] and bd[d]["unique"] == 0 and bd[d]["found"] == states_d[d] for d in drawable_days):
                    out["uniqueness"]["not_unique_in_every_state_of_a_drawable_day"].append(f"{r['item_id']}:{i + 1}")
            if ln["day0"]["found"]:
                if all(found_d[d] == 0 for d in drawable_days):
                    out["count"] += 1
                    out["ids"].append(f"{r['item_id']}:{i + 1}")
                    out["by_regime"][REGIME_NAME[r["regime"]]] += 1
                if any(found_d[d] == 0 for d in drawable_days):
                    out["absent_on_one_drawable_day"] += 1
                if any(found_d[d] < states_d[d] for d in drawable_days):
                    out["absent_in_some_state_of_a_drawable_day"] += 1
            else:
                if any(found_d[d] > 0 for d in drawable_days):
                    out["forward_case_count"] += 1
                    out["forward_case_by_regime"][REGIME_NAME[r["regime"]]] += 1
                if all(bd[d]["unique"] == states_d[d] and states_d[d] > 0 for d in drawable_days):
                    out["forward_case_found_unique_on_both_days"] += 1
    out["by_regime"] = dict(out["by_regime"])
    out["forward_case_by_regime"] = dict(out["forward_case_by_regime"])
    return out


def findings(rows: Sequence[Mapping[str, Any]], mod: Mapping[str, Any]) -> list[dict]:
    """Module behaviours that bear on S1's draw restriction: counts and line numbers; nothing is changed here."""
    L = mod["lines"]
    nonunique = sum(1 for r in rows for ln in r["lines"] if any(k == R_MULTI for k in ln["part_s"]["reasons"]))
    diff = sum(1 for r in rows for ln in r["lines"] if any(k == R_DIFF for k in ln["part_s"]["reasons"]))
    present = sum(1 for r in rows for ln in r["lines"] if any(k == R_PRESENT for k in ln["part_s"]["reasons"]))
    invalid_drawable = sum(1 for r in rows if r["draws"]["invalid_draws"] > 0)
    lone_lines = sum(len(r["lone_lines"]) for r in rows if r["regime"] == "candidate")
    return [
        {"id": "M1", "lines": [L["resolve_anchor"], L["resolve_first_match"], L["primary_find"]],
         "what": "resolve_anchor takes the first line that starts with the anchor and nothing checks that it is the only one",
         "count": nonunique, "count_of": "lines with a non-unique target at a state some drawable placement reaches"},
        {"id": "M2", "lines": [L["replace_first_occurrence"]],
         "what": "apply_edit's replace substitutes the first substring occurrence of the resolved line, which is another position when that text occurs earlier",
         "count": diff, "count_of": "lines whose application differs from the intended document at a reachable state"},
        {"id": "M3", "lines": [L["primary_find"]],
         "what": "the first delivery of a line does not check that the line is already present (only the redundant delivery does, F2)",
         "count": present, "count_of": "lines already present at a reachable state"},
        {"id": "M4", "lines": [L["roles"], L["composed_needs_three"], L["load_payloads_three"]],
         "what": "the module has no lone-line (singleton) arm: arms are lone, k2 and k3 over three statements, load_payloads asserts three, and composed needs three statement indices; the dry run applied each lone line through the one-statement role path (k3's role logic with one day) and read presence itself",
         "count": lone_lines, "count_of": "lone lines of A6.8's arm that S1 must plant through code the module does not have as an arm"},
        {"id": "M5", "lines": [L["anchored_pool"], L["touching_pool"], L["plant_redraws"], L["plant_accepts_unclean"], L["plant_returns_uncomposed"]],
         "what": "the draw rule restricts authors to sessions where every target resolves and re-draws when not composed, but checks neither uniqueness, exact application nor interference, and after MAX_REDRAWS returns a delivered or last layout rather than refusing",
         "count": invalid_drawable, "count_of": "items with at least one drawable placement that is not valid"},
    ]


# ── report ─────────────────────────────────────────────────────────────────────────────────────────

def _f(x: Any) -> str:
    return "" if x is None else str(x)


def render_md(res: Mapping[str, Any]) -> str:
    L: list[str] = []
    m, ag, dl = res["module"], res["aggregates"], res["drop_list"]
    L.append("# Brief 26: the edit-application dry run on every B3 item (blue; ids, counts and hashes only)\n")
    L.append(f"**Drop list: {len(dl['ids'])} item(s)** under brief 26's rule at T2+S2 (A6.17.10 (c)); "
             f"literal two-valid-draws count beside: {len(dl['ids_literal'])}. "
             f"**Reverse-case count: {res['reverse_case']['count']}** line(s) found at day 0 but absent from every Part S state "
             f"of both drawable days. No item line, anchor, rubric, declared effect or document text appears in this file.\n")
    L.append("## Module, document states and position case\n")
    L.append(f"- Application module: `{m['path']}` sha256 `{m['sha256']}` (fork copy `{m['fork_path']}` identical: "
             f"{m['fork_copy_identical']}); `Inserter` class sha256 `{m['inserter_class_sha256']}`, equal to the T1 v3 manifest's: "
             f"{m['inserter_class_equals_t1v3_manifest']}. Not changed.")
    for c in m["candidates"]:
        L.append(f"  - candidate `{c['path']}`: {c['role']}; Part S uses it: {c['part_s_uses']} ({c['why']}).")
    ds = res["document_states"]
    L.append(f"- Day 0: {ds['day0']['source']}; sha256 of the six texts (brief 23's rule) `{ds['day0']['day0_sha256']}`, "
             f"equal to brief 25's items-v0: {ds['day0']['equals_items_v0']}.")
    L.append(f"- Part S states: {ds['part_s']['source']}; corpus `{ds['part_s']['corpus']}` sha256 `{ds['part_s']['corpus_sha256']}` "
             f"(the T1 v3 and B1 null: {ds['part_s']['corpus_equals_t1v3']}); bank days {', '.join(ds['part_s']['bank_days'])}; "
             f"the lone layout draws {', '.join(ds['part_s']['drawable_days'])} (module line {m['lines']['lone_day_draw']}). "
             f"**{ds['part_s']['day_note']}**")
    L.append(f"- Position case: **{res['position_case']}**")
    L.append(f"- Module runs per draw: {res['runs_per_draw']} that place (timestamp samples, seed label `{res['run_seed']}`; a sample in "
             f"which the drawn session has no second left for a later line is re-drawn, as `plant()` re-draws it, up to {res['max_samples']} "
             f"samples), plus every state the drawn sessions can reach. Draws enumerated: {res['totals']['item_draws']} item draws, "
             f"{res['totals']['lone_line_draws']} lone-line draws; module runs {res['totals']['module_runs']}, of which "
             f"{res['totals']['module_samples_no_time']} had no second left and were re-drawn; "
             f"line-state checks {res['totals']['states_checked']}; joint checks at reachable states where every line passes alone "
             f"{res['totals']['joint_states_applicable']} (item draws with no such state, read through the module runs alone: "
             f"{res['totals']['item_draws_without_an_applicable_joint_state']}).\n")
    L.append("## Rule applied\n")
    for k, v in res["rule"].items():
        L.append(f"- **{k}:** {v}")
    L.append("")
    L.append("## Aggregates\n")
    hdr = ("| group | items | lines | day 0 found | unique | diff equal | lines ok | items joint ok | items with a drawable author | "
           "valid draws / drawable | items with two valid placements | dropped | dropped (literal) |")
    L.append(hdr)
    L.append("|" + "---|" * 13)

    def row(name: str, a: Mapping[str, Any]) -> str:
        d0, ps = a["day0"], a["part_s"]
        return (f"| {name} | {a['items']} | {a['lines']} | {d0['found']} | {d0['unique']} | {d0['diff_equal']} | {d0['ok']} | "
                f"{d0['items_joint_ok']} | {ps['items_with_a_drawable_author']} | {ps['valid_draws']} / {ps['drawable_draws']} | "
                f"{ps['items_two_valid_placements']} | {a['dropped']} | {a['dropped_literal']} |")
    for k, a in ag["by_regime"].items():
        L.append(row(f"regime: {k}", a))
    for k, a in ag["by_writer"].items():
        L.append(row(f"writer: {k}", a))
    for k, a in ag["by_population"].items():
        L.append(row(f"population: {k}", a))
    for v, byg in ag["by_anchors_resolve"].items():
        for g, a in byg.items():
            if a["items"]:
                L.append(row(f"anchors_resolve {v}: {REGIME_NAME[g]}", a))
    L.append("")
    L.append("Per line at the Part S state (the item's drawable placements; counts of lines):\n")
    L.append("| group | lines | no drawable placement | found at every draw | found once at every draw | diff equal at every draw | ok at every draw |")
    L.append("|---|---|---|---|---|---|---|")
    for k, a in list(ag["by_regime"].items()) + [(f"population {p}", a) for p, a in ag["by_population"].items()]:
        ps = a["part_s"]
        L.append(f"| {k} | {a['lines']} | {ps['lines_without_a_drawable_draw']} | {ps['lines_found_at_every_draw']} | "
                 f"{ps['lines_found_once_at_every_draw']} | {ps['lines_diff_equal_at_every_draw']} | {ps['lines_ok_at_every_draw']} |")
    L.append("")
    L.append("Day-0 line failures by reason (brief 26's classes):\n")
    for k, a in ag["by_regime"].items():
        L.append(f"- {k}: {json.dumps(a['day0']['failures_by_reason'])}; at reachable Part S states (state checks, counted per state): "
                 f"{json.dumps(a['part_s']['line_failures_by_reason_state_checks'])}")
    L.append("")
    ll = res["lone_lines"]
    L.append(f"**Lone lines (A6.8, the 78 x 3):** {ll['lines']} lines; with a drawable author {ll['with_a_drawable_author']}; "
             f"valid draws {ll['valid_draws']} of {ll['drawable_draws']}; two valid by different authors {ll['two_valid_distinct_authors']}; "
             f"literal two valid {ll['literal_two_valid']}; two valid on different days {ll['two_valid_distinct_days']}; "
             f"lines with at most three valid authors (where excluding the triple's author could bite) {ll['at_most_three_valid_authors']}; "
             f"invalid-draw reasons {json.dumps(ll['invalid_draw_reasons'])}.\n")
    L.append("## Drop list\n")
    if dl["ids"]:
        for e in dl["entries"]:
            where = {"candidate": ", ".join(e["populations"]), "control": "the control arm", "sham": "the floor"}[e["regime"]]
            L.append(f"- `{e['item_id']}` ({REGIME_NAME[e['regime']]}, {e['writer']}; leaves {where}): "
                     + "; ".join(f"{r['what']}: {r['valid_draws']} valid draws {json.dumps(r['valid_by_day'])}, reasons {r['why']}" for r in e["drop_reasons"]))
    else:
        L.append("- **Empty**: every item has two valid placements on different days by different authors, and every lone line two by different authors.")
    if set(dl["ids_literal"]) != set(dl["ids"]):
        L.append(f"- Under the literal count (two valid draws, any days and authors) the list would be: {dl['ids_literal'] or 'empty'}.")
    L.append(f"\nNet n's after drops: {json.dumps(dl['net_n'])}.\n")
    L.append("## The nine stratum members whose day-0 anchors do not resolve\n")
    L.append("| id | writer | day-0 unresolved lines | valid item draws (day 1 / day 2) | item placements | lone lines with two valid | dropped |")
    L.append("|---|---|---|---|---|---|---|")
    for e in res["unresolved_stratum_members"]:
        L.append(f"| `{e['item_id']}` | {e['writer']} | {e['n_unresolved_anchors']} | {e['valid_draws']} ({e['valid_by_day_1']} / {e['valid_by_day_2']}) | "
                 f"{'ok' if e['item_pair_ok'] else 'too few'} | {e['lone_lines_ok']} of 3 | {e['drop']} |")
    L.append("")
    rc = res["reverse_case"]
    L.append("## Reverse case\n")
    L.append(f"- **{rc['count']}** line(s) ({rc['definition']}){': ' + ', '.join(rc['ids']) if rc['ids'] else ''}; by regime {json.dumps(rc['by_regime'])}.")
    L.append(f"- Beside: absent on at least one drawable day {rc['absent_on_one_drawable_day']}; absent in some state of a drawable day "
             f"{rc['absent_in_some_state_of_a_drawable_day']}. Forward case (absent at day 0, found in a Part S state): {rc['forward_case_count']} "
             f"{json.dumps(rc['forward_case_by_regime'])}; found once in every state of both drawable days {rc['forward_case_found_unique_on_both_days']}.")
    u = rc["uniqueness"]
    L.append(f"- Beside, for uniqueness ({u['definition']}): {len(u['not_unique_in_some_state'])} line(s) not unique in some state of a "
             f"drawable day ({', '.join(u['not_unique_in_some_state']) or 'none'}); of them {len(u['not_unique_in_every_state_of_a_drawable_day'])} "
             f"not unique in every state of a drawable day.\n")
    L.append("## Module findings (reported, not fixed; the coordinator decides)\n")
    for f in res["module_findings"]:
        L.append(f"- **{f['id']}** (stage3_t1.py lines {', '.join(str(x) for x in f['lines'])}): {f['what']}. Count: {f['count']} ({f['count_of']}).")
    L.append("")
    L.append("## S1's draw restriction\n")
    L.append(res["s1_restriction"] + "\n")
    L.append("## Hashes\n")
    for k, v in res["inputs_sha256"].items():
        L.append(f"- `{k}`: `{v}`")
    L.append(f"- script `{res['script']['path']}`: `{res['script']['sha256']}`")
    return "\n".join(L) + "\n"


# ── the run ────────────────────────────────────────────────────────────────────────────────────────

def run(out_dir: Path, corpus: Path, template: Path, procs: int, controls_lone_lines: bool = False) -> dict:
    """`controls_lone_lines` (brief 32): also enumerate each control item's three lines as lone lines."""
    import stage3_legibility as lg
    line_regimes = ("candidate", "control") if controls_lone_lines else ("candidate",)
    from stage3_t1v2_checks import DOCS
    paths = input_paths()
    items, meta = load_items(paths)
    seed = sv.seed_base()
    day0 = {path: text for (_svc, path), text in seed.items() if path in DOCS}
    _init_globals(corpus, template)
    ins, states = _G["ins"], _G["states"]
    days = list(ins.days)
    static = {it["item_id"]: static_checks(states, days, it, day0) for it in items}
    tasks = []
    for it in items:
        payload = {"id": it["payload_id"], "document": it["document"], "statements": it["statements"], "arm": RATED_ARM[it["regime"]]}
        f0 = static[it["item_id"]]["found_day0"]
        tasks.append(("item", it["item_id"], payload, it["statements"], f0))
        if it["regime"] in line_regimes:
            for i, st in enumerate(it["statements"]):
                single = {"id": f"{it['payload_id']}#L{i + 1}", "document": it["document"], "statements": [st], "arm": "singleton"}
                tasks.append(("line", f"{it['item_id']}:{i + 1}", single, [st], [f0[i]]))
    ctx = mp.get_context("fork")
    with ctx.Pool(procs) as pool:
        results = pool.map(_task, tasks, chunksize=1)
    by = {(k, key): r for k, key, r in results}
    rows = []
    for it in items:
        tid = it["item_id"]
        dr = by[("item", tid)]
        all_lone = [by[("line", f"{tid}:{i + 1}")] for i in range(3)] if it["regime"] in line_regimes else None
        # brief 26's fields read the candidates' lone lines only: a control's lines[].lone_line and its drop stay brief 26's
        lone = all_lone if it["regime"] == "candidate" else None
        st = static[tid]
        lines = []
        for i, sm in enumerate(it["statements"]):
            lines.append({"index": i + 1, "op": sm["op"], "day0": st["day0"]["lines"][i],
                          "bank_days": {d: st["bank_days"][d]["lines"][i] for d in days},
                          "part_s": dr["per_line"][i],
                          "lone_line": None if lone is None else {k: lone[i][k] for k in (
                              "n_drawable", "n_valid", "valid_by_day", "pair_ok_distinct_authors", "literal_ok")}})
        dec = decide(it, dr, lone)
        rows.append({"item_id": tid, "regime": it["regime"], "writer": it["writer"], "document": it["document"],
                     "populations": it["populations"], "anchors_resolve": it["anchors_resolve"],
                     "n_unresolved_anchors": it["n_unresolved_anchors"], "lines": lines,
                     "day0_joint_ok": st["day0"]["joint_ok"], "day0_joint_reason": st["day0"]["joint_reason"],
                     "bank_days_joint": {d: {k: st["bank_days"][d][k] for k in ("states", "joint_ok", "joint_reasons")} for d in days},
                     "draws": {k: v for k, v in dr.items() if k != "per_line"},
                     "lone_lines": [] if all_lone is None else [{k: v for k, v in ld.items() if k != "per_line"} for ld in all_lone],
                     **dec})
    rows.sort(key=lambda r: r["item_id"])
    # day 0: brief 25's anchors_resolve reproduced
    reproduced = all(r["anchors_resolve"] == all(ln["day0"]["found"] for ln in r["lines"]) for r in rows)
    drop = [r for r in rows if r["drop"]]
    net = {"78": sum(1 for r in rows if "78" in r["populations"] and not r["drop"]),
           "28": sum(1 for r in rows if "28" in r["populations"] and not r["drop"]),
           "19": sum(1 for r in rows if "19" in r["populations"] and not r["drop"]),
           "21": sum(1 for r in rows if "21" in r["populations"] and not r["drop"]),
           "controls": sum(1 for r in rows if r["regime"] == "control" and not r["drop"]),
           "comparison": sum(1 for r in rows if r["regime"] == "sham" and not r["drop"])}
    mod = module_record()
    unresolved = []
    for r in rows:
        if "28" in r["populations"] and not r["anchors_resolve"]:
            unresolved.append({"item_id": r["item_id"], "writer": r["writer"], "n_unresolved_anchors": r["n_unresolved_anchors"],
                               "valid_draws": r["draws"]["n_valid"], "valid_by_day_1": r["draws"]["valid_by_day"][days[0]],
                               "valid_by_day_2": r["draws"]["valid_by_day"][days[1]], "item_pair_ok": r["draws"]["pair_ok_distinct_days"],
                               "lone_lines_ok": sum(ld["pair_ok_distinct_authors"] for ld in r["lone_lines"]), "drop": r["drop"],
                               "drop_reasons": r["drop_reasons"]})
    if len(unresolved) != 9:
        raise ValueError(f"expected nine unresolved-anchor stratum members, found {len(unresolved)}")
    invalid_drawable = sum(r["draws"]["invalid_draws"] for r in rows) + sum(ld["n_drawable"] - ld["n_valid"] for r in rows for ld in r["lone_lines"])
    total_drawable = sum(r["draws"]["n_drawable"] for r in rows) + sum(ld["n_drawable"] for r in rows for ld in r["lone_lines"])
    s1 = (f"The module's draw rule restricts authors to those with a session in which every target of the role resolves "
          f"(stage3_t1.py line {mod['lines']['anchored_pool']}, `_sessions_with_anchors` line {mod['lines']['sessions_with_anchors']}, "
          f"`_anchor_ready` line {mod['lines']['anchor_ready']}) and re-draws a layout that does not compose (line {mod['lines']['plant_redraws']}), "
          f"but it checks neither a unique target, the exact application, an already-present line nor interference, and after "
          f"{t1.MAX_REDRAWS} re-draws it returns a delivered or last layout (line {mod['lines']['plant_returns_uncomposed']}). "
          + (f"On these items {invalid_drawable} of {total_drawable} drawable placements (item and lone-line) are not valid, so the draw rule "
             f"does not already restrict to valid positions: S1 restricts its seeded draws to the valid (day, author) pairs listed per item "
             f"and per lone line in inserter-dry-run-v0.json (`valid_draws`), and plants lone lines through code the module does not have as an arm (M4)."
             if invalid_drawable else
             f"On these items every one of the {total_drawable} drawable placements (item and lone-line) is valid, so the draw rule already "
             f"restricts to valid positions on this data; S1 may state so citing the lines above, and still needs a lone-line arm (M4)."))
    res = {
        "version": VERSION_V1 if controls_lone_lines else VERSION,
        "brief": "32 v3 (S2, H2 step 1): brief 26 v2's method, by a copy of its script"
                 + (", with the control items' lone lines" if controls_lone_lines else ", default mode"),
        "written": datetime.now().astimezone().isoformat(timespec="seconds"),
        "module": mod,
        "document_states": {
            "day0": {"source": "the seeder's day-0 texts (stage3_views.seed_base(), the six class documents), as briefs 23 and 25 rendered them",
                     "day0_sha256": lg.day0_sha256(day0), "equals_items_v0": lg.day0_sha256(day0) == meta["day0_sha256_items_v0"],
                     "anchors_resolve_reproduced": reproduced},
            "part_s": {"source": "the null corpus rebuilt in memory through mole/oracles/document.py (content_at from the seed) as brief 07h did; the module's whole-write floor applied",
                       "corpus": str(corpus.relative_to(PROJECT)), "corpus_sha256": file_sha256(corpus),
                       "corpus_equals_t1v3": file_sha256(corpus) == meta["t1v3_corpus_sha256"] == V2C_CORPUS_SHA256,
                       "bank_days": days, "drawable_days": days[:2], "day_fixed": False,
                       "day_note": "The day is not fixed (S1's seed stream is not written): every day of the bank is checked (part ii, per line and per state), "
                                   "and the drop rule counts every draw of the two days the lone layout can draw."}},
        "position_case": "every draw enumerated: S1's seed stream is not written, so every (day, author) the module's lone-arm rule can draw "
                         "(the pool `draw_author` would draw from, captured), each with the module's own run and every state the drawn sessions can reach",
        "runs_per_draw": RUNS_PER_DRAW, "max_samples": MAX_SAMPLES, "run_seed": RUN_SEED,
        "rule": {
            "valid draw": "every placed module run composes, with every line's target found exactly once, the line not already present, and the "
                          "planted bytes equal to the intended document (line in place by line index); and at every state the drawn sessions can "
                          "reach, every line passes the same checks alone and the item's lines applied in the module's order do not affect one another. "
                          "A timestamp sample in which the session has no second left for a later line is a property of the sample, not of the "
                          "(day, author) draw: it is re-drawn as the module's plant() re-draws it, and the draw fails for time only when none of "
                          f"{MAX_SAMPLES} samples places",
            "item need (T2)": "two valid draws usable as Part S's two placements: on different days and by different authors (brief 15 S1: "
                              "'a second placement (different authors and days)'); the lone layout draws only days[:2]",
            "lone-line need (S2, candidates only)": "two valid draws by different authors (A6.5 (iii): each line on its own author)",
            **({"lone-line valid draws (controls' add-on, A6.22 (2); brief 32)":
                "listed for every control item's three lines by the same method; a control's drop is the item rule alone, and "
                "whether its lines meet the need is decided after its pair is drawn (S3, tag 6)"} if controls_lone_lines else {}),
            "literal count beside": "two valid draws, any days and authors",
            "drop": "an item short of its need, or a candidate with a lone line short of its need, leaves every population it belongs to"},
        "inputs_sha256": {**{k: file_sha256(p) for k, p in paths.items()},
                          "stratum_ids_sha256 (recorded)": meta["stratum_ids_sha256"]},
        "script": {"path": "work/checks/stage3_b3_inserter_dry_run_v1.py", "sha256": file_sha256(Path(__file__)),
                   "copy_of": {"path": "work/checks/stage3_b3_inserter_dry_run.py", "sha256": B26_SCRIPT_SHA256,
                               "sha256_now": file_sha256(HERE / "stage3_b3_inserter_dry_run.py")},
                   "controls_lone_lines": controls_lone_lines,
                   "table_of_shape": {"path": "work/stage3/b3/inserter-dry-run-v0.json", "sha256": B26_JSON_SHA256}},
        "totals": {"items": len(rows), "item_draws": sum(r["draws"]["n_drawable"] for r in rows),
                   "lone_line_draws": sum(ld["n_drawable"] for r in rows for ld in r["lone_lines"]),
                   "module_runs": sum(r["draws"]["module_runs"] for r in rows) + sum(ld["module_runs"] for r in rows for ld in r["lone_lines"]),
                   "module_samples_no_time": sum(r["draws"]["module_samples_no_time"] for r in rows)
                   + sum(ld["module_samples_no_time"] for r in rows for ld in r["lone_lines"]),
                   "states_checked": sum(r["draws"]["states_checked"] for r in rows) + sum(ld["states_checked"] for r in rows for ld in r["lone_lines"]),
                   "joint_states_applicable": sum(r["draws"]["joint_states_applicable"] for r in rows),
                   "item_draws_without_an_applicable_joint_state": sum(r["draws"]["draws_without_an_applicable_joint_state"] for r in rows)},
        "aggregates": aggregates(rows),
        "lone_lines": lone_line_summary(rows),
        "lone_lines_controls": lone_line_summary(rows, "control") if controls_lone_lines else None,
        "summary_scope": {
            "lone_lines": "candidates only (brief 26's summary, unchanged)",
            "lone_lines_controls": ("the control items' lone lines, the same summary" if controls_lone_lines
                                    else "not computed (default mode)"),
            "totals": ("recomputed with the control items' lone lines (lone_line_draws, module_runs, module_samples_no_time, "
                       "states_checked)" if controls_lone_lines else "brief 26's scope"),
            "s1_restriction": ("recomputed with the control items' lone lines (its drawable and invalid counts)"
                               if controls_lone_lines else "brief 26's scope"),
            "aggregates, drop_list, reverse_case, unresolved_stratum_members": "item-level or candidates only; unaffected by the opt-in",
            "module_findings": "brief 26's function on this run (M4 counts the candidates' lone lines; brief 27 handled M4 and M5)"},
        "drop_list": {"ids": [r["item_id"] for r in drop], "ids_literal": [r["item_id"] for r in rows if r["drop_literal"]],
                      "entries": [{"item_id": r["item_id"], "regime": r["regime"], "writer": r["writer"],
                                   "populations": r["populations"], "drop_reasons": r["drop_reasons"]} for r in drop],
                      "net_n": net},
        "reverse_case": reverse_case(rows, days[:2]),
        "unresolved_stratum_members": unresolved,
        "module_findings": findings(rows, mod),
        "s1_restriction": s1,
        "items": rows,
    }
    return res


def output_paths(out_dir: Path, controls_lone_lines: bool) -> tuple[Path, Path]:
    """brief 32: `inserter-dry-run-v1` with the opt-in, else brief 26's name; never the pinned v0 files in work/stage3/b3."""
    stem = "inserter-dry-run-v1" if controls_lone_lines else "inserter-dry-run-v0"
    pj, pm = out_dir / f"{stem}.json", out_dir / f"{stem}.md"
    pinned = {(OUT / "inserter-dry-run-v0.json").resolve(), (OUT / "inserter-dry-run-v0.md").resolve()}
    if {pj.resolve(), pm.resolve()} & pinned:
        raise SystemExit("refusing to write over brief 26's pinned inserter-dry-run-v0 files: pass --out-dir elsewhere")
    return pj, pm


def render_md_v1(res: Mapping[str, Any]) -> str:
    """brief 26's report, headed by this copy's run and, with the opt-in, the control items' lone-line summary."""
    sc = res["script"]
    head = [f"# Brief 32 v3 (S2): `{Path(sc['path']).name}`, {res['version']} (blue; ids, counts and hashes only)\n",
            f"- Script: `{sc['path']}` sha256 `{sc['sha256']}`, a copy of `{sc['copy_of']['path']}` "
            f"(`{sc['copy_of']['sha256']}`, unchanged on disk: {sc['copy_of']['sha256_now'] == sc['copy_of']['sha256']}); "
            f"control items' lone lines: {sc['controls_lone_lines']}; written {res['written']}.",
            f"- Module: `{res['module']['path']}` sha256 `{res['module']['sha256']}`.",
            "- Summary scope: " + "; ".join(f"{k}: {v}" for k, v in res["summary_scope"].items()) + "."]
    lc = res.get("lone_lines_controls")
    if lc:
        head.append(f"- **Control items' lone lines:** {lc['lines']} lines; with a drawable author {lc['with_a_drawable_author']}; "
                    f"valid draws {lc['valid_draws']} of {lc['drawable_draws']}; two valid by different authors "
                    f"{lc['two_valid_distinct_authors']}; literal two valid {lc['literal_two_valid']}; invalid-draw reasons "
                    f"{json.dumps(lc['invalid_draw_reasons'])}.")
    head.append("\nBrief 26's report on this run follows (its title is brief 26's).\n")
    return "\n".join(head) + "\n" + render_md(res)


def write_outputs(res: Mapping[str, Any], out_dir: Path, guard: Sequence[str]) -> dict[str, str]:
    js = json.dumps(res, indent=1, sort_keys=False, ensure_ascii=False) + "\n"
    md = render_md_v1(res)
    assert_clean(js, guard)
    assert_clean(md, guard)
    pj, pm = output_paths(out_dir, bool(res["script"]["controls_lone_lines"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    pj.write_text(js, encoding="utf-8")
    pm.write_text(md, encoding="utf-8")
    return {"json": file_sha256(pj), "md": file_sha256(pm)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="brief 32 (copy of brief 26's script): the edit-application dry run on every B3 item")
    ap.add_argument("mode", choices=("run",))
    ap.add_argument("--controls-lone-lines", action="store_true",
                    help="brief 32: also enumerate the control items' lone lines; writes inserter-dry-run-v1.{json,md}")
    ap.add_argument("--out-dir", default=str(OUT))
    ap.add_argument("--corpus", default=str(CORPUS))
    ap.add_argument("--template", default=str(sv.jc_mod.FORK / "bootstrap" / "org_template.yaml"))
    ap.add_argument("--procs", type=int, default=12)
    ns = ap.parse_args(argv)
    from stage3_t1v2_checks import DOCS
    output_paths(Path(ns.out_dir), ns.controls_lone_lines)     # refuse before the run, not after it
    res = run(Path(ns.out_dir), Path(ns.corpus), Path(ns.template), ns.procs, ns.controls_lone_lines)
    items, _meta = load_items(input_paths())
    day0 = {path: text for (_svc, path), text in sv.seed_base().items() if path in DOCS}
    h = write_outputs(res, Path(ns.out_dir), guard_texts(items, day0, input_paths()))
    print(json.dumps({"drop": len(res["drop_list"]["ids"]), "drop_literal": len(res["drop_list"]["ids_literal"]),
                      "reverse_case": res["reverse_case"]["count"], "net_n": res["drop_list"]["net_n"],
                      "totals": res["totals"], "lone_lines_controls": res["lone_lines_controls"], "sha256": h}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
