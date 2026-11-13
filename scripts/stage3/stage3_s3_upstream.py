#!/usr/bin/env python3
"""Line S3 (roadmap v5): the released MOLE corpora (forgelab/mole, 8 splits) under the frozen rules
in stage3_s3_deviance.py (unchanged). Streams the audit and transcripts parquet files (read as data
only; paths are arguments-free constants under work/upstream-data/) and writes counts, ids, flags
and hashes only. No task, write or transcript text is printed or stored.

HONEST ONLY: a write is kept when its session's transcript has session_mode == "benign" and no
insider persona, AND its account-day (account, ts[:10]) carries no row in the split's label file.
Everything else is dropped and counted beside.

ORDER: writes are ordered by (ts[:10], real_ts, file row). A write is a no-op (not a unit) when its
content equals the last content written to the same resource earlier in the split (ownCloud path;
GitLab project, branch and path); the seeded state before the first write is unknown.

  scan   per split: units, L at path level, the proxy, cluster aggregates, the seeded judge sample
         -> work/stage3/v5/S3/upstream/s3-upstream-<split>.json
  plan   the judge call count and estimate per split (builds packets in memory, no call)
  judge  the judge calls for one split (--go; stops at 1.5 x the printed estimate)

    work/mole-fork/.venv/bin/python -I work/checks/stage3_s3_upstream.py scan --split gpt53_single_day
"""
from __future__ import annotations

import argparse
import asyncio
import gc
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pyarrow as pa  # noqa: E402
import pyarrow.compute as pc  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

import stage3_s3_deviance as s3  # noqa: E402
import stage3_write_yield as wy  # noqa: E402

WORK = HERE.parent
UP = WORK / "upstream-data"
OUT = WORK / "stage3" / "v5" / "S3" / "upstream"
SPLITS = tuple(f"{m}_{k}" for m in ("gpt53", "kimi_k26", "deepseek_v4_flash", "qwen36_27b")
               for k in ("single_day", "multiday"))
WRITE_ACTIONS = sorted({a for _, a in s3.FILE_WRITE_ACTIONS})
DISK_STOP = 3.5 * 2 ** 30
JUDGE_MODEL = "anthropic.claude-sonnet-5"
EST_IN_CHARS_PER_TOKEN = 3.5
EST_OUT_TOKENS = 15
STOP_FACTOR = 1.5


def disk_ok() -> None:
    free = shutil.disk_usage(str(WORK)).free
    if free < DISK_STOP:
        raise SystemExit(f"STOP: host free disk {free / 2 ** 30:.2f} GiB < 3.5 GiB")


def h(s: str | None) -> str | None:
    return None if s is None else hashlib.sha256(s.encode("utf-8", "surrogatepass")).hexdigest()


def sessions(split: str) -> dict[str, dict]:
    """task_id -> {benign, account, fed}; one transcript file and one row group at a time."""
    out: dict[str, dict] = {}
    for p in sorted((UP / "transcripts" / "data" / "transcripts" / split).glob("*.parquet")):
        disk_ok()
        f = pq.ParquetFile(p)
        for t in f.iter_batches(batch_size=50, use_threads=False,
                                columns=["task_id", "account", "session_mode", "has_insider_persona", "messages"]):
            for row in t.to_pylist():
                msgs = [{"role": m.get("role"), "content": m.get("content")} for m in (row.get("messages") or [])]
                out[str(row.get("task_id") or "")] = {
                    "benign": row.get("session_mode") == "benign" and not row.get("has_insider_persona"),
                    "account": row.get("account"), "fed": wy.fed_items({"messages": msgs})}
            del t
            gc.collect()
    return out


def labelled_account_days(split: str) -> set[tuple[str, str]]:
    t = pq.read_table(UP / "data" / "labels" / split / "0000.parquet", columns=["account", "date"])
    return {(str(a), str(d)[:10]) for a, d in zip(t["account"].to_pylist(), t["date"].to_pylist())}


