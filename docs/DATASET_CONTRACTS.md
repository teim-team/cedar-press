# Dataset contracts - generated, do not hand-edit

*Generated 2026-09-02 by `code/512_build_dataset_contracts.py` (mission Phase 1). Regenerate rather than edit; `verify` exits 1 when the world breaks a contract, and 62 gates on it.*

**13 collections, 266 tables claimed, 7 orphaned shippable tables, 12 violations.**

**Grain: 218 of 225 shippable tables declare and VALIDATE a row grain, a primary key and a join cardinality; 7 do not.** A declared grain the data contradicts is a release-blocking violation, listed below. An unstated grain is ratcheted by `62_no_regression_check.contract_grain_unstated_shippable`: the count may only fall, and a new shippable table that lands without one fails the gate that day.

<details><summary>Shippable tables with an UNSTATED grain (7) - a buyer cannot join these safely</summary>

- `native_owned_businesses.bak_2026-09-02_010526.csv`
- `native_owned_businesses.bak_2026-09-02_010557.csv`
- `native_owned_businesses.csv`
- `prime_contracts.bak_2026-09-02_011205_pre772.csv`
- `regulations_gov_comments.csv`
- `regulations_gov_entity_coverage.csv`
- `sam_native_class_distributions.csv`

</details>

## VIOLATIONS - the contract the world currently breaks

- federal_funding_transactions.csv: declared join_cardinality names column(s) not in the header: ['tribe_id']
- federal_funding_tribe_year_panel.csv: declared primary_key names column(s) not in the header: ['tribe_id']
- federal_funding_tribe_year_panel.csv: declared join_cardinality names column(s) not in the header: ['tribe_id']
- federal_funding_tribe_year_panel.csv: declared primary_key ['fiscal_year'] is NOT unique - 5,480 duplicate row(s) of 5,496, e.g. ('2008',). A buyer joining on it gets rows we did not promise them.
- entity_aliases.csv: declared primary_key ['alias_id'] is NOT unique - 1 duplicate row(s) of 6,298, e.g. ('',). A buyer joining on it gets rows we did not promise them.
- ORPHAN shippable table: native_owned_businesses.bak_2026-09-02_010526.csv - registered in the codebook but claimed by NO collection
- ORPHAN shippable table: native_owned_businesses.bak_2026-09-02_010557.csv - registered in the codebook but claimed by NO collection
- ORPHAN shippable table: native_owned_businesses.csv - registered in the codebook but claimed by NO collection
- ORPHAN shippable table: prime_contracts.bak_2026-09-02_011205_pre772.csv - registered in the codebook but claimed by NO collection
- ORPHAN shippable table: regulations_gov_comments.csv - registered in the codebook but claimed by NO collection
- ORPHAN shippable table: regulations_gov_entity_coverage.csv - registered in the codebook but claimed by NO collection
- ORPHAN shippable table: sam_native_class_distributions.csv - registered in the codebook but claimed by NO collection

## Federal Funding to Indian Country  (`funding`, shelf: standard)

Rebuild: `py -3 code/build.py run funding --execute` — 16 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `bie_uio_dollars_by_entity.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `bie_uio_identifier_links.csv` | internal-by-decision | `tribe_id` `cedar_uid` `uei` `ein` | — | — |
| `faads_attribution_audit_sample.csv` | internal-by-decision | `tribe_id` `cedar_uid` | — | — |
| `faads_entity_attribution.csv` | shippable | `tribe_id` `cedar_uid` | `73_faads_name_attribution.py` | `710_faads_attribution_content_key.py` `791_faads_transaction_key_and_repoint.py` |
| `faads_identifier_coverage_by_agency_year.csv` | internal-by-decision | — | — | — |
| `faads_transactions.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `faads_transactions_all_agencies.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `federal_funding_rulings_from_dofile.csv` | unregistered | — | — | — |
| `federal_funding_transactions.csv` | shippable | `cedar_uid` | `24_funding_merge.py` | `115_pull_assistance_archive.py` `335_harmonize_assistance_seams_in_place.py` `336_correct_scheme_resolution_by_spine_membership.py` `503_identity.py` |
| `federal_funding_tribe_year_panel.csv` | shippable | `cedar_uid` | — | — |
| `federal_funding_year_comparison_2026-08-05.csv` | internal-by-decision | — | — | — |
| `funding_identifier_harvest.csv` | internal-by-decision | `cage_code` | — | — |
| `funding_identifier_netnew_ueis.csv` | shippable | — | — | — |
| `inflation_deflator.csv` | shippable | — | — | — |
| `native_passthrough.csv` | shippable | — | — | — |
| `native_passthrough_pairs.csv` | shippable | — | — | — |

Declared grain — validated against the file on every run:

- `bie_uio_dollars_by_entity.csv` — one row per BIE school or Urban Indian Organisation entity, with its dollars summed across sources
  - primary key: `tribe_id`  (validated unique)
  - join cardinality: `cedar_uid` → one row(s) per value (measured max 1), `tribe_id` → one row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `faads_entity_attribution.csv` — one row per FAADS transaction that was attributed to an entity - docs/FAADS_NAME_ATTRIBUTION_LOG.md
  - primary key: `faads_row_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 536), `tribe_id` → many row(s) per value (measured max 536)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `faads_transactions.csv` — one row per FY2001-2007 assistance TRANSACTION awarded by the Department of the Interior - an action on an award, not an award: one FAIN carries many transactions, including $0 modifications, and they are all real. This is an AGENCY filter, NOT a Native one: `tribe_id` is blank on all 60,661 rows and the $9,348,473,200 here is every Interior assistance recipient in the country, Native and not. It must never be quoted as money reaching Indian Country. These 60,661 rows are also carried VERBATIM into faads_transactions_all_agencies.csv, so the two files must never be added together. `obligated_usd` is additive at this grain
  - primary key: `assistance_transaction_unique_key`  (validated unique)
  - join cardinality: `assistance_transaction_unique_key` → one row(s) per value (measured max 1), `award_id_fain` → many row(s) per value (measured max 317)
  - declared by: workstream FAADS 2026-09-01: the key was restored from the seven full-column DOI seam zips by code/791_faads_transaction_key_and_repoint.py interior and confirmed unique on the FULL 60,661-row file (0 collisions, 0 blanks); re-measured by `py -3 code/791_faads_transaction_key_and_repoint.py measure`
- `faads_transactions_all_agencies.csv` — one row per PRE-2008 FEDERAL ASSISTANCE TRANSACTION - an action on an award, not an award: one FAIN carries many transactions including $0 modifications and they are all real. FY2001-2007, ten agencies, $1,830,639,317,707.66. THIS IS A NATIONAL SOURCE MIRROR AND NOT A NATIVE FILTER: `tribe_id` and `cedar_uid` are blank on every row and the recipients are every assistance recipient in the country, Native and not. It must never be quoted as money reaching Indian Country - the Native attribution for this table lives in `faads_entity_attribution.csv` (29,594 rows, all keyed). MONEY: `obligated_usd` IS additive at this grain. Two stacking hazards, both measured: `faads_transactions.csv` (60,661 rows) is the Interior slice of THIS file carried verbatim, so the two must never be added; and this file's FY2007 (774,755 rows) overlaps `federal_funding_transactions.csv`'s FY2007, where 98.9% of the modern table's FY2007 dollars sit on FAINs this file also carries - the identified seam is 11,063 rows and $2,165,856,968.60. NO PRIMARY KEY EXISTS AND NONE IS CLAIMED - see key_refused
  - primary key: —  (validated unique)
  - declared by: workstream SUBAWARD-FUNDING 2026-09-02: grain declared WITHOUT a primary key, with the refusal recorded in `key_refused` and re-checked against the file on every run of this script
- `federal_funding_transactions.csv` — one row per federal assistance award TRANSACTION, across the union of the assistance and archive pulls
  - primary key: `assistance_transaction_unique_key`  (**VALIDATION FAILED — see violations**)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 18574), `tribe_id` → many row(s) per value
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `federal_funding_tribe_year_panel.csv` — one row per (entity, federal fiscal year). A join on tribe_id alone fans out across years
  - primary key: `tribe_id` + `fiscal_year`  (**VALIDATION FAILED — see violations**)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 32), `tribe_id` → many row(s) per value
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `funding_identifier_netnew_ueis.csv` — one row per recipient UEI that the funding pull added and no other Cedar source had
  - primary key: `recipient_uei`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `inflation_deflator.csv` — one row per year of the GDP deflator series
  - primary key: `year`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `native_passthrough.csv` — one row per NATIVE-TO-NATIVE SUBAWARD FILING - the `direction == 'both_sides_native'` slice of subawards.csv, 1:1, with both legs resolved to spine entities. It is a PROJECTION of subawards.csv and NOT new money: adding this table to subawards.csv, or to prime_contracts.csv, counts the same federal dollar twice. It inherits its parent's grain exactly, so a row is one FILING and repeat monthly filings of one pass-through are separate rows. MONEY: `amount_usd` is additive ONLY where `amount_countable == 1`, which is the parent's two filters (`duplicate_status == 'primary'` AND `subaward_exceeds_prime_flag != 'yes'`) computed on the parent row; both source columns are now carried so a subscriber can reproduce or disagree with the filter instead of taking the flag on trust. `amount_countable` is a 0/1 FLAG and is not a money column
  - primary key: `source_dataset` + `subaward_source_record_id`  (validated unique)
  - join cardinality: `from_tribe_id` → many row(s) per value (measured max 371), `to_tribe_id` → many row(s) per value (measured max 376)
  - declared by: workstream SUBAWARD-FUNDING 2026-09-02: 81_build_passthrough_dataset.py now carries the parent's key plus `duplicate_status` and `subaward_exceeds_prime_flag` - the one-line fix GRAIN_WS4 named. Confirmed on the rebuilt 1,663-row file: 0 blank keys, 0 collisions, 0 byte-identical whole rows (was 116). Re-measure with `py -3 code/81_build_passthrough_dataset.py verify`
