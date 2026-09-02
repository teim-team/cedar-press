# Capability-statement harvest — Cedar's first second source

*Built 2026-09-02 by `code/1114_capability_statement_harvest.py`. Every number
below is re-derivable: `worklist` → `run` → `harvest` → `purge` → `build` →
`verify`. `data/staging/capability_1114/run_summary.json` is the machine-readable
form and is written by the same command that produced this prose.*

```
py -3 code/1114_capability_statement_harvest.py worklist     # offline
py -3 code/1114_capability_statement_harvest.py run --job released
py -3 code/1114_capability_statement_harvest.py run --job identifiers
py -3 code/1114_capability_statement_harvest.py run --job institutions
py -3 code/1114_capability_statement_harvest.py harvest       # ranked 2nd pass
py -3 code/1114_capability_statement_harvest.py purge         # (host, md5) dupes
py -3 code/1114_capability_statement_harvest.py build         # offline
py -3 code/1114_capability_statement_harvest.py verify        # 10 invariants, exits 1
py -3 code/1114_capability_statement_harvest.py selftest      # PASSES
```

---

## THE HEADLINE — 55 facts in Cedar now have a second source

`docs/ASSERTION_LAYER.md` measured that **0 of 8,975 single-valued facts carry a
second source**. Every UEI and CAGE Cedar holds came from the federal side —
FPDS, SAM, the award archive — which is one evidence family however many tables
it has been copied into.

This pass read **151 distinct federal identifiers off the entities' own public
pages**, an `entity_self_published_web` evidence family that has never touched
the federal one:

| disposition | distinct identifiers | what it is |
|---|---:|---|
| `CORROBORATES_LEDGER_SAME_ENTITY` | **55** | the entity publishes the identifier the ledger already attributes to it. **The first genuine corroboration in this project.** |
| `NOT_IN_LEDGER` | 77 | self-disclosed and previously unheld |
| `HELD_IN_LEDGER_UNDER_ANOTHER_ENTITY` | 19 | a parent publishes an identifier the ledger attributes to a different entity — an **ownership signal**, not a repointing licence |

By type: CAGE 53 · UEI 39 · DUNS 33 · NAICS 23 · EIN 3.
Per-identifier exhibit, with the label matched, the quote around it, the source
URL and the document md5:
**`review/capability_statement_identifiers_1114_2026-09-02.csv`**.

**The 33 DUNS rows are flagged `may_publish = N`.** D-U-N-S is proprietary under
ruling item 4 and stays internal *even though the entity published it itself*.

**Where they came from** — 14 entities, and the shape is worth reading:

| entity | identifiers | corroborating |
|---|---:|---:|
| NANA Regional Corporation (`akima.com`) | 80 | 45 |
| Kikiktagruk Inupiat Corporation | 18 | 4 |
| Nakupuna Foundation | 16 | 1 |
| Kijik · Kootznoowoo · Sealaska · Tyonek · Afognak · Tatitlek · Tyonek Native Corp · Southcentral Foundation · Urban Indian Center of Salt Lake · Native American Connections · Grand Ronde | 37 | 5 |

**Almost all of it is Alaska Native corporations and NHO operating groups.**
A tribal *government* site publishes governance, not a capability statement; the
*operating company* publishes the capability statement, because it is selling to
the federal government. That is a finding about where this data lives, and it
should shape the next pass: point it at the enterprise, not the nation.

---

## What was probed

**981 entity+host probes, 879 reached, 47 refused, 55 unreachable on every rung**
(https/http × www/apex × declared UA/browser headers × relaxed TLS).
**3,630 documents fetched, 3,529 distinct md5.** 23,787 surfaces recorded.

### Job 1 — the hosts the 2026-09-02 ruling released

All eight hard-listed sources plus the `METHOD_RESTRICTED_HOSTS` state on
navajo-nsn.gov were reached and harvested:

