# NEST: Native Enterprise Structures and Ties: a researcher's guide

Collection `nest` · public file `nest.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Enterprise ownership and affiliation across tribes, Alaska Native corporations, Native Hawaiian organizations, and state-recognized Native entities — the parent, the holding company and the operating company, kept as a chain rather than a flat list.

## Population

Enterprises (subsidiaries, holding companies, joint ventures, affiliates) and the Native entity that owns or is affiliated with each, built from what each owner publishes about itself: audited ANCSA annual reports, nations' own enterprise registers, ANC and NHO subsidiary directories. Ownership is recorded only where a source asserted it; a shared name or address is not evidence and does not create a row (collection descriptor).

## One row is

**Today:** One enterprise (a subsidiary, a joint venture, an affiliate) with the Native entity that owns or is affiliated with it.

**When the specification is applied:** One enterprise-owner relationship, with an effective period where known; businesses are counted by distinct enterprise_id, and an enterprise with several owners shows each.

**Grain change:** Owed (§13): ownership effective dates separated from observation dates; multiple owners visible (nest_enterprise_relations.csv holds the assertions); duplicate observations merged only on confirmed identity.

## Key identifiers

`enterprise_id` is Cedar's permanent, check-digited identifier for the enterprise; `parent_enterprise_id` names the immediate parent enterprise; `uei` and `cage_code` are the enterprise's official identifiers where the owner published them.

## Sources and coverage

**Sources:** What each owner publishes about itself: audited annual reports filed by ANCSA corporations with the Alaska Division of Banking and Securities under Alaska Statute 45.55.139, whose Principles of Consolidation note enumerates the subsidiaries by legal name; nations' own “Our Companies” and enterprise registers; ANC and NHO subsidiary directories. Publishers whose terms forbid reuse are excluded by every route and named as excluded.

**Rows in the flagship table as released (recorded 2026-09-04):** 5,820. This is the count the release recorded for `nest_enterprises.csv`, not the sum of the collection's 3 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`first_observed_year` and `last_observed_year` are when Cedar observed the relationship, not when it began or ended; `ownership_effective_start` and `ownership_effective_end` (owed) will carry the effective period where a source states it. `city` and `state_province` are the enterprise's business location.

## Entity relationships

The opening block of every row is `cedar_uid`, `cedar_entity_name`, `cedar_entity_type` and `cedar_entity_role`. `cedar_entity_role` is `ownership` or `affiliation`, from the relationship class; `relationship` is the finer type (subsidiary, joint venture, management). `parent_is_hub` says whether the immediate parent is the Native entity itself; `hierarchy_level` is the depth below it. `parent_corroboration` says whether the parent FPDS declares agrees, and a contested affiliation ships as contested, never as verified ownership; `fpds_declared_parent_name` is kept as evidence.

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

A relationship is re-observed on each source edition (`source_edition_date`). Duplicate observations are merged only on confirmed identity. Multiple owners of one enterprise are held in the collection's relations table and are owed in this file (§13); an arbitrary primary owner is never chosen.

## Field dictionary

The approved header, in order (33 columns, of which 2 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `cedar_entity_name` (was `owner_hub_name`) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 3 | `cedar_entity_type` (was `owner_hub_entity_class`) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 4 | `cedar_entity_role` (was `relation_class`) | Entity role | Why the entity is on this row: read from relationship_type: owner, or affiliated entity, of the enterprise. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 5 | `enterprise_id` | Enterprise ID | Cedar's identifier for the enterprise. | identifier, as text | the source states none, or not applicable to this row |
| 6 | `enterprise_name` | Enterprise | The enterprise's name. | text | the source states none, or not applicable to this row |
| 7 | `name_variants` (was `name_variants_observed`) | Also seen as | Other spellings of the name in the sources, separated by \|. | list, separated by | | the source states none, or not applicable to this row |
| 8 | `owner_class` | Owner kind | The owner's kind in the collection's own terms: tribal government, ANC, NHO. | text | the source states none, or not applicable to this row |
| 9 | `parent_enterprise_id` | Parent enterprise ID | The immediate parent enterprise's ID, where the parent is an enterprise rather than the Native entity itself. | identifier, as text | the source states none, or not applicable to this row |
| 10 | `parent_name` | Parent | The immediate parent, which may itself be an enterprise. | text | the source states none, or not applicable to this row |
| 11 | `parent_is_hub` | Parent is the Native entity (yes or no) | Whether the immediate parent is the Native entity itself rather than another enterprise. | yes or no (1 or 0) | not stated; 0 is no |
| 12 | `hierarchy_level` | Level | How many steps below the owner the enterprise sits. | number | the source states none, or not applicable to this row |
| 13 | `relationship` | Relationship | How the enterprise relates to the owner: wholly owned, subsidiary, affiliated, unspecified. | text | the source states none, or not applicable to this row |
| 14 | `ownership_percent_stated` | Ownership share | The percentage owned, where a source states it. | text | the source states none, or not applicable to this row |
| 15 | `ownership_effective_start` | ownership effective start | When the ownership began, where a source states it. | — | owed: not in the file until the terminal builds it |
| 16 | `ownership_effective_end` | ownership effective end | When it ended, where a source states it. | — | owed: not in the file until the terminal builds it |
| 17 | `industry` (was `sector`) | Sector | The enterprise's sector. | text | the source states none, or not applicable to this row |
| 18 | `operating_status` (was `status`) | Status | Operating, dissolved, or unknown. | text | the source states none, or not applicable to this row |
| 19 | `city` | City | Where the enterprise is. | text | the source states none, or not applicable to this row |
| 20 | `state_province` | State | Its state or province. | text | the source states none, or not applicable to this row |
| 21 | `uei` | UEI | Its federal Unique Entity ID, where one is published. | identifier, as text | the source states none, or not applicable to this row |
| 22 | `cage_code` | CAGE code | The enterprise's CAGE code, where known. | identifier, as text | the source states none, or not applicable to this row |
| 23 | `in_federal_contracting` | Federal contractor | Whether the enterprise appears in federal contracting records (yes or no). | yes or no (1 or 0) | not stated; 0 is no |
| 24 | `first_observed_year` | First seen | The earliest year a source names the enterprise. | year | the source states no date |
| 25 | `last_observed_year` | Last seen | The latest. | year | the source states no date |
| 26 | `evidence_class` | Kind of evidence | What kind of source establishes the relationship (the owner's own list, an audited report, a resolver). | text | the source states none, or not applicable to this row |
| 27 | `evidence_human_reviewed` | Reviewed by a person | Whether a person reviewed the evidence (yes or no). | yes or no (1 or 0) | not stated; 0 is no |
| 28 | `source_count` (was `n_distinct_sources`) | Sources | How many distinct sources support the relationship. | number | the source states none, or not applicable to this row |
| 29 | `parent_corroboration` (was `fpds_parent_corroboration`) | Federal records agree | Whether the parent the enterprise declares in federal records agrees with this owner. | text | the source states none, or not applicable to this row |
| 30 | `fpds_declared_parent_name` | Parent declared in FPDS | The parent the enterprise declares in federal contracting records, kept as evidence beside Cedar's relationship. | text | the source states none, or not applicable to this row |
| 31 | `source_document` | Source document | The document, where the source is a file. | text | the source states none, or not applicable to this row |
| 32 | `source_edition_date` | Source date | The date of that source. | date (YYYY-MM-DD) | the source states no date |
| 33 | `source_url` | Source | Where the relationship is stated. | web address | the source states none, or not applicable to this row |

## Missing values

A blank is never zero and never an invented date. Beyond the column-level rules above:

- A blank `ownership_percent_stated` means the source states no percentage.
- A blank `uei` means the owner published none; Cedar does not pad with plausible matches.

## Limitations

- The file is not a census of Native enterprises; it holds what owners publish and what corroborates it.
- A firm serving a tribe is not thereby owned by it; `evidence_class` and `evidence_human_reviewed` say what supports each row.
- Historical existence and continuous ownership are not inferred from a current page.

## Suitable analyses

- Enterprises per owner, counted by distinct `enterprise_id`.
- Ownership chains from nation to operating company.
- Industries and federal-contracting presence of Native-owned enterprises.

## Unsafe aggregations

- Counting relationships as businesses.
- Reading an affiliation or a contested parent as ownership.
- Reading `first_observed_year` as a founding or acquisition date.

## What is still owed

Target columns the specification asks for that the terminal has not yet built from the full table. Each ships blank-free, not blank: it is absent until it exists.

- `ownership_effective_start` (pending:relations): When the ownership began, where a source states it.
- `ownership_effective_end` (pending:relations): When it ended, where a source states it.

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "NEST: Native Enterprise Structures and Ties" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** Two relations, declared per row and never conflated: a STRUCTURE is ownership — nation, holding company, operating company — and a TIE is a published relationship that is not ownership, such as a joint venture, which genuinely has two parents. Ownership is only ever recorded where a source asserted it; a shared name or a shared address is not evidence and does not create a row. An external identifier appears only where the owner published it, so the register is not padded with plausible matches. Where no external identifier exists the enterprise still gets a permanent, check-digited Cedar identifier and is carried as a sub-hub of its nation, which is what makes visible the enterprises federal contracting never sees.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

