# Gaming — the source surface

*Workstream M, 2026-09-01. Companion to `docs/datasets/gaming.md` (what the
dataset IS) and `docs/GAMING_SOURCE_AUDIT_2026-08-26.md` (why what we built was
not shipping). **This file answers a different question: what EXISTS that we
could hold, what we actually hold, over what period, and what is left.***

**Read this table before pulling anything gaming.** It exists so the next
session does not re-derive it. Every figure below was measured against the
files on disk or against a live probe on the date stated — none of it is read
out of an older document.

---

## THE ONE-PARAGRAPH ANSWER

Cedar's gaming collection is **53 clean tables** built from **20 raw source
families**, and against its own sources it is in far better shape than the
"we're missing stuff" instinct suggests: NIGC ordinances, declination letters
and GGR-by-region are all **complete to the earliest year the agency
publishes**; CA payments, MI/CT/AZ digital and FL are current to within two
months of what their regulators have released; and Connecticut holds every
casino-month back to 1993-01 — its eight-month lag is **the source's, re-proved
live on 2026-09-01**. The three real problems are different from each other and
none of them is "we forgot to collect it":

1. **Four whole NIGC families were never collected.** Nobody had enumerated the
   agency's document surface. It is **72 categories / 4,071 documents**, and
   Cedar held five of the 72. Two of the missing four — Indian lands opinions
   and game classification opinions — are **fully structured index tables
   reaching back to 1997 and 1992**, and a third, management-contract
   approvals, was already **named as a hole in our own build log**
   (`GAMING_TEMPORAL_BUILD_LOG.md` §10.6). **All four were fetched this pass.**
2. **In two states the RAW CORPUS IS AHEAD OF THE CLEAN TABLE.** New Mexico's
   FY2023–FY2026 per-tribe net win and California's 2024Q4 / 2026Q1 / 2026Q2
   RSTF reports are **on disk and not in `data/clean/`**. Those are parse and
   promotion jobs, not pulls. Diagnosing them as coverage gaps and re-fetching
   would have been the expensive wrong move.
3. **Two source families are genuinely absent and neither is cheap**: state
   regulator *licensee* lists (Cedar's `gaming_vendor_tribal_licenses` is 100%
   SEC-filing-derived, zero regulator rows), and per-property operator
   financials, which for most of the country do not exist in public at all.

---

## PART 1 — THE COVERAGE TABLE

`earliest available` is the earliest the SOURCE publishes, not the earliest
that could theoretically exist. Where a boundary is real — IGRA is 1988, NIGC
began approving ordinances in 1993, a compact began in 1993 — the row reads
**COMPLETE**, and that is a finding, not a gap.

### 1A. NIGC — www.nigc.gov

| source | what it gives | held | earliest avail | earliest held | latest avail | latest held | verdict |
|---|---|---|---|---|---|---|---|
| GGR by region (annual) | region × FY gross gaming revenue, operation counts | `nigc_regional_ggr` 198 | FY2001 | FY2001 | FY2025 | FY2025 | **COMPLETE.** FY2026 is not published — NIGC's FY ends 30 Sep 2026 and the report follows ~10 months later. Nothing to fetch until mid-2027. |
| Gaming ordinances & amendments | approval date, type, tribe, full PDF | `gaming_ordinances` 1,155 + `gaming_ordinance_ocr` 263 | 1993 | 1993 | rolling | 2026-08-07 index pull | **COMPLETE to the last index pull.** 1,155 instrument rows = NIGC's whole index; 1,151 PDFs retrieved. 264 image-only scans remain an OCR backlog, not an absence. Refresh due (index last read 2026-08-07). |
| Declination letters | is-this-a-management-contract opinions | `nigc_declination_letters` 327 | **2013** | 2013 | 2026 | 2026 | **COMPLETE.** NIGC publishes this family from 2013 only; 327 held = 327 on the index. The pre-2013 absence is the agency's, not ours. |
| Gaming operations roster / map | the operating universe, region assignment | `nigc_region_assignments` 2,438 · `gaming_nigc_roster_link` 453 | snapshot only | 2026-08-06 | current | 2026-08-26 | **CURRENT.** No historical roster is published; only snapshots and Wayback. `gaming_property_universe_events` (10) is the Wayback-derived change record. |
| **Indian lands opinions** | tribe × parcel × legal theory × **theory accepted Y/N** × date | **NEW THIS PASS** — 102 rows | **1997-08-12** | **1997-08-12** | 2026-05-18 | **2026-05-18** | **CLOSED THIS PASS, full horizon.** |
| **Game classification opinions** | game × Class II/III × bingo / cards / pull-tabs / internet flags × date | **NEW THIS PASS** — 122 rows | **1992-09-14** | **1992-09-14** | 2024-04-26 | **2024-04-26** | **CLOSED THIS PASS, full horizon.** Predates every other gaming series Cedar holds. |
| **Enforcement actions** | NOVs, settlement agreements, civil fine assessments, closure orders | **NEW THIS PASS** — 362 rows / 362 documents | **1995** (`action_code_year` 95) | **1995** | 2026 | **2026** | **CLOSED THIS PASS, full horizon.** 146 NOV, 99 SA, 17 CFA, 10 CO, 1 TCO, 1 NDO. |
| **Approved management contracts** | Chair-approved management contracts, by tribe | **NEW THIS PASS** — 68 rows, **55 tribes** | current roster only (NIGC posts no retired contracts) | same | current | current | **CLOSED THIS PASS.** This is `GAMING_TEMPORAL_BUILD_LOG.md` §10.6's named hole — `trace_nigc_management_contract` was 0 on all 774 property rows and read `not_held_by_cedar_press_this_session`. |
| The other 64 wpdm categories | annual reports, commission final decisions, self-regulation certificates, bulletins, MICS alternate standards, fee-rate notices, tribal consultation transcripts, FOIA logs… | **index only, this pass** | varies | — | current | — | **ENUMERATED, NOT FETCHED.** Part 2 lists them with counts so the next session picks by value, not by memory. |

### 1B. State commissions and compacts

