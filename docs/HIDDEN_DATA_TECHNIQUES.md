# What the page sends but does not show

*Written 2026-09-01. Live doc. Standing practice for every scraping workstream —
read this before harvesting any site.*

Owner, 2026-09-01: *"All these website scrapings check for, like, hidden stuff.
Like, stuff that's not published on the website for user to see, but, like, is
in the HTML code or whatever."*

He was right that this was not written down anywhere. It is now.

## The premise

A rendered page is a *view* of the data behind it, and it is usually a lossy one.
A vendor directory showing 10 of 340 businesses across 34 pages very often ships
all 340 in a single JSON blob, or exposes them through an API the page itself
calls. Harvesting the rendered HTML gets you 10 rows and 34 fetches. Finding what
the page is actually reading gets you 340 rows in one.

This is not a trick. It is reading what the server voluntarily sends to any
visitor who asks — the same bytes the browser received. **The boundary is at the
end of this document and it is not negotiable.**

## The checklist — run it on every site before crawling page by page

### 1. `<script type="application/ld+json">` — JSON-LD / schema.org
Structured markup for organizations, places, events, articles. Frequently carries
the legal name, full address, phone, geo coordinates, founding date and parent
organization in clean fields while the visible page shows a stylized logo. Also
the single best source for **event and newsletter publication dates**.

### 2. Embedded application state
Look for `window.__INITIAL_STATE__`, `__NEXT_DATA__` (Next.js), `__NUXT__`
(Nuxt), `page-data.json` (Gatsby), or any large `JSON.parse("...")`. These
routinely contain the **complete unpaginated collection** the page is rendering a
slice of, plus fields the template never displays — internal IDs, categories,
status flags, timestamps.

### 3. The WordPress REST API — the highest-yield item on this list
Most tribal government sites are WordPress. If `/wp-json/` responds, so do:

- `/wp-json/wp/v2/pages?per_page=100` — every page, including ones not in the nav
- `/wp-json/wp/v2/posts?per_page=100&page=N` — the full news/newsletter archive
  with dates, in JSON, no crawling
- `/wp-json/wp/v2/media?per_page=100` — **every uploaded PDF**, which is where
  TERO vendor lists, budgets, ordinances and newsletter back issues actually live
- `/wp-json/wp/v2/types` — reveals **custom post types**. Vendor directories,
  business registries and staff listings are usually a CPT, and the type name
  tells you the endpoint that returns all of them.

`?per_page=100` is the max; paginate with `&page=N` and read the
`X-WP-TotalPages` response header so you know when you are done.

### 4. `sitemap.xml` and `sitemap_index.xml`
The site's own inventory of its pages, including ones removed from navigation but
still served. Newsletter archives and old vendor lists survive here constantly.
Also check `robots.txt` — it names sitemap locations. **See the boundary section
on what `robots.txt` also means.**

### 5. Select options, filters and hidden inputs
A `<select>` of tribes, categories, counties or years IS a complete list — the
taxonomy, handed over, without crawling. Filter dropdowns on a vendor directory
give you the full category vocabulary. `<input type="hidden">` carries nonces,
IDs and sometimes totals.

### 6. `data-*` attributes
Row IDs, coordinates, category codes, sort keys, statuses. Frequently richer than
the rendered cell text, and often the join key you need.

### 7. HTML comments
`<!-- -->` blocks hold removed sections, staging notes, template scaffolding, and
occasionally an entire commented-out earlier version of a table.

### 8. The AJAX source behind any table
A sortable/searchable table is almost always DataTables, Algolia, or a custom
`fetch`. Read the page's JS for the endpoint URL, then call it directly with a
large page size. One request replaces the whole crawl.

### 9. ArcGIS / map services — very high yield for this project
Tribal sites embed maps constantly. A `FeatureServer` or `MapServer` URL accepts
`?where=1=1&outFields=*&f=json`, which returns the **complete attribute table**:
facility names, addresses, parcel data, boundary metadata, service areas. This is
often the single richest structured source on a tribal site.

### 10. Embedded Google Sheets and Docs
An `<iframe>` pointing at a published Sheet can be re-requested as CSV via its
`/export?format=csv` form. Tribal vendor and contact lists live here often.

### 11. PDF internals
Extract text, but also metadata: author, producer, creation and modification
dates, and sometimes the original filename and directory. A vendor list PDF's
creation date is the `as_of_date` the document itself never prints.