def write_rows(split: str, keep_content_for: set | None = None):
    """Successful file-content writes in file order: (row, ts, real_ts, account, task_id, service,
    action, path, project, resource key, content hash, content or None)."""
    f = pq.ParquetFile(UP / "data" / "audit" / split / "0000.parquet")
    cols = ["ts", "real_ts", "account", "task_id", "service", "action", "args", "exit_code"]
    # the matching rows are numbered in file order (iter_batches is ordered)
    n = 0
    acts = pa.array(WRITE_ACTIONS)
    for b in f.iter_batches(columns=cols, batch_size=2000, use_threads=False):
        m = pc.and_(pc.is_in(b.column("action"), value_set=acts), pc.equal(b.column("exit_code"), 0))
        b = b.filter(m)
        for r in b.to_pylist():
            n += 1
            try:
                args = json.loads(r["args"]) if isinstance(r["args"], str) else (r["args"] or {})
            except json.JSONDecodeError:
                args = {}
            tg = s3.write_target(r["service"], r["action"], args)
            if tg is None:
                continue
            path, project = tg
            key = (r["service"], project or "", str(args.get("branch") or "") if r["service"] == "gitlab" else "", path)
            content = args.get("content")
            if not isinstance(content, str):
                content = None
            yield (n, str(r["ts"] or ""), float(r["real_ts"] or 0.0), str(r["account"] or ""), str(r["task_id"] or ""),
                   r["service"], r["action"], path, project, key, h(content),
                   content if (keep_content_for is not None and key in keep_content_for) else None)
        disk_ok()


def ordered(rows):
    return sorted(rows, key=lambda x: (x[1][:10], x[2], x[0]))


def cmd_scan(ns) -> None:
    split = ns.split
    disk_ok()
    S = sessions(split)
    lab = labelled_account_days(split)
    rows = ordered(list(write_rows(split)))
    last: dict[tuple, str | None] = {}
    beside = Counter()
    clusters: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    units = []
    for (n, ts, rts, acct, tid, svc, act, path, project, key, ch, _) in rows:
        before = last.get(key)
        last[key] = ch
        beside["successful_file_writes"] += 1
        sess = S.get(tid)
        if (acct, ts[:10]) in lab:
            beside["dropped_labelled_account_day"] += 1
            continue
        if sess is not None and not sess["benign"]:
            beside["dropped_non_benign_session"] += 1
            continue
        if not s3.is_changing(act, {}, before, ch):
            beside["noop_writes"] += 1
            continue
        if sess is None:
            beside["no_transcript_for_task_id"] += 1
            beside["writes_with_no_task"] += 1
            continue
        if not sess["fed"]:
            beside["writes_with_no_task"] += 1
            continue
        L = s3.literal_path_licensed(path, project, sess["fed"])
        P = s3.contained(path, project, sess["fed"])
        c = clusters[tid]
        c[0] += 1
        c[1] += int(not L)
        c[2] += int(not P)
        units.append((f"{split}:{n}", tid, L, P, svc))
    beside["sessions"] = len(S)
    beside["benign_sessions"] = sum(1 for s in S.values() if s["benign"])
    beside["benign_sessions_with_no_fed_item"] = sum(1 for s in S.values() if s["benign"] and not s["fed"])
    beside["label_rows"] = len(lab)
    by_svc = Counter(u[4] for u in units)
    samp, w = s3.draw_sample([u[0] for u in units], s3.SAMPLE_CAP, s3.SEED)
    sset = set(samp)
    sample = [{"uid": u[0], "cluster": u[1], "L_path": u[2], "proxy": u[3], "service": u[4]} for u in units if u[0] in sset]
    out = {"split": split, "rules": s3.VERSION, "rules_sha8": hashlib.sha256((HERE / "stage3_s3_deviance.py").read_bytes()).hexdigest()[:8],
           "driver_sha8": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:8],
           "n_units": len(units), "units_by_service": dict(by_svc), "beside": dict(beside),
           "clusters": [[k, *v] for k, v in sorted(clusters.items())],
           "sample_weight": (w[samp[0]] if samp else None), "sample": sample,
           "L_unlicensed": sum(1 for u in units if not u[2]), "proxy_unlicensed": sum(1 for u in units if not u[3])}
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"s3-upstream-{split}.json"
    p.write_text(json.dumps(out, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("split", "n_units", "units_by_service", "beside", "L_unlicensed", "proxy_unlicensed")}),
          f"clusters={len(clusters)} sample={len(sample)} file_MB={p.stat().st_size / 1e6:.1f}", flush=True)


