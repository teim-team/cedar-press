# Native Legislation and Votes: a researcher's guide

Collection `legislation` · public file `legislation.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Federal bills affecting Indian Country and the recorded votes on them, with sponsors, cosponsors and subject classification.

## Population

Bills in Congress that concern Native nations or organizations, judged relevant by Congress.gov's policy area and Cedar's subject classification with the basis recorded. Most legislation affecting Indian Country names no single tribe, so a row scoped to Indian Country as a whole is the correct representation, not a gap (collection descriptor).

## One row is

One bill, as today; no rows for actions, cosponsors, votes or entity associations in this pass.

This pass changes columns, never rows: no aggregation, deduplication, change of publication eligibility or reassignment of Cedar IDs.

## Key identifiers

`bill_id` is Congress, bill type and number (`103-hr-2366`); `companion_bill_id` names the companion in the other chamber; `sponsor_bioguide_id` identifies the sponsor. A new introduction in a later Congress is a different bill even under the same title.

## Sources and coverage

**Sources:** Congress.gov API; Voteview roll-call records; committee and hearing records.

**Rows in the flagship table as released (recorded 2026-09-04):** 3,069. This is the count the release recorded for `native_bills.csv`, not the sum of the collection's 17 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`introduced_date` and `latest_action_date` are the bill's own dates; `status` is current as of `latest_action_date`. There is no geography beyond the entities named.

## Entity relationships

The opening block of every row is `cedar_uids`, `canonical_names`, `entity_classes`, `entity_roles` and `entity_names_as_published`, aligned JSON arrays. `cedar_uids`, `canonical_names`, `entity_classes`, `entity_roles` and `entity_names_as_published` are aligned JSON arrays: each position is one entity-role association, the role here being named in the bill. A named but unresolved party has null in `cedar_uids` and its name in `entity_names_as_published` once Cedar supplies it from the relationship evidence (null until then); `entity_link_statuses` is aligned the same way. `bill_scope` says whether the bill is tribe-specific, class-wide or topic-wide, and `affected_entity_classes` names the class a class-wide bill is about, kept apart from the named entities' registry classes. A broad Indigenous-policy bill does not name every tribe and is not attributed to any. Unpacking the arrays for analysis must keep the distinct `bill_id`, so the expansion does not inflate bill counts.

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

Status is derived from the action history on each rebuild; a bill's row changes as it moves. Passage by one chamber is not enactment; `status` distinguishes them.

## Field dictionary

The approved header, in the owner's exact order (29 columns, of which 0 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros; a JSON array cell is one list, aligned with its neighbours where the dictionary says so.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uids` | Cedar IDs | The Native entities associated with this record, as a JSON array; one position per entity-role association. A named but unresolved party has null here and its name in the names-as-published column. | JSON array (one list; aligned with its neighbours where the definition says so; null for an unresolved member) | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `canonical_names` | Native entities | Their register names, aligned position by position with the Cedar IDs. | JSON array (one list; aligned with its neighbours where the definition says so; null for an unresolved member) | the source states none, or not applicable to this row |
| 3 | `entity_classes` | Entity types | Their register classes, aligned. | JSON array (one list; aligned with its neighbours where the definition says so; null for an unresolved member) | the source states none, or not applicable to this row |
| 4 | `entity_roles` | Entity roles | The role of each association (affiliated, consulted, repatriation recipient; named in the bill), aligned. An entity in two roles occupies two positions. | JSON array (one list; aligned with its neighbours where the definition says so; null for an unresolved member) | the source states none, or not applicable to this row |
| 5 | `entity_names_as_published` | Names as published | What the source called each entity, aligned; null until Cedar supplies it from the relationship evidence. A register name is not proof of what the source said. | JSON array (one list; aligned with its neighbours where the definition says so; null for an unresolved member) | the source states none, or not applicable to this row |
| 6 | `bill_id` | Bill ID | Congress, chamber and number, for example 103-hr-2366. | identifier, as text | the source states none, or not applicable to this row |
| 7 | `congress` | Congress | Which Congress (the 103rd, and so on). | year | the source states no date |
| 8 | `chamber` | Chamber | House or Senate. | text | the source states none, or not applicable to this row |
| 9 | `bill_type` | Bill type | hr, s, hjres and the like, as Congress.gov codes them. | text | the source states none, or not applicable to this row |
| 10 | `bill_number` (was `number`) | Number | The bill's number in its chamber. | number | the source states none, or not applicable to this row |
| 11 | `title` | Title | The bill's title. | text | the source states none, or not applicable to this row |
| 12 | `policy_area` | Policy area | Congress.gov's policy area for the bill. | text | the source states none, or not applicable to this row |
| 13 | `bill_scope` | Scope | Whether the bill is specific to one tribe or general to Indian Country. | text | the source states none, or not applicable to this row |
| 14 | `affected_entity_classes` (was `entity_class_scope`) | Relevance class scope | When the bill names no entity, the class of entity it is about (federally recognized tribes, Alaska Native corporations). Class-wide relevance, not any entity's class. | text | the source states none, or not applicable to this row |
| 15 | `affected_entities_as_published` (was `affected_entities`) | Affected entities as published | The entities the source itself names as affected, as it names them; empty where the source names none. | text | the source states none, or not applicable to this row |
| 16 | `introduced_date` | Introduced | The date the bill was introduced; the year filter uses this. | date (YYYY-MM-DD) | the source states no date |
| 17 | `sponsor_name` (was `sponsor`) | Sponsor | The sponsoring member, with party and state. | text | the source states none, or not applicable to this row |
| 18 | `sponsor_bioguide_id` | Sponsor ID | The sponsor's Biographical Directory identifier. | identifier, as text | the source states none, or not applicable to this row |
| 19 | `cosponsor_count` | Cosponsors | How many members cosponsored it. | number | the source states none, or not applicable to this row |
| 20 | `latest_action` | Latest action | The most recent action recorded on the bill. | text | the source states none, or not applicable to this row |
| 21 | `latest_action_date` | Latest action date | When that action happened. | date (YYYY-MM-DD) | the source states no date |
| 22 | `outcome` | Outcome | Where the bill ended: enacted, passed one chamber, died in committee. | text | the source states none, or not applicable to this row |
| 23 | `companion_bill_id` | Companion bill | The matching bill in the other chamber, where one exists. | identifier, as text | the source states none, or not applicable to this row |
| 24 | `rollcall_count` (was `n_rollcalls`) | Roll-call votes | How many recorded roll-call votes the bill had. | number | the source states none, or not applicable to this row |
| 25 | `resolved_entity_count` (was `n_entities_resolved`) | Resolved entities | How many of the named entities Cedar resolved to its register. | number | the source states none, or not applicable to this row |
| 26 | `entity_link_statuses` | Entity link statuses | How firmly each named entity resolves to the register, aligned with the Cedar IDs (A strongest). | JSON array (one list; aligned with its neighbours where the definition says so; null for an unresolved member) | the source states none, or not applicable to this row |
| 27 | `source_system` | Source system | Which source the record came from. | text | the source states none, or not applicable to this row |
| 28 | `source_url` | Source | The official page for this record, written into the file so it cites itself. | web address | the source states none, or not applicable to this row |
| 29 | `research_note` | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. | text | the source states none, or not applicable to this row |

## Missing values

A blank is never zero and never an invented date. A blank JSON-list cell means unknown; `[]` means known to be empty (no additional source, no additional institution); a null element inside a list is one member the evidence names but does not resolve. Identifiers and codes are text with their leading zeros. Beyond the column-level rules above:

- An empty `cedar_uids` with `relevance_scope` other than tribe-specific means the bill names no entity, which is correct for most Native legislation.
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

Nothing beyond the grain and harmonization work named above.

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Native Legislation and Votes" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** Most legislation affecting Indian Country names no single tribe, so records are scoped to Indian Country as a whole rather than forced onto an entity — an unattached row here is the correct representation, not a gap. Subject classification is recorded with the basis on which a bill was judged Native-relevant.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

