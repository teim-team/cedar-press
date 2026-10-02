# Cedar Press dataset dictionaries

Generated from `data/cedar/codebook.json` and `data/cedar/collections.manifest.json` by `scripts/docs-markdown.mjs --kind codebook`. Edit the source dictionaries and regenerate this document.

## Scope

This document contains 26 dictionary entries. 14 entries describe the installed producer spreadsheets selected by the manifest. Any other entry is labelled as a compatibility reference and does not describe a currently served spreadsheet.

Each exported field keeps its own meaning, source role and publication qualification. A business identifier, an owner link, a certifying-authority link and a source-record key identify different objects or relationships. A missing identity is not filled by a shared name.

Read `record_type`, `record_key` and `record_grain` together. A researcher spreadsheet can contain several logical record types whose grains overlap. Amounts retain their stated basis; obligations, allocations, payments, ceilings and reported spending are not interchangeable.

The served previews are short excerpts. Matching a dictionary to a preview verifies the displayed schema, not every underlying fact or the entire population. Publication and field restrictions remain governed by the release.

## The dictionaries

### Federal Funding to Indian Country

Collection `funding` · table `federal_funding_transactions` · compatibility reference; not the manifest's installed spreadsheet

**One row is:** One federal assistance transaction (a grant, loan, direct payment or insurance action) reported on USAspending, linked to the Native entity that received it.

**Release or source location:** workspace dist/customer/funding.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/funding/federal_funding_transactions.csv; built by code/1135_full_dataset_review_bundle.py from the USAspending assistance archive.

**Fields (41):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_class` (to add in the compatibility transform) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (to add in the compatibility transform) | Entity role | Why the entity is on this row: recipient. |
| 5 | `assistance_transaction_unique_key` (rename to `transaction_id`) | Transaction ID | USAspending's unique key for this transaction. Cite it to find the exact record. |
| 6 | `assistance_award_unique_key` (rename to `award_id`) | Award ID | USAspending's key for the whole award; the source link is built from it. |
| 7 | `award_id_fain` (rename to `fain`) | Award number | The award's Federal Award Identification Number; several transactions can share one. |
| 8 | `action_date` | Action date | The date the agency took this action. |
| 9 | `fiscal_year` | Fiscal year | The federal fiscal year of the action (October to September), which is what USAspending reports and what the year filter uses. |
| 10 | `fy_partial_flag` | Partial fiscal year | Whether this row falls in a fiscal year the source had not finished reporting when Cedar pulled it (yes or no). Do not compare a partial year to a complete one. |
| 11 | `recipient_name` | Recipient as recorded | The recipient's name as the award records it, before Cedar resolved it to the entity. |
| 12 | `recipient_uei` | Recipient UEI | The recipient's federal Unique Entity ID. |
| 13 | `business_types_code` (combines into `recipient_type`) | Business types code | One of three overlapping recipient-type fields, consolidated through the source-code dictionary with conflict checks. |
| 14 | `business_types_description` (combines into `recipient_type`) | Recipient type as recorded | How USAspending classifies the recipient (for example, federally recognized tribal government). |
| 15 | `business_types_description_normalized` (combines into `recipient_type`) | Recipient type | The normalized spelling, the third of the three. |
| 16 | `assistance_type` (rename to `assistance_type_code`) | Assistance type code | The source's code for the assistance type (grant, loan, direct payment, insurance), defined in the dictionary; the readable type is beside it. |
| 17 | `assistance_type_description` (rename to `assistance_type`) | Assistance type | What kind of assistance it is: formula grant, project grant, direct payment, loan, insurance. |
| 18 | `cfda` (rename to `program_code`) | Program number | The Assistance Listing (CFDA) number of the federal program. |
| 19 | `cfda_title` (rename to `program_name`) | Program | The federal program's name. |
| 20 | `awarding_agency_name` (rename to `awarding_agency`) | Agency | The department that made the award. |
| 21 | `awarding_sub_agency_name` (rename to `awarding_subagency`) | Office | The office within the department. |
| 22 | `obligated_usd` (rename to `obligations_usd`) | Amount obligated | Dollars obligated by this transaction. Negative values are de-obligations, kept as recorded. |
| 23 | `obligated_usd_real2025` (rename to `obligations_usd_real2025`) | Amount in 2025 dollars | The same amount adjusted for inflation to 2025 dollars. |
| 24 | `face_value_of_loan` (rename to `loan_face_value_usd`) | Loan face value | For loans, the face value of this loan; zero for grants. |
| 25 | `original_loan_subsidy_cost` (rename to `loan_subsidy_cost_usd`) | Original loan subsidy cost | For a loan, the government's estimated cost of the subsidy when it was made. A loan measure; never added to obligations. |
| 26 | `total_face_value_of_loan` (rename to `total_loan_face_value_usd`) | Award loan face value | For loans, the face value of the whole award to date. |
| 27 | `total_loan_subsidy_cost` (rename to `total_loan_subsidy_cost_usd`) | Total loan subsidy cost | The subsidy cost across the award's loan actions. Never added to obligations. |
| 28 | `recipient_city_name` (rename to `recipient_city`) | Recipient city | City of the recipient's address on the award. |
| 29 | `recipient_state_code` (rename to `recipient_state`) | Recipient state | State of the recipient's address on the award. |
| 30 | `geo_recipient_county_name` (rename to `recipient_county`) | Recipient county | The county of the recipient's address, which is not necessarily where the funded work happens. |
| 31 | `geo_recipient_county_fips` (rename to `recipient_county_fips`) | Recipient county FIPS | The county code of the recipient's address. |
| 32 | `geo_pop_county_name` (rename to `performance_county`) | Place of performance county | The county where the funded work is performed, as the award reports it. |
| 33 | `geo_pop_county_fips` (rename to `performance_county_fips`) | Place of performance county FIPS | The county code where the funded work is performed, as the award reports it. |
| 34 | `recipient_geography_status` (to add in the compatibility transform) | Recipient geography status | Whether the recipient's address was placed in a county: placed, placed with an ambiguous place name, or unplaced. |
| 35 | `performance_geography_status` (to add in the compatibility transform) | Performance geography status | The same for the place of performance. |
| 36 | `attributed_flag` | Attributed to the entity | Whether Cedar attributes this transaction to the Native entity (yes) or keeps it in the file unattributed (no). Cedar's totals count attributed rows only. |
| 37 | `attribution_status` | Attribution status | How the attribution stands: attributed through the register, unattributed, or under review. |
| 38 | `source_system` (to add in the compatibility transform) | Source system | Which source the record came from. |
| 39 | `source_vintage` | Source vintage | The date stamp of the archive the row was taken from. |
| 40 | `source_url` (to add in the compatibility transform) | Source | The official page for this record, written into the file so it cites itself. |
| 41 | `research_note` (to add in the compatibility transform) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Federal Register

Collection `federal-register` · table `consultation_events` · compatibility reference; not the manifest's installed spreadsheet

**One row is:** One tribal consultation event announced or reported in the Federal Register, one row per event and named participant (most events name no single tribe).

**Release or source location:** workspace dist/customer/federal-register.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/federal-register/consultation_events.csv; built from Federal Register documents.

**Fields (34):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` (to add in the compatibility transform) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_class` (to add in the compatibility transform) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (to add in the compatibility transform) | Entity role | Why the entity is on this row: participant. |
| 5 | `consultation_event_id` | Event ID | Cedar's identifier for the consultation event. |
| 6 | `consultation_record_key` (to add in the compatibility transform) | Record key | Identifies this row within this collection: a JSON array of the notice's consultation event ID, the participant name as published and the participant's role. Use it to cite or deduplicate a row. It is not a Cedar ID and identifies no event or entity outside this table. |
| 7 | `fr_document_number` | Document number | The Federal Register document number. |
| 8 | `agency` | Agency | The department holding the consultation. |
| 9 | `sub_agency` (rename to `subagency`) | Office | The office within the department. |
| 10 | `program` | Program | The program or matter the consultation concerns, where the document names one. |
| 11 | `consultation_type` (rename to `activity_type`) | Kind of consultation | Whether this is a consultation session, a notice of consultation, or a consultation reported inside another document. |
| 12 | `topic` | Topic | What the consultation was about, from the document's title. |
| 13 | `document_role` | Document role | Whether the document announces a consultation or reports one that already happened. |
| 14 | `notice_date` | Notice date | The date the Federal Register document was published. |
| 15 | `event_start_date` | Event start | When the consultation began, as the notice states it. |
| 16 | `event_end_date` | Event end | When it ended, where stated. |
| 17 | `event_date_precision` (to add in the compatibility transform) | Date precision | Whether the event date is known to the day, the month or the year, read from the date as the notice writes it; unstated when the notice gives no date. |
| 18 | `participant_name_as_published` (rename to `participant_name`) | Participant as published | The tribe or organization named in the document, as it spells it. |
| 19 | `participant_role` | Entity role | Why the entity is on this row: read from participant_role. |
| 20 | `entity_link_status` (to add in the compatibility transform) | Entity link status | Whether the participant on this row is linked to a Cedar entity: resolved when a registered link exists, no_individual_named when the notice names no individual participant, and unresolved when a participant is named but not yet linked. Unresolved is not a finding that no Native entity took part. |
| 21 | `collective_scopes` (to add in the compatibility transform) | Collective scopes | Not yet evaluated for this collection, so always null here. Null means the notice has not been checked for a population it applies to (such as every federally recognized tribe); it is neither an empty scope nor a universal one. |
| 22 | `location` | Location | Where the consultation was held. |
| 23 | `format` (rename to `event_format`) | Format | In person, virtual, teleconference, written comment, or a combination. |
| 24 | `comment_deadline` | Comment deadline | The date written comments were due, where stated. |
| 25 | `has_written_comments` | Written comments invited | Whether the document invites written comments (yes or no). |
| 26 | `has_summary` | Summary available (yes or no) | Whether a summary of the consultation is available from the source. |
| 27 | `has_transcript` | Transcript available (yes or no) | Whether a transcript is available from the source. |
| 28 | `is_event_primary_row` | Counts as one consultation | One row per event carries yes; the rest are additional participants of the same event. Count consultations by this column, not by rows. |
| 29 | `n_participant_rows_for_event` (rename to `participant_rows_per_event`) | Participant rows for this event | How many rows this event has in the file. |
| 30 | `federal_register_citation` | Citation | The Federal Register citation (volume FR page). |
| 31 | `source_system` (to add in the compatibility transform) | Source system | Which source the record came from. |
| 32 | `source_url` | Source | The document on federalregister.gov. |
| 33 | `source_quote` | Source passage | The sentence in the document this row was read from. |
| 34 | `research_note` (to add in the compatibility transform) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Legislation

Collection `legislation` · table `native_bills` · compatibility reference; not the manifest's installed spreadsheet

**One row is:** One bill in Congress that concerns Native nations or organizations, with the entities it names.

**Release or source location:** workspace dist/customer/legislation.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/legislation/native_bills.csv; built from the Congress.gov API.

**Fields (30):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uids` (to add in the compatibility transform) | Cedar IDs | The Native entities associated with this record, as a JSON array; one position per entity-role association. A named but unresolved party has null here and its name in the names-as-published column. |
| 2 | `canonical_names` (to add in the compatibility transform) | Native entities | Their register names, aligned position by position with the Cedar IDs. |
| 3 | `entity_classes` (to add in the compatibility transform) | Entity types | Their register classes, aligned. |
| 4 | `entity_roles` (to add in the compatibility transform) | Entity roles | The role of each association (affiliated, consulted, repatriation recipient; named in the bill), aligned. An entity in two roles occupies two positions. |
| 5 | `entity_names_as_published` (to add in the compatibility transform) | Names as published | What the source called each entity, aligned; null until Cedar supplies it from the relationship evidence. A register name is not proof of what the source said. |
| 6 | `bill_id` | Bill ID | Congress, chamber and number, for example 103-hr-2366. |
| 7 | `congress` | Congress | Which Congress (the 103rd, and so on). |
| 8 | `chamber` | Chamber | House or Senate. |
| 9 | `bill_type` | Bill type | hr, s, hjres and the like, as Congress.gov codes them. |
| 10 | `number` (rename to `bill_number`) | Number | The bill's number in its chamber. |
| 11 | `title` | Title | The bill's title. |
| 12 | `policy_area` | Policy area | Congress.gov's policy area for the bill. |
| 13 | `bill_scope` | Scope | Whether the bill is specific to one tribe or general to Indian Country. |
| 14 | `entity_class_scope` (rename to `affected_entity_classes`) | Relevance class scope | When the bill names no entity, the class of entity it is about (federally recognized tribes, Alaska Native corporations). Class-wide relevance, not any entity's class. |
| 15 | `collective_scopes` (to add in the compatibility transform) | Collective scopes | The population this record relates to, kept apart from the entities it names: a JSON array of {scope, relationship, as_of, as_of_rule, basis} elements from the vocabulary in data/cedar/scopes.json, [] when the record names no population, null when not evaluated. A scope is not an entity: it has no Cedar ID, is never counted as one and never receives dollars. |
| 16 | `affected_entities` (rename to `affected_entities_as_published`) | Affected entities as published | The entities the source itself names as affected, as it names them; empty where the source names none. |
| 17 | `introduced_date` | Introduced | The date the bill was introduced; the year filter uses this. |
| 18 | `sponsor` (rename to `sponsor_name`) | Sponsor | The sponsoring member, with party and state. |
| 19 | `sponsor_bioguide_id` | Sponsor ID | The sponsor's Biographical Directory identifier. |
| 20 | `cosponsor_count` | Cosponsors | How many members cosponsored it. |
| 21 | `latest_action` | Latest action | The most recent action recorded on the bill. |
| 22 | `latest_action_date` | Latest action date | When that action happened. |
| 23 | `outcome` | Outcome | Where the bill ended: enacted, passed one chamber, died in committee. |
| 24 | `companion_bill_id` | Companion bill | The matching bill in the other chamber, where one exists. |
| 25 | `n_rollcalls` (rename to `rollcall_count`) | Roll-call votes | How many recorded roll-call votes the bill had. |
| 26 | `n_entities_resolved` (rename to `resolved_entity_count`) | Resolved entities | How many of the named entities Cedar resolved to its register. |
| 27 | `entity_link_statuses` (to add in the compatibility transform) | Entity link statuses | How firmly each named entity resolves to the register, aligned with the Cedar IDs (A strongest). |
| 28 | `source_system` (to add in the compatibility transform) | Source system | Which source the record came from. |
| 29 | `source_url` (to add in the compatibility transform) | Source | The official page for this record, written into the file so it cites itself. |
| 30 | `research_note` (to add in the compatibility transform) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Indian Country Deals

Collection `deals` · table `deals_classified` · compatibility reference; not the manifest's installed spreadsheet

**One row is:** One announced transaction or award involving a Native party: an acquisition, a financing, a grant, a partnership.

**Release or source location:** workspace dist/customer/deals.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/deals/deals_classified.csv; assembled from announcements, filings and agency award lists.

