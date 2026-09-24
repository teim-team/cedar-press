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

## 4. Identifier contracts (migrated to the ratified contract 2026-09-24)

**IMPLEMENTED on this branch (candidate only).** Codex ratified the allowed-ID
contract in `docs/IDENTIFIER_STANDARD.md`, section "CICD retirement contract
and Gaming handoff (2026-09-24)". The Gaming identity layer now follows it.
`cedar_ids.py` was **not** modified: the Gaming static blocks are declared
from `gaming_grove.py` through `cedar_ids.declare_static_block`.

| Object | Public column(s) | Identifier | Authority |
|---|---|---|---|
| Native entity | `cedar_uid`, `*_cedar_uid` | `CE-xxxxx-CC` | 503 register; legacy handles only through `cedar_publication.resolve_retired_entity_handle` (`gaming_grove.legacy_handle_uid`), kept internal |
| Physical gaming facility | `gaming_facility_id` | the existing `CEDAR-PLACE-nnnnnn-CC`, unwrapped (no `PROV-GFAC:`) | 1129 place register; check characters verified |
| Distinct legal business / operator | `business_uid` (facility relationships) | `CB-nnnnnnn` from the gated Cedar Business Register | none bound: blank, `business_binding_status = held_business_unbound`, operator text kept as reported |
| Tribally owned enterprise | `enterprise_id` | an existing Cedar NEED enterprise ID (legacy prefix `CEDAR-NEST`) | only when that enterprise independently qualifies; Gaming never creates one, never copies Gaming facts into NEED; NEED hold applies |
| Observations: regional revenue, bands, reported revenue, financial disclosures, facility names, capacity, labor, compact terms, sportsbook financials | component ID columns | `CEDAR-OBS-nnnnnnnnn` | Gaming block 500000001-509999999 |
| Events: payments, regulatory events, land eligibility, environmental reviews, litigation, licence issuances, facility history | component ID columns | `CEDAR-EVENT-nnnnnn` | Gaming block 500001-799999 |
| Relationships: facility, sportsbook unit, advocacy links | component ID columns | `CEDAR-REL-nnnnnnnn` | Gaming block 50000001-50999999 |
| Online sportsbook reported-unit source series | `sportsbook_unit_id` | `CEDAR-SRC-nnnnnnnnn` | Gaming block 500000001-500999999 |
| Compacts and compact versions | `compact_id`, `successor_compact_id`, `version_id` | `CEDAR-CONTRACT-nnnnnnnn` | Gaming block 10000001-10099999; the BIA-index key (built from a tribe name and date) is kept as `source_record_id` |
| Coverage gaps | `coverage_gap_id` | natural composite key, no minted ID | an absence is not an object |

Every prefix above is an existing `cedar_ids.PREFIXES` entry; no namespace was
added. A compact version is an instrument document of its own (amendment,
extension, renewal), so it is a contract object; its approval is the separate
`CEDAR-EVENT` in `regulatory_event_id`.

**Binding register.** A producer calls `gaming_grove.derive_id(KEY_CLASS,
*stable_source_key_parts)`, which returns an internal key token. `build.py
candidate gaming` then runs `gaming_grove.bind_candidate`. It reads the prior
register from `--bindings` (default `<input-root>/data/spine/gaming_id_bindings.csv`,
read-only; absent means empty). Existing bindings are reused byte-exactly. New
keys take the next ordinals of their block in sorted `source_key_sha256`
order, with status `PROPOSED`. Every token in every component table is
replaced, and the register is written to `<candidate>/components/gaming_id_bindings.csv`
with columns `object_prefix, key_class, source_key, source_key_sha256,
issued_id, table, column, status, first_seen_as_of`. The pre-migration hash
survives only as `source_key_sha256`. A prior register that fails any check
(header, key class, block range, hash recomputation, duplicate key or ID) is
refused (`FAILED_BINDING`).

**Allocator safety.** The blocks sit far above every live counter
(`CEDAR-REL` 16044, `CEDAR-PLACE` 997; no `CEDAR-OBS/EVENT/SRC/CONTRACT`
counter, and no other caller of those prefixes in `code/`). `allocate` steps
over them in any process that imports `gaming_grove`
(`GamingBlocksTest`). **Residual risk for review:** `STATIC_BLOCKS` is
per-process. An `allocate` call from a process that never imports
`gaming_grove` is protected only by the distance between the live counters
and the blocks. **Proposal:** declare the Gaming blocks inside `cedar_ids`
(or persist declared blocks in `_id_registry.json`) when Codex next edits it.

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

