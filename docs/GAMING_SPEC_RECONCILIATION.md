# Gaming Spec Reconciliation

*Two specs handed over 2026-08-07. They agree on nearly everything. This records
where they conflict, and the one decision that has to be made before any agent
runs.*

> ## ⚠ THREE NUMBERS ON THIS PAGE ARE SUPERSEDED. Flagged 2026-08-26.
>
> This document is not named as a companion by either gaming ordinance log, so it does not
> receive their corrections. It does now.
>
> - **:155 "321 tribes, 321 original ordinances, 834 amendments = 1,155 instrument rows."**
>   The arithmetic is right. **"321 tribes" is not.** Measured on
>   `data/clean/gaming_ordinances.csv`: **299 distinct `tribe_id`**, 55 rows with none, 314
>   distinct `tribe_name`. `docs/GAMING_ORDINANCE_BUILD_LOG.md:269-270` says so directly —
>   *"NIGC's 321 rows are not 321 distinct tribes."* 321 is the count of
>   `ORIGINAL_ORDINANCE` rows.
> - **:196 "284 of 321 tribes name a Tribal Gaming Agency; 397 distinct names."**
>   Superseded by `docs/GAMING_ORDINANCE_OCR_MERGE_LOG.md`: **973 rows, 307 tribes, 469
>   distinct names.** The OCR merge added the provisions that scanned ordinances were
>   hiding.
> - **:231 "2,046 of 6,774 tribal FAC records (30.2%) are `is_public = true`."**
>   Measured on `data/clean/fac_tribal_single_audits.csv`: **2,052 of 6,780 (30.3%)**.
>   `docs/GAMING_FINANCIAL_EXHAUST_BUILD_LOG.md:27` carries the same superseded 6,774.
>
> Full register: `docs/DOC_CONTRADICTIONS_2026-08-26.md`.

---

## THE CONFLICT: what is the property backbone?

**Spec A** — *"do not treat the gaming work below as a new dataset. Do not
create a second gaming-property universe. Do not assign new IDs to properties
that already have Cedar IDs."*

**Spec B** — *"Continue using the NIGC gaming-property universe as the primary
backbone"* and *"Casino City may be treated as a competitor whose feature
coverage we want to exceed, not as a source for Cedar."*

Both are right on their own terms. Together they are not satisfiable as written,
because of a fact neither spec states:

> **Our existing property universe IS Casino City derived.**
> 595 of 774 properties carry a `casino_city_id`. Facility IDs are literally
> prefixed `CCP-` (595), `VP-` (164), `TPL-` (15). All 64,181 capacity
> observations carry `source = Casino City Press gaming-property panel`.

So "preserve the existing universe" and "do not depend on Casino City" point in
opposite directions, and "make NIGC the backbone" is a third position again —
NIGC's map holds 490 locations against our 774, and the roster diff found
**140 NIGC properties we do not have** and **424 of ours not on NIGC**.

### The resolution

**Keep the IDs. Replace the evidence under them.** This satisfies both specs and
costs nothing already built:

1. **`CCP-`/`VP-`/`TPL-` IDs stay.** They are Cedar's stable keys and everything
   downstream — declination letters, land decisions, compacts, region
   assignments, triage traces — already joins on them. Migrating IDs would
   destroy the crosswalking that is the actual asset.
2. **Casino City becomes an internal QA layer only**, exactly like DUNS. It
   validates; it never publishes. Already enforced as a hard gate in
   `code/87_build_dataset_notes.py` (`LICENSED_SOURCE_FILES`), so the vendor
   panel gets no notes contract and therefore cannot ship.
3. **The PUBLISHED capacity layer is rebuilt from free official sources** —
   `data/clean/gaming_capacity_official.csv` already holds **6,027** such
   observations from state regulators. That file, not the vendor panel, is the
   product.
4. **NIGC is the backbone for IGRA COVERAGE, not for property identity.** It
   answers "is this a regulated gaming operation," which is what it is
   authoritative for. It cannot be the identity backbone because its 490
   locations do not cover our universe, and because a tribally owned casino
   operating outside IGRA never appears in it at all.

**The 140 NIGC properties we lack are the exception**: those get new Cedar IDs,
because they genuinely are not in our universe. They are staged in
`review/gaming_additions_2026-08-06.csv`, not yet appended.

