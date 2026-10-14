# Cedar data to Cedar Press

This directory owns Cedar Press's tracked product metadata.

## Refresh the served data

The site serves ten-row previews of verified Lumecon-data releases. Nothing in
this repository fetches them: a refresh is done by hand, in this order. CI does
not run it. CI checks that the committed files agree with each other, and (in
the `gaming-release-consumer` job) that every receipt in
`verified-preview-releases.json` is a release the producer verified.

1. **Build and verify the releases in Lumecon-data**, and note the producer
   commit. Each new release must also be recorded in the producer's
   `docs/cloud-review-inventory.json`, or the check in step 9 fails.
2. **Write the queue file:** a JSON array of exactly 15 objects, one per
   collection (Gaming included), each with `collection`, `release`, `store`
   (the release store's absolute path) and `manifest_sha256`, and optionally
   `expected_public_rows`. Neither repository holds the queue or the store.
3. **Stage.** With the producer checked out clean at that commit:

   ```
   LUMECON_ENVIRONMENT=review PYTHONPATH=<Lumecon-data>/src:server TEMP=<review volume> \
     python3 scripts/stage_verified_previews.py --repo . --producer <Lumecon-data> \
       --producer-commit <sha> --queue <queue.json> --output <new directory> --updated <YYYY-MM-DD>
   ```

   It writes only into the new directory, and writes `READY.json` last; a
   directory without it is incomplete. To refresh some collections only, add
   `--refresh-existing`, then `--collection <id>` and
   `--expected-existing-release <id>=<release>` for each. (`--admit-existing`
   with `--apply` is the separate admission path for Giving and PLOT, and the
   only mode that installs anything.)
4. **Install by hand.** Review the staged diff, copy each file under the
   directory's `assets/` to the same path here, keep the Gaming exclusion and
   the production pin files, then `git add` the samples: step 7 reads the Git
   index, not the working tree.
5. **Review the descriptors.** The stager updates each collection's count,
   release and date, and carries its prose (`name`, `short_name`, `tracks`,
   `sources`, `method`) forward from the previous manifest. Nothing compares the
   prose with the producer, so read each refreshed collection's text against
   its release.
6. `python3 scripts/render_sample_downloads.py` (needs `pip install -e server`)
   writes the customer tables in `public/data/cedar/downloads/` and
   `sample_downloads.json`.
7. `node scripts/measure-samples.mjs`, then `node scripts/derive-explore.mjs`.
8. If a collection's version changed, `node scripts/record-release.mjs`. Then
   `node scripts/dump.mjs --kind press --target server/cedar_press/_press_data.json`
   (without `--target` it only prints), `node scripts/seo-head.mjs` and
   `node scripts/docs-markdown.mjs --kind all`.
9. **Check:** `make check-generated`, `make test-python`, `npm run test`,
   `npm run test:smoke` and
   `python3 scripts/check_receipts_against_producer.py --producer <Lumecon-data>`;
   then review the site in a browser before committing.

## Add a collection

A collection is built and verified in Lumecon-data; this repository serves
previews of its verified releases and, for subscribers, the full downloads.

1. **Build it in Lumecon-data**, following "Onboard a collection" in its
   `docs/data-contracts.md` and its `docs/developer-guide.md`: a reviewed source
   profile under `intake/profiles/` (`lumecon-data intake-check`, then
   `lumecon-data intake-plan --collection <id>`), a bounded producer under
   `src/lumecon_data/collections/` added to `lumecon-data collection-build`,
   then `lumecon-data collection-build <id> ...` and
   `lumecon-data verify --dataset <dataset> --release <release> --root <store>`.
   Record the release in the producer's `docs/cloud-review-inventory.json`.
2. **Declare it here.** Add the collection to `scripts/stage_verified_previews.py`
   (`EXPECTED`, and its descriptor prose in `ADDITIONS`) and to the queue size in
   "Refresh the served data", step 2. Give it entries in `field_map.json` and
   `codebook.json`, and, where it needs reviewed presentation, in
   `explore.overrides.json`, `source_display.json` and `source_presentation.json`.
   Add it to the storefront catalog (`pressCatalog.js`); the Press snapshot
   regenerated in the refresh's step 8 carries it to the API, and a test holds the two
   catalogs to the same collections. A collection with Cedar Grove components
   also needs `server/cedar_press/governed_collections.py` and its
   `<id>_component_contracts.json` here.
3. **Stage, install and check** with "Refresh the served data", steps 2 to 9.
   Tests that count collections (for example the sixteen targets in
   `server/tests/test_shared_release_collections.py`) move with it.
4. **Full downloads** need the server-only catalog settings and a rehearsal
   (`server/tests/release_download_rehearsal.py`, or
   `shared_collection_rehearsal.py` for component collections), as
   `server/README.md` describes.

Do not add another transform, a handwritten release schema or a
collection-specific branch in the shared adapters; the producer owns the data.

## Tracked metadata files

These five small product contracts are **tracked Git inputs**. `/data/*` is
ignored, and narrow `.gitignore` exceptions name these files; unapproved sibling
JSON, bulk CSV, raw data and restricted decisions stay ignored.
Do not replace these files with consumer-specific copies or regenerate missing
release history from the latest dataset. Large data belongs in the governed
versioned data store; this repository retains the metadata for the release it serves.

| File | Authority and required inputs | Consumers | Fresh-clone and release rule |
|---|---|---|---|
| `codebook.json` | Curated field definitions; no JSON generator. `scripts/docs-markdown.mjs --kind codebook` generates its Markdown view, not this source. | `src/features/grove/explore.js` supplies headings/record meanings; codebook and guide generators; Explore tests and `server/tests/test_collection.py` compare approved fields. | Commit the reviewed source. Definitions cannot be reconstructed from column names alone. Generated documentation is reproducible and freshness-checked. |
| `collections.manifest.json` | `scripts/stage_verified_previews.py`, from verified Lumecon-data releases: it stages each collection's preview in a new directory, which is then installed here by hand (see "Refresh the served data"). | `collection.js` and `server/cedar_press/collections.py`, then catalog, filters, sources, citations, downloads and API; Explore, guides, codebook, field-map, sample, release and SEO generators. | Commit the installed snapshot. A fresh product clone can serve and test it, but cannot regenerate it without the pinned Lumecon-data releases and the staging queue. |
| `field_map.json` | Curated publication/column decisions under the owner's 2026-09-05 public dataset specification (`docs/PUBLIC_DATASET_SPEC_2026-09-05.md`, at the tag `data-workspace-final`); no JSON generator. `scripts/docs-markdown.mjs --kind field-map` generates its two review documents. | The API's spreadsheet and repository modules (`server/cedar_press/spreadsheet.py`, `repository.py`), `collections.py`, the stager, `preview_definitions.py`; guide/field-map generators, Explore tests and the Python collection and preview-definition tests. | Commit reviewed decisions. A clone can test fixtures and sample compatibility; proving mappings on full customer files needs the full-data release job. Do not infer a decision for an undeclared column. |
| `releases.json` | `scripts/record-release.mjs`, using the manifest **and retained prior ledger**. | `src/features/grove/pressReleases.js`, release feed and citations, release tests; `scripts/dump.mjs --kind press` includes that catalog in the Python API snapshot. | Commit append-only release history. `--check` verifies current manifest/ledger consistency without rewriting history. The latest manifest cannot recreate superseded releases. |
| `samples.published.json` | `scripts/measure-samples.mjs`, using the manifest plus Git index and the matching sample bytes in `data/cedar/samples/`. | `collection.js` and Python `collections.py` determine sample availability, then download/UI/API paths; sample and collection parity tests. | Commit the deterministic measured snapshot with its inputs. `--check` and `--selftest` distinguish committed, absent, untracked and unstaged samples. A file merely present on one machine is not a published sample. |

The supported freshness surface remains `make check-generated`: codebook, Explore,
field-map, guides, Press snapshot, samples, release ledger and SEO checks. Both PR CI and deployment
call it. The product build bundles the tracked contracts; it does not fetch bulk
inputs or invent new release metadata. `pressDownload.test.js` now checks all five
are tracked and exempted by name, and proves unrelated data remains ignored.
`server/tests/test_collection.py` also requires all five in the index, retaining
its existing checks for the Explore contracts.

For a new release, follow "Refresh the served data" above: review changes to the
same contracts and sample files, record the new version without replacing
history, and commit the resulting metadata snapshot as one change. A passing
static build is not a completed data release.