| host | reached | wp media items | surfaces | identifiers |
|---|---|---:|---:|---:|
| `akima.com` (NANA) | Y | — | 60 | **80** |
| `southernute-nsn.gov` | Y | 4,638 | 65 | 0 |
| `fcpotawatomi.com` | Y | 3,257 | 63 | 0 |
| `nana.com` | Y | 726 | 6 | 0 |
| `stillaguamish.com` | Y | 632 | 9 | 0 |
| `yakama.com` | Y | 457 | 36 | 0 |
| `colvilletribes.com` | Y | — | 3 | 0 |
| `ctuir.org` | Y | — | 4 | 0 |
| `chickasawbusinessnetwork.com` | Y | — | — | 0 |
| `navajo-nsn.gov` | Y | — | 6 | 0 |

Two of the eight are **not any entity's mapped URL in `cedar_web_map.csv`** —
`akima.com` is NANA's operating group and `chickasawbusinessnetwork.com` is the
Chickasaw Nation's business portal — so walking the web map would never have
reached them. They are bound to their owner by hand in `RELEASED_HOST_OWNERS`,
with the owner named rather than inferred. **`akima.com` alone produced 80 of
the pass's 151 distinct identifiers**, which is the whole argument for doing this by
host and not by map row.

Two more were being probed as the wrong host entirely: Colville's best 2xx URL
in the map is `colvillecasinos.com` and CTUIR's is `wildhorseresort.com`, so
`best_url` alone skipped both hosts the ruling actually names. The run now
dedupes on **(cedar_uid, host)**, not on cedar_uid, and a released host is
probed as itself.

### Job 2 — the CAGE/UEI gap

**930 of the 1,439 entities that had never been checked for a federal identifier
now carry a recorded outcome.** The honest remainder is **509**, and every one
of them lacks either a live site, a held identifier, or a clean contamination
flag — the three conditions the route needs.

| outcome | entities |
|---|---:|
| `HARVESTED` | 15 |
| `FOUND_NOT_EXTRACTED` | 142 |
| `CHECKED_ABSENT` | 219 |
| `REFUSED` | 47 |
| `ATTEMPTED_INCONCLUSIVE` | 558 |

**`ATTEMPTED_INCONCLUSIVE` is the largest bucket and that is the honest answer,
not a failure.** Its composition:

| cause | entities |
|---|---:|
| site reached, fewer than 2 of the 4 machine-readable routes answered | 336 |
| the site does not name the entity | 167 |
| host unreachable on every rung | 55 |

The 336 are `NOT_SEARCHED_MACHINE_READABLE` in the
`docs/HIDDEN_DATA_TECHNIQUES.md` sense: a negative from search alone is not a
negative, so they are not recorded as absences. **`verify` invariant V10 refuses
any `CHECKED_ABSENT` backed by fewer than two routes**, which is what keeps that
line honest rather than a matter of intention.

Routes that answered, per host: 0 → 382 · 1 → 267 · 2 → 36 · 3 → 201 · 4 → 95.
**310 of 981 hosts run WordPress and advertise 419,582 media documents between
them.** That is the surface the next pass should work, and it is already mapped.

### Job 3 — the institutions nobody had ever touched

| class | probed | of | reached | refused | unreachable |
|---|---:|---:|---:|---:|---:|
| BIE School | 175 | 185 | 157 | 14 | 4 |
| Native CDFI | 62 | 64 | 57 | 2 | 3 |
| Native Financial Institution | 29 | 29 | 23 | 3 | 3 |
| Tribal College or University | 37 | 37 | 35 | 1 | 1 |
| Urban Indian Organization | 43 | 43 | 40 | 2 | 1 |

**346 of the 358 institution-class entities were probed on all five dimensions**;
the 12 not probed have no URL of any kind in `cedar_web_map.csv` or the spine.
The BIE-school refusals are concentrated on shared state-education and diocesan
hosts whose robots ban every agent at the root — recorded per host in
`data/staging/capability_1114/refusals_1114.csv`.

