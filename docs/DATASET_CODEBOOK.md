# Cedar Press datasets: the proposed structure of each, for review

Generated from `data/cedar/codebook.json` by `scripts/codebook-markdown.mjs`; edit the JSON, not this file. Written 2026-09-05.

## What this is

Cedar Press sells twelve collections. Each collection has one customer-facing dataset (its flagship table) and, in the workspace, a number of supporting tables. Today the flagship files carry between 37 and 78 columns, of which a third to two-thirds are pipeline bookkeeping: how a row was matched, when it was built, the basis of a derived value. This document proposes the structure each dataset should have when a customer downloads it: what one row is, and the columns to keep, each with a plain-English label and what it means. Columns not listed stay in the workspace. The per-table drop lists and the reasoning are in `docs/COLUMN_ORDER_NOTE_FOR_THE_TERMINAL_2026-09-05.md`.

Three rules apply to every dataset:

1. **The Cedar identity block comes first**: `cedar_uid` (the entity's permanent ID), `canonical_name` (its name as Cedar's register spells it), `entity_class` (which of Cedar's eighteen classes it is). These three are the join key across collections. Where a table lacks one today it is marked *to add*; where it carries the same thing under another name, the rename is shown.
2. **One row is one thing**, stated at the top of each dataset; a table whose rows name several entities carries them separated by `|`.
3. **Every amount says what it is** (an obligation, an announced value, a reported spend) and is never summed across datasets; every row cites a source.

Where the data lives: the full tables are built in the Cedar data workspace by `code/1135_full_dataset_review_bundle.py` into `dist/review/spreadsheets/<collection>/<table>.csv` (6.2 GB in all, not in the website repository); ten-row samples of each are copied to the website at `public/data/cedar/samples/<collection>/<table>__10.csv` and served at `https://cedarpress.ai/data/cedar/samples/...`. The entity register is `data/spine/cedar_entity_names.csv` (1,916 entities, 18 classes).

Meanings below were read from the column names and ten rows of values and are to be confirmed against the build scripts; a meaning marked *(confirm)* is the least certain.

## The datasets

### Federal Funding to Indian Country

Collection `funding` · table `federal_funding_transactions` · 701,955 rows in the full table · Cedar Press shelf

**One row is** One federal assistance transaction (a grant, loan, direct payment or insurance action) reported on USAspending, linked to the Native entity that received it.

**Where:** workspace dist/customer/funding.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/funding/federal_funding_transactions.csv; built by code/1135_full_dataset_review_bundle.py from the USAspending assistance archive.

**Columns to keep (28):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is linked to. Join key across every collection. |
| 2 | `canonical_name` | Native entity | The entity's name as Cedar's register spells it, so one entity reads the same in every collection. |
| 3 | `entity_class` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village corporation, Native nonprofit, and so on). |
| 4 | `assistance_transaction_unique_key` | Transaction ID | USAspending's unique key for this transaction. Cite it to find the exact record. |
| 5 | `action_date` | Action date | The date the agency took this action. |
| 6 | `fiscal_year` | Fiscal year | The federal fiscal year of the action (October to September), which is what USAspending reports and what the year filter uses. |
| 7 | `fy_partial_flag` | Partial fiscal year | Whether this row falls in a fiscal year the source had not finished reporting when Cedar pulled it (yes or no). Do not compare a partial year to a complete one. |
| 8 | `obligated_usd` | Amount obligated | Dollars obligated by this transaction. Negative values are de-obligations, kept as recorded. |
| 9 | `obligated_usd_real2025` | Amount in 2025 dollars | The same amount adjusted for inflation to 2025 dollars. |
| 10 | `assistance_type_description` | Assistance type | What kind of assistance it is: formula grant, project grant, direct payment, loan, insurance. |
| 11 | `cfda` | Program number | The Assistance Listing (CFDA) number of the federal program. |
| 12 | `cfda_title` | Program | The federal program's name. |
| 13 | `awarding_agency_name` | Agency | The department that made the award. |
| 14 | `awarding_sub_agency_name` | Office | The office within the department. |
| 15 | `recipient_name` | Recipient as recorded | The recipient's name as the award records it, before Cedar resolved it to the entity. |
| 16 | `recipient_uei` | Recipient UEI | The recipient's federal Unique Entity ID. |
| 17 | `recipient_city_name` | Recipient city | City of the recipient's address on the award. |
| 18 | `recipient_state_code` | Recipient state | State of the recipient's address on the award. |
| 19 | `business_types_description` | Recipient type as recorded | How USAspending classifies the recipient (for example, federally recognized tribal government). |
| 20 | `face_value_of_loan` | Loan face value | For loans, the face value of this loan; zero for grants. |
| 21 | `total_face_value_of_loan` | Award loan face value | For loans, the face value of the whole award to date. |
| 22 | `award_id_fain` | Award number | The award's Federal Award Identification Number; several transactions can share one. |
| 23 | `assistance_award_unique_key` | Award ID | USAspending's key for the whole award; the source link is built from it. |
| 24 | `attribution_method` | How the entity was matched | How Cedar linked this recipient to the entity (for example, an exact UEI match). |
| 25 | `confidence_tier` | Match confidence | Cedar's confidence in the link: A is strongest. |
| 26 | `attributed_flag` | Attributed to the entity | Whether Cedar attributes this transaction to the Native entity (yes) or keeps it in the file unattributed (no). Cedar's totals count attributed rows only. |
| 27 | `attribution_status` | Attribution status | How the attribution stands: attributed through the register, unattributed, or under review. |
| 28 | `source_url` (*to add*) | Source | The award's page on USAspending. |

