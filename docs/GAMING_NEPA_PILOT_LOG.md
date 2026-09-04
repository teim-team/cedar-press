# Gaming Development & Markets — Phase 2: NEPA document extraction pilot

*Run 2026-08-05. Scripts `code/32a`–`32b`. Console log: `logs/32_gaming_nepa_pilot.log`.*
*Plan: `docs/plans/GAMING_DATASET_PLAN.md` phasing step 2. Phase 1: `docs/GAMING_BUILD_LOG_2026-08-05.md`.*

Two document sets only, exactly as the plan scopes the pilot. **No bulk extraction was run.**

---

## What was built

| File | Rows | What it is |
|---|---:|---|
| `data/clean/gaming_project_facilities.csv` | 19 | Table 1 — one row per development **alternative per program source** |
| `data/clean/gaming_projections.csv` | 116 | Table 2 — one row per project × metric × geography × period |
| `data/clean/gaming_mitigation_agreements.csv` | 24 | Table 3 — mitigation & intergovernmental agreements |
| `data/raw/external/gaming_nepa/` | 24 docs | Retrieved PDFs + `_SOURCE_MANIFEST.csv` |

`entity_id` is blank on every row. Spine linking was out of scope and is not guessed.

---

## Retrieval

**24 of 24 documents retrieved, HTTP 200, first attempt.** 198,330,824 bytes, 2,837 PDF pages.
Plain `urllib` with a declared User-Agent was sufficient — bia.gov never 403'd, so
the curl fallback coded into `32a` never fired. Phase 1's robots.txt evidence holds:
`/as-ia/*` is permitted, and the PDFs sit on the same host under
`/sites/default/files/media_document/`.

URLs were read out of `data/clean/gaming_land_decisions.csv` rather than typed, so
the provenance chain from the BIA index to the bytes on disk is unbroken.

`_SOURCE_MANIFEST.csv` carries, per document: project_id, decision_id, local file,
source URL, BIA's own document label and the Phase 1 document type, HTTP status,
bytes, SHA-256, content type, **page count**, and retrieval date.

### The size asymmetry is the scaling fact

| | Osage Lake Ozark | Menominee Kenosha |
|---|---:|---:|
| Documents posted | 3 | 19 (+ project page) |
| Total bytes | 5.2 MB | 193 MB |
| Total PDF pages | 86 | 2,751 |
| Main EA | 83 pp | 72 pp |
| Largest appendix | — | Appendix TIA, **1,297 pp / 44.6 MB** |

The plan predicted "main documents are bounded, appendices are tonnage." Confirmed
precisely: the two EA bodies are 83 and 72 pages, and 96% of the Menominee tonnage
is in appendices. Appendix GRADE is 505 pp, HAZMAT 225 pp, IGA 214 pp, BIO 187 pp.

---

## A. Osage Lake Ozark — the clean single-document test

**It is clean, and it is also the weaker of the two documents**, for a reason the
plan did not anticipate.

### What extracted cleanly
- **Alternative A** in full: 29 acres, 40,000 sf gaming floor, 750 Class II gaming
  devices, 237,160 sf total, 150 hotel rooms, 435 parking spaces, 6,000 sf meeting
  rooms, 24/7 operation, construction commencing 2025 over 12–18 months. From EA
  Table 2 plus the Section 2.1 narrative.
- **Alternative B** (100-room hotel, no casino, ~150 stalls) and **Alternative C**
  (No Action) as their own rows.
- **Four alternatives eliminated from consideration** — Reduced Intensity, Increased
  Intensity, Class III Gaming Facility, Off-Site Development — carried as rows with
  the stated reason and no quantities. The road not taken is in the file.
- Table 26 is the operating-assumption goldmine the plan promised: **1,760 average
  daily patrons, 128 average daily occupied rooms**, with per-unit GPD factors.
- Trip generation **7,448 daily trips** on 750 slot machines (EA Table 22).
- Fiscal: **$56,840/yr property tax forgone**, 0.5% of the Miller County budget.
- Substitution: **$1.8M** from the Isle of Capri Boonville in year one declining to
  zero; **9,900 room nights**, 1.5 occupancy points and $1.1M from the local hotel market.
- A named **$50,000/yr, 3-year Sheriff's agreement** effective on casino opening.

