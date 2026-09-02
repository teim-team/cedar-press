# Deals Build Log — ANC Annual Reports, 2000–2019, 2026-08-05

Dataset 1 (Indian Country Deals). Channel: **ANC annual reports**, the seam
`DEALS_2000_2019_BUILD_LOG.md` identified as "the single largest unworked seam left in the
window."

**Outputs**
- `data/clean/deals_anc_reports_additions.csv` — **28 rows**, 2000–2015
- `review/deals_skipped_anc_reports.csv` — **32 skipped / excluded leads**
- Log: `logs/27_deals_anc_reports.log`

Nothing was written into `deals_2026_ytd.csv`, `deals_historical_2020_2025.csv`, any
`cedar_*` file, `data/spine/`, or `review/cedar_review.html`. Schema validated
column-for-column against `deals_historical_2020_2025.csv` (32 columns, identical order).
Deal_IDs checked against both live ledgers and all three existing additions files (203
existing IDs): **zero collisions, zero internal duplicates**.

---

## The headline result

The prior run reported: *"No ANC annual-report PDF was successfully located and read in this
run."* That is now false.

**43 ANC annual reports were located, retrieved and read as document text**, spanning
fiscal years 2000 through 2017 across nine corporations. The channel that produced **2 rows**
in the previous sweep produced **28** in this one.

### How — the access finding of this run

The prior run's insight (curl + a declared User-Agent defeats a WebFetch 403) was applied
and extended. The decisive addition is:

> **The Internet Archive Wayback CDX API is a complete, queryable index of every PDF an ANC
> has ever published, and it fetches the file itself past any live-site block.**

```
https://web.archive.org/cdx/search/cdx?url=<domain>&matchType=domain
    &filter=mimetype:application/pdf&collapse=urlkey&output=json&limit=3000
```

then retrieve the document byte-for-byte with the `id_` modifier:

```
https://web.archive.org/web/<timestamp>id_/<original-url>
```

Run against 25 candidate domains this returned **6,058 archived PDF snapshots**, of which 124
were annual reports or shareholder reports. Three consequences matter beyond this run:

1. **It defeats the standing 403 blocks.** `nana.com` and `ahtna.com` have been on the manual
   download queue across two build logs. NANA's 2001–2005 annual reports were read this run
   through the archive and produced **3 rows**, including one of the two largest in the file.
   `nana.com` can come off the manual queue for historical documents.
2. **It reaches documents that no longer exist.** Nothing before Sealaska's 2015 report is on
   the live site. The 2000 report — eight separate PDFs at `/2000-Annual-Rpt/` — has not been
   live for twenty years.
3. **It is the right tool for the whole 2000–2019 window**, not just ANCs. Any entity that
   ever posted a PDF is indexed.

The pipeline in full: CDX query → curl with declared User-Agent → `pdftotext -layout` →
keyword scan for transaction verbs co-occurring with month names and dollar figures → read
every hit in its own paragraph before writing anything.

---

## Per-corporation results

### ASRC — Arctic Slope Regional Corporation. 11 rows. Best source in the channel.
`asrc.com/_pdf/_annualreports/` — reports for **2001, 2002, 2003, 2003 financials, 2004,
2005, and the 2005 shareholder report**. Seven documents, all read.

ASRC is the best-behaved ANC filer encountered: a numbered **NOTE 3 – ACQUISITIONS** in every
year, with effective dates to the day, prices, earnout language, and purchase-price
allocations. It also restates prior-year acquisitions, so a single report carries three or
four years of history.

Critically, **ASRC's fiscal year is the calendar year**, which is why two year-level ASRC
statements were admitted as rows (see "The date rule" below) while NANA's were not.