### Federal Register

Collection `federal-register` · table `consultation_events` · 11,402 rows in the full table · Cedar Press shelf

**One row is** One tribal consultation event announced or reported in the Federal Register, one row per event and named participant (most events name no single tribe).

**Where:** workspace dist/customer/federal-register.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/federal-register/consultation_events.csv; built from Federal Register documents.

**Columns to keep (26):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is linked to. Join key across every collection. |
| 2 | `canonical_name` (*to add*) | Native entity | The entity's name as Cedar's register spells it, so one entity reads the same in every collection. |
| 3 | `entity_class` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village corporation, Native nonprofit, and so on). |
| 4 | `consultation_event_id` | Event ID | Cedar's identifier for the consultation event. |
| 5 | `notice_date` | Notice date | The date the Federal Register document was published. |
| 6 | `event_start_date` | Event start | When the consultation began, as the notice states it. |
| 7 | `event_end_date` | Event end | When it ended, where stated. |
| 8 | `consultation_type` | Kind of consultation | Whether this is a consultation session, a notice of consultation, or a consultation reported inside another document. |
| 9 | `document_role` | Document role | Whether the document announces a consultation or reports one that already happened. |
| 10 | `is_event_primary_row` | Counts as one consultation | One row per event carries yes; the rest are additional participants of the same event. Count consultations by this column, not by rows. |
| 11 | `n_participant_rows_for_event` | Participant rows for this event | How many rows this event has in the file. |
| 12 | `topic` | Topic | What the consultation was about, from the document's title. |
| 13 | `agency` | Agency | The department holding the consultation. |
| 14 | `sub_agency` | Office | The office within the department. |
| 15 | `program` | Program | The program or matter the consultation concerns, where the document names one. |
| 16 | `participant_name_as_published` | Participant as published | The tribe or organization named in the document, as it spells it. |
| 17 | `participant_role` | Participant role | How the document names the participant: consulted, invited, or not enumerated. |
| 18 | `location` | Location | Where the consultation was held. |
| 19 | `format` | Format | In person, virtual, teleconference, written comment, or a combination. |
| 20 | `comment_deadline` | Comment deadline | The date written comments were due, where stated. |
| 21 | `has_written_comments` | Written comments invited | Whether the document invites written comments (yes or no). |
| 22 | `federal_register_citation` | Citation | The Federal Register citation (volume FR page). |
| 23 | `fr_document_number` | Document number | The Federal Register document number. |
| 24 | `source_url` | Source | The document on federalregister.gov. |
| 25 | `source_quote` | Source passage | The sentence in the document this row was read from. |
| 26 | `confidence` | Match confidence | Cedar's confidence that the row reads the document correctly. |

### Legislation

Collection `legislation` · table `native_bills` · 3,069 rows in the full table · Cedar Press shelf

**One row is** One bill in Congress that concerns Native nations or organizations, with the entities it names.

**Where:** workspace dist/customer/legislation.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/legislation/native_bills.csv; built from the Congress.gov API.

