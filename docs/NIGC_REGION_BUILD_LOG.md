# NIGC Region Build Log

*Built 2026-08-06 by `code/84_build_nigc_regions.py`. Cedar Press.*

This log separates **what was verified against a retrieved document** from
**what was taken on faith**. Every figure in `nigc_regional_ggr.csv` is in the
first category or it is not in the file.

---

## The rule this build is organised around

> A property being **included in** a regional revenue universe is not the same
> as that property **generating** the region's revenue.

NIGC publishes GGR at the region level and nowhere else. A source report
proposed a `MODELED_PROPERTY_GGR` column — regional GGR allocated across
properties, calibrated to sum back to the regional total. **It was refused and
no such column exists.** NIGC's own FY2025 revenue-by-range page is the reason,
and it is quoted below because the refusal has to be measurable, not stylistic.

The one regional average we publish is `region_mean_ggr_per_operation_usd`,
which carries a companion flag `region_mean_is_descriptive_only = 1` and is
never joined to a property.

*(A source report circulated for this work names the venture "Cedar Grove". It
is Cedar **Press**. Noted so the mistake does not propagate.)*

---

## 1. Verified against the FY2025 PDF

Source: `GGR25_071526.pdf`, retrieved 2026-08-06 from
<https://www.nigc.gov/downloads/gross-gaming-revenue-reports/> via the WPDM
download link on `/download/ggr25_071526/`. Held at
`data/raw/external/nigc/ggr_reports/GGR25_071526.pdf` (2,366,998 bytes,
md5 in `data/raw/external/nigc/_SOURCE_MANIFEST.csv`).

The claimed table was handed to me already checked for arithmetic. Arithmetic
consistency is not sourcing, so each figure was located in the document. **All
sixteen figures appear verbatim.** They come from the report's *Revenue
Comparison* table (page 6), which prints exact dollars, and the operation counts
from the *Revenue by Region* map (page 5).

| Region | Claimed GGR | In document | Claimed ops | In document |
|---|---|---|---:|---|
| Sacramento | $12.631B | `$12,631,303,247` ✓ | 88 | `88 Operations` ✓ |
| Washington DC | $11.218B | `$11,218,298,614` ✓ (printed as **D.C.**) | 46 | `46 Operations` ✓ |
| St. Paul | $5.320B | `$5,320,261,193` ✓ | 101 | `101 Operations` ✓ |
| Portland | $4.944B | `$4,943,983,904` ✓ | 58 | `58 Operations` ✓ |
| Phoenix | $4.211B | `$4,211,135,056` ✓ | 54 | `54 Operations` ✓ |
| Oklahoma City | $3.745B | `$3,744,841,561` ✓ | 80 | `80 Operations` ✓ |
| Tulsa | $3.653B | `$3,653,169,798` ✓ | 74 | `74 Operations` ✓ |
| Rapid City | $439.8M | `$439,790,197` ✓ | 44 | `44 Operations` ✓ |

Also verified in the same document:

- Printed total `$46,162,783,570`; our eight rows sum to the same. ✓
- `545` operations, printed twice — in *About this Report* and on the cover
  callout. Our counts sum to 545. ✓
- `5.3%` increase over FY2024's `$43,852,030,848`. ✓
- The report calls the region **D.C.**, not "Washington DC". The name has had
  five printed forms since FY2002; see §5.

### The distribution figures, verified

> "Approximately 9% of gaming operations reported more than $250 million of GGR
> in FY 2025 and their aggregate revenues made up more than half (56%) of the
> total GGR. In comparison, just over 54% of Tribal gaming facilities reported
> less than $25 million in GGR, and this group represents about 5% of the total
> GGR share."
> — `GGR25_071526.pdf`, *Revenue by Range*, page 7

The chart above that paragraph prints `54.3%` and `55.8%` as the two extreme
bars. **Both claimed distribution figures are confirmed.**

Why it settles the modelling question: $46.163B / 545 = **$84.7M** per
operation. For the 54% of operations reporting under $25M that is wrong by at
least 3.4×, and for the largest properties it is wrong by an order of magnitude
in the other direction. A constrained allocation that reconciles to the regional
total is the same error with a checksum attached.

