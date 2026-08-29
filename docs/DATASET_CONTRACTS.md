# Dataset contracts - generated, do not hand-edit

*Generated 2026-08-29 by `code/512_build_dataset_contracts.py` (mission Phase 1). Regenerate rather than edit; `verify` exits 1 when the world breaks a contract, and 62 gates on it.*

**13 collections, 255 tables claimed, 0 orphaned shippable tables, 0 violations.**

**Grain: 182 of 210 shippable tables declare and VALIDATE a row grain, a primary key and a join cardinality; 28 do not.** A declared grain the data contradicts is a release-blocking violation, listed below. An unstated grain is ratcheted by `62_no_regression_check.contract_grain_unstated_shippable`: the count may only fall, and a new shippable table that lands without one fails the gate that day.

<details><summary>Shippable tables with an UNSTATED grain (28) - a buyer cannot join these safely</summary>

- `admin_appeal_positions.csv` — the file has ONE row. `matter_id` and `cedar_uid` are unique, and so is every other column - one row proves nothing. QUESTION: is a row a POSITION taken by one organisation in one matter (in which case position_id is the key and it is empty of evidence), or one row per matter?
- `cedar_identifier_graph_edges.csv`
- `cedar_ruling_ledger_consolidated.csv`
- `congressional_correspondence_log.csv` — the file has ZERO rows. Every candidate key is vacuously unique, so the data cannot evidence a grain. QUESTION: is this table meant to ship empty, and what is one row when it fills?
- `contractor_ranking.csv` — the only unique keys over 1,429 rows require `firm_transaction_rows` - a MEASURE. A key that needs a count in it is not a grain. (owner_entity_id, operating_company_uei, link_identifier) collides 30 times. QUESTION: is a row an (owner, operating company, identifier link) triple, and if so what distinguishes the 30 collisions?
- `cross_dataset_ruling_map.csv`
- `deals_2026_ytd_additions.csv` — the file has ZERO rows (the build log records 1 row added, which is not what is on disk). QUESTION: was the YTD additions file consumed into deals_classified.csv and left as a stub, or did a rebuild empty it?
- `faads_transactions.csv`
- `faads_transactions_all_agencies.csv`
- `fac_audit_sefa_gaming_programs.csv` — the file has ONE row. Uniqueness is vacuous. QUESTION: is a row a (report, federal program) line off the SEFA, so that report_id repeats once a second program is parsed?
- `ferc_docket_filings.csv`
- `ferc_ex_parte_communications.csv` — `ferc_ex_parte_id` has 56 collisions over 713 rows, and adding accession_number, docket_number or the FR document number removes none of them - the colliding rows differ somewhere else. QUESTION: what distinguishes two rows sharing a ferc_ex_parte_id? Until that is named the table has no key.
- `foia_request_index.csv` — no key was found at any arity up to 6 over 9,481 rows. `foia_request_id` REPEATS 381 times; adding `status` still leaves 66 collisions; adding source_url, received_date and both `seeks_*` flags still leaves 8. QUESTION: is a row one FOIA request - in which case the 381 repeats are a defect and the id must be made unique - or one (request, matched tribe mention), in which case the key needs the entity column and should be stated?
- `fpds_uei_cage_map.csv` — a MAP that maps nothing uniquely: `uei` repeats 11,455 times over 29,981 rows and (uei, cage_code, source_file) still collides 4,680 times. The only unique key needs all six columns including first_year and last_year, and 22,518 rows have a blank cage_code. QUESTION: is a row a (UEI, CAGE) pair as OBSERVED in one source file and year-range - and if so should the year range be part of the published key - or is the table meant to be one row per UEI?
- `gaming_projections.csv` — docs/GAMING_NEPA_PILOT_LOG.md states the grain as 'one row per project x metric x geography x period'. The data CONTRADICTS it: that key collides 8 times over 116 rows, and adding `alternative` leaves 5. The only unique keys contain `value`, a measure. QUESTION: which column separates two projections of the same metric for the same project, geography and period - alternative, reported_or_calculated, or the source document?
- `hearing_bill_links.csv`
- `lobbying_registrant_native_ownership_evidence.csv`
- `native_bills_subject_sweep.csv`
- `native_passthrough.csv`
- `np_schedule_i_grants.csv`
- `prime_contracts.csv`
- `prime_contracts_archive_backfill.csv`
- `prime_contracts_entity_year.csv` — the table is NAMED entity-year and (tribe_id, fiscal_year) is NOT unique - 1,751 collisions over 8,464 rows; (cedar_uid, fiscal_year) collides identically. Uniqueness needs canonical_name AND confidence_tier as well. So one entity-year has several rows under different NAMES and tiers. QUESTION: is a row an entity-year (then the extra rows are a defect and anyone summing obligations_usd by tribe-year today DOUBLE-COUNTS), or is it deliberately entity x name-variant x year x tier? This is the single most consequential open question in the sweep.
- `subawards.csv`
- `tcu_cdfi_ownership_evidence.csv`
- `tribal_bond_issuances.csv` — `cusip` is BLANK on all 29 rows, so the natural key of a bond table is absent, and the only unique column is `notes`. QUESTION: can CUSIPs be backfilled, and until then is a row one issuance (issuer, issue_date, series) or one disclosure document?
- `tribal_resolution_financings.csv` — the file has ONE row. Uniqueness is vacuous. QUESTION: is a row one financing INSTRUMENT (instrument_number) or one tribal resolution?
- `visitor_record_foia_requests.csv` — the only unique key over 667 rows is `request_description_verbatim`, a free-text field. `foia_request_id` has 22 collisions. QUESTION: does one FOIA request legitimately appear once per agency or per discovery role, or is the id supposed to be unique?

