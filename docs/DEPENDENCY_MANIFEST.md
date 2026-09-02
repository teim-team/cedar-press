# Dependency manifest

*Generated 2026-09-01 by `code/287_build_dependency_manifest.py`. Regenerate; do not edit.*

The number prefix has not implied step order since 2026-08-07 and there are 38+
collisions, so **order is declared here, never inferred from a filename**.

## Never run these, ever

Enforced in code by `cedar_pipeline.guard()`, not by comment.

| script | why |
|---|---|
| `41_build_codebooks.py` | Writes codebook_master.csv in 'w' mode from a hardcoded 19-group DATASETS dict. Running it today DELETES 21 OF THE 43 dataset blocks, including every block registered on 2026-08-26. The single most destructive command in the repo, and its name does not say so. Use cedar_codebook.write_fragment() or cedar_register_codebook.py. |

## Declared orderings

The enricher runs **last**. Each row is a measured loss.

| file | rebuild | then enricher | what it cost |
|---|---|---|---|
| `ferc_docket_filings.csv` | `133_build_ferc_advocacy.py` | `168_link_adjudication_hubs.py` | 931 entity links and 9 columns discarded on 2026-08-26; the rebuild printed a LARGER row count and read as progress |
| `ferc_tribal_dockets.csv` | `133_build_ferc_advocacy.py` | `175_restore_ferc_docket_table_after_rebuild_revert.py` | a PARTIAL restore left 102,615 filings from 307 dockets described by a docket table listing 183; neither file looked wrong on its own |
| `cedar_identifier_ledger_final.csv` | `09_import_rulings.py` | `50_fix_kootenai_conflation.py` | 09 reverted 50's patches by rebuilding _final from the stale _tiered. Fixed 2026-09-01 (C8): 09 now re-tiers LIVE _final in place, so it no longer reverts 50 - but 50 still runs after it |
| `cedar_entity_spine.csv` | `01_build_entity_spine.py` | `61_add_nho_intertribal_to_spine.py` | a rebuild drops every entity appended by 52, 61, 73 and 75 |
| `native_entity_lobbying_disclosures.csv` | `05_match_filings_v2.py` | `65_lobbying_organization_type_guard.py` | not yet paid - declared on retirement of the v1 chain, before a rebuild could revert the guard |
| `tribe_year_lobbying_panel.csv` | `05_match_filings_v2.py` | `65_lobbying_organization_type_guard.py` | not yet paid - see the sibling entry above. 351 rebuilt this panel in place on 2026-08-28 (5,051 -> 4,997 rows); a straight 05 rebuild would revert that correction |
| `cedar_entity_spine.csv` | `01_build_entity_spine.py` | `503_identity.py` | not yet paid - a spine rebuild drops cedar_uid, which every dataset now materialises. 01 append-merges since 2026-09-01, so a rerun no longer drops appended entities; even so, re-run 504 then 505 |
| `prime_contracts_archive_backfill.csv` | `114_pull_prime_archive.py` | `430_restore_prime_transaction_key.py` | NONE, and writing that down is the point: 114's `map_row` and `PRIME_FIELDS` now emit `contract_transaction_unique_key` themselves, so a re-pull WRITES the column rather than dropping it. 430 is a ONE-TIME backfill for the 631,507 rows pulled before the mapper was fixed - the 60,919 apparent literal duplicates that were distinct FPDS transactions all along - and is a no-op on a fresh pull |
| `prime_contracts.csv` | `40_build_prime_contracts.py` | `429_apply_asof_ownership_status.py` | not yet paid - declared at creation. A rebuild drops `owner_attribution_status`, and the file then presents Cedar's CURRENT owner on twenty-six years of dated transactions with nothing saying whether the temporal layer confirms it. 81.4% of $244.766B is not confirmed and $2.074B is actively CONTRADICTED, so the missing column is the difference between 'unknown, and it says so' and 'definite, and it is wrong' |
| `prime_contracts.csv` | `40_build_prime_contracts.py` | `430_restore_prime_transaction_key.py` | not yet paid - declared at creation. A rebuild drops `contract_transaction_unique_key` and 80,778 distinct FPDS transactions become byte-identical rows again. The danger is not the duplication, it is that the next reader believes the grain audit and DELETES them - they carry real dollars, and 97% of them are $0 administrative modifications whose loss would silently change every contract-count in the dataset |
| `prime_contracts_entity_year.csv` | `40_build_prime_contracts.py` | `428_rebuild_prime_entity_year.py` | not yet paid - declared at creation. 40 rebuilds the panel from the .dta and 428 re-derives it from prime_contracts.csv AS IT STANDS. Only 428 sees the archive merge (131), the rulings (174/427/64) and the as-of stamp (429). Skipping it left the panel 42 (entity, year) cells stale and $4,729,215.51 of village-corporation dollars booked on the village GOVERNMENT after the row table had already been corrected |
| `federal_funding_transactions.csv` | `24_funding_merge.py` | `503_identity.py` | not yet paid - 505 runs LAST of all enrichers; any rebuild of a stamped table drops cedar_uid and ships a dataset a customer cannot join |
| `assistance_tribe_id_crosswalk.csv` | `152_build_assistance_id_crosswalk.py` | `503_identity.py` | not yet paid - declared at creation, same day as the reconciliation it protects |
| `federal_funding_transactions.csv` | `24_funding_merge.py` | `503_identity.py` | not yet paid - declared at creation. A 24 rebuild reverts the owner-directed Cedar-ID reconciliation of 350,465 rows (96.8% of lineageA dollars); re-run 335 -> 336 -> 503 after |
| `prime_contracts_entity_year.csv` | `40_build_prime_contracts.py` | `131_merge_archive_backfill.py` | not yet paid - declared before a 40 re-run could revert the FY2008-FY2022 archive backfill out of the panel |
| `prime_contracts.csv` | `40_build_prime_contracts.py` | `207_normalize_extent_competed.py` | extent_competed_normalized and its _basis column are written in place; START_HERE.md records that a rebuild of prime_contracts.csv reverts it and 207 must be re-run |
| `nagpra_notice_entity_bridge.csv` | `77_build_nagpra_dataset.py` | `503_identity.py` | PAID 2026-08-29 - a rebuild dropped the cedar_uid 503 stamped on 2026-08-28, and the shipped bridge lost the column a buyer joins the entity layer on. Re-run `503_identity.py stamp --apply` after any 77 build |
| `lobbying_issue_families_filing.csv` | `78_content_analysis.py` | `503_identity.py` | not yet paid - 78 is in the `nagpra` plan but rebuilds a `lobbying` table. Use `78_content_analysis.py --nagpra-only` for a nagpra rebuild; a full 78 run must be followed by 353 then 503 |
| `lobbying_issue_families_filing.csv` | `78_content_analysis.py` | `353_propagate_lobbying_corrections_to_consumers.py` | not yet paid - see the sibling entry above. 353 writes the four entity_id_withdrawn* columns in place; a full 78 run reverts a correction, which is the disease corrections exist to cure |
| `federal_actions.csv` | `11_classify_federal_actions.py` | `22_apply_temporal_floor.py` | not yet paid, but it is inside `build.py run federal-register --execute`: 11 rebuilds this table from the raw pull and writes 31 of its 33 columns. pre_2000_flag and floor_basis_field are 22's, and the shipped view filters on pre_2000_flag. Prefer 342_pull_federal_register_incremental.py, which appends and never runs 11; if 11 is run, re-run 22 immediately after |
| `consultation_events.csv` | `96_build_consultation_events.py` | `503_identity.py` | not yet paid HERE, but paid on the identical shape in nagpra on 2026-08-29. The shipped release already has this table without cedar_uid (28 cols vs 29 live); a rebuild returns it there. Re-run `503_identity.py stamp --apply` after any 96 build |
| `federal_actions_entity_bridge.csv` | `70_key_unjoined_datasets.py` | `503_identity.py` | not yet paid - and 70 is invisible to `build.py plan` because 293's io scan does not recognise its `wr(` write helper, so a planned rebuild of this collection leaves the bridge stale rather than reverting it. Run 70 by hand after 11, then 503 |
| `fr_ex_parte_parties.csv` | `154_build_fr_ex_parte_notices.py` | `503_identity.py` | not yet paid - declared on the pre505 receipt beside the table |
| `fr_ex_parte_party_entity_links.csv` | `154_build_fr_ex_parte_notices.py` | `503_identity.py` | not yet paid - declared on the pre505 receipt beside the table |
| `nepa_administrative_record_parties.csv` | `134_build_nepa_eplanning.py` | `503_identity.py` | not yet paid - declared on the pre505 receipt beside the table |
| `section_106_consultation_events.csv` | `130_build_section_106_consultation.py` | `503_identity.py` | not yet paid - declared on the pre505 receipt beside the table. 130 is also AMBIGUOUS to build.py (it rebuilds section_106_source_coverage.csv and enriches this file), so it is not in the plan at all and must be run by hand - see docs/datasets/federal-register.md |
| `section_106_project_parties.csv` | `130_build_section_106_consultation.py` | `503_identity.py` | not yet paid - declared on the pre505 receipt beside the table |
| `cedar_identifier_graph_edges.csv` | `169_build_identifier_graph.py` | `741_hub_grain_and_rebuild.py` | NONE. 169 now writes `asserting_row_ref` on BLOCK edges itself, so a rebuild WRITES the column rather than dropping it. 741 is a one-time splice of the ruling-map BLOCK slice for the rows built before that change - the 2,451 apparent literal duplicates that were distinct applications of a negative ruling to distinct target rows all along - and is a no-op on a fresh 169 build. 169 was deliberately NOT re-run: it also rebuilds cedar_identifier_graph_nodes.csv and cedar_identifier_propagation.csv, and 354 and 427 have written to the graph since it last ran |

