# FPDS Corporate-Hierarchy Rebuild — Build Log

**Date:** 2026-08-05  
**Script:** `code/13_build_fpds_hierarchy.py`  
**Log:** `logs/13_fpds_hierarchy_2026-08-05.log`  
**Runtime:** 1.4 minutes

## Purpose

Rebuild the UEI parent/child edge list from raw FPDS + FSRS transaction rows so
that spiderweb attribution can propagate a verified Native-entity owner across a
whole corporate family. The previously used derived graph
(`data/raw/external/uei_hierarchy_graph.csv`) is almost entirely edgeless.

**Zero fabrication.** Every edge below is a literal (child, parent) pair present
on at least one observed transaction row. No name matching, no inference, no
transitive closure. Self-edges (child == parent) are dropped as uninformative and
counted separately.

## Identifier columns found in each source

| File | Rows | Child UEI col | Parent cols | CAGE col | Year col |
|---|---:|---|---|---|---|
| `Data Request 4-5-2023 File 1.csv` | 1,101,796 | `uei_id` (`uei_legal_business_name`) | `immediate_parent_uei`, `domestic_parent_uei`, `ultimate_parent_uei` (+ `_name`) | `cage_code` | `action_date_fiscal_year` |
| `Data Request 4-5-2023 File 2.csv` | 1,078,021 | same (316 cols, identical schema) | same | `cage_code` | `action_date_fiscal_year` |
| `Data Request 5-8-2023 IDVs.csv` | 100,074 | same (300 cols) | same | `cage_code` | `action_date_fiscal_year` |
| `contract-03-18-23-19-40-24.csv` | 4,000 | `Awardee UEI` (`Awardee Name`) | `Parent UEI` (`Awardee Parent Name`) | `Awardee Cage Code`, `Parent CAGE Code` | `Most Recent Action Date Fiscal Year` |
| `subcontract-05-09-23-22-23-37.csv` | 998 | `Sub Awardee UEI`, `Prime Awardee UEI` | `Sub Awardee Parent UEI`, `Prime Awardee Parent UEI` | `Sub Awardee Cage Code`, `Sub Awardee Parent Cage Code`, `CAGE Code` (x2, positional) | `Subaward Action Date Fiscal Year` |

Notes on schema gotchas:

- There is **no** `parent_uei` / `recipient_uei` / `awardee_uei` column in the three big
  FPDS extracts. The entity block is `uei_id` + `immediate_parent_uei` +
  `domestic_parent_uei` + `ultimate_parent_uei`, each with a paired `_name`.
- Legacy `recipient_duns` / `recipient_parent_duns` / `recipient_parent_name` also exist
  but are DUNS-era and are not used for UEI edges.
- `subcontract-05-09-23-22-23-37.csv` has **two columns both literally named `CAGE Code`**
  (positions 22 and 23 = prime CAGE and prime-parent CAGE). They are read positionally;
  a `pandas` name-based read would mangle them.

## Rows scanned per file

| File | Rows scanned | Bad/short rows skipped | csv parse errors | Distinct UEIs | New distinct edge keys |
|---|---:|---:|---:|---:|---:|
| `Data Request 4-5-2023 File 1.csv` | 1,101,796 | 0 | 0 | 13,129 | 1,755 |
| `Data Request 4-5-2023 File 2.csv` | 1,078,021 | 0 | 0 | 7,498 | 69 |
| `Data Request 5-8-2023 IDVs.csv` | 100,074 | 0 | 0 | 5,015 | 67 |
| `contract-03-18-23-19-40-24.csv` | 4,000 | 0 | 0 | 28 | 27 |
| `subcontract-05-09-23-22-23-37.csv` | 998 | 0 | 0 | 304 | 372 |
| **TOTAL** | **2,284,889** | **0** | **0** | **14,341 (union)** | **2,290** |

No malformed rows encountered: every data row parsed to the full header width.

## How often each parent column was actually populated

This is the key coverage fact for the rebuild. In the three big FPDS extracts the
`immediate_parent_uei` and `domestic_parent_uei` columns are present in the schema but
almost never filled; virtually all FPDS-side hierarchy comes from `ultimate_parent_uei`.

