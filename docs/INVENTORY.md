# Cedar Press inventory — every table, every script

*Generated 2026-09-01 by `code/521_inventory.py` from live artefacts. **Do not hand-edit** — regenerate. Every column is read from a registry that already owns the fact, or measured off the file on disk; nothing here is typed. A fact that cannot be derived prints `UNKNOWN`.*

```
py -3 code/521_inventory.py            # regenerate this document
py -3 code/521_inventory.py --no-scan  # cache only, uncached -> UNKNOWN
py -3 code/521_inventory.py check      # exit 1 if the headline is stale
```

## Headline

| | |
|---|---:|
| tables inventoried | **305** |
| — in `data/clean` | 287 |
| — in `data/spine` | 18 |
| status `shippable` | 210 |
| status `internal-by-decision` | 65 |
| status `licensed` | 2 |
| status `undocumented` | 3 |
| status `spine` | 18 |
| status `excluded-by-codebook` | 7 |
| rows across all inventoried tables | 8,915,870 |
| entity-bearing tables | 137 |
| entity-bearing rows | 7,250,729 |
| — carrying a Cedar id | 3,215,604 (44.3%) |
| grain declared AND validated | 186 |
| shipping in `dist/cedar_press.db` | 181 |
| scripts inventoried (`code/**/*.py`) | **427** |
| — live | 103 |
| — referenced | 311 |
| — spent one-off | 8 |
| — unreferenced | 1 |
| — NEVER_RUN | 4 |
| script numbers colliding within one directory | 43 |

**How `keyed %` is defined here**, because two documents have used two different denominators: a table is *entity-bearing* if its header carries `cedar_uid` or one of the eighteen id columns in `503_identity.ID_COLS` (imported, not copied). `keyed` counts rows whose value in that column is non-empty and is not a null-word. A table with no such column is not counted at all — that is different from 0%, and the two are printed differently below.

## Tables, by collection

`grain` — `Y` declared **and** validated against the file on every run (ADR-007); `open` — an owner ruling is pending with evidence attached; `DEFECT` — the data itself is broken and a declaration cannot fix it; `—` unstated. `ship` — `db` present in `dist/cedar_press.db`, `notes` a `.notes.json` receipt only, `—` neither. `NEVER_RUN` — a script in this table's build or enrich chain is in `cedar_pipeline.NEVER_RUN` and running it destroys work.

### `(no collection)` — 36 table(s)

| table | status | rows | cols | grain | PK | keyed | latest yr | modified | ship | agg | built by | enriched by | flags |
|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|
| `_bill_actions.csv` | excluded-by-codebook | 31,936 | 15 | — | — | n/a | 2026 | 2026-08-06 | — | — | — | — | — |
| `_bill_actions_fetch_log.csv` | excluded-by-codebook | 3,061 | 7 | — | — | n/a | — | 2026-08-06 | — | — | — | — | — |
| `_bill_metadata_backfill.csv` | excluded-by-codebook | 128 | 13 | — | — | n/a | 2025 | 2026-08-06 | — | — | — | — | — |
| `_cosponsor_fetch_log.csv` | excluded-by-codebook | 275 | 6 | — | — | n/a | — | 2026-08-05 | — | — | — | — | — |
| `_cosponsors.csv` | excluded-by-codebook | 5,318 | 8 | — | — | n/a | 2024 | 2026-08-05 | — | — | — | — | — |
| `brand_family_proposals.csv` | internal-by-decision | 609 | 12 | — | — | n/a | — | 2026-08-06 | — | — | — | — | — |
| `brand_family_registry.csv` | internal-by-decision | 106 | 8 | — | — | 100% | — | 2026-08-28 | — | — | — | — | — |
| `cedar_assertions.csv` | internal-by-decision | 34,503 | 19 | — | — | 100% | 2026 | 2026-08-29 | — | — | — | — | — |
| `cedar_cage_backfill.csv` | internal-by-decision | 4,362 | 7 | — | — | n/a | 2026 | 2026-08-05 | — | — | — | — | — |
| `cedar_dataset_punchlist.csv` | internal-by-decision | 418 | 8 | — | — | n/a | 2026 | 2026-09-01 | — | — | — | — | — |
| `cedar_dataset_readiness.csv` | internal-by-decision | 13 | 25 | — | — | n/a | 2026 | 2026-09-01 | — | — | — | — | — |
| `cedar_export_safety.csv` | internal-by-decision | 214 | 11 | — | — | n/a | — | 2026-08-29 | — | — | — | — | — |
| `cedar_fact_conflicts.csv` | internal-by-decision | 0 | 15 | — | — | n/a | — | 2026-08-29 | — | — | — | — | — |
| `cedar_harvest_conservation.csv` | internal-by-decision | 88 | 7 | — | — | n/a | — | 2026-08-29 | — | — | — | — | — |
| `cedar_inherited_from_rulings_2026-08-05.csv` | internal-by-decision | 80 | 9 | — | — | n/a | 2026 | 2026-08-05 | — | — | — | — | — |
| `cedar_inherited_from_rulings_2026-08-06.csv` | internal-by-decision | 80 | 9 | — | — | n/a | 2026 | 2026-08-06 | — | — | — | — | — |
| `cedar_inherited_from_rulings_2026-08-07.csv` | internal-by-decision | 100 | 9 | — | — | n/a | 2026 | 2026-08-07 | — | — | — | — | — |
| `cedar_resolved_facts.csv` | internal-by-decision | 34,163 | 22 | — | — | 100% | 2026 | 2026-08-29 | — | — | — | — | — |
| `cedar_spiderweb_v2.csv` | internal-by-decision | 79 | 16 | — | — | 100% | 2026 | 2026-08-28 | — | — | — | — | — |
| `codebook_master.csv` | excluded-by-codebook | 4,614 | 10 | — | — | n/a | — | 2026-08-29 | — | — | 41_build_codebooks.py | 104_build_wa_allocatio, 107_pull_remaining_sta, 108_build_tribal_tax_b +9 | **NEVER_RUN:** 41 |
| `content_analysis_accuracy.csv` | internal-by-decision | 4 | 16 | — | — | n/a | 2026 | 2026-08-06 | — | — | — | — | — |
| `content_audit_fr_relevance.csv` | internal-by-decision | 120 | 9 | — | — | n/a | 2026 | 2026-08-06 | — | — | — | — | — |
| `content_audit_fr_theme.csv` | internal-by-decision | 110 | 8 | — | — | n/a | 2026 | 2026-08-06 | — | — | — | — | — |
| `content_audit_lobbying_family.csv` | internal-by-decision | 120 | 8 | — | — | n/a | 2026 | 2026-08-06 | — | — | — | — | — |
| `coverage_audit.csv` | internal-by-decision | 912 | 6 | — | — | n/a | 2026 | 2026-08-28 | — | — | — | — | — |
| `instrument_taxonomy.csv` | internal-by-decision | 17 | 8 | — | — | n/a | — | 2026-08-06 | — | — | — | — | — |
| `sam_entity_connections.csv` | internal-by-decision | 0 | 16 | — | — | n/a | — | 2026-08-29 | — | — | — | — | — |
| `sam_subsidiary_candidates.csv` | internal-by-decision | 0 | 11 | — | — | n/a | — | 2026-08-29 | — | — | — | — | — |
| `series_breaks.csv` | excluded-by-codebook | 24 | 9 | — | — | n/a | 2026 | 2026-08-26 | — | — | — | — | — |
| `source_coverage_admin_appeals.csv` | internal-by-decision | 114 | 7 | — | — | n/a | 2026 | 2026-08-12 | — | — | — | — | — |
| `source_coverage_fac.csv` | internal-by-decision | 62 | 8 | — | — | n/a | — | 2026-08-12 | — | — | — | — | — |
| `source_coverage_nrc_meetings.csv` | internal-by-decision | 37 | 8 | — | — | n/a | — | 2026-08-12 | — | — | — | — | — |
| `source_coverage_tribal_legislative.csv` | internal-by-decision | 17 | 10 | — | — | n/a | — | 2026-08-12 | — | — | — | — | — |
| `source_coverage_vendor_disclosure.csv` | internal-by-decision | 2 | 9 | — | — | n/a | — | 2026-08-12 | — | — | — | — | — |
| `source_coverage_visitor_records.csv` | internal-by-decision | 11 | 7 | — | — | n/a | — | 2026-08-12 | — | — | — | — | — |
| `variable_registry.csv` | internal-by-decision | 22 | 11 | — | — | n/a | — | 2026-08-07 | — | — | — | — | — |

### `contractors` — pro shelf — 11 table(s)

| table | status | rows | cols | grain | PK | keyed | latest yr | modified | ship | agg | built by | enriched by | flags |
|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|
| `contractor_ranking.csv` | shippable | 1,429 | 43 | open | — | n/a | 2026 | 2026-08-26 | db | **row-only** | — | — | — |
| `fpds_uei_cage_map.csv` | shippable | 34,601 | 7 | open | — | n/a | 2026 | 2026-09-01 | notes | **row-only** | — | — | — |
| `fpds_uei_edges.csv` | shippable | 5,167 | 12 | Y | child_uei+parent_uei+edge_type | n/a | 2026 | 2026-09-01 | notes | safe | 13_build_fpds_hierarch | 26_fix_sanity_failures | — |
| `prime_contracts.csv` | shippable | 1,217,768 | 47 | Y | contract_transaction_unique_key+contract_number+parent_contract_number+fiscal_year+awardee_uei | 73% | 2026 | 2026-08-29 | db | safe | 40_build_prime_contrac | 207_normalize_extent_c, 429_apply_asof_ownersh, 430_restore_prime_tran | — |
| `prime_contracts_archive_backfill.csv` | shippable | 631,507 | 40 | Y | contract_transaction_unique_key | 100% | 2025 | 2026-08-29 | db | safe | 114_pull_prime_archive | 430_restore_prime_tran | — |
| `prime_contracts_awards.csv` | shippable | 455,080 | 31 | Y | contract_number | 59% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `prime_contracts_entity_year.csv` | shippable | 6,715 | 17 | Y | tribe_id+fiscal_year | 100% | 2026 | 2026-08-29 | db | safe | 40_build_prime_contrac | 131_merge_archive_back, 428_rebuild_prime_enti | — |
| `prime_contracts_published.csv` | shippable | 455,080 | 25 | Y | contract_number | 59% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `sam_prime_contracts_fy2000_2007.csv` | shippable | 269,312 | 90 | Y | sam_transaction_key | n/a | 2099 | 2026-08-26 | db | safe | — | — | — |
| `sam_prime_contracts_fy2000_2007_PUBLISHABLE.csv` | shippable | 269,312 | 80 | Y | sam_transaction_key | n/a | 2099 | 2026-08-26 | notes | safe | — | — | — |
| `sam_prime_contracts_fy2000_2007_reconciliation.csv` | internal-by-decision | 6 | 13 | — | — | n/a | — | 2026-08-26 | — | — | — | — | — |

