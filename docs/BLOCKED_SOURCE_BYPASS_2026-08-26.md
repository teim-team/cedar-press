# Blocked-source bypass — 2026-08-26

*Scripts `code/211`–`code/218`. Every number here is written by a run and logged to
`logs/`; none is asserted by hand. Companion to
`docs/GAMING_UNIVERSE_REBUILD_2026-08-26.md`, whose "two regulators are blocked at the
edge" section this file **supersedes**.*

> **A 403 is a fact about ONE ROUTE, not about the DOCUMENT.**

---

## THE HEADLINE

| | before | after |
|---|---:|---:|
| New Mexico per-tribe quarterly net win — last quarter held | **2022 Q4** | **2026 Q2** |
| …new quarters recovered | 0 | **14, all footing** |
| …new tribe-quarter observations staged | 0 | **188** |
| …dollars of per-tribe Adjusted Net Win newly on disk | $0 | **$3,059,077,514** |
| NMGCB PDFs on disk | 84 | **206 + 91 monthly Quick Facts** |
| ADG PDFs on disk (live origin, not Wayback) | 12 | **81** |
| Per-property figures in a "sealed" state (NV/ND/KS) | 0 | **10 rows, 5 named casinos** |

**Neither of the two hosts recorded as blocked was blocked.** One was a User-Agent. The
other was a domain that no longer belongs to the agency.

---

## TARGET 1 — NEW MEXICO. **RECOVERED.**

### `nmgcb.org` IS NOT THE NEW MEXICO GAMING CONTROL BOARD ANY MORE

This is the finding that mattered, and it is worse than a block.

`docs/GAMING_UNIVERSE_REBUILD_2026-08-26.md` records `www.nmgcb.org` as **403 on the site
root**, typed `NOT_CHECKED`. Measured 2026-08-26 with a browser User-Agent:

```
https://www.nmgcb.org/                          HTTP 403     1,827 B
https://www.nmgcb.org/tribal-revenue-sharing/   HTTP 404    24,422 B   <-- a real page
https://nmgcb.org/tribal-revenue-sharing/       HTTP 301       521 B
```

**The root 403s and every other path serves.** And what it serves, verbatim from
`data/raw/external/gaming_official/bypass_2026-08-26/nmgcb_404_probe_2026-08-26.html`:

```html
<title>Page not found -</title>
```
> "Mejores Casinos Online · Sobre nosotros · Contacto …
>  Parece que esta página no existe. … Contacto - © 2025 nmgcb.org"

The domain lapsed and was re-registered as a **Spanish-language online-casino affiliate
site**. There is no regulator behind that 403. Anything scraped from it today would be an
advertising site wearing a state agency's old name — a *worse* outcome than the block,
because it would have looked like a success.

**The agency is at `www.gcb.nm.gov`.** HTTP 200, 254 KB, and its `robots.txt` is

```
User-agent: *
Disallow:
Sitemap: https://www.gcb.nm.gov/sitemap_index.xml
```

— everything allowed.

> **RULE EARNED.** *A persistent 403 at a root, with no other path ever tried, is as
> consistent with "the agency moved" as with "the agency is defended."* One request to a
> sub-path separates them, and the answer changes what you do next completely. Cedar's own
> `source_url` values on any `nmgcb.org` citation are now pointing at a gambling
> advertiser; the 1,072 rows already in `gaming_capacity_official.csv` are safe because
> they cite `api.realfile.rtsclients.com`, not the agency host.

### The RealFile widget API — read the client, do not guess the server

`docs/GAMING_CAPACITY_OFFICIAL_LOG.md` records four probes of the file-listing API, all
failed, and concludes *"do not re-probe the RealFile API"*:

```
GET api.realfile.rtsclients.com/GetWidgetFiles?widgetId=…   502
GET …?acc=…&wid=…                                           502
GET …?accountId=…&widgetId=…                                502
POST /GetWidgetFiles  (both param shapes)                   404 Cannot POST
```

Every one of those is against **the wrong host**. `api.realfile.rtsclients.com` serves
`PublicFiles/…` and nothing else. The real endpoint is named in the site's own JavaScript,
which is two requests away:

```
https://prod.realfile.rtsclients.com/js/rf-tables.js
https://cdn.rtsclients.com/SDKs/RealFile/JavaScript/rf_sdk.min.js

    var realFileLambdaURL = "https://klvg4oyd4j.execute-api.us-west-2.amazonaws.com/prod/";
    RFModule.getWidgetFiles = function (options, callback) { … url: realFileLambdaURL + "GetWidgetFiles" … type: "GET" }
    widgets.push({ widgetId, folderId, rootFolderId, accountGUID })
```

> **RULE EARNED.** *Four guessed spellings cost four requests and produced one wrong
> conclusion. Reading the SDK cost one request and produced the host, the path, the four
> parameter names and the HTTP verb.* When a page loads data you want, the page already
> contains the correct call. Do not reverse-engineer it from error codes.

**A note on `realfile.rtsclients.com/js/rf-tables.js`: that URL is an S3 `AccessDenied`.**
The working path is `prod.realfile.rtsclients.com`. The archived 2023 page cites the
former; the live page cites the latter.

### The control that made the new answer trustworthy

`code/214` refuses to touch a new folder until the endpoint has **reproduced a folder we
already hold**: the 2022 revenue-sharing folder must return exactly the four `fileId`s in
`nm_revsharing_files.json`. It did. Only then were the unknown GUIDs called.

### `rootFolderId` MUST MATCH THE WIDGET — an empty result that was a typo

The first sub-folder run returned `HTTP 200` and `files: []` for **every FY2023–FY2026
folder**, which reads exactly like "the folder is empty." Measured on the 2023 folder:

| widgetId | rootFolderId | result |
|---|---|---|
| year's own widget | **parent** folder | 200, `files: []` |
| year's own widget | **the year folder itself** | 200, **4 files** |
| root widget | root folder | 200, **4 files** |

`PULL_DISCIPLINE.md` already states it: *"An empty result is not evidence of absence; it
may be evidence of a typo."* Here the typo was a **mismatched pair** — each parameter
legal on its own.

### What came back

`review/nm_revshare_2023_2026_staged_2026-08-26.csv` — **188 rows, 14 tribes, 14 quarters,
2023 Q1 → 2026 Q2**, every quarter footing against its own printed total.

| | |
|---|---:|
| new quarterly news releases downloaded | **14** |
| quarters extracted | 14 |
| quarters that foot | **14 / 14** |
| …exactly | 4 |
| …within the source's own rounding | 10 |
| tribe-quarter rows | **188** |
| sum of staged Adjusted Net Win | **$3,059,077,514** |
| monthly *Quick Facts* PDFs, FY2021–FY2026, new to Cedar | **91** |
| other NMGCB PDFs recovered (annual reports, cumulative quick facts, per-tribe compacts) | 93 |

The 14 tribes: Acoma, Isleta, Jicarilla Apache, Laguna, Mescalero Apache, Navajo Nation,
Ohkay Owingeh, Pojoaque, San Felipe, Sandia, Santa Ana, Santa Clara, Taos, Tesuque.
**Jicarilla Apache Nation enters the series in 2025 Q1** — 13 tribes 2023–2024, 14 from
2025 — so a panel built on this must not treat the change as missing data.

### The footing tolerance is DERIVED, not picked

2002–2022 releases print **cents** (`Acoma $10,436,789.58`). From 2023 NMGCB prints
**whole dollars per tribe** and a total rounded from the unrounded figures. Ten of
fourteen quarters therefore miss exact equality by **$1–$2**, and all ten are correct
extractions. The tolerance used is `n_tribes / 2` — half a dollar per rounded addend,
the largest error rounding can produce.

**This cannot hide the failure it guards against.** The defect a footing check exists to
catch is `pdftotext`'s one-row column shift, which moves a figure by *millions*.
`residual_vs_printed_total` and `exact_equality` are both stored per quarter in
`review/nm_revshare_2023_2026_footing_2026-08-26.json` so the next reader can see which is
which rather than trusting the flag.

### What the rows are NOT

The measure definition is quoted onto every row, from the document itself:

> *"'Adjusted Net Win' is the amount wagered on gaming machines, less the amount paid out
> in cash and non-cash prizes won on the gaming machines, less State and Tribal Regulatory
> Fees. 'Adjusted Net Win' is not the net profit of the casino."*

So: `net_win`, **per TRIBE**, **machines only**, typed `ADJUSTED_NET_WIN_TRIBE_LEVEL` and
`applies_to = tribe`. Every row carries **two** URLs — `source_url`, the agency landing
page, and `source_file_url`, the direct RealFile address of the PDF the figure is in
(spot-checked: HTTP 200, 249,556 B). A landing page is citable; only the file URL resolves
to the document, and the file id is the only addressable handle this widget exposes. Several New Mexico tribes run more than one facility; the state does
not split them. Amended editions supersede originals and both stay on disk.

