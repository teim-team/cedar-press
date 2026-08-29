# Deals Build Log — SEC EDGAR channel, 2010–2017 soft spot, 2026-08-05

Dataset 1 (Indian Country Deals). Window: **2010-01-01 through 2017-12-31**.
Single channel: **SEC EDGAR**, the channel the 2000–2019 backfill identified as highest-yield.

**Outputs**
- `data/clean/deals_sec_2010_2017_additions.csv` — **16 rows**
- `review/deals_skipped_sec_2010_2017.csv` — **26 skipped / excluded leads**
- Log: `logs/28_deals_sec_2010_2017.log`

Nothing was written into `deals_2026_ytd.csv` or `deals_historical_2020_2025.csv`.
`data/spine/`, `data/clean/cedar_*` and `review/cedar_review.html` were not touched.

Schema validated column-for-column against `deals_historical_2020_2025.csv`: **32 columns, identical
order**. Deal_IDs checked against both live ledgers and all three existing additions files
(`deals_2000_2019_additions.csv`, `deals_historical_additions.csv`, `deals_2026_ytd_additions.csv`):
**zero collisions, zero internal duplicates**. IDs continue the `ND-<year>-###` sequence from the
highest number already used in each year, so the file merges cleanly with
`deals_2000_2019_additions.csv`.

---

## Access

`WebFetch` returns HTTP 403 on sec.gov; `curl`/`urllib` with a declared User-Agent (name + contact
email) returns 200. That finding from the prior run held for every request in this session. Three
endpoints were used:

1. **`www.sec.gov/Archives/edgar/full-index/<year>/<QTR>/company.idx`** — the quarterly filing index.
   All 32 files for 2010–2017 (1.2 GB) were downloaded and scanned. **This is the new access
   technique worth memorialising.** It converts registrant discovery from a guessing game into a
   census: every filer name with any filing in the window, exhaustively.
