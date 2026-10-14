"""Candidate-group generators G1 to G6 (TRACK-B part 1, section 2), windows (section 3),
the B0 rank rule (section 4) and the B1 volume rule (section 5).

Every generator is a function of (corpus index, day d, window w, scope) returning
(a) the candidate groups emitted on day d and (b) the link strength L(a, b) for every
ordered pair of accounts, as an n x n numpy array indexed by `CorpusIndex.accounts`
(L[a, b] = L(a, b); symmetric for G1, G3, G4, G6, directed for G2 and G5 with the
first index the writer: L2[A, B] = handoffs from A's record to B's action,
L5[B, A] = B's records that name A).

Window (section 3): the trailing `w` calendar days d-w+1 .. d inclusive (days are the
simulated dates `ts[:10]`; the released corpora have no events on weekends, so a
calendar window can hold fewer than `w` active days; see the errata list in the B0/B1
reports). Ordering (section 0): `okey = day_rel * 1e8 + real_ts`, i.e. the day first,
`real_ts` inside a day.

Emission (section 2): a group is emitted on day d only if one of its members touched the
group's artefact on day d. Review pairs (section 5, volume V): reviewing a group means
reviewing each member on each day within the window on which it touched the group's
artefact; G2 and G5 have no single shared artefact, see `groups_g2` / `groups_g5`.
"""
from __future__ import annotations

import bisect
import hashlib
import pickle
import time
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import numpy as np
import pandas as pd
import scipy.sparse as sp

import mole_corpus as mc

TYPE_CODES: dict[str, int] = {t: i for i, t in enumerate(mc.ALL_TYPES)}
WINDOWS: tuple[int, ...] = (1, 3, 7)
TAUS: tuple[int, ...] = (60, 180)
BUDGETS: tuple[float, ...] = (0.02, 0.10)
MAX_W = max(WINDOWS)
DAYCODE = 10000          # review pair code = acct * DAYCODE + day_rel
GEN_VERSION = "gen-v3"

#: B0/B1 generator variants (section 2; G4 at both taus, G2 strict and loose).
VARIANTS: tuple[str, ...] = ("G1", "G2-strict", "G2-loose", "G3", "G4-60", "G4-180", "G5", "G6")


# ----------------------------------------------------------------------------------
# Corpus index
# ----------------------------------------------------------------------------------

@dataclass
class CorpusIndex:
    """Array form of one corpus (or induced sub-org) for the window/day loops."""
    corpus: str
    accounts: list[str]
    acc_idx: dict[str, int]
    day0: int                       # ordinal of day_rel 0
    n_days: int                     # day_rel in [0, n_days)
    day_list: list[str]             # day_rel -> date (calendar days; or active days in v1)
    days: np.ndarray                # active day_rel values, sorted
    ad_acct: np.ndarray             # account-days
    ad_day: np.ndarray
    active: np.ndarray              # bool [n_days, n]
    # touches (write/read only), sorted by okey (hence by day)
    t_acct: np.ndarray
    t_day: np.ndarray
    t_okey: np.ndarray
    t_tsmin: np.ndarray
    t_type: np.ndarray
    t_art: np.ndarray
    t_write: np.ndarray
    art_type: np.ndarray            # art id -> type code
    art_value: np.ndarray           # art id -> bare value (object)
    # G2 handoffs per variant ("strict", "loose"): DataFrame with columns
    # rec, act_ev, A, B, rec_day, read_day, act_day, R, R_is_ticket
    handoffs: dict[str, pd.DataFrame]
    # G5 name mentions: DataFrame rec, B, A, day, like
    mentions: pd.DataFrame
    # G2 naming index for the unrequested-action rate: value -> (okeys, days), sorted
    naming: dict[str, tuple[np.ndarray, np.ndarray]] | None
    # like-for-like write touches with bare values (unrequested-action rate)
    lw_acct: np.ndarray
    lw_day: np.ndarray
    lw_okey: np.ndarray
    lw_value: np.ndarray
    lw_type: np.ndarray
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.accounts)

    def day_str(self, d: int) -> str:
        return self.day_list[int(d)]

    def day_rel(self, s: str) -> int:
        """Day index of a date; -1 when the date is not a day of this index."""
        try:
            return self.day_list.index(s)
        except ValueError:
            return -1

    def n_account_days(self) -> int:
        return int(len(self.ad_acct))

    def window(self, d: int, w: int) -> tuple[int, int]:
        """Index range [lo, hi) of touches with day in [d-w+1, d] (section 3)."""
        lo = int(np.searchsorted(self.t_day, d - w + 1, side="left"))
        hi = int(np.searchsorted(self.t_day, d, side="right"))
        return lo, hi

    def active_in_window(self, d: int, w: int) -> np.ndarray:
        a = max(0, d - w + 1)
        return self.active[a:d + 1].any(axis=0)

    def n_active(self, d: int) -> int:
        return int(self.active[d].sum())