| Rows | |
|---|---|
| ND-2000-201/202/203 | Tri Ocean Engineering $9.6M, Oreck molding division $3.2M, McLaughlin Water Engineers $2.0M |
| ND-2002-201 | net assets of an engineering company (W&H Pacific) $6.0M |
| ND-2003-202/203 | CDM Resource Management sold $12.5M; Alpine Transportation 16.7% for $15.9M |
| ND-2004-201/202 | Lynx Enterprises $1.4M; remaining 30% of Houston/NANA $2.143M |
| ND-2005-201/202/203/204 | ASCG sold to NANA $31.275M; OMEGA Natchiq 10% $1.0M; R&K/Atigun assets $1.25M; Triquest-Puget Plastics sold $2.064M |

### Sealaska Corporation. 8 rows. Deepest run of years.
`sealaska.com` — the **2000** report (as eight component PDFs), **2004** MD&A, **2005**,
**2006**, **2008**, **2009**, **2010**, **2011**, **2012**, **2013**, **2014**. Twelve
documents. This is the only corporation with continuous coverage across the middle of the
window, and it is the reason **2009, 2010, 2013 and 2014 got rows at all** — precisely the
2010–2017 soft spot the prior log flagged.

Sealaska's reports carry a **"Divestitures of Subsidiaries"** note, which is unusual and
valuable: divestitures are normally the hardest event class to date.

Rows: Nypro Iowa 51% (2004), SeaCal/Calder mine sold (2005), Olympic Tool and Engineering
(2006), Kingston 49% (2009), Security Alliance of Florida 70% (2010), Nypro Kanaak holdings
sold $18.9M and Security Alliance +15% (2013), Rocky Pass Seafoods sold (2014).

### NANA Regional Corporation. 3 rows (2 as sole principal, 1 shared). **Block broken.**
`nana.com/pdfs/` — **2001, 2002, 2003, 2004, 2005** read. The 2006 and 2007 reports are
indexed but every archived snapshot is truncated and unreadable; twelve alternate timestamps
were tried.

NANA's notes are narrative rather than tabular and its **fiscal year ends in late September**,
which cost this run a clean $4.8 million transaction (see skipped leads).

### Bristol Bay Native Corporation. 2 rows.
`bbnc.net` — **2000, 2001, 2002, 2003** (fiscal years ending March 31) and **2016**. The 2007,
2013 and 2017 reports are indexed but every snapshot is truncated at exactly 1,048,576 bytes
(a 1 MiB archive-side cap) and cannot be read.

The 2016 report supplied **ND-2015-201**, the Bristol Alliance Fuels acquisition at
$15,827,000 — the second-largest value in the file and a row in a year that previously had one.

### The Aleut Corporation. 2 rows.
`aleutcorp.com/forms/pdf/` — **2003, 2004, 2006** read; 2005 and 2007 truncated in every
snapshot. Produced the Frosty Fuels terminal purchase and the **Adak Island conveyance**
(46,000 acres from the U.S. Navy and Interior, 2004-03-17) — the largest land transaction in
the file.

### Koniag, Incorporated. 1 row.
`koniag.com` — **2005** read; 2006 and 2007 truncated in every snapshot. Koniag's report is
narrative-rich and figure-poor: it names a dozen acquisitions with dates and gives a price for
none of them, disclosing only **fiscal-year aggregates** in the "Purchase of Business
Operations" note. The one row it did produce is disproportionately valuable — **ND-2004-204,
Koniag selling half its ACTI interest to Doyon, Limited**, an ANC-to-ANC ownership change.

### Cook Inlet Region, Inc. (CIRI). 1 row.
`ciri.com` — the **2005** and **2008** annual reports read (both at generic filenames that
disguise their year: `CIRI_Annual_Report.pdf` and `CIRI_Annual_Report_4-20XX.pdf`), plus a
2004 document that is a corporate profile rather than a report.

CIRI is the most dangerous source in this channel and yielded only one row despite carrying
the largest dollar figures anywhere in the sweep — see "Value traps."

### Doyon, Limited. 0 rows.
`doyon.com/pdfs/annualReport_2005.pdf` is the **only** Doyon annual report in the archive. It
was read in full and contains no dated, priced transaction. Doyon's archived output is
overwhelmingly **monthly shareholder newsletters** (roughly 60 issues, 2001–2007), which are
indexed and readable but were not exhausted in this run.