**Columns to keep (20):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `entity_cedar_uids` | Cedar IDs | The Cedar IDs of every entity the bill names, separated by \|. |
| 2 | `entity_names` | Native entities | The names of those entities, in the same order. |
| 3 | `entity_classes` (*to add*) | Entity types | Their entity types, in the same order. |
| 4 | `bill_id` | Bill ID | Congress, chamber and number, for example 103-hr-2366. |
| 5 | `congress` | Congress | Which Congress (the 103rd, and so on). |
| 6 | `chamber` | Chamber | House or Senate. |
| 7 | `bill_type` | Bill type | hr, s, hjres and the like, as Congress.gov codes them. |
| 8 | `number` | Number | The bill's number in its chamber. |
| 9 | `title` | Title | The bill's title. |
| 10 | `policy_area` | Policy area | Congress.gov's policy area for the bill. |
| 11 | `bill_scope` | Scope | Whether the bill is specific to one tribe or general to Indian Country. |
| 12 | `introduced_date` | Introduced | The date the bill was introduced; the year filter uses this. |
| 13 | `sponsor` | Sponsor | The sponsoring member, with party and state. |
| 14 | `cosponsor_count` | Cosponsors | How many members cosponsored it. |
| 15 | `latest_action` | Latest action | The most recent action recorded on the bill. |
| 16 | `latest_action_date` | Latest action date | When that action happened. |
| 17 | `outcome` | Outcome | Where the bill ended: enacted, passed one chamber, died in committee. |
| 18 | `has_rollcall` | Had a roll-call vote | Whether any roll-call vote was taken (yes or no). |
| 19 | `companion_bill_id` | Companion bill | The matching bill in the other chamber, where one exists. |
| 20 | `source_url` (*to add*) | Source | The bill's page on congress.gov. |

### Indian Country Deals

Collection `deals` · table `deals_classified` · 1,073 rows in the full table · Cedar Press shelf

**One row is** One announced transaction or award involving a Native party: an acquisition, a financing, a grant, a partnership.

**Where:** workspace dist/customer/deals.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/deals/deals_classified.csv; assembled from announcements, filings and agency award lists.

**Columns to keep (27):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is linked to. Join key across every collection. |
| 2 | `native_party_canonical_name` (*rename to `canonical_name`*) | Native entity | The entity's name as Cedar's register spells it, so one entity reads the same in every collection. |
| 3 | `entity_class` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village corporation, Native nonprofit, and so on). |
| 4 | `Deal_ID` | Deal ID | Cedar's identifier for the deal. |
| 5 | `Event_Date` | Date | When the deal happened or was announced. |
| 6 | `Event_Date_precision` | Date precision | Whether the date is known to the day, the month or the year. |
| 7 | `Deal_Title` | Title | A one-line description of the deal. |
| 8 | `Native_Party` | Native party as published | The Native party's name as the source gives it. |
| 9 | `Native_Party_Type` | Native party type as published | How the source describes the Native party. |
| 10 | `native_party_role` | Native party's role | Acquirer, grantee, borrower, partner, seller. |
| 11 | `Counterparty_or_Funder` | Counterparty or funder | The other side of the deal. |
| 12 | `Deal_Category` | Category | Acquisition, grant or public financing, joint venture, and so on. |
| 13 | `Industry` | Industry | The industry the deal is in. |
| 14 | `Event_Type` | Event | What kind of event this row records (an acquisition of a 90% interest, an award). |
| 15 | `Status` | Status | Completed, announced, awarded, pending. |
| 16 | `Announced_Value_USD` | Announced value | The dollar value announced, where one was. |
| 17 | `Value_Type` | What the value is | What the announced figure represents (consideration paid, grant amount, project cost). |
| 18 | `Project_Total_Value_USD` | Project total | The total project value, where larger than the announced value. |
| 19 | `State` | State | The state the deal is located in. |
| 20 | `Location` | Location | The place, as the source gives it. |
| 21 | `Description` | Description | A longer description of the deal. |
| 22 | `Native_Connection` | Native connection | Why this deal is in the collection: how the Native party is connected. |
| 23 | `Source_1` | Source | The primary source document or page. |
| 24 | `Source_1_Type` | Source type | What kind of document the primary source is. |
| 25 | `Source_2` | Second source | A second source, where one was found. |
| 26 | `Verification_Status` | Verification | Whether the deal was verified against a primary source. |
| 27 | `Confidence` | Confidence | Cedar's confidence in the record: high, medium, low. |

### NAGPRA

Collection `nagpra` · table `nagpra_notices` · 6,792 rows in the full table · Cedar Press shelf

**One row is** One NAGPRA notice in the Federal Register (a notice of inventory completion or intent to repatriate), with the institution holding the remains or objects and the Native entities the notice names.

**Where:** workspace dist/customer/nagpra.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/nagpra/nagpra_notices.csv; built from Federal Register NAGPRA notices.

