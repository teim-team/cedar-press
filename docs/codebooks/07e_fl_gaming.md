# Codebook — Fl Gaming

*9,781 rows across 2 file(s). Generated 2026-08-07.*

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `payment_id` | text |  | 100% | Cedar-internal row identifier for one published Florida figure: one metric, one period, one conference document. |
| `state` | text | 2-letter code | 100% | US state or territory. |
| `fund` | text |  | 100% | The money stream. Florida has exactly one: the revenue share the Seminole Tribe of Florida pays the State under the Tribal-State Gaming Compact. Blank on rows that state the absence of a series rather than a payment. |
| `direction` | text |  | 100% | `paid_in` where the Tribe pays the State. Florida runs no distribution back to tribes, so there is no `paid_out` side. |
| `recipient_type` | text | code | 100% | Recipient organisation type code. |
| `tribe_id` | text | code | 100% | Cedar Press permanent identifier for the Native entity. Stable across releases; use this to join datasets. |
| `tribe_canonical_name` | text | text | 100% | Name. |
| `party_name_as_published` | text |  | 100% | The payer exactly as the source names it. Always the Seminole Tribe of Florida, which is a different federally recognised tribe from the Seminole Nation of Oklahoma. |
| `facility_id` | text | code | 0% | Identifier. |
| `facility_name` | text | text | 0% | Name. |
| `metric` | text | text | 100% | Name of the reported measure. |
| `value` | integer | see `unit` | 100% | Value of the reported measure. |
| `unit` | text | text | 100% | Unit of the reported measure. |
| `value_as_published` | integer | 0 to 8.17307e+08 | 100% | The figure exactly as the document prints it, before any unit conversion. Read it with `published_unit`: a source that prints millions is recorded in millions here and in dollars in `value`. |
| `published_unit` | text |  | 100% | One of: `USD millions`, `USD`, `percent` |
| `period_start` | text | YYYY-MM-DD | 100% | First day of the period the amount covers. |
| `period_end` | text | YYYY-MM-DD | 100% | Last day of the period the amount covers. |
| `period_basis` *(internal)* | text |  | 100% | What span the amount covers: `quarter`, `fiscal_year_to_date`, or `fiscal_year`. A fiscal-year-to-date figure accumulates within the year and consecutive quarters must be differenced, not summed. |
| `period_label` | text | text | 100% | The period exactly as the document labels it, e.g. `FY 2013/14`, `2024-25 cycle`, `Mar-14`. |
| `conference_date` | text | YYYY-MM-DD | 97% | Date the Revenue Estimating Conference met and adopted the document. It is what orders restatements of the same period, and what separates a closed period's actual from a forecast. |
| `measurement_type` | text | category | 100% | What kind of quantity the value is. Caps are AUTHORIZED_MAXIMUM: the maximum a compact permits, never the number in operation. |
| `is_forecast` | text |  | 100% | `yes` where the figure covers a period that had not closed when the publishing body met, and is therefore that body's forecast. |
| `revenue_evidence_class` | text | category | 100% | The level and strength a revenue figure derived from this term would carry. |
| `governing_compact_id` | text | code | 100% | The compact in force over the row's period, keyed to compacts.csv. |
| `compact_rate_schedule` | text |  | 100% | The governing compact's revenue-share schedule in its own terms. Florida's is graduated by band and by game category, not flat. |
| `compact_rate_min_pct` | integer | percent | 99% | Lowest marginal rate anywhere in the governing schedule. |
| `compact_rate_max_pct` | integer | percent | 99% | Highest marginal rate anywhere in the governing schedule. |
| `compact_revenue_concept` | text |  | 99% | The compact's own words for what the rate applies to (`Net Win`, `Gross Gaming Revenue`), copied verbatim and never generalised. |
| `compact_base_scope` | text |  | 99% | The scope the compact binds the revenue base to. `tribe` throughout Florida: the base is Net Win across all Facilities plus, from 2021, a statewide mobile sports betting product. |
| `compact_guaranteed_minimum` | text |  | 99% | The compact's guaranteed minimum payment terms. A guaranteed minimum is a floor on the PAYMENT and says nothing about revenue whenever it binds. |
| `payment_invertible` | text |  | 100% | Whether a revenue figure can be recovered from this row by dividing the payment by the compact rate. It is `no` on every Florida payment row, and the reason is in `bound_basis`. |
| `derived_revenue_bound_value` | empty | USD | 0% | A revenue figure bounded by arithmetic on a published payment and a published rate, where that arithmetic is valid. Empty throughout the Florida layer. |
| `derived_bound_direction` | empty |  | 0% | Which side of the revenue figure the bound constrains, upper or lower. Empty where no bound is published. |
| `derived_revenue_scope` | empty |  | 0% | The scope any derivation on this row would reach. Empty throughout, because no derivation is published from a Florida payment. |
| `bound_basis` | text |  | 100% | One of: `A Revenue Estimating Conference forecast. EDR estimates Net Win in order to forecast the payment; for a period that had not closed there is no reported figure behind it.`, `Refused, not caveated. The published figure is CASH RECEIVED in a state fiscal year and the compact's rate applies to a Revenue Sharing Cycle's Net Win. EDR states the mismatch itself - 'Revenues collected are lagged by one month' and 'True-up payments generated from activity in any Fiscal Year are received in the following Fiscal Year' - and the arithmetic confirms it: FY 2013/14 receipts of $237,312,301 give an apparent ceiling of $1.978bn on Net Win, while EDR's own Net Win for that year is $2.098bn. Two further blockers survive a matched period: the payment is max(percentage amount, guaranteed minimum) and a binding minimum carries no information about Net Win; and under the 2021 Compact one total is the sum of four category schedules and does not determine the four bases.`, `A destination split of a payment recorded in full elsewhere in this file; deriving on it would double count. Refused, not caveated. The published figure is CASH RECEIVED in a state fiscal year and the compact's rate applies to a Revenue Sharing Cycle's Net Win. EDR states the mismatch itself - 'Revenues collected are lagged by one month' and 'True-up payments generated from activity in any Fiscal Year are received in the following Fiscal Year' - and the arithmetic confirms it: FY 2013/14 receipts of $237,312,301 give an apparent ceiling of $1.978bn on Net Win, while EDR's own Net Win for that year is $2.098bn. Two further blockers survive a matched period: the payment is max(percentage amount, guaranteed minimum) and a binding minimum carries no information about Net Win; and under the 2021 Compact one total is the sum of four category schedules and does not determine the four bases.`, `Stated by the State, not derived here. EDR's December 2015 conference names its source: 'the actual Net Win for Fiscal Year 2014-15, and other information from the most recent quarterly financial reports available from the Tribe'. The figure is Net Win as the compact defines it, for the whole tribe. It is not a property figure and cannot be split to one.`, `The amount owed for the cycle under the schedule, which is not the amount received in any one state fiscal year.` |
| `compact_term_source_url` | text |  | 99% | Live URL of the compact instrument the rate was read from. |
| `compact_term_source_quote` | text |  | 99% | Verbatim clause from the governing compact stating the rate and the base it applies to. It is what licenses - or refuses - the derivation on the row, so it travels with the number. |
| `confidence_tier` | text | category | 100% | Publication tier. A = verified, publishable. B = provisional, withheld from published extracts. C = unattributed. X = ruled out. |
| `entity_match_method` *(internal)* | text |  | 100% | One of: `alias`, `carried_from_gaming_facilities` |
| `entity_tier` | text |  | 100% | One of: `B`, `A` |
| `exclusion_flag` | text | 0/1 | 95% | Indicator variable. |
| `exclusion_reason` | text | text | 95% | Why a record was ruled outside the Native universe. |
| `source_authority` *(internal)* | text |  | 100% | One of: `Florida Legislature, Office of Economic and Demographic Research`, `Florida Gaming Control Commission`, `Moody's Investors Service`, `Federal Audit Clearinghouse (GSA)`, `U.S. Securities and Exchange Commission, EDGAR`, `Municipal Securities Rulemaking Board, EMMA` |
| `source_document_type` | text |  | 100% | One of: `edr_revenue_estimating_conference`, `fgcc_annual_report`, `rating_agency_press_release`, `fac_dissemination_general_record`, `sec_registered_fund_schedule_of_investments`, `robots_exclusion_file` |
| `source_url` | text | URL | 100% | Link to the record's published source. |
| `source_page` | integer | integer | 100% | Page of the source document. |
| `source_quote` | text | text | 100% | The document's own words supporting the recorded term. |
| `source_link_text` | text |  | 100% | The label the publishing agency gives the document on its own index page, e.g. `January 2026` for a conference document. |
| `zone_header` | text |  | 100% | The caption printed above the table the row came from, verbatim. |
| `foot_status` | text |  | 100% | Whether the extracted figures reconcile to the document's own printed total, or to the compact schedule the document prints beneath the table. Only reconciling zones are published. |
| `foot_detail` | text |  | 100% | Per-column comparison of the extracted sum against the printed total, so the reconciliation can be checked without the PDF. |
| `document_status` | text |  | 8% | `latest_statement_for_period` where no later conference has restated the same metric and period. Every other statement of that period stays readable and carries an exclusion flag instead. |
| `fetched_date` | text | YYYY-MM-DD | 100% | Date. |
| `built_date` | text | YYYY-MM-DD | 100% | Date. |
| `built_by_script` | text |  | 100% | One of: `code/105_build_florida_gaming.py` |
| `disclosure_id` | text | code | 100% | Identifier. |
| `obligor_name_as_published` | text |  | 100% | The party on whose behalf the debt was issued, or the auditee, exactly as the source names it. |
| `conduit_issuer_as_published` | text |  | 12% | The governmental issuer that sold the bonds on the obligor's behalf. A conduit issuer lends the proceeds on and is not the credit. |
| `disclosure_class` | text |  | 100% | What kind of disclosure the row is: a bond named in a registered fund's holdings, a rating action, a Single Audit reporting package, or a repository whose documents could not be retrieved. |
| `security_description` | text | text | 56% | The security exactly as the filing describes it: conduit issuer, series, coupon, purpose and maturity, in the filer's own words. |
| `series` | text |  | 12% | One of: `2001`, `2003A` |
| `coupon_pct` | numeric | percent | 12% | Stated interest rate on the security. |
| `maturity_date` | text | YYYY-MM-DD | 56% | Date. |
| `amount_usd` | integer | USD, nominal | 84% | Amount. |
| `amount_concept` | text |  | 84% | What the amount MEANS in its own source's terms. Federal awards expended in a Single Audit is not revenue and not gaming; par amount in a rating action is face value, not proceeds. |
| `rating` | text |  | 20% | One of: `Ba1`, `Baa3` |
| `rating_agency` | text |  | 44% | One of: `Moody's Investors Service` |
| `filer_name` | text | text | 100% | Name. |
| `filer_cik` | empty | code | 0% | SEC Central Index Key of the entity that filed the document, where the source states one. |
| `filing_form` | text |  | 100% | One of: `rating action`, `Single Audit (2 CFR 200 Subpart F)`, `N-CSR`, `EMMA official statements and continuing disclosures` |
| `filing_date` | text | YYYY-MM-DD | 12% | Date. |
| `fiscal_year` | integer | YYYY | 40% | The audit year of a Single Audit filing. The Seminole Tribe of Florida's fiscal year ends 30 September. |
| `availability_status` | text |  | 100% | Whether the document behind the row was retrieved, withheld by rule, or not retrievable by an automated client. |
| `availability_basis` *(internal)* | text |  | 100% | Why the document is or is not available, quoting the rule or the repository's own restriction. |
| `carries_gaming_revenue` | text |  | 100% | Whether the disclosure contains a gaming revenue figure. `unknown` where the document itself could not be read. |

