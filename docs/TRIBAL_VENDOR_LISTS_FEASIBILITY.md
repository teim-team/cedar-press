# Tribal vendor and certification lists — feasibility study, now a build

*Run 2026-08-26. Scripts `code/316`–`code/324`. Registry:
`review/tribal_vendor_list_registry_2026-08-26.csv`. Machine-readable payoff:
`docs/TRIBAL_VENDOR_LIST_PAYOFF.json`. Staged rows:
`data/staging/tribal_vendor_lists/`. Codebook fragment:
`docs/codebooks/02m_tribal_certification_layer.md`.*

> **STATUS 2026-08-26, second pass: the owner said BUILD IT, both options, and
> keep going. The study is now a build.** The roster went **30 → 62 entities**,
> **13 → 22 lists**, and the certification RULE is now its own first-class
> table with **11 of 14 programmes quoted verbatim from the governing
> ordinance**. Sections 1–11 below are the original 30-entity feasibility
> study and their numbers are preserved as written. **Section 12 carries the
> scale-up and supersedes any headline count above it.**

---

## THE ONE-PARAGRAPH ANSWER *(written at 30 entities; see §12 for the 62-entity numbers)*

**GO, with the value in a different place than the pitch suggested.** Thirteen
of thirty entities publish an ownership assertion — a 43% hit rate against a
sample deliberately stratified to include five entities Cedar Press holds
nothing for. But **only 3 of the 13 publish a joinable identifier**, and when
those three were tested against `prime_contracts.csv` all four sampled
identifiers came back **already attributed at tier A**. So this source will not
discover many new dollars. What it does is supply the thing Cedar Press is
most short of: **a leg that is not the firm.** The 13 publishing entities carry
**390 tier-B ledger rows riding on $41.10B of attributed prime obligations**,
including **37 rows whose method is literally `agent_research_one_leg`** — one
leg short of tier A, carrying $3.73B, and a tribal certification is that leg.
On the discovery side the honest number is small: **two roster entities produced
8 of the top 400 unattributed identifiers, worth $818.9M**, and a full
574-tribe sweep extrapolates to roughly **1–2% of the $65.24B universe.** Build
option B first. Option A, the certification registry, is worth building on the
pro shelf but it is a **~1,800-row dataset today and ~17,000–21,000 at 574, not
a 100,000-row one**, and its distinctiveness is the Wayback time series rather
than the current roster.

---

## 1. THE THIRTY, AND WHY EACH

Drawn from `data/spine/cedar_entity_spine.csv` (1,534 entities) so every row
keys to a real spine id. Priority order is the owner's: **lower 48 first, then
ANC regional corporations, then Alaska Native villages.** Contracting rank and
dollars are from `data/clean/contractor_ranking.csv` (283 ranked owners, ASRC
$25.17B down to entities with none).

### Lower 48 — 20

| # | spine id | entity | ST | rank | prime $ | why chosen |
|---:|---|---|---|---:|---:|---|
| 1 | `TRBF-NAVAJO-00` | Navajo Nation | AZ | 29 | $930M | Largest land base and population. The Navajo Business Opportunity Act runs a **statutory** certified-Navajo-owned list — the highest-value target in the study. |
| 2 | `TRBF-GILARV-00` | Gila River Indian Community | AZ | 168 | $0.9M | Large gaming revenue against near-zero contracting. Tests whether a tribe whose money is *not* federal still publishes. |
| 3 | `TRBF-CHKNAT-00` | Cherokee Nation | OK | 6 | $9.92B | Largest lower-48 federal contractor. If the best-resourced tribal government does not publish, few will. |
| 4 | `TRBF-CTWNAT-00` | Choctaw Nation of Oklahoma | OK | 65 | $240M | Big dollars, **zero tier-A UEI links** and 28 tier-B. The evidence-poor-at-scale case. |
| 5 | `TRBF-CSKTFR-00` | Confederated Salish & Kootenai | MT | 22 | $1.82B | $1.8B and **zero tier-A UEI links**. One of the oldest Indian-preference regimes in the country. |
| 6 | `TRBF-COLVLL-00` | Confederated Colville | WA | 87 | $73.6M | Long-standing TERO; large on-reservation construction workforce. |
| 7 | `TRBF-YAKAMA-00` | Yakama Nation | WA | 93 | $38.0M | TERO office; heavy on-reservation construction and agriculture — what a TERO list is *for*. |
| 8 | `TRBF-UMATLL-00` | Umatilla (CTUIR) | OR | 42 | $542M | A contracting tribe *and* an active employment-rights programme: both legs present. |
| 9 | `TRBF-MHATAT-00` | Three Affiliated Tribes (MHA) | ND | 31 | $889M | Bakken-era TERO with the largest oilfield certification volume of any tribe. |
| 10 | `TRBF-STNDRK-00` | Standing Rock Sioux | ND | 119 | $7.6M | TERO office, pipeline-era contractor scrutiny, large land base, modest dollars. |
| 11 | `TRBF-OGLALA-00` | Oglala Sioux | SD | 117 | $8.2M | One of the largest enrolled populations against small contracting dollars — the population stratum. |
| 12 | `TRBF-ONDAWI-00` | Oneida Nation (Wisconsin) | WI | 49 | $422M | Gaming *and* contracting, with a formal purchasing function. |
| 13 | `TRBF-LCORLS-00` | Lac Courte Oreilles | WI | — | $0 | **WE HOLD NOTHING.** No rank, no tier-A UEI. |
| 14 | `TRBF-MSBCTW-00` | Mississippi Band of Choctaw | MS | 69 | $208M | The Southeast's largest tribal industrial employer. |
| 15 | `TRBF-POARCH-00` | Poarch Band of Creek | AL | 34 | $812M | Only federally recognised tribe in Alabama; heavy 8(a) presence, where the ownership question actually bites. |
| 16 | `TRBF-ESTCHK-00` | Eastern Band of Cherokee | NC | 95 | $34.1M | Well-established TERO. Also tests `NAME_TRAPS` — "cherokee" is a trap token and this is a different nation from #3. |
| 17 | `TRBF-SNCNAT-00` | Seneca Nation of Indians | NY | 21 | $1.84B | Large Northeast contractor with a TERO commission. |
| 18 | `TRBF-SRMHWK-00` | Saint Regis Mohawk | NY | 270 | $3,500 | A border reservation with essentially no federal contracting. Tests whether publication tracks contracting at all. |
| 19 | `TRBF-PCHNGA-00` | Pechanga Band | CA | — | $0 | **WE HOLD NOTHING.** Among the largest gaming revenues in the country; federally invisible. California is the densest tribal jurisdiction in the study. |
| 20 | `TRBF-ELYTNV-00` | Ely Shoshone | NV | — | $0 | **WE HOLD ABSOLUTELY NOTHING** — `n_uei_tierA=0`, `n_uei_tierB=0`, `n_cage=0`, `n_ein=0`. The floor case. |

### ANC regional corporations — 5

| # | spine id | entity | rank | prime $ | why chosen |
|---:|---|---|---:|---:|---|
| 21 | `ANRC-ARCSLO-00` | Arctic Slope Regional | 1 | $25.17B | Largest Native federal contractor there is, 57 operating companies. |
| 22 | `ANRC-NANARC-00` | NANA Regional | 2 | $19.89B | Same test on a second large corporation, so one corporation's habit is not generalised into a rule. |
| 23 | `ANRC-CALSTA-00` | Calista | 7 | $8.83B | Largest shareholder base of any regional; the hardest hierarchy in the spine sits under it. |
| 24 | `ANRC-DOYONL-00` | Doyon, Limited | 24 | $1.61B | Mid-scale, with a distinct government-services grouping. |
| 25 | `ANRC-SEALSK-00` | Sealaska | 174 | $0.70M | **A very large shareholder base with almost no federal contracting.** Tests whether publication tracks contracting dollars or shareholder obligation. |

### Alaska Native villages — 5

