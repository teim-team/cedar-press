# Codebook — NIGC regions

*Variables only. Method, sourcing and every figure verified against a document are in `docs/NIGC_REGION_BUILD_LOG.md`.*
*2,636 rows across 2 files. Built 2026-08-06.*


## `nigc_regional_ggr.csv`

The NIGC regional gross gaming revenue series, FY2001-FY2025. 198 rows.

| Variable | Type | Filled | Description |
|---|---|---:|---|
| `administrative_region_id` | text | 100% | Cedar Press administrative-region key, format `CEDAR-ADMREG-######`. Shared column contract with the BIA/IHS/HUD-ONAP region crosswalk. NIGC regions occupy the reserved 9000xx block. **A region id is specific to a region SYSTEM VERSION**: `Region I` under the FY2001 system and `Region I` under the FY2003 system are different geographies and carry different ids. |
| `region_system_code` | text | 100% | Always `NIGC_REGION`. Names the region system this row belongs to. |
| `region_name` | text | 100% | NIGC's name for the region as printed for that system version. Values change across versions (`Eastern Region` -> `Region VI` -> `Washington DC`); see `region_system_version`. |
| `region_system_version` | text | 100% | Which of NIGC's four region systems was in force. One of: `NIGC_R1_FY2001_FY2002` (6 regions), `NIGC_R2_FY2003_FY2007` (6), `NIGC_R3_FY2008_FY2016` (7), `NIGC_R4_FY2017_present` (8). **Never join across versions on `region_name` alone.** |
| `fiscal_year` | numeric | 100% | NIGC fiscal year the revenue covers. Operations have differing fiscal year-ends, so a fiscal year is a reporting window, not a calendar window. |
| `ggr_usd` | numeric | 100% | Gross gaming revenue in nominal US dollars as NIGC printed it. See `figure_precision` before treating it as exact. |
| `ggr_usd_real2025` | numeric | 100% | `ggr_usd` in constant 2025 dollars, BEA GDP implicit price deflator (NIPA Table 1.1.9). Base year is 2025 because 2026 is not a complete year and BEA publishes no annual index for it. |
| `operation_count` | numeric | 100% | Number of gaming operations NIGC counted in the region that year. **An operation is a submitter of audited financial statements, not a building.** It is not a property count and will not reconcile 1:1 with a facility file. |
| `ggr_change_pct` | numeric | 86% | Percent change in `ggr_usd` against the same region's prior fiscal year within the same region system version. Blank where the prior year sits in a different system. |
| `ggr_change_pct_basis` | text | 100% | How `ggr_change_pct` was obtained. One of: `computed_from_cedar_series_exact`, `computed_from_cedar_series_rounded_inputs` (inputs rounded to $0.1B, so the percentage carries that rounding), `no_prior_year_in_this_region_system`. |
| `region_mean_ggr_per_operation_usd` | numeric | 100% | `ggr_usd` / `operation_count`. **A descriptive statistic about the region, never an estimate for any property.** In FY2025 roughly 9% of operations made ~56% of GGR while 54%+ made ~5%, so this mean describes almost no individual operation. |
| `region_mean_is_descriptive_only` | numeric | 100% | Always 1. Present so that a downstream join cannot silently promote the regional mean into a property-level figure. |
| `revenue_measure` | text | 100% | Always `nigc_gross_gaming_revenue`. |
| `geographic_level` | text | 100% | Always `nigc_region`. The finest level at which this revenue exists. |
| `allocation_level` | text | 100% | Always `aggregate_only`. NIGC publishes no property-level revenue and Cedar Press does not construct one. |
| `includes_nongaming_revenue` | text | 100% | Always `false`. |
| `measure_note` | text | 100% | What GGR is and is not, repeated on every row so a single extracted row still carries its own definition. |
| `figure_precision` | text | 100% | How precisely NIGC printed the figure. One of: `exact_dollars`, `exact_thousands` (printed in thousands, stored in dollars), `rounded_0.1B` (map-only years FY2013-FY2020; up to $50M of rounding per region). |
| `figure_vintage` | text | 100% | Which column of which report the figure came from. `own_year_report` = the report headlined for this fiscal year. `prior_year_column` = the comparison column of a later report. NIGC restated prior years in the early series, so the two vintages can differ for the same fiscal year. |
| `deflator_factor_2025` | numeric | 100% | Multiplier applied to reach 2025 dollars. |
| `inflation_base_year` | numeric | 100% | Always 2025. |
| `region_states_in_force` | text | 100% | States (or sub-state parts) NIGC printed in this region's legend for this system version. `NV-N`/`NV-S` = Northern/Southern Nevada; `OK-E`/`OK-W` = Eastern/Western Oklahoma. NIGC publishes no boundary line inside either state. |
| `source_url` | text | 100% | The NIGC page the document was retrieved from. |
| `source_document` | text | 100% | Filename of the NIGC PDF the figure was read out of. The file is held under `data/raw/external/nigc/ggr_reports/`. |
| `source_document_title` | text | 100% | Title NIGC gives that document. |
| `fetched_date` | text | 100% | Date the document was retrieved. |
| `built_date` | text | 100% | Date this row was written. |

