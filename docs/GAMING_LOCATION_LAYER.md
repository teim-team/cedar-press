# Gaming Property Location Layer

> ## ⚠ DO NOT QUOTE THE TIER DISTRIBUTION AT LINE ~218 — it cannot be what it says
> *Banner added 2026-08-28 during doc consolidation. Source:
> `docs/DOC_CONTRADICTIONS_2026-08-26.md` item **C5**. Everything else in this
> document stands.*
>
> The line reads *"Tier distribution of **publishable rows**: A 689 · B 101 ·
> C 681"*, which **sums to 1,471**. Two lines later the document says *"1,067
> geocoded rows."* Measured 2026-08-26: **1,068 rows** are `publishable = Y`
> with coordinates.
>
> - 539 (properties) and 1,068 (observation rows) are compatible — different units.
> - **1,471 is compatible with neither**, and 1,067 is off by one against 1,068.
> - Line 218 is *probably* measuring all 2,212 rows, **but that is a guess and it
>   is undecidable from the files.** It was not corrected in place for exactly
>   that reason — a guessed correction is worse than a flagged one.
>
> **Use 1,068 for publishable geocoded observation rows.**

*Built 2026-08-12 by `code/143_build_gaming_property_locations.py`.
Output: `data/clean/gaming_property_locations.csv` — 2,212 observations on 751
of the 774 properties.*

`data/clean/gaming_facilities.csv` was **not** touched. The merge is proposed at
the end of this file, not performed.

---

## THE FINDING THAT REFRAMED THE JOB

`gaming_facilities.csv` looks 89% geocoded: 688 coordinates, 677 addresses.
Almost none of it can ship, and the vendor share is **larger than the column
names suggest**.

> **`tribal_property_list` IS ALSO CASINO CITY.** It is the *Casino City Tribal
> Property List* — `23d_build_gaming_facilities.py` says so in as many words
> (`open_date_basis = "Casino City Tribal Property List, 'Open Date'"`).

So the vendor-derived share is not the 440 rows naming `casino_city_press`. It
is **610 of 774**. Only `votingpatterns_canonical` (164 rows) was free-sourced
end to end.

That inverts the stated priority. The brief said 68 of the 86 properties with no
coordinate "already have an address to work with."

> **All 68 of those addresses are Casino City's, and all 86 uncoordinated rows
> are `tribal_property_list`-sourced.**

Geocoding them would have produced 68 coordinates that still cannot ship.
Re-geocoding a vendor address does not launder it: the address is the vendor's
fact and the coordinate is derived from it. What looked like the cheapest win in
the brief was the one route that buys nothing.

---

## WHAT WAS BUILT

| | before | after |
|---|---:|---:|
| properties with a **publishable** address | 0 | **536** |
| properties with a **publishable** coordinate | 0 | **539** |
| properties with a **publishable** 2020 census block | 0 | **539** |
| properties with any publishable location row | 0 | **560** |
| properties with **nothing** publishable | 774 | **214** |

"Before = 0" is not rhetorical. Every coordinate in `gaming_facilities.csv` was
either Casino City's or a votingpatterns hand-curation carried with no URL,
retrieval date or quote — nothing in that file was in a shippable state.

Best publishable coordinate per property, by method:

| method | properties |
|---|---:|
| Census Geocoder, `Exact` | 228 |
| NIGC published point | 163 |
| votingpatterns compiled point | 112 |
| Census Geocoder, `Non_Exact` | 36 |

---

## SOURCES USED, AND WHAT EACH IS AUTHORITATIVE FOR

**1. NIGC gaming location map** — 490 markers, already on disk at
`data/raw/external/nigc/locations/nigc_gaming_locations_map6_2026-08-06.json`.
A federal regulator publishing an address and a point for every location it
maps. 350 attached to existing Cedar IDs through the **existing deterministic
roster match** in `review/nigc_roster_diff_2026-08-06.csv`. No new match was
invented and **no new property ID was minted**; the 140 unmatched markers stay
staged in `review/gaming_additions_2026-08-06.csv` behind
`do_not_append_without_ruling`.

**2. US Census Geocoder** — free, no key, no licence. Two distinct services kept
as two distinct observations because they are two different facts:
`geographies/addressbatch` (address → coordinate + block, with a match quality)
and `geographies/coordinates` (coordinate → block). Benchmark
`Public_AR_Current`, vintage `Census2020_Current` — the 2020 block vintage that
LODES8 uses, so the block joins straight through.

**3. votingpatterns canonical casino addresses** — 411 records, 405 attached.
Addresses and coordinates compiled from each property's **own official
website** (the `source` column names the site). Free and official in origin; the
weakness is documentation, not licence, so these publish at **tier C** with the
gap stated on every row.

