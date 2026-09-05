# NAGPRA Notices: a researcher's guide

Collection `nagpra` · public file `nagpra.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Notices of Inventory Completion and Intent to Repatriate published under the Native American Graves Protection and Repatriation Act, with the institutions and affiliated tribes named in each.

## Population

Notices published under the Native American Graves Protection and Repatriation Act in the Federal Register: notices of inventory completion and of intent to repatriate, with the institution and the Native entities the notice names in each role. Affiliations are taken from the notice's own text, which is the legally operative statement (collection descriptor).

## One row is

One notice, as today, with its correction handling; no aggregation of counts.

This pass changes columns, never rows: no aggregation, deduplication, change of publication eligibility or reassignment of Cedar IDs.

## Key identifiers

`document_number` is the Federal Register document number. `related_notice_id` (owed) links a correction to the notice it corrects. `source_url` and `pdf_url` are the official text.

## Sources and coverage

**Sources:** Federal Register NAGPRA notices, full text.

**Rows in the flagship table as released (recorded 2026-09-04):** 6,792. This is the count the release recorded for `nagpra_notices.csv`, not the sum of the collection's 12 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`publication_date` is the notice's publication; `repatriation_eligible_date` and `response_deadline_date` are the dates the notice states. Institution geography (`institution_city`, `institution_state`) is where the holdings are; removal geography (`removal_counties`, `removal_states`) is where they were removed from, at county level. Precise removal sites do not ship.

## Entity relationships

The opening block of every row is `cedar_uids`, `canonical_names`, `entity_classes`, `entity_roles` and `entity_names_as_published`, aligned JSON arrays. `cedar_uids`, `canonical_names`, `entity_classes`, `entity_roles` and `entity_names_as_published` are aligned JSON arrays with one position per entity-role association across six roles: affiliated, consulted, disposition priority, repatriation recipient, letter of support, aboriginal land. An entity in two roles occupies two positions; the roles are legally different and are never flattened into one list of tribes. A named but unresolved party has null in `cedar_uids`; the twelve `n_*_named` and `n_*_resolved` counts keep the unresolved visible on every row, and `entity_names_as_published` carries the names once Cedar supplies them from the relationship evidence (null until then). Unpacking the arrays must keep the distinct `document_number`, so the expansion does not inflate notice counts or repeat stated counts.

Further role-specific links on the row, each an entity of the record the viewer finds it by:

- `consulted_entity_ids`: consulted (several, separated by |)
- `disposition_priority_entity_ids`: disposition priority (several, separated by |)
- `repatriation_recipient_entity_ids`: repatriation recipient (several, separated by |)
- `letter_of_support_entity_ids`: letter of support (several, separated by |)
- `aboriginal_land_entity_ids`: aboriginal land (several, separated by |)

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

A correction is its own notice (`is_correction` = 1) and can restate the same holdings; totals must not add a notice and its correction. The bridge names 51,338 party relationships and resolves 47,688; the `n_*_named` and `n_*_resolved` pairs carry that gap on every row as real uncertainty (docs/COLUMN_ORDER_NOTE_FOR_THE_TERMINAL_2026-09-05.md).

## Field dictionary

The approved header, in the owner's exact order (52 columns, of which 0 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros; a JSON array cell is one list, aligned with its neighbours where the dictionary says so.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uids` | Cedar IDs | The Native entities associated with this record, as a JSON array; one position per entity-role association. A named but unresolved party has null here and its name in the names-as-published column. | JSON array (one list; aligned with its neighbours where the definition says so; null for an unresolved member) | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `canonical_names` | Native entities | Their register names, aligned position by position with the Cedar IDs. | JSON array (one list; aligned with its neighbours where the definition says so; null for an unresolved member) | the source states none, or not applicable to this row |
| 3 | `entity_classes` | Entity types | Their register classes, aligned. | JSON array (one list; aligned with its neighbours where the definition says so; null for an unresolved member) | the source states none, or not applicable to this row |
| 4 | `entity_roles` | Entity roles | The role of each association (affiliated, consulted, repatriation recipient; named in the bill), aligned. An entity in two roles occupies two positions. | JSON array (one list; aligned with its neighbours where the definition says so; null for an unresolved member) | the source states none, or not applicable to this row |
| 5 | `entity_names_as_published` | Names as published | What the source called each entity, aligned; null until Cedar supplies it from the relationship evidence. A register name is not proof of what the source said. | JSON array (one list; aligned with its neighbours where the definition says so; null for an unresolved member) | the source states none, or not applicable to this row |
| 6 | `document_number` | Document number | The Federal Register document number. | identifier, as text | the source states none, or not applicable to this row |
| 7 | `publication_date` | Published | The date the notice was published. | date (YYYY-MM-DD) | the source states no date |
| 8 | `publication_year` | Publication year | The year the notice was published. | year | the source states no date |
| 9 | `notice_type` | Notice type | Inventory completion, intent to repatriate, or correction. | text | the source states none, or not applicable to this row |
| 10 | `process_stage` (was `statute_stage`) | Statute stage | Which stage of NAGPRA the notice is made under. | text | the source states none, or not applicable to this row |
| 11 | `is_correction` | Correction | Whether this notice corrects an earlier one (yes or no). | yes or no (1 or 0) | not stated; 0 is no |
| 12 | `title` | Title | The notice's title. | text | the source states none, or not applicable to this row |
| 13 | `institution_name` | Institution | The museum, university or agency holding the remains or objects. | text | the source states none, or not applicable to this row |
| 14 | `additional_institution_names` | Additional institutions | The institutions the notice names beyond the designated one, as a JSON list. | JSON array (one list; aligned with its neighbours where the definition says so; null for an unresolved member) | the source states none, or not applicable to this row |
| 15 | `institution_city` | Institution city | Where the institution is. | text | the source states none, or not applicable to this row |
| 16 | `institution_state` | Institution state | Its state. | text | the source states none, or not applicable to this row |
| 17 | `institution_type` (was `institution_type_derived`) | Institution type | Museum, university, federal agency, and so on. | text | the source states none, or not applicable to this row |
| 18 | `institution_split_flag` | Institution split (yes or no) | Whether the notice's institution field named several institutions that were split into the designated one and the additional ones. | yes or no (1 or 0) | not stated; 0 is no |
| 19 | `responsible_party_statement` | Responsible party | The official the notice names as responsible for the holdings, as stated. | text | the source states none, or not applicable to this row |
| 20 | `agency_names` | Publishing agency | The agency that published the notice. | list, separated by | | the source states none, or not applicable to this row |
| 21 | `object_categories` | Object categories | Which categories of items the notice covers (human remains, associated funerary objects, sacred objects, objects of cultural patrimony). | text | the source states none, or not applicable to this row |
| 22 | `individuals_stated` (was `mni_total_stated`) | Individuals | The minimum number of individuals the notice states. | number | the source states none, or not applicable to this row |
| 23 | `individuals_statement` (was `mni_statements`) | Individuals count, as stated | The sentence stating the minimum number of individuals, kept where the number alone is ambiguous. | text | the source states none, or not applicable to this row |
| 24 | `associated_funerary_objects_stated` (was `n_associated_funerary_objects_stated`) | Associated funerary objects | Count stated in the notice. | number | the source states none, or not applicable to this row |
| 25 | `unassociated_funerary_objects_stated` (was `n_unassociated_funerary_objects_stated`) | Unassociated funerary objects | Count stated in the notice. | number | the source states none, or not applicable to this row |
| 26 | `sacred_objects_stated` (was `n_sacred_objects_stated`) | Sacred objects | Count stated in the notice. | text | the source states none, or not applicable to this row |
| 27 | `cultural_patrimony_objects_stated` (was `n_objects_of_cultural_patrimony_stated`) | Objects of cultural patrimony | Count stated in the notice. | text | the source states none, or not applicable to this row |
| 28 | `cultural_items_total_stated` | Cultural items total, as stated | A total the notice itself states. Cedar never adds the categories together. | text | the source states none, or not applicable to this row |
| 29 | `removal_counties` | Removal counties | Where the remains or objects were removed from. | list, separated by | | the source states none, or not applicable to this row |
| 30 | `removal_states` | Removal states | The states of those places. | list, separated by | | the source states none, or not applicable to this row |
| 31 | `removal_location` (was `removal_location_statements`) | Removal location | Where the holdings were removed from, as the notice states it, with the existing restrictions on sensitive location applied before export. | text | the source states none, or not applicable to this row |
| 32 | `repatriation_eligible_date` | Repatriation eligible from | The date after which repatriation may proceed, as the notice states. Not evidence that a transfer happened. | text | the source states none, or not applicable to this row |
| 33 | `response_deadline_date` | Response deadline | The date by which other claimants must respond. | date (YYYY-MM-DD) | the source states no date |
| 34 | `lineal_descendant_determination` | Lineal descendant found | Whether a lineal descendant was determined (yes or no). | yes or no (1 or 0) | not stated; 0 is no |
| 35 | `culturally_unidentifiable` | Culturally unidentifiable | Whether the remains are determined culturally unidentifiable (yes or no). | yes or no (1 or 0) | not stated; 0 is no |
| 36 | `n_consulted_named` | Consulted parties named | How many parties the notice names as consulted. | number | not stated by the source; 0 means the source states none |
| 37 | `n_consulted_resolved` | Consulted parties resolved | How many of those Cedar could resolve to a register entity. The gap is real uncertainty, not an omission. | number | not stated by the source; 0 means the source states none |
| 38 | `n_affiliated_named` | Affiliated parties named | How many parties the notice names as culturally affiliated. | number | not stated by the source; 0 means the source states none |
| 39 | `n_affiliated_resolved` | Affiliated parties resolved | How many of those Cedar could resolve to a register entity. | number | not stated by the source; 0 means the source states none |
| 40 | `n_disposition_priority_named` | Priority parties named | How many parties the notice names with disposition priority. | number | not stated by the source; 0 means the source states none |
| 41 | `n_disposition_priority_resolved` | Priority parties resolved | How many of those Cedar could resolve. | number | not stated by the source; 0 means the source states none |
| 42 | `n_repatriation_recipient_named` | Recipients named | How many recipients the notice names. | number | not stated by the source; 0 means the source states none |
| 43 | `n_repatriation_recipient_resolved` | Recipients resolved | How many of those Cedar could resolve. | number | not stated by the source; 0 means the source states none |
| 44 | `n_letter_of_support_named` | Letters of support named | How many parties the notice names as having submitted a letter of support. | number | not stated by the source; 0 means the source states none |
| 45 | `n_letter_of_support_resolved` | Letters of support resolved | How many of those Cedar could resolve to a register entity. | number | not stated by the source; 0 means the source states none |
| 46 | `n_aboriginal_land_named` | Aboriginal-land parties named | How many parties the notice names for aboriginal land. | number | not stated by the source; 0 means the source states none |
| 47 | `n_aboriginal_land_resolved` | Aboriginal-land parties resolved | How many of those Cedar could resolve. | number | not stated by the source; 0 means the source states none |
| 48 | `n_parties_named` | Parties named in all | All parties the notice names, across roles. | number | not stated by the source; 0 means the source states none |
| 49 | `n_entities_resolved` | Entities resolved in all | How many distinct register entities those resolve to. | number | not stated by the source; 0 means the source states none |
| 50 | `source_url` | Source | The notice on federalregister.gov. | web address | the source states none, or not applicable to this row |
| 51 | `pdf_url` | PDF | The notice as published, in PDF. | web address | the source states none, or not applicable to this row |
| 52 | `research_note` | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. | text | the source states none, or not applicable to this row |

