# Grantmaker funding flows — build log, 2026-08-12

Build script: `code/140_build_grantmaker_funding_flows.py`
(`--steps eins,index,probe,xml,deflate64,parse,overlap,coverage,codebook,report`)

| Path | What |
|---|---|
| `data/clean/grantmaker_funding_flows.csv` | **18,656 rows**, 43 cols — one row per named grant recipient on a conservative-movement grantmaker's own return |
| `data/clean/grantmaker_funding_overlap.csv` | the overlap matrix, in **two evidence tiers that must never be added together** |
| `data/clean/grantmaker_funding_coverage.csv` | per-funder and per-recipient retrievability, including what is NOT observable |
| `review/grantmaker_name_trap_exclusions_2026-08-12.csv` | 5 returns from 2 organisations refused as name traps |
| `data/raw/external/irs990_grantmakers/` | index targets, fetch log, EIN resolution, 84 return XMLs (26 MB) |
| `logs/140_build_report_2026-08-12.txt` | the run report |

---

## THE QUESTION

An earlier build (`code/139_build_litigation_positions.py`) tested whether the
Hoover Institution and George Mason University took **institutional** actions
against ICWA. They did not. Both appear in
`data/clean/native_issue_litigation_positions.csv` only as
`B_AFFILIATED_INDIVIDUAL` — a scholar signed an amicus brief — and never as
`C_INSTITUTIONAL_ACTION`. **That hypothesis failed and stays failed.**

The refined claim is about money: that the foundations funding the anti-ICWA
litigators also fund Hoover and Mercatus. This build tests it.

## WHY THE EXISTING SCHEDULE I LAYER COULD NOT ANSWER IT

`data/clean/np_schedule_i_grants.csv` holds 58,685 rows, but only from the 628
filers scripts 99 and 112 had already cached — Native-connected nonprofits and
their grantees. **A conservative foundation is absent from that file by
construction.** Absence there is absence in a sample, not in the world. So this
build pulled the grantmakers' own returns.

---

## RESULT: THE HYPOTHESIS SURVIVES, AT ONE TIER AND NOT THE OTHER

**8 of the 14 grantmakers gave both to a documented anti-ICWA institutional
actor and to a grant whose own filed return NAMES Hoover or Mercatus.** Two of
the eight are donor-advised funds and are separated out below because they are
a different kind of fact.

Dollars are cash grants paid during the year, from the filers' own returns,
tax years 2016 and 2020–2024 (see coverage).

| funder | DAF | anti-ICWA side | Hoover, unit named | Mercatus, unit named | host institution, unit NOT named |
|---|---|---:|---:|---:|---:|
| Lynde and Harry Bradley Foundation | | $4,730,000 | **$1,775,000** | **$1,700,000** | $3,320,000 |
| Sarah Scaife Foundation | | $4,180,000 | **$5,350,000** | **$1,900,000** | $7,723,740 |
| Searle Freedom Trust | | $10,580,000 | **$240,000** | **$1,750,000** | $7,910,000 |
| Charles Koch Foundation | | $10,503,201 | **$430,000** | — | $123,893,883 |
| John Templeton Foundation | | $1,141,200 | — | **$8,734,882** | $15,554,542 |
| Diana Davis Spencer Foundation | | $1,005,000 | — | **$60,000** | $1,500,000 |
| DonorsTrust | ✔ | $23,506,779 | **$2,414,670** | **$757,730** | $25,156,000 |
| Donors Capital Fund | ✔ | $1,265,000 | — | **$250,000** | — |
| The JM Foundation | | — *(none observed)* | **$290,000** | — | — |
| Adolph Coors Foundation | | $1,365,000 | — | — | $25,000 |
| Charles Koch Institute | | $11,748,815 | — | — | — |
| Ed Uihlein Family Foundation | | $22,500 | — | — | — |
| F M Kirby Foundation | | — | — | — | — |
| Charles Koch Foundation II | | — | — | — | — |

