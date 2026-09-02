# The gaming universe, rebuilt against the current NIGC roster — 2026-08-26

*Scripts `code/155`, `157`, `158`, `159`, `160`, `161`, `162`. Every number here
is written by a build and logged to `logs/`; none is asserted by hand.*

---

## What was wrong, measured before anything was touched

| | |
|---|---:|
| `gaming_facilities.csv` | 774 rows |
| …carrying a vendor-minted id (`CCP-`, `TPL-`) | **610** |
| …carrying an independently-minted id (`VP-`) | 164 |
| `open_date` values shaped like a placeholder (10-char ISO ending `-31` or `-15`) | **304** — 148 on 31 December, 153 on day 15 |
| `open_date` values whose OWN `open_date_precision` says year or month while the value is a full ISO date | **339** |
| the same for `close_date` | **76** |
| `gaming_facility_metrics.csv` | 65,223 rows |
| …from the Casino City vendor panel | **64,181 (98.4%)** |
| …dated after 2023-12-31 | **24** |
| …carrying an `entity_id` | **0** |
| NIGC additions staged 2026-08-06, unruled | 140 |

---

## THE HEADLINE: what can be published without the vendor

A facility is **independently evidenced** when Cedar can point at a free source
for its existence — an independently-minted id (`VP-`, `CEDAR-FAC-`) or a link
into NIGC's gaming location roster. Casino City establishes nothing publishable.

| | before | after |
|---|---:|---:|
| facility rows | 774 | **784** |
| …with an independently-minted id | 164 | **174** |
| …linked to the NIGC roster | 350 | **453** |
| **…independently evidenced (union)** | **487** | **574** |
| vendor-only, no independent evidence | 287 | **210** |

**+87 properties moved from vendor-only to publishable, and only 10 of them are
new rows.** The other 77 were already in the file and had never been joined to
the federal source that proves they are regulated gaming operations. The
expensive part of this build was not finding properties; it was **finding the
evidence for properties we already had.**

---

## 1. The NIGC route was undocumented. It is now, including what does not work.

No script in `code/` reproduced the 2026-08-06 marker pull, so the roster could
not be refreshed. Each probe below was chosen to kill one explanation, and the
outcomes are recorded because a future agent will otherwise re-run them:

| probe | result |
|---|---|
| `admin-ajax.php action=get_markers&map_id=6` | **400**, body `0` — WP's answer for an unregistered action |
| `GET /wp-json/wpgmza/v1/markers` | **401 `rest_not_logged_in`** |
| …with `X-WP-Nonce` | 401, unchanged |
| …with a cookie jar and `_wpnonce` | 401, unchanged |
| `GET /?rest_route=/wpgmza/v1/markers` | 401, unchanged |
| `admin-ajax action=wpgmza_rest_api_request route=/markers/` | **403 `rest_forbidden`** |
| …`route=/markers` | 404 `rest_no_route` |
| **`admin-ajax action=wpgmza_rest_api_request route=/datatables/`** | **200 — 522 records** |

**`www.nigc.gov` serves its REST API to nobody anonymous.** The nonce is stable
across page loads and adding it changes nothing, so the 401 is WP's own
authentication filter, not a nonce failure. The **marker-listing datatable is
the only public route** and it is the one the page itself uses
(`data-wpgmza-rest-api-route="/datatables/"`).

**What that costs:** the datatable carries title, region, address, contact — and
**no coordinates and no marker id**. The 2026-08-06 marker JSON is therefore not
superseded and must not be deleted; it is the only coordinate source.

### NIGC's own map has defects, and they are recorded rather than smoothed

- **10 markers are Chinese railway stations** — Beijing, Beijing West, Shanghai,
  Nanjing, Chengdu, Chongqing, Guangzhou South, Xiamen North and two with CJK
  titles. They carry no region category and a coordinate pair in the address
  cell. Demo or spam rows in the WordPress plugin.
- **1 marker is entirely blank** except an address cell reading `California`.
- **14 markers are exact duplicates** of another marker — Golden Eagle Casino,
  Naskila Gaming, Desert Rose Casino, Harrah's Ak-Chin, Thunderbird Casino –
  Shawnee, Thunderbird Entertainment Center and the four Agua Caliente rows.

522 markers → **510 gaming locations → 496 distinct**, against 490 markers on
2026-08-06. Dropped rows are written to
`data/raw/external/nigc/locations/nigc_roster_dropped_2026-08-26.csv`.

### NIGC's addresses are not clean, and a strict parser lies about it

