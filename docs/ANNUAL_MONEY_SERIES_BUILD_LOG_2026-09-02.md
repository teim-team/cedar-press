# The annual series — federal obligations beside tribal gaming revenue

*Build log, 2026-09-02. `code/1126_annual_total_federal_and_gaming.py` →
`data/clean/annual_indian_country_money_series.csv` (116 rows) and
`docs/ANNUAL_INDIAN_COUNTRY_MONEY_SERIES.json`. The totalling rules live in
`docs/MONEY_TOTALLING_RULES.md` inside `<!-- BEGIN GAMING-TOTAL -->`. Model
decision: **ADR-031**. Grain: `GRAIN_ANNUAL_TOTAL` in `code/512`.
`1126 verify` exits 0 on nine checks; `1126 selftest` fires 9 of 9.*

**The owner:** *"I think we have a more accurate annual total of funding
flowing to Indian Country when we include NIGC's regional gaming numbers."*

He is right. The reason has to be stated precisely, because it is also the
reason the two streams may not be quietly added:

> **Federal obligations are transfers INTO Indian Country.
> Gaming revenue is Indian Country's OWN-SOURCE revenue.**

A total that omits the largest own-source stream badly understates the economy.
A total that adds them into one number claims they are the same kind of money.
Both are published, side by side; `money_class` is on every row; **no row of
the table is a grand total**, and `verify` V3 recomputes federal + gaming per
year and fails if any row equals it.

---

## The series

$B, from `data/clean/annual_indian_country_money_series.csv`. `federal_obligations_total`
is prime + assistance and **never includes subawards**.

| FY | prime | assistance | federal total | NIGC GGR | gaming ÷ federal |
|---|---:|---:|---:|---:|---:|
| 2000 | 0.43 | — | 0.43 | — | — |
| 2001 | 0.58 | — | 0.58 | 12.82 | *(no assistance leg)* |
| 2002 | 0.99 | — | 0.99 | 14.50 | *(no assistance leg)* |
| 2003 | 1.98 | — | 1.98 | 16.73 | *(no assistance leg)* |
| 2004 | 2.62 | — | 2.62 | 19.41 | *(no assistance leg)* |
| 2005 | 3.21 | — | 3.21 | 22.63 | *(no assistance leg)* |
| 2006 | 3.57 | — | 3.57 | 25.08 | *(no assistance leg)* |
| 2007 | 4.13 | 1.86 | 5.99 | 26.02 | 4.34 |
| 2008 | 7.89 | 1.72 | 9.61 | 26.74 | 2.78 |
| 2009 | 8.78 | 4.54 | 13.32 | 26.48 | 1.99 |
| 2010 | 8.89 | 3.60 | 12.49 | 26.50 | 2.12 |
| 2011 | 8.43 | 3.46 | 11.88 | 27.15 | 2.28 |
| 2012 | 9.54 | 3.83 | 13.37 | 27.90 | 2.09 |
| 2013 | 6.57 | 5.80 | 12.37 | 28.00 | 2.26 |
| 2014 | 7.76 | 5.33 | 13.09 | 28.50 | 2.18 |
| 2015 | 7.76 | 5.42 | 13.17 | 29.80 | 2.26 |
| 2016 | 8.48 | 5.84 | 14.32 | 31.30 | 2.19 |
| 2017 | 9.91 | 6.04 | 15.94 | 32.40 | 2.03 |
| 2018 | 10.74 | 7.08 | 17.82 | 33.80 | 1.90 |
| 2019 | 12.22 | 7.50 | 19.72 | 34.70 | 1.76 |
| 2020 | 13.63 | 16.72 | 30.34 | 27.80 | **0.92** |
| 2021 | 15.21 | 33.22 | 48.43 | 39.03 | **0.81** |
| 2022 | 15.64 | 10.95 | 26.59 | 40.94 | 1.54 |
| 2023 | 16.83 | 11.10 | 27.93 | 41.91 | 1.50 |
| 2024 | 18.02 | 12.73 | 30.75 | 43.85 | 1.43 |
| 2025 | 17.62 | 12.86 | 30.48 | 46.16 | 1.51 |
| 2026 | 8.02 | 9.07 | 17.10 | — | *(partial FY)* |

**Over FY2007–FY2025, the 19 years where both federal legs and the gaming
series all exist: federal $367,602,232,832 · NIGC GGR $618,977,205,572 ·
gaming 1.68× federal.**

The ratio is quoted only over that window, deliberately. The modern assistance
table begins at FY2007, so a ratio across FY2001–06 divides gaming by a federal
figure missing one of its two legs — which is how FY2001 comes out at 22× and
means nothing.