def packets(split: str) -> list[dict]:
    """The sampled units with packets built in memory (second streaming pass over the audit)."""
    rec = json.loads((OUT / f"s3-upstream-{split}.json").read_text(encoding="utf-8"))
    want = {u["uid"]: u for u in rec["sample"]}
    # first find the sampled rows' resource keys, then stream again keeping those resources' content
    keys: dict[str, tuple] = {}
    for r in write_rows(split):
        uid = f"{split}:{r[0]}"
        if uid in want:
            keys[uid] = r[9]
    kset = set(keys.values())
    seq: dict[tuple, list] = defaultdict(list)
    for r in write_rows(split, keep_content_for=kset):
        if r[9] in kset:
            seq[r[9]].append(r)
    S = sessions(split)
    out = []
    for k, rows in seq.items():
        rows = ordered(rows)
        prev = None
        for r in rows:
            uid = f"{split}:{r[0]}"
            if uid in want:
                before, after = prev, r[11]
                if before is None:
                    rem, add = [], (after or "").splitlines()
                else:
                    rem, add = s3.changed_lines(before, after)
                desc = s3.render_write(r[5], r[6], r[7], r[8], rem, add)
                out.append({"uid": uid, "cluster": want[uid]["cluster"],
                            "_packet": s3.judge_packet(S[r[4]]["fed"], desc)})
            prev = r[11]
    del S
    gc.collect()
    out.sort(key=lambda x: x["uid"])
    return out


def estimate(P: list[dict]) -> dict:
    tin = sum((len(u["_packet"]) + len(s3.S_SYSTEM)) / EST_IN_CHARS_PER_TOKEN for u in P)
    usd = tin * 2.00 / 1e6 + len(P) * EST_OUT_TOKENS * 10.00 / 1e6
    return {"calls": len(P), "est_input_tokens": int(tin), "est_usd": round(usd, 4),
            "stop_usd": round(usd * STOP_FACTOR, 4), "max_packet_chars": max((len(u["_packet"]) for u in P), default=0)}


def records_path(split: str) -> Path:
    return OUT / f"s3-judge-records-{split}.jsonl"


def cmd_plan(ns) -> None:
    P = packets(ns.split)
    print(json.dumps({"split": ns.split, **estimate(P)}), flush=True)


def cmd_judge(ns) -> None:
    from judge_client import JudgeClient
    P = packets(ns.split)
    est = estimate(P)
    print(json.dumps({"split": ns.split, **est}), flush=True)
    if not ns.go:
        return
    jc = JudgeClient(cache_path=records_path(ns.split), concurrency=6, rpm=60, model=JUDGE_MODEL,
                     spend_cap_usd=est["stop_usd"], system=s3.S_SYSTEM, prompt_version=s3.S_PROMPT_VERSION,
                     parse=s3.parse_reply, max_tokens=s3.MAX_TOKENS_S, verbose=False)
    recs = asyncio.run(jc.score_many([("S", u["uid"], u["_packet"]) for u in P]))
    print(json.dumps({"split": ns.split, "outcomes": dict(Counter(r.get("outcome") for r in recs)),
                      "dollars_this_run": jc.stats().get("dollars"), "dollars_total": jc.total_spent(),
                      "abort": jc.abort}), flush=True)


def bank(split: str) -> dict:
    """The fed task texts, folded to their bank variant (stage3_write_yield.variant_key) and hashed:
    distinct variants and how often each was fed (hashes only)."""
    c = Counter()
    for v in sessions(split).values():
        if v["benign"]:
            for t in v["fed"]:
                c[hashlib.sha256(wy.variant_key(t).encode()).hexdigest()[:16]] += 1
    return dict(c)


