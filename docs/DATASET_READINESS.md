# Cedar dataset readiness — the scoreboard

*Generated 2026-08-29 by `code/518_dataset_readiness.py` from live artifacts. Three statuses only: **READY / BLOCKED / NOT_TESTED**. There is no 'mostly ready' — a dataset crosses the minimum shipping contract or it has named blockers.*

## READY: 2 / 13

BLOCKED 11 · NOT_TESTED 0

| dataset | status | tables | grain | keys | duplicates | agg-unsafe | rebuild |
|---|---|---:|---|---|---|---:|---|
| `federal-register` | **READY** | 22 | 22/22 | 22/22 | clean | 0 | declared |
| `nagpra` | **READY** | 4 | 4/4 | 4/4 | clean | 0 | declared |
| `native-owned-businesses` | **BLOCKED** | 6 | 6/6 | 6/6 | clean | 0 | declared |
| `natural-resources` | **BLOCKED** | 8 | 7/8 | 7/8 | clean | 1 | declared |
| `legislation` | **BLOCKED** | 12 | 10/12 | 10/12 | 5 rows | 2 | declared |
| `subcontracting` | **BLOCKED** | 3 | 2/3 | 2/3 | 10,770 rows | 1 | declared |
| `gaming` | **BLOCKED** | 46 | 44/46 | 44/46 | clean | 2 | declared |
| `nonprofits` | **BLOCKED** | 10 | 9/10 | 9/10 | 101 rows | 1 | declared |
| `lobbying` | **BLOCKED** | 34 | 29/34 | 29/34 | 827 rows | 5 | declared |
| `deals` | **BLOCKED** | 14 | 12/14 | 12/14 | clean | 2 | DESTRUCTIVE |
| `contractors` | **BLOCKED** | 10 | 6/10 | 6/10 | 141,697 rows | 5 | declared |
| `_entity_layer` | **BLOCKED** | 35 | 29/35 | 29/35 | 10,985 rows | 6 | DESTRUCTIVE |
| `funding` | **BLOCKED** | 10 | 7/10 | 7/10 | 180,374 rows | 3 | declared |

## Blockers, by dataset

### `native-owned-businesses` — BLOCKED

- C5 no row-conservation coverage

### `natural-resources` — BLOCKED

- C1 grain UNSTATED on 1: tribal_bond_issuances.csv
- C2 no validated primary key on 1
- C7 DOUBLE-COUNTING RISK - money tables a buyer cannot safely total: tribal_bond_issuances.csv
- C5 no row-conservation coverage

### `legislation` — BLOCKED

- C1 grain UNSTATED on 2: congressional_correspondence_log.csv, native_bills_subject_sweep.csv
- C2 no validated primary key on 2
- C3 literal duplicates: native_bills_subject_sweep.csv(5)
- C5 no row-conservation coverage

### `subcontracting` — BLOCKED

- C1 grain UNSTATED on 1: subawards.csv
- C2 no validated primary key on 1
- C3 literal duplicates: subawards.csv(10,770)
- C7 DOUBLE-COUNTING RISK - money tables a buyer cannot safely total: subawards.csv
- C5 no row-conservation coverage

### `gaming` — BLOCKED

- C1 grain UNSTATED on 2: fac_audit_sefa_gaming_programs.csv, gaming_projections.csv
- C2 no validated primary key on 2
- C7 DOUBLE-COUNTING RISK - money tables a buyer cannot safely total: fac_audit_sefa_gaming_programs.csv, gaming_projections.csv

### `nonprofits` — BLOCKED

- C1 grain UNSTATED on 1: np_schedule_i_grants.csv
- C2 no validated primary key on 1
- C3 literal duplicates: np_schedule_i_grants.csv(101)
- C7 DOUBLE-COUNTING RISK - money tables a buyer cannot safely total: np_schedule_i_grants.csv
- C5 no row-conservation coverage

### `lobbying` — BLOCKED

- C1 grain UNSTATED on 5: admin_appeal_positions.csv, ferc_docket_filings.csv, ferc_ex_parte_communications.csv
- C2 no validated primary key on 5
- C3 literal duplicates: ferc_docket_filings.csv(822), hearing_bill_links.csv(1), lobbying_registrant_native_ownership_evidence.csv(4)

### `deals` — BLOCKED

- C1 grain UNSTATED on 2: deals_2026_ytd_additions.csv, tribal_resolution_financings.csv
- C2 no validated primary key on 2
- C7 DOUBLE-COUNTING RISK - money tables a buyer cannot safely total: deals_2026_ytd_additions.csv, tribal_resolution_financings.csv
- C5 no row-conservation coverage
- C8 rebuild is DESTRUCTIVE (88_build_deals_taxonomy.py) - no safe documented rebuild path

### `contractors` — BLOCKED

- C1 grain UNSTATED on 4: contractor_ranking.csv, fpds_uei_cage_map.csv, prime_contracts.csv
- C2 no validated primary key on 4
- C3 literal duplicates: prime_contracts.csv(80,778), prime_contracts_archive_backfill.csv(60,919)
- C7 DOUBLE-COUNTING RISK - money tables a buyer cannot safely total: contractor_ranking.csv, prime_contracts.csv, prime_contracts_archive_backfill.csv
- C5 no row-conservation coverage

### `_entity_layer` — BLOCKED

- C1 grain UNSTATED on 6: cedar_identifier_graph_edges.csv, cedar_ruling_ledger_consolidated.csv, cross_dataset_ruling_map.csv
- C2 no validated primary key on 6
- C3 literal duplicates: cedar_identifier_graph_edges.csv(2,451), cedar_ruling_ledger_consolidated.csv(6,302), cross_dataset_ruling_map.csv(2,228)
- C8 rebuild is DESTRUCTIVE (01_build_entity_spine.py, 09_import_rulings.py) - no safe documented rebuild path

### `funding` — BLOCKED

- C1 grain UNSTATED on 3: faads_transactions.csv, faads_transactions_all_agencies.csv, native_passthrough.csv
- C2 no validated primary key on 3
- C3 literal duplicates: faads_transactions.csv(1,001), faads_transactions_all_agencies.csv(179,259), native_passthrough.csv(114)
- C7 DOUBLE-COUNTING RISK - money tables a buyer cannot safely total: faads_transactions.csv, faads_transactions_all_agencies.csv, native_passthrough.csv
- C5 no row-conservation coverage
