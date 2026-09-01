# Per-dataset punch list

*Generated 2026-09-01 by `code/526_dataset_standard.py`. Not an audit — every line is an action with a target. A dataset is clean when its list is empty.*

**418 open items across 13 datasets.**

| dataset | critical | high | medium | low | total |
|---|---:|---:|---:|---:|---:|
| `gaming` | 2 | 7 | 72 | 1 | **82** |
| `_entity_layer` | 0 | 28 | 52 | 0 | **80** |
| `lobbying` | 0 | 21 | 43 | 0 | **64** |
| `funding` | 3 | 19 | 15 | 0 | **37** |
| `deals` | 2 | 7 | 21 | 0 | **30** |
| `contractors` | 1 | 9 | 13 | 0 | **23** |
| `legislation` | 0 | 8 | 14 | 0 | **22** |
| `nonprofits` | 1 | 4 | 16 | 0 | **21** |
| `natural-resources` | 1 | 5 | 14 | 0 | **20** |
| `federal-register` | 0 | 6 | 7 | 1 | **14** |
| `subcontracting` | 1 | 6 | 4 | 0 | **11** |
| `native-owned-businesses` | 0 | 2 | 8 | 0 | **10** |
| `nagpra` | 0 | 1 | 2 | 1 | **4** |

## `gaming`

- **C7 / critical** · `fac_audit_sefa_gaming_programs.csv` — a buyer will total this table and get a wrong answer - resolve grain/duplicates before it ships as analytical  
  *evidence:* money columns amount_expended on an aggregation-unsafe table
- **C7 / critical** · `gaming_projections.csv` — a buyer will total this table and get a wrong answer - resolve grain/duplicates before it ships as analytical  
  *evidence:* money columns value on an aggregation-unsafe table
- **C1 / high** · `fac_audit_sefa_gaming_programs.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `fac_audit_sefa_gaming_programs.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C12 / high** · `gaming_capacity_official.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `gaming_project_facilities.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C1 / high** · `gaming_projections.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `gaming_projections.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C12 / high** · `state_gaming_observations.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C11 / medium** · `ca_gaming_facilities_official.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 245 rows: measurement_type
- **C5 / medium** · `ca_gaming_facilities_official.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `ca_gaming_payments.csv` — drop 4 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 20,001 rows: county, derived_tribe_revenue_value, derived_revenue_scope, issue_date
- **C5 / medium** · `ca_gaming_payments.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `compact_events.csv` — drop 2 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 31 rows: FR_citation, FR_notice_url
- **C5 / medium** · `compact_events.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `compact_obligation_tribal_agency_bridge.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `compact_required_reports.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `compact_structured_terms.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `compact_terms.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `compact_versions.csv` — write codebook entries for 5 column(s)  
  *evidence:* not in any codebook: what_changed, has_text, approval_date_basis, text_alpha_ratio ...
- **C5 / medium** · `compact_versions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `compacts.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `digital_gaming_relationships.csv` — drop 4 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 154 rows: facility_id, facility_name, designee_entity_id, cessation_date
- **C5 / medium** · `digital_gaming_relationships.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `digital_gaming_revenue.csv` — drop 2 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 10,661 rows: digital_gaming_id, facility_id
- **C5 / medium** · `digital_gaming_revenue.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `fac_audit_gaming_disclosures.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `fac_audit_sefa_gaming_programs.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 1 rows: loan_balance
- **C5 / medium** · `fac_audit_sefa_gaming_programs.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `fl_gaming_payments.csv` — drop 3 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 9,756 rows: derived_revenue_bound_value, derived_bound_direction, derived_revenue_scope
- **C5 / medium** · `fl_gaming_payments.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `gaming_capacity_official.csv` — write codebook entries for 3 column(s)  
  *evidence:* not in any codebook: qualifier, proposed_vs_actual, corroborating_sources
- **C5 / medium** · `gaming_capacity_official.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `gaming_decision_compact_join.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `gaming_decision_events.csv` — write codebook entries for 3 column(s)  
  *evidence:* not in any codebook: derivation_rule, event_date_basis, document_url
- **C5 / medium** · `gaming_decision_events.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `gaming_device_observations.csv` — drop 5 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 1,326 rows: manufacturer, platform_or_cabinet, game_theme, shipment_origin ...
- **C5 / medium** · `gaming_device_observations.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `gaming_employment_observations.csv` — write codebook entries for 1 column(s)  
  *evidence:* not in any codebook: observation_id_as_staged
- **C5 / medium** · `gaming_employment_observations.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `gaming_facilities.csv` — write codebook entries for 2 column(s)  
  *evidence:* not in any codebook: open_date_source_value_verbatim, close_date_source_value_verbatim