def _okey(day_rel: np.ndarray, real_ts: np.ndarray) -> np.ndarray:
    return day_rel.astype(np.float64) * mc.ORDER_DAY_SCALE + real_ts.astype(np.float64)


def build_index(corpus: str, tdf: pd.DataFrame, rdf: pd.DataFrame, adf: pd.DataFrame,
                template: mc.OrgTemplate, *, cache_dir: str | Path | None = None,
                log: Callable[..., None] = lambda *a: None,
                day_rank: bool = False) -> CorpusIndex:
    """Index a corpus: touch arrays, account-days, G2 handoffs, G5 mentions.

    `day_rank` (fork corpora, TRACK-B part 2 draft section 2): the day index is the rank
    of the date among the corpus's dates (as sensitivity v1 does), so a trailing window
    of w days is w corpus days; the released-corpus default is calendar days."""
    t0 = time.time()
    accounts = sorted(set(template.usernames) | set(adf["account"]) | set(tdf["account"]))
    acc_idx = {a: i for i, a in enumerate(accounts)}
    all_days = pd.concat([adf["day"], tdf["day"]]).unique()
    ords = mc.day_ordinal(all_days)
    day0 = int(ords.min())
    if mc.sens_v1() or day_rank:
        # post-hoc sensitivity v1 (errata item 1): windows counted in active corpus days
        day_list = sorted(str(x) for x in all_days)
    else:
        day_list = [date.fromordinal(o).isoformat() for o in range(day0, int(ords.max()) + 1)]
    n_days = len(day_list)
    day_pos = {d_: i for i, d_ in enumerate(day_list)}

    def rel(days: pd.Series) -> np.ndarray:
        u, inv = np.unique(days.to_numpy(), return_inverse=True)
        return np.array([day_pos[x] for x in u], dtype=np.int64)[inv]

    ad_acct = adf["account"].map(acc_idx).to_numpy(np.int64)
    ad_day = rel(adf["day"])
    active = np.zeros((n_days, len(accounts)), dtype=bool)
    active[ad_day, ad_acct] = True

    t = tdf
    tday = rel(t["day"])
    tokey = _okey(tday, t["real_ts"].to_numpy())
    is_cont = (t["kind"] == "container").to_numpy()
    key = (t["type"] + "\x1f" + t["sub"] + "\x1f" + t["artefact"]).to_numpy()
    art_id, art_keys = pd.factorize(key)
    art_type_all = np.empty(len(art_keys), dtype=np.int64)
    art_value_all = np.empty(len(art_keys), dtype=object)
    tt = t["type"].map(TYPE_CODES).to_numpy(np.int64)
    art_type_all[art_id] = tt
    art_value_all[art_id] = t["artefact"].to_numpy()
    tsmin = mc.sim_minutes(t["ts"])
    tacct = t["account"].map(acc_idx).to_numpy(np.int64)
    m = ~is_cont
    order = np.argsort(tokey[m], kind="stable")
    sel = np.flatnonzero(m)[order]

    like_codes = np.array([TYPE_CODES[x] for x in mc.LIKE_TYPES])
    is_write = (t["kind"] == "write").to_numpy()
    lw = np.flatnonzero(is_write & np.isin(tt, like_codes))
    lw = lw[np.argsort(tokey[lw], kind="stable")]

    ci = CorpusIndex(
        corpus=corpus, accounts=accounts, acc_idx=acc_idx, day0=day0, n_days=n_days,
        day_list=day_list,
        days=np.unique(ad_day), ad_acct=ad_acct, ad_day=ad_day, active=active,
        t_acct=tacct[sel], t_day=tday[sel], t_okey=tokey[sel], t_tsmin=tsmin[sel],
        t_type=tt[sel], t_art=art_id[sel], t_write=is_write[sel],
        art_type=art_type_all, art_value=art_value_all,
        handoffs={}, mentions=pd.DataFrame(), naming=None,
        lw_acct=tacct[lw], lw_day=tday[lw], lw_okey=tokey[lw],
        lw_value=t["artefact"].to_numpy()[lw], lw_type=tt[lw],
    )
    log(f"[{corpus}] index arrays {time.time()-t0:.1f}s ({len(sel):,} touches)")

    # Derived G2 / G5 products, cached per corpus.
    cpath = None
    if cache_dir is not None:
        sig = hashlib.sha256(f"{mc.CACHE_VERSION}|{GEN_VERSION}|{len(tdf)}|{len(rdf)}".encode()
                             ).hexdigest()[:12]
        cpath = Path(cache_dir) / f"{corpus}{mc.cache_suffix()}.derived.{sig}.pkl"
    if cpath is not None and cpath.exists():
        with open(cpath, "rb") as f:
            d = pickle.load(f)
    else:
        d = _derive_g2_g5(ci, t, tday, tokey, tacct, is_cont, rdf, template, log)
        if cpath is not None:
            with open(cpath, "wb") as f:
                pickle.dump(d, f)
    ci.handoffs = d["handoffs"]
    ci.mentions = d["mentions"]
    ci.naming = d["naming"]
    ci.diagnostics.update(d["diagnostics"])
    log(f"[{corpus}] index built {time.time()-t0:.1f}s")
    return ci


