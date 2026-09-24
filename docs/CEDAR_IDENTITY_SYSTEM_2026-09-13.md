# The Cedar identity system

*The owner's specification, given 2026-09-13. This file is the current
statement of the identity model, extended by the owner on 2026-09-23. Where it disagrees with an
earlier document, this one is later and wins; §7 lists every disagreement
found so far rather than leaving them for someone to trip over.*

Supersedes nothing outright. Read with `docs/IDENTIFIER_STANDARD.md` (the
`cedar_uid` contract), `docs/CEDAR_BUSINESS_ID_DECISION_2026-09-06.md` and
ADR-043 in `docs/ARCHITECTURE_DECISIONS.md`.

---

## 0. The model

Cedar uses two separate, permanent ID namespaces:

- **`CE-…`** — Cedar Entity ID, for a canonical Native entity
- **`CB-…`** — Cedar Business ID, for a distinct business or enterprise

They are identity anchors for the Cedar graph, not descriptive labels,
classifications, or source-system IDs.

---

## 1. Cedar Entity ID (`CE-…`)

Identifies **one canonical Native entity across all Cedar datasets**: a
federally recognized tribe, Alaska Native corporation, Native Hawaiian
organization, tribal government, tribal nonprofit, or other defined Native
entity class in the register.

Display form: **`CE-00001-6S`**

The number is an opaque serial and the final characters can serve as a
validation/check component. Neither portion encodes the entity's geography,
tribe type, ownership, legal status, dataset, or ordering significance. The ID
is deliberately non-semantic so it stays stable when Cedar improves a name,
reclassifies an entity, or corrects its attributes.

**The invariant:** a given `CE-…` must always resolve to the same impermeable
canonical entity. Never recycled. Never changed to make a dataset cleaner.

The entity register holds the current canonical name, entity class, aliases,
status, evidence, and source-specific identifiers. Source text might say
"Cherokee Nation Businesses"; a dataset row preserves that published party name
and separately links to the appropriate canonical Cedar entity.

Role-specific column names, where the role matters:

| Field | Meaning |
|---|---|
| `native_entity_uid` | The primary Native entity represented by the row |
| `recipient_native_entity_uid` | Native entity receiving an award, funding, or benefit |
| `owner_cedar_uid` | Native entity that owns or controls a business |
| `parent_cedar_uid` | Parent Native entity, where a sourced relationship exists |

A `CE-…` is **not** an award ID, deal ID, contract number, filing number,
Federal Register document ID, NAGPRA notice ID, bill ID, place ID, or person
ID.

---

## 2. Cedar Business ID (`CB-…`)

Identifies **one distinct business or enterprise**. Working format:

```
CB-0000001
```

Opaque, append-only, never reused, conveying no meaning about the business. A
check-character convention **can be added later**; the prefix and stable serial
are the important part.

A `CB-…` identifies the business itself, **not**:

- its owner
- a tribal citizenship or certification claim
- a UEI, CAGE, EIN, DUNS, SAM registration, or NAICS code
- a business location, facility, brand, project, contract, or dataset row
- a person or individual proprietor

Those are attributes or relationships recorded separately, with sources and
dates.

Business identity stays stable when the name, DBA, location, NAICS,
certification, owner, or registration changes. A dissolved or acquired business
keeps its historical `CB-…` record and status. A surviving legal business
retains its ID after a change; a genuinely new legal successor receives a new
one.

---

## 3. Why both are necessary

A Native entity can own or operate a business. That does not make the business
and the entity the same thing.

```
CE-00001-6S   Cherokee Nation                 the Native government
     │
     │  owns or controls   ← dated relationship, with a source
     ▼
CB-0000001    Cherokee Nation Businesses      a distinct operating enterprise
```

A contract, deal, lobbying filing, or subsidiary then links to the relevant
entity and/or business, depending on what the source actually identifies.

This prevents Cedar from collapsing an enterprise, subsidiary, holding company,
nonprofit, or Native-backed company into its tribal owner. It also lets Cedar
answer two distinct questions:

- *What activity is associated with this tribe?*
- *What contracts has this enterprise received?*

If a record legitimately refers to both, include both columns. **Do not place a
`CE-…` in a business-ID column or a `CB-…` in an entity-ID column.**

---

## 4. Relationships and external identifiers

Ownership, control, affiliation, and parent-child structure belong in
**relationship tables**, not inside either ID. A relationship record states:

- `owner_cedar_uid`
- `business_uid`
- relationship type — owner, parent, subsidiary, operator, affiliated entity
- effective dates where known
- source and confidence/evidence

UEI, CAGE, EIN, SAM identifiers, NAICS, state registrations, websites and
aliases belong in an **identifier or attribute ledger**. They change, go
missing, get shared, and get reported wrong by sources. Cedar IDs do not.

---

## 5. One framework, collection-scoped record namespaces

Owner direction, 2026-09-23: the two durable identity anchors sit within one shared
ID framework, not a universal event registry and not unrelated per-script schemes.
An ID belongs to one object type and one immutable declared grain. Existing issued
IDs remain stable, including CEDAR-NEST and NESTREL; illustrative DEAL/LOB prefixes
are not an instruction to rename existing IDs or mint replacements.