- **C5 / medium** · `gaming_facilities.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `gaming_financing_events.csv` — drop 2 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 293 rows: trustee, principal_amount_usd
- **C5 / medium** · `gaming_financing_events.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `gaming_game_finder_observations.csv` — drop 3 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 6,851 rows: floor_location, quantity_if_known, supersedes_observation_id
- **C5 / medium** · `gaming_game_finder_observations.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `gaming_land_decisions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `gaming_manufacturer_facts.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `gaming_mitigation_agreements.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `gaming_nigc_roster_link.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `gaming_ordinance_ocr.csv` — write codebook entries for 4 column(s)  
  *evidence:* not in any codebook: text_layer_status_after, ocr_shard, ocr_chars_on_disk, ocr_chars_agreement
- **C5 / medium** · `gaming_ordinance_ocr.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `gaming_ordinances.csv` — write codebook entries for 1 column(s)  
  *evidence:* not in any codebook: tribe_id_as_built
- **C5 / medium** · `gaming_ordinances.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `gaming_project_facilities.csv` — drop 4 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 19 rows: entity_id, facility_name, projected_opening, cedar_uid
- **C5 / medium** · `gaming_project_facilities.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `gaming_projections.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `gaming_properties.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 784 rows: source_url
- **C5 / medium** · `gaming_properties.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `gaming_property_federal_traces.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `gaming_property_labor_demand.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 43 rows: supersedes_observation_id
- **C5 / medium** · `gaming_property_labor_demand.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `gaming_property_site_observations.csv` — drop 2 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 262 rows: site_name_as_published, supersedes_observation_id
- **C5 / medium** · `gaming_property_site_observations.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `gaming_property_universe_events.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 10 rows: link_anachronism_note
- **C5 / medium** · `gaming_property_universe_events.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `gaming_revenue_bounds.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `gaming_source_claims.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 113 rows: effective_date
- **C11 / medium** · `gaming_vendor_tribal_licenses.csv` — drop 4 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 740 rows: license_number, application_date, approval_date, measurement_type
- **C5 / medium** · `gaming_vendor_tribal_licenses.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `loyalty_program_property.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 48 rows: source_url
- **C5 / medium** · `loyalty_program_property.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `loyalty_programs.csv` — drop 8 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 18 rows: start_date, end_date, tier_names, tier_thresholds ...
- **C5 / medium** · `loyalty_programs.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `nigc_declination_letters.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `nigc_region_assignments.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `nigc_regional_ggr.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `nigc_revenue_bands.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `state_gaming_observations.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 494 rows: fetched_date
- **C5 / medium** · `state_gaming_observations.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `wa_machine_allocations.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C9 / low** · `(dataset)` — have a DIFFERENT session execute the runbook from the document alone - written is not tested  
  *evidence:* runbook exists, execution never verified

## `_entity_layer`

- **C12 / high** · `admin_region_overlap_derived.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `admin_region_systems.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `admin_regions.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `bie_uio_dollars_by_entity.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `cedar_correction_register.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C1 / high** · `cedar_identifier_graph_edges.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `cedar_identifier_graph_edges.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C3 / high** · `cedar_identifier_graph_edges.csv` — diagnose the duplicate source (ingest / join / repeated source rows / legitimate dimension) and FIX THE PIPELINE, or declare the distinguishing dimension  
  *evidence:* 2,451 literal duplicate rows
- **C1 / high** · `cedar_ruling_ledger_consolidated.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `cedar_ruling_ledger_consolidated.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C3 / high** · `cedar_ruling_ledger_consolidated.csv` — diagnose the duplicate source (ingest / join / repeated source rows / legitimate dimension) and FIX THE PIPELINE, or declare the distinguishing dimension  
  *evidence:* 6,302 literal duplicate rows
- **C1 / high** · `cross_dataset_ruling_map.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `cross_dataset_ruling_map.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C3 / high** · `cross_dataset_ruling_map.csv` — diagnose the duplicate source (ingest / join / repeated source rows / legitimate dimension) and FIX THE PIPELINE, or declare the distinguishing dimension  
  *evidence:* 2,228 literal duplicate rows
- **C12 / high** · `cross_dataset_ruling_map.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `federal_recognition_roster.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `foia_discovery_targets.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C1 / high** · `foia_request_index.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `foia_request_index.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C12 / high** · `intertribal_memberships.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C1 / high** · `tcu_cdfi_ownership_evidence.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `tcu_cdfi_ownership_evidence.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C3 / high** · `tcu_cdfi_ownership_evidence.csv` — diagnose the duplicate source (ingest / join / repeated source rows / legitimate dimension) and FIX THE PIPELINE, or declare the distinguishing dimension  
  *evidence:* 4 literal duplicate rows
- **C12 / high** · `tcu_cdfi_ownership_evidence.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C1 / high** · `visitor_record_foia_requests.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `visitor_record_foia_requests.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C8 / high** · `(dataset)` — establish a rebuild path that does not destroy later enrichment; declare the ordering in KNOWN_ORDERINGS  
  *evidence:* rebuild is DESTRUCTIVE: 01_build_entity_spine.py|09_import_rulings.py