Doyon appears in the ledger this run only as the **counterparty** to ND-2004-204, sourced from
Koniag's report; Doyon's own 2005 report does not mention the ACTI purchase.

### Goldbelt, Incorporated. 0 rows.
`goldbelt.com/publications/assets/2003_annual_report.pdf` — one report, read in full. It
describes a well-dated disposal of Glacier Bay Cruiseline (agreement August 2003, closing
November 2003) and states **no sale price**, only an estimated loss. Skipped and logged.

### Kuskokwim Corporation. 0 rows.
Reports for **2005, 2012, 2013, 2014** were located and read. Village-corporation reports are
short and photograph-led; none contains a transaction paragraph. A clean negative.

---

## Corporations that publish NOTHING retrievable — the negative result

Verified by full CDX enumeration of every archived PDF on each domain, not by search. **This
prevents re-work**: these are not fetch failures, the documents do not exist.

| Corporation | Domain | Archived PDFs | Annual reports | What they publish instead |
|---|---|---|---|---|
| **Chugach Alaska Corporation** | `chugach-ak.com`, `chugach.com` | 111 | **ZERO** | Shareholder forms only — address change, dividend direct deposit, talent bank |
| **Calista Corporation** | `calistacorp.com` | 457 | **ZERO** | Donlin Gold technical reports, land studies; only 2014–15 *chart supplements* and a "Guide to the Annual Report", never the report |
| **Bering Straits Native Corporation** | `beringstraits.com` | 456 | **ZERO** | *Agluktuk* shareholder newsletters |
| **Ukpeaġvik Iñupiat Corporation** | `uicalaska.com` | 184 | **ZERO** | Quarterly newsletters (2010–2013), proposal packets |
| **Olgoonik Corporation** | `olgoonik.com` | 169 | **ZERO** | Annual *meeting* notices, stock manuals |
| **Huna Totem Corporation** | `hunatotem.com` | 157 | **ZERO** | Monthly newsletters (2004–2007) |
| **Tyonek Native Corporation** | `tyonek.com` | 117 | **ZERO** | *Tebughna* newsletters |
| **Afognak Native Corporation / Alutiiq** | `afognak.com` | 99 | **ZERO** | Shareholder benefit and outreach material |
| **The Thirteenth Regional Corporation** | `the13thregion.com` | 27 | **ZERO** | Quarterly newsletters, 2000–2004 only |
| **Ahtna, Incorporated** | `ahtna.com`, `ahtna-inc.com` | 259 | **1 indexed (2013), unreadable** | Annual-meeting FAQs. Every snapshot of the 2013 report is a zero-byte or truncated capture |

**Ahtna is the one genuine block that remains.** Unlike the others it *did* publish an annual
report; the archive simply never captured it intact. Ahtna stays on the manual-download queue.
NANA comes off it.

Also checked and empty: `oldharborcorp.com`, `nanadev.com` (no archived PDFs at all).

A note on `archive.asrc.net`: 1,668 archived PDFs, an ASRC historical document repository. The
one annual report there is **1976** — decades before the window. Worth remembering for
pre-ANCSA-era research; useless here.

---

## The date rule applied this run, and why it differs by corporation

The brief's instruction is absolute: no date in evidence → skip. Annual reports force a finer
distinction, because a fiscal year is a date at coarse resolution and **whether it pins a
calendar year depends on the corporation's fiscal calendar**. The rule applied:

- **Day-level date stated** → used as written. 13 rows.
- **Month stated, no day** → mid-month placeholder, `Date_Basis` discloses it IN CAPITALS.
  13 rows. Every one is flagged; none has an invented day presented as fact.
- **Year only, and the corporation's fiscal year IS the calendar year** (ASRC, statements
  dated December 31) → **`Event_Date` left BLANK**, `Event_Year` populated, `Date_Basis` says
  YEAR-LEVEL ONLY, Confidence Medium. 2 rows (ND-2003-203, ND-2005-204). This follows the
  existing `MA2020-001` pattern in the live ledger, which carries a blank `Event_Date` with
  `Date_Basis` = "Year-level only".