## Missing values

A blank is never zero and never an invented date. A blank JSON-list cell means unknown; `[]` means known to be empty (no additional source, no additional institution); a null element inside a list is one member the evidence names but does not resolve. Identifiers and codes are text with their leading zeros. Beyond the column-level rules above:

- A blank count column means the notice states no count for that category; 0 means it states zero.
- A blank role list with `n_*_named` = 0 means the notice names no party in that role; with `n_*_named` > 0 it means the named parties did not resolve.

## Limitations

- Counts are the notice's stated counts in the notice's own units. The minimum number of individuals (`individuals_stated`), associated and unassociated funerary objects, sacred objects and objects of cultural patrimony are different measures and are never added into one total.
- A notice, an eligibility date or a named recipient does not establish that a physical transfer was completed.
- Names as published beside each role's IDs are owed (§8), so the unresolved parties are visible; until then `n_*_named` against `n_*_resolved` is the measure of what is unresolved.

## Suitable analyses

- Notices by institution, state, type and year.
- Which entities are named as affiliated, consulted or recipient, and how often.
- Stated counts by category and institution, each category on its own.

## Unsafe aggregations

- Adding individuals to objects, or any two count categories together.
- Summing counts across a notice and its correction.
- Reading a notice as a completed repatriation.

## What is still owed

Nothing beyond the grain and harmonization work named above.

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "NAGPRA Notices" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** Tribal affiliations are taken from the notice's own text, which is the legally operative statement of affiliation, and an alias is only accepted into the identity layer when it appears across at least three independent notices. Cultural detail beyond what the notice publishes is not extracted, and no inference is made about ancestral remains or objects beyond the notice's own words.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