The pattern is stable, not an FY2025 artefact: FY2022 `8% / 51%` and
`55% / 5%`; FY2023 `9% / 55%` and `55% / 5%`; FY2024 `9% / 55%` and `54% / 5%`.

---

## 2. Coverage: what NIGC has, and what it does not

**Years covered: FY2001–FY2025 (25 fiscal years), 198 region-years.**

Cedar Press targets 2000–2026. Both endpoints are unavailable and neither is a
gap in our effort:

- **FY2000 does not exist as an NIGC regional report.** The archive's earliest
  item is the FY2001-and-FY2002 comparison (`gamingrevenuesbyregion2002to2001.pdf`).
  FY2001 is recoverable only as that document's prior-year column.
- **FY2026 is not published.** The FY2025 report was released 2026-07-15; an
  FY2026 report would follow in mid-2027.

All 24 documents were taken from **nigc.gov itself**. The Wayback Machine was
used only to enumerate historical URL patterns and supplied **no figure in this
build** — nothing NIGC hosts today needed backfilling.

Two documents in the archive have **no text layer** and were read as rendered
images rather than skipped:

- `NIGC_GGR_Chart_2014_Gaming_Revenue_Distributed_by_Region.pdf` — the sole
  source for FY2013 and FY2014 regional figures.
- `Regional-Gross-Gaming-Revenue-Trends-2.pdf` — growth rates only, no dollars;
  used below as an independent check on FY2011.

Archive gaps: NIGC hosts no 2010-and-2011 and no 2012-and-2013 comparison.
FY2011 comes from the FY2012 table's prior-year column and FY2013 from the
FY2014 map's prior-year annotations. Both are labelled `prior_year_column` in
`figure_vintage`.

---

## 3. Independent verification, document against document

Cross-checks that could have failed and did not:

**FY2011, seven regions, two unrelated documents.** The 2011-2012 trends chart
(image-only, growth rates) prints Portland 4.1%, Sacramento 1.6%, Phoenix 3%,
St. Paul 2.5%, Tulsa 6.8%, Washington DC 0.1%, Oklahoma City 7.6%. Computing
those rates from the FY2010 and FY2012 tables gives 4.09, 1.60, 2.98, 2.55,
6.79, 0.07, 7.57. **Seven of seven agree.**

**The FY2017 region split, arithmetic.** FY16 map: St. Paul `132 AFS`, `$4.9B`,
no Rapid City region on the page. FY17 map: `St. Paul 93 (\`16=93)` and
`Rapid City 39 (\`16=39)`. 93 + 39 = 132 exactly, and $4.5B + $0.4B = $4.9B.
**The split is confirmed, and it is confirmed as FY2017, not FY2020.**

**Every national total.** `review/nigc_total_reconciliation_2026-08-06.csv`
re-sums our regional rows against NIGC's own printed totals for all 26
year-vintages that print one. **26 of 26 agree** on both dollars and operation
counts. Exact-dollar years are held to $2,000; map years to a rounding envelope
of $0.05B per region, because n regions each rounded to $0.1B cannot sum
exactly to a total that is itself rounded.

**FY2025 percentage column.** NIGC prints per-region change; recomputing from
its own FY2024 and FY2025 dollars reproduces all eight to the printed decimal.

---

## 4. Region systems — four, not two

`series_breaks.csv` carried this as UNVERIFIED: *"seven regions in 2009 and
eight in FY2020."* **The seven is right for 2009 and the FY2020 is wrong**, and
there were two earlier systems it did not cover. Confirmed detail is in
`review/nigc_series_breaks_2026-08-06.csv`.

| Version | Reports | Regions | What changed |
|---|---|---:|---|
| `NIGC_R1_FY2001_FY2002` | FY2001–FY2002 | 6 | Region I–V plus a separately named "Eastern Region" |
| `NIGC_R2_FY2003_FY2007` | FY2003–FY2007 | 6 | Eastern → Region VI; **Montana moved Region I → Region IV** |
| `NIGC_R3_FY2008_FY2016` | FY2008–FY2016 | 7 | Roman numerals → city names; **Region V split into Tulsa and OK City** |
| `NIGC_R4_FY2017_present` | FY2017– | 8 | **Rapid City split out of St. Paul** |

