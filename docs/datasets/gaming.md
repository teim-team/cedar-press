# Tribal Gaming Development & Markets

*Maintenance doc. Generated 2026-09-01. Tier: **Cedar Grove ($2,500) - Gaming Intelligence***

## What this is

Two layers: the current facility universe (directory core) and the proposal-to-operation history reconstructed from federal decisions and NEPA documents. The development layer exists nowhere else.

## Files

| File | Rows | Size |
|---|---:|---:|
| `data/clean/gaming_land_decisions.csv` | 138 | 180 KB |
| `data/clean/gaming_decision_events.csv` | 265 | 127 KB |
| `data/clean/gaming_facilities.csv` | 787 | 1 MB |

## Refresh

**Cadence:** Quarterly index scrape; NEPA extraction is Phase 2 and pilot-gated.

**Build:** `py -3 code/build.py plan gaming   (46 tables, 7 declared rebuilders incl. 82_build_gaming_property_dataset.py, 91_build_nigc_declinations.py, 92_build_gaming_capacity_official.py)`

Run `py -3 code/00_run_all.py --list` to see pipeline stages.

## NEVER do these

- Never quote a proposal-stage number as a facility fact. 1,108 capacity observations are proposal/construction stage, including 298 machine counts.
- Never use decision STATUS alone. Scotts Valley is listed Approved but was rescinded 2025-03-27; Koi Nation is listed Approved with an FR reversal published 2026-04-02. Read the event stream.
- Never trust votingpatterns' tier2A_agent_verified_real. It certifies the PAYMENT was verified, not that revenue was reported — 372 of 435 rows are compact-rate inversions. Derive value_basis from the metric.
- Never bulk-parse NEPA documents without a piloted schema.
- Never read gaming_facilities.open_date as 'gaming commenced'. It carries BOTH that event and 'this property opened', which differ on a site that existed before it hosted gaming — Lake of Isles is Foxwoods' GOLF COURSE (2005) and Crosby Lodge is a verified non-gaming lodge (1905). Read open_date_event first; it is `unspecified` on 446 rows because the source does not say, and that is what the source supports, not a defect.
- Never treat open_date as day-precise. Two thirds of the inherited ISO values are placeholders wearing day precision — YYYY-12-31 is the source's year placeholder and YYYY-MM-15 its mid-month convention. Read open_date_precision and use open_date_not_before/not_after.
- Never chart openings by year without excluding open_date_postdates_observation = 1 (27 rows date a rebuild, not the original opening) — and never filter out the pre-IGRA rows. The 50 facilities dated before 1988 are mostly the high-stakes bingo halls whose litigation PRODUCED IGRA; only 4 are anything else and all 4 are named in open_date_event. The filter you want is open_date_event, not the year.
- Never infer an opening date from a BIA land-decision date. The lag is real, variable, and not a fact we have. Of 13 (tribe, state) matches, 12 were rejected — the join asserted Muckleshoot Casino could not have opened before 2008, when it has operated since the 1990s.

## Known issues and caveats

- Only 126 of 592 gaming-revenue observations (21%) are REPORTED revenue — essentially Connecticut slot win. 372 payments-derived, 56 modelled, 38 reverse-engineered.
- The BIA gaming index has the SAME Tribe(s)-column defect as the compact index (3 of 138 rows). Two BIA indexes with identical breakage — assume any future BIA scrape has it until checked.
- STRUCTURAL BIAS: only projects requiring a federal action appear. Routine on-reservation building never enters this pipeline. BIA also states its list is not exhaustive.
- BIA writes 'Two-Part Secretarial Determination', not the plan's shorthand.

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