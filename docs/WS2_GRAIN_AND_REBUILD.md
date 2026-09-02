# WS2 — the entity-layer hub and contractors: grain, keys, and the spine rebuild

*Measured 2026-09-01 by `code/572_ws2_contracts.py`. Regenerate rather than edit — every number below is taken from the files on disk at run time.*

## 1. The three alleged duplicate counts: CONFIRMED, and they are one defect

`prime_contracts.csv` was once recorded at 80,778 literal duplicate rows and the real answer was zero, so these were re-measured before anything was written down. This time the allegation holds:

| table | rows | literal duplicate rows | alleged | verdict |
|---|---:|---:|---:|---|
| `cedar_identifier_graph_edges.csv` | 46,051 | 2,451 | 2,451 | confirmed |
| `cedar_ruling_ledger_consolidated.csv` | 15,587 | 6,302 | 6,302 | confirmed |
| `cross_dataset_ruling_map.csv` | 7,507 | 2,228 | 2,228 | confirmed |
| `tcu_cdfi_ownership_evidence.csv` | 130 | 4 | 4 | confirmed |
| `contractor_ranking.csv` | 1,429 | 0 | 0 | confirmed |
| `fpds_uei_cage_map.csv` | 34,601 | 0 | 0 | confirmed |

But the count being right does not make three defects. It is **one defect in one script, propagated twice.**

`23_cross_dataset_propagation.py` appends one row every time a ruled identifier is seen **in a target dataset row**, and the row it writes carries no column naming that target row. So N real applications of one ruling render as N byte-identical rows. UEI `KDGNQQAMNUD1` alone produces 860 rows in `cross_dataset_ruling_map.csv`; `173_consolidate_rulings_ledger.py` turns them into 860 ledger rows and `169_build_identifier_graph.py` into 860 identical `BLOCK` edges, each stamped `n_asserting_sources = 1`.

2,850 of the ledger's 15,587 rows and 7,228 of the graph's 46,051 edges are sourced from that one file.

**Do not de-duplicate any of the three.** Each row in `cross_dataset_ruling_map.csv` records a real, distinct application of a ruling to a real target row; deleting them destroys the only measure of how far a ruling reached. The fix is the same shape as `430`'s fix for `prime_contracts`: write the identity that was dropped. `23` holds the target row at the moment it appends — one extra column (the target row's own transaction/award key) turns every duplicate into a distinct, keyable event, and the counts go to zero without removing a row. Until that change, the graph's degree counts and the ledger's per-subject counts are inflated and neither table can be given a primary key.

## 2. `fpds_uei_cage_map.csv` — DECLARED

The `GRAIN_OPEN` question asked whether the key needs the year range, or whether the table is one row per UEI. Neither. **`(uei, cage_code, legal_business_name)` is unique across all 34,601 rows** (0 duplicates), so `first_year`/`last_year`/`n_observations` are the rollup and `source_file` — a `;`-joined list — is not needed in the key. One row per UEI is refuted: `uei` repeats up to 16 times.

**A join hazard that matters more than the grain.**

- `cage_code` is blank on **23,510** rows — a UEI observed under a legal name with no CAGE in that extract. Blank is a value here, not a gap.
- `cage_code` is the literal string **`NAN`** on **2,196** rows spanning **2,193 distinct UEIs** — a null stringified on export. Anyone joining on `cage_code` without excluding it fuses 2,193 unrelated entities into one.
- 9 further rows carry something that is not five characters and cannot be a CAGE.
- Excluding those, the route is near-exact: of **6,843 real CAGE codes only 15 map to more than one UEI**, and none maps to more than two. This is why the shard-E ASRC Federal link worked where name matching cannot — and why the `NAN` rows have to be excluded in the query, not discovered later.

## 3. `contractor_ranking.csv` — UNSTATED, and this is the answer, not a shortfall

`269_build_contractor_ranking.py` emits one row per `(tribe_id, firm_key)`, where `firm_key` is the awardee UEI or a `NAME:` fallback. **`firm_key` is never written to the file**, and the privacy guard then blanks `operating_company_uei` and replaces `operating_company_name` with the literal `WITHHELD_POSSIBLE_PERSONAL_NAME` on 134 of 1,429 rows. The redaction is not injective, so distinct operating companies of the same owner become indistinguishable.

Measured: **all 19 non-measure columns taken together still leave 6 duplicate rows.** `(owner_entity_id, operating_company_uei, operating_company_name)` leaves 30, and **every one of them is a withheld row** — on the 1,295 published rows that key is unique with no blanks. There is no primary key on the shipped, non-measure columns, and a key containing a dollar amount is not a grain.

The withheld rows are also a false positive worth naming on its own: they include **Nez Perce Tribe, Pueblo of Acoma, Rosebud Sioux Tribe, Ramah Navajo Chapter, Blackfeet Utilities and Wyandotte Net Tel** — tribal governments and tribal utilities, suppressed as possible personal names, one of them carrying $71.9M.

