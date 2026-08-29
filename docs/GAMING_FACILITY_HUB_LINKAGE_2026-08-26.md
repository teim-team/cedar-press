# The facility hub, wired to the entity — 2026-08-26

*Scripts `code/164`, `code/165`, `code/166`, plus an additive repair to
`code/102`. Every number below is printed by a build and logged; none is
asserted by hand. Read this after `docs/GAMING_UNIVERSE_REBUILD_2026-08-26.md`
and `docs/GAMING_SOURCE_AUDIT_2026-08-26.md`.*

---

## THE MODEL THIS IMPLEMENTS

Elijah, 2026-08-26:

> "everything connects to a native entity — ANC, NHO, tribe, native org,
> individual native. **A CASINO IS A HUB**: many sources hang off one facility
> — devices, game listings, loyalty programmes, employment, OSHA records,
> websites, promotional material, capacity, revenue. The facility links to the
> entity; the sources link to the facility."

Script 159 wired `gaming_facility_metrics.csv` that way on 2026-08-26 morning
(`entity_id` 0% → 95.9%). **Every other facility-hub source was still keyed to
nothing.** 104,000 rows of gaming evidence existed with no route to an entity,
so the question "what does Cedar know about this tribe's gaming operations?"
could not be answered by a join — it had to be answered by a name match, which
is the thing this project spends its days refusing to do.

---

## WHAT MOVED

| source | rows | entity_id before | after | % |
|---|---:|---:|---:|---:|
| `gaming_property_capacity_history.csv` *(licensed)* | 64,181 | 0 | **62,445** | 97.3 |
| `gaming_game_finder_observations.csv` | 6,851 | 0 | **6,851** | 100.0 |
| `gaming_device_observations.csv` | 1,326 | 0 | **1,271** | 95.9 |
| `gaming_property_site_observations.csv` | 262 | 0 | **186** | 71.0 |
| `gaming_property_labor_demand.csv` | 43 | 0 | **33** | 76.7 |
| `loyalty_program_property.csv` | 48 | 0 | **48** | 100.0 |
| `loyalty_programs.csv` | 18 | 0 | **18** | 100.0 |
| `digital_gaming_relationships.csv` | 154 | 0 | **154** | 100.0 |
| `digital_gaming_revenue.csv` | 10,661 | 0 | **7,811** | 73.3 |
| `gaming_employment_observations.csv` | 769 | 0 | **733** | 95.3 |
| `gaming_property_universe_events.csv` | 10 | 0 | **4** | 40.0 |
| `gaming_property_coverage.csv` | 774 → **784** | 0 | **764** | 97.4 |
| **total** | **85,107** | **0** | **80,318** | **94.4** |

Plus `gaming_facility_metrics.csv` (68,211 rows), which already carried
`entity_id` and now carries the **tier** that link was made at — see below.

**`gaming_property_universe_events` gained a `facility_id` on 6 of 10 rows but
an `entity_id` on only 4.** Two of the ruled NIGC roster rows it joined to
carry no `tribe_id` themselves. The facility link is real and is kept; the
entity is left blank rather than reached round the back through a name, which
is the same refusal the 20 unkeyed hub rows get below.

**Nothing was rebuilt, no row was dropped, no column was removed.** Verified
cell-by-cell against every backup: on all twelve source tables, rows unchanged,
zero columns lost, and **zero pre-existing cells changed**. Only the two derived
coverage tables differ in their existing columns, because 102 recomputes them.

---

## THE COLUMN BLOCK, AND WHY THE TIER IS A COLUMN

Every table gains the same six columns, appended:

    entity_id  entity_level  entity_tier  entity_tier_basis
    entity_link_rung  entity_link_date

`entity_tier` is copied **verbatim** from the facility row. `entity_tier_basis`
says so in words — `inherited from gaming_facilities.CCP-38800.entity_tier
(method=alias)`.

### Script 159 filled `entity_id` and recorded the tier only in its log

That is not a criticism of 159 — it counted the tiers correctly and printed
them. But a tier that lives in a log is a tier every consumer has to re-derive,
and **re-deriving a tier on the consuming side is the exact failure that
attributed UNITED WAY OF THE GREATER CHIPPEWA VALLEY (Wisconsin) to United
Auburn Indian Community (California) at tier A.** The link was exact; the tier
was assigned by the reader.

