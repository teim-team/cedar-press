# Native Nonprofits: a researcher's guide

Collection `nonprofits` · public file `nonprofits.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Native-controlled, tribally affiliated and Native-serving nonprofit organisations, with EIN, financial scale and filing status.

## Population

Nonprofit organizations in the IRS Business Master File that are Native-led, tribally affiliated or Native-serving, with their EIN, BMF financial measures and filing status. Native status is established from what an organization says about itself in its own filing, never from an NTEE code and never from a name (collection descriptor). Tribal instrumentalities largely do not file under IRC section 7871, so the largest tribal institutions can be absent by law.

## One row is

One organization snapshot, as today; not an organization-year panel.

This pass changes columns, never rows: no aggregation, deduplication, change of publication eligibility or reassignment of Cedar IDs.

## Key identifiers

`ein` is the organization's Employer Identification Number, kept as text with leading zeros. `inclusion_basis` says why the organization is in Cedar.

## Sources and coverage

**Sources:** IRS Business Master File; Form 990 e-file returns; the 990-N e-Postcard corpus; ProPublica Nonprofit Explorer.

**Rows in the flagship table as released (recorded 2026-09-04):** 12,764. This is the count the release recorded for `np_orgs.csv`, not the sum of the collection's 14 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`tax_period` is the reporting period the BMF amounts belong to; `bmf_snapshot_date` is when the BMF snapshot was taken and is a retrieval date, not a tax year; `irs_ruling_month` is when the IRS ruled on exemption. `city` and `state` are the organization's address.

## Entity relationships

The opening block of every row is `cedar_uid`, `canonical_name`, `entity_class` and `cedar_entity_role`. `cedar_entity_role` is the associated Native entity; `inclusion_category` says whether the organization is Native-serving, Native-controlled, a tribal government's own organization or a candidate, and `entity_link_status` how firmly the link is established, each consolidated through a documented crosswalk (owed). `organization_entity_class` is the organization's own kind (ANC, tribal college, CDFI) and is distinct from `entity_class`, the linked entity's class. A nonprofit serving several tribes is not assigned to one by a shared word in its name.

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

A newer BMF snapshot is not a new annual financial observation. The organization-EIN-reporting-period financial table (the collection's `np_financials.csv`) is where financial analysis belongs; whether it ships inside this file or beside it is owed (§14).

## Field dictionary

The approved header, in the owner's exact order (24 columns, of which 2 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros; a JSON array cell is one list, aligned with its neighbours where the dictionary says so.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `canonical_name` (was `cedar_spine_canonical_name`) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. | text | the source states none, or not applicable to this row |
| 3 | `entity_class` (was `cedar_spine_entity_class`) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. | text | the source states none, or not applicable to this row |
| 4 | `cedar_entity_role` | Entity role | Why the entity is on this row: associated Native entity. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 5 | `ein` (was `EIN`) | EIN | The organization's Employer Identification Number. | identifier, as text | the source states none, or not applicable to this row |
| 6 | `organization_name` (was `org_name`) | Organization | The organization's name as the IRS records it. | text | the source states none, or not applicable to this row |
| 7 | `organization_entity_class` (was `cedar_native_entity_class`) | Organization type | Whether the organization is itself a tribe, an ANC, a Native organization. | text | the source states none, or not applicable to this row |
| 8 | `inclusion_category` | inclusion category | Native-serving, Native-controlled, tribal-government or candidate, through a documented crosswalk. | — | owed: not in the file until the terminal builds it |
| 9 | `city` | City | Its city. | text | the source states none, or not applicable to this row |
| 10 | `state` | State | The organization's state. | text | the source states none, or not applicable to this row |
| 11 | `ntee_code` | NTEE code | The IRS activity code for what the organization does. | text | the source states none, or not applicable to this row |
| 12 | `irs_status` (was `bmf_status`) | IRS status code | The organization's status code in the Business Master File, defined in the dictionary. | number | the source states none, or not applicable to this row |
| 13 | `irs_subsection` (was `bmf_subsection`) | Tax subsection | The 501(c) subsection (3 for charities). | number | the source states none, or not applicable to this row |
| 14 | `irs_foundation_code` (was `bmf_foundation_cd`) | Foundation code | The IRS foundation classification code, defined in the dictionary. | number | the source states none, or not applicable to this row |
| 15 | `irs_ruling_month` (was `bmf_irs_ruling_yyyymm`) | IRS ruling date | When the IRS recognized the organization (year and month). | number | the source states none, or not applicable to this row |
| 16 | `tax_period` (was `bmf_tax_period`) | Latest tax period | The most recent tax period in the file. | text | the source states none, or not applicable to this row |
| 17 | `bmf_revenue_usd` (was `bmf_revenue_amt`) | Revenue | Revenue in the latest return the IRS holds. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 18 | `bmf_assets_usd` (was `bmf_asset_amt`) | Assets | Assets in that return. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 19 | `bmf_income_usd` (was `bmf_income_amt`) | Income | Income in that return. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 20 | `bmf_as_of_date` (was `bmf_vintage_fetched`) | IRS file date | The date of the IRS file these figures come from. | date (YYYY-MM-DD) | the source states no date |
| 21 | `entity_link_status` | entity link status | One linkage status through a documented crosswalk. | — | owed: not in the file until the terminal builds it |
| 22 | `source_system` (was `source_dataset`) | Source system | The source: the IRS Exempt Organizations Business Master File. | text | the source states none, or not applicable to this row |
| 23 | `source_url` | Source | The IRS Business Master File. | web address | the source states none, or not applicable to this row |
| 24 | `research_note` | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. | text | the source states none, or not applicable to this row |

Until the combined columns exist, the file carries their sources, each with its own label:

- `classification_ruling` (Relationship to the entity) combines into `inclusion_category`: Whether the organization is tribally controlled, tribally affiliated, or unruled.
- `disposition` (Inclusion basis) combines into `inclusion_category`: Why the organization is in Cedar: verified strictly, verified, or a candidate.
- `entity_tier` (Match confidence) combines into `entity_link_status`: Cedar's confidence in the link to the entity: A is strongest.
- `cedar_link_tier` (Cedar link tier) combines into `entity_link_status`: Shown until the combined column replaces it.
- `key_review_disposition` (Key review disposition) combines into `entity_link_status`: Shown until the combined column replaces it.

## Missing values

A blank is never zero and never an invented date. A blank JSON-list cell means unknown; `[]` means known to be empty (no additional source, no additional institution); a null element inside a list is one member the evidence names but does not resolve. Identifiers and codes are text with their leading zeros. Beyond the column-level rules above:

- A blank `cedar_uid` means the organization is in the population on its own filing but is not linked to one Native entity.
- A blank financial measure means the BMF carries none for the organization (a 990-N filer, say), never zero.

## Limitations

- `bmf_revenue_usd`, `bmf_income_usd` and `bmf_assets_usd` are the Business Master File's own measures under their own names; `bmf_income_usd` is not net income and none is relabelled until the source definition is confirmed.
- IRS codes (`irs_status`, `irs_subsection`, `bmf_filing_req_cd`, `irs_foundation_code`) are defined in the dictionary and carry the IRS's meaning.
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

Identifier retirement findings that stop this dataset until they are settled (see `docs/IDENTIFIER_RETIREMENT_2026-09-05.md`):

- `entity_id`: unknown: an earlier or different entity link that disagrees with cedar_uid on at least one row (adjudicate).
- `cedar_spine_entity_id`: the spine entity the organization was keyed to before a redirect that cedar_uid reflects and this column does not, on at least one row (adjudicate).

Target columns the specification asks for that the terminal has not yet built from the full table. Each is absent until it exists, never blank.

- `inclusion_category` (combine:classification_ruling\|disposition): Native-serving, Native-controlled, tribal-government or candidate, through a documented crosswalk.
- `entity_link_status` (combine:entity_tier\|cedar_link_tier\|key_review_disposition): One linkage status through a documented crosswalk.

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Native Nonprofits" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** Native status is established from what an organisation says about itself in its own filing, never from an NTEE code and never from a name. A mission statement naming a specific nation is a stronger claim than one describing Native-serving work generally, and the two are recorded separately. The dataset states plainly what it cannot see: tribal instrumentalities largely do not file 990s under IRC section 7871, so the largest tribal institutions can be absent by law, and place-named organisations that are not Native are identified and excluded rather than left to inflate the totals — 4,651 of 12,764 rows are excluded by a prior ruling. The disposition of a row is carried in `funnel_stage`, not in `classification_ruling`, which holds an explicit ruling for only 398 rows; 1,831 rows sit at `canonical_name_match` as unruled candidates, and the token the match turned on ships with each so a reader can see the ones that are wrong rather than take the tier on trust.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

