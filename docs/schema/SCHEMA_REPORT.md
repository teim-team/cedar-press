# Generated schema report

*Written 2026-08-26 by `code/285_build_table_schemas.py`. Regenerate; do not edit.*

**220 of 271 tables are ingest-ready (81.2%).**

| status | tables |
|---|---:|
| `READY` | 220 |
| `BLOCKED_UNSTABLE_KEY` | 28 |
| `BLOCKED_NO_STABLE_KEY` | 21 |
| `REFUSED_LICENSED_SOURCE` | 2 |

## Licence gate

Refused at the column definition, so nothing downstream can emit them.

| table | column | populated | reason |
|---|---|---:|---|
| `federal_funding_transactions.csv` | `recipient_duns` | 253,453 | licensed identifier (cedar_codebook.is_licensed_col) |
| `faads_transactions_all_agencies.csv` | `recipient_duns` | 152,899 | licensed identifier (cedar_codebook.is_licensed_col) |
| `funding_identifier_harvest.csv` | `recipient_duns` | 9,015 | licensed identifier (cedar_codebook.is_licensed_col) |
| `gaming_facilities.csv` | `casino_city_id` | 595 | licensed identifier (cedar_codebook.is_licensed_col) |
| `bie_uio_identifier_links.csv` | `duns_internal_only` | 144 | licensed identifier (cedar_codebook.is_licensed_col) |
| `faads_identifier_coverage_by_agency_year.csv` | `pct_with_duns` | 77 | licensed identifier (cedar_codebook.is_licensed_col) |
| `faads_identifier_coverage_by_agency_year.csv` | `pct_with_duns_tribal_rows_only` | 77 | licensed identifier (cedar_codebook.is_licensed_col) |
| `faads_transactions.csv` | `recipient_duns` | 1 | licensed identifier (cedar_codebook.is_licensed_col) |
| `subaward_identifier_harvest.csv` | `duns` | 0 | licensed identifier (cedar_codebook.is_licensed_col) |
| `subaward_identifier_netnew.csv` | `duns` | 0 | licensed identifier (cedar_codebook.is_licensed_col) |

## Blocked for ingest

