# Native-owned businesses

**Dataset owner:** `code/330_build_native_owned_businesses.py` (the only builder).
**Table:** `data/clean/native_owned_businesses.csv`
**Staging:** `data/staging/business_registry/*.jsonl` (+ `raw/` snapshots)
**Survey / tracker:** `review/tribal_vendor_list_registry_2026-08-26.csv`

A tribal government certifying a business is a **third party with authority
over the ownership question**. That is the tier-A evidence leg Cedar Press has
almost none of: a SAM socio-economic flag is self-certification, and an
ANCSA subsidiary certifying `alaskanNativeCorporationOwnedFirm = NO` is the
standing proof that self-certification is not a determination.

## THE INCLUSION BASIS IS THE PRODUCT (ADR-013)

`identity_claim_text` is quoted verbatim from the source and is why the row is
in Cedar at all. **It is not uniform, and `assertion_class` keeps the two
kinds apart on every row:**

| assertion_class | the authority asserts | example |
|---|---|---|
| `OWNERSHIP` | who **owns** the firm | EBCI: "TRIBAL MEMBER owned businesses ... vetted by the TERO office" |
| `RELATIONSHIP` | the firm **does business with** the tribe | Menominee Contractors listing |

Within `OWNERSHIP` the strength varies by an order of magnitude and
`identity_scope` records it. From strongest to weakest:

| identity_scope | what is certified |
|---|---|
| `enrolled_member_100pct` / `enrolled_member_51pct` | Poarch, per TERO Ordinance Title 33, section-labelled in the source |
| `enrolled_member_cskt` / `..._other_federally_recognized` | CSKT Preference 1 vs Preference 2 |
| `any_native_oodham_and_local` | Tohono O'odham, 51%+ owned by O'odham and other local Indians |
| `any_native` / `any_native_graded` | Cherokee, MHA tiers, Lummi, Blackfeet, Muscogee, Oneida |
| `tribally_owned_entity` | Poarch "TRIBAL BUSINESSES" - the tribe itself owns the firm |
| `parent_asserted_subsidiary` | ASRC Federal, Doyon - a parent naming its own subsidiary |
| `shareholder_descendant_or_spouse` | Calista, Pokagon - **weakest; a spouse-owned firm is not a Native-owned firm and these sources cannot tell you which is which** |
| `vendor_relationship` | Menominee - not ownership at all |

**A consumer that sums OWNERSHIP and RELATIONSHIP rows has added two different
facts.** So has one that treats a Calista shareholder listing as equivalent to
a Poarch 100%-tribal-member certification.

## NOTHING HERE PUBLISHES

Every row carries `consent_status = UNRESOLVED`, `publishable = N` and a
`suppression_key`. A federal record is public by statute; **a sovereign
government's own publication is not the same thing**, and "publicly reachable"
is not "licensed for commercial redistribution."
`code/321_gate_tribal_source_restriction.py` is the machinery; flipping one
`consent_status` field admits or removes an entire authority, and saying yes
must be as cheap as saying no.

## PRIVACY: THE CLEAN TABLE CARRIES THE CERTIFICATION, NOT THE FRONT DOOR

A TERO roster of sole proprietorships is a list of private individuals with
their home addresses and mobile numbers.
`cedar_domain.INDIVIDUAL_NATIVE_WITHHELD_FIELDS` already withholds
`owner_name`, `street`, `recipient_city_name` and `dba_name` for exactly this
case; that rule is **inherited here, not re-invented**.

| | |
|---|---|
| **carried** | business name, normalized name, certifying authority, nation, city, state, service category, certification number / tier / dates, licence number, the verbatim claim |
| **withheld from `data/clean`** | `owner_name_raw`, `email`, `phone`, `address_raw`, `postal_code`, `website`, `dba_name`, `description_raw` - kept in staging only, and named per row in `withheld_fields` |
| **flagged** | `business_name_is_person_name` (1 / 0 / -1 undecidable) so a consumer can apply `cedar_domain.may_publish_individual_native_field` per field |
| **counted, not named** | `owner_name_present`, `n_owners_named` |