### `deals` — standard shelf — 19 table(s)

| table | status | rows | cols | grain | PK | keyed | latest yr | modified | ship | agg | built by | enriched by | flags |
|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|
| `deals_2000_2019_additions.csv` | shippable | 40 | 32 | Y | Deal_ID | n/a | 2019 | 2026-08-05 | db | safe | — | — | — |
| `deals_2026_ytd_additions.csv` | shippable | 0 | 31 | open | — | n/a | — | 2026-08-05 | db | **row-only** | — | — | — |
| `deals_anc_reports_additions.csv` | shippable | 28 | 32 | Y | Deal_ID | n/a | 2015 | 2026-08-05 | db | safe | — | — | — |
| `deals_ancsa_portal_additions.csv` | shippable | 34 | 32 | Y | Deal_ID | n/a | 2025 | 2026-08-05 | db | safe | build_deals.py | build_deals2.py | — |
| `deals_ancsa_portal_v2_additions.csv` | shippable | 42 | 32 | Y | Deal_ID | n/a | 2026 | 2026-08-05 | db | safe | — | — | — |
| `deals_classified.csv` | shippable | 935 | 52 | Y | Deal_ID | 95% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `deals_federal_awards_additions.csv` | shippable | 594 | 32 | Y | Deal_ID | n/a | 2025 | 2026-08-05 | db | safe | — | — | — |
| `deals_historical_additions.csv` | shippable | 30 | 32 | Y | Deal_ID | n/a | 2025 | 2026-08-05 | db | safe | — | — | — |
| `deals_party_attribution.csv` | internal-by-decision | 56 | 14 | — | — | 73% | — | 2026-08-28 | — | — | — | — | — |
| `deals_party_attribution_agent.csv` | internal-by-decision | 530 | 20 | — | — | 95% | — | 2026-08-28 | — | — | — | — | — |
| `deals_party_autoresolved.csv` | internal-by-decision | 502 | 12 | — | — | 100% | 2026 | 2026-08-28 | — | — | 57_autoresolve_deal_pa | 154_extend_autoresolve | — |
| `deals_party_matches.csv` | internal-by-decision | 481 | 6 | — | — | n/a | — | 2026-08-26 | — | — | — | — | — |
| `deals_sec_2010_2017_additions.csv` | shippable | 16 | 32 | Y | Deal_ID | n/a | 2017 | 2026-08-05 | db | safe | — | — | — |
| `deals_source_index.csv` | shippable | 533 | 10 | Y | native_party | n/a | — | 2026-08-06 | db | safe | — | — | — |
| `deals_taxonomy.csv` | internal-by-decision | 48 | 4 | — | — | n/a | — | 2026-08-06 | — | — | — | — | — |
| `deals_tribal_debt_additions.csv` | shippable | 6 | 32 | Y | Deal_ID | n/a | 2021 | 2026-08-05 | db | safe | — | — | — |
| `ownership_events.csv` | shippable | 98 | 33 | Y | event_id | 95% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `seminole_bond_disclosures.csv` | shippable | 29 | 37 | Y | disclosure_id | 100% | 2033 | 2026-08-28 | db | safe | — | — | — |
| `tribal_resolution_financings.csv` | shippable | 1 | 33 | open | — | 100% | — | 2026-08-28 | db | **row-only** | — | — | — |

### `federal-register` — standard shelf — 23 table(s)

| table | status | rows | cols | grain | PK | keyed | latest yr | modified | ship | agg | built by | enriched by | flags |
|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|
| `consultation_agency_coverage.csv` | undocumented | 66 | 25 | — | — | n/a | 2026 | 2026-08-07 | — | — | — | — | — |
| `consultation_events.csv` | shippable | 11,402 | 29 | Y | consultation_event_id+participant_name_as_published | 91% | 2026 | 2026-08-28 | db | safe | 96_build_consultation_ | 503_identity.py | — |
| `correspondence_foia_source_coverage.csv` | shippable | 124 | 8 | Y | url | n/a | — | 2026-08-12 | db | safe | — | — | — |
| `federal_actions.csv` | shippable | 156,772 | 33 | Y | document_number | n/a | 2026 | 2026-08-26 | db | safe | 11_classify_federal_ac | 22_apply_temporal_floo, 519_closure_federal_re | — |
| `federal_actions_entity_bridge.csv` | shippable | 5,786 | 14 | Y | document_number+tribe_id | 100% | 2026 | 2026-08-28 | db | safe | 70_key_unjoined_datase | 503_identity.py | — |
| `federal_actions_raw.csv` | shippable | 156,772 | 25 | Y | document_number | n/a | 2026 | 2026-08-26 | db | safe | — | — | — |
| `fr_abstract_availability_year.csv` | shippable | 33 | 4 | Y | publication_year | n/a | 2026 | 2026-08-29 | db | safe | — | — | — |
| `fr_consultation_by_agency.csv` | shippable | 21 | 3 | Y | normalized_department | n/a | — | 2026-08-06 | — | safe | — | — | — |
| `fr_consultation_notices.csv` | shippable | 484 | 11 | Y | document_number | n/a | 2026 | 2026-08-06 | db | safe | — | — | — |
| `fr_consultation_referenced.csv` | shippable | 1,829 | 5 | Y | document_number | n/a | 2025 | 2026-08-06 | db | safe | — | — | — |
| `fr_consultation_year.csv` | shippable | 33 | 3 | Y | publication_year | n/a | 2026 | 2026-08-06 | db | safe | — | — | — |
| `fr_content_classification.csv` | shippable | 156,452 | 13 | Y | document_number | n/a | 2026 | 2026-08-06 | db | safe | — | — | — |
| `fr_recognized_entities.csv` | internal-by-decision | 575 | 7 | — | — | n/a | — | 2026-08-06 | — | — | — | — | — |
| `fr_relevance_stratum_audit.csv` | internal-by-decision | 4 | 5 | — | — | n/a | — | 2026-08-06 | — | — | — | — | — |
| `fr_relevance_tier_year.csv` | shippable | 132 | 3 | Y | publication_year+relevance_tier | n/a | 2026 | 2026-08-06 | db | safe | — | — | — |
| `fr_theme_year.csv` | shippable | 627 | 5 | Y | publication_year+theme | n/a | 2026 | 2026-08-06 | db | safe | — | — | — |
| `nepa_administrative_record_parties.csv` | shippable | 36 | 23 | Y | party_id+party_name_as_published | 100% | — | 2026-08-28 | db | safe | 134_build_nepa_eplanni | 503_identity.py | — |
| `nepa_eplanning_projects.csv` | shippable | 312 | 27 | Y | nepa_number | n/a | — | 2026-08-12 | db | safe | — | — | — |
| `nepa_project_documents.csv` | shippable | 789 | 21 | Y | nepa_number+document_name_verbatim | n/a | 2026 | 2026-08-12 | db | safe | — | — | — |
| `nepa_source_coverage.csv` | internal-by-decision | 5 | 7 | — | — | n/a | — | 2026-08-12 | — | — | — | — | — |
| `section_106_consultation_events.csv` | shippable | 1,363 | 43 | Y | consultation_event_id | 17% | 2026 | 2026-08-28 | db | safe | 130_build_section_106_ | 503_identity.py | — |
| `section_106_project_parties.csv` | shippable | 51 | 25 | Y | party_id | 0% | 2025 | 2026-08-28 | db | safe | 130_build_section_106_ | 503_identity.py | — |
| `section_106_source_coverage.csv` | shippable | 5 | 9 | Y | source | n/a | — | 2026-08-12 | db | safe | — | — | — |

### `funding` — standard shelf — 15 table(s)

| table | status | rows | cols | grain | PK | keyed | latest yr | modified | ship | agg | built by | enriched by | flags |
|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|
| `assistance_tribe_id_crosswalk.csv` | internal-by-decision | 361 | 15 | — | — | n/a | — | 2026-08-28 | — | — | 152_build_assistance_i | 503_identity.py | — |
| `faads_attribution_audit_sample.csv` | internal-by-decision | 2,287 | 13 | — | — | 100% | — | 2026-08-28 | — | — | — | — | — |
| `faads_entity_attribution.csv` | shippable | 29,594 | 27 | Y | faads_row_id | 100% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `faads_identifier_coverage_by_agency_year.csv` | internal-by-decision | 77 | 11 | — | — | n/a | 2007 | 2026-08-05 | — | — | — | — | — |
| `faads_transactions.csv` | shippable | 60,661 | 25 | **DEFECT** | — | 0% | 2007 | 2026-08-28 | db | **row-only** | — | — | 1,001 dup rows |
| `faads_transactions_all_agencies.csv` | shippable | 2,769,748 | 25 | **DEFECT** | — | 0% | 2007 | 2026-08-28 | db | **row-only** | — | — | 179,259 dup rows |
| `federal_funding_rulings_from_dofile.csv` | spine | 3,789 | 8 | — | — | n/a | — | 2026-08-05 | — | — | — | — | — |
| `federal_funding_transactions.csv` | shippable | 701,955 | 58 | Y | assistance_transaction_unique_key | 79% | 2026 | 2026-08-29 | notes | safe | 24_funding_merge.py | 115_pull_assistance_ar, 335_harmonize_assistan, 336_correct_scheme_res +1 | — |
| `federal_funding_tribe_year_panel.csv` | shippable | 5,496 | 16 | Y | tribe_id+fiscal_year | 100% | 2023 | 2026-08-28 | notes | safe | — | — | — |
| `federal_funding_year_comparison_2026-08-05.csv` | internal-by-decision | 26 | 10 | — | — | n/a | 2025 | 2026-08-05 | — | — | — | — | — |
| `funding_identifier_harvest.csv` | internal-by-decision | 37,704 | 16 | — | — | n/a | 2025 | 2026-08-05 | — | — | — | — | — |
| `funding_identifier_netnew_ueis.csv` | shippable | 4,249 | 1 | Y | recipient_uei | n/a | — | 2026-08-05 | db | safe | — | — | — |
| `inflation_deflator.csv` | shippable | 27 | 6 | Y | year | n/a | 2025 | 2026-08-06 | — | safe | — | — | — |
| `native_passthrough.csv` | shippable | 1,262 | 18 | **DEFECT** | — | n/a | 2026 | 2026-08-29 | db | **row-only** | — | — | 114 dup rows |
| `native_passthrough_pairs.csv` | shippable | 212 | 10 | Y | from_tribe_id+to_tribe_id | n/a | 2026 | 2026-08-12 | db | safe | — | — | — |

