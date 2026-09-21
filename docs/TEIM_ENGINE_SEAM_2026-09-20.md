# What Cedar Press can take from teim-engine, and the one join that does not exist yet

*Measured 2026-09-20 against the checkouts of teim-team/cedar-press, teim-team/teim-engine
and teim-team/teim-app. File and line references are to those trees on that day. Report
only: nothing here has been built, and no change has been made to either repository's code.*

## The premise, corrected

The working assumption was that Cedar Press, or Cedar Grove, is already set up to read
from teim-engine and that the remaining work is adding proprietary data at the far end.

Neither reads it. The reason is structural rather than a missing configuration value.

- **cedar-press has no code touching teim-engine.** The only mentions are four lines of
  README prose (`README.md:69-74`, the sibling-repository paragraph) and
  `src/features/grove/appLink.js`, which resolves `VITE_APP_URL` — the *app's* origin, not
  the engine's. There is no client, no base URL, no environment variable.
- **teim-app's Grove does not read it either.** `src/features/grove/collection.js` holds
  the collection's descriptors, its supported findings, the figure specs behind the
  Overview cards and the CSV rows behind each download button, all in-module; its only
  import is `CLAIM_CLASS` from `./claims.js`. No fetch, no engine reference.
- **The engine exposes nothing to read.** All seven routes in `api.py` are run-scoped:
  `/health`, `POST /run`, `POST /run/mrio`, `GET /run/{id}`,
  `GET /run/{id}/impacts.json`, `GET /run/{id}/mrio_impacts.json`,
  `GET /run/{id}/report.pdf`. You can commission an economic impact analysis and read its
  result. You cannot ask the engine what it knows about a county.

So this is a new seam, not a wiring job. That matters for sequencing: there is nothing to
switch on, and the first piece of work is not an API.

## What the engine actually holds

Four distinct things sit behind the phrase "data we already need", and only two of them
are datasets in the sense Cedar Press means.

**1. The vendored state input-output tables** — `data/stateior_csv/`, nine years
(2015–2023) × 51 jurisdictions (50 states and DC; Puerto Rico is absent from every year,
per `run_manifest.csv`), BEA Summary level aggregated to 2-digit NAICS. Complete, on disk,
checksummed and versioned in the `reference_dataset` table. This is a real reference
dataset and the model's largest single input. Provenance is EPA's **stateior**, not BEA —
BEA publishes no state-level I-O tables; it is upstream, not the publisher. The EPA
package version behind the vendored snapshot **is not recorded** and is an open
reproducibility gap in the engine's own log.

**2. The `data_snapshot` table — a cache, not a dataset.** This is the item most likely to
be over-read. It is keyed `(source, geo_key, series_key, data_year)` with `series_key`
always the literal `"default"`; `read_cache` applies a 30-day freshness window; and
`data/cache.py` degrades to no-cache when the database is unreachable, by design. Rows
appear only as a side effect of runs, so coverage is *whatever has been analysed*, not
whatever exists. A county nobody has run is simply absent, and an absent row is
indistinguishable from a county with no data. Reading it as a national series would
silently return a convenience sample.

**3. The fetchers — the actual asset, and it is code.** Twenty-one `fetch_`/`load_`
functions across twelve modules in `data/`, carrying the judgement that took the engine a
year to accumulate: BEA's `NoteRef == "(D)"` disclosure flag, which sits in a field
*separate* from `DataValue` and which the engine read as a genuine zero until it was
caught; the CAINC5N LineCode↔NAICS-2 crosswalk, confirmed against BEA's own
`GetParameterValuesFiltered` rather than inferred from documentation; CBP's structural
exclusion of agricultural employees, non-employer establishments and most government
workers; land-area-weighted Gazetteer centroid aggregation. Cedar Press does not want
these numbers copied. It wants them fetched the same way.

**4. Run outputs** — the `impact_result` table, whose JSON shape was frozen and published
as a versioned contract in the engine's PR #19. This is the one surface already safe to
consume, and it is per-project, not per-place.

## Two geography questions, and only one of them is open

*This section was rewritten on the day it was written. The first version said
Cedar Press "carries no geography below the state, and no FIPS at all." That
was measured against the identity spine only, and generalising it to the
collections was wrong — they carry county FIPS and have since ADR-015. The
correction changes what the first piece of work is, so it is recorded rather
than quietly edited.*