No digest surrogate is minted for a personal name. A digest of an enumerable
value is not a privacy control; the protection is that the column does not
ship.

## RESOLUTION: EXACT NAME ONLY, AND AN UNRESOLVED ROW KEEPS ITS ROW

Each business is offered to `503_identity.resolve()` and **only an exact
normalized name/alias hit is accepted.** The loose gov-class token path is
refused by design - it exists to match a filing to the government that filed
it, and on a business roster it produces false ownership claims:

```
Navajo Engineering & Construction  -> 'Navajo'          REFUSED
Osage Electrical Contractors, Inc. -> 'The Osage Nation' REFUSED
Arctic Information Technology, Inc -> 'Arctic Village'   REFUSED
```

78 rows matched that way and every one of them would have been wrong.
A business that does not resolve **keeps its row** with a blank
`business_entity_id` and `record_scope = unresolved` (ADR-010). Nothing here
mints a spine entity.


## THE HARVEST, SOURCE BY SOURCE

`data/clean/native_owned_businesses.csv` holds **2,393 rows** from **18 authorities**.

| authority | source | checked | list found | format | assertion | last harvested | rows in clean | terms |
|---|---|---|---|---|---|---|---:|---|
| Arctic Slope Regional Corporation | `TBD-056` | yes | yes | HTML | OWNERSHIP | 2026-09-01 | 20 | SILENT |
| Blackfeet Nation | `TBD-053` | yes | yes | PDF | OWNERSHIP | 2026-09-01 | 25 | SILENT |
| Calista Corporation | `TBD-058` | yes | yes | MACHINE_READABLE | OWNERSHIP | 2026-09-01 | 98 | SILENT |
| Cherokee Nation | `TBD-045` | yes | yes | HTML | OWNERSHIP | 2026-09-01 | 836 | SILENT |
| Confederated Salish & Kootenai Tribes | `TBD-044` | yes | yes | PDF | OWNERSHIP | 2026-09-01 | 116 | SILENT |
| Doyon, Limited | `TBD-059` | yes | yes | HTML | OWNERSHIP | 2026-09-01 | 8 | SILENT |
| Lummi Nation | `TBD-052` | yes | yes | PDF | OWNERSHIP | 2026-09-01 | 140 | SILENT |
| Menominee Indian Tribe of Wisconsin | `TBD-054` | yes | yes | HTML | RELATIONSHIP | 2026-09-01 | 4 | SILENT |
| Muscogee (Creek) Nation | `TBD-079` | yes | yes | MACHINE_READABLE | OWNERSHIP | 2026-09-01 | 337 | SILENT |
| Oneida Nation (Wisconsin) | `TBD-047` | yes | yes | PORTAL_SEARCH_ONLY | OWNERSHIP | 2026-09-01 | 34 | SILENT |
| Poarch Band of Creek Indians | `TBD-048` | yes | yes | PDF | OWNERSHIP | 2026-09-01 | 13 | SILENT |
| Three Affiliated Tribes (MHA Nation) | `TBD-046` | yes | yes | MACHINE_READABLE | OWNERSHIP | 2026-09-01 | 133 | SILENT |
| Tohono O'odham Nation | `TBD-050` | yes | yes | PDF | OWNERSHIP | 2026-09-01 | 17 | SILENT |
| Confederated Tribes of Grand Ronde | `TBD-032` | yes | yes | HTML/PDF | OWNERSHIP | 2026-08-28 | 81 | SILENT |
| Eastern Band of Cherokee Indians | `TBD-043` | yes | yes | PDF | OWNERSHIP | 2026-08-28 | 68 | SILENT |
| Navajo Nation | `TBD-041` | yes | yes | PDF | OWNERSHIP | 2026-08-28 | 346 | TERMS_STATED_RESTRICTIVE |
| Tulalip Tribes | `TBD-030` | yes | yes | MACHINE_READABLE | OWNERSHIP | 2026-08-28 | 49 | TERMS_STATED_NO_REUSE_RESTRICTION |
| Pokagon Band of Potawatomi Indians | `TBD-C02` | yes | yes | HTML | OWNERSHIP | 2026-09-01 | 68 | SILENT (no terms page published) |

