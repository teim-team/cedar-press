# Cedar Press — State of Build

*The single state document. Update this file; do not create parallel status memos.*
*Last updated: 2026-08-06*

> ## ⚠ SUPERSEDED — read `START_HERE.md` first. Flagged 2026-08-26.
>
> This file is **twenty days old and has not been touched since 2026-08-06.** It predates
> the archive backfill, the subaward promotion, the raw-match pass and the spine merges.
> It is, together with `STATE_OF_THE_LAND_2026-08-07.md`, one of the **two densest
> concentrations of superseded numbers in the project**.
>
> **It is deliberately not rewritten.** Its reasoning is still good and its record of how
> the project thought on 08-06 has value. Only its counts are dead. `START_HERE.md` is now
> the state document; **it wins on every conflict with this file.**
>
> Known-wrong figures on this page, measured against the CSVs 2026-08-26:
>
> | line | says | actually |
> |---|---|---|
> | :108 | subawards **67,229** | **63,548** — and 67,229 matches no file at any stage of the build |
> | :110 | lobbying **43,963** | **27,796** — flagged as an error by `docs/FACT_CHECK_2026-08-06.md` B-2/B-3 the same week; the raw pull is 39,448, so 43,963 is not "raw filings" either |
> | :118, :175 | spine **952** | **1,310** |
> | :126-127 | ledger **20,559**, tiers 1,708/5,963/12,711/177 | 20,559 is right; tiers are now **2,148 / 5,690 / 12,524 / 197** |
> | :176-177 | ledger **19,232**, tiers 1,705/4,637/12,711/179 | **wrong, and self-contradicting** — this file asserts two different ledger sizes fifty lines apart, neither naming the file it measured. 19,232 is the signature of the unsafe `09_import_rulings.py` rebuild that destroyed 1,327 rows (`AGENTS.md:33`). |
>
> Full register: `docs/DOC_CONTRADICTIONS_2026-08-26.md`.

---

## Documentation map

Three generated references. All three are measured from the data, so none can
drift from the files they describe — regenerate rather than hand-edit.

| What | Where | Regenerate with |
|---|---|---|
| What every variable means | `docs/codebooks/` | `py -3 code/41_build_codebooks.py` |
| Year coverage and gaps vs 2000–2026 | `docs/COVERAGE_AUDIT.md` | `py -3 code/35_coverage_audit.py` |
| How to maintain each dataset | `docs/datasets/` | `py -3 code/24_generate_dataset_docs.py` |

**Codebooks state what a variable is, never how it was derived.** The linkage
method is the product. Columns are tiered `public` / `subscriber` / `internal`:
internal columns would disclose the method and never ship; federal identifiers
sit at `subscriber` — licensed rather than hidden, because vendor name, year
and amount already join back to the public source, so withholding the UEI
would cost the subscriber their join key and cost a copyist nothing. The
defensible asset is the crosswalk from identifier to Native entity.

---

## How to run it

```
py -3 code/00_run_all.py            # full rebuild, ~10 seconds
py -3 code/00_run_all.py --list     # show all stages
py -3 code/00_run_all.py --from rulings   # after a batch of rulings
py -3 code/00_run_all.py --include-slow   # add the 4.4 GB FPDS rebuild
```

**The update loop.** Elijah rules in the review page → clicks Export → drops the CSV
into `review/rulings_inbox_<date>.csv` → `--from rulings` re-imports, propagates, and
regenerates the queue with settled items removed. Rulings accumulate across files and
are re-applied on every run, so re-running is always safe.

**Review page:** https://claude.ai/code/artifact/45b3551f-38be-4947-8549-ee6e7a3b0e98

---

## Temporal floor: 2000 (set by Elijah 2026-08-05)

**Every dataset targets 2000 → present.** Where a source cannot reach 2000, say so
explicitly. Where a source reaches *further back*, we still stop at 2000 for the
published product — consistency across datasets beats depth in one, and pre-2000 web
sourcing is materially thinner and harder to verify.

**Implementation — flag, never delete.** Pre-2000 rows already retrieved from
*authoritative archival* sources (Voteview roll calls to 1973, Federal Register to 1994,
LDA to 1999, BGOV contracts to 1991) are **retained with `pre_2000_flag = 1`** and
excluded from the default published view. Deleting them would violate the standing
never-drop rule and would discard records whose quality does not actually degrade —
a 1987 roll-call vote is not less reliable than a 2007 one. The rationale for the floor
is *web-sourced* material, so it binds hardest on the deals ledger and press sweeps.