| state | what the framework forces into existence | held | earliest avail | earliest held | latest avail | latest held | verdict |
|---|---|---|---|---|---|---|---|
| **CT** | monthly per-casino slot win, handle, payment to state | `gaming_capacity_official` 3,100 (+ `gaming_facility_metrics`, licensed table) | 1993-01 | **1993-01** | **2025-12** | **2025-12** | **COMPLETE — and the residual gap is the SOURCE's.** Re-probed live 2026-09-01: `data.ct.gov/resource/i6ts-ib7c` reports `min 1993-01-31, max 2025-12-31, count 748`. Cedar holds every casino-month it serves. **`REFRESH_CADENCE.md`'s "238 days behind" is CT's lag, not ours.** |
| **CA** | RSTF + SDF quarterly distributions, tribe-identified, including non-gaming tribes | `ca_gaming_payments` 40,164 · `ca_gaming_facilities_official` 245 | 2000-07 | **2000-07** | 2026-06-30 (99th report) | 2026-06-30 | **HOLES, AND THEY ARE PARSE HOLES.** See 1E. |
| **NM** | quarterly per-tribe Adjusted Net Win | `gaming_capacity_official` 1,090 (`net_win` 1,072) | FY1999 | **FY2001** | **2026 Q2** | **FY2022 in `clean/`** | **RAW IS AHEAD OF CLEAN.** FY2023–2026Q2 is extracted, footing-checked and sitting in `review/nm_revshare_2023_2026_staged_2026-08-26.csv` (**188 rows**). Promotion, not a pull. |
| **OK** | annual exclusivity-fee payments per compacted tribe | `gaming_capacity_official` 680 (`payment_to_state` 624) | FY2005/06 (compacts effective 2005) | **FY2010** | FY2025 | FY2025 | **HISTORICAL TAIL OPEN, FY2006–FY2009.** OMES's live reports page lists FY2014 forward only (`GameCompAnnReport14` is the oldest link); FY2010–13 came from elsewhere. The tail is a **Wayback CDX** job, not a live fetch. |
| **AZ** | per-casino device/table counts; **statewide aggregate GGR only, by statute** | `gaming_capacity_official` 463 | 1992 | **1992** | 2026 | **2026** | **COMPLETE for what AZ publishes.** A.R.S. § 5-601.02(H)(1) *requires* aggregation — per-tribe revenue does not exist, it is not withheld from us. Note `gaming.az.gov` 403s an automated client; the archive route is `code/217`. |
| **WA** | per-tribe transferable machine allocation **and** a transfer ledger | `wa_machine_allocations` 75 · `wa_machine_transfers` **0 by design** | 1991 | 1991 (capacity) / 2026 (allocations) | current | 2026 | **ALLOCATIONS CURRENT, TRANSFER LEDGER NEVER OBTAINED.** `STATE_GAMING_FRAMEWORKS.md` establishes WA's Appendix D inter-tribal transfer market. Each transfer is a **Native-to-Native commercial event** that federal data cannot see. `wa_machine_transfers.csv` is 0 rows and empty *by design* pending the source. **Highest-value unfetched state item in this file.** |
| **WI** | per-casino devices/tables; per-tribe lump-sum payments; statewide net win | `state_gaming_observations` 458 | 1992 (net win) / 2013 (per-casino) | 1992 / 2013 | 2025 | 2025 | **COMPLETE for what WI publishes.** Per-property revenue is **prohibited by compact confidentiality clauses**, quoted in `STATE_GAMING_PULL_LOG.md`. Withheld ≠ never collected. |
| **FL** | Seminole revenue-share payments and the compact schedule | `fl_gaming_payments` 9,756 | FY2008 | **FY2008** | FY2031 (forward schedule) | FY2031 | **CURRENT.** Rows past 2026 are compact *schedule* rows, not observations — never read them as receipts. |
| **MI** | per-tribe payments to state and local government; iGaming per operator | `gaming_capacity_official` 200 · `digital_gaming_revenue` | 1993 | 1993 | 2026-06 | 2026-06 | **CURRENT to within 2 months.** MGCB publishes monthly ~3 weeks after month end, so Jul/Aug 2026 are the only open months. |
| **NY** | per-tribe payments — **2019 edition only** | `state_gaming_observations` 11 | 2019 | 2019 | 2019 | 2019 | **COMPLETE.** Every other NYSGC edition publishes the compact roster and nothing numeric. |
| **MN · ND · SD · CO · RI · MS · NV · KS · LA · IA · IN · NE** | — | `state_gaming_observations` 1–5 rows each | — | — | — | — | **STRUCTURALLY GENERATES NOTHING, or HELD-AND-SEALED.** Fifteen states were worked to a documented verdict in `STATE_GAMING_PULL_LOG.md` with the statute or the compact clause quoted. **`never_collected` and `held_by_state_but_sealed` are different facts and the table carries the distinction.** Do not re-work these. |
| **ID · TX · AL · AK · MO · OR · MT · NC** | — | facilities only, no regulator pull | — | — | — | — | **NEVER WORKED.** 13 ID + 7 TX + 3 AL + 3 AK + 1 MO facilities. OR (16), MT (43) and NC (5) have capacity rows but those come from **BIA compact PDFs**, not from a state regulator. See Part 4 for the ranking. |

### 1C. Compacts and federal decisions

| source | what it gives | held | earliest avail | earliest held | latest | verdict |
|---|---|---|---|---|---|---|
| Class III compacts and amendments (BIA OIG + FR) | parties, dates, term, scope, machine caps, revenue-share terms | `compacts` 707 (28 states) · `compact_terms` 1,311 · `compact_structured_terms` 2,887 · `compact_versions` 1,158 · `compact_required_reports` 4,121 | 1989–91 (first compacts under IGRA 1988) | **1990** | 2026 | **COMPLETE.** The 1988–89 window is real: IGRA passed 1988-10-17 and the first compacts date from 1989–91. |
| BIA Gaming Land Decisions | 138 fee-to-trust / §20 determinations with status and documents | `gaming_land_decisions` 138 · `gaming_decision_events` 265 | 1990 | **1990** | 2026 | **COMPLETE against the index — but BIA states its own list is NOT exhaustive.** That is the source's caveat, and it must ship with the data. |
| Federal Register gaming actions | compact approvals, Secretarial procedures, land-into-trust, gaming eligibility | held in the **federal-register** collection: 1,257 gaming-mentioning rows in `federal_actions` | 1994 (FR API full text) | **1994** | 2026 | **COMPLETE against the API.** Owned by another workstream; joinable, not duplicated here. |
| Gaming NEPA (EA/EIS/FONSI/ROD) | proposed capacity, modelled economics, mitigation agreements | `gaming_project_facilities` 19 · `gaming_projections` 116 · `gaming_mitigation_agreements` 24 | 1987 (EPA EIS db) | 1992 (mitigation) | 2024 | **PILOT ONLY.** 25 documents against a 138-decision seed list. The development layer `GAMING_DATASET_PLAN.md` describes is ~15% built. Largest *unbuilt* thing in the gaming dataset. |

