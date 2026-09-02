# Pre-FY2007 federal spending — every source, typed

*Cedar Press, 2026-08-26. Written in answer to a challenge from the owner:*

> *"Why aren't you getting data on federal spending from another data source that's not
> USAspending that you can get prior to 2007? I still feel like you should be able to
> download data from USAspending if you need to, to fill gaps, so we don't always need
> SAM. Try that too — don't just give up if one approach didn't work, and research."*

**He was right to ask, and the answer is not the one the project has been assuming.**

Scripts: `code/197_measure_pre2007_identifier_surface.py`,
`code/198_compare_fpds_extracts_vs_prime_clean.py`,
`code/199_faads_identifier_by_agency_year.py`,
`code/200_probe_fac_historical_depth.py`,
`code/201_value_of_pre2007_fpds_netnew.py`.
Machine-readable outputs: `docs/PRE2007_IDENTIFIER_SURFACE.json`,
`docs/PRE2007_FPDS_VS_PRIME_OVERLAP.json`, `docs/PRE2007_IDENTIFIER_BY_AGENCY.{json,csv}`,
`docs/FAC_HISTORICAL_DEPTH_PROBE.json`, `docs/PRE2007_FPDS_NETNEW_VALUE.json`.

**Network discipline observed.** `api.usaspending.gov` and `files.usaspending.gov` were
**not contacted**: `code/121_pull_subawards_api.py` held the host lock throughout with a
live poller (PID 13736, verified in `Win32_Process`, not in `ps`). `api.sam.gov` was not
contacted — its 10/day budget is spent. Hosts touched: `api.fac.gov` (22 requests),
`www.fpds.gov` and `catalog.archives.gov` (10 requests combined). Locks claimed and
released on all three.

---

## THE HEADLINE, IN FIVE SENTENCES

0. **CEILING 1 HAS A HOLE, AND IT IS $3.07 BILLION WIDE.** The Federal Audit Clearinghouse
   publishes a Census-era bulk archive reaching **FY1998** with **`EIN` populated on
   100.0% of auditees**. Joined to FAC's own tribal roster on the EIN — **no name matching
   anywhere** — **FY1998 yields 544 tribal entities and $3,069,210,887 of reported federal
   expenditures across 11,745 auditee × CFDA programme rows**; FY2005 yields 696 entities
   and $5.77B. **Per-entity federal assistance in Indian Country is observable nine years
   before the floor Cedar Press publishes.**
1. **The pre-FY2007 recipient-identifier wall is real for FAADS, and it is now measured
   across all 66 agency-year cells rather than one agency — but it is a fact about ONE
   SOURCE, not about the era.**
2. **For CONTRACTS the wall does not exist at all.** Per-entity procurement with a modern
   UEI on **100.0% of rows back to FY1979** is already sitting on this machine, and
   **49,043 rows carrying $9.83B of it — $4.23B at inherited tier A — has never been
   merged.**
3. **Two free, live, record-level routes to FY1979–2007 procurement exist outside
   USAspending and outside SAM, and both were verified from this repo today**: the
   **FPDS-NG ATOM feed** (26,936,840 records for FY1979–2007, no key) and **NARA RG 269**
   (8.66M records, direct ZIPs, no login).
4. **The one route `COMPETITIVE_POSITION.md` calls unexploited has in fact already been
   used, at scale**, and it is where the 2.77M-row "FAADS" file came from.
5. **`docs/API_KEYS.md`'s claim that SAM is "the **only** route to FY2000–2007 prime
   contracts" is false by a wide margin** — five other routes exist, four of them free and
   one already on disk. SAM is uniquely required for **nothing**.

---

## PART 1 — CEILING 1 RE-EXAMINED

### What was claimed

> Per-entity federal assistance **cannot begin before FY2007**: FAADS carries a recipient
> identifier on 0.0% of rows FY2001–06.
> — `docs/COMPETITIVE_POSITION.md` §0 Finding 5

The brief that commissioned this work said the measurement is sound and stands, and that
what does not follow is the generalisation to *all* per-entity federal spending. Both
halves check out, and the measurement is now **stronger** than it was.

### The measurement, re-run and widened

`docs/FAADS_FEASIBILITY_2026-08-05.md` measured the identifier gap on **one agency**
(Interior). That is the error shape this project has already paid for twice — the tribal
Single Audit "dead end" and `resource_assets.csv` — so it was re-run across every agency.

`code/199_faads_identifier_by_agency_year.py`, all 2,769,748 rows:

| pre-FY2007 | measured |
|---|---:|
| rows | **1,994,993** |
| obligations | **$1,355,279,614,576** |
| agency-year cells | **66** |
| cells carrying **≥1** DUNS | 14 |
| **rows carrying a DUNS** | **65** — 0.0033% |
| tribal-flagged rows (`recipient_type` I/J/K) | **40,657** ($7,333,734,061) |
| **tribal rows carrying a DUNS** | **2** |

**There is no agency escape hatch.** The best pre-2007 cell in the entire corpus is HHS
FY2006 at **25 DUNS in 65,296 rows (0.038%)**. CEILING 1 survives contact with a
per-agency test, which it had never had.

### Why it is real — the cause is documentary, not a pull artefact

`docs/FAADS_FEASIBILITY_2026-08-05.md` §3 already recovered the authoritative Census
record layout (staged at `data/raw/external/faads/census_faads_usrguide.txt`): FAADS is a
**624-byte fixed-width record with 34 fields, and neither DUNS nor EIN is one of them.**
Census states it directly — FAADS *"does not currently collect DUNS information for
recipients of Federal assistance."* DUNS arrives only with **FAADS PLUS in 2007** under
FFATA. UEI did not exist until 2022 and can never appear in this era.

So the wall is a property of **what the federal government collected**, not of any route,
any vendor, or any pull. **No source can supply a pre-2007 assistance recipient identifier,
because none was ever recorded.** That is the strongest possible form of this finding and
it is now defensible per-agency and per-document.

### NEW FINDING — the published FY2007 identifier floor is WRONG for the two agencies that matter most

The project publishes an "identifier floor (tier A) FY2007". Measured per agency, FY2007
is **not** a uniform crossover:

| agency, FY2007 | rows | DUNS % | tribal-flagged rows | tribal DUNS % |
|---|---:|---:|---:|---:|
| Education | 344,401 | **100.0** | 1,480 | 100.0 |
| Housing and Urban Development | 171,554 | **100.0** | 21 | 100.0 |
| Energy | 5,765 | **100.0** | 83 | 100.0 |
| Labor | 3,085 | **100.0** | 207 | 100.0 |
| Health and Human Services | 74,163 | 99.67 | 1 | 100.0 |
| Agriculture | 67,615 | 98.02 | 1,652 | 98.18 |
| Environmental Protection Agency | 4,595 | 97.76 | 977 | 97.85 |
| Justice | 4,470 | 96.20 | 245 | 98.37 |
| **Transportation** | 86,921 | **0.749** | 59 | **0.0** |
| **Interior** | 9,662 | **0.0103** | 841 | **0.0** |

**Interior — the single largest tribal assistance agency — carries a recipient identifier
on 0.0% of its tribal rows in FY2007, the year Cedar Press calls the tier-A floor.** Per
`FAADS_FEASIBILITY`, Interior does not cross over until **FY2010 (14.3%) / FY2011
(99.9%)**.