| Dataset | Current reach | vs floor |
|---|---|---|
| Deals | 2020–2026 | **gap 2000–2019 — backfill running** |
| Federal contracting (prime) | 1991–2022 | meets; pre-2000 flagged |
| Subcontracting (2b) | 2010–2026 | **cannot reach 2000 — FSRS did not exist before FFATA.** Demonstrated, not assumed: FY2001–09 jobs returned 4,945 rows and *every one* carries `subaward_sam_report_year` ≥ 2010 (min = 2010, running to 2026), so those action dates are filer typos. Flagged `action_date_precedes_ffata_flag`, never deleted — which is why the coverage audit reports an observed floor of 2002 and "interior gaps" at 2005–06. Both are artifacts of the flagged typo band, not real coverage. **FY2021–2024 are genuinely thin** (165/87/99/127 countable rows) because the primary pull has not returned those years yet; they currently rest on the HigherGov export and the funding forward-fill alone. |
| Federal funding | FY2008–2023 | **gap 2000–2007** |
| Lobbying | 1999– | meets (LDA begins 1999) |
| Federal Actions (FR) | 1994–2026 | meets; pre-2000 flagged |
| Bills & Votes | Congress 93– (1973) | meets; pre-2000 flagged |
| Compacts | 1988– | meets; pre-2000 flagged |
| Nonprofit / 990 | e-file era | **cannot reach 2000 — state it** |
| Gaming — facility metrics | 1994–2026 | meets; `as_of_date` on 65,223 of 65,223 rows |
| Gaming — land decisions | 1990–2026 | meets; pre-2000 flagged |
| Gaming — facility openings | 1905–2025 | meets. **But the inherited `Open Date` column stops at 2018** — everything after it was dated by hand against primary sources, so recent years are as complete as the hand research is and no more. The `SOURCE_CEILINGS` entry was retired 2026-08-06: the remaining gap to 2026 is unfinished work, not a source limit. |

## The rule everything hangs on

**Never falsely attribute.** Missing coverage is acceptable and expandable; a wrong
attribution is not. Confidence tiers:

| Tier | Meaning |
|---|---|
| **A** | Hand-checked, verified against a retrieved source, structural inheritance, or ruled by Elijah. **Publishable.** |
| **B** | Algorithmic. Never publishes until ruled. |
| **C** | Unattributed. Discovery pool. |
| **X** | Matches an exclusion ruling. Never publishes. |

Authority order: Elijah's hand-checked work (Federal Spending folder, BGOV crosswalk,
ESM/HCI) outranks any automated method. On conflict, hand-checked wins and the
automated claim is demoted.

---

## Where every dataset stands (MEASURED 2026-08-06)

*Every number below is recomputed from `data/clean/` by
`code/62_no_regression_check.py` and written to `data/clean/_state_metrics.json`.
Do not hand-edit them - regenerate. A figure typed into a doc is a claim; a
figure read out of the data is a fact, and this project has already shipped
several of the former.*

| Dataset | Rows | State |
|---|---:|---|
| 1 Deals | 443 parties auto-resolved | 2000-2026; 661 of 724 deal rows keyed without a human |
| 2 Prime contracting | 617,142 | FY2000-2022 contiguous. $134.61B linked across 434 entities; **$78.04B publishable (tier A)**. FY2023-26 not yet pulled |
| 2b Subcontracting | 67,229 | FSRS floor is 2010, proven not assumed. Prime-side and subawardee-side kept apart |
| 3 Federal funding | 476,924 | FY2007-2026. Tribal recipient-type filter reproduced and validated |
| 3b FAADS | 2,769,748 | FY2001-2007. **No per-entity attribution before FY2007** - no recipient identifier exists in the source |
| 4 Lobbying | 43,963 | 1999-2026. 458 clients settled |
| 6 Nonprofit | 12,764 | 990 filers |
| 9 Federal actions | 156,466 | 1994-2026 |

## Spine and ledger (MEASURED 2026-08-06)

| Metric | Value |
|---|---:|
| Spine entities | **952** |
| Federally recognised tribes | 348 |
| Alaska Native villages | 229 |
| ANCSA village corporations | 173 |
| ANC regional corporations | 12 |
| State-recognised tribes | 64 |
| Intertribal organisations | 55 |
| Native Hawaiian Organizations | 31 |
| Identifier links | 20,559 |
| Tier A / B / C / X | 1,708 / 5,963 / 12,711 / 177 |
| Elijah rulings on file | **335** |
| Brands learned from those rulings | 89 |
| Codebook variables documented | 638 |
| FR recognised entities parsed (91 FR 4102) | 575 |
| Entities still linking to nothing | 273 |

## Invariants that must never regress

`code/62_no_regression_check.py` enforces these and its docstring carries ten
standing rules. It currently reports **no regressions**. Run it before and after
any change to the ledger, the spine, the resolver or the ruling importer.

Four things it watches, each because they were live defects:
- a ruling that names an owner must never end at tier X (cost $17.8B once)
- no tier-A link may lack an entity (was 16, now 0)
- no `tribe_id` may be absent from the spine (was 29, now 0)
- DUNS must never be publishable - it is D&B licensed

## Taxonomy (set 2026-08-05)

**Native entities** are the top level and the only roll-up targets:
`T-` tribes (federal + state) · `A-` ANCs (regional + village corps) · `N-` NHOs.

*In the spine these carry NEID-style prefixes:* `TRBF`/`TRBS` tribes ·
`AKNF` Alaska Native villages · `ANRC`/`ANVC` ANCs · **`NHO-`** Native Hawaiian
Organizations · **`ITO-`** intertribal organizations.