### 1D. Company, audit and labour seams

| source | what it gives | held | period held | verdict |
|---|---|---|---|---|
| SEC EDGAR — vendor / manufacturer / bond filings | device counts, licence disclosures, capacity windows, financing | `gaming_device_observations` 1,326 · `gaming_manufacturer_facts` 62 · `gaming_vendor_tribal_licenses` 740 · `gaming_financing_events` 293 | 1990–2026 (devices) / 2001–2026 (licences) | **CURRENT.** Note what `gaming_vendor_tribal_licenses` IS: 100% **SEC-filing-derived** — the vendor's own disclosure that a tribal regulator licensed it. **Zero rows come from a state regulator's licensee list.** |
| Federal Audit Clearinghouse single audits | gaming enterprise funds inside tribal single audits | `fac_audit_gaming_disclosures` 1,521 · `fac_audit_sefa_gaming_programs` 1 | 2016–2026 | **HISTORICAL TAIL OPEN.** FAC's Census-era bulk archive reaches **FY1998**; Cedar starts 2016. `PULL_DISCIPLINE.md` Tier 3 already names this route. |
| OSHA ITA 300A + Census LODES | establishment-level injury filings and workplace jobs | `gaming_employment_observations` 3,246 | 2008–2026 (OSHA CY2016–2025) | **CURRENT to source.** 711 further OSHA establishments (1,879 filings) staged in `review/`, unadjudicated. |
| DOL Form 5500 (retirement) | plan sponsor, active participants — a **headcount** series | **staged, not merged** — `data/staging/gaming_employment_form5500_staged.csv` 2,046 rows, 140 tribes | 2009–2025 | **PROMOTION OWED.** Two rulings block it (a new `MeasurementType`; whether the employment table admits tribe-level rows with no `facility_id`). |
| Operator / tribal-enterprise websites | property counts, amenities, hotel keys, machine counts, loyalty tiers, careers | `gaming_property_site_observations` 262 · `gaming_game_finder_observations` 6,851 · `gaming_property_labor_demand` 43 · `loyalty_programs` 18 · `loyalty_program_property` 48 | snapshot 2026 | **SNAPSHOT ONLY, BY NATURE.** 1,749 pages / 144 hosts crawled. 281 open properties never crawled; 959 further rows re-mined 2026-08-26 and staged. A website has no history except Wayback. |

### 1E. WHERE THE RAW CORPUS IS AHEAD OF THE CLEAN TABLE

**These are not acquisition gaps and must not be re-fetched.** Both were found
by comparing `data/raw/` against `data/clean/` rather than by reading a build
log, which is the only way this class of defect surfaces.

| what | on disk | in `data/clean/` | the actual job |
|---|---|---|---|
| **NM per-tribe net win FY2023 – 2026Q2** | 14 quarterly news releases, extracted and **footed against the source's own printed total, 14/14 pass** (`code/216`) | absent — `gaming_capacity_official` NM stops at **FY2022** | promote `review/nm_revshare_2023_2026_staged_2026-08-26.csv`, **188 rows** |
| **CA RSTF 93rd report, quarter ending 2024-12-31** | `rstfi__2024__13_RSTF_Distrib_93rd_CommStaffReport-12-31-24.pdf`, **37,974 characters of extractable text** | `period_end = 2024-12-31` **has zero rows** | a parse defect in `code/103`. The file is fine. |
| **CA RSTF 98th report, quarter ending 2026-03-31** | `rstfi__2026__...98th...-3-31-26.pdf`, **0 characters — image-only** | `period_end = 2026-03-31` **has zero rows** | **OCR**, not a pull. `code/122`/`150` already do this for ordinance scans. |
| **CA RSTF 95th / 97th / 99th** (2025-03, 2025-12, 2026-06) | on disk | 112 / 110 / 167 rows against a ~400-row norm | partial parses; same defect family |

Measured 2026-09-01. **`REFRESH_CADENCE.md` records "CA gaming is missing
2026-03 entirely" as a lag. It is not a lag. The document is on disk and it is
a scan.**

### 1F. THE GRAIN OF `gaming_facilities.csv`, STATED

**Grain: one row per gaming FACILITY.** 787 rows, **786 facilities**, and the
difference is not a rounding error — it is a named exclusion.

> **`facility_id = VP-0109` ("Konkow Valley Band - no casino", Oroville CA) is
> NOT an instance of the grain.** It is a row asserting the ABSENCE of a
> facility, inherited from the votingpatterns tribe roster. Its own fields say
> so: `n_capacity_observations = 0`, every `*_value_basis` reads
> `no_capacity_source_for_this_facility`, and `open_date_absent_reason` reads
> verbatim *"not a gaming facility … the tribe operates no casino; there is no
> opening to date"*.
>
> **Exclude VP-0109 from every facility count.** Do not delete it — a tribe
> with no casino is a real negative, and it is Cedar's only record of
> "Cher-O-Kee Concow Rancheria". The durable fix is one column, `row_is_facility`,
> emitted by `code/23d_build_gaming_facilities.py`; until it exists this
> sentence is the exclusion list, and it has exactly one member.

**785 of 787 rows carry a `tribe_id`.** The two that do not are VP-0109 above
and `CEDAR-FAC-000020` "Golden Eagle Casino", which is a genuine attribution
gap and is **deliberately blank, not overlooked**. Both are adjudicated in
`review/gaming_facility_attribution_rulings_2026-09-01.csv`, which extends the
2026-08-26 card with a third, independent leg — the Oklahoma state regulator.
See Part 3.4.

