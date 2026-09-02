# Gaming property employment observations — build log

*Built 2026-08-07. Script: `code/100_finish_declinations_and_employment.py`
(steps `osha`, `geocode`, `lodes`, `build`). Output:
`data/clean/gaming_employment_observations.csv`, **769 rows**. Cedar Press.*

---

## 0. The one thing to carry away

**Four sources measure four different things, and none of them is "how many
people work at this casino."**

| source | what it actually counts |
|---|---|
| OSHA ITA 300A | the **establishment's own filed** annual average employees |
| Census LODES WAC | **all jobs whose workplace is a census block**, whoever the employer |
| Environmental review | what a planner **expected** a project to employ |
| Official document | a figure **an agency printed**, on the date it printed it |

They are all retained, each with its own `measurement_type`, and **none is
reconciled into a preferred number.** Cedar may derive a preferred observation
later; the underlying values stay.

The measured proof that reconciling them would be wrong: **52 properties carry
both an OSHA figure and a LODES figure. The median LODES/OSHA ratio is 0.385,
16 of the 52 are below 0.1, and 12 are above 1.0.** A single "employment" column
would have had to pick, and either pick would be wrong for most of the file.

---

## 1. What was built

| measurement_type | rows | properties |
|---|---:|---:|
| `LODES_BLOCK_WORKPLACE_JOBS` | **384** | 384 |
| `OSHA_ESTABLISHMENT_REPORTED` | **364** | 92 |
| `PROJECTED` | **20** | 2 with a facility, 10 tribes |
| `ENVIRONMENTAL_REVIEW_COUNT` | **1** | 1 |
| **total** | **769** | **425 properties, 198 tribes** |

**53 properties carry two independent measurement types.** None carries three —
the OSHA and LODES layers overlap on 52 properties, and the environmental-review
layer touches almost none of the same properties because it is about projects
that are proposed, not operating. That is the shape of the evidence, not a gap
in the build.

`observation_id` prefixes name the source family: `EMP-OSHA-`, `EMP-LODES-`,
`EMP-DOC-`, `EMP-EA-`.

---

## 2. OSHA ITA — the only source that is an employer's own count

`data/raw/external/osha_ita/`, ten annual files CY2016–CY2025, retrieved from
`https://www.osha.gov/itadata` with a manifest carrying md5 and byte count on
every object. **3,189,050 establishment-year rows**, of which **5,062** are in a
gambling NAICS (`7132*`, `721120`).

| | |
|---|---:|
| ITA rows attached to exactly one Cedar property | **364** |
| — by exact normalised establishment name + state | 360 |
| — by token-set equality + state | 4 |
| distinct properties | **92** |
| distinct establishment names | 102 |
| properties with 5+ years of OSHA filings | **39** |
| properties with all 10 years | 3 |
| employment range | 21 … 7,449 (median 630) |

Rows per year are stable at 31–45, so this is a genuine ten-year panel for the
properties it covers rather than a single snapshot.

### 2.1 Matching is name equality, in both tiers

**No containment, no fuzzy matching, no coordinate proximity.** Tier 1 is exact
normalised name plus state agreement. Tier 2 is **token-set equality** plus
state — `Casino Resort Barona` and `Barona Resort & Casino` are the same
multiset of words. Containment would also have accepted bare `Barona`, which is
a different claim, and containment is what booked $2.8B onto a school in this
project's own history.

### 2.2 The same figure filed under two property names is ONE figure

**Six observations are flagged `IDENTICAL_VALUE_FILED_UNDER_n_PROPERTY_NAMES_
SAME_TRIBE_YEAR`.** The clearest case is Salt River: `Casino Arizona` and
`Talking Stick Resort` both report **3,331** employees for CY2016. That is one
enterprise-level filing submitted under each property's name, not two
independent property counts.

**It is flagged, not merged and not divided.** Merging would destroy a real
observation; dividing would invent one. The flag lets a user decide, and it is
exactly the five-legal-persons problem showing up in employment data: the
*enterprise* filed, and the filing carries two *property* names.

### 2.3 What ITA cannot tell us

- **It is not a census of casinos.** 2,819 gambling-NAICS establishment-years
  share no distinctive token with any Cedar property — the whole commercial
  industry, Las Vegas and riverboats included. They were never candidates.
