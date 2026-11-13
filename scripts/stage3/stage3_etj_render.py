#!/usr/bin/env python3
"""Line ETJ: render the composed-view (O_diff) packets of the 184 in-scope planted applications, by the recorded
scorers' own functions, for the explain-then-judge study. Written by the blue side; RUN BY THE RED SIDE ONLY, because
it reads the T1 payload files. It prints counts and hashes, never a packet.

The path is the one the recorded scores used (judge_opus_q1q2.build_units for T1 v2, stage3_t1v3_score.build_units
for T1 v3): `stage3_t1_score.regenerate(corpus, planting payloads, template, plants manifest)` re-plants and refuses
unless the plants reproduce the manifest's own hash; `stage3_t1_score.build_items(results, days, seed base,
stem + "+t1v2" / "+t1v3", render)` builds the units; the composed O_diff items are kept. A plant's regime comes from
its own result (the payload's `arm`). In scope: T1 v2 conforming (routine) and alarming; T1 v3 middle and
routine_redraw (routine); the sham arms are left out. Application keys are `stage3_ft_join.load_flags`' form,
"<planting>:<payload_id>:<arm>".

Outputs (never overwritten):
* the packets file, one JSON line per application: key, planting, payload_id, arm, recorded_regime, regime,
  document, label, packet (exactly as the composed-view prompt receives it), packet_sha256, packet_chars,
  text_chars, truncated;
* a text-free index: per application key, planting, recorded_regime, regime, packet_chars, text_chars,
  packet_sha256, truncated; counts by planting and regime; the packets file's sha256.

It opens the corpus, the org template, the two payload files and the two plants manifests, and nothing else: no
judge cache, no result record, no score or rule file.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_etj_render.py --payloads-v2 ... --plants-v2 ...
        --payloads-v3 ... --plants-v3 ... --packets-out ... --index-out ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

IN_SCOPE = {"t1v2": {"conforming": "routine", "alarming": "alarming"},
            "t1v3": {"middle": "middle", "routine_redraw": "routine"}}
STEM_TAGS = {"t1v2": "t1v2", "t1v3": "t1v3"}
INDEX_FIELDS = ("key", "planting", "recorded_regime", "regime", "packet_chars", "text_chars", "packet_sha256", "truncated")


@dataclass(frozen=True)
class Planting:
    name: str                 # "t1v2" or "t1v3"
    payloads: Path            # the planting list the plants were made from
    manifest: Mapping[str, Any]


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def render(plantings: Sequence[Planting], *, corpus: Path, template: Path, regenerate: Callable, build_items: Callable,
           days: Sequence[str], base: Any, stem: str, render_event: Any) -> list[dict]:
    recs: list[dict] = []
    seen: set[str] = set()
    for pl in plantings:
        scope = IN_SCOPE[pl.name]
        results = regenerate(corpus, pl.payloads, template, pl.manifest)
        regime = {(r.payload_id, r.arm): r.regime for r in results}
        items = build_items(results, days, base, f"{stem}+{STEM_TAGS[pl.name]}", render_event)
        for it in items["O_diff"]:
            rr = regime.get((it["payload_id"], it["arm"]))
            if rr not in scope:
                continue
            key = f"{pl.name}:{it['payload_id']}:{it['arm']}"
            if key in seen:
                raise ValueError(f"duplicate application key {key}")
            seen.add(key)
            pk = it["packet"]
            recs.append({"key": key, "planting": pl.name, "payload_id": it["payload_id"], "arm": it["arm"],
                         "recorded_regime": rr, "regime": scope[rr], "document": it.get("path") or it.get("document"),
                         "label": it.get("label"), "packet": pk, "packet_sha256": _sha(pk), "packet_chars": len(pk),
                         "text_chars": it.get("text_chars"), "truncated": bool(it.get("truncated"))})
    return recs


def write_outputs(recs: Sequence[Mapping], packets_out: Path, index_out: Path) -> dict:
    packets_out, index_out = Path(packets_out), Path(index_out)
    for p in (packets_out, index_out):
        if p.exists():
            raise SystemExit(f"{p} exists; never overwritten")
    packets_out.parent.mkdir(parents=True, exist_ok=True)
    with packets_out.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    by = Counter(f"{r['planting']}|{r['recorded_regime']}" for r in recs)
    summary = {"n_applications": len(recs), "by_planting_and_regime": dict(sorted(by.items())),
               "by_regime": dict(sorted(Counter(r["regime"] for r in recs).items())),
               "n_truncated": sum(1 for r in recs if r["truncated"]),
               "packets_file": str(packets_out), "packets_file_sha256": hashlib.sha256(packets_out.read_bytes()).hexdigest()}
    index = {**summary, "applications": [{k: r[k] for k in INDEX_FIELDS} for r in recs]}
    index_out.parent.mkdir(parents=True, exist_ok=True)
    index_out.write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    summary["index_file"] = str(index_out)
    summary["index_file_sha256"] = hashlib.sha256(index_out.read_bytes()).hexdigest()
    return summary


def print_summary(summary: Mapping) -> None:
    print(json.dumps(summary, indent=1))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    import stage3_ft_slots as sl
    import judge_client as jc
    ap = argparse.ArgumentParser(description="Render the ETJ planted packets (red side runs this; counts and hashes only).")
    ap.add_argument("--payloads-v2", type=Path, required=True, help="work/stage3/t1v2/payloads-v2.json")
    ap.add_argument("--plants-v2", type=Path, required=True, help="work/stage3/t1v2/plants-v2.json")
    ap.add_argument("--payloads-v3", type=Path, required=True, help="work/stage3/t1v3/payloads-v3-planting.json")
    ap.add_argument("--plants-v3", type=Path, required=True, help="work/stage3/t1v3/plants-v3.json")
    ap.add_argument("--packets-out", type=Path, required=True)
    ap.add_argument("--index-out", type=Path, required=True)
    ap.add_argument("--corpus", type=Path, default=Path(sl.CORPUS))
    ap.add_argument("--template", type=Path, default=jc.FORK / "bootstrap" / "org_template.yaml")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    a = parse_args(argv)
    for p in (a.packets_out, a.index_out):
        if p.exists():
            raise SystemExit(f"{p} exists; never overwritten")
    import stage3_t1_score as ts
    import stage3_views as sv
    rows = sv.read_jsonl(a.corpus)
    plantings = []
    for name, payloads, plants in (("t1v2", a.payloads_v2, a.plants_v2), ("t1v3", a.payloads_v3, a.plants_v3)):
        manifest = json.loads(plants.read_text(encoding="utf-8"))
        if manifest.get("payloads_sha256") != sv.file_sha256(payloads):
            raise SystemExit(f"refusing: {payloads.name} is not the planting list {plants.name} was made from")
        plantings.append(Planting(name, payloads, manifest))
    recs = render(plantings, corpus=a.corpus, template=a.template, regenerate=ts.regenerate, build_items=ts.build_items,
                  days=sv.corpus_days(rows), base=sv.seed_base(), stem=sv.stem_of(a.corpus), render_event=sv.jc_mod.get_render_event())
    summary = write_outputs(recs, a.packets_out, a.index_out)
    summary["inputs_sha256"] = {"corpus": sv.file_sha256(a.corpus), "payloads_v2": sv.file_sha256(a.payloads_v2),
                                "plants_v2": sv.file_sha256(a.plants_v2), "payloads_v3": sv.file_sha256(a.payloads_v3),
                                "plants_v3": sv.file_sha256(a.plants_v3), "render_module": sv.file_sha256(Path(__file__).resolve())}
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