def cmd_bank(ns) -> None:
    out = {}
    for sp in SPLITS:
        disk_ok()
        out[sp] = bank(sp)
        gc.collect()
        print(sp, len(out[sp]), sum(out[sp].values()), flush=True)
    sets = {k: set(v) for k, v in out.items()}
    allv = set().union(*sets.values())
    shared = set.intersection(*sets.values())
    gens = sorted({sp.rsplit("_", 2)[0] if sp.endswith("single_day") else sp[: -len("_multiday")] for sp in SPLITS})
    rec = {"distinct_variants_per_split": {k: len(v) for k, v in sets.items()},
           "fed_items_per_split": {k: sum(v.values()) for k, v in out.items()},
           "distinct_variants_all": len(allv), "variants_in_all_eight": len(shared),
           "share_of_fed_items_on_variants_in_all_eight": {k: sum(n for x, n in v.items() if x in shared) / max(1, sum(v.values()))
                                                           for k, v in out.items()},
           "pairwise_jaccard": {f"{a}|{b}": len(sets[a] & sets[b]) / max(1, len(sets[a] | sets[b]))
                                for i, a in enumerate(SPLITS) for b in SPLITS[i + 1:]}}
    (OUT / "s3-upstream-bank-overlap.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: rec[k] for k in ("distinct_variants_per_split", "distinct_variants_all", "variants_in_all_eight",
                                          "share_of_fed_items_on_variants_in_all_eight")}, indent=1))


def _judge_map(split: str) -> dict[str, bool | None]:
    p = records_path(split)
    out: dict[str, bool | None] = {}
    if p.exists():
        for ln in p.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                d = json.loads(ln)
                if d.get("outcome") == "scored":
                    out[d["label"]] = d.get("score") == 1
                elif d.get("outcome") == "refused":
                    out.setdefault(d["label"], None)
    return out


def _rows_from_clusters(clusters, idx):
    rows = []
    for c in clusters:
        n, k = c[1], c[idx]
        rows += [(c[0], 1, 1.0)] * k + [(c[0], 0, 1.0)] * (n - k)
    return rows


def _cell(r: dict) -> str:
    if r.get("d") is None:
        return "—"
    return f"{r['d']:.3f} [{r['lo']:.3f}, {r['hi']:.3f}] ({r['k']}/{r['n']})"