| Layer | Meaning |
|---|---|
| cedar_uid | Durable canonical Native entity; never a source tribe_id, business or event |
| business_uid / enterprise_id | Durable business/enterprise object; distinct from its affiliated entity |
| Collection record ID | Record/event in a declared collection and table grain |
| source_system + source_record_id | External issuing system and its original identifier |
| Relationship ID | Explicit evidence-backed connection between stable typed objects |
| Release ID | Published version/snapshot, not a record or entity |

Use (collection_id, table_id, record_id) as the global infrastructure reference.
A lobbying filing cannot be a deal merely because a string key matches; the two
connect through a validated canonical identity or an explicit relationship mapping.
A source-native bill/document/award ID remains source-native even when used as a
collection table's natural key. Do not silently promote it into Cedar identity.

Extend code/cedar_ids.py and the existing identity/key services as the central
contract and validator authority. Every namespace declares meaning, owner,
validation pattern, minting authority, collection/table scope and immutable grain.
Do not create per-script registries. Collection packages may mint only their
declared record IDs. Source rows never populate cedar_uid through a bare assignment
from tribe_id. Shared validators must reject wrong namespace/object type, duplicate
keys, immutable binding reassignment and undeclared cross-collection joins.

Changing names, classification, source evidence or affiliation does not change
stable IDs. Keep object bindings separate from mutable attributes. Derived samples
and aggregates do not acquire permanent IDs merely because a script emits them;
registration requires a real stable citation need. Legacy generic event_id fields
must be inventoried and scoped, not globally joined or bulk-renamed.

Cross-listing schools, colleges, CDFIs, nonprofits or businesses across collections
is collection membership, not an identity merge. Same-legal-object claims require
explicit evidence-gated relationships. Public affiliation wording and preservation
of precise source assertions follow docs/PUBLICATION_POLICY.md.

---

## 6. State, as of 2026-09-13

| | `CE-…` | `CB-…` |
|---|---|---|
| Specified | yes | yes |
| Minted | **yes** — 1,916 published in `public/data/cedar/register.json`, from `data/spine/cedar_identity_register.csv` | **no** — no `CB-` exists anywhere in `data/spine/` |
| Documented | `docs/IDENTIFIER_STANDARD.md` | this file, ADR-043, the 2026-09-06 decision |

`CE-00001-6S` is a real uid in the published register;
`src/features/grove/pressIdentity.test.js` in `cedar-press` asserts that, so the
site can never teach a form by inventing an entity.

---

## 7. Disagreements with earlier documents

Recorded rather than silently resolved. The terminal owns reconciling these in
the ADR; the site follows this specification because it is the latest word.

**7.1 Check characters on `CB-`.** ADR-043 says "the id carries the standard's
two check characters over the uid's alphabet (`CB-0001842-XQ`)". This
specification says the working format is `CB-0000001` and "a check-character
convention can be added later". The site shows `CB-0000001`. **If ADR-043's
form is the real one, say so and the site changes in one line.**

**7.2 Cherokee Nation Businesses is a business. Corrected 2026-09-13.**

This section previously claimed a disagreement here. There is none, and the
claim was mine, not the owner's. `docs/CEDAR_BUSINESS_ID_DECISION_2026-09-06.md`
carries a long blockquote of **a reviewer's proposal**, and inside it the
hedged line "Cherokee Nation Businesses *may* legitimately belong in the entity
register". I wrote that up as though the owner had taken that position and then
flagged it as conflicting with his own specification.

The owner's ruling, stated directly: **Cherokee Nation Businesses is not an
entity.** It is an operating enterprise, it takes a `CB-`, and the ownership
between it and the Cherokee Nation (`CE-00134-BX`) is a dated relationship row.
That is what §3 says and what the site teaches.

Do not re-raise this from the 2026-09-06 blockquote. A hedged suggestion inside
a quoted proposal is not a decision.

**7.3 No tribal-enterprise class exists in the register.** The published
register's eighteen classes contain no "tribal enterprise". An earlier draft of
the site's copy said the entity id names "an enterprise a nation owns", which
neither the register nor this specification supports. Corrected: enterprises are
`CB-`.

**7.4 The harmonized registry's own keys are not Cedar IDs.**
`business_source_id` (layer 1) and `entity_id` (layer 2) in
`cedar_source_registry/` are source-system and dataset identifiers under §5,
not the Cedar Business ID. The site briefly displayed `TBD-030:4033` as the
Cedar business id; that has been corrected. When `CB-` is minted, the harmonized
`entity_id` becomes a **link target**, not the identity.

---

## 8. What the terminal owns

1. **Mint the `CB-` register.** Seed per ADR-043 (the NEED register is its
   largest seed; the 45 `Individually Native-owned business` entities keep
   their uids and gain business ids with an equivalence row).
2. **Settle §7.1**, check characters or not, and record it here.
3. **Rename the role-specific columns** across published datasets to match §1
   and §4 where they do not already: `native_entity_uid`,
   `recipient_native_entity_uid`, `owner_cedar_uid`, `parent_cedar_uid`,
   `business_uid`.
4. **Audit for §3's hard rule** — no `CE-…` in a business-ID column, no `CB-…`
   in an entity-ID column — once both namespaces are populated.

When 1 and 2 are done, flip `IDENTIFIERS[1].live` to `true` in
`src/features/grove/pressIdentity.js`; a test fails until the page's liveness
line is updated with it.
