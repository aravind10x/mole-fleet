# FT red-side certification (red side; content-free; 2026-11-13)

Hashes are of the files as they stand when the red side stops. After this file, nothing under `work/stage3/red/ft/` changes until the coordinator says the blocks have landed.

## Final hashes (sha256)

| file | sha256 |
|---|---|
| `cells-manifest.json` | `7f44e41c9e26eac479c1349b8c950701a32ed7e67de130c589ddab540c177e9d` |
| `cells-manifest-dose.json` | `5e4a1dbf4fd7e926d42371da4d4a70166d65a95aaa88da2c97591a5593349797` |
| `predicates.py` | `4737b1caa0823fe0fab1cb3f5446c94db6cdbf88782f847668c65adcc77afb38` |
| `predicate-specs.json` | `c82f22863dc9a4df0029dc281d2b13605447d04041f51aa616a07cb833b81998` |
| `selection-rules.md` | `dbe34c5054a8041f39356714fef4af4e6c22500a1c5719c1076e56a651f48730` |
| `dose-draw-rule.md` | `369c9cafb74ef01985156f390eb53c663266969e83e6a1882f43ebaa5a84839f` |
| `dose-draw-v0.json` | `983d7587a122f5ba9058745bcd7098d4b00d5b096bab63b9e375bf6779d2195d` |
| `audit-rule.md (amended)` | `7b3170928f5b23d463ecd38df99935f7f712be0edcbcccf50f25abf7c3621e2e` |
| frozen documents, `docs/` (the runner's tree hash, `stage3_ft_run.docs_tree_sha256`) | `543ab3ecc6480107f0f59ef4a39470f54684e92b1e161143cc565f0a5b495dc5` |

Supporting code (hashed for the record; the runner need not check them): `ft_select.py` `d06e2f98`, `ft_dose.py` `c32e9ce0`, `ft_freeze.py` `1db8a863`, `ft_literal_statements.py` `cd1463ba`, `ft_reader_identical.py` `f36f47bc`, `ft_audit_prepare.py` `646c07d8`, `ft_audit_join.py` `f3625b45`, `ft_census.py` `2cb16c9e`, `ft_part3_supply.py` `2caaaa07`.

The tree hash in `red-census.md` (Part R1) was taken before the dose cells were added and used a different format; the one above is the current one.

## Statements

- Predicates are code (`predicates.py` with `predicate-specs.json`) evaluated on action logs. They are never shown to any model: no prompt, task, tool description or colleague prompt carries a predicate, a literal or a spec.
- No outcomes file and no transcript has been read by the red side. The audit scripts have been run only on synthetic transcripts in their tests; no real outcomes exist.
- No model call was made on the red side; cost $0.

## Test modules (run by module name under `work/mole-fork/.venv/bin/python -m pytest -q`, exit code kept)

| module | result | sha256[:8] |
|---|---|---|
| `test_ft_freeze.py` | PASS: 13 passed in 0.71s | `d105e090` |
| `test_ft_select.py` | PASS: 156 passed in 0.11s | `f56f0fcf` |
| `test_ft_dose.py` | PASS: 9 passed in 0.64s | `9837c3a8` |
| `test_ft_audit.py` | PASS: 11 passed in 0.18s | `10f01941` |

Total passed: 189.
