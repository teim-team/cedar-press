# Federal Award Lists — retrieval log, 2026-08-05

The four bulk federal award lists that had blocked every prior session. All four were
retrieved. Nothing on the manual-download queue for these programs remains except two
IHBG-Competitive rounds and the pre-2023 national ICDBG rounds (exact URLs at the bottom).

**Outputs**
- `data/clean/deals_federal_awards_additions.csv` — **594 rows**, schema identical to
  `deals_historical_2020_2025.csv` (32 columns), Deal_IDs `FA-NTIA-*`, `FA-HUD-*`, `FA-EDA-*`,
  `FA-DOE-*`. Zero collisions against both live ledgers and all four existing additions files
  (checked programmatically: 247 existing IDs, 594 new, intersection = 0).
- `data/raw/external/federal_award_lists/` — 243 files + `_SOURCE_MANIFEST.csv`
  (138 fetched documents, 105 derived extractions; every row carries its URL and fetch date).
- `review/federal_award_lists_skipped_leads.csv` — 63 skipped items with reasons.
- `logs/34_federal_award_lists.log`

---

## Captured vs. known universe

| List | Known universe | Rows written | Coverage | Verdict |
|---|---|---|---|---|
| **NTIA TBCP** | **274 awards, ~$2.2B** (GAO-24-106541: 136 standard + 90 equitable-distribution R1 + 48 R2) | **272** | **~99%** | **Unblocked.** NTIA's own award pages and press releases fetch fine with a declared browser User-Agent |
| **HUD ONAP — IHBG Competitive** | ~130 across 5 rounds | **148** across **4 rounds** (FY2018-19, FY2020, FY2023, FY2024) | 4 of 5 rounds | **Unblocked via Wayback.** FY2021 and FY2022 award lists not located |
| **HUD ONAP — ICDBG** | ~300 | **72** written (FY2023, FY2024) + **50** parsed but sub-threshold (Alaska ONAP FFY2016-2018) | ~24% written | **Partly unblocked.** Only FY2023/FY2024 national lists and three Alaska regional lists exist as archived documents |
| **EDA Indigenous Communities** | **51 awards, $100M** (EDA fact sheet) | **51** | **100%** | **Unblocked via Wayback.** Complete round with exact per-award dates |
| **DOE Office of Indian Energy** | ~100 (brief) / **225 projects in DOE's own database** | **49** (every project with a DOE share ≥ $1M) | 49 of 49 eligible | **Unblocked.** 176 sub-$1M projects deliberately not written |

