# Labor data sources for the gaming collection

*Written 2026-08-26. Source project: `Desktop/4wheeler` (read only, nothing
modified). Target: Cedar Press gaming collection. One build was cheap and
unambiguous and was done — `code/156_stage_form5500_gaming_employment.py`. The
rest is staged and names what needs ruling.*

---

## 0. The one thing to carry away

**Cedar Press's gaming employment depth today is 769 publishable rows and 10,122
unpublishable ones, and the unpublishable ones are the good ones.**

| | rows | facilities | years | may publish |
|---|---:|---:|---|---|
| `gaming_facility_metrics`, `metric = employees` | **10,122** | **323** | 2002–2023 | **NO** — 100% Casino City Press |
| `gaming_employment_observations` | **769** | 425 | 2008–2026 | yes |
| — `OSHA_ESTABLISHMENT_REPORTED` | 364 | 92 | 2016–2025 | yes |
| — `LODES_BLOCK_WORKPLACE_JOBS` | 384 | 384 | **2021–2022 only** | yes |
| — `PROJECTED` / `ENVIRONMENTAL_REVIEW_COUNT` | 21 | 3 | 2008–2026 | yes |

Every one of the 10,122 employee observations carries
`source = "Casino City Press gaming-property panel (tribal_casino_panel.dta)"`,
and `START_HERE.md` is explicit: *Casino City may be read for QA and never
published.* So the collection's longest, densest, widest employment series is a
QA asset, not a product. The 4wheeler labor sources are the route to a
**publishable** series of comparable reach — and one that runs past 2023, where
both Casino City and `gaming_facility_metrics` stop.

---

## 1. Where the work is, in 4wheeler

Two separate bodies of labor work, built four months apart, for different
purposes. Both are relevant and they do not overlap.

### A. `casino_employment_validation/` — 2026-08-12, casino-specific

The recent work. 22 numbered scripts, five employment sources, a 7,396-row
analysis file over 443 Native entities, a factcheck harness (123/123) and a
sanity harness (0 FAIL / 0 WARN / 5 NOTE). Built to supply **predictive
validity** for IMPLAN, which is why it is organised around headcounts rather
than around geography.

Read first: `docs/DATA_SOURCES.md`, then `docs/KNOWN_DEFECTS.md`, then
`HANDOFF.md`.

**It already speaks Cedar's language.** Step 18 replaced its hand-written regex
tribe filter with the **Cedar Press entity spine** — `resolved_*.csv` files carry
`tribe_id` in Cedar's own vocabulary (`TRBF-`/`AKNF-`/`ANRC-`/`SGVF-`). Nothing
here needs a new matching pass; it needs a join.

### B. `project/build/08–10` + `api/00_download_all.py` — 2026-03/04, geographic

The Lumecon EIA layer. Reservation- and county-level, keyed on 6-character
zero-padded AIANNH `geo_id`, built to feed location quotients and multipliers.
`04_tez_mobility.do` (named in the brief) is the Advan mobility layer, not an
employment source — it carries visit shares, not headcounts.

---

## 2. Source inventory, with casino coverage per source

Casino coverage is asked three ways: by **NAICS**, by **geography**, by **named
establishment**. Each source answers only some of them.

| # | Source | Unit | Years | NAICS 713210 / 721120 / 7132 | reservation / AIANNH | names the establishment | in Cedar already |
|---|---|---|---|---|---|---|---|
| 1 | **DOL Form 5500** | plan sponsor (EIN) | **2009–2025** | **yes, on the filing** | no | sponsor, not property | **no — staged today** |
| 2 | **SEC EDGAR 10-K** | bond issuer | 1996–2022 | n/a | no | enterprise | no |
| 3 | **OSHA ITA 300A** | establishment | 2016–2025 | **yes, on the filing** | no | **yes, by name+address** | **yes** (better in Cedar) |
| 4 | **SBA PPP** | legal entity | 2020–21 | yes, self-certified | no | borrower legal name | no |
| 5 | **NLRB elections** | bargaining unit | 1994–2026 | no | no | **yes, employer + unit** | no |
| 6 | **BLS QCEW** | county × ownership × NAICS | 1990–present | **7132 exists and is SUPPRESSED** | county only | no | no |
| 7 | **Census LEHD LODES8 WAC** | census block | 2002–2022 | **sector only (CNS17 = NAICS 71)** | **yes, block → AIANNH** | no | **partly** — 2021/22 only |
| 8 | **Census LEHD QWI** | county × race × industry | 2005–2022 | 2-digit industry | county → weighted | no | no |
| 9 | **BEA CAEMP25S/N** | county | 1969–present | no | county only | no | no |
| 10 | **Census CBP** | county × NAICS | 1986–2022 | **structurally excludes tribal casinos** | county only | no | no |
| 11 | **BLS OES/OEWS** | — | — | **not built, not checked** | — | — | no |

### The details that decide whether a source is usable

**1 — Form 5500.** The best unbuilt source, and the reason is coverage:
**204 distinct EINs**, 130–143 gaming-NAICS tribal sponsors filing *every year*,
**through 2025**. `TOT_ACTIVE_PARTCP_CNT` is a count of active plan
participants. Two traps: **NAICS is a prefix problem, not a set problem** —
`713200` (the 4-digit group padded out) is filed **1,607 times against 439** for
the specific codes in the staged file, and Seminole Tribe of Florida, the largest
employer in it, files `713200`. An exact-set filter on `713210` cost 4wheeler 120
sponsors including Mashantucket, San Manuel, Tulalip and Shakopee. Second:
**one sponsor files several plans**; they are never summed.

