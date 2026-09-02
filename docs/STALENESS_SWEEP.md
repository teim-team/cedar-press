# Staleness sweep — what the other instruments cannot see

*Generated 2026-09-02 by `code/940_staleness_sweep.py`. Measured with `csv.reader` against the live files; nothing here is read from a manifest or a docstring.*

`830` answers *when was this entity last touched*, `630` *is this source behind its publisher*, `528` *does this entity have a website*, `527` *does a doc's number disagree with the data*. This one answers **does a shipped artefact still describe a world that no longer exists** — a column that was removed, a file that moved, a backup that acquired a shipping contract.

| check | n |
|---|---:|
| notes contracts naming a column the file does not have | 4 |
| notes contracts for a table that is not on disk | 0 |
| source files still naming a retired identifier or moved path | 24 |
| backups shipped into `dist/` | 0 |
| backups in `data/clean` named `.csv` last | 3 |

## Shipped contracts naming a dead column

| artefact | ghost columns |
|---|---|
| `dist\06_nonprofit\np_financials.notes.json` | EIN |
| `dist\06_nonprofit\np_grantee_financials.notes.json` | EIN |
| `dist\06_nonprofit\np_org_scale.notes.json` | EIN |
| `dist\06_nonprofit\np_orgs.notes.json` | ein |

## Source files still naming a retired identifier

| file | reference |
|---|---|
| `START_HERE.md` | tribe_id_scheme_resolved -> attribution_status |
| `code/335_harmonize_assistance_seams_in_place.py` | tribe_id_scheme_resolved -> attribution_status |
| `code/335_harmonize_assistance_seams_in_place.py` | tribe_id_scheme_resolved_basis -> attribution_basis |
| `code/335_harmonize_assistance_seams_in_place.py` | data/clean/assistance_tribe_id_crosswalk.csv -> data/spine/legacy/assistance_tribe_id_crosswalk.csv |
| `code/336_correct_scheme_resolution_by_spine_membership.py` | tribe_id_scheme_resolved -> attribution_status |
| `code/336_correct_scheme_resolution_by_spine_membership.py` | tribe_id_scheme_resolved_basis -> attribution_basis |
| `code/415_audit_identity_layer.py` | tribe_id_scheme_resolved -> attribution_status |
| `code/416_reconcile_spine_id_columns.py` | tribe_id_scheme_resolved -> attribution_status |
| `code/503_identity.py` | tribe_id_scheme_resolved -> attribution_status |
| `code/cedar_ids.py` | tribe_id_scheme_resolved -> attribution_status |
| `code/cedar_pipeline.py` | tribe_id_scheme_resolved -> attribution_status |
| `code/cedar_pipeline.py` | tribe_id_scheme_resolved_basis -> attribution_basis |
| `docs/ASSUMPTIONS_AND_LIMITATIONS.md` | tribe_id_scheme_resolved -> attribution_status |
| `docs/CEDAR_TAXONOMY.md` | tribe_id_scheme_resolved -> attribution_status |
| `docs/HANDOFF.md` | tribe_id_scheme_resolved -> attribution_status |
| `docs/IDENTIFIER_STANDARD.md` | tribe_id_scheme_resolved -> attribution_status |
| `docs/codebooks/03_federal_funding.md` | tribe_id_scheme_resolved -> attribution_status |
| `docs/datasets/_PUNCHLIST.md` | tribe_id_scheme_resolved -> attribution_status |
| `docs/datasets/_PUNCHLIST.md` | tribe_id_scheme_resolved_basis -> attribution_basis |
| `docs/methodology/funding.md` | tribe_id_scheme_resolved -> attribution_status |
| `docs/methodology/funding.md` | tribe_id_scheme_resolved_basis -> attribution_basis |
| `docs/methodology/_entity_layer.md` | tribe_id_scheme_resolved -> attribution_status |
| `docs/methodology/_entity_layer.md` | tribe_id_scheme_resolved_basis -> attribution_basis |
| `dist/03_federal_funding/federal_funding_transactions.NOTES.md` | tribe_id_scheme_resolved -> attribution_status |

## Derived artefacts and their age

| artefact | age | behind the newest clean table |
|---|---|---|
| `dist/notes_index.json` | 0d | yes |
| `dist/collection_descriptors.json` | 0d | yes |
| `dist/schema.sql` | 1d | yes |
| `docs/schema/dataset_contracts.json` | 0d | yes |
| `docs/schema/schema_index.json` | 7d | yes |
| `docs/schema/keys.json` | 7d | yes |
| `data/clean/codebook_master.csv` | 0d | yes |

## Sibling gates, called rather than re-implemented

| gate | exit | last line |
|---|---:|---|
| `830_entity_freshness.py` | 1 |   830 verify   FAIL   1 problem(s) |
| `941_refresh_codebook_fragment.py` | 0 | 941 verify   ok   0 codebook(s) documenting a retired column |
| `843_retire_cicd_scheme.py` | 0 | 843 verify   ok   0 CICD remnant(s) in the shipped tree |