- **1,879 rows (711 distinct establishments) share a distinctive token with a
  Cedar property but do not match by name.** They are staged in
  `review/employment_osha_unmatched_2026-08-07.csv`, **one row per
  establishment** with its year span and value series, not one row per
  establishment-year — a queue that asks for the same ruling ten times stops
  being used.
- **Coverage depends on OSHA's electronic-submission rule, on whether the
  operator files under the property's name or the enterprise's, and on the
  tribe's posture toward OSHA jurisdiction over tribal enterprises**, which is
  contested and varies by circuit. **Absence from ITA is a property of ITA.**
- It is a **filing**, not an audited count.

---

## 3. Census LODES — block, never tract

688 facilities carry coordinates. Each was geocoded to its **2020 census block**
through the Census geocoder (`geocoding.geo.census.gov`, 685 of 688 resolved),
and LODES8 WAC `S000 JT00` was pulled per state.

**Block, not tract, and the reason matters.** A tract is large enough that "jobs
in the tract" says almost nothing about one employer. A block is tight enough to
be informative and *still* is not casino payroll whenever another employer
shares it. Both sentences ride on every row in `measurement_note`, and the flag
`BLOCK_JOBS_ARE_NOT_PROPERTY_PAYROLL` is set on all 384.

`CNS17` (Arts, Entertainment and Recreation) and `CNS18` (Accommodation and Food
Services) are carried alongside `C000` so the industry mix of the block is
**visible rather than assumed**.

### 3.1 The two states LODES does not have, and the trap that hid one

- **Alaska has never participated in LEHD.** No WAC file exists for any year.
- **Michigan stops at 2021.** `mi_wac_S000_JT00_2022.csv.gz` returns HTTP 404
  while 2021, 2020 and 2019 all return 200. Michigan holds 39 Cedar properties,
  so treating one national vintage as universal would have dropped them
  silently. The pull now walks back to the newest year each state actually
  publishes and records which vintage it used: **2022 for 30 states, 2021 for
  Michigan.**

**The trap:** Alaska's 404 page, saved under a `.gz` name, is **32 KB** — large
enough to pass any file-size test, and it fails only when gzip tries to read it.
This is AGENTS.md's *"check the HTTP status, not the file"* in a new costume.
The pull now checks **the status code AND the gzip magic bytes**, two
independent tests, and renames anything that fails to `.NOT_A_GZIP` rather than
leaving a poisoned file in the cache.

### 3.2 301 properties whose block carries no jobs at all

301 geocoded facilities sit in blocks that do not appear in the WAC file at all.
**That is recorded as an absence and never written as a zero.** Either the block
genuinely has no allocated workplace jobs, or — far more likely — the geocoded
point falls on a parking lot, an access road or a parcel centroid one block over
and the jobs sit next door. A zero would be a claim; the absence is a fact about
the join.

### 3.3 The 52-property comparison, which is the argument for keeping both

| | |
|---|---:|
| properties with both an OSHA and a LODES figure | **52** |
| median LODES ÷ OSHA | **0.385** |
| LODES below 10% of OSHA | 16 |
| LODES at or above OSHA | 12 |

LODES is usually well below the establishment's own count and sometimes well
above it. Below is the block-boundary problem; above is a block that holds a
resort, a hotel, a truck stop and a tribal administration building. **Neither
direction is an error to be corrected. They are two different measurements, and
the file says so on every row.**

---

## 4. Environmental reviews and official documents

330 official PDFs already on disk — BIA two-part determinations, records of
decision, FONSIs, environmental assessments, state regulator reports — were
scanned for employment sentences. Extracted text is cached under
`data/raw/external/_pdf_textcache/` so a rerun costs nothing.

**11 observations attached; 4 held for a ruling; 10 further projections carried
from `gaming_projections.csv`.** Small, and deliberately so — every guard below
was bought by a bad row in an earlier pass:

1. **A projected figure is not an operating one.** Tense and modality decide:
   *expected / anticipated / projected / estimated / would / will create* →
   `PROJECTED`; *employs / employed / currently employs* in an environmental
   review → `ENVIRONMENTAL_REVIEW_COUNT`. `cedar_domain.may_promote()` refuses
   `PROJECTED → ACTIVE_FLOOR_COUNT` and the refusal is **asserted in code**, not
   trusted.