- `native_passthrough_pairs.csv` — one row per (paying entity, receiving entity) pair, rolled up across their subawards
  - primary key: `from_tribe_id` + `to_tribe_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json

## Federal Register  (`federal-register`, shelf: standard)

Rebuild: `py -3 code/build.py run federal-register --execute` — 27 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `consultation_agency_coverage.csv` | UNDOCUMENTED | — | — | — |
| `consultation_events.csv` | shippable | `tribe_id` `cedar_uid` | `96_build_consultation_events.py` | `503_identity.py` |
| `consultation_source_probe.csv` | internal-by-decision | — | — | — |
| `correspondence_foia_source_coverage.csv` | shippable | — | — | — |
| `federal_actions.csv` | shippable | — | `11_classify_federal_actions.py` | `22_apply_temporal_floor.py` |
| `federal_actions_entity_bridge.csv` | shippable | `tribe_id` `cedar_uid` | `70_key_unjoined_datasets.py` | `503_identity.py` |
| `federal_actions_raw.csv` | shippable | — | — | — |
| `fr_abstract_availability_year.csv` | shippable | — | — | — |
| `fr_consultation_by_agency.csv` | shippable | — | — | — |
| `fr_consultation_notices.csv` | shippable | — | — | — |
| `fr_consultation_referenced.csv` | shippable | — | — | — |
| `fr_consultation_year.csv` | shippable | — | — | — |
| `fr_content_classification.csv` | shippable | — | — | — |
| `fr_ex_parte_notices.csv` | shippable | — | — | — |
| `fr_ex_parte_parties.csv` | shippable | `cedar_uid` | `154_build_fr_ex_parte_notices.py` | `503_identity.py` |
| `fr_ex_parte_party_entity_links.csv` | shippable | `cedar_uid` | `154_build_fr_ex_parte_notices.py` | `503_identity.py` |
| `fr_recognized_entities.csv` | internal-by-decision | — | — | — |
| `fr_relevance_stratum_audit.csv` | internal-by-decision | — | — | — |
| `fr_relevance_tier_year.csv` | shippable | — | — | — |
| `fr_theme_year.csv` | shippable | — | — | — |
| `nepa_administrative_record_parties.csv` | shippable | `cedar_uid` | `134_build_nepa_eplanning.py` | `503_identity.py` |
| `nepa_eplanning_projects.csv` | shippable | — | — | — |
| `nepa_project_documents.csv` | shippable | — | — | — |
| `nepa_source_coverage.csv` | internal-by-decision | — | — | — |
| `section_106_consultation_events.csv` | shippable | `tribe_id` `cedar_uid` | `130_build_section_106_consultation.py` | `503_identity.py` |
| `section_106_project_parties.csv` | shippable | `cedar_uid` | `130_build_section_106_consultation.py` | `503_identity.py` |
| `section_106_source_coverage.csv` | shippable | — | — | — |

Declared grain — validated against the file on every run:

- `consultation_events.csv` — one row per (consultation event, participant as published). `consultation_event_id` alone is NOT unique - an event with several named participants has one row each, and 1,006 rows name no participant at all
  - primary key: `consultation_event_id` + `participant_name_as_published`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 170), `tribe_id` → many row(s) per value (measured max 170)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `correspondence_foia_source_coverage.csv` — one row per source URL checked for congressional-correspondence coverage. 17 rows repeat (agency, source, status, evidence) under a DIFFERENT url - one agency publishing several correspondence pages, not a duplicate: the url is the probe and the probe is the row
  - primary key: `url`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `federal_actions.csv` — one row per Federal Register document, classified
  - primary key: `document_number`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `federal_actions_entity_bridge.csv` — one row per (Federal Register document, entity named in it)
  - primary key: `document_number` + `tribe_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 165), `tribe_id` → many row(s) per value (measured max 165)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `federal_actions_raw.csv` — one row per Federal Register document as pulled, before classification
  - primary key: `document_number`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_abstract_availability_year.csv` — one row per publication year: how many FR documents that year carried an abstract
  - primary key: `publication_year`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_consultation_by_agency.csv` — one row per normalised department, counting its consultation notices. One row carries a blank department and is the unattributed bucket
  - primary key: `normalized_department`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_consultation_notices.csv` — one row per Federal Register notice carrying a consultation signal
  - primary key: `document_number`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_consultation_referenced.csv` — one row per Federal Register document that REFERENCES a consultation having been undertaken. 652 rows repeat (year, title, agency, basis) under a DIFFERENT document_number, because the Federal Register reissues an identically titled NAGPRA notice for different collections - each is its own document and none is a duplicate. COUNT DOCUMENTS, NOT DISTINCT TITLES
  - primary key: `document_number`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_consultation_year.csv` — one row per publication year of consultation counts. 5 rows carry an identical PAIR of counts to another year - two quiet years coinciding, not a repeated row
  - primary key: `publication_year`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_content_classification.csv` — one row per Federal Register document, with its relevance tier and themes
  - primary key: `document_number`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_ex_parte_notices.csv` — one row per Federal Register ex parte notice
  - primary key: `fr_ex_parte_notice_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_ex_parte_parties.csv` — one row per party named in a Federal Register ex parte notice
  - primary key: `fr_ex_parte_party_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_ex_parte_party_entity_links.csv` — one row per resolved link from an ex parte party to a Cedar entity, across TWO source tables - `source_dataset` says which, and the join key is (source_dataset, source_row_id), never source_row_id alone. All 9 links currently come from `ferc_ex_parte_parties.csv`; `fr_ex_parte_parties.csv` resolves 0 of its 112 parties, so a join from fr_ex_parte_parties returns NOTHING and that is the data, not a broken key
  - primary key: `link_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 2)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_relevance_tier_year.csv` — one row per (publication year, relevance tier)
  - primary key: `publication_year` + `relevance_tier`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_theme_year.csv` — one row per (publication year, theme)
  - primary key: `publication_year` + `theme`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nepa_administrative_record_parties.csv` — one row per (NEPA administrative record, party as published)
  - primary key: `party_id` + `party_name_as_published`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 5)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nepa_eplanning_projects.csv` — one row per NEPA ePlanning project
  - primary key: `nepa_number`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nepa_project_documents.csv` — one row per (NEPA project, document as named in the record)
  - primary key: `nepa_number` + `document_name_verbatim`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `section_106_consultation_events.csv` — one row per Section 106 consultation event
  - primary key: `consultation_event_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 15), `tribe_id` → many row(s) per value (measured max 15)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `section_106_project_parties.csv` — one row per party named in a Section 106 undertaking
  - primary key: `party_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `section_106_source_coverage.csv` — one row per source swept for Section 106 records, with what it yielded and what it could not
  - primary key: `source`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json

## Congressional Votes and Proposed Legislation  (`legislation`, shelf: standard)

Rebuild: `py -3 code/build.py run legislation --execute` — 13 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `bill_votes.csv` | shippable | — | `14_build_bills_votes.py` | `73_bills_votes_completion.py` `890_bill_votes_threshold_and_titles.py` |
| `bill_votes_entity_bridge.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `bill_votes_official_verification.csv` | shippable | — | — | — |
| `congressional_correspondence_log.csv` | internal-by-decision | `cedar_uid` | — | — |
| `congressional_correspondence_systems.csv` | shippable | — | — | — |
| `member_positions.csv` | shippable | — | — | — |
| `native_bill_outcomes.csv` | shippable | — | — | — |
| `native_bills.csv` | shippable | — | `14_build_bills_votes.py` | `35_entity_harvest.py` |
| `native_bills_entity_bridge.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `native_bills_entity_class.csv` | shippable | — | — | — |
| `native_bills_subject_sweep.csv` | shippable | — | — | — |
| `native_issue_litigation_coverage.csv` | internal-by-decision | — | — | — |
| `native_issue_litigation_positions.csv` | shippable | — | `139_build_litigation_positions.py` | `140_build_grantmaker_funding_flows.py` |

Declared grain — validated against the file on every run:

- `bill_votes.csv` — one row per roll-call vote on a Native-relevant bill
  - primary key: `vote_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `bill_votes_entity_bridge.csv` — one row per (roll-call vote, entity named in the bill)
  - primary key: `vote_id` + `tribe_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 10), `tribe_id` → many row(s) per value (measured max 10)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `bill_votes_official_verification.csv` — one row per roll call as pulled from the official record - docs/BILLS_VOTES_COMPLETION_LOG.md
  - primary key: `vote_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `congressional_correspondence_systems.csv` — one row per (correspondence system, quoted evidence for it). `system_id` alone repeats where several citations evidence one system
  - primary key: `system_id` + `verbatim_quote`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `member_positions.csv` — one row per (roll-call vote, member of Congress) - the member's cast position
  - primary key: `vote_id` + `bioguide_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `native_bill_outcomes.csv` — one row per bill, with its final disposition - docs/BILLS_VOTES_COMPLETION_LOG.md
  - primary key: `bill_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `native_bills.csv` — one row per Native-relevant bill
  - primary key: `bill_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `native_bills_entity_bridge.csv` — one row per (bill, entity named in it)
  - primary key: `bill_id` + `tribe_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 41), `tribe_id` → many row(s) per value (measured max 41)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `native_bills_entity_class.csv` — one row per (bill, class-match BASIS) where the bill names a class of Native entity rather than an entity. (bill_id, entity_class) is NOT unique - 34 collisions - because one class can be matched through more than one basis
  - primary key: `bill_id` + `class_match_basis`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `native_bills_subject_sweep.csv` — one row per BILL in the all_bill_intros corpus whose title, subjects or policy area matched a Native subject-family phrase. A SWEEP HIT IS NOT AN ADJUDICATED CLASSIFICATION - `sweep_basis` names the phrase and where it matched, and `already_in_native_bills` says whether the two-coder corpus had already reached the bill. The corpus repeats 595 bill ids byte-identically and each is now read once, so `bill_id` is unique here and a count of rows IS a count of bills. This table holds no money column
  - primary key: `bill_id`  (validated unique)
  - join cardinality: `subject_family` → many row(s) per value (measured max 2185)
  - declared by: workstream UPSTREAM 2026-09-01: the de-dupe was applied to the CORPUS in `73.stage_sweep`, not to this output - every one of the 595 corpus repeats is byte-identical to its first occurrence on all 18 columns, so nothing is lost by reading it once, and no Cedar row was deleted. Re-swept: 2,414 -> 2,409 rows with ZERO bill_ids leaving the table, literal duplicates 5 -> 0, key confirmed unique on the FULL file
- `native_issue_litigation_positions.csv` — one row per position taken by an organisation in one case at one stage
  - primary key: `position_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json

## Indian Country Deals  (`deals`, shelf: standard)

Rebuild: `py -3 code/build.py run deals --execute` — 19 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `deals_2000_2019_additions.csv` | shippable | — | — | — |
| `deals_2026_ytd_additions.csv` | shippable | — | — | — |
| `deals_anc_reports_additions.csv` | shippable | — | — | — |
| `deals_ancsa_portal_additions.csv` | shippable | — | `build_deals.py` | `build_deals2.py` |
| `deals_ancsa_portal_v2_additions.csv` | shippable | — | — | — |
| `deals_classified.csv` | shippable | `cedar_uid` | — | — |
| `deals_federal_awards_additions.csv` | shippable | — | — | — |
| `deals_historical_additions.csv` | shippable | — | — | — |
| `deals_party_attribution.csv` | internal-by-decision | `tribe_id` `cedar_uid` | — | — |
| `deals_party_attribution_agent.csv` | internal-by-decision | `tribe_id` `cedar_uid` `uei` `cage_code` | — | — |
| `deals_party_autoresolved.csv` | internal-by-decision | `tribe_id` `cedar_uid` | `57_autoresolve_deal_parties.py` | `154_extend_autoresolved_parties_additive.py` |
| `deals_party_matches.csv` | internal-by-decision | — | — | — |
| `deals_sec_2010_2017_additions.csv` | shippable | — | — | — |
| `deals_source_index.csv` | shippable | — | — | — |
| `deals_taxonomy.csv` | internal-by-decision | — | — | — |
| `deals_tribal_debt_additions.csv` | shippable | — | — | — |
| `ownership_events.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` | — | — |
| `seminole_bond_disclosures.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `tribal_resolution_financings.csv` | shippable | `cedar_uid` `entity_id` | — | — |

Declared grain — validated against the file on every run:

- `deals_2000_2019_additions.csv` — one row per deal event added by the 2000-2019 backfill
  - primary key: `Deal_ID`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `deals_2026_ytd_additions.csv` — one row per deal event added by the 2026 year-to-date pass - a STAGING SLICE, identical in schema and key to the eight sibling `deals_*_additions.csv` files. THE FILE IS EMPTY (0 rows, header only) because its contents were folded into `deals_classified.csv`, which is what happened to all nine slices: 790 of the 790 rows in the eight non-empty slices carry a `Deal_ID` the classified ledger already holds. NEVER SUM ANY ADDITIONS FILE ALONGSIDE `deals_classified.csv` - that is the largest double-counting path in the deals dataset, worth $22.67B against a $45.20B headline. All nine tables are individually safe to aggregate and NO TWO OF THEM ARE SAFE TOGETHER.
  - primary key: `Deal_ID`  (validated unique)
  - join cardinality: `Deal_ID` → one row(s) per value
  - declared by: workstream GRAIN-WS5 2026-09-01: declared from the writer and from the eight sibling slices, which share this file's schema and are all keyed on Deal_ID; the 790-of-790 fold-in was measured on the live files. Re-measured by code/731_ws5_grain_contractors_nonprofits_deals.py measure
- `deals_anc_reports_additions.csv` — one row per deal event added from ANC annual reports
  - primary key: `Deal_ID`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `deals_ancsa_portal_additions.csv` — one row per deal event added from the ANCSA portal
  - primary key: `Deal_ID`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `deals_ancsa_portal_v2_additions.csv` — one row per deal event added from the ANCSA portal, second pass
  - primary key: `Deal_ID`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `deals_classified.csv` — one row per classified deal event - the merged deals ledger
  - primary key: `Deal_ID`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 39)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `deals_federal_awards_additions.csv` — one row per deal event derived from a federal award
  - primary key: `Deal_ID`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `deals_historical_additions.csv` — one row per deal event added by the historical pass
  - primary key: `Deal_ID`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `deals_sec_2010_2017_additions.csv` — one row per deal event added from SEC filings 2010-2017
  - primary key: `Deal_ID`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `deals_source_index.csv` — one row per Native party named in the deals ledger, with the sources its deals were discovered through
  - primary key: `native_party`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `deals_tribal_debt_additions.csv` — one row per deal event added from the tribal-debt pass
  - primary key: `Deal_ID`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `ownership_events.csv` — one row per ownership-change event derived from the deals ledger
  - primary key: `event_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 12), `entity_id` → many row(s) per value (measured max 12), `tribe_id` → many row(s) per value (measured max 12)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `seminole_bond_disclosures.csv` — one row per bond disclosure document filed for the obligor
  - primary key: `disclosure_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 29), `tribe_id` → many row(s) per value (measured max 29)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `tribal_resolution_financings.csv` — one row per RETRIEVED DOCUMENT from one nation's legislative archive whose text names a financing authorisation - not one row per instrument and not one row per resolution. `instrument_number` is BLANK on the only row on disk, so the instrument key is absent, not merely unproven. A ROW PROVES AUTHORISATION AND NOTHING FURTHER: `financing_status` is AUTHORIZED on the whole table and the build's own ladder is AUTHORIZED -> NIGC_REVIEWED -> EXECUTION_UNCONFIRMED -> EXECUTED_CONFIRMED. A council resolution records that a governing body voted to PERMIT an officer to enter a transaction; it does not establish that the transaction was negotiated, executed or funded. `principal_amount_text` and `pledged_revenues_text` are FREE TEXT carrying whatever figures the quote held, are blank on the only row, and are NOT money columns - they may not be totalled at all. And `nigc_declination_cross_reference` exists precisely so a resolution and an NIGC review of ONE transaction are never counted as two: never sum this table with `nigc_declination_letters.csv`, `gaming_financing_events.csv` or `tribal_bond_issuances.csv`.
  - primary key: `entity_id` + `source_url` + `source_index_url` + `instrument_title`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 1), `entity_id` → many row(s) per value (measured max 1)
  - declared by: workstream GRAIN-WS5 2026-09-01: declared from the build log in code/149_build_tribal_resolution_financings.py, whose `doc_links` set de-duplicates on exactly (document_url, link_text, index_page) within one nation's loop - the same route GRAIN-WS3 declared admin_appeal_positions.csv by. Key confirmed unique with no blank component on the FULL 1-row file. Re-measured by code/731_ws5_grain_contractors_nonprofits_deals.py measure

## NAGPRA  (`nagpra`, shelf: standard)

Rebuild: `py -3 code/build.py run nagpra --execute` — 4 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `fr_nagpra_title_index.csv` | shippable | — | — | — |
| `fr_nagpra_title_index_year.csv` | shippable | — | — | — |
| `nagpra_notice_entity_bridge.csv` | shippable | `tribe_id` | `77_build_nagpra_dataset.py` | `503_identity.py` |
| `nagpra_notices.csv` | shippable | — | — | — |

Declared grain — validated against the file on every run:

