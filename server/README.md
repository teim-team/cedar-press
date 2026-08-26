# The Cedar Press API

A FastAPI service serving the routes the React client calls. Python because
the part of this service with real logic in it — inclusion rules, entity
resolution, release bookkeeping, CSV shaping — was already written in Python
for Cedar Grove, and is carried over here rather than reimplemented.

```
cedar_press/
  app.py             the routes: HTTP concerns only
  repository.py      where data comes from — the seam Postgres replaces
  session.py         who is signed in; a signed, HTTP-only cookie
  collections.py     the launch collection, ported from Cedar Grove's package
  press_catalog.py   briefs and the citation register, likewise
  claims.py          the claim-class discipline the findings are held to
```

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
| `CEDAR_PRESS_SECRET` | Signs the session cookie. Without one, a restart invalidates every session rather than accepting forgeable cookies. |
| `CEDAR_PRESS_ACCOUNTS` | Provisioned subscribers as JSON. Empty by default, so a service started without accounts authenticates nobody. |
| `CEDAR_PRESS_ORIGINS` | Comma-separated origins allowed to send credentialed requests. |
| `CEDAR_PRESS_INSECURE_COOKIE` | `1` in local development only: drops `Secure` so the cookie works over http. |

## Where the database goes

Every route reads through `repository.py`, which answers from the ported
modules today. When the collections move into Postgres it answers from there
and `app.py` does not change — routes hold HTTP concerns and no data access
of their own, which is what keeps that swap to one module.

`session.py` is the same shape: `_lookup` is the seam the subscriber table
replaces, and the cookie, its flags and the payload the client reads all stay.

## Checks

```sh
ruff check . && ruff format --check .
python -m unittest discover -s tests -t .
```
