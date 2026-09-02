# The geography axis — build log (ADR-015, workstream INT)

*Built 2026-09-02 by `code/870`–`875`. Every figure here was measured with
`csv.reader` against the live files; none is copied from a docstring. Where this
document disagrees with an earlier one, the disagreement is named rather than
silently corrected.*

---

## What was asked, and what shipped

ADR-015 measured the geography axis on 2026-09-02 and found **1,070 rows (0.0%)**
across `data/clean/` carrying a joinable key, against 7,399,905 rows carrying a
place in prose. The axis is now built.

Measured over the same population — the transaction and asset tables that carry
a location — with `csv.reader`:

| | rows | carrying a joinable geographic key |
|---|---:|---:|
| before | 4,768,577 | **1,070** (0.0%) |
| after | 4,768,577 | **4,295,674** (90.1%) |

(The six new `geo_*` crosswalk and dimension files add a further ~1.1M keyed
rows of infrastructure on top of that. They are not counted above, because they
are lookup tables rather than Cedar records that gained a key, and counting them
would flatter the figure.)

Six scripts, all with `verify` and a `selftest` that proves `verify` fires on a
synthetic violation:

| script | what it does | outputs |
|---|---|---|
| `870_build_geo_crosswalks.py` | harvests county FIPS crosswalks from five local USAspending corpora | `geo_award_county_crosswalk.csv`, `geo_place_county_crosswalk.csv`, `geo_county_dim.csv` |
| `871_promote_geo_keys_contracts.py` | promotes keys onto the contracting tables | `prime_contracts.csv`, `subawards.csv` (in place) |
| `872_promote_geo_keys_assistance.py` | promotes keys onto the assistance tables | `federal_funding_transactions.csv`, `faads_transactions_all_agencies.csv` (in place) |
| `873_build_aiannh_crosswalk.py` | AIANNH shared infrastructure from TIGER 2024 | `geo_aiannh_dim.csv`, `geo_point_aiannh_assignment.csv`, `geo_aiannh_county_observed.csv` |
| `874_geography_two_sums.py` | the ADR-015 two sums, per dataset per county | `geo_county_two_sums.csv`, `docs/GEO_TWO_SUMS_DEMONSTRATION.md` |
| `875_geo_money_rules_section.py` | the `GEO` block of `MONEY_TOTALLING_RULES.md` | that block only |

---

## Rows keyed, by table

| table | rows | keyed EXACT | keyed DERIVED | unkeyed | any key |
|---|---:|---:|---:|---:|---:|
| `prime_contracts.csv` | 1,217,768 | 247,987 | 963,727 | 6,054 | **99.5%** |
| `federal_funding_transactions.csv` | 701,955 | 149,112 | 514,061 | 38,782 | **94.5%** |
| `faads_transactions_all_agencies.csv` | 2,769,748 | 615,012 | 1,792,565 | 362,171 | **86.9%** |
| `subawards.csv` | 76,859 | 12,140 | 0 | 64,719 | **15.8%** |

`exact` = a federal award-summary or transaction record named the county for
that specific key. `derived` = the row's own zip5 or city+state resolved to its
modal county in `geo_place_county_crosswalk.csv`, carrying
`geo_*_place_dominance_share` and `geo_*_place_ambiguous` on the row.

**The derived share is the honest caveat on the headline.** On
`prime_contracts.csv`, 79.1% of rows are derived. A county figure built mostly
on derived keys must say so.

### Two columns, never one

Every promoted table carries `geo_recipient_county_fips` **and**
`geo_pop_county_fips` separately, plus county name, state FIPS, dominance share,
ambiguity flag, tier, basis and build date. On `subawards.csv` they are named
`geo_prime_award_recipient_county_fips` / `geo_prime_award_pop_county_fips`
because the crosswalk key there is the PRIME award's, and the subawardee's own
county is not derivable from that table at all.

---

## What could NOT be keyed, and why

1. **`subawards.csv`, 64,719 rows (84.2%).** The table joins to the crosswalk on
   `prime_award_unique_key`, and only 12,140 of its prime keys are in the gapfill
   corpus. The rest are primes outside the Native-candidate pull. Worse, the
   **subawardee's own county is not derivable at any tier**: the clean table
   carries `sub_state` and no sub city, sub zip or sub county column. The raw
   `All_Subawards` zips in `data/raw/subcontracts/` DO carry `subawardee_zip_code`
   and `subawardee_city_name` — 1.6 GB of them, feeding 6.6M rows that 870 already
   reads for place evidence. Promoting the subawardee side is a real, unblocked
   next job; it was out of scope here and is not done.