So `164` adds `entity_tier` + `entity_tier_basis` to
`gaming_facility_metrics.csv` and **touches nothing else in that file** —
`entity_id` is not recomputed, not re-joined, not re-verified. Measured:

    18,313 rows key through a tier-A facility
    47,123 rows key through a tier-B facility
     2,775 rows carry no entity_id  (unchanged)

The facility hub is **213 tier A / 551 tier B / 20 unkeyed**, so roughly
**three quarters of every gaming metric in Cedar rides on a tier-B link**. That
was always true. It is now visible in the data instead of in a log nobody
opens.

---

## THE RUNGS. NAME AND ID FIRST; NO RUNG USES A COORDINATE.

| rung | what it is | rows |
|---|---|---:|
| `facility_id_exact` | the row names a facility that exists in the hub and carries an entity | **71,246** |
| `row_tribe_id_mirror` | the row is tribe-level *by design* — a compact authorises a tribe, an online sportsbook is not a building, a Form 5500 keys to an EIN. Mirrors a link an earlier build already made; **creates none** | 8,283 |
| `multi_property_host_unanimous_tribe` | a website host serving several properties that all belong to one tribe | 21 |
| `ruled_nigc_name_exact` | exact join into `gaming_nigc_roster_link.csv`, a **ruled** table | 6 |
| `not_tribe_attributable_by_source` | the source itself says this licensee is not a Native entity | 2,850 |

### Proximity was not used anywhere, deliberately

The 2026-08-26 rebuild measured what a 1.2 km coordinate carry-over costs:
`Sportman's Bar` claimed `4 Bears Casino & Lodge`, `Firelake Bowling Center`
claimed `Thunderbird Casino`, and **each theft then made the correctly-named row
look missing — one error producing two wrong answers at opposite ends of the
diff.** `gaming_property_universe_events.csv` carries latitude and longitude and
four of its ten rows are unlinked. They stay unlinked. The review card says
why, so the next agent does not "improve" on it.

### The multi-property-host rung takes the WEAKEST tier in the group

Script 142 could not attribute 19 website observations to one property because
the host serves several, and it wrote the candidate facility ids into
`attribution_basis` verbatim:

    multi_property_host: 3 Cedar properties resolve to this host
                         (CCP-692800, CCP-570000, CCP-544800)

All seven such groups are **unanimous on the tribe**, so the observation is a
fact about that tribe even though it is not a fact about one property. It is
therefore linked at `entity_level = tribe`, never `facility` — and at the
**weakest** tier among the candidates. A rung that could not pick a property
must not inherit the best evidence in the group. This is the standing rule *"a
weak rung may not claim a row carrying close evidence"* pointed at tiers rather
than at dates.

### Historical records are marked, not silently ruled against a current roster

`165` links a NIGC map-change event to the **current** roster. Where the event
is a disappearance, `link_anachronism_note` states in words that the link
identifies *which* property the record is about and is **not** evidence about
that property today. Three gaming rulings were withdrawn on 2026-08-06 for
exactly that conflation.

---

## THREE THINGS THAT LOOK LIKE GAPS AND ARE NOT

**1. `digital_gaming_revenue` is "73% linked" and that is the correct number.**
All 2,849 unlinked rows carry the source's own `is_tribe_attributable = no`:
CT Lottery Corp (1,254), MGM Grand Detroit / MotorCity / Greektown (1,134
commercial Detroit rows), CLC XL Center (374), and the Arizona operator brands
ADG publishes without a licence holder. **Quoting 73% as a linkage shortfall
reports 2,849 right answers as open questions.** They now carry
`entity_link_rung = not_tribe_attributable_by_source` so nobody re-opens them.
Every row the source itself calls attributable is linked: **7,811 of 7,811 — 100%**.

**2. `gaming_manufacturer_facts.csv` (62 rows) is correctly facility-less.** Its
own `property_attributed` column states on every row that a manufacturer's
installed base is never apportioned to a property
(`GAMING_DEVICE_BUILD_LOG.md`). Linking it would contradict the column that
build wrote to prevent exactly that. Reported as CORRECTLY_UNLINKED.

**3. 346 device observations and 291 loyalty/digital rows have no
`facility_id` because a compact authorises a TRIBE.** 200 `AUTHORIZED_MAXIMUM`
and 146 `REGULATORY_INVENTORY` rows are tribe-level facts. They are mirrored at
`entity_level = tribe` and must never be attached to one property.

---

## A COLUMN NAME THAT WAS ABSENT READ AS A SOURCE THAT WAS EMPTY

The highest-value single line in this build, and it is one word twice.

