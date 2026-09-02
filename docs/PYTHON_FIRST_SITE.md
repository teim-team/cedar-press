# Rendering Cedar Press from Python

**Status:** proposal, with one page already built and running.
**Written:** 2026-09-02. Every number below is measured; `scripts/measure_duplication.py` re-derives the ones that can go stale.

---

## The short version

Cedar Press is a React client with a Python API beside it. Six subjects are
currently written **twice**, once in each language, and have to be kept
value-for-value in agreement. That is **5,493 lines across 15 files**, of which
**3,577 are code**. One of the six pairs has a cross-language test. Three have
nothing comparing them at all, and **two of those three have already drifted —
today, measurably, in ways a reader would notice.**

Rendering the site from Python deletes that class of work. Not reduces it —
deletes it, because there stops being a second implementation to disagree with.

It costs a real host. `.github/workflows/deploy.yml` publishes `dist/` to
GitHub Pages, which serves static files and cannot run a Python process. This
is not a code-only change and the section on hosting does not pretend it is.

**The working half of this document:** `GET /press/shelf` on the existing
FastAPI app renders the shelves page — the page that reads more of the
duplicated modules than any other — from `collections.py`, `repository.py` and
`press_catalog.py`, wearing the client's own `press.css`, with 359 lines of
tests. It is not a mock. Run it:

```
pip install -e server[dev]
uvicorn cedar_press.app:app --port 8000
# then http://localhost:8000/press/shelf?tier=press_pro
```

---

## 1. What is actually true today

```
src/     10,256 lines CSS · 5,879 JS · 4,964 JSX      Vite + React client
server/   3,886 lines Python                          FastAPI: collections, claims,
scripts/    456 lines Python                          codes, session, ratelimit,
                                                      repository, catalog, profiles
```

Nine client routes (`src/features/grove/pressRoutes.js`), twelve API routes
(`server/cedar_press/app.py`) before this change, thirteen after it.

**The API has never been deployed.** `.env.example` documents `VITE_API_URL` as
optional, `src/config.js` treats an empty value as STANDALONE, and
`deploy.yml` sets no environment at all. So cedarpress.ai is a wholly static
site serving a catalog bundled into the JavaScript, and `server/` exists in CI
— `ruff check server`, `python -m unittest discover` — and nowhere else. That
matters for section 5: going Python-first is not moving a running service, it
is standing one up for the first time.

---

## 2. The duplication, measured

Run `python scripts/measure_duplication.py`. Output on 2026-09-02:

| Subject | JavaScript | Python | Kept in agreement by |
|---|---|---|---|
| Launch collection: descriptors, figures, findings, citations, download bytes | `collection.js` (470 / 250 code) | `collections.py` (565 / 321) | `server/tests/test_collection.py` |
| Claim discipline: class taxonomy, verb tables, linter | `claims.js` (566 / 306) | `claims.py` (757 / 490) | **nothing** |
| Shelf access: which plan reaches which shelf | `pressAccess.js` (158 / 64) | `repository.py` (194 / 83) | **nothing** |
| Catalog, releases, articles, citation register | `pressCatalog.js` (519 / 355), `pressReleases.js` (368 / 304), `pressArticles.js` (404 / 322), `pressCitations.js` (40 / 6) | `press_catalog.py` (150 / 40) + `_press_data.json` (784, generated) | a hand-run dump |
| Activation refusals: error codes and their wording | `pressSignup.js` (141 / 58) | `codes.py` (168 / 73) | **nothing** |
| Download shaping: filename, citation row, tile promise | `pressDownload.js` (209 / 121) | `collections.py`, `repository.py` | `test_collection.py` (bytes only) |

```
JavaScript in a mirrored pair: 2,875 lines, 1,786 code
Python in a mirrored pair:     2,618 lines, 1,791 code
Both sides together:           5,493 lines, 3,577 code
Files counted once each:       15 (2 shared across pairs)

pairs with a cross-language test:  2 of 6
pairs with nothing comparing them: 3 of 6
```

And what the one real parity test costs to run, every CI run:

```
leaf values compared:                       2,475
of those, produced twice rather than read once: 159
download bytes compared byte-for-byte:      164,553
```

Read the 159 carefully — it is the honest number. Both implementations read
`data/cedar/collections.manifest.json`, so 2,316 of those values cannot differ
by construction. The 159 are the ones two bodies of code compute independently:
the context line, the figures, the findings, the citations, the download bytes.
Those are what `test_collection.py` is actually protecting, and they are the
only reason it exists.

