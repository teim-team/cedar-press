# 02j_individual_native_firm_contracts

*Firm-year federal prime contracting for the class, rolled up READ-ONLY from prime_contracts.csv. The internal join surface; names and identifiers on it do not publish.*

Generated 2026-08-26 by `code/243_write_individual_native_class_codebook_fragment.py` from `individual_native_firm_contracts.csv` (324 rows, 28 variables).

**Publication is answered PER FIELD, never per dataset.** `published = 0` on 3 of 28 variables here; every one of them is a name, an address, an identifier that resolves to a name, or a sentence that pairs a person with an assertion about their ancestry.

| variable | type | units | filled | published | tier | description |
|---|---|---|---:|---:|---|---|
| `surrogate_entity_id` | text | code | 100.0% | 1 | public | Cedar surrogate key. Joins to individual_native_firm_register.csv and to the spine's tribe_id. |
| `entity_class` | text | category | 100.0% | 1 | public | Always `Individually Native-owned business`. NEVER summed with any tribal, ANC or NHO total. These firms were never in one, and no published tribal figure changes because this class exists. |
| `fiscal_year` | int | fiscal year | 100.0% | 1 | public | Federal fiscal year. |
| `canonical_name` | text | name | 100.0% | 0 | internal | WITHHELD from publication. Present so this table can be joined by hand; released only where the register's publish_name = 1. |
| `identifier_type` | text | category | 100.0% | 1 | public | `UEI` or `CAGE` - the key that matched prime_contracts.csv. |
| `identifier` | text | code | 100.0% | 0 | internal | WITHHELD from publication. SAM's public entity search resolves a UEI to a legal name and a street address, so where the legal name is a private person's name this identifier publishes the name by ONE HOP. Released only where firm_legal_name_is_person = 0, or on recorded consent. Independent of the D&B question and survives any answer to it. |
| `recipient_states` | text | list | 100.0% | 0 | internal | WITHHELD from publication. on a firm-level row; publishes only in a 3+-firm aggregate. |
| `n_contract_rows` | int | count | 100.0% | 1 | public | Prime transaction rows for this firm-year. `prime_contracts.csv` is read ONLY - nothing is written back to it, so `attributed_flag` and the $244.77B attributed total are untouched by this class. |
| `total_obligations_usd` | float | USD nominal | 100.0% | 1 | public | Nominal obligations. `total_obligations` is transactional and SUMS. |
| `total_obligations_real2025_usd` | float | USD 2025 | 100.0% | 1 | public | Deflated to 2025 dollars using the deflator already on the prime row. Never mix base years. |
| `rows_with_a_native_setaside_flag` | int | count | 100.0% | 1 | public | Rows carrying any of reported_8a / reported_buy_indian / reported_indian_business / reported_native_preference. SAM socio-economic self-certification as carried on the contract rows. A CHANNEL, NEVER A VERDICT: americanIndianOwned = YES on 2,846 of 8,273 rows of the TRIBAL SAM extract, so the flag does not separate individual from entity ownership; and 57.2% of attributed prime dollars carry no Native set-aside at all, so its absence is not evidence against. 22 of the 40 prior-ruled firms here carry zero flags on every contract row. |
| `obligations_with_a_native_setaside_flag` | float | USD nominal | 100.0% | 1 | public | Obligations on those rows. The complement is NOT evidence that a firm is not Native-owned; it is 76.7% of this class's dollars. |
| `n_funding_agencies` | int | count | 100.0% | 1 | public | Distinct funding agencies in the firm-year. |
| `funding_agencies` | text | list | 100.0% | 1 | public | Agency LABELS, pipe-delimited. A rendered label, never an identifier - putting `funding_agency` in a join key once left $20.5B double-counted. |
| `sectors` | text | list | 100.0% | 1 | public | Sector labels, pipe-delimited. |
| `top_setaside` | text | category | 100.0% | 1 | public | Modal set-aside on the firm-year. A set-aside is a property of the AWARD, not of each modification, and is blank on ~56% of archive rows. |
| `extent_competed_modal` | text | category | 100.0% | 1 | public | Modal normalised extent of competition. |
| `evidence_tier` | text | category | 100.0% | 1 | public | `A`, inherited from the owner ruling. Never assigned here. |
| `evidence_grade` | text | category | 100.0% | 1 | public | `elijah_ruling`. |
| `sam_self_certification` | text | category | 100.0% | 1 | public | SAM socio-economic self-certification as carried on the contract rows. A CHANNEL, NEVER A VERDICT: americanIndianOwned = YES on 2,846 of 8,273 rows of the TRIBAL SAM extract, so the flag does not separate individual from entity ownership; and 57.2% of attributed prime dollars carry no Native set-aside at all, so its absence is not evidence against. 22 of the 40 prior-ruled firms here carry zero flags on every contract row. |
| `firm_legal_name_is_person` | text | 0/1/UNKNOWN | 100.0% | 1 | public | Drives every name and identifier release decision on this row. UNKNOWN counts as a person. |
| `publish_name` | int | 0/1 | 100.0% | 1 | public | See the register. |
| `publish_federal_identifier` | int | 0/1 | 100.0% | 1 | public | See the one-hop rule on `identifier`. |
| `publishable_contract_facts` | text | Y/N | 100.0% | 1 | public | `Y` throughout. |
| `temporal_caveat` | text | text | 100.0% | 1 | public | A current page cannot testify about a historical record. Contract activity in this class ends FY2022; a ruling or a page dated 2026 speaks to 2026. Three gaming rulings were withdrawn 2026-08-06 for exactly this error. |
| `source_table` | text | text | 100.0% | 1 | public | `prime_contracts.csv (read only)`. Recorded so the read-only discipline is visible in the data and not only in a docstring. |
| `built_date` | date | ISO date | 100.0% | 1 | public | Build date. |
| `built_by` | text | path | 100.0% | 1 | public | Producing script. |
