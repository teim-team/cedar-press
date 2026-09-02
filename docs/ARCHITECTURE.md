# Architecture

The Cedar Press web client: a Vite + React application built as a static
bundle and served at `cedarpress.ai`.

## Shared lineage

Cedar Press and the Lumecon platform render the same collections. Rather than
describe them twice, this client carries the platform's own modules — design
tokens, figure specs, collection and release models, entitlement rules — so a
change to a collection reaches both surfaces and neither can drift from the
other. Files under `src/features/grove/`, `src/components/grove/`,
`src/pages/grove/` and `src/styles/` keep the platform's paths for that
reason: re-syncing a module is a copy, not a translation.

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
| `POST /cedar/ask` | Cedar, scoped to this surface |

## Running the API

The API is a FastAPI service in `server/`, carrying Cedar Grove's own Python
collection modules rather than reimplementing them, so the inclusion rules and
release bookkeeping have one definition.

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

The build output is **`dist-site/`**, not vite's default `dist/`. The data
workspace tracks 295 files under `dist/` and vite empties its output directory
before every build, so sharing the name meant every `npm run build` deleted
them. `build.outDir` in `vite.config.js` and `upload-pages-artifact`'s `path:`
in the workflow have to move together; changing one alone publishes the data
bundle, or nothing.

An operator sets exactly two things, both in repository settings rather than
in code:

| Setting | Effect |
| --- | --- |
| `vars.VITE_API_URL` (repository **variable**) | Unset is standalone. Set it and the deployment is connected: real sessions, activation, the database as the source of truth. |
| `secrets.VITE_PRESS_DEMO_ACCOUNTS` (repository **secret**) | The standalone preview account, as a salted digest. Unset means the build signs nobody in. Ignored entirely once `VITE_API_URL` is set. |

Because the Pages deployment is standalone by default, the gate there offers
sign-in only. Activation needs an API to validate a code against, and
`PRESS_ACTIVATION_AVAILABLE` follows `isConnected()` rather than a constant,
so a build with nothing behind it cannot ask for a code it cannot check.

## The standalone sign-in

`features/grove/pressDemoGate.js` is the sign-in on a build with no API. It is
a **demonstration gate, not access control**, and the module and the page copy
both say so: a static site ships every byte it checks against, so a visitor
who opens devtools can read the account record and delete the check. What it
does is keep the preview shut to a casual visitor and let a named reviewer in.

It is acceptable only because nothing behind it is confidential. The
standalone bundle carries the catalog, the methods, the release history and
ten sampled rows per table (`public/data/cedar/samples/*__10.csv`); the
collections are not in it. If that stops being true the deployment has to
connect.

Two properties make it defensible on its own terms. The account arrives as a
salted SHA-256 digest, so no password is committed or bundled — the same
reason `server/cedar_press/session.py` reads `CEDAR_PRESS_ACCOUNTS` from the
environment. And a build configured with nothing authenticates nobody:
`PRESS_DEMO_GATE_ACTIVE` is false, the gate renders a sentence instead of a
form, and `verifyPressDemoAccount` returns null for every password.

`isConnected()` turns it off. Connected, `AuthProvider` never consults it and
`POST /auth/login` with the signed, HTTP-only cookie takes over.

## Access

`features/grove/pressAccess.js` resolves a session's tier to what the client
renders — which shelves open, which collections download. Entitlement is
authoritative on the server, and the client model is written to answer
identically. The demo gate's account is a standalone-only path: a connected
deployment authenticates against the API and never reads it.

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