### `gaming` — grove shelf — 53 table(s)

| table | status | rows | cols | grain | PK | keyed | latest yr | modified | ship | agg | built by | enriched by | flags |
|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|
| `ca_gaming_facilities_official.csv` | shippable | 245 | 30 | Y | record_id | 98% | 2026 | 2026-08-28 | db | safe | 103_build_california_g | 266_apply_gaming_hub_s | — |
| `ca_gaming_payments.csv` | shippable | 40,164 | 46 | Y | payment_id | 89% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `compact_events.csv` | shippable | 31 | 20 | Y | event_id | 100% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `compact_obligation_tribal_agency_bridge.csv` | shippable | 927 | 20 | Y | bridge_id | 100% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `compact_required_reports.csv` | shippable | 4,121 | 34 | Y | report_id | 99% | 2051 | 2026-08-28 | db | safe | — | — | — |
| `compact_structured_terms.csv` | shippable | 2,887 | 40 | Y | term_id | 99% | 2060 | 2026-08-28 | db | safe | — | — | — |
| `compact_terms.csv` | shippable | 1,311 | 22 | Y | version_id+quote | 99% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `compact_versions.csv` | shippable | 1,158 | 25 | Y | version_id | n/a | 2026 | 2026-08-05 | db | safe | — | — | — |
| `compacts.csv` | shippable | 707 | 34 | Y | compact_id | 99% | 2060 | 2026-08-28 | db | safe | — | — | — |
| `digital_gaming_relationships.csv` | shippable | 154 | 40 | Y | digital_gaming_id | 100% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `digital_gaming_revenue.csv` | shippable | 10,661 | 34 | Y | revenue_id | 73% | 2026 | 2026-08-28 | db | safe | 119_build_digital_and_ | 174_backfill_digital_g | — |
| `fac_audit_gaming_disclosures.csv` | shippable | 1,521 | 25 | Y | report_id+verbatim_quote+source_page | 88% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `fac_audit_sefa_gaming_programs.csv` | shippable | 1 | 25 | open | — | 100% | 2021 | 2026-08-28 | db | **row-only** | — | — | — |
| `fl_gaming_payments.csv` | shippable | 9,756 | 56 | Y | payment_id | 100% | 2031 | 2026-08-28 | db | safe | — | — | — |
| `gaming_capacity_official.csv` | shippable | 6,461 | 34 | Y | observation_id | 98% | 2050 | 2026-08-28 | db | safe | 92_build_gaming_capaci | 106_build_revenue_boun | — |
| `gaming_decision_compact_join.csv` | shippable | 138 | 16 | Y | decision_id | n/a | 2026 | 2026-08-05 | db | safe | — | — | — |
| `gaming_decision_events.csv` | shippable | 265 | 13 | Y | event_id | n/a | 2026 | 2026-08-05 | db | safe | — | — | — |
| `gaming_device_observations.csv` | shippable | 1,326 | 26 | Y | observation_id | 94% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `gaming_employment_observations.csv` | shippable | 3,246 | 63 | Y | observation_id | 99% | 2026 | 2026-08-28 | db | safe | 100_finish_declination | 158_merge_staged_labor, 262_repair_form5500_tr, 265_merge_osha_relift_ | — |
| `gaming_facilities.csv` | shippable | 787 | 105 | Y | facility_id | 100% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `gaming_facility_metrics.csv` | licensed | 68,211 | 25 | — | — | 98% | 2026 | 2026-08-26 | — | — | — | — | never ships |
| `gaming_field_coverage.csv` | internal-by-decision | 110 | 7 | — | — | n/a | — | 2026-08-26 | — | — | — | — | — |
| `gaming_financing_events.csv` | shippable | 293 | 39 | Y | financing_event_id | 94% | 2026 | 2026-08-28 | db | safe | 91_build_nigc_declinat | 100_finish_declination | — |
| `gaming_game_finder_observations.csv` | shippable | 6,851 | 38 | Y | observation_id | 100% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `gaming_game_finder_systems.csv` | internal-by-decision | 3 | 16 | — | — | n/a | — | 2026-08-12 | — | — | — | — | — |
| `gaming_land_decisions.csv` | shippable | 138 | 37 | Y | decision_id | 99% | 2026 | 2026-08-28 | notes | safe | — | — | — |
| `gaming_manufacturer_facts.csv` | shippable | 62 | 20 | Y | fact_id | n/a | 2026 | 2026-08-26 | db | safe | — | — | — |
| `gaming_mitigation_agreements.csv` | shippable | 24 | 20 | Y | project_id+counterparty_government+service | n/a | 2024 | 2026-08-05 | — | safe | — | — | — |
| `gaming_nigc_roster_link.csv` | shippable | 453 | 18 | Y | facility_id | 98% | — | 2026-08-28 | db | safe | — | — | — |
| `gaming_ordinance_ocr.csv` | shippable | 263 | 19 | Y | ordinance_id | 96% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `gaming_ordinances.csv` | shippable | 1,155 | 74 | Y | ordinance_id | 96% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `gaming_project_facilities.csv` | shippable | 19 | 40 | Y | project_id+alternative+source_document | 0% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `gaming_projections.csv` | shippable | 116 | 22 | open | — | n/a | 2026 | 2026-08-06 | db | **row-only** | — | — | — |
| `gaming_properties.csv` | shippable | 784 | 55 | Y | facility_id | 100% | 2025 | 2026-08-28 | db | safe | 82_build_gaming_proper | 160_sync_published_gam, 175_sync_published_pro, 255_fix_gaming_propert | — |
| `gaming_property_capacity_history.csv` | licensed | 64,181 | 16 | — | — | 100% | 2026 | 2026-08-26 | — | — | — | — | never ships |
| `gaming_property_coverage.csv` | internal-by-decision | 787 | 37 | — | — | 100% | — | 2026-08-28 | — | — | — | — | — |
| `gaming_property_federal_traces.csv` | shippable | 774 | 68 | Y | facility_id | 98% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `gaming_property_labor_demand.csv` | shippable | 43 | 30 | Y | observation_id | 72% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `gaming_property_locations.csv` | undocumented | 2,212 | 32 | — | — | n/a | — | 2026-08-12 | — | — | — | — | — |
| `gaming_property_site_observations.csv` | shippable | 262 | 33 | Y | observation_id | 64% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `gaming_property_universe_events.csv` | shippable | 10 | 33 | Y | event_id | 40% | 2026 | 2026-08-28 | db | safe | 89_nigc_map_wayback_un | 165_link_universe_even | — |
| `gaming_revenue_bounds.csv` | shippable | 13,803 | 20 | Y | bound_id | 97% | 2025 | 2026-08-28 | db | safe | — | — | — |
| `gaming_source_claims.csv` | shippable | 113 | 25 | Y | source_claim_id | n/a | 2026 | 2026-08-07 | db | safe | 91_build_nigc_declinat | 100_finish_declination, 510_assertions.py | — |
| `gaming_vendor_tribal_licenses.csv` | shippable | 740 | 31 | Y | vendor_name+tribal_gaming_regulator+source_url | 80% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `loyalty_program_property.csv` | shippable | 48 | 20 | Y | loyalty_program_id+facility_id | 100% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `loyalty_programs.csv` | shippable | 18 | 39 | Y | loyalty_program_id | 100% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `nigc_declination_letters.csv` | shippable | 327 | 61 | Y | cedar_opinion_id | 94% | 2026 | 2026-08-28 | db | safe | 91_build_nigc_declinat | 100_finish_declination | — |
| `nigc_region_assignments.csv` | shippable | 2,438 | 21 | Y | facility_id+effective_start_year | 98% | 2025 | 2026-08-28 | db | safe | — | — | — |
| `nigc_regional_ggr.csv` | shippable | 198 | 27 | Y | administrative_region_id+fiscal_year | n/a | 2025 | 2026-08-06 | db | safe | — | — | — |
| `nigc_revenue_bands.csv` | shippable | 20 | 29 | Y | band_id | n/a | 2025 | 2026-08-26 | db | safe | — | — | — |
| `state_gaming_observations.csv` | shippable | 494 | 32 | Y | observation_id | 70% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `wa_machine_allocations.csv` | shippable | 75 | 17 | Y | allocation_id | 100% | 2021 | 2026-08-28 | db | safe | — | — | — |
| `wa_machine_transfers.csv` | undocumented | 0 | 18 | — | — | n/a | — | 2026-08-07 | — | — | — | — | — |

### `legislation` — standard shelf — 13 table(s)

| table | status | rows | cols | grain | PK | keyed | latest yr | modified | ship | agg | built by | enriched by | flags |
|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|
| `bill_votes.csv` | shippable | 423 | 60 | Y | vote_id | n/a | 2025 | 2026-09-01 | db | safe | — | — | — |
| `bill_votes_entity_bridge.csv` | shippable | 75 | 11 | Y | vote_id+tribe_id | 100% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `bill_votes_official_verification.csv` | shippable | 305 | 26 | Y | vote_id | n/a | 2025 | 2026-08-06 | db | safe | — | — | — |
| `congressional_correspondence_log.csv` | shippable | 0 | 24 | open | — | n/a | — | 2026-08-28 | db | **row-only** | — | — | — |
| `congressional_correspondence_systems.csv` | shippable | 257 | 18 | Y | system_id+verbatim_quote | n/a | 2026 | 2026-08-12 | db | safe | — | — | — |
| `member_positions.csv` | shippable | 136,119 | 17 | Y | vote_id+bioguide_id | n/a | — | 2026-08-05 | db | safe | — | — | — |
| `native_bill_outcomes.csv` | shippable | 3,069 | 25 | Y | bill_id | n/a | 2026 | 2026-08-06 | db | safe | — | — | — |
| `native_bills.csv` | shippable | 3,069 | 29 | Y | bill_id | n/a | 2026 | 2026-08-06 | db | safe | 14_build_bills_votes.p | 35_entity_harvest.py | — |
| `native_bills_entity_bridge.csv` | shippable | 676 | 13 | Y | bill_id+tribe_id | 100% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `native_bills_entity_class.csv` | shippable | 2,694 | 13 | Y | bill_id+class_match_basis | n/a | — | 2026-08-06 | db | safe | — | — | — |
| `native_bills_subject_sweep.csv` | shippable | 2,414 | 21 | **DEFECT** | — | n/a | 2026 | 2026-08-06 | db | **row-only** | — | — | 5 dup rows |
| `native_issue_litigation_coverage.csv` | internal-by-decision | 8 | 8 | — | — | n/a | — | 2026-08-12 | — | — | — | — | — |
| `native_issue_litigation_positions.csv` | shippable | 197 | 39 | Y | position_id | n/a | 2025 | 2026-08-12 | db | safe | 139_build_litigation_p | 140_build_grantmaker_f | — |