- `fr_nagpra_title_index.csv` — one row per Federal Register document whose TITLE is a NAGPRA notice heading. A title-only index of the parent FR corpus, not the notice product: its regex omits 'notice of intended disposition', so it is NOT a superset of nagpra_notices.csv (168 notices are in the product and not here; 2 are here and not there, having no cached full text). Use nagpra_notices.csv for the notices and this only for corpus-level coverage over time - docs/datasets/nagpra.md
  - primary key: `document_number`  (validated unique)
  - join cardinality: `document_number` → one row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_nagpra_title_index_year.csv` — one row per publication year, aggregating fr_nagpra_title_index.csv. Counts DOCUMENTS, not ancestors and not repatriations - docs/datasets/nagpra.md
  - primary key: `publication_year`  (validated unique)
  - join cardinality: `publication_year` → one row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nagpra_notice_entity_bridge.csv` — one row per (notice, relationship, named party) - docs/NAGPRA_BUILD_LOG.md. (document_number, party) alone collides 12,800 times because one party can hold several relationships to one notice. `relationship` is a LEGAL FINDING and the values are not interchangeable: consulted (25 U.S.C. 3003-3004) is not culturally_affiliated, and filtering to one is mandatory before any count. `tribe_id` is blank wherever the resolver was not certain - 3,467 rows - and `resolve_method` says why (`ambiguous_containment:N:...` names every candidate it would not choose between)
  - primary key: `document_number` + `relationship` + `party_name_verbatim`  (validated unique)
  - join cardinality: `document_number` → many row(s) per value (measured max 183), `tribe_id` → many row(s) per value (measured max 900)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nagpra_notices.csv` — one row per NAGPRA notice, keyed on the Federal Register document number - docs/NAGPRA_BUILD_LOG.md. A correction notice is its own row (is_correction=1) and does not supersede the row it amends. The `*_entity_ids` columns are PIPE-DELIMITED LISTS, not join keys: join to entities through nagpra_notice_entity_bridge.csv. `mni_total_stated` is blank wherever the notice did not state one total, and must never be defaulted to 0
  - primary key: `document_number`  (validated unique)
  - join cardinality: `document_number` → one row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json

## Lobbying  (`lobbying`, shelf: standard)

Rebuild: `py -3 code/build.py run lobbying --execute` — 39 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `admin_appeal_decisions.csv` | shippable | — | — | — |
| `admin_appeal_parties.csv` | shippable | `cedar_uid` | — | — |
| `admin_appeal_positions.csv` | shippable | `cedar_uid` | — | — |
| `advocacy_passthrough.csv` | shippable | `cedar_uid` | — | — |
| `advocacy_passthrough_2026-08-07.csv` | internal-by-decision | `cedar_uid` | — | — |
| `agency_attention_vs_advocacy.csv` | shippable | — | — | — |
| `agency_attention_vs_advocacy_year.csv` | shippable | — | — | — |
| `earmarks.csv` | shippable | `cedar_uid` `entity_id` | — | — |
| `ferc_docket_filings.csv` | shippable | `cedar_uid` | `133_build_ferc_advocacy.py` | `168_link_adjudication_hubs.py` |
| `ferc_docket_parties.csv` | shippable | `cedar_uid` | — | — |
| `ferc_ex_parte_communications.csv` | shippable | `cedar_uid` | — | — |
| `ferc_ex_parte_parties.csv` | shippable | `cedar_uid` | `133_build_ferc_advocacy.py` | `168_link_adjudication_hubs.py` |
| `ferc_source_coverage.csv` | internal-by-decision | — | — | — |
| `ferc_tribal_dockets.csv` | shippable | — | `133_build_ferc_advocacy.py` | `168_link_adjudication_hubs.py` `175_restore_ferc_docket_table_after_rebuild_revert.py` |
| `fr_ex_parte_notices.csv` | shippable | — | — | — |
| `fr_ex_parte_parties.csv` | shippable | `cedar_uid` | `154_build_fr_ex_parte_notices.py` | `503_identity.py` |
| `fr_ex_parte_party_entity_links.csv` | shippable | `cedar_uid` | `154_build_fr_ex_parte_notices.py` | `503_identity.py` |
| `hearing_appearances.csv` | shippable | `cedar_uid` `entity_id` | `98_build_oira_and_hearings.py` | `400_promote_stranded_hearing_appearances.py` |
| `hearing_bill_links.csv` | shippable | — | — | — |
| `lobbying_client_attribution.csv` | internal-by-decision | `tribe_id` `cedar_uid` | — | — |
| `lobbying_disclosure_verbosity_year.csv` | shippable | — | — | — |
| `lobbying_issue_families_filing.csv` | shippable | `cedar_uid` `entity_id` | `78_content_analysis.py` | `353_propagate_lobbying_corrections_to_consumers.py` `503_identity.py` |
| `lobbying_issue_family_year.csv` | shippable | — | — | — |
| `lobbying_registrant_client_relationships.csv` | shippable | `cedar_uid` | — | — |
| `lobbying_registrant_concentration.csv` | shippable | — | — | — |
| `lobbying_registrant_identifiers.csv` | shippable | — | — | — |
| `lobbying_registrant_native_ownership_evidence.csv` | shippable | `cedar_uid` | — | — |
| `lobbying_registrants.csv` | shippable | — | — | — |
| `lobbying_target_entities.csv` | shippable | — | — | — |
| `lobbying_unmatched_clients.csv` | internal-by-decision | — | — | — |
| `native_entity_lobbying_disclosures.csv` | shippable | `cedar_uid` `entity_id` | `05_match_filings_v2.py` | `350_withdraw_false_lobbying_attributions.py` `65_lobbying_organization_type_guard.py` |
| `nonprofit_schedule_c_coverage.csv` | shippable | — | — | — |
| `nonprofit_schedule_c_lobbying.csv` | shippable | `ein` | — | — |
| `nrc_meeting_participants.csv` | shippable | `cedar_uid` | — | — |
| `nrc_public_meetings.csv` | shippable | — | — | — |
| `oira_federal_action_links.csv` | shippable | — | — | — |
| `oira_meeting_participants.csv` | shippable | `cedar_uid` `entity_id` | — | — |
| `oira_meetings.csv` | shippable | `cedar_uid` `entity_id` | — | — |
| `tribe_year_lobbying_panel.csv` | shippable | `cedar_uid` `entity_id` | `05_match_filings_v2.py` | `351_rebuild_lobbying_panel_from_corrected_disclosures.py` `65_lobbying_organization_type_guard.py` |

Declared grain — validated against the file on every run:

- `admin_appeal_decisions.csv` — one row per published administrative appeal decision
  - primary key: `decision_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `admin_appeal_parties.csv` — one row per party named in an administrative appeal decision
  - primary key: `party_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 21)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `admin_appeal_positions.csv` — one row per (administrative appeal decision, organisation named opposite it, resolved Native entity) - the position ONE organisation is recorded in with respect to ONE Native entity in ONE matter. `position` is UNDETERMINED on all 8 rows BY DESIGN: the OHA chronological index publishes case name, date and citation, which establishes who appealed and never whether the Interior action favoured or harmed the Native entity
  - primary key: `position_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 1), `matter_id` → many row(s) per value (measured max 1)
  - declared by: workstream GRAIN-WS3 2026-09-01: declared from the build log in code/144_build_admin_appeals.py `stage_positions`, which states the id construction and refuses duplicates; key confirmed unique on the FULL 8-row file after the 1 -> 8 re-derivation. Re-measured by code/573_ws3_grain_and_money.py measure
- `advocacy_passthrough.csv` — one row per funder-to-recipient grant that the passthrough chain connects to lobbying
  - primary key: `passthrough_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 10)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `advocacy_passthrough_2026-08-07.csv` — one row per funder-to-recipient grant in the 2026-08-07 snapshot of advocacy_passthrough
  - primary key: `passthrough_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 10)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `agency_attention_vs_advocacy.csv` — one row per department, comparing Federal Register attention with lobbying targeting
  - primary key: `department`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `agency_attention_vs_advocacy_year.csv` — one row per (department, year)
  - primary key: `department` + `year`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `earmarks.csv` — one row per congressional earmark request
  - primary key: `earmark_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 42), `entity_id` → many row(s) per value (measured max 42)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `ferc_docket_filings.csv` — one row per OCCURRENCE of a document on a FERC docket as eLibrary returns it: (content identity of the filing, occurrence ordinal). `ferc_filing_id` is a blake2b digest of five columns eLibrary states and IS NOT UNIQUE BY DESIGN - it collides on 769 groups, of which 602 are the same document published twice under one accession and 167 are two filings whose recorded filer name differs only in CASE and are NOT the same filing. `filing_occurrence_seq` separates both without deleting either, and is assigned by sorting each colliding group on its own full content, so it is a function of the data and not of fetch order. A COUNT OF ROWS IS NOT A COUNT OF DOCUMENTS: 102,615 rows carry 101,626 distinct content identities. This table holds no money column
  - primary key: `ferc_filing_id` + `filing_occurrence_seq`  (validated unique)
  - join cardinality: `accession_number` → many row(s) per value (measured max 1515), `cedar_uid` → many row(s) per value (measured max 389), `docket_number` → many row(s) per value (measured max 5270), `resolved_native_entity_id` → many row(s) per value (measured max 389)
  - declared by: workstream UPSTREAM 2026-09-01: ordinal added by code/781_upstream_grain_columns.py because `133`'s own header states that running it reverts `168`'s in-place enrichment; `133` was fixed in the same pass so a future rebuild reproduces the column. Key confirmed unique on the FULL 102,615-row file, whole-row duplicates 822 -> 0, rows 102,615 -> 102,615
- `ferc_docket_parties.csv` — one row per party on a FERC docket
  - primary key: `ferc_docket_party_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 14)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `ferc_ex_parte_communications.csv` — one row per (ex parte communication notice, party recorded as having filed or issued it). One notice names more than one such party and each is a row, so a count of ROWS is not a count of NOTICES: 713 rows carry 657 distinct notices. `filed_or_issued_by_as_recorded` is blank on 44 rows, where the notice names no filing party, and blank is a value of this key rather than a gap in it
  - primary key: `ferc_ex_parte_id` + `filed_or_issued_by_as_recorded`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 2)
  - declared by: workstream GRAIN-WS3 2026-09-01: the discriminator was found by diffing every colliding group column by column, then the key was confirmed unique on the FULL 713-row file. Re-measured by code/573_ws3_grain_and_money.py measure
- `ferc_ex_parte_parties.csv` — one row per party row printed in a FERC ex parte notice table. `ferc_ex_parte_party_id` alone is NOT unique (9 collisions) and must not be used as a key
  - primary key: `ferc_ex_parte_party_id` + `table_row_quote`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 2)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `ferc_tribal_dockets.csv` — one row per FERC docket swept, with retrieved-vs-reported totals - docs/UNSHIPPED_TABLE_TRIAGE.md
  - primary key: `docket_number` + `subdocket`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_ex_parte_notices.csv` — one row per Federal Register ex parte notice
  - primary key: `fr_ex_parte_notice_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_ex_parte_parties.csv` — one row per party named in a Federal Register ex parte notice
  - primary key: `fr_ex_parte_party_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_ex_parte_party_entity_links.csv` — one row per resolved link from an ex parte party to a Cedar entity, across TWO source tables - `source_dataset` says which, and the join key is (source_dataset, source_row_id), never source_row_id alone. All 9 links currently come from `ferc_ex_parte_parties.csv`; `fr_ex_parte_parties.csv` resolves 0 of its 112 parties, so a join from fr_ex_parte_parties returns NOTHING and that is the data, not a broken key
  - primary key: `link_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 2)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `hearing_appearances.csv` — one row per witness appearance at a congressional hearing
  - primary key: `hearing_appearance_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 78), `entity_id` → many row(s) per value (measured max 78)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `hearing_bill_links.csv` — one row per (committee meeting event, bill named in that event's relatedItems and present in native_bills.csv). NOT one row per hearing and NOT one row per bill: one event reaches 19 bills and one bill reaches 4 events. The link is Congress.gov's own related-item assertion - `link_basis` says so on every row - and it states that the meeting CONCERNS the bill, never that the bill was marked up, voted or reported. This table holds no money column
  - primary key: `event_id` + `bill_id`  (validated unique)
  - join cardinality: `bill_id` → many row(s) per value (measured max 4), `event_id` → many row(s) per value (measured max 19)
  - declared by: workstream UPSTREAM 2026-09-01: `98.dedupe_related_bills` now reads each relatedItems.bills element ONCE, and the one row that existed only because event 338549 lists 119-s-3878 twice verbatim was un-ingested by code/781 after proving the repetition against the cached payload. Key confirmed unique on the FULL 464-row file, literal duplicates 1 -> 0
- `lobbying_disclosure_verbosity_year.csv` — one row per filing year of disclosure verbosity measures
  - primary key: `filing_year`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `lobbying_issue_families_filing.csv` — one row per LDA filing, with the issue families classified from its text
  - primary key: `filing_uuid`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 400), `entity_id` → many row(s) per value (measured max 400)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `lobbying_issue_family_year.csv` — one row per (issue family, filing year)
  - primary key: `issue_family` + `filing_year`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `lobbying_registrant_client_relationships.csv` — one row per (registrant, client) - docs/LOBBYING_REGISTRANT_BUILD_LOG.md
  - primary key: `registrant_id` + `client_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 16)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `lobbying_registrant_concentration.csv` — one row per scope over which concentration is measured - docs/LOBBYING_REGISTRANT_BUILD_LOG.md
  - primary key: `scope` + `scope_value`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `lobbying_registrant_identifiers.csv` — one row per identifier assertion about a registrant, with its asserter - docs/LOBBYING_REGISTRANT_BUILD_LOG.md
  - primary key: `identifier` + `asserted_by_source`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `lobbying_registrant_native_ownership_evidence.csv` — one row per (registrant, evidence route, Native entity, identifier assertion) - ONE PIECE OF EVIDENCE, not one registrant and not one ruling. A registrant appears on up to 5 rows and the table is deliberately allowed to contradict itself: two routes may name different entities, and `182` refuses to pick when they are equally strong. `identifier` and `asserted_by_source` are BLANK on the 16 rows whose route is not an identifier route (R1/R2/R3), and blank is a value of this key rather than a gap in it. The four rows sharing UEI CY16XXPHX213 are four INDEPENDENT sources asserting one identifier and must never be collapsed - collapsing them destroys the corroboration that is the entire content of this table
  - primary key: `registrant_id` + `evidence_route` + `native_entity_id` + `identifier` + `asserted_by_source`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 5), `native_entity_id` → many row(s) per value (measured max 5), `registrant_id` → many row(s) per value (measured max 5)
  - declared by: workstream UPSTREAM 2026-09-01: `182` now carries identifier_type, identifier and asserted_by_source from lobbying_registrant_identifiers.csv onto the R4/R5 evidence rows, and carries `cedar_uid` FORWARD from the previous output so the rebuild cannot erase a minted column. Key confirmed unique on the FULL 27-row file, literal duplicates 4 -> 0, rows 27 -> 27
