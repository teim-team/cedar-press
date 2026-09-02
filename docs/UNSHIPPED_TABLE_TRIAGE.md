# Triage of the zero-ship tables

*Written 2026-09-02 by `code/391_triage_unshipped_tables.py`. Re-runnable; it reads `data/clean` live rather than a snapshot.*

`docs/SHIP_GAP_REPORT.json` counts these as a backlog and prints one fix against all of them. This file says which of them SHOULD take that fix, which are internal by decision, and which turn on a question that is not a build's to answer.

| verdict | tables | rows |
|---|---:|---:|
| SHIP | 84 | 518,483 |
| INTERNAL | 56 | 108,769 |
| NEEDS_A_RULING | 3 | 2,456 |
| NEVER_SHIP | 2 | 132,392 |
| EMPTY | 4 | 0 |

## NEVER_SHIP — 2 table(s), 132,392 rows

| table | rows | block | why |
|---|---:|---|---|
| `gaming_facility_metrics.csv` | 68,211 | — | Casino City Press derived; cedar_codebook.LICENSED_SOURCE_FILES |
| `gaming_property_capacity_history.csv` | 64,181 | — | 100% Casino City Press panel; cedar_codebook.LICENSED_SOURCE_FILES |

## NEEDS_A_RULING — 3 table(s), 2,456 rows

| table | rows | block | why |
|---|---:|---|---|
| `gaming_property_locations.csv` | 2,212 | — | docs/SHIPPING_RUNBOOK.md Part 4 states it 'also needs a row filter - 741 rows are publishable = N'. NO SCRIPT APPLIES THAT FILTER TODAY. Registering a block would put all 2,212 rows in a notes contract and decide the question by default. QUESTION: who applies the publishable = Y filter - 143 at build time, or the bundler? |
| `cedar_correction_register.csv` | 178 | — | written IN PLACE right now by the lobbying-correction pass (scripts 350-358), which AGENTS.md names as the live owner of the failing registry metrics in 62. QUESTION: does the correction register publish as a transparency artefact, and does its owner want it registered? Not mine to answer while they are mid-pass |
| `consultation_agency_coverage.csv` | 66 | — | a hybrid. Half its columns are findings about AGENCIES - whether each publishes named participants, event locations, dates, and what its own consultation policy obliges - and half are counts of what WE collected. QUESTION: split it, or ship it with the coverage columns tiered internal? |

## SHIP — 84 table(s), 518,483 rows

