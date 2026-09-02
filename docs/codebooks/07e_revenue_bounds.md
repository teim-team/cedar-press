# Codebook - gaming revenue bounds

*Variables only. Method, sourcing and every figure verified against a document are in `docs/REVENUE_BOUNDS_LOG.md`.*

**A factual bound is not a confidence interval.** Every number in these two files is arithmetic on figures a source printed. Nothing here is modelled and no column may be read as one.

## `data/clean/gaming_revenue_bounds.csv`

| variable | type | definition |
|---|---|---|
| `bound_id` | string | Cedar row id. `RVB-CEIL-` regional ceiling, `RVB-CEILNET-` ceiling net of known property revenue, `RVB-RESID-` region-year residual, `RVB-REPT-` reported property revenue, `RVB-SINGLE-` single-property attribution, `RVB-TRIBE-` tribe-level figure held at tribe level. |
| `facility_id` | string | Cedar property id (`CCP-`/`VP-`/`TPL-`), key into `gaming_facilities.csv`. **Blank on region-level and tribe-level rows**, where no single property is named. |
| `tribe_id` | string | Cedar entity spine id of the owning entity. Blank on region-level rows. |
| `fiscal_year` | integer | The year the bound covers. For rows carrying a NIGC figure this is the NIGC fiscal year (October to September). For rows carrying a state figure it is the period the state published, which is NOT always the NIGC fiscal year; `assumption_note` states which on every row. |
| `revenue_lower_bound` | number, USD | A floor: the property's revenue for the stated concept is at least this. Blank where no floor is established. |
| `revenue_upper_bound` | number, USD | A ceiling: the revenue cannot exceed this, because a part cannot exceed its total. Blank where no ceiling applies. |
| `point_value` | number, USD | A single figure, used only where a source states one or where arithmetic on published figures yields exactly one. Never a midpoint of the bounds. |
| `measurement_status` | enum | What KIND of revenue evidence the row is. From `cedar_domain.REVENUE_EVIDENCE`: `REPORTED_PROPERTY_REVENUE`, `TRIBE_LEVEL_REVENUE`, `REGIONAL_GGR_CEILING`; plus `SINGLE_PROPERTY_ATTRIBUTED` from `cedar_domain.SINGLE_PROPERTY_ATTRIBUTED`, which is deliberately its own status so an inference can never be read as an observation. |
| `bound_basis` | enum | What makes the bound true. `REGIONAL_GGR_CEILING`; `REGIONAL_GGR_CEILING_NET_OF_KNOWN`; `UNKNOWN_PROPERTIES_RESIDUAL_SUM`; `RESIDUAL_CLOSED_SINGLE_UNKNOWN_OPERATION`; `REPORTED_SLOT_WIN_IS_FLOOR_FOR_GGR`; `SINGLE_PROPERTY_TRIBE_LEVEL_GAMING_REVENUE`; `TRIBE_LEVEL_NOT_ATTRIBUTABLE_TO_A_PROPERTY`. Populated on every row: without it a bound is indistinguishable from a modelled figure. |
| `n_properties_tribe_operated` | integer | Gaming properties Cedar records the tribe as operating in that year. Blank where the tribe is not named or the count is not determinable. |
| `n_operations_in_region` | integer | Operations NIGC counted in the region that year. **An operation is a submitter of audited financial statements, not a building**, so it will not reconcile 1:1 with a property file. Present so a reader can see the denominator - it is NOT a divisor. |
| `regional_total_usd` | number, USD | NIGC gross gaming revenue for the whole region-year. Gaming win only; excludes hotel, food, entertainment and retail. |
| `known_property_sum_usd` | number, USD | Property revenue Cedar already holds inside that region-year and has subtracted. Blank where nothing was subtracted. |
| `assumption_note` | string | What the row assumes, which direction it can be wrong in, and what its revenue concept and period are. Travels with the row so a join cannot lose it. |
| `source_url` | string | The publisher's URL for the figure. |
| `source_quote` | string | Verbatim support, whitespace collapsed and nothing else changed. For a total built from monthly figures, ALL the monthly quotes are carried, because one month's quote would not support a twelve-month figure. Blank where the source is a chart or map with no quotable line rather than where support is missing. |
| `confidence` | enum | `high` / `medium`. Not a probability and not an interval. |
| `tier` | enum | Always `B` - pending review. |
| `built_date` | date | When this row was written. |

## `data/clean/nigc_revenue_bands.csv`

| variable | type | definition |
|---|---|---|
| `band_id` | string | Cedar row id, `NIGCBAND-<fiscal year>-<band ordinal>`. |
| `fiscal_year` | integer | NIGC fiscal year. Bands exist for FY2022 to FY2025 only; NIGC published no band table before FY2022. |
| `band_ordinal` | integer | 1 (lowest band) to 5 (highest). |
| `band_label` | string | The band as NIGC labels it: `<$25M`, `$25-50M`, `$50-100M`, `$100-250M`, `$250M+`. |
| `band_lower_usd` | number, USD | Lower edge. Blank on the lowest band, which is open below. |
| `band_upper_usd` | number, USD | Upper edge. Blank on the highest band, which is open above. |
| `pct_of_operations` | number, percent | Share of gaming operations in this band, as NIGC printed it. |
| `pct_of_revenue` | number, percent | Share of total GGR contributed by this band, as NIGC printed it. |
| `pct_precision` | enum | `1_percent` (FY2022, FY2023) or `0.1_percent` (FY2024, FY2025). Sets the rounding interval that the implied counts and dollars carry. |
| `national_operation_count` | integer | Operations in NIGC's national total that year, as its own report states. |
| `national_ggr_usd` | number, USD | National GGR that year, the sum of NIGC's published region figures. |
| `n_operations_implied_low` | integer | Fewest operations consistent with the printed share and its rounding. |
| `n_operations_implied_high` | integer | Most operations consistent with the printed share and its rounding. NIGC printed the share, not the count; a single count would be a figure it did not publish. |
| `band_aggregate_ggr_implied_low_usd` | number, USD | Least combined GGR consistent with the printed revenue share and its rounding. |
| `band_aggregate_ggr_implied_high_usd` | number, USD | Most combined GGR consistent with the same. |
| `per_operation_upper_bound_usd` | number, USD | The band's upper edge, which is a ceiling on any single operation inside it. Blank on the top band, which has no upper edge. |
| `derivation_note` | string | What the arithmetic is and what it does not license. The band bounds the SET; it never names a property. |
| `chart_label_basis` | string | Which labels came from the PDF text layer and which were read off a render of the chart by hand. |
| `source_url` | string | NIGC's report landing page. |
| `source_document` | string | Filename of the NIGC PDF, held under `data/raw/external/nigc/ggr_reports/`. |
| `source_document_title` | string | Title NIGC gives that document. |
| `source_page` | integer | Page of that PDF carrying the chart. |
| `source_quote` | string | NIGC's own sentence stating the top band's share, verbatim. |
| `operation_count_source_quote` | string | NIGC's own sentence stating the national operation count, verbatim. |
| `confidence` | enum | `high`. |
| `tier` | enum | Always `B` - pending review. |
| `review_status` | enum | `pending_review`. |
| `fetched_date` | date | When the PDF was retrieved. |
| `built_date` | date | When this row was written. |
