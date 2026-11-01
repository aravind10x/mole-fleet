#!/usr/bin/env python3
"""Brief 33 A3, A4, B1 and B2 (S3, 2026-11-02): the driver. Modes `apply | render | score`; the readings are
`stage3_b3_s3_readings.py`.

apply   The pre-flight (26 files, the configuration, the stream set asserted as exactly {1, 2, 3, 4, 6}), the payload and
        control files verified against `inserter-dry-run-v1.json` `inputs_sha256`, the applied id sets checked against plan
        section 1.1's hashes, then THE ONE DRAW in section 3's order with the arm seeds of A1 (tag 1 the candidates' item
        pairs; tag 2 their lone lines after every tag-1 draw, `exclude` = the item's two authors as drawn; tag 3 the control
        items' pairs; tag 4 the comparison items; tag 6 the control items' lone lines after every tag-3 pair), through
        `build_parts_inserter(corpus, template, inserter-dry-run-v1.json)`'s restricted mode (`plant_pair`; section 2.4 (3)
        is the module's `_draw_listed`, up to MAX_REDRAWS re-draws from the same stream, refusals counted; an item that
        cannot complete its need leaves every population, S-S; a control item whose lines cannot supply the pair leaves the
        add-on only). Each application is made on its own copy of the state (brief 27 E3). Every unit is rendered at once
        under every row of section 2.6 it is scored under (`planted_items`, `author_items`, `o_packet`; the window is the
        corpus span, B1's `build_world`) and its packets are stored in `s3-applications-v0.json`, a never-open file for the
        coordinator and the reviewer (it holds applied document states); `s3-applications-v0.md` is the record (counts,
        hashes, refusals by reason, drops by reason; no item text in any printed line).
render  Counts per row, the sha256 over each row's sorted packet hashes, and the character-based pre-signal estimate
        beside S2's $76.62 (`estimate`'s 2.15 characters per token, PRICES and CONVERSE_PRICES, B1's output-token basis).
        No request is sent.
score   Stage B. One spend ledger across every S3 cache file, enforced through `request_guard` on every client, with the
        in-flight units' bases reserved (the overshoot is at most four units' bases at concurrency 4), stopping at $153.25;
        each client's own spend cap is $153.25 less the dollars recorded in the other S3 caches; the view order of B2
        enforced (cell k + 1 opens only when cell k is complete); the pause after the first about 20 carrier units
        (`--first-batch`), continued only with `--continue` after the coordinator's STATUS line; persistent, resumable
        state in `s3-run-v0.json` (a restart re-asks nothing cached); counts and dollars printed, never a score or flag
        aggregate. The scores file `s3-scores-v0.json` is rebuilt from the caches after every cell: unit id, view, judge,
        outcome, score, the flag at the sealed rule (`stage3_thresholds.is_flagged`, the tie draw keyed by author for an
        author rule and by the cache label for a unit rule, as B1 and T1 did), cache label; no text.

Never printed, logged or written into any record: an item line, document text, rubric or declared effect. No OpenRouter
request of any kind.

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_s3.py apply
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import judge_client as jc_mod  # noqa: E402
import score_expensive_tier as set_  # noqa: E402
import stage3_author_doc as ad  # noqa: E402
import stage3_b1_dossier as b1  # noqa: E402
import stage3_b3_inserter_dry_run as dr  # noqa: E402
import stage3_b3_preflight as pf  # noqa: E402
import stage3_t1 as t1  # noqa: E402
import stage3_thresholds as th  # noqa: E402
import stage3_views as sv  # noqa: E402
from mole.oracles import document as doc  # noqa: E402

VERSION = "b3-s3-driver/v0"
PROJECT = HERE.parents[1]
B3 = PROJECT / "work" / "stage3" / "b3"
RUN_TAG = "s3"
CONFIG = B3 / "s3-config-v0.json"
MATRIX = B3 / "s3-analysis-matrix-v0.json"
APPLICATIONS = B3 / "s3-applications-v0.json"
APPLICATIONS_MD = B3 / "s3-applications-v0.md"
RENDER = B3 / "s3-render-v0.json"
RUN = B3 / "s3-run-v0.json"
SCORES = B3 / "s3-scores-v0.json"
CACHE_DIR = B3 / "cache-s3"
LOCK_FILE = CACHE_DIR / ".s3-run.lock"
CORPUS = PROJECT / "work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl"
TEMPLATE = PROJECT / "work/mole-fork/bootstrap/org_template.yaml"
VALID = B3 / "inserter-dry-run-v1.json"
S2 = B3 / "s2-estimate-v0.json"
PINNED = {CORPUS: "ffc1f6cd423cae68ac5bd752580f845a838625ebc57a9cf1e083d7e6ddaeeb74",
          TEMPLATE: "294d59d267335ee19c4d7c06d15d4ecfe59c621a21e90c1ac73ccee8757ce6dc",
          VALID: "021389311e33658884cf316778dc19a39b880ff9f884f9bb85598857c3260a47",
          S2: "46d2e153798cad2b4259bf2e708f56937c233f86295963edda234a2e057ed7a0"}
ARMS_EXPECTED = {1: 2026118110, 2: 2026118120, 3: 2026118130, 4: 2026118140, 6: 2026118160}   # plan section 3 and its note; no tag 5
#: plan section 1.1's net id hashes (sha256 of the sorted ids joined by newlines)
ID_SHA256 = {"full": "5dbd067d66497329c85135775c681b199aa14cc1f52c4bd5be438bedd61ea68f",
             "controls": "3db4d199cc3dc9edf215a91de84de2861b0cd42b81c21f984318345b2afdfb4c",
             "sham": "27909dc26b5dcdc0a46cdc41bfb3215114eab93af2378f7b418e2eb1d011d70a"}
EXPECTED_COUNTS = {"items": 232, "lines": 564, "candidate_items": 146, "control_items": 42, "sham_items": 44, "candidate_lines": 438, "control_lines": 126}
FIGURE_USD, STOP_USD = 76.62, 153.25          # brief 15 A6.25
ESCALATE_RATIO = 4 / 3                         # brief 33 A4 and B1: more than a third over the figure goes to Aravind
FIRST_BATCH = 20
CONCURRENCY, RPM = 4, 30
MODELS = {"opus48": "anthropic.claude-opus-4-8", "sonnet": "anthropic.claude-sonnet-5", "sol": "us.openai.gpt-6-sol"}
MAX_TOKENS = {"opus48": 4000, "sonnet": jc_mod.MAX_TOKENS, "sol": jc_mod.CONVERSE_MAX_TOKENS}
JUDGE_NAME = {"opus48": "Opus 4.8", "sonnet": "Sonnet 5", "sol": "GPT-6 Sol"}
#: B2's order: each cell (view key, judge) complete before the next; within a per-agent cell items then lines
ORDER: list[tuple[str, str]] = [(ad.ISO, "opus48"), ("P_author", "opus48"), (ad.ISO, "sonnet"), ("P_author", "sonnet"),
                                (ad.LIVE, "opus48"), (ad.LIVE, "sonnet"), ("O_diff", "sonnet"), ("O_diff", "opus48"), ("O_diff", "sol")]
PER_AGENT = (ad.ISO, "P_author")                 # the rows that carry lone-line units
S2_CELL = {(ad.ISO, "opus48"): "dossier_iso:opus48", ("P_author", "opus48"): "P_author:opus48", (ad.ISO, "sonnet"): "dossier_iso:sonnet",
           ("P_author", "sonnet"): "P_author:sonnet", (ad.LIVE, "opus48"): "dossier_live:opus48", (ad.LIVE, "sonnet"): "dossier_live:sonnet",
           ("O_diff", "sonnet"): "O_diff:sonnet", ("O_diff", "opus48"): "O_diff:opus48", ("O_diff", "sol"): "O_diff:sol"}
#: the sealed rules per cell (plan section 4.9), read by script at scoring time; never printed
RULE_SOURCE = {(ad.ISO, "opus48"): ("work/stage3/b1/b1-null.json", ("judges", "opus48", "views", ad.ISO, "author_rule")),
               (ad.ISO, "sonnet"): ("work/stage3/b1/b1-null.json", ("judges", "sonnet", "views", ad.ISO, "author_rule")),
               (ad.LIVE, "opus48"): ("work/stage3/b1/b1-null.json", ("judges", "opus48", "views", ad.LIVE, "author_rule")),
               (ad.LIVE, "sonnet"): ("work/stage3/b1/b1-null.json", ("judges", "sonnet", "views", ad.LIVE, "author_rule")),
               ("P_author", "opus48"): ("work/stage3/q1q2-synthetic/opus48/judge-null.json", ("views", "P_author", "author_rule")),
               ("P_author", "sonnet"): ("work/stage3/views/calibration-v1.json", ("views", "P_author", "author_rule")),
               ("O_diff", "opus48"): ("work/stage3/q1q2-synthetic/opus48/judge-null.json", ("views", "O_diff", "rule")),
               ("O_diff", "sonnet"): ("work/stage3/views/calibration-v1.json", ("views", "O_diff", "rule")),
               ("O_diff", "sol"): ("work/stage3/q1q2-synthetic/extra-judge-null.sol.json", ("views", "O_diff", "rule"))}
SCORES_VIEW = {ad.ISO: "P_author_doc_iso", ad.LIVE: "P_author_doc_live", "P_author": "P_author", "O_diff": "O_diff"}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_json(p: Path) -> Any:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p: Path, obj: Any) -> str:
    text = json.dumps(obj, indent=1, ensure_ascii=False) + "\n"
    Path(p).write_text(text, encoding="utf-8")
    return sha256_text(text)


def ids_sha256(ids) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()


# ── A1 and A3's pre-draw checks ───────────────────────────────────────────────────────────────────

def assert_arm_seeds(config: Mapping[str, Any]) -> dict[int, int]:
    """The stream set is exactly {1, 2, 3, 4, 6} at 20261181 x 100 + 10 t (the pre-flight alone admits a tag 5 or a missing 6)."""
    arms = {int(t): int(s) for t, s in config["arm_seeds"].items()}
    if arms != ARMS_EXPECTED:
        raise SystemExit(f"refusing: the arm-seed set {sorted(arms)} is not exactly {sorted(ARMS_EXPECTED)} at the plan's values")
    for t, s in arms.items():
        if s != pf.arm_seed(t):
            raise SystemExit(f"refusing: arm {t} seed {s} is not {pf.arm_seed(t)}")
    return arms


def preflight(config_path: Path = CONFIG) -> dict:
    config = load_json(config_path)
    out = pf.run(config=config)
    if not out["pass"] or out["n_files"] != 26:
        raise SystemExit("refusing: the pre-flight did not pass 26 of 26 with the configuration: " + "; ".join(out["refusals"]))
    assert_arm_seeds(config)
    for p, want in PINNED.items():
        if sha256_file(p) != want:
            raise SystemExit(f"refusing: {p.name} is not {want[:8]}")
    return out


def verify_payload_files() -> dict[str, str]:
    """The payload and control files against inserter-dry-run-v1.json `inputs_sha256`, before they are read."""
    v1 = load_json(VALID)["inputs_sha256"]
    paths = dr.input_paths()
    got = {}
    for k in ("candidates_sonnet55", "candidates_glm53", "controls_sonnet55", "controls_glm53", "payloads_v2", "items_v0", "stratum_v0", "key_b3",
              "triples_b3", "t1_triples", "t1v3_manifest"):
        h = sha256_file(paths[k])
        if h != v1[k]:
            raise SystemExit(f"refusing: {paths[k].name} sha256 {h[:8]} is not inserter-dry-run-v1.json's {v1[k][:8]}")
        got[str(paths[k].relative_to(PROJECT))] = h
    return got


def net_sets(matrix: Mapping[str, Any]) -> dict[str, list[str]]:
    """The applied id sets, checked against section 1.1's hashes (section 2.5)."""
    sets = {k: list(matrix["populations"][k]["ids"]) for k in ("full", "controls", "sham")}
    for k, ids in sets.items():
        if ids_sha256(ids) != ID_SHA256[k]:
            raise SystemExit(f"refusing: the {k} id set does not hash to plan section 1.1's value")
    return sets