**2 — SEC 10-K.** Only five tribes ever filed real series — Mohegan (FY1996–
FY2022, the longest), Seneca Gaming, Inn of the Mountain Gods (Mescalero),
River Rock (Dry Creek), Choctaw Resort Development (Mississippi Choctaw). Small,
but it is the only *audited-adjacent* headcount and it reaches back to 1997,
**four years before `gaming_facility_metrics` begins**. Definitions move between
filings (Mohegan FY1997 is FTE, later years headcount; Dry Creek switches to
"full and part-time" in 2006) — the verbatim sentence must be read before
differencing.

**3 — OSHA ITA.** Cedar's own layer is already the stronger one:
`data/raw/external/osha_ita/` holds **CY2016–CY2025**, 3,189,050 establishment-
years, of which **5,062 are in a gambling NAICS**, against 4wheeler's 2016–2022.
Two things 4wheeler has that Cedar does not: it carries **`total_hours_worked`**
(so FTE = hours/2080, the only FTE-capable source anywhere here), and it resolves
by **company name to a tribe** where Cedar matched **establishment name to a
property**. Cedar attached only **364 of its 5,062 gambling rows**. The other
~4,700 are on disk, need no network, and 4,700 of them would attach at the tribe
level under 4wheeler's method.

**4 — SBA PPP.** Not for casinos. Eligibility capped at 500 employees, so the
large tribal casinos were **ineligible and never applied — absent, not
censored**. Its value is the small end (median 124 jobs) and **959 non-gaming
tribal businesses** no gaming source captures. **The 959 is an upper bound, not
a Native denominator**: hand review found **at least 317 of 1,069 rows are not
Native entities at all** (Tribe Media Corp, Sun Tribe Solar, Band of Bohemia).
Filter on `review_verdict` in `ppp_resolved_typed.csv`, never on the wide file.

**5 — NLRB.** Tribal casinos are NLRA-covered under *San Manuel Indian Bingo &
Casino*, 341 NLRB 1055 (2004), aff'd 475 F.3d 1306 (D.C. Cir. 2007). 34,794
elections scraped; **~321 gaming; only ~7 genuinely tribal across 3 tribes**
(Mashantucket/Foxwoods, Viejas, Saginaw Chippewa). It measures a **unit, not an
employer** — dealers and housekeeping are separate rows. The one prize:
**Foxwoods, 2,619 eligible voters, November 2007**, the largest single unit in
the national file, for a tribe that files no 10-Ks.

**6 — QCEW.** Two findings from step 19 that must travel with any QCEW figure:

> **Ownership codes break in 2001.** The Community Renewal Tax Relief Act of
> 2000 (P.L. 106-554) made Indian tribes UI-equivalent to state and local
> government, so BLS moved tribal employers from `own_code` 5 (Private) to 3
> (Local Government). New London County CT local government goes **9,811 →
> 29,930** across 2000/2001 while total covered moves 1,779. Neshoba County MS
> goes **1,229 → 6,125** while total covered moves 98. **New York reclassified
> in 2003, not 2001.** Only `own_code` 0 (Total Covered) may be differenced
> across the break.

That break is also the **incidental proof that tribal casino employment is
inside QCEW at all** — a county of 28,000 people does not otherwise have 7,000
local-government jobs.

> **NAICS 7132 is disclosure-suppressed in every shock county-year checked.**
> One or two establishments makes the cell non-disclosable. **The direct route —
> read gaming employment straight off QCEW — does not exist.**

**7 — LODES.** Native grain is the **census block**, which is why Cedar's script
100 pulls block WAC and joins on a geocoded property point. The 4wheeler file is
that same data **aggregated up to the AIANNH boundary** (399 reservations,
**2005–2022**), which sums the casino, the tribal government, the school and the
clinic together — useful as a denominator, never as a property figure.

**8 — QWI.** The only source in either project with a **race dimension** —
`aian_emp` / `white_emp` / `total_emp` by county, 921 counties, 2005–2022 annual
plus 177,245 quarterly rows. It is what CBP structurally cannot give. County
grain, area-weighted to reservations by `aiannh_county_overlaps_multiyear.csv`.

**10 — CBP is ruled out, and this is a finding, not a gap.** 4wheeler's own
`ADDITIONAL_SOURCE_LEADS.md`, under *"Checked and not useful for employment"*:

> **Census County Business Patterns** — excludes government-owned
> establishments, which is what a tribal casino is.

The eight CBP county files (2015–2022, ~68 MB each) in
`project/raw/api/` are still useful for the **non-gaming** side of a reservation
economy. They must never be used to count casino employment. Note this cuts the
other way from QCEW: the FUTA reclassification that put tribal employers into
local government is precisely what makes them **visible in QCEW** and
**invisible in CBP**.

**11 — OES/OEWS is `NOT_CHECKED`.** Nobody in either project looked. It is not
absent; it is unexamined. OEWS publishes MSA/nonmetro-area × occupation and is
the only route to an *occupational* wage structure for gaming floors (dealers,
cage, security), but it does not identify establishments or tribes.

