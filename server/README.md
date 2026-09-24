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
| `CEDAR_PRESS_SECRET` | Signs the session cookie. Without one, a restart invalidates every session rather than accepting forgeable cookies. |
| `CEDAR_PRESS_ACCOUNTS` | Provisioned subscribers as JSON. Empty by default, so a service started without accounts authenticates nobody. |
| `CEDAR_PRESS_CODES` | Access codes as issued, keyed by code: `{"CODE": {"email": ..., "tier": ..., "expires": "YYYY-MM-DD"}}`. `expires` is optional. Empty by default, so a service started without a register activates nobody. |
| `CEDAR_PRESS_ORIGINS` | Comma-separated origins allowed to send credentialed requests. |
| `CEDAR_PRESS_INSECURE_COOKIE` | `1` in local development only: drops `Secure` so the cookie works over http. |

## Where the database goes

Every route reads through `repository.py`, which answers from the ported
modules today. When the collections move into Postgres it answers from there
and `app.py` does not change — routes hold HTTP concerns and no data access
of their own, which is what keeps that swap to one module.

Two other seams are marked and both are in-memory today, which means they are
forgotten on restart: `codes.py` holds which access codes have been spent, and
`session.py` holds accounts created by activation. In production both are rows
written in the same transaction — the account created, the code spent — and
neither belongs in process memory.

`session.py` is the same shape: `_lookup` is the seam the subscriber table
replaces, and the cookie, its flags and the payload the client reads all stay.

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
- Staging/production also require explicit secrets of at least 32 characters, a
  Postgres `DATABASE_URL`, and no development `CEDAR_PRESS_ACCOUNTS` fallback.
  Configuration validation is not proof of database availability or deployment readiness.

Cedar enforces subscriber access before fetching data, checks catalog integrity,
explicit release equality, schema, publication holds, rights, exact artifact
bytes/hash, row count and primary keys. No matching or cleaning happens in the
consumer. Missing, stale or malformed pins and service failures do not fall back
to a sample. NEED remains held by `code/cedar_publication.py`. Unconfigured
collections fail closed. Artifacts larger than 128 MiB require a reviewed streaming
extension; the cap is not silently raised or bypassed.

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