- **C9 / high** · `(dataset)` — write docs/datasets/_entity_layer.md - fetch -> normalize -> resolve -> enrich -> validate -> build -> ship, executable by a session with no history  
  *evidence:* no runbook
- **C11 / medium** · `admin_region_assignments.csv` — drop 3 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 2,124 rows: effective_start_date, effective_end_date, effective_end_year
- **C5 / medium** · `admin_region_assignments.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `admin_region_overlap_derived.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `admin_region_systems.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 6 rows: effective_end_year
- **C5 / medium** · `admin_region_systems.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `admin_regional_observations.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `admin_regions.csv` — drop 2 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 155 rows: effective_start_date, effective_end_date
- **C5 / medium** · `admin_regions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `bie_uio_dollars_by_entity.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `cedar_correction_register.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `cedar_entity_identity_crosswalk.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `cedar_identifier_graph_edges.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `cedar_identifier_graph_nodes.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `cedar_identifier_ledger_final.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `cedar_identifier_propagation.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `cedar_publishable_identifiers.csv` — drop 2 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 1,577 rows: exclusion_id, exclusion_evidence
- **C5 / medium** · `cedar_publishable_identifiers.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `cedar_ruling_ledger_consolidated.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `cross_dataset_ruling_map.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `entity_aliases.csv` — drop 3 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 6,296 rows: start_date, first_observed_date, last_observed_date
- **C5 / medium** · `entity_hierarchy.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `entity_relationships.csv` — drop 2 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 2,292 rows: start_date, end_date
- **C5 / medium** · `entity_relationships.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `entity_year_panel.csv` — drop 4 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 12,534 rows: n_deals, deal_value_usd, n_bills_affecting, n_compacts_active
- **C5 / medium** · `entity_year_panel.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `federal_recognition_events.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `federal_recognition_roster.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 17,058 rows: parent_fr_name
- **C5 / medium** · `federal_recognition_roster.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `foia_discovery_targets.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `foia_request_index.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 9,481 rows: release_url
- **C11 / medium** · `foia_request_index.csv` — write codebook entries for 6 column(s)  
  *evidence:* not in any codebook: tribe_entity_id_withdrawn, tribe_entity_link_withdrawn, tribe_entity_link_withdrawn_reason, tribe_entity_link_withdrawn_evidence_verbatim ...
- **C5 / medium** · `foia_request_index.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `intertribal_memberships.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 989 rows: member_entity_id
- **C5 / medium** · `intertribal_memberships.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `intertribal_orgs.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `native_fi_roster.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `nho_doi_notification_roster.csv` — drop 5 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 190 rows: verification_8a, uei, cage_code, is_federal_contractor ...
- **C5 / medium** · `nho_doi_notification_roster.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `nho_ownership_changes.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 9 rows: effective_date
- **C5 / medium** · `nho_ownership_changes.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `nho_register.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `nho_verified_entities.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 36 rows: cedar_uid
- **C5 / medium** · `nho_verified_entities.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `tcu_cdfi_added.csv` — drop 8 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 130 rows: bia_region, self_governance, cedar_entity_id, ultimate_parent_entity_id ...
- **C5 / medium** · `tcu_cdfi_added.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `tcu_cdfi_ownership_evidence.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `tcu_roster.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `visitor_access_events.csv` — drop 5 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 20 rows: appointment_cancelled_date, native_entity_id, organisation_id, matter_id ...
- **C5 / medium** · `visitor_access_events.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `visitor_record_foia_requests.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 667 rows: release_url
- **C11 / medium** · `visitor_record_foia_requests.csv` — write codebook entries for 2 column(s)  
  *evidence:* not in any codebook: request_description_verbatim, discovery_role
- **C5 / medium** · `visitor_record_foia_requests.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage

## `lobbying`

- **C1 / high** · `admin_appeal_positions.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `admin_appeal_positions.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C12 / high** · `agency_attention_vs_advocacy_year.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C1 / high** · `ferc_docket_filings.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `ferc_docket_filings.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C3 / high** · `ferc_docket_filings.csv` — diagnose the duplicate source (ingest / join / repeated source rows / legitimate dimension) and FIX THE PIPELINE, or declare the distinguishing dimension  
  *evidence:* 822 literal duplicate rows
