# NAGPRA Notices: a researcher's guide

Collection `nagpra` · public file `nagpra.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Notices of Inventory Completion and Intent to Repatriate published under the Native American Graves Protection and Repatriation Act, with the institutions and affiliated tribes named in each.

## Population

Notices published under the Native American Graves Protection and Repatriation Act in the Federal Register: notices of inventory completion and of intent to repatriate, with the institution and the Native entities the notice names in each role. Affiliations are taken from the notice's own text, which is the legally operative statement (collection descriptor).

## One row is

**Today:** One NAGPRA notice in the Federal Register, with the institution and the Native entities named in each role.

**When the specification is applied:** The same: one notice or document, with its correction relationship retained and each role's entities kept distinct.

**Grain change:** Owed (§8): related_notice_id for corrections so a corrected notice does not repeat holdings in totals; names as published beside each role's ids so the resolved subset is not shown as the whole.

## Key identifiers

`document_number` is the Federal Register document number. `related_notice_id` (owed) links a correction to the notice it corrects. `source_url` and `pdf_url` are the official text.

## Sources and coverage

**Sources:** Federal Register NAGPRA notices, full text.

**Rows in the flagship table as released (recorded 2026-09-04):** 6,792. This is the count the release recorded for `nagpra_notices.csv`, not the sum of the collection's 12 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`publication_date` is the notice's publication; `repatriation_eligible_date` and `response_deadline_date` are the dates the notice states. Institution geography (`institution_city`, `institution_state`) is where the holdings are; removal geography (`removal_counties`, `removal_states`) is where they were removed from, at county level. Precise removal sites do not ship.

## Entity relationships

The opening block of every row is `cedar_uid`, `cedar_entity_name`, `cedar_entity_type` and `cedar_entity_role`. The opening block carries the culturally affiliated entities (`cedar_entity_role` = culturally affiliated), separated by |. The other roles keep their own lists beside it: `consulted_entity_ids`, `disposition_priority_entity_ids`, `repatriation_recipient_entity_ids`, `letter_of_support_entity_ids`, `aboriginal_land_entity_ids`. These roles are legally different and are never collapsed into one list of tribes. The viewer finds a notice through any of them.

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

The approved header, in order (59 columns, of which 7 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uid` (was `affiliated_entity_ids`) | Cedar IDs | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. Several, separated by \|, where a row names several entities. | list, separated by | | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `cedar_entity_name` | Native entities | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 3 | `cedar_entity_type` | Entity types | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 4 | `cedar_entity_role` | Entity role | Why the entity is on this row: culturally affiliated, as the notice determines. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 5 | `document_number` | Document number | The Federal Register document number. | identifier, as text | the source states none, or not applicable to this row |
| 6 | `related_notice_id` | related notice id | The notice this one corrects, or is corrected by. | — | owed: not in the file until the terminal builds it |
| 7 | `notice_type` | Notice type | Inventory completion, intent to repatriate, or correction. | text | the source states none, or not applicable to this row |
| 8 | `process_stage` (was `statute_stage`) | Statute stage | Which stage of NAGPRA the notice is made under. | text | the source states none, or not applicable to this row |
| 9 | `is_correction` | Correction | Whether this notice corrects an earlier one (yes or no). | yes or no (1 or 0) | not stated; 0 is no |
| 10 | `publication_date` | Published | The date the notice was published. | date (YYYY-MM-DD) | the source states no date |
| 11 | `title` | Title | The notice's title. | text | the source states none, or not applicable to this row |
| 12 | `institution_name` | Institution | The museum, university or agency holding the remains or objects. | text | the source states none, or not applicable to this row |
| 13 | `institution_names_all` | All institutions | Every institution the notice names, where it names more than one, separated by \|. | text | the source states none, or not applicable to this row |
| 14 | `institution_type` (was `institution_type_derived`) | Institution type | Museum, university, federal agency, and so on. | text | the source states none, or not applicable to this row |
| 15 | `institution_city` | Institution city | Where the institution is. | text | the source states none, or not applicable to this row |
| 16 | `institution_state` | Institution state | Its state. | text | the source states none, or not applicable to this row |
| 17 | `responsible_party_statement` | Responsible party | The official the notice names as responsible for the holdings, as stated. | text | the source states none, or not applicable to this row |
| 18 | `agency_names` | Publishing agency | The agency that published the notice. | list, separated by | | the source states none, or not applicable to this row |
| 19 | `object_categories` | Object categories | Which categories of items the notice covers (human remains, associated funerary objects, sacred objects, objects of cultural patrimony). | text | the source states none, or not applicable to this row |
| 20 | `mni_total_stated` | Individuals | The minimum number of individuals the notice states. | number | the source states none, or not applicable to this row |
| 21 | `mni_statements` | Individuals count, as stated | The sentence stating the minimum number of individuals, kept where the number alone is ambiguous. | text | the source states none, or not applicable to this row |
| 22 | `n_associated_funerary_objects_stated` | Associated funerary objects | Count stated in the notice. | number | not stated by the source; 0 means the source states none |
| 23 | `n_unassociated_funerary_objects_stated` | Unassociated funerary objects | Count stated in the notice. | number | not stated by the source; 0 means the source states none |
| 24 | `n_sacred_objects_stated` | Sacred objects | Count stated in the notice. | text | not stated by the source; 0 means the source states none |
| 25 | `n_objects_of_cultural_patrimony_stated` | Objects of cultural patrimony | Count stated in the notice. | text | not stated by the source; 0 means the source states none |
| 26 | `cultural_items_total_stated` | Cultural items total, as stated | A total the notice itself states. Cedar never adds the categories together. | text | the source states none, or not applicable to this row |
| 27 | `removal_counties` | Removal counties | Where the remains or objects were removed from. | list, separated by | | the source states none, or not applicable to this row |
| 28 | `removal_states` | Removal states | The states of those places. | list, separated by | | the source states none, or not applicable to this row |
| 29 | `repatriation_eligible_date` | Repatriation eligible from | The date after which repatriation may proceed, as the notice states. Not evidence that a transfer happened. | text | the source states none, or not applicable to this row |
| 30 | `response_deadline_date` | Response deadline | The date by which other claimants must respond. | date (YYYY-MM-DD) | the source states no date |
| 31 | `lineal_descendant_determination` | Lineal descendant found | Whether a lineal descendant was determined (yes or no). | yes or no (1 or 0) | not stated; 0 is no |
| 32 | `culturally_unidentifiable` | Culturally unidentifiable | Whether the remains are determined culturally unidentifiable (yes or no). | yes or no (1 or 0) | not stated; 0 is no |
| 33 | `n_affiliated_named` | Affiliated parties named | How many parties the notice names as culturally affiliated. | number | not stated by the source; 0 means the source states none |
| 34 | `n_affiliated_resolved` | Affiliated parties resolved | How many of those Cedar could resolve to a register entity. | number | not stated by the source; 0 means the source states none |
| 35 | `affiliated_entity_names` | affiliated entity names | The affiliated parties as the notice names them. | — | owed: not in the file until the terminal builds it |
| 36 | `n_consulted_named` | Consulted parties named | How many parties the notice names as consulted. | number | not stated by the source; 0 means the source states none |
| 37 | `n_consulted_resolved` | Consulted parties resolved | How many of those Cedar could resolve to a register entity. The gap is real uncertainty, not an omission. | number | not stated by the source; 0 means the source states none |
| 38 | `consulted_entity_ids` | Cedar IDs (consulted) | Entities the notice says were consulted. | list, separated by | | the source states none, or not applicable to this row |
| 39 | `consulted_entity_names` | consulted entity names | The consulted parties as the notice names them, so the unresolved are visible. | — | owed: not in the file until the terminal builds it |
| 40 | `n_disposition_priority_named` | Priority parties named | How many parties the notice names with disposition priority. | number | not stated by the source; 0 means the source states none |
| 41 | `n_disposition_priority_resolved` | Priority parties resolved | How many of those Cedar could resolve. | number | not stated by the source; 0 means the source states none |
| 42 | `disposition_priority_entity_ids` | Cedar IDs (disposition priority) | Entities with priority for disposition, where stated. | list, separated by | | the source states none, or not applicable to this row |
| 43 | `disposition_priority_entity_names` | disposition priority entity names | Owed: see below. | — | owed: not in the file until the terminal builds it |
| 44 | `n_repatriation_recipient_named` | Recipients named | How many recipients the notice names. | number | not stated by the source; 0 means the source states none |
| 45 | `n_repatriation_recipient_resolved` | Recipients resolved | How many of those Cedar could resolve. | number | not stated by the source; 0 means the source states none |
| 46 | `repatriation_recipient_entity_ids` | Cedar IDs (repatriation recipient) | Entities the notice names to receive the repatriation. | list, separated by | | the source states none, or not applicable to this row |
| 47 | `repatriation_recipient_entity_names` | repatriation recipient entity names | Owed: see below. | — | owed: not in the file until the terminal builds it |
| 48 | `n_letter_of_support_named` | Letters of support named | How many parties the notice names as having submitted a letter of support. | number | not stated by the source; 0 means the source states none |
| 49 | `n_letter_of_support_resolved` | Letters of support resolved | How many of those Cedar could resolve to a register entity. | number | not stated by the source; 0 means the source states none |
| 50 | `letter_of_support_entity_ids` | Cedar IDs (letter of support) | The Cedar IDs of the parties named as submitting a letter of support, separated by \|. | list, separated by | | the source states none, or not applicable to this row |
| 51 | `letter_of_support_entity_names` | letter of support entity names | Owed: see below. | — | owed: not in the file until the terminal builds it |
| 52 | `n_aboriginal_land_named` | Aboriginal-land parties named | How many parties the notice names for aboriginal land. | number | not stated by the source; 0 means the source states none |
| 53 | `n_aboriginal_land_resolved` | Aboriginal-land parties resolved | How many of those Cedar could resolve. | number | not stated by the source; 0 means the source states none |
| 54 | `aboriginal_land_entity_ids` | Cedar IDs (aboriginal land) | Entities on whose aboriginal land the removal site lies, where stated. | list, separated by | | the source states none, or not applicable to this row |
| 55 | `aboriginal_land_entity_names` | aboriginal land entity names | Owed: see below. | — | owed: not in the file until the terminal builds it |
| 56 | `n_parties_named` | Parties named in all | All parties the notice names, across roles. | number | not stated by the source; 0 means the source states none |
| 57 | `n_entities_resolved` | Entities resolved in all | How many distinct register entities those resolve to. | number | not stated by the source; 0 means the source states none |
| 58 | `source_url` | Source | The notice on federalregister.gov. | web address | the source states none, or not applicable to this row |
| 59 | `pdf_url` | PDF | The notice as published, in PDF. | web address | the source states none, or not applicable to this row |

