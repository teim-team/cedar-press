# ANCSA Portal Build Log — Alaska DBS STAR, harvested 2026-08-05

Dataset 1 (Indian Country Deals). Source: the Alaska Department of Commerce, Community and
Economic Development, Division of Banking and Securities STAR portal, which holds ANCSA
corporation filings made under AS 45.55.139. Access was granted to Elijah by the Division
("the ANCSA portal is live and you are now able to view and retrieve documents on your own").

**Outputs**
- `data/raw/external/ancsa_portal/` — 171 PDFs (1.63 GB) + `_SOURCE_MANIFEST.csv`
- `data/clean/ancsa_filings_index.csv` — **19,269 documents**, one row per document, downloaded or not
- `data/clean/deals_ancsa_portal_additions.csv` — **34 deal rows**
- `review/deals_skipped_ancsa_portal.csv` — **21 skipped leads**
- Log: `logs/29_ancsa_portal.log` (access method, search contract, year census, HB126 text)

Nothing was written into `deals_2026_ytd.csv`, `deals_historical_2020_2025.csv`, `data/spine/`,
`data/clean/cedar_*` or `review/cedar_review*.html`. Schema of the additions file was validated
column-for-column against `deals_historical_2020_2025.csv` (32 columns, identical order).
Deal_IDs use the reserved prefix `ANCSA-` and were checked against both live ledgers and all
three existing additions files: **zero collisions**, zero internal duplicates.

---

## 1. The access method that worked (this is the reusable part)

The entry points named in the brief are a dead end for retrieval, and the reason is worth
recording precisely.

1. `https://portal.akdbsstar.us/StarWebPortal/` → 302 → `/page/default/portal.aspx`, HTTP 200,
   issues an `ASP.NET_SessionId`.
2. `/UIPViews/FillXPForm.aspx` fetched directly returns HTTP 500, as previously established.
3. The root page exposes exactly two `__doPostBack` actions: **Search ANCSA Filings** and
   **Submit ANCSA Documents**.
4. POSTing the *Search ANCSA Filings* action does land on `FillXPForm.aspx` with HTTP 200 — but
   that page is titled **"Application - Public Record Request (Web)"**. It is a REQUEST INTAKE
   WIZARD: last name, first name, firm, mailing address, phone, email, a free-text
   "File(s) Requested" box, and a Next button. It is not a document index. **Nothing was
   submitted through it.** No personal data was transmitted and no records request was filed;
   filing a request in Elijah's name is a human decision, not an agent decision.
5. The actual self-service search is a different page that is **not linked from the root action
   list** and whose URL path is **case-sensitive**:

   ```
   https://portal.akdbsstar.us/StarWebPortal/page/ANCSA/portal.aspx    <- the search page
   https://portal.akdbsstar.us/StarWebPortal/page/ancsa/portal.aspx    <- 200, but renders EMPTY
   ```

   Lowercase returns the site chrome with no search control at all, which reads exactly like a
   page that does not exist. This one capital letter is the whole difference between "the portal
   has no public search" and 19,269 retrievable documents.

### Search contract

POST to the same URL. Field prefix `P = ctl00$ContentPlaceholder1$PortalPageControl1$ctl26$`:

| Field | Values |
|---|---|
| `P+ddCorporationName` | one of 60 exact strings, or `-----Select Corporation Name-----` (= all) |
| `P+ddDocumentCategory` | `ANCSA Annual Report`, `ANCSA Independent Candidate Proxy Materials`, `ANCSA Proxy Materials`, `ANCSA Proxy Statement`, or the `-----Select...-----` placeholder (= all) |
| `P+txtYear` | **required**; RangeValidator 1900–2100. A blank year returns zero rows with `* Invalid year.` **There is no all-years search.** |
| `P+btnSubmit` | `Submit` |

Hidden fields on this portal are `__EVENTTARGET`, `__EVENTARGUMENT`, `__VIEWSTATE`,
`__VIEWSTATE1`, `__VIEWSTATEENCRYPTED`. There is **no `__VIEWSTATEGENERATOR` and no
`__EVENTVALIDATION`** — echo whatever hidden inputs the previous response carried.

Results grid `ctl00_ContentPlaceholder1_PortalPageControl1_ctl26_gvFileList`: 25 rows per page,
columns *Document Description | Year | Category*. **There is no corporation column and no filing-date
column.** Pagination is `__EVENTTARGET=<grid id>`, `__EVENTARGUMENT=Page$N`. The result count is in
`..._lblGridPosition` ("Displaying record 1 to 25 of 1534").