def _derive_g2_g5(ci: CorpusIndex, t: pd.DataFrame, tday: np.ndarray, tokey: np.ndarray,
                  tacct: np.ndarray, is_cont: np.ndarray, rdf: pd.DataFrame,
                  template: mc.OrgTemplate, log: Callable[..., None]) -> dict[str, Any]:
    """G2 handoffs (strict, loose), the naming index, and G5 mentions (section 2)."""
    t0 = time.time()
    vocab = mc.g2_vocabulary(t)
    rd = rdf.copy()
    _pos = {d_: i for i, d_ in enumerate(ci.day_list)}
    rd["day_rel"] = rd["day"].map(_pos).to_numpy(np.int64) if len(rd) else []
    rd["okey"] = _okey(rd["day_rel"].to_numpy(), rd["real_ts"].to_numpy()) if len(rd) else []
    rd["acct"] = rd["account"].map(ci.acc_idx)

    # ---- G2 records (ticket records with text) and their identifiers
    tick = rd[rd["rkind"] == "ticket"]
    idents: list[set[str]] = [mc.match_identifiers(x, vocab) for x in tick["text"]]
    # diagnostic: extra matches if trailing '.' / ':' were stripped from tokens
    extra = 0
    for x, ids in zip(tick["text"], idents):
        cands = {c.rstrip(".:") for c in mc.token_candidates(mc.tokenize(x))}
        extra += len({c for c in cands if c in vocab or mc.TICKET_ID_RE.fullmatch(c)} - ids)
    log(f"[{ci.corpus}] G2 identifiers matched in {time.time()-t0:.1f}s")

    # naming index (any account's ticket record naming a value), for unrequested rate
    nm: dict[str, list[tuple[float, int]]] = {}
    for ok, dr, ids in zip(tick["okey"].to_numpy(), tick["day_rel"].to_numpy(), idents):
        for r in ids:
            nm.setdefault(r, []).append((ok, dr))
    naming = {}
    for r, lst in nm.items():
        lst.sort()
        naming[r] = (np.array([x[0] for x in lst]), np.array([x[1] for x in lst], dtype=np.int64))

    # reads of tickets (get_issue) and list_issues on projects
    gi = (t["service"].eq("plane") & t["action"].eq("get_issue")).to_numpy()
    li = (t["service"].eq("plane") & t["action"].eq("list_issues") & t["kind"].eq("container")
          ).to_numpy()

    def index_by(mask: np.ndarray) -> dict[str, tuple[list[float], list[int], list[int]]]:
        idx = np.flatnonzero(mask)
        idx = idx[np.argsort(tokey[idx], kind="stable")]
        out: dict[str, tuple[list[float], list[int], list[int]]] = {}
        vals = t["artefact"].to_numpy()
        for i in idx:
            e = out.setdefault(vals[i], ([], [], []))
            e[0].append(float(tokey[i])); e[1].append(int(tacct[i])); e[2].append(int(tday[i]))
        return out

    reads_t = index_by(gi)
    reads_p = index_by(li)
    like_codes = {TYPE_CODES[x] for x in mc.LIKE_TYPES}
    tt = t["type"].map(TYPE_CODES).to_numpy()
    wmask = (t["kind"] == "write").to_numpy() & np.isin(tt, list(like_codes))
    widx = np.flatnonzero(wmask)
    widx = widx[np.argsort(tokey[widx], kind="stable")]
    writes: dict[str, tuple[list[float], list[int], list[int], list[int]]] = {}
    vals = t["artefact"].to_numpy()
    evs = t["ev"].to_numpy()
    for i in widx:
        e = writes.setdefault(vals[i], ([], [], [], []))
        e[0].append(float(tokey[i])); e[1].append(int(tacct[i])); e[2].append(int(tday[i]))
        e[3].append(int(evs[i]))

    def readers_after(src: tuple[list[float], list[int], list[int]] | None, ok: float,
                      day: int, A: int, acc: dict[int, tuple[float, int]]) -> None:
        if not src:
            return
        oks, accs, days = src
        j = bisect.bisect_right(oks, ok)
        while j < len(oks) and days[j] <= day + MAX_W - 1:
            B = accs[j]
            if B != A and (B not in acc or oks[j] < acc[B][0]):
                acc[B] = (oks[j], days[j])
            j += 1

    rows: dict[str, list[tuple]] = {"strict": [], "loose": []}
    for (ev, A, day, ok, ticket, project), ids in zip(
            tick[["ev", "acct", "day_rel", "okey", "ticket", "project"]].itertuples(index=False,
                                                                                 name=None),
            idents):
        if not ids:
            continue
        rs: dict[int, tuple[float, int]] = {}
        if ticket:
            readers_after(reads_t.get(ticket), ok, day, A, rs)
        rl = dict(rs)
        if project:
            readers_after(reads_p.get(project), ok, day, A, rl)
        for variant, readers in (("strict", rs), ("loose", rl)):
            if not readers:
                continue
            seen: set[int] = set()
            for R in ids:
                src = writes.get(R)
                if not src:
                    continue
                oks, accs, days, wev = src
                j = bisect.bisect_right(oks, ok)
                while j < len(oks) and days[j] <= day + MAX_W - 1:
                    B = accs[j]
                    rb = readers.get(B)
                    if rb is not None and oks[j] > rb[0] and wev[j] not in seen:
                        seen.add(wev[j])
                        rows[variant].append((int(ev), wev[j], int(A), B, int(day), rb[1],
                                              days[j], R, R == ticket))
                    j += 1
    cols = ["rec", "act_ev", "A", "B", "rec_day", "read_day", "act_day", "R", "R_is_ticket"]
    handoffs = {k: _typed_empty(pd.DataFrame(v, columns=cols),
                                ["rec", "act_ev", "A", "B", "rec_day", "read_day", "act_day"],
                                ["R_is_ticket"])
                for k, v in rows.items()}
    log(f"[{ci.corpus}] G2 handoffs strict={len(handoffs['strict']):,} "
        f"loose={len(handoffs['loose']):,} in {time.time()-t0:.1f}s")

    # ---- G5 mentions
    users = frozenset(template.usernames)
    full = {v: k for k, v in template.full_names.items() if v}
    mrows: list[tuple] = []
    for ev, B, day, ok, rkind, scope, text, assignee in rd[
            ["ev", "acct", "day_rel", "okey", "rkind", "scope", "text", "assignee"]
    ].itertuples(index=False, name=None):
        if pd.isna(B):
            continue
        hit = mc.name_mentions(text, users, full) if text else set()
        if assignee and assignee in users:
            hit.add(assignee)
        Bn = ci.accounts[int(B)]
        hit.discard(Bn)
        like = scope == "likeforlike"
        for a in hit:
            mrows.append((int(ev), int(B), ci.acc_idx[a], int(day), like))
    mentions = _typed_empty(pd.DataFrame(mrows, columns=["rec", "B", "A", "day", "like"]),
                            ["rec", "B", "A", "day"], ["like"])
    log(f"[{ci.corpus}] G5 mentions {len(mentions):,} in {time.time()-t0:.1f}s")
    diag = {"g2_vocabulary_size": len(vocab), "g2_ticket_records": int(len(tick)),
            "g2_records_with_identifier": int(sum(1 for x in idents if x)),
            "g2_extra_matches_if_trailing_dot_colon_stripped": int(extra)}
    return {"handoffs": handoffs, "mentions": mentions, "naming": naming, "diagnostics": diag}


