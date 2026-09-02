# Deals Build Log — 2000–2019 Backfill, 2026-08-05

Dataset 1 (Indian Country Deals). Window: **2000-01-01 through 2019-12-31**, per the
project-wide temporal floor of 2000 set 2026-08-05.

**Outputs**
- `data/clean/deals_2000_2019_additions.csv` — **40 rows**, 2000–2019
- `review/deals_skipped_leads_2000_2019.csv` — **28 skipped / excluded leads**
- Log: `logs/25_deals_2000_2019.log`

Nothing was written into `deals_2026_ytd.csv` or `deals_historical_2020_2025.csv`.
Schema was validated column-for-column against `deals_historical_2020_2025.csv`
(32 columns, identical order). Deal_IDs were checked against both live ledgers and both
existing additions files: **zero collisions**, zero internal duplicates. No `ND-<year>-###`
identifiers existed anywhere for 2000–2019, so that ID space was free and is now used.

`data/spine/`, `data/clean/cedar_*` and `review/cedar_review.html` were not touched.

---

## The rule applied this run

Every date and every dollar figure below was re-read in retrieved document text before it
was written. The older half of the window made this harder, not easier, in exactly the way
the brief predicted: search-engine summaries were confidently wrong about a completion year
(Hard Rock), a closing day (Sands Bethlehem), and a purchase price that was never disclosed
at all (Lone Star Park). All three are documented under "Traps caught".

---

## Per-channel yield

| Channel | Rows | Verdict |
|---|---|---|
| **3. SEC EDGAR (tribal registrants)** | **24** | Far and away the highest-yield channel, and the only one that reaches 2000–2005 at all |
| **1. Entity newsrooms** | **11** | Reliable but shallow: most newsrooms bottom out around 2015–2018 |
| **4. Gaming-era milestones** | **4** | Worked, but each row cost several searches and one careful date adjudication |
| **2. ANC annual reports / newsletters** | **2** | Underperformed badly (see below) |
| **5. Federal Register** | **0** | Zero direct conversion. Valuable as a lead index only |

### Channel 5 — Federal Register. Cheapest, and it produced no rows.
`data/clean/federal_actions.csv` holds 97,857 documents in the 2000–2019 window. The
deal-candidate action types are there in volume — 509 `ancsa_conveyance`, 356
`tribal_state_compact`, 199 `land_into_trust`, 88 `gaming_land_decision`, 81
`reservation_proclamation` — and every one of them is dated authoritatively.

**But in this window they are almost entirely NEPA process notices** (notice of intent,
draft EIS, final EIS, record of decision, cancellation), proclamations, and statutory
conveyances. They date *projects and federal actions*, not *transactions*. None carries a
counterparty or consideration. The 88 gaming-land decisions name roughly thirty casino
projects — Jamul, Graton Rancheria, Menominee Kenosha, North Fork, Enterprise, Cowlitz,
Spokane West Plains, Ho-Chunk Beloit, Wilton Rancheria, Tule River, Little River, Redding
Rancheria — each of which is a *lead* requiring separate transaction verification.

Honest assessment: the brief called channel 5 "highest-value and cheapest". It is the
cheapest, and it is the best lead index in the project, but its **direct conversion rate to
deal rows in 2000–2019 is zero**. It should be worked as a targeting list for channels 1/3/4,
not as a row source.