**Columns to keep (42):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `affiliated_entity_ids` | Cedar IDs (culturally affiliated) | The Cedar IDs of the entities the notice finds culturally affiliated, separated by \|. |
| 2 | `affiliated_entity_names` (*to add*) | Native entities (culturally affiliated) | Their names, in the same order. |
| 3 | `affiliated_entity_classes` (*to add*) | Entity types | Their entity types, in the same order. |
| 4 | `n_affiliated_named` | Affiliated parties named | How many parties the notice names as culturally affiliated. |
| 5 | `n_affiliated_resolved` | Affiliated parties resolved | How many of those Cedar could resolve to a register entity. |
| 6 | `document_number` | Document number | The Federal Register document number. |
| 7 | `publication_date` | Published | The date the notice was published. |
| 8 | `notice_type` | Notice type | Inventory completion, intent to repatriate, or correction. |
| 9 | `statute_stage` | Statute stage | Which stage of NAGPRA the notice is made under. |
| 10 | `is_correction` | Correction | Whether this notice corrects an earlier one (yes or no). |
| 11 | `title` | Title | The notice's title. |
| 12 | `institution_name` | Institution | The museum, university or agency holding the remains or objects. |
| 13 | `institution_city` | Institution city | Where the institution is. |
| 14 | `institution_state` | Institution state | Its state. |
| 15 | `institution_type_derived` | Institution type | Museum, university, federal agency, and so on. |
| 16 | `mni_total_stated` | Individuals | The minimum number of individuals the notice states. |
| 17 | `n_associated_funerary_objects_stated` | Associated funerary objects | Count stated in the notice. |
| 18 | `n_unassociated_funerary_objects_stated` | Unassociated funerary objects | Count stated in the notice. |
| 19 | `n_sacred_objects_stated` | Sacred objects | Count stated in the notice. |
| 20 | `n_objects_of_cultural_patrimony_stated` | Objects of cultural patrimony | Count stated in the notice. |
| 21 | `removal_counties` | Removal counties | Where the remains or objects were removed from. |
| 22 | `removal_states` | Removal states | The states of those places. |
| 23 | `consulted_entity_ids` | Cedar IDs (consulted) | Entities the notice says were consulted. |
| 24 | `n_consulted_named` | Consulted parties named | How many parties the notice names as consulted. |
| 25 | `n_consulted_resolved` | Consulted parties resolved | How many of those Cedar could resolve to a register entity. The gap is real uncertainty, not an omission. |
| 26 | `repatriation_recipient_entity_ids` | Cedar IDs (repatriation recipient) | Entities the notice names to receive the repatriation. |
| 27 | `n_repatriation_recipient_named` | Recipients named | How many recipients the notice names. |
| 28 | `n_repatriation_recipient_resolved` | Recipients resolved | How many of those Cedar could resolve. |
| 29 | `disposition_priority_entity_ids` | Cedar IDs (disposition priority) | Entities with priority for disposition, where stated. |
| 30 | `n_disposition_priority_named` | Priority parties named | How many parties the notice names with disposition priority. |
| 31 | `n_disposition_priority_resolved` | Priority parties resolved | How many of those Cedar could resolve. |
| 32 | `aboriginal_land_entity_ids` | Cedar IDs (aboriginal land) | Entities on whose aboriginal land the removal site lies, where stated. |
| 33 | `n_aboriginal_land_named` | Aboriginal-land parties named | How many parties the notice names for aboriginal land. |
| 34 | `n_aboriginal_land_resolved` | Aboriginal-land parties resolved | How many of those Cedar could resolve. |
| 35 | `n_parties_named` | Parties named in all | All parties the notice names, across roles. |
| 36 | `n_entities_resolved` | Entities resolved in all | How many distinct register entities those resolve to. |
| 37 | `response_deadline_date` | Response deadline | The date by which other claimants must respond. |
| 38 | `culturally_unidentifiable` | Culturally unidentifiable | Whether the remains are determined culturally unidentifiable (yes or no). |
| 39 | `lineal_descendant_determination` | Lineal descendant found | Whether a lineal descendant was determined (yes or no). |
| 40 | `agency_names` | Publishing agency | The agency that published the notice. |
| 41 | `source_url` | Source | The notice on federalregister.gov. |
| 42 | `pdf_url` | PDF | The notice as published, in PDF. |

### Native Federal Advocacy & Engagement

Collection `lobbying` · table `native_entity_lobbying_disclosures` · 27,825 rows in the full table · Cedar Press shelf

**One row is** One federal lobbying filing under the Lobbying Disclosure Act in which the client is a Native entity, one row per filing (amended filings appear once, as the current version).

**Where:** workspace dist/customer/lobbying.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/lobbying/native_entity_lobbying_disclosures.csv; built from the Senate LDA filings database.

