# The Cedar Press API

A FastAPI service serving the routes the React client calls. Python because
the part of this service with real logic in it — inclusion rules, entity
resolution, release bookkeeping, CSV shaping — was already written in Python
for Cedar Grove, and was carried over here rather than reimplemented.

That is provenance, not a dependency. Cedar Press is a standalone product: this
package imports nothing from Cedar Grove and calls no Grove service. It reads
`data/cedar/collections.manifest.json`, generated from the Cedar data workspace
in `code/`, which is the same file the JavaScript client reads.

```
cedar_press/
  app.py             the routes: HTTP concerns only
  repository.py      where data comes from — the seam Postgres replaces
  session.py         who is signed in; a signed, HTTP-only cookie
  collections.py     the launch collection, ported from Cedar Grove's package
  press_catalog.py   briefs and the citation register, likewise
  claims.py          the claim-class discipline the findings are held to
```

`tests/test_collection.py` and `tests/test_access.py` each run both the Python
and the JavaScript implementation and compare them — the collection values in
the first, the access rules in the second — so the two cannot drift.

## Running it

```sh
pip install -e .[dev]
CEDAR_PRESS_SECRET=dev-secret \
CEDAR_PRESS_INSECURE_COOKIE=1 \
CEDAR_PRESS_ACCOUNTS='{"reader@example.org":{"password":"...","tier":"press"}}' \
CEDAR_PRESS_CODES='{"TBN4-9K2M-X7QD":{"email":"reader@example.org","tier":"press"}}' \
uvicorn cedar_press.app:app --reload --port 8000
```

| Variable | Purpose |
| --- | --- |
| `CEDAR_PRESS_SECRET` | Stable server-only session signing secret; staging/production require at least 32 characters. Only development may generate a temporary key. |
| `CEDAR_PRESS_ACCOUNTS` | Provisioned subscribers as JSON. Empty by default, so a service started without accounts authenticates nobody. |
| `CEDAR_PRESS_CODES` | Access codes as issued, keyed by code: `{"CODE": {"email": ..., "tier": ..., "expires": "YYYY-MM-DD"}}`. `expires` is optional. Empty by default, so a service started without a register activates nobody. |
| `CEDAR_PRESS_ORIGINS` | Comma-separated origins allowed to send credentialed requests. |
| `CEDAR_PRESS_INSECURE_COOKIE` | `1` in local development only: drops `Secure` so the cookie works over http. |

## Where the database goes

Every route reads through `repository.py`, which answers from the ported
modules today. When the collections move into Postgres it answers from there
and `app.py` does not change — routes hold HTTP concerns and no data access
of their own, which is what keeps that swap to one module.

`subscribers.py` already persists subscribers and access codes when `DATABASE_URL`
is configured. Redemption spends the code and creates its subscriber in one
PostgreSQL transaction. The environment-backed account/code fallback is for
development; staging and production refuse it. Install the PostgreSQL extra
with `uv sync --locked --no-dev --extra postgres --project server` from the
repository root and run the existing migration command in `DATABASE.md`.

Sessions expire after 14 days. Every authenticated request re-reads the subscriber
and current Press tier; removed subscribers and changed credentials or account
bindings invalidate existing cookies. Logout advances the subscriber's persistent
revocation revision, ending that email's sessions on all devices without ending
other seats' sessions. A stable server-only signing secret is required in staging
and production. Existing passwords, accounts and subscription tiers are preserved;
old cookies without lifecycle claims require a fresh sign-in.

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

## Shape the Research

`CEDAR_PRESS_DB` names the SQLite file that holds the Cedar Points ledger, the
priorities' counts and subscribers' requests (for example `server/var/cedar_press.sqlite`,
which is ignored). Unset, the store lives in memory and a restart forgets it:
right for the tests, wrong for a deployment. An account record in
`CEDAR_PRESS_ACCOUNTS` may carry `"account": "acct-name"` so several seats share
one subscription's ledger.


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
explicit release equality, schema, publication holds, rights, exact artifact
bytes/hash, row count and primary keys. No matching or cleaning happens in the
consumer. Missing, stale or malformed pins and service failures do not fall back
to a sample. NEED remains held by `code/cedar_publication.py`. Unconfigured
collections fail closed. Single artifacts and individual manifest parts are bounded
at 256 MiB. Larger logical tables require the explicit development-only
`CEDAR_PRESS_PARTITIONED_REHEARSAL=1` contract; staging/production refuse that path.
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
`docs/HAVALA_INFRASTRUCTURE_REVIEW.md` for exact revisions and results.

## Giving and PLOT component releases

`GET /press/release-collections` is the authenticated integration registry for
the 15 collection targets: the original 12, Foundation and Corporate Giving,
PLOT, and Gaming. Its tier-filtered entries have verified release metadata or
an explicit missing/unavailable value. It supplies no invented samples or row
counts. The existing original-12 storefront registry is preserved; this server
surface does not claim the new collection pages are delivered.

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
review path; production refuses this setting. Source rights remain enforced
even in review.

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
Use `foundation-corporate-giving` for Giving; the current real 14-row candidate
has redistribution disabled, so all subscriber tiers correctly receive a hold.

Recovery verification on 2026-09-26 used real PLOT release
`1d8a75617b4ee1749d65c7aacc344f9a228f7f2ea9081420bcd0547956fef3a6`:
1,242 permit rows and 3,210 event rows matched their manifest checksums at both
entitled tiers. Giving release
`f65ea15d5f63ccd4ccb8b9425a744ab7e33f77e62ca66bb98a962fd4b81b6fac`
was verified at 14 rows and download-held. These are rehearsal releases, not
production eligibility or complete PLOT parcel/ownership coverage.

### Replay the original collections and Gaming without collecting large bodies

The legacy dataset v1 format has no governed production eligibility label.
Its full-download path now requires both `CEDAR_PRESS_ENVIRONMENT=development`
and `LUMECON_ENVIRONMENT=review`; staging and production refuse before calling
the data API. Collection releases retain their existing production/class gates.
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
remain active. An absent component is disclosed separately from served or held
components. Failures write per-collection receipts and the queue continues.

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
producer schema exactly. Component rights, proposed-ID review restrictions and
Grove-only entitlement remain runtime gates. Internal tables remain unavailable.
The stream rehearsal now refuses to resume an old two-table receipt as evidence
for the complete declaration. It checks each component, including held responses.


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
per-component limit still applies. This change does not clear a publication
hold, promote a rehearsal release or certify upstream transforms as streaming.
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