| # | spine id | entity | rank | prime $ | why chosen |
|---:|---|---|---:|---:|---|
| 26 | `AKNF-CHNEGA-00-…` | Chenega (IRA Council) | 41 | $549M | Village government at rank 41 beside Chenega Corporation at rank 4 ($10.64B) — the clearest village/corporation split in the data. |
| 27 | `AKNF-INPTBW-00-ARCSLO` | Native Village of Barrow | 216 | $151K | Beside Ukpeaġvik Iñupiat Corporation at rank 8 ($5.76B). Same split, opposite proportions. |
| 28 | `AKNF-WAINWT-00-ARCSLO` | Native Village of Wainwright | 122 | $6.7M | 35 tier-A UEI links on a tiny village — unusually well identified. Beside Olgoonik, rank 25. |
| 29 | `AKNF-KTZBUE-00-…` | Native Village of Kotzebue | — | $0 | **WE HOLD NOTHING.** NANA-region hub village. |
| 30 | `AKNF-EKLTNA-00-CKINLT` | Native Village of Eklutna | — | $0 | **WE HOLD NOTHING.** Anchorage-adjacent, so the village most likely to have a real web presence — which makes a null here informative rather than a connectivity artefact. |

**Geographic coverage:** Southwest 2 · Oklahoma 2 · Northwest 4 · Plains 3 ·
Great Lakes 2 · Southeast 3 · Northeast 2 · California 1 · Great Basin 1 ·
Alaska 10. **Five entities we hold nothing for.**

**Where the sample is thin, stated rather than hidden:** one California entity
where California holds 129 spine entities, and no Pueblo other than through
Navajo. A second California tribe and one Rio Grande Pueblo are the first two
additions if the sample is extended.

---

## 2. HOW DISCOVERY ACTUALLY RAN — this bounds every negative below

In all four parallel discovery passes the **WebSearch budget was exhausted
before the first call**, and DuckDuckGo, Brave and Mojeek all refused (CAPTCHA
/ HTTP 429 / HTTP 403). Discovery therefore ran by **direct navigation from
known official domains, each site's own on-site search, and `sitemap.xml` /
`robots.txt` enumeration.**

That method is gentler on small tribal servers, and it found 13 lists. It also
means:

> **A `NO_LIST_FOUND` here means "not published on the entity's own site as at
> 2026-08-26". That is a weaker claim than "does not exist."** A list on a
> third-party host — a TERO consortium page, a regional nonprofit, a state DBE
> crossover — would have been missed.

This project has twice reversed a "documented dead end" that was one entity's
behaviour generalised into a rule about a source. That is not repeated here:
every `NO_LIST_FOUND` row in the registry carries the exact queries and paths
tried in its `searched` column, so the next pass extends the search instead of
inheriting the conclusion.

**Ethics, recorded as fact:**

- No login, paywall or access control was bypassed. The Oneida WP REST route
  answered 401 and was not worked around; NANAtkut, mySealaska, Eklutna
  `/members` and Beacon Bid were not probed.
- **`elyshoshonetribe.com` names `ClaudeBot` and `anthropic-ai` in robots.txt
  under an explicit Disallow.** Crawling stopped on discovery, and the host is
  `wayback_priority = EXCLUDED`: an origin's stated refusal of this agent is
  not routed around by fetching the same content from an archive.
- **`colvilletribes.com` also names `anthropic-ai` and `ClaudeBot`** but groups
  them with `User-agent: *` with no blanket disallow, and the TERO paths are
  permitted. That is an expressed preference, not a technical prohibition, and
  it is recorded as a reason to *ask before publishing*, not a licence to
  ignore.
- `cskt.org` sets `Crawl-delay: 10`. `choctawnation.com` disallows `/pdfs/`.
  Both honoured.
- Three hosts — `kotzebueira.org`, `nana.com`, `olgoonik.com` — answer HTTP 403
  to an automated client **on every path including `robots.txt`**. That is a
  WAF, not a robots disallow and not a login. **Their terms could not be read,
  so their terms status is `NOT_CHECKED`, not `SILENT` — an unreadable term is
  not an absent one**, and these are recorded as `NOT_CHECKED`, never as
  negatives.

---

## 3. THE THIRTY VERDICTS

**Product 1 — CERTIFICATION (ownership).** This is what the study searched for.

| verdict | n |
|---|---:|
| `LIST_FOUND_HTML` | 6 |
| `LIST_FOUND_PDF` | 5 |
| `LIST_FOUND_MACHINE_READABLE` | 2 |
| `LIST_REFERENCED_NOT_PUBLISHED` | 1 |
| `LIST_BEHIND_LOGIN` | 1 |
| `NO_LIST_FOUND` | 14 |
| `SITE_UNREACHABLE` | 1 |

**13 lists found. All 13 are ownership assertions.** Zero were general vendor
lists misread as certifications.

| entity | verdict | type | entries | joinable id? | cadence |
|---|---|---|---:|---|---|
| Navajo Nation | `LIST_FOUND_PDF` | TERO | 346 | no | **monthly, by statute** |
| Cherokee Nation | `LIST_FOUND_HTML` | TERO | ~700 *(their claim)* | no | not stated |
| CSKT | `LIST_FOUND_PDF` | TERO | 118 | no | annual per-firm recert |
| Colville | `LIST_FOUND_PDF` | TERO | 37–40 | no | not stated |
| Umatilla (CTUIR) | `LIST_FOUND_MACHINE_READABLE` | TERO | 14 | no | 2-year certificates |
| MHA Nation | `LIST_FOUND_MACHINE_READABLE` | TERO | 136 | no | date-stamped, ~monthly |
| Oneida (WI) | `LIST_FOUND_HTML` | TERO | *unverified* | no | **weekly, stated** |
| Poarch Creek | `LIST_FOUND_PDF` | TERO | 40–55 | no | dated-list rule |
| Eastern Band Cherokee | `LIST_FOUND_PDF` | TERO | ~80 | no | bimonthly |
| ASRC | `LIST_FOUND_HTML` | subsidiary directory | ~46 | **UEI + CAGE + DUNS** | not stated |
| NANA | `LIST_FOUND_HTML` | subsidiary directory | ~55 + 8 | **UEI + CAGE + DUNS** | not stated |
| Calista | `LIST_FOUND_HTML` | shareholder-owned + subsidiary | 150 + 40 | no | rolling |
| Doyon | `LIST_FOUND_HTML` | subsidiary directory | ~15 | **UEI + CAGE** *(in capability-statement PDFs)* | not stated |

**Roughly 1,800 harvestable records today**, of which the Oneida count is
unknown and several are the authority's own claim rather than an enumeration —
the registry's `entry_count_is_verified` column says which.

### The seventeen that did not produce a list