**Fields (38):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `native_party_canonical_name` (rename to `canonical_name`) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_class` (to add in the compatibility transform) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (to add in the compatibility transform) | Entity role | The Native entity's relationship to the deal, published only when a source establishes it and blank otherwise. A blank role never implies that the entity owns, controls or funds any party to the deal. |
| 5 | `Deal_ID` (rename to `deal_id`) | Deal ID | Cedar's identifier for the deal. |
| 6 | `Event_Date` (rename to `event_date`) | Date | When the deal happened or was announced. |
| 7 | `Event_Date_precision` (rename to `event_date_precision`) | Date precision | Whether the date is known to the day, the month or the year. |
| 8 | `Event_Date_not_before` (rename to `event_date_not_before`) | Date not before | The earliest date the event could have happened, where the source gives an interval rather than a day. |
| 9 | `Event_Date_not_after` (rename to `event_date_not_after`) | Date not after | The latest date the event could have happened. |
| 10 | `Event_Year` (rename to `event_year`) | Year | The year of the event date. |
| 11 | `Deal_Title` (rename to `title`) | Title | A one-line description of the deal. |
| 12 | `Native_Party` (rename to `native_party_name`) | Native party as published | The Native party's name as the source gives it. |
| 13 | `Native_Party_Type` (rename to `native_party_type`) | Native party type as published | How the source describes the Native party. |
| 14 | `native_party_role` | Entity role | Why the entity is on this row: read from native_party_role (acquirer, borrower, issuer, partner, grantee, seller). |
| 15 | `Counterparty_or_Funder` (rename to `counterparty_or_funder`) | Counterparty or funder | The other side of the deal. |
| 16 | `Deal_Category` (combines into `deal_type`) | Category | Acquisition, grant or public financing, joint venture, and so on. |
| 17 | `deal_type` (to add in the compatibility transform) | Deal type | The kind of deal under Cedar's one reviewed deal taxonomy, mapped value by value from the source's own category. |
| 18 | `transaction_type` (combines into `deal_type`) | Transaction type | The third of three overlapping classifications; shown until the one taxonomy replaces all three. |
| 19 | `Event_Type` (combines into `transaction_structure`) | Event | What kind of event this row records (an acquisition of a 90% interest, an award). |
| 20 | `transaction_structure` (to add in the compatibility transform) | Transaction structure | How the transaction is structured, mapped value by value from the source's own event type. |
| 21 | `Industry` (rename to `industry`) | Industry | The industry the deal is in. |
| 22 | `sector` | Sector | The broad sector the deal belongs to, beside the finer industry. |
| 23 | `capital_source` | Capital source | Where the capital comes from: public, private or tribal. |
| 24 | `Status` (combines into `deal_status`) | Status | Completed, announced, awarded, pending. |
| 25 | `deal_status_std` (combines into `deal_status`) | Status (standardized) | The standardized status; shown until one status column replaces the two. |
| 26 | `deal_status` (to add in the compatibility transform) | Deal status | Where the deal stands under Cedar's reviewed status list, mapped value by value from the source's own status. |
| 27 | `Announced_Value_USD` (rename to `announced_value_usd`) | Announced value | The dollar value announced, where one was. |
| 28 | `Value_Type` (rename to `value_basis`) | What the value is | What the announced figure represents (consideration paid, grant amount, project cost). |
| 29 | `Project_Total_Value_USD` (rename to `project_total_value_usd`) | Project total | The total project value, where larger than the announced value. |
| 30 | `State` (rename to `state`) | State | The state the deal is located in. |
| 31 | `Location` (rename to `location`) | Location | The place, as the source gives it. |
| 32 | `Description` (rename to `description`) | Description | A longer description of the deal. |
| 33 | `Native_Connection` (rename to `native_connection`) | Native connection | Why this deal is in the collection: how the Native party is connected. |
| 34 | `Verification_Status` (rename to `verification_status`) | Verification | Whether the deal was verified against a primary source. |
| 35 | `Source_1` (rename to `source_url`) | Source | The primary source document or page. |
| 36 | `Source_1_Type` (rename to `source_type`) | Source type | What kind of document the primary source is. |
| 37 | `additional_sources` (to add in the compatibility transform) | Additional sources | Further public sources beyond the primary one, as a JSON list of {url, source_type}. |
| 38 | `research_note` (to add in the compatibility transform) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### NAGPRA

Collection `nagpra` · table `nagpra_notices` · compatibility reference; not the manifest's installed spreadsheet

**One row is:** One NAGPRA notice in the Federal Register (a notice of inventory completion or intent to repatriate), with the institution holding the remains or objects and the Native entities the notice names.

**Release or source location:** workspace dist/customer/nagpra.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/nagpra/nagpra_notices.csv; built from Federal Register NAGPRA notices.

**Fields (52):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uids` (to add in the compatibility transform) | Cedar IDs | The Native entities associated with this record, as a JSON array; one position per entity-role association. A named but unresolved party has null here and its name in the names-as-published column. |
| 2 | `canonical_names` (to add in the compatibility transform) | Native entities | Their register names, aligned position by position with the Cedar IDs. |
| 3 | `entity_classes` (to add in the compatibility transform) | Entity types | Their register classes, aligned. |
| 4 | `entity_roles` (to add in the compatibility transform) | Entity roles | The role of each association (affiliated, consulted, repatriation recipient; named in the bill), aligned. An entity in two roles occupies two positions. |
| 5 | `entity_names_as_published` (to add in the compatibility transform) | Names as published | What the source called each entity, aligned; null until Cedar supplies it from the relationship evidence. A register name is not proof of what the source said. |
| 6 | `document_number` | Document number | The Federal Register document number. |
| 7 | `publication_date` | Published | The date the notice was published. |
| 8 | `publication_year` | Publication year | The year the notice was published. |
| 9 | `notice_type` | Notice type | Inventory completion, intent to repatriate, or correction. |
| 10 | `statute_stage` (rename to `process_stage`) | Statute stage | Which stage of NAGPRA the notice is made under. |
| 11 | `is_correction` | Correction | Whether this notice corrects an earlier one (yes or no). |
| 12 | `title` | Title | The notice's title. |
| 13 | `institution_name` | Institution | The museum, university or agency holding the remains or objects. |
| 14 | `additional_institution_names` (to add in the compatibility transform) | Additional institutions | The institutions the notice names beyond the designated one, as a JSON list. |
| 15 | `institution_city` | Institution city | Where the institution is. |
| 16 | `institution_state` | Institution state | Its state. |
| 17 | `institution_type_derived` (rename to `institution_type`) | Institution type | Museum, university, federal agency, and so on. |
| 18 | `institution_split_flag` | Institution split (yes or no) | Whether the notice's institution field named several institutions that were split into the designated one and the additional ones. |
| 19 | `responsible_party_statement` | Responsible party | The official the notice names as responsible for the holdings, as stated. |
| 20 | `agency_names` | Publishing agency | The agency that published the notice. |
| 21 | `object_categories` | Object categories | Which categories of items the notice covers (human remains, associated funerary objects, sacred objects, objects of cultural patrimony). |
| 22 | `mni_total_stated` (rename to `individuals_stated`) | Individuals | The minimum number of individuals the notice states. |
| 23 | `mni_statements` (rename to `individuals_statement`) | Individuals count, as stated | The sentence stating the minimum number of individuals, kept where the number alone is ambiguous. |
| 24 | `n_associated_funerary_objects_stated` (rename to `associated_funerary_objects_stated`) | Associated funerary objects | Count stated in the notice. |
| 25 | `n_unassociated_funerary_objects_stated` (rename to `unassociated_funerary_objects_stated`) | Unassociated funerary objects | Count stated in the notice. |
| 26 | `n_sacred_objects_stated` (rename to `sacred_objects_stated`) | Sacred objects | Count stated in the notice. |
| 27 | `n_objects_of_cultural_patrimony_stated` (rename to `cultural_patrimony_objects_stated`) | Objects of cultural patrimony | Count stated in the notice. |
| 28 | `cultural_items_total_stated` | Cultural items total, as stated | A total the notice itself states. Cedar never adds the categories together. |
| 29 | `removal_counties` | Removal counties | Where the remains or objects were removed from. |
| 30 | `removal_states` | Removal states | The states of those places. |
| 31 | `removal_location_statements` (rename to `removal_location`) | Removal location | Where the holdings were removed from, as the notice states it, with the existing restrictions on sensitive location applied before export. |
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
| 52 | `research_note` (to add in the compatibility transform) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Native Federal Advocacy and Engagement

Collection `lobbying` · table `native_entity_lobbying_disclosures` · compatibility reference; not the manifest's installed spreadsheet

**One row is:** One federal lobbying filing under the Lobbying Disclosure Act in which the client is a Native entity, one row per filing (amended filings appear once, as the current version).

**Release or source location:** workspace dist/customer/lobbying.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/lobbying/native_entity_lobbying_disclosures.csv; built from the Senate LDA filings database.

**Fields (38):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_type` (rename to `entity_class`) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (to add in the compatibility transform) | Entity role | Why the entity is on this row: client. |
| 5 | `activity_id` (to add in the compatibility transform) | Activity ID | A stable, source-based identifier for the activity (lda:<filing uuid> for a filing). |
| 6 | `activity_type` (to add in the compatibility transform) | Activity type | Which kind of documented advocacy the row is. Every row today is an LDA filing; other source families populate other values only as they are actually sourced. |
| 7 | `filing_uuid` (rename to `source_record_id`) | Filing ID | The filing's identifier in the Senate LDA database. |
| 8 | `filing_year` (rename to `reporting_year`) | Filing year | The year the filing covers. |
| 9 | `filing_period` (rename to `reporting_period`) | Period | Which reporting period of the year. |
| 10 | `dt_posted` (rename to `activity_date`) | Posted | When the filing was posted. |
| 11 | `filing_type_display` (rename to `activity_title`) | Filing type | Registration, quarterly or year-end report, amendment, termination. |
| 12 | `client_name` | Client | The client as the filing names it (the Native entity, in its own spelling). |
| 13 | `client_id` | Client ID | The client's identifier in the Lobbying Disclosure Act database. |
| 14 | `client_state` | Client state | The client's state. |
| 15 | `registrant_name` | Registrant | The lobbying firm or, for a self-filer, the client itself. |
| 16 | `registrant_id` | Registrant ID | The registrant's identifier in the Lobbying Disclosure Act database. |
| 17 | `registrant_state` | Registrant state | The registrant's state. |
| 18 | `self_filed` | Self-filed | Whether the client filed for itself rather than through a firm (yes or no). |
| 19 | `participant_name` (to add in the compatibility transform) | Participant | The participant as the source names it, for consultations, testimony and meetings; blank for a filing. |
| 20 | `participant_role` (to add in the compatibility transform) | Participant role | The participant's role, for consultations, testimony and meetings; blank for a filing. |
| 21 | `government_entities` (rename to `government_bodies`) | Government entities contacted | Agencies and chambers the filing lists, separated by \|. |
| 22 | `lobbying_issues_codes` (rename to `issue_codes`) | Issue codes | The LDA issue area codes on the filing. |
| 23 | `specific_issues_text` (rename to `issues_text`) | Specific issues | What the filing says was lobbied on. |
| 24 | `affiliated_organizations` | Affiliated organizations | Organizations the filing lists as affiliated with the client. |
| 25 | `income_usd` | Income reported | What the registrant reported receiving from the client this period. |
| 26 | `expenses_usd` | Expenses reported | What a self-filer reported spending this period. |
| 27 | `spend_usd` (rename to `reported_amount_usd`) | Reported spend | Whichever of the two the filing reports; the basis column says which. |
| 28 | `spend_basis` (rename to `amount_basis`) | Basis of spend | Income, expenses, or none reported. |
| 29 | `termination_date` | Termination date | When the registration was terminated, where the filing is a termination. |
| 30 | `supersession_status` | Version status | Whether a later amendment replaces this filing. |
| 31 | `is_superseded` | Superseded (yes or no) | Whether a later filing replaces this one; the default view counts current filings only. |
| 32 | `superseded_by_filing_uuid` (rename to `superseded_by_record_id`) | Replaced by | The filing that replaces this one, where one does. |
| 33 | `supersession_group_id` | Supersession group | The group of filings (an original and its amendments) this filing belongs to. |
| 34 | `attribution_withdrawn` | Attribution withdrawn | Whether Cedar withdrew its link between this filing and the entity after review (yes or no). A withdrawn filing stays in the file; its spend is not counted as the entity's. |
| 35 | `attribution_withdrawn_reason` | Why withdrawn | The reason recorded for the withdrawal. |
| 36 | `source_system` (to add in the compatibility transform) | Source system | Which source the record came from. |
| 37 | `filing_url` (rename to `source_url`) | Source | The filing on lda.senate.gov. |
| 38 | `research_note` (to add in the compatibility transform) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Native Federal Contractors

Collection `contractors` · table `prime_contracts` · compatibility reference; not the manifest's installed spreadsheet

**One row is:** One federal contract transaction (an award or a modification) to a firm owned by a Native entity, as reported to FPDS and published on USAspending.

**Release or source location:** workspace dist/customer/contractors.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/contractors/prime_contracts.csv; built from the USAspending contract archive.

**Fields (51):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_class` (to add in the compatibility transform) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (to add in the compatibility transform) | Entity role | Why the entity is on this row: owner of the awardee. |
| 5 | `contract_transaction_unique_key` (rename to `transaction_id`) | Transaction ID | USAspending's key for this transaction. |
| 6 | `contract_award_unique_key` (rename to `award_id`) | Award ID | USAspending's key for the whole award; the source link is built from it. |
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
| 18 | `award_base_description` (rename to `description`) | Description | The award's own description of the work. |
| 19 | `naics_code` | NAICS | The industry code of the work. |
| 20 | `naics_description` | Industry | What that code means. |
| 21 | `product_or_service_code` (rename to `psc_code`) | Product or service code | The federal product or service code (PSC), defined in the dictionary; the description is beside it. |
| 22 | `product_or_service_code_description` (rename to `psc_description`) | Product or service | What was bought. |
| 23 | `sector` (combines into `sector`) | Sector | The two-digit sector code and the readable group consolidated into one readable sector through the dictionary. |
| 24 | `supersector` (combines into `sector`) | Industry group | The broad industry group the contract's NAICS code belongs to. |
| 25 | `total_obligations` (rename to `obligations_usd`) | Amount obligated | Dollars obligated by this transaction. Sum these, never the award value. |
| 26 | `total_obligations_real2025` (rename to `obligations_usd_real2025`) | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. |
| 27 | `total_award_value` (rename to `cumulative_award_value_usd`) | Award value to date | The whole award's value as restated on this row. Cumulative: never add it across rows. |
| 28 | `setaside_reported` (rename to `set_aside_reported`) | Set-aside reported (yes or no) | Whether the award reports any set-aside; the classification beside it says which. |
| 29 | `setaside` (rename to `set_aside_classification`) | Set-aside | The set-aside the award was made under, if any. |
| 30 | `reported_8a` | 8(a) reported | Whether the award reports the 8(a) program (yes or no). |
| 31 | `reported_buy_indian` | Buy Indian Act reported (yes or no) | Whether the award reports use of the Buy Indian Act preference. Reported use, not eligibility. |
| 32 | `reported_indian_business` | Indian business reported (yes or no) | Whether the award reports the contractor as an Indian business under the relevant preference. |
| 33 | `reported_native_preference` | Native preference reported | Whether the award reports a Native preference (yes or no). |
| 34 | `extent_competed` (combines into `competition_type`) | Extent competed | Raw and normalized competition labels consolidated through a validated dictionary. |
| 35 | `extent_competed_normalized` (combines into `competition_type`) | Competition | How the award was competed. |
| 36 | `recipient_city_name` (rename to `recipient_city`) | Awardee city | City of the awardee's address. |
| 37 | `recipient_state_code` (rename to `recipient_state`) | Awardee state | Its state. |
| 38 | `geo_recipient_county_name` (rename to `recipient_county`) | Recipient county | The county of the contractor's address, which is not where the work is performed. |
| 39 | `geo_recipient_county_fips` (rename to `recipient_county_fips`) | Recipient county FIPS | The county code of the contractor's address. |
| 40 | `place_of_perform_city` (rename to `performance_city`) | Place of performance | City where the work is performed. |
| 41 | `place_of_perform_state` (rename to `performance_state`) | Place of performance state | Its state. |
| 42 | `geo_pop_county_name` (rename to `performance_county`) | Place of performance county | The county where the contract is performed, as the award reports it. |
| 43 | `geo_pop_county_fips` (rename to `performance_county_fips`) | Place of performance county FIPS | The county code where the contract is performed. |
| 44 | `recipient_geography_status` (to add in the compatibility transform) | Recipient geography status | Whether the recipient's address was placed in a county: placed, placed with an ambiguous place name, or unplaced. |
| 45 | `performance_geography_status` (to add in the compatibility transform) | Performance geography status | The same for the place of performance. |
| 46 | `attributed_flag` | Attributed (yes or no) | Whether the row is attributed to the Native entity in the opening block; the totals count attributed rows only. |
| 47 | `owner_attribution_status` (rename to `affiliation_attribution_status`) | Affiliation status at the time | How the sources describe the entity's relationship to the awardee as of the transaction. A source-described assessment: Cedar does not independently certify ownership. |
| 48 | `owner_as_of_transaction_cedar_uid` (rename to `affiliation_as_of_transaction_cedar_uid`) | Affiliated entity as of the action | The Cedar ID of the entity the sources associate with the contractor on the action date, where the affiliation history resolves it; UNKNOWN where it does not. Never today's affiliation assumed backwards, and not a certification of ownership. |
| 49 | `source_system` (to add in the compatibility transform) | Source system | Which source the record came from. |
| 50 | `source_url` (to add in the compatibility transform) | Source | The official page for this record, written into the file so it cites itself. |
| 51 | `research_note` (to add in the compatibility transform) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Native Subcontracting

Collection `subcontracting` · table `subawards` · compatibility reference; not the manifest's installed spreadsheet

**One row is:** One reported federal subaward or version with source-attributed Native-entity associations. Those associations do not establish ownership at the action date.

**Release or source location:** workspace dist/customer/subcontracting.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/subcontracting/subawards.csv; built from the USAspending FSRS subaward pull.

