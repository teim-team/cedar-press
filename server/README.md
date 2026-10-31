# The Cedar Press API

A FastAPI service serving the routes the React client calls. Python because
the part of this service with real logic in it — inclusion rules, entity
resolution, release bookkeeping, CSV shaping — was already written in Python
for Cedar Grove, and was carried over here rather than reimplemented.

That is provenance, not a dependency. Cedar Press is a standalone product: this
package imports nothing from Cedar Grove and calls no Grove service. It reads
`data/cedar/collections.manifest.json`, the same file the JavaScript client
reads. `scripts/stage_verified_previews.py` stages its updates from verified
Lumecon-data releases; the refresh order is in `data/cedar/README.md`.

```
cedar_press/
  routes and data
    app.py                  the routes: HTTP concerns only
    repository.py           where data comes from, the seam Postgres replaces;
                            verifies a pinned release before any byte is served
    spreadsheet.py          one customer CSV per collection, from the verified download path
    customer_sheet.py       the customer table rules, vendored from Lumecon-data
    governed_collections.py the added release targets (Giving, PLOT) and their column order
    release_research.py     bounded research previews from hash-pinned producer packets
    csv_safety.py           writes a cell a spreadsheet would run as a formula as text

  what readers see
    collections.py          the 14 storefront collections, ported from Cedar Grove's package
    collection_profiles.py  the machine-readable data dictionary Cedar answers from
    source_presentation.py  readable citations, naming original publishers, never file names
    press_catalog.py        the tiers and the catalog
    claims.py               the claim classes a finding carries
    plot_map.py             checks pinned PLOT map evidence and shapes its outlines
    shelf.py, templates/    the HTML shelf page, GET /press/shelf

  NEED
    need_preview.py         admits the small committed NEED preview on exact proof
    need_publication.py     NEED admission after the normal release verifier
    need_profiles.py        NEED evidence on registered Native entity profiles

  subscribers
    accounts/services/
      sessions.py           who is signed in: a signed, HTTP-only cookie
      subscribers.py        subscriber persistence, credentials and legacy access
    ratelimit.py            rate limits on sign-in and password reset
    priorities.py           Shape the Research: Cedar Points, priorities and requests
    db.py, migrate.py,      the Postgres connection, used when DATABASE_URL is set,
      migrations/           and its migrations

  other services
    cedar_service.py        the client for Cedar, the AI economic analyst (the cedar repository)
    grove_exchange.py       a local process interface for Cedar Grove's application
```

`tests/test_collection.py` and `tests/test_access.py` each run both the Python
and the JavaScript implementation and compare them — the collection values in
the first, the access rules in the second — so the two cannot drift.

`GET /press/shelf` is the one route that returns HTML: the shelf page, composed
by `shelf.py` from the same modules the JSON routes read and styled by the
client's own stylesheets. It is a demonstration that this service can render
the site, from the Python-first proposal of 2026-09-02 (`docs/PYTHON_FIRST_SITE.md`,
at the tag `data-workspace-final`); whether readers are meant to see it is an open
question for the owner.

## Running it

```sh
pip install -e .[dev]
CEDAR_PRESS_SECRET=dev-secret \
CEDAR_PRESS_INSECURE_COOKIE=1 \
CEDAR_PRESS_ACCOUNTS='{"reader@example.org":{"password":"...","tier":"press"}}' \
uvicorn cedar_press.app:app --reload --port 8000
```

