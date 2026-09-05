# Native-Owned Businesses: a researcher's guide

Collection `owned` · public file `owned.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Firms certified or listed as Native-owned by a tribal certifying authority — TERO vendor lists, Indian preference registers, tribal business licences and tribal enterprise registers — harmonised across nations into one schema.

## Population

Firms certified or listed as Native-owned by a certifying authority: TERO vendor lists, Indian preference registers, tribal business licences and tribal enterprise registers, harmonized across nations into one schema. The strength of each certification is preserved rather than flattened: a firm certified at 100% enrolled-member ownership, one on an any-Native list, one qualifying through a shareholder's spouse or descendant, and a vendor with no ownership relation are different claims on the same scale (collection descriptor).

## One row is

One business-directory or certification listing, as today; distinct certifications are not merged into a business snapshot.

This pass changes columns, never rows: no aggregation, deduplication, change of publication eligibility or reassignment of Cedar IDs.

**Note:** The 53-column baseline is the builder's declaration, not a verified public export, and no sample is in this repository. The field-by-field decisions are written when the sample lands, after `python scripts/import_cedar_manifest.py --audit` has run; the publication restrictions apply to every field before any preview, download, search index or Cedar answer.

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

The field dictionary is written when this collection's flagship sample lands in the repository and its field map is decided. The approved opening block and the specification's field list for it:

- `cedar_uid`
- `canonical_name`: The certifying authority's register name.
- `entity_class`: The certifying authority's register class.
- `cedar_entity_role`: certifying_authority, never owner; a missing business identity is never filled with the nation's uid.
- `business_source_id`
- `business_name`
- `business_entity_id`
- `certifying_authority_entity_id`
- `certifying_authority_name`
- `program_name`
- `directory_type`
- `assertion_class`
- `identity_scope`
- `identity_claim_text`
- `ownership_percent`
- `ownership_threshold_min`
- `certification_number`
- `certification_tier`
- `certification_start`
- `certification_expiration`
- `business_license_number`
- `service_category`
- `naics_code`
- `city`
- `state`
- `source_edition`
- `source_last_updated`
- `first_seen`
- `last_seen`
- `is_current`
- `source_url`
- `research_note`: A concise factual qualification that changes interpretation; blank when unnecessary. Built blank at write time.

## Missing values

A blank is never zero and never an invented date. Beyond the column-level rules above:

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

Target columns the specification asks for that the terminal has not yet built from the full table. Each is absent until it exists, never blank.

- `business_source_id` (pending:sample): see the field map
- `business_name` (pending:sample): see the field map
- `business_entity_id` (pending:sample): see the field map
- `certifying_authority_entity_id` (pending:sample): see the field map
- `certifying_authority_name` (pending:sample): see the field map
- `program_name` (pending:sample): see the field map
- `directory_type` (pending:sample): see the field map
- `assertion_class` (pending:sample): see the field map
- `identity_scope` (pending:sample): see the field map
- `identity_claim_text` (pending:sample): see the field map
- `ownership_percent` (pending:sample): see the field map
- `ownership_threshold_min` (pending:sample): see the field map
- `certification_number` (pending:sample): see the field map
- `certification_tier` (pending:sample): see the field map
- `certification_start` (pending:sample): see the field map
- `certification_expiration` (pending:sample): see the field map
- `business_license_number` (pending:sample): see the field map
- `service_category` (pending:sample): see the field map
- `naics_code` (pending:sample): see the field map
- `city` (pending:sample): see the field map
- `state` (pending:sample): see the field map
- `source_edition` (pending:sample): see the field map
- `source_last_updated` (pending:sample): see the field map
- `first_seen` (pending:sample): see the field map
- `last_seen` (pending:sample): see the field map
- `is_current` (pending:sample): see the field map
- `source_url` (pending:sample): see the field map

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Native-Owned Businesses" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** The strength of each certification is preserved rather than flattened, because the authorities do not mean the same thing: a firm certified at 100% enrolled-member ownership, one on an any-Native list, one qualifying through a shareholder's spouse or descendant, and a vendor with no ownership relation at all are recorded as different claims on the same scale. The relation published is affiliation with a named nation, not an ownership assertion the source never made. Sources whose terms forbid reuse are excluded by every route and named as excluded.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