### The dangerous one: a boundary that moved without a rename

Region I and Region IV kept their names across FY2002→FY2003 while Montana
moved between them. Measured in NIGC's own pages:

| | FY2002 as first published | FY2002 as restated in the FY2003 report |
|---|---|---|
| Region I | 72 ops, $1,196,178K | **47 ops**, $1,230,194K |
| Region IV | 75 ops, $3,523,690K | **109 ops**, $3,537,227K |
| Total | 330 ops, $14,497,000K | 348 ops, $14,716,056K |

A Region I series charted straight through FY2003 loses a quarter of its
operations to a definition. Both vintages are in `nigc_regional_ggr.csv` under
their own `region_system_version`, so the discontinuity is visible rather than
smoothed.

### The Oklahoma and Nevada splits, verified

- **Oklahoma.** NIGC's legend, unchanged from the FY2008 report to the current
  Regions page: **Tulsa = Kansas + Eastern Oklahoma; Oklahoma City = Western
  Oklahoma + Texas.** Independently visible on the FY2014 map, where Oklahoma
  is drawn in two colours. NIGC's gaming location map splits its 124 Oklahoma
  locations 62 Tulsa / 62 Oklahoma City.
- **Nevada.** **Sacramento = California + Northern Nevada; Phoenix = Arizona,
  Colorado, New Mexico + Southern Nevada.** Printed on every legend from the
  FY2002 report onward and on the current Regions page.

**NIGC publishes no boundary line inside either state, and this build does not
draw one.** Where a property sits in Oklahoma or Nevada, the only sourced answer
is NIGC's own placement of that property on its gaming location map. Properties
in those states that NIGC does not map are left `unassigned_substate_split_not_sourced`
— 171 assignment rows. That is the correct outcome, not a shortfall.

### States outside every legend

`review/nigc_out_of_legend_states_2026-08-06.csv` — two properties, in **Missouri**
and **Pennsylvania**, sit in states no NIGC legend has ever listed. No region
assigned. Separately, NIGC's own map places an **Arkansas** location in the
Tulsa region while Arkansas appears in no printed legend; recorded as a series
break rather than resolved.

---

## 5. Names, and the joins they break

One region has carried five printed names: `Eastern Region` (FY2002) →
`Region VI` (FY2003–07) → `Washington (fka Region VI)` (FY2008–09) →
`Washington DC` (FY2010–21) → `D.C.` (FY2022–25). Oklahoma City is `OK City`
through FY2012 and `Oklahoma City` after; NIGC's gaming location map calls that
same region `Oklahoma Region`. The operation count is labelled `ops` on the FY15
map, `AFS` on FY16, and `submissions` on FY21.

`nigc_regional_ggr.csv` normalises to one `region_name` per system version.

---

## 6. The "operation" definition — partly confirmed, partly not

**Confirmed, in NIGC's own prose** (FY2022–FY2025 reports, *About this Report*):

> "The GGR figure identified in this report is an aggregate of gaming revenues
> collected from the audited financial statements of 545 gaming operations,
> facilities operated by nearly 250 Tribal Governments across 29 states. …
> Tribes are required to submit financial statements within 120 days after the
> end of the operation's fiscal year."

FY2025 adds the timing consequence:

> "Because Tribes have differing fiscal year-ends for their operations, the
> Agency receives audited financial statements continually during the calendar
> year. … Consequently, fiscal year GGR data found in this report includes
> revenue which may have been earned up to 16 months prior to publication."

**NOT confirmed: the consolidated-audit clause.** The claim that an operation
may report "individually or through a consolidated audit" was carried into
`series_breaks.csv`. **The string "consolidat" does not appear in any of the 24
NIGC GGR documents retrieved for this build.** It may well be true — it is not
in these documents, so it stays `UNVERIFIED`. **Taken on faith, and flagged.**

**Partly confirmed: late submissions.** The FY2005 report footnotes:

> "12 operations' revenue figures compiled from fee worksheets, as audited
> financial statements of those operations were not received."

