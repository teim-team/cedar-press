# ANCSA Portal v2 — OCR, village corporations and 2020–2026, harvested 2026-08-05

Dataset 1 (Indian Country Deals). Second pass on the Alaska Department of Commerce, Community and
Economic Development, Division of Banking and Securities STAR portal. This run closes the three
follow-ups the first pass named in `docs/ANCSA_PORTAL_BUILD_LOG.md` §9: OCR the image-only PDFs,
retrieve and mine village-corporation annual reports, and work 2020–2026 systematically.

**Outputs**
- `data/clean/deals_ancsa_portal_v2_additions.csv` — **43 deal rows**, prefix `ANCSA2-`
- `review/deals_skipped_ancsa_portal_v2.csv` — **24 skipped leads**
- `data/raw/external/ancsa_portal_v2/` — **80 village-corporation PDFs** + `_SOURCE_MANIFEST_V2.csv`
- `data/interim/ancsa_ocr/` and `data/interim/ancsa_ocr_v2/` — OCR text, one JSON per document
- `data/clean/ancsa_filings_index.csv` — 80 rows flipped to `downloaded = yes` (backup at `.bak_2026-08-05_v2`)
- Log: `logs/39_ancsa_portal_v2.log`

Nothing was written into `deals_2026_ytd.csv`, `deals_historical_2020_2025.csv`, `data/spine/`,
`data/clean/cedar_*` or `review/cedar_review*.html`. The additions file was validated column-for-column
against `deals_historical_2020_2025.csv` (32 columns, identical order). Deal_IDs were checked against
both live ledgers and all seven existing `deals_*_additions.csv` files — 875 existing Deal_IDs,
**zero collisions, zero internal duplicates**.

---

## 1. Task 1 — OCR

**The manifest's `text_extractable` flag is a whole-document boolean and it is wrong in both directions.**
That is the single most useful finding of this task, because the first pass built its OCR queue from it.

- It **missed 127 documents.** A page-level scan of all 171 downloaded files found **994 image-only
  pages across 155 documents**, not 28. The flag says "yes" as soon as a document contains any
  extractable text at all. The **2017 ASRC annual report is flagged `yes`** and is 34 image-only pages
  out of 38 — which is exactly why the first pass could not date Finite and USC and wrongly assumed
  the file was not in the OCR queue.
- It **over-flagged 9.** Of the 28 PDFs flagged image-only, nine carry a small but genuine text layer
  (170–3,477 characters) and have no image-only pages: seven NANA 2018 annual-meeting items
  (announcement, Facebook event, proxy example, shareholder cover letter, yellow envelopes, postcard
  advertisement, poster advertisement), one 2022 Sealaska proxy document and a one-page 2024 Chugach
  cover. None is a deal source. Logged as `SK2-ANCSA-024` so the backlog is not re-queued.

### What was run

`pytesseract` was importable but **the tesseract binary is not on PATH**; it is installed at
`C:\Users\esm247\AppData\Local\Programs\Tesseract-OCR\tesseract.exe` (**v5.5.0.20241111**, `eng` and
`osd` language data). Set `pytesseract.pytesseract.tesseract_cmd` to that path. Pages were rendered
with PyMuPDF at 300 dpi grayscale, about 1.0–2.5 s per page.

| Corpus | Documents | Pages attempted | Pages returning ≥100 chars | Characters recovered |
|---|---|---|---|---|
| Regional (the 171 first-pass PDFs) | 155 | 994 | 566 | 1,229,959 |
| Village (the 80 retrieved here) | 64 | 629 | 397 | 773,545 |
| **Total** | **219** | **1,623** | **963** | **2,003,504** |

Of the 28 manifest-flagged PDFs specifically, **19 had image-only pages and were OCRed; 11 returned
1,000+ characters and 1 returned 100–999.** The seven that returned under 100 characters are Doyon
settlement-trust cover sheets and a NANA prize card — genuinely blank pages, not OCR failures. The
five PNGs (Sealaska independent-candidate proxy material) OCRed to 41–337 characters each and contain
no transaction.

### What OCR actually recovered

**9 of the 43 rows in this run exist only because of OCR**, plus one date upgrade:

| Row | What OCR unlocked |
|---|---|
| `ANCSA2-2017-001` ASRC / Finite Holdings, May 2017, $7,700,000 | Resolves `SK-ANCSA-001` |
| `ANCSA2-2017-002` ASRC / US Coatings, September 2017, $17,500,000 | Resolves `SK-ANCSA-001` |
| `ANCSA2-2017-003` CIRI / Portage Inc., 20 Jan 2017, $24,267,000 | 2017 CIRI report is 93/93 image-only |
| `ANCSA2-2016-001` CIRI sells CATC, 11 Mar 2016, $45,000,000 | same document |
| `ANCSA2-2021-005` BSNC / Central Environmental + 4, 23 Oct 2021, $38,403,000 | 2021 and 2022 BSNC reports are 64/64 image-only |
| `ANCSA2-2022-007` Calista / Troy 7, 24 Jun 2022, $7,951,426 | corrupt text layer, re-OCRed at 400 dpi |
| `ANCSA2-2022-008` Calista / StraitSys, 29 Jul 2022, $3,090,274 | same |
| `ANCSA2-2021-006` Calista / Demil Transport, 2 Jun 2021, $3.1M | same |
| `ANCSA2-2020-004` Calista / Nordic Well Servicing, 1 Jan 2020, $58,355,884 | same; resolves half of `SK-ANCSA-013` |
| `ANCSA2-2022-006` Huna Totem / Icy Strait Brewing | **date upgraded** from month-level "January 2022" to exact **1 February 2022** |

**A second failure mode worth recording: a corrupt embedded text layer.** The FY2022 Calista annual
report is not image-only — `text_extractable` says yes and PyMuPDF returns 136,000 characters — but
the PDF's own text layer is itself bad OCR. It renders "Acquisitions" as "Acquishions", "liabilities"
as "liabifities", and mangles every figure in the consideration table (`!Z42,69:[l`). Extracting
values from it would have been fabrication with a plausible-looking source. The pages were
**re-OCRed at 400 dpi** and the clean re-read cross-foots two ways
(Troy 7 $7,951,426 + StraitSys $3,090,274 = $11,041,700; net assets $1,329,494 + goodwill
$9,712,206 = $11,041,700). Screen for this: a document that extracts plenty of text but whose prose
contains impossible words is more dangerous than one that extracts none.

`SK-ANCSA-002` also closed: the first pass logged an unidentified 2016 ASRC target "SCI" at $16,274
thousand. The OCR of the 2017 report shows the same column headed **BCI — Builders Choice, Inc.** —
already recorded as `ANCSA-2016-003`. "SCI" was a misread. No row was owed.

---

## 2. Task 2 — village corporations

All seven named filers retrieved in full: **80 annual reports, 100% of what the index attributes to
them**, every year each appears, 2016–2026. Downloads throttled at 4 s; zero failures.

| Corporation | Reports in index | Retrieved | Rows |
|---|---|---|---|
| Ukpeaġvik Iñupiat Corporation | 17 | 17 | **5** |
| Sitnasuak Native Corporation | 18 | 18 | **1** |
| Huna Totem Corporation | 15 | 15 | **2** |
| Goldbelt Incorporated | 11 | 11 | 0 |
| Olgoonik Corporation | 11 | 11 | 0 |
| Tikigaq Corporation | 6 | 6 | 0 |
| Kuukpik Corporation | 2 | 2 | 0 |
| **Total** | **80** | **80** | **8** |

**8 village-corporation rows, $112,365,905** — the first village rows in this dataset.

UIC is the whole story. Its audited financial statements carry a `Business Acquisition` note in
*every* year, each with an exact date, an exact cash consideration and an acquisition-date allocation
table that correctly nets out the noncontrolling interest:

- 31 Mar 2020 — Johansen Construction + Highmark Concrete, 51%, **$4,080,000**
- 19 May 2022 — HC Construction Holdings + 4 subsidiaries, 70%, **$23,008,605**
- 28 Feb 2023 — HME Construction (via KUUK), 100%, **$18,000,000**
- 29 Nov 2024 — Delta Strategies and Solutions, 70%, **$41,772,300**
- 31 Dec 2025 — Northbank Civil & Marine, 51%, **$11,730,000**

That is a five-transaction, six-year acquisition programme by a single village corporation, none of
it previously in the ledger with a value. UIC discloses better than most regionals.

Sitnasuak and Huna Totem each yielded rows but bury them: Sitnasuak's Bennettsville price is in
Note 17, not the management discussion; Huna Totem's Icy Strait Brewing note is on an image-only page.

