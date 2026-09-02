# What Cedar publishes, and what stays inside

*Written 2026-09-01. Live doc. Owner decision — this settles item 16.11 in the
decision queue and sets the default for every dataset.*

## The owner's framing

> *"It doesn't make sense to list every single source for every single row of
> data. They can check the data themselves if they don't believe it… To the
> extent where we said we'll acknowledge you because you shared this data,
> we'll do that. But besides that, it's not like we just are taking a tribe
> dataset of their vendors and just putting it on our website. We're making it
> all cohesive and harmonized into one dataset per category."*

## The product is harmonization, not redistribution

A tribe's TERO vendor list is not a Cedar dataset. It becomes **rows inside**
`native_owned_businesses.csv` — currently 2,393 rows from **18 certifying
authorities** — normalized to one schema, with a stated `identity_scope` so a
buyer can see that `enrolled_member_100pct` and `shareholder_descendant_or_spouse`
are different claims, keyed to the entity layer, and comparable across nations
for the first time.

That is the value, and it is not something any single source already offers.
Nobody publishes the harmonized view. **We are not competing with the tribes'
own pages and we are not a mirror of them.**

The same holds for every category: gaming, contracting, funding, lobbying,
nonprofits. One dataset per category, sources reconciled into it.

## Two layers, and only one of them ships

**The evidence layer is internal.** `review/` holds 369 files, and a full sweep
on 2026-09-01 found **63% of it is refusal logs, conflict registers, coverage
audits, probes and hand-validation samples**. That layer is how this project
catches its own errors, and today alone it caught:

- a de-duplication that would have destroyed **$8,291,124,113** of real
  obligations
- a Crown Heights Jewish organisation keyed to Council, Alaska
- a `$200B` benchmark "shortfall" that was a deflation artefact
- `subaward_amount` overstating by **$21.21B (86.9%)** if summed unfiltered

It stays, it stays internal, and it is not the customer-facing product.

**The published layer is the harmonized dataset**, plus:

1. **A source registry per dataset** — which authorities, which years, what
   each covers. `docs/datasets/*_sources.md` already does this. Dataset-level,
   not row-level.
2. **An acknowledgments section** naming the nations and organisations whose
   published data is in it. The owner asked for this specifically and it is the
   right thing on its own terms.
3. **A codebook** stating grain, keys, and what may and may not be summed —
   see `docs/MONEY_TOTALLING_RULES.md`.
4. **Row-level source columns where they are cheap and machine-generated**, so
   a buyer who wants to check can. Not a citation apparatus, and not a
   deliverable to hand-curate.

## What this changes in practice

**Stop treating a per-row verbatim quote as required output for everything.**
It is required where a *claim* is contestable — an entity attribution, a
self-published capacity figure, a recognition instrument. It is not required
for a row that is simply a normalized copy of a published record.

**Do not defer a dataset because its provenance apparatus is incomplete.** The
question is whether the DATA is right, not whether every row carries a
citation.

## THE ONE THING HARMONIZATION DOES NOT CURE

> **SUPERSEDED IN PART, 2026-09-02 — read
> `<!-- BEGIN TERMS-OWNER-RULING-2026-09-02 -->` at the foot of this file
> before acting on anything in this section.** The owner ruled that a tribal
> website's terms language does not block harvest, and the eight-source hard
> list below is **released for harvest of those entities' own public pages**.
> The section is kept because the *reasoning* — that harmonizing changes what
> we publish and not what we were allowed to take — is still exactly right, and
> because it names the four things the ruling did **not** touch. Read every
> "stay excluded" sentence below as **"was excluded until 2026-09-02"**.

Harmonizing changes what we publish. It does not change what we were allowed to
take.

~~Sources marked `TERMS_STATED_RESTRICTIVE` stay excluded by **every** route,
including the WordPress media API, the Wayback Machine, and a harmonized
derivative:~~ **Released 2026-09-02 for these entities' own public pages.** The
list is retained as the worklist the ruling creates — each of these is now a
harvest *candidate*, and the logged refusal is where to start:

