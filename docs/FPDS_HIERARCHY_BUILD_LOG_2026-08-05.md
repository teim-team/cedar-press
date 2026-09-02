# FPDS Corporate-Hierarchy Rebuild — Build Log

**Date:** 2026-08-05  
**Script:** `code/13_build_fpds_hierarchy.py`  
**Log:** `logs/13_fpds_hierarchy_2026-08-05.log`  
**Runtime:** 1.0 minutes

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
| `Data Request 4-5-2023 File 1.csv` | 476,924 | `uei_id` (`uei_legal_business_name`) | `immediate_parent_uei`, `domestic_parent_uei`, `ultimate_parent_uei` (+ `_name`) | `cage_code` | `action_date_fiscal_year` |
| `Data Request 4-5-2023 File 2.csv` | 1,101,796 | same (316 cols, identical schema) | same | `cage_code` | `action_date_fiscal_year` |
| `Data Request 5-8-2023 IDVs.csv` | 1,078,021 | same (300 cols) | same | `cage_code` | `action_date_fiscal_year` |
| `contract-03-18-23-19-40-24.csv` | 100,074 | `Awardee UEI` (`Awardee Name`) | `Parent UEI` (`Awardee Parent Name`) | `Awardee Cage Code`, `Parent CAGE Code` | `Most Recent Action Date Fiscal Year` |
| `subcontract-05-09-23-22-23-37.csv` | 4,000 | `Sub Awardee UEI`, `Prime Awardee UEI` | `Sub Awardee Parent UEI`, `Prime Awardee Parent UEI` | `Sub Awardee Cage Code`, `Sub Awardee Parent Cage Code`, `CAGE Code` (x2, positional) | `Subaward Action Date Fiscal Year` |

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
| `C:\Users\esm247\Desktop\Cedar Press\Federal Spending\raw\Assistance_PrimeTransactions_2023-04-09_H19M53S53_1.csv` | 476,924 | 0 | 0 | 5,821 | 616 |
| `Data Request 4-5-2023 File 1.csv` | 1,101,796 | 0 | 0 | 13,129 | 1,755 |
| `Data Request 4-5-2023 File 2.csv` | 1,078,021 | 0 | 0 | 7,498 | 69 |
| `Data Request 5-8-2023 IDVs.csv` | 100,074 | 0 | 0 | 5,015 | 67 |
| `contract-03-18-23-19-40-24.csv` | 4,000 | 0 | 0 | 28 | 25 |
| `subcontract-05-09-23-22-23-37.csv` | 998 | 0 | 0 | 304 | 369 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2007_ledger_rows.csv` | 39,498 | 0 | 0 | 1,011 | 287 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2008_ledger_rows.csv` | 43,157 | 0 | 0 | 1,029 | 71 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2009_ledger_rows.csv` | 44,938 | 0 | 0 | 1,074 | 44 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2010_ledger_rows.csv` | 47,317 | 0 | 0 | 1,158 | 51 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2011_ledger_rows.csv` | 48,481 | 0 | 0 | 1,167 | 45 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2012_ledger_rows.csv` | 43,991 | 0 | 0 | 1,146 | 34 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2013_ledger_rows.csv` | 37,876 | 0 | 0 | 1,146 | 58 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2014_ledger_rows.csv` | 37,812 | 0 | 0 | 1,185 | 49 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2015_ledger_rows.csv` | 38,771 | 0 | 0 | 1,165 | 62 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2016_ledger_rows.csv` | 39,317 | 0 | 0 | 1,219 | 63 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2017_ledger_rows.csv` | 43,695 | 0 | 0 | 1,330 | 68 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2018_ledger_rows.csv` | 43,530 | 0 | 0 | 1,392 | 55 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2019_ledger_rows.csv` | 44,845 | 0 | 0 | 1,424 | 52 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2020_ledger_rows.csv` | 46,680 | 0 | 0 | 1,423 | 76 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2021_ledger_rows.csv` | 45,090 | 0 | 0 | 1,499 | 53 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2022_ledger_rows.csv` | 46,634 | 0 | 0 | 1,543 | 95 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2023_ledger_rows.csv` | 46,727 | 0 | 0 | 1,568 | 88 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2024_ledger_rows.csv` | 53,966 | 0 | 0 | 1,587 | 162 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2025_ledger_rows.csv` | 49,789 | 0 | 0 | 1,490 | 57 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2026_ledger_rows.csv` | 62,168 | 0 | 0 | 1,267 | 34 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_PrimeTransactions_2026-08-05_H21M06S30_1.csv` | 25,654 | 0 | 0 | 1,434 | 67 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_PrimeTransactions_2026-08-05_H21M11S35_1.csv` | 45,497 | 0 | 0 | 2,349 | 57 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_PrimeTransactions_2026-08-05_H22M21S40_1.csv` | 40,092 | 0 | 0 | 2,281 | 8 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_PrimeTransactions_2026-08-05_H22M29S13_1.csv` | 25,058 | 0 | 0 | 2,120 | 5 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_credit_2026-08-06\Assistance_PrimeTransactions_2026-08-26_H20M59S33_1.csv` | 7 | 0 | 0 | 3 | 0 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_credit_2026-08-06\Assistance_PrimeTransactions_2026-08-26_H21M02S36_1.csv` | 9 | 0 | 0 | 3 | 1 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_credit_2026-08-06\Assistance_PrimeTransactions_2026-08-26_H21M05S40_1.csv` | 34 | 0 | 0 | 6 | 0 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H21M06S27_1.csv` | 102 | 0 | 0 | 92 | 87 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H21M06S27_1.csv` | 102 | 0 | 0 | 18 | 0 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H21M11S29_1.csv` | 184 | 0 | 0 | 160 | 114 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H21M11S29_1.csv` | 184 | 0 | 0 | 35 | 0 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H22M21S36_1.csv` | 261 | 0 | 0 | 225 | 143 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H22M21S36_1.csv` | 261 | 0 | 0 | 40 | 0 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H22M29S09_1.csv` | 135 | 0 | 0 | 128 | 74 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H22M29S09_1.csv` | 135 | 0 | 0 | 20 | 0 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_gapfill_2026-08-05\gapfill_recipient_universe.csv` | 2,396 | 0 | 0 | 2,756 | 206 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\esm_hci\ESM\raw\Assistance_56G180126_TransactionHistory_1.csv` | 92 | 0 | 0 | 1 | 0 |
| **TOTAL** | **3,806,298** | **0** | **0** | **20,555 (union)** | **5,167** |

No malformed rows encountered: every data row parsed to the full header width.

## How often each parent column was actually populated

This is the key coverage fact for the rebuild. In the three big FPDS extracts the
`immediate_parent_uei` and `domestic_parent_uei` columns are present in the schema but
almost never filled; virtually all FPDS-side hierarchy comes from `ultimate_parent_uei`.

| File | Column | Rows with a value | Rows where value != child UEI |
|---|---|---:|---:|
| `C:\Users\esm247\Desktop\Cedar Press\Federal Spending\raw\Assistance_PrimeTransactions_2023-04-09_H19M53S53_1.csv` | `recipient_parent_uei` | 324,488 | 35,232 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2007_ledger_rows.csv` | `recipient_parent_uei` | 39,498 | 25,704 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2008_ledger_rows.csv` | `recipient_parent_uei` | 43,157 | 28,603 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2009_ledger_rows.csv` | `recipient_parent_uei` | 44,938 | 30,778 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2010_ledger_rows.csv` | `recipient_parent_uei` | 47,317 | 31,589 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2011_ledger_rows.csv` | `recipient_parent_uei` | 48,481 | 31,757 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2012_ledger_rows.csv` | `recipient_parent_uei` | 43,991 | 26,356 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2013_ledger_rows.csv` | `recipient_parent_uei` | 37,876 | 20,740 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2014_ledger_rows.csv` | `recipient_parent_uei` | 37,812 | 20,047 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2015_ledger_rows.csv` | `recipient_parent_uei` | 38,771 | 21,036 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2016_ledger_rows.csv` | `recipient_parent_uei` | 39,317 | 23,556 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2017_ledger_rows.csv` | `recipient_parent_uei` | 43,695 | 25,376 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2018_ledger_rows.csv` | `recipient_parent_uei` | 43,530 | 24,934 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2019_ledger_rows.csv` | `recipient_parent_uei` | 44,845 | 24,870 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2020_ledger_rows.csv` | `recipient_parent_uei` | 46,680 | 26,310 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2021_ledger_rows.csv` | `recipient_parent_uei` | 45,090 | 24,792 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2022_ledger_rows.csv` | `recipient_parent_uei` | 46,634 | 24,389 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2023_ledger_rows.csv` | `recipient_parent_uei` | 46,727 | 24,689 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2024_ledger_rows.csv` | `recipient_parent_uei` | 53,966 | 18,543 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2025_ledger_rows.csv` | `recipient_parent_uei` | 49,789 | 14,515 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_archive_2026-08-07\filtered\FY2026_ledger_rows.csv` | `recipient_parent_uei` | 62,168 | 46,083 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\usaspending_gapfill_2026-08-05\gapfill_recipient_universe.csv` | `recipient_parent_uei` | 695 | 695 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\esm_hci\ESM\raw\Assistance_56G180126_TransactionHistory_1.csv` | `recipient_parent_uei` | 82 | 0 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_PrimeTransactions_2026-08-05_H21M06S30_1.csv` | `recipient_parent_uei` | 10,826 | 3,764 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_PrimeTransactions_2026-08-05_H21M11S35_1.csv` | `recipient_parent_uei` | 17,802 | 6,750 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_PrimeTransactions_2026-08-05_H22M21S40_1.csv` | `recipient_parent_uei` | 16,362 | 5,741 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_PrimeTransactions_2026-08-05_H22M29S13_1.csv` | `recipient_parent_uei` | 9,874 | 3,459 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H21M06S27_1.csv` | `prime_awardee_parent_uei` | 44 | 9 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H21M06S27_1.csv` | `prime_awardee_uei` | 102 | 102 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H21M06S27_1.csv` | `subawardee_parent_uei` | 29 | 23 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H21M11S29_1.csv` | `prime_awardee_parent_uei` | 91 | 10 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H21M11S29_1.csv` | `prime_awardee_uei` | 184 | 183 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H21M11S29_1.csv` | `subawardee_parent_uei` | 64 | 50 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H22M21S36_1.csv` | `prime_awardee_parent_uei` | 107 | 21 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H22M21S36_1.csv` | `prime_awardee_uei` | 261 | 260 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H22M21S36_1.csv` | `subawardee_parent_uei` | 94 | 88 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H22M29S09_1.csv` | `prime_awardee_parent_uei` | 61 | 0 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H22M29S09_1.csv` | `prime_awardee_uei` | 135 | 135 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_2023_2026\Assistance_Subawards_2026-08-05_H22M29S09_1.csv` | `subawardee_parent_uei` | 61 | 61 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_credit_2026-08-06\Assistance_PrimeTransactions_2026-08-26_H20M59S33_1.csv` | `recipient_parent_uei` | 1 | 1 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_credit_2026-08-06\Assistance_PrimeTransactions_2026-08-26_H21M02S36_1.csv` | `recipient_parent_uei` | 6 | 5 |
| `C:\Users\esm247\Desktop\Cedar Press\data\raw\federal_funding\usaspending_credit_2026-08-06\Assistance_PrimeTransactions_2026-08-26_H21M05S40_1.csv` | `recipient_parent_uei` | 27 | 27 |
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
| `parent_uei` | 2,726 | immediate/direct corporate parent |
| `domestic_parent_uei` | 0 | highest US-domiciled parent (extra type, see note) |
| `ultimate_parent_uei` | 1,891 | top of the corporate family |
| `prime_to_sub` | 550 | subawardee -> prime (CONTRACTING, not ownership) |
| **TOTAL** | **5,167** | |

Self-edges dropped (row-level occurrences): 2,128,727.
Rows where one side of a candidate edge was blank: 4,796,598.

> `domestic_parent_uei` was not in the original three-type spec. It is real observed
> data and is retained because it distinguishes a US-domiciled intermediate holding
> company from a foreign ultimate parent. Filter on `edge_type` if you want only the
> three specified types.

> `prime_to_sub` is a **contracting** relationship, not ownership. Do **not** propagate
> Native-entity ownership along `prime_to_sub` edges during spiderweb expansion.

## Corporate families (ownership edges only)

- Distinct parents with at least one child: **1,608**
- Parents with **more than one child**: **296**
- Parents with >1 child under `ultimate_parent_uei` alone: **174**
- Distinct children carrying at least one ownership parent: **2,725**
- Children recorded under **more than one** ownership parent: **372**

The last figure matters for spiderweb attribution. A subsidiary can legitimately appear
under two parents because ownership changed hands (e.g. a firm sold from one ANC to
another) or because SAM restated the record. Both edges are emitted with their own
`first_year`/`last_year`, so resolve conflicts by the observation window and
`n_observations` rather than assuming a single parent.

### 20 largest corporate families by distinct child count

| # | parent_uei | parent_name | distinct children |
|---:|---|---|---:|
| 1 | `KW9NCQ8W64S4` | NANA REGIONAL CORPORATION  INC. | 69 |
| 2 | `NW2RJN8TQQW1` | GOVERNMENT OF THE UNITED STATES | 67 |
| 3 | `CY16XXPHX213` | ARCTIC SLOPE REGIONAL CORPORATION | 62 |
| 4 | `RQ13XQQKKQ67` | AFOGNAK NATIVE CORPORATION | 62 |
| 5 | `ZHEGXL9HYV43` | CHENEGA CORPORATION | 54 |
| 6 | `PQUEL5MZFDJ3` | BRISTOL BAY NATIVE CORPORATION | 51 |
| 7 | `TBAHL1WANLF3` | CHEROKEE NATION | 39 |
| 8 | `S2SVA1GNRVK5` | COOK INLET REGION INC | 37 |
| 9 | `QHU1JXKM7D51` | WINNEBAGO TRIBE OF NEBRASKA | 28 |
| 10 | `JM61NJRD58C8` | CALISTA CORPORATION | 26 |
| 11 | `KZMRSJJJN1L6` | UKPEAGVIK INUPIAT CORPORATION | 25 |
| 12 | `DRDKNY4L1T33` | KONIAG  INC. | 24 |
| 13 | `C471YH1GMPX7` | NORTHWEST INDIAN FISHERIES COMMISSION | 24 |
| 14 | `FM96SF3VF8H9` | TYONEK NATIVE CORPORATION | 23 |
| 15 | `L2YMLW7SK3K8` | CHUGACH ALASKA CORPORATION | 23 |
| 16 | `NWK9D2XDFGM8` | BERING STRAITS NATIVE CORPORATION | 23 |
| 17 | `CKLKWJSYK9T5` | HO-CHUNK, INC. | 23 |
| 18 | `M5H7HESFYJL5` | ALEUT CORPORATION  THE | 22 |
| 19 | `H8ZXCH5PPEQ1` | KIKIKTAGRUK INUPIAT CORP | 22 |
| 20 | `KEBVZNK93W87` | NAVAJO NATION TRIBAL GOVERNMENT, THE | 21 |

Names shown are the **modal** name recorded for that UEI (the name appearing on the most
transaction rows). 9,556 UEIs were recorded under more than one distinct
legal name across the corpus; no name was invented or normalized beyond whitespace trim.

### CAUTION — federal registrants appear as ultimate parents

These parent UEIs carry the recorded parent name `GOVERNMENT OF THE UNITED STATES`.
They are federal registrant roll-ups (BIA, IHS, Army, tribally-controlled grant
schools filing under a federal umbrella), **not** corporate owners. Do NOT propagate
Native-entity ownership through them in the spiderweb step — a single one of these
would contaminate every child beneath it.

| parent_uei | modal parent_name | distinct children |
|---|---|---:|
| `NW2RJN8TQQW1` | GOVERNMENT OF THE UNITED STATES | 67 |
| `R8U7S9K184F6` | GOVERNMENT OF THE UNITED STATES | 2 |
| `GK1ECPGZV897` | GOVERNMENT OF THE UNITED STATES | 1 |
| `V425F7L4X4R1` | GOVERNMENT OF THE UNITED STATES | 1 |
| `FVP4QBB76J19` | GOVERNMENT OF THE UNITED STATES | 1 |

## Comparison against the old derived graph

Old graph: `data/raw/external/uei_hierarchy_graph.csv` — 12,744 rows / nodes.

| Metric | Old graph | This rebuild |
|---|---:|---:|
| Nodes (distinct UEIs) | 12,744 | 20,555 |
| Non-self ownership pairs | 1,593 | 3,191 |
| ... of which `parent_uei` | 1,548 | 2,726 |
| ... of which `ultimate_parent_uei` | 1,548 | 1,891 |

- **NEW ownership pairs found by this rebuild (not in the old graph): 1,609**
- Ownership pairs in the old graph not reproduced here: 11
- UEIs observed here that are absent from the old graph: 7,811
- Old-graph UEIs not observed in these raw files: 0

The old graph's coverage gap is structural: it carried one row per node with a mostly
blank `parent_uei` and a self-referential `ultimate_parent_uei`, so it encoded almost no
edges. The rebuild reads the parent columns off every transaction, so a child is linked
to its parent whenever any single transaction recorded that parent.

## UEI -> CAGE map

`data/clean/fpds_uei_cage_map.csv` — 34,601 distinct (uei, cage_code,
legal_business_name) triples.

- Triples with a non-empty CAGE code: 11,091
- Distinct UEIs with at least one CAGE code: 7,732 of 20,555 observed UEIs

Triples with a blank CAGE are retained deliberately: they document that FPDS observed the
UEI under that legal name but recorded no CAGE, which is itself a coverage fact. Filter on
`cage_code != ''` for a pure crosswalk.

Legal names are stored exactly as recorded, including casing, so the same UEI+CAGE pair
can appear on more than one row (`HCI MANAGEMENT SERVICES COMPANY` vs `HCI Management
Services Company`). Join on `uei` (+ `cage_code`); treat the name as a label, not a key.

## Outputs

| Path | Rows |
|---|---:|
| `data/clean/fpds_uei_edges.csv` | 5,167 |
| `data/clean/fpds_uei_cage_map.csv` | 34,601 |

Nothing under `data/spine/`, `data/clean/cedar_*`, or `review/` was read or modified.
