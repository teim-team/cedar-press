# Grain audit - what one row IS, table by table

*Generated 2026-09-02 by `code/512_build_dataset_contracts.py` (workstream E). Regenerate rather than edit. Measurements live in `docs/schema/grain_evidence.json`; re-measure with `py -3 code/512_build_dataset_contracts.py probe`.*

## Why this document exists

Cedar Press is sold to buyers who JOIN it. A table whose real grain is entity x UEI x year, joined on `cedar_uid` alone, silently multiplies every dollar in it. External review finding F9 named that failure; ADR-007 built the machinery that validates a declaration - and left **207 of 210 shippable tables with no declaration at all**. This is the sweep that reduces that number using evidence rather than guesswork.

## What was measured

For every undeclared shippable table the probe generated candidate keys from a sample and then **confirmed each one against the full file** - 207 tables, several GB. Uniqueness is hash-based for memory and every colliding hash is re-read and compared as a literal string, so a duplicate reported here is a literal duplicate. Sampling can only ever propose a false key (a key unique on the whole file is unique on every prefix of it); the full-file confirm is what kills those.

Three honest outcomes, and they are three different jobs:

| outcome | meaning | who acts |
|---|---|---|
| **DECLARED_VALIDATED** | a key measured unique on the full file, and the row meaning is stated | done - it is in `GRAIN` and re-validated on every run |
| **OPEN_WITH_EVIDENCE** | the data cannot say what one row is *meant* to be | an owner answers the named question |
| **DEFECTIVE** | the table has duplicate rows or a broken key | the pipeline owner fixes the DATA; a declaration cannot |

| | count |
|---|---:|
| shippable tables | 228 |
| **DECLARED_VALIDATED** | **221** |
| OPEN_WITH_EVIDENCE | 0 |
| DEFECTIVE | 0 |
| still unexplained | 7 |
| ratchet `contract_grain_unstated_shippable` | **7** (was 207) |

A declaration that the data contradicts is release-blocking through `contract_violations`; there are **11**.

## Per collection

### Federal Funding to Indian Country  (`funding`)

8 of 10 shippable tables declared.

| table | rows | outcome | primary key | max rows per join-key value |
|---|---:|---|---|---|
| `bie_uio_dollars_by_entity.csv` | 114 | DECLARED_VALIDATED | `tribe_id` | `cedar_uid`→1, `tribe_id`→1 |
| `faads_entity_attribution.csv` | 29,594 | DECLARED_VALIDATED | `faads_row_id` | `cedar_uid`→536, `tribe_id`→536 |
| `faads_transactions.csv` | 60,661 | DECLARED_VALIDATED | `assistance_transaction_unique_key` | `cedar_uid`→0, `tribe_id`→0 |
| `faads_transactions_all_agencies.csv` | 2,769,748 | DECLARED_VALIDATED | — | `cedar_uid`→0, `tribe_id`→0 |
| `federal_funding_transactions.csv` | 701,955 | **DECLARATION FAILED** | `assistance_transaction_unique_key` | `cedar_uid`→18,574, `tribe_id`→12,764 |
| `federal_funding_tribe_year_panel.csv` | 5,496 | **DECLARATION FAILED** | `tribe_id` + `fiscal_year` | `cedar_uid`→32, `tribe_id`→16 |
| `funding_identifier_netnew_ueis.csv` | 4,249 | DECLARED_VALIDATED | `recipient_uei` | — |
| `inflation_deflator.csv` | 27 | DECLARED_VALIDATED | `year` | — |
| `native_passthrough.csv` | 1,663 | DECLARED_VALIDATED | `source_dataset` + `subaward_source_record_id` | `from_tribe_id`→371, `to_tribe_id`→376 |
| `native_passthrough_pairs.csv` | 307 | DECLARED_VALIDATED | `from_tribe_id` + `to_tribe_id` | — |

### Federal Register  (`federal-register`)

22 of 22 shippable tables declared.