**Consequence:** anyone building a per-entity Interior or DOT series from FY2007 gets
three to four years that look in-window on the coverage strip and carry no identifier at
all. The floor is not FY2007; it is **FY2007 for eight agencies and FY2010/11 for Interior
and Transportation**. This belongs in `series_breaks.csv` and on the profile page's
coverage strip. It is a defect in a published claim, found by widening a one-agency
measurement.

### What pre-2007 assistance DOES carry — the routes that are not the identifier route

Measured across all 2,769,748 rows (`docs/PRE2007_IDENTIFIER_SURFACE.json`):

| column | FY2001 | FY2002 | FY2003 | FY2004 | FY2005 | FY2006 | FY2007 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `recipient_duns` | 0.0003% | 0.0009% | 0.0018% | 0.0028% | 0.0021% | 0.0103% | 87.38% |
| `recipient_uei` | 0.0003% | 0.0006% | 0.0012% | 0.0025% | 0.0012% | 0.0093% | 78.04% |
| **`award_id_fain`** | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **100.0%** |
| `recipient_name` | 99.99% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| `recipient_state` | ~100% | ~100% | ~100% | ~100% | ~100% | ~100% | ~100% |
| `recipient_zip` | 66.17% | 81.71% | 82.39% | 81.75% | 84.01% | 89.45% | 99.79% |
| `cfda_program` | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| distinct (name, city, state, zip) | 88,138 | 69,519 | 71,542 | 69,562 | 72,435 | 76,247 | — |

Three things follow that the "0.0%" headline hides:

- **`award_id_fain` is 100% populated on every pre-2007 year.** Every row is an identified
  *award*, even though the *recipient* is unidentified. That is the correct join key for
  any future enrichment, and it is why a name-floor row is not a floating string.
- **The name floor is a four-part key, not a name.** `(name, city, state, zip5)` resolves
  to ~70–88k distinct recipients per year. Attribution against it is still name matching
  and still tier B — but it is materially more constrained than matching on a name alone,
  and the project has never characterised it this way.
- **The source's own tribal flag needs no name matching at all.** `recipient_type` I/J/K
  is ~100% populated and isolates **40,657 pre-2007 tribal rows worth $7.33B** with zero
  inference. Per-tribe totals are not constructible; **aggregate Indian Country totals
  FY2001–2006 are**, at zero fabrication risk. Nobody in the landscape scan publishes that
  series.

### Verdict on CEILING 1

**CONFIRMED ABOUT FAADS. FALSE AS A STATEMENT ABOUT THE ERA.**

The measurement is sound and now much stronger — 66 agency-year cells, a documentary
cause, no agency escape hatch. But the claim it was used to support —
*"per-entity federal assistance **cannot begin** before FY2007"* — does not follow, and
**Part 1C disproves it outright with an EIN-keyed source reaching FY1998.**

The correct statement is narrower and entirely defensible:

> **The federal assistance TRANSACTION record carries no recipient identifier before
> FY2007, because none was collected.** Per-entity pre-2007 assistance is therefore not
> observable from the transaction stream — but it *is* observable from the **audit**
> stream, at the auditee × programme grain, for every recipient above the Single Audit
> threshold.

**It also says nothing whatever about contracts, and Part 2 shows why that distinction is
worth $9.83B.**

---

## PART 1C — THE FEDERAL AUDIT CLEARINGHOUSE REACHES FY1998, WITH AN EIN

### How this was nearly missed, twice

`code/200_probe_fac_historical_depth.py` measured `api.fac.gov` properly — 22 requests,
lock claimed and released — and found the dissemination table starts at **`audit_year`
2016**: zero rows for every year 1997–2013, `count(audit_year < 2016) = 0`. On that
evidence the honest write-up was *"FAC: NOT_FOUND pre-2016"*, and it would have been
**wrong**.

FAC publishes the **Census-era 1998–2015 archive as bulk ZIPs on an entirely different
path**, which the API does not expose:

```
https://www.fac.gov/data/download/historic/
  -> https://app.fac.gov/dissemination/public-data/census/csv/census-YYYY.zip
```

**The API and the bulk archive are different surfaces over different eras.** Probing one
and concluding about the source is the exact error this project has already paid for twice
— the tribal Single Audit "dead end" and `resource_assets.csv` — and it came within one
document of happening a third time, *in the same dataset*.

**The rule this earns: an API's floor is a fact about the API. Before recording
`NOT_FOUND` on a source, enumerate its SURFACES — API, bulk download, archive path, FOIA
reading room — and probe each one.** A single-surface probe justifies `NOT_CHECKED` on the
others, never `NOT_FOUND`.

### Measured (`code/203_...py`, 5 requests, ~38 MB fetched)

| probe | result |
|---|---|
| index page | HTTP 200, links **census-1998.zip … census-2015.zip** — 18 years |
| `census-1997.zip` | **HTTP 404** — a fact about the object. The series starts at FY1998, not FY1997 |
| `census-1998.zip` | 200, **15,180,572 bytes**, 8 members |
| `census-2005.zip` | 200, **23,080,466 bytes**, 8 members |
| `census-2015.zip` | 403 — the links 302 to signed S3 with a ~30s expiry; **403 here is a signature artefact, not absence.** Follow redirects promptly |

Payload, measured from the archives themselves:

| | FY1998 | FY2005 |
|---|---:|---:|
| `ELECAUDITHEADER` rows (one per auditee-year) | **32,247** | **38,216** |
| **`EIN` populated** | **100.0%** | **100.0%** |
| `DUNS` populated | 0.0% | 60.5% |
| `ELECAUDITS` rows (auditee × CFDA programme) | **338,085** | **511,410** |

`ELECAUDITHEADER` carries `AUDITEENAME`, `EIN`, `DUNS`, `UEI`, street, city, state, ZIP,
`TOTFEDEXPEND`, `ENTITY_TYPE`. `ELECAUDITS` carries `CFDA`, `FEDERALPROGRAMNAME`,
`AMOUNT`, `DIRECT`, `PASSTHROUGHAMOUNT`. **That is a recipient-identified, programme-level
federal spending record for FY1998.**

### The tribal slice — measured with zero name matching (`code/204_...py`)

`data/clean/fac_tribal_single_audits.csv` holds **1,075 distinct EINs** that **FAC itself**
types `entity_type = tribal` in the 2016+ era. Looking those EINs up in the Census-era
archive is an **exact join on a federal identifier** — the operation supposed to be
impossible before FY2007.

| | FY1998 | FY2005 |
|---|---:|---:|
| **tribal EIN matches** | **544** | **696** |
| **reported federal expenditures** | **$3,069,210,887** | **$5,769,615,604** |
| **SEFA programme rows for those EINs** | **11,745** | **16,722** |
| SEFA amount | $3,193,222,837 | $5,864,144,973 |

Largest FY1998 auditees: Navajo Nation $215.7M · Cherokee Nation $88.4M · Qualla Housing
Authority $71.6M · Navajo Housing Authority $56.6M · Chickasaw Nation $52.6M · Choctaw
Nation of Oklahoma $52.2M · Mississippi Band of Choctaw $46.7M · Tanana Chiefs Conference
$46.1M · Confederated Salish & Kootenai $41.2M.

