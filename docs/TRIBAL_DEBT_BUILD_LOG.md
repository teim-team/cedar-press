# Tribal Debt Build Log — Rule 144A / private tribal debt and tribal bond finance, 2026-08-05

Dataset 1 (Indian Country Deals) plus the seed for the Q4 candidate dataset **tribal municipal/bond
finance**. Priority window **2010-01-01 to 2017-12-31**, extended beyond it where cheap.

Acting on follow-up 1 of `docs/DEALS_SEC_2010_2017_BUILD_LOG.md`: the transactions missing from
2010–2017 are Rule 144A private tribal debt, invisible to EDGAR by construction.

**Outputs**
- `data/clean/deals_tribal_debt_additions.csv` — **6 rows**, 32 columns, schema-identical to `deals_historical_2020_2025.csv`
- `data/clean/tribal_bond_issuances.csv` — **29 rows**, standalone issuance register
- `review/deals_skipped_tribal_debt.csv` — **18 skips / negative findings**
- Log: `logs/37_tribal_debt.log`

Nothing was written into `deals_2026_ytd.csv` or `deals_historical_2020_2025.csv`. `data/spine/`,
`data/clean/cedar_*` and `review/cedar_review*.html` were not touched.

Deal_IDs use a fresh **`ND-<year>-3xx`** block, checked against both live ledgers and **all five**
existing additions files (`deals_2000_2019_additions.csv`, `deals_historical_additions.csv`,
`deals_2026_ytd_additions.csv`, `deals_anc_reports_additions.csv`, `deals_sec_2010_2017_additions.csv`,
plus `deals_federal_awards_additions.csv`): 918 existing IDs, **zero collisions**, and no `3xx` ID
existed anywhere before this run.

---

## Access: what opened, what closed, and what was refused

| Host / endpoint | Result |
|---|---|
| `emma.msrb.org/` | 200 with a declared browser User-Agent |
| `emma.msrb.org/QuickSearch/SearchAhead` (POST JSON) | **200, un-gated** — the public type-ahead. Returns the issuer roster. |
| `emma.msrb.org/IssuerHomePage/Issuer?id=…` | 200, **but the body is the MSRB Terms of Use click-through**, not issuer data |
| `emma.msrb.org/robots.txt` | `Disallow: /*.pdf$` — every official statement is robots-disallowed |
| `www.moodys.com/credit-ratings/<entity>` | **302 → `/account/sign-in`** (registration gated) |
| `www.moodys.com/research/…?docid=PR_…` | 200 but a single-page-application shell, no content |
| `www.moodys.com/sitemap*.xml` | **200 — the opening**, ~200,000 URLs, robots-sanctioned |
| `www.fitchratings.com/research/…` | 200 but Gatsby SPA; content only under `/page-data/`, which **robots.txt disallows** |
| `www.spglobal.com/ratings/en/` | **403** |
| `web.archive.org/cdx` + `/web/<ts>id_/…` | **200 — the second opening**; archived Moody's releases render full text with dates and amounts |

### Two refusals, recorded as refusals

1. **MSRB EMMA's document layer was not scraped.** Issuer pages sit behind a Terms-of-Use
   click-through, and the MSRB Terms of Use expressly prohibit "any data mining, crawling, 'scraping',
   robot or similar automated or data gathering or extraction method" and prohibit using the content
   "to develop or create a database to be sold, leased, furnished, licensed or otherwise exploited."
   The click-through was not bypassed and no PDF was fetched. Only the public, un-gated type-ahead was
   used, for **issuer names only** — no par amounts, no dates, no CUSIPs.

   **This is a commercial blocker Elijah needs to resolve, not just an access note.** Cedar Press is a
   paid product. Publishing EMMA-derived figures in it would run directly into that clause. The clean
   paths are (a) an MSRB data licence — MSRB sells subscription feeds, or (b) sourcing the same
   official statements from issuers and underwriters directly. Logged as `SK-TD-001`.

2. **Fitch was not scraped through `/page-data/`.** That is the only path carrying the release text and
   `robots.txt` disallows it. Fitch is therefore absent from this run except through its public sitemaps,
   which contain exactly one tribal entity (Southern Ute Indian Tribe CO). S&P returned 403 throughout.

### The access finding worth memorialising

