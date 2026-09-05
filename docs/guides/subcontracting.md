# Native Federal Subcontracting: a researcher's guide

Collection `subcontracting` · public file `subcontracting.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Subaward transactions where a Native entity is the prime, the subcontractor, or both, drawn from federal subaward reporting.

## Population

Reported subawards where the prime, the subrecipient or both are owned by a Native entity, drawn from FSRS subaward reporting through USAspending and keyed to the prime award. Both sides are resolved independently, so a Native prime paying a non-Native sub and the reverse are distinguishable (collection descriptor).

## One row is

One reported subaward or version, as today, with its controls; revisions are not collapsed.

This pass changes columns, never rows: no aggregation, deduplication, change of publication eligibility or reassignment of Cedar IDs.

## Key identifiers

`subaward_record_id` makes the row unique; `subaward_number` is the subaward's own number; `prime_award_id` and `prime_award_unique_key` name the prime award. UEIs and CAGE codes identify each side and its declared parent; a UEI, CAGE or name is masked on a row of an individually owned firm without recorded consent.

## Sources and coverage

**Sources:** FSRS subaward reporting via USAspending, keyed to the prime award.

**Rows in the flagship table as released (recorded 2026-09-04):** 89,809. This is the count the release recorded for `subawards.csv`, not the sum of the collection's 5 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`subaward_date` and `fiscal_year` are the subaward's; `report_year` and `report_last_modified_date` are the report's, which is the version marker. Subrecipient geography (`sub_city`, `subcontractor_state`, `sub_zip5`, `sub_county_name`) is the subrecipient's own and is never filled from the prime's address; the prime's geography does not ship here.

## Entity relationships

The opening block of every row is `cedar_uid`, `canonical_name`, `entity_class` and `cedar_entity_role`. `native_direction` says which side creates the Native connection (sub, prime or both) and `cedar_entity_role` is read from it. `sub_cedar_uid` and `prime_cedar_uid` are role-specific links and both ship; the viewer finds a row through either. A Native prime does not make its subcontractors Native.

Further role-specific links on the row, each an entity of the record the viewer finds it by:

- `sub_cedar_uid`: owner of the subcontractor
- `prime_cedar_uid`: owner of the prime

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

Repeat monthly filings of one subaward are retained and flagged, not deleted: `duplicate_status` is primary for the countable filing and names the repeat otherwise. Summing without that filter lands 63.4% above the correct total: $57.02B unfiltered against $34.91B correct, a $22.11B difference, which is 38.8% of the unfiltered figure (collection descriptor and docs/MONEY_TOTALLING_RULES.md, measured 2026-09-02).

## Field dictionary

The approved header, in the owner's exact order (54 columns, of which 0 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros; a JSON array cell is one list, aligned with its neighbours where the dictionary says so.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. | text | the source states none, or not applicable to this row |
| 3 | `entity_class` | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. | text | the source states none, or not applicable to this row |
| 4 | `cedar_entity_role` | Entity role | Why the entity is on this row: from native_direction: owner of the subcontractor, of the prime, or of both. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 5 | `subaward_record_id` (was `subaward_source_record_id`) | Subaward ID | The subaward report's identifier. | identifier, as text | the source states none, or not applicable to this row |
| 6 | `subaward_number` | Subaward number | The subaward's own number as the prime reported it. | identifier, as text | the source states none, or not applicable to this row |
| 7 | `report_id` (was `subaward_sam_report_id`) | Report ID | The SAM subaward report's identifier: the version of the report this row comes from. | identifier, as text | the source states none, or not applicable to this row |
| 8 | `subaward_date` | Subaward date | The date of the subaward. | date (YYYY-MM-DD) | the source states no date |
| 9 | `fiscal_year` | Fiscal year | The federal fiscal year of the subaward. | year | the source states no date |
| 10 | `report_year` (was `subaward_sam_report_year`) | Report year | The year of the report the subaward was filed in: the reporting period. | year | the source states no date |
| 11 | `award_kind` | Award type | Whether the prime award is a contract or an assistance award. The two populations are never combined in a total. | text | the source states none, or not applicable to this row |
| 12 | `subaward_type` | Subaward type | Sub-contract or sub-grant, as reported. | text | the source states none, or not applicable to this row |
| 13 | `description` | Description | What the subcontract is for, as reported. | text | the source states none, or not applicable to this row |
| 14 | `subcontractor_name` (was `sub_name`) | Subcontractor | The subcontractor as reported. | text | the source states none, or not applicable to this row |
| 15 | `subcontractor_uei` (was `sub_uei`) | Subcontractor UEI | Its Unique Entity ID. | identifier, as text | the source states none, or not applicable to this row |
| 16 | `subcontractor_cage` (was `sub_cage`) | Subcontractor CAGE | Its CAGE code, where reported. | identifier, as text | the source states none, or not applicable to this row |
| 17 | `subcontractor_parent_name` (was `sub_parent_name`) | Subcontractor's parent | Its parent as reported. | text | the source states none, or not applicable to this row |
| 18 | `subcontractor_parent_uei` (was `sub_parent_uei`) | Subrecipient parent UEI | The UEI of the subrecipient's declared parent. | identifier, as text | the source states none, or not applicable to this row |
| 19 | `subcontractor_parent_cage` (was `sub_parent_cage`) | Subrecipient parent CAGE | The CAGE code of the subrecipient's declared parent. | identifier, as text | the source states none, or not applicable to this row |
| 20 | `sub_cedar_uid` | Subcontractor's Cedar ID | The Native entity owning the subcontractor, where one does. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 21 | `prime_name` | Prime contractor | The prime as reported. | text | the source states none, or not applicable to this row |
| 22 | `prime_uei` | Prime UEI | Its Unique Entity ID. | identifier, as text | the source states none, or not applicable to this row |
| 23 | `prime_cage` | Prime CAGE | Its CAGE code, where reported. | identifier, as text | the source states none, or not applicable to this row |
| 24 | `prime_parent_name` | Prime's parent | Its parent as reported. | text | the source states none, or not applicable to this row |
| 25 | `prime_parent_uei` | Prime parent UEI | The UEI of the prime's declared parent. | identifier, as text | the source states none, or not applicable to this row |
| 26 | `prime_parent_cage` | Prime parent CAGE | The CAGE code of the prime's declared parent. | identifier, as text | the source states none, or not applicable to this row |
| 27 | `prime_cedar_uid` | Prime's Cedar ID | The Native entity owning the prime contractor, where one does. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 28 | `native_direction` (was `direction`) | Which side is Native | Whether the prime, the sub, or both sides are Native-owned. | text | the source states none, or not applicable to this row |
| 29 | `prime_award_id` | Prime award number | The prime contract's number. | identifier, as text | the source states none, or not applicable to this row |
| 30 | `prime_award_unique_key` | Prime award key | USAspending's key for the prime award. | identifier, as text | the source states none, or not applicable to this row |
| 31 | `subaward_amount_usd` (was `subaward_amount`) | Subaward amount | Dollars of the subaward. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 32 | `subaward_amount_usd_real2025` (was `subaward_amount_real2025`) | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. | number | the source states none, or not applicable to this row |
| 33 | `prime_award_amount_usd` (was `prime_award_amount`) | Prime award amount | The prime contract's value. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 34 | `subaward_to_prime_ratio` | Subaward to prime ratio | The subaward amount divided by the prime award amount, with the amount, period and version definitions the guide states; never recomputed from incompatible snapshots. | number | the source states none, or not applicable to this row |
| 35 | `awarding_agency` (was `prime_top_awarding_agency`) | Agency | The department that awarded the prime contract. | text | the source states none, or not applicable to this row |
| 36 | `awarding_subagency` (was `prime_awarding_sub_agency`) | Office | The office within it. | text | the source states none, or not applicable to this row |
| 37 | `prime_set_aside` | Prime set-aside | The set-aside category of the prime award, where reported. | text | the source states none, or not applicable to this row |
| 38 | `naics_code` (was `naics`) | NAICS | The industry code. | number | the source states none, or not applicable to this row |
| 39 | `naics_description` (was `naics_title`) | Industry | What that code means. | text | the source states none, or not applicable to this row |
| 40 | `psc_code` (was `psc`) | Product or service code | The federal product or service code of the subaward, where reported. | text | the source states none, or not applicable to this row |
| 41 | `psc_description` (was `psc_title`) | Product or service | What the product or service code means. | text | the source states none, or not applicable to this row |
| 42 | `subcontractor_business_types` (was `sub_business_types`) | Subcontractor business types | The business types it reports (for example, Alaska Native Corporation owned). | text | the source states none, or not applicable to this row |
| 43 | `subcontractor_city` (was `geo_subawardee_city`) | Subrecipient city | The subrecipient's own city, never filled from the prime's address. | text | the source states none, or not applicable to this row |
| 44 | `subcontractor_state` (was `sub_state`) | Subcontractor state | Its state. | text | the source states none, or not applicable to this row |
| 45 | `subcontractor_county` (was `geo_subawardee_county_name`) | Subrecipient county | The county of the subrecipient's address. | text | the source states none, or not applicable to this row |
| 46 | `subcontractor_county_fips` (was `geo_subawardee_county_fips`) | Subrecipient county FIPS | The county code of the subrecipient's address. | text | the source states none, or not applicable to this row |
| 47 | `subcontractor_country` (was `geo_subawardee_country_code`) | Subrecipient country | The subrecipient's country code. | text | the source states none, or not applicable to this row |
| 48 | `subcontractor_geography_status` | Subcontractor geography status | Whether the subcontractor's own address was placed in a county: placed, placed with an ambiguous place name, or unplaced. Never filled from the prime's address. | text | the source states none, or not applicable to this row |
| 49 | `duplicate_status` | Duplicate status | Whether this row is the primary filing or a duplicate of one. Sum primaries only. | text | the source states none, or not applicable to this row |
| 50 | `subaward_exceeds_prime_flag` | Exceeds the prime award | Whether the subaward amount exceeds its prime award (yes or no). A real filing, kept in the file, but never added into totals. | yes or no (1 or 0) | not stated; 0 is no |
| 51 | `action_date_precedes_ffata_flag` | Date before FFATA | Whether the reported date precedes the reporting law itself (yes or no), a known filer anomaly; do not treat such a date as when the work happened. | yes or no (1 or 0) | not stated; 0 is no |
| 52 | `source_system` (was `source_dataset`) | Source system | Which source the report came from (the USAspending FSRS pull). | text | the source states none, or not applicable to this row |
| 53 | `source_url` | Source | The prime award's page on USAspending. | web address | the source states none, or not applicable to this row |
| 54 | `research_note` | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. | text | the source states none, or not applicable to this row |

## Missing values

A blank is never zero and never an invented date. A blank JSON-list cell means unknown; `[]` means known to be empty (no additional source, no additional institution); a null element inside a list is one member the evidence names but does not resolve. Identifiers and codes are text with their leading zeros. Beyond the column-level rules above:

- Blank CAGE or parent columns mean the report carries none (FSRS reports UEIs; CAGE is filled from SAM where known).
- A blank `product_or_service_code` means the report carries none.

## Limitations

- `subaward_amount_usd` is additive only where `duplicate_status` is primary and `subaward_exceeds_prime_flag` is not yes; a subaward exceeding its prime is a real filing that is never summed.
- `action_date_precedes_ffata_flag` marks filings whose action dates precede the reporting requirement and are known filer anomalies; do not read such a date as when the work happened.
- `award_type` separates contract subawards from assistance subawards; the two populations are never combined in one total.
- The subaward-to-prime ratio does not ship: numerator and denominator have not been shown to cover compatible definitions, periods and versions (§11).

## Suitable analyses

- Subaward amounts by entity, year, agency and NAICS over the countable rows.
- Prime-to-sub networks between Native firms (`native_side` = both).
- Subrecipient geography of Native primes' subawards.

## Unsafe aggregations

- Summing `subaward_amount_usd` over every row.
- Adding subaward amounts to prime obligations as independent federal spending.
- Summing successive report versions of one subaward.

## What is still owed

Nothing beyond the grain and harmonization work named above.

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Native Federal Subcontracting" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** Both sides of every subaward are resolved independently, so a Native prime paying a non-Native sub and the reverse are distinguishable rather than collapsed. Repeat monthly filings of one subaward are retained and flagged in-band rather than deleted, because the filings are real events: summing without that filter lands 63.4% above the correct total ($57.02B unfiltered against $34.91B correct, a $22.11B difference), and the denominator is stated because the same difference is 38.8% of the unfiltered figure and quoting the two without saying which is which makes an honest warning look like an arithmetic error. A subaward is a slice of a prime award and must never be added to the prime contracting dataset — the totalling rules ship with the data.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

