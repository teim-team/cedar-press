# Gaming property web harvest — build log

*Run 2026-09-02 by `code/980_gaming_web_harvest.py`. Owner mandate: **"You should
be scraping casino websites… coordinate per-tribe"** and **"All these website
scrapings, check for stuff that's not published on the website for a user to
see, but is in the HTML code."***

**One pass per nation.** Each facility-bearing tribe's casino / gaming-authority
hosts and its TERO / vendor / procurement surface were taken together, not as
two separate dataset passes.

## Scope boundary

A separate agent owns `gaming` dataset promotion (revenue bounds, class II/III
derivation) in the 960–979 band. **This workstream wrote only its own files and
did not edit `gaming_property_self_published_assertions.csv` or
`gaming_property_self_published_claims.csv`.** See *What should be merged* below.

## Files written

| path | rows | what |
|---|---:|---|
| `code/980_gaming_web_harvest.py` | — | the harvester: `targets` / `probe` / `pages` / `cpt` / `escalate` / `build` / `verify` |
| `data/clean/gaming_web_harvest_observations.csv` | **1,166** | staged observations — capacity signals and facility identity |
| `data/clean/gaming_web_harvest_coverage.csv` | **590** | one row per (nation, host): URL found, what was harvested, **what was checked and absent**, date |
| `data/staging/gaming_web_harvest/targets.csv` | 773 | the per-tribe target list, 590 hosts |
| `data/staging/gaming_web_harvest/host_probe.jsonl` | 4,545 | append-only, one row per host per endpoint |
| `data/staging/gaming_web_harvest/page_fetch.jsonl` | 1,727 | append-only, one row per page / CPT endpoint |
| `data/staging/gaming_web_harvest/escalation.jsonl` | 10 | the ladder walked for nations whose sourced URL failed |
| `data/staging/gaming_web_harvest/raw/` | 3,561 objects, 470 MB | every body retrieved, hashed |
| `review/gaming_web_harvest_escalation_candidates_2026-09-02.csv` | 10 | the candidates, each with its derivation |
| `logs/_HOSTLOCK_gaming_web_harvest_980.json` | — | released, `active: false` |

## Reach

| | n |
|---|---:|
| facility-bearing tribes in `gaming_facilities.csv` | 284 |
| …with at least one host **reached** | **273** |
| …whose sites **yielded data** | 190 |
| …excluded, `TERMS_STATED_RESTRICTIVE` | 8 |
| …still unreached | **3** |
| facilities whose operating nation was reached | **736 of 787** |
| hosts probed | 590 (355 gaming-surface, 235 tribe-surface) |
| content requests made (excluding `robots.txt`) | **5,057** |

Per-host coverage status:

| status | hosts |
|---|---:|
| `HARVESTED` | 273 |
| `TOUCHED_NOTHING_FOUND` | 249 |
| `EXCLUDED_TERMS_STATED_RESTRICTIVE` | 25 |
| `UNREACHABLE_202` (bot-challenge stub, 169 bytes) | 18 |
| `UNREACHABLE_TRANSPORT_FAILURE` | 12 |
| `UNREACHABLE_403` | 6 |
| `REACHED_BUT_DOMAIN_SUSPECT` | 3 |
| `REACHED_BUT_PARKED_DOMAIN` · `UNREACHABLE_404` · `UNREACHABLE_503` · `REFUSED_ROBOTS_DISALLOW` | 1 each |

**`TOUCHED_NOTHING_FOUND` is not `UNTOUCHED`** and the table keeps them apart.
Every coverage row also carries `checked_and_absent`, naming the techniques that
were run and returned nothing — so the next agent does not re-run them:

```
arcgis_feature_service        526      json_ld                       245
embedded_google_sheet         526      sitemap                       169
embedded_app_state            513      substantive_html_comments     139
vendor_procurement_tero       436      rss_feed                      138
wordpress_rest_api            258      wp_media_pdfs                   9
```

## Hidden data, by technique

`docs/HIDDEN_DATA_TECHNIQUES.md`, run against every reachable host.