**Fields (54):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` (to add in the compatibility transform) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_class` (to add in the compatibility transform) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (to add in the compatibility transform) | Entity role | The side of the source-attributed Native-entity association after publication masks. Separate prime_cedar_uid and sub_cedar_uid retain the links; ownership at the action date is not established. |
| 5 | `subaward_source_record_id` (rename to `subaward_record_id`) | Subaward ID | The subaward report's identifier. |
| 6 | `subaward_number` | Subaward number | The subaward's own number as the prime reported it. |
| 7 | `subaward_sam_report_id` (rename to `report_id`) | Report ID | The SAM subaward report's identifier: the version of the report this row comes from. |
| 8 | `subaward_date` | Subaward date | The date of the subaward. |
| 9 | `fiscal_year` | Fiscal year | The federal fiscal year of the subaward. |
| 10 | `subaward_sam_report_year` (rename to `report_year`) | Report year | The year of the report the subaward was filed in: the reporting period. |
| 11 | `award_kind` | Award type | Whether the prime award is a contract or an assistance award. The two populations are never combined in a total. |
| 12 | `subaward_type` | Subaward type | Sub-contract or sub-grant, as reported. |
| 13 | `description` | Description | What the subcontract is for, as reported. |
| 14 | `sub_name` (rename to `subcontractor_name`) | Subcontractor | The subcontractor as reported. |
| 15 | `sub_uei` (rename to `subcontractor_uei`) | Subcontractor UEI | Its Unique Entity ID. |
| 16 | `sub_cage` (rename to `subcontractor_cage`) | Subcontractor CAGE | Its CAGE code, where reported. |
| 17 | `sub_parent_name` (rename to `subcontractor_parent_name`) | Subcontractor's parent | Its parent as reported. |
| 18 | `sub_parent_uei` (rename to `subcontractor_parent_uei`) | Subrecipient parent UEI | The UEI of the subrecipient's declared parent. |
| 19 | `sub_parent_cage` (rename to `subcontractor_parent_cage`) | Subrecipient parent CAGE | The CAGE code of the subrecipient's declared parent. |
| 20 | `sub_cedar_uid` | Subcontractor's Cedar ID | The source-attributed Native entity associated with the subcontractor. This does not establish ownership or its effective dates. |
| 21 | `prime_name` | Prime contractor | The prime as reported. |
| 22 | `prime_uei` | Prime UEI | Its Unique Entity ID. |
| 23 | `prime_cage` | Prime CAGE | Its CAGE code, where reported. |
| 24 | `prime_parent_name` | Prime's parent | Its parent as reported. |
| 25 | `prime_parent_uei` | Prime parent UEI | The UEI of the prime's declared parent. |
| 26 | `prime_parent_cage` | Prime parent CAGE | The CAGE code of the prime's declared parent. |
| 27 | `prime_cedar_uid` | Prime's Cedar ID | The source-attributed Native entity associated with the prime. This does not establish ownership or its effective dates. |
| 28 | `direction` (rename to `native_direction`) | Source Native association | The retained source classification of which side has a Native-entity association. It is not independently verified ownership at the subaward action date. |
| 29 | `prime_award_id` | Prime award number | The prime contract's number. |
| 30 | `prime_award_unique_key` | Prime award key | USAspending's key for the prime award. |
| 31 | `subaward_amount` (rename to `subaward_amount_usd`) | Subaward amount | Dollars of the subaward. |
| 32 | `subaward_amount_real2025` (rename to `subaward_amount_usd_real2025`) | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. |
| 33 | `prime_award_amount` (rename to `prime_award_amount_usd`) | Prime award amount | The prime contract's value. |
| 34 | `subaward_to_prime_ratio` | Subaward to prime ratio | The subaward amount divided by the prime award amount, with the amount, period and version definitions the guide states; never recomputed from incompatible snapshots. |
| 35 | `prime_top_awarding_agency` (rename to `awarding_agency`) | Agency | The department that awarded the prime contract. |
| 36 | `prime_awarding_sub_agency` (rename to `awarding_subagency`) | Office | The office within it. |
| 37 | `prime_set_aside` | Prime set-aside | The set-aside category of the prime award, where reported. |
| 38 | `naics` (rename to `naics_code`) | NAICS | The industry code. |
| 39 | `naics_title` (rename to `naics_description`) | Industry | What that code means. |
| 40 | `psc` (rename to `psc_code`) | Product or service code | The federal product or service code of the subaward, where reported. |
| 41 | `psc_title` (rename to `psc_description`) | Product or service | What the product or service code means. |
| 42 | `sub_business_types` (rename to `subcontractor_business_types`) | Subcontractor business types | The business types it reports (for example, Alaska Native Corporation owned). |
| 43 | `geo_subawardee_city` (rename to `subcontractor_city`) | Subrecipient city | The subrecipient's own city, never filled from the prime's address. |
| 44 | `sub_state` (rename to `subcontractor_state`) | Subcontractor state | Its state. |
| 45 | `geo_subawardee_county_name` (rename to `subcontractor_county`) | Subrecipient county | The county of the subrecipient's address. |
| 46 | `geo_subawardee_county_fips` (rename to `subcontractor_county_fips`) | Subrecipient county FIPS | The county code of the subrecipient's address. |
| 47 | `geo_subawardee_country_code` (rename to `subcontractor_country`) | Subrecipient country | The subrecipient's country code. |
| 48 | `subcontractor_geography_status` (to add in the compatibility transform) | Subcontractor geography status | Whether the subcontractor's own address was placed in a county: placed, placed with an ambiguous place name, or unplaced. Never filled from the prime's address. |
| 49 | `duplicate_status` | Duplicate status | Whether this row is the primary filing or a duplicate of one. Sum primaries only. |
| 50 | `subaward_exceeds_prime_flag` | Exceeds the prime award | Whether the subaward amount exceeds its prime award (yes or no). A real filing, kept in the file, but never added into totals. |
| 51 | `action_date_precedes_ffata_flag` | Date before FFATA | Whether the reported action date precedes FFATA reporting. This is a chronology-review flag; it does not prove a typo or supply a corrected date. |
| 52 | `source_dataset` (rename to `source_system`) | Source system | Which source the report came from (the USAspending FSRS pull). |
| 53 | `source_url` | Source | The prime award's page on USAspending. |
| 54 | `research_note` (to add in the compatibility transform) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Native-Owned Businesses

Collection `owned` · table `native_owned_businesses` · compatibility reference; not the manifest's installed spreadsheet

**One row is:** One business owned by a Native entity, in the register of such businesses.

**Release or source location:** workspace dist/customer/owned.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/native-owned-businesses/native_owned_businesses.csv. NOT AUDITED: the sample is not in the repository yet; run scripts/import_cedar_manifest.py --audit after adding it.

**Fields (32):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` (to add in the compatibility transform) | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` (to add in the compatibility transform) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_class` (to add in the compatibility transform) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (to add in the compatibility transform) | Entity role | Why the entity is on this row: certifying_authority. |
| 5 | `business_source_id` | Business source id |  |
| 6 | `business_name_raw` (rename to `business_name`) | Business name |  |
| 7 | `business_entity_id` | Business entity id |  |
| 8 | `certifying_authority_entity_id` | Certifying authority entity id |  |
| 9 | `certifying_authority_name` | Certifying authority name |  |
| 10 | `programme_name` (rename to `program_name`) | Program name |  |
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
| 22 | `service_category_raw` (rename to `service_category`) | Service category |  |
| 23 | `naics` (rename to `naics_code`) | Naics code |  |
| 24 | `city` | City |  |
| 25 | `state_province` (rename to `state`) | State |  |
| 26 | `source_edition` | Source edition |  |
| 27 | `source_last_updated` | Source last updated |  |
| 28 | `first_seen` | First seen |  |
| 29 | `last_seen` | Last seen |  |
| 30 | `is_current` | Is current |  |
| 31 | `source_url` | Source | The official page for this record, written into the file so it cites itself. |
| 32 | `research_note` (to add in the compatibility transform) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Native Enterprises

Collection `need` · table `need_enterprises` · compatibility reference; not the manifest's installed spreadsheet

**One row is:** One enterprise (a subsidiary, a joint venture, an affiliate) with the Native entity that owns or is affiliated with it and how.

**Release or source location:** workspace dist/customer/need.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/need/need_enterprises.csv; built from owners' own subsidiary listings, annual reports and federal identifier records.

**Fields (30):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `owner_hub_name` (rename to `canonical_name`) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `owner_hub_entity_class` (rename to `entity_class`) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (to add in the compatibility transform) | Entity role | Why the entity is on this row: read from relationship_type. |
| 5 | `enterprise_id` | Enterprise ID | Cedar's identifier for the enterprise. |
| 6 | `enterprise_name` | Enterprise | The enterprise's name. |
| 7 | `name_variants_observed` (rename to `alternative_names`) | Also seen as | Other spellings of the name in the sources, separated by \|. |
| 8 | `parent_enterprise_id` | Parent enterprise ID | The immediate parent enterprise's ID, where the parent is an enterprise rather than the Native entity itself. |
| 9 | `parent_name` | Parent | The immediate parent, which may itself be an enterprise. |
| 10 | `relation_class` (rename to `relationship_type`) | Entity role | Why the entity is on this row: read from relationship_type: owner, or affiliated entity, of the enterprise. |
| 11 | `relationship_as_recorded` | Relationship as recorded | The relationship in the source's own words, beside the normalized relationship type. |
| 12 | `ownership_percent_stated` (rename to `ownership_percent`) | Ownership share | The percentage owned, where a source states it. |
| 13 | `sector` | Sector | The enterprise's sector. |
| 14 | `status` (rename to `operating_status`) | Status | Operating, dissolved, or unknown. |
| 15 | `city` | City | Where the enterprise is. |
| 16 | `state_province` (rename to `state`) | State | Its state or province. |
| 17 | `uei` | UEI | Its federal Unique Entity ID, where one is published. |
| 18 | `cage_code` | CAGE code | The enterprise's CAGE code, where known. |
| 19 | `in_federal_contracting` | Federal contractor | Whether the enterprise appears in federal contracting records (yes or no). |
| 20 | `first_observed_year` | First seen | The earliest year a source names the enterprise. |
| 21 | `last_observed_year` | Last seen | The latest. |
| 22 | `n_distinct_sources` (rename to `source_count`) | Sources | How many distinct sources support the relationship. |
| 23 | `evidence_class` (rename to `relationship_evidence_status`) | Kind of evidence | What kind of source establishes the relationship (the owner's own list, an audited report, a resolver). |
| 24 | `fpds_declared_parent_name` (rename to `reported_federal_parent_name`) | Parent declared in FPDS | The parent the enterprise declares in federal contracting records, kept as evidence beside Cedar's relationship. |
| 25 | `fpds_parent_corroboration` (rename to `federal_parent_corroboration`) | Federal records agree | Whether the parent the enterprise declares in federal records agrees with this owner. |
| 26 | `source_document` | Source document | The document, where the source is a file. |
| 27 | `source_edition_date` | Source date | The date of that source. |
| 28 | `source_url` | Source | Where the relationship is stated. |
| 29 | `additional_source_urls` (to add in the compatibility transform) | Additional source URLs | Further source URLs, as a JSON list; blank until the sources table supplies them. |
| 30 | `research_note` (to add in the compatibility transform) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Natural Resource Revenue

Collection `natural-resources` · table `resource_revenue` · compatibility reference; not the manifest's installed spreadsheet

**One row is:** One payment or distribution of natural-resource revenue (royalties, severance tax shares, reclamation distributions) to a Native entity.

**Release or source location:** workspace dist/customer/natural-resources.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/natural-resources/resource_revenue.csv; built from federal and state revenue records.

**Fields (38):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` (to add in the compatibility transform) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `entity_class` (to add in the compatibility transform) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (to add in the compatibility transform) | Entity role | Why the entity is on this row: recipient. |
| 5 | `resource_revenue_event_id` | Payment ID | Cedar's identifier for the payment. |
| 6 | `source_record_id` | Source record ID | The record's identifier in that source. |
| 7 | `recipient_entity_name` (rename to `recipient_name`) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. |
| 8 | `beneficiary_entity_id` | Beneficiary ID | The identifier of the beneficiary where it differs from the recipient. |
| 9 | `beneficiary_entity_name` (rename to `beneficiary_name`) | Beneficiary | Who the payment is for, where different from the recipient. |
| 10 | `payer_entity_id` | Payer ID | The identifier of the payer. |
| 11 | `payer_entity_name` (rename to `payer_name`) | Payer | Who made the payment (a federal office, a state). |
| 12 | `operator_entity_id` | Operator ID | The identifier of the related operator, where a source supports one. |
| 13 | `operator_entity_name` (rename to `operator_name`) | Operator | The related operator's name, where a source supports one. |
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
| 35 | `entity_attribution_status` (rename to `attribution_status`) | Attribution status | Whether the row is keyed to a Native entity, to an aggregate, or unresolved. A blank Cedar ID has a stated reason here. |
| 36 | `source_system` | Source system | Which source system the record came from. |
| 37 | `source_url` | Source | Where the payment is recorded. |
| 38 | `research_note` (to add in the compatibility transform) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Native Nonprofits

Collection `nonprofits` · table `np_orgs` · compatibility reference; not the manifest's installed spreadsheet

**One row is:** One nonprofit organization in the IRS Business Master File that is Native-led or tribally controlled, with the Native entity it is linked to.

**Release or source location:** workspace dist/customer/nonprofits.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/nonprofits/np_orgs.csv; built from the IRS Exempt Organizations Business Master File and Native-led directories.

**Fields (29):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 2 | `cedar_spine_canonical_name` (rename to `canonical_name`) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 3 | `cedar_spine_entity_class` (rename to `entity_class`) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (to add in the compatibility transform) | Entity role | Why the entity is on this row: associated Native entity. |
| 5 | `EIN` (rename to `ein`) | EIN | The organization's Employer Identification Number. |
| 6 | `org_name` (rename to `organization_name`) | Organization | The organization's name as the IRS records it. |
| 7 | `cedar_native_entity_class` (rename to `organization_entity_class`) | Organization type | Whether the organization is itself a tribe, an ANC, a Native organization. |
| 8 | `inclusion_category` (to add in the compatibility transform) | Inclusion basis | Why the organization is in the collection, read from primary sources through a documented crosswalk: Native-serving, Native-controlled, tribal government, or candidate. Candidate means inclusion is not yet confirmed. |
| 9 | `classification_ruling` (combines into `inclusion_category`) | Relationship to the entity | Whether the organization is tribally controlled, tribally affiliated, or unruled. |
| 10 | `disposition` (combines into `inclusion_category`) | Inclusion basis | Why the organization is in Cedar: verified strictly, verified, or a candidate. |
| 11 | `city` | City | Its city. |
| 12 | `state` | State | The organization's state. |
| 13 | `ntee_code` | NTEE code | The IRS activity code for what the organization does. |
| 14 | `bmf_status` (rename to `irs_status`) | IRS status code | The organization's status code in the Business Master File, defined in the dictionary. |
| 15 | `bmf_subsection` (rename to `irs_subsection`) | Tax subsection | The 501(c) subsection (3 for charities). |
| 16 | `bmf_foundation_cd` (rename to `irs_foundation_code`) | Foundation code | The IRS foundation classification code, defined in the dictionary. |
| 17 | `bmf_irs_ruling_yyyymm` (rename to `irs_ruling_month`) | IRS ruling date | When the IRS recognized the organization (year and month). |
| 18 | `bmf_tax_period` (rename to `tax_period`) | Latest tax period | The most recent tax period in the file. |
| 19 | `bmf_revenue_amt` (rename to `bmf_revenue_usd`) | Revenue | Revenue in the latest return the IRS holds. |
| 20 | `bmf_asset_amt` (rename to `bmf_assets_usd`) | Assets | Assets in that return. |
| 21 | `bmf_income_amt` (rename to `bmf_income_usd`) | Income | Income in that return. |
| 22 | `bmf_vintage_fetched` (rename to `bmf_as_of_date`) | IRS file date | The date of the IRS file these figures come from. |
| 23 | `entity_tier` (combines into `entity_link_status`) | Match confidence | Cedar's confidence in the link to the entity: A is strongest. |
| 24 | `cedar_link_tier` (combines into `entity_link_status`) | Cedar link tier | Shown until the combined column replaces it. |
| 25 | `entity_link_status` (to add in the compatibility transform) | Entity link status | Whether the organization's link to a Cedar entity has been validated, as one status through a documented crosswalk. An unvalidated link is not a finding that no Native entity is associated. |
| 26 | `key_review_disposition` (combines into `entity_link_status`) | Key review disposition | Shown until the combined column replaces it. |
| 27 | `source_dataset` (rename to `source_system`) | Source system | The source: the IRS Exempt Organizations Business Master File. |
| 28 | `source_url` | Source | The IRS Business Master File. |
| 29 | `research_note` (to add in the compatibility transform) | Research note | A concise factual qualification that changes how the row should be read (an uncertain closing date, an amount covering a whole joint venture, a geography that cannot be assigned precisely). Blank when nothing needs saying. |

### Native Federal Contractors

Collection `contractors` · table `contractors` · installed producer spreadsheet

**Rows in this installed spreadsheet:** 841,002. This is an observation count at the declared record types and grains.

**One row is:** One permitted observation at its declared record_type and record_grain.

**Release or source location:** Exact release 4df9d034a1bbb9b788ba63b5106a37e2da48cecb1c5ffdb2345a03e01456c7e3; one researcher spreadsheet.

The columns below describe the exported names directly. No legacy rename, combine or promised identity block is applied to this spreadsheet.