FY1998 top CFDA programmes: `93.228` (Indian Health Service — Health Management
Development), `93.575` (CCDF), `66.926` (EPA Indian Environmental General Assistance),
`93.612` (Native American Programs), `15.142` (Indian Housing Block Grants).

**And FAC types tribal entities natively in the Census era too**: `ENTITY_TYPE =
'INDIAN TRIBE OR TRIBAL ORGANIZATION'` is a first-class value — 183 rows in FY1998, 231 in
FY2005. It is sparsely populated (23,949 of 32,247 blank in FY1998), which is *why* the
EIN join finds three times as many, but it means the source carries its own tribal flag
and a name-free floor exists even without Cedar's roster.

### THE VOCABULARY TRAP THIS RUN WALKED INTO — recorded because it printed a clean zero

`code/203` filtered for tribal auditees on `TYPEOFENTITY.startswith("I")` — the modern
vocabulary — and printed:

```
TRIBAL auditee rows = 0; distinct EIN = 0; total fed expend = $0
```

**Every one of those zeros is an artefact.** In the Census-era files `TYPEOFENTITY` is a
**numeric code** (`908`, `505`, `903`, `909`, …) and in FY1998 it is **blank on all 32,247
rows**; the text vocabulary lives in a *different column*, `ENTITY_TYPE`. A filter written
against the wrong vocabulary returns zero and is **indistinguishable from an empty
source** — it even looks like a *confirmation* of CEILING 1.

`AGENTS.md` concurrency rule 8 already names the column version of this: *an absent column
reads as an empty source; a coverage computation must RAISE on a missing column, never
print a zero.* **This is the vocabulary version, and it is worse, because the column was
present and merely spoke a different language.** Extend the rule: **a categorical filter
must assert that its vocabulary intersects the data, and RAISE when the intersection is
empty.** A filter matching nothing is a bug until proven otherwise.

### THREE CAVEATS THAT MUST TRAVEL WITH ANY FAC-DERIVED SERIES

1. **An expenditure is not an obligation.** Single Audit reports what the auditee
   **expended**, as the auditee reported it. FAADS and USAspending report what the agency
   **obligated**. These are different quantities on different timing bases, and the project
   has already been burned by exactly this distinction — *"A RECEIPT IS NOT AN OBLIGATION"*
   (AGENTS.md, 2026-08-07), where a cash-basis series was inverted against an accrual one
   and produced a bound the publisher's own figures falsified. **Never splice a FAC series
   onto a FAADS series and call it one line.**
2. **It is a census of LARGE grantees, not of assistance.** Only entities above the Single
   Audit threshold file — **$300,000 in FY1998**, raised to $500,000 and later $750,000.
   The threshold moved twice inside the window, so the *population changes* over the
   series. That belongs in `data/clean/series_breaks.csv` before any trend is drawn.
3. **FAC's own `entity_type = tribal` is not clean, and Cedar inherits the defect.**
   Found incidentally by the EIN join and confirmed in the shipped file:
   - **`SACRAMENTO HOUSING AND REDEVELOPMENT AGENCY`, EIN 946000759, CA, is carried as
     `entity_type = tribal`** — a California municipal housing agency, matching $69.5M
     (FY1998) and $131.7M (FY2005). It has no Cedar entity link, so nothing is currently
     mis-attributed, but **the 6,780-record tribal headline includes non-tribal entities.**
   - **EIN 810230409 (Confederated Salish and Kootenai Tribes) resolves BOTH ways** — to
     `TRBF-CSKTFR-00` (the tribal government) **and** to `TCU-SLSHKT-00` (Salish Kootenai
     College), both tier B, both `attribution_method = containment`. This is the
     containment defect **live in a shipped file**, and it is the identical collision
     `START_HERE.md` records from the rejected script-57 re-run.
   - **`QUALLA HOUSING AUTHORITY`, EIN 560795881, appears under state `NC` and state
     `MI`.** Qualla is the Eastern Band of Cherokee's housing authority, in North Carolina.

   None of these were introduced by this work; the EIN join simply lit them up. They belong
   in `review/`, not in a merge.

### Verdict

**AVAILABLE — FY1998 onward, free, no key, recipient-identified by EIN, at the
auditee × CFDA-programme grain.** It does not restore the *transaction* stream and it must
never be summed with one. It does supply what CEILING 1 said was unobtainable: **who got
federal money in Indian Country before FY2007, and how much, keyed on an identifier.**

---

## PART 2 — THE FINDING THE PROJECT ALREADY OWNED AND HAD NOT NOTICED

The brief flagged that `fpds_uei_cage_map.csv` spans **1979–2023** and asked where that
came from. It came from three files sitting in `data/raw/esm_hci/ESM/raw/`:

| file | size | rows |
|---|---:|---:|
| `Data Request 4-5-2023 File 1.csv` | 2.31 GB | 1,101,796 |
| `Data Request 4-5-2023 File 2.csv` | 2.26 GB | 1,078,021 |
| `Data Request 5-8-2023 IDVs.csv` | 206 MB | 100,074 |

These are **HigherGov FPDS extracts**, 316 columns, full award records — `award_id_piid`,
`action_date`, `federal_action_obligation`, `naics_code`, `type_of_set_aside`,
`awarding_agency_name`, `recipient_*`, `uei_id`, `cage_code`, `recipient_duns`,
`ultimate_parent_uei`.

### The identifier population, measured (`code/197_...py`)

| | FY1979 | FY1989 | FY1999 | FY2000 | FY2003 | FY2006 |
|---|---:|---:|---:|---:|---:|---:|
| `uei_id` | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **100.0%** |
| `recipient_duns` | 100.0% | 81–100% | 99.7% | 99.6% | 99.5% | 99.6% |
| `award_id_piid` | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

**`uei_id` is 100% populated on every fiscal year back to FY1979.** UEI did not exist
before 2022, so this is a **back-stamp**: HigherGov carried the modern UEI onto historical
records through the DUNS→UEI crosswalk, which is exactly the mechanism that makes pre-2007
entity resolution possible for contracts and impossible for assistance. **Contracts
recorded a DUNS; assistance did not.** That single asymmetry is the whole of Part 1 versus
Part 2.

Pre-FY2007 content across the three files: **249,133 rows, $49.28B, 48,374 + 52,099 +
2,413 distinct PIIDs.**

### Provenance — and why File 2 was never merged

`data/raw/esm_hci/ESM/documents/Gmail - Data request for Taylor policy group.pdf` is the
March 2023 correspondence with Justin Siken (HigherGov founder) and settles what each file
is:

- **File 1 = flag-at-award.** Siken, verbatim: *"Do you basically want every transaction
  from FPDS where they flagged the contract as Tribal Owned, Alaskan Native, etc?"*
- **File 2 = SAM-registration match.** *"a second based on current registration status of
  child or parent."*

These are the two methodologies `AGENTS.md` records under *Identifier strategy*. **Only
File 1 was ever ingested** — it became `master prime file.dta`, which is the sole
`source_file` on every FY2000–2007 row of `prime_contracts.csv`. Verified by
`code/198_...py`: File 1's 78,267 pre-2007 keys match the clean table's 78,267 pre-2007
keys **exactly**. File 2 has never been merged into anything.

### What is net-new, measured (`code/198_...py`, `code/201_...py`)