- `lobbying_registrants.csv` — one row per Senate LDA registrant_id - docs/LOBBYING_REGISTRANT_BUILD_LOG.md
  - primary key: `registrant_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `lobbying_target_entities.csv` — one row per government entity as written on the filings
  - primary key: `government_entity_as_filed`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `native_entity_lobbying_disclosures.csv` — one row per LDA filing attributed to a Native entity
  - primary key: `filing_uuid`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 401), `entity_id` → many row(s) per value (measured max 401)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nonprofit_schedule_c_coverage.csv` — one row per IRS e-file INDEX YEAR (submission year, not tax year), carrying how many returns that year's index held for Cedar's Native nonprofit EIN target list, how many were retrieved, and how many carried a Schedule C. `not_downloaded` is Cedar's fetch backlog, never an absence at the IRS.
  - primary key: `index_year`  (validated unique)
  - join cardinality: `index_year` → one row(s) per value (measured max 1)
  - declared by: workstream INT-READY 2026-09-02: index_year confirmed 10 distinct / 0 blank on the FULL 10-row file
- `nonprofit_schedule_c_lobbying.csv` — one row per IRS 990 e-file RETURN parsed for Schedule C - one accepted return of one filer, identified by its IRS OBJECT_ID. NOT one row per organisation and NOT one row per tax year: an amended or short-period return for the same (ein, tax_year) is a second return and a second row (29 such pairs).
  - primary key: `schedule_c_row_id`  (validated unique)
  - join cardinality: `cedar_entity_id` → many row(s) per value (measured max 82), `ein` → many row(s) per value (measured max 10), `object_id` → one row(s) per value (measured max 1), `schedule_c_row_id` → one row(s) per value (measured max 1)
  - declared by: workstream INT-READY 2026-09-02: schedule_c_row_id and object_id each confirmed 6,870 distinct / 0 blank on the FULL 6,870-row file with csv.reader; 0 literal duplicate rows; (ein, tax_year) tested and REJECTED at 6,841
- `nrc_meeting_participants.csv` — one row per external participant in an NRC public meeting
  - primary key: `participant_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nrc_public_meetings.csv` — one row per NRC public meeting
  - primary key: `nrc_meeting_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `oira_federal_action_links.csv` — one row per (OIRA meeting, Federal Register document) link
  - primary key: `oira_meeting_id` + `federal_action_document_number`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `oira_meeting_participants.csv` — one row per attendee organisation at an OIRA meeting - docs/OIRA_HEARINGS_BUILD_LOG.md
  - primary key: `oira_participant_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 18), `entity_id` → many row(s) per value (measured max 18)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `oira_meetings.csv` — one row per OIRA meeting; attendance lives in oira_meeting_participants.csv - docs/OIRA_HEARINGS_BUILD_LOG.md
  - primary key: `oira_meeting_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 2), `entity_id` → many row(s) per value (measured max 2)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `tribe_year_lobbying_panel.csv` — one row per (entity, filing year). A join on entity alone fans out across years
  - primary key: `entity_id` + `filing_year`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 28), `entity_id` → many row(s) per value (measured max 28)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json

## Federal Prime Contracting  (`contractors`, shelf: pro)

Rebuild: `py -3 code/build.py run contractors --execute` — 11 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `contractor_ranking.csv` | shippable | — | — | — |
| `fpds_uei_cage_map.csv` | shippable | `uei` `cage_code` | — | — |
| `fpds_uei_edges.csv` | shippable | — | `13_build_fpds_hierarchy.py` | `26_fix_sanity_failures.py` |
| `prime_contracts.csv` | shippable | `tribe_id` `cedar_uid` `cage_code` | `40_build_prime_contracts.py` `871_promote_geo_keys_contracts.py` | `114_pull_prime_archive.py` `131_merge_archive_backfill.py` `174_apply_rulings_to_source_tables.py` `207_normalize_extent_competed.py` `366_courtlistener_ownership_adjudication.py` `40_build_prime_contracts.py` `429_apply_asof_ownership_status.py` `430_restore_prime_transaction_key.py` `950_promote_contract_attributes.py` |
| `prime_contracts_archive_backfill.csv` | shippable | `tribe_id` `cedar_uid` `cage_code` | `114_pull_prime_archive.py` | `430_restore_prime_transaction_key.py` |
| `prime_contracts_awards.csv` | shippable | `tribe_id` `cedar_uid` `cage_code` | — | — |
| `prime_contracts_entity_year.csv` | shippable | `tribe_id` `cedar_uid` | `40_build_prime_contracts.py` | `131_merge_archive_backfill.py` `428_rebuild_prime_entity_year.py` |
| `prime_contracts_published.csv` | shippable | `tribe_id` `cedar_uid` `cage_code` | — | — |
| `sam_prime_contracts_fy2000_2007.csv` | shippable | `cage_code` | — | — |
| `sam_prime_contracts_fy2000_2007_PUBLISHABLE.csv` | shippable | `cage_code` | — | — |
| `sam_prime_contracts_fy2000_2007_reconciliation.csv` | internal-by-decision | — | — | — |

Declared grain — validated against the file on every run:

- `contractor_ranking.csv` — one row per OPERATING COMPANY of one Native owner entity: the firm, the entity that owns it, that entity's class, and the identifier link that establishes the ownership, TIER A ONLY. An owner with nine subsidiaries occupies nine rows carrying one `owner_rank`. `operating_company_seq` is 1..n within the owner in DESCENDING `firm_obligations_usd` - a POSITION, not an identity: it is recomputed on every build and it moves when a firm's obligations move, so join on `operating_company_uei` if you need something stable across vintages. THE ADDITIVE FAMILY IS `firm_*` AND ONLY `firm_*`. Every `owner_*` column is an OWNER-grain attribute repeated on every operating-company row of that owner: SUM(owner_obligations_usd) over rows is $6,535.96B against a true $176.74B, a 36.98x inflation over 283 owners, and they may be totalled only after collapsing to distinct `owner_entity_id`. `owner_rank` is an owner attribute, not a row attribute. AND THE WHOLE TABLE IS THE SAME MONEY AS `prime_contracts.csv`: SUM(firm_obligations_usd) = $176.74B, equal to that file's tier-A attributed obligations to within $0.04, so the ranking is a LOSSLESS PARTITION of that slice. Summing the two together, or unioning them, double-counts $176.74B.
  - primary key: `owner_entity_id` + `operating_company_seq`  (validated unique)
  - join cardinality: `operating_company_uei` → many row(s) per value (measured max 1), `owner_entity_id` → many row(s) per value (measured max 70)
  - declared by: workstream GRAIN-WS5 2026-09-01: `operating_company_seq` added to code/269_build_contractor_ranking.py (the fix WS2 proposed and did not make); key confirmed unique on the FULL 1,429-row file with 0 duplicates on the run that wrote it. Re-measured by code/731_ws5_grain_contractors_nonprofits_deals.py measure
- `fpds_uei_cage_map.csv` — one row per (UEI, CAGE code, legal business name as recorded) triple OBSERVED in the FPDS/USAspending extracts, rolled up across every extract that carried it: `source_file` is a ';'-joined LIST of source files and n_observations/first_year/last_year are that rollup, never a key. NOT one row per UEI (19,475 UEIs over 34,601 rows) and NOT one row per firm. A BLANK cage_code is a VALUE, not a gap - it means the extract recorded this UEI under this legal name with no CAGE at all, which is 23,510 of the 34,601 rows. JOIN WARNING, measured 2026-09-01: 2,196 rows carry the LITERAL STRING 'NAN' in cage_code - a pandas null stringified on export, not a CAGE - and they span 2,193 DISTINCT UEIs. Joining another table on cage_code without excluding 'NAN' fuses 2,193 unrelated entities into one. Excluding it, the route is near-exact: of 6,843 real CAGE codes only 15 map to more than one UEI and none maps to more than two.
  - primary key: `uei` + `cage_code` + `legal_business_name`  (validated unique)
  - join cardinality: `cage_code` → many row(s) per value (measured max 2196), `uei` → many row(s) per value (measured max 16)
  - declared by: workstream GRAIN-WS2 2026-09-01; key confirmed unique on the FULL 34,601-row file and the 'NAN' hazard measured by code/572_ws2_contracts.py measure
- `fpds_uei_edges.csv` — one row per DECLARED (child_uei, parent_uei, edge_type) - literal pairs observed on transactions; connections, not a verified tree
  - primary key: `child_uei` + `parent_uei` + `edge_type`  (validated unique)
  - declared by: docs/HIERARCHY_MODEL.md
- `prime_contracts.csv` — TWO populations under one schema, and the seam is real. Archive rows (FY2008-FY2026, source_file `FY*_All_Contracts_Full_*.zip`): one row per FPDS TRANSACTION, identified by `contract_transaction_unique_key`. BGOV rows (`master prime file.dta`): one row per (contract, parent vehicle, fiscal year, vendor) AGGREGATE, with an EMPTY transaction key because none exists for them. Both are additive in `total_obligations`; neither row count is comparable to the other
  - primary key: `contract_transaction_unique_key` + `contract_number` + `parent_contract_number` + `fiscal_year` + `awardee_uei`  (validated unique)
  - join cardinality: `cage_code` → many row(s) per value (measured max 398840), `cedar_uid` → many row(s) per value (measured max 111398), `contract_number` → many row(s) per value (measured max 11700), `tribe_id` → many row(s) per value (measured max 111398)
  - declared by: code/430_restore_prime_transaction_key.py - the transaction key restored from the staged archive rows (1:1 on all 19 fiscal years), 2026-08-29 correctness pass. Literal duplicate rows 80,778 -> 0 with no row and no dollar removed
- `prime_contracts_archive_backfill.csv` — one row per FPDS TRANSACTION in the USAspending static archive for FY2008-FY2022, restricted to rows the identifier ledger matched at tier A or B. This is the staged half of prime_contracts.csv and every row of it is also in that file - the two must NEVER be summed together
  - primary key: `contract_transaction_unique_key`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 50208), `contract_number` → many row(s) per value (measured max 7029), `tribe_id` → many row(s) per value (measured max 50208)
  - declared by: code/430_restore_prime_transaction_key.py, 2026-08-29 correctness pass: 631,507 rows, key unique on the FULL file, literal duplicate rows 60,919 -> 0 with no row and no dollar removed
- `prime_contracts_awards.csv` — one row per CONTRACT (award), rolled up across its transactions - not one row per transaction
  - primary key: `contract_number`  (validated unique)
  - join cardinality: `cage_code` → many row(s) per value (measured max 85976), `cedar_uid` → many row(s) per value (measured max 55184), `tribe_id` → many row(s) per value (measured max 55184)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `prime_contracts_entity_year.csv` — one row per (Native entity, federal fiscal year) with that entity's prime contracting obligations summed across every attributed transaction. Tier A and tier B attributions are SEPARATE COLUMNS, never separate rows
  - primary key: `tribe_id` + `fiscal_year`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 27), `fiscal_year` → many row(s) per value (measured max 298), `tribe_id` → many row(s) per value (measured max 27)
  - declared by: code/cedar_prime_panel.py - the entity-year ruling, 2026-08-29 correctness pass; rebuilt by code/428_rebuild_prime_entity_year.py, whose assert_grain() refuses to write a panel this declaration would not hold for
- `prime_contracts_published.csv` — one row per CONTRACT (award), the publishable projection of prime_contracts_awards.csv
  - primary key: `contract_number`  (validated unique)
  - join cardinality: `cage_code` → many row(s) per value (measured max 85976), `cedar_uid` → many row(s) per value (measured max 55184), `tribe_id` → many row(s) per value (measured max 55184)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `sam_prime_contracts_fy2000_2007.csv` — one row per FPDS transaction in the FY2000-2007 SAM archive pull
  - primary key: `sam_transaction_key`  (validated unique)
  - join cardinality: `cage_code` → many row(s) per value (measured max 304)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `sam_prime_contracts_fy2000_2007_PUBLISHABLE.csv` — one row per FPDS transaction in the FY2000-2007 SAM archive pull, publishable projection
  - primary key: `sam_transaction_key`  (validated unique)
  - join cardinality: `cage_code` → many row(s) per value (measured max 304)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json

## Federal Subcontracting  (`subcontracting`, shelf: pro)

Rebuild: `py -3 code/build.py run subcontracting --execute` — 5 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `prime_sub_network.csv` | shippable | — | — | — |
| `subaward_entity_rollup.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `subaward_identifier_harvest.csv` | internal-by-decision | `uei` `cage_code` | — | — |
| `subaward_identifier_netnew.csv` | internal-by-decision | `uei` `cage_code` | — | — |
| `subawards.csv` | shippable | `cedar_uid` | `20_build_subcontracts.py` `871_promote_geo_keys_contracts.py` | `121_pull_subawards_api.py` `250_demote_stale_tierA_subaward_rows.py` `45_promote_subawards.py` `910_subaward_report_id_backfill.py` `911_subaward_sub_leg_cedar_uid.py` |

Declared grain — validated against the file on every run:

- `prime_sub_network.csv` — one row per (prime UEI, sub UEI) edge, rolled up across subawards
  - primary key: `prime_uei` + `sub_uei`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `subaward_entity_rollup.csv` — one row per entity, rolled up across both sides of the subaward network
  - primary key: `tribe_id`  (validated unique)
  - join cardinality: `cedar_uid` → one row(s) per value (measured max 1), `tribe_id` → one row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `subawards.csv` — one row per SUBAWARD FILING AS INGESTED FROM ONE SOURCE - not one row per subaward. FFATA/FSRS requires the PRIME to re-file an open subaward monthly, and every filing is a real reporting event, so one $57,500 subaward can be 93 rows spanning 2022-08 to 2025-01. Cedar RETAINS all of them and flags the repeats in `duplicate_status`; it does not delete them. A row is therefore (one SAM subaward report) x (the Cedar pull that ingested it). MONEY: `subaward_amount` is additive ONLY where `duplicate_status == 'primary'` AND `subaward_exceeds_prime_flag != 'yes'` - $25,864,997,128.19 correct against $47,301,660,819.78 unfiltered, so an unfiltered sum is 82.9% TOO HIGH as a share of the correct total (45.3% of the inflated one; say which denominator you mean). A SUBAWARD IS A SLICE OF A PRIME AWARD and must never be added to prime_contracts.csv - that double-counts the same federal dollar. The two entity legs are `prime_cedar_uid` and `sub_cedar_uid`; `cedar_uid` is the PRIME leg only and is legitimately blank on the 43,282 rows whose only Native party is the subawardee
  - primary key: `source_dataset` + `subaward_source_record_id`  (validated unique)
  - join cardinality: `prime_award_unique_key` → many row(s) per value (measured max 1536), `prime_cedar_uid` → many row(s) per value (measured max 6651), `prime_uei` → many row(s) per value (measured max 2377), `sub_cedar_uid` → many row(s) per value (measured max 2839), `sub_uei` → many row(s) per value (measured max 2766)
  - declared by: workstream SUBAWARD-FUNDING 2026-09-02: `subaward_source_record_id` recovered from the staged FSRS extracts by code/910_subaward_report_id_backfill.py (75,861 SAM report ids + 998 HigherGov permalinks, 0 blank), and the pair confirmed unique on the FULL 76,859-row file - 0 collisions, 0 blanks, whole-row duplicates 10,770 -> 0 with zero rows removed. Re-measure with `py -3 code/910_subaward_report_id_backfill.py verify`; the recovery's own refusal is proved to fire by `... selftest`

## Native-Owned Businesses  (`native-owned-businesses`, shelf: pro)

Rebuild: `py -3 code/build.py run native-owned-businesses --execute` — 7 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `individual_native_exclusion_pairs.csv` | shippable | — | — | — |
| `individual_native_firm_contracts.csv` | shippable | `cedar_uid` | — | — |
| `individual_native_firm_contracts_published.csv` | shippable | — | — | — |
| `individual_native_firm_register.csv` | shippable | `cedar_uid` | — | — |
| `individual_native_ownership_verification.csv` | shippable | — | — | — |
| `individual_native_prior_rulings.csv` | internal-by-decision | — | — | — |
| `individual_native_verification_candidates.csv` | shippable | — | — | — |

Declared grain — validated against the file on every run:

- `individual_native_exclusion_pairs.csv` — one row per (identifier, excluded entity) exclusion ruling
  - primary key: `identifier_type` + `identifier`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `individual_native_firm_contracts.csv` — one row per (individually-Native-owned firm, fiscal year)
  - primary key: `surrogate_entity_id` + `fiscal_year`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 23)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `individual_native_firm_contracts_published.csv` — one row per published aggregate CELL (cell type x dimension 1 x dimension 2) - not per firm
  - primary key: `cell_type` + `dimension_1` + `dimension_2`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `individual_native_firm_register.csv` — one row per individually-Native-owned firm ruled into the class
  - primary key: `surrogate_entity_id`  (validated unique)
  - join cardinality: `cedar_uid` → one row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `individual_native_ownership_verification.csv` — one row per verification candidate, with its four independent evidence fields - docs/INDIVIDUAL_NATIVE_OWNERSHIP_VERIFICATION_BUILD_LOG.md
  - primary key: `verification_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `individual_native_verification_candidates.csv` — one row per candidate UEI staged for individual-Native verification
  - primary key: `verification_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json

## Natural Resource Revenues  (`natural-resources`, shelf: pro)

Rebuild: `py -3 code/build.py run natural-resources --execute` — 9 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `anc_ceiling_roster.csv` | shippable | `cedar_uid` `uei` `cage_code` | — | — |
| `ancsa_filings_index.csv` | shippable | `cedar_uid` | `build_manifest_index.py` | `update_index.py` |
| `nd_severance_allocation.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `resource_asset_source_coverage.csv` | internal-by-decision | — | — | — |
| `resource_assets.csv` | shippable | `cedar_uid` | — | — |
| `resource_parties.csv` | shippable | `cedar_uid` `entity_id` | — | — |
| `resource_revenue.csv` | shippable | `cedar_uid` | — | — |
| `tribal_bond_issuances.csv` | shippable | — | — | — |
| `tribal_tax_bases.csv` | shippable | `tribe_id` `cedar_uid` | — | — |

Declared grain — validated against the file on every run:

- `anc_ceiling_roster.csv` — one row per Alaska Native Corporation on the ANCSA ceiling roster
  - primary key: `anc_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `ancsa_filings_index.csv` — one row per document in the ANCSA portal index, downloaded or not - docs/ANCSA_PORTAL_BUILD_LOG.md
  - primary key: `portal_document_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nd_severance_allocation.csv` — one row per North Dakota severance-allocation rule in force over an interval
  - primary key: `allocation_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 7), `tribe_id` → many row(s) per value (measured max 7)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `resource_assets.csv` — one row per resource asset (lease, tract, agreement or well)
  - primary key: `resource_asset_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `resource_parties.csv` — one row per (party link, entity as named). `party_link_id` alone has 1 collision and is not a key on its own
  - primary key: `party_link_id` + `entity_name`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 518), `entity_id` → many row(s) per value (measured max 518)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `resource_revenue.csv` — one row per resource revenue event as recorded by its source system
  - primary key: `resource_revenue_event_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 492)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `tribal_bond_issuances.csv` — one row per debt instrument of one tribal issuer, as described in one retrieved rating action or disclosure document. NOT one row per issuer and NOT a time series: `issue_date` is blank on 28 of 29 rows BY DESIGN (the retrieved document states none and none is inferred), and `cusip` is blank on all 29, so the market key of a bond is absent. `par_amount` is the size AT ISSUE of a distinct instrument and is additive across rows; it is NOT debt outstanding, several rows say so in `instrument_type` ('amount outstanding at'), and refinancings of one facility appear as separate instruments
  - primary key: `issuer` + `instrument_type` + `source_url`  (validated unique)
  - declared by: workstream GRAIN-WS3 2026-09-01: key confirmed unique on the FULL 29-row file with zero blank components; `issuer+par_amount+instrument_type` and `issuer+instrument_type+maturity` are also unique but each carries a blank, and `cusip` is blank on every row. Re-measured by code/573_ws3_grain_and_money.py measure
- `tribal_tax_bases.csv` — one row per (tribe, tax type, period) - docs/TRIBAL_TAX_DECOMPOSITION.md
  - primary key: `tax_observation_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 660), `tribe_id` → many row(s) per value (measured max 660)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json

## Native Nonprofits  (`nonprofits`, shelf: pro)

Rebuild: `py -3 code/build.py run nonprofits --execute` — 12 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `fac_tribal_single_audits.csv` | shippable | `cedar_uid` `entity_id` | — | — |
| `grantmaker_funding_coverage.csv` | internal-by-decision | — | — | — |
| `grantmaker_funding_flows.csv` | shippable | `cedar_uid` | — | — |
| `grantmaker_funding_overlap.csv` | shippable | — | — | — |
| `np_ein_entity_hub.csv` | shippable | `cedar_uid` `entity_id` `ein` | — | — |
| `np_ein_uei_bridge.csv` | internal-by-decision | `uei` `ein` | — | — |
| `np_financials.csv` | shippable | `ein` | — | — |
| `np_grantee_financials.csv` | shippable | `ein` | — | — |
| `np_org_scale.csv` | shippable | `ein` | — | — |
| `np_orgs.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` | — | — |
| `np_schedule_i_filers.csv` | shippable | — | — | — |
| `np_schedule_i_grants.csv` | shippable | `cedar_uid` | — | — |

Declared grain — validated against the file on every run:

- `fac_tribal_single_audits.csv` — one row per Single Audit report for a tribal auditee
  - primary key: `report_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 32), `entity_id` → many row(s) per value (measured max 32)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `grantmaker_funding_flows.csv` — one row per named grant recipient on a grantmaker's own return - docs/GRANTMAKER_FUNDING_FLOWS_BUILD_LOG.md
  - primary key: `flow_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `grantmaker_funding_overlap.csv` — one row per (funder, resolved recipient target) overlap cell
  - primary key: `funder_key` + `recipient_resolved_target`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `np_ein_entity_hub.csv` — one row per EIN linked to a Cedar entity
  - primary key: `ein`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 123), `ein` → one row(s) per value (measured max 1), `entity_id` → many row(s) per value (measured max 123)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `np_financials.csv` — one row per (EIN, tax filing period) - docs/NONPROFIT_FINANCIALS_LOG.md
  - primary key: `ein` + `tax_period`  (validated unique)
  - join cardinality: `ein` → many row(s) per value (measured max 27)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `np_grantee_financials.csv` — one row per (EIN, source return) for pulled grantee 990s
  - primary key: `ein` + `source_url`  (validated unique)
  - join cardinality: `ein` → many row(s) per value (measured max 12)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `np_org_scale.csv` — one row per pulled EIN, latest year and scale band - docs/NONPROFIT_FINANCIALS_LOG.md
  - primary key: `ein`  (validated unique)
  - join cardinality: `ein` → one row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `np_orgs.csv` — one row per EIN considered for the Native nonprofit universe, ruled in or out
  - primary key: `EIN`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 121), `entity_id` → many row(s) per value (measured max 2), `tribe_id` → many row(s) per value (measured max 121)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `np_schedule_i_filers.csv` — one row per parsed 990 return - docs/SCHEDULE_I_BUILD_LOG.md
  - primary key: `object_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `np_schedule_i_grants.csv` — one row per RECIPIENT LINE of Form 990 Schedule I Part II on one filed return: (object_id, schedule_i_line_seq). ONE FILER MAY LIST ONE RECIPIENT TWICE and routinely does - 90 groups of rows are identical on every other column and every one of them is two real grant lines inside a single return, which is what Part II's repeating RecipientTable is for. `schedule_i_line_seq` is the 1-based position among the PUBLISHED lines of that return in document order; on the 5 returns where a recipient line names nobody at all and is held out to review/, it is a dense position among what ships rather than the printed form line. MONEY: `cash_grant_usd` and `noncash_assistance_usd` are additive across rows and each is a DIFFERENT dollar - never add the two columns to each other and then to a total. Summing by `recipient_ein` is safe; summing by `recipient_entity_id` covers only the 2,442 rows where it is populated. This is a FLOOR, not a universe: Part II has a $5,000 floor, e-file coverage is partial before tax year 2019, and Part III grants to individuals carry no names by form design and are NOT in this table
  - primary key: `object_id` + `schedule_i_line_seq`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 46), `filer_ein` → many row(s) per value (measured max 8463), `object_id` → many row(s) per value (measured max 1165), `recipient_ein` → many row(s) per value (measured max 80), `recipient_entity_id` → many row(s) per value (measured max 46)
  - declared by: workstream UPSTREAM 2026-09-01: ordinal added by code/781_upstream_grain_columns.py, which first PROVED no group is a double-ingest (every colliding object_id appears exactly once in np_schedule_i_filers.csv) and that object_id runs are still contiguous, so file position is document order. `132` was fixed in the same pass; it cannot be re-run today because both its XML caches hold zero files. Key confirmed unique on the FULL 58,685-row file, whole-row duplicates 101 -> 0, rows 58,685 -> 58,685, $2,089,185 of real grants NOT deleted

## Gaming Intelligence  (`gaming`, shelf: grove)

Rebuild: `py -3 code/build.py run gaming --execute` — 61 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `ca_gaming_facilities_official.csv` | shippable | `tribe_id` `cedar_uid` `facility_id` | — | — |
| `ca_gaming_payments.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `compact_events.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `compact_id` | — | — |
| `compact_obligation_tribal_agency_bridge.csv` | shippable | `tribe_id` `cedar_uid` `compact_id` | — | — |
| `compact_required_reports.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `compact_id` | — | — |
| `compact_structured_terms.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `compact_id` | — | — |
| `compact_terms.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `compact_id` | — | — |
| `compact_versions.csv` | shippable | `compact_id` | — | — |
| `compacts.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `compact_id` | — | — |
| `digital_gaming_relationships.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `facility_id` | — | — |
| `digital_gaming_revenue.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `facility_id` | `119_build_digital_and_loyalty.py` | `174_backfill_digital_gaming_tiers.py` `860_state2_acquisition.py` |
| `fac_audit_gaming_disclosures.csv` | shippable | `cedar_uid` `entity_id` | — | — |
| `fac_audit_sefa_gaming_programs.csv` | shippable | `cedar_uid` `entity_id` | `147_build_fac_single_audits.py` | `814_gaming_nr_grain_and_conservation.py` |
| `fl_gaming_payments.csv` | shippable | `tribe_id` `cedar_uid` `facility_id` | — | — |
| `gaming_capacity_official.csv` | shippable | `tribe_id` `cedar_uid` `facility_id` | `92_build_gaming_capacity_official.py` | `106_build_revenue_bounds.py` |
| `gaming_decision_compact_join.csv` | shippable | — | — | — |
| `gaming_decision_events.csv` | shippable | — | — | — |
| `gaming_device_observations.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `facility_id` | — | — |
| `gaming_employment_observations.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `facility_id` `ein` | `100_finish_declinations_and_employment.py` | `158_merge_staged_labor_employment.py` `262_repair_form5500_tribe_attribution.py` `265_merge_osha_relift_rows.py` |
| `gaming_facilities.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `facility_id` | — | — |
| `gaming_facility_metrics.csv` | licensed-never-ships | `entity_id` `facility_id` | — | — |
| `gaming_field_coverage.csv` | internal-by-decision | — | — | — |
| `gaming_financing_events.csv` | shippable | `cedar_uid` | `91_build_nigc_declinations.py` | `100_finish_declinations_and_employment.py` |
| `gaming_game_finder_observations.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `facility_id` | — | — |
| `gaming_game_finder_systems.csv` | internal-by-decision | — | — | — |
| `gaming_land_decisions.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` | — | — |
| `gaming_manufacturer_facts.csv` | shippable | — | — | — |
| `gaming_mitigation_agreements.csv` | shippable | — | — | — |
| `gaming_nigc_roster_link.csv` | shippable | `tribe_id` `cedar_uid` `facility_id` | — | — |
| `gaming_ordinance_ocr.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `gaming_ordinances.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `gaming_project_facilities.csv` | shippable | `cedar_uid` `entity_id` | — | — |
| `gaming_projections.csv` | shippable | — | — | — |
| `gaming_properties.csv` | shippable | `tribe_id` `cedar_uid` `facility_id` | `82_build_gaming_property_dataset.py` | `160_sync_published_gaming_view.py` `175_sync_published_property_view_entities.py` `255_fix_gaming_property_deal_counts.py` |
| `gaming_property_capacity_history.csv` | licensed-never-ships | `entity_id` `facility_id` | — | — |
| `gaming_property_coverage.csv` | internal-by-decision | `tribe_id` `cedar_uid` `entity_id` `facility_id` | — | — |
| `gaming_property_federal_traces.csv` | shippable | `tribe_id` `cedar_uid` `facility_id` `compact_id` | — | — |
| `gaming_property_labor_demand.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `facility_id` | — | — |
| `gaming_property_locations.csv` | UNDOCUMENTED | `property_id` | — | — |
| `gaming_property_self_published_assertions.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `facility_id` | — | — |
| `gaming_property_self_published_claims.csv` | shippable | `tribe_id` `cedar_uid` `facility_id` | — | — |
| `gaming_property_site_observations.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `facility_id` | — | — |
| `gaming_property_universe_events.csv` | shippable | `cedar_uid` `entity_id` `facility_id` | `89_nigc_map_wayback_universe.py` | `165_link_universe_events_to_hub.py` |
| `gaming_revenue_bounds.csv` | shippable | `tribe_id` `cedar_uid` `facility_id` | — | — |
| `gaming_source_claims.csv` | shippable | — | `91_build_nigc_declinations.py` | `100_finish_declinations_and_employment.py` `510_assertions.py` |
| `gaming_vendor_tribal_licenses.csv` | shippable | `cedar_uid` `entity_id` | — | — |
| `loyalty_program_property.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `facility_id` | — | — |
| `loyalty_programs.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` | — | — |
| `nigc_action_parties.csv` | shippable | `cedar_uid` | — | — |
| `nigc_declination_letters.csv` | shippable | `cedar_uid` | `91_build_nigc_declinations.py` | `100_finish_declinations_and_employment.py` |
| `nigc_document_surface.csv` | shippable | — | — | — |
| `nigc_enforcement_actions.csv` | shippable | `cedar_uid` | — | — |
| `nigc_game_classification_opinions.csv` | shippable | — | — | — |
| `nigc_indian_lands_opinions.csv` | shippable | `cedar_uid` | — | — |
| `nigc_management_contract_approvals.csv` | shippable | `cedar_uid` | — | — |
| `nigc_region_assignments.csv` | shippable | `tribe_id` `cedar_uid` `facility_id` `administrative_region_id` | — | — |
| `nigc_regional_ggr.csv` | shippable | `administrative_region_id` | — | — |
| `nigc_revenue_bands.csv` | shippable | — | — | — |
| `state_gaming_observations.csv` | shippable | `tribe_id` `cedar_uid` `facility_id` | — | — |
| `wa_machine_allocations.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `wa_machine_transfers.csv` | UNDOCUMENTED | — | — | — |