- **Confederated Colville** and **CTUIR / Umatilla** — long standing
- **Chickasaw** — its terms name company directories specifically (~622 firms)
- **NANA / Akima** — forbids automated use, scraping and aggregation. Cost:
  ~55 operating companies carrying UEI, CAGE, DUNS, NAICS and 8(a) status, the
  single highest-value refusal in the dataset. A sitemap enumeration was
  **stopped mid-run** when the terms were read, which was correct.
- **Southern Ute** (27 firms) and **Forest County Potawatomi** (18 firms)
- **Yakama**

~~This is a permission question, not a provenance question. The exclusions are
recorded with the quote that justifies each, so the boundary is auditable and
so a future OPT_IN request has something to point at. **Asking is the route
back in; a cleverer scrape is not.**~~

**As ruled 2026-09-02:** it is a permission question, and the owner answered it
— he carries the publication risk on publicly served tribal content. The
recorded quotes keep their value: they are now the *observation* of what each
publisher stated, not the gate. **What did NOT move, and none of it is a terms
question:** technical access controls (nothing login-gated, no admin or staging
path, no misconfiguration); **a natural person's data held apart from their
public role** — the business rows may be harvested and `owner_name_raw`,
`email`, `phone` and `address_raw` still may not be published; **EMMA / MSRB**
with CUSIP Global Services as a second licensor, which is a third party's
contract and not a tribal publisher's preference; and the proprietary
identifiers **Casino City** and **D-U-N-S**, held internally and never shipped.

## Acknowledgment, concretely

Each published dataset carries a section naming the nations, tribal
enterprises, intertribal organisations and agencies whose published data it
draws on. Where a source asked to be credited a particular way, use their
wording. Where a source shared data directly rather than publishing it, say so.

This costs nothing and it is how a project that depends on tribal publication
should behave.

## Coverage thresholds — decide AFTER collation, and judge the pooled measure

*Owner, 2026-09-01: "Just because we have data doesn't mean we need to publish
it... if there's only data for like some threshold, don't need it because it's
a really messy dataset... but that should be decided after we've kind of
collated the data and cleaned it up."*

Right on both counts, and the deferral is the important half. **This decision is
not made now.** It is made once a category's sources are collated and cleaned,
because until then you are judging an input, not the product.

### The measured case that shows why

The owner's own example was gaming employment — his recollection was Form 5500
at about two thirds of tribes and OSHA at about nineteen. Measured
2026-09-01, against the 284 tribes that operate a gaming facility:

> **CORRECTED 2026-09-02, and the correction makes the argument stronger.** The
> table as first written was right about the shape and wrong about three things
> at once: the OSHA layer has grown, and **the pooled row mixed two universes** -
> it took its ROW count from the whole table and its coverage percentage from
> the gaming-tribe subset, so `3,421 / 243 / 86%` is not one measurement. Both
> halves re-derived below against **one** denominator. Re-derive, do not quote:
> `py -3 code/1116_ruling_propagation_2026_09_02.py derive`.

~~| source | rows | tribes | years | coverage |~~
~~| DOL Form 5500 | 2,046 | 140 | 2009–2025 | **46%** |~~
~~| OSHA ITA 300A | 502 | 86 | 2016–2025 | **30%** |~~
~~| **`gaming_employment_observations` (pooled)** | **3,421** | **243** | **2008–2026** | **86%** |~~

| source | rows | tribes | coverage of the 284 gaming tribes |
|---|---:|---:|---:|
| Census LEHD LODES | 373 | 183 | 64.4% |
| DOL Form 5500 | 1926 | 137 | 48.2% |
| OSHA ITA 300A | 1045 | 109 | 38.4% |
| NEPA / other documents | 7 | 4 | 1.4% |
| **pooled `gaming_employment_observations`** | **3351** | **236** | **83.1%** |

