# 02k_individual_native_firm_contracts_published

*The publishable view of the class: surrogate-keyed firm rows and aggregate cells, with cells under 3 firms suppressed and the suppression reported.*

Generated 2026-08-26 by `code/243_write_individual_native_class_codebook_fragment.py` from `individual_native_firm_contracts_published.csv` (613 rows, 11 variables).

**Publication is answered PER FIELD, never per dataset.** `published = 0` on 0 of 11 variables here; every one of them is a name, an address, an identifier that resolves to a name, or a sentence that pairs a person with an assertion about their ancestry.

| variable | type | units | filled | published | tier | description |
|---|---|---|---:|---:|---|---|
| `cell_type` | text | category | 100.0% | 1 | public | `FIRM`, `FISCAL_YEAR`, `FISCAL_YEAR_x_AGENCY`, `FISCAL_YEAR_x_SECTOR`, `STATE`, `SETASIDE`, `CLASS_TOTAL`, `NATIVE_SETASIDE_COVERAGE`. A `FIRM` row carries the Cedar surrogate and nothing but totals and a year span - no name, no identifier, no state, no agency, no sector. |
| `dimension_1` | text | code | 99.8% | 1 | public | First dimension of the cell: a surrogate id, a fiscal year, a state or a set-aside label. |
| `dimension_2` | text | code | 84.3% | 1 | public | Second dimension where the cell is a cross-tabulation. |
| `entity_class` | text | category | 100.0% | 1 | public | Always `Individually Native-owned business`. NEVER summed with any tribal, ANC or NHO total. These firms were never in one, and no published tribal figure changes because this class exists. |
| `n_firms` | int | count | 100.0% | 1 | public | Distinct firms resolving to the cell. Reported even where the value is suppressed, so the reader can see how much was withheld. |
| `n_contract_rows` | int | count | 38.8% | 1 | public | Prime transaction rows in the cell. BLANK where value_suppressed_small_cell = 1. |
| `total_obligations_usd` | float | USD nominal | 38.8% | 1 | public | Nominal obligations in the cell. BLANK where suppressed. |
| `value_suppressed_small_cell` | int | 0/1 | 100.0% | 1 | public | 1 where fewer than 3 firms resolve to the cell. A one- or two-firm cell in a class of privately owned firms is a person's name written in another alphabet. |
| `suppression_rule` | text | text | 61.2% | 1 | public | The rule, stated on the row itself. The suppression is REPORTED and the row is never silently dropped - the CGCC precedent, where 318 rows carry a suppression flag with a blank value and the aggregate is kept typed and never attributed to a tribe. |
| `note` | text | text | 8.8% | 1 | public | What the cell means and what it must not be used for. |
| `built_date` | date | ISO date | 100.0% | 1 | public | Build date. |
