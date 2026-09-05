# Tribal Natural Resource Revenue: a researcher's guide

Collection `natural-resources` · public file `natural-resources.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Revenue reaching tribes and individual allottees from minerals, oil and gas, coal, timber and surface leases, 1880 to current.

## Population

Payments and distributions of natural-resource revenue reaching tribes and individual allottees from minerals, oil and gas, coal, timber and surface leases, with each row's measurement status and aggregation level stated. Where Interior suppresses the entity by law the row is published as an aggregate and labelled as one: 88.1% (9,791 national plus 167 state of 11,305 rows) of rows are aggregate for that reason (collection descriptor, measured 2026-09-02). Individual allottee detail is never published.

## One row is

One event or period at its stated measurement level, as today.

This pass changes columns, never rows: no aggregation, deduplication, change of publication eligibility or reassignment of Cedar IDs.

## Key identifiers

`resource_revenue_event_id` names the event; `source_system` and `source_record_id` name the record in its source. `beneficiary_entity_id`, `payer_entity_id` and `operator_entity_id` keep their declared namespaces and are Cedar IDs only where the party is a Native entity; only verified Cedar IDs are used as Native entity join keys.

## Sources and coverage

**Sources:** ONRR disbursements and monthly revenue; historical MMS American Indian collections; OSMRE Abandoned Mine Land distributions; state severance distributions; ANCSA section 7(i) and 7(j) filings; Osage Minerals Council payment history.

**Rows in the flagship table as released (recorded 2026-09-04):** 11,305. This is the count the release recorded for `resource_revenue.csv`, not the sum of the collection's 10 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`period_type`, `period_start` and `period_end` are the period the amount covers; `payment_date` is the payment's or announcement's date, and `measurement_status` says which it is (an actual payment, an announced allocation, a budget). `geography_note` and `land_status` carry what the source states about place and land.

## Entity relationships

The opening block of every row is `cedar_uid`, `canonical_name`, `entity_class` and `cedar_entity_role`. `cedar_entity_role` is `recipient`. `beneficiary_entity_id` names the beneficiary where it differs from the recipient (a distribution to allottees through a tribe, say), with `beneficiary_note` explaining. `attribution_status` says whether the row is keyed to an entity, to an aggregate or unresolved, so a blank `cedar_uid` has a stated reason.

Further role-specific links on the row, each an entity of the record the viewer finds it by:

- `beneficiary_entity_id`: beneficiary

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

Sources restate prior periods; `amount_sign_meaning` says what a negative or an adjustment means. Allocation rules (`allocation_formula` and its effective dates) are documented with their periods and never used to fill an unsupported tribal share.

## Field dictionary

The approved header, in the owner's exact order (38 columns, of which 0 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros; a JSON array cell is one list, aligned with its neighbours where the dictionary says so.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. | text | the source states none, or not applicable to this row |
| 3 | `entity_class` | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. | text | the source states none, or not applicable to this row |
| 4 | `cedar_entity_role` | Entity role | Why the entity is on this row: recipient. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 5 | `resource_revenue_event_id` | Payment ID | Cedar's identifier for the payment. | identifier, as text | the source states none, or not applicable to this row |
| 6 | `source_record_id` | Source record ID | The record's identifier in that source. | list, separated by | | the source states none, or not applicable to this row |
| 7 | `recipient_name` (was `recipient_entity_name`) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. | text | the source states none, or not applicable to this row |
| 8 | `beneficiary_entity_id` | Beneficiary ID | The identifier of the beneficiary where it differs from the recipient. | identifier, as text | the source states none, or not applicable to this row |
| 9 | `beneficiary_name` (was `beneficiary_entity_name`) | Beneficiary | Who the payment is for, where different from the recipient. | text | the source states none, or not applicable to this row |
| 10 | `payer_entity_id` | Payer ID | The identifier of the payer. | identifier, as text | the source states none, or not applicable to this row |
| 11 | `payer_name` (was `payer_entity_name`) | Payer | Who made the payment (a federal office, a state). | text | the source states none, or not applicable to this row |
| 12 | `operator_entity_id` | Operator ID | The identifier of the related operator, where a source supports one. | identifier, as text | the source states none, or not applicable to this row |
| 13 | `operator_name` (was `operator_entity_name`) | Operator | The related operator's name, where a source supports one. | text | the source states none, or not applicable to this row |
| 14 | `related_asset_ids` | Related assets | The wells, tracts or leases the payment relates to, where a source names them; empty today and kept for when one does. | list, separated by | | the source states none, or not applicable to this row |
| 15 | `revenue_type` | Revenue type | Royalty, severance tax share, reclamation fee distribution, and so on. | text | the source states none, or not applicable to this row |
| 16 | `resource_type` | Resource | Oil and gas, coal, timber, minerals. | text | the source states none, or not applicable to this row |
| 17 | `commodity` | Commodity | The commodity, as the source names it. | text | the source states none, or not applicable to this row |
| 18 | `product` | Product | The product, where the source states one below the commodity. | text | the source states none, or not applicable to this row |
| 19 | `mineral_lease_type` | Mineral lease type | The lease type, where the source states it. | text | the source states none, or not applicable to this row |
| 20 | `period_type` | Period covered | Whether the payment covers a fiscal year, a month, or is dated only by payment. | text | the source states none, or not applicable to this row |
| 21 | `period_start` | Period start | Start of the period the payment covers, where stated. | date (YYYY-MM-DD) | the source states no date |
| 22 | `period_end` | Period end | End of that period. | date (YYYY-MM-DD) | the source states no date |
| 23 | `payment_date` | Payment date | When the payment was made. | date (YYYY-MM-DD) | the source states no date |
| 24 | `amount_usd` | Amount | Dollars paid. The sign column says what a negative means. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 25 | `amount_usd_real2025` | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 26 | `measurement_status` | Actual or estimated | Whether the amount is an actual payment or an estimate. | text | the source states none, or not applicable to this row |
| 27 | `aggregation_level` | Aggregation level | Whether the amount is specific to the entity, a regional aggregate or a countrywide aggregate. An aggregate is never assigned to one tribe. | text | the source states none, or not applicable to this row |
| 28 | `amount_sign_meaning` | What the sign means | How to read a negative amount (a correction, a recoupment). | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 29 | `land_status` | Land status | Trust or fee land, where the source states it. | text | the source states none, or not applicable to this row |
| 30 | `allocation_formula` | Allocation formula | The rule that determined the amount, where the source states it. | text | the source states none, or not applicable to this row |
| 31 | `allocation_formula_effective_start` | Allocation rule effective from | When the allocation rule took effect. | date (YYYY-MM-DD) | the source states no date |
| 32 | `allocation_formula_effective_end` | Allocation rule effective to | When the allocation rule ceased to apply. | date (YYYY-MM-DD) | the source states no date |
| 33 | `allocation_formula_source_url` | Formula source | Where that rule is published. | web address | the source states none, or not applicable to this row |
| 34 | `geography_note` | Place | What the source says about where the revenue arose. | text | the source states none, or not applicable to this row |
| 35 | `attribution_status` (was `entity_attribution_status`) | Attribution status | Whether the row is keyed to a Native entity, to an aggregate, or unresolved. A blank Cedar ID has a stated reason here. | text | the source states none, or not applicable to this row |
| 36 | `source_system` | Source system | Which source system the record came from. | text | the source states none, or not applicable to this row |
| 37 | `source_url` | Source | Where the payment is recorded. | web address | the source states none, or not applicable to this row |
| 38 | `research_note` | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. | text | the source states none, or not applicable to this row |

## Missing values

A blank is never zero and never an invented date. Beyond the column-level rules above:

- A blank `cedar_uid` with `attribution_status` naming an aggregate means the source suppressed the entity, not that no tribe received revenue.
- Blank `period_start` and `period_end` mean the source states a date but no period.
- `related_asset_ids` is empty today and kept for when a source names assets.

## Limitations

- An aggregate row is never assigned to a tribe: `aggregation_level` is entity_specific, regional or countrywide.
- Royalties, distributions, reclamation grants, budgets, announced allocations and actual payments are different `revenue_type` and `measurement_status` values and are compared only within a kind.
- The same financial event can appear in Federal Funding (a reclamation grant, say); the cross-reference is owed, and until it ships the two collections are not added.

## Suitable analyses

- Entity-specific actual payments by year, resource and revenue type.
- Aggregate series by region or nationally, kept apart from entity-specific rows.
- Allocation rules in force by period.

## Unsafe aggregations

- Adding entity-specific rows to regional or countrywide aggregates, or aggregates to each other across levels.
- Adding an announced allocation to an actual payment.
- Reading the absence of a named recipient as zero tribal revenue.

## What is still owed

Nothing beyond the grain and harmonization work named above.

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Tribal Natural Resource Revenue" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** Attribution routes through a party table rather than a single owner column, because one payment can involve the tribal government, allottees, an enterprise, an operator and a trust account at once. Where Interior suppresses the entity by law the row is published as an aggregate and labelled as one — 88.1% (9,791 national plus 167 state of 11,305 rows) of rows are aggregate for that reason, and none are unattributed for want of effort. Individual allottee detail is never published: Osage rows carry a class recipient at a per-headright rate, and the headright divisor is used as a check, never as a multiplier.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