# ── rendering (A4): every unit under every row it is scored under ────────────────────────────────

class World:
    def __init__(self):
        self.rows = sv.read_jsonl(CORPUS)
        self.days = sv.corpus_days(self.rows)       # the window rule: the corpus span (build_world, line 231)
        self.base = sv.seed_base()
        self.stem = sv.stem_of(CORPUS)
        self.render_event = jc_mod.get_render_event()


def unit_label(stem: str, unit_id: str) -> str:
    return f"{stem}+{RUN_TAG}:{unit_id}"


def render_unit(W: World, res: t1.PlantResult, unit_id: str, with_lines_rows: bool) -> dict[str, dict]:
    """Packets per row for one application: the dossier readings (B1's planted_items), P_author zero-context
    (author_items) and, for an item application, O_diff (as T1's build_items). The label is S3's own, unique per unit and
    view; the key is cache_key(view key, label, packet)."""
    out: dict[str, dict] = {}
    pstem = f"{W.stem}+{RUN_TAG}"
    label = unit_label(W.stem, unit_id)
    # the dossier readings
    its = b1.planted_items(res, RUN_TAG, W.days, W.base, W.stem)
    for key, lst in its.items():
        if len(lst) != 1:
            raise SystemExit(f"{unit_id}: {len(lst)} dossier units under {key}, not one")
        it = lst[0]
        if key == ad.LIVE and not with_lines_rows:
            pass
        out[key] = {"packet": it["packet"], "truncated": bool(it["truncated"]), "label": label, "key": jc_mod.cache_key(key, label, it["packet"]),
                    "author": it["author"], "meta": {k: it[k] for k in ("n_changes", "n_marked_plus", "n_marked_minus", "n_shown_as_written_lines",
                                                                       "neighbour_statements_shown", "own_statements", "own_statements_shown")}}
    # P_author zero-context
    units = sv.author_units(res.rows, [res.document], W.days, W.base, "pair", authors=res.authors)
    pa = sv.author_items(pstem, units, 0)
    if len(pa) != 1:
        raise SystemExit(f"{unit_id}: {len(pa)} P_author units, not one")
    it = pa[0]
    out["P_author"] = {"packet": it["packet"], "truncated": bool(it["truncated"]), "label": label, "key": jc_mod.cache_key("P_author", label, it["packet"]),
                       "author": it["author"], "meta": {k: it[k] for k in ("n_changes", "n_lines_changed", "all_one_line")}}
    # O_diff, item applications only
    if res.arm == "lone":
        ref = doc.DocRef("owncloud", res.document)
        if res.pre_window_boundary == "day0":
            before, frm = W.base[("owncloud", res.document)], f"start of {W.days[0]} (day-0 state)"
        else:
            before, frm = doc.content_at(res.rows, ref, res.pre_window_boundary, base=W.base), f"end of {res.pre_window_boundary}"
        after = doc.content_at(res.rows, ref, res.composition_day, base=W.base)
        text = doc.unified_diff(before, after, res.document)
        last_ts = max((w.ts for w in doc.content_writes(res.rows, ref) if w.ts[:10] == res.composition_day), default=res.composition_day)
        pk, trunc = sv.o_packet("O_diff", res.document, text, frm, last_ts)
        out["O_diff"] = {"packet": pk, "truncated": bool(trunc), "label": label, "key": jc_mod.cache_key("O_diff", label, pk), "author": res.authors[0],
                         "meta": {"boundary": frm, "write_day": res.composition_day, "text_chars": len(text)}}
    return out


