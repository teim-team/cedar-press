# Export safety — which tables a buyer may total

*Generated 2026-08-29 by `code/517_export_safety.py`. Derived from the grain contracts and the temporal layer; this file measures nothing new, it REFUSES on what they already know.*

**The rule that matters most:** unknown ownership may ship as unknown. **Contradicted ownership may never ship as a definite historical owner.**

- **SAFE_TO_AGGREGATE**: 189
- **ROW_LEVEL_ONLY**: 25 (of which **11 carry money columns** — the unsafe analysis is also the most likely one)

## Ownership as-of status

14823 (uei, fiscal-year) cells resolved; **3840 are NOT definite** and must not be exported as a historical owner:

- `RESOLVED` — 10,983
- `UNKNOWN_OUTSIDE_EVIDENCE` — 2,913
- `AMBIGUOUS_OVERLAP` — 502
- `NO_FACT_ON_SUBJECT` — 416
- `NO_COVERING_FACT` — 8
- `AMBIGUOUS_GRANULARITY` — 1

## Tables a buyer must NOT aggregate

| table | collection | money columns | why |
|---|---|---|---|
| `admin_appeal_positions.csv` | lobbying | — | grain UNSTATED; no validated primary key |
| `cedar_identifier_graph_edges.csv` | _entity_layer | — | grain UNSTATED; no validated primary key; 2451 literal duplicate rows |
| `cedar_ruling_ledger_consolidated.csv` | _entity_layer | — | grain UNSTATED; no validated primary key; 6302 literal duplicate rows |
| `congressional_correspondence_log.csv` | legislation | — | grain UNSTATED; no validated primary key |
| `contractor_ranking.csv` | contractors | owner_obligations_usd|owner_native_setaside_usd|owner_8a_usd|owner_native_specific_setaside_usd|owner_no_setaside_usd_award_level|firm_obligations_usd | grain UNSTATED; no validated primary key |
| `cross_dataset_ruling_map.csv` | _entity_layer | — | grain UNSTATED; no validated primary key; 2228 literal duplicate rows |
| `deals_2026_ytd_additions.csv` | deals | Announced_Value_USD|Value_Type|Project_Total_Value_USD | grain UNSTATED; no validated primary key |
| `faads_transactions.csv` | funding | obligated_usd | grain UNSTATED; no validated primary key; 1001 literal duplicate rows |
| `faads_transactions_all_agencies.csv` | funding | obligated_usd | grain UNSTATED; no validated primary key; 179259 literal duplicate rows |
| `fac_audit_sefa_gaming_programs.csv` | gaming | amount_expended | grain UNSTATED; no validated primary key |
| `ferc_docket_filings.csv` | lobbying | — | grain UNSTATED; no validated primary key; 822 literal duplicate rows |
| `ferc_ex_parte_communications.csv` | lobbying | — | grain UNSTATED; no validated primary key |
| `foia_request_index.csv` | _entity_layer | — | grain UNSTATED; no validated primary key |
| `fpds_uei_cage_map.csv` | contractors | — | grain UNSTATED; no validated primary key |
| `gaming_projections.csv` | gaming | value | grain UNSTATED; no validated primary key |
| `hearing_bill_links.csv` | lobbying | — | grain UNSTATED; no validated primary key; 1 literal duplicate rows |
| `lobbying_registrant_native_ownership_evidence.csv` | lobbying | — | grain UNSTATED; no validated primary key; 4 literal duplicate rows |
| `native_bills_subject_sweep.csv` | legislation | — | grain UNSTATED; no validated primary key; 5 literal duplicate rows |
| `native_passthrough.csv` | funding | amount_usd|amount_countable | grain UNSTATED; no validated primary key; 114 literal duplicate rows |
| `np_schedule_i_grants.csv` | nonprofits | cash_grant_usd|noncash_assistance_usd | grain UNSTATED; no validated primary key; 101 literal duplicate rows |
| `subawards.csv` | subcontracting | subaward_amount|prime_award_amount|subaward_amount_real2025 | grain UNSTATED; no validated primary key; 10770 literal duplicate rows |
| `tcu_cdfi_ownership_evidence.csv` | _entity_layer | — | grain UNSTATED; no validated primary key; 4 literal duplicate rows |
| `tribal_bond_issuances.csv` | natural-resources | par_amount | grain UNSTATED; no validated primary key |
| `tribal_resolution_financings.csv` | deals | principal_amount_text|pledged_revenues_text | grain UNSTATED; no validated primary key |
| `visitor_record_foia_requests.csv` | _entity_layer | — | grain UNSTATED; no validated primary key |