# Cedar dataset readiness — the scoreboard

*Generated 2026-09-01 by `code/518_dataset_readiness.py` from live artifacts. Three statuses only: **READY / BLOCKED / NOT_TESTED**. There is no 'mostly ready' — a dataset crosses the minimum shipping contract or it has named blockers.*

## READY: 8 / 13

BLOCKED 5 · NOT_TESTED 0

| dataset | status | tables | grain | keys | duplicates | agg-unsafe | rebuild |
|---|---|---:|---|---|---|---:|---|
| `_entity_layer` | **READY** | 35 | 35/35 | 35/35 | clean | 0 | declared |
| `contractors` | **READY** | 10 | 10/10 | 10/10 | clean | 0 | declared |
| `deals` | **READY** | 14 | 14/14 | 14/14 | clean | 0 | declared |
| `federal-register` | **READY** | 22 | 22/22 | 22/22 | clean | 0 | declared |
| `lobbying` | **READY** | 33 | 33/33 | 33/33 | clean | 0 | declared |
| `nagpra` | **READY** | 4 | 4/4 | 4/4 | clean | 0 | declared |
| `native-owned-businesses` | **READY** | 6 | 6/6 | 6/6 | clean | 0 | declared |
| `nonprofits` | **READY** | 10 | 10/10 | 10/10 | clean | 0 | declared |
| `legislation` | **BLOCKED** | 12 | 11/12 | 11/12 | clean | 1 | declared |
| `natural-resources` | **BLOCKED** | 8 | 8/8 | 8/8 | clean | 0 | declared |
| `gaming` | **BLOCKED** | 54 | 51/54 | 51/54 | clean | 3 | declared |
| `subcontracting` | **BLOCKED** | 3 | 2/3 | 2/3 | 10,770 rows | 1 | declared |
| `funding` | **BLOCKED** | 9 | 7/9 | 7/9 | 180,376 rows | 3 | declared |

## Blockers, by dataset

### `legislation` — BLOCKED

- C1 grain UNSTATED on 1: congressional_correspondence_log.csv
- C2 no validated primary key on 1

### `natural-resources` — BLOCKED

- C5 no row-conservation coverage
- C4 only 25% of entity-bearing rows carry a Cedar id, and every record in this dataset HAS an entity subject - so this is unresolved work, not scope. See ADR-009 and ADR-010.

### `gaming` — BLOCKED

- C1 grain UNSTATED on 3: fac_audit_sefa_gaming_programs.csv, gaming_property_self_published_assertions.csv, gaming_property_self_published_claims.csv
- C2 no validated primary key on 3
- C7 DOUBLE-COUNTING RISK - money tables a buyer cannot safely total: fac_audit_sefa_gaming_programs.csv, gaming_property_self_published_assertions.csv, gaming_property_self_published_claims.csv

### `subcontracting` — BLOCKED

- C1 grain UNSTATED on 1: subawards.csv
- C2 no validated primary key on 1
- C3 literal duplicates: subawards.csv(10,770)
- C7 DOUBLE-COUNTING RISK - money tables a buyer cannot safely total: subawards.csv
- C4 only 42% of entity-bearing rows carry a Cedar id, and every record in this dataset HAS an entity subject - so this is unresolved work, not scope. See ADR-009 and ADR-010.

### `funding` — BLOCKED

- C1 grain UNSTATED on 2: faads_transactions_all_agencies.csv, native_passthrough.csv
- C2 no validated primary key on 2
- C3 literal duplicates: faads_transactions.csv(1,001), faads_transactions_all_agencies.csv(179,259), native_passthrough.csv(116)
- C7 DOUBLE-COUNTING RISK - money tables a buyer cannot safely total: faads_transactions.csv, faads_transactions_all_agencies.csv, native_passthrough.csv
- C4 only 28% of entity-bearing rows carry a Cedar id, and every record in this dataset HAS an entity subject - so this is unresolved work, not scope. See ADR-009 and ADR-010.