| table | rows | block | why |
|---|---:|---|---|
| `fr_content_classification.csv` | 156,897 | `09b_fr_content_classification` | docs/CONTENT_ANALYSIS.md 'Outputs' lists this under Series, which that document separates by name from its 'Audit and accuracy' files |
| `ferc_docket_filings.csv` | 102,615 | `04s_ferc_docket_filings` | 102,615 filings across 307 of 307 dockets; the sibling link tables (04g/04h/04i) already have blocks and ship, this one never did |
| `fpds_uei_cage_map.csv` | 34,601 | `02n_fpds_uei_cage_map` | already curated into 25_build_publication_layer.TABLES and shipping into cedar_press.db; the only thing missing is a notes contract |
| `lobbying_issue_families_filing.csv` | 27,796 | `04m_lobbying_issue_families_filing` | docs/CONTENT_ANALYSIS.md 'Outputs' lists this under Series, which that document separates by name from its 'Audit and accuracy' files. NOTE: scripts 350-358 write this table in place; registering a codebook block does not touch the data |
| `cross_dataset_ruling_map.csv` | 22,936 | `05f_cross_dataset_ruling_map` | already curated into 25_build_publication_layer.TABLES and shipping into cedar_press.db; the only thing missing is a notes contract |
| `cedar_identifier_ledger_final.csv` | 20,577 | `05e_identifier_ledger` | already curated into 25_build_publication_layer.TABLES and shipping into cedar_press.db; the only thing missing is a notes contract |
| `admin_appeal_parties.csv` | 20,027 | `04x_admin_appeal_parties` | party grain of the same decisions; natural-person names are already governed on the row by is_natural_person and party_name_withheld_reason |
| `ancsa_filings_index.csv` | 19,269 | `12c_ancsa_filings_index` | the index of ANCSA corporation filings on the state portal |
| `federal_recognition_roster.csv` | 17,058 | `05h_federal_recognition_roster` | every entry of every published Federal Register recognition list, 1979-2026 |
| `admin_appeal_decisions.csv` | 15,613 | `04w_admin_appeal_decisions` | IBIA and IBLA decisions as published by the boards |
| `entity_year_panel.csv` | 12,534 | `05o_entity_year_panel` | the entity-by-year panel across every money component; a product surface, not an intermediate |
| `np_schedule_i_filers.csv` | 10,314 | `04f_schedule_i_filers` | 990 Schedule I filer grain; the grant grain (04e) already ships |
| `gaming_game_finder_observations.csv` | 6,851 | `07q_gaming_game_finder_observations` | named in docs/SHIPPING_RUNBOOK.md Part 4 as a table awaiting a codebook block |
| `fac_tribal_single_audits.csv` | 6,780 | `07ze_fac_tribal_single_audits` | tribal Single Audits from api.fac.gov |
| `fr_nagpra_title_index.csv` | 6,664 | `11b_fr_nagpra_title_index` | docs/CONTENT_ANALYSIS.md 'Outputs' lists this under Series, which that document separates by name from its 'Audit and accuracy' files |
| `federal_actions_entity_bridge.csv` | 5,786 | `09h_federal_actions_entity_bridge` | entity linkage for federal actions. 62_no_regression_check tracks its row count as MUST_NOT_FALL, and the sibling *_entity_links blocks already ship |
| `fpds_uei_edges.csv` | 5,167 | `02o_fpds_uei_edges` | already curated into 25_build_publication_layer.TABLES and shipping into cedar_press.db; the only thing missing is a notes contract |
| `ferc_ex_parte_parties.csv` | 4,246 | `04t_ferc_ex_parte_parties` | FERC ex parte communications, party grain |
| `fr_consultation_referenced.csv` | 1,829 | `09i_fr_consultation_referenced` | already ships, but under 11_nagpra at 0.80 - a consultation table documented by the NAGPRA block. Given its own block so it is neither mis-documented nor outranked by 11b |
| `cedar_publishable_identifiers.csv` | 1,577 | `05d_publishable_identifiers` | already curated into 25_build_publication_layer.TABLES and shipping into cedar_press.db; the only thing missing is a notes contract; also in 27_SPEC |
| `native_passthrough.csv` | 1,522 | `02q_native_passthrough` | Native prime to Native sub passthrough, award grain |
| `fac_audit_gaming_disclosures.csv` | 1,521 | `07zf_fac_audit_gaming_disclosures` | named in docs/SHIPPING_RUNBOOK.md Part 4 as a table awaiting a codebook block |
| `earmarks.csv` | 1,002 | `04zf_earmarks` | congressionally directed spending requests and enactments |
| `intertribal_memberships.csv` | 989 | `05j_intertribal_memberships` | membership of intertribal organisations as those organisations publish it |
| `compact_obligation_tribal_agency_bridge.csv` | 927 | `08b_compact_obligation_tribal_agency_bridge` | compact revenue-sharing obligations bridged to the named tribal gaming agency that receives them |
| `nepa_project_documents.csv` | 789 | `04zb_nepa_project_documents` | BLM ePlanning NEPA project documents |
| `gaming_properties.csv` | 784 | `07r_gaming_properties` | named in docs/SHIPPING_RUNBOOK.md Part 4 as a table awaiting a codebook block |
| `gaming_property_federal_traces.csv` | 774 | `07s_gaming_property_federal_traces` | named in docs/SHIPPING_RUNBOOK.md Part 4 as a table awaiting a codebook block |
| `gaming_vendor_tribal_licenses.csv` | 740 | `07t_gaming_vendor_tribal_licenses` | named in docs/SHIPPING_RUNBOOK.md Part 4 as a table awaiting a codebook block |
| `ferc_ex_parte_communications.csv` | 713 | `04u_ferc_ex_parte_communications` | FERC ex parte communications, notice grain |
| `agency_attention_vs_advocacy_year.csv` | 698 | `04r_agency_attention_vs_advocacy_year` | docs/CONTENT_ANALYSIS.md 'Outputs' lists this under Series, which that document separates by name from its 'Audit and accuracy' files |
| `native_bills_entity_bridge.csv` | 676 | `10b_native_bills_entity_bridge` | entity linkage for Native bills; same standing as the federal actions bridge |
| `fr_theme_year.csv` | 627 | `09c_fr_theme_year` | docs/CONTENT_ANALYSIS.md 'Outputs' lists this under Series, which that document separates by name from its 'Audit and accuracy' files |
| `deals_source_index.csv` | 533 | `01b_deals_source_index` | the source URLs behind each deal party - the provenance the notes contract promises on every row |
| `fr_consultation_notices.csv` | 485 | `09j_fr_consultation_notices` | already ships, but under 09_federal_actions at 0.636. Given its own block so it is neither mis-documented nor outranked by 09b |
| `lobbying_issue_family_year.csv` | 476 | `04n_lobbying_issue_family_year` | docs/CONTENT_ANALYSIS.md 'Outputs' lists this under Series, which that document separates by name from its 'Audit and accuracy' files |
| `gaming_nigc_roster_link.csv` | 453 | `07u_gaming_nigc_roster_link` | named in docs/SHIPPING_RUNBOOK.md Part 4 as a table awaiting a codebook block |
| `subaward_entity_rollup.csv` | 450 | `02p_subaward_entity_rollup` | subaward dollars per entity, split by which side of the award the entity sat on |
| `nrc_meeting_participants.csv` | 407 | `04za_nrc_meeting_participants` | participant grain of the NRC meetings |
| `federal_recognition_events.csv` | 366 | `05i_federal_recognition_events` | recognition, restoration, termination and rename events with the Federal Register citation that effected each |
| `nepa_eplanning_projects.csv` | 312 | `04zc_nepa_eplanning_projects` | BLM ePlanning NEPA projects |
| `ferc_tribal_dockets.csv` | 307 | `04v_ferc_tribal_dockets` | one row per docket swept, with retrieved-vs-reported totals on it |
| `native_passthrough_pairs.csv` | 307 | `02r_native_passthrough_pairs` | the same passthrough, entity-pair grain |
| `bill_votes_official_verification.csv` | 305 | `10c_bill_votes_official_verification` | our vote tallies checked against the Clerk's and the Senate's own published counts, row by row |
| `gaming_financing_events.csv` | 293 | `07v_gaming_financing_events` | named in docs/SHIPPING_RUNBOOK.md Part 4 as a table awaiting a codebook block |
| `gaming_property_site_observations.csv` | 262 | `07w_gaming_property_site_observations` | named in docs/SHIPPING_RUNBOOK.md Part 4 as a table awaiting a codebook block (the existing 07j fragment is a 6-of-26 stub and can never reach 0.60) |
| `nrc_public_meetings.csv` | 251 | `04z_nrc_public_meetings` | NRC public meeting notices |
| `native_issue_litigation_positions.csv` | 197 | `04ze_native_issue_litigation_positions` | positions taken in litigation on Native issues |
| `anc_ceiling_roster.csv` | 196 | `12b_anc_ceiling_roster` | already curated into 25_build_publication_layer.TABLES and shipping into cedar_press.db; the only thing missing is a notes contract |
| `nho_doi_notification_roster.csv` | 190 | `05k_nho_doi_notification_roster` | the DOI Native Hawaiian Organization notification list |
| `gaming_decision_compact_join.csv` | 138 | `07z_gaming_decision_compact_join` | land decisions joined to the compacts they sit under |
| `fr_relevance_tier_year.csv` | 132 | `09d_fr_relevance_tier_year` | docs/CONTENT_ANALYSIS.md 'Outputs' lists this under Series, which that document separates by name from its 'Audit and accuracy' files |
| `tcu_cdfi_ownership_evidence.csv` | 130 | `05n_tcu_cdfi_ownership_evidence` | quoted ownership language for each TCU and Native CDFI, with the URL it was quoted from |
| `gaming_projections.csv` | 116 | `07za_gaming_projections` | capacity and impact figures as projected in environmental and planning documents |
| `lobbying_target_entities.csv` | 116 | `04p_lobbying_target_entities` | docs/CONTENT_ANALYSIS.md 'Outputs' lists this under Series, which that document separates by name from its 'Audit and accuracy' files |
| `bie_uio_dollars_by_entity.csv` | 114 | `03b_bie_uio_dollars_by_entity` | federal dollars to BIE schools and Urban Indian Organizations |
| `gaming_source_claims.csv` | 113 | `07x_gaming_source_claims` | named in docs/SHIPPING_RUNBOOK.md Part 4 as a table awaiting a codebook block |
| `ownership_events.csv` | 98 | `12d_ownership_events` | ownership-change events with the deal they were read from |
| `native_fi_roster.csv` | 94 | `05m_native_fi_roster` | Native financial institutions - CDFI Fund, NCUA, FDIC rosters |
| `bill_votes_entity_bridge.csv` | 75 | `10d_bill_votes_entity_bridge` | already ships, but under 06_nonprofit at 0.60 - a bill-vote bridge documented by the nonprofit block. Given its own block so it is neither mis-documented nor outranked by 10b |
| `wa_machine_allocations.csv` | 75 | `14b_wa_machine_allocations` | Washington machine allocations as set out in compacts and appendices |
| `grantmaker_funding_overlap.csv` | 69 | `17b_grantmaker_funding_overlap` | which grantmakers funded both sides of a contested issue - a finding, not a coverage measurement |
| `loyalty_program_property.csv` | 48 | `16e_loyalty_program_property` | already ships, but under 16_digital_gaming at 0.737, because its own block 16d_loyalty_program_property is a 13-of-19 STUB scoring 0.684 and a stub can never win. `07q_gaming_game_finder_observations` TIES it at 0.737 and takes it on alphabetical order, which is no way to decide what documents a table. 16d's rows live inside the 16_digital_gaming.csv FRAGMENT, which belongs to another writer and must not be edited, so a complete block is added beside it at 16e: 19 of 19 columns, score 1.0, beats both on merit rather than on sort order. 16d is now superseded and is a candidate for cedar_register_codebook.RETIRE_FROM_MASTER |
| `gaming_property_labor_demand.csv` | 43 | `07y_gaming_property_labor_demand` | named in docs/SHIPPING_RUNBOOK.md Part 4 as a table awaiting a codebook block (the existing 07k fragment is a stub) |
| `tcu_roster.csv` | 37 | `05l_tcu_roster` | tribal colleges and universities roster |
| `nepa_administrative_record_parties.csv` | 36 | `04zd_nepa_administrative_record_parties` | parties named in NEPA administrative records |
| `nho_verified_entities.csv` | 36 | `05g_nho_verified_entities` | already curated into 25_build_publication_layer.TABLES and shipping into cedar_press.db; the only thing missing is a notes contract |
| `fr_abstract_availability_year.csv` | 33 | `09e_fr_abstract_availability_year` | docs/CONTENT_ANALYSIS.md 'Outputs' lists this under Series, which that document separates by name from its 'Audit and accuracy' files |
| `fr_consultation_year.csv` | 33 | `09f_fr_consultation_year` | docs/CONTENT_ANALYSIS.md 'Outputs' lists this under Series, which that document separates by name from its 'Audit and accuracy' files |
| `fr_nagpra_title_index_year.csv` | 33 | `11c_fr_nagpra_title_index_year` | docs/CONTENT_ANALYSIS.md 'Outputs' lists this under Series, which that document separates by name from its 'Audit and accuracy' files |
| `tribal_bond_issuances.csv` | 29 | `12f_tribal_bond_issuances` | tribal bond issuances as disclosed on EMMA |
| `inflation_deflator.csv` | 27 | `19_inflation_deflator` | the GDP deflator series every nominal-to-constant restatement in this project runs through; a published BEA series |
| `lobbying_disclosure_verbosity_year.csv` | 27 | `04o_lobbying_disclosure_verbosity_year` | docs/CONTENT_ANALYSIS.md 'Outputs' lists this under Series, which that document separates by name from its 'Audit and accuracy' files |
| `gaming_mitigation_agreements.csv` | 24 | `07zc_gaming_mitigation_agreements` | mitigation agreements between tribes and local governments |
| `agency_attention_vs_advocacy.csv` | 22 | `04q_agency_attention_vs_advocacy` | docs/CONTENT_ANALYSIS.md 'Outputs' lists this under Series, which that document separates by name from its 'Audit and accuracy' files |
| `fr_consultation_by_agency.csv` | 21 | `09g_fr_consultation_by_agency` | docs/CONTENT_ANALYSIS.md 'Outputs' lists this under Series, which that document separates by name from its 'Audit and accuracy' files |
| `visitor_access_events.csv` | 20 | `13b_visitor_access_events` | published visitor-access records; withholding is already declared per row in visitor_name_withheld_reason |
| `gaming_project_facilities.csv` | 19 | `07zb_gaming_project_facilities` | facility programme as described in project documents |
| `gaming_property_universe_events.csv` | 10 | `07zd_gaming_property_universe_events` | additions and removals observed in the NIGC location map over time |
| `nho_ownership_changes.csv` | 9 | `12e_nho_ownership_changes` | ownership changes affecting Native Hawaiian Organizations |
| `admin_appeal_positions.csv` | 8 | `04y_admin_appeal_positions` | positions taken before the boards |
| `nd_severance_allocation.csv` | 7 | `15b_nd_severance_allocation` | the statutory North Dakota oil and gas severance split, by vintage |
| `fac_audit_sefa_gaming_programs.csv` | 1 | `07zg_fac_audit_sefa_gaming_programs` | SEFA programme rows on gaming-related awards |
| `tribal_resolution_financings.csv` | 1 | `07zh_tribal_resolution_financings` | financings authorised by published tribal council resolutions |

