#!/usr/bin/env python3
"""Brief 30 Part 3: the figures of a writer round's record. Blue side; pure; counts and aggregates only.

`rater_proxy` and `reader_proxy` are protocol section 1's proxy agreement, reported every writer round per instrument:
development against certification (a gap is read as Goodhart on the development instrument and named).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_legibility as lg  # noqa: E402

VERSION = "elicitation-round/v0"
WITHIN_TARGET_MAX = 60.0


def rater_proxy(dev: Mapping[str, float], cert_mean: Mapping[str, float]) -> dict:
    """The development rater's statement ratings against the certification sessions' means, over the statements both rated."""
    ids = sorted(set(dev) & set(cert_mean))
    a = [float(dev[i]) for i in ids]
    b = [float(cert_mean[i]) for i in ids]
    agree = [(x <= WITHIN_TARGET_MAX) == (y <= WITHIN_TARGET_MAX) for x, y in zip(a, b)]
    return {"n": len(ids), "spearman": lg.spearman(a, b) if len(ids) >= 3 else None,
            "within_target_agreement": (sum(agree) / len(agree)) if agree else None}


def reader_proxy(dev: Mapping[str, Mapping[str, Any]], cert: Mapping[str, Mapping[str, Any]], fams: Sequence[str]) -> dict:
    """Per reader, over the items certification read: agreement of the development sample with certification's two on whole
    credited (D_whole above 0 on the sample against on any of the two) and on part credited (D_part above 0). A missing
    value is skipped and counted out, never agreement."""
    out: dict[str, dict] = {}
    for f in fams:
        ids = sorted(i for i in dev if i in cert and f in cert[i])
        wh, pt = [], []
        for i in ids:
            d, c = dev[i][f], cert[i][f]
            if d["D_whole"][0] is not None and all(x is not None for x in c["D_whole"]):
                wh.append((d["D_whole"][0] > 0) == any(x > 0 for x in c["D_whole"]))
            if d["D_part"][0] is not None and all(x is not None for x in c["D_part"]):
                pt.append((d["D_part"][0] > 0) == any(x > 0 for x in c["D_part"]))
        out[f] = {"n": len(ids), "whole_n": len(wh), "part_n": len(pt),
                  "whole_agreement": (sum(wh) / len(wh)) if wh else None, "part_agreement": (sum(pt) / len(pt)) if pt else None}
    return out


# ── the record builder (data plumbing over the tested pieces; counts and aggregates only) ──────────────────────

def _read_json(p: Path) -> Any:
    import json
    return json.loads(Path(p).read_text(encoding="utf-8"))


def stream_cost(path: Path) -> float | None:
    """total_cost_usd of a Claude Code stream's result event (None when the stream has none)."""
    import json
    for line in reversed(Path(path).read_text(encoding="utf-8", errors="replace").splitlines()):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("type") == "result":
            return row.get("total_cost_usd")
    return None


def build_record(writer: str, round_no: int, part3: Path) -> dict:
    """The writer round's record from the files the steps wrote under part3/."""
    import stage3_elicitation_classes as cl
    import stage3_elicitation_matching as mt
    import stage3_elicitation_reads as rd
    P = Path(part3)
    conv = P / f"round-{round_no}" / writer / "converted"
    key = _read_json(conv / "key.json")
    report = _read_json(conv / "report.json")
    O_dev = P / "raters" / f"{writer}-r{round_no}-dev"
    O_cert = P / "raters" / f"{writer}-r{round_no}-cert"
    gate = _read_json(O_cert / "gate-i.json")
    fams = rd.reader_names(writer)
    second, rule = cl.second_reader(writer)
    cert = _read_json(rd.phase_dir(rd.READS_ROOT, writer, round_no, "cert") / "collected.json")
    dev = _read_json(rd.phase_dir(rd.READS_ROOT, writer, round_no, "dev") / "collected.json")
    items = sorted(key["triples"])
    inputs = []
    for i in items:
        inputs.append({"id": i, "gate_i": bool(gate["gate_i"][i]),
                       "readers": {f: {"D_whole": cert[i][f]["D_whole"], "D_part": cert[i][f]["D_part"]} for f in fams} if i in cert else {}})
    classes = {it["id"]: cl.item_class(it, fams[0], fams[1], rule, 2) for it in inputs}
    rows = [{"id": i, "mechanism": key["triples"][i]["mechanism"], "document": key["triples"][i]["document"],
             "composition": gate["composition"][i], "class": classes[i]} for i in items]
    written = int(report["funnel"]["written"])
    valid = int(report["funnel"]["valid"])
    funnel = cl.funnel(written, valid, [r["class"] for r in rows])
    by_mech = cl.funnel_by([{"mechanism": r["mechanism"], "class": r["class"]} for r in rows], "mechanism")
    comp = sorted(r["composition"] for r in rows)
    match = mt.match([{"writer": writer, "document": r["document"], "composition": r["composition"], "class": r["class"]} for r in rows], mt.BAND_WIDTH)
    dev_scores = _read_json(O_dev / "collected" / "ratings-dev-statements-p1.json")
    skey = _read_json(O_dev / "statement-key.json")
    ckey = _read_json(O_cert / "statement-key.json")
    # the development and certification statement ids differ (different salts): compare by (item, writer index)
    dev_by_pos = {(k["item_id"], k["writer_index"]): float(dev_scores[sid]) for sid, k in skey.items()}
    cert_by_pos = {(k["item_id"], k["writer_index"]): gate["statement_means"][k["item_id"]][k["writer_index"]] for sid, k in ckey.items()}
    rater = rater_proxy({str(p): v for p, v in dev_by_pos.items()}, {str(p): v for p, v in cert_by_pos.items()})
    reader = reader_proxy(dev, cert, fams)
    return {"version": VERSION, "writer": writer, "round": round_no, "second_reader": {"name": second, "rule": rule},
            "funnel": funnel, "by_mechanism": by_mech, "matching": {k: v for k, v in match.items()},
            "composition": {"n": len(comp), "min": comp[0], "median": comp[len(comp) // 2], "max": comp[-1]},
            "proxy": {"rater": rater, "readers": reader},
            "ids_by_class": {c: sorted(r["id"] for r in rows if r["class"] == c) for c in cl.CLASSES}}
