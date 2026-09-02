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

## A NEGATIVE FROM SEARCH ALONE IS NOT A NEGATIVE

*Added 2026-09-01 by shard A, which caught itself producing a false one.*

Shard A searched Bad River's site and recorded **"no TERO."** The WordPress
media index then returned a **2024 TERO Compliance Plan** and a TERO Plan
attached to a 2026 RFP. Same site, same session, opposite answer.

Its own conclusion, and it is now project standard:

> **A "no TERO" from search alone is not evidence.**

The reason is structural, not incidental. Search — site search, a search
engine, or reading the navigation — only sees what the CMS chose to render and
link. A PDF uploaded to the media library and referenced from one RFP, or
linked from a page since removed, is invisible to all three and is sitting
right there in `/wp-json/wp/v2/media`. On the same pass, Grand Portage's
enacted Tribal Employment Rights Ordinance — with a 2026-07-15 council letter
announcing its adoption — returned **zero search results** and was found only
in the media index.

**Before recording any absence, you must have run the machine-readable routes:**

1. `/wp-json/wp/v2/media?per_page=100` with pagination (read `X-WP-Total`)
2. `/wp-json/wp/v2/types`, then the endpoint of any custom post type
3. `/wp-json/wp/v2/search?search=<term>&per_page=100`
4. `sitemap.xml` / `sitemap_index.xml`

Only then is "not published" a finding. Otherwise the honest status is
**`NOT_SEARCHED_MACHINE_READABLE`**, which is a different claim.

This matters beyond tidiness because **false negatives are load-bearing here**.
The native-owned-business workstreams are measuring a hit rate that decides
whether hundreds of remaining tribes are ever attempted; the coverage ledger
separates "attempted, none found" from "untouched" precisely so effort gaps
stay visible. A false absence corrupts both, and unlike a false positive it
leaves no trace to trip over later.

Scale, from the same shard: 65 of ~90 hosts had the media index open, and
`/wp/v2/media` returned **11,863 documents in about 660 requests**. Bad River
alone advertises 2,629 via `X-WP-Total`, Cow Creek 2,007, Acoma 1,266. This is
also *gentler* on the host than crawling for them.

### The companion: a 403 is often a user-agent filter, not a refusal

Shard A turned a 403 into a 202 on `fortpecktribes.org` **and on
`cherokeetero.com/directory/`** by sending browser headers — the vendor
registry had the latter logged as a hard 403 for a week. Relaxed TLS recovered
three more hosts; `crit-nsn.gov`'s certificate covers the apex only;
`chehalistribe.org` refuses 443 at the apex and serves on `www`.

None of that is bypassing an access control — it is speaking HTTP the way a
browser does to a server that is willing to serve you. **A `robots.txt`
Disallow, a login wall, and a `TERMS_STATED_RESTRICTIVE` source remain
refusals and stay refused.** Colville's TERO was not fetched by any route on
this pass, including these.

## SEARCHING FOR THE INSTITUTION INSTEAD OF THE THING

*Added 2026-09-01. This invalidated a rate measured across 298 tribes.*

Shards L and M swept all 297 unsurveyed federally recognized tribes and both
independently returned **3.4%**. The number is real, replicated and honest — and
it answers the wrong question, because both searched **TERO vocabulary**.

The owner:

> *"A tribe may not have TERO, or obviously has TERO but maintains member-owned
> lists."*

**A TERO office is an institution. A business list is an artifact.** They
correlate; they are not the same thing. A tribe with no TERO programme can still
publish a member-owned business directory, an enterprise register, a chamber
roster or an economic-development portfolio — and a search for `tero`,
`preference` and `certified vendor` finds none of them.

The evidence was already in the sweep. Shard L's broader count was **11 of 149
(7.4%)**, and the extra six were tribal-enterprise registers surfaced through
WordPress custom post types literally named **`enterprise`** and
**`tribalbusiness`**. No TERO term would ever have reached them.

**The general rule:** when a search is built from the vocabulary of the
programme rather than the vocabulary of the object, its negatives measure the
programme's prevalence and nothing else. Before recording a rate, ask what the
search terms were a proxy for, and whether the thing can exist without them.

