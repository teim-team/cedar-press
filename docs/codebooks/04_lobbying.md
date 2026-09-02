# Codebook — Lobbying

*32,847 rows across 2 file(s). Generated 2026-08-07.*

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `filing_uuid` *(subscriber)* | text | code | 100% | Unique identifier of the disclosure filing. |
| `entity_id` | text | code | 97% | Identifier. |
| `canonical_name` | text | text | 97% | Cedar Press standard name for the Native entity. |
| `entity_type` | text |  | 100% | One of: `Federally recognized tribe`, `Alaska Native Regional Corporation`, `Federally recognized Alaska Native Village`, `Federal-level self-governance consortium`, `State-recognized tribe`, `Federal-level constituency entity`, `State-level constituency entity` |
| `entity_state` | text | 2-letter code | 100% | State of the Native entity. |
| `client_name` | text | text | 100% | Client named on the lobbying disclosure. |
| `client_id` | integer | code | 100% | Identifier. |
| `client_state` | text | 2-letter code | 93% | State of the client. |
| `registrant_name` | text | text | 100% | Lobbying firm, or the entity itself when self-filed. |
| `registrant_id` | integer | code | 100% | Identifier. |
| `registrant_state` | text | 2-letter code | 100% | State of the registrant. |
| `self_filed` | integer | 0/1 | 100% | 1 when the entity filed its own disclosure rather than retaining an outside firm. |
| `filing_year` | integer | YYYY | 100% | Calendar year of the disclosure filing. |
| `filing_period` | text | category | 100% | Reporting period covered. |
| `filing_type` | text | code | 100% | Filing type code. |
| `filing_type_display` | text | category | 100% | Filing type, such as a quarterly report or a registration. |
| `income_usd` | integer | USD, nominal | 63% | Lobbying income reported by the registrant. |
| `expenses_usd` | integer | USD, nominal | 1% | Lobbying expenses reported by the filer. |
| `spend_usd` | integer | USD, nominal | 100% | Reported lobbying spend for the filing period. |
| `spend_basis` | text |  | 100% | One of: `income`, `none_reported`, `expenses` |
| `lobbying_issues_codes` | text | codes | 82% | Issue-area codes on the filing. |
| `specific_issues_text` | text | text | 70% | Narrative description of the issues lobbied. |
| `government_entities` | text | text | 75% | Chambers and agencies lobbied. |
| `affiliated_organizations` | text | text | 0% | Organisations affiliated with the client. |
| `dt_posted` | text | YYYY-MM-DD | 100% | Date the filing was posted. |
| `termination_date` | text | YYYY-MM-DD | 3% | Date the lobbying relationship ended. |
| `filing_url` | text | URL | 100% | Link to the filed disclosure. |
| `attribution_method` *(internal)* | text |  | 100% |  |
| `match_confidence` | text |  | 100% | One of: `high`, `medium`, `withdrawn_org_type` |
| `matched_alias` *(internal)* | text |  | 100% |  |
| `pull_keyword` *(internal)* | text |  | 100% |  |
| `org_type_barred` | integer | constant 1 | 3% | One of: `1` |
| `org_type_reason` | text |  | 3% | One of: `the Salt River Project, an Arizona public power and irrigation district - NOT the Salt River Pima-Maricopa Indian Community`, `a special district`, `a mining company`, `a municipality`, `a university (tribal colleges are ruled separately, by name)`, `a member cooperative` |
| `filing_url_original` | text | URL | 5% | The filing URL exactly as retrieved. Kept because 1,483 filings were captured under `lda.senate.gov`, which published a sunset notice and went dead; `filing_url` was repointed to the live `lda.gov` host, which serves the same filing under the same UUID. This column preserves what was actually retrieved so the rewrite is auditable. |
| `total_lobbying_spend_usd` | integer | USD, nominal | 100% | Amount. |
| `spend_from_client_income_usd` | integer | USD, nominal | 100% | Amount. |
| `spend_from_registrant_expenses_usd` | integer | USD, nominal | 100% | Amount. |
| `n_filings` | integer | integer | 100% | Count. |
| `n_self_filed_filings` | integer | integer | 100% | Count. |
| `n_unique_registrants` | integer | integer | 100% | Count. |
| `top_lobbying_issue_codes` | text | codes | 91% | Most frequent issue-area codes across the entity's filings. |
| `top_government_entities` | text | text | 90% | Chambers and agencies most often lobbied. |

## Value sets

- **`entity_type`** — `Federally recognized tribe`, `Alaska Native Regional Corporation`, `Federally recognized Alaska Native Village`, `Federal-level self-governance consortium`, `State-recognized tribe`, `Federal-level constituency entity`, `State-level constituency entity`
- **`filing_period`** — `first_quarter`, `second_quarter`, `third_quarter`, `fourth_quarter`, `mid_year`, `year_end`
- **`spend_basis`** — `income`, `none_reported`, `expenses`
- **`match_confidence`** — `high`, `medium`, `withdrawn_org_type`
- **`org_type_reason`** — `the Salt River Project, an Arizona public power and irrigation district - NOT the Salt River Pima-Maricopa Indian Community`, `a special district`, `a mining company`, `a municipality`, `a university (tribal colleges are ruled separately, by name)`, `a member cooperative`