Only **192 of 787 rows carry any URL.** The entity-sharded agents (A–D) are
closing that, writing to `data/staging/tribe_web_map/` and
`data/staging/tribe_harvest/`. **This workstream does not crawl operator sites**
— that would duplicate their pass.

---

## PART 2 — THE NIGC DOCUMENT SURFACE, ENUMERATED

*Nobody had ever asked what NIGC publishes. This is the answer, and it is now a
file rather than a memory.*

**Route, measured 2026-09-01, each probe recorded because each kills an
explanation (`docs/PULL_DISCIPLINE.md`):**

```
GET  /robots.txt                            200  Disallow: /wp-admin/ and
                                                 /wp-content/uploads/wpforms/
                                                 ONLY. Sitemap declared.
                                                 Every path used here is allowed.
GET  /wp-sitemap.xml                        200  14 child sitemaps
GET  /wp-sitemap-posts-wpdmpro-{1,2,3}.xml  200  4,071 documents
GET  /wp-sitemap-taxonomies-wpdmcategory-1  200  72 categories
GET  /wp-json/wp/v2/types                   401  rest_not_logged_in
GET  /wp-json/wp/v2/wpdmpro?per_page=1      401  rest_not_logged_in
GET  /wp-json/wp/v2/wpdmcategory            401  rest_not_logged_in
GET  /downloads/<category>/[page/N/]        200  24 <article> per page, rel=next
GET  /download/<slug>/?wpdmdl=<id>          302  -> the wp-content object
```

**The REST API is closed to anonymous callers** — the identical 401 script 155
measured on the map route, from WordPress's own `rest_authentication_errors`
filter and not a nonce failure. The **server-rendered category listings are the
only public enumeration**, and they carry everything an index needs: title,
`/download/<slug>/` URL and a `datePublished`.

### The date trap, and how this build handles it

`datePublished` on a listing is **when NIGC posted the file to the website**. It
is **not** when the action issued. Iowa Tribe of Kansas and Nebraska NOV-25-01
carries `datePublished 2025-09-26` and resolves to
`.../2025/09/2025.09.24-NOV-25-01-Iowa-KS-NE.pdf` — the action is **2025-09-24**.

`code/344` therefore stores three fields and never collapses them:
`wp_post_date`, `document_date` (parsed from the **resolved** filename, blank
when the filename has none) and `document_date_basis`. Where the filename has
no date but the upload path says `/2025/09/`, `document_date` stays **blank**
and the basis records that *an upload month is not a document date*. The action
code (`NOV-25-01`) is parsed separately, and its two-digit year is stored as
`action_code_year` **unexpanded** — a two-digit year inside NIGC's own code is
a claim by NIGC, not a date we computed.

### Full category index

See `data/staging/nigc_document_surface_staged.csv` — one row per
(category, document), with the title, the URL, the post date, and a
`cedar_holds_this_family` column naming where Cedar already holds it.
`_UNCATEGORISED_IN_LISTINGS` rows are documents present in the sitemap that no
category listing surfaced; they are carried, not dropped.

**7,930 (category, document) memberships over 4,071 distinct documents in 72
categories.** Three documents are in the sitemap and in no listing; they are
carried as `_UNCATEGORISED_IN_LISTINGS` rather than dropped.

A **caution on `wp_post_date`**: nearly every category's post dates fall in
**2024–2026** because NIGC rebuilt its website in 2024 and re-posted the whole
archive. A 1994 ordinance approval letter carries a 2024 post date. **This is a
second, independent reason `wp_post_date` is not a document date**, on top of
the NOV-25-01 case above, and it means the post date cannot be used to date
anything at all in this corpus.

| category | docs | Cedar holds it? |
|---|---:|---|
| `general-councel` | 1,727 | partly — this is the OGC umbrella and it re-lists the ordinance, declination and opinion families |
| `commission` | 1,230 | partly — umbrella |
| `gaming-ordinances` | **1,162** | **YES — 1,155.** The 7-document difference is new since the 2026-08-07 index pull. **Refresh signal.** |
| `tribal-consultations` | 673 | no — consultation transcripts and comment corpora |
| `office-of-chief-of-staff` | 658 | no — umbrella |
| **`enforcement-actions`** | **362** | **NO → FETCHED THIS PASS** |
| `declination-letters` | **329** | **YES — 327.** 2 new since 2026-08-06. **Refresh signal.** |
| `reports-and-publications` | 209 | no — this, not `annual-reports`, is where the older agency annual reports live |
| **`game-classification-opinions`** | 122 | **NO → FETCHED THIS PASS (index, 122 rows, 1992–2024)** |
| `media-center` / `news` / `featured-articles` | 111 / 104 / 17 | no — press |
| `bulletins` | 103 | no — regulatory guidance |
| **`indian-lands-opinions`** | 101 | **NO → FETCHED THIS PASS (index, 102 rows, 1997–2026)** |
| `qr-codes` | 100 | no — not data |
| `gross-gaming-revenue-reports` | 94 | **YES** — the by-region series FY2001–FY2025 |
| **`approved-management-contracts`** | **68** | **NO → FETCHED THIS PASS.** The `GAMING_TEMPORAL_BUILD_LOG.md` §10.6 hole. |
| `commission-final-decisions` | 65 | no — appeals of Chair actions. **Highest-value unfetched family.** |
| `cjis-resource-materials` / `checklists-and-worksheets` / `technology` / `training` | 63 / 60 / 37 / 23 | no — operational |
| `foia-reports` | 54 | no |
| `chairs-notice` | 34 | no — Chair notices of violation-adjacent action |
| `congressional-testimony` | 33 | no |
| `past-fonsis` / `decision-of-records` / `2015-consultation-nepa-comments` / `comments-on-draft-nepa-manual` | 29 / 4 / 18 / 4 | no — NIGC's own NEPA record, distinct from the BIA NEPA corpus Cedar piloted |
| `alternate-standards` | 26 | no — **per-tribe MICS alternate-standard approvals.** A tribe-identified regulatory series. |
| `rulemaking` / `laws-and-regulations` | 25 / 10 | no |
| `finance` / `annual-commission-budgets` / `financial-submissions` | 24 / 18 / 2 | no — includes the **fee rate** NIGC assesses on GGR |
| `compliance-reports` | 18 | no |
| `2013`–`2021 quarterly-report` (9 categories) | 3–4 each, 33 total | no — NIGC quarterly performance reports |
| `office-of-self-regulation` | 5 | no — **Class II self-regulation certificates.** Small, tribe-identified, unique. |
| `strategic-plan` / `performance-dashboard` / `biographies` / `speeches` / `privacy` / `eeo` / `pay-gov` / `ephs` / `nigc-ai` / `utility` / `tooltips` / … | 1–38 each | no — agency administration, no gaming facts |
| `annual-reports` | 1 | no — misleading name; only one document is filed here |
| `gaming-locations` | 4 | **YES** — the roster route `code/155` uses |

