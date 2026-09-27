# The Cedar identifier standard

> 2026-09-24 retirement correction: the older passages below describe the
> pre-retirement handle system. The **CICD retirement contract** at the end of
> this document controls wherever a historical passage conflicts with it.

*Policy plus a dated retirement audit. Re-measure snapshot counts before release.
`code/audit_retired_ids.py` reproduces retired-value counts without editing data.*

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
3. No new class-prefixed handle is minted. Record the class change and keep
   the old handle as read-only provenance.
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

`graveyard/cicd/cedar_handle_history.csv` and
`data/spine/cedar_retired_neid_crosswalk.csv` retain historical bindings:

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

### A second register for businesses, decided 2026-09-06

`cedar_uid` identifies the canonical Native institution and nothing else. A
business that is not one (an operating subsidiary, a privately owned Native
firm, a vendor, a deal target) gets a **Cedar Business ID**, `CB-`, from a
separate register with the same contract: encodes nothing, never changes,
never reused, never dropped, never a substitute for a uid. Ownership is a
relationship; registrations are attributes; name changes are aliases. The
decision and its reconciliation with the NEED, place and identifier ledgers
are in `docs/CEDAR_BUSINESS_ID_DECISION_2026-09-06.md` (ADR-043). It
supersedes ADR-008.

---

## 1. There is one identity system, and it is ours

**`cedar_uid` is the identity.** The class-prefixed handles below are
retired historical keys, not current identity attributes or new issuance
targets. New Native entities do not receive one. Other objects have
separately typed identifiers.

Historical Cedar handles were class-prefixed and readable on sight:

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
| `CEDAR-ENT-` | Historical individually Native-owned business surrogate; retired for new issuance |

Those are ENTITY (hub) prefixes. Two prefixes name SUB-HUBS and are **not** entities — see §2:

| prefix | what it names | register |
|---|---|---|
| `CEDAR-NEST-nnnnnn-CC` | an enterprise a nation, ANC or NHO owns. The collection was renamed NEST → NEED on 2026-09-10 and the prefix was NOT: these ids are issued, and a prefix is never rewritten — `docs/NEED_RENAME_2026-09-10.md` | `data/spine/cedar_need_id_register.csv` |
| `CEDAR-PLACE-nnnnnn-CC` | a **physical place** an entity operates — gaming property, BIE school, IHS facility, BIA office, distinguished by a `place_class` COLUMN, never by the prefix | `data/spine/cedar_place_id_register.csv` |

*This is a historical vocabulary, not a minting template. The original
`tribe_id` columns in internal tables hold retired handles. They are never
canonical `cedar_uid` fields and cannot be copied into new releases.*

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

---

## CICD retirement contract and Gaming handoff (2026-09-24)

This section supersedes the pre-retirement language above that calls a
class-prefixed handle a current attribute or proposes a new handle on
reclassification. The source finding is
`docs/GAMING_ID_CONTRACT_REQUEST.md` on `claude/gaming-intelligence`.
Code review used the isolated `codex/cicd-id-retirement-audit` worktree from
`origin/pr122` (`3195e70`), `origin/main` (`6d445f4`), the active Press
workspace (`49c846a`), the Gaming worktree (`9ab9efc` at inspection), and
Lumecon Data (`f882fb1`). The populated active Press data tree was read-only;
Claude's branch and uncommitted Gaming work were untouched.
**Gaming is a Cedar Grove collection, outside Cedar Press's twelve-collection
launch set.** The old `dist/customer/gaming.csv` is a historical Press artifact,
not authorization for a new Press Gaming release.

### Allowed IDs and boundaries

| Object | New canonical ID and authority | Historical/source values |
|---|---|---|
| Native entity | `cedar_uid = CE-xxxxx-CC`, `503_identity.mint`; exact register membership and check characters required | `TRBF`, `TRBS`, `AKNF`, `ANVC`, `ANRC`, `CNSF`, `CNSS`, `NHO`, `ITO`, `TCU`, `CDFI`, `BIE`, `UIO`, `SGVF`, `CEDAR-ENT` are read-only handles, never `cedar_uid` |
| Legal business/operator | `CB-` in the separate Cedar Business Register, with its own reviewed binding | A business is not made a Native entity by ownership |
| Tribally owned enterprise sub-hub | Existing `CEDAR-NEST-nnnnnn-CC`, ordinal from `cedar_ids.allocate`, check characters from `503_identity`; append-only NEED register | NEED affiliation remains on its separate publication hold. `CEDAR-HOLD` is retired and unissued |
| Physical gaming facility | Existing `CEDAR-PLACE-nnnnnn-CC`, allocated through `code/1129_place_ids.py` using the shared `cedar_ids` counter and `503_identity` checks; bind only after place-identity review | `CCP-`, `VP-`, `TPL-`, `CEDAR-FAC-` and `CED-` are source-scoped/internal facility keys. Keep them beside the canonical place ID in an internal crosswalk, never as the public Gaming facility ID. `CEDAR-FAC` may still name an internal source row; it is not a second physical-place namespace |
| Compact/agreement | Existing `CEDAR-CONTRACT` allocator for a Cedar-authored stable compact object, with source compact number retained | Do not derive identity from mutable title, state or tribe name |
| Payment, license issuance, decision, regulatory/environmental/litigation event | Existing `CEDAR-EVENT` allocator for a Cedar-authored event; retain any stable official source event ID separately | Existing `GLD` values are historical Gaming decision source IDs, not a new global event namespace |
| Labor, revenue, capacity, amenity and source observation | Existing `CEDAR-OBS` allocator for a Cedar-authored observation; `CEDAR-SRC` for a source record and `CEDAR-REL` for an evidenced relationship | Preserve official filing/transaction keys and their row grain; do not convert an aggregate regional observation into a tribe or facility observation |

