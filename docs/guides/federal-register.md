# Federal Register — Indian Affairs: a researcher's guide

Collection `federal-register` · public file `federal-register.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Federal Register documents affecting Indian Country since 1994 — consultation notices, land-into-trust decisions, recognition actions, rules and ex parte communications.

## Population

Tribal consultation events announced or reported in the Federal Register, one row per event and named participant. The composition is stated rather than smoothed: 10,888 of 11,402 rows (95.5%) are NAGPRA consultation reported inside a NAGPRA notice, because that is what the Federal Register carries at volume; policy consultation is the smaller remainder and is typed separately (collection descriptor, measured 2026-09-02). Agency-wide and Indian-Country-wide documents are kept even when no tribe is named, with their scope stated.

## One row is

One consultation event and named participant, as today; count events by is_event_primary_row, never rows.

This pass changes columns, never rows: no aggregation, deduplication, change of publication eligibility or reassignment of Cedar IDs.

## Key identifiers

`consultation_event_id` names the event; `fr_document_number` is the Federal Register document number and `federal_register_citation` the official citation. A document that is also a NAGPRA notice is cross-referenced by `related_nagpra_document_number` once the terminal builds it, rather than counted as a second action.

## Sources and coverage

**Sources:** federalregister.gov, by agency and by subject, back to 1994.

**Rows in the flagship table as released (recorded 2026-09-04):** 11,402. This is the count the release recorded for `consultation_events.csv`, not the sum of the collection's 29 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`publication_date` is when the Federal Register published the document; `event_start_date` and `event_end_date` are the consultation's own dates; `comment_deadline` is the deadline the notice states. `location` is the event's location as the notice gives it, which may be several places or a format such as written comment.

## Entity relationships

The opening block of every row is `cedar_uid`, `canonical_name`, `entity_class` and `cedar_entity_role`. `cedar_entity_role` is the participant's role as the notice states it (`participant_role` today: named, invited, not enumerated). A blank `cedar_uid` is explained by `entity_link_status`, never left to be guessed: `no_individual_named` (the notice addresses a population, not an entity), `unresolved` (a named party the register could not place), `withheld` (the publication rule applies) or `resolved`. `collective_scopes` carries the population the notice addresses or applies to, as a JSON array of elements from the vocabulary in data/cedar/scopes.json: the scope, the relationship (addressed, applies_to, eligible_class, aggregate_population, general_subject), the as-of date and its rule, and the source words. A scope is not an entity: it has no Cedar ID, is never counted as one, and a notice addressed to every federally recognized tribe is not a record of any one of them. Both columns are owed by the terminal from the source text; until then they are absent, and a blank `cedar_uid` still never means no tribe was consulted.

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

Corrections and withdrawals are separate Federal Register documents; each is its own row with its own document number. The terminal's merge of duplicate representations of one document is owed (§5).

## Field dictionary

The approved header, in the owner's exact order (33 columns, of which 3 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros; a JSON array cell is one list, aligned with its neighbours where the dictionary says so.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. | text | the source states none, or not applicable to this row |
| 3 | `entity_class` | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. | text | the source states none, or not applicable to this row |
| 4 | `cedar_entity_role` | Entity role | Why the entity is on this row: participant. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 5 | `entity_link_status` | entity link status | Why the Cedar block is filled or blank on this row: a notice addressed to a population names no individual entity, which is not a failed match (owner's decision of 2026-09-05, docs/COLLECTIVE_SCOPE_DECISION_2026-09-05.md). | — | owed: not in the file until the terminal builds it |
| 6 | `collective_scopes` | collective scopes | JSON array of collective scopes: the population the notice addresses or applies to, with the relationship, the as-of date and rule, and the source words; null until evaluated, [] when the notice names none. | — | owed: not in the file until the terminal builds it |
| 7 | `consultation_event_id` | Event ID | Cedar's identifier for the consultation event. | identifier, as text | the source states none, or not applicable to this row |
| 8 | `fr_document_number` | Document number | The Federal Register document number. | identifier, as text | the source states none, or not applicable to this row |
| 9 | `agency` | Agency | The department holding the consultation. | text | the source states none, or not applicable to this row |
| 10 | `subagency` (was `sub_agency`) | Office | The office within the department. | text | the source states none, or not applicable to this row |
| 11 | `program` | Program | The program or matter the consultation concerns, where the document names one. | text | the source states none, or not applicable to this row |
| 12 | `activity_type` (was `consultation_type`) | Kind of consultation | Whether this is a consultation session, a notice of consultation, or a consultation reported inside another document. | text | the source states none, or not applicable to this row |
| 13 | `topic` | Topic | What the consultation was about, from the document's title. | text | the source states none, or not applicable to this row |
| 14 | `document_role` | Document role | Whether the document announces a consultation or reports one that already happened. | text | the source states none, or not applicable to this row |
| 15 | `notice_date` | Notice date | The date the Federal Register document was published. | date (YYYY-MM-DD) | the source states no date |
| 16 | `event_start_date` | Event start | When the consultation began, as the notice states it. | date (YYYY-MM-DD) | the source states no date |
| 17 | `event_end_date` | Event end | When it ended, where stated. | date (YYYY-MM-DD) | the source states no date |
| 18 | `event_date_precision` | event date precision | day, month, year or unstated, translated from the date qualification. | — | owed: not in the file until the terminal builds it |
| 19 | `participant_name` (was `participant_name_as_published`) | Participant as published | The tribe or organization named in the document, as it spells it. | text | the source states none, or not applicable to this row |
| 20 | `participant_role` | Entity role | Why the entity is on this row: read from participant_role. | text | the source states none, or not applicable to this row |
| 21 | `location` | Location | Where the consultation was held. | text | the source states none, or not applicable to this row |
| 22 | `event_format` (was `format`) | Format | In person, virtual, teleconference, written comment, or a combination. | text | the source states none, or not applicable to this row |
| 23 | `comment_deadline` | Comment deadline | The date written comments were due, where stated. | date (YYYY-MM-DD) | the source states no date |
| 24 | `has_written_comments` | Written comments invited | Whether the document invites written comments (yes or no). | yes or no (1 or 0) | not stated; 0 is no |
| 25 | `has_summary` | Summary available (yes or no) | Whether a summary of the consultation is available from the source. | yes or no (1 or 0) | not stated; 0 is no |
| 26 | `has_transcript` | Transcript available (yes or no) | Whether a transcript is available from the source. | yes or no (1 or 0) | not stated; 0 is no |
| 27 | `is_event_primary_row` | Counts as one consultation | One row per event carries yes; the rest are additional participants of the same event. Count consultations by this column, not by rows. | yes or no (1 or 0) | not stated; 0 is no |
| 28 | `participant_rows_per_event` (was `n_participant_rows_for_event`) | Participant rows for this event | How many rows this event has in the file. | number | the source states none, or not applicable to this row |
| 29 | `federal_register_citation` | Citation | The Federal Register citation (volume FR page). | text | the source states none, or not applicable to this row |
| 30 | `source_system` | Source system | Which source the record came from. | text | the source states none, or not applicable to this row |
| 31 | `source_url` | Source | The document on federalregister.gov. | web address | the source states none, or not applicable to this row |
| 32 | `source_quote` | Source passage | The sentence in the document this row was read from. | text | the source states none, or not applicable to this row |
| 33 | `research_note` | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. | text | the source states none, or not applicable to this row |

## Missing values

A blank is never zero and never an invented date. A blank JSON-list cell means unknown; `[]` means known to be empty (no additional source, no additional institution); a null element inside a list is one member the evidence names but does not resolve. Identifiers and codes are text with their leading zeros. Beyond the column-level rules above:

- A blank `cedar_uid` means no participant is enumerated or the named one is unresolved.
- Blank event dates mean the notice announces no dated event (a written comment period, say).
- `has_written_comments`, `has_summary` and `has_transcript` are 0 where nothing was found, not where nothing exists.

## Limitations

- A notice inviting consultation is not proof that consultation occurred; `document_role` says whether the row is a notice announcing a consultation or a report of one.
- One event fans out to as many rows as it has named participants. `is_event_primary_row` marks one row per event; a reader counting rows instead overstates by about 4.9× (docs/COLUMN_ORDER_NOTE_FOR_THE_TERMINAL_2026-09-05.md).
- `source_quote` is the sentence that classified the row; it is kept because it materially clarifies the classification, not as a citation apparatus.

## Suitable analyses

- Consultations by agency, topic and year, counted as SUM(`is_event_primary_row`).
- Which entities were named in which consultations, and how far in advance of the event the notice was published.
- Comment-period lengths by agency.

## Unsafe aggregations

- Counting rows as consultations.
- Counting a document that is also a NAGPRA notice twice across the two collections.
- Reading an announced opportunity as documented participation.

## What is still owed

Target columns the specification asks for that the terminal has not yet built from the full table. Each is absent until it exists, never blank.

- `entity_link_status` (pending:terminal reads the source: no_individual_named, resolved, unresolved or withheld): Why the Cedar block is filled or blank on this row: a notice addressed to a population names no individual entity, which is not a failed match (owner's decision of 2026-09-05, docs/COLLECTIVE_SCOPE_DECISION_2026-09-05.md).
- `collective_scopes` (pending:terminal reads the source's addressee, applicability or eligibility clause into elements of data/cedar/scopes.json): JSON array of collective scopes: the population the notice addresses or applies to, with the relationship, the as-of date and rule, and the source words; null until evaluated, [] when the notice names none.
- `event_date_precision` (derive:event_date_basis): day, month, year or unstated, translated from the date qualification.

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Federal Register — Indian Affairs" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** Scope is recorded per document because it genuinely varies: a notice can name one tribe, several, or all of Indian Country, and each is a different fact. Participants in consultation events are resolved to the entity layer where the notice names them and left unresolved where it does not, rather than inferred. The consultation table's composition is stated rather than smoothed: 10,888 of its 11,402 rows (95.5%) are NAGPRA consultation reported inside a NAGPRA notice, because that is what the Federal Register carries at volume. Policy consultation is the smaller remainder and is typed separately. The Federal Register is not the ceiling for Dear Tribal Leader letters and this copy said it nearly was. Probed on 2026-09-02 the Register holds 46 documents carrying the phrase, and that reading was used here to call a thin count close to the source's limit, with the agencies' own websites recorded as not yet acquired. They have since been acquired and the surface is 17.5 times larger: 807 letters spanning 2000–2026 — Indian Health Service 783, Bureau of Indian Education 14, Bureau of Indian Affairs 10. What had looked like an absent source was a request that the host answered with 406 until its headers were shaped correctly, which is a fact about the request and not about the publisher.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