### Channel 3 — SEC EDGAR. The find of this run.
**Access note worth memorialising: `WebFetch` returns HTTP 403 on sec.gov. `curl` with a
declared User-Agent (name + contact email, per SEC's access policy) returns 200.** Every SEC
document below was fetched that way and stripped to text locally, so the evidence was
re-read rather than summarized by an intermediary.

Tribal instrumentalities carry public debt, which makes them SEC registrants, which makes
their financings and acquisitions dated, precise and authoritative. Seven were located:

| Registrant | CIK | Tribe | Rows |
|---|---|---|---|
| Mohegan Tribal Gaming Authority | 1005276 | Mohegan Tribe of Indians of CT | 11 |
| Seneca Gaming Corporation | 1296785 | Seneca Nation of Indians | 5 |
| River Rock Entertainment Authority | 1288924 | Dry Creek Rancheria Band of Pomo | 2 |
| Choctaw Resort Development Enterprise | 1141344 | Mississippi Band of Choctaw | 1 |
| Chukchansi Economic Development Authority | 1210298 | Picayune Rancheria of Chukchansi | 1 |
| Inn of the Mountain Gods Resorts & Casino | 1280352 | Mescalero Apache Tribe | 1 |
| Agua Caliente Band of Cahuilla Indians | 1263067 | Agua Caliente | 0 (no filings in window) |

Plus 1 row where a Native entity was counterparty to a public company: **Las Vegas Sands'
Form 8-K exhibit** dated the Sands Bethlehem closing, and **Penn National** as Mohegan's
Pocono Downs seller.

Method that worked, and is reusable:
1. `data.sec.gov/submissions/CIK##########.json` → filter to 8-K with **Items 1.01 / 2.01 /
   2.03** (material agreement / completion of acquisition / new financial obligation). Item
   tagging exists only from August 2004, so this covers 2004–2019.
2. For 2000–2004, use **S-4 exchange-offer prospectuses**. A tribal authority that privately
   places notes must register an exchange offer, and the prospectus states the **original
   private-placement date and amount** in plain text — often three times, in the cover, the
   business description and the audited-financials note. This is how every 2001–2004 row was
   dated.
3. `efts.sec.gov/LATEST/search-index` (full text, 2001+) to discover registrants by phrase
   ("federally recognized Indian tribe", "Indian Gaming Regulatory Act"). EDGAR's
   `browse-edgar?company=` is prefix-match only and misses "… Tribal Gaming Authority".

**Reading the filings mattered.** Nine item-1.01 filings that looked like deals in the index
turned out to be executive employment agreements, and were discarded. Four more were
covenant or repricing amendments with no new money, and were skipped and logged.

### Channel 1 — Entity newsrooms.
`chickasaw.com/about/news` was again the richest newsroom in Indian Country: a fully dated
index reaching 2018, with each release on its own permalink. Six rows (three acquisitions,
three contract awards). Its floor for automated fetch is 2018 — `/about/news/2017` returns
404.

`waseyabek.com` was pushed back past the 2019 floor the previous sweep reported, yielding
two 2018 rows. Its own text then flagged a gap: the February 2018 release calls Baker
Engineering WDC's **fourth** acquisition, so three earlier transactions exist and are
undated in anything retrieved.

`beringstraits.com` and `sealaska.com` each gave one row.

### Channel 2 — ANC annual reports. The disappointment.
The brief expected the thirteen regional corporations to be "the richest 2000s-era source".
They were not, at least not through automated fetch. Two rows total (BSNC 2015, Sealaska
2016), plus one 2014 joint venture reached through trade press. No ANC annual-report PDF was
successfully located and read in this run. `beringstraits.com/category/company-news/`
paginates back to December 2010 but its first page renders only 2026 items to automated
fetch, and `olgoonik.com` (which mirrors the ASRC release) returns 403.

This is the single largest unworked seam left in the window and it needs a paging pass or a
manual download, not more search queries.

---

## Rows by year, and where the ceiling is

| Year | Rows | | Year | Rows |
|---|---|---|---|---|
| 2000 | **1** | | 2010 | 1 |
| 2001 | 2 | | 2011 | 2 |
| 2002 | 2 | | 2012 | **1** |
| 2003 | 3 | | 2013 | 1 |
| 2004 | 2 | | 2014 | **1** |
| 2005 | 2 | | 2015 | **1** |
| 2006 | **1** | | 2016 | 2 |
| 2007 | **1** | | 2017 | **1** |
| 2008 | 2 | | 2018 | 3 |
| 2009 | 2 | | 2019 | **9** |

**Thinnest years: 2000, 2006, 2007, 2012, 2014, 2015 and 2017 — one row each.**

**Answering the brief's question directly: 2000–2005 is NOT unreachable.** It produced 11
rows, all primary-sourced from SEC filings, all High confidence but one. That is a better
result than 2010–2017, which produced 9 rows across eight years. The reachability curve in
this window is **not** monotonic in time — it tracks *whether a tribal entity had public
debt*, not how old the deal is.

The real ceiling is shaped like this:
- **2000 is genuinely hard.** The single row is a bank-facility increase option recovered
  from a 2001 filing's history section. EDGAR full-text search does not reach before 2001,
  8-K item tagging does not exist before August 2004, and no tribal newsroom retrieved in
  this run reaches 2000. The best remaining year-2000 lead is Ho-Chunk, Inc.'s purchase of
  Dynamic Homes, which a BIA page dates only to "2000".
- **2006–2007 is thin for a structural reason**, not a sourcing one: the SEC registrants were
  between financings (Mohegan issued in 2004 and again in 2009; Seneca in 2004, 2005 and
  2010), and the era's biggest tribal transaction — Hard Rock — is a single deal that
  correctly occupies one row in one year.
- **2010–2017 is the true soft spot.** It is neither old enough for the SEC channel to be
  dense nor recent enough for entity newsrooms to reach. This is exactly the decade the ANC
  channel should cover, and exactly where the ANC channel underperformed. **If one further
  session is spent on this window, spend it paging ANC newsroom archives for 2010–2017.**
- **2019 at 9 rows is roughly the yield a fully worked year looks like** with these channels.
  Judged against that, 2000–2018 is running at about 1.6 rows/year, so the capture rate over
  the older nineteen years is on the order of **15–20% of what a fully worked year produces**.

---

## Traps caught and excluded

1. **Hard Rock / Seminole Tribe — completion year.** Nearly every secondary reference dates
   this transaction to **7 December 2006**. That is the Rank Group *announcement*. The Rank
   disposal statement said completion was expected 5 March 2007, and a completion-day report
   confirms it completed Monday **5 March 2007**. Filed as **ND-2007-001**, in 2007. The 2006
   date is logged as reviewed-and-excluded so no future sweep creates a second row.
2. **Sands Bethlehem — closing day.** The buyer's own press release is datelined **June 3,
   2019**. Las Vegas Sands' Form 8-K exhibit is datelined **May 31, 2019** and states the
   company "has completed the sale". Closing beats announcement, so **ND-2019-002 is dated
   2019-05-31**. Both dates land in Q2, so this changed the day rather than the quarter — but
   it is precisely the class of error the brief warned about, and the seller's SEC filing is
   the authority.
3. **Lone Star Park — a price that does not exist.** A search summary offered "$47.8
   million". The retrieved BloodHorse article states explicitly that terms were **not
   disclosed**. No figure was written. ND-2011-001 carries an undisclosed value.
4. **Waséyabek $28.5 million.** That is the value of WDC's real-estate *portfolio after* the
   two 2018 purchases, not the price paid. Excluded from every value field.
5. **Wind Creek $340 million.** Planned future expansion at Bethlehem — prospective capex,
   not consideration. In no value field.
6. **Mohegan Pocono Downs, $175M + $50M.** The closing release also states the Authority
   planned to spend up to $175 million building the slot facility and pay a one-time $50
   million Pennsylvania license fee. Prospective spend and a regulatory fee, neither of them
   consideration. Excluded.
7. **Seneca / City of Buffalo, $631,000 vs $125 million.** The only actual purchase price is
   a $631,000 parcel, which is *below* the $1M threshold; the $125 million is a minimum
   committed capital investment. So `Announced_Value_USD` is blank, `Project_Total_Value_USD`
   is $125,000,000, and the $5–7M infrastructure and $1.7M/yr marketing commitments (a range
   and a recurring obligation) went into no value field at all.
8. **Mohegan Niagara — currency.** Every figure in that filing is Canadian dollars (C$290M
   facilities). `Announced_Value_USD` is **blank**. No conversion was performed and no
   exchange rate was invented.
9. **Sealaska / Independent Packers — a classification trap, not a value trap.** Trade press
   headlined it as an acquisition; Sealaska's own release says **minority interest**. The
   company wording governs; the row is an equity investment.
10. **Seneca head leases.** Dated, quantified ($62M→$81M fiscal-2009 rent), and *not a deal* —
    it is a tribe charging rent to its own wholly owned subsidiaries. Logged so the numbers
    are never mistaken for transaction values.

## Double-count hazards, flagged inside the rows themselves

The SEC channel produces multiple events on the *same instrument*. Three pairs are flagged
in the `Notes` field of the rows concerned:
- **ND-2003-003** (River Rock issues $200M of 9¾% notes) and **ND-2011-002** (the same $200M
  being restructured). Same instrument, two events. Never sum.
- **ND-2012-001** (Mohegan exchanges $961.8M across five series) overlaps **ND-2009-002**,
  **ND-2002-001** and **ND-2004-002**, which issued three of those five series.
- **ND-2004-001** ($300M, May 2004) and **ND-2005-002** ($200M, May 2005) are separate Seneca
  money, explicitly distinguished in the same prospectus. Those two *should* be summed.
- **ND-2008-001** ($50M Seneca revolver) is the facility that **ND-2010-001** replaced.

Aggregating `Announced_Value_USD` across this file without reading these notes will
overstate capital raised. Sum of the field as written is $9.49B across 26 valued rows.

## Skipped and excluded leads — 28

| Reason | Count |
|---|---|
| `no_date` | 11 |
| `no_amount` | 9 |
| `out_of_window` | 4 |
| `aggregator_only` | 4 |

Four `out_of_window` entries are deliberate contamination-prevention records for
transactions that ARE in the ledger under a different year (Hard Rock 2006→2007, Pocono
Downs 2004→2005, Sands Bethlehem Jun 3→May 31) or that are not deals at all (Seneca head
leases).

## Blocks hit

| Domain | Status | Consequence |
|---|---|---|
| `sec.gov` via **WebFetch** | HTTP 403 | **Worked around with curl + declared User-Agent.** This is the single most useful access finding of the run |
| `olgoonik.com` | HTTP 403 | Primary ASRC release on the Shell JV unreachable; ND-2014-001 stuck at Medium |
| `seattletimes.com` | HTTP 403 | Salish Lodge corroboration came from the tribal release + Native press instead |
| `refrigeratedfrozenfood.com` | HTTP 403 | Sealaska/IPC trade coverage unreadable; company wording used |
| `chickasaw.com/about/news/2017` | HTTP 404 | CNI newsroom floor is 2018 for automated fetch |
| `beringstraits.com/category/company-news/` | fetches, renders 2026 only | Archive reaches Dec 2010 but needs paging |
| `snoqualmietribe.us/content/...` | HTTP 404 | Alternate slug `snoqualmietribe.us/snoqualmie-muckleshoot-.../` works |

Previously known blocks (`nana.com`, `ahtna.com`, `crainsgrandrapids.com`, `journalstar.com`)
were not re-tested and remain on the manual-download queue.

## Confidence distribution

| Confidence | Count | Which |
|---|---|---|
| High | 35 | Primary SEC filing text, or primary company release, or primary + independent |
| Medium | 5 | ND-2001-001 (month-level date only), ND-2009-001 (closing date unknown), ND-2011-001 (single trade-press source), ND-2014-001 (5-day date conflict, no value), ND-2017-001 (single secondary source, ceiling not obligation) |

Every Medium row states its reason in `Notes` and its date limitation in `Date_Basis`.
One row, **ND-2001-001**, carries a mid-month placeholder date (2001-03-15) because the
filing says only "In March 2001". It is disclosed in `Date_Basis` in capitals. **No other row
in this file has an invented day.**

## Ownership-change records to emit

19 of the 40 rows are acquisitions, divestitures or interest changes and should emit records
into the time-aware attribution ledger. The most valuable:
- **ND-2019-007** — Salish Lodge moves **between two tribes**, Muckleshoot → Snoqualmie,
  2019-10-31. A divestiture and an acquisition in one transaction; recorded as one row, and
  the Notes say so explicitly so it is never entered twice.
- **ND-2007-001** — Hard Rock International enters the Seminole family 2007-03-05. A global
  brand with hundreds of establishments changing to tribal ownership on a known date is
  probably the single highest-value ownership-change record in the whole ledger.
- **ND-2019-002** — Sands Bethlehem enters the Poarch Band family 2019-05-31.
- **ND-2005-001** — Pocono Downs and five OTW operations enter the Mohegan family 2005-01-25.

## Follow-ups, ranked

1. **Page ANC newsroom archives for 2010–2017** (Bering Straits back to Dec 2010; Chugach;
   Koniag; Calista; Doyon; Afognak; Goldbelt). This is where the window is thinnest and where
   the expected source underdelivered.
2. **Muckleshoot's 2007 Salish Lodge purchase, $62.5M** — price and year are corroborated in
   two retrieved sources; only the day is missing. Would double the 2007 count and pair with
   ND-2019-007 into a complete twelve-year hold-and-sell arc on one asset.
3. **Ho-Chunk, Inc. / Dynamic Homes (2000)** — the best remaining shot at a second year-2000
   row.
4. **Waséyabek's first three acquisitions (pre-Feb 2018)** — known to exist from WDC's own
   text; three rows in the soft 2016–2017 patch.
5. **Extend the SEC channel.** Seven registrants were found; more certainly exist (Mashantucket
   Pequot, Shingle Springs, Jamul, Downstream/Quapaw, Santa Ysabel, Tunica-Biloxi, Cow Creek,
   Snoqualmie Entertainment Authority were all searched for and not resolved by name in this
   run). Each additional registrant is worth roughly 1–5 precisely dated 2000s rows.
6. **Remington Park closing date** — pull the Delaware bankruptcy sale order. If the closing
   is 2010, ND-2009-001 must be re-dated.
7. **Chickasaw newsroom pre-2018 via web.archive.org** — CNI was acquisitive well before its
   live archive floor.
8. **FPDS/USAspending** for the four contract-award rows (ND-2017-001, ND-2019-004/005/006) to
   convert reported ceilings into obligated dollars and true award dates.
