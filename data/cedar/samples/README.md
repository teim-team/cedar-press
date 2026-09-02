# Cedar Press — sample extracts

*Built 2026-09-02 by `code/770_sample_extracts.py`. 10 real rows per dataset, straight from the clean tables — nothing synthesised.*

These exist so the finished shape can be judged before the datasets are finished. Every automated gate in Cedar checks the data against a rule; none of them checks whether thirty rows make sense to someone reading them.

**What is excluded, and why the counts here are smaller than the dataset:** rows marked `publishable = N`, and any source marked `TERMS_STATED_RESTRICTIVE` (Navajo's NBOA list, Colville, CTUIR and five others). Sampling prefers complete rows and then spreads evenly across the file, so a sample is not the first ten rows of one agency in one year.

**On natural persons, narrowly.** A table is refused if it carries a person's data held APART from a public role — home address, personal email or phone, date of birth, SSN or TIN. It is *not* refused for naming an individual who is the public record: `lobbying_registrants.csv` publishes STEPHEN GRAHAM of Boston MA, and that is correct, because an individual may register as a lobbyist and the registration IS the disclosure the LDA creates. Codex was right that the older blanket wording — *any table carrying a natural person is refused* — described neither what this enforces nor what it should.

| dataset | table | rows shown | of | cols | one row is |
|---|---|---:|---:|---:|---|
| `_entity_layer` | `cedar_identity_register.csv` | 10 | 1,555 | 6 | UNSTATED |
| `contractors` | `prime_contracts.csv` | 10 | 1,217,768 | 12 | TWO populations under one schema, and the seam is real. Archive rows (FY2008-FY2026, source_file `FY*_All_Cont |
| `deals` | `deals_classified.csv` | 10 | 935 | 12 | one row per classified deal event - the merged deals ledger |
| `federal-register` | `consultation_events.csv` | 10 | 11,402 | 15 | one row per (consultation event, participant as published). `consultation_event_id` alone is NOT unique - an e |
| `funding` | `federal_funding_transactions.csv` | 10 | 701,955 | 12 | one row per federal assistance award TRANSACTION, across the union of the assistance and archive pulls |
| `gaming` | `gaming_facilities.csv` | 10 | 787 | 19 | one row per gaming facility - the directory core, docs/GAMING_BUILD_LOG_2026-08-05.md |
| `legislation` | `bill_votes.csv` | 10 | 423 | 14 | one row per roll-call vote on a Native-relevant bill |
| `lobbying` | `lobbying_registrants.csv` | 10 | 653 | 15 | one row per Senate LDA registrant_id - docs/LOBBYING_REGISTRANT_BUILD_LOG.md |
| `nagpra` | `nagpra_notices.csv` | 10 | 6,792 | 15 | one row per NAGPRA notice, keyed on the Federal Register document number - docs/NAGPRA_BUILD_LOG.md. A correct |
| `native-owned-businesses` | `native_owned_businesses.csv` | 10 | 2,393 | 11 | UNSTATED |
| `natural-resources` | `resource_revenue.csv` | 10 | 11,305 | 9 | one row per resource revenue event as recorded by its source system |
| `nonprofits` | `np_orgs.csv` | 10 | 12,764 | 13 | one row per EIN considered for the Native nonprofit universe, ruled in or out |
| `subcontracting` | `subawards.csv` | 10 | 76,859 | 13 | UNSTATED - no owner ruling or build log has declared this table's grain |

## Before totalling any money column

See `docs/MONEY_TOTALLING_RULES.md`. Two that bite hardest:

- **`subawards.subaward_amount`** summed unfiltered gives **$45.62B** against a correct **$24.41B**. The filter removes **$21.21B** — which is **86.9% of the correct total** and **46.5% of the unfiltered one**. *Both percentages are of that same $21.21B; they differ only in denominator, and an overstatement is measured against the truth, so the number to quote is 86.9%.* Filter to `duplicate_status = 'primary'` and `subaward_exceeds_prime_flag != 'yes'`.
- **`contractor_ranking.owner_obligations_usd`** sums to $6,535.96B against a true $176.74B — a **36.98×** inflation, because owner-grain attributes repeat on every operating-company row. `firm_*` is the additive family.
- **A subaward is a slice of a prime award.** Never add `subawards` to `prime_contracts`.

## Two columns that look like keys and are not, alone

- **`prime_contracts.contract_number`** is the awarding PIID and on 290,525 rows (23.9%) it is a modification stub — `0098`, `0006`, `SBA0001` — meaningless without the IDV it references. **`parent_contract_number` ships beside it and the pair is the key.** They are complementary: 664,470 rows carry both, 290,525 a parent plus a stub, 262,773 no parent and a complete standalone PIID, and **no row has neither**.
- **`federal_funding_transactions.canonical_name`** is a legacy display label, not Cedar's name for the entity. Group on **`cedar_uid`**, which is the key ADR-009 mandates. Measured 2026-09-01 in `docs/FAADS_TRANSACTION_KEY_LOG.md`: of 552,602 rows carrying a uid, **345,108 disagree** with the register's name for that uid, and **339,129 of those (98.3%, $94.0B) are a right identity under a stale label** — `haaku community academy` on rows correctly keyed to Pueblo of Acoma. Grouping on the label credits a school; grouping on the uid credits the nation. *(A re-count on 2026-09-02 returns 345,180 rather than 345,108 — the table was rebuilt between the two. The split is the point, not the last two digits, and one measurement is quoted everywhere rather than two.)*

## Columns that are in the schema and empty in this sample

The column set of every sample is fixed by the curated `SHOW` list in `code/770_sample_extracts.py` and does not change with which rows are drawn. Where a requested column came back blank on all ten rows it is still shipped, and named here, because that is a coverage fact about the dataset rather than something to hide by dropping the column.

- `federal-register` — blank on all 10 sampled rows: `format`
- `native-owned-businesses` — blank on all 10 sampled rows: `naics`
