# Native Federal Contractors: a researcher's guide

Collection `contractors` · public file `contractors.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Federal prime contract transactions awarded to tribally owned firms, ANC and NHO subsidiaries and individually Native-owned businesses, FY2000 to current, matched to the Native entity that ultimately owns the awardee.

## Population

Federal prime contract transactions awarded to firms owned by a Native entity: tribally owned firms, ANC and NHO subsidiaries and individually Native-owned businesses, FY2000 to current, matched to the entity that ultimately owns the awardee. Coverage begins at FY2000 because Native identification does not exist in the pre-2000 federal record, and $65.2B of candidate rows remain unattributed rather than assigned by guesswork (collection descriptor, measured 2026-09-02).

## One row is

**Today:** One federal contract transaction (an award or a modification) to a firm owned by a Native entity, as FPDS reports it through USAspending.

**When the specification is applied:** One transaction, as today, until the terminal measures whether the transaction history supports the award-recipient-fiscal-year public record the specification asks for; where it does, annual obligations are built from incremental transaction measures and the transactions stay internal.

**Grain change:** Owed (§10): annual obligations from verified incremental measures, deobligations kept, cumulative award values never summed; ownership matched to the period (an as-of owner per transaction is already carried and must not be replaced by the current owner); a within-year ownership change gets an attribution-period grain or a stated qualification. Needs the full table and docs/schema/ownership_change_invariants.json.

## Key identifiers

`contract_award_unique_key` names the award and `contract_transaction_unique_key` the transaction; `contract_number` and `parent_contract_number` are the contract's own numbers; `awardee_uei` and `cage_code` identify the contractor and `parent_uei` its declared parent. CAGE is kept because it persists across the DUNS-to-UEI change; a UEI, CAGE or name is masked on a row of an individually owned firm without recorded consent, never dropped as a column.

## Sources and coverage

**Sources:** FPDS via USAspending; SAM entity registrations; parent-published subsidiary disclosures, including ANCSA audited filings under Alaska Statute 45.55.139.

**Rows in the flagship table as released (recorded 2026-09-04):** 1,217,768. This is the count the release recorded for `prime_contracts.csv`, not the sum of the collection's 11 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`fiscal_year` is the federal fiscal year of `action_date`. Recipient geography (`recipient_city_name`, `recipient_state_code`, `recipient_county_name`) is the contractor's address; place-of-performance geography is where the work is performed.

## Entity relationships

The opening block of every row is `cedar_uid`, `cedar_entity_name`, `cedar_entity_type` and `cedar_entity_role`. `cedar_entity_role` is the owner of the awardee as resolved for the transaction's date. The contractor's own name stays in `awardee_name` and is never replaced by the owner's. `owner_attribution_status` says whether ownership is known for that date, and `owner_as_of_transaction_cedar_uid` names the owner as of the action where the ownership history resolves it; UNKNOWN ships as unknown, and current ownership is never assigned backwards.

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

FPDS reports modifications as further transactions on the award. `total_obligations` is the incremental obligation on each transaction, negative for a deobligation, and is the additive measure; `total_award_value` is the award's ceiling, non-additive across transactions and years.

## Field dictionary

The approved header, in order (48 columns, of which 3 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `cedar_entity_name` (was `canonical_name`) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 3 | `cedar_entity_type` | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 4 | `cedar_entity_role` | Entity role | Why the entity is on this row: owner of the awardee, as resolved for the transaction's date. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 5 | `contract_award_unique_key` | Award ID | USAspending's key for the whole award; the source link is built from it. | identifier, as text | the source states none, or not applicable to this row |
| 6 | `contract_number` | Contract number | The contract or order number. | identifier, as text | the source states none, or not applicable to this row |
| 7 | `parent_contract_number` | Parent contract | The parent contract or vehicle, for orders. | identifier, as text | the source states none, or not applicable to this row |
| 8 | `contract_transaction_unique_key` | Transaction ID | USAspending's key for this transaction. | identifier, as text | the source states none, or not applicable to this row |
| 9 | `awardee_name` | Awardee | The contractor as the award names it. | text | masked where the publication policy withholds it; otherwise the source reports none |
| 10 | `awardee_uei` | Awardee UEI | The contractor's federal Unique Entity ID. | identifier, as text | masked where the publication policy withholds it; otherwise the source reports none |
| 11 | `cage_code` | Awardee CAGE | The contractor's CAGE code, the identifier that persists across the DUNS-to-UEI change; masked on rows the publication rule withholds. | identifier, as text | masked where the publication policy withholds it; otherwise the source reports none |
| 12 | `parent_name` | Awardee's parent | The contractor's parent as the award records it. | text | the source states none, or not applicable to this row |
| 13 | `parent_uei` | Parent UEI | The UEI of the parent FPDS declares for the contractor. | identifier, as text | the source states none, or not applicable to this row |
| 14 | `owner_attribution_status` | Ownership at the time | Whether the entity's ownership of the awardee was confirmed as of the transaction. | text | the source states none, or not applicable to this row |
| 15 | `owner_as_of_transaction_cedar_uid` | Owner as of the action | The Cedar ID of the entity that owned the contractor on the action date where the ownership history resolves it; UNKNOWN where it does not. Never the current owner assumed backwards. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 16 | `fiscal_year` | Fiscal year | The federal fiscal year of the action. | year | the source states no date |
| 17 | `action_date` | Action date | The date of this award or modification. | date (YYYY-MM-DD) | the source states no date |
| 18 | `first_action_date` | first action date | Earliest action date within the award-awardee-fiscal-year. | — | owed: not in the file until the terminal builds it |
| 19 | `last_action_date` | last action date | Latest action date within the award-awardee-fiscal-year. | — | owed: not in the file until the terminal builds it |
| 20 | `total_obligations` | Amount obligated | Dollars obligated by this transaction. Sum these, never the award value. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 21 | `annual_obligations` | annual obligations | Sum of total_obligations within award, awardee and fiscal year, once the annual grain is supported. | — | owed: not in the file until the terminal builds it |
| 22 | `total_obligations_real2025` | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. | number | the source states none, or not applicable to this row |
| 23 | `total_award_value` | Award value to date | The whole award's value as restated on this row. Cumulative: never add it across rows. | number | the source states none, or not applicable to this row |
| 24 | `funding_agency` | Funding agency | The agency paying for the work. | text | the source states none, or not applicable to this row |
| 25 | `award_type` | Award type | Delivery order, BPA call, definitive contract, and so on. | text | the source states none, or not applicable to this row |
| 26 | `contract_description` (was `award_base_description`) | Description | The award's own description of the work. | text | the source states none, or not applicable to this row |
| 27 | `naics_code` | NAICS | The industry code of the work. | text | the source states none, or not applicable to this row |
| 28 | `naics_description` | Industry | What that code means. | text | the source states none, or not applicable to this row |
| 29 | `industry_group` (was `supersector`) | Industry group | The broad industry group the contract's NAICS code belongs to. | text | the source states none, or not applicable to this row |
| 30 | `product_or_service_code` | Product or service code | The federal product or service code (PSC), defined in the dictionary; the description is beside it. | text | the source states none, or not applicable to this row |
| 31 | `product_or_service_code_description` | Product or service | What was bought. | text | the source states none, or not applicable to this row |
| 32 | `setaside` | Set-aside | The set-aside the award was made under, if any. | text | the source states none, or not applicable to this row |
| 33 | `extent_competed` (was `extent_competed_normalized`) | Competition | How the award was competed. | text | the source states none, or not applicable to this row |
| 34 | `reported_8a` | 8(a) reported | Whether the award reports the 8(a) program (yes or no). | yes or no (1 or 0) | not stated; 0 is no |
| 35 | `reported_buy_indian` | Buy Indian Act reported (yes or no) | Whether the award reports use of the Buy Indian Act preference. Reported use, not eligibility. | yes or no (1 or 0) | not stated; 0 is no |
| 36 | `reported_indian_business` | Indian business reported (yes or no) | Whether the award reports the contractor as an Indian business under the relevant preference. | yes or no (1 or 0) | not stated; 0 is no |
| 37 | `reported_native_preference` | Native preference reported | Whether the award reports a Native preference (yes or no). | yes or no (1 or 0) | not stated; 0 is no |
| 38 | `recipient_city_name` | Awardee city | City of the awardee's address. | text | the source states none, or not applicable to this row |
| 39 | `recipient_state_code` | Awardee state | Its state. | text | the source states none, or not applicable to this row |
| 40 | `recipient_county_name` (was `geo_recipient_county_name`) | Recipient county | The county of the contractor's address, which is not where the work is performed. | text | the source states none, or not applicable to this row |
| 41 | `recipient_county_fips` (was `geo_recipient_county_fips`) | Recipient county FIPS | The county code of the contractor's address. | text | the source states none, or not applicable to this row |
| 42 | `place_of_perform_city` | Place of performance | City where the work is performed. | text | the source states none, or not applicable to this row |
| 43 | `place_of_perform_state` | Place of performance state | Its state. | text | the source states none, or not applicable to this row |
| 44 | `place_of_performance_county_name` (was `geo_pop_county_name`) | Place of performance county | The county where the contract is performed, as the award reports it. | text | the source states none, or not applicable to this row |
| 45 | `place_of_performance_county_fips` (was `geo_pop_county_fips`) | Place of performance county FIPS | The county code where the contract is performed. | text | the source states none, or not applicable to this row |
| 46 | `attribution_method` | How the entity was matched | How Cedar linked the awardee to its Native owner. | text | the source states none, or not applicable to this row |
| 47 | `confidence_tier` | Match confidence | Cedar's confidence in the link: A is strongest. | text | the source states none, or not applicable to this row |
| 48 | `source_url` | Source | The award's page on USAspending. | web address | the source states none, or not applicable to this row |

## Missing values

A blank is never zero and never an invented date. Beyond the column-level rules above:

- `owner_as_of_transaction_cedar_uid` = UNKNOWN means the ownership history does not cover the date; the row is still attributed to the entity in the opening block by its current resolution.
- A blank `place_of_perform_city` means the award reports none.

## Limitations

- The award-recipient-fiscal-year public record the specification asks for (§10) is owed: annual obligations from incremental measures, with an attribution-period grain or a stated qualification where ownership changes within a year. Until then the row is the transaction.
- Ownership, preference eligibility and use of a preference are different concepts: `setaside` is the category used on the award; the four `reported_*` columns are reported preference use.
- Award obligations are not contractor revenue or economic impact.

## Suitable analyses

- Obligations by fiscal year, agency, NAICS and entity, summing `total_obligations`.
- Contractors per entity and awards per contractor.
- Set-aside and competition categories by year.

## Unsafe aggregations

- Summing `total_award_value` across transactions or years.
- Assigning a full year's obligations to a current owner where `owner_attribution_status` says the owner as of the action is unknown or different.
- Adding subawards from the subcontracting collection to prime obligations: a subaward is a slice of a prime already counted.

## What is still owed

Target columns the specification asks for that the terminal has not yet built from the full table. Each ships blank-free, not blank: it is absent until it exists.

- `annual_obligations` (pending:grain change): Sum of total_obligations within award, awardee and fiscal year, once the annual grain is supported.
- `first_action_date` (pending:grain change): Earliest action date within the award-awardee-fiscal-year.
- `last_action_date` (pending:grain change): Latest action date within the award-awardee-fiscal-year.

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Native Federal Contractors" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** Awardees are matched to a Native entity by identifier first (UEI, CAGE, declared parent UEI) and by name only with corroboration, because a subsidiary's legal name routinely shares no token with its owner — ASRC Federal's operating companies file as BROADLEAF, INUTEQ and VISTRONIX. Attribution tier is recorded on every row and a tier is never promoted by a name match alone. Known limits are published, not hidden: coverage begins at FY2000 because Native identification does not exist in the pre-2000 federal record at all, and $65.2B of candidate rows remain unattributed rather than being assigned to a plausible owner.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

