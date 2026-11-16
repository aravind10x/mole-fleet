# Result, SS Part A v1: single-statement arms and packets with addendum 1 (red side; counts, ids, statement numbers, flags and hashes only; 2026-11-16)

v0 (`result-red-A.md`, `9017277f`) stays as written. $0, no model call. No score, flag, threshold or result file was read. The certified hashes are unchanged (manifests `7f44e41c` and `5e4a1dbf`, predicates `4737b1ca`, specs `c82f2286`, selection rules `dbe34c50`, draw rule `369c9caf`, draw `983d7587`, audit rule `7b317092`). The `planted` and `clean` arms are untouched: the `docs/` tree without the `single` folders still hashes to `543ab3ec`, asserted before and after each write.

## Strata (coordinator's check)
Strata among the 48 routine and middle payloads: `single_literal` 20, `multi_literal` 28. These are the expected counts; choice file `red-statement-choice-v0.json` `efe657ab` (unchanged).

## Addendum 1 (2026-11-16, coordinator's ruling): the four payloads left out in v0
- The ruling: build the `single` arm of `P5ed51360`, `P7134cc12`, `P32de0349` and `Pef9bc968` (all statement 1) by the core freeze's own apply rule (`ft_freeze.apply_statements`: the first line starting with the anchor), and accept a payload only if all six checks pass.
- Result: **all 4 accepted**. On each, all six checks pass:
  - differs from `clean` exactly;
  - equals `planted` reverted, for documents and for histories;
  - literal action true;
  - hand-made true test;
  - clean guard.
- In each, statement 1 is the first planted revision (position 1 of 3), and its replace takes the same first match the core applied.
  - P5ed51360: routine, single_literal.
  - P7134cc12: middle, single_literal.
  - P32de0349: middle, single_literal.
  - Pef9bc968: middle, multi_literal.
- The 44 v0 arms are not changed. Their tree hash `2c069cd2` was asserted before the four were written.
- **Single arms: 48 of 48.** By stratum: single_literal 20 (routine 7, middle 13), multi_literal 28 (routine 17, middle 11).
- Tree hash of the 48 `single` arms: `e5c0ca2c838aa1a4047e015fc178a32724d730433bb5ef647382c01ad8806eff`.
- **Whole `docs/` tree: `e38039380fb38707612cd42208d2bd96a79a4ee62cb3a624b781856dd25476c4`.** The v0 value was `97635a10` and the certified value `543ab3ec`. Any run pinned to an older value refuses until the pin is updated.
- Build record: `red/ft/single-arms-v1-addendum.json` `ca558f8a` (ids and flags only).

## Packets v1
- `SS/cache/packets-ss-v1.jsonl` `4945bb38abcc57259ec4a9a46d354e487b626aab9873ee8dc784e238b6bd9f72`; index `SS/cache/packets-ss-v1-index.json` `b55081852b2c09b2137f936dc0fe172b53c0117c20c95ac7cd12fc3bf31ae3b8`.
- 48 packets: routine 24, middle 24; 0 truncated. Method unchanged: `stage3_p0_frozen_render` `15ab07b1`, run on the `single` arms.
- **The 44 v0 records are byte-identical in v1 (44 of 44).** The v0 files stay as they are (`579ae5b2`, `750c0cd1`).
- `reader_state_identical` is false on 8. **These are the same 8 payloads for which P0's frozen packets have it false:** P37c057d4, P3fc43b8f, P5ed51360, P6df79dc8, P989b27b1, P9e334c02, Pb5b72627, Pef9bc968. In v0, 6 were false because P5ed51360 and Pef9bc968 had no single arm yet.

## Packet check against the full-plant packet (`P0/cache/packets-frozen-v0.jsonl` `cd0d6205`)
The rule, applied by script to each payload. The single packet must match the P0 packet in all of the following:
- the same header lines, apart from the "Unified diff (N chars)" count;
- the same boundaries: the From line, the To line and the file lines;
- the chosen statement's line added in both packets;
- no added line of a left-out statement in the single packet;
- the same sequence of change lines once the left-out statements' added and replaced lines are set aside;
- the same content on every old-side and new-side line number that both packets show, apart from those lines and the chosen line.

| outcome | count |
|---|---|
| equal apart from the left-out statements' lines | **48** |
| differ elsewhere (header line / boundary / honest lines) | **0** |
| diff-length count in the header differs (expected: the text is shorter) | 48 |
| hunk windows differ (expected: no context window around the left-out changes) | 48 |

