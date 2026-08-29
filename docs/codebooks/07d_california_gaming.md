# Codebook — California Gaming

*40,409 rows across 2 file(s). Generated 2026-08-07.*

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `payment_id` | text |  | 100% | Cedar-internal row identifier for one published California fund transfer: one party, one metric, one period. |
| `fund` | text |  | 100% | Which California fund the money moved through. `RSTF` is the Indian Gaming Revenue Sharing Trust Fund, `TNGF` the Tribal Nation Grant Fund, `SDF` the Indian Gaming Special Distribution Fund. Never sum across funds: RSTF and TNGF pay tribes, SDF pays local government. |
| `direction` | text |  | 100% | `paid_in` where a compacted tribe pays into the fund, `paid_out` where the fund pays a recipient. Both sides of the RSTF are Native governments, which is why the direction is a column and not an assumption. |
| `recipient_type` | text | code | 100% | Recipient organisation type code. |
| `tribe_id` | text | code | 89% | Cedar Press permanent identifier for the Native entity. Stable across releases; use this to join datasets. |
| `tribe_canonical_name` | text | text | 89% | Name. |
| `party_name_as_published` | text | text | 100% | The undivided string the notice published, before any splitting. Where a single published phrase named two nations, several rows share one value here. |
| `county` | empty | text | 0% | County as the source names it. Blank where the source publishes no county. |
| `metric` | text |  | 100% | What the amount is. RSTF recipient side: `rstf_distribution_from_revenue_received`, `rstf_distribution_from_shortfall_transfer`, `rstf_distribution_total`, `rstf_distribution_inception_to_date`. RSTF payer side: `rstf_payment_received_fiscal_year_to_date`, `rstf_payment_received_inception_to_date`. TNGF: one metric per grant programme. |
| `value` | numeric | USD, or a count | 99% | The published amount. Blank where the Commission suppressed the figure - see `value_suppressed_by_regulator`. |
| `unit` | text | text | 100% | Unit of the reported measure. |
| `period_start` | text | YYYY-MM-DD | 100% | First day of the period the amount covers. |
| `period_end` | text | YYYY-MM-DD | 100% | Last day of the period the amount covers. |
| `period_basis` *(internal)* | text |  | 100% | What span the amount covers: `quarter`, `fiscal_year_to_date`, or `fiscal_year`. A fiscal-year-to-date figure accumulates within the year and consecutive quarters must be differenced, not summed. |
| `measurement_type` | text | category | 99% | What kind of quantity the value is. Caps are AUTHORIZED_MAXIMUM: the maximum a compact permits, never the number in operation. |
| `value_suppressed_by_regulator` | text |  | 1% | `yes` where CGCC printed `--` against the tribe and reported its figure only inside the report's `Aggregate Total for Tribes` line. The obligation and the period are published; the amount is not. Suppressed is not zero. |
| `revenue_evidence_class` | text | category | 100% | The level and strength a revenue figure derived from this term would carry. |
| `compact_rate_pct` | numeric | percent | 2% | The single flat revenue-share rate the governing compact states, taken from `compact_structured_terms.csv`. Blank where the instrument carries no invertible flat rate. |
| `compact_revenue_concept` | text |  | 2% | The compact's own words for what the rate applies to (`Net Win`, `Gross Gaming Revenue`), copied verbatim and never generalised. |
| `compact_base_scope` | text |  | 2% | Whether the compact binds the revenue base to a single property or to the tribe's gaming as a whole. California's typical base, `the operation of Gaming Devices`, is tribe-level. |
| `payment_invertible` | text |  | 25% | Whether payment divided by rate recovers a revenue amount: `yes`, `bounded_below` where the compact lets the tribe deposit into either the RSTF or the TNGF so RSTF receipts alone understate the base, or `no`. |
| `derived_tribe_revenue_value` | empty | USD | 0% | `value / compact_rate_pct`, exact arithmetic, written only where the governing instrument states one flat rate against a stated base. It is the tribe's revenue under the compact's own concept, never a property revenue figure and never a total casino revenue figure. |
| `derived_revenue_scope` | empty |  | 0% | The scope the derivation actually reaches - `tribe` throughout California, because the compact base is tribe-level. |
| `bound_basis` | text |  | 100% | One of: `payment_is_a_transfer_not_a_revenue_base`, `no_invertible_flat_rate_in_governing_instrument`, `tribe_unresolved_no_compact_join`, `marginal_base_rate_applies_only_to_net_win_from_devices_above_a_stated_threshold`, `no_governing_compact_rate_term_on_file`, `per_device_component_in_same_instrument`, `rate_governs_a_different_fund_than_the_payment` |
| `compact_term_source_url` | text |  | 24% | Live URL of the compact instrument the rate was read from. |
| `compact_term_source_quote` | text |  | 24% | Verbatim clause from the governing compact stating the rate and the base it applies to. It is what licenses - or refuses - the derivation on the row, so it travels with the number. |
| `confidence_tier` | text | category | 100% | Publication tier. A = verified, publishable. B = provisional, withheld from published extracts. C = unattributed. X = ruled out. |
| `entity_match_method` *(internal)* | text |  | 100% |  |
| `entity_tier` | text |  | 89% | One of: `B` |
| `exclusion_flag` | text | 0/1 | 35% | Indicator variable. |
| `exclusion_reason` | text | text | 35% | Why a record was ruled outside the Native universe. |
| `source_authority` *(internal)* | text |  | 100% | One of: `California Gambling Control Commission` |
| `source_document_type` | text |  | 100% | One of: `rstf_quarterly_distribution`, `tngf_disbursement_report`, `cgcc_casino_list`, `rstf_shortfall_notification`, `cgcc_rstf_eligible_list`, `cgcc_paying_tribes_list` |
| `source_url` | text | URL | 100% | Link to the record's published source. |
| `source_page` | integer | integer | 100% | Page of the source document. |
| `source_quote` | text | text | 100% | The document's own words supporting the recorded term. |
| `source_link_text` | text |  | 100% | The label CGCC gives the document on its own index page, e.g. `Quarter Ended: 06/30/2026`. It is the Commission's own statement of the period and is preferred over any date inside the file. |
| `zone_header` | text |  | 100% | The exhibit caption above the table the row came from, verbatim. The exhibit NUMBER is not stable across editions - the payer table is Exhibit 3 in the 2000s and Exhibit 2 in the 2020s - so the caption, not the number, identifies the table. |
| `foot_status` | text |  | 100% | Whether the extracted table reconciles against the document's own printed Totals row: `foots`, `no_total`, or a per-programme variant. A table that does not foot is not published. |
| `foot_detail` | text |  | 100% | Per-column comparison of the extracted sum against the printed total, so the reconciliation can be checked without the PDF. |
| `document_status` | text |  | 100% | `original` or `revised`. CGCC republishes some quarters as REVISED staff reports; the superseded rows stay readable and carry an exclusion flag rather than being deleted. |
| `issue_date` | text | ISO date | 0% | Date the Commission records for a Tribal Nation Grant Fund disbursement. |
| `fetched_date` | text | YYYY-MM-DD | 100% | Date. |
| `built_date` | text | YYYY-MM-DD | 100% | Date. |
| `built_by_script` | text |  | 100% | One of: `code/103_build_california_gaming.py` |
| `record_id` | text |  | 100% | Cedar-internal identifier for one line of one CGCC roster. |
| `list_type` | text |  | 100% | Which CGCC roster the row came from: `cgcc_casino_list`, `cgcc_rstf_eligible_list`, or `cgcc_paying_tribes_list`. |
| `as_of_date` | text | ISO date | 100% | The date the Commission prints on the roster itself. |
| `tribe_name_as_published` | text |  | 100% | The tribe's name exactly as the roster prints it, before resolution. |
| `facility_id` | text | code | 73% | Identifier. |
| `facility_name` | text | text | 73% | Name. |
| `facility_name_as_published` | text |  | 98% | The casino name exactly as the roster prints it. A regulator using a different name for a known property is an alias, not a second property. |
| `facility_name_match_method` *(internal)* | text |  | 100% | How the roster's casino name was attached to an existing Cedar property: `exact_name_in_state`, `sole_property_of_tribe_in_state`, `no_facility_named` for a tribe with no casino, or `unresolved_facility_name` with candidates listed in the review queue. There is no fuzzy tier. |
| `casino_city` | text |  | 98% | City the Commission gives for the casino. |
| `casino_county` | text |  | 98% | County the Commission gives for the casino. |
| `pays_into_sdf` | text |  | 14% | `yes` where the Commission ticks the Special Distribution Fund column for this tribe. Read from which column the tick sits in, never from how many ticks the row carries. |
| `pays_into_rstf` | text |  | 13% | `yes` where the Commission ticks the Revenue Sharing Trust Fund column for this tribe. |
| `rstf_eligible` | text |  | 30% | `yes` where the tribe appears on the Commission's list of tribes eligible to RECEIVE RSTF distributions - the non-gaming and limited-gaming tribes. Most carry no casino at all, and that is the point of the fund. |