---

## 3. Suppression and disclosure limits — these travel with every figure

**No figure from sources 6, 7 or 8 may be published without the line beside it.**

| source | mechanism | practical effect |
|---|---|---|
| **QCEW** | Establishment-count / dominance rule. A cell with too few establishments, or one dominant employer, is withheld and **published as 0 with a `disclosure_code`** | **NAICS 7132 is suppressed in every shock county-year checked.** A sum over industries silently understates; the suppressed-cell count must gate the value. This is the *worst* failure mode in this document because the suppressed cell looks like a real zero. |
| **LODES** | **Noise infusion by design**, plus synthetic allocation of jobs to blocks | Small-cell block counts are deliberately perturbed. A block figure is an **order-of-magnitude observation, never a payroll number**. Cedar's existing rows already carry `BLOCK_JOBS_ARE_NOT_PROPERTY_PAYROLL`. |
| **LODES, second limit** | A block holds every employer in it, and a large property spans several blocks | The 52 properties carrying both OSHA and LODES have a **median LODES/OSHA ratio of 0.385, 16 below 0.1 and 12 above 1.0**. Reconciling them into one column would be wrong for most of the file. |
| **QWI** | Small-cell suppression on county × race × industry cells | AIAN cells in small counties are the ones that suppress, which is exactly where reservations are. Suppression is **correlated with the population of interest**, so a complete-looking AIAN series is a selected one. |
| **OSHA ITA** | No suppression, but **thin and uneven compliance** | The set of establishments filing under one tribe changes year to year, so a tribe-year **sum** is not a consistent panel. Screen hours-per-employee before use — 6 of 327 rows sit outside 200–5,000 (a "Choctaw Casino Amenity Refresh" reports 19 employees and 117,335 hours). |
| **Form 5500** | No suppression | But **plan participants are not employees**, see §5. |
| **PPP** | Right-censored at 500 | Binds on only 5 of 110 gaming records — large casinos are **absent, not censored**. |
| **Casino City (existing)** | Licence | May be read for QA, never published. |

---

## 4. What was BUILT today

### `code/156_stage_form5500_gaming_employment.py` → `data/staging/gaming_employment_form5500_staged.csv`

**2,046 observations · 140 tribes · 2009–2025.** No network. Reads 4wheeler
read-only. Writes `.part` then renames. Nothing existing was opened for writing.

```
read 10,733 resolved Form 5500 rows (4wheeler, read-only)
  gaming-NAICS rows: 3,335
    resolution 'matched':                     2,839
    resolution 'matched (state mismatch)':      349   kept, flagged
    resolution 'no spine match':                147   dropped, carries no tribe_id
  usable (tribe_id + matched + participants>0): 3,112
  exact-alias defect names present in this subset: NONE
  collapsed to (tribe_id, ein, year), largest plan:  2,046

  tribes with a Cedar gaming facility   127
  tribes NEW to the employment table     34
  rows in 2024-2025                     153  (103 tribes)
  naics_specificity  padded_group_code       1,607
                     specific_industry_code    439
```

Coverage by year: `review/form5500_gaming_coverage_2026-08-26.csv`.

**Checks run before writing, not assumed:**

- The 4wheeler exact-alias resolver defect — Hamilton (110 rows), Evansville
  (17), Georgetown (4), all Alaska Native villages capturing unrelated
  commercial employers, **none of the rows in Alaska** — **does not touch the
  gaming-NAICS subset.** Measured: zero of those names appear. The defect is
  real and open (`4wheeler/.../docs/KNOWN_DEFECTS.md` §1); it is simply not in
  this slice.
- Face validity on the largest rows: Seminole 13,015 (2019) matches 4wheeler's
  independently published figure; Mohegan 8,059 (2024); Yuhaaviatam/San Manuel
  7,368 (2024); Mashantucket Pequot 4,288 (2024).

**A flag was written, measured, and rewritten.** The first version carried
`naics_is_casino_strict`, which came out **0 on Seminole Tribe of Florida** —
because Seminole files the padded group code `713200`. A consumer reading that
column would have concluded the largest employer in the file was not a casino.
It is now `naics_specificity`, which records **how precisely the sponsor filed**
and asserts nothing about the industry. Same shape as the prefix bug that cost
4wheeler 120 sponsors: the padding is a property of the filer, not of the firm.

### Why it is STAGED and not merged

Two rulings block the merge. Neither is this script's to make.

1. **`FORM5500_ACTIVE_PARTICIPANTS` is not in `cedar_domain.MeasurementType`.**
   Adding a term to the shared vocabulary is a domain change. The existing enum
   holds 12 terms and `is_observed` / `NEVER_PROMOTES_TO_ACTIVE` both partition
   it. A plan-participant count **is** observed (somebody counted it) but it is
   **not** a headcount — it may need its own third state rather than either
   existing bucket.
2. **A Form 5500 row keys to an EIN, never to a facility.** Every staged row
   carries `facility_id = ""`. The table already admits tribe-level rows (the
   `PROJECTED` layer has 10 tribes against 2 facilities), so the precedent
   exists — but admitting 2,046 of them changes what the file is. That is a
   schema call.

Merging also moves the asserted count `769`, which appears in
`docs/GAMING_EMPLOYMENT_LOG.md` and in the dataset tables. **Back up before
that runs.**

---