---

## TARGET 1 — ARIZONA. **HOST RECOVERED. THE SERIES DOES NOT EXIST.**

### `gaming.az.gov` was a User-Agent, and `docs/ACCESS_TECHNIQUES.md` §2 already said so

Recorded: *403 with `<title>Just a moment…</title>` — a Cloudflare interstitial.*
Measured 2026-08-26 with a browser User-Agent and an `Accept` header:

```
https://gaming.az.gov/                                     HTTP 200   89,601 B
https://gaming.az.gov/tribal-gaming/tribal-contributions   HTTP 200   78,045 B
https://gaming.az.gov/robots.txt                           HTTP 200    2,189 B
https://gaming.az.gov/sitemap.xml                          HTTP 200    3,682 B
```

`ACCESS_TECHNIQUES.md` technique 2 is *"curl with a declared User-Agent … Try this first
on any 403. It is the cheapest thing that works."* It was not tried.

**The User-Agent alone is not enough, and that is the sharper finding.** `urllib` with a
browser UA still drew 403 on **9 of 10** pages in the first run of `code/217`. `curl` with
the full navigation header set — `Sec-Fetch-Dest/Mode/Site/User`,
`Upgrade-Insecure-Requests`, `Referer`, brotli via `--compressed` — drew **200 on 10 of
10**. The discriminator is the header **shape**, not the UA string.

> **AMENDMENT TO A STANDING RULE.** *"Only 404 and 403 are facts about an object"* holds
> for an ORIGIN answering for our request. It does not reach a **bot-score challenge
> issued in front of one**. Measured on one URL, three minutes apart:
>
> ```
> GET /annual-reports/gaming?title=4   403   3,481 B   (Cloudflare interstitial)
> GET /annual-reports/gaming?title=4   200  21,914 B
> GET /annual-reports/gaming?title=4   200  21,959 B
> ```
>
> **A 403 whose body is the ~3.5 KB `Just a moment…` page is a fact about the CLIENT.**
> `code/217` retries that case with backoff and treats a 403 with any other body as final,
> which keeps the original rule intact where it applies.

`gaming.az.gov/robots.txt` sets `Crawl-delay: 10`. `code/217` honours it exactly.

### What came back: a census of the ADG report archive

`/resources/reports` carries a Drupal exposed filter, `GET /annual-reports/gaming?title=n`.
**The filter does not filter** — all nine year values return the same 49 links — but the
unfiltered list *is* the census. Plus the current-reports page and four PDFs found only
through the Wayback CDX index:

| | |
|---|---:|
| distinct PDF paths enumerated | **77** |
| downloaded | **77**, 0 refused |
| plus, found via CDX and fetched from the live origin | **4** |
| **total AZ PDFs on disk** | **81** |

Includes the complete ADG *Tribal Contributions* annual report series FY2003–FY2025, every
ADG Department annual report FY2006–FY2025, the *Annual Compact Trust Fund Report FY2025*
(a document class Cedar did not hold), and —

**`Gaming_Status_Report_08012026.pdf`**, the *Status of Tribal Gaming in Arizona* as of
**2026-08-01**, one month newer than Cedar's 2026-07-01 edition. That is the per-casino
Class III / Class II device panel `code/97_extract_az_status_archive.py` reads, and it is
the only per-property device count published by any regulator in the country.

`cdx_az_all_pdf.json` holds **1,755** archived AZ PDF captures, **141** of them matching
revenue/contribution/status terms, including **the 2015 `currentstatus*.pdf` editions**
that `docs/GAMING_CAPACITY_OFFICIAL_LOG.md` calls *"the remaining prize."* They are
enumerated here and **not yet fetched** — that is the named next job, not a claim.

### Per-tribe contributions: `NOT_PUBLISHED_BY_THIS_BODY`

This is a different verdict from `NOT_FOUND`, and the distinction is the point.

**The data exists.** ADG's live page, verbatim:

> *"Each tribe reports its Class III Net Win to ADG on a monthly and quarterly basis. ADG
> audits the tribes' gaming revenues and contributions."*

**The statute asks only for totals.** A.R.S. § 5-601.02(H)(1), quoted verbatim inside
ADG's own letters:

> *"a statement of **aggregate** gross gaming revenue for all Indian tribes, **aggregate**
> revenues deposited in the Arizona Benefits Fund, including interest thereon,
> expenditures made from the Arizona Benefits Fund, and **aggregate** amounts contributed
> by all Indian tribes to cities, towns, and counties"*

**And every edition reports exactly those aggregates and no tribe split.** Checked across
five editions spanning 21 years and three document classes — this is not one entity's
behaviour generalised into a rule about a source, which is the error
`START_HERE.md` records at the tribal Single Audit dead end:

| document | route | result |
|---|---|---|
| FY2004 TC report (`Y4FR`) | text layer | 4 aggregates, no tribe split |
| FY2013 quarterly release (`AzTribalGamingRevenue.pdf`) | live origin | one statewide figure, fund split only |
| FY2018 TC report | **OCR'd this pass** (rapidocr, no text layer) | 4 aggregates, no tribe split |
| FY2025 TC report | text layer | 4 aggregates, no tribe split |
| **`APPENDIX I — TRIBAL CONTRIBUTIONS.pdf`** | found via CDX, fetched live | the compact's **computation and auditing methodology**. Defines the sliding scale. Contains no data. |
| all 77 archive PDFs | automated scan for a tribe name on a line with a dollar figure | **zero per-tribe contribution tables** |

The scan's only hits were `Yavapai Downs` (a **racetrack**, in the racing tables) and a
sentence fragment — a reminder that a tribe-name match is a hypothesis.

**Where an Arizona per-tribe figure could still be found**, named and not attempted:

1. **The 12%.** *"12 percent is distributed by the tribe to the cities, towns and counties
   of their choosing."* Each recipient city, town and county books that receipt and names
   the tribe in its ACFR. Aggregate FY2025: **$21,822,667**. This is a per-recipient crawl,
   not a single document.
2. **The sliding scale is invertible for the flat-rate tribes.** ADG: contributions are on
   a sliding scale *"For Gila River, Salt River, Ak-Chin, Tohono O'odham, or Pascua
   Yaqui"* — the remaining tribes pay a flat rate, so a per-tribe **contribution** would
   yield Class III Net Win exactly, the way Michigan's 2% does for its four 1999-compact
   tribes. The missing half is still the contribution.
3. **AZ tribal Single Audits.** Swept this pass across the 27 Arizona reporting packages on
   disk: **zero** carry a casino money line. `NOT_FOUND_IN_THIS_CORPUS`, not `NOT_FOUND` —
   Arizona's largest gaming tribes are mostly `is_public = false`.

---

## TARGET 2 — NV / ND / KS. **THE SEAL DOES NOT REACH THE FEDERAL AUDIT.**

Zero network calls. The 340 accepted Single Audit reporting packages were already on disk
as text; the 2026-08-12 sweep that produced `fac_audit_gaming_disclosures.csv` was aimed at
machine **participation arrangements** and typed only 25 of its 1,521 rows. It was never
looking for per-property money.

`code/212` swept the 17 sealed-state packages and staged **72 candidate quotes**;
`code/218` typed **10 rows by hand**, because the measure differs sentence by sentence and
a regex that guessed it would produce exactly the defect this project keeps catching — a
figure that is well-sourced and mislabelled.

`review/sealed_state_typed_rows_2026-08-26.csv` — **5 named casinos, 2 states**:

| state | property | measure | value | FY | seal it bypasses |
|---|---|---|---:|---|---|
| KS | Sac and Fox Casino | `CASINO_ENTERPRISE_FUND_REVENUE` | $15,995,512 | 2016 | KLRD / KS State Gaming Agency publish a roster only |
| KS | Sac and Fox Casino | ” | $15,478,290 | 2017 | ” |
| KS | Sac and Fox Casino | ” | $16,359,772 | 2018 | ” |
| KS | Golden Eagle Casino | `CASINO_PAYABLE_TO_TRIBE` | $34,481 | 2021 | ” |
| KS | Golden Eagle Casino | ” | $45,460 | 2022 | ” |
| ND | Sky Dancer Casino and Resort | `CASINO_DISTRIBUTION_TO_TRIBE` | $644,999 | 2020 | ND AG gaming division publishes nothing per tribe |
| ND | Grand Treasure Casino | ” | $6,028,837 | 2020 | ” |
| ND | Sky Dancer Casino and Resort | ” | $963,745 | 2021 | ” |
| ND | Grand Treasure Casino | ” | $3,661,712 | 2021 | ” |
| ND | Prairie Knights Casino | `CASINO_PAYABLE_TO_TRIBE` | $720,943 | 2023 | ” |