Identifier yield from the institution classes is **three entities** (Southcentral
Foundation, Urban Indian Center of Salt Lake, Native American Connections) and
one identifier each. A
school does not publish a capability statement. That is a fact about the world,
and it is now measured rather than assumed.

---

## Outcomes, all five dimensions, 4,905 rows

`data/staging/capability_1114/coverage_1114.csv` — one row per (entity, host,
harvest_type), each naming the basis of its outcome.

| harvest type | HARVESTED | FOUND_NOT_EXTRACTED | CHECKED_ABSENT | REFUSED | ATTEMPTED_INCONCLUSIVE |
|---|---:|---:|---:|---:|---:|
| identifiers | 15 | 142 | 219 | 47 | 558 |
| enterprises | 0 | 211 | 189 | 47 | 534 |
| individual business | 0 | 150 | 225 | 47 | 559 |
| gaming | 0 | 215 | 195 | 47 | 524 |
| newsletter | 0 | 370 | 116 | 47 | 448 |

**`FOUND_NOT_EXTRACTED` is 1,088 cells and is the biggest thing this pass leaves
behind.** A newsletter archive located on a sitemap is not a newsletter in a
table, and calling it harvested is how a coverage number stops meaning anything.
The surfaces are all recorded, with the technique that found each one, in
`data/staging/capability_1114/surfaces_found.jsonl` (20,724 rows; the 23,787 in the summary is that spool de-duplicated against the CSV the first 47 hosts wrote before the spool existed) — the next
pass is an extraction, not a crawl.

---

## FOUR DEFECTS THIS PASS FOUND IN ITSELF, AND ONE IN THE RECORD

### 1. `CCBot` is not a name that means us — it cost four hosts

The first 47 hosts were probed with `CCBot` in `AGENT_TOKENS`. CCBot is Common
Crawl. Four hosts were recorded `REFUSED` on it — `omtribe.org`,
`sokaogonchippewa.com`, `wildhorseresort.com`, `ukb-nsn.gov`. Removed, the four
rows purged and re-run: **three of them genuinely name `ClaudeBot` and are
still refused; `wildhorseresort.com` was a false refusal and is now harvested.**

The rule the field guide gives — *ask robots as every name that means you* — has
a second half nobody had written down: **and no name that does not.** An
over-broad refusal is still a check that is not measuring its own name, and it
is invisible because it fails in the safe direction.

### 2. THE RECORD SAYS `elyshoshonetribe.com` REFUSES US. MEASURED TODAY, IT DOES NOT.

`review/tribal_vendor_list_registry_2026-08-26.csv` records
`ROBOTS_DISALLOW`, quoting *"robots.txt explicitly names and disallows
'ClaudeBot', 'anthropic-ai', 'GPTBot', 'Amazonbot' and others"*.
`review/1020_named_agent_robots_exposure.csv` rows 40–41 carry it forward, and
shard N purged the host's bodies on 2026-09-02 for it.

The live file, fetched 2026-09-02 and reproducible with one request, is the
Squarespace template. It is **one group**: thirty `User-agent:` lines —
`AI2Bot` … `ClaudeBot` … `AdsBot-Google-Mobile-Apps`, and then `User-agent: *`
— followed by a single shared rule block of **27 path-scoped `Disallow`
directives** (`/config`, `/search`, `/account`, `/api/`, `/static/` and twenty-two
query-parameter patterns). **There is no `Disallow: /` anywhere in the file, for
any agent.**

**Being named in a `User-agent:` list is not being disallowed.** ClaudeBot is
subject to exactly the rules the wildcard is subject to, and none of them
touches the pages in question.