def _typed_empty(df: pd.DataFrame, int_cols: Sequence[str],
                 bool_cols: Sequence[str] = ()) -> pd.DataFrame:
    """An empty handoff / mention frame gets integer index columns (a corpus with no G2
    handoff or no G5 mention, e.g. a small fork corpus); non-empty frames are unchanged."""
    if len(df):
        return df
    return df.astype({**{c: np.int64 for c in int_cols}, **{c: bool for c in bool_cols}})


def restrict(ci: CorpusIndex, keep: Iterable[str]) -> CorpusIndex:
    """The index restricted to events by the accounts in `keep` (section 5, N-scaling):
    artefacts created by excluded accounts remain as objects but lose their touches."""
    keep_idx = np.array(sorted(ci.acc_idx[a] for a in keep if a in ci.acc_idx), dtype=np.int64)
    kmask = np.zeros(ci.n, dtype=bool)
    kmask[keep_idx] = True
    tm = kmask[ci.t_acct]
    am = kmask[ci.ad_acct]
    active = ci.active & kmask[None, :]
    ho = {k: v[kmask[v["A"].to_numpy()] & kmask[v["B"].to_numpy()]].reset_index(drop=True)
          for k, v in ci.handoffs.items()}
    me = ci.mentions
    me = me[kmask[me["A"].to_numpy()] & kmask[me["B"].to_numpy()]].reset_index(drop=True)
    lm = kmask[ci.lw_acct]
    return replace(
        ci, ad_acct=ci.ad_acct[am], ad_day=ci.ad_day[am], active=active,
        days=np.unique(ci.ad_day[am]),
        t_acct=ci.t_acct[tm], t_day=ci.t_day[tm], t_okey=ci.t_okey[tm],
        t_tsmin=ci.t_tsmin[tm], t_type=ci.t_type[tm], t_art=ci.t_art[tm],
        t_write=ci.t_write[tm], handoffs=ho, mentions=me, naming=None,
        lw_acct=ci.lw_acct[lm], lw_day=ci.lw_day[lm], lw_okey=ci.lw_okey[lm],
        lw_value=ci.lw_value[lm], lw_type=ci.lw_type[lm], diagnostics=dict(ci.diagnostics))