Standing Rock FY2023, verbatim:

> *"At September 30, 2023, Prairie Knights Casino, which is the enterprise fund of the
> Standing Rock Sioux Tribe, owed the Department $720,943 for the gaming revenue
> distribution. The Department subsequently received it in October 2023."*

Sac and Fox FY2018, verbatim:

> *"Business-type activities for the Casino had program revenues of $16,359,772 compared
> with expenses of $14,134,240 for a net operating income of $2,225,532; compared to 2017
> with program revenues of $15,478,290 and expenses totaling $13,551,151 for a net
> operating income of $1,927,139 in the previous year."*

**THREE MEASURES, AND THEY ARE NOT INTERCHANGEABLE.** Every row carries a
`not_a_substitute_for` column saying so in the file itself:

- `CASINO_ENTERPRISE_FUND_REVENUE` — the casino fund's **total program revenues**. Not
  gaming revenue: it includes food, beverage, retail and hotel.
- `CASINO_DISTRIBUTION_TO_TRIBE` — a transfer, per casino. **Not a floor for revenue and
  not a ceiling.** A casino can distribute out of reserves in a bad year and retain
  earnings in a good one. It proves a per-property flow exists; it does not measure the
  property.
- `CASINO_PAYABLE_TO_TRIBE` — a **stock**, not a flow. Never summed with either.

**FY2016 is a prior-year comparative restated inside the FY2017 report**, not its own
filing, and is marked as such — `ACCESS_TECHNIQUES.md` §6 working in a new place.

### Nevada: `NOT_FOUND_IN_THIS_CORPUS`, and the regulator is the wrong body anyway

Only **4** of the 340 packages are Nevada — Washoe Housing Authority and three years of
Pyramid Lake Jr/Sr High School. Neither is a gaming tribe's government; neither names a
casino. But **216 Nevada tribal filings exist in `fac_tribal_single_audits.csv` and 41 are
`is_public = 1`**, so the route is open and simply unmined. Separately,
`docs/GAMING_CAPACITY_OFFICIAL_LOG.md` records that NGCB reports cover *"nonrestricted
gaming licensees"*, which **excludes IGRA operations** — so in Nevada the NGC-31 seal is
not even the binding constraint. Wrong agency, as that log already said.

---

## ROUTES TRIED THAT DID NOT PAY, AND WHY

| route | verdict | detail |
|---|---|---|
| **CourtListener / RECAP** | **`ROBOTS_FORBIDDEN`** | `https://www.courtlistener.com/robots.txt` ends `User-agent: * / Disallow: /`, and carries an explicit AI-agent block listing `ClaudeBot`, `Claude-User`, `Claude-SearchBot`, `GPTBot` and others under `Disallow: /`. **Not attempted.** Their own header says *"If you would like to crawl CourtListener, please contact us. We also have an extensive REST API and provide bulk data"* — the sanctioned routes are an authenticated API token and the bulk dumps, both free, both needing the owner to create an account. That is a decision for the owner, not a bypass. |
| **MSRB EMMA** | **`ROBOTS_FORBIDDEN`** | Not attempted, per standing instruction. Bond official statements mirrored outside EMMA remain a live route and were not reached this pass. |
| **Federal Register corpus on disk** | **`NOT_FOUND` (for figures)** | 451 shards, **322,964 documents**, **1,097** with `gaming compact` in the title, including *"Tribal-State Class III Gaming Compacts Taking Effect in the State of New Mexico"*. The corpus stores `title`/`abstract`/`agencies`/URLs — **no full text** — and FR compact-approval notices are one-paragraph effectiveness announcements that carry no revenue schedule. Checked on disk first, zero network calls. |
| **Wayback CDX, domain-wide with `collapse=digest`** | **`DOES_NOT_RETURN`** | A first page for `gaming.az.gov` was still in flight after **26 minutes** and was killed. The same query with `collapse=urlkey` answers in **27 seconds**. Digest collapse de-duplicates by CONTENT across a whole host — a far more expensive scan than collapsing adjacent urlkeys. `code/211` records this; `code/213` supersedes it with targeted queries. |
| **Wayback CDX for `nmgcb.org/tribal-revenue-sharing*`** | **0 rows** | The revenue-sharing page was never archived under that path. Irrelevant in the end — the live agency host served it. |
| **`api.realfile.rtsclients.com` widget API** | **`WRONG_HOST` (was recorded as 502)** | See above. The 502s were real and were about a host that does not serve that API. |
| **`realfile.rtsclients.com/js/rf-tables.js`** | **S3 `AccessDenied`** | The archived page's script URL is stale. `prod.realfile.rtsclients.com/js/rf-tables.js` serves 200. |
| **AZ Single Audits for a per-tribe contribution** | **`NOT_FOUND_IN_THIS_CORPUS`** | 27 Arizona packages on disk, zero casino money lines. |

