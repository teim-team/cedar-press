# GAMING-NR — the twelve read counts, and three gaming grains

*Generated 2026-09-01 by `code/814_gaming_nr_grain_and_conservation.py measure`. Every number is re-measured on every run; `verify` exits 1 when one stops being true.*

## natural-resources C5 — `resource_revenue.csv`

**421,590 source readings → 11,305 published rows.** `573 conserve-probe` accounted for 9,434 of 11,305 rows from the two countable CSVs and deliberately did not merge the partial. All twelve source systems are now counted, so the merge is honest.

The unit is a CANDIDATE LEDGER ROW: one reading the harvest examined and either published or refused for a named reason. That is what makes twelve incompatible sources commensurable, and it is why `emitted` sums to exactly the 11,305 rows the table ships.

| source system | read unit | readings | published | refused |
|---|---|---:|---:|---:|
| `ONRR_NRRD_monthly_revenue` | one row of the ONRR Natural Resources Revenue Data monthly revenue extract | 410,901 | 9,277 | 401,624 |
| `ONRR_NRRD_fiscal_year_disbursements` | one row of the ONRR fiscal-year disbursements extract | 8,437 | 157 | 8,280 |
| `OMC_headright_payment_history` | one money cell of the Osage Minerals Council headright payment spreadsheet - a (year, quarter) rate or a printed annual total | 628 | 508 | 120 |
| `ND_State_Treasurer_tax_distribution_search` | one payment line matched in an archived ND State Treasurer tax distribution search result | 492 | 492 | 0 |
| `MMS_MRM_american_indian_revenues_calendar` | one (calendar year, revenue component) cell of the CY1925-2000 table read by coordinate out of one archived PDF | 456 | 315 | 141 |
| `ANCSA_7i_7j_annual_reports` | one (regional corporation, series, fiscal year) claim read out of a retrieved ANCSA portal annual report | 185 | 185 | 0 |
| `OSMRE_AML_fee_based_grant_distribution` | one (fiscal-year document, tribal programme, sequestration basis) reading of an OSMRE AML fee-based distribution table | 150 | 76 | 74 |
| `UT_COBI_fund_financials` | one (fund, state fiscal year, measure) cell of a Utah COBI fund financial history | 118 | 118 | 0 |
| `OMC_quarterly_newsletter` | one printed figure slot of an Osage Minerals Council quarterly newsletter - the total, the seven revenue component lines, or the Oklahoma gross production tax line | 108 | 68 | 40 |
| `MT_DOR_county_oil_gas_distribution` | one 'Tribal Distribution' line on a Montana DOR quarterly county-distribution cover letter | 49 | 49 | 0 |
| `MMS_MRM_american_indian_revenues` | one (fiscal-year document, revenue component) reading of an archived MMS American Indian collections PDF | 48 | 42 | 6 |
| `OSMRE_AML_IIJA_grant_distribution` | one (distribution document, tribal programme) reading of an IIJA abandoned-mine-land distribution table | 18 | 18 | 0 |

### how each read count was established

- **`ONRR_NRRD_monthly_revenue`** — the publisher's own Land Class column is the filter; nothing is inferred. 1 source document(s) on disk.
    - `rejected:onrr_land_class_is_not_Native_American` — 401,624
- **`ONRR_NRRD_fiscal_year_disbursements`** — Fund Type is the publisher's own bucket. 1 source document(s) on disk.
    - `rejected:onrr_disbursement_fund_type_is_not_Native_American` — 8,280
- **`OMC_headright_payment_history`** — three side-by-side year blocks; 482 quarterly cells and 146 printed annual totals. The annual total of a quarterly year is the GATE the four quarters must sum to, so publishing it as well would double count the year. 1 source document(s) on disk.
    - `rejected:osage_printed_annual_total_is_the_reconciliation_gate_input_for_a_year_that_also_prints_quarters` — 120
- **`ND_State_Treasurer_tax_distribution_search`** — 3 archived HTML search results; the parser's own per-file match counts are [216, 216, 60]. Every matched line published - no ND tax type is outside the revenue_type mapping. 3 source document(s) on disk.
- **`MMS_MRM_american_indian_revenues_calendar`** — one document (Am_Ind_Coll.pdf), 76 years x 6 components. Three gates passed on this run: per-year cross-foot, per-column printed total, and agreement with an independent hand transcription of CY1996-2000. 1 source document(s) on disk.
    - `rejected:mms_component_printed_as_N_A_by_the_source_which_is_not_a_zero` — 141