**Native organizations** are actors that may be *owned by* an entity:
`E-` enterprises + subsidiaries (parent **REQUIRED** — 1,367 are incomplete records) ·
`NP-` Native-focused nonprofits (parent optional) ·
`I-` intertribal orgs (**no parent** — they have members, not owners).

Two separate fields, never collapsed: `parent_native_entity` is **ownership** and drives
attribution; `serves_native_entities` is **who it serves** and does not. An org can serve
a community it is not owned by.

## THE DEALS CHARTING RULE

The ledger now holds two populations — **622 "Grant / public financing" rows against 116
acquisitions**. The federal-award share by year: 0% pre-2010, 85% 2019, 97% 2022, 93%
2024, 35% 2026. That swing tracks when TBCP and HUD ran competitive rounds, **not Indian
Country deal activity**. Never chart deals-by-year without splitting the two.

## Spine status

| Metric | Value |
|---|---|
| Spine entities | **952** (687 NEID backbone + 179 ANCSA village/group corps + 31 NHOs + 55 intertribal orgs) |
| Identifier links | 19,232 |
| Tier A / B / C / X | 1,705 / 4,637 / 12,711 / 179 |
| Publishable prime dollars | $90,876M |
| Exclusion rulings enforced | 123 (UEI) + 4,656 (nonprofit) |
| Elijah rulings on file | 25 |

**Universe ceilings** — coverage is a fraction of a known denominator:
575 federally recognized tribes · 196 ANCs (13 regional incl. the defunct Thirteenth,
retained for historical panels) · 190 DOI NHO roster (a **consultation** list, not a
contracting registry — the 185 unverified rows stay a tier-C discovery pool) →
33 contracting NHOs verified, **31 in the spine** · 57 intertribal organizations,
**55 in the spine** (AVCP and Tanana Chiefs Conference were already there as `SGVF`) ·
64 state-recognized tribes carried by the CICD connector.

**NHO + intertribal layer added 2026-08-06** — `code/61_add_nho_intertribal_to_spine.py`,
866 → 952 entities. First federal contracting dollars ever attributed to an NHO in
this project ($88.3M across 6 UEIs). Membership joins through
`data/clean/nho_ito_spine_crosswalk.csv`. See `docs/NHO_SPINE_MERGE_LOG.md`.

---

## Datasets

| # | Dataset | Status | Rows |
|---|---|---|---|
| 1 | Indian Country Deals | Inherited, not extended | 132 |
| 2 | Federal contracting (prime) | Spine + ledger built | 19,232 links |
| 3 | Federal funding | **Merged. Regression test PASS** | 476,924 tx / 5,496 tribe-yr |
| 4 | Lobbying | Agent running | — |
| 5 | **Linked analytical file** | **Built.** Deals/bills/compacts unjoinable | 10,845 entity-yrs / 99 ownership events |
| 6 | Nonprofit / IRS 990 | Built | 12,764 orgs |
| 9 | Federal Actions (FR) | Built | 156,452 docs |
| 10 | Bills & Votes | Built | 3,037 bills / 423 votes / 136,119 positions |
| — | Compacts | Built | 707 / 1,158 versions / 1,311 terms |
| — | Gaming (Phase 1) | Decision index + directory core built | 138 decisions / 265 events / 774 facilities / 65,223 metric observations |

---

## Corrections made this build — do not re-introduce

1. **BGOV ends 2020, not 2023.** 1991–2020, 241 tribes. Prime-contracting gap is six
   years.
2. **Federal funding does NOT thin after 2022.** The 592→409 drop was a
   `first_seen_year` artifact. True FY tribe counts: 598/535/554/550.
3. **8(a) does not prove NHO ownership.** It admits both entity-owned and
   *individually* disadvantaged-owned firms. HALOA Construction (8(a), family-owned)
   disproved it. Script 06 called 36 firms NHO-verified; only 12 are, and only
   because Elijah ruled them. Script 19 supersedes it.
4. **Exclusions have two kinds.** *Ownership* exclusions block globally. *Scope*
   exclusions (comment reads `ANC`, or a state-recognized entity in a
   federally-recognized-only analysis) must NOT block — applying them globally
   falsely flagged a $302.5M Doyon attribution.
5. **USAspending assistance has no EIN and no CAGE columns.** EIN comes from IRS-990 /
   SAM enrichment only.
6. **FPDS cannot give multi-level corporate trees.** `immediate_parent_uei` and
   `domestic_parent_uei` are populated on 0 of 2,279,891 rows. Flat root→child only.
7. **`fed_funding_do_file_corrtd.do` does not rebuild its own `.dta`.** The Oneida
   renumbering was left incomplete — line 696's WI catch-all still sits after the NY
   rulings at 684–685, and line 1516 still says 204. Run literally it puts all $1.06B
   of Oneida money on 205. The `.dta` is the authority (204 = NY, 205 = WI); script 24
   re-applies lines 686/684/685 last and flags every row it touches. Do not "fix" the
   do-file silently.
