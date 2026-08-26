# Cedar Press

**Trusted intelligence for Indian Country.** Cedar Press is a subscriber
intelligence service: original economic collections, data-driven research and
transparent method, covering the money, policy, transactions, institutions and
public actions that shape Indian Country's economy.

Built by [Lumecon](https://lumecon.ai). Available exclusively through
[Tribal Business News](https://tribalbusinessnews.com). Served at
[cedarpress.ai](https://cedarpress.ai).

## The service

| Section | What it holds |
| --- | --- |
| Overview | The service at a glance, with each section's current standing. |
| Articles | Data Briefs: original research built from the collections. |
| Data | The collections themselves — coverage, method and the release. |
| What's new | Every release, dated and versioned, for tracing a cited figure. |
| Methods | How collections are sourced, resolved and kept current. |

Alongside these, `/tribal-data-request` carries the tribal data request
policy and `/research-access` the limited research access path — each on its
own URL, so either can be sent to a council office or a researcher directly.

Access follows the subscription: the Cedar Press tier arrives with a Tribal
Business News membership, Cedar Press+ adds the deeper shelf, and Cedar Grove
carries the same collections into the full analysis environment.

## This repository

The subscriber-facing web client: a [Vite](https://vite.dev) + React
application, deployed as a static build. It shares its design tokens, figure
specs and collection models with the Lumecon platform, so what a subscriber
reads here cannot drift from what the platform renders. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how the code is organized.

```sh
npm install
npm run dev      # development server
npm run test     # unit tests (node --test)
npm run build    # production build into dist/
```

### Configuration

The client runs in two modes, and knows which one it is in rather than
inferring it from a failed request:

| Mode | When | Behavior |
| --- | --- | --- |
| Connected | `VITE_API_URL` is set | Sessions, catalog, releases, downloads, subscriber datasets and Cedar come from the platform API; the database behind it is the source of truth. |
| Standalone | No API configured | The bundled catalog is served so the service can be demonstrated and reviewed on its own. Anything that would write to the database stays in the browser, and the interface says so. |

Datadog RUM reports errors, performance and a small set of product events
when `VITE_DATADOG_APPLICATION_ID` and `VITE_DATADOG_CLIENT_TOKEN` are both
set; nothing is sent otherwise. See [`.env.example`](.env.example) for every
value.

## Deployment

Pushes to `main` build and deploy to GitHub Pages via
[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml). The custom
domain is set in `public/CNAME`, and the build emits `404.html` alongside
`index.html` so client-side routes resolve.

## Security

Please report vulnerabilities as described in [SECURITY.md](SECURITY.md).

## Contact

[contact@lumecon.ai](mailto:contact@lumecon.ai)