| table | rows | outcome | primary key | max rows per join-key value |
|---|---:|---|---|---|
| `consultation_events.csv` | 11,402 | DECLARED_VALIDATED | `consultation_event_id` + `participant_name_as_published` | `cedar_uid`→170, `tribe_id`→170 |
| `correspondence_foia_source_coverage.csv` | 124 | DECLARED_VALIDATED | `url` | — |
| `federal_actions.csv` | 156,772 | DECLARED_VALIDATED | `document_number` | — |
| `federal_actions_entity_bridge.csv` | 5,786 | DECLARED_VALIDATED | `document_number` + `tribe_id` | `cedar_uid`→165, `tribe_id`→165 |
| `federal_actions_raw.csv` | 156,772 | DECLARED_VALIDATED | `document_number` | — |
| `fr_abstract_availability_year.csv` | 33 | DECLARED_VALIDATED | `publication_year` | — |
| `fr_consultation_by_agency.csv` | 21 | DECLARED_VALIDATED | `normalized_department` | — |
| `fr_consultation_notices.csv` | 484 | DECLARED_VALIDATED | `document_number` | — |
| `fr_consultation_referenced.csv` | 1,829 | DECLARED_VALIDATED | `document_number` | — |
| `fr_consultation_year.csv` | 33 | DECLARED_VALIDATED | `publication_year` | — |
| `fr_content_classification.csv` | 156,452 | DECLARED_VALIDATED | `document_number` | — |
| `fr_ex_parte_notices.csv` | 7,820 | DECLARED_VALIDATED | `fr_ex_parte_notice_id` | — |
| `fr_ex_parte_parties.csv` | 112 | DECLARED_VALIDATED | `fr_ex_parte_party_id` | `cedar_uid`→0 |
| `fr_ex_parte_party_entity_links.csv` | 9 | DECLARED_VALIDATED | `link_id` | `cedar_uid`→2 |
| `fr_relevance_tier_year.csv` | 132 | DECLARED_VALIDATED | `publication_year` + `relevance_tier` | — |
| `fr_theme_year.csv` | 627 | DECLARED_VALIDATED | `publication_year` + `theme` | — |
| `nepa_administrative_record_parties.csv` | 36 | DECLARED_VALIDATED | `party_id` + `party_name_as_published` | `cedar_uid`→5 |
| `nepa_eplanning_projects.csv` | 312 | DECLARED_VALIDATED | `nepa_number` | — |
| `nepa_project_documents.csv` | 789 | DECLARED_VALIDATED | `nepa_number` + `document_name_verbatim` | — |
| `section_106_consultation_events.csv` | 1,363 | DECLARED_VALIDATED | `consultation_event_id` | `cedar_uid`→15, `tribe_id`→15 |
| `section_106_project_parties.csv` | 51 | DECLARED_VALIDATED | `party_id` | `cedar_uid`→0 |
| `section_106_source_coverage.csv` | 5 | DECLARED_VALIDATED | `source` | — |

### Congressional Votes and Proposed Legislation  (`legislation`)

11 of 11 shippable tables declared.

| table | rows | outcome | primary key | max rows per join-key value |
|---|---:|---|---|---|
| `bill_votes.csv` | 423 | DECLARED_VALIDATED | `vote_id` | — |
| `bill_votes_entity_bridge.csv` | 75 | DECLARED_VALIDATED | `vote_id` + `tribe_id` | `cedar_uid`→10, `tribe_id`→10 |
| `bill_votes_official_verification.csv` | 305 | DECLARED_VALIDATED | `vote_id` | — |
| `congressional_correspondence_systems.csv` | 257 | DECLARED_VALIDATED | `system_id` + `verbatim_quote` | — |
| `member_positions.csv` | 136,119 | DECLARED_VALIDATED | `vote_id` + `bioguide_id` | — |
| `native_bill_outcomes.csv` | 3,069 | DECLARED_VALIDATED | `bill_id` | — |
| `native_bills.csv` | 3,069 | DECLARED_VALIDATED | `bill_id` | — |
| `native_bills_entity_bridge.csv` | 676 | DECLARED_VALIDATED | `bill_id` + `tribe_id` | `cedar_uid`→41, `tribe_id`→41 |
| `native_bills_entity_class.csv` | 2,694 | DECLARED_VALIDATED | `bill_id` + `class_match_basis` | — |
| `native_bills_subject_sweep.csv` | 2,409 | DECLARED_VALIDATED | `bill_id` | `subject_family`→2,185 |
| `native_issue_litigation_positions.csv` | 197 | DECLARED_VALIDATED | `position_id` | — |

### Indian Country Deals  (`deals`)

14 of 14 shippable tables declared.

| table | rows | outcome | primary key | max rows per join-key value |
|---|---:|---|---|---|
| `deals_2000_2019_additions.csv` | 40 | DECLARED_VALIDATED | `Deal_ID` | — |
| `deals_2026_ytd_additions.csv` | 0 | DECLARED_VALIDATED | `Deal_ID` | `Deal_ID`→0 |
| `deals_anc_reports_additions.csv` | 28 | DECLARED_VALIDATED | `Deal_ID` | — |
| `deals_ancsa_portal_additions.csv` | 34 | DECLARED_VALIDATED | `Deal_ID` | — |
| `deals_ancsa_portal_v2_additions.csv` | 42 | DECLARED_VALIDATED | `Deal_ID` | — |
| `deals_classified.csv` | 935 | DECLARED_VALIDATED | `Deal_ID` | `cedar_uid`→39 |
| `deals_federal_awards_additions.csv` | 594 | DECLARED_VALIDATED | `Deal_ID` | — |
| `deals_historical_additions.csv` | 30 | DECLARED_VALIDATED | `Deal_ID` | — |
| `deals_sec_2010_2017_additions.csv` | 16 | DECLARED_VALIDATED | `Deal_ID` | — |
| `deals_source_index.csv` | 533 | DECLARED_VALIDATED | `native_party` | — |
| `deals_tribal_debt_additions.csv` | 6 | DECLARED_VALIDATED | `Deal_ID` | — |
| `ownership_events.csv` | 98 | DECLARED_VALIDATED | `event_id` | `cedar_uid`→12, `entity_id`→12, `tribe_id`→12 |
| `seminole_bond_disclosures.csv` | 29 | DECLARED_VALIDATED | `disclosure_id` | `cedar_uid`→29, `tribe_id`→29 |
| `tribal_resolution_financings.csv` | 1 | DECLARED_VALIDATED | `entity_id` + `source_url` + `source_index_url` + `instrument_title` | `cedar_uid`→1, `entity_id`→1 |