`102_build_coverage_profile.py` declared:

    ("nigc_declination_letters.csv", "declination_letter", "tribe_id"),
    ("gaming_financing_events.csv",  "financing",          "tribe_id"),

**Neither file has a `tribe_id` column.** Both key the entity as
`tribe_entity_id`. `DictReader.get("tribe_id")` returns `None` on every row, so
from 2026-08-07 to 2026-08-26 the coverage profile reported:

    declination_letter    0/774   0.0%
    financing             0/774   0.0%

while the two files held **307 and 274 keyed rows**. Nineteen days of a
published coverage table saying two sources cover nothing, when they cover more
than half the property universe:

| | before | after |
|---|---:|---:|
| `declination_letter` | 0 (0.0%) | **460 properties (58.7%)** |
| `financing` | 0 (0.0%) | **400 properties (51.0%)** |

**A named column that is absent and a source that is empty produce the same
0.0% and nothing distinguished them.** `102` now raises `SystemExit` naming the
column and the file's real header. This is the same shape as *"a broken search
is not evidence of absence"* and *"a matcher that fails closed and reports a
zero looks exactly like a finding about the agency"* — a defect in our reader,
published as a fact about the source.

---

## THE COVERAGE PROFILE MEASURED EIGHT OF FOURTEEN HUB SOURCES

`102` counted eight facility-level sources. Six more hang off `facility_id` and
were never in the list, so a property with a crawled website, a slot finder, a
loyalty programme and device observations could read as `THIN - 1 source`.
Added: `game_finder`, `website`, `website_labor_demand`, `device_observation`,
`loyalty_program`, `vendor_metrics` (licensed), plus `digital_gaming` and
`digital_revenue` at tribe level.

| | before | after |
|---|---:|---:|
| properties profiled | 774 | **784** |
| STRONG — 4+ independent sources | 662 (85.5%) | **713 (90.9%)** |
| MODERATE — 2–3 | 112 | 68 |
| THIN — 1 | 0 | 0 |
| NONE | 0 | **3** |

The three `NONE` rows are `CEDAR-FAC-000011 Okanogan Bingo Casino`,
`CEDAR-FAC-000017 Numunu Pahmu Travel Plaza/Casino` and `CEDAR-FAC-000020
Golden Eagle Casino` — all appended from the NIGC roster today and carrying
nothing yet. That is a correct new zero, not a regression.

### The source stack, per facility, over 22 measured sources

    0 sources     3      8 sources   121
    2 sources    18      9 sources   123
    3 sources    24     10 sources    79
    4 sources    50     11 sources    55
    5 sources    54     12 sources    16
    6 sources    84     13 sources    10
    7 sources   139     14+ sources    8

**551 of 784 facilities (70.3%) now carry seven or more sources** on one
`facility_id`, all reaching the same entity by the same join.
`logs/164_facility_source_stack_2026-08-26.csv` has the per-facility ledger.

---

## REVIEW — 173 rows, and the first 20 are worth more than the rest

`review/gaming_facility_hub_unlinked_2026-08-26.csv` (169) ·
`review/gaming_universe_events_unlinked_2026-08-26.csv` (4)

| reason | n |
|---|---:|
| `NO_FACILITY_AND_NO_TRIBE` | 146 |
| `HUB_FACILITY_UNKEYED_BLOCKS_DOWNSTREAM` | **15** |
| `HUB_FACILITY_UNKEYED_NO_SOURCES_YET` | 5 |
| `MIRRORED_LINK_CARRIES_NO_TIER` | 3 |
| `NO_RULED_NIGC_NAME` | 4 |

### The 20 unkeyed hub rows are the whole leverage

**Twenty of the 784 facility rows carry no `tribe_id`, and fifteen of them block
1,767 downstream source rows from reaching an entity.** They are not obscure
properties:

    Barona Resort & Casino (CA)          San Manuel Casino (CA)
    Yaamava Resort and Casino (CA)       Foxwoods (CT)
    Akwesasne Mohawk Casino Resort (NY)  Spirit Mountain Casino (OR)
    Mohawk Bingo Palace (NY)             Angel of the Winds (WA)
    Lucky 7 Casino & Hotel (CA)          Okanogan Bingo Casino (WA)

Keying **one** hub row links every source hanging off it — that is the whole
point of a hub. This is the single highest rows-per-ruling item in the gaming
collection today, and it was invisible before, because the loss was distributed
across eleven files.

