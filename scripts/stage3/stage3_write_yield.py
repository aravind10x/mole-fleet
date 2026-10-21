#!/usr/bin/env python3
"""Measured write yield of the class bank on a generated lab corpus, and the re-weight it implies
(brief 07e E3; design v4 section 11.10: tested numbers correct the inferred draw model).

The rung-1 draw model (`stage3_rung1_class.py`) counted task VARIANTS: every item of an agenda
of k ~ U{2,3,4} was assumed to run and to produce one write. Day 1 of `prefix_rw_v1` showed
two to four times fewer writes on two documents than that model predicted. This script reads
what actually happened, per task variant that names a class document:

  * fed      -- how often the variant reached a session ("Next on your agenda: ..." in the
                transcript; the generator feeds agenda items one at a time, so an item drawn
                after the turn cap is never fed and is not observable);
  * wrote    -- how often the session then made a successful content write to that document
                (ownCloud write_file / append_to_file / replace_in_file, exit code 0, by task_id);
  * nonempty -- how often at least one of those writes carried content;
  * empty    -- how often the session's only writes to the document were empty.

From these it calibrates two pooled numbers, f = agenda items fed per session and y = the
share of fed WRITE variants that produced a non-empty write, and reads the EXPECTED non-empty
honest writes per class document per day under a candidate class design as

    E[doc] = sum over write teams of  S_team * (f / n_team) * W[doc][team] * y

with S_team = members * sessions per account-day * presence (sessions observed / nominal),
n_team = the team's pool (shipped tasks + its class tasks under the design) and W the design's
write-variant count. `propose` raises the write counts, one variant at a time on the write team
with the fewest variants per member, until every document clears the target (the brief's 5,
a margin over rung 1's bar of 3); the read-and-act variants are untouched. The result is a
NEW bank version, recorded in rung1-class.md's version table as "pass by construction
(inferred)" on the measured basis; the tested reading is the day-1 stop of prefix_rw_v2.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_write_yield.py \\
        --transcripts <corpus>.transcripts.jsonl --audit <corpus>.jsonl --day 2026-04-06 \\
        --bank-v2 work/mole-fork/bootstrap/benign_task_bank_v2.yaml \\
        --template work/mole-fork/bootstrap/org_template.yaml \\
        --target 5 --out-json ... --out-md ...
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_rung1_class as rc  # noqa: E402

AGENDA_RE = re.compile(r"Next on your agenda: (.*?)\nCarry it out", re.S)
WS_RE = re.compile(r"/work/[a-z0-9.-]+/")
SESSIONS_PER_ACCOUNT_DAY = 2
NOMINAL_ROSTER = 50


# ── reading a corpus ───────────────────────────────────────────────────────────────────────

def fed_items(transcript_row: dict[str, Any]) -> list[str]:
    """The agenda items a session was fed, in order (the user turns that name them)."""
    out = []
    for m in transcript_row.get("messages") or []:
        if m.get("role") != "user":
            continue
        c = m.get("content")
        if not isinstance(c, str):
            continue
        mm = AGENDA_RE.match(c)
        if mm:
            out.append(mm.group(1).strip())
    return out


def variant_key(text: str) -> str:
    """The bank variant behind a fed item: the account's /work/<ws>/ folded back to {ws}."""
    return WS_RE.sub("/work/{ws}/", " ".join(text.split()))


def class_doc_of(text: str) -> str | None:
    for p in rc.DOC_PATHS:
        if p in text:
            return p
    return None


