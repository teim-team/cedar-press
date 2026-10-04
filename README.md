# Cedar Press

**Trusted intelligence for Indian Country.** Cedar Press is a Lumecon research
publication, partnered with Tribal Business News: original economic
collections, data-driven research and
transparent method, covering the money, policy, transactions, institutions and
public actions that shape Indian Country's economy.

Built by [Lumecon](https://lumecon.ai). Available exclusively through
[Tribal Business News](https://tribalbusinessnews.com). Served at
[cedarpress.ai](https://cedarpress.ai).

## The service

Registered Native entity profiles use the same pinned, verified collection releases as
downloads. NEED records remain named related records, without a separate public
profile. Patent observations and ratings attach to the exact legal owner or issuer:
a registered entity, its evidenced NEED counterpart, or a related enterprise.
Showing a related record does not transfer its facts to the parent. NEED has no
publication hold: NEED records come from publicly available websites and Lumecon has
permission to publish them (owner ruling 2026-10-04), so the endpoint serves the
pinned release.
The authenticated evidence endpoint is
`GET /press/entities/{cedar_uid}/need-evidence`. The entity register is internal
infrastructure and is not an additional customer collection.
NEED keeps its existing Press+ and Grove access. Its component declarations
describe the producer's logical tables, including bounded partitions; they do
not grant publication rights or add another collection to the fifteen targets.

The Grove application in `teim-team/teim-app` can use
`python -m cedar_press.grove_exchange` as a local process interface after resolving
its authenticated account and sponsorship. Version 1 accepts bounded JSON on
stdin for discovery, registered entity evidence and downloads. It calls the same
release consumer and publication gates as the Press API. Completed downloads go
to the caller's private `CEDAR_GROVE_EXCHANGE_DIRECTORY`; stdout carries metadata
only. The caller must pin this checkout, verify its commit, stream the completed
file and remove its own temporary directory. This interface does not issue a
session or authenticate a browser request.

| Section | What it holds |
| --- | --- |
| Overview | The service at a glance, with each section's current standing. |
| Articles | Research Briefs: original research built from the collections. |
| Data | The collections themselves — coverage, method and the release. |
| What's new | Every release, dated and versioned, for tracing a cited figure. |
| Methods | How collections are sourced, resolved and kept current. |

Alongside these, `/tribal-data-request` carries the tribal data request
policy and `/research-access` the limited research access path — each on its
own URL, so either can be sent to a council office or a researcher directly.

## The collections

Fourteen collections, built and verified in `Lumecon-data` and served here as
pinned releases. The counts below are the permitted observations in each
collection's current producer spreadsheet, read from
`data/cedar/collections.manifest.json` on 2026-10-02; they are mixed-grain
observation counts, not counts of unique people, businesses, awards or dollars,
and the collections must not be added together. Every collection was Updated
2026-10-01. The datasets are maintained with human review; the cadence is a
promise, not yet a measured interval.

| Collection | Shelf | Observations | One row is |
| --- | --- | ---: | --- |
| Federal Funding to Indian Country | Cedar Press | 640,942 | one federal assistance transaction |
| Federal Register — Indian Affairs | Cedar Press | 21,258 | one consultation participant row or one federal action |
| Native Legislation and Votes | Cedar Press | 3,064 | one bill with its recorded votes |
| Indian Country Deals | Cedar Press | 978 | one source-described deal or milestone |
| NAGPRA Notices | Cedar Press | 6,792 | one Federal Register NAGPRA notice |
| Native Federal Advocacy and Engagement | Cedar Press | 27,825 | one entity-linked activity or source record |
| Foundation & Corporate Giving | Cedar Press | 193 | one disclosure or award version |
| Native Federal Contractors | Cedar Press+ | 841,002 | one prime contract transaction |
| Native Federal Subcontracting | Cedar Press+ | 70,054 | one subaward filing |
| Individual Native-Owned Businesses | Cedar Press+ | 3,725 | one directory or certification listing |
| Cedar Native Entity Enterprise Dataset (NEED) | Cedar Press+ | 43 | one reviewed enterprise in the public base |
| Tribal Natural Resource Revenue | Cedar Press+ | 11,120 | one revenue event as its source reports it |
| Native Nonprofits | Cedar Press+ | 89 | one organization (EIN) |
| PLOT | Cedar Press+ | 151,715 | one tract, parcel, permit or environmental observation |

Cedar Press carries the first seven; Cedar Press+ adds the other seven at the
same depth. Each collection's grain, keys, field dictionary, missing-value
rules, units and citation are in its researcher guide under
[`docs/guides/`](docs/guides/README.md), regenerated from the release manifest
and the served preview by `node scripts/docs-markdown.mjs --kind guides`.
The public preview of each collection is ten rows
(`public/data/cedar/samples/<collection>/spreadsheet__10.csv`), byte-identical
to the producer's pinned sample; a preview describes itself, not the full
spreadsheet. Gaming and Native Infrastructure are Cedar Grove collections and
are not sold or previewed here.

### Where the data comes from

Every collection is built on publicly available primary sources, extended
through original research and entity resolution, and each row carries its
source link. In brief: USAspending and the FAADS archives (funding, prime
contracting, subcontracting); federalregister.gov and govinfo (Federal
Register, NAGPRA); Congress.gov and Voteview (legislation); Senate and House
lobbying disclosure, agency dockets and IRS Form 990 Schedule C (advocacy);
tribal and enterprise announcements, lender and counsel releases and ANCSA
shareholder filings (deals); tribal TERO and licensing registers published by
each nation (Native-owned businesses); audited ANCSA filings and owners' own
enterprise registers (NEED); ONRR, MMS, OSMRE and Osage Minerals Council
records (natural resources); the IRS Business Master File and 990 filings
(nonprofits); first-party donation reports and public foundation, corporate
and bank disclosures (giving); BIA tract maps, the Wisconsin statewide parcel
layer, local permit feeds and EPA regulatory records (PLOT). The full source
statement per collection is the `sources` field of its manifest descriptor,
and the row-level `source_url` is the citation for any single record.

### How to cite

Cite a collection by its name and Updated date, never by a version label or a
file or table count. This is the sentence every download carries:

```
Lumecon, "<Collection name>", Cedar Press collection, cedarpress.ai. Updated <YYYY-MM-DD>. Accessed <YYYY-MM-DD>.
```

For a row-specific claim add the record type and record key, and the exact
release identifier from the collection's guide when a reviewer must reproduce
the file.

### What is not claimed

- A Cedar entity link (`cedar_uid`) is an association in the stated role. It
  does not establish ownership, Native status or a party's share, and a blank
  link is never a finding that no Native entity is involved.
- Observation counts are not totals. Grains overlap, obligations and award
  values are different measures, and a subaward is a slice of a prime award.
- Previews are excerpts, not samples in the statistical sense, and a column
  blank in a preview says nothing about its coverage in the spreadsheet.
- Cadence is a commitment, not a measured interval; no vintage is stated for
  any collection because none has been measured.
- IMPLAN, where it is used elsewhere in the Cedar products, is a benchmark to
  measure agreement with, not ground truth.

The most recent structural fact-check of the served previews, the spine and
the public text is [`docs/FACT_CHECK_2026-10-02.md`](docs/FACT_CHECK_2026-10-02.md);
`python3 server/tests/test_public_preview_audit.py --report` reproduces its measurements, and `make test-python` keeps its invariants firing.
Its section 8 records what was then fixed at source on 2026-10-02: the register spelling
of two ANCSA names (source renderings kept as aliases in `data/spine/cedar_entity_name_aliases.csv`),
the Native nonprofit count, the subcontracting flag rule, and two definitions. One
reader-visible definition changed: `ownership_percent` in Individual Native-Owned Businesses is the
share owned by the certifying tribe's members as the certifier reports it, not the Native
ownership share overall, so a certified Native-owned firm can read `0.0` there.

## Access

Subscriber plans are handled on the Tribal Business News side. An eligible
membership issues an access code, and the code establishes the entitlement and
the account; Tribal Business News owns payment, renewals and issuance. Cedar
Press has no year gating: every subscriber gets full coverage, and no plan
changes how far back a collection goes.

Separately, [Cedar Grove](https://lumecon.ai/cedar-grove), which Lumecon runs
in `teim-app`, carries the same collections into the full analysis
environment.

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

Checked 2026-10-02 on Linux, Node 22, Python 3.11: `npm run lint` clean;
`make check-generated` current; `npm run test` 634 pass, 0 fail, 1 skipped,
coverage 88.64 lines / 85.00 branches / 90.80 functions, floors met;
`ruff check server` clean; `make test-python` ran 664 tests with 33 skipped
and 85% coverage against the 77 floor, with five import errors and one
failure that are Python 3.11 artifacts (`code/` scripts use 3.12 f-string
syntax, and the writer census parses them), so the hosted run on Python 3.12
is the record for that suite; `npm run build` completes (the chunk-size
warning is pre-existing); `make audit-node` and `make audit-python` report no
known vulnerabilities. `npm run test:smoke` was not rerun; the hosted Checks
run covers it. The full list of checks CI runs, with how to run the API
suite, is [`AGENTS.md`](AGENTS.md) §3.

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
behind Cedar Impact, internal), [`cedar`](https://github.com/teim-team/cedar)
(Cedar, Lumecon's AI economic analyst, as a service),
[`lumecon-website`](https://github.com/teim-team/lumecon-website) (the
public site and the reference for product vocabulary) and
[`Lumecon-data`](https://github.com/teim-team/Lumecon-data) (the shared
Python data foundation behind Cedar Press, Cedar Grove, Cedar and Cedar
Impact). `Lumecon-data` is the separate data repository the team decided on
2026-09-21 for extraction and harmonization; it exists as of 2026-09-23, and
the pipeline in `code/` is still here. Product names and
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

This repository retains the historical Cedar data workspace, merged on 2026-09-02.
Current versioned releases and researcher spreadsheets are built in Lumecon-data;
Press consumes explicit release pins. Use these entry points:

| | |
|---|---|
| Consumer continuation | [`docs/TERMINAL_HANDOFF.md`](docs/TERMINAL_HANDOFF.md): current workflow, maintained authorities and archived checkpoints. |
| Historical workspace orientation | [`START_HERE.md`](START_HERE.md); its dated counts and assignments are not current release evidence. |
| Rules for agents working in it | [`AGENTS.md`](AGENTS.md) |
| Current release evidence | [Producer convergence checkpoint](https://github.com/teim-team/Lumecon-data/blob/codex/convergence-packet-guard-20260928/docs/cedar-convergence.md) and its linked dependency ledger. The older [`DATASET_READINESS.md`](docs/DATASET_READINESS.md) and [`TWELVE_DATASET_PLAN.md`](docs/TWELVE_DATASET_PLAN.md) describe the historical workspace. |
| Past handoffs, kept as records | [`docs/handoffs/`](docs/handoffs/); each carries a banner saying what superseded it |
| The dataset plans and the v2 spec | [`docs/plans/`](docs/plans/) |
| Measured map of the collections | [`docs/DATA_ARCHITECTURE.md`](docs/DATA_ARCHITECTURE.md) |
| Historical combined deliverables | `dist/customer/` preserves workspace CSVs, codebooks and notes; it is not the connected release authority. |
| Build current researcher deliverables | The producer's installed `lumecon-data spreadsheet` command with explicit store, collection and release pins; see the [spreadsheet guide](https://github.com/teim-team/Lumecon-data/blob/codex/convergence-packet-guard-20260928/README.md#one-living-dataset-one-spreadsheet). The Press API consumes those verified releases. |
| Historical workspace reproduction | `code/1137_customer_dataset_combine.py` and `code/846_session_audit.py` retain their original scopes and safety gates. Their prior results are historical evidence, not current release acceptance. |

`py -3` is the Windows launcher; on Linux and macOS use `python3`, which
must be 3.12 or later (some scripts, `code/1137_customer_dataset_combine.py`
among them, use 3.12 f-string syntax and do not compile under 3.11).

The two trees were developed independently and share no history; the merge that
brought them together is a deliberate `--allow-unrelated-histories` join, and
only three paths collided. `docs/ARCHITECTURE.md` describes the **web client**;
`docs/DATA_ARCHITECTURE.md` is the generated map of the **data collections**.

Source cards in previews and record pages distinguish the original publisher,
registered dataset title, event description and original source link. Missing
publisher or document evidence stays explicit. The shared source labels are
projected from Lumecon-data intake with `python -m lumecon_data.source_presentation
--profiles intake/profiles --collection foundation-corporate-giving --collection
federal-register --output <cedar-checkout>/data/cedar/source_display.json`.
This projection does not clear records or establish acquisition hashes. Local
source paths and ingest filenames remain outside displayed citation labels.

Giving declarations append recipient state, source locator and award-family
evidence. The earlier exact 27-column schema remains explicitly supported for
pinned rollback; undeclared extra columns still refuse delivery.

## Living datasets and the researcher spreadsheet

Public labels and citations use the collection name and its recorded Updated date. Version labels and internal file/table counts are not product descriptions or source counts. The authenticated spreadsheet-download route returns one CSV per collection through the same pinned, rights-checked download verifier. Existing component routes remain internal compatibility interfaces. Compatible columns align; conflicting definitions or units stay separate until reviewed, and record type/key/grain prevent accidental aggregation across observations. Preview extracts remain explicitly labeled as samples.

Rebuild and inspect the real collection exports in the data workspace before publication. Review conflicting column definitions, duplicate keys, missing values and original-source provenance. Agents do not impose publication holds (owner ruling 2026-10-04). The code change itself does not rebuild the external data store or deploy the service.

## Presentation maintenance

[Press and Grove presentation data flow](docs/PRESENTATION_DATA_FLOW.md) is the maintained guide to public sample counts, connected release counts, shared reader labels and the export/codebook review boundary. Historical handoffs keep their dated measurements; avoid copying those counts into the current product.
