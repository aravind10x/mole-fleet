#!/usr/bin/env python3
"""Line FT, blue side, step 1: the slot inventory of the six class documents from the honest states.

A slot is either an ITEM (one line of a document, identified without its content) or a SECTION taken
as a whole (for content that is added to a section). Identity is content-independent: the document,
the section path (lower-cased heading texts joined by " > ") and a selector that is never a value:

  label=<label>#<n>   a `Label: value` line (bullet, bold or plain), the n-th with that label in the section
  step=<N>            a numbered line, by its number
  yaml=<a.b.c>        a key inside a fenced yaml block, by its dotted path
  ord=<n>             any other line, by its position among the section's unkeyed lines
  section             the section as a whole

The same slot can hold different content in different honest states; `honest_states` lists the state
indices (per document: 0 the day-0 seed, then one per successful content write, in log order) in which
the slot exists. Kinds: `procedure_step` (numbered lines), `operational_value` (a keyed line whose value
is a single configuration-type token or a short list of them), `label` (a keyed line whose value is prose
or empty), `other` (everything else: free lines, date-valued lines, boolean toggles). A slot's kind is
the modal kind over its states, a tie going to the first state. A section slot is `procedure_step` when
most of its direct lines are numbered, else `other`; never `operational_value`.

Nothing here reads a plants file, an application file, a t1 result or the pilot corpus; the states are
replayed from the honest prefix by the shared reader (`stage3_views.document_timeline`).

    work/mole-fork/.venv/bin/python -I work/checks/stage3_ft_slots.py write
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent


def _roots() -> tuple[Path, Path]:
    """(work dir, fork dir): this file lives in work/checks or in the fork's scripts/stage3 mirror."""
    for p in (HERE, *HERE.parents):
        if (p / "mole-fork").is_dir():
            return p, p / "mole-fork"
        if p.name == "mole-fork":
            return p.parent, p
    raise RuntimeError("cannot locate work/mole-fork")


WORK, FORK = _roots()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(FORK) not in sys.path:
    sys.path.insert(0, str(FORK))

CORPUS = FORK / "data" / "corpus" / "spike" / "prefix_rw_v2c.jsonl"
OUT_DIR = WORK / "stage3" / "v5" / "FT" / "blue"
KINDS = ("operational_value", "procedure_step", "label", "other")

_HEAD = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_STEP = re.compile(r"^\s*(\d+)\.\s+(.*?)\s*$")
_BULLET = re.compile(r"^\s*[-*]\s+")
_FENCE = re.compile(r"^\s*```")
_RULE = re.compile(r"^\s*(?:-{3,}|\*{3,})\s*$")
_YAML = re.compile(r"^(\s*)([A-Za-z0-9_.-]+):\s*(.*?)\s*$")
_KEYED = re.compile(r"^(?:\*\*)?(?P<label>[^:*`—]{1,40}?)(?:\*\*)?:(?:\s+|$)(?P<value>.*)$")
_DATE_LABEL = re.compile(r"^\d{4}-\d{2}-\d{2}")
_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ][\d:.]+Z?)?$")
_WS = re.compile(r"\s+")

_TOKEN_VERSIONISH = re.compile(r"^[A-Za-z0-9_.:/<>-]*\d[A-Za-z0-9_.:/<>-]*$")
_TOKEN_HANDLE = re.compile(r"^[a-z]+\.[a-z0-9]+$")
_PLAIN = re.compile(r"^[A-Za-z][A-Za-z-]*$")


def _norm(s: str) -> str:
    return _WS.sub(" ", s).strip()


# ── value classification ─────────────────────────────────────────────────────────────────────────

def _strip_annotation(v: str) -> str:
    s = v.strip()
    s = re.sub(r"\s+#\s.*$", "", s)                 # trailing yaml comment
    s = s.split(" — ")[0]                           # dated or attributed tail
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s)          # trailing parenthetical
    s = re.sub(r"\s+by\s+\S+$", "", s)              # "... by handle"
    return s.strip()


def _is_token(p: str) -> bool:
    p = p.strip()
    if not p:
        return False
    if p.startswith("`") and p.endswith("`") and len(p) > 2:
        return True
    if re.match(r"^#[\w-]+$", p) or re.match(r"^https?://\S+$", p) or re.match(r"^/\S+$", p):
        return True
    if _TOKEN_VERSIONISH.match(p) or _TOKEN_HANDLE.match(p):
        return True
    return False