| # | technique | yield |
|---|---|---|
| 1 | **JSON-LD / schema.org** | **281 hosts**; 136 carry a full `Organization`/`Casino`/`Hotel` record — legal name, street address, locality, postal code, telephone, geo, parent organization |
| 2 | embedded app state (`__NEXT_DATA__`, `__NUXT__`, `__INITIAL_STATE__`, `drupalSettings`) | 13 hosts |
| 3 | **WordPress REST API** | **306 hosts alive.** `/wp/v2/media?mime_type=application/pdf` → **15,265 documents indexed**. `/wp/v2/pages` → **12,907 pages, including pages absent from the nav.** `/wp/v2/types` → custom post types on **259 hosts** |
| 3b | **custom post type collections** | **2,210 items in 110 requests across 68 hosts** — the "one request replaces the crawl" payoff |
| 4 | **sitemap / sitemap index** | **57,840 URLs enumerated** (child sitemaps followed, bounded at 3 per host) |
| 5 | `<select>` option vocabularies | recorded per host in `host_probe.jsonl` |
| 6 | `data-*` attributes | 472 hosts |
| 7 | HTML comment blocks | 387 hosts |
| 8 | AJAX sources | **233 hosts publish `/wp-admin/admin-ajax.php`. It was RECORDED AND NEVER FETCHED** — it lives under `/wp-admin/` |
| 9 | ArcGIS FeatureServer | **0.** Genuinely absent on casino properties, unlike tribal-government sites |
| 10 | embedded Google Sheets | **0** |
| 12 | `<meta>` / OpenGraph | all 590 hosts |
| 13 | RSS feeds | **1,430 dated items** |

### The custom post types are the find

`docs/HIDDEN_DATA_TECHNIQUES.md` says a CPT name is the single highest-yield
signal in this project, and it was again:

- **`enterprise`** — `shakopeedakota.org` (13: SMSC Storage Facility, Shakopee
  Dakota Convenience Store, The Meadows at Mystic Lake, Native Harvest Catering…)
  and **`www.potawatomi.org` (27: Firelake Discount Foods, FireLake Express
  Grocery Tecumseh / McLoud, FireLake Corner Store…)**. These are
  **parent-asserted ownership** — the strongest evidence class here — and feed
  the hub/sub-hub crosswalk, not the vendor dataset.
- **`tribalbusiness`** — `delawaretribe.org` (4: Lenape Reserve, Teton Trade
  Cloth by Lenape, Delaware Tribe Ranch, Tahkox e2).
- **`rfp`** — `morongonation.org` (32 live solicitations).
- **`department` / `departments`** — `stcroixojibwe-nsn.gov` (34),
  `lowersioux.com` (30), `shakopeedakota.org` (21), `enterpriserancheria.org` (13).
- Property-side: **`games`** (chukchansigold.com 62, blackmesacasino.com 8),
  **`casino`** (oneidacasinohotel.com 15 table games by name),
  **`hotel-rooms`/`rooms`** (chukchansigold.com 8, sevenfeathers.com 8),
  **`venue`** (bluelakecasino.com 5).

None of these are reachable by a TERO-vocabulary search, which is the point
`docs/HIDDEN_DATA_TECHNIQUES.md` makes under *searching for the institution
instead of the thing*.

### Vendor / procurement / TERO surface

**868 vendor, procurement, TERO, RFP and "doing business with us" URLs on 154
hosts**; 163 of those pages were fetched this pass. Examples that answered 200:
`ebci-tero.com` (plus `/compliance/` and a 2024 procurement conference),
`boisforte.com/resources/assistance-services/tribal-employment-rights-office/`,
`apachetribe.org/tribal-departments/procurement/`, `cskt.org/rfps/`,
`delawaretribe.org/procurement-notices/`, `ashiwi.org/rfp/`,
`chukchansi-nsn.gov/rfp/`.

## THE FENCE — self-published capacity is never a regulator's figure

Every capacity row carries `assertion_class = SELF_PUBLISHED_OPERATOR_ASSERTION`
and a populated `not_summable_with`:

```
nigc_gross_gaming_revenue;state_regulator_device_counts;
gaming_facility_metrics.official;other_rows_of_this_table_for_the_same_facility
```

**309 capacity observations across 122 hosts and 104 nations:**
gaming_machines 189 · table_games 48 · hotel_rooms 23 · gaming_square_feet 15 ·
employees 12 · convention_square_feet 11 · restaurants 8 · bingo_seats 3.

Three qualifiers ride on every row, and each exists because the first run got it
wrong:

1. **`value_is_bounded` / `bound_direction`.** 152 of 309 are lower bounds —
   "over 650 slot machines", "500 + Slot Machines". The word-based detector
   missed the trailing `+` form entirely on the first pass. **A bound recorded
   as an exact value is the same class of error as a self-published figure
   recorded as a regulator's.**
2. **`measurement_scope`.** A capacity figure can describe ONE ROOM.
   `chukchansigold.com` publishes *"79 slot machines at the entrance"* and
   *"45 slot machines"* in the Firehouse Lounge; both are true, neither is the
   property total, and summing them is wrong in a way no total, count or date
   range would reveal. 5 rows are `SUBPROPERTY_QUALIFIED`; the other 304 are
   **`UNVERIFIED_SCOPE`** — *nothing in the sentence says whether this is the
   whole property or one room, and Cedar has not verified it either way.* That
   is the honest label, not `PROPERTY_LEVEL`.
3. **`facility_attribution_status`.** 703 of 1,166 rows are
   `TRIBE_LEVEL_MULTI_FACILITY_NOT_DISAMBIGUATED` — the nation operates more
   than one property and the page does not say which one the number belongs to.
   463 are `SINGLE_FACILITY_TRIBE`, where the attribution is unambiguous.
   **Only the second group is safe to key to a `facility_id`.**

## Terms restrictions — what was NOT taken

Eight nations, 25 hosts, **45 facilities**, excluded by every route including the
WordPress media API and Wayback. No request of any kind was made to them; the
exclusion is recorded per host in the probe log as
`EXCLUDED_TERMS_STATED_RESTRICTIVE` with the registry row that justifies it.

Confederated Colville · CTUIR/Umatilla · Yakama · Chickasaw · Southern Ute ·
Forest County Potawatomi · Stillaguamish · **Navajo Nation**.

> **Navajo is a judgement call and should get an owner ruling.**
> `review/tribal_vendor_list_registry_2026-08-26.csv` marks the source
> `TERMS_STATED_RESTRICTIVE` on the strength of a copyright footer on
> **navajoeconomy.org**, and the standing mandate list does not name Navajo.
> This run excluded the nation **entirely** — including Fire Rock, Northern
> Edge, Flowing Water and Twin Arrows — which is the safe direction but may be
> broader than the publisher's actual statement. Asking is the route back in.

**One over-broad exclusion was found and corrected mid-run.**
`dancingeaglecasino.com` was in the restricted-host list as Navajo. Dancing
Eagle is **Pueblo of Laguna**. An over-broad restriction costs a nation its
coverage just as surely as a missed one costs the publisher their terms.

## Still unreached, and what was tried

**A negative from search alone is not a negative.** For every nation whose
sourced URL failed, the ladder in the mandate was walked — the nation's own
domain, its `-nsn.gov` / `.nsn.us` form, and the **facility name separately** —
and each candidate was judged before it counted as found.