Documents download from `https://portal.akdbsstar.us/StarWebPortal/ViewFile.aspx?Id=<GUID>`,
`application/pdf`, no `Content-Disposition`, same session cookie. **The href emitted in the grid
is malformed**: the GUID is immediately followed by the literal text `rel="noreferrer"` with no
separator. Parse the GUID with a `[0-9a-fA-F-]{36}` regex; do not take the href verbatim.

### Throughput trap that cost about forty minutes

Re-fetching `page/ANCSA/portal.aspx` with a GET before every search made a single search take
25–45 seconds. Reusing the hidden fields from the **previous POST response** and chaining POSTs on
one session brings a search to 1.2–2.1 seconds. Throttle used: 1.0 s between requests, one
connection, sequential. 171 document downloads were throttled at 4 s. No error responses were
returned by the portal at any point, and no request was retried more than once.

---

## 2. What is actually in the portal

### Year census (one page-1 search per year, 1971–2026)

Every year from 1971 to 2011 and the years 2013, 2014 and 2015 return **zero documents**. These
are valid queries — the year validator accepts 1900–2100 — so the zeros are real absences, not
rejected searches.

| Year | Documents |
|---|---|
| 2012 | 2 |
| 2016 | 89 |
| 2017 | 1,534 |
| 2018 | 1,467 |
| 2019 | 1,704 |
| 2020 | 3,075 |
| 2021 | 1,693 |
| 2022 | 1,419 |
| 2023 | 1,910 |
| 2024 | 2,374 |
| 2025 | 2,304 |
| 2026 | 1,698 |
| **Total** | **19,269** |

**The portal's effective coverage floor is 2016.** The two 2012 documents are strays. This is a
live filing system, not a historical archive: it does not reach the 1970s–2000s ANCSA filings at
all, and the pre-2016 deal history this project wants has to come from somewhere else.

### By document type (19,269 indexed documents)

| Category | Documents |
|---|---|
| ANCSA Proxy Materials | 10,174 |
| ANCSA Independent Candidate Proxy Materials | 7,990 |
| ANCSA Annual Report | 609 |
| ANCSA Proxy Statement | 496 |

Annual reports are about 3% of the portal by count. The other ~97% is shareholder-election
material — proxy cards, candidate statements, meeting notices, solicitation letters. That is a
governance corpus, not a transaction corpus, and it should not be mined for deal rows. It is,
however, a strong seed for a future ANC board/elections dataset, and the index built here already
enumerates all of it by corporation and year.

A caution for anyone filtering on category: **the Division's `ANCSA Annual Report` category is not
purely annual reports.** It also carries settlement-trust financial statements, consolidated
financial statements filed separately from the report, and — in NANA's 2018 filings — annual-meeting
posters, postcards, envelopes and a prize card. Filter on category to find candidates, then read.

### By year

| Year | Documents indexed |
|---|---|
| 2012 | 2 |
| 2016 | 89 |
| 2017 | 1,534 |
| 2018 | 1,467 |
| 2019 | 1,704 |
| 2020 | 3,075 |
| 2021 | 1,693 |
| 2022 | 1,419 |
| 2023 | 1,910 |
| 2024 | 2,374 |
| 2025 | 2,304 |
| 2026 | 1,698 |

### Index completeness

The index was built by running **every one of the 720 corporation x year searches** (60 corporations
x 12 years with documents). It is complete.

---

## 3. Coverage against the 196-entry ANC roster

The portal's corporation dropdown holds **60 corporations**. Every one of them matched a row in
`data/clean/anc_ceiling_roster.csv` (196 entries) after Unicode normalisation — the only non-trivial
match was *Ukpeagvik Inupiat Corporation* in the portal against *Ukpeaġvik Iñupiat Corporation* in
the roster. So corporation attribution in the index is **19,269 of 19,269 document rows carrying an anc_id**.

| Roster class | On roster | Present in the portal |
|---|---|---|
| ANC_REGIONAL | 13 | 12 |
| ANC_VILLAGE | 182 | 48 |
| ANC_URBAN | 1 | 0 |
| **Total** | **196** | **60** |

**60 of 196 roster entries (31%) appear in this source.** That number should not be read as a
failure of the harvest, and the Division said so before the harvest started:

- Filing under AS 45.55.139 is **conditional**, not universal. Only corporations meeting the
  statutory test file at all. The remaining roster entries are largely small village corporations
  that have never been filers.