**The shape inside the window is the interesting part and it is not flat.**
Gaming runs about 2× federal through the 2010s, **crosses below 1.0 in FY2020
and FY2021** — pandemic assistance more than doubled the federal stream in the
same two years COVID closures took GGR from $34.7B to $27.8B — and settles near
1.5× from FY2022. Neither series explains Indian Country's year on its own,
which is the argument for the owner's instinct and against collapsing it into
one number.

Two more series ride in the table and are never part of that ratio:
`faads_pre2008_assistance_attributed` ($4.722B, FY2001–06, **tier B on every
row** — no DUNS or UEI exists on any pre-FY2007 FAADS row) and
`sec_filed_per_property_net_revenues` ($8.720B across 11 fiscal years, which is
7 properties out of the ~717 the gated ladder currently reports, and sits
**inside** the NIGC figure for the same year).

---

## THE DEFECT THIS PASS FOUND: a naive year sum doubles three years of NIGC

`nigc_regional_ggr.csv` holds 198 region-years across FY2001–FY2025. Grouping
it by `fiscal_year` — the obvious thing to do — silently doubles three of them:

| fiscal year | naive `GROUP BY fiscal_year` | one region system | overstated by |
|---|---:|---:|---:|
| FY2002 | $29.213B | **$14.497B** | $14.716B |
| FY2007 | $52.160B | **$26.016B** | $26.143B |
| FY2016 | $62.600B | **$31.300B** | $31.300B |

**Why.** Every NIGC report publishes the current fiscal year *and* the prior
year, and NIGC re-drew its regions three times. So the boundary year appears
once as the older report's current-year column and once as the newer report's
prior-year column, under two different `region_system_version` values:

| region system | fiscal years held |
|---|---|
| `NIGC_R1_FY2001_FY2002` | 2001, **2002** |
| `NIGC_R2_FY2003_FY2007` | **2002**, 2003–2006, **2007** |
| `NIGC_R3_FY2008_FY2016` | **2007**, 2008–2015, **2016** |
| `NIGC_R4_FY2017_present` | **2016**, 2017–2025 |

The two vintages of an overlap year are close but not equal — FY2002 at
$14.497B against $14.716B, FY2007 at $26.016B against $26.143B, FY2016
identical — so the doubling is not even detectable as a repeated figure.

**The discriminator was already in the file and nothing was reading it:
`figure_vintage`** (`own_year_report` 149 rows, `prior_year_column` 49).
`docs/NIGC_REGION_BUILD_LOG.md` §7 documents both the restatements and the
three duplicate years correctly; what did not exist was a consumer-side rule.

**The rule, now enforced:** *sum only `figure_vintage = own_year_report` within
a fiscal year — which is also NIGC's FIRST publication of that year rather than
its later restatement — and where a year has no own-year report on this disk,
take its prior-year column and say so in `basis`.* Four years are in that state:
**FY2001, FY2011, FY2013, FY2021.**

`verify` V6 does not assert this; it re-derives the naive sum from the live
file every run and **fails unless the fence removes at least three overlap
years**, so the check can tell the difference between working and not being
needed. `selftest` reverts FY2002 to $29.213B and V6 fires.

---

## The fences the series obeys

**1. Prime + assistance, never summed with subawards.** `subawards.csv` does
not appear in this table at all, and `verify` V5 fails if a subaward-sourced
row ever does. A subaward is a slice of a prime award already counted.

**2. A regional figure is never a property's money.** NIGC publishes GGR at the
region level and nowhere else. Measured in `gaming_revenue_bounds.csv`:
**13,803 rows, of which 13,494 are `REGIONAL_GGR_CEILING` spread across 694
distinct `facility_id`s**, and the single largest region-year ceiling is
carried by **162** of them. Apportioning a regional figure to facilities, or
summing it across them, multiplies a region's entire GGR by its property count.
This series rolls NIGC up **only along the axis NIGC itself publishes** —
region to nation. (158 of the 13,803 rows carry no `facility_id`; a
facility-keyed join drops them silently.)

**3. The denominator is imported, never retyped.**
`code/846_session_audit.py::_denom` is the single gated ladder:

```
787 rows - 16 NOT_A_PLACE = 771 placed -> 717 distinct properties
```

**THE LADDER MOVED WHILE THIS WAS BEING WRITTEN — 714 in the morning, 717 by
the evening**, after ADR-030 adjudicated three of the mechanical duplicate
groups as genuinely distinct properties rather than merges. That is precisely
why `1126` **imports the ladder and pastes both its number AND its sentence**
into `coverage_note` and into the `GAMING-TOTAL` block at build time. Nothing
in the output table types a denominator. Re-run `build` and the sentence
updates itself; quote this paragraph and you will be wrong by evening.