**Columns to keep (26):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is linked to. Join key across every collection. |
| 2 | `canonical_name` | Native entity | The entity's name as Cedar's register spells it, so one entity reads the same in every collection. |
| 3 | `entity_type` (*rename to `entity_class`*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village corporation, Native nonprofit, and so on). |
| 4 | `filing_uuid` | Filing ID | The filing's identifier in the Senate LDA database. |
| 5 | `filing_year` | Filing year | The year the filing covers. |
| 6 | `filing_period` | Period | Which reporting period of the year. |
| 7 | `filing_type_display` | Filing type | Registration, quarterly or year-end report, amendment, termination. |
| 8 | `dt_posted` | Posted | When the filing was posted. |
| 9 | `client_name` | Client | The client as the filing names it (the Native entity, in its own spelling). |
| 10 | `client_state` | Client state | The client's state. |
| 11 | `registrant_name` | Registrant | The lobbying firm or, for a self-filer, the client itself. |
| 12 | `registrant_state` | Registrant state | The registrant's state. |
| 13 | `self_filed` | Self-filed | Whether the client filed for itself rather than through a firm (yes or no). |
| 14 | `income_usd` | Income reported | What the registrant reported receiving from the client this period. |
| 15 | `expenses_usd` | Expenses reported | What a self-filer reported spending this period. |
| 16 | `spend_usd` | Reported spend | Whichever of the two the filing reports; the basis column says which. |
| 17 | `spend_basis` | Basis of spend | Income, expenses, or none reported. |
| 18 | `lobbying_issues_codes` | Issue codes | The LDA issue area codes on the filing. |
| 19 | `specific_issues_text` | Specific issues | What the filing says was lobbied on. |
| 20 | `government_entities` | Government entities contacted | Agencies and chambers the filing lists, separated by \|. |
| 21 | `supersession_status` | Version status | Whether a later amendment replaces this filing. |
| 22 | `superseded_by_filing_uuid` | Replaced by | The filing that replaces this one, where one does. |
| 23 | `attribution_withdrawn` | Attribution withdrawn | Whether Cedar withdrew its link between this filing and the entity after review (yes or no). A withdrawn filing stays in the file; its spend is not counted as the entity's. |
| 24 | `attribution_withdrawn_reason` | Why withdrawn | The reason recorded for the withdrawal. |
| 25 | `filing_url` | Source | The filing on lda.senate.gov. |
| 26 | `match_confidence` | Match confidence | Cedar's confidence that the client is this entity. |

### Native Federal Contractors

Collection `contractors` · table `prime_contracts` · 1,217,768 rows in the full table · Cedar Press+ shelf

**One row is** One federal contract transaction (an award or a modification) to a firm owned by a Native entity, as reported to FPDS and published on USAspending.

**Where:** workspace dist/customer/contractors.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/contractors/prime_contracts.csv; built from the USAspending contract archive.

**Columns to keep (34):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is linked to. Join key across every collection. |
| 2 | `canonical_name` | Native entity | The entity's name as Cedar's register spells it, so one entity reads the same in every collection. |
| 3 | `entity_class` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village corporation, Native nonprofit, and so on). |
| 4 | `contract_transaction_unique_key` | Transaction ID | USAspending's key for this transaction. |
| 5 | `action_date` | Action date | The date of this award or modification. |
| 6 | `fiscal_year` | Fiscal year | The federal fiscal year of the action. |
| 7 | `total_obligations` | Amount obligated | Dollars obligated by this transaction. Sum these, never the award value. |
| 8 | `total_obligations_real2025` | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. |
| 9 | `total_award_value` | Award value to date | The whole award's value as restated on this row. Cumulative: never add it across rows. |
| 10 | `awardee_name` | Awardee | The contractor as the award names it. |
| 11 | `awardee_uei` | Awardee UEI | The contractor's federal Unique Entity ID. |
| 12 | `cage_code` | Awardee CAGE | The contractor's CAGE code, the identifier that persists across the DUNS-to-UEI change; masked on rows the publication rule withholds. |
| 13 | `parent_name` | Awardee's parent | The contractor's parent as the award records it. |
| 14 | `contract_number` | Contract number | The contract or order number. |
| 15 | `parent_contract_number` | Parent contract | The parent contract or vehicle, for orders. |
| 16 | `contract_award_unique_key` | Award ID | USAspending's key for the whole award; the source link is built from it. |
| 17 | `funding_agency` | Funding agency | The agency paying for the work. |
| 18 | `award_type` | Award type | Delivery order, BPA call, definitive contract, and so on. |
| 19 | `naics_code` | NAICS | The industry code of the work. |
| 20 | `naics_description` | Industry | What that code means. |
| 21 | `product_or_service_code_description` | Product or service | What was bought. |
| 22 | `award_base_description` | Description | The award's own description of the work. |
| 23 | `setaside` | Set-aside | The set-aside the award was made under, if any. |
| 24 | `reported_8a` | 8(a) reported | Whether the award reports the 8(a) program (yes or no). |
| 25 | `reported_native_preference` | Native preference reported | Whether the award reports a Native preference (yes or no). |
| 26 | `extent_competed_normalized` | Competition | How the award was competed. |
| 27 | `place_of_perform_city` | Place of performance | City where the work is performed. |
| 28 | `place_of_perform_state` | Place of performance state | Its state. |
| 29 | `recipient_city_name` | Awardee city | City of the awardee's address. |
| 30 | `recipient_state_code` | Awardee state | Its state. |
| 31 | `owner_attribution_status` | Ownership at the time | Whether the entity's ownership of the awardee was confirmed as of the transaction. |
| 32 | `attribution_method` | How the entity was matched | How Cedar linked the awardee to its Native owner. |
| 33 | `confidence_tier` | Match confidence | Cedar's confidence in the link: A is strongest. |
| 34 | `source_url` (*to add*) | Source | The award's page on USAspending. |

