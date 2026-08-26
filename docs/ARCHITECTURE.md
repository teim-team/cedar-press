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
mode they are in; `features/grove/datasets.js` presents one descriptor shape
whether a dataset lives in the database or in this browser, with a
`published` flag that says which. Connecting a deployment is configuration,
not a rewrite.

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
| `GET`/`POST` `/press/datasets`, `DELETE /press/datasets/:id` | Subscriber datasets |
| `POST /cedar/ask` | Cedar, scoped to this surface |

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
opened, dataset uploaded, Cedar asked. There is deliberately no page-wide
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
- **Accessibility.** The pages carry one `main` landmark, headings that
  descend by one, and text that clears WCAG AA contrast; the interactive
  diagram on the methods page is a group of buttons rather than an image.
  Checked with axe against every route.
- **Demonstration content.** Where fixtures stand in for material that has not
  published, the interface says so on the item itself rather than in a
  disclaimer far from it.