Row totals by source: NTIA 272, HUD 222, EDA 51, DOE 49. Sum of `Announced_Value_USD`
across the 590 valued rows is **$4.61B** (do not aggregate blindly — see "Double-count
hazards").

---

## What worked, per list

### 1. NTIA TBCP — the block does not exist any more

`www.ntia.gov/programs-and-initiatives/tribal-broadband-connectivity-program` 404s and
`internetforall.gov` does not resolve at all from this network, which is probably what
earlier sessions hit. But **`broadbandusa.ntia.gov` returns HTTP 200 to plain `curl` with a
declared browser User-Agent** — the sec.gov trick, applied unchanged. No CAPTCHA, no
challenge, no rate limiting.

Two document families, and the join between them is the whole trick:

1. **Awardee pages** — `/funding-programs/tribal-broadband-connectivity-round-{1,2}/award-recipients`
   index 221 Round 1 and 49 Round 2 awardees (270 total). Each links to a detail page with
   **funding amount, state, project title and purpose — and no date whatsoever.** All 270
   were scraped (`tbcp_awardee_pages.csv`); 270 of 270 carry an amount.
2. **Press releases** — the full `broadbandusa.ntia.gov/news/latest-news` feed is 328 items
   across 39 pages. 43 are TBCP award announcements. **These carry the date and, in almost
   every tranche, a table of `Applicant | Location | Type | Funding Amount | Description`.**
   That is date + recipient + amount in one retrieved document.

Result: 284 table rows parsed, 280 after dropping one duplicate fetch, **267 with an
in-document release date**, and the remaining 17 dated from the news listing page. 272 rows
written after removing the nine December-2025 equitable-distribution awards (already in the
ledger as `ND-2025-010`).

Strict exact-name coverage of NTIA's own 270-entity awardee roster by a dated press-release
row is **221 of 270** (196 of 221 Round 1, 25 of 49 Round 2); the remainder are name variants
("NANA Regional Corp., Inc." vs "NANA Regional Corporation, Inc.", "Cape Fox Corporation",
"Alaska Tribal Spectrum") that are the same awards under different spellings, not gaps.

`jsonapi` is disabled on the NTIA Drupal site, and there is no CSV/XLSX export.

### 2. HUD ONAP — Wayback CDX plus the `id_` modifier, exactly as briefed

Confirmed first that the live pages really are dead: `hud.gov/program_offices/public_indian_housing/ih/grants/icdbg`
returns HTTP 200 but the page body has been emptied by the reorg (the title is prefixed
`25red-`, HUD's redirect-stub marker) and every historical `/codetalk/onap/...` award path
404s.

CDX index queries that worked (note the query form — `url=hud.gov&matchType=domain` with a
`filter=original:` regex; combining `url=hud.gov*` with `matchType=domain` and an `fl=` list
returns an empty body):

```
http://web.archive.org/cdx/search/cdx?url=hud.gov/sites/dfiles/PIH*&output=json
  &collapse=urlkey&limit=20000&filter=statuscode:200
```

13,488 archived PIH document URLs; 215 contain `icdbg` or `ihbg`; 23 look like award lists.
Twelve were retrieved with `https://web.archive.org/web/<timestamp>id_/<url>` — **12 of 12
returned intact PDF bytes, zero corrupt snapshots.**

| Document | Awards parsed | ≥ $1M |
|---|---|---|
| `FY_2018-2019_IHBG_Comp_Awards_Corrected.pdf` | 52 | 51 |
| `HUD_IHBG_Competitive_Awards_4.12.21.pdf` (FY2020) | 24 | 24 |
| `FY23_IHBGCOMP_Awardees.pdf` | 41 | 41 |
| `FY24_IHBG-COMP_Awards.pdf` | 32 | 32 |
| `FY_23_ICDBG_Awards_and_Project_Summaries.pdf` | 39 | 36 |
| `FY2024ICDBGAwardsandProjectSummaries.pdf` | 36 | 36 |
| `2016/2017/2018_Alaska_ICDBG_Awards.pdf` | 50 | **0** |
| `DTL IHBG ARP Allocations 3.25.21.pdf` | formula round | 1 portfolio row |
| `FY-2025IHBG-Formula-Allocation-Press-Release-Awards-List.pdf` | formula round | 1 portfolio row |

**The HUD dating problem, stated plainly.** HUD publishes no award action date on any of
these lists. Three documents carry a real in-document date and those rows are High
confidence:

- FY2023 IHBG-Competitive — **July 29, 2024** printed on the document
- FY2024 IHBG-Competitive — **December 27, 2024** printed on the document
- IHBG-ARP allocations — **March 25, 2021**, the Dear Tribal Leader letter's own date

For the rest I used the **PDF's embedded CreationDate**, transcribed from the retrieved
file's metadata, and said so in capitals in `Date_Basis` ("NOT an award action date").
Those 169 rows are Medium confidence. The FY2020 list is corroborated twice — PDF
CreationDate `2021-04-12` and HUD's own file name `HUD_IHBG_Competitive_Awards_4.12.21.pdf`.

The three Alaska ONAP ICDBG lists were parsed (50 awards, FFY2016-2018) but **every award is
between $148,940 and $600,000**, so none is written. Their PDF creation dates are two years
after the fiscal year, so using them as event dates would have put FY2016 awards in 2018 —
they are logged as sub-threshold rather than mis-dated.

`FY-2025IHBG-Formula-Allocation-Press-Release-Awards-List.pdf` has 594 recipient lines
totalling **$1,119,638,884** and no date at all. It is one portfolio row (formula convention)
with `Event_Date` deliberately **blank** rather than inferred.

### 3. EDA Indigenous Communities — the single cleanest result of the run

`www.eda.gov/funding/programs/american-rescue-plan/indigenous-communities` and
`/arpa/impact` both return **HTTP 403 (Cloudflare "Just a moment...")**. But
`www.eda.gov/arpa/indigenous-communities` (the short path) returns 200, and its archived
sibling `/archives/2022/arpa/impact/` linked a file the live site hides:

**`https://www.eda.gov/archives/2022/files/arpa/impact/2022_ARPA_Award_Data.xlsx`**

780 ARPA awards, 25 columns, including **`DEC_Award_Date`** — an actual award date per row —
plus EDA funding, local match, total project cost, city/county/state, congressional district,
estimated jobs and the full project description. **51 rows carry
`Appropriation_Detail_Derived = "ARPA - Indigenous Communities Program"`, which is exactly the
51 awards / $100M the EDA fact sheet states.** The whole round, complete, with real dates.
All 51 are written; 33 are below $1M and carry `Threshold_Exception=Yes` on the RTA precedent.

The same file holds 729 more ARPA awards under the other five programs. The EDA fact sheet
says 128 grants totalling $489M across all six programs serve Indigenous communities, so
roughly **77 further Indigenous-serving ARPA awards sit in this file already downloaded**,
tagged only by program, not by Indigenous status. Identifying them is a name-match job
against `entity_master.csv`, not another retrieval.

### 4. DOE Office of Indian Energy — no list page, but a live data source behind the map

`energy.gov/indianenergy/tribal-energy-projects-database` renders its table in JavaScript.
The page embeds `<iframe src="//natlabrockies.github.io/eere-ie-projects-map/">`; the app's
source (`src/client/js/app.es6.js` on GitHub) names a **public Google Sheet**, which exports
as CSV without a key:

```
https://docs.google.com/spreadsheets/d/1PeYaVWqSWABu6kWKI3VF48_iL-YLAyFJIo9j8Hnx73Y/export?format=csv&gid=0
```

**225 projects, 2010–2022**, each with a link to an `energy.gov` project page carrying
Tribe/Awardee, DOE Grant Number, **DOE share / awardee cost share / total project cost**, and
**Project Period of Performance start and end**. All 225 pages were scraped; 223 have a DOE
amount, **49 have a DOE share ≥ $1M**, and all 49 of those have a period-of-performance start.

28 of the 49 give an exact `m/d/yyyy` start (High confidence). 21 give month and year only
("September 2017") — those use a disclosed mid-month placeholder (day 15) and are Medium
confidence, exactly the `ND-2001-001` precedent. `Date_Basis` says so on every row.

The 176 sub-$1M projects are not written. DOE's own database is materially larger than the
"~100" in the brief.

---

## Hosts that refused, and what it cost

| Host / endpoint | Result | Consequence |
|---|---|---|
| `api.usaspending.gov`, `files.usaspending.gov` | **HTTP 000 — connection closed by a network middlebox** (DNS resolves to 166.123.8.118, not USAspending's IP) | No award action dates or FAIN identifiers from USAspending. This is the single biggest remaining gap and it is a *network* block on this machine, not a site block |
| `www.gao.gov` | **HTTP 403** to every request including the direct PDF `assets/gao-24-106541.pdf` | GAO-24-106541 could not be read. Its award counts are used here only as the universe figure already supplied in the brief |
| `www.internetforall.gov` | **HTTP 000 — does not resolve** | Irrelevant in the end; broadbandusa.ntia.gov carries the same content |
| `www.eda.gov/funding/programs/...` and `/arpa/impact` | **HTTP 403 Cloudflare** | Worked around: short path `/arpa/indigenous-communities` + Wayback for the data file |
| `www.ntia.gov/programs-and-initiatives/...`, `/press-releases`, `/news` | HTTP 404 | Worked around: `broadbandusa.ntia.gov` |
| `catalog.data.gov/api/3/action/package_search` | HTTP 404 (CKAN endpoint retired) | No agency award mirrors from data.gov |
| `broadbandusa.ntia.gov/jsonapi` | Disabled | Had to page HTML instead |
| Wayback **CDX** on whole-domain queries | Intermittent **504** and truncated JSON at ~66KB | Fixed by narrowing to path prefixes and retrying with delays. Two whole-domain passes were lost to this |
| `hud.gov` live ONAP pages | 200 but **emptied stubs** (`25red-` prefix) | Confirms the brief; Wayback was the answer |

**No access control was bypassed.** The only header sent beyond a normal request was a
standard browser `User-Agent`, `Accept` and `Accept-Language`. No CAPTCHA was solved, no
login used, no identity misrepresented beyond that User-Agent.

---

## Zero-fabrication discipline — what was deliberately NOT written

63 items in `review/federal_award_lists_skipped_leads.csv`:

| Reason | Count | What |
|---|---|---|
| `below_threshold` | 54 | 50 Alaska ONAP ICDBG awards ($148,940–$600,000) + 3 ICDBG FY2023 + 1 IHBG FY2018-19 sub-$1M award in a round that is otherwise all above it |
| `already_in_ledger` | 9 | The nine December-2025 TBCP equitable-distribution awards. `ND-2025-010` already records that round as a $6.5M aggregate; entering them per-award would double count |

Plus, not written at all and stated here rather than guessed:

- **4 TBCP rows carry no `Announced_Value_USD`** (Old Harbor Native Corporation, Kawerak Inc.,
  Pueblo de Cochiti, Taos Pueblo). NTIA's 16 January 2025 "recommends for award $162 million"
  release names four applicants and gives **one aggregate figure and no per-award amounts**.
  All four names also exist on Round *1* awardee pages with Round 1 amounts —
  **$1,000,000 for Kawerak and $477,817 for Taos Pueblo — and those are different awards.**
  An early build wrongly pulled them in; the join is now restricted to the round implied by
  the release date, so a Round 1 page can never supply a Round 2 amount. The four values stay
  blank.
- **1 row has a blank `Event_Date`** (`FA-HUD-9002`, FY2025 IHBG formula): the HUD allocation
  list carries no date, so `Event_Year` is 2025 and the date field is empty.
- **176 DOE projects** below $1M.
- **~729 non-Indigenous-Communities EDA ARPA awards** in the retrieved file.

**One date discrepancy worth Elijah's eye.** `ND-2025-010` in the live ledger is dated
**2025-12-19**. The NTIA release it cites is datelined **December 23, 2025**. The live ledger
was not modified.

---

## Double-count hazards inside this file

1. **`FA-NTIA-0155`–`FA-NTIA-0198` are "Recommended for award", not awarded.** The 16 Dec 2024
   ($276M, 44 applicants) and 16 Jan 2025 ($162M, 4 applicants) releases say NTIA "has
   recommended for award … awards will be issued following budget review". `Event_Type`,
   `Status` and `Value_Type` all say so. Several of these applicants also appear on the
   TBCP Round 2 awardee pages, i.e. the same money may later appear as an obligation.
2. **HUD FY2018-19 is one combined round** covering two fiscal years; it is not two rounds.
3. **DOE `Announced_Value_USD` is the DOE share only**; `Project_Total_Value_USD` includes the
   awardee's cost share. Never sum the two.
4. **EDA `Announced_Value_USD` is the EDA share**; total project cost includes local match and,
   in a few cases, state funding.
5. The TBCP awardee pages and the press releases describe the **same** awards. `Source_2`
   links the awardee page for corroboration only — it is not a second award.

---

## Entity typing is unresolved and deliberately generic

`Native_Party_Type` is `"Tribal government or Native entity"` on the NTIA, DOE and EDA rows
and `"Tribal government, TDHE or tribal housing authority"` on the HUD rows. TBCP alone mixes
tribal governments, ANCs (Cape Fox, NANA, Doyon, Old Harbor Native Corporation, Calista,
Bethel Native Corporation), tribal consortia, tribal health boards, urban Indian
organizations and the Hawaii Department of Hawaiian Home Lands. Assigning a specific type per
row without resolving each against `entity_master.csv` would be exactly the "Cherokee Inc.
trap" the matching memo warns about. **These 594 recipient names are a large, clean,
federally published seed list for the NEID/Entity_Master fuzzy pass** — that is the natural
next step, and it should drive the typing rather than the other way round.

---

## What still needs a manual download — exact URLs

Only two things, both HUD:

1. **FY2021 and FY2022 IHBG-Competitive award lists.** Not present in the Wayback index for
   `hud.gov/sites/dfiles/PIH*`. Only the rating-factor training decks for those years are
   archived. Start here:
   - <https://www.hud.gov/program_offices/public_indian_housing/ih/codetalk/onap>
   - <https://www.hud.gov/sites/dfiles/PIH/documents/> (browse for `FY21`/`FY22 IHBG Comp`)
2. **National ICDBG award lists before FY2023.** Only FY2023 and FY2024 national lists and the
   three Alaska ONAP regional lists are archived. FY2019–FY2022 national ICDBG lists were not
   found under any Wayback path searched.

Everything else that refused is a network-level block on this machine rather than a document
that needs downloading:

3. **USAspending.** `https://api.usaspending.gov/api/v2/search/spending_by_award/` — POST from
   a network that can reach it. Assistance listings **11.554** (TBCP), **14.862** (ICDBG),
   **14.867** (IHBG), **81.087/81.214** (DOE Indian Energy), **11.307** (EDA EAA). This would
   convert every Medium-confidence HUD date in this file into a real action date and attach
   FAIN identifiers to all 594 rows.
4. **GAO-24-106541.** `https://www.gao.gov/assets/gao-24-106541.pdf` — 403 to this machine;
   opens fine in a browser.

---

## Reusable findings

- **The sec.gov User-Agent trick generalises.** It unblocked `broadbandusa.ntia.gov` and
  `www.energy.gov` outright, and `www.eda.gov` on its short paths.
- **Wayback CDX + `id_` is now proven on hud.gov and eda.gov**, 12 of 12 and 1 of 1 PDFs
  intact. Query form matters: use `url=<host>/<prefix>*` **or** `url=<host>&matchType=domain`,
  add `filter=original:.*(?i)<term>.*`, and expect 504s on whole-domain queries.
- **When a federal table renders in JavaScript, read the app, not the page.** DOE's entire
  Indian Energy project database is a public Google Sheet named in a GitHub-hosted map app.
  This pattern is worth trying on any `energy.gov`, `doi.gov` or `bia.gov` map.
- **Agency "impact map" pages hide bulk XLSX files.** EDA's whole ARPA portfolio — 780 awards
  with award dates — was one file behind a 403'd map page and one Wayback fetch away.
- **Award lists and dates usually live in different documents.** NTIA amounts are on
  undated awardee pages and NTIA dates are in press releases with no amounts for one tranche;
  HUD lists have neither. Plan for the join, and restrict it by round.

---

## Code

- `code/fetch_util.py` — curl + browser UA fetcher, writes the source manifest
- `code/parse_tbcp.py` — NTIA press releases → award table
- `code/scrape_tbcp_awardees.py` — 270 NTIA awardee detail pages
- `code/scrape_doe_indian_energy.py` — 225 DOE project pages
- `code/cdx_hud.py`, `code/cdx_eda_hud2.py`, `code/cdx_round3.py` — Wayback CDX index queries
- `code/parse_hud_awards.py` — the nine HUD award PDFs → award table
- `code/build_federal_award_rows.py` — builds the additions CSV
- `code/build_source_manifest.py` — rebuilds `_SOURCE_MANIFEST.csv`

Live ledgers, `data/spine/`, `data/clean/cedar_*` and `review/cedar_review*.html` were not
touched.