That is *substitution*, not exclusion, and no later report repeats the footnote.
Whether the practice continued is unknown.

---

## 7. What NIGC restates, and what it does not

Every early report revises the prior year, in both directions:

| Fiscal year | As first published | As restated next year |
|---|---|---|
| FY2003 | 330 ops / $16,730,148K | 358 ops / $16,826,126K |
| FY2004 | 367 ops / $19,407,510K | 375 ops / $19,479,134K |
| FY2005 Region II | $7,042,686K | **$6,992,784K** (down) |
| FY2006 Region III | $2,927,711K | **$2,718,914K** (down 7.1%) |

`nigc_regional_ggr.csv` publishes the **first** publication and records which it
is in `figure_vintage`. Where a later report restates onto a new region system,
both vintages are present under their own version — that is why FY2002, FY2007
and FY2016 each appear twice.

**No restatement is detectable in the modern series.** The FY2024 report's
FY2023 column equals the FY2023 report's own total to the dollar
(`$41,905,347,538`), and the FY2025 report's FY2024 column equals the FY2024
report's own total (`$43,852,030,848`).

---

## 8. Precision — the part a chart will get wrong

| Years | Precision | Why |
|---|---|---|
| FY2001–FY2012 | exact, printed in thousands | regional tables |
| FY2013–FY2020 | **rounded to $0.1B** | NIGC published only a distribution map |
| FY2021–FY2025 | exact dollars | regional tables returned with the FY2022 report |

Eight regions each rounded to $0.1B carry up to $0.4B of rounding in a national
total. `figure_precision` marks every affected row; do not present FY2013–FY2020
regional figures to more than one decimal of a billion.

Two further caveats NIGC states itself: three FY2010 operations reported only
nine months of revenue after changing their fiscal year-end, and FY2020 is a
COVID trough ($34.6B → $27.8B → $39.0B) that must not be smoothed and must not
be used as a growth base.

---

## 9. Region assignments — by location, never by headquarters

`data/clean/nigc_region_assignments.csv`, 2,438 rows over 772 of the 774 properties;
**738 properties carry at least one sourced region**.

| Method | Rows |
|---|---:|
| `nigc_published_state_to_region_legend` | 2,072 |
| `nigc_published_gaming_location_map` | 188 |
| `unassigned_substate_split_not_sourced` | 171 |
| `state_absent_from_published_legend_for_this_system` | 7 |

Every row carries `assignment_geography_basis = property_location_not_tribal_headquarters`.
A tribe headquartered in one state can operate in another; the region follows
the property. Rows are emitted per region-system version with effective years
clipped to the property's own opening and closing years, so no assignment
claims a property existed before it did or survived after it closed. **No
assignment for any year whose legend we could not source.**

### One federal-source conflict, recorded both ways

`review/nigc_region_conflicts_2026-08-06.csv` — **Rosebud Casino**, addressed
`HC 14, Box 135, Valentine NE 69201`. NIGC's state legend puts Nebraska in
**St. Paul**; NIGC's own gaming location map puts this property in **Rapid
City**. Both are NIGC. Both are recorded; the property-specific map placement is
used and the legend disagreement is kept visible rather than resolved away. The
likely explanation — the property sits on the Nebraska/South Dakota line with a
Nebraska mailing address — is a hypothesis, not a finding, and is not written to
any data file.

---

## 10. Roster diff — the highest-value output

`review/nigc_roster_diff_2026-08-06.csv`, 914 rows.

NIGC's gaming location map (`https://www.nigc.gov/map/`) is a published
universe: every entry exists by definition. Its marker set is served through
`admin-ajax.php` for `map_id=6` (the `wp-json` route requires login) and is
held raw at `data/raw/external/nigc/locations/`. **490 locations**, each
carrying NIGC's own region as its marker category — so the region assignment
for a matched property is NIGC's, not ours.

| Outcome | Rows |
|---|---:|
| `IN_CEDAR_NOT_IN_NIGC` | 424 |
| `MATCHED` | 350 |
| `IN_NIGC_NOT_IN_CEDAR` | **140** |