### Native Subcontracting

Collection `subcontracting` · table `subawards` · 89,809 rows in the full table · Cedar Press+ shelf

**One row is** One federal subcontract reported through FSRS where the prime, the subcontractor or both are owned by a Native entity.

**Where:** workspace dist/customer/subcontracting.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/subcontracting/subawards.csv; built from the USAspending FSRS subaward pull.

**Columns to keep (32):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is linked to. Join key across every collection. |
| 2 | `canonical_name` (*to add*) | Native entity | The entity's name as Cedar's register spells it, so one entity reads the same in every collection. |
| 3 | `entity_class` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village corporation, Native nonprofit, and so on). |
| 4 | `direction` | Which side is Native | Whether the prime, the sub, or both sides are Native-owned. |
| 5 | `prime_cedar_uid` | Prime's Cedar ID | The Native entity owning the prime contractor, where one does. |
| 6 | `sub_cedar_uid` | Subcontractor's Cedar ID | The Native entity owning the subcontractor, where one does. |
| 7 | `subaward_source_record_id` | Subaward ID | The subaward report's identifier. |
| 8 | `subaward_date` | Subaward date | The date of the subaward. |
| 9 | `fiscal_year` | Fiscal year | The federal fiscal year of the subaward. |
| 10 | `subaward_amount` | Subaward amount | Dollars of the subaward. |
| 11 | `subaward_amount_real2025` | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. |
| 12 | `duplicate_status` | Duplicate status | Whether this row is the primary filing or a duplicate of one. Sum primaries only. |
| 13 | `subaward_exceeds_prime_flag` | Exceeds the prime award | Whether the subaward amount exceeds its prime award (yes or no). A real filing, kept in the file, but never added into totals. |
| 14 | `action_date_precedes_ffata_flag` | Date before FFATA | Whether the reported date precedes the reporting law itself (yes or no), a known filer anomaly; do not treat such a date as when the work happened. |
| 15 | `description` | Description | What the subcontract is for, as reported. |
| 16 | `sub_name` | Subcontractor | The subcontractor as reported. |
| 17 | `sub_uei` | Subcontractor UEI | Its Unique Entity ID. |
| 18 | `sub_cage` | Subcontractor CAGE | Its CAGE code, where reported. |
| 19 | `sub_state` | Subcontractor state | Its state. |
| 20 | `sub_parent_name` | Subcontractor's parent | Its parent as reported. |
| 21 | `sub_business_types` | Subcontractor business types | The business types it reports (for example, Alaska Native Corporation owned). |
| 22 | `prime_name` | Prime contractor | The prime as reported. |
| 23 | `prime_uei` | Prime UEI | Its Unique Entity ID. |
| 24 | `prime_cage` | Prime CAGE | Its CAGE code, where reported. |
| 25 | `prime_parent_name` | Prime's parent | Its parent as reported. |
| 26 | `prime_award_id` | Prime award number | The prime contract's number. |
| 27 | `prime_award_amount` | Prime award amount | The prime contract's value. |
| 28 | `prime_top_awarding_agency` | Agency | The department that awarded the prime contract. |
| 29 | `prime_awarding_sub_agency` | Office | The office within it. |
| 30 | `naics` | NAICS | The industry code. |
| 31 | `naics_title` | Industry | What that code means. |
| 32 | `source_url` | Source | The prime award's page on USAspending. |

### Native-Owned Businesses

