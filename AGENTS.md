# AGENTS.md — Native Deals & Native Entity Enterprise Data Project

## Owner adjudication boundary (Elijah, 2026-09-24)

Round-half-away-from-zero is ratified and Claude owns its implementation. Codex must not perform rounding work or edit Claude-owned changes; Havala reviews implementation. Elijah's menu contains only fully researched, genuinely ambiguous identity, affiliation or legal-object linkages. Do not expose receipt commands, schemas, engineering holds, optional history checks or unresolved research. Codex handles imports after an export is returned. When nothing qualifies, display exactly **No owner decisions ready** and continue independent work.


Elijah is only reviewing genuinely ambiguous identity, affiliation, or legal-object linkages where human judgment is required. Never place code defects, schemas, missing fields, tests, source refreshes, documentation, infrastructure, or other engineering work in his adjudication queue. Codex is a frontier coding model and must diagnose and fix those issues itself, validate the fix, and keep working. Only escalate when the repository and available authoritative sources cannot determine a linkage or when an actual product-policy choice belongs to the owner. A queue that asks Elijah to resolve engineering problems is a failed deliverable.

*Operating guide for AI-agent sessions. This repository is Havala Hanson's (§5); the owner rulings below are Elijah Moreno's. Trimmed to its operating sections on 2026-10-12.*

---

## Owner ruling on publication holds (Elijah Moreno, 2026-10-04) — supersedes every earlier hold

**Owner ruling 2026-10-04 (Elijah Moreno): Lumecon decides what is blocked. The only hold is a specific record flagged as attributed to the wrong entity; records in the database have already been reviewed and sourced and are not held. Attribution review is an ongoing process, not a standing hold. Agents do not impose publication holds.**

**Owner ruling 2026-10-04 (Elijah Moreno), on rights: Lumecon transforms the data it publishes; source rights statuses are recorded as provenance and do not block publication.**

Also: NEED records and individual Native-owned business records come from publicly
available websites, and Lumecon has permission to publish them. Neither collection
carries a collection-wide publication hold. **Do not reinstate one without a new
owner ruling.**

This supersedes every instruction that tells an agent to hold, withhold,
quarantine, keep internal or not publish data or a collection pending review,
consent, preview, contested status or a publication class, including those in
this file's former journal, `START_HERE.md`, `docs/` and `review/` (all at the
tag `data-workspace-final`); where one reads as a standing hold, or as a licence
or source term that blocks publication, this ruling wins. What stays out of published
output: proprietary identifiers and a private individual's personal data (`NEVER`
columns). Owner correction 2026-10-04 (Elijah Moreno): "Dataset and public
registry identifiers stay; only proprietary identifiers (DUNS, Casino City) are
removed." So DUNS numbers and Casino City identifiers and content (Casino City is
not published at all; the customer-table rules in `server/cedar_press/customer_sheet.py`,
vendored from Lumecon-data, drop Casino City columns beside the DUNS columns) stay out, and every other identifier that
comes with a dataset (lobbying, deal, disclosure, award and event IDs, UEI, CAGE,
EIN and the like) stays in. The one record-level hold is a specific record ruled to be
attributed to the wrong entity (the mask was in `code/cedar_publication.py`, kept at the
tag `data-workspace-final`). Accuracy
rules about how a figure may be totalled or described, and duplicate filings
collapsed to one record, are correctness rules, not exclusions. What was lifted is
in the former journal's 2026-10-04 entry, at the tag `data-workspace-final`.

## 1. What this repo owns

This repository holds the subscriber-facing service. From 2026-09-02, when the
two were joined with `--allow-unrelated-histories`, until 2026-10-12 it also
held the Cedar data workspace, described below.

**The subscriber-facing service.** Cedar Press at cedarpress.ai: a Vite + React
static client with a FastAPI service alongside it, serving the Overview,
Collections, Research Briefs, Priorities, What's new and Methods, plus
`/tribal-data-request` and `/research-access` on their own URLs. Cedar Press is a Lumecon research publication, partnered
with Tribal Business News: built by Lumecon and available exclusively through
Tribal Business News, which handles subscriber plans (payment, renewals and
issuance). There is no year gating: every subscriber gets full coverage.

**The former Cedar data workspace.** Its historical acquisition, adjudication and
reproduction scripts left the tree and are kept in git history at the tag
`data-workspace-final`, with the build logs and evidence that were in `docs/`. Current versioned release builds and researcher spreadsheets
are maintained in Lumecon-data. Press owns the shared consumer, publication
filters and customer presentation. The journal that recorded it is at the same tag.

