"""Release-level monitors for threat C3 (release-gate sabotage).

  cost             per-call cost record (tokens_in, tokens_out, dollars) for every judge call
  account_history  M2 at MOLE strength: one participant's trailing history with peer context
  graph            M4: the typed account -> object interaction graph, a bounded walk from a
                   release's objects, the non-LLM rarity-weighted path score and the
                   neighbourhood rendering for the LLM variant

All inputs are plain audit rows (dicts, one AuditEvent row each) and the managers.json
state dict. Nothing here reads generation-process timing (see
tests/test_monitor_views_no_timing.py).
"""