# ----------------------------------------------------------------------------------
# Window helpers
# ----------------------------------------------------------------------------------

@dataclass
class Win:
    """Touches of one window (section 3) restricted to the scope's types."""
    acct: np.ndarray
    day: np.ndarray
    okey: np.ndarray
    tsmin: np.ndarray
    type: np.ndarray
    art: np.ndarray
    write: np.ndarray


def window_touches(ci: CorpusIndex, d: int, w: int, scope: str,
                   types: Sequence[str] | None = None) -> Win:
    lo, hi = ci.window(d, w)
    codes = np.array([TYPE_CODES[x] for x in (types or mc.scope_types(scope))])
    m = np.isin(ci.t_type[lo:hi], codes)
    s = slice(lo, hi)
    return Win(ci.t_acct[s][m], ci.t_day[s][m], ci.t_okey[s][m], ci.t_tsmin[s][m],
               ci.t_type[s][m], ci.t_art[s][m], ci.t_write[s][m])


def cooc(acct: np.ndarray, art: np.ndarray, n: int) -> np.ndarray:
    """L[a, b] = number of distinct artefacts both a and b appear with (diag = 0)."""
    L = np.zeros((n, n), dtype=np.float64)
    if len(acct) == 0:
        return L
    pairs = np.unique(np.stack([art, acct], axis=1), axis=0)
    ua, inv = np.unique(pairs[:, 0], return_inverse=True)
    M = sp.csr_matrix((np.ones(len(pairs)), (pairs[:, 1], inv)), shape=(n, len(ua)))
    L = (M @ M.T).toarray()
    np.fill_diagonal(L, 0.0)
    return L


def first_touches(win: Win) -> pd.DataFrame:
    """First touch (by okey) of each (account, artefact) within the window (G4)."""
    df = pd.DataFrame({"acct": win.acct, "art": win.art, "day": win.day, "tsmin": win.tsmin,
                       "okey": win.okey})
    df = df.sort_values("okey", kind="stable").drop_duplicates(["acct", "art"], keep="first")
    return df


# ----------------------------------------------------------------------------------
# Groups
# ----------------------------------------------------------------------------------

@dataclass
class Groups:
    """Groups emitted on day d: sizes, member lists and review pairs (acct*DAYCODE+day)."""
    sizes: np.ndarray
    members: list[tuple[int, ...]]
    review: np.ndarray

    @staticmethod
    def empty() -> "Groups":
        return Groups(np.zeros(0, dtype=np.int64), [], np.zeros(0, dtype=np.int64))


def _touch_groups(win: Win, memb: pd.DataFrame, d: int, want_members: bool) -> Groups:
    """Emit artefact groups (membership `memb`: art, acct) touched on day d by a member;
    review pairs = members x days in window on which they touched the artefact."""
    if len(memb) == 0:
        return Groups.empty()
    tw = pd.DataFrame({"acct": win.acct, "art": win.art, "day": win.day}).drop_duplicates()
    today = tw[tw["day"] == d][["art", "acct"]].drop_duplicates()
    hit = memb.merge(today, on=["art", "acct"])["art"].unique()
    me = memb[memb["art"].isin(hit)]
    if len(me) == 0:
        return Groups.empty()
    sizes = me.groupby("art").size().to_numpy()
    rv = me.merge(tw, on=["art", "acct"])
    review = np.unique(rv["acct"].to_numpy() * DAYCODE + rv["day"].to_numpy())
    members = ([tuple(sorted(g)) for _, g in me.groupby("art")["acct"]] if want_members else [])
    return Groups(sizes, members, review)


