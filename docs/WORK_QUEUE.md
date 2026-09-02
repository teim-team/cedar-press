# Work queue — live

*Maintained 2026-08-26, **corrected 2026-08-28**. This is the plan of record for
what is running, what is next, and what each thing is waiting on. Update it when
you finish something; do not leave the only record of a decision in a chat
message.*

---

## CORRECTIONS 2026-08-28 — three items below are STALE

Found by re-reading this file against the actual files. Recorded here rather
than silently edited in place, per the project's own convention.

1. **The Wayback host-lock claim near queue item 11 is WRONG.** It says the lock
   is stale with `active: true` and dead PID 7420, blocking two items for 19
   days. **Not true as of 2026-08-27.** `code/317_cdx_tribal_vendor_hosts.py`
   took the lock over legitimately, ran a **complete 49-host CDX sweep**
   (`requests_made: 74`, all 49 hosts in `downloaded_this_run`), and **released
   it at 2026-08-27T01:03:03**. The file now reads `active: false`. Snapshots
   are staged at `data/staging/tribal_vendor_lists/cdx/`. **Anyone scraping
   those 49 hosts should read the CDX output first rather than re-fetching.**
2. **The reconciliation artifact line ("400 clusters, $35.9B") is stale.** The
   artifact was rebuilt 2026-08-28: **539 clusters suppressed (was 507), open
   queue $26.22B (was $35.81B)**. The build script had been loading only the
   FIRST owner ruling export, so the 88-row / 33-cluster batch-2 file ($8.0B)
   was invisible to suppression and those clusters were being served back as
   unresolved. Fixed to glob all exports and to read both header shapes.
3. **Queue item 9 (NM/AZ regulators) is half done.** New Mexico was recovered on
   2026-08-26 — `www.nmgcb.org` was a **lapsed domain re-registered as a casino
   affiliate site**; the real regulator is `gcb.nm.gov`, and $3,059,077,514 of
   per-tribe Adjusted Net Win came back. **Arizona is still open.**

---

## 2026-08-28 — FIRST INDIVIDUALLY-OWNED NATIVE BUSINESS FACTS LANDED

The certification track (316-324) had its **rules** and **source survey** built
and its **facts table was a four-row sample, all four ANC subsidiaries**. That
gap was the dataset. `code/329_merge_white_earth_into_certification_facts.py`
closes the first piece of it:

- **`tribal_certification_facts_2026-08-28.csv` — 26 rows**, of which **22 carry
  `evidence_leg = THIRD_PARTY_TRIBAL_GOVT`** (previously zero). A tribal
  government certifying a business is a third party with authority over the
  question — the tier-A leg this track exists to obtain.
- **`tribal_certification_rules_2026-08-28.csv` — 15 rules**, and White Earth's
  is the **only one carrying a quantified bid-price preference schedule**: 10%
  under $100k sliding to 1.5% over $7M, granted ABOVE the lowest responsible bid.
- **Directory columns added** — `owner_name`, `tribal_affiliation_raw`,
  `address_raw`, `city`, `state_province`, `postal_code`, `phone`, `email`,
  `website`, `geocode_status`, `latitude`, `longitude`. Coverage on the 22:
  owner **22/22**, phone **22/22**, address **22/22**, email **20/22**.
  The product is a directory someone can actually use — identify the owner, see
  the affiliation, map it, and contact the firm. The four ANC sample rows carry
  none of this and are left EMPTY, never backfilled.

**The measured finding worth keeping: 0 of the 22 match `prime_contracts` on an
exact name+MN join** (471 distinct MN names indexed, so the join genuinely ran —
an earlier attempt used wrong column names and was correctly reported as
`JOIN_NOT_RUN` rather than as zero). These are small local contractors that are
**invisible to federal contracting data entirely**. That is the argument for the
dataset: it covers firms no federal source sees.

**All 22 are `publishable = N`, `consent_status = UNRESOLVED_OWNER_SUPPLIED_COPY`.**
The roster came from the owner, its provenance is unrecorded, and the Nation has
not authorised publication. Records live at
`data/restricted/white_earth_2026-08-28/` and are **gitignored out of the public
repo**. `geocode_status = PENDING` on all 22 — geocoding is the next step.

---

## THE RULE THIS QUEUE EXISTS TO ENFORCE

**Built is not done. Shipped is done.** This project audits its sources
constantly and its shipment never — measured 2026-08-26, **0.87% of publishable
gaming rows reached a shipping artefact** (104,412 in `data/clean/`, 912 in
`dist/`). Every recurring failure this session had the same shape:

| what happened | where |
|---|---|
| merge step promised in a docstring, never written | `122_ocr_ordinance_scans.py` — 263 docs idle 13 days |
| script written, never run | `46_pull_funding_credit_types.py` (0-byte log) |
| script written, never run, and wrong | `101_build_lodes_block_employment.py` — CNS17/CNS18 swapped |
| built the additions, never read the ledger | `88_build_deals_taxonomy.py` — 790 rows held ONE 2026 row |
| gate declared, never implemented | `LICENSED_SOURCE_FILES` in `87` — 404,236 DUNS shipped |
| codebooks written, never registered | 4 gaming books, 17,555 rows, 19 days |
| entities registered, never promoted | 218 NHOs in the register, 31 in the spine |
| ~~rulings made, never applied back~~ **FIXED 2026-08-26** | 492 clusters / $17.5B re-surfaced as unresolved → 590,752 prime rows now carry a `ruling_status`; see `docs/RULING_APPLICATION_LOG.md` |

