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
shelf, and [Cedar Grove](https://lumecon.ai) carries the same collections into
the full analysis environment. Tribal Business News owns payment, renewals and
issuance.

## Working on it

The subscriber-facing web client is a [Vite](https://vite.dev) + React
application deployed as a static build, with a Python API alongside it.

```sh
npm install
npm run dev        # development server
npm run test       # unit tests
npm run test:smoke # end-to-end checks against a build
npm run build      # production build
```

[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) covers how the code is
organized, how the client and the API fit together, and how to run the API.
[`.env.example`](.env.example) lists every configuration value.

## Security

Please report vulnerabilities as described in [SECURITY.md](SECURITY.md).

## Contact

[contact@lumecon.ai](mailto:contact@lumecon.ai)
