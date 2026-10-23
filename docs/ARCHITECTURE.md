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
read the same upstream, Lumecon-data, and neither reads the other.

```
  Lumecon-data (verified releases)
    │
    └── scripts/stage_verified_previews.py
          │
          └── data/cedar/collections.manifest.json ──┬── server/cedar_press/  (Python)
                                                     └── src/features/grove/  (JavaScript)
```

`data/cedar/collections.manifest.json` is staged by that script and installed by
hand, its descriptor prose reviewed at each refresh (`data/cedar/README.md`,
"Refresh the served data"). It is the only source of collection values either
implementation reads.
`server/tests/test_collection.py` runs both implementations and compares them
field by field; `server/tests/test_access.py` does the same for the access
rules.

### Where the `grove/` paths came from

Until 2026-09-02 this client carried Cedar Grove's modules under the
platform's paths, so that re-syncing one was a copy. The owner retired that
model then, and nothing re-syncs from Grove. The paths are vestigial names:
`src/features/`, `src/components/` and `src/pages/` each hold only a `grove/`
directory, and every file under the four `grove/` paths is Cedar Press.

**The rename is a named next step, not done here.**

`server/tests/test_rename_plan.py` re-measures every figure in this table on
each test run, the breakdowns included, and `test_rename_plan_gate.py` injects
a stale figure to prove the comparison fails. Re-measured with:

```
git grep -I -o -E '(features|pages|components|styles)/grove'   # references
git ls-files src/<dir>/grove                                   # files to move
```

| | |
|---|---|
| Files to move | 184 — `features/grove` 134, `pages/grove` 45, `components/grove` 1, `styles/grove` 4 |
| Path references to rewrite | 407, across 86 files |
| Referencing files inside `src/` | 55 — `pages/` 37, `features/` 15, `context/` 1, `components/` 1, `main.jsx` 1 |
| Referencing files outside `src/` | 31 — `server/cedar_press/` 7, `scripts/` 7, `docs/` 6, `server/tests/` 5, `tests/` 2, `data/` 2, `.env.example` 1, `eslint.config.js` 1 |

The reason this was deferred, open pull requests that touched the same files,
has expired.

It is a mechanical rename with no behaviour change, and it should land as its
own commit: the four directories move to `press/` and the references are
rewritten in one pass. The question "did all 407 references get rewritten?"
is one the build, the suites and the smoke run answer, and a reader cannot
answer it from a diff. Prose (Markdown, comments, `.env.example`) is what no build sees,
which is why `test_rename_plan.py` counts textual occurrences rather than
imports; on the day the directories move, the same check names every file that
still spells the old path. `playwright.config.js` does not reuse a server it
did not start, so the smoke run measures its own checkout; set
`CEDAR_PRESS_SMOKE_PORT` when two checkouts run it at once.

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

## Connected and public

`config.js` decides what a page talks to: with `VITE_API_URL` set the client
is connected to the platform API and its database, except on the public site
(`cedarpress.ai`), which has no API and no signed-in readers. With no
`VITE_API_URL` at all (a dev server, a bare build) nothing is connected and
the login page says so. Modules ask `isConnected()` rather than inferring the
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

Every request has a deadline, body included: 15 seconds
(`REQUEST_TIMEOUT_MS`), 45 for the research preview and 60 for Cedar, whose
server-side waits are 30 and 45. A miss rejects with code `TIMEOUT`, a
dropped connection with `NETWORK`, and `isUnreachable(error)` tells either
from a refusal. The session check, an article and the collection
spreadsheets answer an unreachable service with a Retry rather than a
verdict ("no dataset for this account"); the session's notice is portalled
outside `#root` so the prerender cannot capture it. Before the deadline a
stalled request left those three waiting indefinitely (2026-10-04 audit:
Fast 3G, still loading at 45 to 50 seconds; with it, Retry at 19 seconds).

The API compresses (`GZipMiddleware`, over 1 kB): `/press/collections` is
11,469 bytes instead of 48,283 for a Cedar Press+ account.

