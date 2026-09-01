# Dataset 2 — Federal Contracting (Prime)

*Maintenance doc. Generated 2026-09-01. Tier: **Cedar Press+ ($1,000) - Federal Prime Contracting***

## What this is

Prime contract obligations to Native entities, resolved through the identifier spine. The spine itself (687 entities, UEI/CAGE/DUNS/EIN) underpins every other dataset.

## Files

| File | Rows | Size |
|---|---:|---:|
| `data/clean/cedar_identifier_ledger_final.csv` | 20,577 | 5 MB |
| `data/clean/cedar_publishable_identifiers.csv` | 1,577 | 344 KB |
| `data/clean/fpds_uei_edges.csv` | 5,167 | 2 MB |
| `data/clean/fpds_uei_cage_map.csv` | 34,601 | 8 MB |
| `data/clean/cedar_cage_backfill.csv` | 4,362 | 467 KB |

## Refresh

**Cadence:** Quarterly. Re-run `--include-slow` to rebuild FPDS edges from raw.

**Build:** `code/01, 03, 13, 18`

Run `py -3 code/00_run_all.py --list` to see pipeline stages.

## NEVER do these

- Never publish above tier A. Rulings are the only promotion path.
- Never inherit ownership through UEI NW2RJN8TQQW1 — that is the federal registrant roll-up ('GOVERNMENT OF THE UNITED STATES', 29 children incl. BIA and IHS). It is blocklisted in code/18.
- Never inherit ownership along a prime_to_sub edge. That is a contracting relationship, not ownership.
- Never repair a malformed CAGE silently. Flag it.

## Known issues and caveats

- BGOV crosswalk ends 2020, not 2023. Prime-contracting gap is 2021–2026.
- FPDS populates ultimate_parent_uei but NEVER immediate_parent_uei or domestic_parent_uei (0 of 2,279,891 rows). No multi-level trees are possible from this source; flat root→child only.
- 9 CAGE codes are Excel-corrupted at source — 7 leading-zero-stripped (Boeing 3953 is really 03953), 2 unrecoverable scientific notation. Flagged, not repaired.
- 190 of 1,805 children carry more than one ownership parent — real (firms sold between ANCs). Resolve by year window, never assume uniqueness.

---

**House rules that apply to every dataset:**

- Never falsely attribute. Missing coverage is expandable; a wrong attribution is not.
- Only tier A publishes. Elijah's rulings are the only promotion path.
- Flag, never delete. Retain and mark rather than drop.
- Cedar Press is self-contained — stage inputs into `data/raw/external/` and build from local copies.
- Temporal floor is 2000; pre-2000 rows carry `pre_2000_flag = 1`.

See `STATE_OF_BUILD.md`, `docs/CROSS_DATASET_LEARNING.md`, and `docs/COVERAGE_EXPANSION_OPTIONS.md`.

## Reference

- **Codebook** — `docs/codebooks/` defines every variable, its type and units. Regenerate with `py -3 code/41_build_codebooks.py`; it is measured from the data, so it cannot drift from the files.
- **Oddities** — `docs/DATA_ODDITIES.md` states what a zero, a negative and a blank MEAN in each dataset. They are not rare: 9.7% of contract rows are negative (deobligations, which belong in the total) and 9.9% are zero (actions that moved no money). Zero is an assertion; blank is a silence; neither is an error. Never filter an oddity out silently - flag it, count it, explain it.
- **Refresh cadence** — `docs/REFRESH_CADENCE.md` gives the pull schedule for every dataset, the incremental change key for each source, and the re-run chain that must follow ANY refresh. Refresh on the SOURCE's clock, not ours: pulling a quarterly source weekly earns rate limits, and every unnecessary rebuild is a chance to lose a hand correction (`code/31` once silently reset a dataset from 93 keyed to 0).
- **Coverage** — `docs/COVERAGE_AUDIT.md` reports the observed year range and any gaps against the 2000-2026 target. Regenerate with `py -3 code/35_coverage_audit.py`.

A codebook says WHAT each variable is. It deliberately does not say how a value was derived - the linkage method is the product, so columns whose values would disclose it are marked internal and withheld from published extracts.