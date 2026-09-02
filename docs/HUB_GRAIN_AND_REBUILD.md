# The `_entity_layer` hub - grain, keys, and what a rebuild has to reproduce

*Measured 2026-09-01 by `code/741_hub_grain_and_rebuild.py`. Regenerate rather than edit. **Neither `01_build_entity_spine.py` nor `09_import_rulings.py` was run to produce any number here.***

## 1. C1/C2/C3 - one defect, one fix, nothing deleted

Three tables were listed with literal duplicate rows and no key. The counts were real. The rows were not duplicate facts: a projection dropped the identity of the row a ruling was applied TO, so N distinct applications rendered as N identical rows. The identity is now written back and the counts fall to zero **without a single deleted row**.

| table | rows before | rows after | literal dups before | after | the column that was missing |
|---|---:|---:|---:|---:|---|
| `cross_dataset_ruling_map.csv` | 7,507 | 22,936 | 2,228 | 0 | `target_row_ordinal` (`23`) |
| `cedar_ruling_ledger_consolidated.csv` | 15,587 | 43,321 | 6,302 | 0 | `source_row_ordinal` (`173`) |
| `cedar_identifier_graph_edges.csv` | 46,051 | 46,820 | 2,451 | 0 | `asserting_row_ref` (`169`, spliced by `741 edges`) |
| `tcu_cdfi_ownership_evidence.csv` | 130 | 130 | 4 | 0 | `quote_char_offset` (`73`) |

The row counts GREW because `23` had not been re-run since the ruling and exclusion sets last grew - 380 rulings and 4,779 exclusions reach further than they did when the stale map was written. Nothing was removed at any step.

**The ledger's duplication was NOT only the ruling map.** Measured before the repair: 3,561 of the 6,302 surplus rows came from `review/osha_gambling_unresolved_2026-08-26.csv`, whose 4,560 rows are one per (OSHA establishment-year record, proposed tribe) and are themselves distinct - `173` kept the subject, the verdict and the source FILE and dropped which ROW said it, so the establishment, city, state and year that separate them were thrown away. 2,572 came from the ruling map. The fix is one column in `173` and it closes both.

## 2. C8 - the spine genealogy, read off the backup trail

`build.plan_for` returns the spine enrichers lexicographically (`50`, `503`, `51`, `52`, ...), which is not the order they were applied, so nobody could state what a replay must run. The order was not invented here: **every spine enricher takes a `cedar_entity_spine.csv.bak_<date>_pre<NN>` before it writes**, so the backup directory in modification-time order IS the applied order, and each backup's header is the column set immediately before that enricher ran.

| # | stage that ran next | rows before it | columns before it | columns the PREVIOUS stage added |
|---:|---|---:|---:|---|
| 1 | `51_add_anc_acronym_aliases.py` | 687 | 12 | - |
| 2 | `52_add_village_corporations.py` | 687 | 12 | - |
| 3 | `61_add_nho_intertribal_to_spine.py` | 866 | 12 | - |
| 4 | `66_build_entity_hierarchy.py` | 952 | 12 | - |
| 5 | `alias` | 952 | 18 | `ancsa_region_entity_id`, `hierarchy_basis`, `parent_entity_id`, `parent_entity_name`, `ultimate_parent_entity_id`, `ultimate_parent_entity_name` |
| 6 | `pre_recon` | 952 | 18 | - |
| 7 | `pre_srt_reopen` | 952 | 21 | `cicd_verified`, `reconciliation_note`, `reconciliation_status` |
| 8 | `69_enrich_spine_from_federal_register.py` | 952 | 21 | - |
| 9 | `71_fix_known_defects.py` | 952 | 22 | `fr_official_name` |
| 10 | `pre_tlingit` | 952 | 22 | - |
| 11 | `74_add_organization_acronyms.py` | 952 | 22 | - |
| 12 | `73_add_tcu_and_cdfi.py` | 952 | 22 | - |
| 13 | `75_add_bie_schools_and_uios.py` | 1,082 | 27 | `entity_source_quote`, `entity_source_url`, `ownership_basis`, `parent_native_entity`, `serves_native_entities` |
| 14 | `163_promote_nho_universe_in_place.py` | 1,310 | 33 | `bie_operation_type`, `built_by_script`, `city`, `entity_website`, `source_quote`, `source_url` |
| 15 | `241_promote_individual_native_firms_in_place.py` | 1,489 | 37 | `evidence_grade`, `evidence_tier`, `evidence_url`, `verification_route` |
| 16 | `416_reconcile_spine_id_columns.py` | 1,534 | 37 | - |
| 17 | `426_mint_bristol_bay_spine_entities.py` | 1,534 | 43 | `canonical_entity_id_column`, `cedar_entity_id_scheme`, `constituent_band_of_basis`, `constituent_band_of_entity_id`, `entity_master_register_id`, `entity_master_register_id_basis` |
| 18 | `503_identity.py (via 504/505)` | 1,536 | 43 | - |
| 19 | `71_fix_known_defects.py` | 1,536 | 44 | `cedar_uid` |
| 20 | `503_identity.py (via 504/505)` | 1,536 | 44 | - |
| 21 | `241_promote_individual_native_firms_in_place.py` | 1,536 | 44 | - |
| 22 | `524_universe_gap.py` | 1,536 | 44 | - |
| 23 | `503_identity.py (via 504/505)` | 1,555 | 44 | - |
| 24 | `LIVE` | 1,555 | 44 | - |