### What did not extract, and why it matters
**None of the Osage EA's ten appendices (A–J) are posted.** BIA published three
documents for this project: the Notice of Availability, one aerial-photograph
exhibit, and the 83-page EA body. Appendix C — *Economic and Fiscal Impacts of Osage
Development Alternatives on the Region and State* — is cited on nearly every
socioeconomic page and **is not available**. Consequences:

- **Zero competitor-methodology reconnaissance for Osage.** No model named, no
  geographies, no substitution or local-capture assumptions. The EA's Section 5.4
  names Acorn Environmental and Montrose Environmental as environmental consultants
  and CJW Transportation Consultants as the traffic/grading subconsultant, but
  **never names the author of the economic and fiscal impact study**.
- Appendix E (Traffic Impact Assessment) is likewise unavailable; only the summary
  tables in the EA body survive.
- **No construction cost anywhere in the document.** Not disclosed. Nor a projected
  opening date.

### Contradictions preserved, not resolved
1. **27.6 vs 29 acres.** The BIA Notice of Availability for this EA says
   "approximately 27.6 acres"; the EA says "approximately 29-acre Project Site" in
   three places. Both are in Table 2 with their pages.
2. **455 jobs is direct, or total, depending on the page.** p.11 calls it "full and
   part-time direct and permanent"; p.48 calls the same number "direct, indirect and
   induced"; p.49 makes it the county share of 510 statewide. Flagged
   `confidence=medium` and left ambiguous, because the source is ambiguous.
3. **Table 26's hotel cells do not reproduce from its own factors.** 128 rooms ×
   175 GPD = 22,400, but the table prints 22,313; 128 × 150 = 19,200, but the table
   prints 19,125. The casino cells reproduce exactly. Table values recorded verbatim;
   the arithmetic gap is noted, not corrected. (Alternative B's cells reproduce
   exactly, so this is specific to the Alternative A hotel column.)

---

## B. Menominee Kenosha — the stress test

The stress test is where the schema actually broke, and it broke in a productive way.

### The finding that matters: one alternative, four programs

Alternative A of the Menominee project exists in **four separately-sourced
descriptions that do not agree**:

| Source | Date | Gaming sf | Total sf | Slots | Tables | Rooms | Parking | Meeting sf | F&B seats |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EA body p.15 | 2026-03 | 70,000 | **346,000** | 1,500 | 55 | 150 | 2,400 | — | — |
| Appendix PROJ DESC Table 1 | 2026-03 | 70,000 | **358,350** | 1,500 | 55 | 150 | 2,400 | in HR Live | **750** |
| City IGA Exhibit E ("approved concept program") | 2024-01-03 | 70,000 (incl. support) | — | 1,500 | 55 | 150 | **2,375** | **18,375** | **752** (sum) |
| Appendix SOCIO assumptions (KlasRobinson) | 2023-11-01 | — | — | 1,500 | 55 | 150 | **2,375** | **8,509** | **782** (sum) |

The machine and table counts are stable across all four. **Nothing else is.** The
EA body also says the casino is "up to 95,000 sf" where its own appendix totals the
casino at 106,000 sf. Acreage is 59 in the EA and "approximately 60" in the IGA.

**This is not noise to be averaged away — it is the dataset's product.** A
directory that reports a single square-footage for this project is reporting one
arbitrarily-chosen document. Cedar Press carries all four with `record_type` ∈
{`ea_body`, `ea_appendix_program`, `iga_exhibit_program`, `impact_study_assumption`}
and lets the user choose.

### Stage tracking earns its keep immediately
The City IGA Exhibit E program is recorded `observation_status=approved` with date
2024-01-03 — **approved by the counterparty government, not by BIA**, which still
lists the project Pending. That is a genuine intermediate stage the four-value
vocabulary {proposed, approved, built, current} does not cleanly name. See schema
findings below.

### The 2013 ROD is inside the 2026 EA
Section 2.6 and Table 3 compare the current proposal against the **2013 Record of
Decision for the 223-acre Dairyland Greyhound Park site**: 107,300 sf gaming,
400-room hotel, 5,000-seat entertainment venue, versus 70,000 sf / 150 rooms /
2,000 seats today. A **35% cut in gaming floor and a 62% cut in hotel keys** across
one project's two federal attempts, in a single table. Carried as project_id
`MENOM-KENOSHA-DGP-2013` (3 alternative rows), every row flagged **SECOND-HAND** —
the 2013 ROD/FEIS itself was not retrieved and must be extracted directly before
these figures are treated as primary. Note that the 2013 "Alternative C" is a
different site entirely (Keshena, on-reservation).