`code/160_ship_gap_report.py` exists to make all of this visible in one command.
**Run it before declaring anything done.**

---

## RUNNING

| work | waiting on / note |
|---|---|
| usaspending: script 46, script 44 determination, coverage-profile rebuild, subaward FY2021-24 canary | owns the usaspending host lock |
| FERC docket resume | from `[147/266]` |
| NHO promotion into the spine | 218 registered → 31 in spine; appends IN PLACE (never `01`) |
| Nonprofit / EIN hub linkage | `np_orgs` 0%, Schedule I 1% |
| Docket / proceeding hub linkage | FERC 1%, admin appeals 2-3%, FOIA 5% |
| Ship-gap detector (`160`) | the structural fix for this whole document |
| SAM extract loader + individual-Native class proposal | TRIBAL landed (8,273 rows); 5 tokens pending |
| Facility / casino hub linkage | gaming locks released |
| Individual-Native ownership verification | website corroboration, verbatim sentence + URL |

---

## QUEUED — dependency ordered

**1. ~~Apply prior rulings back to source.~~ DONE 2026-08-26 —
`docs/RULING_APPLICATION_LOG.md`.** 157 files carrying a ruling column were
swept into `data/clean/cedar_ruling_ledger_consolidated.csv` (15,587 rulings,
5,500 subjects with a verdict); `code/174_apply_rulings_to_source_tables.py`
wrote them back onto `prime_contracts.csv` in place. **590,752 prime rows now
carry an explicit `ruling_status` and the file that produced it**, of which
**$13.18B was unattributed and looking untouched while already adjudicated —
20.2% of the $65.2B unattributed pile.** Only 59 rows / $483,462 actually moved
to attributed, because the rulings that could legitimately attribute at tier
A/B had mostly already been applied; **what was missing was the record that a
decision existed at all.** 116 subjects are in genuine conflict and NEITHER
ruling was applied (`review/ruling_conflicts_2026-08-26.csv`). Ledger:
`tier_A_ruled` 1,580 → 1,634, `links_on_village_corporations` 866 → 911.
`federal_funding_transactions.csv` and `subawards.csv` were skipped because
115 and 121 were live on them — a lock on the table, not a gap in the rulings.

**Standing rule earned:** *a ruling that is not applied back to its source
table is not a ruling, it is a note.* `62_no_regression_check.py` now measures
`rulings_unapplied` and reports **UNMEASURED, never 0**, when the consolidated
ledger is absent.

**2. ~~Cross-identifier bridge — UEI ↔ CAGE ↔ EIN ↔ DUNS ↔ tribe_id.~~ BUILT
2026-08-26 — `code/169_build_identifier_graph.py`,
`docs/IDENTIFIER_GRAPH_BUILD_LOG.md`.** 46,051 edges, every one carrying its
evidence, asserting source and INHERITED tier; 115,471 identifier nodes.

**The hypothesis is half wrong, and the wrong half is the useful part.**

- **Propagation resolves 0.6% of the unattributed prime tail.** 57 of 9,277
  UEIs, $0.42B of $65.24B, **and 0 at tier A** — nothing publishable. Not a
  build defect: **58.3% of those UEIs hold exactly one identifier and appear in
  no other file anywhere in the corpus**, and another 39.8% ($51.06B) have a
  CAGE that leads to nothing attributed. Only 162 of the 9,277 appear in
  assistance at all.
- **Real lift is elsewhere:** assistance +207 recipients / **$6.04B** (Dena Nena
  Henash → Tanana Chiefs, $1.78B), FAADS 0% → 862 DUNS / $2.06B, subawards +31.
  Total 1,157 proposed links, **30 tier A / 1,127 tier B**, in
  `data/clean/cedar_identifier_propagation.csv`. **Nothing consumes them yet** —
  the tier-A rows want the `124_apply_rulings_in_place.py` pattern.
- **IRS hypothesis: measured, essentially zero.** **No spending dataset carries
  an EIN column at all** (all four checked; `funding_identifier_harvest`'s
  `recipient_ein` is 0-populated on 37,704 rows). **28 of 12,764 np_orgs EINs —
  0.22% — reach a spending UEI**, all through `np_ein_uei_bridge.csv`, which is
  **28 rows**. Schedule I: 4 of 627 filers, 12 of 18,708 recipients. Reverse:
  28 of 25,419 spending UEIs, 0.11%. `need_v6_geocoded.csv` has **0 rows
  carrying both an EIN and a UEI** and 1,104 carrying an EIN alone — the two
  legs have never been joined. **The only exact route is the SAM
  entity-management extract**, blocked on the same 10/day → 1,000/day role
  request as subawards.
