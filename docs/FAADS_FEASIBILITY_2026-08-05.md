# FAADS feasibility — can Dataset 3 reach the 2000 floor?

*Investigation run 2026-08-05. Evidence trail: `logs/26_faads_2026-08-05.log`.*
*Prime directive observed: zero fabrication. No pre-2008 assistance data was synthesised,
estimated, or reconstructed. Nothing was attributed to any tribe, ANC, or NHO.*

---

## The short answer

| Question | Answer |
|---|---|
| Is the FY2000–2007 gap closable? | **Partly. FY2001–2007 yes. FY2000 no.** |
| Is FAADS the source? | **No — and this is the finding.** USAspending itself holds FY2001+ |
| Actual FAADS coverage | **FY1982–FY2010** (confirmed, not assumed) |
| Joinable recipient identifier pre-2008? | **No. 0.0% DUNS, 0.0% UEI.** Name only |
| Is splicing at FY2008 defensible? | **Yes — the seam is not at FY2008.** The real break is **FY2010** |

**Recommendation: extend Dataset 3 back to FY2001 from USAspending, publish the floor
as FY2001 (not FY2008, not 2000), and carry every pre-2008 row unattributed at Tier C.**

---

## 1. What FAADS is, its true coverage, and where it lives now

The Federal Assistance Award Data System was the Census Bureau's quarterly collection of
standardised records on grants, insurance, loans, subsidies and other economic assistance
awarded by federal agencies — roughly 600 programs across every executive department with
grant-making authority.

**Coverage is FY1982–FY2010.** Verified against the NARA Catalog series record, not
inferred: series naId 604955 runs `1981-10-01` → `2010-09-30`. A predecessor series
(naId 604982, RG 381, Community Services Administration) covers FY1981 alone. The series
ends at FY2010 because the Census Bureau's Federal Financial Statistics program was
terminated; FY2011 forward went to USAspending.gov.

The commonly cited "FY1982–FY2010, with FAADS PLUS as a transitional format" is
**correct**. FAADS PLUS is the expanded submission format introduced in 2007 under the
Federal Funding Accountability and Transparency Act (P.L. 109-282); it is what agencies
began sending to USAspending, and it is the format that added DUNS.

**Where it lives now:**

- **NARA, National Archives at College Park — Electronic Records.** 116 data files, 3
  electronic documentation files, 2 linear feet of paper documentation, 34,200,000
  logical data records. Access and use restrictions: **Unrestricted**.
  <https://catalog.archives.gov/id/604955>
- **NARA AAD** (Access to Archival Databases), series `s=408` — all 116 quarterly files
  are individually searchable online, including every quarter of FY2000–2007.
  <https://aad.archives.gov/aad/series-description.jsp?s=408&cat=GS30>
- **Not at NBER.** Checked and ruled out: `data.nber.org/faads/` → 404,
  `nber.org/research/data/federal-assistance-award-data-system-faads` → 404,
  `data.nber.org/data/faads.html` → 403. There is no NBER mirror.
- **Internet Archive** holds the Census documentation but not the data.
- **USAspending.gov holds the FY2001+ data itself** — see §4.

---

## 2. Is it obtainable?

### From NARA — yes, but only as a paid mail/email order

AAD is a record-at-a-time search interface. It offers no export or bulk-download control.
Worse for our purposes, the fielded-search form for the FAADS files exposes only **eight**
searchable fields:

> RECIPIENT NAME · RECIPIENT CITY NAME · RECIPIENT COUNTY NAME · RECIPIENT STATE CODE ·
> FEDERAL AGENCY/ORGANIZATIONAL UNIT CODE · TYPE OF ASSISTANCE TRANSACTION ·
> RECORD TYPE · PROJECT DESCRIPTION

**Neither CFDA program number nor type of recipient is searchable.** So AAD cannot even be
used to isolate tribal recipients or a specific program — the two things that would have
made it useful without name matching.

The NARA Catalog record lists no digital objects. The only route to the actual files is a
written reproduction order with payment in advance:

> "Extracts of data files are not available, nor are printouts of full data files."
> Fees (from 2012-10-01): $20.00 minimum; $17.00/file for 1–10 files; **$14.00/file for
> 11+ files**. Delivered electronically via secure link, or on CD/DVD. Fixed-length files
> default to ASCII text with record delimiters.
> — <https://www.archives.gov/research/order/electronic-records>
> Electronic Records Reference Branch · cer@nara.gov · (301) 837-0470