2. **Construction, indirect and induced jobs are excluded.** They are not
   property employment. A resort projected to "create 2,441 jobs" in
   construction is not a resort that employs 2,441 people.
3. **Ranges are refused.** *"Creation of 315 to 1,298 new jobs"* was published
   as **1,298** before this guard — taking the upper bound presents the most
   flattering number in the source as if the source had stated it alone.
4. **Chart furniture is not prose.** `$647,995 $0 GAMING HOTEL FOOD & OTHER DEPT
   ADMIN MARKETING ... ■WAGES ■TIP INCOME` extracted as a "sentence" and yielded
   a number. Money symbols and box glyphs mark tables and figures.
5. **More than one multi-digit number in a sentence means the attachment of the
   number to the noun is a guess.** Refused.
6. **A document's tribe is not the sentence's tribe.** *"Legends Casino employs
   over 700 people"* appears inside a **Colville** environmental document as a
   comparison case. Legends is **Yakama's**. Falling back to the document's own
   tribe booked another nation's casino to Colville. The fallback now applies
   only when the sentence names no specific property; if it names one and that
   name does not resolve to a Cedar facility, the row is **held**, not guessed.

### 4.1 Property attribution, and the direction that is defensible

The **whole facility name must appear in the sentence**, and at least one of its
tokens must be distinctive. *"The Ojibwa Casino Resort employs 359 individuals"*
can attach to a facility named *Ojibwa Casino* because every token of the
facility name is present and `ojibwa` is not a generic gaming word. The opposite
direction is refused outright: a sentence saying only *"the Casino"* attaches to
nothing, and a facility whose only matching token is `casino` attaches to
nothing. This is AGENTS.md's rule that **the record must be at least as specific
as the entity**, applied to property names.

The surviving operating counts are worth naming because they are the rarest kind
of row in this file: *"Currently, approximately 55 people are employed at the
existing Osage Nation Ponca City Million Dollar Elm Casino"* (attached to
`VP-0199`).

---

## 5. What is deliberately NOT in this file

- **Casino City's `employees` column.** `gaming_facilities.csv` carries **323**
  vendor employee values. Casino City is licensed, is QA-only, and may never
  publish — the same rule as DUNS. The count is printed by the build so the
  omission is **visible rather than silent**.
- **Any property-level gaming revenue.** None is produced, derived or implied
  anywhere in this script. Employment is not converted into revenue and revenue
  is not converted into employment.
- **A preferred or blended employment number.** There is no model here, so there
  is nothing to blend with.
- **Confidence intervals.** `confidence` is `high`/`medium`/`low` and is a
  handling instruction, not a probability. A factual bound is not a confidence
  interval.

---

## 6. Pull discipline

Three hosts, three locks, one poller each, all released on completion:
`logs/_HOSTLOCK_www.osha.gov.json`,
`logs/_HOSTLOCK_geocoding.geo.census.gov.json`,
`logs/_HOSTLOCK_lehd.ces.census.gov.json`.

Sequential requests with a floor gap (2.0 s OSHA, 0.35 s geocoder, 1.5 s LEHD),
checkpoints written before the first request (the geocoder step flushes every 25
facilities and resumes from what is already held), and a manifest with HTTP
status and md5 on every object. **`api.usaspending.gov` was not touched — it is
edge-blocking us and another agent holds its lock.** No throttling or refusal
was observed on any of the three hosts used.

---

## 7. What this layer structurally cannot tell us

1. **No source here is a census.** OSHA covers filers, LODES covers blocks,
   environmental reviews cover projects under review. A property with no row is
   a property no source covered — not a property with no employees.
2. **Nobody publishes tribal casino payroll by property.** There is no
   authoritative property-level employment series to check any of this against,
   which is exactly why several independent observations are worth more than one
   reconciled number.
3. **OSHA employment is self-reported and is an annual *average*.** A seasonal
   property and a steady one with the same average are not the same employer.
4. **LODES is noise-infused by design** for disclosure avoidance, and its
   geography is the block a geocoder chose, not a parcel boundary.
5. **The environmental-review layer describes projects, and a project is not a
   property.** Some were built at a different size, some later, some not at all.
6. **The panel is only as long as the source.** OSHA begins CY2016; LODES8 goes
   back to 2002 but only 2021–2022 was pulled. Earlier LODES vintages are a
   cheap extension and are the obvious next action on this layer.