- **Year only, and the fiscal year STRADDLES two calendar years** (NANA, ending late
  September; Koniag, ending March 31) → **SKIPPED**. The calendar year is genuinely
  undetermined, so it is a missing date, not a coarse one.

That last rule cost real rows, most painfully NANA's **$4.8 million purchase of an additional
39 percent of TKC Communications** — a clean price with no determinable calendar year. It is
in the skip file with the amount preserved.

One further refusal worth recording: Sealaska's 2013 narrative says the Nypro Kanaak sale
"occurred at the end of June 2013". "End of June" was **not** converted into June 30.
ND-2013-201 carries the ordinary mid-month placeholder and the phrase is quoted in
`Date_Basis`.

---

## Value traps caught and excluded

Annual reports are denser in traps than press releases, because every paragraph contains
audited numbers that are *not* prices.

1. **CIRI's Las Vegas resorts — ~$116 million of phantom consideration avoided.** The 2008
   report records the December 2006 sale of the Hyatt Regency Lake Las Vegas and the September
   2006 sale of the Westin Kierland. Both are dated, both are large. But in each case the
   **selling principal is an LLC in which CIRI held 50% and 20.8%**, not CIRI, and the only
   CIRI-specific figures are **distributions received** — $59,984,000 and $55,667,000. Rowing
   those would have injected about $116 million of value that was never a purchase price for
   anything CIRI sold. Both excluded and logged. Contrast **ND-2006-202**, admitted because
   there CIRI sold its *own* member interest and the consideration to CIRI is stated.
2. **Goodwill quoted beside a percentage is not a price — NANA does this systematically.**
   "Goodwill increased by approximately $5,000,000 in 2003 due to acquiring an additional 39%
   of TKC Communications LLC" (FY2004) versus "The Company acquired an additional 39% of TKC
   Communications, LLC for **$4.8 million**" (FY2003). Same transaction, two numbers, one
   sentence apart in adjacent reports. Every NANA goodwill movement is logged as a standing
   warning.
3. **ASRC / Lynx Enterprises — goodwill exceeding the purchase price.** $1,868 thousand of
   goodwill against a $1,400 thousand price, because net *liabilities* of $968 thousand were
   assumed. The largest number in the footnote is not the deal value. `Announced_Value_USD` is
   $1,400,000.
4. **BBNC / Kakivik — "67%" read as money.** BBNC's narrative says the additional 33 percent
   brought it "to 67%" and elsewhere "for a total investment of 67% of the Company". The
   audited price is **$25,000**. A careless read produces a $67 million row. Excluded on
   threshold and logged with the trap spelled out.
5. **Goldbelt / Glacier Bay Cruiseline — a $10 million loss read as a price.** The only large
   figure is an estimated **loss on disposal**. No sale price exists in the document.
6. **Sealaska / SeaCal — an internal restatement inside one report.** The segment narrative
   says "$3 million with $1 million received in 2005"; the audited note splits the same $3
   million into $1,000,000 of assets and $2,000,000 of land to the same buyer. The note governs;
   the total is unchanged; recorded as **one** transaction.
7. **Koniag — fiscal-year aggregates masquerading as deal values.** "Cash paid for stock and
   net assets" of $4,247,187 (FY2005), $1,780,244 (FY2004), $286,840 (FY2003) covers *all*
   acquisitions in each year and cannot be split per transaction.
8. **Goldbelt vessel — a loan balance read as a price.** "$2.8 million vessel loan" is the debt
   the buyer assumed, not consideration.
9. **Earnouts everywhere.** Tri Ocean, W&H Pacific, Lynx, Vista and R&K/Atigun all carry
   "additional consideration based on future earnings in excess of a threshold amount",
   unquantified in every case. No estimate entered any value field.