Join key `PIID + fiscal_year + UEI`. `funding_agency` deliberately excluded — it is a
rendered label, not an identifier (`AGENTS.md`, 2026-08-12).

| source | pre-2007 keys | already in prime | **NOT in prime** | $ not in prime | new UEIs |
|---|---:|---:|---:|---:|---:|
| File 1 (flag-at-award) | 80,607 | 78,267 | 2,263 | $1.57B | 173 |
| **File 2 (SAM-reg match)** | 81,802 | 47,531 | **26,240** | **$7.93B** | **770** |
| IDVs | 3,005 | 7 | 2,997 | $0.33B | 131 |
| **total** | | | **31,500 keys / 49,043 rows** | **$9.83B** | **1,074** |

Bucketed by **inherited** ledger tier — a tier is inherited from the ledger row, never
assigned by the consumer (`START_HERE.md` standing rule 1):

| inherited tier | rows | obligations | distinct UEI |
|---|---:|---:|---:|
| **A** | **17,076** | **$4,234,581,376** | 337 |
| B | 5,388 | $994,057,954 | 374 |
| C | 22,463 | $3,312,519,092 | 1,356 |
| X (excluded — must stay excluded) | 970 | $105,528,558 | 39 |
| no ledger link | 3,146 | $1,181,658,939 | 450 |

Largest tier-A net-new entities: **Arctic Slope Regional Corporation 5,597 rows /
$1.32B**, Chugach Alaska $431M, NANA $425M, Chenega $345M, Afognak $294M, Calista $148M,
Chickasaw Nation $125M, Eyak $86M, Confederated Salish $82M, Ukpeaġvik Iñupiat $79M.

### And a window the clean table does not cover at all

`prime_contracts.csv` has `min(fiscal_year) = 2000`. The extracts hold **FY1979–FY1999:
6,816 rows, $2,611,636,699**, of which **1,850 rows / $594,557,216 sit on tier-A ledger
UEIs**. Twenty-one fiscal years of Native federal contracting that no Cedar Press table
has ever contained.

### THE CAVEAT THAT MUST TRAVEL WITH THIS, IN SIKEN'S OWN WORDS

File 2 is a *current-registration* match, and its author flagged the defect unprompted in
2023:

> *"There are two potential issues with the second list, one being that it will bias more
> recent awards since the registration data only goes back to 2014 (so may miss some
> companies that came into existence and went defunct before then) and two that **it will
> pick up awards for companies before they were acquired** (e.g., it would pick up all of
> Vistronix's awards before ASRC Federal bought them)."*

**That is a live containment hazard on the largest line in the table.** ASRC is the
biggest tier-A net-new entity at $1.32B, and ASRC Federal is precisely the acquirer Siken
used as his example. Merged naively, File 2 would book a firm's **pre-acquisition** revenue
to the tribe that later bought it — a false attribution that would look impeccably sourced.

This is the same class as the containment defect and the marginal-rate inversion: correct
arithmetic, correct citation, wrong answer.

**The remedy already exists in this project and nowhere else.** `AGENTS.md` §*The subtle
insight*: the deals ledger **is** the missing time-varying ownership source, and
`ownership_events.csv` carries dated acquisitions. Any File 2 merge must be **date-gated
against the ownership-event stream**, with rows preceding an entity's acquisition of the
vendor held at tier B or excluded and flagged. **File 2 is not a merge; it is a merge plus
an adjudication.** Do not run it as a merge.

### Verdict

**AVAILABLE — on disk, free, no network, no SAM, no licence encumbrance.**
$9.83B / 49,043 pre-FY2007 rows net-new, $4.23B of it at inherited tier A, plus a
FY1979–1999 window worth $2.61B that the clean table has never held. **Blocked only on the
date-gating adjudication, which is Cedar Press's own differentiator.**

---

## PART 3 — THE USASPENDING ROUTES

### The route `COMPETITIVE_POSITION.md` calls unexploited has already been used

`docs/COMPETITIVE_POSITION.md` §0 Finding 5 records, as an unexploited lead:

> *"Advanced Search begins FY2008 while Custom Award Data Download reaches FY2001."*

**It was exploited, comprehensively, on 2026-08-05.** Every one of the 2,769,748 rows in
`faads_transactions_all_agencies.csv` carries:

```
api_endpoint = https://api.usaspending.gov/api/v2/bulk_download/awards/
```

across **77 distinct agency-year source files** (`doi_fy2001.zip`, `usda_fy2002.zip`,
`hud_fy2006.zip`, `ed_fy2007_archive.zip`, …). `docs/FAADS_FEASIBILITY_2026-08-05.md` §4
records the API's own verbatim reply to a FY2002 request:

> `start_date falls before the earliest available search date of 2007-10-01. For data
> going back to 2000-10-01, use either the Custom Award Download feature on the website
> or one of our download or bulk_download API endpoints`

`2000-10-01` is day one of FY2001, and the returned file carried the **identical 112-column
modern assistance schema**.

**So the "documented route the project never used" is in fact the origin of the very file
whose 0.0% identifier rate defines CEILING 1.** The route works; the wall is in the data
it returns. That is a much better answer than "we never tried", and it converts CEILING 1
from an untested assumption into a route-verified finding.

Two things follow that were not previously written down:

- **The label "FAADS" on that file is wrong and actively misleading.** It is USAspending's
  own FY2001–2007 assistance republication, pulled through `bulk_download`. It is not the
  Census FAADS fixed-width corpus, which lives at NARA. Anyone reading the filename will
  look for a NARA provenance that does not exist. Rename or annotate.
- **`api_endpoint` and `source_url` are populated on 100% of rows.** The provenance was
  always in the file; nobody read the column. This is the third instance of the standing
  lesson *read the source's own disclosure columns before searching the web*.

### Routes measured, and routes still owed

| route | reaches | verdict |
|---|---|---|
| Award Data Archive (`files.usaspending.gov/award_data_archive/`) | **FY2007–FY2026** | **NOT_FOUND pre-FY2007.** Full enumeration, 4,631 keys, 12 filename shapes, `_All_` series is FY2007–FY2026 (`ASSISTANCE_ARCHIVE_PULL_LOG.md`). No FY2000–2006 object exists. Also publishes **no** subaward file — zero of 4,631 keys contain `sub`. |
| `bulk_download/awards/` — **assistance**, FY2001+ | **FY2001–** | **AVAILABLE and USED.** 2.77M rows on disk, 77 agency-year files. Identifiers absent for reasons in Part 1. |
| `bulk_download/awards/` — **contracts (`prime_award_types` A/B/C/D)**, FY2001+ | FY2001– | **NOT_CHECKED — and this is the single highest-value untested item.** Same endpoint, same floor message, different award-type filter; the assistance leg is proof the endpoint honours the pre-2008 window. Not testable today: `code/121_pull_subawards_api.py` holds the host lock (PID 13736 live). |
| `/api/v2/search/spending_by_award/` | — | **KNOWN-BAD, do not use.** Cumulative snapshots, not transactions; summing inflates ~2.2×. Settled finding. |
| FY2000 (1999-10-01 → 2000-09-30) | — | **NOT_FOUND at USAspending.** Below the stated 2000-10-01 floor. |

### THE EXACT TEST TO RUN WHEN THE LOCK CLEARS

Do not redesign, do not parallelise, do not split years — all three were ruled out on
2026-08-12 by a two-day canary. Run **one** submission:

```
POST https://api.usaspending.gov/api/v2/bulk_download/awards/
{"filters": {"prime_award_types": ["A","B","C","D"],
             "date_type": "action_date",
             "date_range": {"start_date": "2002-10-01", "end_date": "2003-09-30"},
             "agencies": [{"type":"awarding","tier":"toptier",
                           "name":"Department of the Interior"}]},
 "file_format": "csv"}
```

One agency, one year, inside the claimed window. It costs one submission and settles
whether FY2001–2006 **full-universe unfiltered** prime contracts are free.

**Preconditions, in order:** (1) `Win32_Process` shows no `121_pull_subawards_api`
process — *a dead wrapper is not a dead poller*; (2) `logs/_HOSTLOCK_api.usaspending.gov.json`
released; (3) run `py -3 code/121_pull_subawards_api.py canary` first — an accepted token
does not predict a produced file, and nine consecutive jobs proved that on 2026-08-12.

---

## PART 3B — TWO FREE ROUTES TO FY1979–2007 PROCUREMENT, VERIFIED FROM THIS REPO

Both were reported by a research sweep and then **re-measured by
`code/202_verify_pre2007_procurement_routes.py`**, 10 requests, because a route is not
`AVAILABLE` until this repo has seen the response. Raw evidence:
`docs/PRE2007_PROCUREMENT_ROUTE_VERIFICATION.json`.

### ROUTE A — the FPDS-NG ATOM feed. **AVAILABLE, and it is retiring.**

```
https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=PUBLIC&q=<query>&start=<offset>
```

No key, no auth, no registration. Measured here:

| probe | result |
|---|---|
| `SIGNED_DATE:[1978/10/01,2007/09/30]` | **HTTP 200, advertised total 26,936,840, entries present** |
| `SIGNED_DATE:[1980/10/01,1981/09/30]` (FY1981) | **HTTP 200, 609,820 records** |
| `start=399990` on FY1980 | 200, **1 entry** |
| `start=400000` on FY1980 | 200, **0 entries** |
| `https://api.fpds.gov/` | DNS `NameResolutionError` — host does not exist |
| `/ebiz/fpdsatomfeed/1.0/ATOM_FEED` | **404** — a fact about the object |

**FY1979–FY2007 is 26.9M procurement records, free, today.** This is the direct answer to
the owner's question, and it is not a partial one.

**THE 400,000-RECORD CEILING IS A SILENT TRUNCATION AND MUST BE DESIGNED AROUND.** The
feed's own `rel="last"` link advertises 609,820 records for FY1981 and then serves
**nothing past offset 400,000** — no error, no 4xx, just an empty entry set with HTTP 200.
A puller that trusts the advertised total and walks it to the end will record 609,820 as
retrieved and hold 400,000. That is precisely the failure shape `AGENTS.md` concurrency
rule 7 was written for — *a budget that truncates and then marks complete is a silent
ceiling* — arriving from a new direction. **Partition every query below 400k
(agency × date window) and compare retrieved against advertised on every partition.**

Two field-name traps reported and worth carrying: `CONTRACTING_AGENCY_ID:"1700"` works;
**`AGENCY_CODE:` and `DEPARTMENT_ID:` return zero results rather than erroring** — they
fail open, which reads as "this agency has no contracts."

**Cost is the real constraint.** Page size is fixed at 10 and `&size=100` is ignored, so
FY1999–2007 alone is roughly **1.67M requests**. This is a partitioned, budgeted,
multi-day pull, not a session's work — and it needs its own host lock and a
retrieved-vs-advertised gate before the first request.

**⚠ `sam.gov/contracting` states the ATOM feed "will be retired later in FY 2026."** The
ezSearch UI is already gone. **This window is closing, and that is an argument for pulling
a bounded, Native-relevant slice now rather than a complete corpus later.**

**Identifier note, and it inverts the premise.** The ATOM template carries **no DUNS field
at all**, including on 1980 records; GSA back-filled **UEI** retroactively across the whole
corpus in 2022. Requesting the old DUNS-bearing schema (`VERSION=1.4`) returns HTTP 503 —
retired. So this route needs no DUNS→UEI crosswalk, and it *cannot* supply a DUNS for
linkage to other pre-2007 datasets.

**A data-quality caveat that must be spot-checked before any attribution.** The sweep
found UEI `L88SRK33JSR6` / "S.N.C. SCIONTI" recurring across unrelated DLA *and* Army
records in 1978, 1980, 1981 and 1982, `vendorName` frequently blank pre-1985 while UEI is
populated, and early records clustering on the 15th of each month (legacy FPDS captured
month/year only; day precision appears by ~1985). **Treat pre-~1985 vendor attribution as
suspect until reconciled against NARA.** A back-stamped identifier is an inference by the
back-stamper, and this project's own rule applies: *the exactness of the KEY says nothing
about the correctness of the LINK.*

### ROUTE B — NARA RG 269, series naId 573450. **AVAILABLE, free, no login.**

The Federal Procurement Data Center's own files — *Records of Contracts Awarded by Federal
Agencies*, 10/1/1978–9/30/1997, **8,663,457 logical records, Access: Unrestricted**.
Unlike the FAADS series at naId 604955, **these carry digital objects and need no
reproduction order.** Direct, unauthenticated:

```
https://catalog.archives.gov/medialive/{last2ofNaId}/8828/{naId}/content/
    arcmedia/electronic-records/rg-269/FPDS/RG137.FEDPROC.Y{yy}.zip
```

Measured here by HEAD (nothing downloaded):

| object | status | Content-Type | bytes |
|---|---|---|---:|
| naId 1882845, FY1979 | 200 | *(empty)* | **13,480,059** |
| naId 1882874, FY1990 | 200 | *(empty)* | **22,458,880** |
| naId 1882866, FY1981 | 200 | **`text/html`** | **5,454** |

naIds run 1882845 (FY79), 1882864 (FY80), 1882865 (FY82), 1882867–1882881 (FY83–FY97).
**FY1981 is genuinely absent from the series** — and the way that absence presents is a
trap in its own right.

> ### NEW TRAP — `catalog.archives.gov` RETURNS HTTP 200 FOR AN OBJECT THAT DOES NOT EXIST
>
> The FY1981 ZIP answers **200**, not 404. The body is a 5,454-byte `text/html` SPA shell —
> **byte-for-byte the same length as the catalogue search page**. The two real ZIPs answer
> 200 with an *empty* `Content-Type` and millions of bytes.
>
> **On this host, status alone cannot distinguish a present object from an absent one.**
> `AGENTS.md` already records the mirror image at bia.gov — *"a 404 body from bia.gov still
> contains `<main>`, so a parser that trusts 'the file has content' will ship a region with
> zero agencies"*. This is the same lesson from the opposite side: there the body lied,
> here the status does.
>
> **The discriminator is `Content-Type` plus `Content-Length`, and it must be recorded per
> object in the fetch manifest.** A manifest built on status alone would record FY1981 as
> retrieved and hold an HTML shell.

**Two scope caveats, both load-bearing.** (a) **Civilian agencies only**, actions ≥$25k,
plus Small Business Competitiveness Demonstration Program contracts — **DoD is out of
scope for this route** and must come from ATOM. (b) The scope note enumerates fields
ending at *"the name and address of the contractor"*; **no DUNS is confirmed**, and the
record-layout PDF (`236.1DP.pdf`, shipped inside each file unit alongside `236.1SP.pdf`
and `FPDS_TSS.pdf`) is a **scanned image with no text layer**. **OCR it before building
anything on this route** — `code/150_run_ocr_overnight.py` already exists for exactly this.

The two sources corroborate each other on volume: ATOM puts FY1979–FY1998 at ~10.27M
against NARA's 8.66M civilian-only, and the excess is DoD plus sub-$25k actions. That is a
cross-source verification in the sense `docs/CROSS_SOURCE_VERIFICATION.md` means it — two
independent federal sources agreeing on a quantity neither was asked to reproduce.

### One more, worth recording

**DataLumos `10.3886/E237344` — AVAILABLE, FY2006–2019, 63 CSVs, ~96 GB**, unit = the
individual contract action, described by the depositor as *"downloaded from usaspending.gov,
March 2020"* — a **pre-UEI vintage, therefore very likely DUNS-native**. It reaches only the
last two years of the pre-2007 window, but it is the only DUNS-bearing artefact the sweep
found, which makes it the natural **crosswalk validator** for the UEI back-stamps in Part 2
and Route A. The DOI does not resolve to openICPSR; it 302s to
`datalumos.org/datalumos/project/237344/version/V1/view`. Landing page 403s to an automated
fetch, so the DUNS claim is **inferred from vintage, not measured** — say so until someone
opens it.

---

## PART 4 — DOES USASPENDING REMOVE THE SAM DEPENDENCY?

**Direct answer: USAspending removes most of the SAM dependency, and the FPDS-NG ATOM feed
removes the rest. SAM is now uniquely required for nothing.**

`docs/API_KEYS.md` states:

> *"The USAspending static archive begins at FY2008. SAM's Contract Awards API is the
> **only** route to FY2000–2007 prime contracts … So 'stage the data instead' has no
> referent here: there is nothing to stage."*

**Both sentences are false, and the second one is the expensive one.**

1. **The archive begins at FY2007, not FY2008.** `docs/PRIME_ARCHIVE_PULL_LOG.md` measured
   `_All_Contracts_Full_` present for **FY2007–FY2026**; `USASPENDING_PROBLEM_BRIEF.md`
   already flagged this correction. Scoping a 10-call-per-day SAM budget off an FY2008
   floor spends calls on a year the free archive serves.
2. **"There is nothing to stage" is wrong by 4.5 GB.** `Data Request 4-5-2023 File 2.csv`
   has been on this disk since April 2023, holds **26,240 pre-2007 keys / $7.93B** that
   `prime_contracts.csv` does not, and requires **no network call to anyone**.
3. **USAspending's `bulk_download` reaches FY2001**, verified for assistance and untested
   for contracts (Part 3).
4. **The FPDS-NG ATOM feed serves 26,936,840 records for FY1979–2007 with no key**, and
   **NARA RG 269 serves 8.66M civilian records as free ZIPs** — both measured from this
   repo today (Part 3B). FPDS-NG is the *system of record* SAM's Contract Awards API reads
   from; going to SAM for FY2000–2007 procurement is going downstream of a free source.

So there are **six** routes to FY2000–2007 prime contracts, not one. SAM is the sixth, and
it is the only one with a 10-per-day cap and a D&B licence encumbrance.

### What SAM still uniquely supplies — the honest answer is "nothing"

| workstream | can it be done without SAM? |
|---|---|
| FY2001–2006 prime contracts, **full universe** | **Yes, two ways.** USAspending `bulk_download` + `prime_award_types` (untested, one submission to settle — Part 3), or the FPDS-NG ATOM feed (**verified live**, partitioned under the 400k ceiling). |
| **FY2000 prime contracts** | **Yes — and this was the one thing SAM was thought to be needed for.** USAspending's floor is 2000-10-01, so it cannot serve FY2000. But **FPDS-NG ATOM covers FY1979 onward** (FY1981 alone measured at 609,820 records) and **NARA RG 269 holds FY1979–1997 outright**. FY2000 sits inside the ATOM window. **SAM's last unique claim is gone.** |
| Pre-2007 **Native-filtered** prime contracts | **Already answered without any network call** — File 1 is merged; File 2 is on disk (Part 2). |
| Subawards FY2021–24 | **Not a SAM question and never was.** FSRS is served only by `bulk_download`; the archive publishes no subaward file at all (zero of 4,631 keys contain `sub`). |
| CAGE ↔ UEI crosswalk | **Mostly.** USAspending carries UEI, not CAGE; **the ATOM feed carries no CAGE and no DUNS either.** But `fpds_uei_cage_map.csv` already holds **7,465 non-blank CAGE triples over 6,299 UEIs** with zero network calls, and SAM's Contract Awards API does expose `awardeeCageCode`. **This is the one place a SAM call still buys something** — and it is an enrichment, not a blocker. |

### The licensing argument, which is stronger than the availability one

Every row of a SAM FY2000–2007 backfill is a base award dated before 2022-04-04, so **D&B
Open Data attaches to 100% of it** — legal business name, street, city, state, ZIP may not
be disseminated in bulk. `START_HERE.md` and `AGENTS.md` both record this.

**USAspending republishes FPDS base awards and carries no such disclaimer.** `AGENTS.md`
correctly logs this as *open and unresolved* and says it should not be assumed either way
— so treat it as a reason to **prefer** the USAspending route, not as settled licence
freedom. Even so, the asymmetry is real and it points one direction: a USAspending-sourced
FY2001–2006 backfill would publish entity names and addresses that a SAM-sourced one
cannot.

The HigherGov extracts are a third licence position again — vendor-delivered under a 2023
data request — and their terms should be checked before publication, not after.

### The practical recommendation

**Stop treating SAM as the critical path. It is not on the critical path for anything.**

1. **Still spend tomorrow's ten calls on the `download` leg for the six accepted tokens.**
   That server-side work is paid for, a submission is not retryable, and a download is —
   `START_HERE.md` is right about the ordering. Finish it because it is nearly free, not
   because it is required.
2. **Then stand SAM down.** Nothing in the FY2000–2007 window depends on it any more.
   FY2000 — SAM's last exclusive claim — sits inside the FPDS-NG ATOM window, and
   `docs/API_KEYS.md`'s "only route" sentence should be struck and replaced with a pointer
   to this file.
3. **Order the remaining work by cost, cheapest first.** (a) **File 2 on disk** — $7.93B,
   zero network calls, blocked only on date-gating. (b) **One USAspending submission** to
   settle whether `bulk_download` serves contracts back to FY2001. (c) **NARA RG 269** —
   free ZIPs, ~19 objects, but OCR the layout PDF first. (d) **FPDS-NG ATOM** — the deepest
   and most expensive, ~1.67M requests partitioned under a 400k ceiling, **and the only one
   with a deadline: it retires in FY2026.**
4. **Keep the D&B mark on anything SAM-sourced that does land.** Contract facts publish;
   legal name and address do not, in bulk. That restriction is a second, independent reason
   to prefer every one of the routes above.

---

## PART 5 — THE FULL TYPED REGISTER

| # | source | verdict | unit | evidence |
|---|---|---|---|---|
| 1 | **HigherGov FPDS extracts, `data/raw/esm_hci/`** | **AVAILABLE** | recipient-level, UEI+DUNS+PIID | 249,133 pre-2007 rows / $49.28B on disk; 49,043 rows / $9.83B net-new; UEI 100% back to FY1979. `code/197`, `code/198`, `code/201` |
| 2 | USAspending `bulk_download/awards/` — assistance FY2001+ | **AVAILABLE (used)** | award-level; recipient **name only** pre-2007 | 2.77M rows, 77 agency-year files, `api_endpoint` on 100% of rows |
| 3 | USAspending `bulk_download/awards/` — **contracts** FY2001+ | **NOT_CHECKED** | expected recipient-level | Host lock held by a live poller. Exact one-submission test in Part 3 |
| 4 | USAspending Award Data Archive | **NOT_FOUND pre-FY2007** | — | Full 4,631-key enumeration; `_All_` series is FY2007–FY2026 |
| 5 | USAspending `spending_by_award` | **KNOWN-BAD** | cumulative snapshot | Inflates ~2.2×; settled |
| 6 | USAspending, FY2000 | **NOT_FOUND** | — | API floor is 2000-10-01 |
| 7 | **Census FAADS at NARA** (series naId 604955, FY1982–FY2010) | **PAYWALLED** | recipient **name only** — no DUNS, no EIN in the layout | 116 files, 34.2M records, unrestricted use but reproduction-order only: $14–17/file, ~$448 for FY2000–2007. AAD search exposes 8 fields and neither CFDA nor recipient type. **Would not fix CEILING 1 even if bought** |
| 8 | **FAC — `api.fac.gov`** (the API surface) | **NOT_FOUND pre-2016** | — | **Measured, 22 requests, `code/200`**: earliest `audit_year` = **2016**; `count(audit_year < 2016)` = **0**; per-year 1997–2013 all **0**. True of the API and **only** of the API |
| 8b | **FAC — Census-era bulk archive** (`www.fac.gov/data/download/historic/`) | **AVAILABLE** | **auditee × CFDA programme, keyed on EIN** | **Measured, `code/203`/`code/204`**: census-1998 … census-2015; `census-1997.zip` **404**. EIN **100%** populated. FY1998 = **544 tribal EINs / $3.07B / 11,745 SEFA rows**; FY2005 = **696 / $5.77B / 16,722**. Expenditures, not obligations; large-grantee census only |
| 9 | NBER FAADS mirror | **NOT_FOUND** | — | `data.nber.org/faads/` 404, `nber.org/research/data/federal-assistance-award-data-system-faads` 404, `data.nber.org/data/faads.html` 403 |
| 10 | **Census FAADS raw files at census.gov** | **NOT_FOUND** | — | `www2.census.gov/govs/faads/` returns **200 with an empty index** — parent link only, zero files. `www.census.gov/govs/faads/` 404; `www2.census.gov/programs-surveys/faads/` 404. The files are gone from census.gov |
| 10b | **Census FAADS via Wayback** | **AVAILABLE, with a hard gap** | action-level + county-aggregate; recipient **NAME only** | 5,191 archived URLs via the CDX API. **FY1996 Q1 – FY2004 Q1 complete; FY2008 Q1 – FY2010 Q4 complete; FY2004 Q2 – FY2007 Q4 is a HARD GAP** — no data captured. Measured retrieval: `faads021.zip` → 200, 7,979,196 B → `FAADS021.TXT`, 266,999 records, of which 164,755 action-level and **2,776 type-of-recipient = 11 (Indian tribe)**. Both official layouts (`97RecordLayout.pdf`, `98RecordLayout.pdf`) fetched and read: **no DUNS, no EIN in either** |
| 10c | Census FAADS FY1981–FY1995 | **PAYWALLED / offline** | — | The FY2008 Users' Guide states pre-FY1996 files are on **CD-ROM at Census**, obtainable only by contacting the Federal Programs Branch. Not a download |
| 11 | **Census Consolidated Federal Funds Report (CFFR)** | **AVAILABLE but AGGREGATE_ONLY** | **FIPS state × county × place × CFDA programme × object code × agency — no recipient field of any kind** | Two trees, and the obvious one is wrong. `www2.census.gov/programs-surveys/cffr/tables/` = **scanned PDF reports only**, 1981–2010; `.../cffr/datasets/` **404**. The data live at **`www2.census.gov/govs/cffr/`** — 1,922 files, `YYcffXX.zip`, **FY1993–FY2010** (`93cffwy.zip` 200; `92cffwy.zip` **404**; `85cffwy.zip` **404**). `00cffwy.zip` downloaded (42,118 B) → 2,302 records, header verbatim `FIPSST,FIPSCO,FIPSPLAC,STATE,COUNTY,PLACE,POP,CONGDIST,PROG_ID,OBJ_TYPE,AGENCY,AMOUNT`. The 1994 tech doc: *"unit of observation is each Federal government expenditure or obligation."* **Entity resolution is impossible.** ICPSR studies 8720/9081/9364/9511/9718/9872/6187/6408/6997/3146–3150/3179 extend the **geography** series to FY1986 |
| 12 | **FPDS-NG ATOM feed** | **AVAILABLE — verified, retiring FY2026** | recipient-level, **UEI** (no DUNS) | `code/202`: FY1979–2007 = **26,936,840 records**, HTTP 200, no key. FY1981 = 609,820. **Hard 400,000 paging ceiling**, silent. See Part 3B |
| 12b | FPDS bulk downloads / "Historical Data" pages | **NOT_FOUND** | — | `/downloads/`, `/downloads/top_requests/*`, `/fpdsng_cms/index.php/en/reports.html` all 301 → `sam.gov/contracting`. `api.fpds.gov` = DNS failure; `/ebiz/fpdsatomfeed/1.0/ATOM_FEED` = **404**. `sam.gov/data-bank` 404s; `/content/data-bank` is a JS shell → **NOT_CHECKED** |
| 12c | **NARA RG 269, naId 573450** (Federal Procurement Data Center) | **AVAILABLE — verified, free, no login** | recipient-level, name+address; **DUNS unconfirmed** | `code/202`: FY1979 ZIP **13,480,059 B**, FY1990 ZIP **22,458,880 B**, both HTTP 200. 8,663,457 records, Access Unrestricted. **FY1981 genuinely absent.** Civilian ≥$25k only — **no DoD**. Record layout is a **scanned image PDF**; OCR before use. See Part 3B |
| 13 | fedspending.org / OMB Watch corpus | **NOT_FOUND** | — | `fedspending.org` → 302 → `pogo.org`, zero archive hits. archive.org item search `q=fedspending` → **numFound 1** (unrelated audio); `title:(fedspending)` → **0**. GitHub yields only client code (`codeforamerica/fed_spending_ruby`). Not a real loss — it was a presentation layer over FPDS + FAADS, both recoverable |
| 13b | data.gov / catalog.data.gov | **NOT_FOUND** | — | The CKAN Action API is gone (404 on every form). **Trap:** `catalog.data.gov/dataset?q=FPDS` returns **200 but silently drops the query** and renders the default popular list — it fails open. Working path `catalog.data.gov/search?q=FPDS` → 20 results, all FPDS-NG-era, none pre-2007 |
| 13c | **DataLumos `10.3886/E237344`** | **AVAILABLE (FY2006+)** | individual contract action; **likely DUNS-native** | 63 CSVs, ~96 GB, FY2006–2019, *"downloaded from usaspending.gov, March 2020"* — pre-UEI vintage. Landing page 403s to an automated fetch, so **the DUNS claim is inferred from vintage, not measured** |
| 13d | Harvard Dataverse / Zenodo / AWS Open Data / BigQuery / GitHub | **NOT_FOUND or AGGREGATE_ONLY** | — | `10.7910/DVN/8RCMZP` and `/4NEPI7` are replication extracts, not transactions. Zenodo earliest relevant is 2001. No AWS or BigQuery listing. All 97 `fpds` GitHub repos are tooling. **Separately worth a look: `10.7910/DVN/YGHCRG` "D&B Historical Archive (U.S.)" 1969–2025** — point-in-time D&B records, a plausible name/address → DUNS crosswalk for the NARA era. Harvard-restricted |
| 13e | Commercial (HigherGov, Fedmine/GovSpend, GovTribe, Deltek) | **PAYWALLED** | — | All downstream of FPDS-NG. HigherGov $500–2,500/yr, publishes no earliest-year claim. **Fedmine — the vendor most likely to hold deep pre-2000 history — was acquired; `fedmine.us` 301s to `govspend.com/fedmine-now-govspend/`.** That is a phone call, not a fetch |
| 14 | **BIA / IHS agency historical obligations** | **NOT_CHECKED** *(attempted, host-filtered)* | program × tribe-or-area × FY, **in PDF** | `bia.gov/budget`, `/as-ia/ofm`, `/as-ia/ofm/budget-justifications`, `/service/budget-and-performance` **all 404**; `ihs.gov/BudgetFormulation/congressionaljustifications/` 404s on a server-side rewrite; `doi.gov/budget` exposes only 2020. Wayback CDX for `greenbook` on doi.gov → **zero rows**. These sites filter non-browser clients. **This is an unresolved lead, not a negative finding** — retry with `claude-in-chrome`. Note the "Indian Service Population and Labor Force Report" is **population counts, not obligations** |
| 15 | Historical CFDA archives | **AGGREGATE_ONLY** | **national program × fiscal year** | Financial Information/Obligations blocks give FY-actual dollars at national program level — no geography, no recipient. Useful as a **program-code crosswalk and denominator**, nothing more. `cfda.gov` in Wayback was a session-token app, essentially unreplayable; Internet Archive full-text holds 3 items. HathiTrust **NOT_CHECKED** |
| 16 | NARA AAD (`aad.archives.gov`) | **PAYWALLED / blocked** | record-at-a-time | **403** to automated clients. Offers no export control; fielded search exposes 8 fields and neither CFDA nor recipient type |
| 17 | **`fpds_uei_cage_map.csv`** (derived, on disk) | **AVAILABLE** | UEI ↔ CAGE ↔ legal name, 1979–2023 | 24,977 triples, 7,465 with a CAGE, 6,299 UEIs. Reduces the SAM entity-extract dependency |

---

## PART 6 — OPEN, AND WHY

1. **USAspending `bulk_download` for contracts, FY2001–2006.** NOT_CHECKED. Host lock held
   by a live poller for the whole session. Highest-value single test in this document; the
   exact payload and the three preconditions are in Part 3.
2. **BIA / IHS historical obligations. NOT_CHECKED — attempted and host-filtered.**
   Every budget path on `bia.gov` and `ihs.gov` 404s to a non-browser client, and the
   Wayback CDX sweeps returned zero rows. **That is a fact about the navigation, not about
   the documents** — `AGENTS.md`: *a broken search is not evidence of absence.* Retry with
   `claude-in-chrome`. Expect PDF extraction at program × tribe-or-area × FY, not a feed.
3. **The FY2007 floor correction.** Interior and DOT need entries in
   `data/clean/series_breaks.csv` and on the coverage strip; so does the **moving Single
   Audit threshold** ($300k → $500k → $750k) if any FAC series is drawn. Not done here —
   this document is a source assessment, and editing a shipped table mid-assessment is how
   the rebuild/in-place collisions in `AGENTS.md` happened.
4. **File 2 date-gating.** The merge is blocked on adjudication, not on data. See Part 2.
5. **The three FAC data-quality defects** (Sacramento Housing typed tribal; EIN 810230409
   resolving to both the tribe and its college; Qualla Housing under two states) belong in
   `review/`. Found incidentally, not introduced here, and **not** fixed here.
6. **HathiTrust for the CFDA print run 1983–2007**, and the **Harvard D&B Historical
   Archive** (`10.7910/DVN/YGHCRG`) as a possible name/address → DUNS crosswalk for the
   NARA era. Both **NOT_CHECKED**.
7. **A caveat on this document's own coverage.** Both research sweeps ran with an
   **exhausted WebSearch budget (200/200)**, so every external finding rests on direct HTTP
   fetches rather than search. That is *stronger* evidence where a fetch succeeded and
   *weaker* coverage where a site filters robots — which is exactly why item 2 is
   NOT_CHECKED rather than NOT_FOUND.

---

## WHAT THIS CHANGES

- **CEILING 1's measurement stands and is now much stronger** — 66 agency-year cells, a
  documentary cause in the FAADS record layout, no agency escape hatch.
- **CEILING 1's CONCLUSION is false.** "Per-entity federal assistance cannot begin before
  FY2007" is disproved by the FAC Census-era archive: **FY1998, 544 tribal entities,
  $3.07B, EIN-keyed, no name matching.** The wall is around one *source*, not around the
  era.
- **CEILING 1 was also being applied to contracts, where it never held at all.** $9.83B of
  pre-2007 per-entity contracting, $4.23B at inherited tier A, is on this disk right now,
  plus a FY1979–1999 window worth $2.61B.
- **CEILING 2 is broken outright.** SAM is one of **six** routes to FY2000–2007 prime
  contracts and is now uniquely required for **nothing** — the FPDS-NG ATOM feed covers
  even FY2000, which was SAM's last exclusive claim.
- **A published claim is wrong**: the FY2007 tier-A identifier floor does not hold for
  Interior or Transportation, the first of which is the largest tribal assistance agency.
- **A "documented unexploited route" was neither**: Custom Award Data Download was already
  the source of the project's largest pre-2007 file, and the provenance sat in a
  100%-populated column nobody had read.

### Two rules this earns

**1. An API's floor is a fact about the API. Enumerate a source's SURFACES before
recording `NOT_FOUND`.** `api.fac.gov` starts at 2016; the same organisation's bulk
archive starts at 1998. A single-surface probe justifies `NOT_CHECKED` on the others,
never `NOT_FOUND`. This is the third instance of the "one entity's behaviour generalised
into a rule about the source" error, and the first where the generalisation was from one
*interface* rather than one *record*.

**2. A categorical filter must assert that its vocabulary intersects the data, and RAISE
when the intersection is empty.** `code/203` filtered Census-era FAC on the modern
`TYPEOFENTITY` vocabulary and printed `TRIBAL auditee rows = 0` — which looks exactly like
a confirmation of CEILING 1 and is an artefact. `AGENTS.md` rule 8 covers the missing
*column*; this is the missing *vocabulary*, and it is worse because the column was there.
**A filter matching nothing is a bug until proven otherwise.**

*Four of the seven findings above came from re-reading files this project already owned.
That is the pattern worth keeping.*
