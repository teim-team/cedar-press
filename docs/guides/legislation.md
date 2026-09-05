# Native Legislation and Votes: a researcher's guide

Collection `legislation` · public file `legislation.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Federal bills affecting Indian Country and the recorded votes on them, with sponsors, cosponsors and subject classification.

## Population

Bills in Congress that concern Native nations or organizations, judged relevant by Congress.gov's policy area and Cedar's subject classification with the basis recorded. Most legislation affecting Indian Country names no single tribe, so a row scoped to Indian Country as a whole is the correct representation, not a gap (collection descriptor).

## One row is

**Today:** One bill in Congress that concerns Native nations or organizations, with the entities it names.

**When the specification is applied:** One bill keyed by Congress, bill type and number, its status derived from its action history; member votes and actions, where they ship, are explicit record types with their own ids in the same table.

**Grain change:** Owed (§6): whether bill_votes and member_positions ship as vote and action record types inside this file (record_type) or remain supporting tables; either way bill totals count distinct bill_id and the promised vote coverage is not replaced by counts.

## Key identifiers

`bill_id` is Congress, bill type and number (`103-hr-2366`); `companion_bill_id` names the companion in the other chamber; `sponsor_bioguide_id` identifies the sponsor. A new introduction in a later Congress is a different bill even under the same title.

## Sources and coverage

**Sources:** Congress.gov API; Voteview roll-call records; committee and hearing records.

**Rows in the flagship table as released (recorded 2026-09-04):** 3,069. This is the count the release recorded for `native_bills.csv`, not the sum of the collection's 17 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`introduced_date` and `latest_action_date` are the bill's own dates; `status` is current as of `latest_action_date`. There is no geography beyond the entities named.

## Entity relationships

The opening block of every row is `cedar_uid`, `cedar_entity_name`, `cedar_entity_type` and `cedar_entity_role`. `cedar_uid` lists every entity the bill names, separated by |, with `cedar_entity_name` and `cedar_entity_type` in the same order and `entity_link_tiers` saying how firmly each resolves. `relevance_scope` says whether the bill is tribe-specific, class-wide or topic-wide, and `relevance_class_scope` names the class a class-wide bill is about. A broad Indigenous-policy bill does not name every tribe and is not attributed to any.

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

Status is derived from the action history on each rebuild; a bill's row changes as it moves. Passage by one chamber is not enactment; `status` distinguishes them.

## Field dictionary

The approved header, in order (26 columns, of which 1 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uid` (was `entity_cedar_uids`) | Cedar IDs | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. Several, separated by \|, where a row names several entities. | list, separated by | | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `cedar_entity_name` (was `entity_names`) | Native entities | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. | list, separated by | | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 3 | `cedar_entity_type` | Entity types | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 4 | `cedar_entity_role` | Entity role | Why the entity is on this row: named in the bill. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 5 | `bill_id` | Bill ID | Congress, chamber and number, for example 103-hr-2366. | identifier, as text | the source states none, or not applicable to this row |
| 6 | `record_type` | record type | bill, action or vote, if vote and action records ship in this table. | — | owed: not in the file until the terminal builds it |
| 7 | `congress` | Congress | Which Congress (the 103rd, and so on). | year | the source states no date |
| 8 | `chamber` | Chamber | House or Senate. | text | the source states none, or not applicable to this row |
| 9 | `bill_type` | Bill type | hr, s, hjres and the like, as Congress.gov codes them. | text | the source states none, or not applicable to this row |
| 10 | `bill_number` (was `number`) | Number | The bill's number in its chamber. | number | the source states none, or not applicable to this row |
| 11 | `title` | Title | The bill's title. | text | the source states none, or not applicable to this row |
| 12 | `policy_area` | Policy area | Congress.gov's policy area for the bill. | text | the source states none, or not applicable to this row |
| 13 | `relevance_scope` (was `bill_scope`) | Scope | Whether the bill is specific to one tribe or general to Indian Country. | text | the source states none, or not applicable to this row |
| 14 | `relevance_class_scope` (was `entity_class_scope`) | Relevance class scope | When the bill names no entity, the class of entity it is about (federally recognized tribes, Alaska Native corporations). Class-wide relevance, not any entity's class. | text | the source states none, or not applicable to this row |
| 15 | `sponsor_name` (was `sponsor`) | Sponsor | The sponsoring member, with party and state. | text | the source states none, or not applicable to this row |
| 16 | `sponsor_bioguide_id` | Sponsor ID | The sponsor's Biographical Directory identifier. | identifier, as text | the source states none, or not applicable to this row |
| 17 | `cosponsor_count` | Cosponsors | How many members cosponsored it. | number | the source states none, or not applicable to this row |
| 18 | `introduced_date` | Introduced | The date the bill was introduced; the year filter uses this. | date (YYYY-MM-DD) | the source states no date |
| 19 | `latest_action` | Latest action | The most recent action recorded on the bill. | text | the source states none, or not applicable to this row |
| 20 | `latest_action_date` | Latest action date | When that action happened. | date (YYYY-MM-DD) | the source states no date |
| 21 | `status` (was `outcome`) | Outcome | Where the bill ended: enacted, passed one chamber, died in committee. | text | the source states none, or not applicable to this row |
| 22 | `companion_bill_id` | Companion bill | The matching bill in the other chamber, where one exists. | identifier, as text | the source states none, or not applicable to this row |
| 23 | `has_rollcall` | Had a roll-call vote | Whether any roll-call vote was taken (yes or no). | yes or no (1 or 0) | not stated; 0 is no |
| 24 | `rollcall_count` (was `n_rollcalls`) | Roll-call votes | How many recorded roll-call votes the bill had. | number | the source states none, or not applicable to this row |
| 25 | `entity_link_tiers` | Entity link tiers | How firmly each named entity resolves to the register, in the same order as the IDs (A strongest). | list, separated by | | the source states none, or not applicable to this row |
| 26 | `source_url` | Source | The bill's page on congress.gov. | web address | the source states none, or not applicable to this row |

## Missing values

A blank is never zero and never an invented date. Beyond the column-level rules above:

- An empty `cedar_uid` with `relevance_scope` other than tribe-specific means the bill names no entity, which is correct for most Native legislation.
- A blank `companion_bill_id` means no companion was identified.

## Limitations

- Whether member votes and actions ship inside this file under a `record_type`, or remain the collection's supporting tables, is owed (§6). The bill table promises bills; `has_rollcall` and `rollcall_count` summarize the votes without replacing them.
- Relevance coding is a judgment with its basis recorded in the workspace; the readable category ships, the agreement statistics do not.

## Suitable analyses

- Bills by Congress, chamber, policy area and status, counted by distinct `bill_id`.
- Which entities are named in legislation and how often, by Congress.
- Time from introduction to latest action.

## Unsafe aggregations

- Counting a bill once per named entity: the row is the bill and the entities are a list.
- Reading `status` = passed one chamber as enacted.
- Treating a class-wide bill as naming every entity in the class.

## What is still owed

Target columns the specification asks for that the terminal has not yet built from the full table. Each ships blank-free, not blank: it is absent until it exists.

- `record_type` (pending:grain change): bill, action or vote, if vote and action records ship in this table.

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Native Legislation and Votes" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** Most legislation affecting Indian Country names no single tribe, so records are scoped to Indian Country as a whole rather than forced onto an entity — an unattached row here is the correct representation, not a gap. Subject classification is recorded with the basis on which a bill was judged Native-relevant.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