| Endpoint | Purpose |
| --- | --- |
| `GET /me`, `POST /auth/login`, `POST /auth/logout` | The session |
| `POST /press/activation`, `/press/activation/validate` | Subscription activation |
| `GET /press/collections` | The catalog this subscription can see |
| `GET /press/releases` | Release history |
| `GET /press/articles` | Published briefs |
| `GET /press/collections/:id/download` | A release file, served as a blob |
| `GET /press/collections/:id/profile` | The collection's data dictionary |
| `POST /cedar/ask` | Cedar, scoped to this surface (see **Cedar** below) |
| `GET`, `PATCH /press/profile` | The reader's declared work, per seat |
| `GET /press/priorities`, `/press/priorities/related`, `/press/influence`; `POST /press/priorities/:id/points`, `/press/requests` | Shape the Research |

Every row is implemented by the FastAPI service in `server/`; nothing in
teim-app or the Cedar engine serves a `/press/*` route, so that service is
the server this client is built for. How the platform stores accounts and
tiers, how it wires the Cedar engine, and what moving a subscriber into its
Postgres would take (tables, the cookie across origins, the ledger, the error
envelope) was measured on 2026-09-06 (`docs/PLATFORM_INTEGRATION_2026-09-06.md`, at the tag `data-workspace-final`). `/press/profile` was the last gap
(2026-09-05): it now reads and writes `reader_profiles` in the same SQLite
store as the Cedar Points ledger, validated against the vocabulary
`readerWork.js` offers (dumped into `_press_data.json` so the two cannot
drift).

### Cedar

One Cedar, one contract, three surfaces. `POST /cedar/ask` has two answerers
and tries them in this order:

1. **The collection's own release.** `collection_profiles.answer_from_profile`
   reads the profile's fields and never composes past them. The reply carries
   `source: "profile"` and a `basis` naming the release, which the panel
   prints under the answer.
2. **Cedar.** Anything the profiles cannot answer goes to the service in the
   `cedar` repository: `POST {CEDAR_BASE_URL}/api/v1/press/messages`, bearer
   `CEDAR_INTERNAL_API_KEY`, contract `1.0.0`. `server/cedar_press/cedar_service.py`
   is that client; `server/tests/test_cedar_service.py` validates the body
   against `cedar/schemas/press.py` itself when that checkout is present.

Past both it refuses (`501 NOT_ANSWERABLE`) and names the research desk, and
an unreachable Cedar is `503 CEDAR_UNAVAILABLE` rather than a made-up answer.

The hop happens on this side because the key is an internal one a browser
cannot hold: the reader arrives on a session cookie, entitlement is decided
here, and the request is re-issued to Cedar. `threadId` rides back and forth
so a panel is one conversation.

Unset `CEDAR_BASE_URL` (or no `CEDAR_INTERNAL_API_KEY`) means Cedar is not
wired into this deployment; the profiles still answer and the rest refuses.

The variables are teim-app's names, not a second spelling of them, with the
same `CEDAR_ENABLED` semantics. The chat path default is the Press route.
`CEDAR_API_PATH` overrides it. Pinned by `test_cedar_service.py`.

| Variable | Purpose |
| --- | --- |
| `CEDAR_BASE_URL` | Where the Cedar service is. Unset disables the second answerer. |
| `CEDAR_INTERNAL_API_KEY` | The bearer token `cedar/api/deps.require_internal_key` checks. `CEDAR_API_KEY` is read as a fallback. |
| `CEDAR_ENABLED` | Off only for the literal `"false"`; unset is on. |
| `CEDAR_API_PATH` | Endpoint override. Default `/api/v1/press/messages`. |
| `CEDAR_TIMEOUT_MS` | How long a reader waits. Default `45000` — shorter than teim-app's `120000`, because a reader is watching this panel. |