- **`ANCSA_7i_7j_annual_reports`** — 166 retrieved report texts on disk; 134 declared facts, 134 of which pass 84's evidence gate (the quoted sentence or every printed token must appear in the named local document) and 0 refused. The facts flatten to 185 (corp, series, FY) claims with ZERO vintage collisions, so the vintage rule discards nothing. 166 source document(s) on disk.
- **`OSMRE_AML_fee_based_grant_distribution`** — 25 declared documents x 3 certified tribal programmes x 2 bases (before and after the sequestration reduction). Every published tribe-year emits BOTH bases, so the denominator is doubled and no row is a fan-out surprise. Pre-FY2013 vintages predate sequestration and lay the tables out differently in every year; FY2010-FY2012 are scanned images with no text layer. 25 source document(s) on disk.
    - `rejected:osmre_document_lacks_both_the_grant_and_the_sequestration_page_so_no_two_table_cross_check_exists` — 66
    - `rejected:osmre_row_shape_or_ocr_failure_a_money_cell_did_not_parse` — 6
    - `rejected:osmre_two_typeset_tables_in_the_same_document_disagree_on_the_arithmetic` — 2
- **`UT_COBI_fund_financials`** — 2 funds; revenues and expenses per year. Every non-blank cell published, expenses with the source's own negative sign retained. 2 source document(s) on disk.
- **`OMC_quarterly_newsletter`** — 12 documents linked from the OMC newsletter index; 2 are error pages the host still serves, 2 carry a healthy text layer and genuinely print no revenue table (an absent table is not a failed parse), 8 publish. Each publishing letter is dated by agreement between its stated per-headright figure and exactly one cell of the Council's own spreadsheet, never by its own quarter wording. 12 source document(s) on disk.
    - `rejected:omc_newsletter_does_not_print_this_component_line` — 4
    - `rejected:omc_newsletter_linked_from_the_index_but_the_host_returns_an_error_page` — 18
    - `rejected:omc_newsletter_prints_no_revenue_table_text_layer_verified_healthy` — 18
- **`MT_DOR_county_oil_gas_distribution`** — 49 cover letters, each carrying exactly ONE tribal line. The 57 county-distribution detail PDFs beside them carry no tribal line and are not read by this layer. A $0.00 line is an assertion that nothing was distributed and is published. 49 source document(s) on disk.
- **`MMS_MRM_american_indian_revenues`** — 8 CollFY*Ind.pdf documents x 6 published components (coal, gas, oil, other royalties, rents, other revenues). 1 document(s) held: RESOURCE:MMS:FY1997. 8 source document(s) on disk.
    - `rejected:mms_fiscal_year_document_failed_the_printed_subtotal_and_total_arithmetic_gate` — 6
- **`OSMRE_AML_IIJA_grant_distribution`** — 5 annual documents plus 1 one-time e-AMLIS document, x 3 tribal programmes. Crow and Hopi print a 0.0000% share, which is an ASSERTION of ineligibility and is published as a zero, not dropped. 6 source document(s) on disk.

### the other seven tables

`anc_ceiling_roster.csv` and `ancsa_filings_index.csv` are also merged this pass - their harvest is a `len()` and refusing them would be theatre. Five `natural-resources` tables have no conservation ledger yet: `nd_severance_allocation.csv`, `resource_assets.csv`, `resource_parties.csv`, `tribal_bond_issuances.csv`, `tribal_tax_bases.csv`. 518 reports the fraction it covers, so the scoreboard says so too. `resource_parties.csv` is a DERIVED bridge off the revenue and asset tables rather than a harvest, so a source-row ledger is the wrong instrument for it; the other four need their builders instrumented (`105`, `108`, `113`, `135`).

`natural-resources` also carries a C4 blocker — 25% of entity-bearing rows keyed — which is identity work and is NOT this workstream's. See `characterise`.

## gaming C1 — three tables

