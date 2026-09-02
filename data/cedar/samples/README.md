# Cedar Press — sample extracts

*Built 2026-09-01 by `code/770_sample_extracts.py`. 10 real rows per dataset, straight from the clean tables — nothing synthesised.*

These exist so the finished shape can be judged before the datasets are finished. Every automated gate in Cedar checks the data against a rule; none of them checks whether thirty rows make sense to someone reading them.

**What is excluded, and why the counts here are smaller than the dataset:** rows marked `publishable = N`, any source marked `TERMS_STATED_RESTRICTIVE` (Navajo's NBOA list, Colville, CTUIR and five others), and any table carrying a natural person's name, email, phone or address. Sampling prefers complete rows and then spreads evenly across the file, so a sample is not the first thirty rows of one agency in one year.

| dataset | table | rows shown | of | cols | one row is |
|---|---|---:|---:|---:|---|
| `_entity_layer` | `cedar_identity_register.csv` | 10 | 1,555 | 6 | UNSTATED |
| `contractors` | `prime_contracts.csv` | 10 | 1,217,768 | 11 | TWO populations under one schema, and the seam is real. Archive rows (FY2008-FY2026, source_file `FY*_All_Cont |
| `deals` | `deals_classified.csv` | 10 | 935 | 10 | one row per classified deal event - the merged deals ledger |
| `federal-register` | `consultation_events.csv` | 10 | 11,402 | 10 | one row per (consultation event, participant as published). `consultation_event_id` alone is NOT unique - an e |
| `funding` | `federal_funding_transactions.csv` | 10 | 701,955 | 11 | one row per federal assistance award TRANSACTION, across the union of the assistance and archive pulls |
| `gaming` | `gaming_facilities.csv` | 10 | 787 | 13 | one row per gaming facility - the directory core, docs/GAMING_BUILD_LOG_2026-08-05.md |
| `legislation` | `bill_votes.csv` | 10 | 423 | 12 | one row per roll-call vote on a Native-relevant bill |
| `lobbying` | `lobbying_registrants.csv` | 10 | 653 | 10 | one row per Senate LDA registrant_id - docs/LOBBYING_REGISTRANT_BUILD_LOG.md |
| `nagpra` | `fr_nagpra_title_index.csv` | 10 | 6,664 | 6 | one row per Federal Register document whose TITLE is a NAGPRA notice heading. A title-only index of the parent |
| `native-owned-businesses` | `native_owned_businesses.csv` | 10 | 2,393 | 10 | UNSTATED |
| `natural-resources` | `resource_revenue.csv` | 10 | 11,305 | 9 | one row per resource revenue event as recorded by its source system |
| `nonprofits` | `np_orgs.csv` | 10 | 12,764 | 10 | one row per EIN considered for the Native nonprofit universe, ruled in or out |
| `subcontracting` | `subawards.csv` | 10 | 76,859 | 12 | UNSTATED - no owner ruling or build log has declared this table's grain |

## Before totalling any money column

See `docs/MONEY_TOTALLING_RULES.md`. Two that bite hardest:

- **`subawards.subaward_amount`** summed unfiltered gives $45.62B against a correct **$24.41B** — a **46.5%** overstatement. Filter to `duplicate_status = 'primary'` and `subaward_exceeds_prime_flag != 'yes'`.
- **`contractor_ranking.owner_obligations_usd`** sums to $6,535.96B against a true $176.74B — a **36.98×** inflation, because owner-grain attributes repeat on every operating-company row. `firm_*` is the additive family.
- **A subaward is a slice of a prime award.** Never add `subawards` to `prime_contracts`.