| entity | verdict | what is actually true |
|---|---|---|
| Gila River | `NO_LIST_FOUND` | No TERO anywhere on the site map, department tree or on-site search. Business licence = **blank forms only**, no registry. |
| Yakama | `NO_LIST_FOUND` | **TERO exists and operates**; publishes the ordinance and six blank forms, never a roster. The "Indian Preference Application" proves a list exists internally. |
| Standing Rock | `NO_LIST_FOUND` | TERO is a phone number in the programme directory. The ordinance *is* published as Title XXX. |
| Oglala Sioux | `NO_LIST_FOUND` | TERO listed with a phone number, no department page. |
| Lac Courte Oreilles | `NO_LIST_FOUND` | No TERO, no list, no licence registry. `?s=TERO` returned two **false positives** — "Honor the Earth" pageant pages matching the letter string. |
| Mississippi Choctaw | `NO_LIST_FOUND` | Tribal code fully published, **38 titles, no TERO title and no Indian-preference contracting title.** |
| Saint Regis Mohawk | `NO_LIST_FOUND` | No TERO at all — zero sitemap hits for "tero". Published ownership = 2 tribal enterprises. |
| Pechanga | `NO_LIST_FOUND` | Real purchasing department, zero Indian-preference apparatus. Procurement outsourced June 2026 to Beacon Bid. **Not `LIST_BEHIND_LOGIN`** — nothing indicates a certified-ownership list sits behind it. |
| Ely Shoshone | `NO_LIST_FOUND` | 10 departments, none commercial. Crawl stopped at robots.txt. |
| Sealaska | `NO_LIST_FOUND` | **The hypothesis the roster was built to test, confirmed.** Largest shareholder base, near-zero contracting, and **no subsidiary directory at all.** |
| NV Barrow | `NO_LIST_FOUND` | Real, well-maintained 22-page site, **exhaustively enumerated**; none of it is a business list. |
| NV Eklutna | `NO_LIST_FOUND` | Real 34-page site, exhaustively enumerated; economic development is entirely one gaming-hall project. |
| NV Wainwright | `NO_LIST_FOUND` | No village-government web presence exists; the borough's own community page cannot supply one. |
| Chenega IRA Council | `NO_LIST_FOUND` | The **village government** has no site (`chenega.org`, `chenegairacouncil.org` both NXDOMAIN). The **corporation** publishes ~50 operating companies across four microsites. |
| Seneca Nation | `LIST_REFERENCED_NOT_PUBLISHED` | **The crispest case in the study.** The TERO Ordinance mandates certification with graded tiers — "100% Seneca", "100% Indian-Majority Seneca", "Majority Seneca", plus general Commission-certified 51%+ Indian-owned firms. **A register demonstrably exists. None of it is published.** A records request to the Commission is the route. |
| Choctaw Nation OK | `LIST_BEHIND_LOGIN` | See §4 — reclassified by the archive. |
| NV Kotzebue | `SITE_UNREACHABLE` | HTTP 403 on every path including robots.txt. **The host exists and answers.** Not evidence of absence. |

---

## 4. THE ARCHIVE FINDING THAT CHANGED A VERDICT — and the rule it earns

Choctaw Nation's live Commerce page links
`https://preferredsuppliers.choctawnation.com/`, a programme for "qualified
Choctaw tribal member-owned business enterprises." **That host is NXDOMAIN on
two independent resolvers.** It read as a broken link on a live government
page — the highest-value archive recovery in the lower 48, a certification
list that might exist *only* in Wayback.

The CDX enumeration answered it, and the answer is no. **527 archived URLs,
2014-08-23 to 2025-05-24.** The 2023-07-07 capture enumerates:

```
/api/account/register      /api/account/resetpassword   /api/account/userinfo
/api/account/forgotpassword                             /api/account/changepassword
/api/suppliers             /api/supplierprofile/        /api/owners
/api/ownershiproles        /api/macros/Minority
```

**It was a registered-account application, not a published list.** The archive
holds the *route names*; the payload was gated.

> ### WAYBACK IS NOT A ROUTE AROUND A LOGIN.
> A directory a tribe put behind an account is not ours to take from an archive
> either. `LIST_BEHIND_LOGIN` means stop, and it means stop in the archive too.

Dated strictly, as the standing rule requires: **the account gate is what the
2023-07-07 capture shows.** A 2014-08-23 capture returns 200 on the root and
its state is *unknown*. A 2023 snapshot cannot testify about 2014 any more
than it can about 2026. The entity is now `wayback_priority = EXCLUDED` with
the reason recorded in the registry.

**This is also the study's best argument that the CDX leg is worth running.**
It cost one query and it converted a promising target into a closed one before
anybody spent a day on it.

---

## 5. WAYBACK AS A FEATURE, NOT A FALLBACK

The owner's framing is the right one: the archive is for **change over time**,
with currency as the floor requirement. A longitudinal record of tribal
business certification — who was certified when, who entered, who lapsed — does
not exist anywhere.

The CDX sweep (`code/317`, one stream, ≥5s gap, 30→480s backoff, 2h
`RUN_DEADLINE`, resumable — it skips any host already on disk) confirms the
panel is there.

**On the host lock, because the brief's description of it was itself stale.**
The task brief recorded `logs/_HOSTLOCK_web.archive.org.json` as stale with
`active: true` and PID 7420 dead since 2026-08-07, and authorised a takeover.
**What was actually on disk was cleaner than that:** `active: false`, claimed
by `code/213_cdx_targeted_nm_az_documents.py` (pid 26476) and **released at
23:08:38Z with `note: "213 targeted CDX complete"`.** A later agent had already
taken it over from `211` and closed it properly. So no forcible takeover was
needed; `317` claimed a free lock and recorded
`took_over_from: 213 … took_over_reason: prior lock already released at
2026-08-26T23:08:38Z`. *A stale note about a stale lock is still a stale note —
read the file, not the description of the file.*

| host | archived URLs | interesting | span | complete |
|---|---:|---:|---|---|
| `cherokeetero.com` | 4,357 | 4,357 | 2009-03 → 2026-05 | ✔ |
| `www.cherokeebids.org` | 6,000 *(at limit)* | 3,427 | 2005-12 → 2026-06 | — |
| `mhatero.com` | 1,208 | 1,208 | 2009-02 → 2026-08 | ✔ |
| `preferredsuppliers.choctawnation.com` | 527 | 527 | 2014-08 → 2025-05 | ✔ |
| `onlr.navajo-nsn.gov` | 451 | 451 | 2012-05 → 2026-08 | ✔ |
| `ctuir.org` | 6,000 *(at limit)* | 199 | 2009-06 → 2026-08 | — |
| `www.colvilletribes.com` | 6,000 *(at limit)* | 132 | 2000-10 → 2026-07 | — |
| `navajoeconomy.org` | 1,741 | 124 | 2020-08 → 2026-08 | ✔ |
| `cskt.org` | 6,000 *(at limit)* | 112 | 1999-09 → 2026-08 | — |
| `standingrock.org` | 6,000 *(at limit)* | 83 | 2000-08 → 2026-08 | — |
| `yakama.com` | 6,000 *(at limit)* | 48 | 2002-11 → 2026-08 | — |
| `www.navajo-nsn.gov` | 6,000 *(at limit)* | 48 | 2010-10 → 2026-06 | — |
| *…sweep continuing* | | | | |

**Sweep state at time of writing: 21 of 49 hosts enumerated, 7 complete, 10,857 interesting archived objects identified.** The run is resumable and skips any host already on disk, so a later pass finishes it rather than restarting. Hosts still `NOT_CHECKED` are honestly `NOT_CHECKED`.

*"At limit" hosts are recorded `complete = false` and are **NOT marked done** —
a per-unit budget that truncates and then marks COMPLETE is the silent ceiling
that cost this project four FERC dockets. Each artefact records
`rows_retrieved` against `source_reported_total` and `stopped_on_clock`. The
fix for these is a **narrowed `url` prefix, not a bigger limit.**

### The panel is real, and here is the evidence rather than the assertion

- **MHA TERO: 303 archived PDF/XLSX/CSV objects, 2009 → 2026** — 20 in 2009,
  48 in 2011, 26 in 2015, 35 in 2016, 48 in 2022, 35 in 2025, 49 in 2026, with
  a **gap across 2018–2021** that must be stated rather than interpolated. That
  is a decade-and-a-half of certified-contractor vintages for the single
  largest oilfield TERO in the country. **Caveat:** the filenames are opaque
  CMS attachment ids (`/attachment/cms/AXT_14_10B61.pdf`), so which list each
  object is cannot be told from the path — every one needs opening.
- **CTUIR: the archive holds a list the live site no longer has, at a path a
  live crawl cannot reach.** `ctuir.org/human-resources/2018-certified-indian-
  owned-business-directory` captured **2019-08-19**; the directory then lived
  under `/departments/human-resources/tero/` through 2023 and sits under
  `/departments/workforce-development/tero/` today. **Three different paths,
  one dataset.** This is the case the CDX API exists for.
- **Colville: `contractors_2015.php` captured 2015-06-01**, plus TERO objects
  in 2012, 2014, 2016, 2017, 2019, 2021, 2022, 2023, 2025 and 2026 — an
  eleven-year contractor series on a site that has since moved to Squarespace.
- **Cherokee's TERO directory host goes back to 2009-03**; `cskt.org` to
  **1999-09**.