- **874 one-to-many defects, refused, in
  `review/identifier_one_to_many_defects_2026-08-26.csv`** (911 rows with the
  parent-UEI and hub classes). **334 of them are one question** — Alaska
  village GOVERNMENT vs village CORPORATION, $24.52B — and one ruling settles
  the family. 252 sit on already-attributed prime UEIs carrying $38.57B, so
  they are an attribution-QUALITY risk, not a coverage gap.
- **New name trap earned:** `warm springs`. `TRBF-FSCWSA-00` Fort Sill-
  Chiricahua-**Warm Springs**-Apache (OK) vs `TRBF-WRMSPR-00` Warm Springs (OR),
  colliding on $597.4M.

**3. ~~Regression-gate hardening.~~ DONE 2026-08-26.** The gate is **GREEN** and
it is now load-bearing — see the section at the end of `AGENTS.md` before
stepping around a FAIL.

- `codebook_undocumented_public` **45 → 0.** All 47 undocumented
  `07o_nigc_declinations` columns (the script-91 half; the markdown covered only
  the 13 script-100 added) were defined from their own evidence by
  `code/174_document_nigc_declination_codebook.py`, which carries the source of
  every definition beside it. One column, `pdf_path`, was tiered `internal`
  rather than published — a working path on the build machine is not a citation.
  Nothing was invented to clear the counter.
- **Shipping is folded in.** `ship_ratio_pct` 65.202%, `ship_dist_rows`
  5,227,896 of 8,018,053, 49 tables shipping of 257, **205 at 0%**, plus the
  four registry gaps (`27_SPEC` 249, `25_TABLES` 234, notes contract 206,
  codebook block 144) and `rulings_unapplied` 1,215. The baseline stores a
  **per-table** dist row count, so *"this table stopped shipping"* is a hard
  fail distinct from *"the total moved"*.
- **Three traps now have checks**: column loss against the most recent backup
  (a rebuild reverting an enricher), retrieved-vs-reported (a per-unit budget
  that truncated and marked `done`), and coverage columns that do not exist —
  the last applied to the gate's own `keyed_*` counts, which had the bug.
- The retrieved-vs-reported check **failed on its first run** and found a fourth
  rebuild/in-place collision: `ferc_tribal_dockets.csv` had been reverted to its
  183-row pre-rebuild vintage while `ferc_docket_filings.csv` stayed at the
  102,615-row post-rebuild one. Repaired by `code/175_restore_ferc_docket_table_
  after_rebuild_revert.py`; **124 dockets recovered.** Re-run
  `168_link_adjudication_hubs.py` to link them.

**4. Run the shipping chain.** `cedar_codebook.py build` → `62` → `87` → `102` →
`110` → `25` → `27`, per `docs/SHIPPING_RUNBOOK.md`. **Only when no writer is
live** — rebuilding dist from concurrently-changing data is how work was lost
before.

**5. Load the remaining five SAM extracts.** Retry is armed
(`code/retry_sam_downloads.ps1`, sleeps to 00:00 UTC). If the tokens expired,
re-submit. **The 10/day tier is now the binding constraint** — re-submitting and
downloading six variants does not fit in one day. The org role request
(10/day → 1,000/day) unblocks this AND subawards FY2021-24.

**6. Gaming brands → facility universe.** ~137 `blocked_not_leading` /
`blocked_remainder` OSHA rows are real tribal properties whose brands are simply
missing from `gaming_facilities.csv`. Adding them improves the facility universe
*and* auto-attaches on the next run of `157` with no new logic.

**7. Fold the two orphan FERC notices in via `133`, not `154`** — `01-1578`
(2001-01-22, 10 communications) and `2026-16634` (2026-08-14), staged with 13
party rows.

**8. Second reconciliation universe.** Unmatched entities in assistance and
subawards. Keep dollar bases separate — do not mix with the prime queue.

**9. New Mexico and Arizona gaming regulators.** `gaming.az.gov` 403 behind
Cloudflare, `www.nmgcb.org` 403 at root. This is `NOT_CHECKED`, **not**
`NOT_FOUND`. NM quarterly per-tribe revenue sharing and AZ per-tribe
contributions are the highest-value unworked series.

**10. Dewey California extract.** 57.3M rows / 23.8 GB. *Waits on: the 1 TB
drive.* National two-year pull is 298 GB. Advan's usable window is
**2018-03 → 2025, 2026 breaking** — it cannot serve a recent-first mandate.

**11. Three free federal corpora, probed 2026-08-26 —
`docs/UNTAPPED_FREE_SOURCES_2026-08-26.md`.** Reachability, a verified sample
against a named Cedar entity, and a build plan for each. Scripts 219 (CourtListener
/ RECAP), 220 (IRS e-file index), 221 (regulations.gov), 222 (ANCSA statute).
Nothing merged; everything staged in `review/`.

