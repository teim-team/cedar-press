# The Cedar identifier standard

*Policy, hand-written, stable. **No counts live here** — every number about
identifiers is measured by `code/501_build_entity_inventory.py` into
`docs/ENTITY_INVENTORY.md`. A rule that carries its own statistics goes stale
and starts lying; this file carries only rules.*

Read this before writing anything that resolves, joins, or publishes an entity.

---

## 0. THE PERMANENT IDENTITY — read this before §1

**`cedar_uid` is the identity. Everything else, including the class-prefixed
handle, is an attribute.** Minted 2026-08-28 by `503_identity.py mint`
into `data/spine/cedar_identity_register.csv`, and materialised onto every
dataset by `503_identity.py stamp`.

    CE-1A7K3-MQ
    │  │     └─ TWO check characters, from two independent weightings
    │  └─ 5 chars, Crockford base32 (I, L, O, U are NOT in the alphabet)
    └─ namespace

**It encodes nothing on purpose.** Everything about an entity can change except
its identity:

- a **state-recognized tribe wins federal recognition** — its class changes and
  its handle changes (`TRBS-…` → `TRBF-…`); **`cedar_uid` does not.** Any time
  series keyed on the uid survives the event unbroken.
- a nation **renames** — a dated alias; same uid.
- a firm's **ownership changes** — a relationship edge; same uid.

An identifier that encodes class is an identifier that must be rewritten the day
the class changes, and rewriting an identity is the one unforgivable act in an
identity system. So the readable prefix stayed — agents genuinely use it, it
caught a zero-for-O typo, it kills the Elim defect — but it was **demoted from
identity to handle**.

### The check character is not decoration

`O`, `I`, `L` and `U` cannot appear in a valid uid, so the `BANN 0 YEEL KON`
class of transcription error is **unrepresentable**, not merely detectable.

The two trailing characters come from two independent weightings — one linear,
one quadratic — so an error that lands in the null space of the first is caught
by the second. **Measured on the live register:**

| error class | one check char | two check chars |
|---|---:|---:|
| single substitution | 95.5% (382/400) | **100% (1000/1000)** |
| adjacent transposition | partial | **100% (579/579)** |

The single-character version was built first and stress-tested the same hour;
95.5% is what a mod-32 character gives you and it is not good enough for an
identifier a customer transcribes. It was replaced before anything shipped —
**the whole reason to decide this now is that it is free now and expensive
later.** `503_identity.py` self-test asserts the properties on every run.

### THE RECLASSIFICATION RULE — decided now, before it is needed

When an entity's class changes (recognition granted, restored, terminated, or a
corporation reclassified):

1. **`cedar_uid` never changes.** Not for any reason. Ever.
2. The **old handle is retired to an alias** with `valid_to` set. It keeps
   resolving — historical filings use it and must keep working.
3. A **new handle is minted** in the new class and becomes current, with
   `valid_from`.
4. `entity_class` and `class_since_basis` are updated on the register row, with
   the citation (FR notice, court order) in the basis.
5. **No row is rewritten in any dataset.** They carry `cedar_uid`; they are
   already correct.

A uid is **never reused**, even after an entity is retired — same rule as script
numbers, for the same reason.

#### The contract is now enforced, not described (external review F6)

Until 2026-08-30 the four rules above were policy that the code did not
implement. `503_identity.py phase_mint` keyed the existing-uid lookup on the
**handle**, so a reclassification missed, **minted a second uid for an entity
that already had one**, and dropped the old handle from a register documented
as append-only. A buyer who had joined on a handle would have lost their
historical rows with no way to discover it.

`data/spine/cedar_handle_history.csv` retains every binding ever issued:

```
handle, cedar_uid, valid_from, valid_to, status, change_reason, recorded_date
```

- **`cedar_uid` is the only documented external join key.** Handles are
  display identifiers.
- **An old handle always resolves to the same uid**, through
  `503.register_map()` — the map `stamp` keys every dataset with. The history
  is read *first*, so the current register can only ever confirm it.
- **A retired handle pointed at a different entity RAISES** (`HandleReuse`).
  Not a warning: a reused handle resolves to the wrong entity in every
  downstream join and nothing later can detect it.
- **A uid is never dropped from the register.** An entity leaving the spine
  keeps its row, marked `register_status = retired_no_longer_in_spine`.