**The fix, precisely.** `269` should emit one more column — an ordinal `operating_company_seq`, 1..n within `owner_entity_id` in the sort order it already uses. `(owner_entity_id, operating_company_seq)` is then unique by construction, leaks nothing a redaction was protecting, and lets this table be declared. That is a one-column change to a script WS2 does not own.

## 4. C7 — what may be summed in `contractor_ranking.csv`

| statement | measured |
|---|---:|
| `SUM(firm_obligations_usd)` over every row | $176.74B |
| `prime_contracts.csv`, tier-A attributed `total_obligations` | $176.74B |
| difference | $-0.04 |
| `SUM(owner_obligations_usd)` over every row | $6,535.96B |
| the same, over distinct `owner_entity_id` | $176.74B |
| inflation if row-summed | **36.98x** over 283 owners |

So:

1. **`firm_obligations_usd` is the one column summable at row grain.** It totals to within $0.04 of the tier-A attributed slice of `prime_contracts.csv` - rounding, on $176.7B - which means the ranking is a lossless partition of that slice — **and that it is the same money**. Summing this table alongside the transaction table, or unioning them, double-counts $176.74B.
2. **Every `owner_*` column is an OWNER-grain attribute repeated on every operating-company row of that owner.** Row-summing `owner_obligations_usd` inflates it 37.0x. They may be totalled only after collapsing to distinct `owner_entity_id`.
3. `firm_*` columns are firm-grain and additive. `owner_rank` is an owner attribute, not a row attribute.

## 5. C8 — what a rebuild of the hub actually destroys, and what a safe one requires

*Measured without running either builder.*

### 5.1 `01_build_entity_spine.py`

| | |
|---|---:|
| live `cedar_entity_spine.csv` rows | 1,555 |
| `canonical_tribe_table.csv`, 01's **only** spine source | 687 |
| **entities a rebuild drops** | **868** (56%) |
| columns on the live file | 44 |
| columns 01 writes | 12 |
| **columns a rebuild drops** | **32** |

The dropped entities, by class:

- 210 Native Hawaiian Organization
- 185 BIE School
- 173 Alaska Native Village Corporation
- 64 Native Community Development Financial Institution
- 56 Intertribal Organization
- 45 Individually Native-owned business
- 43 Urban Indian Organization
- 37 Tribal College or University
- 29 Native Financial Institution
- 20 Federal-level self-governance consortium
- 6 ANCSA Group Corporation

01 builds `spine = {}` and fills it from `canonical_tribe_table.csv` alone. Everything scripts 52, 61, 73, 75, 163, 241, 426 and 524 appended is absent from that source and therefore gone, and the 12 columns it writes discard the other 32 — including `cedar_uid`, `parent_entity_id`, `fr_official_name`, `evidence_tier` and every hierarchy column.

**What is unrecoverable, and what is not.** `data/spine/*` is gitignored (`.gitignore` line 95) with exactly two exceptions: `cedar_identity_register.csv` and `cedar_handle_history.csv`, which are force-tracked because they are not regenerable. **`cedar_entity_spine.csv` itself is NOT in git, so git cannot restore it.** The only safety net is the `.csv.bak_<date>_pre<NN>` convention — and **`01` is one of the few spine writers that does not take one.** Every enricher that touches the spine (51, 52, 61, 66, 69, 71, 73, 74, 75, 163, 241, 416, 426, 503, 524) does.

The one piece of good news, and it is load-bearing: **`handle` in the register equals `tribe_id` in the spine for all 1,555 of 1,555 rows.** So the `cedar_uid` ↔ entity binding survives a spine overwrite inside a git-tracked file and can be rejoined on `handle`. That matters because only 1,009 spine rows carry a `cedar_entity_id`, so the register's other join column would have recovered barely two thirds of them.

### 5.2 `09_import_rulings.py`

09 rebuilds `cedar_identifier_ledger_final.csv` (20,577 rows) from `cedar_identifier_ledger_tiered.csv` (19,232 rows), which does not carry what later scripts appended directly to `_final`. **A rerun today drops 1,345 ledger rows** - 18 at tier A, 1,325 at tier B, 2 at tier X. The tier-A losses are `elijah_ruling` and `nho_verified_entities.csv` rows — owner adjudications, the one thing in this project that cannot be re-derived from a source. `NEVER_RUN` records that running it on 2026-08-08 destroyed 1,327 rows and 451 village-corporation links; the number has since grown to 1,345.

### 5.3 The safe rebuild procedure

**First, the risk is smaller than the blocker text implies, and the blocker should say so.** `build.plan_for('_entity_layer')` already sorts both scripts into a `blocked` phase, so `py -3 code/build.py run _entity_layer --execute` — the very command 518 prints as `rebuild_entry` — **does not run them**. The residual exposure is a human or an agent invoking `py -3 code/01_build_entity_spine.py` directly, which nothing prevents and which no backup would survive.

A rebuild is survivable only if all six of these hold. **Today item 4 cannot be satisfied**, which is the whole of the C8 answer; the rest are written out because the failure mode is skipping one.