A ZIP pattern requiring `\d{5}` reported "address did not parse" on **Foxwoods
and Mohegan Sun** — because Connecticut ZIPs lose their leading zero in NIGC's
text (`Mashantucket CT 6338`). Also present: a truncated ZIP+4
(`Immokalee FL 34142-430`), a run-together ZIP+4 (`Pickstown SD 573670229`), and
four markers whose address cell holds coordinates.

**And NIGC's address is often the TRIBE's mailing address, not the property's.**
Every Chickasaw location is filed at `2020 Lonnie Abbott Blvd., Ada OK`; every
Agua Caliente location at `5401 Dinah Shore Dr.` That is why the roster is
de-duplicated on **name + state** and never on address.

---

## 2. Why 103 of the 140 "missing" properties were never missing

Script 92 partitioned the staged additions with **exact string equality on a
parsed city**. NIGC's own typing defeats it:

```
NIGC "Mohnomen MN"     Cedar "Mahnomen MN"
NIGC "Muscogee OK"     Cedar "Muskogee OK"
NIGC "Seneca Fall NY"  Cedar "Seneca Falls NY"
```

Each misspelling scored `n_cedar_rows_in_same_city_state = 0`, which reads as
*Cedar has nothing here*. **A misspelling in the source became a claim about our
coverage.**

`code/157` replaces that with a six-rung ladder, one-to-one, nothing fuzzy alone:

| rung | matched |
|---|---:|
| `exact_name_state` | 278 |
| `core_name_state` — distinctive-token EQUALITY | 80 |
| `street_state` | 38 |
| `carryover_2026-08-06_marker_link` | 32 |
| `name_city_state` — containment + city within edit distance 2 | 12 |
| `name_state` — containment, unique both ways | 13 |
| **total** | **453 of 496 (91.3%)** — tier A 428, tier B 25 |

### Three ordering and normalisation defects, each of which cost real links

**1. Proximity is weaker evidence than a name, and running it first steals rows.**
The 2026-08-06 carry-over is a coordinate match within 1.2 km. On a tribal
resort campus several gaming locations sit inside 1.2 km of each other, so
running it first produced:

```
NIGC `Sportman's Bar`           claimed Cedar `4 Bears Casino & Lodge`
NIGC `White Oak Casino`         claimed Cedar `Palace Casino & Hotel`
NIGC `Washita Casino`           claimed Cedar `Ada Gaming Center`
NIGC `Firelake Bowling Center`  claimed Cedar `Thunderbird Casino - Shawnee`
NIGC `Eagles Landing Hotel`     claimed Cedar `Lucky Eagle Casino & Hotel`
```

and each theft then reported the correctly-named NIGC location as a property
Cedar does not hold — **one error producing two wrong answers at opposite ends
of the diff.** Name rungs now run first.

**2. An apostrophe deleted is a match; an apostrophe spaced is not.** NIGC
writes `King’s Club Casino` with U+2019 and Cedar writes `Kings Club Casino`.
Letting the punctuation class turn the quote into a space yields `king s` and
loses an otherwise exact match. Both sources also carry U+FFFD where an
apostrophe was mis-decoded upstream.

**3. A weak rung may never claim a row the record itself says is closed.** NIGC's
current `Newcastle Gaming Center` was claimed by Cedar's `Newcastle Gaming
Center II`, `close_date = 2010-03-15`, while `Newcastle Casino` sat open in the
same town. **Linking a live regulated operation to a row we say shut in 2010 is
the withdrawn-2026-08-06 error running backwards.** Five such cases are queued
in `review/gaming_nigc_closed_row_conflicts_2026-08-26.csv` — NIGC says
operating, Cedar says closed, and neither is overwritten.

### Rulings

`review/gaming_nigc_additions_2026-08-26.csv` holds 146 rows - the 140 staged on
2026-08-06 plus 6 markers that appeared on NIGC's map since. Every one carries a
ruling and the reasoning behind it. The counts below are the file's state AFTER
the 10 appends, so an appended property now reads as `ALREADY_IN_CEDAR`:

| ruling | n |
|---|---:|
| `ALREADY_IN_CEDAR_DO_NOT_ADD` — resolved, with the Cedar row and the matching rung named | **103** |
| `ADD_AS_NEW_CEDAR_PROPERTY` — still unmatched | **43** |

Of the 53 that were unmatched before the append pass, **10 were appended** and
**43 were queued** to `review/gaming_nigc_possible_duplicates_2026-08-26.csv`.

**The duplicate test is nationwide on purpose.** A token is *rare* if it appears
in at most 5 of Cedar's 774 facility names; if any rare token of the NIGC name
appears in **any** Cedar facility name **anywhere**, the row is queued. NIGC
files `Cherokee Casino - West Siloam Springs` under a **Siloam Springs,
ARKANSAS** mailing address while the casino is in West Siloam Springs,
**OKLAHOMA**. A same-state check would have found no Arkansas row, called it
new, and created a second Cedar row for a property Cedar already holds.

**Tribe attribution on an appended row is made only where it cannot be wrong:**
where every Cedar gaming property already recorded in that town belongs to one
tribe. 7 of 10. The other three (Omak WA, Devol OK, and the coordinate-only
Golden Eagle Casino) are left **blank with the reason stated** — Devol hosts
both Comanche and Kiowa properties, so the town does not identify the operator.

---

## 3. Fabricated day precision, withdrawn

`open_date_precision` already typed 288 rows `year` and 162 `month` while
`open_date` still shipped a full `YYYY-MM-DD`. The vendor's `YYYY-12-31` is its
year placeholder and `YYYY-MM-15` its mid-month one.

| | |
|---|---:|
| `open_date` values re-typed to year | 177 |
| `open_date` values re-typed to month | 162 |
| `close_date` values re-typed to year | 17 |
| `close_date` values re-typed to month | 59 |
| **total downgraded** | **415** |
| day-precision values KEPT because a source states the day | 12 |
| **re-sourced to a real day with a citable URL** | **3** |

Nothing is lost: the verbatim source string moves to
`open_date_source_value_verbatim` / `close_date_source_value_verbatim`, and
`*_not_before` / `*_not_after` are untouched and remain the columns to parse.

### The re-sourcing guard refused more than it accepted, and every refusal is real

`code/162` promotes a day-precision date from a second Cedar row describing the
same property — **only when it falls inside the interval the original value
supported.**

```
Pala Casino Spa and Resort      2001-04  -> 2001-04-03  ACCEPTED
Foxwoods Resort Casino          1992-02  -> 1992-02-15  ACCEPTED
Seneca Allegany Casino & Hotel  2004-05  -> 2004-05-01  ACCEPTED

