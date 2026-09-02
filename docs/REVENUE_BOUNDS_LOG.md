# Revenue bounds build log

*Script `code/106_build_revenue_bounds.py`. Built 2026-08-07. 13,803 bound rows, 20 band rows. Everything tier B, pending review.*

> Elijah, 2026-08-07: *"maybe sometimes we can process of eliminate revenue too and attribute it."*

Right in principle. The measured state is the point of this file.

## What Cedar actually holds

| | properties | grain |
|---|---:|---|
| Connecticut DCP slot win | 2 | property-month |
| New Mexico net win | 0 | tribe-quarter, 16 tribes |
| Michigan derived net win | 0 | tribe-year, 4 tribes |

So full residual elimination cannot run. You cannot solve for the 88th Sacramento operation knowing none of the other 87. What follows is what IS derivable, and it is a lot.

## 1. Regional ceilings

12,518 property-year ceilings across 694 properties, FY2001-FY2025, joining `nigc_region_assignments.csv` to `nigc_regional_ggr.csv` through the administrative region id and the assignment's effective years.

147 assignment rows were deliberately given NO ceiling because their `igra_coverage_status` is `NON_IGRA_TRIBALLY_OWNED` or `PROPOSED`. A property outside IGRA is not inside NIGC's total, so the regional total says nothing about it. Absence of a bound there is a property of NIGC's universe, not a gap in ours. A further 178 rows carry no region assignment at all.

**The ceiling is never divided by the operation count.** NIGC's own FY2025 distribution is why, and it was verified against the FY2025 report before being relied on:

> 9% of gaming operations reported more than $250 million of GGR in FY 2025

Read off the FY2025 chart: **8.6% of operations hold 55.8% of GGR, while 54.3% hold 4.8%.** An equal allocation of a regional total would be wrong by an order of magnitude for most properties, in both directions.

951 rows carry the tighter ceiling `regional total - the revenue we already know for OTHER properties in the same region-year`. Today that only bites in the Washington DC region, where Connecticut's two properties sit.

## 2. Band constraints - the new extraction

NIGC publishes a `REVENUE BY RANGE` chart giving, for five revenue bands, the share of operations and the share of revenue. **It appears in four of the 24 GGR reports on disk and in no others** - FY2022, FY2023, FY2024 and FY2025. The other twenty are region tables and distribution maps and contain no band data at any resolution; this was checked document by document, not assumed.

| FY | ops <$25M | $25-50M | $50-100M | $100-250M | $250M+ | rev <$25M | $25-50M | $50-100M | $100-250M | $250M+ | operations |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 55.0% | 13.0% | 11.0% | 13.0% | 8.0% | 5.0% | 6.0% | 10.0% | 29.0% | 51.0% | 519 |
| 2023 | 55.0% | 14.0% | 11.0% | 11.0% | 9.0% | 5.0% | 6.0% | 10.0% | 24.0% | 55.0% | 527 |
| 2024 | 54.3% | 14.1% | 11.7% | 11.5% | 8.5% | 4.9% | 5.9% | 10.1% | 24.5% | 54.5% | 532 |
| 2025 | 54.3% | 13.8% | 11.2% | 12.1% | 8.6% | 4.8% | 5.6% | 9.3% | 24.4% | 55.8% | 545 |

**Why this constrains the whole layer.** The share plus the published operation count gives a count per band - in FY2025, exactly 47 of 545 operations sit above $250M, because 8.6% printed to one decimal admits no other whole number against 545 - and the band's upper edge is a ceiling on every operation inside it. It bounds the SET without naming a member, which is exactly the shape of constraint the rest of this layer needs. FY2022 and FY2023, printed to whole percent, give ranges rather than a single count; `pct_precision` says which you are looking at.

Four checks run on every extraction and stop the build on failure: both series must sum to 100 within rounding; the chart's top band must agree with NIGC's own sentence about the >$250M share; the extracted values must equal the values read off a 220-dpi render of the chart by hand; and where the shares are printed to one decimal, the implied counts must add back to NIGC's own operation count. **They do, exactly** - FY2024 289/75/62/61/45 sums to 532 and FY2025 296/75/61/66/47 sums to 545, both the published totals. That is an independent confirmation that the operations series was paired to the right bars. The band EDGE labels are outlined vector art with no text layer, so they were read by hand for all four years and are identical in all four; `chart_label_basis` says so on every row.