**The review file records one card per FACILITY, not one per affected row.**
1,736 vendor-capacity rows on one unkeyed hub row is one question asked 1,736
times, and a queue of 1,736 identical cards is a queue nobody reads. Each card
carries the downstream count, the per-file breakdown, and the property's own
`property_status` and `close_date` — so the record's dates are in front of the
ruler before they rule it against anything current.

### `MIRRORED_LINK_CARRIES_NO_TIER` — 7,983 rows, and it needs a ruling not a rule

`digital_gaming_revenue` (7,811), `digital_gaming_relationships` (154) and
18 loyalty programmes carry a `tribe_id` whose source row records **no
confidence tier at all** (`confidence_tier` is blank on all 10,661 digital
revenue rows). There is nothing to inherit, so `entity_tier` was left **blank
rather than assigned**. Those rows are entity-linked and un-tiered and must not
be read as tier A. Their `attribution_basis` is strong on its face — *"MGCB
names the tribal operator in its own column header"*, *"Connecticut DCP names
the tribal licensee"* — which is precisely why assigning them a tier here would
be the consumer-assigns-the-tier error wearing good evidence.

### 146 `NO_FACILITY_AND_NO_TRIBE`

71 website observations + 10 labor-demand rows on
`seed_host_with_no_verified_property_link` hosts (choctawcasinos.com,
cherokeecasino.com, turningstone.com and 19 more — multi-property operators
whose host does not name one property), 55 device observations, and 10
employment rows on `no_property_name_matched`.

---

## CODEBOOK — FRAGMENTS ONLY

`166` registered the new columns in **four fragments** —
`07_gaming` (+3), `07h_gaming_device_observations` (+6),
`16_digital_gaming` (+6), `07n_gaming_employment` (+6) — choosing the block with
**`87`'s own `match_group()`**, imported rather than reimplemented, so a
variable is registered in the block `87` will actually score the file against.
`published` and `access_tier` come from `41`'s own functions by import, so the
DUNS rule applies without being copied. `41` was **not run** (it writes the
master in `"w"` mode and would delete fifteen blocks) and
`codebook_master.csv` was not hand-edited; `cedar_codebook.py build`
regenerated it, **2,005 → 2,188** rows.

`entity_tier_basis` is registered `internal`; the other five are `public`. Every
one carries a written description, so `codebook_undocumented_public` did **not**
move.

### Five tables still score under the 0.60 gate and were NOT force-registered

`gaming_game_finder_observations` (0.32), `gaming_property_site_observations`
(0.50), `gaming_property_labor_demand` (0.48),
`gaming_property_universe_events` (0.31), `gaming_property_coverage` (0.23).

They were under the gate before this build too (the source audit measured 0.29,
0.54, 0.43, 0.17, 0.21). Four of the five **improved**; site observations moved
0.54 → 0.50 because its best-matching block changed. Giving them a block means
registering ~30 variables each with **no written description**, which would push
`codebook_undocumented_public` — a MUST-BE-ZERO gate metric already failing at
45 from concurrent work — higher. **Writing those definitions is a ruling, not a
rename**, and it stays queued as Tier-2 items 8/9/13 of the source audit.

---

## COORDINATION — WHAT WAS READ AND NOT TOUCHED

| file | rows | why untouched |
|---|---:|---|
| `data/staging/gaming_employment_osha_tribe_staged.csv` | 485 | another agent's staging file. `facility_id` blank on all 485 by design — OSHA rolls the ESTABLISHMENT up to the TRIBE, so these are `entity_level = tribe` rows and will need the mirror rung, not the facility rung, when they promote. |
| `data/staging/gaming_employment_form5500_staged.csv` | 2,046 | same. `LABOR_SOURCES_FOR_GAMING_2026-08-26.md` §252: *"A Form 5500 row keys to an EIN, never to a facility."* |
| `gaming_manufacturer_facts.csv` | 62 | its own column forbids property attribution |
| `dist/`, `cedar_press.db`, the shipping chain | — | staged in `docs/SHIPPING_RUNBOOK.md`, not run here |

**When the OSHA and 5500 rows promote into
`gaming_employment_observations.csv`, re-run `164`.** It is idempotent —
existing block columns are overwritten in place, backups use
`if not exists` so the originals stay pristine — and the two staged sets will
pick up `entity_level = tribe` + `row_tribe_id_mirror` automatically.

---

## FILES