### 2a. The failure this prevents, in the words of the module itself

`server/cedar_press/collections.py`, before the test existed:

> The two implementations must move together: this file mirrors the JS module
> value for value, and `tests/test_collection.py` holds the same contracts the
> JS suite holds, so a release that changes a series in one language and not
> the other fails a build instead of shipping two different collections.

There was no `tests/test_collection.py`. By the time somebody looked, the two
had drifted in two places: the Python descriptor carried `shelf` and the
JavaScript one did not, and the JavaScript citation resolved its version
through `pressReleases.js` while Python read the descriptor, so `deals` cited
as **v9.0 in the browser and v9 on the server**. A docstring is not a check.

That is the argument. Not that duplication is inelegant — that this specific
duplication has already shipped two different answers to the same question,
twice, in the one place anybody thought to look.

---

## 3. Three live divergences, found while building the slice

These are not hypothetical and they are not from the history. They are true of
`cedar-consolidated` as of 2026-09-02, and each is pinned by a test in
`server/tests/test_shelf.py` written to **fail when it is fixed**, so that
whoever settles it is told.

### 3a. The `tree` plan opens twelve collections on the server and none in the browser

`server/cedar_press/repository.py`:

```python
SHELF_BY_TIER = {"press": "standard", "press_pro": "pro", "grove": "grove", "tree": "grove"}
```

`src/features/grove/pressAccess.js`:

```js
const PLAN_REACH = Object.freeze({ press: SHELF.STANDARD, press_pro: SHELF.PRO, grove: SHELF.GROVE });
```

No `tree`. `tree` is a real tier — `src/workspaceTier.js` declares it and
`resolveTier` returns it. Both implementations were run:

| tier | `repository.may_open` (Python) | `canOpenDataset` (JavaScript) |
|---|---|---|
| press | 6 collections | 6 collections |
| press_pro | 12 | 12 |
| grove | 12 | 12 |
| **tree** | **12** | **0** (`shelfReach` returns `null`) |

It is the *only* disagreement between the two maps: `press`, `press_pro` and
`grove` resolve identically on both sides, and both languages agree that
neither `grove` nor `tree` may read the Cedar Press page at all
(`can_read_cedar_press` / `canReadCedarPress` are `False` for both). So the
question is narrow and answerable — does a full-platform `tree` licence reach
the Press shelves the way a `grove` one does? — and nobody was ever asked it,
because nothing in either suite compares the two maps.

### 3b. The Python catalog is a collection behind the JavaScript one

`press_catalog.CATALOG` is a snapshot of `pressCatalog.js`, regenerated by a
human running `node scripts/dump-press.mjs`. The step was skipped:

```
js  PRESS_CATALOG:      13 entries, includes `nest`
py  press_catalog.CATALOG: 12 entries, does not
```

`nest` is one of the storefront's pinned twelve — `test_collection.py` asserts
it by name. It is on the shelf, it is in the browser's catalog, and the
service's catalog has never heard of it. Regenerating the dump adds exactly
that one entry and nothing else, which is the proof it is staleness and not a
decision. (Left unfixed here on purpose: `press_catalog.py` and
`pressCatalog.js` are another agent's files this week. The server-rendered
shelf **says so on the page** rather than rendering a shorter shelf silently.)

### 3c. A snapshot regenerated by hand is not a contract

3b is not a bug so much as the predictable outcome of the mechanism. Four
JavaScript modules (1,331 lines) reach Python through one 784-line JSON file
that a person has to remember to rebuild. Nothing in `deploy.yml` runs the
dump; nothing fails if it is stale. Under a Python-first site there is no dump,
because there is no second copy to feed.

---

## 4. The framework choice

**FastAPI + Jinja2.** Rejected alternatives below, with what each would have
bought.