- `PROV-` values and unbound `GKEY~` key tokens
- `CCP-`/`VP-`/`TPL-`/`CEDAR-FAC-` source facility keys
- retired entity handles, matched by exact historical membership, as a bare
  value or as the leading member of a composite key such as
  `TRBF-POARCH-00-NIGC-2007-0011-0010` (`RetiredHandleMatcher`; 1169's pattern
  alone misses the composite form)
- non-CE values in `cedar_uid`/`*_cedar_uid`, checked with `cedar_ids`' CE
  contract
- for a Grove collection with a binding register: any `CEDAR-OBS/EVENT/REL/
  SRC/CONTRACT` value whose binding is not `ISSUED` in the LIVE register
  (`--bindings`, default `data/spine/gaming_id_bindings.csv` in the checkout;
  absent means nothing is issued), and a `gaming_facility_id` that is not a
  checked `CEDAR-PLACE`

`pilot_registered_reference` refuses a Lumecon `registered_reference` mapping
that would bless a non-CE or retired value as `id: id`. It runs in phase 1,
before any intake. Lumecon checks pinned membership only; the cross-repository
fixture proves Lumecon accepts such a mapping and Cedar refuses it.

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

## 10. Controlled promotion of PROPOSED Gaming bindings (documented, NOT run)

A candidate's bindings are `PROPOSED`, and `release-pilot` refuses every
Gaming ID that is not `ISSUED` in the live register
(`data/spine/gaming_id_bindings.csv` in the populated workspace). Promotion is
a separate step. It is **not authorized** today, and nothing on this branch
has run it: the live register does not exist yet.

