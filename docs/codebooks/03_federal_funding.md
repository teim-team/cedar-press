# Codebook — Federal Funding

*3,477,199 rows across 3 file(s). Generated 2026-08-07; **retired columns corrected 2026-09-02** by `code/941_refresh_codebook_fragment.py`.*

> **CORRECTION 2026-09-02.** `tribe_id` and `tribe_id_scheme` were removed
> from `federal_funding_transactions.csv` and the tribe-year panel on
> 2026-09-01 by `code/843_retire_cicd_scheme.py`, and
> `tribe_id_scheme_resolved` / `_resolved_basis` became `attribution_status`
> / `attribution_basis`. This codebook still listed both retired columns, and
> stated `tribe_id_neid` — Cedar's own handle — as type `empty`, 0% filled,
> when it is filled on 552,602 rows. Both fixed. **38 live columns are still
> undocumented here**, including every `geo_*` key added 2026-09-02; run
> `py -3 code/941_refresh_codebook_fragment.py drift` for the list. They are
> left blank rather than invented.

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `assistance_transaction_unique_key` *(subscriber)* | text | code | 100% | Stable key for the individual transaction. |
| `assistance_award_unique_key` *(subscriber)* | text | code | 100% | Stable key for the award. |
| `award_id_fain` *(subscriber)* | text | code | 100% | Federal Award Identification Number. |
| `action_date` | text | YYYY-MM-DD | 100% | Date of the transaction. |
| `fiscal_year` | integer | YYYY | 100% | Federal fiscal year (October-September). |
| `fy_partial_flag` | integer | 0/1 | 100% | Indicator variable. |
| `obligated_usd` | integer | USD, nominal | 100% | Obligated amount on the assistance transaction. |
| `assistance_type` | integer | code | 100% | Assistance instrument code. |
| `assistance_type_description` | text | category | 7% | Assistance instrument type, such as formula grant or cooperative agreement. |
| `cfda` | text | code | 100% | Assistance Listing (CFDA) number of the programme. |
| `cfda_title` | text | text | 100% | Assistance Listing programme name. |
| `awarding_agency_name` | text | text | 100% | Name. |
| `awarding_sub_agency_name` | text | text | 100% | Name. |
| `recipient_uei` *(subscriber)* | text | code | 32% | UEI of the recipient. |
| `recipient_duns` *(internal)* | text | code | 33% | Legacy DUNS number. Retired federally in 2022 and retained only for older records. |
| `recipient_name` | text | text | 100% | Recipient name as reported. |
| `recipient_city_name` | text | text | 100% | Name. |
| `recipient_state_code` | text | 2-letter code | 100% | Recipient state. |
| `canonical_name` | text | text | 16% | Cedar Press standard name for the Native entity. |
| `tribe_id_neid` | text | code | 16% | Cedar Press entity handle (NEID form) for the Native entity this row is attributed to. Blank where the row is unattributed. |
| `cedar_uid` | text | code | 16% | Cedar Press permanent identifier for the Native entity. Stable across releases and across renames; use this to join datasets. |
| `attribution_status` | text | category | 20% | Whether this row is attributed to a Native entity, unattributed, or explicitly ruled not Native. One of: `cedar_neid`, `unattributed`, `excluded_not_native`, `unresolved_native`. Renamed 2026-09-01 from `tribe_id_scheme_resolved`; the field is unchanged. |
| `attribution_method` *(internal)* | text |  | 100% | One of: `dofile_corrtd:prefix`, `unattributed`, `not_evaluated:ak_scope_line9`, `dofile_corrtd:exact`, `dofile_corrtd:prefix+city`, `dofile_corrtd:prefix (MR-2 Oneida 204=NY)`, `dofile_corrtd:exact (MR-2 Oneida 204=NY)` |
| `attribution_source_line` *(internal)* | text |  | 77% |  |
| `attribution_rule` *(internal)* | text |  | 77% |  |
| `exclusion_reason` | text | text | 0% | Why a record was ruled outside the Native universe. |
| `exclusion_source_line` *(internal)* | integer | 21 to 2405 | 11% |  |
| `exclusion_rule` *(internal)* | text |  | 11% |  |
| `ak_flag` | integer | 0/1 | 100% | Indicator variable. |
| `excluded_flag` | integer | 0/1 | 100% | Indicator variable. |
| `attributed_flag` | integer | 0/1 | 100% | Indicator variable. |
| `confidence_tier` | text | category | 100% | Publication tier. A = verified, publishable. B = provisional, withheld from published extracts. C = unattributed. X = ruled out. |
| `total_obligated_usd` | numeric | USD, nominal | 100% | Amount. |
| `obl_type_02_block_grant` | integer | USD, nominal | 100% | Obligations under this assistance instrument type. |
| `obl_type_03_formula_grant` | numeric | USD, nominal | 100% | Obligations under this assistance instrument type. |
| `obl_type_04_project_grant` | numeric | USD, nominal | 100% | Obligations under this assistance instrument type. |
| `obl_type_05_cooperative_agreement` | numeric | USD, nominal | 100% | Obligations under this assistance instrument type. |
| `obl_type_06_direct_payment_specified_use` | numeric | USD, nominal | 100% | Obligations under this assistance instrument type. |
| `obl_type_10_direct_payment_unrestricted` | numeric | USD, nominal | 100% | Obligations under this assistance instrument type. |
| `obl_type_11_other_reimbursable_or_indirect` | integer | USD, nominal | 100% | Obligations under this assistance instrument type. |
| `n_transactions` | integer | integer | 100% | Count. |
| `n_recipients` | integer | integer | 100% | Count. |
| `cfda_program` | text | text | 100% | Assistance Listing programme name. |
| `agency` | text | text | 100% | Awarding agency. |
| `recipient_type` | text | code | 100% | Recipient organisation type code. |
| `recipient_city` | text | text | 89% | Recipient city. |
| `recipient_state` | text | 2-letter code | 100% | Recipient state. |
| `recipient_zip` | integer | text | 86% | Recipient postal code. |
| `source_url` | text | URL | 100% | Link to the record's published source. |
| `fetched_date` | text | YYYY-MM-DD | 100% | Date. |
| `recipient_type_description` | text | category | 100% | Recipient organisation type. |
| `awarding_sub_agency` | text | text | 100% | Awarding sub-agency or bureau. |
| `record_type` | integer | 1 to 3 | 100% | One of: `2`, `1`, `3` |
| `api_endpoint` | text |  | 100% | One of: `https://api.usaspending.gov/api/v2/bulk_download/awards/` |
| `source_file` *(internal)* | text |  | 100% |  |