## 3. Single-property attribution

**115 tribe-years attributed to a named property. 133 refused.** Refusals are staged at `review/revenue_bounds_single_property_refusals_2026-08-07.csv` with the condition that failed.

`cedar_domain.may_attribute_to_single_property` needs all three of gaming base, verified count, exactly one property open. Failures:

| condition | tribe-years failing |
|---|---:|
| base is not gaming revenue | 0 |
| property count not verified | 43 |
| not exactly one property open | 111 |
| tribe holds no gaming property at all | 3 |

(A tribe-year can fail more than one condition, so these do not sum to the refusal count.)

**The base condition never fired**, and that is not luck: both tribe-level series are gaming measures by construction. New Mexico's is Class III tribal net win from the Gaming Control Board's quarterly revenue-sharing releases; Michigan's is `payment / compact rate` where the compact rate is written against *"the net win at each casino derived from all Class III electronic games of chance"*. A whole-tribe revenue figure would have failed it, and none was used.

### What the count condition caught

The roster diff holds 140 NIGC properties Cedar lacks. 66 of them resolve as an ALIAS of a property Cedar already holds - same name core, same city or same street address - and an alias is not a second property. 20 pin on a tribe and match nothing we hold, and block that tribe's count. 54 could not be pinned on any tribe; those are disclosed per state in every attributed row's `assumption_note` as residual risk rather than silently ignored.

A second check came out of the same file and was not anticipated: **35 properties Cedar records with a close date are on NIGC's CURRENT gaming location map**, across 30 tribes. NIGC's map is current, so the listing contradicts our close date and every later year has an open-property count we cannot stand behind. This is what stopped the Jicarilla Apache Nation from being attributed: Cedar closes `CCP-799200` Wildhorse Casino in 2006 while NIGC still maps *Wild Horse Casino*, so the tribe's count of one from 2012 is not safe.

### A keying defect the layer surfaced

Three New Mexico tribe-years key to `TRBF-SNJUAN-00`, which holds no gaming property. That is the **San Juan collision** already recorded in `AGENTS.md`: New Mexico's regulator writes *San Juan* meaning Ohkay Owingeh, formerly San Juan Pueblo, in New Mexico - while the spine's `San Juan` is the San Juan Southern Paiute Tribe of **Arizona**. The rows are refused and flagged. `gaming_capacity_official.csv` is owned elsewhere and was not edited.

## 4. Residual, where it closes

**It closes nowhere.** 25 region-years carry a residual bound - `regional total - known property sum`, which bounds the combined revenue of the unknown operations from above and therefore bounds any single one of them. 0 of them reduce to a single unknown operation, which is the only case where the residual is a point value.

Residual rows subtract **only reported property revenue**, never a single-property attribution. Subtracting an inference would propagate it into a published bound with nothing on the row to say so.

## 5. Connecticut as the validation case

Connecticut is the one state where Cedar holds every property's revenue, so it is the one place the residual can be checked. **The check does not reconcile, and the reason is the finding.**

| NIGC FY | CT slot win | Washington DC region GGR | CT share | operations in region |
|---:|---:|---:|---:|---:|
| 2018 | $1.07B | $7.50B | 14.3% | 38 |
| 2019 | $0.99B | $7.40B | 13.3% | 42 |
| 2020 | $0.73B | $5.80B | 12.6% | 43 |
| 2021 | $0.81B | $8.10B | 10.1% | 42 |
| 2022 | $0.85B | $8.98B | 9.5% | 41 |
| 2023 | $0.84B | $9.19B | 9.2% | 44 |
| 2024 | $0.84B | $10.22B | 8.3% | 45 |
| 2025 | $0.87B | $11.22B | 7.7% | 46 |

Two independent reasons, both structural:

1. **Region is not state.** NIGC's Washington DC region covers Alabama, Connecticut, Florida, Louisiana, Mississippi, North Carolina and New York - Seminole Hard Rock is in the same bucket as Foxwoods. Connecticut is 2 of 46 operations in FY2025.
2. **Slot win is not GGR.** Connecticut publishes *"Win (9)"*, slot machine win. It excludes table games, which both properties run at scale. The Connecticut figure is a FLOOR on the property's NIGC-comparable GGR and is stored as one.