### `lobbying` — standard shelf — 37 table(s)

| table | status | rows | cols | grain | PK | keyed | latest yr | modified | ship | agg | built by | enriched by | flags |
|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|
| `admin_appeal_decisions.csv` | shippable | 15,613 | 51 | Y | decision_id | n/a | 2026 | 2026-08-26 | db | safe | 144_build_admin_appeal | 168_link_adjudication_ | — |
| `admin_appeal_parties.csv` | shippable | 20,027 | 33 | Y | party_id | 3% | 2026 | 2026-08-28 | db | safe | 144_build_admin_appeal | 168_link_adjudication_ | — |
| `admin_appeal_positions.csv` | shippable | 1 | 20 | open | — | 100% | 1973 | 2026-08-28 | db | **row-only** | — | — | — |
| `advocacy_passthrough.csv` | shippable | 1,620 | 28 | Y | passthrough_id | 28% | 2025 | 2026-08-28 | db | safe | — | — | — |
| `advocacy_passthrough_2026-08-07.csv` | shippable | 1,620 | 28 | Y | passthrough_id | 28% | 2025 | 2026-08-28 | notes | safe | — | — | — |
| `agency_attention_vs_advocacy.csv` | shippable | 22 | 11 | Y | department | n/a | — | 2026-08-06 | — | safe | — | — | — |
| `agency_attention_vs_advocacy_year.csv` | shippable | 698 | 4 | Y | department+year | n/a | 2026 | 2026-08-06 | — | safe | — | — | — |
| `earmarks.csv` | shippable | 1,002 | 23 | Y | earmark_id | 100% | 2027 | 2026-08-28 | db | safe | — | — | — |
| `ferc_docket_filings.csv` | shippable | 102,615 | 39 | **DEFECT** | — | 1% | 2026 | 2026-08-28 | db | **row-only** | 133_build_ferc_advocac | 168_link_adjudication_ | 822 dup rows |
| `ferc_docket_parties.csv` | shippable | 11,563 | 18 | Y | ferc_docket_party_id | 2% | — | 2026-08-28 | db | safe | — | — | — |
| `ferc_ex_parte_communications.csv` | shippable | 713 | 34 | open | — | 0% | 2026 | 2026-08-28 | db | **row-only** | — | — | — |
| `ferc_ex_parte_parties.csv` | shippable | 4,246 | 45 | Y | ferc_ex_parte_party_id+table_row_quote | 0% | 2026 | 2026-08-28 | db | safe | 133_build_ferc_advocac | 168_link_adjudication_ | — |
| `ferc_source_coverage.csv` | internal-by-decision | 9 | 7 | — | — | n/a | — | 2026-08-26 | — | — | — | — | — |
| `ferc_tribal_dockets.csv` | shippable | 307 | 30 | Y | docket_number+subdocket | n/a | — | 2026-08-26 | db | safe | 133_build_ferc_advocac | 168_link_adjudication_, 175_restore_ferc_docke | — |
| `fr_ex_parte_notices.csv` | shippable | 7,820 | 27 | Y | fr_ex_parte_notice_id | n/a | 2026 | 2026-08-26 | db | safe | — | — | — |
| `fr_ex_parte_parties.csv` | shippable | 112 | 29 | Y | fr_ex_parte_party_id | 0% | 2026 | 2026-08-28 | db | safe | 154_build_fr_ex_parte_ | 503_identity.py | — |
| `fr_ex_parte_party_entity_links.csv` | shippable | 9 | 13 | Y | link_id | 100% | 2024 | 2026-08-28 | db | safe | 154_build_fr_ex_parte_ | 503_identity.py, 519_closure_federal_re | — |
| `hearing_appearances.csv` | shippable | 2,674 | 26 | Y | hearing_appearance_id | 67% | 2026 | 2026-08-28 | db | safe | 98_build_oira_and_hear | 400_promote_stranded_h | — |
| `hearing_bill_links.csv` | shippable | 465 | 16 | **DEFECT** | — | n/a | 2026 | 2026-08-07 | db | **row-only** | — | — | 1 dup rows |
| `lobbying_client_attribution.csv` | internal-by-decision | 458 | 12 | — | — | 32% | — | 2026-08-28 | — | — | — | — | — |
| `lobbying_disclosure_verbosity_year.csv` | shippable | 27 | 4 | Y | filing_year | n/a | 2026 | 2026-08-06 | — | safe | — | — | — |
| `lobbying_issue_families_filing.csv` | shippable | 27,796 | 19 | Y | filing_uuid | 95% | 2026 | 2026-08-28 | db | safe | 78_content_analysis.py | 353_propagate_lobbying, 503_identity.py | — |
| `lobbying_issue_family_year.csv` | shippable | 476 | 9 | Y | issue_family+filing_year | n/a | 2026 | 2026-08-06 | — | safe | — | — | — |
| `lobbying_registrant_client_relationships.csv` | shippable | 1,309 | 40 | Y | registrant_id+client_id | 98% | 2026 | 2026-08-28 | notes | safe | — | — | — |
| `lobbying_registrant_concentration.csv` | shippable | 36 | 29 | Y | scope+scope_value | n/a | — | 2026-08-26 | db | safe | — | — | — |
| `lobbying_registrant_identifiers.csv` | shippable | 525 | 47 | Y | identifier+asserted_by_source | n/a | 2016 | 2026-08-26 | db | safe | — | — | — |
| `lobbying_registrant_native_ownership_evidence.csv` | shippable | 27 | 22 | **DEFECT** | — | 100% | — | 2026-08-28 | notes | **row-only** | — | — | 4 dup rows |
| `lobbying_registrants.csv` | shippable | 653 | 52 | Y | registrant_id | n/a | — | 2026-08-26 | db | safe | — | — | — |
| `lobbying_target_entities.csv` | shippable | 116 | 3 | Y | government_entity_as_filed | n/a | — | 2026-08-06 | — | safe | — | — | — |
| `lobbying_unmatched_clients.csv` | internal-by-decision | 515 | 13 | — | — | n/a | 2026 | 2026-08-05 | — | — | — | — | — |
| `native_entity_lobbying_disclosures.csv` | shippable | 27,796 | 40 | Y | filing_uuid | 95% | 2026 | 2026-08-28 | notes | safe | 05_match_filings_v2.py | 350_withdraw_false_lob, 65_lobbying_organizati | — |
| `nrc_meeting_participants.csv` | shippable | 407 | 32 | Y | participant_id | 2% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `nrc_public_meetings.csv` | shippable | 251 | 34 | Y | nrc_meeting_id | n/a | 2026 | 2026-08-12 | db | safe | — | — | — |
| `oira_federal_action_links.csv` | shippable | 145 | 10 | Y | oira_meeting_id+federal_action_document_number | n/a | 2026 | 2026-08-07 | db | safe | — | — | — |
| `oira_meeting_participants.csv` | shippable | 1,128 | 20 | Y | oira_participant_id | 8% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `oira_meetings.csv` | shippable | 72 | 22 | Y | oira_meeting_id | 26% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `tribe_year_lobbying_panel.csv` | shippable | 4,997 | 14 | Y | entity_id+filing_year | 100% | 2026 | 2026-08-28 | notes | safe | 05_match_filings_v2.py | 351_rebuild_lobbying_p, 65_lobbying_organizati | — |

### `nagpra` — standard shelf — 4 table(s)

| table | status | rows | cols | grain | PK | keyed | latest yr | modified | ship | agg | built by | enriched by | flags |
|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|
| `fr_nagpra_title_index.csv` | shippable | 6,644 | 10 | Y | document_number | n/a | 2026 | 2026-08-29 | db | safe | — | — | — |
| `fr_nagpra_title_index_year.csv` | shippable | 33 | 4 | Y | publication_year | n/a | 2026 | 2026-08-29 | db | safe | — | — | — |
| `nagpra_notice_entity_bridge.csv` | shippable | 51,521 | 14 | Y | document_number+relationship+party_name_verbatim | 93% | 2026 | 2026-08-29 | db | safe | 77_build_nagpra_datase | 503_identity.py | — |
| `nagpra_notices.csv` | shippable | 6,772 | 67 | Y | document_number | n/a | 2027 | 2026-08-29 | db | safe | — | — | — |

### `native-owned-businesses` — pro shelf — 7 table(s)

| table | status | rows | cols | grain | PK | keyed | latest yr | modified | ship | agg | built by | enriched by | flags |
|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|
| `individual_native_exclusion_pairs.csv` | shippable | 5 | 17 | Y | identifier_type+identifier | n/a | 2026 | 2026-08-26 | db | safe | — | — | — |
| `individual_native_firm_contracts.csv` | shippable | 324 | 29 | Y | surrogate_entity_id+fiscal_year | 100% | 2022 | 2026-08-28 | db | safe | — | — | — |
| `individual_native_firm_contracts_published.csv` | shippable | 613 | 11 | Y | cell_type+dimension_1+dimension_2 | n/a | — | 2026-08-26 | db | safe | — | — | — |
| `individual_native_firm_register.csv` | shippable | 45 | 56 | Y | surrogate_entity_id | 100% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `individual_native_ownership_verification.csv` | shippable | 335 | 63 | Y | verification_id | n/a | 2026 | 2026-08-26 | db | safe | — | — | — |
| `individual_native_prior_rulings.csv` | internal-by-decision | 45 | 13 | — | — | n/a | — | 2026-08-26 | — | — | — | — | — |
| `individual_native_verification_candidates.csv` | shippable | 335 | 42 | Y | verification_id | n/a | 2026 | 2026-08-26 | db | safe | — | — | — |