2. **`data.sec.gov/submissions/CIK##########.json`** — per-registrant filing lists with 8-K item tags.
3. **`efts.sec.gov/LATEST/search-index?q=`** — full-text search, used for counterparty discovery
   (tribal entities appearing inside public companies' filings) and for closing the Form D universe.

Every date and dollar figure below was re-read in retrieved filing text. No figure came from a search
summary.

---

## The registrant census — the main methodological result

The prior run found seven tribal registrants by name-guessing and correctly noted "more certainly
exist." **That guess was wrong, and it is now settled.** Scanning the full 2010–2017 EDGAR company
index for 180+ tribal, rancheria, pueblo, band, nation, authority and Alaska Native name patterns
produced 663 candidate CIKs. Hand review of those reduces to this complete list.

### Tribal / ANC entities with ANY filing in 2010–2017

| Registrant | CIK | Nation / corporation | Filings in window | Rows |
|---|---|---|---|---|
| Mohegan Tribal Gaming Authority | 1005276 | Mohegan Tribe of Indians of CT | 199 | **3** |
| River Rock Entertainment Authority | 1288924 | Dry Creek Rancheria Band of Pomo | 29 | **1** |
| Seneca Gaming Corporation | 1296785 | Seneca Nation of Indians | 14 (2010 only) | 0 (dup) |
| Inn of the Mountain Gods Resorts & Casino | 1280352 | Mescalero Apache Tribe | 13 (to Feb 2011) | **1** |
| Kavilco Incorporated | 859765 | Kasaan (ANC village corporation) | 134 | 0 |
| Confederated Tribes of Coos, Lower Umpqua & Siuslaw | 1591305 | same | 2 (Form D) | **2** |
| Oglala Sioux Tribe of the Pine Ridge Indian Reservation | 1422871 | same | 1 (Form D) | **1** |
| Santa Ynez Band of Chumash Indians | 1464764 | same | 1 (SC 13D/A) | 0 |
| Chickasaw Nation Industries, Inc. / CNI Commercial LLC | 1641675 / 1641673 | Chickasaw Nation | 2 | 0 |
| Arctic Slope Regional Corporation | 1428711 | ANC regional | 2 | **1** |
| Bristol Bay Native Corporation Education Foundation | 1605634 | BBNC-affiliated | 2 | 0 |

Plus eleven Mohegan co-registrant guarantor subsidiaries (Downs Racing LP, Backside LP, Mill Creek
Land LP, Northeast Concessions LP, Mohegan Commercial Ventures PA LLC, Mohegan Basketball Club LLC,
Mohegan Ventures-Northwest LLC, Mohegan Golf LLC, Mohegan Ventures Wisconsin LLC, Wisconsin Tribal
Gaming LLC, MTGA Gaming LLC), which file only as co-signatories and generate no independent deals.

### NEW registrants discovered this run (reusable list)

Six that were not on the prior run's list of seven:

- **Kavilco Incorporated** (CIK 859765) — an Alaska Native village corporation that is also a
  registered investment company. No deals in the window, but its N-CSR portfolio schedules are an
  unexploited source of ANC investment data.
- **Confederated Tribes of Coos, Lower Umpqua & Siuslaw Indians** (CIK 1591305) — Form D issuer, two rows.
- **Oglala Sioux Tribe** (CIK 1422871) — Form D issuer, one row.
- **Santa Ynez Band of Chumash Indians** (CIK 1464764) — Schedule 13D filer via Chumash Financial Holdings LLC.
- **Chickasaw Nation Industries, Inc.** and **CNI Commercial LLC** (CIKs 1641675 / 1641673) — Form 3 and Schedule 13D on Ekso Bionics.
- **Arctic Slope Regional Corporation** (CIK 1428711) — Schedule 13D filer, one row and the second-largest value in the file.

**Three of those six are not gaming authorities.** That matters: the channel is not only a casino-debt
channel. Tribes appear on EDGAR in three distinct capacities — as debt issuers (Mohegan, River Rock,
Seneca, IMG), as **Form D exempt-offering issuers** (Coos, Oglala), and as **equity holders filing
13D/13G/Section 16** (ASRC, Chumash, CNI, BBNC Foundation). The prior run had only found the first.

### Registrants confirmed ABSENT (do not re-search)

Every candidate the brief named was checked against the full index and none has a 2010–2017 filing:
San Manuel, Morongo, Pechanga, Santa Ysabel, Jamul (as issuer), Quapaw / Downstream Development
Authority, Wind Creek / PCI Gaming, Kalispel, Snoqualmie, Tulalip, Muckleshoot, Cow Creek / Umpqua,
Yavapai-Apache, Fort McDowell, Gila River, Salt River, Cherokee Nation Entertainment,
Chickasaw / Global Gaming, Choctaw Nation, Citizen Potawatomi, Osage, Prairie Band, Ho-Chunk, Oneida,
Forest County Potawatomi, Lac du Flambeau, Saginaw Chippewa, Little Traverse Bay, Gun Lake, Soaring
Eagle, Turning Stone. Also absent: Choctaw Resort Development Enterprise, Chukchansi Economic
Development Authority and Agua Caliente, all three of which the prior run had found for earlier years
but which filed nothing in this window. Mashantucket Pequot, Shingle Springs and Tunica-Biloxi are
likewise absent as registrants.

The reason is structural and worth recording: these tribes finance through Rule 144A private
placements that are never registered and never require an exchange offer, so they leave no EDGAR
trail at all. **"Extend the SEC channel" (follow-up 5 in the prior log) is now closed.** There are no
more tribal registrants to find in this window.

### The second seam: Native entities as counterparties in public companies' filings

This is where a third of the rows came from, and it is the seam with room left. Full-text search of
8-Ks surfaced dated, quantified transactions where the tribe is a principal but the *filer* is not:

| Filer | Native principal | Rows |
|---|---|---|
| Lakes Entertainment / Golden Entertainment (CIK 1071255) | Iowa Tribe of OK; Jamul Indian Village; Shingle Springs Band of Miwok Indians | **3** |
| Penn National Gaming (CIK 921738) | Jamul Indian Village / JIVDC | **2** |
| Canterbury Park Holding Corporation (CIK 926761) | Shakopee Mdewakanton Sioux Community | **1** |
| General Communication, Inc. (via ASRC's own 13D/A) | Arctic Slope Regional Corporation | **1** |

Lakes Entertainment alone is worth flagging as a permanent lead index: it was counterparty to four
different tribes across the window and filed an Item 1.01 8-K for each stage of each relationship.

---

## Rows by year

| Year | Rows | Prior count | Now |
|---|---|---|---|
| 2010 | **3** | 1 | 4 |
| 2011 | **2** | 2 | 4 |
| 2012 | **2** | 1 | 3 |
| 2013 | **5** | 1 | 6 |
| 2014 | **0** | 1 | 1 |
| 2015 | **2** | 1 | 3 |
| 2016 | **1** | 2 | 3 |
| 2017 | **1** | 1 | 2 |

The window goes from **9 rows across eight years to 25**, a 2.8× increase. Sum of
`Announced_Value_USD` as written is **$2,096,178,803.69 across 12 valued rows** — read the
double-count notes before aggregating.

Confidence: **15 High, 1 Medium**. The single Medium is ND-2010-004 (Inn of the Mountain Gods),
where the exchange offer's completion date does not exist in SEC evidence because the registrant
deregistered while the offer was still open.

No row in this file carries an invented day. Every `Event_Date` is a day-level date quoted from
filing text, and each row's `Date_Basis` names the clause it came from.

---

## Value traps caught

1. **Mohegan's $200 million UBS facility.** The November 2015 Facility Agreement permits issuance of
   *up to* $200 million. Only **$100 million** was actually issued and closed on November 20, 2015.
   Capacity is not a deal value. ND-2015-003 carries $100,000,000.
2. **Mohegan's August 2015 $175 million.** The 8-K contains three large numbers: $90M of increase
   term B loans, $85M of add-on notes, and $175M of subordinated notes redeemed. The first two are
   new money; the third is the *use* of that money. `Announced_Value_USD` is $175,000,000 = 90 + 85,
   not 90 + 85 + 175.
3. **Jamul's $274 million.** Of the ~$460 million of October 2016 facilities, approximately
   $274 million repaid Penn's subsidiary for prior construction loans. Use of proceeds, not
   additional value. Excluded.
4. **Penn/Jamul's $360 million.** Project capex for Hollywood Casino Jamul, quoted in Penn's 10-Q and
   Lakes' release. It is in `Project_Total_Value_USD` only, never in `Announced_Value_USD`.
5. **Jamul's $400 million and $60 million (April 2014).** The $400 million is a *cap on permitted
   future refinancing* in an intercreditor amendment; the $60 million is a pre-existing balance owed
   to Lakes. Neither is consideration. The whole April 2014 instrument was skipped.
6. **SMSC's $75 million + $8.5 million.** Ten-year recurring commitments to Canterbury Park, not a
   purchase price. `Announced_Value_USD` is blank; `Project_Total_Value_USD` is $83,500,000 with an
   explicit warning in Notes. The 2012 payments of $2.7M and $300,000 are the *first year of that
   same commitment* and are not added on top.
7. **Inn of the Mountain Gods' $51.8 million.** Accrued unpaid interest, and the $12.0 million
   semi-annual interest payments. Neither is in any value field; only the $200.0 million principal
   subject to the exchange is.
8. **River Rock's Proschold parcel.** The $9.0 million easement price is stated; the purchase price
   of the underlying ~310-acre parcel is not. Only the $9.0 million is recorded.
9. **ilani's fee formulas.** 24% of net revenues and 3% of total project costs are percentage
   formulas, not consideration. ND-2017-002 has no value field populated, and ilani's project cost
   was deliberately not inferred from any outside source.
10. **The Iowa Tribe's $5.0 million.** Prior advances under the Ioway Note. The consideration is the
    $4.5 million termination payment; the $5.0 million is excluded.

## Date traps caught

- **Shingle Springs.** The Debt Termination Agreement is dated **July 17, 2013**; the $57.1 million
  was actually paid and the ten underlying agreements terminated effective **August 29, 2013**. Filed
  at the completion date. This is the Hard Rock lesson applied: two 8-Ks, one transaction, one row.
- **SMSC / Canterbury Park.** Signed **June 4, 2012**; became effective **June 15, 2012** after three
  conditions precedent were satisfied on June 4, 13 and 14. Filed at effectiveness.
- **River Rock easement.** The 8-K narrative says the Authority entered the easement on **August 3,
  2011**; the exhibit is dated "as of July 31, 2011". The narrative date is used and the discrepancy
  is disclosed in `Date_Basis` rather than silently resolved.
- **Mohegan's failed 2014 tender offer.** Commenced April 22, 2014, **terminated May 1, 2014 with
  none of the notes purchased and no consent fees paid.** A sweep that read only the commencement
  release would create a phantom 2014 row. Logged explicitly as contamination prevention.

## Double-count hazards, flagged inside the rows

The SEC channel keeps producing multiple events on one instrument. Four chains are flagged in Notes:

- **ND-2013-006** ($955M facilities, Nov 2013) **retires** the 11.5% second lien notes created by
  **ND-2012-001** (March 6, 2012 indenture) and the old second lien notes from **ND-2009-002**
  (October 26, 2009 indenture). Never sum.
- **ND-2015-002** ($85M add-on) is a **tap of the same series** as **ND-2013-001** ($500M, Aug 2013).
  Combined outstanding is $585M, not $1.085B. Its $90M term B increase is an add-on to ND-2013-006.
- **ND-2013-004 + ND-2013-005** are two Form D notices filed the same day by the same tribe with the
  same first-sale date. They are separate offerings (separate accessions, 8 vs 6 investors) and the
  combined 2013 exchange is $53,462,053. Both are **refinancings of existing debt**, not new capital.
- **ND-2011-004 → ND-2013-002 → ND-2016-003** are three stages of the *same Jamul casino project*
  (Lakes development agreement → Penn definitive agreements → $460M permanent financing). Never sum
  across the three.
- Also logged, not written: **River Rock's exchange completed December 21, 2011 at $196,393,000
  (98.20% tendered)**. That is the completion of the instrument already recorded as ND-2011-002 and
  was deliberately NOT given a second row. A maintainer may re-date ND-2011-002 using that source.

## Skips — 26

| Reason | Count |
|---|---|
| `no_amount` | 9 |
| `no_date` | 4 |
| `no_transaction` | 3 |
| `not_native_principal` | 3 |
| `duplicate_instrument` | 2 |
| `not_a_deal` | 2 |
| `universe_exhausted` | 2 |
| `below_threshold` | 1 |

Two skip records are **negative universe findings** rather than leads — the registrant census and the
Form D census. They exist so no future session repeats the search.

Two are **false-positive classes** that will keep polluting phrase searches and should be excluded up
front: **Ark Restaurants Corp.** (CIK 779544), whose dividend releases carry "operated by the Seminole
Indian Tribe" in the boilerplate footer of every filing, and gaming-supplier credit agreements
(AGS, Everi, IGT, Scientific Games) whose covenant carve-outs name Indian tribes generically.

---

## Is 2010–2017 now adequately covered? An honest answer.

**Partly. The SEC channel for this window is now exhausted, and it was not enough.**

What is genuinely settled:
- The registrant universe is closed. There are no more tribal SEC registrants to find in 2010–2017,
  and that is now demonstrated by exhaustive index scan rather than asserted.
- The Form D seam is closed for tribal-government issuers: exactly three filings exist and all three
  are captured.
- The counterparty seam (tribes inside public companies' 8-Ks) has been worked hard but **not
  exhausted**. It is the only part of this channel with room left.

What is still thin:
- **2014 has zero SEC-channel rows and this is a real hole, not a search failure.** Every candidate
  failed on a stated ground, and the cause is structural: Mohegan had refinanced in November 2013 and
  would not return to market until August 2015, and its single 2014 attempt — an April consent
  solicitation and tender offer — failed the majority-consent condition and was terminated on May 1
  with nothing purchased. River Rock, Seneca and Inn of the Mountain Gods had all deregistered by
  early 2012. There was simply no tribal issuance activity on EDGAR in 2014.
- **2016 and 2017 have one new row each.** Both are real, but both years remain thin.
- The window still averages about **3.1 rows/year** against the roughly 9 rows/year that the prior run
  established as the shape of a fully worked year. So the capture rate for 2010–2017 is now on the
  order of **35%** of a fully worked year, up from about 12%.

The reachability finding from the prior run is confirmed and sharpened: **reachability tracks whether
a tribal entity had public debt OR a public-company counterparty.** 2000–2005 was reachable because
five tribal authorities were actively issuing registered debt. 2010–2017 is harder because that
cohort deregistered — Seneca in December 2010, Inn of the Mountain Gods in February 2011, River Rock
in January 2012 — leaving Mohegan as effectively the only continuing tribal registrant, while the
rest of Indian Country moved to Rule 144A placements that never touch EDGAR.

### Where the remaining 2010–2017 rows are, ranked

1. **Rule 144A / private tribal debt.** This is the largest single body of missing 2010–2017
   transactions and it is invisible to EDGAR by construction. Chukchansi's 2011 notes and 2014–2016
   restructuring, the Seminole Tribe's 2014 refinancing, Mashantucket Pequot's 2013 restructuring,
   Shingle Springs' 2013 refinancing (the source of the $57.1 million in ND-2013-003) and Cowlitz's
   ilani construction financing all happened and none is on EDGAR. **MSRB EMMA and rating-agency
   press releases (Moody's, S&P, Fitch) are the right channel** — rating actions are dated to the day
   and state the instrument and amount. This is the single highest-value next move for this window.
2. **ANC newsroom paging, 2010–2017.** Still the prior run's ranked follow-up 1 and still unworked.
   This run confirms why it matters: the two ANC rows here (ASRC/GCI, and nothing else) came from a
   13D, not from a newsroom, and ANCs were acquisitive throughout this decade.
3. **The counterparty seam, extended.** Lakes Entertainment produced three rows from one CIK. The
   same pattern — a public gaming or resource company filing Item 1.01 8-Ks for each stage of a
   tribal relationship — should be run against Full House Resorts, Century Casinos, Nevada Gold &
   Casinos, Warwick Valley / Empire Resorts and Butler National (Modoc Tribe).
4. **NIGC-approved management agreements.** Several rows and skips here turn on management agreements
   whose fee schedules are public at the NIGC but absent from SEC filings (Inn of the Mountain Gods /
   WG-IMG 2010; Mohegan / Tunica-Biloxi 2016). The NIGC approval letter dates are day-level.
5. **Three specific named follow-ups** already logged as skips: the MMCT (Mohegan + Mashantucket
   Pequot) East Windsor development agreement, February 2017 — a two-tribe JV that needs a day-level
   date; Mohegan's increase in Salishan-Mohegan from 49.15% to 81.92% during FY2017 — an undated
   interest acquisition; and the Boyd Gaming / Wilton Rancheria development and management agreement,
   undated in any SEC filing.
