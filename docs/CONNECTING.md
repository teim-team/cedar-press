# Connecting the workspace to its data

The workspace (`app.cedarpress.ai`) is the same client as the marketing door. It is connected when `VITE_API_URL` names the Press API in `server/`; with it unset it runs against the bundled sample catalog. The client never reaches a database. Everything below is the API's side.

## Run it locally, connected

```sh
pip install -e 'server[dev]'
cd server && uvicorn cedar_press.app:app --port 8000     # the API
npm run dev:connected                                     # the client, as the workspace host
```

`dev:connected` sets `VITE_API_URL=http://localhost:5173/api` and `VITE_APP_HOST=1`. Vite proxies `/api/*` to `:8000` with the prefix removed, which is how CloudFront will serve it, so the page and the API share one origin. The content policy in `index.html` allows no other origin (`connect-src 'self'` and `*.lumecon.ai`).

A local sign-in needs, on the API process:

- `CEDAR_PRESS_SECRET`: any long random string.
- `CEDAR_PRESS_INSECURE_COOKIE=1`: the cookie is otherwise `Secure`, and `http://localhost` drops it.
- `CEDAR_PRESS_ACCOUNTS`: `{"you@example.invalid": {"password": "<plain text>", "tier": "press_pro"}}`. Plain text is correct without a database; the PBKDF2 form belongs to the Postgres backend.

The client's calls and their paths are in `src/api.js`.

## What "connected and empty" looks like

With the API up and no data source, sign-in works and every page renders, but `GET /press/releases` returns `"releases": []` and each entry in `/press/release-collections` has `"release": null`. The Collections page then lists the collections and says no spreadsheet release has been published for each. That is deliberate: connected mode never falls back to sample records.

## What turns it on

Server-side, in `server/README.md` ("Running it", "Server-only configuration"):

- `CEDAR_PRESS_RELEASE_CATALOG`: a reviewed catalog from Lumecon-data `build_catalog`, or `CEDAR_PRESS_DATA_API` and `CEDAR_PRESS_DATA_TOKEN` for the Lumecon API.
- `DATABASE_URL`: Postgres for subscribers and access codes. Staging and production require it, plus secrets of 32 characters or more.
- `CEDAR_PRESS_ORIGINS`: the exact origins allowed to send credentialed requests.

## Deploying

Build the client with `VITE_API_URL=https://app.cedarpress.ai/api`, and add a CloudFront `/api/*` behavior to the API origin that forwards cookies and methods, disables caching, and removes the `/api` prefix before FastAPI. The router function (`infrastructure/cedarpress-router.js`) already leaves `/api`, `/auth`, `/press` and `/me` alone and serves the app shell for `app.cedarpress.ai`. Checklist and rollback notes: [`HOSTNAMES.md`](HOSTNAMES.md).