### Appendix SOCIO is the competitor-methodology jackpot
**KlasRobinson Q.E.D.** (James M. Klas and Matthew S. Robinson, Minneapolis MN),
*Economic Impact Study*, 1 November 2023, engaged 12 June 2023 by the Menominee
Kenosha Gaming Authority. Captured in full:

- **Model: IMPLAN**, named, with the firm's own description of how it treats
  indirect vs induced effects and its three output levels (output, employment,
  earnings).
- **Geographies: Kenosha County and State of Wisconsin**, reported separately at
  every level.
- **Substitution assumption stated as an assumption**: "we anticipate that an
  additional 0.8 percent of new spending at the subject complex will be substituted
  from spending that would have occurred at other businesses" — an assumption
  "based upon our analysis of the market and our experience," i.e. judgmental.
- **Local capture** given explicitly: 6.6% of spending from Kenosha County, 31.2%
  from the rest of Wisconsin, 62.3% from outside the state; in-state vendor share
  of purchases 56%.
- **Named competitors with dollar cannibalisation by year**: Potawatomi Milwaukee
  ($21.6M in year 1 decaying to $7.3M by year 5), Ho-Chunk Madison ($649K to zero).
- **A reasonableness benchmark table**: employees-per-gaming-position for 10+ named
  regional casinos (FireKeepers 0.42, Potawatomi 0.96, MGM Grand Detroit 1.71,
  Gun Lake 0.36 …), against which the project's 0.57 is defended.
- The report states on its own transmittal page that it "is intended … for use in
  **public relations and lobbying efforts**." That sentence belongs in any
  publication that quotes its numbers.
- Its **social-cost literature review** (Shaffer & Martin 2011; Ohio, Springfield
  MA, Baltimore, South Bend, Bowling Green case studies) is a reusable map of what
  gaming impact consultants cite.

**The full → net → competitive cascade** is captured as separate metric families
(`economic_output_full` / `economic_output_net`, ditto employment and earnings), so
a user can never accidentally quote the gross figure as the net one.

**Output is never labeled revenue.** Every modelled-output row carries
`impact_type=operational_modelled` and a note reading "MODELLED OUTPUT, NOT GAMING
REVENUE." The one genuinely revenue-shaped series — the consultant's projected
$258.9M–$293.1M property revenue by year — is labeled
`metric=projected_property_revenue` with "CONSULTANT PROJECTION, not observed
revenue" on every row.

### Appendix IGA is a mitigation-agreements dataset on its own
214 pages containing three executed agreements. 17 Menominee rows in Table 3,
including terms no directory carries:

- **City of Kenosha (2024-01-03)**: 3% of Net Win, quarterly, with a minimum-payment
  floor stepping $100K → $1M → $2.5M CPI-indexed; $1M for two advanced life support
  vehicles; $500K/yr × 6 for a fire/police/public-works outpost; $500K/yr × 10 for a
  museums trust and homeownership program; $750K to schools in any year Net Win
  payments exceed $2M; a 3% local/minority contractor bid preference; a 25% minority
  employment goal.
- **Kenosha County (Feb 2024 per the EA)**: 1% of Net Win rising to 1.33% in year 9;
  minimum floor $50K → $500K → $1M CPI-indexed; $650K/yr × 4 for human-services
  building debt service; problem-gambling match; $850K cumulative charitable minimum;
  and **75% of the tribe's own sales tax remitted to the county for eight years,
  then 25%**.
- **Kenosha Area Tourism Corporation (2024-01-10)**: **90% of room tax**, monthly,
  in perpetuity while a hotel operates, with the tribe obliged to set its room tax
  equal to the City's.
- Two **exclusivity covenants running the other way** — City and County each agree
  not to endorse or license any competing Class III facility. Table 3 as specified
  assumes payments flow tribe → government; these rows flow government → tribe and
  are marked `amount_basis=non_monetary_commitment`.

Contradictions preserved: the County agreement's problem-gambling clause caps the
tribe's commitment at **$75,000 total**, while the EA summarizes it as "up to $75,000
**per year**." The agreement text is recorded; the EA's reading is in the note. The
County agreement reproduced in the appendix is an **unexecuted template** reading
"this [DATE] day of [MONTH], 2023" — the February 2024 date comes only from the EA's
narrative, and `date_basis` says so.

### Menominee internal conflicts, preserved
- **Visitor origin**: the table (p.23) gives 1,490,500 visits from outside Wisconsin
  and its three components sum exactly to the 2,443,400 total; the executive summary
  (p.11) says "almost 1,623,000." The table is internally consistent, so the summary
  is the outlier — but neither is corrected.
