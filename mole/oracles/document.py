"""The shared document reader: ONE definition of what a shared document says at a point in time.

Stage 3 (family F4) is about shared working documents that honest accounts edit and read. Three
consumers need the same answer to "what did document X say at time t": the composed-document
O-judge view (`work/checks/score_o_composed.py`), the F4 oracle (task S2), and any rung-0/1
counting script. Lesson L4 (and L15 rule 5) says a control and the oracle that grades it must
share one definition in one place; this module is that place. Nothing here reads labels,
transcripts or `is_malicious`.

Public interface (small and stable; the F4 oracle imports exactly these):

* `DocRef(service, key)` / `parse_doc_id("plane:OPS-6")` / `DocRef.id` -- a document identifier.
  Keys per service:
    - ``owncloud``:    the file path (``/shared/README.md``);
    - ``gitlab``:      ``<project>:<branch>:<path>`` (the file on one branch);
    - ``eval_server``: the eval config id (``release-gate``);
    - ``plane``:       the issue id (``OPS-6``): the in-process analogue of a shared document is
                       an issue's title and description plus its comment thread.
* `coerce_text(value) -> str` -- the ONE coercion used for every content field: str passes
  through, bytes decode as UTF-8 (undecodable bytes replaced), dict/list are JSON-dumped
  deterministically (sorted keys, indent 2, non-ASCII kept), None is "", anything else str().
* `unified_diff(before, after, path) -> str` -- a unified diff of two contents (None = absent).
* `content_writes(rows, ref=None, ...)` -- the successful audit rows that change a document's
  content, as `DocWrite` records (who, when, which document); the writer set of a document.
* `content_at(rows, ref, as_of, *, base=None, base_as_of=None)` -- the document's content at
  `as_of`, replayed from the audit log: the last successful write at or before `as_of` for
  whole-content writes (ownCloud `write_file`, GitLab `commit`, eval-server `create_config` /
  `update_config`), and for plane the fold of `create_issue`, `update_issue` (title or
  description) and `add_comment`. `base` is either a managers snapshot holding the state at
  `base_as_of` (rows at or before `base_as_of` are then skipped) or a SEED mapping
  {DocRef or (service, key): seed content} used as the day-0 state before the whole log is
  replayed. Returns `UNKNOWN` (not None) when the content cannot be known (see below).
* `content_from_managers(managers, ref)` / `load_managers(path)` / `managers_path(corpus, day)`
  -- the content read directly from an in-process managers snapshot
  (`.snapshots/<run>/day_<date>/managers.json`). Only in-process services are in a snapshot
  (plane, eval_server); ownCloud and GitLab are read from the log.
* `read_document(ref, *, as_of=None, rows=None, managers=None, base=None, base_as_of=None)` --
  the single entry point: from the snapshot when `managers` is given, else from the log.
* `UNKNOWN` / `is_unknown(x)` -- the explicit "cannot tell" result of a log replay.

Absent versus unknown (review fix 2026-10-20). Seeding writes documents OUTSIDE the audit log
(e.g. mole/seeders/seed_org.py `_seed_owncloud`; seeded plane issues and eval configs), so an
empty replay cannot tell "absent" from "seeded and never rewritten". The rule:
  - None means ABSENT: the document was deleted, or the base says it did not exist (a managers
    snapshot lists every plane issue and eval config; a seed mapping is the complete day-0
    state for every service that appears among its keys).
  - `UNKNOWN` means the reader cannot know: no base covers the document's service AND, at or
    before `as_of`, no whole-content write fixes its content. Whole-content writes: ownCloud
    `write_file` / `delete`, GitLab `commit`, eval `create_config` / `update_config`, plane
    `create_issue`. A plane `update_issue` or `add_comment` on an issue not created in the log
    is partial (title, description or earlier comments unknown), so it stays `UNKNOWN`.
  - A seed value is the content (str; an eval config may be a dict or a JSON string; a plane
    issue is a dict {name, description, comments: [{user, body}]} or a str taken as its
    description with no title and no comments).
`UNKNOWN` is falsy and is never a str; `render` passes it through and `unified_diff` refuses it.

Time bounds (`as_of`, `base_as_of`, `since`, `until`) are either a date ``YYYY-MM-DD``,
meaning the END of that simulated day (inclusive), or a full ISO timestamp compared as a
string (the audit log's canonical ``...Z`` form). Rows are replayed in FILE order (the order
the calls completed, which is the order the state managers applied them), filtered by `ts`.

Success: a row counts only when ``exit_code`` is 0 (a missing exit_code counts as 0, as in
the scorers); the audit collector already marks ``{"ok": False}`` envelopes (e.g. a refused
ticket update) as failed. Not modelled (documented, not silently wrong): GitLab merges and
force pushes (only direct commits to the named branch change that branch's file), ownCloud
moves, bytes written through the audit log (the collector records bytes as their repr), and
the plane `update_issue` patch keys `comment`, `body` and `title` (the manager stores them as
separate issue fields; the document is `name` + `description` + the comment thread, so they do
not change it and such a patch is not a content write).
"""
from __future__ import annotations

