# Shipping runbook

<!-- BEGIN CODEX-ISOLATED-CANDIDATE-RUNBOOK -->
## Current early-access candidate procedure (2026-09-23)

This section supersedes the August gaming chain below for the Codex takeover.
That chain is retained as historical recovery documentation, not a current launch
command. The fixed infrastructure review range, current proofs and blockers are in
`docs/HAVALA_INFRASTRUCTURE_REVIEW.md`; the existing terminal handoff retains the
workspace takeover context.

### Systemic hold supersedes the prior candidate command

The owner review exposed defective automated affiliation routes. New 1072 builds
refuse staged OWNERV6 before output writes, including explicit legacy staging.
The command below is retained as the reproducible historical migration path; it
now stops deliberately until a corrected evidence-qualified staging release exists.
Do not add a bypass or reinterpret this as a dependency failure. Completed pinned
candidates remain recoverable ID-migration evidence, not release candidates.
The independent publication hold remains even after the field's INTERNAL_ONLY
ruling is implemented. No replacement affiliation is promoted automatically.

### Isolated NEED build

Run from Desktop/cedar-press-codex, using a NEW output root each time:

```
py -3 -B code/build.py candidate need --input-root C:/Users/esm247/Desktop/cedar-press-codex --owner-dir C:/Users/esm247/Desktop/cedar-press-codex/data/raw/external/need_owner --output-root C:/Users/esm247/cedar-takeover-checkpoint/need-candidate-NEW --as-of 2026-09-23
```

The supported runner declares NEED_INPUTS/NEED_OUTPUTS in code/build.py, copies
pinned inputs and code into the empty output root, and executes nine real command
stages there. Owner snapshots are copied from the explicit owner-dir. The runner
refuses an existing or overlapping target and insufficient disk headroom. It pins
CEDAR_RUN_DATE and constrains DuckDB memory to 512 MB, one thread and 2 GB spill.

Write boundary: the new candidate root (code, copied inputs, staging, clean outputs,
spine candidate register, diagnostics, review, docs and logs). It does not promote
to the original Windows workspace or customer exports. Preserve the ENTIRE root
and logs/need-candidate.json, not merely four output tables. Inputs and allocator
hashes must remain unchanged; register rows/bindings and all issued IDs survive.
No missing dependency or empty plan may count as successful execution.

Recovery: prior candidates and the original workspace remain untouched. A failed
candidate is retained with its step logs; choose a new output root after repairing
the defect. Do not delete diagnostic history or overwrite an active review's
candidate. Production promotion requires a separately reviewed complete write set,
backup and restoration proof; this procedure authorizes none.

### Active owner review and receipt import

The existing builder has a bounded NEED mode:

```
py -3 -B code/08_build_review_page.py --need-review review/need_existing_cedar_uid_evidence.json
```

It verifies input hashes, writes review/cedar_review.html and preserves a previous
page by content hash. DO NOT run it while Elijah is reviewing the current queue.
The local service at 127.0.0.1:8765 serves that page only on this machine. Browser
storage is origin-specific: moving from file to HTTP requires exporting/importing
decisions. Always retain the downloaded decision CSV as a durable copy.

```
py -3 -B code/09_import_rulings.py --need-review <returned.csv> --queue review/need_existing_cedar_uid_evidence.json --receipt-ledger <isolated-receipt.json> --dry-run
```

After preview validates, omit --dry-run to record the decisions idempotently in
that explicit receipt ledger. The existing eight review CSV columns are retained;
seven appended columns pin decision ID, reviewer/time, evidence fingerprint,
queue version, affiliation target and superseded decision. Unknown targets,
conflicting decisions, stale evidence, malformed timestamps and missing reasoning
are refused. HOLD remains held. This mode NEVER writes canonical identity,
publication policy or exports; receipt status is pending application. The legacy
identifier-propagation path refuses NEED review queues rather than interpreting
publication choices or affiliation decisions as identifier assignments.

