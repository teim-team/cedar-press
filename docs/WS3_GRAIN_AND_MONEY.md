# Workstream GRAIN-WS3 — grain evidence and the money rules

*Generated 2026-09-01 by `code/573_ws3_grain_and_money.py`. Every number is re-measured from the live files on every run; `verify` exits 1 when one of them stops being true.*

## Re-measured duplicate counts

`512.GRAIN_DEFECT` records that `prime_contracts.csv` was listed at 80,778 literal duplicate rows and re-measured to **zero** — the mapper had dropped the transaction identity. Every count this workstream was handed was re-measured and then asked the same second question.

| table | alleged | re-measured | duplicated FACTS | why |
|---|---:|---:|---:|---|
| `ferc_docket_filings.csv` | 822 | 822 | 822 | grain STATEABLE, key REFUSED. A row is one eLibrary document as filed into one docket/subdocket by one filer organisation as recorded. (docket_number, accession_number) collides 9, |
| `np_schedule_i_grants.csv` | 101 | 101 | **0** | NOT duplicates. Every group is inside one return that np_schedule_i_filers.csv holds exactly once, so the return was parsed once and the FILER listed the line twice. De-duplicating |
| `native_bills_subject_sweep.csv` | 5 | 5 | 5 | REAL duplicates, inherited. 73's sweep emits exactly one row per corpus row and the corpus repeats 595 bill_ids byte-identically. A bill is introduced once, so no dimension separat |
| `lobbying_registrant_native_ownership_evidence.csv` | 4 | 4 | **0** | NOT duplicates. Four independent sources asserting one UEI collapse to two B-tier and two C-tier rows that render byte-identical. De-duplicating deletes the corroboration. |
| `hearing_bill_links.csv` | 1 | 1 | 1 | REAL duplicate, and it is the SOURCE API. The Congress.gov committeeMeeting record for event 338549 lists 27 of its 64 relatedItems.bills entries twice, verbatim; one of the 27 is  |

## Declared in `512.GRAIN_WS3`

| table | primary key | rows | dup | blank-component rows |
|---|---|---:|---:|---:|
| `gaming_projections.csv` | `project_id+metric+geography+time_period+alternative+source_document+unit` | 116 | 0 | 4 |
| `tribal_bond_issuances.csv` | `issuer+instrument_type+source_url` | 29 | 0 | 0 |
| `ferc_ex_parte_communications.csv` | `ferc_ex_parte_id+filed_or_issued_by_as_recorded` | 713 | 0 | 44 |
| `admin_appeal_positions.csv` | `position_id` | 8 | 0 | 0 |

## C7 — what a buyer may and may not total

### `gaming`

- **`gaming_projections.csv` · `value`** — additive at (project, metric, geography, time period, NEPA alternative, source document, unit) - and ONLY within one unit and one alternative. **Never sum with:** ANY table of realised gaming revenue, employment or payments - nigc_regional_ggr.csv, ca_gaming_payments.csv, fl_gaming_payments.csv, state_gaming_observations.csv, digital_gaming_revenue.csv. A PROJECTION IS NOT A REALISED FIGURE. 114 of 116 rows carry observation_status = 'proposed': they are what a NEPA consultant expects a casino that may never be built to produce. Adding one to an actual is adding a forecast to a receipt. Two further traps INSIDE the table: alternatives are MUTUALLY EXCLUSIVE futures of one casino and summing across them adds a project to itself, and a study that states a RANGE is stored as two rows (low end / high end) whose sum is meaningless.
- **`fac_audit_sefa_gaming_programs.csv` · `amount_expended`** — additive at UNSAFE - the grain is (report, SEFA award line) and no key validates. **Never sum with:** any gaming revenue table, and any other federal award table. A federal award expenditure is NOT gaming revenue - the row's own measurement_type_note says so. It is also a FEDERAL AWARD, so it is the same dollar the funding dataset already carries. *(measured total $223,322)*

### `deals`