## EXCLUDED, AND WHY - TERMS ARE A DECISION THE PUBLISHER MADE

These stay excluded by **every** route, Wayback included. Two were already recorded restrictive; **four were found restrictive by the 2026-09-01 pass because nobody had opened the terms page** the 2026-08-26 survey recorded as SILENT.

| authority | source | terms read at | the term |
|---|---|---|---|
| Confederated Tribes of the Colville Reservation | `TBD-060` | https://www.colvilletribes.com/ | All rights reserved, Colville Tribes. Copyright (c) |
| Confederated Tribes of the Umatilla Indian Reservation | `TBD-033` | https://ctuir.org/ | Copyright (c) CTUIR 2020 |
| Forest County Potawatomi Community **(NEW)** | `TBD-051` | https://www.fcpotawatomi.com/terms-of-service/ | Permission is granted to temporarily download one copy of the materials ... on FCPC's web site for personal, non-commercial transitory viewing only. This is the grant of a license, not a transfer of title, and under this license you may not: Modify or copy the materials; Use the materials for any commercial purpose,... |
| NANA Regional Corporation, Incorporated **(NEW)** | `TBD-057` | https://www.akima.com/terms-of-use/ | no part of the Services and no Content or Marks may be copied, reproduced, aggregated, republished ... or otherwise exploited for any commercial purpose whatsoever, without our express prior written permission ... Engage in any automated use of the system, such as using scripts ... or using any data mining, scraping... |
| Southern Ute Indian Tribe **(NEW)** | `TBD-055` | https://www.southernute-nsn.gov/terms-of-use | Permission is granted to temporarily download one copy of the materials ... on Southern Ute Indian Tribe's web site for personal, non-commercial transitory viewing only. ... under this license you may not: modify or copy the materials; use the materials for any commercial purpose, or for any public display (commerci... |
| The Chickasaw Nation **(NEW)** | `TBD-018` | http://www.chickasawbusinessnetwork.com/Special-Pages/Terms.aspx | Use of Company Directories - The information contained in any company directories that may be provided on the Service is provided for business lookup purposes and is not to be used for marketing or telemarketing applications. This information may not be copied or redistributed and is provided 'AS IS' without warrant... |

**What the exclusions cost, so the OPT_IN requests can be ranked:**

* **Confederated Tribes of the Colville Reservation** - RICHEST SCHEMA IN THE STUDY: an explicit numeric 'Indian % Owned' column plus a four-level preference tier. It is also the source that PROVES presence on a TERO list is not by itself an ownership claim - firms at 0% Indian ownership still carry 'Certified Title 10 = Yes'. Worth an OPT_IN request.
* **Confederated Tribes of the Umatilla Indian Reservation** - 14 entries, very clean, with owner names and certificate validity ranges.
* **Forest County Potawatomi Community** - 18 FCP tribal-member-owned businesses with owner names.
* **NANA Regional Corporation, Incorporated** - ~55 operating companies each publishing CAGE, UEI, DUNS, primary NAICS and 8(a) status - a UEI-keyed, parent-asserted ANC subsidiary roster joinable to federal award data with no name matching. The single highest-value OPT_IN request in this dataset.
* **Southern Ute Indian Tribe** - 27 firms - and the one source that answers the growth-fund question directly, because Red Willow Production Company and Red Cedar Gathering Company appear on the TERO Indian-owned list itself alongside small local contractors.
* **The Chickasaw Nation** - ~622 businesses, the largest single lower-48 directory after Cherokee.

## COVERAGE AGAINST THE MASTER ENTITY LIST

