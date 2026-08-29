# Sourcing Strategy: roster first, sweep second

*Elijah, 2026-08-06:*

> "searching in usa spending by entity type is a good start or keywords, but
> there are some orgs like Tribalco which is Houlton Band of Maliseet Indians
> which I think didn't identify as native at all and wouldn't be caught with
> those filters — we had to investigate online. So that's why pulling first from
> these universes where we expect to see people makes sense, cuz we can fill in
> UEIs and such quickly, then it's worth doing broader pulls in case we missed
> anything when we have this large corpus of native entity and org names and
> codes to pull from."

That is the strategy. This file records it and the measurements that justify it.

---

## Why filters alone fail — the Tribalco case, measured

**Tribalco, LLC is owned by the Houlton Band of Maliseet Indians.** It carries 8
identifiers in our ledger and **3,152 contract rows worth $1.32 billion**.

| | Rows | Obligations | Share |
|---|---:|---:|---:|
| Reported **NO** Native preference | 2,263 | **$1,013.6M** | **77.0%** |
| Reported a Native preference | 889 | $302.2M | 23.0% |

**A set-aside filter would have found $302.2M and missed $1,013.6M of a single
tribally owned firm.**

The name does not help either. "Tribalco" contains the string *tribal*, which is
exactly the kind of token that a keyword sweep would flag — and that this project
has repeatedly proven cannot be trusted, since it also matches Tribal Energy
Alternatives (individually owned) and hundreds of place names. Being right about
Tribalco by keyword would have been luck, not method.

**The pattern generalises.** Across all prime contracting:

| | Rows | Obligations |
|---|---:|---:|
| We attribute to a Native entity, **no** Native preference reported | 177,544 | **$86.19B** |
| We attribute to a Native entity, preference reported | 110,604 | $55.33B |

**60.9% of the Native federal contracting dollars we can identify are invisible
to the federal preference fields.** Those fields are self-reported and
incomplete. Our `tribe_id` is determined — from hand rulings, firm-declared FPDS
parentage, and retrieved ownership pages. That asymmetry is the product.

This is also why every set-aside column is named `reported_*`. `is_8a` would
assert a fact; `reported_8a` states what the record claims.

---

## The order of operations

### 1. Roster first — pull where entities are guaranteed to be

Start from published universes. Every entity on these lists exists by
definition, so the only question is which identifier it uses — a fast,
high-yield lookup rather than an investigation.

| Roster | Source | Status |
|---|---|---|
| Federally recognised tribes | 91 FR 4102, annual | 575 parsed |
| ANCSA regional + village corporations | `entity_master.csv` | 12 + 173 |
| Native Hawaiian Organizations | NHOA / SBA 8(a) | 31 |
| Intertribal organisations | membership rosters | 55 |
| State-recognised tribes | CICD roster | 64 |
| Tribal colleges | AIHEC / BIE | **37 built** |
| Native CDFIs | CDFI Fund / CICD NAFI map | **64 built** (+29 Native Financial Institutions, a deliberate class split — a credit union is not automatically a CDFI) |
| BIE schools | BIE directory | **185 built** — 56 federally operated, which must NOT roll up to a tribe |
| Urban Indian Organizations | IHS Title V / NCUIH | **43 built** |

**This is the cheap half and it should always run first.** Identifiers found
this way are near-certain, and each one becomes a seed for the next stage.

### 2. Structure second — expand from what the roster found

Once an entity has one identifier, its family follows without further research:

- **FPDS `ultimate_parent_uei`** — the firm's own declaration of who owns it.
- **Brand families** — 106 learned from settled rulings. `alutiiq` → Afognak
  across 9 firms; ruling one settled the rest.
- **Cross-dataset propagation** — 1,374 identifier links that contracting or
  funding already knew and the ledger did not.

This stage found 622 spiderweb rulings and moved $45B, with no new sourcing.

### 3. Sweep last — broad pulls against the corpus we now have

Only now is a broad sweep worth its cost, because by this point Cedar Press
holds 1,310 entity names, thousands of aliases, 106 brand tokens and 20,559
identifiers. A sweep can be matched **against that corpus** instead of against
a keyword list — which is the difference between finding Tribalco and finding
three hundred false positives.

The Tribalco class — a tribally owned firm whose name and self-report reveal
nothing — is only ever caught here, or by hand.

---

## What this means for the filters we already used

The federal-funding forward-fill reproduced the spine's implicit population
filter, `recipient_type_names: indian_native_american_tribal_government`. That
was **correct for its purpose** — matching an existing population so the series
stayed comparable — and it was validated to +0.11% against a year we already
held.

But it carries the Tribalco blind spot by construction. A tribally owned *firm*
is not a tribal *government* and will not appear under that recipient type. So:

> **Federal funding coverage is complete for tribal governments and structurally
> incomplete for tribally owned businesses.** That is a property of the filter,
> not a finding about Native economic activity, and it must be stated wherever
> the totals are published.

The same caution already applies to HUD Section 184, which lends to individual
borrowers and therefore cannot appear in a tribal-recipient population at all.

---

## The rule

**Never conclude "not Native" from a filter.** A filter answers "did this record
self-identify," never "is this entity Native." Absence under a filter is a
property of the filter.

The only thing that settles it is the crosswalk — and the crosswalk is built by
roster, structure, and investigation, in that order.