**Moody's rating actions are publicly readable through the Internet Archive, and they are dated to the
day and state instrument and amount.** The live site is registration-gated, but these releases were
served publicly at publication and the Internet Archive captured a subset of them. Combining
(1) Moody's own public sitemaps for issuer discovery with (2) the Wayback CDX index of
`moodys.com/research/*` for retrieval turns tribal 144A debt from unreachable into partly reachable.
That combination is the reusable technique from this run, the analogue of the EDGAR
`company.idx` census in the previous one.

Two hard limits on it, both established here rather than assumed:
- Wayback's coverage of `moodys.com` is **sparse and non-systematic**. Release URLs enumerated from
  archived issuer pages but absent from the CDX index returned HTTP 404 essentially every time. **An
  issuer's release list is not a retrieval list.**
- Snapshots taken after Moody's moved to a single-page application capture only the 2.7 KB shell. The
  Shingle Springs release `PR_356774` is archived (snapshot `20250520174512`, HTTP 200) and still
  yields nothing.

---

## The Moody's tribal issuer census

Scanning Moody's public sitemaps against 220 tribal name patterns produced 444 candidate URLs, which
hand review reduces to **32 tribal rated entities plus 5 tribal New Public Housing Authorities**. This
is a reusable positive-and-negative universe result: do not re-derive it, extend it. Credit-rating IDs
are given so a subscriber can pull each issuer directly.

| Entity | Moody's credit-rating ID | Releases retrieved here |
|---|---|---|
| Mohegan Tribal Gaming Authority | 600018207 | yes (2010, 2021 ×2) |
| Seminole Tribe of Florida | 805702195 | yes (2007, 2013) |
| Seminole Hard Rock Entertainment Inc | 820024472 | no |
| Mashantucket (Western) Pequot Tribe CT | 600023334 | yes (2021, 2022) |
| Chukchansi Economic Development Authority | 808810542 | yes (2011 only) |
| Shingle Springs Tribal Gaming Authority | 820258471 | no (SPA shell only) |
| Cowlitz Tribal Gaming Authority | 824621960 | no |
| Choctaw Resort Development Enterprise | 600058604 | yes (2001–2016, 12 actions) |
| Downstream Development Authority | 820355688 | yes (2010–2020, 6 actions) |
| Snoqualmie Entertainment Authority | 815149259 | yes (2010, 2011 ×2, 2013) |
| Little Traverse Bay Bands of Odawa Indians | 808810694 | yes (2005–2009, 6 actions) |
| River Rock Entertainment Authority | 806763148 / 869437923 | yes (2011) |
| Tunica-Biloxi Gaming Authority | 808819656 | yes (2010) |
| Seneca Gaming Corporation | 807512559 | no |
| Inn of the Mountain Gods Resort and Casino | 806672648 | no |
| Jamul Indian Village Development Corporation | 824726134 | no |
| Gun Lake Tribal Gaming Authority | 821985752 | no |
| Kalispel Tribal Economic Authority | 822426544 | no |
| Pokagon Gaming Authority | 809523915 | no |
| Catawba Nation Gaming Authority | 869331585 | no |
| Chumash Casino and Resort Enterprise | 600065598 | no |
| Cow Creek Band of Umpqua Tribe OR | 802829321 | no |
| Confederated Tribes of Warm Springs Reservation OR | 600046773 | no |
| United Auburn Indian Community | 600070884 | no |
| Lac du Flambeau Band of Lake Superior Chippewa WI | 444375 | no |
| Lummi Nation, Washington | 600050121 / 400010640 | no |
| Oneida Indian Nation NY | 600057286 / 400014512 / 400022326 | no |
| Salt River Pima-Maricopa Indian Community AZ | 600005233 | no |
| Sault Ste Marie Tribe Building Authority | 600028898 | no |
| White Mountain Apache Housing Authority | 600051396 / 400011201 | no |
| Yakama Indian Nation (Confederated Tribes and Bands) | 600035720 / 400004706 | no |
| Southern Ute Indian Tribe CO | Fitch 80105265 | no (Fitch, robots-blocked) |

Tribal New Public Housing Authorities rated by Moody's: **Blackfeet** (808447821), **Cheyenne River**
(808474995), **Fort Peck** (808463193), **Jicarilla** (808398023), **Navajo** (808548754). These are a
distinct, unexploited seam — HUD-guaranteed tribal housing paper, not gaming.

**False-positive classes that will keep polluting tribal name searches** and should be excluded up
front: Choctaw Generation LP (a Mississippi lignite power project, not tribal), Seminole County FL and
Seminole Electric Cooperative, Saginaw Valley State University, Shakopee ISD 720 / City of Shakopee,
Muscogee County GA schools, Cowlitz County WA, Catawba County/College/Valley NC, Bristol Bay Funding,
Warm Springs Rehabilitation Foundation TX, Little Traverse Township MI, Mohawk Industries and Niagara
Mohawk Power, Dry Creek Joint Elementary School District CA, and the very large family of URLs
containing "sovereign" in the sovereign-debt sense.