**Fields (52):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `record_type` | record type | The permitted logical record type from the pinned release. |
| 2 | `record_key` | record key | The original source primary-key values serialized as JSON. |
| 3 | `record_grain` | record grain | What one observation of this record type represents; never sum across overlapping grains. |
| 4 | `action_date` | Action date | The date of this award or modification. |
| 5 | `affiliation_as_of_transaction_cedar_uid` | Affiliated entity as of the action | The Cedar ID of the entity the sources associate with the contractor on the action date, where the affiliation history resolves it; UNKNOWN where it does not. Never today's affiliation assumed backwards, and not a certification of ownership. |
| 6 | `affiliation_attribution_status` | Affiliation status at the time | How the sources describe the entity's relationship to the awardee as of the transaction. A source-described assessment: Cedar does not independently certify ownership. |
| 7 | `attributed_flag` | Attributed (yes or no) | Whether the row is attributed to the Native entity in the opening block; the totals count attributed rows only. |
| 8 | `award_id` | Award ID | USAspending's key for the whole award; the source link is built from it. |
| 9 | `award_type` | Award type | Delivery order, BPA call, definitive contract, and so on. |
| 10 | `awardee_name` | Awardee | The contractor as the award names it. |
| 11 | `awardee_uei` | Awardee UEI | The contractor's federal Unique Entity ID. |
| 12 | `cage_code` | Awardee CAGE | The contractor's CAGE code, the identifier that persists across the DUNS-to-UEI change; masked on rows the publication rule withholds. |
| 13 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 14 | `cedar_entity_role` | cedar entity role | Relationship of the linked Cedar entity to the contractor transaction: source-attributed affiliation of awardee when cedar_uid is published. It is not independently certified ownership; any separately supported ownership at the action date uses the dedicated dated-relationship fields. |
| 15 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 16 | `competition_type` | competition type | Readable competition category normalized from the source extent_competed code through the pinned dictionary. Missing-source tokens map to NOT_REPORTED; unknown codes and conflicts with an existing normalized value are refused. |
| 17 | `contract_number` | Contract number | The contract or order number. |
| 18 | `cumulative_award_value_usd` | Award value to date | The whole award's value as restated on this row. Cumulative: never add it across rows. |
| 19 | `description` | Description | The award's own description of the work. |
| 20 | `entity_class` | entity class | Entity class from the pinned Cedar register for cedar_uid, blank when no reference is published. It describes the source-associated entity and does not establish the awardee's legal identity or ownership at the action date. |
| 21 | `fiscal_year` | Fiscal year | The federal fiscal year of the action. |
| 22 | `funding_agency` | Funding agency | The agency paying for the work. |
| 23 | `naics_code` | NAICS | The industry code of the work. |
| 24 | `naics_description` | Industry | What that code means. |
| 25 | `obligations_usd` | Amount obligated | Dollars obligated by this transaction. Sum these, never the award value. |
| 26 | `obligations_usd_real2025` | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. |
| 27 | `parent_contract_number` | Parent contract | The parent contract or vehicle, for orders. |
| 28 | `parent_name` | Awardee's parent | The contractor's parent as the award records it. |
| 29 | `parent_uei` | Parent UEI | The UEI of the parent FPDS declares for the contractor. |
| 30 | `performance_city` | Place of performance | City where the work is performed. |
| 31 | `performance_county` | Place of performance county | The county where the contract is performed, as the award reports it. |
| 32 | `performance_county_fips` | Place of performance county FIPS | The county code where the contract is performed. |
| 33 | `performance_geography_status` | performance geography status | Availability of the source place-of-performance county assignment: placed when a county name or FIPS exists, placed_ambiguous when the source ambiguity flag is also set, and unplaced when neither exists. It is not verification of where the contract work occurred. |
| 34 | `performance_state` | Place of performance state | Its state. |
| 35 | `psc_code` | Product or service code | The federal product or service code (PSC), defined in the dictionary; the description is beside it. |
| 36 | `psc_description` | Product or service | What was bought. |
| 37 | `recipient_city` | Awardee city | City of the awardee's address. |
| 38 | `recipient_county` | Recipient county | The county of the contractor's address, which is not where the work is performed. |
| 39 | `recipient_county_fips` | Recipient county FIPS | The county code of the contractor's address. |
| 40 | `recipient_geography_status` | recipient geography status | Availability of the award recipient's source county assignment: placed when a county name or FIPS exists, placed_ambiguous when the source ambiguity flag is set, and unplaced when neither exists. Recipient location and place of performance are separate concepts. |
| 41 | `recipient_state` | Awardee state | Its state. |
| 42 | `reported_8a` | 8(a) reported | Whether the award reports the 8(a) program (yes or no). |
| 43 | `reported_buy_indian` | Buy Indian Act reported (yes or no) | Whether the award reports use of the Buy Indian Act preference. Reported use, not eligibility. |
| 44 | `reported_indian_business` | Indian business reported (yes or no) | Whether the award reports the contractor as an Indian business under the relevant preference. |
| 45 | `reported_native_preference` | Native preference reported | Whether the award reports a Native preference (yes or no). |
| 46 | `research_note` | research note | Interpretive qualification stating that the amount is an incremental transaction obligation, cumulative award values are not additive, and the entity link is source-attributed affiliation. It retains the source relationship assessment and identifies publication masking where applied. |
| 47 | `sector` | sector | Readable sector decoded from the source sector and supersector through the pinned dictionary. It preserves the source code with its label, uses Not reported for the declared missing case, and explicitly identifies a sector whose group label was not reported rather than guessing one. |
| 48 | `set_aside_classification` | Set-aside | The set-aside the award was made under, if any. |
| 49 | `set_aside_reported` | Set-aside reported (yes or no) | Whether the award reports any set-aside; the classification beside it says which. |
| 50 | `source_system` | source system | Source-system label for the accepted prime-contract transaction lineage: usaspending_fpds, denoting FPDS contract information carried through USAspending. It does not indicate an independently collected new contract record. |
| 51 | `source_url` | source url | USAspending award-page URL constructed from the transaction's original contract award unique key. It points to the parent award page, which can contain multiple incremental actions. |
| 52 | `transaction_id` | Transaction ID | USAspending's key for this transaction. |

### Indian Country Deals

Collection `deals` · table `deals` · installed producer spreadsheet

**Rows in this installed spreadsheet:** 978. This is an observation count at the declared record types and grains.

**One row is:** One permitted observation at its declared record_type and record_grain.

**Release or source location:** Exact release f9f50ccadc3bfe10089e47a0c8710a3ac382651703571f38ed6a2d57ba47623b; one researcher spreadsheet.

The columns below describe the exported names directly. No legacy rename, combine or promised identity block is applied to this spreadsheet.

**Fields (36):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `record_type` | record type | The permitted logical record type from the pinned release. |
| 2 | `record_key` | record key | The original source primary-key values serialized as JSON. |
| 3 | `record_grain` | record grain | What one observation of this record type represents; never sum across overlapping grains. |
| 4 | `additional_sources` | additional sources | JSON array containing the optional secondary source as an object with url and normalized source_type. An empty array means no secondary source was supplied; the primary source remains in the separate primary-source fields. |
| 5 | `announced_value_usd` | Announced value | The dollar value announced, where one was. |
| 6 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 7 | `capital_source` | Capital source | Where the capital comes from: public, private or tribal. |
| 8 | `cedar_entity_role` | cedar entity role | Reserved role of the linked Cedar entity in the transaction. The current deals projection deliberately leaves it blank because an entity association alone does not establish ownership or a particular party's role. |
| 9 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 10 | `counterparty_or_funder` | Counterparty or funder | The other side of the deal. |
| 11 | `deal_id` | Deal ID | Cedar's identifier for the deal. |
| 12 | `deal_status` | deal status | Controlled status taken from the source's normalized status or derived through the reviewed source-status crosswalk. UNCLASSIFIED preserves an unresolved status and must not be read as closed, completed, or financially realized. |
| 13 | `deal_type` | deal type | Controlled transaction category taken from the source's transaction_type or derived through the reviewed Deal_Category crosswalk. Unresolved or unrecognized categories are held rather than assigned a guessed transaction type. |
| 14 | `description` | Description | A longer description of the deal. |
| 15 | `entity_class` | entity class | Entity class from the pinned Cedar register for the existing linked cedar_uid; blank when no entity reference is published. This class describes the associated entity and does not establish its ownership share or role in the transaction. |
| 16 | `event_date` | Date | When the deal happened or was announced. |
| 17 | `event_date_not_after` | Date not after | The latest date the event could have happened. |
| 18 | `event_date_not_before` | Date not before | The earliest date the event could have happened, where the source gives an interval rather than a day. |
| 19 | `event_date_precision` | Date precision | Whether the date is known to the day, the month or the year. |
| 20 | `event_year` | Year | The year of the event date. |
| 21 | `industry` | Industry | The industry the deal is in. |
| 22 | `location` | Location | The place, as the source gives it. |
| 23 | `native_connection` | Native connection | Why this deal is in the collection: how the Native party is connected. |
| 24 | `native_party_name` | Native party as published | The Native party's name as the source gives it. |
| 25 | `native_party_role` | Entity role | Why the entity is on this row: read from native_party_role (acquirer, borrower, issuer, partner, grantee, seller). |
| 26 | `native_party_type` | Native party type as published | How the source describes the Native party. |
| 27 | `project_total_value_usd` | Project total | The total project value, where larger than the announced value. |
| 28 | `research_note` | research note | Interpretive qualification assembled from substantive source notes, reviewed caveats, candidate and date-basis information, and source category/status context. It includes explicit cautions for overlapping project milestones or announcement rounds where applicable; it is not evidence that every reported amount is additive. |
| 29 | `sector` | Sector | The broad sector the deal belongs to, beside the finer industry. |
| 30 | `source_type` | Source type | What kind of document the primary source is. |
| 31 | `source_url` | Source | The primary source document or page. |
| 32 | `state` | State | The state the deal is located in. |
| 33 | `title` | Title | A one-line description of the deal. |
| 34 | `transaction_structure` | transaction structure | Source Event_Type text carried into the public transaction-structure field. It preserves the source's event characterization and is not an independently inferred legal, financing, or ownership structure. |
| 35 | `value_basis` | What the value is | What the announced figure represents (consideration paid, grant amount, project cost). |
| 36 | `verification_status` | Verification | Whether the deal was verified against a primary source. |

### Federal Register — Indian Affairs

Collection `federal-register` · table `federal-register` · installed producer spreadsheet

**Rows in this installed spreadsheet:** 21,258. This is an observation count at the declared record types and grains.

**One row is:** One permitted observation at its declared record_type and record_grain.

**Release or source location:** Exact release c28a84fb4e008363499eb23dbac5030ba2f279f90924ded090ddc6e251b711c2; one researcher spreadsheet.

The columns below describe the exported names directly. No legacy rename, combine or promised identity block is applied to this spreadsheet.

**Fields (61):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `record_type` | record type | The permitted logical record type from the pinned release. |
| 2 | `record_key` | record key | The original source primary-key values serialized as JSON. |
| 3 | `record_grain` | record grain | What one observation of this record type represents; never sum across overlapping grains. |
| 4 | `action` | Agency action | The action label supplied by the issuing agency for the Federal Register document, when reported; distinct from Cedar's source-text classification. |
| 5 | `activity_type` | Kind of consultation | Whether this is a consultation session, a notice of consultation, or a consultation reported inside another document. |
| 6 | `agency` | Agency | The department holding the consultation. |
| 7 | `agency_names` | Issuing agencies | Issuing agency names from the Federal Register source agency array, separated by semicolons. |
| 8 | `canonical_name` | Registered participant name | The pinned register's name for the participant's existing cedar_uid; blank when that row has no linked Cedar entity. The participant_name field preserves the published name. |
| 9 | `cedar_entity_role` | Cedar entity role | participant when the participant row has a linked cedar_uid; otherwise blank. The separate participant_role field preserves whether the source describes consultation, invitation, nonparticipation or unenumerated participants. |
| 10 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 11 | `cfr_references` | CFR references | Code of Federal Regulations references supplied for the source document, serialized as a JSON array when reported. |
| 12 | `classification_rule` | Text classification rule | The maintained first matching source-text classifier rule; blank when the document is unclassified other. This is Cedar classification provenance, not an agency taxonomy or a Native-entity link. |
| 13 | `classification_signal` | Classification evidence text | The source text matched by the classifier, limited to 160 characters, or the source document type used for a rulemaking classification. |
| 14 | `classification_source_field` | Classification source field | The field supporting the classification: title, abstract or the source document type. It identifies the evidence location, not a source agency or entity. |
| 15 | `collective_scopes` | Collective scopes | Blank for the consultation-participant projection because collective scope has not been evaluated for it (producer transform fr-participant-observations-v2 writes the empty cell; the earlier v1 wrote the text null, which is what a pinned sample built before it still shows). Blank does not mean an empty set, all tribes or an identified individual participant; an evaluated record would carry a JSON array, [] when it names no population. |
| 16 | `comment_deadline` | Comment deadline | The date written comments were due, where stated. |
| 17 | `consultation_event_id` | Event ID | Cedar's identifier for the consultation event. |
| 18 | `consultation_participants__source_system` | Participant observation source system | The value federal_register assigned by the consultation-participant projector. This identifies the source system, not the agency, the entity or the ingestion filename. |
| 19 | `consultation_participants__source_url` | Participant observation source | The original public source URL retained on the consultation-participant observation. It cites that observation's evidence and is distinct from the broad-document component's URL field. |
| 20 | `consultation_record_key` | Participant observation key | A deterministic JSON array of the preserved consultation_event_id, participant name as published and participant_role. It identifies one participant-role observation, not a distinct event or an entity. |
| 21 | `docket_ids` | Docket IDs | Docket identifiers supplied for the source document, serialized as a JSON array; these are source docket identifiers, not Cedar IDs. |
| 22 | `document_number` | Document number | The source-issued Federal Register document number. It identifies one source document, not one tribe, consultation event or participant. |
| 23 | `document_role` | Document role | Whether the document announces a consultation or reports one that already happened. |
| 24 | `effective_on` | Effective date | The legal effective date reported by the source document, when present. It is separate from the publication date and may be later or in the future. |
| 25 | `entity_class` | Registered participant class | The pinned register's entity class for the participant's existing cedar_uid; blank when no Cedar entity is linked to that participant row. |
| 26 | `entity_link_status` | Participant link status | resolved when a registered cedar_uid is present; no_individual_named when the participant role is not_enumerated and no entity is linked; otherwise unresolved. An unresolved link does not establish that no Native entity participated. |
| 27 | `event_date_precision` | Event date precision | Precision of the retained event_start_date: year, month or day for a valid date of that form, or unstated for a blank. The separate notice_date does not supply an event date. |
| 28 | `event_end_date` | Event end | When it ended, where stated. |
| 29 | `event_format` | Format | In person, virtual, teleconference, written comment, or a combination. |
| 30 | `event_start_date` | Event start | When the consultation began, as the notice states it. |
| 31 | `federal_actions__source_system` | Document source system | The value Federal Register assigned to the broad federal-action document component. It identifies the document source system, not the issuing agency, a Native entity or the source file name. |
| 32 | `federal_actions__source_url` | Document source page | The official Federal Register or GovInfo source URL preserved for the broad federal-action document record. This cites the document component and is separate from the consultation-participant component's source URL; it does not establish Native entity linkage. |
| 33 | `federal_register_citation` | Citation | The Federal Register citation (volume FR page). |
| 34 | `fr_document_number` | Document number | The Federal Register document number. |
| 35 | `has_summary` | Summary available (yes or no) | Whether a summary of the consultation is available from the source. |
| 36 | `has_transcript` | Transcript available (yes or no) | Whether a transcript is available from the source. |
| 37 | `has_written_comments` | Written comments invited | Whether the document invites written comments (yes or no). |
| 38 | `html_url` | Document page | The source-provided FederalRegister.gov page for the document; an informational rendition of the published document. |
| 39 | `is_event_primary_row` | Counts as one consultation | One row per event carries yes; the rest are additional participants of the same event. Count consultations by this column, not by rows. |
| 40 | `json_url` | Document API URL | The source-provided API URL for this Federal Register document number. |
| 41 | `location` | Location | Where the consultation was held. |
| 42 | `net_caught` | Acquisition nets | The agency or keyword acquisition nets recorded for this source document version. Being returned by a search net does not establish Native relevance or an entity relationship. |
| 43 | `notice_date` | Notice date | The date the Federal Register document was published. |
| 44 | `participant_name` | Participant as published | The tribe or organization named in the document, as it spells it. |
| 45 | `participant_role` | Entity role | Why the entity is on this row: read from participant_role. |
| 46 | `participant_rows_per_event` | Participant rows for this event | How many rows this event has in the file. |
| 47 | `pdf_url` | Document PDF | The source-provided PDF link for the document. The official GovInfo edition is the source identified for legal reliance. |
| 48 | `pre_2000_flag` | Publication before 2000 flag | The preserved source flag for publication before 2000: 1 or 0 where supplied, with blank allowed by the projector. Use publication_date for calendar-year selection. |
| 49 | `program` | Program | The program or matter the consultation concerns, where the document names one. |
| 50 | `publication_date` | Publication date | The calendar date the Federal Register document was published. It dates the document and its coverage window, not an event or consultation described in it. |
| 51 | `regulation_id_numbers` | Regulation IDs | Regulation identifier numbers supplied by the source document, serialized as a JSON array when reported. |
| 52 | `research_note` | Participant research note | Maintained qualifications for the participant observation: an invitation does not establish participation and collective scope has not been evaluated. The note can also retain event-date or location-basis qualifications. |
| 53 | `scope_qualification` | Document scope qualification | The broad-document component's stated limitation: acquisition across agency and keyword nets is broad recall and does not establish Native relevance or a verified Native-entity relationship. |
| 54 | `source_classification` | source classification | Cedar legacy classification from source text; not an FR-issued taxonomy |
| 55 | `source_quote` | Source passage | The sentence in the document this row was read from. |
| 56 | `subagency` | Office | The office within the department. |
| 57 | `title` | Document title | The title reported by the Federal Register API for the source document. A title or keyword does not by itself assert a Cedar entity relationship. |
| 58 | `title_abstract_term_hit` | Acquisition keyword flag | The preserved 1/0 acquisition flag for a keyword occurrence in the source title or abstract. It is a search-recall indicator, not verified Native relevance. |
| 59 | `title_abstract_terms` | Matched acquisition terms | The acquisition keywords recorded as matching the source title or abstract. Their presence does not verify Native relevance or identity. |
| 60 | `topic` | Topic | What the consultation was about, from the document's title. |
| 61 | `type` | Document type | The source document type: Notice, Rule, Proposed Rule or Presidential Document; separate from Cedar's source-text classification. |

