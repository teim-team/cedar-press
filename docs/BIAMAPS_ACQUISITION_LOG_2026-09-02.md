# Acquisition log — the eight ACQUIRE sources, 2026-09-02

*Workstream `ACQUIRE-1119-1121`. Work order:
`docs/SOURCE_EXPLORATION_2026-09-02.md` and its `.csv`, which probed 57
candidates in ~200 requests and rated **8 ACQUIRE, 35 INVESTIGATE, 14
REJECT**. This log records what was acquired, what it joins to, what it
measurably closes, and the four places the survey was wrong. **Nothing was
committed.**

Scripts, all claimed atomically via `code/1050_preflight.py claim`:
`code/cedar_arcgis.py` (new shared client),
`code/1119_acquire_biamaps_arcgis.py`, `code/1120_acquire_usac_open_data.py`,
`code/1121_acquire_nppes_corroboration.py`.
Model decision: **ADR-028** in `docs/ARCHITECTURE_DECISIONS.md`.*

---

## THE SCOREBOARD

| # | source | rows acquired | new Cedar tables | feeds | gate |
|---|---|---:|---:|---|---|
| 1 | `biamaps.geoplatform.gov` — BIA ArcGIS, 6 layers | **250,284** | 6 | `natural-resources` (1) + `_entity_layer` (5) | `1119 verify` 37 checks, 0 failed |
| 2 | BIE Schools Directory | **0 — already on disk** | 0 | — | see **CORRECTION 1** |
| 3 | `opendata.usac.org` — E-Rate + RHC | **72,850** | 4 | `funding` | `1120 verify` 19 checks, 0 failed |
| 4 | CMS NPPES | **35,202** | 2 | `_entity_layer` → `1118` | `1121 verify` 12 checks, 0 failed |
| 5 | CDFI Fund AMIS | **0** | 0 | — | closed as a measured dead end, **CORRECTION 4** |

**Total new rows in `data/clean`: 358,336** across 12 tables, from 3 hosts,
in 840 HTTP requests. Every page hashed; every table's row count reconciled
against a **fresh** count taken *after* the last page.

---

## 1. `biamaps.geoplatform.gov` — the BIA's own ArcGIS server

`code/1119_acquire_biamaps_arcgis.py`. 148 requests, 76.5 MB, one host, 1.5 s
between requests, `robots.txt` 404 → not served → allowed for every one of
nine agent tokens (union check, not our own UA).

**Every count the survey stated was confirmed exactly**, against a live
`returnCountOnly` taken before *and* after paging:

| table | rows | survey said | feeds |
|---|---:|---:|---|
| `resource_bia_mineral_acreage_tracts.csv` | 249,165 | 249,165 ✅ | `natural-resources` |
| `bia_tribal_leaders_directory.csv` | 587 | 587 ✅ | `_entity_layer` |
| `bia_aian_national_lar.csv` | 335 | 335 ✅ | `_entity_layer` |
| `bia_offices.csv` | 93 | 93 ✅ | `_entity_layer` |
| `bia_pl102_477_plans.csv` | 84 | 84 ✅ | `_entity_layer` |
| `bia_ofa_petitioners.csv` | 20 | 20 ✅ | `_entity_layer` |
| **total** | **250,284** | **250,284** ✅ | |

Codebooks: `docs/codebooks/05q_bia_arcgis_registers.md` (the five entity
registers) and `docs/codebooks/12g_bia_mineral_acreage.md` (the acreage
table). Grain declared in `512`, dict `GRAIN_ACQUIRE`.

### How it joins, MEASURED — and the answer is uncomfortable

Naive name matching against `cedar_entity_spine.csv` (exact on
`canonical_name` or `fr_official_name`, then token-set with a short stoplist).
**No link table was written**; these are the measurements that say how much
work a real linkage is.