---

## The EMMA tribal issuer roster — the bond-finance dataset seed

Names only, from the public type-ahead. **No financial data was taken from EMMA.** Roughly **95 tribal
issuer records** across ~70 distinct tribal governments. This is the single most valuable artefact of
the run for the Q4 "tribal municipal/bond finance (EMMA)" dataset.

The important structural finding: **tribal municipal issuance is overwhelmingly not gaming debt.** The
roster is dominated by housing authorities, health facilities, water and sewer, sales-tax revenue,
tribal infrastructure and general governmental purposes. Cedar Press has been treating tribal debt as a
casino story; EMMA says it is mostly a government-finance story.

Gaming / enterprise issuers: Agua Caliente Dev Auth CA · Barona Band of Mission Indians CA · Cabazon
Band of Mission Indians CA (+ special leasehold tax rev) · Fort McDowell Yavapai Nation Gaming Rev AZ ·
Fort Sill Apache Tribe OK Economic Dev Auth Gaming Enterprise Rev · Grand Traverse Band Economic Dev
Corp MI · Kalispel Tribe Priority Distr WA · Laguna Dev Corp NM · Mohegan Tribal Finance Authority (×2)
· Mohegan Tribal Gaming Auth CT · Mohegan Tribe of Indians of CT · Morongo Band of Mission Indians CA
(×3) · River Rock Entertainment Auth / Dry Creek Rancheria CA · Santa Rosa Rancheria Tachi Yokut Tribe
CA (×2) · Seminole Tribe FL (×3) · Mashantucket Western Pequot Tribe CT (×3, incl. IAM commercial paper
Series 1996).

Government / infrastructure / health / housing issuers: Ak-Chin Indian Community AZ · Apache Tribe
Mescalero Reservation Housing Auth NM · Chemehuevi Indian Tribe · Cherokee Nation of OK (rev + health
care system) · Cheyenne River Sioux Tribal Finance Corp SD · Chickasaw Nation OK (+ COPs) · Citizen
Potawatomi Nation OK · Cow Creek Band of Umpqua Tribe OR · Crow Finance Auth MT · Eastern Band of
Cherokee Indians NC · Fort Mojave Indian Tribe AZ/CA (×4, incl. water & sewer) · Grand Ronde Community
OR · Jicarilla Apache Nation/Tribe NM (×2) · Klamath Tribes OR · Lac Courte Oreilles Band WI (×2) · Lac
du Flambeau Band WI · Lummi Nation WA · Mille Lacs Band of Ojibwe Corporate Commission MN · Navajo
Nation AZ · Navajo Tribal Utility Authority (×2) · Nooksack Indian Tribe WA · Oglala Sioux Tribe SD
(×3: essential governmental function, sales tax, tribal rev) · Omaha Tribe NE Public Improvements Auth
· Oneida Indian Nation NY (×2) · Oneida Tribe of Indians WI (health facility + retail sales) · Pueblo
of Sandia NM (×2) · Pueblo of Santa Ana NM · Quechan Indian Tribe Fort Yuma CA/AZ · Quinault Indian
Nation WA · Red Lake Band of Chippewa Indians MN · Salt River Pima-Maricopa Indian Community AZ (×2) ·
San Carlos Apache Healthcare Corporation · Sault Ste Marie Chippewa Indians Housing Auth MI · Sault Ste
Marie Tribe Building Auth MI · Seneca Nation Capital Improvements Auth NY · Shoalwater Bay Indian Tribe
WA · Sisseton-Wahpeton Sioux Tribe SD · Southern Ute Indian Tribe CO · Squaxin Island Tribe WA · Three
Affiliated Tribes Fort Berthold ND · Tulalip Tribes WA (×2) · Umatilla Indian Reservation Confederated
Tribes OR (×2) · Confederated Tribes of Warm Springs OR (×2) · White Earth Band of Chippewa Indians MN
· White Mountain Apache Tribe AZ (+ housing auth) · Yakama Indian Nation WA · Yavapai-Apache Nation AZ.

Tribal New Public Housing Authorities on EMMA: Blackfeet MT · Cheyenne River SD · Fort Peck MT ·
Jicarilla NM · Oglala Sioux SD · San Carlos AZ · Seneca Nation NY · Standing Rock ND.

