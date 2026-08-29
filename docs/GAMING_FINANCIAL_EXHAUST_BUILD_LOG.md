# Gaming financial exhaust — Steps 12-14 build log

*Built 2026-08-12. Scripts `code/147`, `code/148`, `code/149`. Guard clean before
and after.*

Three sources, in the priority the brief set: Single Audits, tribal resolutions,
gaming supplier disclosure filings.

---

## THE HEADLINE FINDING: THE FAC DEAD END WAS ONE AUDITEE'S ELECTION

`START_HERE.md` and `AGENTS.md` carried this from the Florida build:

> "Tribal Single Audits are withheld at the Federal Audit Clearinghouse.
> Seminole Tribe of Florida (EIN 59-1415030) ... all ten filings FY2016-FY2025
> are `is_public: false` under 2 CFR 200.512(b)(2)"

Every word is true about the Seminole Tribe of Florida. **As a statement about
Indian Country it is false, and the false part is the valuable part.**
2 CFR 200.512(b)(2) is an **opt-out**, not a bar: an Indian tribe or tribal
organization *may elect* not to authorise public availability. Measured against
`api.fac.gov`:

| `entity_type = tribal`, all audit years | |
|---|---:|
| general records | **6,774** |
| `is_public = true` | **2,046 (30.2%)** |
| `is_public = false` | 4,728 (69.8%) |

**2,046 tribal reporting packages are published and their PDFs download** —
including the audits of gaming tribes: Sault Ste. Marie, Mississippi Band of
Choctaw, Muscogee (Creek) Nation, Gila River, Turtle Mountain, San Carlos
Apache, Quapaw, Grand Traverse, Robinson Rancheria.

A source's refusal on one record is a fact about that record. This one cost the
project its highest-value gaming financial source for five days.

## THE WITHHOLDING IS PER-ENDPOINT, AND MEASURED — NOT ASSUMED

A single non-public report returning zero notes proves nothing; plenty of public
filings have no notes either. So the test is the **rate**, on two matched
samples of the 25 largest tribal filings by federal expenditure:

| API table | public (n=25) | non-public (n=25) |
|---|---:|---:|
| `notes_to_sefa` | **25/25** (52 rows) | **0/25** |
| `findings_text` | 11/25 (29) | **0/25** |
| `corrective_action_plans` | 11/25 (29) | **0/25** |
| `federal_awards` (SEFA) | 25/25 (2,026) | **25/25 (4,010)** |
| reporting-package PDF | HTTP 200 | **HTTP 403** |

**The SEFA survives the withholding.** Seminole Tribe of Florida FY2022 returns
127 `federal_awards` rows, program by program with dollars, while its PDF 403s.
The election withholds the **reporting package**, not the schedule of federal
expenditures. That is a usable line into 4,728 otherwise-closed filings.

**No API table carries the financial statements.** Component-unit statements,
transfers to the tribe and participation expense exist only inside the PDF —
which is why the PDF layer had to be built rather than substituted.

## MACHINE PARTICIPATION: FOUND, AND IT IS RARE ON PURPOSE

**25 `MACHINE_PARTICIPATION_ARRANGEMENT` disclosures across 8 tribal entities**
— Sault Ste. Marie, Quapaw, Grand Traverse, Little Traverse, Muscogee (Creek),
Robinson Rancheria, Ottawa Tribe of Oklahoma, Sac & Fox of Missouri. The
canonical form, Sault Ste. Marie FY2022-FY2024:

> "The Gaming Authority leases some of its slot machines from gaming equipment
> manufacturers under participation arrangements, whereby the gaming
> manufacturer receives a percentage of the handle or net win associated with
> the leased machine."

And Quapaw Nation FY2023-FY2025, which says where it lands on the income
statement:

> "Fees paid under participation arrangements are recorded as part of Casino
> gaming expense."

**Two rows carry an exact figure and are typed
`MACHINE_PARTICIPATION_EXPENSE`** — Robinson Rancheria, wide-area progressive
jackpot participation: **$319,889 (FY2019)** and **$210,827 (FY2020)**, both
"included as a contra to gaming machine revenues".

An **arrangement** and a **measure** are separate columns (`disclosure_class`
and `measurement_type`) because they are separate facts. An arrangement with no
dollar still establishes that machine participation exists at that operator in
that year, and nothing else in the project exposes that.

## FOUR TYPING ERRORS CAUGHT BEFORE THEY SHIPPED

Each was live in an earlier pass of `147`, each looked well-sourced, and each is
now a guard with the failing case quoted in the code.

**1. GGR labelled as participation expense.** Robinson Rancheria FY2020 page 37
flattened to one "sentence":