| table | join column | reaches a spine entity |
|---|---|---|
| `bia_pl102_477_plans` | `partner_name` (84) | **73 (87%)** — the 11 misses are consortia (`Tanana Chiefs Conference`, `Kawerak, Inc.`, `South Puget Intertribal Planning Agency`, `Central Council of Tlingit and Haida`), several of which the spine holds under another name |
| `bia_tribal_leaders_directory` | `tribefullname` (587 distinct) | **508 (87%)** — misses are FR parenthetical variants and cross-references |
| `bia_aian_national_lar` | `LARNAME` (335 distinct) | **219 (65%)** — and the 116 misses are mostly *correct*: `Allegany`, `Aquinnah`, `Annette Island` are land areas, not nations |
| `resource_bia_mineral_acreage_tracts` | `land_area_name` (495 distinct) | **184 (37%)** |
| `bia_ofa_petitioners` | `petitioner_name` (20) | **4 (20%)** — and **that is the point**, see below |

> ### ⚠ THE ACREAGE DENOMINATOR DOES NOT ARRIVE WITH A TRIBE KEY
> 184 of 495. The other 311 include boarding-school lands
> (`ALBUQUERQUE INDIAN SCHOOL - NM`), ANCSA areas (`AHTNA`, `ALEUT`), and
> public-domain allotments named for individuals (`AHPEATONE - OK`). **Do not
> manufacture the link with a name matcher.** `START_HERE.md` standing rule 1
> and the NAME_TRAPS lesson both apply, and a land area genuinely belonging
> to no single nation is a fact about the world, not a matching failure.
>
> **OPEN TASK, named so it is a task and not a silence:** a
> land-area-to-entity ruling. It is an adjudication (`elijah_ruling` class),
> not a computation, and it is what stands between this table and being a
> per-nation revenue denominator.

### What it measurably closes

**a. `natural-resources` #3 — "revenue with no denominator".**
`docs/WHAT_IS_MISSING.md` records that `resource_revenue.csv` is 87%
aggregate-suppressed by statute and has no base to divide by. This is
**70,290,363.9 acres of Indian trust and restricted-fee title across 494 land
areas and 39 states**, per tract, from the agency that holds the title. It
does not close the gap — see the tribe-key box — but it is the first time the
denominator exists on disk at all.

**A totalling fence was required and is in place.** Summing the `acres` column
naively overstates by **417,504.8 acres (0.60%)**, concentrated at **FORT HALL
(172,026)**, because 5,465 tracts are written twice, once `Trust` and once
`Restricted`, **with the identical acreage on both rows**. Fenced in
`docs/MONEY_TOTALLING_RULES.md` `<!-- BEGIN ACQUIRE-BIA-ACREAGE -->`.

**b. The recognition boundary gets a negative case, for the first time.**
`docs/ASSERTION_LAYER.md`, under *Where this is honestly weak*:
*"`entity.is_federally_recognized` has no negative case."*
`bia_ofa_petitioners.csv` is 20 petitioners before the Office of Federal
Acknowledgment, **16 of whom do not reach the spine**. A roster of only
positives cannot support any claim about a boundary; this is the other side.

**The table publishes no outcome**, so what a consumer may say is bounded:
*"petitioned for federal acknowledgment and does not appear on the FR
roster"* — yes. *"was refused"*, *"was denied"*, *"is not a tribe"* — no. The
codebook states this.

**c. 84 DATED public facts against the 545-entity stale tail.**
`docs/STALE_TAIL_CLOSURE_1081.md` leaves 545 entities with no dated public
record, and the SBA DSBS extract already on disk **cannot** close it because
it carries no date column (see CORRECTION 2). `bia_pl102_477_plans.csv`
carries `plan_start_date`, `plan_expiration_date` and `plan_renewal_date`,
100% populated, on 84 tribal and consortium plans — **73 of which reach a
spine entity today**. No Cedar source covered PL 102-477.

**d. The BIA facility register, which the brief named as likely unheld.** 93
offices with coordinates, type, region and URL.

**e. `bia_directory` gets its structured form.** Cedar reads the Tribal
Leaders Directory as HTML today. The feature service adds `biaregion`,
`biaagency`, `tribalcomponent`, `tribealternatename` (an alias source),
`dateelected`/`nextelection`, and **seven other agencies' regional
assignments for the same nation** — ANCSA, BLM, BOR, FWS, LCC, NPS, USGS —
a crosswalk nothing in Cedar holds. **It does not corroborate the FR**: it is
the same evidence family (ADR-028 §I1).