The anti-ICWA column aggregates grants to the six organisations script 139
records as `C_INSTITUTIONAL_ACTION` / `OPPOSED_TO_TRIBAL_PARTIES` in
*Haaland v. Brackeen*: the Goldwater Institute (whose Scharf-Norton Center was
amicus lead), Cato, Texas Public Policy Foundation, Pacific Legal Foundation,
New Civil Liberties Alliance and the Project on Fair Representation. **Those
sides are read from script 139, where every row is gated on a verbatim quote
located in the filed document. This build asserts no positions of its own.**

### The strongest single-row evidence

Grants whose filed return names Hoover, verbatim from the purpose or recipient
field:

```
Bradley       TY2020  $250,000  "Hoover Institution" / "To support the Monetary Policy in Practice Project"
Bradley       TY2020  $150,000  "Hoover Institution" / "To support the Role of Military History in Contemporary Conflict..."
Bradley       TY2022  $175,000  "Hoover Institution" / "To support the Monetary Policy in Practice Project"
Scaife        TY2022  $1,150,000 "BOARD OF TRUSTEES OF THE LELAND STANFORD JUNIOR UNIVERSITY" / "HOOVER INSTITUTION ON WAR, REVOLUTION AND PEACE"
Scaife        TY2024  $1,000,000 same
Koch Fdn      TY2017  $380,000  "Hoover Institution" / "General Operating Support"
Searle        TY2020  $80,000   "HOOVER INSTITUTION" / "RESEARCH"
JM Foundation TY2020  $290,000  "HOOVER INSTITUTION" / "GENERAL SUPPORT"
DonorsTrust   TY2020  $500,000  "Hoover Institution-Stanford University" / "Military History Working Group under the direction of Victor Davis Hanson"
```

---

## THE THREE HARD LIMITS. RECORDED, NOT WORKED AROUND.

### 1. Hoover files no Form 990, and this build measured that rather than assuming it

A search of the **full IRS EO BMF — 1,957,340 organisations** — for
"HOOVER INSTITUTION" returns **zero rows**. Hoover is a unit of Stanford
University. A grant to it is filed as a grant to "The Board of Trustees of the
Leland Stanford Junior University" (EIN 94-1156365) and is indistinguishable
from a grant to the medical school.

So the overlap file carries **two tiers, and they are never summed**:

| tier | meaning |
|---|---|
| `UNIT_IDENTIFIED` | the filed return NAMES Hoover or Mercatus, as the recipient or in the purpose. **The only tier that supports "this foundation funded Hoover".** |
| `INSTITUTION_LEVEL` | the recipient is Stanford or the GMU Foundation and **no unit is named**. The money reached a university that houses Hoover or Mercatus. It **cannot** be claimed to have reached them. |

The gap is large and it matters. Of 111 Stanford grant rows, **22 name Hoover
and 89 name no unit at all**. Of 116 GMU Foundation rows, 29 name the law
school and 87 name no unit. The Charles Koch Foundation's $123.9M institution-
level column is $118.8M George Mason (foundation and bare university) with
no unit named, plus $5.1M Stanford with no unit named — **read as Mercatus money it would be off by more than two
orders of magnitude against the $0 Mercatus figure the returns actually
support.**

`recipient_unit_identified` is a first-class column on every row and takes the
values `HOOVER_NAMED_IN_TEXT`, `MERCATUS_NAMED_IN_TEXT`, `GMU_LAW_NAMED_IN_TEXT`,
`STANFORD_UNIT_NOT_IDENTIFIED`, `GMU_UNIT_NOT_IDENTIFIED`,
`NOT_APPLICABLE_SINGLE_LEGAL_PERSON`.

### 2. DonorsTrust and Donors Capital Fund anonymise the donor by design

They are donor-advised funds. The grant is legally the fund's own; **no return
discloses who advised it.** A DonorsTrust grant proves money moved through,
never who chose it. `funder_is_donor_advised_fund` is 1 on 3,859 rows and the
caveat is on every one. DonorsTrust is the single largest anti-ICWA-side funder
in the file at $23.5M — and it is also the one about which the least can be
said. **This is a hard wall; the file never infers past it.**

### 3. A shared funder is not a shared position

