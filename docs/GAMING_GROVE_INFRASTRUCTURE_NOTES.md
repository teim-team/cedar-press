# Gaming Grove: proposed shared-infrastructure improvements (for Havala/Codex review)

Written 2026-09-24 during the Cedar Grove Gaming Intelligence implementation on
branch `claude/gaming-intelligence`, which is based on Cedar PR #122 at `3195e70`.
Everything below is a **proposal**. None of it has been applied to Cedar PR #122,
Lumecon Data PR #8 (`codex/legislation-storage-safety` at `f882fb1`), or the
active branches of either repository. Gaming reuses the existing path unchanged
except for the bounded changes listed in section 1.

## 1. What Gaming changed in the shared path

These are the only additions, and they sit inside existing authorities:

| Where | Change | Why |
|---|---|---|
| `cedar_pipeline.RELEASE_PILOTS["gaming"]` | Adds optional keys: `table`/`replaces_flagship`, `product`, `time_coverage`, `identifier_refusals` | The flagship `FLAGSHIP["gaming"]` is vendor lineage. The pilot must write a `cedar_grove` catalog, and the time coverage must not claim 2026 |
| `cedar_pipeline.GROVE_COMPONENTS`, `GROVE_REFERENCES` | Declares the producer order and the cross-table references | The runner needs one ordered list and must not use a second registry |
| `build.py candidate gaming`, `build.py grove-contracts gaming` | Adds the Grove branch of the existing `candidate` command, plus a generator with `--check` | One orchestrator entry for multi-table components |
| `build.py cmd_release_pilot` | Refuses when `apply_field_map` reports `mapped: False`. Adds `pilot_table`, `pilot_table_contract` and `pilot_identifier_refusals`. Uses `config.get("product", "cedar_press")` | An unmapped collection used to pass the projection unchanged, which would have released every column (this affects all pilots) |
| `server/tests/test_field_map.py` | The "unmapped collection" example changes from `gaming` to a fictional ID | Gaming now has a generated field-map entry |

## 2. Multi-table release (the main gap)

`release-pilot` projects **one** table per collection:

- `FLAGSHIP[collection]`
- `field_map()` keyed by collection, so a second `collection/table` entry silently overwrites the first
- `full_release()` requires exactly one `collection/` field-map entry
- a catalog pin per `dataset_id`

A Grove collection has many component tables: 1200 has 5 and 1201 has 6, for
example. Each has its own grain, key and rights. **Proposal:** let a release
unit be `(collection, table)`:

- The Lumecon `dataset_id` becomes `gaming--regional-revenue`, which is safe
  under the existing ID regex.
- `field_map()` is keyed by `collection/table`, with the per-collection
  flagship lookup kept for the storefront.
- `full_release(collection_id, table_id=...)` selects the pin for that table.
- The catalog is extended with `collection_id` and `table_id` on each pin.

Until then, Gaming releases only the regional-revenue flagship. Every other
component stays a local candidate.

## 3. Grove catalog product and entitlement

- Lumecon `build_catalog` already accepts `product="cedar_grove"`.
- Cedar `repository.full_release` hard-codes `product == "cedar_press"`. It
  also refuses any collection outside `LAUNCH_COLLECTION` (the twelve
  storefront collections).
- The tier model already has `grove` and `tree`, which reach the `grove`
  shelf (`SHELF_BY_TIER`).

**Proposal:** add one reviewed Grove declaration. This would be either a Grove
list in the manifest's `excluded` entry or a separate `GROVE_COLLECTION`,
built from the same descriptor type. `full_release` would then accept
`cedar_grove` catalogs for that list only, gated by
`_reaches(tier, "grove")`. There would be no new tier and no new endpoint.

`server/tests/test_gaming_release.py::GamingServerDeliveryTest` simulates this
with the existing tier model and shows the following carry over unchanged:

- denial for anonymous (401) and for press/press_pro (403)
- exact bytes and a SHA header for grove/tree (200)
- stale-account denial: downgraded 403, removed 401, outage 503, with no fetch
- redacted audit
- stale-pin refusal (503)
- rollback by catalog reselection

The current code refuses Gaming, which is also tested.

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

**Proposal:** add an optional `rights_class` per field in `field_map.json`, and
have `apply_field_map` refuse `keep` or `rename` on a non-public class. One
rights vocabulary would then serve Press and Grove. Row-level rights
(`rights_class` column) also need a shared gate. Today `public_projection` in
`gaming_grove` and the 1137 row gate are separate.

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

It runs only for pilots that set `identifier_refusals`. **Proposal:** once
reviewed, make it unconditional for every pilot, and move the vendor pattern
into `cedar_ids.EXTERNAL_IDENTIFIER_SCHEMES` as a non-publishable scheme.

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