The fifteen `GREV`, `GPAY`, `GREG`, etc. hashes currently proposed in
`claude/gaming-intelligence:code/gaming_grove.py` are **not registered Cedar
namespaces**. Its `PROV-` values are structural dry-run markers only. Claude
must replace those public IDs with registered object IDs, and must retain a
stable source-key crosswalk so rebuilds reuse the same issued ID. A hash of
source keys may be an internal deduplication key, never independent mint
authority. `PROV-`, `CCP-`, `VP-`, `TPL-` and retired class handles are rejected
from canonical ID columns, governed manifests, APIs and customer outputs.

For a legacy entity handle, call
`cedar_publication.resolve_retired_entity_handle(handle)`. It reads the
historical binding vocabulary and returns only one exact `CE-` binding;
unknown or contested values raise. Keep the original in an internal
provenance crosswalk. Never prefix-strip or manufacture a CE value. The
crosswalk is a reader, not an allocator or publication field.

### Evidence, enforcement and remaining release blocker

The live Cedar Press workspace measured on 2026-09-24 has 1,916 rows and
1,916 distinct `CE-` values in `data/spine/cedar_identity_register.csv`, with
zero non-CE values in `cedar_uid`. The historical
`data/spine/cedar_retired_neid_crosswalk.csv` has 1,555 rows and 1,555
distinct retired values; `graveyard/cicd/cedar_handle_history.csv` has 1,555
rows. The place register has 1,051 source-key binding rows for 997 distinct
places; 771 rows / 717 distinct place IDs are classed `GAMING_PROPERTY`.
The NEED register has 6,089 distinct `CEDAR-NEST` IDs. Multiple source keys
for one place are expected; a new facility ID per source row would duplicate
one property.

The historical spine `data/spine/cedar_entity_spine.csv` has 1,555 rows;
its `tribe_id` column contains `TRBF` 348, `AKNF` 229, `NHO` 210, `BIE` 185,
`ANVC` 179, `CDFI` 93, `TRBS` 64, `ITO` 56, `CEDAR-ENT` 45, `UIO` 43,
`TCU` 37, `SGVF` 29, `CNSF` 22, `ANRC` 12 and `CNSS` 3. These are historical
handles, not `cedar_uid`. The 787-row
`data/clean/gaming_facilities.csv` has `facility_id` `CCP` 595, `VP` 164,
`TPL` 15 and `CEDAR-FAC` 13; its `tribe_id` has `TRBF` 739, `CNSF` 43 and
`AKNF` 3, while `entity_id` has `TRBF` 226 and `AKNF` 2. In the place register,
`source_key` has `CCP` 595, `VP` 148, `TPL` 15 and `CEDAR-FAC` 13. The 16
`VP` facility rows without a corresponding `VP` source-key binding require
identity review or an explicit unresolved status before Gaming publication;
the count difference alone does not authorize a merge or a new place ID.
They are `VP-0063`, `VP-0101`, `VP-0102`, `VP-0109`, `VP-0110`, `VP-0241`,
`VP-0242`, `VP-0243`, `VP-0254`, `VP-0255`, `VP-0335`, `VP-0336`, `VP-0337`,
`VP-0338`, `VP-0405` and `VP-0406`.

`cedar_ids.allocate`, `format_id` and `declare_static_block` now reject every
retired issuance prefix, including the previously allocatable `CEDAR-ENT`
and `CEDAR-HOLD`. `cedar_ids.class_prefix` and `reclassify` refuse historical
issuance; `historical_class_prefix` is read-only. The old inline minting script
`426_mint_bristol_bay_spine_entities.py` refuse new class-prefixed handles.
The same refusal closes the historical `52`, `61`, `73 add`, `75`, `163` and `524 promote`
write entry points; source evidence and read-only measurements remain intact.
These safeguards exist on this audit branch only until integrated. At the
inspection point, `origin/main` and the active Press/Gaming worktrees still
carry older issuance code, so **repository-wide zero active minting is not yet
proved**. Cherry-pick/merge this commit and rerun the guards on each release
branch before lifting the Gaming ID hold.
The legacy spine and clean tables still contain old handles as historical
input, source keys and compatibility evidence; their mere presence there is
not a new issuance. The `code/audit_retired_ids.py` CSV inventory prints exact
path, column, prefix, occurrence count, row count and example for every file
under the supplied roots, including ignored files. Run it against `data/spine`,
`data/clean`, `dist/customer`, `dist/review/samples`, and
`public/data/cedar/samples` in the populated workspace before each release.