def measure(transcripts: Sequence[dict[str, Any]], audit: Sequence[dict[str, Any]],
            day: str | None = None) -> dict[str, Any]:
    """Per variant naming a class document: fed, wrote, nonempty, empty; per document and role
    the same; the session statistics the calibration needs."""
    tr = [t for t in transcripts if day is None or str(t.get("sim_ts") or "")[:10] == day]
    rows = [r for r in audit if day is None or str(r.get("ts") or "")[:10] == day]
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if (r.get("service") == "owncloud" and r.get("action") in rc.CLASS_WRITE_ACTIONS
                and (r.get("exit_code") or 0) == 0 and rc._class_path(r)):
            by_task[str(r.get("task_id") or "")].append(r)
    variants: dict[str, dict[str, Any]] = {}
    n_fed_total = 0
    capped_fed: list[int] = []
    uncapped_fed: list[int] = []
    writes_total = writes_empty = writes_unexplained = 0
    writes_per_doc: Counter = Counter()
    for t in tr:
        items = fed_items(t)
        n_fed_total += len(items)
        (capped_fed if t.get("aborted_reason") == "max_turns" else uncapped_fed).append(len(items))
        wr = by_task.get(str(t.get("task_id") or ""), [])
        lens_by_doc: dict[str, list[int]] = defaultdict(list)
        for r in wr:
            p = rc._class_path(r)
            lens_by_doc[p].append(len(str((r.get("args") or {}).get("content") or "")))
        named = set()
        for txt in items:
            d = class_doc_of(txt)
            if d is None:
                continue
            named.add(d)
            key = variant_key(txt)
            v = variants.setdefault(key, {"document": d, "role": rc.cd.classify_doc_task(txt, d),
                                          "fed": 0, "wrote": 0, "nonempty": 0, "empty": 0})
            v["fed"] += 1
            lens = lens_by_doc.get(d, [])
            if lens:
                v["wrote"] += 1
                if any(n > 0 for n in lens):
                    v["nonempty"] += 1
                else:
                    v["empty"] += 1
        for p, lens in lens_by_doc.items():
            for n in lens:
                writes_total += 1
                writes_per_doc[p] += 1
                if n == 0:
                    writes_empty += 1
            if p not in named:
                writes_unexplained += len(lens)
    per_doc_role: dict[str, dict[str, dict[str, int]]] = {
        p: {"write": {"fed": 0, "wrote": 0, "nonempty": 0, "empty": 0, "variants": 0},
            "read": {"fed": 0, "wrote": 0, "nonempty": 0, "empty": 0, "variants": 0}} for p in rc.DOC_PATHS}
    for v in variants.values():
        agg = per_doc_role[v["document"]][v["role"]]
        for k in ("fed", "wrote", "nonempty", "empty"):
            agg[k] += v[k]
        agg["variants"] += 1
    wf = sum(a["write"]["fed"] for a in per_doc_role.values())
    wn = sum(a["write"]["nonempty"] for a in per_doc_role.values())
    n_sess = len(tr)
    return {
        "day": day, "sessions": n_sess,
        "sessions_turn_capped": len(capped_fed),
        "items_fed_total": n_fed_total,
        "items_fed_per_session": (n_fed_total / n_sess) if n_sess else 0.0,
        "items_fed_per_session_capped": (sum(capped_fed) / len(capped_fed)) if capped_fed else None,
        "items_fed_per_session_uncapped": (sum(uncapped_fed) / len(uncapped_fed)) if uncapped_fed else None,
        "class_items_fed": sum(v["fed"] for v in variants.values()),
        "write_variants_fed": wf, "write_variants_nonempty": wn,
        "write_yield": (wn / wf) if wf else None,
        "class_writes": writes_total, "class_writes_empty": writes_empty,
        "class_writes_not_named_by_a_fed_item": writes_unexplained,
        "class_writes_per_document": {p: writes_per_doc.get(p, 0) for p in rc.DOC_PATHS},
        "per_document_role": per_doc_role,
        "variants": dict(sorted(variants.items())),
    }


# ── the calibrated expectation and the proposal ────────────────────────────────────────────

def class_counts_per_team(design: Sequence[dict[str, Any]]) -> dict[str, int]:
    """Class tasks (write + read) each team's pool gains under a design."""
    n: Counter = Counter()
    for d in design:
        for t, m in d["write_teams"].items():
            n[t] += m
        for t, m in d["read_teams"].items():
            n[t] += m
    return dict(n)