### 12. `<meta>` and OpenGraph tags
Canonical URLs, official organization names, descriptions, publication dates —
often more precise than the visible heading.

### 13. Feeds
`/feed/`, `/rss`, `/atom.xml`, `?feed=rss2`. Newsletter and press-release
archives in dated, parseable form. Try these before scraping a news page.

## Record what you did

Whenever a technique above is what actually produced the data, record it in the
`evidence` column alongside the rung of the alternative-route ladder. Two reasons:
the next agent working that tribe skips straight to the method that worked, and a
customer asking where a number came from gets a real answer rather than "the
website."

Note the technique per site, not per row.

## THE BOUNDARY — read this part twice

Everything above is **reading what the server sends to any anonymous visitor**.
None of it is an access-control bypass, and the distinction is absolute:

**Permitted** — parsing the HTML, JSON, JS, XML and headers you were served;
calling a public API the page itself calls; requesting a documented public
endpoint like `/wp-json/wp/v2/posts`; reading a published sitemap or feed;
extracting metadata from a PDF you were allowed to download.

**Not permitted, ever**
- Guessing, brute-forcing or enumerating credentials, tokens, API keys or nonces
- Requesting admin, staging or internal endpoints (`/wp-admin/`, `/admin`,
  `/.env`, `/.git/`, backup files, database dumps) — these are not "hidden data,"
  they are someone's private infrastructure
- Anything behind a login, paywall or session, including reusing a token you
  happened to observe
- Exploiting a misconfiguration — an exposed directory listing or an unsecured
  endpoint is a mistake by the operator, not an invitation
- Ignoring `robots.txt`. It names sitemaps, which you may use; it also names
  `Disallow` paths, which you must not fetch even though they would respond
- Volume that burdens a small tribal server. Rate-limit. An API call that returns
  340 rows at once is *gentler* than 34 page fetches, which is part of why this
  document exists
- Any of the above on a source marked `TERMS_STATED_RESTRICTIVE` — Confederated
  Colville and CTUIR among them. **Terms are a decision the publisher made.** A
  JSON endpoint on a site that has told us not to scrape it is still off limits,
  and finding a cleverer route to refused data is the one failure mode that would
  genuinely damage this project's standing with the nations it covers.

If a technique feels like it is working *around* someone rather than *with* what
they published, stop and put it in `review/OWNER_DECISION_QUEUE.md` instead.

`docs/PULL_DISCIPLINE.md` governs throughout and outranks this document wherever
they touch.

## A 200 with a valid file is not proof you fetched the right file

*Added 2026-09-01 by the gaming workstream, which caught this three objects
before it would have shipped.*

A download endpoint of the shape `?wpdmdl=<id>` was called with an **empty**
value. It returned **HTTP 200 and a valid, openable PDF — 302 times, the same
PDF every time.** Every status code was green, every file passed a "is this a
real PDF" check, and the corpus would have been 302 copies of one document
filed under 302 different names.

This is the download-side twin of the robots false-block in
`PULL_DISCIPLINE.md`. There, a check failed closed for the wrong reason and
silently stopped good work. Here, a check passed for the wrong reason and
silently manufactured a fake corpus. **Both are checks that are not measuring
what their name says**, and a green one is the more dangerous of the two
because nothing prompts you to look.

WordPress Download Manager, `?download=`, `?file=`, `?attachment_id=` and most
CMS download shims behave this way: an unrecognised or empty id falls through
to a default, an index, or the most recent upload rather than erroring.

**Three guards, all cheap:**

1. **Hash every object and count distinct hashes.** If `n_objects` and
   `n_distinct_md5` diverge, stop. The gaming pull now carries an
   `IDENTICAL_MD5_CEILING` for exactly this.
2. **Match the download link to the slug you asked for.** Do not construct an
   id and hope; take the href the page actually publishes for that document.
3. **Canary before the run.** Fetch three objects, confirm three distinct
   hashes and three distinct titles, and only then loop. Three wasted requests
   beats 302 wasted ones and a poisoned table.

Record the outcome honestly when it fires: this one was logged as
`accepted_then_failed_server_side: 302` and all 302 objects were deleted. A
fetch that returned 200 and the wrong content is a **failure**, and calling it
anything else puts the lie in the provenance record.
