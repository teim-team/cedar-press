# Source exploration — what Cedar does not have, and can reach for free

*Written 2026-09-02 by the `source-exploration` workstream. Nothing was committed.
Nothing was written to `data/clean/` or `data/spine/`.*

**Script:** `code/1111_probe_new_source_candidates.py` (claimed atomically via
`1050_preflight.py claim`). `selftest` passes and **fires on an injected
violation**. Re-derive everything below with:

```
py -3 code/1111_probe_new_source_candidates.py selftest
py -3 code/1111_probe_new_source_candidates.py probe      # ~200 requests, 53 candidates
py -3 code/1111_probe_new_source_candidates.py report
```

**Machine-readable candidate table:** `docs/SOURCE_EXPLORATION_2026-09-02.csv`
— **57 rows × 17 columns**, one row per candidate object, each carrying
`grain`, `feeds_cedar_dataset`, `join_identifier`, `access_route`,
`terms_verbatim`, `robots_posture`, `estimated_rows`, `refresh_cadence`,
`measured_status` and a `verdict` of ACQUIRE / INVESTIGATE / REJECT with its
reason.

**Raw evidence:** `data/staging/source_exploration_1111/probe_log.jsonl`
(one JSON record per HTTP request — URL, UA used, status, content-type, bytes,
elapsed, first 2,000 bytes of body) and `probe_results.csv`.

> **This was a survey, not a scrape.** No bulk object was downloaded. The
> largest single read was 60 KB and most were under 5 KB. Two artefacts were
> saved because they are the evidence for a claim in this document:
> `nhoa_membership.html` (36 KB) and `biamaps_hosted.json` (2 KB).

**Verdict split: ACQUIRE 8 · INVESTIGATE 35 · REJECT 14.**

---

## 0. THE METHOD FINDING, BEFORE THE SOURCES

The brief warned that `can_fetch()` called with our own User-Agent misses a
`User-agent: ClaudeBot` rule, because `RobotFileParser` only consults a group
whose token is a prefix of the string you hand it. **`1111` asks `can_fetch()`
once per agent token — ours, `CedarPress`, `ClaudeBot`, `Claude-User`,
`Claude-SearchBot`, `anthropic-ai`, `CCBot`, `Python-urllib`, `*` — and reports
the union.** `selftest` proves the naive check misses a ClaudeBot-only rule and
the union check catches it:

```
OK  naive can_fetch(OUR_UA)=True (misses it); union check denies ['ClaudeBot']
OK  empty robots.txt reads as ALLOWED for every token
OK  'Disallow:' with no path reads as ALLOWED
```

**It fired on live hosts. Five of 53 candidates are robots-disallowed for an
agent this client plausibly is, and on THREE of them a `can_fetch()` with
Cedar's own UA returns ALLOWED:**

| host | denied agents | would our own UA have seen it? |
|---|---|---|
| `civilrightsdata.ed.gov` | `ClaudeBot`, `anthropic-ai`, `CCBot` | **No — allowed** |
| `data.hrsa.gov` | `ClaudeBot`, `Claude-User`, `anthropic-ai`, `CCBot` | **No — allowed** (there is no `*` group at all) |
| `www.hud.gov` | `ClaudeBot`, `CCBot` | **No — allowed** |
| `educationdata.urban.org` | every token, on `/api/` | yes |
| `hbe.dcca.hawaii.gov` | every token, whole host | yes |

`civilrightsdata.ed.gov` states it in fourteen named groups, verbatim:

> `User-agent: anthropic-ai` / `Disallow: /`
> `User-agent: ClaudeBot` / `Disallow: /`

`data.hrsa.gov` puts twenty-four agents in one group under the comment
`#ai chatbots`, including `ClaudeBot`, `Claude-Web`, `Claude-User` and
`anthropic-ai`, ending `Disallow: /`.

**And a third posture appeared that Cedar has no vocabulary for yet.**
`www.hud.gov` allows `*` and then adds:

> `Content-Signal: search=yes,ai-train=no,use=reference`

with a header stating that *"ANY RESTRICTIONS EXPRESSED VIA CONTENT SIGNALS ARE
EXPRESS RESERVATIONS OF RIGHTS UNDER ARTICLE 4 OF THE EUROPEAN UNION DIRECTIVE
2019/790"*. That is neither a source restriction nor a method restriction —
it is a **use** restriction, and `docs/PUBLICATION_POLICY.md` `TERMS-METHOD`
enumerates only three kinds. **Owner decision, before any HUD fetch.**

