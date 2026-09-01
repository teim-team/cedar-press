# Dataset 1 — Indian Country Deals

*Maintenance doc. Generated 2026-09-01. Tier: **Cedar Press ($500) - Indian Country Deals***

## What this is

Dated M&A, financing, land, and award events where a Native entity is a principal. The only dataset built from press rather than an API, and therefore the highest fabrication risk in the project.

## Files

| File | Rows | Size |
|---|---:|---:|
| `data/clean/deals_classified.csv` | 935 | 2 MB |
| `../../deals_2026_ytd.csv` | (live ledger) | |
| `../../deals_historical_2020_2025.csv` | (live ledger) | |
| `deals_*_additions.csv (9 files)` | (live ledger) | |

## Refresh

**Cadence:** Monthly newsroom sweep; quarterly deep pass with one historical year backfilled (reverse-chronological — link rot punishes delay).

**Build:** `py -3 code/build.py plan deals   (then run it; the ledger sweep itself is agent-driven and per-run). Promoted table is written by 57_autoresolve_deal_parties.py; 88_build_deals_taxonomy.py is on cedar_pipeline.NEVER_RUN and must not be used to rebuild it.`

Run `py -3 code/00_run_all.py --list` to see pipeline stages.

## NEVER do these

- **NEVER chart 'deals by year' without splitting negotiated transactions from federal awards.** The ledger holds two populations: 622 'Grant / public financing' rows against 116 acquisitions. The federal-award share is 0% before 2010, 85% in 2019, 97% in 2022, 93% in 2024, 35% in 2026 — that swing tracks when TBCP and HUD ran competitive rounds, NOT Indian Country deal activity. A combined series shows a hockey stick that is pure source composition.
- Never write a row whose DATE is not in retrieved evidence. Skip and log it.
- Never write a dollar figure you cannot re-read in retrieved text.
- Never file a deal by announcement year when the transaction year differs.
- **NEVER let a newsroom release date or price stand where the party's own AUDITED FINANCIAL STATEMENTS cover the same transaction.** See the dating rule below — this is a general precedence rule, not a per-row judgement.
- Never merge additions into the live ledger without Elijah reviewing.

## Known issues and caveats

- **THE DATING RULE: audited financial statements outrank a newsroom release, for both DATE and VALUE.** Where an ANCSA filer's (or any registrant's) audited statements cover a transaction, the acquisition date in the business acquisition note governs and the press release becomes a corroborating second source. Two reasons, and the second is the one that bites. (1) The audited date is the date control transferred — the filing consolidates the target from it, so it is the date the money actually moved; a newsroom release is published when communications got to it. (2) Newsroom dates in this corpus ran LATER than audited dates in EVERY case checked, by 2 to 16 days — a one-directional bias, never earlier. Near a year boundary that bias silently moves a transaction into the wrong year: UIC/Northbank was announced 2026-01-16 and audited at 2025-12-31, so the press date filed a 2025 transaction into 2026 and inflated 2026 year-to-date. CIRI/I2X (12 days) and CIRI/HABCO (6 days) shifted only within a month, but the same mechanism produced them. Consequence for the ledger: when a filing-sourced row and a press-sourced row describe one transaction, KEEP the filing-dated row, withdraw the press-dated row to `review/deals_withdrawn_duplicates.csv` with its reason, and carry the press URL onto the survivor as `Source_2` so no retrieved evidence is lost. Applied by `code/54_reconcile_deals_duplicates.py`; the reasoning is in `docs/ANCSA_PORTAL_V2_LOG.md` §5.
- **Withdrawn rows are not deleted rows.** `review/deals_withdrawn_duplicates.csv` carries every withdrawn row whole, plus `_superseded_by_deal_id`, `_withdrawn_from_file` and `_reason`. Check it before concluding a Deal_ID was lost.
- **A near-duplicate is not automatically a duplicate.** `review/deals_duplicate_candidates.csv` is a REVIEW queue and nothing in it is auto-merged: `ND-2013-004` ($43.6M) and `ND-2013-005` ($9.855M) are two genuine tranches of one Coos bond exchange on one day, and the tribal-debt sweep found that pattern repeatedly. The NTIA TBCP pairs share an identical `Deal_Title` because the title is built from the recipient name alone — they are distinct awards from two program rounds, and the titles are the defect.
- **SEC EDGAR is the highest-yield channel for 2000-2019** and it produced 24 of 40 backfill rows. Tribal gaming authorities carry public debt and are therefore SEC registrants: Mohegan, Seneca, River Rock, Choctaw Resort Development, Chukchansi, Inn of the Mountain Gods, Agua Caliente. ACCESS: WebFetch gets HTTP 403 on sec.gov; `curl` with a declared User-Agent returns 200.
- PRE-2004 DATING TRICK: 8-K item tagging did not exist before Aug 2004, but S-4 exchange-offer prospectuses restate the original private-placement date and amount in plain text, often three times. That is how every 2001-2004 row was dated.
- SEC filings yield MULTIPLE events on the same instrument (issue → exchange → restructure). Four such pairs are flagged in the rows' own Notes. Summing Announced_Value_USD blind will overstate capital raised.
- Reachability tracks WHETHER AN ENTITY HAD PUBLIC DEBT, not deal age. 2000-2005 yielded 11 rows — more than 2010-2017 managed in eight years. The genuine soft spot is 2010-2017: too recent for dense SEC coverage, too old for newsrooms. 2000 itself is the one hard year (1 row).
- The FEDERAL REGISTER produces ZERO deal rows for 2000-2019. Its 833 candidates there are NEPA notices, proclamations and statutory conveyances — they date PROJECTS, not transactions, and carry no counterparty or consideration. Use it as a lead index only.
- ANC annual reports are the LARGEST UNWORKED SEAM — 2 rows, and no annual-report PDF was ever located and read.
- Capture rate is driven by NEWSROOM STRUCTURE, not deal volume. Waséyabek and CNI yielded 16 of 31 rows because they publish dated permalinks; Doyon is far more acquisitive and yielded fewer.
- Intermediary search summaries have misreported YEARS (Graphite One came back 2024; the PR Newswire dateline says 2025). Always confirm against the primary dateline.
- Value traps seen: a ~$600M 'full deal value' estimate vs a $96M recorded deed price; planned equipment spend presented as purchase price; a VA grant to a STATE mis-framed as a tribal deal.
- BLOCKED (403/paywall): nana.com, ahtna.com, crainsgrandrapids.com, journalstar.com. These need manual download.

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