The client side is `src/pages/grove/PressCedarFab.jsx`. It and the door's
`PressDoorCedar.jsx` render one component, `CedarPanel.jsx`, sized to the
measured geometry of lumecon.ai's `CedarFAB.astro` panel, and run one
conversation runtime, `src/features/grove/cedarConversation.js` through the
`useCedarThread` hook: thread memory, drill-downs, repeat awareness, quick
replies under each answer. What differs is the answer source. The door sits
in front of the paywall and resolves against the bank in `doorCedar.js`
without touching the network; the reader's panel resolves against
`POST /cedar/ask`, keeps the service's `threadId`, and prints the answer
basis under every answer (`readerCedar.js` holds its quick replies).

Two client behaviours change with the switch and nothing else does:
`downloadCsv` asks `GET /press/collections/:id/download` (the service
enforces entitlement and serves the release file) instead of fetching the
static sample, and `readerWork.js` reads and writes the profile route instead
of `localStorage`. The demo gate turns itself off because every module
discriminates on `isConnected()`.

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

Pushes to `main` build once and publish that build to GitHub Pages and to an
S3 bucket behind CloudFront via `.github/workflows/deploy.yml`
(`docs/HOSTNAMES.md`), which runs lint, unit tests, the smoke suite and the
API's own checks first. The custom domain is set in `public/CNAME`, and the
build emits `404.html` alongside `index.html` so client-side routes resolve on
a static host.

The build output is **`dist-site/`**, not vite's default `dist/`: `dist/` was
the retired data workspace's output directory, which may still exist in a
checkout, and vite empties its output directory before every build.
`build.outDir` in `vite.config.js` and the `path:` of the workflow's artifact
steps have to move together; changing one alone publishes the wrong folder, or
nothing.

An operator sets exactly two things, both in repository settings rather than
in code:

| Setting | Effect |
| --- | --- |
| `vars.VITE_API_URL` (repository **variable**) | The API the workspace talks to, `https://app.cedarpress.ai/api`. Unset, nothing is connected: real sessions, activation and the database as the source of truth all need it. |

Activation needs an API to validate a code against, and
`PRESS_ACTIVATION_AVAILABLE` follows `isConnected()` rather than a constant,
so a build with nothing behind it cannot ask for a code it cannot check.

## What a crawler reads, and what a slow connection gets first

Three pages are public: the door (`/`), the tribal data request policy and
research access. They are what someone searching for data on a tribe, a
Native enterprise or Indian Country's economy should find, and everything
else answers with a sign-in, which a search engine should not rank.

- **Static HTML for the public pages.** `scripts/prerender.mjs` runs after the
  build (`npm run build:site`, which the deployment and the smoke suite both
  use) and renders the three pages with Chromium into `dist-site/index.html`,
  `dist-site/tribal-data-request/index.html` and
  `dist-site/research-access/index.html`. A crawler, and a reader whose
  bundle has not arrived, meets the page's text in the document; React then
  mounts over the same markup. `404.html` stays the empty shell, which is
  what every other path serves.
- **Per-page head.** `useDocumentTitle(title, { description, index })` sets
  the title, description, canonical address, Open Graph pair and a robots
  meta on navigation. The three public pages pass `index: true` with a
  description of their own; every page behind the gate says `noindex`, in
  agreement with `public/robots.txt`.
- **Structured data.** `scripts/seo-head.mjs` writes the JSON-LD in
  `index.html` from the catalog: the site, Lumecon, the product, a
  `DataCatalog` and one `Dataset` per storefront collection with its name,
  description, coverage, keywords and `isAccessibleForFree: false`. It also
  writes `public/sitemap.xml` with `lastmod` from the release ledger.
  `npm run seo:check` (a unit test runs it) fails when either is stale.
- **The first bundle is the reader.** `pages.jsx`, beside the pages, lazy-loads
  the nine satellite pages and `PressShelf.jsx` lazy-loads the Explore viewer,
  so the door paints before the Methods reference or the viewer's contracts
  are fetched. Measured at 400 kbps with a 4x CPU throttle: everything in one
  bundle was 184 kB gzipped and nine seconds to the first headline; split and
  prerendered, the headline is in the HTML at 0.7 seconds and the first
  bundle is 123 kB.