This is the same family as the false-negative rule above — a negative from a
narrow route is not a negative — but a level up: there the route was narrow
(rendered HTML instead of the media index), here the *concept* was narrow.
Widening the route does not fix a search for the wrong noun, which is why
shard L's 2.3× media-index re-sweep added exactly one list.

**Vocabulary to run alongside the programme terms**, ordered by observed yield:
`/wp-json/wp/v2/types` first — a custom post type name is the single highest-
yield signal in this project — then `enterprise`, `enterprises`,
`tribalbusiness`, `business-directory`, `member-owned`, `citizen-owned`,
`tribally-owned`, `our-companies`, `subsidiaries`, `holdings`,
`economic-development`, `chamber`, `commerce`, `entrepreneur`,
`small-business`, `artisan`, `craft`.

And an enterprise register is worth more than the vendor list that was being
hunted: it is **parent-asserted ownership**, the strongest evidence class here,
and it feeds the hub/sub-hub crosswalk rather than the vendor dataset.

## THE URL IS THE GUESS. IT IS NEVER THE EVIDENCE.

*Added 2026-09-02 by shard N, the coverage tail, which caught itself
fabricating ten websites.*

Shard N's last rung derives a candidate domain from an entity's name, fetches
it, and requires the page to prove it belongs to that entity before recording
it. The name-evidence check was written as:

```python
hay = text_of(html) + " " + url          # <-- the defect
hits = sum(1 for t in name_tokens if t in hay)
```

The URL under test was in the haystack. Every candidate therefore proved
itself: `capitan.org` "carried the name" of the Capitan Grande Band because the
string `capitan` was in the URL being tested. On that reasoning the rung
accepted, as verified tribal and business websites:

| recorded as | actually |
|---|---|
| `fort.org` — Fort Bidwell Indian Community | a Gandi domain-parking page |
| `biglagoon.org` — Big Lagoon Rancheria | Big Lagoon **Elementary School** |
| `capitan.org`, `grindstone.org`, `laguna.org` | blank pages |
| `cherokee.gov` — "Cherokee Unlimited, Inc" | **the Cherokee Nation** |
| `sanjuan.com`, `tribalenergy.org`, `tallsalt.com` | unrelated |

Ten rows, every one of which would have read in the coverage ledger as a
**closed gap** — the most expensive kind of wrong, because a blank invites
another attempt and a filled cell does not.

**Circular evidence is not weak evidence. It is no evidence.** The test felt
strict — it demanded name tokens on the page — and could not fail.

### The four rules that came out of it

1. **Never let the thing being tested into the evidence for the test.** The
   URL, the filename, the search query you used: all of them contain the
   answer you are looking for, which is exactly why they cannot corroborate it.
2. **A 200 is not the site.** Two of shard N's tribal sites were 169 bytes of
   SiteGround captcha redirect (`/.well-known/sgcaptcha/`) — HTTP 200, valid
   HTML, none of it the tribe's website. Same family as the `?wpdmdl=`
   incident above: a check that passes for the wrong reason. Detect
   interstitials (`sgcaptcha`, `cf-browser-verification`, "Just a moment…")
   and registrar parking boilerplate by their content, and record the body
   size so a later gate can read it back.
3. **A one-word domain guess belongs to somebody else.** `fort`, `capitan`,
   `laguna`, `cherokee`, `grindstone`, `sanjuan` are all real organisations'
   domains, none of them the entity being probed. Guess only labels that join
   two or more of the entity's distinctive tokens, or one long one.
4. **Require the class, not only the name.** A page can carry an entity's whole
   name and be a different kind of thing entirely — `biglagoon.org` carries
   "Big Lagoon" on every page and is a primary school. Demand a marker that the
   page is the *kind* of organisation you are looking for.

### And put it in the gate, not only in the code

Each of the four is now a `verify` invariant in `code/1020_tail_web_probe.py`
that exits 1 on a synthetic violation, and rerunning the gate over the
already-written rows is what proved all ten were bad. **A guard that lives only
in the writing path cannot tell you what it already let through.**

A publisher-stated URL is exempt and should be: a domain the BIA publishes in
its Tribal Leaders Directory, or one derived from an email address the
organisation itself filed with DOI, is an assertion by the publisher and needs
no page-text proof. The rule is about *guesses*.

## A CUSTOM USER-AGENT DOES NOT MAKE YOU A DIFFERENT AGENT

*Added 2026-09-02 by shard N, which found it in its own output and then in
seven other shards'.*

