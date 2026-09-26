# Request to Codex: CICD identifier-retirement audit (blocks Gaming ID creation)

Status: **ANSWERED 2026-09-24.** Codex ratified the allowed-ID contract in
`docs/IDENTIFIER_STANDARD.md`, section "CICD retirement contract and Gaming
handoff (2026-09-24)". The Gaming candidate identity layer has been migrated
to it (`ID_CONTRACT_STATUS = "RATIFIED_CANDIDATE_BINDINGS"`). The design,
blocks and binding register are in
`docs/GAMING_GROVE_INFRASTRUCTURE_NOTES.md` section 4, and the controlled
promotion process is in section 10. **No Gaming ID is issued.** Every
candidate binding is `PROPOSED`, and the release path refuses anything not
`ISSUED` in the live register. Codex's stop condition still holds: no live
issuance and no release until the shared-ID binding migration, the negative
tests, the Lumecon fixture and an independent release scan all pass with zero
retired values. The request text below is kept as the historical record.

## Owner's instruction (verbatim)

> Perform an immediate CICD identifier-retirement audit across Cedar Press, Cedar Grove, Lumecon Data, all active branches/worktrees, canonical registers, `data/clean`, `data/spine`, manifests, APIs, customer exports, public outputs, tests, and documentation.
>
> For every legacy prefix and CICD identifier, report:
>
> * exact path, column, and count;
> * whether it is historical input, compatibility crosswalk, test fixture, canonical value, published value, or actively generated output;
> * every script capable of minting, validating, copying, or publishing it;
> * whether the current code can still issue it.
>
> Enforce the retirement mechanically:
>
> 1. Current Native entities use only canonical `CE-` identifiers.
> 2. Legacy CICD prefixes may remain only behind an explicitly named read-only compatibility parser or historical crosswalk.
> 3. Generic validators and allocators must refuse to mint legacy prefixes.
> 4. New canonical tables, manifests, APIs, releases, and customer exports must reject legacy IDs.
> 5. Historical IDs must be preserved in a provenance crosswalk rather than silently deleted or reused.
> 6. Add CI tests proving legacy IDs cannot be minted, written, promoted, or published.
> 7. Search generated and ignored outputs too, while preserving user data.
>
> For Gaming, do not use CICD IDs or public `CCP-` vendor IDs. A casino receives a new canonical gaming-facility ID from the approved shared allocator; the affiliated Native entity retains its `CE-` ID; an operator may have a separate enterprise ID. Relationships connect them without collapsing the objects.
>
> Do not claim retirement is complete until the scan proves there are zero active minting paths and zero legacy IDs in governed outputs. Send architecture questions to Havala, not Elijah. Provide Claude with the resulting allowed-ID contract before Gaming IDs are created.

## What Gaming needs back (the allowed-ID contract)

1. The approved shared allocator and prefix for a **gaming facility** (a physical
   casino/resort/bingo hall/sportsbook). Candidates already in `cedar_ids.PREFIXES`:
   `CEDAR-FAC` (minted by 158 via `allocate`) and `CEDAR-PLACE` (1129, with 503
   check characters). Gaming currently wraps `CEDAR-PLACE` provisionally in one
   function, `gaming_grove.facility_id_for`.
2. Whether `CCP-`/`VP-`/`TPL-` may survive as an internal read-only crosswalk
   column (Gaming keeps them only in an `internal_crosswalk` table, never public).
3. Whether component IDs (payments, licenses, regulatory events, environmental
   reviews, labor observations, litigation, advocacy links, source observations)
   are minted by `cedar_ids.allocate` under existing prefixes (`CEDAR-EVENT`,
   `CEDAR-OBS`, `CEDAR-REL`, `CEDAR-SRC`...) or derived deterministically from
   source keys (`gaming_grove.derive_id`, 15 prefixes, not registered anywhere).
4. The enterprise namespace to use for operators/holding companies (`CEDAR-NEST`
   under the NEED affiliation hold?).
5. The named read-only compatibility parser Gaming should call when a source row
   carries only a legacy entity handle (e.g. `gaming_facilities.entity_id`
   holds `AKNF-…`/`TRBF-…` values). Until then Gaming refuses such values as
   `cedar_uid` and leaves the link unresolved.

Gaming-side legacy-prefix observations are collected in the forensics output
of this branch and will be attached here for the audit.