---

## WHAT IS GENUINELY UNAVAILABLE vs UNAVAILABLE-BY-THE-OBVIOUS-ROUTE

**Unavailable by the obvious route only — now recovered:**
New Mexico 2023–2026 per-tribe net win · the NMGCB monthly Quick Facts series · the entire
ADG report archive · the 2026-08-01 Arizona per-casino device panel · per-property casino
money in Kansas and North Dakota.

**Genuinely unavailable from the body that holds it:**
**Arizona per-tribe contributions.** ADG measures them monthly and quarterly, audits them,
and publishes only four statutory aggregates. Five editions across 21 years and three
document classes all agree. This is a publication choice under a statute that asks for
totals — `NOT_PUBLISHED_BY_THIS_BODY`, which is neither `NOT_FOUND` nor `NOT_CHECKED`, and
the named alternate routes (the 12% in municipal ACFRs; inverting the flat rate for the
non-sliding-scale tribes) are per-recipient work, not a single missing document.

**Off-limits by rule, not by capability:** CourtListener/RECAP and MSRB EMMA. Both hold
material that would answer parts of Target 2. Neither was touched.

---

## STAGED, NOT MERGED

Every output is in `review/`. **Nothing was written into a shared gaming table** —
`gaming_capacity_official.csv`, `state_gaming_observations.csv`,
`gaming_facility_metrics.csv` and `gaming_facilities.csv` are all untouched, per the
2026-08-26 concurrency rules, because other agents are live.

```
review/nm_revshare_2023_2026_staged_2026-08-26.csv            188 rows, 14 tribes, 14 quarters
review/nm_revshare_2023_2026_footing_2026-08-26.json          per-quarter footing evidence
review/sealed_state_typed_rows_2026-08-26.csv                  10 typed rows, 5 properties
review/sealed_state_property_figures_2026-08-26.csv             72 candidate quotes
review/sealed_state_audit_sweep_2026-08-26.json                 sweep provenance, 0 network calls

data/raw/external/gaming_official/nm_tribal_revenue_sharing/   206 PDFs (was 84)
data/raw/external/gaming_official/bypass_2026-08-26/
    nm_quick_facts/                                             91 PDFs, new series
    az_pdfs/                                                    81 PDFs
    az_ocr/FY2018_TC_report.txt                                 rapidocr, 3 pages
    cdx_*.json                                        3,633 archived captures enumerated
    gcb_*.html, nmgcb_404_probe_2026-08-26.html       the evidence for the domain finding
    rf-tables.js, rf_sdk.min.js                       the SDK that named the endpoint
    _nm_recovery_state.json, _nm_quarters_state.json, _az_archive_state.json,
    _cdx_targeted_state.json
```

### Merge path, when a merger is free to run

1. `review/nm_revshare_2023_2026_staged_2026-08-26.csv` → `gaming_capacity_official.csv`.
   It already holds 1,072 NM `net_win` rows on the identical measure. **Resolve
   `tribe_name_as_published` through the spine, not by string** — and note the **San Juan
   collision** recorded in `AGENTS.md` and `docs/REVENUE_BOUNDS_LOG.md`: NMGCB's *San Juan*
   is Ohkay Owingeh in **New Mexico**, while the spine's `San Juan` is the San Juan
   Southern Paiute Tribe of **Arizona**. The 2023+ releases write `Ohkay Owingeh`, which
   avoids it — do not "helpfully" alias it back.
2. Check `mtime` on the target and any `.bak_*_pre<script>` beside it first. An in-place
   enricher runs **last**.
3. `py -3 code/62_no_regression_check.py` after.

---

## NEXT, IN VALUE ORDER