- **C1 / high** · `ferc_ex_parte_communications.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `ferc_ex_parte_communications.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C1 / high** · `hearing_bill_links.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `hearing_bill_links.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C3 / high** · `hearing_bill_links.csv` — diagnose the duplicate source (ingest / join / repeated source rows / legitimate dimension) and FIX THE PIPELINE, or declare the distinguishing dimension  
  *evidence:* 1 literal duplicate rows
- **C12 / high** · `lobbying_disclosure_verbosity_year.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `lobbying_issue_families_filing.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `lobbying_issue_family_year.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `lobbying_registrant_client_relationships.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C1 / high** · `lobbying_registrant_native_ownership_evidence.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `lobbying_registrant_native_ownership_evidence.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C3 / high** · `lobbying_registrant_native_ownership_evidence.csv` — diagnose the duplicate source (ingest / join / repeated source rows / legitimate dimension) and FIX THE PIPELINE, or declare the distinguishing dimension  
  *evidence:* 4 literal duplicate rows
- **C12 / high** · `lobbying_target_entities.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `tribe_year_lobbying_panel.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C9 / high** · `(dataset)` — write docs/datasets/lobbying.md - fetch -> normalize -> resolve -> enrich -> validate -> build -> ship, executable by a session with no history  
  *evidence:* no runbook
- **C11 / medium** · `admin_appeal_decisions.csv` — drop 7 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 15,613 rows: disposition, native_petitioner_entity_ids, native_petitioner_entity_names, native_estate_subject_entity_ids ...
- **C5 / medium** · `admin_appeal_decisions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `admin_appeal_parties.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `admin_appeal_positions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `advocacy_passthrough.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 1,620 rows: recipient_lobbying_expenditure
- **C5 / medium** · `advocacy_passthrough.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `advocacy_passthrough_2026-08-07.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `agency_attention_vs_advocacy.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `agency_attention_vs_advocacy_year.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `earmarks.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `ferc_docket_filings.csv` — drop 2 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 20,001 rows: issued_date, lobbying_position
- **C5 / medium** · `ferc_docket_filings.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `ferc_docket_parties.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `ferc_ex_parte_communications.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 713 rows: issued_date
- **C5 / medium** · `ferc_ex_parte_communications.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `ferc_ex_parte_parties.csv` — drop 2 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 4,246 rows: position_relative_to_native_interest, entity_link_built_by_script
- **C5 / medium** · `ferc_ex_parte_parties.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `ferc_tribal_dockets.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `fr_ex_parte_parties.csv` — drop 5 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 112 rows: resolved_native_entity_id, resolved_native_entity_name, resolution_method, position_relative_to_native_interest ...
- **C11 / medium** · `hearing_appearances.csv` — write codebook entries for 2 column(s)  
  *evidence:* not in any codebook: promoted_by_script, promotion_basis
- **C5 / medium** · `hearing_appearances.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `hearing_bill_links.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `lobbying_disclosure_verbosity_year.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `lobbying_issue_families_filing.csv` — drop 4 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 20,001 rows: entity_id_withdrawn, entity_id_withdrawn_reason, entity_id_withdrawn_by_script, entity_id_withdrawn_date
- **C5 / medium** · `lobbying_issue_families_filing.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `lobbying_issue_family_year.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `lobbying_registrant_client_relationships.csv` — write codebook entries for 4 column(s)  
  *evidence:* not in any codebook: native_entity_id_withdrawn, native_entity_id_withdrawn_reason, native_entity_id_withdrawn_by_script, native_entity_id_withdrawn_date
- **C5 / medium** · `lobbying_registrant_client_relationships.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `lobbying_registrant_concentration.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `lobbying_registrant_identifiers.csv` — drop 4 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 525 rows: np_990_form_type, np_990_filing_regime, np_990_lobbying_field_basis, np_990_schedc_total_lobbying
- **C5 / medium** · `lobbying_registrant_identifiers.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `lobbying_registrant_native_ownership_evidence.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `lobbying_registrants.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `lobbying_target_entities.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `native_entity_lobbying_disclosures.csv` — drop 8 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 20,001 rows: expenses_usd, org_type_barred, org_type_reason, attribution_withdrawn ...
- **C11 / medium** · `native_entity_lobbying_disclosures.csv` — write codebook entries for 5 column(s)  
  *evidence:* not in any codebook: attribution_withdrawn, attribution_withdrawn_entity_id, attribution_withdrawn_reason, attribution_withdrawn_by_script ...
