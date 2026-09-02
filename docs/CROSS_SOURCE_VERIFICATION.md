# Cross-Source Verification

*Elijah, 2026-08-06:* **"to the extent we can use different federal sources to
sanity check we should."**

A standing rule, not a per-dataset instruction. Every build reads this.

---

## The rule

**One federal source is a claim. Two independent federal sources that agree is a
verification. Two that disagree is a finding.**

Where a fact can be reached through more than one federal trace, reach it more
than one way and record which sources confirm it. Where they conflict, record
**both** with their sources and flag it to `review/` — never silently pick the
one that looks better.

This is the same discipline as the two-leg evidence standard on ownership
(firm-declared FPDS parentage AND a retrieved document = tier A; one leg = tier
B). Cross-source verification extends it from entities to facts.

---

## The column

Every dataset that can support it carries `corroborating_sources` — a list of
the independent federal sources confirming the row — and reports its
distribution. A row confirmed by three federal sources is a different asset than
one resting on a single scrape, and a subscriber is entitled to know which they
have.

---

## Independent traces we already hold

| Fact | Traces |
|---|---|
| A Class III gaming property exists | NIGC location list · Federal Register compact approval · BIA land-into-trust / gaming-eligibility determination · NIGC management contract approval · IGRA §20 determination |
| A firm is tribally owned | FPDS `ultimate_parent_uei` · SAM registration · retrieved ownership page · 8(a) participation record |
| A tribe is federally recognised | Federal Register annual list · BIA tribal leaders directory · recognition-history docket |
| A dollar amount moved | USAspending transaction · agency budget justification · recipient's own audited financials |
| An entity's identifiers | BGOV crosswalk (hand-checked, outranks all) · CICD connector · SAM · cross-dataset propagation |

---

## The direction that finds what is missing

A **count** comparison tells you a gap exists. A **roster diff** tells you which
row. Always prefer the roster.

Three outcomes, all of them informative:

- `IN_SOURCE_NOT_IN_CEDAR` — usually the highest-value output of a build. We are
  missing something a published federal universe says exists.
- `IN_CEDAR_NOT_IN_SOURCE` — investigate before concluding. Duplicate, stale
  status, name variant, consolidated reporting, or a genuine entity outside that
  source's scope.
- `MATCHED` — with the match basis recorded.

---

## The ceiling that must travel with every diff

**A federal source's universe is defined by its statute, not by reality.**

Absence from a source is a property of the source. Examples measured on this
project:

- **NIGC** covers Class II and Class III gaming *on Indian lands*. A tribally
  owned casino operating under a commercial licence off Indian lands will never
  appear. NIGC is a floor for the IGRA subset, not a ceiling for Cedar Press.
- **Form 990** excludes tribal governments under **IRC §7871**. Shakopee, San
  Manuel, Tulalip, Muckleshoot, Morongo, Pechanga and Seminole return HTTP 404
  on ProPublica — not because they do not give, but because they are not in the
  universe. SMSC states it has given over $400M and publishes no grantee list.
- **HUD Section 184** lends to individual borrowers, so zero rows in a
  tribal-recipient population is a property of the filter.
- **Federal set-aside fields** are self-reported: 60.9% of the Native
  contracting dollars we can identify report no Native preference at all.

So the standing prohibition holds without exception:

> **Never conclude "does not exist" or "not Native" from absence in one source.**

---

## When sources disagree

Authority order, unchanged:

1. Elijah's hand-checked work — BGOV crosswalk, ESM/HCI, rulings
2. A retrieved primary document
3. A firm's or agency's own declaration
4. Algorithmic inference — never publishes on its own

A disagreement between two sources at the same level goes to `review/` with both
values, both URLs, and no resolution. An unresolved conflict recorded honestly
is worth more than a resolved one guessed.

---

## Cross-agent verification

The same principle applies to our own work. When two builds could each produce
the same entity, one holds its rows out as a **cross-check** rather than
publishing competing proposals — as the philanthropy build did with 34 tribal
colleges belonging to the TCU class. Agreement between two independent internal
methods is evidence; a silent merge destroys it.