Full listing with titles and URLs:
`data/staging/nigc_document_surface_staged.csv`.

---

## PART 3 — WHAT WAS FETCHED THIS PASS

All by `code/344_pull_nigc_document_surface.py`, one dataset-scoped fetcher,
one host, one lock, released with all four outcome fields.

### 3.1 The enumeration — `data/staging/nigc_document_surface_staged.csv`

**7,930 rows** — one per (category, document) membership — over **4,071
distinct documents** in **72 categories**. This is the "what should exist"
half of the brief, in a file. `cedar_holds_this_family` names where Cedar
already holds each family, so the next reader can see the gap without
re-deriving it.

### 3.2 The two structured opinion indexes

Both are tablepress tables in the page HTML, so the index alone is a dataset.

**`data/staging/nigc_indian_lands_opinions_staged.csv` — 102 rows,
1997-08-12 → 2026-05-18.** Columns: tribe (verbatim), parcel, legal theory,
**theory accepted Y/N**, date, document URL. **98 of 102 keyed to the spine**
by `resolve_entity`; the 4 that are not are all *"Delaware Tribe of Western
Oklahoma"*, refused as `ambiguous_containment:2` between Delaware Nation and
Delaware Tribe of Indians and queued to
`review/nigc_document_surface_unresolved_2026-09-01.csv`. **Held, never
guessed.**

Outcome distribution: **66 accepted, 36 not.** Top legal theories: Restored
Lands 33, Within Reservation Boundaries 12, Jurisdiction 11, Settlement of a
Land Claim 6, Indian Lands Oklahoma 5, Contiguous to Reservation 5.

*Why this matters beyond its size:* `gaming_land_decisions` (BIA, 138 rows)
carries the **land** determination. This is the **gaming-eligibility** opinion
on the same legal theories, from a different agency, with an explicit
accepted/rejected outcome. Together they are a two-agency panel on the same
question, and the 36 rejections are the half no directory product carries.

**`data/staging/nigc_game_classification_opinions_staged.csv` — 122 rows,
1992-09-14 → 2024-04-26.** Columns: game title, Class II/III/Both, and boolean
flags for bingo, card games, pull tabs, internet gaming and other. 62 Class
III, 55 Class II, 3 Both, 2 unstated; 29 bingo, **6 internet gaming**. Not
tribe-keyed and correctly so — the grain is a **game**, not an operator.
**This is the earliest-reaching series in the whole gaming dataset**, four
years earlier than any other, and the Class II/III line it draws is the line
IGRA turns on.

### 3.3 The two document families

**430 objects fetched, 673 MB, 424 distinct md5s, 0 refused by the host.** The
six repeated md5s are genuine — NIGC re-posts the same letter under two slugs,
never more than three — and they sit well under the same-object guard described
in 3.5. Every object is in
`data/raw/external/nigc_documents/_SOURCE_MANIFEST.csv` with its bytes, md5,
`md5_duplicate_of`, resolved URL and HTTP status.

**`data/staging/nigc_enforcement_actions_staged.csv` — 362 rows, 320 keyed to
the spine.** NIGC's whole published enforcement record:

| action type | rows |
|---|---:|
| NOV — notice of violation | 146 |
| SA — settlement agreement | 99 |
| CFA — civil fine assessment | 17 |
| CO — closure order | 10 |
| TCO — temporary closure order | 1 |
| NDO — notice of default / order | 1 |
| no code in the title or filename | 88 |

**Horizon: `action_code_year` runs 95, 96, 98, 99 → 26 — 1995 to 2026, the full
enforcement life of the agency.** The heaviest years are 08 (57) and 09 (66),
the post-financial-crisis enforcement wave.

Dates are handled with three separate fields and no collapsing, because in this
corpus they genuinely differ in strength:

* `document_date` — **25 rows**, 2005-06-08 → 2026-01-12, parsed from the
  resolved filename (`2026.01.12-NOV-26-01-Grand-Traverse.pdf`,
  `20240905_Alabama_Coushatta_NOV_24-01.pdf`).
* `action_code_year` — **274 rows**, stored as **the two digits NIGC printed**
  and deliberately **not expanded to four**. `SA-00-09` is 2000 and `NDO-99-05`
  is 1999, but that is an inference about a century and it is left to the
  consumer with the evidence in front of it.
* `wp_post_date` — always present, and **never a document date**: NIGC rebuilt
  its site in 2024, so a 1999 civil fine assessment carries a 2025 post date.
  The `document_date_basis` column says so on every row, naming the upload
  month it refused to promote.

**67 rows carry neither a code nor a date.** Their date is inside the PDF and
this build did not open one — a named, sized follow-up, not a silent blank.

**`data/staging/nigc_management_contract_approvals_staged.csv` — 68 rows, 67
keyed, 55 distinct tribes.** Only 3 carry a filename date (2011-06-20 →
2018-10-31); NIGC names these files after the property
(`cheyennearapahoswcasino.pdf`), not the date.

**This closes `GAMING_TEMPORAL_BUILD_LOG.md` §10.6 at the source.** That log
recorded `trace_nigc_management_contract = 0` on all 774 property rows with
`nigc_management_contract_status = not_held_by_cedar_press_this_session`, and
said the right thing about it: *"recorded as NOT SEARCHED rather than as
absent, because absence under a filter is a property of the filter."* It has
now been searched. **55 tribes have a Chair-approved management contract on
file**; the trace can be filled from this table rather than from a fresh pull.

**43 names were not resolved** and are queued to
`review/nigc_documents_unresolved_2026-09-01.csv`: 40 `no_spine_match` — almost
all enforcement documents whose only title is a file code (`NOV-02-01`,
`SA-00-09`) with no tribe named anywhere outside the PDF — plus 2 San Carlos
Apache and 1 Delaware `ambiguous_containment`. **Held, never guessed.**

