# Native Federal Contractors: a researcher's guide

Collection `contractors` · public file `contractors.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Federal prime contract transactions awarded to tribally owned firms, ANC and NHO subsidiaries and individually Native-owned businesses, FY2000 to current, matched to the Native entity that ultimately owns the awardee.

## Population

Federal prime contract transactions awarded to firms owned by a Native entity: tribally owned firms, ANC and NHO subsidiaries and individually Native-owned businesses, FY2000 to current, matched to the entity that ultimately owns the awardee. Coverage begins at FY2000 because Native identification does not exist in the pre-2000 federal record, and $65.2B of candidate rows remain unattributed rather than assigned by guesswork (collection descriptor, measured 2026-09-02).

## One row is

One transaction or modification, as today; no aggregation to award-year and no collapsing of genuine modifications.

This pass changes columns, never rows: no aggregation, deduplication, change of publication eligibility or reassignment of Cedar IDs.

## Key identifiers

`award_id` names the award and `transaction_id` the transaction; `contract_number` and `parent_contract_number` are the contract's own numbers; `awardee_uei` and `cage_code` identify the contractor and `parent_uei` its declared parent. CAGE is kept because it persists across the DUNS-to-UEI change; a UEI, CAGE or name is masked on a row of an individually owned firm without recorded consent, never dropped as a column.

## Sources and coverage

**Sources:** FPDS via USAspending; SAM entity registrations; parent-published subsidiary disclosures, including ANCSA audited filings under Alaska Statute 45.55.139.

**Rows in the flagship table as released (recorded 2026-09-04):** 1,217,768. This is the count the release recorded for `prime_contracts.csv`, not the sum of the collection's 11 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`fiscal_year` is the federal fiscal year of `action_date`. Recipient geography (`recipient_city`, `recipient_state`, `recipient_county_name`) is the contractor's address; place-of-performance geography is where the work is performed.

## Entity relationships

The opening block of every row is `cedar_uid`, `canonical_name`, `entity_class` and `cedar_entity_role`. `cedar_entity_role` is the owner of the awardee as resolved for the transaction's date. The contractor's own name stays in `awardee_name` and is never replaced by the owner's. `owner_attribution_status` says whether ownership is known for that date, and `owner_as_of_transaction_cedar_uid` names the owner as of the action where the ownership history resolves it; UNKNOWN ships as unknown, and current ownership is never assigned backwards.

Further role-specific links on the row, each an entity of the record the viewer finds it by:

- `owner_as_of_transaction_cedar_uid`: owner as of the action date

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

FPDS reports modifications as further transactions on the award. `obligations_usd` is the incremental obligation on each transaction, negative for a deobligation, and is the additive measure; `cumulative_award_value_usd` is the award's ceiling, non-additive across transactions and years.

## Field dictionary

The approved header, in the owner's exact order (49 columns, of which 2 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros; a JSON array cell is one list, aligned with its neighbours where the dictionary says so.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. | text | the source states none, or not applicable to this row |
| 3 | `entity_class` | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. | text | the source states none, or not applicable to this row |
| 4 | `cedar_entity_role` | Entity role | Why the entity is on this row: owner of the awardee. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 5 | `transaction_id` (was `contract_transaction_unique_key`) | Transaction ID | USAspending's key for this transaction. | identifier, as text | the source states none, or not applicable to this row |
| 6 | `award_id` (was `contract_award_unique_key`) | Award ID | USAspending's key for the whole award; the source link is built from it. | identifier, as text | the source states none, or not applicable to this row |
| 7 | `contract_number` | Contract number | The contract or order number. | identifier, as text | the source states none, or not applicable to this row |
| 8 | `parent_contract_number` | Parent contract | The parent contract or vehicle, for orders. | identifier, as text | the source states none, or not applicable to this row |
| 9 | `action_date` | Action date | The date of this award or modification. | date (YYYY-MM-DD) | the source states no date |
| 10 | `fiscal_year` | Fiscal year | The federal fiscal year of the action. | year | the source states no date |
| 11 | `awardee_name` | Awardee | The contractor as the award names it. | text | masked where the publication policy withholds it; otherwise the source reports none |
| 12 | `awardee_uei` | Awardee UEI | The contractor's federal Unique Entity ID. | identifier, as text | masked where the publication policy withholds it; otherwise the source reports none |
| 13 | `cage_code` | Awardee CAGE | The contractor's CAGE code, the identifier that persists across the DUNS-to-UEI change; masked on rows the publication rule withholds. | identifier, as text | masked where the publication policy withholds it; otherwise the source reports none |
| 14 | `parent_name` | Awardee's parent | The contractor's parent as the award records it. | text | the source states none, or not applicable to this row |
| 15 | `parent_uei` | Parent UEI | The UEI of the parent FPDS declares for the contractor. | identifier, as text | the source states none, or not applicable to this row |
| 16 | `funding_agency` | Funding agency | The agency paying for the work. | text | the source states none, or not applicable to this row |
| 17 | `award_type` | Award type | Delivery order, BPA call, definitive contract, and so on. | text | the source states none, or not applicable to this row |
| 18 | `description` (was `award_base_description`) | Description | The award's own description of the work. | text | the source states none, or not applicable to this row |
| 19 | `naics_code` | NAICS | The industry code of the work. | text | the source states none, or not applicable to this row |
| 20 | `naics_description` | Industry | What that code means. | text | the source states none, or not applicable to this row |
| 21 | `psc_code` (was `product_or_service_code`) | Product or service code | The federal product or service code (PSC), defined in the dictionary; the description is beside it. | text | the source states none, or not applicable to this row |
| 22 | `psc_description` (was `product_or_service_code_description`) | Product or service | What was bought. | text | the source states none, or not applicable to this row |
| 23 | `sector` | Sector | The two-digit sector code and the readable group consolidated into one readable sector through the dictionary. | number | the source states none, or not applicable to this row |
| 24 | `obligations_usd` (was `total_obligations`) | Amount obligated | Dollars obligated by this transaction. Sum these, never the award value. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 25 | `obligations_usd_real2025` (was `total_obligations_real2025`) | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. | number | the source states none, or not applicable to this row |
| 26 | `cumulative_award_value_usd` (was `total_award_value`) | Award value to date | The whole award's value as restated on this row. Cumulative: never add it across rows. | number | the source states none, or not applicable to this row |
| 27 | `set_aside_reported` (was `setaside_reported`) | Set-aside reported (yes or no) | Whether the award reports any set-aside; the classification beside it says which. | number | the source states none, or not applicable to this row |
| 28 | `set_aside_classification` (was `setaside`) | Set-aside | The set-aside the award was made under, if any. | text | the source states none, or not applicable to this row |
| 29 | `reported_8a` | 8(a) reported | Whether the award reports the 8(a) program (yes or no). | yes or no (1 or 0) | not stated; 0 is no |
| 30 | `reported_buy_indian` | Buy Indian Act reported (yes or no) | Whether the award reports use of the Buy Indian Act preference. Reported use, not eligibility. | yes or no (1 or 0) | not stated; 0 is no |
| 31 | `reported_indian_business` | Indian business reported (yes or no) | Whether the award reports the contractor as an Indian business under the relevant preference. | yes or no (1 or 0) | not stated; 0 is no |
| 32 | `reported_native_preference` | Native preference reported | Whether the award reports a Native preference (yes or no). | yes or no (1 or 0) | not stated; 0 is no |
| 33 | `competition_type` | competition type | Consolidated through a validated dictionary. | — | owed: not in the file until the terminal builds it |
| 34 | `recipient_city` (was `recipient_city_name`) | Awardee city | City of the awardee's address. | text | the source states none, or not applicable to this row |
| 35 | `recipient_state` (was `recipient_state_code`) | Awardee state | Its state. | text | the source states none, or not applicable to this row |
| 36 | `recipient_county` (was `geo_recipient_county_name`) | Recipient county | The county of the contractor's address, which is not where the work is performed. | text | the source states none, or not applicable to this row |
| 37 | `recipient_county_fips` (was `geo_recipient_county_fips`) | Recipient county FIPS | The county code of the contractor's address. | text | the source states none, or not applicable to this row |
| 38 | `performance_city` (was `place_of_perform_city`) | Place of performance | City where the work is performed. | text | the source states none, or not applicable to this row |
| 39 | `performance_state` (was `place_of_perform_state`) | Place of performance state | Its state. | text | the source states none, or not applicable to this row |
| 40 | `performance_county` (was `geo_pop_county_name`) | Place of performance county | The county where the contract is performed, as the award reports it. | text | the source states none, or not applicable to this row |
| 41 | `performance_county_fips` (was `geo_pop_county_fips`) | Place of performance county FIPS | The county code where the contract is performed. | text | the source states none, or not applicable to this row |
| 42 | `recipient_geography_status` | Recipient geography status | Whether the recipient's address was placed in a county: placed, placed with an ambiguous place name, or unplaced. | text | the source states none, or not applicable to this row |
| 43 | `performance_geography_status` | Performance geography status | The same for the place of performance. | text | the source states none, or not applicable to this row |
| 44 | `attributed_flag` | Attributed (yes or no) | Whether the row is attributed to the Native entity in the opening block; the totals count attributed rows only. | yes or no (1 or 0) | not stated; 0 is no |
| 45 | `owner_attribution_status` | Ownership at the time | Whether the entity's ownership of the awardee was confirmed as of the transaction. | text | the source states none, or not applicable to this row |
| 46 | `owner_as_of_transaction_cedar_uid` | Owner as of the action | The Cedar ID of the entity that owned the contractor on the action date where the ownership history resolves it; UNKNOWN where it does not. Never the current owner assumed backwards. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 47 | `source_system` | Source system | Which source the record came from. | text | the source states none, or not applicable to this row |
| 48 | `source_url` | Source | The official page for this record, written into the file so it cites itself. | web address | the source states none, or not applicable to this row |
| 49 | `research_note` | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. | text | the source states none, or not applicable to this row |

Until the combined columns exist, the file carries their sources, each with its own label:

- `sector` (Sector) combines into `sector`: The two-digit sector code and the readable group consolidated into one readable sector through the dictionary.
- `supersector` (Industry group) combines into `sector`: The broad industry group the contract's NAICS code belongs to.
- `extent_competed` (Extent competed) combines into `competition_type`: Raw and normalized competition labels consolidated through a validated dictionary.
- `extent_competed_normalized` (Competition) combines into `competition_type`: How the award was competed.

## Missing values

A blank is never zero and never an invented date. Beyond the column-level rules above:

- `owner_as_of_transaction_cedar_uid` = UNKNOWN means the ownership history does not cover the date; the row is still attributed to the entity in the opening block by its current resolution.
- A blank `performance_city` means the award reports none.

## Limitations

- Ownership, preference eligibility and use of a preference are different concepts: `set_aside_classification` is the category used on the award; the four `reported_*` columns are reported preference use.
- Award obligations are not contractor revenue or economic impact.
- This pass changes columns, never rows: the row stays the transaction or modification, and genuine modifications are never collapsed. The annual record the earlier brief mentioned was withdrawn by the owner's column specification.

## Suitable analyses

- Obligations by fiscal year, agency, NAICS and entity, summing `obligations_usd`.
- Contractors per entity and awards per contractor.
- Set-aside and competition categories by year.

## Unsafe aggregations

- Summing `cumulative_award_value_usd` across transactions or years.
- Assigning a full year's obligations to a current owner where `owner_attribution_status` says the owner as of the action is unknown or different.
- Adding subawards from the subcontracting collection to prime obligations: a subaward is a slice of a prime already counted.

## What is still owed

Target columns the specification asks for that the terminal has not yet built from the full table. Each is absent until it exists, never blank.

- `sector` (combine:sector\|supersector): One readable sector through the dictionary.
- `competition_type` (combine:extent_competed\|extent_competed_normalized): Consolidated through a validated dictionary.

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Native Federal Contractors" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** Awardees are matched to a Native entity by identifier first (UEI, CAGE, declared parent UEI) and by name only with corroboration, because a subsidiary's legal name routinely shares no token with its owner — ASRC Federal's operating companies file as BROADLEAF, INUTEQ and VISTRONIX. Attribution tier is recorded on every row and a tier is never promoted by a name match alone. Known limits are published, not hidden: coverage begins at FY2000 because Native identification does not exist in the pre-2000 federal record at all, and $65.2B of candidate rows remain unattributed rather than being assigned to a plausible owner.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