This is the exact mirror of the defect the coverage audit caught in itself.
There, `"Disallow" in robots_note` fired on the string `no Disallow directives`
and manufactured 106 refusals against a true 54. Here, a *name* match
manufactured a refusal. Both are checks that ran, passed, and were not measuring
what their name says — and this one is the more expensive direction, because a
false refusal produces no artefact to trip over later. It reads as a completed
decision.

**What is NOT claimed.** The file may have changed since 2026-08-26 and nothing
on this machine can prove it did not. The claim is bounded: *as of 2026-09-02,
`elyshoshonetribe.com` does not disallow this agent from any path.*
`www.penobscotnation.org`, checked the same minute by the same code, **does**
carry `Disallow: /` for `ClaudeBot` and is correctly still refused. The parser
separates them, which is the evidence that it is reading groups and not strings.

Raised for the owner in `review/OWNER_DECISION_QUEUE.md`. **Nothing was
re-harvested from Ely Shoshone beyond the robots file and the home page on the
strength of this reading**; it is a proposal, not an action.

### 3. `small business` is in the capability vocabulary, and so is a JPEG

At 333 hosts the top-ranked capability candidates were
`Small-Business-Coaching-Flyer-768x994-1.jpg`,
`Small_Business_Academy_Crandon.jpg` and their thumbnails. Fourteen fetches per
host were going to images that cannot carry a CAGE.

Two fixes, both kept: images, video, fonts, CSS and JS are **never** candidates
(`NON_DOCUMENT_EXT`, plus a Content-Type guard for a server that lies about the
extension), and a **second pass** re-ranks the surfaces the first pass already
recorded — strong identifier vocabulary (`capability statement`, `CAGE`, `UEI`,
`DUNS`, `NAICS`, `SAM`, `8(a)`, `GSA schedule`, `contract vehicle`) ahead of
programme vocabulary (`small business`, `procurement`) — and fetches only what
was not fetched. The enumeration is the expensive half and it is already on
disk; re-crawling to fix a ranking would have been the wrong repair.

### 4. A FRAGMENT IS NOT A DOCUMENT — V7 fired on the real run

`www.tyonek.com/capabilities`, `/capabilities/`, `/capabilities#manufacturing`,
`/capabilities/#services`, `/capabilities/#construction` and six more were
treated as eleven documents. Eleven fetches, **the same md5 eleven times**, and
the same three NAICS codes booked eleven times as if they had eleven sources.

Identical in shape to the `?wpdmdl=` incident: green statuses, valid files, one
document. `verify` V7 caught it — the identical-md5 ceiling exists for exactly
this — and the answer was to **purge, not to raise the ceiling**. A ceiling
raised to accommodate a defect is a waiver wearing a gate's clothes.

`purge` collapsed **209 duplicate document rows across 158 (host, md5) pairs**
over two runs; **79 finding rows rode on a purged URL and went with them**;
3,630 documents and 3,529 distinct md5 remain. Every dropped row is kept with its reason in
`data/staging/capability_1114/purged_duplicate_documents.csv`. URLs are
defragmented at candidate time so it cannot recur.

### 5. `ex.map` yields in order, so a kill loses finished work

The first attempt wrote 66 rows while the pool had completed far more:
`ThreadPoolExecutor.map` buffers a result finished by worker 8 until worker 1's
straggler returns. "Flush per entity" was in the docstring and was not true of
the code. Replaced with `submit` + `as_completed`, so each entity is fsync'd the
moment it lands and a kill costs at most the in-flight hosts. A per-host
exception is caught and written as its own row rather than ending the run.

---

## THE FOUR THINGS THE RULING DOES NOT RELEASE, AND HOW EACH IS ENFORCED

