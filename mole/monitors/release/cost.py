"""Per-call cost record for release-judge calls.

Every judge (and per-day summary) call yields `{"tokens_in", "tokens_out", "dollars",
"cost_source", "tokens_estimated"}`:

  tokens   the client's reported usage (`resp.usage.input_tokens/output_tokens`); when the
           client reports none, chars/4 of the prompt and of the completion, and
           `tokens_estimated` is True.
  dollars  first that applies:
             "provider"     the client's reported `usage.cost_usd` (> 0)
             "price_hook"   `set_price_hook(fn)`: fn(model, tokens_in, tokens_out) -> USD or None
             "price_env"    env JUDGE_PRICE_PER_MTOK="<usd per 1M in>,<usd per 1M out>"
             "price_table"  PRICE_PER_MTOK[model] = (usd per 1M in, usd per 1M out)
             "unpriced"     0.0 (nothing known for this model)

PRICE_PER_MTOK ships empty on purpose: a stale hard-coded price would silently mis-state
oversight cost. Fill it (or the env var / hook) for backends that do not report cost.
"""
from __future__ import annotations

import os
from typing import Any, Callable

PRICE_PER_MTOK: dict[str, tuple[float, float]] = {}
_PRICE_HOOK: Callable[[str, int, int], float | None] | None = None


def set_price_hook(fn: Callable[[str, int, int], float | None] | None) -> None:
    global _PRICE_HOOK
    _PRICE_HOOK = fn


def _price(model: str, tin: int, tout: int) -> tuple[float, str]:
    if _PRICE_HOOK is not None:
        usd = _PRICE_HOOK(model, tin, tout)
        if usd is not None:
            return float(usd), "price_hook"
    env = os.environ.get("JUDGE_PRICE_PER_MTOK", "").strip()
    if env:
        p_in, p_out = (float(x) for x in env.split(","))
        return tin * p_in / 1e6 + tout * p_out / 1e6, "price_env"
    if model in PRICE_PER_MTOK:
        p_in, p_out = PRICE_PER_MTOK[model]
        return tin * p_in / 1e6 + tout * p_out / 1e6, "price_table"
    return 0.0, "unpriced"


def call_cost(resp: Any, *, model: str, prompt_chars: int) -> dict[str, Any]:
    """Cost record for one completed call (`resp` = the client's response object)."""
    usage = getattr(resp, "usage", None)
    content = getattr(resp, "content", "") or ""
    tin = int(getattr(usage, "input_tokens", 0) or 0) if usage is not None else 0
    tout = int(getattr(usage, "output_tokens", 0) or 0) if usage is not None else 0
    estimated = usage is None or (tin == 0 and tout == 0)
    if estimated:
        tin, tout = max(1, prompt_chars // 4), max(1, len(content) // 4)
    reported = float(getattr(usage, "cost_usd", 0.0) or 0.0) if usage is not None else 0.0
    if reported > 0:
        dollars, source = reported, "provider"
    else:
        dollars, source = _price(model, tin, tout)
    return {"tokens_in": tin, "tokens_out": tout, "dollars": round(dollars, 6),
            "cost_source": source, "tokens_estimated": estimated}


def ensure_cost_fields(v: dict[str, Any]) -> dict[str, Any]:
    """Backfill tokens_in/tokens_out/dollars on a verdict that only has the legacy
    input_tokens/output_tokens/cost_usd keys (or none, e.g. a failed call)."""
    out = dict(v)
    out.setdefault("tokens_in", int(out.get("input_tokens") or 0))
    out.setdefault("tokens_out", int(out.get("output_tokens") or 0))
    out.setdefault("dollars", round(float(out.get("cost_usd") or 0.0), 6))
    out.setdefault("cost_source", "error" if out.get("error") else "legacy")
    return out