### NAGPRA  (`nagpra`)

5 of 5 shippable tables declared.

| table | rows | outcome | primary key | max rows per join-key value |
|---|---:|---|---|---|
| `fr_nagpra_title_index.csv` | 6,606 | DECLARED_VALIDATED | `document_number` | `document_number`→1 |
| `fr_nagpra_title_index_year.csv` | 33 | DECLARED_VALIDATED | `publication_year` | `publication_year`→1 |
| `nagpra_notice_entity_bridge.csv` | 51,521 | DECLARED_VALIDATED | `document_number` + `relationship` + `party_name_verbatim` | `tribe_id`→900 |
| `nagpra_notice_institutions.csv` | — | DECLARED_VALIDATED | `nagpra_notice_institution_id` | `document_number`→8, `nagpra_notice_institution_id`→1 |
| `nagpra_notices.csv` | 6,772 | DECLARED_VALIDATED | `document_number` | `document_number`→1 |

### Lobbying  (`lobbying`)

35 of 35 shippable tables declared.

| table | rows | outcome | primary key | max rows per join-key value |
|---|---:|---|---|---|
| `admin_appeal_decisions.csv` | 15,613 | DECLARED_VALIDATED | `decision_id` | — |
| `admin_appeal_parties.csv` | 20,027 | DECLARED_VALIDATED | `party_id` | `cedar_uid`→21 |
| `admin_appeal_positions.csv` | 8 | DECLARED_VALIDATED | `position_id` | `cedar_uid`→1 |
| `advocacy_passthrough.csv` | 1,620 | DECLARED_VALIDATED | `passthrough_id` | `cedar_uid`→10 |
| `agency_attention_vs_advocacy.csv` | 22 | DECLARED_VALIDATED | `department` | — |
| `agency_attention_vs_advocacy_year.csv` | 698 | DECLARED_VALIDATED | `department` + `year` | — |
| `earmarks.csv` | 1,002 | DECLARED_VALIDATED | `earmark_id` | `cedar_uid`→42, `entity_id`→42 |
| `ferc_docket_filings.csv` | 102,615 | DECLARED_VALIDATED | `ferc_filing_id` + `filing_occurrence_seq` | `cedar_uid`→389 |
| `ferc_docket_parties.csv` | 11,563 | DECLARED_VALIDATED | `ferc_docket_party_id` | `cedar_uid`→14 |
| `ferc_ex_parte_communications.csv` | 713 | DECLARED_VALIDATED | `ferc_ex_parte_id` + `filed_or_issued_by_as_recorded` | `cedar_uid`→2 |
| `ferc_ex_parte_parties.csv` | 4,246 | DECLARED_VALIDATED | `ferc_ex_parte_party_id` + `table_row_quote` | `cedar_uid`→2 |
| `ferc_tribal_dockets.csv` | 307 | DECLARED_VALIDATED | `docket_number` + `subdocket` | — |
| `fr_ex_parte_notices.csv` | 7,820 | DECLARED_VALIDATED | `fr_ex_parte_notice_id` | — |
| `fr_ex_parte_parties.csv` | 112 | DECLARED_VALIDATED | `fr_ex_parte_party_id` | `cedar_uid`→0 |
| `fr_ex_parte_party_entity_links.csv` | 9 | DECLARED_VALIDATED | `link_id` | `cedar_uid`→2 |
| `hearing_appearances.csv` | 2,674 | DECLARED_VALIDATED | `hearing_appearance_id` | `cedar_uid`→78, `entity_id`→78 |
| `hearing_bill_links.csv` | 464 | DECLARED_VALIDATED | `event_id` + `bill_id` | `bill_id`→4, `event_id`→19 |
| `lobbying_disclosure_verbosity_year.csv` | 27 | DECLARED_VALIDATED | `filing_year` | — |
| `lobbying_issue_families_filing.csv` | 27,796 | DECLARED_VALIDATED | `filing_uuid` | `cedar_uid`→400, `entity_id`→400 |
| `lobbying_issue_family_year.csv` | 476 | DECLARED_VALIDATED | `issue_family` + `filing_year` | — |
| `lobbying_registrant_client_relationships.csv` | 1,309 | DECLARED_VALIDATED | `registrant_id` + `client_id` | `cedar_uid`→16 |
| `lobbying_registrant_concentration.csv` | 36 | DECLARED_VALIDATED | `scope` + `scope_value` | — |
| `lobbying_registrant_identifiers.csv` | 525 | DECLARED_VALIDATED | `identifier` + `asserted_by_source` | — |
| `lobbying_registrant_native_ownership_evidence.csv` | 27 | DECLARED_VALIDATED | `registrant_id` + `evidence_route` + `native_entity_id` + `identifier` + `asserted_by_source` | `cedar_uid`→5 |
| `lobbying_registrants.csv` | 653 | DECLARED_VALIDATED | `registrant_id` | — |
| `lobbying_target_entities.csv` | 116 | DECLARED_VALIDATED | `government_entity_as_filed` | — |
| `native_entity_lobbying_disclosures.csv` | 27,796 | DECLARED_VALIDATED | `filing_uuid` | `cedar_uid`→400, `entity_id`→400 |
| `nonprofit_schedule_c_coverage.csv` | — | DECLARED_VALIDATED | `index_year` | `index_year`→1 |
| `nonprofit_schedule_c_lobbying.csv` | — | DECLARED_VALIDATED | `schedule_c_row_id` | `cedar_entity_id`→82, `ein`→10, `object_id`→1, `schedule_c_row_id`→1 |
| `nrc_meeting_participants.csv` | 407 | DECLARED_VALIDATED | `participant_id` | `cedar_uid`→1 |
| `nrc_public_meetings.csv` | 251 | DECLARED_VALIDATED | `nrc_meeting_id` | — |
| `oira_federal_action_links.csv` | 145 | DECLARED_VALIDATED | `oira_meeting_id` + `federal_action_document_number` | — |
| `oira_meeting_participants.csv` | 1,128 | DECLARED_VALIDATED | `oira_participant_id` | `cedar_uid`→18, `entity_id`→18 |
| `oira_meetings.csv` | 72 | DECLARED_VALIDATED | `oira_meeting_id` | `cedar_uid`→2, `entity_id`→2 |
| `tribe_year_lobbying_panel.csv` | 4,997 | DECLARED_VALIDATED | `entity_id` + `filing_year` | `cedar_uid`→28, `entity_id`→28 |

