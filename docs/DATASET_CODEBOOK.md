# Cedar Press datasets: the proposed structure of each, for review

Generated from `data/cedar/codebook.json` by `scripts/codebook-markdown.mjs`; edit the JSON, not this file. Written 2026-09-05.

## What this is

Cedar Press sells twelve collections. Each collection has one customer-facing dataset (its flagship table) and, in the workspace, a number of supporting tables. Today the flagship files carry between 37 and 78 columns, of which a third to two-thirds are pipeline bookkeeping: how a row was matched, when it was built, the basis of a derived value. This document is the data dictionary of the structure each dataset has when a customer downloads it under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`: what one row is, and the columns that ship, each with a plain-English label and what it means. Every column here is one `docs/FIELD_MAP_2026-09-05.md` ships, under the name the map gives it; columns not listed stay in the workspace, and the per-column decisions with their reasons are in the map (the earlier reasoning is in `docs/COLUMN_ORDER_NOTE_FOR_THE_TERMINAL_2026-09-05.md`).

Three rules apply to every dataset:

1. **The Cedar opening block comes first**: `cedar_uid` (the entity's permanent ID), `cedar_entity_name` (its name as Cedar's register spells it), `cedar_entity_type` (which of Cedar's eighteen classes it is) and `cedar_entity_role` (why the entity is on the row). The first three are the join key across collections; the fourth says what the join means. Where a table lacks one today it is marked *to add* and the writer fills it from the register; where it carries the same thing under another name, the rename is shown.
2. **One row is one thing**, stated at the top of each dataset; a table whose rows name several entities carries them separated by `|`.
3. **Every amount says what it is** (an obligation, an announced value, a reported spend) and is never summed across datasets; every row cites a source.

Where the data lives: the full tables are built in the Cedar data workspace by `code/1135_full_dataset_review_bundle.py` into `dist/review/spreadsheets/<collection>/<table>.csv` (6.2 GB in all, not in the website repository); ten-row samples of each are copied to the website at `public/data/cedar/samples/<collection>/<table>__10.csv` and served at `https://cedarpress.ai/data/cedar/samples/...`. The entity register is `data/spine/cedar_entity_names.csv` (1,916 entities, 18 classes).

Meanings below were read from the column names and ten rows of values and are to be confirmed against the build scripts; a meaning marked *(confirm)* is the least certain.

## The datasets

### Federal Funding to Indian Country

Collection `funding` · table `federal_funding_transactions` · 701,955 rows in the full table · Cedar Press shelf

**One row is** One federal assistance transaction (a grant, loan, direct payment or insurance action) reported on USAspending, linked to the Native entity that received it.

**Where:** workspace dist/customer/funding.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/funding/federal_funding_transactions.csv; built by code/1135_full_dataset_review_bundle.py from the USAspending assistance archive.