FY2000–2007 is 32 quarterly files ≈ **$448** plus documentation. This is a human action,
not an agent action. No access control or paywall was bypassed at any point in this
investigation.

### From USAspending — yes, free, immediately, and this is the better answer

See §4. This is the material finding.

---

## 3. Schema, and the identifier situation

The authoritative Census record layout was recovered from the Internet Archive (the live
`census.gov/govs/faads/usrguide.txt` is now 404) and is staged at
`data/raw/external/faads/census_faads_usrguide.txt`. FAADS is a **624-byte fixed-width
record with 34 fields**. The full field map is in the log.

The fields that matter here:

| # | Field | Verdict |
|---|---|---|
| 1 | CFDA Program Number (6-pos) | **Present.** 100.0% populated in retrieved data |
| 3 | Recipient Name (45 chars) | Present — and it is the *only* recipient identifier |
| 11 | Type of Recipient | **Present, and carries an explicit tribal code** |
| 17 | Federal Funding Amount | Present, whole dollars |
| 22 | Obligation/Action Date | Present, `yymmdd` |
| 25 | Type of Assistance Transaction | Present, codes 02–11 |
| 26 | Record Type | 1 = county aggregate, 2 = action-by-action |
| — | DUNS | **Absent** |
| — | EIN | **Absent** |

### The deciding constraint

**There is no DUNS and no EIN anywhere in the FAADS layout.** The Census documentation
says so directly — FAADS "does not currently collect DUNS information for recipients of
Federal assistance." DUNS arrives only with FAADS PLUS in 2007. UEI did not exist until
2022 and can never appear in this era.

This is not merely a documentary claim. It is confirmed empirically against data actually
retrieved: across **60,661 Department of the Interior assistance transactions FY2001–2007**,
`recipient_duns` and `recipient_uei` are populated on **0 rows — 0.0%**.

**Joining pre-2008 assistance to the Cedar Press spine is therefore a name-matching
problem.** Per the brief, that is the method ruled against 9 times out of 9, and it is
reported here as the deciding constraint. **No join was attempted.** `tribe_id` is blank
on every row of the delivered file.

### The partial escape hatch — a source-provided tribal flag

Field 11 *Type of Recipient* carries `11 = Indian tribe` as an explicit source code. In
the USAspending rendering of the same era this is `business_types_code`, a stable single
letter, with **`I` = "INDIAN/NATIVE AMERICAN TRIBAL GOVERNMENT (FEDERALLY RECOGNIZED)"**.
It is **100.0% populated**.

This matters, and it is worth being precise about what it does and does not buy:

- **It does isolate tribal rows with zero name matching.** 7,646 of the 60,661 retrieved
  Interior FY2001–2007 transactions carry code `I`.
- **It does not say which tribe.** Per-entity attribution still requires the name.

So **aggregate** tribal assistance totals for FY2001–2007 are constructible with zero
fabrication and zero name matching. **Per-tribe** series are not.

### Granularity caveat

Record Type 1 rows are county aggregates — recipient name reads `MULTIPLE RECIPIENTS` and
~14 of the 34 fields are blank *by design*. These are unattributable in principle, not
merely in practice. Empirically 0.0% of the retrieved Interior rows are record type 1, but
this must be checked per agency before any other agency's data is used.

---

## 4. The material finding — USAspending already holds FY2001+

Cedar Press's stated premise is that "USAspending assistance data begins FY2008." **That
is true only of the search index.** Asked for FY2002 assistance, the API replies verbatim:

> `start_date falls before the earliest available search date of 2007-10-01. For data
> going back to 2000-10-01, use either the Custom Award Download feature on the website
> or one of our download or bulk_download API endpoints`

`2000-10-01` is the first day of FY2001. This was **verified by actual retrieval**, not by
reading documentation:

```
POST https://api.usaspending.gov/api/v2/bulk_download/awards/
  prime_award_types 02..11 · date_type action_date
  date_range 2002-10-01 .. 2003-09-30
  agencies [{awarding, toptier, "Department of the Interior"}]
→ status finished · total_rows 8,180 · total_columns 112 · 1,042,631 bytes
```

The returned file carries the **identical 112-column modern USAspending assistance schema**
(`assistance_transaction_unique_key` … `last_modified_date`). Same columns, same code sets,
same producer as the FY2008–2023 data already in Dataset 3.

**Consequence: FY2001–2007 does not require FAADS from NARA at all.** It requires re-running
the existing Dataset 3 pull with an earlier date range. Only **FY2000**
(1999-10-01 – 2000-09-30) lies outside USAspending, and reaching it means the $448 NARA
order for data that would carry no identifiers anyway.

