# Codebook — Nonprofit

*21,271 rows across 2 file(s). Generated 2026-08-07.*

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `EIN` *(subscriber)* | integer | code | 100% | Employer Identification Number, the IRS taxpayer identifier. |
| `entity_id` | text | code | 0% | Identifier. |
| `org_name` | text | text | 100% | Name. |
| `classification_ruling` | text |  | 100% | One of: `UNRULED`, `place_name_coincidence`, `native_controlled`, `tribally_controlled`, `native_serving` |
| `evidence` *(internal)* | text |  | 100% |  |
| `tier` | text |  | 100% | One of: `990_N`, `full_990`, `not_required_to_file`, `990_EZ`, `UNKNOWN` |
| `tier_basis` *(internal)* | text |  | 100% |  |
| `state` | text | 2-letter code | 100% | US state or territory. |
| `city` | text | text | 100% | City. |
| `ntee_code` | text | code | 72% | National Taxonomy of Exempt Entities code describing the organisation's field of activity. |
| `confidence_tier` | text | category | 100% | Publication tier. A = verified, publishable. B = provisional, withheld from published extracts. C = unattributed. X = ruled out. |
| `funnel_stage` *(internal)* | text |  | 100% | One of: `raw_name_candidate`, `excluded_by_prior_ruling`, `canonical_name_match`, `verified_strict`, `ruled_not_native`, `state_validated`, `ruled_native_needs_elijah`, `ruled_native_verified` |
| `review_flag` *(internal)* | text | 0/1 | 14% | Indicator variable. |
| `review_flag_token` *(internal)* | text |  | 14% |  |
| `excluded_by_prior_ruling` | integer | 0 to 1 | 100% | One of: `0`, `1` |
| `exclusion_reason` | text | text | 39% | Why a record was ruled outside the Native universe. |
| `tribe_id_token_match` *(internal)* | text |  | 59% |  |
| `canonical_name_token_match` *(internal)* | text |  | 59% |  |
| `n_coders_agree` | integer | integer | 45% | Count. |
| `bmf_in_snapshot` | integer | constant 1 | 100% | One of: `1` |
| `bmf_status` | integer | 1 to 25 | 100% | One of: `01`, `12`, `02`, `25` |
| `bmf_subsection` | integer | code | 100% | Internal Revenue Code subsection granting exemption. |
| `bmf_filing_req_cd` | integer | 0 to 14 | 100% | One of: `02`, `01`, `06`, `00`, `14`, `13`, `07`, `03` |
| `bmf_foundation_cd` | integer | code | 100% | Foundation classification code. |
| `bmf_irs_ruling_yyyymm` | integer | YYYYMM | 100% | Month the IRS exemption ruling was issued. |
| `bmf_tax_period` | integer | YYYYMM | 82% | Accounting period recorded in the IRS master file. |
| `bmf_revenue_amt` | integer | USD, nominal | 78% | Revenue recorded in the IRS master file. |
| `bmf_asset_amt` | integer | USD, nominal | 81% | Assets recorded in the IRS master file. |
| `bmf_income_amt` | integer | USD, nominal | 81% | Income recorded in the IRS master file. |
| `source_files` *(internal)* | text |  | 100% |  |
| `source_dataset` *(internal)* | text |  | 100% | One of: `IRS Exempt Organizations Business Master File (eo1-eo4)`, `ProPublica Nonprofit Explorer API v2` |
| `source_url` | text | URL | 100% | Link to the record's published source. |
| `bmf_vintage_fetched` | text |  | 100% | One of: `2026-04-29` |
| `built_date` | text | YYYY-MM-DD | 100% | Date. |
| `placename_risk_flag` | text | 0/1 | 29% | Indicator variable. |
| `ruling_authority` *(internal)* | text |  | 3% | One of: `agent_research` |
| `ruling_confidence` | text |  | 3% | One of: `medium`, `high`, `low`, `unstated` |
| `ruling_date` | text | YYYY-MM-DD | 3% | Date. |
| `tribe_id` | text | code | 11% | Cedar Press permanent identifier for the Native entity. Stable across releases; use this to join datasets. |
| `tribe_canonical_name` | text | text | 11% | Name. |
| `entity_match_method` *(internal)* | text |  | 11% | One of: `containment`, `exact`, `core`, `alias` |
| `entity_tier` | text |  | 50% | One of: `X`, `B`, `A` |
| `entity_match_basis` *(internal)* | text |  | 100% |  |
| `entity_keyed_date` | text | YYYY-MM-DD | 100% | Date. |
| `ein` *(subscriber)* | integer | code | 100% | Employer Identification Number, the IRS taxpayer identifier. |
| `tax_year` | integer | YYYY | 100% | Tax year covered by the return. |
| `form_type` | text | category | 100% | Annual return filed: full return, short form, or electronic postcard. |
| `total_revenue` | integer | USD, nominal | 60% | Total revenue reported on the organisation's annual information return. |
| `total_expenses` | integer | USD, nominal | 60% | Total expenses reported. |
| `total_assets` | integer | USD, nominal | 60% | Total assets at period end. |
| `total_liabilities` | integer | USD, nominal | 60% | Total liabilities at period end. |
| `program_service_revenue` | integer | USD, nominal | 57% | Revenue from programme services. |
| `contributions_grants` | integer | USD, nominal | 60% | Revenue from contributions and grants. |
| `lobbying_expenditure` | empty | USD, nominal | 0% | Lobbying expenditure reported on the return. |
| `n_employees` | empty | integer | 0% | Count. |
| `pdf_url` | text | URL | 93% | Link to the document as filed. |
| `retrieved_date` | text | YYYY-MM-DD | 100% | Date. |
| `tax_period` | integer | YYYYMM | 100% | Accounting period of the return. |
| `form_type_raw` | text | text | 40% | Return type exactly as reported. |
| `has_financial_data` | integer | 0 to 1 | 100% | One of: `1`, `0` |
| `pre_2000_flag` | integer | 0/1 | 100% | 1 when the record predates the 2000 coverage floor. Such records are retained but fall outside the standard reporting window. |
| `lobbying_indicator_990pf` | text |  | 3% | One of: `N` |
| `propaganda_indicator_990pf` | text |  | 3% | One of: `N` |
| `lobbying_field_basis` *(internal)* | text |  | 100% | One of: `not_exposed_by_api`, `990pf_infleg_indicator_only` |
| `n_employees_basis` *(internal)* | text | integer | 100% | Count. |
| `net_assets_end` | integer | USD, nominal | 57% | Net assets at period end. |
| `officer_compensation` | integer | USD, nominal | 41% | Compensation paid to officers. |
| `bmf_990_tier` | text |  | 100% | One of: `full_990`, `990_N`, `990_EZ`, `not_required_to_file` |
| `in_tier_a` | integer | 0 to 1 | 100% | One of: `1`, `0` |
| `in_recheck_candidate` | integer | 0 to 1 | 100% | One of: `0`, `1` |
| `in_placename_risk` | integer | 0 to 1 | 100% | One of: `0`, `1` |
| `filing_updated` | text | YYYY-MM-DD | 60% | When the filing record was last revised. |
| `filing_regime` | text |  | 100% | One of: `990_or_990EZ`, `990_N`, `not_required`, `990_PF` |
| `schedc_expected` | integer | 0 to 1 | 100% | One of: `1`, `0` |
| `schedc_basis` *(internal)* | text |  | 100% | One of: `outside_efile_index_coverage_submission_years_2017_2026`, `irs_efile_xml_no_schedule_c_filed`, `990N_filer_no_schedule_exists`, `no_efile_return_indexed_for_period`, `bmf_filing_not_required`, `efile_return_indexed_not_retrieved`, `irs_efile_xml_schedule_c` |
| `schedc_source_url` | text | URL | 26% | Link. |
| `schedc_object_id` | integer | code | 26% | Identifier. |
| `schedc_present` | integer | 0 to 1 | 26% | One of: `0`, `1` |
| `schedc_501h_election` | integer | 0 to 1 | 1% | One of: `0`, `1` |
| `schedc_501h_basis` *(internal)* | text |  | 1% | One of: `not determinable from this return`, `derived: Schedule C Part II-B completed, the non-electing regime`, `derived: Schedule C Part II-A completed, which only a 501(h) electing filer does` |
| `schedc_total_lobbying` | integer | USD | 0% | Total lobbying expenditure the organisation reports on Schedule C Part II-A, the regime for a filer that has made the 501(h) election. Grassroots plus direct. |
| `schedc_direct_lobbying` | integer | 793 to 15000 | 0% | One of: `2500`, `4291`, `793`, `15000`, `2000`, `2727`, `7500`, `10545` |
| `schedc_grassroots_lobbying` | integer | 1915 to 27532 | 0% | One of: `1915`, `27532` |
| `schedc_nonelecting_total` | integer | USD | 0% | Total lobbying expenditure reported on Schedule C Part II-B, the regime for a filer that has NOT made the 501(h) election. Never added to the Part II-A total: the two are alternative regimes, not components. |
| `schedc_lobbying_nontaxable` | integer | USD | 0% | The lobbying nontaxable amount: the ceiling on total lobbying expenditure a 501(h) electing filer may incur without tax, computed from exempt purpose expenditures. |
| `schedc_grassroots_nontaxable` | integer | USD | 0% | The grassroots nontaxable amount: the separate, lower ceiling that applies to grassroots lobbying alone under the 501(h) election. |
| `schedc_exempt_purpose_expend` | integer | USD | 0% | Total exempt purpose expenditures, the base the 501(h) lobbying ceilings are computed from. |
| `schedc_political_expenditure` | integer | 1000 to 118725 | 0% | One of: `1000`, `35000`, `11500`, `6000`, `3350`, `110350`, `118725` |
| `schedc_527_amount` | integer | USD, nominal | 0% | Amount. |
| `schedc_dues_lobbying_political` | empty | USD | 0% | The portion of members' dues the organisation reports on Schedule C Part III as non-deductible because it is allocable to lobbying and political expenditure. |
| `schedc_dues_received` | integer | constant 187887 | 0% | One of: `187887` |
| `schedc_used_volunteers` | integer | constant 0 | 0% | One of: `0` |
| `schedc_used_paid_staff` | integer | constant 0 | 0% | One of: `0` |
| `schedc_used_media` | integer | constant 0 | 0% | One of: `0` |
| `schedc_used_mailings` | integer | constant 0 | 0% | One of: `0` |
| `schedc_used_publications` | integer | constant 0 | 0% | One of: `0` |
| `schedc_used_grants` | integer | 0 to 1 | 0% | One of: `0`, `1` |
| `schedc_used_direct_contact` | integer | 0 to 1 | 0% | One of: `0`, `1` |
| `schedc_used_rallies` | integer | constant 0 | 0% | One of: `0` |
| `schedc_used_other` | integer | 0 to 1 | 0% | One of: `0`, `1` |
| `form990_lobbying_activities_ind` | integer | 0 to 1 | 22% | One of: `0`, `1` |
| `form990_political_activity_ind` | integer | 0 to 1 | 25% | One of: `0`, `1` |
| `form990_part9_lobbying_fees` | integer | USD | 5% | Fees paid to OUTSIDE lobbyists, Form 990 Part IX line 11d. A different measurement from Schedule C, which counts the organisation's own lobbying expenditure, and never added to it. |
| `form990pf_influence_legislation_ind` | empty | 1/0 | 0% | Form 990-PF trigger question: whether the private foundation spent anything to influence legislation during the year. |
| `form990pf_legislative_political_ind` | empty | 1/0 | 0% | Form 990-PF trigger question: whether the private foundation engaged in legislative or political activity during the year. |
| `schedc_lobbying_usd` | integer | USD, nominal | 1% | Amount. |
| `schedc_lobbying_basis` *(internal)* | text |  | 51% | One of: `no_schedule_c_filed_with_return`, `990N_no_financial_detail_filed`, `no_filing_requirement`, `schedule_c_filed_no_expenditure_reported`, `schedc_part2b_nonelecting_total`, `schedc_part2a_501h_electing_total`, `schedc_part2a_reported_zero` |
| `schedc_built_date` | text | YYYY-MM-DD | 100% | Date. |

## Value sets

- **`classification_ruling`** — `UNRULED`, `place_name_coincidence`, `native_controlled`, `tribally_controlled`, `native_serving`
- **`tier`** — `990_N`, `full_990`, `not_required_to_file`, `990_EZ`, `UNKNOWN`
- **`confidence_tier`** — `A`, `B`, `X`
- **`exclusion_reason`** — `ambiguous_place_token_no_tribal_purpose`, `place_name_false_positive`, `Agent-researched 2026-08-05: place-name coincidence`
- **`placename_risk_flag`** — `REVIEW`, `HIGH`
- **`ruling_confidence`** — `medium`, `high`, `low`, `unstated`
- **`entity_tier`** — `X`, `B`, `A`
- **`form_type`** — `990`, `990EZ`, `990PF`
- **`form_type_raw`** — `990`, `990EZ`, `990O`, `990EO`, `990PF`, `990ER`, `990R`, `990PR`, `990OR`, `990EOR`
- **`bmf_990_tier`** — `full_990`, `990_N`, `990_EZ`, `not_required_to_file`
- **`filing_regime`** — `990_or_990EZ`, `990_N`, `not_required`, `990_PF`