def apply_min_link(memb: pd.DataFrame, L: np.ndarray, min_link: float) -> pd.DataFrame:
    """Rule T support (TRACK-B part 2 draft section 2): keep only the groups (membership
    rows `art, acct`) whose strongest pairwise link max_{a != b in group} L[a, b] is at
    least `min_link`. `min_link <= 1` returns `memb` unchanged (every emitted G1 / G3 /
    G4 group has a pair with L >= 1, so t = 1 is the unthresholded generator)."""
    if min_link <= 1 or len(memb) == 0:
        return memb
    keep = [art for art, g in memb.groupby("art")["acct"]
            if group_strength(L, g.to_numpy()) >= min_link]
    return memb[memb["art"].isin(keep)]


def group_strength(L: np.ndarray, members: Sequence[int] | np.ndarray) -> float:
    """Strongest pairwise link of a group: max over ordered pairs a != b of L[a, b]."""
    m = np.asarray(members, dtype=np.int64)
    if len(m) < 2:
        return 0.0
    sub = L[np.ix_(m, m)].copy()
    np.fill_diagonal(sub, -np.inf)
    return float(sub.max())


def g1(ci: CorpusIndex, d: int, w: int, scope: str, *, types: Sequence[str] | None = None,
       want_groups: bool = True, want_members: bool = False, min_link: float = 1
       ) -> tuple[Groups, np.ndarray]:
    """G1, shared-artefact write co-touch (section 2). Group for artefact x = accounts
    with a write touch on x in the window; L1 = artefacts (types in scope) both wrote.
    `types` restricts to one type (L1_t); G3 is G1 on tickets. `min_link` (Rule T)
    drops groups whose strongest pairwise L1 is below it; L is returned unthresholded."""
    win = window_touches(ci, d, w, scope, types)
    wm = win.write
    L = cooc(win.acct[wm], win.art[wm], ci.n)
    if not want_groups:
        return Groups.empty(), L
    wr = pd.DataFrame({"art": win.art[wm], "acct": win.acct[wm]}).drop_duplicates()
    cnt = wr.groupby("art").size()
    memb = wr[wr["art"].isin(cnt[cnt >= 2].index)]
    memb = apply_min_link(memb, L, min_link)
    return _touch_groups(win, memb, d, want_members), L


def g3(ci: CorpusIndex, d: int, w: int, scope: str, **kw: Any) -> tuple[Groups, np.ndarray]:
    """G3, same-ticket participation: G1 restricted to tickets (section 2)."""
    return g1(ci, d, w, scope, types=("ticket",), **kw)


def g4(ci: CorpusIndex, d: int, w: int, scope: str, tau: float, *, want_groups: bool = True,
       want_members: bool = False, _ft: pd.DataFrame | None = None,
       _win: Win | None = None, min_link: float = 1) -> tuple[Groups, np.ndarray]:
    """G4, temporal burst (section 2): first touches (write or read) of the same artefact
    within the window, same simulated day, |delta ts| <= tau minutes (symmetric).
    L4 = number of such artefacts; group = accounts whose first touch is on the day of,
    and within tau of, the artefact's earliest first touch. `min_link` (Rule T) drops
    groups whose strongest pairwise L4 is below it."""
    win = _win if _win is not None else window_touches(ci, d, w, scope)
    ft = _ft if _ft is not None else first_touches(win)
    L = g4_links(ft, ci.n, (tau,))[tau]
    if not want_groups:
        return Groups.empty(), L
    cnt = ft.groupby("art").size()
    f2 = ft[ft["art"].isin(cnt[cnt >= 2].index)]
    if len(f2) == 0:
        return Groups.empty(), L
    e = f2.sort_values("okey", kind="stable").drop_duplicates("art", keep="first")
    e = e.set_index("art")[["day", "tsmin"]].rename(columns={"day": "eday", "tsmin": "ets"})
    j = f2.join(e, on="art")
    j = j[(j["day"] == j["eday"]) & ((j["tsmin"] - j["ets"]).abs() <= tau)]
    c2 = j.groupby("art").size()
    memb = j[j["art"].isin(c2[c2 >= 2].index)][["art", "acct"]]
    memb = apply_min_link(memb, L, min_link)
    return _touch_groups(win, memb, d, want_members), L