`503_identity.py verify` checks H1–H5 (one uid per handle forever; a
retirement carries a date; no uid dropped; at most one current handle per
uid; every register handle has a history row). `62_no_regression_check.py`
carries `handles_reused_or_double_bound` (MUST_BE_ZERO),
`handle_history_bindings` (MUST_NOT_FALL) and `sem_entities_uid_reassigned`
(MUST_BE_ZERO — a handle pointing at a different uid than it did at the
baseline is a silent re-keying).

Proven by `review/fixtures_D/fixture_F6_handle_contract.py`: it reclassifies a
real entity in a copy of the real spine, shows the uid does not move, shows
the retired handle still resolves through `register_map()`, and shows that
reusing it for a different entity raises.

### What this means for a customer

Every shipped dataset carries `cedar_uid` **in the file**. A buyer holding one
CSV can join it to any other Cedar dataset without holding the spine and without
a join whose semantics we control. Measured 2026-08-28: **125 tables,
3,007,088 of 3,007,806 entity-bearing rows (100.0%) carry a resolved uid.**
Blank means the handle is not a known entity — never "no entity", and never
guessed.

---

## 1. There is one identity system, and it is ours

**`cedar_uid` is the identity (see §0); the class-prefixed handle below is the
readable attribute of it.** Every Native entity has both, and nothing outside
them is an identity — everything else is an *attribute of* an entity.

Cedar IDs are class-prefixed and readable on sight:

| prefix | class |
|---|---|
| `TRBF` | Federally recognized tribe |
| `TRBS` | State-recognized tribe |
| `AKNF` | Federally recognized Alaska Native Village |
| `ANVC` | Alaska Native Village Corporation |
| `ANRC` | Alaska Native Regional Corporation |
| `NHO` | Native Hawaiian Organization |
| `ITO` | Intertribal Organization |
| `TCU` | Tribal College or University |
| `CDFI` | Native Community Development Financial Institution |
| `UIO` | Urban Indian Organization |
| `BIE` | BIE School |
| `CNSF` | Federal-level constituency entity |
| `CNSS` | State-level constituency entity |
| `SGVF` | Federal-level self-governance consortium |
| `CEDAR-ENT-` | Individually Native-owned business and other minted entities |

Those are ENTITY (hub) prefixes. Two prefixes name SUB-HUBS and are **not** entities — see §2:

| prefix | what it names | register |
|---|---|---|
| `CEDAR-NEST-nnnnnn-CC` | an enterprise a nation, ANC or NHO owns | `data/spine/cedar_nest_id_register.csv` |
| `CEDAR-PLACE-nnnnnn-CC` | a **physical place** an entity operates — gaming property, BIE school, IHS facility, BIA office, distinguished by a `place_class` COLUMN, never by the prefix | `data/spine/cedar_place_id_register.csv` |

*Verified against the spine 2026-08-28: every prefix above is present, and no
prefix in the spine is missing from this table. If you add a class, add its
prefix here — an undocumented prefix is how a reader concludes a class does not
exist.*

`tribe_id` is the canonical column name for a Cedar ID, for historical reasons.
It is **not** a tribe-only field — an NHO and an individually-owned firm both
carry one. Do not rename it casually; ~71 tables key on it.

### The CICD / lineage-A integer scheme is RETIRED as an identity

`lineageA_dofile_integer` (small integers: `192`, `201`, `343`) came in with the
HCI/CICD contracting lineage. It is **no longer an identity**. It survives in
exactly one role: **evidence of which vintage a row came from**, the same role
`extent_competed` plays for the FY2016/17 seam.

- Never mint a new row on it.
- Never join across it and Cedar IDs — the ranges overlap and *disagree*:
  `playground.do` says `307 → Stillaguamish`; the assistance lineage's `307` is
  `southern ute indian tribe`. A join across the seam silently mislabels.
- `attribution_status` declares whether a row is attributed, unattributed or
  ruled not Native. It is never blank. **Renamed 2026-09-01 from
  `tribe_id_scheme_resolved` by `code/843_retire_cicd_scheme.py`, which also
  dropped `tribe_id` and `tribe_id_scheme` from the table.** The
  split-an-entity hazard this bullet warned about is CLOSED, not renamed:
  measured 2026-09-02, there are zero `lineageA_dofile_integer` rows left
  (cedar_neid 553,106 · unattributed 146,717 · excluded_not_native 2,119 ·
  unresolved_native 13, over all 701,955 rows).

**Retiring it is a promotion, not a deletion** — see §5.

---

## 2. The hub model

    external identifiers  ─┐
    (UEI, CAGE, EIN, UBI)  │
                           ▼
      sub-hub  ────────►  ENTITY  ◄────────  collection rows
    (facility, property,  (Cedar ID)         (contracts, grants,
     docket, EIN filer)                       filings, deals …)

