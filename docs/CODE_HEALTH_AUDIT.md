# Code health audit — the seven named defect classes

> **UPDATE 2026-08-28 — CURRENT COUNTS. Everything below this block is older.**
>
> Measured by `293` on 2026-08-28, and this is what `62` now floors:
>
> class1 **0** · class2a **0** · class2b **0** · class2c **60** · class3 **0** ·
> class4 **9** · class5 **6** · class6 **30** · class7 **42** ·
> **TOTAL (unwaived) 147**, waived **19**.
>
> Against the 2026-08-26 baseline of 182: **−35**. class7 74 → 42, class6 33 → 30.
>
> **Type-A collisions — one table with two or more WHOLESALE writers and no
> declared ordering — went 5 → 1** on 2026-08-28. Resolved: the lobbying v1
> chain and `06_verify_nho_via_8a.py` were archived (see `graveyard/`), and
> `40 → 131` was declared for `prime_contracts_entity_year.csv`. The one
> remaining is structural, not undeclared.
>
> **Ordering coverage went 5 → 80.** `cedar_pipeline.KNOWN_ORDERINGS` held five
> curated pairs while 293 found 32 class6 tables; `derived_orderings()` now
> derives the rest from 293's own `class6_io_map`, so a build runner can ask
> `enrichers_to_rerun(table)` and get a complete answer.
> **`cedar_entity_spine.csv` had 1 declared enricher and has 15.**
>
> New in `62`, both ratcheted: `code_duplicate_numbers` (floor 43 — a new
> script may not reuse a taken number) and `tables_undocumented_in_codebook`
> (floor 14 — and see the note under class 6 about why the older
> `tables_missing_from_25_TABLES` is **not** the shipping gate).

> **UPDATE 2026-08-26, ~20:00 — read this before the counts below.**
>
> **A SEVENTH CLASS was added and `code/248_audit_tier_inheritance_patterns.py`
> was RETIRED into `293`.** 248 was a second detector for class 3, written the
> same evening by a different agent; its per-site disposition table and its
> ledger-exposure measurement are now inside 293 and the file is a stub that
> exits 2. **Two detectors drift, and a drifted detector is worse than none,
> because it is trusted.**
>
> **CLASS 7 — a POSITIONAL or otherwise NON-DETERMINISTIC PRIMARY KEY.** An id
> minted from outside the row, so the same fact gets a different id next build.
> `293` **consumes** `code/284_audit_nondeterministic_keys.lint_key_stability()`
> rather than re-deriving it, and `--selftest` now runs 284's three measured
> fixtures (`ferc_filing_id` 4 of 2,534 ids stable; `verification_id`
> rank-derived, a concurrent rewrite gave one firm another's ownership
> sentence; `observation_id` positional, 482 of 492 ids changed on a re-run
> and a merge would have appended 492 silent duplicates).
>
> **NEW BASELINE, recorded 2026-08-26:**
> class1 **0** · class2a **0** · class2b **0** · class2c **60** · class3 **0** ·
> class4 **9** · class5 **6** · class6 **33** · class7 **74** ·
> **TOTAL (unwaived) 182**, waived **3**.
> The +77 against the old floor of 105 is class 7 arriving, plus three findings
> named with their owners in `AGENTS.md` under "THE THREE FINDINGS THAT
> RE-BASELINING ABSORBED". `62_no_regression_check.py` now tracks
> `lint_class7` as MUST_NOT_RISE alongside the other eight counters — and note
> that before this, `62`'s baseline predated 293, so **every `lint_*` metric
> was printed and silently skipped**. They are floors now.
>
> The class-1..6 narrative below is unchanged and still correct; only the
> counts moved.

*2026-08-26, evening. Written by the agent that claimed script number 293.
Every count below was produced by `code/293_lint_bug_classes.py` against the
files on disk, not read out of a build log. Re-run it and you get these numbers
back, or you get a named difference.*

    py -3 code/293_lint_bug_classes.py            # check against the floor
    py -3 code/293_lint_bug_classes.py --class 6  # one class, with the reason
    py -3 code/293_lint_bug_classes.py --selftest # the detectors still work
    py -3 code/293_lint_bug_classes.py --baseline # record a new floor

---

## WHY THIS EXISTS

Six distinct bug classes were each found **more than once on 2026-08-26**, in
unrelated scripts, by different agents. Every one of them was invisible until
somebody tripped over it, and every one was fixed **only where it was tripped
over** — script 88's additions glob was named in `docs/FACT_CHECK_2026-08-06.md`
finding B-1 three weeks before it was fixed, and it was still live in nine other
scripts on the day it finally got swept.