def g4_links(ft: pd.DataFrame, n: int, taus: Sequence[float]) -> dict[float, np.ndarray]:
    out = {tau: np.zeros((n, n), dtype=np.float64) for tau in taus}
    cnt = ft.groupby("art").size()
    f2 = ft[ft["art"].isin(cnt[cnt >= 2].index)][["art", "acct", "day", "tsmin"]]
    if len(f2) == 0:
        return out
    pr = f2.merge(f2, on=["art", "day"], suffixes=("_a", "_b"))
    pr = pr[pr["acct_a"] != pr["acct_b"]]
    dt = (pr["tsmin_a"] - pr["tsmin_b"]).abs().to_numpy()
    a = pr["acct_a"].to_numpy()
    b = pr["acct_b"].to_numpy()
    for tau in taus:
        m = dt <= tau
        np.add.at(out[tau], (a[m], b[m]), 1.0)
    return out


def _handoffs_in(ci: CorpusIndex, variant: str, d: int, w: int, emitted_only: bool
                 ) -> pd.DataFrame:
    h = ci.handoffs[variant]
    lo = d - w + 1
    if emitted_only:
        m = (h["act_day"].to_numpy() == d) & (h["rec_day"].to_numpy() >= lo)
    else:
        m = (h["act_day"].to_numpy() <= d) & (h["rec_day"].to_numpy() >= lo)
    return h[m]


def g2(ci: CorpusIndex, d: int, w: int, scope: str, variant: str = "strict", *,
       want_groups: bool = True, want_members: bool = False) -> tuple[Groups, np.ndarray]:
    """G2, handoff (section 2). A handoff = A's ticket record naming R, then B's read of
    that ticket (strict: get_issue; loose: also list_issues on its project) after A's
    write, then B's write touch with R as argument; record, read and action all inside
    the window. L2[A, B] = (record, action) handoffs. The group {A, B} of a handoff is
    emitted on the day of B's action; review pairs (A, record day), (B, read day),
    (B, action day). G2 is defined on like-for-like types; both scopes give the same G2."""
    h = _handoffs_in(ci, variant, d, w, emitted_only=False)
    L = np.zeros((ci.n, ci.n), dtype=np.float64)
    np.add.at(L, (h["A"].to_numpy(), h["B"].to_numpy()), 1.0)
    if not want_groups:
        return Groups.empty(), L
    e = h[h["act_day"].to_numpy() == d]
    if len(e) == 0:
        return Groups.empty(), L
    A = e["A"].to_numpy(); B = e["B"].to_numpy()
    review = np.unique(np.concatenate([A * DAYCODE + e["rec_day"].to_numpy(),
                                       B * DAYCODE + e["read_day"].to_numpy(),
                                       B * DAYCODE + e["act_day"].to_numpy()]))
    members = [tuple(sorted(x)) for x in zip(A.tolist(), B.tolist())] if want_members else []
    return Groups(np.full(len(e), 2, dtype=np.int64), members, review), L


def g5(ci: CorpusIndex, d: int, w: int, scope: str, *, want_groups: bool = True,
       want_members: bool = False) -> tuple[Groups, np.ndarray]:
    """G5, name co-mention (section 2): L5[B, A] = records written by B in the window
    naming A (username or full name as whole tokens; like-for-like: ticket text and
    `assignee`; all-services adds mail, chat, commit and MR text). Group {A, B} per
    (record, A) emitted on the record's day; review pairs (B, d) and (A, d) when A is
    active on d (A did not touch the record)."""
    me = ci.mentions
    m = (me["day"].to_numpy() >= d - w + 1) & (me["day"].to_numpy() <= d)
    if scope == "likeforlike":
        m &= me["like"].to_numpy()
    x = me[m]
    L = np.zeros((ci.n, ci.n), dtype=np.float64)
    if len(x):
        rb = x[["rec", "B", "A"]].drop_duplicates()
        np.add.at(L, (rb["B"].to_numpy(), rb["A"].to_numpy()), 1.0)
    if not want_groups:
        return Groups.empty(), L
    e = x[x["day"].to_numpy() == d][["rec", "B", "A"]].drop_duplicates()
    if len(e) == 0:
        return Groups.empty(), L
    A = e["A"].to_numpy(); B = e["B"].to_numpy()
    actA = ci.active[d, A]
    review = np.unique(np.concatenate([B * DAYCODE + d, A[actA] * DAYCODE + d]))
    members = [tuple(sorted(p)) for p in zip(A.tolist(), B.tolist())] if want_members else []
    return Groups(np.full(len(e), 2, dtype=np.int64), members, review), L


def interaction_w(win: Win, n: int) -> np.ndarray:
    """W[a, b] = artefact instances both touched (write or read) in the window (G6)."""
    return cooc(win.acct, win.art, n)


def g6_scores(W: np.ndarray) -> np.ndarray:
    """S[s, c] = W[s, c] / sqrt(deg(s) deg(c)), deg(a) = sum_x W(a, x), x != a (G6)."""
    deg = W.sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        S = W / np.sqrt(np.outer(deg, deg))
    S[~np.isfinite(S)] = 0.0
    np.fill_diagonal(S, 0.0)
    return S