Declared grain — validated against the file on every run:

- `ca_gaming_facilities_official.csv` — one row per facility as it appears on ONE official California list at ONE as-of date - a facility on three lists has three rows
  - primary key: `record_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 7), `facility_id` → many row(s) per value (measured max 4), `tribe_id` → many row(s) per value (measured max 7)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `ca_gaming_payments.csv` — one row per published California gaming payment observation (fund x party x period x metric)
  - primary key: `payment_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 554), `tribe_id` → many row(s) per value (measured max 554)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `compact_events.csv` — one row per dated event in a compact's life
  - primary key: `event_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 2), `compact_id` → many row(s) per value (measured max 2), `entity_id` → many row(s) per value (measured max 2), `tribe_id` → many row(s) per value (measured max 2)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `compact_obligation_tribal_agency_bridge.csv` — one row per compact reporting obligation bridged to the named tribal gaming agency
  - primary key: `bridge_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 23), `compact_id` → many row(s) per value (measured max 15), `tribe_id` → many row(s) per value (measured max 23)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `compact_required_reports.csv` — one row per reporting obligation typed out of one compact version
  - primary key: `report_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 56), `compact_id` → many row(s) per value (measured max 47), `entity_id` → many row(s) per value (measured max 56), `tribe_id` → many row(s) per value (measured max 56)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `compact_structured_terms.csv` — one row per structured term extracted from one compact version
  - primary key: `term_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 44), `compact_id` → many row(s) per value (measured max 33), `entity_id` → many row(s) per value (measured max 44), `tribe_id` → many row(s) per value (measured max 44)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `compact_terms.csv` — one row per term quote extracted from one compact version
  - primary key: `version_id` + `quote`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 21), `compact_id` → many row(s) per value (measured max 11), `entity_id` → many row(s) per value (measured max 21), `tribe_id` → many row(s) per value (measured max 21)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `compact_versions.csv` — one row per compact version (original or amendment)
  - primary key: `version_id`  (validated unique)
  - join cardinality: `compact_id` → many row(s) per value (measured max 30)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `compacts.csv` — one row per compact
  - primary key: `compact_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 14), `compact_id` → one row(s) per value (measured max 1), `entity_id` → many row(s) per value (measured max 14), `tribe_id` → many row(s) per value (measured max 14)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `digital_gaming_relationships.csv` — one row per digital-gaming relationship (tribe x brand x product authorisation)
  - primary key: `digital_gaming_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 4), `entity_id` → many row(s) per value (measured max 4), `tribe_id` → many row(s) per value (measured max 4)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `digital_gaming_revenue.csv` — one row per published digital-gaming revenue observation (licensee x period x metric)
  - primary key: `revenue_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 1788), `entity_id` → many row(s) per value (measured max 1788), `tribe_id` → many row(s) per value (measured max 1788)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fac_audit_gaming_disclosures.csv` — one row per gaming disclosure QUOTE found on one page of one Single Audit report. The table mints no disclosure id, so the quote is part of the key; `report_id` alone repeats
  - primary key: `report_id` + `verbatim_quote` + `source_page`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 136), `entity_id` → many row(s) per value (measured max 136)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fac_audit_sefa_gaming_programs.csv` — one SEFA FEDERAL AWARD LINE - one `federal_awards` record of one Single Audit reporting package - whose `federal_program_name` names gaming or a casino, on a report already in Cedar's tribal audit census. NOT one row per audit and NOT one row per tribe: `report_id` REPEATS once a report carries a second gaming line, which is why the key needs the FAC's own `award_reference`. It ships at ONE row today and that is a coverage fact, not a grain fact - it is the only line of a WITHHELD tribal reporting package the FAC still disseminates. `amount_expended` is a FEDERAL AWARD EXPENDITURE and is NOT gaming revenue; it may not be summed with any gaming money column
  - primary key: `report_id` + `award_reference`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 1), `entity_id` → many row(s) per value (measured max 1), `report_id` → many row(s) per value (measured max 1)
  - declared by: workstream GAMING-NR 2026-09-01: answers the GRAIN_OPEN question from the FAC's own cached record. Key confirmed unique with no blank component on the FULL file by code/814_gaming_nr_grain_and_conservation.py verify
- `fl_gaming_payments.csv` — one row per published Florida gaming payment observation, forecasts included and flagged
  - primary key: `payment_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 9754), `tribe_id` → many row(s) per value (measured max 9754)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_capacity_official.csv` — one row per officially published capacity observation (facility x metric x as-of date)
  - primary key: `observation_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 1584), `facility_id` → many row(s) per value (measured max 1584), `tribe_id` → many row(s) per value (measured max 1584)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_decision_compact_join.csv` — one row per BIA gaming-land decision, with the compacts it was matched to
  - primary key: `decision_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_decision_events.csv` — one row per dated status event behind a gaming-land decision - docs/GAMING_BUILD_LOG_2026-08-05.md
  - primary key: `event_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_device_observations.csv` — one row per device observation (facility x date x device class)
  - primary key: `observation_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 396), `entity_id` → many row(s) per value (measured max 396), `facility_id` → many row(s) per value (measured max 396), `tribe_id` → many row(s) per value (measured max 396)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_employment_observations.csv` — one row per employment observation at one geographic level
  - primary key: `observation_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 84), `ein` → many row(s) per value (measured max 32), `entity_id` → many row(s) per value (measured max 84), `facility_id` → many row(s) per value (measured max 11), `tribe_id` → many row(s) per value (measured max 84)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_facilities.csv` — one row per gaming facility - the directory core, docs/GAMING_BUILD_LOG_2026-08-05.md
  - primary key: `facility_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 28), `entity_id` → many row(s) per value (measured max 15), `facility_id` → one row(s) per value (measured max 1), `tribe_id` → many row(s) per value (measured max 28)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_financing_events.csv` — one row per financing event evidenced by an NIGC opinion
  - primary key: `financing_event_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 7)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_game_finder_observations.csv` — one row per game-finder listing observation
  - primary key: `observation_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 3878), `entity_id` → many row(s) per value (measured max 3878), `facility_id` → many row(s) per value (measured max 2973), `tribe_id` → many row(s) per value (measured max 3878)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_land_decisions.csv` — one row per BIA gaming-land decision record - docs/GAMING_BUILD_LOG_2026-08-05.md
  - primary key: `decision_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 5), `entity_id` → many row(s) per value (measured max 5), `tribe_id` → many row(s) per value (measured max 5)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_manufacturer_facts.csv` — one row per manufacturer fact taken from one filing
  - primary key: `fact_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_mitigation_agreements.csv` — one row per service commitment in a mitigation agreement between a project and one counterparty government
  - primary key: `project_id` + `counterparty_government` + `service`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_nigc_roster_link.csv` — one row per Cedar facility linked to the NIGC roster
  - primary key: `facility_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 18), `facility_id` → one row(s) per value (measured max 1), `tribe_id` → many row(s) per value (measured max 18)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_ordinance_ocr.csv` — one row per gaming ordinance PDF put through OCR
  - primary key: `ordinance_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 10), `tribe_id` → many row(s) per value (measured max 10)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_ordinances.csv` — one row per gaming ordinance or amendment
  - primary key: `ordinance_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 23), `tribe_id` → many row(s) per value (measured max 23)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_project_facilities.csv` — one row per development ALTERNATIVE per program source - docs/GAMING_NEPA_PILOT_LOG.md
  - primary key: `project_id` + `alternative` + `source_document`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_projections.csv` — one row per PROJECTED figure: (project, metric, geography, time period, NEPA alternative, source document, unit). A PROJECTION IS NOT A REALISED FIGURE - 114 of 116 rows carry observation_status = 'proposed' - and it must never be summed into, or alongside, any table of actual gaming revenue, employment or payments. `value` is additive across rows ONLY within one unit and one alternative; summing across alternatives adds mutually exclusive futures of the same casino, and summing a two-row range adds its own low and high endpoints
  - primary key: `project_id` + `metric` + `geography` + `time_period` + `alternative` + `source_document` + `unit`  (validated unique)
  - declared by: workstream GRAIN-WS3 2026-09-01: answers the GRAIN_OPEN question by measurement - `unit` is the third discriminator because a stated range is recorded as two endpoint rows. Key confirmed unique on the FULL 116-row file; re-measured by code/573_ws3_grain_and_money.py measure
- `gaming_properties.csv` — one row per gaming property, the temporal view of the facility directory
  - primary key: `facility_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 28), `facility_id` → one row(s) per value (measured max 1), `tribe_id` → many row(s) per value (measured max 28)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_property_federal_traces.csv` — one row per gaming property, carrying the federal traces found for it
  - primary key: `facility_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 28), `compact_id` → many row(s) per value (measured max 28), `facility_id` → one row(s) per value (measured max 1), `tribe_id` → many row(s) per value (measured max 28)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_property_labor_demand.csv` — one row per labour-demand observation on a property site
  - primary key: `observation_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 6), `entity_id` → many row(s) per value (measured max 6), `facility_id` → many row(s) per value (measured max 6), `tribe_id` → many row(s) per value (measured max 6)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_property_self_published_assertions.csv` — one SELF-PUBLISHED ASSERTION OCCURRENCE: one sentence on one page of a gaming property's OWN website making one claim about itself. Keyed by 382 as a digest of (site host, page URL, assertion kind, asserted value, first 120 characters of the quote), so the SAME claim on two pages of one host is two rows and the same sentence twice on one page is collapsed. THIS IS NOT A MEASUREMENT TABLE - every `assertion_class` is deliberately outside `cedar_domain.MeasurementType`, and the class is a first-class column because a buyer must be able to filter on it. NEVER SUM OR RECONCILE AGAINST A REGULATOR: not gaming_capacity_official.csv, not nigc_regional_ggr.csv, not nigc_revenue_bands.csv, not state_gaming_observations.csv, not wa_machine_allocations.csv. A casino's claim about its own floor and a regulator's count of that floor are TWO CLAIMS ABOUT ONE THING; adding them doubles the floor and preferring the larger turns marketing into a statistic. 2 rows are WITHDRAWN_NOT_SELF_PUBLISHED and are retained, labelled, rather than deleted
  - primary key: `assertion_id`  (validated unique)
  - join cardinality: `assertion_id` → one row(s) per value (measured max 1), `cedar_uid` → many row(s) per value (measured max 51), `facility_id` → many row(s) per value (measured max 51), `site_host` → many row(s) per value (measured max 51), `source_url` → many row(s) per value (measured max 5), `tribe_id` → many row(s) per value (measured max 51)
  - declared by: workstream GAMING-NR 2026-09-01: grain asserted in code by code/588_promote_self_published_claims.py, which refuses to write on a duplicate key; confirmed unique with no blank component and 0 literal duplicate rows on the FULL 622-row file by code/814_gaming_nr_grain_and_conservation.py verify
- `gaming_property_self_published_claims.csv` — one ADJUDICATED CLAIM OCCURRENCE - one numeric claim a gaming property publishes about itself, as the adjudicating script identified it, namespaced by `claim_family` (recovered_from_refusal_pile | first_pass_extraction). NOT one row per (source_url, metric, value): that triple collides 15 times and every collision is REAL - one page states the same number in two sentences about two different things, so collapsing it deletes a ballroom. True repetition of the SAME sentence is collapsed upstream and counted in `n_occurrences_collapsed`. THIS IS NOT A MEASUREMENT TABLE: `assertion_class` is SELF_PUBLISHED_OPERATOR_CLAIM on every row and never becomes one. NEVER SUM OR RECONCILE AGAINST A REGULATOR - the per-row `not_summable_with` column names the tables. Two further traps carried as columns: `value_is_bounded` = Y means the source said 'more than 1,000 slots' and a bound is not a count, and `also_in_gaming_property_site_observations` = Y means the row restates an observation that already ships in gaming_property_site_observations.csv, so stacking the two files double counts it
  - primary key: `claim_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 22), `claim_id` → one row(s) per value (measured max 1), `facility_id` → many row(s) per value (measured max 22), `site_host` → many row(s) per value (measured max 22), `source_claim_id` → one row(s) per value (measured max 1), `source_url` → many row(s) per value (measured max 7), `tribe_id` → many row(s) per value (measured max 22)
  - declared by: workstream GAMING-NR 2026-09-01: grain asserted in code by code/588_promote_self_published_claims.py, which refuses to write on a duplicate key; confirmed unique with no blank component and 0 literal duplicate rows on the FULL 270-row file by code/814_gaming_nr_grain_and_conservation.py verify