1. **Back up first, by hand, because the builders will not.** `shutil.copy2` (or `cp`) `data/spine/cedar_entity_spine.csv`, `data/spine/cedar_identifier_ledger.csv`, `data/clean/cedar_identifier_ledger_final.csv` and `data/clean/cedar_identifier_ledger_tiered.csv` to `<name>.bak_<date>_pre01` / `_pre09`. This is the project's existing convention and it is the ONLY recovery route for these files.
2. **Record the pre-rebuild census**: row count, distinct `tribe_id`, full column list, and the tier histogram of the ledger. Without it there is nothing to compare the rebuild against, and a 56% loss looks like a successful run.
3. **Confirm the seven external inputs are present** under `data/raw/external/` and that `C:\Users\esm247\Desktop\dissertation\data\tribal_federal_spending` still resolves. All seven are present as of this measurement. If a source is missing, 01 logs `MISSING` and silently builds from the previously staged copy — which is a resilience, but it means a rebuild can succeed while quietly using stale inputs.
4. **Replay every enricher, and understand that the ORDER is not recorded anywhere.** `cedar_pipeline.all_orderings` names 15 spine-modifying enrichers and 8 ledger enrichers, but `build.plan_for` returns them in lexicographic order (…, `50`, `503`, `51`, `52`, …), which is not the order in which they were originally applied. **No dependency-correct replay order exists in the repo.** Producing one is the prerequisite this blocker really names.
5. **Do not replay a minting enricher blind.** `426_mint_bristol_bay_spine_entities.py` mints. `503_identity.py mint` re-uses existing uids keyed on the handle and is safe because handle equals tribe_id; 426 must be checked against the register before it is run, and the register is append-only — a wrong replay cannot be undone by deleting rows from it.
6. **Gate on conservation, not on completion.** The rebuild is acceptable only if the post-replay spine has ≥ 1,555 rows and all 44 columns, and the post-replay ledger has ≥ 20,577 rows with no fall in the tier-A count. Anything less is a partial restore wearing a green build log.

**The honest bottom line: the spine cannot be rebuilt safely today, and the missing piece is specific.** It is not the backups — the convention exists and every enricher but the two rebuilders honours it. It is that *no dependency-correct enricher replay order is recorded*, so nobody can state what the 15 spine enrichers must run in, or prove that running them reproduces the 1,555 rows and 44 columns that are on disk. Two changes convert this from a mystery into a task: (a) `01` and `09` take a `.bak` before writing, like every other writer in the project; (b) the replay order is recorded in `cedar_pipeline` and exercised once, against the census in step 2. Until (b), the correct operational posture is the one already in force — never run them, keep them in `NEVER_RUN`, and keep the planner's `blocked` phase.

## 6. `foia_request_index.csv` — a GRAIN_OPEN question answered

The open question asked whether the 381 surplus rows mean the grain is `(request, matched tribe mention)` or whether `foia_request_id` is simply not unique. It is neither ambiguous nor a grain: **all 744 rows in a collision group carry `control_number_appears_more_than_once` in their own `parse_quality_reason`, and no row outside one does.** `request_description` differs in 363 of 363 groups. One FOIA log entry was split across two rows by the parser, and the table already names every instance. `foia_request_id` IS the intended key; this is a defect for the owner of `136_build_congressional_correspondence_and_foia_index.py` to repair, not a grain for a contract to declare.

**`visitor_record_foia_requests.csv` has the identical signature from a different builder.** 22 colliding `foia_request_id` values, 22 surplus rows, and `request_description_verbatim` differs in 22 of 22 groups — which is why the only "unique key" anyone found on that table was the free-text description itself. `136` and `146` parse different sources and produced the same defect, so this is **one class of fix, not two open questions**: a FOIA log entry whose control number appears twice in the source text is being emitted as two fragmentary rows instead of one.

## 7. C5 — row conservation for `contractors`

Merged into the shared `data/clean/cedar_harvest_conservation.csv` on the `(source_table, disposition)` key: 111 → 111 ledger rows, accounted rows 2,196,501 → 2,196,501. Nothing belonging to another workstream was rewritten, and a `.bak` was taken first.

## 8. What is still blocked, and who owns it

| blocker | table | owner |
|---|---|---|
| C1/C2/C3 — no key while the rows are indistinguishable | `cross_dataset_ruling_map.csv` | `23_cross_dataset_propagation.py`: write the target row key |
| C1/C2/C3 — inherited from the above | `cedar_ruling_ledger_consolidated.csv` | `173_consolidate_rulings_ledger.py` |
| C1/C2/C3 — inherited from the above | `cedar_identifier_graph_edges.csv` | `169_build_identifier_graph.py` |
| C1/C2/C7 — key destroyed by redaction | `contractor_ranking.csv` | `269`: emit `operating_company_seq` |
| C1/C2 — parse split, table names it itself | `foia_request_index.csv` | `136` |
| C1/C2 — 22 collisions on `foia_request_id` | `visitor_record_foia_requests.csv` | `146` |
| C1/C2/C3 — 4 literal duplicate rows of 130 | `tcu_cdfi_ownership_evidence.csv` | `73_add_tcu_and_cdfi.py` |
| C8 — no recorded enricher replay order | `cedar_entity_spine.csv` | pipeline owner; see §5.3 |