**Type-ahead false positives to filter in any reuse:** Chickasha OK (city), Little Rock AR Quapaw
Quarter business improvement district, Lake Mohegan NY Fire District, Pueblo CO, Colville WA (city),
Sisseton SD (city), Catawba NC (town), Indiana / Indianapolis / Indian Hills Community College, Indio
CA, Salt River Project AZ, Salt River MO, Church Rock Housing Finance LLC NM, Chicago airports,
National Finance Authority NH, United Nations Development Corporation.

---

## Rows written — 6

| Deal_ID | Date | Entity | Value | Confidence |
|---|---|---|---|---|
| ND-2007-301 | 2007-09-14 | Seminole Tribe of Florida — $459M special obligation bonds (2007A + 2007B) | $459,000,000 | Medium |
| ND-2012-301 | 2012-03-14 | Choctaw Resort Development Enterprise — $78M senior secured term loan due Feb 2017 | $78,000,000 | Medium |
| ND-2013-301 | 2013-04-02 | Seminole Tribe of Florida — $750M term loan B due 2020 | $750,000,000 | Medium |
| ND-2014-301 | 2014-07-10 | Choctaw Resort Development Enterprise — $145M senior secured term loan due 2019 | $145,000,000 | Medium |
| ND-2018-301 | 2018-02-22 | Downstream Development Authority (Quapaw) — $270M notes due 2023 + $40M term loan | $310,000,000 | Medium |
| ND-2021-301 | 2021-01-26 | Mohegan Tribal Gaming Authority — $1.175B second lien notes due 2026 | $1,175,000,000 | High |

### Rows by year

| Year | New rows | 2010–2017 window? |
|---|---|---|
| 2007 | 1 | no |
| 2012 | 1 | **yes** |
| 2013 | 1 | **yes** |
| 2014 | 1 | **yes** |
| 2018 | 1 | no |
| 2021 | 1 | no |

**Three rows land inside 2010–2017**, and one of them is the first transaction of any kind found for
**2014**, the year the exhausted SEC channel returned zero rows and the previous log called "a real
hole, not a search failure." That hole is now filled from a channel EDGAR cannot see, which is direct
evidence for the previous log's structural explanation.

Confidence is **1 High, 5 Medium**. The single High is ND-2021-301, the only row whose closing date is
quoted verbatim from a retrieved document ("on January 26, MTGA closed on a refinancing"). Every Medium
row carries a `Date_Basis` that names exactly which date it is using — rating-action date or
publication date — and says explicitly that no closing date exists in any retrieved document. **No row
carries an invented day.**

---

## Value traps caught

1. **Mohegan's $263 million revolver (Jan 2021).** Amended and extended, but less than $100 million was
   drawn pro forma. Capacity is not a transaction. ND-2021-301 carries only the $1.175 billion of notes.
2. **Mohegan's $232M + $814M + $55M + $100M.** Term loan A, term loan B, other debt and a revolver
   repayment — all uses of proceeds. Not added to the $1.175 billion.
3. **Choctaw's second $75 million (2014).** The July 2014 credit agreement carried *up to* $75 million
   of **additional** borrowing capacity for future capex on top of the $145 million drawn. Undrawn
   commitment, excluded. The other $75 million — the pre-funded capex tranche — is inside the $145M.
4. **Choctaw's $70 million (2014) and pre-existing term loan (2012).** Repayments, not consideration.
5. **Seminole's $794 million (2013).** The outstanding balance being refinanced. Excluded; only the
   $750 million new term loan B is recorded.
6. **Downstream's $32 million and $265 million (2018).** Refinanced facilities, excluded. Only the
   $270M notes + $40M term loan are in the value.
7. **Choctaw's $125 million revolver and $34 million tribal equity (2001).** A reducing revolver
   (capacity) and an equity contribution, neither of which is note principal.
8. **Mashantucket's "$2 billion" and "$1.8 billion."** Moody's states these as junior note **principal
   and accrued interest combined**. Accrued interest is not principal, so no principal figure can be
   extracted and none was recorded.
9. **Little Traverse's $6.3 million.** A semi-annual interest payment, not principal.
10. **Tunica-Biloxi's "approximately $150 million of rated debt affected."** A Moody's header figure for
    total rated debt, not a stated par. `par_amount` in the register is deliberately **blank**.

### Two pre-sale-versus-priced traps — a new trap class for this project