| File | Column | Rows with a value | Rows where value != child UEI |
|---|---|---:|---:|
| `Data Request 4-5-2023 File 1.csv` | `domestic_parent_uei` | 0 | 0 |
| `Data Request 4-5-2023 File 1.csv` | `immediate_parent_uei` | 0 | 0 |
| `Data Request 4-5-2023 File 1.csv` | `ultimate_parent_uei` | 1,101,617 | 394,476 |
| `Data Request 4-5-2023 File 2.csv` | `domestic_parent_uei` | 0 | 0 |
| `Data Request 4-5-2023 File 2.csv` | `immediate_parent_uei` | 0 | 0 |
| `Data Request 4-5-2023 File 2.csv` | `ultimate_parent_uei` | 1,077,830 | 437,576 |
| `Data Request 5-8-2023 IDVs.csv` | `domestic_parent_uei` | 0 | 0 |
| `Data Request 5-8-2023 IDVs.csv` | `immediate_parent_uei` | 0 | 0 |
| `Data Request 5-8-2023 IDVs.csv` | `ultimate_parent_uei` | 100,043 | 33,451 |
| `contract-03-18-23-19-40-24.csv` | `Parent UEI` | 4,000 | 3,998 |

## Distinct edges by type

| edge_type | distinct edges | meaning |
|---|---:|---|
| `parent_uei` | 182 | immediate/direct corporate parent |
| `domestic_parent_uei` | 0 | highest US-domiciled parent (extra type, see note) |
| `ultimate_parent_uei` | 1,891 | top of the corporate family |
| `prime_to_sub` | 217 | subawardee -> prime (CONTRACTING, not ownership) |
| **TOTAL** | **2,290** | |

Self-edges dropped (row-level occurrences): 1,414,332.
Rows where one side of a candidate edge was blank: 4,560,185.

> `domestic_parent_uei` was not in the original three-type spec. It is real observed
> data and is retained because it distinguishes a US-domiciled intermediate holding
> company from a foreign ultimate parent. Filter on `edge_type` if you want only the
> three specified types.

> `prime_to_sub` is a **contracting** relationship, not ownership. Do **not** propagate
> Native-entity ownership along `prime_to_sub` edges during spiderweb expansion.

## Corporate families (ownership edges only)

- Distinct parents with at least one child: **859**
- Parents with **more than one child**: **196**
- Parents with >1 child under `ultimate_parent_uei` alone: **174**
- Distinct children carrying at least one ownership parent: **1,805**
- Children recorded under **more than one** ownership parent: **190**

The last figure matters for spiderweb attribution. A subsidiary can legitimately appear
under two parents because ownership changed hands (e.g. a firm sold from one ANC to
another) or because SAM restated the record. Both edges are emitted with their own
`first_year`/`last_year`, so resolve conflicts by the observation window and
`n_observations` rather than assuming a single parent.

### 20 largest corporate families by distinct child count