### Federal Prime Contracting  (`contractors`)

10 of 10 shippable tables declared.

| table | rows | outcome | primary key | max rows per join-key value |
|---|---:|---|---|---|
| `contractor_ranking.csv` | 1,429 | DECLARED_VALIDATED | `owner_entity_id` + `operating_company_seq` | `operating_company_uei`→1, `owner_entity_id`→70 |
| `fpds_uei_cage_map.csv` | 29,981 | DECLARED_VALIDATED | `uei` + `cage_code` + `legal_business_name` | `cage_code`→6, `uei`→16 |
| `fpds_uei_edges.csv` | — | DECLARED_VALIDATED | `child_uei` + `parent_uei` + `edge_type` | — |
| `prime_contracts.csv` | 1,217,768 | DECLARED_VALIDATED | `contract_transaction_unique_key` + `contract_number` + `parent_contract_number` + `fiscal_year` + `awardee_uei` | `cage_code`→398,840, `cedar_uid`→111,398, `tribe_id`→111,398 |
| `prime_contracts_archive_backfill.csv` | 631,507 | DECLARED_VALIDATED | `contract_transaction_unique_key` | `cage_code`→398,840, `cedar_uid`→50,208, `tribe_id`→50,208 |
| `prime_contracts_awards.csv` | 455,080 | DECLARED_VALIDATED | `contract_number` | `cage_code`→85,976, `cedar_uid`→55,184, `tribe_id`→55,184 |
| `prime_contracts_entity_year.csv` | 6,715 | DECLARED_VALIDATED | `tribe_id` + `fiscal_year` | `cedar_uid`→27, `tribe_id`→27 |
| `prime_contracts_published.csv` | 455,080 | DECLARED_VALIDATED | `contract_number` | `cage_code`→85,976, `cedar_uid`→55,184, `tribe_id`→55,184 |
| `sam_prime_contracts_fy2000_2007.csv` | 269,312 | DECLARED_VALIDATED | `sam_transaction_key` | `cage_code`→304 |
| `sam_prime_contracts_fy2000_2007_PUBLISHABLE.csv` | 269,312 | DECLARED_VALIDATED | `sam_transaction_key` | `cage_code`→304 |

### Federal Subcontracting  (`subcontracting`)

3 of 3 shippable tables declared.

| table | rows | outcome | primary key | max rows per join-key value |
|---|---:|---|---|---|
| `prime_sub_network.csv` | 220 | DECLARED_VALIDATED | `prime_uei` + `sub_uei` | — |
| `subaward_entity_rollup.csv` | 450 | DECLARED_VALIDATED | `tribe_id` | `cedar_uid`→1, `tribe_id`→1 |
| `subawards.csv` | 76,859 | DECLARED_VALIDATED | `source_dataset` + `subaward_source_record_id` | `cedar_uid`→6,651 |

### Native-Owned Businesses  (`native-owned-businesses`)

6 of 6 shippable tables declared.

