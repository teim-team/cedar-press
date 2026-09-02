# Architecture

The Cedar Press web client: a Vite + React application built as a static
bundle and served at `cedarpress.ai`.

## Cedar Press is standalone; Cedar Grove is a superset

Cedar Press is a product in its own right. It has no runtime dependency on
Cedar Grove: nothing in this repository imports a Grove module, calls a Grove
service, or reads a file only Grove produces.

The relationship that remains is one of content. Cedar Grove includes all the
datasets Cedar Press sells, and adds a data library and other public data work
that this repository neither builds nor describes. Grove is therefore a
superset of Press *by content*, and the two are siblings by construction: both
read the same upstream, the Cedar data workspace, and neither reads the other.

```
  code/  (the Cedar data workspace)
    │
    └── scripts/import_cedar_manifest.py
          │
          └── data/cedar/collections.manifest.json ──┬── server/cedar_press/  (Python)
                                                     └── src/features/grove/  (JavaScript)
```

`data/cedar/collections.manifest.json` is generated, never hand-edited, and is
the only source of collection values either implementation reads.
`server/tests/test_collection.py` runs both implementations and compares them
field by field; `server/tests/test_access.py` does the same for the access
rules.

### Where the `grove/` paths came from

The retired model was a pipeline: the data workspace fed Cedar Grove, and Cedar
Grove published a slice of itself as Cedar Press. Under that model this client
carried the platform's own modules and kept the platform's paths so that
"re-syncing a module is a copy, not a translation" — which is why the code sits
under `src/features/grove/`, `src/components/grove/`, `src/pages/grove/` and
`src/styles/grove/`.

The owner retired the model on 2026-09-02. Nothing re-syncs from Grove any
more, so the paths no longer state a fact about the code; they are vestigial
names. Note that `src/features/`, `src/components/` and `src/pages/` contain
*only* a `grove/` directory each: every file under those paths is Cedar Press,
and there is no Grove code in this repository to be distinguished from.

**The rename is a named next step, not done here.** Measured on
`cedar-consolidated` at `05b438d`:

| | |
|---|---|
| Files to move | 55 (`features/grove` 32, `pages/grove` 21, `components/grove` 1, `styles/grove` 1) |
| Path references to rewrite | 164, across 42 files |
| Referencing files inside `src/` | 22 — 17 pages, 2 features, and one each of `context/`, `components/` and `main.jsx` |
| Referencing files outside `src/` | 20 — `package.json`, `tests/smoke.spec.js`, 3 under `scripts/`, 5 under `server/cedar_press/`, 4 under `code/`, 5 under `docs/`, 1 under `data/` |
| Files also touched by an open PR | 12 — 9 by #36, 3 by #37 (2 of them new files) |

It is a mechanical rename with no behaviour change, and the reason to defer it
is the last row: every one of those 12 files would become a rename/edit
conflict in a PR that is already open against this branch. It should land as
its own commit once #36, #37 and #38 are merged, moving the four directories to
`press/` and rewriting the references in one pass.

## Layout

```
src/
  main.jsx                 route table and providers
  api.js                   platform API client
  context/                 session provider and the useAuth hook
  features/grove/          collection, release, entitlement and article models
                           (+ their unit tests, run by `npm run test`)
  components/grove/        figure renderers shared with the platform
  pages/grove/             the pages, their chrome and their page-local parts
  styles/                  tokens (index, redesign) and the press stylesheet
public/                    fonts, imagery, CNAME
```

## Routing

`src/features/grove/pressRoutes.js` is the single source of the URL map;
`main.jsx` registers it. Paths sit at the domain root here (`/data`), where
the platform namespaces them (`/press/data`), and every page reads its path
from that module rather than writing a string.

## Pages

The overview states what the service is and indexes the sections, with each
section's standing read from the catalog. `Articles` and `Data` are the two
content sections; `What's new`, `Methods`, `Tribal data request` and
`Research access` stand alone so each URL can be sent to someone directly.
`PressChrome.jsx` owns the masthead, its section nav and the footer, so the
pages cannot drift apart.

## Connected and standalone

`config.js` decides which deployment this is: with `VITE_API_URL` set the
client is connected to the platform API and its database; without it the
client serves the bundled catalog, so the service can be demonstrated and
reviewed on its own. Modules ask `isConnected()` rather than inferring the
answer from a failed request, so a network error never silently reads as
"standalone" and shows fixtures in production.

The seam is deliberately narrow. Pages read `user`, `loading`, `login`,
`logout` and `refreshSession` from the session provider and never learn which
mode they are in. Connecting a deployment is configuration, not a rewrite.

## The API