The 2026-08-26 survey was a **priority sample of 62**, stratified by federal contracting rank, gaming revenue and geography - not a census. Against the 1,555-entity spine:

| entity class | in spine | checked | never checked |
|---|---:|---:|---:|
| Federally recognized tribe | 349 | 52 | 297 |
| Federally recognized Alaska Native Village | 228 | 5 | 223 |
| Native Hawaiian Organization | 210 | 0 | 210 |
| BIE School | 185 | 0 | 185 |
| Alaska Native Village Corporation | 173 | 0 | 173 |
| State-recognized tribe | 64 | 0 | 64 |
| Native Community Development Financial Institution | 64 | 0 | 64 |
| Intertribal Organization | 56 | 0 | 56 |
| Individually Native-owned business | 45 | 0 | 45 |
| Urban Indian Organization | 43 | 0 | 43 |
| Tribal College or University | 37 | 0 | 37 |
| Federal-level self-governance consortium | 29 | 0 | 29 |
| Native Financial Institution | 29 | 0 | 29 |
| Federal-level constituency entity | 22 | 0 | 22 |
| Alaska Native Regional Corporation | 12 | 5 | 7 |
| ANCSA Group Corporation | 6 | 0 | 6 |
| State-level constituency entity | 3 | 0 | 3 |
| **total** | **1,555** | **62** | **1,493** |

**62 of 1,555 entities (4.0%) have ever been checked for a published business directory.** Among federally recognized tribes it is 52 of 349 (14.9%); **297 have never been looked at.** An entity absent from the registry is NEVER_CHECKED, which is a different fact from NO_LIST_FOUND and must not be read as one.

### What checking the rest would take

The 2026-08-26 pass measured the cost: **four parallel agents, one day, 62 tribes**, and its own notes name the four things that made a find hard, all of which generalise:

1. **The list is usually on a SEPARATE DOMAIN** the government site barely links - `cherokeetero.com`, `ebci-tero.com`, `mhatero.com`, `btero.com`. Blackfeet's only pointer was a phone-book entry in a staff directory reachable through the WordPress `?s=` search.
2. **The word 'TERO' is not the search term.** CSKT calls it the *Indian Preference Office*; Muscogee's statute never uses 'TERO'; Poarch's site search for 'vendor' returns pow-wow craft vendors.
3. **Sitemap enumeration beats navigation.** Tohono O'odham's list sits on a third-level page not linked from the TERO landing page body. Lummi's own directory page renders 'no documents currently available' - navigating by it produces a FALSE NEGATIVE.
4. **The terms page must be opened before the list is parsed.** Four of six exclusions on this page exist because it was not.

At the measured rate (~15 tribes per agent-day including the terms read), the remaining **297 federally recognized tribes are roughly 20 agent-days**, and the 2026-08-26 hit rate (22 lists per 62 tribes, 35%) predicts on the order of **100 further published lists**. The Alaska Native villages, village corporations, NHOs, BIE schools and TCUs in the table above are a different question and mostly will not have one; they should be marked `NOT_APPLICABLE` after a cheap first pass rather than left indefinitely NEVER_CHECKED.

### Registry rows that are not a harvest gap

| status | tribes | meaning |
|---|---:|---|
| `NO_LIST_TO_HARVEST` | 28 | the site was enumerated and publishes no list |
| `HARVESTED` | 12 | in data/clean |
| `NOT_PUBLISHED` | 7 | a list is REFERENCED in an ordinance or on a page but not published |
| `EXCLUDED_TERMS_STATED_RESTRICTIVE` | 6 | the publisher stated a term; excluded by every route |
| `HARVESTED_2026-08-28` | 3 | harvested by the earlier pass, promoted by this one |
| `SITE_UNREACHABLE` | 3 |  |
| `BEHIND_LOGIN_OUT_OF_SCOPE` | 1 | Choctaw Nation - a directory behind a login is out of scope, and Wayback is not a route around a login |
| `ROBOTS_DISALLOW_ALL` | 1 | Turtle Mountain: tmchippewa.com robots.txt disallows '/'. A refusal, not an outage |
| `HARVESTED_PARTIAL` | 1 | in data/clean with a stated shortfall |

