#!/usr/bin/env python3
"""Line P0, Part 1 (brief `work/stage3/v5/P0/brief-state-and-rescore.md`, a519f2ce): the T1 state check, $0, on the
honest corpus prefix_rw_v2c. Blue side; counts only, no text printed.

Facts from the code (stated with file and line in `P0/state-check-v0.md`): `mole/oracles/document.py` replays writes in
file order (`_iter_writes`, enumerate over the rows) and a time bound only selects which writes count; the null's "after"
state is a file-order prefix (`stage3_views.document_timeline`), its "before" state and the planted units' states are
time-bounded selections applied in file order (`stage3_views.cumulative_diff_units`, `stage3_t1_score.build_items`).

What this module measures:
* which order the live world applied writes in: each candidate order (file, simulated `ts`, wall-clock `real_ts`) is
  replayed over the six class documents and checked against the log's own observations: a successful read's `bytes`
  must equal the document's size, a successful `replace_in_file` must find its text;
* whether a time-bounded state is a live state: the writes selected by the bound must be a file-order prefix of that
  document's writes (else the state is a mixture no reader could have seen), and whether its content equals that
  prefix's content anyway;
* how many null units and composition-time states differ between file order and simulated-time order.
Plant records are read by script for ids and times only (`PLANT_FIELDS`); no statement text is touched.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import judge_client  # noqa: E402,F401  (puts the fork on sys.path)
from mole.oracles import document as doc  # noqa: E402

PLANT_FIELDS = ("payload_id", "arm", "regime", "document", "pre_window_boundary", "composition_ts", "composition_day",
                "composed", "delivered")
WRITE_ACTIONS = ("write_file", "append_to_file", "replace_in_file", "delete")
IN_SCOPE = {"t1v2": ("conforming", "alarming"), "t1v3": ("middle", "routine_redraw")}


def plant_fields(rec: Mapping[str, Any]) -> dict:
    return {k: rec.get(k) for k in PLANT_FIELDS}


def orders(rows: Sequence[Mapping]) -> dict[str, list[int]]:
    n = len(rows)
    return {"file": list(range(n)),
            "ts": sorted(range(n), key=lambda i: (str(rows[i].get("ts") or ""), i)),
            "real_ts": sorted(range(n), key=lambda i: (float(rows[i].get("real_ts") or 0.0), i))}


def _ok(r: Mapping) -> bool:
    return (r.get("exit_code") or 0) == 0


def _path(r: Mapping) -> str | None:
    return (r.get("args") or {}).get("path") if r.get("service") == "owncloud" else None


def _seed(path: str, base: Mapping) -> Any:
    return doc.content_at([], doc.DocRef("owncloud", path), None, base=base)


def _apply(cur: Any, r: Mapping, path: str, base: Mapping) -> Any:
    b = {("owncloud", path): cur} if isinstance(cur, str) else {k: v for k, v in base.items() if k != ("owncloud", path)} | {("owncloud", "\0none"): ""}
    return doc.content_at([r], doc.DocRef("owncloud", path), None, base=b)


def state(rows: Sequence[Mapping], order: Sequence[int], path: str, base: Mapping, *, upto: int | None = None) -> Any:
    """The document after replaying, in `order`, every successful write to it among the first `upto` positions."""
    cur = _seed(path, base)
    for k, i in enumerate(order):
        if upto is not None and k >= upto:
            break
        r = rows[i]
        if _path(r) == path and _ok(r) and r.get("action") in WRITE_ACTIONS:
            cur = _apply(cur, r, path, base)
    return cur


def event_consistency(rows: Sequence[Mapping], paths: Sequence[str], base: Mapping) -> dict[str, dict]:
    out = {}
    for name, order in orders(rows).items():
        cur = {p: _seed(p, base) for p in paths}
        c = Counter({"reads": 0, "read_bytes_match": 0, "replaces": 0, "replace_find_present": 0})
        for i in order:
            r = rows[i]
            p = _path(r)
            if p not in cur or not _ok(r):
                continue
            if r.get("action") == "read_file" and isinstance(cur[p], str) and r.get("bytes") is not None:
                c["reads"] += 1
                c["read_bytes_match"] += int(len(cur[p].encode("utf-8")) == int(r["bytes"]))
            if r.get("action") == "replace_in_file":
                f = (r.get("args") or {}).get("find")
                c["replaces"] += 1
                c["replace_find_present"] += int(isinstance(cur[p], str) and isinstance(f, str) and f in cur[p])
            if r.get("action") in WRITE_ACTIONS:
                cur[p] = _apply(cur[p], r, p, base)
        out[name] = dict(c)
    return out


def _writes(rows: Sequence[Mapping], path: str) -> list[int]:
    return [i for i, r in enumerate(rows) if _path(r) == path and _ok(r) and r.get("action") in WRITE_ACTIONS]


def _le(ts: str, bound: str) -> bool:
    return ts[:10] <= bound if len(bound) == 10 else ts <= bound


def live_state(rows: Sequence[Mapping], path: str, bound: str, base: Mapping) -> dict:
    """Is the state the recorded scorers build at `bound` (writes with ts <= bound, in file order) a live state?"""
    ws = _writes(rows, path)
    sel = [i for i in ws if _le(str(rows[i].get("ts") or ""), bound)]
    if not sel:
        return {"prefix": True, "n_selected": 0, "n_excluded_before_last": 0, "content_equals_prefix": True}
    last = max(sel)
    prefix = [i for i in ws if i <= last]
    excluded = len(prefix) - len(sel)
    file_order = orders(rows)["file"]
    got = state([rows[i] for i in sel], list(range(len(sel))), path, base)
    pre = state(rows, file_order, path, base, upto=last + 1)
    return {"prefix": excluded == 0, "n_selected": len(sel), "n_excluded_before_last": excluded, "content_equals_prefix": got == pre}


def compare_at(rows: Sequence[Mapping], path: str, bound: str, base: Mapping) -> dict:
    """The state at `bound` built in file order (the recorded way) against simulated-time order."""
    sel = [i for i in _writes(rows, path) if _le(str(rows[i].get("ts") or ""), bound)]
    f = state([rows[i] for i in sel], list(range(len(sel))), path, base)
    t_sel = sorted(sel, key=lambda i: (str(rows[i].get("ts") or ""), i))
    t = state([rows[i] for i in t_sel], list(range(len(t_sel))), path, base)
    lines = lambda s: set(s.splitlines()) if isinstance(s, str) else None  # noqa: E731
    return {"differs": f != t, "line_set_differs": lines(f) != lines(t)}


def null_unit_compare(rows: Sequence[Mapping], units: Sequence[Mapping], base: Mapping) -> list[dict]:
    """Per null unit: does its packet (diff from the boundary state to the state at its write) change if both states are
    built in simulated-time order? `units` carry path, boundary name and index, write index (file position)."""
    o = orders(rows)
    pos_ts = {i: k for k, i in enumerate(o["ts"])}
    days = sorted({str(r.get("ts") or "")[:10] for r in rows if r.get("ts")})
    out = []
    cache: dict[tuple, Any] = {}
    for u in units:
        p, bi, wi = u["path"], u["boundary_index"], u["write_index"]
        bound = days[0] + "T00:00:00Z" if bi == 0 else days[bi - 1]
        kf = ("f", p, bound)
        if kf not in cache:
            sel = [i for i in _writes(rows, p) if _le(str(rows[i].get("ts") or ""), bound)]
            cache[kf] = state([rows[i] for i in sel], list(range(len(sel))), p, base)
            ts_sel = sorted(sel, key=lambda i: (str(rows[i].get("ts") or ""), i))
            cache[("t", p, bound)] = state([rows[i] for i in ts_sel], list(range(len(ts_sel))), p, base)
            cache[("live", p, bound)] = live_state(rows, p, bound, base)
        af = state(rows, o["file"], p, base, upto=wi + 1)
        at = state(rows, o["ts"], p, base, upto=pos_ts[wi] + 1)
        bf, bt = cache[kf], cache[("t", p, bound)]
        df, dt = doc.unified_diff(bf, af, p), doc.unified_diff(bt, at, p)
        lines = lambda s: set(s.splitlines()) if isinstance(s, str) else None  # noqa: E731
        out.append({"path": p, "write_day": u["write_day"], "boundary_index": bi,
                    "packet_differs": df != dt, "line_set_differs": (lines(bf), lines(af)) != (lines(bt), lines(at)),
                    "before_is_live": cache[("live", p, bound)]["prefix"], "before_content_live": cache[("live", p, bound)]["content_equals_prefix"]})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P0 Part 1: the T1 state check (counts only).")
    ap.add_argument("--plants-v2", type=Path, required=True)
    ap.add_argument("--plants-v3", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out} exists")
    import stage3_ft_slots as sl
    import stage3_views as sv
    corpus = Path(sl.CORPUS)
    rows = sv.read_jsonl(corpus)
    base = sv.seed_base()
    paths = sv.class_doc_paths()
    days = sv.corpus_days(rows)
    res: dict[str, Any] = {"corpus_sha256": sv.file_sha256(corpus), "n_rows": len(rows)}
    o = orders(rows)
    res["adjacent_inversions_in_file_order"] = {k: sum(1 for i in range(1, len(rows)) if (rows[i].get(f) or ("" if k == "ts" else 0)) < (rows[i - 1].get(f) or ("" if k == "ts" else 0)))
                                               for k, f in (("ts", "ts"), ("real_ts", "real_ts"))}
    res["event_consistency"] = event_consistency(rows, paths, base)
    tl = {p: sv.document_timeline(rows, p, base) for p in paths}
    units = [u for u in sv.cumulative_diff_units(rows, paths, days, base, sv.stem_of(corpus), tl) if u.get("packet") is not None]
    nc = null_unit_compare(rows, units, base)
    by = defaultdict(Counter)
    for u in nc:
        k = f"{u['path'].split('/')[-1]}|{u['write_day']}"
        by[k]["units"] += 1
        for f in ("packet_differs", "line_set_differs"):
            by[k][f] += int(u[f])
        by[k]["before_not_live"] += int(not u["before_is_live"])
        by[k]["before_content_not_live"] += int(not u["before_content_live"])
    tot = Counter()
    for v in by.values():
        tot.update(v)
    res["null_units"] = {"total": dict(tot), "by_document_and_day": {k: dict(v) for k, v in sorted(by.items())}}
    # composition-time states of the in-scope applications (honest corpus; plants files read for ids and times only)
    apps = []
    for planting, pth in (("t1v2", a.plants_v2), ("t1v3", a.plants_v3)):
        man = json.loads(pth.read_text(encoding="utf-8"))
        for rec in man["plants"]:
            f = plant_fields(rec)
            if f["regime"] in IN_SCOPE[planting] and f["composed"] and f["delivered"]:
                apps.append({"planting": planting, **f})
    rows_c = []
    for ap_ in apps:
        p = ap_["document"]
        for label, bound in (("composition_ts", ap_["composition_ts"]), ("composition_day_end", ap_["composition_day"])):
            cmp_ = compare_at(rows, p, bound, base)
            live = live_state(rows, p, bound, base)
            rows_c.append({"key": f"{ap_['planting']}:{ap_['payload_id']}:{ap_['arm']}", "regime": ap_["regime"], "doc": p.split("/")[-1],
                           "day": ap_["composition_day"], "bound": label, **cmp_, "prefix": live["prefix"], "content_live": live["content_equals_prefix"]})
        pre = ap_["pre_window_boundary"]
        if pre and pre != "day0":
            cmp_ = compare_at(rows, p, pre, base)
            live = live_state(rows, p, pre, base)
            rows_c.append({"key": f"{ap_['planting']}:{ap_['payload_id']}:{ap_['arm']}", "regime": ap_["regime"], "doc": p.split("/")[-1],
                           "day": ap_["composition_day"], "bound": "pre_window", **cmp_, "prefix": live["prefix"], "content_live": live["content_equals_prefix"]})
    summ = defaultdict(Counter)
    for r in rows_c:
        k = r["bound"]
        summ[k]["states"] += 1
        summ[k]["differs"] += int(r["differs"])
        summ[k]["line_set_differs"] += int(r["line_set_differs"])
        summ[k]["not_prefix"] += int(not r["prefix"])
        summ[k]["content_not_live"] += int(not r["content_live"])
    by_doc = defaultdict(Counter)
    for r in rows_c:
        if r["bound"] == "composition_day_end":
            kk = f"{r['doc']}|{r['day']}"
            by_doc[kk]["apps"] += 1
            by_doc[kk]["differs"] += int(r["differs"])
            by_doc[kk]["content_not_live"] += int(not r["content_live"])
    res["applications"] = {"n": len(apps), "by_bound": {k: dict(v) for k, v in summ.items()},
                           "composition_day_end_by_document_and_day": {k: dict(v) for k, v in sorted(by_doc.items())},
                           "content_not_live_keys": sorted({r["key"] for r in rows_c if not r["content_live"]})}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("null_units",)} | {"null_units_total": res["null_units"]["total"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