**Navajo is the only entity that could support a genuine *monthly* panel**: a
statutory monthly cadence on a `/wp-content/uploads/YYYY/MM/` path, plus a
2012-onward Office of Navajo Labor Relations subdomain. And **EBCI's list
carries a stable tribal vendor number** — the only identifier in the study that
makes a time series joinable *to itself* across vintages, which is what turns a
stack of snapshots into an entry/exit series rather than a stack of snapshots.

The schema is built for this from the first row — `capture_date` on
everything, `first_seen` / `last_seen` per firm-authority pair, and a
`certification_status` vocabulary in which a single capture can only support
`ASSERTED_AS_OF_CAPTURE`. `LAPSED_BY_CAPTURE` requires two captures.

---

## 6. THE MEASURED PAYOFF

### 6a. The universe being addressed

Measured directly from `data/clean/prime_contracts.csv`, 1,217,768 rows:

| | |
|---|---:|
| unattributed rows (`attributed_flag = 0`) | **328,906** |
| unattributed identifiers | **9,385** |
| unattributed obligations | **$65.24B** |
| top 400 identifiers by dollars | $47.63B (73.0%) |

*The reconciliation tool's "top 400 clusters, $35.81B" is a **different unit** —
9,385 identifiers collapse to 8,876 clusters and 507 already-ruled clusters are
suppressed before a human sees them. Do not reconcile the two by adjusting
either.*

**The reachability split is the most important number in this document:**

| slice of the unattributed universe | identifiers | share | dollars |
|---|---:|---:|---:|
| carries any Native-specific flag | 2,550 | 27.2% | $48.73B |
| carries `american_indian_owned` self-cert | 408 | 4.3% | $3.79B |
| carries Buy Indian | 720 | 7.7% | $4.62B |
| **carries NO flag at all** | **6,835** | **72.8%** | **$16.51B** |
| sits in a state a roster entity occupies | 4,927 | 52.5% | $29.95B |

**The no-flag block is what a certification list is for.** Those 6,835
identifiers are invisible to every flag-based discovery route Cedar Press has,
so a third-party ownership assertion is the only evidence that can reach them.

### 6b. Option B — the evidence layer. This is where the value is.

Tier A requires *a leg that is not the firm*. A tribal government certifying a
business **is** a third party with authority over the question.

Across the **13 publishing entities**, the identifier ledger holds:

| tier-B method | ledger ids | prime rows | prime $ |
|---|---:|---:|---:|
| `cross_dataset_propagation:contracting` | 158 | 79,328 | **$33.690B** |
| `agent_research_one_leg` | **37** | 9,374 | **$3.734B** |
| `cluster_v3` | 77 | 10,037 | $3.567B |
| `need_v6` | 66 | 313 | $0.108B |
| `cross_dataset_propagation:funding` | 46 | 14 | $0.000B |
| `sam_namematch_2026_05_06` | 6 | 1 | $0.000B |
| **total tier B** | **390** | | **$41.10B** |

> **`agent_research_one_leg` is the sharpest target in the whole study.** The
> method name says exactly what is wrong: one leg short. Thirty-seven
> identifiers, $3.73B, and the missing leg is a tribal certification that
> thirteen of these entities already publish.

`need_v6` is the project's own **6.5%-accurate** method. Sixty-six of those
rows sit on publishing entities, so a certification either confirms or refutes
them cheaply — and refutation is as valuable as confirmation here.

By contrast the 17 non-publishing entities carry 281 tier-B rows on $15.27B,
which no amount of sweeping will reach from this source.

### 6c. Option A — the certification registry. Real, and smaller than it looks.

**The joinability test, run rather than assumed.** Three of thirteen lists
publish a UEI or CAGE. Four identifiers read directly off the certifying
party's own page were tested against `prime_contracts.csv`:

| firm | identifier | source | prime rows | $ | current state |
|---|---|---|---:|---:|---|
| Doyon Project Services | `F9M5KXFBC8N3` | Doyon capability statement | 799 | $363.5M | **already tier A** |
| ASRC Federal NetCentric | `T65LCYKJCW58` | ASRC Federal page | 1,039 | $661.3M | **already tier A** |
| ASRC Federal Holding (parent) | `VYN3SB8H8BL7` | same page | 2 | $30.5K | **already tier A** |
| Nakuuruq Solutions | `FZYKN78D9LJ2` | Akima opco page | 1,327 | $259.3M | **already tier A** |

**Four of four join perfectly. Four of four were already attributed.**
`value_added = INDEPENDENT_CORROBORATION` on all four, `NEW_ATTRIBUTION` on
none.

That is the honest headline for option A: **at the top of the distribution
this source confirms rather than discovers.** It is not nothing — the
reconciliation tool records that tier A requires a non-firm leg and that
correctly typing the SAM mirrors (govcb, opengovus, Buzzfile, LinkedIn) moved
tier A from **39 to 18**. A parent corporation publishing its subsidiary's UEI
*is* the missing venue. But it does not move the $65.24B.

**Where option A does reach the unattributed universe**, tested by name stem
across the five ANC regionals and the village corporations beside them:

| name stem | unattributed ids | $ |
|---|---:|---:|
| `brice` (Calista) | 9 | $636.2M |
| `asrc` | 7 | $225.8M |
| `uic` | 3 | $22.8M |
| `akima` | 2 | $1.6M |
| `tunista` (Calista) | 2 | $11.1M |
| `qayaq` (UIC) | 1 | $10.5M |
| `petrochem` (ASRC Industrial) | 1 | $0.006M |
| **total** | **25** | **$908.0M** |

**These are CANDIDATES, not links.** They come from a name stem, and one of the
eight stems tested demonstrated the trap in a single row: `nana` matched
**`PANANA DELENA` (OK)**, which is not NANA. `NAME_TRAPS` holds 51 tokens for
exactly this reason, and every one of these 25 goes to the review queue with
`join_outcome = CANDIDATE_ONLY_NO_IDENTIFIER`, never to the ledger.

**Against the top 400 specifically — the sharpest single number in the study.**
Eight of the 400 largest unattributed identifiers, carrying **$818.9M**, are
candidates traceable to just **two of the thirty** roster entities:

| unattributed identifier | $ | FY span | family |
|---|---:|---|---|
| `BRICE TURNAGAIN JV LLC` | $176.7M | 2022 | Calista |
| `BRICE CIVIL CONSTRUCTORS, INC.` | $161.8M | 2018–22 | Calista |
| `BRICE ENGINEERING, LLC` | $137.0M | 2017–22 | Calista |
| `ASRC CONSTRUCTORS, INC` | $116.2M | 2003–10 | ASRC |
| `ASRC CIVIL CONSTRUCTION, LLC` | $74.1M | 2008–22 | ASRC |
| `BRICE BUILDERS, LLC` | $59.6M | 2019–22 | Calista |
| `BRICE-AECOM JV1` | $51.0M | 2018–22 | Calista |
| `BRICE SOLUTIONS, LLC` | $42.6M | 2021–22 | ASRC/Calista |

**Read this carefully before treating it as $818.9M of resolution.** Two of the
eight are **joint ventures** (`BRICE-AECOM JV1`, `BRICE TURNAGAIN JV LLC`,
$227.7M between them) and a JV is part-owned by construction — the ledger's
`joint_ownership_flag` exists for exactly this and a JV must never be
attributed wholesale to one parent. And every one of the eight is a name-stem
candidate, not a key join, because **neither Calista's `/our-businesses/` page
nor `/federal-contracting/` publishes a UEI or CAGE** — Calista is
identifier-poor precisely where NANA and ASRC are identifier-rich.

What this shows is where the value sits: **not in confirming the giants, whose
identifiers are already tier A, but in the second rank of operating companies
and JVs that the parent names and the federal data does not connect.** Two
entities produced eight top-400 candidates. That is the number to extrapolate
from, and it is the reason the answer is GO rather than NO.

### 6d. Extrapolation to 574 tribes — with the assumption stated

