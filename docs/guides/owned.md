# Native-Owned Businesses: a researcher's guide

Collection `owned` · public file `owned.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Firms certified or listed as Native-owned by a tribal certifying authority — TERO vendor lists, Indian preference registers, tribal business licences and tribal enterprise registers — harmonised across nations into one schema.

## Population

Firms certified or listed as Native-owned by a certifying authority: TERO vendor lists, Indian preference registers, tribal business licences and tribal enterprise registers, harmonized across nations into one schema. The strength of each certification is preserved rather than flattened: a firm certified at 100% enrolled-member ownership, one on an any-Native list, one qualifying through a shareholder's spouse or descendant, and a vendor with no ownership relation are different claims on the same scale (collection descriptor).

## One row is

One business-directory or certification listing, as the builder declares it; distinct certifications are not collapsed into an invented business snapshot.

This pass changes columns, never rows: no aggregation, deduplication, change of publication eligibility or reassignment of Cedar IDs.

**Note:** The 53 fields are the builder's CLEAN_COLUMNS declaration, not a shipped public export; no sample is in the repository. The publication gate (consent_status, publishable, withheld_fields, business_name_is_person_name, the WITHHELD list of owner names, contact and website fields) applies to every row before any preview, download, search index or Cedar answer; retiring the gate's columns does not retire the gate.

## Key identifiers

`business_id` is the business's own identifier; an existing business Cedar ID is used only where the identity system already assigns one. Certifying authorities are named in `listing_authority`.

## Sources and coverage

**Sources:** Tribal TERO offices, business licensing departments and enterprise registers, harvested from each nation's own publication. Contributing authorities are acknowledged in every release.

**Rows in the flagship table as released (recorded 2026-09-04):** 4,273. This is the count the release recorded for `native_owned_businesses.csv`, not the sum of the collection's 8 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`observation_date` is when Cedar observed the listing; `certification_date` and `certification_expiry_date` are stated only where the authority states them. Current listings are not historical coverage. `city` and `state` are the business's publishable location.

## Entity relationships

The opening block of every row is `cedar_uid`, `canonical_name`, `entity_class` and `cedar_entity_role`. `cedar_entity_role` is `certifying_authority`: the nation or office that lists or certifies the business, never its owner. Individual Native ownership is not tribal-government ownership.

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

Multiple directory listings enrich one business record where identity is verified; certification by two authorities is one business; same-name businesses are never merged without evidence.

## Field dictionary

The approved header, in the owner's exact order (32 columns, of which 0 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros; a JSON array cell is one list, aligned with its neighbours where the dictionary says so.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. | text | the source states none, or not applicable to this row |
| 3 | `entity_class` | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. | text | the source states none, or not applicable to this row |
| 4 | `cedar_entity_role` | Entity role | Why the entity is on this row: certifying_authority. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 5 | `business_source_id` | Business source id |  | identifier, as text | the source states none, or not applicable to this row |
| 6 | `business_name` (was `business_name_raw`) | Business name |  | text | the source states none, or not applicable to this row |
| 7 | `business_entity_id` | Business entity id |  | identifier, as text | the source states none, or not applicable to this row |
| 8 | `certifying_authority_entity_id` | Certifying authority entity id |  | identifier, as text | the source states none, or not applicable to this row |
| 9 | `certifying_authority_name` | Certifying authority name |  | text | the source states none, or not applicable to this row |
| 10 | `program_name` (was `programme_name`) | Program name |  | text | the source states none, or not applicable to this row |
| 11 | `directory_type` | Directory type |  | text | the source states none, or not applicable to this row |
| 12 | `assertion_class` | Assertion class |  | text | the source states none, or not applicable to this row |
| 13 | `identity_scope` | Identity scope |  | text | the source states none, or not applicable to this row |
| 14 | `identity_claim_text` | Identity claim text |  | text | the source states none, or not applicable to this row |
| 15 | `ownership_percent` | Ownership percent |  | text | the source states none, or not applicable to this row |
| 16 | `ownership_threshold_min` | Ownership threshold min |  | text | the source states none, or not applicable to this row |
| 17 | `certification_number` | Certification number |  | identifier, as text | the source states none, or not applicable to this row |
| 18 | `certification_tier` | Certification tier |  | text | the source states none, or not applicable to this row |
| 19 | `certification_start` | Certification start |  | text | the source states none, or not applicable to this row |
| 20 | `certification_expiration` | Certification expiration |  | text | the source states none, or not applicable to this row |
| 21 | `business_license_number` | Business license number |  | identifier, as text | the source states none, or not applicable to this row |
| 22 | `service_category` (was `service_category_raw`) | Service category |  | text | the source states none, or not applicable to this row |
| 23 | `naics_code` (was `naics`) | Naics code |  | text | the source states none, or not applicable to this row |
| 24 | `city` | City |  | text | the source states none, or not applicable to this row |
| 25 | `state` (was `state_province`) | State |  | text | the source states none, or not applicable to this row |
| 26 | `source_edition` | Source edition |  | text | the source states none, or not applicable to this row |
| 27 | `source_last_updated` | Source last updated |  | text | the source states none, or not applicable to this row |
| 28 | `first_seen` | First seen |  | text | the source states none, or not applicable to this row |
| 29 | `last_seen` | Last seen |  | text | the source states none, or not applicable to this row |
| 30 | `is_current` | Is current |  | yes or no (1 or 0) | not stated; 0 is no |
| 31 | `source_url` | Source | The official page for this record, written into the file so it cites itself. | web address | the source states none, or not applicable to this row |
| 32 | `research_note` | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. | text | the source states none, or not applicable to this row |

## Missing values

A blank is never zero and never an invented date. A blank JSON-list cell means unknown; `[]` means known to be empty (no additional source, no additional institution); a null element inside a list is one member the evidence names but does not resolve. Identifiers and codes are text with their leading zeros. Beyond the column-level rules above:

- A blank name means withheld under the publication policy, with the reason recorded.
- Blank certification dates mean the authority states none.

## Limitations

- The publication policy withholds a firm's name where its legal name is a person's and no consent is recorded; a withheld name is never reintroduced through aliases, source text or fallback fields, in the preview, the download, the search index or Cedar's answers.
- Absence from the roster does not establish that a business is not Native-owned.
- This collection's flagship sample is not yet in the repository; its field map and dictionary are written when it lands, after the withholding audit has run (§15).

## Suitable analyses

- Businesses by certifying authority, program, category and state.
- Which authorities certify which categories, in the authority's own terms.

## Unsafe aggregations

- Treating different programs as equivalent certifications.
- Counting one business twice for two certifications.
- Reading the roster as a census of Native-owned businesses.

## What is still owed

Identifier retirement findings that stop this dataset until they are settled (see `docs/IDENTIFIER_RETIREMENT_2026-09-05.md`):

- `nation_id`: the certifying nation, in a namespace the declaration does not name (adjudicate).

Nothing beyond the grain and harmonization work named above.

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Native-Owned Businesses" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** The strength of each certification is preserved rather than flattened, because the authorities do not mean the same thing: a firm certified at 100% enrolled-member ownership, one on an any-Native list, one qualifying through a shareholder's spouse or descendant, and a vendor with no ownership relation at all are recorded as different claims on the same scale. The relation published is affiliation with a named nation, not an ownership assertion the source never made. Sources whose terms forbid reuse are excluded by every route and named as excluded.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

