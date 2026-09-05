# Native Nonprofits: a researcher's guide

Collection `nonprofits` · public file `nonprofits.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Native-controlled, tribally affiliated and Native-serving nonprofit organisations, with EIN, financial scale and filing status.

## Population

Nonprofit organizations in the IRS Business Master File that are Native-led, tribally affiliated or Native-serving, with their EIN, BMF financial measures and filing status. Native status is established from what an organization says about itself in its own filing, never from an NTEE code and never from a name (collection descriptor). Tribal instrumentalities largely do not file under IRC section 7871, so the largest tribal institutions can be absent by law.

## One row is

**Today:** One nonprofit organization in the IRS Business Master File that is Native-led or tribally controlled, with the Native entity it is linked to.

**When the specification is applied:** One organization (EIN) with its BMF snapshot; financial analysis rows are organization-EIN-reporting-period (np_financials.csv), and a directory-only row is distinguishable and gets no invented year.

**Grain change:** Owed (§14): the organization-EIN-reporting-period financial table is np_financials.csv in the workspace; whether it ships inside this file under a record_type or as the collection's financial companion is the terminal's call after measuring compatible periods.

## Key identifiers

`ein` is the organization's Employer Identification Number, kept as text with leading zeros. `inclusion_basis` says why the organization is in Cedar.

## Sources and coverage

**Sources:** IRS Business Master File; Form 990 e-file returns; the 990-N e-Postcard corpus; ProPublica Nonprofit Explorer.

**Rows in the flagship table as released (recorded 2026-09-04):** 12,764. This is the count the release recorded for `np_orgs.csv`, not the sum of the collection's 14 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`tax_period` is the reporting period the BMF amounts belong to; `bmf_snapshot_date` is when the BMF snapshot was taken and is a retrieval date, not a tax year; `irs_ruling_month` is when the IRS ruled on exemption. `city` and `state` are the organization's address.

## Entity relationships

The opening block of every row is `cedar_uid`, `cedar_entity_name`, `cedar_entity_type` and `cedar_entity_role`. `cedar_entity_role` is the associated Native entity; `native_relationship` (owed) will say whether the organization is controlled by, serves, or is the linked entity. `org_entity_class` is the organization's own kind (ANC, tribal college, CDFI) and is distinct from `cedar_entity_type`, the linked entity's class. A nonprofit serving several tribes is not assigned to one by a shared word in its name; `attribution_method` and `attribution_tier` say how the link was made.

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

A newer BMF snapshot is not a new annual financial observation. The organization-EIN-reporting-period financial table (the collection's `np_financials.csv`) is where financial analysis belongs; whether it ships inside this file or beside it is owed (§14).

## Field dictionary

The approved header, in order (28 columns, of which 1 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `cedar_entity_name` (was `cedar_spine_canonical_name`) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 3 | `cedar_entity_type` (was `cedar_spine_entity_class`) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 4 | `cedar_entity_role` | Entity role | Why the entity is on this row: associated Native entity. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 5 | `ein` (was `EIN`) | EIN | The organization's Employer Identification Number. | identifier, as text | the source states none, or not applicable to this row |
| 6 | `org_name` | Organization | The organization's name as the IRS records it. | text | the source states none, or not applicable to this row |
| 7 | `org_entity_class` (was `cedar_native_entity_class`) | Organization type | Whether the organization is itself a tribe, an ANC, a Native organization. | text | the source states none, or not applicable to this row |
| 8 | `native_relationship` | native relationship | controlled_by, serves, or is (a tribal government's own organization): the relationship to the linked entity, distinct from a name match. | — | owed: not in the file until the terminal builds it |
| 9 | `classification_ruling` | Relationship to the entity | Whether the organization is tribally controlled, tribally affiliated, or unruled. | text | the source states none, or not applicable to this row |
| 10 | `inclusion_basis` (was `disposition`) | Inclusion basis | Why the organization is in Cedar: verified strictly, verified, or a candidate. | text | the source states none, or not applicable to this row |
| 11 | `city` | City | Its city. | text | the source states none, or not applicable to this row |
| 12 | `state` | State | The organization's state. | text | the source states none, or not applicable to this row |
| 13 | `ntee_code` | NTEE code | The IRS activity code for what the organization does. | text | the source states none, or not applicable to this row |
| 14 | `bmf_status` | IRS status code | The organization's status code in the Business Master File, defined in the dictionary. | number | the source states none, or not applicable to this row |
| 15 | `bmf_subsection` | Tax subsection | The 501(c) subsection (3 for charities). | number | the source states none, or not applicable to this row |
| 16 | `bmf_filing_req_cd` | Filing requirement code | Which return the IRS requires, as a code defined in the dictionary. | number | the source states none, or not applicable to this row |
| 17 | `bmf_foundation_cd` | Foundation code | The IRS foundation classification code, defined in the dictionary. | number | the source states none, or not applicable to this row |
| 18 | `irs_ruling_month` (was `bmf_irs_ruling_yyyymm`) | IRS ruling date | When the IRS recognized the organization (year and month). | number | the source states none, or not applicable to this row |
| 19 | `filing_tier` (was `tier`) | Filing tier | Which IRS return it files: full 990, 990-EZ or 990-N. | text | the source states none, or not applicable to this row |
| 20 | `tax_period` (was `bmf_tax_period`) | Latest tax period | The most recent tax period in the file. | text | the source states none, or not applicable to this row |
| 21 | `bmf_revenue_amt` | Revenue | Revenue in the latest return the IRS holds. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 22 | `bmf_income_amt` | Income | Income in that return. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 23 | `bmf_asset_amt` | Assets | Assets in that return. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 24 | `bmf_snapshot_date` (was `bmf_vintage_fetched`) | IRS file date | The date of the IRS file these figures come from. | date (YYYY-MM-DD) | the source states no date |
| 25 | `attribution_method` (was `entity_match_method`) | Attribution method | How the organization was linked to the Native entity. | text | the source states none, or not applicable to this row |
| 26 | `attribution_tier` (was `entity_tier`) | Match confidence | Cedar's confidence in the link to the entity: A is strongest. | text | the source states none, or not applicable to this row |
| 27 | `source_system` (was `source_dataset`) | Source system | The source: the IRS Exempt Organizations Business Master File. | text | the source states none, or not applicable to this row |
| 28 | `source_url` | Source | The IRS Business Master File. | web address | the source states none, or not applicable to this row |

## Missing values

A blank is never zero and never an invented date. Beyond the column-level rules above:

- A blank `cedar_uid` means the organization is in the population on its own filing but is not linked to one Native entity.
- A blank financial measure means the BMF carries none for the organization (a 990-N filer, say), never zero.

## Limitations

- `bmf_revenue_amt`, `bmf_income_amt` and `bmf_asset_amt` are the Business Master File's own measures under their own names; `bmf_income_amt` is not net income and none is relabelled until the source definition is confirmed.
- IRS codes (`bmf_status`, `bmf_subsection`, `bmf_filing_req_cd`, `bmf_foundation_cd`) are defined in the dictionary and carry the IRS's meaning.
- Place-named organizations that are not Native are excluded rather than left to inflate totals.

## Suitable analyses

- Organizations by state, NTEE code, filing tier and linked entity.
- BMF financial scale by organization, each measure on its own.
- Ruling years and exemption subsections.

## Unsafe aggregations

- Adding revenue, income and asset measures together, or across organizations with different `tax_period` values as if they were one year.
- Treating a BMF snapshot date as a fiscal year.
- Reading a name match as Native control.

## What is still owed

Target columns the specification asks for that the terminal has not yet built from the full table. Each ships blank-free, not blank: it is absent until it exists.

- `native_relationship` (pending:classification): controlled_by, serves, or is (a tribal government's own organization): the relationship to the linked entity, distinct from a name match.

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Native Nonprofits" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** Native status is established from what an organisation says about itself in its own filing, never from an NTEE code and never from a name. A mission statement naming a specific nation is a stronger claim than one describing Native-serving work generally, and the two are recorded separately. The dataset states plainly what it cannot see: tribal instrumentalities largely do not file 990s under IRC section 7871, so the largest tribal institutions can be absent by law, and place-named organisations that are not Native are identified and excluded rather than left to inflate the totals — 4,651 of 12,764 rows are excluded by a prior ruling. The disposition of a row is carried in `funnel_stage`, not in `classification_ruling`, which holds an explicit ruling for only 398 rows; 1,831 rows sit at `canonical_name_match` as unruled candidates, and the token the match turned on ships with each so a reader can see the ones that are wrong rather than take the tier on trust.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

