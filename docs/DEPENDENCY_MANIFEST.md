# Dependency manifest

*Generated 2026-08-28 by `code/287_build_dependency_manifest.py`. Regenerate; do not edit.*

The number prefix has not implied step order since 2026-08-07 and there are 38+
collisions, so **order is declared here, never inferred from a filename**.

## Never run these, ever

Enforced in code by `cedar_pipeline.guard()`, not by comment.

| script | why |
|---|---|
| `01_build_entity_spine.py` | A full rebuild DROPS EVERY APPENDED ENTITY - the village corporations, NHOs, TCUs, CDFIs, BIE schools and UIOs added by scripts 52, 61, 73 and 75. Safe to IMPORT, never to RUN. Append-merge instead, re-reading the spine immediately before writing so a concurrent agent is not clobbered. |
| `09_import_rulings.py` | Rebuilds cedar_identifier_ledger_final.csv FROM the stale cedar_identifier_ledger_tiered.csv, which does not carry rows later scripts appended directly to _final. Running it on 2026-08-08 destroyed 1,327 ledger rows and 451 village-corporation links, 121 of them tier A - lost, not moved. Use 124_apply_rulings_in_place.py. |
| `41_build_codebooks.py` | Writes codebook_master.csv in 'w' mode from a hardcoded 19-group DATASETS dict. Running it today DELETES 21 OF THE 43 dataset blocks, including every block registered on 2026-08-26. The single most destructive command in the repo, and its name does not say so. Use cedar_codebook.write_fragment() or cedar_register_codebook.py. |
| `88_build_deals_taxonomy.py` | Rebuilds the deals taxonomy. Its glob read deals_*_additions.csv and never saw the 131 rows in the two root ledgers - the miscount that propagated as '790 deals' for three weeks. The glob was repaired at source, but a full taxonomy rebuild still discards the party rulings 33/53/57/154 wrote in place. |

## Declared orderings

The enricher runs **last**. Each row is a measured loss.

| file | rebuild | then enricher | what it cost |
|---|---|---|---|
| `ferc_docket_filings.csv` | `133_build_ferc_advocacy.py` | `168_link_adjudication_hubs.py` | 931 entity links and 9 columns discarded on 2026-08-26; the rebuild printed a LARGER row count and read as progress |
| `ferc_tribal_dockets.csv` | `133_build_ferc_advocacy.py` | `175_restore_ferc_docket_table_after_rebuild_revert.py` | a PARTIAL restore left 102,615 filings from 307 dockets described by a docket table listing 183; neither file looked wrong on its own |
| `cedar_identifier_ledger_final.csv` | `09_import_rulings.py` | `50_fix_kootenai_conflation.py` | 09 reverts 50's patches; 09 is in NEVER_RUN for this and worse |
| `cedar_entity_spine.csv` | `01_build_entity_spine.py` | `61_add_nho_intertribal_to_spine.py` | a rebuild drops every entity appended by 52, 61, 73 and 75 |
| `native_entity_lobbying_disclosures.csv` | `05_match_filings_v2.py` | `65_lobbying_organization_type_guard.py` | not yet paid - declared on retirement of the v1 chain, before a rebuild could revert the guard |
| `tribe_year_lobbying_panel.csv` | `05_match_filings_v2.py` | `65_lobbying_organization_type_guard.py` | not yet paid - see the sibling entry above. 351 rebuilt this panel in place on 2026-08-28 (5,051 -> 4,997 rows); a straight 05 rebuild would revert that correction |
| `prime_contracts_entity_year.csv` | `40_build_prime_contracts.py` | `131_merge_archive_backfill.py` | not yet paid - declared before a 40 re-run could revert the FY2008-FY2022 archive backfill out of the panel |
| `prime_contracts.csv` | `40_build_prime_contracts.py` | `207_normalize_extent_competed.py` | extent_competed_normalized and its _basis column are written in place; START_HERE.md records that a rebuild of prime_contracts.csv reverts it and 207 must be re-run |

## Contested files (40)

A full rebuild and an in-place enricher both write these. This is the list
of places the 133/168 collision can happen again.