So the Connecticut sum SHOULD sit well under the regional total, and it does. A reconciliation would have been evidence of an error, not of success.

## 6. How far residual elimination is from being usable

The question worth answering. `more needed` counts additional property revenues before a single operation remains unknown in that region-year.

| NIGC region | FY | operations | known (reported) | known (incl. attributed) | more needed | best-covered year |
|---|---:|---:|---:|---:|---:|---|
| Oklahoma City | 2025 | 80 | 0 | 0 | 79 | FY2016 (0 known) |
| Phoenix | 2025 | 54 | 0 | 0 | 53 | FY2018 (6 known) |
| Portland | 2025 | 58 | 0 | 0 | 57 | FY2016 (0 known) |
| Rapid City | 2025 | 44 | 0 | 0 | 43 | FY2016 (0 known) |
| Sacramento | 2025 | 88 | 0 | 0 | 87 | FY2016 (0 known) |
| St. Paul | 2025 | 101 | 0 | 2 | 98 | FY2019 (2 known) |
| Tulsa | 2025 | 74 | 0 | 0 | 73 | FY2016 (0 known) |
| Washington DC | 2025 | 46 | 2 | 2 | 43 | FY2017 (2 known) |

**These counts are a floor on the work, not a target, and strict residual elimination is probably unreachable in most regions at any coverage.** NIGC's `operation_count` counts submitters of audited financial statements, not buildings. One submitter can cover several properties, so a complete property file still would not put the two universes in 1:1 correspondence, and `n_known == operations - 1` would remain unverifiable.

What DOES scale with coverage is the tighter ceiling: every additional known property revenue lowers `REGIONAL_GGR_CEILING_NET_OF_KNOWN` for every other property in the same region-year. That is a real, monotonic gain and it needs no closure.

The highest-yield next pulls, from the table above: **Washington DC** (46 operations, smallest region with the largest GGR, and 2 already known), then **Rapid City** (44) and **Phoenix** (54). St. Paul at 101 operations and Sacramento at 88 are the furthest away.

## Guards that ran

- `cedar_domain.may_promote(DERIVED_BOUND, ACTIVE_FLOOR_COUNT)` is asserted False at runtime. A bound can never be relabelled an observation.
- Every `measurement_status` is checked against `cedar_domain.REVENUE_EVIDENCE` plus `SINGLE_PROPERTY_ATTRIBUTED`.
- Every row must carry a `bound_basis` and must bound something; a row with three empty value columns stops the build.
- No row may have a lower bound above its upper bound.
- **No row may contain the words** *estimate*, *predicted*, *confidence interval*, *forecast*, *imputed* or *modelled*, in any column. Scanned on every build.
- `resolve_entity` from `code/33_apply_party_rulings.py` is the only name matcher used. No second matcher was written.

## Files this build did not touch

`gaming_facilities.csv`, `gaming_capacity_official.csv`, `nigc_regional_ggr.csv`, `nigc_region_assignments.csv`, `compact_*`, `ca_gaming_*`, the spine, and every other file owned elsewhere. This layer is additive: two new clean files, one review file, one codebook, this log.

**One step is deliberately left open.** The codebook is written as `docs/codebooks/07e_revenue_bounds.md`, following the precedent of scripts 84 and 100, which write their own. It is NOT yet registered in `code/41_build_codebooks.py`'s `DATASETS`, so the two files do not appear in `codebook_master.csv`. That file was being rewritten by another agent's run of script 41 while this build was running, and editing 41 concurrently would have collided. Adding `"07e_revenue_bounds": ["gaming_revenue_bounds.csv", "nigc_revenue_bands.csv"]` and re-running 41 is the whole remaining job. Note that `bound_basis` is already in 41's `PUBLIC_OVERRIDE`, so the generic `_basis$` internal rule will not swallow it.

A standing failure in `code/62_no_regression_check.py` (`codebook_undocumented_public = 10`) predates this build and belongs to datasets 06 and 12. It was verified as pre-existing, not caused here, and not touched.

Source quotes were located in the NIGC report text for 130 of 198 region-years. The gap is the FY2013-FY2020 map-only reports, which print `$4.8B` rather than a full figure and carry `figure_precision = rounded_0.1B` upstream; those rows leave `source_quote` blank rather than restating a figure the document never printed.