**Does not own:**

- Subscriber plans: payment, renewals and access-code issuance. Those belong
  to Tribal Business News, whose involvement is with Cedar Press only.
- The shared data foundation. That is
  [`Lumecon-data`](https://github.com/teim-team/Lumecon-data), the separate
  data repository decided on 2026-09-21. Its installed builders and spreadsheet
  exporter now own current pinned releases. The historical scripts that were
  under `code/` remain available, for their documented reproduction and
  adjudication roles, in git history at the tag `data-workspace-final`.
- The economic model. That is `teim-engine`, whose reference data the former
  workspace read under ADR-044 `reference_dataset` treatment (pinned,
  checksummed, versioned, never `data_snapshot`). Nothing in this tree reads it.
- Product vocabulary and brand copy. That is `lumecon-website`, the North Star:
  where this repository and that one disagree about what something is called,
  that one wins.
- The analysis environment. Cedar Grove carries these same collections into it,
  and lives in `teim-app`.

## 2. Stack and entry points

| Tree | Stack | Entry points |
|---|---|---|
| Web client | Vite + React, deployed as a static build | `npm run dev`; `src/` |
| API | FastAPI, Python | `server/` — see [`server/README.md`](server/README.md) |
| Former data workspace | Historical Python scripts, numbered | Not in the tree: `code/<n>_*.py`, with `code/archive/` (18 unreferenced scripts moved there 2026-10-02), are at the tag `data-workspace-final`. Current release entrypoints are linked from [`docs/TERMINAL_HANDOFF.md`](docs/TERMINAL_HANDOFF.md). |

Pointing `VITE_API_URL` at the API is the whole switch from the standalone build
to a connected one. [`.env.example`](.env.example) lists every configuration
value. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) describes the **web
client**. The generated map of the former workspace's **data collections**,
`docs/DATA_ARCHITECTURE.md`, is at the tag `data-workspace-final` with the
scripts that wrote it.

`.teim-rd` is a CSS class root inherited from the product's design system. It is
a contract, not a label anyone reads; leave it alone.

## 3. Setup and checks

Node 22 and Python 3.12, the versions CI uses. Two tools have to be installed
by hand: `uv`, which `make audit-python` uses to resolve the server's
dependencies (CI takes it from `astral-sh/setup-uv`), and `pre-commit`, which
only `make hooks` needs (CI does not run it):

<!-- gate:setup -->
```bash
pip install uv pre-commit
```

The checks CI runs, in order. This block is every `run:` step of `ci.yml`,
step for step, installs included, so it can be pasted into a fresh checkout
and run as it stands; `gateCopies.test.js` fails if it and the workflow
differ, and `deployGates.test.js` holds `deploy.yml` to `ci.yml`:

<!-- gate:ci-steps -->
```bash
npm ci
npm run lint
make check-generated
npm run test
npx playwright install --with-deps chromium
npm run test:smoke
pip install -e server[dev] httpx2 coverage pip-audit
ruff check server
make test-python
make audit-python
make audit-node
```

`make check` runs all of it bar the Playwright pair (lint, the generated
files, both suites with their coverage floors, both audits); the audits need
the network. `npm run test` is the node suite under
`scripts/coverage-gate.mjs`, whose floor counts every production module,
including the ones no test imports. `make test-python` runs the API suite
with warnings as errors and the `.coveragerc` floor, from the repository
root: its `-s server/tests -t server` is why a bare
`python -m unittest discover` from the root fails with `Start directory is not
importable` (`tests/` at the root is the Playwright smoke directory, not a
Python package).

**Verified 2026-10-14** (Linux, Node 22, Python 3.12, at `main` commit
`78a80e3`), in the order above: `npm run lint` exits `0` · `make
check-generated` reports every generator current · `npm run test` reports
`704 pass, 0 fail, 1 skipped` and a coverage floor met at 89.43 lines / 85.51
branches / 91.53 functions · `npm run test:smoke` reports 310 passed, 42
skipped · `ruff check server` reports `All checks passed!` · `make
test-python` reports `Ran 599 tests`, 36 skipped, 84% coverage against the 77
floor · `make audit-python` and `make audit-node` report no known
vulnerabilities · `npm run build` completes.

**`py -3` is the Windows Python launcher.** On Linux and macOS, and in this
repository's own CI, the equivalent is `python3` (or `python`).

**The data workspace's scripts have left the tree**, `code/1050_preflight.py`
among them, and are kept at the tag `data-workspace-final`. New data work goes to
Lumecon-data.

