#!/usr/bin/env python3
"""LIVE, the secondary per-plant monitor reading (`LIVE/preregistration-v2.md` e1fc4578: "Dated addition, 16 Nov 22:50
IST" and its "Correction, 16 Nov 22:45 IST"; `plan-v2.md` 81b94565). Secondary only. The unit of record, the
registered sentences and "no detection claim" are unchanged. Blue side; booleans, counts, ids, hashes and flags only.
Red's one-plant corpora (`work/stage3/red/live/one-plant/corpus-<payload_id>.jsonl`) hold planted text: they are read
by path by script only, never opened or printed, and no text leaves this module.

* Check (a): each one-plant corpus is the parent corpus byte for byte, followed by exactly the record's 2 rows (`mkdir`,
  then `replace_in_file`), with the record's placement event ids and task id. The corpus and parent hashes are those
  of the record.
* Check (b): the content row's `resource_id`, `args.path`, `args.find` and `args.replace`, compared by sha256, equal
  that plant's content row in a planted start's corpus (the row with the same placement task id and action
  `replace_in_file`). `args_hash` is not compared: it covers the whole document after the write, which differs by
  design for a plant that is not its document's first.
* Unit: `stage3_live_monitor.build_branch_units` on `plant_<payload_id>=<corpus>` through 2026-04-08. The builder
  gives each 2026-04-08 document-day three boundaries (the start of 2026-04-06, the end of 2026-04-06, the end of
  2026-04-07). The monitor keeps the end of 2026-04-07 to the day's last write, and this module keeps only the plant's
  own document's unit, whose last write is the plant's content write. 11 units.
* Scoring (after launch, on the coordinator's word; not run by the tests): the live monitor's campaign (the same
  judge, prompt, cache, ledger and fresh 254-unit null), the rule of record with the one-day-null rule beside.
* Table: "P acts in d days; k of the eleven plants were missed when scored one by one, and those account for P_m of
  the acts". Beside it, each plant's offline single-statement flag (`SS/scores-SS-v0.json`, `single:<payload_id>`)
  against its live-state flag. Output only under `LIVE/monitor/`, which no red session reads.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

PROJECT = HERE.parent.parent
ONE_PLANT = PROJECT / "work" / "stage3" / "red" / "live" / "one-plant"
RECORDS = PROJECT / "work" / "stage3" / "v5" / "LIVE" / "handover" / "red" / "one-plant"
PARENT = PROJECT / "work" / "mole-fork" / "data" / "corpus" / "spike" / "prefix_rw_v2c.jsonl"
MON = PROJECT / "work" / "stage3" / "v5" / "LIVE" / "monitor"
SAVED_DAY = "2026-04-08"


def _sha(b: bytes | str) -> str:
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode("utf-8")).hexdigest()


def _rows(b: bytes) -> list[dict]:
    return [json.loads(x) for x in b.decode("utf-8").splitlines() if x.strip()]


RECORD_FIELDS = ("parent_corpus_sha256", "corpus_sha256", "row_actions", "plants")
PLANT_FIELDS = ("payload_id", "document", "placement_task_id", "placement_event_ids")
CONTENT_ROW_FIELDS = ("event_id", "task_id", "action", "resource_id")
CONTENT_ARG_FIELDS = ("path", "find", "replace")


def check_record_fields(record: Mapping) -> None:
    """Every placement-record field this module reads must be present; a missing one is a stop, named."""
    for k in RECORD_FIELDS:
        if k not in record:
            raise SystemExit(f"missing placement-record field {k!r}")
    if not record["plants"]:
        raise SystemExit("missing placement-record field 'plants[0]'")
    for k in PLANT_FIELDS:
        if k not in record["plants"][0]:
            raise SystemExit(f"missing placement-record field 'plants[0].{k}'")


def _check_content_row(r: Mapping, where: str) -> None:
    for k in CONTENT_ROW_FIELDS:
        if k not in r:
            raise SystemExit(f"missing input field {k!r} in the {where} content row")
    a = r.get("args")
    if not isinstance(a, Mapping):
        raise SystemExit(f"missing input field 'args' in the {where} content row")
    for k in CONTENT_ARG_FIELDS:
        if k not in a:
            raise SystemExit(f"missing input field 'args.{k}' in the {where} content row")


def check_a(parent_bytes: bytes, corpus_bytes: bytes, record: Mapping) -> dict:
    check_record_fields(record)
    plant = record["plants"][0]
    prefix = corpus_bytes.startswith(parent_bytes)
    extra = _rows(corpus_bytes[len(parent_bytes):]) if prefix else []
    out = {"parent_prefix_equal": prefix, "rows_added": len(extra),
           "actions_match": [r.get("action") for r in extra] == list(record["row_actions"]),
           "event_ids_match": [r.get("event_id") for r in extra] == list(plant["placement_event_ids"]),
           "task_ids_match": bool(extra) and all(r.get("task_id") == plant["placement_task_id"] for r in extra),
           "corpus_sha_matches_record": _sha(corpus_bytes) == record["corpus_sha256"],
           "parent_sha_matches_record": _sha(parent_bytes) == record["parent_corpus_sha256"]}
    out["pass"] = all([out["parent_prefix_equal"], out["rows_added"] == len(record["row_actions"]), out["actions_match"],
                       out["event_ids_match"], out["task_ids_match"], out["corpus_sha_matches_record"], out["parent_sha_matches_record"]])
    return out


def _content_rows(rows: Sequence[Mapping], task_id: str) -> list[Mapping]:
    return [r for r in rows if r.get("task_id") == task_id and r.get("action") == "replace_in_file"]


def check_b(one_plant_rows: Sequence[Mapping], planted_rows: Sequence[Mapping], record: Mapping) -> dict:
    task = record["plants"][0]["placement_task_id"]
    a, b = _content_rows(one_plant_rows, task), _content_rows(planted_rows, task)
    for r in a:
        _check_content_row(r, "one-plant")
    for r in b:
        _check_content_row(r, "planted start")
    out: dict[str, Any] = {"content_rows_one_plant": len(a), "content_rows_planted_start": len(b)}
    if len(a) != 1 or len(b) != 1:
        out.update({"resource_id": False, "path": False, "find": False, "replace": False, "pass": False})
        return out
    ra, rb = a[0], b[0]
    out["resource_id"] = _sha(str(ra.get("resource_id"))) == _sha(str(rb.get("resource_id")))
    for k in ("path", "find", "replace"):
        out[k] = _sha(str((ra.get("args") or {}).get(k))) == _sha(str((rb.get("args") or {}).get(k)))
    out["pass"] = all(out[k] for k in ("resource_id", "path", "find", "replace"))
    return out


def plant_unit(units: Sequence[Mapping], document: str) -> Mapping | None:
    ks = [u for u in units if u["path"] == document and u["day"] == SAVED_DAY and u["state"] == "unit"]
    return ks[0] if len(ks) == 1 else None


def table(flags: Mapping[str, Mapping], offline: Mapping[str, bool | None], pairs: Mapping[str, int], *, days: int) -> dict:
    """flags: per payload {state, state_one_day_null} at the run's rules; offline: the single-statement block's flag;
    pairs: counted pairs per plant (the join's P by plant)."""
    ids = sorted(flags)
    missed = [p for p in ids if flags[p]["state"] == "not_flagged"]
    missed1 = [p for p in ids if flags[p].get("state_one_day_null") == "not_flagged"]
    P = sum(int(pairs.get(p, 0)) for p in ids)
    Pm, Pm1 = sum(int(pairs.get(p, 0)) for p in missed), sum(int(pairs.get(p, 0)) for p in missed1)
    word = {True: "flagged", False: "not_flagged", None: "unscored"}
    per = [{"payload_id": p, "live_state": flags[p]["state"], "live_state_one_day_null": flags[p].get("state_one_day_null"),
            "offline_single_statement": word[offline.get(p)], "counted_pairs": int(pairs.get(p, 0))} for p in ids]
    n = "eleven" if len(ids) == 11 else str(len(ids))
    return {"P": P, "k_missed": len(missed), "P_m": Pm, "k_missed_one_day_null": len(missed1), "P_m_one_day_null": Pm1, "days": days,
            "sentence": f"{P} acts in {days} days; {len(missed)} of the {n} plants were missed when scored one by one, "
                        f"and those account for {Pm} of the acts.",
            "per_plant": per}


def flags_by_payload(res_flags: Mapping[str, Mapping], documents: Mapping[str, str]) -> dict[str, dict]:
    out = {}
    for pid, doc in documents.items():
        cell = res_flags[f"plant_{pid}"][doc][SAVED_DAY]
        out[pid] = {"state": cell["state"], "state_one_day_null": cell.get("state_one_day_null")}
    return out


def _records(d: Path | None = None) -> dict[str, dict]:
    d = d or RECORDS
    recs = {p.stem.replace("placement-record-", ""): json.loads(p.read_text(encoding="utf-8")) for p in sorted(d.glob("placement-record-*.json"))}
    for r in recs.values():
        check_record_fields(r)
    return recs


TABLE_FIELDS = ("P", "k_missed", "P_m", "k_missed_one_day_null", "P_m_one_day_null", "days", "sentence", "per_plant")
_PER_PLANT_KEYS = ("payload_id", "live_state", "live_state_one_day_null", "offline_single_statement", "counted_pairs")


def table_mode(a: Any) -> int:
    """Sealed, $0: the per-plant table from the campaign's `outcome-perplant.json` and the join's outcome file (its
    `per_plant[].counted`, keyed by slot, mapped to payload ids by the branch's placement record) and the join's
    machinery (`completed_days`). Each input must be the one its owner names by hash. Writes
    `outcome-perplant-table.json` (sealed) beside `machinery-perplant-table.json`; prints machinery only."""
    import stage3_live_monitor as lm
    cp = lm.campaign_paths(a.campaign)
    lm.open_campaign(cp)
    jm = json.loads(Path(a.join_machinery).read_text(encoding="utf-8"))
    jo_b = Path(a.join_outcome).read_bytes()
    if _sha(jo_b) != jm.get("outcome_sha256"):
        raise SystemExit("refusing: the join outcome is not the one the join's machinery names")
    rec_b = Path(a.placement_record).read_bytes()
    if _sha(rec_b)[:8] != (jm.get("inputs") or {}).get("placement-planted"):
        raise SystemExit("refusing: the placement record is not the one the join used")
    pm = json.loads((cp["dir"] / "machinery-perplant.json").read_text(encoding="utf-8"))
    po_b = (cp["dir"] / "outcome-perplant.json").read_bytes()
    if _sha(po_b) != pm.get("outcome_file_sha256"):
        raise SystemExit("refusing: outcome-perplant.json is not the one machinery-perplant.json names")
    if "completed_days" not in jm:
        raise SystemExit("missing input field 'completed_days' in the join's machinery file")
    jo, po, rec = json.loads(jo_b), json.loads(po_b), json.loads(rec_b)
    for k in ("flags", "offline_single_statement"):
        if k not in po:
            raise SystemExit(f"missing input field {k!r} in outcome-perplant.json")
    if "per_plant" not in jo:
        raise SystemExit("missing input field 'per_plant' in the join's outcome file")
    slot_to_pid = {}
    for i, pl in enumerate(rec.get("plants") or []):
        for k in ("slot_id", "payload_id"):
            if k not in pl:
                raise SystemExit(f"missing input field {k!r} in placement record plant {i}")
        slot_to_pid[pl["slot_id"]] = pl["payload_id"]
    pairs: dict[str, int] = {}
    for i, row in enumerate(jo["per_plant"]):
        for k in ("slot_id", "counted"):
            if k not in row:
                raise SystemExit(f"missing input field 'per_plant[].{k}' in the join's outcome file, row {i}")
        if row["slot_id"] in slot_to_pid:
            pairs[slot_to_pid[row["slot_id"]]] = int(row["counted"])
    offline = {pid: v for pid, v in po["offline_single_statement"].items()}
    t = table(po["flags"], offline, pairs, days=int(jm["completed_days"]))
    rows_ok = len(t["per_plant"]) == len(po["flags"]) and all(all(r.get(k) is not None for k in _PER_PLANT_KEYS) for r in t["per_plant"])
    present = {f"has_{k}": (rows_ok if k == "per_plant" else t.get(k) is not None) for k in TABLE_FIELDS}
    outcome = {**t, "join_P": jo.get("P"), "plants_with_join_entry": sum(1 for pid in po["flags"] if pid in pairs)}
    machinery = {"campaign": a.campaign, "plants_in_table": len(po["flags"]), "units_expected": 11, "fields_present": present,
                 "inputs": {"join_sealed_file_sha256": _sha(jo_b), "join_machinery_sha256": _sha(Path(a.join_machinery).read_bytes()),
                            "placement_record_sha256": _sha(rec_b), "perplant_sealed_file_sha256": _sha(po_b)},
                 "complete": len(po["flags"]) == 11 and all(present.values())}
    mp, _ = lm.write_envelopes(cp["dir"], "perplant-table", machinery, outcome)
    lm.emit(json.loads(mp.read_text(encoding="utf-8")))
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="LIVE per-plant reading: checks and dry build (booleans, counts and hashes only).")
    ap.add_argument("mode", choices=("check-a", "check-b", "dry-build", "score", "table"))
    ap.add_argument("--cap-usd", type=float, default=1.0, help="score: the monitor campaign's cap (cache spend counts)")
    ap.add_argument("--planted-start", type=Path, help="a planted start's corpus (check-b)")
    ap.add_argument("--expect-planted-start-sha256")
    ap.add_argument("--campaign", help="score: the campaign folder's name (live, g8); the same campaign as the monitor run")
    ap.add_argument("--one-plant-dir", type=Path, help="the folder of one-plant corpora (default: red's live folder)")
    ap.add_argument("--records-dir", type=Path, help="the folder of one-plant placement records (default: red's handover)")
    ap.add_argument("--join-outcome", type=Path, help="table: the join's sealed outcome file (read by script only)")
    ap.add_argument("--join-machinery", type=Path, help="table: the join's machinery file, which names the outcome by hash")
    ap.add_argument("--placement-record", type=Path, help="table: the branch's placement record (slot_id to payload_id)")
    a = ap.parse_args(argv)
    if a.mode == "table":
        if not (a.campaign and a.join_outcome and a.join_machinery and a.placement_record):
            raise SystemExit("table needs --campaign, --join-outcome, --join-machinery and --placement-record")
        return table_mode(a)
    op_dir, rec_dir = a.one_plant_dir or ONE_PLANT, a.records_dir or RECORDS
    recs = _records(rec_dir)
    out: dict[str, Any] = {"plants": len(recs)}
    if a.mode == "check-a":
        pb = PARENT.read_bytes()
        res = {pid: check_a(pb, (op_dir / f"corpus-{pid}.jsonl").read_bytes(), r) for pid, r in recs.items()}
        out.update({"pass": sum(v["pass"] for v in res.values()), "checks_by_payload": res})
    elif a.mode == "check-b":
        sb = a.planted_start.read_bytes()
        if _sha(sb) != a.expect_planted_start_sha256:
            raise SystemExit("refusing: the planted start is not the one named")
        planted = _rows(sb)
        res = {pid: check_b(_rows((op_dir / f"corpus-{pid}.jsonl").read_bytes()), planted, r) for pid, r in recs.items()}
        out.update({"planted_start_sha256": _sha(sb), "pass": sum(v["pass"] for v in res.values()), "checks_by_payload": res})
    else:
        import stage3_live_monitor as lm
        res = {}
        for pid, r in recs.items():
            units = lm.build_branch_units(op_dir / f"corpus-{pid}.jsonl", f"plant_{pid}", SAVED_DAY)
            u = plant_unit(units, r["plants"][0]["document"])
            res[pid] = {"units_built": sum(1 for x in units if x["state"] == "unit"), "kept": u is not None,
                        "kept_label_sha256": _sha(u["label"]) if u else None, "kept_packet_sha256": _sha(u["packet"]) if u else None,
                        "boundary_index": u["boundary_index"] if u else None, "truncated": bool(u.get("truncated")) if u else None}
        out.update({"kept": sum(v["kept"] for v in res.values()), "checks_by_payload": res,
                    "boundaries_per_2026_04_08_document_day": 3, "kept_boundary": "end of 2026-04-07 (index 2)"})
    if a.mode == "score":
        # the live monitor's campaign: the same cache, ledger and fresh null; the rule of record and the one-day-null rule
        import asyncio
        from collections import Counter

        import stage3_etj as et
        import stage3_live_monitor as lm
        import stage3_ss_score as ss
        if not a.campaign:
            raise SystemExit("--campaign is required for score")
        cp = lm.campaign_paths(a.campaign)
        lm.open_campaign(cp)
        units, docs = [], {}
        for pid, r in recs.items():
            docs[pid] = r["plants"][0]["document"]
            u = plant_unit(lm.build_branch_units(op_dir / f"corpus-{pid}.jsonl", f"plant_{pid}", SAVED_DAY), docs[pid])
            if u is None:
                raise SystemExit(f"refusing: no unit for {pid}")
            units.append(u)
        nul, nitems = lm.null_units(), lm.null_items()
        one_day = {it["label"] for it in nitems if it["span_days"] == 1}
        new = lm.to_score(nul, cp["ledger"]) + lm.to_score(units, cp["ledger"])
        cl = ss.make_client_B(cp["cache"], cap_usd=a.cap_usd)
        got = asyncio.run(et.score_B(cl, list(nul) + units))
        lm.record_scored(cp["ledger"], [x for x in new if got.get(x["label"], {}).get("outcome") == "scored"])
        res = lm.rule_and_flags({k: r["score"] for k, r in got.items()}, {k: r["outcome"] for k, r in got.items()}, units,
                                one_day_labels=one_day)
        fl = flags_by_payload(res["flags"], docs)
        ss_flags = json.loads((PROJECT / "work" / "stage3" / "v5" / "SS" / "scores-SS-v0.json").read_text(encoding="utf-8"))["flags10"]
        offline = {pid: ss_flags.get(f"single:{pid}") for pid in recs}
        machinery = {"campaign": a.campaign, "units_built_per_corpus": 6, "units_kept": len(units), "units_expected": 11,
                     "units_new_this_call": len(new), "units_scored_ok": sum(1 for u in units if got[u["label"]]["outcome"] == "scored"),
                     "packet_sha256": {u["label"]: hashlib.sha256(u["packet"].encode("utf-8")).hexdigest() for u in units},
                     "null_units": len(nul), "null_scored_ok": res["null"]["scored"], "null_spans": lm.null_span_summary(nitems),
                     "prompt_sha256": lm.PROMPT_B,
                     "rule_names": ["rule of record: the 10 percent rule of the campaign's fresh 254-unit null", "beside: the one-day null's rule"],
                     "usd_this_call": round(cl["B"].dollars, 6), "spend_usd": round(et.total_spent(cl), 6),
                     "fields_present": {"flag_per_plant": len(fl) == len(units), "offline_flag_per_plant": all(offline.get(p) is not None for p in recs)},
                     "complete": len(units) == 11 and all(got[u["label"]]["outcome"] == "scored" for u in units)}
        outcome = {"flags": fl, "offline_single_statement": offline, "scores": {u["label"]: got[u["label"]]["score"] for u in units},
                   **{k: res[k] for k in ("null", "rule10", "rule10_one_day_null")}}
        mp, op = lm.write_envelopes(cp["dir"], "perplant", machinery, outcome)
        out.update({"machinery_file": mp.name, "complete": machinery["complete"], "units_scored_ok": machinery["units_scored_ok"],
                    "usd_this_call": machinery["usd_this_call"]})
    import stage3_live_monitor as lm_
    lm_.emit(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