| # | parent_uei | parent_name | distinct children |
|---:|---|---|---:|
| 1 | `KW9NCQ8W64S4` | NANA REGIONAL CORPORATION  INC. | 67 |
| 2 | `RQ13XQQKKQ67` | AFOGNAK NATIVE CORPORATION | 62 |
| 3 | `CY16XXPHX213` | ARCTIC SLOPE REGIONAL CORPORATION | 49 |
| 4 | `ZHEGXL9HYV43` | CHENEGA CORPORATION | 49 |
| 5 | `PQUEL5MZFDJ3` | BRISTOL BAY NATIVE CORPORATION | 45 |
| 6 | `S2SVA1GNRVK5` | COOK INLET REGION  INC | 34 |
| 7 | `NW2RJN8TQQW1` | GOVERNMENT OF THE UNITED STATES | 29 |
| 8 | `QHU1JXKM7D51` | WINNEBAGO TRIBE OF NEBRASKA | 27 |
| 9 | `KZMRSJJJN1L6` | UKPEAGVIK INUPIAT CORPORATION | 25 |
| 10 | `JM61NJRD58C8` | CALISTA CORPORATION | 25 |
| 11 | `DRDKNY4L1T33` | KONIAG  INC. | 24 |
| 12 | `FM96SF3VF8H9` | TYONEK NATIVE CORPORATION | 23 |
| 13 | `L2YMLW7SK3K8` | CHUGACH ALASKA CORPORATION | 23 |
| 14 | `TBAHL1WANLF3` | THE CHEROKEE NATION | 22 |
| 15 | `M5H7HESFYJL5` | ALEUT CORPORATION  THE | 21 |
| 16 | `P9QQX7RT8E98` | GOLDBELT  INCORPORATED | 21 |
| 17 | `R9JCCCG5ETB6` | OLGOONIK CORPORATION | 20 |
| 18 | `XMKLMV8GCWJ5` | SEALASKA CORPORATION | 18 |
| 19 | `HM1PS6FAK6U7` | AHTNA  INCORPORATED | 18 |
| 20 | `NWK9D2XDFGM8` | BERING STRAITS NATIVE CORPORATION | 17 |

Names shown are the **modal** name recorded for that UEI (the name appearing on the most
transaction rows). 8,706 UEIs were recorded under more than one distinct
legal name across the corpus; no name was invented or normalized beyond whitespace trim.

### CAUTION — federal registrants appear as ultimate parents

These parent UEIs carry the recorded parent name `GOVERNMENT OF THE UNITED STATES`.
They are federal registrant roll-ups (BIA, IHS, Army, tribally-controlled grant
schools filing under a federal umbrella), **not** corporate owners. Do NOT propagate
Native-entity ownership through them in the spiderweb step — a single one of these
would contaminate every child beneath it.

| parent_uei | modal parent_name | distinct children |
|---|---|---:|
| `NW2RJN8TQQW1` | GOVERNMENT OF THE UNITED STATES | 29 |

## Comparison against the old derived graph

Old graph: `data/raw/external/uei_hierarchy_graph.csv` — 12,744 rows / nodes.

| Metric | Old graph | This rebuild |
|---|---:|---:|
| Nodes (distinct UEIs) | 12,744 | 14,341 |
| Non-self ownership pairs | 1,593 | 2,015 |
| ... of which `parent_uei` | 1,548 | 182 |
| ... of which `ultimate_parent_uei` | 1,548 | 1,891 |

- **NEW ownership pairs found by this rebuild (not in the old graph): 433**
- Ownership pairs in the old graph not reproduced here: 11
- UEIs observed here that are absent from the old graph: 1,597
- Old-graph UEIs not observed in these raw files: 0

The old graph's coverage gap is structural: it carried one row per node with a mostly
blank `parent_uei` and a self-referential `ultimate_parent_uei`, so it encoded almost no
edges. The rebuild reads the parent columns off every transaction, so a child is linked
to its parent whenever any single transaction recorded that parent.

## UEI -> CAGE map

`data/clean/fpds_uei_cage_map.csv` — 24,977 distinct (uei, cage_code,
legal_business_name) triples.

- Triples with a non-empty CAGE code: 7,465
- Distinct UEIs with at least one CAGE code: 6,299 of 14,341 observed UEIs

Triples with a blank CAGE are retained deliberately: they document that FPDS observed the
UEI under that legal name but recorded no CAGE, which is itself a coverage fact. Filter on
`cage_code != ''` for a pure crosswalk.

Legal names are stored exactly as recorded, including casing, so the same UEI+CAGE pair
can appear on more than one row (`HCI MANAGEMENT SERVICES COMPANY` vs `HCI Management
Services Company`). Join on `uei` (+ `cage_code`); treat the name as a label, not a key.

## Outputs

| Path | Rows |
|---|---:|
| `data/clean/fpds_uei_edges.csv` | 2,290 |
| `data/clean/fpds_uei_cage_map.csv` | 24,977 |

Nothing under `data/spine/`, `data/clean/cedar_*`, or `review/` was read or modified.