</details>

## Federal Funding to Indian Country  (`funding`, shelf: standard)

Rebuild: `py -3 code/build.py run funding --execute` — 17 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `assistance_tribe_id_crosswalk.csv` | internal-by-decision | — | `152_build_assistance_id_crosswalk.py` | `503_identity.py` |
| `bie_uio_dollars_by_entity.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `bie_uio_identifier_links.csv` | internal-by-decision | `tribe_id` `cedar_uid` `uei` `ein` | — | — |
| `faads_attribution_audit_sample.csv` | internal-by-decision | `tribe_id` `cedar_uid` | — | — |
| `faads_entity_attribution.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `faads_identifier_coverage_by_agency_year.csv` | internal-by-decision | — | — | — |
| `faads_transactions.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `faads_transactions_all_agencies.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `federal_funding_rulings_from_dofile.csv` | unregistered | — | — | — |
| `federal_funding_transactions.csv` | shippable | `tribe_id` `cedar_uid` | `24_funding_merge.py` | `115_pull_assistance_archive.py` `335_harmonize_assistance_seams_in_place.py` `336_correct_scheme_resolution_by_spine_membership.py` `503_identity.py` |
| `federal_funding_tribe_year_panel.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
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
- `federal_funding_transactions.csv` — one row per federal assistance award TRANSACTION, across the union of the assistance and archive pulls
  - primary key: `assistance_transaction_unique_key`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 18574), `tribe_id` → many row(s) per value (measured max 12764)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `federal_funding_tribe_year_panel.csv` — one row per (entity, federal fiscal year). A join on tribe_id alone fans out across years
  - primary key: `tribe_id` + `fiscal_year`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 32), `tribe_id` → many row(s) per value (measured max 16)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `funding_identifier_netnew_ueis.csv` — one row per recipient UEI that the funding pull added and no other Cedar source had
  - primary key: `recipient_uei`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `inflation_deflator.csv` — one row per year of the GDP deflator series
  - primary key: `year`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `native_passthrough_pairs.csv` — one row per (paying entity, receiving entity) pair, rolled up across their subawards
  - primary key: `from_tribe_id` + `to_tribe_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json

## Federal Register  (`federal-register`, shelf: standard)