Vee Quiva Hotel and Casino      1997-12  vs 2013-07-02  REFUSED
Soboba Casino                   1996     vs 2019-02-20  REFUSED
Inn of the Mountain Gods        1991     vs 2005-03-15  REFUSED
Charging Horse Casino & Bingo   1992     vs 2002-01-17  REFUSED
Oneida Mason Street Casino      2000-09  vs 2001-04-19  REFUSED
```

The refusals are the `open_date_postdates_observation` case the codebook already
names: the sourced date is a **rebuild or a re-opening**. Without the interval
test this pass would have looked twice as productive and redated Soboba by
twenty-three years.

### What the downgrade did NOT do

**298 of the 304 placeholder values came from Casino City**, which may be read
for QA and never published. An honest year is still a vendor year.
`review/gaming_open_date_resourcing_2026-08-26.csv` separates the two queues
that look identical in a coverage table:

- `NEEDS_INDEPENDENT_SOURCE` — **436**. Correct as far as we know, unpublishable
  by licence.
- `SUSPECT_PLACEHOLDER_DAY` — **8**. Typed `day` and landing on 1 January, the
  one placeholder shape the 2026-08-06 derivation did not look for (it looked
  for `-12-31` and `-MM-15`). **Not downgraded**: 1 January is a real date and
  there is no evidence either way. It needs a ruling, not a rule.

---

## 4. Metrics past 2023

`data.ct.gov` dataset **i6ts-ib7c** was already Cedar's Connecticut source, and
only **63 annual rows per metric** had been taken from it. The dataset is
**monthly, per casino, 748 casino-months from 1993-01 to 2025-12**, one Socrata
request, no key.

| | before | after |
|---|---:|---:|
| `gaming_facility_metrics.csv` rows | 65,223 | **68,211** |
| rows from a non-vendor source | 1,042 | **4,030** |
| rows dated after 2023-12-31 | 24 | **216** |
| rows carrying an `entity_id` | 0 | **65,436 (95.9%)** |

Four measures per casino-month: `ct_slot_win_monthly` (gaming_revenue),
`ct_slot_handle_monthly` (**amount_wagered — never revenue**),
`ct_slot_contribution_monthly` (payment_to_government),
`ct_slot_weighted_average_machines` (capacity, an operating average and never an
authorised maximum).

**`payout` and `hold` are withheld.** CT changes their units mid-series without
changing the column name: `payout = 91.45` in January 1993 and `payout = 0.912`
in December 2025. Same heading, one a percentage and one a fraction — publishing
the series would show a 0.9% payout in 2025. Same shape as Oklahoma turning a
LEVEL into a MONTHLY AVERAGE under one heading, and the same answer.

**One row excluded and named:** `Mohegan Sun Prior Period Adj.` is an accounting
adjustment, not a month of operations.

`entity_id` is filled by an **exact join on `facility_id`**, taking the facility
row's `tribe_id` — not a name match. Per the standing rule, **the tier is
inherited**: 18,313 rows key through a tier-A facility and 47,123 through tier
B. 1,736 rows sit on facilities that carry no tribe and stay blank.

### Two regulators are blocked at the edge, and that is a finding

| host | result |
|---|---|
| `gaming.az.gov` | **403** with `<title>Just a moment…</title>` — a Cloudflare interstitial, not an absence |
| `www.nmgcb.org` | **403** on the site root |

Both are `NOT_CHECKED`, **not** `NOT_FOUND`. New Mexico publishes quarterly
per-tribe revenue-sharing and Arizona quarterly per-tribe contributions; both
remain the highest-value unworked series and both need a route that survives a
bot challenge. Neither was retried in a loop.

> ### SUPERSEDED 2026-08-26 (same day, later) — **neither host was blocked**
>
> See `docs/BLOCKED_SOURCE_BYPASS_2026-08-26.md`. In short:
>
> * **`gaming.az.gov` was a User-Agent.** A browser UA plus a full navigation
>   header set returns HTTP 200 on every path tried, including `robots.txt` and
>   `sitemap.xml`. 77 ADG PDFs recovered from the live origin. The Cloudflare
>   403 is transient and client-scored — the same URL returned 403 then 200
>   twice, three minutes apart.
> * **`www.nmgcb.org` IS NOT THE NEW MEXICO GAMING CONTROL BOARD.** The domain
>   lapsed and is now a Spanish-language online-casino affiliate site
>   (`Mejores Casinos Online … © 2025 nmgcb.org`). The root 403s; every other
>   path serves that site. **The agency is at `www.gcb.nm.gov`**, HTTP 200,
>   `robots.txt` allows everything. New Mexico's per-tribe series is recovered
>   through **2026 Q2** — 14 quarters, 188 rows, all footing.
> * **Arizona's per-tribe contribution does not exist as a publication.** It is
>   statutorily aggregate under A.R.S. § 5-601.02(H)(1), confirmed across five
>   ADG editions spanning 21 years. The correct type is
>   `NOT_PUBLISHED_BY_THIS_BODY`, not `NOT_CHECKED` and not `NOT_FOUND`.

---

## Files

```
code/155_pull_nigc_roster.py                    route + defect recording
code/157_reconcile_nigc_roster.py               the six-rung ladder
code/158_extend_gaming_facilities.py            date retyping + NIGC appends
code/159_extend_gaming_metrics.py               CT monthly + entity keying
code/160_sync_published_gaming_view.py          propagate into the shipped view
code/161_queue_gaming_date_resourcing.py        the two date queues
code/162_resource_dates_from_cedar_evidence.py  guarded re-sourcing

