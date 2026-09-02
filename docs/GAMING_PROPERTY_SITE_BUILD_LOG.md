# Official property sites and public game finders — build log

*Gaming spec steps 11 and 21. Built 2026-08-12 by
`code/142_build_property_site_observations.py`. Every number below is computed
by the build and written to `logs/142_summary_2026-08-12.json`; none is asserted
by hand.*

---

## The honest headline

**A game finder does not tell you how many machines a casino has, and the
temptation to read it that way is the whole risk of this step.**

Four properties publish a browsable game list. Between them the four list
**6,851 games**. Those four properties do not have 6,851 slot machines between
them, and they do not have 3,808 either. The listing is a **SKU**, not a
cabinet, and this was measured before anything was counted:

```
"$$$ Fever!"                Castle Hill Gaming   25c   -> map id geadfcc6…
"$$$ Fever!"                Castle Hill Gaming   $1    -> map id g174f6b9…
"Dancing Pots Mc Md Prog"   Bluberi   $0.01 / $0.02 / $0.05 / $0.10  -> 4 rows
"Long Tehng Hu Xiao"        Aristocrat                              -> 12 rows
```

**1,211 of 4,513 (title, manufacturer) pairs carry more than one listing**, and
the maximum for a single pair is **12**. In the other direction a bank of forty
identical cabinets is **one** listing. So the row count is wrong in both
directions at once, which is exactly why `measurement_type` is
`GAME_FINDER_OBSERVATION` on all 6,851 rows and why that value sits in
`cedar_domain.NEVER_PROMOTES_TO_ACTIVE`. `ACTIVE_FLOOR_COUNT` is unreachable
from this file by construction, asserted at module import and again per row.

WinStar says the same thing in its own words, and the quote is carried on the
system registry row:

> "DISCLAIMER: Our Game Finder tool is as accurate as possible — but since we're
> constantly expanding, there may be differences or changes that aren't
> reflected here."

---

## What was built

| file | rows | what it is |
|---|---:|---|
| `data/clean/gaming_game_finder_observations.csv` | **6,851** | game title · manufacturer · denomination · type · volatility, per listing |
| `data/clean/gaming_property_site_observations.csv` | **262** | operator-published SCALE: machines, tables, gaming/meeting sq ft, hotel rooms, venue capacity |
| `data/clean/gaming_property_labor_demand.csv` | **43** | Indian Preference, gaming-licence requirements, wage floors, TERO |
| `data/clean/gaming_game_finder_systems.csv` | 3 | the systems themselves and **what one row of each means** |
| `data/clean/codebook/07j_gaming_property_sites.csv` | 13 | codebook fragment; `codebook_master.csv` untouched |
| `review/gaming_game_finder_signals_2026-08-12.csv` | 447 | finder-shaped language found on 58 hosts, harvested or not |
| `review/gaming_property_site_refused_2026-08-12.csv` | 1,621 | numbers that looked like counts and were **refused** |

Observations by measurement type:

| measurement_type | n |
|---|---:|
| `GAME_FINDER_OBSERVATION` | 6,851 |
| `PROPERTY_REPORTED_COUNT` | 262 |
| `LABOR_DEMAND_STATEMENT` | 43 |

`LABOR_DEMAND_STATEMENT` is deliberately **outside**
`cedar_domain.MeasurementType`. A job posting measures nothing about capacity
and must never join the count vocabulary; every labour row carries
`not_an_employee_count` saying so in words.

---

## Coverage against the 775-property universe

`gaming_facilities.csv` holds **774** properties. **440** carry a current status
literal (Open / Temporarily Closed / Under Construction) and are the frame this
build could probe.

- **159 properties** were matched to a verified official site, on **144
  distinct hosts**.
- **171 hosts** crawled (144 discovered + the 27 seeds proven by script 119),
  **2,273 requests**, **1,749 pages** retained.
- **80 properties** now carry at least one observation from their own site:
  72 with a scale metric, 17 with careers language, 4 with a game finder.