### Federal Funding to Indian Country

Collection `funding` · table `funding` · installed producer spreadsheet

**Rows in this installed spreadsheet:** 640,942. This is an observation count at the declared record types and grains.

**One row is:** One permitted observation at its declared record_type and record_grain.

**Release or source location:** Exact release 6ba2dd2144d0a7cad1a0e8b57e801f170cbd47c4c5464d38c42b97999c0a837c; one researcher spreadsheet.

The columns below describe the exported names directly. No legacy rename, combine or promised identity block is applied to this spreadsheet.

**Fields (42):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `record_type` | record type | The permitted logical record type from the pinned release. |
| 2 | `record_key` | record key | The original source primary-key values serialized as JSON. |
| 3 | `record_grain` | record grain | What one observation of this record type represents; never sum across overlapping grains. |
| 4 | `action_date` | Action date | The date the agency took this action. |
| 5 | `assistance_type` | Assistance type | What kind of assistance it is: formula grant, project grant, direct payment, loan, insurance. |
| 6 | `assistance_type_code` | Assistance type code | The source's code for the assistance type (grant, loan, direct payment, insurance), defined in the dictionary; the readable type is beside it. |
| 7 | `attributed_flag` | Attributed to the entity | Whether Cedar attributes this transaction to the Native entity (yes) or keeps it in the file unattributed (no). Cedar's totals count attributed rows only. |
| 8 | `attribution_status` | Attribution status | How the attribution stands: attributed through the register, unattributed, or under review. |
| 9 | `award_id` | Award ID | USAspending's key for the whole award; the source link is built from it. |
| 10 | `awarding_agency` | Agency | The department that made the award. |
| 11 | `awarding_subagency` | Office | The office within the department. |
| 12 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 13 | `cedar_entity_role` | cedar entity role | Role of the linked Cedar entity in this assistance transaction: recipient when cedar_uid is present, otherwise blank. The role describes this row's recipient association, not the identity of every organization named in the award. |
| 14 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 15 | `entity_class` | entity class | Entity class from the pinned Cedar register for cedar_uid. Blank when no Cedar entity reference is published; it does not classify the unlinked recipient or establish ownership. |
| 16 | `fain` | Award number | The award's Federal Award Identification Number; several transactions can share one. |
| 17 | `fiscal_year` | Fiscal year | The federal fiscal year of the action (October to September), which is what USAspending reports and what the year filter uses. |
| 18 | `fy_partial_flag` | Partial fiscal year | Whether this row falls in a fiscal year the source had not finished reporting when Cedar pulled it (yes or no). Do not compare a partial year to a complete one. |
| 19 | `loan_face_value_usd` | Loan face value | For loans, the face value of this loan; zero for grants. |
| 20 | `loan_subsidy_cost_usd` | Original loan subsidy cost | For a loan, the government's estimated cost of the subsidy when it was made. A loan measure; never added to obligations. |
| 21 | `obligations_usd` | Amount obligated | Dollars obligated by this transaction. Negative values are de-obligations, kept as recorded. |
| 22 | `obligations_usd_real2025` | Amount in 2025 dollars | The same amount adjusted for inflation to 2025 dollars. |
| 23 | `performance_county` | Place of performance county | The county where the funded work is performed, as the award reports it. |
| 24 | `performance_county_fips` | Place of performance county FIPS | The county code where the funded work is performed, as the award reports it. |
| 25 | `performance_geography_status` | performance geography status | Availability of the source place-of-performance county assignment: placed when a county name or FIPS is present, placed_ambiguous when that assignment also has the source ambiguity flag, and unplaced when neither county field is present. This is a geography diagnostic, not verification of where services occurred. |
| 26 | `program_code` | Program number | The Assistance Listing (CFDA) number of the federal program. |
| 27 | `program_name` | Program | The federal program's name. |
| 28 | `recipient_city` | Recipient city | City of the recipient's address on the award. |
| 29 | `recipient_county` | Recipient county | The county of the recipient's address, which is not necessarily where the funded work happens. |
| 30 | `recipient_county_fips` | Recipient county FIPS | The county code of the recipient's address. |
| 31 | `recipient_geography_status` | recipient geography status | Availability of the recipient's source county assignment: placed when a county name or FIPS is present, placed_ambiguous when the source ambiguity flag is set, and unplaced when neither is present. It describes recipient geography, separately from place of performance. |
| 32 | `recipient_name` | Recipient as recorded | The recipient's name as the award records it, before Cedar resolved it to the entity. |
| 33 | `recipient_state` | Recipient state | State of the recipient's address on the award. |
| 34 | `recipient_type` | recipient type | Readable recipient categories decoded from the pinned assistance business-type code dictionary and reconciled with the source descriptions. Multiple categories are separated by semicolons; conflicting codes or descriptions are refused rather than silently preferred. |
| 35 | `recipient_uei` | Recipient UEI | The recipient's federal Unique Entity ID. |
| 36 | `research_note` | research note | Space for an additional factual qualification affecting interpretation of the transaction. The current funding projection writes this field blank; a blank is not an independent verification or a statement that the record has no limitations. |
| 37 | `source_system` | source system | Source-system label for the accepted assistance transaction lineage. The current projection writes usaspending after requiring a recognized USAspending bulk-download or award-archive source vintage. |
| 38 | `source_url` | source url | USAspending award-page URL constructed from the transaction's original assistance award unique key. It identifies the parent award page rather than a separate URL for each incremental transaction. |
| 39 | `source_vintage` | Source vintage | The date stamp of the archive the row was taken from. |
| 40 | `total_loan_face_value_usd` | Award loan face value | For loans, the face value of the whole award to date. |
| 41 | `total_loan_subsidy_cost_usd` | Total loan subsidy cost | The subsidy cost across the award's loan actions. Never added to obligations. |
| 42 | `transaction_id` | Transaction ID | USAspending's unique key for this transaction. Cite it to find the exact record. |

### Native Legislation and Votes

Collection `legislation` · table `legislation` · installed producer spreadsheet

**Rows in this installed spreadsheet:** 3,064. This is an observation count at the declared record types and grains.

**One row is:** One permitted observation at its declared record_type and record_grain.

**Release or source location:** Exact release 8b4569e17831f4a0dfc7a6df8f03e39191f79637f714fe76bd9ba0991e56f2f3; one researcher spreadsheet.

The columns below describe the exported names directly. No legacy rename, combine or promised identity block is applied to this spreadsheet.

**Fields (33):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `record_type` | record type | The permitted logical record type from the pinned release. |
| 2 | `record_key` | record key | The original source primary-key values serialized as JSON. |
| 3 | `record_grain` | record grain | What one observation of this record type represents; never sum across overlapping grains. |
| 4 | `affected_entities_as_published` | Affected entities as published | The entities the source itself names as affected, as it names them; empty where the source names none. |
| 5 | `affected_entity_classes` | Relevance class scope | When the bill names no entity, the class of entity it is about (federally recognized tribes, Alaska Native corporations). Class-wide relevance, not any entity's class. |
| 6 | `bill_id` | Bill ID | Congress, chamber and number, for example 103-hr-2366. |
| 7 | `bill_number` | Number | The bill's number in its chamber. |
| 8 | `bill_scope` | Scope | Whether the bill is specific to one tribe or general to Indian Country. |
| 9 | `bill_type` | Bill type | hr, s, hjres and the like, as Congress.gov codes them. |
| 10 | `canonical_names` | canonical names | JSON array of names from the pinned Cedar register, in the same order as cedar_uids. These are canonical entity names, not transcriptions of names appearing in the bill. |
| 11 | `cedar_uids` | cedar uids | JSON array of existing Cedar entity references carried by the bill's source entity list and validated against the pinned register. Positions align with the other entity arrays; collective topical scopes are represented separately and do not mint entity references. |
| 12 | `chamber` | Chamber | House or Senate. |
| 13 | `collective_scopes` | collective scopes | JSON value describing collective topical coverage. A general bill carries scope objects with relationship general_subject and unknown as-of date; a tribe-specific bill carries an empty array; an unevaluated bill scope is blank (producer transform legislation-projection-v3; the earlier v2 wrote the text null). These objects do not establish legal applicability or population membership at a particular date. |
| 14 | `companion_bill_id` | Companion bill | The matching bill in the other chamber, where one exists. |
| 15 | `congress` | Congress | Which Congress (the 103rd, and so on). |
| 16 | `cosponsor_count` | Cosponsors | How many members cosponsored it. |
| 17 | `entity_classes` | entity classes | JSON array of registered entity classes aligned position by position with cedar_uids. It describes the linked entities, not a classification of all people or organizations potentially affected by the bill. |
| 18 | `entity_link_statuses` | entity link statuses | JSON array of source linkage tiers aligned with cedar_uids. Missing tiers are null and excess tiers are omitted to preserve array alignment; the labels are source assessments rather than new identity adjudications. |
| 19 | `entity_names_as_published` | entity names as published | JSON array reserved for names as stated in the source, aligned with cedar_uids. The current projection writes null in each position because it does not extract those source-name strings; canonical_names must not be substituted as though quoted from the bill. |
| 20 | `entity_roles` | entity roles | JSON array aligned with cedar_uids; the current bill projection assigns named in the bill to each linked entity. This role does not assert that a bill applies to, benefits, or was sponsored by that entity. |
| 21 | `introduced_date` | Introduced | The date the bill was introduced; the year filter uses this. |
| 22 | `latest_action` | Latest action | The most recent action recorded on the bill. |
| 23 | `latest_action_date` | Latest action date | When that action happened. |
| 24 | `outcome` | Outcome | Where the bill ended: enacted, passed one chamber, died in committee. |
| 25 | `policy_area` | Policy area | Congress.gov's policy area for the bill. |
| 26 | `research_note` | research note | Additional factual qualification affecting interpretation of a bill record, when supplied by the declared public source fields. The current computed-field rule initializes it blank; blank does not certify source completeness or legal applicability. |
| 27 | `resolved_entity_count` | Resolved entities | How many of the named entities Cedar resolved to its register. |
| 28 | `rollcall_count` | Roll-call votes | How many recorded roll-call votes the bill had. |
| 29 | `source_system` | source system | Source-system label for the bill record. The current projection writes congress.gov. |
| 30 | `source_url` | source url | Official Congress.gov bill-page URL constructed from the validated Congress number, bill type, and bill number. The coordinates must agree with bill_id; this is the bill's landing page, not a link to a particular action. |
| 31 | `sponsor_bioguide_id` | Sponsor ID | The sponsor's Biographical Directory identifier. |
| 32 | `sponsor_name` | Sponsor | The sponsoring member, with party and state. |
| 33 | `title` | Title | The bill's title. |

### Native Federal Advocacy and Engagement

Collection `lobbying` · table `lobbying` · installed producer spreadsheet

**Rows in this installed spreadsheet:** 27,825. This is an observation count at the declared record types and grains.

**One row is:** One permitted observation at its declared record_type and record_grain.

**Release or source location:** Exact release c37e800572a0b108d27eca98248f51d0a1d9bb7335c1340abdf96540efc79cc5; one researcher spreadsheet.

The columns below describe the exported names directly. No legacy rename, combine or promised identity block is applied to this spreadsheet.

**Fields (41):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `record_type` | record type | The permitted logical record type from the pinned release. |
| 2 | `record_key` | record key | The original source primary-key values serialized as JSON. |
| 3 | `record_grain` | record grain | What one observation of this record type represents; never sum across overlapping grains. |
| 4 | `activity_date` | Posted | When the filing was posted. |
| 5 | `activity_id` | activity id | Source-based activity identifier formed as lda: followed by the filing UUID published as source_record_id. It identifies a filing record rather than a person, client, lobbying topic, or combined amendment history. |
| 6 | `activity_title` | Filing type | Registration, quarterly or year-end report, amendment, termination. |
| 7 | `activity_type` | activity type | Source-family label for the activity row. The current projection writes lda_filing; it does not imply that consultation, testimony, meeting, or other activity families are already included. |
| 8 | `affiliated_organizations` | Affiliated organizations | Organizations the filing lists as affiliated with the client. |
| 9 | `amount_basis` | Basis of spend | Income, expenses, or none reported. |
| 10 | `attribution_withdrawn` | Attribution withdrawn | Whether Cedar withdrew its link between this filing and the entity after review (yes or no). A withdrawn filing stays in the file; its spend is not counted as the entity's. |
| 11 | `attribution_withdrawn_reason` | Why withdrawn | The reason recorded for the withdrawal. |
| 12 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 13 | `cedar_entity_role` | cedar entity role | Role of the linked Cedar entity in the LDA filing: client when a Cedar reference is published. The value is blank when the association is absent or withdrawn and does not classify the registrant as the same entity. |
| 14 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 15 | `client_id` | Client ID | The client's identifier in the Lobbying Disclosure Act database. |
| 16 | `client_name` | Client | The client as the filing names it (the Native entity, in its own spelling). |
| 17 | `client_state` | Client state | The client's state. |
| 18 | `entity_class` | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 19 | `expenses_usd` | Expenses reported | What a self-filer reported spending this period. |
| 20 | `government_bodies` | Government entities contacted | Agencies and chambers the filing lists, separated by \|. |
| 21 | `income_usd` | Income reported | What the registrant reported receiving from the client this period. |
| 22 | `is_superseded` | Superseded (yes or no) | Whether a later filing replaces this one; the default view counts current filings only. |
| 23 | `issue_codes` | Issue codes | The LDA issue area codes on the filing. |
| 24 | `issues_text` | Specific issues | What the filing says was lobbied on. |
| 25 | `participant_name` | participant name | Participant-name field reserved for activity families that report individual or organizational participation. It is blank by default for the current LDA filing rows and is not filled from the client or registrant name. |
| 26 | `participant_role` | participant role | Participant-role field reserved for source-reported participation in applicable activity families. It is blank by default for current LDA filing rows; the filing's client association is recorded separately in cedar_entity_role. |
| 27 | `registrant_id` | Registrant ID | The registrant's identifier in the Lobbying Disclosure Act database. |
| 28 | `registrant_name` | Registrant | The lobbying firm or, for a self-filer, the client itself. |
| 29 | `registrant_state` | Registrant state | The registrant's state. |
| 30 | `reported_amount_usd` | Reported spend | Whichever of the two the filing reports; the basis column says which. |
| 31 | `reporting_period` | Period | Which reporting period of the year. |
| 32 | `reporting_year` | Filing year | The year the filing covers. |
| 33 | `research_note` | research note | Additional factual qualification affecting interpretation of the filing or activity, retained when supplied to the declared field. The current default is blank and does not signify a new verification of lobbying statements or amounts. |
| 34 | `self_filed` | Self-filed | Whether the client filed for itself rather than through a firm (yes or no). |
| 35 | `source_record_id` | Filing ID | The filing's identifier in the Senate LDA database. |
| 36 | `source_system` | source system | Source-system label for the current filing rows: lda, referring to the federal Lobbying Disclosure Act filing system. The exact filing is identified by source_record_id and its filing source link. |
| 37 | `source_url` | Source | The filing on lda.senate.gov. |
| 38 | `superseded_by_record_id` | Replaced by | The filing that replaces this one, where one does. |
| 39 | `supersession_group_id` | Supersession group | The group of filings (an original and its amendments) this filing belongs to. |
| 40 | `supersession_status` | Version status | Whether a later amendment replaces this filing. |
| 41 | `termination_date` | Termination date | When the registration was terminated, where the filing is a termination. |

### NAGPRA Notices

Collection `nagpra` · table `nagpra` · installed producer spreadsheet

**Rows in this installed spreadsheet:** 6,792. This is an observation count at the declared record types and grains.

**One row is:** One permitted observation at its declared record_type and record_grain.

**Release or source location:** Exact release b45822cd045724582cee3e2be0e87008fc61569d82cf2fa53fe2e2c309eb3c0d; one researcher spreadsheet.

The columns below describe the exported names directly. No legacy rename, combine or promised identity block is applied to this spreadsheet.