| table | rows | outcome | primary key | max rows per join-key value |
|---|---:|---|---|---|
| `individual_native_exclusion_pairs.csv` | 5 | DECLARED_VALIDATED | `identifier_type` + `identifier` | — |
| `individual_native_firm_contracts.csv` | 324 | DECLARED_VALIDATED | `surrogate_entity_id` + `fiscal_year` | `cedar_uid`→23 |
| `individual_native_firm_contracts_published.csv` | 613 | DECLARED_VALIDATED | `cell_type` + `dimension_1` + `dimension_2` | — |
| `individual_native_firm_register.csv` | 45 | DECLARED_VALIDATED | `surrogate_entity_id` | `cedar_uid`→1 |
| `individual_native_ownership_verification.csv` | 335 | DECLARED_VALIDATED | `verification_id` | — |
| `individual_native_verification_candidates.csv` | 335 | DECLARED_VALIDATED | `verification_id` | — |

### NEST: Native Enterprise Structures and Ties  (`nest`)

2 of 2 shippable tables declared.

| table | rows | outcome | primary key | max rows per join-key value |
|---|---:|---|---|---|
| `nest_enterprise_relations.csv` | — | DECLARED_VALIDATED | `enterprise_edge_id` | `cedar_uid`→367, `enterprise_edge_id`→1, `enterprise_id`→15, `owner_hub_cedar_uid`→367 |
| `nest_enterprises.csv` | — | DECLARED_VALIDATED | `enterprise_id` | `cedar_uid`→172, `enterprise_id`→1, `owner_hub_cedar_uid`→172, `parent_enterprise_id`→34 |

### Natural Resource Revenues  (`natural-resources`)

8 of 8 shippable tables declared.

| table | rows | outcome | primary key | max rows per join-key value |
|---|---:|---|---|---|
| `anc_ceiling_roster.csv` | 196 | DECLARED_VALIDATED | `anc_id` | `cage_code`→0, `uei`→0 |
| `ancsa_filings_index.csv` | 19,269 | DECLARED_VALIDATED | `portal_document_id` | — |
| `nd_severance_allocation.csv` | 7 | DECLARED_VALIDATED | `allocation_id` | `cedar_uid`→7, `tribe_id`→7 |
| `resource_assets.csv` | 35 | DECLARED_VALIDATED | `resource_asset_id` | `cedar_uid`→0 |
| `resource_parties.csv` | 1,436 | DECLARED_VALIDATED | `party_link_id` + `entity_name` | `cedar_uid`→489, `entity_id`→489 |
| `resource_revenue.csv` | 10,482 | DECLARED_VALIDATED | `resource_revenue_event_id` | `cedar_uid`→489 |
| `tribal_bond_issuances.csv` | 29 | DECLARED_VALIDATED | `issuer` + `instrument_type` + `source_url` | — |
| `tribal_tax_bases.csv` | 1,712 | DECLARED_VALIDATED | `tax_observation_id` | `cedar_uid`→660, `tribe_id`→660 |

### Native Nonprofits  (`nonprofits`)

10 of 10 shippable tables declared.

| table | rows | outcome | primary key | max rows per join-key value |
|---|---:|---|---|---|
| `fac_tribal_single_audits.csv` | 6,780 | DECLARED_VALIDATED | `report_id` | `cedar_uid`→32, `entity_id`→32 |
| `grantmaker_funding_flows.csv` | 18,656 | DECLARED_VALIDATED | `flow_id` | `cedar_uid`→0 |
| `grantmaker_funding_overlap.csv` | 69 | DECLARED_VALIDATED | `funder_key` + `recipient_resolved_target` | — |
| `np_ein_entity_hub.csv` | 2,303 | DECLARED_VALIDATED | `ein` | `cedar_uid`→123, `ein`→1, `entity_id`→123 |
| `np_financials.csv` | 8,507 | DECLARED_VALIDATED | `ein` + `tax_period` | `ein`→27 |
| `np_grantee_financials.csv` | 4,058 | DECLARED_VALIDATED | `ein` + `source_url` | `ein`→12 |
| `np_org_scale.csv` | 1,157 | DECLARED_VALIDATED | `ein` | `ein`→1 |
| `np_orgs.csv` | 12,764 | DECLARED_VALIDATED | `EIN` | `cedar_uid`→121, `entity_id`→2, `tribe_id`→121 |
| `np_schedule_i_filers.csv` | 10,314 | DECLARED_VALIDATED | `object_id` | — |
| `np_schedule_i_grants.csv` | 58,685 | DECLARED_VALIDATED | `object_id` + `schedule_i_line_seq` | `cedar_uid`→46 |

### Gaming Intelligence  (`gaming`)

54 of 54 shippable tables declared.