**The entity is the hub.** Everything associated with it hangs off the Cedar ID.

**Sub-hubs exist where a thing is complex enough to deserve its own record and
its own children.** A casino is the worked example: a facility has capacity
observations, employment observations, property locations, financing events and
licences of its own, *and* it belongs to an entity. Flattening it onto the
entity would lose the level at which most gaming facts are actually true.

Implemented sub-hubs today: `facility_id` (gaming_facilities), `property_id`
(gaming_property_locations, itself parent to `location_observation_id`),
`np_ein_entity_hub`, and the FERC docket filer layer.

**A PLACE IS A SUB-HUB, AND SINCE 2026-09-02 IT HAS ITS OWN CEDAR ID** — `CEDAR-PLACE-nnnnnn-CC`, ADR-030, minted by `code/1129_place_ids.py` into an append-only register. It exists because the source keys did not survive contact with a second source: `gaming_facilities.facility_id` is source-scoped (595 `CCP-`, 164 `VP-`, 15 `TPL-`, 13 `CED-`) and 26 clean tables inherit the split, and `bia_offices.OFFICEID` is **not unique** — `OFID0038` is both Salt River Agency and San Carlos Agency.

Three rules go with it, and they are the general shape of a sub-hub id:

1. **The source key is never overwritten.** Every migrated table keeps its `facility_id` / `OFFICEID` and gains `cedar_place_id` beside it. The source key is the evidence of where a row came from.
2. **The place is a sub-hub of the OPERATOR, and the operator can change without the place changing** — the D-U-N-S property, in the owner's own words: *"it's like our own D-U-N-S number, basically."* Where the operator is not a Cedar entity (a BIA office is federal) or is unresolved (a BIE school), `operator_cedar_uid` is BLANK and `operator_basis` says which. **Blank is never "no operator".**
3. **`place_class` is a column, never the prefix**, for the same reason `cedar_uid` encodes nothing: a gaming property that stops gaming must not have to be re-keyed.

**Hierarchy is a relationship, not an identity.** Corporate parentage is
genuinely ambiguous — a subsidiary is sometimes operated as a parent, ANCSA
corporations invert the usual shape, and the same firm appears as both in
different sources. So Cedar does **not** encode hierarchy in the id. Parentage
lives in `entity_relationships` / `parent_entity_id` as a typed, evidenced,
revisable claim. If you find yourself wanting to change an entity's id because
its ownership changed, you want a relationship edge instead.

---

## 3. External identifiers are attributes, and they are open-ended

`cedar_identifier_ledger_final.csv` is the register: one row per
(identifier_type, identifier, tribe_id) with a tier and a method.

Tracked today: **UEI**, **CAGE**, **EIN**. Expected and welcome as they are
collected: **state registration ids** (Washington UBI, state SOS numbers),
**NIGC ids**, **SAM legacy ids**, tribal charter numbers, licence numbers.

Adding a type requires nothing but a new `identifier_type` value and a tier
rationale. **Do not add a column per identifier type** — that is why this is a
long table and not a wide one, and it is what lets a new state's UBI land
without a schema change.

**An identifier is not a link.** The exactness of the KEY says nothing about the
correctness of the LINK. An EIN is an exact string and 821 EIN rows still sit at
tier B. `attribution_method` says *who* decided; `confidence_tier` says *what*
was decided. Read the sign before you inherit the authority.

---

## 4. Proprietary identifiers: hold internally, never publish

Some identifiers we may **use** but may not **redistribute**. They are real and
useful for QA and matching; they are not ours to hand out.

| identifier | source | status |
|---|---|---|
| DUNS / D&B fields | Dun & Bradstreet Open Data | **internal only** — attaches to every base award dated before 2022-04-04 |
| Casino City ids | Casino City | **internal only** — read for QA, never published |

Rules:

1. **Never ship a proprietary identifier as a column.** Not in `dist/`, not in a
   codebook, not in an export. Naming it in a caveat is fine and expected —
   saying *"we hold this and will not publish it"* is a disclosure, not a leak.
2. **Mark it in the column name where practical.** `duns_internal_only` and
   `dnb_open_data_restricted` are the established convention. Follow it.
3. **Where a table mixes both, ship a `_PUBLISHABLE` variant** rather than
   filtering at export time. `sam_prime_contracts_fy2000_2007_PUBLISHABLE.csv`
   is the pattern: the restriction is visible in the filename, so a later reader
   cannot pick the wrong file by accident.