**The gap is honest and it is a discovery gap, not a publishing gap.** Domains
were generated from the property name and accepted only when the page named
every distinctive token of the property AND placed it in the right city or
state. That is precision-first: it will never invent a link, and it cannot
reach a property whose domain does not contain its name. **WinStar is the proof
— `winstar.com` does not contain "world", so the generated pass missed the
largest casino in the country**, and it is in this build only through a hand
ruling. The 281 open properties without a verified site are a **NOT_CHECKED**
on the domain, not a **NOT_FOUND** on the publication.

Six hand rulings resolve hosts the generator cannot: WinStar, Riverwind,
Newcastle, Coushatta, FireKeepers (×2 host spellings). Each names the property
and the reason, in `SEED_PROPERTY_RULINGS`.

---

## The three game-finder systems, and the data model of each

### 1. The Chickasaw Nation shared WordPress theme — HARVESTED

Serves **WinStar World Casino (CCP-411600), Riverwind (CCP-773500) and
Newcastle (CCP-410800)** from one theme (`chickasaw`). Custom post type
`wscp_casino_game`, archive at `/gaming/casino-games/list/`, 20 per page,
paginated with `?page=N`, total printed as `data-max-pages` in the Load More
control. Taxonomies `wscp_casino_game_category` (electronic-games /
table-games / off-track-betting) and `wscp_casino_game_venue`.

Published per listing: **title, manufacturer, one or more denominations**, and a
map id linking to `/casino-map/?game-id=g<32 hex>`. **No quantity anywhere.**

**The REST API is off.** `/wp-json/` and `?rest_route=` both return the site's
own HTML, so there is no JSON route and the archive HTML is the only surface.

#### The venue filter does not filter — and believing it would have been a false attribution

The finder prints an 18-entry venue dropdown for WinStar (Baccarat Salon,
Beijing/Cairo/London/Madrid/New York/Paris/Rio/Rome/Vienna Gaming Plazas,
Belvedere/Crown/Regal High Stakes, Bingo Hall, Poker Room, Racers OTB, Lightning
Link Lounge, Global Event Center). Measured:

- `…&wscp_casino_game_venue=41187` (Baccarat Salon) returns the **same first
  page** as the unfiltered archive;
- Newcastle venues `1` and `3` return **identical** pages;
- Riverwind publishes **no venue dropdown at all**.

The first harvest ran venue-by-venue and would have written *every game at
WinStar into a Baccarat Salon*. It was thrown away and re-run unfiltered.
`floor_location` is therefore **blank with a stated reason** on this platform,
and the venue list is kept as a published fact about the property's named
gaming areas — in the crawl manifest, never joined to a game.

### 2. The Coushatta Slot Finder — HARVESTED

`www.coushattacasinoresort.com/gaming/slot-search/` (CCP-38800). A bespoke PHP
application. Its result fragment is served unauthenticated at
`/ajax-slot-result.php` — resolved through the page's own `<base href>` to the
site **root**, not to the form's directory, which is why the obvious URL
appears to 404. It refuses an empty query —

> "Please enter a slot name, denomination, or a manufacturer."

— so the harvest iterates the finder's **own published manufacturer list**
(13 names), one request each.

**This is the richest finder found anywhere.** Per listing it publishes title,
manufacturer, denomination, type (Poker / Reel / Video) and **volatility**
(High / Medium-High / Medium / Medium-Low / Low) — a field no regulator
publishes and no other operator in this sweep publishes. Floor position is a
**pixel marker on a floor-plan SVG** (`/slot-map.php?sid=N`), not a named zone,
so the sid is kept in `source_game_id` and `floor_location` stays blank.

### 3. FireKeepers "Find Your Game" — FOUND, NOT HARVESTED