def cmd_table(ns) -> None:
    S3D = WORK / "stage3" / "v5" / "S3"
    v0 = json.loads((S3D / "s3-table-v0.json").read_text(encoding="utf-8"))
    rows = []
    groups: dict[str, list[str]] = defaultdict(list)
    for sp in SPLITS:
        rec = json.loads((OUT / f"s3-upstream-{sp}.json").read_text(encoding="utf-8"))
        gen = sp[: -len("_single_day")] if sp.endswith("_single_day") else sp[: -len("_multiday")]
        groups[gen].append(sp)
        jm = _judge_map(sp)
        J = [u for u in rec["sample"] if jm.get(u["uid"]) is not None]
        w = rec["sample_weight"] or 1.0
        rows.append({"source": "MOLE released", "generator": gen, "scope": sp, "n_writes": rec["n_units"],
                     "n_clusters": len(rec["clusters"]), "writes_with_no_task": rec["beside"].get("writes_with_no_task", 0),
                     "beside": rec["beside"], "units_by_service": rec["units_by_service"],
                     "d_L_path": s3.cluster_rate(_rows_from_clusters(rec["clusters"], 2)),
                     "d_proxy": s3.cluster_rate(_rows_from_clusters(rec["clusters"], 3)),
                     "judge_sampled": len(rec["sample"]), "judge_scored": len(J),
                     "judge_not_scored": len(rec["sample"]) - len(J),
                     "d_S": s3.cluster_rate([(u["cluster"], int(not jm[u["uid"]]), w) for u in J]),
                     "proxy_vs_judge": s3.agreement([(bool(u["proxy"]), bool(jm[u["uid"]])) for u in J]),
                     "_J": [(u["cluster"], int(not jm[u["uid"]]), w) for u in J],
                     "_pairs": [(bool(u["proxy"]), bool(jm[u["uid"]])) for u in J],
                     "_cl": rec["clusters"]})
        print(sp, "done", flush=True)
    pooled = []
    for gen, sps in groups.items():
        R = [r for r in rows if r["scope"] in sps]
        cl = [c for r in R for c in r["_cl"]]
        pooled.append({"source": "MOLE released", "generator": gen, "scope": " + ".join(sps) + " (pooled; judge weighted)",
                       "n_writes": sum(r["n_writes"] for r in R), "n_clusters": sum(r["n_clusters"] for r in R),
                       "writes_with_no_task": sum(r["writes_with_no_task"] for r in R),
                       "d_L_path": s3.cluster_rate(_rows_from_clusters(cl, 2)), "d_proxy": s3.cluster_rate(_rows_from_clusters(cl, 3)),
                       "judge_sampled": sum(r["judge_sampled"] for r in R), "judge_scored": sum(r["judge_scored"] for r in R),
                       "judge_not_scored": sum(r["judge_not_scored"] for r in R),
                       "d_S": s3.cluster_rate([x for r in R for x in r["_J"]]),
                       "proxy_vs_judge": s3.agreement([x for r in R for x in r["_pairs"]])})
    for r in rows:
        for k in ("_J", "_pairs", "_cl"):
            r.pop(k)
    mole_rows = rows + pooled
    prefix_rows = [r for r in v0["rows"] if r["source"] == "prefix_rw_v2c"]
    fakelab_rows = [r for r in v0["rows"] if r["source"] != "prefix_rw_v2c"]
    bank_p = OUT / "s3-upstream-bank-overlap.json"
    meta = {"version": "s3-table-v1", "rules": s3.VERSION,
            "rules_sha8": hashlib.sha256((HERE / "stage3_s3_deviance.py").read_bytes()).hexdigest()[:8],
            "prompt_sha8": s3.prompt_sha256()[:8], "driver_sha8": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:8],
            "v0_rows_from": "s3-table-v0.json", "bank_overlap": json.loads(bank_p.read_text()) if bank_p.exists() else None,
            "inputs": {f"s3-upstream-{sp}.json": hashlib.sha256((OUT / f"s3-upstream-{sp}.json").read_bytes()).hexdigest()[:8] for sp in SPLITS}
            | {f"s3-judge-records-{sp}.jsonl": (hashlib.sha256(records_path(sp).read_bytes()).hexdigest()[:8] if records_path(sp).exists() else None) for sp in SPLITS}}
    hdr = ["| source | generator | scope | n writes | n sessions / sequences | d under L | d under S (judge sample) | d under the proxy | no task at all | proxy vs judge: agreement, kappa (n) |",
           "|---|---|---|---|---|---|---|---|---|---|"]

    def line(r):
        dl = _cell(r["d_L_path"]) + (f"; item level {_cell(r['d_L_item'])}" if "d_L_item" in r else "")
        a = r["proxy_vs_judge"]
        ag = "—" if not a["n"] else (f"{a['agreement']:.3f}, {a['kappa']:.3f} ({a['n']})" if a["kappa"] is not None else f"{a['agreement']:.3f}, — ({a['n']})")
        return (f"| {r['source']} | {r['generator']} | {r['scope']} | {r['n_writes']} | {r['n_clusters']} | {dl} | "
                f"{_cell(r['d_S'])} | {_cell(r['d_proxy'])} | {r['writes_with_no_task']} | {ag} |")
    full = {**meta, "rows": prefix_rows + fakelab_rows + mole_rows}
    public = {**meta, "rows": prefix_rows + mole_rows, "note": "FakeLab rows omitted (not publishable); they are in the project copy only"}
    (S3D / "s3-table-v1.json").write_text(json.dumps(full, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (S3D / "s3-table-v1-public.json").write_text(json.dumps(public, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (S3D / "s3-table-v1.rows.md").write_text("\n".join(hdr + [line(r) for r in full["rows"]]) + "\n", encoding="utf-8")
    (S3D / "s3-table-v1-public.rows.md").write_text("\n".join(hdr + [line(r) for r in public["rows"]]) + "\n", encoding="utf-8")
    print("\n".join(hdr + [line(r) for r in mole_rows]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bank")
    sub.add_parser("table")
    for name in ("scan", "plan", "judge"):
        sp = sub.add_parser(name)
        sp.add_argument("--split", required=True, choices=SPLITS)
        if name == "judge":
            sp.add_argument("--go", action="store_true")
    ns = ap.parse_args(argv)
    {"scan": cmd_scan, "plan": cmd_plan, "judge": cmd_judge, "bank": cmd_bank, "table": cmd_table}[ns.cmd](ns)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