---

## WHERE THE SPECS AGREE — treat as settled

| Principle | Status |
|---|---|
| One stable property ID; observations attach to it | already true |
| Never overwrite a historical observation | already true — 64,181 dated obs, 367 properties with 10+ yrs |
| Do not flatten tribe / gaming authority / enterprise / operator / brand | already the spine rule |
| Regional GGR is context and a CEILING, never property revenue | built — `nigc_regional_ggr.csv`, 198 region-years |
| No modelled property revenue in this phase | standing rule |
| Declination letters are a first-class source, not legal trivia | built — 327 letters, 113 source claims, 145 financing events |
| Proposed ≠ operating; authorised max ≠ active count | must be enforced in every new field |
| Source-claim provenance with verbatim supporting text | built — `gaming_source_claims.csv` |
| Multiple independent employment figures are a feature | not yet built |
| Free sources only | now binding |

---

## WHAT IS ALREADY BUILT — do not rebuild

```
gaming_facilities.csv                 774 properties, 101 columns
gaming_property_capacity_history.csv  64,181 dated obs  [VENDOR - internal only]
gaming_capacity_official.csv           6,027 obs        [OFFICIAL - publishes]
nigc_regional_ggr.csv                    198 region-years, FY2001-FY2025
nigc_region_assignments.csv            2,438 property-year assignments
nigc_declination_letters.csv             327 letters
gaming_source_claims.csv                 113 sourced claims
gaming_financing_events.csv              145 financing events
gaming_property_federal_traces.csv       774 properties scored by federal trace
gaming_property_universe_events.csv       10 universe events
gaming_land_decisions.csv                138 BIA decisions
compacts.csv / compact_terms.csv         707 compacts
gaming_properties.csv                    774 published property rows
```

Four region schema versions are recorded (FY2001-02, FY2003-07, FY2008-16,
FY2017-), including the case where **FY2002 Region I published 72 operations and
was restated as 47** — a boundary that moved while the name did not.

---

## THE GAPS, RANKED BY WHAT THEY ADD

1. **Compact terms as structured data** — device caps, table caps, revenue-share
   rates, reporting obligations. We hold 707 compacts and have not parsed their
   *terms*. Highest value, zero new access needed.
2. **Compact-derived revenue** — where a public payment and an invertible
   formula exist, `payment / rate` is **exact arithmetic, not an estimate**, and
   is publishable as `EXACT_DERIVED_FROM_STATUTORY_FORMULA`. This is the one
   route to real revenue figures that does not violate the no-estimation rule.
   **The revenue concept must be preserved exactly** — if the formula covers
   only Class III electronic net win, it is not total casino revenue.
3. **Digital gaming** — retail/mobile sportsbook, iGaming, platform providers.
   State regulators publish monthly handle and GGR. Entirely unbuilt.
4. **Device observations** — Class II/III mix, manufacturer relationships, fleet
   changes. The Class II/III split is **time-varying and unobservable per
   property** (a floor can be swapped), so it is a dated observation, never an
   attribute.
5. **Loyalty programs** — free from official sites, and a shared program is
   evidence of enterprise integration.
6. **Resort components** — hotel rooms, meeting space, venue capacity.
   Environmental reviews are the richest untapped seam and Casino City has none
   of it.
7. **Employment** — OSHA establishment, Census LODES at block level, EA figures.
   Keep all three; never force one number. LODES block jobs are not casino
   payroll when other employers share the block.
8. **Energy** — operating-scale signal only. **Never convert electricity into
   revenue**; hotel, convention and HVAC load move independently of gaming.

---

## THE RULES A GAMING AGENT MUST NOT BREAK

- Attach to existing `CCP-`/`VP-`/`TPL-` IDs. A new ID only for a property
  genuinely absent from our universe.
- A manufacturer or regulator using a different property name is an **alias**,
  not a second property.
- `AUTHORIZED_MAXIMUM` is never `ACTIVE_FLOOR_COUNT`.
- `PROJECTED_2500_DEVICES` never silently becomes `ACTIVE_2500_DEVICES`.
- A declination letter proves NIGC **reviewed** documents. It does not prove
  execution, closing, construction, opening, or continued operation.