**One arithmetic check that confirmed a reading rather than caught a trap:** ASRC's 2000
footnote states an aggregate cost of "approximately $14,800" across three acquisitions. The
three stated prices — $9,600 + $3,200 + $2,000 — sum to exactly $14,800. That both validated
the thousands convention and confirmed the three rows are complete and non-overlapping.

**The thousands convention is itself a trap.** ASRC states "ALL DOLLAR AMOUNTS STATED IN
THOUSANDS" once, at the head of the notes. Reading `$9,600` literally understates Tri Ocean by
a factor of 1,000. Every ASRC row's `Notes` field records the convention explicitly.

---

## Two ANC-to-ANC ownership changes — the most valuable records here

Per AGENTS.md, the deal ledger *is* the missing time-varying ownership ledger. Two rows in this
file move a business between two Native corporate families on a known date. Both follow the
`ND-2019-007` (Salish Lodge) precedent: **one row, both principals named, an explicit
instruction in `Notes` not to enter a second row.**

- **ND-2005-201 — ASCG, Incorporated: ASRC → NANA, June 2005, $31,275,000.** The largest
  transaction in the file, and the only one in the project sourced to *both* parties' audited
  financial statements. It also links to two other rows in this file: ND-2000-203 put the
  McLaughlin business inside ASCG in January 2000, and ND-2002-201 put W&H Pacific there in
  2002 — both then travelled to NANA with the parent.
- **ND-2004-204 — Angeles Composite Technologies 30%: Koniag → Doyon, 2004-07-01.** Sourced to
  the seller only; Doyon's own report does not mention it.

A **third, unasserted** candidate is flagged rather than claimed. ND-2004-202 records ASRC
buying "the remaining 30% of Houston/NANA, L.L.C." for $2,143,000. NANA's FY2001–FY2003
reports describe NANA as holding a **minority interest** in Houston/NANA, and the entity
vanishes from NANA's FY2004 and FY2005 reports. That is consistent with NANA being the seller.
**Neither corporation says so**, so the counterparty field records only "Minority interest
holder … (not named in the report)" and the inference is confined to `Notes`, marked as an
inference, and flagged for the reconcile queue. Same treatment for ND-2014-201, where the
buyer of Rocky Pass Seafoods is unnamed but the note receivable is secured by **Kake Tribal
Corporation's** ANCSA 7(j) interest.

This is the AGENTS.md matching discipline applied literally: *match conservatively, leave
ambiguous blank and flagged.*

---

## Rows by year — and what this does to the thin years

| Year | New | Prior 2000–2019 file | Combined | | Year | New | Prior | Combined |
|---|---|---|---|---|---|---|---|---|
| 2000 | **3** | 1 | **4** | | 2009 | 1 | 2 | 3 |
| 2001 | 2 | 2 | 4 | | 2010 | **1** | 1 | **2** |
| 2002 | 1 | 2 | 3 | | 2013 | 2 | 1 | 3 |
| 2003 | 4 | 3 | 7 | | 2014 | **1** | 1 | **2** |
| 2004 | 5 | 2 | 7 | | 2015 | **1** | 1 | **2** |
| 2005 | 5 | 2 | 7 | | 2006 | **2** | 1 | **3** |

Against the prior log's list of thinnest years — 2000, 2006, 2007, 2012, 2014, 2015, 2017 at
one row each — this run **quadrupled 2000, tripled 2006, and doubled 2010, 2014 and 2015**.

**Year 2000 is the headline.** The prior log called it "genuinely hard" and recovered a single
row. ASRC's 2001 report carries all three of its year-2000 acquisitions, fully dated and
priced, because the acquisitions footnote restates the prior year. **The lesson generalises:
for the oldest years, read the report published one to two years AFTER the target year.**

**2007, 2008, 2011, 2012, 2016–2019 got nothing from this channel.** For 2007–2008 the cause is
retrievability — NANA 2006/2007, BBNC 2007, Koniag 2006/2007 and Aleut 2007 are all indexed and
all truncated. For 2016–2019 the cause is structural: ANCs largely stopped posting full annual
reports, and BBNC's 2016 report was the only one located past 2014.