Rebuild: `py -3 code/build.py run federal-register --execute` — 26 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `consultation_agency_coverage.csv` | UNDOCUMENTED | — | — | — |
| `consultation_events.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `correspondence_foia_source_coverage.csv` | shippable | — | — | — |
| `federal_actions.csv` | shippable | — | — | — |
| `federal_actions_entity_bridge.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `federal_actions_raw.csv` | shippable | — | — | — |
| `fr_abstract_availability_year.csv` | shippable | — | — | — |
| `fr_consultation_by_agency.csv` | shippable | — | — | — |
| `fr_consultation_notices.csv` | shippable | — | — | — |
| `fr_consultation_referenced.csv` | shippable | — | — | — |
| `fr_consultation_year.csv` | shippable | — | — | — |
| `fr_content_classification.csv` | shippable | — | — | — |
| `fr_ex_parte_notices.csv` | shippable | — | — | — |
| `fr_ex_parte_parties.csv` | shippable | `cedar_uid` | — | — |
| `fr_ex_parte_party_entity_links.csv` | shippable | `cedar_uid` | — | — |
| `fr_recognized_entities.csv` | internal-by-decision | — | — | — |
| `fr_relevance_stratum_audit.csv` | internal-by-decision | — | — | — |
| `fr_relevance_tier_year.csv` | shippable | — | — | — |
| `fr_theme_year.csv` | shippable | — | — | — |
| `nepa_administrative_record_parties.csv` | shippable | `cedar_uid` | — | — |
| `nepa_eplanning_projects.csv` | shippable | — | — | — |
| `nepa_project_documents.csv` | shippable | — | — | — |
| `nepa_source_coverage.csv` | internal-by-decision | — | — | — |
| `section_106_consultation_events.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `section_106_project_parties.csv` | shippable | `cedar_uid` | — | — |
| `section_106_source_coverage.csv` | shippable | — | — | — |

Declared grain — validated against the file on every run:

- `consultation_events.csv` — one row per (consultation event, participant as published). `consultation_event_id` alone is NOT unique - an event with several named participants has one row each, and 1,006 rows name no participant at all
  - primary key: `consultation_event_id` + `participant_name_as_published`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 170), `tribe_id` → many row(s) per value (measured max 170)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `correspondence_foia_source_coverage.csv` — one row per source URL checked for congressional-correspondence coverage
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
- `fr_consultation_referenced.csv` — one row per Federal Register document that REFERENCES a consultation having been undertaken
  - primary key: `document_number`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_consultation_year.csv` — one row per publication year of consultation counts
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
- `fr_ex_parte_party_entity_links.csv` — one row per resolved link from an ex parte party to a Cedar entity
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
| `bill_votes.csv` | shippable | — | — | — |
| `bill_votes_entity_bridge.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `bill_votes_official_verification.csv` | shippable | — | — | — |
| `congressional_correspondence_log.csv` | shippable | `cedar_uid` | — | — |
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
| `deals_ancsa_portal_additions.csv` | shippable | — | — | — |
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

## NAGPRA  (`nagpra`, shelf: standard)

Rebuild: `py -3 code/build.py run nagpra --execute` — 4 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `fr_nagpra_title_index.csv` | shippable | — | — | — |
| `fr_nagpra_title_index_year.csv` | shippable | — | — | — |
| `nagpra_notice_entity_bridge.csv` | shippable | `tribe_id` | — | — |
| `nagpra_notices.csv` | shippable | — | — | — |

Declared grain — validated against the file on every run:

- `fr_nagpra_title_index.csv` — one row per Federal Register document identified as a NAGPRA notice by its title
  - primary key: `document_number`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `fr_nagpra_title_index_year.csv` — one row per publication year of NAGPRA notice counts
  - primary key: `publication_year`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nagpra_notice_entity_bridge.csv` — one row per (notice, relationship, named party) - docs/NAGPRA_BUILD_LOG.md. (document_number, party) alone collides 12,800 times because one party can hold several relationships to one notice
  - primary key: `document_number` + `relationship` + `party_name_verbatim`  (validated unique)
  - join cardinality: `tribe_id` → many row(s) per value (measured max 900)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `nagpra_notices.csv` — one row per NAGPRA notice - docs/NAGPRA_BUILD_LOG.md
  - primary key: `document_number`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json

## Lobbying  (`lobbying`, shelf: standard)