| file | rebuilders | enrichers |
|---|---|---|
| `admin_appeal_decisions.csv` | `144_build_admin_appeals.py`, `168_link_adjudication_hubs.py` | `168_link_adjudication_hubs.py` |
| `admin_appeal_parties.csv` | `144_build_admin_appeals.py`, `168_link_adjudication_hubs.py` | `168_link_adjudication_hubs.py` |
| `ca_gaming_facilities_official.csv` | `103_build_california_gaming.py`, `266_apply_gaming_hub_spillover_rulings.py` | `266_apply_gaming_hub_spillover_rulings.py` |
| `cedar_identifier_ledger_final.csv` | `124_apply_rulings_in_place.py`, `163_promote_nho_universe_in_place.py`, `174_apply_rulings_to_source_tables.py`, `241_promote_individual_native_firms_in_place.py`, `44_pull_contracts_transactions.py`, `56_apply_agent_identifier_rulings.py`, `63_cross_dataset_reconcile.py`, `71_fix_known_defects.py` | `09_import_rulings.py`, `124_apply_rulings_in_place.py`, `163_promote_nho_universe_in_place.py`, `174_apply_rulings_to_source_tables.py`, `241_promote_individual_native_firms_in_place.py`, `56_apply_agent_identifier_rulings.py`, `63_cross_dataset_reconcile.py`, `71_fix_known_defects.py` |
| `cedar_identifier_ledger_tiered.csv` | `03_apply_exclusions_and_tier.py`, `50_fix_kootenai_conflation.py`, `64_fix_village_government_misattribution.py` | `09_import_rulings.py`, `50_fix_kootenai_conflation.py`, `64_fix_village_government_misattribution.py` |
| `codebook_master.csv` | `104_build_wa_allocations.py`, `107_pull_remaining_states.py`, `108_build_tribal_tax_bases.py`, `111_build_advocacy_passthrough.py`, `112_pull_grantee_990s.py`, `113_build_nd_severance.py`, `132_build_schedule_i_layer.py`, `41_build_codebooks.py`, `96_build_consultation_events.py`, `97_build_aliases_and_relationships.py`, `cedar_codebook.py` | `104_build_wa_allocations.py`, `107_pull_remaining_states.py`, `108_build_tribal_tax_bases.py`, `111_build_advocacy_passthrough.py`, `112_pull_grantee_990s.py`, `113_build_nd_severance.py`, `132_build_schedule_i_layer.py`, `140_build_grantmaker_funding_flows.py`, `96_build_consultation_events.py`, `97_build_aliases_and_relationships.py`, `cedar_codebook.py` |
| `compacts.csv` | `15b_build_compact_index.py` | `15e_finalize_terms.py` |
| `deals_party_autoresolved.csv` | `154_extend_autoresolved_parties_additive.py`, `57_autoresolve_deal_parties.py` | `154_extend_autoresolved_parties_additive.py` |
| `digital_gaming_revenue.csv` | `119_build_digital_and_loyalty.py`, `174_backfill_digital_gaming_tiers.py` | `174_backfill_digital_gaming_tiers.py` |
| `entity_aliases.csv` | `418_build_entity_alias_layer.py`, `97_build_aliases_and_relationships.py` | `418_build_entity_alias_layer.py` |
| `entity_candidates_new.csv` | `35_entity_harvest.py`, `36_cull_entity_candidates.py` | `36_cull_entity_candidates.py` |
| `entity_evidence_profile.csv` | `110_build_harmonized_views.py`, `151_rebuild_entity_evidence_profile.py` | `110_build_harmonized_views.py` |
| `entity_relationships.csv` | `310_correct_overstated_owned_by_edge_tiers.py`, `97_build_aliases_and_relationships.py` | `310_correct_overstated_owned_by_edge_tiers.py` |
| `federal_actions.csv` | `11_classify_federal_actions.py`, `70_key_unjoined_datasets.py` | `70_key_unjoined_datasets.py` |
| `federal_funding_transactions.csv` | `115_pull_assistance_archive.py`, `24_funding_merge.py`, `335_harmonize_assistance_seams_in_place.py`, `336_correct_scheme_resolution_by_spine_membership.py` | `115_pull_assistance_archive.py`, `335_harmonize_assistance_seams_in_place.py`, `336_correct_scheme_resolution_by_spine_membership.py` |
| `ferc_docket_filings.csv` | `133_build_ferc_advocacy.py`, `168_link_adjudication_hubs.py` | `168_link_adjudication_hubs.py` |
| `ferc_ex_parte_parties.csv` | `133_build_ferc_advocacy.py`, `168_link_adjudication_hubs.py` | `168_link_adjudication_hubs.py` |
| `ferc_tribal_dockets.csv` | `133_build_ferc_advocacy.py`, `168_link_adjudication_hubs.py`, `175_restore_ferc_docket_table_after_rebuild_revert.py` | `168_link_adjudication_hubs.py`, `175_restore_ferc_docket_table_after_rebuild_revert.py` |
| `fpds_uei_edges.csv` | `13_build_fpds_hierarchy.py`, `26_fix_sanity_failures.py` | `26_fix_sanity_failures.py` |
| `gaming_capacity_official.csv` | `106_build_revenue_bounds.py`, `92_build_gaming_capacity_official.py` | `106_build_revenue_bounds.py` |
| `gaming_employment_observations.csv` | `100_finish_declinations_and_employment.py`, `158_merge_staged_labor_employment.py`, `262_repair_form5500_tribe_attribution.py`, `265_merge_osha_relift_rows.py` | `158_merge_staged_labor_employment.py`, `262_repair_form5500_tribe_attribution.py`, `265_merge_osha_relift_rows.py` |
| `gaming_facilities.csv` | `143_build_gaming_property_locations.py`, `162_resource_dates_from_cedar_evidence.py`, `172_key_unkeyed_gaming_facility_hubs.py`, `264_add_missing_osha_tribal_facilities.py` | `143_build_gaming_property_locations.py`, `158_extend_gaming_facilities.py`, `162_resource_dates_from_cedar_evidence.py`, `172_key_unkeyed_gaming_facility_hubs.py`, `264_add_missing_osha_tribal_facilities.py` |
| `gaming_financing_events.csv` | `100_finish_declinations_and_employment.py`, `91_build_nigc_declinations.py` | `100_finish_declinations_and_employment.py` |
| `gaming_projections.csv` | `100_finish_declinations_and_employment.py`, `32b_build_gaming_nepa_pilot.py` | `100_finish_declinations_and_employment.py` |
| `gaming_properties.csv` | `160_sync_published_gaming_view.py`, `175_sync_published_property_view_entities.py`, `255_fix_gaming_property_deal_counts.py`, `82_build_gaming_property_dataset.py` | `160_sync_published_gaming_view.py`, `175_sync_published_property_view_entities.py`, `255_fix_gaming_property_deal_counts.py` |
| `gaming_source_claims.csv` | `100_finish_declinations_and_employment.py`, `91_build_nigc_declinations.py` | `100_finish_declinations_and_employment.py` |
| `grantmaker_funding_flows.csv` | `167_link_nonprofit_family_via_ein_hub.py` | `140_build_grantmaker_funding_flows.py`, `167_link_nonprofit_family_via_ein_hub.py` |
| `hearing_appearances.csv` | `400_promote_stranded_hearing_appearances.py`, `98_build_oira_and_hearings.py` | `400_promote_stranded_hearing_appearances.py` |
| `individual_native_ownership_verification.csv` | `171_build_individual_native_verification.py` | `269_build_contractor_ranking.py` |
| `lobbying_issue_families_filing.csv` | `353_propagate_lobbying_corrections_to_consumers.py`, `78_content_analysis.py` | `353_propagate_lobbying_corrections_to_consumers.py` |
| `native_bills.csv` | `14_build_bills_votes.py` | `14_pull_cosponsors.py` |
| `native_issue_litigation_positions.csv` | `139_build_litigation_positions.py` | `139_build_litigation_positions.py`, `140_build_grantmaker_funding_flows.py` |
| `nho_ito_spine_crosswalk.csv` | `163_promote_nho_universe_in_place.py`, `61_add_nho_intertribal_to_spine.py` | `163_promote_nho_universe_in_place.py` |
| `nigc_declination_letters.csv` | `100_finish_declinations_and_employment.py`, `91_build_nigc_declinations.py` | `100_finish_declinations_and_employment.py` |
| `np_financials.csv` | `181_enrich_lobbying_registrant_identifiers.py`, `33_nonprofit_financials.py`, `99_build_earmarks_and_schedc.py` | `33_nonprofit_financials.py`, `99_build_earmarks_and_schedc.py` |
| `np_grantee_financials.csv` | `112_pull_grantee_990s.py`, `181_enrich_lobbying_registrant_identifiers.py` | `112_pull_grantee_990s.py` |
| `np_orgs.csv` | `17_build_nonprofit_990.py`, `20_fix_nonprofit_authority.py`, `251_apply_np_ein_exclusions_to_np_orgs.py`, `34_apply_nonprofit_rulings.py`, `70_key_unjoined_datasets.py`, `99_build_earmarks_and_schedc.py` | `17_build_nonprofit_990.py`, `20_fix_nonprofit_authority.py`, `251_apply_np_ein_exclusions_to_np_orgs.py`, `34_apply_nonprofit_rulings.py`, `70_key_unjoined_datasets.py` |
| `prime_contracts.csv` | `114_pull_prime_archive.py`, `131_merge_archive_backfill.py`, `174_apply_rulings_to_source_tables.py`, `227_anomaly_sweep.py`, `374_build_cedar_taxonomy_export.py`, `40_build_prime_contracts.py` | `114_pull_prime_archive.py`, `131_merge_archive_backfill.py`, `174_apply_rulings_to_source_tables.py`, `206_profile_prime_vocabulary_seams.py`, `207_normalize_extent_competed.py`, `227_anomaly_sweep.py`, `269_build_contractor_ranking.py`, `366_courtlistener_ownership_adjudication.py`, `40_build_prime_contracts.py` |
| `state_gaming_observations.csv` | `107_pull_remaining_states.py`, `117_build_gaming_devices.py` | `117_build_gaming_devices.py` |
| `subawards.csv` | `121_pull_subawards_api.py`, `20_build_subcontracts.py`, `250_demote_stale_tierA_subaward_rows.py`, `45_promote_subawards.py`, `94_match_raw_subawards.py`, `94_rescan_universes.py` | `121_pull_subawards_api.py`, `250_demote_stale_tierA_subaward_rows.py`, `45_promote_subawards.py`, `94_match_raw_subawards.py`, `94_rescan_universes.py` |

## Survival check

`99` clean tables carry an enricher backup. **0** have lost columns against it.


## Pre-flight before any rebuild

```
py -3 code/287_build_dependency_manifest.py --check <table.csv>
```

Exit 0 means no enricher columns are missing. Exit 1 names the enricher to
re-run **after** the rebuild.