- **The codebook is fetched, not bundled.** `data/cedar/codebook.json`
  (400 kB minified) was compiled into the chunk every page loads.
  `features/grove/codebook.js` now imports it on demand: the record and the
  Explore viewer load it with their chunks, the door's preview with its
  sample, the download before it builds the file; nothing else fetches it.
  Its synchronous readers throw if called first, and `codebook.test.js`
  fails if any module imports the file statically again. Measured
  2026-10-04: the scripts and stylesheet every page loads before it mounts
  went from 270.5 to 238.6 KiB brotli; on the wire, fonts and HTML included,
  from 415.5 to 383.5 KiB before the door mounts.
- **Samples and chunks recover.** A sample that fails (error, non-200, or
  no answer in 15 seconds, `sampleFetch.js`) is not kept: the page says it
  could not be loaded, offers Retry, and reads it again when the browser is
  back online. A page whose code did not arrive keeps its Reload button and
  also reloads itself once on the `online` event (`reloadOnReconnect.js`).
  `tests/resilience.spec.js` holds both.

What this does not do: it does not publish records, entity pages or per-tribe
pages to the open web. The collections stay behind the subscription, and a
public page per Native entity is a product decision, not a build step.

## The public samples

The public door shows real rows: one sample customer table per collection, up
to ten rows (`public/data/cedar/downloads/<collection>.csv`), rendered from
verified Lumecon-data releases. Nothing confidential is in the bundle; the
collections are not. The signed-in viewer reads the same layout from the API
(`GET /press/collections/{id}/download`), so what a subscriber sees has the
shape of the sample, with whatever rows the API's data source holds.

## Access

`features/grove/pressAccess.js` resolves a session's tier to what the client
renders — which shelves open, which collections download. Entitlement is
authoritative on the server, and the client model is written to answer
identically.

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

`features/grove/collection.js` holds the descriptors and figure specs of the
collections that have a release, read from the manifest. `pressReleases.js` derives each
collection's release record from the same descriptor, so the version the
What's New feed shows, the version a citation names and the version a
download's filename carries are one value read from one place; the feed adds
a declared cadence per collection and, when a later release ships, editorial
change notes. `pressDownload.js` builds the file, and every download carries
its own citation, because provenance that lives only in the interface is
provenance a reader loses on save.

## Explore the collections

The card under the shelves (`pages/grove/PressExplore.jsx`) shows every
collection's records through the same three filters: which entity, which kind
of entity, which years. It can do that because no page knows a collection's
column names. `data/cedar/explore.json` is a CONTRACT per table, derived by
`scripts/derive-explore.mjs` from each collection's customer table
(`public/data/cedar/downloads/<collection>.csv`), that says which of the
table's columns are the record id, the entity uid, the name, the type, the
record's own subject, the year and what year means there (`year_basis`), the
date, the amount and its basis, the source, supersession, and which columns
make the one-line observation. Since 2026-10-04 every contract is a
customer-table contract (`customerTableContract`), marked reviewed, and the
few reviewed readings of a column carried over from the earlier producer
previews are in the script (`CUSTOMER_PRESENTATION`).
`data/cedar/explore.overrides.json` still wins where it speaks, but declares
no table today: its 2026-09-05 declarations named tables the 2026-10-01
release renamed, and were retired on 2026-10-02. The refresh steps run the
derivation (`data/cedar/README.md`, "Refresh the served data"), and
`make check-generated` and the node suite fail a stale file. The entity
register the pickers read is exported to `public/data/cedar/register.json` by
the same script.

Until the owner ruling of 2026-10-02 (a firm is a business entity whatever it
is named after; its name, identifiers and business address are public
business records), the retired importer struck any sample that carried an
individually Native-owned firm's name, and the register wrote those names
null. The register now writes every name (`withheld_names: 0`, asserted in
`explore.test.js`). In the model a withheld register name is `withheld`, never
a prompt to read the table's own name column.

