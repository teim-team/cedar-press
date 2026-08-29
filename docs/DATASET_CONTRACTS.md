# Dataset contracts - generated, do not hand-edit

*Generated 2026-08-29 by `code/512_build_dataset_contracts.py` (mission Phase 1). Regenerate rather than edit; `verify` exits 1 when the world breaks a contract, and 62 gates on it.*

**13 collections, 255 tables claimed, 0 orphaned shippable tables, 0 violations.**

**Grain: 3 of 210 shippable tables declare and VALIDATE a row grain, a primary key and a join cardinality; 207 do not.** A declared grain the data contradicts is a release-blocking violation, listed below. An unstated grain is ratcheted by `62_no_regression_check.contract_grain_unstated_shippable`: the count may only fall, and a new shippable table that lands without one fails the gate that day.

<details><summary>Shippable tables with an UNSTATED grain (207) - a buyer cannot join these safely</summary>

- `admin_appeal_decisions.csv`
- `admin_appeal_parties.csv`
- `admin_appeal_positions.csv`
- `admin_region_assignments.csv`
- `admin_region_overlap_derived.csv`
- `admin_region_systems.csv`
- `admin_regional_observations.csv`
- `admin_regions.csv`
- `advocacy_passthrough.csv`
- `advocacy_passthrough_2026-08-07.csv`
- `agency_attention_vs_advocacy.csv`
- `agency_attention_vs_advocacy_year.csv`
- `anc_ceiling_roster.csv`
- `ancsa_filings_index.csv`
- `bie_uio_dollars_by_entity.csv`
- `bill_votes.csv`
- `bill_votes_entity_bridge.csv`
- `bill_votes_official_verification.csv`
- `ca_gaming_facilities_official.csv`
- `ca_gaming_payments.csv`
- `cedar_correction_register.csv`
- `cedar_entity_identity_crosswalk.csv`
- `cedar_identifier_graph_edges.csv`
- `cedar_identifier_graph_nodes.csv`
- `cedar_identifier_propagation.csv`
- `cedar_publishable_identifiers.csv`
- `cedar_ruling_ledger_consolidated.csv`
- `compact_events.csv`
- `compact_obligation_tribal_agency_bridge.csv`
- `compact_required_reports.csv`
- `compact_structured_terms.csv`
- `compact_terms.csv`
- `compact_versions.csv`
- `compacts.csv`
- `congressional_correspondence_log.csv`
- `congressional_correspondence_systems.csv`
- `consultation_events.csv`
- `contractor_ranking.csv`
- `correspondence_foia_source_coverage.csv`
- `cross_dataset_ruling_map.csv`
- `deals_2000_2019_additions.csv`
- `deals_2026_ytd_additions.csv`
- `deals_anc_reports_additions.csv`
- `deals_ancsa_portal_additions.csv`
- `deals_ancsa_portal_v2_additions.csv`
- `deals_classified.csv`
- `deals_federal_awards_additions.csv`
- `deals_historical_additions.csv`
- `deals_sec_2010_2017_additions.csv`
- `deals_source_index.csv`
- `deals_tribal_debt_additions.csv`
- `digital_gaming_relationships.csv`
- `digital_gaming_revenue.csv`
- `earmarks.csv`
- `entity_aliases.csv`
- `entity_hierarchy.csv`
- `entity_relationships.csv`
- `entity_year_panel.csv`
- `faads_entity_attribution.csv`
- `faads_transactions.csv`
- `faads_transactions_all_agencies.csv`
- `fac_audit_gaming_disclosures.csv`
- `fac_audit_sefa_gaming_programs.csv`
- `fac_tribal_single_audits.csv`
- `federal_actions.csv`
- `federal_actions_entity_bridge.csv`
- `federal_actions_raw.csv`
- `federal_funding_transactions.csv` — grain stated as 'one row per federal award transaction', but the file is a UNION of assistance and archive pulls and no owner has ruled whether assistance_transaction_unique_key is unique ACROSS the union or only within one pull. Declaring a key we have not ruled on is the one way this file can lie, so it stays open.
- `federal_funding_tribe_year_panel.csv`
- `federal_recognition_events.csv`
- `federal_recognition_roster.csv`
- `ferc_docket_filings.csv`
- `ferc_docket_parties.csv`
- `ferc_ex_parte_communications.csv`
- `ferc_ex_parte_parties.csv`
- `ferc_tribal_dockets.csv`
- `fl_gaming_payments.csv`
- `foia_discovery_targets.csv`
- `foia_request_index.csv`
- `fpds_uei_cage_map.csv`
- `fr_abstract_availability_year.csv`
- `fr_consultation_by_agency.csv`
- `fr_consultation_notices.csv`
- `fr_consultation_referenced.csv`
- `fr_consultation_year.csv`
- `fr_content_classification.csv`
- `fr_ex_parte_notices.csv`
- `fr_ex_parte_parties.csv`
- `fr_ex_parte_party_entity_links.csv`
- `fr_nagpra_title_index.csv`
- `fr_nagpra_title_index_year.csv`
- `fr_relevance_tier_year.csv`
- `fr_theme_year.csv`
- `funding_identifier_netnew_ueis.csv`
- `gaming_capacity_official.csv`
- `gaming_decision_compact_join.csv`
- `gaming_decision_events.csv`
- `gaming_device_observations.csv`
- `gaming_employment_observations.csv`
- `gaming_facilities.csv`
- `gaming_financing_events.csv`
- `gaming_game_finder_observations.csv`
- `gaming_land_decisions.csv`
- `gaming_manufacturer_facts.csv`
- `gaming_mitigation_agreements.csv`
- `gaming_nigc_roster_link.csv`
- `gaming_ordinance_ocr.csv`
- `gaming_ordinances.csv`
- `gaming_project_facilities.csv`
- `gaming_projections.csv`
- `gaming_properties.csv`
- `gaming_property_federal_traces.csv`
- `gaming_property_labor_demand.csv`
- `gaming_property_site_observations.csv`
- `gaming_property_universe_events.csv`
- `gaming_revenue_bounds.csv`
- `gaming_vendor_tribal_licenses.csv`
- `grantmaker_funding_flows.csv`
- `grantmaker_funding_overlap.csv`
- `hearing_appearances.csv`
- `hearing_bill_links.csv`
- `individual_native_exclusion_pairs.csv`
- `individual_native_firm_contracts.csv`
- `individual_native_firm_contracts_published.csv`
- `individual_native_firm_register.csv`
- `individual_native_ownership_verification.csv`
- `individual_native_verification_candidates.csv`
- `inflation_deflator.csv`
- `intertribal_memberships.csv`
- `intertribal_orgs.csv`
- `lobbying_disclosure_verbosity_year.csv`
- `lobbying_issue_families_filing.csv`
- `lobbying_issue_family_year.csv`
- `lobbying_registrant_client_relationships.csv`
- `lobbying_registrant_concentration.csv`
- `lobbying_registrant_identifiers.csv`
- `lobbying_registrant_native_ownership_evidence.csv`
- `lobbying_registrants.csv`
- `lobbying_target_entities.csv`
- `loyalty_program_property.csv`
- `loyalty_programs.csv`
- `member_positions.csv`
- `nagpra_notice_entity_bridge.csv`
- `nagpra_notices.csv`
- `native_bill_outcomes.csv`
- `native_bills.csv`
- `native_bills_entity_bridge.csv`
- `native_bills_entity_class.csv`
- `native_bills_subject_sweep.csv`
- `native_entity_lobbying_disclosures.csv`
- `native_fi_roster.csv`
- `native_issue_litigation_positions.csv`
- `native_passthrough.csv`
- `native_passthrough_pairs.csv`
- `nd_severance_allocation.csv`
- `nepa_administrative_record_parties.csv`
- `nepa_eplanning_projects.csv`
- `nepa_project_documents.csv`
- `nho_doi_notification_roster.csv`
- `nho_ownership_changes.csv`
- `nho_register.csv`
- `nho_verified_entities.csv`
- `nigc_declination_letters.csv`
- `nigc_region_assignments.csv`
- `nigc_regional_ggr.csv`
- `nigc_revenue_bands.csv`
- `np_ein_entity_hub.csv`
- `np_financials.csv`
- `np_grantee_financials.csv`
- `np_org_scale.csv`
- `np_orgs.csv`
- `np_schedule_i_filers.csv`
- `np_schedule_i_grants.csv`
- `nrc_meeting_participants.csv`
- `nrc_public_meetings.csv`
- `oira_federal_action_links.csv`
- `oira_meeting_participants.csv`
- `oira_meetings.csv`
- `ownership_events.csv`
- `prime_contracts.csv`
- `prime_contracts_archive_backfill.csv`
- `prime_contracts_awards.csv`
- `prime_contracts_entity_year.csv`
- `prime_contracts_published.csv`
- `prime_sub_network.csv`
- `resource_assets.csv`
- `resource_parties.csv`
- `resource_revenue.csv`
- `sam_prime_contracts_fy2000_2007.csv`
- `sam_prime_contracts_fy2000_2007_PUBLISHABLE.csv`
- `section_106_consultation_events.csv`
- `section_106_project_parties.csv`
- `section_106_source_coverage.csv`
- `seminole_bond_disclosures.csv`
- `state_gaming_observations.csv`
- `subaward_entity_rollup.csv`
- `subawards.csv`
- `tcu_cdfi_added.csv`
- `tcu_cdfi_ownership_evidence.csv`
- `tcu_roster.csv`
- `tribal_bond_issuances.csv`
- `tribal_resolution_financings.csv`
- `tribal_tax_bases.csv`
- `tribe_year_lobbying_panel.csv`
- `visitor_access_events.csv`
- `visitor_record_foia_requests.csv`
- `wa_machine_allocations.csv`

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