Rebuild: `py -3 code/build.py run lobbying --execute` — 37 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `admin_appeal_decisions.csv` | shippable | — | `144_build_admin_appeals.py` | `168_link_adjudication_hubs.py` |
| `admin_appeal_parties.csv` | shippable | `cedar_uid` | `144_build_admin_appeals.py` | `168_link_adjudication_hubs.py` |
| `admin_appeal_positions.csv` | shippable | `cedar_uid` | — | — |
| `advocacy_passthrough.csv` | shippable | `cedar_uid` | — | — |
| `advocacy_passthrough_2026-08-07.csv` | shippable | `cedar_uid` | — | — |
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
| `fr_ex_parte_parties.csv` | shippable | `cedar_uid` | — | — |
| `fr_ex_parte_party_entity_links.csv` | shippable | `cedar_uid` | — | — |
| `hearing_appearances.csv` | shippable | `cedar_uid` `entity_id` | `98_build_oira_and_hearings.py` | `400_promote_stranded_hearing_appearances.py` |
| `hearing_bill_links.csv` | shippable | — | — | — |
| `lobbying_client_attribution.csv` | internal-by-decision | `tribe_id` `cedar_uid` | — | — |
| `lobbying_disclosure_verbosity_year.csv` | shippable | — | — | — |
| `lobbying_issue_families_filing.csv` | shippable | `cedar_uid` `entity_id` | — | — |
| `lobbying_issue_family_year.csv` | shippable | — | — | — |
| `lobbying_registrant_client_relationships.csv` | shippable | `cedar_uid` | — | — |
| `lobbying_registrant_concentration.csv` | shippable | — | — | — |
| `lobbying_registrant_identifiers.csv` | shippable | — | — | — |
| `lobbying_registrant_native_ownership_evidence.csv` | shippable | `cedar_uid` | — | — |
| `lobbying_registrants.csv` | shippable | — | — | — |
| `lobbying_target_entities.csv` | shippable | — | — | — |
| `lobbying_unmatched_clients.csv` | internal-by-decision | — | — | — |
| `native_entity_lobbying_disclosures.csv` | shippable | `cedar_uid` `entity_id` | `05_match_filings_v2.py` | `350_withdraw_false_lobbying_attributions.py` `65_lobbying_organization_type_guard.py` |
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
- `ferc_docket_parties.csv` — one row per party on a FERC docket
  - primary key: `ferc_docket_party_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 14)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
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
- `fr_ex_parte_party_entity_links.csv` — one row per resolved link from an ex parte party to a Cedar entity
  - primary key: `link_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 2)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `hearing_appearances.csv` — one row per witness appearance at a congressional hearing
  - primary key: `hearing_appearance_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 78), `entity_id` → many row(s) per value (measured max 78)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
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
- `lobbying_registrants.csv` — one row per Senate LDA registrant_id - docs/LOBBYING_REGISTRANT_BUILD_LOG.md
  - primary key: `registrant_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `lobbying_target_entities.csv` — one row per government entity as written on the filings
  - primary key: `government_entity_as_filed`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `native_entity_lobbying_disclosures.csv` — one row per LDA filing attributed to a Native entity
  - primary key: `filing_uuid`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 400), `entity_id` → many row(s) per value (measured max 400)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
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
| `prime_contracts.csv` | shippable | `tribe_id` `cedar_uid` `cage_code` | `40_build_prime_contracts.py` | `207_normalize_extent_competed.py` |
| `prime_contracts_archive_backfill.csv` | shippable | `tribe_id` `cedar_uid` `cage_code` | — | — |
| `prime_contracts_awards.csv` | shippable | `tribe_id` `cedar_uid` `cage_code` | — | — |
| `prime_contracts_entity_year.csv` | shippable | `tribe_id` `cedar_uid` | `40_build_prime_contracts.py` | `131_merge_archive_backfill.py` |
| `prime_contracts_published.csv` | shippable | `tribe_id` `cedar_uid` `cage_code` | — | — |
| `sam_prime_contracts_fy2000_2007.csv` | shippable | `cage_code` | — | — |
| `sam_prime_contracts_fy2000_2007_PUBLISHABLE.csv` | shippable | `cage_code` | — | — |
| `sam_prime_contracts_fy2000_2007_reconciliation.csv` | internal-by-decision | — | — | — |

Declared grain — validated against the file on every run:

- `fpds_uei_edges.csv` — one row per DECLARED (child_uei, parent_uei, edge_type) - literal pairs observed on transactions; connections, not a verified tree
  - primary key: `child_uei` + `parent_uei` + `edge_type`  (validated unique)
  - declared by: docs/HIERARCHY_MODEL.md
