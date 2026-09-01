# Dataset 4 — Native Influence / Lobbying

*Maintenance doc. Generated 2026-09-01. Tier: **Cedar Press ($500) - Lobbying***

## What this is

Senate LDA filings by and about Native entities, including the government-entities-contacted field at scale — the part almost nobody parses.

## Files

| File | Rows | Size |
|---|---:|---:|
| `data/clean/native_entity_lobbying_disclosures.csv` | 27,796 | 18 MB |
| `data/clean/tribe_year_lobbying_panel.csv` | 4,997 | 952 KB |
| `data/clean/lobbying_unmatched_clients.csv` | 515 | 79 KB |

## Refresh

**Cadence:** Quarterly. Resume-safe; dedupes on filing_uuid.

**Build:** `code/lobbying_pull/`

Run `py -3 code/00_run_all.py --list` to see pipeline stages.

## NEVER do these

- Never match a client on a single generic token. 'Cherokee' alone must not reach Cherokee Nation; 'Creek' alone must not reach Berry Creek.
- Never collapse qualified tribe names — ABSENTEE SHAWNEE TRIBE OF OKLAHOMA is not the Shawnee Tribe. Three distinct governments were merged by this bug.
- Never sum client income and registrant expenses into one figure — self-filers report the latter. Keep the columns separate.

## Known issues and caveats

- LDA begins 1999. That is a STATUTORY floor, not a gap.
- API: page_size is capped server-side at 25; anonymous throttle ~15/min with Retry-After: 30; client_name is a token-PREFIX match, not substring ('ribe' returns RIBERA DEVELOPMENT).
- $3K/quarter de minimis means small entities need individual search.
- lda.senate.gov is under RFC 8594 sunset to lda.gov.
- The LDA carries NO UEI/CAGE/EIN. This dataset joins on name → entity_id only, so cross-dataset rulings reach it through the spine, not directly.

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