- **C5 / medium** · `native_entity_lobbying_disclosures.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `nrc_meeting_participants.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `nrc_public_meetings.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `oira_federal_action_links.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `oira_meeting_participants.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `oira_meetings.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `tribe_year_lobbying_panel.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage

## `funding`

- **C7 / critical** · `faads_transactions.csv` — a buyer will total this table and get a wrong answer - resolve grain/duplicates before it ships as analytical  
  *evidence:* money columns obligated_usd on an aggregation-unsafe table
- **C7 / critical** · `faads_transactions_all_agencies.csv` — a buyer will total this table and get a wrong answer - resolve grain/duplicates before it ships as analytical  
  *evidence:* money columns obligated_usd on an aggregation-unsafe table
- **C7 / critical** · `native_passthrough.csv` — a buyer will total this table and get a wrong answer - resolve grain/duplicates before it ships as analytical  
  *evidence:* money columns amount_usd|amount_countable on an aggregation-unsafe table
- **C12 / high** · `bie_uio_dollars_by_entity.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C1 / high** · `faads_transactions.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `faads_transactions.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C3 / high** · `faads_transactions.csv` — diagnose the duplicate source (ingest / join / repeated source rows / legitimate dimension) and FIX THE PIPELINE, or declare the distinguishing dimension  
  *evidence:* 1,001 literal duplicate rows
- **C12 / high** · `faads_transactions.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C1 / high** · `faads_transactions_all_agencies.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `faads_transactions_all_agencies.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C3 / high** · `faads_transactions_all_agencies.csv` — diagnose the duplicate source (ingest / join / repeated source rows / legitimate dimension) and FIX THE PIPELINE, or declare the distinguishing dimension  
  *evidence:* 179,259 literal duplicate rows
- **C12 / high** · `faads_transactions_all_agencies.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `federal_funding_tribe_year_panel.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `funding_identifier_netnew_ueis.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `inflation_deflator.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C1 / high** · `native_passthrough.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `native_passthrough.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C3 / high** · `native_passthrough.csv` — diagnose the duplicate source (ingest / join / repeated source rows / legitimate dimension) and FIX THE PIPELINE, or declare the distinguishing dimension  
  *evidence:* 114 literal duplicate rows
- **C12 / high** · `native_passthrough.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `native_passthrough_pairs.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C9 / high** · `(dataset)` — write docs/datasets/funding.md - fetch -> normalize -> resolve -> enrich -> validate -> build -> ship, executable by a session with no history  
  *evidence:* no runbook
- **C4 / high** · `(dataset)` — attach the unkeyed rows to the entity layer (dataset 13) - this dataset's subject IS an entity, so unkeyed is unresolved work, not scope  
  *evidence:* 40% keyed keyed, scope=entity
- **C5 / medium** · `bie_uio_dollars_by_entity.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `faads_entity_attribution.csv` — write codebook entries for 6 column(s)  
  *evidence:* not in any codebook: faads_row_id, spine_state, state_check, state_check_passed ...
- **C5 / medium** · `faads_entity_attribution.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `faads_transactions.csv` — drop 5 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 20,001 rows: recipient_duns, tribe_id, recipient_uei, assistance_type_description ...
- **C5 / medium** · `faads_transactions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `faads_transactions_all_agencies.csv` — drop 5 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 20,001 rows: recipient_duns, tribe_id, recipient_uei, assistance_type_description ...
- **C5 / medium** · `faads_transactions_all_agencies.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `federal_funding_transactions.csv` — drop 13 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 20,001 rows: face_value_of_loan, original_loan_subsidy_cost, total_face_value_of_loan, total_loan_subsidy_cost ...
- **C11 / medium** · `federal_funding_transactions.csv` — write codebook entries for 8 column(s)  
  *evidence:* not in any codebook: tribe_id_scheme_resolved, tribe_id_scheme_resolved_basis, tribe_id_neid_proposed, tribe_id_neid_proposed_tier ...
- **C5 / medium** · `federal_funding_transactions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `federal_funding_tribe_year_panel.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `funding_identifier_netnew_ueis.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `inflation_deflator.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `native_passthrough.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `native_passthrough_pairs.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage

## `deals`

- **C7 / critical** · `deals_2026_ytd_additions.csv` — a buyer will total this table and get a wrong answer - resolve grain/duplicates before it ships as analytical  
  *evidence:* money columns Announced_Value_USD|Value_Type|Project_Total_Value_USD on an aggregation-unsafe table
- **C7 / critical** · `tribal_resolution_financings.csv` — a buyer will total this table and get a wrong answer - resolve grain/duplicates before it ships as analytical  
  *evidence:* money columns principal_amount_text|pledged_revenues_text on an aggregation-unsafe table
- **C1 / high** · `deals_2026_ytd_additions.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `deals_2026_ytd_additions.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C12 / high** · `deals_source_index.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C1 / high** · `tribal_resolution_financings.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `tribal_resolution_financings.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C8 / high** · `(dataset)` — establish a rebuild path that does not destroy later enrichment; declare the ordering in KNOWN_ORDERINGS  
  *evidence:* rebuild is DESTRUCTIVE: 88_build_deals_taxonomy.py
