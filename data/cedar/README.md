# Cedar data to Cedar Press

This directory owns Cedar Press's tracked product metadata. The release proofs,
fixed review ranges and limitations of 2026-09-24 to 26 are in
`docs/HAVALA_INFRASTRUCTURE_REVIEW.md`, at the tag `data-workspace-final`.

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

## Add a collection to the governed release path

Onboard one approved flagship with its existing collection ID and declared grain.
This does not authorize production publication or certify ancillary tables. Reuse
the existing runner, manifest, catalog and download adapter.

1. **Pin evidence and gates.** Run `python code/build.py plan <collection>`, then
   inspect its stages' inputs. Missing workspace data can leave this acquisition
   plan incomplete; a snapshot pilot does not certify that acquisition rebuilt.
   Record source, register and decision hashes; source
   dates, rights, grain and primary key. Agents do not impose publication holds
   (owner ruling 2026-10-04). Preserve rows and issued
   IDs. Resolve owed fields through `data/cedar/field_map.json` and existing owner
   decisions; never discard qualifications or rematch identities to pass.
2. **Register the producer in Lumecon Data.** Follow its authoritative
   `docs/data-intake.md` and `docs/developer-guide.md`: a reviewed source profile,
   existing `DatasetContract`, bounded producer under `collections/`, and the
   existing `collection-build` dispatch. Cedar's `RELEASE_PILOTS` is only a
   compatibility allowlist, not the source schema or producer registry.
   Preserve existing grains/keys during migration and regenerate contracts
   through their owners. Lumecon's `DatasetContract`,
   `ingest_csv`, `build_release` and `verify_release` own governed releases.
   `registered_reference` preserves existing scalar CE links: null stays null,
   unknown fails; preserve plural associations separately. The fixed
   `REFERENCE_PRESERVATION_AUTHORITY` records preservation authorization, not
   historical identity approval or the build's check date.
3. **Build and repeat in isolation.** Use Lumecon's declared locked environment
   and explicit immutable source, reviewed field-map, resolved register and scope
   snapshots. Legislation additionally needs its action snapshot. These are
   migration inputs, not live imports of the Cedar workspace. Keep stores outside
   Git checkouts and canonical input directories:

   ```powershell
   Set-Location '<Lumecon-data-checkout>'
   & '<Lumecon-python>' -B -m lumecon_data collection-build legislation --source '<snapshot>\native_bills.csv' --actions '<snapshot>\native_bill_actions.csv' --field-map '<snapshot>\legislation-field-map.json' --register '<snapshot>\register.json' --scopes '<snapshot>\scopes.json' --root '<isolated-store>' --as-of '2026-09-24'
   ```

   `--as-of` is an operator check date, not source cutoff. Require deterministic
   release IDs, row/key conservation, namespace/minting-authority validation, no
   filled/reassigned CE links, and recorded schema/count/snapshot/hashes. Missing
   inputs, malformed CSV, path escapes and attempted immutable
   replacement must fail. An empty plan is not success.
4. **Pin and exercise the consumer.** Existing `build_catalog(...,
   product="cedar_press")` binds the release and public API manifest through
   `manifest_sha256`, including artifact hashes. Regenerate older catalogs lacking
   that digest from verified releases. Catalog/API share `manifest_metadata`;
   private identity mappings stay internal. Configure server-only
   `CEDAR_PRESS_RELEASE_CATALOG`, `CEDAR_PRESS_DATA_API` and `CEDAR_PRESS_DATA_TOKEN`
   per [server/README.md](../../server/README.md). The local rehearsal creates
   development credentials and refuses inherited `DATABASE_URL`/`CEDAR_PRESS_DB`:

   ```powershell
   Set-Location '<Cedar-Press-checkout>'
   $env:PYTHONPATH='<Lumecon-data-checkout>\src;<Cedar-Press-checkout>\server'
   & '<consumer-test-python>' -B server/tests/release_download_rehearsal.py --store '<isolated-store>' --catalog '<printed-catalog-path>'
   ```

   Require anonymous/wrong-tier denial, exact authorized bytes, matching metadata,
   eight current-run redacted audit events and rollback. Focused/database tests
   must also prove removed/downgraded accounts and subscriber-store failures cannot
   fetch artifacts. Rollback selects a previously verified catalog without
   mutating either immutable release.
5. **Verify format, metadata and handoff.** Full downloads are exact
   `records.jsonl` (`application/x-ndjson`); samples remain CSV. `fullRelease`
   excludes ancillary tables. Customer CSV and frontend full-download controls
   require separate implementation/proof. Preserve the five metadata authorities
   below; regenerate affected outputs without API-specific copies. Run
   `python code/521_inventory.py check-scripts`, `make check-generated`, focused
   registration/publication/ID and release-contract tests, and both repositories'
   full CI, including Ubuntu symlinks and disposable Postgres. Preserve canonical
   and published hashes; exclude private candidates from Git. Record results in
   the existing Havala packet. Production changes require separate authorization.

**Minimum files:** Lumecon's reviewed collection contract/producer and tests;
Cedar's product field presentation/catalog and consumer tests only where required.
Do not add another Cedar transform or handwritten release schema. Refresh
registered transitional executable changes with
`python code/521_inventory.py scripts-only`; preserve dated table measurements.
No numbered scripts, new registries or collection-specific adapter branches.
Retire replaced producers only after consumer, test and documentation cutover.

**Historical onboarding before producer cutover:** Natural Resources added 9 configuration lines and one
19-line qualification-preservation branch: zero new configuration files/endpoints
or shared-adapter collection branches. Shared build and Lumecon validation changes
are additional, separately reviewed infrastructure work. Its producer and source
qualification rules now live in Lumecon; this historical count does not describe
the later repository migration.

