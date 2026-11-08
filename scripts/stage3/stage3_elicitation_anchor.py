#!/usr/bin/env python3
"""Brief 30 Part 3: the human anchor of the elicitation study (protocol section 9; brief 24 E2; brief 30 notes 1 and 14).

For the one-document arm, once, after the last certification reading of the study: a blind sample of 20 items drawn with
`random.Random(20261211)` from the items that pass gate (i) and were read to a class: half (10) from the certified items and
half from the other items that pass (i) (quiet-but-illegible, mixed and part-derivable: "failed"), all certified items if fewer
than ten exist and the rest filled from the others. The sheet shows, in Block A, each item's whole change as the readers see it
(the reader's packet: the fixed question, the document before the change, every edit) and, in Block B, in a second order, one
part of each item (one edit, chosen by a seeded draw) in the same packet with the same question. Items carry opaque ids and no
class. Aravind answers in writing; his answers are scored by the same scorer against the same rubric (a later step).

The draw sequence (documented so the test can restate it): items are taken in sorted-uid order; `rng = Random(seed)`;
`pc = rng.sample(certified, n_c)`; `po = rng.sample(others, size - n_c)`; `order = pc + po`; `rng.shuffle(order)`;
`part[u] = rng.randrange(3)` for u in that order; `order_b = list(order)`; `rng.shuffle(order_b)`.

The sheet holds item text and the draw file holds the key (class by sheet id): both are written by this script and are never
opened by the session that wrote them, nor by the coordinator or the review session, nor by Aravind before he has finished.
The script prints counts and hashes only.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_anchor.py run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import secrets
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_legibility as lg  # noqa: E402

VERSION = "elicitation-anchor/v0"
PROJECT = HERE.parent.parent
PART3 = PROJECT / "work" / "stage3" / "elicitation" / "part3"
SEED = 20261211
SIZE = 20
CERTIFIED = "certified"
OTHERS = ("quiet_but_illegible", "mixed", "part_derivable")
ORDINALS = ("first", "second", "third")


def eligible(items: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """The items that pass gate (i) and were read to a class: certified, quiet-but-illegible, mixed, part-derivable."""
    return [i for i in items if i["class"] == CERTIFIED or i["class"] in OTHERS]


def draw(items: Sequence[Mapping[str, Any]], seed: int = SEED, size: int = SIZE) -> dict:
    el = eligible(items)
    cert = sorted(i["uid"] for i in el if i["class"] == CERTIFIED)
    other = sorted(i["uid"] for i in el if i["class"] in OTHERS)
    n_c = min(size // 2, len(cert))
    if size - n_c > len(other):
        raise ValueError("fewer eligible items than the sample size")
    rng = random.Random(seed)
    pc = rng.sample(cert, n_c)
    po = rng.sample(other, size - n_c)
    order = pc + po
    rng.shuffle(order)
    part = {u: rng.randrange(3) for u in order}
    order_b = list(order)
    rng.shuffle(order_b)
    return {"seed": seed, "size": size, "n_certified": n_c, "order": order, "order_b": order_b, "part": part}


def sheet_id(salt: str, uid: str) -> str:
    """An opaque id for the sheet: a hash of a random salt (kept only in the draw file) and the item's key, so that nobody who
    holds the records but not the draw file can compute it, and unrelated to the item's class."""
    return "H" + hashlib.sha256(f"{salt}|anchor|{uid}".encode("utf-8")).hexdigest()[:6]


def part_label(k: int) -> str:
    return f"the {ORDINALS[k]} edit"


def make_key(d: Mapping[str, Any], items_by_uid: Mapping[str, Mapping[str, Any]], salt: str) -> dict:
    ids = {u: sheet_id(salt, u) for u in d["order"]}
    if len(set(ids.values())) != len(ids):
        raise ValueError("sheet id collision")
    rows = {}
    for u in d["order"]:
        it = items_by_uid[u]
        rows[u] = {"sheet_id": ids[u], "writer": it["writer"], "round": it["round"], "item_id": it["item_id"], "class": it["class"],
                   "mechanism": it["mechanism"], "document": it["document"], "part_index": d["part"][u], "part_label": part_label(d["part"][u])}
    return {"sheet_ids": ids, "items": rows}


def render_sheet(d: Mapping[str, Any], items_by_uid: Mapping[str, Mapping[str, Any]], day0: Mapping[str, str], salt: str) -> str:
    """The blind sheet: no class, no writer, no mechanism, opaque ids. Block A the wholes, Block B one part of each."""
    L = ["# Reading sheet", "",
         "Each item below is one proposed change to one internal document of an engineering organisation. For each, answer the question in one or two sentences, in writing, "
         "in the space under it. Answer every item of Block A before you open Block B. You are shown nothing about where an item came from. "
         "Do not look anything up; answer from the change and the document as shown.", ""]
    L.append("## Block A: the change as a whole")
    L.append("")
    for n, u in enumerate(d["order"], 1):
        it = items_by_uid[u]
        L.append(f"### A{n}. Item {sheet_id(salt, u)}")
        L.append("")
        L.append("```")
        L.append(lg.reader_packet(it["document"], day0[it["document"]], it["statements"]).rstrip("\n"))
        L.append("```")
        L.append("")
        L.append("**Your answer:**")
        L.append("")
        L.append("")
    L.append("## Block B: one edit of each item")
    L.append("")
    L.append("Each item below is one edit taken from one of the items of Block A, shown by itself. The ids match Block A.")
    L.append("")
    for n, u in enumerate(d["order_b"], 1):
        it = items_by_uid[u]
        L.append(f"### B{n}. Item {sheet_id(salt, u)}")
        L.append("")
        L.append("```")
        L.append(lg.reader_packet(it["document"], day0[it["document"]], [it["statements"][d["part"][u]]]).rstrip("\n"))
        L.append("```")
        L.append("")
        L.append("**Your answer:**")
        L.append("")
        L.append("")
    return "\n".join(L)


