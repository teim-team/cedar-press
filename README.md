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

Every collection begins with public records, is extended through original
research and entity resolution, and stays current as new information arrives.
Every download carries its own citation, so a figure can be traced back to the
release it came from.

## Access

Access follows the subscription. An eligible Tribal Business News membership
issues an access code, the code establishes the entitlement, and the account
follows: Cedar Press arrives with a membership, Cedar Press+ adds the deeper
shelf, and [Cedar Grove](https://lumecon.ai/cedar-grove) carries the same collections into
the full analysis environment. Tribal Business News owns payment, renewals and
issuance.

## Working on it

The subscriber-facing web client is a [Vite](https://vite.dev) + React
application deployed as a static build, with a Python API alongside it.

```sh
npm install
npm run dev        # development server
npm run test       # unit tests
npm run test:smoke # end-to-end checks against a build (prerendered, as deployed)
npm run build      # production build
npm run build:site # the build, then the three public pages prerendered to HTML
npm run seo:check  # the structured data and sitemap are current with the catalog
```

The API is a FastAPI service in [`server/`](server/README.md); it serves every
route the client calls, and pointing `VITE_API_URL` at it is the whole switch
from the standalone build to a connected one.

[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) covers how the code is
organized, how the client and the API fit together, and how to run the API.
[`.env.example`](.env.example) lists every configuration value.

## Where this fits

Cedar Press is one of Lumecon's Cedar products and is deliberately
unannounced on [lumecon.ai](https://lumecon.ai): it reaches readers through
Tribal Business News, and the site's own rules keep the name out of anything
a visitor or crawler can reach. The sibling repositories are
[`teim-app`](https://github.com/teim-team/teim-app) (the authenticated
platform: Cedar Impact, Cedar Commons and Cedar Grove),
[`teim-engine`](https://github.com/teim-team/teim-engine) (the model engine
behind Cedar Impact), [`cedar`](https://github.com/teim-team/cedar) (Cedar,
the AI economic analyst, as a service) and
[`lumecon-website`](https://github.com/teim-team/lumecon-website) (the
public site and the reference for product vocabulary). Product names and
their one-line definitions follow the website's `AGENTS.md`, which is the
North Star: where this repository and the website disagree about what
something is called, the website wins. The vocabulary rule that matters most
here is that Cedar Grove is "the living evidence base for your organization's
economy" (owner ruling 2026-09-13, replacing "the advanced data library"). The
shared tier catalog in `src/workspaceTier.js` uses that definition.

The Lumecon copy rules apply to every string a reader can see in the client.
The three that catch people out:

- **No ampersands.** Write "and", never "&". **Grep for both forms**, because
  each misses the other: it has leaked as `&amp;` in JSX text, which a search
  for a bare `&` does not match, and as a plain `&` inside a string literal,
  which a search for the entity does not match. A regex that catches both:
  `&amp;|[A-Za-z0-9] & [A-Za-z0-9]`. Worth checking the visible label against
  its own `aria-label` too: one occurrence had "Requests and support" in the
  label and "Requests &amp; support" on screen.
  The one collection name that carried an ampersand, the lobbying collection,
  was renamed to `Native Federal Advocacy and Engagement` on 2026-09-18. Its
  name is embedded verbatim in the citation written into every downloaded CSV,
  so six sources had to move together: the manifest, the storefront catalog, the
  codebook, the descriptors, the release ledger and the prerendered HTML, with
  `server/cedar_press/_press_data.json` regenerated from the catalog.
  `pressReleases.test.js` fails if the ledger and the manifest disagree, which is
  what catches a half-done rename.
- **No em dashes in prose a reader sees.** A `—` standing in for an empty
  table cell is typography, not prose, and is fine.
- **Cedar is the AI economic analyst**, never an "AI assistant".

`.teim-rd` is a CSS class root inherited from the product's design system. It
is a contract, not a label anyone reads; leave it alone.

## Security

Please report vulnerabilities as described in [SECURITY.md](SECURITY.md).

## Contact

[contact@lumecon.ai](mailto:contact@lumecon.ai)

## The data workspace

This repository also contains the Cedar data workspace, merged on 2026-09-02.
It has its own entry points and its own conventions:

| | |
|---|---|
| **What the site needs from the workspace** | [`docs/TERMINAL_HANDOFF.md`](docs/TERMINAL_HANDOFF.md) — read this after every pull. One table of open items, and the tests that fail when the workspace moves under a published claim. |
| Start here | [`START_HERE.md`](START_HERE.md) |
| Rules for agents working in it | [`AGENTS.md`](AGENTS.md) |
| Current state of the datasets | [`docs/DATASET_READINESS.md`](docs/DATASET_READINESS.md) (regenerate: `py -3 code/518_dataset_readiness.py`) and [`docs/TWELVE_DATASET_PLAN.md`](docs/TWELVE_DATASET_PLAN.md) |
| Past handoffs, kept as records | [`docs/handoffs/`](docs/handoffs/); each carries a banner saying what superseded it |
| The dataset plans and the v2 spec | [`docs/plans/`](docs/plans/) |
| Measured map of the collections | [`docs/DATA_ARCHITECTURE.md`](docs/DATA_ARCHITECTURE.md) |
| The thirteen built datasets | `dist/customer/` (CSV + codebook + notes) |
| Rebuild the deliverables | `py -3 code/1137_customer_dataset_combine.py build` |
| Audit | `py -3 code/846_session_audit.py` |

The two trees were developed independently and share no history; the merge that
brought them together is a deliberate `--allow-unrelated-histories` join, and
only three paths collided. `docs/ARCHITECTURE.md` describes the **web client**;
`docs/DATA_ARCHITECTURE.md` is the generated map of the **data collections**.