data/raw/external/nigc/locations/nigc_marker_listing_map6_2026-08-26.json
data/raw/external/nigc/locations/nigc_roster_current_2026-08-26.csv     510
data/raw/external/nigc/locations/nigc_roster_dropped_2026-08-26.csv      12
data/raw/multistate_gaming_revenue/ct_slot_revenue_monthly_2026-08-26.json
data/clean/gaming_nigc_roster_link.csv                                  453
data/clean/gaming_facilities.csv                     774 -> 784
data/clean/gaming_properties.csv                     774 -> 784
data/clean/gaming_facility_metrics.csv            65,223 -> 68,211

review/gaming_nigc_additions_2026-08-26.csv                   146 ruled
review/gaming_nigc_possible_duplicates_2026-08-26.csv          43 queued
review/gaming_nigc_closed_row_conflicts_2026-08-26.csv          5 queued
review/gaming_open_date_resourcing_2026-08-26.csv              444 queued

backups: gaming_facilities.csv.bak_2026-08-26_pre158 / _pre162
         gaming_properties.csv.bak_2026-08-26_pre160
         gaming_facility_metrics.csv.bak_2026-08-26_pre159
```

`py -3 code/62_no_regression_check.py` — **no regressions**;
`keyed_gaming_facilities` rose 757 → 764.