- **C9 / high** · `(dataset)` — write docs/datasets/deals.md - fetch -> normalize -> resolve -> enrich -> validate -> build -> ship, executable by a session with no history  
  *evidence:* no runbook
- **C5 / medium** · `deals_2000_2019_additions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `deals_2026_ytd_additions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `deals_anc_reports_additions.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 28 rows: Project_Total_Value_USD
- **C5 / medium** · `deals_anc_reports_additions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `deals_ancsa_portal_additions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `deals_ancsa_portal_v2_additions.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 42 rows: Project_Total_Value_USD
- **C5 / medium** · `deals_ancsa_portal_v2_additions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `deals_classified.csv` — write codebook entries for 17 column(s)  
  *evidence:* not in any codebook: _source_file, record_class, transaction_type, capital_source ...
- **C5 / medium** · `deals_classified.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `deals_federal_awards_additions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `deals_historical_additions.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 30 rows: Project_Total_Value_USD
- **C5 / medium** · `deals_historical_additions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `deals_sec_2010_2017_additions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `deals_source_index.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `deals_tribal_debt_additions.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 6 rows: Project_Total_Value_USD
- **C5 / medium** · `deals_tribal_debt_additions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `ownership_events.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `seminole_bond_disclosures.csv` — drop 3 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 29 rows: filer_cik, measurement_type, source_page
- **C5 / medium** · `seminole_bond_disclosures.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `tribal_resolution_financings.csv` — drop 9 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 1 rows: instrument_number, borrower, principal_amount_text, interest_formula_text ...
- **C5 / medium** · `tribal_resolution_financings.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage

## `contractors`

- **C7 / critical** · `contractor_ranking.csv` — a buyer will total this table and get a wrong answer - resolve grain/duplicates before it ships as analytical  
  *evidence:* money columns owner_obligations_usd|owner_native_setaside_usd|owner_8a_usd|owner_native_specific_setaside_usd|owner_no_setaside_usd_award_level|firm_obligations_usd on an aggregation-unsafe table
- **C1 / high** · `contractor_ranking.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `contractor_ranking.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C1 / high** · `fpds_uei_cage_map.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `fpds_uei_cage_map.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C12 / high** · `fpds_uei_cage_map.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `fpds_uei_edges.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `prime_contracts_published.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C9 / high** · `(dataset)` — write docs/datasets/contractors.md - fetch -> normalize -> resolve -> enrich -> validate -> build -> ship, executable by a session with no history  
  *evidence:* no runbook
- **C4 / high** · `(dataset)` — attach the unkeyed rows to the entity layer (dataset 13) - this dataset's subject IS an entity, so unkeyed is unresolved work, not scope  
  *evidence:* 59% keyed keyed, scope=entity
- **C5 / medium** · `contractor_ranking.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `fpds_uei_cage_map.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `fpds_uei_edges.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `prime_contracts.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 20,001 rows: contract_transaction_unique_key
- **C5 / medium** · `prime_contracts.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `prime_contracts_archive_backfill.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `prime_contracts_awards.csv` — write codebook entries for 4 column(s)  
  *evidence:* not in any codebook: first_award_fy, last_action_fy, max_award_value_usd, cumulative_snapshot_flag
- **C5 / medium** · `prime_contracts_awards.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `prime_contracts_entity_year.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `prime_contracts_published.csv` — write codebook entries for 4 column(s)  
  *evidence:* not in any codebook: first_award_fy, last_action_fy, max_award_value_usd, cumulative_snapshot_flag
- **C5 / medium** · `prime_contracts_published.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `sam_prime_contracts_fy2000_2007.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `sam_prime_contracts_fy2000_2007_PUBLISHABLE.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage

## `legislation`

- **C12 / high** · `bill_votes_official_verification.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C1 / high** · `congressional_correspondence_log.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `congressional_correspondence_log.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C12 / high** · `member_positions.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C1 / high** · `native_bills_subject_sweep.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `native_bills_subject_sweep.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C3 / high** · `native_bills_subject_sweep.csv` — diagnose the duplicate source (ingest / join / repeated source rows / legitimate dimension) and FIX THE PIPELINE, or declare the distinguishing dimension  
  *evidence:* 5 literal duplicate rows
- **C9 / high** · `(dataset)` — write docs/datasets/legislation.md - fetch -> normalize -> resolve -> enrich -> validate -> build -> ship, executable by a session with no history  
  *evidence:* no runbook