### `natural-resources` — pro shelf — 9 table(s)

| table | status | rows | cols | grain | PK | keyed | latest yr | modified | ship | agg | built by | enriched by | flags |
|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|
| `anc_ceiling_roster.csv` | shippable | 196 | 12 | Y | anc_id | n/a | — | 2026-08-26 | notes | safe | — | — | — |
| `ancsa_filings_index.csv` | shippable | 19,269 | 17 | Y | portal_document_id | n/a | — | 2026-08-26 | db | safe | build_manifest_index.p | update_index.py | — |
| `nd_severance_allocation.csv` | shippable | 7 | 18 | Y | allocation_id | 100% | 2021 | 2026-08-28 | db | safe | — | — | — |
| `resource_asset_source_coverage.csv` | internal-by-decision | 18 | 8 | — | — | n/a | — | 2026-08-12 | — | — | — | — | — |
| `resource_assets.csv` | shippable | 35 | 45 | Y | resource_asset_id | 0% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `resource_parties.csv` | shippable | 1,436 | 15 | Y | party_link_id+entity_name | 66% | — | 2026-08-28 | db | safe | — | — | — |
| `resource_revenue.csv` | shippable | 10,482 | 41 | Y | resource_revenue_event_id | 7% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `tribal_bond_issuances.csv` | shippable | 29 | 14 | open | — | n/a | 2027 | 2026-08-05 | db | **row-only** | — | — | — |
| `tribal_tax_bases.csv` | shippable | 1,712 | 23 | Y | tax_observation_id | 98% | 2027 | 2026-08-28 | db | safe | — | — | — |

### `nonprofits` — pro shelf — 12 table(s)

| table | status | rows | cols | grain | PK | keyed | latest yr | modified | ship | agg | built by | enriched by | flags |
|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|
| `fac_tribal_single_audits.csv` | shippable | 6,780 | 36 | Y | report_id | 82% | 2026 | 2026-08-29 | db | safe | — | — | — |
| `grantmaker_funding_coverage.csv` | internal-by-decision | 27 | 15 | — | — | n/a | — | 2026-08-12 | — | — | — | — | — |
| `grantmaker_funding_flows.csv` | shippable | 18,656 | 60 | Y | flow_id | 0% | 2025 | 2026-08-28 | db | safe | — | — | — |
| `grantmaker_funding_overlap.csv` | shippable | 69 | 20 | Y | funder_key+recipient_resolved_target | n/a | — | 2026-08-12 | — | safe | — | — | — |
| `np_ein_entity_hub.csv` | shippable | 2,303 | 17 | Y | ein | 100% | — | 2026-08-28 | db | safe | — | — | — |
| `np_ein_uei_bridge.csv` | internal-by-decision | 28 | 17 | — | — | n/a | — | 2026-08-05 | — | — | — | — | — |
| `np_financials.csv` | shippable | 8,507 | 77 | Y | ein+tax_period | n/a | 2075 | 2026-08-26 | db | safe | — | — | — |
| `np_grantee_financials.csv` | shippable | 4,058 | 19 | Y | ein+source_url | n/a | 2025 | 2026-08-07 | db | safe | — | — | — |
| `np_org_scale.csv` | shippable | 1,157 | 30 | Y | ein | n/a | 2025 | 2026-08-05 | db | safe | — | — | — |
| `np_orgs.csv` | shippable | 12,764 | 53 | Y | EIN | 11% | 2026 | 2026-08-28 | notes | safe | — | — | — |
| `np_schedule_i_filers.csv` | shippable | 10,314 | 39 | Y | object_id | n/a | 2026 | 2026-08-26 | db | safe | — | — | — |
| `np_schedule_i_grants.csv` | shippable | 58,685 | 64 | **DEFECT** | — | 4% | 2025 | 2026-08-29 | db | **row-only** | — | — | 101 dup rows |

### `subcontracting` — pro shelf — 5 table(s)

| table | status | rows | cols | grain | PK | keyed | latest yr | modified | ship | agg | built by | enriched by | flags |
|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|
| `prime_sub_network.csv` | shippable | 220 | 12 | Y | prime_uei+sub_uei | n/a | 2023 | 2026-08-05 | db | safe | — | — | — |
| `subaward_entity_rollup.csv` | shippable | 450 | 10 | Y | tribe_id | 100% | — | 2026-08-28 | db | safe | — | — | — |
| `subaward_identifier_harvest.csv` | internal-by-decision | 304 | 16 | — | — | n/a | 2023 | 2026-08-05 | — | — | — | — | — |
| `subaward_identifier_netnew.csv` | internal-by-decision | 210 | 21 | — | — | n/a | 2023 | 2026-08-05 | — | — | — | — | — |
| `subawards.csv` | shippable | 72,837 | 53 | **DEFECT** | — | 43% | 2026 | 2026-08-29 | db | **row-only** | 20_build_subcontracts. | 121_pull_subawards_api, 250_demote_stale_tierA, 45_promote_subawards.p | 10,770 dup rows |

### `_entity_layer` — infrastructure shelf — 47 table(s)

| table | status | rows | cols | grain | PK | keyed | latest yr | modified | ship | agg | built by | enriched by | flags |
|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|
| `admin_region_assignments.csv` | shippable | 2,124 | 22 | Y | assignment_id | n/a | 2025 | 2026-08-06 | db | safe | — | — | — |
| `admin_region_overlap_derived.csv` | shippable | 28 | 10 | Y | administrative_region_id_a+administrative_region_id_b | n/a | — | 2026-08-06 | db | safe | — | — | — |
| `admin_region_systems.csv` | shippable | 6 | 17 | Y | region_system_code | n/a | 2026 | 2026-08-06 | db | safe | — | — | — |
| `admin_regional_observations.csv` | shippable | 27 | 16 | Y | observation_id | n/a | 2026 | 2026-08-26 | db | safe | — | — | — |
| `admin_regions.csv` | shippable | 155 | 17 | Y | administrative_region_id | n/a | — | 2026-08-06 | db | safe | — | — | — |
| `bie_uio_dollars_by_entity.csv` | shippable | 114 | 15 | Y | tribe_id | 100% | — | 2026-08-28 | db | safe | — | — | — |
| `bie_uio_identifier_links.csv` | internal-by-decision | 302 | 20 | — | — | 100% | — | 2026-08-28 | — | — | — | — | — |
| `cedar_correction_register.csv` | shippable | 175 | 14 | Y | correction_id | 99% | — | 2026-09-01 | notes | safe | — | — | — |
| `cedar_entity_identity_crosswalk.csv` | shippable | 10,107 | 20 | Y | crosswalk_id | 100% | — | 2026-08-28 | db | safe | — | — | — |
| `cedar_entity_spine.csv` | spine | 1,555 | 44 | Y | tribe_id | 99% | — | 2026-09-01 | — | — | 01_build_entity_spine. | 08_build_review_page.p, 115_pull_assistance_ar, 163_promote_nho_univer +14 | **NEVER_RUN:** 01 |
| `cedar_identifier_graph_edges.csv` | shippable | 46,051 | 13 | **DEFECT** | — | n/a | — | 2026-08-26 | db | **row-only** | — | — | 2,451 dup rows |
| `cedar_identifier_graph_nodes.csv` | shippable | 115,471 | 16 | Y | node | n/a | — | 2026-08-29 | db | safe | — | — | — |
| `cedar_identifier_ledger.csv` | spine | 19,232 | 14 | — | — | 29% | — | 2026-08-05 | — | — | 01_build_entity_spine. | 03_apply_exclusions_an, 510_assertions.py | **NEVER_RUN:** 01 |
| `cedar_identifier_ledger_final.csv` | shippable | 20,577 | 22 | Y | identifier_type+identifier+tribe_id+attribution_method+evidence_url+verified_date | 39% | — | 2026-08-29 | notes | safe | 09_import_rulings.py | 124_apply_rulings_in_p, 163_promote_nho_univer, 174_apply_rulings_to_s +5 | **NEVER_RUN:** 09 |
| `cedar_identifier_ledger_tiered.csv` | internal-by-decision | 19,232 | 22 | — | — | 33% | — | 2026-08-29 | — | — | 03_apply_exclusions_an | 09_import_rulings.py, 50_fix_kootenai_confla, 64_fix_village_governm | **NEVER_RUN:** 09 |
| `cedar_identifier_propagation.csv` | shippable | 1,157 | 17 | Y | dataset+identifier | n/a | — | 2026-08-29 | db | safe | — | — | — |
| `cedar_publishable_identifiers.csv` | shippable | 1,577 | 18 | Y | identifier | 44% | — | 2026-08-28 | notes | safe | — | — | — |
| `cedar_ruling_ledger_consolidated.csv` | shippable | 15,587 | 15 | **DEFECT** | — | n/a | 2026 | 2026-08-26 | db | **row-only** | — | — | 6,302 dup rows |
| `cedar_rulings.csv` | spine | 8 | 15 | — | — | 62% | — | 2026-08-05 | — | — | — | — | — |
| `cross_dataset_ruling_map.csv` | shippable | 7,507 | 8 | **DEFECT** | — | n/a | 2026 | 2026-08-05 | notes | **row-only** | — | — | 2,228 dup rows |
| `entity_aliases.csv` | shippable | 6,296 | 19 | Y | alias_id | 100% | 2026 | 2026-08-29 | db | safe | 97_build_aliases_and_r | 418_build_entity_alias | — |
| `entity_candidates_new.csv` | internal-by-decision | 2,874 | 27 | — | — | 0% | — | 2026-08-28 | — | — | — | — | — |
| `entity_candidates_rejected.csv` | internal-by-decision | 1,045 | 28 | — | — | 0% | — | 2026-08-28 | — | — | — | — | — |
| `entity_evidence_profile.csv` | internal-by-decision | 1,282 | 11 | — | — | 100% | — | 2026-08-28 | — | — | 151_rebuild_entity_evi | 110_build_harmonized_v | — |
| `entity_hierarchy.csv` | shippable | 952 | 11 | Y | tribe_id | 100% | — | 2026-08-28 | db | safe | — | — | — |
| `entity_name_harvest.csv` | internal-by-decision | 31,728 | 14 | — | — | n/a | — | 2026-08-05 | — | — | — | — | — |
| `entity_relationships.csv` | shippable | 2,292 | 16 | Y | relationship_id | n/a | — | 2026-08-26 | db | safe | 97_build_aliases_and_r | 310_correct_overstated | — |
| `entity_year_coverage.csv` | internal-by-decision | 196 | 7 | — | — | n/a | 2026 | 2026-08-06 | — | — | — | — | — |
| `entity_year_panel.csv` | shippable | 12,534 | 42 | Y | tribe_id+year | 100% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `federal_recognition_events.csv` | shippable | 366 | 31 | Y | entity_key+fr_document_number | 93% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `federal_recognition_roster.csv` | shippable | 17,058 | 22 | Y | fr_document_number+entry_raw | 89% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `foia_discovery_targets.csv` | shippable | 122 | 12 | Y | url | n/a | 2026 | 2026-08-12 | db | safe | — | — | — |
| `foia_request_index.csv` | shippable | 9,481 | 46 | open | — | 4% | 2026 | 2026-08-28 | db | **row-only** | — | — | — |
| `intertribal_memberships.csv` | shippable | 989 | 7 | Y | org_id+member_entity_name+year_observed | n/a | — | 2026-08-05 | db | safe | — | — | — |
| `intertribal_orgs.csv` | shippable | 57 | 15 | Y | proposed_id | n/a | 2018 | 2026-08-05 | db | safe | — | — | — |
| `native_fi_roster.csv` | shippable | 94 | 23 | Y | name | n/a | — | 2026-08-06 | db | safe | — | — | — |
| `nho_doi_notification_roster.csv` | shippable | 190 | 13 | Y | nho_id | 0% | — | 2026-08-28 | db | safe | — | — | — |
| `nho_ito_spine_crosswalk.csv` | internal-by-decision | 269 | 9 | — | — | 100% | — | 2026-08-28 | — | — | 61_add_nho_intertribal | 163_promote_nho_univer | — |
| `nho_ownership_changes.csv` | shippable | 9 | 20 | Y | event_id | 100% | 2026 | 2026-08-28 | db | safe | — | — | — |
| `nho_parents.csv` | internal-by-decision | 21 | 4 | — | — | n/a | — | 2026-08-05 | — | — | — | — | — |
| `nho_register.csv` | shippable | 218 | 19 | Y | proposed_id | n/a | 2008 | 2026-08-05 | db | safe | — | — | — |
| `nho_verified_entities.csv` | shippable | 36 | 14 | Y | uei | 0% | — | 2026-08-28 | notes | safe | — | — | — |
| `tcu_cdfi_added.csv` | shippable | 130 | 28 | Y | tribe_id | 100% | — | 2026-08-28 | db | safe | — | — | — |
| `tcu_cdfi_ownership_evidence.csv` | shippable | 130 | 6 | **DEFECT** | — | n/a | — | 2026-08-06 | — | **row-only** | — | — | 4 dup rows |
| `tcu_roster.csv` | shippable | 37 | 12 | Y | name | n/a | 2017 | 2026-08-06 | — | safe | — | — | — |
| `visitor_access_events.csv` | shippable | 20 | 38 | Y | visitor_access_event_id | 0% | 2016 | 2026-08-28 | db | safe | — | — | — |
| `visitor_record_foia_requests.csv` | shippable | 667 | 21 | open | — | 2% | 2026 | 2026-08-28 | db | **row-only** | — | — | — |

