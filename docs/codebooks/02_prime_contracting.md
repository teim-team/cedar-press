# Codebook — Prime Contracting

*623,496 rows across 2 file(s). Generated 2026-08-07.*

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `contract_number` *(subscriber)* | text | code | 100% | Contract or award identifier. |
| `parent_contract_number` *(subscriber)* | text | code | 100% | Identifier of the parent vehicle the action was placed against. |
| `fiscal_year` | integer | YYYY | 100% | Federal fiscal year (October-September). |
| `pre_2000_flag` | integer | 0/1 | 100% | 1 when the record predates the 2000 coverage floor. Such records are retained but fall outside the standard reporting window. |
| `awardee_name` | text | text | 100% | Name. |
| `awardee_uei` *(subscriber)* | text | code | 100% | UEI of the contracting party. |
| `cage_code` *(subscriber)* | text | code | 34% | Commercial and Government Entity code (5 characters). |
| `parent_name` | text | text | 100% | Name. |
| `parent_uei` *(subscriber)* | text | code | 100% | UEI of the awardee's parent organisation. |
| `total_obligations` | text | USD, nominal | 100% | Obligated amount on the contract action. |
| `total_award_value` | integer | USD, nominal | 100% | Total potential award value including unexercised options. |
| `total_obligations_real2025` | numeric | USD, constant 2025 | 100% | Obligations restated in constant 2025 dollars. Empty where the deflator has not been applied to that row. |
| `total_award_value_real2025` | numeric | USD, constant 2025 | 100% | Award value restated in constant 2025 dollars. Empty where the deflator has not been applied to that row. |
| `deflator_factor_2025` | numeric | ratio | 100% | The factor multiplying nominal dollars to reach constant 2025 dollars. Base years must never be mixed across a sum. |
| `inflation_base_year` | integer | YYYY | 100% | Year. |
| `setaside` | text | category | 100% | Set-aside or preference programme under which the contract was awarded. |
| `reported_8a` | integer | 0 to 1 | 100% | One of: `0`, `1` |
| `reported_buy_indian` | integer | 0 to 1 | 100% | One of: `0`, `1` |
| `reported_indian_business` | integer | 0 to 1 | 100% | One of: `0`, `1` |
| `reported_native_preference` | integer | 0 to 1 | 100% | One of: `0`, `1` |
| `setaside_reported` | integer | 0 to 1 | 100% | One of: `1`, `0` |
| `extent_competed` | text | category | 98% | Degree of competition in the award. |
| `funding_agency` | text | text | 100% | Agency funding the action. |
| `sector` | text | category | 100% | Industry sector of the work. |
| `supersector` | text | category | 99% | Aggregated industry grouping. |
| `defense` | integer | 0/1 | 100% | 1 when the funding agency is a defence agency. |
| `recipient_city_name` | text | text | 100% | Name. |
| `recipient_state_code` | text | 2-letter code | 100% | Recipient state. |
| `place_of_perform_city` | text | text | 89% | City where the work is performed. |
| `place_of_perform_state` | text | 2-letter code | 98% | State where the work is performed. Often differs from the recipient's state. |
| `tribe_id` | text | code | 47% | Cedar Press permanent identifier for the Native entity. Stable across releases; use this to join datasets. |
| `canonical_name` | text | text | 47% | Cedar Press standard name for the Native entity. |
| `attribution_method` *(internal)* | text |  | 100% | One of: `unattributed`, `uei_exact`, `cage_exact`, `parent_uei` |
| `confidence_tier` | text | category | 100% | Publication tier. A = verified, publishable. B = provisional, withheld from published extracts. C = unattributed. X = ruled out. |
| `attributed_flag` | integer | 0/1 | 100% | Indicator variable. |
| `source_file` *(internal)* | text |  | 100% | One of: `master prime file.dta` |
| `source_authority` *(internal)* | text |  | 100% | One of: `Elijah hand-checked master prime file` |
| `built_date` | text | YYYY-MM-DD | 100% | Date. |
| `obligations_usd` | numeric | USD, nominal | 100% | Obligated amount. |
| `n_contracts` | integer | integer | 100% | Count. |

## Value sets

- **`setaside`** — `None reported`, `8(a)`, `Small Business`, `Other`, `HUBZone`, `Indian Business`, `Buy Indian`
- **`extent_competed`** — `NOT AVAILABLE FOR COMPETITION`, `FULL AND OPEN COMPETITION AFTER EXCLUSION OF SOURCES`, `COMPETED UNDER SAP`, `FULL AND OPEN COMPETITION`, `NOT COMPETED UNDER SAP`, `NOT COMPETED`, `COMPETITIVE DELIVERY ORDER`, `NON-COMPETITIVE DELIVERY ORDER`, `FOLLOW ON TO COMPETED ACTION`
- **`sector`** — `23`, `54`, `56`, `33`, `32`, `42`, `Not given`, `62`, `51`, `53`, `81`, `61`, `31`, `48`, `11`, `22`, `72`, `44`, `92`, `45`, `71`, `49`, `21`, `52`, `55`
- **`supersector`** — `Professional & Business Services`, `Construction`, `Manufacturing`, `Trade, Transportation, & Utilities`, `Other services or Not given`, `Education & Health Services`, `Information`, `Financial Activities`, `Leisure & Hospitality`, `Natural Resources & Mining`
- **`confidence_tier`** — `C`, `A`, `B`