## INTERNAL — 56 table(s), 108,769 rows

| table | rows | block | why |
|---|---:|---|---|
| `funding_identifier_harvest.csv` | 37,704 | — | identifier/name harvest working set, assembled to feed the spine and the ledger; the grain is our resolution process, not an event in the world. It also carries recipient_duns and recipient address, which are the D&B fields that may not be disseminated in bulk |
| `entity_name_harvest.csv` | 31,728 | — | identifier/name harvest working set, assembled to feed the spine and the ledger; the grain is our resolution process, not an event in the world |
| `cedar_identifier_ledger_tiered.csv` | 19,232 | — | the pre-consolidation vintage of the ledger. Its header is IDENTICAL to cedar_identifier_ledger_final.csv, which is the one 25 publishes; shipping both would put two vintages of the same ledger on the shelf and let a reader pick the stale one |
| `cedar_cage_backfill.csv` | 4,362 | — | identifier/name harvest working set, assembled to feed the spine and the ledger; the grain is our resolution process, not an event in the world |
| `entity_candidates_new.csv` | 2,874 | — | a review by-product: it records what a human ruled, or has yet to rule, on a proposal. The ruling corpus is named proprietary and unpublished in 87_build_dataset_notes.TERMS. It carries a YOUR_RULING column and seven DUPLICATED column names, which is a review sheet's shape, not a dataset's |
| `faads_attribution_audit_sample.csv` | 2,287 | — | a hand-coding sheet - AUDIT_VERDICT and AUDIT_NOTE are columns for a person to fill in |
| `entity_evidence_profile.csv` | 1,313 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country; its own column amounts_per_source_NEVER_SUM says what it is for |
| `entity_candidates_rejected.csv` | 1,045 | — | a review by-product: it records what a human ruled, or has yet to rule, on a proposal. The ruling corpus is named proprietary and unpublished in 87_build_dataset_notes.TERMS; the rejected half of the same sheet, same duplicate columns |
| `coverage_audit.csv` | 912 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country. START_HERE.md also records this file as STALE and explicitly not to be quoted |
| `gaming_property_coverage.csv` | 787 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country |
| `brand_family_proposals.csv` | 609 | — | a review by-product: it records what a human ruled, or has yet to rule, on a proposal. The ruling corpus is named proprietary and unpublished in 87_build_dataset_notes.TERMS |
| `fr_recognized_entities.csv` | 575 | — | the raw parse intermediate behind federal_recognition_roster.csv, which ships. Its `parsed` column is a parser status |
| `deals_party_attribution_agent.csv` | 530 | — | a review by-product: it records what a human ruled, or has yet to rule, on a proposal. The ruling corpus is named proprietary and unpublished in 87_build_dataset_notes.TERMS |
| `lobbying_unmatched_clients.csv` | 515 | — | a work queue: why_unmatched and pull_keywords are next actions for us, and pull_keywords discloses the search recipe |
| `deals_party_autoresolved.csv` | 502 | — | a review by-product: it records what a human ruled, or has yet to rule, on a proposal. The ruling corpus is named proprietary and unpublished in 87_build_dataset_notes.TERMS |
| `deals_party_matches.csv` | 481 | — | a review by-product: it records what a human ruled, or has yet to rule, on a proposal. The ruling corpus is named proprietary and unpublished in 87_build_dataset_notes.TERMS |
| `lobbying_client_attribution.csv` | 458 | — | a review by-product: it records what a human ruled, or has yet to rule, on a proposal. The ruling corpus is named proprietary and unpublished in 87_build_dataset_notes.TERMS |
| `subaward_identifier_harvest.csv` | 304 | — | identifier/name harvest working set, assembled to feed the spine and the ledger; the grain is our resolution process, not an event in the world; carries a duns column |
| `bie_uio_identifier_links.csv` | 302 | — | identifier/name harvest working set, assembled to feed the spine and the ledger; the grain is our resolution process, not an event in the world; carries duns_internal_only, whose name is the ruling. The dollar rollup built from it (bie_uio_dollars_by_entity) ships |
| `nho_ito_spine_crosswalk.csv` | 269 | — | a review by-product: it records what a human ruled, or has yet to rule, on a proposal. The ruling corpus is named proprietary and unpublished in 87_build_dataset_notes.TERMS |
| `subaward_identifier_netnew.csv` | 210 | — | identifier/name harvest working set, assembled to feed the spine and the ledger; the grain is our resolution process, not an event in the world; every column past the first ten is a comparison against our own prior ledger |
| `entity_year_coverage.csv` | 196 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country |
| `content_audit_fr_relevance.csv` | 120 | — | docs/CONTENT_ANALYSIS.md 'Outputs' files it under 'Audit and accuracy'; it is hand-coded validation of our own classifier, not a record of anything a tribe did |
| `content_audit_lobbying_family.csv` | 120 | — | docs/CONTENT_ANALYSIS.md 'Outputs' files it under 'Audit and accuracy'; it is hand-coded validation of our own classifier, not a record of anything a tribe did |
| `source_coverage_admin_appeals.csv` | 114 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country |
| `gaming_field_coverage.csv` | 112 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country |
| `content_audit_fr_theme.csv` | 110 | — | docs/CONTENT_ANALYSIS.md 'Outputs' files it under 'Audit and accuracy'; it is hand-coded validation of our own classifier, not a record of anything a tribe did |
| `brand_family_registry.csv` | 106 | — | the learned brand-to-entity map. This IS the crosswalk the terms of use name as proprietary and refuse to release as a standalone deliverable |
| `cedar_inherited_from_rulings_2026-08-07.csv` | 100 | — | a dated snapshot of ruling inheritance with NO producing script left in code/; superseded by cedar_identifier_ledger_final.csv |
| `cedar_inherited_from_rulings_2026-08-05.csv` | 80 | — | a dated snapshot of ruling inheritance with NO producing script left in code/; superseded by cedar_identifier_ledger_final.csv |
| `cedar_inherited_from_rulings_2026-08-06.csv` | 80 | — | a dated snapshot of ruling inheritance with NO producing script left in code/; superseded by cedar_identifier_ledger_final.csv |
| `cedar_spiderweb_v2.csv` | 79 | — | identifier/name harvest working set, assembled to feed the spine and the ledger; the grain is our resolution process, not an event in the world |
| `faads_identifier_coverage_by_agency_year.csv` | 77 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country; its measures are percentages of rows carrying DUNS, which is a property of the source extract we hold |
| `source_coverage_fac.csv` | 62 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country |
| `deals_party_attribution.csv` | 56 | — | a review by-product: it records what a human ruled, or has yet to rule, on a proposal. The ruling corpus is named proprietary and unpublished in 87_build_dataset_notes.TERMS |
| `deals_taxonomy.csv` | 48 | — | a four-column count of our own deal axes, produced by 88_build_deals_taxonomy.py, which is on the do-not-run list |
| `individual_native_prior_rulings.csv` | 45 | — | a review by-product: it records what a human ruled, or has yet to rule, on a proposal. The ruling corpus is named proprietary and unpublished in 87_build_dataset_notes.TERMS |
| `source_coverage_nrc_meetings.csv` | 37 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country |
| `np_ein_uei_bridge.csv` | 28 | — | identifier/name harvest working set, assembled to feed the spine and the ledger; the grain is our resolution process, not an event in the world; match_evidence, funnel_stage and review_flag are the recipe, and 41_build_codebooks tiers all three internal already |
| `grantmaker_funding_coverage.csv` | 27 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country |
| `federal_funding_year_comparison_2026-08-05.csv` | 26 | — | a dated reconciliation of two of our own extracts against each other. Its column names (A_raw_rows, B_wide_tribe_rows) are working notation |
| `variable_registry.csv` | 22 | — | Cedar's internal concept-to-column registry; it documents our naming rather than measuring anything |
| `nho_parents.csv` | 21 | — | a by-product of the NHO review queues: parent name and a count of subsidiaries, with no source and no date |
| `resource_asset_source_coverage.csv` | 18 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country |
| `instrument_taxonomy.csv` | 17 | — | Cedar's own instrument taxonomy, including sum_obligations_directly - an instruction to our builds |
| `source_coverage_tribal_legislative.csv` | 17 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country |
| `source_coverage_visitor_records.csv` | 11 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country |
| `ferc_source_coverage.csv` | 9 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country |
| `native_issue_litigation_coverage.csv` | 8 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country |
| `sam_prime_contracts_fy2000_2007_reconciliation.csv` | 6 | — | a reconciliation of the SAM backfill against the archive, including double_count_risk_rows - a check on our own load |
| `nepa_source_coverage.csv` | 5 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country |
| `content_analysis_accuracy.csv` | 4 | — | docs/CONTENT_ANALYSIS.md 'Outputs' files it under 'Audit and accuracy'; it is hand-coded validation of our own classifier, not a record of anything a tribe did |
| `fr_relevance_stratum_audit.csv` | 4 | — | docs/CONTENT_ANALYSIS.md 'Outputs' files it under 'Audit and accuracy'; it is hand-coded validation of our own classifier, not a record of anything a tribe did |
| `gaming_game_finder_systems.csv` | 3 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country; three rows describing the three harvest systems, their entry points and transports |
| `source_coverage_vendor_disclosure.csv` | 2 | — | a self-measurement of Cedar's own collection - what we swept, what answered, how much we covered. A fact about us, not about Indian Country |
| `congressional_correspondence_log.csv` | 0 | — | OUT OF SCOPE. Its generator (136.build_correspondence_layer) would today emit FOUR rows, not zero - the FOIA index grew 9,481 -> 20,102 - and all four are HHS Office of the Secretary requests carrying native_related=N (Tom Price, Alex Azar, unaccompanied alien children, a Rand Paul meta-FOIA). Four rows of non-Native noise in an Indian-affairs collection is worse than nothing. No agency in scope publishes the log itself: log_publicly_posted is NOT_FOUND or NO_ONLY_RELEASED_ON_REQUEST on all 257 rows of congressional_correspondence_systems.csv, which is the table that carries the finding and does ship |

## EMPTY — 4 table(s), 0 rows

| table | rows | block | why |
|---|---:|---|---|
| `cedar_fact_conflicts.csv` | 0 | — | zero rows; nothing to ship and nothing to rule on |
| `sam_entity_connections.csv` | 0 | — | zero rows; nothing to ship and nothing to rule on |
| `sam_subsidiary_candidates.csv` | 0 | — | zero rows; nothing to ship and nothing to rule on |
| `wa_machine_transfers.csv` | 0 | — | zero rows; nothing to ship and nothing to rule on |