### Defects found in the publisher's own data, recorded not repaired

1. **`bia_offices.OFFICEID` is not unique.** `OFID0038` is carried by *both*
   `Salt River Agency` and `San Carlos Agency`. Joining on it merges two
   agencies. Key on `OBJECTID`.
2. **`resource_bia_mineral_acreage_tracts` has no natural key.** The obvious
   four-part key is 249,161 distinct of 249,165, and all four collisions are
   real: three tracts with two acreages under one number, and **FORT MOJAVE
   604 T 106 recorded once under AZ and once under CA** (the reservation
   straddles the line). No published column separates that pair, so **a
   per-state acreage total double-counts it.**
3. **Two `land_area_name` values are leaked internal keys** — `E|E|01|982`
   (elsewhere `SEALASKA`) and `P|P|04|183` (elsewhere `KOOTENAI`).
4. **`bia_offices` carries three columns whose value is the literal string
   `<Null>`**, not a blank — `ADDRESSID`, `POCEMAILADDRESS`, `POCMIDDLENAME`.
   Neither an SQL `IS NULL` nor a Python `== ""` finds them.
5. **Five `bia_offices` columns are 0% filled** (`REGION`, `AGENCY`,
   `CONTACTNAME`, `POCPREFIX`, `POCSUFFIX`). Written as served so the absence
   is visible.
6. **`bia_ofa_petitioners.state` holds full state names**, not USPS codes.
   Any join to a two-letter state column matches nothing, silently.
7. **`inactivated_date` is `0` on all 249,165 rows** — see ADR-028 §D3 for the
   1970-01-01 rendering this nearly shipped with.

---

## 2. USAC open data — `opendata.usac.org`

`code/1120_acquire_usac_open_data.py`. 12 requests, 121 MB, `Crawl-delay: 1`
honoured at 1.5 s. **Licence, verbatim from the asset metadata:
`license.name = "Public Domain"`, `licenseId = PUBLIC_DOMAIN`,
`attribution = "Universal Service Administrative Company"`** — stored in the
run manifest so the permission is auditable without re-fetching.

| table | rows | grain |
|---|---:|---|
| `usac_erate_tribal_commitments.csv` | **53,847** | Form 471 line item × recipient of service, `tribal_type IS NOT NULL` |
| `usac_erate_tribal_entities.csv` | **2,752** | one row per distinct recipient — the entity grain |
| `usac_rhc_hcp_directory.csv` | **11,142** | the full RHC provider universe (11,116 distinct providers) |
| `usac_rhc_native_candidate_lines.csv` | **5,109** | RHC lines whose provider name carries a Native token — **tier C candidates** |

Codebook: `docs/codebooks/03g_usac_universal_service.md`. Collection:
`funding` (pattern extended with `usac_` in `500`).

### What it measurably closes

**a. Cedar's first publisher-assigned TYPE FILTER leg.**
`docs/PULL_DISCIPLINE.md` measured that an identifier-seeded pull *"can never
discover an entity we do not already know"* and that **roughly three quarters
of the entity universe is invisible to one**. `tribal_type` is the leg that
finds unknowns, and USAC did the Native identification itself. The census
reconciles **exactly** to USAC's own `$group`: `Tribal School` 42,967 ·
`Tribal Library` 10,862 · `Tribal College/University Library (for public
use)` 17 · a comma-joined multi-value cell 1 → **53,847**.

**b. 2,752 tribal schools and libraries with funding years to 2026.**
`docs/KNOWN_ISSUES.md` **A4** says NCES CCD cannot make a BIE school look
fresh *by construction* — newest fips-59 collection year 2024, count date
2024-10-01, static 174-school universe. This is a different publisher with no
relationship to NCES, **2,752 entities**, years **2017–2026**. It is a funding
recipient list, not a school register, and it carries no NCES school number,
so the join is name + state — but it is a genuinely independent second
observation of a tribal school's existence, name and address, and Cedar had
none.