**Goldbelt, Olgoonik, Tikigaq and Kuukpik disclose no transactions at all** (`SK2-ANCSA-020`). This is
a real negative finding, not a retrieval gap — all 30 of their filings were retrieved and searched,
including OCR of the two fully image-only Tikigaq reports. Goldbelt's only dated, priced events are
two unattributed property purchases; Tikigaq's is an unpriced Point Hope real-estate sale.

---

## 3. Task 3 — 2020–2026

**39 of the 43 rows fall in 2020–2026**, worth **$1.88 billion**.

| Year | Rows | Value as written |
|---|---|---|
| 2016 | 1 | $45,000,000 |
| 2017 | 3 | $49,467,000 |
| 2020 | 4 | $141,063,884 |
| 2021 | 6 | $137,852,000 |
| 2022 | 8 | $110,680,305 |
| 2023 | 8 | $151,740,000 |
| 2024 | 5 | $60,093,300 |
| 2025 | 7 | $224,652,896 |
| 2026 | 1 | $1,050,000,000 |
| **Total** | **43** | **$1,970,549,385** |

| Native party | Rows |
|---|---|
| Bristol Bay Native Corporation | 11 |
| Arctic Slope Regional Corporation | 9 |
| Sealaska Corporation | 6 |
| Ukpeaġvik Iñupiat Corporation | 5 |
| Calista Corporation | 4 |
| Cook Inlet Region, Inc. | 2 |
| Huna Totem Corporation | 2 |
| Aleut, Bering Straits, Koniag, Sitnasuak | 1 each |

Confidence: 14 High, 29 Medium. 24 rows carry a day-level date; 19 are month-level with the
disclosure required by the ledger convention in `Date_Basis`. Five rows are **divestitures**.

### The four named follow-ups

- **BBNC's GHEMM / John Burns / CSI / Precision table** — converted in full. BBNC's footnote 3 is the
  richest acquisition disclosure in the corpus after ASRC's: a per-target purchase-price table plus a
  lettered narrative for each target, restated across FY2023–FY2025. **11 rows, $359,660,000**,
  covering April 2020 through February 2023.
- **Sealaska's UK acquisitions** — DME Systems ($14,120,000), Blue Sea Food ($1,826,000) and Scantech
  ($1,132,000) converted, plus Normarine, Gregg Marine and the ILPS buy-out found alongside them.
  **6 rows.**
- **CIRI's January 2026 I2X and HABCO** — **already in the live 2026 ledger**, so no rows were written.
  This turned into a ledger-repair finding instead; see §5.
- **ASRC's 2025 Sigma Science and Applied Research Solutions** — converted ($15,938,000 and
  $170,794,000), plus Pitco and three divestitures found in the same note, plus the transaction the
  first pass could not have seen: **ASRC acquired Coinstar, LLC on 9 February 2026 for approximately
  $1,050,000,000 in cash**, disclosed as a subsequent event in the 2025 annual report. That is the
  largest transaction in this dataset by a factor of six and it establishes a sixth ASRC core business
  segment. It is filed by transaction year (2026) and its value is explicitly preliminary — the price
  is stated as "approximately" and the purchase price allocation was still in process at issuance.

### Negative findings, recorded so nobody re-searches them

BBNC states there were **no acquisitions in FY2024 or FY2025** and Sealaska's 2025 report discloses
**no 2025 acquisition or divestiture** (`SK2-ANCSA-016`, `SK2-ANCSA-017`).

---

## 4. Value traps caught in this run

Every one of these was present in retrieved text next to a real transaction and none was written into
a value field.

1. **Noncontrolling interest inside a "purchase price" — the Odyssey pattern, three more times.**
   BBNC's John Burns table books a purchase price of $83,389 thousand including $8,339 thousand of
   minority interest BBNC did not buy; the row carries **$75,050,000**. Sealaska's Normarine note
   shows "fair value of total consideration transferred" of $5,349 thousand including $1,962 thousand
   of NCI; the row carries the **$3,387,000** actually paid. UIC's tables do this correctly on their
   own and were followed.
2. **A previously held equity interest inside "total consideration transferred" — the step-acquisition
   variant.** Calista's Nordic Well Servicing note gives a "fair value of purchase price" of
   $58,355,884 and then adds $10,212,280 for the equity interest Calista **already owned** to reach a
   larger total. The row carries $58,355,884.