| Variable | Purpose |
| --- | --- |
| `CEDAR_PRESS_SECRET` | Stable server-only session signing secret; staging/production require at least 32 characters. Only development may generate a temporary key. |
| `CEDAR_PRESS_ACCOUNTS` | Provisioned subscribers as JSON. Empty by default, so a service started without accounts authenticates nobody. |
| `CEDAR_PRESS_ORIGINS` | Comma-separated origins allowed to send credentialed requests. |
| `CEDAR_PRESS_APP_URL` | The client's origin, where password reset links open (`<url>/login#reset=...`); default `http://localhost:5173`. Reset by email is development-only until a mail provider is configured: development logs the link, and staging and production answer 503. |
| `CEDAR_PRESS_INSECURE_COOKIE` | `1` in local development only: drops `Secure` so the cookie works over http. |
| `CEDAR_PRESS_TRUST_PROXY` | `1` when the API sits behind a proxy that appends to `X-Forwarded-For` (the intended deployment once the API is activated: CloudFront in front of the API origin, `docs/HOSTNAMES.md`); `0` when clients connect directly. Sign-in and password reset are rate limited per client address, so this decides what "client" means. Unset reads as `0` in development and is refused (503) in staging and production, because behind CloudFront `0` would key every subscriber to CloudFront's address and one stranger's wrong passwords would lock everyone out. |
| `CEDAR_PRESS_PROXY_HOPS` | With `CEDAR_PRESS_TRUST_PROXY=1`, how many trusted proxies append to `X-Forwarded-For`; default `1` (CloudFront). Set `2` if a load balancer sits between CloudFront and the service. The client is the entry that many places from the right; everything left of it is caller-written and ignored. Only correct when the service cannot be reached except through that chain. |

## Where the database goes

Every route reads through `repository.py`, which answers from the ported
modules today. When the collections move into Postgres it answers from there
and `app.py` does not change — routes hold HTTP concerns and no data access
of their own, which is what keeps that swap to one module.

`accounts/services/subscribers.py` already persists subscribers when `DATABASE_URL`
is configured. The environment-backed account fallback is for
development; staging and production refuse it. Install the PostgreSQL extra
with `uv sync --locked --no-dev --extra postgres --project server` from the
repository root and run the existing migration command in `DATABASE.md`.

Sessions expire after 14 days. Every authenticated request re-reads the subscriber
and current Press tier; removed subscribers and changed credentials or account
bindings invalidate existing cookies. Logout advances `sessions_revoked_at`,
ending that user's sessions on all devices. A stable server-only signing secret is required in staging
and production. Existing passwords, accounts and subscription tiers are preserved;
old cookies without lifecycle claims require a fresh sign-in.