Matching is deterministic and one-to-one — nearest-first greedy on coordinates
within 1.2 km in the same state (230), then identical normalised name in the
same state (97 near, 23 far, kept separate). Name normalisation is script 33's
`norm`; tribe resolution on new rows is script 33's `resolve_entity`. **No new
name matcher was written.**

**The 140 `IN_NIGC_NOT_IN_CEDAR` rows are staged for addition**, by NIGC region:
St. Paul 36, Phoenix 24, Oklahoma City 19, Portland 16, Rapid City 15,
Sacramento 13, Tulsa 9, D.C. 8. `resolve_entity` settles 39 of them to a spine
entity; the remaining 101 are held unresolved rather than guessed, because an
NIGC location name is a facility name and often contains no tribe name at all.
Many are small class II locations inside bars, stores and lodges — `M&W Service
of White Earth`, `Ogema Fire Department, d/b/a Ogema Liquor Store` — which is
precisely the tail a casino-oriented property list misses.

**`data/clean/gaming_facilities.csv` was not touched.** Another agent owns it;
additions are staged in `review/`.

### The ceiling on this diff

**NIGC's universe is class II and class III gaming on Indian lands. A tribally
owned casino operating outside IGRA — commercial licence, off Indian lands —
will never appear there.** NIGC completeness is therefore a **floor for the IGRA
subset, not a ceiling for Cedar Press**. A property absent from NIGC's map is
not evidence it is not ours. This is the same class of error as concluding "not
Native" from a set-aside filter, which `docs/SOURCING_STRATEGY.md` measures at
$1.01B of missed Tribalco contracting.

The two NIGC universes do not even agree with each other: **490 mapped locations
against 545 FY2025 audited-financial-statement operations.**

---

## 11. Triangulation across independent federal sources

`corroborating_sources` on every diff row lists which independent federal traces
confirm a property: NIGC's gaming location map, a tribal-state class III compact
(`compacts.csv`, Federal Register approval notices), a BIA gaming land / Section
20 determination (`gaming_land_decisions.csv`), and a Federal Register gaming
project record (`gaming_project_facilities.csv`).

| Independent federal sources | Cedar properties |
|---:|---:|
| 3 | 133 |
| 2 | 314 |
| 1 | 263 |
| **0** | **64** |

A property confirmed by three federal sources is a materially different asset
from one resting on a single map scrape, and the 64 rows resting on none are the
first place to look for a phantom. Where sources disagree the conflict is
written to `review/` and both are kept; §9 has the one case found.

---

## 12. Coverage benchmark

`review/nigc_coverage_gap_2026-08-06.csv`, 198 region-years. FY2025:

| Region | NIGC operations | Cedar properties assigned | Difference |
|---|---:|---:|---:|
| Oklahoma City | 80 | 44 | **−36** |
| Tulsa | 74 | 53 | **−21** |
| Sacramento | 88 | 108 | +20 |
| Phoenix | 54 | 72 | +18 |
| St. Paul | 101 | 114 | +13 |
| Portland | 58 | 68 | +10 |
| Rapid City | 44 | 48 | +4 |
| Washington DC | 46 | 45 | −1 |
| **Total** | **545** | **552** | **+7** |

**A gap here is a lead, not an error in either source.** An NIGC operation is a
submitter of audited financial statements — one submission can cover more than
one building — and our file is a property list that includes closed rows and
non-IGRA properties. The two Oklahoma deficits are almost entirely our own
refusal to guess the east/west line: properties in Oklahoma that NIGC does not
map get no region at all. The positive differences point at closed rows still
marked current, duplicates, and non-IGRA tribally owned properties NIGC never
counts.

---

## 13. Coverage classification

| `igra_coverage_status` | Rows |
|---|---:|
| `VERIFIED_NIGC_OPERATION` | 490 |
| `LIKELY_IGRA_OPERATION` | 272 |
| `CLOSED_IGRA_OPERATION` | 106 |
| `NON_IGRA_TRIBALLY_OWNED` | 24 |
| `UNKNOWN` | 21 |
| `PROPOSED_IGRA_OPERATION` | 1 |

