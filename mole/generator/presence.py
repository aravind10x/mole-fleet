"""ONE presence rule for every member class and for the coalition planner (L15 rule 4; brief
07b F1.7, after the branch review's "two planners" finding).

A background account's presence on a simulated day (whole-day absence, then which of its
planned slots it loafs) is drawn from a stream keyed by (rng seed, day), not from the member's
main RNG. Two consequences, both load-bearing:

* The coalition planner (`campaign.build_campaign(acts_on_day=...)`, reached through
  `run.campaign_schedule_for`) can know BEFORE the run whether an account acts on a day, so a
  role's day is drawn, re-drawn inside its rank slice, or refused loudly, the same way in
  rules mode and in agentic mode. The agentic member no longer forces a session on a role day.
* A day's draw never shifts another day's: the rules `Member` (n = sessions x touch-points
  slots) and the `AgenticMember` (n = sessions slots) draw the same absence for the same
  (seed, day) and the same loaf decisions on their first `sessions` slots, so a rules-mode
  rehearsal's presence agrees with the agentic run's on every day the planner reads.

Erratum, dated 2026-10-20: before this module presence came from the member's main RNG,
interleaved with its agenda and timing draws, so it could not be known before the run;
honest scheduling for a given seed therefore differs from the `stage2b` code (the prefix and
the Stage 2b branches are frozen corpora and are not regenerated).
"""
from __future__ import annotations

import random
from collections.abc import Callable, Mapping
from typing import Any

__all__ = ["presence_rng", "day_presence", "acts_on_day", "acts_predicate"]


def presence_rng(rng_seed: int | None, day: str) -> random.Random:
    """The per-(seed, day) stream. A None seed gives an unseeded stream (not reproducible,
    as a seedless member never was)."""
    if rng_seed is None:
        return random.Random()
    return random.Random(f"presence:{int(rng_seed)}:{day[:10]}")


def day_presence(rng_seed: int | None, day: str, config: Any, n_slots: int) -> list[bool] | None:
    """None when the account is absent (PTO) that day; else one keep-flag per slot (False =
    loafed). Draw order: the absence draw first, then one loaf draw per slot."""
    rng = presence_rng(rng_seed, day)
    if config.absent_probability > 0 and rng.random() < config.absent_probability:
        return None
    return [not (rng.random() < config.loaf_probability) for _ in range(max(0, int(n_slots)))]


def acts_on_day(rng_seed: int | None, day: str, config: Any, sessions: int) -> bool:
    """True iff the account has at least one kept session that day (the agentic member's
    slot count: `max(1, sessions)`)."""
    mask = day_presence(rng_seed, day, config, max(1, int(sessions)))
    return mask is not None and any(mask)


def acts_predicate(seed: int | None, index_of: Mapping[str, int], config: Any,
                   sessions: int) -> Callable[[str | None, str], bool]:
    """The planner's predicate for a run: account -> its member seed is `seed + index`
    (`run.simulate` gives member i `rng_seed = seed + i`). An account not in `index_of` is
    not in the roster and never acts."""
    def _acts(account: str | None, day: str) -> bool:
        if account is None or account not in index_of:
            return False
        rng_seed = None if seed is None else int(seed) + int(index_of[account])
        return acts_on_day(rng_seed, day, config, sessions)
    return _acts