import copy
import difflib
import json
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SERVICES = ("owncloud", "gitlab", "eval_server", "plane")


class _Unknown:
    """The reader cannot know the content (see "Absent versus unknown"). Singleton, falsy."""
    _inst: "_Unknown | None" = None

    def __new__(cls) -> "_Unknown":
        if cls._inst is None:
            cls._inst = super().__new__(cls)
        return cls._inst

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "UNKNOWN"


UNKNOWN = _Unknown()


def is_unknown(value: Any) -> bool:
    """True for the `UNKNOWN` sentinel."""
    return value is UNKNOWN

#: The content arg key of each document type's writes, for the renderer's whole-key list
#: (mole.monitors.release.account_history.whole_key_set) so P and O see the same text.
CONTENT_KEYS: dict[str, tuple[str, ...]] = {
    "owncloud": ("content", "data", "body"),
    "gitlab": ("content",),
    "eval_server": ("config",),
    "plane": ("description", "body", "text", "comment"),
}

#: (service, action) pairs that can change a document's content.
WRITE_ACTIONS: frozenset[tuple[str, str]] = frozenset({
    ("owncloud", "write_file"), ("owncloud", "delete"),
    ("gitlab", "commit"),
    ("eval_server", "create_config"), ("eval_server", "update_config"),
    ("plane", "create_issue"), ("plane", "update_issue"), ("plane", "add_comment"),
})

# plane.update_issue lifts these top-level kwargs into the patch (PlaneManager.update_issue).
_PLANE_PATCH_FIELDS = ("state", "status", "title", "description", "label", "labels",
                       "priority", "assignee", "name", "comment", "body",
                       "requested_for", "requested_group", "manager_signoff")
# The issue fields that make up the plane document (comments are the thread).
_PLANE_DOC_FIELDS = ("name", "description")


# ── identifiers ──────────────────────────────────────────────────────

@dataclass(frozen=True, order=True)
class DocRef:
    """One shared document: a service and its key (see the module docstring)."""
    service: str
    key: str

    def __post_init__(self) -> None:
        if self.service not in SERVICES:
            raise ValueError(f"unknown document service {self.service!r} (known: {SERVICES})")
        if not self.key:
            raise ValueError("empty document key")
        if self.service == "gitlab" and len(self.key.split(":", 2)) != 3:
            raise ValueError(f"gitlab key must be '<project>:<branch>:<path>', got {self.key!r}")

    @property
    def id(self) -> str:
        """``<service>:<key>``, the form `parse_doc_id` reads and scorer labels carry."""
        return f"{self.service}:{self.key}"

    def __str__(self) -> str:
        return self.id


def parse_doc_id(doc_id: str) -> DocRef:
    """``"plane:OPS-6"`` -> DocRef("plane", "OPS-6"); the key may itself contain colons."""
    service, sep, key = str(doc_id).partition(":")
    if not sep:
        raise ValueError(f"document id must be '<service>:<key>', got {doc_id!r}")
    return DocRef(service, key)


@dataclass(frozen=True)
class DocWrite:
    """One successful audit row that changes a document's content."""
    ref: DocRef
    account: str
    ts: str
    action: str
    index: int                     # row position in the log (file order)


# ── coercion and diff ────────────────────────────────────────────────

