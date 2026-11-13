#!/usr/bin/env python3
"""Line S3 (roadmap v5) drivers on the fork's venv: read the corpora, apply the frozen rules in
stage3_s3_deviance.py, write ids, flags and counts only. Never prints task, write or transcript
text; judge packets are built in memory (MOLE-shaped) or read from work/fakelab/s3/ (FakeLab,
built there by s3_fakelab.py under the FakeLab venv) and are never written by this script.

  prefix     prefix_rw_v2c: every changing file write, the item-level reproduction (59 of 127),
             L at path level, the containment proxy -> work/stage3/v5/S3/s3-units-prefix.json
  plan       the judge sample per source, its call count and dollar estimate (no call)
  judge      the judge calls for one source (needs --go; stops at 1.5 x the printed estimate)
  table      s3-table-v0.json and .md from the unit files and judge records

    work/mole-fork/.venv/bin/python -I work/checks/stage3_s3_run.py prefix
    (cd work && set -a && source mole-fork/.env && set +a && \
       mole-fork/.venv/bin/python -I checks/stage3_s3_run.py judge --source prefix --go)
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_s3_deviance as s3  # noqa: E402

WORK = HERE.parent
OUT = WORK / "stage3" / "v5" / "S3"
FL = WORK / "fakelab" / "s3"
A2_V1 = WORK / "stage3" / "phase-a" / "a2-tail-v1.json"
JUDGE_MODEL = "anthropic.claude-sonnet-5"
EST_IN_CHARS_PER_TOKEN = 3.5
EST_OUT_TOKENS = 15
STOP_FACTOR = 1.5


def sha8(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:8]


def wjson(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n", encoding="utf-8")


# ── prefix_rw_v2c ──────────────────────────────────────────────────────────────────────

def prefix_units(keep_text: bool = False) -> tuple[list[dict], dict, dict]:
    """(units, beside counts, reproduction). With keep_text, each unit carries its task texts and
    changed lines in memory (for packets); the written file never does."""
    import stage3_a1_cover as a1
    import stage3_rung1_class as rc
    import stage3_views as sv
    import stage3_write_yield as wy

    rows = a1.read_jsonl(a1.CORPUS)
    trs = a1.read_jsonl(a1.TRANSCRIPTS)
    sess: dict[str, dict] = {}
    for t in trs:
        tid = str(t.get("task_id") or "")
        fed = wy.fed_items(dict(t))
        parsed = [a1.parse_task(x) for x in fed]
        lic = [x for x, p in zip(fed, parsed) if not (p is not None and p.kind == "read")]
        sess[tid] = {"fed": fed, "lic": lic, "tasks": [p for p in parsed if p is not None]}
    base = sv.seed_base()
    paths = sorted({s3.write_target(r.get("service"), r.get("action"), r.get("args") or {})[0]
                    for r in rows if r.get("exit_code") == 0
                    and s3.write_target(r.get("service"), r.get("action"), r.get("args") or {})})
    changes: dict[int, Any] = {}
    for p in paths:
        for c in sv.document_timeline(rows, p, base):
            changes[c.index] = c
    units: list[dict] = []
    beside = Counter()
    for i, r in enumerate(rows):
        if r.get("exit_code") != 0:
            continue
        tg = s3.write_target(r.get("service"), r.get("action"), r.get("args") or {})
        if tg is None:
            if r.get("action") in ("mkdir", "delete", "share", "public_link", "create_issue", "update_issue",
                                   "transition_issue", "add_comment", "tag_approved", "deploy", "register_checkpoint",
                                   "ensure_checkpoint", "set_access_policy", "rotate", "submit_eval", "create_config",
                                   "create_project", "create_channel", "add_group_member", "run_reference_suite"):
                beside["other_state_changing_calls"] += 1
            continue
        path, project = tg
        c = changes.get(i)
        before = c.before if c is not None else None
        after = c.after if c is not None else None
        if c is None:
            beside["write_not_in_reader_timeline"] += 1
        args = r.get("args") or {}
        changing = s3.is_changing(r.get("action"), args, before, after)
        if not changing:
            beside["noop_writes"] += 1
            continue
        tid = str(r.get("task_id") or "")
        S = sess.get(tid)
        has_task = bool(S and S["fed"])
        is_class = path in rc.DOC_PATHS
        u = {"uid": f"prefix:{i}", "index": i, "cluster": tid, "path_class_doc": is_class,
             "action": r.get("action"), "has_session": S is not None, "has_task": has_task,
             "n_fed": len(S["fed"]) if S else 0}
        if has_task:
            u["L_path"] = s3.literal_path_licensed(path, project, S["lic"])
            u["proxy"] = s3.contained(path, project, S["lic"])
        if is_class:
            if before is None and after is None:
                rem, add = [], []
            else:
                rem, add = s3.changed_lines(before, after)
            items, route = s3.attribute(rem + add, a1.ITEMS[path])
            named_w = {t.item for t in (S["tasks"] if S else []) if t.doc == path and t.kind == "write"}
            u.update({"items": sorted(items), "route": route, "L_item": s3.item_licensed(items, named_w)})
        if keep_text:
            if before is None and after is None:
                rem, add = ([], [args.get("text") or ""]) if r.get("action") == "append_to_file" else \
                    ([args.get("find") or ""], [args.get("replace") or ""]) if r.get("action") == "replace_in_file" else \
                    ([], (args.get("content") or "").splitlines())
            else:
                rem, add = s3.changed_lines(before, after)
            u["_desc"] = s3.render_write(r.get("service"), r.get("action"), path, project, rem, add)
            u["_tasks"] = list(S["fed"]) if S else []
        units.append(u)
    # reproduction against stage3_a2_audit (a2-tail-v1 write records: ids and classes only)
    rec = {w["index"]: w for w in json.loads(A2_V1.read_text(encoding="utf-8"))["write_records"]}
    cls = [u for u in units if u["path_class_doc"]]
    a2_live = {i for i, w in rec.items() if not w["noop"]}
    mine = {u["index"] for u in cls}
    agree = sum(1 for u in cls if u["index"] in rec and
                (rec[u["index"]]["class"] == "item_licensed") == u["L_item"])
    repro = {"a2_changing": len(a2_live), "a2_unlicensed_item": sum(1 for i in a2_live if rec[i]["class"] == "unlicensed"),
             "mine_changing": len(cls), "mine_unlicensed_item": sum(1 for u in cls if not u["L_item"]),
             "same_write_set": mine == a2_live, "only_a2": sorted(a2_live - mine), "only_mine": sorted(mine - a2_live),
             "class_agree": agree, "items_agree": sum(1 for u in cls if u["index"] in rec and
                                                      sorted(rec[u["index"]]["items"]) == u["items"])}
    beside["sessions"] = len(sess)
    beside["sessions_with_no_fed_item"] = sum(1 for s in sess.values() if not s["fed"])
    return units, dict(beside), repro


def cmd_prefix(ns) -> None:
    units, beside, repro = prefix_units()
    out = {"source": "prefix_rw_v2c", "rules": s3.VERSION, "rules_sha8": sha8(HERE / "stage3_s3_deviance.py"),
           "driver_sha8": sha8(Path(__file__)), "units": units, "beside": beside, "reproduction": repro}
    wjson(OUT / "s3-units-prefix.json", out)
    print(json.dumps({"n_units": len(units), "beside": beside, "reproduction": repro}, indent=1))


# ── the judge ──────────────────────────────────────────────────────────────────────────

def sample_for(source: str) -> tuple[list[dict], dict[str, float], dict]:
    """(sampled units with packets in memory, weights, meta)."""
    if source == "prefix":
        units, _, _ = prefix_units(keep_text=True)
        tasked = [u for u in units if u["has_task"]]
        must = [u["uid"] for u in tasked if u["path_class_doc"]]
        uids, w = s3.draw_sample([u["uid"] for u in tasked], s3.SAMPLE_CAP, s3.SEED, must=must)
        by = {u["uid"]: u for u in tasked}
        S = [by[x] for x in uids]
        for u in S:
            u["_packet"] = s3.judge_packet(u["_tasks"], u["_desc"])
        return S, w, {"n_tasked": len(tasked), "must": len(must)}
    if source == "fakelab":
        P = [json.loads(x) for x in (FL / "_packets" / "packets-fakelab.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        uids, w = s3.draw_sample([p["uid"] for p in P], s3.SAMPLE_CAP, s3.SEED)
        by = {p["uid"]: p for p in P}
        S = [{"uid": x, "cluster": by[x]["cluster"], "_packet": by[x]["packet"]} for x in uids]
        return S, w, {"n_tasked": len(P), "must": 0}
    raise SystemExit(f"unknown source {source}")


def records_path(source: str) -> Path:
    return (FL if source == "fakelab" else OUT) / f"s3-judge-records-{source}.jsonl"


def estimate(S: list[dict]) -> dict:
    tin = sum((len(u["_packet"]) + len(s3.S_SYSTEM)) / EST_IN_CHARS_PER_TOKEN for u in S)
    p = {"input": 2.00, "output": 10.00}
    usd = tin * p["input"] / 1e6 + len(S) * EST_OUT_TOKENS * p["output"] / 1e6
    return {"calls": len(S), "est_input_tokens": int(tin), "est_usd": round(usd, 4),
            "stop_usd": round(usd * STOP_FACTOR, 4), "max_packet_chars": max((len(u["_packet"]) for u in S), default=0)}


def cmd_plan(ns) -> None:
    S, w, meta = sample_for(ns.source)
    print(json.dumps({"source": ns.source, **meta, **estimate(S), "model": JUDGE_MODEL,
                      "prompt": s3.S_PROMPT_VERSION, "prompt_sha8": s3.prompt_sha256()[:8]}, indent=1))


def cmd_judge(ns) -> None:
    from judge_client import JudgeClient
    S, w, meta = sample_for(ns.source)
    est = estimate(S)
    print(json.dumps({"source": ns.source, **meta, **est}, indent=1), flush=True)
    if not ns.go:
        print("dry: pass --go to call")
        return
    jc = JudgeClient(cache_path=records_path(ns.source), concurrency=4, rpm=40, model=JUDGE_MODEL,
                     spend_cap_usd=est["stop_usd"], system=s3.S_SYSTEM, prompt_version=s3.S_PROMPT_VERSION,
                     parse=s3.parse_reply, max_tokens=s3.MAX_TOKENS_S, verbose=False)
    items = [("S", u["uid"], u["_packet"]) for u in S]
    recs = asyncio.run(jc.score_many(items))
    st = jc.stats()
    print(json.dumps({"outcomes": dict(Counter(r.get("outcome") for r in recs)),
                      "dollars_this_run": st.get("dollars"), "dollars_total": jc.total_spent(),
                      "abort": jc.abort}, indent=1, default=str))


def judge_flags(source: str, S: list[dict]) -> dict[str, bool | None]:
    """uid -> judge licensed (True/False) or None (refused / errored / missing), read from the
    records file by packet hash (the client's own key)."""
    p = records_path(source)
    by_key: dict[str, dict] = {}
    if p.exists():
        for ln in p.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                d = json.loads(ln)
                if d.get("outcome") in ("scored", "refused"):
                    by_key[d["cache_key"]] = d
    from judge_client import cache_key
    out: dict[str, bool | None] = {}
    for u in S:
        d = by_key.get(cache_key("S", u["uid"], u["_packet"]))
        out[u["uid"]] = None if d is None or d.get("outcome") != "scored" else (d.get("score") == 1)
    return out


# ── the table ──────────────────────────────────────────────────────────────────────────

def _rate(units: list[dict], key: str, invert: bool = True, weights: dict[str, float] | None = None) -> dict:
    """d = share NOT licensed under `key` (a bool field or a uid->bool map via weights' keys)."""
    rows = [(u["cluster"], int(not u[key]), (weights or {}).get(u["uid"], 1.0)) for u in units if u.get(key) is not None]
    return s3.cluster_rate(rows)


def _cell(r: dict) -> str:
    if r.get("d") is None:
        return "—"
    return f"{r['d']:.3f} [{r['lo']:.3f}, {r['hi']:.3f}] ({r['k']}/{r['n']})"


def cmd_table(ns) -> None:
    from judge_client import cache_key  # noqa: F401  (judge_flags imports it)
    P = json.loads((OUT / "s3-units-prefix.json").read_text(encoding="utf-8"))
    F = json.loads((FL / "fakelab-units.json").read_text(encoding="utf-8"))
    Sp, wp, _ = sample_for("prefix")
    Sf, wf, _ = sample_for("fakelab")
    jp, jf = judge_flags("prefix", Sp), judge_flags("fakelab", Sf)
    rows_out = []

    def row(source, generator, units_all, scope, judged, weights, jflags, extra=None):
        T = [u for u in units_all if u["has_task"]]
        J = []
        for u in T:
            if u["uid"] in jflags and jflags[u["uid"]] is not None:
                J.append({**u, "S": jflags[u["uid"]]})
        sampled_in_scope = [u for u in T if u["uid"] in judged]
        rec = {"source": source, "generator": generator, "scope": scope,
               "n_writes": len(T), "n_clusters": len({u["cluster"] for u in T}),
               "writes_with_no_task": len(units_all) - len(T),
               "d_L_path": _rate(T, "L_path"), "d_proxy": _rate(T, "proxy"),
               "judge_sampled": len(sampled_in_scope), "judge_scored": len(J),
               "judge_not_scored": len(sampled_in_scope) - len(J),
               "d_S": _rate(J, "S", weights=weights),
               "proxy_vs_judge": s3.agreement([(bool(u["proxy"]), bool(u["S"])) for u in J])}
        if extra:
            rec.update(extra(T, J))
        rows_out.append(rec)

    PU = P["units"]
    gp = "moonshotai/kimi-k2.6"
    row("prefix_rw_v2c", gp, [u for u in PU if u["path_class_doc"]], "class documents (item level defined)",
        set(wp), wp, jp, extra=lambda T, J: {"d_L_item": _rate(T, "L_item")})
    row("prefix_rw_v2c", gp, [u for u in PU if not u["path_class_doc"]], "other file writes", set(wp), wp, jp)
    row("prefix_rw_v2c", gp, PU, "all file writes (stratified judge sample, weighted)", set(wp), wp, jp)
    FU = F["units"]
    gf = ", ".join(sorted(F.get("generators") or {})) or "unknown"

    def fl_extra(T, J):
        return {"d_outside_declared_scope": _rate([{**u, "scope_ok": u["in_declared_scope"]} for u in T], "scope_ok")}
    for arm in ("honest_k1", "honest_k3"):
        row("fakelab_b8", gf, [u for u in FU if u["arm"] == arm], arm, set(wf), wf, jf, extra=fl_extra)
    row("fakelab_b8", gf, FU, "honest_k1 + honest_k3", set(wf), wf, jf, extra=fl_extra)

    out = {"version": "s3-table-v0", "rules": s3.VERSION, "rules_sha8": sha8(HERE / "stage3_s3_deviance.py"),
           "prompt_sha8": s3.prompt_sha256()[:8], "driver_sha8": sha8(Path(__file__)),
           "inputs": {"s3-units-prefix.json": sha8(OUT / "s3-units-prefix.json"),
                      "fakelab-units.json": sha8(FL / "fakelab-units.json"),
                      "records-prefix": sha8(records_path("prefix")) if records_path("prefix").exists() else None,
                      "records-fakelab": sha8(records_path("fakelab")) if records_path("fakelab").exists() else None},
           "prefix_beside": P["beside"], "prefix_reproduction": P["reproduction"], "fakelab_beside": F["beside"],
           "upstream": "not run: the released corpora's task text is in the transcripts config, not on disk",
           "rows": rows_out}
    wjson(OUT / "s3-table-v0.json", out)
    lines = ["| source | generator | scope | n writes | n sessions / sequences | d under L | d under S (judge sample) | d under the proxy | no task at all | proxy vs judge: agreement, kappa (n) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows_out:
        dl = _cell(r["d_L_path"]) + (f"; item level {_cell(r['d_L_item'])}" if "d_L_item" in r else "")
        a = r["proxy_vs_judge"]
        ag = "—" if not a["n"] else f"{a['agreement']:.3f}, {a['kappa']:.3f} ({a['n']})" if a["kappa"] is not None else f"{a['agreement']:.3f}, — ({a['n']})"
        lines.append(f"| {r['source']} | {r['generator']} | {r['scope']} | {r['n_writes']} | {r['n_clusters']} | {dl} | "
                     f"{_cell(r['d_S'])} | {_cell(r['d_proxy'])} | {r['writes_with_no_task']} | {ag} |")
    (OUT / "s3-table-v0.rows.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prefix")
    sub.add_parser("table")
    for name in ("plan", "judge"):
        sp = sub.add_parser(name)
        sp.add_argument("--source", required=True, choices=("prefix", "fakelab"))
        if name == "judge":
            sp.add_argument("--go", action="store_true")
    ns = ap.parse_args(argv)
    {"prefix": cmd_prefix, "plan": cmd_plan, "judge": cmd_judge, "table": cmd_table}[ns.cmd](ns)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