## NAGPRA  (`nagpra`, shelf: standard)

Rebuild: `py -3 code/build.py run nagpra --execute` — 4 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `fr_nagpra_title_index.csv` | shippable | — | — | — |
| `fr_nagpra_title_index_year.csv` | shippable | — | — | — |
| `nagpra_notice_entity_bridge.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `nagpra_notices.csv` | shippable | — | — | — |

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

## Federal Subcontracting  (`subcontracting`, shelf: pro)

Rebuild: `py -3 code/build.py run subcontracting --execute` — 5 tables.

| table | status | keys | rebuilt by | enriched by |
|---|---|---|---|---|
| `prime_sub_network.csv` | shippable | — | — | — |
| `subaward_entity_rollup.csv` | shippable | `tribe_id` `cedar_uid` | — | — |
| `subaward_identifier_harvest.csv` | internal-by-decision | `uei` `cage_code` | — | — |
| `subaward_identifier_netnew.csv` | internal-by-decision | `uei` `cage_code` | — | — |
| `subawards.csv` | shippable | `cedar_uid` | `20_build_subcontracts.py` | `121_pull_subawards_api.py` `250_demote_stale_tierA_subaward_rows.py` `45_promote_subawards.py` |

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
| `gaming_source_claims.csv` | shippable | — | `91_build_nigc_declinations.py` | `100_finish_declinations_and_employment.py` |
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

- `gaming_source_claims.csv` — one row per claim extracted from one source document
  - primary key: `source_claim_id`  (validated unique)
  - declared by: docs/GAMING_DATASET_PLAN.md

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
| `cedar_entity_spine.csv` | unregistered | `tribe_id` `cedar_uid` | `01_build_entity_spine.py` | `08_build_review_page.py` `115_pull_assistance_archive.py` `163_promote_nho_universe_in_place.py` `241_promote_individual_native_firms_in_place.py` `416_reconcile_spine_id_columns.py` `426_mint_bristol_bay_spine_entities.py` `503_identity.py` `510_assertions.py` `51_add_anc_acronym_aliases.py` `52_add_village_corporations.py` `61_add_nho_intertribal_to_spine.py` `66_build_entity_hierarchy.py` `69_enrich_spine_from_federal_register.py` `71_fix_known_defects.py` `73_add_tcu_and_cdfi.py` `74_add_organization_acronyms.py` `75_add_bie_schools_and_uios.py` |
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

- `cedar_entity_spine.csv` — one row per canonical Native entity (hub). Sub-hubs (registrations, facilities) are NEVER rows here - IDENTIFIER_STANDARD.md
  - primary key: `tribe_id`  (validated unique)
  - join cardinality: `cedar_uid` → one row(s) per value (measured max 1), `tribe_id` → one row(s) per value (measured max 1)
  - declared by: docs/IDENTIFIER_STANDARD.md 1
- `cedar_identifier_ledger_final.csv` — one row per (identifier, entity, evidence) claim; tier X rows are REFUTATIONS and must not be dropped by consumers
  - primary key: `identifier_type` + `identifier` + `tribe_id` + `attribution_method` + `evidence_url` + `verified_date`  (validated unique)
  - join cardinality: `cedar_uid` → many row(s) per value (measured max 159), `identifier` → many row(s) per value (measured max 2), `tribe_id` → many row(s) per value (measured max 159)
  - declared by: docs/IDENTIFIER_STANDARD.md 3

> **NEVER RUN** for `cedar_entity_spine.csv`: 01_build_entity_spine.py: A full rebuild DROPS EVERY APPENDED ENTITY - the village corporations, NHOs, TCUs, CDFIs, BIE schools and UIOs added by ...

> **NEVER RUN** for `cedar_identifier_ledger.csv`: 01_build_entity_spine.py: A full rebuild DROPS EVERY APPENDED ENTITY - the village corporations, NHOs, TCUs, CDFIs, BIE schools and UIOs added by ...

> **NEVER RUN** for `cedar_identifier_ledger_final.csv`: 09_import_rulings.py: Rebuilds cedar_identifier_ledger_final.csv FROM the stale cedar_identifier_ledger_tiered.csv, which does not carry rows ...