### `_spine` — 14 table(s)

| table | status | rows | cols | grain | PK | keyed | latest yr | modified | ship | agg | built by | enriched by | flags |
|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|
| `cedar_event_id_registry.csv` | spine | 11 | 8 | — | — | n/a | 2026 | 2026-09-01 | — | — | — | — | — |
| `cedar_exclusion_rulings.csv` | spine | 123 | 12 | — | — | n/a | — | 2026-08-05 | — | — | — | — | — |
| `cedar_handle_history.csv` | spine | 1,536 | 7 | — | — | 100% | 2026 | 2026-08-29 | — | — | — | — | — |
| `cedar_identity_register.csv` | spine | 1,536 | 10 | — | — | 100% | — | 2026-08-29 | — | — | — | — | — |
| `cedar_observations.csv` | spine | 35,741 | 17 | — | — | n/a | — | 2026-08-29 | — | — | — | — | — |
| `cedar_resolution_policies.csv` | spine | 6 | 10 | — | — | n/a | — | 2026-08-29 | — | — | — | — | — |
| `cedar_resolution_rules.csv` | spine | 9 | 7 | — | — | n/a | — | 2026-08-29 | — | — | — | — | — |
| `cedar_source_record_links.csv` | spine | 585 | 19 | — | — | 100% | 2026 | 2026-08-29 | — | — | — | — | — |
| `cedar_source_records.csv` | spine | 575 | 17 | — | — | n/a | 2026 | 2026-08-29 | — | — | — | — | — |
| `cedar_source_registry.csv` | spine | 16 | 11 | — | — | n/a | — | 2026-08-29 | — | — | — | — | — |
| `cedar_temporal_facts.csv` | spine | 2,867 | 32 | — | — | n/a | 2026 | 2026-08-29 | — | — | — | — | — |
| `cedar_temporal_policy.csv` | spine | 10 | 6 | — | — | n/a | — | 2026-08-29 | — | — | — | — | — |
| `consortium_entities.csv` | spine | 1 | 12 | — | — | n/a | — | 2026-08-05 | — | — | — | — | — |
| `nonprofit_exclusion_rulings.csv` | spine | 4,656 | 20 | — | — | n/a | 2026 | 2026-08-05 | — | — | — | — | — |

## Cross-cutting reads

### Tables whose build or enrich chain contains a NEVER_RUN script

| table | NEVER_RUN script | what it destroys |
|---|---|---|
| `cedar_entity_spine.csv` | `01_build_entity_spine.py` | A full rebuild DROPS EVERY APPENDED ENTITY - the village corporations, NHOs, TCUs, CDFIs, BIE schools and UIOs added by scripts 52, 61, 73 and 75. Safe to IMPORT, never to RUN. Append-merge instead, re-reading the spine immediately before writing so a concurrent agent is not clobbered. |
| `cedar_identifier_ledger.csv` | `01_build_entity_spine.py` | A full rebuild DROPS EVERY APPENDED ENTITY - the village corporations, NHOs, TCUs, CDFIs, BIE schools and UIOs added by scripts 52, 61, 73 and 75. Safe to IMPORT, never to RUN. Append-merge instead, re-reading the spine immediately before writing so a concurrent agent is not clobbered. |
| `cedar_identifier_ledger_final.csv` | `09_import_rulings.py` | Rebuilds cedar_identifier_ledger_final.csv FROM the stale cedar_identifier_ledger_tiered.csv, which does not carry rows later scripts appended directly to _final. Running it on 2026-08-08 destroyed 1,327 ledger rows and 451 village-corporation links, 121 of them tier A - lost, not moved. Use 124_apply_rulings_in_place.py. |
| `cedar_identifier_ledger_tiered.csv` | `09_import_rulings.py` | Rebuilds cedar_identifier_ledger_final.csv FROM the stale cedar_identifier_ledger_tiered.csv, which does not carry rows later scripts appended directly to _final. Running it on 2026-08-08 destroyed 1,327 ledger rows and 451 village-corporation links, 121 of them tier A - lost, not moved. Use 124_apply_rulings_in_place.py. |
| `codebook_master.csv` | `41_build_codebooks.py` | Writes codebook_master.csv in 'w' mode from a hardcoded 19-group DATASETS dict. Running it today DELETES 21 OF THE 43 dataset blocks, including every block registered on 2026-08-26. The single most destructive command in the repo, and its name does not say so. Use cedar_codebook.write_fragment() or cedar_register_codebook.py. |

### Shippable tables a buyer may NOT total

25 table(s), from `data/clean/cedar_export_safety.csv`:

| table | collection | rows | why |
|---|---|---:|---|
| `cedar_identifier_graph_edges.csv` | _entity_layer | 46,051 | 2,451 LITERAL duplicate rows of 46,051. A graph with duplicate edges inflates `n_asserting_sources` and every degree count computed from it. |
| `cedar_ruling_ledger_consolidated.csv` | _entity_layer | 15,587 | 6,302 LITERAL duplicate rows of 15,587 - 40% of the file. A ruling ledger that records the same ruling twice cannot be counted, and 157 source files f |
| `cross_dataset_ruling_map.csv` | _entity_layer | 7,507 | 2,228 LITERAL duplicate rows of 7,507 - 30% of the file. |
| `foia_request_index.csv` | _entity_layer | 9,481 | no key was found at any arity up to 6 over 9,481 rows. `foia_request_id` REPEATS 381 times; adding `status` still leaves 66 collisions; adding source_ |
| `tcu_cdfi_ownership_evidence.csv` | _entity_layer | 130 | 4 LITERAL duplicate rows of 130. |
| `visitor_record_foia_requests.csv` | _entity_layer | 667 | the only unique key over 667 rows is `request_description_verbatim`, a free-text field. `foia_request_id` has 22 collisions. QUESTION: does one FOIA r |
| `contractor_ranking.csv` | contractors | 1,429 | the only unique keys over 1,429 rows require `firm_transaction_rows` - a MEASURE. A key that needs a count in it is not a grain. (owner_entity_id, ope |
| `fpds_uei_cage_map.csv` | contractors | 34,601 | a MAP that maps nothing uniquely: `uei` repeats 11,455 times over 29,981 rows and (uei, cage_code, source_file) still collides 4,680 times. The only u |
| `deals_2026_ytd_additions.csv` | deals | 0 | the file has ZERO rows (the build log records 1 row added, which is not what is on disk). QUESTION: was the YTD additions file consumed into deals_cla |
| `tribal_resolution_financings.csv` | deals | 1 | the file has ONE row. Uniqueness is vacuous. QUESTION: is a row one financing INSTRUMENT (instrument_number) or one tribal resolution? |
| `faads_transactions.csv` | funding | 60,661 | 1,001 LITERAL duplicate rows of 60,661. Same cause as faads_transactions_all_agencies.csv. |
| `faads_transactions_all_agencies.csv` | funding | 2,769,748 | 179,259 LITERAL duplicate rows of 2,769,748 (6.5%). DIAGNOSED 2026-08-29 and it is NOT a page fetched twice, which is what this entry used to say: 174 |
| `native_passthrough.csv` | funding | 1,262 | 114 LITERAL duplicate rows of 1,262. This table is derived from subawards.csv and inherits its duplication; the passthrough dollars are therefore over |
| `fac_audit_sefa_gaming_programs.csv` | gaming | 1 | the file has ONE row. Uniqueness is vacuous. QUESTION: is a row a (report, federal program) line off the SEFA, so that report_id repeats once a second |
| `gaming_projections.csv` | gaming | 116 | docs/GAMING_NEPA_PILOT_LOG.md states the grain as 'one row per project x metric x geography x period'. The data CONTRADICTS it: that key collides 8 ti |
| `congressional_correspondence_log.csv` | legislation | 0 | the file has ZERO rows. Every candidate key is vacuously unique, so the data cannot evidence a grain. QUESTION: is this table meant to ship empty, and |
| `native_bills_subject_sweep.csv` | legislation | 2,414 | 5 LITERAL duplicate rows of 2,414. |
| `admin_appeal_positions.csv` | lobbying | 1 | the file has ONE row. `matter_id` and `cedar_uid` are unique, and so is every other column - one row proves nothing. QUESTION: is a row a POSITION tak |
| `ferc_docket_filings.csv` | lobbying | 102,615 | 822 LITERAL duplicate rows of 102,615. docs/ANOMALY_REPORT.md already records 9,570 rows repeating (docket_number, accession_number); this measurement |
| `ferc_ex_parte_communications.csv` | lobbying | 713 | `ferc_ex_parte_id` has 56 collisions over 713 rows, and adding accession_number, docket_number or the FR document number removes none of them - the co |
| `hearing_bill_links.csv` | lobbying | 465 | 1 LITERAL duplicate row of 465: (bill_id, event_id) = (119-s-3878, 338549) appears twice. |
| `lobbying_registrant_native_ownership_evidence.csv` | lobbying | 27 | 4 LITERAL duplicate rows of 27 - 15% of a table the build log describes as 'one row per evidence route'. Four evidence routes are recorded twice. |
| `tribal_bond_issuances.csv` | natural-resources | 29 | `cusip` is BLANK on all 29 rows, so the natural key of a bond table is absent, and the only unique column is `notes`. QUESTION: can CUSIPs be backfill |
| `np_schedule_i_grants.csv` | nonprofits | 58,685 | 101 LITERAL duplicate rows of 58,685. (object_id, recipient_name_as_filed) collides 860 times - some legitimately (one filer can grant to the same rec |
| `subawards.csv` | subcontracting | 72,837 | 10,770 LITERAL duplicate rows of 72,837. (subaward_number, subaward_date) collides 27,470 times, so even the natural key of a subaward is not unique h |

### Tables with literal duplicate rows

13 table(s), measured by `512 probe` and recorded in `docs/schema/grain_evidence.json`. A literal duplicate is a byte-equal row, re-read and compared as a string after a hash collision — not a hash coincidence.

| table | rows | duplicate rows | % |
|---|---:|---:|---:|
| `faads_transactions_all_agencies.csv` | 2,769,748 | 179,259 | 6.5% |
| `subawards.csv` | 72,837 | 10,770 | 14.8% |
| `cedar_ruling_ledger_consolidated.csv` | 15,587 | 6,302 | 40.4% |
| `cedar_identifier_graph_edges.csv` | 46,051 | 2,451 | 5.3% |
| `cross_dataset_ruling_map.csv` | 7,507 | 2,228 | 29.7% |
| `faads_transactions.csv` | 60,661 | 1,001 | 1.7% |
| `ferc_docket_filings.csv` | 102,615 | 822 | 0.8% |
| `native_passthrough.csv` | 1,262 | 114 | 9.0% |
| `np_schedule_i_grants.csv` | 58,685 | 101 | 0.2% |
| `native_bills_subject_sweep.csv` | 2,414 | 5 | 0.2% |
| `lobbying_registrant_native_ownership_evidence.csv` | 27 | 4 | 14.8% |
| `tcu_cdfi_ownership_evidence.csv` | 130 | 4 | 3.1% |
| `hearing_bill_links.csv` | 465 | 1 | 0.2% |

### Grain evidence that no longer matches the file

`docs/schema/grain_evidence.json` records the row count each table had when `512 probe` measured its key. If the file has since changed size, **the recorded uniqueness proof is about a file that no longer exists** — and the contract still presents it as validated. This is the 'a check reading a key that does not exist passes for the same reason it is useless' failure, one level up: a check whose evidence has expired.

| table | rows when probed | rows now | delta | grain claim |
|---|---:|---:|---:|---|
| `fpds_uei_cage_map.csv` | 29,981 | 34,601 | +4,620 | unstated |
| `fr_nagpra_title_index.csv` | 6,606 | 6,644 | +38 | validated |
| `cedar_correction_register.csv` | 173 | 175 | +2 | validated |
| `entity_aliases.csv` | 6,297 | 6,296 | -1 | validated |

Re-probe with `py -3 code/512_build_dataset_contracts.py probe` (owned by the integrator this pass).

### Entity coverage — the tables holding the unkeyed mass

Ranked by UNKEYED rows, because that is the size of the lever, not the percentage. `candidates`/`rejected` tables are 0% by design: they hold things Cedar has NOT admitted to the universe.

| table | collection | rows | keyed | unkeyed |
|---|---|---:|---:|---:|
| `faads_transactions_all_agencies.csv` | funding | 2,769,748 | 0.0% | 2,769,748 |
| `prime_contracts.csv` | contractors | 1,217,768 | 73.0% | 328,810 |
| `prime_contracts_awards.csv` | contractors | 455,080 | 59.2% | 185,554 |
| `prime_contracts_published.csv` | contractors | 455,080 | 59.2% | 185,554 |
| `federal_funding_transactions.csv` | funding | 701,955 | 78.7% | 149,353 |
| `ferc_docket_filings.csv` | lobbying | 102,615 | 1.1% | 101,506 |
| `faads_transactions.csv` | funding | 60,661 | 0.0% | 60,661 |
| `np_schedule_i_grants.csv` | nonprofits | 58,685 | 4.2% | 56,243 |
| `subawards.csv` | subcontracting | 72,837 | 43.2% | 41,354 |
| `admin_appeal_parties.csv` | lobbying | 20,027 | 2.8% | 19,461 |
| `grantmaker_funding_flows.csv` | nonprofits | 18,656 | 0.0% | 18,656 |
| `cedar_identifier_ledger.csv` | _entity_layer | 19,232 | 28.8% | 13,687 |
| `cedar_identifier_ledger_tiered.csv` | _entity_layer | 19,232 | 33.3% | 12,834 |
| `cedar_identifier_ledger_final.csv` | _entity_layer | 20,577 | 39.3% | 12,489 |
| `ferc_docket_parties.csv` | lobbying | 11,563 | 1.9% | 11,346 |
| `np_orgs.csv` | nonprofits | 12,764 | 11.1% | 11,341 |
| `resource_revenue.csv` | natural-resources | 10,482 | 7.0% | 9,748 |
| `foia_request_index.csv` | _entity_layer | 9,481 | 3.6% | 9,137 |
| `ca_gaming_payments.csv` | gaming | 40,164 | 89.0% | 4,434 |
| `ferc_ex_parte_parties.csv` | lobbying | 4,246 | 0.2% | 4,237 |
| `nagpra_notice_entity_bridge.csv` | nagpra | 51,521 | 93.3% | 3,467 |
| `entity_candidates_new.csv` | _entity_layer | 2,874 | 0.0% | 2,874 |
| `digital_gaming_revenue.csv` | gaming | 10,661 | 73.3% | 2,849 |
| `federal_recognition_roster.csv` | _entity_layer | 17,058 | 89.3% | 1,820 |
| `lobbying_issue_families_filing.csv` | lobbying | 27,796 | 95.3% | 1,312 |

### Latest year present, by table count

Read off the table's **coverage** columns only. Provenance columns — `fetched_date`, `retrieved_date`, `classified_date` and the other 283 wall-clock stamps debt D4 counts — are refused **by name** before the file is opened. An earlier version of this scan accepted them and reported 255 of 303 tables as current through 2026; they are not, and `faads_transactions.csv` (FY2001–2007) was one of them.

| latest coverage year | tables |
|---:|---:|
| 2026 or later | 152 |
| 2025 | 25 |
| 2024 | 3 |
| 2023 | 4 |
| 2022 | 1 |
| 2021 | 4 |
| 2019 | 1 |
| 2018 | 1 |
| 2017 | 2 |
| 2016 | 2 |
| 2015 | 1 |
| 2008 | 1 |
| 2007 | 3 |
| 1973 | 1 |
| (no coverage column found) | 104 |

13 table(s) carry dates BEYOND 2026. That is not an error and it is not coverage: a compact expiry, a bond maturity and a NEPA projection are all legitimately in the future, and folding them into a coverage figure would overstate how current the data is. They are counted above at 2026 and named here:

| table | collection | furthest date |
|---|---|---:|
| `sam_prime_contracts_fy2000_2007.csv` | contractors | 2099 |
| `sam_prime_contracts_fy2000_2007_PUBLISHABLE.csv` | contractors | 2099 |
| `np_financials.csv` | nonprofits | 2075 |
| `compact_structured_terms.csv` | gaming | 2060 |
| `compacts.csv` | gaming | 2060 |
| `compact_required_reports.csv` | gaming | 2051 |
| `gaming_capacity_official.csv` | gaming | 2050 |
| `seminole_bond_disclosures.csv` | deals | 2033 |
| `fl_gaming_payments.csv` | gaming | 2031 |
| `earmarks.csv` | lobbying | 2027 |
| `nagpra_notices.csv` | nagpra | 2027 |
| `tribal_bond_issuances.csv` | natural-resources | 2027 |
| `tribal_tax_bases.csv` | natural-resources | 2027 |

**A year is not a staleness verdict.** `faads_*` ends in 2007 because that is the era it covers; `sam_prime_contracts_fy2000_2007` says so in its name. The contract has no `coverage_intent` field yet, so this table cannot separate *archive by design* from *nobody re-pulled it*, and it does not pretend to. See `docs/KNOWN_ISSUES.md`.

## Scripts

427 Python files under `code/` (recursive; `__pycache__` excluded). This is the same census `62_no_regression_check.py` reports as `code_scripts_total`.

A script is **live** if a dataset contract names it as a rebuilder or enricher, or `cedar_pipeline` declares an ordering for it. It is a **spent one-off** if its name says it repairs one named thing and a `.bak_<date>_pre<token>` receipt beside a table proves it ran. It is **history-only** if the only files mentioning it are `AGENTS.md` or `graveyard/`. It is **unreferenced** if nothing in the repository mentions it at all.

| class | scripts | what to do with them |
|---|---:|---|
| `live` | 103 | in a build path — do not move |
| `referenced` | 311 | named by a doc or another script, but in no contract and no ordering |
| `spent one-off` | 8 | ran, left a receipt; archive candidates, but the receipt is the audit trail |
| `history-only` | 0 | only `AGENTS.md` / `graveyard/` mention them |
| `unreferenced` | 1 | **nothing in the repository names them** |
| `NEVER_RUN` | 4 | guarded by `cedar_pipeline.guard()`; running one destroys work |

### Dead scripts — 502's verdict, not a second one

`code/502_archive_candidates.py` already answers this, on **seven** independent signals, and calls a script a candidate only when it fails all seven. Re-deriving a weaker version here would be the second registry this project has been burned by three times, so this section READS 502's report.

- report generated: **2026-09-01 20:17** (scripts scored: 411; 502 skips the 11 shared `cedar_*.py` libraries, which is why its census is lower than the 427 above)
- archive candidates: **1** — `ocr_stats.py` (ancsa_v2)

**Unreferenced is not dead, and 502 says so in its own header.** A script nothing names may still be the only writer of a shipped table — `70_key_unjoined_datasets.py` is exactly that, invisible to the io scan because its write helper is spelled `wr(`. Read the evidence column in `docs/ARCHIVE_CANDIDATES.md` before moving anything.

Scripts named by **no document and no other script** (generated catalogues excluded, because they name all of them). This is one of 502's seven signals, not a verdict:

| script | dir | lines | kind | writes | modified |
|---|---|---:|---|---|---|
| `dl_regional.py` | ancsa_portal | 41 | both | download_log.json | 2026-08-29 |

### Script numbers colliding inside one directory

43 number(s). Collisions are scoped per directory on purpose: `code/lobbying_pull/02_*.py` and `code/02_*.py` are unambiguous. Two files in the SAME directory sharing a number make "script 154" meaningless, which is why `62` ratchets this at MUST_NOT_RISE.

| dir | number | files |
|---|---:|---|
| code | 14 | `14_build_bills_votes.py`, `14_copy_votingpatterns_sources.py`, `14_pull_cosponsors.py` |
| code | 172 | `172_key_unkeyed_gaming_facility_hubs.py`, `172_probe_archive_stamp_per_year.py`, `172_write_individual_native_codebook_fragment.py` |
| code | 173 | `173_consolidate_rulings_ledger.py`, `173_fill_gaming_metrics_entity_for_newly_keyed_hubs.py`, `173_refresh_individual_native_results_section.py` |
| code | 174 | `174_apply_rulings_to_source_tables.py`, `174_backfill_digital_gaming_tiers.py`, `174_document_nigc_declination_codebook.py` |
| code | 30 | `30_funding_pre2008.py`, `30_probe_usaspending.py`, `30_wait_and_pull.py` |
| code | 40 | `40_build_prime_contracts.py`, `40_contracts_ledger_pass.py`, `40_pull_usaspending_subawards.py` |
| code | 73 | `73_add_tcu_and_cdfi.py`, `73_bills_votes_completion.py`, `73_faads_name_attribution.py` |
| code | 91 | `91_apply_existing_rulings.py`, `91_build_nigc_declinations.py`, `91_extract_compact_authorizations.py` |
| code | 92 | `92_build_gaming_capacity_official.py`, `92_find_identifier_conflicts.py`, `92_stage_nigc_missing_properties.py` |
| code | 94 | `94_extract_mi_mgcb_revshare.py`, `94_match_raw_subawards.py`, `94_rescan_universes.py` |
| code | 148 | `148_build_gaming_vendor_tribal_licenses.py`, `148_resolve_schedule_i_recipients.py` |
| code | 149 | `149_apply_resource_entity_links.py`, `149_build_tribal_resolution_financings.py` |
| code | 153 | `153_merge_base_ledgers_into_classified.py`, `153_merge_ordinance_ocr.py` |
| code | 154 | `154_build_fr_ex_parte_notices.py`, `154_extend_autoresolved_parties_additive.py` |
| code | 155 | `155_collect_deals_2026_08.py`, `155_pull_nigc_roster.py` |
| code | 156 | `156_refresh_deals_codebook_fragment.py`, `156_stage_form5500_gaming_employment.py` |
| code | 157 | `157_reconcile_nigc_roster.py`, `157_stage_osha_tribe_level_employment.py` |
| code | 158 | `158_extend_gaming_facilities.py`, `158_merge_staged_labor_employment.py` |
| code | 160 | `160_ship_gap_report.py`, `160_sync_published_gaming_view.py` |
| code | 163 | `163_load_sam_contract_awards.py`, `163_promote_nho_universe_in_place.py` |
| code | 164 | `164_link_facility_hub_sources.py`, `164_refresh_nho_review_queues.py` |
| code | 171 | `171_build_individual_native_verification.py`, `171_credit_gap_measure.py` |
| code | 175 | `175_restore_ferc_docket_table_after_rebuild_revert.py`, `175_sync_published_property_view_entities.py` |
| code | 20 | `20_build_subcontracts.py`, `20_fix_nonprofit_authority.py` |
| code | 24 | `24_funding_merge.py`, `24_generate_dataset_docs.py` |
| code | 33 | `33_apply_party_rulings.py`, `33_nonprofit_financials.py` |
| code | 35 | `35_coverage_audit.py`, `35_entity_harvest.py` |
| code | 36 | `36_build_nho_intertribal.py`, `36_cull_entity_candidates.py` |
| code | 37 | `37_contracts_gapfill.py`, `37_wait_then_pull.py` |
| code | 41 | `41_build_codebooks.py`, `41_match_subawards_to_ledger.py` |
| code | 45 | `45_contract_spiderweb_2026-08-06.py`, `45_promote_subawards.py` |
| code | 70 | `70_find_identifiers_for_unreconciled.py`, `70_key_unjoined_datasets.py` |
| code | 75 | `75_add_bie_schools_and_uios.py`, `75_philanthropy_schedule_i.py` |
| code | 76 | `76_build_recognition_history.py`, `76_philanthropy_classify.py` |
| code | 77 | `77_build_nagpra_dataset.py`, `77_philanthropy_review_queue.py` |
| code | 84 | `84_build_nigc_regions.py`, `84_resource_recipient_side.py` |
| code | 88 | `88_build_deals_taxonomy.py`, `88_gaming_property_federal_traces.py` |
| code | 89 | `89_build_master_review_queue.py`, `89_nigc_map_wayback_universe.py` |
| code | 90 | `90_build_review_page.py`, `90_fetch_nigc_declinations.py` |
| code | 93 | `93_build_leverage_cards.py`, `93_extract_az_gaming_status.py` |
| code | 95 | `95_parse_compact_terms.py`, `95_wayback_az_gaming_status.py` |
| code | 96 | `96_build_consultation_events.py`, `96_extract_sec_property_capacity.py` |
| code | 97 | `97_build_aliases_and_relationships.py`, `97_extract_az_status_archive.py` |

### NEVER_RUN

| script | number shared with | why |
|---|---|---|
| `01_build_entity_spine.py` | — | A full rebuild DROPS EVERY APPENDED ENTITY - the village corporations, NHOs, TCUs, CDFIs, BIE schools and UIOs added by scripts 52, 61, 73 and 75. Safe to IMPORT, never to RUN. Append-merge instead, re-reading the spine immediately before writing so a concurrent agent is not clobbered. |
| `09_import_rulings.py` | — | Rebuilds cedar_identifier_ledger_final.csv FROM the stale cedar_identifier_ledger_tiered.csv, which does not carry rows later scripts appended directly to _final. Running it on 2026-08-08 destroyed 1,327 ledger rows and 451 village-corporation links, 121 of them tier A - lost, not moved. Use 124_apply_rulings_in_place.py. |
| `41_build_codebooks.py` | **`41_match_subawards_to_ledger.py`** | Writes codebook_master.csv in 'w' mode from a hardcoded 19-group DATASETS dict. Running it today DELETES 21 OF THE 43 dataset blocks, including every block registered on 2026-08-26. The single most destructive command in the repo, and its name does not say so. Use cedar_codebook.write_fragment() or cedar_register_codebook.py. |
| `88_build_deals_taxonomy.py` | **`88_gaming_property_federal_traces.py`** | Rebuilds the deals taxonomy. Its glob read deals_*_additions.csv and never saw the 131 rows in the two root ledgers - the miscount that propagated as '790 deals' for three weeks. The glob was repaired at source, but a full taxonomy rebuild still discards the party rulings 33/53/57/154 wrote in place. |

**2 of the 4 guarded scripts share their number with a live sibling.** `guard()` keys on the FILENAME, so the guard itself is safe — but a human or an agent citing "script 41" or "script 88", or typing `code/88_*.py`, is naming two files, one of which destroys work. This is the sharpest instance of the 43 number collisions above and the reason `62` ratchets them.

### Spent one-off fixers

8 script(s) whose name says they repair one named thing and which left a `.bak_*_pre*` receipt beside a table. They are archive candidates, **but the receipt beside the data is what makes the correction auditable**, and `columns_lost_vs_backup` reads those same backups — so archiving the script must not remove the backup.

| script | writes | modified |
|---|---|---|
| `126_apply_deal_party_attribution.py` | deals_classified.csv | 2026-08-29 |
| `192_apply_ancsa_resolutions_in_place.py` | ANCSA_ATTRIBUTION_CHANGES.json | 2026-08-26 |
| `251_apply_np_ein_exclusions_to_np_orgs.py` | np_orgs.csv, renamed .part -> np_orgs.csv | 2026-08-29 |
| `263_register_attribution_repair_fragment.py` | — | 2026-08-29 |
| `327_migrate_class7_keys_to_digests.py` | class7_key_migration_map.json | 2026-08-29 |
| `34_apply_nonprofit_rulings.py` | np_orgs.csv | 2026-08-29 |
| `54_reconcile_deals_duplicates.py` | deals_duplicate_candidates.csv, deals_withdrawn_duplicates.csv | 2026-08-29 |
| `72_fix_brand_and_government_misattribution.py` | brand_family_registry.csv, brand_government_corrections.csv | 2026-08-29 |

---

*Open defects are not listed here. They are in `docs/KNOWN_ISSUES.md`, ranked, deduplicated, and each one naming the dataset it blocks.*