**The gate a replay must clear:** at least 1,555 rows and all 44 columns. `docs/schema/hub_rebuild_census.json` carries the column list so the check is mechanical.

### What this does and does not close

`01` and `09` now take a `.bak` before writing, like all fifteen spine enrichers, so the unrecoverable case is gone - and that matters more here than elsewhere, because `.gitignore:95` excludes `data/spine/*` apart from `cedar_identity_register.csv` and `cedar_handle_history.csv`, so **git cannot restore the spine**.

**It does not make `01` non-destructive, and C8 is not closed.** `01` builds the spine from `canonical_tribe_table.csv` alone - 687 rows, 12 columns - against a live hub of 1,555 rows and 44. A direct invocation still drops 868 entities and 32 columns; the backup makes that recoverable, not acceptable. `09` still drops 1,345 ledger rows, 18 of them tier A owner adjudications. Both remain in `cedar_pipeline.NEVER_RUN`, `build.plan_for` still sorts them into its `blocked` phase, and the scoreboard reads that guard as the C8 blocker - correctly. The only way to make the blocker green today would be to remove the guard, which would let `py -3 code/build.py run _entity_layer --execute` destroy the hub. **A gate satisfied by removing the thing that protects the data is worse than a red one.**

What genuinely closes C8 is a `01` that append-merges instead of rebuilding - which `NEVER_RUN`'s own text already prescribes - and a `09` that merges rather than replacing `_final`. The census above is the target either of them has to hit, and it is the piece that was missing.

## 3. THE GATE LINE THIS WORK MOVED THE WRONG WAY, AND WHOSE IT IS

`62_no_regression_check.py` reports **`rulings_unapplied ROSE 1,215 -> 2,894`**, a metric declared to only go down. It counts rows of `cedar_ruling_ledger_consolidated.csv` with `status = CONFLICT_NOT_APPLIED`. Recorded here rather than stepped around, per standing rule 15, and attributed by measurement rather than by assertion.

The rise is 116 -> **263 conflicting SUBJECTS**, 147 of them new and **none resolved**. Of those 147:

| | subjects |
|---|---:|
| carry no `cross_dataset_ruling_map.csv` row at all - they arrived from OTHER workstreams' files that `173` swept today (`gaming_employment_observations.csv`, `523_idgraph_q4_split_entity_suspects.csv`, `individual_native_firm_register.csv`) | 114 |
| carry a map row but the conflict stands without it | 5 |
| **need a map row - attributable to re-running `23`** | **28** |

So 28 subjects of the 147 are this workstream's, and every one of them is a NEGATIVE ruling and a positive ruling on the SAME identifier, both of which already existed. `cedar_exclusion_rulings.csv` lives in `data/spine`, which `173.discover()` does not scan, so `cross_dataset_ruling_map.csv` is the ONLY channel by which an exclusion reaches the ledger - and the map was stale. The 28 were hidden by that staleness, not created by refreshing it.

**They must not be suppressed.** C6 is 'material unresolved identity conflicts do not ship as definite facts', and `173` applied NEITHER side of any of them: all 263 are in `review/ruling_conflicts_2026-09-01.csv` awaiting adjudication, which is the correct destination for a disagreement this project cannot resolve by preference. Making the gate green by re-hiding them would trade a red metric for a false fact.

This needs a line in `AGENTS.md` naming the owner, which this workstream was instructed not to write. The owner of the 28 is the GRAIN-HUB workstream; the owner of the other 119 is whoever rebuilt `gaming_employment_observations.csv` and wrote `523_idgraph_q4_split_entity_suspects.csv` today.