```
code/164_link_facility_hub_sources.py             the four rungs
code/165_link_universe_events_to_hub.py           ruled-NIGC-name join
code/166_register_entity_link_block_fragments.py  codebook FRAGMENTS only
code/102_build_coverage_profile.py                +6 facility sources,
                                                  +2 tribe sources,
                                                  tribe_id -> tribe_entity_id,
                                                  absent-column now FATAL,
                                                  backup + .part + rename

review/gaming_facility_hub_unlinked_2026-08-26.csv      169
review/gaming_universe_events_unlinked_2026-08-26.csv     4
logs/164_facility_source_stack_2026-08-26.csv           784
logs/164_linkage_summary_2026-08-26.csv                  10

backups: data/clean/*.bak_2026-08-26_pre164   (12 files)
         data/clean/gaming_property_universe_events.csv.bak_2026-08-26_pre165
         data/clean/codebook/*.bak_2026-08-26_pre166  (4 fragments)
         data/clean/codebook_master.csv.bak_2026-08-26_pre166
```

`py -3 code/62_no_regression_check.py` before and after: **no new regressions.**
`codebook_variables` 2,005 → 2,188. `duns_marked_publishable` 0.
`codebook_undocumented_public = 45` is unchanged and is **not from this build**
— it is pre-existing from concurrent agents' fragments.

---

## SHIPPED IS PART OF DONE

Per the source audit's own closing rule, this log states it rather than leaving
it implied:

- **Rows written:** 80,320 new entity links across 12 tables + 68,211 tiers on
  the metrics table.
- **Codebook blocks registered:** `07_gaming`, `07h_gaming_device_observations`,
  `16_digital_gaming`, `07n_gaming_employment`. Five tables remain unregistered
  and are named above with their scores.
- **Ship rate after the next chain run:** unchanged by this build for the four
  registered blocks (all four were already past the gate) and unchanged for the
  five that were already under it. **This build did not move the ship rate. It
  moved what a shipped row can be joined to.**
- **Filters the bundler must apply:** `gaming_property_capacity_history.csv` and
  `gaming_facility_metrics.csv` are in `cedar_domain.LICENSED_SOURCE_FILES` and
  are refused by `87` **by name**. They were linked for internal join-ability
  only. **No licensed column was added to any table that ships**, and
  `casino_city_id` was not touched.

---

# ADDENDUM, same day — the 20 unkeyed hub rows are now 2

*Scripts `code/172`, `code/173`, `code/174`, `code/175`, plus a source fix to
`code/119` (NOT run) and an idempotency fix to `code/164`. Every number below is
printed by a build and logged.*

## WHAT MOVED

`gaming_facilities.csv`: **764 → 782 keyed**, 20 unkeyed → **2**.
`62_no_regression_check.py` before and after: **no regressions**;
`keyed_gaming_facilities` 764 → 782.

Measured downstream lift after re-running `164` — counted from a pre-run
snapshot of `entity_id` on every table, not projected:

| table | rows | entity_id before | after | lift |
|---|---:|---:|---:|---:|
| `gaming_property_capacity_history.csv` *(licensed)* | 64,181 | 62,445 | **64,181 (100.0%)** | **+1,736** |
| `gaming_employment_observations.csv` | 769 | 733 | **758 (98.6%)** | **+25** |
| `gaming_property_site_observations.csv` | 262 | 186 | **191 (72.9%)** | **+5** |
| the other eight hub tables | — | — | unchanged | 0 |
| **164's eleven tables** | | **144,986** | **146,752** | **+1,766** |
| `gaming_facility_metrics.csv` *(licensed, via 173)* | 68,211 | 65,436 | **67,172** | **+1,736** |
| **total new entity links** | | | | **+3,502** |

The review card predicted 1,767. **1,766 landed; the missing one is `VP-0109`,
refused on purpose** (below). The difference between 1,767 and 1,766 is one
row, and it is named.

**`gaming_properties.csv`, the view that SHIPS, was patched too** (`175`): 782
of 784 rows now carry `tribe_id`, and the 18 rows pick up **22 compact links
and 8 land-decision links** that were invisible while the tribe was blank —
every tribe-keyed roll-up on those rows was stale *by construction*, not merely
absent. 160's own rule: fixing the internal file and leaving the published one
wrong is worse than not fixing it.

## THE RULINGS — 18 keyed, 2 refused

Every one was settled from sources ALREADY ON DISK. **One network request was
spent in the whole build, and it produced a refusal, not a link.**