## Value sets

- **`fund`** — `RSTF`, `TNGF`
- **`direction`** — `paid_out`, `paid_in`
- **`recipient_type`** — `tribe`, `aggregate_of_suppressed_tribes`
- **`metric`** — `rstf_distribution_total`, `rstf_distribution_from_revenue_received`, `rstf_distribution_from_shortfall_transfer`, `rstf_distribution_inception_to_date`, `rstf_payment_received_fiscal_year_to_date`, `rstf_payment_received_inception_to_date`, `tngf_equal_distribution_grant`, `tngf_covid19_emergency_grant`, `tngf_emergency_response_grant`, `tngf_impact_grant`, `tngf_capacity_building_grant`
- **`revenue_evidence_class`** — `NO_REVENUE_OBSERVATION`, `TRIBE_LEVEL_REVENUE`, `BOUNDED_DERIVED_REVENUE`
- **`compact_revenue_concept`** — `Net Win`, `Gross Gaming Revenue`, `net win`
- **`bound_basis`** — `payment_is_a_transfer_not_a_revenue_base`, `no_invertible_flat_rate_in_governing_instrument`, `tribe_unresolved_no_compact_join`, `marginal_base_rate_applies_only_to_net_win_from_devices_above_a_stated_threshold`, `no_governing_compact_rate_term_on_file`, `per_device_component_in_same_instrument`, `rate_governs_a_different_fund_than_the_payment`
- **`exclusion_flag`** — `cumulative_do_not_sum`, `superseded_by_revised_report`, `value_suppressed_by_regulator`, `not_a_single_tribe`
- **`exclusion_reason`** — `Inception-to-date total. Published beside annual figures it is a double count; extracted and footed, withheld from any sum.`, `CGCC republished this quarter as a REVISED staff report.`, `CGCC prints `--` against this tribe and reports its figure only inside the report's `Aggregate Total for Tribes` line. The obligation and the period are published; the amount is not. Suppressed is not zero.`, `Combined figure for the tribes whose individual amounts CGCC suppresses. Kept because the report's Totals row foots only with it; never attributed to any tribe.`
- **`source_document_type`** — `rstf_quarterly_distribution`, `tngf_disbursement_report`, `cgcc_casino_list`, `rstf_shortfall_notification`, `cgcc_rstf_eligible_list`, `cgcc_paying_tribes_list`
- **`foot_status`** — `foots`, `no_total`
- **`document_status`** — `original`, `revised`
- **`list_type`** — `cgcc_casino_list`, `cgcc_rstf_eligible_list`, `cgcc_paying_tribes_list`
- **`as_of_date`** — `2025-01-23`, `2025-11-13`, `2024-11-05`