`api.js` is the only module that knows the platform's endpoints. Sessions
ride in cookies (`credentials: "include"`) rather than browser storage,
because a token in storage is a token any script on the page can read.
Errors come back as `{ code, message }` and are rethrown as an `ApiError`
carrying `code` — the shape `pressSignup.pressSignupError` already reads.

| Endpoint | Purpose |
| --- | --- |
| `GET /me`, `POST /auth/login`, `POST /auth/logout` | The session |
| `POST /press/activation`, `/press/activation/validate` | Subscription activation |
| `GET /press/collections` | The catalog this subscription can see |
| `GET /press/releases` | Release history |
| `GET /press/articles` | Published briefs |
| `GET /press/collections/:id/download` | A release file, served as a blob |
| `GET /press/collections/:id/profile` | The collection's data dictionary |
| `POST /cedar/ask` | Cedar, scoped to this surface |
| `GET`, `PATCH /press/profile` | The reader's declared work — **not served by `server/`** |

Every row but the last is implemented by the FastAPI service in `server/`.
`/press/profile` (`src/features/grove/readerWork.js`) exists only on the
Lumecon platform backend, so a deployment pointed at Cedar Press's own API
404s on it: the read is swallowed and reads as "not answered", the write
rejects with nothing shown to the reader. It is the one endpoint the client
still assumes the platform for, and closing it is either implementing the
route in `server/` or dropping the connected path in favour of the
`localStorage` one `readerWork.js` already has.

## Running the API

The API is a FastAPI service in `server/`. Its collection modules were ported
from Cedar Grove's Python package rather than rewritten, so the inclusion rules
and release bookkeeping kept one definition. That is where the code came from,
not something it still depends on: the service imports nothing from Grove and
reads its values from `data/cedar/collections.manifest.json` like the client
does.

```sh
pip install -e server[dev]
uvicorn cedar_press.app:app --reload --port 8000
cd server && python -m unittest discover -s tests -t .
```

Point the client at it with `VITE_API_URL=http://localhost:8000 npm run dev`.

## Deployment

Pushes to `main` build and deploy to GitHub Pages via
`.github/workflows/deploy.yml`, which runs lint, unit tests, the smoke suite
and the API's own checks first. The custom domain is set in `public/CNAME`,
and the build emits `404.html` alongside `index.html` so client-side routes
resolve on a static host.

Because that deployment is standalone — no `VITE_API_URL` — the gate there
offers sign-in only. Activation needs an API to validate a code against, and
`PRESS_ACTIVATION_AVAILABLE` follows `isConnected()` rather than a constant,
so a build with nothing behind it cannot ask for a code it cannot check.

## Access

`features/grove/pressAccess.js` resolves a session's tier to what the client
renders — which shelves open, which collections download. Entitlement is
authoritative on the server, and the client model is written to answer
identically. The preview accounts in `context/authContext.js` are a
standalone-only path: a connected deployment authenticates against the API
and rejects them.

## Telemetry

`features/grove/telemetry.js` starts Datadog RUM only when an application id
and client token are both configured, and imports the SDK dynamically so a
deployment without telemetry never downloads it. It reports errors and
performance plus a small set of named product events — signed in, section
opened, collection viewed and downloaded, locked collection tapped, article
opened, Cedar asked. There is deliberately no page-wide
click or scroll capture: behavioural exhaust nobody reads is a privacy cost
with no product return. Subscribers are identified by tier and an opaque id;
email addresses are never sent.

## Data and downloads

`features/grove/collection.js` holds the launch collection's descriptors and
figure specs; `pressReleases.js` holds release history and is the source of
the version a download carries, so a saved file can be matched to the
changelog. `pressDownload.js` builds the file, and every download carries its
own citation, because provenance that lives only in the interface is
provenance a reader loses on save.

## Interface conventions

- **Both pointers.** Hover affordances have tap equivalents: on a coarse
  pointer the shelf's first tap opens the collection's description and the
  download moves into that panel.
- **Themes.** The press pages hold the paper palette in both themes
  (`.teim-rd--paper` re-pins the light tokens), so the document declares
  `color-scheme: light`.
- **Reveals.** Sections arrive on scroll through `useReveal`; anything behind
  one must still be present for a reader who does not scroll it.
- **Accessibility.** A skip link opens every page and lands on its `main`;
  one focus ring covers every control and inverts on the teal panels, where a
  dark ring is invisible; headings descend by one; text clears WCAG AA
  contrast; the methods diagram is a group of buttons rather than an image.
  Motion — the page's arrival rise and the tile hover — collapses entirely
  under `prefers-reduced-motion`, not merely shortens. Checked with axe
  against every route at desktop and phone widths.