**Columns a subscriber sees (37):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` (*rename to `cedar_entity_name`*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. |
| 3 | `cedar_entity_type` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: recipient. |
| 5 | `assistance_award_unique_key` | Award ID | USAspending's key for the whole award; the source link is built from it. |
| 6 | `award_id_fain` | Award number | The award's Federal Award Identification Number; several transactions can share one. |
| 7 | `assistance_transaction_unique_key` | Transaction ID | USAspending's unique key for this transaction. Cite it to find the exact record. |
| 8 | `recipient_name` | Recipient as recorded | The recipient's name as the award records it, before Cedar resolved it to the entity. |
| 9 | `recipient_uei` | Recipient UEI | The recipient's federal Unique Entity ID. |
| 10 | `assistance_type_description` | Assistance type | What kind of assistance it is: formula grant, project grant, direct payment, loan, insurance. |
| 11 | `credit_instrument_flag` | Loan or guarantee (yes or no) | Whether this row is a loan or loan guarantee, so the loan columns are read for the rows they belong to. |
| 12 | `awarding_agency_name` | Agency | The department that made the award. |
| 13 | `awarding_sub_agency_name` | Office | The office within the department. |
| 14 | `cfda` | Program number | The Assistance Listing (CFDA) number of the federal program. |
| 15 | `cfda_title` | Program | The federal program's name. |
| 16 | `fiscal_year` | Fiscal year | The federal fiscal year of the action (October to September), which is what USAspending reports and what the year filter uses. |
| 17 | `fy_partial_flag` | Partial fiscal year | Whether this row falls in a fiscal year the source had not finished reporting when Cedar pulled it (yes or no). Do not compare a partial year to a complete one. |
| 18 | `action_date` | Action date | The date the agency took this action. |
| 19 | `obligated_usd` | Amount obligated | Dollars obligated by this transaction. Negative values are de-obligations, kept as recorded. |
| 20 | `obligated_usd_real2025` | Amount in 2025 dollars | The same amount adjusted for inflation to 2025 dollars. |
| 21 | `face_value_of_loan` | Loan face value | For loans, the face value of this loan; zero for grants. |
| 22 | `original_loan_subsidy_cost` | Original loan subsidy cost | For a loan, the government's estimated cost of the subsidy when it was made. A loan measure; never added to obligations. |
| 23 | `total_face_value_of_loan` | Award loan face value | For loans, the face value of the whole award to date. |
| 24 | `total_loan_subsidy_cost` | Total loan subsidy cost | The subsidy cost across the award's loan actions. Never added to obligations. |
| 25 | `business_types_description` | Recipient type as recorded | How USAspending classifies the recipient (for example, federally recognized tribal government). |
| 26 | `recipient_city_name` | Recipient city | City of the recipient's address on the award. |
| 27 | `recipient_state_code` | Recipient state | State of the recipient's address on the award. |
| 28 | `geo_recipient_county_name` (*rename to `recipient_county_name`*) | Recipient county | The county of the recipient's address, which is not necessarily where the funded work happens. |
| 29 | `geo_recipient_county_fips` (*rename to `recipient_county_fips`*) | Recipient county FIPS | The county code of the recipient's address. |
| 30 | `geo_pop_county_name` (*rename to `place_of_performance_county_name`*) | Place of performance county | The county where the funded work is performed, as the award reports it. |
| 31 | `geo_pop_county_fips` (*rename to `place_of_performance_county_fips`*) | Place of performance county FIPS | The county code where the funded work is performed, as the award reports it. |
| 32 | `attributed_flag` | Attributed to the entity | Whether Cedar attributes this transaction to the Native entity (yes) or keeps it in the file unattributed (no). Cedar's totals count attributed rows only. |
| 33 | `attribution_status` | Attribution status | How the attribution stands: attributed through the register, unattributed, or under review. |
| 34 | `attribution_method` | How the entity was matched | How Cedar linked this recipient to the entity (for example, an exact UEI match). |
| 35 | `confidence_tier` | Match confidence | Cedar's confidence in the link: A is strongest. |
| 36 | `source_system` (*to add*) | Source system | Which source family the row came from: the USAspending archive or the historical FAADS files. The two overlap in coverage and are never summed as one. |
| 37 | `source_url` (*to add*) | Source | The award's page on USAspending. |

### Federal Register

Collection `federal-register` · table `consultation_events` · 11,402 rows in the full table · Cedar Press shelf

**One row is** One tribal consultation event announced or reported in the Federal Register, one row per event and named participant (most events name no single tribe).

**Where:** workspace dist/customer/federal-register.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/federal-register/consultation_events.csv; built from Federal Register documents.

**Columns a subscriber sees (27):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. |
| 2 | `cedar_entity_name` (*to add*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. |
| 3 | `cedar_entity_type` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `participant_role` (*rename to `cedar_entity_role`*) | Entity role | Why the entity is on this row: read from participant_role. |
| 5 | `consultation_event_id` | Event ID | Cedar's identifier for the consultation event. |
| 6 | `fr_document_number` | Document number | The Federal Register document number. |
| 7 | `consultation_type` (*rename to `action_type`*) | Kind of consultation | Whether this is a consultation session, a notice of consultation, or a consultation reported inside another document. |
| 8 | `document_role` | Document role | Whether the document announces a consultation or reports one that already happened. |
| 9 | `topic` | Topic | What the consultation was about, from the document's title. |
| 10 | `agency` | Agency | The department holding the consultation. |
| 11 | `sub_agency` | Office | The office within the department. |
| 12 | `program` | Program | The program or matter the consultation concerns, where the document names one. |
| 13 | `notice_date` (*rename to `publication_date`*) | Notice date | The date the Federal Register document was published. |
| 14 | `event_start_date` | Event start | When the consultation began, as the notice states it. |
| 15 | `event_end_date` | Event end | When it ended, where stated. |
| 16 | `comment_deadline` | Comment deadline | The date written comments were due, where stated. |
| 17 | `location` | Location | Where the consultation was held. |
| 18 | `format` | Format | In person, virtual, teleconference, written comment, or a combination. |
| 19 | `participant_name_as_published` | Participant as published | The tribe or organization named in the document, as it spells it. |
| 20 | `has_written_comments` | Written comments invited | Whether the document invites written comments (yes or no). |
| 21 | `has_summary` | Summary available (yes or no) | Whether a summary of the consultation is available from the source. |
| 22 | `has_transcript` | Transcript available (yes or no) | Whether a transcript is available from the source. |
| 23 | `is_event_primary_row` | Counts as one consultation | One row per event carries yes; the rest are additional participants of the same event. Count consultations by this column, not by rows. |
| 24 | `n_participant_rows_for_event` | Participant rows for this event | How many rows this event has in the file. |
| 25 | `federal_register_citation` | Citation | The Federal Register citation (volume FR page). |
| 26 | `source_quote` | Source passage | The sentence in the document this row was read from. |
| 27 | `source_url` | Source | The document on federalregister.gov. |

### Legislation

Collection `legislation` · table `native_bills` · 3,069 rows in the full table · Cedar Press shelf

**One row is** One bill in Congress that concerns Native nations or organizations, with the entities it names.

**Where:** workspace dist/customer/legislation.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/legislation/native_bills.csv; built from the Congress.gov API.

**Columns a subscriber sees (25):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `entity_cedar_uids` (*rename to `cedar_uid`*) | Cedar IDs | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. Several, separated by \|, where a row names several entities. |
| 2 | `entity_names` (*rename to `cedar_entity_name`*) | Native entities | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. |
| 3 | `cedar_entity_type` (*to add*) | Entity types | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: named in the bill. |
| 5 | `bill_id` | Bill ID | Congress, chamber and number, for example 103-hr-2366. |
| 6 | `congress` | Congress | Which Congress (the 103rd, and so on). |
| 7 | `chamber` | Chamber | House or Senate. |
| 8 | `bill_type` | Bill type | hr, s, hjres and the like, as Congress.gov codes them. |
| 9 | `number` (*rename to `bill_number`*) | Number | The bill's number in its chamber. |
| 10 | `title` | Title | The bill's title. |
| 11 | `policy_area` | Policy area | Congress.gov's policy area for the bill. |
| 12 | `bill_scope` (*rename to `relevance_scope`*) | Scope | Whether the bill is specific to one tribe or general to Indian Country. |
| 13 | `entity_class_scope` (*rename to `relevance_class_scope`*) | Relevance class scope | When the bill names no entity, the class of entity it is about (federally recognized tribes, Alaska Native corporations). Class-wide relevance, not any entity's class. |
| 14 | `sponsor` (*rename to `sponsor_name`*) | Sponsor | The sponsoring member, with party and state. |
| 15 | `sponsor_bioguide_id` | Sponsor ID | The sponsor's Biographical Directory identifier. |
| 16 | `cosponsor_count` | Cosponsors | How many members cosponsored it. |
| 17 | `introduced_date` | Introduced | The date the bill was introduced; the year filter uses this. |
| 18 | `latest_action` | Latest action | The most recent action recorded on the bill. |
| 19 | `latest_action_date` | Latest action date | When that action happened. |
| 20 | `outcome` (*rename to `status`*) | Outcome | Where the bill ended: enacted, passed one chamber, died in committee. |
| 21 | `companion_bill_id` | Companion bill | The matching bill in the other chamber, where one exists. |
| 22 | `has_rollcall` | Had a roll-call vote | Whether any roll-call vote was taken (yes or no). |
| 23 | `n_rollcalls` (*rename to `rollcall_count`*) | Roll-call votes | How many recorded roll-call votes the bill had. |
| 24 | `entity_link_tiers` | Entity link tiers | How firmly each named entity resolves to the register, in the same order as the IDs (A strongest). |
| 25 | `source_url` (*to add*) | Source | The bill's page on congress.gov. |

### Indian Country Deals

Collection `deals` · table `deals_classified` · 1,073 rows in the full table · Cedar Press shelf

**One row is** One announced transaction or award involving a Native party: an acquisition, a financing, a grant, a partnership.

**Where:** workspace dist/customer/deals.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/deals/deals_classified.csv; assembled from announcements, filings and agency award lists.

**Columns a subscriber sees (32):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. |
| 2 | `native_party_canonical_name` (*rename to `cedar_entity_name`*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. |
| 3 | `cedar_entity_type` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `native_party_role` (*rename to `cedar_entity_role`*) | Entity role | Why the entity is on this row: read from native_party_role (acquirer, borrower, issuer, partner, grantee, seller). |
| 5 | `Deal_ID` (*rename to `deal_id`*) | Deal ID | Cedar's identifier for the deal. |
| 6 | `Deal_Title` (*rename to `deal_title`*) | Title | A one-line description of the deal. |
| 7 | `Native_Party` (*rename to `native_party`*) | Native party as published | The Native party's name as the source gives it. |
| 8 | `Native_Party_Type` (*rename to `native_party_type`*) | Native party type as published | How the source describes the Native party. |
| 9 | `Counterparty_or_Funder` (*rename to `counterparty`*) | Counterparty or funder | The other side of the deal. |
| 10 | `Deal_Category` (*combines into `deal_category`*) | Category | Acquisition, grant or public financing, joint venture, and so on. |
| 11 | `Event_Type` (*combines into `deal_category`*) | Event | What kind of event this row records (an acquisition of a 90% interest, an award). |
| 12 | `transaction_type` (*combines into `deal_category`*) | Transaction type | The third of three overlapping classifications; shown until the one taxonomy replaces all three. |
| 13 | `Industry` (*rename to `industry`*) | Industry | The industry the deal is in. |
| 14 | `sector` | Sector | The broad sector the deal belongs to, beside the finer industry. |
| 15 | `capital_source` | Capital source | Where the capital comes from: public, private or tribal. |
| 16 | `Event_Date` (*rename to `event_date`*) | Date | When the deal happened or was announced. |
| 17 | `Event_Date_precision` (*rename to `event_date_precision`*) | Date precision | Whether the date is known to the day, the month or the year. |
| 18 | `Status` (*combines into `status`*) | Status | Completed, announced, awarded, pending. |
| 19 | `deal_status_std` (*combines into `status`*) | Status (standardized) | The standardized status; shown until one status column replaces the two. |
| 20 | `Announced_Value_USD` (*rename to `announced_value_usd`*) | Announced value | The dollar value announced, where one was. |
| 21 | `Value_Type` (*rename to `value_basis`*) | What the value is | What the announced figure represents (consideration paid, grant amount, project cost). |
| 22 | `Project_Total_Value_USD` (*rename to `project_total_value_usd`*) | Project total | The total project value, where larger than the announced value. |
| 23 | `State` (*rename to `state`*) | State | The state the deal is located in. |
| 24 | `Location` (*rename to `location`*) | Location | The place, as the source gives it. |
| 25 | `Description` (*rename to `description`*) | Description | A longer description of the deal. |
| 26 | `Native_Connection` (*rename to `native_connection`*) | Native connection | Why this deal is in the collection: how the Native party is connected. |
| 27 | `Verification_Status` (*rename to `verification_status`*) | Verification | Whether the deal was verified against a primary source. |
| 28 | `native_party_attribution_tier` (*rename to `attribution_tier`*) | Attribution tier | How firmly the Native party resolves to Cedar's register (A strongest). |
| 29 | `Source_1` (*rename to `source_url`*) | Source | The primary source document or page. |
| 30 | `Source_1_Type` (*rename to `source_type`*) | Source type | What kind of document the primary source is. |
| 31 | `Source_2` (*rename to `source_url_2`*) | Second source | A second source, where one was found. |
| 32 | `Source_2_Type` (*rename to `source_type_2`*) | Second source type | What kind of document the second source is. |

### NAGPRA

Collection `nagpra` · table `nagpra_notices` · 6,792 rows in the full table · Cedar Press shelf

**One row is** One NAGPRA notice in the Federal Register (a notice of inventory completion or intent to repatriate), with the institution holding the remains or objects and the Native entities the notice names.

**Where:** workspace dist/customer/nagpra.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/nagpra/nagpra_notices.csv; built from Federal Register NAGPRA notices.

**Columns a subscriber sees (52):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `affiliated_entity_ids` (*rename to `cedar_uid`*) | Cedar IDs | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. Several, separated by \|, where a row names several entities. |
| 2 | `cedar_entity_name` (*to add*) | Native entities | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. |
| 3 | `cedar_entity_type` (*to add*) | Entity types | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: culturally affiliated, as the notice determines. |
| 5 | `document_number` | Document number | The Federal Register document number. |
| 6 | `notice_type` | Notice type | Inventory completion, intent to repatriate, or correction. |
| 7 | `statute_stage` (*rename to `process_stage`*) | Statute stage | Which stage of NAGPRA the notice is made under. |
| 8 | `is_correction` | Correction | Whether this notice corrects an earlier one (yes or no). |
| 9 | `publication_date` | Published | The date the notice was published. |
| 10 | `title` | Title | The notice's title. |
| 11 | `institution_name` | Institution | The museum, university or agency holding the remains or objects. |
| 12 | `institution_names_all` | All institutions | Every institution the notice names, where it names more than one, separated by \|. |
| 13 | `institution_type_derived` (*rename to `institution_type`*) | Institution type | Museum, university, federal agency, and so on. |
| 14 | `institution_city` | Institution city | Where the institution is. |
| 15 | `institution_state` | Institution state | Its state. |
| 16 | `responsible_party_statement` | Responsible party | The official the notice names as responsible for the holdings, as stated. |
| 17 | `agency_names` | Publishing agency | The agency that published the notice. |
| 18 | `object_categories` | Object categories | Which categories of items the notice covers (human remains, associated funerary objects, sacred objects, objects of cultural patrimony). |
| 19 | `mni_total_stated` | Individuals | The minimum number of individuals the notice states. |
| 20 | `mni_statements` | Individuals count, as stated | The sentence stating the minimum number of individuals, kept where the number alone is ambiguous. |
| 21 | `n_associated_funerary_objects_stated` | Associated funerary objects | Count stated in the notice. |
| 22 | `n_unassociated_funerary_objects_stated` | Unassociated funerary objects | Count stated in the notice. |
| 23 | `n_sacred_objects_stated` | Sacred objects | Count stated in the notice. |
| 24 | `n_objects_of_cultural_patrimony_stated` | Objects of cultural patrimony | Count stated in the notice. |
| 25 | `cultural_items_total_stated` | Cultural items total, as stated | A total the notice itself states. Cedar never adds the categories together. |
| 26 | `removal_counties` | Removal counties | Where the remains or objects were removed from. |
| 27 | `removal_states` | Removal states | The states of those places. |
| 28 | `repatriation_eligible_date` | Repatriation eligible from | The date after which repatriation may proceed, as the notice states. Not evidence that a transfer happened. |
| 29 | `response_deadline_date` | Response deadline | The date by which other claimants must respond. |
| 30 | `lineal_descendant_determination` | Lineal descendant found | Whether a lineal descendant was determined (yes or no). |
| 31 | `culturally_unidentifiable` | Culturally unidentifiable | Whether the remains are determined culturally unidentifiable (yes or no). |
| 32 | `n_affiliated_named` | Affiliated parties named | How many parties the notice names as culturally affiliated. |
| 33 | `n_affiliated_resolved` | Affiliated parties resolved | How many of those Cedar could resolve to a register entity. |
| 34 | `n_consulted_named` | Consulted parties named | How many parties the notice names as consulted. |
| 35 | `n_consulted_resolved` | Consulted parties resolved | How many of those Cedar could resolve to a register entity. The gap is real uncertainty, not an omission. |
| 36 | `consulted_entity_ids` | Cedar IDs (consulted) | Entities the notice says were consulted. |
| 37 | `n_disposition_priority_named` | Priority parties named | How many parties the notice names with disposition priority. |
| 38 | `n_disposition_priority_resolved` | Priority parties resolved | How many of those Cedar could resolve. |
| 39 | `disposition_priority_entity_ids` | Cedar IDs (disposition priority) | Entities with priority for disposition, where stated. |
| 40 | `n_repatriation_recipient_named` | Recipients named | How many recipients the notice names. |
| 41 | `n_repatriation_recipient_resolved` | Recipients resolved | How many of those Cedar could resolve. |
| 42 | `repatriation_recipient_entity_ids` | Cedar IDs (repatriation recipient) | Entities the notice names to receive the repatriation. |
| 43 | `n_letter_of_support_named` | Letters of support named | How many parties the notice names as having submitted a letter of support. |
| 44 | `n_letter_of_support_resolved` | Letters of support resolved | How many of those Cedar could resolve to a register entity. |
| 45 | `letter_of_support_entity_ids` | Cedar IDs (letter of support) | The Cedar IDs of the parties named as submitting a letter of support, separated by \|. |
| 46 | `n_aboriginal_land_named` | Aboriginal-land parties named | How many parties the notice names for aboriginal land. |
| 47 | `n_aboriginal_land_resolved` | Aboriginal-land parties resolved | How many of those Cedar could resolve. |
| 48 | `aboriginal_land_entity_ids` | Cedar IDs (aboriginal land) | Entities on whose aboriginal land the removal site lies, where stated. |
| 49 | `n_parties_named` | Parties named in all | All parties the notice names, across roles. |
| 50 | `n_entities_resolved` | Entities resolved in all | How many distinct register entities those resolve to. |
| 51 | `source_url` | Source | The notice on federalregister.gov. |
| 52 | `pdf_url` | PDF | The notice as published, in PDF. |

### Native Federal Advocacy & Engagement

Collection `lobbying` · table `native_entity_lobbying_disclosures` · 27,825 rows in the full table · Cedar Press shelf

**One row is** One federal lobbying filing under the Lobbying Disclosure Act in which the client is a Native entity, one row per filing (amended filings appear once, as the current version).

**Where:** workspace dist/customer/lobbying.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/lobbying/native_entity_lobbying_disclosures.csv; built from the Senate LDA filings database.

**Columns a subscriber sees (34):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` (*rename to `cedar_entity_name`*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. |
| 3 | `entity_type` (*rename to `cedar_entity_type`*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: client. |
| 5 | `activity_type` (*to add*) | Activity type | Which kind of documented advocacy the row is. Every row today is an LDA filing; other source families join under the same schema as they are obtained. |
| 6 | `filing_uuid` (*rename to `filing_id`*) | Filing ID | The filing's identifier in the Senate LDA database. |
| 7 | `client_name` | Client | The client as the filing names it (the Native entity, in its own spelling). |
| 8 | `client_id` | Client ID | The client's identifier in the Lobbying Disclosure Act database. |
| 9 | `client_state` | Client state | The client's state. |
| 10 | `registrant_name` | Registrant | The lobbying firm or, for a self-filer, the client itself. |
| 11 | `registrant_id` | Registrant ID | The registrant's identifier in the Lobbying Disclosure Act database. |
| 12 | `registrant_state` | Registrant state | The registrant's state. |
| 13 | `self_filed` | Self-filed | Whether the client filed for itself rather than through a firm (yes or no). |
| 14 | `filing_type_display` (*rename to `filing_type`*) | Filing type | Registration, quarterly or year-end report, amendment, termination. |
| 15 | `filing_year` | Filing year | The year the filing covers. |
| 16 | `filing_period` | Period | Which reporting period of the year. |
| 17 | `dt_posted` (*rename to `posted_date`*) | Posted | When the filing was posted. |
| 18 | `termination_date` | Termination date | When the registration was terminated, where the filing is a termination. |
| 19 | `spend_usd` (*rename to `amount_usd`*) | Reported spend | Whichever of the two the filing reports; the basis column says which. |
| 20 | `spend_basis` (*rename to `amount_basis`*) | Basis of spend | Income, expenses, or none reported. |
| 21 | `income_usd` | Income reported | What the registrant reported receiving from the client this period. |
| 22 | `expenses_usd` | Expenses reported | What a self-filer reported spending this period. |
| 23 | `lobbying_issues_codes` | Issue codes | The LDA issue area codes on the filing. |
| 24 | `specific_issues_text` | Specific issues | What the filing says was lobbied on. |
| 25 | `government_entities` | Government entities contacted | Agencies and chambers the filing lists, separated by \|. |
| 26 | `affiliated_organizations` | Affiliated organizations | Organizations the filing lists as affiliated with the client. |
| 27 | `supersession_status` (*rename to `filing_status`*) | Version status | Whether a later amendment replaces this filing. |
| 28 | `superseded_by_filing_uuid` (*rename to `superseded_by_filing_id`*) | Replaced by | The filing that replaces this one, where one does. |
| 29 | `attribution_withdrawn` | Attribution withdrawn | Whether Cedar withdrew its link between this filing and the entity after review (yes or no). A withdrawn filing stays in the file; its spend is not counted as the entity's. |
| 30 | `attribution_withdrawn_reason` | Why withdrawn | The reason recorded for the withdrawal. |
| 31 | `attribution_method` | Attribution method | How the client was linked to the Native entity (an identifier, or a name with corroboration). |
| 32 | `match_confidence` | Match confidence | Cedar's confidence that the client is this entity. |
| 33 | `source_system` (*to add*) | Source system | Where the record came from: the Senate and House LDA database. |
| 34 | `filing_url` (*rename to `source_url`*) | Source | The filing on lda.senate.gov. |

### Native Federal Contractors

Collection `contractors` · table `prime_contracts` · 1,217,768 rows in the full table · Cedar Press+ shelf

**One row is** One federal contract transaction (an award or a modification) to a firm owned by a Native entity, as reported to FPDS and published on USAspending.

**Where:** workspace dist/customer/contractors.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/contractors/prime_contracts.csv; built from the USAspending contract archive.

**Columns a subscriber sees (45):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. |
| 2 | `canonical_name` (*rename to `cedar_entity_name`*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. |
| 3 | `cedar_entity_type` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: owner of the awardee, as resolved for the transaction's date. |
| 5 | `contract_award_unique_key` | Award ID | USAspending's key for the whole award; the source link is built from it. |
| 6 | `contract_number` | Contract number | The contract or order number. |
| 7 | `parent_contract_number` | Parent contract | The parent contract or vehicle, for orders. |
| 8 | `contract_transaction_unique_key` | Transaction ID | USAspending's key for this transaction. |
| 9 | `awardee_name` | Awardee | The contractor as the award names it. |
| 10 | `awardee_uei` | Awardee UEI | The contractor's federal Unique Entity ID. |
| 11 | `cage_code` | Awardee CAGE | The contractor's CAGE code, the identifier that persists across the DUNS-to-UEI change; masked on rows the publication rule withholds. |
| 12 | `parent_name` | Awardee's parent | The contractor's parent as the award records it. |
| 13 | `parent_uei` | Parent UEI | The UEI of the parent FPDS declares for the contractor. |
| 14 | `owner_attribution_status` | Ownership at the time | Whether the entity's ownership of the awardee was confirmed as of the transaction. |
| 15 | `owner_as_of_transaction_cedar_uid` | Owner as of the action | The Cedar ID of the entity that owned the contractor on the action date where the ownership history resolves it; UNKNOWN where it does not. Never the current owner assumed backwards. |
| 16 | `fiscal_year` | Fiscal year | The federal fiscal year of the action. |
| 17 | `action_date` | Action date | The date of this award or modification. |
| 18 | `total_obligations` | Amount obligated | Dollars obligated by this transaction. Sum these, never the award value. |
| 19 | `total_obligations_real2025` | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. |
| 20 | `total_award_value` | Award value to date | The whole award's value as restated on this row. Cumulative: never add it across rows. |
| 21 | `funding_agency` | Funding agency | The agency paying for the work. |
| 22 | `award_type` | Award type | Delivery order, BPA call, definitive contract, and so on. |
| 23 | `award_base_description` (*rename to `contract_description`*) | Description | The award's own description of the work. |
| 24 | `naics_code` | NAICS | The industry code of the work. |
| 25 | `naics_description` | Industry | What that code means. |
| 26 | `supersector` (*rename to `industry_group`*) | Industry group | The broad industry group the contract's NAICS code belongs to. |
| 27 | `product_or_service_code` | Product or service code | The federal product or service code (PSC), defined in the dictionary; the description is beside it. |
| 28 | `product_or_service_code_description` | Product or service | What was bought. |
| 29 | `setaside` | Set-aside | The set-aside the award was made under, if any. |
| 30 | `extent_competed_normalized` (*rename to `extent_competed`*) | Competition | How the award was competed. |
| 31 | `reported_8a` | 8(a) reported | Whether the award reports the 8(a) program (yes or no). |
| 32 | `reported_buy_indian` | Buy Indian Act reported (yes or no) | Whether the award reports use of the Buy Indian Act preference. Reported use, not eligibility. |
| 33 | `reported_indian_business` | Indian business reported (yes or no) | Whether the award reports the contractor as an Indian business under the relevant preference. |
| 34 | `reported_native_preference` | Native preference reported | Whether the award reports a Native preference (yes or no). |
| 35 | `recipient_city_name` | Awardee city | City of the awardee's address. |
| 36 | `recipient_state_code` | Awardee state | Its state. |
| 37 | `geo_recipient_county_name` (*rename to `recipient_county_name`*) | Recipient county | The county of the contractor's address, which is not where the work is performed. |
| 38 | `geo_recipient_county_fips` (*rename to `recipient_county_fips`*) | Recipient county FIPS | The county code of the contractor's address. |
| 39 | `place_of_perform_city` | Place of performance | City where the work is performed. |
| 40 | `place_of_perform_state` | Place of performance state | Its state. |
| 41 | `geo_pop_county_name` (*rename to `place_of_performance_county_name`*) | Place of performance county | The county where the contract is performed, as the award reports it. |
| 42 | `geo_pop_county_fips` (*rename to `place_of_performance_county_fips`*) | Place of performance county FIPS | The county code where the contract is performed. |
| 43 | `attribution_method` | How the entity was matched | How Cedar linked the awardee to its Native owner. |
| 44 | `confidence_tier` | Match confidence | Cedar's confidence in the link: A is strongest. |
| 45 | `source_url` (*to add*) | Source | The award's page on USAspending. |

### Native Subcontracting

Collection `subcontracting` · table `subawards` · 89,809 rows in the full table · Cedar Press+ shelf

**One row is** One federal subcontract reported through FSRS where the prime, the subcontractor or both are owned by a Native entity.

**Where:** workspace dist/customer/subcontracting.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/subcontracting/subawards.csv; built from the USAspending FSRS subaward pull.

**Columns a subscriber sees (54):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. |
| 2 | `cedar_entity_name` (*to add*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. |
| 3 | `cedar_entity_type` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: read from native_side: the Native owner of the subrecipient, of the prime, or of both. |
| 5 | `direction` (*rename to `native_side`*) | Which side is Native | Whether the prime, the sub, or both sides are Native-owned. |
| 6 | `sub_cedar_uid` | Subcontractor's Cedar ID | The Native entity owning the subcontractor, where one does. |
| 7 | `prime_cedar_uid` | Prime's Cedar ID | The Native entity owning the prime contractor, where one does. |
| 8 | `subaward_source_record_id` | Subaward ID | The subaward report's identifier. |
| 9 | `subaward_number` | Subaward number | The subaward's own number as the prime reported it. |
| 10 | `prime_award_id` | Prime award number | The prime contract's number. |
| 11 | `prime_award_unique_key` | Prime award key | USAspending's key for the prime award. |
| 12 | `sub_name` | Subcontractor | The subcontractor as reported. |
| 13 | `sub_uei` | Subcontractor UEI | Its Unique Entity ID. |
| 14 | `sub_cage` | Subcontractor CAGE | Its CAGE code, where reported. |
| 15 | `sub_parent_name` | Subcontractor's parent | Its parent as reported. |
| 16 | `sub_parent_uei` | Subrecipient parent UEI | The UEI of the subrecipient's declared parent. |
| 17 | `sub_parent_cage` | Subrecipient parent CAGE | The CAGE code of the subrecipient's declared parent. |
| 18 | `sub_business_types` | Subcontractor business types | The business types it reports (for example, Alaska Native Corporation owned). |
| 19 | `sub_native_tier` | Subrecipient attribution tier | How firmly the subrecipient resolves to a Native owner (A strongest). |
| 20 | `prime_name` | Prime contractor | The prime as reported. |
| 21 | `prime_uei` | Prime UEI | Its Unique Entity ID. |
| 22 | `prime_cage` | Prime CAGE | Its CAGE code, where reported. |
| 23 | `prime_parent_name` | Prime's parent | Its parent as reported. |
| 24 | `prime_parent_uei` | Prime parent UEI | The UEI of the prime's declared parent. |
| 25 | `prime_parent_cage` | Prime parent CAGE | The CAGE code of the prime's declared parent. |
| 26 | `prime_native_tier` | Prime attribution tier | How firmly the prime resolves to a Native owner (A strongest). |
| 27 | `award_kind` (*rename to `award_type`*) | Award type | Whether the prime award is a contract or an assistance award. The two populations are never combined in a total. |
| 28 | `subaward_type` | Subaward type | Sub-contract or sub-grant, as reported. |
| 29 | `subaward_date` | Subaward date | The date of the subaward. |
| 30 | `fiscal_year` | Fiscal year | The federal fiscal year of the subaward. |
| 31 | `subaward_sam_report_year` (*rename to `report_year`*) | Report year | The year of the report the subaward was filed in: the reporting period. |
| 32 | `subaward_sam_report_last_modified_date` (*rename to `report_last_modified_date`*) | Report last modified | When the report this row comes from was last modified: the version marker. A refreshed copy of the same report is not another subaward. |
| 33 | `subaward_amount` | Subaward amount | Dollars of the subaward. |
| 34 | `subaward_amount_real2025` | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. |
| 35 | `prime_award_amount` | Prime award amount | The prime contract's value. |
| 36 | `description` | Description | What the subcontract is for, as reported. |
| 37 | `naics` (*rename to `naics_code`*) | NAICS | The industry code. |
| 38 | `naics_title` (*rename to `naics_description`*) | Industry | What that code means. |
| 39 | `psc` (*rename to `product_or_service_code`*) | Product or service code | The federal product or service code of the subaward, where reported. |
| 40 | `psc_title` (*rename to `product_or_service_code_description`*) | Product or service | What the product or service code means. |
| 41 | `prime_top_awarding_agency` (*rename to `awarding_agency`*) | Agency | The department that awarded the prime contract. |
| 42 | `prime_awarding_sub_agency` (*rename to `awarding_sub_agency`*) | Office | The office within it. |
| 43 | `prime_set_aside` | Prime set-aside | The set-aside category of the prime award, where reported. |
| 44 | `geo_subawardee_city` (*rename to `sub_city`*) | Subrecipient city | The subrecipient's own city, never filled from the prime's address. |
| 45 | `sub_state` | Subcontractor state | Its state. |
| 46 | `geo_subawardee_zip5` (*rename to `sub_zip5`*) | Subrecipient ZIP | The subrecipient's own five-digit ZIP. |
| 47 | `geo_subawardee_country_code` (*rename to `sub_country_code`*) | Subrecipient country | The subrecipient's country code. |
| 48 | `geo_subawardee_county_name` (*rename to `sub_county_name`*) | Subrecipient county | The county of the subrecipient's address. |
| 49 | `geo_subawardee_county_fips` (*rename to `sub_county_fips`*) | Subrecipient county FIPS | The county code of the subrecipient's address. |
| 50 | `duplicate_status` | Duplicate status | Whether this row is the primary filing or a duplicate of one. Sum primaries only. |
| 51 | `subaward_exceeds_prime_flag` | Exceeds the prime award | Whether the subaward amount exceeds its prime award (yes or no). A real filing, kept in the file, but never added into totals. |
| 52 | `action_date_precedes_ffata_flag` | Date before FFATA | Whether the reported date precedes the reporting law itself (yes or no), a known filer anomaly; do not treat such a date as when the work happened. |
| 53 | `source_dataset` (*rename to `source_system`*) | Source system | Which source the report came from (the USAspending FSRS pull). |
| 54 | `source_url` | Source | The prime award's page on USAspending. |

### Native-Owned Businesses

Collection `owned` · table `native_owned_businesses` · 4,273 rows in the full table · Cedar Press+ shelf

**One row is** One business owned by a Native entity, in the register of such businesses.

**Where:** workspace dist/customer/owned.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/native-owned-businesses/native_owned_businesses.csv. NOT AUDITED: the sample is not in the repository yet; run scripts/import_cedar_manifest.py --audit after adding it.

**Columns a subscriber sees (3):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is linked to. Join key across every collection. |
| 2 | `canonical_name` | Native entity | The entity's name as Cedar's register spells it, so one entity reads the same in every collection. |
| 3 | `entity_class` | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village corporation, Native nonprofit, and so on). |

### Native Enterprises

Collection `nest` · table `nest_enterprises` · 5,820 rows in the full table · Cedar Press+ shelf

**One row is** One enterprise (a subsidiary, a joint venture, an affiliate) with the Native entity that owns or is affiliated with it and how.

**Where:** workspace dist/customer/nest.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/nest/nest_enterprises.csv; built from owners' own subsidiary listings, annual reports and federal identifier records.

**Columns a subscriber sees (31):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. |
| 2 | `owner_hub_name` (*rename to `cedar_entity_name`*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. |
| 3 | `owner_hub_entity_class` (*rename to `cedar_entity_type`*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `relation_class` (*rename to `cedar_entity_role`*) | Entity role | Why the entity is on this row: read from relationship_type: owner, or affiliated entity, of the enterprise. |
| 5 | `enterprise_id` | Enterprise ID | Cedar's identifier for the enterprise. |
| 6 | `enterprise_name` | Enterprise | The enterprise's name. |
| 7 | `name_variants_observed` (*rename to `name_variants`*) | Also seen as | Other spellings of the name in the sources, separated by \|. |
| 8 | `owner_class` | Owner kind | The owner's kind in the collection's own terms: tribal government, ANC, NHO. |
| 9 | `parent_enterprise_id` | Parent enterprise ID | The immediate parent enterprise's ID, where the parent is an enterprise rather than the Native entity itself. |
| 10 | `parent_name` | Parent | The immediate parent, which may itself be an enterprise. |
| 11 | `parent_is_hub` | Parent is the Native entity (yes or no) | Whether the immediate parent is the Native entity itself rather than another enterprise. |
| 12 | `hierarchy_level` | Level | How many steps below the owner the enterprise sits. |
| 13 | `relationship` | Relationship | How the enterprise relates to the owner: wholly owned, subsidiary, affiliated, unspecified. |
| 14 | `ownership_percent_stated` | Ownership share | The percentage owned, where a source states it. |
| 15 | `sector` (*rename to `industry`*) | Sector | The enterprise's sector. |
| 16 | `status` (*rename to `operating_status`*) | Status | Operating, dissolved, or unknown. |
| 17 | `city` | City | Where the enterprise is. |
| 18 | `state_province` | State | Its state or province. |
| 19 | `uei` | UEI | Its federal Unique Entity ID, where one is published. |
| 20 | `cage_code` | CAGE code | The enterprise's CAGE code, where known. |
| 21 | `in_federal_contracting` | Federal contractor | Whether the enterprise appears in federal contracting records (yes or no). |
| 22 | `first_observed_year` | First seen | The earliest year a source names the enterprise. |
| 23 | `last_observed_year` | Last seen | The latest. |
| 24 | `evidence_class` | Kind of evidence | What kind of source establishes the relationship (the owner's own list, an audited report, a resolver). |
| 25 | `evidence_human_reviewed` | Reviewed by a person | Whether a person reviewed the evidence (yes or no). |
| 26 | `n_distinct_sources` (*rename to `source_count`*) | Sources | How many distinct sources support the relationship. |
| 27 | `fpds_parent_corroboration` (*rename to `parent_corroboration`*) | Federal records agree | Whether the parent the enterprise declares in federal records agrees with this owner. |
| 28 | `fpds_declared_parent_name` | Parent declared in FPDS | The parent the enterprise declares in federal contracting records, kept as evidence beside Cedar's relationship. |
| 29 | `source_document` | Source document | The document, where the source is a file. |
| 30 | `source_edition_date` | Source date | The date of that source. |
| 31 | `source_url` | Source | Where the relationship is stated. |

### Natural Resource Revenue

Collection `natural-resources` · table `resource_revenue` · 11,305 rows in the full table · Cedar Press+ shelf

**One row is** One payment or distribution of natural-resource revenue (royalties, severance tax shares, reclamation distributions) to a Native entity.

**Where:** workspace dist/customer/natural-resources.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/natural-resources/resource_revenue.csv; built from federal and state revenue records.

**Columns a subscriber sees (37):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. |
| 2 | `recipient_entity_name` (*rename to `cedar_entity_name`*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. |
| 3 | `cedar_entity_type` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: recipient. |
| 5 | `resource_revenue_event_id` | Payment ID | Cedar's identifier for the payment. |
| 6 | `entity_attribution_status` (*rename to `attribution_status`*) | Attribution status | Whether the row is keyed to a Native entity, to an aggregate, or unresolved. A blank Cedar ID has a stated reason here. |
| 7 | `beneficiary_entity_id` | Beneficiary ID | The identifier of the beneficiary where it differs from the recipient. |
| 8 | `beneficiary_entity_name` | Beneficiary | Who the payment is for, where different from the recipient. |
| 9 | `beneficiary_note` | Beneficiary note | How the source describes the beneficiary. |
| 10 | `payer_entity_id` | Payer ID | The identifier of the payer. |
| 11 | `payer_entity_name` | Payer | Who made the payment (a federal office, a state). |
| 12 | `operator_entity_id` | Operator ID | The identifier of the related operator, where a source supports one. |
| 13 | `operator_entity_name` | Operator | The related operator's name, where a source supports one. |
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
| 24 | `measurement_status` | Actual or estimated | Whether the amount is an actual payment or an estimate. |
| 25 | `amount_usd` | Amount | Dollars paid. The sign column says what a negative means. |
| 26 | `amount_usd_real2025` | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. |
| 27 | `amount_sign_meaning` | What the sign means | How to read a negative amount (a correction, a recoupment). |
| 28 | `aggregation_level` | Aggregation level | Whether the amount is specific to the entity, a regional aggregate or a countrywide aggregate. An aggregate is never assigned to one tribe. |
| 29 | `land_status` | Land status | Trust or fee land, where the source states it. |
| 30 | `geography_note` | Place | What the source says about where the revenue arose. |
| 31 | `allocation_formula` | Allocation formula | The rule that determined the amount, where the source states it. |
| 32 | `allocation_formula_effective_start` | Allocation rule effective from | When the allocation rule took effect. |
| 33 | `allocation_formula_effective_end` | Allocation rule effective to | When the allocation rule ceased to apply. |
| 34 | `allocation_formula_source_url` | Formula source | Where that rule is published. |
| 35 | `source_system` | Source system | Which source system the record came from. |
| 36 | `source_record_id` | Source record ID | The record's identifier in that source. |
| 37 | `source_url` | Source | Where the payment is recorded. |

### Native Nonprofits

Collection `nonprofits` · table `np_orgs` · 12,764 rows in the full table · Cedar Press+ shelf

**One row is** One nonprofit organization in the IRS Business Master File that is Native-led or tribally controlled, with the Native entity it is linked to.

**Where:** workspace dist/customer/nonprofits.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/nonprofits/np_orgs.csv; built from the IRS Exempt Organizations Business Master File and Native-led directories.

**Columns a subscriber sees (27):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. |
| 2 | `cedar_spine_canonical_name` (*rename to `cedar_entity_name`*) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. |
| 3 | `cedar_spine_entity_class` (*rename to `cedar_entity_type`*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. |
| 4 | `cedar_entity_role` (*to add*) | Entity role | Why the entity is on this row: associated Native entity. |
| 5 | `EIN` (*rename to `ein`*) | EIN | The organization's Employer Identification Number. |
| 6 | `org_name` | Organization | The organization's name as the IRS records it. |
| 7 | `cedar_native_entity_class` (*rename to `org_entity_class`*) | Organization type | Whether the organization is itself a tribe, an ANC, a Native organization. |
| 8 | `classification_ruling` | Relationship to the entity | Whether the organization is tribally controlled, tribally affiliated, or unruled. |
| 9 | `disposition` (*rename to `inclusion_basis`*) | Inclusion basis | Why the organization is in Cedar: verified strictly, verified, or a candidate. |
| 10 | `city` | City | Its city. |
| 11 | `state` | State | The organization's state. |
| 12 | `ntee_code` | NTEE code | The IRS activity code for what the organization does. |
| 13 | `bmf_status` | IRS status code | The organization's status code in the Business Master File, defined in the dictionary. |
| 14 | `bmf_subsection` | Tax subsection | The 501(c) subsection (3 for charities). |
| 15 | `bmf_filing_req_cd` | Filing requirement code | Which return the IRS requires, as a code defined in the dictionary. |
| 16 | `bmf_foundation_cd` | Foundation code | The IRS foundation classification code, defined in the dictionary. |
| 17 | `bmf_irs_ruling_yyyymm` (*rename to `irs_ruling_month`*) | IRS ruling date | When the IRS recognized the organization (year and month). |
| 18 | `tier` (*rename to `filing_tier`*) | Filing tier | Which IRS return it files: full 990, 990-EZ or 990-N. |
| 19 | `bmf_tax_period` (*rename to `tax_period`*) | Latest tax period | The most recent tax period in the file. |
| 20 | `bmf_revenue_amt` | Revenue | Revenue in the latest return the IRS holds. |
| 21 | `bmf_income_amt` | Income | Income in that return. |
| 22 | `bmf_asset_amt` | Assets | Assets in that return. |
| 23 | `bmf_vintage_fetched` (*rename to `bmf_snapshot_date`*) | IRS file date | The date of the IRS file these figures come from. |
| 24 | `entity_match_method` (*rename to `attribution_method`*) | Attribution method | How the organization was linked to the Native entity. |
| 25 | `entity_tier` (*rename to `attribution_tier`*) | Match confidence | Cedar's confidence in the link to the entity: A is strongest. |
| 26 | `source_dataset` (*rename to `source_system`*) | Source system | The source: the IRS Exempt Organizations Business Master File. |
| 27 | `source_url` | Source | The IRS Business Master File. |

## Questions for the reviewer

- Is any kept column unnecessary for a subscriber, and is any dropped column (see the note) something a subscriber would miss?
- Are the labels the words a subscriber would use? Is any meaning wrong or unclear?
- Is the opening block the right first four columns for every dataset, and should the record's own identifier be the fifth everywhere?
- For datasets whose rows name several entities (Legislation, NAGPRA), is one row per record with `|`-separated entities better than one row per record and entity?
- Which datasets should carry inflation-adjusted amounts, and should the base year be a column or a note?

