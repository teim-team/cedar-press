# Native-Owned Businesses: a researcher's guide

Collection `owned` · public file `owned.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Firms certified or listed as Native-owned by a tribal certifying authority — TERO vendor lists, Indian preference registers, tribal business licences and tribal enterprise registers — harmonised across nations into one schema.

## Population

Firms certified or listed as Native-owned by a certifying authority: TERO vendor lists, Indian preference registers, tribal business licences and tribal enterprise registers, harmonized across nations into one schema. The strength of each certification is preserved rather than flattened: a firm certified at 100% enrolled-member ownership, one on an any-Native list, one qualifying through a shareholder's spouse or descendant, and a vendor with no ownership relation are different claims on the same scale (collection descriptor).

## One row is

**Today:** One business certified or listed as Native-owned by a certifying authority (no sample is published in this repository yet; the flagship is one of the nineteen samples still to be added).

**When the specification is applied:** One supported business, enriched by every directory listing whose identity is verified; certification by two authorities is one business, and same-name businesses are never merged without evidence.

**Grain change:** Owed (§15): the map for this table is written when its sample lands, after `python scripts/import_cedar_manifest.py --audit` has run (the collection's supporting tables carried withheld names and were struck on 2026-09-05).

## Key identifiers

`business_id` is the business's own identifier; an existing business Cedar ID is used only where the identity system already assigns one. Certifying authorities are named in `listing_authority`.

## Sources and coverage

**Sources:** Tribal TERO offices, business licensing departments and enterprise registers, harvested from each nation's own publication. Contributing authorities are acknowledged in every release.

**Rows in the flagship table as released (recorded 2026-09-04):** 4,273. This is the count the release recorded for `native_owned_businesses.csv`, not the sum of the collection's 8 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`observation_date` is when Cedar observed the listing; `certification_date` and `certification_expiry_date` are stated only where the authority states them. Current listings are not historical coverage. `city` and `state` are the business's publishable location.

## Entity relationships

The opening block of every row is `cedar_uid`, `cedar_entity_name`, `cedar_entity_type` and `cedar_entity_role`. `cedar_entity_role` is `certifying_authority`: the nation or office that lists or certifies the business, never its owner. Individual Native ownership is not tribal-government ownership.

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

Multiple directory listings enrich one business record where identity is verified; certification by two authorities is one business; same-name businesses are never merged without evidence.

## Field dictionary

The field dictionary is written when this collection's flagship sample lands in the repository and its field map is decided. The approved opening block and the specification's field list for it:

- `cedar_uid`
- `cedar_entity_name`: The certifying authority's register name.
- `cedar_entity_type`: The certifying authority's register class.
- `cedar_entity_role`: A certifying nation's uid is an associated link labelled certifying_authority, not owner.
- `business_id`: The business's own id; an existing business Cedar uid only where the identity system already assigns one.
- `business_name`: Withheld where the publication policy withholds it; never reintroduced through aliases, source text or fallback fields.
- `trade_name`: Where publishable.
- `business_category`: Normalized across directories, with the issuing authority's own terminology kept beside it.
- `services`
- `city`: Publishable business location.
- `state`
- `contact_channels`: Publishable channels only.
- `listing_authority`: The directory or certifying authority.
- `program`: The certification or preference program, in the authority's terms.
- `certification_status`
- `certification_date`: Where stated.
- `certification_expiry_date`: Where stated.
- `observation_date`: When Cedar observed the listing; not historical coverage.
- `source_url`

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

Target columns the specification asks for that the terminal has not yet built from the full table. Each ships blank-free, not blank: it is absent until it exists.

- `business_id` (pending:sample): The business's own id; an existing business Cedar uid only where the identity system already assigns one.
- `business_name` (pending:sample): Withheld where the publication policy withholds it; never reintroduced through aliases, source text or fallback fields.
- `trade_name` (pending:sample): Where publishable.
- `business_category` (pending:sample): Normalized across directories, with the issuing authority's own terminology kept beside it.
- `services` (pending:sample): see the field map
- `city` (pending:sample): Publishable business location.
- `state` (pending:sample): see the field map
- `contact_channels` (pending:sample): Publishable channels only.
- `listing_authority` (pending:sample): The directory or certifying authority.
- `program` (pending:sample): The certification or preference program, in the authority's terms.
- `certification_status` (pending:sample): see the field map
- `certification_date` (pending:sample): Where stated.
- `certification_expiry_date` (pending:sample): Where stated.
- `observation_date` (pending:sample): When Cedar observed the listing; not historical coverage.
- `source_url` (pending:sample): see the field map

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Native-Owned Businesses" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** The strength of each certification is preserved rather than flattened, because the authorities do not mean the same thing: a firm certified at 100% enrolled-member ownership, one on an any-Native list, one qualifying through a shareholder's spouse or descendant, and a vendor with no ownership relation at all are recorded as different claims on the same scale. The relation published is affiliation with a named nation, not an ownership assertion the source never made. Sources whose terms forbid reuse are excluded by every route and named as excluded.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