### 3.5 THE DEFECT THIS PASS ALMOST SHIPPED, AND THE GUARD THAT NOW STOPS IT

The first attempt requested `https://www.nigc.gov/download/<slug>/?wpdmdl=` —
the parameter **present and empty**. WP Download Manager returned **HTTP 200
with a valid PDF every time**, and it was **the same PDF every time**: NIGC's
generic *"Helpful Hints: Requesting a Game Classification Opinion"*, md5
`a917db80b6027b0ffd8a8b233eb8331a`. **302 enforcement actions were
"downloaded" and all 302 were that one file.**

Nothing in the transport said so — right status, right content type, right
`%PDF` magic bytes, one file per slug on disk. It surfaced only because several
files shared an identical byte size and `md5sum | sort | uniq -c` then returned
a single line reading `302`.

It is `PULL_DISCIPLINE.md`'s **"an accepted token is not a working job"** in a
new costume: the transport succeeded and the CONTENT was wrong. The
generalisable rule:

> **A `?param=` with an empty value is not the same request as no parameter at
> all.** A CMS that would 404 on a bad id will happily serve a default for a
> blank one.

All 302 were deleted, the host lock was released with
`accepted_then_failed_server_side: 302` and the cause named in it, and two
guards were added before re-running: the download URL is now **read off the
landing page and must contain the package's own slug** (which excludes the
site-navigation `https://www.nigc.gov/?wpdmdl=3974` links that make a bare
parameter look reasonable), and **`IDENTICAL_MD5_CEILING = 6`** stops the run
if one md5 comes back for more than six distinct slugs. A **three-object canary
with three distinct md5s** was run before re-committing to 430.

### 3.4 The two `gaming_facilities` defects

Raised by the coordinator, both worked, and **one of them was already
adjudicated and refused for a reason worth preserving**. Full cards, with the
evidence chains, in
`review/gaming_facility_attribution_rulings_2026-09-01.csv`.

**`VP-0109` "Konkow Valley Band - no casino" — GRAIN.** Not an attribution
problem. It is a row asserting the absence of a facility inside a
one-row-per-facility table, and it inflates every count. Disposition: **keep,
flag, exclude from counts**; the grain and the one-member exclusion list are
now stated in 1F above. The attribution half was already ruled on 2026-08-26
and that ruling stands: nothing named Konkow or Concow exists in the
1,489-row spine, and keying it needs a **recognition** ruling, which is not a
gaming ruling.

**`CEDAR-FAC-000020` "Golden Eagle Casino" — ATTRIBUTION.**
`review/gaming_facility_hub_rulings_2026-08-26.csv` had already refused this
one, correctly, because **NIGC's own record contradicts itself**: the marker's
contact block pairs the Apache Tribe of Oklahoma's PO Box with
`Mspell@goldeneaglecasino.com`, and `goldeneaglecasino.com` is the **Kansas**
Kickapoo operator's domain. An address-only chain would have walked straight
past that.

This pass adds a **third, independent leg the earlier card did not have — a
state regulator** — and on it recommends `TRBF-APCHOK-00`:

1. **Region.** NIGC files this marker under its **Oklahoma** Region. The
   Kansas Golden Eagle Casino is a **separate marker (id 458) under NIGC's
   Tulsa Region** with its own street address. NIGC treats them as two
   locations.
2. **Address, and its uniqueness.** NIGC publishes the marker's contact as
   *"P.O. Box 1330, Anadarko OK 73005"*. NIGC's own ordinance approval letter
   of 2016-12-01 is addressed to *"Mr. Bobby Komardley, Chairman, Apache
   Business Committee, 511 East Colorado, Post Office Box 1330, Anadarko, OK
   73005"*. **That PO Box was searched across all 1,151 NIGC ordinance PDFs on
   disk and appears for exactly one tribe.**
3. **NEW — Oklahoma OMES, Gaming Compliance Annual Report FY2025**, *"OKLAHOMA
   CASINO LISTING"*: *"At the end of fiscal year 2025, 33 tribes were
   operating 138 facilities…"*, and the table beneath reads **"Apache Tribe of
   Oklahoma  2"**. The State says the tribe runs **two** Oklahoma casinos.
   Cedar holds **one** (Silver Buffalo, Anadarko). A Kansas property cannot be
   the other. Measured alongside: **Silver Buffalo does not appear in NIGC's
   510-row roster at all**, so NIGC's Oklahoma Region carries no other
   Apache-Tribe-of-Oklahoma marker.
4. Corroboration only, **explicitly not a rung**: the published coordinate
   34.893841,-98.364952 is the town of Apache, Caddo County OK, 22.5 km from
   Silver Buffalo. **A coordinate is not a rung in this project** and nothing
   here rests on it.

**The cell is still blank.** Tier-A attribution is Elijah's ruling, and the
disconfirming leg is real. What would close it is the **name** of the Apache
Tribe of Oklahoma's second facility — OMES counts, it does not name — and the
entity-sharded agents are visiting that tribe's site now. **This workstream
did not crawl for it**, deliberately.

---

## PART 4 — DELIBERATELY EXCLUDED, WITH THE REASON

A source excluded for a reason is not a gap. Re-litigating these costs
requests and earns blocks.