The diagnosis was never the hard part. **The hard part is that a defect fixed in
one place leaves no trace in the other nine.** So the deliverable that matters
here is not the fix list; it is `code/293_lint_bug_classes.py`, which detects
the SHAPE of all six by AST, and its fold-in to `62_no_regression_check.py`,
which makes a NEW instance a stop-work gate failure instead of an accident three
weeks later.

---

## THE HEADLINE

| | |
|---|---:|
| Python files in `code/` parsed | **353** |
| …that failed to parse (NOT checked, and that is not the same as clean) | **0** |
| files carrying at least one finding | **68** |
| **files checked and CLEAN of all six classes** | **285** |
| findings, unwaived | **106** |
| findings waived, with a written reason | **1** |

*The file count moves while you read it. Ten-plus agents are live on this repo
tonight and `code/` grew by three files during this audit. Re-run the linter for
today's denominator; the per-class counts are what the gate compares.*

| class | what it is | found | fixed | flagged |
|---|---|---:|---:|---:|
| **1** | reads the ADDITIONS, never the promoted LEDGER | **0** | — | — |
| **2a** | `setdefault()` on a key that already exists — a no-op | **2** | **2** | 0 |
| **2b** | a coverage % over a column the file does not have | **0** | — | — |
| **2c** | a drop counter that never names what it dropped | **61** | **1** | 60 |
| **3** | a RULED method read as a POSITIVE ruling | **0** | — | — |
| **4** | a per-unit budget that truncates and marks COMPLETE | **8** | 0 | **8** |
| **5** | a non-idempotent build that rewrites its own log | **6** | 0 | **6** |
| **6** | a full rebuild reverting an in-place enricher | **32 tables** | 0 | **32** |

**Baseline recorded: 105, against 106 live findings.** The gap is deliberate.
The class-4 finding in `215_pull_nm_revenue_sharing_quarters.py` landed at
**19:14:54 while the baseline was being recorded**, and baselining it would have
made a named, owned, live failure disappear on the day it was found. It is
**excluded from the floor and named with its owner in `AGENTS.md`**, so the gate
stays red until its author fixes it. `--baseline` records a floor; it is not an
acknowledgement button.

`62_no_regression_check.py` now carries `lint_new_defect_instances`, which
**must be 0**, plus every per-class counter as MUST_NOT_RISE.

The rule applied throughout: **fix only what is unambiguous.** Where a fix is a
judgement call — a matcher's behaviour, a threshold, a definition, another
agent's live file — it is FLAGGED with its evidence and left alone. A wrong fix
that looks right is worse than a flagged bug, because it will never be
questioned again.

---

## CLASS 1 — reading the additions and never the ledger

**Instances remaining: 0. The sweep is clean, and it is clean against the
project's own declaration rather than against my opinion.**

A concurrent agent landed `cedar_domain.PROMOTED_TABLES` and
`PROMOTED_TABLE_PRODUCERS` — the single declaration of which file is the truth
and which scripts are allowed to read the parts. **The detector imports that
registry rather than keeping a second copy** (standing rule 8 applied to a
detector; a drifting detector reports clean). It then flags any script that

- names a PART (`deals_*_additions.csv`, `deals_2026_ytd.csv`,
  `deals_historical_2020_2025.csv`), **and**
- never names the PROMOTED table (`deals_classified.csv`), **and**
- is not in `PROMOTED_TABLE_PRODUCERS`.

Every one of the ten scripts that carried this defect now reads the ledger too:
`88`, `57`, `41`, `82`, `35`, `33`, `59`, `73`, `31`, `175`. Verified by
re-running the detector against the registry, not by reading their docstrings.

**The one thing to keep doing:** the day a new promoted table is created, add it
to `PROMOTED_TABLES`. The detector is only as wide as that dict. Right now the
dict holds exactly one family — deals — and the same shape certainly exists
elsewhere (`data/staging/*`, `review/*_additions_*.csv`) with no promoted table
declared for it yet. **That is a coverage limit of the check, stated rather than
hidden.**

**One waiver, counted and named:**

| file | reason |
|---|---|
| `164_link_facility_hub_sources.py:532` | the two `*_staged.csv` files are read only to COUNT and NAME them as unpromoted. No promoted table exists for them yet; printing them is the point. |

---

## CLASS 2 — our own defect published as a fact about the source