## Contested files (52)

A full rebuild and an in-place enricher both write these. This is the list
of places the 133/168 collision can happen again.

| file | rebuilders | enrichers |
|---|---|---|
| `admin_appeal_decisions.csv` | `144_build_admin_appeals.py`, `168_link_adjudication_hubs.py` | `168_link_adjudication_hubs.py` |
| `ancsa_filings_index.csv` | `814_gaming_nr_grain_and_conservation.py` | `814_gaming_nr_grain_and_conservation.py`, `84_resource_recipient_side.py` |
| `assistance_tribe_id_crosswalk.csv` | `152_build_assistance_id_crosswalk.py`, `503_identity.py` | `503_identity.py` |
| `cedar_dataset_readiness.csv` | `518_dataset_readiness.py`, `621_dataset_coverage.py` | `621_dataset_coverage.py` |
| `cedar_identifier_graph_edges.csv` | `169_build_identifier_graph.py`, `741_hub_grain_and_rebuild.py` | `741_hub_grain_and_rebuild.py` |
| `cedar_identifier_ledger_final.csv` | `09_import_rulings.py`, `124_apply_rulings_in_place.py`, `163_promote_nho_universe_in_place.py`, `174_apply_rulings_to_source_tables.py`, `241_promote_individual_native_firms_in_place.py`, `44_pull_contracts_transactions.py`, `56_apply_agent_identifier_rulings.py`, `63_cross_dataset_reconcile.py`, `71_fix_known_defects.py` | `09_import_rulings.py`, `124_apply_rulings_in_place.py`, `163_promote_nho_universe_in_place.py`, `174_apply_rulings_to_source_tables.py`, `241_promote_individual_native_firms_in_place.py`, `56_apply_agent_identifier_rulings.py`, `63_cross_dataset_reconcile.py`, `71_fix_known_defects.py` |
| `cedar_identifier_ledger_tiered.csv` | `03_apply_exclusions_and_tier.py`, `50_fix_kootenai_conflation.py`, `64_fix_village_government_misattribution.py` | `50_fix_kootenai_conflation.py`, `64_fix_village_government_misattribution.py` |
| `codebook_master.csv` | `104_build_wa_allocations.py`, `107_pull_remaining_states.py`, `108_build_tribal_tax_bases.py`, `111_build_advocacy_passthrough.py`, `112_pull_grantee_990s.py`, `113_build_nd_severance.py`, `132_build_schedule_i_layer.py`, `41_build_codebooks.py`, `96_build_consultation_events.py`, `97_build_aliases_and_relationships.py`, `cedar_codebook.py` | `104_build_wa_allocations.py`, `107_pull_remaining_states.py`, `108_build_tribal_tax_bases.py`, `111_build_advocacy_passthrough.py`, `112_pull_grantee_990s.py`, `113_build_nd_severance.py`, `132_build_schedule_i_layer.py`, `140_build_grantmaker_funding_flows.py`, `96_build_consultation_events.py`, `97_build_aliases_and_relationships.py`, `cedar_codebook.py` |
| `compacts.csv` | `15b_build_compact_index.py` | `15e_finalize_terms.py` |
| `contractor_ranking.csv` | `572_ws2_contracts.py` | `269_build_contractor_ranking.py`, `572_ws2_contracts.py` |
| `deals_party_autoresolved.csv` | `154_extend_autoresolved_parties_additive.py`, `57_autoresolve_deal_parties.py` | `154_extend_autoresolved_parties_additive.py` |
| `digital_gaming_revenue.csv` | `119_build_digital_and_loyalty.py`, `174_backfill_digital_gaming_tiers.py` | `174_backfill_digital_gaming_tiers.py` |
| `entity_aliases.csv` | `418_build_entity_alias_layer.py`, `97_build_aliases_and_relationships.py` | `418_build_entity_alias_layer.py` |
| `entity_candidates_new.csv` | `35_entity_harvest.py`, `36_cull_entity_candidates.py` | `36_cull_entity_candidates.py` |
| `entity_evidence_profile.csv` | `110_build_harmonized_views.py`, `151_rebuild_entity_evidence_profile.py` | `110_build_harmonized_views.py` |
| `entity_relationships.csv` | `310_correct_overstated_owned_by_edge_tiers.py`, `97_build_aliases_and_relationships.py` | `310_correct_overstated_owned_by_edge_tiers.py` |
| `faads_entity_attribution.csv` | `710_faads_attribution_content_key.py`, `73_faads_name_attribution.py`, `791_faads_transaction_key_and_repoint.py` | `710_faads_attribution_content_key.py`, `791_faads_transaction_key_and_repoint.py` |
| `faads_transactions.csv` | `574_ws1_money_and_conservation.py`, `791_faads_transaction_key_and_repoint.py` | `791_faads_transaction_key_and_repoint.py` |
| `fac_audit_sefa_gaming_programs.csv` | `147_build_fac_single_audits.py`, `814_gaming_nr_grain_and_conservation.py` | `814_gaming_nr_grain_and_conservation.py` |
| `federal_actions.csv` | `11_classify_federal_actions.py`, `70_key_unjoined_datasets.py` | `70_key_unjoined_datasets.py` |
| `federal_funding_transactions.csv` | `115_pull_assistance_archive.py`, `24_funding_merge.py`, `335_harmonize_assistance_seams_in_place.py`, `336_correct_scheme_resolution_by_spine_membership.py`, `503_identity.py` | `115_pull_assistance_archive.py`, `335_harmonize_assistance_seams_in_place.py`, `336_correct_scheme_resolution_by_spine_membership.py`, `503_identity.py` |
| `ferc_docket_filings.csv` | `133_build_ferc_advocacy.py`, `168_link_adjudication_hubs.py`, `781_upstream_grain_columns.py` | `168_link_adjudication_hubs.py`, `781_upstream_grain_columns.py` |
| `ferc_ex_parte_communications.csv` | `133_build_ferc_advocacy.py`, `573_ws3_grain_and_money.py` | `573_ws3_grain_and_money.py` |
| `ferc_ex_parte_parties.csv` | `133_build_ferc_advocacy.py`, `168_link_adjudication_hubs.py` | `168_link_adjudication_hubs.py` |
| `ferc_tribal_dockets.csv` | `133_build_ferc_advocacy.py`, `168_link_adjudication_hubs.py`, `175_restore_ferc_docket_table_after_rebuild_revert.py` | `168_link_adjudication_hubs.py`, `175_restore_ferc_docket_table_after_rebuild_revert.py` |
| `fpds_uei_cage_map.csv` | `13_build_fpds_hierarchy.py`, `572_ws2_contracts.py` | `572_ws2_contracts.py` |
| `fpds_uei_edges.csv` | `13_build_fpds_hierarchy.py`, `26_fix_sanity_failures.py` | `26_fix_sanity_failures.py` |
| `gaming_capacity_official.csv` | `106_build_revenue_bounds.py`, `92_build_gaming_capacity_official.py` | `106_build_revenue_bounds.py` |
| `gaming_employment_observations.csv` | `100_finish_declinations_and_employment.py`, `158_merge_staged_labor_employment.py`, `262_repair_form5500_tribe_attribution.py`, `265_merge_osha_relift_rows.py`, `583_labor_surface_factcheck.py`, `589_adjudicate_osha_711.py` | `158_merge_staged_labor_employment.py`, `262_repair_form5500_tribe_attribution.py`, `265_merge_osha_relift_rows.py`, `583_labor_surface_factcheck.py`, `589_adjudicate_osha_711.py` |
| `gaming_facilities.csv` | `143_build_gaming_property_locations.py`, `162_resource_dates_from_cedar_evidence.py`, `172_key_unkeyed_gaming_facility_hubs.py`, `264_add_missing_osha_tribal_facilities.py`, `587_gaming_facility_corrections.py` | `143_build_gaming_property_locations.py`, `158_extend_gaming_facilities.py`, `162_resource_dates_from_cedar_evidence.py`, `172_key_unkeyed_gaming_facility_hubs.py`, `264_add_missing_osha_tribal_facilities.py`, `587_gaming_facility_corrections.py` |
| `gaming_financing_events.csv` | `100_finish_declinations_and_employment.py`, `91_build_nigc_declinations.py` | `100_finish_declinations_and_employment.py` |
| `gaming_projections.csv` | `100_finish_declinations_and_employment.py`, `32b_build_gaming_nepa_pilot.py` | `100_finish_declinations_and_employment.py` |
| `gaming_properties.csv` | `160_sync_published_gaming_view.py`, `175_sync_published_property_view_entities.py`, `255_fix_gaming_property_deal_counts.py`, `82_build_gaming_property_dataset.py` | `160_sync_published_gaming_view.py`, `175_sync_published_property_view_entities.py`, `255_fix_gaming_property_deal_counts.py` |
| `gaming_source_claims.csv` | `100_finish_declinations_and_employment.py`, `510_assertions.py`, `91_build_nigc_declinations.py` | `100_finish_declinations_and_employment.py`, `510_assertions.py` |
| `grantmaker_funding_flows.csv` | `167_link_nonprofit_family_via_ein_hub.py` | `140_build_grantmaker_funding_flows.py`, `167_link_nonprofit_family_via_ein_hub.py` |
| `hearing_appearances.csv` | `400_promote_stranded_hearing_appearances.py`, `98_build_oira_and_hearings.py` | `400_promote_stranded_hearing_appearances.py` |
| `hearing_bill_links.csv` | `781_upstream_grain_columns.py`, `98_build_oira_and_hearings.py` | `781_upstream_grain_columns.py` |
| `individual_native_ownership_verification.csv` | `171_build_individual_native_verification.py` | `269_build_contractor_ranking.py` |
| `lobbying_issue_families_filing.csv` | `353_propagate_lobbying_corrections_to_consumers.py`, `78_content_analysis.py` | `353_propagate_lobbying_corrections_to_consumers.py` |
| `native_bills.csv` | `14_build_bills_votes.py` | `14_pull_cosponsors.py` |
| `native_issue_litigation_positions.csv` | `139_build_litigation_positions.py` | `139_build_litigation_positions.py`, `140_build_grantmaker_funding_flows.py` |
| `native_owned_businesses.csv` | `330_build_native_owned_businesses.py` | `330_build_native_owned_businesses.py`, `615_set_publishable_native_owned_businesses.py` |
| `nho_ito_spine_crosswalk.csv` | `163_promote_nho_universe_in_place.py`, `61_add_nho_intertribal_to_spine.py` | `163_promote_nho_universe_in_place.py` |
| `nigc_declination_letters.csv` | `100_finish_declinations_and_employment.py`, `91_build_nigc_declinations.py` | `100_finish_declinations_and_employment.py` |
| `np_financials.csv` | `181_enrich_lobbying_registrant_identifiers.py`, `33_nonprofit_financials.py`, `99_build_earmarks_and_schedc.py` | `33_nonprofit_financials.py`, `99_build_earmarks_and_schedc.py` |
| `np_grantee_financials.csv` | `112_pull_grantee_990s.py`, `181_enrich_lobbying_registrant_identifiers.py` | `112_pull_grantee_990s.py` |
| `np_orgs.csv` | `17_build_nonprofit_990.py`, `20_fix_nonprofit_authority.py`, `251_apply_np_ein_exclusions_to_np_orgs.py`, `34_apply_nonprofit_rulings.py`, `70_key_unjoined_datasets.py`, `99_build_earmarks_and_schedc.py` | `17_build_nonprofit_990.py`, `20_fix_nonprofit_authority.py`, `251_apply_np_ein_exclusions_to_np_orgs.py`, `34_apply_nonprofit_rulings.py`, `70_key_unjoined_datasets.py` |
| `np_schedule_i_grants.csv` | `132_build_schedule_i_layer.py`, `781_upstream_grain_columns.py` | `781_upstream_grain_columns.py` |
| `prime_contracts.csv` | `114_pull_prime_archive.py`, `131_merge_archive_backfill.py`, `174_apply_rulings_to_source_tables.py`, `227_anomaly_sweep.py`, `374_build_cedar_taxonomy_export.py`, `40_build_prime_contracts.py`, `429_apply_asof_ownership_status.py`, `430_restore_prime_transaction_key.py` | `114_pull_prime_archive.py`, `131_merge_archive_backfill.py`, `174_apply_rulings_to_source_tables.py`, `206_profile_prime_vocabulary_seams.py`, `207_normalize_extent_competed.py`, `227_anomaly_sweep.py`, `269_build_contractor_ranking.py`, `366_courtlistener_ownership_adjudication.py`, `40_build_prime_contracts.py`, `429_apply_asof_ownership_status.py`, `430_restore_prime_transaction_key.py` |
| `prime_contracts_entity_year.csv` | `114_pull_prime_archive.py`, `131_merge_archive_backfill.py`, `40_build_prime_contracts.py`, `428_rebuild_prime_entity_year.py`, `cedar_prime_panel.py` | `428_rebuild_prime_entity_year.py` |
| `state_gaming_observations.csv` | `107_pull_remaining_states.py`, `117_build_gaming_devices.py` | `117_build_gaming_devices.py` |
| `subawards.csv` | `121_pull_subawards_api.py`, `20_build_subcontracts.py`, `250_demote_stale_tierA_subaward_rows.py`, `45_promote_subawards.py`, `94_match_raw_subawards.py`, `94_rescan_universes.py` | `121_pull_subawards_api.py`, `250_demote_stale_tierA_subaward_rows.py`, `45_promote_subawards.py`, `94_match_raw_subawards.py`, `94_rescan_universes.py` |

## Survival check

`191` clean tables carry an enricher backup. **1** have lost columns against it.

| table | columns lost | compared against |
|---|---|---|
| `entity_evidence_profile.csv` | in_spine, rows_per_source, amounts_per_source_NEVER_SUM | `entity_evidence_profile.csv.bak_2026-08-28_pre505` |

## Pre-flight before any rebuild

```
py -3 code/287_build_dependency_manifest.py --check <table.csv>
```

Exit 0 means no enricher columns are missing. Exit 1 names the enricher to
re-run **after** the rebuild.

