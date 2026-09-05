# Cedar Press datasets: the proposed structure of each, for review

Generated from `data/cedar/codebook.json` by `scripts/codebook-markdown.mjs`; edit the JSON, not this file. Written 2026-09-05.

## What this is

Cedar Press sells twelve collections. Each collection has one customer-facing dataset (its flagship table) and, in the workspace, a number of supporting tables. Today the flagship files carry between 37 and 78 columns, of which a third to two-thirds are pipeline bookkeeping: how a row was matched, when it was built, the basis of a derived value. This document is the data dictionary of the structure each dataset has when a customer downloads it under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`: what one row is, and the columns that ship, each with a plain-English label and what it means. Every column here is one `docs/FIELD_MAP_2026-09-05.md` ships, under the name the map gives it; columns not listed stay in the workspace, and the per-column decisions with their reasons are in the map (the earlier reasoning is in `docs/COLUMN_ORDER_NOTE_FOR_THE_TERMINAL_2026-09-05.md`).

Three rules apply to every dataset:

1. **The Cedar opening block comes first**: `cedar_uid` (the entity's permanent ID), `canonical_name` (its name as Cedar's register spells it), `entity_class` (which of Cedar's eighteen classes it is) and `cedar_entity_role` (why the entity is on the row). The first three are the join key across collections; the fourth says what the join means. Legislation and NAGPRA, whose records concern several entities, carry the plural block instead: `cedar_uids`, `canonical_names`, `entity_classes`, `entity_roles`, `entity_names_as_published`, aligned JSON arrays with one position per entity-role association. Where a table lacks a column today it is marked *to add* and the writer fills it from the register; where it carries the same thing under another name, the rename is shown; a combine's sources are shown until the combined column exists.
2. **One row is one thing**, stated at the top of each dataset, and this pass changes columns, never rows; a table whose records concern several entities carries them in the plural block's aligned arrays, never as several ids in one singular cell.
3. **Every amount says what it is** (an obligation, an announced value, a reported spend) and is never summed across datasets; every row cites a source; every dataset ends with `research_note`, a concise factual qualification, blank when nothing needs saying.

Where the data lives: the full tables are built in the Cedar data workspace by `code/1135_full_dataset_review_bundle.py` into `dist/review/spreadsheets/<collection>/<table>.csv` (6.2 GB in all, not in the website repository); ten-row samples of each are copied to the website at `public/data/cedar/samples/<collection>/<table>__10.csv` and served at `https://cedarpress.ai/data/cedar/samples/...`. The entity register is `data/spine/cedar_entity_names.csv` (1,916 entities, 18 classes).

Meanings below were read from the column names and ten rows of values and are to be confirmed against the build scripts; a meaning marked *(confirm)* is the least certain.

## The datasets

### Federal Funding to Indian Country

Collection `funding` · table `federal_funding_transactions` · 701,955 rows in the full table · Cedar Press shelf

**One row is** One federal assistance transaction (a grant, loan, direct payment or insurance action) reported on USAspending, linked to the Native entity that received it.

**Where:** workspace dist/customer/funding.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/funding/federal_funding_transactions.csv; built by code/1135_full_dataset_review_bundle.py from the USAspending assistance archive.