> "FY 2020 Gaming machines $ 8,963,507 Table games 524,777 Bingo 295,086 Total
> gaming revenues $ 9,783,370 Participation Agreements:"

A revenue table whose next *heading* is "Participation Agreements". Typed
`MACHINE_PARTICIPATION_EXPENSE` on $9.78M — the brief's rule inverted, wrong by
~45x and pointing the wrong way on the income statement. Guard: the sentence
must carry an expense verb and must not carry a revenue **total** label. Both
guards keep the true $210,827 row on the same page.

**2. A satellite-internet fee filed as a gaming input.** Cheyenne River Sioux
Tribe **Telephone Authority** FY2017: "a deposit of $1,650 ... for satellite
internet service participation fees based on the number of access lines." The
matcher exempted "inherently gaming" terms from the gaming-context test, and
`machine_participation` matches a bare "participation fee". Guard: gaming
context is now required on **every** row with no exemptions; every true positive
carries "gaming" or "slot" in the same sentence, so it costs nothing.

**3. A table row is not a sentence.** Sac and Fox Nation of Missouri FY2018
produced a flattened column band — "Due To Gaming Other Other Operations
Governmental SFNMKN, Housing Proprietary ... $ $ l,240 $ 2,759,945 ..." — typed
`TRIBAL_TAX` on $2.76M belonging to no named concept. Guard: four or more raw
`$` characters means a money column, and its figures are not attributable to
whichever term appeared in the header band. Counting **parsed figures** was not
enough — only two of the eight dollar signs parse, because "$ $ l,240" is a
gutter and an OCR'd 1. The row is kept as a disclosure with
`parse_quality = SUSPECT_TABLE_FRAGMENT`; only the type is refused.

**4. An RSTF receipt is not a compact payment.** California's Revenue Sharing
Trust Fund pays **non-gaming** tribes out of gaming tribes' contributions, so
Big Valley Rancheria and Quartz Valley *receiving* $1.1M is the opposite
direction from a payment made. Retyped `TRIBE_LEVEL_REVENUE`, which is what
`code/103_build_california_gaming.py` already uses. Merging them would have put
payers and payees in one column.

## STEP 13 — TRIBAL RESOLUTIONS: MOSTLY AN HONEST NOT_FOUND

17 nations' legislative hosts swept: **1 PUBLISHES, 13 NOT_FOUND, 3
NOT_CHECKED**, 1 financing row (Navajo Nation, Capital Development Financing
Act amendment). Every row sits at `AUTHORIZED` on the existing ladder and
carries a cross-reference to `nigc_declination_letters.csv` with the explicit
note that a resolution and a declination letter covering the same transaction
are **one** financing relationship.

Two things worth keeping:

- **The first pass matched the financing vocabulary against LINK TEXT and
  returned zero rows on nine hosts that were serving HTTP 200s.** That is the
  wrong test — a tribal document library links its instruments as "TR 24-011" or
  "March 2024 minutes" and puts the subject inside the file. Fetching
  instrument-shaped documents and reading their own text turned Navajo from
  NOT_FOUND into PUBLISHES. A zero from a shallow matcher looks exactly like a
  finding about the nation.
- **Four hosts failed at the transport layer on the first run and were recorded
  NOT_CHECKED, not NOT_FOUND.** `swinomish-nsn.gov`, `www.gtb-nsn.gov`,
  `pci-nsn.gov`, `www.fmyn.org` — a DNS/TLS failure is a fact about the hostname
  string. Three still refuse under www-qualified names and remain NOT_CHECKED.

The honest reading: tribal legislative publication is sparse, voluntary and
unindexed, and the coverage table is the deliverable here rather than the row
count.

## STEP 14 — SUPPLIER DISCLOSURE: THE ROUTE WORKS, THE YIELD IS THIN

EDGAR full-text search, 10 phrase queries, 660 distinct documents, 655 parsed.
**740 rows on 51 spine entities**, split three ways:

| status | rows |
|---|---:|
| `TRIBAL_REGULATOR_NAMED` | 463 |
| `SELF_REFERENCE_NOT_A_VENDOR_RELATIONSHIP` | 275 |
| `VENDOR_AUTHORIZED_BY_TRIBAL_REGULATOR` | **2** |

The two authorisations are VendingData Corp's 10-QSBs of 2001:

> "The Jackson Rancheria Tribal Gaming Agency granted the Company a license
> certificate, effective July 19, 2001."

**Why only two, and why that is the right number.** Three refusals do the work:

- **A mention is not an authorisation.** A filing naming a tribal regulator is
  `TRIBAL_REGULATOR_NAMED` unless the sentence says the registrant *is*
  licensed, certified, registered, found suitable or approved.