- **Some corporations will not have annual reports at all**, depending on when their annual meeting
  falls (Division's own caveat). An absent report is not a missing document.
- **HB126 shrank the filer population further as of 2026-06-25** (section 5 below). The 60-name
  dropdown captured on 2026-08-05 is already a post-HB126 list.

Twelve of the thirteen ANCSA **regional** corporations are present. The absentee is **The 13th
Regional Corporation**, organised for Alaska Natives resident outside Alaska; it is not in the
dropdown. Absence from the dropdown is evidence that it is not a current filer, not evidence that
no filings exist. Do not claim "all thirteen regionals" from this source.

### Documents per corporation — top 15

| Corporation | Documents |
|---|---|
| Sealaska Corporation | 1,965 |
| Cook Inlet Region, Inc. | 1,557 |
| Doyon Limited | 1,397 |
| Calista Corporation | 1,283 |
| Arctic Slope Regional Corporation | 1,119 |
| Shee Atika, Incorporated | 1,115 |
| Goldbelt Incorporated | 1,044 |
| Kootznoowoo Incorporated | 988 |
| Afognak Native Corporation | 777 |
| Sitnasuak Native Corporation | 775 |
| NANA Regional Corporation, Inc. | 756 |
| Bering Straits Native Corporation | 597 |
| Aleut Corporation | 547 |
| The Kuskokwim Corporation | 509 |
| Chugach Alaska Corporation | 438 |

Every one of the 60 portal corporations returned at least one document.

---

## 4. Deal rows extracted

**34 rows**, all from ANCSA annual reports retrieved in this run, 21 of them with an exact
day-level transaction date stated in the filing and 13 with a month-level date only. 33 rows carry
a value; the sum of `Announced_Value_USD` as written is **$1.06 billion**.

| Year | Rows | | Native party | Rows |
|---|---|---|---|---|
| 2012 | 2 | Arctic Slope Regional Corporation | 14 |
| 2014 | 1 | Chugach Alaska Corporation | 6 |
| 2015 | 5 | Cook Inlet Region, Inc. | 3 |
| 2016 | 6 | Doyon, Limited | 2 |
| 2017 | 1 | Koniag, Inc. | 2 |
| 2018 | 6 | Ahtna, Inc. | 2 |
| 2019 | 5 | Sealaska Corporation | 2 |
| 2020 | 1 | Bristol Bay Native Corporation | 1 |
| 2023 | 3 | Bering Straits Native Corporation | 1 |
| 2024 | 3 | Calista Corporation | 1 |
| 2025 | 1 | | |

Confidence: 21 High, 13 Medium.

### Where the value is

Arctic Slope Regional Corporation alone accounts for 14 of the 34 rows. ASRC's annual reports carry
a full acquisitions note with a per-target purchase-price table AND a narrative giving the month and
the price for each target. Nobody else in the corpus documents transactions that systematically.
The single largest row is **ASRC Federal's acquisition of Vistronix on 16 August 2016 for
$182,500,000** (ANCSA-2016-004).

### What this seam is good for

The prior 2000–2019 build log named **2010–2017 the true soft spot** of the ledger, at roughly one
row per year, and named ANC annual reports as the channel that should cover it and had
underperformed. This run puts **26 rows into 2012–2019**, which is more than the entire 2010–2017
stretch produced in the previous sweep. The seam the earlier log identified was real, and the
obstacle was never the source — it was not knowing the URL had a capital A.

### Deduplication and restatement

Annual reports restate the same transaction for three to five years running. Deduplication was done
on the **transaction**, never on the mention, and every restatement is flagged in `Notes`. Worked
examples in the file: Chugach's Rex Electric acquisition appears in the 2016, 2017 and 2018 reports
(one row); Sealaska's Odyssey purchase appears as a 2016 subsequent event, a 2017 note and a 2018
restatement (one row); Ahtna's AAA Valley Gravel appears in 2016 and again in the 2018 cash-flow
disclosures (one row); Chugach's VPSI purchase appears in the 2024 and 2025 reports (one row).

Rows are filed by **transaction year, not report year**. ANCSA-2014-001 (ASRC/Little Red Services,
May 2014) was recovered from the 2016 annual report; ANCSA-2012-001 and -002 (CIRI/Cruzco and
CIRI/Weldin, March 2012) were recovered from the 2016 annual report four years after the fact.

---

## 5. HB126 — what changed, and what it does to any coverage claim

Verified against the enrolled bill text and the legislature's action history, not against the
Division's summary alone.

- **HB 126, 34th Alaska Legislature**, version SCS CSHB 126(L&C), short title
  *REINSTATEMENT NATIVE CORPS/ANCSA REPORTS*.
- **CHAPTER 37 SLA 26. Signed into law 6/24/2026. Effective date of law 6/25/26.**
  Section 3: "This Act takes effect immediately under AS 01.10.070(c)."
- The DBS notice on the portal root states: "On June 25, 2026, HB126 became law and changes which
  Alaska Native Claims Settlement Act (ANCSA) Corporations meet the Division's filing requirements
  under AS 45.55.139."

**Section 2 amends AS 45.55.139.** In the enrolled text, bracketed capitals are deletions:

> A copy of all annual reports, proxies, consents or authorizations, proxy statements, and other
> materials relating to proxy solicitations distributed, published, or made available by any person
> to at least 30 Alaska resident shareholders of a corporation organized under Alaska law under 43
> U.S.C. 1601 et seq. (Alaska Native Claims Settlement Act) **with** [THAT HAS TOTAL ASSETS
> EXCEEDING $1,000,000 AND] a class of equity security held of record by 500 or more **original
> shareholders when the corporation was originally organized** [PERSONS] shall be filed with the
> administrator concurrently with its distribution to shareholders.

Two changes, both narrowing who files:

1. **The $1,000,000 total-assets test is deleted outright.**
2. **The 500-holder test is re-anchored in time** — from 500 or more *current* holders of record to
   500 or more *original shareholders at original organisation* under ANCSA.

The practical effect runs one way: a village corporation whose shareholder roll grew past 500 through
inheritance since 1971, but which enrolled fewer than 500 originally, **is no longer a filer**.
Regional corporations and originally-large village corporations remain filers. So:

- Any coverage statement built on this source for periods **after 2026-06-25** is coverage of the
  **post-HB126 filer population**, which is smaller than the pre-HB126 population and much smaller
  than the 196-entry roster. Do not express portal coverage as a fraction of the roster without
  saying this.
- Expect the 60-name dropdown to **shrink** in future harvests, and expect some corporations with
  2016–2025 filings to stop appearing. That is a statutory change, not data loss. Re-capture the
  dropdown on every future run and diff it; this run's list is preserved in
  `code/ancsa_portal/corps.json`.

**Section 1 also matters to the entity spine** even though it is not a filing rule. It amends
AS 10.06.960(k) so an involuntarily dissolved Native village corporation may be reinstated **at any
time**, deleting both the two-year window in AS 10.06.633(e) and the "on or before December 31, 2020"
deadline. Reinstated corporations will appear as new or returning entities in the ANC roster.

---

## 6. The Division's own caveats, recorded

Stated by the Division to Elijah and reproduced here so no future run scores them as gaps:

1. **Filings sit in a queue. Allow ten business days** before concluding a document is missing. The
   Division recommends checking late Friday afternoon. Any document filed in the ten business days
   before 2026-08-05 may therefore be absent from this harvest.
2. **Some corporations will not have annual reports at all**, depending on when their annual meeting
   falls. An absent report is not a missing document.
3. **HB126 changed which corporations meet the filing requirements** — section 5 above.

---

## 7. Value traps caught

Every one of these was present in retrieved text next to a real transaction, and none was written
into a value field.

1. **Purchase-price allocation totals that look like prices.** Chugach's Rex Electric note ends
   "Total assets net of liabilities assumed $32,549,086" — the same number as total consideration by
   construction, not a second figure. Total assets of $54,754,313 in the same table is a balance-sheet
   item.
2. **Fair value of total consideration transferred, when a minority stake was bought.** Sealaska paid
   $17,850,000 for 51% of Odyssey; the note's "fair value of total consideration transferred" is
   $35,000,000 because it adds the $17,150,000 fair value of the 49% Sealaska did **not** buy. Same
   pattern at Geo Services ($8,225,000 cash vs $16,128,000 stated total).
3. **Contingent consideration inflating a table figure above the stated price.** ASRC's Brad Cole
   narrative says $15,925,000; the acquisition table says a net purchase price of $32,175,000 because
   it books an estimated $16,250,000 of a potential $24,000,000 earn-out that the filing itself says
   depends on BCC winning a future contract. Same at Hudspeth ($13,000,000 narrative vs $18,500,000
   table).
4. **Revenue contribution quoted next to an acquisition.** ASRC reports that DNC and Vistronix
   "provided an additional $115.8 million of combined revenues" and that API "added $7.3 million of
   revenues". Those are segment revenue effects, not prices.
5. **Portfolio balances beside a minority investment.** ASRC Capital's minority interest in Pirlo
   Energy Holdings sits two sentences from "$76.3 million" of alternative investments and "$68.8
   million" of unfunded commitments. No price for Pirlo exists in the filing; the lead was skipped.
6. **Escrow and earn-out deposits.** Aleut's $3,700,000 escrow for the Patrick Mechanical earn-out is
   not the purchase price. ASRC's escrow and holdback amounts are components of prices already
   recorded.
7. **Impairment charges.** ASRC's $10.2 million Trilogy impairment "to align with the value of the
   purchase price at acquisition" is a write-down, not consideration, and ASRC was a minority holder.
8. **Balance-sheet effects attributed to a deal.** BSNC's 2016 report attributes a $34 million rise in
   total assets and long-term debt reaching $41 million to the AIH acquisition. The price is
   $65,000,000 and is stated separately.
9. **A corporation contradicting itself.** The Aleut Corporation's own annual reports date the ARS
   International acquisition to *both* June 1, 2013 and June 1, 2014. No row was written. A
   restatement in a later annual report is not independent verification of an earlier one.

---

## 8. Skipped leads — 21

| Reason | Count |
|---|---|
| `no_date` | 10 |
| `no_amount` | 6 |
| `no_counterparty` | 2 |
| `below_threshold` | 1 |
| `not_a_deal_source` | 1 |
| `not_in_source` | 1 |

The `no_date` entries are almost all year-only or fiscal-year-only statements. The brief's rule was
applied literally: a fiscal year is not a date and nothing was inferred from one. The two most
valuable follow-ups are **Sealaska/Orca Bay (April 1, 2019, exact date, price not in the retrieved
document)** and **CIRI's 2015 buy-out of the remaining 25% of Weldin for $6,000,000 (price exact,
date year-only)** — each needs one more annual report from the index to convert.

