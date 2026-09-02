# Event IDs — the *thing*, alongside the *who*

*Generated 2026-09-01 by `code/525_event_ids.py`. `cedar_uid` says WHO (dataset 13, the hub). This says WHAT HAPPENED, and keeps the two namespaces from colliding.*

**A natural key beats a surrogate every time.** Where the source already assigns a stable id, that IS the event id and we mint nothing — a surrogate beside a good natural key is two ids for one thing.

| dataset | event | prefix | kind | key |
|---|---|---|---|---|
| deals | a transaction in Indian Country | `DEAL` | **existing** | `Deal_ID` |
| natural-resources | a resource revenue payment | `RRE` | **existing** | `resource_revenue_event_id` |
| natural-resources | a lease / asset record | `RAS` | **existing** | `resource_asset_id` |
| gaming | a gaming land / ordinance decision | `GLD` | **existing** | `decision_id` |
| contractors | a prime contract transaction | `FPDSTX` | **natural** | `contract_transaction_unique_key` |
| funding | an assistance transaction | `ASSTTX` | **natural** | `assistance_transaction_unique_key` |
| funding | obligations per entity-year | `—` | **panel** | `tribe_id+fiscal_year` |
| lobbying | an LDA filing | `LDAFIL` | **natural** | `filing_uuid` |
| federal-register | a Federal Register document | `FRDOC` | **natural** | `document_number` |
| nagpra | a NAGPRA notice | `FRDOC` | **natural** | `document_number` |
| subcontracting | a subaward | `SUBAW` | **MISSING** | `` |

## Why some tables get no event id

A **panel** (a measure per entity × period) has the dimensions as its key. Minting a surrogate would let a buyer believe two rows are different events when they are one measure — the trap the grain sweep found in `contractor_ranking.csv`, whose only unique keys required a *measure*.

## Event tables with no registered id yet

| collection | table | current PK |
|---|---|---|
| funding | `faads_entity_attribution.csv` | `faads_row_id` |
| funding | `native_passthrough_pairs.csv` | `from_tribe_id+to_tribe_id` |
| federal-register | `consultation_events.csv` | `consultation_event_id+participant_name_as_published` |
| federal-register | `fr_consultation_by_agency.csv` | `normalized_department` |
| federal-register | `fr_consultation_notices.csv` | `document_number` |
| federal-register | `fr_consultation_referenced.csv` | `document_number` |
| federal-register | `fr_ex_parte_notices.csv` | `fr_ex_parte_notice_id` |
| federal-register | `fr_ex_parte_parties.csv` | `fr_ex_parte_party_id` |
| federal-register | `section_106_consultation_events.csv` | `consultation_event_id` |
| deals | `deals_2000_2019_additions.csv` | `Deal_ID` |
| deals | `deals_anc_reports_additions.csv` | `Deal_ID` |
| deals | `deals_ancsa_portal_additions.csv` | `Deal_ID` |
| deals | `deals_ancsa_portal_v2_additions.csv` | `Deal_ID` |
| deals | `deals_federal_awards_additions.csv` | `Deal_ID` |
| deals | `deals_historical_additions.csv` | `Deal_ID` |
| deals | `deals_sec_2010_2017_additions.csv` | `Deal_ID` |
| deals | `deals_source_index.csv` | `native_party` |
| deals | `deals_tribal_debt_additions.csv` | `Deal_ID` |
| deals | `ownership_events.csv` | `event_id` |
| nagpra | `fr_nagpra_title_index.csv` | `document_number` |
| nagpra | `nagpra_notice_entity_bridge.csv` | `document_number+relationship+party_name_verbatim` |
| lobbying | `admin_appeal_decisions.csv` | `decision_id` |
| lobbying | `admin_appeal_parties.csv` | `party_id` |
| lobbying | `advocacy_passthrough.csv` | `passthrough_id` |
| lobbying | `advocacy_passthrough_2026-08-07.csv` | `passthrough_id` |
| lobbying | `ferc_ex_parte_parties.csv` | `ferc_ex_parte_party_id+table_row_quote` |
| lobbying | `fr_ex_parte_notices.csv` | `fr_ex_parte_notice_id` |
| lobbying | `fr_ex_parte_parties.csv` | `fr_ex_parte_party_id` |
| lobbying | `lobbying_disclosure_verbosity_year.csv` | `filing_year` |
| lobbying | `lobbying_issue_families_filing.csv` | `filing_uuid` |
| lobbying | `lobbying_issue_family_year.csv` | `issue_family+filing_year` |
| lobbying | `lobbying_target_entities.csv` | `government_entity_as_filed` |
| lobbying | `tribe_year_lobbying_panel.csv` | `entity_id+filing_year` |
| contractors | `fpds_uei_edges.csv` | `child_uei+parent_uei+edge_type` |
| contractors | `prime_contracts_archive_backfill.csv` | `contract_transaction_unique_key` |
| contractors | `prime_contracts_awards.csv` | `contract_number` |
| contractors | `prime_contracts_entity_year.csv` | `tribe_id+fiscal_year` |
| contractors | `prime_contracts_published.csv` | `contract_number` |
| contractors | `sam_prime_contracts_fy2000_2007.csv` | `sam_transaction_key` |
| contractors | `sam_prime_contracts_fy2000_2007_PUBLISHABLE.csv` | `sam_transaction_key` |
| subcontracting | `prime_sub_network.csv` | `prime_uei+sub_uei` |
| subcontracting | `subaward_entity_rollup.csv` | `tribe_id` |
| nonprofits | `grantmaker_funding_flows.csv` | `flow_id` |
| nonprofits | `np_financials.csv` | `ein+tax_period` |
| nonprofits | `np_grantee_financials.csv` | `ein+source_url` |
| gaming | `ca_gaming_payments.csv` | `payment_id` |
| gaming | `compact_events.csv` | `event_id` |
| gaming | `fl_gaming_payments.csv` | `payment_id` |
| gaming | `gaming_decision_compact_join.csv` | `decision_id` |
| gaming | `gaming_decision_events.csv` | `event_id` |
| gaming | `gaming_financing_events.csv` | `financing_event_id` |
| gaming | `gaming_manufacturer_facts.csv` | `fact_id` |
| gaming | `gaming_source_claims.csv` | `source_claim_id` |
| _entity_layer | `cedar_identifier_ledger_final.csv` | `identifier_type+identifier+tribe_id+attribution_method+evidence_url+verified_date` |
| _entity_layer | `federal_recognition_events.csv` | `entity_key+fr_document_number` |
| _entity_layer | `federal_recognition_roster.csv` | `fr_document_number+entry_raw` |
| _entity_layer | `nho_ownership_changes.csv` | `event_id` |
| _entity_layer | `visitor_access_events.csv` | `visitor_access_event_id` |