**Preconditions (Codex's stop condition, all required):**

1. The shared-ID binding migration and the `cedar_ids` retirement guards are
   integrated on the release branch, and the guards pass there. Codex also
   declares `cedar_ids.IDENTIFIER_CONTRACTS` bindings for each Gaming public
   key column. Without them `release-pilot` still refuses with "no declared
   identifier binding", even for an ISSUED ID.
2. Negative tests pass for every canonical table and public surface
   (`server/tests/test_gaming_release.py`), and so does the Lumecon
   `registered_reference` fixture.
3. An independent release scan (Codex, not the builder) finds zero retired
   values: `py -3 code/build.py grove-leak-gate gaming --candidate <C>` and
   `python code/audit_retired_ids.py <C>/samples` over the frozen candidate.
4. The owner records a decision ID authorizing issuance.

**Reviewers.** Codex does the independent verification, Havala answers
architecture questions, and the owner makes the decision.

**Commands** (run from the release checkout; `<LIVE>` is the populated Cedar
workspace; `<C>` is a new root outside Git):

```powershell
# 1. Build from exactly the live register, twice, and compare.
py -3 code/build.py candidate gaming --input-root "<LIVE>" --output-root <C1> --as-of <date> --bindings "<LIVE>\data\spine\gaming_id_bindings.csv"
py -3 code/build.py candidate gaming --input-root "<LIVE>" --output-root <C2> --as-of <date> --bindings "<LIVE>\data\spine\gaming_id_bindings.csv"
#    every file except logs\*.volatile.json must be byte-identical between <C1> and <C2>
# 2. Independent gate (a second agent).
py -3 code/build.py grove-leak-gate gaming --candidate <C1>
python code/audit_retired_ids.py <C1>\samples
# 3. Dry run: prints the plan (rows to promote by prefix), writes nothing.
py -3 code/build.py grove-promote-bindings gaming --candidate <C1> --live-root "<LIVE>"
# 4. Owner-authorized execution.
py -3 code/build.py grove-promote-bindings gaming --candidate <C1> --live-root "<LIVE>" --execute --decision-id <ID> --approved-by <name>
# 5. Release through the one path, which now finds the IDs ISSUED.
py -3 code/build.py release-pilot gaming --source <C1>\components\gaming_regional_revenue.csv --output-root <store> --as-of <date> --bindings "<LIVE>\data\spine\gaming_id_bindings.csv"
```

**Checks enforced by `grove-promote-bindings`.** The candidate must be
`LOCAL_CANDIDATE_PROPOSED_BINDINGS` with validation and the leak gate passed.
Its code hashes must equal the current code. It must have been built from
the live register byte-for-byte: the manifest records the prior register's
SHA-256, and a rebuild is required if another promotion happened since. Its
own register must match its manifest hash. Every live binding must survive
unchanged (`cedar_ids.validate_binding_history`: no binding disappears or is
reassigned, and no object gets two IDs). Promotion only flips `PROPOSED` to
`ISSUED`; it never allocates, renumbers or removes a binding.

**Rollback.** `--execute` first copies the prior register to
`gaming_id_bindings.csv.bak_<date>_pre_promotion`, then writes the new one
atomically, and appends the decision ID, approver, candidate manifest hash
and before/after hashes to `data/spine/gaming_id_bindings_promotions.jsonl`.
Before any release has pinned a promoted ID, restoring the backup is a
complete rollback. After a release pins one, the ID is permanent and is never
rolled back or reused. A wrong binding is retired forward, with a dated
successor, under the same rules as a `cedar_uid`.

## 11. Migration measured on the rebuilt candidate (2026-09-24)

`py -3 code/build.py candidate gaming --input-root "C:\Users\esm247\Desktop\Cedar Press" --output-root <root> --as-of 2026-09-24`
was run twice, into `idmig-1` and `idmig-2` under `~/cedar-grove-gaming-work`.
No prior register existed, so every binding is new and `PROPOSED`. The status
is `LOCAL_CANDIDATE_PROPOSED_BINDINGS`, validation passed with no problems,
and input and code conservation both held.

- **Determinism.** All 62 files are byte-identical between the two roots:
  components, receipts, samples, coverage and the manifest. Only
  `logs/gaming-candidate.volatile.json` is excluded; it holds the timings and
  the output-root argv.
- **Bindings.** The two builds wrote 93,824 bindings: `CEDAR-OBS` 25,433,
  `CEDAR-EVENT` 60,716, `CEDAR-REL` 5,775, `CEDAR-SRC` 35 and
  `CEDAR-CONTRACT` 1,865.
- **Leak gate.** Zero findings and zero screening occurrences over 50 public
  surfaces: 25 public projections and 25 sample files, 87,538 rows in all,
  checked against a 1,555-handle vocabulary. `audit_retired_ids.py` over
  `samples/` finds zero values.
- **Before/after.** Compared with the pre-migration candidate
  (`candidate-sports-2`), with ID columns mapped through the crosswalk, every
  table has the same rows and values, with three exceptions. The crosswalk
  gained 14 re-keyed tribe-level rows and the `rekeyed_cedar_uid` column.
  `gaming_facility_relationships` gained `business_uid` and
  `business_binding_status`. One online sportsbook unit (`MI_nhbp`,
  FireKeepers Casino) now links to `CEDAR-PLACE-000176-S0`; the other six
  named properties stay unresolved. Exact `Decimal` money handling changed no
  published value.
- **Online sports controls are unchanged.** There are 35 units, 1,546
  financial observations, 39 relationships and 20 gaps. The 62 NJ overlap
  rows are flagged and cross-referenced, one PA discrepancy is isolated, and
  the Maine three-tribe report stays `not_allocated`. There are 885 payment
  and 2,997 reported-revenue overlap references, and every one resolves to a
  sportsbook financial observation.
- **Crosswalk.** `components/gaming_id_migration_crosswalk.csv` has 95,380
  rows, one per key.

| Key family | Public identifier or held status | Keys | Rows |
|---|---|---:|---:|
| PROV-<class> component keys (17 classes) | bound `CEDAR-OBS/EVENT/REL/SRC`, PROPOSED | 91,959 | 99,759 |
| BIA compact / version key | bound `CEDAR-CONTRACT`, PROPOSED | 707 / 1,158 | 6,713 / 5,529 |
| PROV-GFAC | existing `CEDAR-PLACE`, unwrapped | 702 | 13,732 |
| PROV-GGAP | natural composite key, no minted ID | 20 | 20 |
| CCP | internal source key (573 mapped, 21 merged), 1 held_unresolved | 595 | 8,676 |
| VP | internal source key (94 mapped, 37 merged), 23 held_not_a_facility (incl. the 16 reviewed), 10 held_unresolved | 164 | 1,134 |
| TPL | internal source key (13 mapped, 1 merged), 1 held_unresolved | 15 | 88 |
| CEDAR-FAC | internal source key, mapped | 13 | 91 |
| tribe-level rows on reviewed VP keys | re-keyed to the tribe's CE with no facility (17); held_unresolved, no CE on the source row (2) | 19 | 19 |
| operator as reported | held_business_unbound (`business_uid` blank) | 4 | 6 |
| legacy entity handle, output columns | internal_only_provenance (none public) | 12 columns | 11,056 |
| legacy entity handle, input columns | dropped, not translated | 12 columns | 64,926 |

`release-pilot gaming` on `idmig-1/components/gaming_regional_revenue.csv`
refuses with "identifier binding ABSENT", against the default live register,
which does not exist in the checkout. With `--bindings` set to the
candidate's own register it refuses with "identifier binding PROPOSED".
Nothing is written in either case. With a scratch copy marked ISSUED, the next
refusal is the missing ruling-ledger authority in this checkout (section 8).
After that comes the pending `cedar_ids` Gaming identifier contract; the
fixture test shows it.