| facility | tribe | method / tier | what carried it |
|---|---|---|---|
| Spirit Mountain Casino (OR) | Grand Ronde | alias / **A** | NIGC operator address `PO Box 39, Grand Ronde OR`; the row's own tribe field misspells it "Grande" |
| Lucky 7 Casino & Hotel · Fuel Mart · VP-0095 | Tolowa Dee-ni' | alias / **A** | CGCC rows carry the facility_id; **81 FR 5019** records "previously listed as the Smith River Rancheria" |
| San Manuel Casino · Yaamava (VP-0013) | Yuhaaviatam | alias / **A** | CGCC rows carry the facility_id; **87 FR 4636** records the rename |
| Akwesasne Mohawk Casino Resort | Saint Regis Mohawk | alias / **A** | NIGC's own ordinance text names the "Saint Regis Mohawk Tribal Council" under its index name "St. Regis Band of Mohawk Indians" |
| Mohawk Bingo Palace *(closed 2013)* | Saint Regis Mohawk | alias / **A** | the 1994–2002 ordinance documents only — **nothing current** |
| Angel of the Winds | Stillaguamish | alias / **A** | three Secretary-approved WA compacts; Cedar's own VP-0213 |
| Lakeside Entertainment · Lakeside Gaming *(both closed 2005)* | Cayuga Nation of New York | alias / **A** | the row's tribe field plus state NY separates it from the Oklahoma Seneca-Cayuga Nation |
| Okanogan Bingo Casino | Confederated Colville | alias / **A** | **street-address identity** with CCP-865000 (`41 Appleway Rd` == `41 Apple Way Road`) plus NIGC contact `@colvillecasino.com` |
| Numunu Pahmu Travel Plaza/Casino | Comanche Nation | exact / **A** | NIGC lists the **same named general manager** as Comanche Red River Casino, `@comanchemail.com` |
| Kletsel Dehe Wintun Nation *(no casino)* | Kletsel Dehe Wintun | alias / **A** | CGCC RSTF-eligible list |
| Yokut Gas | Santa Rosa Rancheria | core / **B** | Cedar's own Tachi Palace row discloses "Tachi Yokut Tribe (Santa Rosa Rancheria)"; **no source names Yokut Gas itself** |
| Barona Resort & Casino | **CNSF-CPTNGR-BA** | containment / **B** | HAND RULING — see below |
| Foxwoods (VP-0042) | Mashantucket Pequot | core / **B** | NIGC contact `@mptn-nsn.gov`; CT DCP dataset; matches its two Cedar siblings' tier |
| Sage Hill Casino (NV) | Shoshone-Paiute (Duck Valley) | containment / **B, capped** | NIGC ordinance letter gives the tribe's own `Owyhee, NV 89832` |

**No tier was assigned by hand except Barona's.** The other 17 were produced by
`70.key_name` — the same function that keyed the other 764 rows of this file —
fed a tribe name **as published by a citable source**, with the state. The
input string and the resolver's verdict are both written into
`entity_match_basis` on every row.

### Barona is the one hand ruling, and it is a constituency question

The CGCC and NIGC both name the operator "Barona Group of Capitan Grande Band
of Mission Indians of the Barona Reservation". `resolve_entity` refuses it:
`ambiguous_containment:2:Capitan Grande, Capitan Grande Band`. The spine holds
the umbrella tribe **plus two constituency entities** — `CNSF-CPTNGR-BA`
(Barona) and `CNSF-CPTNGR-VJ` (Viejas). Cedar already keys all three Viejas
properties to `CNSF-CPTNGR-VJ` at tier B containment. **Keying Barona to the
umbrella `TRBF-CPTNGR-00` would merge two distinct gaming operations under one
id.** Ruled to `CNSF-CPTNGR-BA` at tier B — the identical treatment.

### The date rule, applied to three closed records

Mohawk Bingo Palace (2013-03-13), Lakeside Entertainment (2005-10-01) and
Lakeside Gaming (2005-09-30) are keyed **only from evidence contemporaneous
with their operating lives**. Where the current NIGC roster lists the same
street address under a `gocayuga.com` contact, that is recorded in the basis as
corroboration **of the operator only**, with the anachronism stated in words.
No close date was overwritten. No 2026 page testifies about a 2005 property.

### Proximity was not used, and it is why one row stays blank

No rung here reads a coordinate. Okanogan Bingo Casino is a **street_state**
match, which `157` already rates tier A — an address identity, not a distance.

## THE TWO THAT STAY BLANK