- **Daily visits**: the study states "almost 6,995 visits per day" alongside 2,443,400
  annual visits. 2,443,400 ÷ 365 = 6,694. Cedar Press emits the calculated 6,694 with
  its derivation and notes the source's own conflicting figure.
- **Gaming positions**: 1,830 in the TIA (1,500 machines + 330 table seats) vs 1,885
  in the impact study (a different way of counting 55 tables). Both recorded.
- **Wisconsin net earnings total** is cut off in the source PDF's text layer.
  Components read cleanly; the total is left **blank** at `confidence=low` rather than
  summed, because summing it would be Cedar Press inventing a source figure.

### Skipped, per the plan
No comment corpus is posted for either project, so nothing was skipped on that
ground. Appendices ACRO, AIR, BIO, CULTURAL, GRADE, HAZMAT, LAND RES, NIGC, REF, REG
were **retrieved and manifested but not extracted** — they carry regulatory,
biological and geotechnical content outside the three tables. Appendix TIA (1,297 pp)
was **not extracted directly**; its summary tables were taken from the EA body, which
reproduces trip generation for all three alternatives with exhibit-level citations.
Extracting TIA itself would add turning-movement detail and is deferred.

---

## Reported vs calculated — the count

| | n |
|---|---:|
| `reported` | 108 |
| `calculated` | 8 |

All 8 calculated rows carry their arithmetic in `derivation` and a note beginning
"CEDAR PRESS CALCULATION" or "CEDAR PRESS SUM":

| project | metric | value | derivation |
|---|---|---:|---|
| Osage | annual_visits | 642,400 | 1,760 patrons/day × 365 |
| Osage | implied_hotel_occupancy (Alt A) | 85.3% | 128 ÷ 150 rooms |
| Osage | implied_hotel_occupancy (Alt B) | 85.0% | 85 ÷ 100 rooms |
| Osage | food_and_beverage_seats_total | 264 | 60 + 150 + 24 + 30 (lower bound; two venues "TBD") |
| Menominee | implied_mean_daily_visits | 6,694 | 2,443,400 ÷ 365 |
| Menominee | implied_win_per_position_per_day | 401.5 | $276.25M ÷ 1,885 positions ÷ 365 |
| Menominee | food_and_beverage_seats_total (SOCIO) | 782 | 675 + 107 |
| Menominee | food_and_beverage_seats_total (IGA) | 752 | 150 + 250 + 87 + 95 + 170 |

A third category emerged that the plan's binary does not cover: figures the **source
document itself derives** and prints — Osage's "455 × 40% = 182 in-migrating school
children," Menominee's "4% × $259M Net Win = $10.4M." These are `reported` (they are
printed in the document) but carry the source's own arithmetic in `derivation`. They
are not Cedar Press calculations and must not be attributed to us.

---

## Schema findings — what the pilot proves needs changing

1. **Table 1 needs a `record_type`, because one alternative can have several
   programs.** Menominee Alternative A has four. Without it, either three documents
   get silently dropped or the row becomes a lie. Added.
2. **`observation_status` needs a fifth value, or `observation_status` needs a
   companion `approving_body`.** The Menominee City IGA program was *approved by the
   City of Kenosha* in January 2024 while BIA still lists the project *Pending*.
   Neither "proposed" nor "approved" is honest without naming who approved it. The
   pilot uses `approved` plus an explicit note; a `status_authority` column is the
   right fix at scale.
3. **Table 1 has no reported/calculated flag.** Table 2 does; Table 1 does not, so a
   summed field (F&B seats) cannot be honestly stored there. The pilot's workaround —
   store only reported values in Table 1 and push every sum into Table 2 as a
   calculated row — works and should become the rule. `value_completeness` was added
   to say in words what a row does *not* contain.
4. **Table 1 needs `alternative_role`** ∈ {analyzed, eliminated_from_consideration}.
   Six eliminated alternatives across the two projects are named but unquantified;
   without the flag they read as data-entry failures rather than as the decision
   record they are.
5. **Table 1's specified columns miss real capacity classes.** Added
   `table_game_seats`, `entertainment_sqft`, `entertainment_seats`, `gaming_class`.
   Table game *seats* (330) and table *count* (55) are different quantities and the
   traffic model uses the former.