def expected_writes(design: Sequence[dict[str, Any]], team_sizes: dict[str, int],
                    shipped_sizes: dict[str, int], *, f: float, y: float, presence: float,
                    s: int = SESSIONS_PER_ACCOUNT_DAY) -> dict[str, dict[str, Any]]:
    """E[non-empty honest writes per document per day] under the model in the module docstring,
    per document with its per-team terms."""
    cls = class_counts_per_team(design)
    out = {}
    for d in design:
        terms = {}
        for team, w in d["write_teams"].items():
            n_team = shipped_sizes.get(team, 0) + cls.get(team, 0)
            sess = team_sizes.get(team, 0) * s * presence
            terms[team] = sess * (f / n_team) * w * y if n_team else 0.0
        out[d["path"]] = {"expected": sum(terms.values()), "terms": terms}
    return out


def propose(design: Sequence[dict[str, Any]], team_sizes: dict[str, int],
            shipped_sizes: dict[str, int], *, f: float, y: float, presence: float,
            target: float, s: int = SESSIONS_PER_ACCOUNT_DAY, max_steps: int = 1000
            ) -> list[dict[str, Any]]:
    """A copy of `design` with write counts raised until every document's expectation is at
    least `target` (reads untouched). Each step adds one write variant to the write team of
    the thinnest document that has the fewest variants per member (ties: the larger team), so
    the spread across teams is kept and no one team's pool fills up first."""
    new = [{**d, "write_teams": dict(d["write_teams"]), "read_teams": dict(d["read_teams"])}
           for d in design]
    for _ in range(max_steps):
        exp = expected_writes(new, team_sizes, shipped_sizes, f=f, y=y, presence=presence, s=s)
        thin = [d for d in new if exp[d["path"]]["expected"] < target]
        if not thin:
            return new
        d = min(thin, key=lambda x: exp[x["path"]]["expected"])
        team = min(d["write_teams"], key=lambda t: (d["write_teams"][t] / max(1, team_sizes.get(t, 1)),
                                                     -team_sizes.get(t, 0)))
        d["write_teams"][team] += 1
    raise RuntimeError("propose: target not reached within max_steps")


# ── CLI ────────────────────────────────────────────────────────────────────────────────────

def _load_jsonl(path: str) -> list[dict[str, Any]]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def _f(x: Any) -> str:
    return "-" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))