| | |
|---|---:|
| roster checked | 30 / 30 |
| ownership lists found | 13 (43.3%) |
| lists carrying a joinable identifier | 3 (10.0%) |
| **projected ownership lists at 574** | **249** |
| projected joinable lists at 574 | 57 |

> **THE ASSUMPTION, and it matters more than the number.** The roster was
> stratified to **over-sample the entities most likely to publish** — large
> contractors, known TERO offices, and the ANCSA corporations with the most
> operating companies. It also deliberately includes five entities we hold
> nothing for, all five of which returned nothing. **A straight rate applied to
> 574 is an UPPER BOUND, not a central estimate.**

Two independent signals say to halve it:

1. **Publication tracks contracting intensity, not size or population.**
   Sealaska — the largest shareholder base of any ANCSA regional, rank 174 in
   contracting — publishes nothing. Doyon and Chenega, the heavy federal
   contractors, publish structured per-company directories, because those pages
   are business-development assets aimed at contracting officers. The 574
   includes several hundred tribes with no federal contracting at all.
2. **Four of the lower-48 negatives have a working TERO that simply does not
   publish** (Yakama, Standing Rock, Oglala, and Seneca by ordinance). The
   binding constraint is publication capacity, and it is worse in the tail than
   in this sample.

**Central estimate: ~120–150 published ownership lists across 574, of which
~25–35 carry a joinable identifier.** At the observed average of ~140 entries
per list, that is a **certification registry of roughly 17,000–21,000 rows**,
concentrated in the tribes that already contract.

**Dollars a full sweep would plausibly RESOLVE, and the arithmetic behind the
number.** Two roster entities produced **8 top-400 candidates worth $818.9M**;
five ANC regionals plus the village corporations beside them produced **25
candidates worth $908.0M** in total. Discount that:

- **~30% is joint ventures** ($227.7M of the top-400 set), which a parent
  directory cannot resolve outright.
- **All 25 are name-stem candidates**, and the reconciliation queue's own
  confidence work says most such cards sit under 20%. Assume a **50–70%
  survival rate** through review.
- The lower-48 TERO lists carry **no identifiers at all** and their firms are
  small — 346 Navajo entries against $34.5M of tier-B exposure. They will
  produce many candidates and few large ones.
- Alaska is where the dollars are and Alaska is **10 of the 30 here** — a full
  574-tribe sweep dilutes toward the lower 48, not toward more Alaska.

**Central estimate for a full 574-tribe sweep: $1.5B–$3B of unattributed
obligations reachable as candidates, of which perhaps half survive review.
Call it $0.75B–$1.5B resolved, against a $65.24B universe — roughly 1–2%.**

**Say that plainly: this source does not solve the discovery gap.** It is a
1–2% instrument on discovery. The tens of billions are on the *corroboration*
side — $41.10B of tier-B attributions on the 13 publishing entities that a
certification leg could firm up — and that is a different and better argument
for building it.

---

## 7. THREE PRODUCTS, STRICTLY TYPED

The registry types every list into exactly one of three, and never a row that
is ambiguous between them. **Conflating a vendor list with a certification list
is the single failure mode that would discredit all three.**

### Product 1 — CERTIFICATION (ownership). **GO.**
Covered above. 13 of 30. This is the priority.

### Product 2 — "DOES BUSINESS WITH A TRIBE" (relationship). **GO, but it needs its own sweep.**

A general vendor or supplier list is a **bad ownership claim and a good
relationship claim**: it says where tribal procurement dollars actually go.
Nobody publishes this as a dataset.

**What this pass found — incidentally, while looking for something else:**

| entity | verdict | what |
|---|---|---|
| MHA Nation | `LIST_FOUND_MACHINE_READABLE` | **Seven vendor-type lists** beside the certified one, on the same page and not the same thing: Approved Oilfield Vendors, General Contractors, Prime General, Prime Oilfield, Consultants, Subs w/ DOT Exemption, Suppliers. |
| Colville | `LIST_REFERENCED_NOT_PUBLISHED` | A **Small Works Roster** among 16+ TERO downloads. A small works roster is a bidders list — product 2, not product 1. |
| Choctaw OK | `LIST_REFERENCED_NOT_PUBLISHED` | The dead portal straddles 1 and 2 and resolves as neither. |
| Cherokee, Gila River, Pechanga, CTUIR, Seneca, LCO | `NO_LIST_FOUND` | Solicitation boards and registration funnels. **An open solicitation is not a vendor list and registration is not publication.** |
| the other 21 | `NOT_CHECKED` | |

> **THE COUNT ABOVE IS A LOWER BOUND AND ITS RATE IS NOT MEASURED.** Twenty-one
> of thirty are `NOT_CHECKED` because this pass searched for ownership. The
> coordinator's expectation — that general vendor lists are *more* common than
> TERO certifications while being worth less per row — is **not tested here**
> and must not be quoted as if it were. Reporting these numbers as a measured
> rate would be our own scope limit published as a fact about the source, which
> is defect class 2.

**Why it is worth a dedicated sweep.** MHA alone is a Bakken-scale procurement
surface with named counterparties. This is the **spending-side complement to
the owner's local-capture research** at `Desktop\lumecon_local_capture`, which
measures how much activity stays local from Advan mobility data (WA/OR/ID,
19 reservations, median local capture 20.8%, outside-origin 75.4%). Mobility
data can say *how much* leaks; a vendor list can say **to whom**. That is a
question no mobility panel can answer.

**Its own sweep needs its own query set**: "bidders list", "small works
roster", "approved supplier", "approved vendor", "prime contractor list",
"consultant roster".

### Product 3 — "ON RESERVATION" (business location). **WEAK GO — the regimes exist, the registries do not.**

| entity | verdict | what |
|---|---|---|
| Gila River | `LIST_REFERENCED_NOT_PUBLISHED` | **The cleanest case.** Business Licence application, Transaction Privilege Tax form and Title 13 ordinance all published; **no registry of licensed businesses.** |
| Oneida (WI) | `LIST_REFERENCED_NOT_PUBLISHED` | Vendor Licensing runs as a function distinct from Indian Preference certification; no roster seen. |
| Saint Regis Mohawk | `LIST_REFERENCED_NOT_PUBLISHED` | Compliance Department levies and maintains "all fees associated with licensing regulated business activity". Nothing published. |
| Navajo | `LIST_REFERENCED_NOT_PUBLISHED` | The NBOA list carries a per-record `license no.` field, often blank — implying a licence regime whose registry was not located. |
| Pechanga, LCO | `NO_LIST_FOUND` | |
| the other 24 | `NOT_CHECKED` | |

**Four of six checked have a licence regime and none publishes a registry.**
That is a real pattern and a poor prospect for scraping — the realistic route
is records requests, not crawling.

Its value if obtained is high and specific: it connects to
`Desktop\lumecon_reservation_industry_mix` (NaNDA vs host-county industry mix,
location quotients) and it would fix a known defect in the gaming and
employment layers, where location is currently inferred from mailing addresses
— **NIGC's own addresses are frequently the tribe's mailing address, not the
property's; every Chickasaw property files at "2020 Lonnie Abbott Blvd., Ada
OK".**

**Do not design a shelf for products 2 or 3 now.** Recorded, costed, parked.

---

## 8. SOVEREIGNTY, CONSENT AND LICENCE — as a gate, not a paragraph

A federal record is public by statute. **A sovereign government's own
publication is not the same thing, and "publicly reachable" is not "licensed
for commercial redistribution."**

Cedar Press already runs two provenance restrictions as machinery — the Casino
City `LICENSED_SOURCE_FILES` rule and the D&B pre-2022-04-04 rule on legal name
and address. This is the third, and it is implemented the same way rather than
written down and remembered:

- **`cedar_codebook.TRIBAL_SOURCE_RESTRICTED_FILES`** declares the restricted
  files, beside `LICENSED_SOURCE_FILES`, one definition and many importers.