**4. California CGCC licensed-facility list** — 77 city/county observations on
already-keyed facility IDs. No street address, therefore no coordinate, and the
row says so.

**5. Casino City Press / Tribal Property List** — 592 observations recorded,
every one `publishable = N`, so the vendor dependency is visible per property
instead of inferred from a column name.

**6. Indian Gaming Dataset** — 149 addresses. Not Casino City, but the file
states no origin for its address column: no URL, no retrieval date, no quote.
`publishable = N`. A source of unknown provenance is not a free source, it is an
unsourced one.

### Refused

- **`bia_compact_properties_geocoded_v2.csv` (766 rows).** Its addresses are
  regex-extracted from compact PDF text and are frequently not property
  addresses at all — `11 Supreme Court`, `202 East Drive`. 590 of 766 are
  `No_Match`, `casino_name_candidate` is null on nearly all of them, and nothing
  keys a row to a facility. Attaching a compact's stray street string to a
  casino is the false-attribution trap.
- **Property websites.** Another agent holds those hosts for the capacity build;
  ~100 `logs/_HOSTLOCK_*.json` files exist for casino domains. Not crawled.
- **46 vendor-only properties that have an unmatched NIGC marker in their own
  city and state.** Deliberately not auto-attached — see the counter-example
  below.

---

## FOUR FINDINGS ABOUT THE SOURCES

### 1. NIGC reuses one point across a tribe's properties

**105 of 490 markers share a coordinate with another marker, across 30 shared
coordinate values.** Nineteen White Earth locations sit on one point; eighteen
Chickasaw locations on another; six Ho-Chunk, six Oneida, three Tulalip.

Those are tribal or administrative markers, not property positions — and the
marker's **address is property-specific while its coordinate is not**. So the
coordinate is **withheld** from the latitude/longitude fields on the 50 affected
attached rows, preserved verbatim in `coordinate_withheld_reason`, and the
address is still used to geocode a real point. Publishing a tribe-level point in
a column called `latitude` on a property row is the same error as writing
`AUTHORIZED_MAXIMUM` into `ACTIVE_FLOOR_COUNT`.

### 2. NIGC's coordinate is sometimes simply wrong, and its own address proves it

`Northern Edge Navajo Casino` — NIGC address `2752 N36, Fruitland NM 87411`,
NIGC coordinate `33.358531, -104.530976`, which is **Roswell, 492 km away**.
`Running Creek Casino` — a P.O. Box in Upper Lake CA against a point near Santa
Rosa, 95 km off.

**173 conflicts are the same source disagreeing with itself** (its published
point against the Census geocode of its own address), separate from 249 where
two different sources disagree. Median separation across all 422 is 4.5 km; 189
exceed 5 km. All are retained in
`review/gaming_locations_geocode_conflicts_2026-08-12.csv`, typed by
`conflict_class`, with a `YOUR_RULING` column. Nothing is averaged. A source
disagreeing with itself is a finding, not a bug to smooth over.

### 3. TIGER cannot geocode tribal-land casino addresses at anything like the
### normal rate

**263 of 639 free-sourced addresses returned `No_Match` — 41%.** A national
batch typically fails in the single digits to low teens.