8. **Never dedup federal funding on `(award_id, uei, family)` keeping max-$.** MR-7.
   That operator discarded ~$60.6B of unequal-value rows, 83.7% of them distinct
   fiscal-year slices of live awards. Dataset 3 has no dedup step at all — the
   transaction key is already 1:1 across all 476,924 rows.

---

## Live warnings

- **`code/09_import_rulings.py` has no ruling grammar, and it is corrupting rulings.**
  Its `named owner NOT in the spine` count is read as a spine gap. Measured
  2026-08-06: of 67, **57 are ruling SHAPES, not owner names** — `Named for a place -
  demote` (42 ledger rows), `Not a Native entity` (7), `No - not this entity` (2),
  `NATIVE ORGANIZATION - …` (3), `MULTI-ENTITY …` (1), and two more. Script 09 feeds
  each phrase to a spine resolver and sends the link to tier X. `code/33` parses all
  of these correctly; **port its `NOT_NATIVE_RE` / `ORG_RE` / `MULTI_RE` into 09.**
  Two more of the 67 are resolver ambiguity against entities already in the spine
  (below). Only 8 were ever real spine gaps.
- **`resolve_entity` cannot separate an Alaska village GOVERNMENT from its ANCSA
  CORPORATION.** `core()` strips `native`, `village` and `corporation` as structural,
  so `Native Village of Eyak` and `Eyak Corporation` both reduce to `{eyak}` — and
  `Tyonek` likewise. Both return `ambiguous_core:2_spine_entities` and both strand a
  ruling. The distinction script 52 exists to preserve is lost at the resolver. Fix
  using the raw string `core()` discards.
- **`NHO-MANUKAI-00` conflates at least 17 unrelated organisations** — 19 links, 16
  from the quarantined `need_v6`. Ailani Hawaiian Defense/Federal/Solutions/Technology,
  Hungry Hawaiian LLC, Hawaiian Steam Inc, Native Hawaiian Legal Corporation and
  **Council for Native Hawaiian Advancement (I-012, a wholly different organisation)**
  all sit under it. All tier C, so nothing publishable is wrong today. Split before any
  of them leaves tier C. `review/nho_ledger_id_conflations_2026-08-06.csv`.
- **`ALAKA'I FOUNDATION, INC.` is not `ALAKA'INA FOUNDATION`.** Two organisations, two
  letters apart, both in the spine (`NHO-ALAKA1-00`, `NHO-ALAKAI-00`). Never merge.
  `Alaka'i Services Group Inc.` is ASGI, the *subsidiary* of the former, and is
  deliberately **not** a spine entity.
- **The nine Alaka'ina firms became ANC-owned in June 2026.** Wholly acquired by Bering
  Straits Native Corporation; the Foundation itself remains an NHO. Month precision
  only — `data/clean/nho_ownership_changes.csv`, `date_usable_for_attribution = 0`.
  FPDS does not update retroactively, so pre-event awards stay NHO-attributed.
- **Audited financial statements outrank a newsroom release on a deal's DATE and VALUE.**
  Newsroom dates ran 2–16 days *later* than the audited acquisition date in every ANCSA
  case checked — a one-directional bias that moves a transaction into the wrong year
  near a boundary. UIC/Northbank was announced 2026-01-16 and audited at 2025-12-31;
  keeping the press-dated row inflated 2026 YTD by one acquisition. `ND-2026-077` and
  `ANCSA2-2020-003` were withdrawn to `review/deals_withdrawn_duplicates.csv` (whole,
  with reason and successor); the rule is in `docs/datasets/01_deals.md`.
- **Agent deals rulings are NOT Elijah rulings.** `data/clean/deals_party_attribution.csv`
  is Elijah's, 34 parties, final. `data/clean/deals_party_attribution_agent.csv` is
  agent research, 530 parties, applied by `code/53_apply_agent_deals_rulings.py` under an
  asymmetric standard: exclusions land at X, inclusions need a primary source (BIA FR
  notice for the entity ITSELF, SEC filing, tribal .gov page, or the firm's own About
  page) to reach A — otherwise B, queued in
  `review/deals_party_agent_needs_elijah_2026-08-05.csv`. Never feed that file through
  `code/33`/`code/09`; the `rulings_inbox_*` glob is Elijah's authority and lands at A.
- **`data/clean/ownership_events.csv` still contains the withdrawn `ND-2026-077`.** It is
  a derived output of `code/31_build_dataset5_linked.py` and needs a rebuild.

- **Never sum FSRS subaward dollars without filtering `subaward_exceeds_prime_flag`.**
  Amounts are filer-entered and unaudited. Across the full 6,613,471-row pull, **54,469
  rows (0.82%) report a subaward LARGER than its own prime award**, totalling **$1.42
  trillion**. Worst case: prime `N6945011M3601` is a **$64,910.88** award whose reported
  subaward to GEOPAVE LLC is **$794,526,041** — 12,240×, for "asphalt and stripe parking
  spaces". Inside promoted Dataset 2b the rule removes **492 rows carrying $5.96B**, a
  quarter of the unfiltered total. Flagged with `subaward_to_prime_ratio`, never deleted.
  The rule now lives in `code/24_generate_dataset_docs.py`'s SPEC, so regenerating the
  docs cannot wipe it.
