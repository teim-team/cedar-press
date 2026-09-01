# Tribal-State Gaming Compacts

*Maintenance doc. Generated 2026-09-01. Tier: **Cedar Grove ($2,500) - Gaming Intelligence***

## What this is

Class III compacts and amendments — who may operate what, until when, and on what fiscal terms.

## Files

| File | Rows | Size |
|---|---:|---:|
| `data/clean/compacts.csv` | 707 | 674 KB |
| `data/clean/compact_versions.csv` | 1,158 | 910 KB |
| `data/clean/compact_terms.csv` | 1,311 | 1 MB |
| `data/clean/compact_events.csv` | 31 | 21 KB |

## Refresh

**Cadence:** Quarterly against the BIA compact index + FR notice sweep.

**Build:** `py -3 code/15a_compacts_inventory.py -> 15b_build_compact_index.py -> 15c_terms_pilot.py -> 15d_terms_extract.py -> 15e_finalize_terms.py`

Run `py -3 code/00_run_all.py --list` to see pipeline stages.

## NEVER do these

- Never trust the BIA index's Tribes column. It is misaligned with Title on 61 of 1,189 rows (5.1%) — Mohegan filed under Mississippi Choctaw, Mashpee under Mashantucket. Verified against archived HTML; it is BIA's error.
- Never collapse amendments. 'Current terms' is a COMPUTED VIEW, never a stored fact.
- Never propagate a facility-specific term tribewide — that is what applies_to is for.
- Never treat a disapproval or litigation as a deletion. They are events.

## Known issues and caveats

- 165 compacts are DEEMED-APPROVED (took effect by Secretarial inaction under 25 U.S.C. 2710(d)(8)(C)) and carry a legal asterisk. approval_type is first-class.
- Term recall is 53% (618/1,158 versions). Absent terms are UNEXTRACTED, not absent from the compact. This distinction must survive into any method note.
- Extraction traps found in piloting: a payout floor ('shall pay out a minimum of 80 percent') read as a revenue share; a 3-year amendment moratorium read as three terms; a non-tribal racino's cap attributed to a Pueblo; and an approval letter stating exclusivity was NOT provided being recorded as present. Every term row now carries doc_zone.
- Tier brackets are located but NOT parsed (21 rows). Highest-value curation target.

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