## Runtime metadata contract (takeover verification, 2026-09-23)

These five small product contracts are **tracked Git inputs**. All five were already
tracked at `b6abb374a7a40216a7648ef79fc1df9e5b471f79`, although `/data/*` ignored
new copies. The narrow `.gitignore` exceptions now make that policy explicit;
unapproved sibling JSON, bulk CSV, raw data and restricted decisions stay ignored.
Do not replace these files with consumer-specific copies or regenerate missing
release history from the latest dataset. Large data belongs in the governed
versioned data store; this repository retains the metadata for the release it serves.

| File | Authority and required inputs | Consumers | Fresh-clone and release rule |
|---|---|---|---|
| `codebook.json` | Curated field definitions; no JSON generator. `scripts/docs-markdown.mjs --kind codebook` generates its Markdown view, not this source. | `src/features/grove/explore.js` supplies headings/record meanings; codebook and guide generators; `server/tests/test_field_map.py` and Explore tests compare approved fields. | Commit the reviewed source. Definitions cannot be reconstructed from column names alone. Generated documentation is reproducible and freshness-checked. |
| `collections.manifest.json` | `scripts/stage_verified_previews.py`, from verified Lumecon-data releases: it stages each collection's preview in a new directory, which is then installed here by hand (see "Refresh the served data"). | `collection.js` and `server/cedar_press/collections.py`, then catalog, filters, sources, citations, downloads and API; Explore, guides, codebook, field-map, sample, release and SEO generators. | Commit the installed snapshot. A fresh product clone can serve and test it, but cannot regenerate it without the pinned Lumecon-data releases and the staging queue. |
| `field_map.json` | Curated publication/column decisions under the owner's 2026-09-05 public dataset specification (`docs/PUBLIC_DATASET_SPEC_2026-09-05.md`, at the tag `data-workspace-final`); no JSON generator. `scripts/docs-markdown.mjs --kind field-map` generates its two review documents. | The API's spreadsheet and repository modules (`server/cedar_press/spreadsheet.py`, `repository.py`), `collections.py`, the stager, `preview_definitions.py`; guide/field-map generators, Explore and Python field-map tests. | Commit reviewed decisions. A clone can test fixtures and sample compatibility; proving mappings on full customer files needs the full-data release job. Do not infer a decision for an undeclared column. |
| `releases.json` | `scripts/record-release.mjs`, using the manifest **and retained prior ledger**. | `src/features/grove/pressReleases.js`, release feed and citations, release tests; `scripts/dump.mjs --kind press` includes that catalog in the Python API snapshot. | Commit append-only release history. `--check` verifies current manifest/ledger consistency without rewriting history. The latest manifest cannot recreate superseded releases. |
| `samples.published.json` | `scripts/measure-samples.mjs`, using the manifest plus Git index and the matching sample bytes in `data/cedar/samples/`. | `collection.js` and Python `collections.py` determine sample availability, then download/UI/API paths; sample and collection parity tests. | Commit the deterministic measured snapshot with its inputs. `--check` and `--selftest` distinguish committed, absent, untracked and unstaged samples. A file merely present on one machine is not a published sample. |

The supported freshness surface remains `make check-generated`: codebook, Explore,
field-map, guides, samples, release ledger and SEO checks. Both PR CI and deployment
call it. The product build bundles the tracked contracts; it does not fetch bulk
inputs or invent new release metadata. `pressDownload.test.js` now checks all five
are tracked and exempted by name, and proves unrelated data remains ignored.
`server/tests/test_collection.py` also requires all five in the index, retaining
its existing checks for the Explore contracts.

**Reproduced verification.** An independent local clone at the SHA above was
materialized with only the proposed tracked metadata/test/attribute patch. No
ignored full-data inputs or existing `node_modules` were copied. Windows' default
`core.autocrlf=true` initially made four generated-text checks fail: Git blobs
were LF, while checkout files became CRLF. Exact generated output paths now have
`text eol=lf` in `.gitattributes`; R7 byte-preservation attributes are unchanged.
Applying the attribute patch before first checkout reproduced all seven freshness
checks successfully. `npm ci` and `npm run build` passed; 58 focused JavaScript
Explore/download/release tests and 43 Python collection/UI-API parity tests passed.
Removing the codebook ignore exception deliberately failed the new regression
test, and restoring it returned the fixture to its original state. This used
Node 24.21.0 and Python 3.14 on Windows; deployment and browser rehearsal were not
performed by this metadata check. Vite still reports its existing large-chunk warning.

**What those passes establish.** These files agree with the committed product
snapshot, declared sample availability and tested JavaScript/Python consumer
behavior. They do **not** certify the new full-data release. All twelve current
manifest descriptors still say `v1`, updated `2026-09-04`; vintage remains
unmeasured. The codebook explicitly says its initial meanings require confirmation
against build scripts. The sample record reports 19 declared samples unavailable.
The pending NEED candidate and any new NAGPRA full export must pass their own
publication gates before these snapshots are updated together. Current deployment
bytes and entitled full-download equivalence remain unverified here.

For a new release, follow "Refresh the served data" above: review changes to the
same contracts and sample files, record the new version without replacing
history, and commit the resulting metadata snapshot as one change. A passing
static build is not a completed data release.

## Historical sample integration background

The measured findings and review history of the 2026-09-02 sample extracts
(the top-level `samples/*__sample.csv` files and `collection_descriptors.cedar.json`,
removed 2026-10-12) are kept in git history at the tag `data-workspace-final`.