---

## 5. Comparability to the FY2008+ series — would splicing produce a false break?

This mattered more than raw availability, so it was tested directly rather than reasoned
about. The Department of the Interior — the dominant tribal assistance agency in this
window — was retrieved in full for **FY2001 through FY2011**, straddling the seam.

| FY | rows | oblig $M | DUNS% | UEI% | CFDA% | bizType% | tribal-flagged |
|---|---|---|---|---|---|---|---|
| 2001 | 6,951 | 1,019.6 | 0.0 | 0.0 | 100.0 | 100.0 | 1,219 |
| 2002 | 6,842 | 998.8 | 0.0 | 0.0 | 100.0 | 100.0 | 1,176 |
| 2003 | 8,180 | 951.7 | 0.0 | 0.0 | 100.0 | 100.0 | 739 |
| 2004 | 10,703 | 1,698.1 | 0.0 | 0.0 | 100.0 | 100.0 | 1,138 |
| 2005 | 9,088 | 1,877.5 | 0.0 | 0.0 | 100.0 | 100.0 | 1,145 |
| 2006 | 9,235 | 1,336.6 | 0.0 | 0.0 | 100.0 | 100.0 | 1,388 |
| 2007 | 9,662 | 1,466.2 | 0.0 | 0.0 | 100.0 | 100.0 | 841 |
| **2008** | **11,585** | **2,188.6** | **0.0** | **0.0** | **100.0** | **100.0** | **1,629** |
| 2009 | 12,295 | 2,615.4 | 0.0 | 0.0 | 100.0 | 99.3 | 5,339 |
| **2010** | **3,273** | **794.0** | **14.3** | **14.3** | 100.0 | 100.0 | **141** |
| 2011 | 3,452 | 799.2 | 99.9 | 99.7 | 100.0 | 100.0 | 74 |

### Dollars, codes and programs are on the same basis

- **Assistance types are the same 02–11 CFDA-derived scheme on both sides.** Pre-2008
  Interior uses 05, 04, 06, 03, 02, 10, 11; Cedar's FY2008–2023 file uses 06, 04, 02, 03,
  05, 10, 11. No remapping needed.
- **CFDA program number is 100% populated on both sides**, same 6-position format.
- **Recipient business-type codes are a stable single-letter scheme across FY2001–FY2011.**
  No recoding break.
- **Obligations are the same `federal_action_obligation` field**, whole dollars, signed.

### The seam is at FY2010, not FY2008

FY2007 → FY2008 is smooth on every measure: rows 9,662 → 11,585, dollars $1,466M → $2,189M,
identifier fill unchanged, schema identical. **Splicing FY2007 to FY2008 introduces no
discontinuity.**

FY2009 → FY2010 is not smooth. Rows fall 73% (12,295 → 3,273), obligations fall from
$2,615M to $794M, tribal-flagged rows collapse from 5,339 to 141, and DUNS/UEI appear for
the first time — **all in the same year**. That is the signature of a reporting-system
changeover, and it lands exactly where FAADS was terminated (end of FY2010).

### This is a defect in the *current* Dataset 3, not only in a backfill

Cross-checked against `data/clean/federal_funding_transactions.csv`, DUNS fill by agency:

| agency | FY2008 | FY2009 | FY2010 | FY2011 |
|---|---|---|---|---|
| Health and Human Services | 99.3% | 99.6% | 99.6% | 100.0% |
| Agriculture | 98.7% | 98.0% | 97.4% | 98.5% |
| Education | 100.0% | 100.0% | 100.0% | 100.0% |
| **Interior** | **0.0%** | **0.0%** | **10.6%** | **100.0%** |
| Environmental Protection Agency | 99.8% | 100.0% | 100.0% | 100.0% |
| Housing and Urban Development | 97.8% | 93.1% | 88.7% | 100.0% |

**The identifier break is agency-specific, not year-specific.** Interior/BIA reported no
DUNS at all until FY2010 and reached full coverage only in FY2011, while every other major
agency was already at ~99–100% in FY2008. Cedar Press's 1,629 Interior FY2008 rows and
5,339 Interior FY2009 rows are *already* carried with 0% UEI in the published dataset.

A validation worth recording: those counts — 1,629 and 5,339 — match the independently
retrieved USAspending Interior tribal-flagged row counts **exactly**. Dataset 3's Interior
rows *are* the rows carrying `business_types_code = 'I'`. The retrieval method and the
tribal-flag approach both check out.