- **C5 / medium** · `bill_votes.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `bill_votes_entity_bridge.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `bill_votes_official_verification.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `congressional_correspondence_log.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `congressional_correspondence_systems.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `member_positions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `native_bill_outcomes.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `native_bills.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 3,069 rows: affected_entities
- **C5 / medium** · `native_bills.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `native_bills_entity_bridge.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `native_bills_entity_class.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `native_bills_subject_sweep.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 2,414 rows: subjects
- **C5 / medium** · `native_bills_subject_sweep.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `native_issue_litigation_positions.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage

## `nonprofits`

- **C7 / critical** · `np_schedule_i_grants.csv` — a buyer will total this table and get a wrong answer - resolve grain/duplicates before it ships as analytical  
  *evidence:* money columns cash_grant_usd|noncash_assistance_usd on an aggregation-unsafe table
- **C1 / high** · `np_schedule_i_grants.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `np_schedule_i_grants.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C3 / high** · `np_schedule_i_grants.csv` — diagnose the duplicate source (ingest / join / repeated source rows / legitimate dimension) and FIX THE PIPELINE, or declare the distinguishing dimension  
  *evidence:* 101 literal duplicate rows
- **C9 / high** · `(dataset)` — write docs/datasets/nonprofits.md - fetch -> normalize -> resolve -> enrich -> validate -> build -> ship, executable by a session with no history  
  *evidence:* no runbook
- **C11 / medium** · `fac_tribal_single_audits.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 6,780 rows: measurement_type
- **C5 / medium** · `fac_tribal_single_audits.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `grantmaker_funding_flows.csv` — drop 15 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 18,656 rows: cedar_funder_spine_entity_id, cedar_funder_spine_canonical_name, cedar_funder_spine_entity_class, cedar_funder_native_entity_class ...
- **C5 / medium** · `grantmaker_funding_flows.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `grantmaker_funding_overlap.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `np_ein_entity_hub.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `np_financials.csv` — drop 5 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 8,507 rows: lobbying_expenditure, n_employees, schedc_dues_lobbying_political, form990pf_influence_legislation_ind ...
- **C5 / medium** · `np_financials.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `np_grantee_financials.csv` — write codebook entries for 5 column(s)  
  *evidence:* not in any codebook: schedc_filed, grassroots_lobbying, direct_lobbying, political_activity ...
- **C5 / medium** · `np_grantee_financials.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `np_org_scale.csv` — write codebook entries for 9 column(s)  
  *evidence:* not in any codebook: api_status, n_filings_returned, n_filings_with_financials, latest_filing_year ...
- **C5 / medium** · `np_org_scale.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `np_orgs.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `np_schedule_i_filers.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `np_schedule_i_grants.csv` — write codebook entries for 11 column(s)  
  *evidence:* not in any codebook: recipient_address, noncash_valuation_method, noncash_description, recipient_np_orgs_name ...
- **C5 / medium** · `np_schedule_i_grants.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage

## `natural-resources`

- **C7 / critical** · `tribal_bond_issuances.csv` — a buyer will total this table and get a wrong answer - resolve grain/duplicates before it ships as analytical  
  *evidence:* money columns par_amount on an aggregation-unsafe table
- **C12 / high** · `ancsa_filings_index.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C1 / high** · `tribal_bond_issuances.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `tribal_bond_issuances.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C9 / high** · `(dataset)` — write docs/datasets/natural-resources.md - fetch -> normalize -> resolve -> enrich -> validate -> build -> ship, executable by a session with no history  
  *evidence:* no runbook
- **C4 / high** · `(dataset)` — attach the unkeyed rows to the entity layer (dataset 13) - this dataset's subject IS an entity, so unkeyed is unresolved work, not scope  
  *evidence:* 28% keyed keyed, scope=entity
- **C11 / medium** · `anc_ceiling_roster.csv` — drop 2 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 196 rows: uei, cage_code
- **C5 / medium** · `anc_ceiling_roster.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `ancsa_filings_index.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 19,269 rows: filing_date
- **C5 / medium** · `ancsa_filings_index.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `nd_severance_allocation.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `resource_assets.csv` — drop 10 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 35 rows: niogems_lease_id, niogems_tract_id, niogems_agreement_id, niogems_well_id ...
- **C11 / medium** · `resource_assets.csv` — write codebook entries for 12 column(s)  
  *evidence:* not in any codebook: legal_title_holder, beneficial_interest_class, area_acres, area_unit ...