- `prime_contracts_awards.csv` — one row per CONTRACT (award), rolled up across its transactions - not one row per transaction
  - primary key: `contract_number`  (validated unique)
  - join cardinality: `cage_code` → many row(s) per value (measured max 85976), `cedar_uid` → many row(s) per value (measured max 55184), `tribe_id` → many row(s) per value (measured max 55184)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
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
| `subawards.csv` | shippable | `cedar_uid` | `20_build_subcontracts.py` | `121_pull_subawards_api.py` `250_demote_stale_tierA_subaward_rows.py` `45_promote_subawards.py` |

Declared grain — validated against the file on every run:

- `prime_sub_network.csv` — one row per (prime UEI, sub UEI) edge, rolled up across subawards
  - primary key: `prime_uei` + `sub_uei`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `subaward_entity_rollup.csv` — one row per entity, rolled up across both sides of the subaward network
  - primary key: `tribe_id`  (validated unique)
  - join cardinality: `cedar_uid` → one row(s) per value (measured max 1), `tribe_id` → one row(s) per value (measured max 1)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json

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
| `anc_ceiling_roster.csv` | shippable | `uei` `cage_code` | — | — |
| `ancsa_filings_index.csv` | shippable | — | — | — |
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
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 489), `entity_id` → many row(s) per value (measured max 489)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `resource_revenue.csv` — one row per resource revenue event as recorded by its source system
  - primary key: `resource_revenue_event_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 489)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
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

## Gaming Intelligence  (`gaming`, shelf: grove)

Rebuild: `py -3 code/build.py run gaming --execute` — 53 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `ca_gaming_facilities_official.csv` | shippable | `tribe_id` `cedar_uid` `facility_id` | `103_build_california_gaming.py` | `266_apply_gaming_hub_spillover_rulings.py` |
| `ca_gaming_payments.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `compact_events.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `compact_id` | — | — |
| `compact_obligation_tribal_agency_bridge.csv` | shippable | `tribe_id` `cedar_uid` `compact_id` | — | — |
| `compact_required_reports.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `compact_id` | — | — |
| `compact_structured_terms.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `compact_id` | — | — |
| `compact_terms.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `compact_id` | — | — |
| `compact_versions.csv` | shippable | `compact_id` | — | — |
| `compacts.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `compact_id` | — | — |
| `digital_gaming_relationships.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `facility_id` | — | — |
| `digital_gaming_revenue.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `facility_id` | `119_build_digital_and_loyalty.py` | `174_backfill_digital_gaming_tiers.py` |
| `fac_audit_gaming_disclosures.csv` | shippable | `cedar_uid` `entity_id` | — | — |
| `fac_audit_sefa_gaming_programs.csv` | shippable | `cedar_uid` `entity_id` | — | — |
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
| `gaming_property_site_observations.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `facility_id` | — | — |
| `gaming_property_universe_events.csv` | shippable | `cedar_uid` `entity_id` `facility_id` | `89_nigc_map_wayback_universe.py` | `165_link_universe_events_to_hub.py` |
| `gaming_revenue_bounds.csv` | shippable | `tribe_id` `cedar_uid` `facility_id` | — | — |
| `gaming_source_claims.csv` | shippable | — | `91_build_nigc_declinations.py` | `100_finish_declinations_and_employment.py` `510_assertions.py` |
| `gaming_vendor_tribal_licenses.csv` | shippable | `cedar_uid` `entity_id` | — | — |
| `loyalty_program_property.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` `facility_id` | — | — |
| `loyalty_programs.csv` | shippable | `tribe_id` `cedar_uid` `entity_id` | — | — |
| `nigc_declination_letters.csv` | shippable | `cedar_uid` | `91_build_nigc_declinations.py` | `100_finish_declinations_and_employment.py` |
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
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 534), `tribe_id` → many row(s) per value (measured max 534)
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
- `nigc_declination_letters.csv` — one row per NIGC declination opinion
  - primary key: `cedar_opinion_id`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 7)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
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

