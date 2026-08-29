# Access Techniques

*Retrieval methods proven on this project, with the case that proved each one.
Check here before declaring a source blocked.*

*Created 2026-08-05.*

---

## 1. Wayback CDX API as a queryable index — the strongest tool here

**Proven 2026-08-05** on ANC annual reports: indexed **6,058 archived PDFs across 25
domains**, found 124 annual reports, read 43 as text — where the prior run had located
and read **zero**. It also **bypassed a standing `nana.com` HTTP 403** that had been on
the manual-download queue for the whole project.

This is not a search engine. It is an enumeration of everything the archive holds for a
domain, which turns "I could not find it" into "it does not exist."

```
http://web.archive.org/cdx/search/cdx?url=<domain>*&output=json
    &filter=mimetype:application/pdf&filter=statuscode:200
    &collapse=urlkey&limit=20000
```

Retrieve with the `id_` modifier to get the **original bytes** rather than Wayback's
rewritten wrapper:

```
https://web.archive.org/web/<timestamp>id_/<original_url>
```

**Use it for:** any 403, any 404, and any document that used to exist. HUD's 2025–26
reorg 404'd archived ONAP award PDFs — that is a Wayback case, not a lost document.

### Outage observed 2026-08-06 — and how to tell an outage from a block

**`web.archive.org` was unreachable for a whole session on 2026-08-06**, which
matters because the gaming build had just taken **63% of its opening-date
evidence** from it the day before. The shape of the failure was worth pinning
down exactly, because "Wayback is blocked" and "Wayback is down" call for
different responses:

```
https://www.irs.gov/robots.txt          HTTP 200  0.20s
https://www.nigc.gov/robots.txt         HTTP 200  0.39s
https://archive.org/robots.txt          HTTP 200  0.29s   <-- parent domain fine
https://web.archive.org/robots.txt      HTTP 000 20.00s   <-- this subdomain only
```

CDX returned `503 No server is available to handle this request` before going
dark entirely, and `WebFetch` reported it could not fetch the host at all.

**`archive.org` answering in 0.29s while `web.archive.org` hangs for 20s is the
whole diagnosis.** It is not the network, not the sandbox, not our IP, and not
rate limiting — we had made no requests. It is that one subdomain. Probing the
*parent domain* is the cheapest way to make that call, and it takes one second.

Per `docs/PULL_DISCIPLINE.md` rule 4 this is neither an edge block (which is
instant) nor a throttle (which returns 429): a 20-second hang is a server-side
failure, so retrying is legitimate — but **not in this session**, and no poller
was left running. Work that needed Wayback was rerouted to origin sites and to
SEC EDGAR instead, which is where the Seneca Irving result came from.

### A domain that archives is not necessarily *your* domain

**Caught 2026-08-06.** Dating `Trade Winds Central Casino` (Pawnee Nation, OK)
led to `tradewindscasino.com`, which has clean 1996–99 Wayback captures. Fetching
one showed it is an **unrelated offshore sportsbook**. The CDX index was working
perfectly; the name was the trap.

This is the "Cherokee Inc." matching pitfall arriving through the archive rather
than through a crosswalk, and Wayback makes it *more* dangerous, not less,
because a plausible domain with a deep capture history reads as strong evidence.
**Open the snapshot and confirm the operator before citing it.** A domain name is
a hypothesis.

**Two cautions.**
- A snapshot can be *indexed but corrupt on retrieval*. Ahtna had exactly one report
  indexed and every snapshot corrupt. Report that as a distinct outcome from
  "not archived" — it is the difference between a dead end and a manual-download item.
- **The snapshot timestamp is when the page was captured, not when the event happened.**
  Read the date out of the document.

---

## 2. curl with a declared User-Agent

**Proven** on `sec.gov`, where `WebFetch` returns HTTP 403 and curl with a normal browser
User-Agent returns 200. That single change produced 24 of 40 rows in the 2000–2019 deals
backfill.

Try this first on any 403. It is the cheapest thing that works.

---

## 3. Full-index files beat name guessing

**Proven** on SEC EDGAR: downloading the quarterly `company.idx` files (32 files,
1.2 GB for 2010–2017) turned registrant discovery from pattern-guessing into a **census**.
663 candidates enumerated, then hand-reduced to a definitive list — which is how that
agent could report the registrant universe as *closed and demonstrated* rather than
merely "nothing else found."

Generalise: prefer a source's own index or bulk manifest over its search interface.
Search tells you what matched; an index tells you what exists.

---

## 4. Bulk endpoints reach further back than search indexes