**Live warning to add:** the Interior series in Dataset 3 drops from 5,339 tribal rows in
FY2009 to 141 in FY2010 and 74 in FY2011. Whatever the cause, an Interior/BIA time series
read straight across FY2009→FY2010 will show a ~97% collapse that is a reporting artefact,
not a funding change. This is in the published data now.

---

## 6. What was acquired

Staged under `data/raw/external/faads/` with `_SOURCE_MANIFEST_faads.csv`
(URL, description, bytes, row count, SHA-256, retrieved date for all 16 artefacts).

**Documentation** — Census FAADS user guide (34,600 bytes, via Internet Archive), NARA
series record, AAD series listing, AAD fielded-search form.

**Data** — Department of the Interior assistance prime transactions, FY2001–FY2011, eleven
quarterly-year zips, retrieved from the USAspending bulk-download API.

**Built:** `data/clean/faads_transactions.csv`

- **60,661 transactions · FY2001–2007 · $9,348,473,200.00 obligated**
- 7,646 rows carry the federally-recognized tribal-government flag
- SHA-256 `9459ce8de09812e80e554d31babe73400fc34068d75391b3033fa0561cfc3c87`
- `tribe_id` is **blank on every row**. No entity linking performed.
- Every row carries a per-row `source_url` (USAspending permalink, 100% populated),
  `api_endpoint`, `fetched_date`, and `source_file`.

### Scope limits of this file — read before using it

1. **Department of the Interior only.** It is not the full FY2001–2007 assistance
   universe. Interior is the largest single tribal assistance agency, so it is the most
   valuable one agency, but HHS, Education, USDA, HUD, EPA and Justice are **not** in this
   file. Do not read it as complete.
2. **FY2001–2007, not FY2000.** FY2000 is outside USAspending's reach entirely.
3. **Untested dimension, stated honestly:** the USAspending bulk-download API began
   refusing connections from this IP after roughly 20 generated downloads. The Interior
   series completed before the limit; **EPA and HHS pre-2008 probes did not**, and ~15
   minutes of backoff did not clear it. So "0% DUNS pre-2008" is **proven for Interior
   across FY2001–2009** and is **untested for other agencies pre-2008**. Given those
   agencies sit at ~99–100% in FY2008, the pre-2008 picture for them is genuinely open.
   It must not be asserted in either direction until measured.

---

## 7. Recommendation

**Extend Dataset 3 back to FY2001 — but from USAspending, not from FAADS — and publish
the floor as FY2001.**

1. **Do not order FAADS from NARA.** It costs ~$448, arrives as fixed-width ASCII by mail
   order, is one system generation removed from the FY2008+ series, and carries strictly
   *less* than what USAspending already serves for free for the same years. The only thing
   it uniquely buys is FY2000 — a single year, with no identifiers, requiring name
   matching. Not worth it.

2. **Backfill FY2001–2007 from the USAspending bulk-download API**, the same source and
   the same 112-column schema as the existing FY2008–2023 data. Complete the remaining
   agencies once the rate limit clears. The Interior series is already in hand.

3. **State the temporal floor for Dataset 3 as FY2001, and publish that limit.** The
   project-wide floor of 2000 cannot be met by this dataset. FY2000 is one year short and
   the honest move is to say so in the coverage table rather than reach for a source that
   would degrade the series to close it.

4. **Carry every pre-2008 row unattributed — Tier C.** With 0% DUNS and 0% UEI, the only
   join is on name, and that is ruled out. These rows are a discovery pool, not a
   publishable per-tribe series.

5. **Publish aggregate pre-2008 tribal totals if wanted — they are legitimate.** The
   source-provided `business_types_code = 'I'` flag isolates federally-recognized
   tribal-government recipients at 100% population with no name matching. "Total federal
   assistance obligated to federally recognized tribal governments, FY2001–2007" is a
   defensible published number. "Assistance to *the Navajo Nation*, FY2001–2007" is not,
   and will not be until Elijah rules on a name-based route.

6. **Add the FY2010 Interior discontinuity to the live warnings** in `STATE_OF_BUILD.md`.
   It affects the currently published dataset, independent of any backfill.

### What needs a ruling from Elijah

- Accept **FY2001** as Dataset 3's published floor, against the project-wide 2000 target?
- Is the pre-2008 window worth carrying at all as an unattributed Tier C pool, given it
  can never reach per-tribe attribution without a name-matching ruling?
- Should aggregate tribal totals from the `business_types_code = 'I'` flag be published
  for FY2001–2007, sitting alongside a per-tribe series that starts FY2008?
