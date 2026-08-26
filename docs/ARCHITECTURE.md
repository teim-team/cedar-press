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

## Access

`features/grove/pressAccess.js` resolves a session's tier to what the client
renders — which shelves open, which collections download. The session
provider in `src/context/` is the integration point for the platform's
authentication; `api.js` holds the client for the subscriber endpoints.
Entitlement is authoritative on the server, and the client model is written
to answer identically.

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
- **Demonstration content.** Where fixtures stand in for material that has not
  published, the interface says so on the item itself rather than in a
  disclaimer far from it.