## Value sets

- **`recipient_type`** — `state_of_florida`, `facility`
- **`tribe_id`** — `TRBF-SMNLFL-00`, `TRBF-MCSKEE-00`
- **`tribe_canonical_name`** — `Seminole`, `Miccosukee`
- **`party_name_as_published`** — `Seminole Tribe of Florida`, `Miccosukee Tribe of Indians of Florida`
- **`facility_id`** — `CCP-823500`, `VP-0341`, `VP-0342`, `CCP-19700`, `VP-0008`, `CCP-124600`, `CCP-512300`, `CCP-51500`, `CCP-335400`, `VP-0340`, `CCP-70500`, `CCP-51600`
- **`facility_name`** — `Big Cypress Casino`, `Big Cypress Casino - small bingo`, `Miccosukee Resort & Gaming`, `Miccosukee Resort & Gaming Center`, `Seminole Brighton Casino`, `Seminole Casino Brighton`, `Seminole Casino Coconut Creek`, `Seminole Casino Hotel Immokalee`, `Seminole Classic Casino`, `Seminole Classic Casino Hollywood`, `Seminole Hard Rock Hotel & Casino Hollywood`, `Seminole Hard Rock Hotel & Casino Tampa`
- **`unit`** — `USD`, `percent`
- **`published_unit`** — `USD millions`, `USD`, `percent`
- **`measurement_type`** — `PROJECTED`, `REGULATORY_REPORTED_COUNT`
- **`is_forecast`** — `yes`, `no`
- **`revenue_evidence_class`** — `NO_REVENUE_OBSERVATION`, `TRIBE_LEVEL_REVENUE`
- **`governing_compact_id`** — `CMP-FL-seminole-tribe-of-florida-20100706`, `CMP-FL-seminole-tribe-of-florida-20210811`, `CMP-FL-seminole-tribe-of-florida-20080107`
- **`compact_rate_schedule`** — `12% / 15% / 17.5% / 20% / 22.5% / 25% of Net Win from Covered Games, by band`, `Slot Machines 12%-25%; Table Games 15%-25%; Sports Betting 13.75%; Sports Betting via a Qualified Pari-mutuel Permitholder brand 10% - all of Net Win, by band`, `stated guaranteed dollar payments, no percentage of any revenue base`
- **`compact_revenue_concept`** — `Net Win from Covered Games`, `Net Win`
- **`compact_guaranteed_minimum`** — `Guaranteed Minimum Revenue Sharing Cycle Payment for the first three Revenue Sharing Cycles`, `$1.5bn by the end of the 3rd cycle, $2.5bn by the end of the 5th cycle, and not less than $400m for any cycle in the first five years`
- **`payment_invertible`** — `not_a_payment_a_state_forecast`, `no_period_mismatch_and_guaranteed_minimum`, `component_of_a_payment_not_the_payment`, `not_applicable_this_row_is_a_revenue_figure`, `obligation_for_the_cycle_not_cash_received`
- **`bound_basis`** — `A Revenue Estimating Conference forecast. EDR estimates Net Win in order to forecast the payment; for a period that had not closed there is no reported figure behind it.`, `Refused, not caveated. The published figure is CASH RECEIVED in a state fiscal year and the compact's rate applies to a Revenue Sharing Cycle's Net Win. EDR states the mismatch itself - 'Revenues collected are lagged by one month' and 'True-up payments generated from activity in any Fiscal Year are received in the following Fiscal Year' - and the arithmetic confirms it: FY 2013/14 receipts of $237,312,301 give an apparent ceiling of $1.978bn on Net Win, while EDR's own Net Win for that year is $2.098bn. Two further blockers survive a matched period: the payment is max(percentage amount, guaranteed minimum) and a binding minimum carries no information about Net Win; and under the 2021 Compact one total is the sum of four category schedules and does not determine the four bases.`, `A destination split of a payment recorded in full elsewhere in this file; deriving on it would double count. Refused, not caveated. The published figure is CASH RECEIVED in a state fiscal year and the compact's rate applies to a Revenue Sharing Cycle's Net Win. EDR states the mismatch itself - 'Revenues collected are lagged by one month' and 'True-up payments generated from activity in any Fiscal Year are received in the following Fiscal Year' - and the arithmetic confirms it: FY 2013/14 receipts of $237,312,301 give an apparent ceiling of $1.978bn on Net Win, while EDR's own Net Win for that year is $2.098bn. Two further blockers survive a matched period: the payment is max(percentage amount, guaranteed minimum) and a binding minimum carries no information about Net Win; and under the 2021 Compact one total is the sum of four category schedules and does not determine the four bases.`, `Stated by the State, not derived here. EDR's December 2015 conference names its source: 'the actual Net Win for Fiscal Year 2014-15, and other information from the most recent quarterly financial reports available from the Tribe'. The figure is Net Win as the compact defines it, for the whole tribe. It is not a property figure and cannot be split to one.`, `The amount owed for the cycle under the schedule, which is not the amount received in any one state fiscal year.`
- **`compact_term_source_url`** — `https://www.bia.gov/sites/default/files/dup/assets/as-ia/oig/pdf/508_compliant_2010.07.06_seminole_tribe_tribal_state_gaming_compact.pdf`, `https://www.bia.gov/sites/default/files/dup/assets/as-ia/oig/pdf/508%20Compliant%202021.08.11%20Seminole%20Tribe%20Gaming%20Compact.pdf`
- **`compact_term_source_quote`** — `Twelve percent (12%) of all amounts up to Two Billion Dollars ($2,000,000,000) of Net Win received by the Tribe from the operation and play of Covered Games during each Revenue Sharing Cycle; (ii) Fifteen percent (15%) of all amounts greater than Two Billion Dollars ($2,000,000,000) up to and including Three Billion Dollars ($3,00,000,000) of Net Win received by the Tribe from`, `Ten percent (10%) of Net Win received by the Tribe from the operation and play of Sports Betting, during each Revenue Sharing Cycle, on such wagering by Patrons who access the Tribe's wagering platform via software that uses a brand of a Qualified Pari-mutuel Permitholder pursuant to Part III, Section CC.3. 2. Monthly Payment of Revenue Share Payments (a) On or before the fifte`
- **`entity_tier`** — `B`, `A`
- **`exclusion_flag`** — `state_forecast_not_an_observation`, `restated_by_later_conference`, `month_after_conference_date_not_yet_occurred`, `no_such_series_exists`
- **`exclusion_reason`** — `The month falls after this conference's own date, so the figure is the conference's forecast of a payment not yet made.`, `A later Revenue Estimating Conference published the same period. Retained as the conference's statement at the time; excluded from any single-value series.`, `Adopted forecast of the Revenue Estimating Conference. EDR estimates Net Win in order to forecast the payment; the Tribe does not publish Net Win and the compact marks what it gives the State confidential. Never read as a reported revenue.`, `The fiscal year had not closed when the conference met, so the figure is a forecast.`, `Printed as 0.0 in an in-progress fiscal year. The month falls after the conference date, so the zero is an empty cell, not a measured zero.`, `Florida publishes per-facility slot revenue, cardroom gross receipts and pari-mutuel handle for LICENSED PERMITHOLDERS. A tribal casino operates under the Tribal-State Compact and holds no pari-mutuel permit, so it is outside the population of every per-facility series the State publishes. The 2021 Compact additionally lets the Tribe mark what it does give the State 'Trade Secret, Confidential and Proprietary'.`
- **`source_document_type`** — `edr_revenue_estimating_conference`, `fgcc_annual_report`, `rating_agency_press_release`, `fac_dissemination_general_record`, `sec_registered_fund_schedule_of_investments`, `robots_exclusion_file`
- **`fetched_date`** — `2026-08-07`, `2026-08-05`
- **`disclosure_id`** — `SMBD-0001`, `SMBD-0002`, `SMBD-0003`, `SMBD-0004`, `SMBD-0005`, `SMBD-0006`, `SMBD-0007`, `SMBD-0008`, `SMBD-0009`, `SMBD-0010`, `SMBD-0011`, `SMBD-0012`, `SMBD-0013`, `SMBD-0014`, `SMBD-0015`, `SMBD-0016`, `SMBD-0017`, `SMBD-0018`, `SMBD-0019`, `SMBD-0020`, `SMBD-0021`, `SMBD-0022`, `SMBD-0023`, `SMBD-0024`, `SMBD-0025`
- **`obligor_name_as_published`** — `Seminole Tribe of Florida`, `SEMINOLE TRIBE OF FLORIDA`, `Seminole Tribe of Florida Convention and Resort Hotel Facilities`
- **`conduit_issuer_as_published`** — `Capital Trust Agency`, `Date Acquisition Cost Capital Trust Agency`
- **`disclosure_class`** — `rating_agency_action`, `single_audit_reporting_package`, `bond_named_in_registered_fund_holding`, `municipal_continuing_disclosure_repository`
- **`security_description`** — `Capital Trust Agency, FL, Revenue Bonds (Series 2001), 10.00% (Seminole Tribe of Florida Convention and Resort Hotel Facilities), 10/1/2033`, `Capital Trust Agency, FL, Revenue Bonds (Series 2003A), 8.95% (Seminole Tribe of Florida Convention and Resort Hotel Facilities), 10/1/2033`, `Date Acquisition Cost Capital Trust Agency, FL, Revenue Bonds (Series 2001), 10.00% (Seminole Tribe of Florida Convention and Resort Hotel Facilities), 10/1/2033`, `Series 2005A taxable 5.798% term revenue bonds`, `Series 2005B taxable 6.535% term revenue bonds`, `Series 2007A tax-exempt 5.250% special obligation bonds`, `Series 2007A tax-exempt 5.750% special obligation bonds`, `Series 2007A tax-exempt 5.50% special obligation bonds`, `Series 2007B taxable 7.804% special obligation bonds`, `Series 2008A taxable 8.030% special obligation bonds`, `Series 2010A tax-exempt 5.125% bonds`, `Series 2010B taxable 7.75% bonds`, `Senior term loan (2007 vintage), amount outstanding at 2013-04-02`, `Senior secured term loan B`
- **`series`** — `2001`, `2003A`
- **`maturity_date`** — `2033-10-01`, `2020`, `2017-10`, `2013-10`, `2020-10`, `2027`, `2022`, `2024`, `2014`
- **`amount_concept`** — `par amount as quoted in the rating action`, `total federal awards expended (NOT revenue, NOT gaming; the Single Audit threshold measure)`
- **`rating`** — `Ba1`, `Baa3`
- **`filer_name`** — `Moody's Investors Service`, `DELOITTE & TOUCHE LLP`, `FEDERATED PREMIER MUNICIPAL INCOME FUND  (FMN)  (CIK 0001199004)`, `Deloitte and Touche LLP`, `DELOITTE AND TOUCHE LLP`, `Municipal Securities Rulemaking Board`
- **`filing_form`** — `rating action`, `Single Audit (2 CFR 200 Subpart F)`, `N-CSR`, `EMMA official statements and continuing disclosures`
- **`filing_date`** — `2003-07-29`, `2005-02-07`
- **`availability_status`** — `carried_from_tribal_bond_issuances`, `withheld_by_rule`, `retrieved`, `not_retrievable_by_automated_client`
- **`carries_gaming_revenue`** — `no`, `unknown_document_not_available`, `unknown_document_not_retrieved`