## 5. What a Form 5500 figure means — the caveat that must travel

`TOT_ACTIVE_PARTCP_CNT` **brackets** employment, and the bracket is
**conditional in two directions at once**:

- plans exclude employees below an age or service threshold → **below** total
  employment
- plans include part-timers who clear that threshold → **above** full-time
  headcount

Measured on the same 13 SEC-overlapping tribe-years, *nothing about the employer
changing*:

| comparison | ratio |
|---|---:|
| largest **retirement** plan vs SEC full-time | 1.65 |
| largest **welfare** plan vs SEC full-time | 1.19 |
| vs a study's **total** employment | 0.79 |

**None of 0.79 / 1.19 / 1.65 is a calibration factor.** The usable result is
longitudinal: against SEC full-time counts, year-over-year log changes correlate
at **0.93 (R² 0.86) with a slope of about 0.63** — a slope, on 11 change pairs
across 2 entities. Full conditional estimates:
`4wheeler/casino_employment_validation/docs/FORM5500_CALIBRATION.md`.

Every staged row carries this in `measurement_note`.

---

## 6. Concretely, what each source extends

Cedar's four holdings, and what moves.

### `gaming_facility_metrics` — 65,223 rows, `employees` stops 2023

The `employees` metric is **10,122 rows over 323 facilities, 2002–2023, 100%
Casino City**. It stops at 2023 and it cannot ship.

- **Form 5500 covers 2024 (113 rows / 97 tribes) and 2025 (partial, 27
  sponsors)** — two years past the wall, publishable, and the first year is
  effectively complete.
- **OSHA covers 2023 (768 rows), 2024 (732) and 2025 (784)** in Cedar's *own*
  raw gambling extract, already on disk. Cedar's employment table reaches 2025
  for the 92 matched properties; the other ~4,700 rows are unattached.
- Together these turn "the series ends in 2023" into "the series runs to 2025 on
  a different, publishable footing", with the seam disclosed.

### `gaming_employment_observations` — 769 rows

- **+2,046 staged Form 5500 rows**, of which **34 tribes are new to this table**
  and 127 already have a Cedar facility.
- **LODES is the thinnest layer here — 2021 and 2022 only.** 4wheeler holds
  state-year block WAC back to **2002** for CT/MS/NM/NY, and the LEHD path is
  the same one script 100 already uses, so extending Cedar's block series
  backwards is a re-pull of a known URL pattern, not new research.
- **FTE is derivable today with no network.** `total_hours_worked` is present on
  **5,048 of the 5,062** rows in `data/raw/external/osha_ita/_gambling_naics_rows.csv`.
  It is the only FTE-capable field in any source in this document.

### `gaming_facilities` — 774 rows, 275 tribe_ids, only 164 independently sourced

The licence problem: **610 of 774 properties are Casino City**. Independent
labor sources are independent *existence* evidence.

- **13 tribes file a gaming-NAICS Form 5500 but have no Cedar gaming facility.**
  That is a facility-universe gap with a federal filing behind it, and it is a
  review queue, not a merge.
- **147 of Cedar's 275 facility tribes have no gaming-NAICS 5500 filing** — most
  will be small operations that sponsor no plan, but the list is a checkable
  coverage statement rather than a silence.
- OSHA is the strongest independent-source lever: it names the **establishment
  and its street address**, which is what a facility record needs.

### `gaming_capacity_official` — 6,461 rows

Untouched by any of this. Labor sources carry no device or capacity fields.

---

## 7. Build plan

Ordered by value per unit of work. **Steps 1–3 need no network at all.**

| # | Build | Network | Blocked on |
|---|---|---|---|
| 1 | ~~Stage Form 5500 gaming employment~~ | no | **DONE — script 156** |
| 2 | **OSHA tribe-level attachment + FTE** | **no** | nothing — see below |
| 3 | **Merge the staged Form 5500 rows** | no | **two rulings, §4** |
| 4 | **LODES block backfill 2010–2020** | yes | host lock on `lehd.ces.census.gov` |
| 5 | **QCEW county panel for gaming counties** | yes | ruling on §3 suppression display |
| 6 | **SEC 10-K import (5 tribes, 1997–2022)** | no | 4wheeler cache is local |
| 7 | **QWI AIAN county layer** | no | 4wheeler cache is local; needs a geo rule |
| 8 | **NLRB units** | no | small; 7 rows |
| 9 | PPP ancillary | no | needs the `review_verdict` filter carried through |

### Step 2 is the next cheap one and it is genuinely cheap

Everything it needs is already on disk in Cedar:
`data/raw/external/osha_ita/_gambling_naics_rows.csv` — **5,062 gambling-NAICS
establishment-years, CY2016–CY2025, 5,048 with hours worked.** Cedar attached
**364**. The method that attaches the rest is 4wheeler's: resolve
`company_name` (not `establishment_name`) to a tribe.