def g6(ci: CorpusIndex, d: int, w: int, scope: str, *, want_groups: bool = False,
       want_members: bool = False) -> tuple[Groups, np.ndarray]:
    """G6, one-step suspicion propagation (section 2). Emits no groups in B1."""
    win = window_touches(ci, d, w, scope)
    return Groups.empty(), g6_scores(interaction_w(win, ci.n))


# ----------------------------------------------------------------------------------
# All link strengths of a window at once (B0)
# ----------------------------------------------------------------------------------

def link_matrices(ci: CorpusIndex, d: int, w: int, scope: str,
                  per_type: bool = True) -> dict[str, np.ndarray]:
    """L(a, b) for every generator variant on (d, w, scope); keys VARIANTS plus
    `G1:<type>` per type in scope (sections 2 and 4)."""
    win = window_touches(ci, d, w, scope)
    out: dict[str, np.ndarray] = {}
    L1 = np.zeros((ci.n, ci.n))
    for t in mc.scope_types(scope):
        m = (win.type == TYPE_CODES[t]) & win.write
        Lt = cooc(win.acct[m], win.art[m], ci.n)
        L1 += Lt
        if per_type:
            out[f"G1:{t}"] = Lt
        if t == "ticket":
            out["G3"] = Lt
    out["G1"] = L1
    ft = first_touches(win)
    l4 = g4_links(ft, ci.n, TAUS)
    out["G4-60"], out["G4-180"] = l4[60], l4[180]
    out["G2-strict"] = g2(ci, d, w, scope, "strict", want_groups=False)[1]
    out["G2-loose"] = g2(ci, d, w, scope, "loose", want_groups=False)[1]
    out["G5"] = g5(ci, d, w, scope, want_groups=False)[1]
    out["G6"] = g6_scores(interaction_w(win, ci.n))
    return out


# ----------------------------------------------------------------------------------
# Section 4: ranks
# ----------------------------------------------------------------------------------

def rank_partner(Lrow: np.ndarray, cand: np.ndarray, p: int) -> dict[str, float]:
    """Pessimistic / optimistic rank of partner p among candidates (section 4).

    `cand` is a boolean mask of candidates (accounts active in the window, seed
    excluded). r_pess = 1 + #{c in cand, c != p : L(c) >= L(p)} (ties against the
    defender; a partner with L = 0 gets the number of candidates when it is one);
    r_opt = 1 + #{c in cand : L(c) > L(p)}; honest_above = #{c in cand : L(c) > L(p)}.
    """
    lp = float(Lrow[p])
    others = cand.copy()
    others[p] = False
    vals = Lrow[others]
    r_pess = 1 + int((vals >= lp).sum())
    above = int((vals > lp).sum())
    return {"L": lp, "r_pess": r_pess, "r_opt": 1 + above, "honest_above": above,
            "n_cand": int(cand.sum())}


def budget_cap(B: float, n_active: int) -> int:
    """max(1, floor(B * N_active(d))) (section 4)."""
    return max(1, int(np.floor(B * n_active + 1e-9)))


# ----------------------------------------------------------------------------------
# Section 5 helpers
# ----------------------------------------------------------------------------------

def pct(a: Sequence[float] | np.ndarray, q: float) -> float:
    a = np.asarray(a, dtype=float)
    if a.size == 0:
        return float("nan")
    return float(np.percentile(a, q))


def unrequested_rate(ci: CorpusIndex, w: int) -> dict[str, Any]:
    """G2 right tail: share of like-for-like write touches for which no ticket record by
    any account named the value beforehand within the window (section 2), by type."""
    assert ci.naming is not None
    tot: dict[str, int] = {}
    unreq: dict[str, int] = {}
    for v, ok, dd, ty in zip(ci.lw_value, ci.lw_okey, ci.lw_day, ci.lw_type):
        tname = mc.ALL_TYPES[int(ty)]
        tot[tname] = tot.get(tname, 0) + 1
        nmv = ci.naming.get(v)
        req = False
        if nmv is not None:
            j = int(np.searchsorted(nmv[0], ok, side="left")) - 1
            if j >= 0 and nmv[1][j] >= dd - w + 1:
                req = True
        if not req:
            unreq[tname] = unreq.get(tname, 0) + 1
    T = sum(tot.values())
    U = sum(unreq.values())
    return {"n_write_touches": T, "n_unrequested": U, "rate": U / T if T else float("nan"),
            "by_type": {k: {"n": tot[k], "unrequested": unreq.get(k, 0),
                            "rate": unreq.get(k, 0) / tot[k]} for k in sorted(tot)}}