**Proven** on USAspending: the assistance *search* index begins FY2008, and the API says
so — but the **bulk_download endpoints reach 2000-10-01**, returning pre-2008 records in
the identical 112-column modern schema. Dataset 3's floor moved from FY2008 to FY2001 on
this alone, with no new source.

When an API states a coverage floor, check whether that floor belongs to the *index* or
to the *data*.

---

## 4b. Try case variants, and distinguish "empty" from "absent"

**Proven 2026-08-05** on the Alaska DBS ANCSA portal, and it was worth 19,269 documents.

```
/StarWebPortal/page/ANCSA/portal.aspx   -> the real search, 19,269 docs
/StarWebPortal/page/ancsa/portal.aspx   -> HTTP 200, renders EMPTY
```

The lowercase path returns **200 with site chrome and no search control**. Nothing
errors. It reads exactly like "this portal has no public search," and one
capital letter is the whole difference.

The general lesson: **a 200 that renders empty is not evidence of absence.** On
IIS/ASP.NET especially, route segments can be case-sensitive while the server
still happily serves a shell for the wrong case. Before concluding a feature
does not exist, try case variants of the path and check whether the response
actually contains the control you expect.

Related, from the same run: the portal's advertised entry point
(`FillXPForm.aspx`, reached from a "Search ANCSA Filings" button) is a
**public-records REQUEST wizard** — name, firm, mailing address, free-text
"File(s) Requested" — not an index. Recognise intake forms for what they are
and do not submit them; filing a records request in the user's name is the
user's decision.

## 5. ASP.NET WebForms portals need a session first

**Proven** on the Alaska DBS ANCSA portal: the root returns 200, but hitting
`FillXPForm.aspx` directly returns **HTTP 500**. It requires a session established by
visiting the root, then `__VIEWSTATE`, `__VIEWSTATEGENERATOR` and `__EVENTVALIDATION`
echoed back on every POST, with `__doPostBack` for navigation.

Use a session-preserving client and parse the hidden fields out of each response.

---

## 6. Read the report published *after* the target year

Not an access technique but the same class of finding. **ASRC's 2001 annual report
restates all three of its 2000 acquisitions.** Year 2000 was called "genuinely hard" and
this quadrupled it. Annual reports, 10-Ks and S-4s all restate prior-period events —
and S-4 exchange-offer prospectuses restate the original private-placement date and
amount in plain text, often three times, which is how every 2001–2004 deal row got dated
despite 8-K item tagging not existing before Aug 2004.

---

## Known remaining blocks

| Host | Status | Note |
|---|---|---|
| `ahtna.com` | **hard block** | 1 report indexed in CDX, every snapshot corrupt. Manual download. |
| `cage.dla.mil` | interactive only | Detail pages need a browser session. Elijah checks these by hand. |
| Rating agencies | paywalled | Public press releases only. |
| `crainsgrandrapids.com`, `journalstar.com` | 403 / paywall | Try CDX before treating as final. |

**Sources confirmed to have nothing** (verified by full CDX enumeration, not search — do
not re-search these for annual reports): Chugach, Calista, Bering Straits, UIC, Olgoonik,
Huna Totem, Tyonek, Afognak, The Thirteenth Regional. 1,700+ archived PDFs between them,
zero annual reports; they publish newsletters and shareholder forms instead.

## Hosts that 403 automated fetch (2026-08-06)

- **justice.gov** returns 403 to automated fetch. Joins `ntia.gov` / `broadbandusa.ntia.gov` on this list. Litigation and settlement figures (Cobell, tribal trust settlements) are behind it, and they are exactly the numbers that are *almost* right from memory - so they must be retrieved, never recalled.
- **sanmanuel-nsn.gov** 403s automated fetch; archived Charitable Giving pages are stubs with no recipient names.
- **comptroller.defense.gov** 403s where **comptroller.war.gov** serves byte-identical books with HTTP 200. Try the alternate host before concluding a document is unavailable.

**A 404 body can still contain `<main>`.** Record the HTTP status per file in the fetch manifest and refuse anything that is not 200 - bia.gov will otherwise hand you a plausible-looking empty page and a silently empty dataset.

---

# Added 2026-08-26 — from `docs/BLOCKED_SOURCE_BYPASS_2026-08-26.md`

Four techniques, each paid for by a source this project had recorded as blocked and
which turned out not to be.

## 7. A 403 AT THE ROOT IS NOT A 403 AT A PATH — and the agency may have MOVED

`www.nmgcb.org` was on the blocked list as *"403 on the site root."* Measured:

```
https://www.nmgcb.org/                          HTTP 403     1,827 B
https://www.nmgcb.org/tribal-revenue-sharing/   HTTP 404    24,422 B
```

The 24 KB body is a real page — and it belongs to a **Spanish-language online-casino
affiliate site**. The domain had lapsed and been re-registered. The New Mexico Gaming
Control Board is at `www.gcb.nm.gov` and answers HTTP 200 to a browser User-Agent.

**A persistent root 403 with no other path ever tried is as consistent with "the agency
moved" as with "the agency is defended."** One request to a sub-path separates them.
Always read the body of the page you did get, not just its status.

**And the danger is asymmetric.** A block costs you the data. A squatted domain hands you
data from an advertiser under a state agency's name, and it looks like success. Before
citing any host you have not touched in months, confirm the `<title>` still belongs to
the body you think you are quoting.

## 8. READ THE CLIENT, DO NOT GUESS THE SERVER

NMGCB's report PDFs sit in a third-party "RealFile" widget. A prior pass guessed four
spellings of the file-listing endpoint against `api.realfile.rtsclients.com` and got
502/502/502/404, and recorded *"do not re-probe the RealFile API."* All four were against
a host that serves `PublicFiles/…` and nothing else.

The page that loads the data **already contains the correct call**. Two requests:

```
https://prod.realfile.rtsclients.com/js/rf-tables.js
https://cdn.rtsclients.com/SDKs/RealFile/JavaScript/rf_sdk.min.js

    var realFileLambdaURL = "https://klvg4oyd4j.execute-api.us-west-2.amazonaws.com/prod/";
    RFModule.getWidgetFiles = ... url: realFileLambdaURL + "GetWidgetFiles" ... type: "GET"
    widgets.push({ widgetId, folderId, rootFolderId, accountGUID })
```

Host, path, verb and all four parameter names, from the source. Four guesses cost four
requests and produced a wrong conclusion; one read produced the answer.

**Corollary — validate a newly-found endpoint against data you already hold**, before
trusting anything new it returns. `code/214` refuses to call an unknown folder until the
endpoint has reproduced, exactly, the four `fileId`s Cedar already had for 2022.

**Corollary 2 — a 200 with an empty list can be a MISMATCHED PAIR of legal parameters.**
`rootFolderId` must match the widget: the year's own `widgetId` with the *parent* as
`rootFolderId` returns `files: []`; with the year folder itself it returns four files.
Every FY2023–FY2026 folder read as empty until that was found.

## 9. A CLOUDFLARE 403 IS A FACT ABOUT THE CLIENT, NOT THE OBJECT

`gaming.az.gov` was recorded as *"403 with `<title>Just a moment…</title>`."* With a
browser User-Agent it returns 200 — technique 2, not tried at the time.

But the User-Agent alone is not sufficient. `urllib` with a browser UA still drew 403 on
**9 of 10** pages; `curl --compressed` with the full navigation header set
(`Sec-Fetch-Dest/Mode/Site/User`, `Upgrade-Insecure-Requests`, `Referer`, `Accept`,
`Accept-Language`) drew **200 on 10 of 10**. **The discriminator is the header SHAPE.**

And the 403 is *transient*. Same URL, three minutes apart:

```
403   3,481 B   (the interstitial)
200  21,914 B
200  21,959 B
```

**This amends the standing rule.** *"Only 404 and 403 are facts about an object"* holds
for an ORIGIN answering for our request. It does not reach a bot-score challenge issued in
front of one. Distinguish by BODY: a 403 carrying a small `Just a moment…` / Cloudflare
page is retryable; a 403 with any other body is final. Then honour the host's
`Crawl-delay` — ADG's `robots.txt` sets 10 seconds.

## 10. CDX: `collapse=urlkey`, NEVER `collapse=digest`, on a domain-wide sweep

A domain-wide `gaming.az.gov/*` query with `collapse=digest` had not returned its **first
page after 26 minutes** and was killed. The identical query with `collapse=urlkey`
answered in **27 seconds**. Digest collapse de-duplicates by CONTENT across the whole
host; urlkey collapse only merges adjacent keys.

Better still, **index the right axis**. Two cheap queries beat one exhaustive one:

```
filter=mimetype:application/pdf        the documents are PDFs; skip the HTML
url=<the one page whose markup holds the ids>   with NO collapse, so every capture
                                                comes back in timestamp order and the
                                                NEWEST can be taken
```

Technique 1 says CDX turns *"I could not find it"* into *"it does not exist."* That is
still true — but only if the sweep finishes.