- **`fac_audit_sefa_gaming_programs.csv`** — 1 rows, key `report_id+award_reference`: unique on the full file, no blank component, 0 literal duplicate rows
- **`gaming_property_self_published_assertions.csv`** — 622 rows, key `assertion_id`: unique on the full file, no blank component, 0 literal duplicate rows
- **`gaming_property_self_published_claims.csv`** — 270 rows, key `claim_id`: unique on the full file, no blank component, 0 literal duplicate rows

The two self-published tables are prevented from being summed against a regulator's figure in three places at once: the `assertion_class` column on every row, the prohibition written into the grain prose in `512.GRAIN_GAMING_NR`, and the GAMING-NR section of `docs/MONEY_TOTALLING_RULES.md`.

## `62_no_regression_check.py` on 2026-09-01, and who owns each red line

62 exited 0 at the start of this workstream's pass and exits 1 at the end. TWO of the red lines were GAMING-NR's and are FIXED:

- `code_duplicate_numbers` 43 → 44. This script was first written as `812`, which `812_c8_rebuild_proof.py` had taken in the same window. Renumbered to 814; the metric is back at 43.
- `lint_class2c` 60 → 62, one instance named as this script's ANCSA evidence-gate counter. FIXED at source rather than waived: a refused fact is now recorded as (corporation, series, document stem, why) and printed. Back at 60.

A THIRD was created by this work and is DECLARED, not waived away. Carrying `award_reference` makes 814 an in-place enricher of a table 147 rebuilds wholesale — a class-6 pair. The ordering is written down by a person in 147's leading comment block (comment only; no logic in 147 was changed) and the waiver carries that reason, so it is counted and named by 293, never hidden. The enricher runs LAST.

The rest belong to other workstreams, are named here because GAMING-NR may not edit `AGENTS.md`, and standing rule 15 asks for a named owner rather than 'pre-existing, not mine':

| red line | measured cause | owner |
|---|---|---|
| `contract_orphan_shippable = 6` | `native_owned_businesses.csv`, `nonprofit_schedule_c_coverage.csv`, `nonprofit_schedule_c_lobbying.csv`, `regulations_gov_comments.csv`, `regulations_gov_entity_coverage.csv`, `sam_native_class_distributions.csv` are registered in the codebook and claimed by NO collection. All six are in the committed contracts at HEAD too. | native-owned-businesses, nonprofits, lobbying, contractors |
| `contract_violations = 7` | the six orphans above plus `entity_aliases.csv`: declared primary_key `alias_id` is NOT unique, 1 duplicate of 6,298, the value being blank. HEAD carries 8 violations; this pass's run of 512 REDUCED it to 7. | entity layer |
| `files_with_columns_lost_vs_backup = 1` | `entity_evidence_profile.csv` lost `in_spine`, `rows_per_source` and `amounts_per_source_NEVER_SUM` against `.bak_2026-08-28_pre505`. | entity layer / 505 |
| `lint_new_defect_instances = 1` | class6 on `cedar_dataset_readiness.csv`: 518 rebuilds it wholesale and another of 526/527/621/760 enriches it in place. | integrator |
| `rulings_unapplied` 1,215 → 2,894 | `cedar_ruling_ledger_consolidated.csv` now holds 2,894 `CONFLICT_NOT_APPLIED` of 43,321. | 173_consolidate_rulings_ledger.py |
| `tables_undocumented_in_codebook` / `tables_missing_codebook_block` 3 → 4, `tables_missing_from_25_TABLES` 179 → 188, `tables_missing_from_27_SPEC` 194 → 195 | new tables landed today without a codebook block; `cedar_entity_freshness.csv` (1,555 rows) is the one at a 0% ship ratio. | entity layer |
| SHIPPING LOST: `advocacy_passthrough_2026-08-07.csv` | was shipping 1,620 rows and the table is GONE from `data/clean`. | 111_build_advocacy_passthrough.py |

GAMING-NR touched none of those files. Its own writes are: `512.GRAIN_GAMING_NR`, `code/814_*`, one carried column on `fac_audit_sefa_gaming_programs.csv`, 19 merged rows in `cedar_harvest_conservation.csv`, a comment block in `147`, an inverted alarm in `573` whose own refusal asked to be retired on exactly this condition, and two marked docs.