4. **Facts derived from a proprietary id are usually fine; the id is not.**
   Contract facts publish. The D&B legal name and street address do not, in bulk.
5. A proprietary id may **never** be the only evidence for a published link. If
   removing it would leave the link unsupported, the link is not publishable.

### What "publishable" already means in practice

`cedar_publishable_identifiers.csv` is the enforced answer, and it is stricter
than the rules above require:

- **CAGE and UEI only.** EIN is held in the ledger and is **not** in the
  publishable set — an EIN identifies a filer and reaches further into an
  organization's affairs than a procurement id does.
- **Tier A only.** Every row is tier A; nothing tier B or below ships, which is
  the same rule as §5's "tier B may not key a dollar", applied to identity.

Publish from that table. Do not re-derive a publishable set by filtering the
full ledger yourself — the filter is the policy, and a second copy of it will
drift from this one.

---

## 5. Promoting a legacy id to a Cedar ID

A crosswalk from a legacy scheme is **a ruling, not a computation.** It is
adopted per-row, by match basis, never in one pass.

| match basis | disposition |
|---|---|
| **exact** | promote |
| **alias** | promote — the alias layer is first-class and evidenced |
| **distinctive spine token** | promote with review |
| **core resolver** | REVIEW. `core()` has folded the distinguishing word before — *NATIONAL EDUCATION ASSOCIATION → National **INDIAN** Education Association* |
| **containment** | **REFUSE.** AGENTS.md: containment may resolve an owner already named in evidence — never detect a match, and **never key a dollar** |
| **no candidate** | spine gap. Mint the entity or record the refusal; do not force a match |

**Keep the legacy value.** Promotion adds the Cedar ID and sets
`attribution_status`; it does not overwrite the original. The legacy value
is the evidence of provenance and it is how a mis-promotion is ever found.
**Superseded 2026-09-01 for the assistance table specifically:** the owner
retired the CICD scheme outright, so the legacy integer is no longer kept on
the row. It survives in
`data/spine/legacy/assistance_tribe_id_crosswalk.csv`, which is where a
mis-promotion is now found.

---

## 6. For an agent picking this up

Resolve an entity, in order. Stop at the first that succeeds:

1. **Cedar ID already on the row** — use it. Check `attribution_status`
   first; if it says anything but `cedar_neid`, you do not have a Cedar ID.
2. **Exact external identifier** — UEI, then CAGE, then EIN, via
   `cedar_identifier_ledger_final.csv`. Carry the row's tier forward; **do not
   upgrade it because the key was exact.**
3. **Alias** — `entity_aliases.csv`.
4. **Stop.** If none of those resolve it, the honest output is
   `unattributed` plus a refusal reason. A guessed entity is fabrication, and
   every expensive misattribution in this project began as a plausible guess.

Never:

- join on a legacy integer;
- strip a compound NEID suffix to make a join work (`AKNF-MTLKTL-00-TLNGHD` is
  canonical; its apparent "base" is not in the spine);
- let a tier-B link key a dollar figure;
- treat a `RULED` attribution method as a positive ruling — negative rulings are
  ruled too, and they are tier X.

**Related:** `docs/NATIVE_ENTITY_NUANCES.md` (the domain knowledge that resolves names — FR parentheticals, renames, enterprises, exclusions) ·  `docs/DATA_ARCHITECTURE.md` (what exists, generated) ·
`docs/ENTITY_INVENTORY.md` (coverage per entity, generated) · `AGENTS.md` (the
defect classes) · `docs/CEDAR_TAXONOMY.md` (entity classes).

## HUB AND SUB-HUB — the model, with the worked example that proves it

*Owner, 2026-09-01: "We just need the hub and sub-hubs. So Ho-Chunk means a
sub-hub, or Winnebago casino is a sub-hub. And then the hub is Winnebago
Tribe."*

```
HUB          Winnebago Tribe of Nebraska          TRBF-WNNBGO-00
  SUB-HUB    Ho-Chunk, Inc.        (holding co)   CKLKWJSYK9T5
    firm     All Native Services Company
    firm     All Native Synergies Company
    firm     Ho-Chunk Construction Management Services Co
    firm     ... and the rest of the family
  SUB-HUB    the tribe's casino    (facility)
  SUB-HUB    each SAM registration (UEI / CAGE)
```