**Fields (55):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `record_type` | record type | The permitted logical record type from the pinned release. |
| 2 | `record_key` | record key | The original source primary-key values serialized as JSON. |
| 3 | `record_grain` | record grain | What one observation of this record type represents; never sum across overlapping grains. |
| 4 | `additional_institution_names` | additional institution names | JSON array of institution names listed beyond the designated institution_name. Names are split from the source institution list, trimmed, and excluded when equal to the designated name; the array does not itself resolve those institutions to legal identities. |
| 5 | `agency_names` | Publishing agency | The agency that published the notice. |
| 6 | `associated_funerary_objects_stated` | Associated funerary objects | Count stated in the notice. |
| 7 | `canonical_names` | canonical names | JSON array of pinned-register names aligned with the entity-role associations in cedar_uids. An entity appearing in more than one role can occur more than once; these names are not source quotations. |
| 8 | `cedar_uids` | cedar uids | JSON array of validated existing Cedar references, with one position per source entity-role association across the affiliated, consulted, disposition-priority, repatriation-recipient, letter-of-support, and aboriginal-land lists. Repeated entities in distinct roles retain distinct positions. |
| 9 | `cultural_items_total_stated` | Cultural items total, as stated | A total the notice itself states. Cedar never adds the categories together. |
| 10 | `cultural_patrimony_objects_stated` | Objects of cultural patrimony | Count stated in the notice. |
| 11 | `culturally_unidentifiable` | Culturally unidentifiable | Whether the remains are determined culturally unidentifiable (yes or no). |
| 12 | `document_number` | Document number | The Federal Register document number. |
| 13 | `entity_classes` | entity classes | JSON array of pinned-register classes aligned with cedar_uids and entity_roles. Each value classifies the associated entity, not an institution or a new ownership finding. |
| 14 | `entity_names_as_published` | entity names as published | JSON array of source-reported names aligned with the entity-role positions when such a source array is supplied. Otherwise each position is null; a missing source-name string is not replaced by the canonical register name. |
| 15 | `entity_roles` | entity roles | JSON array aligned with cedar_uids, recording the source role: affiliated, consulted, disposition priority, repatriation recipient, letter of support, or aboriginal land. The roles remain distinct and do not by themselves establish that a transfer has occurred. |
| 16 | `individuals_stated` | Individuals | The minimum number of individuals the notice states. |
| 17 | `individuals_statement` | Individuals count, as stated | The sentence stating the minimum number of individuals, kept where the number alone is ambiguous. |
| 18 | `institution_city` | Institution city | Where the institution is. |
| 19 | `institution_name` | Institution | The museum, university or agency holding the remains or objects. |
| 20 | `institution_split_flag` | Institution split (yes or no) | Whether the notice's institution field named several institutions that were split into the designated one and the additional ones. |
| 21 | `institution_state` | Institution state | Its state. |
| 22 | `institution_type` | Institution type | Museum, university, federal agency, and so on. |
| 23 | `is_correction` | Correction | Whether this notice corrects an earlier one (yes or no). |
| 24 | `lineal_descendant_determination` | Lineal descendant found | Whether a lineal descendant was determined (yes or no). |
| 25 | `n_aboriginal_land_named` | Aboriginal-land parties named | How many parties the notice names for aboriginal land. |
| 26 | `n_aboriginal_land_resolved` | Aboriginal-land parties resolved | How many of those Cedar could resolve. |
| 27 | `n_affiliated_named` | Affiliated parties named | How many parties the notice names as culturally affiliated. |
| 28 | `n_affiliated_resolved` | Affiliated parties resolved | How many of those Cedar could resolve to a register entity. |
| 29 | `n_consulted_named` | Consulted parties named | How many parties the notice names as consulted. |
| 30 | `n_consulted_resolved` | Consulted parties resolved | How many of those Cedar could resolve to a register entity. The gap is real uncertainty, not an omission. |
| 31 | `n_disposition_priority_named` | Priority parties named | How many parties the notice names with disposition priority. |
| 32 | `n_disposition_priority_resolved` | Priority parties resolved | How many of those Cedar could resolve. |
| 33 | `n_entities_resolved` | Entities resolved in all | How many distinct register entities those resolve to. |
| 34 | `n_letter_of_support_named` | Letters of support named | How many parties the notice names as having submitted a letter of support. |
| 35 | `n_letter_of_support_resolved` | Letters of support resolved | How many of those Cedar could resolve to a register entity. |
| 36 | `n_parties_named` | Parties named in all | All parties the notice names, across roles. |
| 37 | `n_repatriation_recipient_named` | Recipients named | How many recipients the notice names. |
| 38 | `n_repatriation_recipient_resolved` | Recipients resolved | How many of those Cedar could resolve. |
| 39 | `notice_type` | Notice type | Inventory completion, intent to repatriate, or correction. |
| 40 | `object_categories` | Object categories | Which categories of items the notice covers (human remains, associated funerary objects, sacred objects, objects of cultural patrimony). |
| 41 | `pdf_url` | PDF | The notice as published, in PDF. |
| 42 | `process_stage` | Statute stage | Which stage of NAGPRA the notice is made under. |
| 43 | `publication_date` | Published | The date the notice was published. |
| 44 | `publication_year` | Publication year | The year the notice was published. |
| 45 | `removal_counties` | Removal counties | Where the remains or objects were removed from. |
| 46 | `removal_location` | Removal location | Where the holdings were removed from, as the notice states it, with the existing restrictions on sensitive location applied before export. |
| 47 | `removal_states` | Removal states | The states of those places. |
| 48 | `repatriation_eligible_date` | Repatriation eligible from | The date after which repatriation may proceed, as the notice states. Not evidence that a transfer happened. |
| 49 | `research_note` | research note | Additional factual qualification affecting interpretation of the notice, retained when supplied to the declared field. The current default is blank; unresolved named entities and source limitations must still be read from the other notice fields. |
| 50 | `response_deadline_date` | Response deadline | The date by which other claimants must respond. |
| 51 | `responsible_party_statement` | Responsible party | The official the notice names as responsible for the holdings, as stated. |
| 52 | `sacred_objects_stated` | Sacred objects | Count stated in the notice. |
| 53 | `source_url` | Source | The notice on federalregister.gov. |
| 54 | `title` | Title | The notice's title. |
| 55 | `unassociated_funerary_objects_stated` | Unassociated funerary objects | Count stated in the notice. |

### Tribal Natural Resource Revenue

Collection `natural-resources` · table `natural-resources` · installed producer spreadsheet

**Rows in this installed spreadsheet:** 11,120. This is an observation count at the declared record types and grains.

**One row is:** One permitted observation at its declared record_type and record_grain.

**Release or source location:** Exact release f65f92d809d91fa07c977f37ff2a4c3830ca014eccb728daaaf43ebfaa61e7e5; one researcher spreadsheet.

The columns below describe the exported names directly. No legacy rename, combine or promised identity block is applied to this spreadsheet.

**Fields (41):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `record_type` | record type | The permitted logical record type from the pinned release. |
| 2 | `record_key` | record key | The original source primary-key values serialized as JSON. |
| 3 | `record_grain` | record grain | What one observation of this record type represents; never sum across overlapping grains. |
| 4 | `aggregation_level` | Aggregation level | Whether the amount is specific to the entity, a regional aggregate or a countrywide aggregate. An aggregate is never assigned to one tribe. |
| 5 | `allocation_formula` | Allocation formula | The rule that determined the amount, where the source states it. |
| 6 | `allocation_formula_effective_end` | Allocation rule effective to | When the allocation rule ceased to apply. |
| 7 | `allocation_formula_effective_start` | Allocation rule effective from | When the allocation rule took effect. |
| 8 | `allocation_formula_source_url` | Formula source | Where that rule is published. |
| 9 | `amount_sign_meaning` | What the sign means | How to read a negative amount (a correction, a recoupment). |
| 10 | `amount_usd` | Amount | The source-reported amount in US dollars. Read measurement_status and amount_sign_meaning with it: a revenue amount, appropriation, allocation, estimate or payment does not imply another of those measures. |
| 11 | `amount_usd_real2025` | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. |
| 12 | `attribution_status` | Attribution status | Whether the row is keyed to a Native entity, to an aggregate, or unresolved. A blank Cedar ID has a stated reason here. |
| 13 | `beneficiary_entity_id` | Beneficiary ID | The identifier of the beneficiary where it differs from the recipient. |
| 14 | `beneficiary_name` | Source beneficiary | The source-reported beneficiary, where one is given separately from the recipient. This field does not resolve or promote a canonical entity identity. |
| 15 | `canonical_name` | canonical name | Name from the pinned Cedar register for the existing, published recipient cedar_uid. Blank means no recipient identity is published; a source recipient label is not automatically promoted into a new Cedar identity. |
| 16 | `cedar_entity_role` | cedar entity role | Role of the registered Cedar entity in the resource record: recipient when a Cedar reference survives the source and publication checks, otherwise blank. This role does not establish that the reported measure was an actual payment. |
| 17 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 18 | `commodity` | Commodity | The commodity, as the source names it. |
| 19 | `entity_class` | entity class | Entity class from the pinned Cedar register for the published recipient cedar_uid. It describes the recipient entity and does not classify a payer, resource project, or revenue mechanism. |
| 20 | `geography_note` | Place | What the source says about where the revenue arose. |
| 21 | `land_status` | Land status | Trust or fee land, where the source states it. |
| 22 | `measurement_status` | Measurement basis | The source or reviewed classification of the reported measure, including reported revenue, an appropriated amount, an allocation, estimate or actual payment. An appropriation or allocation is not evidence of a completed payment. |
| 23 | `mineral_lease_type` | Mineral lease type | The lease type, where the source states it. |
| 24 | `operator_entity_id` | Operator ID | The identifier of the related operator, where a source supports one. |
| 25 | `operator_name` | Operator | The related operator's name, where a source supports one. |
| 26 | `payer_entity_id` | Payer ID | The identifier of the payer. |
| 27 | `payer_name` | Source payer | The payer name retained from the source, where one is given. Its presence does not establish that an appropriated or allocated amount has been paid. |
| 28 | `payment_date` | Payment date | When the payment was made. |
| 29 | `period_end` | Period end | End of that period. |
| 30 | `period_start` | Period start | The beginning of the period covered by the reported observation, where stated. This is not necessarily a transaction or payment date. |
| 31 | `period_type` | Period covered | The time basis used by the source observation, such as calendar year, fiscal year or month. Read alongside period_start, period_end and any separately reported payment_date. |
| 32 | `product` | Product | The product, where the source states one below the commodity. |
| 33 | `recipient_name` | Source recipient | The recipient name retained from the source, where one is provided. It is not automatically a canonical Cedar entity and a blank does not identify a tribal recipient. |
| 34 | `related_asset_ids` | Related assets | Source-linked identifiers for related wells, tracts, leases or other assets when provided. Empty values do not establish a missing payment or a new asset identity. |
| 35 | `research_note` | research note | Preserved or specifically reviewed qualification of the beneficiary, measurement basis, period, or source evidence. It includes distinctions between OSMRE allocations or appropriations and payments, and cautions about Osage headright rates and overlapping measures where applicable. |
| 36 | `resource_revenue_event_id` | Observation ID | The existing identifier for this source revenue observation. It can identify an appropriation, allocation or reported revenue row; it does not itself establish a payment. |
| 37 | `resource_type` | Resource | Oil and gas, coal, timber, minerals. |
| 38 | `revenue_type` | Revenue type | Royalty, severance tax share, reclamation fee distribution, and so on. |
| 39 | `source_record_id` | Source record ID | The record's identifier in that source. |
| 40 | `source_system` | Source system | Which source system the record came from. |
| 41 | `source_url` | Source | The cited source for this observation and its reported measure. A source link does not change the row into a payment or establish a different recipient. |

### Cedar Native Entity Enterprise Dataset (NEED)

Collection `need` · table `need` · installed producer spreadsheet

**Rows in this installed spreadsheet:** 43. This is an observation count at the declared record types and grains.

**One row is:** One permitted observation at its declared record_type and record_grain.

**Release or source location:** Exact release 428d11048f12cd819f7cf95dccdbbe4c1ea20a8c81c635a7e985fbc17b1b983b; one researcher spreadsheet.

The columns below describe the exported names directly. No legacy rename, combine or promised identity block is applied to this spreadsheet.

**Fields (23):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `record_type` | record type | The permitted logical record type from the pinned release. |
| 2 | `record_key` | record key | The original source primary-key values serialized as JSON. |
| 3 | `record_grain` | record grain | What one observation of this record type represents; never sum across overlapping grains. |
| 4 | `cage_code` | cage code | CAGE independently supported by evidence; blank is unreviewed. |
| 5 | `cage_evidence_scope` | cage evidence scope | Whether evidence corroborates an existing CAGE or supplies a previously blank value through the exact UEI. The preserved authority is never overwritten. |
| 6 | `decision_sha256` | decision sha256 | SHA-256 of this exact reviewed decision including its evidence pins. |
| 7 | `enterprise_id` | enterprise id | Existing permanent enterprise ID, preserved without issuance or merging. |
| 8 | `enterprise_name` | enterprise name | Exact name in the pinned enterprise authority; not a new canonical-name ruling. |
| 9 | `evidence_pins` | evidence pins | JSON citations with exact stored evidence SHA-256 and supported fact types. |
| 10 | `owner_name` | owner name | Explicitly reviewed owner only; subsidiary and affiliation counterparts are separate. |
| 11 | `owner_scope` | owner scope | Whether owner_name is the immediate legal parent or ultimate owner. |
| 12 | `ownership_extent` | ownership extent | Source-supported majority or wholly-owned extent; blank means unspecified, never zero. |
| 13 | `publication_status` | publication status | Publication applies only to this whitelisted reviewed base record. |
| 14 | `related_entity_name` | related entity name | Counterpart explicitly named by the source for the reviewed relationship. Affiliation and subsidiary statements do not assert an ownership percentage. |
| 15 | `relationship_type` | relationship type | Reviewed owned_by, subsidiary_of or affiliated_with claim; blank is unreviewed. |
| 16 | `review_reason` | review reason | Reviewer-written factual basis; no licensed report prose. |
| 17 | `reviewed_on` | reviewed on | Evidence review date, not the relationship's effective date or a current-status guarantee. |
| 18 | `source_release_id` | source release id | Immutable NEED source release reviewed for this decision. |
| 19 | `source_reported_name` | source reported name | Name shown by the reviewed primary evidence. |
| 20 | `source_row_sha256` | source row sha256 | SHA-256 of the exact preserved enterprise source row. |
| 21 | `subject_binding` | subject binding | Exact identifier or preserved reviewed profile-link evidence connecting the source subject to this existing enterprise ID; never a shared-name join. |
| 22 | `uei` | uei | Exact existing UEI independently corroborated by primary evidence; blank is unreviewed. |
| 23 | `verified_claims` | verified claims | JSON list of independently evidenced claims in this row. Missing claims are unreviewed, not negative findings; identifiers and relationships are distinct. |

### Native Nonprofits

Collection `nonprofits` · table `nonprofits` · installed producer spreadsheet

**Rows in this installed spreadsheet:** 89. This is an observation count at the declared record types and grains.

**One row is:** One permitted observation at its declared record_type and record_grain.

**Release or source location:** Exact release bb679c5bb80b210fc42ab22a5241941220c1fc823e85dcda5d6a11e0045a24a6; one researcher spreadsheet.

The columns below describe the exported names directly. No legacy rename, combine or promised identity block is applied to this spreadsheet.

**Fields (27):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `record_type` | record type | The permitted logical record type from the pinned release. |
| 2 | `record_key` | record key | The original source primary-key values serialized as JSON. |
| 3 | `record_grain` | record grain | What one observation of this record type represents; never sum across overlapping grains. |
| 4 | `bmf_as_of_date` | IRS file date | The date of the IRS file these figures come from. |
| 5 | `bmf_assets_usd` | Assets | Assets in that return. |
| 6 | `bmf_income_usd` | Income | Income in that return. |
| 7 | `bmf_revenue_usd` | Revenue | Revenue in the latest return the IRS holds. |
| 8 | `canonical_name` | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) stay in their own columns. |
| 9 | `cedar_entity_role` | cedar entity role | Published role of the existing Cedar association: affiliated_with when cedar_uid is present, otherwise blank. The association does not make the IRS organization and the Native entity the same legal object or certify ownership. |
| 10 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 11 | `city` | City | Its city. |
| 12 | `ein` | EIN | The organization's Employer Identification Number. |
| 13 | `entity_class` | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 14 | `entity_link_status` | entity link status | Status of the published Cedar association: source-supported existing relationship when cedar_uid is present, or unlinked organization when it is absent. An unlinked organization can still qualify for the collection on separately supported Native-serving evidence. |
| 15 | `inclusion_category` | inclusion category | Evidence-backed reason for including the IRS organization, such as Native-serving, source-identified Native organization, source-described control or tribal charter, intertribal organization, or tribal government. This category is supported by the reviewed source evidence and is separate from tax status, ownership certification, and Cedar identity linkage. |
| 16 | `irs_foundation_code` | Foundation code | The IRS foundation classification code, defined in the dictionary. |
| 17 | `irs_ruling_month` | IRS ruling date | When the IRS recognized the organization (year and month). |
| 18 | `irs_status` | IRS status code | The organization's status code in the Business Master File, defined in the dictionary. |
| 19 | `irs_subsection` | Tax subsection | The 501(c) subsection (3 for charities). |
| 20 | `ntee_code` | NTEE code | The IRS activity code for what the organization does. |
| 21 | `organization_entity_class` | Organization type | Whether the organization is itself a tribe, an ANC, a Native organization. |
| 22 | `organization_name` | Organization | The organization's name as the IRS records it. |
| 23 | `research_note` | research note | Source-evidence qualification retaining the relationship, observation date, source URL, stated source date, and limitations. It distinguishes tax facts from Native affiliation and identifies filed-service evidence when used; it does not imply an ownership certification or an unrecorded human identity ruling. |
| 24 | `source_system` | Source system | The source: the IRS Exempt Organizations Business Master File. |
| 25 | `source_url` | Source | The IRS Business Master File. |
| 26 | `state` | State | The organization's state. |
| 27 | `tax_period` | Latest tax period | The most recent tax period in the file. |