Collection `owned` · table `native_owned_businesses` · 4,273 rows in the full table · Cedar Press+ shelf

**One row is** One business owned by a Native entity, in the register of such businesses.

**Where:** workspace dist/customer/owned.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/native-owned-businesses/native_owned_businesses.csv. NOT AUDITED: the sample is not in the repository yet; run scripts/import_cedar_manifest.py --audit after adding it.

**Columns to keep (3):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is linked to. Join key across every collection. |
| 2 | `canonical_name` | Native entity | The entity's name as Cedar's register spells it, so one entity reads the same in every collection. |
| 3 | `entity_class` | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village corporation, Native nonprofit, and so on). |

### Native Enterprises

Collection `nest` · table `nest_enterprises` · 5,820 rows in the full table · Cedar Press+ shelf

**One row is** One enterprise (a subsidiary, a joint venture, an affiliate) with the Native entity that owns or is affiliated with it and how.

**Where:** workspace dist/customer/nest.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/nest/nest_enterprises.csv; built from owners' own subsidiary listings, annual reports and federal identifier records.

**Columns to keep (25):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is linked to. Join key across every collection. |
| 2 | `owner_hub_name` (*rename to `canonical_name`*) | Native entity | The entity's name as Cedar's register spells it, so one entity reads the same in every collection. |
| 3 | `owner_hub_entity_class` (*rename to `entity_class`*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village corporation, Native nonprofit, and so on). |
| 4 | `enterprise_id` | Enterprise ID | Cedar's identifier for the enterprise. |
| 5 | `enterprise_name` | Enterprise | The enterprise's name. |
| 6 | `name_variants_observed` | Also seen as | Other spellings of the name in the sources, separated by \|. |
| 7 | `relationship` | Relationship | How the enterprise relates to the owner: wholly owned, subsidiary, affiliated, unspecified. |
| 8 | `relation_class` | Ownership or affiliation | Whether the relationship is ownership or only affiliation. Dollars roll up only through ownership. |
| 9 | `parent_name` | Parent | The immediate parent, which may itself be an enterprise. |
| 10 | `hierarchy_level` | Level | How many steps below the owner the enterprise sits. |
| 11 | `ownership_percent_stated` | Ownership share | The percentage owned, where a source states it. |
| 12 | `sector` | Sector | The enterprise's sector. |
| 13 | `status` | Status | Operating, dissolved, or unknown. |
| 14 | `city` | City | Where the enterprise is. |
| 15 | `state_province` | State | Its state or province. |
| 16 | `uei` | UEI | Its federal Unique Entity ID, where one is published. |
| 17 | `in_federal_contracting` | Federal contractor | Whether the enterprise appears in federal contracting records (yes or no). |
| 18 | `first_observed_year` | First seen | The earliest year a source names the enterprise. |
| 19 | `last_observed_year` | Last seen | The latest. |
| 20 | `evidence_class` | Kind of evidence | What kind of source establishes the relationship (the owner's own list, an audited report, a resolver). |
| 21 | `evidence_human_reviewed` | Reviewed by a person | Whether a person reviewed the evidence (yes or no). |
| 22 | `source_url` | Source | Where the relationship is stated. |
| 23 | `source_document` | Source document | The document, where the source is a file. |
| 24 | `source_edition_date` | Source date | The date of that source. |
| 25 | `fpds_parent_corroboration` | Federal records agree | Whether the parent the enterprise declares in federal records agrees with this owner. |

### Natural Resource Revenue

Collection `natural-resources` · table `resource_revenue` · 11,305 rows in the full table · Cedar Press+ shelf

**One row is** One payment or distribution of natural-resource revenue (royalties, severance tax shares, reclamation distributions) to a Native entity.

**Where:** workspace dist/customer/natural-resources.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/natural-resources/resource_revenue.csv; built from federal and state revenue records.

**Columns to keep (25):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is linked to. Join key across every collection. |
| 2 | `recipient_entity_name` (*rename to `canonical_name`*) | Native entity | The entity's name as Cedar's register spells it, so one entity reads the same in every collection. |
| 3 | `entity_class` (*to add*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village corporation, Native nonprofit, and so on). |
| 4 | `resource_revenue_event_id` | Payment ID | Cedar's identifier for the payment. |
| 5 | `payment_date` | Payment date | When the payment was made. |
| 6 | `period_type` | Period covered | Whether the payment covers a fiscal year, a month, or is dated only by payment. |
| 7 | `period_start` | Period start | Start of the period the payment covers, where stated. |
| 8 | `period_end` | Period end | End of that period. |
| 9 | `revenue_type` | Revenue type | Royalty, severance tax share, reclamation fee distribution, and so on. |
| 10 | `resource_type` | Resource | Oil and gas, coal, timber, minerals. |
| 11 | `commodity` | Commodity | The commodity, as the source names it. |
| 12 | `related_asset_ids` | Related assets | The wells, tracts or leases the payment relates to, where a source names them; empty today and kept for when one does. |
| 13 | `amount_usd` | Amount | Dollars paid. The sign column says what a negative means. |
| 14 | `amount_usd_real2025` | Amount in 2025 dollars | The same amount adjusted to 2025 dollars. |
| 15 | `amount_sign_meaning` | What the sign means | How to read a negative amount (a correction, a recoupment). |
| 16 | `measurement_status` | Actual or estimated | Whether the amount is an actual payment or an estimate. |
| 17 | `beneficiary_entity_name` | Beneficiary | Who the payment is for, where different from the recipient. |
| 18 | `beneficiary_note` | Beneficiary note | How the source describes the beneficiary. |
| 19 | `payer_entity_name` | Payer | Who made the payment (a federal office, a state). |
| 20 | `land_status` | Land status | Trust or fee land, where the source states it. |
| 21 | `allocation_formula` | Allocation formula | The rule that determined the amount, where the source states it. |
| 22 | `allocation_formula_source_url` | Formula source | Where that rule is published. |
| 23 | `geography_note` | Place | What the source says about where the revenue arose. |
| 24 | `confidence` | Confidence | Cedar's confidence in the record: A is strongest. |
| 25 | `source_url` | Source | Where the payment is recorded. |

### Native Nonprofits

Collection `nonprofits` · table `np_orgs` · 12,764 rows in the full table · Cedar Press+ shelf

**One row is** One nonprofit organization in the IRS Business Master File that is Native-led or tribally controlled, with the Native entity it is linked to.

**Where:** workspace dist/customer/nonprofits.csv (the customer file, written by code/1137_customer_dataset_combine.py); the review copy is dist/review/spreadsheets/nonprofits/np_orgs.csv; built from the IRS Exempt Organizations Business Master File and Native-led directories.

**Columns to keep (20):**

| # | Column | Label | Meaning |
|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is linked to. Join key across every collection. |
| 2 | `cedar_spine_canonical_name` (*rename to `canonical_name`*) | Native entity | The entity's name as Cedar's register spells it, so one entity reads the same in every collection. |
| 3 | `cedar_spine_entity_class` (*rename to `entity_class`*) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village corporation, Native nonprofit, and so on). |
| 4 | `EIN` | EIN | The organization's Employer Identification Number. |
| 5 | `org_name` | Organization | The organization's name as the IRS records it. |
| 6 | `classification_ruling` | Relationship to the entity | Whether the organization is tribally controlled, tribally affiliated, or unruled. |
| 7 | `cedar_native_entity_class` | Organization type | Whether the organization is itself a tribe, an ANC, a Native organization. |
| 8 | `state` | State | The organization's state. |
| 9 | `city` | City | Its city. |
| 10 | `ntee_code` | NTEE code | The IRS activity code for what the organization does. |
| 11 | `tier` | Filing tier | Which IRS return it files: full 990, 990-EZ or 990-N. |
| 12 | `bmf_subsection` | Tax subsection | The 501(c) subsection (3 for charities). |
| 13 | `bmf_irs_ruling_yyyymm` | IRS ruling date | When the IRS recognized the organization (year and month). |
| 14 | `bmf_tax_period` | Latest tax period | The most recent tax period in the file. |
| 15 | `bmf_revenue_amt` | Revenue | Revenue in the latest return the IRS holds. |
| 16 | `bmf_asset_amt` | Assets | Assets in that return. |
| 17 | `bmf_income_amt` | Income | Income in that return. |
| 18 | `bmf_vintage_fetched` | IRS file date | The date of the IRS file these figures come from. |
| 19 | `entity_tier` | Match confidence | Cedar's confidence in the link to the entity: A is strongest. |
| 20 | `source_url` | Source | The IRS Business Master File. |

## Questions for the reviewer

- Is any kept column unnecessary for a subscriber, and is any dropped column (see the note) something a subscriber would miss?
- Are the labels the words a subscriber would use? Is any meaning wrong or unclear?
- Is the identity block the right first three columns for every dataset, and should the record's own identifier be the fourth everywhere?
- For datasets whose rows name several entities (Legislation, NAGPRA), is one row per record with `|`-separated entities better than one row per record and entity?
- Which datasets should carry inflation-adjusted amounts, and should the base year be a column or a note?