- **C5 / medium** · `resource_assets.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `resource_parties.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `resource_revenue.csv` — drop 3 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 10,482 rows: operator_entity_id, operator_entity_name, related_asset_ids
- **C5 / medium** · `resource_revenue.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `tribal_bond_issuances.csv` — drop 2 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 29 rows: issuer_entity_id, cusip
- **C5 / medium** · `tribal_bond_issuances.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `tribal_tax_bases.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage

## `federal-register`

- **C12 / high** · `correspondence_foia_source_coverage.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `fr_abstract_availability_year.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `fr_consultation_by_agency.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `fr_consultation_year.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `fr_theme_year.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C12 / high** · `section_106_source_coverage.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C11 / medium** · `consultation_events.csv` — write codebook entries for 7 column(s)  
  *evidence:* not in any codebook: topic, event_start_date, event_end_date, format ...
- **C11 / medium** · `federal_actions.csv` — drop 2 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 20,001 rows: comment_url, tribe_or_native_entity
- **C11 / medium** · `federal_actions_raw.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 20,001 rows: comment_url
- **C11 / medium** · `fr_ex_parte_parties.csv` — drop 5 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 112 rows: resolved_native_entity_id, resolved_native_entity_name, resolution_method, position_relative_to_native_interest ...
- **C11 / medium** · `nepa_administrative_record_parties.csv` — drop 2 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 36 rows: administrative_record_position_quote, lobbying_position
- **C11 / medium** · `nepa_project_documents.csv` — drop 2 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 789 rows: administrative_record_position_quote, lobbying_position
- **C11 / medium** · `section_106_project_parties.csv` — drop 4 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 51 rows: resolved_native_entity_id, resolved_native_entity_name, resolution_method, cedar_uid
- **C9 / low** · `(dataset)` — have a DIFFERENT session execute the runbook from the document alone - written is not tested  
  *evidence:* runbook exists, execution never verified

## `subcontracting`

- **C7 / critical** · `subawards.csv` — a buyer will total this table and get a wrong answer - resolve grain/duplicates before it ships as analytical  
  *evidence:* money columns subaward_amount|prime_award_amount|subaward_amount_real2025 on an aggregation-unsafe table
- **C12 / high** · `prime_sub_network.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C1 / high** · `subawards.csv` — declare grain + PK + join keys + cardinality in 512, validated on the full file  
  *evidence:* grain UNSTATED
- **C2 / high** · `subawards.csv` — establish and declare a validated primary key  
  *evidence:* no PK declared
- **C3 / high** · `subawards.csv` — diagnose the duplicate source (ingest / join / repeated source rows / legitimate dimension) and FIX THE PIPELINE, or declare the distinguishing dimension  
  *evidence:* 10,770 literal duplicate rows
- **C9 / high** · `(dataset)` — write docs/datasets/subcontracting.md - fetch -> normalize -> resolve -> enrich -> validate -> build -> ship, executable by a session with no history  
  *evidence:* no runbook
- **C4 / high** · `(dataset)` — attach the unkeyed rows to the entity layer (dataset 13) - this dataset's subject IS an entity, so unkeyed is unresolved work, not scope  
  *evidence:* 42% keyed keyed, scope=entity
- **C5 / medium** · `prime_sub_network.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `subaward_entity_rollup.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `subawards.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 20,001 rows: pre_2000_flag
- **C5 / medium** · `subawards.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage

## `native-owned-businesses`

- **C12 / high** · `individual_native_firm_contracts_published.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C9 / high** · `(dataset)` — write docs/datasets/native-owned-businesses.md - fetch -> normalize -> resolve -> enrich -> validate -> build -> ship, executable by a session with no history  
  *evidence:* no runbook
- **C5 / medium** · `individual_native_exclusion_pairs.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `individual_native_firm_contracts.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `individual_native_firm_contracts_published.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `individual_native_firm_register.csv` — drop 3 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 45 rows: owner_tribal_affiliation_resolved_to_tribe_id, consent_date, consent_source
- **C5 / medium** · `individual_native_firm_register.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C5 / medium** · `individual_native_ownership_verification.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage
- **C11 / medium** · `individual_native_verification_candidates.csv` — drop 11 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 335 rows: self_description_sentence, self_description_url, self_description_fetch_date, self_description_http_status ...
- **C5 / medium** · `individual_native_verification_candidates.csv` — add row-conservation: every source row into a NAMED bucket, merged into cedar_harvest_conservation.csv  
  *evidence:* no conservation coverage

## `nagpra`

- **C12 / high** · `fr_nagpra_title_index_year.csv` — add an inclusion basis - a row must be able to say WHY it is in Cedar (ADR-013: named_entity / term_match / program_authority / geographic / subject_classification / human_ruling)  
  *evidence:* no basis column of any kind
- **C11 / medium** · `nagpra_notices.csv` — drop 1 always-empty column(s) with a correction-register row, or populate them  
  *evidence:* always empty in 6,772 rows: fetched_date
- **C11 / medium** · `nagpra_notices.csv` — write codebook entries for 1 column(s)  
  *evidence:* not in any codebook: artifact_mtime
- **C9 / low** · `(dataset)` — have a DIFFERENT session execute the runbook from the document alone - written is not tested  
  *evidence:* runbook exists, execution never verified