`features/grove/explore.js` is the model. Everything the card shows is a
function of one object, the CUT: entities, entity types, a year range, the
collections, one table or none, a search, a sort, a page, and whether
superseded versions are shown. `types` and `collections` are `null` for no
restriction and `[]` for an explicit nothing, in the URL too (`t=`, `c=`).
The cut is the URL (`?e=…&t=…&y=2015-2024&c=…&tb=…&q=…&h=1`), written at once
so the controls and the applied query are one thing; a saved view is a
permalink with a name and the collections spelled out; the download is a ZIP
of `records.csv`, rectangular, one line per record, and a `README.txt` with
the citation per collection and the cut; the question to Cedar names the
collection. A link naming a collection this catalog lacks is not widened. A
record naming several entities carries each as an entity, and an entity
filter and a type filter are satisfied by the same one. A table with a year
column answers the year filter from that column only; `year_basis` is shown
over the control.

THE TILES DRIVE THE VIEWER. A tile on the shelf selects its collection in
the viewer and stays lit while the viewer shows it; the reader beside the
grid describes the collection and carries its sample download on every
pointer; hovering changes what is described, never what is selected. A
collection is ONE DATASET to a reader: its flagship table with the declared
default columns first and the rest one click away; supporting tables are not
browsing options (a `tb=` link is still honoured). A record opens in three
groups: what it says, its source and attribution, and its technical fields
folded away, with links, dates, money and flags rendered for a person and
the raw values kept for the download. On a phone the records are a list
(who, where, when, what; tap for the record), the three pickers sit behind
"Filters", and the year control is two boxes. Cedar's floating launcher
steps aside while the viewer is on screen; the viewer's foot carries the
Cedar action.

Phase one, shipped: the viewer over the customer tables (three to ten rows
each), static on Pages, the caption counting sample records and saying so, and what it is not showing
(locked, no preview, unreachable, undated, superseded). Not shipped, and
needing the API deployed: the full tables behind the same cut (a rows-and-
facets endpoint with authorization on every request), Cedar answering from
the cut rather than from the collection profile, and saved extracts pinned to
a release, shareable by opaque link, private by default, with the rows
following the viewer's own entitlement (`may_open`) and every open logged.
`CUT_VERSION` names the cut's shape so the service can accept older links and
say what changed.

## Collective scope: the population a record relates to

A Federal Register notice addressed to every federally recognized tribe, a
bill about a class of entities, a program open to all Alaska Native
Corporations: these records name no individual entity, and before 2026-09-05
they were indistinguishable from records whose named party the resolver
could not place. The owner's decision of 2026-09-05
(`docs/COLLECTIVE_SCOPE_DECISION_2026-09-05.md`, verbatim with its reasoning,
at the tag `data-workspace-final`) settles how they are represented, and its
centre is a boundary: **a scope is a population, never an entity**. No
`CE-XXXXX-CC` uid is minted for "all tribes", no entity class is added, and
`cedar_uid` keeps meaning the canonical Native entity. A record can carry both
named entities and scopes, and a scope is never a fallback for a failed entity
match. A scope never occupies a recipient or owner field, and scope-based
relevance never makes dollars attributable to an entity.

### What this repository does with it

- `data/cedar/scopes.json` is the vocabulary: the scope codes and their
  definitions, the five relationships (addressed, applies_to,
  eligible_class, aggregate_population, general_subject), the as-of rules,
  the membership kinds, and the element schema of the `collective_scopes`
  column (a JSON array; `[]` evaluated and none; null not evaluated).
- The field map declares `collective_scopes` on Legislation (built at write
  time from `bill_scope` and the class-level scope, relationship
  `general_subject`) and on the Federal Register (owed by the producer,
  Lumecon-data, from the source text, together with an `entity_link_status`
  of `no_individual_named`, `resolved`, `unresolved` or `withheld`).
- The retired writer (`code/cedar_publication.apply_field_map`, at the tag
  `data-workspace-final`) validated every element against the vocabulary and
  refused a scope code in an identity field; customer tables are now built in
  Lumecon-data.