def classify_value(value: str) -> str:
    """The kind a keyed line's value gives the line: operational_value, label or other (a date or a boolean)."""
    s = _strip_annotation(value)
    if not s:
        return "label"
    if _DATE_ONLY.match(s) or s.lower() in ("true", "false"):
        return "other"
    parts = [p.strip() for p in s.split(",")]
    ok = True
    n_tok = 0
    for p in parts:
        if _is_token(p):
            n_tok += 1
        elif len(p.split()) <= 3 and all(_PLAIN.match(w) for w in p.split()) and p:
            continue
        else:
            ok = False
            break
    return "operational_value" if ok and n_tok else "label"


# ── parsing one state ───────────────────────────────────────────────────────────────────────────

def parse_state(text: str) -> list[dict[str, Any]]:
    """The item lines of one document state, each with its section key, selector, value and raw text."""
    items: list[dict[str, Any]] = []
    stack: list[tuple[int, str, str]] = []          # (level, display text, key text)
    ord_n: Counter = Counter()
    label_n: Counter = Counter()
    in_fence = False
    ystack: list[tuple[int, str]] = []

    def skey() -> str:
        return " > ".join(f"{'#' * lv} {k}" for lv, _d, k in stack)

    # a title-less preamble counts as a section with an empty key
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if not in_fence:
            m = _HEAD.match(line)
            if m:
                lvl, disp = len(m.group(1)), _norm(m.group(2))
                while stack and stack[-1][0] >= lvl:
                    stack.pop()
                stack.append((lvl, disp, disp.lower()))
                continue
        if _FENCE.match(line):
            in_fence = not in_fence
            ystack = []
            continue
        if _RULE.match(line):
            continue
        sec = skey()
        disp = stack[-1][1] if stack else ""
        rec: dict[str, Any] = {"section_key": sec, "section": disp, "raw": _norm(line)}
        if in_fence:
            ym = _YAML.match(line)
            if ym:
                ind, key, val = len(ym.group(1)), ym.group(2), ym.group(3)
                while ystack and ystack[-1][0] >= ind:
                    ystack.pop()
                if val == "":
                    ystack.append((ind, key))
                    continue
                path = ".".join([k for _i, k in ystack] + [key])
                rec.update(selector=f"yaml={path.lower()}", value=_norm(val), kind=classify_value(val),
                           label_disp=path)
                items.append(rec)
                continue
        sm = _STEP.match(line)
        if sm:
            rec.update(selector=f"step={int(sm.group(1))}", value=_norm(sm.group(2)), kind="procedure_step")
            items.append(rec)
            continue
        body = _BULLET.sub("", line, count=1).strip()
        km = _KEYED.match(body)
        if km:
            label = _norm(km.group("label")).lower()
            if len(label.split()) <= 6 and not _DATE_LABEL.match(label) and label:
                label_n[(sec, label)] += 1
                val = _norm(km.group("value"))
                rec.update(selector=f"label={label}#{label_n[(sec, label)]}", value=val, kind=classify_value(val),
                           label_disp=_norm(km.group("label")))
                items.append(rec)
                continue
        ord_n[sec] += 1
        rec.update(selector=f"ord={ord_n[sec]}", value=_norm(body), kind="other")
        items.append(rec)
    return items


def _sections_of(text: str) -> dict[str, str]:
    """{section key: display heading} for every heading of a state, empty sections included."""
    out: dict[str, str] = {}
    stack: list[tuple[int, str, str]] = []
    in_fence = False
    for line in text.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEAD.match(line.rstrip())
        if m:
            lvl, disp = len(m.group(1)), _norm(m.group(2))
            while stack and stack[-1][0] >= lvl:
                stack.pop()
            stack.append((lvl, disp, disp.lower()))
            out[" > ".join(f"{'#' * lv} {k}" for lv, _d, k in stack)] = disp
    return out


# ── enumeration ──────────────────────────────────────────────────────────────────────────────────

def _locator(doc: str, section_key: str, selector: str) -> str:
    return f"{doc} :: {section_key} :: {selector}"


def _slot_id(locator: str) -> str:
    return "ft-" + hashlib.sha256(locator.encode("utf-8")).hexdigest()[:8]


def _modal(kinds_in_order: Sequence[str]) -> str:
    c = Counter(kinds_in_order)
    top = max(c.values())
    for k in kinds_in_order:                        # first state wins a tie
        if c[k] == top:
            return k
    return "other"