2. **`faads_transactions_all_agencies.csv`, 362,171 rows (13.1%) unkeyed, and
   only 615,012 rows (22.2%) EXACT.** Two separate ceilings:
   - the table carries `assistance_transaction_unique_key` on **825,754 of
     2,769,748 rows (29.8%)**. The other 70% never got one; `30_funding_pre2008
     .to_out_row` did not carry the column, as `MONEY_TOTALLING_RULES.md` already
     records, and the re-extract that would restore it is queued and unrun. **This
     is a mapper defect, not a source defect — the key is in the staged zips.** It
     is the single largest ceiling on the geography axis.
   - of the FAADS archive zips, only the twelve `*_fy2007_archive.zip` and the
     eleven DOI `seam/doi_fy*.zip` carry the county columns at all. The FY2001–2006
     per-agency pulls use an older extract schema with no county FIPS in it. No
     local work fixes that; it needs a re-pull.

3. **`federal_funding_transactions.csv`, 38,782 rows (5.5%).** Foreign and
   blank-place recipients, plus rows whose city+state pair was never observed
   beside a county FIPS anywhere in five corpora.

4. **County ↔ AIANNH overlap is partial and says so.** TIGER county polygons are
   not on disk, so an exhaustive intersection is impossible today.
   `geo_aiannh_county_observed.csv` holds the **374 (AIANNH, county) pairs
   covering 261 of 864 areas** that Cedar has actually observed from geocoded
   points, and carries a `coverage_note` on every row saying absence of a pair is
   not evidence of no overlap.

5. **`resource_assets.csv` has 35 rows and zero usable coordinates**; its
   `fips_code` is populated on 3. Nothing to promote.

---

## Where ADR-015 is wrong, incomplete, or was overtaken

It is a specification, not scripture. Five findings.

### 1. The unlock is bigger than the ADR says, and in more places

> *"The unlock is already on disk. `data/raw/contracts/usaspending_gapfill_2026-08-05/`…"*

True but an undercount. **Five** local corpora carry USAspending county-FIPS
columns, not one:

| corpus | grain | rows read | place observations |
|---|---|---:|---:|
| `contracts/usaspending_gapfill_2026-08-05/` | award summary | 1,124,547 | 3,341,466 |
| `external/faads/{agencies,seam}/` | transaction | 874,201 | 1,137,878 |
| `federal_funding/usaspending_2023_2026/` | transaction | 273,966 | 436,916 |
| `federal_funding/usaspending_credit_2026-08-06/` | transaction | 100 | 194 |
| `subcontracts/usaspending_subawards_2026-08-05/` | subaward | 6,613,471 | 10,698,367 |

This matters concretely. The gapfill corpus is a **Native recipient universe**,
so the place lookup it yields alone covered **6,421 zip codes**. Pooled across
all five it covers **21,923 zip codes and 20,727 city+state pairs** — and that is
what made it possible to key 2.4M rows of `faads_transactions_all_agencies.csv`,
the largest table in Cedar, which the gapfill corpus alone could barely touch.

### 2. TIGER AIANNH was already on disk

> *"AIANNH is the better key where it can be had."*

It could be had, that day. `data/raw/external/tiger/tl_2024_us_aiannh.zip` — the
national TIGER/Line 2024 AIANNH shapefile, 864 areas — was pulled 2026-09-01, the
day before ADR-015 was written, and the ADR does not mention it. `geopandas`,
`shapely` and `pyshp` are all installed. `873` does exact point-in-polygon
assignment with zero downloads: **2,895 Cedar points tested, 2,164 inside an
AIANNH area, 731 outside.**

### 3. "Money flowing TO an area" is not computable on two of the three tables

This is the substantive one. ADR-015's measure reads:

> *money flowing TO an area — sum by PLACE OF PERFORMANCE*

That is only "money flowing to an area" if the table is the **whole federal
universe** for that area. Two of Cedar's three big money tables are not:

| table | universe |
|---|---|
| `prime_contracts.csv` | Native-CANDIDATE corpus — recipient universe pulled from Native entity lists |
| `federal_funding_transactions.csv` | same shape, assistance, FY2007–2026 |
| `faads_transactions_all_agencies.csv` | **UNFILTERED** — every recipient in the country, FY2001–2007 |

`MONEY_TOTALLING_RULES.md` already stated the third in prose. ADR-015 was written
without it in view. On the first two, the difference is *money in Cedar's corpus
performed in this county that did not reach an attributed Native entity* — a much
narrower claim than the ADR's wording invites, and the most likely misuse of
`geo_county_two_sums.csv`. Every row of that file therefore carries a
`universe_note` saying which it is.

### 4. Rule 3 is right for a reason the ADR does not give

> *"The difference is not always positive or meaningful."*

The ADR justifies this with recipient-vs-performer geography, which is true. It
misses a second reason: **obligations are signed.** A deobligation is a negative
row, so a county whose non-Native rows net negative has an all-recipient sum
*below* its Native sum with nothing whatever wrong. This happens in **49 cells**
of `geo_county_two_sums.csv`. An invariant asserting the Native sum nests inside
the all-recipient sum fired on all 49 — the invariant was wrong, not the data.
Only the ROW COUNTS nest, and that is now what I3 tests.

### 5. `SS000` is not a county