| table | rows | outcome | primary key | max rows per join-key value |
|---|---:|---|---|---|
| `ca_gaming_facilities_official.csv` | 245 | DECLARED_VALIDATED | `record_id` | `cedar_uid`→7, `facility_id`→4, `tribe_id`→7 |
| `ca_gaming_payments.csv` | 40,164 | DECLARED_VALIDATED | `payment_id` | `cedar_uid`→534, `tribe_id`→534 |
| `compact_events.csv` | 31 | DECLARED_VALIDATED | `event_id` | `cedar_uid`→2, `compact_id`→2, `entity_id`→2, `tribe_id`→2 |
| `compact_obligation_tribal_agency_bridge.csv` | 927 | DECLARED_VALIDATED | `bridge_id` | `cedar_uid`→23, `compact_id`→15, `tribe_id`→23 |
| `compact_required_reports.csv` | 4,121 | DECLARED_VALIDATED | `report_id` | `cedar_uid`→56, `compact_id`→47, `entity_id`→56, `tribe_id`→56 |
| `compact_structured_terms.csv` | 2,887 | DECLARED_VALIDATED | `term_id` | `cedar_uid`→44, `compact_id`→33, `entity_id`→44, `tribe_id`→44 |
| `compact_terms.csv` | 1,311 | DECLARED_VALIDATED | `version_id` + `quote` | `cedar_uid`→21, `compact_id`→11, `entity_id`→21, `tribe_id`→21 |
| `compact_versions.csv` | 1,158 | DECLARED_VALIDATED | `version_id` | `compact_id`→30 |
| `compacts.csv` | 707 | DECLARED_VALIDATED | `compact_id` | `cedar_uid`→14, `compact_id`→1, `entity_id`→14, `tribe_id`→14 |
| `digital_gaming_relationships.csv` | 154 | DECLARED_VALIDATED | `digital_gaming_id` | `cedar_uid`→4, `entity_id`→4, `facility_id`→0, `tribe_id`→4 |
| `digital_gaming_revenue.csv` | 10,661 | DECLARED_VALIDATED | `revenue_id` | `cedar_uid`→1,788, `entity_id`→1,788, `facility_id`→0, `tribe_id`→1,788 |
| `fac_audit_gaming_disclosures.csv` | 1,521 | DECLARED_VALIDATED | `report_id` + `verbatim_quote` + `source_page` | `cedar_uid`→136, `entity_id`→136 |
| `fac_audit_sefa_gaming_programs.csv` | 1 | DECLARED_VALIDATED | `report_id` + `award_reference` | `cedar_uid`→1, `entity_id`→1 |
| `fl_gaming_payments.csv` | 9,756 | DECLARED_VALIDATED | `payment_id` | `cedar_uid`→9,754, `facility_id`→1, `tribe_id`→9,754 |
| `gaming_capacity_official.csv` | 6,461 | DECLARED_VALIDATED | `observation_id` | `cedar_uid`→1,584, `facility_id`→1,584, `tribe_id`→1,584 |
| `gaming_decision_compact_join.csv` | 138 | DECLARED_VALIDATED | `decision_id` | — |
| `gaming_decision_events.csv` | 265 | DECLARED_VALIDATED | `event_id` | — |
| `gaming_device_observations.csv` | 1,326 | DECLARED_VALIDATED | `observation_id` | `cedar_uid`→396, `entity_id`→396, `facility_id`→396, `tribe_id`→396 |
| `gaming_employment_observations.csv` | 3,246 | DECLARED_VALIDATED | `observation_id` | `cedar_uid`→84, `ein`→32, `entity_id`→84, `facility_id`→11, `tribe_id`→84 |
| `gaming_facilities.csv` | 787 | DECLARED_VALIDATED | `facility_id` | `cedar_uid`→28, `entity_id`→15, `facility_id`→1, `tribe_id`→28 |
| `gaming_financing_events.csv` | 293 | DECLARED_VALIDATED | `financing_event_id` | `cedar_uid`→7 |
| `gaming_game_finder_observations.csv` | 6,851 | DECLARED_VALIDATED | `observation_id` | `cedar_uid`→3,878, `entity_id`→3,878, `facility_id`→2,973, `tribe_id`→3,878 |
| `gaming_land_decisions.csv` | 138 | DECLARED_VALIDATED | `decision_id` | `cedar_uid`→5, `entity_id`→5, `tribe_id`→5 |
| `gaming_manufacturer_facts.csv` | 62 | DECLARED_VALIDATED | `fact_id` | — |
| `gaming_mitigation_agreements.csv` | 24 | DECLARED_VALIDATED | `project_id` + `counterparty_government` + `service` | — |
| `gaming_nigc_roster_link.csv` | 453 | DECLARED_VALIDATED | `facility_id` | `cedar_uid`→18, `facility_id`→1, `tribe_id`→18 |
| `gaming_ordinance_ocr.csv` | 263 | DECLARED_VALIDATED | `ordinance_id` | `cedar_uid`→10, `tribe_id`→10 |
| `gaming_ordinances.csv` | 1,155 | DECLARED_VALIDATED | `ordinance_id` | `cedar_uid`→23, `tribe_id`→23 |
| `gaming_project_facilities.csv` | 19 | DECLARED_VALIDATED | `project_id` + `alternative` + `source_document` | `cedar_uid`→0, `entity_id`→0 |
| `gaming_projections.csv` | 116 | DECLARED_VALIDATED | `project_id` + `metric` + `geography` + `time_period` + `alternative` + `source_document` + `unit` | — |
| `gaming_properties.csv` | 784 | DECLARED_VALIDATED | `facility_id` | `cedar_uid`→28, `facility_id`→1, `tribe_id`→28 |
| `gaming_property_federal_traces.csv` | 774 | DECLARED_VALIDATED | `facility_id` | `cedar_uid`→28, `compact_id`→28, `facility_id`→1, `tribe_id`→28 |
| `gaming_property_labor_demand.csv` | 43 | DECLARED_VALIDATED | `observation_id` | `cedar_uid`→6, `entity_id`→6, `facility_id`→6, `tribe_id`→6 |
| `gaming_property_self_published_assertions.csv` | — | DECLARED_VALIDATED | `assertion_id` | `assertion_id`→1, `cedar_uid`→51, `facility_id`→51, `site_host`→51, `source_url`→5, `tribe_id`→51 |
| `gaming_property_self_published_claims.csv` | — | DECLARED_VALIDATED | `claim_id` | `cedar_uid`→22, `claim_id`→1, `facility_id`→22, `site_host`→22, `source_claim_id`→1, `source_url`→7, `tribe_id`→22 |
| `gaming_property_site_observations.csv` | 262 | DECLARED_VALIDATED | `observation_id` | `cedar_uid`→25, `entity_id`→25, `facility_id`→13, `tribe_id`→25 |
| `gaming_property_universe_events.csv` | 10 | DECLARED_VALIDATED | `event_id` | `cedar_uid`→1, `entity_id`→1, `facility_id`→1 |
| `gaming_revenue_bounds.csv` | 13,803 | DECLARED_VALIDATED | `bound_id` | `cedar_uid`→466, `facility_id`→82, `tribe_id`→466 |
| `gaming_source_claims.csv` | — | DECLARED_VALIDATED | `source_claim_id` | — |
| `gaming_vendor_tribal_licenses.csv` | 740 | DECLARED_VALIDATED | `vendor_name` + `tribal_gaming_regulator` + `source_url` | `cedar_uid`→287, `entity_id`→287 |
| `loyalty_program_property.csv` | 48 | DECLARED_VALIDATED | `loyalty_program_id` + `facility_id` | `cedar_uid`→11, `entity_id`→11, `facility_id`→1, `tribe_id`→11 |
| `loyalty_programs.csv` | 18 | DECLARED_VALIDATED | `loyalty_program_id` | `cedar_uid`→1, `entity_id`→1, `tribe_id`→1 |
| `nigc_action_parties.csv` | — | DECLARED_VALIDATED | `record_id` + `tribe_entity_id` + `role` | `record_id`→2, `tribe_entity_id`→15 |
| `nigc_declination_letters.csv` | 327 | DECLARED_VALIDATED | `cedar_opinion_id` | `cedar_uid`→7 |
| `nigc_document_surface.csv` | — | DECLARED_VALIDATED | `nigc_category` + `document_slug` | `document_slug`→4 |
| `nigc_enforcement_actions.csv` | — | DECLARED_VALIDATED | `action_id` | `action_id`→1, `tribe_entity_id`→15 |
| `nigc_game_classification_opinions.csv` | — | DECLARED_VALIDATED | `opinion_id` | `opinion_id`→1 |
| `nigc_indian_lands_opinions.csv` | — | DECLARED_VALIDATED | `opinion_id` | `opinion_id`→1 |
| `nigc_management_contract_approvals.csv` | — | DECLARED_VALIDATED | `action_id` | `action_id`→1 |
| `nigc_region_assignments.csv` | 2,438 | DECLARED_VALIDATED | `facility_id` + `effective_start_year` | `administrative_region_id`→190, `cedar_uid`→81, `facility_id`→4, `tribe_id`→81 |
| `nigc_regional_ggr.csv` | 198 | DECLARED_VALIDATED | `administrative_region_id` + `fiscal_year` | `administrative_region_id`→10 |
| `nigc_revenue_bands.csv` | 20 | DECLARED_VALIDATED | `band_id` | — |
| `state_gaming_observations.csv` | 494 | DECLARED_VALIDATED | `observation_id` | `cedar_uid`→78, `facility_id`→14, `tribe_id`→78 |
| `wa_machine_allocations.csv` | 75 | DECLARED_VALIDATED | `allocation_id` | `cedar_uid`→3, `tribe_id`→3 |