3. **A bargain purchase gain.** Sealaska paid $1,826 thousand for Blue Sea Food's assets and booked a
   $6,001 thousand bargain gain because the seller was distressed. The gain is an accounting outcome.
4. **Contingent consideration maxima.** Calista's Nordic contingent arrangement has a **$24,000,000
   maximum** that pays nothing unless cumulative operating cash flows clear zero and return on
   investment clears 8%. Only the recorded estimate of $1,713,691 is inside the price. Same discipline
   applied to ASRC's Finite ($4,000 thousand potential, excluded) and to UIC's employment-contingent
   seller payments at Johansen ($800,000) and HC ($1,500,000), both of which the filings themselves
   exclude from acquisition accounting.
5. **Impairments.** ASRC fully impaired Pirlo in 2024 with a $46,092 thousand loss and then sold the
   West Deptford investment for $3,000 thousand in March 2025. The impairment is a write-down.
6. **Financing mistaken for consideration.** ASRC's Coinstar note sits beside an $850,000 thousand
   revolver and $1,250,000 thousand of term borrowings. Neither is a price.
7. **Revenue and operating results beside an acquisition.** Aleut Energy's $1.2 million of first-year
   revenue; BBNC's statement that GHEMM and John Burns "collectively contributed $65.8 million".
8. **Goodwill larger than the price.** UIC's Delta Strategies goodwill is $52,263,023 against a
   $41,772,300 consideration, because the table nets NCI against assets acquired. Goodwill is never a
   price.
9. **A corporation contradicting itself.** Huna Totem dates the DCSSP purchase to December 2018 in two
   reports and December **2019** in three others, a full year apart, and dates the 25% buy-out to both
   December 2020 and January 2020. **No row was written** (`SK2-ANCSA-021`), following the Aleut/ARS
   precedent.