## TWO THINGS THIS BUILD COULD NOT SETTLE - THEY ARE THE OWNER'S

### 1. The terms bar is not applied consistently, and Navajo is inside the table

`TBD-041` (Navajo, 346 rows) is in `data/clean/native_owned_businesses.csv`
carrying `source_terms_status = TERMS_STATED_RESTRICTIVE`. It was harvested on
2026-08-28 and promoted here because the promotion brief says to promote
everything already in staging. **That is a contradiction and it is left
visible rather than resolved unilaterally.**

The reason it exists is that two different bars have been applied:

| source | what was read | verdict |
|---|---|---|
| Navajo, Colville, CTUIR | a bare copyright footer - "(c) 2025 ... All Rights Reserved" | TERMS_STATED_RESTRICTIVE |
| Chickasaw, FCP, Southern Ute, NANA | an actual terms page saying you may not copy, redistribute, use commercially or collect automatically | TERMS_STATED_RESTRICTIVE |

On the first bar, essentially every tribal site is restricted, because
essentially every website carries a copyright footer. On the second, four
sources refused and the rest did not. **This build applied the second bar to
its own findings and did not reverse the first bar's verdicts** - so Colville
and CTUIR stay excluded, and Navajo stays in the table with the restrictive
flag on every row and `publishable = N`.

Someone has to pick one bar. Until then: **no row from any of these
authorities publishes**, which is what `consent_status = UNRESOLVED` and
`321_gate_tribal_source_restriction.py` are for.

### 2. Muscogee: is a "Vendor List" an ownership list?

A concurrent workstream harvested the same MCN CESO xlsx as `TBD-C01` and
typed it `directory_type = vendor_list`, `identity_scope = unspecified`, on the
ground that **the file itself states no ownership threshold**. This build kept
`TBD-079` and typed it OWNERSHIP, on the ground that **NCA 18-199 s.9-105(I)
requires "fifty-one percent (51%) or more Native ownership and proof of Native
control and management"** to be on it, and that the registry's own verdict is
`assertion_class = OWNERSHIP`.

Both readings are defensible and they are 337 rows apart in what the dataset
claims. `TBD-C01` is refused as a duplicate rather than merged, so the
disagreement is recorded rather than averaged away. The general question -
*does the statute behind a list, or only the text printed on it, set the
assertion class?* - decides more than this one source.

## HOW TO RE-PULL

`py -3 code/330_build_native_owned_businesses.py --list-sources` prints, per
source, the URL, the per-host delay and the robots note.
`docs/PULL_DISCIPLINE.md` governs. Two host notes that will otherwise be
rediscovered the hard way:

* **Lummi** - robots.txt disallows `/apps`, and the tribe's own directory page
  links the report at `/apps/BusLicenses/LummiOwnedBusinesses.php`. The
  identical report is served from `/widgets/`, which is not disallowed.
  **Any re-run must use `/widgets/`.**
* **cherokeetero.com** - the 2026-08-26 survey recorded "403 to a plain client,
  robots.txt UNREADABLE". Both are superseded: robots.txt reads
  `User-agent: * / Disallow:` and a browser User-Agent gets HTTP 200. It was a
  UA gate, not a block.

## KNOWN GAPS, STATED RATHER THAN PADDED

* **Menominee** - 4 firms from 10 of the source's own 23 grid rows. The
  DevExpress pager callback refused three argument formats; Wayback holds
  captures 2015-2026 for a later pass.
* **Tohono O'odham** - 17 firms against the 19 certification stamps the
  document carries. Two rows whose owner blocks sit inside the row-gap
  threshold merged into the preceding firm.
* **CSKT** - 116 of the 118 `PREFERENCE:` records; 5 rows carry
  `BUSINESS_NAME_MAY_BE_AN_ADDRESS_LINE` because the two-column PDF marks no
  boundary between a firm's name and its street line. Kept and flagged, never
  dropped or guessed.