`npm run test:smoke` needs Playwright's browsers, which
`npx playwright install --with-deps chromium` installs once. It **builds as
well as tests**: `playwright.config.js` starts the server with `npm run build`
configured with a throwaway demo account, which is why the deployed build is
the last step of the CI job and not this one.

## 4. Branch, commit and review conventions

- **Branch from `main`** (this repo's default). Agent work goes on
  `claude/<slug>-<id>` or `codex/<slug>`; human work uses `feat/` or `fix/`.
- Never reset, rebase or force-push a shared or pushed branch. If the branch
  already exists on the remote, check it out and build on it; to take in the
  base, merge it in.
- **An attribution trailer is a claim, so it is only ever true.** It says
  who made a commit; it is not a house style every commit wears. The test is
  who made the commit, not who wrote the lines in it.
  - **A person's commit carries no AI trailer**, including when an agent
    wrote the change with them in a session they were directing. The person
    reviewed the change and committed it, so the person is its author.
  - **A commit an agent makes on its own** (none are made while people make
    the commits; see below), for example an agent given a
    task and left to work and commit unattended, ends with exactly the two
    trailer lines its session gives it, and no other trailer of that kind:

    ```
    Co-Authored-By: Claude <model name, as the session reports it> <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_<id>
    ```

    Copy both lines from the session rather than from here: the model name
    and the session id are the session's facts, which is why this file names
    neither.
  - A Codex branch uses whatever attribution Codex itself records, and never
    a Claude line. Nobody names a co-author who did not take part or writes a
    session URL that does not exist.
  - Whoever made the commit, no model identifier appears in a PR title or
    body or in a code comment.
- Push with `git push -u origin <branch>`. Do not open a pull request unless
  you were asked to. Agents never merge.

> **Until further notice, people make the commits** (Havala Hanson, 2026-10-12).
> An agent prepares the change, runs the checks and gives commit guidance: what
> to stage and a suggested message. A person reviews the change and commits it.
> Agents do not commit, push or merge.

## 5. Who reviews what

*Ownership as set by Elijah Moreno, 2026-10-04. It supersedes the earlier table, which routed frontend to Isabella and teim-engine to Francesca.*

| Area | Owner |
|---|---|
| **Team lead; Cedar Press and Cedar Grove, including their data** | Havala Hanson (@Havala-Hanson) |
| The app users see: teim-app's interface, product behaviour and customer-facing copy | Kaylyn Lee (@kaylynhl) |
| Backend and ML outside the existing teim-app: Cedar Grove's server side, data pipelines, ML | Ari (@ArihantSwainLumecon) |
| The existing teim-app's backend: account access, payments, the database, dependencies, Datadog | Brian Kim (@bkim28964) |
| Cedar, the AI economic analyst (the `cedar` service) | Francesca Agnes (@mafranagn) |
| teim-engine | Isabella Agnes (@magnes1) |

This repository is Havala's. A change to the web client's interface also goes
to Kaylyn; a change to the pipeline or ML work goes to Ari; a change to the existing
teim-app's backend (accounts, access, payments, database, dependencies) is
Brian's wherever it lands.
None of that displaces the self-verification rule in §6 — a reviewer is not a
substitute for an independent re-execution.

## 6. Invariants

The full statement of the data rules, with the mistake each prevents, is the
rules catalogue in Lumecon-data (`docs/data-rules-catalogue.md`). The short
list, all of which this project has paid for:

- **Zero fabrication.** Never write a deal row, dollar amount, date or identifier
  that is not present in retrieved or uploaded evidence. A smaller true dataset
  always beats a larger padded one.
- **Unknown stays unknown.** Deterministically wrong metadata is worse than
  deterministically missing metadata. Every dropped row gets a NAMED reason;
  `other` / `unknown` / `misc` are refused.
- **There is no fourth status.** A dataset is READY, BLOCKED or NOT_TESTED. Not
  "mostly ready", not "effectively done".
- **A check does not count until a fixture proves it FIRES.** Inject the
  violation, exit 1, restore, exit 0, and assert the NAMED invariant fired.
- **Never re-baseline to clear a red gate.** A gate you stepped around is a gate
  the next six sessions will also step around.
- **Fix the generating pipeline, never the output CSV.**
- **Self-verification is refused.** A completion claim carries re-executable
  commands, run by a different session (the workspace's `513_handoffs.py`
  ledger is at the tag `data-workspace-final`).
- **The copy rules apply to every string a reader can see.** No em dashes in
  prose a reader sees, though a `—` standing in for an empty table cell is
  typography and is fine; and **Cedar is the AI economic analyst**, never an
  "AI assistant". Ampersands are allowed (owner ruling 2026-10-13, Elijah
  Moreno); the no-ampersand rule was retired.
- **No year gating.** Every subscriber gets full coverage; no plan changes how
  far back a collection goes. Subscriber plans are handled on the Tribal
  Business News side. The year cap that once separated the tiers was retired
  on the owner's ruling of 2026-09-02 (see the `ONE AXIS` note in
  `pressCatalog.js`).