The account foundation extends the existing subscriber account with verification
and Stripe customer fields. Google identities and access grants reference its UUID.
Annual Stripe Checkout, billing portal and signed webhook reconciliation are implemented.
Checkout starts at `/subscribe`; paid customers create an account through
a single-use email link. Stripe collects the email and discount code. Existing emails keep their
credentials and sign in normally.
The `cedar_press.billing` package uses `BillingService`, `CheckoutService` and `BillingReconciler`,
with `StripeAdapter` in `billing/adapters/stripe.py` for Stripe calls.
Both packages keep HTTP routes, schemas and dependencies under `api/`, application
services under `services/`, and domain records in `models.py`. Accounts owns
authentication, sessions, setup links and email transport. Billing owns purchase delivery tracking in `billing/services/purchase_email.py`.
Dependencies share one `StripeAdapter`; its client initializes on first use.
Tests can inject `StripeAdapter(client=...)`.
`AccountSetupService` handles activation; `PurchaseEmailService` handles purchase
email delivery and retries.
Google sign-in remains separate work. See
[DATABASE.md](DATABASE.md) for the [schema ERD](DATABASE.md#schema-erd) and local Docker setup.

The static browser preview gate is a separate login authority. Enabling
`VITE_API_URL` does not migrate its accounts. Before switching an existing site,
verify every existing subscriber's credential compatibility and entitlement in
the persistent API. Do not
reset credentials or treat a public preview digest as a PostgreSQL password hash.

## Checks

```sh
ruff check . && ruff format --check .
python -m unittest discover -s tests -t .
```

### No third-party enrichment of subscribers

Subscriber addresses are not sent to an enrichment vendor (Clearbit, Apollo,
ZoomInfo and the like) to buy back employer and job title, and that is not to be
added without a deliberate decision. The list itself is sensitive: it names the
tribal governments and lenders reading Cedar Press. Profiling Native readers
through a broker contradicts the product's case for careful, sovereign handling of
Indian Country's data; the inferred titles are worst at tribal governments and
enterprises; and purchased personal data carries CCPA/CPRA and GDPR duties. If
enrichment is still wanted, it runs server-side against organizations (the domain,
not the person), is disclosed in the privacy policy, and is a platform decision
made with counsel. The client's `subscriberProfile.js` classifies a reader's
domain in the browser and goes no further.

## Shape the Research

`CEDAR_PRESS_DB` names the SQLite file that holds the Cedar Points ledger, the
priorities' counts and subscribers' requests (for example `server/var/cedar_press.sqlite`,
which is ignored). Unset, the store lives in memory and a restart forgets it:
right for the tests, wrong for a deployment. An account record in
`CEDAR_PRESS_ACCOUNTS` may carry `"account": "acct-name"` so several seats share
one subscription's ledger.


## The customer table (owner rulings 2026-10-04)

Every spreadsheet and sample download is one flat table per collection, built
by `cedar_press/customer_sheet.py` (vendored byte for byte from Lumecon-data
`src/lumecon_data/customer_sheet.py`; `tests/test_customer_sheet_policy.py`
compares the copies where the producer is installed). Owner rulings,
2026-10-04: the only Cedar identifiers published are the Cedar Entity ID
(`CE-00001-6S`) and the Cedar Business ID (`CB-0000001`); an event-grain row
carries its own dataset's event ID (`EVENT_ID_COLUMNS`) and never another
dataset's (`DATASET_EVENT_ID_COLUMNS`, `DATASET_EVENT_ID_FORMS`); the public
registry identifiers in `PUBLIC_REGISTRY_ID_COLUMNS` and every other identifier
the source dataset carries ship as the source carries them; DUNS never ships;
Casino City columns, `CCP-`/`TPL-` keys and values are removed; outdated Cedar
schemes (`RETIRED_ID`: the CICD/NEID handles such as `TRBF-CHKNAT-00`, every
`CEDAR-` namespace including `CEDAR-NEST-` and the Gaming facility keys
`CEDAR-PLACE-`, `NESTREL-`, the `VP-`/`CED-` facility keys, `PROV-` keys,
NEID/CICD codes) are removed from every column, and the `tribe_id` and
`legacy_facility_id` columns that hold them are not shown. A Cedar ID column
holds only `CE-`/`CB-`: another value takes the ID the exact register
`data/spine/cedar_retired_neid_crosswalk.csv` binds it to
(`spreadsheet.cedar_id_crosswalk`), otherwise it is blank. NEED and Gaming show
`business_uid` with `needs_cedar_id`; no Cedar Business ID is issued yet, so
those rows read `yes`. No replacement place ID exists or is built;
internal content checksums, dedup and batch labels stay internal; a local source value (path, spreadsheet, terminal, desktop, manual entry)
is traced to the release's recorded public source URL or left blank; version
columns and labels stay internal. `spreadsheet.download` presents the pinned
release this way after every byte check; `repository.collection_csv` presents
the committed ten-row samples this way; `release_research` presents verified
examples this way. Release bytes, hashes and the per-component JSONL routes are
unchanged.

Native identity basis (owner request, 2026-10-04). The customer tables of
`owned`, `contractors`, `subcontracting`, `funding`, `deals`, `need` and
`gaming` carry `native_identity_basis`, the strongest evidence behind the
Native identity the record asserts (`tribal_government`, `ancsa_corporation`,
`native_hawaiian_organization`, `enrolled_tribal_citizen`, `program_certified`,
`publicly_stated`, `self_certified`, `unknown`), and `native_identity_source`,
its public citation. Both are derived by the vendored module from evidence on
the row, never guessed; the mapping and the measured sample distribution are in
Lumecon-data `docs/native-identity-basis.md`. A ten-row sample is built without
related tables, so NEED's sample rows (whose owner class is attached from
`enterprises`) read `unknown`; the full table carries the owner class.