- `gaming_property_site_observations.csv` — one row per metric observed on a property's own website at one retrieval
  - primary key: `observation_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 25), `entity_id` → many row(s) per value (measured max 25), `facility_id` → many row(s) per value (measured max 13), `tribe_id` → many row(s) per value (measured max 25)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_property_universe_events.csv` — one row per change detected between two snapshots of the NIGC property universe
  - primary key: `event_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 1), `entity_id` → many row(s) per value (measured max 1), `facility_id` → many row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_revenue_bounds.csv` — one row per (facility or tribe, fiscal year) revenue bound
  - primary key: `bound_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 466), `facility_id` → many row(s) per value (measured max 82), `tribe_id` → many row(s) per value (measured max 466)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `gaming_source_claims.csv` — one row per claim extracted from one source document
  - primary key: `source_claim_id`  (validated unique)
  - declared by: docs/GAMING_DATASET_PLAN.md
- `gaming_vendor_tribal_licenses.csv` — one row per (vendor, tribal gaming regulator) licence as reported in one source document. `license_number` is blank on all 740 rows and cannot be part of the key
  - primary key: `vendor_name` + `tribal_gaming_regulator` + `source_url`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 287), `entity_id` → many row(s) per value (measured max 287)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `loyalty_program_property.csv` — one row per property enrolled in a loyalty program
  - primary key: `loyalty_program_id` + `facility_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 11), `entity_id` → many row(s) per value (measured max 11), `facility_id` → one row(s) per value (measured max 1), `tribe_id` → many row(s) per value (measured max 11)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `loyalty_programs.csv` — one row per loyalty program. One program per operating tribe today
  - primary key: `loyalty_program_id`  (validated unique)
  - join cardinality: `cedar_uid` → one row(s) per value (measured max 1), `entity_id` → one row(s) per value (measured max 1), `tribe_id` → one row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nigc_action_parties.csv` — one row per (ACTION, PARTY, ROLE) - the ADR-010 party bridge for the two NIGC document tables. Roles respondent and tribal_party; 384 entity, 2 multi_entity
  - primary key: `record_id` + `tribe_entity_id` + `role`  (validated unique)
  - join cardinality: `record_id` → many row(s) per value (measured max 2), `tribe_entity_id` → many row(s) per value (measured max 15)
  - declared by: code/586 assertion; INT-2 2026-09-01
- `nigc_declination_letters.csv` — one row per NIGC declination opinion
  - primary key: `cedar_opinion_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 7)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nigc_document_surface.csv` — one row per (CATEGORY, DOCUMENT) MEMBERSHIP - NOT one row per document. 7,930 memberships over 4,071 distinct documents in 73 categories; a document filed in three categories has three rows. NEVER SUM THIS AGAINST nigc_ordinances.csv (1,155) or nigc_declination_letters.csv (327): those are instrument tables at one row per instrument and this is the INDEX that measures them. NIGC's index carries 1,162 ordinance and 329 declination documents, so +7 and +2 are the REFRESH SIGNAL, not a double count
  - primary key: `nigc_category` + `document_slug`  (validated unique)
  - join cardinality: `document_slug` → many row(s) per value (measured max 4)
  - declared by: code/586 assertion; INT-2 2026-09-01
- `nigc_enforcement_actions.csv` — one row per published NIGC ENFORCEMENT DOCUMENT, 1995-2026. NOT one row per violation and NOT one row per tribe: a single matter routinely yields both an NOV and a settlement agreement - Squaxin Island NOV-06-07 and SA-06-07 are two documents and two rows
  - primary key: `action_id`  (validated unique)
  - join cardinality: `action_id` → one row(s) per value (measured max 1), `tribe_entity_id` → many row(s) per value (measured max 15)
  - declared by: code/586 assertion; INT-2 2026-09-01
- `nigc_game_classification_opinions.csv` — one row per published GAME CLASSIFICATION OPINION, 1992-09-14 to 2024-04-26. NO ENTITY COLUMN BY NATURE - the subject is a GAME, so record_scope = indian_country on all 122 (ADR-010) and this table must NOT be scored on entity attachment
  - primary key: `opinion_id`  (validated unique)
  - join cardinality: `opinion_id` → one row(s) per value (measured max 1)
  - declared by: code/586 assertion; INT-2 2026-09-01
- `nigc_indian_lands_opinions.csv` — one row per published INDIAN LANDS OPINION, 1997-08-12 to 2026-05-18. A tribe with four parcels has four rows
  - primary key: `opinion_id`  (validated unique)
  - join cardinality: `opinion_id` → one row(s) per value (measured max 1)
  - declared by: code/586 assertion; INT-2 2026-09-01
- `nigc_management_contract_approvals.csv` — one row per Chair-approved MANAGEMENT CONTRACT DOCUMENT, 55 tribes. A SNAPSHOT, not a history - NIGC posts the current roster only and publishes no retired contracts, so absence here is not evidence a contract never existed
  - primary key: `action_id`  (validated unique)
  - join cardinality: `action_id` → one row(s) per value (measured max 1)
  - declared by: code/586 assertion; INT-2 2026-09-01
- `nigc_region_assignments.csv` — one row per (facility, NIGC region assignment start year)
  - primary key: `facility_id` + `effective_start_year`  (validated unique)
  - join cardinality: `administrative_region_id` → many row(s) per value (measured max 190), `cedar_uid` → many row(s) per value (measured max 81), `facility_id` → many row(s) per value (measured max 4), `tribe_id` → many row(s) per value (measured max 81)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nigc_regional_ggr.csv` — one row per (NIGC region, fiscal year) gross gaming revenue figure
  - primary key: `administrative_region_id` + `fiscal_year`  (validated unique)
  - join cardinality: `administrative_region_id` → many row(s) per value (measured max 10)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nigc_revenue_bands.csv` — one row per (fiscal year, revenue band) in the NIGC band table
  - primary key: `band_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `state_gaming_observations.csv` — one row per state-published gaming observation (facility or tribe x metric x period)
  - primary key: `observation_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 78), `facility_id` → many row(s) per value (measured max 14), `tribe_id` → many row(s) per value (measured max 78)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `wa_machine_allocations.csv` — one row per Washington machine-allocation record for a tribe over an interval
  - primary key: `allocation_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 3), `tribe_id` → many row(s) per value (measured max 3)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json

## Entity spine, identifiers and reference  (`_entity_layer`, shelf: infrastructure)

Rebuild: `py -3 code/build.py run _entity_layer --execute` — 48 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `admin_region_assignments.csv` | shippable | `administrative_region_id` | — | — |
| `admin_region_overlap_derived.csv` | shippable | — | — | — |
| `admin_region_systems.csv` | shippable | — | — | — |
| `admin_regional_observations.csv` | shippable | `administrative_region_id` | — | — |
| `admin_regions.csv` | shippable | `administrative_region_id` | — | — |
| `bie_uio_dollars_by_entity.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `bie_uio_identifier_links.csv` | internal-by-decision | `tribe_id` `cedar_uid` `uei` `ein` | — | — |
| `cedar_correction_register.csv` | shippable | `entity_id` | — | — |
| `cedar_entity_freshness.csv` | UNDOCUMENTED | `cedar_uid` | — | — |
| `cedar_entity_identity_crosswalk.csv` | shippable | `cedar_uid` | — | — |
| `cedar_entity_spine.csv` | unregistered | `tribe_id` `cedar_uid` | `01_build_entity_spine.py` | `503_identity.py` `61_add_nho_intertribal_to_spine.py` |
| `cedar_identifier_graph_edges.csv` | shippable | — | `169_build_identifier_graph.py` | `741_hub_grain_and_rebuild.py` |
| `cedar_identifier_graph_nodes.csv` | shippable | — | — | — |
| `cedar_identifier_ledger.csv` | unregistered | `tribe_id` | — | — |
| `cedar_identifier_ledger_final.csv` | shippable | `tribe_id` `cedar_uid` | `09_import_rulings.py` | `50_fix_kootenai_conflation.py` |
| `cedar_identifier_ledger_tiered.csv` | internal-by-decision | `tribe_id` `cedar_uid` | `03_apply_exclusions_and_tier.py` | `50_fix_kootenai_conflation.py` `64_fix_village_government_misattribution.py` |
| `cedar_identifier_propagation.csv` | shippable | — | — | — |
| `cedar_publishable_identifiers.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `cedar_ruling_ledger_consolidated.csv` | shippable | — | — | — |
| `cedar_rulings.csv` | unregistered | `cage_code` | — | — |
| `cross_dataset_ruling_map.csv` | shippable | — | — | — |
| `entity_aliases.csv` | shippable | `cedar_uid` `entity_id` | `97_build_aliases_and_relationships.py` | `418_build_entity_alias_layer.py` |
| `entity_candidates_new.csv` | internal-by-decision | `cedar_uid` | — | — |
| `entity_candidates_rejected.csv` | internal-by-decision | `cedar_uid` | — | — |
| `entity_evidence_profile.csv` | internal-by-decision | — | `151_rebuild_entity_evidence_profile.py` | `110_build_harmonized_views.py` |
| `entity_hierarchy.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `entity_name_harvest.csv` | internal-by-decision | — | — | — |
| `entity_relationships.csv` | shippable | — | `97_build_aliases_and_relationships.py` | `310_correct_overstated_owned_by_edge_tiers.py` |
| `entity_year_coverage.csv` | internal-by-decision | — | — | — |
| `entity_year_panel.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `federal_recognition_events.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `federal_recognition_roster.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `foia_discovery_targets.csv` | shippable | — | — | — |
| `foia_request_index.csv` | shippable | `cedar_uid` | — | — |
| `intertribal_memberships.csv` | shippable | — | — | — |
| `intertribal_orgs.csv` | shippable | `ein` | — | — |
| `native_fi_roster.csv` | shippable | — | — | — |
| `nho_doi_notification_roster.csv` | shippable | `cedar_uid` `uei` `cage_code` | — | — |
| `nho_ito_spine_crosswalk.csv` | internal-by-decision | `tribe_id` `cedar_uid` | `61_add_nho_intertribal_to_spine.py` | `163_promote_nho_universe_in_place.py` |
| `nho_ownership_changes.csv` | shippable | `cedar_uid` | — | — |
| `nho_parents.csv` | internal-by-decision | — | — | — |
| `nho_register.csv` | shippable | `ein` | — | — |
| `nho_verified_entities.csv` | shippable | `cedar_uid` `uei` `cage_code` | — | — |
| `tcu_cdfi_added.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `tcu_cdfi_ownership_evidence.csv` | shippable | — | — | — |
| `tcu_roster.csv` | shippable | — | — | — |
| `visitor_access_events.csv` | shippable | `cedar_uid` | — | — |
| `visitor_record_foia_requests.csv` | shippable | `cedar_uid` | — | — |

Declared grain — validated against the file on every run:

- `admin_region_assignments.csv` — one row per assignment of a subject (entity, facility or other keyed subject) to one administrative region, with the interval it held
  - primary key: `assignment_id`  (validated unique)
  - join cardinality: `administrative_region_id` → many row(s) per value (measured max 465)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `admin_region_overlap_derived.csv` — one row per derived pair of administrative regions from two different region systems that share tribes
  - primary key: `administrative_region_id_a` + `administrative_region_id_b`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `admin_region_systems.csv` — one row per administrative region SYSTEM (an agency's way of dividing the country), not per region
  - primary key: `region_system_code`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `admin_regional_observations.csv` — one row per statistic published at the level of one administrative region
  - primary key: `observation_id`  (validated unique)
  - join cardinality: `administrative_region_id` → many row(s) per value (measured max 4)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `admin_regions.csv` — one row per administrative region within a system
  - primary key: `administrative_region_id`  (validated unique)
  - join cardinality: `administrative_region_id` → one row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `bie_uio_dollars_by_entity.csv` — one row per BIE school or Urban Indian Organisation entity, with its dollars summed across sources
  - primary key: `tribe_id`  (validated unique)
  - join cardinality: `cedar_uid` → one row(s) per value (measured max 1), `tribe_id` → one row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `cedar_correction_register.csv` — one row per recorded correction action - what was withdrawn or repointed, in which table, and why
  - primary key: `correction_id`  (validated unique)
  - join cardinality: `entity_id` → many row(s) per value (measured max 94)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `cedar_entity_identity_crosswalk.csv` — one row per mapping between a Cedar entity and one external identifier in one external scheme
  - primary key: `crosswalk_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 160)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `cedar_entity_spine.csv` — one row per canonical Native entity (hub). Sub-hubs (registrations, facilities) are NEVER rows here - IDENTIFIER_STANDARD.md
  - primary key: `tribe_id`  (validated unique)
  - join cardinality: `cedar_uid` → one row(s) per value (measured max 1), `tribe_id` → one row(s) per value (measured max 1)
  - declared by: docs/IDENTIFIER_STANDARD.md 1