`firekeeperscasino.com/casino/games/slots/slots-results/` (CCP-658400) carries a
legacy **ExpressionEngine** search form (`ACT=2`, an `XID` CSRF token and an
encrypted `meta` blob) embedded in a WordPress page, POSTing to
`http://firekeeperscasino.com/games/slots/slots-results` — a path **without the
`/casino/` prefix that no longer exists**. Its WordPress REST namespace `fk/v1`
publishes `shows`, `restaurants`, `restaurants-old` and `promotions` and **no
games route**. There is no browsable listing without a query.

**Recorded as FOUND rather than forced.** Replaying a per-session CSRF token
against a dead action path to guess at results is not a fact anyone could audit.

### Nothing else in 171 hosts

Every crawled page was scanned for finder language. **447 pages on 58 hosts**
carry some — mostly "progressive jackpots" (306) and "casino map" / "interactive
map" (42) — but only the three systems above serve a machine-readable listing.
The tell is a **manufacturer or denomination FIELD sitting next to titles**:
across all 1,749 retained pages, only Coushatta and Riverwind have one. Four
strong-signal candidates were probed directly (Kiowa `/new-slots/`, Kiowa
`/gaming/slot-machines/`, Spirit Mountain `/casino/slots/`, Seneca Buffalo
Creek `/casino/slots/`) and all four are marketing pages. Seneca Buffalo Creek's
"Over 1,000 Reel and Video Slot Machines" is a scale claim, and it is captured
as one — as a `PROPERTY_REPORTED_COUNT`, not as a floor count.

**Manufacturer strings are stored verbatim, including the operators' own vendor
shorthand** — `EVERI2`, `ATI`, `VGT`, `ASTG`, `Ainsworth/AW`. Normalising them
would assert an identity the source does not, so 78 distinct strings are kept as
78 distinct strings.

---

## The guard that stopped a game title becoming a slot count

The first extraction pass produced this, and it is exactly the shape of error
this project keeps finding:

```
gaming_machines 1000  "… Sugar Rush 1000 Slots 8/9/2026 …"   <- a jackpot ticker
gaming_machines   88  "… Fire 88 Slots brings a v…"          <- a game title
gaming_machines 2026  "… 8/9/2026 Kaylee M. … Slots"         <- a date
```

A number next to the word "slots" is not a count of slots. The rule now is that
a number is accepted **only when a counting cue immediately precedes it**
(`over`, `more than`, `features`, `houses`, `with`, `experience`, `between`, …)
and no date sits in the preceding fourteen characters. **1,621 candidates were
refused** and written to `review/gaming_property_site_refused_2026-08-12.csv`
rather than dropped silently, so recall is recoverable and precision is not
traded away.

What survives reads like a fact:

> "With over 600 electronic games, you can test your luck regularly in our
> 22,000 square foot…" — Chisholm Trail Casino

---

## Careers pages carry things no other source has

**10 Indian Preference statements across 7 properties**, verbatim — e.g. Dakota
Magic's *"Indian preference will apply/EEO (Please Provide Tribal Enrollment)"*.
Plus **31 gaming-licence requirements**, one wage floor
(*"Waitstaff is $13/hour plus tips"*, Gold River) and one TERO reference.

**Every one is LABOR DEMAND.** An open posting says a property wants to hire; it
says nothing about how many people work there, and this file must never be read
against `gaming_employment_observations.csv`.

---

## What was refused, and what refused us

| | |
|---|---|
| **robots.txt** | `shootingstarcasino.com` and `www.baymillscasino.com` disallow the paths this build wants. **34 URLs not fetched.** Both are recorded as refusals, not as absences. |
| **403 / stop-work** | `downstreamcasino.com`, `www.apachecasinohotel.com`, `www.emeraldqueen.com`, `www.luckyturtlecasino.com`, `www.windcreek.com`. First refusal stopped that host; no retry loop anywhere. |
| **HTTP 500** | `chisholmtrailcasino.com`, `jetstreamcasino.com`, `mytexomacasino.com`, `washitacasino.com`, `www.saltcreekcasino.com`. **A 500 is a fact about the moment, not about the object** — those pages are unresolved, not unpublished. |
| **Transport failure (status 0)** | 4 URLs. Recorded as `http_status=0` with the reading spelled out. **A dropped connection is not a 404.** |
| **Authentication** | Nothing behind a login was touched. No CSRF token was replayed, no access control was probed. FireKeepers was left unharvested for exactly this reason. |
| **Attribution** | 12 hosts serve more than one Cedar property (windcreek.com → 3, casino.hardrock.com → 3, newcastlecasino.com → 3, pearlriverresort.com → 2 …). Their observations are written with a **blank `facility_id`** and a named reason. Nothing is snapped to a nearest property. |

