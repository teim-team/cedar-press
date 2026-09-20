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

## The join key does not exist, in either direction

This is the decisive finding, and it is measurable in one line each way.

**Cedar Press carries no geography below the state, and no FIPS at all.** The identity
register (`data/spine/cedar_identity_register.csv`, 1,916 entities) has columns
`cedar_uid, cedar_entity_id, canonical_name, entity_class, class_since_basis,
former_names, minted, register_status, federal_register_legal_name,
federal_register_legal_name_basis, federal_register_legal_name_url, state, minted_basis`.
`state` is a two-letter postal abbreviation (`AK`). A case-insensitive grep for `fips`
across the file returns **zero**. `cedar_source_registry/nations.jsonl` carries `states`
as a list of the same abbreviations.

**The engine is keyed on FIPS and holds no postal crosswalk.** Every geography argument in
`data/` is a 5-digit county FIPS or a 2-digit state FIPS, and the only state mapping in the
repository, `_FIPS_TO_STATE` in `data/io_tables.py:161`, maps FIPS to a state *name*
(`"40": "Oklahoma"`). Postal `AK` to FIPS `02` is a crosswalk neither repository has.

**And the engine cannot resolve a tribe to a place either.** `fetch_tribal_population`
(`data/employment_data.py:46`) takes `(tribe_name, county_fips, year)`, and its own
docstring states that the name "is used only for the cache key". The value returned is the
county's total AIAN population, whatever the affiliation. The engine's decision log
records what that cost in practice: a validation region was built from the wrong county
for weeks, and the county's Native residents were attributed to the tribe under study
regardless of affiliation, because nothing in the pipeline could tell the difference.

So the gap is symmetric. Cedar Press knows which nation and cannot say where; the engine
knows which county and cannot say whose. That is the same missing table seen from two
sides, and it is the first thing to build.

## The seam, in the order it has to be built

1. **A nation → county FIPS crosswalk, with its basis recorded per row.** This is the
   join, and it is the proprietary data. It belongs in Cedar's spine, because that is
   where entity identity already lives and where `cedar_uid` is minted; the engine should
   consume it, not own it. Each row needs the same evidentiary treatment the rest of the
   register gets — a basis and a citation — because "which counties are this nation's
   service area" is a contested question with several defensible federal answers (the BIA
   jurisdictional area, the Census AIANNH tract, the tribe's own statement) that do not
   agree, and the engine's regionalization reads the answer as fact.
2. **A postal → state FIPS column** on the register. Trivial, mechanical, and it unblocks
   every state-level engine call without waiting for (1).
3. **Only then, a read surface on the engine.** A reference-data route keyed by geography
   and year, answering from the fetchers rather than from `data_snapshot`, so a cache miss
   fetches instead of returning silence. The cache stays what it is: an implementation
   detail of a run, not a public dataset.
4. **A client in cedar-press**, alongside the existing FastAPI service in `server/`,
   following the arrangement already in place for the platform — a base URL, a bearer key,
   a feature flag, and a degraded answer rather than an error when the engine is not
   configured.

Steps 1 and 2 are Cedar Press work and need nothing from the engine. Step 3 is engine work
and should not start before step 1 exists, because until there is a join the route has no
caller and its shape would be guessed.

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