def state_sha256(res: t1.PlantResult, base) -> str:
    ref = doc.DocRef("owncloud", res.document)
    st = doc.content_at(res.rows, ref, res.composition_day, base=base)
    return sha256_text(st if isinstance(st, str) else "")


# ── A3: the one draw ──────────────────────────────────────────────────────────────────────────────

def payload_of(it: Mapping[str, Any]) -> dict:
    return {"id": it["payload_id"], "document": it["document"], "statements": it["statements"], "arm": dr.RATED_ARM[it["regime"]]}


def classify_refusal(r: t1.Refused) -> str:
    """Section 2.4 (4) (the valid set cannot supply the need) against a module-induced drop (MAX_REDRAWS re-draws exhausted
    with listed pairs remaining; brief 33 A0)."""
    if r.reason == t1.RF_NO_VALID_DRAW and len(r.refused) >= t1.MAX_REDRAWS + 1:
        return "module-induced: 20 re-draws refused with listed pairs remaining"
    return f"section 2.4 (4): {r.reason}"


def mode_apply(ns) -> int:
    t0 = time.monotonic()
    if APPLICATIONS.exists() and not ns.force:
        raise SystemExit(f"refusing: {APPLICATIONS.name} exists; the draw is made once (plan section 2.4 (5))")
    if (RUN.exists() or (CACHE_DIR.exists() and any(CACHE_DIR.glob("*.jsonl")))):
        raise SystemExit("refusing: a judge call has been made (a run record or a cache exists); no draw is repeated after any judge call")
    pre = preflight(Path(ns.config))
    payload_hashes = verify_payload_files()
    matrix = load_json(MATRIX)
    sets = net_sets(matrix)
    config = load_json(Path(ns.config))
    arms = assert_arm_seeds(config)
    items, _meta = dr.load_items(dr.input_paths())
    by_id = {it["item_id"]: it for it in items}
    W = World()
    ins = t1.build_parts_inserter(CORPUS, TEMPLATE, VALID)
    rngs = {t: random.Random(s) for t, s in arms.items()}       # K5: one random.Random per arm, passed to every call of that arm
    units: dict[str, dict] = {}
    drops: dict[str, dict] = {}                                  # S3's own drops (candidates leave every population)
    addon_left: dict[str, dict] = {}                             # control items leaving the add-on only
    refusals: Counter = Counter()
    redraws: Counter = Counter()
    authors: dict[str, list[str]] = {}
    guard = dr.guard_texts(items, {p: txt for (_s, p), txt in W.base.items()}, dr.input_paths())

    def store(res: t1.PlantResult, iid: str, arm: str, role: int, placement: int, tag: int, index: int) -> None:
        uid = f"{iid}:{arm}{role}:{placement}"
        packets = render_unit(W, res, uid, with_lines_rows=(arm == "item"))
        rec = res.record()
        for x in res.refused_draws:
            refusals[x["reason"]] += 1
        redraws[str(res.redraws)] += 1
        units[uid] = {"unit_id": uid, "item_id": iid, "regime": by_id[iid]["regime"], "writer": by_id[iid]["writer"], "arm": arm, "role": role, "placement": placement,
                      "stream_tag": tag, "draw_index": index, "day": res.days[0], "author": res.authors[0], "document": res.document,
                      "redraws": res.redraws, "refused_draws": list(res.refused_draws), "composed": res.composed, "delivered": res.delivered,
                      "state_sha256": state_sha256(res, W.base), "record": rec, "packets": packets}

    def pair(iid: str, which, rng: random.Random, exclude=None) -> list[t1.PlantResult]:
        it = by_id[iid]
        if which == "item":
            return ins.plant_pair(payload_of(it), "item", rng, key=iid)
        return ins.plant_pair(payload_of(it), which, rng, key=iid, exclude=tuple(exclude))

    # tag 1: the candidates' item applications, ascending opaque id, two placements in draw order
    cand = sorted(sets["full"])
    for idx, iid in enumerate(cand):
        try:
            res = pair(iid, "item", rngs[1])
        except t1.Refused as r:
            drops[iid] = {"arm": "item", "reason": r.reason, "class": classify_refusal(r), "refused_draws": len(r.refused), "stream_tag": 1}
            continue
        authors[iid] = [x.authors[0] for x in res]
        for p, x in enumerate(res, 1):
            store(x, iid, "item", 0, p, 1, idx)
    # tag 2: the lone lines, ascending item id then role index 1, 2, 3, after every tag-1 draw; exclude = the item's two authors as drawn
    for idx, iid in enumerate(cand):
        if iid in drops:
            continue
        try:
            for role in (0, 1, 2):
                res = pair(iid, role, rngs[2], exclude=authors[iid])
                for p, x in enumerate(res, 1):
                    store(x, iid, "line", role + 1, p, 2, idx)
        except t1.Refused as r:
            drops[iid] = {"arm": f"line{r.what}", "reason": r.reason, "class": classify_refusal(r), "refused_draws": len(r.refused), "stream_tag": 2}
            for uid in [u for u in units if u.startswith(iid + ":")]:
                units.pop(uid)
    # tag 3: the control items' pairs
    ctrl = sorted(sets["controls"])
    for idx, iid in enumerate(ctrl):
        try:
            res = pair(iid, "item", rngs[3])
        except t1.Refused as r:
            drops[iid] = {"arm": "item", "reason": r.reason, "class": classify_refusal(r), "refused_draws": len(r.refused), "stream_tag": 3}
            continue
        authors[iid] = [x.authors[0] for x in res]
        for p, x in enumerate(res, 1):
            store(x, iid, "item", 0, p, 3, idx)
    # tag 4: the same-shape comparison items
    sham = sorted(sets["sham"])
    for idx, iid in enumerate(sham):
        try:
            res = pair(iid, "item", rngs[4])
        except t1.Refused as r:
            drops[iid] = {"arm": "item", "reason": r.reason, "class": classify_refusal(r), "refused_draws": len(r.refused), "stream_tag": 4}
            continue
        for p, x in enumerate(res, 1):
            store(x, iid, "item", 0, p, 4, idx)
    # tag 6: the control items' lone lines, once after every tag-3 pair; exclude = that control item's two authors as drawn
    for idx, iid in enumerate(ctrl):
        if iid in drops:
            continue
        try:
            for role in (0, 1, 2):
                res = pair(iid, role, rngs[6], exclude=authors[iid])
                for p, x in enumerate(res, 1):
                    store(x, iid, "line", role + 1, p, 6, idx)
        except t1.Refused as r:
            addon_left[iid] = {"line": r.what, "reason": r.reason, "class": classify_refusal(r), "refused_draws": len(r.refused)}
            for uid in [u for u in units if u.startswith(iid + ":line")]:
                units.pop(uid)
    counts = unit_counts(units)
    out = {"version": VERSION, "brief": "33 v2.1", "written": now_iso(), "run_tag": RUN_TAG,
           "plan_sha256": pre["plan_sha256"], "preflight": {"pass": pre["pass"], "n_files": pre["n_files"]},
           "module": {"path": "work/checks/stage3_t1.py", "sha256": sha256_file(HERE / "stage3_t1.py")},
           "inputs_sha256": {str(CORPUS.relative_to(PROJECT)): sha256_file(CORPUS), str(TEMPLATE.relative_to(PROJECT)): sha256_file(TEMPLATE),
                             str(VALID.relative_to(PROJECT)): sha256_file(VALID), str(MATRIX.relative_to(PROJECT)): sha256_file(MATRIX), **payload_hashes},
           "arm_seeds": {str(t): s for t, s in arms.items()}, "window": {"days": W.days, "rule": "the corpus span (build_world); units as planted_items"},
           "id_sets": {k: {"n": len(v), "ids_sha256": ids_sha256(v)} for k, v in sets.items()},
           "counts": counts, "expected": EXPECTED_COUNTS, "counts_equal_expected": counts_equal(counts),
           "refused_draws_by_reason": dict(refusals), "redraws": dict(sorted(redraws.items(), key=lambda kv: int(kv[0]))),
           "own_drops": {"n": len(drops), "ids": sorted(drops), "by_reason": dict(Counter(d["class"] for d in drops.values())), "entries": drops,
                         "by_population": by_population(matrix, drops)},
           "addon_left": {"n": len(addon_left), "ids": sorted(addon_left), "entries": addon_left},
           "seconds": round(time.monotonic() - t0), "units": units}
    js = json.dumps(out, indent=1, ensure_ascii=False) + "\n"
    APPLICATIONS.write_text(js, encoding="utf-8")
    h = sha256_file(APPLICATIONS)
    md = applications_md(out, h)
    dr.assert_clean(md, guard)
    APPLICATIONS_MD.write_text(md, encoding="utf-8")
    print(md)
    return 0