- `cedar_identifier_graph_edges.csv` — one row per ASSERTED EDGE: an IDENTITY edge (two identifiers are the same entity), an ATTRIBUTION edge (an identifier belongs to a Native entity), or a BLOCK edge (a tier-X negative ruling bars an identifier, `to_node` empty by design). IDENTITY and ATTRIBUTION edges are COLLAPSED to one row per pair by the builder, so their `asserting_source` is a pipe-joined list and `n_asserting_sources` is its length. BLOCK edges are NOT collapsed - each names the row that asserted it in `asserting_row_ref`, and one identifier blocked because it appears in 860 target rows is 860 edges, which is why `n_asserting_sources` is 1 on every one of them and must NEVER be read as agreement between sources. `asserting_row_ref` is blank on IDENTITY and ATTRIBUTION edges, where the collapse already made the pair unique. A DEGREE COUNT OVER THIS FILE IS NOT A COUNT OF DISTINCT ASSERTIONS: collapse BLOCK edges to distinct `from_node` first - 4,777 identifiers over 7,997 ruling-map block edges
  - primary key: `edge_kind` + `from_node` + `to_node` + `asserting_source` + `asserting_row_ref` + `edge_tier` + `method`  (validated unique)
  - join cardinality: `from_node` → many row(s) per value (measured max 1095)
  - declared by: workstream GRAIN-HUB 2026-09-01: key confirmed unique on the FULL 46,820-row file, 0 literal duplicate rows, after code/741_hub_grain_and_rebuild.py edges spliced the ruling-map BLOCK slice with `asserting_row_ref`. 169 now writes the column itself, so a rebuild reproduces it and the splice is a one-time backfill
- `cedar_identifier_graph_nodes.csv` — one row per identifier observed anywhere in Cedar, with its resolution and its block - docs/IDENTIFIER_GRAPH_BUILD_LOG.md
  - primary key: `node`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `cedar_identifier_ledger_final.csv` — one row per (identifier, entity, evidence) claim; tier X rows are REFUTATIONS and must not be dropped by consumers
  - primary key: `identifier_type` + `identifier` + `tribe_id` + `attribution_method` + `evidence_url` + `verified_date`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 159), `identifier` → many row(s) per value (measured max 2), `tribe_id` → many row(s) per value (measured max 159)
  - declared by: docs/IDENTIFIER_STANDARD.md 3
- `cedar_identifier_propagation.csv` — one row per (dataset, identifier) propagation proposal, with the path it travelled and the tier that path earns
  - primary key: `dataset` + `identifier`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `cedar_publishable_identifiers.csv` — one row per identifier Cedar may publish, with the entity it is attributed to and the evidence tier
  - primary key: `identifier`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 35), `tribe_id` → many row(s) per value (measured max 35)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `cedar_ruling_ledger_consolidated.csv` — one row per (SUBJECT, source row that recorded a verdict about it). NOT one row per ruling and NOT one row per subject: 13,440 subjects over 43,321 rows, and one subject carries up to 2,778 rows because that many distinct source rows assert something about it. Those repeats are the CORROBORATION - N independent rows agreeing is the evidence, and collapsing them would delete it. `source_row_ordinal` is the 0-based data row index inside `source_file` as 173 swept it. One source row appears once per SUBJECT it names, so a row carrying two identifiers produces two rows under one ordinal and they differ in `subject_key`. `outcome` and `status` are properties of the SUBJECT repeated on every one of its rows, never of the row: counting rows by `status` counts sources, not decisions, and `status = CONFLICT_NOT_APPLIED` means NEITHER verdict was applied
  - primary key: `subject_key` + `source_file` + `source_row_ordinal`  (validated unique)
  - join cardinality: `resolved_tribe_id` → many row(s) per value (measured max 661), `subject_key` → many row(s) per value (measured max 2778)
  - declared by: workstream GRAIN-HUB 2026-09-01: key confirmed unique on the FULL 43,321-row file, 0 literal duplicate rows. Re-measured by code/741_hub_grain_and_rebuild.py verify
- `cross_dataset_ruling_map.csv` — one row per APPLICATION of one ruling to ONE ROW of one target dataset, per channel. NOT one row per ruling and NOT one row per (ruling, dataset): a ruling that reaches 2,776 rows of federal_funding_transactions.csv is 2,776 rows here, and that count IS the reach this table exists to measure. `target_row_ordinal` is the 0-based position of the target row inside `source_file` AT SCAN TIME, not a durable identifier - `target_row_hash` (sha1-16 of the target row's full content) is what survives a rebuild of the target table. `target_row_key` quotes the target row's own key where that table has one and is BLANK where it does not, which is a statement about the target, not a gap here. This table carries no money and must never be joined to a transaction table and summed: one target row can appear under both an IDENTITY and an EXCLUSION channel and under more than one identifier type
  - primary key: `source_file` + `target_row_ordinal` + `identifier_type` + `channel`  (validated unique)
  - join cardinality: `identifier` → many row(s) per value (measured max 2776)
  - declared by: workstream GRAIN-HUB 2026-09-01: the key is unique by construction - 23 refuses to write if it is not - and confirmed unique on the FULL 22,936-row file. Re-measured by code/741_hub_grain_and_rebuild.py verify
- `entity_aliases.csv` — one row per alias binding: one name form for one entity from one source system
  - primary key: `alias_id`  (**VALIDATION FAILED — see violations**)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 20), `entity_id` → many row(s) per value (measured max 20)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `entity_hierarchy.csv` — one row per entity, carrying its parent and ultimate parent - docs/ALIAS_RELATIONSHIP_MIGRATION_LOG.md
  - primary key: `tribe_id`  (validated unique)
  - join cardinality: `cedar_uid` → one row(s) per value (measured max 1), `tribe_id` → one row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `entity_relationships.csv` — one row per directed relationship between two entities, with the interval and the evidence
  - primary key: `relationship_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `entity_year_panel.csv` — one row per (entity, calendar year). A JOIN ON cedar_uid ALONE FANS OUT ACROSS 28 YEARS - summing a dollar column after that join multiplies it
  - primary key: `tribe_id` + `year`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 28), `tribe_id` → many row(s) per value (measured max 28)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `federal_recognition_events.csv` — one row per federal recognition status change, identified by the entity and the Federal Register notice that effected it - docs/RECOGNITION_HISTORY_BUILD_LOG.md
  - primary key: `entity_key` + `fr_document_number`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 4), `tribe_id` → many row(s) per value (measured max 4)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `federal_recognition_roster.csv` — one row per (recognition notice, listed entry) - the entry as printed, not the entity - docs/RECOGNITION_HISTORY_BUILD_LOG.md
  - primary key: `fr_document_number` + `entry_raw`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 54), `tribe_id` → many row(s) per value (measured max 54)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `foia_discovery_targets.csv` — one row per discovered FOIA-related URL, with what it was found on and whether it fetched
  - primary key: `url`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `foia_request_index.csv` — one row per FOIA log entry AS PARSED - which is one row per REQUEST except where the parser split one entry in two, and the table names every one of those itself: `foia_request_id` repeats 381 times over 9,481 rows and EVERY row in a collision group carries `control_number_appears_more_than_once` in `parse_quality_reason` while no row outside one does. So a COUNT OF ROWS IS NOT A COUNT OF REQUESTS - 9,100 distinct ids - and a buyer counting requests must collapse on `foia_request_id`. `request_description` is blank on 49 rows, where the source log records none, and blank is a value of this key. `tribe_entity_id` and `cedar_uid` are blank on 9,137 of 9,481 rows: a FOIA request usually names no tribe, which is scope, not an unresolved link
  - primary key: `foia_request_id` + `request_description`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 55), `foia_request_id` → many row(s) per value (measured max 4), `tribe_entity_id` → many row(s) per value (measured max 55)
  - declared by: workstream GRAIN-HUB 2026-09-01: key confirmed unique on the FULL 9,481-row file, 0 literal duplicate rows. The 381 id collisions are a PARSE DEFECT for the owner of 136_build_congressional_correspondence_and_foia_index.py, evidenced by the table's own parse_quality_reason; the declaration records the row that exists rather than pretending the id is unique
- `intertribal_memberships.csv` — one row per (intertribal organisation, member entity as named, observation year)
  - primary key: `org_id` + `member_entity_name` + `year_observed`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `intertribal_orgs.csv` — one row per intertribal organisation
  - primary key: `proposed_id`  (validated unique)
  - join cardinality: `ein` → many row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `native_fi_roster.csv` — one row per Native financial institution. The roster mints no id: `name` IS the key, so a renamed institution changes key
  - primary key: `name`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nho_doi_notification_roster.csv` — one row per Native Hawaiian Organisation on the DOI notification list
  - primary key: `nho_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nho_ownership_changes.csv` — one row per recorded ownership-change event affecting an NHO firm
  - primary key: `event_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 9)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nho_register.csv` — one row per Native Hawaiian Organisation in the register
  - primary key: `proposed_id`  (validated unique)
  - join cardinality: `ein` → many row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nho_verified_entities.csv` — one row per verified NHO contracting firm, keyed by its UEI
  - primary key: `uei`  (validated unique)
  - join cardinality: `cage_code` → one row(s) per value (measured max 1), `uei` → one row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `tcu_cdfi_added.csv` — one row per entity added to the spine by the TCU/CDFI pass
  - primary key: `tribe_id`  (validated unique)
  - join cardinality: `cedar_uid` → one row(s) per value (measured max 1), `tribe_id` → one row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `tcu_cdfi_ownership_evidence.csv` — one row per OCCURRENCE of one evidence sentence on one retrieved page: (institution, layer, capture pattern, page URL, character offset of the sentence in that page). A page that states the same sentence twice - once in a nav or banner block and once in the body - yields two rows, and both are real: First State Bank's service sentence and Little Priest Tribal College's charter sentence are the measured cases. `captured_owner` is BLANK on every `serves` row by design, because 'we serve members of all tribes' names no owner; a blank there is a refusal to infer ownership from service, not a gap. This is EVIDENCE, not a roster: it is not one row per institution, and counting rows counts quotes
  - primary key: `institution` + `layer` + `pattern` + `evidence_url` + `quote_char_offset`  (validated unique)
  - declared by: workstream GRAIN-HUB 2026-09-01: `quote_char_offset` added to 73_add_tcu_and_cdfi.py find_ownership/find_serves and the table re-extracted from the CACHED pages with no network. 130 rows before and 130 after, content multiset IDENTICAL to the .bak_2026-09-01_pre73, 4 literal duplicates to 0. 73 refuses to write if the key is not unique
- `tcu_roster.csv` — one row per tribal college or university. No id is minted; `name` is the key
  - primary key: `name`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `visitor_access_events.csv` — one row per visitor-access event recovered from an agency visitor record
  - primary key: `visitor_access_event_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `visitor_record_foia_requests.csv` — one row per FOIA log entry AS PARSED, for requests seeking visitor or calendar records. Same shape and same defect as foia_request_index.csv from a different builder: `foia_request_id` collides 22 times over 667 rows and `request_description_verbatim` differs in 22 of the 22 groups, so a count of rows is not a count of requests - 645 distinct ids. `tribe_entity_id` and `cedar_uid` are blank on 654 of 667 rows: these are requests filed with an agency, most of which name no tribe. `discovery_role` and `channel` describe how Cedar FOUND the request, not anything the agency recorded
  - primary key: `foia_request_id` + `request_description_verbatim`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 6), `foia_request_id` → many row(s) per value (measured max 2), `tribe_entity_id` → many row(s) per value (measured max 6)
  - declared by: workstream GRAIN-HUB 2026-09-01: key confirmed unique on the FULL 667-row file with NO blank component and 0 literal duplicate rows. The 22 id collisions are a parse defect for the owner of 146; re-measured by code/741_hub_grain_and_rebuild.py verify