**Exactly 11 properties carry an honest per-property revenue figure** —
`SINGLE_PROPERTY_ATTRIBUTED` (115 rows) or `REPORTED_PROPERTY_REVENUE` (61
rows), counted as distinct properties rather than as rows. Every gaming row of
the output states that denominator in `coverage_note`, and `verify` V7 fails if
one does not.

> **And importing it found the ladder BROKEN.** `_denom()` was returning
> **771** as a *distinct-property* count with a shape-change warning attached,
> because the word-boundary escapes in its name-normalising
> regex were on disk as literal 0x08 backspace bytes, so the pattern matched
> nothing and every facility name kept its `CASINO`/`GAMING` token. It failed
> loudly — its own shape test appended *"shape changed, re-derive before
> quoting"* — rather than publishing a sixth denominator. Repaired in `846`
> only, proved byte-for-byte against the backup. **Seven other scripts carry
> the same corruption and are NOT repaired here.** Full account:
> `docs/KNOWN_ISSUES.md`, `<!-- BEGIN ESCAPE-COLLAPSE-1125 -->`.

**4. SEC per-property figures are a third class and are never netted against a
regional figure.** The property is *inside* the region and the regional figure
already contains it. Only `is_first_filing_of_this_fact = Y` rows are summed —
a 10-K restates its two prior years — only `FACILITY_NET_REVENUES`, and the
twelve Mohegan Sun Pocono rows are excluded on
`facility_is_on_indian_lands = N`.

**5. Precision, and the years a chart will get wrong.** `figure_precision`
rides on every gaming row. FY2001–FY2012 are exact thousands; **FY2013–FY2020
are rounded to $0.1B** because NIGC published only a distribution map in those
years, so eight regions each rounded to $0.1B carry up to $0.4B of rounding in
the national figure; FY2021–FY2025 are exact dollars. FY2020 is a COVID trough
and must not be smoothed or used as a growth base.

**6. The two clocks are not the same clock.** NIGC aggregates **each gaming
operation's own audited fiscal year** — *"revenue which may have been earned up
to 16 months prior to publication"* (FY2025 report) — while a federal fiscal
year is the government's. The series places them on one axis because that is
the only axis both publish on; it does not claim they are the same interval.

**7. Partial years are flagged, not hidden.** `is_partial_fiscal_year = Y` on
FY2026 for both federal legs (20,715 assistance rows carry `fy_partial_flag`)
and on FY2023 assistance. NIGC has no FY2026 figure.

---

## The federal side, with its denominator

- `federal_prime_obligations` = `sum(total_obligations)` where
  `attributed_flag = '1'` — **$229,441,298,847.36 across 789,360 rows**, which
  is **74.0%** of the $310,005,258,660.75 the whole table holds.
  `attributed_flag` already excludes the 103,221 rows / $17.07B that
  `code/1079` moved to the honestly-unattributed pool on 2026-09-02.
- `federal_assistance_obligations` = `sum(obligated_usd)` on the same flag —
  **$168,639,438,944.64 across 549,530 rows**.
  *(`attribution_status = 'cedar_neid'` is a slightly different population —
  553,106 rows / $170.17B. `attributed_flag` was used throughout for
  consistency with the prime leg; a consumer preferring the newer column will
  get a figure about $1.5B higher and should say which they used.)*
- **The federal total is complete only from FY2007.** FY2000–06 carries prime
  only. The pre-2008 Native assistance slice is its own series, is tier B
  throughout, and overlaps the modern table in FY2007 by 11,063 transactions /
  $2.166B — subtract by key if you stack them.

## Reproduce

```
py -3 code/1126_annual_total_federal_and_gaming.py build
py -3 code/1126_annual_total_federal_and_gaming.py verify     # exit 1 on breach
py -3 code/1126_annual_total_federal_and_gaming.py selftest   # 9/9 fire
py -3 code/1126_annual_total_federal_and_gaming.py doc        # print the block
```

## What is not in this series, and why

- **Tribal tax revenue, resource royalties and state gaming payments.** All
  three are own-source or intergovernmental and all three would belong in a
  fuller own-source picture. `resource_revenue.csv`, `tribal_tax_bases.csv` and
  the state gaming tables are each on a different grain and none was added
  without its own totalling fence. That is the next extension.
- **A grand total.** Deliberately absent, and gated.