* **Blackfeet** - OCR-recovered from a scan (`ingestion_method =
  ocr_rapidocr_220dpi`, mean line confidence on every row). `OCR_RECOVERED` is
  not the same evidence grade as a born-digital text layer and stays
  distinguishable.
* **ASRC / Doyon** - names only. The UEI/CAGE that make these joinable sit on
  per-subsidiary pages and capability-statement PDFs not harvested here.

## THE 2026-09-01 HIDDEN-ROUTE SWEEP - IT FOUND NOTHING, AND THAT IS RECORDED

`docs/HIDDEN_DATA_TECHNIQUES.md` was run against the **eleven** registry rows
that were REFERENCED-BUT-NOT-PUBLISHED or SITE_UNREACHABLE: robots.txt first,
then `/wp-json/wp/v2/types`, `/wp-json/wp/v2/media?search=`,
`/wp-json/wp/v2/search` and `sitemap.xml`. **None of the six
TERMS_STATED_RESTRICTIVE sources were probed by any of these routes.**

**Yield: zero new vendor lists.** Per-tribe results are in the registry's
`hidden_route_sweep_2026-09-01` column. What the media API returned instead was
consistent and is itself the finding: **ordinances, codes and blank application
forms, never a roster.** Laguna publishes its Indian Preference Code and five
contractor application forms; Warm Springs publishes the TERO Code, an FAQ, a
Contractor Registration form and a Business Certification Form. These tribes
are not hiding a list behind a bad link. They are certifying businesses and not
publishing the register - which is exactly what the 2026-08-26 survey called
`LIST_REFERENCED_NOT_PUBLISHED`, now confirmed by a route the survey did not
run.

Three corrections came out of it, and they matter more than the null:

| tribe | 2026-08-26 | 2026-09-01 |
|---|---|---|
| Turtle Mountain | SITE_UNREACHABLE | **ROBOTS_DISALLOW_ALL** - tmchippewa.com answers, and its robots.txt disallows `/`. A refusal, not an outage; Wayback is not a route around it either. |
| White Mountain Apache | SITE_UNREACHABLE | reachable - it was a **TLS chain problem**, not an absent site. No WP REST and `/sitemap.xml` is 404, so the list question is OPEN, not negative. |
| Kotzebue | SITE_UNREACHABLE | answers HTTP 200 to a browser User-Agent. Open, not negative. |

`harvest_technique` in the registry records, per source, which technique
actually produced the data, so the next agent skips the routes that did not.

### One boundary call, flagged rather than buried

Oneida Nation (WI) renders its vendor list in JavaScript from
`admin-ajax.php?action=collect_ipv_list`, using a nonce **the page itself
prints for anonymous visitors**. `HIDDEN_DATA_TECHNIQUES.md` lists "the AJAX
source behind any table" as technique 8 and separately forbids `/wp-admin/` as
private infrastructure; `admin-ajax.php` is WordPress's public front-end AJAX
handler and lives under that path by convention. `oneida-nsn.gov/robots.txt`
was read on 2026-09-01 and disallows only calendar views and
`/wp-content/uploads/formidable/` - not this path. No login was involved and no
nonce was guessed. **34 rows rest on that judgment; it is the owner's to
overturn.**

## THE TIME DIMENSION NOBODY HAS USED YET

These are current directories, so the universe is TRIBES, not years - but the
registry's `wayback_snapshots` / `wayback_first_capture` / `wayback_last_capture`
columns point at real history. Menominee alone has captures from 2015 to 2026.
A 2019 TERO list against a 2026 one is **certification entry and exit**, which
does not exist as a dataset anywhere. The schema is already built for it:
`first_seen`, `last_seen`, `is_current`, `source_edition`. Two standing rules
apply the moment anyone builds it - never present a historical snapshot as
current, and never rule a current page against a historical record or the
reverse.