6. **`meeting_sqft` is ambiguous when meeting space is inside an entertainment
   venue.** Menominee's ballroom is "included in seats in Hard Rock Live" in one
   document and 18,375 sf in another. Left blank rather than double-counted, with the
   reason in `notes`.
7. **Table 2 needs `modeling_basis`.** "Who modelled this and with what" is the
   competitor-methodology payload and has nowhere else to live. Also added
   `derivation` (for both Cedar Press and source-internal arithmetic), `alternative`
   (a projection belongs to an alternative, not just a project), and `page_label`
   (printed page ≠ PDF page in every one of these documents, by offsets of 3–5).
8. **Table 3's payment vocabulary is far richer than "amount".** Fourteen distinct
   `amount_basis` values appeared in two projects: percent_of_net_win, minimum_annual,
   conditional_annual, matching_capped, minimum_cumulative, share_of_tax, one_time,
   fixed_annual, service_rate_premium, in_kind_capital_works, non_monetary_commitment,
   not_yet_agreed, and more. A single `amount` string cannot be aggregated. Added
   `amount_basis`, `amount_value`, `amount_unit` alongside the human-readable `amount`.
9. **Table 3 needs `date_basis`** for the same reason the deals ledger does. The
   Menominee County IGA's date exists only in the EA's narrative; the agreement copy
   is an undated template.
10. **Table 3 needs `agreement_status`.** Osage has one executed agreement and four
    that are "in the process of negotiating" or "tentative." Recording them with a
    blank amount and no status flag would make them look like extraction failures.
11. **`source_page` must accept ranges and lists** ("91-93", "15; 49"). Values are
    routinely stated in two places with different wording, and both citations matter.
12. **A `project_id` for a superseded prior proposal at a different site is needed.**
    `MENOM-KENOSHA-DGP-2013` exists only because the 2026 EA summarizes it. The
    proposed-vs-built paper the plan wants depends on this linkage being explicit.

---

## Accuracy self-assessment — honest

**What I am confident in (high):** every facility quantity in Table 1 and every
reported figure in Table 2 marked `confidence=high` was read from a printed table
cell or an unambiguous sentence in the retrieved PDF, and carries its document, PDF
page, printed page label and table reference. Machine counts, square footages,
acreages, GPD figures, trip counts, dollar impact figures and every IGA payment rate
and threshold were re-read against the source text after first entry.

**What is medium confidence (8 rows):** figures where the source contradicts itself
(Osage 455 jobs; Osage 27.6 vs 29 acres; Menominee visitor origin; Menominee gaming
positions) or where a Cedar Press calculation rests on an assumption the source does
not endorse (annualising 1,760 patrons/day at 365 days in a market the EA itself
calls seasonal; implied occupancy).

**What is low confidence (5 rows):** the Wisconsin net-earnings total (illegible in
the source text layer, left blank); the $75,000–$125,000 human-services range the
consultant itself says cannot be separated from background variation; the
$1M Menominee hotel substitution figure, which is an assumption stacked on an
assumption; and `implied_win_per_position_per_day`, offered only as a scale check
because its numerator is total property revenue rather than gaming win.

**Errors I caught in my own work and fixed before shipping:**
- `implied_win_per_position_per_day` was first entered as 376; the correct quotient
  is 401.5. Every calculated row was then recomputed independently.
- Two Osage water/wastewater notes asserted that the table's hotel cells were the
  product of its stated per-unit factors. They are not (22,313 ≠ 128 × 175). The
  notes now report the printed cells and flag the gap.

**Residual risk.** Text-layer extraction from these PDFs is imperfect: the Osage EA
in particular interleaves figure-caption fragments and whitespace with body text, and
Menominee Appendix SOCIO's charts leak axis labels into the text stream (the
"1,622,900 / 15,600" fragment on p.24 is a mangled chart label, not data, and was not
recorded as a value). Every figure entered here was read in its surrounding sentence
or table, not lifted by pattern match, which is the mitigation. Anything a chart-only
figure would have contributed is simply absent rather than guessed.

**Not verified:** nothing in these tables was checked against any external source.
Cross-checking Menominee's proposals against Wisconsin compact machine caps, or the
2013 ROD figures against the 2013 ROD itself, is deliberately out of scope here.

---

## Effort per document — for pricing the backfill

Measured on this run, one operator with these scripts already written:

| Stage | Osage (3 docs, 86 pp) | Menominee (19 docs, 2,751 pp) |
|---|---|---|
| Retrieval + manifest | ~1 min (scripted, both projects together) | — |
| Text extraction | ~10 s | ~90 s (all appendices) |
| Locating the extractable sections | ~15 min | ~35 min |
| Reading and transcribing to schema | ~45 min | ~2 h 15 min |
| Cross-checking and conflict documentation | ~20 min | ~40 min |
| **Total analyst time** | **~1 h 20 min** | **~3 h 30 min** |

**Rule of thumb for scaling: ~1.5 h per single-document EA project, ~3.5–4 h per
project with a full separately-posted appendix set.** Retrieval and extraction are
free; **reading is the entire cost**, and it scales with the number of *distinct
documents carrying numbers*, not with page count. Menominee's 2,751 pages cost only
2.6× Osage's 86 because 2,200 of those pages are engineering plans, species lists and
zoning code with nothing for these three tables.

The better predictor is **appendix composition**: a project with a socioeconomic /
economic-impact appendix and an intergovernmental-agreements appendix costs roughly
3× one without. Of the two pilot projects, one had both and one had neither.

### What this implies for the 138-record decision list
The pilot cannot tell you what share of the list carries appendix sets — Phase 1
recorded 304 document URLs across 138 records, an average of 2.2 documents per
record, which suggests **most records look more like Osage than like Menominee**.
A defensible planning figure is:

- **~110 Osage-shaped records × 1.5 h ≈ 165 h**
- **~28 Menominee-shaped records × 3.75 h ≈ 105 h**
- **≈ 270 analyst-hours for the full backfill**, plus retrieval of roughly 6–10 GB.

Before committing to that, run the cheap diagnostic the pilot makes possible: fetch
HEAD/size and page counts for all 304 already-captured URLs (minutes of work) and
bucket the records by document count and total pages. That converts the estimate
above from a guess into a measurement.

### Where automation would actually pay
1. **Program tables** (Osage Table 2, Menominee Appendix PROJ DESC) are structurally
   regular — `pdfplumber.extract_tables()` recovered the Menominee program tables
   cleanly and could pre-fill Table 1 for review rather than transcription.
2. **The IGA payment clauses** are boilerplate across tribes and law firms (the City
   and County agreements here are near-identical in structure). A clause-level
   template would cut Table 3 time sharply.
3. **The consultant roster** (Section 5/6 "Preparers" in every BIA EA) is trivially
   harvestable and is a deliverable in itself — this pilot alone yields Montrose
   Environmental, Acorn Environmental, KlasRobinson Q.E.D., CJW Transportation
   Consultants, Eriksson Engineering Associates, Heartland Ecological Group, MSA
   Professional Services, Marnell Architecture, and Hard Rock International as
   developer-partner, with named individuals and years of experience.

**What will not automate:** the conflicts. Every one of the ten contradictions logged
above was found by reading two passages against each other. That is the value being
added, and it is the part that costs the hours.

---

## Coverage caveats — publish these

1. **The appendix lottery decides how much a project yields.** Osage and Menominee
   are both Two-Part Determination casino projects at the same NEPA stage, and one
   yields a full consultant methodology and three intergovernmental agreements while
   the other yields none, purely because of what BIA posted. Depth is not a property
   of the project; it is a property of the posting.
2. **Second-hand figures are marked and must stay marked.** The three 2013 ROD rows
   come from a summary table in a 2026 document. They are a pointer to the 2013
   record, not a substitute for it.
3. **Every economic figure in both projects is a consultant projection** commissioned
   by the applicant — in the Menominee case, by a report that states its own purpose
   as public relations and lobbying. Nothing here is an observed outcome.
4. **Proposed ≠ approved ≠ built** applies within a single project: Menominee's
   Alternative A appears at four different specifications across three years, and the
   only figures that held constant were the machine and table counts.
5. **Nothing has been reconciled to the compact layer or the facility directory.**
   Whether Wisconsin's compact permits 1,500 machines at a Kenosha facility is exactly
   the join the plan wants and is not attempted here.

---

## Next

1. Run the cheap page-count/size diagnostic across the 304 Phase 1 document URLs to
   bucket the backfill by cost.
2. Adopt the twelve schema changes above before any bulk run.
3. Retrieve the 2013 Menominee ROD/FEIS directly and replace the three second-hand
   rows with primary extraction — it is the pilot's clearest proposed-vs-proposed test
   case.
4. Harvest the preparers/consultants roster across the decision list as a standalone
   pass; it is nearly free and is its own dataset.