| table | why |
|---|---|
| `admin_regional_observations.csv` | minted by 85_build_admin_region_crosswalk.py:743 (POSITIONAL) - unique in this build, not stable across builds |
| `advocacy_passthrough.csv` | minted by 111_build_advocacy_passthrough.py:975 (POSITIONAL) - unique in this build, not stable across builds |
| `advocacy_passthrough_2026-08-07.csv` | minted by 111_build_advocacy_passthrough.py:975 (POSITIONAL) - unique in this build, not stable across builds |
| `anc_ceiling_roster.csv` | minted by 07_parse_ancsa_ceiling.py:163 (POSITIONAL) - unique in this build, not stable across builds |
| `cedar_identifier_graph_edges.csv` | no unique key found. Best candidate (from_node, evidence) still has 2,456 duplicate and 0 all-blank rows; the full row has 2,451 exact duplicates. |
| `cedar_identifier_ledger_final.csv` | minted by 02_extract_exclusion_rulings.py:116 (POSITIONAL) - unique in this build, not stable across builds |
| `cedar_identifier_ledger_tiered.csv` | minted by 02_extract_exclusion_rulings.py:116 (POSITIONAL) - unique in this build, not stable across builds |
| `cedar_ruling_ledger_consolidated.csv` | no unique key found. Best candidate (subject_key, ruling, source_file) still has 6,672 duplicate and 0 all-blank rows; the full row has 6,325 exact duplicates. |
| `codebook_master.csv` | no unique key found. Best candidate (variable, dataset) still has 39 duplicate and 0 all-blank rows; the full row has 1 exact duplicates. |
| `compact_events.csv` | minted by 15b_build_compact_index.py:262 (POSITIONAL) - unique in this build, not stable across builds |
| `compact_required_reports.csv` | minted by 95_parse_compact_terms.py:1614 (POSITIONAL) - unique in this build, not stable across builds |
| `compact_structured_terms.csv` | minted by 95_parse_compact_terms.py:1560 (POSITIONAL) - unique in this build, not stable across builds |
| `congressional_correspondence_log.csv` | no column is >=99% populated; every candidate carries blanks, so nothing can be NOT NULL |
| `cross_dataset_ruling_map.csv` | no unique key found. Best candidate (identifier, ruling, dataset) still has 2,228 duplicate and 0 all-blank rows; the full row has 2,228 exact duplicates. |
| `deals_2026_ytd_additions.csv` | no column is >=99% populated; every candidate carries blanks, so nothing can be NOT NULL |
| `entity_candidates_new.csv` | DUPLICATE COLUMN NAMES (entity_category, parent_native_entity, parent_requirement, record_complete, roll_up_target, serves_basis, serves_native_entities). Every SQL dialect refuses the CREATE TABLE; the table cannot be ingested at all until the producing script disambiguates them. |
| `entity_candidates_rejected.csv` | DUPLICATE COLUMN NAMES (entity_category, parent_native_entity, parent_requirement, record_complete, roll_up_target, serves_basis, serves_native_entities). Every SQL dialect refuses the CREATE TABLE; the table cannot be ingested at all until the producing script disambiguates them. |
| `faads_transactions.csv` | no unique key found. Best candidate (source_url, award_id_fain, obligated_usd, recipient_name) still has 2,831 duplicate and 0 all-blank rows; the full row has 1,001 exact duplicates. |
| `faads_transactions_all_agencies.csv` | no unique key found. Best candidate (source_url, award_id_fain, recipient_name, obligated_usd) still has 19,110 duplicate and 0 all-blank rows; the full row has 8,912 exact duplicates. |
| `ferc_docket_filings.csv` | no unique key found. Best candidate (accession_number, source_url, document_description_verbatim, docket_number) still has 9,570 duplicate and 0 all-blank rows; the full row has 822 exact duplicates. |
| `ferc_docket_parties.csv` | minted by 168_link_adjudication_hubs.py:786 (POSITIONAL) - unique in this build, not stable across builds |
| `fpds_uei_cage_map.csv` | no unique key found. Best candidate (uei, legal_business_name, n_observations, first_year) still has 14 duplicate and 0 all-blank rows; the full row has 2 exact duplicates. |
| `gaming_capacity_official.csv` | minted by 92_build_gaming_capacity_official.py:382 (POSITIONAL) - unique in this build, not stable across builds |
| `gaming_decision_events.csv` | minted by 23b_build_gaming_land_decisions.py:380 (POSITIONAL) - unique in this build, not stable across builds |
| `gaming_employment_observations.csv` | minted by 100_finish_declinations_and_employment.py:1580 (POSITIONAL) - unique in this build, not stable across builds |
| `gaming_manufacturer_facts.csv` | minted by 117_build_gaming_devices.py:623 (POSITIONAL) - unique in this build, not stable across builds |
| `gaming_ordinance_ocr.csv` | minted by 118_build_gaming_ordinances.py:295 (POSITIONAL) - unique in this build, not stable across builds |
| `gaming_ordinances.csv` | minted by 118_build_gaming_ordinances.py:295 (POSITIONAL) - unique in this build, not stable across builds |
| `gaming_property_locations.csv` | minted by 143_build_gaming_property_locations.py:953 (POSITIONAL) - unique in this build, not stable across builds |
| `hearing_bill_links.csv` | no unique key found. Best candidate (bill_id, event_id) still has 1 duplicate and 0 all-blank rows; the full row has 1 exact duplicates. |
| `individual_native_ownership_verification.csv` | minted by 170_build_individual_native_candidates.py:482 (RANK_DERIVED) - unique in this build, not stable across builds |
| `individual_native_verification_candidates.csv` | minted by 170_build_individual_native_candidates.py:482 (RANK_DERIVED) - unique in this build, not stable across builds |
| `lobbying_registrant_native_ownership_evidence.csv` | no unique key found. Best candidate (registrant_id, native_entity_id, evidence_verbatim) still has 7 duplicate and 0 all-blank rows; the full row has 4 exact duplicates. |
| `native_bills_subject_sweep.csv` | no unique key found. Best candidate (bill_id) still has 5 duplicate and 0 all-blank rows; the full row has 5 exact duplicates. |
| `native_passthrough.csv` | no unique key found. Best candidate (subaward_number, prime_award_id, to_tribe_id) still has 469 duplicate and 0 all-blank rows; the full row has 121 exact duplicates. |
| `nho_doi_notification_roster.csv` | minted by 05_parse_doi_nho_list.py:90 (POSITIONAL) - unique in this build, not stable across builds |
| `nho_ownership_changes.csv` | minted by 61_add_nho_intertribal_to_spine.py:496 (POSITIONAL) - unique in this build, not stable across builds |
| `nigc_declination_letters.csv` | minted by 90_fetch_nigc_declinations.py:209 (POSITIONAL) - unique in this build, not stable across builds |
| `nigc_revenue_bands.csv` | minted by 106_build_revenue_bounds.py:308 (POSITIONAL) - unique in this build, not stable across builds |
| `np_schedule_i_grants.csv` | no unique key found. Best candidate (recipient_name_as_filed, recipient_address, cash_grant_usd, object_id) still has 119 duplicate and 0 all-blank rows; the full row has 101 exact duplicates. |
| `prime_contracts_archive_backfill.csv` | no unique key found. Best candidate (contract_number, total_award_value, total_award_value_real2025, total_obligations) still has 34,812 duplicate and 0 all-blank rows; the full row has 18,357 exact duplicates. |
| `resource_revenue.csv` | minted by 83_build_resource_ledger.py:441 (POSITIONAL) - unique in this build, not stable across builds |
| `section_106_consultation_events.csv` | minted by 130_build_section_106_consultation.py:974 (POSITIONAL) - unique in this build, not stable across builds |
| `section_106_project_parties.csv` | minted by 130_build_section_106_consultation.py:830 (POSITIONAL) - unique in this build, not stable across builds |
| `state_gaming_observations.csv` | minted by 107_pull_remaining_states.py:991 (POSITIONAL) - unique in this build, not stable across builds |
| `subawards.csv` | no unique key found. Best candidate (subaward_number, subaward_amount, description, source_url) still has 16,088 duplicate and 0 all-blank rows; the full row has 9,662 exact duplicates. |
| `tcu_cdfi_ownership_evidence.csv` | no unique key found. Best candidate (evidence_url, quote, institution, pattern) still has 4 duplicate and 0 all-blank rows; the full row has 4 exact duplicates. |
| `wa_machine_allocations.csv` | minted by 104_build_wa_allocations.py:629 (POSITIONAL) - unique in this build, not stable across builds |
| `wa_machine_transfers.csv` | no column is >=99% populated; every candidate carries blanks, so nothing can be NOT NULL |
