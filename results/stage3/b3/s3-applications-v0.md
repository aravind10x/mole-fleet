# S3 applications (brief 33 A3): the one draw, 2026-11-01T20:17:45Z

`s3-applications-v0.json` sha256 **02edac2a88fbdd3d9cfd4404e496aac6991c2f917fd27ca191394dc225c229bc** (a never-open file: it holds applied document states and the packets). Module `stage3_t1.py` 240f4ed9 (restricted mode, valid draws `inserter-dry-run-v1.json` 02138931); corpus ffc1f6cd; template 294d59d2; plan.md a411d8a2; pre-flight PASS 26 of 26. Arm seeds {'1': 2026118110, '2': 2026118120, '3': 2026118130, '4': 2026118140, '6': 2026118160} (no tag 5). Window: the corpus span (build_world); units as planted_items; days ['2026-04-06', '2026-04-07', '2026-04-08']. Wall time 626 s.

| count | got | expected |
|---|---|---|
| items | 232 | 232 |
| lines | 564 | 564 |
| candidate_items | 146 | 146 |
| control_items | 42 | 42 |
| sham_items | 44 | 44 |
| candidate_lines | 438 | 438 |
| control_lines | 126 | 126 |
| units | 796 | 796 |

Counts equal the plan's: **True**. By stream tag: {'tag1': 146, 'tag2': 438, 'tag3': 42, 'tag4': 44, 'tag6': 126}. By day: {'2026-04-06': 319, '2026-04-07': 477}. By writer: {'glm53:items': 90, 'glm53:lines': 270, 'sonnet55:items': 98, 'sonnet55:lines': 294, 't1v2:items': 44}.

Id sets (section 2.5): full 73 (5dbd067d); controls 21 (3db4d199); sham 22 (27909dc2).

Refused draws at application time, by brief 27's reason class (section 2.4 (3), the module's `_draw_listed`, the next draw of the same stream taken): none. Re-draws per application: {'0': 748, '2': 4, '4': 2, '5': 2, '7': 2, '9': 2, '10': 36}.

S3's own drops (section 2.4 (4) and module-induced): **0**; every population is as pre-registered (S-S0).
Control items leaving the add-on only (S2's rule for tag 6): **0**.