## Value sets

- **`assistance_type_description`** — `DIRECT PAYMENT FOR SPECIFIED USE, AS A SUBSIDY OR OTHER NON-REIMBURSABLE DIRECT FINANCIAL AID (C)`, `PROJECT GRANT (B)`, `FORMULA GRANT (A)`, `BLOCK GRANT (A)`, `COOPERATIVE AGREEMENT (B)`, `DIRECT PAYMENT WITH UNRESTRICTED USE (RETIREMENT, PENSION, VETERANS BENEFITS, ETC.) (D)`, `OTHER REIMBURSABLE, CONTINGENT, INTANGIBLE, OR INDIRECT FINANCIAL ASSISTANCE`, `PROJECT GRANT`, `NOT SPECIFIED`, `DIRECT PAYMENT FOR SPECIFIED USE`, `FORMULA GRANT`, `COOPERATIVE AGREEMENT`, `BLOCK GRANT`, `OTHER FINANCIAL ASSISTANCE`, `DIRECT PAYMENT WITH UNRESTRICTED USE`, `DIRECT LOAN (E)`
- **`exclusion_reason`** — `I'm unsure about this hospital as it is not a tribal org but it serves ony Navajo`, `navajo agricultural projects industry (napi) is owned by navajo nation;`, `I'm unsure about zuni housing authority but I'll drop it`, `rocky boy schools and chippewa cree tribe/health care are not flagged because they are affiliated with the tribe`, `this is a tribal college that appears to serve Native Americans from multiple tribes`, `santa clara day school is owned by the tribe`, `Alaska's tribal college`, `not sure about this one, couldn't find much`, `I'm not 100% sure about this one`, `burt lake band of ottawa & chippewa indians got federal recognition around 2022-2023, but they are not in our roaster of federally recognized tribes`, `they are a state-recognized tribe`, `can't find this organization at all`, `tohono o'odham farming authority is tribally owned`, `acoma cattle growers association appears separate from the tribe`, `I'm unsure about turtle mountain public utilities comm but I'll keep it`, `this enterprise appears to have no connection to the tribe`, `this district is entirely or almost entirely on the Rosebud reservation`, `Koi nation lives on lower lake rancheria`, `laguna rainbow corp appears to be a tribe entity`, `primary place of performance is in FL but the city doesn't match at all`
- **`confidence_tier`** — `A`, `C`, `X`
- **`agency`** — `Department of Education`, `Department of Transportation`, `Department of Agriculture`, `Department of Health and Human Services`, `Department of Housing and Urban Development`, `Department of Justice`, `Department of the Interior`, `Environmental Protection Agency`, `Department of Energy`, `Department of Commerce`, `Department of Labor`
- **`recipient_type`** — `A`, `P`, `H`, `Q`, `O`, `C`, `M`, `D`, `X`, `G`, `B`, `R`, `I`, `07`, `T`
- **`recipient_type_description`** — `STATE GOVERNMENT`, `INDIVIDUAL`, `PUBLIC/STATE CONTROLLED INSTITUTION OF HIGHER EDUCATION`, `FOR-PROFIT ORGANIZATION (OTHER THAN SMALL BUSINESS)`, `PRIVATE INSTITUTION OF HIGHER EDUCATION`, `CITY OR TOWNSHIP GOVERNMENT`, `NONPROFIT WITH 501C3 IRS STATUS (OTHER THEN INSTITUTION OF HIGHER EDUCATION)`, `SPECIAL DISTRICT GOVERNMENT`, `OTHER`, `INDEPENDENT SCHOOL DISTRICT`, `COUNTY GOVERNMENT`, `SMALL BUSINESS`, `INDIAN/NATIVE AMERICANTRIBAL GOVERNMENT (FEDERALLY RECOGNIZED)`, `NONPROFIT WITH 501C3 IRS STATUS (OTHER THAN AN INSTITUTION OF HIGHER EDUCATION)`, `HISTORICALLY BLACK COLLEGE OR UNIVERSITY (HBCU)`