**In the other direction**, the phantom-block trap held: `api.fac.gov` and
`api.eia.gov` 403 their own `robots.txt` because the *API* answers that path
and demands a key; `cage.dla.mil`, `biamaps.geoplatform.gov` and
`irs-form-990.s3.amazonaws.com` 404 it; `npiregistry.cms.hhs.gov` and
`gis.data.alaska.gov` serve their single-page-app HTML at it. **None of those
seven is a refusal**, and reading any of them as `disallow_all` would have
killed three of the eight ACQUIRE candidates.

---

## 1. THE TOP FIVE BY VALUE, AND WHAT EACH CLOSES

### 1. `biamaps.geoplatform.gov` — the BIA's own ArcGIS server. **250,284 rows across six layers, no key, nothing in Cedar's 55-source registry touches it.**

Found by following `www.bie.edu/schools`, not by searching. Its
`og:image` points at `biamaps.geoplatform.gov`; the ArcGIS REST root answers:

```
GET https://biamaps.geoplatform.gov/server/rest/services?f=json   -> 200
{"currentVersion":11.5,"folders":["AgyChickasaw","AgyOsage","BOGS","DivLTR",
 "ForestCover","Hosted","NIOGEMS","ParcelFabric","RegARO","RegEOR","RegERO",
 "RegGPR","RegMWR","RegNRO","RegNWR","RegPRO","RegRMR","RegSPR","RegSWR",
 "RegWRO","sde","Test","Utilities"]}
```

`DivLTR` is the **Division of Land Titles and Records**. `NIOGEMS` is the
**National Indian Oil and Gas Evaluation Management System**. `robots.txt`
returns 404, so nothing is disallowed. Every count below is `returnCountOnly`
on the live service:

| layer | rows | what it is | closes |
|---|---:|---|---|
| `Hosted/BIA_Mineral_Acreage_Table` | **249,165** | tract-level Indian mineral acreage: `ltro_code`, `regional_office`, `land_area_name`, `tract_id`, `acres`, `inactivated_date`, `resource_code`, `ownership_type`, `state` | `WHAT_IS_MISSING` natural-resources **#3 — "no volume, no price — revenue with no denominator"**. This is the acreage denominator, from the agency that holds the title |
| `Hosted/Tribal_Leaders_Directory_new` | 587 | the TLD as a queryable feature service with `biaregion`, `biaagency`, `tribalcomponent`, `tribealternatename` | structured fields for a source (`bia_directory`) Cedar currently reads as HTML |
| `DivLTR/BIA_AIAN_National_LAR` | 335 | *"the external extent of federal Indian reservations and the external extent of associated land held in 'trust' by the United States, 'restricted fee' or 'mixed ownership' status"* (the service's own description, verbatim) | the authoritative trust-land layer |
| `BOGS/BIA_Office` | 93 | BIA office locations | **the "BIA facility register" the brief names as likely unheld** |
| `Hosted/PL102_477_Contracts` | 84 | PL 102-477 self-governance plan agreements with `plan_start_date`, `plan_expiration_date`, `plan_renewal_date`, `partner_name`, `region` | **84 DATED public facts** against a 545-entity stale tail, from a programme no Cedar source covers |
| `Hosted/OFAPetitioners` | 20 | Office of Federal Acknowledgment petitioners | `ASSERTION_LAYER`: *"`entity.is_federally_recognized` has no negative case"* |

Also present and unexamined: `Hosted/EE_Permitting`, `Hosted/NEPA_Table` (74),
`Hosted/BIA_RGCs`, `Hosted/MRO_Tribes_Boundaries`, `Hosted/TribalGrasslands_NLCD`,
`ParcelFabric`, and twelve regional folders.

**Verdict ACQUIRE.** One host, one API shape, no key, no robots restriction,
and it reaches four different Cedar datasets.

### 2. BIE Schools Directory — **183 schools**, and the only route found that can beat NCES's 2024 ceiling

`KNOWN_ISSUES` **A4** says NCES cannot make a BIE school look fresh *by
construction*: CCD's newest fips-59 collection year is 2024 (count date
2024-10-01) and the reporting universe is a static 174 schools. That is true of
NCES. It is not true of the agency.

`https://www.bie.edu/schools` returns 200 and its own `og:description` says,
verbatim:

> *"Here are 183 Bureau-funded elementary and secondary schools and residential
> facilities. Of these, 55 are BIE-Operated and 128 are Tribally Controlled.
> The BIE also directly operates two postsecondary institutions… **This web
> application replaces the Bureau of Indian Education School Directory on the
> BIE website.** This shows the location and contact information for BIE
> schools."*

**183 against CCD's static 174**, an operated/controlled split CCD does not
carry, and it is served off the open ArcGIS host in §1. **Verdict ACQUIRE** —
this is the named untried route for the 116 stale BIE schools.

### 3. USAC open data — **53,847 rows that carry a `tribal_type` the publisher assigned**, public domain

`opendata.usac.org` is a Socrata portal, 77 assets, no key for read. Measured
by `$select=count(*)` and `$group=tribal_type` on the live API:

| asset | rows | note |
|---|---:|---|
| E-Rate Recipient Details And Commitments (`avi8-svp9`) | **19,422,016** | of which **53,847** carry a `tribal_type`: **42,967 Tribal School**, **10,862 Tribal Library**, 18 Tribal College/University Library |
| Rural Health Care Commitments and Disbursements (`2kme-evqq`) | **471,726** | tribal and IHS clinics draw RHC funds; no Cedar source sees them |
| High Cost Disbursements (`w6qn-gx72`) | 1,045,128 | keyed on study-area code, so the tribal carriers must be identified first — INVESTIGATE |

Asset metadata `license` reads **`Public Domain`**. `rowsUpdatedAt` on
`avi8-svp9` was **2026-09-02T09:38:57Z** — the day it was probed.

Why this ranks so high is not the row count. `docs/PULL_DISCIPLINE.md`'s
selection doctrine measured that **an identifier-seeded pull can never discover
an entity Cedar does not already know**, and that roughly three quarters of the
entity universe is invisible to one. **`tribal_type` is a TYPE FILTER leg** —
the publisher's own categorisation — which is precisely the leg that finds
unknown entities. **Verdict ACQUIRE.**

### 4. CMS NPPES — the second independent source `ASSERTION_LAYER` item 0 asks for

`START_HERE` item 0: *"Harvest a SECOND, GENUINELY INDEPENDENT SOURCE for a
field the spine already asserts… every fact in Cedar rests on exactly one
source."* Its named candidates are the IRS BMF and SAM registration. **SAM is
self-reported and the registry itself says it is "NOT authoritative for who
owns it"; the IRS has already been tried and `KNOWN_ISSUES` A3 records that 258
Native Hawaiian entities return no IRS organisation at all.**

CMS enumeration is a third family. `npiregistry.cms.hhs.gov/api/?version=2.1`
returns 200 with no key and real records carrying organisation legal name,
*other* name, mailing address, practice-location address, taxonomy and
enumeration date. Wildcard organisation search works
(`organization_name=tribal*`). It is independent of both the FR roster and the
IRS BMF, and it is authoritative for a *health* organisation's registered
address in a way neither of those is.

**Verdict ACQUIRE for the API.** The bulk-file route
(`download.cms.gov/nppes/NPI_Files.html`) is **INVESTIGATE, not ACQUIRE** —
the page answers 200 but its `.zip` links are script-rendered and were not
enumerated, so no row count is claimed.

### 5. CDFI Fund AMIS — **the working route the brief asked for**

The brief: *"Treasury CDFI Fund awards (its export 404s — find the working
route)."* Reproduced: `www.cdfifund.gov/sites/cdfi/files/…/CDFI_Cert_List.xlsx`
returns 404. But `amis.cdfifund.gov` — the Awards Management Information
System — answers 200 and its `robots.txt` says, verbatim:

```
User-agent: *    # applies to all robots
Allow: /      # allow all
Disallow: */secur/forgotpassword.jsp?*

Sitemap: https://amis.cdfifund.gov/OpportunityZones/s/sitemap.xml
Sitemap: https://amis.cdfifund.gov/s/sitemap.xml
```

**A publisher that explicitly allows all robots and publishes two sitemaps.**
`docs/STALE_TAIL_CLOSURE_1081.md` leaves **26 Native CDFIs still stale and 10
undated**. **Verdict INVESTIGATE** — the sitemap was not walked in this pass,
so no grain or row count is claimed, and ACQUIRE would be a guess.

---

## 2. THE OWNER'S NONPROFIT / PHILANTHROPY LEAD, ANSWERED

