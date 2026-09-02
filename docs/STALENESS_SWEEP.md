# Staleness sweep — what the other instruments cannot see

*Generated 2026-09-02 by `code/940_staleness_sweep.py`. Measured with `csv.reader` against the live files; nothing here is read from a manifest or a docstring.*

`830` answers *when was this entity last touched*, `630` *is this source behind its publisher*, `528` *does this entity have a website*, `527` *does a doc's number disagree with the data*. This one answers **does a shipped artefact still describe a world that no longer exists** — a column that was removed, a file that moved, a backup that acquired a shipping contract.

| check | n |
|---|---:|
| notes contracts naming a column the file does not have | 1 |
| notes contracts for a table that is not on disk | 0 |
| source files still naming a retired identifier or moved path | 0 |
| backups shipped into `dist/` | 0 |
| backups in `data/clean` named `.csv` last | 3 |

## Shipped contracts naming a dead column

| artefact | ghost columns |
|---|---|
| `dist\05_entities\tcu_cdfi_added.notes.json` | cicd_verified |

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
| `830_entity_freshness.py` | 0 |   830 verify   ok   0 problem(s) |
| `941_refresh_codebook_fragment.py` | 0 | 941 verify   ok   0 codebook(s) documenting a retired column |
| `843_retire_cicd_scheme.py` | 0 | 843 verify   ok   0 CICD remnant(s) in the shipped tree |