## Pinned governed release downloads

The existing sample download remains a sample. The additive
`GET /press/collections/{collection_id}/full-download?release_id=<sha256>`
serves the exact immutable `records.jsonl` artifact from an approved Lumecon
release. The adapter is shared across collections; the local Legislation
flagship is the first real-data proof. A passing table is not a complete product.
`GET /press/collections` exposes separate `fullRelease` metadata with the table,
format, rows, release, checksum and explicit pinned download URL.

Server-only configuration (never Vite/browser variables):

- `CEDAR_PRESS_ENVIRONMENT`: `development` (default), `staging`, or `production`.
- `CEDAR_PRESS_RELEASE_CATALOG`: a reviewed local catalog from Lumecon `build_catalog`.
- `CEDAR_PRESS_DATA_API`: the Lumecon API origin. HTTPS is required; HTTP loopback
  is allowed only in development. Staging/production reject loopback and insecure cookies.
- `CEDAR_PRESS_DATA_TOKEN`: a dataset-scoped backend grant; never a subscriber credential.
- `CEDAR_PRESS_DATA_TIMEOUT_SECONDS`: bounded data-service socket wait, 1–300 seconds
  (default 30). Cold validation of large multipart releases may require a measured
  higher value in development. Invalid/nonfinite values fail before a request.
  This does not change byte limits, verification, entitlement or production gates.
- Staging/production also require explicit secrets of at least 32 characters, a
  Postgres `DATABASE_URL`, and no development `CEDAR_PRESS_ACCOUNTS` fallback.
  Configuration validation is not proof of database availability or deployment readiness.

Cedar enforces subscriber access before fetching data, checks catalog integrity,
explicit release equality, schema, exact artifact bytes/hash, row count and
primary keys. Rights are recorded as provenance (owner ruling 2026-10-04): a
tenant-private release, which is a customer's own data, is refused, and no other
rights status or publication hold stops a download. No matching or cleaning happens in the
consumer. Missing, stale or malformed pins and service failures do not fall back
to a sample. Unconfigured collections fail closed. Single artifacts and individual manifest parts are bounded
at 256 MiB. Larger logical tables require the explicit
`CEDAR_PRESS_PARTITIONED_REHEARSAL=1` contract, which works in development and
staging; production refuses that path.
The paired Lumecon collection `/download` endpoint verifies every component once
and returns the exact manifest-ordered JSONL concatenation. Cedar verifies each
part boundary, digest, schema and row count plus global primary-key uniqueness
before releasing bytes. Temporary disk storage bounds memory to one part and a
64 MiB key-index cache. An older producer without this endpoint fails closed.

`cedar_press.download` emits redacted structured INFO events to stderr for denial,
invalid requests, verification failure and authorized/prepared responses. An event
records no account, token or row data. Prepared bytes are not proof of completed
network delivery. Production still needs durable log collection and tested session
expiry/revocation; the local fixture is not production approval.

Rollback selects a previous verified catalog pin, without mutating either release.
The old client pin is refused after a catalog switch. Run
`server/tests/release_download_rehearsal.py --store <root> --catalog <catalog>`
with both existing packages for real local login, 401/403/200, exact download,
stale-pin and byte-preserving rollback checks. See
`docs/HAVALA_INFRASTRUCTURE_REVIEW.md`, at the tag `data-workspace-final`, for exact revisions
and results.

## Giving and PLOT component releases

`GET /press/release-collections` is the authenticated integration registry for
the 16 release targets: the 14 storefront collections (the original 12,
Foundation and Corporate Giving, and PLOT) and the two Grove-only datasets,
Gaming and Native Infrastructure. Its tier-filtered entries have verified release
metadata or an explicit missing/unavailable value. It supplies no invented
samples or row counts. The storefront's own registry, `GET /press/collections`,
is separate and unchanged by it.