**`VP-0109` Konkow Valley Band — no spine entity exists.** NAGPRA notice
FR 2012-10497 names the "Koyomi'Kawi (Konkow) Maidu Tribe" and states in the
same breath that it is *"a non-Federally recognized Indian group"*.
"Cher-O-Kee Concow Rancheria" already sits UNRULED in
`entity_candidates_new.csv`, sourced from this very row. Keying it needs a
**recognition** ruling, not a gaming one. Blocks 1 row.

**`CEDAR-FAC-000020` Golden Eagle Casino — NIGC's record contradicts itself,
and that is the finding.** The marker (ids 21 and 31, a duplicate pair) is
filed under "Oklahoma Region", its address cell holds a **coordinate** instead
of an address, and its contact block reads
`P.O. Box 1330, Anadarko OK 73005 | Mspell@goldeneaglecasino.com`.

- **Leg one → Apache Tribe of Oklahoma.** NIGC's own gaming-ordinance approval
  letter of 2016-12-01 is addressed to *"Apache Business Committee, 511 East
  Colorado, Post Office Box 1330, Anadarko, OK 73005"* — the identical PO Box.
- **Leg two → Kickapoo Tribe in Kansas.** `goldeneaglecasino.com` is the
  operator site of the **Kansas** Golden Eagle Casino: *"Golden Eagle Casino is
  located on the Kickapoo Nation Reservation, just 6 miles West of Horton,
  Kansas."* Cedar already holds that as `CCP-72200` at tier A, and NIGC lists
  it separately under the **Tulsa** Region with a different contact,
  `jsimon@gecasino.com`.

The only thing that would break the tie is the coordinate, and a coordinate is
not a rung here. **Left blank.** It blocks 0 downstream rows. A human should
also decide whether this is a property at all, or a defective duplicate of
CCP-72200 that survived de-duplication only because its address cell carries no
state.

## `MIRRORED_LINK_CARRIES_NO_TIER` — the source DID record a tier, and the write was dead

Three cards, ~7,983 rows, asking *"what tier does this build's own linkage
earn?"*. Leaving the tier blank was right. **The premise was wrong.**

`119_build_digital_and_loyalty.py` builds every row as

    row = {k: "" for k in REL_FIELDS}      # every key already exists, empty
    row.update(kw)
    row.setdefault("tier", Tier.B.value)   # <-- NO-OP, forever

`dict.setdefault` writes only when the **key is absent**. The comprehension has
already created it. **Three columns shipped blank because of it:**

| file | column | intended | shipped |
|---|---|---|---:|
| `digital_gaming_relationships.csv` | `tier` | `Tier.B` | blank 154/154 |
| `digital_gaming_revenue.csv` | `confidence_tier` | `Tier.B` | blank 10,661/10,661 |
| `digital_gaming_revenue.csv` | `period_type` | `"month"` | blank 10,660/10,661 |

This is the same shape as the `tribe_id` / `tribe_entity_id` defect that made
`102` publish "declination_letter 0/774" for nineteen days: **a defect in our
writer, published as a fact about the source** — here as *"the source records
no tier"*, which then correctly propagated into 164 as a blank and into the
review queue as a question nobody could answer.

**The tier is B, and it is inherited, not assigned.** Two independent legs:
119's own code names `Tier.B.value` as the default for these columns, and
`digital_gaming_relationships.csv` **already carries `confidence = B` on
154/154 rows** through the kwarg path `setdefault` never touched. `period_type`
gets a third, data-internal leg: all 10,660 blank rows have a
`period_start`/`period_end` pair 28–31 days apart, measured before writing; the
one row that is not blank reads `none` and was left alone.

`174` restored all three **in place**. `119` was **fixed at source and NOT
run** — it is a full rebuild and would revert the six-column entity block, the
`133`/`168` collision in a new place. After re-running `164`:

    digital_gaming_relationships   entity_tier  (blank) x154   ->  B x154
    digital_gaming_revenue         entity_tier  (blank) x7,811 ->  B x7,811
    review MIRRORED_LINK_CARRIES_NO_TIER    3 cards -> 1

### The one card that remains is a correct blank

**9 `gaming_employment_observations.csv` rows stay untiered.** Their
`confidence` column holds **`low`** — high/medium/low, which `164`'s own
docstring already says is NOT a tier — and every one is a **PROJECTED** figure
from a NEPA planning document (`cedar_domain.may_promote()` refuses PROJECTED).
Mapping `low` → `C` would be manufacturing a tier to make a number move. Left
blank, said out loud.

## TWO DEFECTS FOUND WHILE DOING IT, ONE FIXED, ONE QUEUED

