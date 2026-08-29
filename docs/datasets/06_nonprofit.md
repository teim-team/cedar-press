# Dataset 6 — Native Nonprofit & Philanthropic Economy

*Maintenance doc. Generated 2026-08-28. Tier: **Cedar Press+ ($1,000) - Native Nonprofits***

## What this is

Native-controlled, tribally affiliated and Native-serving nonprofits from IRS records. Adds EIN to the spine.

## Files

| File | Rows | Size |
|---|---:|---:|
| `data/clean/np_orgs.csv` | 12,764 | 11 MB |
| `data/clean/np_ein_uei_bridge.csv` | 28 | 20 KB |

## Refresh

**Cadence:** Annual (BMF monthly snapshots; keep vintages — orgs vanish on revocation).

**Build:** `code/17_build_nonprofit_990.py, code/20_fix_nonprofit_authority.py`

Run `py -3 code/00_run_all.py --list` to see pipeline stages.

## NEVER do these

- Never quote the tier-A revenue aggregate. Tier A leaks place-named orgs (Umatilla Electric Co-op $592M, Yavapai Community Hospital $497M). 412 tier-A rows are awaiting a ruling.
- Never treat the 4,656 exclusions as hand rulings. They are authority_class = automated_filter, fired from regex — reversible, unlike the cited per-UEI drops.
- Never use NTEE codes to classify Native status. Weak signal only.

## Known issues and caveats

- Tribal instrumentalities largely DO NOT file 990s (IRC §7871) — the LARGEST tribal institutions can be invisible here. State what the dataset cannot see.
- 990-N postcard filers (<$50K) yield existence only, no financials.
- Fiscal sponsorship hides orgs that never hold an EIN. Churches are exempt.
- Filing lag is 1–2 years; the 'current year' is always trailing.
- The upstream 'intercoder reliability' is NOT reliability-validated: pairwise κ < 0.05 for every pair but one (0.143). It is a ≥3-of-5 coverage threshold.

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