| Collection | Minimum Press tier | Grove access | Components |
| --- | --- | --- | --- |
| Foundation and Corporate Giving | Standard | Shared | `reviewed_disclosures` |
| PLOT | Press+ | Shared | `environmental_permits`, `environmental_events` |
| Gaming Intelligence | Unavailable | Exclusive | Existing Gaming component map |

The existing `/press/collections/{id}/full-download` endpoint accepts an explicit
`release_id` and `component` for these collections. All component downloads use
the established collection catalog/manifest/hash/schema/rights verifier. The
presentation list in `governed_collections.py` is a compatibility gate; Lumecon's
embedded contract remains the type, grain, rights and release authority. Giving
decimal amounts remain exact serialized strings. PLOT EPA context does not
establish Native ownership or parcel affiliation.

Configure `CEDAR_PRESS_COMPONENT_RELEASE_CATALOG` and
`CEDAR_PRESS_COMPONENT_RELEASE_PIN` with the exact reviewed collection catalog
and pin. They are separate from the original dataset catalog configuration so
both formats can coexist. The committed shared pin is empty. Gaming keeps its
existing Grove pin/catalog. A review requires `CEDAR_GROVE_ENVIRONMENT=review`
with `CEDAR_PRESS_ENVIRONMENT=development`, matching the existing component
review path; production refuses this setting. Source rights are provenance in
review as in production: only tenant-private data is refused.

Reproduce a saved real candidate without a server listener or child process:

```sh
PYTHONPATH=server python server/tests/shared_collection_rehearsal.py \
  --store <immutable-store> --collection plot --release <sha256> \
  --output <isolated-review-directory>
```

The interpreter must have both Cedar and Lumecon importable. The command verifies
the actual immutable candidate, writes an isolated review catalog/pin, calls both
FastAPI applications in process, tests Press/Press+/Grove and production refusal,
and writes `receipt.json`. It does not start a database or claim database proof.
Use `foundation-corporate-giving` for Giving.

Recovery verification on 2026-09-26 used real PLOT release
`1d8a75617b4ee1749d65c7aacc344f9a228f7f2ea9081420bcd0547956fef3a6`:
1,242 permit rows and 3,210 event rows matched their manifest checksums at both
entitled tiers. Giving release
`f65ea15d5f63ccd4ccb8b9425a744ab7e33f77e62ca66bb98a962fd4b81b6fac`
was verified at 14 rows and download-held, because its redistribution flag was
off. That result predates the owner ruling of 2026-10-04, under which the flag is
provenance and no longer holds a download; the Giving candidate has not been
re-run since. These are rehearsal releases, not production eligibility or
complete PLOT parcel/ownership coverage.

### Replay the original collections and Gaming without collecting large bodies

The legacy dataset v1 format has no governed production eligibility label.
Its full-download path now requires both `CEDAR_PRESS_ENVIRONMENT=development`
and `LUMECON_ENVIRONMENT=review`; staging and production refuse before calling
the data API. Collection releases keep their production gate; a rights class is recorded as provenance and no longer gates (owner ruling 2026-10-04), except `tenant_private`.
Neither redistribution rights nor a successful database import issues a release.

`tests/stream_release_rehearsal.py` runs saved native datasets, original
partitioned tables, and Gaming components through both real ASGI applications.
The queue is a JSON array of `{ "collection": "...", "release": "<sha256>",
"store": "<immutable-store>" }`. Install both packages in one interpreter.

```sh
PYTHONPATH=server python server/tests/stream_release_rehearsal.py \
  --queue <saved-queue.json> --output <review-receipts> \
  --temporary-directory <bulk-scratch-directory> --code-revision <consumer-sha> \
  --timeout-seconds 1800
```