def enumerate_slots(states: Mapping[str, Sequence[tuple[int, str, str]]]) -> list[dict[str, Any]]:
    """One record per slot: slot_id, document, section, granularity, slot_kind, locator, honest_states."""
    slots: list[dict[str, Any]] = []
    for doc in states:
        item_info: dict[tuple[str, str], dict[str, Any]] = {}
        sec_info: dict[str, dict[str, Any]] = {}
        order: list[tuple[str, str]] = []
        for idx, _ts, text in states[doc]:
            for sk, disp in _sections_of(text).items():
                si = sec_info.setdefault(sk, {"section": disp, "states": [], "kinds": []})
                si["states"].append(idx)
            for it in parse_state(text):
                key = (it["section_key"], it["selector"])
                if key not in item_info:
                    item_info[key] = {"section": it["section"], "states": [], "kinds": []}
                    order.append(key)
                item_info[key]["states"].append(idx)
                item_info[key]["kinds"].append(it["kind"])
                sec_info.setdefault(it["section_key"], {"section": it["section"], "states": [], "kinds": []})
                sec_info[it["section_key"]]["kinds"].append(it["kind"])
        for sk, si in sec_info.items():
            loc = _locator(doc, sk, "section")
            n_step = sum(1 for k in si["kinds"] if k == "procedure_step")
            kind = "procedure_step" if si["kinds"] and n_step * 2 > len(si["kinds"]) else "other"
            slots.append({"slot_id": _slot_id(loc), "document": doc, "section": si["section"],
                          "granularity": "section", "slot_kind": kind, "locator": loc,
                          "honest_states": sorted(set(si["states"]))})
        for key in order:
            sk, sel = key
            ii = item_info[key]
            loc = _locator(doc, sk, sel)
            slots.append({"slot_id": _slot_id(loc), "document": doc, "section": ii["section"],
                          "granularity": "item", "slot_kind": _modal(ii["kinds"]), "locator": loc,
                          "honest_states": sorted(set(ii["states"]))})
    return slots


def slot_contents(states: Mapping[str, Sequence[tuple[int, str, str]]], slot: Mapping[str, Any]
                  ) -> dict[int, list[str]]:
    """{state index: the slot's content in that state}. An item slot: [value] (a numbered line's text, a
    keyed line's value, a free line's text). A section slot: the raw text of every direct line."""
    doc, sk, sel = [p.strip() for p in slot["locator"].split(" :: ", 2)]
    out: dict[int, list[str]] = {}
    for idx, _ts, text in states[doc]:
        items = parse_state(text)
        if sel == "section":
            if sk in _sections_of(text):
                out[idx] = [i["raw"] for i in items if i["section_key"] == sk]
        else:
            for i in items:
                if i["section_key"] == sk and i["selector"] == sel:
                    out[idx] = [i["value"]]
                    break
    return out


def summarise(slots: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_doc: Counter = Counter(s["document"] for s in slots)
    by_gran: Counter = Counter(s["granularity"] for s in slots)
    by_kind: Counter = Counter(s["slot_kind"] for s in slots)
    cross: dict[str, Counter] = defaultdict(Counter)
    for s in slots:
        cross[s["document"]][f'{s["granularity"]}/{s["slot_kind"]}'] += 1
    return {"total": len(slots), "by_document": dict(by_doc), "by_granularity": dict(by_gran),
            "by_kind": dict(by_kind), "by_document_kind": {d: dict(c) for d, c in cross.items()}}


# ── the honest states ────────────────────────────────────────────────────────────────────────────

def load_honest_states(corpus: Path = CORPUS) -> dict[str, list[tuple[int, str, str]]]:
    """{document: [(state index, timestamp or 'seed', text)]}: the day-0 seed (index 0) and the state after
    every successful content write, replayed by the shared reader."""
    import stage3_views as sv
    rows = sv.read_jsonl(Path(corpus))
    base = sv.seed_base()
    out: dict[str, list[tuple[int, str, str]]] = {}
    for p in sv.class_doc_paths():
        seed = base[("owncloud", p)]
        lst: list[tuple[int, str, str]] = [(0, "seed", seed)]
        for ch in sv.document_timeline(rows, p, base):
            if ch.after is not None:
                lst.append((len(lst), str(ch.ts), ch.after))
        out[p] = lst
    return out


def sha8(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:8]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["write"])
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ns = ap.parse_args(argv)
    states = load_honest_states()
    slots = enumerate_slots(states)
    summ = summarise(slots)
    out = Path(ns.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "slots-v0.json").write_text(json.dumps(slots, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    state_map = {d: [{"index": i, "ts": ts} for i, ts, _t in lst] for d, lst in states.items()}
    (out / "states-v0.json").write_text(json.dumps(state_map, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