| ruling item | enforcement | proven by |
|---|---|---|
| 1. technical access controls | `FORBIDDEN_PATH_PAT` — `/wp-admin`, `/Stagingsite`, `/login`, `/.env`, `/.git`, `/portal/`, `/intranet`, `/account/` and eleven more are **never requested**, on any host, released or not | `verify` V5 |
| 2. a natural person's data apart from their public role | the script **emits no such field at all**. There is no `owner_name`, `email`, `phone` or `address` column in anything it writes | `verify` V6, and `selftest` proves it fires |
| 3. EMMA/MSRB | `NON_TRIBAL_TERMS_HOSTS`, refused before robots is even fetched | the refusal is recorded with the reason |
| 4. Casino City and D-U-N-S | not fetched; the 31 DUNS values self-published by entities are held with `may_publish = N` | the review file carries the flag and its basis |

A **named-agent whole-site `Disallow`** is also still honoured. The ruling makes
a *terms page* an observation; it does not make a publisher's operational
refusal one. 47 host probes ended `REFUSED` on that basis and each row names the
token that refused.

---

## THE GATE

`verify` holds **ten invariants** and `selftest` proves six of them fire on a
synthetic violation and that a clean fixture exits 0.

| # | invariant |
|---|---|
| V1 | the CAGE and UEI validators must accept **every one of the 19,473 identifiers already in `cedar_identifier_ledger_final.csv`**. The rules are derived from that file, not remembered: 5,966 CAGE all length 5, none containing `I` or `O`, none all-alpha, 5,966/5,966 ending in a digit; 13,507 UEI all length 12, none with `I`/`O`, none starting `0`, all mixing letters and digits |
| V2 | the trap strings are rejected — `JONES` fails on the `O`, on carrying no digit, and on its last character |
| V3 | six robots fixtures, including `no Disallow directives` (must **not** ban), `/wp-admin/` (must not ban), a named `ClaudeBot` block beating a permissive wildcard (must ban), and a `Googlebot` block that does not bind us (must not ban) |
| V4 | the identity check never sees the URL; the City of Scotts Valley and Big Lagoon Elementary fixtures must be rejected; an all-stopword name gets its own verdict |
| V5 | technical-access paths are refused |
| V6 | no PII column in any output |
| V7 | the identical-md5 ceiling, per host |
| V8 | every finding carries a label, an evidence quote, a source URL and a token that passes its own validator |
| V9 | the six outcomes stay distinct; a seventh value fails |
| V10 | `CHECKED_ABSENT` requires ≥ 2 machine-readable routes to have answered |

`V1` is the one worth noticing: it is not a fixture somebody wrote, it is the
whole ledger. If a future edit loosens the charset rule, 19,473 rows say so.

---

## WHAT IS HONESTLY LEFT

1. **509 entities still `NEVER_CHECKED` for a federal identifier.** They fail
   one of the route's three conditions. Closing them means finding a live site,
   not running this script again.
2. **1088 `FOUND_NOT_EXTRACTED` cells** — surfaces located, nothing pulled into
   a table. The URLs and the technique that found each are on disk. This is an
   extraction task, not a crawl.
3. **49 host records still have a truncated media index.** `deepmedia` resumed
   250 of them — 139,097 outstanding media records, about 1,450 requests,
   **2,485 new CAP/BIZ surfaces**, of which the ranked harvest turned 80 into
   fetched documents and 7 into new identifiers. The 49 that remain exceed the
   200-page resume cap (meherrinnation.org advertises 13,564). The coverage row
   carries `media_index_truncated` so a reader can see which absences rest on a
   partial read: **89 of the 944 `CHECKED_ABSENT` cells** do, and all of them
   still clear V10 on the other three routes.
4. **167 entities whose site does not name them** — this pass adds to the 127
   already in `data/staging/native_business_sweep_1070/verdicts.csv` rather than
   resolving any. A site that does not name the entity is an identity problem,
   not a harvest problem.
5. **Nothing here is promoted into `data/clean/`.** The pass writes only
   `data/staging/capability_1114/` and one review file. Promotion of the 53
   corroborations into the assertion layer is an integrator action and needs a
   tier decision — and the tier is inherited from the source
   (`self_disclosed_web`), never from the exactness of the key.
