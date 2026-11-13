#!/usr/bin/env python3
"""Line P0, Part 2: composed-view (O_diff) packets on the states the followers saw. Written by the blue side; RUN BY THE
RED SIDE ONLY, because it reads the frozen planted documents. It prints counts and hashes, never a packet.

For each scorable payload of the core manifest (`work/stage3/red/ft/cells-manifest.json`, 56): its governing
application (`application_id`, "<payload>@v<set>.<rank><arm>"), and from that application's plant record (the plants
manifests, read for `document` and `pre_window_boundary` only) the document and the From boundary the recorded unit used.
* From: the honest document at that boundary, replayed as the recorded scorers replayed it (`stage3_t1_score.build_items`:
  writes with a timestamp at or before the boundary, file order; the day-0 seed for "day0").
* To: the frozen planted document under `<docs-root>/<payload_id>/planted/` (the file whose world path, in that folder's
  `history.json` `paths`, is the application's document), stamped with that history's `as_of`.
* The packet: `stage3_views.o_packet("O_diff", path, unified_diff(From, To, path), From label, as_of)`, as the sealed
  composed view receives it.

Outputs (never overwritten): the packets file, one JSON line per payload (payload_id, key, regime,
reader_state_identical, from, to, packet, packet_sha256, packet_chars, text_chars, truncated); a text-free index of the
same without the packet. It opens the manifest, the two plants manifests, the corpus and the frozen planted documents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_views as sv  # noqa: E402
from mole.oracles import document as doc  # noqa: E402

APP_ID = re.compile(r"^(?P<pid>.+)@v(?P<set>\d+)\.(?P<rank>\d+)(?P<arm>lone|k2|k3)$")
INDEX_FIELDS = ("payload_id", "key", "regime", "reader_state_identical", "from", "to", "packet_sha256", "packet_chars",
                "text_chars", "truncated")


def app_key(application_id: str) -> str:
    m = APP_ID.match(str(application_id))
    if not m:
        raise SystemExit(f"application id {application_id!r} is not in the manifest's form")
    return f"t1v{m.group('set')}:{m.group('pid')}:{m.group('arm')}"


def _frozen_file(folder: Path, world_path: str) -> tuple[str, str]:
    hist = json.loads((folder / "history.json").read_text(encoding="utf-8"))
    files = [f for f, p in (hist.get("paths") or {}).items() if p == world_path]
    if len(files) != 1 or not (folder / files[0]).is_file():
        raise SystemExit(f"{folder}: no single frozen file for the application's document")
    return (folder / files[0]).read_text(encoding="utf-8"), str(hist.get("as_of"))


def build_packets(manifest: Sequence[Mapping], plants: Mapping[str, Mapping], docs_root: Path,
                  honest_state: Callable[[str, str], str], *, days: Sequence[str]) -> list[dict]:
    recs = []
    for m in manifest:
        if not m.get("scorable", True):
            continue
        key = app_key(m["application_id"])
        pl = plants.get(key)
        if pl is None:
            raise SystemExit(f"{m['payload_id']}: no plant record for its governing application")
        path, bound = pl["document"], pl["pre_window_boundary"]
        to_text, as_of = _frozen_file(Path(docs_root) / m["payload_id"] / "planted", path)
        before = honest_state(path, "day0" if bound == "day0" else bound)
        frm = f"start of {sorted(days)[0]} (day-0 state)" if bound == "day0" else f"end of {bound}"
        text = doc.unified_diff(before, to_text, path)
        if not text:
            raise SystemExit(f"{m['payload_id']}: the frozen document equals its From state")
        pk, trunc = sv.o_packet("O_diff", path, text, frm, as_of)
        recs.append({"payload_id": m["payload_id"], "key": key, "regime": m.get("regime"),
                     "reader_state_identical": m.get("reader_state_identical"), "from": frm, "to": as_of, "packet": pk,
                     "packet_sha256": hashlib.sha256(pk.encode("utf-8")).hexdigest(), "packet_chars": len(pk),
                     "text_chars": len(text), "truncated": bool(trunc)})
    return recs


def write_outputs(recs: Sequence[Mapping], packets_out: Path, index_out: Path) -> dict:
    for p in (packets_out, index_out):
        if Path(p).exists():
            raise SystemExit(f"{p} exists; never overwritten")
    Path(packets_out).parent.mkdir(parents=True, exist_ok=True)
    with Path(packets_out).open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {"n_payloads": len(recs), "by_regime": dict(sorted(Counter(r["regime"] for r in recs).items())),
               "reader_state_identical": dict(Counter(str(r["reader_state_identical"]) for r in recs)),
               "n_truncated": sum(1 for r in recs if r["truncated"]),
               "packets_file": str(packets_out), "packets_file_sha256": hashlib.sha256(Path(packets_out).read_bytes()).hexdigest()}
    Path(index_out).parent.mkdir(parents=True, exist_ok=True)
    Path(index_out).write_text(json.dumps({**summary, "applications": [{k: r[k] for k in INDEX_FIELDS} for r in recs]}, indent=1) + "\n",
                               encoding="utf-8")
    summary["index_file_sha256"] = hashlib.sha256(Path(index_out).read_bytes()).hexdigest()
    return summary


def print_summary(summary: Mapping) -> None:
    print(json.dumps(summary, indent=1))


def main(argv: list[str] | None = None) -> int:
    import stage3_ft_slots as sl
    ap = argparse.ArgumentParser(description="Render P0 frozen-state packets (red side runs this; counts and hashes only).")
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--docs-root", type=Path, required=True)
    ap.add_argument("--plants-v2", type=Path, required=True)
    ap.add_argument("--plants-v3", type=Path, required=True)
    ap.add_argument("--packets-out", type=Path, required=True)
    ap.add_argument("--index-out", type=Path, required=True)
    ap.add_argument("--corpus", type=Path, default=Path(sl.CORPUS))
    a = ap.parse_args(argv)
    for p in (a.packets_out, a.index_out):
        if p.exists():
            raise SystemExit(f"{p} exists; never overwritten")
    d = json.loads(a.manifest.read_text(encoding="utf-8"))
    manifest = d if isinstance(d, list) else d.get("cells") or d.get("payloads")
    plants: dict[str, dict] = {}
    for planting, pth in (("t1v2", a.plants_v2), ("t1v3", a.plants_v3)):
        for rec in json.loads(pth.read_text(encoding="utf-8"))["plants"]:
            plants[f"{planting}:{rec['payload_id']}:{rec['arm']}"] = {"document": rec["document"], "pre_window_boundary": rec["pre_window_boundary"]}
    rows = sv.read_jsonl(a.corpus)
    base = sv.seed_base()

    def honest_state(path: str, bound: str) -> str:
        if bound == "day0":
            return base[("owncloud", path)]
        st = doc.content_at(rows, doc.DocRef("owncloud", path), bound, base=base)
        return "" if doc.is_unknown(st) or st is None else st
    recs = build_packets(manifest, plants, a.docs_root, honest_state, days=sv.corpus_days(rows))
    summary = write_outputs(recs, a.packets_out, a.index_out)
    summary["inputs_sha256"] = {"manifest": sv.file_sha256(a.manifest), "plants_v2": sv.file_sha256(a.plants_v2),
                                "plants_v3": sv.file_sha256(a.plants_v3), "corpus": sv.file_sha256(a.corpus),
                                "render_module": sv.file_sha256(Path(__file__).resolve())}
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