The independent `1165_delivered_publication_audit.py` full scan found zero
**retired Native-handle** violations in 16 delivered CSVs, including an old
787-row Gaming CSV. That check did not cover vendor facility IDs. The original
`1169_release_verify.py --json` gate found zero retired Native handles in
17 customer CSVs and 476 sample files, but **failed** the customer database:
15 of 280 tables still have 18 retired-scheme columns containing 13,549
populated rows. It also marked the no-regression and semantic checks
`NOT_ESTABLISHED`. Thus no claim of complete retirement or a green Press
release is warranted. The database migration and twelve-collection semantic
readiness remain engineering tasks, without editing the active launch queue.
The separate read-only inventory found that the old `dist/customer/gaming.csv`
still publishes `CCP-` in `facility_id` on 595 rows, `VP-` on 164 and `TPL-`
on 15, plus vendor IDs in provenance columns. This artifact is incompatible
with the new Cedar Grove-only Gaming contract and must not be promoted.
It also publishes `CEDAR-FAC-` in `facility_id` on 13 rows and once in
`entity_match_basis`: 935 source-only facility-key occurrences in all.
Exact source-only facility ID counts in this 787-row file are:

| Path | Column | CCP | VP | TPL |
|---|---|---:|---:|---:|
| `dist/customer/gaming.csv` | `facility_id` | 595 | 164 | 15 |
| same | `duplicate_of_facility_id` | 9 | 1 | 0 |
| same | `entity_match_basis` | 17 | 5 | 2 |
| same | `gaming_property_federal_traces__property_likelihood_basis` | 8 | 1 | 0 |
| same | `loyalty_program_property__entity_tier_basis` | 35 | 12 | 1 |
| same | `open_date_absent_reason` | 29 | 7 | 1 |
| same | `open_date_basis` / `open_date_event_basis` | 0 | 4 | 0 |
| same | `open_date_evidence` | 1 | 14 | 0 |

The uncapped inventory read 25 current spine CSVs, 596 clean CSVs (including
ignored historical backups), 17 customer CSVs and 476 sample CSVs without
writing to those trees, with zero read errors. The CLI prints the exact
path-column-prefix counts; the public Gaming counts above were remeasured
after adding the internal `CEDAR-FAC-` source namespace to the screen.
These are **screening occurrences**, not distinct entities or publication
violations: e.g. `BIE-funded` and `NHO-owned` match the broad prefix screen but
are not registered handles. Exact membership and object-role checks determine
violations. Reproduce every path/column/count with:

```powershell
python code/audit_retired_ids.py data/spine data/clean dist/customer dist/review/samples public/data/cedar/samples
```

The active Press release gate is red independently of Gaming. Its customer
database identity check fails, and semantic/no-regression checks are not
established. That is the current twelve-collection readiness result; the old
`docs/DATASET_READINESS.md` 15/15 READY figure is a 2026-09-02 source-artifact
check and does not establish storefront release readiness. The twelve-collection
identifier-contract test still enumerates exactly twelve launch collections.
Focused Cedar identity/field-map tests passed (46 cases); the `1169` release
selftest proved 17 positive/negative controls. Lumecon's contract and pipeline
suite passed 121 cases; its sole failure was Windows symlink creation privilege
(`WinError 1314`) before the security assertion ran. The Press collection and
download suite reached 66 cases with one import error because `uvicorn` is
absent from this worktree's Python environment. Neither environment failure
is evidence of a green release.
`1169` now tests exact historical vocabulary inside composite/prose values as
well as bare cells, and also blocks `CCP-`, `VP-`, `TPL-` and `CEDAR-FAC-`
numeric IDs on Gaming customer/sample surfaces. Its selftest plants both a composite
handle and a vendor facility ID. Existing outputs must be regenerated only
under a separately authorized release process; this audit does not touch them.
Running the amended customer check on a temporary copy of the live
`gaming.csv` returns `FAIL` with 935 source-only facility-key occurrences.

Lumecon Data's `identity.mode: registered_reference` verifies exact pinned
membership, nullable blanks and immutable release bindings. It does not
independently determine CE checksum or Native identity; the Cedar producer
must validate against the authoritative register before constructing the
binding. A source mapping containing a retired handle must be refused, not
blessed through an `id: id` entry. Existing Lumecon tests cover unknown and
modified registered references; a cross-repository release fixture with a
retired handle is still needed before claiming end-to-end proof.

**Claude stop condition:** keep Gaming ID creation and release paused until
the shared-ID binding migration, negative tests for every canonical table and
public surface, Lumecon fixture, and independent release scan all pass with
zero retired values. Do not change the active Press Gaming artifact or its
review queue as a side effect of this contract.

The human identity queue is limited to the 16 unbound `VP` facility keys,
contested historical handle bindings, and any operator/enterprise/place
equivalence lacking direct evidence. Assign each a reviewed same-place,
distinct-place or unresolved decision with source and date. Migrating the
customer database, retiring the old Press Gaming output, adding Lumecon
negative fixtures, wiring the new Gaming release and resolving missing source
coverage are engineering/release tasks, not human identity rulings.