1. **Extract the 91 NMGCB monthly Quick Facts** (FY2021–FY2026). A **monthly** series for
   money Cedar currently holds quarterly, and it is already on disk. *Caution: `code/215`'s
   `^FY ?\d{4}$` folder filter also matched three board-**minutes** folders named `FY2023`
   / `FY2025`; 30 of the 91 files are meeting minutes, not Quick Facts. Filter on the file
   name (`January.pdf` … `FY26 Quick Facts April.pdf`), not the folder.*
2. **Fetch the 2015 `currentstatus*.pdf` Arizona editions** now enumerated in
   `cdx_az_all_pdf.json` — per-casino device counts eight years inside the vendor window,
   named as the remaining prize by the capacity log.
3. **Extract `Gaming_Status_Report_08012026.pdf`** with `code/97`'s positional reader (the
   `-layout` output shows the same one-row column shift; `code/97` already handles it).
4. **Mine the other 45 Nevada public tribal Single Audits** for per-property figures. The
   route is proven in Kansas and North Dakota; Nevada is unmined, not closed.
5. **The Arizona 12%.** Aggregate FY2025 $21,822,667, distributed by each tribe to cities,
   towns and counties of its choosing, and booked by each recipient by name.
6. **Ask the owner for a free CourtListener API token**, which converts a
   `ROBOTS_FORBIDDEN` into a sanctioned route.

---

## AMENDMENT 2026-08-26, late — item 6 of "NEXT, IN VALUE ORDER" IS DONE

> *"6. **Ask the owner for a free CourtListener API token**, which converts a
> `ROBOTS_FORBIDDEN` into a sanctioned route."*

**The owner supplied one. It is verified and it was spent.** Recorded here so the
next reader does not re-ask, and so the `ROBOTS_FORBIDDEN` verdict above is not
read as still binding on the whole source.

**The verdict above is CORRECT AND STILL STANDS — for scraping.**
`https://www.courtlistener.com/robots.txt` still ends `User-agent: * /
Disallow: /` and still names `ClaudeBot`, `Claude-User` and `Claude-SearchBot`.
**The HTML site was not touched.** What the token changes is that the REST API —
the route their own robots.txt header points at (*"We also have an extensive
REST API and provide bulk data"*) — is now available and is the sanctioned one.

    ROBOTS_FORBIDDEN   the www HTML site          <- unchanged, do not scrape
    SANCTIONED         api/rest/v4 with a token   <- new

### The rate limit is the design, not a detail

**5 requests/minute, 50/hour, 125/day** on the free authenticated tier. That is
about a hundred QUESTIONS a day, so RECAP is a **targeted adjudication tool and
never a sweep**. Scripts `code/366`–`code/370` meter against a shared ledger at
`data/raw/external/courtlistener_2026-08-26/_request_ledger.json`, one entry per
request sent, with the token redacted out of every logged URL.

**The hourly cap is a ROLLING 60-minute window, not a clock hour.** 49 requests
sent between 00:16Z and 00:34Z freed slots only from 01:16Z onward, a few at a
time. A single pass after a fixed sleep spends eight requests and leaves seventy
unspent; `code/369_courtlistener_budget_drain.sh` walks the window instead.

### Two traps this cost, both worth the price

1. **`party_name` is TOKENISED, not phrase-matched.** It is the right filter —
   it aims the request at the party array instead of at full document text, and
   it lifted `Manu Kai` from 7 hits to 26 — but `party_name=Manu Kai` returns
   **`Lazetta Kay Manus`**, **`Milton Britt Manues and Marilyn Kay Manues`** and
   **`Kirk Edward Mc Manus and Leslie Kay Mc Manus`**. That is the Torres
   Martinez surname trap from `code/221`, arriving in a new field. **Re-verify
   every hit locally against the party array; the filter narrows, it does not
   adjudicate.**
2. **A control must be run per CODE PATH, not per source.** `code/219`'s
   `CONTROL_ABSENT` was run against `q=`. A filter is a different code path and
   inherits none of that evidence, so `party_name=Kwithluk Sentinel Holdings`
   was run as its own control. **Both returned 0**, and that is what makes the
   positives mean anything.

### And the standing rule that paid for itself twice in one session

**A 500 is not a fact about the object.** `party_name=TC&S/F-W` returned
**HTTP 500** — a $160M firm that would have been written off as absent if the
500 had been read the way a 404 is read.