**Columns a subscriber sees (41):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_class` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: recipient. |
| 5 | `assistance_transaction_unique_key` (*rename to `transaction_id`*) | Transaction ID | USAspending's unique key for this transaction. Cite it to find the exact record. |
| 6 | `assistance_award_unique_key` (*rename to `award_id`*) | Award ID | USAspending's key for the whole award; the source link is built from it. |
| 7 | `award_id_fain` (*rename to `fain`*) | Award number | The award's Federal Award Identification Number; several transactions can share one. |
| 8 | `action_date` | Action date | The date the agency took this action. |
| 9 | `fiscal_year` | Fiscal year | The federal fiscal year of the action (October to September), which is what USAspending reports and what the year filter uses. |
| 10 | `fy_partial_flag` | Partial fiscal year | Whether this row falls in a fiscal year the source had not finished reporting when Cedar pulled it (yes or no). Do not compare a partial year to a complete one. |
| 11 | `recipient_name` | Recipient as recorded | The recipient's name as the award records it, before Cedar resolved it to the entity. |
| 12 | `recipient_uei` | Recipient UEI | The recipient's federal Unique Entity ID. |
| 13 | `business_types_code` (*combines into `recipient_type`*) | Business types code | One of three overlapping recipient-type fields, consolidated through the source-code dictionary with conflict checks. |
| 14 | `business_types_description` (*combines into `recipient_type`*) | Recipient type as recorded | How USAspending classifies the recipient (for example, federally recognized tribal government). |
| 15 | `business_types_description_normalized` (*combines into `recipient_type`*) | Business types description normalized | The normalized spelling, the third of the three. |
| 16 | `assistance_type` (*rename to `assistance_type_code`*) | Assistance type code | The source's code for the assistance type (grant, loan, direct payment, insurance), defined in the dictionary; the readable type is beside it. |
| 17 | `assistance_type_description` (*rename to `assistance_type`*) | Assistance type | What kind of assistance it is: formula grant, project grant, direct payment, loan, insurance. |
| 18 | `cfda` (*rename to `program_code`*) | Program number | The Assistance Listing (CFDA) number of the federal program. |
| 19 | `cfda_title` (*rename to `program_name`*) | Program | The federal program's name. |
| 20 | `awarding_agency_name` (*rename to `awarding_agency`*) | Agency | The department that made the award. |
| 21 | `awarding_sub_agency_name` (*rename to `awarding_subagency`*) | Office | The office within the department. |
| 22 | `obligated_usd` (*rename to `obligations_usd`*) | Amount obligated | Dollars obligated by this transaction. Negative values are de-obligations, kept as recorded. |
| 23 | `obligated_usd_real2025` (*rename to `obligations_usd_real2025`*) | Amount in 2025 dollars | The same amount adjusted for inflation to 2025 dollars. |
| 24 | `face_value_of_loan` (*rename to `loan_face_value_usd`*) | Loan face value | For loans, the face value of this loan; zero for grants. |
| 25 | `original_loan_subsidy_cost` (*rename to `loan_subsidy_cost_usd`*) | Original loan subsidy cost | For a loan, the government's estimated cost of the subsidy when it was made. A loan measure; never added to obligations. |
| 26 | `total_face_value_of_loan` (*rename to `total_loan_face_value_usd`*) | Award loan face value | For loans, the face value of the whole award to date. |
| 27 | `total_loan_subsidy_cost` (*rename to `total_loan_subsidy_cost_usd`*) | Total loan subsidy cost | The subsidy cost across the award's loan actions. Never added to obligations. |
| 28 | `recipient_city_name` (*rename to `recipient_city`*) | Recipient city | City of the recipient's address on the award. |
| 29 | `recipient_state_code` (*rename to `recipient_state`*) | Recipient state | State of the recipient's address on the award. |
| 30 | `geo_recipient_county_name` (*rename to `recipient_county`*) | Recipient county | The county of the recipient's address, which is not necessarily where the funded work happens. |
| 31 | `geo_recipient_county_fips` (*rename to `recipient_county_fips`*) | Recipient county FIPS | The county code of the recipient's address. |
| 32 | `geo_pop_county_name` (*rename to `performance_county`*) | Place of performance county | The county where the funded work is performed, as the award reports it. |
| 33 | `geo_pop_county_fips` (*rename to `performance_county_fips`*) | Place of performance county FIPS | The county code where the funded work is performed, as the award reports it. |
| 34 | `recipient_geography_status` (*to add*) | Recipient geography status | Whether the recipient's address was placed in a county: placed, placed with an ambiguous place name, or unplaced. |
| 35 | `performance_geography_status` (*to add*) | Performance geography status | The same for the place of performance. |
| 36 | `attributed_flag` | Attributed to the entity | Whether Cedar attributes this transaction to the Native entity (yes) or keeps it in the file unattributed (no). Cedar's totals count attributed rows only. |
| 37 | `attribution_status` | Attribution status | How the attribution stands: attributed through the register, unattributed, or under review. |
| 38 | `source_system` (*to add*) | Source system | Which source the record came from. |
| 39 | `source_vintage` | Source vintage | The date stamp of the archive the row was taken from. |
| 40 | `source_url` (*to add*) | Source | The official page for this record, written into the file so it cites itself. |
| 41 | `research_note` (*to add*) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Federal Register

Collection `federal-register` · table `consultation_events` · 11,402 rows in the full table · Cedar Press shelf

**One row is** One tribal consultation event announced or reported in the Federal Register, one row per event and named participant (most events name no single tribe).

**Where:** workspace dist/customer/federal-register.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/federal-register/consultation_events.csv; built from Federal Register documents.

**Columns a subscriber sees (30):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` (*to add*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_class` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: participant. |
| 5 | `consultation_event_id` | Event ID | Cedar's identifier for the consultation event. |
| 6 | `fr_document_number` | Document number | The Federal Register document number. |
| 7 | `agency` | Agency | The department holding the consultation. |
| 8 | `sub_agency` (*rename to `subagency`*) | Office | The office within the department. |
| 9 | `program` | Program | The program or matter the consultation concerns, where the document names one. |
| 10 | `consultation_type` (*rename to `activity_type`*) | Kind of consultation | Whether this is a consultation session, a notice of consultation, or a consultation reported inside another document. |
| 11 | `topic` | Topic | What the consultation was about, from the document's title. |
| 12 | `document_role` | Document role | Whether the document announces a consultation or reports one that already happened. |
| 13 | `notice_date` | Notice date | The date the Federal Register document was published. |
| 14 | `event_start_date` | Event start | When the consultation began, as the notice states it. |
| 15 | `event_end_date` | Event end | When it ended, where stated. |
| 16 | `participant_name_as_published` (*rename to `participant_name`*) | Participant as published | The tribe or organization named in the document, as it spells it. |
| 17 | `participant_role` | Entity role | Why the entity is on this row: read from participant_role. |
| 18 | `location` | Location | Where the consultation was held. |
| 19 | `format` (*rename to `event_format`*) | Format | In person, virtual, teleconference, written comment, or a combination. |
| 20 | `comment_deadline` | Comment deadline | The date written comments were due, where stated. |
| 21 | `has_written_comments` | Written comments invited | Whether the document invites written comments (yes or no). |
| 22 | `has_summary` | Summary available (yes or no) | Whether a summary of the consultation is available from the source. |
| 23 | `has_transcript` | Transcript available (yes or no) | Whether a transcript is available from the source. |
| 24 | `is_event_primary_row` | Counts as one consultation | One row per event carries yes; the rest are additional participants of the same event. Count consultations by this column, not by rows. |
| 25 | `n_participant_rows_for_event` (*rename to `participant_rows_per_event`*) | Participant rows for this event | How many rows this event has in the file. |
| 26 | `federal_register_citation` | Citation | The Federal Register citation (volume FR page). |
| 27 | `source_system` (*to add*) | Source system | Which source the record came from. |
| 28 | `source_url` | Source | The document on federalregister.gov. |
| 29 | `source_quote` | Source passage | The sentence in the document this row was read from. |
| 30 | `research_note` (*to add*) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Legislation

Collection `legislation` · table `native_bills` · 3,069 rows in the full table · Cedar Press shelf

**One row is** One bill in Congress that concerns Native nations or organizations, with the entities it names.

**Where:** workspace dist/customer/legislation.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/legislation/native_bills.csv; built from the Congress.gov API.

**Columns a subscriber sees (29):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uids` (*to add*) | Cedar IDs | The Native entities associated with this record, as a JSON array; one position per entity-role association. A named but unresolved party has null here and its name in the names-as-published column. |
| 2 | `canonical_names` (*to add*) | Native entities | Their register names, aligned position by position with the Cedar IDs. |
| 3 | `entity_classes` (*to add*) | Entity types | Their register classes, aligned. |
| 4 | `entity_roles` (*to add*) | Entity roles | The role of each association (affiliated, consulted, repatriation recipient; named in the bill), aligned. An entity in two roles occupies two positions. |
| 5 | `entity_names_as_published` (*to add*) | Names as published | What the source called each entity, aligned; null until Cedar supplies it from the relationship evidence. A register name is not proof of what the source said. |
| 6 | `bill_id` | Bill ID | Congress, chamber and number, for example 103-hr-2366. |
| 7 | `congress` | Congress | Which Congress (the 103rd, and so on). |
| 8 | `chamber` | Chamber | House or Senate. |
| 9 | `bill_type` | Bill type | hr, s, hjres and the like, as Congress.gov codes them. |
| 10 | `number` (*rename to `bill_number`*) | Number | The bill's number in its chamber. |
| 11 | `title` | Title | The bill's title. |
| 12 | `policy_area` | Policy area | Congress.gov's policy area for the bill. |
| 13 | `bill_scope` | Scope | Whether the bill is specific to one tribe or general to Indian Country. |
| 14 | `entity_class_scope` (*rename to `affected_entity_classes`*) | Relevance class scope | When the bill names no entity, the class of entity it is about (federally recognized tribes, Alaska Native corporations). Class-wide relevance, not any entity's class. |
| 15 | `affected_entities` (*rename to `affected_entities_as_published`*) | Affected entities as published | The entities the source itself names as affected, as it names them; empty where the source names none. |
| 16 | `introduced_date` | Introduced | The date the bill was introduced; the year filter uses this. |
| 17 | `sponsor` (*rename to `sponsor_name`*) | Sponsor | The sponsoring member, with party and state. |
| 18 | `sponsor_bioguide_id` | Sponsor ID | The sponsor's Biographical Directory identifier. |
| 19 | `cosponsor_count` | Cosponsors | How many members cosponsored it. |
| 20 | `latest_action` | Latest action | The most recent action recorded on the bill. |
| 21 | `latest_action_date` | Latest action date | When that action happened. |
| 22 | `outcome` | Outcome | Where the bill ended: enacted, passed one chamber, died in committee. |
| 23 | `companion_bill_id` | Companion bill | The matching bill in the other chamber, where one exists. |
| 24 | `n_rollcalls` (*rename to `rollcall_count`*) | Roll-call votes | How many recorded roll-call votes the bill had. |
| 25 | `n_entities_resolved` (*rename to `resolved_entity_count`*) | Resolved entities | How many of the named entities Cedar resolved to its register. |
| 26 | `entity_link_statuses` (*to add*) | Entity link statuses | How firmly each named entity resolves to the register, aligned with the Cedar IDs (A strongest). |
| 27 | `source_system` (*to add*) | Source system | Which source the record came from. |
| 28 | `source_url` (*to add*) | Source | The official page for this record, written into the file so it cites itself. |
| 29 | `research_note` (*to add*) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Indian Country Deals

Collection `deals` · table `deals_classified` · 1,073 rows in the full table · Cedar Press shelf

**One row is** One announced transaction or award involving a Native party: an acquisition, a financing, a grant, a partnership.

**Where:** workspace dist/customer/deals.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/deals/deals_classified.csv; assembled from announcements, filings and agency award lists.

**Columns a subscriber sees (35):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `native_party_canonical_name` (*rename to `canonical_name`*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_class` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: Native party or its owner (per-row derivation owed from the party attribution). |
| 5 | `Deal_ID` (*rename to `deal_id`*) | Deal ID | Cedar's identifier for the deal. |
| 6 | `Event_Date` (*rename to `event_date`*) | Date | When the deal happened or was announced. |
| 7 | `Event_Date_precision` (*rename to `event_date_precision`*) | Date precision | Whether the date is known to the day, the month or the year. |
| 8 | `Event_Date_not_before` (*rename to `event_date_not_before`*) | Date not before | The earliest date the event could have happened, where the source gives an interval rather than a day. |
| 9 | `Event_Date_not_after` (*rename to `event_date_not_after`*) | Date not after | The latest date the event could have happened. |
| 10 | `Event_Year` (*rename to `event_year`*) | Year | The year of the event date. |
| 11 | `Deal_Title` (*rename to `title`*) | Title | A one-line description of the deal. |
| 12 | `Native_Party` (*rename to `native_party_name`*) | Native party as published | The Native party's name as the source gives it. |
| 13 | `Native_Party_Type` (*rename to `native_party_type`*) | Native party type as published | How the source describes the Native party. |
| 14 | `native_party_role` | Entity role | Why the entity is on this row: read from native_party_role (acquirer, borrower, issuer, partner, grantee, seller). |
| 15 | `Counterparty_or_Funder` (*rename to `counterparty_or_funder`*) | Counterparty or funder | The other side of the deal. |
| 16 | `Deal_Category` (*combines into `deal_type`*) | Category | Acquisition, grant or public financing, joint venture, and so on. |
| 17 | `transaction_type` (*combines into `deal_type`*) | Transaction type | The third of three overlapping classifications; shown until the one taxonomy replaces all three. |
| 18 | `Event_Type` (*combines into `transaction_structure`*) | Event | What kind of event this row records (an acquisition of a 90% interest, an award). |
| 19 | `Industry` (*rename to `industry`*) | Industry | The industry the deal is in. |
| 20 | `sector` | Sector | The broad sector the deal belongs to, beside the finer industry. |
| 21 | `capital_source` | Capital source | Where the capital comes from: public, private or tribal. |
| 22 | `Status` (*combines into `deal_status`*) | Status | Completed, announced, awarded, pending. |
| 23 | `deal_status_std` (*combines into `deal_status`*) | Status (standardized) | The standardized status; shown until one status column replaces the two. |
| 24 | `Announced_Value_USD` (*rename to `announced_value_usd`*) | Announced value | The dollar value announced, where one was. |
| 25 | `Value_Type` (*rename to `value_basis`*) | What the value is | What the announced figure represents (consideration paid, grant amount, project cost). |
| 26 | `Project_Total_Value_USD` (*rename to `project_total_value_usd`*) | Project total | The total project value, where larger than the announced value. |
| 27 | `State` (*rename to `state`*) | State | The state the deal is located in. |
| 28 | `Location` (*rename to `location`*) | Location | The place, as the source gives it. |
| 29 | `Description` (*rename to `description`*) | Description | A longer description of the deal. |
| 30 | `Native_Connection` (*rename to `native_connection`*) | Native connection | Why this deal is in the collection: how the Native party is connected. |
| 31 | `Verification_Status` (*rename to `verification_status`*) | Verification | Whether the deal was verified against a primary source. |
| 32 | `Source_1` (*rename to `source_url`*) | Source | The primary source document or page. |
| 33 | `Source_1_Type` (*rename to `source_type`*) | Source type | What kind of document the primary source is. |
| 34 | `additional_sources` (*to add*) | Additional sources | Further public sources beyond the primary one, as a JSON list of {url, source_type}. |
| 35 | `research_note` (*to add*) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### NAGPRA

Collection `nagpra` · table `nagpra_notices` · 6,792 rows in the full table · Cedar Press shelf

**One row is** One NAGPRA notice in the Federal Register (a notice of inventory completion or intent to repatriate), with the institution holding the remains or objects and the Native entities the notice names.

**Where:** workspace dist/customer/nagpra.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/nagpra/nagpra_notices.csv; built from Federal Register NAGPRA notices.

**Columns a subscriber sees (52):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uids` (*to add*) | Cedar IDs | The Native entities associated with this record, as a JSON array; one position per entity-role association. A named but unresolved party has null here and its name in the names-as-published column. |
| 2 | `canonical_names` (*to add*) | Native entities | Their register names, aligned position by position with the Cedar IDs. |
| 3 | `entity_classes` (*to add*) | Entity types | Their register classes, aligned. |
| 4 | `entity_roles` (*to add*) | Entity roles | The role of each association (affiliated, consulted, repatriation recipient; named in the bill), aligned. An entity in two roles occupies two positions. |
| 5 | `entity_names_as_published` (*to add*) | Names as published | What the source called each entity, aligned; null until Cedar supplies it from the relationship evidence. A register name is not proof of what the source said. |
| 6 | `document_number` | Document number | The Federal Register document number. |
| 7 | `publication_date` | Published | The date the notice was published. |
| 8 | `publication_year` | Publication year | The year the notice was published. |
| 9 | `notice_type` | Notice type | Inventory completion, intent to repatriate, or correction. |
| 10 | `statute_stage` (*rename to `process_stage`*) | Statute stage | Which stage of NAGPRA the notice is made under. |
| 11 | `is_correction` | Correction | Whether this notice corrects an earlier one (yes or no). |
| 12 | `title` | Title | The notice's title. |
| 13 | `institution_name` | Institution | The museum, university or agency holding the remains or objects. |
| 14 | `additional_institution_names` (*to add*) | Additional institutions | The institutions the notice names beyond the designated one, as a JSON list. |
| 15 | `institution_city` | Institution city | Where the institution is. |
| 16 | `institution_state` | Institution state | Its state. |
| 17 | `institution_type_derived` (*rename to `institution_type`*) | Institution type | Museum, university, federal agency, and so on. |
| 18 | `institution_split_flag` | Institution split (yes or no) | Whether the notice's institution field named several institutions that were split into the designated one and the additional ones. |
| 19 | `responsible_party_statement` | Responsible party | The official the notice names as responsible for the holdings, as stated. |
| 20 | `agency_names` | Publishing agency | The agency that published the notice. |
| 21 | `object_categories` | Object categories | Which categories of items the notice covers (human remains, associated funerary objects, sacred objects, objects of cultural patrimony). |
| 22 | `mni_total_stated` (*rename to `individuals_stated`*) | Individuals | The minimum number of individuals the notice states. |
| 23 | `mni_statements` (*rename to `individuals_statement`*) | Individuals count, as stated | The sentence stating the minimum number of individuals, kept where the number alone is ambiguous. |
| 24 | `n_associated_funerary_objects_stated` (*rename to `associated_funerary_objects_stated`*) | Associated funerary objects | Count stated in the notice. |
| 25 | `n_unassociated_funerary_objects_stated` (*rename to `unassociated_funerary_objects_stated`*) | Unassociated funerary objects | Count stated in the notice. |
| 26 | `n_sacred_objects_stated` (*rename to `sacred_objects_stated`*) | Sacred objects | Count stated in the notice. |
| 27 | `n_objects_of_cultural_patrimony_stated` (*rename to `cultural_patrimony_objects_stated`*) | Objects of cultural patrimony | Count stated in the notice. |
| 28 | `cultural_items_total_stated` | Cultural items total, as stated | A total the notice itself states. Cedar never adds the categories together. |
| 29 | `removal_counties` | Removal counties | Where the remains or objects were removed from. |
| 30 | `removal_states` | Removal states | The states of those places. |
| 31 | `removal_location_statements` (*rename to `removal_location`*) | Removal location | Where the holdings were removed from, as the notice states it, with the existing restrictions on sensitive location applied before export. |
| 32 | `repatriation_eligible_date` | Repatriation eligible from | The date after which repatriation may proceed, as the notice states. Not evidence that a transfer happened. |
| 33 | `response_deadline_date` | Response deadline | The date by which other claimants must respond. |
| 34 | `lineal_descendant_determination` | Lineal descendant found | Whether a lineal descendant was determined (yes or no). |
| 35 | `culturally_unidentifiable` | Culturally unidentifiable | Whether the remains are determined culturally unidentifiable (yes or no). |
| 36 | `n_consulted_named` | Consulted parties named | How many parties the notice names as consulted. |
| 37 | `n_consulted_resolved` | Consulted parties resolved | How many of those Cedar could resolve to a register entity. The gap is real uncertainty, not an omission. |
| 38 | `n_affiliated_named` | Affiliated parties named | How many parties the notice names as culturally affiliated. |
| 39 | `n_affiliated_resolved` | Affiliated parties resolved | How many of those Cedar could resolve to a register entity. |
| 40 | `n_disposition_priority_named` | Priority parties named | How many parties the notice names with disposition priority. |
| 41 | `n_disposition_priority_resolved` | Priority parties resolved | How many of those Cedar could resolve. |
| 42 | `n_repatriation_recipient_named` | Recipients named | How many recipients the notice names. |
| 43 | `n_repatriation_recipient_resolved` | Recipients resolved | How many of those Cedar could resolve. |
| 44 | `n_letter_of_support_named` | Letters of support named | How many parties the notice names as having submitted a letter of support. |
| 45 | `n_letter_of_support_resolved` | Letters of support resolved | How many of those Cedar could resolve to a register entity. |
| 46 | `n_aboriginal_land_named` | Aboriginal-land parties named | How many parties the notice names for aboriginal land. |
| 47 | `n_aboriginal_land_resolved` | Aboriginal-land parties resolved | How many of those Cedar could resolve. |
| 48 | `n_parties_named` | Parties named in all | All parties the notice names, across roles. |
| 49 | `n_entities_resolved` | Entities resolved in all | How many distinct register entities those resolve to. |
| 50 | `source_url` | Source | The notice on federalregister.gov. |
| 51 | `pdf_url` | PDF | The notice as published, in PDF. |
| 52 | `research_note` (*to add*) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Native Federal Advocacy & Engagement

Collection `lobbying` · table `native_entity_lobbying_disclosures` · 27,825 rows in the full table · Cedar Press shelf

**One row is** One federal lobbying filing under the Lobbying Disclosure Act in which the client is a Native entity, one row per filing (amended filings appear once, as the current version).

**Where:** workspace dist/customer/lobbying.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/lobbying/native_entity_lobbying_disclosures.csv; built from the Senate LDA filings database.

**Columns a subscriber sees (38):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_type` (*rename to `entity_class`*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: client. |
| 5 | `activity_id` (*to add*) | Activity ID | A stable, source-based identifier for the activity (lda:<filing uuid> for a filing). |
| 6 | `activity_type` (*to add*) | Activity type | Which kind of documented advocacy the row is. Every row today is an LDA filing; other source families populate other values only as they are actually sourced. |
| 7 | `filing_uuid` (*rename to `source_record_id`*) | Filing ID | The filing's identifier in the Senate LDA database. |
| 8 | `filing_year` (*rename to `reporting_year`*) | Filing year | The year the filing covers. |
| 9 | `filing_period` (*rename to `reporting_period`*) | Period | Which reporting period of the year. |
| 10 | `dt_posted` (*rename to `activity_date`*) | Posted | When the filing was posted. |
| 11 | `filing_type_display` (*rename to `activity_title`*) | Filing type | Registration, quarterly or year-end report, amendment, termination. |
| 12 | `client_name` | Client | The client as the filing names it (the Native entity, in its own spelling). |
| 13 | `client_id` | Client ID | The client's identifier in the Lobbying Disclosure Act database. |
| 14 | `client_state` | Client state | The client's state. |
| 15 | `registrant_name` | Registrant | The lobbying firm or, for a self-filer, the client itself. |
| 16 | `registrant_id` | Registrant ID | The registrant's identifier in the Lobbying Disclosure Act database. |
| 17 | `registrant_state` | Registrant state | The registrant's state. |
| 18 | `self_filed` | Self-filed | Whether the client filed for itself rather than through a firm (yes or no). |
| 19 | `participant_name` (*to add*) | Participant | The participant as the source names it, for consultations, testimony and meetings; blank for a filing. |
| 20 | `participant_role` (*to add*) | Participant role | The participant's role, for consultations, testimony and meetings; blank for a filing. |
| 21 | `government_entities` (*rename to `government_bodies`*) | Government entities contacted | Agencies and chambers the filing lists, separated by \|. |
| 22 | `lobbying_issues_codes` (*rename to `issue_codes`*) | Issue codes | The LDA issue area codes on the filing. |
| 23 | `specific_issues_text` (*rename to `issues_text`*) | Specific issues | What the filing says was lobbied on. |
| 24 | `affiliated_organizations` | Affiliated organizations | Organizations the filing lists as affiliated with the client. |
| 25 | `income_usd` | Income reported | What the registrant reported receiving from the client this period. |
| 26 | `expenses_usd` | Expenses reported | What a self-filer reported spending this period. |
| 27 | `spend_usd` (*rename to `reported_amount_usd`*) | Reported spend | Whichever of the two the filing reports; the basis column says which. |
| 28 | `spend_basis` (*rename to `amount_basis`*) | Basis of spend | Income, expenses, or none reported. |
| 29 | `termination_date` | Termination date | When the registration was terminated, where the filing is a termination. |
| 30 | `supersession_status` | Version status | Whether a later amendment replaces this filing. |
| 31 | `is_superseded` | Superseded (yes or no) | Whether a later filing replaces this one; the default view counts current filings only. |
| 32 | `superseded_by_filing_uuid` (*rename to `superseded_by_record_id`*) | Replaced by | The filing that replaces this one, where one does. |
| 33 | `supersession_group_id` | Supersession group | The group of filings (an original and its amendments) this filing belongs to. |
| 34 | `attribution_withdrawn` | Attribution withdrawn | Whether Cedar withdrew its link between this filing and the entity after review (yes or no). A withdrawn filing stays in the file; its spend is not counted as the entity's. |
| 35 | `attribution_withdrawn_reason` | Why withdrawn | The reason recorded for the withdrawal. |
| 36 | `source_system` (*to add*) | Source system | Which source the record came from. |
| 37 | `filing_url` (*rename to `source_url`*) | Source | The filing on lda.senate.gov. |
| 38 | `research_note` (*to add*) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Native Federal Contractors

Collection `contractors` · table `prime_contracts` · 1,217,768 rows in the full table · Cedar Press+ shelf

**One row is** One federal contract transaction (an award or a modification) to a firm owned by a Native entity, as reported to FPDS and published on USAspending.

**Where:** workspace dist/customer/contractors.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/contractors/prime_contracts.csv; built from the USAspending contract archive.

**Columns a subscriber sees (51):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_class` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: owner of the awardee. |
| 5 | `contract_transaction_unique_key` (*rename to `transaction_id`*) | Transaction ID | USAspending's key for this transaction. |
| 6 | `contract_award_unique_key` (*rename to `award_id`*) | Award ID | USAspending's key for the whole award; the source link is built from it. |
| 7 | `contract_number` | Contract number | The contract or order number. |
| 8 | `parent_contract_number` | Parent contract | The parent contract or vehicle, for orders. |
| 9 | `action_date` | Action date | The date of this award or modification. |
| 10 | `fiscal_year` | Fiscal year | The federal fiscal year of the action. |
| 11 | `awardee_name` | Awardee | The contractor as the award names it. |
| 12 | `awardee_uei` | Awardee UEI | The contractor's federal Unique Entity ID. |
| 13 | `cage_code` | Awardee CAGE | The contractor's CAGE code, the identifier that persists across the DUNS-to-UEI change; masked on rows the publication rule withholds. |
| 14 | `parent_name` | Awardee's parent | The contractor's parent as the award records it. |
| 15 | `parent_uei` | Parent UEI | The UEI of the parent FPDS declares for the contractor. |
| 16 | `funding_agency` | Funding agency | The agency paying for the work. |
| 17 | `award_type` | Award type | Delivery order, BPA call, definitive contract, and so on. |
| 18 | `award_base_description` (*rename to `description`*) | Description | The award's own description of the work. |
| 19 | `naics_code` | NAICS | The industry code of the work. |
| 20 | `naics_description` | Industry | What that code means. |
| 21 | `product_or_service_code` (*rename to `psc_code`*) | Product or service code | The federal product or service code (PSC), defined in the dictionary; the description is beside it. |
| 22 | `product_or_service_code_description` (*rename to `psc_description`*) | Product or service | What was bought. |
| 23 | `sector` (*combines into `sector`*) | Sector | The two-digit sector code and the readable group consolidated into one readable sector through the dictionary. |
| 24 | `supersector` (*combines into `sector`*) | Industry group | The broad industry group the contract's NAICS code belongs to. |
| 25 | `total_obligations` (*rename to `obligations_usd`*) | Amount obligated | Dollars obligated by this transaction. Sum these, never the award value. |
| 26 | `total_obligations_real2025` (*rename to `obligations_usd_real2025`*) | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. |
| 27 | `total_award_value` (*rename to `cumulative_award_value_usd`*) | Award value to date | The whole award's value as restated on this row. Cumulative: never add it across rows. |
| 28 | `setaside_reported` (*rename to `set_aside_reported`*) | Set-aside reported (yes or no) | Whether the award reports any set-aside; the classification beside it says which. |
| 29 | `setaside` (*rename to `set_aside_classification`*) | Set-aside | The set-aside the award was made under, if any. |
| 30 | `reported_8a` | 8(a) reported | Whether the award reports the 8(a) program (yes or no). |
| 31 | `reported_buy_indian` | Buy Indian Act reported (yes or no) | Whether the award reports use of the Buy Indian Act preference. Reported use, not eligibility. |
| 32 | `reported_indian_business` | Indian business reported (yes or no) | Whether the award reports the contractor as an Indian business under the relevant preference. |
| 33 | `reported_native_preference` | Native preference reported | Whether the award reports a Native preference (yes or no). |
| 34 | `extent_competed` (*combines into `competition_type`*) | Extent competed | Raw and normalized competition labels consolidated through a validated dictionary. |
| 35 | `extent_competed_normalized` (*combines into `competition_type`*) | Competition | How the award was competed. |
| 36 | `recipient_city_name` (*rename to `recipient_city`*) | Awardee city | City of the awardee's address. |
| 37 | `recipient_state_code` (*rename to `recipient_state`*) | Awardee state | Its state. |
| 38 | `geo_recipient_county_name` (*rename to `recipient_county`*) | Recipient county | The county of the contractor's address, which is not where the work is performed. |
| 39 | `geo_recipient_county_fips` (*rename to `recipient_county_fips`*) | Recipient county FIPS | The county code of the contractor's address. |
| 40 | `place_of_perform_city` (*rename to `performance_city`*) | Place of performance | City where the work is performed. |
| 41 | `place_of_perform_state` (*rename to `performance_state`*) | Place of performance state | Its state. |
| 42 | `geo_pop_county_name` (*rename to `performance_county`*) | Place of performance county | The county where the contract is performed, as the award reports it. |
| 43 | `geo_pop_county_fips` (*rename to `performance_county_fips`*) | Place of performance county FIPS | The county code where the contract is performed. |
| 44 | `recipient_geography_status` (*to add*) | Recipient geography status | Whether the recipient's address was placed in a county: placed, placed with an ambiguous place name, or unplaced. |
| 45 | `performance_geography_status` (*to add*) | Performance geography status | The same for the place of performance. |
| 46 | `attributed_flag` | Attributed (yes or no) | Whether the row is attributed to the Native entity in the opening block; the totals count attributed rows only. |
| 47 | `owner_attribution_status` | Ownership at the time | Whether the entity's ownership of the awardee was confirmed as of the transaction. |
| 48 | `owner_as_of_transaction_cedar_uid` | Owner as of the action | The Cedar ID of the entity that owned the contractor on the action date where the ownership history resolves it; UNKNOWN where it does not. Never the current owner assumed backwards. |
| 49 | `source_system` (*to add*) | Source system | Which source the record came from. |
| 50 | `source_url` (*to add*) | Source | The official page for this record, written into the file so it cites itself. |
| 51 | `research_note` (*to add*) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Native Subcontracting

Collection `subcontracting` · table `subawards` · 89,809 rows in the full table · Cedar Press+ shelf

**One row is** One federal subcontract reported through FSRS where the prime, the subcontractor or both are owned by a Native entity.

**Where:** workspace dist/customer/subcontracting.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/subcontracting/subawards.csv; built from the USAspending FSRS subaward pull.

**Columns a subscriber sees (54):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` (*to add*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_class` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: from native_direction: owner of the subcontractor, of the prime, or of both. |
| 5 | `subaward_source_record_id` (*rename to `subaward_record_id`*) | Subaward ID | The subaward report's identifier. |
| 6 | `subaward_number` | Subaward number | The subaward's own number as the prime reported it. |
| 7 | `subaward_sam_report_id` (*rename to `report_id`*) | Report ID | The SAM subaward report's identifier: the version of the report this row comes from. |
| 8 | `subaward_date` | Subaward date | The date of the subaward. |
| 9 | `fiscal_year` | Fiscal year | The federal fiscal year of the subaward. |
| 10 | `subaward_sam_report_year` (*rename to `report_year`*) | Report year | The year of the report the subaward was filed in: the reporting period. |
| 11 | `award_kind` | Award type | Whether the prime award is a contract or an assistance award. The two populations are never combined in a total. |
| 12 | `subaward_type` | Subaward type | Sub-contract or sub-grant, as reported. |
| 13 | `description` | Description | What the subcontract is for, as reported. |
| 14 | `sub_name` (*rename to `subcontractor_name`*) | Subcontractor | The subcontractor as reported. |
| 15 | `sub_uei` (*rename to `subcontractor_uei`*) | Subcontractor UEI | Its Unique Entity ID. |
| 16 | `sub_cage` (*rename to `subcontractor_cage`*) | Subcontractor CAGE | Its CAGE code, where reported. |
| 17 | `sub_parent_name` (*rename to `subcontractor_parent_name`*) | Subcontractor's parent | Its parent as reported. |
| 18 | `sub_parent_uei` (*rename to `subcontractor_parent_uei`*) | Subrecipient parent UEI | The UEI of the subrecipient's declared parent. |
| 19 | `sub_parent_cage` (*rename to `subcontractor_parent_cage`*) | Subrecipient parent CAGE | The CAGE code of the subrecipient's declared parent. |
| 20 | `sub_cedar_uid` | Subcontractor's Cedar ID | The Native entity owning the subcontractor, where one does. |
| 21 | `prime_name` | Prime contractor | The prime as reported. |
| 22 | `prime_uei` | Prime UEI | Its Unique Entity ID. |
| 23 | `prime_cage` | Prime CAGE | Its CAGE code, where reported. |
| 24 | `prime_parent_name` | Prime's parent | Its parent as reported. |
| 25 | `prime_parent_uei` | Prime parent UEI | The UEI of the prime's declared parent. |
| 26 | `prime_parent_cage` | Prime parent CAGE | The CAGE code of the prime's declared parent. |
| 27 | `prime_cedar_uid` | Prime's Cedar ID | The Native entity owning the prime contractor, where one does. |
| 28 | `direction` (*rename to `native_direction`*) | Which side is Native | Whether the prime, the sub, or both sides are Native-owned. |
| 29 | `prime_award_id` | Prime award number | The prime contract's number. |
| 30 | `prime_award_unique_key` | Prime award key | USAspending's key for the prime award. |
| 31 | `subaward_amount` (*rename to `subaward_amount_usd`*) | Subaward amount | Dollars of the subaward. |
| 32 | `subaward_amount_real2025` (*rename to `subaward_amount_usd_real2025`*) | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. |
| 33 | `prime_award_amount` (*rename to `prime_award_amount_usd`*) | Prime award amount | The prime contract's value. |
| 34 | `subaward_to_prime_ratio` | Subaward to prime ratio | The subaward amount divided by the prime award amount, with the amount, period and version definitions the guide states; never recomputed from incompatible snapshots. |
| 35 | `prime_top_awarding_agency` (*rename to `awarding_agency`*) | Agency | The department that awarded the prime contract. |
| 36 | `prime_awarding_sub_agency` (*rename to `awarding_subagency`*) | Office | The office within it. |
| 37 | `prime_set_aside` | Prime set-aside | The set-aside category of the prime award, where reported. |
| 38 | `naics` (*rename to `naics_code`*) | NAICS | The industry code. |
| 39 | `naics_title` (*rename to `naics_description`*) | Industry | What that code means. |
| 40 | `psc` (*rename to `psc_code`*) | Product or service code | The federal product or service code of the subaward, where reported. |
| 41 | `psc_title` (*rename to `psc_description`*) | Product or service | What the product or service code means. |
| 42 | `sub_business_types` (*rename to `subcontractor_business_types`*) | Subcontractor business types | The business types it reports (for example, Alaska Native Corporation owned). |
| 43 | `geo_subawardee_city` (*rename to `subcontractor_city`*) | Subrecipient city | The subrecipient's own city, never filled from the prime's address. |
| 44 | `sub_state` (*rename to `subcontractor_state`*) | Subcontractor state | Its state. |
| 45 | `geo_subawardee_county_name` (*rename to `subcontractor_county`*) | Subrecipient county | The county of the subrecipient's address. |
| 46 | `geo_subawardee_county_fips` (*rename to `subcontractor_county_fips`*) | Subrecipient county FIPS | The county code of the subrecipient's address. |
| 47 | `geo_subawardee_country_code` (*rename to `subcontractor_country`*) | Subrecipient country | The subrecipient's country code. |
| 48 | `subcontractor_geography_status` (*to add*) | Subcontractor geography status | Whether the subcontractor's own address was placed in a county: placed, placed with an ambiguous place name, or unplaced. Never filled from the prime's address. |
| 49 | `duplicate_status` | Duplicate status | Whether this row is the primary filing or a duplicate of one. Sum primaries only. |
| 50 | `subaward_exceeds_prime_flag` | Exceeds the prime award | Whether the subaward amount exceeds its prime award (yes or no). A real filing, kept in the file, but never added into totals. |
| 51 | `action_date_precedes_ffata_flag` | Date before FFATA | Whether the reported date precedes the reporting law itself (yes or no), a known filer anomaly; do not treat such a date as when the work happened. |
| 52 | `source_dataset` (*rename to `source_system`*) | Source system | Which source the report came from (the USAspending FSRS pull). |
| 53 | `source_url` | Source | The prime award's page on USAspending. |
| 54 | `research_note` (*to add*) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Native-Owned Businesses

Collection `owned` · table `native_owned_businesses` · 4,273 rows in the full table · Cedar Press+ shelf

**One row is** One business owned by a Native entity, in the register of such businesses.

**Where:** workspace dist/customer/owned.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/native-owned-businesses/native_owned_businesses.csv. NOT AUDITED: the sample is not in the repository yet; run scripts/import_cedar_manifest.py --audit after adding it.

**Columns a subscriber sees (32):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` (*to add*) | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` (*to add*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_class` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: certifying_authority. |
| 5 | `business_source_id` | Business source id |  |
| 6 | `business_name_raw` (*rename to `business_name`*) | Business name |  |
| 7 | `business_entity_id` | Business entity id |  |
| 8 | `certifying_authority_entity_id` | Certifying authority entity id |  |
| 9 | `certifying_authority_name` | Certifying authority name |  |
| 10 | `programme_name` (*rename to `program_name`*) | Program name |  |
| 11 | `directory_type` | Directory type |  |
| 12 | `assertion_class` | Assertion class |  |
| 13 | `identity_scope` | Identity scope |  |
| 14 | `identity_claim_text` | Identity claim text |  |
| 15 | `ownership_percent` | Ownership percent |  |
| 16 | `ownership_threshold_min` | Ownership threshold min |  |
| 17 | `certification_number` | Certification number |  |
| 18 | `certification_tier` | Certification tier |  |
| 19 | `certification_start` | Certification start |  |
| 20 | `certification_expiration` | Certification expiration |  |
| 21 | `business_license_number` | Business license number |  |
| 22 | `service_category_raw` (*rename to `service_category`*) | Service category |  |
| 23 | `naics` (*rename to `naics_code`*) | Naics code |  |
| 24 | `city` | City |  |
| 25 | `state_province` (*rename to `state`*) | State |  |
| 26 | `source_edition` | Source edition |  |
| 27 | `source_last_updated` | Source last updated |  |
| 28 | `first_seen` | First seen |  |
| 29 | `last_seen` | Last seen |  |
| 30 | `is_current` | Is current |  |
| 31 | `source_url` | Source | The official page for this record, written into the file so it cites itself. |
| 32 | `research_note` (*to add*) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Native Enterprises

Collection `nest` · table `nest_enterprises` · 5,820 rows in the full table · Cedar Press+ shelf

**One row is** One enterprise (a subsidiary, a joint venture, an affiliate) with the Native entity that owns or is affiliated with it and how.

**Where:** workspace dist/customer/nest.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/nest/nest_enterprises.csv; built from owners' own subsidiary listings, annual reports and federal identifier records.

**Columns a subscriber sees (30):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `owner_hub_name` (*rename to `canonical_name`*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `owner_hub_entity_class` (*rename to `entity_class`*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: read from relationship_type. |
| 5 | `enterprise_id` | Enterprise ID | Cedar's identifier for the enterprise. |
| 6 | `enterprise_name` | Enterprise | The enterprise's name. |
| 7 | `name_variants_observed` (*rename to `alternative_names`*) | Also seen as | Other spellings of the name in the sources, separated by \|. |
| 8 | `parent_enterprise_id` | Parent enterprise ID | The immediate parent enterprise's ID, where the parent is an enterprise rather than the Native entity itself. |
| 9 | `parent_name` | Parent | The immediate parent, which may itself be an enterprise. |
| 10 | `relation_class` (*rename to `relationship_type`*) | Entity role | Why the entity is on this row: read from relationship_type: owner, or affiliated entity, of the enterprise. |
| 11 | `relationship_as_recorded` | Relationship as recorded | The relationship in the source's own words, beside the normalized relationship type. |
| 12 | `ownership_percent_stated` (*rename to `ownership_percent`*) | Ownership share | The percentage owned, where a source states it. |
| 13 | `sector` | Sector | The enterprise's sector. |
| 14 | `status` (*rename to `operating_status`*) | Status | Operating, dissolved, or unknown. |
| 15 | `city` | City | Where the enterprise is. |
| 16 | `state_province` (*rename to `state`*) | State | Its state or province. |
| 17 | `uei` | UEI | Its federal Unique Entity ID, where one is published. |
| 18 | `cage_code` | CAGE code | The enterprise's CAGE code, where known. |
| 19 | `in_federal_contracting` | Federal contractor | Whether the enterprise appears in federal contracting records (yes or no). |
| 20 | `first_observed_year` | First seen | The earliest year a source names the enterprise. |
| 21 | `last_observed_year` | Last seen | The latest. |
| 22 | `n_distinct_sources` (*rename to `source_count`*) | Sources | How many distinct sources support the relationship. |
| 23 | `evidence_class` (*rename to `relationship_evidence_status`*) | Kind of evidence | What kind of source establishes the relationship (the owner's own list, an audited report, a resolver). |
| 24 | `fpds_declared_parent_name` (*rename to `reported_federal_parent_name`*) | Parent declared in FPDS | The parent the enterprise declares in federal contracting records, kept as evidence beside Cedar's relationship. |
| 25 | `fpds_parent_corroboration` (*rename to `federal_parent_corroboration`*) | Federal records agree | Whether the parent the enterprise declares in federal records agrees with this owner. |
| 26 | `source_document` | Source document | The document, where the source is a file. |
| 27 | `source_edition_date` | Source date | The date of that source. |
| 28 | `source_url` | Source | Where the relationship is stated. |
| 29 | `additional_source_urls` (*to add*) | Additional source URLs | Further source URLs, as a JSON list; blank until the sources table supplies them. |
| 30 | `research_note` (*to add*) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Natural Resource Revenue

Collection `natural-resources` · table `resource_revenue` · 11,305 rows in the full table · Cedar Press+ shelf

**One row is** One payment or distribution of natural-resource revenue (royalties, severance tax shares, reclamation distributions) to a Native entity.

**Where:** workspace dist/customer/natural-resources.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/natural-resources/resource_revenue.csv; built from federal and state revenue records.

**Columns a subscriber sees (38):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` (*to add*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_class` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: recipient. |
| 5 | `resource_revenue_event_id` | Payment ID | Cedar's identifier for the payment. |
| 6 | `source_record_id` | Source record ID | The record's identifier in that source. |
| 7 | `recipient_entity_name` (*rename to `recipient_name`*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. |
| 8 | `beneficiary_entity_id` | Beneficiary ID | The identifier of the beneficiary where it differs from the recipient. |
| 9 | `beneficiary_entity_name` (*rename to `beneficiary_name`*) | Beneficiary | Who the payment is for, where different from the recipient. |
| 10 | `payer_entity_id` | Payer ID | The identifier of the payer. |
| 11 | `payer_entity_name` (*rename to `payer_name`*) | Payer | Who made the payment (a federal office, a state). |
| 12 | `operator_entity_id` | Operator ID | The identifier of the related operator, where a source supports one. |
| 13 | `operator_entity_name` (*rename to `operator_name`*) | Operator | The related operator's name, where a source supports one. |
| 14 | `related_asset_ids` | Related assets | The wells, tracts or leases the payment relates to, where a source names them; empty today and kept for when one does. |
| 15 | `revenue_type` | Revenue type | Royalty, severance tax share, reclamation fee distribution, and so on. |
| 16 | `resource_type` | Resource | Oil and gas, coal, timber, minerals. |
| 17 | `commodity` | Commodity | The commodity, as the source names it. |
| 18 | `product` | Product | The product, where the source states one below the commodity. |
| 19 | `mineral_lease_type` | Mineral lease type | The lease type, where the source states it. |
| 20 | `period_type` | Period covered | Whether the payment covers a fiscal year, a month, or is dated only by payment. |
| 21 | `period_start` | Period start | Start of the period the payment covers, where stated. |
| 22 | `period_end` | Period end | End of that period. |
| 23 | `payment_date` | Payment date | When the payment was made. |
| 24 | `amount_usd` | Amount | Dollars paid. The sign column says what a negative means. |
| 25 | `amount_usd_real2025` | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. |
| 26 | `measurement_status` | Actual or estimated | Whether the amount is an actual payment or an estimate. |
| 27 | `aggregation_level` | Aggregation level | Whether the amount is specific to the entity, a regional aggregate or a countrywide aggregate. An aggregate is never assigned to one tribe. |
| 28 | `amount_sign_meaning` | What the sign means | How to read a negative amount (a correction, a recoupment). |
| 29 | `land_status` | Land status | Trust or fee land, where the source states it. |
| 30 | `allocation_formula` | Allocation formula | The rule that determined the amount, where the source states it. |
| 31 | `allocation_formula_effective_start` | Allocation rule effective from | When the allocation rule took effect. |
| 32 | `allocation_formula_effective_end` | Allocation rule effective to | When the allocation rule ceased to apply. |
| 33 | `allocation_formula_source_url` | Formula source | Where that rule is published. |
| 34 | `geography_note` | Place | What the source says about where the revenue arose. |
| 35 | `entity_attribution_status` (*rename to `attribution_status`*) | Attribution status | Whether the row is keyed to a Native entity, to an aggregate, or unresolved. A blank Cedar ID has a stated reason here. |
| 36 | `source_system` | Source system | Which source system the record came from. |
| 37 | `source_url` | Source | Where the payment is recorded. |
| 38 | `research_note` (*to add*) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Native Nonprofits

Collection `nonprofits` · table `np_orgs` · 12,764 rows in the full table · Cedar Press+ shelf

**One row is** One nonprofit organization in the IRS Business Master File that is Native-led or tribally controlled, with the Native entity it is linked to.

**Where:** workspace dist/customer/nonprofits.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/nonprofits/np_orgs.csv; built from the IRS Exempt Organizations Business Master File and Native-led directories.

**Columns a subscriber sees (27):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `cedar_spine_canonical_name` (*rename to `canonical_name`*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `cedar_spine_entity_class` (*rename to `entity_class`*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: associated Native entity. |
| 5 | `EIN` (*rename to `ein`*) | EIN | The organization's Employer Identification Number. |
| 6 | `org_name` (*rename to `organization_name`*) | Organization | The organization's name as the IRS records it. |
| 7 | `cedar_native_entity_class` (*rename to `organization_entity_class`*) | Organization type | Whether the organization is itself a tribe, an ANC, a Native organization. |
| 8 | `classification_ruling` (*combines into `inclusion_category`*) | Relationship to the entity | Whether the organization is tribally controlled, tribally affiliated, or unruled. |
| 9 | `disposition` (*combines into `inclusion_category`*) | Inclusion basis | Why the organization is in Cedar: verified strictly, verified, or a candidate. |
| 10 | `city` | City | Its city. |
| 11 | `state` | State | The organization's state. |
| 12 | `ntee_code` | NTEE code | The IRS activity code for what the organization does. |
| 13 | `bmf_status` (*rename to `irs_status`*) | IRS status code | The organization's status code in the Business Master File, defined in the dictionary. |
| 14 | `bmf_subsection` (*rename to `irs_subsection`*) | Tax subsection | The 501(c) subsection (3 for charities). |
| 15 | `bmf_foundation_cd` (*rename to `irs_foundation_code`*) | Foundation code | The IRS foundation classification code, defined in the dictionary. |
| 16 | `bmf_irs_ruling_yyyymm` (*rename to `irs_ruling_month`*) | IRS ruling date | When the IRS recognized the organization (year and month). |
| 17 | `bmf_tax_period` (*rename to `tax_period`*) | Latest tax period | The most recent tax period in the file. |
| 18 | `bmf_revenue_amt` (*rename to `bmf_revenue_usd`*) | Revenue | Revenue in the latest return the IRS holds. |
| 19 | `bmf_asset_amt` (*rename to `bmf_assets_usd`*) | Assets | Assets in that return. |
| 20 | `bmf_income_amt` (*rename to `bmf_income_usd`*) | Income | Income in that return. |
| 21 | `bmf_vintage_fetched` (*rename to `bmf_as_of_date`*) | IRS file date | The date of the IRS file these figures come from. |
| 22 | `entity_tier` (*combines into `entity_link_status`*) | Match confidence | Cedar's confidence in the link to the entity: A is strongest. |
| 23 | `cedar_link_tier` (*combines into `entity_link_status`*) | Cedar link tier | Shown until the combined column replaces it. |
| 24 | `key_review_disposition` (*combines into `entity_link_status`*) | Key review disposition | Shown until the combined column replaces it. |
| 25 | `source_dataset` (*rename to `source_system`*) | Source system | The source: the IRS Exempt Organizations Business Master File. |
| 26 | `source_url` | Source | The IRS Business Master File. |
| 27 | `research_note` (*to add*) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

## Questions for the reviewer

- Is any kept column unnecessary for a subscriber, and is any dropped column (see the note) something a subscriber would miss?
- Are the labels the words a subscriber would use? Is any meaning wrong or unclear?
- Is the opening block the right first four columns for every dataset, and should the record's own identifier be the fifth everywhere?
- For datasets whose rows name several entities (Legislation, NAGPRA), is one row per record with `|`-separated entities better than one row per record and entity?
- Which datasets should carry inflation-adjusted amounts, and should the base year be a column or a note?