- The shared query model (`explore.js`) carries `scopes` and `broad` in the
  cut, so the permalink, the saved view, the caption, the download and the
  Cedar question agree. Selecting a scope finds the records covering it;
  `broad` lets an entity filter include records covering a broader group the
  entity belongs to, off by default, evaluated per entity from the
  register's class only for scopes whose membership kind is
  `register_class` and only for an element dated on or after the register's
  own date (`register.json` carries `as_of`, the latest mint date: the
  register vouches for a class from then on, not before), and never for a
  state or NHO scope (unknown is never a match). A chosen entity that fails
  the type filter brings nothing in. A row passes once, at its own grain,
  and the export says how each row got in (`matched_by`). Every row included that way
  says why in the viewer, and the reduced export carries `collective_scopes`
  beside the entity columns rather than inside them.
- Nothing here displays a national membership count: the register's class
  totals have to be reconciled against the official BIA list in Lumecon-data
  first.

## The Cedar Business ID: a second identity, kept apart from the uid

On 2026-09-06 the owner adopted a reviewer's proposal for a permanent
business identifier separate from `cedar_uid`
(`docs/CEDAR_BUSINESS_ID_DECISION_2026-09-06.md` and ADR-043, at the tag `data-workspace-final`;
the current model is `docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md` §2). `CE-` keeps
meaning the canonical Native institution; `CB-` names a distinct commercial
business, whoever owns it. The id encodes nothing, never changes, and is
never traded for a uid except by an adjudication that keeps both. Ownership
is a dated relationship, registrations are attributes, name changes are
aliases, and successors get new ids. Minting the register is Lumecon-data's
job (handed over when the data workspace was retired), seeded from the NEED
enterprises, the certified-firm directories, the contracting awardees and the
deal parties. Nothing mints a `CB-` yet. This repository checks only the
form: the vendored customer-table rules (`server/cedar_press/customer_sheet.py`,
`CEDAR_ID`) accept `CB-` and seven digits as a Cedar Business ID, and the NEED
customer table has a `business_uid` column for it, blank until a register
binds one.

## The public dataset specification

The owner's specification of 2026-09-05 for the customer files
(`docs/PUBLIC_DATASET_SPEC_2026-09-05.md`, at the tag `data-workspace-final`)
set an exact public column list for each flagship and a rule retiring the
competing entity identifiers. Its field-by-field map stays, and this
repository reads it.