## `nigc_region_assignments.csv`

Property-to-NIGC-region assignment, dated to the region system in force. 2,438 rows.

| Variable | Type | Filled | Description |
|---|---|---:|---|
| `facility_id` | text | 100% | Key into `gaming_facilities.csv`. |
| `administrative_region_id` | text | 93% | Cedar Press administrative-region key, format `CEDAR-ADMREG-######`. Shared column contract with the BIA/IHS/HUD-ONAP region crosswalk. NIGC regions occupy the reserved 9000xx block. **A region id is specific to a region SYSTEM VERSION**: `Region I` under the FY2001 system and `Region I` under the FY2003 system are different geographies and carry different ids. |
| `region_system_code` | text | 100% | Always `NIGC_REGION`. Names the region system this row belongs to. |
| `region_name` | text | 93% | NIGC's name for the region as printed for that system version. Values change across versions (`Eastern Region` -> `Region VI` -> `Washington DC`); see `region_system_version`. |
| `region_system_version` | text | 100% | Which of NIGC's four region systems was in force. One of: `NIGC_R1_FY2001_FY2002` (6 regions), `NIGC_R2_FY2003_FY2007` (6), `NIGC_R3_FY2008_FY2016` (7), `NIGC_R4_FY2017_present` (8). **Never join across versions on `region_name` alone.** |
| `effective_start_year` | numeric | 100% | First year this assignment holds: the later of the region system's first year and the property's opening year. |
| `effective_end_year` | numeric | 74% | Last year this assignment holds: the earlier of the region system's last year and the property's closing year. Blank means the current system, still open. |
| `assignment_method` | text | 100% | How the region was determined. `nigc_published_state_to_region_legend` = the property's state appears in exactly one region of the legend NIGC printed for this system. `nigc_published_gaming_location_map` = NIGC itself places this property in a region on its gaming location map (the only sourced answer inside Oklahoma and Nevada). `unassigned_substate_split_not_sourced` = the property sits in a split state and is not on NIGC's map, so no region is asserted. `state_absent_from_published_legend_for_this_system` = the state appears in no NIGC legend for this system. |
| `assignment_geography_basis` | text | 100% | Always `property_location_not_tribal_headquarters`. A tribe headquartered in one state can operate a property in another; the region follows the property. |
| `igra_coverage_status` | text | 100% | One of `VERIFIED_NIGC_OPERATION` (on NIGC's published gaming location list), `LIKELY_IGRA_OPERATION`, `NON_IGRA_TRIBALLY_OWNED`, `PROPOSED_IGRA_OPERATION`, `CLOSED_IGRA_OPERATION`, `MANAGED_BUT_NOT_OWNED`, `UNKNOWN`. Absence from NIGC is not evidence a property is not ours: NIGC's universe is class II and class III gaming on Indian lands, so a tribally owned casino operating outside IGRA never appears there. |
| `nigc_operation_match_status` | text | 100% | `MATCHED_NIGC_GAMING_LOCATION` or `NOT_ON_NIGC_GAMING_LOCATION_MAP`. Named for the LOCATION map deliberately: NIGC's 490 mapped locations and its 545 FY2025 audited-financial-statement operations are two different NIGC universes. |
| `is_primary` | numeric | 100% | 1 on the row for the region system currently in force, 0 on historical rows. |
| `confidence` | text | 100% | `high`, `medium`, `none`. `none` accompanies every unassigned row. |
| `facility_state` | text | 100% | Property state, from the facility record. |
| `facility_city` | text | 95% | Property city, from the facility record. |
| `tribe_id` | text | 98% | Cedar entity spine key for the owning entity, as carried on the facility record. |
| `nigc_marker_id` | numeric | 47% | NIGC's own id for the matched location on its gaming location map. |
| `source_url` | text | 100% | The NIGC page the document was retrieved from. |
| `fetched_date` | text | 100% | Date the document was retrieved. |
| `built_date` | text | 100% | Date this row was written. |