It is *not* a copy-paste, and this is the thing to know before starting:
`lib_cedar_resolver.py` **has an open defect** — its exact-alias path runs before
the tribal-word requirement and before class tiering, so place-named Alaska
Native villages (Georgetown, Evansville, Hamilton, St. Mary's) capture unrelated
establishments. It sent **1,228 of 1,731 resolved OSHA rows** into a bad sample
before that build guarded around it locally. Cedar's own `resolve_entity` in
`code/33_apply_party_rulings.py` is **the one resolver** and must be used
instead — AGENTS.md standing rule 8.

So step 2 = read the 5,062 rows, resolve `company_name` through Cedar's own
resolver, emit tribe-level rows with `annual_average_employees`, `total_hours_worked`
and `fte = hours/2080`, and stage them the same way 156 did.

### What needs a ruling, in one place

1. **Does `cedar_domain.MeasurementType` gain `FORM5500_ACTIVE_PARTICIPANTS`?**
   And is a plan-participant count `is_observed` (somebody counted it) or does it
   need a third state (counted, but not the thing)? *Blocks step 3.*
2. **Does `gaming_employment_observations` admit sponsor-level rows with a blank
   `facility_id` at scale?** Precedent exists at 10 rows; this is 2,046.
   *Blocks step 3.*
3. **Do the 254 `state mismatch` rows publish?** They are kept and flagged in the
   staged file. An enterprise HQ filing from another state is ordinary; a
   genuine misroute looks identical on this column alone.
4. **How does a suppressed QCEW cell render?** It is published as **0**. Cedar's
   four-state vocabulary (`PUBLISHES` / `WITHHOLDS` / `NOT_FOUND` /
   `NOT_CHECKED`) already has the right word — a suppressed cell is
   **`WITHHOLDS`** and must never be stored as a zero. *Blocks step 5.*
5. **Is a tribe filing a gaming-NAICS 5500 with no Cedar facility a facility
   lead?** 13 cases. *Feeds the review queue, not a merge.*

---

## 8. Two defects found on the way, both worth writing down

**`code/101_build_lodes_block_employment.py` has CNS17 and CNS18 swapped.**

```python
SECTORS = {
    "CNS17": "jobs_accommodation_food",      # NAICS 72   <- WRONG
    "CNS18": "jobs_arts_entertainment_rec",  # NAICS 71   <- WRONG
```

In LODES WAC, **CNS17 is NAICS 71 (Arts, Entertainment and Recreation)** — where
casinos live — and **CNS18 is NAICS 72 (Accommodation and Food Services)**. The
labels are reversed, so the casino column would ship under the hotel name.

**It has never run**, which is why nothing is contaminated: its outputs
(`data/clean/gaming_employment_lodes.csv`, `data/clean/facility_block_geocode.csv`)
do not exist. The LODES rows in the collection came from
`code/100_finish_declinations_and_employment.py`, which is **correct** — it keeps
the raw `CNS17`/`CNS18` codes in `data/raw/external/lodes/block_wac.csv` and its
`measurement_note` names them the right way round. Verified in the data:
Wetumpka's block `010510308011030` reads `C000=723, CNS17=688` — 688 arts and
entertainment jobs, which is the casino.

**101 is a loaded trap for whoever runs it next.** It was left in place and is
recorded here rather than edited, because it is not this task's file and script
100 supersedes it. Fix it or delete it, but do not run it as it stands.

**`ak_wac_*.csv.gz` files are HTML error bodies, correctly caught.** Three
31,985-byte files sit in `data/raw/external/lodes/` renamed `.NOT_A_GZIP`, and
the manifest records `http_status=200, gzip_magic_ok=False` for ak/2022. LODES8
has never published Alaska. The guard worked — *a 200 body is not proof of an
object* — and it is noted here only so the next reader does not treat the
renamed files as a fetch failure to retry.

---

## 9. Provenance

- **`Desktop/4wheeler` was not modified.** Read only, as instructed.
- **No network calls were made.** Another agent holds the gaming host locks.
- Input: `4wheeler/casino_employment_validation/data/resolved_form5500_tribal.csv`,
  built 2026-08-12, 10,733 rows.
- Outputs: `data/staging/gaming_employment_form5500_staged.csv` (2,046 rows),
  `review/form5500_gaming_coverage_2026-08-26.csv` (17 rows),
  `logs/156_form5500_gaming_2026-08-26.log`.
- Nothing in `data/clean/` was written, and nothing was overwritten, so no
  backup was required.

---
---

# PART II — the OSHA tribe-level build, and both rulings settled

*Appended 2026-08-26, same day. Scripts `157_stage_osha_tribe_level_employment.py`
and `158_merge_staged_labor_employment.py`. No network calls; the OSHA rows were
already on disk.*

---

## 10. Both blocking rulings are RESOLVED, and the reasoning is here so it survives

Part I left two questions open and recorded them only as questions. Both were
settled from precedent already in this codebase. **The reasoning is written here
rather than left in a chat message, because this project's repeated failure mode
is work that gets built and then never plumbed** — script 101 was written and
never run, script 46 the same, an OCR merge step was promised in a docstring and
never written. A staged file plus a question in a transcript is that same shape.

### RULING 1 — `FORM5500_ACTIVE_PARTICIPANTS` is now in `cedar_domain.MeasurementType`

**Precedent:** the enum already carries `OSHA_ESTABLISHMENT_REPORTED` and
`LODES_BLOCK_WORKPLACE_JOBS`, both external administrative employment sources,
and `GAME_FINDER_OBSERVATION` was added the same way on 2026-08-12 by script
142. Adding a term is routine and documented.

**It sits in `is_observed`.** A plan administrator counted a real population on
a real date. `is_observed` asserts that somebody counted something — it does not
assert the population is "employees at a casino", which is what the measurement
type itself is for.

**It also sits in `NEVER_PROMOTES_TO_ACTIVE`,** and that is the load-bearing
half. Active participants are **not** employees: the count **includes** separated
employees who still hold a balance and **excludes** employees who never enrolled
or who sit below the plan's age/service threshold. The two errors do not cancel
and their net sign is not stable. Same shape as the rule the set already
encodes — an authorised maximum is never the number operating, a projection is
never a count, **and an enrollment is never a payroll.**

Verified after the edit:

```
F5500  is_observed: True   never_promotes: True    may_promote(->ACTIVE): False
```

### RULING 2 — a blank `facility_id` on an EIN-keyed row is fine

**Precedent:** `gaming_facility_metrics.csv` already holds **1,039 blank-facility
rows** behind an `entity_level` column — `implied_gaming_revenue` (490),
`ok_exclusivity_fee_annual` (316), `ct_slot_contribution_annual` and
`ct_slot_win_annual` (63 each), plus the MI/WA/WI compact payments. A tribe-level
measure with no facility is an established shape in this collection, not a new
one.

`entity_level = "tribe"` is now set on all 2,046 staged Form 5500 rows and all
485 staged OSHA rows.

### A third measurement type was needed and added

`OSHA_TRIBE_LEVEL_REPORTED` — `is_observed`, and **not** in
`NEVER_PROMOTES_TO_ACTIVE`, because unlike plan participants it *is* a real
employer-filed headcount. Added by script 157 following the same comment pattern.

---

## 11. What was built — `code/157_stage_osha_tribe_level_employment.py`

**485 observations · 84 tribes · 2016–2025 · every row carries a derived FTE.**
No network. Staged, not merged.

```
VERDICTS over 5,062 gambling-NAICS establishment-years:
  blocked_commercial                 2,551  (50.4%)
  unresolved                         1,863  (36.8%)
  attached_via_cedar_facility_brand    345  ( 6.8%)
  attached (spine + 7 guards)          140  ( 2.8%)
  blocked_not_leading                   73  ( 1.4%)
  blocked_remainder                     64  ( 1.3%)
  blocked_class                         17  ( 0.3%)
  blocked_no_tribal_or_gaming_word       6  ( 0.1%)
  candidate_review                       3  ( 0.1%)
```

| | |
|---|---:|
| attach rate | **485 of 5,062 (9.6%)** |
| distinct tribes | **84** |
| year span | **2016–2025** |
| rows already covered at facility grain (flagged, not dropped) | 317 |
| **net new rows** | **168** |
| tribes new to the employment table | **5** |
| hours-per-employee implausible (flagged) | 10 |
| review file rows | 4,577 |

Five tribes gained: Sokaogon, Suquamish (via Port Madison Enterprises), Umatilla
(via Wildhorse Resort & Casino), Chicken Ranch, Mechoopda.

Per year, rows/tribes: 2016 42/29 · 2017 43/27 · 2018 44/30 · 2019 50/31 ·
2020 44/32 · 2021 47/29 · 2022 54/39 · **2023 61/45 · 2024 50/36 · 2025 50/36**.
The last three years are the ones `gaming_facility_metrics` cannot reach.

### The brief's premise was wrong, and the correction is the finding

The brief said *"attach the remaining ~4,700 at tribe level."* **There are not
~4,700 tribal rows.** NAICS 7132/721120 is the *gambling industry*, not the
*tribal* gambling industry, and the pool is majority commercial: International
Game Technology (201 rows), Boyd Gaming (177+76), Caesars (175), Station Casinos
(155), MGM Resorts (138), M.G. Oil (110+38), VICI Properties (96), plus the
California and Oregon state lotteries. **50.4% of the file is blocked as
commercial and that is the correct answer, not a shortfall.**

So the honest job was not "attach the rest" but "find the tribal ones and refuse
the rest out loud." The 4,577-row review file is as much the product as the 485
attachments.

---

## 12. Why the shared resolver could not be used unguarded

`code/33_apply_party_rulings.py::resolve_entity` is the one resolver (AGENTS.md
standing rule 8) and it is used here **unmodified**. 4wheeler's
`lib_cedar_resolver` was **not** used — it carries the open exact-alias defect.

But the containment path has failed in many documented directions and the
central fix was never built. Run unguarded on this exact input, it produced:

| filed name | resolved to | reality |
|---|---|---|
| `CAESARS PALACE LAS VEGAS HOTEL AND CASINO` | **Las Vegas** (Paiute Tribe) | Caesars |
| `BALLY'S LAS VEGAS HOTEL & CASINO` | Las Vegas | Bally's |
| `Circus Circus Las Vegas` | Las Vegas | MGM |
| `Arrow International, Inc - Las Vegas Studio` | Las Vegas | a supplier |
| `CA State Lottery - Santa Ana District Office` | **Pueblo of Santa Ana** | Santa Ana, California |
| `Chumash Casino & Resort Enterprise` | **Enterprise** (Enterprise Rancheria) | Santa Ynez Chumash — matched on the word *enterprise* |
| `Black Diamond Capital, LLC` | Native Community Capital | matched on *capital* |
| `Comfort Suites Oceanside/Camp Pendleton` | Oceanside Corporation | a hotel |
| `Billings` | Billings Urban Indian Health | J&J Ventures Gaming |

**Every one would have written a wrong tribe onto an OSHA injury record.** Seven
local guards were built, each earned by one of those failures. The two that do
the most work:

- **G3, the entity name must LEAD the filed name.** `Blue Lake Casino` leads with
  "Blue Lake"; `CAESARS PALACE LAS VEGAS…` does not lead with "Las Vegas". This
  is 4wheeler's rule 6 reached independently from the same class of failure.
- **G5, a tribal word or a gaming word must be present.** A bare US place name
  resolves to nothing. This is what finally killed `Las Vegas`, `Omaha` and
  `Billings`.

**G7 refuses matches that rest entirely on a `NAME_TRAPS` token** (39 terms).
`Cherokee Nation Entertainment, LLC` and `Little River Casino Resort` are both
*probably right* and both went to review anyway, because "probably right" is not
the standard for writing a tribe onto an injury record.

### A guard that fired in the wrong direction, and the rule it earned

The first version applied the commercial blocklist per **name string**, and let
`establishment_name = "Las Vegas"` resolve to the Las Vegas Paiute Tribe —
**306 employees** — while that same row's `company_name` said **AGS, LLC**, a
slot manufacturer. Fixed by making the block per **row**.

Then the blocklist over-fired in the opposite direction and refused three
genuine tribal properties:

| filed name | `company_name` | actually owned by |
|---|---|---|
| `HARRAH'S CHEROKEE CASINO RESORT` | Caesars Entertainment | **Eastern Band of Cherokee Indians** |
| `Harrah's Ak-Chin Casino` | Caesars | **Ak-Chin Indian Community** |
| `Treasure Island Resort & Casino` (MN) | **Prairie Island Indian Community** | Prairie Island — the field *named the tribe* and the blocklist fired anyway |

**THE RULE: A MANAGEMENT-COMPANY BRAND IS NOT OWNERSHIP.** Caesars *manages*
Harrah's Cherokee; EBCI *owns* it. The blocklist exists to stop heuristic name
matching from inventing a tribe — it must never override a ruling Cedar has
already made about a named property. This is the same shape as the Casino City
note already in AGENTS.md: a tribal convenience store appearing in a gaming
roster is evidence *for* gaming, not against.

Where the two disagree the curated table wins, and `commercial_name_present`
records the tension rather than hiding it.

---

## 13. The brand gap — why a second pass was needed at all

The single biggest reason a genuine tribal casino did not attach was **not**
contamination. It is that **OSHA files a BRAND and the spine keys on a TRIBE
NAME**, and no amount of name matching bridges that:

| OSHA `establishment_name` | employees | owner |
|---|---:|---|
| Yaamava Resort and Casino at San Manuel | 7,449 | Yuhaaviatam / San Manuel |
| Turning Stone Resort Casino | 4,570 | Oneida Indian Nation of New York |
| Casino Arizona · Talking Stick Resort | 3,331 | Salt River Pima-Maricopa |
| Barona Resort & Casino | 3,168 | Capitan Grande / Barona |
| Thunder Valley Casino Resort | 2,555 | United Auburn |
| Cache Creek Casino Resort | 2,044 | Yocha Dehe Wintun Nation |

Cedar already owns that bridge — `data/clean/gaming_facilities.csv` maps
`facility_name → tribe_id`, curated, 758 distinct normalised names. **Pass B**
looks the establishment name up there, requiring an unambiguous single tribe
**and** state agreement. It is not a new name matcher; it is a lookup against a
Cedar-ruled table.

Pass B alone attaches **345 rows the spine refuses**, and it took the build from
284 rows / 41 tribes to **485 rows / 84 tribes**. Pass B runs **first**, and is
exempt from the commercial blocklist, for the ownership reason in section 12.

---

## 14. The FTE measure, and its assumption stated in the open

```
FTE = total_hours_worked / 2080          2080 = 40 hours x 52 weeks
```

**2080 is a CONVENTION, not a measurement** — the federal FTE divisor (OPM, and
the same divisor BLS uses). Two biases run in opposite directions and do not
cancel:

- OSHA 300A `total_hours_worked` is **all hours worked by all employees,
  including overtime** → inflates FTE above true full-time staffing.
- It **excludes paid leave, holidays and sick time** → a salaried full-timer with
  three weeks off books ~1,960 hours and scores 0.94 FTE.

**Measured on the 485 staged rows**, which is the useful part:

| | |
|---|---:|
| median hours per employee | **1,702** |
| median FTE / headcount | **0.818** |
| p10 – p90 of that ratio | 0.594 – 1.000 |

FTE runs **below** headcount, as predicted for a part-time-heavy casino floor,
and 4wheeler measured 1,859 independently. **The ratio is the interesting
quantity — it is a staffing-mix measure, not an error.**

Rows outside 200–5,000 hours per employee are **flagged, not fixed** (10 of
485). 4wheeler's examples of why: Central Valley Indian Health filed 122
employees against 500 total hours; "Choctaw Casino Amenity Refresh" filed 19
employees against 117,335 hours — a construction project booking contractor
hours against a casino establishment.

`fte_2080` is **derived, not filed**. It travels in its own column and must
never enter an `employment` column.

---

## 15. OSHA ITA disclosure limits — these travel with every figure

**OSHA ITA is not a census, and its silences are not zeros.**

- **Electronic submission is required only of establishments above size
  thresholds in covered industries**, and compliance is uneven. Coverage is a
  property of the filing rule and of the filer, not of the industry.
- **AN ESTABLISHMENT ABSENT FROM ITA IS NOT AN ESTABLISHMENT WITH ZERO INJURIES,
  AND NOT ONE WITH ZERO EMPLOYEES.** It is an establishment that did not file.
  This is the same shape as the QCEW suppressed cell published as `0` in section
  3 — an absence that renders as a number.
- **The set of establishments filing under one tribe changes year to year.** A
  tribe-year SUM is therefore **not a consistent panel** and must never be
  differenced as though it were. Every row carries
  `DO_NOT_SUM_ACROSS_YEARS_WITHOUT_A_BALANCED_PANEL`.
- **Self-reported.** The employer files its own 300A.
- Cedar's four-state vocabulary applies: a non-filing establishment is
  `NOT_FOUND`, never `PUBLISHES … 0`.

---

## 16. The merge, written and ready — `code/158_merge_staged_labor_employment.py`

**Written 2026-08-26 and deliberately not run.** Both rulings are settled; the
only blocker is a **concurrent writer**, verified at 17:16 — another agent had
written `gaming_facility_metrics.csv` (17:12), `gaming_properties.csv` (17:15),
`07n_gaming_employment.csv` (17:16), grown `gaming_facilities.csv` 774 → 784, and
had `121_pull_subawards_api.py` live.

```
py -3 code/158_merge_staged_labor_employment.py --check    # read-only
py -3 code/158_merge_staged_labor_employment.py --merge    # refuses if not clear
```

`--merge` **refuses on its own** if any watched gaming table moved in the last 30
minutes. Verified working: it refused, and the target is byte-untouched.

### What the merge does, in the order it must

1. **Backs up first.** 769 is asserted in `docs/GAMING_EMPLOYMENT_LOG.md`.
2. **Re-reads the target inside the write path**, never cached from earlier in
   the run, so a concurrent append is not clobbered.
3. **Adds `entity_level` to the incumbent 769 rows** — `facility` where
   `facility_id` is populated, `tribe` where it is not.
4. **Keeps the 317 duplicate-grain OSHA rows but flags them.** They are the same
   300A filing the existing 364-row layer already carries at facility grain. A
   tribe-level view is a different question from a facility-level one, so they
   are retained — but **any consumer that sums `OSHA_ESTABLISHMENT_REPORTED` and
   `OSHA_TRIBE_LEVEL_REPORTED` together without filtering on
   `already_facility_attached` double-counts 317 filings.**
5. **Never lets `fte_2080` into `employment`.**

Expected result: **769 + 2,531 = 3,300 rows**, and the employment layer stops
being the thin part of the collection.

After running: `py -3 code/62_no_regression_check.py`, restore the backup on any
FELL line.

### One thing not to misread in that gate

**The gate already fails, and it is not this work.**
`codebook_undocumented_public = 65` belongs to `07o_nigc_declinations` (45) and
`04d_fr_ex_parte_*` (20) — datasets written by scripts 154/155,
`codebook_master.csv` last written 17:16 by the concurrent agent. Nothing here
touches the codebook or those datasets. **Compare the metric before and after
the merge rather than reading the failure as caused by it.** Recorded so the
next reader does not spend an hour on someone else's open item.

---

## 17. What is left unresolved, honestly

| | rows | why |
|---|---:|---|
| `unresolved` | **1,863** | mostly commercial operators not on the blocklist, plus brands absent from `gaming_facilities.csv` |
| `blocked_not_leading` / `blocked_remainder` | 137 | genuine tribal properties whose filed name embeds identity tokens — e.g. `Puyallup Tribe of Indians Emerald Queen Hotel & Casinos`, correct but refused because "emerald queen" sits in the remainder |
| `blocked_class` | 17 | a CDFI / UIO / school cannot own a casino |
| `candidate_review` | 3 | trap-only core: `Cherokee Nation Entertainment LLC`, `Little River Casino Resort`, one more |

All of it is in `review/osha_gambling_unresolved_2026-08-26.csv` with a
`verdict`, a `reason`, and a `proposed_tribe_id` where one was computed and
refused. **Nothing was guessed.**

**The cheapest next win is visible in that file:** the ~137
`blocked_not_leading` / `blocked_remainder` rows are largely real tribal
properties whose brands are simply missing from `gaming_facilities.csv`. Adding
those brands to the facility table — which is a *facility-universe* improvement
worth having on its own — would attach them on the next run of 157 with no new
matching logic at all.

---

## 18. Provenance for Part II

- **No network calls.** `_gambling_naics_rows.csv` was already on disk.
- **`Desktop/4wheeler` still untouched** — Part II reads only Cedar files.
- **Nothing in `data/clean/` was written.** `gaming_employment_observations.csv`
  is byte-identical to its 2026-08-07 state.
- Code changed: `code/cedar_domain.py` (two enum members + their membership),
  `code/156_*` (rulings applied), `code/157_*` (new), `code/158_*` (new).
- Outputs: `data/staging/gaming_employment_osha_tribe_staged.csv` (485),
  `review/osha_gambling_unresolved_2026-08-26.csv` (4,577),
  `logs/157_osha_tribe_2026-08-26.log`, `logs/158_merge_2026-08-26.log`.