- Absence from any source is a property of that source. NIGC covers Class II/III
  **on Indian lands** only.
- A factual bound is not a confidence interval. A confidence interval requires a
  model; we have none and are not building one this phase.
- Manufacturer revenue per participation unit measures the **manufacturer's**
  economics, not the casino's GGR.
- Casino City may be read for QA and may never be published or resold.


---

## ORDINANCES — BUILT 2026-08-12, and two corrections

**321 tribes, 321 original ordinances, 834 amendments = 1,155 instrument rows,
1985-12-02 to 2026-02-12.** Amendments stored historically with effective
ranges and supersession chains; Bay Mills alone is 23 instruments.

### The Class II universe is 40 tribes, and it is now named

Tribes with an **ordinance and no compact** — invisible to the compact route by
statute: Alabama-Coushatta, Alabama-Quassarte, Bridgeport, California Valley,
Cayuga Nation of New York, Cloverdale, Delaware Tribe of Indians, Eklutna, Ely
Shoshone, Fort McDermitt, Greenville, Grindstone, Guidiville, Jena, Kake,
Kashia, Kickapoo of Texas, Klawock, Koi, Lytton, Metlakatla, Miccosukee,
Paiute-Shoshone, Passamaquoddy, Poarch, Quartz Valley, Redwood Valley,
Resighini, Round Valley, Santa Rosa of Cahuilla, Santee Sioux, Santo Domingo,
Scotts Valley, Shinnecock, Shoshone-Bannock, Te-Moak, Seminole Nation of
Oklahoma, Tlingit & Haida, Wampanoag, Ysleta del Sur.

**29 of the 40 have no NIGC-mapped location** — authorised, not observed
operating. An ordinance is an authorisation, never evidence of a facility.

**16 unresolved NIGC names were EXCLUDED from that count rather than folded
in.** Joining on a missing key scores every unresolved name as "no compact",
and Viejas, Santa Ysabel, Mille Lacs, Cherokee Nation and St. Regis
demonstrably hold compacts — including them would have inflated the headline by
40% using tribes that contradict it.

### CORRECTION: a Revenue Allocation Plan reference is usually boilerplate

The brief assumed an ordinance referencing a RAP indicates per-capita
distribution exists. **Wrong.** 196 tribes reference one, but **160 carry only
the conditional statutory recitation of 25 U.S.C. 2710(b)(3)** — *"**If** the
Tribe elects to make per capita payments…"* That proves the ordinance
contemplates per capita, not that a plan or a distribution exists.

- **15 tribes assert** a plan or election in the indicative — the real leads.
- **20 prohibit per capita outright** — also a finding.

**Read the mood of the clause, not the presence of the phrase.** A conditional
recitation of a statute is not a fact about the tribe.

### The second payoff: tribal gaming agencies are now named

**284 of 321 tribes name a Tribal Gaming Agency; 397 distinct names, 363
tribe-specific.** This closes a question the compact parse opened — it found
**674 reporting obligations running to a *Tribal* Gaming Agency** and could name
none of them. Tribal regulatory capacity, assembled for the first time.

### Defects found in NIGC's own index

Five, all recorded in `index_anomaly`: one link printed under two dates
(Absentee Shawnee); **Kialegee Tribal Town's amendment link serves Kalispel's
PDF** — different URLs, byte-identical file, caught only by md5, and that row is
refused with no extracted content; Santa Ysabel listed twice under two names; an
`href` containing a tribe's name instead of a URL (Cahto); an approval date
three years before IGRA (Muscogee).

**18 tribes hold compacts with no ordinance on the index, 15 unexplained.** IGRA
requires an ordinance for Class III as well, so that is a gap in NIGC's
published index rather than in our extraction.

### Known backlog

**264 rows (23%) are image-only scans with no text layer**, concentrated in the
1990s–2000s. They still carry a verbatim quote from NIGC's index cell, so every
row has a source URL and quote — but their provisions are an **OCR backlog, not
an absence**. The declination build closed an identical ceiling with
`rapidocr-onnxruntime`; the same route applies here.

---

## STEPS 12-14 BUILT 2026-08-12 — and the FAC dead end was wrong

Full log: `docs/GAMING_FINANCIAL_EXHAUST_BUILD_LOG.md`. Scripts `code/147`,
`code/148`, `code/149`.

