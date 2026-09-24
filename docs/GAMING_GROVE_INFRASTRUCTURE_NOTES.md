# Gaming Grove: shared-infrastructure changes and proposals (for Havala/Codex review)

Written 2026-09-24 during the Cedar Grove Gaming Intelligence implementation on
branch `claude/gaming-intelligence`, which is based on Cedar PR #122 at `3195e70`.
Updated the same day when multi-component release support was implemented
(sections 1-3, and parts of 5 and 7). Each section says whether it is
**IMPLEMENTED** on this branch or still **PROPOSED**. Nothing here has been
applied to Cedar PR #122, Lumecon Data PR #8 (`codex/legislation-storage-safety`
at `f882fb1`), or the active branches of either repository. Lumecon Data was not
modified: everything below uses its existing contracts, pipeline, storage and
`build_catalog`.

## 1. What Gaming changed in the shared path

These are the only additions, and they sit inside existing authorities.

| Where | Change | Why | Status |
|---|---|---|---|
| `cedar_pipeline.RELEASE_PILOTS["gaming"]` | Optional keys `table`/`replaces_flagship`, `product`, `time_coverage`, `identifier_refusals`, and now `components` (see section 2) | The flagship `FLAGSHIP["gaming"]` is vendor lineage. The pilot must write a `cedar_grove` catalog, and the time coverage must not claim 2026 | IMPLEMENTED |
| `cedar_pipeline.GROVE_COMPONENTS`, `GROVE_REFERENCES` | Declares the producer order and the cross-table references | The runner needs one ordered list and must not use a second registry | IMPLEMENTED |
| `build.py candidate gaming`, `build.py grove-contracts gaming` | Adds the Grove branch of the existing `candidate` command, plus a generator with `--check`. The generator now writes one field-map entry per declared release component, each field carrying its `rights_class` | One orchestrator entry for multi-table components | IMPLEMENTED |
| `build.py cmd_release_pilot` | Refuses when `apply_field_map` reports `mapped: False`. Adds `pilot_table`, `pilot_table_contract`, `pilot_identifier_refusals`, and now `pilot_units`, `pilot_component_config`, `pilot_rights_refusals`, `release_dataset_id` (section 2) | An unmapped collection used to pass the projection unchanged, which would have released every column (this affects all pilots) | IMPLEMENTED |
| `cedar_publication` | `field_map_entries()` keyed by `(collection, table)`, `field_map_entry(collection, table=None)`, `apply_field_map(..., table=None)`; `field_map()` kept as the compatibility view | A second `collection/table` entry used to overwrite the first silently | IMPLEMENTED |
| Cedar server (`collections.py`, `repository.py`, `app.py`) | One reviewed Grove declaration; per-component full download from a pinned `cedar_grove` catalog (section 3) | The server accepted only `cedar_press` catalogs and storefront collections | IMPLEMENTED |
| `server/tests/test_field_map.py` | The "unmapped collection" example changes from `gaming` to a fictional ID | Gaming now has a generated field-map entry | IMPLEMENTED |

## 2. Multi-component release unit

**IMPLEMENTED.** The owner's 2026-09-24 integration review asks for "a
collection landing page with several governed component tables". A release
unit is now `(collection, component table)`. One run of `release-pilot`
releases every declared component of a collection and pins them all in **one**
catalog. The existing runner, projection, Lumecon pipeline, storage and catalog
are reused. There is no second runner, registry, manifest format, catalog
definition, ID allocator or audit log.

### Design

- **Declaration.** `RELEASE_PILOTS[c]["components"]` is an ordered
  `{component table: {owner, url, rights, time_coverage, caveats}}`. These keys
  are merged over the collection-level keys, and caveats are concatenated.
  `table` is the landing component and must be one of them. The replaced
  vendor flagship (`replaces_flagship`) may never be a component. A pilot
  without `components` (Legislation, Natural Resources) takes the old path
  unchanged.
- **Field map.** `field_map.json` is keyed `<collection>/<table stem>`.
  `cedar_publication.field_map_entries()` returns
  `{(collection, stem): entry}`, and `field_map_entry(collection, table)`
  selects one component exactly. Without a table, a collection with several
  entries is **refused** (`FieldMapRefusal`) and is never resolved to one of
  its components. `apply_field_map(..., table=None)` uses the same accessor.