Every row is `EvidenceClass.FUNDER_ACTIVITY`, whose
`carries_institutional_position` is False, and `carries_institutional_position`
is written as `0` on all 18,656 rows. `row_caveat` carries the sentence
verbatim:

> A shared funder is not a shared position. This row records that a foundation
> made a grant; it does not state that the recipient holds, endorses or is
> aware of any position taken by any other grantee of the same foundation.

Bradley funds Hoover **and** the Goldwater Institute. That is one fact about
Bradley. It is not a fact about Hoover, and the data cannot be made to say
otherwise.

### 4. A fourth limit the brief did not name: Form 990-PF has no recipient EIN

**Form 990-PF Part XV does not ask for the recipient's EIN.** Ten of the
fourteen funders are private foundations, and **14,320 of the 18,656 rows are
990-PF rows carrying no recipient identifier at all.** Every recipient
identification on those rows is a NAME match, which AGENTS.md records is never
Tier A on its own. `recipient_match_basis` states the leg used: 166 rows matched
on an EIN printed on a Schedule I, 450 on a guarded multi-word name phrase.

Matching is on **multi-word phrases only** — a single token can never carry a
match — which is what stops "Stanford", "Mason", "Cato" and "Hoover" linking on
their own.

---

## COVERAGE — WHAT IS ABSENT AND WHY

**E-file coverage is partial before tax year 2020 for private foundations.**
Mandatory e-filing arrived with the Taxpayer First Act, and the IRS e-file index
begins at submission year 2017. Measured here: Bradley, Scaife, Searle, Spencer,
Kirby, Uihlein, DonorsTrust and Donors Capital have returns only for
**TY2020–TY2024**. Templeton, the Charles Koch Foundation and the Charles Koch
Institute additionally have TY2016–TY2018. **An organisation with no return in a
year may simply have filed on paper. Absence is never read as "did not fund."**

- **Returns indexed 131 across submission years 2017–2026; 87 carry a grants
  schedule; 84 retrieved (96.6%); 79 parsed after name-trap exclusions.**
- **44 Form 990-T returns were deliberately not read.** Form 990-T is the
  business income tax return and carries no grants schedule. That is a fact
  about the form, not about the filer, and it is stated per funder in the
  coverage file.
- **3 indexed returns could not be retrieved** — Templeton TY2015, Charles Koch
  Institute TY2015, Charles Koch Foundation TY2015. All three are indexed in
  `index_2017.csv` with 2016 submission ids and are not present in any of the
  seven archives the IRS publishes for 2017. Recorded as
  `PARTIAL_SOME_RETURNS_INDEXED_NOT_RETRIEVED`, not as absence.
- **F M Kirby Foundation matched no target on either side** across 1,261 grant
  rows and five tax years. Its only movement-adjacent match is the Institute for
  Humane Studies at $20,000/year. That is a clean negative for that funder and
  it is reported as one.
- **Charles Koch Institute matched no Hoover/Mercatus/GMU recipient at all**
  across 477 grant rows, while giving $11.7M to the anti-ICWA side. Also a clean
  negative, in the other direction.

---

## THINGS THIS BUILD GOT WRONG FIRST AND CAUGHT

### The IRS index caught two organisations that are not the ones we wanted

Discovering a funder by NAME in the e-file index is the only route to an
organisation absent from the current BMF — and it is exactly the route that
catches the wrong organisation. Both were caught by reading the **filed
return's own state and grant list**, never by assuming:

| refused | why |
|---|---|
| `JM FOUNDATION` EIN **38-4322070**, Lafayette **California** | a different organisation from the conservative JM Foundation, EIN 13-6068340. Four returns, 0–1 grant rows, no target recipients. |
| `DONORS TRUST` EIN **26-2515785**, **Nebraska** | a different organisation from DonorsTrust Inc of Alexandria VA, EIN 52-2166327. Its single return reports no grants at all. |

Both are in `review/grantmaker_name_trap_exclusions_2026-08-12.csv` with the
reason, rather than quietly dropped.

### The BMF search is the reason the funder EINs are right