Actual application must implement the owner's authorized disposition in the
existing field contract, preserve identity/evidence history, validate downstream
outputs and generate an applied/held/stale/conflict receipt. Recording a receipt
is not that application, and does not open the NEED gate automatically.

### Export planning and product metadata

```
py -3 -B code/1137_customer_dataset_combine.py plan nagpra
```

Planning executes the same joins and publication checks as building, without
writing an export. Missing field decisions are failures in both paths. Blank
join keys never match. Do not strip a blocked field to make the plan pass.
NAGPRA currently refuses seven joined diagnostic/count columns pending explicit
contract destinations; NEED refuses under its independent systemic affiliation hold; its own-entity
field is now internal-only by explicit owner ruling.

Small runtime metadata stays tracked under narrow .gitignore exceptions. Authority,
generators and clean-checkout proof are recorded in data/cedar/README.md. Run the
seven Makefile check-generated commands before app checks/build; a data-less clone
validates committed release metadata, not missing raw data or the entire pipeline.
Do not run import_cedar_manifest.py --audit assuming it is read-only: it mutates
manifest/publication outputs. Release ledger history must be preserved.

### Release infrastructure: local proof and production boundary (2026-09-24)

The implementation and measured release/CI results are recorded in
`docs/HAVALA_INFRASTRUCTURE_REVIEW.md`. This section defines operating boundaries;
it does not certify a deployed service. Lumecon Data owns governed snapshots,
release contracts, validation and immutable storage. Existing acquisition and
collection transforms remain transitional Cedar stages until a tested ownership
transfer retires them; the publication projection currently remains in Cedar.
Cedar Press owns its
catalog adapter, sessions, entitlement checks, download responses and audit events.
The existing Lumecon CLI is the operator interface; no additional runner or
manifest format is required.

| Environment | Store and credentials | Permitted operation |
| --- | --- | --- |
| Development | Explicit isolated local root; loopback API; disposable development accounts and dataset-scoped service grant | Candidate builds, verification, denial/success tests and rollback rehearsal |
| Staging | Separate approved private store, database and service identity; production-like TLS and entitlement configuration | Restore and deployment rehearsal after its owner authorizes provisioning; never share production grants or current pointers |
| Production | Approved private versioned object store, persistent Postgres accounts/codes, restricted service identity and HTTPS | Explicit approved release/catalog selection; no direct browser access to raw evidence or service grants |

`CEDAR_PRESS_ENVIRONMENT` is validated as development, staging or production.
Nondevelopment release access refuses HTTP/loopback, insecure cookies, missing or
short explicit session/service secrets, non-Postgres DATABASE_URL and environment
account fallback. These guards do not certify database availability or implement
session expiry/revocation; those remain production gates.
`DATABASE_URL` selects the existing Postgres-backed stores. When absent, the
application retains development environment accounts/in-memory activation and
SQLite behavior. Do not certify restart persistence from development tests.
`CEDAR_PRESS_DATA_API`, `CEDAR_PRESS_DATA_TOKEN` and
`CEDAR_PRESS_RELEASE_CATALOG` configure the release consumer; the service token
stays on the backend. `CEDAR_PRESS_INSECURE_COOKIE=1` is local-only. Production
must set the persistent session secret, allowed origins and database explicitly.
No secret value belongs in Git, a catalog, an audit event or a command transcript.

