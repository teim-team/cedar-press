# Gaming Grove: Cedar integration notes (for Havala/Codex review)

Written 2026-09-24 on `claude/gaming-intelligence` and rewritten the same day
for the repository split, on Cedar branch `claude/gaming-grove-consumer`. The
old branch (`75a2f1b`) is unchanged. **Lumecon-data owns the Gaming data.**
The producers, candidate build, leak gate, data contract and release/catalog
build moved to Lumecon-data branch `claude/gaming-grove-release`, with their
history and tests. This document now covers only what Cedar does with a Gaming
release. The repository ownership map and the cross-repository release sequence
are in [HAVALA_INFRASTRUCTURE_REVIEW.md](HAVALA_INFRASTRUCTURE_REVIEW.md#gaming-repository-ownership-and-cross-repository-release-sequence-2026-09-24).

Data-side sections that used to live here are now Lumecon-data documents on
`claude/gaming-grove-release`:

| Former section | Now in Lumecon-data |
|---|---|
| Multi-component release unit, per-component release metadata, catalog build | `docs/gaming-contract.md` and the `lumecon-data gaming release` command. It builds ONE collection release with one manifest, not one release per table |
| Producer contracts, rights classes, row-level public projection, registration of producer tables | `src/lumecon_data/gaming/contract.py`, `docs/gaming-contract.md`, JSON contracts under `schemas/gaming/` |
| Shared identifier refusal and leak gate (PROV-, GKEY~, CCP-/VP-/TPL-/CEDAR-FAC-, retired handles incl. composite forms, non-CE, unissued Gaming IDs) | `src/lumecon_data/gaming/leak_gate.py`, `lumecon-data gaming leak-gate` |
| Binding proposal (stable source key -> PROPOSED ordinal in a Cedar-reserved block), append-only and tamper checks | `src/lumecon_data/gaming/candidate.py` |
| Scale bounds (16 MiB source cap vs payments) and migration measurements on the rebuilt candidate | Lumecon-data `docs/HANDOFF.md` Gaming section |
| VP dispositions (reviewed decision) | `decisions/gaming/` |

## 1. What Cedar keeps

| Where | What | Why it stays in Cedar |
|---|---|---|
| `server/cedar_press/collections.py` `GROVE_RELEASE_IDS = ("gaming",)` | The reviewed Grove declaration. It holds only while the manifest keeps `gaming` on the `grove` shelf in `excluded` | Product decision: which collections the full-download route may serve |
| `data/cedar/grove_release_pin.json` | THE pin: one immutable Lumecon release per Grove collection | Consumer choice of release; reviewed like code |
| `server/cedar_press/repository.py` `grove_release_pin`, `grove_full_release`, `grove_component_contract`, `grove_release_metadata` | Pin, catalog and manifest verification, per-component schema check against the field map, exact component bytes | Consumer adapter |
| `server/cedar_press/app.py` `full_download` | Entitlement (grove/tree), redacted audit naming the component, 503 with a clear "not pinned" error | Entitlement belongs to the product |
| `data/cedar/field_map.json` `gaming/gaming_regional_revenue` | Presentation entry: order, default viewer, per-field `rights_class` | Presentation contract. It is checked against the pinned contract and is never the schema authority |
| `cedar_ids.GAMING_BLOCKS` and `code/build.py gaming-issue-ids` | Block reservation and the ONE issuance step | Cedar's identity service is the sole ID issuer |
| `cedar_publication.field_map_entries` / `field_map_entry` / `apply_field_map(table=)` | Keyed field-map accessors | A second `<collection>/<table>` entry must not silently overwrite the first |
| `code/build.py release-pilot` hardening: `pilot_registered_reference`, `RetiredHandleMatcher`, unmapped-collection refusal, `pilot_table_contract` | Single-flagship pilots only | Natural Resources carries `cedar_uid`, so a Press pilot uses it (`code/build_test.py`) |
| `docs/schema/dataset_contracts.json` gaming entry | The 65 legacy clean-table contracts, with `grove_role` naming the Lumecon consumer module | Cedar's transitional inputs, read by hash by Lumecon |
| `scripts/audit_gaming_inventory.py`, `docs/GAMING_ID_CONTRACT_REQUEST.md` | Audit of Cedar's clean workspace; historical ID request and answer | Cedar-side evidence |

Removed from Cedar: the producers and their tests, `gaming_grove.py`, the
online sportsbook module, `build.py candidate gaming`, `grove-contracts`,
`grove-leak-gate`, `grove-promote-bindings`, the multi-component
`release-pilot` mode (Gaming was its only caller),
`cedar_pipeline.RELEASE_PILOTS["gaming"]`, `GROVE_COMPONENTS`,
`GROVE_REFERENCES`, the 25 Grove component registrations, the generated
`GAMING_GROVE_DATA_CONTRACT.md` and the VP dispositions CSV.
`server/tests/test_gaming_release.py` fails if any of them comes back.

## 2. The pin

`data/cedar/grove_release_pin.json`:

```json
{"schema_version": 1, "product": "cedar_grove", "pins": {
  "gaming": {"catalog_id": "<64 hex>", "catalog_sha256": "<64 hex>",
             "collection_id": "gaming", "release_id": "<64 hex>",
             "manifest_sha256": "<64 hex>"}}}
```

- **Production is empty** (`"pins": {}`) until Cedar issues the Gaming IDs
  and Lumecon builds a production release from the issued registry snapshot.
  The route then answers `503 No released data is pinned for this collection
  yet` and audits `not_pinned`. It never falls back to a sample, a local CSV,
  a branch or a `current` pointer.
- **It extends, not replaces, `CEDAR_GROVE_RELEASE_CATALOG`.** The variable
  still names where the reviewed catalog's bytes are deployed. The pin says
  which bytes they must be (`catalog_sha256` over the exact file and the
  recomputed `catalog_id`) and which release inside them.
- **One release, not per-table releases.** `collection_id` must equal the
  collection ID. A pin naming `gaming--<table>` is refused. So is any catalog
  that is not a Lumecon `collection_releases` catalog, such as a dataset
  catalog of per-table releases. Cedar never assembles a collection from
  unrelated table releases.
- **Rehearsal and synthetic releases are never served.**
  `repository.GROVE_SERVED_RELEASE_CLASSES` is `{"production"}` and
  `GROVE_SERVE_SYNTHETIC` is `False`. Only the consumer tests widen them, for
  the synthetic rehearsal fixture.
- **Rollback** is a revert of the pin PR. Because it is one release, every
  component returns to its prior bytes together (atomic).

## 3. What the server checks, in order

1. The collection is in the Grove declaration. The component is well formed
   and is a field-map presentation entry of that collection. Otherwise the
   request is refused before any read, and the audit redacts the component to
   `unknown`.
2. Session and current account tier: anonymous 401, press/press_pro 403, a
   downgraded, removed or unreachable account refused before the pin is read.
3. The publication hold (`cedar_publication.assert_collection_publishable`).
4. The pin is well formed and names the collection.
5. The catalog bytes at `CEDAR_GROVE_RELEASE_CATALOG` hash to
   `catalog_sha256`, `catalog_id` recomputes, and the product is
   `cedar_grove` with `entitlement_required`. The catalog kind is
   `collection_releases`, with exactly one entry for the collection. That
   entry's `release_id`, `manifest_sha256` and
   `manifest_path` (`/v1/collections/<id>/releases/<rid>/manifest`) equal the
   pin.
6. The collection manifest fetched from the Lumecon API hashes to
   `manifest_sha256`. It names the pinned collection and release, has
   `release_kind: collection` and product `cedar_grove`, and its
   `release_class` and `synthetic` flag are served.
7. The component's embedded contract has public/publishable rights,
   redistribution, and `download_permitted: true`. Its field names, in order,
   equal the field-map `order`, and each shipped field's `rights_class` equals
   the contract's `metadata.field_rights`. Its primary key is within the header, and the count and
   artifact size are bounded.
8. The component bytes come from
   `/v1/collections/<id>/releases/<rid>/components/<name>/download`. They
   match the manifest's size and SHA-256, the record count
   and schema, and the primary keys are nonblank and unique.

The response is exact JSONL with `X-Cedar-Release`, `X-Cedar-SHA256`,
`X-Cedar-Component`, `X-Cedar-Rows`, `X-Cedar-Citation`
(`Cedar Grove gaming/<component>, release <id>`) and
`Cache-Control: private, no-store`.

## 4. Tests

- `server/tests/test_gaming_release.py`:
  - `GamingConsumerBoundaryTest` runs without Lumecon. It checks the empty
    production pin (fails closed, clear error), malformed and per-table pins,
    entitlement decided before any pin, catalog or artifact read, redacted
    component refusal, and the storefront unchanged.
  - `ZeroCanonicalDuplicationTest` fails if a producer module, binding
    register, component CSV or schema copy reappears.
  - `PinnedLumeconReleaseTest` builds the synthetic fixture release with the
    installed `lumecon-data gaming fixture-release`, plus a second, later
    release. It serves them through Lumecon's own verification
    (`verify_collection_release`, `collection_manifest_metadata`,
    `read_collection_component`) in place of the API hop, because Lumecon's
    read-only API has no collection routes yet. It covers schema compatibility per component,
    manifest/hash agreement, exact bytes, idempotent re-pinning, atomic
    rollback, unavailable and mismatched releases, and refusal of per-table
    catalogs.
- `server/tests/test_gaming_issuance.py`: the blocks are declared in
  `cedar_ids`, and Lumecon's constants must equal them. It also covers the
  issuance dry run, execution, reuse, snapshot and every refusal.
- CI: job `gaming-release-consumer` in `.github/workflows/ci.yml`.

## 5. Still PROPOSED / for Havala

- **Block reservation vs. ordinal assignment.** Cedar reserves the blocks and
  is the sole issuer. Lumecon proposes the ordinal for a new source key inside
  a block, and Cedar only accepts or refuses it at issuance. Havala should
  confirm whether proposal should stay in Lumecon, or whether Cedar should
  assign the ordinals at issuance, with Lumecon proposing keys only.
- **Landing-page route.** `grove_release_metadata` exists, but no endpoint or
  client renders it yet.
- **Where the declaration lives.** Should `GROVE_RELEASE_IDS` move into the
  generated manifest, for example as an `excluded[].grove_release` flag?
- **512 regeneration.** `code/512_build_dataset_contracts.py` derives tables
  from `data/clean`. A rerun would drop the `grove_role`/`grove_consumers`
  annotations on the 65 legacy tables, so they need to be merged.
- **Rights in `apply_field_map`.** Make every writer refuse `keep`/`rename`
  on a non-public `rights_class`, not only the Gaming contract check.