def unit_counts(units: Mapping[str, dict]) -> dict:
    c = Counter()
    for u in units.values():
        c[("items" if u["arm"] == "item" else "lines")] += 1
        c[f"{u['regime']}_{'items' if u['arm'] == 'item' else 'lines'}"] += 1
    by_arm = Counter(f"tag{u['stream_tag']}" for u in units.values())
    by_day = Counter(u["day"] for u in units.values())
    by_writer = Counter(f"{u.get('writer')}:{'items' if u['arm'] == 'item' else 'lines'}" for u in units.values())
    return {**{k: c.get(k, 0) for k in EXPECTED_COUNTS}, "by_stream_tag": dict(sorted(by_arm.items())), "by_day": dict(sorted(by_day.items())),
            "by_writer": dict(sorted(by_writer.items())), "units": len(units)}


def counts_equal(counts: Mapping[str, Any]) -> bool:
    return all(counts.get(k) == v for k, v in EXPECTED_COUNTS.items())


def by_population(matrix: Mapping[str, Any], drops: Mapping[str, Any]) -> dict[str, int]:
    out = Counter()
    for iid in drops:
        for p in matrix["items"][iid]["populations"]:
            out[p] += 1
    return dict(out)


def applications_md(out: Mapping[str, Any], h: str) -> str:
    """The record: counts by arm, regime, day and writer against the expected 232 and 564; refusals and next-draw
    substitutions by reason; S3's own drops with reasons; the file's sha256. No item text."""
    c = out["counts"]
    L = [f"# S3 applications (brief 33 A3): the one draw, {out['written']}", "",
         f"`s3-applications-v0.json` sha256 **{h}** (a never-open file: it holds applied document states and the packets). Module `stage3_t1.py` "
         f"{out['module']['sha256'][:8]} (restricted mode, valid draws `inserter-dry-run-v1.json` {out['inputs_sha256']['work/stage3/b3/inserter-dry-run-v1.json'][:8]}); "
         f"corpus {out['inputs_sha256']['work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl'][:8]}; template {out['inputs_sha256']['work/mole-fork/bootstrap/org_template.yaml'][:8]}; "
         f"plan.md {out['plan_sha256'][:8]}; pre-flight {'PASS' if out['preflight']['pass'] else 'FAIL'} {out['preflight']['n_files']} of 26. "
         f"Arm seeds {out['arm_seeds']} (no tag 5). Window: {out['window']['rule']}; days {out['window']['days']}. Wall time {out['seconds']} s.", ""]
    L.append("| count | got | expected |")
    L.append("|---|---|---|")
    for k, v in EXPECTED_COUNTS.items():
        L.append(f"| {k} | {c.get(k)} | {v} |")
    L.append(f"| units | {c['units']} | {EXPECTED_COUNTS['items'] + EXPECTED_COUNTS['lines']} |")
    L.append("")
    L.append(f"Counts equal the plan's: **{out['counts_equal_expected']}**. By stream tag: {c['by_stream_tag']}. By day: {c['by_day']}. By writer: {c['by_writer']}.")
    L.append("")
    L.append(f"Id sets (section 2.5): " + "; ".join(f"{k} {v['n']} ({v['ids_sha256'][:8]})" for k, v in out["id_sets"].items()) + ".")
    L.append("")
    L.append(f"Refused draws at application time, by brief 27's reason class (section 2.4 (3), the module's `_draw_listed`, the next draw of the same stream taken): "
             f"{out['refused_draws_by_reason'] or 'none'}. Re-draws per application: {out['redraws']}.")
    L.append("")
    od = out["own_drops"]
    L.append(f"S3's own drops (section 2.4 (4) and module-induced): **{od['n']}**" + (f"; by reason {od['by_reason']}; by population {od['by_population']}; ids {od['ids']}" if od["n"] else "; every population is as pre-registered (S-S0)") + ".")
    al = out["addon_left"]
    L.append(f"Control items leaving the add-on only (S2's rule for tag 6): **{al['n']}**" + (f"; ids {al['ids']}; entries {al['entries']}" if al["n"] else "") + ".")
    L.append("")
    return "\n".join(L)