He asked specifically about this. Each lead, with what was measured:

| lead | measured | verdict |
|---|---|---|
| **IRS 990 e-file XML on AWS** | `s3://irs-form-990` anonymous listing returns **HTTP 200 with `KeyCount=0`, `IsTruncated=false`, empty prefix**. `registry.opendata.aws/irs990/` still advertises it at 200. **The bucket is empty.** | **REJECT** — *a 200 is not presence*. The live route stays `apps.irs.gov`, which Cedar holds |
| **Federal Audit Clearinghouse, full table set** | `api.fac.gov` 403s unkeyed with `API_KEY_MISSING`; `code/147_build_fac_single_audits.py` **already pages `/general`, `/federal_awards`, `/findings_text`, `/notes_to_sefa` and `/corrective_action_plans`** on a hardcoded api.data.gov key | **REJECT — not new.** Its own docstring records 127 `federal_awards` rows on one Seminole audit |
| **Candid / Foundation Directory** | `developer.candid.org` and `candid.org` both 200, neither blocks by robots. **Price and licence were not established.** | **INVESTIGATE** — a terms-and-cost question for the owner. Do not record it as free |
| **State charity registrations — California** | `rct.doj.ca.gov` did not resolve (URLError); the guessed `oag.ca.gov` public-data path 404s | **INVESTIGATE** — a DNS failure is not a refusal and a guessed 404 is not an absence |
| **State charity registrations — New York** | `data.ny.gov` Socrata catalog answers 200; a `q=charit` query returned after-school contract assets, not the Charities Bureau register | **REJECT on this query** — recorded as a measured miss, not as proof of absence |
| **Grantmaker 990-PF grant schedules** | not separately probed — the 990-PF surface is the same `apps.irs.gov` corpus as above, and `grantmaker_funding_flows.csv` already holds 18,656 rows from 14 grantmakers | **not opened** |

---

## 3. THE THREE NAMED GAPS: WHAT ACTUALLY CLOSES THEM

### 170 NHOs with no dated public record — **both named routes are now measured, and neither is simply open**

**Route 1, the NHOA member directory.** The origin is alive
(`http://www.nhoassociation.org/`, 200). **NHOA's own `robots.txt` disallows
exactly the page that holds the list**, verbatim:

```
User-agent: *
Disallow: /ajax/
Disallow: /apps/
Disallow: /sba-private-session-with-nhoa-members.html
Disallow: /nhoa-member-list.html
Disallow: /businesssummit.html
```