### 2a — `setdefault` on a pre-initialised dict. **2 found, 2 FIXED.**

The 119 defect exactly: `row = {k: "" for k in FIELDS}` creates every key
holding `""`, and `setdefault` only writes when a key is **absent**. So it is a
no-op and the column ships blank — and a downstream reader reports the blank as
a fact about the source.

**1. `code/107_pull_remaining_states.py:993` — MEASURED COST: 494 of 494 rows.**

```python
r = {f: "" for f in FIELDS}          # FIELDS holds "fetched_date"
...
r.setdefault("fetched_date", TODAY)  # NO-OP
```

`data/clean/state_gaming_observations.csv` carries **`fetched_date` blank on
494 of 494 rows** — measured today, before the fix. That table is in the
"ships today" list of `docs/GAMING_SOURCE_AUDIT_2026-08-26.md`, so the blank
was on its way to a subscriber as *"the source states no retrieval date"*.

**2. `code/94_rescan_universes.py:189` — `identifier_publishable`.**

Same shape. Every proposal written to `rescan_<date>_proposals.csv` shipped a
**blank** publishability flag where the intent was the default `1`. A blank
reads as *not publishable* or as *the source does not say*; neither is what the
author meant.

Both fixed to `row["k"] = row.get("k") or DEFAULT`, which is the behaviour
`setdefault` was reaching for, with the measurement written beside the change.
Backups: `code/107_pull_remaining_states.py.bak_2026-08-26_pre_293_lint_bug_classes`,
`code/94_rescan_universes.py.bak_2026-08-26_pre_293_lint_bug_classes`.

**Neither script was run.** The fix changes what a future run writes; it does
not retroactively fill the 494 rows. **Re-running `107` is the remaining job and
it is a network pull, so it belongs to whoever owns that host lock.**

### 2b — a coverage % over a column that does not exist. **0 found.**

The `102` defect (two datasets counted on `tribe_id` when both key
`tribe_entity_id`, printing 0.0% for nineteen days) is fixed at source, and
`62_no_regression_check.py` already carries
`coverage_columns_that_do_not_exist` = 0, imported from `102`'s own
declarations. The linter adds a second, independent check: any file whose name
says it reports (`coverage|profile|audit|report|gap|ship|summary|benchmark`)
that computes a share **and never once tests that a named column exists**. None
remain.

### 2c — a drop counter that never names what it dropped. **61 found, 1 fixed, 60 flagged.**

This is the `87` defect — `stats["skipped: not a documented dataset"] += 1`
with no filename, which hid 33,817 unshipped rows for twenty days. **A count is
not actionable and does not accuse anyone of anything, so it scrolls past. A
filename is a task.**

The detector flags an increment whose label matches
`skip|drop|refus|reject|unmatch|miss|fail|blocked|excluded|…` where **nothing in
the same block names the row, file or key**, *and* the tally is later
**printed** — an internal tally nobody reports is bookkeeping; a reported number
whose subject is never named is the defect.

**FIXED — `88_build_deals_taxonomy.py:211`.** It counted withdrawn duplicate
deal rows and printed only the number. It now prints each `Deal_ID` and the
file it came from. Chosen as the fix because it is the deals ledger — the same
table this whole defect family was found on — and because the identity is
already in hand at the point of the drop. Backup:
`code/88_build_deals_taxonomy.py.bak_2026-08-26_pre_293_lint_bug_classes`.
**88 is on the NEVER RUN list; it was edited, never executed.**

**FLAGGED — the other 60, by file and line.** They are not fixed because each
one needs the author's knowledge of *which identity is the useful one* (a
filename? a Deal_ID? a facility? the raw text?), and because sixty edits across
forty scripts owned by live agents is a collision hazard that outweighs the
benefit tonight. The complete list is in `docs/lint_bug_classes.json`; the
counts, by file:

| file | counters |
|---|---:|
| `99_build_earmarks_and_schedc.py` | 5 |
| `94_rescan_universes.py` | 5 |
| `77_build_nagpra_dataset.py` | 6 |
| `70_key_unjoined_datasets.py` | 3 |
| `130_build_section_106_consultation.py` | 3 |
| `144_build_admin_appeals.py` | 3 |
| `98_build_oira_and_hearings.py`, `13_build_fpds_hierarchy.py`, `18_spiderweb_v2_and_cage_backfill.py`, `106_build_revenue_bounds.py`, `148_build_gaming_vendor_tribal_licenses.py`, `168_link_adjudication_hubs.py` | 2 each |
| 26 further files | 1 each |