- **A collection name is a data contract.** It is embedded verbatim in the
  citation written into every downloaded CSV, so renaming one changes how files
  subscribers already hold cite themselves. The lobbying collection's rename to
  `Native Federal Advocacy and Engagement` moved six sources together and is the
  worked example.
- **Build and write it as the shipped product.** No surface, route or copy
  describes Cedar Press as a prototype or a pilot. Something that is not real
  yet is labelled plainly for what it does today and tracked as a gap, never
  called a prototype. Pilots run as ordinary accounts or access codes, not a
  separate code path. Payment for Cedar Press is owned by Tribal Business News
  today (`server/cedar_press/codes.py`); Lumecon's side is codes and
  entitlement. Lumecon's own Stripe account, with Brian Kim and Kaylyn Lee as
  admins, carries Cedar Grove payments: teim-team/teim-app#186.

## 7. How this doc gets updated

Agents update this file as part of the work, in the same change as the work.
If you add an entry point, change a check command, move ownership, or discover
that something here is wrong, fix it here — a stale operating doc is worse than
no operating doc, because it is trusted.

**The whole file is edited in place** so it stays true. Sections 1-8 are the
shape shared across every `teim-team` repository and describe the present. The
append-only journal that used to follow them, with `START_HERE.md` and the field
guide, is at the tag `data-workspace-final`; the data rules it taught are in
Lumecon-data's `docs/data-rules-catalogue.md`.

One other place absorbs a specific kind of update, so it does not land here:
`docs/TERMINAL_HANDOFF.md` is rewritten in place and is never a journal.

## 8. Cross-repo links and status

*Current release workflow is recorded in [the maintained consumer handoff](docs/TERMINAL_HANDOFF.md), which links the producer checkpoint.*

| Repo | What it is | Relationship to this one |
|---|---|---|
| [`teim-app`](https://github.com/teim-team/teim-app) | The authenticated platform — Cedar Impact, Cedar Commons and Cedar Grove | Cedar Grove carries these collections into the full analysis environment |
| [`teim-engine`](https://github.com/teim-team/teim-engine) | The model engine behind Cedar Impact (internal) | The former workspace read its reference data as `reference_dataset` per ADR-044; nothing in this tree reads it |
| [`cedar`](https://github.com/teim-team/cedar) | Cedar, the AI economic analyst, as a service | No runtime dependency in either direction |
| [`lumecon-website`](https://github.com/teim-team/lumecon-website) | The public site, and the **North Star** for product vocabulary | Product names and their one-line definitions follow its `AGENTS.md` |
| [`Lumecon-data`](https://github.com/teim-team/Lumecon-data) | The shared Python data foundation behind Cedar Press, Cedar Grove, Cedar and Cedar Impact | Owns current versioned builders, verification and researcher spreadsheet exports. Press consumes exact pins; the historical workspace scripts are at the tag `data-workspace-final` for reproduction and adjudication. |

**Naming**, per the North Star: the impact product is **Cedar Impact**; "TEIM"
survives as a repository, database and resource name only; "tribal economic
impact" is retired as a product name; and Cedar Grove is "the living evidence
base for your organization's economy" (owner ruling 2026-09-13, replacing "the
advanced data library"). The shared tier catalog in `src/workspaceTier.js` uses
that definition.

**Open, needing a human decision:**

1. **The visibility boundary.** This product is deliberately unannounced on
   lumecon.ai, and that site's rule keeps the name out of anything a visitor or
   crawler can reach. A public GitHub repository is crawler-reachable, and this
   repository's own public `README.md` names the product and links that site.
   Either the rule means "nothing in the built site" or it means what it says.
   The two readings are inconsistent; nothing has been changed in either
   direction pending the founder call.
2. **The rename in `teim-app` is incomplete**, and the website's reconciliation
   tracker records it as done. Nothing here depends on it, but a citation or a
   cross-reference written against either record will be wrong about the other.