Not an ADR error, but the trap under it. USAspending writes `SS000` when it knows
the state and not the county. **56 such codes** appear in the corpora, and
`01000` sitting unlabelled in a county dimension reads as a county. They are kept
— flag, never delete — and labelled: `geo_county_dim.csv` carries a
`county_code_class` of `county` (3,434), `state_wide_placeholder_not_a_county`
(56) or `county_code_observed_without_a_name` (37), and `874`'s I4 fails if any
two-sums row disagrees with the dimension about which it is.

---

## The demonstration

`docs/GEO_TWO_SUMS_DEMONSTRATION.md`, regenerated on every run of `874`.
**Roosevelt County, Montana (FIPS 30085)** — Fort Peck, AIANNH `1250R` observed
inside it — on `federal_funding_transactions.csv`:

| | sum | rows |
|---|---:|---:|
| money flowing TO the area (place of performance, every recipient) | $231,438,735.86 | 443 |
| money reaching Native entities there (recipient county, attributed only) | $171,641,950.76 | 145 |

Both sides 100% / 98.6% exact-tier. The difference is derived once in that
document, with five bounds attached, and is **never published as a column**.

**Only 5 of 7,785 county-dataset cells passed the coverage bar** (both sides
≥95% exact, ≥100 POP rows, ≥20 Native rows, a real county). That is the honest
headline: the axis exists; the places where it is exact enough on both sides to
carry a difference measure are still few.

---

## What should consume each new file

Named here so none of these becomes a stranded artifact.

| file | who should consume it |
|---|---|
| `geo_award_county_crosswalk.csv` | `871`/`872` only. It is a build intermediate, 154 MB, one row per USAspending award key. Nothing downstream should join to it directly — join to the promoted columns on the transaction tables instead. A candidate for `graveyard/` once the promotions are considered stable. |
| `geo_place_county_crosswalk.csv` | any future promotion of a table carrying a city/state/zip and no county — the obvious next ones are `subawards.csv` (subawardee side), `np_schedule_i_grants.csv`, and the nonprofit tables. Also the right place to look up `dominance_share` before trusting a derived key. |
| `geo_county_dim.csv` | **every consumer of any `*_county_fips` column in Cedar.** It is the only file that says whether a code is a county, a state-wide placeholder, or an unnamed code, and the only source of a county NAME. `874` already joins to it and fails if a code is missing. Cedar Grove needs it to label a map. |
| `geo_aiannh_dim.csv` | Cedar Grove, for rendering; and anyone filtering by AIANNH class — `classfp` and `comptyp` distinguish a reservation from an Oklahoma tribal statistical area that covers whole cities. |
| `geo_point_aiannh_assignment.csv` | **the constellation workstream.** This is the evidence feed for ADR-014's `located_within` tier: 2,164 Cedar points proven inside a named AIANNH area. It is deliberately NOT written into `cedar_constellation_edges.csv` — raising an edge is that workstream's call, and ADR-014 rule 3 says an entity's own words outrank a polygon it sits inside. |
| `geo_aiannh_county_observed.csv` | anyone about to publish a county-level Indian Country figure, to check whether the county contains any observed AIANNH area at all. `874` joins it onto every two-sums row. Read as a floor. |
| `geo_county_two_sums.csv` | **Cedar Grove.** ADR-015 gives Grove the picture and Press the coding; this is the coded product Grove renders. Also the reconciliation target for anyone quoting a county figure. |

---

## Files written

**New scripts:** `code/870_build_geo_crosswalks.py` (rewritten from an incomplete
draft), `code/871`, `872`, `873`, `874`, `875`.

**New data:** `geo_award_county_crosswalk.csv`, `geo_place_county_crosswalk.csv`,
`geo_county_dim.csv`, `geo_aiannh_dim.csv`, `geo_point_aiannh_assignment.csv`,
`geo_aiannh_county_observed.csv`, `geo_county_two_sums.csv` — all in `data/clean/`.

**Modified in place, each with a `.bak_2026-09-02_pre87*` backup and row + money
conservation proven to the cent:** `prime_contracts.csv`, `subawards.csv`,
`federal_funding_transactions.csv`, `faads_transactions_all_agencies.csv`.

**Docs:** `GEO_CROSSWALK_STATS.json`, `GEO_AIANNH_STATS.json`,
`GEO_PROMOTION_CONTRACTS.json`, `GEO_PROMOTION_ASSISTANCE.json`,
`GEO_TWO_SUMS_STATS.json`, `GEO_TWO_SUMS_DEMONSTRATION.md`, this file, and the
`GEO`-marked block of `MONEY_TOTALLING_RULES.md`.

**Not touched:** `data/clean/cedar_constellation_edges.csv`,
`docs/ARCHITECTURE_DECISIONS.md`, and every other marked block of
`MONEY_TOTALLING_RULES.md` — `875`'s I2 proves the last of those byte-for-byte
against a pre-run backup.

Nothing was committed.
