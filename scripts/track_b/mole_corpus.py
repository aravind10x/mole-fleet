"""Shared loader and touch table for the Track B part-1 measurements (B0, B1).

Implements `work/mole-fork/protocol/TRACK-B.md` part 1 (commit 0cfe331):

- section 0: unit (account-day = (account, ts[:10]) with >= 1 exit_code == 0 event),
  time ordering (real_ts within a simulated day, the day otherwise);
- section 1: the artefact types and the touch table, as data (`TOUCH_RULES`), and
  `touches(df)` which turns successful audit events into touch rows;
- section 2 (G2, G5 support): ticket / mail / chat / repository records with their text,
  the whole-token tokeniser, the G2 identifier vocabulary and the G5 name matcher;
- section 5: the org-template loader and the induced sub-org (`induce_suborg`);
- the per-corpus argument-key usage table (`key_usage_table`) that section 1 says
  `work/stage2/b1-haystack.md` prints;
- the fork audit loader (`load_fork_audit`, TRACK-B part 2 draft section 2): a fork
  JSONL in the parquet loader's columns, ordered by (day, file order); see
  `FORK_ORDERING_RULE`. Call `touches(df, include_fork_only=True)` on it.

The data directory is untrusted: nothing here executes anything from it; paths are
arguments, and the parquet files are read as data only. Pure functions except the
loaders and the cache helpers.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import random
import re
import string
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------------

CORPORA: tuple[str, ...] = tuple(
    f"{m}_{k}" for m in ("gpt53", "kimi_k26", "deepseek_v4_flash", "qwen36_27b")
    for k in ("single_day", "multiday"))

#: Columns the measurements need (brief: load only these from the large audit files).
AUDIT_COLUMNS: tuple[str, ...] = ("ts", "real_ts", "account", "service", "action", "args",
                                  "exit_code")

#: Artefact types in like-for-like scope (TRACK-B section 1, "Like-for-like scope").
LIKE_TYPES: tuple[str, ...] = ("ticket", "checkpoint", "eval", "secret", "group", "org_record")
#: Types the all-services scope adds (TRACK-B section 1, "all-services scope adds").
ALL_ONLY_TYPES: tuple[str, ...] = ("file", "repo", "mail", "chat")
ALL_TYPES: tuple[str, ...] = LIKE_TYPES + ALL_ONLY_TYPES
SCOPES: tuple[str, ...] = ("likeforlike", "allservices")


def scope_types(scope: str) -> tuple[str, ...]:
    """Artefact types in a scope (TRACK-B section 1)."""
    if scope == "likeforlike":
        return LIKE_TYPES
    if scope == "allservices":
        return ALL_TYPES
    raise ValueError(scope)


#: Ticket id pattern of TRACK-B section 2 (G2 vocabulary) and section 1 (create_issue).
TICKET_ID_RE = re.compile(r"[A-Z][A-Z0-9]*-[0-9]+")
TICKET_ID_AT_START_RE = re.compile(r"^\s*([A-Z][A-Z0-9]*-[0-9]+)(?![A-Za-z0-9_-])")
#: Post-hoc sensitivity v1 (NOT pre-registered; errata items 1, 2, 3, 12): case-insensitive
#: `<prefix>-<N>` with prefix `[A-Za-z][A-Za-z0-9]*` at the start of `name`.
TICKET_ID_AT_START_RE_V1 = re.compile(r"^\s*([A-Za-z][A-Za-z0-9]*-[0-9]+)(?![A-Za-z0-9_-])")

#: Post-hoc sensitivity switch (off = the literal, pre-registered implementation).
SENSITIVITY: dict[str, bool] = {"v1": False}


def set_sensitivity_v1(on: bool) -> None:
    """Switch post-hoc sensitivity v1 on or off (process-wide). It turns on together:
    (1) windows in active corpus days, (2) case-insensitive create_issue id, (3) `ticket_id`
    (and create_issue `issue_id` / `identifier`) as ticket keys on writes, (4) one trailing
    `.` or `:` stripped from tokens before G2 identifier matching."""
    SENSITIVITY["v1"] = bool(on)


def sens_v1() -> bool:
    return SENSITIVITY["v1"]


def create_issue_ids(args: dict) -> list[str]:
    """Explicit ticket ids of a create_issue (section 1; v1 adds issue_id / identifier)."""
    out: list[str] = []
    name = args.get("name")
    rx = TICKET_ID_AT_START_RE_V1 if sens_v1() else TICKET_ID_AT_START_RE
    if isinstance(name, str):
        m = rx.match(name)
        if m:
            out.append(m.group(1))
    if sens_v1():
        for k in ("issue_id", "identifier"):
            v = _scalar(args.get(k))
            if v is not None:
                out.append(v)
    return list(dict.fromkeys(out))


V1_EXTRA_KEYS: dict[tuple[str, str], tuple[str, ...]] = {
    ("plane", "add_comment"): ("issue_id", "ticket_id"),
    ("plane", "update_issue"): ("issue_id", "ticket_id"),
    ("plane", "transition_issue"): ("issue_id", "ticket_id"),
}

#: Arguments that name the caller are never an artefact (TRACK-B section 1, last line).
CALLER_KEYS: frozenset[str] = frozenset({"account", "sender", "actor", "user", "from_user"})


# ----------------------------------------------------------------------------------
# Section 1: the touch table as data
# ----------------------------------------------------------------------------------

@dataclass(frozen=True)
class TouchRule:
    """One row of the TRACK-B section 1 touch table.

    `mode` says how the artefact value is read from the arguments:
      first      the value of the first key of `keys` that is present (key alternatives)
      tuple      every key of `keys` must be present; value = the tuple (repository objects)
      sha256     sha256 of the first present key's string (submit_eval config)
      name_id    explicit `<PREFIX>-<N>` id at the start of `name` (create_issue), else none
      recipients each recipient local part of `to` is one artefact (send_email)
    `sub` namespaces sub-kinds of one type whose identities are different objects
    (e.g. repository paths vs merge requests, chat channels vs DMs, mailboxes vs messages).
    """
    service: str
    action: str
    kind: str                      # write | read | container
    keys: tuple[str, ...]
    type: str
    scope: str                     # likeforlike | allservices
    mode: str = "first"
    sub: str = ""
    fork_only: bool = False
    meta_keys: tuple[str, ...] = ()   # fork erratum: keys read from `result_meta`


def _r(service: str, action: str, kind: str, keys: Sequence[str], typ: str, *,
       mode: str = "first", sub: str = "", fork_only: bool = False,
       meta_keys: Sequence[str] = ()) -> TouchRule:
    scope = "likeforlike" if typ in LIKE_TYPES else "allservices"
    return TouchRule(service, action, kind, tuple(keys), typ, scope, mode, sub, fork_only,
                     tuple(meta_keys))


TOUCH_RULES: tuple[TouchRule, ...] = (
    # ticket / plane
    _r("plane", "add_comment", "write", ["issue_id"], "ticket"),
    _r("plane", "update_issue", "write", ["issue_id"], "ticket"),
    _r("plane", "transition_issue", "write", ["issue_id"], "ticket"),
    _r("plane", "create_issue", "write", ["name"], "ticket", mode="name_id"),
    _r("plane", "get_issue", "read", ["issue_id", "ticket_id"], "ticket"),
    _r("plane", "list_comments", "read", ["issue_id"], "ticket"),
    _r("plane", "list_issues", "container", ["project_id", "project"], "ticket"),
    # checkpoint / model_registry
    _r("model_registry", "tag_approved", "write", ["checkpoint_id", "ckpt_id"], "checkpoint"),
    _r("model_registry", "deploy", "write", ["checkpoint_id"], "checkpoint"),
    _r("model_registry", "ensure_checkpoint", "write", ["checkpoint_id"], "checkpoint"),
    _r("model_registry", "get_checkpoint", "read", ["checkpoint_id", "ckpt_id"], "checkpoint"),
    _r("model_registry", "download_weights", "read", ["checkpoint_id"], "checkpoint"),
    _r("model_registry", "list_checkpoints", "container", ["model_id"], "checkpoint"),
    _r("model_registry", "latest_approved", "container", ["model_id"], "checkpoint"),
    _r("model_registry", "list_deployments", "container", ["model_id"], "checkpoint"),
    # eval job / config / eval_server
    _r("eval_server", "submit_eval", "write", ["eval_config", "config"], "eval", mode="sha256",
       sub="config"),
    _r("eval_server", "update_config", "write", ["config_id"], "eval", sub="config_id",
       fork_only=True),
    _r("eval_server", "create_config", "write", ["config_id"], "eval", sub="config_id",
       fork_only=True),
    _r("eval_server", "cancel_job", "write", ["job_id"], "eval", sub="job", fork_only=True),
    _r("eval_server", "get_job", "read", ["job_id"], "eval", sub="job"),
    _r("eval_server", "get_config", "read", ["config_id"], "eval", sub="config_id",
       fork_only=True),
    _r("eval_server", "list_jobs", "container", [], "eval"),
    _r("eval_server", "list_configs", "container", [], "eval"),
    _r("eval_server", "baseline", "container", [], "eval"),
    _r("eval_server", "recent_logs", "container", [], "eval"),
    # secret / secrets_store
    _r("secrets_store", "rotate", "write", ["key", "name"], "secret"),
    _r("secrets_store", "set_access_policy", "write", ["key", "name"], "secret"),
    _r("secrets_store", "read", "read", ["key", "name"], "secret"),
    _r("secrets_store", "get_meta", "read", ["key", "name"], "secret"),
    _r("secrets_store", "get_policy", "read", ["key", "name"], "secret"),
    _r("secrets_store", "list_keys", "container", [], "secret"),
    # group / org
    _r("org", "add_group_member", "write", ["group"], "group"),
    _r("org", "list_team", "read", ["group", "team"], "group"),
    _r("org", "list_directory", "container", [], "group"),
    _r("org", "find_approvers", "container", [], "group"),
    # org record / org: the person looked up, `id` else `account`
    _r("org", "lookup_person", "read", ["id", "account"], "org_record"),
    # ---- all-services scope adds ----
    # file / owncloud
    _r("owncloud", "write_file", "write", ["path"], "file"),
    _r("owncloud", "mkdir", "write", ["path"], "file"),
    _r("owncloud", "delete", "write", ["path"], "file"),
    _r("owncloud", "share", "write", ["path"], "file"),
    _r("owncloud", "public_link", "write", ["path"], "file"),
    _r("owncloud", "read_file", "read", ["path"], "file"),
    _r("owncloud", "read_bytes", "read", ["path"], "file"),
    _r("owncloud", "exists", "read", ["path"], "file"),
    _r("owncloud", "list_dir", "container", ["path"], "file"),
    _r("owncloud", "dir_size", "container", ["path"], "file"),
    # repository object / gitlab
    _r("gitlab", "commit", "write", ["project", "path"], "repo", mode="tuple", sub="path"),
    _r("gitlab", "open_mr", "write", ["project", "source"], "repo", mode="tuple", sub="branch"),
    _r("gitlab", "approve_mr", "write", ["project", "mr_iid"], "repo", mode="tuple", sub="mr"),
    _r("gitlab", "merge_mr", "write", ["project", "mr_iid"], "repo", mode="tuple", sub="mr"),
    _r("gitlab", "force_push", "write", ["project"], "repo", mode="tuple", sub="project"),
    _r("gitlab", "read_file", "read", ["project", "path"], "repo", mode="tuple", sub="path"),
    _r("gitlab", "get_mr", "read", ["project", "mr_iid"], "repo", mode="tuple", sub="mr"),
    _r("gitlab", "list_files", "container", [], "repo"),
    _r("gitlab", "list_mrs", "container", [], "repo"),
    _r("gitlab", "list_projects", "container", [], "repo"),
    _r("gitlab", "project_exists", "container", [], "repo"),
    # mail thread / email
    _r("email", "send_email", "write", ["to"], "mail", mode="recipients", sub="mailbox"),
    _r("email", "reply_email", "write", ["message_id"], "mail", sub="message"),
    _r("email", "forward_email", "write", ["message_id"], "mail", sub="message"),
    # chat channel / DM / rocketchat
    _r("rocketchat", "post_message", "write", ["channel", "room_name"], "chat", sub="channel"),
    _r("rocketchat", "send_direct_message", "write", ["recipient", "peer"], "chat", sub="dm"),
    _r("rocketchat", "channel_history", "read", ["channel", "room_name"], "chat", sub="channel"),
    _r("rocketchat", "im_history", "read", ["recipient"], "chat", sub="dm"),
    _r("rocketchat", "list_channels", "container", [], "chat"),
    _r("rocketchat", "list_users", "container", [], "chat"),
)

RULES_BY_ACTION: dict[tuple[str, str], TouchRule] = {(r.service, r.action): r for r in TOUCH_RULES}

#: `create_issue`'s created ticket in the fork's `result_meta`. The part 2 draft erratum
#: names `result_meta.issue_id`; the fork corpora (warmup_clean, pilot_a_01, prefix_v1)
#: carry the created ticket only under `result_meta.id` on create_issue (`issue_id`
#: occurs on add_comment only), so `issue_id` is read first, then `id`.
CREATE_ISSUE_META_KEYS: tuple[str, ...] = ("issue_id", "id")

#: Fork touch table (TRACK-B part 2 draft section 2, dated erratum to part 1 section 1
#: for fork corpora). (service, action) -> the complete rule list for that action in fork
#: mode; actions not listed keep their part 1 rule. `meta` mode reads `result_meta`;
#: `first_or_meta` reads the args keys, else `result_meta`.
FORK_ERRATUM_RULES: dict[tuple[str, str], tuple[TouchRule, ...]] = {
    ("plane", "create_issue"): (
        RULES_BY_ACTION[("plane", "create_issue")],
        _r("plane", "create_issue", "write", [], "ticket", mode="meta",
           meta_keys=CREATE_ISSUE_META_KEYS, fork_only=True)),
    ("eval_server", "submit_eval"): (
        RULES_BY_ACTION[("eval_server", "submit_eval")],
        _r("eval_server", "submit_eval", "write", ["config_id"], "eval", sub="config_id",
           fork_only=True),
        _r("eval_server", "submit_eval", "write", ["checkpoint_id"], "checkpoint",
           fork_only=True),
        _r("eval_server", "submit_eval", "write", [], "eval", sub="job", mode="meta",
           meta_keys=["job_id"], fork_only=True)),
    ("eval_server", "create_config"): (
        _r("eval_server", "create_config", "write", ["config_id"], "eval", sub="config_id",
           mode="first_or_meta", meta_keys=["config_id"], fork_only=True),),
    ("eval_server", "update_config"): (
        _r("eval_server", "update_config", "write", ["config_id"], "eval", sub="config_id",
           mode="first_or_meta", meta_keys=["config_id"], fork_only=True),),
    ("model_registry", "register_checkpoint"): (
        _r("model_registry", "register_checkpoint", "write", [], "checkpoint", mode="meta",
           meta_keys=["checkpoint_id"], fork_only=True),),
    ("eval_server", "run_reference_suite"): (
        _r("eval_server", "run_reference_suite", "write", ["checkpoint_id"], "checkpoint",
           fork_only=True),),
    ("eval_server", "redeploy"): (
        _r("eval_server", "redeploy", "container", [], "eval", fork_only=True),),
    ("model_registry", "get_deployed"): (
        _r("model_registry", "get_deployed", "container", [], "checkpoint", fork_only=True),),
}


def rules_for(service: str, action: str, fork_erratum: bool = False) -> tuple[TouchRule, ...]:
    """Touch rules of one action: part 1, or the fork erratum list in fork mode."""
    if fork_erratum and (service, action) in FORK_ERRATUM_RULES:
        return FORK_ERRATUM_RULES[(service, action)]
    r = RULES_BY_ACTION.get((service, action))
    return (r,) if r is not None else ()


# ----------------------------------------------------------------------------------
# Loading and argument parsing (section 0)
# ----------------------------------------------------------------------------------

def audit_path(data_dir: str | Path, corpus: str) -> Path:
    return Path(data_dir) / "data" / "audit" / corpus / "0000.parquet"


def labels_path(data_dir: str | Path, corpus: str) -> Path:
    return Path(data_dir) / "data" / "labels" / corpus / "0000.parquet"


def load_audit(data_dir: str | Path, corpus: str,
               columns: Sequence[str] = AUDIT_COLUMNS, successful_only: bool = True
               ) -> pd.DataFrame:
    """Load a corpus audit parquet (data only), keeping `columns`.

    TRACK-B section 0: only successful events (`exit_code == 0`) are read by every
    generator, so by default the filter is pushed into the parquet read.
    """
    cols = list(dict.fromkeys(list(columns) + (["exit_code"] if successful_only else [])))
    filters = [("exit_code", "==", 0)] if successful_only else None
    df = pd.read_parquet(audit_path(data_dir, corpus), columns=cols, filters=filters)
    return df.reset_index(drop=True)


#: Fork audit (JSONL) ordering rule, recorded in every fork output.
FORK_ORDERING_RULE = (
    "fork ordering rule: within a simulated day (ts[:10]) events are ordered by their position "
    "in the append-ordered audit file (the `real_ts` column of load_fork_audit is the 0-based "
    "event index in the file; the generator's own real_ts is kept as `real_ts_raw` and not "
    "used, because it is not monotone within many fork account-days); days are ordered by "
    "date and indexed by the rank of the date among the corpus's dates")


def load_fork_audit(path: str | Path) -> pd.DataFrame:
    """Load a fork audit JSONL (one JSON event per line) into the parquet loader's columns.

    Output columns: `ts, real_ts, account, service, action, args, exit_code` (as
    `load_audit` yields; `args` is the event's dict, which `parse_args_one` accepts), plus
    `real_ts_raw` (the generator's wall-clock `real_ts`, not used for ordering), `line`
    (1-based line number) and `result_meta` (dict; read by the fork touch erratum,
    `touches(..., fork_erratum=True)`). All events are kept (failures too); `touches()`,
    `records()` and `account_days()` filter on `exit_code == 0` themselves.

    Ordering (`FORK_ORDERING_RULE`): the released-corpus code orders events by
    (day, real_ts); in the fork `real_ts` is not monotone within an account-day, while
    the file is append-ordered and `ts` is non-decreasing in file order within every
    account-day. So `real_ts` here is the 0-based event index in the file, and the
    existing `okey = day_rel * ORDER_DAY_SCALE + real_ts` orders by (day, file order).
    The day index is the rank of the date (`generators.build_index(..., day_rank=True)`).
    Diagnostics on the ordering are in `df.attrs["fork_ordering"]`.

    The file is data only: blank lines are skipped, a line that is not a JSON object
    raises ValueError naming the line.
    """
    rows: list[tuple] = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: not JSON ({exc})") from None
            if not isinstance(e, dict):
                raise ValueError(f"{path}:{lineno}: not a JSON object")
            a = e.get("args")
            if a is None:
                a = {}
            ec = e.get("exit_code")
            rm = e.get("result_meta")
            rows.append((str(e.get("ts") or ""), e.get("real_ts"), e.get("account"),
                         e.get("service"), e.get("action"), a,
                         int(ec) if ec is not None else -1, lineno,
                         rm if isinstance(rm, dict) else {}))
    n = len(rows)
    if n >= ORDER_DAY_SCALE:
        raise ValueError("fork audit too long for the (day, file order) key")
    df = pd.DataFrame({
        "ts": [r[0] for r in rows],
        "real_ts": np.arange(n, dtype=np.float64),
        "account": [r[2] for r in rows],
        "service": [r[3] for r in rows],
        "action": [r[4] for r in rows],
        "args": [r[5] for r in rows],
        "exit_code": np.array([r[6] for r in rows], dtype=np.int64),
        "real_ts_raw": pd.to_numeric(pd.Series([r[1] for r in rows], dtype=object),
                                     errors="coerce").to_numpy(np.float64),
        "line": np.array([r[7] for r in rows], dtype=np.int64),
        "result_meta": [r[8] for r in rows],
    })
    df.attrs["fork_ordering"] = fork_ordering_diagnostics(df)
    return df


def fork_ordering_diagnostics(df: pd.DataFrame) -> dict[str, Any]:
    """Checks behind the fork ordering rule, over successful events: per account-day,
    whether `ts` and `real_ts_raw` are non-decreasing in file order; whether the days
    are contiguous blocks in file order; how often `ts` decreases in file order overall
    (across accounts, sessions interleave)."""
    ok = df[df["exit_code"] == 0]
    day = ok["ts"].astype(str).str[:10]
    ts_bad = rt_bad = n_ad = 0
    for _, g in ok.groupby([ok["account"], day], sort=False):
        n_ad += 1
        ts_bad += int((g["ts"].to_numpy()[1:] < g["ts"].to_numpy()[:-1]).any())
        r = g["real_ts_raw"].to_numpy()
        rt_bad += int((r[1:] < r[:-1]).any())
    alld = df["ts"].astype(str).str[:10].to_numpy()
    tsa = df["ts"].astype(str).to_numpy()
    return {
        "rule": FORK_ORDERING_RULE,
        "n_events": int(len(df)), "n_success_events": int(len(ok)),
        "n_account_days": n_ad,
        "account_days_ts_non_monotone_in_file_order": ts_bad,
        "account_days_real_ts_raw_non_monotone_in_file_order": rt_bad,
        "share_account_days_real_ts_raw_non_monotone": (rt_bad / n_ad) if n_ad else float("nan"),
        "day_decreases_in_file_order": int((alld[1:] < alld[:-1]).sum()),
        "ts_decreases_in_file_order_all_accounts": int((tsa[1:] < tsa[:-1]).sum()),
    }


def load_labels(data_dir: str | Path, corpus: str) -> pd.DataFrame:
    """Load a corpus label parquet (`account, date, scenario, outcome, confidence, judge`)."""
    return pd.read_parquet(labels_path(data_dir, corpus))


def parse_args_one(s: Any) -> tuple[dict, bool]:
    """Parse one `args` cell: json.loads, then ast.literal_eval, then {}.

    Returns (dict, failed). Non-dict results count as failures and become {}.
    """
    if isinstance(s, dict):
        return s, False
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return {}, False
    try:
        o = json.loads(s)
    except Exception:
        try:
            o = ast.literal_eval(s)
        except Exception:
            return {}, True
    if not isinstance(o, dict):
        return {}, True
    return o, False


def parse_args_column(col: Iterable[Any]) -> tuple[list[dict], int]:
    """Parse an `args` column once; returns (dicts, number of failures)."""
    out: list[dict] = []
    fails = 0
    for s in col:
        o, f = parse_args_one(s)
        fails += f
        out.append(o)
    return out, fails


def key_usage_table(df: pd.DataFrame, parsed: Sequence[dict] | None = None
                    ) -> dict[str, Counter]:
    """`service.action` -> Counter of argument keys over successful events (section 1)."""
    if parsed is None:
        parsed, _ = parse_args_column(df["args"])
    ok = (df["exit_code"].to_numpy() == 0) if "exit_code" in df else np.ones(len(df), bool)
    out: dict[str, Counter] = defaultdict(Counter)
    for s, a, o, good in zip(df["service"], df["action"], parsed, ok):
        if good:
            c = out[f"{s}.{a}"]
            c["__events__"] += 1
            c.update(o.keys())
    return dict(out)


# ----------------------------------------------------------------------------------
# Section 0: days and ordering
# ----------------------------------------------------------------------------------

CACHE_VERSION = "tb1-v2"   # bump when touches()/records() change
ORDER_DAY_SCALE = 1e8  # okey = day_rel * 1e8 + real_ts; real_ts must stay below this


def day_of(ts: pd.Series) -> pd.Series:
    """Simulated day `ts[:10]` (section 0)."""
    return ts.astype(str).str[:10]


def sim_minutes(ts: pd.Series) -> np.ndarray:
    """Simulated minutes since midnight of `ts` (used by G4's |delta ts| <= tau)."""
    s = ts.astype(str)
    h = s.str[11:13].astype(float)
    m = s.str[14:16].astype(float)
    sec = pd.to_numeric(s.str[17:].str.rstrip("Z"), errors="coerce").fillna(0.0)
    return (h * 60.0 + m + sec / 60.0).to_numpy()


def day_ordinal(days: Iterable[str]) -> np.ndarray:
    return np.array([date.fromisoformat(d).toordinal() for d in days], dtype=np.int64)


# ----------------------------------------------------------------------------------
# Section 1: touches(df)
# ----------------------------------------------------------------------------------

def _scalar(v: Any) -> str | None:
    """String identity of an argument value: exact string after stripping whitespace."""
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return None
    s = str(v).strip()
    return s or None


def _recipients(v: Any) -> list[str]:
    """Recipient local parts of an email `to` (list, or comma/semicolon separated)."""
    items: list[str] = []
    if isinstance(v, list):
        for x in v:
            items.extend(_recipients(x))
        return items
    if v is None:
        return items
    for part in re.split(r"[,;]", str(v)):
        part = part.strip()
        m = re.search(r"<([^>]+)>", part)
        if m:
            part = m.group(1).strip()
        if not part:
            continue
        local = part.split("@", 1)[0].strip()
        if local:
            items.append(local)
    return items


def _meta_first(meta: dict | None, keys: Sequence[str]) -> list[str]:
    if not isinstance(meta, dict):
        return []
    for k in keys:
        v = _scalar(meta.get(k))
        if v is not None:
            return [v]
    return []


def rule_values(rule: TouchRule, args: dict, caller: str, meta: dict | None = None
                ) -> list[str]:
    """Artefact values named by one event under one touch rule (section 1; `meta` is the
    event's `result_meta`, read only by the fork erratum modes `meta` / `first_or_meta`)."""
    vals: list[str] = []
    keys = rule.keys
    if sens_v1():
        keys = V1_EXTRA_KEYS.get((rule.service, rule.action), keys)
    if rule.mode == "first":
        for k in keys:
            if k in args:
                v = _scalar(args.get(k))
                if v is not None:
                    vals.append(v)
                    break
    elif rule.mode == "tuple":
        parts = [_scalar(args.get(k)) for k in rule.keys]
        if all(p is not None for p in parts):
            vals.append("\t".join(parts))          # type: ignore[arg-type]
    elif rule.mode == "sha256":
        for k in rule.keys:
            v = args.get(k)
            if isinstance(v, str):
                vals.append(hashlib.sha256(v.encode("utf-8")).hexdigest())
                break
            if v is not None:
                vals.append(hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest())
                break
    elif rule.mode == "name_id":
        vals.extend(create_issue_ids(args))
    elif rule.mode == "recipients":
        vals.extend(_recipients(args.get("to")))
    elif rule.mode == "meta":
        vals.extend(_meta_first(meta, rule.meta_keys))
    elif rule.mode == "first_or_meta":
        for k in keys:
            v = _scalar(args.get(k)) if k in args else None
            if v is not None:
                vals.append(v)
                break
        if not vals:
            vals.extend(_meta_first(meta, rule.meta_keys))
    else:
        raise ValueError(rule.mode)
    if rule.type == "org_record":
        # "the person looked up, never the caller"
        vals = [v for v in vals if v != caller]
    return list(dict.fromkeys(vals))


TOUCH_COLUMNS = ["account", "day", "real_ts", "ts", "type", "artefact", "kind", "service",
                 "action", "ev", "sub"]


def touches(df: pd.DataFrame, parsed: Sequence[dict] | None = None,
            include_fork_only: bool = False, fork_erratum: bool = False) -> pd.DataFrame:
    """Touch rows of successful events (TRACK-B section 1).

    Input: audit rows with `ts, real_ts, account, service, action, args, exit_code`
    (`parsed` = the already-parsed args, aligned with df). Output columns
    `account, day, real_ts, ts, type, artefact, kind, service, action, ev` where `ev`
    is the row index in `df` and `sub` the sub-kind namespace of the rule (an artefact
    instance is identified by (type, sub, artefact)). `kind` is write | read | container;
    container rows are not touches (section 1) and are kept only for G2-loose
    (`list_issues`). Container actions without an argument key emit nothing. Rules the
    table marks "fork only" are skipped unless `include_fork_only` (released corpora).
    `fork_erratum` (fork corpora; implies `include_fork_only`) applies the part 2 draft's
    fork touch table (`FORK_ERRATUM_RULES`), which reads `df["result_meta"]`; one touch
    row per distinct (event, type, sub, kind, value).
    """
    if fork_erratum:
        return _touches_fork(df, parsed)
    if parsed is None:
        parsed, _ = parse_args_column(df["args"])
    svc = df["service"].to_numpy()
    act = df["action"].to_numpy()
    acc = df["account"].to_numpy()
    ok = (df["exit_code"].to_numpy() == 0) if "exit_code" in df else np.ones(len(df), bool)
    rows_ev: list[int] = []
    rows_type: list[str] = []
    rows_val: list[str] = []
    rows_kind: list[str] = []
    rows_sub: list[str] = []
    for i in range(len(df)):
        if not ok[i]:
            continue
        rule = RULES_BY_ACTION.get((svc[i], act[i]))
        if rule is None or not rule.keys or (rule.fork_only and not include_fork_only):
            continue
        for v in rule_values(rule, parsed[i], acc[i]):
            rows_ev.append(i)
            rows_type.append(rule.type)
            rows_val.append(v)
            rows_kind.append(rule.kind)
            rows_sub.append(rule.sub)
    ev = np.asarray(rows_ev, dtype=np.int64)
    out = pd.DataFrame({
        "account": acc[ev] if len(ev) else np.array([], dtype=object),
        "day": day_of(df["ts"]).to_numpy()[ev] if len(ev) else np.array([], dtype=object),
        "real_ts": df["real_ts"].to_numpy()[ev] if len(ev) else np.array([], dtype=float),
        "ts": df["ts"].astype(str).to_numpy()[ev] if len(ev) else np.array([], dtype=object),
        "type": rows_type, "artefact": rows_val, "kind": rows_kind,
        "service": svc[ev] if len(ev) else np.array([], dtype=object),
        "action": act[ev] if len(ev) else np.array([], dtype=object),
        "ev": ev, "sub": rows_sub,
    })
    return out[TOUCH_COLUMNS]


def _touches_fork(df: pd.DataFrame, parsed: Sequence[dict] | None) -> pd.DataFrame:
    """`touches()` under the fork erratum table (fork-only rules included)."""
    if parsed is None:
        parsed, _ = parse_args_column(df["args"])
    svc = df["service"].to_numpy()
    act = df["action"].to_numpy()
    acc = df["account"].to_numpy()
    ok = (df["exit_code"].to_numpy() == 0) if "exit_code" in df else np.ones(len(df), bool)
    metas = df["result_meta"].to_numpy() if "result_meta" in df else [None] * len(df)
    rows: list[tuple[int, str, str, str, str]] = []
    for i in range(len(df)):
        if not ok[i]:
            continue
        seen: set[tuple[str, str, str, str]] = set()
        for rule in rules_for(svc[i], act[i], fork_erratum=True):
            if not rule.keys and not rule.meta_keys:
                continue
            for v in rule_values(rule, parsed[i], acc[i], metas[i]):
                k = (rule.type, rule.sub, rule.kind, v)
                if k not in seen:
                    seen.add(k)
                    rows.append((i, rule.type, v, rule.kind, rule.sub))
    ev = np.asarray([r[0] for r in rows], dtype=np.int64)
    out = pd.DataFrame({
        "account": acc[ev] if len(ev) else np.array([], dtype=object),
        "day": day_of(df["ts"]).to_numpy()[ev] if len(ev) else np.array([], dtype=object),
        "real_ts": df["real_ts"].to_numpy()[ev] if len(ev) else np.array([], dtype=float),
        "ts": df["ts"].astype(str).to_numpy()[ev] if len(ev) else np.array([], dtype=object),
        "type": [r[1] for r in rows], "artefact": [r[2] for r in rows],
        "kind": [r[3] for r in rows],
        "service": svc[ev] if len(ev) else np.array([], dtype=object),
        "action": act[ev] if len(ev) else np.array([], dtype=object),
        "ev": ev, "sub": [r[4] for r in rows],
    })
    return out[TOUCH_COLUMNS]


def account_days(df: pd.DataFrame) -> pd.DataFrame:
    """Account-days (section 0): distinct (account, ts[:10]) with an exit_code == 0 event."""
    sub = df if "exit_code" not in df else df[df["exit_code"] == 0]
    ad = pd.DataFrame({"account": sub["account"].to_numpy(), "day": day_of(sub["ts"]).to_numpy()})
    return ad.drop_duplicates().sort_values(["day", "account"]).reset_index(drop=True)


# ----------------------------------------------------------------------------------
# Section 2 (G2, G5): records, tokeniser, vocabulary, names
# ----------------------------------------------------------------------------------

def _build_separator_class() -> re.Pattern[str]:
    keep = set("-_./:")
    seps = set(string.whitespace) | (set(string.punctuation) - keep)
    for cp in range(0x80, 0x10000):
        ch = chr(cp)
        cat = unicodedata.category(ch)
        if (cat.startswith("P") or cat.startswith("Z") or ch.isspace()) and ch not in keep:
            seps.add(ch)
    # compress into ranges
    cps = sorted(ord(c) for c in seps)
    parts: list[str] = []
    start = prev = cps[0]
    for c in cps[1:] + [None]:  # type: ignore[list-item]
        if c is not None and c == prev + 1:
            prev = c
            continue
        if start == prev:
            parts.append(re.escape(chr(start)))
        else:
            parts.append(f"{re.escape(chr(start))}-{re.escape(chr(prev))}")
        if c is not None:
            start = prev = c
    return re.compile("[" + "".join(parts) + "]+")


SEPARATORS: re.Pattern[str] = _build_separator_class()


def tokenize(text: str) -> list[str]:
    """Whole tokens: split on whitespace and punctuation except - _ . / : (section 2, G2)."""
    if not text:
        return []
    return [t for t in SEPARATORS.split(text) if t]


def token_candidates(tokens: Iterable[str]) -> set[str]:
    """Strings an identifier may equal: each token and each `/`-separated path component."""
    out: set[str] = set()
    for t in tokens:
        out.add(t)
        if "/" in t:
            out.update(p for p in t.split("/") if p)
    return out


def match_identifiers(text: str, vocabulary: set[str] | frozenset[str]) -> set[str]:
    """Identifiers of the G2 vocabulary named in `text` as a whole token (section 2).

    An identifier matches if it equals a token or a `/`-separated path component; any
    token or component matching `[A-Z][A-Z0-9]*-[0-9]+` is a ticket identifier.
    """
    toks = tokenize(text)
    if sens_v1():   # post-hoc sensitivity v1: strip one trailing '.' or ':'
        toks = [t[:-1] if len(t) > 1 and t[-1] in ".:" else t for t in toks]
    cands = token_candidates(toks)
    hits = {c for c in cands if c in vocabulary}
    hits.update(c for c in cands if TICKET_ID_RE.fullmatch(c))
    return hits


def g2_vocabulary(touch_df: pd.DataFrame, types: Sequence[str] = LIKE_TYPES) -> frozenset[str]:
    """G2 identifier vocabulary: values observed as (write or read) touch arguments of
    like-for-like types, anywhere in the corpus, any account (section 2, G2). The ticket
    pattern `[A-Z][A-Z0-9]*-[0-9]+` is added at match time (`match_identifiers`).
    """
    t = touch_df[(touch_df["kind"] != "container") & touch_df["type"].isin(types)]
    return frozenset(t["artefact"].unique())


def _text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)


#: Record sources (section 2): (service, action) -> (record kind, scope, text keys).
RECORD_SOURCES: dict[tuple[str, str], tuple[str, str, tuple[str, ...]]] = {
    ("plane", "create_issue"): ("ticket", "likeforlike", ("name", "description")),
    ("plane", "add_comment"): ("ticket", "likeforlike", ("comment", "body", "text")),
    ("plane", "update_issue"): ("ticket", "likeforlike", ("patch",)),
    ("email", "send_email"): ("mail", "allservices", ("to", "subject", "body")),
    ("email", "reply_email"): ("mail", "allservices", ("to", "subject", "body")),
    ("email", "forward_email"): ("mail", "allservices", ("to", "subject", "body")),
    ("rocketchat", "post_message"): ("chat", "allservices", ("text",)),
    ("rocketchat", "send_direct_message"): ("chat", "allservices", ("text",)),
    ("gitlab", "commit"): ("commit", "allservices", ("message", "commit_message")),
    ("gitlab", "open_mr"): ("mr", "allservices", ("title", "description", "reviewers")),
}

RECORD_COLUMNS = ["ev", "account", "day", "real_ts", "ts", "service", "action", "rkind", "scope",
                  "ticket", "project", "text", "assignee"]


def records(df: pd.DataFrame, parsed: Sequence[dict], fork_erratum: bool = False
            ) -> pd.DataFrame:
    """Text records written by an account (section 2, G2 and G5).

    Ticket records: `create_issue` name + description, `add_comment` comment/body/text,
    `update_issue` patch (JSON string when the patch is a dict); `ticket` is the ticket
    the record is written on (add_comment / update_issue `issue_id`; create_issue the
    explicit id at the start of `name`, else empty) and `project` is the record's
    `project_id` (else `project`). `assignee` is the `assignee` argument of any plane
    write. All-services records (mail, chat, commit, merge request) carry their text
    fields as listed for G5. `fork_erratum` (fork corpora): a create_issue record is on
    the created ticket (`result_meta`, `CREATE_ISSUE_META_KEYS`), else the explicit id.
    """
    metas = (df["result_meta"].to_numpy() if fork_erratum and "result_meta" in df
             else None)
    svc = df["service"].to_numpy()
    act = df["action"].to_numpy()
    acc = df["account"].to_numpy()
    ok = (df["exit_code"].to_numpy() == 0) if "exit_code" in df else np.ones(len(df), bool)
    rows: list[tuple] = []
    for i in range(len(df)):
        if not ok[i]:
            continue
        src = RECORD_SOURCES.get((svc[i], act[i]))
        a = parsed[i]
        assignee = _scalar(a.get("assignee")) if svc[i] == "plane" else None
        if src is None:
            if assignee:
                rows.append((i, "plane-assignee", "likeforlike", "", "", "", assignee))
            continue
        rkind, scope, keys = src
        text = "\n".join(_text(a.get(k)) for k in keys if a.get(k) is not None)
        ticket = ""
        project = ""
        if rkind == "ticket":
            if act[i] == "create_issue":
                ids = create_issue_ids(a)
                ticket = ids[0] if ids else ""
                if metas is not None:
                    created = _meta_first(metas[i], CREATE_ISSUE_META_KEYS)
                    ticket = created[0] if created else ticket
            else:
                ticket = _scalar(a.get("issue_id")) or ""
                if not ticket and sens_v1():
                    ticket = _scalar(a.get("ticket_id")) or ""
            project = _scalar(a.get("project_id")) or _scalar(a.get("project")) or ""
        rows.append((i, rkind, scope, ticket, project, text, assignee or ""))
    if not rows:
        return pd.DataFrame(columns=RECORD_COLUMNS)
    ev = np.array([r[0] for r in rows], dtype=np.int64)
    out = pd.DataFrame({
        "ev": ev,
        "account": acc[ev],
        "day": day_of(df["ts"]).to_numpy()[ev],
        "real_ts": df["real_ts"].to_numpy()[ev],
        "ts": df["ts"].astype(str).to_numpy()[ev],
        "service": svc[ev], "action": act[ev],
        "rkind": [r[1] for r in rows], "scope": [r[2] for r in rows],
        "ticket": [r[3] for r in rows], "project": [r[4] for r in rows],
        "text": [r[5] for r in rows], "assignee": [r[6] for r in rows],
    })
    return out[RECORD_COLUMNS]


def name_mentions(text: str, usernames: set[str] | frozenset[str],
                  fullnames: dict[str, str]) -> set[str]:
    """Accounts whose username or full name appears in `text` as a whole token (G5).

    Username: equals a token or a `/`-separated path component (same rule as G2).
    Full name (two or more words): its words appear as consecutive tokens (exact case).
    `fullnames` maps full name -> username.
    """
    toks = tokenize(text)
    cands = token_candidates(toks)
    hits = {c for c in cands if c in usernames}
    if fullnames:
        lens = {len(n.split()) for n in fullnames}
        for L in lens:
            for j in range(len(toks) - L + 1):
                key = " ".join(toks[j:j + L])
                u = fullnames.get(key)
                if u:
                    hits.add(u)
    return hits


# ----------------------------------------------------------------------------------
# Section 5: org template and induced sub-orgs
# ----------------------------------------------------------------------------------

@dataclass
class OrgTemplate:
    """Org template (bootstrap/org_template.yaml): teams, managers, usernames, full names."""
    teams: list[tuple[str, str, list[str]]]      # (team id, manager, members excl. manager)
    full_names: dict[str, str]                   # username -> full name
    groups: dict[str, list[str]] = field(default_factory=dict)  # username -> groups

    @property
    def usernames(self) -> list[str]:
        return list(self.full_names)

    @property
    def managers(self) -> list[str]:
        return [m for _, m, _ in self.teams]

    def team_size(self, i: int) -> int:
        return 1 + len(self.teams[i][2])


def load_org_template(path: str | Path) -> OrgTemplate:
    import yaml
    with open(path, encoding="utf-8") as f:
        y = yaml.safe_load(f)
    teams: list[tuple[str, str, list[str]]] = []
    for dept in y.get("departments", []):
        for t in dept.get("teams", []):
            mgr = t["manager"]
            members = [m for m in t.get("members", []) if m != mgr]
            teams.append((t["id"], mgr, members))
    full: dict[str, str] = {}
    groups: dict[str, list[str]] = {}
    for a in y.get("accounts", []):
        full[a["id"]] = a.get("full_name", "")
        groups[a["id"]] = list(a.get("groups", []) or [])
    return OrgTemplate(teams=teams, full_names=full, groups=groups)


def largest_remainder(sizes: Sequence[int], n: int) -> list[int]:
    """Apportion `n` seats to parts in proportion to `sizes` (largest remainder; ties
    broken by part order)."""
    total = sum(sizes)
    exact = [n * s / total for s in sizes]
    base = [int(math.floor(e)) for e in exact]
    rem = n - sum(base)
    order = sorted(range(len(sizes)), key=lambda i: (-(exact[i] - base[i]), i))
    for i in order[:rem]:
        base[i] += 1
    return base


def induce_suborg(template: OrgTemplate, n: int, seed: int) -> list[str]:
    """Induced sub-org of `n` accounts (TRACK-B section 5, N-scaling).

    Within each of the teams, sample in proportion to team size (largest-remainder
    rounding to `n`), always keeping each team's manager; `random.Random(seed)` drives
    the draw, teams in template order. `n` >= the org size returns the whole org.
    """
    allacc = [m for _, mgr, mem in template.teams for m in [mgr] + mem]
    if n >= len(allacc):
        return sorted(allacc)
    rng = random.Random(seed)
    sizes = [template.team_size(i) for i in range(len(template.teams))]
    quotas = largest_remainder(sizes, n)
    out: list[str] = []
    for (tid, mgr, members), q in zip(template.teams, quotas):
        if q < 1:
            raise ValueError(f"team {tid} gets quota {q}; cannot keep its manager")
        out.append(mgr)
        out.extend(rng.sample(members, q - 1))
    assert len(out) == n
    return sorted(out)


def load_pairs(path: str | Path) -> list[dict]:
    """The four released colluding pairs from bootstrap/insider_assignment.yaml
    (`collusion` -> c1_release_bypass / c2_split_exfil -> s0 / s1 -> role: account)."""
    import yaml
    with open(path, encoding="utf-8") as f:
        y = yaml.safe_load(f)
    out = []
    for threat, short in (("c1_release_bypass", "C1"), ("c2_split_exfil", "C2")):
        for level in ("s0", "s1"):
            roles = y["collusion"][threat][level]
            out.append({"pair": f"{short}-{level}", "threat": threat, "level": level,
                        "roles": dict(roles), "members": list(roles.values())})
    return out


# ----------------------------------------------------------------------------------
# Per-corpus cache
# ----------------------------------------------------------------------------------

def cache_suffix() -> str:
    """Cache file-name suffix: empty for the primary run, `.sensv1` for sensitivity v1."""
    return ".sensv1" if sens_v1() else ""


def build_cache(data_dir: str | Path, corpus: str, cache_dir: str | Path,
                log=lambda *a: None) -> dict[str, Any]:
    """Load one corpus, parse args once, and write the touch table, records,
    account-days and the key-usage table under `cache_dir` (parquet / json)."""
    import time
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    df = load_audit(data_dir, corpus)
    log(f"[{corpus}] loaded {len(df):,} successful events in {time.time()-t0:.1f}s")
    parsed, fails = parse_args_column(df["args"])
    log(f"[{corpus}] parsed args ({fails} failures) in {time.time()-t0:.1f}s")
    keys = key_usage_table(df, parsed)
    t = touches(df, parsed)
    r = records(df, parsed)
    ad = account_days(df)
    rt_max = float(np.nanmax(df["real_ts"].to_numpy())) if len(df) else 0.0
    meta = {"cache_version": CACHE_VERSION, "sensitivity_v1": sens_v1(), "corpus": corpus, "n_success_events": int(len(df)), "args_parse_failures": fails,
            "real_ts_null": int(df["real_ts"].isna().sum()), "real_ts_max": rt_max,
            "keys": {k: dict(v) for k, v in keys.items()}}
    sfx = cache_suffix()
    t.to_parquet(cache / f"{corpus}{sfx}.touches.parquet", index=False)
    r.to_parquet(cache / f"{corpus}{sfx}.records.parquet", index=False)
    ad.to_parquet(cache / f"{corpus}{sfx}.accountdays.parquet", index=False)
    (cache / f"{corpus}{sfx}.meta.json").write_text(json.dumps(meta, indent=1))
    log(f"[{corpus}] cache written: {len(t):,} touch rows, {len(r):,} records, "
        f"{len(ad):,} account-days in {time.time()-t0:.1f}s")
    return meta


def load_cache(data_dir: str | Path, corpus: str, cache_dir: str | Path,
               log=lambda *a: None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """(touches, records, account_days, meta) for a corpus, building the cache if absent."""
    cache = Path(cache_dir)
    need = [cache / f"{corpus}{cache_suffix()}.{x}" for x in
            ("touches.parquet", "records.parquet", "accountdays.parquet", "meta.json")]
    stale = not all(p.exists() for p in need) or \
        json.loads(need[3].read_text()).get("cache_version") != CACHE_VERSION
    if stale:
        build_cache(data_dir, corpus, cache_dir, log)
    t = pd.read_parquet(need[0])
    r = pd.read_parquet(need[1])
    ad = pd.read_parquet(need[2])
    meta = json.loads(need[3].read_text())
    return t, r, ad, meta


def eprint(*a: Any) -> None:
    print(*a, file=sys.stderr, flush=True)