**The ones worth doing first**, on the judgement that the drop is a
publishable-row loss rather than housekeeping:
`115_pull_assistance_archive.py:729` (`ledger_tier_X_excluded` — which entities
were excluded by an X ruling is exactly what a reader needs),
`33_apply_party_rulings.py:393` (`excluded_rows` — the one resolver; the parties
ruled NOT Native are printed as a count and never named),
`70_key_unjoined_datasets.py` ×3 (`stat["refused"]` — entity keying refusals,
the thing the product sells), and `77_build_nagpra_dataset.py:1713`
(`containment_rejected` — the containment defect's own counter, unnamed).

---

## CLASS 3 — a RULED method treated as a POSITIVE ruling

**Instances remaining: 0.**

`148_resolve_schedule_i_recipients.py` was repaired by its owning agent while
this audit ran; the repair is documented in that file at lines 47–200 and the
detector confirms it. The general rule it earned is now enforced, not just
written down:

> **A RULED method says a HUMAN DECIDED. It never says the answer was YES.**
> All 317 `elijah_ruling` EIN rows in the ledger are tier **X** — negative
> rulings. `tier = "A" if meth in RULED` promoted every one of them to a
> confident attribution (`COLVILLE ROTARY → Confederated Colville`, tier A).

> **`status` says the ruling was PROCESSED; `outcome` says what it DECIDED.**
> One ruling read `status = SETTLED` while its outcome was
> *"HOLD — RETRACTION REQUIRED"*.

Two detectors, both live:

- membership of a `RULED`-shaped set deciding a tier-A assignment **in a file
  that shows no awareness of a negative ruling** (no `"X"`, no `NEGATIVE`, no
  `RETRACT`, no `HOLD_OVER`);
- a `status`-named value compared to a PROCESSED literal (`SETTLED`, `RULED`,
  `APPLIED`, `DONE`, `COMPLETE`, `RESOLVED`, `CLOSED`, `FINAL`) **in a file
  where the word `outcome` never appears**.

Both are proven against the original defect by `--selftest`.

**Worth knowing about the second detector's blind spot:** it fires on the
*absence of the word `outcome` in the file*. A script that reads `outcome`
somewhere else for an unrelated purpose will suppress it. That is a deliberate
trade for a zero false-positive rate on 352 files, and it is stated here rather
than discovered later.

---

## CLASS 4 — a per-unit budget that truncates and then marks COMPLETE

**8 found, 0 fixed, 8 FLAGGED.** Every one is a judgement call about a
threshold, which is exactly what the brief says to flag rather than change.

The named defect: `PER_DOCKET_BUDGET_S = 240` wrote four FERC dockets at
2,300–3,200 of 3,555–4,847 documents and then marked them `done`, so no resume
would ever revisit them. **The only thing that exposed it was comparing
`documents_retrieved` against `total_hits_reported_by_source`.**

The detector fires when a module (a) defines a budget/deadline/max-count
constant, (b) exits a loop on it, (c) writes a completion marker
(`done`/`complete`/`finished`/`ok`/`retrieved`), and (d) **never once references
a source-reported total** (`total_hits`, `numFound`, `totalCount`,
`record_count`, `expected_total`, …).

| file | budget | why it is flagged, not fixed |
|---|---|---|
| `121_pull_subawards_api.py:908` | `COLLECT_DEADLINE`, `SUBMIT_DEADLINE` | writes `finished`/`FINISHED`/`RETRIEVED` job states. **The highest-stakes one**: subawards FY2021–24 is an open hole and a job marked `finished` short of its rows would be indistinguishable from the upstream outage. Owner: whoever holds the usaspending host lock. |
| `134_build_nepa_eplanning.py:166` | `DEADLINE_S` | prints `retrieved`; eplanning states a result count that is not read back. |
| `200_probe_fac_historical_depth.py:95` | `MAX_REQUESTS`, `DEADLINE_S` | a **probe**, and a probe that stops early is doing its job — but it writes `completed`, and a probe's conclusion is what gets quoted. |
| `211_cdx_enumerate_blocked_gaming_hosts.py:98` | `RUN_DEADLINE` | CDX serves a total; not compared. An enumeration cut short reads as "the host has nothing more". |
| `213_cdx_targeted_nm_az_documents.py:116` | `RUN_DEADLINE` | same. |
| `214_recover_nm_tribal_revenue_sharing_2023_2025.py:99` | `RUN_DEADLINE` | same. |
| `215_pull_nm_revenue_sharing_quarters.py:67` | `RUN_DEADLINE` | **written at 19:14 today, while this audit ran — LIVE WORK. Named, not touched.** See the named-failure section below. |
| `dl_regional.py:18` | `BUDGET` | small unnumbered helper. |

**The fix shape, for whoever owns each:** record the source's own reported total
next to what you retrieved, and refuse to write `done` when they differ. That is
one field and one comparison, and it is what turned an invisible four-docket
ceiling into a gate metric (`units_short_of_source_reported_total`, currently 0).

**Six of the eight are CDX/probe scripts where stopping early is the design.**
For those the defect is not the stop — it is that the artefact does not say
*"this run stopped on the clock, at N of the M the source reported"*. The
difference between an interruption and a completion is the whole rule.

---

## CLASS 5 — a non-idempotent build

**6 found, 0 fixed, 6 FLAGGED.**

`164_link_facility_hub_sources.py` — the script the class is named after — is
**already repaired**, by its own author, and the repair is documented in the
file at lines 398–402. Re-running it no longer rewrites 187 facilities to read
"0 sources".

The remaining six share one shape: an *already-done* short-circuit skips the
work, and the run still rewrites a log/summary artefact **wholesale**. On a
second run every unit is already done, every counter is zero, and the log says
so — truthfully about that run, and misleadingly about the world.

| file | the short-circuit | the artefact it rewrites |
|---|---|---|
| `159_extend_gaming_metrics.py:217` | `if k in existing or k in seen_keys` | `logs/159_extend_gaming_metrics_<date>.json` (line 275) — a re-run records `ct_rows_added: 0`, which reads as *the CT source has no rows* |
| `98_build_oira_and_hearings.py:837` | `if t in done` | line 2103 |
| `142_build_property_site_observations.py:783` | `if (host, "detect") in done` | line 1518 |
| `112_pull_grantee_990s.py:403` | `if y in done` | line 528 |
| `121_pull_subawards_api.py:848` | `if s == "finished"` | line 732 |
| `105_build_florida_gaming.py:858` | a header-shape test on `"Receipts"` | line 2152 |

**Partial mitigation already present:** several of these date-stamp the log
filename, so a re-run on a *different* day writes a new file and the original
survives. A same-day re-run still overwrites. That is why this is flagged rather
than declared harmless.

**Not fixed because the right fix is a judgement call**: does the log mean *what
this run did* (in which case zero is honest, and the file should say
"incremental run, N already present") or *what the table now holds* (in which
case it must be recomputed from the table, not from the run's counters)? Only
each author knows which. `164` chose the second and says so; the other six have
not chosen.

---

## CLASS 6 — a full rebuild silently reverting an in-place enricher

**32 tables flagged. This is the map the brief asked for, and it is the part of
this audit with the longest half-life.**

The detector builds the read/write map of every `data/clean` and `data/spine`
table across all 352 files and reports two provable hazards:

1. a table with a **rebuild-only writer** (writes it, never reads it) *and* an
   **in-place enricher** (reads it, then writes it) — the rebuild reverts the
   enricher;
2. a table written **wholesale by two or more different scripts, none of which
   reads it first** — whichever runs last discards the other's work.

Shape (2) is why `ferc_docket_filings.csv` and `ferc_tribal_dockets.csv` are
caught: the canonical `133`-vs-`168` collision, where the rebuild printed a
**larger** row count that read as pure progress while 931 entity links and nine
columns went.

### The full conflict list — 32 tables

`admin_appeal_decisions` · `admin_appeal_parties` · `ca_gaming_facilities_official` ·
`cedar_entity_spine` · `cedar_identifier_ledger` · `cedar_identifier_ledger_final` ·
`cedar_identifier_ledger_tiered` · `codebook_master` · `deals_party_autoresolved` ·
`digital_gaming_revenue` · `entity_evidence_profile` · `federal_funding_transactions` ·
`ferc_docket_filings` · `ferc_ex_parte_parties` · `ferc_tribal_dockets` ·
`fpds_uei_edges` · `gaming_capacity_official` · `gaming_employment_observations` ·
`gaming_financing_events` · `gaming_properties` · `gaming_property_universe_events` ·
`gaming_source_claims` · `lobbying_unmatched_clients` · `native_bills` ·
`native_entity_lobbying_disclosures` · `native_issue_litigation_positions` ·
`nho_ito_spine_crosswalk` · `nho_verified_entities` · `nigc_declination_letters` ·
`prime_contracts_entity_year` · `subawards` · `tribe_year_lobbying_panel`

`docs/lint_bug_classes.json` carries the writers per table under
`class6_io_map`. The pairs already known to the project are all present and
correct — `01` vs the thirteen spine appenders, `09` vs `50`/`56`/`63`/`71`,
`41` vs the twelve codebook-fragment writers, `133` vs `168`. **The following
were not written down anywhere before tonight:**

| table | rebuild-only writer(s) | in-place enricher(s) |
|---|---|---|
| `entity_evidence_profile.csv` | `151_rebuild_entity_evidence_profile.py` | `110_build_harmonized_views.py` |
| `federal_funding_transactions.csv` | `24_funding_merge.py` | `115_pull_assistance_archive.py` |
| `fpds_uei_edges.csv` | `13_build_fpds_hierarchy.py` | `26_fix_sanity_failures.py` |
| `gaming_capacity_official.csv` | `92_build_gaming_capacity_official.py` | `106_build_revenue_bounds.py` |
| `gaming_employment_observations.csv` | `100_finish_declinations_and_employment.py` | `158_merge_staged_labor_employment.py`, `262_repair_form5500_tribe_attribution.py`, `265_merge_osha_relift_rows.py` |
| `gaming_financing_events.csv`, `gaming_source_claims.csv`, `nigc_declination_letters.csv` | `91_build_nigc_declinations.py` | `100_finish_declinations_and_employment.py` |
| `gaming_properties.csv` | `82_build_gaming_property_dataset.py` | `160_sync_published_gaming_view.py`, `175_sync_published_property_view_entities.py`, `255_fix_gaming_property_deal_counts.py` |
| `gaming_property_universe_events.csv` | `89_nigc_map_wayback_universe.py` | `165_link_universe_events_to_hub.py` |
| `ca_gaming_facilities_official.csv` | `103_build_california_gaming.py` | `266_apply_gaming_hub_spillover_rulings.py` |
| `digital_gaming_revenue.csv` | `119_build_digital_and_loyalty.py` | `174_backfill_digital_gaming_tiers.py` |
| `deals_party_autoresolved.csv` | `57_autoresolve_deal_parties.py` | `154_extend_autoresolved_parties_additive.py` |
| `native_bills.csv` | `14_build_bills_votes.py` | `35_entity_harvest.py` |
| `native_issue_litigation_positions.csv` | `139_build_litigation_positions.py` | `140_build_grantmaker_funding_flows.py` |
| `native_entity_lobbying_disclosures.csv`, `lobbying_unmatched_clients.csv`, `tribe_year_lobbying_panel.csv` | ~~`02_match_filings_to_tribes.py` **and**~~ `05_match_filings_v2.py` — **RESOLVED 2026-08-28**, v1 chain archived to `graveyard/2026-08-28_lobbying_v1_chain/`; ordering `05 → 65` now declared | `65_lobbying_organization_type_guard.py` |
| `nho_ito_spine_crosswalk.csv` | `61_add_nho_intertribal_to_spine.py` | `163_promote_nho_universe_in_place.py` |
| `nho_verified_entities.csv` | ~~`06_verify_nho_via_8a.py` **and**~~ `19_rebuild_nho_layer.py` — **RESOLVED 2026-08-28**, 06 archived to `graveyard/2026-08-28_nho_disproven_8a_inference/` (its 8(a)-proves-NHO inference is recorded as disproven in 19's own docstring) | — |
| `prime_contracts_entity_year.csv` | `40_build_prime_contracts.py` **then** `131_merge_archive_backfill.py` — **ORDERING DECLARED 2026-08-28**: 40 builds, 131 merges the 631,507-row archive backfill and regenerates the panel. Full chain `40 → 131 → 207` | — |
| `subawards.csv` | `20_build_subcontracts.py` | `121_pull_subawards_api.py`, `45_promote_subawards.py`, `250_demote_stale_tierA_subaward_rows.py` |
| `admin_appeal_decisions.csv`, `admin_appeal_parties.csv` | `144_build_admin_appeals.py` **and** `168_link_adjudication_hubs.py` | — |

**`deals_party_autoresolved.csv` deserves its own line.** `START_HERE.md`
already records, from an actual incident, that re-running `57` to widen its
input **rebuilds from the current spine and loses work** — it repointed
Confederated Salish and Kootenai from the tribal government to that tribe's
college, plus three more, and dropped four parties. `154` exists precisely to
merge additively instead. The pair is now detected, not just remembered.

### 45 tables have more than one writing script

Recorded under `class6_io_map.multi_writer_tables`. More than one writer is not
a defect by itself — the spine legitimately has thirteen in-place appenders —
but **it is the population every class-6 collision has come out of, and the
ordering between them is written down nowhere in code.** The heaviest:

| table | writers |
|---|---:|
| `cedar_entity_spine.csv` | 14 |
| `codebook_master.csv` | 13 |
| `cedar_identifier_ledger_final.csv` | 8 |
| `prime_contracts.csv` | 5 |
| `gaming_facilities.csv`, `gaming_properties.csv`, `deals_classified.csv`, `subawards.csv`, `np_orgs.csv`, `gaming_employment_observations.csv` | 4 each |

**`prime_contracts.csv` is the one to watch and the detector cannot prove it.**
Its five writers all read the file first, so no rebuild-only writer exists and
class 6 does not fire — yet `START_HERE.md` states plainly that a rebuild of
`prime_contracts.csv` reverts `207_normalize_extent_competed.py` and that 207
must be re-run. **A read-then-rewrite-from-elsewhere is indistinguishable from a
read-then-enrich by static analysis.** That limit is stated here rather than
papered over: for tables with many writers, the ordering has to be written down
by a person. `62_no_regression_check.py`'s
`files_with_columns_lost_vs_backup` is the runtime backstop and is currently 0.

### The ordering rule, restated

> A full-rebuild stage and an in-place enricher on one file need an ordering,
> and **the enricher runs LAST**. Before a rebuild, look for a
> `.bak_<date>_pre_<script>` file sitting beside the output — that is the signal
> an enricher has touched it — and re-run that enricher afterwards.
>
> And: **a partial restore is a rebuild revert wearing a different hat.**
> Restore the whole set or none of it.

---

## WHAT WAS CHANGED, EXACTLY

| file | change | backup |
|---|---|---|
| `code/293_lint_bug_classes.py` | **new** — the linter | — |
| `code/62_no_regression_check.py` | `measure_lint_bug_classes()`; nine metrics folded in; `lint_new_defect_instances` added to MUST_BE_ZERO, the eight per-class counters to MUST_NOT_RISE | in place, additive |
| `code/107_pull_remaining_states.py` | class 2a fix (`fetched_date`, 494/494 blank) | `.bak_2026-08-26_pre_293_lint_bug_classes` |
| `code/94_rescan_universes.py` | class 2a fix (`identifier_publishable`) | `.bak_2026-08-26_pre_293_lint_bug_classes` |
| `code/88_build_deals_taxonomy.py` | class 2c fix — names each withdrawn `Deal_ID` instead of counting them | `.bak_2026-08-26_pre_293_lint_bug_classes` |
| `code/164_link_facility_hub_sources.py` | a three-line `lint-ok: class1` waiver **with a reason** | in place, comment only |
| `AGENTS.md` | the six classes added as named, numbered defects | in place, appended |
| `docs/lint_bug_classes.json`, `docs/lint_bug_classes_baseline.json` | new artefacts | — |

**No file in `data/` was written by this pass.** Every edited script was
compiled (`py_compile`) and re-read after editing. **No script on the NEVER RUN
list was executed** — `88` was edited and not run.

---

## HOW TO KEEP IT FIXED

1. **`62_no_regression_check.py` now fails on a new instance.** It proved
   itself within four minutes of being wired in: it caught
   `215_pull_nm_revenue_sharing_quarters.py`, written 96 seconds earlier by a
   live agent, as a new class-4 instance.
2. **`--selftest` proves the detectors still detect.** Each case is the real
   defect reduced to its smallest form. If someone narrows a detector to
   quieten a false positive and it stops seeing the thing it was built for,
   `--selftest` fails and names it. **A detector that has silently stopped
   detecting is worse than no detector: it reports clean.**
3. **A waiver requires a reason.** `# lint-ok: classN - why`, on the flagged
   line or anywhere in the comment block above it. Waived findings are counted
   and listed in every run — never hidden. This project counts what it drops,
   by name; the linter obeys its own rule.
4. **The registries are imported, never copied.** Class 1 reads
   `cedar_domain.PROMOTED_TABLES`. Add a promoted table there the day it is
   created, not the day it is miscounted.
5. **`NOT PARSED` is printed loudly and is not the same as clean.** During this
   audit `227_anomaly_sweep.py` was mid-write and did not parse for about four
   minutes. It parses now. A file the linter could not read has been checked for
   nothing.

---

## NAMED GATE / LINT FAILURES THAT ARE NOT MINE

Per standing rule 15 option 3: name the failing metric, the owning file, and
what has to happen — before continuing.

**1. `62_no_regression_check.py` FAILS on a shipping-registration metric.**
Measured before this pass began, and clearing on its own while it ran.

```
                                 at session start   at session end
ship_tables_at_zero            205 -> 209           cleared
tables_missing_from_25_TABLES  234 -> 238           cleared
tables_missing_from_27_SPEC    249 -> 253           249 -> 250
tables_missing_notes_contract  206 -> 210           cleared
```

**Three of the four cleared without any action from this session**, because the
owning agent re-ran its registry build in between — which is the naming rule
working, and is worth recording as evidence that it does.

**Cause: four unregistered tables**, named by the gate itself —
`contractor_ranking.csv` (1,429), `individual_native_firm_contracts_published.csv`
(613), `individual_native_firm_contracts.csv` (324),
`individual_native_firm_register.csv` (45).
**Owner: whoever is running `code/269_build_contractor_ranking.py`,
`code/241_promote_individual_native_firms_in_place.py` and
`code/242_build_individual_native_firm_contracts.py`.**
**What has to happen:** register a codebook block for each, then re-run
`the full 7-step ship chain (`py -3 code/build.py ship`; “87 → 25 → 27” is a 3-step shorthand that omits the codebook build, the gate, the coverage profile and the harmonised views)` per `docs/SHIPPING_RUNBOOK.md`. **Do not use
`41_build_codebooks.py`** — it writes the master in `"w"` mode and would delete
21 of 43 blocks. Use a fragment plus `cedar_register_codebook.py`.
`ship_dist_rows` ROSE (5,227,896 → 5,230,446) and the three trap metrics are 0,
so nothing was lost: this is collection outrunning registration.

**2. `lint_class4` — `code/215_pull_nm_revenue_sharing_quarters.py:67` and
`code/217_pull_az_adg_report_archive.py`.** 217 appeared at 19:25:05, ten
minutes after 215, same author and same shape — which is this whole audit's
argument in miniature: the class reproduces itself faster than any one fix
travels.
Written **2026-08-26 19:14:54**, ninety-six seconds before the gate ran, by the
agent working New Mexico / Arizona gaming regulators (work-queue item 9). A
`RUN_DEADLINE` exits its loop, the file writes `finished`, and it never compares
what it retrieved against a source-reported total. **This is live work, not
abandoned work, and editing it would race its author.**
**What has to happen:** record NM's own reported document/quarter count beside
what was retrieved, and refuse to write `finished` when they differ. One field,
one comparison. Then `py -3 code/293_lint_bug_classes.py --baseline`.

---

## THE 285 FILES CHECKED AND FOUND CLEAN

All six classes, no findings. The complete list is in
`docs/_clean_scripts_checked_2026-08-26.txt`, written by this pass so the
**denominator is auditable rather than asserted**.

Nine of the scripts named in the original defect reports are on it, re-verified
against the files rather than against their own docstrings:
`35_coverage_audit.py`, `59_build_deal_source_index.py`,
`73_add_tcu_and_cdfi.py`, `31_build_dataset5_linked.py`,
`175_sync_published_property_view_entities.py`,
`148_resolve_schedule_i_recipients.py`, `102_build_coverage_profile.py`,
`164_link_facility_hub_sources.py`, `87_build_dataset_notes.py`.

**Four are NOT on it, and saying so matters more than the nine that are.** Each
is clean of the class it was originally reported for and carries a finding in a
different class — which is the whole argument for sweeping by shape instead of
by incident:

| script | clean of | still flagged for |
|---|---|---|
| `57_autoresolve_deal_parties.py` | class 1 (additions glob) | **class 6** — rebuild-only writer of `deals_party_autoresolved.csv` against `154`'s additive merge |
| `82_build_gaming_property_dataset.py` | class 1 | **class 6** — rebuild-only writer of `gaming_properties.csv` against three in-place syncers |
| `119_build_digital_and_loyalty.py` | class 2a (the dead `setdefault`) | **class 6** — rebuild-only writer of `digital_gaming_revenue.csv` against `174_backfill_digital_gaming_tiers.py` |
| `33_apply_party_rulings.py` | class 1 | **class 2c** — `excluded_rows` counted and never named |

**Clean means clean of these six shapes. It does not mean correct.** The linter
finds structure, not truth; it cannot tell a good matcher from a bad one, and it
has nothing to say about the judgement calls this project actually lives on.