| source | why it is excluded | status |
|---|---|---|
| **Casino City Press panel** | **VENDOR-LICENSED.** `gaming_property_capacity_history.csv` (64,181 rows, 100% Casino City) and `gaming_facility_metrics.csv` (65,223 rows, derived) are in `cedar_codebook.LICENSED_SOURCE_FILES`, and `casino_city_id` is in `LICENSED_COLS`. **May be held internally for QA and may NEVER ship.** Both had live shipping contracts until 2026-08-26; they were purged to `graveyard/2026-08-26_licensed_dist_purge/`. **Do not add a Casino City column to any table this workstream creates.** |
| **MSRB EMMA official statements and continuing disclosures** | `emma.msrb.org/robots.txt` is two lines: `User-agent: *` / `Disallow: /*.pdf$`. The disclosures are PDFs. **Terms forbid an automated client**, so no scrape. Recorded, not attempted. A human-mediated pull is possible and the FL log names the issuer to search under. |
| **Tribal audited financial statements** | Filed annually with the Federal Audit Clearinghouse and **withheld by 2 CFR 200.512(b)(2)** because the auditee is a tribe. Statutory, not technical. |
| **Nevada tribal casino revenue** | The State **holds it and has contracted away the right to publish it**; NRS 463.120 makes the record confidential. `held_by_state_but_sealed`, not `never_collected`. |
| **North Dakota tribal gaming records** | N.D.C.C. § 54-58-02 seals every tribal gaming record submitted to the State. |
| **Kansas tribal casino financials** | Sealed by compact; KLRD states the State receives no revenue except oversight cost. |
| **Wisconsin per-property revenue** | **Prohibited by compact confidentiality clauses**, quoted verbatim in `STATE_GAMING_PULL_LOG.md`. WI does not withhold it from us; the compact forbids the State disclosing it. |
| **Arizona per-tribe revenue** | **Aggregated by statute** — A.R.S. § 5-601.02(H)(1) requires the ADG report to publish a statewide total only. |
| **Minnesota payment series** | **No payment obligation exists.** Confirmed on three legs (compact text, Minn. Stat. § 3.9221 subd. 4, the mandated report). A blank Minnesota is correct. |
| `/wp-admin/`, `/wp-content/uploads/wpforms/` on nigc.gov | robots.txt `Disallow`. Not touched. |

---

## PART 5 — WHAT IS STILL MISSING, RANKED

Effort is in agent-sessions against this repository, assuming
`PULL_DISCIPLINE.md` is obeyed.

| # | what | why it is worth doing | effort | new rows / period |
|---:|---|---|---|---|
| 1 | **Promote NM FY2023 – 2026Q2 per-tribe net win** | Already extracted and **footed 14/14 against the source's own printed totals** (`logs/216_nm_extract.log`), the last quarter released **2026-08-19** — this alone brings New Mexico current to the August 2026 target. It is the country's second-best per-tribe revenue series after Connecticut, and it is sitting in `review/`. Nothing to fetch. **The change belongs in `code/92_build_gaming_capacity_official.py`, which must READ `review/nm_revshare_2023_2026_staged_2026-08-26.csv`** — appending to `data/clean/gaming_capacity_official.csv` by hand is the defect that returns on the next rebuild, which is exactly why this workstream left it staged. | **0.3 session** | **188 rows, FY2023–2026Q2** |
| 2 | **Repair the CA RSTF parse: 93rd report (2024Q4), and OCR the 98th (2026Q1)** | Both documents are on disk. The 93rd has 37,974 characters of text and yields zero rows — a parse defect. The 98th is an image-only scan and needs the OCR path `code/122`/`150` already runs for ordinances. Closes CA to 2026-06 with no network at all. | **0.5 session** | ~800 rows, 2024Q4 + 2026Q1, plus the short 95th/97th/99th |
| 3 | **Fetch the four remaining NIGC regulatory families** — `commission-final-decisions` (65), `chairs-notice` (34), `alternate-standards` (26), `office-of-self-regulation` (5) | **130 documents, and the route is already built.** Add the four slugs to `FETCH_CATEGORIES` in `code/344` and re-run `--stage docs`. Final decisions are appeals of Chair actions; alternate standards are **per-tribe MICS approvals**; self-regulation certificates are a small, unique, tribe-identified Class II series. | **0.3 session** | 130 documents |
| 4 | **Refresh NIGC ordinances (+7) and declinations (+2)** | Measured this pass: NIGC's index now holds **1,162** ordinance documents against Cedar's 1,155, and **329** declination letters against 327. Small, but it is the difference between a current series and a stale one. | **0.2 session** | 9 documents |
| 5 | **Washington inter-tribal machine transfer ledger (compact Appendix D)** | `wa_machine_transfers.csv` is **0 rows by design** and has been since the file was created. Each transfer is a **Native-to-Native commercial event with two tribal parties and a direction** — a flow federal data cannot see at all, and the closest analogue Cedar has to ANCSA §7(i) sharing. `STATE_GAMING_FRAMEWORKS.md` establishes that the State MUST hold these records or the machine cap is unenforceable. | **1 session** (WSGC; may need a public-records request rather than a scrape) | unknown; 29 tribes hold allocations |
| 6 | **State regulator LICENSEE lists** (vendor / supplier / manufacturer / key employee) | Cedar's `gaming_vendor_tribal_licenses` is **100% SEC-filing-derived — zero rows from any regulator.** That means it only sees vendors that are SEC registrants. NV GCB, CA CGCC, WA WSGC, AZ ADG and MI MGCB all publish licensee lists. Joins straight onto `gaming_device_observations` and `gaming_manufacturer_facts`. | **1–2 sessions**, 5–8 hosts, one poller each | likely several thousand |
| 7 | **FAC single-audit historical tail, FY1998–FY2015** | `fac_audit_gaming_disclosures` starts 2016. The FAC Census-era bulk archive reaches **FY1998**, is free and needs no key. `PULL_DISCIPLINE.md` Tier 3 already names this route, and it is the one route that reaches tribes with no federal contract at all. | **1 session** | 18 further audit years |
| 8 | **Oklahoma exclusivity fees FY2006 – FY2009** | OK is the largest gaming state by facility count (190) and Cedar's payment series starts FY2010. OMES's live reports page lists **FY2014 forward only**, so this is a **Wayback CDX** job — `code/211_cdx_enumerate_blocked_gaming_hosts.py` already has the technique. | **0.5 session** | 4 fiscal years × ~30 tribes |
| 9 | **Promote the Form 5500 gaming employment staging** | 2,046 rows, 140 tribes, 2009–2025, ~25 tribes/year new to Cedar's employment table. Blocked on **two rulings**, not on data: a `FORM5500_ACTIVE_PARTICIPANTS` `MeasurementType`, and whether the employment table admits tribe-level rows with no `facility_id`. | **0.3 session + 1 ruling** | 2,046 rows |
| 10 | **The NEPA development layer** | `GAMING_DATASET_PLAN.md`'s differentiating layer is **~15% built** — 25 documents against a 138-decision seed list, yielding 19 project facilities / 116 projections / 24 mitigation agreements. This is the largest unbuilt thing in the gaming dataset and the only one no competitor has. | **3+ sessions** | 100+ projects |
| 11 | **NIGC bulk text families** — `bulletins` (103), `reports-and-publications` (209), `tribal-consultations` (673) | Regulatory guidance and the older agency annual reports (which carry **national** GGR back into the 1990s, earlier than the by-region series). Bulk PDF, needs a piloted schema before parsing. | **1–2 sessions** | ~985 documents |
| 12 | **The five never-worked states: ID (13 facilities), TX (7), AL (3), AK (3), MO (1)** | 27 facilities with no regulator pull of any kind. **Expect mostly structural absences** — TX and AL gaming is litigated rather than compacted, AK has no Class III compacts — but an absence recorded from the instrument is a finding, and an absence nobody checked is not. | **0.5 session** | small; the verdict is the product |
| 13 | **Golden Eagle Casino attribution** | One unattributed facility. **Do not crawl for it** — the entity-sharded agents are visiting the Apache Tribe of Oklahoma's site now and will name the tribe's second Oklahoma facility as a byproduct. See Part 3.4. | free, as a byproduct | 1 row |