The cause is not spelling. A second pass that dropped the city and let the ZIP
carry the locality — the only safe retry, since the street is unchanged and
nothing is invented — recovered **1 of 261**. The failures are casino access
roads on tribal land that are absent from TIGER's address ranges: `777 San
Manuel Blvd`, `125 Ehlers Way`, `777 Casino Way`, `100 Kawi Place`.

This is a structural gap in federal address coverage on Indian lands, and it is
why the NIGC published point and the votingpatterns point are kept as
first-class observations rather than discarded once a geocoder exists.

Addresses were **not rewritten** to force a match — no hyphen stripping on the
Coachella Valley grid addresses, no abbreviation expansion, no unit removal. A
transformed address is a different claim.

### 4. A candidate marker in the same city is not a match

46 of the 214 unsourceable properties have an unmatched NIGC marker in their own
city and state, and several are obviously the same property (`Kewadin Sault Ste.
Marie` ↔ `Kewadin Casino, Hotel & Convention Center`; `Mole Lake Casino Lodge`
↔ `Mole Lake Casino and Bingo`). A one-to-one city test would attach them
automatically. It was not used, because of one case:

> **Flandreau SD.** The only unmatched NIGC marker there is `Royal River Casino
> and Hotel`. The only vendor-only Cedar row there is `First American Mart` — a
> convenience store. A one-to-one city test would have booked the casino's
> address onto the c-store.

All 46 go to `review/gaming_locations_vendor_only_2026-08-12.csv` with the
counter-example printed on every row.

---

## THE CAVEAT THAT TRAVELS ON EVERY ROW

`coordinate_scope_note`, populated on all 2,212 rows:

> The coordinate locates the gaming **property**, not the enterprise. Tribal
> gaming properties commonly sit on a mixed-use campus — hotel, travel plaza,
> convenience store, clinic, tribal administration — so a census block
> containing this point may contain several establishments and several
> employers. LODES block workplace jobs are jobs located in the block, never
> casino payroll.

It is a column rather than a line in a README so a join cannot strip it. This
matters directly for the modelling this layer was built for: script 101 already
records the same rule for LODES, and this layer is what supplies its block key.

---

## PUBLISHABILITY, STATED PER ROW

`publishable` is Y only where the address **and** the coordinate both come from
a free official source. `publishable_reason` gives the ground in words on every
one of the 2,212 rows — it is never left to be inferred from a source name.

The laundering rule is enforced structurally: a Census-geocoded row carries
`address_source_system` naming whichever source supplied the input address, and
inherits `publishable = N` if that source is a vendor. **Vendor addresses were
never sent to the geocoder at all** — it would have bought nothing shippable and
would have put vendor strings on a federal host.

Verified on the built file: **0 rows with `publishable = Y` trace to Casino City
through either `source_system` or `address_source_system`.**

~~Tier distribution of publishable rows: A 689 · B 101 · C 681.~~

> **DO NOT QUOTE THIS LINE. Flagged 2026-08-26 — it cannot be what it says it is.**
> 689 + 101 + 681 = **1,471**, but only **1,068 rows** in
> `data/clean/gaming_property_locations.csv` are `publishable = Y` with both a latitude and
> a longitude (measured 2026-08-26). A distribution over publishable rows cannot exceed the
> number of publishable rows. It is most likely a distribution over some larger set — the
> full 2,212 rows, or all rows carrying a tier — but **that is a guess and the question is
> undecidable from the files.** Recompute before using it.
>
> Two other units on this page are fine and are worth stating explicitly, because they look
> like a contradiction and are not: **539 is a count of PROPERTIES** (line 44) and **1,068 is
> a count of OBSERVATION ROWS**. Several observations can attach to one property. The
> "1,067 geocoded rows" below is off by one against today's file.

### `county_fips`, `census_tract`, `census_block` are TEXT

Zero-padded to 5 / 11 / 15 characters. 287 of the 1,067 geocoded rows begin with
a leading zero (`01053`, `090117011005003`). Read them with
`dtype=str`; a numeric read silently destroys every Alabama, Alaska, Arizona,
Arkansas, California, Colorado and Connecticut row.

---

## PROPOSED MERGE INTO `gaming_facilities.csv`

Not performed. Proposed, so the owner of that file rules on it.

1. **Do not overwrite `latitude` / `longitude` / `address` in place.** The
   incumbent values are Casino City's and are still wanted for QA — the
   vendor-vs-official comparison is exactly how the capacity layer was
   validated. `distance_to_incumbent_coordinate_m` on every publishable row is
   that comparison, already computed.
2. **Add six columns**, sourced from the best publishable observation per
   property under the ranking `Exact` > `NIGC published point` > `Non_Exact` >
   `votingpatterns compiled point`:
   `publishable_latitude`, `publishable_longitude`, `publishable_county_fips`,
   `publishable_census_tract`, `publishable_census_block`,
   `publishable_location_observation_id` (the pointer back into this file, which
   carries the source, the quote, the date and the reason).
3. **Extend the `LICENSED_SOURCE_FILES` gate in
   `code/87_build_dataset_notes.py`.** This file is mixed — 741 of 2,212 rows
   are `publishable = N`. Either register it with a row-level filter on
   `publishable == 'Y'`, or have 87 refuse it outright until one exists. A
   dataset notes contract that ships the whole file ships 592 Casino City
   addresses.
4. **Cascade.** `code/101_build_lodes_block_employment.py` currently geocodes
   properties itself; it should read `census_block` from here instead, so the
   LODES join and the published location layer cannot drift apart.

## OPEN, IN PRIORITY ORDER

1. Rule the 46 candidate NIGC pairs in
   `review/gaming_locations_vendor_only_2026-08-12.csv`. Highest yield per
   minute of anything on this list — each ruling converts a vendor-only property
   into a publishable one at zero fetch cost.
2. Rule the 173 `SOURCE_DISAGREES_WITH_ITSELF` conflicts. Where NIGC's address
   geocodes `Exact` and its own point is kilometres away, the address is
   almost certainly right — but that is a ruling, not an inference.
3. The remaining 168 vendor-only properties need the property's own website or a
   state regulator's licensed-facility list. The website route is held by the
   capacity agent; coordinate rather than duplicate.
4. State regulator address lists were **not swept** for this build. `NOT_CHECKED`,
   not `NOT_FOUND` — nobody looked.