**Registered collection rehearsal.** Follow the short
[Add a collection procedure](../data/cedar/README.md#add-a-collection-to-the-governed-release-path).
`code/build.py release-pilot` is the supported Cedar entry point for the reviewed
Legislation and Natural Resources flagships; it calls the existing Lumecon
contract/build/catalog functions. Use the exact pinned source, authority inputs,
environment and isolated store from the Havala packet. No new endpoint or
collection-specific release format is required.

Full downloads require an approved catalog with `manifest_sha256`; regenerate
older catalogs from verified releases rather than weakening the consumer. The
digest binds the safe API manifest and its artifact hashes. Full downloads are
exact JSONL, while existing product samples remain CSV. A full customer CSV or
frontend control needs a separate verified implementation.

The full-download route checks both the signed cookie's tier and the current
subscriber store before fetching an artifact. Removed accounts return 401;
downgraded accounts return 403; lookup failures return a redacted 503 and never
fall back to stale cookie authorization. Upgraded subscribers sign in again.
Session expiry/revocation and other routes' existing behavior remain separate
production work. The current two-collection proof covers real login, 401/403/200,
exact bytes, redacted current-run audit events and selection of a prior valid
catalog without modifying either release. `authorized_prepared` records response
preparation, not proof that the network delivered the entire response.

**Object layout.** Preserve the existing Lumecon layout within each independent
store: `raw/<source_id>/<snapshot_id>/source.csv`, `receipts/<source_id>/`,
`staging/`, `releases/<dataset_id>/<release_id>/` and `current/<dataset_id>.json`.
The pilot also keeps content-addressed catalog JSON under `catalogs/`. Release
files are `manifest.json`, `contract.json`, `records.jsonl`, `records.parquet` and
`validation.json`; hashes and schema checks belong to the existing verifier.
An approved future S3 backing store should preserve those relative keys under
separate environment roots, with private access, versioning and conditional
immutable creation. **The current filesystem implementation is not an S3
backend.** Provisioning, adapter implementation and restore proof remain required;
copying files to a bucket does not implement the storage contract. Keep restricted
raw evidence separate from publicly distributable artifacts and website assets.

The repository deployment workflow identifies a static-site S3 bucket and
CloudFront distribution for `cedarpress.ai`. It synchronizes built site assets
with deletion enabled; it is not an appropriate destination or retention job for
immutable dataset releases. The AWS certificate is an owner-reported existing
asset. This read-only session found no AWS CLI, no local `.aws` directory and no
AWS environment-variable names; it did not authenticate or inspect live AWS.
Certificate validity, DNS routing, bucket versioning, delivery permissions,
API hosting and monitoring therefore remain **NOT VERIFIED**, not absent.

**Catalog database boundary (specification only).** The current immutable
catalog JSON remains the source contract; do not introduce a second authoritative
manifest. If the operational database needs indexing, project its existing fields
into release rows keyed by `(dataset_id, release_id)` with `catalog_id`, schema
version, manifest/artifact hashes, row count and storage key/version references.
Maintain environment/product catalog selection and append-only promotion/audit
receipts separately. Foreign keys point to verified releases; transactions change
selection atomically. Product entitlements continue to reference existing
account/organization policy, never a manifest's service grant. Bulk records,
raw evidence, secret grants and regenerated competing identity registers do not
belong in this catalog projection. No such database migration was executed.

**Existing local verification, promotion and rollback commands.** From Lumecon
Data with its declared environment activated (substitute explicit approved IDs):

```sh
python -m lumecon_data.cli verify --root STORE --dataset DATASET --release CANDIDATE
python -m lumecon_data.cli compare --root STORE --dataset DATASET --before PRIOR --after CANDIDATE
python -m lumecon_data.cli catalog --root STORE --product cedar_press --dataset-release DATASET:CANDIDATE
python -m lumecon_data.cli promote --root DEV_STORE --dataset DATASET --release CANDIDATE
python -m lumecon_data.cli promote --root DEV_STORE --dataset DATASET --release PRIOR
python -m lumecon_data.cli verify --root DEV_STORE --dataset DATASET --release PRIOR
```

`catalog` prints the existing contract; the supported pilot stores canonical bytes
immutably. `promote` verifies first and atomically changes only the local current
pointer. Cedar's pinned consumer does not follow that pointer automatically:
rollback must select the previously verified immutable catalog through its
configured catalog path, then repeat entitlement, artifact-hash and audit checks.
Compare release-file hashes before and after; none may change. The promotion
commands above are development examples, not production authorization. There is
no existing backup/restore CLI: do not invent one in operator instructions.

**Backup and retention.** Preserve immutable source bytes, approved contracts,
reviewed decisions/issued-ID lineage, released artifacts and their manifests;
retain every release still cited or needed for rollback. Failed candidates and
logs remain until unique evidence and decisions have been checked. Disposable
recomputable caches are not backups. Git retains code, small reviewed contracts,
metadata and manifests; the central producer/store retains bulk canonical data;
Postgres retains operational accounts, codes, entitlements and audit metadata.

Read-only volume measurement on 2026-09-24 found C: NTFS Fixed, 506,332,180,480
bytes total and approximately 15.07 GB free; D: NTFS Fixed, 1,000,186,310,656 bytes
total and 904,739,921,920 bytes free. D: contains `Archive/tero`. Windows reports
it as Fixed, so removability and sequential throughput have not been established
by that label. No data was moved or copied in this inventory. Keep writing builds
sequential and reserve room for both candidate and restoration copies.

The external drive may hold a separately authorized offline backup of immutable
source/release material, never the only copy or the live production store. Every
archive needs a relative-path inventory, byte size, SHA-256, source/release IDs,
creation time, rights classification and producing commit. Verify hashes after
copying and again before recovery. Retain another independent verified copy.
Restore into a new isolated local store, verify each released dataset with the
existing CLI, and exercise the customer download/rollback rehearsal before any
pointer selection. Database recovery additionally requires an authorized
consistent Postgres backup and a tested restore into a separate database;
credentials, retention, recovery objectives and restoration commands must be
established by its operator before production readiness is claimed.

**Production-only completion steps requiring authorization:** provision or select
private versioned artifact storage; implement/test its existing-contract adapter;
verify certificate/domain and API deployment; configure scoped service identities,
secrets, persistent Postgres and customer entitlements; establish audit retention,
request-failure alerts, verification-failure alerts and backup monitoring; restore
from independent backups in staging; approve a specific catalog/release and test
actual production denial/download/rollback. No AWS resource, deployment, public
release or production pointer was changed by this procedure. NEED remains held.

<!-- END CODEX-ISOLATED-CANDIDATE-RUNBOOK -->


*Written 2026-08-26 alongside `docs/GAMING_SOURCE_AUDIT_2026-08-26.md`, which
found the gaming collection shipping **912 of 104,412 rows — 0.87%** — because
this chain had not been run since 2026-08-06 and silently dropped everything it
could not match.*

**The chain is STAGED, NOT RUN.** Two agents were live when this was written:
one rebuilding the gaming collection against NIGC and state regulators
(`gaming_facilities.csv` moved 774 → 784 and `gaming_facility_metrics.csv`
65,223 → 68,211 during the audit itself), one rebuilding `coverage_audit.csv`
via script 102. **Rebuilding `dist/` from data that is concurrently changing is
how this project lost work before.** Do not start until both are done.

---

## 0. BEFORE YOU START — three checks, all cheap

```
# a. is anyone still writing?
ls -l --time-style=full-iso data/clean/*.csv | sort -k6 | tail -20
ls logs/_HOSTLOCK_*.json 2>/dev/null

# b. is the codebook still whole? (read-only, must print SAFE)
py -3 code/cedar_codebook.py check

# c. back up what the chain overwrites
mkdir -p graveyard/$(date +%F)_pre_ship
cp data/clean/codebook_master.csv graveyard/$(date +%F)_pre_ship/
cp -r data/clean/codebook          graveyard/$(date +%F)_pre_ship/fragments
cp -r dist                         graveyard/$(date +%F)_pre_ship/dist
```

**If any `data/clean/*.csv` has changed in the last 30 minutes, stop.** The
gaming agent writes there.

---

## 1. THE ORDER, AND WHY IT IS THIS ORDER

Run these one at a time. Read the output of each before starting the next —
every one of them now names what it drops, which is the entire point of the
2026-08-26 changes.

| # | command | what it does | what to read in the output |
|---|---|---|---|
| 1 | `py -3 code/cedar_codebook.py build` | fragments → `codebook_master.csv` | must say `ADDS`, never `REFUSING` |
| 2 | `py -3 code/62_no_regression_check.py` | the gate. Nothing ships past a regression | any `FAIL` stops the chain |
| 3 | `py -3 code/87_build_dataset_notes.py` | notes contract per dataset | **`SHIP RATE:`** and the `NOT SHIPPED` list |
| 4 | `py -3 code/102_build_coverage_profile.py` | source coverage profile | — |
| 5 | `py -3 code/110_build_harmonized_views.py` | harmonised views | — |
| 6 | `py -3 code/25_build_publication_layer.py` | `cedar_press.db`, `.xlsx`, sanity | **`SHIP RATE:`**, `[licensed]` drops, `FAIL` sanity checks |
| 7 | `py -3 code/27_build_dataset_manifests.py` | app manifests | **`NO MANIFEST`** list, `manifest coverage:` |

**Why 1 first.** `87` reads `codebook_master.csv`. If the master is stale, every
dataset registered since is silently skipped — that is the original defect.

**Why 2 before 3.** A notes contract asserts row counts. Asserting counts that
have regressed publishes the regression.

**Why 6 after 3.** `25`'s table list is now derived from the same codebook
registry `87` uses (`cedar_codebook.registered_tables()`). Running it against a
stale master reproduces the bug in the database instead of the notes.

**NEVER run `41_build_codebooks.py`.** It writes `codebook_master.csv` in `"w"`
mode from a hardcoded 19-group `DATASETS` dict. Running it today deletes **21 of
the 43** dataset blocks, including every block registered on 2026-08-26. If you
need to regenerate a block, use `cedar_register_codebook.py` or write the
fragment directly — never 41. This is the single most destructive command in the
repo and its name does not say so.

---

## 2. WHAT "GOOD" LOOKS LIKE

After step 3 (`87`):

- **`SHIP RATE:` well above 0.87%.** The audit measured the gaming collection at
  0.87%; the registrations on 2026-08-26 unblocked 18,973 gaming rows and the
  registry now resolves 107 shippable tables against 26 previously hardcoded.
- **`LICENCE GATE - 2 file(s) REFUSED, by name`** — `gaming_facility_metrics.csv`
  and `gaming_property_capacity_history.csv`. If this line is absent the gate
  has been broken again; it was dead for twenty days once already.
- **`NOT SHIPPED`** lists every clean table with no codebook block, by name and
  score. This list is the backlog, not an error. It should shrink between runs.
- **`[undefined]`** names tables shipping variables with no description.
  `nigc_declination_letters.csv` will appear: **45 of its 60 public variables
  have no written definition**, because `docs/codebooks/07d_nigc_declination_variables.md`
  documents only the 13 columns script 100 added, not the 47 script 91 built.
  **Registering a block made it shippable; it did not make it documented.**
  Either write those definitions or tier the columns internal before this one
  goes to a subscriber.

After step 6 (`25`):

- **`[licensed] ...: dropping recipient_duns`** on `funding_transactions`. The
  previous database shipped **404,236 populated DUNS** against terms of use that
  say DUNS is never published. If that line does not appear, the strip is broken.
- **`[licensed] gaming_facilities: dropping casino_city_id`** — 595 populated.
- Sanity checks: **zero FAIL**.

After step 7 (`27`):

- **`manifest coverage:`** — expect it to be low and honest. A manifest states
  what a dataset *measures*, which is an authored claim and is never generated.
  The `NO MANIFEST` list is the writing backlog.

---

## 3. IF SOMETHING GOES WRONG

| symptom | cause | fix |
|---|---|---|
| `cedar_codebook.py build` prints `REFUSING` | a fragment failed to write, or a block exists only in the master | `py -3 code/cedar_register_codebook.py reconcile` — it writes the missing fragments one at a time. **Do not use `--force`** until `check` prints `SAFE`. |
| `build` raises on unexpected keys | a fragment with a non-standard schema | `reconcile` normalises it. `02b_subawards_api.csv` was the known one (9 cols vs 10). |
| a dataset you expected is in `NOT SHIPPED` | no codebook block, or a stub block | check the score. Under ~0.25 usually means a **stub** — `07j`/`07k`/`07l` documented 6, 2 and 5 columns of 26, 23 and 31. A stub can never reach 0.60. |
| `87` writes a contract for a licensed file | the gate is dead again | `LICENSED_SOURCE_FILES` must be *referenced* in `main()`, not merely declared. It was declared and unreferenced from 2026-08-06 to 2026-08-26. |
| the DB is missing gaming tables | master is stale | run step 1 first. |

**Rollback.** Everything the chain writes is in `dist/`. Restore from the
`graveyard/<date>_pre_ship/dist` copy made in step 0.

---

## 4. THE BACKLOG THIS CHAIN WILL NAME

Known and expected in the `NOT SHIPPED` list on the next run — these need a
codebook block written, and are ranked in
`docs/GAMING_SOURCE_AUDIT_2026-08-26.md` Part 5:

| table | rows | note |
|---|---:|---|
| `gaming_game_finder_observations.csv` | 6,851 | stub fragment, 5 of 31 columns |
| `gaming_property_locations.csv` | 2,212 | **also needs a row filter — 741 rows are `publishable = N`** |
| `fac_audit_gaming_disclosures.csv` | 1,521 | |
| `gaming_properties.csv` | 784 | the de-vendored replacement for `gaming_facilities` |
| `gaming_property_federal_traces.csv` | 774 | |
| `gaming_property_coverage.csv` | 774 | |
| `gaming_vendor_tribal_licenses.csv` | 740 | |
| `gaming_nigc_roster_link.csv` | 442 | built by the concurrent agent 2026-08-26 |
| `gaming_financing_events.csv` | 293 | |
| `gaming_property_site_observations.csv` | 262 | stub fragment, 6 of 26 columns |
| `gaming_source_claims.csv` | 113 | |
| others | ~400 | |

---

## 5. THE STANDING RULE THIS REPLACES

There was no rule. `AGENTS.md` mentioned script 87 once, in passing, in a
sentence about where presentation lives. The shipping step was written down
exactly once — `docs/handoffs/STATE_OF_THE_LAND_2026-08-07.md` §7, item **6 of 6** — and
carried forward unread through twenty days and roughly twenty builds.

**A build is not finished when the table is written. It is finished when the
table can leave the building, or when a named line says why it cannot.**


---

## 6. UPDATE 2026-08-26 ~21:00 — the backlog in Part 4 is registered; the chain is still staged

**74 codebook blocks were written** (`code/391_triage_unshipped_tables.py`,
`code/392_write_unshipped_codebook_fragments.py`), covering **488,109 rows**
including every gaming table listed in Part 4 above. `codebook_master.csv` was
rebuilt from fragments — **step 1 only** — taking the registry from 128
shippable tables to **199**, and the undocumented list from 140 to **13**.

**Steps 2-7 have NOT been run.** No quiet window opened: `327_migrate_class7_
keys_to_digests.py` was rewriting keys in place, `384_crawl_uncrawled_open_
properties.py` was crawling, `121` was pulling subawards, and `data/clean` was
last written at 20:24, inside the 30-minute stop rule in Part 0 above.

Three things that change what Part 2 tells you to expect:

- **`NOT SHIPPED` should now list 13 tables, not 139.** 56 of the old 139 are
  declared in `cedar_codebook.INTERNAL_TABLES` and appear under a new
  **`INTERNAL BY DECISION`** heading instead. They are a decision, not a gap.
- **`SHIP RATE` was printing 100.0% and was wrong.** `87` unpacked five values
  from `scan()`, which returns eight; the ValueError was swallowed and
  `lost_rows` never left zero. Fixed. The next figure will be far lower and
  will be the first honest one.
- **Four notes contracts must be deleted after the run**, by exact filename —
  four tables move out of a block that never described them. The list is in
  `docs/STAGED_SHIP_CHAIN_2026-08-26.md` Part 3.

**Everything left to run, and what each line must print, is in
`docs/STAGED_SHIP_CHAIN_2026-08-26.md`.** Read Part 4 of it before treating
`62`'s red as yours.