**Transaction geography — built.** `docs/ARCHITECTURE_DECISIONS.md` ADR-015
(accepted 2026-09-02) decided that Cedar Press carries a joinable geographic
key on every row that can carry one and no charting code at all, and that Cedar
Grove renders the picture. That is done. The published samples carry
`geo_recipient_county_fips`, `geo_pop_county_fips` and their state-FIPS pairs,
populated in 10 of 10 rows in both `contractors/prime_contracts` and
`funding/federal_funding_transactions`, with recipient and place-of-performance
kept apart exactly as ADR-015 rule 1 requires. `natural-resources/resource_assets`
carries `fips_code`. This supersedes ADR-015's own 2026-09-02 measurement of
1,070 joinable rows out of 7.5 million; the gapfill it named as "the unlock
already on disk" has evidently been applied.

**Entity geography — open, and it is the one TEIM needs.** The identity
register (`data/spine/cedar_identity_register.csv`, 1,916 entities) carries
`state` as a two-letter postal abbreviation and no FIPS at all: a
case-insensitive grep for `fips` across the file returns **zero**.
`cedar_source_registry/nations.jsonl` carries `states` as a list of the same
abbreviations. So Cedar Press can say which county a dollar landed in. It
cannot say which counties constitute a nation's economy.

That distinction is the whole of the gap, because TEIM's unit of analysis is a
**region**, not a transaction. Every geography argument in the engine's `data/`
is a 5-digit county FIPS or a 2-digit state FIPS, and a run is defined by a
`county_fips_list`. A per-transaction county tells the engine nothing about
which counties to build a region from.

**The engine cannot close it from its side either.** `fetch_tribal_population`
(`data/employment_data.py:46`) takes `(tribe_name, county_fips, year)`, and its
own docstring states that the name "is used only for the cache key". The value
returned is the county's total AIAN population, whatever the affiliation. The
engine's decision log records what that cost: a validation region was built
from the wrong county for weeks, and that county's Native residents were
attributed to the tribe under study regardless of affiliation, because nothing
in the pipeline could tell the difference.

**ADR-015 rule 2 is already a warning about TEIM, and neither side has read it
as one.** "A county is not a reservation: reservations span counties and
counties contain fractions of reservations. A county-level difference is an
approximation and must be published saying so. AIANNH is the better key where
it can be had." TEIM's regionalization is county-keyed *by construction* — a
tribal region is a set of whole counties, and its location quotients,
apportionment weights and RAS row targets are all built from whole-county
totals. So every TEIM tribal result is precisely the approximation that rule
requires to be labelled, and the wrong-county episode above is what it looks
like when it goes wrong. The same objection, reached independently from two
repositories. It belongs in both.

## The seam, in the order it has to be built