### Native-Owned Businesses

Collection `owned` · table `owned` · installed producer spreadsheet

**Rows in this installed spreadsheet:** 3,725. This is an observation count at the declared record types and grains.

**One row is:** One permitted observation at its declared record_type and record_grain.

**Release or source location:** Exact release f298b01f29651ab652e2d8f221d061504b8de035c18ae9e10cf84a3daf777ed9; one researcher spreadsheet.

The columns below describe the exported names directly. No legacy rename, combine or promised identity block is applied to this spreadsheet.

**Fields (35):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `record_type` | record type | The permitted logical record type from the pinned release. |
| 2 | `record_key` | record key | The original source primary-key values serialized as JSON. |
| 3 | `record_grain` | record grain | What one observation of this record type represents; never sum across overlapping grains. |
| 4 | `assertion_class` | assertion class | The class of claim made by the listing authority: OWNERSHIP asserts who owns the firm; RELATIONSHIP asserts that the firm does business with the authority. This source assertion is not an independent Cedar ownership determination, and the two classes must not be counted as the same fact. |
| 5 | `business_entity_id` | business entity id | An existing Cedar register identifier supplied for the listed business, translated through the pinned legacy crosswalk when necessary. A blank records no established register link. This field is separate from the certifying authority's cedar_uid; the projection does not mint a business identifier or substitute the authority's identity. |
| 6 | `business_license_number` | business license number | The tribal business licence number reported in the source listing, where supplied. It identifies a licence in that authority's system, not a Cedar entity, a certification tier, or a federal business identifier. |
| 7 | `business_name` | business name | The business name as printed in the source listing, projected from business_name_raw. Publication masks may leave it blank, including where the name identifies a natural person; a blank must not be restored from aliases or authority names. |
| 8 | `business_source_id` | business source id | Identifier of one source listing, formed from the source namespace and that source's record key. The record key may be a certification number, source slug, or document position; cross-vintage stability depends on the source key. It is not a universal business identifier, and distinct certifications remain separate records. |
| 9 | `canonical_name` | canonical name | The current pinned register name of the certifying authority identified by cedar_uid. It is looked up from the resolved register, not copied from the business listing, and does not name the listed business. |
| 10 | `cedar_entity_role` | cedar entity role | The role of the entity in the opening Cedar identity fields: certifying_authority. It describes the authority making the listing or certification claim, not an owner of the listed business. The producer clears this role when the opening Cedar identifier is blank. |
| 11 | `cedar_uid` | cedar uid | The certifying authority's canonical Cedar entity identifier, derived from certifying_authority_entity_id after pinned crosswalk and register checks. It identifies the authority rather than the listed business; no business identity or ownership relationship is created by this derivation. |
| 12 | `certification_expiration` | certification expiration | The source-reported end or renewal date associated with the listing. Depending on the program it can be a certification expiry, annual-update deadline, or business-licence expiry; Lummi's value is a licence expiry. Recognized dates retain their stated precision; unparseable source text is preserved rather than guessed. |
| 13 | `certification_number` | certification number | The certification or vendor record number supplied by the authority. It can link the same source's records across vintages when that source preserves the number; it is not globally unique across authorities or a substitute for a Cedar business identifier. |
| 14 | `certification_start` | certification start | Start-date value carried in the reviewed listing input. Most source parsers use a printed certification date, but the Oneida parser supplies its field named est; the current producer does not independently establish that field's event meaning. Upstream normalization preserves stated precision and unparseable text. Do not assume a uniform certification, business-formation, or ownership-start event across sources. |
| 15 | `certification_tier` | certification tier | The source's preference level, certification tier, or certification-status wording, such as a preference level, probationary status, or full certification. These source-specific categories are retained rather than collapsed into a common ownership threshold. |
| 16 | `certifying_authority_entity_id` | certifying authority entity id | The registered Cedar entity reference for the government, corporation, or other listing authority making the assertion. The producer resolves the supplied authority reference against its pinned crosswalk and register and uses it for the opening cedar_uid. It never identifies the listed business merely because that business appears in the authority's directory. |
| 17 | `certifying_authority_name` | certifying authority name | The authority name carried in the source configuration or reviewed input for this listing. It names the organization making the assertion, not the listed business, and is retained independently of the register-derived canonical_name. |
| 18 | `city` | city | City recorded in the source's business address. The listing's reported location does not establish tribal jurisdiction, an owner's residence, or operating presence; publication masks continue to apply. |
| 19 | `directory_type` | directory type | The source register's type, such as TERO, Indian preference, business licensing, vendor listing, subsidiary directory, or shareholder vendor list. The register type provides source context and does not by itself establish the listed firm's ownership. |
| 20 | `entity_class` | entity class | The pinned register classification of the certifying authority identified by cedar_uid. It is not the listed business's legal form, industry, ownership class, or certification status. |
| 21 | `first_seen` | first seen | Stored date or timestamp of the first recorded harvest in which this listing appeared in its source. Initial records were seeded with the harvest date; this field does not establish earlier history, business formation, certification onset, or an ownership effective date. |
| 22 | `identity_claim_text` | identity claim text | Source-derived claim wording explaining why the business is included in the directory or program. It may combine program-wide wording with a row-specific source statement, as the Oneida parser does for owner memberships. Read it with assertion_class and identity_scope; it is not an independent Cedar adjudication. Publication masking may withhold the text. |
| 23 | `identity_scope` | identity scope | The population or relationship covered by the source's claim, at the source's stated level: for example enrolled-member ownership, broader Native ownership, a parent-asserted subsidiary, shareholder/descendant/spouse eligibility, or a vendor relationship. These scopes are not interchangeable evidence of Native ownership. |
| 24 | `is_current` | is current | The input record's flag for presence in the latest retained retrieval of its source. It is a snapshot-presence flag, not assurance that the business is operating today, that a licence or certification remains valid, or that ownership has not changed. |
| 25 | `last_seen` | last seen | Stored date or timestamp of the most recent recorded harvest in which this listing appeared in its source. With first_seen and is_current it can describe observed listing persistence across retained vintages; it is not an ownership end date, certification expiry, or proof of coverage beyond those harvests. |
| 26 | `naics_code` | naics code | NAICS industry code or codes explicitly supplied by the source, projected from naics. The projection does not infer a code from a business name or service description, and a missing value remains missing. |
| 27 | `ownership_percent` | ownership percent | The ownership percentage explicitly stated for the particular business by the source. It is not inferred from program membership or substituted with a program's minimum eligibility threshold. A blank means no record-level percentage was supplied, not zero ownership. |
| 28 | `ownership_threshold_min` | ownership threshold min | The minimum ownership percentage required by the stated program, where supported by the program's published list, ordinance, or statute. It is an eligibility rule, not the observed ownership percentage of this business; a blank does not imply either zero or a standard 51-percent threshold. |
| 29 | `program_name` | program name | The name of the authority's program or directory, projected from programme_name, such as its TERO, Indian Preference Office, or CESO program. The source's own program identity is retained rather than labeling every register as TERO. |
| 30 | `research_note` | research note | A concise factual qualification that changes interpretation. The current OWNED field map declares a blank-rule field; the producer's handler retains a supplied reviewed note when present and otherwise leaves it empty. It is not an automatically generated ownership or publication verdict. |
| 31 | `service_category` | service category | The source's trade, service category, or business-line wording, projected from service_category_raw. It preserves the source category rather than asserting a harmonized industry classification or inferring a NAICS code. |
| 32 | `source_edition` | source edition | The source publisher's edition marker, such as a dated filename, build stamp, or printed current-as-of label. It identifies the captured publication version; it is not the Cedar release version and does not establish continuous coverage between editions. |
| 33 | `source_last_updated` | source last updated | The update date explicitly stated by the source publisher. A blank means the source supplied no update date; Cedar's harvest date or the researcher spreadsheet's export date must not be substituted. |
| 34 | `source_url` | Source | The official page for this record, written into the file so it cites itself. |
| 35 | `state` | state | State or province reported in the source's business address, projected from state_province. It is source location text, not a derived Native-entity affiliation, ownership jurisdiction, or inferred state code. |

### Native Federal Subcontracting

Collection `subcontracting` · table `subcontracting` · installed producer spreadsheet

**Rows in this installed spreadsheet:** 70,054. This is an observation count at the declared record types and grains.

**One row is:** One permitted observation at its declared record_type and record_grain.

**Release or source location:** Exact release 126230dd07419a9d1f57c1342fb5e11aae31ffea2fe846d3ea95c9b9934bfc06; one researcher spreadsheet.

The columns below describe the exported names directly. No legacy rename, combine or promised identity block is applied to this spreadsheet.

**Fields (57):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `record_type` | record type | The permitted logical record type from the pinned release. |
| 2 | `record_key` | record key | The original source primary-key values serialized as JSON. |
| 3 | `record_grain` | record grain | What one observation of this record type represents; never sum across overlapping grains. |
| 4 | `action_date_precedes_ffata_flag` | Date before FFATA | Whether the reported action date precedes FFATA reporting. This is a chronology-review flag; it does not prove a typo or supply a corrected date. |
| 5 | `award_kind` | Award type | Whether the prime award is a contract or an assistance award. The two populations are never combined in a total. |
| 6 | `awarding_agency` | Agency | The department that awarded the prime contract. |
| 7 | `awarding_subagency` | Office | The office within it. |
| 8 | `canonical_name` | canonical name | Name from the pinned Cedar register for the published cedar_uid, blank when no reference is published. It names the associated Native entity rather than replacing either the prime contractor's or subcontractor's reported legal name. |
| 9 | `cedar_entity_role` | cedar entity role | Source-attributed affiliation located on the prime-contractor side, subcontractor side, both sides, or an unresolved party side, determined from the preserved party references. Blank means no published primary Cedar reference; the role does not establish ownership at the subaward action date. |
| 10 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the canonical Native entity this record is associated with. The join key across every collection; never the record's own ID. |
| 11 | `description` | Description | What the subcontract is for, as reported. |
| 12 | `duplicate_status` | Duplicate status | Whether this row is the primary filing or a duplicate of one. Sum primaries only. |
| 13 | `entity_class` | entity class | Class from the pinned Cedar register for the published cedar_uid. It classifies the associated Native entity, not the prime contractor or subcontractor merely because that business appears in the same row. |
| 14 | `fiscal_year` | Fiscal year | The federal fiscal year of the subaward. |
| 15 | `naics_code` | NAICS | The industry code. |
| 16 | `naics_description` | Industry | What that code means. |
| 17 | `native_direction` | Source Native association | The retained source classification of which side has a Native-entity association. It is not independently verified ownership at the subaward action date. |
| 18 | `prime_award_amount_usd` | Prime award amount | The prime contract's value. |
| 19 | `prime_award_id` | Prime award number | The prime contract's number. |
| 20 | `prime_award_unique_key` | Prime award key | USAspending's key for the prime award. |
| 21 | `prime_cage` | Prime CAGE | Its CAGE code, where reported. |
| 22 | `prime_cedar_uid` | Prime's Cedar ID | The source-attributed Native entity associated with the prime. This does not establish ownership or its effective dates. |
| 23 | `prime_name` | Prime contractor | The prime as reported. |
| 24 | `prime_parent_cage` | Prime parent CAGE | The CAGE code of the prime's declared parent. |
| 25 | `prime_parent_name` | Prime's parent | Its parent as reported. |
| 26 | `prime_parent_uei` | Prime parent UEI | The UEI of the prime's declared parent. |
| 27 | `prime_set_aside` | Prime set-aside | The set-aside category of the prime award, where reported. |
| 28 | `prime_uei` | Prime UEI | Its Unique Entity ID. |
| 29 | `psc_code` | Product or service code | The federal product or service code of the subaward, where reported. |
| 30 | `psc_description` | Product or service | What the product or service code means. |
| 31 | `report_id` | Report ID | The SAM subaward report's identifier: the version of the report this row comes from. |
| 32 | `report_year` | Report year | The year of the report the subaward was filed in: the reporting period. |
| 33 | `research_note` | research note | Source qualification plus an explicit warning that Native-entity links and direction are source-attributed associations, ownership at the action date is not established, and current affiliation must not be backdated to the reported subaward. |
| 34 | `source_system` | Source system | Which source the report came from (the USAspending FSRS pull). |
| 35 | `source_url` | Source | The prime award's page on USAspending. |
| 36 | `sub_cedar_uid` | Subcontractor's Cedar ID | The source-attributed Native entity associated with the subcontractor. This does not establish ownership or its effective dates. |
| 37 | `subaward_amount_usd` | Subaward amount | Dollars of the subaward. |
| 38 | `subaward_amount_usd_real2025` | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. |
| 39 | `subaward_date` | Subaward date | The date of the subaward. |
| 40 | `subaward_exceeds_prime_flag` | Exceeds the prime award | Whether the subaward amount exceeds its prime award (yes or no). A real filing, kept in the file, but never added into totals. |
| 41 | `subaward_number` | Subaward number | The subaward's own number as the prime reported it. |
| 42 | `subaward_record_id` | Subaward ID | The subaward report's identifier. |
| 43 | `subaward_to_prime_ratio` | Subaward to prime ratio | The subaward amount divided by the prime award amount, with the amount, period and version definitions the guide states; never recomputed from incompatible snapshots. |
| 44 | `subaward_type` | Subaward type | Sub-contract or sub-grant, as reported. |
| 45 | `subcontractor_business_types` | Subcontractor business types | The business types it reports (for example, Alaska Native Corporation owned). |
| 46 | `subcontractor_cage` | Subcontractor CAGE | Its CAGE code, where reported. |
| 47 | `subcontractor_city` | Subrecipient city | The subrecipient's own city, never filled from the prime's address. |
| 48 | `subcontractor_country` | Subrecipient country | The subrecipient's country code. |
| 49 | `subcontractor_county` | Subrecipient county | The county of the subrecipient's address. |
| 50 | `subcontractor_county_fips` | Subrecipient county FIPS | The county code of the subrecipient's address. |
| 51 | `subcontractor_geography_status` | subcontractor geography status | Availability of the subcontractor's own source county assignment: placed when a county name or FIPS is present, placed_ambiguous when the source ambiguity flag is set, and unplaced when neither is present. It is not the prime contractor's address or the award's place of performance. |
| 52 | `subcontractor_name` | Subcontractor | The subcontractor as reported. |
| 53 | `subcontractor_parent_cage` | Subrecipient parent CAGE | The CAGE code of the subrecipient's declared parent. |
| 54 | `subcontractor_parent_name` | Subcontractor's parent | Its parent as reported. |
| 55 | `subcontractor_parent_uei` | Subrecipient parent UEI | The UEI of the subrecipient's declared parent. |
| 56 | `subcontractor_state` | Subcontractor state | Its state. |
| 57 | `subcontractor_uei` | Subcontractor UEI | Its Unique Entity ID. |

### Foundation & Corporate Giving

Collection `foundation-corporate-giving` · table `foundation-corporate-giving` · installed producer spreadsheet

**Rows in this installed spreadsheet:** 193. This is an observation count at the declared record types and grains.

**One row is:** One permitted observation at its declared record_type and record_grain.

**Release or source location:** Exact release 4de9e836933499c5cb083599f2623fa99c99a6d14cfa65b7256a569750a902ec; one researcher spreadsheet.

The columns below describe the exported names directly. No legacy rename, combine or promised identity block is applied to this spreadsheet.