| nation | tried | outcome |
|---|---|---|
| **Rincon Band of Luiseño** | `rincon-nsn.gov`, `www.rincon-nsn.gov` | **RECOVERED.** Only a Wayback capture was on file; the origin had never been tried directly |
| **Cahto Tribe of the Laytonville Rancheria** | `redfoxcasino.net` (NXDOMAIN), `cahto.org` (**hijacked**), `cahtotribe-nsn.gov` (cert failure) | **RECOVERED with relaxed TLS.** See below |
| **Alturas Indian Rancheria** (Desert Rose Casino) | `desertrosecasino.com`, `alturasrancheria.com` | **not found.** The first is parked for sale on HugeDomains; the second does not resolve |
| **Yuhaaviatam of San Manuel** (Yaamava') | `sanmanuel-nsn.gov` (403), `yaamava.com` (403) | **refused by host** to our declared UA, with browser headers already sent |
| **Klawock** (Klawock Casino) | `www.klawocktribe.org` (NXDOMAIN), `klawocktribe.org` over http | **not found.** Shard A previously established the tribe's stated public channel is Facebook |

### Two recoveries worth generalising

- **A Wayback URL in the web map can mean nobody ever tried the origin.**
  Rincon's only recorded URL was a `web.archive.org` capture. The live site
  answers 200.
- **A certificate failure is a misconfiguration, not an access control.**
  `cahtotribe-nsn.gov` fails verification and serves the Cahto Tribe's real
  site. `fetch()` now retries **once** with verification relaxed and stamps
  `tls_relaxed` plus a basis string on the row, so the content is never
  presented as authenticated. This is the same finding shard A recorded for
  `crit-nsn.gov`.

## Compromised and dead domains found

Recorded, never linked, never harvested from:

| host | nation | finding |
|---|---|---|
| **`mewuk.com`** | Tuolumne Band of Me-Wuk | The **Tribal Gaming Agency** page carries injected SEO spam linking to Indonesian gambling sites at `103.179.73.92`. The title and design are the nation's own; the injection is not |
| **`cahto.org`** | Cahto Tribe | Fully hijacked — `<title>` is *"Cahto: Situs Slot Online Terpercaya 2022"* |
| **`lacvieuxdesert.com`** | Lac Vieux Desert | Hijacked, slot-spam landing page (already on the known list in `PULL_DISCIPLINE.md`) |
| **`theluckydogcasino.com`** | Skokomish | Parked and **for sale** on HugeDomains |
| `www.desertrosecasino.com` | Alturas | Parked and for sale on HugeDomains |

Ten further hosts are `DOMAIN_MIGRATED` — a nation moved or rebranded and the
web map still points at the old name: `cherokee.org → cherokee.gov`,
`lvpaiute.com → lvpaiute.gov`, `hoplandtribe.com → hbpi.gov`,
`lvdtribal.com → lvd-nsn.gov`, `southwindcasino.com → rockandbrewscasinobraman.com`,
`cahuillacasino.com → cahuillacasinohotel.com`, `elkvalleyrancheria.com →
elk-valley.com`, plus Greenville, Eastern Shawnee and Fort Independence. **These
are findings, not refusals**, and `cedar_web_map.csv` should be updated.

## The invariant, and the two defects it caught in itself

`py -3 code/980_gaming_web_harvest.py verify` exits 1 on any of eleven
invariants; `verify --selftest` proves each fires on a synthetic violation and
that clean input produces zero failures. **All 11 fire; the run is clean.**

I1 provenance on every row · I2 the self-published fence · I3 nothing from a
restricted source (rows **and** the fetch log) · I4 no forbidden path requested ·
I5 `IDENTICAL_MD5_CEILING` · I6 a known `harvest_status` · I7 no orphan
observation.

Two things the guards caught, both **false positives in the guards themselves**,
and both the project's standing "a marker matched where it did not mean
anything" shape:

1. **I4 fired on `tonation-nsn.gov/departments/administrative-offices/gaming-office/`**
   because `/admin` is a substring of `administrative`. Forbidden paths are now
   matched by **path segment**, not substring. *A guard that over-matches stops
   good work as surely as one that under-matches lets bad work through.*
2. **The hijack detector produced 10 false positives out of 18.** `bandar` inside
   minified JS flagged three legitimate tribal sites, a Korean word in an
   hreflang switcher flagged Kickapoo Lucky Eagle, and an off-apex `og:url`
   flagged eight nations that had simply **moved domains**. Markers are now
   matched against **visible text and `<title>` only**, body-only evidence needs
   **two distinct markers**, an off-apex `og:url` that matches the landed host is
   `DOMAIN_MIGRATED` rather than suspicion, and an `og:url` on a hosting platform
   or a bare IP is a `HOSTING_ARTIFACT`. Four flags remain and all four are real.

**Verdicts are re-adjudicated at BUILD time from the saved raw HTML**, never
taken from what the probe wrote. The probe log is the *record* of what was
served; the verdict is a *judgement*, and a judgement that cannot be revised
without re-fetching is a judgement nobody can fix.

## Politeness

`GLOBAL_DELAY` 0.30 s aggregate, `PER_HOST_DELAY` 2.5 s, six workers each owning
a **disjoint** set of hosts so no host is ever hit concurrently. A host received
roughly 8 requests in total, which is gentler than crawling it — the point
`HIDDEN_DATA_TECHNIQUES.md` makes about one API call replacing 34 page fetches.
`robots.txt` was fetched with **our own declared UA** and a 403/404/empty body
treated as *allowed*; only a real `Disallow` on the path is a refusal (one host).

**A wall-clock read budget had to be added mid-run.** `requests`' read timeout is
per socket read, so a host trickling bytes hung a worker for seven minutes with
no error and no output. `READ_BUDGET_S = 40` now bounds the total and a partial
body is reported as `READ_BUDGET_EXCEEDED`, never as "no content". *A timeout
that cannot bound the total is not a timeout.*

## What should be merged, and by whom

**Nothing here has been merged. The gaming agent owns that decision.**

1. **`gaming_property_self_published_assertions.csv`** — the 857 identity rows
   are the natural fit: `legal_or_published_name`, `street_address`, `city`,
   `state`, `postal_code`, `telephone`, `latitude`/`longitude`,
   `property_type_schema_org`, `operating_hours`, and one `parent_organization`.
   All carry `source_url`, a verbatim `source_quote` (the JSON-LD object as
   served), `source_md5` and `retrieved_at`. **`agrees_with_curated_owner` and
   `agrees_with_cedar_open_year` are not computed here** — that comparison is
   the gaming agent's, not this workstream's.
2. **`gaming_property_self_published_claims.csv`** — the 309 capacity rows,
   **but only after the attribution question is answered**: 703 of 1,166
   observations are tribe-level on a multi-facility nation and must not be keyed
   to a `facility_id` by a consumer. Carry `measurement_scope`,
   `value_is_bounded` and `bound_direction` across unchanged or the fence leaks.
3. **`cedar_web_map.csv`** — 10 `DOMAIN_MIGRATED` corrections, 4 hijacked/parked
   hosts to mark `DOMAIN_HIJACKED_DO_NOT_LINK` / `parked_domain`, and 3 recovered
   hosts (`rincon-nsn.gov`, `www.cahtotribe-nsn.gov`).
4. **The native-owned-business workstream, not gaming** — the `enterprise` and
   `tribalbusiness` custom post types. Parent-asserted ownership belongs in the
   hub/sub-hub crosswalk.
5. **15,265 indexed PDFs and 868 vendor/procurement URLs are a queue, not a
   result.** They are enumerated in `host_probe.jsonl` and `coverage.csv` and
   nothing has been downloaded from them.

## Re-running

```
py -3 code/980_gaming_web_harvest.py targets
py -3 code/980_gaming_web_harvest.py probe    [--surface gaming|tribe] [--deadline-min N]
py -3 code/980_gaming_web_harvest.py pages    [--deadline-min N]
py -3 code/980_gaming_web_harvest.py cpt      [--deadline-min N]
py -3 code/980_gaming_web_harvest.py escalate --candidates review/<file>.csv
py -3 code/980_gaming_web_harvest.py build
py -3 code/980_gaming_web_harvest.py verify   [--selftest]
```

Every network stage is **resumable and append-only** — it rebuilds its `done`
set from the log at startup and re-requests nothing. `build` and `verify` make
no network calls. `targets` folds in anything the escalation ladder confirmed,
judging on `page_verdict` rather than on the stored verdict label, because the
log is append-only and an early row carries the wording in force when it was
written.