1. **A nation → county FIPS crosswalk, with its basis recorded per row.** This
   is the join, and **neither side has it whole — but this repository is not
   starting from nothing, and an earlier draft of this line read as though it
   were.** Three artifacts already exist and the next implementation should
   extend them rather than compete with them:

   | Artifact | What it is |
   | --- | --- |
   | `data/raw/external/compacts/prior_extractions/tribe_aiannh_crosswalk_master.csv` | 303 rows, tribe → AIANNH **name** match, gaming-compact tribes only |
   | `code/873_build_aiannh_crosswalk.py` | The generator, with build / verify / selftest modes |
   | `data/clean/geo_aiannh_county_observed.csv` | **374** (AIANNH, county) pairs across **261** areas, per `docs/GEO_AIANNH_STATS.json` |

   Read what 873 says about its own output before treating 374 pairs as a head
   start. It is explicit that a complete county ↔ AIANNH overlap table *cannot*
   be built from what is on disk, because TIGER county polygons are not there,
   and that the observed file is **"a floor, never a census … Read it as
   evidence, never as coverage."** Two further limits it does not state in those
   words: 261 of 864 AIANNH areas are covered, and **2,876 of its 2,895 points
   come from three gaming files** — so the shape of that evidence is the shape
   of where casinos are, which is not the shape of the collections. The
   remaining work is to add county polygons and widen the point sources, in 873,
   under its verify mode. That is extension, not a second crosswalk. It belongs in Cedar's
   spine, because that is where entity identity already lives and where
   `cedar_uid` is minted; the engine should consume it, not own it. Each row
   needs the evidentiary treatment the rest of the register gets — a basis and
   a citation — because "which counties are this nation's service area" is a
   contested question with several defensible federal answers (the BIA
   jurisdictional area, the Census AIANNH tract, the nation's own statement)
   that do not agree, and the engine's regionalization reads whichever answer
   it gets as fact. Per ADR-015 rule 2, carry AIANNH where it can be had and
   record the county set as the approximation it is, rather than as the truth.
2. **Postal → state FIPS, preserving the one-to-many that already exists.**
   Mechanical, and it unblocks state-level engine calls without waiting for (1)
   — but **not as a single column.** `cedar_source_registry/nations.jsonl`
   carries `states` as a *list*, and 15 of its 584 nations have more than one:

   ```
   AZ,NM,UT   Navajo Nation, Arizona, New Mexico, & Utah
   ND,SD      Standing Rock Sioux Tribe of North & South Dakota
   CO,NM,UT   Ute Mountain Ute Tribe
   AZ,CA,NV   Fort Mojave Indian Tribe of Arizona, California & Nevada
   ...        (11 more)
   ```

   A single postal-to-FIPS column keeps one of them and discards the rest, and
   the engine's region is a county set — so the result is not an error, it is a
   **regional input that is quietly short two states for the largest nation in
   the country.** Nothing downstream can detect that, because a smaller region
   is a valid region. Carry the existing `states` list through, or give the
   register a nation → state relation; do not flatten it to fit a column.
3. **Only then, a read surface on the engine — and it resolves a vintage, it
   does not refetch.** An earlier draft of this step said a route keyed by
   geography and year should answer "from the fetchers rather than from
   `data_snapshot`, so a cache miss fetches instead of returning silence."
   **That is cache semantics wearing a different name, and it contradicts
   ADR-044 in this same change.** Keyed only by geography and year, with a live
   fetch on a miss, the same request returns revised federal values later with
   no Cedar release, no pinned vintage, no checksum and no semantic diff — which
   is exactly the `data_snapshot` behaviour ADR-044 rules out for anything a
   subscriber pays for.

   A read resolves **a specified vintage** and says which one it answered from.
   A miss is an honest miss — the vintage is not published — not an invitation
   to go and get whatever the federal source says today. Refreshes happen
   through an explicit versioned update path that mints a new vintage, and the
   two operations never share a code path. `data_snapshot` stays what it is: an
   implementation detail of a run, not a public dataset, and nothing outside the
   engine reads it.
4. **A client in cedar-press**, alongside the existing FastAPI service in
   `server/`, following the arrangement already in place for the platform — a
   base URL, a bearer key, a feature flag, and a degraded answer rather than an
   error when the engine is not configured.

Steps 1 and 2 are Cedar Press work and need nothing from the engine. Step 3 is
engine work and should not start before step 1 exists, because until there is a
join the route has no caller and its shape would be guessed.

**What the built transaction geography already buys, separately.** County FIPS
on the money rows is a join against the engine's *own* geography today, with no
crosswalk needed — federal obligations landing in a county, beside that
county's earnings, employment and industry structure. That is a Cedar Grove
picture rather than a TEIM input, it needs none of steps 1–4, and it is
probably the cheapest real thing this seam can produce first.

## Putting Cedar's proprietary data into the engine

The engine has a written rule for this, and it is worth meeting on its own terms rather
than discovering it at review. `CLAUDE.md` §4 requires, for any new data, a note on why
the model needs it, where it enters the model, and why this source over the alternatives.
§5 holds the data inventory, one row per dataset with vintage, dollar year, geography and
suppression treatment. §6 sorts every input into required (the math is undefined without
it — hard-error and stop) or optional (impute and flag, so validation can separate
imputed-cell error from model error).

A nation → county crosswalk enters as a **required** input under that rule, because it
defines the study region and the engine already hard-errors on a missing geography
definition. That is the right classification and it has a consequence worth stating: once
the engine depends on the crosswalk, a nation absent from it cannot be analysed at all,
rather than analysed badly. Given what the wrong-county episode cost, refusing is the
better failure.

## What this does not settle

- **Which federal definition of a nation's counties is authoritative.** Named above as the
  hard part of step 1; not resolved here.
- **Whether Cedar Press should read the engine at all, or read a dataset the engine
  publishes.** A read route couples two release cadences. A periodically exported, versioned
  dataset does not, and Cedar Press already knows how to hold one. Step 3 above assumes a
  route because that is what the platform does for the Cedar analyst service; the
  alternative is cheaper and has not been costed.
- **Authentication and origin.** The engine's API key posture and the cross-origin
  constraints measured in `docs/PLATFORM_INTEGRATION_2026-09-06.md` apply here too and are
  not re-derived.
- **Anything about `data_snapshot` as a product.** It is a cache. The one recommendation
  this document makes without qualification is that nothing outside the engine should read
  it.