**c. $8.79B of federal universal-service money nothing in Cedar saw.**
USF money reaches Indian Country through the FCC mechanism, not USAspending.
The committed federal figure is
`post_discount_extended_eligible_line_item_costs` on `Funded` rows only:
**$8,791,223,114**.

> ### ⚠ TWO TOTALLING TRAPS, MEASURED, BOTH IN THE CODEBOOK
> **`pre_discount = post_discount + applicant_share`, exactly.** The three
> columns are one money in two parts; summing more than one double-counts.
>
> **8,358 of 53,847 rows are not committed money.**
> `form_471_frn_status_name`: `Funded` 45,489 · `Pending` 3,940 · `Cancelled`
> 3,909 · `Denied` 509. Summing all rows books **$11.97B** against a committed
> **$8.79B** — a **36% overstatement**, a third of it money that was denied or
> cancelled.
>
> **And 53,847 rows are 2,752 schools — 19.6×.** The entity count is done once,
> in the entities table.

**No federal identifier anywhere.** Measured across all 68 source columns:
no UEI, EIN or CAGE. Any spine link is name + state, i.e. a candidate.

---

## 3. CMS NPPES — the second independent source

`code/1121_acquire_nppes_corroboration.py`. One query per spine entity, 1,555
entities, name-seeded.

> ### The design decision, restated because it is the whole value
> **The query passes the NAME and nothing else.** NPPES accepts `state=` and
> `city=`; sending Cedar's own `state` would have raised the hit rate and made
> the output worthless, because a search seeded with our answer can only
> return records that agree with it. `ASSERTION_LAYER`'s evidence-lineage rule
> applies to a query parameter exactly as to a table.
>
> **`state_agrees = DISAGREE` is therefore reachable, and `verify` FAILS if
> the file contains none.** A corroboration source that can only ever agree is
> measuring itself.

**1,555 spine entities queried — all of them, no sampling. 406 returned at
least one hit; 1,149 returned none. 16,981 distinct NPIs retrieved in 680
requests.**

| table | rows |
|---|---:|
| `nppes_org_registrations.csv` | **16,981** — one row per NPI-2 organisation, deduplicated on `npi` |
| `nppes_spine_name_candidates.csv` | **18,221** — 17,072 candidate pairs + **1,149 `NOT_MATCHED` negatives** |

Negatives are rows: *attempted and found nothing* must be distinguishable
from *never attempted*, and `verify` asserts all 1,555 entities appear.
**1,149 of 1,555 matching nothing is correct** — an Alaska Native village
corporation, an ANCSA group corporation and a BIE school have no reason to
hold an NPI.

### ⚠ READ THE JACCARD BAND BEFORE THE AGREEMENT RATE

| band | pairs | spine entities | AGREE | DISAGREE | agreement |
|---|---:|---:|---:|---:|---:|
| all pairs | 17,072 | 406 | 3,994 | 13,057 | **23.4%** |
| jaccard ≥ 0.5 | 3,284 | 282 | 1,455 | 1,808 | 44.6% |
| **jaccard ≥ 0.8** | **644** | **76** | **603** | **20** | **96.8%** |

**The 23.4% headline is not a quality figure and must never be quoted as
one.** `CHEROKEE NATION*` returns 33 organisations, most of them somebody
else's; the raw pool is deliberately wide so the arbiter can see what was
rejected. **At a real name match the source agrees with Cedar 96.8% of the
time**, across 76 spine entities — mostly tribal health boards, clinics and
Urban Indian Organizations, which is exactly the population an HHS
enumeration can see.

### ⚠ AND THE 20 EXACT-NAME DISAGREEMENTS ARE THE MOST VALUABLE ROWS IN THE FILE

They are almost all **place-name collisions on single-word Alaska village
names**, and the state comparison is the only thing that catches them:

| spine entity | spine state | NPPES legal name | NPPES state |
|---|---|---|---|
| Circle | AK | `CIRCLE INC` | NC |
| Pilot Point | AK | `PILOT POINT LLC` | TX |
| Platinum | AK | `PLATINUM INC.` | CA |
| Solomon | AK | `SOLOMON LLC` | MN |
| Hoh | WA | `HOH, LLC` | OR |
| Pine Ridge School | SD | `PINE RIDGE SCHOOL, INC.` | VT |

**A pure name matcher would have booked every one of these as a match.**
This is the design decision paying for itself twice: because the query never
sent Cedar's `state`, the state column is free to refute. **For `1118`:
`state_agrees = DISAGREE` at high `name_token_jaccard` is a REFUTATION
signal, not a missing corroboration** — it is currently the only column in
Cedar that can tell a name match from a name collision without a human.

`city_agrees` is `NO_SPINE_VALUE` on **16,883 of 17,072** rows, because the
spine carries a city on only 229 of 1,555 entities. That is Cedar having
nothing to compare, **never** the two agreeing. Where Cedar did have one:
**118 AGREE, 71 DISAGREE.**

**Every row is tier C and nothing is attributed.** This script hands evidence
to `code/1118_corroboration_layer.py`, which is the consumer that arbitrates —
per the brief, it does not build a parallel layer.

**`authorized_official_*` is not written at all.** NPPES publishes a named
natural person and their direct telephone; Cedar needs the organisation, not
the person. The organisation's own `location_telephone` is kept.

### What it measurably closes

`START_HERE.md` item 0: *"across 8,975 single-valued facts, **0** have a
second source, **0** disagree, and **2** have more than one independent
evidence family."* NPPES is a **third** evidence family — HHS enumeration,
independent of Interior's FR roster and Treasury's BMF, and `KNOWN_ISSUES` A3
records that 258 Native Hawaiian entities return no IRS organisation at all.
This is the input that lets that count move off zero. **The move itself is
1118's to make.**

### One defect this pass caused and fixed

The first `pull` ran 875 of 1,555 entities and **died on
`UnicodeEncodeError` printing a spine name containing `ū`** — this console is
cp1252. Nothing was lost (`_state.json` checkpoints every 25 entities; the
resume began at 875), but **a progress line took down a network job.** Every
user-facing string now goes through an encode-safe `_p()`.

---

## CORRECTIONS TO THE SURVEY

*Each of these is a claim in `docs/SOURCE_EXPLORATION_2026-09-02.md` or its
CSV that measurement contradicts. Recorded so the next reader does not act on
the stale version — the failure mode this repo names as "numbers go stale in
place".*

### CORRECTION 1 — BIE Schools Directory is `ON_DISK_NOT_PROMOTED`, not ACQUIRE

The survey rates it **ACQUIRE** and ranks it **second by priority**, on the
reasoning that it is *"the only route identified that can beat 2024-10-01"*.
The reasoning is right. **The fetch already happened.**

```
data/raw/external/bie_uio/bie_schools_featureserver.json     187 features, 2026-08-06
data/staging/tribe_harvest/shard_g/raw/
        bie_schools_featureserver_2026-09-01.json            187 features, 2026-09-01
```

Fetched by `code/75_add_bie_schools_and_uios.py` from
`services1.arcgis.com/UxqqIfhng71wUT9x` — a different host from
`biamaps.geoplatform.gov`, serving the same application's data — and the spine
already holds **185 `BIE School` entities**. Note also that the file has
**187 features**, not the 183 the publisher's `og:description` states; the
survey's own CSV flags that 183 was *"stated by the publisher, not counted"*.

**Nothing was re-fetched.** The state is a promotion question (do the 187
features carry a fresher `as_of_date` than CCD's 2024-10-01 for the stale
BIE schools?), which belongs to the stale-tail workstream, not to an
acquisition.

**Why it matters beyond this row:** it is at least the fourth recorded
instance. `docs/AGENT_FIELD_GUIDE.md` §5 already says *"27 of the 39 ranked
absences are `ON_DISK_NOT_PROMOTED`"* and *"at least three sessions have
re-downloaded files that were already on this machine."* The survey ran ~200
network probes and **zero `ondisk` checks**. Recommendation in ADR-028 §I3:
`1111 report` should call `py -3 code/1050_preflight.py ondisk` for every row
before it may print ACQUIRE.