- **Compatibility and `full_release` semantics.** `field_map()` still returns
  `{collection: entry}`. It is byte-identical for every single-entry
  collection. A multi-component collection maps to its first declared (landing)
  entry, so "is this collection mapped?" callers (770, 1135) still hear yes.
  Those callers then call `apply_field_map(collection)` without a table, which
  refuses, so a component is never projected through another component's
  header. The server's `full_release(collection)` keeps "exactly one entry" for
  Press. For a Grove collection it requires `component` and selects exactly
  `<collection>/<component>`.
- **Lumecon dataset ID.** Lumecon requires `[a-z0-9][a-z0-9_-]{0,99}`, with no
  slash. The component dataset ID is therefore `<collection>--<table stem>`,
  for example `gaming--gaming_regional_revenue`. `release_dataset_id` refuses
  a stem outside `[a-z0-9][a-z0-9_]{0,59}` and a collection containing `--`.
  Press pilots keep the bare collection ID, so their release bytes and IDs are
  unchanged.
- **CLI.** `release-pilot <collection> --source <csv> [--source <csv> ...]`.
  Each source's filename names its component. Every declared component must be
  supplied exactly once. A partial catalog would silently drop a component at
  the next pin. A single-flagship pilot takes exactly one `--source`, as before.
- **Two phases.** Phase 1 projects and validates **every** component, in
  declared order, before anything is written. A refusal in any component
  therefore stops the whole collection with no intake, release or catalog
  artifact. Phase 2 writes one immutable Lumecon release per component,
  checking determinism twice and verifying each release. It then calls
  `build_catalog(target, [(dataset_id, release_id), ...], product=...)` once.
- **Refusals for components.** These run in addition to the existing checks
  (registered table contract, declared primary key, source/target separation,
  strict CSV, unique keys, field map, no owed/held fields, record conservation,
  a `cedar_ids` binding for every key column, and CE entity references). All
  of them are unconditional:
  - the table contract's `publication_status` must be `public`;
  - `pilot_identifier_refusals` refuses `PROV-`, CCP-/VP-/TPL- and non-CE
    `cedar_uid`/`*_cedar_uid` values;
  - `pilot_rights_refusals` refuses a shipped (`keep`/`rename`/`withhold`)
    field whose field-map `rights_class` is missing or outside the
    collection's `PUBLIC_RIGHTS` (`gaming_grove`: `public_official`,
    `public_derived`, `public_first_party`). It also refuses any row whose
    `rights_class` is not public, such as `secondary_corroboration`,
    `internal_*` or `withheld_*`. Rows are refused, not filtered, because
    filtering would break record conservation. The producer must emit a
    public-only release table.
- **Rollback** is still reselection of a prior verified catalog. A change to
  one component makes a new release for that component, the sibling's release
  ID is unchanged, and a new catalog pins both.

### Diff summary (release path)

- `code/cedar_pipeline.py`: `RELEASE_PILOTS["gaming"]` moves the NIGC-specific
  owner, url, rights, caveats and time coverage under
  `components["gaming_regional_revenue.csv"]`, and documents the `components`
  key. Only the regional-revenue component is declared. Adding a component
  means adding one entry here and running `code/build.py grove-contracts
  gaming`; it then still needs a public table contract, public-only rights and
  a `cedar_ids` binding before it can release.
- `code/build.py`: `release_dataset_id`, `pilot_component_config`,
  `pilot_units`, `pilot_rights_refusals`, the two-phase `cmd_release_pilot`,
  and `--source` becoming repeatable. `grove_release_tables` and
  `grove_field_map` now generate one entry per component, in declared order.
  `grove_field_map_entry` adds `rights_class` per field. The contract-doc text
  is updated.
- `code/cedar_publication.py`: `field_map_entries`, `field_map_entry`, the
  compatibility `field_map`, and `apply_field_map(table=)`.
- `data/cedar/field_map.json`: regenerated. The `gaming/gaming_regional_revenue`
  fields gain `rights_class`, and nothing else changes. The field-map and guide
  markdown generators report "current".

## 3. Grove catalog product and entitlement

**IMPLEMENTED**, with no new tier, route or catalog format.