---

## PART 6 — HOW TO REFRESH EACH SOURCE

| source | cadence | change key | command |
|---|---|---|---|
| NIGC document surface (all 72 categories) | quarterly | `document_slug` new to `nigc_document_surface_staged.csv` | `py -3 code/344_pull_nigc_document_surface.py --stage surface` |
| NIGC legal-opinion index tables | quarterly | new `source_row` in tablepress-9 / tablepress-10 | `py -3 code/344_pull_nigc_document_surface.py --stage opinions` |
| NIGC enforcement + management contracts | quarterly | new `document_url` not in `_SOURCE_MANIFEST.csv` | `py -3 code/344_pull_nigc_document_surface.py --stage docs` |
| NIGC GGR by region | **annual, mid-year for the prior FY** | `fiscal_year` | `code/84_build_nigc_regions.py` |
| NIGC ordinances | quarterly | index row count | `code/118_build_gaming_ordinances.py` |
| CT monthly slot | monthly (**source is currently 8 months behind itself**) | `max(date)` on the Socrata endpoint | `py -3 code/343_refresh_ct_gaming_monthly.py` |
| CA RSTF/SDF | quarterly, ~6 weeks after close | RSTF report ordinal (99th = 2026-06-30) | `code/103_build_california_gaming.py` |
| NM revenue sharing | quarterly | quarter in the news-release filename | `code/215` then `code/216` |
| MI / CT / AZ digital | monthly | `period_end` | `code/119_build_digital_and_loyalty.py` |

`code/344` is **resumable and idempotent**: pages already on disk are read from
disk, objects already in `_SOURCE_MANIFEST.csv` are skipped, and the host lock
records `downloaded_this_run` / `already_on_disk_skipped` / `refused_by_host` /
`accepted_then_failed_server_side` as four separate fields so no other agent can
read "there was nothing to do" as "the host is refusing".

---

## PART 7 — THE PROMOTION PATH FOR THE STAGED TABLES

Everything `code/344` writes lands in `data/staging/`, deliberately. These are
new grains, and `docs/GAMING_SOURCE_AUDIT_2026-08-26.md` is 945 lines about
what happens when a table reaches `data/clean/` without a codebook block: it
scores under 0.60 against `codebook_master.csv`, script 87 skips it, and it
becomes invisible.

To promote any of them:

1. declare the grain and the primary key (see the per-table note in Part 3);
2. write a codebook fragment with `py -3 code/cedar_register_codebook.py`
   — **new block letters only**; `07d` and `07e` are already taken twice each,
   and the last collision cost 13,803 rows nineteen days of invisibility;
3. copy `data/staging/<t>.csv` to `data/clean/<t>.csv` from a builder, never by
   hand — "fix the generating pipeline, never the output CSV";
4. re-run the shipping chain in `docs/SHIPPING_RUNBOOK.md` and check
   `dist/_ship_rate.csv` actually moved.

**A build is not finished when the table is written. It is finished when the
table can leave the building, or when a named line says why it cannot.**

---

## PART 8 — GATE STATUS AT THE END OF THIS PASS

`py -3 code/62_no_regression_check.py` **exited 0 at 2026-09-01 18:47**, before
this workstream changed anything, and **exits 1 at 20:0x**. **Not one of the
failures is gaming, and none is this workstream's.** Standing rule 15 says name
them and their owners rather than record them as "pre-existing, not mine", so:

| failing metric | the actual line | owner |
|---|---|---|
| `lint_class1`, `lint_class2a`, `lint_class5` | `code/570_shard_l_vendor_list_hunt.py` :279, :740, :540 | the entity-sharded scrape program (shard L) |
| `lint_class2b` | `code/shard_f_membership.py` | same program (shard F) |
| `lint_class5` (2nd) | `code/shard_g_newsletters.py` :368 | same program (shard G) |
| `code_duplicate_numbers` 43 → 44 | `code/561_shard_k_alaska_villages.py` collides with `code/561_shard_m_vendor_list_sweep.py` | same program |
| `tables_missing_from_25_TABLES` 179 → 180, `_27_SPEC` 194 → 195, `tables_undocumented_in_codebook` | `data/clean/native_owned_businesses.csv`, 2,393 rows, written 19:20 | `code/330_build_native_owned_businesses.py` |
| `F-DELAWARE-ALIAS` | `cedar_identifier_ledger_final.csv` / `_tiered.csv`, 1 row each | entity layer, pre-existing |

**This workstream wrote ZERO tables to `data/clean/`** — everything is in
`data/staging/`, `review/`, `data/raw/` and `docs/`. The linter reports
`code/344_pull_nigc_document_surface.py` with **zero findings**: its one
`class2c` instance (a `skipped` counter that named nothing) was **fixed, not
waived** — every skipped object is now named in `_state.json['objects_done']`
and the first five print to the log.

`AGENTS.md` is the place 62 asks for this note. It was **not edited**, because
several agents are live and AGENTS.md is the most central file in the repo —
"only one agent may own a central file per pass". The same content is in the
handoff ledger instead, where it is append-only and cannot lose an update:
**`HAND-4BEB2F5D06`**, alongside this pass's work record **`HAND-043E178D5B`**.