A sub-hub is never a hub. `cedar_entity_spine.csv`'s declared grain already
says so — *"one row per canonical Native entity (hub). Sub-hubs (registrations,
facilities) are NEVER rows here."* Ho-Chunk Inc is a sub-hub of the Winnebago
Tribe, not a peer of it, and every dollar under it rolls up to the hub.

### The defect this model catches, found 2026-09-01

```
HO-CHUNK, INC.               CKLKWJSYK9T5  parent WINNEBAGO TRIBE OF NEBRASKA
                                           -> keyed Winnebago   uei_exact, 47 rows   CORRECT
HO-CHUNK CONSTRUCTION MGMT   S4LTC7CL8RW7  parent HO-CHUNK, INC. (FY2025-26)
                                           -> keyed Ho-Chunk    cage_exact, 6 rows   WRONG
```

**The subsidiary is keyed to a different nation than its own declared parent.**
`Ho-Chunk` (`TRBF-HOCHNK-00`) is the Ho-Chunk Nation of Wisconsin — a separate
federally recognized tribe that happens to share a name with the Winnebago
Tribe of Nebraska's holding company. Two tribes, one word.

Only $100,758 across 6 rows, so the money is trivial. **The shape is not.** It
is a name match beating a declared ownership chain, which is rule 11 in
`ENTITY_MATCH_RULES.md` inverted, and it is the exact confusion the owner
warned about at the start of the day: *"the highest owner can sometimes be say
Ho-Chunk Inc, not Winnebago Tribe — that's why the spiderweb approach is so
important."*

### Identifiers are the route to the hub, and they are messier than the theory

*Owner: "In theory one company should have one CAGE code, but sometimes they
could have multiple... they'll get a new CAGE technically as a new company for
the 8(a) pass-through stuff, but it's literally the same company."*

Measured in `fpds_uei_cage_map.csv`:

```
UEIs carrying a real CAGE                 6,840
  with MORE THAN ONE CAGE                    18   0.3%, never more than two
CAGE codes mapping to more than one UEI      15   never more than two
plus: literal string NAN as a cage_code   2,196 rows across 2,193 UEIs
```

So the idiosyncrasy is real and **rare** — the crosswalk is near 1:1 in
practice, which is why shard E's CAGE route linked seven ASRC subsidiaries
cleanly. The `NAN` rows are a far bigger hazard than the genuine one-to-many
cases, and they are a data-quality defect rather than a fact about the world.

**The point of any identifier is that it names THIS entity**, and none of them
names the hub directly. UEI and CAGE identify a registration; a registration is
a sub-hub. Getting from a sub-hub to its hub is the crosswalking work, and the
routes in order of strength are: the parent's own published subsidiary list
(shard E's 482 edges, 355 of them from audited filings under Alaska Statute
45.55.139), a declared parent UEI in FPDS, then anything name-based.

### Joining `fpds_uei_cage_map.csv`: two traps, both measured

**1. Do not pick the row with the most observations.** A UEI has several rows in
this map and they disagree about `cage_code` — the highest-observation row very
often has it **blank** while a sibling row carries the code.

Shard H's first lookup did exactly that and recovered **2 CAGEs for 45 firms**.
Re-ranking so that rows *having* a CAGE sort first took it to **23**, with no
additional network requests. Before that fix, `cedar_identifier_ledger_final.csv`
held **no CAGE at all for any of the 40 UEI-bearing firms in that class**.

```python
# WRONG - picks a blank cage_code most of the time
best = max(rows_for_uei, key=lambda r: int(r["n_observations"] or 0))

# RIGHT - prefer a row that actually carries the identifier
best = max(rows_for_uei,
           key=lambda r: (bool(clean_cage(r["cage_code"])),
                          int(r["n_observations"] or 0)))
```

**2. The literal string `NAN`** sits in `cage_code` on 2,196 rows spanning 2,193
UEIs. Excluding it from the index is necessary but **not sufficient**: shard H
excluded it correctly and still nearly shipped a join payload *reporting*
`map_cage_code: NAN` for Cherokee Components (UEI `DNLMR9ACL2J7`), because every
map row for that UEI carries the sentinel. No CAGE was minted, but a downstream
reader would have taken `NAN` as the firm's code. **Suppress the sentinel on
output, not just on lookup.**

### One registrant can carry two legal names with no shared token

UEI `SE78D4FEDA87` appears on CAGE `0SU10` as both **`CHEROKEE INFORMATION
SERVICES, INC.`** and **`AXSEUM, INC.`** — one registrant, one rename, zero
tokens in common. No name matcher reaches across that; the identifier does. It
is the ASRC argument in miniature, and it is the reason the map is worth its
defects.