Use `--collection <id>` to run one unfinished collection, or `--resume` to
reuse same-revision successes only after the producer re-verifies every saved
part. The script refuses inherited database configuration before importing the
app. It starts no listener or subprocess and does not rebuild source data.
Producer HTTP bodies are disk-spooled; the unchanged consumer verifies bounded
parts; the consumer ASGI send callback computes SHA-256, bytes and newline rows
without storing the logical body. An independent streaming read checks the
manifest-ordered local artifacts. Anonymous, wrong-tier and production controls
remain active. An absent component is disclosed separately from a served one.
Failures write per-collection receipts and the queue continues. A tenant-private
or internal-only component must be refused with a 503, as the API refuses it.

Temporary files, SQLite scratch, and configurable caches must point at a drive
with measured space. Progress is emitted by collection and every 64 MiB of HTTP
body. Requests have an asynchronous timeout; synchronous producer verification
may finish before cancellation can complete, so retain the coordinator's process
and log stall monitoring. Redirect output to a persistent operation log. The
collector regression streams 16 MiB with less than 2 MiB of traced allocation;
that synthetic check is not a real collection receipt.

### Complete Gaming component review

`data/cedar/gaming_component_contracts.json` records presentation columns from
the exact saved Gaming release: 24 logical tables, including nine tables with
permitted downloads. It contains schema metadata only. Existing field-map
entries take precedence; additional tables must still match their pinned
producer schema exactly. Since the owner ruling of 2026-10-04 ("Lumecon
transforms the data it publishes; source rights statuses are recorded as
provenance and do not block publication") Lumecon-data's Gaming releases ship
every column of any field-rights class (projection rule
`gaming-presented-fields-v2`), so each changed entry, and the
`gaming_government_payments` field-map entry, also lists that column set in
`compatible_orders`; `order` stays the saved release's columns. The added
columns are in `fields` with their rights class and are not in `display_order`.
Since projection rule `gaming-presented-rows-v3` (Lumecon-data
`gaming.2026-10-04.2`) a Gaming row of any row-level rights class or publication
status ships too, with both recorded, and every component, partitioned parts
included, is downloadable; the columns did not change, so no declaration did.
Since `gaming.2026-10-04.3` (owner ruling 2026-10-04) FAC single audits and
bond disclosures (rating actions, fund holdings, MSRB EMMA) are tribal entity
filings, not Gaming: `gaming_financial_disclosures` carries only SEC facility
figures, management-contract terms and NIGC financing reviews, with the same
columns, and Lumecon-data's `entity-filings` producer writes
`tribal_entity_financial_filings.csv` for the entity layer keyed by Cedar ID.
Since projection rule `gaming-public-sources-v4` (owner ruling 2026-10-04:
"Casino City data is not published; Gaming publishes from public sources") a
Gaming row of `rights_class` `internal_vendor`, or naming Casino City or
4wheeler, is not published; columns are unchanged, so no declaration changed.
The release-class gate (a rehearsal
release, built on proposed IDs, is served only in review) and Grove-only
entitlement remain runtime gates. Tables marked `internal_only` remain
unavailable. The stream rehearsal refuses to resume an old two-table receipt as
evidence for the complete declaration, and checks each component.


### Verified download memory and lifetime

Governed single components and multipart components use the same disk-backed
validation path as partitioned Press tables. Network reads are at most 64 KiB;
validation retains one JSON record at a time and uses SQLite for global key
uniqueness. Every part must match its exact size, SHA-256, field set, row count
and primary key before any response starts. Duplicate JSON fields, nonfinite
constants, truncated records and duplicate keys are refused. Exact source bytes,
including decimal spellings, remain unchanged. Temporary storage closes on
validation failure, response completion, disconnect and cancellation.

Size temporary storage for concurrent verified downloads; the configured
per-component limit still applies. This path does not promote a rehearsal
release or certify upstream transforms as streaming.
Reproduce with `python -m unittest server.tests.test_partitioned_release
server.tests.test_gaming_release server.tests.test_shared_release_collections
server.tests.test_grove_exchange` from the repository root, with `server` on
`PYTHONPATH` and the pinned Lumecon runtime installed. Fixture tests require the
explicit review environment already used by CI.

The Grove container installs only this consumer's dependencies from the
committed `server/uv.lock`, using `uv sync --locked --no-dev --no-install-project
--project server`. It imports the pinned checkout through `PYTHONPATH`. The
producer remains behind the authenticated Lumecon API; producer source code is
not a runtime dependency of the Grove container. The producer commit in the
application contract identifies the tested API pair, not an extra local service.
Regenerate this lock from `server/pyproject.toml` with `uv lock --project server`
when changing dependencies and rerun the pinned container and consumer tests.

## Cedar Grove Gaming release pin

Moved here on 2026-10-12 from `docs/GAMING_GROVE_INFRASTRUCTURE_NOTES.md` (2026-09-24,
at the tag `data-workspace-final`). Its publication-hold step is gone since the owner
rulings of 2026-10-04, and its issuance tests left with the data workspace. Minting
Cedar IDs and issuing Gaming IDs have no home in this repository: both jobs were
handed to Lumecon-data's maintainers when the data workspace was retired, and the
issuing code is at the tag `data-workspace-final`.

### The pin

`data/cedar/grove_release_pin.json`:

```json
{"schema_version": 1, "product": "cedar_grove", "pins": {
  "gaming": {"catalog_id": "<64 hex>", "catalog_sha256": "<64 hex>",
             "collection_id": "gaming", "release_id": "<64 hex>",
             "manifest_sha256": "<64 hex>"}}}
```

- **Production is empty** (`"pins": {}`) until Cedar issues the Gaming IDs
  and Lumecon builds a production release from the issued registry snapshot.
  The route then answers `503 No released data is pinned for this collection
  yet` and audits `not_pinned`. It never falls back to a sample, a local CSV,
  a branch or a `current` pointer.
- **It extends, not replaces, `CEDAR_GROVE_RELEASE_CATALOG`.** The variable
  still names where the reviewed catalog's bytes are deployed. The pin says
  which bytes they must be (`catalog_sha256` over the exact file and the
  recomputed `catalog_id`) and which release inside them.
- **One release, not per-table releases.** `collection_id` must equal the
  collection ID. A pin naming `gaming--<table>` is refused. So is any catalog
  that is not a Lumecon `collection_releases` catalog, such as a dataset
  catalog of per-table releases. Cedar never assembles a collection from
  unrelated table releases.
- **Rehearsal releases are served only in an explicit nonproduction review;
  synthetic ones never in a deployed server.** `repository.GROVE_SERVED_RELEASE_CLASSES`
  is `{"production"}` and `GROVE_SERVE_SYNTHETIC` is `False`.
  `CEDAR_GROVE_ENVIRONMENT=review` (the analogue of Lumecon-data's
  `LUMECON_ENVIRONMENT=review`) adds `rehearsal`, and only when
  `CEDAR_PRESS_ENVIRONMENT` is not `production`. Unset or `production` serves
  production releases only. `review` in a production service, or any other
  value, refuses every Grove download (fails closed, 503). Only the consumer
  tests widen `GROVE_SERVE_SYNTHETIC`, for the synthetic rehearsal fixture.
- **Rollback** is a revert of the pin PR. Because it is one release, every
  component returns to its prior bytes together (atomic).

### What the server checks, in order

1. The collection is in the Grove declaration. The component is well formed
   and is a field-map presentation entry of that collection. Otherwise the
   request is refused before any read, and the audit redacts the component to
   `unknown`.
2. Session and current account tier: anonymous 401, press/press_pro 403, a
   downgraded, removed or unreachable account refused before the pin is read.
3. The pin is well formed and names the collection.
4. The catalog bytes at `CEDAR_GROVE_RELEASE_CATALOG` hash to
   `catalog_sha256`, `catalog_id` recomputes, and the product is
   `cedar_grove` with `entitlement_required`. The catalog kind is
   `collection_releases`, with exactly one entry for the collection. That
   entry's `release_id`, `manifest_sha256` and
   `manifest_path` (`/v1/collections/<id>/releases/<rid>/manifest`) equal the
   pin.
5. The collection manifest fetched from the Lumecon API hashes to
   `manifest_sha256`. It names the pinned collection and release, has
   `release_kind: collection` and product `cedar_grove`, and its
   `release_class` and `synthetic` flag are served.
   A `partitioned_components` declaration (bounded parts, e.g. payments)
   must agree with its part entries in this manifest. Every part must be
   present with the same record count and `records.jsonl` hash, and the
   logical count must be their sum. Otherwise the whole release is refused.
6. A logical partitioned component is assembled in manifest order into a
   temporary disk spool, after each part passes the same contract checks.
   Direct part requests remain refused. No part may be tenant-private; its
   publication class, redistribution and `download_permitted` are recorded as
   provenance and not checked (owner ruling 2026-10-04). Its field names, in
   order, equal the field-map `order`, and each shipped field's `rights_class`
   equals the contract's `metadata.field_rights` (the classes must agree; none
   has to be public). Its primary key is within the header, and the count and
   artifact size are bounded.