- **`subawards.csv` needs TWO filters, not one.** The countable set is
  `duplicate_status == 'primary'` **and** `subaward_exceeds_prime_flag != 'yes'`. All
  55,035 rows are retained; 12,446 are `exact_repeat_within_source` and 846 are
  `superseded_by_primary_source`.
- **NEVER dedupe subawards on `(prime_award_id, subaward_number)`.** It is not unique and
  the collision is not a duplicate. FEMA grant `1843DRAKP0000000` reports subaward number
  `1843-GR35056` against **eleven different Alaska Native villages** — Eagle, Tuluksak,
  Akiak, Akiachak, Tanana, Fort Yukon, Kwethluk and more. That key would have destroyed
  **22,644 of 53,417 rows** and merged eleven tribes into one. This is MR-7 in a new
  costume. The identity key is `(prime_award_unique_key, subaward_number, subawardee_uei,
  action_date, amount, description)`.
- **Penn State and George Mason are attributed to tribes at ledger tier B.**
  `PENNSYLVANIA STATE UNIVERSITY, THE` → `TRBF-LWSXMN-00` (3,301 subaward rows, ~$987M)
  and `GEORGE MASON UNIVERSITY` → `AKNF-PRBLFC-00` (1,346 rows, ~$425M). Tier B never
  publishes, so nothing ships wrong — but **any tier-B aggregate is corrupted by them.**
  432 tier-B entities carrying ≥$1M each, $9.84B in total, are queued in
  `review/subaward_tierB_attribution_review_2026-08-06.csv`. Tier A alone is $8.03B.
- **The population-(b) "state pass-through" shape holds by ROW COUNT, not by DOLLARS.**
  At 1,074 rows (FY2001–11) the primes paying Native subawardees looked overwhelmingly
  like state agencies. At 21,954 rows the count is still dominated by that channel
  (16,941 assistance vs 5,013 contract subawards), but the **dollar** ranking is led by
  defense and commercial primes — Alcyon Technical Services JV $972M, Indyne $552M,
  Exelis $506M, Lockheed Martin $480M. State agencies (SC Employment & Workforce $103M,
  PA Public Welfare $79M) rank lower. Report the channel by count, or say which.
- **Prime contracting has a six-month hole nobody has filled: 2022-10-01 → 2023-04-04.**
  `prime_contracts.csv` ends at FY2022 (2022-09-30). The 2026-08-05 gapfill starts at
  **2023-04-05**, a date taken from the raw extracts' max `action_date`. The first half
  of FY2023 is therefore in *neither*. Any FY2023 figure built from the gapfill alone
  understates it by roughly half a year. `code/44_pull_contracts_transactions.py` starts
  FY2023 at 2022-10-01 for exactly this reason.
- **`prime_contracts.csv`'s `attributed_flag` is a stale snapshot of a LIVE ledger.**
  `data/clean/cedar_identifier_ledger_final.csv` was rewritten twice inside one hour on
  2026-08-06 (tier-A UEIs 823 → 781 → 787; tier-A links 1,740 → 1,699). Row total held at
  13,191, so this is **re-tiering, not ingestion**. Under the newer ledger **13,945 rows
  lose attribution and ~3.3% of attributed dollars move.** Never hardcode an attributed
  total as a validation target — recompute it by applying the current ledger to the spine
  and record the ledger's sha256 and mtime beside the result.
- **The ledger-UEI route reproduces the ATTRIBUTED spine, not the whole spine** — 70.6%
  of FY2019 dollars, 69.9% FY2020, 72.6% FY2021, **66.0% FY2022**, and *declining*.
  Validating a ledger-scoped pull against the full spine total would show a false ~−30%
  failure. Coverage will be lower still in FY2023–26; that forward-fill is a lower bound
  that loosens each year, and must publish as one.
- **`recipient_parent_uei` is not one value per recipient.** In the gapfill award
  summaries **528 of 4,023 recipients (13.1%)** report more than one parent, from two
  different causes: self-parent placeholders (`parent == recipient`), and genuine
  ownership changes that FPDS never backfills — ASRC Federal Facilities Logistics appears
  under both Arctic Slope and SAIC. Collapsing to last-seen picks one arbitrarily by file
  order. Drop self-parents; keep real conflicts as separate dated edges. Note that after
  dropping self-parents the spine's "11,449 distinct parent UEIs" falls to **656**.
- **`TRBF-KTNIID-00` conflates two distinct tribes** — tier A, `attribution_method=hand`.
  Its UEIs cover both the **Kootenai Tribe of Idaho** and the **Confederated Salish and
  Kootenai Tribes** of the Flathead Reservation, Montana (`Cs&Kt`, Salish Kootenai
  College, the S&K company family). Any per-tribe total for either is wrong. Needs a
  ruling.
- **`need_v6` is quarantined.** 9 rulings against, 0 for. **1,993 links** rely on it.
  Prioritized in the review queue.