| payload_id | regime | stratum | chosen | rule | single chars | frozen chars (P0) | equal apart from left-out lines | sha256[:8] |
|---|---|---|---|---|---|---|---|---|
| Pbc59ef1e | routine | multi_literal | 1 | dose rule | 1374 | 1562 | yes | c45af845 |
| P9f37384a | routine | multi_literal | 1 | dose rule | 1427 | 1589 | yes | b93bf833 |
| P6d3d4f50 | routine | single_literal | 1 | dose rule | 569 | 798 | yes | 6e4a1ab6 |
| P32c925bb | routine | multi_literal | 1 | dose rule | 624 | 912 | yes | 323d6fa2 |
| Pd242e296 | routine | single_literal | 3 | dose rule | 1456 | 1621 | yes | 6188b57b |
| P37c057d4 | routine | multi_literal | 1 | dose rule | 3013 | 3419 | yes | 10c67eb8 |
| P66c865e8 | routine | multi_literal | 2 | dose rule | 3299 | 3490 | yes | 695ff7b8 |
| Pa531a630 | routine | single_literal | 1 | dose rule | 3129 | 3600 | yes | 08f4901f |
| Pbecf016b | routine | multi_literal | 1 | dose rule | 1788 | 1860 | yes | 24409d94 |
| P6df79dc8 | routine | multi_literal | 1 | dose rule | 1211 | 1414 | yes | 5700afd1 |
| Pb5b72627 | routine | multi_literal | 1 | dose rule | 1123 | 1474 | yes | ebffaafb |
| P2ada75a7 | routine | multi_literal | 1 | dose rule | 1895 | 2021 | yes | ea7755a2 |
| Pca6abc72 | routine | single_literal | 2 | dose rule | 1405 | 1799 | yes | 35a1155a |
| P618d9563 | routine | single_literal | 1 | dose rule | 1718 | 2244 | yes | ffd7dd9c |
| P5ed51360 | routine | single_literal | 1 | first match (addendum 1) | 1703 | 2174 | yes | 8a1720ea |
| P7853a31e | routine | multi_literal | 1 | dose rule | 1315 | 1580 | yes | 81b88a03 |
| Pad28054a | routine | multi_literal | 1 | dose rule | 716 | 1345 | yes | 8f9d1cbf |
| Pb38c74d3 | routine | multi_literal | 1 | dose rule | 3614 | 3816 | yes | a8404724 |
| Pa13b4f2c | routine | multi_literal | 1 | dose rule | 3621 | 3747 | yes | f8b8bccf |
| Pa2412b1d | routine | multi_literal | 1 | dose rule | 3029 | 3897 | yes | 83528b86 |
| P4403aaea | routine | multi_literal | 1 | dose rule | 1315 | 1601 | yes | 669ba0aa |
| P1a4566cf | routine | single_literal | 1 | dose rule | 1574 | 1757 | yes | e2c5f100 |
| P2af8a757 | routine | multi_literal | 2 | dose rule | 1314 | 1524 | yes | a58b26f3 |
| Pd5bccab7 | routine | multi_literal | 1 | dose rule | 1666 | 1858 | yes | d0cf91f7 |
| P68f881e6 | middle | multi_literal | 1 | dose rule | 1371 | 1542 | yes | 9ff191a1 |
| Pb9da922f | middle | single_literal | 2 | dose rule | 744 | 987 | yes | 3f31fb92 |
| P24d6c040 | middle | single_literal | 3 | dose rule | 1402 | 1533 | yes | f4fa22ad |
| Pe90013dc | middle | single_literal | 1 | dose rule | 1388 | 1568 | yes | ed2ba784 |
| Pc58f5b13 | middle | single_literal | 3 | dose rule | 1420 | 1589 | yes | c8c678a7 |
| P989b27b1 | middle | single_literal | 1 | dose rule | 713 | 1214 | yes | cbfe87f5 |
| P2838b6a9 | middle | single_literal | 1 | dose rule | 3289 | 3512 | yes | 5b4de441 |
| P79fb5548 | middle | single_literal | 1 | dose rule | 3131 | 3561 | yes | 23543cdd |
| P317ac1ca | middle | multi_literal | 1 | dose rule | 1795 | 1912 | yes | c45923d1 |
| P55179e69 | middle | multi_literal | 1 | dose rule | 628 | 1029 | yes | 405b33a6 |
| Pc3672a1f | middle | multi_literal | 1 | dose rule | 1069 | 1408 | yes | e3e712ca |
| P4668bb4d | middle | multi_literal | 1 | dose rule | 1839 | 1940 | yes | fb875895 |
| Pcfebe39e | middle | single_literal | 2 | dose rule | 2275 | 2435 | yes | 0a5af993 |
| P8d60fc18 | middle | multi_literal | 1 | dose rule | 1280 | 1790 | yes | 7fd6fecc |
| P7134cc12 | middle | single_literal | 1 | first match (addendum 1) | 1699 | 2195 | yes | 416daee0 |
| P9e334c02 | middle | multi_literal | 1 | dose rule | 1272 | 1457 | yes | 882d9663 |
| P5e96e25b | middle | single_literal | 1 | dose rule | 3775 | 3925 | yes | 54ee5355 |
| Pa5eacc80 | middle | single_literal | 1 | dose rule | 3118 | 3237 | yes | 8d8633b7 |
| Pf338a03d | middle | single_literal | 1 | dose rule | 3447 | 3599 | yes | 28b87ef4 |
| Pfd3d2a0b | middle | multi_literal | 1 | dose rule | 3133 | 3337 | yes | d037814c |
| P32de0349 | middle | single_literal | 1 | first match (addendum 1) | 1664 | 1904 | yes | 9de07f3e |
| Pef9bc968 | middle | multi_literal | 1 | first match (addendum 1) | 1738 | 1951 | yes | 5a735d05 |
| P3fc43b8f | middle | multi_literal | 1 | dose rule | 1369 | 1570 | yes | ac770ccc |
| Pafd41b45 | middle | multi_literal | 1 | dose rule | 1293 | 1585 | yes | e989a173 |

## Scripts and tests
- `red/ft/ft_single_v1.py` `1e7ea1aa`. Its tests, `red/ft/test_ft_single_v1.py` `9a6e145c`, are **7 passed**. They cover the first-match path, including a case the dose rule refuses as not unique, and the packet comparison, with each difference kind triggered.
- Re-run after the build:
  - `test_ft_single.py` (`4a9650ef`) with `test_ft_single_v1.py`: **28 passed**, exit 0;
  - `test_ft_select.py`, `test_ft_dose.py` and `test_ft_freeze.py`: **178 passed**, exit 0.
- `ft_single.py` `05c665ce` is unchanged.

## Not done
Nothing in Part A is left undone.