# ── render: packets per row, the pre-signal estimate ─────────────────────────────────────────────

def cell_units(app: Mapping[str, Any], view: str, judge: str) -> list[dict]:
    """The units a cell scores, in order: item applications ascending opaque id (placement 1 then 2), then the lone lines."""
    us = sorted(app["units"].values(), key=lambda u: (u["arm"] != "item", u["item_id"], u["role"], u["placement"]))
    out = []
    for u in us:
        if u["arm"] == "line" and view not in PER_AGENT:
            continue
        if view not in u["packets"]:
            raise SystemExit(f"{u['unit_id']} has no packet under {view}")
        out.append(u)
    return out


def output_basis(judge: str, view: str) -> float:
    """B1's output-token basis for Opus 4.8 (its estimate's `opus_output_basis`: O_diff for O_diff, P_author for the per-agent
    rows); `EST_OUTPUT_TOKENS` for Sonnet; brief 09's 250 for Sol."""
    if judge == "opus48":
        b = load_json(PROJECT / "work/stage3/b1/b1-estimate.json")["opus_output_basis"]
        return float(b["O_diff" if view == "O_diff" else "P_author"]["mean"])
    if judge == "sonnet":
        return float(sv.EST_OUTPUT_TOKENS)
    return 250.0


def estimate_cell(units: Sequence[dict], view: str, judge: str) -> dict:
    system = sv.system_prompt(view, 0) if view in ("P_author", "O_diff") else ad.system_prompt(view)
    chars = sum(len(u["packets"][view]["packet"]) for u in units)
    in_tok = (chars + len(units) * len(system)) / sv.EST_CHARS_PER_TOKEN
    out_tok = len(units) * output_basis(judge, view)
    price = jc_mod.CONVERSE_PRICES[MODELS[judge]] if judge == "sol" else jc_mod.PRICES[MODELS[judge]]
    usd = (in_tok * price["input"] + out_tok * price["output"]) / 1e6
    return {"n_calls": len(units), "packet_chars": chars, "system_chars": len(system), "est_input_tokens": round(in_tok), "est_output_tokens": round(out_tok),
            "output_tokens_per_call": output_basis(judge, view), "est_cost_usd": round(usd, 4), "n_truncated": sum(1 for u in units if u["packets"][view]["truncated"])}