Rebuild: `py -3 code/build.py run _entity_layer --execute` — 47 tables.

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
| `cedar_entity_identity_crosswalk.csv` | shippable | `cedar_uid` | — | — |
| `cedar_entity_spine.csv` | unregistered | `tribe_id` `cedar_uid` | `01_build_entity_spine.py` | `08_build_review_page.py` `115_pull_assistance_archive.py` `163_promote_nho_universe_in_place.py` `241_promote_individual_native_firms_in_place.py` `416_reconcile_spine_id_columns.py` `426_mint_bristol_bay_spine_entities.py` `503_identity.py` `51_add_anc_acronym_aliases.py` `52_add_village_corporations.py` `61_add_nho_intertribal_to_spine.py` `66_build_entity_hierarchy.py` `69_enrich_spine_from_federal_register.py` `71_fix_known_defects.py` `73_add_tcu_and_cdfi.py` `74_add_organization_acronyms.py` `75_add_bie_schools_and_uios.py` |
| `cedar_identifier_graph_edges.csv` | shippable | — | — | — |
| `cedar_identifier_graph_nodes.csv` | shippable | — | — | — |
| `cedar_identifier_ledger.csv` | unregistered | `tribe_id` | `01_build_entity_spine.py` | `03_apply_exclusions_and_tier.py` `510_assertions.py` |
| `cedar_identifier_ledger_final.csv` | shippable | `tribe_id` `cedar_uid` | `09_import_rulings.py` | `124_apply_rulings_in_place.py` `163_promote_nho_universe_in_place.py` `174_apply_rulings_to_source_tables.py` `241_promote_individual_native_firms_in_place.py` `50_fix_kootenai_conflation.py` `56_apply_agent_identifier_rulings.py` `63_cross_dataset_reconcile.py` `71_fix_known_defects.py` |
| `cedar_identifier_ledger_tiered.csv` | internal-by-decision | `tribe_id` `cedar_uid` | `03_apply_exclusions_and_tier.py` | `09_import_rulings.py` `50_fix_kootenai_conflation.py` `64_fix_village_government_misattribution.py` |
| `cedar_identifier_propagation.csv` | shippable | — | — | — |
| `cedar_publishable_identifiers.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `cedar_ruling_ledger_consolidated.csv` | shippable | — | — | — |
| `cedar_rulings.csv` | unregistered | `cage_code` | — | — |
| `cross_dataset_ruling_map.csv` | shippable | — | — | — |
| `entity_aliases.csv` | shippable | `cedar_uid` `entity_id` | `97_build_aliases_and_relationships.py` | `418_build_entity_alias_layer.py` |
| `entity_candidates_new.csv` | internal-by-decision | `cedar_uid` | — | — |
| `entity_candidates_rejected.csv` | internal-by-decision | `cedar_uid` | — | — |
| `entity_evidence_profile.csv` | internal-by-decision | `cedar_uid` | `151_rebuild_entity_evidence_profile.py` | `110_build_harmonized_views.py` |
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
- `entity_aliases.csv` — one row per alias binding: one name form for one entity from one source system
  - primary key: `alias_id`  (validated unique)
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
- `tcu_roster.csv` — one row per tribal college or university. No id is minted; `name` is the key
  - primary key: `name`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json
- `visitor_access_events.csv` — one row per visitor-access event recovered from an agency visitor record
  - primary key: `visitor_access_event_id`  (validated unique)
  - declared by: workstream-E grain sweep 2026-08-29: primary key confirmed unique on the FULL file; evidence in docs/schema/grain_evidence.json

> **NEVER RUN** for `cedar_entity_spine.csv`: 01_build_entity_spine.py: A full rebuild DROPS EVERY APPENDED ENTITY - the village corporations, NHOs, TCUs, CDFIs, BIE schools and UIOs added by ...

> **NEVER RUN** for `cedar_identifier_ledger.csv`: 01_build_entity_spine.py: A full rebuild DROPS EVERY APPENDED ENTITY - the village corporations, NHOs, TCUs, CDFIs, BIE schools and UIOs added by ...

> **NEVER RUN** for `cedar_identifier_ledger_final.csv`: 09_import_rulings.py: Rebuilds cedar_identifier_ledger_final.csv FROM the stale cedar_identifier_ledger_tiered.csv, which does not carry rows ...