Nothing that is not a gaming operation comes out as `VERIFIED_NIGC_OPERATION`.
The rule-out list is narrow on purpose: a name test that dropped everything
called "Travel Plaza" would have discarded the Choctaw Nation's class II
locations, which are real gaming operations. A row is `NON_IGRA_TRIBALLY_OWNED`
only when its name asserts a non-gaming use **and** it carries no gaming word
**and** it reports no machines, tables, poker or bingo. The negation
`no casino` / `no gaming` is handled explicitly, because
`Las Vegas Paiute Smoke Shop - no casino` contains the word *casino* in order to
deny one and a naive keyword test reads it backwards.

That test surfaced a finding about our own file: **`gaming_facilities.csv`
contains placeholder rows whose facility name is literally `No casino`,
`No casino currently`, `Tribal admin only - no casino`, or
`Pipe Spring National Monument area - no casino`** — 16 such rows, plus a golf
resort, a golf course, a fire-department liquor store and several smoke shops.
They are correctly kept out of the NIGC operation universe here; the facility
file's owner may want them out of the property count entirely.

---

## 14. Files written

| Path | Rows |
|---|---:|
| `data/clean/nigc_regional_ggr.csv` | 198 |
| `data/clean/nigc_region_assignments.csv` | 2,438 |
| `review/nigc_roster_diff_2026-08-06.csv` | 914 |
| `review/nigc_coverage_gap_2026-08-06.csv` | 198 |
| `review/nigc_series_breaks_2026-08-06.csv` | 14 |
| `review/nigc_total_reconciliation_2026-08-06.csv` | 26 |
| `review/nigc_region_conflicts_2026-08-06.csv` | 1 |
| `review/nigc_out_of_legend_states_2026-08-06.csv` | 7 |
| `docs/codebooks/07b_nigc_regions.md` | — |
| `data/raw/external/nigc/` | 24 PDFs + marker JSON + map page + manifest |

`data/clean/series_breaks.csv` was **not** edited — confirmations are in
`review/nigc_series_breaks_2026-08-06.csv` for its owner to merge. No shared
region registry was created or edited. `code/01_build_entity_spine.py` was not
run.

Region ids: NIGC occupies the reserved block **`CEDAR-ADMREG-900001`–`900027`**
(27 region-versions). The owner of the shared crosswalk may renumber; the join
key inside this build is `(region_system_version, region_name)`.

---

## 15. Pull discipline

One poller, one host. `logs/_HOSTLOCK_www.nigc.gov.json` was written before the
first request. Requests were sequential with a 2 s gap; 26 objects retrieved,
26 HTTP 200, no throttling, no retries, lock released on completion. No
concurrent poller against nigc.gov was found.

One trap worth recording for the next agent: **every landing page under
`nigc.gov/download/<slug>/` contains a sidebar WPDM link with the same
`wpdmdl=3974`.** Taking the first `wpdmdl=` match on the page returns *the same
PDF 24 times*, all 192,025 bytes, and it looks like a successful download.
Match on the link that carries `filename=`, then verify distinct md5s before
parsing anything.

---

## 16. Taken on faith — the honest list

1. **The consolidated-audit clause in the NIGC "operation" definition.** Not
   present in any retrieved document. Left `UNVERIFIED`.
2. **The FY2017–FY2021 region legend.** NIGC's map PDFs for those years print
   no state legend. The R4 state list is NIGC's **current** Regions page,
   retrieved 2026-08-06, and is recorded with `legend_as_of` saying so. Indiana
   and Massachusetts appear only in that current legend, so whether they were in
   the FY2017 legend is unknown.
3. **The Wyoming legend gap.** Wyoming is printed in the FY2002 Region IV
   legend, absent from the FY2003 and FY2004 legends, and back in FY2005.
   Treated as a printing omission and carried in R2 throughout — this is an
   assumption, and it is the only place a legend was smoothed.
4. **Arkansas.** NIGC's map places an Arkansas location in Tulsa; no NIGC legend
   lists Arkansas. Recorded as a break, not resolved.
5. **FY2013 and FY2014 figures** were read from a rendered image of an
   image-only PDF. The internal arithmetic checks out (region counts sum to the
   printed 459 for FY2014; regional dollars sum to the printed $28.5B), but no
   text layer exists to re-extract them mechanically.
