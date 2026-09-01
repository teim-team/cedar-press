# Dataset 2b — Subcontracting

*Maintenance doc. Generated 2026-09-01. Tier: **Cedar Press+ ($1,000) - Federal Subcontracting***

## What this is

Subaward relationships in both directions: Native entities as SUBS under non-Native primes (a revenue channel prime data misses entirely), and Native primes' own subcontractor networks (observed input-output linkage, which feeds TEIM leakage structure).

## Files

| File | Rows | Size |
|---|---:|---:|
| `data/clean/subawards.csv` | 72,837 | 58 MB |
| `data/clean/subaward_identifier_harvest.csv` | 304 | 44 KB |
| `data/clean/prime_sub_network.csv` | 220 | 33 KB |
| `data/clean/subaward_identifier_netnew.csv` | 210 | 44 KB |

## Refresh

**Cadence:** USAspending/FSRS bulk_download `sub_award_types=[procurement, grant]`, one fiscal year per request (`date_range` is capped at one year), `date_type=action_date` (keys on the SUBAWARD action date, not the prime's). No recipient filter — the full federal subaward universe is what gives 2b a denominator. Re-run code/41_match_subawards_to_ledger.py then code/45_promote_subawards.py; both are idempotent. The 2023 HigherGov export is superseded: it was a different population, not a sample — only 19 of its rows recur in the primary-source pull.

**Build:** `code/20_build_subcontracts.py → code/45_promote_subawards.py`

Run `py -3 code/00_run_all.py --list` to see pipeline stages.

## NEVER do these

- NEVER SUM FSRS SUBAWARD DOLLARS UNFILTERED. Amounts are filer-entered and unaudited, and a subaward that exceeds its own prime award is arithmetically impossible, so every such row is a source defect. In the 2026-08-05 pull 5,941 of 345,090 rows (1.7%) reported a subaward LARGER than its prime, totalling $68.7B. Worst case: prime N6945011M3601 is a $64,910.88 award whose reported subaward to GEOPAVE LLC is $794,526,041 — 12,240x — for 'subgrade repairs, asphalt and stripe parking spaces'. Among Native-linked rows, 17 rows (0.9%) carried 54.6% of all dollars, and that single GEOPAVE row alone put a state-recognized tribe at the top of the subcontracting-out league table. ALWAYS filter `subaward_exceeds_prime_flag` before any total, mean, rank or chart. Both that flag and `subaward_to_prime_ratio` are carried on every row. Rows are FLAGGED, NEVER DELETED, per the house never-drop rule.
- Never pool population (a) with population (b). `direction` separates them: (a) a_native_as_prime is a Native entity subcontracting OUT; (b) b_native_as_subawardee is a Native entity RECEIVING from a prime. They are different economic relationships measured in opposite directions, and summing them double-counts the `both` rows besides.
- Never count a ledger tier-C hit as an attribution. Tier C is literally 'No attribution - discovery candidate' and `tribe_id` is blank on all but a handful of tier-C ledger rows (measured 2026-08-06: 12,681 blank of 12,711; tier C is 12,524 as of 2026-08-26 — recompute rather than quoting either). A first pass that counted tier C reported 285 linked rows on FY2010 where the true figure is 113 — it fabricated attributions at roughly 2.5x. Only tiers A and B with a non-blank tribe_id are links.
- Never read subcontract-05-09-*.csv by column NAME — it ships two columns both literally named 'CAGE Code' (pos 22 = Prime Awardee, pos 23 = Prime Parent). Read positionally.
- Never treat naics/psc as the SUB's industry — they are the PRIME award's codes. An I-O linkage built on them describes the demand side, not the supplier.
- Never compute leakage without filtering self-edges (prime_uei == sub_uei).
- Never chart the most recent fiscal year as a decline — FY2026 was pulled mid-year and is partial by construction.
- Never chart by `subaward_date` without excluding `action_date_precedes_ffata_flag` — it would publish a phantom FY2001-09 series built entirely on filer typos.

## Known issues and caveats

- FSRS is threshold-gated, self-reported and unaudited. Absence of a subaward is NOT evidence of no subcontracting; every total is a lower bound.
- Population (b) — the valuable direction — is overwhelmingly STATE AGENCIES passing federal grants through to tribal governments (WA OSPI to Makah, Montana DOT to Fort Peck, WI DPI to Menominee). That channel is invisible in prime contracting (the prime is a state) and in federal funding (the recipient of record is a state). Anyone measuring federal dollars reaching tribes from prime awards alone undercounts by this entire channel.
- Assistance subawards carry NO NAICS at all, so any industry cut silently restricts to the contract rows and drops the assistance rows — which is exactly where population (b) lives.
- FSRS began under FFATA and phased in during 2010, so 2010 is the permanent data floor. Demonstrated, not assumed: FY2001-09 jobs returned 4,945 rows and every one carries `subaward_sam_report_year` >= 2010 — including a SpaceX subaward dated 2000-11-09 and filed in 2024. Those action dates are filer typos.
- The 682 rows sourced from the federal-funding forward-fill (Assistance_Subawards_*.csv) are NOT a full-universe slice. That pull filtered `recipient_type_names=indian_native_american_tribal_government` on the PRIME, so the prime is a Native entity by construction and the file cannot observe population (b) at all. The rows whose ledger match falls only on the subawardee side have intertribal-organization primes (Northwest Indian Fisheries Commission, USET, CRITFC, tribal health boards) that the ledger declines to attribute to a single tribe because they have members, not owners. Carried as direction (a) with `source_population=prime_tribal_filtered`.
- The HigherGov query definition was not preserved, so its sampling frame is unknown. No share-of-market claim was ever supportable from that file; from the unfiltered primary-source pull it is.
- Subaward Number is NOT unique. The key is Prime Award ID + Subaward Number, and even that repeats across amendment rows — 18 duplicate keys sit inside the 998 inherited HigherGov rows alone.
- Tier B is not publishable. Most linked rows are tier B and need rulings first.

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