- **`code/321_gate_tribal_source_restriction.py`** fails a build on five
  checks: a restricted file missing its consent columns (a gate that cannot
  evaluate a file must fail it, never pass it); an unrecognised
  `consent_status` value; `publishable = Y` without `OPT_IN`; an `OPT_OUT`
  that did not suppress; and a restricted file leaking into `data/clean/` or
  `dist/`. It has a `--selftest` with seven fixtures, because a detector
  narrowed until it stops seeing its own defect reports clean.
- **Every row carries `consent_status` ∈ {`UNRESOLVED`, `OPT_IN`, `OPT_OUT`},
  a `suppression_key`, and `publishable`.** Removal is one field, not a search
  — and so is admission, because some TERO offices will want the reach and
  **saying yes must be as cheap as saying no.**
- **Silence is `UNRESOLVED`, never permission.** All 30 authorities are
  `UNRESOLVED` today and **`publishable = N` on every staged row.**

**Terms as measured:** 4 entities state a restrictive term (all bare
"All Rights Reserved" footers, which are boilerplate rather than considered
data policy — recorded as `TERMS_STATED_RESTRICTIVE` because an
all-rights-reserved assertion is affirmative, with the caveat in the row).
**No entity in the study states a data-specific redistribution licence,
permission, or prohibition.** One states a robots disallow naming this agent.
Four are `NOT_CHECKED` because a WAF made the terms unreadable.

**Attribution is a design requirement, not a courtesy.** Every published row
names the certifying tribe: *"certified by the [Nation] TERO, retrieved
2026-08-26,"* with the URL. **The tribe did the verification work; the citation
says so.**

---

## 9. GO / NO-GO

### Option B — the evidence layer. **GO. Build first.**
Highest value, lowest risk, no redistribution question at all: we publish the
**finding**, not their list. Target the 37 `agent_research_one_leg` rows
($3.73B) first, then the 66 `need_v6` rows, then the 158 propagated rows
($33.69B). Cost is one extraction pass over 13 sources.

### Option A — the certification registry, pro shelf (Cedar Press+). **GO, framed as a REGISTRY.**
Not republished directories. A registry row asserts *"firm X is certified by
Nation Y as of date Z, per this URL"* — a **citation index over public
assertions, each attributed to the tribe that made it.** That is the thing with
analytical value anyway, because it is joinable and dated, and it is what the
Wayback layer turns into a time series.

**Shelf: `pro`.** The pro shelf already holds `contractors`,
`subcontracting`, `natural-resources` and `nonprofits` — all entity-level
commercial identity — and this is specifically the **verification layer for
`contractors`**. Someone buying one wants the other. Shelves nest upward, so
Grove licensees see it too. And an unclassified dataset defaults to `pro`
anyway: *an entry nobody has placed must not fall open to the cheapest plan.*

**Descriptor** (`server/cedar_press/collections.py`, `CollectionDataset`):
`id`, `name`, `short_name`, `origin`, `level`, `tracks`, `rows_label`,
`downloads`, `vintage`, `version`, `updated`, `sources`, `method` — **computed
at build time, never hand-typed.** The citation string is generated from
`version` and `vintage`; the server's own docstring says *"Version and vintage
are load-bearing, not garnish."* Registered in `pressCatalog.js` under `pro`.

**Size it honestly in the descriptor**: ~1,800 rows at 30 entities, ~17,000–
21,000 projected at 574. This is a small, high-density, high-provenance
dataset. Do not promise a large one.

### Products 2 and 3. **PARKED with a costed next step.**
Both are real. Neither was measured by this pass, and saying so is the finding.

### What would make this a NO
If the 13 publishing entities had held **no tier-B rows** — if every one were
already tier A — option B would be worthless and option A would be a 1,800-row
curiosity. They hold 390 rows on $41.10B. That is what turns it.

---

## 10. NEXT STEPS, IN ORDER

1. **Finish the CDX sweep** (`py -3 code/317_cdx_tribal_vendor_hosts.py`) —
   resumable, skips hosts already on disk, honours the host lock. Hosts at the
   6,000-row limit need a narrowed `url` prefix, not a bigger limit.
2. **Extract the 13 lists.** Three PDFs and one DOCX extracted cleanly in
   discovery; Colville's wide printed spreadsheet is lossy and needs per-file
   tuning; Oneida and Cherokee need a headless render.
3. **Match into the ledger at the right tier.** A list with no identifier
   produces `CANDIDATE_ONLY_NO_IDENTIFIER` rows for the reconciliation queue.
   **Never a link.** Read `NAME_TRAPS` first — `PANANA DELENA` is the worked
   example.
4. **Sweep `*Capability-Statement*.pdf` across ANC government-services
   domains.** If Doyon's one-PDF-per-company convention generalises, that file
   naming may be the highest-yield artefact class in the whole study, because
   those PDFs carry UEI *and* CAGE *and* an explicit parent sentence.
5. **Ask.** Write to the 13 TERO and corporate offices with the registry row we
   hold for them and the `consent_status` question. Some will say yes.
6. **Re-run the three negatives whose search was budget-limited** (Gila River,
   Yakama, Choctaw MS) with WebSearch available, before anyone treats them as
   settled.

---

## 11. THINGS THAT WOULD HAVE BITTEN US, RECORDED SO THEY DO NOT

- **"TERO" is the wrong search term.** CSKT calls it the **Indian Preference
  Office**; CTUIR buries it under Workforce Development; Navajo runs it as the
  Business Regulatory Department; Cherokee, EBCI and MHA run it on **separate
  domains** (`cherokeetero.com`, `ebci-tero.com`, `mhatero.com`) barely linked
  from the tribal site. **A keyword sweep on "TERO" alone finds 3 of 13.** The
  synonym set is: TERO · Tribal Employment Rights · Indian Preference ·
  Indian-Owned Business · Business Regulatory · Preferred Supplier · Certified
  Contractor · Source List.
- **Being on a TERO list is not by itself an ownership claim.** Colville's file
  flags firms `Certified Title 10 = Yes` at **0% Indian ownership**. The
  percentage column must be read. Navajo and Colville are graded; the others
  are binary.
- **"Vendor" is a false friend.** Poarch's on-site search for "vendor" returns
  **pow-wow craft vendors**. Saint Regis Mohawk's robots.txt disallows
  `/vendor/` — a **Composer directory**, not a vendor list.
- **A published directory is not a complete one.** UIC displays 23 companies
  and claims "over 70 subsidiaries" — a successful scrape may capture **a
  third** of a corporate family. ASRC's ranking in Cedar's own data shows 57
  operating companies against ~46 published.
- **A directory can be federated across hosts.** Chenega's lives on four SBU
  microsites, not the parent domain. A crawler that stops at the parent misses
  most of it.
- **`oglalalakotanation.net` is an offshore online casino impersonating the
  tribe**, served through a Cloudflare Workers subdomain. It must never enter a
  host list or be cited as tribal. The legitimate host is `oglala.gov`.
- **Akwesasne material online frequently belongs to the Mohawk Council of
  Akwesasne (Canada)** — a different government. Do not conflate.
- **403 on every path including robots.txt is a WAF, not a refusal we can
  read.** `kotzebueira.org`, `nana.com` and `olgoonik.com` are `NOT_CHECKED`,
  never negatives. Olgoonik is rank 25 in our own ranking — that is real unread
  value, not absence.
- **MHA publishes a "Preference Level 3 — Brokers" list**: a tribal government
  publicly naming which of its certified firms operate as pass-throughs. If the
  attribution work ever touches pass-through structure, that is a primary
  source and it is already public.

---

# 12. THE SCALE-UP — 62 entities, and the rule table that changes the product

*Second pass, 2026-08-26, on the owner's decision to build both options. These
numbers supersede every count in §§1–11.*

## 12a. Where the roster stands

| | tranche 1 | + tranche 2 | total |
|---|---:|---:|---:|
| entities on the roster | 30 | 32 | **62** |
| checkable (excl. `SITE_UNREACHABLE`) | 29 | 29 | **58** |
| lists found | 13 | 9 | **22** |
| …ownership assertions | 13 | 8 | **21** |
| …carrying a joinable identifier | 3 | 0 | **3** |
| `LIST_REFERENCED_NOT_PUBLISHED` | 1 | 6 | **7** |
| `NO_LIST_FOUND` | 14 | 14 | **28** |
| `SITE_UNREACHABLE` | 1 | 3 | **4** |