7. The component bytes come from
   `/v1/collections/<id>/releases/<rid>/components/<name>/download`. They
   match the manifest's size and SHA-256, the record count
   and schema, and the primary keys are nonblank and unique.

For partitioned downloads, all parts must agree on fields and primary keys.
A disk-backed unique-key index checks keys across the entire logical table.
Every bounded part is verified before any response bytes are sent; a missing,
restricted, malformed or tampered final part refuses the entire download.
The successful response streams the verified spool in 64 KiB chunks and closes
it on completion or disconnect. The response hash is the SHA-256 of the exact
manifest-ordered concatenation; metadata exposes individual pinned part hashes.
JSONL remains the internal and customer transport here; no CSV conversion is implied.
This adapter does not itself establish scientific validity or production eligibility.

The response is exact JSONL with `X-Cedar-Release`, `X-Cedar-SHA256`,
`X-Cedar-Component`, `X-Cedar-Rows`, `X-Cedar-Citation`
(`Cedar Grove gaming/<component>, release <id>`) and
`Cache-Control: private, no-store`.

### Tests

- `server/tests/test_gaming_release.py`:
  - `GamingConsumerBoundaryTest` runs without Lumecon. It checks the empty
    production pin (fails closed, clear error), malformed and per-table pins,
    entitlement decided before any pin, catalog or artifact read, redacted
    component refusal, and the storefront unchanged.
  - `ZeroCanonicalDuplicationTest` fails if a producer module, binding
    register, component CSV or schema copy reappears.
  - `PinnedLumeconReleaseTest` builds the synthetic fixture release with the
    installed `lumecon-data gaming fixture-release`, plus a second, later
    release. It serves them through Lumecon's own verification
    (`verify_collection_release`, `collection_manifest_metadata`,
    `read_collection_component`) in place of the network hop to Lumecon's
    read-only API collection routes. It covers schema compatibility per component,
    manifest/hash agreement, exact bytes, idempotent re-pinning, atomic
    rollback, unavailable and mismatched releases, served bytes that differ
    from the manifest (Cedar's own size/SHA-256 check), rehearsal refused in
    production and served only under `CEDAR_GROVE_ENVIRONMENT=review`, and
    refusal of per-table catalogs.
- CI: job `gaming-release-consumer` in `.github/workflows/ci.yml`. It checks
  out Lumecon-data at the exact pinned SHA with the read-only secret
  `LUMECON_DATA_READ_TOKEN` (`persist-credentials: false`), fails unless
  `git rev-parse HEAD` equals the pin, installs from that local checkout, and
  fails naming the secret when it is absent. `gamingConsumerCi.test.js` (node suite)
  lints those properties and shows each rule catching its own mutation.