10. **A capital contribution mistaken for a purchase price.** Huna Totem contributed $2,550,000 to
    Na-Dena`, a 50/50 joint venture with Doyon, which then bought 80% of Alaska Independent Coach
    Tours. The contribution is not the price of the stake (`SK2-ANCSA-009`).

### Two judgement calls, both disclosed in the row

- **BBNC / GHEMM.** The FY2022 subsequent-events note says $32,743 thousand; the FY2023, FY2024 and
  FY2025 reports all say $23,853 thousand and call the allocation final. The $8,890 thousand gap is
  consistent with a measurement-period revision to the $10,248 thousand of contingent consideration.
  A row **was** written at the final figure, because this is preliminary-versus-final measurement of
  one event and not the mutually exclusive conflict that killed Aleut/ARS (two different acquisition
  dates). Confidence Medium, both figures in `Notes`.
- **Sealaska / Gregg Marine.** $4,000 thousand is the only figure the filing calls "the purchase
  price"; a further $3,000 thousand is due on the second anniversary. The row carries $4,000,000 and
  states that total cash to the seller is $7,000,000 if the deferred payment is included. The sum was
  not written into the value field because the filing never states it as a price.

---

## 5. Four live-ledger rows this run can repair — Elijah's call, not the agent's

The most valuable output of this pass may not be the new rows. Four transactions already in the live
ledgers are **dateless, valueless or misdated**, and primary filings now resolve them. **Nothing was
modified.** Each is logged with the exact edit in `review/deals_skipped_ancsa_portal_v2.csv`.

| Live row | Problem today | What the filing says |
|---|---|---|
| `MA2020-001` (historical) UIC / Johansen | blank `Event_Date`, `Undisclosed` value, **empty `Source_1`**, flagged UNSOURCED in AGENTS.md | 31 March 2020, **$4,080,000**, 51% |
| `MA2020-003` (historical) BSNC / Northwest Contracting | value `Undisclosed` | **$18,324,000**; date already correct |
| `ND-2026-004` (2026 YTD) CIRI / I2X | dated 2026-02-02, no value | **21 January 2026, $42,100,000** |
| `ND-2026-005` (2026 YTD) CIRI / HABCO | dated 2026-02-04, no value | **29 January 2026, $60,612,000** |

**And one that changes a scope window.** `ND-2026-077` in `deals_2026_ytd_additions.csv` records
UIC/Northbank as a 2026 event dated 2026-01-16 from a newsroom release. **UIC's audited financial
statements date the acquisition to 31 December 2025** and consolidate Northbank from that date. Under
the file-by-transaction-year rule the transaction is 2025, not 2026. This run wrote it as
`ANCSA2-2025-006`; the two rows describe the same transaction and **must be reconciled before
publication**, because leaving both in place double-counts and keeping the 2026 date overstates
2026 year-to-date. See `SK2-ANCSA-005`.

The pattern is general and worth acting on: **newsroom announcement dates ran 2–16 days later than the
audited transaction dates in every case here.** Where an ANCSA filer's audited statements cover a
transaction, they should outrank the press release for both date and value.

---

## 6. Skipped leads — 24

| Reason | Count |
|---|---|
| `duplicate_in_live_ledger` | 5 |
| `no_amount` | 6 |
| `not_in_source` | 4 |
| `not_a_deal_source` | 4 |
| `no_date` | 3 |
| `no_counterparty` | 2 |

Four are **negative findings** recorded so a future run does not re-search a dry seam (BBNC FY2024–25,
Sealaska 2025, the four silent village corporations, the mis-flagged OCR nine). Three close prior-run
leads: `SK-ANCSA-001` converted to two rows, `SK-ANCSA-002` closed as a misread, `SK-ANCSA-013`
half-converted.

---

## 7. What remains unworked

1. **358 village-corporation annual reports across 41 corporations were not retrieved** — 80 of 438
   indexed village annual reports are now in hand. Ranked by document count and known
   government-contracting activity, the next targets are Gana-A'Yoo (24), Natives of Kodiak (20),
   Ouzinkie (17), Shaan Seet (17), Klawock Heenya (17), Bethel Native (16), Tyonek (15), Shee Atika
   (14), Afognak (12), The Eyak (12), The Kuskokwim (12), Kikiktagruk Inupiat (11), Far West (11),
   Kootznoowoo (10), Choggiung (10) and Tanadgusix (10). At the 4 s throttle this is roughly a
   five-hour download plus OCR. **Afognak/Alutiiq and Shee Atika are the largest omissions by
   federal-contracting revenue.** UIC's yield here — five priced acquisitions from one corporation —
   is the argument for doing it.
2. **The four live-ledger repairs and the Northbank year conflict in §5.** These need a human decision
   and they touch published totals.
3. **Doyon's 49% buy-out of Doyon Energy Services (30 Sep 2024)** has an exact date and no stated
   price. The equity roll-forward implies $5,500 thousand but that is arithmetic on a statement of
   changes in equity, not a disclosed price, so no value was written. The FY2024 Doyon report may
   state it (`SK2-ANCSA-008`).
4. **Petro Star / Tesoro Logistics Terminal 1 (June 2017).** OCR resolved the counterparty and the
   month; the price is not in any ASRC filing. Tesoro Logistics was an SEC registrant and may disclose
   it from the seller side (`SK2-ANCSA-006`).
5. **Six more unpriced or undated leads** — Sitnasuak/Kiska CS, Sitnasuak/Mocean, Huna
   Totem/AICT, Huna Totem/Chukka Boat Leasing, BBNC's fuel tank farm assets, ASRC's three convenience
   stores.
6. **Ownership-change records.** All 43 rows are acquisitions, interest changes or divestitures and
   every one should feed the time-aware attribution ledger. Three complete arcs now exist in the
   combined ANCSA files: ASRC/Alpine Transportation (16.7% in 2003 → exit October 2023),
   Sealaska/ILPS (62.5% → 100% December 2024) and Sealaska/Gregg Marine (51% → 100% May 2023).
   **Na-Dena`, LLC should be added to the entity spine** as a 50/50 Huna Totem / Doyon joint venture —
   a village-corporation/regional-corporation vehicle that the roster does not currently model.
7. **Chugach per-target splits.** The 2025 Chugach report splits two combined prior-run rows into
   four (Pollard Wireline $9,200,000 / Alaska E-Line $13,800,000; HVAC $5,000,000 / AIS $4,000,000).
   No rows were written, to avoid double counting. The ledger needs a granularity convention for
   same-day multi-target acquisitions before anyone acts (`SK2-ANCSA-015`).
8. **The proxy corpus stays out of scope for deals**, per the first pass and reconfirmed here.
9. **Re-harvest after each annual-meeting season**, respecting the Division's ten-business-day filing
   queue, and diff the corporation dropdown to track the post-HB126 filer population.