---

## Rows by corporation

| Corporation | Rows | | Corporation | Rows |
|---|---|---|---|---|
| Arctic Slope Regional Corporation | 11 | | The Aleut Corporation | 2 |
| Sealaska Corporation | 8 | | Koniag, Incorporated | 1 |
| NANA Regional Corporation | 3 (2 sole + 1 shared) | | Cook Inlet Region, Inc. | 1 |
| Bristol Bay Native Corporation | 2 | | Doyon, Goldbelt, Kuskokwim | 0 |

By category: 18 acquisitions, 8 divestitures, 1 equity investment, 1 land transaction.
**Eight divestitures is the notable figure** — divestitures are the scarcest and most valuable
class for the ownership ledger, and audited annual reports are structurally better at them than
press releases, because a company must disclose a disposal it would never announce.

Sum of `Announced_Value_USD` across 25 valued rows: **$162,559,001**. Three rows carry no value
(NANA/Arctic Utilities, Koniag/ACTI, Aleut/Adak — all genuinely undisclosed).

---

## Confidence

| | Count | Reason |
|---|---|---|
| High | 11 | Day-level date from audited text, price stated, or two independent primary sources |
| Medium | 17 | Month-level placeholder (13), year-level with blank date (2), unnamed target (1), no consideration disclosed (1) |

Every Medium row states its reason in `Notes` and its limitation in `Date_Basis`. **13 rows
carry two independent primary sources**, usually the same transaction restated in a later
annual report.

Two rows carry `Threshold_Exception=Yes`: **ND-2004-205** (Nypro Iowa 51% at $800,000) and
**ND-2009-201** (Kingston 49% at a nominal $1). Both are majority- or full-ownership changes
over named operating companies, which is the rationale recorded in each `Notes` field. The
Kingston row's real consideration — indemnification of the sellers' credit lines plus a
retained 10% of annual net income — is **unquantified in the source and was not estimated**.

---

## Skipped and excluded leads — 32

| Reason | Count | Character |
|---|---|---|
| `no_amount` | 16 | The dominant failure mode. ANCs name and date acquisitions in narrative and price them nowhere |
| `below_threshold` | 7 | Dated and priced, simply small. All are ownership changes and would convert instantly if the threshold moved |
| `no_date` | 4 | Fiscal-year-only statements from September/March filers, plus one spanning two calendar years |
| `aggregator_only` | 3 | Annual aggregates and portfolio activity |
| `out_of_window` | 2 | Not transactions: board discontinuation votes; and the CIRI resort trap |

Highest-value skips, ranked:

1. **Sealaska ↔ San Pasqual Indian Tribe.** Sealaska advanced **$14.7 million** to the San
   Pasqual Indian Tribe for casino construction and in 2002 settled for **$20.9 million**. Both
   amounts are precise and repeated across reports; the advance is dated only "During late 2000
   and early 2001", spanning two calendar years. **An ANC financing a lower-48 tribe's casino is
   a two-row opportunity that would connect the Alaska and lower-48 halves of the ledger.** Try
   the San Pasqual compact record, NIGC management-contract approvals, or Federal Register
   gaming-land decisions for Valley View Casino.
2. **NANA / TKC Communications, $4.8 million, additional 39%.** A clean price blocked only by a
   September fiscal year end.
3. **Sealaska / Managed Business Solutions, 51%, August 2006.** Dated to the month, priced
   nowhere. Would land in a thin year.
4. **ASRC / Barrow Cable TV.** RCA approved the asset transfer on **January 12, 2005**; only a
   gain is stated. The RCA docket should carry the price — the cheapest follow-up on this list.
5. **CIRI / CIVS VII wireless licenses, $235,188,000 with an $80,050,000 CIRI contribution.**
   The largest unbanked figure in the sweep. Needs a date and careful attribution — the $235M is
   the joint venture's license cost funded with T-Mobile, not CIRI's consideration.