- **`api.regulations.gov` was NEVER TOUCHED and is the highest-value new source.**
  It is the only source for `AdvocacyChannel.ADMINISTRATIVE_COMMENT`, and it
  supplies positions as **retrieved facts** — the thing
  `docs/LOBBYING_EXPANSION_RECONCILIATION.md` says to build instead of an authored
  `position_on_native_issue`. **The existing api.data.gov key works; no new
  credential.** Sweep **docket-first**, not entity-first: a surname collision put
  two form letters into a tribe's bucket on the first pass.
- **CourtListener is unswept, not unused.** `139` typed five dockets by hand.
  219's entity-keyed sample verified 22 entities by `party` array with a zero
  control. Get a free Free Law Project token before sweeping.
- **`docs/SCHEDULE_I_BUILD_LOG.md` line 133 and `docs/EDITORIAL_PIPELINE.md` line
  2699 need a correction.** "It files no return" is **false for 424 of the 6,217
  no-BMF EINs** ($144.4M), measured against the IRS e-file index 2017–2026; and
  only **2.50% of the $4.92B** reaches a spine-linked recipient, with **40.2% of it
  from Johns Hopkins University**. The 9.6%-vs-1.6% Native-density claim is a RATE
  claim and survives. Correct by appending, never by overwriting.
- **`logs/_HOSTLOCK_web.archive.org.json` is stale** — `active: true`, claimed
  2026-08-07, **PID 7420 is dead**. Two items have been queued behind it for
  nineteen days (`104_build_wa_allocations.py`, `119_build_digital_and_loyalty.py`).
  Takeover is permitted by `PULL_DISCIPLINE.md` rule 2. Drain the queue first.

**~~ANCSA §7(h) share transfer~~ — SETTLED 2026-08-26** from 43 U.S.C. §1606(h),
§1607(c) and §1602(r), retrieved from govinfo and quoted verbatim with URLs in
`docs/ANCSA_OWNERSHIP_RULING.md`. Adopted persons: **yes**, if adopted before
majority and recognised at law or in equity. Gift to a non-Native: **no**. Gift to
a spouse: **no** — not in the closed list. **Still open: each corporation's own
articles and bylaws, and whether a given ANC has terminated alienability
restrictions under §1629c.** A shareholder-level measure is unblocked at the
statutory level only.

---

## AWAITING A HUMAN RULING

Do not answer these by inference; they are Elijah's.

| file | rows |
|---|---:|
| `review/gaming_open_date_resourcing_2026-08-26.csv` | 444 |
| `review/gaming_nigc_possible_duplicates_2026-08-26.csv` | 43 |
| `review/nho_parent_unknown_2026-08-05.csv` | 33 |
| `review/entity_candidates_nho_intertribal.csv` | 16 |
| `review/gaming_nigc_closed_row_conflicts_2026-08-26.csv` | 5 |
| `review/deals_status_corrections_2026-08-26.csv` | 1 — Scotts Valley $700M, Interior withdrew the determination; `Status` has no term for it |
| `review/ruling_class_only_owner_unnamed_2026-08-26.csv` `triage = NEEDS_AN_OWNER` | **7 — $2.75B. Ruled `NATIVE` and nothing more. Cheapest large win in the file: one sentence each.** Redstone Defense Systems $1.36B, Manu Kai $760M. The other 27 subjects in that file are triaged `SETTLED_INDIVIDUAL_NATIVE` (12, $2.65B — its own class, never rolls up to a tribe) or `SETTLED_NO_OWNING_ENTITY` (13) and are **not** open questions |
| `review/ruling_tier_unstated_2026-08-26.csv` | 420 — $375M. An owner is named and no source records the tier it was ruled at. A tier is inherited, never assigned, so these were refused rather than guessed |
| `review/ruling_vs_table_contradictions_2026-08-26.csv` | 122 — a ruling that disagrees with what `prime_contracts.csv` already says. Neither side overwritten |
| `review/ruling_conflicts_2026-08-26.csv` | 116 subjects / 1,215 rows — two rulings that genuinely disagree; NEITHER applied |
| Native entity reconciliation artifact | 400 clusters, $35.9B |

---

## NEVER RUN

- `01_build_entity_spine.py` — rebuilds from a stale upstream, silently drops every appended entity
- `09_import_rulings.py` — same; `124_apply_rulings_in_place.py` is the correct tool
- `41_build_codebooks.py` — writes the master in `"w"` mode; would now delete **21 of 43** blocks
- `88_build_deals_taxonomy.py` — full rebuild, drops the attribution columns

---

## THE SIX NAMED DEFECT CLASSES ARE NOW LINTED (2026-08-26, script 293)

**`code/293_lint_bug_classes.py`** detects, by AST and with no network, the six
bug classes that were each found more than once on 2026-08-26 in unrelated
scripts by different agents. **`62_no_regression_check.py` fails on a new
instance** (`lint_new_defect_instances`, must be 0) and tracks all eight
per-class counters as MUST_NOT_RISE. Full audit, every instance by file and
line, plus the 285 scripts checked and found clean:
**`docs/CODE_HEALTH_AUDIT.md`**.

    py -3 code/293_lint_bug_classes.py            # check against the floor
    py -3 code/293_lint_bug_classes.py --class 6  # one class, with the reason
    py -3 code/293_lint_bug_classes.py --selftest # prove the detectors detect