def render_md(res: dict[str, Any]) -> str:
    m = res["measure"]
    L = [f"# Measured write yield on `{res['corpus']}` day {m['day']} (brief 07e E3; observed, `work/checks/stage3_write_yield.py`)", "",
         f"Sessions {m['sessions']} ({m['sessions_turn_capped']} at the turn cap); agenda items fed per session "
         f"**{_f(m['items_fed_per_session'])}** (turn-capped {_f(m['items_fed_per_session_capped'])}, "
         f"others {_f(m['items_fed_per_session_uncapped'])}); class items fed {m['class_items_fed']}; "
         f"write variants fed {m['write_variants_fed']}, of which with a non-empty write {m['write_variants_nonempty']} "
         f"(**write yield {_f(m['write_yield'])}**); class writes {m['class_writes']} ({m['class_writes_empty']} empty; "
         f"{m['class_writes_not_named_by_a_fed_item']} in sessions whose fed agenda never named that document).", "",
         "| document | role | variants fed | sessions with a write | non-empty | only empty | writes on the document |",
         "|---|---|---|---|---|---|---|"]
    for p, roles in m["per_document_role"].items():
        for role in ("write", "read"):
            a = roles[role]
            L.append(f"| `{p}` | {role} | {a['fed']} | {a['wrote']} | {a['nonempty']} | {a['empty']} | "
                     f"{m['class_writes_per_document'][p] if role == 'write' else ''} |")
    L += ["", "## Per variant (fed at least once)", "", "| variant | document | role | fed | wrote | non-empty | only empty |", "|---|---|---|---|---|---|---|"]
    for k, v in m["variants"].items():
        L.append(f"| {k} | `{v['document']}` | {v['role']} | {v['fed']} | {v['wrote']} | {v['nonempty']} | {v['empty']} |")
    c = res["calibration"]
    L += ["", "## Calibration and the expectation under the current design (inferred from the numbers above)", "",
          f"f = {_f(c['f'])} items fed per session; y = {_f(c['y'])}; presence = {_f(c['presence'])} "
          f"(sessions / nominal {c['nominal_sessions']}); shipped pool sizes {c['shipped_sizes']}; team sizes {c['team_sizes']}.", "",
          "| document | current writes | E current | proposed writes | E proposed |", "|---|---|---|---|---|"]
    for d_cur, d_new in zip(res["design_current"], res["design_proposed"]):
        p = d_cur["path"]
        L.append(f"| `{p}` | {d_cur['write_teams']} ({sum(d_cur['write_teams'].values())}) | "
                 f"{_f(res['expected_current'][p]['expected'])} | {d_new['write_teams']} ({sum(d_new['write_teams'].values())}) | "
                 f"{_f(res['expected_proposed'][p]['expected'])} |")
    L += ["", f"Target: every document at least {res['target']} expected non-empty honest writes per day at fifty "
          f"accounts and two sessions (a margin over rung 1's bar of 3). Write variants: {res['write_variants_current']} "
          f"now, {res['write_variants_proposed']} proposed; read variants unchanged. The proposed design is "
          "'pass by construction (inferred)' on this measured basis (11.10); the tested reading is the day-1 "
          "instrument stop of the restarted prefix."]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    import yaml
    import stage3_rung1_density as r1
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--transcripts", required=True)
    ap.add_argument("--audit", required=True)
    ap.add_argument("--day", default=None)
    ap.add_argument("--bank-v2", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--target", type=float, default=5.0)
    ap.add_argument("--presence", type=float, default=None,
                    help="sessions per nominal slot; default: observed sessions / (50 x 2)")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    ns = ap.parse_args(argv)
    m = measure(_load_jsonl(ns.transcripts), _load_jsonl(ns.audit), ns.day)
    tmpl = yaml.safe_load(open(ns.template, encoding="utf-8"))
    roster = r1.roster_from_template(tmpl)
    team_sizes = dict(Counter(t for _, t in roster))
    shipped = yaml.safe_load(open(ns.bank_v2, encoding="utf-8"))
    shipped_sizes = {t: len(r1.team_tasks(e)) for t, e in shipped.items()}
    nominal = NOMINAL_ROSTER * SESSIONS_PER_ACCOUNT_DAY
    presence = ns.presence if ns.presence is not None else (m["sessions"] / nominal)
    f, y = m["items_fed_per_session"], m["write_yield"] or 0.0
    cur = [{"path": d["path"], "write_teams": dict(d["write_teams"]), "read_teams": dict(d["read_teams"])}
           for d in rc.CLASS]
    exp_cur = expected_writes(cur, team_sizes, shipped_sizes, f=f, y=y, presence=presence)
    new = propose(cur, team_sizes, shipped_sizes, f=f, y=y, presence=presence, target=ns.target)
    exp_new = expected_writes(new, team_sizes, shipped_sizes, f=f, y=y, presence=presence)
    res = {"script": "work/checks/stage3_write_yield.py", "corpus": ns.audit, "measure": m,
           "calibration": {"f": f, "y": y, "presence": presence, "nominal_sessions": nominal,
                           "shipped_sizes": shipped_sizes, "team_sizes": team_sizes},
           "target": ns.target, "design_current": cur, "expected_current": exp_cur,
           "design_proposed": new, "expected_proposed": exp_new,
           "write_variants_current": sum(sum(d["write_teams"].values()) for d in cur),
           "write_variants_proposed": sum(sum(d["write_teams"].values()) for d in new)}
    Path(ns.out_json).write_text(json.dumps(res, indent=1), encoding="utf-8")
    Path(ns.out_md).write_text(render_md(res), encoding="utf-8")
    print(json.dumps({"f": f, "y": y, "presence": presence,
                      "expected_current": {p: round(v["expected"], 2) for p, v in exp_cur.items()},
                      "expected_proposed": {p: round(v["expected"], 2) for p, v in exp_new.items()},
                      "write_variants": [res["write_variants_current"], res["write_variants_proposed"]]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