**Publication rate holds: 22 of 58 checkable = 37.9%**, against 43% in the
top-weighted first tranche. Tranche 2 was deliberately weighted to the middle
and tail of federal contracting, so **publication falls only modestly as you go
down the distribution.** Projected ownership lists at 574: **208, still an
upper bound** for the reasons in §6d.

> **`SITE_UNREACHABLE` IS EXCLUDED FROM THE DENOMINATOR, AND THAT IS A
> DELIBERATE CHOICE.** Turtle Mountain and San Carlos Apache return HTTP 403 or
> 307 on every HTML path; White Mountain Apache's TLS certificate is expired.
> The hosts exist and answer. Counting them as negatives would publish **our own
> access problem as a fact about the source** — defect class 2, in the exact
> shape this project has already paid for twice. San Carlos is the sharp case:
> **its sitemap serves fine and proves two distinct TERO pages exist**
> (`/tribal-employment-rights-office/` *and* `/tero-2/`), while every HTML page
> is filtered. That is a false unknown, never a false negative.

## 12b. The nine new lists

| entity | verdict | format | entries | the thing that matters |
|---|---|---|---:|---|
| **Tulalip Tribes** | `MACHINE_READABLE` | CSV/TXT export | hundreds *(cert #s run 143→5196)* | **The best source found anywhere.** A "Native American Owned Business (NAOB) Registry" with a real CSV export, a **stable certification number**, an **explicit ownership percentage**, and **tribe affiliation** recorded for non-Tulalip Natives. |
| **Muscogee (Creek) Nation** | `MACHINE_READABLE` | native XLSX | ~380 | Per-row **owner names**; 51% codified in NCA 18-199; filename date-stamped nine days before the check on a predictable `…-YYMMDD.xlsx` pattern. |
| Tohono O'odham Nation | `PDF` | PDF | 19 | Owner names, **date certified**, Full vs Probationary status. An entity we hold **zero tier-A UEI links** for. |
| Southern Ute Indian Tribe | `PDF` | PDF | 27 | The **Growth Fund's energy companies appear on the TERO list itself** — Red Willow Production and Red Cedar Gathering, beside small local contractors. |
| Lummi Nation | `PDF` | dynamic `.php` | ~143 | **Regenerated per request** — "Current as of Wednesday August 26th, 2026", the fetch date. Carries **licence expiry** per firm. |
| Blackfeet Nation | `PDF` | scanned PDF | 25 | Carries a **tribal business licence number** — the only artefact bridging products 1 and 3. |
| The Chickasaw Nation | `HTML` | HTML | 500–900 est. | 51% Chickasaw **citizen** ownership stated; 17 enumerable categories. |
| Forest County Potawatomi | `HTML` | HTML | 18 | Owner names on 18/18. Small and **self-asserted — no verification stated**. |
| Menominee Indian Tribe | `HTML` | HTML | 23 | **Deliberately typed DOWN to `VENDOR`** — see 12e. |

## 12c. THE RULE TABLE — `tribal_certification_rules`

`code/323` builds it; `docs/codebooks/02m_tribal_certification_layer.md`
documents it. **14 programmes, 11 `RULE_FOUND` quoted verbatim from the
governing ordinance, 3 `RULE_PARTIAL`.** A rule is **quoted, never inferred**:
the build **refuses to write** `RULE_FOUND` or `RULE_PARTIAL` without a verbatim
quote *and* a source URL, and refuses `RULE_NOT_PUBLISHED` without a `searched`
value.

### The finding that justifies the whole table

**Ownership floors are 51%, 60% or 100% depending on the tribe, and nothing on
the lists says so.**

| floor | programmes |
|---:|---|
| **51%** | Navajo (P2), CSKT, EBCI, Poarch, Cherokee Nation, Oneida (WI), Seneca, Muscogee, Chickasaw, Laguna, Sault Ste. Marie |
| **60%** | **Colville, CTUIR** |
| **100%** | **MHA Nation** |

> **A blanket 51% filter silently mis-states Colville and CTUIR, and badly
> mis-states MHA.** That is precisely the adjudication Cedar Press should not be
> doing on the subscriber's behalf — publish the floor, let them filter.

### Colville is a genuine contradiction, not a definitional difference

The first pass reported that Colville flags firms `Certified Title 10 = Yes` at
0% Indian ownership, and concluded "presence on a TERO list is not by itself an
ownership claim." **Retrieving Colville Tribal Code Title 10 makes it
stronger.** §10-3-4(h), verbatim:

> *"No contractor or subcontractor shall qualify for preference if Indian
> ownership in, or control of, the business is less than the required minimum
> percent at any time during the bidding stage, the proposal stage, or the
> performance of the contract."*

The lowest certifiable category requires **60%**. So a published row at 0%
**contradicts the governing chapter on its face**. Publish the rule beside the
flag and let the contradiction show — do not drop the rows, and do not infer a
threshold. **Also: since 2026-04-23 there are FIVE tiers, and Tier 5 is
"Indian owned businesses that are *not* certified by the Colville Tribes" — so
"on the list" and "certified" are no longer the same predicate.**

### Two lists misdescribe their own rule

- **EBCI** says "Certified TERO vendors are **TRIBAL MEMBER** owned businesses."
  Its own rule is weaker in one direction (**51%**, not whole ownership) and
  broader in another (**Priority 2 admits members of any federally recognised
  tribe**). And the **P1/P2 flag is not published on the list**, so a subscriber
  cannot currently tell an EBCI-owned firm from an any-tribe firm.
- **CSKT's** legend — "PREFERENCE 1 = CSKT TRIBAL MEMBER" — reads as a statement
  about a *person's enrolment*. Ordinance 101A is a **51% ownership + management
  control + integrity-of-structure test on the firm**.

### The cross-cutting fact with the widest reach

**Most of these certifications are not evidence of citizenship in the certifying
nation.** Cherokee, Oneida (WI) and CTUIR all define the qualifying person as an
enrolled member of **any** federally recognised tribe. Oneida says so in terms —
*"'Indian preference' means preference for Indians, **regardless of tribal
affiliation**"* (§502.3-1(t)). Seneca is the exception, and only in its
additional-certification tiers, which is why the Seneca ordinance is the most
publishable rule in the set.

**Calista's Calivika is the weakest assertion and it says so itself**, which
the rule table now records verbatim: *"Calista does not investigate or evaluate
the listed businesses in any way."* Eligibility is "owned by at least one
qualified individual" — **satisfiable by a 1% owner, and spouses and
grandchildren qualify**, so a listed business may have no Native owner at all.
Type it `SHAREHOLDER_OR_DESCENDANT_OR_SPOUSE`, never aggregate it with a TERO
certification.

**MHA is the model for what we should publish.** Its Preference Level 3 is an
**openly declared brokering tier** — the tribe certifies, publishes and ranks
contractors acting as brokers rather than self-performing, and labels it. MHA
has done deliberately what Colville's list appears to have done by accident:
**separated the certification from the self-performance claim.**

### One correction the rule capture forced on us

The first pass read MHA's four "Preference Levels" as a flat 1-2-3-4 ranking.
**It is a two-level nesting**: Levels 1–3 subdivide *Tier 1* (MHA-member-owned)
by **how the work gets done**; what was called "L4" is *Tier 2* — a different
axis entirely, **which tribe the owner belongs to**. A flat column
misrepresents the tribe's own scheme. Corrected in the table.

## 12d. The outward joins — `code/324`, typed

`KEY_JOIN` (an identifier the authority published) and `NAME_CANDIDATE` (a name
only) are **never summed**.

| universe | KEY_JOIN | NAME_CANDIDATE | refused |
|---|---:|---:|---:|
| `prime_contracts` | 7 rows, **$2,135.4M** | 2 | 34 family-stem |
| `subawards` | **4** (Doyon Project Services **151 rows**, ASRC NetCentric **194**, Nakuuruq **5**) | 2 | — |
| `deals_classified` | **0** | 2 | — |
| identifier ledger | 7 | — | — |

**Answering the owner's deals question directly: certified firms do appear in
deals, but only as name candidates — zero key joins — because
`deals_classified.csv` carries no firm-level identifier column at all.** It has
`native_party_entity_id`, a Cedar spine id. To answer "are certified firms in
deals?" with a key rather than a name, the deals table needs a firm-level UEI
column it does not have. That is a schema finding, not a data absence.

**Subawards is where the new value showed up** — 350 subaward rows reached by
four identifiers, and subcontracting is exactly where small Native firms live.

### A new guard the run earned: A CORPORATE FAMILY STEM IS NOT A FIRM IDENTITY

"ASRC Federal NetCentric Technology" matched **eighteen distinct ASRC Federal
subsidiaries** on the overlap `{asrc, federal}`. Two non-generic, non-trap
tokens cleared every guard we had, and the match was still wrong: it identifies
the **family** correctly and the **firm** not at all — and being right about the
parent is exactly what the parent's own directory already told us.

`324` now refuses the whole group **by name**: if one asserted firm matches
three or more distinct counterparties on the *same* overlap token set, that set
is a stem, not an identity. **34 false candidates refused, each named in the
run output.** Same shape as `NAME_TRAPS` one level up — a token shared by a
whole family cannot distinguish within it.

## 12e. Judgement calls, recorded rather than smoothed

- **Menominee typed DOWN to `VENDOR`.** For ownership: the application collects
  an **enrolment number and affiliation**, the listing is branded "Menominee
  Contractors", entries are **reviewed and approved** before publication, and
  individual principals are named. Against: no TERO branding, no ownership
  threshold, no certification number or expiry, no published eligibility rule.
  **When a row is genuinely ambiguous the honest move is to type it down and say
  why.** Confirm by phone before counting it either way.
- **Chickasaw carries a caveat on its own rule.** The directory states 51%
  Chickasaw-citizen ownership, but the companion Preferred Vendor Program page
  frames eligibility more broadly and the Construction listing holds many
  non-Chickasaw-sounding firms. **Confirm the two are the same population**
  before treating 51% as binding on every row.
- **Lummi is a Chamber of Commerce compilation** served on the tribal
  government's own system, carrying LIBC licence-expiry data. Provenance
  recorded on the row.

## 12f. Ethics — two new stops, both honoured

- **`penobscotnation.org` names `ClaudeBot` under `Disallow: /`**, alongside a
  Cloudflare content signal `ai-train=no`. Collection stopped on discovery;
  **a handful of pages had already been fetched before robots.txt was read, and
  that is disclosed on the row rather than tidied away.** `wayback_priority =
  EXCLUDED` — the same rule Ely Shoshone earned. Substantively this is a live
  lead: the Penobscot **Business & Services Directory** was announced
  2026-06-08, is explicitly ownership-scoped and explicitly promised
  "public-facing", and **does not exist yet**. Any future acquisition goes
  through **direct contact with the Nation, not crawling**.
- **Lummi's robots.txt disallows `/apps`** — the exact path the tribe's own
  Business Directory page uses to link the file. That path was **not fetched**.
  The identical report is served from `/widgets/`, which is permitted, and that
  is the copy retrieved. **Any re-run must use `/widgets/`.**
- Crawl-delays honoured throughout: `cskt.org` 10s, `blackfeetnation.com` 10s,
  `hopi-nsn.gov` 10s, `southernute-nsn.gov` 10s,
  `shop.fcpotawatomi.com` **15s**.

## 12g. Three hijacked domains — blacklist these

All three look like plausible official URLs and all three now redirect to
unrelated commercial sites. **None may enter a host list or be cited as
tribal.**

| domain | now serves | legitimate host |
|---|---|---|
| `oglalalakotanation.net` | an **offshore online casino impersonating the tribe**, via Cloudflare Workers | `oglala.gov` |
| `cheyenneriversiouxtribe.org` | 301 → `laurenscounty.us` | `cheyenneriversioux.com` |
| `whitemountainapache.org` | 301 → `sticksushi.es` | `wmat.us` |

Two more traps that look like blocks and are not: `ohkay.org` (expired TLS
certificate) and `maliseets.com` (certificate valid only for
`*.townsquareinteractive.com`, 301s to `maliseets.net`). Both were reached; both
are **genuine negatives, not `SITE_UNREACHABLE`**. And `redlakenation.org`'s
apex serves an IIS7 default page while the live site is on `www.` — querying the
apex alone produces a false unreachable.

## 12h. The method finding, now with nine confirmations

**Separate domains carry the lists. Treat `<tribe>tero.com` as a PRIMARY step,
not a fallback.**

`cherokeetero.com` · `ebci-tero.com` · `mhatero.com` · **`tulaliptero.com`** ·
**`btero.com`** · **`wstero.com`** · **`chickasawbusinessnetwork.com`** ·
**`shop.fcpotawatomi.com`** · **`fortpecktero.org`**

**Blackfeet is the extreme case and the best argument for the rule:** the word
"TERO" appears **nowhere** in `blackfeetnation.com`'s sitemap, and neither the
Economic Development nor the Employment page mentions it. The only pointer to
`btero.com` was a **plain-text phone-book entry in the Tribal Directory staff
listing**, reachable only through the WordPress `?s=` search.

Two more that generalise:

- **Sitemap enumeration beats navigation, again.** Tohono O'odham's list sits on
  a third-level page not linked from the TERO landing page body. **Lummi's own
  directory page renders "no documents currently available" while the identical
  report is live at two other paths** — navigating by the site's own directory
  would have produced a false negative.
- **Laguna files its TERO under *Tax Administration*.** No employment- or
  business-oriented navigation path reaches it. **Department-agnostic sitemap
  keyword grep is now a standard step.**

## 12i. "Certifies but does not publish" is now the second-largest category

**Seven entities** have a working certification programme and publish no roster:
Seneca, Quinault, Ute Mountain Ute, Warm Springs, Sault Ste. Marie, Laguna,
Penobscot. Add the four from tranche 1 whose TERO plainly operates without
publishing (Yakama, Standing Rock, Oglala, Gila River) and **the binding
constraint is confirmed: publication capacity, not TERO adoption.**

The cleanest evidence anywhere in the study is Quinault's own construction bid
packet, verbatim: **"A list of Quinault Native American Owned Businesses is
available from TERO."** The blank certification application is published; the
list is distributed **only on request**.

**That makes records requests, not crawling, the highest-yield next channel** —
and it is also the channel that asks permission rather than taking.

## 12j. Next, in order

1. **Pull Tulalip's NAOB `.csv`** — hundreds of records with certification
   numbers *and* ownership percentages, the only such dataset found. **Read
   `tulaliptero.com/Home/TermsOfUse` first**; it is `NOT_CHECKED` and an
   unreadable term is not an absent one.
2. **Pull Muscogee's XLSX** for an exact row count and owner names.
3. **Re-check the four unreachable** (Turtle Mountain, San Carlos, White
   Mountain Apache) from a different egress. San Carlos first — its sitemap
   proves two TERO pages exist.
4. **Wayback-sweep `fortpecktero.org`** — one page today, `lastmod` 2025-03-25,
   so an earlier version is likely richer. Best archive lead in tranche 2.
5. **Records requests** to Quinault, Laguna (`pol.ipeco@pol-nsn.gov`), Seneca's
   TERO Commission, and the Osage Tax Commission.
6. **Municode blocks two rules we still want** — Poarch Title 33 and EBCI
   Cherokee Code ch. 92 both return HTTP 403 to an automated client at the host
   level. No bypass was attempted. Both rules were recovered one remove away
   from the tribes' own application packages; only Poarch's **"BID LIMIT"**
   remains genuinely undefined in anything publicly reachable.
