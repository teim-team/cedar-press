# Codebook — Subcontracting

*63,768 rows across 2 file(s). Generated 2026-08-07.*

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `sub_uei` *(subscriber)* | text | code | 100% | UEI of the subawardee. |
| `sub_cage` | text | code | 2% | CAGE code of the subawardee. |
| `sub_name` | text | text | 100% | Name. |
| `sub_state` | text | 2-letter code | 100% | State of the subawardee. |
| `prime_uei` *(subscriber)* | text | code | 100% | UEI of the prime contractor. |
| `prime_cage` | text | code | 2% | CAGE code of the prime contractor. |
| `prime_name` | text | text | 100% | Name. |
| `prime_award_id` | text | code | 100% | Identifier. |
| `subaward_amount` | numeric | USD, nominal | 100% | Amount of the subaward. |
| `subaward_date` | text | YYYY-MM-DD | 100% | Date. |
| `fiscal_year` | integer | YYYY | 100% | Federal fiscal year (October-September). |
| `naics` | integer | code | 49% | North American Industry Classification System code. |
| `psc` | text | code | 2% | Product or Service Code describing what was bought. |
| `description` | text | text | 100% | Description of the item. |
| `direction` | text |  | 100% | `paid_in` where a compacted tribe pays into the fund, `paid_out` where the fund pays a recipient. Both sides of the RSTF are Native governments, which is why the direction is a column and not an assumption. |
| `source_file` *(internal)* | text |  | 100% |  |
| `fetched_date` | text | YYYY-MM-DD | 100% | Date. |
| `subaward_number` *(subscriber)* | text | code | 100% | Subaward identifier. |
| `source_url` | text | URL | 100% | Link to the record's published source. |
| `sub_parent_uei` *(subscriber)* | text | code | 60% | UEI of the subawardee's parent. |
| `sub_parent_cage` | text | code | 2% | CAGE code of the subawardee's parent. |
| `sub_parent_name` | text | text | 50% | Name. |
| `prime_parent_uei` *(subscriber)* | text | code | 87% | UEI of the prime contractor's parent. |
| `prime_parent_cage` | text | code | 1% | CAGE code of the prime contractor's parent. |
| `prime_parent_name` | text | text | 80% | Name. |
| `naics_title` | text | text | 49% | Industry name for the NAICS code. |
| `psc_title` | text | text | 2% | Description of the Product or Service Code. |
| `prime_top_awarding_agency` | text | text | 100% | Agency awarding most of the prime's value. |
| `prime_set_aside` | text |  | 0% | One of: `8(A) Sole Source  (8AN)`, `Small Business Set Aside - Total (SBA)`, `Hubzone Set-Aside (HZC)`, `8(A) Competed (8A)`, `Indian Economic Enterprise (IEE)`, `Economically Disadvantaged Women Owned Small Business (EDWOSB)`, `Indian Small Business Economic Enterprise (ISBEE)`, `Service Disabled Veteran Owned Small Business Set-Aside (SDVOSBC)` |
| `pre_2000_flag` | empty | 0/1 | 0% | 1 when the record predates the 2000 coverage floor. Such records are retained but fall outside the standard reporting window. |
| `floor_basis_field` | text |  | 100% | One of: `subaward_date` |
| `source_dataset` *(internal)* | text |  | 100% | One of: `usaspending_fsrs_pull`, `usaspending_fsrs_name_match`, `highergov_2023_export`, `funding_forward_fill`, `usaspending_fsrs_parent_cluster` |
| `source_population` | text |  | 100% | One of: `full_federal_subaward_universe`, `highergov_query_frame_unpreserved`, `prime_tribal_filtered` |
| `award_kind` | text |  | 100% | One of: `assistance`, `contract` |
| `subaward_type` | text |  | 98% | One of: `sub-grant`, `sub-contract` |
| `prime_award_unique_key` | text | code | 98% | Stable key of the prime award the subaward sits under. |
| `prime_award_amount` | numeric | USD, nominal | 94% | Amount. |
| `subaward_to_prime_ratio` | numeric | ratio | 94% | Subaward amount divided by its own prime award amount. A value above 1 is a filer error, not a large subaward: 0.82% of rows report a subaward LARGER than the prime it came from, one of them 12,240x. Filter on this before summing; the rows are flagged, never deleted. |
| `subaward_exceeds_prime_flag` | text | 0/1 | 1% | Indicator variable. |
| `action_date_precedes_ffata_flag` | text | 0/1 | 0% | Indicator variable. |
| `subaward_sam_report_year` | integer | YYYY | 98% | Year. |
| `prime_native_tribe_id` | text | code | 42% | Identifier. |
| `prime_native_tier` | text |  | 42% | One of: `A`, `B`, `source_filter` |
| `sub_native_tribe_id` | text | code | 60% | Identifier. |
| `sub_native_tier` | text |  | 60% | One of: `B`, `A` |
| `sub_business_types` | text | codes | 95% | Business-type codes reported for the subawardee. |
| `prime_awarding_sub_agency` | text | text | 98% | Sub-agency that made the prime award. |
| `duplicate_status` | text |  | 100% | One of: `primary`, `exact_repeat_within_source`, `superseded_by_primary_source` |
| `promoted_date` | text | YYYY-MM-DD | 100% | Date. |
| `n_subawards` | integer | integer | 100% | Count. |
| `total_usd` | integer | USD, nominal | 100% | Amount. |
| `first_year` | integer | YYYY | 100% | Year. |
| `last_year` | integer | YYYY | 100% | Year. |
| `naics_modal` | integer | code | 100% | Most frequent NAICS industry code across the relationship. |
| `self_edge_flag` | text | 0/1 | 1% | Indicator variable. |

## Value sets

- **`direction`** — `b_native_as_subawardee`, `a_native_as_prime`, `both_sides_native`, `unknown`
- **`prime_set_aside`** — `8(A) Sole Source  (8AN)`, `Small Business Set Aside - Total (SBA)`, `Hubzone Set-Aside (HZC)`, `8(A) Competed (8A)`, `Indian Economic Enterprise (IEE)`, `Economically Disadvantaged Women Owned Small Business (EDWOSB)`, `Indian Small Business Economic Enterprise (ISBEE)`, `Service Disabled Veteran Owned Small Business Set-Aside (SDVOSBC)`
- **`source_population`** — `full_federal_subaward_universe`, `highergov_query_frame_unpreserved`, `prime_tribal_filtered`
- **`award_kind`** — `assistance`, `contract`
- **`subaward_type`** — `sub-grant`, `sub-contract`
- **`prime_native_tier`** — `A`, `B`, `source_filter`
- **`sub_native_tier`** — `B`, `A`
- **`duplicate_status`** — `primary`, `exact_repeat_within_source`, `superseded_by_primary_source`
- **`promoted_date`** — `2026-08-06`, `2026-08-07`