**`164` was not idempotent, and the second run degraded a published log.** Its
metrics branch short-circuited on `if "entity_tier" in mfields: nothing to do`
— so a re-run skipped the metrics table entirely, `stack` lost the largest
facility-level source, and `logs/164_facility_source_stack_<date>.csv` was
**rewritten** with 187 facilities reading "0 sources" that hold thousands of
metric rows each. Fixed: the recompute always runs, the column-add is what is
conditional, and `entity_id` is still never touched there (159 owns it).

**Also: the source-stack distribution printed earlier in this document is
`102`'s coverage profile over 22 sources, not
`logs/164_facility_source_stack_*.csv`.** 164's own stack counts only its
twelve tables, and **598 of 784 facilities appear in at least one of them**, so
its maximum is 7 and 187 facilities legitimately read zero. Two different
measurements have been carried under one filename. Do not reconcile them by
adjusting either.

**`82_build_gaming_property_view.py` has two live defects, reproduced
deliberately by `175` rather than fixed for 18 rows only:**

1. `n_deals_for_entity` matches a **short canonical name** against a free-text
   party string, exactly — so "Mashantucket Pequot" never matches
   "mashantucket pequot tribal nation" and "Saint Regis" never matches "saint
   regis mohawk tribe". Of the 13 entities keyed here, deals exist for 7 and
   **exactly one matches**. The column under-reports across the whole view.
2. 82 still globs `deals_*_additions.csv` only — the miscount
   `docs/FACT_CHECK_2026-08-06.md` B-1 identified and `START_HERE.md` records
   as repaired in `88` and `57`. **82 was missed.**

## SPILLOVER LEFT FOR A HUMAN — `review/gaming_facility_hub_rulings_2026-08-26.csv`

12 cards: 2 still-unkeyed (above), 6 property-identity duplicate questions, and
4 spillover items in other tables that this build's evidence would settle:

- **7 `gaming_ordinances.csv` rows indexed "St. Regis Band of Mohawk Indians"
  carry a blank `tribe_id`.** Their own text names the Saint Regis Mohawk
  Tribal Council = `TRBF-SRMHWK-00`. One ruling, seven rows.
- **2 ordinance rows indexed "Shoshone-Paiute Tribes"** are blank on
  `ambiguous_core`; their OCR text gives `Owyhee, NV 89832` = `TRBF-DUCKVY-00`,
  not Fallon.
- **3 ordinances whose PDFs are named `ftsillapachetribeofok-*` are keyed to
  `TRBF-APCHOK-00`.** The Fort Sill Apache Tribe is a different spine entity,
  `TRBF-FSCWSA-00`.
- **`ca_gaming_facilities_official.csv` CAFAC-00006/00070/00134 (Barona)** are
  blank for the same ambiguity this build ruled by hand; the `CNSF-CPTNGR-BA`
  ruling should be propagated by whoever owns `103`.

The six property-identity cards are duplicate questions, not entity questions:
Lucky 7 (VP-0095 / CCP-248000), San Manuel (VP-0013 / CCP-698400), Foxwoods
(VP-0042 / CCP-10600 / VP-0037), Sage Hill (VP-0393 NV / CCP-908000 ID — the
reason VP-0393's tier is capped), Okanogan (CEDAR-FAC-000011 / CCP-865000) and
Golden Eagle (CEDAR-FAC-000020 / CCP-72200).

## FILES

    code/172_key_unkeyed_gaming_facility_hubs.py        the ruling table, applied
    code/173_fill_gaming_metrics_entity_for_newly_keyed_hubs.py
    code/174_backfill_digital_gaming_tiers.py           the dead-setdefault repair
    code/175_sync_published_property_view_entities.py   the shipped view
    code/119_build_digital_and_loyalty.py               3 setdefault calls fixed, NOT RUN
    code/164_link_facility_hub_sources.py               metrics branch made idempotent

    logs/172_facility_hub_rulings_2026-08-26.csv                 18
    review/gaming_facility_hub_rulings_2026-08-26.csv            12
    review/gaming_facility_hub_unlinked_2026-08-26.csv    169 -> 149

    backups: gaming_facilities.csv.bak_2026-08-26_pre172
             gaming_facility_metrics.csv.bak_2026-08-26_pre173
             digital_gaming_{revenue,relationships}.csv.bak_2026-08-26_pre174
             gaming_properties.csv.bak_2026-08-26_pre175

Verified after every write: row counts unchanged, column lists byte-identical,
and **no populated cell overwritten** outside the columns each script declares.