`/membership.html` **is** allowed; it was fetched (36,863 bytes) and **contains
no member names** — only the eligibility sentence Cedar already quotes
(*"NHOA membership is open to any non-profit NHO certified by the SBA pursuant
to 13 C.F.R. 124.3"*) and a contact address. Cedar's shard H used a Wayback
capture of the member page. **Whether Wayback is a different route or the same
refusal is a `TERMS-METHOD` question and it is an owner decision, not an
agent's.** The site publishes an email address; asking is the route back in.

**Route 2, the SBA 8(a) register. `KNOWN_ISSUES` A3 is wrong that it is
untried.** Measured:

* `data.sba.gov`'s own dataset index was **walked, both pager pages** — ten
  datasets, and **not one is an 8(a) or HUBZone certified-FIRM roster**. The
  only Native-relevant asset is *HUBZone Qualified Indian Lands*, a geography
  layer. It is not CKAN; `/api/3/action/*` 404s.
* `certification.sba.gov` is an **application portal**, not a register.
* **`data/raw/external/sba_dsbs_native_entities.csv` is already on this
  machine** — a DSBS extract dated **2026-04-30**, **5,087 rows**, `uei`,
  `cage_code`, `name_clean`, `Active SBA certifications`, `City`, `State`.
  **442 rows are Hawaii**; 1,257 carry a certification value. Beside it,
  `hawaii_nho_candidates.csv`, **444 rows** with an `nho_status` column.
  `code/01_build_entity_spine.py` loads both.

  **So the state is `ON_DISK_NOT_PROMOTED`, not `NOT_ACQUIRED`** — with one
  caveat that keeps A3 open: **the DSBS extract carries no date column**, so it
  cannot supply the *dated* public fact A3 needs.

**Route 3, which nobody had named: the Hawaii state register. It is closed by
the publisher.** `hbe.dcca.hawaii.gov/robots.txt` is two lines:

```
User-agent: *
Disallow: /
```

The predecessor `hbe.ehawaii.gov` answers 200 only to serve a ten-second
redirect notice to that host.

**What is left, and it is real:** `dhhl.hawaii.gov` (Dept. of Hawaiian Home
Lands) and `www.oha.org` (Office of Hawaiian Affairs) both allow robots and
both publish sitemap indexes that answer 200 and **were not walked**. Most of
the 170 are homestead associations and *hui*; DHHL is the agency they exist
under and OHA is the grantmaker that pays them. Both are INVESTIGATE and both
are the highest-value remaining leads for this gap.

### 95 Alaska village corporations behind one CAPTCHA — **re-confirmed closed, two alternates found, one of them worth an hour**

`www.commerce.alaska.gov` returns **HTTP 403 with a DataDome interstitial to
BOTH the declared UA and a browser UA**, on `robots.txt`, on the bulk
`CorporationsDownload.CSV`, and on `/dcra/DCRAExternal/community`. The body
names `geo.captcha-delivery.com`. `KNOWN_ISSUES` A1 is independently confirmed.

* **`dcced.maps.arcgis.com`** — Alaska DCCED's ArcGIS Online organisation —
  answers 200, serves a robots.txt with no blocking directive, and hosts the
  DCRA Community Database, which names each community's ANCSA village
  corporation. **The right owner/group filter was not found**
  (`q=owner:DCCED_GIS` returned empty; the generic query returned Esri federal
  content). **INVESTIGATE, worth one more hour and not more.**
* **Wayback CDX** for the bulk file **timed out at 30 s and is UNMEASURED** —
  not a negative. `UNTAPPED_FREE_SOURCES` already records the `web.archive.org`
  host lock as stale; whoever takes it should run this one query.
* **OpenCorporates is a REJECT with the quote to prove it.** Its `robots.txt`
  disallows `/search`, `/data`, `/filings`, `/officers` and `/*?page=` for
  `User-agent: *` — every route that would enumerate a jurisdiction — and
  `/info/our-data` redirects to `/pricing/`.

### 116 BIE schools stale by construction — **closed by §1.2**, and two republishers rejected

`ed_crdc` refuses ClaudeBot and `anthropic-ai` by name and puts its download
directory off limits to everyone. `educationdata.urban.org` disallows `/api/`
to all robots — **and it is a republication of NCES CCD, so under
`ASSERTION_LAYER` it is the same evidence family as the CCD data `code/1081`
already loaded.** It could not corroborate anything and could not beat CCD's
edge. Both REJECT.

---

## 4. NEGATIVES THAT ARE WORTH AS MUCH AS THE POSITIVES

Each of these closes a question that was open in a Cedar document.

| what was open | now measured | evidence |
|---|---|---|
| `UNTAPPED_FREE_SOURCES` **G4**: GSA eLibrary *"reachable; not queried"* | **CLOSED as a negative.** `robots.txt` is three lines: `User-agent: *` / `Allow: /ElibMain/home.do` / `Disallow: /ElibMain/`. The publisher allows the landing page and disallows the entire application | `https://www.gsaelibrary.gsa.gov/robots.txt` |
| brief: *"FSRS"* | `www.fsrs.gov` **did not resolve** from this network, and it is redundant — FSRS data reaches Cedar through `api.usaspending.gov` as `fsrs_subawards`, 76,859 rows through 2026-08-03 | probe log |
| brief: *"IRS 990 e-file"* on AWS | bucket empty, 200 with `KeyCount=0` | §2 |
| brief: *"SAM.gov Entity Management public extracts"* | **not a new source — an unfinished one.** Cedar holds `SAM_GOV_API_KEY` and `code/67_sam_entity_harvest.py`; `START_HERE` item 6 names the role request (10/day → 1,000/day) as the blocker | `docs/API_KEYS.md` lines 24–25 |
| brief: *"BLS QCEW tribal ownership codes"* | **NOT ANSWERED.** The ownership-titles page returns 200 and its table was not extracted. Recording either answer would be inventing one. Note the upside is small: the pooled Form 5500 + OSHA measure already reaches **86%** of gaming tribes | `PUBLICATION_POLICY.md` coverage table |
| brief: *"ONRR beyond what is held"* | `revenuedata.doi.gov/downloads/` 200, robots allows all but `/patterns/`. **This is the production half of a source already CURRENT in the registry**, which `WHAT_IS_MISSING` labels `NOT_ACQUIRED` *from a source already held* — one extract, not a new relationship | probe log |

**Eleven candidates were guessed-path 404s and are recorded as UNRESOLVED, not
as absences** — `ok_exclusivity`, `wi_doa_gaming`, `ks_gaming`,
`nigc_tribe_list`, `nps_thpo_grants`, `doi_landbuyback`, `denali_commission`,
`hi_dhhl`, `nathpo`, `achp_e106`, `ca_charity_registry`. Where the publisher
offers an enumeration it was probed and is named in the CSV; where the sitemap
answered but was not walked, the row says so. Two hosts (`highways.dot.gov`,
`www.rd.usda.gov`) 403 **both** user agents including on `robots.txt` — an edge
filter, not a stated refusal.

---

## 5. WHAT THIS PASS DID *NOT* DO

Stated so the next agent does not read silence as coverage.

* **No bulk object was downloaded**, so no candidate is proved to *parse* — only
  to exist, be reachable, and have a stated grain.
* **Six ACQUIRE rows carry a measured row count; two do not.**
  `bie_schools_directory`'s 183 is **stated by the publisher**, not counted, and
  `biamaps_bia_arcgis` is a folder count, not a row count. The CSV says so.
* **`api.usaspending.gov` and `files.usaspending.gov` were not touched.**
  `code/1085_prime_psc_desc_repull.py pull` was live on this machine when this
  pass began — two PIDs, confirmed via `Win32_Process.CommandLine`, per
  `PULL_DISCIPLINE` rule 1, because `ps aux` cannot answer this on Windows —
  and had finished by the time it ended. Neither host was contacted either way.
* **No host lock was taken**, because no candidate was polled: every host got
  between one and six requests, once, with a 2-second gap, a declared UA and a
  90-minute run deadline. `MAX_PER_HOST = 6` is enforced in code.
* **Per-facility gaming revenue was not solved.** It stands at **11 of 787
  facilities (1.4%)** — of which only **7 are Indian-lands properties (0.9%)**,
  which is the honest headline `SEC_GAMING_FACILITY_REVENUE_BUILD_LOG.md`
  prints. Four state routes were probed; New York's tribal page
  answers 200 and was not parsed, Oklahoma's is **already on disk** as two HTML
  captures in `data/raw/external/gaming_official/`, Wisconsin's sitemap is 347
  bytes and is not a site index, Kansas was not enumerated. **The honest state
  is that no new per-facility revenue source was established.**
* **`federal-register`'s thin non-NAGPRA surface was scoped, not closed.** The
  best lead found is **ACHP**, which runs the Section 106 process Cedar holds
  twenty rows of; its digital library answers 200 (51,985 bytes) but
  `/sitemap.xml` 404s, so the enumeration route is unresolved.
* **The `$65.2B` unattributed contracting pile was not moved.** The two routes
  that would move it — SAM entity extracts and `cage.dla.mil` — are
  respectively an existing blocked key and **the owner's own adjudication
  method**, which an agent should not automate without a ruling.

---

## 6. RECOMMENDED ORDER, BY WHAT EACH UNBLOCKS

1. **`biamaps.geoplatform.gov`, mineral acreage first.** 249,165 tract rows
   against a dataset whose own gap register says it has revenue with no
   denominator. One API, no key, no robots restriction.
2. **BIE Schools Directory**, off the same host. It is the only measured route
   past the 2024-10-01 ceiling A4 describes, and it is 183 rows.
3. **USAC E-Rate `tribal_type`.** 53,847 publisher-flagged rows, public domain,
   and it is the discovery leg the selection doctrine says Cedar structurally
   lacks.
4. **NPPES API against the spine's `entity.state` / `entity.city` / legal
   name.** This is the one candidate that could take a corroboration count off
   zero, which `ASSERTION_LAYER` calls the highest-value work in the project.
5. **DHHL and OHA sitemaps, then the CDFI AMIS sitemap.** Three walks, all
   robots-clean, aimed at the two entity classes that are most undated.

Two things need the owner before anyone fetches them: **the HUD
`Content-Signal: ai-train=no,use=reference` wording**, and **whether the
Wayback route to NHOA's robots-disallowed member list is a different route or
the same refusal.** Both are appended to `review/OWNER_DECISION_QUEUE.md`
discipline as questions, not as proposals to proceed.
