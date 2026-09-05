# Federal Funding to Indian Country: a researcher's guide

Collection `funding` · public file `funding.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Federal financial assistance — grants, cooperative agreements, direct payments and loans — to tribes, tribal organisations and Native-serving entities.

## Population

Federal financial assistance transactions whose recipient Cedar links to a Native entity, together with candidate rows the pipeline could not attribute, which ship with `attributed_flag` = 0 so that the totals a reader builds can be reproduced against Cedar's own (docs/COLUMN_ORDER_NOTE_FOR_THE_TERMINAL_2026-09-05.md). A payment to a tribal government, to an intertribal consortium acting for many tribes, and to a Native-serving non-Native organization are different facts and are kept distinguishable by `business_types_description` and `attribution_method`; a consortium's award is never attributed to each member tribe.

## One row is

**Today:** One federal assistance transaction (an award action or modification) on USAspending or in the FAADS archive, linked to the Native entity that received it.

**When the specification is applied:** One transaction, as today, until the terminal measures whether stable award identity and compatible transaction measures support the award-recipient-fiscal-year product the specification asks for; where they do, that becomes the public grain and the transactions stay internal.

**Grain change:** Owed (§4): an award-recipient-fiscal-year product built by summing verified transaction-level obligations within award and year, negatives kept, loan face values and subsidy costs never added to obligations; historical FAADS rows that cannot support award identity ship under an explicit record_type with their own counting rule. Not attempted here: it needs the full table and the FAADS/USAspending seam measured (docs/schema/faads_fy2007_seam.json).

## Key identifiers

`assistance_award_unique_key` names the award and `assistance_transaction_unique_key` the transaction within it; `award_id_fain` is the official Federal Award Identification Number and `recipient_uei` the recipient's registration. Retired identifier schemes are not in the file, its text or its values, and must not be reconstructed from it.

## Sources and coverage

**Sources:** USAspending assistance transactions; FAADS historical archives for the pre-2008 record.

**Rows in the flagship table as released (recorded 2026-09-04):** 701,955. This is the count the release recorded for `federal_funding_transactions.csv`, not the sum of the collection's 20 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`fiscal_year` is the federal fiscal year (October to September) of `action_date`; `fy_partial_flag` marks rows in a fiscal year the source had not finished reporting when Cedar pulled it, and a partial year must not be compared to a complete one. Recipient geography (`recipient_city_name`, `recipient_state_code`, `recipient_county_name`) is where the recipient is registered; place-of-performance geography is where the funded work is performed, and the two are different columns because they are different places.

## Entity relationships

The opening block of every row is `cedar_uid`, `cedar_entity_name`, `cedar_entity_type` and `cedar_entity_role`. `cedar_entity_role` is `recipient` on every row: the Native entity is the recipient or the entity that stands behind the recipient, resolved by identifier first and by name only with corroboration (`attribution_method`, `confidence_tier`). The recipient's own name stays in `recipient_name`; the register's name is `cedar_entity_name`. Where `attributed_flag` is 0 the opening block is blank: the row is a candidate Cedar could not attribute, not a non-Native recipient.

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

USAspending re-reports awards; a transaction can appear with corrected values in a later archive. Cedar rebuilds from the current archive and states the archive's date in the release; it does not stack archives. Apparent duplicate transactions are retained on purpose: they are distinct modifications to one award that agree on every published field, and removing them would have destroyed $8.29B of real obligations (collection descriptor, measured 2026-09-02).

## Field dictionary

The approved header, in order (41 columns, of which 4 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `cedar_entity_name` (was `canonical_name`) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 3 | `cedar_entity_type` | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 4 | `cedar_entity_role` | Entity role | Why the entity is on this row: recipient. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 5 | `assistance_award_unique_key` | Award ID | USAspending's key for the whole award; the source link is built from it. | identifier, as text | the source states none, or not applicable to this row |
| 6 | `award_id_fain` | Award number | The award's Federal Award Identification Number; several transactions can share one. | text | the source states none, or not applicable to this row |
| 7 | `assistance_transaction_unique_key` | Transaction ID | USAspending's unique key for this transaction. Cite it to find the exact record. | identifier, as text | the source states none, or not applicable to this row |
| 8 | `record_type` | record type | award_year or source_record, for historical rows that cannot support award identity. | — | owed: not in the file until the terminal builds it |
| 9 | `recipient_name` | Recipient as recorded | The recipient's name as the award records it, before Cedar resolved it to the entity. | text | the source states none, or not applicable to this row |
| 10 | `recipient_uei` | Recipient UEI | The recipient's federal Unique Entity ID. | identifier, as text | the source states none, or not applicable to this row |
| 11 | `assistance_type_description` | Assistance type | What kind of assistance it is: formula grant, project grant, direct payment, loan, insurance. | text | the source states none, or not applicable to this row |
| 12 | `credit_instrument_flag` | Loan or guarantee (yes or no) | Whether this row is a loan or loan guarantee, so the loan columns are read for the rows they belong to. | yes or no (1 or 0) | not stated; 0 is no |
| 13 | `awarding_agency_name` | Agency | The department that made the award. | text | the source states none, or not applicable to this row |
| 14 | `awarding_sub_agency_name` | Office | The office within the department. | text | the source states none, or not applicable to this row |
| 15 | `cfda` | Program number | The Assistance Listing (CFDA) number of the federal program. | number | the source states none, or not applicable to this row |
| 16 | `cfda_title` | Program | The federal program's name. | text | the source states none, or not applicable to this row |
| 17 | `fiscal_year` | Fiscal year | The federal fiscal year of the action (October to September), which is what USAspending reports and what the year filter uses. | year | the source states no date |
| 18 | `fy_partial_flag` | Partial fiscal year | Whether this row falls in a fiscal year the source had not finished reporting when Cedar pulled it (yes or no). Do not compare a partial year to a complete one. | yes or no (1 or 0) | not stated; 0 is no |
| 19 | `action_date` | Action date | The date the agency took this action. | date (YYYY-MM-DD) | the source states no date |
| 20 | `first_action_date` | first action date | Earliest action date within the award-recipient-fiscal-year. | — | owed: not in the file until the terminal builds it |
| 21 | `last_action_date` | last action date | Latest action date within the award-recipient-fiscal-year. | — | owed: not in the file until the terminal builds it |
| 22 | `obligated_usd` | Amount obligated | Dollars obligated by this transaction. Negative values are de-obligations, kept as recorded. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 23 | `annual_obligations` | annual obligations | Sum of obligated_usd within award, recipient and fiscal year, once the annual grain is supported. | — | owed: not in the file until the terminal builds it |
| 24 | `obligated_usd_real2025` | Amount in 2025 dollars | The same amount adjusted for inflation to 2025 dollars. | number | the source states none, or not applicable to this row |
| 25 | `face_value_of_loan` | Loan face value | For loans, the face value of this loan; zero for grants. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 26 | `original_loan_subsidy_cost` | Original loan subsidy cost | For a loan, the government's estimated cost of the subsidy when it was made. A loan measure; never added to obligations. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 27 | `total_face_value_of_loan` | Award loan face value | For loans, the face value of the whole award to date. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 28 | `total_loan_subsidy_cost` | Total loan subsidy cost | The subsidy cost across the award's loan actions. Never added to obligations. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 29 | `business_types_description` | Recipient type as recorded | How USAspending classifies the recipient (for example, federally recognized tribal government). | text | the source states none, or not applicable to this row |
| 30 | `recipient_city_name` | Recipient city | City of the recipient's address on the award. | text | the source states none, or not applicable to this row |
| 31 | `recipient_state_code` | Recipient state | State of the recipient's address on the award. | text | the source states none, or not applicable to this row |
| 32 | `recipient_county_name` (was `geo_recipient_county_name`) | Recipient county | The county of the recipient's address, which is not necessarily where the funded work happens. | text | the source states none, or not applicable to this row |
| 33 | `recipient_county_fips` (was `geo_recipient_county_fips`) | Recipient county FIPS | The county code of the recipient's address. | text | the source states none, or not applicable to this row |
| 34 | `place_of_performance_county_name` (was `geo_pop_county_name`) | Place of performance county | The county where the funded work is performed, as the award reports it. | text | the source states none, or not applicable to this row |
| 35 | `place_of_performance_county_fips` (was `geo_pop_county_fips`) | Place of performance county FIPS | The county code where the funded work is performed, as the award reports it. | text | the source states none, or not applicable to this row |
| 36 | `attributed_flag` | Attributed to the entity | Whether Cedar attributes this transaction to the Native entity (yes) or keeps it in the file unattributed (no). Cedar's totals count attributed rows only. | yes or no (1 or 0) | not stated; 0 is no |
| 37 | `attribution_status` | Attribution status | How the attribution stands: attributed through the register, unattributed, or under review. | text | the source states none, or not applicable to this row |
| 38 | `attribution_method` | How the entity was matched | How Cedar linked this recipient to the entity (for example, an exact UEI match). | text | the source states none, or not applicable to this row |
| 39 | `confidence_tier` | Match confidence | Cedar's confidence in the link: A is strongest. | text | the source states none, or not applicable to this row |
| 40 | `source_system` | Source system | Which source family the row came from: the USAspending archive or the historical FAADS files. The two overlap in coverage and are never summed as one. | text | the source states none, or not applicable to this row |
| 41 | `source_url` | Source | The award's page on USAspending. | web address | the source states none, or not applicable to this row |

## Missing values

A blank is never zero and never an invented date. Beyond the column-level rules above:

- A blank `cedar_uid` with `attributed_flag` = 0 means unattributed, not non-Native.
- A blank loan column on a grant row means not applicable; on a loan row it means the source did not report it.
- A blank `recipient_county_name` means the address could not be placed in one county with confidence; the city and state still ship.

## Limitations

- Two source families cover the years: the USAspending archive (FY2007 onward) and the historical FAADS files (FY2001 to FY2007). They both hold FY2007, and 98.9% of the modern table's FY2007 dollars sit on awards the archive table also carries (docs/MONEY_TOTALLING_RULES.md, the FY2007 seam). `source_system` says which family a row is from; never stack the two families for one year.
- Coverage begins where the source does. An award that is not in the file, or a blank amount, is not evidence that no funding reached the entity.
- The award-recipient-fiscal-year product the specification asks for (§4) is owed: the terminal measures whether stable award identity and compatible transaction measures support it before it ships. Until then the row is the transaction.
- Loan measures (face value, subsidy cost) describe credit instruments and are not obligations; `credit_instrument_flag` marks the rows they belong to.

## Suitable analyses

- Obligations by fiscal year, program (`cfda`), agency or entity, counting `attributed_flag` = 1 rows and excluding partial fiscal years, or stating them.
- Which programs reach which entities, and first and last action dates per award.
- Constant-dollar comparisons across years using `obligated_usd_real2025` (base year 2025; the deflator is stated in the release, not on the row).

## Unsafe aggregations

- Summing `obligated_usd` across both source families for FY2007, or stacking the FAADS and USAspending files for a multi-year series without the seam rule above.
- Adding loan face values or subsidy costs to obligations, or to each other.
- Attributing a consortium's or a Native-serving organization's award to a member tribe.
- Treating a partial fiscal year (`fy_partial_flag` = 1) as a complete one in a year-on-year comparison.
- Joining this table to another collection on `cedar_uid` alone and summing: one entity has many transactions, and the join multiplies rows. Aggregate to the entity-year here first.

## What is still owed

Target columns the specification asks for that the terminal has not yet built from the full table. Each ships blank-free, not blank: it is absent until it exists.

- `annual_obligations` (pending:grain change): Sum of obligated_usd within award, recipient and fiscal year, once the annual grain is supported.
- `first_action_date` (pending:grain change): Earliest action date within the award-recipient-fiscal-year.
- `last_action_date` (pending:grain change): Latest action date within the award-recipient-fiscal-year.
- `record_type` (pending:grain change): award_year or source_record, for historical rows that cannot support award identity.

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Federal Funding to Indian Country" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** Recipients are matched to the entity layer and the basis for inclusion is carried on the row, so a payment to a tribal government, to an intertribal consortium acting for many tribes, and to a Native-serving non-Native organisation are distinguishable. Apparent duplicate transactions are retained: they are usually distinct modifications to one award that agree on every published field, and removing them would have destroyed $8.29B of real obligations.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

