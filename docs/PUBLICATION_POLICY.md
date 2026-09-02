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
- `subaward_amount` overstating by **$21.21B (46.5%)** if summed unfiltered

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

Harmonizing changes what we publish. It does not change what we were allowed to
take.

Sources marked `TERMS_STATED_RESTRICTIVE` stay excluded by **every** route,
including the WordPress media API, the Wayback Machine, and a harmonized
derivative:

- **Confederated Colville** and **CTUIR / Umatilla** — long standing
- **Chickasaw** — its terms name company directories specifically (~622 firms)
- **NANA / Akima** — forbids automated use, scraping and aggregation. Cost:
  ~55 operating companies carrying UEI, CAGE, DUNS, NAICS and 8(a) status, the
  single highest-value refusal in the dataset. A sitemap enumeration was
  **stopped mid-run** when the terms were read, which was correct.
- **Southern Ute** (27 firms) and **Forest County Potawatomi** (18 firms)
- **Yakama**

This is a permission question, not a provenance question. The exclusions are
recorded with the quote that justifies each, so the boundary is auditable and
so a future OPT_IN request has something to point at. **Asking is the route
back in; a cleverer scrape is not.**

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

| source | rows | tribes | years | coverage |
|---|---:|---:|---|---:|
| DOL Form 5500 | 2,046 | 140 | 2009–2025 | **46%** |
| OSHA ITA 300A | 502 | 86 | 2016–2025 | **30%** |
| **`gaming_employment_observations` (pooled)** | **3,421** | **243** | **2008–2026** | **86%** |

**No single source clears half. The pooled table clears six sevenths.**

So the threshold applies to the **harmonized measure**, not to each input.
Dropping OSHA at 30% would remove tribes Form 5500 never sees, and the union is
the product. An input that is thin on its own but disjoint from the others
earns its place; an input that is thin AND redundant does not.

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