**Fields (66):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `record_type` | record type | The permitted logical record type from the pinned release. |
| 2 | `record_key` | record key | The original source primary-key values serialized as JSON. |
| 3 | `record_grain` | record grain | What one observation of this record type represents; never sum across overlapping grains. |
| 4 | `addability_status` | addability status | nonadditive_disclosure_view forbids treating rows as independent additive award totals. |
| 5 | `aggregation_status` | aggregation status | nonadditive_disclosure_observation requires award/version and period reconciliation before totals. |
| 6 | `amount_aggregate_usd` | amount aggregate usd | Umbrella or multi-recipient nominal USD total, not allocated to this recipient. Never add it to recipient amounts. |
| 7 | `amount_basis` | amount basis | Source measure: commitment, commitment_increment, payment, future_payable or reported_grant. These are not interchangeable. |
| 8 | `amount_class` | amount class | Exact, range or unstated representation; a range is not a point estimate and unstated is not zero. |
| 9 | `amount_exact_usd` | amount exact usd | Exact reported nominal USD for this disclosure and financial status, stored as decimal text; blank is unknown, never zero. |
| 10 | `amount_lower_usd` | amount lower usd | Lower bound of a reported nominal USD range; not an additional amount or point estimate. Blank means unstated. |
| 11 | `amount_upper_usd` | amount upper usd | Upper bound of a reported nominal USD range; not an additional amount or point estimate. Blank means unstated. |
| 12 | `announcement_date` | announcement date | Explicit public announcement date, distinct from approval and payment; blank means unestablished. |
| 13 | `approval_date` | approval date | Reported approval date, distinct from announcement and payment; blank means unestablished. |
| 14 | `award_family_source` | award family source | Explicit reviewed or preserved source family key, used with funder and recipient; blank leaves family unresolved. |
| 15 | `award_id` | award id | Reviewed award-family key grouping versions; blank means no confirmed family. Amounts remain nonadditive. |
| 16 | `award_period_text` | award period text | Source-supported duration or coverage text, not a payment schedule or proof of disbursement. |
| 17 | `beneficiary_name` | beneficiary name | Separately reported ultimate beneficiary, not necessarily the legal recipient or payee. |
| 18 | `cedar_uid` | cedar uid | Existing registered Native entity ID for the reviewed recipient only; blank means no approved binding. Do not infer an ID from its name or parent. |
| 19 | `currency` | currency | Reported currency; verified USD here is nominal and not inflation adjusted. |
| 20 | `disclosure_id` | disclosure id | Stable key for one source disclosure, not a recipient or distinct award count. |
| 21 | `event_type` | event type | Reported disclosure category; does not alone establish a new award or payment. |
| 22 | `financial_status` | financial status | Committed, pledged or authorized is not paid. Paid reports disbursement; unpaid_balance is outstanding stock; committed_increment is an increment, not a restated total; unknown establishes none. |
| 23 | `fiscal_sponsor_name` | fiscal sponsor name | Separately reported fiscal sponsor or intermediary; distinct from recipient and ultimate beneficiary. |
| 24 | `funder_class` | funder class | Reported funder category, separate from canonical identity. |
| 25 | `funder_ein` | funder ein | Reported funder tax identifier as text; blank means unavailable or unverified. |
| 26 | `funder_name` | funder name | Funder name reported by the source; no Native identity or ownership is implied. |
| 27 | `hold_reason` | hold reason | Explicit withholding reason; blank is not unrestricted source or production permission. |
| 28 | `observation` | observation | Generated sentence naming funder, reported recipient and source year; not copied prose or proof of payment. |
| 29 | `overlap_status` | overlap status | Review state of repeated or aggregate disclosures; reviewed_distinct does not make rows summable. |
| 30 | `partition` | partition | Original primary, other_recipient or held delivery partition; provenance, not current eligibility by itself. |
| 31 | `payment_date` | payment date | Reported disbursement date; blank does not establish paid or unpaid status. |
| 32 | `project_geography` | project geography | Explicitly supported project or service geography. Recipient address is never a fallback; blank means unestablished. |
| 33 | `publication_rights_status` | publication rights status | Approved projection use; derived_facts_only excludes copied prose and raw-source exports. |
| 34 | `publication_status` | publication status | observed permits the governed review view; held remains internal. Neither authorizes production by itself. |
| 35 | `purpose` | purpose | Copied source-purpose prose is intentionally withheld; blank does not establish a missing project purpose. |
| 36 | `recipient_affiliation` | recipient affiliation | Reviewed recipient-scope label; not a legal ownership relationship or canonical identity binding. |
| 37 | `recipient_city` | recipient city | Source-reported recipient locality, not necessarily headquarters or project geography. |
| 38 | `recipient_country` | recipient country | Source-reported recipient country, not project footprint. |
| 39 | `recipient_ein` | recipient ein | Reported recipient tax identifier as text; blank means unavailable or unverified. |
| 40 | `recipient_entity_type` | recipient entity type | Type of the approved registered recipient; blank when no approved recipient binding exists. |
| 41 | `recipient_name` | recipient name | Recipient name as published; may identify a program or intermediary rather than a distinct legal payee. |
| 42 | `recipient_name_reported` | recipient name reported | Recipient name as published, without asserting an approved Cedar identity. |
| 43 | `recipient_role` | recipient role | Presence of a fiscal sponsor or beneficiary. Consult both fields; the label does not identify the legal payee. |
| 44 | `recipient_state` | recipient state | Source-reported recipient state, not project footprint. Blank means unstated or not representable as one state. |
| 45 | `record_kind` | record kind | grant_event is a grant-related disclosure; recipient_year_total is an annual aggregate, not a distinct award. |
| 46 | `report_year` | report year | Source year label; fiscal, calendar, reporting or grant-cycle basis must not be inferred. |
| 47 | `report_year_basis` | report year basis | Source-supported meaning of report_year; blank means fiscal/calendar basis is unestablished. |
| 48 | `review_action` | review action | Recorded repeat-disclosure review action, not an affirmative canonical identity decision. |
| 49 | `rights_classification` | rights classification | Existing source-family rights classification; does not override row, field or release holds. |
| 50 | `source_class` | source class | Reviewed source-family category used by maintained acquisition and factual-publication policy. |
| 51 | `source_document_sha256` | source document sha256 | SHA256 of retained source bytes; identifies evidence, not legal clearance or verification of every assertion. |
| 52 | `source_id` | source id | Acquisition or source-registry key; not a recipient ID and not itself a readable publisher name. |
| 53 | `source_locator` | source locator | Within-document recipient, page or section locator; used with URL and recipient to reproduce the disclosure key. |
| 54 | `source_observation_status` | source observation status | Preserved upstream verification status, not a canonical identity determination. |
| 55 | `source_policy_eligibility` | source policy eligibility | Existing source-policy permission for this factual projection, separate from production approval. |
| 56 | `source_qa_flags` | source qa flags | Upstream quality flags; blank means none recorded, not that every semantic issue is resolved. |
| 57 | `source_record_id` | source record id | Source-system record ID; may be blank and need not be unique across publishers. |
| 58 | `source_retrieved_date` | source retrieved date | Evidence retrieval date; never substitute for announcement, approval, payment or reporting period. |
| 59 | `source_url` | source url | Exact source citation; a public URL alone does not grant redistribution rights. |
| 60 | `temporal_caveat` | temporal caveat | Limit on source-date or source-year interpretation, including unestablished report-year basis. |
| 61 | `term_end` | term end | Reported award or coverage-period end; interpret with precision, not as payment date. |
| 62 | `term_end_precision` | term end precision | Source precision of the end date; never invent a day for month-only or year-only evidence. |
| 63 | `term_start` | term start | Reported award or coverage-period start; interpret with precision, not as payment date. |
| 64 | `term_start_precision` | term start precision | Source precision of the start date; never invent a day for month-only or year-only evidence. |
| 65 | `transfer_kind` | transfer kind | Reported transfer category, separate from its commitment or payment status. |
| 66 | `version_kind` | version kind | Disclosure version: original, amended, renewed, expanded or unknown. Delivered original_unconfirmed remains unconfirmed; a version is not a new award. |

### PLOT

Collection `plot` · table `plot` · installed producer spreadsheet

**Rows in this installed spreadsheet:** 151,715. This is an observation count at the declared record types and grains.

**One row is:** One permitted observation at its declared record_type and record_grain.

**Release or source location:** Exact release a450bd56cdcafd2f7ff1d8191f141b025ad384eeb5a3d676fc96a6598c4d182b; one researcher spreadsheet.

The columns below describe the exported names directly. No legacy rename, combine or promised identity block is applied to this spreadsheet.

**Fields (106):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `record_type` | record type | The permitted logical record type from the pinned release. |
| 2 | `record_key` | record key | The original source primary-key values serialized as JSON. |
| 3 | `record_grain` | record grain | What one observation of this record type represents; never sum across overlapping grains. |
| 4 | `application_date` | application date | Reported application date, not approval |
| 5 | `application_number` | application number | Application number, distinct from issued permit number |
| 6 | `approved_date` | approved date | Reported approval date, not issuance |
| 7 | `authority_name` | authority name | Issuing or reviewing public authority |
| 8 | `completion_date` | completion date | Reported completion date under source definition |
| 9 | `date_source_field` | date source field | Source field furnishing event date |
| 10 | `default_map_visible` | default map visible | Preserved map display gate; false rows are not map features |
| 11 | `effective_date` | effective date | Reported effective date |
| 12 | `environmental_event_id` | environmental event id | Preserved lifecycle event object ID |
| 13 | `environmental_events__environmental_record_id` | environmental events  environmental record id | Parent EPA program record object ID |
| 14 | `environmental_events__event_date` | environmental events  event date | Source lifecycle date; scheduled dates remain flagged |
| 15 | `environmental_events__event_date_precision` | environmental events  event date precision | Precision of source event date |
| 16 | `environmental_events__event_type` | environmental events  event type | Distinct program lifecycle event kind |
| 17 | `environmental_events__source_id` | environmental events  source id | Saved official EPA source family |
| 18 | `environmental_events__source_url` | environmental events  source url | Exact source citation; saved query may no longer resolve |
| 19 | `environmental_permits__environmental_record_id` | environmental permits  environmental record id | Preserved EPA program record object ID |
| 20 | `environmental_permits__expiration_date` | environmental permits  expiration date | Reported or scheduled expiration date |
| 21 | `environmental_permits__issued_date` | environmental permits  issued date | Reported issuance date |
| 22 | `environmental_permits__program` | environmental permits  program | Environmental regulatory program |
| 23 | `environmental_permits__source_id` | environmental permits  source id | Saved official EPA source family |
| 24 | `environmental_permits__source_permit_id` | environmental permits  source permit id | EPA NPDES permit identifier; not a parcel identifier |
| 25 | `environmental_permits__source_record_url` | environmental permits  source record url | EPA record citation |
| 26 | `environmental_permits__source_snapshot_date` | environmental permits  source snapshot date | Exact ISO capture date or timestamp; not event time |
| 27 | `environmental_permits__source_url` | environmental permits  source url | Exact source citation; saved query may no longer resolve |
| 28 | `environmental_permits__state` | environmental permits  state | EPA reported state |
| 29 | `environmental_permits__status_raw` | environmental permits  status raw | EPA reported permit status at snapshot |
| 30 | `estate_type` | estate type | Reported interest or estate category; partial interests remain distinct |
| 31 | `event_interpretation` | event interpretation | Reported program date or scheduled-date interpretation |
| 32 | `facility_name_raw` | facility name raw | Facility name reported by EPA; not verified legal owner |
| 33 | `facility_registry_id` | facility registry id | External EPA FRS identifier; not a Cedar business ID |
| 34 | `future_relative_to_capture` | future relative to capture | True if event date follows source snapshot |
| 35 | `geometry_display_scope` | geometry display scope | Preserved geometry interest scope; not exclusive title |
| 36 | `geometry_wkb_hex` | geometry wkb hex | Original 2D WKB encoded as hex, CRS84 longitude/latitude; structural checks only |
| 37 | `latitude` | latitude | Reported WGS84 latitude; environmental context only |
| 38 | `longitude` | longitude | Reported WGS84 longitude; environmental context only |
| 39 | `municipality` | municipality | Source municipality |
| 40 | `native_ownership_supported` | native ownership supported | Always false: EPA flags do not establish Native ownership |
| 41 | `owner_name_raw` | owner name raw | Assessor-reported owner label; not verified beneficial ownership or title |
| 42 | `ownership_observation_date` | ownership observation date | Preserved ownership observation date and precision |
| 43 | `ownership_observations__county_fips` | ownership observations  county fips | County FIPS context; parcel IDs are not nationally unique |
| 44 | `ownership_observations__record_grain` | ownership observations  record grain | BIA tract feature or assessor parcel feature; a tract can contain several parcels |
| 45 | `ownership_observations__source_id` | ownership observations  source id | Exact acquired source family |
| 46 | `ownership_observations__source_record_url` | ownership observations  source record url | Exact source feature citation |
| 47 | `ownership_observations__source_snapshot_date` | ownership observations  source snapshot date | Reported source snapshot date; blank remains unknown |
| 48 | `ownership_observations__source_url` | ownership observations  source url | Source dataset citation |
| 49 | `ownership_observations__state` | ownership observations  state | State context |
| 50 | `ownership_time_basis` | ownership time basis | Evidence basis and limitations for owner observation time |
| 51 | `permit_event_id` | permit event id | Preserved lifecycle event key |
| 52 | `permit_events__event_date` | permit events  event date | Reported lifecycle date, not necessarily actual physical activity |
| 53 | `permit_events__event_date_precision` | permit events  event date precision | Source date precision |
| 54 | `permit_events__event_type` | permit events  event type | Application, approval, issuance, inspection or other lifecycle kind |
| 55 | `permit_events__permit_id` | permit events  permit id | Parent permit key; many events per permit |
| 56 | `permit_events__source_id` | permit events  source id | Exact source dataset |
| 57 | `permit_events__source_url` | permit events  source url | Exact source event citation |
| 58 | `permit_events__state` | permit events  state | Source state |
| 59 | `permit_number` | permit number | Public authority permit number |
| 60 | `permit_type_raw` | permit type raw | Source permit category |
| 61 | `permits__county_fips` | permits  county fips | County FIPS context |
| 62 | `permits__expiration_date` | permits  expiration date | Reported or scheduled expiration; not a realized event |
| 63 | `permits__issued_date` | permits  issued date | Reported issuance date, not work completion |
| 64 | `permits__permit_id` | permits  permit id | Preserved permit/application object key |
| 65 | `permits__program` | permits  program | Permit program |
| 66 | `permits__source_id` | permits  source id | Source jurisdiction and dataset |
| 67 | `permits__source_permit_id` | permits  source permit id | Source permit key scoped to jurisdiction |
| 68 | `permits__source_record_url` | permits  source record url | Additional exact source citation |
| 69 | `permits__source_snapshot_date` | permits  source snapshot date | Source capture date, distinct from lifecycle dates |
| 70 | `permits__source_url` | permits  source url | Source record citation |
| 71 | `permits__state` | permits  state | Source state |
| 72 | `permits__status_raw` | permits  status raw | Source status at capture; no completion inferred |
| 73 | `plot_record_id` | plot record id | Preserved PLOT observation object key; not a Native entity ID |
| 74 | `record_kind` | record kind | Source application, permit or agency action record kind |
| 75 | `record_role` | record role | Preserved interpretation of source observation |
| 76 | `recorded_acres` | recorded acres | Source reported land area; use recorded_acres_measure before aggregation |
| 77 | `recorded_acres_measure` | recorded acres measure | Area measurement basis; not necessarily surveyed or exclusive area |
| 78 | `reported_value` | reported value | Source permit valuation; repeated child permits may carry same value |
| 79 | `research_scope` | research scope | EPA Indian Country program context; no parcel affiliation |
| 80 | `scheduled_only` | scheduled only | Scheduled rather than completed or observed lifecycle activity |
| 81 | `source_field` | source field | EPA field that supplied the lifecycle date |
| 82 | `source_object_id` | source object id | Source feature key scoped to source_id |
| 83 | `source_ownership_code` | source ownership code | Source ownership category, such as BIA T; not a canonical owner binding |
| 84 | `source_parcel_id` | source parcel id | Source parcel or tract identifier; jurisdiction and grain required |
| 85 | `source_tax_aggregation_eligible` | source tax aggregation eligible | Preserved source tax aggregation gate; no override |
| 86 | `source_vintage` | source vintage | Source release vintage; not an event date |
| 87 | `submitted_date` | submitted date | Reported submission date |
| 88 | `tax_aggregation_status` | tax aggregation status | Preserved aggregation exclusion or eligibility explanation |
| 89 | `tax_amount` | tax amount | Reported property tax; tax_measure and tax_year define meaning; not payment |
| 90 | `tax_amount_observed` | tax amount observed | Observed tax monetary value, distinct from harmonized tax_amount; not a boolean |
| 91 | `tax_comparison_group` | tax comparison group | Comparable tax series classification; aggregate only within permitted group |
| 92 | `tax_cross_county_pooling_status` | tax cross county pooling status | Whether county definitions permit pooling; preserve restrictions |
| 93 | `tax_measure` | tax measure | Source-specific net, gross or other tax measure; not interchangeable |
| 94 | `tax_year` | tax year | Source tax-roll year; not owner observation or filing year |
| 95 | `terminated_date` | terminated date | Reported termination date |
| 96 | `tract_observations__county_fips` | tract observations  county fips | County FIPS context; parcel IDs are not nationally unique |
| 97 | `tract_observations__record_grain` | tract observations  record grain | BIA tract feature or assessor parcel feature; a tract can contain several parcels |
| 98 | `tract_observations__source_id` | tract observations  source id | Exact acquired source family |
| 99 | `tract_observations__source_record_url` | tract observations  source record url | Exact source feature citation |
| 100 | `tract_observations__source_snapshot_date` | tract observations  source snapshot date | Reported source snapshot date; blank remains unknown |
| 101 | `tract_observations__source_url` | tract observations  source url | Source dataset citation |
| 102 | `tract_observations__state` | tract observations  state | State context |
| 103 | `trust_status` | trust status | Preserved reported trust classification |
| 104 | `value_currency` | value currency | Currency reported for valuation |
| 105 | `value_measure` | value measure | Source valuation definition; not a payment or expenditure |
| 106 | `whole_footprint_ownership_claim` | whole footprint ownership claim | Preserved limit on whole-footprint ownership interpretation |

## Review questions

- Does each definition preserve the source's subject, relationship, date and amount basis?
- Are record type, grain and version restrictions sufficient for the proposed analysis?
- Which identity or source conflicts still need adjudication, and what evidence would resolve them?