THE FIELD MAP. `data/cedar/field_map.json` holds, per flagship, one decision
per column, the approved public header in order (`order`, and
`compatible_orders` for a newer release's column set), the default viewer
columns and a retirement entry for every competing identifier. The API lists
a Grove collection's components from its keys (`repository.grove_components`),
serves a full release only when the release's header matches an entry's
`order` or one of its `compatible_orders` and its rights classes agree with
the pinned contract, and takes a flagship's column order for the researcher
spreadsheet from it (`spreadsheet.py`). The staging script
(`scripts/stage_verified_previews.py`) and `scripts/preview_definitions.py`
read it when they build preview definitions.
The two review documents once rendered from it (`FIELD_MAP_2026-09-05.md`
and `IDENTIFIER_RETIREMENT_2026-09-05.md`) are at the tag
`data-workspace-final`. `explore.test.js` holds the map, the codebook and the
samples together.

The retired writer that generated each customer header from the map
(`code/cedar_publication.apply_field_map`, called by
`code/1137_customer_dataset_combine.py`) is at the tag; customer tables are now
built in Lumecon-data and rendered here by the vendored rules in
`server/cedar_press/customer_sheet.py`.

THE CODEBOOK. `data/cedar/codebook.json` is the dictionary of the producer
previews' columns. The viewer describes each collection by its customer table:
`codebookFor` (`explore.js`) takes the header and grain from
`data/cedar/sample_downloads.json` and each column's meaning from the codebook,
or from `customerTables.js` for the columns the customer-table rules add or
rename.

THE VIEWER READS BOTH SHAPES. A list cell may be pipe-separated (the
samples today) or a JSON array (the approved schema); `listCell` reads
both, so a row's entities, the filters, the facets and the record work
before and after the export changes. A contract may declare
`entity_roles`, the table's further entity columns with the role each
carries, and `rowEntities` unions them into the row's entities with the
role on each, so an entity filter finds a row through any supported role
and never only the first displayed uid.

THE GUIDES. `scripts/docs-markdown.mjs --kind guides` writes one researcher guide per
collection into `docs/guides/` from `data/cedar/guides.json` (the prose),
the collection descriptor (purpose, sources, method), the field map (row
unit, roles, approved header, what is owed, the retirement findings that
stop the dataset) and the codebook (the field dictionary, with data types
read off the sample and what a blank means). A collection with an installed
producer release is described by its download instead: the download's header,
grain and column meanings as the site's reader shows them, with types read off
the sample download. Every figure in the prose is
quoted from a repository document named beside it; the finished public
table is re-measured at release, which nothing here can do.

## Shape the Research

A Cedar Press subscription earns Cedar Points for using the product and
spends them on what Cedar should research or build next. The rule and the
ledger are `server/cedar_press/priorities.py`; the endpoints are in `app.py`
(`/press/priorities`, `/press/priorities/related`, `/press/influence`,
`/press/priorities/{id}/points`, `/press/requests`); the client is
`features/grove/pressPriorities.js` (the seed, the words, the same
related-priority search), `features/grove/usePriorities.js` (the reads),
`pages/grove/CedarPressPriorities.jsx` (the page), `pages/grove/PressInfluence.jsx`
(the profile's card) and `pages/grove/PressPrioritiesBlock.jsx` (the homepage).

THE RULE. The SUBSCRIPTION (not each seat) earns points once per calendar
month, the first time anyone on it signs in that month: Cedar Press 1, Cedar
Press+ 2. The unique index on (account, month) is what makes a refresh, a
sign-out and back, or forty sessions credit nothing more. Points expire
twelve months after the month they were earned if unspent, oldest spent
first. A subscriber puts points on priorities in any amounts and takes them
back; every priority shows its points and how many subscriptions put them
there. Points inform; feasibility, data quality, research value and Cedar's
editorial judgment sit beside them, and the copy says so.

THE LEDGER IS APPEND-ONLY: `research_points_ledger` rows say why every point
came or went (`monthly_activity`, `allocation`, `refund`, `expiration`);
`priority_allocations` is derived for the totals; `research_requests` keeps
a subscriber's own words beside the priority they read as related, with the
stated use, so Cedar sees behind a priority the points, the subscriptions and
the requests. Two seats naming one `account` in `CEDAR_PRESS_ACCOUNTS` share
one ledger.

THE PRIORITIES ARE THE OWNER'S: `data/cedar/priorities.json` (force-added)
holds the titles, descriptions, types (research question or dataset),
statuses (interest, under review, research underway, data construction
underway, published), what got published and what evolved from what. The
service re-seeds those fields on start and never writes them; counts live
only in the ledger. The store is SQLite through the standard library, at
`CEDAR_PRESS_DB` (in memory when unset, which a deployment must not leave).

WITHOUT THE SERVICE the page lists the seeded priorities with no counts and
says the counting begins with the service; nothing counts a point on the
client, and a build without the service never shows a zero that means
"unknown".

## Interface conventions

- **Both pointers.** Hover affordances have tap equivalents: on a coarse
  pointer the shelf's first tap opens the collection's description and the
  download moves into that panel.
- **Themes.** The press pages have one palette, the light one, and nothing
  sets a dark theme, so the document declares `color-scheme: light`.
- **Reveals.** Sections arrive on scroll through `useReveal`; anything behind
  one must still be present for a reader who does not scroll it.
- **Accessibility.** A skip link opens every page and lands on its `main`;
  one focus ring covers every control and inverts on the teal panels, where a
  dark ring is invisible; headings descend by one; text clears WCAG AA
  contrast; the methods diagram is a group of buttons rather than an image.
  Motion — the page's arrival rise and the tile hover — collapses entirely
  under `prefers-reduced-motion`, not merely shortens. Checked with axe
  against every route at desktop and phone widths.