Measured against the **284 tribes with a `tribe_id` in `gaming_facilities.csv`**. State the universe: the whole table is 3421 rows over 243 tribes, and quoting the pooled ROW count from the unrestricted table beside a coverage percentage from the restricted one mixes two denominators in one line. **13 tribes are reached by OSHA and by NOTHING ELSE** - that, not OSHA's own share, is what an input has to beat to be dropped. An input thin on its own but disjoint from the others earns its place; one that is thin AND redundant does not.

**No single source clears two thirds. The pooled table clears five sixths.**

So the threshold applies to the **harmonized measure**, not to each input.
Dropping OSHA — the thinnest of the three at ~38% — would remove **13 tribes that
no other source in this table reaches at all**, and the union is the product. An
input that is thin on its own but disjoint from the others earns its place; an
input that is thin AND redundant does not. *(The disjointness is the argument,
and it is the number to re-derive when someone next proposes a drop: measure
`OSHA-only`, not OSHA's share.)*

### What to record instead of dropping

Where a measure is genuinely sparse, the honest move is to say so in the
codebook and let the buyer filter — *this observation is absent for this tribe
because the source does not cover it* is a fact, and Cedar already distinguishes
"attempted, none found" from "untouched" for exactly this reason. That is fine
at 20% of rows. At 80% it stops being a caveat and becomes the dataset's
character, and the measure should not ship.

There is no clean numeric rule and the owner did not pretend otherwise. What
makes the call possible is having the coverage table in front of you, which is
why every dataset doc carries one.

## Affiliation, not ownership, is the safer claim

*Owner, same conversation: "maybe every dataset we can tie to a tribe, so we
can say that they're tribally owned — like, this is the tribe they're a member
of, or something, or affiliated with. Affiliated with is better."*

He is right that the weaker word is the correct one, and the reason is in the
data. `native_owned_businesses.csv` records an `identity_scope` gradient
straight from what each certifying authority actually asserts:

```
enrolled_member_100pct  ->  enrolled_member_cskt  ->  any_native_oodham_and_local
  ->  any_native  ->  parent_asserted_subsidiary
  ->  shareholder_descendant_or_spouse  ->  vendor_relationship
```

A firm on a list whose bar is *shareholder descendant or spouse* is not a
tribally-owned firm, and a firm on a TERO **vendor** list may have no ownership
relationship at all. Calling the whole column "tribally owned" would flatten a
gradient the sources went to the trouble of stating.

**So the relation Cedar publishes is `affiliated_with` a named tribe, and the
`identity_scope` beside it says what the affiliation actually is.** The strong
claim stays available to anyone who filters for it; the dataset does not assert
it on rows that never supported it.

## Thirteen clean datasets first; linkage later; cross-validation NOW

*Owner, 2026-09-01. This is the architecture priority and it settles a
recurring temptation.*

> *"We just want thirteen clean datasets. And then you can combine them if you
> want by Native entity. But the linkages we can improve over time... we can
> use each dataset to fact check each other. If we see a deal that's published,
> we should see the federal contracting company change owners in the federal
> contracting data. Or if we see the federal contracting company change owners,
> that's not something publicly available — it's a deal we can report."*

### The priority

**Do not build cross-dataset linkage infrastructure yet.** Every dataset keys
to the entity layer (dataset 13); that is the only linkage required now.
IRS ↔ lobbying ↔ contracting joins are a later product, and the owner is right
that they get *easier* once each dataset is clean and its events are properly
identified. Chasing them first would mean linking dirty data.

### But cross-validation is not linkage, and it is available today

Two different things share one word. Linkage is a *feature* — a customer
joining datasets. Cross-validation is a *method*, and it runs on the data we
already hold:

- **A published deal implies an ownership change in the contracting data.** If
  the deal is real and the contracting record does not move, one of them is
  wrong. That is a free check on both.
- **An ownership change in the contracting data with no published deal is a
  deal Cedar can report.** This is the owner's sharpest point. FPDS parent
  changes are a matter of public record and nobody assembles them; a
  transaction visible only that way is genuinely new information, not a
  restatement of someone else's reporting.

### Measured 2026-09-01, as a first pass

```
attributed UEIs with >=2 years of parent data      2,807
parent changed between first and last year           630
  name overlaps a known deal in deals_classified     537   <- UPPER bound
  no deal anywhere in Cedar                           93   <- LOWER bound
deals_classified, entire dataset                     935
```

**Read those two bounds honestly.** The overlap test was a loose token match —
precisely the weak method `ENTITY_MATCH_RULES.md` refuses for attribution. It
will call a change "known" whenever any Ahtna deal shares a token with any
Ahtna subsidiary. So 537 is inflated, 93 is a floor, and the true count of
unexplained ownership changes sits between them.

Also: **a `parent_uei` change is not always an acquisition.** It can be a
re-registration, a data correction, or an internal reorganisation. 630 is a
candidate list, not 630 deals. Working it means checking each against the
parent's own filings — the route shard E proved, where an ANCSA corporation's
audited *Principles of Consolidation* note enumerates its subsidiaries by legal
name under Alaska Statute 45.55.139.

One name in the unexplained set is `BROADLEAF, INC.` — an ASRC Federal
operating company that only became visible at all because ASRC publishes its
CAGE code. Its parent moved and no deal records it.

### What this means for the datasets now

Nothing changes about the order of work: clean the thirteen. But **each
dataset's own consistency check should look sideways where a sibling can see
the same event**, because it is cheaper than a new source and it generates
rows rather than only validating them. The deals dataset gains candidates from
contracting; contracting gains a date and a counterparty from deals.

Keep the direction straight when recording: a candidate derived from a sibling
dataset is an **observation Cedar made**, not a claim some source published,
and its `inclusion_basis` should say so.

### Tested: a new CAGE is NOT a reliable signal of a change of hands

The owner's hypothesis, worth testing because it would have been a clean
discriminator: *"when a company changes hands, it's a complicated process, so
they do get issued a new CAGE code."*

Measured against the one unambiguous acquisition in Cedar's data:

```
BROADLEAF, INC.   cage 5RWC4   uei DGA4AQ4DJYY9   2017-2026   1,962 obs
```

**Broadleaf keeps CAGE 5RWC4 straight through the ASRC acquisition.** A
separate `BROADLEAF SERVICES, INC.` appears in 2025 on a different UEI and CAGE
8JY35, but that is a different legal entity, not a reissue. Every All Native
and Ho-Chunk company holds exactly one CAGE across its whole span too, which is
consistent with the reporting-change reading but tells us nothing new.

The hypothesis is plausible in DLA practice and probably turns on deal
structure — a stock purchase leaves the legal entity intact and its CAGE with
it, an asset purchase creates a new entity and a new CAGE. But **Cedar's data
does not support using CAGE change as a discriminator**, and one confirmed
counter-example is enough to keep it out of a rule.

The ultimate-parent-family test above remains the discriminator. Note also that
`fpds_uei_cage_map.csv` carries blank and literal-`NAN` CAGE values on the same
UEIs, so any CAGE-based reasoning has to clean that first.

<!-- BEGIN TERMS-SCOPE -->
## A terms restriction is scoped to the SOURCE that stated it, not to the nation

**Ruling, 2026-09-02.** The gaming web harvest excluded the **entire Navajo
Nation** — Fire Rock, Northern Edge, Flowing Water and Twin Arrows — because
one Navajo host, `navajoeconomy.org/business-regulatory/`, is recorded
`TERMS_STATED_RESTRICTIVE`. The casinos sit on different hosts entirely.

**That is over-compliance, and it misrepresents the publisher.** The owner's
principle is *"terms are a decision the publisher made, not an obstacle."* The
Navajo Nation made a decision about its business-regulatory page. It made no
decision about its gaming properties' sites. Treating one restrictive page as a
nation-wide prohibition invents a restriction the publisher never stated, and
would let a single page on any tribal domain erase that nation from the dataset.

**The rule:**

* A restriction attaches to the **host and path** where the terms were found.
* It does **not** propagate to other hosts operated by the same entity.
* It does **not** propagate from a subdomain to an apex, or the reverse, unless
  the terms themselves say so.
* ~~The eight hard-listed sources — Confederated Colville, CTUIR/Umatilla,
  Yakama, Chickasaw, NANA/Akima, Southern Ute, Forest County Potawatomi,
  Stillaguamish — remain excluded **by every route**, including Wayback, the
  WordPress media API and any harmonized derivative. That list names sources,
  and it is unchanged by this ruling.~~ **SUPERSEDED the same day** by the
  owner ruling at `<!-- BEGIN TERMS-OWNER-RULING-2026-09-02 -->`: all eight are
  released for harvest of their own public pages. *The rest of TERMS-SCOPE
  survives intact* — host-and-path scoping and the authorship distinction are
  what make the ruling applicable at all, and they still decide cases the
  ruling does not reach (a non-Native licensor, a third party's filing).
* Over-exclusion is recorded as a defect, not as caution. An entity absent for
  a restriction its publisher never stated is as wrong as one included against
  stated terms — it is simply wrong in the quieter direction.

`navajoeconomy.org` stays excluded. The Navajo gaming hosts do not.

### And it does not bind a third party's filing

**Same ruling, 2026-09-02, second application.** The EDGAR sweep held back real
transactions naming **NANA**, **Southern Ute** and **Chickasaw** — all three
hard-listed — and asked whether the exclusion reaches a filing those entities
did not write.

It does not. The restriction is a term **NANA set on NANA's website**. Trilogy
Metals' 10-K disclosing the Ambler Metals joint venture is *Trilogy's*
publication, filed with the SEC under a federal disclosure obligation; NANA has
no terms over it and set none. Reading the exclusion as "no material about this
entity from any source" would let a website footer suppress a public company's
mandatory securities disclosure, which is neither what the publisher decided
nor something they could decide.

* Excluded: anything **taken from** a hard-listed source's own publication —
  its site, its documents, its API, its Wayback captures, and any harmonized
  derivative of those.
* Not excluded: a **third party's** independent publication that happens to
  name them — an SEC filing, a Federal Register notice, a counterparty's
  annual report, a court record.
* The distinction is authorship, not subject matter.

The three held EDGAR families are releasable on that basis.
<!-- END TERMS-SCOPE -->

<!-- BEGIN TERMS-METHOD -->
## A restriction can attach to the METHOD rather than to the source

**Applied 2026-09-02 by `code/1096_navajo_unexclude_and_harvest.py`, while
carrying out the TERMS-SCOPE ruling above.** Recorded here because the ruling
could not be applied without inventing this state, and the next agent will hit
it again.

Cedar had exactly two dispositions for a source: **excluded by every route**, or
**open**. *(**SUPERSEDED 2026-09-02.** Both readings of the first are dead as of the owner ruling at the foot of this file, for a Native entity's own site — but the THREE-STATE lesson below survives it and is the durable part: ask whether a clause restricts the SOURCE, the CONTENT, or the METHOD, because only the first could ever justify dropping a host.)* Applying TERMS-SCOPE to the eight Navajo hosts produced a case that is
neither, and forcing it into either one would have been wrong in a different
direction each time.

`navajo-nsn.gov/Terms` was READ, not assumed. It says:

> "You may not obtain or attempt to obtain any materials or information through
> any means not intentionally made available or provided for through the Navajo
> Nation Web Sites."

That sentence does not forbid reading the site, and it does not restrict any
content. **It restricts the ROUTE.** A homepage the publisher links from its own
navigation is intentionally made available. An unlinked `/wp-json/wp/v2/pages`
index, a sitemap walk, a custom-post-type enumeration — techniques #3 and #4 in
`docs/HIDDEN_DATA_TECHNIQUES.md` — are precisely what the clause describes.

* Excluding the host entirely would be the over-compliance TERMS-SCOPE names as
  a defect: it invents a prohibition on content the publisher did not state.
* Harvesting it the way every other host is harvested would ignore a clause the
  publisher did state, in writing, on the page.

**The third state:** `980.METHOD_RESTRICTED_HOSTS`, keyed by host suffix, valued
with the verbatim clause. The homepage is fetched; the hidden-endpoint probe,
the sitemap/WP-REST page walk and the custom-post-type sweep are refused, and
the refusal is written into `host_probe.jsonl` as
`REFUSED_METHOD_RESTRICTED_BY_STATED_TERMS` carrying the quote — so the reason
is auditable from the data and not only from the code.

**The rule:**

* Read the terms before deciding, per host. `1096` did this for all seven Navajo
  hosts: four casino hosts return robots.txt 200 with **zero** Disallow
  directives and carry no restrictive language, `nnooc.org` returns robots 404
  (**allowed**, not blocked — `PULL_DISCIPLINE.md`'s 22 phantom blocks came from
  reading a non-200 as `disallow_all`), and only the two `navajo-nsn.gov` hosts
  state anything.
* Ask what the clause restricts: the **source**, the **content**, or the
  **method**. Only the first justifies excluding a host.
* A method restriction is honoured by dropping the routes it names, not by
  dropping the host.
* **A cached refusal is not a completed fetch.** The seven hosts each carried an
  `EXCLUDED_TERMS_STATED_RESTRICTIVE` record in `host_probe.jsonl`, and 980
  builds its resume set from that file — so a re-run would have skipped all
  seven silently, printing nothing. When a restriction is lifted, the cached
  refusals have to be retired or the correction never takes effect. They were
  MOVED to `host_probe_retired_navajo_exclusions_2026-09-02.jsonl`, not deleted:
  the refusal happened, and the record of it is the evidence the correction was
  needed.

**Result:** `navajoeconomy.org` stays excluded. The other seven were harvested
on 2026-09-02 — 37 requests, 20 pages, HTTP 200 throughout — and produced **9
observations** for the Navajo Nation, its first rows in the web-harvest layer:
gaming-machine counts published by Fire Rock (900), Northern Edge (750), the
Nation's gaming enterprise (2,800) and Flowing Water, plus four operating-hours
statements. All nine are `TRIBE_LEVEL_MULTI_FACILITY_NOT_DISAMBIGUATED`, because
the Nation operates four facilities and 980 keys attribution by the tribe's
facility count rather than by the host.
<!-- END TERMS-METHOD -->

<!-- BEGIN TERMS-OWNER-RULING-2026-09-02 -->
## Owner ruling, 2026-09-02: a tribal website's terms language does not block harvest

> *"So tribal websites, I actually don't care if they say it does scrape.
> Because if it's publicly available and you can scrape it, scrape it."*

This **supersedes** the `TERMS_STATED_RESTRICTIVE` exclusion as it applied to
Native entities' own websites. The eight-source hard list — Confederated
Colville, CTUIR/Umatilla, Yakama, Chickasaw, NANA/Akima, Southern Ute, Forest
County Potawatomi, Stillaguamish — is **released for harvest of their own
public web pages**. So is the `METHOD_RESTRICTED_HOSTS` state invented for
navajo-nsn.gov.

The reasoning is the owner's and it is his to make: this is publicly served
content, he carries the publication risk, and a reuse restriction in a terms
page is a licensing question rather than a technical boundary.

### What this ruling does NOT touch

Four things are unchanged, and none of them is a terms question:

1. **Technical access controls.** No login-gated content, no admin or staging
   paths, no exploiting a misconfiguration. `/Stagingsite/` stays refused.
   Publicly *reachable* is not the same as publicly *served*.
2. **A natural person's data held apart from their public role** — home
   address, personal email or phone, DOB, SSN/TIN. This is a privacy line, not
   a licensing one, and the owner has drawn it himself: a firm's name is not
   PII, a person's home phone is. The Southern Ute file purged today carried
   `owner_name_raw`, `email`, `phone` and `address_raw`; **under this ruling
   the business rows may be harvested and those four fields still may not be
   published.**
3. **Non-tribal licensors.** EMMA/MSRB bars redistribution of its output "sold
   or free of charge" and names "any manual process", with CUSIP Global
   Services as a second licensor. That is a contract with a third party, not a
   tribal publisher's preference, and it stands.
4. **Proprietary identifiers** — Casino City, D-U-N-S — held internally, never
   shipped.

### What changes in practice

* `source_terms_status = TERMS_STATED_RESTRICTIVE` on a Native entity's own
  site becomes a **recorded observation, not a gate**. Keep recording it; stop
  refusing on it.
* Robots `Disallow` and named-agent refusals: continue to record them, and
  treat them as the publisher's operational preference rather than a
  prohibition on public pages. Rate-limit politely and identify honestly.
* Every previously refused Native-entity host is now a **harvest candidate**,
  and the refusals already logged are the worklist.
<!-- END TERMS-OWNER-RULING-2026-09-02 -->

<!-- BEGIN TERMS-OWNER-RULING-PUBLISH-2026-09-02 -->

## OWNER RULING 2026-09-02 (second) — the harvest ruling COVERS PUBLICATION

The first ruling of 2026-09-02 released **harvesting** a Native entity's own
public pages regardless of a terms statement. It did not say what that meant
for **publishing** what was harvested, and the gap was real: 1,827 of 4,273
`native_owned_businesses` rows sat `publishable = N` on terms grounds after
being lawfully harvested under the first ruling. Asked directly, the owner
ruled:

> **Publish all harvested rows.** If a tribe puts its business directory on its
> own public website, Cedar may republish the listing.

So `PERMISSION:TERMS_STATED_RESTRICTIVE`, `PERMISSION:NO_TERMS_PAGE_SERVED` and
`PERMISSION:TERMS_STATED_COPYRIGHT_ONLY` no longer withhold a row **whose
source is the entity's own public page**. 1,090 + 175 + 17 rows are released.

### WHAT THIS RULING DOES NOT TOUCH

It moves one gate and no others. Every one of these still withholds, and a
reader reaching for this ruling to justify one of them has misread it:

1. **Technical access controls.** Login-gated content, admin or staging paths
   (`/Stagingsite/` stays refused), anything reached by exploiting a
   misconfiguration. The ruling is about a page a tribe chose to publish.
2. **A natural person's data held apart from their public role** — home
   address, personal email or phone, DOB, SSN/TIN. This is not theoretical
   here: four directory parsers in this session produced plausible wrong
   output, and the CTUIR one would have published the office's own phone
   number, four named staff and five named TERO commissioners **as firms**.
   `cedar_publication.NEVER` drops those as COLUMNS as of today.
3. **A third party's terms.** EMMA/MSRB is a contract with MSRB and CUSIP
   Global Services, not a tribal publisher, and stays refused. The ruling
   reaches an entity's OWN publications, not a vendor's database about them.
4. **Proprietary identifiers.** Casino City and D-U-N-S are licensed to Cedar
   for internal use and never ship, in any dataset, at any tier.

### THE DISTINCTION THAT MAKES THIS COHERENT

A tribe publishing its own business directory has already decided that
information is public. Cedar republishing it adds reach, not disclosure. That
reasoning does not extend to a source that never made that choice — which is
why 1 through 4 above are unaffected, and why the ruling is scoped to the
entity's own pages rather than to "anything we managed to fetch".

<!-- END TERMS-OWNER-RULING-PUBLISH-2026-09-02 -->