---

## 9. Retrieval scope and what is still on the table

171 of the 19,269 indexed documents were downloaded (1.63 GB): every document the per-corporation index
attributed to one of the twelve **regional** corporations in the `ANCSA Annual Report` category,
2016 through 2026. Village-corporation annual reports and the ~19,098 proxy documents were indexed but
not retrieved — indexing is complete, retrieval is deliberately partial, and the index records
`downloaded = no` for every one of them so the boundary is explicit rather than implied.

**28 of the 171 downloaded PDFs are image-only** and yield no extractable text (notably the 2017 CIRI
and 2017 Calista annual reports, several Doyon settlement-trust reports, and the 2021–2022 Bering
Straits reports). They are archived and hashed, and they are the obvious OCR queue. The 2017 ASRC
annual report is in this group, which is exactly why the ASRC "Finite" and "USC" 2017 acquisitions
could not be dated.

Ranked follow-ups:

1. **OCR the 28 image-only PDFs.** Two named ASRC 2017 acquisitions and two 2022 Calista
   acquisitions are sitting behind them.
2. **Download and mine village-corporation annual reports.** Choggiung, Olgoonik, Kuukpik, Tikigaq,
   Ukpeaġvik, Huna Totem, Goldbelt and Sitnasuak all file, all operate government-contracting
   subsidiaries, and none was retrieved in this run.
3. **Work 2020–2026 systematically.** The mining pass found dated, priced transactions in the 2020+
   reports that were not carried into rows here for time — BBNC's GHEMM/John Burns/CSI/Precision
   table, Sealaska's UK acquisitions (DME Systems, Blue Sea Food, Scantech), CIRI's January 2026 I2X
   and HABCO purchases, and ASRC's 2025 Sigma Science and Applied Research Solutions deals. Each is a
   verifiable row.
4. **Emit ownership-change records.** All 34 rows are acquisitions or interest changes and every one
   should feed the time-aware attribution ledger. The Chugach/All American Oilfield pair
   (ANCSA-2015-001 at 90%, ANCSA-2020-001 taking it to 100%) is a complete five-year arc on one
   subsidiary.
5. **Re-harvest after each annual-meeting season**, respecting the ten-business-day queue, and diff
   the corporation dropdown to track the post-HB126 filer population.
6. **Do not mine the proxy corpus for deals.** Use it to seed an ANC governance dataset instead.