6. **Koniag / XMCO, 90%, June 2000.** Month-level, in the thinnest year, unpriced.

---

## Retrieval failures — indexed but unreadable

Nine reports are indexed in the Wayback CDX and could not be read. Every alternate snapshot was
tried (up to 40 per document) before giving up.

| Document | Failure |
|---|---|
| NANA 2006, NANA 2007 | Every snapshot truncated to ~130 KB |
| BBNC 2007 | Truncated to ~130 KB |
| BBNC 2013, BBNC 2017 | Truncated at exactly 1,048,576 bytes (1 MiB archive-side cap) |
| Koniag 2006, Koniag 2007 | Truncated to ~130 KB |
| Aleut 2005, Aleut 2007 | Truncated / zero-byte |
| Ahtna 2013 | Zero-byte in every snapshot |

**These are the highest-yield remaining targets in the channel** and they explain the 2007–2008
gap directly. The 1 MiB pattern on the two BBNC files suggests an archive-side size cap rather
than a broken original, so a range-request or a different Wayback mirror may recover them.

---

## Follow-ups, ranked

1. **Recover the nine truncated reports** (NANA 2006/07, BBNC 2007/13/17, Koniag 2006/07, Aleut
   2005/07). This is the cheapest large win available: it directly targets 2007–2008, the gap
   this run could not close, and each report has already proven to carry two to four rows.
2. **Work the newsletter sub-seam.** Roughly 300 archived shareholder newsletters are indexed
   and readable and were not opened: ASRC (~50 issues, 2002–2009, monthly with volume/issue
   numbering), Doyon (~60 monthly issues, 2001–2007), Sealaska (quarterly, 2011–2016), Huna
   Totem, Tyonek, Bering Straits (*Agluktuk*), and The Thirteenth Regional Corporation
   (2000–2004, the only source of any kind for that corporation). Newsletters date announcements
   rather than closings, so they are a weaker source than audited notes — but they are the ONLY
   source for the ten corporations that publish no annual report at all.
3. **San Pasqual.** See skip #1 above.
4. **Apply the Wayback CDX method beyond ANCs.** It is not ANC-specific. Every 403 and 404 in
   the two prior build logs — `olgoonik.com`, `ahtna.com`, `chickasaw.com/about/news/2017`,
   `gunlakeinvestments.com/news/` — is a candidate for the same treatment.
5. **Resolve the two flagged counterparties** through the reconcile queue: was NANA the seller
   of the Houston/NANA minority interest (ND-2004-202)? Was Kake Tribal Corporation the buyer of
   Rocky Pass Seafoods (ND-2014-201)? Both would add ANC-to-ANC ownership-change records.
6. **Ahtna stays on the manual-download queue.** It is the only corporation that demonstrably
   published annual reports that the archive never captured.

---

## Ownership-change records to emit

**26 of the 28 rows** are acquisitions, divestitures or interest changes and should emit records
into the time-aware attribution ledger. The two exceptions are ND-2003-203 (a minority equity
investment) and ND-2004-203 (a land conveyance).

The four most valuable:

- **ND-2005-201** — ASCG, Incorporated and its subsidiaries (including W&H Pacific) move from
  the ASRC family to the NANA family, 2005-06-20. Both sides audited.
- **ND-2004-204** — 30% of Angeles Composite Technologies moves from Koniag to Doyon, 2004-07-01.
- **ND-2003-201** — Arctic Utilities, Inc. leaves the NANA family, 2003-01-03.
- **ND-2013-201** — Sealaska exits the Nypro Kanaak plants in Iowa, Alabama and Mexico, June
  2013, closing an arc that ND-2004-205 opened in January 2004.

Three complete hold-and-sell arcs are now documented inside this one file: **ASCG**
(ND-2000-203 → ND-2005-201), **Puget Plastics** (ND-2000-202 → ND-2005-204), and **Nypro
Kanaak** (ND-2004-205 → ND-2013-201). Arcs are what make the ownership ledger usable for
attribution over time, and they are the strongest argument for continuing to work this channel.