- **Prospective is not held.** IGT's 2001 10-K says a merger "is subject to the
  approval of ... the Pala Gaming Commission" — a licence not yet held. Same
  rule the capacity build uses for PROJECTED device counts.
- **Self-reference is not a vendor relationship.** Mohegan Tribal Gaming
  Authority filing its own 10-K and naming itself produced 234 rows in the first
  pass. Now typed and excluded from vendor counts.

`property_inference` is `REFUSED` on every row: a licence with a tribe's
regulator says nothing about which property carries the vendor's product.

And the measure boundary is held in the other direction too — **where a supplier
filing reports participation *revenue*, that is the vendor's economics and is
never written into `MACHINE_PARTICIPATION_EXPENSE`**, which is the operator's
expense. This build emits none.

**What the licence NUMBER and application DATE would need.** They live in
licensing *applications* and multi-jurisdictional personal history disclosure
forms, and no state checked publishes those. Published state rosters name only
that state's own licence. Recorded as `NOT_CHECKED` in
`source_coverage_vendor_disclosure.csv` rather than as an absence.

Two extraction defects fixed, both measured:

- The federal/state exclusion list was tested against the captured **prefix**
  while every entry names the full institution, so "Nevada Gaming Commission",
  "Indiana", "Mississippi" and "Massachusetts" all shipped as tribal regulators.
  Now tested against the assembled name.
- The prefix ran into the preceding clause: "Chief Executive Officer of the
  Mohegan Tribal Gaming Authority", "Press Release of the ...", "Table of
  Contents The Tribal Gaming Commission", "Total Mohegan ...". Now cut at the
  **last** connective particle, with a document-furniture stoplist.

## OUTPUTS

```
data/clean/fac_tribal_single_audits.csv          6,780 report records, 638 entities
data/clean/fac_audit_gaming_disclosures.csv      1,521 disclosures, 70 entities,
                                                 123 reporting packages
data/clean/fac_audit_sefa_gaming_programs.csv        1 SEFA gaming programme row
data/clean/source_coverage_fac.csv                  62 coverage statements
data/clean/gaming_vendor_tribal_licenses.csv       740 rows, 51 entities
data/clean/source_coverage_vendor_disclosure.csv     2 coverage statements
data/clean/tribal_resolution_financings.csv          1 row
data/clean/source_coverage_tribal_legislative.csv   17 hosts
review/fac_unresolved_auditees_2026-08-12.csv      540 auditees
review/vendor_disclosure_unresolved_regulators_2026-08-12.csv
```

## ACCESS NOTES WORTH KEEPING

- **`api.fac.gov` is fronted by api.data.gov, so any api.data.gov key works on
  it.** `DEMO_KEY` returns HTTP 429 after ~7 calls; the existing key in
  `dissertation/docs/API_KEYS.md` gives 1,000/hour and needed no new
  registration.
- **The FAC API supports PostgREST `ilike`**, so its text tables can be swept
  corpus-wide. Yields are small (`notes_to_sefa.content ~ 'gaming'` returns 9)
  because SEFA notes are about federal awards, not about the casino.
- **PDFs are at `app.fac.gov/dissemination/report/pdf/<report_id>`** — a
  different host from the API, and it needs its own lock. 340 fetched at a 3 s
  gap with zero refusals; **all 340 had a text layer**, unlike the ordinance and
  FOIA corpora.

## WHAT IS OWED NEXT

1. **The other ~1,700 public tribal reporting packages.** 340 were fetched under
   a priority rule (public, gaming-linked, ≤3 years per entity). The rule is
   stated on every row in `_priority_basis`; widening it is a disk and
   wall-clock question, not a new access question.
2. **540 unresolved auditees** in `review/`. Many are tribal programme entities
   the spine does not hold (housing authorities, health boards, schools) —
   the same class as the 148 TDHEs already recorded in AGENTS.md.
3. **The 4,728 withheld filings' SEFA.** `federal_awards` is retrievable for all
   of them and only one gaming-named programme row exists so far, because the
   sweep filtered on `federal_program_name`. Pulling SEFA per withheld tribal
   report is a separate, cheap build.
4. **SEC tribal gaming issuers.** `data/raw/external/gaming_official/sec_filings/txt/`
   already holds 27 Mohegan and 11 Seneca filings, read by `code/96` for device
   counts only. Their audited statements carry transfers to the tribe, the
   Connecticut slot-win contribution and debt schedules and have never been
   read for financial measures. Checked here: **neither issuer discloses machine
   participation** — every "participation" hit in those 38 files is voter
   participation or consumer participation in leisure activities.