Rating agencies rate the **proposed** deal. The deal that prices is often a different size.

- **Choctaw 2001:** Moody's rated a proposed **$150 million**; the notes priced at **$200 million**
  (already in the ledger as ND-2001-001). A sweep that trusted the rating action would have understated
  the deal by 25%.
- **Little Traverse 2005:** Moody's rated a proposed **$195 million due 2013**; every later Moody's
  action describes the outstanding instrument as **$122 million 10.25% due 2014** — a different size
  *and* a different maturity. **No deal row was written at either figure**, because $195M is a size the
  tribe never sold and $122M has no retrievable pricing date. Both are in the register with the
  discrepancy stated.

**Add this to the standing trap list: a rating action headline amount is a launch size, not a
settlement size.** Where a deal row is written from a rating action alone, Confidence cannot exceed
Medium.

### Date traps caught

- **Downstream's December 2016 refinancing never happened.** Moody's placed the ratings on review on
  December 5, 2016 after the announcement, then on December 20 withdrew the B2 on the proposed $250
  million second lien notes because DDA "terminated the tender offer and consent solicitation … and as a
  result, will not be pursuing a refinancing." A sweep reading only the December 5 announcement creates
  a phantom $325 million 2016 row. Logged as `SK-TD-004`, no row written. Exactly parallel to Mohegan's
  failed April–May 2014 tender in the SEC run — **this is now the second instance, so failed tenders
  should be treated as a standing contamination class in tribal gaming, not a one-off.**
- **Mohegan announced January 13, 2021; closed January 26, 2021.** Filed at the closing date.
- **"Recently entered into" / "recently announced."** Both Choctaw rows rest on this phrasing. No day is
  invented; the publication date is used and the vagueness is disclosed in `Date_Basis`.

### Instrument chains — never sum

- **ND-2012-301 → ND-2014-301.** The $145 million 2019 term loan refinances the $78 million 2017 term
  loan (drawn down to $70 million). One credit line, two events.
- **ND-2013-301** refinances the 2007 Seminole term loan; **ND-2007-301** is a different instrument
  (special obligation bonds). They do not overlap and must not be netted against each other either.
- **`SK-TD-004` (terminated Dec 2016) → ND-2018-301.** The same refinancing, attempted and abandoned,
  then completed fourteen months later. Only the completion has a row.
- **ND-2021-301** is distinct from ND-2021-002 (INSPIRE Korea Phase 1, 2021-11-29) and ND-2025-001
  ($1.2 billion secured notes, 2025-04-10).
- **River Rock's $110m Series A + $95m Series B** pre-sale snapshot is the tranching of the exchange
  already recorded as ND-2011-002. Following the River Rock precedent from the SEC run, logged as
  `duplicate_instrument` (`SK-TD-007`), no second row.
- **Choctaw's $150M rated / $200M priced** is ND-2001-001, corroborated not duplicated (`SK-TD-006`).

---

## Skips — 18

| Reason | Count |
|---|---|
| `no_date` | 6 |
| `no_amount` | 4 |
| `refused_terms_of_use` | 1 |
| `refused_robots_and_403` | 1 |
| `registration_gated` | 1 |
| `duplicate_instrument` | 2 |
| `no_transaction` | 1 |
| `universe_exhausted` | 2 |

Four of these are **negative or universe findings** rather than leads, written so no future session
repeats the work: the EMMA refusal (`SK-TD-001`), the Moody's/Fitch/S&P gating (`SK-TD-002`,
`SK-TD-003`), the Moody's tribal issuer census (`SK-TD-015`), and the measured limit of Internet
Archive coverage (`SK-TD-016`).

**The highest-value skips carry exact Moody's document IDs**, so a subscriber can retrieve them in
minutes rather than re-running discovery:

- `SK-TD-011` **Chukchansi 2012 refinancing** — `PR_247365` ("assigns Caa2 to Chukchansi's 9.75%
  secured notes"), plus `PR_233708`, `PR_242437`, `PR_272606`, `PR_290707` covering the restructuring,
  the limited default, the D-PD and the ratings withdrawal. All confirmed to exist, none archived.
- `SK-TD-013` **Seminole $395 million incremental term loan** — `PR_284098`. The docid sits between
  `PR_269885` (2013-04-02) and `PR_303516` (2014-07-10), so it is very probably an in-window 2013–14
  transaction. **"Probably" is not a date and no row was written.**
- `SK-TD-018` **Gun Lake's proposed $160 million term loan** — `PR_195611`, sitemap `lastmod`
  2010-06-18. A sitemap lastmod is not a transaction date and a URL slug is not a retrieved document,
  so no row was written despite this being very likely a real 2010 in-window financing.
- `SK-TD-014` **Seminole Series 2010A ($37M) and 2010B ($330M)**, both due October 2017. $367 million of
  issuance squarely inside the window, itemised with exact par, coupon and maturity in the 2013 Moody's
  action, but with no retrievable issue date. Both are in the register with a blank `issue_date`.

---

## The issuance register — `tribal_bond_issuances.csv`

29 rows across 11 issuers, every `par_amount` quoted from a retrieved Moody's rating action.

Two columns were **added** to the schema named in the brief: `date_basis` and `notes`. They are additive
and are there because the register's central integrity problem is that a retrieved document often gives
par, coupon, maturity and rating but **not** an issue date. Rather than mislabel a rating-action date as
an issue date, `issue_date` is left blank and `date_basis` says why. Exactly **one** row carries a
populated `issue_date`: Mohegan's 2021-01-26 second lien notes, the only stated closing date in the
entire corpus retrieved.

That ratio — 1 issue date out of 29 instruments — is the honest measure of what this channel currently
delivers. Rating actions are excellent for *what* and *how much*, and poor for *when*.

---

## Does this close 2010–2017? No. Here is where the floor is.

**It does not close, and the floor is now measurable rather than suspected.**

What genuinely improved:
- The 2010–2017 window gains **3 rows**, including the **first-ever 2014 row from any channel**. Against
  the SEC log's 25 rows for the window, that is a 12% increase, and it comes from precisely the channel
  the SEC log predicted would hold the missing transactions. **The diagnosis in the previous log is
  confirmed.**
- The issuer universe is no longer the constraint. 32 Moody's-rated tribal entities and ~70 EMMA tribal
  issuers are now enumerated by name and ID. Discovery is done.

What the floor actually is, and it is a hard one:

**The binding constraint is retrieval, not discovery.** Every remaining lead in this window is an entity
whose existence, instrument type, and often amount are all known — and whose *date* sits inside a
document behind a paywall or a terms-of-use clause. Gun Lake's $160 million, Seminole's $395 million
incremental, Seminole's $367 million of 2010 bonds, Chukchansi's 2012 refinancing, Shingle Springs' 2013
refinancing, Cowlitz's ilani financing: six known in-window transactions, six unretrievable dates, six
rows not written.

That is a **hard floor for free-channel work**, and it is a different floor from the one the SEC log
described. The SEC log's floor was structural — tribes stopped registering, so the documents do not
exist publicly. This floor is commercial — the documents exist and are dated, but the three firms that
hold them sell access. No amount of further free scraping moves it.

Two honest consequences:
1. **2010–2017 will not be adequately covered without paid access.** A Moody's subscription (or a Fitch
   account, which is free and covers most rating actions) would convert perhaps 15–25 of the named leads
   into rows in a single session, because the docids are already in the skip file. This is now a
   procurement decision, not a research problem.
2. **The EMMA licensing question must be answered before publication, not after.** It is not merely an
   access nuisance; it governs whether EMMA-derived figures can appear in a paid Cedar Press dataset at
   all. See `SK-TD-001`.

### Where the remaining rows are, ranked

1. **Buy retrieval.** Fitch registration is free and covers most rating actions; Moody's is paid. The
   skip file already names the exact documents. Highest return per hour of anything in this project.
2. **Resolve the EMMA licence**, then work the ~70-issuer roster. This is simultaneously the completion
   of Dataset 1's 2010–2017 window and the whole of the Q4 tribal bond-finance dataset — one licence
   unlocks both, and the roster in this log is the work plan.
3. **Finish the Internet Archive CDX sweep.** 76 of 108 index pages were harvested before archive.org
   rate limiting made paging uneconomic; resuming at page 76 should add 15–20 more tribal rating actions
   at zero cost. Bounded but free.
4. **Tribal New Public Housing Authorities.** Five are Moody's-rated and eight are on EMMA. Nobody has
   touched them. They are not gaming, they are HUD-guaranteed tribal housing paper, and they are the
   clearest evidence that this dataset should not be scoped as a casino-debt dataset.
5. **Non-gaming tribal government issuance generally.** The EMMA roster's composition — water and sewer,
   health facilities, sales-tax revenue, tribal infrastructure — says the centre of gravity of tribal
   debt is governmental, not commercial. Cedar Press's framing of Dataset 1 should absorb that finding.