| class | found | fixed | flagged |
|---|---|---:|---:|
| 1 — reads the additions, never the ledger | **0** | — | — |
| 2a — dead `setdefault` shipping a blank column | 2 | **2** | 0 |
| 2b — a coverage % over a column that is absent | **0** | — | — |
| 2c — a drop counter that never names what it dropped | 61 | 1 | **60** |
| 3 — a RULED method read as a positive ruling | **0** | — | — |
| 4 — a budget that truncates and marks COMPLETE | 8 | 0 | **8** |
| 5 — a non-idempotent build rewriting its own log | 6 | 0 | **6** |
| 6 — a full rebuild reverting an in-place enricher | **32 tables** | 0 | **32** |

**Fixed, unambiguous, measured:** `107_pull_remaining_states.py` shipped
`fetched_date` blank on **494 of 494** rows of `state_gaming_observations.csv`
via a dead `setdefault` — the 119 defect in a second place.
`94_rescan_universes.py` the same on `identifier_publishable`.
`88_build_deals_taxonomy.py` now names each withdrawn `Deal_ID` instead of
counting them. **88 was edited, never run.**

**The most reusable output is the class-6 map**: 32 tables with a
rebuild/in-place conflict and **45 tables with more than one writing script**,
scripts named per table, in `docs/lint_bug_classes.json` under `class6_io_map`.
Seventeen of those pairs had never been written down anywhere — including
`entity_evidence_profile`, `federal_funding_transactions`, `fpds_uei_edges`,
`gaming_capacity_official`, `gaming_employment_observations`,
`gaming_properties`, `native_bills` and `subawards`.

**Open, and NOT this session's:**

- **`215_pull_nm_revenue_sharing_quarters.py:67` — a NEW class-4 instance**,
  written 96 seconds before the gate ran. **Owner: the NM/AZ regulator agent
  (queue item 9).** Deliberately excluded from the lint baseline so it cannot be
  baselined away. Named with its owner in `AGENTS.md`.
- **60 class-2c drop counters** and **6 class-5 non-idempotent logs** need their
  authors' knowledge of which identity to print and what their log means. Both
  lists are in the audit.
- **`107_pull_remaining_states.py` needs a re-run** to fill the 494 blank
  `fetched_date` values. It is a network pull, so it belongs to whoever holds
  that host lock.

---

## NEW DATASET — tribally-maintained vendor lists (feasibility, 2026-08-26)

**Owner's idea, and it targets the project's weakest point.** Almost all our
ownership evidence is self-certification. **A tribal government certifying a
business is a THIRD PARTY with authority over the question** — a tier-A leg,
and we have almost none. Measured today: `americanIndianOwned = YES` on 2,846 of
8,273 rows of the *TRIBAL* SAM extract; typing SAM mirrors correctly moved tier
A from 39 to 18.

**Priority order, as specified: lower 48 FIRST, then ANC regional, then Alaska
villages.**

**THE DISTINCTION THAT DECIDES THE VALUE — never conflate:**
| list type | asserts | ownership evidence? |
|---|---|---|
| **TERO / Indian-preference certified** | the business is Indian-owned | **YES — this is the prize** |
| general vendor / supplier / procurement | the firm does business with the tribe | **NO** — many entries are Home Depot |
| tribal business license | the firm operates on tribal land | no, but useful |

A general vendor list still has value as a *relationship* dataset. It is never
an ownership claim.

**Feasibility run: 30 tribes**, stratified large/small, geographically diverse,
including tribes we hold nothing for. Typed verdicts per tribe
(`LIST_FOUND_MACHINE_READABLE` / `_PDF` / `_HTML` / `LIST_BEHIND_LOGIN` /
`LIST_REFERENCED_NOT_PUBLISHED` / `NO_LIST_FOUND` / `NOT_CHECKED` /
`SITE_UNREACHABLE`), Wayback CDX checked for each.

**The payoff must be MEASURED, not assumed**: cross-reference against the 9,385
unattributed identifiers carrying $65.24B and the reconciliation queue's top 400
clusters, then extrapolate to a full 574-tribe sweep with the assumption stated.
**If the answer is "few", that is a valid finding** and cheap to learn now.

**Sovereignty rule, absolute:** these are sovereign governments' own
publications. Respect robots.txt and stated terms. **A directory intended for a
tribe's own members is not ours to take** — `LIST_BEHIND_LOGIN` means stop.

Tracking file `review/tribal_vendor_list_registry_2026-08-26.csv` is re-runnable
so a later sweep resumes rather than restarts. Deliverable
`docs/TRIBAL_VENDOR_LISTS_FEASIBILITY.md` ends in a go/no-go.

*Note: `logs/_HOSTLOCK_web.archive.org.json` is STALE — `active: true`, PID 7420
dead since 2026-08-07, two items queued 19 days. Takeover permitted, record it.*

---

## ADDED 2026-08-26 — refresh cadence, measured (`docs/REFRESH_CADENCE.md`, `code/301_source_freshness_probe.py`)