- **The BIA compact index is defective at source** — `Tribes` misaligned with `Title`
  on **61 of 1,189 rows (5.1%)**; Mohegan filed under Mississippi Choctaw, Mashpee
  under Mashantucket. Verified against archived HTML. **Every prior extraction
  inherited it unflagged, including `compact_master_aiannh.csv` and
  `tribe_compact_history.csv` in votingpatterns**, which that project's README
  designates cross-project authoritative. See `docs/VOTINGPATTERNS_BIA_INDEX_WARNING.md`.
- **Do not quote 63,248 FR "rulemakings" as tribal.** Only 14.2% of the FR corpus names
  a tribal term in its own title/abstract; use `title_abstract_term_hit`. The ten named
  buckets (2,794 rows) are 82–100% precise.
- **Do not quote the $2.51B nonprofit tier-A revenue aggregate.** Tier A leaks
  place-named orgs (Umatilla Electric Co-op $592M, Yavapai Community Hospital $497M).
- **990 "intercoder reliability" is not reliability-validated.** Pairwise κ < 0.05 for
  every pair but one (0.143). It is a ≥3-of-5 coverage threshold, not ICR.
- **Compact term recall is 53%** (618/1,158 versions). Absent terms are *unextracted*,
  not absent from the compact.
- **21 anti-tribal vote directions are circular** — assigned from the observed partisan
  split, against a Republican-margin outcome. Flagged and excluded from derived shares.
- **The BIA *gaming land decisions* index carries the same `Tribe(s)`-column defect** —
  **3 of 138 rows (2.2%)**: Graton Rancheria filed under Ewiiaapaayp, Tunica-Biloxi
  under Tonawanda Band of Seneca (and under Louisiana), Saint Regis Mohawk under
  Rappahannock. BIA's value is preserved verbatim and flagged
  `bia_tribes_column_conflict`; `tribe_from_title` carries the corroborated candidate.
- **Do not read `tier2A_agent_verified_real` as reported gaming revenue.** In
  votingpatterns' `per_property_gaming_revenue_FINAL_v3_audited.csv` that label
  certifies the *payment* was verified — **372 of its 435 "verified real" rows are
  compact-rate inversions** (OK ×20, CT ×4). The v2 vintage labeled them honestly as
  `tier2b_reverse_engineered`. Cedar Press derives `value_basis` from the metric.
  Only **126 of 592 gaming-revenue observations (21%) are reported revenue.**
- **Never split the Arizona gaming figure across tribes.** AZ compacts prohibit
  per-tribe disclosure; 19 per-tribe AZ rows in an earlier votingpatterns vintage were
  produced by proportionally guessing a statewide total. Carried state-aggregate only.
- **1,108 gaming capacity observations are proposal- or construction-stage** (Casino
  City `Planned` / `Under Construction`), incl. 298 machine counts. Read
  `observation_status` before quoting any slot count as a facility fact.
- **Two thirds of gaming `open_date` values are placeholders wearing day precision.**
  Of the 447 ISO opening dates inherited from the Casino City Tribal Property List,
  **150 fall on day 31** (147 of them `12-31`) and **148 on day 15** — against ~3%
  expected for each. `YYYY-12-31` is that source's year placeholder and day 15 its
  mid-month convention. `open_date_precision` now records the honest precision
  (**185 day · 288 year · 162 month**, refreshed 2026-08-06) and
  `open_date_not_before` / `open_date_not_after` carry the interval the source
  actually supports. The source value is unmodified. See
  `docs/GAMING_TEMPORAL_BUILD_LOG.md`.
- **Most "undated" gaming facilities are DUPLICATE ROWS, not missing research.**
  Of the 56 undated rows standing after the first sweep, **49 carried
  `duplicate_risk = 1`** — `votingpatterns_only_no_exact_casino_city_match` rows
  that describe a property already in the file under a Casino City name, with
  the date on the twin. Demonstrated, not assumed: researching `VP-0185` Kiowa
  Casino Red River from primary sources returned **2007-05-23**, byte-identical
  to the date already held on `CCP-773800`; two more matched their twin to the
  month or year. **Researching these harder is the wrong move** — it yields a
  second *dated* row for one property, which double-counts in any
  openings-by-year series. Candidates for a ruling are in
  `review/gaming_facility_duplicate_candidates_2026-08-06.csv` (**7 of the
  remaining 23 still have a STRONG twin**, down from 19 of 48 as dating
  progressed); nothing was merged. **Dedup before dating** — several rows dated
  on 2026-08-06 now sit opposite an already-dated twin.