### Entity spine, identifiers and reference  (`_entity_layer`)

35 of 35 shippable tables declared.

| table | rows | outcome | primary key | max rows per join-key value |
|---|---:|---|---|---|
| `admin_region_assignments.csv` | 2,124 | DECLARED_VALIDATED | `assignment_id` | `administrative_region_id`→465 |
| `admin_region_overlap_derived.csv` | 28 | DECLARED_VALIDATED | `administrative_region_id_a` + `administrative_region_id_b` | — |
| `admin_region_systems.csv` | 6 | DECLARED_VALIDATED | `region_system_code` | — |
| `admin_regional_observations.csv` | 27 | DECLARED_VALIDATED | `observation_id` | `administrative_region_id`→4 |
| `admin_regions.csv` | 155 | DECLARED_VALIDATED | `administrative_region_id` | `administrative_region_id`→1 |
| `bie_uio_dollars_by_entity.csv` | 114 | DECLARED_VALIDATED | `tribe_id` | `cedar_uid`→1, `tribe_id`→1 |
| `cedar_correction_register.csv` | 173 | DECLARED_VALIDATED | `correction_id` | `entity_id`→94 |
| `cedar_entity_identity_crosswalk.csv` | 10,107 | DECLARED_VALIDATED | `crosswalk_id` | `cedar_uid`→160 |
| `cedar_identifier_graph_edges.csv` | 46,820 | DECLARED_VALIDATED | `edge_kind` + `from_node` + `to_node` + `asserting_source` + `asserting_row_ref` + `edge_tier` + `method` | `from_node`→1,095 |
| `cedar_identifier_graph_nodes.csv` | 115,471 | DECLARED_VALIDATED | `node` | — |
| `cedar_identifier_ledger_final.csv` | — | DECLARED_VALIDATED | `identifier_type` + `identifier` + `tribe_id` + `attribution_method` + `evidence_url` + `verified_date` | `cedar_uid`→159, `identifier`→2, `tribe_id`→159 |
| `cedar_identifier_propagation.csv` | 1,157 | DECLARED_VALIDATED | `dataset` + `identifier` | — |
| `cedar_publishable_identifiers.csv` | 1,577 | DECLARED_VALIDATED | `identifier` | `cedar_uid`→35, `tribe_id`→35 |
| `cedar_ruling_ledger_consolidated.csv` | 43,321 | DECLARED_VALIDATED | `subject_key` + `source_file` + `source_row_ordinal` | `resolved_tribe_id`→661, `subject_key`→2,778 |
| `cross_dataset_ruling_map.csv` | 22,936 | DECLARED_VALIDATED | `source_file` + `target_row_ordinal` + `identifier_type` + `channel` | `identifier`→2,776 |
| `entity_aliases.csv` | 6,297 | DECLARED_VALIDATED | `alias_id` | `cedar_uid`→20, `entity_id`→20 |
| `entity_hierarchy.csv` | 952 | DECLARED_VALIDATED | `tribe_id` | `cedar_uid`→1, `tribe_id`→1 |
| `entity_relationships.csv` | 2,292 | DECLARED_VALIDATED | `relationship_id` | — |
| `entity_year_panel.csv` | 12,534 | DECLARED_VALIDATED | `tribe_id` + `year` | `cedar_uid`→28, `tribe_id`→28 |
| `federal_recognition_events.csv` | 366 | DECLARED_VALIDATED | `entity_key` + `fr_document_number` | `cedar_uid`→4, `tribe_id`→4 |
| `federal_recognition_roster.csv` | 17,058 | DECLARED_VALIDATED | `fr_document_number` + `entry_raw` | `cedar_uid`→54, `tribe_id`→54 |
| `foia_discovery_targets.csv` | 122 | DECLARED_VALIDATED | `url` | — |
| `foia_request_index.csv` | 9,481 | DECLARED_VALIDATED | `foia_request_id` + `request_description` | `cedar_uid`→55 |
| `intertribal_memberships.csv` | 989 | DECLARED_VALIDATED | `org_id` + `member_entity_name` + `year_observed` | — |
| `intertribal_orgs.csv` | 57 | DECLARED_VALIDATED | `proposed_id` | `ein`→1 |
| `native_fi_roster.csv` | 94 | DECLARED_VALIDATED | `name` | — |
| `nho_doi_notification_roster.csv` | 190 | DECLARED_VALIDATED | `nho_id` | `cage_code`→0, `cedar_uid`→0, `uei`→0 |
| `nho_ownership_changes.csv` | 9 | DECLARED_VALIDATED | `event_id` | `cedar_uid`→9 |
| `nho_register.csv` | 218 | DECLARED_VALIDATED | `proposed_id` | `ein`→1 |
| `nho_verified_entities.csv` | 36 | DECLARED_VALIDATED | `uei` | `cage_code`→1, `cedar_uid`→0, `uei`→1 |
| `tcu_cdfi_added.csv` | 130 | DECLARED_VALIDATED | `tribe_id` | `cedar_uid`→1, `tribe_id`→1 |
| `tcu_cdfi_ownership_evidence.csv` | 130 | DECLARED_VALIDATED | `institution` + `layer` + `pattern` + `evidence_url` + `quote_char_offset` | — |
| `tcu_roster.csv` | 37 | DECLARED_VALIDATED | `name` | — |
| `visitor_access_events.csv` | 20 | DECLARED_VALIDATED | `visitor_access_event_id` | `cedar_uid`→0 |
| `visitor_record_foia_requests.csv` | 667 | DECLARED_VALIDATED | `foia_request_id` + `request_description_verbatim` | `cedar_uid`→6 |
