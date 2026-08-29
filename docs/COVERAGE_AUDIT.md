# Coverage Audit

*Measured from the data on 2026-08-28. Not copied from any doc - regenerate with `py -3 code/35_coverage_audit.py` and this file reflects the files as they actually are.*

Target window: **2000-2026**.

| Dataset | Observed | Rows | Interior gaps | Outside target window |
|---|---|---:|---|---|
| `deals` | 2000–2026 | 935 | none | complete |
| `federal_funding` | 2006–2026 | 701,955 | none | 6 yr |
| `faads` | 2000–2007 | 2,769,748 | none | 19 yr |
| `subcontracts` | 2001–2026 | 72,837 | 2005, 2006 | complete |
| `lobbying` | 1999–2026 | 27,796 | none | complete |
| `federal_actions` | 1994–2026 | 156,772 | none | complete |
| `bills_votes` | 1973–2025 | 423 | none | 1 yr |
| `native_bills` | 1973–2026 | 3,069 | 1974 | complete |
| `nonprofit_financials` | 1996–2025 | 8,507 | none | 1 yr |
| `compacts` | 1992–2025 | 31 | none | 1 yr |
| `gaming_land_decisions` | 1990–2026 | 138 | none | complete |
| `gaming_decision_events` | 1990–2026 | 265 | none | complete |
| `gaming_facilities` | 1905–2025 | 787 | none | 1 yr |
| `gaming_facility_metrics` | 1993–2026 | 68,211 | none | complete |
| `gaming_project_facilities` | 2013–2026 | 19 | none | complete |
| `gaming_projections` | 2023–2026 | 116 | none | complete |
| `gaming_mitigation_agreements` | 1992–2024 | 24 | none | 2 yr |
| `prime_contracts` | 2000–2026 | 1,217,768 | none | complete |
| `ownership_events` | 2005–2026 | 98 | none | 5 yr |
| `gaming_revenue_bounds` | 1994–2025 | 13,803 | none | 1 yr |
| `ca_gaming_payments` | 2001–2026 | 40,164 | none | 1 yr |
| `resource_revenue` | 1994–2026 | 10,482 | none | complete |
| `consultation_events` | 1994–2026 | 11,402 | none | complete |
| `section_106_consultation_events` | 1994–2026 | 1,363 | none | complete |
| `ferc_docket_filings` | 1990–2026 | 102,615 | none | complete |

## Interior gaps

A year inside a dataset's own range with zero rows. These are defects until proven otherwise - a year that genuinely had no activity is rare, and a failed pull looks exactly like one.

- **`subcontracts`** — [2005, 2006]
- **`native_bills`** — [1974]

## Distance to the target window

- **`federal_funding`** — starts 2006, 6 yr short of 2000  
  *No documented source limit — treat as unfinished work.*
- **`faads`** — ends 2007, 19 yr short of 2026  
  *No documented source limit — treat as unfinished work.*
- **`bills_votes`** — ends 2025, 1 yr short of 2026  
  *No documented source limit — treat as unfinished work.*
- **`nonprofit_financials`** — ends 2025, 1 yr short of 2026  
  *No documented source limit — treat as unfinished work.*
- **`compacts`** — ends 2025, 1 yr short of 2026  
  *No documented source limit — treat as unfinished work.*
- **`gaming_facilities`** — ends 2025, 1 yr short of 2026  
  *No documented source limit — treat as unfinished work.*
- **`gaming_mitigation_agreements`** — ends 2024, 2 yr short of 2026  
  *Documented source limit (start):* Same two-project NEPA pilot; the 1992 row is the Menominee-Wisconsin compact cited in the Kenosha EA.
- **`ownership_events`** — starts 2005, 5 yr short of 2000  
  *No documented source limit — treat as unfinished work.*
- **`gaming_revenue_bounds`** — ends 2025, 1 yr short of 2026  
  *No documented source limit — treat as unfinished work.*
- **`ca_gaming_payments`** — starts 2001, 1 yr short of 2000  
  *No documented source limit — treat as unfinished work.*

## Attributable coverage

Rows existing is a weaker claim than rows usable, so each dataset reports the year from which its rows can actually be attributed to an entity — which is not always the year its rows begin.

Attributability is a TIER, not a yes/no. A row carrying a DUNS or UEI supports a tier-A per-entity series. A row carrying only a recipient name, state and recipient-type code supports a tier-B one — weaker, guarded, and auditable, but not nothing. A row carrying neither supports programme-level totals only. Conflating the second case with the third is how six years of this dataset were written off once.

- **`faads`** — rows span 2001–2007. **No row carries a recipient identifier before 2007**: 6 fiscal years (2001–2006) are 0.0% DUNS across every agency, maximum 0.0%. That is a reporting-regime fact, not a retrieval failure, and it was confirmed by pulling one agency-year through two independent routes with identical results.
  
  **Identifier floor (tier A): FY2007.** Any series that requires a DUNS or UEI must start there.
  
  **Name floor (tier B): FY2001.** The pre-2007 rows are NOT unattributable. They are 100.0% populated on `recipient_name`, `recipient_type` and `recipient_state`, and `code/73_faads_name_attribution.py` attributes **29,594 transactions** to **686 entities** across FY2001–FY2006 — $4,951,906,323 gross, $4,721,685,550 net of deobligations. Every one of those links is **tier B**: a name is not an identifier, and none may be promoted to tier A.
  
  The attributed rows are 1.48% of the 1,994,993 rows in the window and 72.8% of the 40,657 rows USAspending itself codes as tribal government (`recipient_type = I`). The remainder of the window is state governments, individuals, universities and cities — not Native recipients, and never attributable to a tribe. Refusals are itemised in `review/faads_attribution_refusals_*.csv` and the method and audited error rate in `docs/FAADS_NAME_ATTRIBUTION_LOG.md`.

## Combined series

Two files can form one continuous series. Judged separately each looks short; judged together the coverage is real. Report the combination, not either half.

- **Federal assistance** — `faads` 2000–2007 + `federal_funding` 2006–2026 → **2000–2026 continuous**

## Undated rows

A row with no parseable date cannot be placed in any year, so it silently vanishes from every time series built off this data.

- **`deals`** — 5 of 935 (0.5%)
- **`native_bills`** — 8 of 3,069 (0.3%)
- **`gaming_decision_events`** — 25 of 265 (9.4%)
- **`gaming_facilities`** — 151 of 787 (19.2%)
- **`gaming_mitigation_agreements`** — 5 of 24 (20.8%)
- **`ownership_events`** — 2 of 98 (2.0%)

## Undated is not one thing

Where a dataset grades its own date evidence, an undated row splits into **bounded** (a source proves the event happened inside a window; no source states the date) and **absent** (nothing found, or the row is not the kind of thing that has one). A bounded row is usable — it can be filtered, ranked and placed in an interval — so pooling the two understates the dataset.

- **`gaming_facilities`** (open_date_class) — **exact** 635 (81%) · **bounded** 90 (11%) · **absent** 62 (8%)
  
  Bounded rows are pinned to intervals spanning 1980–2026; none of that shows in the `open_date` range above.