def mode_render(ns) -> int:
    app = load_json(APPLICATIONS)
    s2 = load_json(S2)
    bases = {r["cell"]: r for r in s2["h1"]["rows"]}
    addon_per_unit = {}
    for r in s2["h2"]["addon"]["rows"] if isinstance(s2["h2"].get("addon"), dict) and "rows" in s2["h2"]["addon"] else []:
        addon_per_unit[r.get("cell")] = r
    out = {"version": VERSION, "written": now_iso(), "applications_sha256": sha256_file(APPLICATIONS), "rows": {}, "labels_unique": True}
    labels = Counter()
    total = 0.0
    s2_total = 0.0
    for view, judge in ORDER:
        us = cell_units(app, view, judge)
        for u in us:
            labels[(view, u["packets"][view]["label"])] += 1
        e = estimate_cell(us, view, judge)
        ph = hashlib.sha256("\n".join(sorted(sha256_text(u["packets"][view]["packet"]) for u in us)).encode()).hexdigest()
        cell = S2_CELL[(view, judge)]
        basis = float(bases[cell]["basis"])
        n_item = sum(1 for u in us if u["arm"] == "item")
        n_line = len(us) - n_item
        s2_dollars = basis * len(us)
        out["rows"]["|".join((view, judge))] = {"view": view, "judge": judge, "model": MODELS[judge], "n_units": len(us), "n_item_units": n_item, "n_line_units": n_line,
                                                "packets_sha256": ph, "estimate": e, "s2_basis_per_unit": basis, "s2_dollars_at_basis": round(s2_dollars, 4)}
        total += e["est_cost_usd"]
        s2_total += s2_dollars
    out["labels_unique"] = all(v == 1 for v in labels.values())
    out["n_labels"] = len(labels)
    out["pre_signal_total_usd"] = round(total, 2)
    out["s2_total_usd"] = round(s2_total, 2)
    out["s2_figure_usd"] = FIGURE_USD
    out["ratio_to_figure"] = round(total / FIGURE_USD, 3)
    out["escalate"] = total > FIGURE_USD * ESCALATE_RATIO
    out["note"] = ("a pre-signal only: no exact token count exists before a request is sent; the exact count and the re-base are B1's "
                   "(the plan's note of 2026-11-02, item 4)")
    h = write_json(RENDER, out)
    print(json.dumps({k: v for k, v in out.items() if k != "rows"} | {"rows": {k: {"n_units": r["n_units"], "est_cost_usd": r["estimate"]["est_cost_usd"],
                                                                                   "s2_dollars_at_basis": r["s2_dollars_at_basis"], "n_truncated": r["estimate"]["n_truncated"]}
                                                                              for k, r in out["rows"].items()}, "sha256": h}, indent=1))
    return 0


# ── score: the controller ─────────────────────────────────────────────────────────────────────────

def cache_path(view: str, judge: str) -> Path:
    return CACHE_DIR / f"judge-cache.{RUN_TAG}.{view}.{b1.slug(MODELS[judge])}.jsonl"


def dollars_in(path: Path) -> float:
    return round(sum(float(r.get("cost_usd") or 0.0) for r in b1.read_jsonl(path)), 6) if path.exists() else 0.0


def dollars_all() -> dict[str, float]:
    """Every dollar recorded in every S3 cache file, errored records included (B1's `dollars_all`)."""
    per = {"|".join((v, j)): dollars_in(cache_path(v, j)) for v, j in ORDER}
    per["total"] = round(sum(per.values()), 6)
    return per


class Ledger:
    """One spend ledger across every S3 cache: `guard` (the clients' request_guard) raises JudgeAborted when the dollars
    recorded in every cache plus the in-flight units' reserved bases reach the stop; `enter`/`leave` reserve and release
    one unit's basis around its scoring (the reconciliation: a reservation lasts exactly as long as the unit is in flight,
    whatever its retries, so the overshoot is at most `concurrency` bases)."""

    def __init__(self, stop: float, clients: Mapping[str, Any] | None = None):
        self.stop = stop
        self.clients: dict[str, Any] = dict(clients or {})
        self.in_flight = 0
        self.basis = 0.0
        self.aborted: str | None = None

    def recorded(self) -> float:
        """The dollars of every S3 cache: the live clients' totals (their own cache file plus this run) and the other files on disk."""
        live = {k: c.total_spent() for k, c in self.clients.items()}
        disk = {k: v for k, v in dollars_all().items() if k != "total" and k not in live}
        return round(sum(live.values()) + sum(disk.values()), 6)

    def guard(self) -> None:
        rec = self.recorded()
        if rec + self.in_flight * self.basis >= self.stop:
            self.aborted = f"S3 stop: recorded ${rec:.4f} plus {self.in_flight} in-flight units at ${self.basis:.4f} reach ${self.stop:.2f}"
            raise jc_mod.JudgeAborted(self.aborted)

    def enter(self, basis: float) -> None:
        self.basis = basis
        self.in_flight += 1

    def leave(self) -> None:
        self.in_flight -= 1


def sealed_rule(view: str, judge: str) -> dict:
    path, keys = RULE_SOURCE[(view, judge)]
    d = load_json(PROJECT / path)
    for k in keys:
        d = d[k]
    if int(d.get("seed")) != 20261112:
        raise SystemExit(f"refusing: the sealed rule for {view}|{judge} does not carry the tie seed")
    return d


def make_client(view: str, judge: str, ledger: Ledger, concurrency: int = CONCURRENCY, rpm: int = RPM):
    cp = cache_path(view, judge)
    model = MODELS[judge]
    others = round(sum(v for k, v in dollars_all().items() if k not in ("total", "|".join((view, judge)))), 6)
    cap = STOP_USD - others          # the client's own cap: the stop less the dollars already recorded in the other S3 caches
    if view in ("P_author", "O_diff"):
        system, pv_ = sv.system_prompt(view, 0), sv.prompt_version(view, 0)
    else:
        system, pv_ = ad.system_prompt(view), ad.prompt_version(view)
    if judge == "sol":
        jc = jc_mod.BedrockConverseJudge(cp, model, system=system, prompt_version=pv_, concurrency=concurrency, rpm=rpm, max_tokens=MAX_TOKENS[judge],
                                         spend_cap_usd=cap, request_guard=ledger.guard)
    else:
        set_.check_cache(cp, model, prompt_version=pv_)
        jc = jc_mod.JudgeClient(cache_path=cp, concurrency=concurrency, rpm=rpm, model=model, spend_cap_usd=cap, max_tokens=MAX_TOKENS[judge],
                                system=system, prompt_version=pv_, request_guard=ledger.guard)
        want = jc_mod.sha256(system)
        bad = [r.get("cache_key") for r in jc.cache.values() if (r.get("request_params") or {}).get("system_sha256") not in (None, want)
               or (r.get("request_params") or {}).get("output_config") is not None or (r.get("request_params") or {}).get("max_tokens") not in (None, MAX_TOKENS[judge])]
        if bad:
            raise SystemExit(f"refusing: cache {cp.name} holds {len(bad)} record(s) under another prompt, effort or max_tokens")
    ledger.clients["|".join((view, judge))] = jc
    return jc