Every scraper here declares a polite UA — `CedarPress-research/1.0 (…contact…)`
— and hands `robots.txt` to `RobotFileParser`, then asks:

```python
rp.can_fetch(UA, url)          # UA = "CedarPress-research/1.0 (…)"
```

`penobscotnation.org` publishes:

```
User-agent: ClaudeBot
Disallow: /
...
User-agent: *
Allow: /
```

Our UA string contains no `ClaudeBot` token, so the parser matched the
permissive wildcard block and returned **allowed**. The site was fetched.
`elyshoshonetribe.com` names `ClaudeBot` and `anthropic-ai` and went the same
way. Cedar had already ruled on both hosts on 2026-08-26 — *"the named-agent
rule is more specific and therefore governs us"* — and excluded them from
Wayback for it. The ruling was in the registry; the code never asked.

**A named-agent disallow is aimed at us.** Declaring a project-specific UA is a
courtesy that tells a server who is calling; it is not a way to stop being the
agent the publisher refused. Reading the wildcard block instead of the block
with our name on it is the same shape as every other defect in this document:
a check that ran, passed, and was not measuring what its name says.

**The fix, and it is three lines:**

```python
AGENT_TOKENS = ("ClaudeBot", "anthropic-ai", "Claude-User",
                "Claude-SearchBot", "Claude-Web")
for tok in (UA,) + AGENT_TOKENS:
    if not rp.can_fetch(tok, url):
        return False, "robots.txt Disallow for " + tok
```

Most restrictive answer wins, and name the token that refused so the row says
who was being spoken to.

### The exposure, measured

Re-checking every host shard N had fetched found **two more** beyond the two
from the registry — `sanipueblo.org` (Pueblo of San Ildefonso) and
`loscoyotestribe.org` (Los Coyotes). All four were purged: cached bodies
deleted, rows removed, entities re-run, and the outcome recorded as
`TERMS_RESTRICTED_DO_NOT_HARVEST` / `government_refused_robots` — **a site that
exists and refuses us, which is a finding and not an absence.**

An offline cross-check of the merged `cedar_web_map.csv` against the
`source_terms_status` column of
`review/tribal_vendor_list_registry_2026-08-26.csv` then found **42 rows
carrying a 2xx from a host already recorded as refusing this agent or stating
restrictive terms**, spread across shards A, B, C, D, E, F, G and N. Shard N's
four are cleared. The other 38 are listed per row, with the registry's own
quotation of the terms, in **`review/1020_named_agent_robots_exposure.csv`**
for the shards that own them.

**Two standing lessons:**

1. **Ask robots as every name that means you.** Anthropic's crawler tokens are
   the ones publishers actually write.
2. **When one workstream records a refusal, the others must be able to see
   it.** The Penobscot and Ely Shoshone refusals were documented, quoted and
   correctly reasoned in the vendor-list registry two weeks before four other
   shards fetched a restricted host. A ruling that lives only in a CSV nobody
   joins to is a ruling that gets re-broken. Read
   `source_terms_status` before you fetch.

### The town has the same name, and it has a council too

*Same shard, same day, one rung further down.*

After the circular-evidence fix, the derived-domain rung still accepted
`scottsvalley.gov` as the website of the **Scotts Valley Band of Pomo
Indians**. It is the **City of Scotts Valley, California**. The page carried
both of the tribe's distinctive tokens — they are the same two words because
they are the same place — and it passed the class-marker test on the word
**`council`**, which appeared seven times because a city has a city council.
`tribe`, `tribal`, `band`, `rancheria`, `pomo` and `indian`: zero occurrences
each.

A marker that both kinds of organisation use is not a class marker. Two rules
came out of it:

* **Drop any positive marker a look-alike also uses.** `council` went; `city
  of` and `town of` never belonged.
* **Add negative markers, and let them win.** A page that calls itself the
  City of X, a school district, a chamber of commerce or a public library is
  not a tribal government however much of the name it carries. The same guard
  catches `biglagoon.org`, which is Big Lagoon **Elementary School**.

And record *which* marker qualified a page, in the row. A gate can then re-read
it — `verify` invariant (12) in `code/1020_tail_web_probe.py` refuses any
derived government site that does not name the marker it passed on, which is
how the four rows written before the fix were found and re-run.