def coerce_text(value: Any) -> str:
    """The one text coercion for every content field (see the module docstring)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace")
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, default=str)
    return str(value)


def unified_diff(before: str | None, after: str | None, path: str) -> str:
    """Unified diff of two contents of the document at `path` ("" when they are equal).
    None means the document did not exist (``/dev/null`` side)."""
    if is_unknown(before) or is_unknown(after):
        raise ValueError("cannot diff UNKNOWN content (seeded outside the log, no base)")
    a = "" if before is None else before
    b = "" if after is None else after
    if before == after:
        return ""
    lines = difflib.unified_diff(
        a.splitlines(keepends=True), b.splitlines(keepends=True),
        fromfile="/dev/null" if before is None else f"a/{path.lstrip('/')}",
        tofile="/dev/null" if after is None else f"b/{path.lstrip('/')}")
    out = []
    for ln in lines:
        out.append(ln if ln.endswith("\n") else ln + "\n\\ No newline at end of file\n")
    return "".join(out)


# ── time bounds ──────────────────────────────────────────────────────

def _le(ts: str, bound: str | None) -> bool:
    """ts at or before bound (a date bound means the end of that day)."""
    if bound is None:
        return True
    ts = str(ts or "")
    return ts[:10] <= bound if len(bound) == 10 else ts <= bound


def _ok(row: Mapping[str, Any]) -> bool:
    return (row.get("exit_code") or 0) == 0


def _args(row: Mapping[str, Any]) -> dict[str, Any]:
    a = row.get("args") or {}
    return a if isinstance(a, dict) else {}


def _meta(row: Mapping[str, Any]) -> dict[str, Any]:
    m = row.get("result_meta") or {}
    return m if isinstance(m, dict) else {}


# ── which document does a row write? ─────────────────────────────────

def _first(*vals: Any) -> Any:
    """The first truthy value (the managers' `a or b or c` alias rule), else the last."""
    for v in vals:
        if v:
            return v
    return vals[-1] if vals else None


def _plane_patch(args: Mapping[str, Any]) -> dict[str, Any]:
    """PlaneManager.update_issue's patch coercion: JSON string -> dict, non-dict -> {},
    then the top-level field kwargs folded in."""
    patch = args.get("patch")
    if isinstance(patch, str):
        try:
            patch = json.loads(patch)
        except ValueError:
            patch = {}
    patch = dict(patch) if isinstance(patch, dict) else {}
    for fld in _PLANE_PATCH_FIELDS:
        if args.get(fld) is not None:
            patch[fld] = args[fld]
    return patch


def _row_ref(row: Mapping[str, Any]) -> DocRef | None:
    """The document a successful row writes, or None (reads, failures, non-content edits)."""
    svc, act = row.get("service"), row.get("action")
    if (svc, act) not in WRITE_ACTIONS or not _ok(row):
        return None
    a, m = _args(row), _meta(row)
    if svc == "owncloud":
        p = a.get("path")
        return DocRef(svc, str(p)) if p else None
    if svc == "gitlab":
        proj, branch, p = a.get("project"), a.get("branch"), a.get("path")
        return DocRef(svc, f"{proj}:{branch}:{p}") if proj and branch and p else None
    if svc == "eval_server":
        cid = m.get("config_id") if act == "create_config" else a.get("config_id")
        return DocRef(svc, str(cid)) if cid else None
    # plane
    if act == "create_issue":
        iid = m.get("id")
    elif act == "add_comment":
        iid = a.get("issue_id") if m.get("id") else None      # no id in the result: no comment
    else:                                                     # update_issue
        iid = a.get("issue_id")
        if iid and not any(k in _plane_patch(a) for k in _PLANE_DOC_FIELDS):
            return None                                       # state / label only: not content
    return DocRef(svc, str(iid)) if iid else None


def _iter_writes(rows: Iterable[Mapping[str, Any]], ref: DocRef | None,
                 since: str | None, until: str | None
                 ) -> Iterator[tuple[int, Mapping[str, Any], DocRef]]:
    """(index, row, ref) for successful content writes with since < ts <= until, file order.
    An ownCloud delete of a folder writes every document under it."""
    for i, r in enumerate(rows):
        if ref is not None and r.get("service") != ref.service:
            continue
        rr = _row_ref(r)
        if rr is None:
            continue
        ts = str(r.get("ts") or "")
        if not _le(ts, until) or (since is not None and _le(ts, since)):
            continue
        if ref is None or rr == ref or _deletes(r, rr, ref):
            yield i, r, (ref if ref is not None and rr != ref else rr)


def _deletes(row: Mapping[str, Any], rr: DocRef, ref: DocRef) -> bool:
    """An ownCloud delete of a folder that contains `ref` (either slash form)."""
    if ref.service != "owncloud" or row.get("action") != "delete":
        return False
    d = rr.key.rstrip("/")
    return bool(d) and ref.key.startswith(d + "/")


def content_writes(rows: Iterable[Mapping[str, Any]], ref: DocRef | None = None, *,
                   since: str | None = None, until: str | None = None) -> list[DocWrite]:
    """Successful content writes (to `ref`, or to every document when None) with
    since < ts <= until, in file order. The writer set of a document is
    ``{w.account for w in content_writes(rows, ref, ...)}``."""
    return [DocWrite(ref=rr, account=str(r.get("account") or ""), ts=str(r.get("ts") or ""),
                     action=str(r.get("action")), index=i)
            for i, r, rr in _iter_writes(rows, ref, since, until)]


# ── state: snapshot read, replay, render ─────────────────────────────

def load_managers(path: str | Path) -> dict[str, Any]:
    """A managers.json snapshot (read only)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def managers_path(corpus: str | Path, day: str) -> Path:
    """`.snapshots/<corpus stem>/day_<day>/managers.json` beside a corpus JSONL (the
    generator's layout; the state at the END of `day`)."""
    corpus = Path(corpus)
    stem = corpus.name[:-len(".jsonl")] if corpus.name.endswith(".jsonl") else corpus.stem
    return corpus.parent / ".snapshots" / stem / f"day_{day}" / "managers.json"


def _plane_ws(managers: Mapping[str, Any]) -> dict[str, Any]:
    pl = managers.get("plane") or {}
    st = pl.get("_state") or {}
    slug = pl.get("_workspace_slug") or (next(iter(st)) if st else None)
    return (st.get(slug) if slug else None) or {}


def _snapshot_state(managers: Mapping[str, Any], ref: DocRef) -> Any:
    """The structured state of `ref` in a snapshot (None if absent): a plane issue as
    {name, description, comments}, an eval config object. ownCloud/GitLab are not in
    in-process snapshots: ValueError."""
    if ref.service == "plane":
        ws = _plane_ws(managers)
        issue = (ws.get("issues") or {}).get(ref.key)
        if issue is None:
            return None
        return {"name": issue.get("name"), "description": issue.get("description"),
                "comments": [{"user": c.get("user") or c.get("username"),
                              "body": c.get("body") if c.get("body") is not None else c.get("text")}
                             for c in (ws.get("comments") or {}).get(ref.key) or []]}
    if ref.service == "eval_server":
        rec = ((managers.get("eval_server") or {}).get("_configs") or {}).get(ref.key)
        if not rec or not rec.get("versions"):
            return None
        return copy.deepcopy(rec["versions"][-1].get("config"))
    raise ValueError(f"{ref.service} documents are not in an in-process managers snapshot; "
                     "read them from the audit log")


def _config_obj(value: Any) -> Any:
    """EvalServerManager._coerce_config's string rule: a JSON string is parsed."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def _apply(state: Any, row: Mapping[str, Any], ref: DocRef) -> Any:
    """The document state after one successful write row (None = absent)."""
    a, act = _args(row), row.get("action")
    if ref.service == "owncloud":
        if act == "delete":
            return None
        return _first(a.get("content"), a.get("data"), a.get("body"), "")
    if ref.service == "gitlab":
        return a.get("content", "")
    if ref.service == "eval_server":
        return _config_obj(a.get("config"))
    # plane
    if act == "create_issue":
        return {"name": a.get("name"), "description": a.get("description", ""), "comments": []}
    st = copy.deepcopy(state) if state is not None else \
        {"name": None, "description": None, "comments": []}
    if act == "add_comment":
        st["comments"].append({"user": a.get("sender") or "system",
                               "body": _first(a.get("body"), a.get("text"), a.get("comment"), "")})
        return st
    patch = _plane_patch(a)                                   # update_issue
    for fld in _PLANE_DOC_FIELDS:
        if fld in patch:
            st[fld] = patch[fld]
    return st


def render(ref: DocRef, state: Any) -> str | None:
    """The document text of a structured state (None stays None). Plane: the title line,
    the description, then one line per comment (author: body), as a reader of the issue
    sees it. Eval config: the config object through coerce_text. Files: coerce_text."""
    if state is None or is_unknown(state):
        return state
    if ref.service != "plane":
        return coerce_text(state)
    parts = [f"Title: {coerce_text(state.get('name'))}", "", coerce_text(state.get("description"))]
    cs = state.get("comments") or []
    if cs:
        parts += ["", f"Comments ({len(cs)}):"]
        parts += [f"- {coerce_text(c.get('user'))}: {coerce_text(c.get('body'))}" for c in cs]
    return "\n".join(parts) + "\n"


def content_from_managers(managers: Mapping[str, Any], ref: DocRef) -> str | None:
    """The document's content in a managers snapshot (None if it does not exist there)."""
    return render(ref, _snapshot_state(managers, ref))


_FULL_WRITES = frozenset({
    ("owncloud", "write_file"), ("owncloud", "delete"), ("gitlab", "commit"),
    ("eval_server", "create_config"), ("eval_server", "update_config"),
    ("plane", "create_issue"),
})


def _seed_key(k: Any) -> DocRef:
    if isinstance(k, DocRef):
        return k
    if isinstance(k, tuple) and len(k) == 2:
        return DocRef(str(k[0]), str(k[1]))
    raise ValueError(f"seed mapping keys must be DocRef or (service, key), got {k!r}")


def _is_seed_mapping(base: Mapping[Any, Any]) -> bool:
    """A seed mapping has DocRef / (service, key) keys; a managers snapshot has service-name
    string keys. An empty mapping is refused (it would be ambiguous)."""
    if not base:
        raise ValueError("empty base: pass None, a managers snapshot or a seed mapping")
    kinds = {isinstance(k, (DocRef, tuple)) for k in base}
    if len(kinds) != 1:
        raise ValueError("base mixes DocRef/(service, key) keys with other keys")
    return kinds.pop()


def _seed_state(ref: DocRef, value: Any) -> Any:
    """A seed value as the reader's structured state (see "Absent versus unknown")."""
    if value is None:
        return None
    if ref.service == "eval_server":
        return _config_obj(value)
    if ref.service == "plane":
        if isinstance(value, Mapping):
            return {"name": value.get("name"), "description": value.get("description"),
                    "comments": [{"user": c.get("user"), "body": c.get("body")}
                                 for c in value.get("comments") or []]}
        return {"name": None, "description": coerce_text(value), "comments": []}
    return value


def content_at(rows: Iterable[Mapping[str, Any]], ref: DocRef, as_of: str | None, *,
               base: Mapping[Any, Any] | None = None,
               base_as_of: str | None = None) -> str | None:
    """The document's content at `as_of` replayed from the audit log: a str, None (absent) or
    `UNKNOWN` (see "Absent versus unknown" in the module docstring).

    `base` = a managers snapshot taken at `base_as_of` (required then): replay starts from the
    snapshot's state and only rows after `base_as_of` are applied. `base` = a seed mapping
    {DocRef or (service, key): content}: the day-0 state of every service among its keys
    (a document of such a service missing from the mapping did not exist); rows after
    `base_as_of` (default: the whole log) are applied. Without a base covering the service,
    the result is `UNKNOWN` unless a whole-content write at or before `as_of` fixes it."""
    known = False
    state: Any = None
    since: str | None = None
    if base is not None:
        if _is_seed_mapping(base):
            seeds = {_seed_key(k): v for k, v in base.items()}
            if ref.service in {k.service for k in seeds}:
                known = True
                state = _seed_state(ref, seeds.get(ref))
            since = base_as_of
        else:
            if base_as_of is None:
                raise ValueError("base needs base_as_of (the time the snapshot was taken)")
            state = _snapshot_state(base, ref)
            known = True
            since = base_as_of
    for _i, r, _rr in _iter_writes(rows, ref, since, as_of):
        if (r.get("service"), r.get("action")) in _FULL_WRITES:
            known = True
        state = _apply(state, r, ref)
    return render(ref, state) if known else UNKNOWN


def read_document(ref: DocRef, *, as_of: str | None = None,
                  rows: Iterable[Mapping[str, Any]] | None = None,
                  managers: Mapping[str, Any] | None = None,
                  base: Mapping[str, Any] | None = None,
                  base_as_of: str | None = None) -> str | None:
    """The one entry point. With `managers`: the content in that snapshot (the caller picks
    the snapshot for the time it wants; `as_of` is then not used). Otherwise: replay `rows`
    up to `as_of` (optionally from `base` at `base_as_of`). Giving both `managers` and `as_of`
    is a ValueError (the snapshot fixes the time)."""
    if managers is not None:
        if as_of is not None:
            raise ValueError("read_document: give managers (a snapshot) or as_of (a log "
                             "replay time), not both")
        return content_from_managers(managers, ref)
    if rows is None:
        raise ValueError("read_document needs rows (an audit log) or managers (a snapshot)")
    return content_at(rows, ref, as_of, base=base, base_as_of=base_as_of)