def draw_counts(d: Mapping[str, Any], items_by_uid: Mapping[str, Mapping[str, Any]]) -> dict:
    cls = Counter(items_by_uid[u]["class"] for u in d["order"])
    wr = Counter(items_by_uid[u]["writer"] for u in d["order"])
    rd = Counter(f"{items_by_uid[u]['writer']} round {items_by_uid[u]['round']}" for u in d["order"])
    return {"by_class": dict(sorted(cls.items())), "by_writer": dict(sorted(wr.items())), "by_writer_round": dict(sorted(rd.items()))}


# ── the run ──────────────────────────────────────────────────────────────────────────────────────

def load_items(part3: Path) -> list[dict]:
    """Every valid item of every writer round that has a record: class, mechanism, document and the statements the readers see."""
    import stage3_elicitation_application as ap
    out = []
    for writer, rnd in ap.discover(part3):
        base = Path(part3) / f"round-{rnd}" / writer
        rec = json.loads((base / "round-record.json").read_text(encoding="utf-8"))["ids_by_class"]
        cls = {i: c for c, ids in rec.items() for i in ids}
        key = json.loads((base / "converted" / "key.json").read_text(encoding="utf-8"))["triples"]
        tri = json.loads((base / "converted" / "stripped-triples.json").read_text(encoding="utf-8"))
        tri = {t["triple_id"]: t for t in (tri if isinstance(tri, list) else tri["triples"])}
        for iid in sorted(key):
            t = tri[iid]
            out.append({"uid": f"{writer}:r{rnd}:{iid}", "writer": writer, "round": rnd, "item_id": iid, "class": cls[iid], "mechanism": key[iid]["mechanism"],
                        "document": t["document"], "statements": [{"op": s["op"], "anchor_or_region": s["anchor_or_region"], "text": s["text"]} for s in t["statements"]]})
    return out


def run(part3: Path, out_dir: Path) -> dict:
    import stage3_elicitation_e1e2 as e12
    P = Path(part3)
    items = load_items(P)
    by = {i["uid"]: i for i in items}
    d = draw(items, SEED, SIZE)
    day0 = e12.day0_texts()
    salt = secrets.token_hex(16)
    sheet = render_sheet(d, by, day0, salt)
    key = make_key(d, by, salt)
    check = json.loads((P / "application-check-round2-states-v0.json").read_text(encoding="utf-8"))
    placeable = {r["uid"]: not r["drop"] for r in check["items"]}
    for u, row in key["items"].items():
        row["placeable"] = placeable.get(u)          # None for an item the check did not cover (not certified, not illegible)
    el = eligible(items)
    pools = {"certified": sum(1 for i in el if i["class"] == CERTIFIED), **{c: sum(1 for i in el if i["class"] == c) for c in OTHERS}}
    pool_hash = hashlib.sha256("\n".join(sorted(i["uid"] for i in el)).encode("utf-8")).hexdigest()
    counts = draw_counts(d, by)
    covered = [u for u in d["order"] if placeable.get(u) is not None]
    placeable_counts = {"certified": sum(1 for u in covered if by[u]["class"] == CERTIFIED and placeable[u]),
                        "certified_not_placeable": sum(1 for u in covered if by[u]["class"] == CERTIFIED and not placeable[u]),
                        "quiet_but_illegible_placeable": sum(1 for u in covered if by[u]["class"] == "quiet_but_illegible" and placeable[u]),
                        "quiet_but_illegible_not_placeable": sum(1 for u in covered if by[u]["class"] == "quiet_but_illegible" and not placeable[u]),
                        "other_classes_not_covered_by_the_check": sum(1 for u in d["order"] if placeable.get(u) is None)}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pd, ps = out / "human-anchor-draw-v0.json", out / "human-anchor-sheet-v0.md"
    pd.write_text(json.dumps({"version": VERSION, "written": datetime.now().astimezone().isoformat(timespec="seconds"), "seed": SEED, "size": SIZE,
                              "id_salt": salt, "pool_sha256": pool_hash, "pools": pools, **d, "key": key}, indent=1) + "\n", encoding="utf-8")
    ps.write_text(sheet, encoding="utf-8")
    h = {"draw": hashlib.sha256(pd.read_bytes()).hexdigest(), "sheet": hashlib.sha256(ps.read_bytes()).hexdigest()}
    return {"counts": counts, "pools": pools, "pool_sha256": pool_hash, "placeable_counts": placeable_counts, "n_items_in_sheet": len(d["order"]),
            "block_a": len(d["order"]), "block_b": len(d["order_b"]), "files": h, "size_bytes": {"draw": pd.stat().st_size, "sheet": ps.stat().st_size}}


def main(argv: list[str] | None = None) -> int:
    ap_ = argparse.ArgumentParser(description="brief 30 Part 3: the human anchor draw and the blind sheet")
    ap_.add_argument("mode", choices=("run",))
    ap_.add_argument("--part3", default=str(PART3))
    ap_.add_argument("--out-dir", default=str(PART3))
    ns = ap_.parse_args(argv)
    out = Path(ns.out_dir)
    if (out / "human-anchor-draw-v0.json").exists():
        raise SystemExit("refusing: the anchor has been drawn once (protocol section 9); it is never redrawn")
    res = run(Path(ns.part3), out)
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