The decisive constraint is the one the owner did not state but the repository
does: **10,256 lines of hand-written, reviewed, contrast-audited CSS**
(`press.css` alone carries 400 distinct `.cp-*` selectors and a review
owner's name in its header). Any framework that generates its own markup means re-attaching that
stylesheet class by class, or abandoning it. That is the axis the choice turns
on, more than language purity.

### FastAPI + Jinja2 — chosen

- FastAPI is **already here**, with thirteen working routes, a session cookie,
  rate limiting, and a repository seam written for a future Postgres. Adding
  HTML is `Jinja2Templates` and a `response_class`. No second app, no second
  process, no second deployment.
- Jinja templates **are HTML**. `press.css` attaches by writing the class
  names it already styles. The slice proves this: the shelf page adds **zero
  lines of CSS**, links `fonts.css`, `redesign.css` and `press.css`
  (7,062 of the 10,256 lines) unchanged, and a test asserts the page contains
  no `<style>` block and invents no class name.
- A designer can open `shelf.html` and read it. That is not a small thing on a
  publication whose stylesheet has a named review owner.
- Server-rendered HTML is cacheable, indexable and works with JavaScript off —
  which for a subscription publication whose readers cite it is the right
  default, and is not what any of the three Python-native frameworks below
  optimise for.
- Cost: it is a template language, so nothing type-checks the template against
  the view model. Mitigated by keeping every decision in `shelf.py` and
  leaving the template dumb, and by testing the rendered HTML rather than the
  view model.

### Reflex — rejected

Reflex compiles Python components to a **React** front end with a Node build
step and a WebSocket-synced server state. Confirmed from its own docs: external
CSS arrives via `rx.App(stylesheets=[...])`, and components are Python objects
(`rx.box`, `rx.hstack`) whose class names you set per component.

- It does not remove JavaScript. It moves who writes it. A Node toolchain, a
  React runtime and a build step all remain — the exact things a Python
  collaborator would be told had gone away.
- All 4,964 JSX lines become Reflex component trees. That is a rewrite of every
  page, not an incremental migration, and there is no half-way state where both
  clients run.
- `press.css` would be re-attached by setting `class_name=` on every generated
  element. Possible, tedious, and one typo produces an unstyled band with no
  build error.
- What it would have bought: real Python types over the whole UI, and
  interactivity (the shelf's hover reader, the Cedar ask box) without hand-written
  JavaScript. Genuinely attractive if this were a green field. It is not.

### NiceGUI — rejected

NiceGUI mounts a **Vue/Quasar** app in the browser and holds a persistent
WebSocket per client; the README describes the architecture in exactly those
terms.

- Every page view becomes a stateful server connection. Cedar Press is a
  publication: pages that must be indexable, linkable, cacheable and cheap to
  serve to a reader who opens one brief. A per-viewer WebSocket is the wrong
  cost shape and the wrong failure mode.
- It is built for internal tools and dashboards, and it is very good at that.
  Cedar Grove's analysis surface may well be the right home for it later. The
  storefront is not.
- Same stylesheet problem as Reflex, plus Quasar's own component CSS to fight.

### FastHTML — rejected, but it was close

FastHTML is Starlette + Uvicorn + HTMX + `fastcore` FastTags: markup written as
Python objects, decorator routing, no build step, no template language. It is
the nearest thing to the right answer.

- It is **its own application framework**, on Starlette. Adopting it means
  replacing the FastAPI app — thirteen routes, the Pydantic request models, the
  session dependency, the flattened-error handler with its written-out
  reasoning — for a rendering layer. That is work whose payoff is stylistic.
- Markup as Python calls (`Div(H3(...), cls="cp-band__name")`) is harder for a
  designer to read and edit than HTML is, and this stylesheet has a designer.
- What it would have bought: no second language in the templates, and markup
  that type-checks. If the templates ever grow past a handful of pages and the
  team is all-Python, revisit — the HTMX half of it is available to Jinja
  anyway, as a `<script>` tag.

### Django, Flask — not seriously considered, and why

Django would bring an ORM, migrations and an admin the project has no use for
yet (`repository.py` exists precisely so the storage swap is one module) and
would replace FastAPI. Flask is the same architecture as the chosen option with
an older async story and no OpenAPI. Neither buys anything the incumbent does
not already have.

---

## 5. The hosting change, named and priced

**GitHub Pages cannot run Python.** `.github/workflows/deploy.yml` builds
`dist/` and hands it to `actions/deploy-pages`. There is no process. A
Python-rendered page needs a host that runs one.

This is the real cost of the proposal and the only part that cannot be done
incrementally inside the repository.

### What has to change

| Today | Under a Python-first site |
|---|---|
| `deploy.yml` → `upload-pages-artifact` → `deploy-pages` | build a container (or a buildpack), push to a host, run `uvicorn` behind it |
| No runtime, no secrets in production | `CEDAR_PRESS_SECRET`, `CEDAR_PRESS_ACCOUNTS`, `CEDAR_PRESS_CODES`, `CEDAR_PRESS_ORIGINS` must exist in a real secret store |
| cedarpress.ai → Pages, via `public/CNAME` | cedarpress.ai → the host; the CNAME file stops being how DNS is decided |
| Static assets served by Pages' CDN | either the host serves them, or they stay on a CDN and the app renders HTML only |
| Nothing to monitor; a bad deploy is a bad file | a process that can crash, restart, run out of memory, and needs health checks (`/health` already exists) |
| £0 | a small always-on instance, plus a database when `repository.py` stops answering from files |

### Candidate hosts

Judgment, not measurement — the numbers below are what each provider publishes
and should be re-checked before anyone signs anything.

- **Fly.io** — a Dockerfile and `fly.toml`; scale-to-zero is available, so an
  idle publication costs close to nothing; regions are explicit. Best fit for
  a low-traffic site that must feel instant when it is read.
- **Render** — the least work: point it at the repo, it detects Python, gives a
  URL and TLS. Free tier sleeps, which for a subscriber publication is a
  cold-start on the first read of the morning; the paid tier does not.
- **Google Cloud Run** — request-scoped billing genuinely suits a site nobody
  reads at 3am, and it is the most operationally serious of the three. Also the
  most setup: a container registry, IAM, a load balancer for the custom domain.
- **Railway** — comparable to Render, simpler pricing, smaller company.

**Recommendation: Fly.io**, with Render as the escape hatch if the Dockerfile
becomes a fight. The deciding factor is scale-to-zero on a site with a small,
known readership, plus the fact that the same host will later need to run
whatever `repository.py` talks to.

### The keep-Pages option, stated honestly

There is a version of this that does not move hosts: keep publishing `dist/`,
and render the Python pages **at build time** into static HTML in CI. Every
duplication argument in section 2 still holds — one implementation, no drift —
and the deploy pipeline barely changes.

What it cannot do: per-reader pages. The shelf differs by plan, the gate and
activation are inherently dynamic, and downloads are entitlement-checked. So a
build-time render works for `/methods`, `/tribal-data-request`,
`/research-access`, `/whats-new` and `/articles` — five of nine routes — and
stops. It is a real intermediate step and step 3 below takes it, precisely
because it delivers most of the anti-drift benefit before anyone has to buy a
server.

---

## 6. The order of work

Each step is independently shippable and leaves both clients working. Sizes are
measured line counts of the thing being replaced; the effort bands are
judgment.

**Step 0 — done, in this change.** `GET /press/shelf`, `shelf.py` (261 lines),
`shelf.html` (222), `test_shelf.py` (359). Proves the data, the stylesheet and
the host process. **Buys:** the argument stops being an argument.
**Breaks:** nothing; it is a new route.

**Step 1 — close the three drifts, before migrating anything.**
Settle `tree` (3a) by deciding which answer is right and making both say it;
regenerate `_press_data.json` (3b); and add parity tests for `claims.js ↔
claims.py` and `pressSignup.js ↔ codes.py` on the model of
`test_collection.py`. **Buys:** the migration starts from a known state instead
of quietly canonising whichever copy got ported. **Breaks:** possibly a tier's
access, deliberately. *Small — a day.*

**Step 2 — move the tier ladder and the collection marks into shared data.**
`PRESS_TIERS` (the band copy) lives only in `pressCatalog.js`;
`pressCollectionIcons.jsx` is 210 lines of JSX SVG. Both are why the
server-rendered shelf currently shows a shelf id where a product name belongs
and a badge with no mark. Move the ladder into the manifest or the dump; move
the icons to an SVG sprite both languages can reference. **Buys:** the Python
shelf becomes a complete page. **Breaks:** nothing, if the dump is regenerated.
*Small.*

**Step 3 — render the five static pages from Python, at build time, still on
Pages.** `/methods` (230 JSX + 293 in `pressMethodSections.jsx`),
`/tribal-data-request` (203), `/research-access` (112), `/whats-new` (314),
`/articles` (121 + 354 for a piece). CI runs the app, fetches each route,
writes the HTML into `dist/`. **Buys:** `pressMethod.js` (333),
`pressArticles.js` (404), `pressReleases.js` (368) and `pressCitations.js` (40)
stop needing a JavaScript reader — the largest single reduction available
without changing hosts. **Breaks:** any interactivity on those pages must
degrade to links or `<details>`; the article page's parallax and fade-in hooks
go. *Medium — a week or two.*

**Step 4 — stand up the host.** Dockerfile, Fly (or Render), secrets, DNS,
health checks, a staging URL. Serve steps 0 and 3 from it in parallel with
Pages before cutting DNS. **Buys:** everything after this point.
**Breaks:** nothing until DNS moves; that is the risky day and it should have
its own runbook. *Medium, and mostly not code.*

**Step 5 — move the shelf and the reader for real.** `/data` (494 JSX) and
`/` (188 + 166 + 276). **Buys:** `pressAccess.js`, `pressCatalog.js`,
`pressDownload.js` and `collection.js` lose their reason to exist —
1,356 JavaScript lines, and with them `test_collection.py`'s whole job.
**Breaks:** the hover reader, the badge reveal, the Cedar ask box. Each is a
deliberate decision: keep it as progressive enhancement, or let it go.
*Large.*

**Step 6 — the gate, activation and settings.** `/settings` (224),
`PressGate` (546). These are forms and a session, which is the thing
server-rendered HTML has always been best at, but they are also the paths where
a mistake locks a paying subscriber out. Last on purpose. **Buys:**
`pressSignup.js` retires; `codes.py` becomes the only copy of the refusals.
*Medium, high care.*

**Step 7 — delete.** Remove the retired JavaScript modules, the dump scripts
and the parity tests they existed to support. **Buys:** the number in section 2
goes to zero. Nothing before this step is wasted if the project stops here
instead; that is the point of the ordering.

### What is deliberately not in the plan

- **Deleting the React client.** Both run side by side until step 7, and the
  owner keeps a URL to send a reviewer throughout.
- **Rewriting the stylesheet.** 10,256 lines of reviewed design carry over
  untouched. The slice adds zero.
- **Touching `data/cedar/collections.manifest.json` or the import pipeline.**
  The manifest is already the single source both languages read, and it is the
  part of this architecture that is right.

---

## 7. The slice, and how to check it

`GET /press/shelf` — `server/cedar_press/shelf.py`,
`server/cedar_press/templates/shelf.html`, route in `server/cedar_press/app.py`.

Why the shelf and not another page: `src/pages/grove/PressShelf.jsx` reads five
modules that have Python counterparts — `collection.js`, `pressAccess.js`,
`pressCatalog.js`, `pressReleases.js`, `pressDownload.js` — more than any other
page in the client. If the central claim is that the mirrored logic is already
in Python, the shelf is where it has to be demonstrated.

What it does:

- Renders all twelve collections from `LAUNCH_COLLECTION`, which reads
  `data/cedar/collections.manifest.json`. No fixtures. The version string in
  the masthead is `collection_context_line()`, the same function
  `test_collection.py` compares across languages.
- Decides what is open with `repository.may_open` — literally the function
  `/press/collections` uses. A test asserts the page and the JSON route open
  the same set for every known tier.
- Wears `fonts.css`, `redesign.css` and `press.css` unchanged. Verified in a
  real browser (headless Chromium, 1440px): no failed requests, zero horizontal
  overflow, badges laying out as 172px squares in Inter.
- Says what it does not know. The catalog gap from 3b is printed on the page.
  The tier ladder's marketing copy is named as missing rather than retyped,
  because adding a seventh hand-kept mirror to a page arguing against six would
  refute the page.
- Grants nothing. The tier comes from the session when there is one and from
  `?tier=` otherwise, and it changes only what is *described*: every badge
  submits to `/press/collections/{id}/download`, which still requires a session
  and still asks `may_open`. A test walks every link on the grove-tier page and
  asserts each returns 401 unauthenticated.

What it does not do, honestly:

- **No hover reader.** That is React state. The panel shows every collection's
  detail at once instead, which is more information and no script — but it
  makes the panel column much taller than the badge grid, so the wide bands
  carry visible empty space. One CSS rule or a `<details>` per collection would
  fix it; neither was added, because "zero new CSS" is a claim worth being able
  to make.
- **No badge marks.** See step 2.
- **No band reveal animation.** `is-in` is set on every band, which is the
  correct resting state without an `IntersectionObserver`.

Checks, all passing on 2026-09-02:

```
npm run lint                                        clean
npm run test                                        86 passed
ruff check server scripts                           clean
python -m unittest discover -s tests -t .  (server) 96 passed
```

The 96 includes `test_collection.py` — the cross-language contract test still
runs and still passes. It has a job until step 7, and this change does not take
it away.
