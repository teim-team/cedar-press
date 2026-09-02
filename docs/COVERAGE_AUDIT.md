# Coverage Audit

*Measured from the data on 2026-08-28. Not copied from any doc - regenerate with `py -3 code/35_coverage_audit.py` and this file reflects the files as they actually are.*

Target window: **2000-2026**.

| Dataset | Observed | Rows | Interior gaps | Outside target window |
|---|---|---:|---|---|
| `deals` | 2000–2026 | ~~935~~ **1,073** *(CORRECTED 2026-09-02: `code/1088_merge_staged_deals.py` merged the staged wave, 935 → 1,073 rows and `Announced_Value_USD` $45,195,917,316 → $47,880,355,533, **+$2,684,438,217**; conservation proved row-for-row, 0 of the 935 pre-merge rows lost)* | none | complete |
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
> **STALE DENOMINATORS — read before quoting anything below (2026-09-02).**
> This document is hand-maintained and several of its denominators have moved:
> `deals` 935 → **1,073**; `gaming_facilities` 787 is a **row** count and the
> facility count is **734–780**; `subawards`, `federal_funding_transactions` and
> the `prime_contracts` year rows are sourced from
> `data/clean/coverage_audit.csv`, which `START_HERE.md` records as dated
> 2026-08-06 and reporting **zero** rows for years that hold tens of thousands.
> `docs/INVENTORY.md` (`code/521_inventory.py`) measures every table and **is**
> regenerable; prefer it. Gate:
> `py -3 code/1116_ruling_propagation_2026_09_02.py verify`.

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
> **GAMING-DENOMINATOR-2026-09-02 — the gaming denominator, re-derived from the live files.**
> **`gaming_facilities.csv` holds 787 ROWS, and a row is not a facility.** The ladder, owned and gated by `code/846_session_audit.py::_denom`:
> 
> ```
> 787   rows in gaming_facilities.csv
> -16   whose NAME says no casino - 7 exactly "No casino", plus 9 more like
>       "Grand Canyon West - no casino", "Tribal admin only - no casino"
> =771   facility rows
> -57   extra rows across the same-tribe duplicate groups
> =714   distinct properties
> ```
> 
> **FIVE denominators circulated on 2026-09-02 and all five were quoted as settled: 787, 780, 734, 727, 714.** Each came from a different definition of "facility" and none said which. 787 is raw rows; 780 removes only the 7 EXACT placeholders and misses the 9 that say it in a longer name; 734 is 787 minus duplicates with every placeholder left in; 727 is 780 minus a duplicate count of 53. **None of them is wrong about the piece it measured, and four of them are wrong as a denominator.** No verdict is applied in the table itself - `duplicate_of_facility_id` is populated on 10 rows, not 57 - so 714 is a measurement, not a state of the file. Note also that the duplicate register carries `DIFFERENT_TRIBES_CHECK_BOTH` groups that are **not** duplicates: Stables Casino pairs the Miami Tribe with Modoc Nation, which is a joint operation. Dividing by 787 inflates the denominator by 10.2% and understates every gaming coverage percentage by about 9.3%.
>
> Authority: `code/846_session_audit.py::_denom`, which gates this ladder.
> Re-derive rather than quote: `py -3 code/1116_ruling_propagation_2026_09_02.py derive`.
> `py -3 code/1116_ruling_propagation_2026_09_02.py verify` exits 1 while any
> document in `docs/` or `review/` still states a superseded figure unmarked.
>
> Re-derive rather than quote: `py -3 code/1116_ruling_propagation_2026_09_02.py derive`.
> `py -3 code/1116_ruling_propagation_2026_09_02.py verify` exits 1 while any
> document in `docs/` or `review/` still states a superseded figure unmarked.

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

- **`deals`** — 5 of ~~935~~ **1,073** (0.5% → re-derive; the denominator moved)
- **`native_bills`** — 8 of 3,069 (0.3%)
- **`gaming_decision_events`** — 25 of 265 (9.4%)
- **`gaming_facilities`** — 151 of 787 (19.2%)
- **`gaming_mitigation_agreements`** — 5 of 24 (20.8%)
- **`ownership_events`** — 2 of 98 (2.0%)

## Undated is not one thing

Where a dataset grades its own date evidence, an undated row splits into **bounded** (a source proves the event happened inside a window; no source states the date) and **absent** (nothing found, or the row is not the kind of thing that has one). A bounded row is usable — it can be filtered, ranked and placed in an interval — so pooling the two understates the dataset.

- **`gaming_facilities`** (open_date_class) — **exact** 635 (81%) · **bounded** 90 (11%) · **absent** 62 (8%)
  
  Bounded rows are pinned to intervals spanning 1980–2026; none of that shows in the `open_date` range above.