- **One reviewed declaration:** `server/cedar_press/collections.py`
  `GROVE_RELEASE_IDS = ("gaming",)`. `GROVE_RELEASE_COLLECTIONS` keeps a
  declared ID only while the generated manifest still lists it in `excluded`
  with shelf `grove`. The served **components** are not listed a second time.
  They are the collection's field-map entries (generated from
  `RELEASE_PILOTS[...]["components"]`) that the pinned catalog also pins
  (`repository.grove_components`).
- **Entitlement:** `repository.may_download_full(tier, id)` is `may_open`
  (unchanged) for every Press collection. For a declared Grove collection it
  is `_reaches(tier, "grove")`, so `grove` and `tree` pass and `press` and
  `press_pro` are refused. `may_open`, `is_sold`, the shelf, the sample route
  and Ask still refuse Gaming to every tier.
- **Catalog pin:** a Lumecon catalog carries one product, so Grove has its own
  pin, `CEDAR_GROVE_RELEASE_CATALOG`, beside `CEDAR_PRESS_RELEASE_CATALOG`
  (`repository.RELEASE_CATALOG_ENV`). Each pin must hold a catalog of its own
  product. `full_release(collection, release_id, component=...)` shares every
  existing check: catalog checksum, schema, `entitlement_required`, exactly
  one pin, explicit release ID equal to the pin, manifest digest, metadata
  equality, rights, field-map header equality, byte count, SHA-256, record
  count, schema and primary keys.
- **Route:** `GET /press/collections/{id}/full-download?release_id=...&component=<stem>`.
  A Grove request without `component` is refused with 400. An unknown or
  malformed component is refused with 503 before any fetch. Responses add
  `X-Cedar-Component`, a filename of `<collection>--<component>-<release>.jsonl`
  and a citation of `Cedar Grove <collection>/<component>, release ...`.
  `repository.grove_release_metadata` lists the verified descriptor for each
  component, for a landing page.
- **Audit:** it uses the same logger and record. A Grove event adds
  `component`, which is redacted to `unknown` unless it is a declared
  component. Press events are byte-for-byte unchanged, with no new key.
- **Tests (`server/tests/test_gaming_release.py`):** two synthetic components
  in one catalog are each downloaded exactly for grove and tree. Anonymous,
  press and press_pro requests, a downgraded account, a removed account and an
  account-store outage are all denied with zero catalog or artifact fetches.
  Missing, unknown and malformed components are refused and redacted. A
  sibling's release ID is refused. A stale pin is refused. Rollback restores
  both components' exact bytes. The pins are per product. The pilot tests cover
  both components in one catalog, with exact bytes, determinism, the
  immutable-replacement refusal and rollback. They also cover refusal of the
  whole release for PROV-, CCP-, non-CE, `secondary_corroboration` and
  `internal_vendor` rows, a non-public or undeclared field, a `source_limited`
  status and an unmapped component. Finally they show single-flagship pilots
  and single-entry field-map callers unchanged.

**Still PROPOSED / for Havala:**

- **Per-product catalog pin.** The second environment variable is the
  smallest change that lets Press and Grove be served at once. Havala may
  prefer one deployment-level catalog directory keyed by product.
- **Landing-page route.** `grove_release_metadata` exists, but no endpoint or
  client renders it yet.
- **Where the declaration lives.** Should `GROVE_RELEASE_IDS` move into the
  generated manifest, for example as an `excluded[].grove_release` flag from
  the Cedar workspace? That would keep the declaration in the manifest's
  single source.
- **Metadata cost.** `grove_components` re-reads `field_map.json` per call,
  which is the same cost as the existing `full_release` read. It could be
  cached with the manifest if needed.

## 4. Identifier contracts (drafted; `cedar_ids.py` is under audit)

The owner hold of 2026-09-24 pauses Gaming ID creation until Codex returns the
CICD identifier-retirement audit and an allowed-ID contract. `cedar_ids.py` was
**not** modified. Proposed bindings for review:

| Binding (collection, table, column) | Namespace | Object kind / role | Mint authority | Note |
|---|---|---|---|---|
| gaming, gaming_grove_facilities.csv, gaming_facility_id | per allowed-ID contract ("new canonical gaming-facility ID from the approved shared allocator") | facility / identity | shared allocator (`cedar_ids.allocate`), not 1129 and not a derived hash | Do **not** hard-wire `CEDAR-PLACE` as the public facility key. The place ID stays a crosswalk (`gaming_facility_crosswalk.csv`). CCP-/VP-/TPL- are internal only |
| gaming, *component tables*, derived observation IDs (GREV, GBND, GPAY, GREG, GLIC, GENV, GLAB, GFIN, GLIT, GADV, GSRC, GFNM, GFST, GFCP, GREL) | per prefix | record / observation | `gaming_grove.derive_id` from stable source keys, if the contract permits derived IDs | Pattern `<PREFIX>-[0-9A-F]{12}`. `PROV-` is never valid |
| gaming, *any*, cedar_uid (and `*_cedar_uid`) | CE | native_entity / role per table (e.g. `payment_recipient`, `facility_affiliate`) | 503_identity.py | Same shape as the existing CE role bindings |
| gaming, *any*, enterprise_id | CEDAR-NEST | enterprise / operator_or_holding | 1072 via `cedar_ids.allocate` | NEED publication hold still applies |
| gaming, gaming_compacts.csv, compact_id | existing compact ID scheme | source_document / instrument | BIA compact index (15b) | Source key, not a Cedar object |

**Proposal:** add a first-class **derived-ID contract** to `cedar_ids`. It
would record the prefix, the hash recipe, the source-key columns and the
binding, and `validate_identifier` would accept a derived ID only if it
recomputes from the row's declared source keys. The Gaming ID contract request
is at `docs/GAMING_ID_CONTRACT_REQUEST.md`.

## 5. Rights registry belongs in the field map

Gaming field rights (`gaming_grove.RIGHTS_CLASSES`) are declared per column in
each producer's `CONTRACTS`. The field map has only `keep`, `rename`,
`internal`, `withhold` and similar decisions. `grove-contracts` projects rights
into decisions: public classes become `keep` and everything else becomes
`internal`. The rights class is kept in `why`, which loses structure.

**Partly IMPLEMENTED:** generated Grove field-map entries now carry
`rights_class` on every field. `release-pilot` refuses a component whose
shipped field or row rights class is not public (`pilot_rights_refusals`,
section 2).

**Still PROPOSED:** move the check into `apply_field_map` itself, so every
writer refuses `keep`/`rename`/`withhold` on a non-public class, not only the
release pilot. Give Press entries the same optional key, so that one rights
vocabulary serves Press and Grove. Unify the row-level gate: today
`public_projection` in `gaming_grove`, the pilot's row refusal and the 1137 row
gate are three separate places.

## 6. Registration of producer-declared tables

- `code/512_build_dataset_contracts.py` derives the table list from `data/clean`.
  Grove components live in a candidate root, and a 512 rerun would drop their
  entries and the `grove_role` annotations. **Proposal:** 512 should merge
  entries whose `grain_declared_by` names producer `CONTRACTS`, or read them
  through `grove-contracts`.
- `registration_problems` refuses duplicate table names. That is correct, and
  Gaming adds a `NAME_COLLISION` refusal at sync time. **Proposal:**
  table-name uniqueness should be enforced across all collections, not only
  within one contract.

## 7. Shared identifier refusal

`pilot_identifier_refusals` refuses the following:

- `PROV-`
- CCP-/VP-/TPL- vendor IDs
- non-CE values in `cedar_uid`/`*_cedar_uid`, checked with `cedar_ids`' CE
  contract

**Partly IMPLEMENTED:** it is unconditional for every multi-component pilot.
For a single-flagship pilot it still runs only when the pilot sets
`identifier_refusals`, which leaves Legislation and Natural Resources
unchanged.

**Still PROPOSED:** once reviewed, make it unconditional for every pilot, and
move the vendor pattern into `cedar_ids.EXTERNAL_IDENTIFIER_SCHEMES` as a
non-publishable scheme.

## 8. Authority inputs the pilot reads from the checkout

`combine.load` needs `data/clean/cedar_ruling_ledger_consolidated.csv`, and
`register()` needs `data/spine/cedar_entity_names.csv`. The pilot reads both
from the **code checkout**, not from `--source`. A worktree without ignored
data therefore cannot run a real pilot. **Proposal:** add an
`--authority-root` so that these inputs are pinned and hashed from the data
workspace. `pilot_authority_hashes` already records them.

## 9. Scale bounds

Lumecon enforces a 16 MiB source cap. `gaming_government_payments.csv` (CA
payments alone are 41,758 lines) may exceed it when it becomes a release
candidate. This is the same streaming gap already recorded for Advocacy.