---

## Rules honoured

- **No new facility id is minted anywhere.** Asserted per row against
  `gaming_facilities.csv` before write.
- **Append-only history.** `merge_dated()` refreshes `last_seen` when a row is
  unchanged and appends a new dated row with `supersedes_observation_id` when a
  value **meaningfully changes**. Verified idempotent: a second and third
  consecutive run append **zero** rows.
- **Every row carries** `source_url`, `retrieved_at`, a verbatim `source_quote`,
  `measurement_type`, `confidence` and the source file's `source_md5`.
- **One resolver.** `resolve_entity` is imported from
  `code/33_apply_party_rulings.py`. **No new name matching is performed** — tribe
  ids ride along from `gaming_facilities.csv`, which an earlier build keyed with
  that resolver.
- **Pull discipline.** One `logs/_HOSTLOCK_<host>.json` per host, ≥1.6 s gap
  within a host, sequential within a host, three hosts in parallel at most,
  robots.txt evaluated per path, wall-clock deadline per phase, skip-if-present
  so a re-run costs nothing.
- **Not edited:** `gaming_facilities.csv`, `gaming_capacity_official.csv`,
  `gaming_property_capacity_history.csv`, `gaming_device_observations.csv`,
  `compacts.csv`, `gaming_ordinances.csv`, the spine, the identifier ledger,
  `codebook_master.csv`, `series_breaks.csv`.
- **Casino City** was not read, written or published by this build.
- `code/62_no_regression_check.py` clean **before and after**.

---

## Two operational scars from this session

**1. `code/142_` is a COLLIDED PREFIX.** Another agent was running
`code/142_build_nrc_public_meetings.py` concurrently. Both files exist. This is
the same condition AGENTS.md already records for `95_`, and it is now true of
142 as well — **`ls code/<n>_*` before claiming a number is not optional.**

**2. A kill filter matched the wrong process, and the lock outlived it.**
`CommandLine -like '*--hosts www.winstar.com*'` was meant to stop a duplicate
writer and instead killed the seven-host run, because `www.winstar.com` appears
inside that run's comma-separated `--hosts` list. AGENTS.md already says *never
kill by image name*; the sharper rule is **match the full argument, or kill by a
PID you enumerated and read**. Two consequences worth carrying forward:

- The killed process left `active: true` in two host locks, which then blocked
  the replacement run from those exact hosts. **A lock is released by the
  process, so a killed process always leaks one.** Both were released by hand
  with the reason written into the lock.
- Its manifest rows were lost while its HTML was not, so the resume path was
  changed: a cached file now **re-emits its manifest row** instead of being
  skipped, and a manifest destroyed by a kill rebuilds with zero extra requests.

---

## Next, in value order

1. **Domain discovery for the remaining 281 open properties.** The generated
   pass is precision-first and leaves recall on the table; a search-assisted or
   hand pass would roughly double site coverage.
2. **Re-run the crawl for the five 500-ing hosts and the five that refused.** A
   500 is a moment, and a 403 may pass at a different hour.
3. **Meetings and convention pages are under-harvested.** 45 meeting-sqft rows
   across 11 properties is well short of what `/groups/`, `/sales/` and
   downloadable capacity charts hold; the richest of those are PDFs this pass
   did not open.
4. **Re-run the finders on a schedule.** The whole point of `first_seen` /
   `last_seen` is a fleet-turnover series, and it needs a second date to exist.