- **Some gaming facility rows do not describe a real, distinct property.** Fifteen of
  the 56 facilities researched 2026-08-06 had an identity problem rather than a
  missing date. `VP-0169` "7 Clans Ponca Casino" fuses an
  **Otoe-Missouria brand**, a **Ponca** tribe attribution and an **Osage**
  location — a false attribution. `VP-0155` Peoria Ridge is a **golf course**.
  `VP-0160` "FireLake Express Grand" merges a casino name with the tribe's
  **grocery** chain. `TPL-0128` is a phantom travel plaza. `VP-0123` "Atoka"
  appears nowhere in 31,054 rows of the operator's archive history. `VP-0133`
  "WinStar additional plaza" is not a facility. The two **Emerald Queen** rows
  have `city` and `facility_name` disagreeing and may be swapped. **`VP-0393`
  Sage Hill is keyed to Shoshone-Paiute / Owyhee NEVADA but is a
  Shoshone-Bannock casino at Fort Hall, IDAHO.** Queued in
  `review/gaming_facility_identity_queue_2026-08-06.csv` (17 rows); nothing changed in
  `data/clean/`. **Searching harder cannot date a row whose subject is
  undefined.**
- **Two well-sourced gaming opening dates were deliberately NOT recorded.**
  `VP-0393` Sage Hill has a clean primary-source date ("opened … in February
  2009") that belongs to an **Idaho** casino, while the row is keyed to a
  **Nevada** tribe — applying it would have produced a false attribution wearing
  a verbatim citation, unfalsifiable by inspection. `VP-0116` "Pala Casino -
  hotel tower" is a sub-component whose submitted date is already carried by
  `VP-0011`. Both are rejected by name in the merge step with the reason
  attached. **A date's quality is not the only question — whose it is, and what
  row it lands on, are separate tests.**
- **`gaming_facilities.open_date` is NOT a uniform ISO column — do not parse it
  strictly.** Because the source value is never modified it holds 523
  `YYYY-MM-DD`, **111 bare `YYYY`** and one literal `1980s`; `close_date` holds
  133 ISO and **15 float artefacts** (`2019.0`). A strict parser drops 112
  opening dates *silently*, leaving a series that looks complete. The codebook
  declared both as `YYYY-MM-DD` until 2026-08-06. **Parse
  `open_date_not_before` / `open_date_not_after` instead — those are uniformly
  ISO with zero exceptions**, and they carry the interval rather than a padded
  point.
- **`gaming_facilities.open_date` is not reliably the ORIGINAL opening.** On **27
  facilities** it postdates an observation of the same property already operating
  (Apache Casino Hotel says 2012, observed open 2001), so it dates the current
  building or a re-opening. **Never chart openings by year without excluding
  `open_date_postdates_observation = 1`.** Four more rows close before they open.
- **`gaming_facilities.open_date` does not always mean "gaming commenced".** It
  also carries property-establishment dates. **Read `open_date_event` first** —
  refreshed 2026-08-06: `unspecified` on **447 of 636** stated dates (Casino City
  publishes an `Open Date` without saying which event it marks),
  `gaming_commenced` on 180, `property_opened` on 8, `not_gaming_commencement`
  on 1. Verified case: **Crosby Lodge, `1905-06-07`, day precision** — the
  operator's own site describes a lodge, store and bar with *no* gaming, "in the
  family since 1896", "your hosts since 1970".
  **The same defect exists above the pre-1979 detector's reach**, where no
  automatic rule can see it: **Lake of Isles (`VP-0002`, 2005) is Foxwoods' GOLF
  COURSE**, and its source quote says so — *"one of the top golf facilities in
  the country"*. Three more (Shoshone-Bannock 2019, Foxwoods 1992, Soboba 2019)
  date a replacement building over an operation that already existed. All four
  were publishing as `gaming_commenced`; they are now `property_opened`, ruled
  individually in `RULED_EVENT`.
- **`not_gaming_commencement` means VERIFIED, and only Crosby Lodge earns it.**
  Corrected 2026-08-06: the pre-1979 detector used to publish that value on the
  threshold alone, which asserts a negative it cannot carry — 1979 is the first
  year of *high-stakes* tribal bingo, not of tribal gaming, and small charitable
  bingo predates it. Rule-only rows now stay `unspecified` and carry
  `open_date_predates_tribal_gaming_era`, which fires on **4** rows.
- **The 50 pre-IGRA gaming facilities are correct and deliberate.** Seminole
  Classic 1979 (*Butterworth*), Sycuan 1982, Morongo 1983, Seminole Brighton
  1981 are the high-stakes bingo halls that produced IGRA. **Do not "clean"
  them.** Only 4 of the 50 are anything else (Crosby Lodge 1905, Singing Hills
  1956 and Pala Mesa 1961 are golf/lodge properties; Yaamava 1986 is a later
  building) and every one is named in `open_date_event`. **The filter you want is
  `open_date_event`, never the year.**
- **A land-decision date is not an opening date.** 13 undated facilities matched a
  BIA gaming-land decision on `(tribe, state)`; **12 were rejected** and only the
  Coquille/North Bend site-level match was used. The join would have asserted that
  Muckleshoot Casino — operating since the 1990s — could not have opened before
  2008.

---

- **The six unjoined datasets now carry an entity key** — `code/70_key_unjoined_datasets.py`,
  2026-08-06, log in `docs/ENTITY_KEY_PROPAGATION_LOG.md`. Compacts, compact
  events and terms, gaming facilities, gaming land decisions, ownership events
  and nonprofits carry `tribe_id` in place; bills, bill votes and federal
  actions get **bridge tables**, because a bill affects many tribes and one
  `tribe_id` would be a false attribution by construction.

  | | rows | keyed | tier A |
  |---|---:|---:|---:|
  | ownership_events | 98 | 94.9% | 77 |
  | compacts | 707 | 99.3% | 628 |
  | compact_terms | 1,311 | 99.4% | 1,205 |
  | gaming_land_decisions | 138 | 99.3% | 125 |
  | gaming_facilities | 774 | 97.8% | 213 |
  | np_orgs | 12,764 | 11.4% | 54 |
  | native_bills (bridge) | 3,037 | 18.7% | 548 links |
  | federal_actions (bridge) | 156,452 | 3.2% | 1,461 links |

  **`entity_id` is the publishable key and is written at tier A only.**
  `tribe_id` carries every match and must be read with `entity_tier`. Tier A
  means exact name, alias, documented ruling, or structural inheritance from a
  tier-A parent; core-set and containment matches are tier B and queued in
  `review/entity_key_tierB_promotion_queue_2026-08-06.csv`, where one ruling
  settles every row carrying that name.

  **RE-RUN 70 AFTER 15 / 17 / 23d / 31.** Each rebuilds a dataset 70 writes
  into and will silently return it to 0% keyed.
- **`member_positions.csv` is not keyed, by design.** It joins through `bill_id`
  to `native_bills_entity_bridge.csv`. A member's vote is a fact about a person.
- **Two false attributions were caught inside the new bridges before they
  published, and both were already-known traps in new clothes.** `Confederated
  Salish and Kootenai Tribes` split into CSKT plus the **Kootenai Tribe of
  Idaho** — the `TRBF-KTNIID-00` conflation, which the regression check only
  watches in the ledger. And the compact filed as `Oneida Nation` / **Wisconsin**
  resolves to spine `Oneida` / **NY** — the $716M Oneida mis-split. Both are
  refused or demoted by name, with the reason recorded on the row.
- **A place name alone is not an entity, in any free-text dataset.** The first
  pass of 70 put 157 Federal Register documents on the San Juan tribe (incl.
  `Business Development Center Applications: San Juan, PR`), 114 on Las Vegas
  Paiute, and `St. Mary's County, MD` on an Alaska Native village. Free-text
  tier A now requires a tribal designator in the span or within a few tokens of
  it. This is the same defect as the 282 place-name nonprofits; expect it again
  in the next text dataset.
- **Dataset 5 has not yet been rebuilt against the new keys.** `code/31` still
  produces blank deal/bill/compact components on all 10,845 entity-year rows.
  The linking columns now exist; the rebuild is the remaining step, and it is
  the highest-value single run in the project.
- **Dataset 5's `assistance_usd` is NOT the do-file figure.** It attributes
  independently via `recipient_uei` → identifier ledger, because
  `tribe_id_neid` is still empty pending MR-4. It will not reproduce
  $107,047,741,074.94 and is not meant to. Only the do-file path is
  regression-tested. See `docs/DATASET5_LINKED_FILE_BUILD_LOG.md`.
- **Only 2011–2022 has all four Dataset 5 components in window** (prime 2000–2022,
  assistance FY2008–2023, subawards 2011–2023, lobbying 1999–). Any
  cross-component ratio outside that band compares a measured quantity to an
  unmeasured one. `data/clean/entity_year_coverage.csv` carries `in_source_window`
  per component per year.

## Open decisions for Elijah

1. **Federal funding NEID crosswalk.** The merge itself is **done and passing**
   (`code/24_funding_merge.py`, `docs/FEDERAL_FUNDING_MERGE_LOG_2026-08-05.md`):
   364,095 rows / $107,047,741,074.94 reproduced exactly, all 476,924 spine rows
   retained, zero dropped. What is still open is MR-4 — 975 recipient UEIs in
   `review/funding_tribe_candidates_2026-08-05.csv` need a ruling before
   `tribe_id_neid` can be populated and Dataset 3 can join the spine. Lineage A's
   integer `tribe_id` is local to the do-file until then.
2. **votingpatterns BIA correction** — flag only (done), or write the fix back?
3. Four do-file rulings: BIA-operated schools, ~120 "missing data" tribes, three
   self-declared coin-flip exclusions, state-recognized-tribe policy.
4. **Deals dataset** — still 132 rows against a 500 target. NTIA TBCP (274 awards,
   $2.2B) and HUD ONAP lists are robot-blocked and need manual download.

---

## Layout

```
code/           00_run_all.py + numbered stages, each independently runnable
data/raw/       esm_hci/ (5.14 GB archive) · external/ (staged copies + manifests)
data/spine/     entity spine · identifier ledger · exclusion rulings · cedar_rulings
data/clean/     tiered ledger · publishable set · per-dataset outputs
review/         rulings_inbox_*.csv · queues · cedar_review.html
docs/           per-dataset build logs
logs/           one log per script run
```

Cedar Press is **self-contained**: every stage stages its inputs into
`data/raw/external/` and builds from local copies. Nothing reads outside the folder at
runtime.