## Missing values

A blank is never zero and never an invented date. Beyond the column-level rules above:

- A blank count column means the notice states no count for that category; 0 means it states zero.
- A blank role list with `n_*_named` = 0 means the notice names no party in that role; with `n_*_named` > 0 it means the named parties did not resolve.

## Limitations

- Counts are the notice's stated counts in the notice's own units. The minimum number of individuals (`mni_total_stated`), associated and unassociated funerary objects, sacred objects and objects of cultural patrimony are different measures and are never added into one total.
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

Target columns the specification asks for that the terminal has not yet built from the full table. Each ships blank-free, not blank: it is absent until it exists.

- `related_notice_id` (pending:corrections): The notice this one corrects, or is corrected by.
- `consulted_entity_names` (pending:names as published): The consulted parties as the notice names them, so the unresolved are visible.
- `affiliated_entity_names` (pending:names as published): The affiliated parties as the notice names them.
- `disposition_priority_entity_names` (pending:names as published): see the field map
- `repatriation_recipient_entity_names` (pending:names as published): see the field map
- `letter_of_support_entity_names` (pending:names as published): see the field map
- `aboriginal_land_entity_names` (pending:names as published): see the field map

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "NAGPRA Notices" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** Tribal affiliations are taken from the notice's own text, which is the legally operative statement of affiliation, and an alias is only accepted into the identity layer when it appears across at least three independent notices. Cultural detail beyond what the notice publishes is not extracted, and no inference is made about ancestral remains or objects beyond the notice's own words.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