`301` measures the lag profile of every shipped collection from files already on
disk, zero network requests, and writes `docs/SOURCE_FRESHNESS.json` plus a
snapshot for diffing. **Re-run it after every refresh** — its snapshot diff is
the only mechanism that turns "we think the source corrects retroactively" into
a measured trailing-window number.

**Four collections are stale for reasons that have nothing to do with the
source.** These are the cheapest wins in the repo:

| collection | our last date | source verified at | do |
|---|---|---|---|
| Federal Register / `federal_actions.csv` | 2026-08-05 | **2026-08-26, probed HTTP 200** | re-pull; it is the dating authority for everything else and the recognition-notice trigger for the spine |
| NAGPRA notices | 2026-08-03 | rides the FR pull | re-pull with the above |
| Lobbying (LDA) | 2026-08-04 | `lda.senate.gov` 200, 1,976,414 filings | re-pull **keyed on `dt_posted`**, not on period |
| CT gaming (`gaming_facility_metrics`) | 2025-12-31 | CT publishes monthly | **8 months behind on a monthly open-data endpoint** |

**Open, and worth doing next:**

1. **Cedar holds no genuine cross-vintage archive measurement.**
   `_SOURCE_MANIFEST.csv` is generated from `_state.json`, so differencing them
   yields a convincing all-zeros table that measures nothing (the trap is
   encoded in 301's output). Fix cheaply: re-filter **one** already-held fiscal
   year under the next stamp (`20270106`, published ~2027-01-10) and diff the row
   counts. That single number replaces every within-vintage estimate in Part 1.
2. **Subaward cadence is unmeasurable until the FY2021–24 hole closes.** 301's
   `PLATEAU_WARNING` fires because the mature window lands inside the gap.
   `code/121_pull_subawards_api.py pull --sequential` was live at 23:37Z with a
   collect deadline of 2026-08-27T05:19Z.
3. **CA gaming has holes, not lag** — 2026-03 is missing outright and 2025-03 /
   2025-12 are ~25% of a normal quarter. Backfill in the same pass as the next
   quarterly pull.
4. **`fl_gaming.period_end` runs to 2031-06-30** — forward-dated compact schedule
   rows. Any "last data" claim built on that column is wrong by five years. It
   needs a separate observation-date column before it can carry a `vintage`.
5. **`federal_funding_transactions.csv` carries two archive stamps at once**
   (`20260706` 131,495 rows, `20260806` 93,536). No single `vintage` string
   describes it. Re-pull the span under one stamp before shipping, or publish the
   **oldest** contributing stamp and say so.

---

## ADDED 2026-08-26 — unfinished work, ranked (`docs/UNFINISHED_WORK_AUDIT.md`, script 407)

The other half of the ship-gap question: not *"what was built and never
plumbed"* but **"what was started and never finished."** All 53 scripts the
detector filed `OUTPUT_MISSING` / `NEVER_RUN` are dispositioned by name in the
audit.

**45 of 53 were the detector's own fragments, not the project's gaps** — an 85%
false-positive rate on the strongest verdict the report issues, including its
sole `NEVER_RUN` (`90_build_review_page.py`, whose one declared path was a
browser `a.download` attribute). **Fixed at source in
`code/160_ship_gap_report.py`: `scripts_output_missing` 52 → 10,
`scripts_never_run` 1 → 0.** A detector that cries wolf gets skimmed, and the
real findings ride out on the noise — which is how the 0.87% ship rate survived
twenty days.

**Four false positives were files whose ABSENCE IS THE SUCCESS CONDITION** — the
script deletes them (`14`, `36_cull`) or writes them only when a check FAILS
(`85`'s `admin_region_missing_bia.csv`, `143`'s no-network refusal branch). A
passing check was being reported as a missing output.

**Nothing in the still-wanted set was run.** Not one is blocked on doubt about
whether it should be; every one is blocked on a live host lock, a spent API
budget, or an input a human must write.

| # | script | what it is | blocked on | effort |
|---|---|---|---|---|
| **U1** | `40_contracts_ledger_pass.py` | **NEVER RUN.** Measures the hole the flag route cannot see: four socio-economic flags (`indian_tribe_federally_recognized`, `us_tribal_government`, `housing_authorities_public_tribal`, `tribal_college`) **return ZERO as USAspending filters**, so a tribal government contracting in its own name is invisible to Pass A. Queries by the ledger's own tier-A UEIs instead. Bears on the $65.24B unattributed prime tail | `api.usaspending.gov` lock — `121` live to 2026-08-27T05:19Z | one unattended run, resumable. **Never raise `BATCH` above 20** (21+ → HTTP 503, not a clean 400) |
| **U2** | `67_sam_entity_harvest.py` | **NEVER RUN.** `extract()` refuses until `--discover` writes `sam_business_type_codes.csv`; it never has, so the whole leg is stopped by one uncalled function. Item 2 measured the IRS route to 0.22% and concluded **"the only exact route is the SAM entity-management extract"** — this is it | SAM 10/day; 8 spent today and **tomorrow's first six are reserved for `141 download`** (tokens paid for; a submission is not retryable). Genuinely unblocked by the **role request** | 1 call `--discover`, then 1 per Native code |
| **U3** | `211_cdx_enumerate_blocked_gaming_hosts.py` | **RUN BUT FAILED SILENTLY — it was KILLED.** `logs/211_cdx_bypass.log` is 166 bytes and stops at page 3 of `gaming.az.gov`. The `_cdx_state.json` write is inside `finally:`, which did not execute — **a kill, not an exception**. No checkpoint, no `cdx_<host>.json`, and a resume restarts from zero. Only route into `gaming.az.gov` / `www.nmgcb.org` (both 403), i.e. queue item 9's "highest-value unworked series" | `web.archive.org` lock — `317` live, claimed 23:53Z, **49 hosts queued**. *(The stale-lock note under item 11 is out of date: taken over legitimately by 213 then 317)* | ~2h unattended |
| **U4** | `83_build_resource_ledger.py` — Navajo leg | **The parser is shipped and the data was never harvested.** `build_navajo()` no-ops without `cedar_navajo_audited_actuals.csv`. `docs/RESOURCE_LEDGER_STATES_LOG.md` item 3 says so. Navajo is the largest single resource-revenue entity in the corpus | a `dibb.nnols.org` harvest under a fresh host lock | harvest only, no code |
| **U5** | `289_update_collection.py` | **NEVER RUN for real** — only `289_dryrun_2026-08-26.log`, and no `_MANIFEST.json` under `dist/`. **This is queue item 4**, listed for completeness | *"only when no writer is live"* — five are | the full chain |
| **U6** | `107b_fill_source_urls.py` | **NEVER RUN — the `122` shape.** `docs/STATE_GAMING_PULL_LOG.md` promises *"drop a `_retriever_urls.csv` … and run it"*; **it was never dropped**, so the script `sys.exit`s. Closes a REPRODUCIBILITY gap: part of the state_gaming raw tree's URLs live only in agent transcripts | a human, or a transcript archive | manual transcription, recoverability unknown. **`UNKNOWN` is a legitimate value and a guess is not** |
| **U7** | `101_build_lodes_block_employment.py` — geocode leg only | **Employment leg SUPERSEDED by `100`; the CNS17/18 trap is FIXED (see below).** `facility_block_geocode.csv` is NOT superseded — `100` does not produce it and `102` lists it as a hub source | Census Geocoder / LEHD locks | geocode pass only. **Do not re-derive the employment leg** |

### Specified, not started — hand-offs rather than half-builds

- **`_retriever_urls.csv` for U6.** Columns `relative_path, source_url,
  fetched_date, note`, one row per file in `data/raw/external/state_gaming/`.
  If the transcripts are gone, a file of `UNKNOWN`s plus a count is the honest
  output — it makes the irreproducibility visible instead of latent.
- **Persist the DOI EIN probe and repoint `36_build_nho_intertribal.py`.** It
  reads `doi_ein_results_v2.json` from **another Claude session's temp
  directory** (`…\ea2ef30b-…\scratchpad`), which no longer exists. That file
  recovered **8 EINs (47 → 55)** via a diacritic-aware normaliser, and the read
  is guarded by `.exists()` — so **a re-run today silently yields the 47-EIN
  version and says nothing.** Re-run the probe, write to
  `data/raw/external/nho/doi_ein_results.json`, repoint `SCRATCH`.

### `101`'s trap is defused — it will not catch the next reader

`CNS17`/`CNS18` were labelled **backwards**, and backwards in exactly the
direction that mattered: a casino is NAICS 713210, sector 71, i.e. **`CNS17`**,
so the file would have shipped casino employment under `jobs_accommodation_food`,
the hotel name. LODES WAC segments are the twenty NAICS supersectors in order,
and the dict's own `CNS07`/`CNS12`/`CNS20` entries already agreed with that
ordering, which is what pins it. Corrected in place with the reasoning beside it;
**the script was not run**, and nothing was contaminated because it has no log
and neither output has ever existed.

### Standing rule earned

**A checkpoint written only in `finally:` is not a checkpoint.** `finally:` does
not survive a kill, and a kill is the failure mode a checkpoint exists for — U3
lost a 60,000-capture sweep three pages in and left no trace but a 166-byte log.
Write the state file after each page.

### Second rule earned, about the detector

**A superset must still be made of names.** `160`'s `declared_outputs()` is
deliberately a superset — inputs land in it too — and that is sound. What was
not sound is that it was a superset of *fragments*: half-names cut at a space, an
escape, a `+`, or a second extension. Every speculative repair added today is
**existence-gated with the bare token as fallback**, so it can only turn a
reported gap into a satisfied declaration and never the reverse — **a mistake in
the fix cannot hide a real gap.** An earlier ungated version was measured at
52 → 77 and reverted before it shipped.

---

<!-- BEGIN MASTER-LIST-SWEEP-2026-09-02 -->
# THE REGISTER IS A SEARCH KEY — which sources to sweep next, measured

*Added 2026-09-02 by workstream `nest-owner-v6`
(`code/1130_nest_owner_v6_reconcile.py`). Every number below was measured on
this machine with no network call. Owner:*

> *"Our native entity master list is pretty comprehensive... it can be as
> simple as keyword searching all of them, or building scrapers. That is a
> source we're not using as much as I think we could."*

**The principle, stated so it can be applied to a source nobody has looked at
yet:** where a source carries a **Native flag**, use the flag. Where it does
not, **sweep all 1,555 register names against it** — the register is the
discovery leg. And where it *does* carry a flag, ask what the flag misses,
because a flag is a self-declaration under one definition and the register is
a different definition.

**The method already has a proof.** `1130`'s R3 rung swept the register
against the SBA DSBS extract already on disk and found **106 register
entities registered as firms under their own legal name** — including 13
NHOs, which is the only reason the ANC/NHO dual role could be evidenced at
all (ADR-032). Zero network requests, one pass, one new fact class.
Uniqueness was required on both sides and 73 candidates were refused for it.

## Ranked, with the yield measured rather than guessed

Exact normalised name, unique in the register and unique in the source. This
is the FLOOR — a real sweep would add alias and identifier legs.

| source | rows | register entities it names exactly | verdict |
|---|---:|---:|---|
| **`fpds_uei_cage_map.csv`** | 34,601 | **666 of 1,555 (42.8%)** | **sweep first.** On disk, no network, and it hands back a UEI/CAGE binding per hit — the identifier rung every other matcher wants |
| **Federal Audit Clearinghouse** | 6,780 held | **638 reached today** | **the owner's own pick, and the gap is structural — see below** |
| **NPPES organisational registrations** | 16,981 | **147** | on disk (`code/1121`, 2026-09-02), carries **no `cedar_uid` column at all**, and `nppes_spine_name_candidates.csv` (18,221 rows) is a candidate list nobody has resolved |
| SBA DSBS extract | 5,087 | 106 (already done by `1130` R3) | done; extend to aliases |
| IBIA / IBLA case names | 15,613 | 32 | thin on exact name because a case caption is *"X v. Acting Regional Director"*; needs a caption parser, not a sweep |
| USAC RHC provider directory | 11,142 | 2 | **do not sweep.** Provider names are clinics, not nations |
| NAGPRA institutions | 6,792 | 1 | **do not sweep.** The institution side is museums; the tribal side is already keyed |

The last two rows are the point of measuring rather than proposing: two
sources that look obviously sweepable return one and two hits, and an hour
spent on either buys nothing.

## FAC is the right pick, and the reason is sharper than "it is under-used"

`code/147` pulls `entity_type = eq.tribal` from the FAC dissemination API.
**6,774 of the 6,780 rows Cedar holds came in through that flag** (the other
six are `local`). It reaches **638 of 1,555** register entities.

**Look at what the flag misses.** Of the 917 entities FAC has never reached:

```
Native Hawaiian Organization                  210   <- every single one
Alaska Native Village Corporation             152
Federally recognized Alaska Native Village    115
BIE School                                    114
State-recognized tribe                         63
Native Community Development Financial Inst.   55
Individually Native-owned business             45
Intertribal Organization                       37
```

**An NHO does not file a Single Audit as a tribe.** Neither does a tribal
college, a Native CDFI, a BIE school or an intertribal health board — they
file as `non-profit`, and `entity_type = tribal` cannot see one of them.
Every organisation on that list that expends $750k of federal awards in a
year **must** file, and Cedar is not looking for their filings. This is not a
coverage shortfall in FAC; it is Cedar asking FAC the wrong question.

**The sweep:** query the FAC `general` table by `auditee_name` (and by
`auditee_ein` where the ledger holds one) for the 917 unreached register
entities, with **no `entity_type` filter at all**, and resolve each hit
through `147`'s existing single resolver. Then record what came back, and
just as importantly record `CHECKED_ABSENT` for the entities that genuinely
have no filing — `docs/SHARD_COVERAGE.md` distinguishes *attempted, none
found* from *untouched* for exactly this reason, and today all 917 are
untouched.

**Two traps to carry into it, both already paid for elsewhere in this
project.** The `is_public` opt-out is **not a bar** — `START_HERE`'s FAC
correction and the 2,052 public rows of 6,780 say so; and a hit on
`auditee_name` alone is a name match, so `ENTITY_MATCH_RULES` rule 7's
residue test decides it, not containment. `NAVAJO TRIBAL UTILITY AUTHORITY`
is not the Navajo Nation.

## And the standing measurement that says how much of this is left

`py -3 code/1112_harvest_coverage_matrix.py verify` — per entity, per thing,
what was actually looked for. `NEVER_CHECKED` today:

```
identifiers          1,439 of 1,555   (92.5%)
gaming               1,257            (80.8%)
enterprises            455            (29.3%)
individual_business    450            (28.9%)
newsletter             373            (24.0%)
```

The register-as-search-key is the cheapest instrument that moves the first
two, and `identifiers` is where it pays fastest, because
`fpds_uei_cage_map.csv` is sitting on disk naming 666 of them already.
<!-- END MASTER-LIST-SWEEP-2026-09-02 -->