Probing the BMF for "BRADLEY FOUNDATION" returns **32 organisations**, of which
one is ours. "TEMPLETON" returns **100**. The near-misses were kept in
`data/raw/external/irs990_grantmakers/_ein_resolution.csv` rather than thrown
away, because the near-misses are the evidence that the hit is the right one.
`SCAIFE FAMILY FOUNDATION` (25-1427015) is a **different foundation** from the
Sarah Scaife Foundation (25-1113452) and would have been an easy wrong answer.

### Two identity findings that came out of the returns, not out of a lookup

- **The Charles Koch Institute is EIN 27-4967732**, which the current BMF
  carries as **STAND TOGETHER FELLOWSHIP**, Arlington VA. The filed returns name
  the filer "Charles Koch Institute" through TY2024. The rename is what
  establishes the identity — a BMF name lookup alone would have missed it
  entirely.
- **EIN 85-4058882 is "CHARLES KOCH FOUNDATION II" in the BMF and files as
  "Charles Koch Charitable Fund".** Same EIN, two names, seven grant rows.

### The Institute for Humane Studies is not the GMU Foundation

Three grant rows are filed to "INSTITUTE FOR HUMANE STUDIES GEORGE MASON
UNIVERSITY". Without its own key those rows land on the George Mason University
Foundation, which is a different legal person. IHS (EIN 94-1623852,
BMF-confirmed) now has its own key, is matched ahead of GMU by the
longest-phrase rule, and — having no documented ICWA position — correctly
appears on **neither** side of the overlap. 71 rows across 12 funders.

### Bare "George Mason University" is not the GMU Foundation either

George Mason University is an instrumentality of Virginia and files no Form 990.
Whether a grant filed to the bare university name legally landed at the
university or at its foundation is **not established by the return**, so it has
its own key `GMU` and its own coverage status
`NOT_SEPARATELY_OBSERVABLE_NO_OWN_FORM_990`. 10 rows, including $16,970,700 from
the Charles Koch Foundation.

### New name traps, measured and added to `cedar_domain.NAME_TRAPS`

Each count is the number of organisations in the **full** BMF whose name
contains the word — a single one of which is the organisation being looked for:

```
mason 697 · bradley 262 · spencer 261 · hoover 127 · stanford 105 · kirby 74
koch 52 · templeton 51 · cato 17 · coors 7 · scaife 6 · goldwater 5
```

`mercatus` returns **1** and is therefore genuinely distinctive; it was NOT
added. The guard ran clean before and after the change.

---

## TECHNICAL — THE ROUTE, AND WHAT IT COST

The same route script 132 used: **IRS e-file XML via HTTP range reads** into the
published ZIP archives, `HttpRangeFile` imported from
`code/99_build_earmarks_and_schedc.py`. **No bulk year archive was downloaded
for the range path.** Free disk was 4.82 GB at the start and 4.77 GB at the end;
a 2 GB floor was checked before every archive open and every file write and was
never approached.

```
index    10 requests, ~676 MB streamed and discarded, ZERO disk
xml      466 range requests across 81+2 archives -> 80 returns, 26 MB
deflate64  4 archives downloaded WHOLE (0.37-0.50 GB each), one at a time,
           extracted with system 7-Zip, DELETED before the next started
           -> 4 more returns. Peak extra disk: one 0.50 GB archive.
```

`apps.irs.gov` was claimed in `logs/_HOSTLOCK_apps.irs.gov.json` before every
network step and released after; sequential, 1.0 s gap on index requests and
0.35 s on range reads. **Zero refusals, zero 429s, zero transport failures.**

Four of the archives are written with **DEFLATE64** (compression method 9),
which CPython's `zipfile` cannot decode — the bytes arrive fine, the decoder is
missing. That is why those four were downloaded whole. Script 99 and 112 hit
the same six archives.

### The IRS publishes ONE archive for 2021 and TWO for 2022

Measured by HEAD probe over `{YYYY}_TEOS_XML_{NN}{A,B}.zip` for NN=1..25:

```
200  2021_TEOS_XML_01A.zip  3.72 GB
200  2022_TEOS_XML_01A.zip  2.60 GB
200  2022_TEOS_XML_02A.zip  1.41 GB   <- exists, NOT listed on the IRS page
```

Nothing else exists for those years. 2019 and 2020 have 18 listed objects each,
2023 and 2024 have 24, 2025 has 32. **The IRS download page under-lists 2022 by
one archive**, and that one archive held 11 of our TY2021 returns — every
TY2021 return in the first pass was missing because of it. The extra archive is
recorded in `data/raw/external/irs990_grantmakers/_zip_manifest_extra.csv` with
`basis = probe_verified_http_200_not_page_listed`.

A first probe walk missed it by interleaving the A/B/C/D suffixes: three
consecutive `01B/01C/01D` misses plus three more consumed the miss budget before
reaching `02A`. **Walk the numeric part continuously; treat the letter suffix
separately.**

---

## WHAT THIS CAN AND CANNOT SUPPORT IN A PUBLISHED ARTICLE

**It supports**, on the funders' own filed federal returns, with an object id
and a ZIP member on every row:

- that six non-DAF foundations — Bradley, Sarah Scaife, Searle, Charles Koch,
  Templeton and Diana Davis Spencer — gave in the same years both to
  organisations that filed against the tribal parties in *Brackeen* and to
  Hoover or Mercatus by name;
- the amounts, the tax years and the verbatim purpose of each grant;
- that the flow is not incidental: Scaife's Hoover line runs every year
  TY2020–TY2024, Bradley's Mercatus line every year TY2020–TY2024, Templeton's
  Mercatus line in **every one of its eight observed tax years**.

**It does not support**, and no column in the file can be made to support:

- that Hoover or Mercatus holds any position on ICWA. Script 139 already
  measured that they took **no institutional action**, and a funder's other
  grantees are not their position;
- that any particular dollar paid for any particular activity. Money is
  fungible, most grants are restricted to program work, and whether a grant was
  restricted is unobservable on a 990;
- that the $123.9M of Charles Koch Foundation money at George Mason reached
  Mercatus. It names no unit. The Mercatus figure the returns support for that
  funder is **$0**;
- who directed the DonorsTrust and Donors Capital money. That is closed by the
  DAF structure, not by our coverage;
- anything about years a funder filed on paper. TY2011–TY2019 is largely
  invisible for the private foundations here and that gap is the source's, not
  a finding.

The publishable sentence is a sentence about **foundations**, in the
conditional-free past tense, with the unit-identification stated: *"In tax years
2020 through 2024 the Sarah Scaife Foundation reported $5,350,000 in grants
whose stated purpose was the Hoover Institution on War, Revolution and Peace,
and $4,180,000 to organisations that filed against the tribal parties in
Haaland v. Brackeen."* Every clause in that sentence is a line on a filed
return.

---

## Regression check

`code/62_no_regression_check.py` before: **no regressions**, 39 metrics.
After: **no regressions**. `codebook_variables` 1,512 → 1,555,
`codebook_undocumented_public` 0, `duns_marked_publishable` 0.
`codebook_master.csv` was backed up to `.bak_2026-08-12_pre140` and only rows
whose `dataset` is `17_grantmaker_funding_flows` were written.
**No existing data file was overwritten.** `native_issue_litigation_positions
.csv` is read only.

## What would move this furthest next

1. **The Bradley Impact Fund, Allegheny Foundation and Carthage Foundation** are
   the obvious next filers — Bradley- and Scaife-family vehicles that were not
   in the brief and are not in this pull.
2. **The recipients' own Schedule I** is the other half of the ledger. Cato,
   TPPF and Mercatus all file 990s; their Schedule I would show where the money
   went next, and script 132's parser reads it already.
3. **TY2025 returns land through 2026** — the index step is cheap and
   re-runnable, and the 2026 archives already carry two of our returns.
4. **The 3 unretrieved TY2015 returns** would extend Templeton and both Koch
   entities back one more year. They are indexed; they are not in the archives
   the IRS publishes for 2017. Worth one more probe walk, not worth a bulk pull.