**The recorded dead end — "tribal Single Audits are withheld at the FAC" — was
one auditee's election read as a rule.** 2 CFR 200.512(b)(2) is an opt-out.
**2,046 of 6,774 tribal FAC records (30.2%) are `is_public = true`** and their
reporting-package PDFs download, including gaming tribes. Seminole Tribe of
Florida elected to withhold; most did not.

The withholding is **per endpoint**, measured on matched samples of 25:
`notes_to_sefa` 25/25 public vs **0/25** non-public, same for findings and
corrective actions, the **PDF 403s** — but `federal_awards` is **25/25 on
both**. The SEFA survives the withholding; the reporting package does not. No
API table carries the financial statements at all, which is why the PDF layer
had to be built.

**Machine participation exists and is now observed: 25
`MACHINE_PARTICIPATION_ARRANGEMENT` disclosures on 8 tribal entities**, two of
them carrying an exact figure (Robinson Rancheria wide-area progressive,
$319,889 FY2019 / $210,827 FY2020). An arrangement and a measure are separate
columns, because a participation note with no dollar still establishes that the
arrangement exists.

**Four typing errors were caught before shipping**, all recorded in the build
log with the failing quote: a flattened revenue table typed as participation
expense (GGR mislabelled, ~45x), a telephone authority's satellite-internet
participation fee typed as a gaming input, a money column typed `TRIBAL_TAX`,
and an RSTF **receipt** typed `COMPACT_PAYMENT` when it is the recipient's
revenue and travels in the opposite direction.

Steps 13 and 14 are thinner and the coverage tables are their real output:
17 tribal legislative hosts (1 PUBLISHES / 13 NOT_FOUND / 3 NOT_CHECKED), and
740 supplier-disclosure rows on 51 entities of which only **2** are
`VENDOR_AUTHORIZED_BY_TRIBAL_REGULATOR` — because a mention is not an
authorisation, a prospective approval is not a licence held, and a tribal
gaming authority naming itself in its own 10-K is not a vendor relationship.

---

## THE 140 STAGED ADDITIONS ARE RULED — 2026-08-26

`docs/GAMING_UNIVERSE_REBUILD_2026-08-26.md`. Scripts `code/155`, `157`–`162`.

**The roster diff that produced the 140 was wrong about most of them, and the
reason is worth carrying.** Script 92's partition test was *exact string
equality on a parsed city*, and NIGC's own address text misspells the city:
`Mohnomen` for Mahnomen, `Muscogee` for Muskogee, `Seneca Fall` for Seneca
Falls. Each misspelling scored "Cedar has nothing in this city" — **a
misspelling in the source became a claim about our coverage.**

| | |
|---|---:|
| NIGC current roster (2026-08-26) | 522 markers → 510 locations → **496 distinct** |
| …linked to a Cedar property | **453 (91.3%)** — tier A 428, tier B 25 |
| staged additions ruled `ALREADY_IN_CEDAR_DO_NOT_ADD` | **103** |
| appended as new Cedar properties (`CEDAR-FAC-`) | **10** |
| queued as possible duplicates | 43 |
| queued: NIGC-current vs Cedar-closed conflict | 5 |

**"NIGC's map holds 490 locations against our 774" is superseded**: it holds 496
distinct gaming locations, plus 10 Chinese railway stations, a blank marker and
14 exact duplicates — defects in NIGC's own WordPress map, all enumerated in the
build log.

**The 424-of-ours-not-on-NIGC figure was also over-read.** 324 Cedar rows are
absent from the current map and **112 of them carry close evidence**, which is
exactly what a current-operations map should do with a closed property. Absence
from NIGC is only a question for the 212 that carry none.

### Two corrections to the resolution recorded above

1. **`CCP-`/`VP-`/`TPL-` are no longer the only facility prefixes.** New
   properties genuinely absent from Cedar are minted `CEDAR-FAC-` through
   `code/cedar_ids.allocate`, as this file anticipated ("those get new Cedar
   IDs"). The prefix remains history, not provenance.
2. **NIGC is now joined, not merely diffed.**
   `data/clean/gaming_nigc_roster_link.csv` carries the 453 links with the
   matching rung and its tier, so "is this a regulated gaming operation" is
   answerable per property instead of per build.