async def score_units(jc, view: str, units: Sequence[dict], ledger: Ledger, basis: float, concurrency: int = CONCURRENCY) -> tuple[dict, str | None]:
    sem = asyncio.Semaphore(concurrency)
    recs: dict[str, dict] = {}
    aborted: str | None = None

    async def one(u):
        nonlocal aborted
        pk = u["packets"][view]
        if pk["key"] in jc.cache:
            recs[u["unit_id"]] = dict(jc.cache[pk["key"]])
            return
        async with sem:
            ledger.enter(basis)
            try:
                recs[u["unit_id"]] = await jc.score(view, pk["label"], pk["packet"])
            except jc_mod.JudgeAborted as exc:
                aborted = str(exc)
            finally:
                ledger.leave()

    await asyncio.gather(*(one(u) for u in units))
    return recs, aborted


def load_run() -> dict:
    return load_json(RUN) if RUN.exists() else {"version": VERSION, "run_tag": RUN_TAG, "stage_b_started": None, "first_batch": None, "cells": {}, "stopped": None,
                                                "order": ["|".join(c) for c in ORDER]}


def cell_status(app: Mapping[str, Any], view: str, judge: str) -> dict:
    """Completed units from the cache: scored or refused records; errored-only units are not complete."""
    us = cell_units(app, view, judge)
    cp = cache_path(view, judge)
    recs = {}
    for r in b1.read_jsonl(cp) if cp.exists() else []:
        if r.get("outcome") in ("scored", "refused"):
            recs[r["cache_key"]] = r
    errored = Counter()
    for r in b1.read_jsonl(cp) if cp.exists() else []:
        if r.get("outcome") == "errored":
            errored[r["cache_key"]] += 1
    done = [u["unit_id"] for u in us if u["packets"][view]["key"] in recs]
    oc = Counter(recs[u["packets"][view]["key"]]["outcome"] for u in us if u["packets"][view]["key"] in recs)
    return {"n_units": len(us), "completed": len(done), "scored": oc.get("scored", 0), "refused": oc.get("refused", 0),
            "errored_only": sum(1 for u in us if u["packets"][view]["key"] not in recs and u["packets"][view]["key"] in errored),
            "missing": len(us) - len(done), "dollars": dollars_in(cp), "complete": len(done) == len(us)}


def build_scores(app: Mapping[str, Any], run: Mapping[str, Any]) -> dict:
    """The scores file from the caches: one row per unit and cell; the flag at the sealed rule through stage3_thresholds."""
    rows = []
    cells = {}
    for view, judge in ORDER:
        us = cell_units(app, view, judge)
        cp = cache_path(view, judge)
        recs, err = {}, set()
        for r in b1.read_jsonl(cp) if cp.exists() else []:
            if r.get("outcome") in ("scored", "refused"):
                recs[r["cache_key"]] = r
            elif r.get("outcome") == "errored":
                err.add(r["cache_key"])
        rule = sealed_rule(view, judge) if recs else None
        oc = Counter()
        for u in us:
            pk = u["packets"][view]
            r = recs.get(pk["key"])
            if r is None:
                outcome, score, flag = ("errored" if pk["key"] in err else "missing"), None, None
            else:
                outcome, score = r["outcome"], (float(r["score"]) if r.get("outcome") == "scored" and r.get("score") is not None else None)
                tie = pk["author"] if rule["kind"] == "author" else pk["label"]
                flag = bool(th.is_flagged(score, rule, tie)) if score is not None else None
            oc[outcome] += 1
            rows.append({"unit_id": u["unit_id"], "item_id": u["item_id"], "regime": u["regime"], "arm": u["arm"], "role": u["role"], "placement": u["placement"],
                         "view": SCORES_VIEW[view], "judge": judge, "outcome": outcome, "score": score, "flag": flag, "cache_label": pk["label"]})
        cells["|".join((SCORES_VIEW[view], judge))] = {"n_units": len(us), **{k: oc.get(k, 0) for k in ("scored", "refused", "errored", "missing")},
                                                      "rule_kind": rule["kind"] if rule else None, "tie_seed": rule["seed"] if rule else None}
    stopped = run.get("stopped")
    incomplete = {c: {"scored_rows": v["scored"] + v["refused"], "of": v["n_units"]} for c, v in cells.items() if v["scored"] + v["refused"] < v["n_units"]}
    if stopped:
        stopped = {**stopped, "incomplete_rows": incomplete}
    rows_present = [r for r in rows if r["outcome"] != "missing"]
    return {"version": "b3-s3-scores/v0", "run_tag": RUN_TAG, "written": now_iso(), "applications_sha256": sha256_file(APPLICATIONS),
            "cells": cells, "stopped": stopped, "rows": rows_present if stopped else rows}


def write_scores(app: Mapping[str, Any], run: Mapping[str, Any]) -> str:
    return write_json(SCORES, build_scores(app, run))


class RunLock:
    def __enter__(self):
        import os
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise SystemExit(f"refusing: another S3 scoring run holds {LOCK_FILE} (remove it only if no run is alive)")
        os.write(fd, now_iso().encode())
        os.close(fd)
        return self

    def __exit__(self, *exc):
        LOCK_FILE.unlink(missing_ok=True)
        return False