- **`deals_classified.csv` · `Announced_Value_USD`** — additive at one row per deal EVENT. **Never sum with:** any deals_*_additions.csv file - deals_2000_2019_additions.csv, deals_anc_reports_additions.csv, deals_ancsa_portal_additions.csv, deals_ancsa_portal_v2_additions.csv, deals_federal_awards_additions.csv, deals_historical_additions.csv, deals_sec_2010_2017_additions.csv, deals_tribal_debt_additions.csv. THE LARGEST DOUBLE-COUNTING PATH IN THESE SIX DATASETS. Every one of the 8 additions files is a STAGING SLICE that was already folded into deals_classified.csv: 790 of their rows carry a Deal_ID that deals_classified.csv already holds. Summing the additions alongside the classified table adds their whole value again. All nine tables are currently classified SAFE_TO_AGGREGATE, which is true of each ALONE and false of any two together. *(measured total $45,195,917,316; overlap $22,669,271,316)*
- **`deals_classified.csv` · `Announced_Value_USD`** — additive at one row per deal EVENT. **Never sum with:** federal_funding_transactions.csv / faads_transactions*.csv / prime_contracts.csv. 618 of 935 rows have a Value_Type that names a FEDERAL award ('Federal grant award', 'Federal competitive grant award', ...). Those are federal obligations Cedar already ships in the funding and contracting datasets. A deal announcement and the obligation behind it are one dollar. *(measured total $45,195,917,316; overlap $6,870,716,041)*
- **`tribal_resolution_financings.csv` · `principal_amount_text`** — additive at UNSAFE - free text, and no key validates. **Never sum with:** gaming_financing_events.csv, tribal_bond_issuances.csv, nigc_declination_letters.csv. A council resolution AUTHORISES; it does not close or fund. The build's own ladder is AUTHORIZED -> NIGC_REVIEWED -> EXECUTION_UNCONFIRMED -> EXECUTED_CONFIRMED, and the row carries the NIGC cross-reference precisely so an authorisation and a review of one transaction are not counted as two.

### `natural-resources`

- **`resource_revenue.csv` · `amount_usd`** — additive at one revenue EVENT; safe within one source_system. **Never sum with:** tribal_tax_bases.csv. Both tables observe the SAME North Dakota severance stream at two points on its way. resource_revenue carries 492 ND State Treasurer DISTRIBUTION rows; tribal_tax_bases carries 1640 ND rows of tax REMITTED, which is the pool the distribution is paid out of, split by the shares in nd_severance_allocation.csv. Adding them counts the tribe's share inside the remitted total and again as the distribution. Across eight source systems resource_revenue also mixes royalty, rent, direct pay and tax shares - a total over all of them is not 'resource revenue to Indian Country', it is four different measures added up. *(measured total $50,973,259,111; overlap $3,144,235,827)*
- **`tribal_tax_bases.csv` · `tax_remitted_usd`** — additive at one (tribe, tax type, period) observation. **Never sum with:** resource_revenue.csv (see above). tax_remitted_usd is the TOTAL remitted, not the tribal share. 1640 of 1712 rows are ND. `derived_taxable_base` is a derivation from a rate and must never be added to a remittance. *(measured total $8,652,041,939; overlap $8,467,030,616)*
- **`tribal_bond_issuances.csv` · `par_amount`** — additive at one debt INSTRUMENT of one issuer, as described in one document. **Never sum with:** itself across refinancings, and gaming_financing_events.csv / seminole_bond_disclosures.csv. par_amount is size AT ISSUE, NOT debt outstanding. Several rows say so in instrument_type ('amount outstanding at', 'proposed size at rating'), and a refinanced facility appears as two instruments, so a sum over an issuer is a sum over its borrowing history rather than its balance sheet. 11 of 29 rows are one issuer. *(measured total $6,712,500,000)*

### `nonprofits`