### CORRECTION 2 — the SBA 8(a) / DSBS register is not untried (confirmed)

The brief already carried this correction and it is confirmed on disk:
`data/raw/external/sba_dsbs_native_entities.csv`, **5,087 rows**, 442 Hawaii,
dated 2026-04-30, already loaded by `code/01_build_entity_spine.py`. State is
`ON_DISK_NOT_PROMOTED`. **It has no date column, so it cannot close the
`KNOWN_ISSUES` A3 dated-record question** — which is precisely the gap
`bia_pl102_477_plans.csv` now puts 84 dated rows into. **It was not
re-fetched.**

### CORRECTION 3 — RHC has no tribal type

`docs/SOURCE_EXPLORATION_2026-09-02.md` §1.3 lists Rural Health Care beside
the E-Rate file, and the CSV row `usac_rhc` gives the verdict reason
*"Same portal, same terms, one more extract."* The portal and terms match.
**The flag does not exist.** Measured on the live asset: the only categorical
is `filing_hcp_entity_type`, twelve values — `Consortium Of The Above`,
`Not-For-Profit Hospital`, `Rural Health Clinic`, `Community Health Center…`,
`Community Mental Health Center`, `Local Health Department Or Agency`,
`Dedicated Er Of Rural, For-Profit Hospital`, `Skilled Nursing Facility`,
`Not Available`, `Post-Secondary Educational Institution…`,
`Part-Time Eligible Entity` — **none of them tribal**.

The verdict survives (tribal and IHS clinics do draw RHC funds and no Cedar
source saw them); the *method* does not. This half is a **name sweep**, so:
the full 11,142-provider roster is held as a denominator, the 5,109 matched
lines are **tier C candidates** carrying the tokens that matched them, and
nothing is attributed.

### CORRECTION 4 — CDFI Fund AMIS: the sitemap was walked, and it dead-ends

The survey left AMIS as **INVESTIGATE** with *"the sitemap was not walked in
this pass, so no grain or row count is claimed"*. **It was walked. Here is
what is there.**

```
https://amis.cdfifund.gov/robots.txt              200  Allow: /   (confirmed verbatim)
https://amis.cdfifund.gov/s/sitemap.xml           200  -> 1 sitemap
https://amis.cdfifund.gov/s/sitemap-view-1.xml    200  -> exactly ONE <loc>
                                                       https://amis.cdfifund.gov/s/cims-public
https://amis.cdfifund.gov/OpportunityZones/s/...  200  -> exactly ONE <loc>
```

Both sitemaps resolve to a single URL each, and that URL is a **Salesforce
Lightning community** — client-rendered, no server-side content, no data in
the HTML. The CSP header names `cims-public.cdfifund.gov`, which was followed:
it is a **Vite SPA whose bundle references only ArcGIS basemaps and census
tract layers** (`2020_BEA_TRACTS`, `CT_2016_2020_NMTC`,
`CT_2011_2015_ERP`). CIMS is a **tract-eligibility mapper, not an institution
roster.** `www.cdfifund.gov/documents/data-releases` publishes NMTC releases
and no certified-CDFI list; the certification page links no spreadsheet.

**Verdict: the 26 stale Native CDFIs are not closed by AMIS, and the
enumeration route the survey hoped for does not exist at that host.** Two
routes remain and neither was attempted here: (a) the Salesforce Aura POST
endpoint behind the Lightning community — reverse-engineering an internal
API, which is a `TERMS-METHOD` question and an owner decision, not an
agent's; (b) asking the CDFI Fund, which publishes a contact address. **The
robots posture (`Allow: /`) is real and is not the constraint** — the
constraint is that there is nothing served to fetch.

---

## SOURCE REGISTRY ROWS TO ADD — a proposal, not an edit

`data/spine/cedar_source_registry.csv` is **generated by
`code/510_assertions.py`**, which the pass-3 ownership table assigns to the
integrator. This workstream did not touch it. The three `source_id` values
its tables carry are therefore **unregistered**, and these are the rows to add
to `LINEAGE_ROOTS` / the sources dict in `510`:

| `source_id` | `lineage_root_id` | `derives_from` | `tier_ceiling` | `authority_for` | lineage note |
|---|---|---|---|---|---|
| `bia_biamaps_arcgis` | `LR_BIA_DIRECTORY` | `LR_FEDERAL_REGISTER` | **B** | `entity.bia_region` · `entity.bia_agency` | **Same evidence family as the existing `bia_directory` entry.** Agreement with the FR about *which* nations exist is an echo, not corroboration. Genuinely new for the BIA's own regional assignment, the PL 102-477 plan dates, and the OFA petitioner list — **the last of which is a negative case the FR family structurally cannot produce.** |
| `usac_open_data` | `LR_USAC` *(new root)* | — | **A** | `entity.tribal_school_type` | FCC universal service administration. Unrelated to Interior, Treasury or SAM. The `tribal_type` flag is USAC's own determination on a filed Form 471. |
| `cms_nppes` | `LR_CMS_NPPES` *(new root)* | — | **A** | a health organisation's registered address | HHS provider enumeration, populated by a separate application under a separate authority. **This is the third evidence family `START_HERE.md` item 0 asks for.** |

---

## WHAT THIS PASS DID NOT DO

Stated so the next agent does not read silence as coverage.

* **No entity linkage was written.** The join rates above are measurements,
  not a link table. Linking `land_area_name` (37%) or `LARNAME` (65%) to the
  spine is an adjudication and a name matcher would be the containment defect
  with a new front door.
* **No assertions were written and `510` was not run.** `1121` hands evidence
  to `1118`; it adjudicates nothing.
* **The five unexamined biamaps layers were left** — `Hosted/EE_Permitting`,
  `Hosted/NEPA_Table` (74 rows), `Hosted/BIA_RGCs`,
  `Hosted/MRO_Tribes_Boundaries`, `Hosted/TribalGrasslands_NLCD` — plus
  `ParcelFabric`, `NIOGEMS` (the National Indian Oil and Gas Evaluation
  Management System, which is the obvious next target for
  `natural-resources`) and twelve regional folders. The survey named them and
  did not count them; neither did this pass.
* **HUD was not touched.** `www.hud.gov` serves
  `Content-Signal: search=yes,ai-train=no,use=reference` under a header
  invoking Article 4 of EU Directive 2019/790. That is a **use** restriction
  and `PUBLICATION_POLICY`'s `TERMS-METHOD` enumerates only three kinds. It
  is an owner decision and remains one.
* **NHOA's Wayback question was not touched.** Its `robots.txt` disallows
  `/nhoa-member-list.html` by name; whether a Wayback capture is a different
  route or the same refusal is a `TERMS-METHOD` owner decision.
* **`api.usaspending.gov` / `files.usaspending.gov` were not contacted**, in
  either direction. No host lock was taken on either.
* **The 35 INVESTIGATE rows were not re-probed** and the 14 REJECT rows were
  not touched, per the work order.

## Reproducing everything above

```
py -3 code/cedar_arcgis.py selftest                       # offline, no network
py -3 code/1119_acquire_biamaps_arcgis.py probe|pull|build|verify|selftest
py -3 code/1120_acquire_usac_open_data.py  probe|pull|build|verify|selftest
py -3 code/1121_acquire_nppes_corroboration.py probe|pull|build|verify|selftest
```

`build` is always zero-network. `verify` exits 1 on breach. `selftest` injects
a violation into a copy of the manifest, asserts `verify` exits 1, restores,
and asserts it exits 0 — because **a check that has never failed on purpose is
not known to work.**

Machine-readable summaries: `docs/biamaps_acquisition_1119.json`,
`docs/usac_acquisition_1120.json`, `docs/nppes_acquisition_1121.json`.
Per-request logs with URL, status, byte count and sha256:
`logs/1119_*.jsonl`, `logs/1120_*.jsonl`, `logs/1121_*.jsonl`.