def first_batch_report(app: Mapping[str, Any], recs: Mapping[str, dict], units: Sequence[dict], render: Mapping[str, Any]) -> dict:
    """B1: the realised cost of the first about 20 carrier units from `_usage_tokens` (input and output tokens, retries
    included) against the character-based estimate, the carrier's realised cost per unit against Part 2's basis, the re-base
    (the carrier cell re-based by realised over estimated per unit, every other cell scaled by the same ratio, as B1's
    `rebase`), the re-based total beside $76.62, and refusals. No score or flag aggregate."""
    rs = [recs[u["unit_id"]] for u in units if u["unit_id"] in recs]
    cost = sum(float(r.get("cost_usd") or 0.0) for r in rs)
    n = len(rs)
    key = "|".join((ad.ISO, "opus48"))
    est = render["rows"][key]["estimate"]
    est_per_unit = est["est_cost_usd"] / est["n_calls"]
    real_per_unit = cost / n if n else None
    ratio = (real_per_unit / est_per_unit) if real_per_unit else None
    rebased = {k: round(r["estimate"]["est_cost_usd"] * ratio, 4) for k, r in render["rows"].items()} if ratio else None
    total = round(sum(rebased.values()), 2) if rebased else None
    return {"n_units": n, "unit_ids": [u["unit_id"] for u in units if u["unit_id"] in recs], "outcomes": dict(Counter(r["outcome"] for r in rs)),
            "input_tokens": sum(int(r.get("input_tokens") or 0) for r in rs), "output_tokens": sum(int(r.get("output_tokens") or 0) for r in rs),
            "attempts": sum(len(r.get("attempts") or []) for r in rs), "refused": sum(1 for r in rs if r["outcome"] == "refused"),
            "dollars": round(cost, 6), "realised_per_unit_usd": round(real_per_unit, 6) if real_per_unit else None,
            "estimated_per_unit_usd": round(est_per_unit, 6), "ratio_realised_over_estimated": round(ratio, 4) if ratio else None,
            "part2_basis_per_unit_usd": render["rows"][key]["s2_basis_per_unit"],
            "ratio_realised_over_part2_basis": round(real_per_unit / render["rows"][key]["s2_basis_per_unit"], 4) if real_per_unit else None,
            "rebased_by_cell": rebased, "rebased_total_usd": total, "figure_usd": FIGURE_USD, "stop_usd": STOP_USD,
            "escalate": (total is not None and total > FIGURE_USD * ESCALATE_RATIO), "ts": now_iso()}


async def run_cells(ns, app: Mapping[str, Any], render: Mapping[str, Any], run: dict) -> int:
    ledger = Ledger(STOP_USD)
    bases = {"|".join(c): render["rows"]["|".join(c)]["s2_basis_per_unit"] for c in ORDER}
    for k, (view, judge) in enumerate(ORDER):
        key = "|".join((view, judge))
        st = cell_status(app, view, judge)
        if st["complete"]:
            run["cells"][key] = {**st, "status": "complete", "ts": now_iso()}
            continue
        if k > 0:
            prev = "|".join(ORDER[k - 1])
            if not cell_status(app, *ORDER[k - 1])["complete"]:
                raise SystemExit(f"refusing: cell {prev} is not complete; the view order is enforced")
        us = cell_units(app, view, judge)
        if k == 0 and run.get("first_batch") is None:
            us = [u for u in us if u["arm"] == "item"][:FIRST_BATCH]
            note = "first batch"
        elif k == 0 and not ns.cont:
            raise SystemExit("refusing: the first batch is recorded; the rest runs only with --continue after the coordinator's STATUS line")
        else:
            note = "cell"
        jc = make_client(view, judge, ledger, ns.concurrency, ns.rpm)
        print(f"[{key}] {note}: {len(us)} units; recorded so far ${ledger.recorded():.4f}; stop ${STOP_USD}", file=sys.stderr, flush=True)
        recs, aborted = await score_units(jc, view, us, ledger, bases[key], ns.concurrency)
        jc.batch_log(CACHE_DIR / "judge-batches.jsonl", note=f"{RUN_TAG} {key} {note}" + (" ABORTED" if aborted else ""))
        st = cell_status(app, view, judge)
        run["cells"][key] = {**st, "status": "complete" if st["complete"] else "partial", "ts": now_iso()}
        run["dollars"] = dollars_all()
        if note == "first batch":
            run["first_batch"] = first_batch_report(app, recs, us, render)
            write_json(RUN, run)
            write_scores(app, run)
            fb = run["first_batch"]
            print(json.dumps({"first_batch": {k_: fb[k_] for k_ in fb if k_ not in ("unit_ids", "rebased_by_cell")}, "rebased_by_cell": fb["rebased_by_cell"], "dollars": run["dollars"]}, indent=1))
            print("PAUSED after the first batch: continue with --continue after the coordinator's STATUS line" + (" (ESCALATE: the re-based total exceeds the figure by more than a third)" if fb["escalate"] else ""))
            return 2 if fb["escalate"] else 3
        if aborted:
            run["stopped"] = {"reason": aborted, "cell": key, "ts": now_iso()}
            write_json(RUN, run)
            write_scores(app, run)
            print(json.dumps({"STOPPED": aborted, "cell": key, "status": run["cells"][key], "dollars": run["dollars"]}, indent=1))
            return 1
        print(json.dumps({key: run["cells"][key], "dollars": run["dollars"]}, indent=1), flush=True)
        write_json(RUN, run)
        write_scores(app, run)
        if not st["complete"]:
            run["stopped"] = {"reason": f"cell {key} incomplete after the run ({st['missing']} units without a scored or refused record)", "cell": key, "ts": now_iso()}
            write_json(RUN, run)
            write_scores(app, run)
            return 1
    run["completed"] = now_iso()
    write_json(RUN, run)
    write_scores(app, run)
    print(json.dumps({"complete": True, "cells": {k: v["status"] for k, v in run["cells"].items()}, "dollars": run["dollars"]}, indent=1))
    return 0


def mode_score(ns) -> int:
    preflight(Path(ns.config))
    app = load_json(APPLICATIONS)
    render = load_json(RENDER)
    if render["applications_sha256"] != sha256_file(APPLICATIONS):
        raise SystemExit("refusing: the render record is not of this applications file")
    run = load_run()
    if run.get("stopped") and not ns.cont:
        raise SystemExit(f"refusing: the run is stopped ({run['stopped']['reason']}); the coordinator decides")
    if run["stage_b_started"] is None:
        if CACHE_DIR.exists() and any(CACHE_DIR.glob("*.jsonl")):
            raise SystemExit("refusing: a cache exists before Stage B started")
        run["stage_b_started"] = now_iso()
    write_json(RUN, run)
    with RunLock():
        return asyncio.run(run_cells(ns, app, render, run))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=("apply", "render", "score"))
    ap.add_argument("--config", default=str(CONFIG))
    ap.add_argument("--force", action="store_true", help="apply: overwrite an existing applications file (never after a judge call)")
    ap.add_argument("--continue", dest="cont", action="store_true", help="score: continue after the first batch (the coordinator's STATUS line)")
    ap.add_argument("--concurrency", type=int, default=CONCURRENCY)
    ap.add_argument("--rpm", type=int, default=RPM)
    ns = ap.parse_args(argv)
    if ns.concurrency > CONCURRENCY:
        raise SystemExit(f"concurrency at most {CONCURRENCY}")
    return {"apply": mode_apply, "render": mode_render, "score": mode_score}[ns.mode](ns)


if __name__ == "__main__":
    sys.exit(main())