- **`np_schedule_i_grants.csv` · `cash_grant_usd`** — additive at one Schedule I Part II GRANT LINE (see the refusal: no key validates). **Never sum with:** np_schedule_i_filers.csv. THE SAME MONEY AT TWO GRAINS, and it reconciles to the dollar: the grant rows total $16,439,532,633 and np_schedule_i_filers.part2_cash_grant_total_usd totals $16,439,532,633. The filers table is the return-level roll-up of the very rows beside it. *(measured total $16,439,532,633; overlap $16,439,532,633)*
- **`np_schedule_i_grants.csv` · `cash_grant_usd`** — additive at one grant line. **Never sum with:** federal_funding_transactions.csv / faads_transactions*.csv / native_passthrough.csv. A Schedule I grant is money the FILER GRANTED OUT. Where the filer is a nonprofit that received a federal award and re-granted it, the federal dollar is in the funding dataset AND here. Cedar already has the shape for this: native_passthrough.csv models a pass-through as a DIRECTED EDGE between two resolved parties with an explicit `amount_countable` flag, so the pass-through can be seen without being added to the prime. np_schedule_i_grants carries no such flag, so the safe reading is: total it as GRANTS MADE BY NONPROFITS, never add it to federal obligations, and never call the sum 'money reaching Indian Country'. *(measured total $16,439,532,633)*
- **`grantmaker_funding_flows.csv` · `cash_grant_usd`** — additive at one grant line off a grantmaker's 990. **Never sum with:** grantmaker_funding_overlap.csv. MEASURED SAFE against np_schedule_i_grants.csv: 0 of 18656 flow rows share an object_id with a Schedule I grant row, so the two tables read DIFFERENT returns - flows are non-Native grantmakers granting to Native-serving recipients (Charles Koch Foundation and the like), Schedule I is the Native-linked filer side. They may be added. grantmaker_funding_overlap.csv is a roll-up OF flows and may not. *(measured total $4,358,173,488; overlap $280,782,942)*
- **`np_financials.csv` · `total_revenue`** — additive at one (organisation, tax year) return. **Never sum with:** np_org_scale.csv, np_grantee_financials.csv. Three tables carry total_revenue for overlapping organisation universes. A revenue figure is a STOCK of one filer-year; summing it across two tables that both hold that filer-year doubles it, and summing revenue across a grantor and its grantee counts the grant twice by construction. *(measured total $20,331,102,383)*

### `legislation`

- **`native_issue_litigation_positions.csv` · `grant_cash_usd`** — additive at one litigation POSITION - it is NOT a money table. **Never sum with:** grantmaker_funding_flows.csv, np_schedule_i_grants.csv. grant_cash_usd is carried on a position row to say what the position-taker was FUNDED WITH, joined in from the grant tables. Totalling it sums the same grant once per position the grantee took. *(measured total $14,970,998)*

### `lobbying`

- **`lobbying_registrants.csv` · `spend_reported_usd`** — additive at one registrant. **Never sum with:** lobbying_registrant_client_relationships.csv. The same money at two grains, to the dollar: $645,052,869 on 653 registrants and $645,052,869 on 1309 registrant-client pairs. *(measured total $645,052,869; overlap $645,052,869)*
- **`native_entity_lobbying_disclosures.csv` · `spend_usd`** — additive at one LDA filing. **Never sum with:** income_usd and expenses_usd ON THE SAME ROW, and tribe_year_lobbying_panel.csv. spend_usd IS income_usd + expenses_usd - $694,102,069 + $31,121,656 = $725,223,725. A filer reports INCOME when it is a firm lobbying for a client and EXPENSES when it lobbies for itself; the two are never both true of one filing, so spend_usd is the one column to total and adding any two of the three inflates the answer. *(measured total $725,223,725)*
- **`tribe_year_lobbying_panel.csv` · `total_lobbying_spend_usd`** — additive at one (entity, year). **Never sum with:** native_entity_lobbying_disclosures.csv, and its own two component columns. The panel is the entity-year ROLL-UP of the disclosures: $680,041,391 = $672,829,735 client income + $7,211,656 registrant expenses. Add the panel to the filings and every dollar is counted twice; add the components to the total and it is counted twice inside one row. *(measured total $680,041,391)*
- **`advocacy_passthrough.csv` · `grant_amount_usd`** — additive at one passthrough grant. **Never sum with:** advocacy_passthrough_2026-08-07.csv. THE SAME FILE TWICE. Both ship, both hold 1620 rows and both total $193,592,975: the dated one is a snapshot of the live one and a buyer who loads the directory loads the money twice. *(measured total $193,592,975; overlap $193,592,975)*
