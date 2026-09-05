# Federal Funding to Indian Country: a researcher's guide

Collection `funding` · public file `funding.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Federal financial assistance — grants, cooperative agreements, direct payments and loans — to tribes, tribal organisations and Native-serving entities.

## Population

Federal financial assistance transactions whose recipient Cedar links to a Native entity, together with candidate rows the pipeline could not attribute, which ship with `attributed_flag` = 0 so that the totals a reader builds can be reproduced against Cedar's own (docs/COLUMN_ORDER_NOTE_FOR_THE_TERMINAL_2026-09-05.md). A payment to a tribal government, to an intertribal consortium acting for many tribes, and to a Native-serving non-Native organization are different facts and are kept distinguishable by `business_types_description` and `attribution_method`; a consortium's award is never attributed to each member tribe.

## One row is

One federal assistance transaction (an award action or modification), preserved as such: no aggregation to award-year in this pass.

This pass changes columns, never rows: no aggregation, deduplication, change of publication eligibility or reassignment of Cedar IDs.

**Note:** The owner's list carries recipient_duns (40 columns). The retirement rule in the same addendum says DUNS is used internally to reconcile historical records and is not published; the later rule wins, DUNS is internal_crosswalk, and the file ships 39.

## Key identifiers

`transaction_id` names the transaction and `award_id` the award; `fain` is the official Federal Award Identification Number and `recipient_uei` the recipient's registration. DUNS is used internally to reconcile historical records to the UEI and the Cedar ID and is not published; retired identity schemes appear in no column, value or text.

## Sources and coverage

**Sources:** USAspending assistance transactions; FAADS historical archives for the pre-2008 record.

**Rows in the flagship table as released (recorded 2026-09-04):** 701,955. This is the count the release recorded for `federal_funding_transactions.csv`, not the sum of the collection's 20 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`fiscal_year` is the federal fiscal year (October to September) of `action_date`; `fy_partial_flag` marks rows in a fiscal year the source had not finished reporting when Cedar pulled it, and a partial year must not be compared to a complete one. Recipient geography (`recipient_city`, `recipient_state`, `recipient_county_name`) is where the recipient is registered; place-of-performance geography is where the funded work is performed, and the two are different columns because they are different places.

## Entity relationships

The opening block of every row is `cedar_uid`, `canonical_name`, `entity_class` and `cedar_entity_role`. `cedar_entity_role` is `recipient` on every row: the Native entity is the recipient or the entity that stands behind the recipient, resolved by identifier first and by name only with corroboration (`attribution_method`, `confidence_tier`). The recipient's own name stays in `recipient_name`; the register's name is `canonical_name`. Where `attributed_flag` is 0 the opening block is blank: the row is a candidate Cedar could not attribute, not a non-Native recipient.

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

USAspending re-reports awards; a transaction can appear with corrected values in a later archive. Cedar rebuilds from the current archive and states the archive's date in the release; it does not stack archives. Apparent duplicate transactions are retained on purpose: they are distinct modifications to one award that agree on every published field, and removing them would have destroyed $8.29B of real obligations (collection descriptor, measured 2026-09-02).

## Field dictionary

The approved header, in the owner's exact order (39 columns, of which 1 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros; a JSON array cell is one list, aligned with its neighbours where the dictionary says so.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. | text | the source states none, or not applicable to this row |
| 3 | `entity_class` | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. | text | the source states none, or not applicable to this row |
| 4 | `cedar_entity_role` | Entity role | Why the entity is on this row: recipient. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 5 | `transaction_id` (was `assistance_transaction_unique_key`) | Transaction ID | USAspending's unique key for this transaction. Cite it to find the exact record. | identifier, as text | the source states none, or not applicable to this row |
| 6 | `award_id` (was `assistance_award_unique_key`) | Award ID | USAspending's key for the whole award; the source link is built from it. | identifier, as text | the source states none, or not applicable to this row |
| 7 | `fain` (was `award_id_fain`) | Award number | The award's Federal Award Identification Number; several transactions can share one. | text | the source states none, or not applicable to this row |
| 8 | `action_date` | Action date | The date the agency took this action. | date (YYYY-MM-DD) | the source states no date |
| 9 | `fiscal_year` | Fiscal year | The federal fiscal year of the action (October to September), which is what USAspending reports and what the year filter uses. | year | the source states no date |
| 10 | `fy_partial_flag` | Partial fiscal year | Whether this row falls in a fiscal year the source had not finished reporting when Cedar pulled it (yes or no). Do not compare a partial year to a complete one. | yes or no (1 or 0) | not stated; 0 is no |
| 11 | `recipient_name` | Recipient as recorded | The recipient's name as the award records it, before Cedar resolved it to the entity. | text | the source states none, or not applicable to this row |
| 12 | `recipient_uei` | Recipient UEI | The recipient's federal Unique Entity ID. | identifier, as text | the source states none, or not applicable to this row |
| 13 | `recipient_type` | recipient type | One readable recipient type from the source-code dictionary, after the conflict check. | — | owed: not in the file until the terminal builds it |
| 14 | `assistance_type_code` (was `assistance_type`) | Assistance type code | The source's code for the assistance type (grant, loan, direct payment, insurance), defined in the dictionary; the readable type is beside it. | number | the source states none, or not applicable to this row |
| 15 | `assistance_type` (was `assistance_type_description`) | Assistance type | What kind of assistance it is: formula grant, project grant, direct payment, loan, insurance. | text | the source states none, or not applicable to this row |
| 16 | `program_code` (was `cfda`) | Program number | The Assistance Listing (CFDA) number of the federal program. | number | the source states none, or not applicable to this row |
| 17 | `program_name` (was `cfda_title`) | Program | The federal program's name. | text | the source states none, or not applicable to this row |
| 18 | `awarding_agency` (was `awarding_agency_name`) | Agency | The department that made the award. | text | the source states none, or not applicable to this row |
| 19 | `awarding_subagency` (was `awarding_sub_agency_name`) | Office | The office within the department. | text | the source states none, or not applicable to this row |
| 20 | `obligations_usd` (was `obligated_usd`) | Amount obligated | Dollars obligated by this transaction. Negative values are de-obligations, kept as recorded. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 21 | `obligations_usd_real2025` (was `obligated_usd_real2025`) | Amount in 2025 dollars | The same amount adjusted for inflation to 2025 dollars. | number | the source states none, or not applicable to this row |
| 22 | `loan_face_value_usd` (was `face_value_of_loan`) | Loan face value | For loans, the face value of this loan; zero for grants. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 23 | `loan_subsidy_cost_usd` (was `original_loan_subsidy_cost`) | Original loan subsidy cost | For a loan, the government's estimated cost of the subsidy when it was made. A loan measure; never added to obligations. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 24 | `total_loan_face_value_usd` (was `total_face_value_of_loan`) | Award loan face value | For loans, the face value of the whole award to date. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 25 | `total_loan_subsidy_cost_usd` (was `total_loan_subsidy_cost`) | Total loan subsidy cost | The subsidy cost across the award's loan actions. Never added to obligations. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 26 | `recipient_city` (was `recipient_city_name`) | Recipient city | City of the recipient's address on the award. | text | the source states none, or not applicable to this row |
| 27 | `recipient_state` (was `recipient_state_code`) | Recipient state | State of the recipient's address on the award. | text | the source states none, or not applicable to this row |
| 28 | `recipient_county` (was `geo_recipient_county_name`) | Recipient county | The county of the recipient's address, which is not necessarily where the funded work happens. | text | the source states none, or not applicable to this row |
| 29 | `recipient_county_fips` (was `geo_recipient_county_fips`) | Recipient county FIPS | The county code of the recipient's address. | text | the source states none, or not applicable to this row |
| 30 | `performance_county` (was `geo_pop_county_name`) | Place of performance county | The county where the funded work is performed, as the award reports it. | text | the source states none, or not applicable to this row |
| 31 | `performance_county_fips` (was `geo_pop_county_fips`) | Place of performance county FIPS | The county code where the funded work is performed, as the award reports it. | text | the source states none, or not applicable to this row |
| 32 | `recipient_geography_status` | Recipient geography status | Whether the recipient's address was placed in a county: placed, placed with an ambiguous place name, or unplaced. | text | the source states none, or not applicable to this row |
| 33 | `performance_geography_status` | Performance geography status | The same for the place of performance. | text | the source states none, or not applicable to this row |
| 34 | `attributed_flag` | Attributed to the entity | Whether Cedar attributes this transaction to the Native entity (yes) or keeps it in the file unattributed (no). Cedar's totals count attributed rows only. | yes or no (1 or 0) | not stated; 0 is no |
| 35 | `attribution_status` | Attribution status | How the attribution stands: attributed through the register, unattributed, or under review. | text | the source states none, or not applicable to this row |
| 36 | `source_system` | Source system | Which source the record came from. | text | the source states none, or not applicable to this row |
| 37 | `source_vintage` | Source vintage | The date stamp of the archive the row was taken from. | text | the source states none, or not applicable to this row |
| 38 | `source_url` | Source | The official page for this record, written into the file so it cites itself. | web address | the source states none, or not applicable to this row |
| 39 | `research_note` | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. | text | the source states none, or not applicable to this row |

Until the combined columns exist, the file carries their sources, each with its own label:

- `business_types_code` (Business types code) combines into `recipient_type`: One of three overlapping recipient-type fields, consolidated through the source-code dictionary with conflict checks.
- `business_types_description` (Recipient type as recorded) combines into `recipient_type`: How USAspending classifies the recipient (for example, federally recognized tribal government).
- `business_types_description_normalized` (Business types description normalized) combines into `recipient_type`: The normalized spelling, the third of the three.

## Missing values

A blank is never zero and never an invented date. Beyond the column-level rules above:

- A blank `cedar_uid` with `attributed_flag` = 0 means unattributed, not non-Native.
- A blank loan column on a grant row means not applicable; on a loan row it means the source did not report it.
- A blank `recipient_county_name` means the address could not be placed in one county with confidence; the city and state still ship.

## Limitations

- Two source families cover the years: the USAspending archive (FY2007 onward) and the historical FAADS files (FY2001 to FY2007). They both hold FY2007, and 98.9% of the modern table's FY2007 dollars sit on awards the archive table also carries (docs/MONEY_TOTALLING_RULES.md, the FY2007 seam). `source_system` says which family a row is from; never stack the two families for one year.
- Coverage begins where the source does. An award that is not in the file, or a blank amount, is not evidence that no funding reached the entity.
- Loan measures (face value, subsidy cost) describe credit instruments and are not obligations; `credit_instrument_flag` marks the rows they belong to.
- This pass changes columns, never rows: the row stays the transaction. The annual product the earlier brief mentioned was withdrawn by the owner's column specification.

## Suitable analyses

- Obligations by fiscal year, program (`program_code`), agency or entity, counting `attributed_flag` = 1 rows and excluding partial fiscal years, or stating them.
- Which programs reach which entities, and first and last action dates per award.
- Constant-dollar comparisons across years using `obligations_usd_real2025` (base year 2025; the deflator is stated in the release, not on the row).

## Unsafe aggregations

- Summing `obligations_usd` across both source families for FY2007, or stacking the FAADS and USAspending files for a multi-year series without the seam rule above.
- Adding loan face values or subsidy costs to obligations, or to each other.
- Attributing a consortium's or a Native-serving organization's award to a member tribe.
- Treating a partial fiscal year (`fy_partial_flag` = 1) as a complete one in a year-on-year comparison.
- Joining this table to another collection on `cedar_uid` alone and summing: one entity has many transactions, and the join multiplies rows. Aggregate to the entity-year here first.

## What is still owed

Identifier retirement findings that stop this dataset until they are settled (see `docs/IDENTIFIER_RETIREMENT_2026-09-05.md`):

- `attribution_status`: how the row was attributed, in a vocabulary naming the retired scheme (retired_scheme).

Target columns the specification asks for that the terminal has not yet built from the full table. Each is absent until it exists, never blank.

- `recipient_type` (combine:business_types_code\|business_types_description\|business_types_description_normalized): One readable recipient type from the source-code dictionary, after the conflict check.

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Federal Funding to Indian Country" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** Recipients are matched to the entity layer and the basis for inclusion is carried on the row, so a payment to a tribal government, to an intertribal consortium acting for many tribes, and to a Native-serving non-Native organisation are distinguishable. Apparent duplicate transactions are retained: they are usually distinct modifications to one award that agree on every published field, and removing them would have destroyed $8.29B of real obligations.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

